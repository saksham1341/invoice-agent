import os
import json
from typing import TypedDict, Optional, List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers.openai_functions import JsonOutputFunctionsParser
from langgraph.graph import StateGraph, END
import pandas as pd
from io import BytesIO
from PIL import Image
import pytesseract
from langchain_core.exceptions import OutputParserException
from . import config
from .schema import (
    BoundingBox, WithValue, AreasOfInterest, ExtractedHeader, 
    LineItem, ExtractedLineItems, ExtractedSummary
)

# --- Configuration ---
GEMINI_MODEL_NAME = config.GEMINI_MODEL_NAME

def filter_ocr_data_by_bbox(ocr_data, bbox_dict):
    """Filters OCR data to include only items within a given bounding box."""
    if not bbox_dict:
        return []
    bbox = BoundingBox(**bbox_dict)
    filtered_data = [
        item for item in ocr_data
        if (item['left'] >= bbox.x1 and item['top'] >= bbox.y1 and
            (item['left'] + item['width']) <= bbox.x2 and
            (item['top'] + item['height']) <= bbox.y2)
    ]
    return filtered_data

# --- LangGraph Agent State ---

class GraphState(TypedDict):
    """Represents the state of our new agentic workflow."""
    image_content: bytes
    ocr_data: List[Dict[str, Any]] 
    areas_of_interest: Optional[AreasOfInterest]
    extracted_header: Optional[ExtractedHeader]
    extracted_line_items: Optional[ExtractedLineItems]
    extracted_summary: Optional[ExtractedSummary]
    extracted_data: Dict[str, Any]

# --- Graph Nodes ---

def extract_structured_ocr(state: GraphState):
    """Extracts structured OCR data from the image file content."""
    print("--- EXTRACTING STRUCTURED OCR DATA ---")
    image_file = BytesIO(state['image_content'])
    image = Image.open(image_file)
    ocr_df = pytesseract.image_to_data(image, output_type=pytesseract.Output.DATAFRAME)
    ocr_df.dropna(inplace=True)
    ocr_df = ocr_df[ocr_df.conf != -1]
    ocr_data = ocr_df.to_dict('records')
    return {"ocr_data": ocr_data}

def decide_aoi(state: GraphState):
    """Identifies the coordinates of key areas of interest."""
    print("--- DECIDING AREAS OF INTEREST ---")
    ocr_text_with_coords = "\n".join([
        f"text: '{item['text']}', x1: {item['left']}, y1: {item['top']}, x2: {item['left'] + item['width']}, y2: {item['top'] + item['height']}" 
        for item in state['ocr_data']
    ])

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert document layout analyst specializing in invoice processing. Your task is to identify the precise bounding boxes (x1, y1, x2, y2) for the primary functional areas of the provided invoice based on OCR tokens.\n\n"
                   "Definitions:\n"
                   "1. **header_area**: Encapsulates identifying metadata: Vendor/Client names, addresses, Invoice Number, Date, and Due Date.\n"
                   "2. **line_items_area**: The core tabular region containing itemized descriptions, quantities, and prices. Must include column headers and all rows.\n"
                   "3. **summary_area**: The bottom section containing Subtotal, Taxes (VAT/GST), and the final Total Amount.\n\n"
                   "Guidelines:\n"
                   "- Bounding boxes must be inclusive of all relevant text. IMPORTANT: The x2 and y2 coordinates must be large enough to contain the full width and height of the last tokens in that area.\n"
                   "- If an area is missing, return null for that specific box.\n"
                   "- Ensure coordinates are consistent with the provided OCR input."),
        ("human", "OCR Token Data with Full Coordinates:\n{ocr_data}")
    ])
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL_NAME, temperature=0)
    parser = JsonOutputFunctionsParser()
    chain = prompt | llm.bind(functions=[AreasOfInterest]) | parser
    try:
        areas = chain.invoke({"ocr_data": ocr_text_with_coords})
    except OutputParserException:
        print("Warning: Could not parse LLM output for AOI. Returning empty.")
        areas = {}
    return {"areas_of_interest": areas}

def extract_header_data(state: GraphState):
    """Extracts data from the header area."""
    print("--- EXTRACTING HEADER DATA ---")
    header_area = state["areas_of_interest"].get("header_area")
    if not header_area:
        return {"extracted_header": None}
    header_ocr_data = filter_ocr_data_by_bbox(state['ocr_data'], header_area)
    
    ocr_text_with_coords = "\n".join([f"text: '{item['text']}', x1: {item['left']}, y1: {item['top']}, x2: {item['left'] + item['width']}, y2: {item['top'] + item['height']}" for item in header_ocr_data])

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a specialized extraction agent for invoice headers. Your goal is to extract key metadata from the provided OCR tokens. For each field, you must provide both the 'value' and a precise 'bbox' (x1, y1, x2, y2) that encompasses the source text.\n\n"
                   "Fields to Extract:\n"
                   "- **invoice_number**: The unique ID (often labeled 'Invoice #', 'Bill No', 'Ref').\n"
                   "- **vendor_name**: Full legal name of the entity issuing the invoice.\n"
                   "- **client_name**: Full legal name of the entity receiving the invoice.\n"
                   "- **invoice_date**: Date of issue. Standardize to YYYY-MM-DD if possible.\n"
                   "- **due_date**: Deadline for payment. Standardize to YYYY-MM-DD if possible.\n\n"
                   "Instructions:\n"
                   "- Be extremely precise with bounding boxes; they should tightly wrap the relevant text.\n"
                   "- IMPORTANT: The 'x2' and 'y2' must reflect the bottom-right corner of the final token in the field (x2 = left + width, y2 = top + height).\n"
                   "- If a field is not present, return null for its object."),
        ("human", "Header Area OCR Tokens:\n{ocr_data_with_coords}")
    ])
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL_NAME, temperature=0)
    parser = JsonOutputFunctionsParser()
    chain = prompt | llm.bind(functions=[ExtractedHeader]) | parser
    try:
        header_data = chain.invoke({"ocr_data_with_coords": ocr_text_with_coords})
    except OutputParserException:
        print("Warning: Could not parse LLM output for header extraction. Returning None.")
        header_data = None
    return {"extracted_header": header_data}

def extract_line_items_data(state: GraphState):
    """Extracts data from the line items area."""
    print("--- EXTRACTING LINE ITEMS DATA ---")
    line_items_area = state["areas_of_interest"].get("line_items_area")
    if not line_items_area:
        return {"extracted_line_items": None}
    line_items_ocr_data = filter_ocr_data_by_bbox(state['ocr_data'], line_items_area)
    
    ocr_text_with_coords = "\n".join([f"text: '{item['text']}', x1: {item['left']}, y1: {item['top']}, x2: {item['left'] + item['width']}, y2: {item['top'] + item['height']}" for item in line_items_ocr_data])

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a specialized agent for itemizing invoice rows. Your task is to extract all line items from the provided OCR data. For each row, you must identify:\n"
                   "1. **description**: Full text of the service or product. Provide value and field-specific bbox.\n"
                   "2. **quantity**: Numeric count. Provide value and field-specific bbox.\n"
                   "3. **unit_price**: Price per unit. Provide value and field-specific bbox.\n"
                   "4. **total_price**: Line total. Provide value and field-specific bbox.\n"
                   "5. **bbox**: A single bounding box that encompasses the entire row (all columns).\n\n"
                   "Precision Guidelines:\n"
                   "- Ensure each 'LineItem' object represents exactly one row in the invoice table.\n"
                   "- Bounding boxes must accurately reflect the coordinates in the OCR input. The 'x2' of the row bbox must match the 'x2' of the rightmost column (usually total_price), and 'y2' must match the bottom-most coordinate of that row's tokens.\n"
                   "- Do not merge adjacent line items."),
        ("human", "Line Items Area OCR Tokens:\n{ocr_data_with_coords}")
    ])
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL_NAME, temperature=0)
    parser = JsonOutputFunctionsParser()
    chain = prompt | llm.bind(functions=[ExtractedLineItems]) | parser
    try:
        line_items_data = chain.invoke({"ocr_data_with_coords": ocr_text_with_coords})
    except OutputParserException:
        print("Warning: Could not parse LLM output for line items extraction. Returning None.")
        line_items_data = None
    return {"extracted_line_items": line_items_data}

def extract_summary_data(state: GraphState):
    """Extracts data from the summary area."""
    print("--- EXTRACTING SUMMARY DATA ---")
    summary_area = state["areas_of_interest"].get("summary_area")
    if not summary_area:
        return {"extracted_summary": None}
    summary_ocr_data = filter_ocr_data_by_bbox(state['ocr_data'], summary_area)
    
    ocr_text_with_coords = "\n".join([f"text: '{item['text']}', x1: {item['left']}, y1: {item['top']}, x2: {item['left'] + item['width']}, y2: {item['top'] + item['height']}" for item in summary_ocr_data])

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a specialized agent for invoice summary extraction. Your task is to extract the final financial totals. For each field, provide the 'value' and a precise 'bbox'.\n\n"
                   "Fields:\n"
                   "- **total_amount**: The final gross amount due (often 'Grand Total', 'Total', 'Net Payable').\n"
                   "- **tax_amount**: The total tax applied (often 'VAT', 'GST', 'Sales Tax').\n\n"
                   "Guidelines:\n"
                   "- Bounding boxes must tightly wrap the numeric value and any currency symbol if present.\n"
                   "- Ensure 'x2' and 'y2' include the full width and height of the last digits/tokens to avoid cropping.\n"
                   "- If a field is missing, return null."),
        ("human", "Summary Area OCR Tokens:\n{ocr_data_with_coords}")
    ])
    llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL_NAME, temperature=0)
    parser = JsonOutputFunctionsParser()
    chain = prompt | llm.bind(functions=[ExtractedSummary]) | parser
    try:
        summary_data = chain.invoke({"ocr_data_with_coords": ocr_text_with_coords})
    except OutputParserException:
        print("Warning: Could not parse LLM output for summary extraction. Returning None.")
        summary_data = None
    return {"extracted_summary": summary_data}

def aggregate_results(state: GraphState):
    """Aggregates results from all extractors into the final JSON."""
    print("--- AGGREGATING RESULTS ---")
    
    final_data = {}

    # Process header
    header = state.get("extracted_header")
    if header:
        for field, value_with_bbox in header.items():
            if value_with_bbox:
                final_data[field] = value_with_bbox

    # Process summary
    summary = state.get("extracted_summary")
    if summary:
        for field, value_with_bbox in summary.items():
            if value_with_bbox:
                final_data[field] = value_with_bbox

    # Process line items
    line_items_data = state.get("extracted_line_items")
    if line_items_data and line_items_data.get("line_items"):
        final_data["line_items"] = [
            {
                "description": item.get("description"),
                "quantity": item.get("quantity"),
                "unit_price": item.get("unit_price"),
                "total_price": item.get("total_price"),
                "bbox": item.get("bbox")
            }
            for item in line_items_data["line_items"]
        ]
    else:
        final_data["line_items"] = []

    return {"extracted_data": final_data}

# --- Graph Definition ---
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("extract_structured_ocr", extract_structured_ocr)
workflow.add_node("decide_aoi", decide_aoi)
workflow.add_node("extract_header_data", extract_header_data)
workflow.add_node("extract_line_items_data", extract_line_items_data)
workflow.add_node("extract_summary_data", extract_summary_data)
workflow.add_node("aggregate_results", aggregate_results)

# Define edges
workflow.set_entry_point("extract_structured_ocr")
workflow.add_edge("extract_structured_ocr", "decide_aoi")
workflow.add_edge("decide_aoi", "extract_header_data")
workflow.add_edge("extract_header_data", "extract_line_items_data")
workflow.add_edge("extract_line_items_data", "extract_summary_data")
workflow.add_edge("extract_summary_data", "aggregate_results")
workflow.add_edge("aggregate_results", END)


# Compile the graph
agent = workflow.compile()

def run_agent(image_content: bytes) -> dict:
    """
    Runs the invoice extraction agentic workflow (Synchronous version).
    """
    initial_state = {"image_content": image_content}
    final_state = agent.invoke(initial_state)
    extracted_data = final_state.get("extracted_data", {})
    return extracted_data

def run_agent_stream(image_content: bytes):
    """
    Runs the invoice extraction agentic workflow and yields updates as they occur.
    """
    initial_state = {"image_content": image_content}
    for output in agent.stream(initial_state):
        # output is a dict with node name as key and its return value as value
        yield output

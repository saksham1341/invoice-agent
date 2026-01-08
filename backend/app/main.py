import json
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

# Create the FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Determine the base directory of the backend
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from .schema import CompleteInvoice

@app.get("/api/invoice-schema")
async def get_invoice_schema():
    """
    This endpoint serves the invoice schema.
    The frontend will use this to dynamically build its form.
    """
    return CompleteInvoice.model_json_schema()

from .agent import run_agent, run_agent_stream
from fastapi.responses import StreamingResponse
import asyncio

# IMPORTANT: Check for the Google API key
if "GOOGLE_API_KEY" not in os.environ:
    raise ValueError("The GOOGLE_API_KEY environment variable is not set. Please set it to your Google API key.")

@app.post("/api/extract-invoice")
async def extract_invoice_data(file: UploadFile = File(...)):
    """
    This endpoint receives an invoice image and streams the extraction progress.
    """
    contents = await file.read()
    
    async def event_generator():
        # run_agent_stream is a generator, we run it in a thread pool to avoid blocking
        # since LangGraph invoke/stream is synchronous (usually)
        loop = asyncio.get_event_loop()
        gen = run_agent_stream(contents)
        sentinel = object()
        
        while True:
            try:
                # Get next chunk from generator. Use a sentinel to avoid StopIteration exception
                # which interacts badly with Futures in run_in_executor.
                chunk = await loop.run_in_executor(None, next, gen, sentinel)
                if chunk is sentinel:
                    break
                # Yield chunk as SSE data
                yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

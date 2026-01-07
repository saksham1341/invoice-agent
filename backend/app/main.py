import json
import os
import asyncio
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from . import config
from .schema import CompleteInvoice
from .agent import run_agent, run_agent_stream

# Create the FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/invoice-schema")
async def get_invoice_schema():
    """
    This endpoint serves the invoice schema dynamically generated from Pydantic.
    """
    return CompleteInvoice.model_json_schema()

@app.post("/api/extract-invoice")
async def extract_invoice_data(file: UploadFile = File(...)):
    """
    This endpoint receives an invoice image and streams the extraction progress.
    """
    contents = await file.read()
    
    async def event_generator():
        loop = asyncio.get_event_loop()
        gen = run_agent_stream(contents)
        sentinel = object()
        
        while True:
            try:
                # Use a sentinel to avoid StopIteration exception in run_in_executor
                chunk = await loop.run_in_executor(None, next, gen, sentinel)
                if chunk is sentinel:
                    break
                yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
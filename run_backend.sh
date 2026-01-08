#!/bin/bash

# This script runs the backend server for the invoice extraction agent.

# Activate the virtual environment
source backend/venv/bin/activate

# Check if the GOOGLE_API_KEY is set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "ERROR: The GOOGLE_API_KEY environment variable is not set."
    echo "Please set it to your Google API key."
    exit 1
fi

# Run the uvicorn server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir backend

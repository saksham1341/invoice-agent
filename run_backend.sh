#!/bin/bash

# This script runs the backend server for the invoice extraction agent.

# Activate the virtual environment
source backend/venv/bin/activate

# Run the uvicorn server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir backend

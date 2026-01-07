#!/bin/bash

# This script runs the backend server for the invoice extraction agent.
# It is configured to work both locally and on hosting services like Render.

# Use the PORT environment variable provided by Render, defaulting to 8000
PORT="${PORT:-8000}"

# Run the uvicorn server
# --app-dir backend ensures uvicorn looks in the backend directory for the app
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --app-dir backend

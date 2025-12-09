#!/bin/bash

# Start the FastAPI backend server
cd "$(dirname "$0")"

echo "Starting PerfectPunch Backend Server..."
echo "Make sure you have activated your virtual environment (venv)"

# Check if venv exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Try to start from perfectpunch_backend directory
if [ -f "perfectpunch_backend/main.py" ]; then
    cd perfectpunch_backend
    uvicorn main:app --reload --host 127.0.0.1 --port 8000
else
    echo "Error: Could not find perfectpunch_backend/main.py"
    echo "Please make sure you're in the project root directory"
    exit 1
fi


#!/bin/bash

# Simple script to check for existing NEMO processes and start only one instance

echo "Checking for existing NEMO processes..."

# Find any Python processes running main.py
EXISTING_PIDS=$(pgrep -f "python.*main.py" 2>/dev/null)

if [ ! -z "$EXISTING_PIDS" ]; then
    echo "Found existing NEMO processes: $EXISTING_PIDS"
    echo "Stopping existing processes..."
    pkill -f "python.*main.py"
    sleep 2
    echo "Existing processes stopped."
else
    echo "No existing NEMO processes found."
fi

echo "Starting NEMO server..."
cd "$(dirname "$0")"
source venv/bin/activate
python main.py

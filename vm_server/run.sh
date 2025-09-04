#!/bin/bash

# NEMO Tool Display Server Startup Script

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Check if config file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cp config.env.example .env
    echo "Please edit .env file with your configuration before running again."
    exit 1
fi

# Start the server
echo "Starting NEMO Tool Display Server..."
python main.py

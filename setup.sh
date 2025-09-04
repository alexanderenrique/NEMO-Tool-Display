#!/bin/bash

# NEMO Tool Display - Complete Setup Script

echo "NEMO Tool Display Setup"
echo "======================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check if PlatformIO is installed
if ! command -v pio &> /dev/null; then
    echo "Installing PlatformIO..."
    pip install platformio
fi

# Setup VM Server
echo "Setting up VM Server..."
cd vm_server

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp config.env.example .env
    echo "Please edit .env file with your configuration."
fi

cd ..

# Setup MQTT directories
echo "Setting up MQTT broker directories..."
mkdir -p mqtt/data mqtt/log

# Make scripts executable
chmod +x vm_server/run.sh
chmod +x setup.sh

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit vm_server/.env with your API and MQTT settings"
echo "2. Edit platformio.ini with your WiFi and MQTT settings"
echo "3. Start MQTT broker: docker-compose up -d mosquitto"
echo "4. Start VM server: cd vm_server && ./run.sh"
echo "5. Upload ESP32 firmware: pio run --target upload"
echo ""
echo "For testing:"
echo "- Test API: cd vm_server && python test_api.py"
echo "- Test MQTT: cd vm_server && python mqtt_test.py"

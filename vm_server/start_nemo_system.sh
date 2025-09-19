#!/bin/bash

# NEMO Tool Display - Complete System Startup Script
# This script starts both the MQTT broker and the NEMO server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}NEMO Tool Display - Complete System Startup${NC}"
echo "=============================================="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
ENV_FILE=".env"
BROKER_SCRIPT="start_mqtt_broker.sh"
SERVER_SCRIPT="main.py"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down NEMO system...${NC}"
    
    # Stop the Python server
    if [ ! -z "$SERVER_PID" ]; then
        echo "Stopping NEMO server (PID: $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null || true
    fi
    
    # Stop the MQTT broker
    echo "Stopping MQTT broker..."
    pkill -f "mosquitto.*mqtt/config/mosquitto.conf" 2>/dev/null || true
    
    echo -e "${GREEN}Cleanup completed.${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check if we're in the right directory
if [ ! -f "$SERVER_SCRIPT" ]; then
    echo -e "${RED}Error: $SERVER_SCRIPT not found. Please run this script from the vm_server directory.${NC}"
    exit 1
fi

# Check if Python dependencies are available
echo -e "${YELLOW}Checking Python dependencies...${NC}"
python3 -c "import paho.mqtt.client, dotenv, aiohttp" 2>/dev/null || {
    echo -e "${YELLOW}Installing required Python packages...${NC}"
    pip3 install -r requirements.txt
}

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Warning: $ENV_FILE not found. Using default configuration.${NC}"
    echo "You can copy config.env.example to .env and customize it."
fi

# Check if mosquitto is installed
if ! command_exists mosquitto; then
    echo -e "${RED}Error: mosquitto is not installed.${NC}"
    echo "Please install mosquitto:"
    echo "  Ubuntu/Debian: sudo apt-get install mosquitto mosquitto-clients"
    echo "  CentOS/RHEL: sudo yum install mosquitto mosquitto-clients"
    echo "  macOS: brew install mosquitto"
    exit 1
fi

# Check if Python is available
if ! command_exists python3; then
    echo -e "${RED}Error: python3 is not installed.${NC}"
    exit 1
fi

# Check if ports are already in use
if port_in_use 1883; then
    echo -e "${YELLOW}Warning: Port 1883 is already in use.${NC}"
fi

if port_in_use 8883; then
    echo -e "${YELLOW}Warning: Port 8883 is already in use.${NC}"
fi

# Start MQTT broker
echo -e "${YELLOW}Starting MQTT broker...${NC}"
if [ -f "$BROKER_SCRIPT" ]; then
    bash "$BROKER_SCRIPT"
else
    echo -e "${RED}Error: $BROKER_SCRIPT not found.${NC}"
    exit 1
fi

# Wait for broker to be ready
echo -e "${YELLOW}Waiting for MQTT broker to be ready...${NC}"
sleep 5

# Test broker connection
echo -e "${YELLOW}Testing MQTT broker connection...${NC}"
if command_exists mosquitto_pub; then
    mosquitto_pub -h localhost -p 1883 -t "nemo/test/startup" -m "System startup test" -q 1 || {
        echo -e "${RED}Warning: Could not connect to MQTT broker on port 1883${NC}"
    }
else
    echo -e "${YELLOW}Warning: mosquitto_pub not available, skipping connection test${NC}"
fi

# Start Python server
echo -e "${YELLOW}Starting NEMO server...${NC}"

# Start the server in the background
python3 "$SERVER_SCRIPT" &
SERVER_PID=$!

# Wait a moment for the server to start
sleep 3

# Check if server started successfully
if kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${GREEN}NEMO system started successfully!${NC}"
    echo ""
    echo "System Status:"
    echo "  - MQTT Broker: Running on port 1883 (non-SSL)"
    echo "  - NEMO Server: Running (PID: $SERVER_PID)"
    echo "  - Configuration: $ENV_FILE"
    echo ""
    echo "MQTT Topics:"
    echo "  - Backend Input: nemo/backend/tools/+/status"
    echo "  - Backend Overall: nemo/backend/tools/overall"
    echo "  - ESP32 Output: nemo/esp32/{tool_id}/status"
    echo "  - ESP32 Overall: nemo/esp32/overall"
    echo "  - Server Status: nemo/server/status"
    echo ""
    echo "Logs:"
    echo "  - MQTT Broker: mqtt/log/mosquitto.log"
    echo "  - NEMO Server: Check console output"
    echo ""
    echo "To stop the system: Press Ctrl+C or run 'pkill -f start_nemo_system.sh'"
    echo ""
    
    # Keep the script running and monitor the server
    while kill -0 $SERVER_PID 2>/dev/null; do
        sleep 1
    done
    
    echo -e "${RED}NEMO server stopped unexpectedly.${NC}"
else
    echo -e "${RED}Failed to start NEMO server.${NC}"
    exit 1
fi

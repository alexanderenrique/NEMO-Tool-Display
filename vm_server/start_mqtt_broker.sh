#!/bin/bash

# NEMO Tool Display - MQTT Broker Startup Script
# This script sets up and starts the MQTT broker with SSL support

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}NEMO Tool Display - MQTT Broker Setup${NC}"
echo "=============================================="

# Configuration
BROKER_NAME="nemo-mqtt-broker"
CERT_DIR="./mqtt/certs"
CONFIG_DIR="./mqtt/config"
DATA_DIR="./mqtt/data"
LOG_DIR="./mqtt/log"

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p "$CERT_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"

# Copy config file if it doesn't exist
if [ ! -f "$CONFIG_DIR/mosquitto.conf" ]; then
    echo -e "${YELLOW}Copying MQTT configuration...${NC}"
    if [ -f "../mqtt/config/mosquitto.conf" ]; then
        cp "../mqtt/config/mosquitto.conf" "$CONFIG_DIR/"
        echo -e "${GREEN}Configuration file copied successfully!${NC}"
    else
        echo -e "${RED}Error: Configuration file not found at ../mqtt/config/mosquitto.conf${NC}"
        echo "Please ensure the configuration file exists in the parent directory."
        exit 1
    fi
else
    echo -e "${GREEN}Configuration file already exists.${NC}"
fi

# Check if certificates already exist (optional for non-SSL setup)
if [ ! -f "$CERT_DIR/ca.crt" ] || [ ! -f "$CERT_DIR/server.crt" ] || [ ! -f "$CERT_DIR/server.key" ]; then
    echo -e "${YELLOW}Generating SSL certificates (optional for non-SSL setup)...${NC}"
    
    # Generate CA private key
    openssl genrsa -out "$CERT_DIR/ca.key" 2048
    
    # Generate CA certificate
    openssl req -new -x509 -days 365 -key "$CERT_DIR/ca.key" -out "$CERT_DIR/ca.crt" -subj "/C=US/ST=CA/L=Stanford/O=NEMO/OU=ToolDisplay/CN=NEMO-CA"
    
    # Generate server private key
    openssl genrsa -out "$CERT_DIR/server.key" 2048
    
    # Generate server certificate request
    openssl req -new -key "$CERT_DIR/server.key" -out "$CERT_DIR/server.csr" -subj "/C=US/ST=CA/L=Stanford/O=NEMO/OU=ToolDisplay/CN=localhost"
    
    # Generate server certificate signed by CA
    openssl x509 -req -in "$CERT_DIR/server.csr" -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" -CAcreateserial -out "$CERT_DIR/server.crt" -days 365
    
    # Clean up CSR file
    rm "$CERT_DIR/server.csr"
    
    echo -e "${GREEN}SSL certificates generated successfully!${NC}"
else
    echo -e "${GREEN}SSL certificates already exist, skipping generation.${NC}"
fi

# Set proper permissions
chmod 600 "$CERT_DIR"/*.key
chmod 644 "$CERT_DIR"/*.crt

# Check if mosquitto is installed
if ! command -v mosquitto &> /dev/null; then
    echo -e "${RED}Error: mosquitto is not installed.${NC}"
    echo "Please install mosquitto:"
    echo "  Ubuntu/Debian: sudo apt-get install mosquitto mosquitto-clients"
    echo "  CentOS/RHEL: sudo yum install mosquitto mosquitto-clients"
    echo "  macOS: brew install mosquitto"
    exit 1
fi

# Check if broker is already running
if pgrep -f "mosquitto.*$CONFIG_DIR/mosquitto.conf" > /dev/null; then
    echo -e "${YELLOW}MQTT broker is already running. Stopping existing instance...${NC}"
    pkill -f "mosquitto.*$CONFIG_DIR/mosquitto.conf" || true
    sleep 2
fi

# Start the MQTT broker
echo -e "${YELLOW}Starting MQTT broker...${NC}"
echo "Configuration: $CONFIG_DIR/mosquitto.conf"
echo "Data directory: $DATA_DIR"
echo "Log directory: $LOG_DIR"
echo "SSL certificates: $CERT_DIR"

# Start mosquitto in the background
mosquitto -c "$CONFIG_DIR/mosquitto.conf" -v &

# Wait a moment for the broker to start
sleep 3

# Check if broker started successfully
if pgrep -f "mosquitto.*$CONFIG_DIR/mosquitto.conf" > /dev/null; then
    echo -e "${GREEN}MQTT broker started successfully!${NC}"
    echo ""
    echo "Broker Information:"
    echo "  - Primary Port (Non-SSL): 1883  <-- Use this for ESP32"
    echo "  - SSL Port: 8883 (optional)"
    echo "  - WebSocket Port: 9001 (optional)"
    echo "  - Configuration: $CONFIG_DIR/mosquitto.conf"
    echo "  - Logs: $LOG_DIR/mosquitto.log"
    echo ""
    echo "For ESP32 Testing (Non-SSL):"
    echo "  - Broker IP: $(hostname -I | awk '{print $1}')"
    echo "  - Port: 1883"
    echo "  - Test: mosquitto_pub -h localhost -p 1883 -t 'test/topic' -m 'Hello World'"
    echo ""
    echo "SSL Certificate Information (optional):"
    echo "  - CA Certificate: $CERT_DIR/ca.crt"
    echo "  - Server Certificate: $CERT_DIR/server.crt"
    echo "  - Server Private Key: $CERT_DIR/server.key"
    echo ""
    echo "To stop the broker: pkill -f 'mosquitto.*$CONFIG_DIR/mosquitto.conf'"
else
    echo -e "${RED}Failed to start MQTT broker. Check the logs at $LOG_DIR/mosquitto.log${NC}"
    exit 1
fi

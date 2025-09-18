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
mkdir -p "$CERT_DIR" "$DATA_DIR" "$LOG_DIR"

# Check if certificates already exist
if [ ! -f "$CERT_DIR/ca.crt" ] || [ ! -f "$CERT_DIR/server.crt" ] || [ ! -f "$CERT_DIR/server.key" ]; then
    echo -e "${YELLOW}Generating SSL certificates...${NC}"
    
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
    echo "  - Non-SSL Port: 1883"
    echo "  - SSL Port: 8883"
    echo "  - WebSocket Port: 9001"
    echo "  - Configuration: $CONFIG_DIR/mosquitto.conf"
    echo "  - Logs: $LOG_DIR/mosquitto.log"
    echo ""
    echo "SSL Certificate Information:"
    echo "  - CA Certificate: $CERT_DIR/ca.crt"
    echo "  - Server Certificate: $CERT_DIR/server.crt"
    echo "  - Server Private Key: $CERT_DIR/server.key"
    echo ""
    echo "To test the broker:"
    echo "  - Non-SSL: mosquitto_pub -h localhost -p 1883 -t 'test/topic' -m 'Hello World'"
    echo "  - SSL: mosquitto_pub -h localhost -p 8883 -t 'test/topic' -m 'Hello World' --cafile $CERT_DIR/ca.crt"
    echo ""
    echo "To stop the broker: pkill -f 'mosquitto.*$CONFIG_DIR/mosquitto.conf'"
else
    echo -e "${RED}Failed to start MQTT broker. Check the logs at $LOG_DIR/mosquitto.log${NC}"
    exit 1
fi

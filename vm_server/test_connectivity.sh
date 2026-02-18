#!/bin/bash

# Test connectivity to VM MQTT broker
# Usage: ./test_connectivity.sh [VM_IP] [PORT]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get VM IP from config or use provided argument
if [ -n "$1" ]; then
    VM_IP="$1"
else
    # Try to get from config.env
    if [ -f "config.env" ]; then
        VM_IP=$(grep -E "^MQTT_BROKER=" config.env 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
    fi
    
    # If still empty, prompt user
    if [ -z "$VM_IP" ]; then
        echo -e "${YELLOW}VM IP not found in config.env${NC}"
        read -p "Enter VM IP address: " VM_IP
    fi
fi

# Get port from argument or use default NEMO port
PORT="${2:-1886}"

echo "=========================================="
echo "MQTT Connectivity Test"
echo "=========================================="
echo "VM IP: $VM_IP"
echo "Port: $PORT"
echo ""

# Test 1: Ping test
echo -e "${YELLOW}[1/4] Testing ICMP ping...${NC}"
if ping -c 3 -W 2 "$VM_IP" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Ping successful${NC}"
else
    echo -e "${RED}✗ Ping failed (this is OK if ICMP is disabled)${NC}"
fi
echo ""

# Test 2: Port connectivity test using nc (netcat) or telnet
echo -e "${YELLOW}[2/4] Testing TCP port connectivity...${NC}"
if command -v nc >/dev/null 2>&1; then
    # Using netcat
    if nc -z -w 3 "$VM_IP" "$PORT" 2>/dev/null; then
        echo -e "${GREEN}✓ Port $PORT is open and accepting connections${NC}"
        PORT_OPEN=true
    else
        echo -e "${RED}✗ Port $PORT is not accessible (connection refused or timeout)${NC}"
        PORT_OPEN=false
    fi
elif command -v telnet >/dev/null 2>&1; then
    # Using telnet (timeout after 3 seconds)
    if timeout 3 telnet "$VM_IP" "$PORT" </dev/null 2>&1 | grep -q "Connected"; then
        echo -e "${GREEN}✓ Port $PORT is open and accepting connections${NC}"
        PORT_OPEN=true
    else
        echo -e "${RED}✗ Port $PORT is not accessible (connection refused or timeout)${NC}"
        PORT_OPEN=false
    fi
else
    echo -e "${YELLOW}⚠ Neither 'nc' nor 'telnet' found. Skipping port test.${NC}"
    PORT_OPEN=false
fi
echo ""

# Test 3: MQTT connection test (if mosquitto clients are available)
echo -e "${YELLOW}[3/4] Testing MQTT protocol connection...${NC}"
if command -v mosquitto_pub >/dev/null 2>&1; then
    TEST_TOPIC="nemo/test/connectivity_$(date +%s)"
    if timeout 5 mosquitto_pub -h "$VM_IP" -p "$PORT" -t "$TEST_TOPIC" -m "test" -q 1 2>/dev/null; then
        echo -e "${GREEN}✓ MQTT connection successful${NC}"
        MQTT_CONNECTED=true
    else
        echo -e "${RED}✗ MQTT connection failed${NC}"
        MQTT_CONNECTED=false
    fi
else
    echo -e "${YELLOW}⚠ mosquitto_pub not found. Install mosquitto-clients to test MQTT protocol.${NC}"
    MQTT_CONNECTED=false
fi
echo ""

# Test 4: Check if port is listening on VM (if we can SSH in)
echo -e "${YELLOW}[4/4] Summary and recommendations...${NC}"
echo ""

if [ "$PORT_OPEN" = true ] && [ "$MQTT_CONNECTED" = true ]; then
    echo -e "${GREEN}✓✓✓ All tests passed! MQTT broker is accessible.${NC}"
    exit 0
elif [ "$PORT_OPEN" = true ] && [ "$MQTT_CONNECTED" = false ]; then
    echo -e "${YELLOW}⚠ Port is open but MQTT connection failed.${NC}"
    echo "  - Check if Mosquitto is running on the VM"
    echo "  - Verify Mosquitto is listening on 0.0.0.0:$PORT"
    echo "  - Check Mosquitto logs: tail -f mqtt/log/mosquitto.log"
    exit 1
elif [ "$PORT_OPEN" = false ]; then
    echo -e "${RED}✗ Port $PORT is not accessible.${NC}"
    echo ""
    echo "Common causes:"
    echo "  1. Firewall blocking port $PORT"
    echo "  2. Mosquitto not running or not listening on 0.0.0.0"
    echo "  3. Network routing issues"
    echo ""
    echo "Troubleshooting steps:"
    echo "  On VM:"
    echo "    - Check if Mosquitto is running: ps aux | grep mosquitto"
    echo "    - Check if port is listening: lsof -i :$PORT"
    echo "    - Check firewall: sudo ufw status (Linux) or System Preferences > Security > Firewall (macOS)"
    echo "    - Check Mosquitto config binds to 0.0.0.0: grep 'listener.*$PORT' mqtt/config/mosquitto.conf"
    echo ""
    echo "  On this machine:"
    echo "    - Verify network connectivity: ping $VM_IP"
    echo "    - Check if you're on the same network/subnet"
    exit 1
else
    echo -e "${YELLOW}⚠ Could not complete all tests.${NC}"
    exit 1
fi

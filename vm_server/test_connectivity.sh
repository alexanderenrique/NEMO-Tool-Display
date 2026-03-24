#!/bin/bash

# Test connectivity to VM MQTT broker (TCP + optional mosquitto_pub).
# Usage: ./test_connectivity.sh [VM_IP] [PORT]
# With no args, reads MQTT_BROKER and MQTT_PORT from vm_server/config.env next to this script.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_ENV="${SCRIPT_DIR}/config.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

_get_kv() {
    local key="$1"
    local file="$2"
    [ -f "$file" ] || return 1
    grep -E "^${key}=" "$file" 2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

# Optional MQTT auth from config (for brokers with allow_anonymous false)
MQTT_USER=""
MQTT_PASS=""
if [ -f "$CONFIG_ENV" ]; then
    MQTT_USER="$(_get_kv MQTT_USERNAME "$CONFIG_ENV" || true)"
    MQTT_PASS="$(_get_kv MQTT_PASSWORD "$CONFIG_ENV" || true)"
fi

# Get VM IP from config or use provided argument
if [ -n "$1" ]; then
    VM_IP="$1"
else
    if [ -f "$CONFIG_ENV" ]; then
        VM_IP="$(_get_kv MQTT_BROKER "$CONFIG_ENV" || true)"
    fi

    if [ -z "$VM_IP" ]; then
        echo -e "${YELLOW}MQTT_BROKER not found in ${CONFIG_ENV}${NC}"
        read -r -p "Enter broker host or VM IP address: " VM_IP
    fi
fi

# Get port from argument or from config (NEMO port), default 1886
if [ -n "$2" ]; then
    PORT="$2"
elif [ -f "$CONFIG_ENV" ]; then
    PORT="$(_get_kv MQTT_PORT "$CONFIG_ENV" || true)"
    PORT="${PORT:-1886}"
else
    PORT="1886"
fi

ESP32_PORT=""
if [ -f "$CONFIG_ENV" ]; then
    ESP32_PORT="$(_get_kv MQTT_PORT_ESP32 "$CONFIG_ENV" || true)"
fi

echo "=========================================="
echo "MQTT Connectivity Test"
echo "=========================================="
echo "Broker host: $VM_IP"
echo "NEMO port: $PORT"
if [ -n "$ESP32_PORT" ] && [ "$ESP32_PORT" != "$PORT" ]; then
    echo "ESP32 port (from config): $ESP32_PORT"
fi
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
    # Use QoS 0 so we don't wait for PUBACK; more reliable for connectivity check
    # timeout is not available on macOS; use it only when present (e.g. Linux)
    if command -v timeout >/dev/null 2>&1; then
        MQTT_CMD="timeout 10 mosquitto_pub"
    else
        MQTT_CMD="mosquitto_pub"
    fi
    MQTT_AUTH=()
    if [ -n "$MQTT_USER" ]; then
        MQTT_AUTH=(-u "$MQTT_USER" -P "$MQTT_PASS")
    fi
    if $MQTT_CMD -h "$VM_IP" -p "$PORT" "${MQTT_AUTH[@]}" -t "$TEST_TOPIC" -m "test" -q 0; then
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

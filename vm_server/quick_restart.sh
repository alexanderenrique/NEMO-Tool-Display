#!/bin/bash

# NEMO Tool Display - Quick Restart Script
# Fast restart for development - stops all processes and restarts services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MQTT_CONFIG_DIR="$SCRIPT_DIR/mqtt/config"
MQTT_DATA_DIR="$SCRIPT_DIR/mqtt/data"
MQTT_LOG_DIR="$SCRIPT_DIR/mqtt/log"
CONFIG_FILE="$MQTT_CONFIG_DIR/mosquitto.conf"

# Load configuration from config.env
if [ -f "$SCRIPT_DIR/config.env" ]; then
    source "$SCRIPT_DIR/config.env"
else
    echo "Warning: config.env not found, using defaults"
fi

# Set defaults if not defined in config.env
MQTT_BROKER=${MQTT_BROKER:-"localhost"}
MQTT_PORT_ESP32=${MQTT_PORT_ESP32:-"1883"}
MQTT_PORT=${MQTT_PORT:-"1886"}

# Function to print colored output
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to get ports from config.env
get_esp32_port() {
    echo "${MQTT_PORT_ESP32:-1883}"
}

get_nemo_port() {
    echo "$MQTT_PORT"  # NEMO port from config.env
}

# Get all MQTT ports from config (space-separated for loops)
get_mqtt_ports() {
    echo "$(get_esp32_port) $(get_nemo_port)"
}

# Ensure MQTT directories and files have correct permissions for the user running Mosquitto
ensure_mqtt_permissions() {
    mkdir -p "$MQTT_CONFIG_DIR" "$MQTT_DATA_DIR" "$MQTT_LOG_DIR"
    if [ -n "${SUDO_UID:-}" ] && [ -n "${SUDO_GID:-}" ]; then
        chown -R "$SUDO_UID:$SUDO_GID" "$MQTT_CONFIG_DIR" "$MQTT_DATA_DIR" "$MQTT_LOG_DIR" 2>/dev/null || true
    fi
    chmod 755 "$MQTT_CONFIG_DIR" "$MQTT_LOG_DIR" 2>/dev/null || true
    chmod 700 "$MQTT_DATA_DIR" 2>/dev/null || true
    if [ -f "$MQTT_CONFIG_DIR/passwd" ]; then
        chmod 600 "$MQTT_CONFIG_DIR/passwd" 2>/dev/null || true
        [ -n "${SUDO_UID:-}" ] && [ -n "${SUDO_GID:-}" ] && chown "$SUDO_UID:$SUDO_GID" "$MQTT_CONFIG_DIR/passwd" 2>/dev/null || true
    fi
    touch "$MQTT_LOG_DIR/mosquitto.log" 2>/dev/null || true
    chmod 644 "$MQTT_LOG_DIR/mosquitto.log" 2>/dev/null || true
    [ -n "${SUDO_UID:-}" ] && [ -n "${SUDO_GID:-}" ] && chown "$SUDO_UID:$SUDO_GID" "$MQTT_LOG_DIR/mosquitto.log" 2>/dev/null || true
    if [ -f "$MQTT_DATA_DIR/mosquitto.db" ]; then
        chmod 600 "$MQTT_DATA_DIR/mosquitto.db" 2>/dev/null || true
    fi
}

# Kill any process bound to a given port; use sudo if needed.
kill_port() {
    local port="$1"
    if lsof -ti :"$port" >/dev/null 2>&1; then
        lsof -ti :"$port" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
    if lsof -ti :"$port" >/dev/null 2>&1; then
        sudo lsof -ti :"$port" | xargs sudo kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Phase 1: Close all MQTT ports from config and kill every process using them.
# Run this first so the broker can bind to localhost later.
close_mqtt_ports_and_kill_connections() {
    local ports esp32_port nemo_port
    esp32_port=$(get_esp32_port)
    nemo_port=$(get_nemo_port)
    ports="$esp32_port $nemo_port"
    print_info "Closing MQTT ports from config: $esp32_port, $nemo_port"
    # Kill processes by port (listeners and connections)
    for port in $ports; do
        kill_port "$port"
    done
    # Kill broker by name so we don't leave a daemon
    pkill -f "mosquitto.*mqtt/config/mosquitto.conf" 2>/dev/null || true
    pkill mosquitto 2>/dev/null || true
    pkill -9 mosquitto 2>/dev/null || true
    if systemctl is-active --quiet mosquitto 2>/dev/null; then
        sudo systemctl stop mosquitto 2>/dev/null || true
    fi
    # Kill NEMO / Python services that use MQTT
    pkill -f "python.*main\.py" 2>/dev/null || true
    pkill -f "python.*manage\.py" 2>/dev/null || true
    pkill -f "python.*nemo" 2>/dev/null || true
    pkill -f "mosquitto_sub" 2>/dev/null || true
    # Ensure ports are really free (second pass)
    for port in $ports; do
        kill_port "$port"
    done
    sleep 2
    print_success "MQTT ports closed and connections killed"
}

# Wait for a port to be listening (with timeout). Returns 0 if ready, 1 if timeout.
# Passive check only: see if something is bound to the port on this host (no outbound connect).
wait_for_port() {
    local port="$1"
    local timeout="${2:-20}"
    local i
    for (( i = 0; i < timeout; i++ )); do
        if lsof -i :"$port" >/dev/null 2>&1; then
            return 0
        fi
        # Linux fallback: ss shows listening ports without needing lsof
        if command -v ss >/dev/null 2>&1 && ss -tln 2>/dev/null | grep -q ":${port} "; then
            return 0
        fi
        sleep 1
    done
    return 1
}

# Function to kill all NEMO processes
kill_all_processes() {
    print_info "Stopping all NEMO-related processes..."
    close_mqtt_ports_and_kill_connections
}

# Function to start services
start_services() {
    local esp32_port nemo_port
    esp32_port=$(get_esp32_port)
    nemo_port=$(get_nemo_port)

    # One more pass so nothing bound to ports between phase 1 and 2
    print_info "Ensuring MQTT ports $esp32_port, $nemo_port are free..."
    for port in $esp32_port $nemo_port; do
        kill_port "$port"
    done
    sleep 1

    # Ensure MQTT dirs and files have correct permissions so Mosquitto can read passwd and write log
    ensure_mqtt_permissions

    # Start MQTT broker (passive: binds to localhost on config ports)
    print_info "Starting MQTT broker on localhost:$esp32_port, localhost:$nemo_port..."
    echo "=== quick_restart.sh $(date) ===" >> "$MQTT_LOG_DIR/mosquitto.log" 2>/dev/null || true
    mosquitto -c "$CONFIG_FILE" -d

    if ! wait_for_port "$nemo_port" 15; then
        print_error "MQTT broker did not start (port $nemo_port not listening after 15s)"
        if [ -f "$MQTT_LOG_DIR/mosquitto.log" ]; then
            print_info "Last lines of mosquitto.log (from this run):"
            tail -n 25 "$MQTT_LOG_DIR/mosquitto.log" | sed 's/^/  /'
        fi
        print_info "Attempting to start broker in foreground to capture error:"
        timeout 3 mosquitto -c "$CONFIG_FILE" 2>&1 | sed 's/^/  /' || true
        return 1
    fi
    print_success "MQTT broker listening on localhost:$esp32_port, localhost:$nemo_port"

    # Start NEMO server (connects to localhost / MQTT_BROKER)
    print_info "Starting NEMO server..."
    source venv/bin/activate
    python3 main.py &
    sleep 3

    print_success "Services started"
}

# Function to show status
show_status() {
    print_header "System Status"
    
    # Check processes
    if pgrep -f "mosquitto.*mqtt/config/mosquitto.conf" >/dev/null; then
        print_success "MQTT broker: Running"
    else
        print_error "MQTT broker: Not running"
    fi
    
    if pgrep -f "python.*main\.py" >/dev/null; then
        print_success "NEMO server: Running"
    else
        print_error "NEMO server: Not running"
    fi
    
    # Check ports
    esp32_port=$(get_esp32_port)
    nemo_port=$(get_nemo_port)
    
    for port in $esp32_port $nemo_port; do
        if lsof -i :$port >/dev/null 2>&1; then
            print_success "Port $port: Listening"
        else
            print_error "Port $port: Not listening"
        fi
    done
    
}

# Main execution
main() {
    print_header "NEMO Quick Restart"
    cd "$SCRIPT_DIR"

    print_info "Configuration loaded from config.env:"
    print_info "  MQTT_BROKER: $MQTT_BROKER"
    print_info "  MQTT_PORT_ESP32: $MQTT_PORT_ESP32, MQTT_PORT (NEMO): $MQTT_PORT"
    echo ""

    # Phase 1: Close all MQTT ports from config and kill connections
    kill_all_processes

    # Phase 2: Start broker on those localhost ports, then NEMO
    if ! start_services; then
        show_status
        print_error "Could not start services. Check mosquitto log above."
        exit 1
    fi

    show_status
    print_success "Quick restart completed!"
    print_info "Monitor: python3 mqtt_monitor.py"
    print_info "Test: python3 test_system.py"
}

# Run main function
main "$@"
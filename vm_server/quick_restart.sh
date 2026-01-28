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
CONFIG_FILE="$MQTT_CONFIG_DIR/mosquitto.conf"

# Load configuration from config.env
if [ -f "$SCRIPT_DIR/config.env" ]; then
    source "$SCRIPT_DIR/config.env"
else
    echo "Warning: config.env not found, using defaults"
fi

# Set defaults if not defined in config.env
MQTT_BROKER=${MQTT_BROKER:-"localhost"}
MQTT_PORT=${MQTT_PORT:-"1886"}
MQTT_USE_SSL=${MQTT_USE_SSL:-"False"}

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
    echo "1883"  # ESP32 port is always 1883
}

get_nemo_port() {
    echo "$MQTT_PORT"  # NEMO port from config.env
}

# Function to check if SSL is enabled
is_ssl_enabled() {
    if [[ "$MQTT_USE_SSL" =~ ^(true|True|TRUE|1|yes|Yes|YES|on|On|ON)$ ]]; then
        return 0
    else
        return 1
    fi
}

# Function to kill all NEMO processes
kill_all_processes() {
    print_info "Stopping all NEMO-related processes..."
    pkill -f "python.*main\.py" 2>/dev/null || true
    pkill -f "python.*manage\.py" 2>/dev/null || true
    pkill -f "python.*nemo" 2>/dev/null || true
    pkill -f "mosquitto.*mqtt/config/mosquitto.conf" 2>/dev/null || true
    pkill -f "mosquitto_sub" 2>/dev/null || true
    
    # Clear ports
    esp32_port=$(get_esp32_port)
    nemo_port=$(get_nemo_port)
    
    # Build port list based on configuration
    ports_to_clear="$esp32_port $nemo_port 9001"
    if is_ssl_enabled; then
        ports_to_clear="$ports_to_clear 8883"
    fi
    
    for port in $ports_to_clear; do
        if lsof -ti :$port >/dev/null 2>&1; then
            lsof -ti :$port | xargs kill -9 2>/dev/null || true
        fi
    done
    
    sleep 2
    print_success "All processes stopped"
}

# Function to start services
start_services() {
    # Start MQTT broker
    print_info "Starting MQTT broker..."
    mosquitto -c "$CONFIG_FILE" -d
    sleep 3
    
    # Start NEMO server
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
    
    # Check SSL port if SSL is enabled and certificates exist
    if is_ssl_enabled && [ -f "$SCRIPT_DIR/mqtt/certs/ca.crt" ]; then
        if lsof -i :8883 >/dev/null 2>&1; then
            print_success "Port 8883 (SSL): Listening"
        else
            print_error "Port 8883 (SSL): Not listening"
        fi
    elif is_ssl_enabled && [ ! -f "$SCRIPT_DIR/mqtt/certs/ca.crt" ]; then
        print_info "Port 8883 (SSL): SSL enabled but no certificates found"
    else
        print_info "Port 8883 (SSL): SSL disabled in config"
    fi
}

# Main execution
main() {
    print_header "NEMO Quick Restart"
    
    # Change to script directory
    cd "$SCRIPT_DIR"
    
    # Display configuration
    print_info "Configuration loaded from config.env:"
    print_info "  MQTT_BROKER: $MQTT_BROKER"
    print_info "  MQTT_PORT: $MQTT_PORT"
    print_info "  MQTT_USE_SSL: $MQTT_USE_SSL"
    if is_ssl_enabled; then
        if [ -f "$SCRIPT_DIR/mqtt/certs/ca.crt" ]; then
            print_info "  SSL Certificates: Found"
        else
            print_warning "  SSL Certificates: Missing (SSL enabled but no certs)"
        fi
    else
        print_info "  SSL Certificates: Not needed (SSL disabled)"
    fi
    echo ""
    
    # Kill all processes
    kill_all_processes
    
    # Start services
    start_services
    
    # Show status
    show_status
    
    print_success "Quick restart completed!"
    print_info "Monitor: python3 mqtt_monitor.py"
    print_info "Test: python3 test_system.py"
}

# Run main function
main "$@"
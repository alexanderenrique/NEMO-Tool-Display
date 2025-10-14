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

# Function to get ports from centralized config
get_esp32_port() {
    python3 -c "from config_parser import get_esp32_port; print(get_esp32_port())" 2>/dev/null || echo "1883"
}

get_nemo_port() {
    python3 -c "from config_parser import get_nemo_port; print(get_nemo_port())" 2>/dev/null || echo "1886"
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
    
    for port in $esp32_port $nemo_port 8883 9001; do
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
}

# Main execution
main() {
    print_header "NEMO Quick Restart"
    
    # Change to script directory
    cd "$SCRIPT_DIR"
    
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
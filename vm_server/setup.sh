#!/bin/bash

# NEMO Tool Display - Setup Script
# Consolidated setup script that handles installation, configuration, and startup

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

# Function to print colored output
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists apt-get; then
            echo "ubuntu"
        elif command_exists yum; then
            echo "centos"
        elif command_exists dnf; then
            echo "fedora"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

# Function to install Mosquitto
install_mosquitto() {
    local os=$(detect_os)
    
    print_header "Installing Mosquitto MQTT Broker"
    
    if command_exists mosquitto; then
        print_success "Mosquitto is already installed"
        mosquitto --version
        return 0
    fi
    
    print_info "Installing Mosquitto for $os..."
    
    case $os in
        "ubuntu")
            sudo apt-get update
            sudo apt-get install -y mosquitto mosquitto-clients
            sudo systemctl enable mosquitto
            ;;
        "centos")
            sudo yum install -y epel-release
            sudo yum install -y mosquitto mosquitto-clients
            sudo systemctl enable mosquitto
            ;;
        "fedora")
            sudo dnf install -y mosquitto mosquitto-clients
            sudo systemctl enable mosquitto
            ;;
        "macos")
            if command_exists brew; then
                brew install mosquitto
            else
                print_error "Homebrew not found. Please install Homebrew first:"
                echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
            ;;
        *)
            print_error "Unsupported operating system: $os"
            echo "Please install Mosquitto manually:"
            echo "  - Ubuntu/Debian: sudo apt-get install mosquitto mosquitto-clients"
            echo "  - CentOS/RHEL: sudo yum install mosquitto mosquitto-clients"
            echo "  - macOS: brew install mosquitto"
            exit 1
            ;;
    esac
    
    if command_exists mosquitto; then
        print_success "Mosquitto installed successfully"
        mosquitto --version
    else
        print_error "Failed to install Mosquitto"
        exit 1
    fi
}

# Function to stop existing processes
stop_existing_processes() {
    print_header "Stopping Existing Processes"
    
    # Stop NEMO server processes
    if pgrep -f "python.*main\.py" >/dev/null 2>&1; then
        print_info "Stopping existing NEMO server processes..."
        pkill -f "python.*main\.py" 2>/dev/null || true
    fi
    
    # Stop MQTT broker
    if pgrep -f "mosquitto.*mqtt/config/mosquitto.conf" >/dev/null 2>&1; then
        print_info "Stopping existing MQTT broker..."
        pkill -f "mosquitto.*mqtt/config/mosquitto.conf" 2>/dev/null || true
    fi
    
    # Clean up ports
    for port in 1883 1886 8883 9001; do
        if lsof -ti :$port >/dev/null 2>&1; then
            print_info "Clearing port $port..."
            lsof -ti :$port | xargs kill -9 2>/dev/null || true
        fi
    done
    
    sleep 2
    print_success "Existing processes stopped"
}

# Function to setup Python environment
setup_python_environment() {
    print_header "Setting up Python Environment"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    print_info "Installing Python dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
    
    print_success "Python environment ready"
}

# Function to create Mosquitto configuration
create_mosquitto_config() {
    print_header "Creating Mosquitto Configuration"
    
    # Create necessary directories
    mkdir -p "$MQTT_CONFIG_DIR" "$MQTT_DATA_DIR" "$MQTT_LOG_DIR"
    
    # Get ports from centralized config
    ESP32_PORT=$(python3 -c "from config_parser import get_esp32_port; print(get_esp32_port())" 2>/dev/null || echo "1883")
    NEMO_PORT=$(python3 -c "from config_parser import get_nemo_port; print(get_nemo_port())" 2>/dev/null || echo "1886")
    
    # Create Mosquitto configuration
    cat > "$CONFIG_FILE" << EOF
# Mosquitto MQTT Broker Configuration for NEMO Tool Display
# Auto-generated by setup.sh

# General settings
persistence true
persistence_location $MQTT_DATA_DIR/
log_dest file $MQTT_LOG_DIR/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information

# Network settings - ESP32 displays
listener $ESP32_PORT
protocol mqtt
allow_anonymous true

# Network settings - NEMO backend
listener $NEMO_PORT
protocol mqtt
allow_anonymous true

# WebSocket support (optional)
listener 9001
protocol websockets
allow_anonymous true

# Connection settings
max_connections 100
max_inflight_messages 20
max_queued_messages 100

# Message settings
max_packet_size 268435456
max_topic_alias 10
EOF

    print_success "Mosquitto configuration created: $CONFIG_FILE"
    print_info "ESP32 port: $ESP32_PORT, NEMO port: $NEMO_PORT"
}

# Function to start services
start_services() {
    print_header "Starting Services"
    
    # Start MQTT broker
    print_info "Starting MQTT broker..."
    mosquitto -c "$CONFIG_FILE" -d
    sleep 3
    
    # Verify MQTT broker is running
    if pgrep -f "mosquitto.*mqtt/config/mosquitto.conf" >/dev/null; then
        print_success "MQTT broker started successfully"
    else
        print_error "Failed to start MQTT broker"
        return 1
    fi
    
    # Start NEMO server
    print_info "Starting NEMO server..."
    source venv/bin/activate
    python3 main.py &
    NEMO_PID=$!
    sleep 3
    
    # Verify NEMO server is running
    if kill -0 $NEMO_PID 2>/dev/null; then
        print_success "NEMO server started successfully (PID: $NEMO_PID)"
    else
        print_error "Failed to start NEMO server"
        return 1
    fi
}

# Function to show status
show_status() {
    print_header "System Status"
    
    # Check MQTT broker
    if pgrep -f "mosquitto.*mqtt/config/mosquitto.conf" >/dev/null; then
        print_success "MQTT broker: Running"
    else
        print_error "MQTT broker: Not running"
    fi
    
    # Check NEMO server
    if pgrep -f "python.*main\.py" >/dev/null; then
        print_success "NEMO server: Running"
    else
        print_error "NEMO server: Not running"
    fi
    
    # Check ports
    for port in 1883 1886; do
        if lsof -i :$port >/dev/null 2>&1; then
            print_success "Port $port: Listening"
        else
            print_error "Port $port: Not listening"
        fi
    done
    
    echo ""
    print_info "Quick commands:"
    echo "  - Restart: ./quick_restart.sh"
    echo "  - Monitor: python3 mqtt_monitor.py"
    echo "  - Logs: tail -f nemo_server.log"
}

# Main execution
main() {
    print_header "NEMO Tool Display Setup"
    echo "This script will:"
    echo "  - Install Mosquitto MQTT broker"
    echo "  - Set up Python environment"
    echo "  - Configure MQTT broker"
    echo "  - Start all services"
    echo ""
    
    # Change to script directory
    cd "$SCRIPT_DIR"
    
    # Install Mosquitto
    install_mosquitto
    
    # Stop existing processes
    stop_existing_processes
    
    # Setup Python environment
    setup_python_environment
    
    # Create Mosquitto configuration
    create_mosquitto_config
    
    # Start services
    start_services
    
    # Show status
    show_status
    
    print_success "NEMO Tool Display setup completed successfully!"
}

# Run main function
main "$@"

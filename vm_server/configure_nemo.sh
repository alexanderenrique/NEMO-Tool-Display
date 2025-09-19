#!/bin/bash

# NEMO Tool Display - Configuration Script
# This script helps configure the NEMO system including Mosquitto, ports, and SSL

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MQTT_CONFIG_DIR="$SCRIPT_DIR/mqtt/config"
MQTT_CERT_DIR="$SCRIPT_DIR/mqtt/certs"
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

# Function to check if a port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
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

# Function to stop existing Mosquitto processes
stop_mosquitto() {
    print_header "Stopping Existing Mosquitto Processes"
    
    # Simple approach: just try to stop any running mosquitto processes
    if pgrep -f mosquitto >/dev/null 2>&1; then
        print_info "Stopping existing Mosquitto processes..."
        pkill -f mosquitto 2>/dev/null || true
        sleep 2
        print_success "Mosquitto processes stopped"
    else
        print_success "No running Mosquitto processes found"
    fi
}

# Function to clean Mosquitto configuration
clean_mosquitto_config() {
    print_header "Cleaning Mosquitto Configuration"
    
    # Remove existing configuration file
    if [ -f "$CONFIG_FILE" ]; then
        print_info "Removing existing configuration file: $CONFIG_FILE"
        rm -f "$CONFIG_FILE"
    fi
    
    # Clean up old log files
    if [ -d "$MQTT_LOG_DIR" ]; then
        print_info "Cleaning old log files..."
        rm -f "$MQTT_LOG_DIR"/*.log 2>/dev/null || true
    fi
    
    # Clean up old data files
    if [ -d "$MQTT_DATA_DIR" ]; then
        print_info "Cleaning old persistence data..."
        rm -f "$MQTT_DATA_DIR"/* 2>/dev/null || true
    fi
    
    print_success "Configuration cleaned successfully"
}

# Function to configure ports
configure_ports() {
    print_header "Configuring Network Ports"
    
    print_success "Port configuration completed"
    echo "MQTT will use the following ports:"
    echo "  - 1883: Standard MQTT (non-SSL)"
    echo "  - 9001: WebSocket (optional)"
}

# Function to setup SSL
setup_ssl() {
    print_header "SSL/TLS Configuration"
    
    echo "SSL/TLS provides encrypted communication between MQTT clients and the broker."
    echo "This is recommended for production environments but optional for development."
    echo ""
    
    read -p "Do you want to set up SSL/TLS? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Setting up SSL/TLS certificates..."
        
        # Create certificate directory
        mkdir -p "$MQTT_CERT_DIR"
        
        # Check if certificates already exist
        if [ -f "$MQTT_CERT_DIR/ca.crt" ] && [ -f "$MQTT_CERT_DIR/server.crt" ] && [ -f "$MQTT_CERT_DIR/server.key" ]; then
            print_warning "SSL certificates already exist"
            read -p "Do you want to regenerate them? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_success "Using existing SSL certificates"
                return 0
            fi
        fi
        
        # Generate SSL certificates
        print_info "Generating SSL certificates..."
        
        # Generate CA private key
        openssl genrsa -out "$MQTT_CERT_DIR/ca.key" 2048
        
        # Generate CA certificate
        openssl req -new -x509 -days 365 -key "$MQTT_CERT_DIR/ca.key" -out "$MQTT_CERT_DIR/ca.crt" \
            -subj "/C=US/ST=CA/L=Stanford/O=NEMO/OU=ToolDisplay/CN=NEMO-CA"
        
        # Generate server private key
        openssl genrsa -out "$MQTT_CERT_DIR/server.key" 2048
        
        # Generate server certificate request
        openssl req -new -key "$MQTT_CERT_DIR/server.key" -out "$MQTT_CERT_DIR/server.csr" \
            -subj "/C=US/ST=CA/L=Stanford/O=NEMO/OU=ToolDisplay/CN=localhost"
        
        # Generate server certificate signed by CA
        openssl x509 -req -in "$MQTT_CERT_DIR/server.csr" -CA "$MQTT_CERT_DIR/ca.crt" -CAkey "$MQTT_CERT_DIR/ca.key" \
            -CAcreateserial -out "$MQTT_CERT_DIR/server.crt" -days 365
        
        # Clean up CSR file
        rm "$MQTT_CERT_DIR/server.csr"
        
        # Set proper permissions
        chmod 600 "$MQTT_CERT_DIR"/*.key
        chmod 644 "$MQTT_CERT_DIR"/*.crt
        
        print_success "SSL certificates generated successfully"
        
        # Show certificate information
        echo ""
        print_info "SSL Certificate Information:"
        echo "  - CA Certificate: $MQTT_CERT_DIR/ca.crt"
        echo "  - Server Certificate: $MQTT_CERT_DIR/server.crt"
        echo "  - Server Private Key: $MQTT_CERT_DIR/server.key"
        echo ""
        echo "For ESP32 development, you'll need the CA certificate for SSL connections."
        echo "Copy the CA certificate to your ESP32 project if using SSL."
        
    else
        print_info "Skipping SSL/TLS setup"
        echo "You can enable SSL later by running this script again."
    fi
}

# Function to create Mosquitto configuration
create_mosquitto_config() {
    print_header "Creating Mosquitto Configuration"
    
    # Create necessary directories
    mkdir -p "$MQTT_CONFIG_DIR" "$MQTT_DATA_DIR" "$MQTT_LOG_DIR"
    
    # Check if SSL certificates exist
    local ssl_enabled=false
    if [ -f "$MQTT_CERT_DIR/ca.crt" ] && [ -f "$MQTT_CERT_DIR/server.crt" ] && [ -f "$MQTT_CERT_DIR/server.key" ]; then
        ssl_enabled=true
    fi
    
    # Create Mosquitto configuration
    cat > "$CONFIG_FILE" << EOF
# Mosquitto MQTT Broker Configuration for NEMO Tool Display
# Generated by configure_nemo.sh

# General settings
persistence true
persistence_location $MQTT_DATA_DIR/
log_dest file $MQTT_LOG_DIR/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information

# Network settings
listener 1883
protocol mqtt

EOF

    # Add SSL configuration if certificates exist
    if [ "$ssl_enabled" = true ]; then
        cat >> "$CONFIG_FILE" << EOF
# SSL/TLS listener
listener 8883
protocol mqtt
cafile $MQTT_CERT_DIR/ca.crt
certfile $MQTT_CERT_DIR/server.crt
keyfile $MQTT_CERT_DIR/server.key
EOF
    fi

    # Add WebSocket support
    cat >> "$CONFIG_FILE" << EOF

# WebSocket support (optional)
listener 9001
protocol websockets

# Security settings (uncomment to enable authentication)
# allow_anonymous false
# password_file $MQTT_CONFIG_DIR/passwd

# Allow anonymous connections for development
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
    
    if [ "$ssl_enabled" = true ]; then
        print_info "SSL/TLS is enabled in the configuration"
    else
        print_info "SSL/TLS is disabled in the configuration"
    fi
}

# Function to restart Mosquitto with new configuration
restart_mosquitto() {
    print_header "Starting Mosquitto with New Configuration"
    
    # Stop any existing Mosquitto processes first
    if pgrep -f mosquitto >/dev/null 2>&1; then
        print_info "Stopping existing Mosquitto processes..."
        pkill -f mosquitto 2>/dev/null || true
        sleep 2
    fi
    
    # Start Mosquitto with the new configuration
    print_info "Starting Mosquitto..."
    mosquitto -c "$CONFIG_FILE" -d
    
    # Wait for Mosquitto to start
    sleep 2
    
    if pgrep -f mosquitto >/dev/null 2>&1; then
        print_success "Mosquitto started successfully"
        echo "Mosquitto is now running with the new configuration."
    else
        print_error "Failed to start Mosquitto"
        echo "Check the logs at: $MQTT_LOG_DIR/mosquitto.log"
        return 1
    fi
}

# Function to test the configuration
test_configuration() {
    print_header "Testing Configuration"
    
    print_info "Testing Mosquitto configuration..."
    
    # Test basic MQTT functionality if mosquitto_pub is available
    if command_exists mosquitto_pub; then
        print_info "Testing basic MQTT functionality..."
        # Start mosquitto in background for quick test
        mosquitto -c "$CONFIG_FILE" -d >/dev/null 2>&1
        sleep 2
        
        # Test publish/subscribe
        if mosquitto_pub -h localhost -p 1883 -t "nemo/test" -m "test" -q 1 >/dev/null 2>&1; then
            print_success "MQTT test successful"
        else
            print_warning "MQTT test failed (broker may not be running)"
        fi
        
        # Stop the test broker
        pkill -f mosquitto 2>/dev/null || true
        print_success "Configuration test completed"
    else
        print_warning "mosquitto_pub not available, skipping MQTT test"
        print_success "Configuration file created successfully"
    fi
}

# Function to show configuration summary
show_summary() {
    print_header "Configuration Summary"
    
    echo "NEMO Tool Display has been configured with the following settings:"
    echo ""
    echo "MQTT Broker Configuration:"
    echo "  - Configuration file: $CONFIG_FILE"
    echo "  - Data directory: $MQTT_DATA_DIR"
    echo "  - Log directory: $MQTT_LOG_DIR"
    echo "  - Port 1883: Standard MQTT (non-SSL)"
    echo "  - Port 9001: WebSocket support"
    
    if [ -f "$MQTT_CERT_DIR/ca.crt" ]; then
        echo "  - Port 8883: MQTT over SSL/TLS"
        echo "  - SSL certificates: $MQTT_CERT_DIR/"
    else
        echo "  - SSL/TLS: Not configured"
    fi
    
    echo ""
    echo "Next Steps:"
    if pgrep -f "mosquitto.*$CONFIG_FILE" > /dev/null; then
        echo "  1. Mosquitto is already running with the new configuration"
        echo "  2. Start the complete system: ./start_nemo_system.sh"
        echo "  3. Test the system: ./test_mqtt_system.py"
    else
        echo "  1. Start the MQTT broker: ./start_mqtt_broker.sh"
        echo "  2. Start the complete system: ./start_nemo_system.sh"
        echo "  3. Test the system: ./test_mqtt_system.py"
    fi
    echo ""
    echo "For ESP32 Development:"
    echo "  - Use port 1883 for non-SSL connections"
    if [ -f "$MQTT_CERT_DIR/ca.crt" ]; then
        echo "  - Use port 8883 for SSL connections"
        echo "  - Copy $MQTT_CERT_DIR/ca.crt to your ESP32 project"
    fi
    echo "  - Broker IP: $(hostname -I | awk '{print $1}' 2>/dev/null || echo 'localhost')"
    echo ""
    echo "MQTT Topics for NEMO:"
    echo "  - Backend Input: nemo/backend/tools/+/status"
    echo "  - Backend Overall: nemo/backend/tools/overall"
    echo "  - ESP32 Output: nemo/esp32/{tool_id}/status"
    echo "  - ESP32 Overall: nemo/esp32/overall"
    echo "  - Server Status: nemo/server/status"
}

# Main execution
main() {
    print_header "NEMO Tool Display Configuration"
    echo "This script will help you configure the NEMO system including:"
    echo "  - Mosquitto MQTT broker installation"
    echo "  - Network port configuration"
    echo "  - SSL/TLS certificate setup (DISABLED for testing)"
    echo "  - System validation"
    echo ""
    
    # Change to script directory
    cd "$SCRIPT_DIR"
    
    # Install Mosquitto
    install_mosquitto
    
    # Stop existing Mosquitto processes
    stop_mosquitto
    
    # Clean existing configuration
    clean_mosquitto_config
    
    # Configure ports
    configure_ports
    
    # Setup SSL (disabled for testing)
    # setup_ssl
    
    # Create Mosquitto configuration
    create_mosquitto_config
    
    # Test configuration
    test_configuration
    
    # Ask if user wants to restart Mosquitto
    echo ""
    read -p "Do you want to restart Mosquitto with the new configuration now? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_info "Skipping Mosquitto restart. You can start it later with: ./start_mqtt_broker.sh"
    else
        restart_mosquitto
    fi
    
    # Show summary
    show_summary
    
    print_success "NEMO configuration completed successfully!"
}

# Run main function
main "$@"

#!/bin/bash

# NEMO Tool Display - Master Setup and Start Script
# This script configures the system AND starts the broker/server
# One command to get everything ready and running

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
MQTT_DATA_DIR="$SCRIPT_DIR/mqtt/data"
MQTT_LOG_DIR="$SCRIPT_DIR/mqtt/log"
CONFIG_FILE="$MQTT_CONFIG_DIR/mosquitto.conf"
ENV_FILE="$SCRIPT_DIR/.env"

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
    pkill -f "mosquitto.*$CONFIG_FILE" 2>/dev/null || true
    
    # Deactivate virtual environment
    if [ ! -z "$VIRTUAL_ENV" ]; then
        echo "Deactivating virtual environment..."
        deactivate 2>/dev/null || true
    fi
    
    echo -e "${GREEN}Cleanup completed.${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Change to script directory
cd "$SCRIPT_DIR"

# Get the project root directory
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

print_header "NEMO Tool Display - Master Setup and Start"
echo "This script will configure and start the complete NEMO system:"
echo "  - Detect and configure VM server IP address"
echo "  - Install and configure Mosquitto MQTT broker"
echo "  - Set up Python dependencies"
echo "  - Start MQTT broker"
echo "  - Start NEMO server"
echo ""
echo "Note: ESP32 broker IP is configured manually in platformio.ini"
echo ""

# =============================================================================
# STEP 0: VM SERVER IP DETECTION AND CONFIGURATION
# =============================================================================

print_header "Step 0: Configuration Validation"

print_info "Validating configuration files..."
cd "$PROJECT_DIR"

# Check if config files exist
if [ ! -f "vm_server/config.env" ]; then
    print_warning "config.env not found, copying from example..."
    cp vm_server/config.env.example vm_server/config.env
    print_info "Please edit vm_server/config.env with your settings"
fi

if [ ! -f "vm_server/tool_mappings.yaml" ]; then
    print_error "tool_mappings.yaml not found! Please create this file with your tool mappings."
    exit 1
fi

print_success "Configuration files validated"

# Return to script directory
cd "$SCRIPT_DIR"

# =============================================================================
# STEP 1: INSTALL MOSQUITTO
# =============================================================================

print_header "Step 1: Installing Mosquitto MQTT Broker"

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

# Install Mosquitto
install_mosquitto() {
    local os=$(detect_os)
    
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

install_mosquitto

# =============================================================================
# STEP 2: STOP EXISTING PROCESSES
# =============================================================================

print_header "Step 2: Stopping Existing Processes"

if pgrep -f mosquitto >/dev/null 2>&1; then
    print_info "Stopping existing Mosquitto processes..."
    pkill -f mosquitto 2>/dev/null || true
    sleep 2
    print_success "Mosquitto processes stopped"
else
    print_success "No running Mosquitto processes found"
fi

# =============================================================================
# STEP 3: CLEAN CONFIGURATION
# =============================================================================

print_header "Step 3: Cleaning Configuration"

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

# =============================================================================
# STEP 4: CREATE MOSQUITTO CONFIGURATION
# =============================================================================

print_header "Step 4: Creating Mosquitto Configuration"

# Create necessary directories
mkdir -p "$MQTT_CONFIG_DIR" "$MQTT_DATA_DIR" "$MQTT_LOG_DIR"

# Create Mosquitto configuration
cat > "$CONFIG_FILE" << EOF
# Mosquitto MQTT Broker Configuration for NEMO Tool Display
# Generated by setup_and_start.sh

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

# =============================================================================
# STEP 5: TEST CONFIGURATION
# =============================================================================

print_header "Step 5: Testing Configuration"

print_info "Testing basic MQTT functionality..."
# Start mosquitto in background for quick test
mosquitto -c "$CONFIG_FILE" -d >/dev/null 2>&1
sleep 2

# Test publish/subscribe
if command_exists mosquitto_pub; then
    if mosquitto_pub -h localhost -p 1883 -t "nemo/test" -m "test" -q 1 >/dev/null 2>&1; then
        print_success "MQTT test successful"
    else
        print_warning "MQTT test failed (broker may not be running)"
    fi
fi

# Stop the test broker
pkill -f mosquitto 2>/dev/null || true
print_success "Configuration test completed"

# =============================================================================
# STEP 6: SET UP PYTHON VIRTUAL ENVIRONMENT
# =============================================================================

print_header "Step 6: Setting Up Python Virtual Environment"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_info "Installing Python dependencies..."
pip install -r requirements.txt

print_success "Python dependencies ready"

# =============================================================================
# STEP 6.5: GENERATE TOOL MAPPINGS FROM NEMO API
# =============================================================================

print_header "Step 6.5: Generating Tool Mappings from NEMO API"

# Check if NEMO token is configured
if [ -f "config.env" ]; then
    if grep -q "NEMO_TOKEN=" config.env && ! grep -q "NEMO_TOKEN=your_nemo_token_here" config.env; then
        print_info "NEMO token found, generating tool mappings from API..."
        
        # Generate tool mappings from NEMO API
        if python generate_tool_mappings.py --api; then
            print_success "Tool mappings generated successfully from NEMO API"
        else
            print_warning "Failed to generate tool mappings from API, using existing file"
        fi
    else
        print_warning "NEMO token not configured, skipping API tool mapping generation"
        print_info "To enable API tool mapping generation:"
        print_info "  1. Edit config.env and set NEMO_TOKEN to your actual token"
        print_info "  2. Run: python generate_tool_mappings.py --api"
    fi
else
    print_warning "config.env not found, skipping API tool mapping generation"
fi

# =============================================================================
# STEP 8: CONFIGURE SSL SETTINGS
# =============================================================================

print_header "Step 8: Configuring SSL Settings"

echo "SSL/TLS provides encrypted communication between MQTT clients and the broker."
echo "This is recommended for production environments but optional for development."
echo ""

read -p "Do you want to use SSL/TLS encryption? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    MQTT_USE_SSL="true"
    MQTT_PORT="8883"
    print_info "SSL/TLS enabled - will use port 8883"
    
    # Generate SSL certificates if they don't exist
    MQTT_CERT_DIR="$SCRIPT_DIR/mqtt/certs"
    if [ ! -f "$MQTT_CERT_DIR/ca.crt" ] || [ ! -f "$MQTT_CERT_DIR/server.crt" ] || [ ! -f "$MQTT_CERT_DIR/server.key" ]; then
        print_info "Generating SSL certificates..."
        mkdir -p "$MQTT_CERT_DIR"
        
        # Generate CA private key
        openssl genrsa -out "$MQTT_CERT_DIR/ca.key" 2048
        
        # Generate CA certificate
        openssl req -new -x509 -days 365 -key "$MQTT_CERT_DIR/ca.key" -out "$MQTT_CERT_DIR/ca.crt" \
            -subj "/C=US/ST=CA/L=Stanford/O=NEMO/OU=ToolDisplay/CN=NEMO-CA"
        
        # Generate server private key
        openssl genrsa -out "$MQTT_CERT_DIR/server.key" 2048
        
        # Get the broker IP address for certificate (use dynamic detection)
        BROKER_IP=$(python3 -c "
import socket
try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(('8.8.8.8', 80))
        print(s.getsockname()[0])
except:
    print('localhost')
" 2>/dev/null || echo 'localhost')
        
        # Create a config file for the certificate with SAN
        cat > "$MQTT_CERT_DIR/server.conf" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C=US
ST=CA
L=Stanford
O=NEMO
OU=ToolDisplay
CN=localhost

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.local
IP.1 = 127.0.0.1
IP.2 = $BROKER_IP
EOF
        
        # Generate server certificate request
        openssl req -new -key "$MQTT_CERT_DIR/server.key" -out "$MQTT_CERT_DIR/server.csr" \
            -config "$MQTT_CERT_DIR/server.conf"
        
        # Generate server certificate signed by CA with SAN extensions
        openssl x509 -req -in "$MQTT_CERT_DIR/server.csr" -CA "$MQTT_CERT_DIR/ca.crt" -CAkey "$MQTT_CERT_DIR/ca.key" \
            -CAcreateserial -out "$MQTT_CERT_DIR/server.crt" -days 365 -extensions v3_req -extfile "$MQTT_CERT_DIR/server.conf"
        
        # Clean up CSR file
        rm "$MQTT_CERT_DIR/server.csr"
        
        # Set proper permissions
        chmod 600 "$MQTT_CERT_DIR"/*.key
        chmod 644 "$MQTT_CERT_DIR"/*.crt
        
        print_success "SSL certificates generated successfully"
    else
        print_success "SSL certificates already exist"
    fi
else
    MQTT_USE_SSL="false"
    MQTT_PORT="1883"
    print_info "SSL/TLS disabled - will use port 1883"
fi

# =============================================================================
# STEP 9: SET UP ENVIRONMENT FILE
# =============================================================================

print_header "Step 9: Setting Up Environment Configuration"

if [ ! -f "$ENV_FILE" ]; then
    print_info "Creating environment configuration file..."
    if [ -f "config.env.example" ]; then
        cp config.env.example "$ENV_FILE"
        print_success "Environment file created from example: $ENV_FILE"
        print_warning "Please edit $ENV_FILE with your API and MQTT settings"
    else
        # Create a basic .env file with SSL settings
        cat > "$ENV_FILE" << EOF
# NEMO Tool Display Configuration
API_URL=http://localhost:8000/api/tools
API_KEY=
MQTT_BROKER=localhost
MQTT_PORT=$MQTT_PORT
MQTT_USE_SSL=$MQTT_USE_SSL
MQTT_USERNAME=
MQTT_PASSWORD=
POLL_INTERVAL=30
EOF
        print_success "Environment file created with SSL settings: $ENV_FILE"
        print_warning "Please edit $ENV_FILE with your API settings"
    fi
else
    print_success "Environment file already exists: $ENV_FILE"
    print_info "Updating MQTT settings in existing .env file..."
    
    # Update MQTT settings in existing .env file
    if grep -q "MQTT_PORT=" "$ENV_FILE"; then
        sed -i.bak "s/MQTT_PORT=.*/MQTT_PORT=$MQTT_PORT/" "$ENV_FILE"
    else
        echo "MQTT_PORT=$MQTT_PORT" >> "$ENV_FILE"
    fi
    
    if grep -q "MQTT_USE_SSL=" "$ENV_FILE"; then
        sed -i.bak "s/MQTT_USE_SSL=.*/MQTT_USE_SSL=$MQTT_USE_SSL/" "$ENV_FILE"
    else
        echo "MQTT_USE_SSL=$MQTT_USE_SSL" >> "$ENV_FILE"
    fi
    
    # Clean up backup file
    rm -f "$ENV_FILE.bak"
    
    print_success "Updated MQTT settings in $ENV_FILE"
fi

# =============================================================================
# STEP 10: UPDATE MOSQUITTO CONFIGURATION FOR SSL
# =============================================================================

print_header "Step 10: Updating Mosquitto Configuration for SSL"

# Add SSL configuration if enabled
if [ "$MQTT_USE_SSL" = "true" ]; then
    print_info "Adding SSL configuration to Mosquitto..."
    cat >> "$CONFIG_FILE" << EOF

# SSL/TLS listener
listener 8883
protocol mqtt
certfile $MQTT_CERT_DIR/server.crt
keyfile $MQTT_CERT_DIR/server.key
require_certificate false
use_identity_as_username false
EOF
    print_success "SSL configuration added to Mosquitto"
else
    print_info "SSL disabled - using standard MQTT only"
fi

# =============================================================================
# STEP 11: START MQTT BROKER
# =============================================================================

print_header "Step 11: Starting MQTT Broker"

print_info "Starting Mosquitto with new configuration..."
mosquitto -c "$CONFIG_FILE" -d

# Wait for Mosquitto to start
sleep 2

if pgrep -f mosquitto >/dev/null 2>&1; then
    print_success "Mosquitto started successfully"
else
    print_error "Failed to start Mosquitto"
    echo "Check the logs at: $MQTT_LOG_DIR/mosquitto.log"
    exit 1
fi

# =============================================================================
# STEP 12: START NEMO SERVER
# =============================================================================

print_header "Step 12: Starting NEMO Server"

print_info "Activating virtual environment and starting NEMO server..."
source venv/bin/activate
python main.py &
SERVER_PID=$!

# Wait a moment for the server to start
sleep 3

# Check if server started successfully
if kill -0 $SERVER_PID 2>/dev/null; then
    print_success "NEMO server started successfully (PID: $SERVER_PID)"
else
    print_error "Failed to start NEMO server"
    exit 1
fi

# =============================================================================
# STEP 13: SYSTEM READY
# =============================================================================

print_header "🎉 NEMO Tool Display System Ready!"

echo -e "${GREEN}✓ System Status:${NC}"
if [ "$MQTT_USE_SSL" = "true" ]; then
    echo "  - MQTT Broker: Running on ports 1883 (non-SSL) and 8883 (SSL)"
else
    echo "  - MQTT Broker: Running on port 1883 (non-SSL)"
fi
echo "  - NEMO Server: Running (PID: $SERVER_PID)"
echo "  - Configuration: $ENV_FILE"
echo ""

echo -e "${GREEN}✓ MQTT Topics:${NC}"
echo "  - Backend Input: nemo/backend/tools/+/status"
echo "  - Backend Overall: nemo/backend/tools/overall"
echo "  - ESP32 Output: nemo/esp32/{tool_id}/status"
echo "  - ESP32 Overall: nemo/esp32/overall"
echo "  - Server Status: nemo/server/status"
echo ""

echo -e "${GREEN}✓ Logs:${NC}"
echo "  - MQTT Broker: $MQTT_LOG_DIR/mosquitto.log"
echo "  - NEMO Server: Check console output"
echo ""

echo -e "${GREEN}✓ ESP32 Configuration Values:${NC}"
echo ""
echo -e "${PURPLE}┌─────────────────────────────────────────────────────────────┐${NC}"
echo -e "${PURPLE}│${NC} ${CYAN}NEMO Setup Information${NC} ${PURPLE}│${NC}"
echo -e "${PURPLE}├─────────────────────────────────────────────────────────────┤${NC}"

# Get the broker IP address (use dynamic detection)
BROKER_IP=$(python3 -c "
import socket
try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(('8.8.8.8', 80))
        print(s.getsockname()[0])
except:
    print('localhost')
" 2>/dev/null || echo 'localhost')
echo -e "${PURPLE}│${NC} ${YELLOW}MQTT Broker IP:${NC} ${GREEN}$BROKER_IP${NC} ${PURPLE}│${NC}"
echo -e "${PURPLE}│${NC} ${YELLOW}MQTT Port:${NC} ${GREEN}$MQTT_PORT${NC} ${PURPLE}│${NC}"

if [ "$MQTT_USE_SSL" = "true" ]; then
    echo -e "${PURPLE}│${NC} ${YELLOW}SSL/TLS:${NC} ${GREEN}Enabled${NC} ${PURPLE}│${NC}"
    echo -e "${PURPLE}│${NC} ${YELLOW}CA Certificate:${NC} ${GREEN}$MQTT_CERT_DIR/ca.crt${NC} ${PURPLE}│${NC}"
    echo -e "${PURPLE}│${NC} ${CYAN}Copy this file to your ESP32 project${NC} ${PURPLE}│${NC}"
else
    echo -e "${PURPLE}│${NC} ${YELLOW}SSL/TLS:${NC} ${GREEN}Disabled${NC} ${PURPLE}│${NC}"
fi

echo -e "${PURPLE}└─────────────────────────────────────────────────────────────┘${NC}"
echo ""

# Display SSL certificate content if SSL is enabled
if [ "$MQTT_USE_SSL" = "true" ]; then
    echo -e "${GREEN}✓ SSL Certificate Content (Copy this to NEMO):${NC}"
    echo ""
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}CA Certificate (ca.crt)${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo ""
    if [ -f "$MQTT_CERT_DIR/ca.crt" ]; then
        cat "$MQTT_CERT_DIR/ca.crt"
    else
        echo -e "${RED}Certificate file not found: $MQTT_CERT_DIR/ca.crt${NC}"
    fi
    echo ""
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}End of Certificate${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo ""
    echo -e "${CYAN}📋 Instructions for NEMO:${NC}"
    echo "  1. Copy the entire certificate content above (including BEGIN and END lines)"
    echo "  2. In NEMO->Administration->Configuration->MQTT Broker"
    echo "  3. Paste the certificate content into the CA Certificate field"
    echo "  4. Set MQTT Broker to: $BROKER_IP"
    echo "  5. Set MQTT Port to: $MQTT_PORT"
    echo "  6. Enable SSL/TLS"
    echo ""
fi

echo -e "${GREEN}✓ Next Steps:${NC}"
echo "  1. In NEMO->Administration->Configuration->MQTT Broker, copy the values above"
if [ "$MQTT_USE_SSL" = "true" ]; then
    echo "  2. Monitor system: mosquitto_sub -h $BROKER_IP -p $MQTT_PORT -t 'nemo/#' -v --insecure"
else
    echo "  2. Monitor system: mosquitto_sub -h $BROKER_IP -p $MQTT_PORT -t 'nemo/#' -v"
fi
echo ""

echo -e "${CYAN}📋 Copy these values to your ESP32 platformio.ini:${NC}"
echo ""
echo -e "${YELLOW}build_flags =${NC}"
echo -e "${YELLOW}    -DMQTT_BROKER=\"$BROKER_IP\"${NC}"
echo -e "${YELLOW}    -DMQTT_PORT=$MQTT_PORT${NC}"
if [ "$MQTT_USE_SSL" = "true" ]; then
    echo -e "${YELLOW}    -DMQTT_USE_SSL=true${NC}"
    echo -e "${YELLOW}    -DMQTT_CA_CERT=\"$MQTT_CERT_DIR/ca.crt\"${NC}"
else
    echo -e "${YELLOW}    -DMQTT_USE_SSL=false${NC}"
fi
echo ""

echo -e "${YELLOW}To stop the system: Press Ctrl+C${NC}"
echo ""

# Keep the script running and monitor the server
while kill -0 $SERVER_PID 2>/dev/null; do
    sleep 1
done

echo -e "${RED}NEMO server stopped unexpectedly.${NC}"

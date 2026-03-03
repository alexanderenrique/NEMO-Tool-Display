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
    else
        print_error "Failed to install Mosquitto"
        exit 1
    fi
}

# Function to stop existing processes
stop_existing_processes() {
    print_header "Stopping Existing Processes"
    
    # Kill anything on MQTT ports first (with sudo fallback for system mosquitto)
    ESP32_PORT=$(_get_esp32_port)
    NEMO_PORT=$(_get_nemo_port)
    print_info "Clearing MQTT ports $ESP32_PORT, $NEMO_PORT..."
    for port in $ESP32_PORT $NEMO_PORT; do
        if lsof -ti :$port >/dev/null 2>&1; then
            lsof -ti :$port | xargs kill -9 2>/dev/null || true
            sleep 1
        fi
        if lsof -ti :$port >/dev/null 2>&1; then
            sudo lsof -ti :$port | xargs sudo kill -9 2>/dev/null || true
            sleep 1
        fi
    done
    pkill -f "mosquitto.*mqtt/config/mosquitto.conf" 2>/dev/null || true
    pkill mosquitto 2>/dev/null || true
    pkill -9 mosquitto 2>/dev/null || true
    if systemctl is-active --quiet mosquitto 2>/dev/null; then
        print_info "Stopping systemd Mosquitto service..."
        sudo systemctl stop mosquitto 2>/dev/null || true
    fi
    for port in $ESP32_PORT $NEMO_PORT; do
        if lsof -ti :$port >/dev/null 2>&1; then
            sudo lsof -ti :$port | xargs sudo kill -9 2>/dev/null || true
            sleep 1
        fi
    done
    sleep 2

    # Stop NEMO server processes
    if pgrep -f "python.*main\.py" >/dev/null 2>&1; then
        print_info "Stopping existing NEMO server processes..."
        pkill -f "python.*main\.py" 2>/dev/null || true
    fi
    
    sleep 1
    
    # Verify ports are free
    ports_free=true
    for port in $ESP32_PORT $NEMO_PORT; do
        if lsof -ti :$port >/dev/null 2>&1; then
            print_warning "Port $port is still in use after cleanup attempt"
            ports_free=false
        fi
    done
    
    if [ "$ports_free" = true ]; then
        print_success "Existing processes stopped and ports freed"
    else
        print_warning "Some ports may still be in use. Manual cleanup may be needed."
    fi
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

# Function to generate HMAC key and write config.env (create from example if missing)
write_config_env() {
    local config_env="$SCRIPT_DIR/config.env"
    local example="$SCRIPT_DIR/config.env.example"
    
    if [ ! -f "$config_env" ] && [ -f "$example" ]; then
        print_info "Creating config.env from config.env.example..."
        cp "$example" "$config_env"
    fi
    
    if [ -f "$config_env" ]; then
        # Prompt for ports (defaults: ESP32=1883, NEMO=1886)
        echo ""
        read -p "ESP32 MQTT port [1883]: " esp32_port_input
        esp32_port="${esp32_port_input:-1883}"
        read -p "NEMO MQTT port [1886]: " nemo_port_input
        nemo_port="${nemo_port_input:-1886}"
        _set_config_env_value "MQTT_PORT_ESP32" "$esp32_port" "$config_env"
        _set_config_env_value "MQTT_PORT" "$nemo_port" "$config_env"
        print_success "Ports set: ESP32=$esp32_port, NEMO=$nemo_port"
        # Generate HMAC key if not already set
        if ! grep -qE '^MQTT_HMAC_KEY=.+$' "$config_env" 2>/dev/null; then
            local hmac_key
            hmac_key=$(openssl rand -hex 32)
            _set_config_env_value "MQTT_HMAC_KEY" "$hmac_key" "$config_env"
            print_success "Generated MQTT_HMAC_KEY (saved to config.env)"
            echo ""
            echo -e "  ${CYAN}MQTT_HMAC_KEY=${NC}${YELLOW}$hmac_key${NC}"
            echo ""
            print_info "Share this key with your NEMO backend for authenticated MQTT (keep it secret)."
        else
            print_info "config.env: MQTT_HMAC_KEY already set"
            hmac_key=$(grep -E '^MQTT_HMAC_KEY=' "$config_env" 2>/dev/null | cut -d= -f2- | tr -d '\r')
            if [ -n "$hmac_key" ]; then
                echo ""
                echo -e "  ${CYAN}MQTT_HMAC_KEY=${NC}${YELLOW}$hmac_key${NC}"
                echo ""
            fi
        fi
        print_info "config.env: MQTT_PORT_ESP32=$esp32_port, MQTT_PORT=$nemo_port"
        _print_mqtt_config_verification
    fi
}

# Print MQTT config from config.env for verification during debugging
_print_mqtt_config_verification() {
    local config_env="$SCRIPT_DIR/config.env"
    [ ! -f "$config_env" ] && return
    echo ""
    echo "============================================================"
    echo "MQTT config (for NEMO backend verification)"
    echo "============================================================"
    grep -E '^MQTT_BROKER=' "$config_env" 2>/dev/null | sed 's/^/  /' || echo "  MQTT_BROKER=(not set)"
    grep -E '^MQTT_PORT='   "$config_env" 2>/dev/null | sed 's/^/  /' || echo "  MQTT_PORT=(not set)"
    grep -E '^MQTT_PORT_ESP32=' "$config_env" 2>/dev/null | sed 's/^/  /' || echo "  MQTT_PORT_ESP32=(not set)"
    grep -E '^MQTT_USERNAME='   "$config_env" 2>/dev/null | sed 's/^/  /' || echo "  MQTT_USERNAME=(not set)"
    if grep -qE '^MQTT_PASSWORD=.+$' "$config_env" 2>/dev/null; then
        echo "  MQTT_PASSWORD set=yes"
    else
        echo "  MQTT_PASSWORD set=no"
    fi
    echo "============================================================"
    echo ""
}

# Read ESP32 and NEMO ports from config.env (defaults if file or keys missing)
_get_esp32_port() {
    local config_env="$SCRIPT_DIR/config.env"
    if [ -f "$config_env" ]; then
        local p
        p=$(grep -E '^MQTT_PORT_ESP32=' "$config_env" 2>/dev/null | cut -d= -f2- | tr -d '\r' | head -1)
        [ -n "$p" ] && echo "$p" && return
    fi
    echo "1883"
}
_get_nemo_port() {
    local config_env="$SCRIPT_DIR/config.env"
    if [ -f "$config_env" ]; then
        local p
        p=$(grep -E '^MQTT_PORT=' "$config_env" 2>/dev/null | cut -d= -f2- | tr -d '\r' | head -1)
        [ -n "$p" ] && echo "$p" && return
    fi
    echo "1886"
}

# Helper: set or replace KEY=VALUE in config file (portable)
_set_config_env_value() {
    local key="$1"
    local value="$2"
    local file="$3"
    if grep -q "^${key}=" "$file" 2>/dev/null; then
        if [[ "$(uname)" = "Darwin" ]]; then
            sed -i '' "s|^${key}=.*|${key}=${value}|" "$file"
        else
            sed -i "s|^${key}=.*|${key}=${value}|" "$file"
        fi
    else
        echo "${key}=${value}" >> "$file"
    fi
}

# Helper: set MQTT_USERNAME or MQTT_PASSWORD in config.env (value may contain special chars)
_set_config_env_password_line() {
    local key="$1"
    local value="$2"
    local file="$3"
    if [ ! -f "$file" ]; then
        return 1
    fi
    # Remove existing line and append new one (avoids sed escaping issues)
    grep -v "^${key}=" "$file" > "${file}.tmp" 2>/dev/null || true
    # Escape double-quotes in value for safe echo
    printf '%s=%s\n' "$key" "$value" >> "${file}.tmp"
    mv "${file}.tmp" "$file"
}

# Function to set up broker authentication (username/password stored in Mosquitto passwd file)
setup_broker_auth() {
    local config_env="$SCRIPT_DIR/config.env"
    local passwd_file="$MQTT_CONFIG_DIR/passwd"
    
    echo ""
    print_header "MQTT Broker Authentication"
    echo "You can require a username and password to connect to the MQTT broker."
    echo "Credentials are stored in a hashed password file on the broker."
    echo ""
    read -p "Enable MQTT broker authentication? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Broker authentication disabled (allow_anonymous)"
        return 0
    fi
    
    if ! command_exists mosquitto_passwd; then
        print_error "mosquitto_passwd not found. Install mosquitto with password utility (e.g. mosquitto-clients)."
        return 1
    fi
    
    read -p "MQTT username: " mqtt_user
    if [ -z "$mqtt_user" ]; then
        print_error "Username cannot be empty"
        return 1
    fi
    
    read -s -p "MQTT password: " mqtt_pass
    echo ""
    read -s -p "Confirm password: " mqtt_pass2
    echo ""
    
    if [ "$mqtt_pass" != "$mqtt_pass2" ]; then
        print_error "Passwords do not match"
        return 1
    fi
    
    if [ -z "$mqtt_pass" ]; then
        print_error "Password cannot be empty"
        return 1
    fi
    
    mkdir -p "$MQTT_CONFIG_DIR"
    # -c creates new file (overwrites); -b batch mode (password on command line)
    mosquitto_passwd -b -c "$passwd_file" "$mqtt_user" "$mqtt_pass"
    if [ $? -ne 0 ]; then
        print_error "Failed to create password file"
        return 1
    fi
    
    chmod 600 "$passwd_file"
    print_success "Password file created: $passwd_file"
    
    # Store credentials in config.env so NEMO server and clients can connect
    if [ -f "$config_env" ]; then
        _set_config_env_password_line "MQTT_USERNAME" "$mqtt_user" "$config_env"
        _set_config_env_password_line "MQTT_PASSWORD" "$mqtt_pass" "$config_env"
        _set_config_env_value "MQTT_ALLOW_ANONYMOUS" "false" "$config_env"
        chmod 600 "$config_env" 2>/dev/null || true
        print_success "Credentials written to config.env (used by NEMO server and monitor)"
        print_info "ESP32 displays: set MQTT_USERNAME and MQTT_PASSWORD in platformio.ini (same values) so they can connect to port 1883."
        _print_mqtt_config_verification
    fi
    
    # Clear from environment
    unset mqtt_pass mqtt_pass2
    print_info "Broker will use allow_anonymous false and password_file"
}

# Function to ensure MQTT directories and files have correct permissions for the user running Mosquitto
ensure_mqtt_permissions() {
    mkdir -p "$MQTT_CONFIG_DIR" "$MQTT_DATA_DIR" "$MQTT_LOG_DIR"
    # When run with sudo (e.g. after deploy to /opt), give ownership to the invoking user
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

# Decide how to run Mosquitto: as current user, or as the user who ran sudo (so broker can read passwd and write log)
# Usage: run_mosquitto "mosquitto" "-c" "$CONFIG_FILE" "-d"  (pass arguments after the broker binary)
run_mosquitto() {
    if [ "$(id -u)" = "0" ] && [ -n "${SUDO_UID:-}" ]; then
        local run_user
        run_user=$(id -un "$SUDO_UID" 2>/dev/null || true)
        if [ -n "$run_user" ]; then
            if command -v runuser >/dev/null 2>&1; then
                runuser -u "$run_user" -- "$@"
                return
            fi
            if command -v sudo >/dev/null 2>&1; then
                sudo -u "$run_user" "$@"
                return
            fi
        fi
    fi
    "$@"
}

# Function to create Mosquitto configuration
create_mosquitto_config() {
    print_header "Creating Mosquitto Configuration"
    
    # Create necessary directories
    mkdir -p "$MQTT_CONFIG_DIR" "$MQTT_DATA_DIR" "$MQTT_LOG_DIR"
    
    # Ensure correct permissions so Mosquitto can read config/passwd and write log
    ensure_mqtt_permissions
    
    # Get ports from config.env (set by write_config_env)
    ESP32_PORT=$(_get_esp32_port)
    NEMO_PORT=$(_get_nemo_port)
    
    PASSWD_FILE="$MQTT_CONFIG_DIR/passwd"
    USE_AUTH=false
    if [ -f "$PASSWD_FILE" ]; then
        # Respect explicit MQTT_ALLOW_ANONYMOUS from config.env: only allow anonymous if set to "true"
        local config_env="$SCRIPT_DIR/config.env"
        allow_anon=
        if [ -f "$config_env" ]; then
            allow_anon=$(grep -E '^MQTT_ALLOW_ANONYMOUS=' "$config_env" 2>/dev/null | cut -d= -f2- | tr -d '\r' | head -1)
        fi
        if [ "$allow_anon" != "true" ]; then
            USE_AUTH=true
        fi
    fi
    
    # Build config: general settings first
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

EOF
    
    # Add broker authentication when password file exists
    if [ "$USE_AUTH" = true ]; then
        cat >> "$CONFIG_FILE" << EOF
# Broker authentication (hashed credentials in password file)
allow_anonymous false
password_file $PASSWD_FILE

EOF
    fi
    
    # Network listeners (inherit allow_anonymous from global if set)
    cat >> "$CONFIG_FILE" << EOF
# Network settings - ESP32 displays
listener $ESP32_PORT 0.0.0.0
protocol mqtt
EOF
    if [ "$USE_AUTH" = false ]; then
        echo "allow_anonymous true" >> "$CONFIG_FILE"
    fi
    
    cat >> "$CONFIG_FILE" << EOF

# Network settings - NEMO backend
listener $NEMO_PORT 0.0.0.0
protocol mqtt
EOF
    if [ "$USE_AUTH" = false ]; then
        echo "allow_anonymous true" >> "$CONFIG_FILE"
    fi
    
    cat >> "$CONFIG_FILE" << EOF

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
    if [ "$USE_AUTH" = true ]; then
        print_info "Broker authentication: enabled (password_file)"
    else
        print_info "Broker authentication: disabled (allow_anonymous)"
    fi
}

# Function to start services
start_services() {
    print_header "Starting Services"
    
    # Start MQTT broker
    print_info "Starting MQTT broker..."
    
    # Ensure MQTT ports are free (kill by port with sudo fallback)
    ESP32_PORT=$(_get_esp32_port)
    NEMO_PORT=$(_get_nemo_port)
    for port in $ESP32_PORT $NEMO_PORT; do
        if lsof -ti :$port >/dev/null 2>&1; then
            print_info "Clearing port $port before starting broker..."
            lsof -ti :$port | xargs kill -9 2>/dev/null || true
            sleep 1
        fi
        if lsof -ti :$port >/dev/null 2>&1; then
            sudo lsof -ti :$port | xargs sudo kill -9 2>/dev/null || true
            sleep 1
        fi
    done
    pkill -f "mosquitto.*mqtt/config/mosquitto.conf" 2>/dev/null || true
    pkill -9 mosquitto 2>/dev/null || true
    if systemctl is-active --quiet mosquitto 2>/dev/null; then
        sudo systemctl stop mosquitto 2>/dev/null || true
    fi
    sleep 2
    
    # Verify config file exists
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "Mosquitto config file not found: $CONFIG_FILE"
        return 1
    fi
    
    # Ensure MQTT dirs and files have correct permissions before starting
    ensure_mqtt_permissions

    # Try to start Mosquitto and capture any errors (run as invoking user when using sudo so broker can access log/passwd)
    MOSQUITTO_ERROR=$(run_mosquitto mosquitto -c "$CONFIG_FILE" -d 2>&1)
    MOSQUITTO_EXIT=$?
    
    sleep 3
    
    # Verify MQTT broker is running
    if pgrep -f "mosquitto.*mqtt/config/mosquitto.conf" >/dev/null; then
        print_success "MQTT broker started successfully"
    else
        print_error "Failed to start MQTT broker"
        
        # Show any error output
        if [ -n "$MOSQUITTO_ERROR" ]; then
            print_error "Mosquitto error: $MOSQUITTO_ERROR"
        fi
        
        # Check if there's an error in the log file
        if [ -f "$MQTT_LOG_DIR/mosquitto.log" ]; then
            print_info "Recent Mosquitto log entries:"
            tail -10 "$MQTT_LOG_DIR/mosquitto.log" | sed 's/^/  /'
        fi
        
        # Try to start without -d flag to see errors
        print_info "Attempting to start Mosquitto in foreground to see errors..."
        print_info "Running: mosquitto -c $CONFIG_FILE"
        print_warning "If Mosquitto starts successfully, press Ctrl+C and check the error above"
        run_mosquitto mosquitto -c "$CONFIG_FILE" 2>&1 | head -20 || true
        
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
    
    # Check ports (from config.env)
    ESP32_PORT=$(_get_esp32_port)
    NEMO_PORT=$(_get_nemo_port)
    for port in $ESP32_PORT $NEMO_PORT; do
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

# Function to get VM IP address
get_vm_ip() {
    local ip=""
    local os=$(detect_os)
    
    # Try method 1: Get IP from default route interface (Linux)
    if [ "$os" != "macos" ] && command_exists ip; then
        ip=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' | head -1)
    fi
    
    # Try method 2: Use ifconfig (works on both Linux and macOS)
    if [ -z "$ip" ] || [ "$ip" = "127.0.0.1" ]; then
        if command_exists ifconfig; then
            if [ "$os" = "macos" ]; then
                # macOS: Get IP from active network interfaces (en0, en1, etc.)
                for interface in en0 en1 eth0 wlan0; do
                    ip=$(ifconfig "$interface" 2>/dev/null | grep "inet " | awk '{print $2}' | grep -v '127.0.0.1')
                    if [ -n "$ip" ] && [ "$ip" != "127.0.0.1" ]; then
                        break
                    fi
                done
            else
                # Linux: Get IP from non-loopback interface
                ip=$(ifconfig 2>/dev/null | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -1)
            fi
        fi
    fi
    
    # Try method 3: Use route command to find default interface (macOS/Linux)
    if [ -z "$ip" ] || [ "$ip" = "127.0.0.1" ]; then
        if [ "$os" = "macos" ] && command_exists route; then
            local default_if=$(route get default 2>/dev/null | grep interface | awk '{print $2}')
            if [ -n "$default_if" ]; then
                ip=$(ifconfig "$default_if" 2>/dev/null | grep "inet " | awk '{print $2}' | grep -v '127.0.0.1')
            fi
        elif [ "$os" != "macos" ] && command_exists ip; then
            local default_if=$(ip route | grep default | awk '{print $5}' | head -1)
            if [ -n "$default_if" ]; then
                ip=$(ip addr show "$default_if" 2>/dev/null | grep "inet " | awk '{print $2}' | cut -d/ -f1 | grep -v '127.0.0.1')
            fi
        fi
    fi
    
    # Fallback: Show a message if we can't determine IP
    if [ -z "$ip" ] || [ "$ip" = "127.0.0.1" ]; then
        ip="<unable to detect - check network settings>"
    fi
    
    echo "$ip"
}

# Function to display VM IP address for NEMO configuration
display_vm_ip() {
    print_header "VM IP Address for NEMO Configuration"
    
    local vm_ip=$(get_vm_ip)
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}VM IP Address:${NC} ${YELLOW}$vm_ip${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    local nemo_port=$(_get_nemo_port)
    local esp32_port=$(_get_esp32_port)
    print_info "Copy the IP address above and configure it in your NEMO backend:"
    echo "  - MQTT Broker Host: $vm_ip"
    echo "  - NEMO port: ${nemo_port}"
    echo "  - ESP32 port: ${esp32_port}"
    echo ""
}

# Main execution
main() {
    print_header "NEMO Tool Display Setup"
    echo "This script will:"
    echo "  - Install Mosquitto MQTT broker"
    echo "  - Set up Python environment"
    echo "  - Generate HMAC key; optionally set broker username/password"
    echo "  - Start all services"
    echo ""
    
    # Change to script directory
    cd "$SCRIPT_DIR"
    
    # Install Mosquitto
    install_mosquitto
    
    # Configure ports and auth first so we clear only those ports
    echo ""
    print_header "Configuration"
    write_config_env
    setup_broker_auth
    
    # Stop existing processes (clears only the configured ports)
    stop_existing_processes
    
    # Setup Python environment
    setup_python_environment
    
    # Create Mosquitto configuration (uses ports from config.env)
    create_mosquitto_config
    
    # Display VM IP address for NEMO configuration (so user can copy it)
    display_vm_ip
    
    # Ask user if ready to launch services
    echo ""
    print_header "Ready to Launch Services?"
    echo "Before starting the MQTT broker and NEMO server, make sure you have:"
    echo "  ✓ Copied the VM IP address (shown above)"
    echo "  ✓ Noted MQTT_HMAC_KEY in config.env if you need it for NEMO"
    echo ""
    read -p "Ready to launch MQTT broker and NEMO server? (Y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_info "Setup paused. Run the script again when ready, or start services manually:"
        echo "  - MQTT broker: mosquitto -c mqtt/config/mosquitto.conf -d"
        echo "  - NEMO server: source venv/bin/activate && python3 main.py"
        echo ""
        print_warning "Services were not started. Configuration is ready."
        return 0
    fi
    
    # Stop any processes that might have started during setup
    print_info "Ensuring ports are free before starting services..."
    stop_existing_processes
    
    # Start services
    start_services
    
    # Show status
    show_status
    
    print_success "NEMO Tool Display setup completed successfully!"
}

# Run main function
main "$@"

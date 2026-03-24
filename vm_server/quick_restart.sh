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
MQTT_MONITOR_LOG="$MQTT_LOG_DIR/mqtt_monitor.log"
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

# Function to get ports from config.env (always distinct: ESP32 and NEMO)
get_esp32_port() {
    echo "${MQTT_PORT_ESP32:-1883}"
}

get_nemo_port() {
    local nemo="${MQTT_PORT:-1886}"
    local esp32="${MQTT_PORT_ESP32:-1883}"
    # NEMO must not use the same port as ESP32; default 1886 if missing or duplicate
    if [ -z "$nemo" ] || [ "$nemo" = "$esp32" ]; then
        echo "1886"
    else
        echo "$nemo"
    fi
}

# Get all MQTT ports from config (space-separated for loops)
get_mqtt_ports() {
    echo "$(get_esp32_port) $(get_nemo_port)"
}

# Ensure MQTT directories and files are readable/writable by the user that runs Mosquitto.
# Fixes deploys under /opt where mqtt/ was created as root while quick_restart runs as a normal user.
ensure_mqtt_permissions() {
    mkdir -p "$MQTT_CONFIG_DIR" "$MQTT_DATA_DIR" "$MQTT_LOG_DIR"

    local target_u target_g
    if [ -n "${SUDO_UID:-}" ] && [ -n "${SUDO_GID:-}" ] && [ "${EUID:-$(id -u)}" -eq 0 ]; then
        target_u="$SUDO_UID"
        target_g="$SUDO_GID"
    else
        target_u="$(id -u)"
        target_g="$(id -g)"
    fi

    if [ "${EUID:-$(id -u)}" -ne 0 ]; then
        if ! touch "$MQTT_LOG_DIR/.perm_test_$$" 2>/dev/null || { [ -f "$MQTT_CONFIG_DIR/passwd" ] && [ ! -r "$MQTT_CONFIG_DIR/passwd" ]; }; then
            print_warning "MQTT tree not accessible as $(id -un); fixing ownership with sudo..."
            if ! sudo chown -R "$target_u:$target_g" "$MQTT_CONFIG_DIR" "$MQTT_DATA_DIR" "$MQTT_LOG_DIR"; then
                print_error "Could not fix permissions. Run once:"
                echo "  sudo chown -R $(id -un):$(id -gn) \"$MQTT_CONFIG_DIR\" \"$MQTT_DATA_DIR\" \"$MQTT_LOG_DIR\""
                return 1
            fi
        fi
        rm -f "$MQTT_LOG_DIR/.perm_test_$$" 2>/dev/null || true
    else
        chown -R "$target_u:$target_g" "$MQTT_CONFIG_DIR" "$MQTT_DATA_DIR" "$MQTT_LOG_DIR" 2>/dev/null || true
    fi

    chmod 755 "$MQTT_CONFIG_DIR" "$MQTT_LOG_DIR" 2>/dev/null || true
    chmod 700 "$MQTT_DATA_DIR" 2>/dev/null || true
    if [ -f "$MQTT_CONFIG_DIR/passwd" ]; then
        chmod 600 "$MQTT_CONFIG_DIR/passwd" 2>/dev/null || true
    fi
    touch "$MQTT_LOG_DIR/mosquitto.log" 2>/dev/null || true
    chmod 644 "$MQTT_LOG_DIR/mosquitto.log" 2>/dev/null || true
    if [ -f "$MQTT_DATA_DIR/mosquitto.db" ]; then
        chmod 600 "$MQTT_DATA_DIR/mosquitto.db" 2>/dev/null || true
    fi

    if ! touch "$MQTT_LOG_DIR/.perm_verify_$$" 2>/dev/null; then
        print_error "Cannot write $MQTT_LOG_DIR after permission fix."
        return 1
    fi
    rm -f "$MQTT_LOG_DIR/.perm_verify_$$" 2>/dev/null || true
    if [ -f "$MQTT_CONFIG_DIR/passwd" ] && [ ! -r "$MQTT_CONFIG_DIR/passwd" ]; then
        print_error "Cannot read $MQTT_CONFIG_DIR/passwd after permission fix."
        return 1
    fi
    return 0
}

# Run Mosquitto as the invoking user when this script was started with sudo (matches setup.sh).
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
                sudo -u "$run_user" -- "$@"
                return
            fi
        fi
    fi
    "$@"
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
    if command -v fuser >/dev/null 2>&1; then
        fuser -k "${port}/tcp" 2>/dev/null || sudo fuser -k "${port}/tcp" 2>/dev/null || true
        sleep 1
    fi
}

# Phase 1: Close all MQTT ports from config and kill every process using them.
# Run this first so the broker can bind to localhost later.
close_mqtt_ports_and_kill_connections() {
    local ports esp32_port nemo_port port i
    esp32_port=$(get_esp32_port)
    nemo_port=$(get_nemo_port)
    ports="$esp32_port $nemo_port"
    print_info "Closing MQTT ports from config: $esp32_port, $nemo_port"

    # Stop systemd mosquitto so it doesn't hold the port (and doesn't respawn if we kill it)
    if systemctl is-active --quiet mosquitto 2>/dev/null; then
        sudo systemctl stop mosquitto 2>/dev/null || true
    fi

    # Kill processes by port and by name
    for port in $ports; do
        kill_port "$port"
    done
    pkill -9 -f "mosquitto.*mqtt/config/mosquitto.conf" 2>/dev/null || true
    pkill -9 mosquitto 2>/dev/null || true
    pkill -f "python.*main\.py" 2>/dev/null || true
    pkill -f "python.*mqtt_monitor\.py" 2>/dev/null || true
    pkill -f "python.*manage\.py" 2>/dev/null || true
    pkill -f "python.*nemo" 2>/dev/null || true
    pkill -f "mosquitto_sub" 2>/dev/null || true
    for port in $ports; do
        kill_port "$port"
    done
    # Wait until ports are actually free (up to 5s)
    for i in 1 2 3 4 5; do
        local busy=0
        for port in $ports; do
            if lsof -i :"$port" >/dev/null 2>&1 || (command -v ss >/dev/null 2>&1 && ss -tln 2>/dev/null | grep -q ":${port} "); then
                busy=1
                kill_port "$port"
            fi
        done
        [ "$busy" -eq 0 ] && break
        sleep 1
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

# Ensure mosquitto.conf has two distinct listeners (esp32_port and nemo_port).
# Fixes broken configs where both listeners were the same (e.g. 1883,1883).
ensure_mosquitto_conf_listeners() {
    local esp32_port="$1" nemo_port="$2"
    [ ! -f "$CONFIG_FILE" ] && return 0
    local first_second
    first_second=$(awk -v e="$esp32_port" -v n="$nemo_port" '
        /^listener [0-9]+ / { if (++c==1) { sub(/listener [0-9]+/, "listener " e); print; next } else if (c==2) { sub(/listener [0-9]+/, "listener " n); print; next } }
        { print }
    ' "$CONFIG_FILE")
    echo "$first_second" > "$CONFIG_FILE"
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
    if ! ensure_mqtt_permissions; then
        return 1
    fi

    # Ensure broker config has two distinct ports (fixes 1883+1883 from bad config)
    ensure_mosquitto_conf_listeners "$esp32_port" "$nemo_port"

    # Start MQTT broker (run as invoking user when script was sudo'd — same as setup.sh)
    print_info "Starting MQTT broker on localhost:$esp32_port, localhost:$nemo_port..."
    if ! echo "=== quick_restart.sh $(date) ===" >> "$MQTT_LOG_DIR/mosquitto.log"; then
        print_error "Cannot append to $MQTT_LOG_DIR/mosquitto.log (permissions?)"
        return 1
    fi
    run_mosquitto mosquitto -c "$CONFIG_FILE" -d

    if ! wait_for_port "$nemo_port" 15; then
        print_error "MQTT broker did not start (port $nemo_port not listening after 15s)"
        if [ -f "$MQTT_LOG_DIR/mosquitto.log" ]; then
            print_info "Last lines of mosquitto.log (from this run):"
            tail -n 25 "$MQTT_LOG_DIR/mosquitto.log" | sed 's/^/  /'
        fi
        print_info "Attempting to start broker in foreground to capture error:"
        if command -v timeout >/dev/null 2>&1; then
            timeout 3 run_mosquitto mosquitto -c "$CONFIG_FILE" 2>&1 | sed 's/^/  /' || true
        else
            run_mosquitto mosquitto -c "$CONFIG_FILE" 2>&1 | sed 's/^/  /' | head -40 || true
        fi
        return 1
    fi
    print_success "MQTT broker listening on localhost:$esp32_port, localhost:$nemo_port"

    # Start NEMO server (connects to localhost / MQTT_BROKER)
    print_info "Starting NEMO server..."
    source venv/bin/activate
    python3 main.py &
    sleep 3

    print_info "Starting MQTT monitor (logging to mqtt/log/mqtt_monitor.log)..."
    : > "$MQTT_MONITOR_LOG"
    PYTHONUNBUFFERED=1 nohup python3 mqtt_monitor.py >> "$MQTT_MONITOR_LOG" 2>&1 &
    sleep 2

    print_success "Services started"
}

# Stream MQTT monitor log; Ctrl+C stops only this view (monitor keeps running).
follow_mqtt_monitor_log() {
    print_header "MQTT monitor (live log)"
    print_info "Monitor runs in the background. Press Ctrl+C to stop viewing; the monitor keeps running."
    echo ""
    print_info "Log file: $MQTT_MONITOR_LOG"
    echo ""
    tail -f "$MQTT_MONITOR_LOG" || true
    echo ""
    print_info "Stopped following log. Monitor is still running (same log: $MQTT_MONITOR_LOG)."
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
    
    if pgrep -f "python.*mqtt_monitor\.py" >/dev/null; then
        print_success "MQTT monitor: Running"
    else
        print_error "MQTT monitor: Not running"
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
    print_info "Test: python3 test_system.py  (add --forward to verify NEMO→ESP32 forwarding)"
    follow_mqtt_monitor_log
}

# Run main function
main "$@"
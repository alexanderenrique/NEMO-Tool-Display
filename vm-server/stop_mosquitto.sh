#!/bin/bash

# Script to forcefully stop all Mosquitto instances and free ports

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SCRIPT_DIR/config.env" ] && set -a && source "$SCRIPT_DIR/config.env" && set +a
ESP32_PORT="${MQTT_PORT_ESP32:-1883}"
NEMO_PORT="${MQTT_PORT:-1886}"

echo "Stopping all Mosquitto processes..."

# Stop all Mosquitto processes
pkill mosquitto 2>/dev/null && echo "✓ Sent SIGTERM to Mosquitto processes"
sleep 1
pkill -9 mosquitto 2>/dev/null && echo "✓ Force killed any remaining Mosquitto processes"

# Stop systemd service if it exists
if systemctl is-active --quiet mosquitto 2>/dev/null; then
    echo "Stopping systemd Mosquitto service..."
    sudo systemctl stop mosquitto 2>/dev/null && echo "✓ Stopped systemd Mosquitto service"
fi

# Free ports
for port in $ESP32_PORT $NEMO_PORT; do
    if lsof -ti :$port >/dev/null 2>&1; then
        echo "Freeing port $port..."
        lsof -ti :$port | xargs kill -9 2>/dev/null && echo "✓ Port $port freed"
    fi
done

sleep 2

# Verify
echo ""
echo "Verification:"
for port in $ESP32_PORT $NEMO_PORT; do
    if lsof -ti :$port >/dev/null 2>&1; then
        echo "⚠ Port $port is still in use:"
        lsof -ti :$port | xargs ps -p 2>/dev/null || echo "  (process info unavailable)"
    else
        echo "✓ Port $port is free"
    fi
done

echo ""
echo "Done!"

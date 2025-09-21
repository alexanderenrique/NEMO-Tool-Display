#!/bin/bash

# Quick Restart - One-liner restart with VM server IP detection
echo "🔄 Quick restarting services with VM server IP detection..."

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Run dynamic IP setup for VM server only
echo "🔍 Detecting and updating VM server IP address..."
cd "$PROJECT_DIR"
python3 vm_server/dynamic_ip_setup.py

if [ $? -ne 0 ]; then
    echo "❌ VM server IP setup failed. Continuing with existing configuration..."
fi

# Kill everything
echo "🛑 Stopping existing services..."
pkill -f "mosquitto.*mqtt/config/mosquitto.conf" 2>/dev/null
pkill -f "python.*main\.py" 2>/dev/null
pkill -f "mosquitto_sub" 2>/dev/null

# Wait a moment
sleep 2

# Start MQTT broker
cd /Users/adenton/Desktop/NEMO-Tool-Display/vm_server
mosquitto -c mqtt/config/mosquitto.conf -d
sleep 3

# Start NEMO server with venv
source venv/bin/activate && python3 main.py &

echo "✅ Services restarted! Check with: ./quick_mqtt_check.sh"

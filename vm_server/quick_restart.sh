#!/bin/bash

# Quick Restart - One-liner restart
echo "🔄 Quick restarting services..."

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

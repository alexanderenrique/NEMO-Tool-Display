#!/bin/bash

# Watch All MQTT Messages
# Simple and reliable message monitoring using mosquitto_sub

echo "=========================================="
echo "MQTT Message Watcher - All Topics"
echo "=========================================="
echo "Watching all messages on both ports..."
echo "Press Ctrl+C to stop"
echo ""

# Function to add timestamp and source to messages
add_timestamp() {
    while IFS= read -r line; do
        timestamp=$(date '+%H:%M:%S')
        echo "[$timestamp] $line"
    done
}

# Start monitoring port 1883 (ESP32s) in background
echo "🔌 Starting monitor for port 1883 (ESP32s)..."
mosquitto_sub -h localhost -p 1883 -t "#" -v | add_timestamp | sed 's/^/[ESP32s] /' &

# Start monitoring port 8883 (NEMO SSL) in background  
echo "🔌 Starting monitor for port 8883 (NEMO SSL)..."
mosquitto_sub -h localhost -p 8883 -t "#" -v --cafile mqtt/certs/ca.crt | add_timestamp | sed 's/^/[NEMO  ] /' &

echo ""
echo "✅ Both monitors started!"
echo "📡 Watching for messages on all topics..."
echo ""

# Wait for user interrupt
trap 'echo ""; echo "🛑 Stopping message monitors..."; pkill -f "mosquitto_sub.*1883"; pkill -f "mosquitto_sub.*8883"; echo "✅ Monitors stopped."; exit 0' INT

# Keep script running
while true; do
    sleep 1
done

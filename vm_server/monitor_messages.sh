#!/bin/bash

# MQTT Message Monitor
# Shows all messages flowing through the broker in real-time

echo "=========================================="
echo "MQTT Message Monitor - All Topics"
echo "=========================================="
echo "Monitoring all MQTT messages on both ports..."
echo "Press Ctrl+C to stop"
echo ""

# Function to monitor messages on a specific port
monitor_port() {
    local port=$1
    local port_name=$2
    local ssl_flag=$3
    
    echo "Starting monitor for $port_name (port $port)..."
    
    if [ "$ssl_flag" = "ssl" ]; then
        mosquitto_sub -h localhost -p $port -t "#" --cafile mqtt/certs/ca.crt -v | while read line; do
            timestamp=$(date '+%H:%M:%S')
            echo "[$timestamp] [$port_name] $line"
        done &
    else
        mosquitto_sub -h localhost -p $port -t "#" -v | while read line; do
            timestamp=$(date '+%H:%M:%S')
            echo "[$timestamp] [$port_name] $line"
        done &
    fi
}

# Start monitoring both ports
monitor_port 1883 "ESP32s" "non-ssl"
monitor_port 8883 "NEMO" "ssl"

# Wait for user to stop
echo "Message monitoring active. Press Ctrl+C to stop all monitors..."
wait

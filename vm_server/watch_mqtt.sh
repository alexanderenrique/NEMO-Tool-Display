#!/bin/bash

# Real-time MQTT Broker Monitoring
# Watches broker status and shows live updates

echo "Starting real-time MQTT broker monitoring..."
echo "Press Ctrl+C to stop"
echo ""

while true; do
    clear
    echo "=========================================="
    echo "MQTT Broker Live Monitor - $(date)"
    echo "=========================================="
    
    # Process status
    if pgrep -f "mosquitto.*mqtt/config/mosquitto.conf" > /dev/null; then
        echo "🟢 Broker: RUNNING (PID: $(pgrep -f "mosquitto.*mqtt/config/mosquitto.conf"))"
    else
        echo "🔴 Broker: NOT RUNNING"
    fi
    
    # Port status
    echo ""
    echo "Ports:"
    if lsof -i :1883 > /dev/null 2>&1; then
        echo "  🟢 1883 (ESP32s): LISTENING"
    else
        echo "  🔴 1883 (ESP32s): NOT LISTENING"
    fi
    
    if lsof -i :8883 > /dev/null 2>&1; then
        echo "  🟢 8883 (NEMO SSL): LISTENING"
    else
        echo "  🔴 8883 (NEMO SSL): NOT LISTENING"
    fi
    
    if lsof -i :9001 > /dev/null 2>&1; then
        echo "  🟢 9001 (WebSocket): LISTENING"
    else
        echo "  🔴 9001 (WebSocket): NOT LISTENING"
    fi
    
    # Active connections
    echo ""
    echo "Active Connections:"
    connections=$(lsof -i :1883 -i :8883 -i :9001 | grep -v "LISTEN" | wc -l)
    if [ $connections -gt 0 ]; then
        echo "  📡 $connections active connection(s)"
        lsof -i :1883 -i :8883 -i :9001 | grep -v "LISTEN" | head -3 | while read line; do
            echo "     $line"
        done
    else
        echo "  📡 No active connections"
    fi
    
    # Recent activity
    echo ""
    echo "Recent Activity:"
    if [ -f "mqtt/log/mosquitto.log" ]; then
        tail -3 mqtt/log/mosquitto.log | while read line; do
            echo "  📝 $line"
        done
    else
        echo "  📝 No log activity"
    fi
    
    echo ""
    echo "=========================================="
    echo "Refreshing in 5 seconds... (Ctrl+C to stop)"
    
    sleep 5
done

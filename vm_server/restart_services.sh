#!/bin/bash

# Restart Services Script
# Easy way to restart both MQTT broker and NEMO server

echo "=========================================="
echo "Restarting NEMO Tool Display Services"
echo "=========================================="

# Function to kill processes
kill_service() {
    local service_name=$1
    local pattern=$2
    
    echo "🛑 Stopping $service_name..."
    pkill -f "$pattern" 2>/dev/null
    sleep 2
    
    # Force kill if still running
    if pgrep -f "$pattern" > /dev/null; then
        echo "   Force killing $service_name..."
        pkill -9 -f "$pattern" 2>/dev/null
        sleep 1
    fi
    
    if pgrep -f "$pattern" > /dev/null; then
        echo "   ❌ Failed to stop $service_name"
        return 1
    else
        echo "   ✅ $service_name stopped"
        return 0
    fi
}

# Function to start services
start_service() {
    local service_name=$1
    local command=$2
    
    echo "🚀 Starting $service_name..."
    eval "$command" &
    sleep 2
    
    if pgrep -f "$service_name" > /dev/null; then
        echo "   ✅ $service_name started successfully"
        return 0
    else
        echo "   ❌ Failed to start $service_name"
        return 1
    fi
}

# Stop all services
echo "Stopping all services..."
kill_service "MQTT Broker" "mosquitto.*mqtt/config/mosquitto.conf"
kill_service "NEMO Server" "python.*main\.py"
kill_service "Message Monitors" "mosquitto_sub"

echo ""

# Start MQTT broker
echo "Starting MQTT broker..."
cd /Users/adenton/Desktop/NEMO-Tool-Display/vm_server
mosquitto -c mqtt/config/mosquitto.conf -d

if [ $? -eq 0 ]; then
    echo "✅ MQTT broker started"
    sleep 3
else
    echo "❌ Failed to start MQTT broker"
    exit 1
fi

# Start NEMO server
echo "Starting NEMO server..."
cd /Users/adenton/Desktop/NEMO-Tool-Display/vm_server
source venv/bin/activate && python3 main.py &

if [ $? -eq 0 ]; then
    echo "✅ NEMO server started"
    sleep 2
else
    echo "❌ Failed to start NEMO server"
    exit 1
fi

# Verify services are running
echo ""
echo "Verifying services..."
sleep 2

if pgrep -f "mosquitto.*mqtt/config/mosquitto.conf" > /dev/null; then
    echo "✅ MQTT broker is running (PID: $(pgrep -f "mosquitto.*mqtt/config/mosquitto.conf"))"
else
    echo "❌ MQTT broker is not running"
fi

if pgrep -f "python.*main\.py" > /dev/null; then
    echo "✅ NEMO server is running (PID: $(pgrep -f "python.*main\.py"))"
else
    echo "❌ NEMO server is not running"
fi

# Test connectivity
echo ""
echo "Testing connectivity..."
if mosquitto_pub -h localhost -p 1883 -t "test/restart" -m "Services restarted" > /dev/null 2>&1; then
    echo "✅ Port 1883 (ESP32s) - Working"
else
    echo "❌ Port 1883 (ESP32s) - Failed"
fi

if mosquitto_pub -h localhost -p 8883 -t "test/restart" -m "Services restarted" --cafile mqtt/certs/ca.crt > /dev/null 2>&1; then
    echo "✅ Port 8883 (NEMO SSL) - Working"
else
    echo "❌ Port 8883 (NEMO SSL) - Failed"
fi

echo ""
echo "=========================================="
echo "✅ Services restart complete!"
echo "=========================================="
echo "MQTT Broker: localhost:1883 (ESP32s), localhost:8883 (NEMO SSL)"
echo "NEMO Server: Running and monitoring tool status"
echo ""
echo "To monitor messages: ./watch_all_messages.sh"
echo "To check status: ./quick_mqtt_check.sh"

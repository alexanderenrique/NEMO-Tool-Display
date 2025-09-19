#!/bin/bash

# MQTT Broker Monitoring Script
# Monitors Mosquitto broker status and port connectivity

echo "=========================================="
echo "MQTT Broker Monitoring Dashboard"
echo "=========================================="
echo "Timestamp: $(date)"
echo ""

# Check if Mosquitto process is running
echo "1. PROCESS STATUS:"
if pgrep -f "mosquitto.*mqtt/config/mosquitto.conf" > /dev/null; then
    echo "   ✅ Mosquitto broker is RUNNING"
    echo "   PID: $(pgrep -f "mosquitto.*mqtt/config/mosquitto.conf")"
else
    echo "   ❌ Mosquitto broker is NOT RUNNING"
    echo "   Start with: mosquitto -c mqtt/config/mosquitto.conf -d"
fi
echo ""

# Check port listeners
echo "2. PORT STATUS:"
echo "   Checking listening ports..."

# Port 1883 (Non-SSL for ESP32s)
if lsof -i :1883 > /dev/null 2>&1; then
    echo "   ✅ Port 1883 (Non-SSL) - LISTENING"
    echo "      ESP32s can connect here"
else
    echo "   ❌ Port 1883 (Non-SSL) - NOT LISTENING"
fi

# Port 8883 (SSL for NEMO)
if lsof -i :8883 > /dev/null 2>&1; then
    echo "   ✅ Port 8883 (SSL) - LISTENING"
    echo "      NEMO publisher can connect here"
else
    echo "   ❌ Port 8883 (SSL) - NOT LISTENING"
fi

# Port 9001 (WebSocket)
if lsof -i :9001 > /dev/null 2>&1; then
    echo "   ✅ Port 9001 (WebSocket) - LISTENING"
else
    echo "   ❌ Port 9001 (WebSocket) - NOT LISTENING"
fi
echo ""

# Test connectivity
echo "3. CONNECTIVITY TESTS:"
echo "   Testing port connections..."

# Test port 1883
if mosquitto_pub -h localhost -p 1883 -t "monitor/test" -m "test" > /dev/null 2>&1; then
    echo "   ✅ Port 1883 - CONNECTIVITY OK"
else
    echo "   ❌ Port 1883 - CONNECTIVITY FAILED"
fi

# Test port 8883 (SSL)
if mosquitto_pub -h localhost -p 8883 -t "monitor/test" -m "test" --cafile mqtt/certs/ca.crt > /dev/null 2>&1; then
    echo "   ✅ Port 8883 (SSL) - CONNECTIVITY OK"
else
    echo "   ❌ Port 8883 (SSL) - CONNECTIVITY FAILED"
fi
echo ""

# Show active connections
echo "4. ACTIVE CONNECTIONS:"
echo "   Current MQTT connections:"
lsof -i :1883 -i :8883 -i :9001 | grep -v "LISTEN" | while read line; do
    if [ ! -z "$line" ]; then
        echo "   📡 $line"
    fi
done
echo ""

# Show recent log entries
echo "5. RECENT LOG ENTRIES:"
if [ -f "mqtt/log/mosquitto.log" ]; then
    echo "   Last 5 log entries:"
    tail -5 mqtt/log/mosquitto.log | while read line; do
        echo "   📝 $line"
    done
else
    echo "   📝 No log file found at mqtt/log/mosquitto.log"
fi
echo ""

# SSL Certificate status
echo "6. SSL CERTIFICATE STATUS:"
if [ -f "mqtt/certs/server.crt" ] && [ -f "mqtt/certs/server.key" ] && [ -f "mqtt/certs/ca.crt" ]; then
    echo "   ✅ SSL certificates are present"
    echo "   📄 Server cert: $(ls -la mqtt/certs/server.crt | awk '{print $5}') bytes"
    echo "   🔑 Server key: $(ls -la mqtt/certs/server.key | awk '{print $5}') bytes"
    echo "   🏛️  CA cert: $(ls -la mqtt/certs/ca.crt | awk '{print $5}') bytes"
else
    echo "   ❌ SSL certificates missing or incomplete"
fi
echo ""

echo "=========================================="
echo "Monitoring complete!"
echo "=========================================="

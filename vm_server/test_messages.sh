#!/bin/bash

# Test Message Publisher
# Sends test messages to both ports to verify monitoring

echo "Sending test messages to both MQTT ports..."

# Test messages for port 1883 (ESP32s)
echo "📤 Sending test messages to port 1883 (ESP32s)..."
mosquitto_pub -h localhost -p 1883 -t "esp32/sensor/temperature" -m "23.5"
mosquitto_pub -h localhost -p 1883 -t "esp32/sensor/humidity" -m "65.2"
mosquitto_pub -h localhost -p 1883 -t "esp32/status" -m "online"
mosquitto_pub -h localhost -p 1883 -t "esp32/display/update" -m "Tool 1: Active"

# Test messages for port 8883 (NEMO SSL)
echo "📤 Sending test messages to port 8883 (NEMO SSL)..."
mosquitto_pub -h localhost -p 8883 -t "nemo/tool/status" -m "Tool 1: In Use" --cafile mqtt/certs/ca.crt
mosquitto_pub -h localhost -p 8883 -t "nemo/tool/location" -m "Station A" --cafile mqtt/certs/ca.crt
mosquitto_pub -h localhost -p 8883 -t "nemo/system/status" -m "Operational" --cafile mqtt/certs/ca.crt

echo "✅ Test messages sent to both ports!"
echo "Check your message monitor to see them flowing through the broker."

#!/bin/bash

# Quick MQTT Status Check
# One-liner to check broker status

echo "MQTT Status: $(if pgrep -f "mosquitto.*mqtt/config/mosquitto.conf" > /dev/null; then echo "🟢 RUNNING"; else echo "🔴 STOPPED"; fi) | Ports: $(if lsof -i :1883 > /dev/null 2>&1; then echo -n "1883✅ "; else echo -n "1883❌ "; fi)$(if lsof -i :8883 > /dev/null 2>&1; then echo -n "8883✅ "; else echo -n "8883❌ "; fi)$(if lsof -i :9001 > /dev/null 2>&1; then echo -n "9001✅"; else echo -n "9001❌"; fi) | Connections: $(lsof -i :1883 -i :8883 -i :9001 | grep -v "LISTEN" | wc -l | tr -d ' ') | $(date '+%H:%M:%S')"

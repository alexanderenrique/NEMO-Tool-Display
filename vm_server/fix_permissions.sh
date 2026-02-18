#!/bin/bash

# Quick script to fix Mosquitto database file permissions

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MQTT_DATA_DIR="$SCRIPT_DIR/mqtt/data"

echo "Fixing Mosquitto data directory permissions..."

# Create directory if it doesn't exist
mkdir -p "$MQTT_DATA_DIR"

# Fix directory permissions
chmod 700 "$MQTT_DATA_DIR" 2>/dev/null && echo "✓ Fixed directory permissions: $MQTT_DATA_DIR"

# Fix database file permissions if it exists
if [ -f "$MQTT_DATA_DIR/mosquitto.db" ]; then
    chmod 600 "$MQTT_DATA_DIR/mosquitto.db" 2>/dev/null && echo "✓ Fixed database file permissions: $MQTT_DATA_DIR/mosquitto.db"
else
    echo "ℹ Database file doesn't exist yet (will be created when Mosquitto starts)"
fi

echo ""
echo "Permissions fixed! You can now try starting Mosquitto again."

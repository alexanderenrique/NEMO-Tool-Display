#!/bin/bash

# Quick script to fix Mosquitto directory and file permissions (config, data, log, passwd)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MQTT_CONFIG_DIR="$SCRIPT_DIR/mqtt/config"
MQTT_DATA_DIR="$SCRIPT_DIR/mqtt/data"
MQTT_LOG_DIR="$SCRIPT_DIR/mqtt/log"

echo "Fixing Mosquitto permissions..."

mkdir -p "$MQTT_CONFIG_DIR" "$MQTT_DATA_DIR" "$MQTT_LOG_DIR"

# When run with sudo (e.g. after deploy to /opt), give ownership to the invoking user
if [ -n "${SUDO_UID:-}" ] && [ -n "${SUDO_GID:-}" ]; then
    chown -R "$SUDO_UID:$SUDO_GID" "$MQTT_CONFIG_DIR" "$MQTT_DATA_DIR" "$MQTT_LOG_DIR" 2>/dev/null && echo "✓ Set ownership to current user"
fi

chmod 755 "$MQTT_CONFIG_DIR" "$MQTT_LOG_DIR" 2>/dev/null && echo "✓ Fixed config and log directory permissions"
chmod 700 "$MQTT_DATA_DIR" 2>/dev/null && echo "✓ Fixed data directory permissions: $MQTT_DATA_DIR"

if [ -f "$MQTT_CONFIG_DIR/passwd" ]; then
    chmod 600 "$MQTT_CONFIG_DIR/passwd" 2>/dev/null && echo "✓ Fixed password file permissions: $MQTT_CONFIG_DIR/passwd"
    [ -n "${SUDO_UID:-}" ] && [ -n "${SUDO_GID:-}" ] && chown "$SUDO_UID:$SUDO_GID" "$MQTT_CONFIG_DIR/passwd" 2>/dev/null || true
else
    echo "ℹ Password file doesn't exist (broker may use allow_anonymous)"
fi

touch "$MQTT_LOG_DIR/mosquitto.log" 2>/dev/null || true
chmod 644 "$MQTT_LOG_DIR/mosquitto.log" 2>/dev/null && echo "✓ Fixed log file permissions: $MQTT_LOG_DIR/mosquitto.log"
[ -n "${SUDO_UID:-}" ] && [ -n "${SUDO_GID:-}" ] && chown "$SUDO_UID:$SUDO_GID" "$MQTT_LOG_DIR/mosquitto.log" 2>/dev/null || true

if [ -f "$MQTT_DATA_DIR/mosquitto.db" ]; then
    chmod 600 "$MQTT_DATA_DIR/mosquitto.db" 2>/dev/null && echo "✓ Fixed database file permissions: $MQTT_DATA_DIR/mosquitto.db"
else
    echo "ℹ Database file doesn't exist yet (will be created when Mosquitto starts)"
fi

echo ""
echo "Permissions fixed! You can now try starting Mosquitto again."
echo "If files are under /opt and were created by root, run: sudo $0"

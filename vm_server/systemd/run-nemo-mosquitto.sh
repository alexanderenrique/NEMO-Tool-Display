#!/usr/bin/env bash
# Resolves vm_server from this file's location (works when symlinked from /etc/systemd/system/).
set -euo pipefail
MOSQUITTO_BIN="${MOSQUITTO_BIN:-/usr/sbin/mosquitto}"
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
VM_SERVER="$(cd "$HERE/.." && pwd)"
cd "$VM_SERVER"
exec "$MOSQUITTO_BIN" -c mqtt/config/mosquitto.conf

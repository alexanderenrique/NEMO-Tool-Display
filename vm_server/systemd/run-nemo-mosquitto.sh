#!/usr/bin/env bash
# Finds vm_server without editing this file. Markers (any): mqtt/config/mosquitto.conf,
# mqtt/config/mosquitto.conf.example, or main.py — so a fresh clone still resolves after git pull
# even though mosquitto.conf is gitignored until setup.sh (or copy from .example).
set -euo pipefail
MOSQUITTO_BIN="${MOSQUITTO_BIN:-/usr/sbin/mosquitto}"

is_vm_server_dir() {
  local d="$1"
  [[ -f "$d/mqtt/config/mosquitto.conf" ]] \
    || [[ -f "$d/mqtt/config/mosquitto.conf.example" ]] \
    || [[ -f "$d/main.py" ]]
}

resolve_vm_server() {
  if [[ -n "${NEMO_VM_SERVER_DIR:-}" ]]; then
    cd "$NEMO_VM_SERVER_DIR" && pwd
    return
  fi
  local script_real here d parent
  script_real="$(readlink -f "${BASH_SOURCE[0]}")"
  here="$(cd "$(dirname "$script_real")" && pwd)"
  d="$here"
  for _ in {1..24}; do
    if is_vm_server_dir "$d"; then
      printf '%s\n' "$d"
      return
    fi
    parent="$(cd "$d/.." && pwd)"
    [[ "$parent" == "$d" ]] && break
    d="$parent"
  done
  echo "nemo-mosquitto: cannot find vm_server (main.py or mqtt/config) starting from ${here}." >&2
  echo "Symlink this script from the repo or set NEMO_VM_SERVER_DIR." >&2
  exit 1
}

VM_SERVER="$(resolve_vm_server)"
cd "$VM_SERVER"
CONF="$VM_SERVER/mqtt/config/mosquitto.conf"
if [[ ! -f "$CONF" ]]; then
  echo "nemo-mosquitto: missing ${CONF}" >&2
  echo "This file is gitignored. From vm_server run ./setup.sh or: cp mqtt/config/mosquitto.conf.example mqtt/config/mosquitto.conf" >&2
  exit 1
fi
exec "$MOSQUITTO_BIN" -c mqtt/config/mosquitto.conf

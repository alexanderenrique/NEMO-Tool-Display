#!/usr/bin/env bash
# Finds vm_server without editing this file: walk up from this script's real path until
# mqtt/config/mosquitto.conf exists. Prefer symlink install from the repo; if you copy the
# script into /etc, set Environment=NEMO_VM_SERVER_DIR=/path/to/vm_server on the unit.
set -euo pipefail
MOSQUITTO_BIN="${MOSQUITTO_BIN:-/usr/sbin/mosquitto}"

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
    if [[ -f "$d/mqtt/config/mosquitto.conf" ]]; then
      printf '%s\n' "$d"
      return
    fi
    parent="$(cd "$d/.." && pwd)"
    [[ "$parent" == "$d" ]] && break
    d="$parent"
  done
  echo "nemo-mosquitto: cannot find mqtt/config/mosquitto.conf starting from ${here}." >&2
  echo "Symlink ${script_real} from the repo (see nemo-mosquitto.service) or set NEMO_VM_SERVER_DIR." >&2
  exit 1
}

VM_SERVER="$(resolve_vm_server)"
cd "$VM_SERVER"
exec "$MOSQUITTO_BIN" -c mqtt/config/mosquitto.conf

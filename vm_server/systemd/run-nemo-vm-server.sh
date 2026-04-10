#!/usr/bin/env bash
# Finds vm_server by walking up from this script's real path until main.py + venv exist.
# If you copy this script into /etc, set Environment=NEMO_VM_SERVER_DIR=/path/to/vm_server on the unit.
set -euo pipefail

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
    if [[ -f "$d/main.py" && -f "$d/venv/bin/python3" ]]; then
      printf '%s\n' "$d"
      return
    fi
    parent="$(cd "$d/.." && pwd)"
    [[ "$parent" == "$d" ]] && break
    d="$parent"
  done
  echo "nemo-vm-server: cannot find main.py + venv/bin/python3 starting from ${here}." >&2
  echo "Symlink this script from the repo or set NEMO_VM_SERVER_DIR." >&2
  exit 1
}

VM_SERVER="$(resolve_vm_server)"
cd "$VM_SERVER"
exec ./venv/bin/python3 ./main.py

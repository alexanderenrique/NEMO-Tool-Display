#!/usr/bin/env bash
# Resolves vm_server from this file's location (works when symlinked from /etc/systemd/system/).
set -euo pipefail
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
VM_SERVER="$(cd "$HERE/.." && pwd)"
cd "$VM_SERVER"
exec ./venv/bin/python3 ./main.py

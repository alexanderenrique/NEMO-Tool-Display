#!/usr/bin/env bash
# Show who is hitting Mosquitto's NEMO-backend listener (port 1886).
#
# Uses the broker log (no root): tail -f mqtt/log/mosquitto.log and filter lines
# like "New connection from … on port 1886." and "New client connected … on port 1886."
#
# If prod never shows up here, traffic may not reach the VM (firewall/DNS/port).
# Optional --tcpdump watches raw TCP on 1886 (needs sudo; use on the VM, not macOS dev).
#
# Usage:
#   ./watch_mosquitto_1886.sh              # live follow
#   ./watch_mosquitto_1886.sh --recent     # last ~2000 log lines, matching 1886 only
#   ./watch_mosquitto_1886.sh --tcpdump    # raw SYN/handshake (sudo)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/mqtt/log/mosquitto.log"
# Client lines only (excludes "Opening … listen socket on port 1886." at broker start).
FILTER_REGEX='New (connection|client connected) from .+ on port 1886\.'

usage() {
  echo "Usage: $0 [--recent] [--tcpdump] [--log PATH]" >&2
  echo "  default: follow ${LOG_FILE} for 1886 listener activity" >&2
  exit 1
}

MODE=follow
CUSTOM_LOG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --recent)
      MODE=recent
      shift
      ;;
    --tcpdump)
      MODE=tcpdump
      shift
      ;;
    --log)
      LOG_FILE="${2:-}"
      [[ -n "$LOG_FILE" ]] || usage
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      usage
      ;;
  esac
done

run_tcpdump() {
  if ! command -v tcpdump >/dev/null 2>&1; then
    echo "tcpdump not found. Install it or use default log follow mode." >&2
    exit 1
  fi
  # Inbound connection attempts: SYN to 1886 without ACK (new TCP handshakes).
  # Requires cap_net_raw / sudo.
  echo "Watching TCP SYN to dst port 1886 (Ctrl+C to stop). Run on the Linux VM." >&2
  exec sudo tcpdump -i any -nn -l \
    'tcp dst port 1886 and tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0'
}

run_follow() {
  if [[ ! -f "$LOG_FILE" ]]; then
    echo "Log not found: $LOG_FILE" >&2
    echo "Start Mosquitto first, or pass --log /path/to/mosquitto.log" >&2
    exit 1
  fi
  echo "Following $LOG_FILE for listener 1886 (Ctrl+C to stop)…" >&2
  tail -Fn0 "$LOG_FILE" | grep -E --line-buffered "$FILTER_REGEX"
}

run_recent() {
  if [[ ! -f "$LOG_FILE" ]]; then
    echo "Log not found: $LOG_FILE" >&2
    exit 1
  fi
  echo "Recent activity on listener 1886 from $LOG_FILE:" >&2
  tail -n 2000 "$LOG_FILE" | grep -E "$FILTER_REGEX" || true
}

case "$MODE" in
  tcpdump) run_tcpdump ;;
  recent)  run_recent ;;
  *)       run_follow ;;
esac

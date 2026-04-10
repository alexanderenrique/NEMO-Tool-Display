#!/usr/bin/env bash
# Show activity and failures for Mosquitto's NEMO-backend listener (port 1886).
#
# Default mode is verbose: every log line that mentions listener 1886 (including
# "Opening … listen socket"), plus common broker errors that explain why a client
# never reaches "New client connected" (TLS mismatch, auth, etc.). Those errors
# are not tagged with 1886 in the log, so they appear for all listeners.
#
# Optional --tcpdump watches raw TCP SYNs to 1886 (needs sudo; use on the Linux VM).
#
# Usage:
#   ./watch_mosquitto_1886.sh                 # live follow (full debug)
#   ./watch_mosquitto_1886.sh --listener-only # only lines mentioning port 1886
#   ./watch_mosquitto_1886.sh --recent       # last N lines of log (see --lines)
#   ./watch_mosquitto_1886.sh --lines 50000 --recent
#   ./watch_mosquitto_1886.sh --tcpdump      # raw SYNs (sudo)
#   ./watch_mosquitto_1886.sh --tcpdump-verbose

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/mqtt/log/mosquitto.log"
RECENT_LINES=8000

# Anything Mosquitto logs against the 1886 listener (opens, TCP accept, MQTT connect).
REGEX_LISTENER_1886='on port 1886'

# Failure / diagnostics not tied to a port in the message (TLS, auth, I/O).
REGEX_BROKER_DEBUG='Client connection from .+ failed:|OpenSSL Error|not authorised|not authorized|Wrong version number|tlsv1 alert|socket error|Broken pipe|Connection reset|identifier rejected|Quota|message too big|Administrative action|already connected, closing old connection|[Cc]onnection refused'

usage() {
  echo "Usage: $0 [--recent] [--listener-only] [--lines N] [--tcpdump] [--tcpdump-verbose] [--log PATH]" >&2
  echo "  default: follow log — listener 1886 + common failure reasons (TLS/auth)." >&2
  echo "  --listener-only: only lines containing '${REGEX_LISTENER_1886}'." >&2
  exit 1
}

MODE=follow
FULL_DEBUG=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --recent)
      MODE=recent
      shift
      ;;
    --listener-only)
      FULL_DEBUG=0
      shift
      ;;
    --tcpdump)
      MODE=tcpdump
      shift
      ;;
    --tcpdump-verbose)
      MODE=tcpdump_verbose
      shift
      ;;
    --log)
      LOG_FILE="${2:-}"
      [[ -n "$LOG_FILE" ]] || usage
      shift 2
      ;;
    --lines)
      RECENT_LINES="${2:-}"
      [[ "$RECENT_LINES" =~ ^[0-9]+$ ]] || usage
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

filter_regex() {
  if [[ "$FULL_DEBUG" -eq 1 ]]; then
    echo "${REGEX_LISTENER_1886}|${REGEX_BROKER_DEBUG}"
  else
    echo "${REGEX_LISTENER_1886}"
  fi
}

run_tcpdump() {
  local verbose="${1:-0}"
  if ! command -v tcpdump >/dev/null 2>&1; then
    echo "tcpdump not found. Install it or use log follow mode." >&2
    exit 1
  fi
  echo "Watching TCP to port 1886 (Ctrl+C to stop). Run on the Linux VM with sudo." >&2
  if [[ "$verbose" == 1 ]]; then
    exec sudo tcpdump -i any -nn -l -vv -S 'tcp port 1886'
  fi
  exec sudo tcpdump -i any -nn -l \
    'tcp dst port 1886 and tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0'
}

run_follow() {
  if [[ ! -f "$LOG_FILE" ]]; then
    echo "Log not found: $LOG_FILE" >&2
    echo "Start Mosquitto first, or pass --log /path/to/mosquitto.log" >&2
    exit 1
  fi
  local rx
  rx="$(filter_regex)"
  if [[ "$FULL_DEBUG" -eq 1 ]]; then
    echo "Following $LOG_FILE — port 1886 listener + TLS/auth/error hints (Ctrl+C to stop)." >&2
    echo "Use --listener-only to hide global broker errors." >&2
  else
    echo "Following $LOG_FILE — lines mentioning listener 1886 only (Ctrl+C to stop)." >&2
  fi
  tail -Fn0 "$LOG_FILE" | grep -E --line-buffered "$rx"
}

run_recent() {
  if [[ ! -f "$LOG_FILE" ]]; then
    echo "Log not found: $LOG_FILE" >&2
    exit 1
  fi
  local rx
  rx="$(filter_regex)"
  echo "Last ${RECENT_LINES} lines of $LOG_FILE (matches below):" >&2
  tail -n "$RECENT_LINES" "$LOG_FILE" | grep -E "$rx" || true
}

case "$MODE" in
  tcpdump)         run_tcpdump 0 ;;
  tcpdump_verbose) run_tcpdump 1 ;;
  recent)          run_recent ;;
  *)               run_follow ;;
esac

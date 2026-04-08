#!/usr/bin/env python3
"""
Combined monitor:
- Runs mqtt_monitor.py (live topic/message view)
- Streams only NON-localhost connection activity to Mosquitto listener port 1886

This is intended to replace using both:
  - vm_server/mqtt_monitor.py
  - vm_server/watch_mosquitto_1886.sh (when you only care about non-local connections)
"""

from __future__ import annotations

import os
import queue
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Iterable, Optional, Sequence, Set, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_LOG_FILE = SCRIPT_DIR / "mqtt" / "log" / "mosquitto.log"


_LOCALHOST_TOKENS = ("127.0.0.1", "::1", "localhost")


def _is_non_localhost_host(host: str) -> bool:
    h = host.strip().lower()
    if not h:
        return False
    return not any(tok in h for tok in _LOCALHOST_TOKENS)


def _which(cmd: str) -> Optional[str]:
    from shutil import which

    return which(cmd)


def _println(prefix: str, line: str) -> None:
    sys.stdout.write(f"{prefix}{line.rstrip()}\n")
    sys.stdout.flush()


def _spawn_tail_f(log_path: Path) -> subprocess.Popen[str]:
    # Using tail keeps this lightweight and robust across log rotation.
    return subprocess.Popen(
        ["tail", "-Fn0", str(log_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def _extract_host_from_mosquitto_line(line: str) -> Optional[str]:
    # Common mosquitto patterns include:
    # - "New connection from 1.2.3.4:12345 on port 1886."
    # - "New client connected from 1.2.3.4:12345 as ..."
    # - "Client <id> disconnected."
    #
    # We mainly care about "from <host>:<port>".
    m = re.search(r"\bfrom\s+([0-9a-fA-F:.%_-]+)(?::\d+)?\b", line)
    if m:
        return m.group(1)
    return None


def _iter_non_local_1886_log_lines(lines: Iterable[str]) -> Iterable[str]:
    # Keep this conservative: only lines that explicitly mention the listener port.
    for line in lines:
        if "on port 1886" not in line:
            continue
        host = _extract_host_from_mosquitto_line(line)
        if host is None:
            continue
        if not _is_non_localhost_host(host):
            continue
        yield line


def _poll_established_non_local_1886() -> Set[Tuple[str, str]]:
    """
    Return a set of (local, remote) endpoint strings for established TCP sessions
    involving local port 1886, excluding localhost remote endpoints.
    """
    # Prefer Linux `ss`, fall back to `lsof` (macOS + Linux).
    if _which("ss"):
        # Example line:
        # ESTAB 0 0 10.0.0.5:1886 10.0.0.12:53214 ...
        p = subprocess.run(
            ["ss", "-tnH", "sport", "=", ":1886", "state", "established"],
            capture_output=True,
            text=True,
            timeout=2.0,
        )
        out = p.stdout.splitlines()
        pairs: Set[Tuple[str, str]] = set()
        for ln in out:
            parts = ln.split()
            if len(parts) < 5:
                continue
            local = parts[3]
            remote = parts[4]
            # local is expected to end with :1886; remote is ip:port
            remote_host = remote.rsplit(":", 1)[0]
            if not _is_non_localhost_host(remote_host):
                continue
            pairs.add((local, remote))
        return pairs

    if _which("lsof"):
        # lsof prints a header; lines typically include:
        # TCP 10.0.0.5:1886->10.0.0.12:53214 (ESTABLISHED)
        p = subprocess.run(
            ["lsof", "-nP", "-iTCP:1886", "-sTCP:ESTABLISHED"],
            capture_output=True,
            text=True,
            timeout=2.0,
        )
        out = p.stdout.splitlines()
        pairs = set()
        for ln in out[1:]:
            if "TCP " not in ln or "->" not in ln:
                continue
            # Grab the TCP endpoint blob: "... TCP local->remote (ESTABLISHED)"
            m = re.search(r"\bTCP\s+(\S+)->(\S+)\s+\(ESTABLISHED\)", ln)
            if not m:
                continue
            local = m.group(1)
            remote = m.group(2)
            remote_host = remote.rsplit(":", 1)[0]
            if not _is_non_localhost_host(remote_host):
                continue
            pairs.add((local, remote))
        return pairs

    return set()


def _reader_thread(
    proc: subprocess.Popen[str],
    prefix: str,
    out_q: "queue.Queue[Tuple[str, str]]",
    stop: threading.Event,
) -> None:
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            if stop.is_set():
                break
            out_q.put((prefix, line))
    except Exception as e:
        out_q.put((prefix, f"[reader error] {e}\n"))


def _mqtt_monitor_cmd() -> Sequence[str]:
    mqtt_monitor = SCRIPT_DIR / "mqtt_monitor.py"
    return [sys.executable, str(mqtt_monitor)]


def main(argv: Sequence[str]) -> int:
    log_file = Path(os.getenv("MOSQUITTO_LOG_FILE", str(DEFAULT_LOG_FILE)))
    show_tcp = os.getenv("SHOW_TCP_1886", "1").strip().lower() not in ("0", "false", "no", "off")
    tcp_interval = float(os.getenv("TCP_1886_INTERVAL_SEC", "2.0"))

    if not log_file.exists():
        _println("[SYS] ", f"Log not found: {log_file}")
        _println("[SYS] ", "Set MOSQUITTO_LOG_FILE to override.")
        return 2

    stop = threading.Event()

    mqtt_proc = subprocess.Popen(
        list(_mqtt_monitor_cmd()),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    tail_proc = _spawn_tail_f(log_file)

    out_q: "queue.Queue[Tuple[str, str]]" = queue.Queue()

    t_mqtt = threading.Thread(
        target=_reader_thread, args=(mqtt_proc, "[MQTT] ", out_q, stop), daemon=True
    )
    t_tail = threading.Thread(
        target=_reader_thread, args=(tail_proc, "[1886] ", out_q, stop), daemon=True
    )
    t_mqtt.start()
    t_tail.start()

    _println("[SYS] ", f"mqtt_monitor.py + non-local :1886 connections (log: {log_file})")
    _println("[SYS] ", "Non-local means remote host is not 127.0.0.1 / ::1 / localhost.")
    if show_tcp:
        _println("[SYS] ", f"Also printing ESTABLISHED socket diffs every {tcp_interval:g}s.")

    last_tcp: Optional[Set[Tuple[str, str]]] = None
    next_tcp = time.monotonic() + tcp_interval

    def _shutdown(signum: int, _frame) -> None:
        stop.set()
        _println("[SYS] ", f"Shutting down (signal {signum})…")
        for p in (tail_proc, mqtt_proc):
            try:
                p.send_signal(signal.SIGTERM)
            except Exception:
                pass

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while not stop.is_set():
            # Drain queued output. Tail lines get filtered before printing.
            try:
                prefix, line = out_q.get(timeout=0.2)
            except queue.Empty:
                prefix, line = "", ""

            if line:
                if prefix == "[1886] ":
                    for ok in _iter_non_local_1886_log_lines([line]):
                        _println(prefix, ok)
                else:
                    _println(prefix, line)

            # Periodic TCP socket snapshot (diff-only).
            if show_tcp and time.monotonic() >= next_tcp:
                next_tcp = time.monotonic() + tcp_interval
                cur = _poll_established_non_local_1886()
                if last_tcp is None:
                    last_tcp = cur
                    if cur:
                        _println("[TCP ] ", "ESTABLISHED (non-local) to :1886:")
                        for local, remote in sorted(cur):
                            _println("[TCP ] ", f"  {local} -> {remote}")
                    continue

                added = cur - last_tcp
                removed = last_tcp - cur
                if added or removed:
                    ts = time.strftime("%H:%M:%S")
                    _println("[TCP ] ", f"{ts} changes:")
                    for local, remote in sorted(added):
                        _println("[TCP ] ", f"  + {local} -> {remote}")
                    for local, remote in sorted(removed):
                        _println("[TCP ] ", f"  - {local} -> {remote}")
                last_tcp = cur

            # Exit if child died.
            if mqtt_proc.poll() is not None:
                stop.set()
                _println("[SYS] ", f"mqtt_monitor.py exited with {mqtt_proc.returncode}")

    finally:
        stop.set()
        for p in (tail_proc, mqtt_proc):
            try:
                p.terminate()
            except Exception:
                pass
        try:
            mqtt_proc.wait(timeout=2.0)
        except Exception:
            pass
        try:
            tail_proc.wait(timeout=2.0)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


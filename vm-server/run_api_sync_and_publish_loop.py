#!/usr/bin/env python3
"""
Always-on helper: refresh NEMO API JSON snapshots on a schedule, then publish per-tool
next_reservation MQTT topics based on those files.

Schedule:
  - Every 15 minutes: download reservations -> republish
  - Nightly (local midnight): download users + tools -> republish
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Sequence

from config_parser import load_config_env
from nemo_helpers import seconds_until_midnight_local


_VM_SERVER_DIR = Path(__file__).resolve().parent


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _configure_logger() -> logging.Logger:
    level_name = (os.getenv("LOG_LEVEL") or "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")
    return logging.getLogger("run_api_sync_and_publish_loop")


def _run(cmd: Sequence[str], logger: logging.Logger, *, cwd: Path) -> int:
    logger.info("Running: %s", " ".join(cmd))
    try:
        r = subprocess.run(list(cmd), cwd=str(cwd), text=True)
        if r.returncode != 0:
            logger.error("Command failed rc=%s: %s", r.returncode, " ".join(cmd))
        return int(r.returncode)
    except Exception as e:
        logger.exception("Command failed to run: %s (%s)", " ".join(cmd), e)
        return 127


def _python_cmd(script_path: Path) -> List[str]:
    # Run using the same interpreter as this daemon (systemd will point at venv python).
    return [sys.executable, str(script_path)]


@dataclass(frozen=True)
class _Paths:
    download_reservations: Path
    download_users: Path
    download_tools: Path
    publisher: Path


def _paths() -> _Paths:
    return _Paths(
        download_reservations=(_VM_SERVER_DIR / "API" / "scripts" / "download_reservations.py").resolve(),
        download_users=(_VM_SERVER_DIR / "API" / "scripts" / "download_user_lookup.py").resolve(),
        download_tools=(_VM_SERVER_DIR / "API" / "scripts" / "download_tool_lookup.py").resolve(),
        publisher=(_VM_SERVER_DIR / "publish_next_reservations_from_files.py").resolve(),
    )


def _sleep_until(t: float, logger: logging.Logger, stop_file: Optional[Path]) -> None:
    """Sleep in small increments so systemd stop is responsive."""
    while True:
        if stop_file and stop_file.exists():
            logger.warning("Stop file present (%s). Exiting.", stop_file)
            raise SystemExit(0)
        now = time.monotonic()
        if now >= t:
            return
        time.sleep(min(2.0, t - now))


def main(argv: Optional[List[str]] = None) -> int:
    load_config_env()
    logger = _configure_logger()

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--reservations-interval-sec",
        type=int,
        default=_env_int("NEMO_RESERVATIONS_POLL_SECONDS", 900),
        help="Seconds between reservations downloads (default: env NEMO_RESERVATIONS_POLL_SECONDS or 900).",
    )
    ap.add_argument(
        "--stop-file",
        default=os.getenv("NEMO_API_SYNC_STOP_FILE", "").strip(),
        help="Optional: if this file exists, exit cleanly (useful outside systemd).",
    )
    args = ap.parse_args(argv)

    p = _paths()
    for sp in (p.download_reservations, p.download_users, p.download_tools, p.publisher):
        if not sp.is_file():
            logger.error("Missing required script: %s", sp)
            return 2

    interval = max(60, int(args.reservations_interval_sec))
    stop_file = Path(args.stop_file).expanduser().resolve() if args.stop_file else None

    logger.info("Starting API sync loop (interval=%ss). VM dir=%s", interval, _VM_SERVER_DIR)
    logger.info("Nightly lookups at local midnight; republish after each refresh.")

    # Run immediately on startup so the system converges quickly after reboot.
    next_reservation_run = time.monotonic()
    next_lookup_run = time.monotonic() + seconds_until_midnight_local()

    while True:
        now_mono = time.monotonic()
        next_run = min(next_reservation_run, next_lookup_run)
        _sleep_until(next_run, logger, stop_file)

        # Re-evaluate times after waking.
        now_mono = time.monotonic()

        # Nightly user/tool refresh
        if now_mono >= next_lookup_run:
            wall = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
            logger.info("Nightly lookup refresh starting (%s)", wall)
            rc_u = _run(_python_cmd(p.download_users), logger, cwd=_VM_SERVER_DIR)
            rc_t = _run(_python_cmd(p.download_tools), logger, cwd=_VM_SERVER_DIR)
            rc_p = _run(_python_cmd(p.publisher), logger, cwd=_VM_SERVER_DIR) if (rc_u == 0 and rc_t == 0) else 3
            logger.info("Nightly refresh done rc_users=%s rc_tools=%s rc_publish=%s", rc_u, rc_t, rc_p)
            next_lookup_run = time.monotonic() + seconds_until_midnight_local()

        # Periodic reservations refresh
        if now_mono >= next_reservation_run:
            rc_r = _run(_python_cmd(p.download_reservations), logger, cwd=_VM_SERVER_DIR)
            rc_p = _run(_python_cmd(p.publisher), logger, cwd=_VM_SERVER_DIR) if rc_r == 0 else 3
            logger.info("15-min refresh done rc_reservations=%s rc_publish=%s", rc_r, rc_p)
            next_reservation_run = time.monotonic() + interval

        # Safety: avoid drift if system clock jumps; schedule from monotonic “now”.
        next_reservation_run = max(next_reservation_run, time.monotonic() + 1.0)
        next_lookup_run = max(next_lookup_run, time.monotonic() + 1.0)


if __name__ == "__main__":
    raise SystemExit(main())


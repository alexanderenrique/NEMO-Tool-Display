#!/usr/bin/env python3
"""
Download the most recent NEMO reservation rows via pagination.

Winning parameters for fast recent pulls:
  format=json
  page_size=500
Then follow paginated "next" links until 2,500 rows (5 pages) are collected.

Run:
  cd vm-server
  ./venv/bin/python download_recent_reservations_probe.py
  ./venv/bin/python download_recent_reservations_probe.py --limit 2500 --page-size 500

Notes:
- Loads env from vm-server/config.env (via config_parser.load_config_env()).
- Uses Authorization header "Token <token>" by default (same as other scripts).
- Makes requests with NO TIMEOUT (timeout=None) because the endpoint may be slow.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin
from pathlib import Path

import requests

_VM_SERVER_DIR = Path(__file__).resolve().parents[2]
if str(_VM_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_VM_SERVER_DIR))

from config_parser import load_config_env
from nemo_helpers import _normalize_base_url, api_auth_headers


load_config_env()


def _api_token() -> str:
    return (os.getenv("NEMO_API_TOKEN") or os.getenv("NEMO_TOKEN") or "").strip()


def _auth_scheme() -> str:
    return (os.getenv("NEMO_API_AUTH_SCHEME") or "Token").strip() or "Token"


def _base_url() -> str:
    return (os.getenv("NEMO_API_BASE_URL") or "https://nemo.stanford.edu/api").strip().rstrip("/")


def _reservations_url() -> str:
    base = _normalize_base_url(_base_url())
    return urljoin(base + "/", "reservations/")

def _default_out_path() -> Path:
    # vm-server/API/scripts/download_reservations.py -> vm-server/API/data/reservations_recent.json
    here = Path(__file__).resolve()
    return here.parents[1] / "data" / "reservations_recent.json"


def _parse_page(body: Any) -> Tuple[List[Any], Optional[str]]:
    if isinstance(body, dict) and isinstance(body.get("results"), list):
        nxt = body.get("next")
        return body["results"], (nxt if isinstance(nxt, str) and nxt.strip() else None)
    if isinstance(body, list):
        return body, None
    return [], None


def _fetch_recent_reservations(
    session: requests.Session,
    url: str,
    headers: Dict[str, str],
    *,
    limit: int,
    page_size: int,
) -> List[Any]:
    params = {"format": "json", "page_size": str(page_size)}
    out: List[Any] = []
    next_url: Optional[str] = url
    first = True

    while next_url and len(out) < limit:
        p = params if first else None  # params only on first request when following "next"
        first = False

        t0 = time.monotonic()
        r = session.get(next_url, headers=headers, params=p, timeout=None)
        dt = time.monotonic() - t0
        r.raise_for_status()

        items, next_url = _parse_page(r.json())
        out.extend(items)
        print(
            f"page items={len(items)} total={min(len(out), limit)} elapsed_s={dt:.2f} next={'yes' if next_url else 'no'}"
        )

        if not items:
            break

    return out[:limit]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=2500, help="Total rows to collect (default: 2500).")
    ap.add_argument("--page-size", type=int, default=500, help="DRF page_size parameter (default: 500).")
    ap.add_argument(
        "--out",
        default=str(_default_out_path()),
        help="Write collected rows to this JSON file (default: vm-server/API/data/reservations_recent.json).",
    )
    args = ap.parse_args()

    tok = _api_token()
    if not tok:
        print("Missing NEMO_API_TOKEN or NEMO_TOKEN in environment (load vm-server/config.env).", file=sys.stderr)
        return 2

    url = _reservations_url()
    hdr = api_auth_headers(tok, _auth_scheme())

    print(f"[download] url={url}")
    print(f"[download] limit={args.limit} page_size={args.page_size} (params: format=json&page_size={args.page_size})")
    print("[download] NOTE: requests timeout is disabled (timeout=None).")

    session = requests.Session()
    try:
        rows = _fetch_recent_reservations(
            session,
            url,
            hdr,
            limit=max(1, args.limit),
            page_size=max(1, args.page_size),
        )
    finally:
        session.close()

    print(f"[download] collected_rows={len(rows)}")
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "nemo_reservations_recent",
        "source_url": url,
        "limit": int(args.limit),
        "page_size": int(args.page_size),
        "rows": rows,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[download] wrote={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


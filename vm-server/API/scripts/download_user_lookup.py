#!/usr/bin/env python3
"""
Download NEMO user directory and write a compact lookup table (id -> display name).

Writes:
  vm-server/API/data/users_lookup.json

Requires:
  vm-server/config.env with NEMO_API_BASE_URL + NEMO_API_TOKEN (or NEMO_TOKEN)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests

_VM_SERVER_DIR = Path(__file__).resolve().parents[2]
if str(_VM_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_VM_SERVER_DIR))

from config_parser import load_config_env
from nemo_helpers import _normalize_base_url, api_auth_headers, user_display_from_record


load_config_env()


def _api_token() -> str:
    return (os.getenv("NEMO_API_TOKEN") or os.getenv("NEMO_TOKEN") or "").strip()


def _auth_scheme() -> str:
    return (os.getenv("NEMO_API_AUTH_SCHEME") or "Token").strip() or "Token"


def _base_url() -> str:
    return (os.getenv("NEMO_API_BASE_URL") or "https://nemo.stanford.edu/api").strip().rstrip("/")


def _users_url() -> str:
    base = _normalize_base_url(_base_url())
    return urljoin(base + "/", "users_details/users/")


def _default_out_path() -> Path:
    # vm-server/API/scripts/download_user_lookup.py -> vm-server/API/data/users_lookup.json
    here = Path(__file__).resolve()
    return here.parents[1] / "data" / "users_lookup.json"


def _parse_page(body: Any) -> Tuple[List[Any], Optional[str]]:
    if isinstance(body, dict) and isinstance(body.get("results"), list):
        nxt = body.get("next")
        return body["results"], (nxt if isinstance(nxt, str) and nxt.strip() else None)
    if isinstance(body, list):
        return body, None
    return [], None


def _fetch_all(session: requests.Session, url: str, headers: Dict[str, str], page_size: int) -> List[Any]:
    params = {"format": "json", "page_size": str(page_size)}
    out: List[Any] = []
    next_url: Optional[str] = url
    first = True
    while next_url:
        p = params if first else None
        first = False
        r = session.get(next_url, headers=headers, params=p, timeout=None)
        r.raise_for_status()
        items, next_url = _parse_page(r.json())
        out.extend(items)
        if not items:
            break
    return out


def _build_user_lookup(records: List[Any]) -> Dict[int, str]:
    out: Dict[int, str] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        uid = rec.get("id")
        try:
            iuid = int(uid)
        except (TypeError, ValueError):
            continue
        disp = user_display_from_record(rec) or f"User {iuid}"
        out[iuid] = disp
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page-size", type=int, default=500, help="DRF page_size parameter (default: 500).")
    ap.add_argument(
        "--out",
        default=str(_default_out_path()),
        help="Write lookup table to this JSON file (default: vm-server/API/data/users_lookup.json).",
    )
    args = ap.parse_args()

    tok = _api_token()
    if not tok:
        print("Missing NEMO_API_TOKEN or NEMO_TOKEN in environment (load vm-server/config.env).", file=sys.stderr)
        return 2

    url = _users_url()
    hdr = api_auth_headers(tok, _auth_scheme())
    print(f"[download] url={url}")

    session = requests.Session()
    try:
        records = _fetch_all(session, url, hdr, page_size=max(1, args.page_size))
    finally:
        session.close()

    lookup = _build_user_lookup(records)
    print(f"[download] collected_users={len(lookup)} raw_records={len(records)}")

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "nemo_users_lookup",
        "source_url": url,
        "users": {str(k): v for k, v in sorted(lookup.items())},
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[download] wrote={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


#!/usr/bin/env python3
"""
NEMO HTTPS API helpers: user directory cache + reservation selection for ESP32 payloads.
Uses requests in thread pool wrappers from asyncio to avoid blocking the event loop.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests

REQUEST_TIMEOUT_SEC = 45
USER_CACHE_VERSION = 1


def api_auth_headers(api_token: str, auth_scheme: str) -> Dict[str, str]:
    scheme = (auth_scheme or "Token").strip()
    tok = api_token.strip()
    return {"Authorization": f"{scheme} {tok}", "Accept": "application/json"}


def _normalize_base_url(api_base_url: str) -> str:
    u = api_base_url.rstrip("/")
    return u


def fetch_all_paginated(
    logger: logging.Logger,
    headers: Dict[str, str],
    session: requests.Session,
    start_url: str,
    label: str,
) -> List[Any]:
    """Accumulate Django-style paginated lists (results + optional next URL) or plain JSON arrays."""
    out: List[Any] = []
    url = start_url
    visited = set()
    while url:
        if url in visited:
            logger.warning("[%s] pagination loop detected, stopping at %s", label, url)
            break
        visited.add(url)
        r = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SEC)
        r.raise_for_status()
        body = r.json()
        page_items: Optional[List[Any]] = None
        next_url = None

        if isinstance(body, dict):
            if "results" in body and isinstance(body["results"], list):
                page_items = body["results"]
            elif isinstance(body.get("detail"), str):
                logger.error("[%s] API error detail: %s", label, body.get("detail"))
                page_items = []
            elif isinstance(body, list):  # guard
                page_items = body  # pragma: no cover
            next_rel = body.get("next") if isinstance(body, dict) else None
            if isinstance(next_rel, str) and next_rel.strip():
                next_url = next_rel.strip()
                if next_url.startswith("/"):
                    parsed = urlparse(start_url)
                    origin = f"{parsed.scheme}://{parsed.netloc}"
                    next_url = origin + next_url
        elif isinstance(body, list):
            page_items = body

        if page_items is None:
            logger.warning("[%s] unexpected JSON shape keys=%s", label, list(body.keys()) if isinstance(body, dict) else type(body))
            break

        out.extend(page_items)
        url = next_url or ""

    return out


def user_display_from_record(record: Dict[str, Any]) -> Optional[str]:
    """Pick a sensible display string for a user object."""
    uid = record.get("id")
    candidates = []

    fn = record.get("full_name") or record.get("display_name") or record.get("name")
    if isinstance(fn, str) and fn.strip():
        candidates.append(fn.strip())

    if isinstance(record.get("first_name"), str) or isinstance(record.get("last_name"), str):
        first = str(record.get("first_name") or "").strip()
        last = str(record.get("last_name") or "").strip()
        if first or last:
            candidates.append((" ".join([first, last])).strip())

    username = record.get("username")
    if isinstance(username, str) and username.strip():
        candidates.append(username.strip())

    if not candidates:
        return None if uid is None else f"User {uid}"
    best = sorted(candidates, key=len, reverse=True)[0]
    return best


def build_user_map_from_records(records: List[Any]) -> Dict[int, str]:
    uid_to_display: Dict[int, str] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        uid = rec.get("id")
        if uid is None:
            continue
        try:
            iuid = int(uid)
        except (ValueError, TypeError):
            continue
        disp = user_display_from_record(rec)
        if disp:
            uid_to_display[iuid] = disp
    return uid_to_display


def load_user_directory_cache(cache_path: Path) -> Dict[int, str]:
    if not cache_path.is_file():
        return {}
    try:
        raw = cache_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        users_raw = data.get("users") or {}
        out: Dict[int, str] = {}
        if isinstance(users_raw, dict):
            for k, v in users_raw.items():
                try:
                    ik = int(k)
                except (ValueError, TypeError):
                    continue
                if isinstance(v, str) and v.strip():
                    out[ik] = v.strip()
        return out
    except (OSError, json.JSONDecodeError):
        return {}


def save_user_directory_cache(cache_path: Path, uid_to_display: Dict[int, str], logger: logging.Logger) -> None:
    payload = {"version": USER_CACHE_VERSION, "users": {str(k): v for k, v in sorted(uid_to_display.items())}}
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(cache_path)
        logger.info("Saved user directory cache: %s entries -> %s", len(uid_to_display), cache_path)
    except OSError as e:
        logger.error("Failed to save user cache: %s", e)


def refresh_user_directory(
    api_base: str,
    headers: Dict[str, str],
    cache_path: Path,
    logger: logging.Logger,
) -> Dict[int, str]:
    """GET /users_details/users/ and persist mapped id -> display name."""
    base = _normalize_base_url(api_base)
    url = urljoin(base + "/", "users_details/users/")
    session = requests.Session()
    try:
        items = fetch_all_paginated(logger, headers, session, url, "users_directory")
        uid_map = build_user_map_from_records(items)
        save_user_directory_cache(cache_path, uid_map, logger)
        return uid_map
    finally:
        session.close()


def parse_iso_dt(value: Optional[str]) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    s = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def format_display_like_vm_main(iso_field: Optional[str], tz_offset_hours: int) -> str:
    """Match vm-server/main.py timestamp formatting (+TIMEZONE_OFFSET_HOURS after fromisoformat)."""
    if not iso_field or not isinstance(iso_field, str):
        return ""
    try:
        dt = parse_iso_dt(iso_field)
        if not dt:
            return "Invalid Time"
        dt = dt + timedelta(hours=tz_offset_hours)
        return dt.strftime("%b %d, %I:%M %p")
    except Exception:
        return "Invalid Time"


def pick_next_reservation_for_tool(
    reservations: List[Any],
    tool_id: int,
    lookahead_days: int,
    tz_offset_hours: int,
    user_map: Dict[int, str],
    tool_name_fallback: str,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Return JSON for a single tool (published to ``MQTT_TOPIC_PREFIX/<tool_id>/next_reservation`` when allowlisted)."""
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    lad = max(lookahead_days, 1)
    lookahead_cutoff = now_utc + timedelta(days=lad)

    best: Optional[Dict[str, Any]] = None
    best_start_utc: Optional[datetime] = None

    for r in reservations:
        if not isinstance(r, dict):
            continue
        if r.get("cancelled"):
            continue
        t = r.get("tool")
        try:
            if int(t) != int(tool_id):
                continue
        except (ValueError, TypeError):
            continue
        su = parse_iso_dt(r.get("start") if isinstance(r.get("start"), str) else None)
        if su is None:
            continue
        su_u = su.astimezone(timezone.utc)
        if su_u < now_utc:
            continue
        if su_u >= lookahead_cutoff:
            continue
        if best_start_utc is None or su_u < best_start_utc:
            best = r
            best_start_utc = su_u

    if best is None:
        return {
            "tool_id": tool_id,
            "tool_name": tool_name_fallback,
            "reservation_id": None,
            "user_name": "",
            "timestamp": "",
            "end_timestamp": "",
            "lookahead_days": lad,
        }

    rid = best.get("id")

    user_field = best.get("user")
    user_name_out = ""
    try:
        ui = int(user_field) if user_field is not None else None
        if ui is not None:
            user_name_out = user_map.get(ui, f"User {ui}")
        else:
            user_name_out = ""
    except (ValueError, TypeError):
        user_name_out = ""

    start_iso = best.get("start") if isinstance(best.get("start"), str) else ""
    end_iso = best.get("end") if isinstance(best.get("end"), str) else ""
    timestamp_s = format_display_like_vm_main(start_iso, tz_offset_hours)
    end_s = format_display_like_vm_main(end_iso, tz_offset_hours) if end_iso else ""

    return {
        "tool_id": tool_id,
        "tool_name": tool_name_fallback,
        "reservation_id": rid,
        "user_name": user_name_out,
        "timestamp": timestamp_s,
        "end_timestamp": end_s,
        "lookahead_days": lad,
        "cancelled": bool(best.get("cancelled")),
    }


def fetch_reservations_list(logger: logging.Logger, api_base: str, headers: Dict[str, str]) -> List[Any]:
    base = _normalize_base_url(api_base)
    url = urljoin(base + "/", "reservations/")
    session = requests.Session()
    try:
        return fetch_all_paginated(logger, headers, session, url, "reservations")
    finally:
        session.close()


def seconds_until_midnight_local() -> float:
    """Seconds until next 00:00:00 local time."""
    now = datetime.now().astimezone()
    td = timedelta(days=1)
    midnight = datetime.combine((now.date() + td), dt_time.min, tzinfo=now.tzinfo)
    delta = midnight - now
    return max(1.0, delta.total_seconds())

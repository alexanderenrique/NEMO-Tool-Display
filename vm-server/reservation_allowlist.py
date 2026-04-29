#!/usr/bin/env python3
"""
Load MQTT reservation publish allowlist: only these tool IDs receive .../<id>/next_reservation.
Supports YAML (.yaml / .yml) or CSV (.csv).
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import List

import yaml

_WARNED_MISSING_PATH: str = ""


def load_allowed_tool_ids(path: Path, logger: logging.Logger) -> List[int]:
    """Return sorted unique positive tool IDs. Empty list if file missing, unreadable, or empty."""
    global _WARNED_MISSING_PATH
    if not path.is_file():
        sp = str(path)
        if _WARNED_MISSING_PATH != sp:
            logger.warning(
                "Reservation MQTT allowlist file not found: %s — no next_reservation publishes",
                path,
            )
            _WARNED_MISSING_PATH = sp
        return []
    suffix = path.suffix.lower()
    try:
        if suffix in (".yaml", ".yml"):
            raw = path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
            ids = _ids_from_yaml(data)
        elif suffix == ".csv":
            ids = _ids_from_csv(path)
        else:
            logger.error(
                "Unsupported reservation allowlist extension %s (use .yaml, .yml, or .csv)",
                suffix,
            )
            return []
    except Exception as e:
        logger.exception("Failed to read reservation allowlist %s: %s", path, e)
        return []

    out: List[int] = []
    for x in ids:
        try:
            n = int(x)
            if n > 0:
                out.append(n)
        except (TypeError, ValueError):
            continue

    uniq = sorted(set(out))
    if not uniq:
        logger.debug(
            "Reservation MQTT allowlist %s has no valid positive tool IDs — no publishes",
            path,
        )
    else:
        logger.debug("Reservation MQTT allowlist: %s tool IDs", len(uniq))
    return uniq


def _ids_from_yaml(data) -> List:
    """Accept top-level list of ints OR dict keys tool_ids / tools / mqtt_tools."""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("tool_ids", "tools", "mqtt_tools"):
            v = data.get(key)
            if isinstance(v, list):
                return v
    return []


def _ids_from_csv(path: Path) -> List:
    """First column numeric tool ID per row; skips header rows named tool_id / id."""
    out: List = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row_num, row in enumerate(reader):
            if not row:
                continue
            cell = str(row[0]).strip()
            if not cell or cell.startswith("#"):
                continue
            if row_num == 0 and cell.lower() in ("tool_id", "id", "tools", "tool"):
                continue
            try:
                out.append(int(cell))
            except ValueError:
                continue
    return out

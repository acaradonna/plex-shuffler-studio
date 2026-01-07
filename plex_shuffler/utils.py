"""Utility helpers for config parsing and data normalization."""

from __future__ import annotations

import datetime as dt
from typing import Iterable
from urllib.parse import parse_qsl


def parse_query_string(query: str) -> list[tuple[str, str]]:
    if not query:
        return []
    return [(key, value) for key, value in parse_qsl(query, keep_blank_values=True)]


def merge_dicts(base: dict, updates: dict) -> dict:
    """Deep-merge two dictionaries without mutating inputs."""
    if not isinstance(base, dict) or not isinstance(updates, dict):
        return updates
    merged = dict(base)
    for key, value in updates.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def ensure_list(value: object | None) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_title(value: str) -> str:
    return value.strip().lower()


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def cutoff_from_days(days: int | float | None, now: dt.datetime) -> dt.datetime | None:
    if not days or days <= 0:
        return None
    return now - dt.timedelta(days=float(days))


def clamp_items(items: list, limit: int | None) -> list:
    if limit and limit > 0:
        return items[:limit]
    return items


def chunked(seq: Iterable, size: int) -> list[list]:
    if size <= 0:
        return [list(seq)]
    chunk = []
    chunks: list[list] = []
    for item in seq:
        chunk.append(item)
        if len(chunk) >= size:
            chunks.append(chunk)
            chunk = []
    if chunk:
        chunks.append(chunk)
    return chunks

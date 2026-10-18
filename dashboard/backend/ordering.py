"""Incident ordering shared by the API and tests.

Priority order is critical, high, medium, low. Any other value, including a
missing priority, is unclassified and sorts after low. Missing timestamps sort
after records that have one. They are never filled in.
"""
from __future__ import annotations

from datetime import datetime

PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
UNCLASSIFIED_RANK = 4


def priority_rank(value: str | None) -> int:
    if value is None:
        return UNCLASSIFIED_RANK
    key = str(value).strip().lower()
    if not key:
        return UNCLASSIFIED_RANK
    return PRIORITY_RANK.get(key, UNCLASSIFIED_RANK)


def parsed_time(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def sort_incidents(items: list[dict], mode: str = "priority") -> list[dict]:
    def ident(item: dict) -> str:
        return str(item.get("id") or "")

    def newest_key(item: dict):
        when = parsed_time(item.get("created_at"))
        missing = when is None
        stamp = -when.timestamp() if when else 0
        return (missing, stamp, ident(item))

    def oldest_key(item: dict):
        when = parsed_time(item.get("created_at"))
        missing = when is None
        stamp = when.timestamp() if when else 0
        return (missing, stamp, ident(item))

    rows = list(items)
    if mode == "newest":
        rows.sort(key=newest_key)
    elif mode == "oldest":
        rows.sort(key=oldest_key)
    else:
        rows.sort(key=lambda item: (priority_rank(item.get("priority")),) + newest_key(item))
    return rows

"""Shared, cache-aware FMP earnings calendar fetcher for sector workflows.

FMP caps large calendar responses at 4,000 rows.  A nominal 30-day request can
therefore return only the newest part of the interval without an explicit
error.  This module detects a saturated response, bisects the date interval,
and de-duplicates the inclusive boundaries.  Exact-range responses are cached
for two hours, matching the provider's calendar refresh cadence.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from scripts._shared import fmp_pool

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "sector" / "cache" / "earnings_calendar"
CACHE_TTL_SEC = 2 * 60 * 60
FMP_RESPONSE_CAP = 4_000


@dataclass
class FetchStats:
    api_calls: int = 0
    cache_hits: int = 0
    splits: int = 0


def _cache_path(from_date: str, to_date: str, cache_dir: Path) -> Path:
    return cache_dir / f"{from_date}_{to_date}.json"


def _read_cache(path: Path, ttl_sec: int) -> list[dict] | None:
    try:
        if time.time() - path.stat().st_mtime > ttl_sec:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("rows") if isinstance(payload, dict) else None
        return rows if isinstance(rows, list) else None
    except (OSError, ValueError, TypeError):
        return None


def _write_cache(path: Path, from_date: str, to_date: str, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "sector.earnings_calendar.raw.v1",
        "from": from_date,
        "to": to_date,
        "fetched_at": time.time(),
        "rows": rows,
    }
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _dedupe(rows: list[dict], from_date: str, to_date: str) -> list[dict]:
    unique: dict[tuple, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        event_date = str(row.get("date") or "")
        if event_date < from_date or event_date > to_date:
            continue
        key = (
            row.get("symbol"),
            event_date,
            row.get("fiscalDateEnding"),
        )
        unique[key] = row
    return sorted(
        unique.values(),
        key=lambda row: (str(row.get("date") or ""), str(row.get("symbol") or "")),
    )


def fetch_calendar_range(
    from_date: str,
    to_date: str,
    *,
    api_key: str | None = None,
    cache_dir: Path = CACHE_DIR,
    ttl_sec: int = CACHE_TTL_SEC,
    response_cap: int = FMP_RESPONSE_CAP,
    stats: FetchStats | None = None,
    getter: Callable | None = None,
) -> list[dict]:
    """Return a complete date interval, recursively splitting capped responses."""
    start = date.fromisoformat(from_date)
    end = date.fromisoformat(to_date)
    if start > end:
        raise ValueError(f"invalid earnings-calendar range: {from_date} > {to_date}")

    fetch_stats = stats if stats is not None else FetchStats()
    get = getter or fmp_pool.get
    path = _cache_path(from_date, to_date, cache_dir)
    rows = _read_cache(path, ttl_sec)
    if rows is not None:
        fetch_stats.cache_hits += 1
    else:
        rows = get(
            "earnings-calendar",
            {"from": from_date, "to": to_date},
            stable=True,
            hard_fail=True,
            api_key=api_key,
        )
        fetch_stats.api_calls += 1
        if not isinstance(rows, list):
            raise ValueError("FMP earnings-calendar returned a non-list response")
        _write_cache(path, from_date, to_date, rows)

    if len(rows) < response_cap:
        return _dedupe(rows, from_date, to_date)
    if start == end:
        raise RuntimeError(
            f"FMP earnings-calendar saturated at {response_cap} rows for {from_date}; "
            "cannot prove completeness"
        )

    fetch_stats.splits += 1
    midpoint = start + timedelta(days=(end - start).days // 2)
    left = fetch_calendar_range(
        from_date,
        midpoint.isoformat(),
        api_key=api_key,
        cache_dir=cache_dir,
        ttl_sec=ttl_sec,
        response_cap=response_cap,
        stats=fetch_stats,
        getter=get,
    )
    right_start = midpoint + timedelta(days=1)
    right = fetch_calendar_range(
        right_start.isoformat(),
        to_date,
        api_key=api_key,
        cache_dir=cache_dir,
        ttl_sec=ttl_sec,
        response_cap=response_cap,
        stats=fetch_stats,
        getter=get,
    )
    return _dedupe(left + right, from_date, to_date)


__all__ = ["FetchStats", "fetch_calendar_range"]

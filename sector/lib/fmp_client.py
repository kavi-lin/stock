"""Shared FMP HTTP client for sector/scripts/fetch_*.py. See sector/scripts/README.md."""
from __future__ import annotations

import os
import sys
import time
from typing import Any

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "sector", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

FMP_BASE = "https://financialmodelingprep.com"

sys.path.insert(0, BASE_DIR)
from skills._shared.company_context import (  # noqa: E402
    SECTOR_UNIVERSE,
    TICKER_TO_SECTOR,
    SECTOR_TOP_5,
)


def fmp_get(
    path: str,
    params: dict,
    *,
    retries: int = 2,
    timeout: int = 20,
    hard_fail: bool = True,
) -> Any:
    """GET FMP REST with 429 exponential backoff. Hard-fails on persistent error
    (sys.exit(1)) when hard_fail=True; returns None on persistent error otherwise.
    """
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        msg = "[ERROR] FMP_API_KEY not set"
        if hard_fail:
            sys.exit(msg)
        print(msg, file=sys.stderr)
        return None
    url = f"{FMP_BASE}{path}"
    full = {**params, "apikey": api_key}
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=full, timeout=timeout)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            # 4xx (except 429) is permanent — no point retrying
            if 400 <= r.status_code < 500:
                last_exc = requests.HTTPError(f"{r.status_code} {r.reason}", response=r)
                break
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_exc = e
            time.sleep(0.5)
    err = f"[ERROR] FMP {path} failed after {retries+1} tries: {last_exc}"
    if hard_fail:
        sys.exit(err)
    print(err, file=sys.stderr)
    return None


def cache_path(name: str, as_of: str) -> str:
    return os.path.join(CACHE_DIR, f"{name}_{as_of}.json")


__all__ = [
    "fmp_get",
    "cache_path",
    "BASE_DIR",
    "CACHE_DIR",
    "FMP_BASE",
    "SECTOR_UNIVERSE",
    "TICKER_TO_SECTOR",
    "SECTOR_TOP_5",
]

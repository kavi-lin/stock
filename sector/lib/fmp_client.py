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
from scripts._shared import fmp_pool  # noqa: E402


def fmp_get(
    path: str,
    params: dict,
    *,
    retries: int = 2,
    timeout: int = 20,
    hard_fail: bool = True,
) -> Any:
    """GET FMP REST, rate-governed by the central cross-process pool.

    Pacing/429-backoff now live in scripts/_shared/fmp_pool (single 250/min
    budget shared across all consumers); this wrapper only forwards the
    caller-supplied full path (e.g. ``/stable/quote``) and preserves the
    hard_fail semantics (sys.exit on missing key / persistent error).
    """
    return fmp_pool.get(
        path, params, stable=False, retries=retries, timeout=timeout, hard_fail=hard_fail
    )


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

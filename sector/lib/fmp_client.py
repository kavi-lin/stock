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


def fmp_get_many(
    reqs: list[tuple[str, dict]],
    *,
    max_workers: int = 8,
    retries: int = 2,
    timeout: int = 20,
    hard_fail: bool = True,
) -> list:
    """Threaded fan-out of :func:`fmp_get`; results align positionally with reqs.

    Same path/hard_fail semantics as fmp_get (caller supplies the leading
    '/'). Aggregate RPM stays governed by the central fmp_pool window, so
    max_workers only bounds local concurrency — use this for the per-ticker
    sweeps whose sequential wall time would otherwise trip phase_prefetch's
    per-task cap.
    """
    return fmp_pool.fetch_many(
        [
            {"path": path, "params": params, "stable": False, "retries": retries,
             "timeout": timeout, "hard_fail": hard_fail}
            for path, params in reqs
        ],
        max_workers=max_workers,
    )


def cache_path(name: str, as_of: str) -> str:
    return os.path.join(CACHE_DIR, f"{name}_{as_of}.json")


__all__ = [
    "fmp_get",
    "fmp_get_many",
    "cache_path",
    "BASE_DIR",
    "CACHE_DIR",
    "FMP_BASE",
    "SECTOR_UNIVERSE",
    "TICKER_TO_SECTOR",
    "SECTOR_TOP_5",
]

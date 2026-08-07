#!/usr/bin/env python3
"""
scripts/_shared/fmp_pool — central, cross-process rate-governed FMP HTTP client.

The project has an FMP **paid** plan (250 calls/min). Historically each consumer
(sector/lib, company_context, fmp_supplementary, the per-skill fmp_client.py
files, supply_chain, the dashboard heatmap fan-out) implemented its own pacing
(hard 300ms sleeps, 150-call/day budgets, 30-min circuit breakers) tuned for the
free tier and with ZERO coordination between them. Under parallel execution
(daily_update.sh launches parallel subprocesses, each spawning threaded workers)
that left the 250/min headroom unused while still risking collective 429s.

This module is the single pacing layer. It does NOT cache — each caller keeps its
own cache/return-shape contract and merely routes the HTTP through here.

Rate limiter — cross-process sliding window
-------------------------------------------
FMP's limit is "calls per rolling minute". We model exactly that:
  - State  : JSON array of recent call epoch timestamps  (~/.cache_bridge/fmp_pool_window.json)
  - Lock   : a dedicated lockfile held via fcntl.flock     (~/.cache_bridge/fmp_pool.lock)
  - Acquire: lock → read+trim(>60s) → if len < TARGET_RPM append now & write & unlock & proceed
             else compute sleep=(oldest+60)-now, UNLOCK, sleep, retry.
The lock is held only for the microsecond read-trim-write — NEVER across the
backoff sleep (that would serialize every process). flock is per open-file-
description, so threads inside one process do not exclude each other via a shared
fd; we add a module threading.Lock so intra-process threads serialize too.

Public API
----------
  get(path, params=None, *, stable=True, retries=3, timeout=20, hard_fail=False)
  get_url(full_url, params=None, *, retries=3, timeout=20, hard_fail=False)
  fetch_many(requests, *, max_workers=12, hard_fail=False)
  acquire_slot(block=True)            # reserve a window slot WITHOUT issuing HTTP
  build_url(path, *, stable=True)

Env tuning
----------
  FMP_TARGET_RPM   target calls/min ceiling (default 220, safety margin under 250)
  FMP_POOL_STATE   override window state path  (hermetic tests)
  FMP_POOL_LOCK    override lockfile path      (hermetic tests)
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

import requests

try:
    import fcntl  # POSIX only — darwin/linux. (Project is macOS/linux per env.)
    _HAS_FCNTL = True
except ImportError:  # pragma: no cover - windows fallback (no cross-proc lock)
    _HAS_FCNTL = False

FMP_HOST = "https://financialmodelingprep.com"

DEFAULT_TARGET_RPM = int(os.getenv("FMP_TARGET_RPM", "220"))
WINDOW_SEC = 60.0
# Tiny deterministic-ish jitter (no Math.random concerns here — plain process
# entropy is fine for spreading retries) added when we have to wait, so many
# blocked workers don't all wake on the exact same instant.
_JITTER_MAX = 0.3

_CACHE_BRIDGE = Path(os.path.expanduser("~/.cache_bridge"))
_STATE_PATH = Path(os.getenv("FMP_POOL_STATE", str(_CACHE_BRIDGE / "fmp_pool_window.json")))
_LOCK_PATH = Path(os.getenv("FMP_POOL_LOCK", str(_CACHE_BRIDGE / "fmp_pool.lock")))
_LAST_429_PATH = Path(
    os.getenv("FMP_LAST_429_PATH", str(_CACHE_BRIDGE / "fmp_last_429.json"))
)

# Intra-process serialization of the lock section (flock alone does not exclude
# threads of the same process reliably).
_THREAD_LOCK = threading.Lock()

_AUTH_BLOCK = (401, 402, 403)  # permanent paid/auth block — never retry, return None


def _redact_error_body(text: str) -> str:
    """Keep FMP diagnostics useful without persisting credentials."""
    clean = (text or "")[:2000]
    key = os.environ.get("FMP_API_KEY")
    if key:
        clean = clean.replace(key, "[REDACTED]")
    clean = re.sub(
        r'(?i)(["\']?apikey["\']?\s*[:=]\s*["\']?)[^"\'\s,&}]+',
        r"\1[REDACTED]",
        clean,
    )
    return clean


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        try:
            when = parsedate_to_datetime(value)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def _record_429(url: str, response) -> float | None:
    """Atomically retain the latest 429 evidence, excluding query/API keys."""
    _ensure_dirs()
    _LAST_429_PATH.parent.mkdir(parents=True, exist_ok=True)
    retry_raw = response.headers.get("Retry-After")
    try:
        body = json.dumps(response.json(), ensure_ascii=False)
    except Exception:
        body = getattr(response, "text", "") or ""
    parsed = urlsplit(url)
    artifact = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "status": 429,
        "endpoint": f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
        "retry_after": retry_raw,
        "response_body": _redact_error_body(body),
    }
    tmp = _LAST_429_PATH.with_suffix(
        _LAST_429_PATH.suffix + f".{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(artifact, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _LAST_429_PATH)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
    return _retry_after_seconds(retry_raw)


def _ensure_dirs() -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)


def _read_window(fh) -> list[float]:
    try:
        fh.seek(0)
        raw = fh.read()
        if not raw.strip():
            return []
        data = json.loads(raw)
        if isinstance(data, list):
            return [float(t) for t in data]
    except Exception:
        # Corrupt / partially-written state (e.g. a process killed mid-write).
        # Recover to empty — we'd rather briefly over-permit than deadlock.
        return []
    return []


def _write_window_atomic(window: list[float]) -> None:
    tmp = _STATE_PATH.with_suffix(_STATE_PATH.suffix + f".{os.getpid()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(window, f)
        os.replace(tmp, _STATE_PATH)  # atomic on POSIX
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def acquire_slot(block: bool = True, *, target_rpm: int | None = None) -> bool:
    """Reserve one slot in the rolling 60s window. Returns True when reserved.

    When the window is full and block=True, sleep until the oldest call expires
    then retry (releasing the lock while sleeping). block=False returns False
    immediately if no slot is free. Used both internally by get()/get_url() and
    directly by the dashboard heatmap fan-out (which keeps its own urllib
    transport but still wants to count against the shared budget)."""
    cap = target_rpm if target_rpm is not None else DEFAULT_TARGET_RPM
    if not _HAS_FCNTL:
        # No cross-process lock available — degrade to a best-effort in-process
        # pause. Correctness across processes is not guaranteed on this platform.
        time.sleep(60.0 / max(cap, 1))
        return True

    _ensure_dirs()
    while True:
        with _THREAD_LOCK:
            with open(_LOCK_PATH, "w") as lockf:
                fcntl.flock(lockf, fcntl.LOCK_EX)
                try:
                    now = time.time()
                    with open(_STATE_PATH, "a+", encoding="utf-8") as sf:
                        window = _read_window(sf)
                    window = [t for t in window if now - t < WINDOW_SEC]
                    if len(window) < cap:
                        window.append(now)
                        _write_window_atomic(window)
                        return True
                    # Full — figure out how long until the oldest call ages out.
                    oldest = min(window)
                    wait = max(0.0, (oldest + WINDOW_SEC) - now)
                finally:
                    fcntl.flock(lockf, fcntl.LOCK_UN)
        # Lock released before sleeping (critical: never sleep holding the lock).
        if not block:
            return False
        jitter = (os.getpid() % 7) / 20.0  # 0..0.3, process-stable spread
        time.sleep(min(wait, WINDOW_SEC) + min(jitter, _JITTER_MAX))


def build_url(path: str, *, stable: bool = True) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if stable:
        return f"{FMP_HOST}/stable/{path.lstrip('/')}"
    return f"{FMP_HOST}{path if path.startswith('/') else '/' + path}"


def _request(url: str, params: dict, *, retries: int, timeout: int) -> tuple[Any | None, int | None]:
    """Issue a single rate-governed GET (with retries). Returns (json|None, last_status).

    A window slot is acquired before EVERY attempt (including retries) so a
    retried call still counts against the budget. 401/402/403 → permanent block,
    return immediately. 429 → exponential backoff + re-acquire. Network/5xx →
    short sleep + retry."""
    last_status: int | None = None
    for attempt in range(retries + 1):
        acquire_slot(block=True)
        try:
            r = requests.get(url, params=params, timeout=timeout)
            last_status = r.status_code
            if r.status_code in _AUTH_BLOCK:
                return None, r.status_code
            if r.status_code == 429:
                retry_after = _record_429(url, r)
                exponential = (2 ** attempt) + (os.getpid() % 5) / 10.0
                time.sleep(max(exponential, retry_after or 0.0))
                continue
            if r.status_code != 200:
                # Other 4xx are permanent; 5xx worth a short retry.
                if 400 <= r.status_code < 500:
                    return None, r.status_code
                time.sleep(0.5)
                continue
            return r.json(), r.status_code
        except Exception:
            time.sleep(0.5)
    return None, last_status


def get(
    path: str,
    params: dict | None = None,
    *,
    stable: bool = True,
    retries: int = 3,
    timeout: int = 20,
    hard_fail: bool = False,
    api_key: str | None = None,
) -> Any | None:
    """Rate-governed GET against FMP.

    stable=True  → {host}/stable/{path}
    stable=False → {host}{path}   (caller supplies the leading '/')

    Returns parsed JSON on 200, None otherwise (auth/paid block, persistent
    network error, non-200). hard_fail=True replicates the legacy sector/lib
    semantics: sys.exit on missing key or persistent network failure."""
    key = api_key or os.environ.get("FMP_API_KEY")
    if not key:
        if hard_fail:
            sys.exit("[ERROR] FMP_API_KEY not set")
        return None
    url = build_url(path, stable=stable)
    full = {**(params or {}), "apikey": key}
    data, status = _request(url, full, retries=retries, timeout=timeout)
    if data is None and hard_fail and status not in _AUTH_BLOCK:
        detail = f"; diagnostic={_LAST_429_PATH}" if status == 429 else ""
        sys.exit(f"[ERROR] FMP {path} failed (status={status}{detail})")
    return data


def get_url(
    full_url: str,
    params: dict | None = None,
    *,
    retries: int = 3,
    timeout: int = 20,
    hard_fail: bool = False,
    api_key: str | None = None,
) -> Any | None:
    """Like get() but the caller provides the fully-qualified URL (used by the
    per-skill clients that build their own stable→v3 fallback URLs). apikey is
    injected into params when absent."""
    key = api_key or os.environ.get("FMP_API_KEY")
    if not key:
        if hard_fail:
            sys.exit("[ERROR] FMP_API_KEY not set")
        return None
    p = dict(params or {})
    p.setdefault("apikey", key)
    data, status = _request(full_url, p, retries=retries, timeout=timeout)
    if data is None and hard_fail and status not in _AUTH_BLOCK:
        detail = f"; diagnostic={_LAST_429_PATH}" if status == 429 else ""
        safe_url = urlsplit(full_url)
        endpoint = f"{safe_url.scheme}://{safe_url.netloc}{safe_url.path}"
        sys.exit(f"[ERROR] FMP {endpoint} failed (status={status}{detail})")
    return data


def fetch_many(
    reqs: Sequence[dict | tuple],
    *,
    max_workers: int = 12,
    hard_fail: bool = False,
) -> list:
    """Threaded fan-out. `reqs` items are either dicts ({path, params, stable, ...})
    or (path, params) tuples. Results are positionally aligned with `reqs`.
    The cross-process window caps aggregate RPM regardless of max_workers, so
    max_workers only bounds local concurrency."""
    def _one(item):
        if isinstance(item, dict):
            kw = dict(item)
            path = kw.pop("path")
            params = kw.pop("params", None)
            kw.setdefault("hard_fail", hard_fail)
            return get(path, params, **kw)
        path, params = item[0], (item[1] if len(item) > 1 else None)
        return get(path, params, hard_fail=hard_fail)

    if not reqs:
        return []
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(reqs)))) as ex:
        return list(ex.map(_one, reqs))


__all__ = [
    "get",
    "get_url",
    "fetch_many",
    "acquire_slot",
    "build_url",
    "DEFAULT_TARGET_RPM",
    "FMP_HOST",
]

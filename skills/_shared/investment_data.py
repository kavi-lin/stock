"""Separated FMP source caches for investment preparation.

Quarter discovery is deliberately uncached; fiscal-period changes invalidate
both financial and market payloads. A failed refresh never renews old data.
"""
from __future__ import annotations

import threading
import contextlib
import contextvars
from pathlib import Path

from investment.scripts.run_data import atomic_json, digest, file_lock, fresh, read_json, source, utcnow
from scripts._shared import fmp_pool

_ACTIVE = contextvars.ContextVar("investment_source_cache", default=None)


def active_cache():
    return _ACTIVE.get()


def fmp_result(path, params=None, *, cache=None, retries=1, timeout=20):
    """Every investment caller uses the shared limiter and classified failures."""
    cache = cache or active_cache()
    params = dict(params or {})
    if cache is None:
        return fmp_pool.get_with_status(path, params, stable=False, retries=retries, timeout=timeout)
    data = cache.get(path, params, retries=retries, timeout=timeout)
    key = digest({"path": path, "params": params}).split(":")[1]
    record = cache.sources[key]
    return {"data": data, "status": record["status"], "http_status": record.get("http_status")}


@contextlib.contextmanager
def source_context(cache):
    token = _ACTIVE.set(cache)
    try:
        yield cache
    finally:
        _ACTIVE.reset(token)

FINANCIAL = {"income-statement", "balance-sheet-statement", "cash-flow-statement",
             "financial-growth", "enterprise-values", "revenue-product-segmentation",
             "revenue-geographic-segmentation", "earning_call_transcript"}


class SourceCache:
    def __init__(self, root, *, period=None, force=False, transport=None):
        self.root = Path(root)
        self.period = period
        self.force = force
        self.transport = transport or fmp_pool.get_with_status
        self.sources = {}
        self.metrics = {"requests": 0, "cache_hits": 0, "http_calls_known": 0, "http_calls_unknown": 0, "outcomes": {}}
        self._lock = threading.Lock()

    def get(self, path, params, *, refresh=False, retries=1, timeout=20):
        endpoint = path.rstrip("/").split("/")[-1]
        kind = "quote" if endpoint == "quote" else "financial" if endpoint in FINANCIAL else "market"
        key = digest({"path": path, "params": params}).split(":")[1]
        dest = self.root / kind / (key + ".json")
        # A stable per-request lock coalesces simultaneous callers as well as
        # repeated requests within a run. It does not serialize other endpoints.
        with file_lock(dest.with_suffix(".lock")):
            record = None
            if dest.exists() and not (refresh or self.force):
                try:
                    cached = read_json(dest)
                    if fresh(cached, period=self.period):
                        record = cached
                except (OSError, ValueError):
                    pass
            hit = record is not None
            if record is None:
                result = self.transport(path, params, stable=False, retries=retries, timeout=timeout)
                data = result.get("data")
                row = data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else {}
                record = source(data, kind=kind, fetched_at=utcnow(), period=self.period,
                                data_as_of=row.get("timestamp") or row.get("date") or row.get("lastUpdated"),
                                published_at=row.get("acceptedDate") or row.get("filingDate") or row.get("publishedDate"),
                                status=result["status"], reason=None if result["status"] == "ok" else result["status"])
                record["endpoint"] = path
                record["http_status"] = result.get("http_status")
                record["http_calls"] = result.get("http_calls")
                record["queue_seconds"] = result.get("queue_seconds")
                if record["status"] == "ok":
                    atomic_json(dest, record)
            with self._lock:
                self.sources[key] = record
                self.metrics["cache_hits" if hit else "requests"] += 1
                if not hit:
                    calls = record.get("http_calls")
                    self.metrics["http_calls_known" if calls is not None else "http_calls_unknown"] += calls if calls is not None else 1
                counts = self.metrics["outcomes"]
                counts[record["status"]] = counts.get(record["status"], 0) + 1
            return record["data"] if record["status"] == "ok" else None

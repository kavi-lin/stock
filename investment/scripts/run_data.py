"""Source-time contracts and immutable investment inputs (no model calls)."""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = Path(os.environ.get("AIC_INVEST_RUNS_ROOT", ROOT / "investment/invest_logs/runs"))
VERSION = "investment-run/1.0"
LANES = ("fundamentals", "sentiment", "news", "technical", "valuation")
TTL = {"quote": 300, "phase0": 10800, "financial": 604800,
       "market": 86400, "forecaster": 14400}


def accepted_lane_detail(result):
    excluded = {"score", "confidence", "signal", "key_factors", "risk_flags",
                "ticker", "phase", "agent", "subagent_isolated"}
    return {key: value for key, value in result.items() if key not in excluded}


def execution_lock(ticker):
    """Same stable lock for Dashboard and manual protocol processes."""
    return file_lock(RUNS / ".execution" / (safe_id(ticker.upper()) + ".lock"), blocking=False)


def protocol_preamble():
    if os.getenv("AIC_INVEST_RUNNER") != "v55":
        return ""
    return ("V5.5 PILOT: Read investment/run_workflow_v55.md first. Use run_investment.py "
            "prepare/claim/accept/compute/finalize and its immutable run directory. "
            "Keep broker routing and every validator. All five prompts must be frozen before "
            "the first result; dispatch at min(3, available slots), unknown=1. "
            "Use independent contexts for later batches. Never edit protocol code to pass a gate.\n\n")


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(value, timezone.utc)
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("source timestamp requires timezone")
    return dt.astimezone(timezone.utc)


def digest(value):
    return "sha256:" + hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextlib.contextmanager
def file_lock(path, *, blocking=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def safe_id(value):
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", str(value)) or value in (".", ".."):
        raise ValueError("invalid ticker/run identifier")
    return value


def source(data, *, kind, fetched_at=None, data_as_of=None, period=None,
           status="ok", reason=None, published_at=None):
    return {"kind": kind, "data": data, "data_as_of": data_as_of,
            "published_at": published_at, "fetched_at": fetched_at,
            "financial_period": period, "content_hash": digest(data),
            "status": status, "reason": reason}


def fresh(record, *, now=None, period=None):
    if not isinstance(record, dict) or record.get("status") != "ok":
        return False
    try:
        age = (timestamp(now or utcnow()) - timestamp(record["fetched_at"])).total_seconds()
        return (0 <= age <= TTL[record["kind"]]
                and record["content_hash"] == digest(record["data"])
                and (period is None or record.get("financial_period") == period))
    except (ValueError, TypeError, KeyError, OverflowError):
        return False


def check_snapshot(snapshot, *, now=None, resume=False):
    body = {k: v for k, v in snapshot.items() if k != "snapshot_hash"}
    if digest(body) != snapshot.get("snapshot_hash"):
        raise ValueError("snapshot hash mismatch")
    sources = snapshot.get("sources") or {}
    frozen_at = snapshot["analysis_at"]
    for name in ("phase0", "quote"):
        if not fresh(sources.get(name), now=frozen_at):
            raise ValueError(f"{name}: missing or stale at freeze time")
    for name, record in sources.items():
        if record.get("content_hash") != digest(record.get("data")):
            raise ValueError(f"{name}: source hash mismatch")
        if record.get("status") == "ok" and not fresh(record, now=frozen_at):
            raise ValueError(f"{name}: stale optional data marked ok")
    price = snapshot.get("price")
    if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
        raise ValueError("missing finite positive frozen price")
    if snapshot["quant_input"].get("current_price") != price:
        raise ValueError("quant price differs from frozen quote")
    if snapshot["quant_input"].get("ticker") != snapshot["ticker"]:
        raise ValueError("quant ticker differs from snapshot")
    quote = sources["quote"]["data"]
    if (quote[0] if isinstance(quote, list) else quote).get("price") != price:
        raise ValueError("frozen price differs from source quote")
    if resume:
        age = (timestamp(now or utcnow()) - timestamp(frozen_at)).total_seconds()
        if age < 0 or age > TTL["phase0"]:
            raise ValueError("snapshot expired: prepare a new run; original evidence retained")
    return snapshot


def load_snapshot(path, **kwargs):
    return check_snapshot(read_json(path), **kwargs)


def freeze_snapshot(path, *, ticker, sources, quant_input, lane_inputs,
                    classification=None, analysis_at=None):
    path = Path(path)
    if path.exists():
        raise ValueError("snapshot is immutable; use a new run")
    snap = {"schema": VERSION, "ticker": ticker, "analysis_at": analysis_at or utcnow(),
            "sources": sources, "quant_input": quant_input, "lane_inputs": lane_inputs,
            "classification": classification or {}, "price": quant_input.get("current_price")}
    snap["snapshot_hash"] = digest(snap)
    check_snapshot(snap)
    if set(lane_inputs) != set(LANES):
        raise ValueError("all five independent lane inputs must be frozen together")
    atomic_json(path, snap)
    return snap

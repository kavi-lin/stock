#!/usr/bin/env python3
"""Regression contract for daily_update exit codes in the premarket chain."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.argv = ["dashboard_server.py"]

import dashboard_server as ds  # noqa: E402


def _run_chain_to_completion(monkeypatch, *, news_result, daily_raises=False, timeout=10.0):
    """Drive run_premarket_chain() with every external leg stubbed out.

    daily is reported fresh so it skips (unless daily_raises); news and sector
    are stale so both get enqueued. Returns the terminal chain state.
    """
    def fake_preflight():
        return [
            {"key": "breadth", "status": "STALE" if daily_raises else "FRESH", "free": True},
            {"key": "news",    "status": "STALE", "free": False},
            {"key": "sector",  "status": "STALE", "free": False},
        ]

    def fake_wait(name, baseline_ts, timeout_sec, on_progress=None):
        if name == "news":
            return news_result
        return {"name": "sector", "status": "done", "error": None}

    def fake_daily():
        raise RuntimeError("daily_update boom")

    monkeypatch.setattr(ds, "preflight_check", fake_preflight)
    monkeypatch.setattr(ds, "_wait_protocol_completion", fake_wait)
    monkeypatch.setattr(ds, "enqueue_protocol", lambda name, source=None: ("queued", None))
    if daily_raises:
        monkeypatch.setattr(ds, "run_daily_update", fake_daily)

    with ds._premarket_chain_lock:
        ds._premarket_chain_state["status"] = "idle"
    ds.run_premarket_chain()

    deadline = time.time() + timeout
    while time.time() < deadline:
        with ds._premarket_chain_lock:
            status = ds._premarket_chain_state["status"]
            if status in ("done", "error"):
                return {k: (dict(v) if isinstance(v, dict) else v)
                        for k, v in ds._premarket_chain_state.items()}
        time.sleep(0.02)
    raise AssertionError("chain did not reach a terminal state")


def test_news_failure_does_not_block_sector(monkeypatch):
    """News has no data edge into sector, so its failure must not cost the sector
    run. Before this contract, phase 1 fail-fast raised on any item error and
    sector was never enqueued — 2026-08-06 lost a whole sector run to a digest
    that was complete but over-cap by the shallow validator."""
    state = _run_chain_to_completion(monkeypatch, news_result={
        "name": "news", "status": "error",
        "error": "validator rc=1: DIGEST shallow over-cap: got 20",
    })

    assert state["status"] == "done", "chain must finish despite the news failure"
    assert state["items"]["news"]["status"] == "error"
    assert state["items"]["sector"]["status"] == "done", "sector must still run"
    assert any("shallow over-cap" in w for w in state["warnings"]), \
        "the news failure must surface as a warning, not be silently swallowed"
    assert state["error"] is None


def test_daily_failure_still_blocks_sector(monkeypatch):
    """daily_update refreshes the breadth / FTD / market-top caches that sector's
    phase 0 reads, so that edge is real and must stay fail-fast."""
    state = _run_chain_to_completion(monkeypatch, news_result={
        "name": "news", "status": "done", "error": None,
    }, daily_raises=True)

    assert state["status"] == "error"
    assert state["items"]["daily"]["status"] == "error"
    assert state["items"]["sector"]["status"] == "idle", "sector must never be enqueued"
    assert "daily" in (state["error"] or "")


def test_nonblocking_set_is_news_only():
    assert ds._PREMARKET_NONBLOCKING == {"news"}


def test_daily_update_exit_contract():
    assert ds._daily_update_outcome(0) == ("done", None)

    status, message = ds._daily_update_outcome(2)
    assert status == "degraded"
    assert "usable artifacts" in message

    status, message = ds._daily_update_outcome(1)
    assert status == "error"
    assert "rc=1" in message

    assert ds._daily_update_is_terminal("done")
    assert ds._daily_update_is_terminal("degraded")
    assert ds._daily_update_is_terminal("error")
    assert not ds._daily_update_is_terminal("running")

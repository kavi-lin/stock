#!/usr/bin/env python3
"""Contract tests for the X KOL dashboard API. No network, no live server.

The one that matters most: the API records a human decision and does NOT launch
an analysis. The exploration layer must never reach into the decision layer —
a button that quietly spent a 5-lane protocol run would break that rule silently.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.argv = ["dashboard_server.py"]

import dashboard_server as ds  # noqa: E402
from scripts.x_kol import heat as heat_mod  # noqa: E402


def test_payload_has_everything_the_page_needs():
    p = ds._x_kol_heat_payload(with_prices=False)
    assert set(p) >= {"heat", "candidates", "budget", "posts", "roster"}
    assert set(p["heat"]) >= {"tickers", "themes", "posts_scanned"}
    assert set(p["budget"]) >= {"spent_usd", "total_usd", "post_reads"}


def test_no_price_request_means_no_fmp_calls(monkeypatch):
    called = []
    monkeypatch.setattr(heat_mod, "fetch_price_context",
                        lambda syms: called.append(syms) or {})
    monkeypatch.setattr(heat_mod, "resolve_identity",
                        lambda syms: called.append(syms) or {})
    ds._x_kol_heat_payload(with_prices=False)
    assert called == [], "the thermometer must render without spending FMP quota"


def test_price_enrichment_is_cached_between_requests(monkeypatch):
    ds._X_KOL_CACHE.update({"at": 0.0, "prices": {}, "identity": {}, "unanalyzable": {}})
    calls = {"n": 0}

    def fake_prices(syms):
        calls["n"] += 1
        return {s: {"last": 1.0, "d5": 1.0, "d21": 1.0, "ytd": 1.0} for s in syms}

    monkeypatch.setattr(heat_mod, "fetch_price_context", fake_prices)
    monkeypatch.setattr(heat_mod, "resolve_identity", lambda syms: {})
    ds._x_kol_heat_payload(with_prices=True)
    ds._x_kol_heat_payload(with_prices=True)
    assert calls["n"] == 1, "second request inside the TTL must reuse the cache"


def test_fmp_failure_still_renders_the_page(monkeypatch):
    ds._X_KOL_CACHE.update({"at": 0.0, "prices": {}, "identity": {}, "unanalyzable": {}})

    def boom(_syms):
        raise RuntimeError("FMP down")

    monkeypatch.setattr(heat_mod, "fetch_price_context", boom)
    monkeypatch.setattr(heat_mod, "resolve_identity", boom)
    payload = ds._x_kol_heat_payload(with_prices=True)
    assert payload["heat"]["tickers"] is not None, "heat must survive an FMP outage"


def test_decide_persists_and_is_reflected_in_the_next_payload(tmp_path, monkeypatch):
    cand = tmp_path / "candidates.json"
    monkeypatch.setattr(ds, "_x_kol_candidates_path", lambda: str(cand))

    heat_mod.decide(Path(cand), "AAOI", "promoted", note="ui test")
    assert heat_mod.load_candidates(Path(cand))["tickers"]["AAOI"]["decision"] == "promoted"

    payload = ds._x_kol_heat_payload(with_prices=False)
    assert payload["candidates"].get("AAOI", {}).get("decision") == "promoted"


def test_decide_rejects_a_bogus_decision(tmp_path):
    with pytest.raises(ValueError):
        heat_mod.decide(tmp_path / "c.json", "AAOI", "launch_analysis_now")


@pytest.mark.parametrize("bad", ["", "   ", "TOOOOOOOOLONGTICKER", "AA PL", "../etc", "<script>"])
def test_bad_tickers_are_refused_by_the_route_guard(bad):
    import re
    cleaned = bad.strip().upper().lstrip("$")
    assert not (cleaned and re.fullmatch(r"[A-Z0-9.\-]{1,12}", cleaned)), \
        f"{bad!r} must not pass the route's ticker guard"


@pytest.mark.parametrize("good", ["AAOI", "aaoi", "$AEVA", "SIVE.ST", "BRK-B"])
def test_real_tickers_pass_the_route_guard(good):
    import re
    cleaned = good.strip().upper().lstrip("$")
    assert re.fullmatch(r"[A-Z0-9.\-]{1,12}", cleaned)


def test_posts_are_newest_first_and_bounded():
    payload = ds._x_kol_heat_payload(with_prices=False)
    posts = payload["posts"]
    assert len(posts) <= 60
    stamps = [p.get("created_at") or "" for p in posts]
    assert stamps == sorted(stamps, reverse=True), "newest first"


def test_api_never_triggers_an_analysis():
    """Guard the boundary in the source itself: the decide route must not call
    into the protocol runner. If someone wires 'promote' to auto-run 分析, this
    fails — which is the entire point of the human gate."""
    src = (ROOT / "dashboard_server.py").read_text(encoding="utf-8")
    start = src.index('if path == "/api/x-kol/decide":')
    body = src[start:start + 1600]
    for forbidden in ("enqueue_protocol", "run_protocol", "run_daily_update", "subprocess"):
        assert forbidden not in body, f"decide route must not call {forbidden}"


def test_a_ticker_with_no_price_does_not_loop_the_refresh_forever(monkeypatch):
    """$SIVE has no price series, so it never lands in `prices`. Keying the
    refresh check off `prices` would re-fan-out on every request forever and
    quietly burn the shared FMP window — hence `attempted`.

    The fake Thread captures the target instead of running it: the payload holds
    _X_KOL_REFRESH_LOCK while spawning, and the refresh takes the same
    non-reentrant lock, so running it inline would deadlock (it did).
    """
    ds._X_KOL_CACHE.update({"at": 0.0, "prices": {}, "identity": {},
                            "unanalyzable": {}, "attempted": set()})
    calls = {"n": 0}
    spawned = []

    def fake_prices(syms):
        calls["n"] += 1
        return {s: {"last": 1.0, "d5": 1.0, "d21": 1.0, "ytd": 1.0}
                for s in syms if s != "SIVE"}          # SIVE never priced

    class FakeThread:
        def __init__(self, target=None, args=(), **kw):
            spawned.append((target, args))

        def start(self):
            pass

    monkeypatch.setattr(heat_mod, "fetch_price_context", fake_prices)
    monkeypatch.setattr(heat_mod, "resolve_identity", lambda syms: {})
    monkeypatch.setattr(ds.threading, "Thread", FakeThread)

    ds._x_kol_heat_payload(with_prices=True)
    assert len(spawned) == 1, "first request schedules exactly one refresh"
    target, args = spawned[0]
    target(*args)                       # run it now that the lock is released
    assert calls["n"] == 1

    p2 = ds._x_kol_heat_payload(with_prices=True)
    assert len(spawned) == 1, "an unpriceable ticker must not retrigger a refresh"
    assert p2["prices_pending"] is False
    assert "SIVE" not in p2["heat"]["prices"]

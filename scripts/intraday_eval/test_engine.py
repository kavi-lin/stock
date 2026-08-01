#!/usr/bin/env python3
"""
Golden-fixture regression test for the intraday_eval engine.

Runs the deterministic evaluate() against a synthetic snapshot and asserts the
strategy rules fire as designed. MUST pass (rc=0) after any engine change.

    python3 -m scripts.intraday_eval.test_engine
    python3 scripts/intraday_eval/test_engine.py   # same result, repo convention
"""
from __future__ import annotations

import sys

if __package__:
    from . import engine
else:
    # Run as a plain script: relative imports have no parent package, so put the
    # repo root on the path and import absolutely. Every other test in this repo
    # is invoked as `python3 <path>`, and failing that way looks like a red test.
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.intraday_eval import engine


def _fixture():
    """A synthetic intraday snapshot: semis crushed, software/crypto ripping,
    committee DEFENSIVE, small-caps leading — the 2026-07-01 archetype."""
    heatmap = {"tickers": (
        # semis — all down hard
        [{"symbol": s, "change_pct": c, "sector": "Technology"} for s, c in
         [("MU", -8.0), ("KLAC", -9.3), ("LRCX", -8.0), ("AMAT", -7.7),
          ("WDC", -6.0), ("GLW", -12.3), ("ASML", -5.7), ("INTC", -7.0)]]
        # software — up
        + [{"symbol": s, "change_pct": c, "sector": "Technology"} for s, c in
           [("APP", 10.9), ("PLTR", 9.4), ("SHOP", 7.8), ("WDAY", 6.8),
            ("TTD", 8.2), ("TEAM", 8.1)]]
        # crypto/fintech
        + [{"symbol": s, "change_pct": c, "sector": "Financial Services"} for s, c in
           [("COIN", 10.7), ("HOOD", 7.5), ("MSTR", 11.0)]]
        # a couple defensive/value names
        + [{"symbol": "JPM", "change_pct": 1.3, "sector": "Financial Services"},
           {"symbol": "LLY", "change_pct": 1.5, "sector": "Healthcare"},
           {"symbol": "XOM", "change_pct": -2.0, "sector": "Energy"}]
    )}
    intraday_mood = {
        "aggregate": {"score": 27, "risk_label": "偏強", "headline_zh": "盤面偏強"},
        "tickers": [
            {"symbol": "SPY", "intraday_return_prevclose_pct": 0.31, "distribution_days": 7},
            {"symbol": "QQQ", "intraday_return_prevclose_pct": -0.66, "distribution_days": 6},
            {"symbol": "IWM", "intraday_return_prevclose_pct": 0.70, "distribution_days": 5},
        ],
    }
    market_mood = {
        "mood": {"score": -19}, "vix": {"current": 16.3, "regime": "NORMAL"},
        "skew": {"current": 149.6, "label": "high"},
        "fear_greed": {"index": 32.8, "label": "Fear"},
    }
    retail_sector_pulse = {"sectors": [
        {"sector": "Financials", "predicted_5d_median_pct": 1.97, "composite_direction": "mod_bull"},
        {"sector": "Healthcare", "predicted_5d_median_pct": 2.0, "composite_direction": "mod_bull"},
        {"sector": "Materials", "predicted_5d_median_pct": 2.04, "composite_direction": "mod_bull"},
        {"sector": "Technology", "predicted_5d_median_pct": -0.62, "composite_direction": "neutral_mixed"},
        {"sector": "Energy", "predicted_5d_median_pct": -1.42, "composite_direction": "mod_bear"},
    ]}
    intraday_spikes = {
        "trends": [{"symbol": "META", "direction": "up", "dir_zh": "順勢續攻", "strength": "strong"}],
        "reversals": [{"symbol": "AVGO", "direction": "up", "dir_zh": "反轉向上",
                       "strength": "strong", "alert": True}],
    }
    thematic = {"themes": [
        {"theme": "AI & Semiconductors", "direction": "bullish", "lifecycle": "Trending"},
        {"theme": "Space Economy", "direction": "bullish", "lifecycle": "Warm"},
    ]}
    return {
        "intraday_mood": intraday_mood, "market_mood": market_mood, "heatmap": heatmap,
        "retail_sector_pulse": retail_sector_pulse, "intraday_spikes": intraday_spikes,
        "kill_triggers": None, "thematic": thematic, "sector_stance": {"stance": "DEFENSIVE"},
    }


def main():
    src = _fixture()
    p = engine.evaluate(src)
    ids = {c["id"] for c in p["strategies"]}
    by_id = {c["id"]: c for c in p["strategies"]}
    checks = []

    def ok(cond, label):
        checks.append((bool(cond), label))

    # regime
    ok(p["regime"]["posture"] == "defensive", "DEFENSIVE stance forces defensive posture")
    ok(p["regime"]["exposure_ceiling"] == "0-25%", "defensive exposure ceiling 0-25%")
    ok(any("SKEW" in c for c in p["regime"]["cautions"]), "SKEW caution surfaced")
    ok(any("F&G" in c for c in p["regime"]["cautions"]), "Fear&Greed caution surfaced")

    # breadth
    ok(p["breadth"]["n"] == 20, "breadth counts all 20 fixture rows")
    ok(p["breadth"]["adv_pct"] is not None, "adv_pct computed")

    # groups / rotation
    ok(p["groups"]["semiconductors"]["avg"] < -5, "semis group deeply negative")
    ok(p["groups"]["software_platforms"]["avg"] > 5, "software group positive")
    ok(p["groups"]["crypto_fintech"]["avg"] > 5, "crypto/fintech group positive")

    # strategy cards
    ok("semis_derisk" in ids, "semis_derisk fires")
    ok("software_momentum" in ids, "software_momentum fires")
    ok("semis_to_software_rotation" in ids, "rotation card fires")
    ok("crypto_fintech_riskon" in ids, "crypto risk-on fires")
    ok("value_defensive_rotation" in ids, "value/defensive rotation fires")
    ok("defensive_cash" in ids, "defensive_cash fires under DEFENSIVE")
    ok("smallcap_riskon" in ids, "small-cap risk-on fires (IWM>SPY>QQQ)")
    ok("event_risk_guard" in ids, "event-risk guard fires (dist days>=6)")
    ok("avoid_laggards" in ids, "avoid laggards fires (Energy AVOID)")

    # semis card carries worst tickers
    ok("GLW" in by_id["semis_derisk"]["tickers"], "semis_derisk lists worst ticker GLW")
    # cards are confidence-sorted
    confs = [c["confidence"] for c in p["strategies"]]
    ok(confs == sorted(confs, reverse=True), "strategies sorted by confidence desc")

    # sectors ranked, Energy AVOID
    energy = next((s for s in p["sectors"] if s["sector"] == "Energy"), None)
    ok(energy and energy["verdict"] == "AVOID", "Energy sector verdict AVOID")

    # ideas: live trend + reversal + leaders, enriched with chg
    idea_ids = {i["ticker"] for i in p["ideas"]}
    ok("META" in idea_ids, "live trend idea META present")
    ok("AVGO" in idea_ids, "alert reversal idea AVGO present")
    ok(any(i["ticker"] == "MSTR" and i["chg"] is not None for i in p["ideas"]),
       "leader idea enriched with chg")

    passed = sum(1 for c, _ in checks if c)
    for cond, label in checks:
        if not cond:
            print(f"  FAIL: {label}")
    print(f"[test_engine] {passed}/{len(checks)} asserts passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())

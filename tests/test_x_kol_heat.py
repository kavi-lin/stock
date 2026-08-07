#!/usr/bin/env python3
"""Contract tests for theme heat + the human-gated promotion queue. No network.

The load-bearing claims, all grounded on real 2026-08-06 data:
  * position matters — in a joke about pronouncing $AAOI, the props $TSM/$AMD
    tracked the market while the subject ran +45.8% over 5 days;
  * but a secondary mention is not noise — $SIVE only ever appeared secondary and
    was the actual supply-chain link;
  * a human decision, once made, is never re-asked.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.x_kol import heat as heat_mod  # noqa: E402

NOW = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
HEAT_CFG = {"half_life_days": 3.0, "primary_weight": 1.0,
            "secondary_weight": 0.4, "surface_min_score": 0.3}


def _rec(tags, *, hours_ago=0, post_id="1", handle="aleabitoreddit"):
    return {
        "post_id": post_id, "handle": handle,
        "created_at": (NOW - timedelta(hours=hours_ago)).isoformat().replace("+00:00", "Z"),
        "cashtags": list(tags), "url": f"https://x.com/{handle}/status/{post_id}",
    }


def test_first_cashtag_outweighs_the_props_it_is_compared_against():
    """The pronunciation joke: $AAOI is the subject, $TSM/$AMD are just syllables."""
    stats = heat_mod.score_tickers([_rec(["AAOI", "TSM", "AMD"])], HEAT_CFG, now=NOW)
    assert stats["AAOI"]["score"] > stats["TSM"]["score"]
    assert stats["TSM"]["score"] == pytest.approx(stats["AMD"]["score"])
    assert stats["AAOI"]["primary_mentions"] == 1
    assert stats["TSM"]["primary_mentions"] == 0


def test_secondary_mentions_are_weighted_down_not_discarded():
    """$SIVE never led a post and was still the real supply-chain link."""
    stats = heat_mod.score_tickers(
        [_rec(["AEVA", "SIVE"]), _rec(["AAOI", "SIVE", "JBL"], post_id="2")],
        HEAT_CFG, now=NOW)
    assert stats["SIVE"]["score"] > 0, "a secondary-only ticker must still surface"
    assert stats["SIVE"]["primary_mentions"] == 0
    assert stats["SIVE"]["mentions"] == 2


def test_recency_decay_favours_the_fresher_mention():
    stats = heat_mod.score_tickers(
        [_rec(["OLD"], hours_ago=72), _rec(["NEW"], hours_ago=0, post_id="2")],
        HEAT_CFG, now=NOW)
    assert stats["NEW"]["score"] > stats["OLD"]["score"]
    # one half-life = 3 days
    assert stats["OLD"]["score"] == pytest.approx(0.5, abs=0.01)


def test_repeat_mentions_accumulate_into_durable_heat():
    once = heat_mod.score_tickers([_rec(["X"])], HEAT_CFG, now=NOW)
    thrice = heat_mod.score_tickers(
        [_rec(["X"], post_id=str(i)) for i in range(3)], HEAT_CFG, now=NOW)
    assert thrice["X"]["score"] > once["X"]["score"]


def test_themes_are_discovered_by_co_mention_not_a_sector_map():
    records = [_rec(["AAOI", "SIVE"]), _rec(["SIVE", "AEVA"], post_id="2"),
               _rec(["RKLB"], post_id="3")]
    stats = heat_mod.score_tickers(records, HEAT_CFG, now=NOW)
    themes = heat_mod.cluster_themes(records, stats)
    members = {frozenset(t["members"]) for t in themes}
    assert frozenset({"AAOI", "SIVE", "AEVA"}) in members, "co-mention must chain transitively"
    assert frozenset({"RKLB"}) in members
    assert themes[0]["score"] >= themes[-1]["score"], "themes ranked by heat"


def test_theme_lead_is_the_hottest_member():
    records = [_rec(["AAOI", "SIVE"]), _rec(["AAOI", "SIVE"], post_id="2")]
    stats = heat_mod.score_tickers(records, HEAT_CFG, now=NOW)
    assert heat_mod.cluster_themes(records, stats)[0]["lead"] == "AAOI"


# ── the human gate ───────────────────────────────────────────────────────
def test_a_decision_is_never_silently_re_asked(tmp_path):
    path = tmp_path / "candidates.json"
    stats = heat_mod.score_tickers([_rec(["AAOI", "TSM"])], HEAT_CFG, now=NOW)
    heat_mod.refresh_candidates(stats, path, surface_min=0.3)
    assert heat_mod.load_candidates(path)["tickers"]["AAOI"]["decision"] == "pending"

    heat_mod.decide(path, "AAOI", "promoted", note="CPO lead")
    heat_mod.decide(path, "TSM", "rejected")

    # later sweeps re-surface the same tickers; the decisions must survive
    heat_mod.refresh_candidates(stats, path, surface_min=0.3)
    tickers = heat_mod.load_candidates(path)["tickers"]
    assert tickers["AAOI"]["decision"] == "promoted"
    assert tickers["AAOI"]["note"] == "CPO lead"
    assert tickers["TSM"]["decision"] == "rejected"


def test_low_score_tickers_do_not_flood_the_queue(tmp_path):
    path = tmp_path / "candidates.json"
    stats = heat_mod.score_tickers([_rec(["HOT", "COLD"], hours_ago=240)], HEAT_CFG, now=NOW)
    heat_mod.refresh_candidates(stats, path, surface_min=0.3)
    assert "COLD" not in heat_mod.load_candidates(path)["tickers"], \
        "a decayed secondary mention is below the surfacing bar"


def test_already_decided_ticker_stays_tracked_even_when_it_cools(tmp_path):
    path = tmp_path / "candidates.json"
    hot = heat_mod.score_tickers([_rec(["AAOI"])], HEAT_CFG, now=NOW)
    heat_mod.refresh_candidates(hot, path, surface_min=0.3)
    heat_mod.decide(path, "AAOI", "promoted")
    cold = heat_mod.score_tickers([_rec(["AAOI"], hours_ago=500)], HEAT_CFG, now=NOW)
    heat_mod.refresh_candidates(cold, path, surface_min=0.3)
    assert heat_mod.load_candidates(path)["tickers"]["AAOI"]["decision"] == "promoted"


def test_unknown_decision_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        heat_mod.decide(tmp_path / "c.json", "AAOI", "maybe_later")


def test_build_tolerates_an_empty_or_missing_log(tmp_path):
    cfg = {"collect": {"shadow_log": "nope.jsonl"}, "heat": HEAT_CFG}
    out = heat_mod.build(cfg, log_path=tmp_path / "nope.jsonl", now=NOW)
    assert out["posts_scanned"] == 0 and out["tickers"] == [] and out["themes"] == []


def test_build_ranks_tickers_and_records_provenance(tmp_path):
    log = tmp_path / "log.jsonl"
    log.write_text("".join(json.dumps(r) + "\n" for r in [
        _rec(["AAOI", "TSM", "AMD"], post_id="p1"),
        _rec(["AEVA", "SIVE"], post_id="p2", hours_ago=6),
    ]), encoding="utf-8")
    cfg = {"collect": {"shadow_log": str(log)}, "heat": HEAT_CFG}
    out = heat_mod.build(cfg, log_path=log, now=NOW)

    assert out["posts_scanned"] == 2
    assert out["tickers"][0]["ticker"] == "AAOI"
    aaoi = out["tickers"][0]
    assert aaoi["posts"][0]["post_id"] == "p1" and aaoi["posts"][0]["primary"] is True
    assert out["prices"] == {} and out["identity_flags"] == {}, "no FMP unless asked"


def test_malformed_lines_do_not_sink_the_table(tmp_path):
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps(_rec(["AAOI"])) + "\n{ broken json\n", encoding="utf-8")
    assert len(heat_mod.load_records(log)) == 1


# ── analysability gate ───────────────────────────────────────────────────
def test_ticker_without_a_price_series_is_marked_unanalyzable():
    """分析 takes every number from FMP by protocol, so no price series means the
    analysis literally cannot run — however good the post was. $SIVE is the real
    case: Sivers Semiconductors prices only as SIVE.ST (no FMP series), and the
    bare SIVE that does price is an unrelated OTC shell."""
    stats = {"AAOI": {}, "SIVE": {}}
    prices = {"AAOI": {"last": 131.35}}
    identity = {"SIVE": {"note": "OTC listing, cap $1,451,835"}}
    blocked = heat_mod.mark_unanalyzable(stats, prices, identity)
    assert "AAOI" not in blocked
    assert "SIVE" in blocked and "OTC" in blocked["SIVE"]


def test_unanalyzable_still_counts_toward_theme_heat():
    """It is evidence about the cluster even though it can never be a position —
    heat and promotion are deliberately different jobs."""
    records = [_rec(["AEVA", "SIVE"]), _rec(["AAOI", "SIVE"], post_id="2")]
    stats = heat_mod.score_tickers(records, HEAT_CFG, now=NOW)
    themes = heat_mod.cluster_themes(records, stats)
    assert stats["SIVE"]["score"] > 0
    assert "SIVE" in themes[0]["members"]

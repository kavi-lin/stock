#!/usr/bin/env python3
"""Focused deterministic tests for the Wind container, gates and budget.

    python3 scripts/wind/test_wind.py

No network, no engine subprocess, no writes outside a temp dir.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.wind import budget as budget_mod  # noqa: E402
from scripts.wind import dispatch as dispatch_mod  # noqa: E402
from scripts.wind import reasoning_adapter as adapter_mod  # noqa: E402
from scripts.wind import terms as terms_mod  # noqa: E402

NOW = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)


def _config():
    return json.loads(json.dumps(budget_mod.load_config()))


# ── normalization ────────────────────────────────────────────────────────
def test_normalize_collapses_spelling_variants():
    # The exact collision observed in bn_20260815_d2e01118.json.
    assert terms_mod.normalize("IP Monetization", "theme") == \
           terms_mod.normalize("IP monetization", "theme")
    assert terms_mod.normalize("  digital   gaming ", "theme") == "digital gaming"
    assert terms_mod.normalize("$aaoi", "ticker") == "AAOI"
    assert terms_mod.normalize("BRK.B", "ticker") == "BRK.B"
    # Prose is not a ticker, however it arrives.
    assert terms_mod.normalize("not a ticker at all", "ticker") is None
    assert terms_mod.normalize("", "theme") is None
    assert terms_mod.normalize(None, "theme") is None


# ── scoring properties ───────────────────────────────────────────────────
def test_surprise_separates_steady_coverage_from_acceleration():
    """A constantly-covered term must not outrank a newly-accelerating one.

    This is the regression that motivated `surprise`: ranking on raw score
    against 14 days of real data returned NVDA / AI capex / SPY / AMZN / MSFT,
    i.e. the permanently-covered mega-caps, every single tick.
    """
    cfg = _config()["heat"]
    half, base = cfg["half_life_days"], cfg["baseline_half_life_days"]
    eps = cfg["surprise_epsilon"]

    def surprise(ages):
        fast = sum(0.5 ** (a / half) for a in ages)
        slow = sum(0.5 ** (a / base) for a in ages)
        return (fast / half) / ((slow / base) + eps)

    steady = surprise([float(d) for d in range(0, 14)])      # mentioned daily
    spiking = surprise([0.1, 0.3, 0.6])                       # only just started
    assert spiking > steady, (spiking, steady)
    # A term covered evenly forever sits near parity, not near zero.
    assert 0.7 < steady < 1.8, steady


def test_decayed_score_prefers_recent_mentions():
    cfg = _config()["heat"]
    half = cfg["half_life_days"]
    fresh = 0.5 ** (0.0 / half)
    stale = 0.5 ** (8.0 / half)
    assert fresh > stale * 8


# ── queue gates ──────────────────────────────────────────────────────────
def _entry(**kw):
    base = {"term": "rcat", "display": "RCAT", "kind": "ticker", "score": 5.0,
            "surprise": 3.0, "mentions": 5, "scan_state": "pending"}
    base.update(kw)
    return base


def test_gates_reject_thin_stopword_and_cold_terms():
    cfg = _config()
    cfg["heat"]["surface_min_score"] = 1.0
    cfg["heat"]["min_mentions"] = 3
    data = {"terms": {
        "ticker:RCAT": _entry(),
        "ticker:SPY": _entry(term="spy", display="SPY", surprise=9.0),   # stop term
        "ticker:IYR": _entry(term="iyr", display="IYR", surprise=9.0, mentions=1),
        "ticker:COLD": _entry(term="cold", display="COLD", surprise=9.0, score=0.2),
        "ticker:BUSY": _entry(term="busy", display="BUSY", surprise=9.0,
                              scan_state="scanning"),
    }}
    keys = [k for k, _ in terms_mod.eligible(data, cfg, now=NOW)]
    assert keys == ["ticker:RCAT"], keys


def test_ranking_is_by_surprise_not_score():
    cfg = _config()
    data = {"terms": {
        "ticker:BIG": _entry(term="big", display="BIG", score=99.0, surprise=1.0),
        "ticker:HOT": _entry(term="hot", display="HOT", score=2.0, surprise=4.0),
    }}
    assert terms_mod.pick_next(data, cfg, now=NOW)[0] == "ticker:HOT"


# ── cooldown ─────────────────────────────────────────────────────────────
def test_cooldown_holds_then_breaks_only_on_real_reacceleration():
    later = (NOW + timedelta(hours=6)).isoformat()
    entry = {"cooldown_until": later, "score_at_scan": 4.0, "score": 4.2}
    assert terms_mod.in_cooldown(entry, rescan_jump=0.5, now=NOW) is True

    # Re-crossing the surface threshold is NOT enough; +50% over the score we
    # already paid to scan is.
    entry["score"] = 6.5
    assert terms_mod.in_cooldown(entry, rescan_jump=0.5, now=NOW) is False

    # Expired cooldown always releases.
    entry = {"cooldown_until": (NOW - timedelta(hours=1)).isoformat(),
             "score_at_scan": 4.0, "score": 0.1}
    assert terms_mod.in_cooldown(entry, rescan_jump=0.5, now=NOW) is False
    assert terms_mod.in_cooldown({}, rescan_jump=0.5, now=NOW) is False


# ── container durability ─────────────────────────────────────────────────
def test_merge_preserves_scan_state_and_stamps_surface_once():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "wind_terms.json"
        stats = {"ticker:RCAT": {"term": "rcat", "display": "RCAT", "kind": "ticker",
                                 "score": 5.0, "baseline": 1.0, "surprise": 3.0,
                                 "mentions": 5, "first_seen": "2026-08-14T00:00:00+00:00",
                                 "last_seen": "2026-08-16T00:00:00+00:00", "sources": []}}
        terms_mod.merge(stats, path, surface_min=1.0, now=NOW)
        terms_mod.set_scan_state(path, "ticker:RCAT", "scanned",
                                 scan_path="news/wind_logs/x.json",
                                 cooldown_hours=24, score_at_scan=5.0)

        first_stamp = terms_mod.load_terms(path)["terms"]["ticker:RCAT"]["first_surfaced_at"]
        assert first_stamp is not None

        # A later rebuild must not reset the scan bookkeeping or restamp the
        # event time the lead-lag evaluation keys on.
        stats["ticker:RCAT"]["score"] = 9.0
        terms_mod.merge(stats, path, surface_min=1.0, now=NOW + timedelta(days=3))
        entry = terms_mod.load_terms(path)["terms"]["ticker:RCAT"]
        assert entry["scan_state"] == "scanned"
        assert entry["score_at_scan"] == 5.0
        assert entry["cooldown_until"] is not None
        assert entry["first_surfaced_at"] == first_stamp
        assert entry["score"] == 9.0

        # A term that decays out of the window is zeroed, not deleted — its
        # first_surfaced_at is evaluation evidence.
        terms_mod.merge({}, path, surface_min=1.0, now=NOW + timedelta(days=9))
        gone = terms_mod.load_terms(path)["terms"]["ticker:RCAT"]
        assert gone["score"] == 0.0 and gone["surprise"] == 0.0
        assert gone["first_surfaced_at"] == first_stamp


# ── budget ───────────────────────────────────────────────────────────────
def test_budget_enforces_usd_and_daily_ceilings():
    cfg = _config()
    cfg["budget"].update({"total_usd": 0.30, "price_per_scan_usd": 0.10, "reserve_usd": 0.0})
    cfg["dispatch"]["max_scans_per_day"] = 2

    with tempfile.TemporaryDirectory() as tmp:
        usage = Path(tmp) / "wind_usage.json"
        assert budget_mod.check(cfg, scans=1, usage_path=usage) == 0.1
        budget_mod.record(cfg, scans=1, usage_path=usage)
        budget_mod.record(cfg, scans=1, usage_path=usage)

        # Daily ceiling bites before the USD ceiling does.
        try:
            budget_mod.check(cfg, scans=1, usage_path=usage)
            raise AssertionError("daily ceiling did not refuse")
        except budget_mod.BudgetExceeded as exc:
            assert "left today" in str(exc), exc
        assert budget_mod.load_ledger(usage)["refusals"] == 1

        # USD ceiling refuses independently of the daily counter.
        cfg["dispatch"]["max_scans_per_day"] = 99
        cfg["budget"]["total_usd"] = 0.20
        try:
            budget_mod.check(cfg, scans=1, usage_path=usage)
            raise AssertionError("usd ceiling did not refuse")
        except budget_mod.BudgetExceeded as exc:
            assert "remaining" in str(exc), exc


# ── post-filter ──────────────────────────────────────────────────────────
def test_relevance_filter_drops_timeline_pollution():
    # Verbatim off-topic items that reached the AAOI report's top-25 clusters
    # because a resolved handle drags its author's whole timeline along.
    assert dispatch_mod._relevance(
        "@RobertKennedyJr Palmer wants to get jacked.", "AAOI", "ticker") == 0.0
    assert dispatch_mod._relevance(
        "THIS ANIME IS BRUTAL DUDE! #animetiktok", "AAOI", "ticker") == 0.0
    assert dispatch_mod._relevance(
        "$AAOI key read-throughs from the Q2 2026 earnings call", "AAOI", "ticker") == 1.0
    # Multi-word themes score by overlap, so a longer phrase still matches.
    assert dispatch_mod._relevance(
        "counter-UAS procurement accelerates", "counter-UAS", "tech_keyword") > 0.5


def test_theme_query_is_anchored_by_co_mentioned_tickers():
    """A theme is not tradeable by itself, so the query must not pretend it is.

    Real case: `Claude` entered the queue from three Anthropic-revenue stories
    filed against AMZN/GOOGL/MSFT/NVDA. `Claude stocks investor discussion`
    searches for a security that does not exist and returns AI-developer
    chatter — the failure that put a 550k-view TikTok about prompting technique
    into an AAOI report.
    """
    claude = {"kind": "tech_keyword", "display": "Claude", "term": "claude",
              "related_tickers": ["AMZN", "GOOGL", "MSFT", "NVDA"]}
    q = dispatch_mod._query_for(claude)
    assert "$AMZN" in q and "$GOOGL" in q and "$MSFT" in q, q
    assert "$NVDA" not in q, "anchors are capped at 3"
    assert "stocks" not in q, q

    # A ticker anchors itself and must not pick up co-mentions.
    assert dispatch_mod._query_for(_entry()) == "$RCAT stock news and investor discussion"

    # No co-mention to anchor on: ask about the theme, do not invent a security.
    orphan = {"kind": "theme", "display": "Consumer Credit", "term": "consumer credit"}
    assert dispatch_mod._query_for(orphan) == "Consumer Credit stock market impact"


def test_co_mentions_are_ticker_validated_and_decayed():
    """Co-mention anchors go through the same ticker normalizer as everything
    else, so prose in an entities list cannot become a `$`-prefixed anchor."""
    assert terms_mod.normalize("AMZN", "ticker") == "AMZN"
    assert terms_mod.normalize("Generative AI", "ticker") is None
    # Only non-ticker terms accumulate anchors; a ticker anchoring itself would
    # duplicate the symbol into its own query.
    stats = terms_mod.score_terms(_config(), now=NOW)
    for slot in stats.values():
        if slot["kind"] == "ticker":
            assert not slot.get("related_tickers"), slot["key"]


def test_engagement_keeps_native_metrics_separate():
    """X reports {likes,replies,reposts}; video platforms report views. Summing
    them into one integer was the first cut and it silently produced 0."""
    cfg = _config()
    payload = {"results": [
        {"title": "$RCAT earnings", "summary": "", "url": "",
         "source": "x", "engagement": {"likes": 98, "replies": 24, "reposts": 5}},
        {"title": "RCAT deep dive", "summary": "", "url": "",
         "source": "youtube", "engagement": {"views": 1200, "likes": 30}},
        {"title": "unrelated anime clip", "summary": "", "url": "",
         "source": "tiktok", "engagement": {"views": 999999}},
    ]}
    art = dispatch_mod.build_artifact(cfg, "ticker:RCAT", _entry(), payload, {"exit_code": 0})
    assert art["filter"]["kept"] == 2 and art["filter"]["dropped"] == 1
    assert art["crowding"]["engagement"] == {"likes": 128, "replies": 24,
                                             "reposts": 5, "views": 1200}


# ── broker-backed reasoning ─────────────────────────────────────────────
def test_reasoning_client_uses_selected_cli_and_fails_closed_on_bad_json():
    calls = []

    def good_runner(agent, prompt, *, assigned_model, timeout):
        calls.append((agent, prompt, assigned_model, timeout))
        return adapter_mod.AgentCall(
            parsed={"intent": "breaking_news"}, raw_text="", exit_code=0,
            latency_ms=125, error=None,
            usage={"input_tokens": 80, "output_tokens": 20, "model_calls": 1},
        )

    client = adapter_mod.BrokerReasoningClient(
        agent="gemini", provider="agy", assigned_model="gemini-test",
        timeout=17, runner=good_runner,
    )
    assert client.generate_json("ignored-upstream-model", "planner prompt") == {
        "intent": "breaking_news"
    }
    assert calls == [("gemini", "planner prompt", "gemini-test", 17)]
    assert client.calls == 1 and client.usage["input_tokens"] == 80

    def bad_runner(*args, **kwargs):
        return adapter_mod.AgentCall(
            parsed=None, raw_text="not json", exit_code=0,
            latency_ms=1, error=None, usage={},
        )

    client.runner = bad_runner
    try:
        client.generate_json("ignored", "rerank prompt")
        raise AssertionError("invalid CLI JSON silently degraded")
    except RuntimeError as exc:
        assert "no valid JSON" in str(exc), exc


def test_reasoning_lease_only_offers_configured_logged_in_agents():
    captured = {}

    class FakeLease:
        provider = "agy"
        model = "gemini-test"
        settled = False

        def start(self, *, model=None):
            captured["started_model"] = model

    class FakeBroker:
        def acquire(self, **fields):
            captured.update(fields)
            return FakeLease()

    config = _config()
    config["dispatch"]["reasoning_agents"] = ["gemini", "codex"]
    with mock.patch.object(adapter_mod.model_router, "load_llm_config", return_value={}), \
         mock.patch.object(adapter_mod.broker_gate, "broker_client", return_value=FakeBroker()):
        lease, agent = adapter_mod.acquire_reasoning_lease(config)

    assert lease.provider == "agy" and agent == "gemini"
    assert captured["preferred_providers"] == ["agy", "codex"]
    assert set(captured["forbidden_providers"]) == {"claude", "grok"}
    assert captured["started_model"] == "gemini-test"
    assert captured["task_type"] == "wind_reasoning"


def test_dispatch_wraps_engine_and_strips_reasoning_api_keys():
    captured = {}
    payload = {"schema_version": "test", "results": [], "window_days": 14}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["env"] = kwargs["env"]
        meta_path = Path(argv[argv.index("--meta-out") + 1])
        meta_path.write_text(json.dumps({
            "route": "broker:agy", "agent": "gemini", "model": "gemini-test",
            "calls": 3, "usage": {"input_tokens": 123}, "ok": True,
        }), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    with tempfile.TemporaryDirectory() as tmp:
        config = _config()
        engine = Path(tmp) / "last30days.py"
        engine.write_text("# fake engine\n", encoding="utf-8")
        config["dispatch"]["engine_path"] = str(engine)
        scratch = Path(tmp) / "raw"
        secret_env = {name: "must-not-reach-child" for name in dispatch_mod._REASONING_API_ENV_VARS}
        with mock.patch.dict(os.environ, secret_env), \
             mock.patch.object(dispatch_mod.subprocess, "run", side_effect=fake_run):
            result, meta = dispatch_mod.run_engine(config, _entry(), scratch=scratch)

    assert result == payload
    assert Path(captured["argv"][1]) == dispatch_mod.REASONING_ADAPTER
    passed_engine = Path(captured["argv"][captured["argv"].index("--engine") + 1])
    assert passed_engine == engine.resolve()
    assert captured["env"]["LAST30DAYS_REASONING_PROVIDER"] == "broker"
    assert all(name not in captured["env"] for name in dispatch_mod._REASONING_API_ENV_VARS)
    assert meta["reasoning"]["route"] == "broker:agy"
    artifact = dispatch_mod.build_artifact(config, "ticker:RCAT", _entry(), result, meta)
    assert artifact["engine"]["reasoning"]["calls"] == 3


def test_adapter_entrypoint_fails_closed_before_engine_when_broker_is_down():
    with tempfile.TemporaryDirectory() as tmp:
        engine = Path(tmp) / "last30days.py"
        engine.write_text("# fake engine\n", encoding="utf-8")
        meta_path = Path(tmp) / "reasoning.json"
        with mock.patch.object(
            adapter_mod, "acquire_reasoning_lease",
            side_effect=RuntimeError("broker unavailable"),
        ), mock.patch.object(adapter_mod, "_run_engine") as engine_run, \
             contextlib.redirect_stderr(io.StringIO()):
            rc = adapter_mod.main([
                "--engine", str(engine), "--meta-out", str(meta_path),
                "--", "test topic",
            ])

        assert rc == 1
        engine_run.assert_not_called()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["route"] == "broker:blocked" and meta["ok"] is False
        assert "broker unavailable" in meta["error"]


def test_language_bucketing_detects_multilingual_spread():
    assert dispatch_mod._script_of("Applied Optoelectronics stock analysis") == "latin"
    assert dispatch_mod._script_of("AAOI 주가 400% 폭등의 진짜 이유") == "korean"
    assert dispatch_mod._script_of("深度拆解AI光模块黑马AAOI") == "cjk"
    assert dispatch_mod._script_of("หุ้น Photonics ได้เวลาหรือยัง") == "thai"
    assert dispatch_mod._script_of("12345 %%%") == "unknown"


# ── daemon heartbeat ─────────────────────────────────────────────────────
def test_heartbeat_merge_keeps_fields_the_caller_did_not_resend():
    """The resident loop writes twice a round and only names what changed.

    Entering the sleep it sets state/next_tick_at; entering the next tick it
    sets state alone. If the write overwrote instead of merging, `started_at`
    and `tick_count` would vanish on the second write and the page would lose
    the daemon's identity between rounds — while still showing a live-looking
    countdown, which is the worst of both.
    """
    with tempfile.TemporaryDirectory() as tmp:
        config = _config()
        config["heat"]["scans_dir"] = tmp

        assert dispatch_mod.read_heartbeat(config) is None   # nothing written yet

        dispatch_mod.write_heartbeat(config, pid=4242, started_at="2026-08-16T10:00:00+00:00",
                                     interval_sec=3600, tick_count=0, state="ticking")
        dispatch_mod.write_heartbeat(config, state="sleeping", tick_count=1,
                                     next_tick_at="2026-08-16T11:04:00+00:00",
                                     last_status="scanned", last_detail="留 8 丟 12")
        hb = dispatch_mod.write_heartbeat(config, state="ticking")

        assert hb["pid"] == 4242                       # survived two later writes
        assert hb["started_at"] == "2026-08-16T10:00:00+00:00"
        assert hb["tick_count"] == 1
        assert hb["state"] == "ticking"
        assert hb["last_detail"] == "留 8 丟 12"
        assert hb == dispatch_mod.read_heartbeat(config)   # what the page reads
        assert hb["written_at"]                            # every write is stamped


def test_heartbeat_is_written_only_by_the_resident_loop():
    """`--once` / `--term` / the dashboard button must leave no heartbeat.

    They are one-shot ticks with no next round. A `next_tick_at` from them
    would render a countdown for a daemon that was never started.
    """
    with tempfile.TemporaryDirectory() as tmp:
        config = _config()
        config["heat"]["scans_dir"] = tmp
        config["heat"]["terms_path"] = str(Path(tmp) / "terms.json")

        dispatch_mod.tick(config, dry_run=True)
        assert dispatch_mod.read_heartbeat(config) is None
        assert not (Path(tmp) / dispatch_mod.HEARTBEAT_NAME).exists()


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    for fn in TESTS:
        fn()
    print(f"wind tests: OK ({len(TESTS)} cases)")

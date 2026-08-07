import json
from datetime import datetime
from pathlib import Path

import pytest

from news.scripts.news_event_store import (
    EventStoreError,
    append_review,
    append_verdict,
    build_projection,
    ingest_digest,
    load_events,
    migrate_digest,
    pending_events,
    rollback,
)
from news.scripts.validate_digest_output import main as validate_digest


# Derived, not hardcoded: validate_digest_output has a freshness gate requiring
# the digest timestamp to be TODAY. A literal date makes these tests pass on the
# day they were written and fail every day after — which is what happened at the
# 2026-08-06 → 08-07 rollover. LOCAL time, not UTC: the validator compares against
# datetime.now() (validate_digest_output.py:269), and in UTC+8 the two disagree
# for eight hours every night.
DATE = datetime.now().strftime("%Y-%m-%d")


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _verdict(status="pending"):
    return {
        "news_id": "n0001", "depth": "deep", "review_status": status,
        "headline": "Material company event", "headline_zh": "重大公司事件",
        "source_label": "Reuters", "source_url": "https://example.com/event?utm_source=x",
        "news_type": "corporate", "source_credibility": "HIGH",
        "published": f"{DATE}T01:00:00Z",
        "bull_case": "bull", "bear_case": "bear", "sector_view": "sector", "macro_view": "macro",
        "verdict": "NEUTRAL", "directional_bias": "NEUTRAL", "net_impact_score": 0.2,
        "arbiter_reasoning": "A sufficiently long deterministic arbiter explanation.",
        "debate_note": "balanced", "binary_risk": False, "binary_event_date": None,
        "within_48h": False, "cache_updated": status == "reviewed",
        "affected_sectors": ["Technology"], "tickers_mentioned": ["AAA"],
        "subagent_isolated": False, "macro_backdrop_delta": 0.1,
        "lane_scores": {"bull": 3, "bear": -2, "sector": 1, "macro": 0},
        "lane_confidences": {"bull": 0.7, "bear": 0.7, "sector": 0.7, "macro": 0.7},
    }


def _cache_setup(root: Path):
    _write(root / "sector/sector_logs/phase0.json", {
        "macro_backdrop_score": 0.0, "news_patch_count": 0,
        "binary_risks": [], "applied_news_event_ids": [],
    })
    _write(root / f"sector/sector_logs/{DATE}_sector_intel.json", {"top_catalysts": []})


def test_flash_append_is_physical_and_projection_idempotent(tmp_path):
    store = tmp_path / "news/news_logs/news_events.jsonl"
    first = append_verdict(_verdict(), event_type="FLASH", date=DATE, root=tmp_path, store_path=store)
    first_projection = (tmp_path / f"news/news_logs/{DATE}_digest.json").read_bytes()
    second = append_verdict(_verdict(), event_type="FLASH", date=DATE, root=tmp_path, store_path=store)

    assert first["appended"] == 1
    assert second["appended"] == 0
    assert len(load_events(store)) == 1
    assert (tmp_path / f"news/news_logs/{DATE}_digest.json").read_bytes() == first_projection
    assert first["record"]["event_id"].startswith("news_")
    assert pending_events(store)[0]["event_id"] == first["record"]["event_id"]


def test_mixed_digest_flash_projection_validates_per_event_mode(tmp_path, monkeypatch):
    store = tmp_path / "news/news_logs/news_events.jsonl"
    digest_verdict = _verdict("reviewed")
    digest_verdict["subagent_isolated"] = True
    digest_verdict["fanout_mode"] = "PER_AGENT_BATCH"
    ingest_digest({
        "timestamp": f"{DATE} 08:00", "mode": "DIGEST", "stage1_count": 1,
        "stage2_count": 1, "fanout_mode": "PER_AGENT_BATCH", "degraded_agents": [],
        "verdicts": [digest_verdict], "session_macro_delta": 0.0,
    }, date=DATE, root=tmp_path, store_path=store)
    flash_verdict = _verdict()
    flash_verdict["news_id"] = "n0002"
    flash_verdict["headline"] = "Separate intraday company event"
    flash_verdict["headline_zh"] = "另一則盤中公司事件"
    flash_verdict["source_url"] = "https://example.com/separate-event"
    appended = append_verdict(
        flash_verdict, event_type="FLASH", date=DATE, root=tmp_path, store_path=store,
    )
    path = tmp_path / f"news/news_logs/{DATE}_digest.json"
    projection = json.loads(path.read_text())

    assert projection["mode"] == "DIGEST"
    assert projection["fanout_mode"] == "PER_AGENT_BATCH"
    assert appended["record"]["event_type"] == "FLASH"
    monkeypatch.delenv("NEWS_RUN_START_MS", raising=False)
    with pytest.raises(SystemExit) as result:
        validate_digest(["--path", str(path)])
    assert result.value.code == 0


def test_invalid_flash_payload_is_rejected_before_append(tmp_path):
    store = tmp_path / "news/news_logs/news_events.jsonl"
    bad = _verdict()
    del bad["published"]
    with pytest.raises(EventStoreError, match="missing text fields"):
        append_verdict(bad, event_type="FLASH", date=DATE, root=tmp_path, store_path=store)
    assert not store.exists()


def test_projection_date_rejects_path_traversal(tmp_path):
    store = tmp_path / "news/news_logs/news_events.jsonl"
    with pytest.raises(EventStoreError, match="YYYY-MM-DD"):
        append_verdict(_verdict(), event_type="FLASH", date="../../tmp", root=tmp_path, store_path=store)


def test_review_supersedes_pending_by_event_id_and_patches_once(tmp_path):
    _cache_setup(tmp_path)
    store = tmp_path / "news/news_logs/news_events.jsonl"
    flash = append_verdict(_verdict(), event_type="FLASH", date=DATE, root=tmp_path, store_path=store)
    event_id = flash["record"]["event_id"]
    reviewed = _verdict("reviewed")
    reviewed["net_impact_score"] = 1.2
    reviewed["verdict"] = "BULLISH"
    reviewed["directional_bias"] = "BULLISH"
    result = append_review(event_id, reviewed, root=tmp_path, store_path=store)

    assert result["appended"] == 1
    assert result["record"]["supersedes_record_id"] == flash["record"]["record_id"]
    assert pending_events(store) == []
    assert result["projection"]["verdicts"][0]["review_status"] == "reviewed"
    assert result["cache"]["new_events"] == 1
    phase0 = json.loads((tmp_path / "sector/sector_logs/phase0.json").read_text())
    assert phase0["applied_news_event_ids"] == [event_id]

    with pytest.raises(EventStoreError, match="not pending"):
        append_review(event_id, reviewed, root=tmp_path, store_path=store)


def _shallow(news_id: str, materiality: float):
    v = _verdict("reviewed")
    v.update({
        "news_id": news_id, "depth": "shallow",
        "headline": f"Shallow item {news_id}", "headline_zh": f"淺層項目 {news_id}",
        "source_url": f"https://example.com/{news_id}",
        "verdict": None, "directional_bias": None,
        "arbiter_reasoning": None, "debate_note": None,
        "net_impact_score": 0.5, "materiality_score": materiality,
    })
    for key in ("lane_scores", "lane_confidences", "source_credibility"):
        v.pop(key, None)
    return v


def _digest_run(timestamp: str, verdicts: list[dict]):
    return {
        "timestamp": timestamp, "mode": "DIGEST", "stage1_count": 50,
        "stage2_count": sum(v["depth"] == "deep" for v in verdicts),
        "fanout_mode": "INLINE", "degraded_agents": [],
        "verdicts": verdicts, "session_macro_delta": 0.0,
    }


def test_multi_run_day_caps_shallow_at_ten_by_materiality(tmp_path, monkeypatch):
    """Two news runs on the same date each contribute their own top-10 shallow.
    latest_by_event_id dedups by event_id, not by run, so the union used to reach
    20 shallow and trip validate_digest_output's >15 gate — which failed the
    premarket chain's phase 1 and stopped sector from ever being enqueued
    (2026-08-06). The projection must re-apply the top-10 cut over the union."""
    store = tmp_path / "news/news_logs/news_events.jsonl"
    deep = _verdict("reviewed")
    # Run 1: shallow ranked 1.0..10.0. Run 2: disjoint items ranked 0.1..1.0,
    # all but one strictly below run 1 — so the survivors are decidable.
    run1 = [deep] + [_shallow(f"n01{i:02d}", float(i + 1)) for i in range(10)]
    run2 = [deep] + [_shallow(f"n02{i:02d}", round(0.1 * (i + 1), 2)) for i in range(10)]
    ingest_digest(_digest_run(f"{DATE} 08:00", run1), date=DATE, root=tmp_path, store_path=store)
    result = ingest_digest(_digest_run(f"{DATE} 20:00", run2), date=DATE, root=tmp_path, store_path=store)

    projection = result["projection"]
    kept = [v for v in projection["verdicts"] if v["depth"] == "shallow"]
    assert len(load_events(store)) == 21, "both runs must stay in the append-only store"
    assert len(kept) == 10, "union of two runs must be re-cut to the top 10"
    assert {v["news_id"] for v in kept} == {f"n01{i:02d}" for i in range(10)}
    assert sum(v["depth"] == "deep" for v in projection["verdicts"]) == 1, "deep is not capped"

    path = tmp_path / f"news/news_logs/{DATE}_digest.json"
    monkeypatch.delenv("NEWS_RUN_START_MS", raising=False)
    with pytest.raises(SystemExit) as exc:
        validate_digest(["--path", str(path)])
    assert exc.value.code == 0


def test_shallow_cap_is_stable_and_order_preserving(tmp_path):
    """Ties (real digests have many identical materiality_scores) must resolve
    deterministically, and survivors must keep their projection slots rather than
    being reshuffled into score order."""
    store = tmp_path / "news/news_logs/news_events.jsonl"
    tied = [_shallow(f"n03{i:02d}", 4.5) for i in range(14)]
    first = ingest_digest(
        _digest_run(f"{DATE} 08:00", [_verdict("reviewed")] + tied),
        date=DATE, root=tmp_path, store_path=store,
    )["projection"]
    kept = [v["news_id"] for v in first["verdicts"] if v["depth"] == "shallow"]
    assert kept == [f"n03{i:02d}" for i in range(10)]

    replay = build_projection(load_events(store), DATE)
    assert [v["news_id"] for v in replay["verdicts"]] == [v["news_id"] for v in first["verdicts"]]


def test_legacy_migration_has_recoverable_rollback(tmp_path):
    store = tmp_path / "news/news_logs/news_events.jsonl"
    digest_path = tmp_path / f"news/news_logs/{DATE}_digest.json"
    legacy = {
        "timestamp": f"{DATE} 09:00", "mode": "FLASH", "stage1_count": 0,
        "stage2_count": 1, "fanout_mode": "INLINE", "degraded_agents": [],
        "verdicts": [_verdict()], "session_macro_delta": 0.0,
    }
    _write(digest_path, legacy)
    result = migrate_digest(digest_path, root=tmp_path, store_path=store)
    assert result["appended"] == 1
    assert json.loads(digest_path.read_text())["event_projection_version"] == 1

    restored = rollback(DATE, root=tmp_path)
    assert json.loads(restored.read_text()) == legacy

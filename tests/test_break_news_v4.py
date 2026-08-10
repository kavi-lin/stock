import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.break_news import debater, poller, prompts
from scripts.nexus import tier1_loaders
from scripts.nexus.build_graph import merge_edges
from scripts.nexus.schema import Edge


def test_universe_loader_accepts_heatmap_dict_list(tmp_path, monkeypatch):
    dash = tmp_path / "Dashboard"
    dash.mkdir()
    (dash / "heatmap_universe.json").write_text(
        json.dumps({"tickers": [{"ticker": "NVDA"}, {"symbol": "AMD"}, "MSFT"]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(debater, "ROOT", tmp_path)

    assert debater._load_universe_tickers() == {"NVDA", "AMD", "MSFT"}


def test_summary_aggregation_confidence_snippets_and_final_take():
    thread = [
        {
            "round": 0,
            "agent_role_label": "Analyst-A (Codex)",
            "parsed": {
                "commentary": "A" * 250,
                "confidence": None,
                "final_take": "早輪低信心",
                "relations": [{"subject": "ticker:TSM", "predicate": "SUPPLIES_TO", "object": "ticker:NVDA"}],
            },
        },
        {
            "round": 1,
            "agent_role_label": "Analyst-B (Gemini)",
            "parsed": {
                "commentary": "B relation evidence",
                "confidence": 0.8,
                "final_take": "高信心判斷",
                "relations": [{"subject": "ticker:TSM", "predicate": "SUPPLIES_TO", "object": "ticker:NVDA"}],
            },
        },
        {
            "round": 2,
            "agent_role_label": "Analyst-A (Codex)",
            "parsed": {
                "commentary": "C relation evidence",
                "confidence": 0.8,
                "final_take": "同信心較晚",
                "relations": [{"subject": "ticker:TSM", "predicate": "SUPPLIES_TO", "object": "ticker:NVDA"}],
            },
        },
        {
            "round": 2,
            "agent_role_label": "Analyst-B (Gemini)",
            "parsed": {
                "commentary": "D relation evidence",
                "confidence": None,
                "relations": [{"subject": "ticker:TSM", "predicate": "SUPPLIES_TO", "object": "ticker:NVDA"}],
            },
        },
    ]

    summary = prompts.build_summary_block(thread)
    rel = summary["merged_relations"][0]

    assert rel["support_count"] == 2
    assert rel["confidence_avg"] == 0.8
    assert len(rel["evidence_snippets"]) == 3
    assert all(len(s) <= 200 for s in rel["evidence_snippets"])
    assert summary["final_take"] == "高信心判斷"
    assert len(summary["final_takes_by_round"]) == 3


def _write_bn(path: Path, news_id: str, rel: dict, *, fetched="2026-08-08T00:00:00Z"):
    path.write_text(
        json.dumps({
            "news_id": news_id,
            "state": "closed",
            "fetched_at": fetched,
            "source": {"url_hash": f"sha1:{news_id}"},
            "headline": news_id,
            "summary": {
                "consensus_verdict": "NEUTRAL",
                "merged_entities": {"tickers": ["TSM", "NVDA"], "sectors": [], "themes": [], "tech_keywords": []},
                "merged_relations": [rel],
            },
        }),
        encoding="utf-8",
    )


def test_direct_edge_gate_and_metadata(tmp_path):
    single = {
        "subject": "ticker:TSM",
        "predicate": "SUPPLIES_TO",
        "object": "ticker:NVDA",
        "support_count": 1,
        "confidence_avg": 0.9,
    }
    _write_bn(tmp_path / "bn_20260521_one.json", "bn_20260521_one", single)
    _, edges = tier1_loaders.load_break_news(
        str(tmp_path), {"TSM", "NVDA"}, enable_direct_edge=True
    )
    assert not [e for e in edges if e.source == "ticker:TSM" and e.target == "ticker:NVDA"]

    supported = dict(single, support_count=2)
    _write_bn(tmp_path / "bn_20260521_two.json", "bn_20260521_two", supported)
    _, edges = tier1_loaders.load_break_news(
        str(tmp_path), {"TSM", "NVDA"}, enable_direct_edge=True
    )
    direct = [e for e in edges if e.source == "ticker:TSM" and e.target == "ticker:NVDA"]

    assert direct
    assert all(e.weight <= 0.15 for e in direct)
    assert all(e.metadata["provisional"] is True for e in direct)
    assert any(e.metadata["support_count"] == 2 for e in direct)
    assert direct[0].to_json()["metadata"]["is_break_news"] is True


def test_edge_metadata_survives_merge_edges():
    edge = Edge(
        source="ticker:TSM",
        target="ticker:NVDA",
        type="SUPPLIES_TO",
        metadata={"provisional": True},
    )

    merged = merge_edges([edge])

    assert merged[0].metadata == {"provisional": True}


def _poll_budget(admission_remaining=3):
    return {
        "admission_remaining": admission_remaining,
        "model_debate_capacity": 10,
        "binding_call_headroom": 20,
        "pending_backlog": 0,
        "estimated_calls_per_debate": 2,
        "reserved_session_calls": 0,
        "emergency_item_limit": 0,
        "emergency_items_remaining": None,
        "break_news_pair": ["claude", "gemini"],
        "model_capacity": {"ok": True},
        "fallback_backed_capacity": False,
        "us_news_window_open": True,
        "hourly_slot": {"hourly_cap": 25, "allowed_this_cycle": admission_remaining},
        "backfill_minutes": 30,
    }


def _rss_item(headline, published_dt, *, fp="event", source="CNBC Top", cred="HIGH"):
    return {
        "headline": headline,
        "raw_summary": "",
        "source": source,
        "source_credibility": cred,
        "source_kind": "publisher",
        "url": f"https://example.test/{fp}",
        "published": published_dt.isoformat(),
        "_dt": published_dt,
        "_fp": fp,
    }


def _raw_pool_entry(headline, published_dt, *, key="pool-key", cred="HIGH"):
    return {
        "key": key,
        "headline": headline,
        "raw_summary": "",
        "source": "CNBC Top",
        "credibility": cred,
        "source_kind": "publisher",
        "url": f"https://example.test/{key}",
        "feed_fingerprint": key,
        "published": published_dt.isoformat(),
        "fetched_at": published_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "news_id": None,
        "is_futu": False,
        "is_social": False,
    }


def _stub_poll_runtime(monkeypatch, items, *, pool=(), admission_remaining=3):
    monkeypatch.setattr(poller, "fetch_fresh_items", lambda _hours: items)
    monkeypatch.setattr(poller.store, "load_seen", lambda: {})
    monkeypatch.setattr(poller.store, "load_raw_stream", lambda: list(pool))
    monkeypatch.setattr(poller, "_count_today", lambda: 0)
    monkeypatch.setattr(
        poller, "_auto_budget_limit",
        lambda *_args, **_kwargs: _poll_budget(admission_remaining),
    )


def test_poller_entry_uses_materiality_not_direction_words(monkeypatch):
    now = datetime.now(timezone.utc)
    item = _rss_item(
        "Apple tests China’s CXMT memory chips for iPhones and MacBooks, WSJ reports",
        now - timedelta(minutes=5),
    )
    _stub_poll_runtime(monkeypatch, [item])

    result = poller.run_once(dry_run=True)

    assert result["items_added"] == 1
    assert result["debate_candidates"] == 1
    assert result["pool_selected"] == 0


def test_poller_entry_rejects_high_credibility_listicle(monkeypatch):
    now = datetime.now(timezone.utc)
    item = _rss_item(
        "Top Wall Street analysts like these 3 stocks for their solid growth potential",
        now - timedelta(minutes=5),
    )
    _stub_poll_runtime(monkeypatch, [item])

    result = poller.run_once(dry_run=True)

    assert result["items_added"] == 0
    assert result["items_gated_out"] == 1


def test_poller_entry_backfills_one_best_quality_item_on_quiet_cycle(monkeypatch):
    now = datetime.now(timezone.utc)
    pool = [
        _raw_pool_entry(
            "Pentagon presses defense firms to build weapons as Iran war depletes stockpiles",
            now - timedelta(hours=1), key="pentagon",
        ),
        _raw_pool_entry(
            "Fed holds rates after inflation report and signals policy path",
            now - timedelta(hours=2), key="fed",
        ),
        _raw_pool_entry(
            "FDA decision on DrugCo treatment due Friday",
            now - timedelta(hours=1), key="low-quality-binary",
        ),
        _raw_pool_entry(
            "What Happens to a Bond ETF's Price When the Fed Cuts Rates -- Using Actual Data",
            now - timedelta(hours=1), key="medium-evergreen", cred="MEDIUM",
        ),
    ]
    _stub_poll_runtime(monkeypatch, [], pool=pool, admission_remaining=5)
    admitted = []
    monkeypatch.setattr(
        poller.store, "init_item",
        lambda **kwargs: admitted.append(kwargs["headline"]) or "bn_test_best",
    )
    monkeypatch.setattr(poller.store, "mark_raw_promoted", lambda *_args: True)
    monkeypatch.setattr(poller.store, "save_raw_stream", lambda _entries: len(pool))
    monkeypatch.setattr(poller.store, "update_state", lambda *_args: None)

    result = poller.run_once(window_hours=6)

    assert result["pool_candidates"] == 2
    assert result["pool_selected"] == 1
    assert result["items_added"] == 1
    assert admitted == ["Fed holds rates after inflation report and signals policy path"]


def test_poller_entry_fresh_candidate_prevents_pool_backfill(monkeypatch):
    now = datetime.now(timezone.utc)
    fresh = _rss_item(
        "Apple tests China’s CXMT memory chips for iPhones and MacBooks, WSJ reports",
        now - timedelta(minutes=5),
    )
    pool = [_raw_pool_entry(
        "Fed holds rates after inflation report and signals policy path",
        now - timedelta(hours=1), key="fed",
    )]
    _stub_poll_runtime(monkeypatch, [fresh], pool=pool)

    result = poller.run_once(window_hours=6, dry_run=True)

    assert result["items_added"] == 1
    assert result["pool_candidates"] == 0
    assert result["pool_selected"] == 0


def test_poller_entry_hourly_capacity_still_binds(monkeypatch):
    now = datetime.now(timezone.utc)
    fresh = _rss_item(
        "Apple tests China’s CXMT memory chips for iPhones and MacBooks, WSJ reports",
        now - timedelta(minutes=5),
    )
    _stub_poll_runtime(monkeypatch, [fresh], admission_remaining=0)

    result = poller.run_once(dry_run=True)

    assert result["items_added"] == 0
    assert result["items_gated_cost"] == 1

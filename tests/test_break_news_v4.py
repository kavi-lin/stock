import json
from pathlib import Path

from scripts.break_news import debater, prompts
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


def _write_bn(path: Path, news_id: str, rel: dict, *, fetched="2026-05-21T00:00:00Z"):
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

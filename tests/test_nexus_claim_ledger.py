import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.nexus import claim_ledger, tier2_regex


ANCHOR = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _write_bn(
    path: Path,
    news_id: str,
    relation: dict,
    *,
    url: str = "https://example.com/story",
    fetched: str = "2026-08-08T00:00:00Z",
) -> None:
    path.write_text(json.dumps({
        "news_id": news_id,
        "state": "closed",
        "fetched_at": fetched,
        "source": {
            "url": url,
            "published": fetched,
            "url_hash": f"sha1:{news_id}",
        },
        "headline": news_id,
        "summary": {"merged_relations": [relation]},
    }), encoding="utf-8")


def _relation(**overrides):
    row = {
        "subject": "ticker:TSM",
        "predicate": "SUPPLIES_TO",
        "object": "ticker:NVDA",
        "support_count": 1,
        "confidence_avg": 0.9,
        "evidence_snippets": ["TSMC supplies advanced silicon to NVIDIA."],
    }
    row.update(overrides)
    return row


def test_canonical_url_removes_tracking_but_keeps_real_query():
    assert claim_ledger.canonical_url(
        "http://WWW.Example.com/a/?utm_source=x&id=7#frag"
    ) == "https://example.com/a?id=7"


def test_agent_agreement_inside_one_article_is_not_independent_evidence(tmp_path):
    _write_bn(
        tmp_path / "bn_one.json",
        "bn_one",
        _relation(support_count=3),
        url="https://example.com/story?utm_source=rss",
    )
    _write_bn(
        tmp_path / "bn_duplicate.json",
        "bn_duplicate",
        _relation(support_count=2),
        url="https://www.example.com/story?src=yahoo",
    )

    records, _ = claim_ledger.build_records(tmp_path, anchor_date=ANCHOR)

    assert len(records) == 1
    assert records[0]["agent_support_max"] == 3
    assert records[0]["source_count"] == 1
    assert records[0]["source_domain_count"] == 1
    assert records[0]["status"] == "provisional"


def test_two_relation_level_sources_on_distinct_domains_are_corroborated(tmp_path):
    rel = _relation(corroborating_sources=[
        "https://reuters.com/technology/tsmc-nvidia",
        "https://investor.nvidia.com/news/tsmc-partnership",
    ])
    _write_bn(tmp_path / "bn_link_digest.json", "bn_link_digest", rel)

    records, quality = claim_ledger.build_records(tmp_path, anchor_date=ANCHOR)

    assert records[0]["status"] == "corroborated"
    assert records[0]["source_count"] == 2
    assert records[0]["source_domain_count"] == 2
    assert quality["counts"]["claims_corroborated"] == 1
    assert not claim_ledger.validate_records(records)


def test_customer_of_is_canonicalized_to_supplier_direction(tmp_path):
    rel = _relation(
        subject="ticker:NVDA",
        predicate="CUSTOMER_OF",
        object="ticker:TSM",
        corroborating_sources=[
            "https://one.example/a",
            "https://two.example/b",
        ],
    )
    _write_bn(tmp_path / "bn_customer.json", "bn_customer", rel)

    records, _ = claim_ledger.build_records(tmp_path, anchor_date=ANCHOR)

    assert (records[0]["subject"], records[0]["predicate"], records[0]["object"]) == (
        "ticker:TSM", "SUPPLIES_TO", "ticker:NVDA"
    )


def test_graph_conversion_only_emits_corroborated_universe_edges(tmp_path):
    rel = _relation(corroborating_sources=[
        "https://one.example/a",
        "https://two.example/b",
    ])
    _write_bn(tmp_path / "bn_ok.json", "bn_ok", rel)
    records, _ = claim_ledger.build_records(tmp_path, anchor_date=ANCHOR)

    nodes, edges = claim_ledger.to_graph(records, {"TSM", "NVDA"})
    assert {n.id for n in nodes} == {"ticker:TSM", "ticker:NVDA"}
    assert len(edges) == 1
    assert edges[0].type == "SUPPLIES_TO"
    assert edges[0].metadata["source_count"] == 2
    assert len(edges[0].metadata["evidence_urls"]) == 2

    assert claim_ledger.to_graph(records, {"TSM"}) == ([], [])


def test_validator_rejects_a_falsely_promoted_single_source_claim(tmp_path):
    _write_bn(tmp_path / "bn_one.json", "bn_one", _relation())
    records, _ = claim_ledger.build_records(tmp_path, anchor_date=ANCHOR)
    records[0]["status"] = "corroborated"

    errors = claim_ledger.validate_records(records)

    assert any("status must be provisional" in error for error in errors)


def test_conflicting_supply_directions_are_reported_and_withheld_from_graph(tmp_path):
    sources = ["https://one.example/a", "https://two.example/b"]
    _write_bn(
        tmp_path / "bn_forward.json", "bn_forward",
        _relation(corroborating_sources=sources),
    )
    _write_bn(
        tmp_path / "bn_reverse.json", "bn_reverse",
        _relation(
            subject="ticker:NVDA", object="ticker:TSM",
            corroborating_sources=["https://three.example/a", "https://four.example/b"],
        ),
    )

    records, quality = claim_ledger.build_records(tmp_path, anchor_date=ANCHOR)
    _, edges = claim_ledger.to_graph(records, {"TSM", "NVDA"})

    assert quality["counts"]["direction_conflicts"] == 1
    assert len(quality["direction_conflicts"][0]["claims"]) == 2
    assert edges == []


def test_tier2_ticker_co_mentions_do_not_become_peer_edges(tmp_path):
    dashboard = tmp_path / "Dashboard"
    reports = tmp_path / "reports"
    dashboard.mkdir()
    reports.mkdir()
    (dashboard / "heatmap_universe.json").write_text(json.dumps({"tickers": [
        {"ticker": "NVDA", "sector": "Technology"},
        {"ticker": "LOW", "sector": "Consumer Cyclical"},
        {"ticker": "PEG", "sector": "Utilities"},
    ]}), encoding="utf-8")
    (reports / "20260808_NVDA.md").write_text(
        "NVDA valuation table also mentions LOW and PEG as unrelated row tokens.",
        encoding="utf-8",
    )
    cfg = {
        "sources": {
            "heatmap_universe": "Dashboard/heatmap_universe.json",
            "reports_dir": "reports",
        },
        "narrative_sector_scope": {},
        "tier2_weights": {"primary_ticker": 1.0},
    }

    nodes, edges = tier2_regex.collect(cfg, tmp_path)

    assert not [edge for edge in edges if edge.type == "PEER_OF"]
    audit = next(n for n in nodes if n.id == "__tier2_audit__")
    assert audit.metadata["counts"]["ticker_co_mention_suppressed"]["rejected_oos"] == 2

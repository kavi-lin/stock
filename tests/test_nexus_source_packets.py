import copy
import json

from scripts.nexus import source_packets


def _draft():
    return {
        "source_topic": {
            "topic_id": "topic:hbm",
            "label": "HBM",
            "tickers": ["MU", "NVDA"],
        },
        "known_gaps": ["foreign_company_coverage_missing"],
        "nodes": [
            {"id": "MU", "ticker": "MU", "layer": "upstream"},
            {"id": "NVDA", "ticker": "NVDA", "layer": "downstream"},
        ],
        "edges": [{
            "from": "MU",
            "to": "NVDA",
            "rel": "SUPPLIES_TO",
            "evidence_level": "corroborated",
            "claim_ids": ["claim:one", "claim:two"],
        }],
        "context_edges": [],
        "evidence": [
            {"source_key": "url:one", "url": "https://one.example/hbm", "headline": "one"},
            {"source_key": "url:two", "url": "https://two.example/hbm", "headline": "two"},
        ],
    }


def _claims():
    return [
        {
            "claim_id": "claim:one",
            "evidence": [{
                "source_key": "url:one",
                "url": "https://one.example/hbm",
                "headline": "one",
                "evidence_snippets": ["Analyst extract describing the reported HBM supply relationship."],
            }],
        },
        {
            "claim_id": "claim:two",
            "evidence": [{
                "source_key": "url:two",
                "url": "https://two.example/hbm",
                "headline": "two",
                "evidence_snippets": ["A second analyst extract describing the same HBM supply relationship."],
            }],
        },
    ]


def test_relation_tier_is_derived_per_edge_and_extracts_are_not_verbatim():
    draft = _draft()
    packet = source_packets.build_packet(
        draft, {claim["claim_id"]: claim for claim in _claims()},
    )

    assert packet["relation_evidence"][0]["packet_evidence_level"] == "corroborated_claim"
    assert packet["quality"]["source_domain_count"] == 2
    assert packet["quality"]["verbatim_excerpt_count"] == 0
    assert all(
        excerpt["provenance"] == "claim_analyst_extract"
        and excerpt["verbatim_page_text"] is False
        for source in packet["sources"] for excerpt in source["excerpts"]
    )


def test_fetch_adds_hashed_page_excerpt_without_storing_full_page():
    draft = _draft()

    def fake_fetch(url, terms, timeout):
        return {
            "status": "fetched",
            "http_status": 200,
            "content_digest": "sha256:page",
            "excerpts": [f"HBM page evidence retrieved directly from {url} for validation."],
        }

    packet = source_packets.build_packet(
        draft, {claim["claim_id"]: claim for claim in _claims()},
        fetch=True, fetch_fn=fake_fetch,
    )

    assert packet["quality"]["fetched_source_count"] == 2
    assert packet["quality"]["verbatim_excerpt_count"] == 2
    assert all("content_digest" in source["retrieval"] for source in packet["sources"])
    assert all(
        any(excerpt["provenance"] == "fetched_page" for excerpt in source["excerpts"])
        for source in packet["sources"]
    )


def test_validator_rejects_excerpt_tampering_and_stale_draft():
    draft = _draft()
    packet = source_packets.build_packet(
        draft, {claim["claim_id"]: claim for claim in _claims()},
    )
    payload = {
        "schema_version": 1,
        "artifact_class": "exploration_only",
        "decision_use": "forbidden",
        "counts": {
            "packets": 1,
            "sources": 2,
            "fetched_sources": 0,
            "verbatim_excerpts": 0,
        },
        "packets": [packet],
    }
    assert not source_packets.validate_payload(payload, {"topic:hbm": draft})

    tampered = copy.deepcopy(payload)
    tampered["packets"][0]["sources"][0]["excerpts"][0]["text"] += " changed"
    tampered["packets"][0]["base_draft_digest"] = "sha256:stale"
    errors = source_packets.validate_payload(tampered, {"topic:hbm": draft})

    assert any("excerpt hash mismatch" in error for error in errors)
    assert any("base_draft_digest mismatch" in error for error in errors)


def test_validator_rejects_excerpt_cited_under_the_wrong_source():
    draft = _draft()
    packet = source_packets.build_packet(
        draft, {claim["claim_id"]: claim for claim in _claims()},
    )
    packet["relation_evidence"][0]["citations"][0]["excerpt_ids"] = [
        packet["sources"][1]["excerpts"][0]["excerpt_id"]
    ]
    payload = {
        "schema_version": 1,
        "artifact_class": "exploration_only",
        "decision_use": "forbidden",
        "counts": {"packets": 1, "sources": 2, "fetched_sources": 0, "verbatim_excerpts": 0},
        "packets": [packet],
    }

    errors = source_packets.validate_payload(payload, {"topic:hbm": draft})

    assert any("excerpt/source mismatch" in error for error in errors)


def test_source_cap_recomputes_relation_evidence_tier():
    draft = _draft()
    claims = {claim["claim_id"]: claim for claim in _claims()}
    old_cap = source_packets.MAX_SOURCES
    source_packets.MAX_SOURCES = 1
    try:
        packet = source_packets.build_packet(draft, claims)
    finally:
        source_packets.MAX_SOURCES = old_cap

    relation = packet["relation_evidence"][0]
    assert relation["source_count"] == 1
    assert relation["packet_evidence_level"] == "single_source_claim"


def test_check_cli_rejects_tampered_artifact(tmp_path):
    draft = _draft()
    packet = source_packets.build_packet(
        draft, {claim["claim_id"]: claim for claim in _claims()},
    )
    packet["sources"][0]["excerpts"][0]["text"] += " tampered"
    drafts_path = tmp_path / "drafts.json"
    output_path = tmp_path / "packets.json"
    drafts_path.write_text(json.dumps({"drafts": [draft]}), encoding="utf-8")
    output_path.write_text(json.dumps({
        "schema_version": 1,
        "artifact_class": "exploration_only",
        "decision_use": "forbidden",
        "counts": {"packets": 1, "sources": 2, "fetched_sources": 0, "verbatim_excerpts": 0},
        "packets": [packet],
    }), encoding="utf-8")

    rc = source_packets.main([
        "--drafts", str(drafts_path), "--output", str(output_path), "--check",
    ])

    assert rc == 1

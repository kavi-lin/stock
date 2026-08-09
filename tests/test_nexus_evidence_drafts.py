import json

from scripts.nexus import evidence_drafts


def _topic_payload():
    candidate = {
        "topic_id": "topic:hbm4",
        "label": "HBM4",
        "state": "validated",
        "score": 82.5,
        "first_seen": "2026-08-01",
        "last_seen": "2026-08-09",
        "source_count": 3,
        "source_domain_count": 2,
        "coverage_status": "new_candidate",
        "tickers": ["MU", "NVDA", "MSFT"],
        "why_now": ["capacity bottleneck"],
        "artifacts": ["break_news:bn_1", "break_news:bn_2"],
        "evidence": [
            {"source_key": "url:1", "url": "https://one.example/a", "domain": "one.example", "published": "2026-08-09", "headline": "one"},
            {"source_key": "url:2", "url": "https://two.example/b", "domain": "two.example", "published": "2026-08-08", "headline": "two"},
            {"source_key": "url:3", "url": "https://one.example/c", "domain": "one.example", "published": "2026-08-07", "headline": "three"},
        ],
        "top_relations": [
            {"subject": "ticker:MU", "predicate": "SUPPLIES_TO", "object": "ticker:NVDA", "mentions": 3},
            {"subject": "ticker:NVDA", "predicate": "SUPPLIES_TO", "object": "ticker:MSFT", "mentions": 2},
            {"subject": "ticker:MU", "predicate": "COMPETES_WITH", "object": "ticker:NVDA", "mentions": 1},
        ],
    }
    return {
        "schema_version": 1,
        "generated_at": "2026-08-09T00:00:00Z",
        "counts": {"new_chain_candidates": 1},
        "new_chain_candidates": [candidate],
    }


def _claims():
    return [{
        "claim_id": "claim:mu_nvda",
        "subject": "ticker:MU",
        "predicate": "SUPPLIES_TO",
        "object": "ticker:NVDA",
        "status": "corroborated",
        "artifacts": ["break_news:bn_1"],
        "evidence": [{"source_key": "url:1"}],
    }]


def test_builds_layered_evidence_only_draft_without_llm_nodes():
    payload = evidence_drafts.build_drafts(_topic_payload(), _claims())
    draft = payload["drafts"][0]

    assert payload["artifact_class"] == "exploration_only"
    assert payload["decision_use"] == "forbidden"
    assert draft["decision_eligible"] is False
    assert {node["ticker"]: node["layer"] for node in draft["nodes"]} == {
        "MSFT": "downstream", "MU": "upstream", "NVDA": "intermediate",
    }
    assert draft["edges"][0]["evidence_level"] == "corroborated"
    assert draft["edges"][1]["evidence_level"] == "topic_context"
    assert draft["context_edges"][0]["rel"] == "COMPETES_WITH"
    assert any("private_and_foreign" in gap for gap in draft["known_gaps"])
    assert not evidence_drafts.validate_payload(payload)


def test_validator_rejects_invented_nodes_and_decision_promotion():
    payload = evidence_drafts.build_drafts(_topic_payload(), _claims())
    draft = payload["drafts"][0]
    draft["decision_eligible"] = True
    draft["nodes"].append({
        "id": "INVENTED", "ticker": "INVENTED", "layer": "upstream",
    })

    errors = evidence_drafts.validate_payload(payload)

    assert any("decision-ineligible" in error for error in errors)
    assert any("nodes not present in source topic" in error for error in errors)


def test_writer_is_validated_and_atomic(tmp_path):
    payload = evidence_drafts.build_drafts(_topic_payload(), _claims())
    output = tmp_path / "drafts.json"

    evidence_drafts.write_payload(output, payload)

    assert json.loads(output.read_text(encoding="utf-8")) == payload
    assert not list(tmp_path.glob(".drafts.json.*"))


def test_dedicated_full_pool_projection_wins_over_display_slice():
    payload = _topic_payload()
    highest_score = payload["new_chain_candidates"][0]
    lower_score = dict(payload["new_chain_candidates"][0])
    lower_score.update({
        "topic_id": "topic:fast_but_weaker",
        "label": "Fast but weaker",
        "score": 40,
        "velocity_ratio": 5,
    })
    payload["new_chain_candidates"] = [lower_score]
    payload["draft_candidates"] = [highest_score]

    result = evidence_drafts.build_drafts(payload, _claims(), limit=1)

    assert result["drafts"][0]["source_topic"]["topic_id"] == "topic:hbm4"

import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.nexus import topic_discovery


ANCHOR = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _write_topic_bn(path: Path, idx: int, domain: str, *, date="2026-08-08"):
    path.write_text(json.dumps({
        "news_id": f"bn_{idx}",
        "state": "closed",
        "fetched_at": f"{date}T00:00:00Z",
        "source": {
            "url": f"https://{domain}/story-{idx}?utm_source=rss",
            "published": f"{date}T00:00:00Z",
        },
        "headline": "HBM4 capacity bottleneck as qualification ramp accelerates",
        "summary": {
            "merged_entities": {
                "tickers": ["MU", "NVDA", "TSM"],
                "themes": ["HBM4"],
                "tech_keywords": ["HBM4"],
            },
            "merged_relations": [{
                "subject": "ticker:MU",
                "predicate": "SUPPLIES_TO",
                "object": "ticker:NVDA",
            }],
            "final_take": "Capacity remains constrained during qualification.",
        },
    }), encoding="utf-8")


def test_three_independent_sources_create_validated_topic(tmp_path):
    _write_topic_bn(tmp_path / "bn_1.json", 1, "reuters.com")
    _write_topic_bn(tmp_path / "bn_2.json", 2, "bloomberg.com")
    _write_topic_bn(tmp_path / "bn_3.json", 3, "reuters.com")

    payload = topic_discovery.build_topics(tmp_path, [], anchor_date=ANCHOR)

    topic = next(t for t in payload["topics"] if t["topic_id"] == "topic:hbm4")
    assert topic["state"] == "validated"
    assert topic["source_count"] == 3
    assert topic["source_domain_count"] == 2
    assert topic["ticker_count"] == 3
    assert topic["structural_relation_count"] == 1
    assert topic["supply_relation_count"] == 1
    assert "bottleneck" in topic["bottleneck_terms"]
    assert any("source velocity" in reason for reason in topic["why_now"])
    assert not topic_discovery.validate_payload(payload)
    assert payload["chain_candidates"][0]["topic_id"] == "topic:hbm4"
    assert payload["new_chain_candidates"][0]["topic_id"] == "topic:hbm4"
    assert payload["draft_candidates"][0]["topic_id"] == "topic:hbm4"


def test_duplicate_url_does_not_promote_topic(tmp_path):
    _write_topic_bn(tmp_path / "bn_1.json", 1, "example.com")
    _write_topic_bn(tmp_path / "bn_2.json", 1, "example.com")

    payload = topic_discovery.build_topics(tmp_path, [], anchor_date=ANCHOR)

    topic = payload["topics"][0]
    assert topic["source_count"] == 1
    assert topic["state"] == "seed"


def test_generic_ai_topic_is_suppressed(tmp_path):
    _write_topic_bn(tmp_path / "bn_1.json", 1, "example.com")
    data = json.loads((tmp_path / "bn_1.json").read_text())
    data["summary"]["merged_entities"] = {
        "tickers": ["NVDA"], "themes": ["AI"], "tech_keywords": []
    }
    (tmp_path / "bn_1.json").write_text(json.dumps(data), encoding="utf-8")

    payload = topic_discovery.build_topics(tmp_path, [], anchor_date=ANCHOR)

    assert payload["topics"] == []


def test_validated_gate_cannot_be_faked():
    payload = {
        "schema_version": 1,
        "chain_candidates": [],
        "topics": [{
            "topic_id": "topic:test",
            "state": "validated",
            "score": 80,
            "source_count": 1,
            "source_domain_count": 1,
            "evidence": [],
        }],
    }

    assert any("does not clear promotion gate" in e for e in topic_discovery.validate_payload(payload))


def test_existing_chain_is_marked_covered_and_removed_from_new_queue(tmp_path):
    news_dir = tmp_path / "news"
    chain_dir = tmp_path / "chains"
    news_dir.mkdir()
    chain_dir.mkdir()
    for idx, domain in enumerate(("one.example", "two.example", "three.example"), 1):
        _write_topic_bn(news_dir / f"bn_{idx}.json", idx, domain)
    (chain_dir / "hbm4.yaml").write_text("theme: HBM4\ntitle: HBM4 Supply Chain\n", encoding="utf-8")

    payload = topic_discovery.build_topics(
        news_dir, [], anchor_date=ANCHOR, supply_chain_dir=chain_dir
    )
    topic = next(t for t in payload["topics"] if t["topic_id"] == "topic:hbm4")

    assert topic["coverage_status"] == "existing_chain"
    assert topic["existing_chain_slug"] == "hbm4"
    assert not [t for t in payload["new_chain_candidates"] if t["topic_id"] == "topic:hbm4"]


def test_supply_relation_survives_top_relation_projection_cap(tmp_path):
    for idx, domain in enumerate(("one.example", "two.example", "three.example"), 1):
        _write_topic_bn(tmp_path / f"bn_{idx}.json", idx, domain)
        data = json.loads((tmp_path / f"bn_{idx}.json").read_text())
        data["summary"]["merged_relations"] = [
            *({
                "subject": f"ticker:C{n:02d}",
                "predicate": "COMPETES_WITH",
                "object": f"ticker:D{n:02d}",
            } for n in range(12)),
            {
                "subject": "ticker:MU",
                "predicate": "SUPPLIES_TO",
                "object": "ticker:NVDA",
            },
        ]
        (tmp_path / f"bn_{idx}.json").write_text(json.dumps(data), encoding="utf-8")

    payload = topic_discovery.build_topics(tmp_path, [], anchor_date=ANCHOR)
    topic = next(t for t in payload["topics"] if t["topic_id"] == "topic:hbm4")

    assert len(topic["top_relations"]) == 10
    assert topic["top_relations"][0]["predicate"] == "SUPPLIES_TO"

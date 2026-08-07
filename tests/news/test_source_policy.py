"""Deterministic tests for RSS source selection and audit metadata."""

import json

from news.fetch_all_news import _dedupe_items, _load_payload
from news.fetch_news_rss import FEEDS
from news.source_policy import infer_source_kind, source_priority


def test_dead_marketwatch_marketpulse_removed():
    names = {name for name, _, _ in FEEDS}
    assert "MarketWatch Mkt" not in names


def test_first_party_feeds_are_present():
    names = {name for name, _, _ in FEEDS}
    assert {
        "SEC Press",
        "FTC Competition",
        "Census Indicators",
        "EIA Press",
    } <= names


def test_source_taxonomy_distinguishes_origin_from_credibility():
    assert infer_source_kind("SEC Press") == "official_regulator"
    assert infer_source_kind("Census Indicators") == "official_macro"
    assert infer_source_kind("SEC EDGAR") == "company_filing"
    assert infer_source_kind("Reuters") == "wire"
    assert infer_source_kind("PR Newswire") == "press_release"
    assert infer_source_kind("Yahoo Finance") == "aggregator"
    assert infer_source_kind("CNBC Top") == "publisher"


def test_original_source_beats_high_credibility_aggregator():
    official = {
        "source": "SEC Press",
        "source_kind": "official_regulator",
        "source_credibility": "HIGH",
    }
    aggregator = {
        "source": "Yahoo Finance",
        "source_kind": "aggregator",
        "source_credibility": "HIGH",
    }
    assert source_priority(official) > source_priority(aggregator)


def test_social_marker_cannot_masquerade_as_unlisted_publisher():
    social = {
        "source": "Reddit r/stocks",
        "source_credibility": "LOW",
        "_social_source": True,
    }
    publisher = {"source": "CNBC Top", "source_credibility": "LOW"}
    assert source_priority(publisher) > source_priority(social)


def test_load_payload_preserves_feed_stats(tmp_path):
    path = tmp_path / "rss.json"
    payload = {
        "feed_stats": [{"feed": "SEC Press", "fetched": 25}],
        "items": [{"headline": "Example"}],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert _load_payload(path) == payload


def test_unified_dedupe_prefers_original_source_for_same_url():
    shared = "https://example.com/story?utm_source=feed"
    items = [
        {
            "headline": "Regulator announces market structure rule",
            "url": shared,
            "source": "Yahoo Finance",
            "source_kind": "aggregator",
            "source_credibility": "HIGH",
        },
        {
            "headline": "SEC publishes final market structure rule",
            "url": "https://example.com/story",
            "source": "SEC Press",
            "source_kind": "official_regulator",
            "source_credibility": "HIGH",
        },
    ]
    assert _dedupe_items(items) == [items[1]]


def test_unified_dedupe_prefers_original_source_for_same_headline():
    items = [
        {
            "headline": "FTC clears proposed IonQ acquisition",
            "url": "https://aggregator.example/ionq",
            "source": "Yahoo Finance",
            "source_kind": "aggregator",
            "source_credibility": "HIGH",
        },
        {
            "headline": "FTC clears proposed IonQ acquisition",
            "url": "https://ftc.example/ionq",
            "source": "FTC Competition",
            "source_kind": "official_regulator",
            "source_credibility": "HIGH",
        },
    ]
    assert _dedupe_items(items) == [items[1]]

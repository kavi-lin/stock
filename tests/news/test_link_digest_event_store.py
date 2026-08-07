import json
from pathlib import Path

from news.scripts.news_event_store import load_events
from scripts.link_digest import build_artifacts


def test_link_digest_appends_event_instead_of_editing_projection(monkeypatch, tmp_path):
    logs = tmp_path / "news/news_logs"
    monkeypatch.setattr(build_artifacts, "ROOT", str(tmp_path))
    monkeypatch.setattr(build_artifacts, "NEWS_LOGS", str(logs))
    judgment = {
        "url": "https://example.com/link-story",
        "headline": "Link story",
        "headline_zh": "連結新聞",
        "source_label": "Example",
        "news_type": "corporate",
        "published": "2026-08-06T01:00:00Z",
        "bull_case": "bull case",
        "bear_case": "bear case",
        "sector_view": "sector view",
        "macro_view": "macro view",
        "verdict": "NEUTRAL",
        "net_impact_score": 0.2,
        "arbiter_reasoning": "A deterministic explanation long enough for the schema.",
        "debate_note": "balanced",
        "binary_risk": False,
        "within_48h": False,
        "affected_sectors": ["Technology"],
    }
    path = build_artifacts.write_digest_verdict(judgment, {"tickers": ["AAA"]}, {})
    projection = json.loads(Path(path).read_text())
    events = load_events(logs / "news_events.jsonl")

    assert len(events) == 1
    assert events[0]["event_type"] == "LINK_DIGEST"
    assert projection["mode"] == "REVIEW"
    assert projection["verdicts"][0]["event_type"] == "LINK_DIGEST"
    assert projection["verdicts"][0]["cache_updated"] is False

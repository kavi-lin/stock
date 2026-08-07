import json
from pathlib import Path

from news.scripts.build_digest_packet import build_packet


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_packet_is_compact_and_excludes_deep_from_shallow(tmp_path):
    verdicts = [
        {
            "news_id": f"n{i:04d}", "headline": f"Headline {i}",
            "url": f"https://example.com/{i}", "materiality_score": 8 - i / 10,
            "raw_summary": "summary", "unused_large_field": "x" * 1000,
        }
        for i in range(15)
    ]
    _write(tmp_path / "news/news_logs/2026-08-06_triage.json", {
        "timestamp": "2026-08-06T09:00:00", "raw_count": 15,
        "shallow_verdicts": verdicts, "stage2_items": verdicts[:3],
        "advanced_count": 3,
    })
    _write(tmp_path / "sector/sector_logs/phase0.json", {
        "macro_backdrop_score": -1.2,
        "binary_risks": list(range(8)),
        "secret_or_large_unused": "do not copy",
    })

    packet = build_packet("2026-08-06", tmp_path)

    assert len(packet["stage2_items"]) == 3
    assert len(packet["shallow_items"]) == 10
    assert packet["triage_stats"]["exported_shallow_count"] == 15
    assert {x["news_id"] for x in packet["stage2_items"]}.isdisjoint(
        {x["news_id"] for x in packet["shallow_items"]}
    )
    assert packet["stage2_items"][0]["url"] == "https://example.com/0"
    assert "unused_large_field" not in packet["stage2_items"][0]
    assert packet["macro_context"]["binary_risks"] == [3, 4, 5, 6, 7]
    assert "secret_or_large_unused" not in packet["macro_context"]


def test_packet_tolerates_missing_optional_context(tmp_path):
    _write(tmp_path / "news/news_logs/2026-08-06_triage.json", {
        "shallow_verdicts": [], "stage2_items": [],
    })
    packet = build_packet("2026-08-06", tmp_path)
    assert packet["macro_context"]["macro_summary"] is None
    assert packet["theme_context"] == {"available": False, "themes": []}

#!/usr/bin/env python3
"""Emit the compact, read-only input packet for News Protocol Stage 2.

This keeps the orchestrating LLM from repeatedly reading triage, phase0 and
theme cache files. Article bodies are intentionally absent; Stage 2 fetches
only the selected URLs.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

TRIAGE_FIELDS = (
    "news_id", "headline", "headline_zh", "source", "source_kind",
    "source_credibility", "effective_credibility", "published", "url",
    "raw_summary", "news_type", "content_genre", "shallow_score",
    "materiality_score", "binary_flag", "bull_case", "bear_case",
    "sector_view", "macro_view",
)
PHASE0_FIELDS = (
    "macro_summary", "market_regime", "macro_backdrop_score",
    "binary_risks", "last_news_update",
)


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"expected object in {path}")
    return data


def _slim_item(item: dict) -> dict:
    return {key: item.get(key) for key in TRIAGE_FIELDS}


def _theme_context(root: Path) -> dict:
    pattern = root / "skills/theme-detector/cache/theme_detector_*.json"
    files = [Path(p) for p in glob.glob(str(pattern))]
    if not files:
        return {"available": False, "themes": []}
    latest = max(files, key=lambda p: p.stat().st_mtime)
    try:
        data = _load_json(latest)
    except ValueError:
        return {"available": False, "themes": []}
    raw_themes = ((data.get("themes") or {}).get("all") or [])
    themes = []
    for theme in raw_themes[:10]:
        if isinstance(theme, dict):
            themes.append({
                key: theme.get(key)
                for key in ("name", "direction", "heat", "stage", "confidence")
            })
    return {"available": True, "source": latest.name, "themes": themes}


def build_packet(date: str, root: Path = ROOT) -> dict:
    triage_path = root / f"news/news_logs/{date}_triage.json"
    triage = _load_json(triage_path)
    all_shallow = [x for x in (triage.get("shallow_verdicts") or []) if isinstance(x, dict)]
    stage2 = [x for x in (triage.get("stage2_items") or []) if isinstance(x, dict)]
    stage2_ids = {x.get("news_id") for x in stage2}
    shallow = [
        x for x in all_shallow if x.get("news_id") not in stage2_ids
    ][:10]

    phase0_path = root / "sector/sector_logs/phase0.json"
    try:
        phase0 = _load_json(phase0_path)
    except ValueError:
        phase0 = {}
    macro = {key: phase0.get(key) for key in PHASE0_FIELDS}
    if isinstance(macro.get("binary_risks"), list):
        macro["binary_risks"] = macro["binary_risks"][-5:]
    triage_stats = {
        key: triage.get(key)
        for key in (
            "raw_count", "items_scored", "items_blocked",
            "items_dedup_dropped", "advanced_count", "blocked_counts",
            "template_dedup_dropped",
        )
    }
    triage_stats["exported_shallow_count"] = len(all_shallow)

    return {
        "packet_version": "NEWS_RUN_PACKET_V1",
        "date": date,
        "triage_timestamp": triage.get("timestamp"),
        "triage_stats": triage_stats,
        "stage2_items": [_slim_item(x) for x in stage2],
        "shallow_items": [_slim_item(x) for x in shallow],
        "macro_context": macro,
        "theme_context": _theme_context(root),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()
    try:
        packet = build_packet(args.date)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    json.dump(packet, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

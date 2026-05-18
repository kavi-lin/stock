#!/usr/bin/env python3
"""V2.20.2 — Phase 0 unified cache reader.

Reads all 5 Phase 0 layer caches (breadth / FTD / market_top / FRED / sentiment)
in one shot, returns single JSON to stdout for sector_protocol Phase 0 to consume.

Replaces 5+ inline `python -c "import json; ..."` bash calls that each cost
1 turn (~3-5s LLM overhead). Single call here = single turn.

Usage:
    python3 sector/scripts/phase0_read_caches.py
    python3 sector/scripts/phase0_read_caches.py --fresh-window-sec 10800  # 3h

Output JSON shape:
    {
      "as_of":  ISO timestamp,
      "fresh_window_sec": int,
      "layers": {
        "breadth":    {"available": bool, "file": str, "age_hr": float, "fresh": bool, "data": {composite, components, trend_summary, key_levels}},
        "ftd":        {"available": bool, ..., "data": {market_state, ftd_timeline, quality_score}},
        "market_top": {"available": bool, ..., "data": {composite, components}},
        "fred":       {"available": bool, ..., "data": {regime_label, regime_confidence, macro_scores, regime_signals slim}},
        "sentiment":  {"available": bool, ..., "data": null | dict}
      },
      "stale_layers":  [list of layer names with age > fresh_window],
      "missing_layers": [list of layer names with no cache file]
    }

Exit codes:
    0 — at least 1 layer available
    1 — all layers missing (sector protocol should abort or fall back to WebSearch)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BREADTH_DIR    = ROOT / "sector" / "breadth_cache"
FTD_DIR        = ROOT / "sector" / "ftd_cache"
MARKET_TOP_DIR = ROOT / "sector" / "market_top_cache"
FRED_CACHE     = ROOT / "skills" / "fred-macro" / "cache" / "fred_latest.json"
SENTIMENT_CACHE_DIR = ROOT / "skills" / "market-sentiment-analyzer" / "cache"


def _latest(pattern_dir: Path, glob_pat: str) -> Path | None:
    files = sorted(pattern_dir.glob(glob_pat), reverse=True)
    # Exclude history aggregate files that aren't single-run snapshots
    files = [f for f in files if "history" not in f.name]
    return files[0] if files else None


def _read_layer(path: Path | None, fresh_window: int, slim_fn=None) -> dict:
    if not path or not path.exists():
        return {"available": False, "file": None, "age_hr": None, "fresh": False, "data": None}
    try:
        with path.open("r", encoding="utf-8") as fp:
            raw = json.load(fp)
    except (OSError, json.JSONDecodeError) as e:
        return {"available": False, "file": str(path), "age_hr": None, "fresh": False,
                "data": None, "error": str(e)[:120]}
    age_sec = time.time() - path.stat().st_mtime
    age_hr = round(age_sec / 3600, 2)
    fresh = age_sec < fresh_window
    data = slim_fn(raw) if slim_fn else raw
    return {
        "available": True,
        "file":  str(path.relative_to(ROOT)),
        "age_hr": age_hr,
        "fresh": fresh,
        "data":  data,
    }


def _slim_breadth(d: dict) -> dict:
    """Keep only fields Phase 0 needs: composite + trend_summary + key_levels."""
    return {
        "composite":     d.get("composite") or {},
        "components":    d.get("components") or {},
        "trend_summary": d.get("trend_summary") or {},
        "key_levels":    d.get("key_levels") or {},
        "metadata":      {"data_date": (d.get("metadata") or {}).get("data_date")},
    }


def _slim_ftd(d: dict) -> dict:
    return {
        "market_state":  d.get("market_state") or {},
        "quality_score": d.get("quality_score") or {},
        "ftd_timeline":  d.get("ftd_timeline") or {},
        "metadata":      {"data_date": (d.get("metadata") or {}).get("data_date")},
    }


def _slim_market_top(d: dict) -> dict:
    return {
        "composite":  d.get("composite") or {},
        "components": d.get("components") or {},
        "metadata":   {"data_date": (d.get("metadata") or {}).get("data_date")},
    }


def _slim_fred(d: dict) -> dict:
    """Match phase_0.md slim shape (11 fields)."""
    rs_raw = d.get("regime_signals")
    rs = rs_raw if isinstance(rs_raw, dict) else {}
    mi_raw = d.get("market_implications")
    mi = mi_raw if isinstance(mi_raw, dict) else {}
    rot_raw = mi.get("sector_rotation")
    rot = rot_raw if isinstance(rot_raw, dict) else {}
    # velocity_highlights from change_velocity (top 3 accelerating/decelerating)
    cv = d.get("change_velocity") or {}
    vel = []
    for series_id, info in (cv.items() if isinstance(cv, dict) else []):
        v = (info or {}).get("velocity")
        if v in ("accelerating", "decelerating"):
            vel.append(f"{series_id}:{v}")
        if len(vel) >= 3:
            break
    return {
        "generated_at":            d.get("generated_at"),
        "regime_label":            d.get("regime_label"),
        "regime_confidence":       d.get("regime_confidence"),
        "macro_scores_composite":  (d.get("macro_scores") or {}).get("composite"),
        "yield_curve_value":       rs.get("yield_curve_value"),
        "yield_curve_inverted":    rs.get("yield_curve_inverted"),
        "credit_stress_elevated":  rs.get("credit_stress_elevated"),
        "financial_stress_above_avg": rs.get("financial_stress_above_avg"),
        "fed_rate_direction":      rs.get("fed_rate_direction"),
        "real_rate_preferred":     rs.get("real_rate_preferred"),
        "sector_rotation_favor":   rot.get("favor") or [],
        "sector_rotation_avoid":   rot.get("avoid") or [],
        "velocity_highlights":     vel,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh-window-sec", type=int, default=10800,
                    help="Cache freshness threshold (default 3h)")
    args = ap.parse_args()

    out = {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fresh_window_sec": args.fresh_window_sec,
        "layers": {},
    }

    out["layers"]["breadth"]    = _read_layer(_latest(BREADTH_DIR,    "market_breadth_2*.json"),
                                              args.fresh_window_sec, _slim_breadth)
    out["layers"]["ftd"]        = _read_layer(_latest(FTD_DIR,        "ftd_detector_*.json"),
                                              args.fresh_window_sec, _slim_ftd)
    out["layers"]["market_top"] = _read_layer(_latest(MARKET_TOP_DIR, "market_top_*.json"),
                                              args.fresh_window_sec, _slim_market_top)
    out["layers"]["fred"]       = _read_layer(FRED_CACHE if FRED_CACHE.exists() else None,
                                              3600, _slim_fred)  # fred has own 1h cache
    # Sentiment is optional (Phase 3 Step 1, not Phase 0); skip from this reader.

    stale = [k for k, v in out["layers"].items() if v.get("available") and not v.get("fresh")]
    missing = [k for k, v in out["layers"].items() if not v.get("available")]
    out["stale_layers"]   = stale
    out["missing_layers"] = missing

    available_count = sum(1 for v in out["layers"].values() if v.get("available"))
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")

    return 0 if available_count >= 1 else 1


if __name__ == "__main__":
    sys.exit(main())

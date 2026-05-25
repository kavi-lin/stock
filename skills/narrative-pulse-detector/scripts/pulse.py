#!/usr/bin/env python3
"""
narrative-pulse-detector — single-ticker CLI entry point.

Usage:
    python3 skills/narrative-pulse-detector/scripts/pulse.py NOK
    python3 skills/narrative-pulse-detector/scripts/pulse.py NOK --no-cache
    python3 skills/narrative-pulse-detector/scripts/pulse.py NOK --json   # stdout only
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Local imports
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from fetch_inputs import fetch_all
from classify_stage import classify, load_weights

CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(ticker: str) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return CACHE_DIR / f"{ticker.upper()}_{today}.json"


def _cache_fresh(path: Path, ttl_hours: int, expected_weights_version: str | None = None) -> bool:
    """Cache is fresh iff file exists, age < TTL, AND weights_version matches.
    Codex review #3 fix: previously only checked mtime; same-day edits to
    `stage_weights.yaml` would still return stale classifications.
    """
    if not path.exists():
        return False
    age_h = (datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 3600
    if age_h >= ttl_hours:
        return False
    if expected_weights_version is None:
        return True
    try:
        with open(path, encoding="utf-8") as f:
            cached = json.load(f)
        return cached.get("weights_version") == expected_weights_version
    except (OSError, json.JSONDecodeError):
        return False


def run(ticker: str, no_cache: bool = False) -> dict:
    ticker = ticker.upper().strip()
    cfg = load_weights()
    cp = _cache_path(ticker)

    expected_wv = cfg.get("weights_version", "v1.0")
    if not no_cache and _cache_fresh(cp, cfg.get("cache_ttl_hours", 4), expected_wv):
        with open(cp, encoding="utf-8") as f:
            return json.load(f)

    # 1) Fetch all inputs
    bundle = fetch_all(ticker)
    components = bundle.get("components", {})

    # Codex review #1 + critical-input gate: OHLCV is the only truly required
    # input. Without it we have no RSI / MA / volume / impulse-day signals at
    # all — fewer than half the stage conditions can ever evaluate True. Skip
    # classify entirely so the cache holds a clear `insufficient_data` verdict
    # instead of a low-confidence guess that downstream consumers might honor.
    ih = bundle.get("input_health") or {}
    if not ih.get("ohlcv_ok"):
        cls = {
            "stage": None,
            "stage_label_zh": "資料不足 (OHLCV 缺失)",
            "stage_label_en": "Insufficient (no OHLCV)",
            "stage_confidence": 0.0,
            "scenarios": [],
            "expected_return_pct": 0.0,
            "expected_return_pct_pre_macro": 0.0,
            "expected_return_pct_base": 0.0,
            "scenario_model_version": "v1.1_declarative",
            "macro_adjustments_applied": [],
            "recommended_action": "insufficient_data",
            "next_warning_condition": f"reason: {bundle.get('reason') or 'unknown OHLCV failure'}",
            "stage_components_triggered": [],
            "all_stage_scores": {},
            "weights_version": cfg.get("weights_version", "v1.0"),
        }
    else:
        # 2) Inject price for target computation
        price = (bundle.get("quote") or {}).get("price")
        if price:
            components["__price_for_target__"] = price

        # 3) Classify
        cls = classify(components, weights_cfg=cfg)
    # Strip internal helper key before persist
    components.pop("__price_for_target__", None)

    # 4) Merge into output bundle
    out = {
        "ticker": ticker,
        "run_at": bundle.get("run_at"),
        "cache_key": f"{ticker}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "data_window": bundle.get("data_window"),
        "quote": bundle.get("quote"),
        "components": components,
        "stage": cls["stage"],
        "stage_label_zh": cls["stage_label_zh"],
        "stage_label_en": cls["stage_label_en"],
        "stage_confidence": cls["stage_confidence"],
        "stage_components_triggered": cls["stage_components_triggered"],
        "scenarios": cls["scenarios"],
        "expected_return_pct": cls["expected_return_pct"],
        "expected_return_pct_pre_macro": cls.get("expected_return_pct_pre_macro"),
        "expected_return_pct_base": cls.get("expected_return_pct_base"),
        "scenario_model_version": cls.get("scenario_model_version"),
        "macro_adjustments_applied": cls.get("macro_adjustments_applied") or [],
        "next_warning_condition": cls.get("next_warning_condition"),
        "recommended_action": cls["recommended_action"],
        "weights_version": cls["weights_version"],
        "input_health": bundle.get("input_health"),
        "all_stage_scores": cls["all_stage_scores"],
        "distribution_detail": bundle.get("distribution_detail", []),
    }

    # 5) Persist cache
    with open(cp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)

    return out


def main():
    ap = argparse.ArgumentParser(description="Narrative Pulse Detector — single ticker")
    ap.add_argument("ticker")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--json", action="store_true", help="Print full JSON to stdout (default: terse one-liner)")
    args = ap.parse_args()

    result = run(args.ticker, no_cache=args.no_cache)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        # Terse: one-liner verdict
        price = (result.get("quote") or {}).get("price") or "?"
        print(
            f"[pulse] {result['ticker']} @ ${price}  "
            f"stage={result['stage']} ({result['stage_label_zh']})  "
            f"conf={result['stage_confidence']}  "
            f"E[R]={result['expected_return_pct']}%  "
            f"action={result['recommended_action']}  "
            f"cache={CACHE_DIR / f'{args.ticker.upper()}_*.json'}",
            file=sys.stderr,
        )
        # Print structured key fields to stdout for piping
        print(json.dumps({
            "ticker": result["ticker"],
            "stage": result["stage"],
            "stage_label_zh": result["stage_label_zh"],
            "stage_confidence": result["stage_confidence"],
            "expected_return_pct": result["expected_return_pct"],
            "recommended_action": result["recommended_action"],
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()

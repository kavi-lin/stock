#!/usr/bin/env python3
"""
narrative-pulse-detector — batch entry (daily_update.sh Step 9).

Pulls universe from:
  1. skills/thematic-screener/data/recommendations/<LATEST>.json — top movers per theme
  2. skills/structural_watchlist/* (if exists) — top 10 by score

For each ticker: runs pulse.run() with cache,collates into Dashboard/narrative_pulse.json.

Usage:
    python3 skills/narrative-pulse-detector/scripts/batch_scan.py
    python3 skills/narrative-pulse-detector/scripts/batch_scan.py --top-n 30 \\
        --output Dashboard/narrative_pulse.json --tickers NOK,AVGO,PLTR
"""
import argparse
import glob
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from pulse import run as pulse_run
from classify_stage import load_weights

REPO_ROOT = Path(__file__).resolve().parents[3]


def collect_universe(top_n: int = 30, explicit: list[str] | None = None) -> list[str]:
    if explicit:
        return [t.upper().strip() for t in explicit if t.strip()]

    tickers: list[str] = []

    # 1) Thematic screener top movers
    rec_dir = REPO_ROOT / "skills/thematic-screener/data/recommendations"
    if rec_dir.is_dir():
        files = sorted(rec_dir.glob("*.json"), reverse=True)
        for fp in files[:1]:  # only newest
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            themes = data.get("themes") or []
            for th in themes:
                movers = th.get("top_movers") or []
                for m in movers:
                    t = m.get("ticker")
                    if t and t not in tickers:
                        tickers.append(t)
            break

    # 2) Structural watchlist (if available)
    sw_paths = [
        REPO_ROOT / "Dashboard" / "data.json",  # contains structural_watchlist key
    ]
    for fp in sw_paths:
        if not fp.exists():
            continue
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        sw = data.get("structural_watchlist") or {}
        for t in (sw.get("tickers") or [])[:10]:
            if isinstance(t, dict):
                t = t.get("ticker")
            if t and t not in tickers:
                tickers.append(t)
        break

    return tickers[:top_n]


def build_rankings(per_ticker: dict) -> dict:
    """Top risk (stage 4-5), top opportunity (stage 1-2), distribution watch."""
    risks = []
    opps = []
    dd_watch = []
    for t, r in per_ticker.items():
        st = r.get("stage")
        if st is None:
            continue
        conf = r.get("stage_confidence", 0)
        if st >= 4:
            risks.append((t, conf, r.get("expected_return_pct", 0)))
        elif st <= 2:
            opps.append((t, conf, r.get("expected_return_pct", 0)))
        # Distribution watch: stage 4 + dd >= 2 (about to flip stage 5)
        if st == 4:
            dd = (r.get("components") or {}).get("distribution_days_25d", 0)
            if dd >= 2:
                dd_watch.append((t, dd))

    risks.sort(key=lambda x: -x[1])      # highest confidence first
    opps.sort(key=lambda x: -x[2])       # highest expected return first
    dd_watch.sort(key=lambda x: -x[1])

    return {
        "top_risk":        [t for t, _, _ in risks[:8]],
        "top_opportunity": [t for t, _, _ in opps[:8]],
        "watch_distribution_imminent": [t for t, _ in dd_watch[:8]],
    }


def main():
    ap = argparse.ArgumentParser(description="Narrative Pulse — batch scan")
    ap.add_argument("--source", default="thematic_screener", help="universe source (info only)")
    ap.add_argument("--top-n", type=int, default=30)
    ap.add_argument("--tickers", default="", help="comma-separated, overrides universe")
    ap.add_argument("--output", default="Dashboard/narrative_pulse.json")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--sleep-between", type=float, default=0.5, help="seconds between tickers (rate limit)")
    args = ap.parse_args()

    explicit = [t.strip() for t in args.tickers.split(",") if t.strip()] if args.tickers else None
    universe = collect_universe(top_n=args.top_n, explicit=explicit)
    if not universe:
        print("[batch_scan] empty universe — nothing to do", file=sys.stderr)
        sys.exit(0)

    print(f"[batch_scan] scanning {len(universe)} tickers: {','.join(universe)}", file=sys.stderr)

    per_ticker = {}
    for i, t in enumerate(universe, 1):
        try:
            r = pulse_run(t, no_cache=args.no_cache)
            per_ticker[t] = {
                "stage": r.get("stage"),
                "stage_label_zh": r.get("stage_label_zh"),
                "stage_confidence": r.get("stage_confidence"),
                "expected_return_pct": r.get("expected_return_pct"),
                "recommended_action": r.get("recommended_action"),
                "scenarios": r.get("scenarios"),
                "next_warning_condition": r.get("next_warning_condition"),
                "components": r.get("components"),
                "quote": r.get("quote"),
            }
            print(f"  [{i}/{len(universe)}] {t} stage={r.get('stage')} E[R]={r.get('expected_return_pct')}%",
                  file=sys.stderr)
        except Exception as e:
            print(f"  [{i}/{len(universe)}] {t} FAILED: {str(e)[:100]}", file=sys.stderr)
            per_ticker[t] = {"error": str(e)[:200]}
        if args.sleep_between > 0 and i < len(universe):
            time.sleep(args.sleep_between)

    # Codex review #5: read weights_version dynamically so Dashboard never
    # shows a stale hardcoded label after stage_weights.yaml is updated.
    weights_cfg = load_weights()
    out = {
        "version": "1.0",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "weights_version": weights_cfg.get("weights_version", "v1.0"),
        "universe": {
            "source": args.source,
            "ticker_count": len(universe),
            "tickers": universe,
        },
        "tickers": per_ticker,
        "ranking": build_rankings(per_ticker),
    }

    output_path = REPO_ROOT / args.output if not Path(args.output).is_absolute() else Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)
    print(f"[batch_scan] wrote {output_path} ({len(per_ticker)} tickers)", file=sys.stderr)


if __name__ == "__main__":
    main()

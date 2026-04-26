#!/usr/bin/env python3
"""
Audit drift checker — scan dual-fetch outputs for systematic provider drift.

A field is "drifting" if abs(diff_pct) exceeds a threshold on >= MIN_HITS
of the last N days. Catches provider methodology gaps, stale caches,
or one-side data corruption.

Usage:
  python3 audit_drift_check.py                       # last 7 days, threshold 5%
  python3 audit_drift_check.py --days 30 --threshold 10
  python3 audit_drift_check.py --output /tmp/drift.md
"""
import sys
import json
import argparse
import datetime
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_audits(days):
    """Walk data/YYYY-MM-DD/*.json from the last N days."""
    today = datetime.date.today()
    samples = []
    for offset in range(days):
        d = today - datetime.timedelta(days=offset)
        day_dir = DATA_DIR / d.isoformat()
        if not day_dir.is_dir():
            continue
        for path in sorted(day_dir.glob("*.json")):
            try:
                bundle = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
            audit = bundle.get("_audit") or {}
            samples.append({
                "date": d.isoformat(),
                "ticker": bundle.get("ticker"),
                "diff": audit.get("diff") or {},
                "fmp_status": audit.get("fmp_status"),
            })
    return samples


def detect_drift(samples, threshold, min_hits):
    """For each (ticker, field), count days where |pct| > threshold."""
    grouped = defaultdict(list)
    for s in samples:
        if s["fmp_status"] != "ok":
            continue
        for k, v in s["diff"].items():
            grouped[(s["ticker"], k)].append(v)
    flagged = []
    for (ticker, field_key), values in grouped.items():
        hits = [v for v in values if abs(v) >= threshold]
        if len(hits) >= min_hits:
            flagged.append({
                "ticker": ticker,
                "field": field_key.replace("_pct", ""),
                "hits": len(hits),
                "samples": len(values),
                "max_abs_pct": max(abs(v) for v in values),
                "avg_pct": sum(values) / len(values),
            })
    flagged.sort(key=lambda x: x["max_abs_pct"], reverse=True)
    return flagged


def render(flagged, days, threshold, min_hits, sample_count):
    lines = [
        f"# Audit Drift Report — last {days} days",
        "",
        f"**Threshold**: |diff| >= {threshold}%",
        f"**Min hits**: {min_hits} days out of {days}",
        f"**Total samples scanned**: {sample_count}",
        "",
    ]
    if not flagged:
        lines.append("No fields exceeded drift criteria.")
        return "\n".join(lines)
    lines += [
        "## Persistent drift",
        "",
        "| Ticker | Field | Hits | Samples | Max \\|diff%\\| | Avg diff% |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for f in flagged:
        lines.append(
            f"| {f['ticker']} | {f['field']} | {f['hits']} | "
            f"{f['samples']} | {f['max_abs_pct']:.2f}% | {f['avg_pct']:+.2f}% |"
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--threshold", type=float, default=5.0)
    ap.add_argument("--min-hits", type=int, default=3,
                    help="Required days exceeding threshold (default 3)")
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    samples = load_audits(args.days)
    flagged = detect_drift(samples, args.threshold, args.min_hits)
    report = render(flagged, args.days, args.threshold,
                    args.min_hits, len(samples))

    if args.output:
        Path(args.output).write_text(report)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()

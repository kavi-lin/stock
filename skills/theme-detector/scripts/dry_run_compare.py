#!/usr/bin/env python3
"""
DRY-RUN: theme-detector industry data — Finviz scrape vs FMP REST.

Outputs side-by-side comparison of perf_1w (rolling 5d) per industry.
Does NOT write themes.yaml or any cache. Pure analysis.

Usage:
    python3 dry_run_compare.py [--out reports/theme_dry_run_<DATE>.md]
"""
from __future__ import annotations
import argparse
import os
import sys
import json
import math
import requests
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "skills" / "theme-detector" / "scripts"))

from finviz_performance_client import get_industry_performance


def _fmp_get(path: str, params: dict, timeout: int = 15):
    key = os.environ.get("FMP_API_KEY", "")
    if not key:
        raise SystemExit("FMP_API_KEY env var missing")
    r = requests.get(
        f"https://financialmodelingprep.com/stable/{path}",
        params={**params, "apikey": key},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def _last_n_business_days(n: int) -> list[str]:
    out, d = [], date.today()
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d -= timedelta(days=1)
    return out


def fmp_industry_rolling(days_back: int = 5) -> dict[str, float]:
    """Returns industry_name -> sum of daily averageChange over last N business days."""
    days = _last_n_business_days(days_back + 1)[1:]  # skip today (likely empty intraday)
    bucket: dict[str, list[float]] = {}
    for d in days:
        try:
            rows = _fmp_get("industry-performance-snapshot", {"date": d}) or []
        except Exception:
            rows = []
        for r in rows:
            ind = r.get("industry")
            chg = r.get("averageChange")
            if ind and chg is not None:
                bucket.setdefault(ind, []).append(float(chg))
    return {ind: round(sum(vals), 4) for ind, vals in bucket.items()}


def normalize(name: str) -> str:
    return (name or "").strip().lower().replace("—", "-").replace("  ", " ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None,
                    help="Write markdown report to this path (default stdout)")
    ap.add_argument("--days-back", type=int, default=5,
                    help="FMP rolling window business days (default 5 ≈ 1w)")
    args = ap.parse_args()

    print("[dry-run] Fetching Finviz industry performance ...", file=sys.stderr)
    finviz = get_industry_performance() or []
    finviz_map = {normalize(r["name"]): r for r in finviz if r.get("name")}
    print(f"[dry-run]   finviz: {len(finviz)} industries", file=sys.stderr)

    print(f"[dry-run] Fetching FMP industry snapshots ({args.days_back}d rolling) ...",
          file=sys.stderr)
    fmp_roll = fmp_industry_rolling(args.days_back)
    fmp_map = {normalize(k): (k, v) for k, v in fmp_roll.items()}
    print(f"[dry-run]   fmp:    {len(fmp_roll)} industries", file=sys.stderr)

    finviz_keys = set(finviz_map.keys())
    fmp_keys = set(fmp_map.keys())
    matched = finviz_keys & fmp_keys
    only_finviz = finviz_keys - fmp_keys
    only_fmp = fmp_keys - finviz_keys

    rows = []
    for k in sorted(matched):
        fz = finviz_map[k]
        fmp_name, fmp_perf = fmp_map[k]
        # Finviz perf_1w in decimal (0.05 = 5%), FMP averageChange in % (1.06 = 1.06%)
        # Normalize both to %
        fz_1w_pct = (fz.get("perf_1w") or 0) * 100.0
        delta = round(fz_1w_pct - fmp_perf, 3)
        rows.append({
            "industry": fz.get("name"),
            "finviz_perf_1w_pct": round(fz_1w_pct, 3),
            "fmp_rolling_pct": fmp_perf,
            "delta_pct": delta,
            "abs_delta_pct": abs(delta),
        })

    rows.sort(key=lambda r: r["abs_delta_pct"], reverse=True)

    # Stats
    deltas = [r["delta_pct"] for r in rows]
    if deltas:
        n = len(deltas)
        mean = sum(deltas) / n
        var = sum((d - mean) ** 2 for d in deltas) / n
        sd = math.sqrt(var)
        large_drift = sum(1 for d in deltas if abs(d) > 2.0)
    else:
        mean = sd = 0; large_drift = 0; n = 0

    md = []
    md.append(f"# theme-detector dry-run: Finviz vs FMP (rolling {args.days_back}d)")
    md.append(f"\n**Date**: {date.today().isoformat()}")
    md.append(f"\n## Coverage\n")
    md.append(f"- Finviz industries: **{len(finviz_keys)}**")
    md.append(f"- FMP industries:    **{len(fmp_keys)}**")
    md.append(f"- Matched (name normalized): **{len(matched)}**")
    md.append(f"- Only in Finviz: **{len(only_finviz)}**")
    md.append(f"- Only in FMP:    **{len(only_fmp)}**\n")

    md.append("## Drift summary (Finviz perf_1w − FMP rolling 5d, both %)\n")
    md.append(f"- Sample size: **{n}**")
    md.append(f"- Mean delta: **{mean:+.3f}%**")
    md.append(f"- Std dev:    **{sd:.3f}%**")
    md.append(f"- Industries with |drift| > 2%: **{large_drift}** / {n}\n")

    md.append("## Top 20 by absolute drift\n")
    md.append("| Industry | Finviz 1w % | FMP roll-5d % | Δ % |")
    md.append("|---|---:|---:|---:|")
    for r in rows[:20]:
        md.append(f"| {r['industry']} | {r['finviz_perf_1w_pct']:+.2f} | "
                  f"{r['fmp_rolling_pct']:+.2f} | {r['delta_pct']:+.2f} |")

    md.append("\n## Bottom 10 (smallest drift = best agreement)\n")
    md.append("| Industry | Finviz 1w % | FMP roll-5d % | Δ % |")
    md.append("|---|---:|---:|---:|")
    for r in rows[-10:]:
        md.append(f"| {r['industry']} | {r['finviz_perf_1w_pct']:+.2f} | "
                  f"{r['fmp_rolling_pct']:+.2f} | {r['delta_pct']:+.2f} |")

    if only_finviz:
        md.append(f"\n## Industries only in Finviz ({len(only_finviz)})\n")
        for k in sorted(only_finviz)[:30]:
            md.append(f"- {finviz_map[k].get('name')}")
        if len(only_finviz) > 30:
            md.append(f"- *(+{len(only_finviz) - 30} more)*")

    if only_fmp:
        md.append(f"\n## Industries only in FMP ({len(only_fmp)})\n")
        for k in sorted(only_fmp)[:30]:
            md.append(f"- {fmp_map[k][0]}")
        if len(only_fmp) > 30:
            md.append(f"- *(+{len(only_fmp) - 30} more)*")

    md.append("\n## Verdict\n")
    coverage_pct = (len(matched) / max(len(finviz_keys), 1)) * 100
    if coverage_pct >= 90 and large_drift / max(n, 1) < 0.15:
        md.append("✅ **GREEN** — name match ≥ 90% and < 15% rows drift > 2%. "
                  "FMP-as-primary migration is low-risk.")
    elif coverage_pct >= 70:
        md.append("🟡 **YELLOW** — significant name mismatch or drift. "
                  "Build mapping table before migration.")
    else:
        md.append("🔴 **RED** — < 70% coverage. Industries differ substantially. "
                  "Migration not recommended without rework.")

    md.append("\n> ⚠️ NOTE: FMP rolling sum ≠ Finviz point-to-point pct. "
              "Some drift is methodological, not data-quality.")

    text = "\n".join(md)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"[dry-run] wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Sector earnings pulse (V1.4 P2 hard-required).

Output: sector/cache/sector_earnings_pulse_<DATE>.json. Hard-fails on FMP error.
詳見 sector/scripts/README.md。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from statistics import mean, median

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sector.lib.date_utils import lookback_window  # noqa: E402
from sector.lib.fmp_client import (  # noqa: E402
    SECTOR_TOP_5,
    SECTOR_UNIVERSE,
    TICKER_TO_SECTOR,
    cache_path,
    fmp_get,
)


def fetch_earnings_window(from_d: str, to_d: str) -> list:
    rows = fmp_get("/stable/earnings-calendar", {"from": from_d, "to": to_d})
    if not isinstance(rows, list):
        sys.exit(f"[ERROR] FMP earnings-calendar non-list response for {from_d}..{to_d}")
    return rows


def aggregate_pulse(rows: list) -> dict:
    by_sector: dict = {sec: {"beats": 0, "misses": 0, "in_line": 0, "surprises": []}
                       for sec in SECTOR_UNIVERSE}

    for r in rows:
        sym = r.get("symbol")
        sec = TICKER_TO_SECTOR.get(sym)
        if not sec:
            continue
        actual = r.get("epsActual")
        est = r.get("epsEstimated")
        if actual is None or est is None:
            continue
        try:
            actual = float(actual)
            est = float(est)
        except (TypeError, ValueError):
            continue
        if est == 0:
            continue

        surprise_pct = (actual - est) / abs(est)
        by_sector[sec]["surprises"].append(surprise_pct)

        # threshold: > +1% beat, < -1% miss, else in-line
        if surprise_pct > 0.01:
            by_sector[sec]["beats"] += 1
        elif surprise_pct < -0.01:
            by_sector[sec]["misses"] += 1
        else:
            by_sector[sec]["in_line"] += 1

    out: dict = {}
    for sec, agg in by_sector.items():
        beats = agg["beats"]
        misses = agg["misses"]
        in_line = agg["in_line"]
        n = beats + misses + in_line
        beat_rate = round(beats / max(beats + misses, 1), 3) if (beats + misses) > 0 else None
        # Cap surprise % at ±100% so a single low-estimate beat (e.g. INTC est 0.019)
        # doesn't dominate the sector average.
        clipped = [max(-1.0, min(1.0, x)) for x in agg["surprises"]]
        surprise_avg = round(mean(clipped), 4) if clipped else None
        out[sec] = {
            "report_count":       n,
            "beats":              beats,
            "misses":             misses,
            "in_line":            in_line,
            "beat_rate_30d":      beat_rate,
            "surprise_score_avg": surprise_avg,
            "analyst_revision_net":         None,
            "analyst_pt_upside_median_pct": None,
            "pt_sample_size":               0,
        }
    return out


def fetch_grades_consensus_for_sectors() -> dict:
    """Best-effort net analyst rating per sector via /stable/grades-consensus on
    SECTOR_TOP_5. Returns {sector: net_int | None}. Soft-fail per ticker."""
    out: dict = {}
    for sec, syms in SECTOR_TOP_5.items():
        net = 0
        seen = 0
        for sym in syms:
            rows = fmp_get(
                "/stable/grades-consensus",
                {"symbol": sym},
                hard_fail=False,
                timeout=10,
            )
            if not isinstance(rows, list) or not rows:
                continue
            row = rows[0]
            try:
                sb = int(row.get("strongBuy") or 0)
                bu = int(row.get("buy") or 0)
                sl = int(row.get("sell") or 0)
                ss = int(row.get("strongSell") or 0)
            except (TypeError, ValueError):
                continue
            net += (sb + bu) - (sl + ss)
            seen += 1
        out[sec] = net if seen > 0 else None
    return out


def fetch_pt_upside_for_sectors() -> dict:
    """Per-sector median analyst PT upside vs current price across SECTOR_TOP_5.

    Returns: {sector: {"median_upside_pct": float | None, "sample_size": int}}.
    Soft-fail per ticker. Single batch call gets all 55 prices.
    """
    all_syms = sorted({s for syms in SECTOR_TOP_5.values() for s in syms})
    quotes = fmp_get(
        "/stable/batch-quote-short",
        {"symbols": ",".join(all_syms)},
        hard_fail=False,
        timeout=15,
    )
    price_by_sym: dict = {}
    if isinstance(quotes, list):
        for q in quotes:
            sym = q.get("symbol")
            try:
                p = float(q.get("price"))
            except (TypeError, ValueError):
                continue
            if sym and p > 0:
                price_by_sym[sym] = p

    out: dict = {}
    for sec, syms in SECTOR_TOP_5.items():
        upsides: list[float] = []
        for sym in syms:
            current = price_by_sym.get(sym)
            if current is None:
                continue
            rows = fmp_get(
                "/stable/price-target-consensus",
                {"symbol": sym},
                hard_fail=False,
                timeout=10,
            )
            if not isinstance(rows, list) or not rows:
                continue
            target = rows[0].get("targetMedian")
            try:
                target = float(target) if target is not None else None
            except (TypeError, ValueError):
                target = None
            if not target or target <= 0:
                continue
            upsides.append((target - current) / current)
        out[sec] = {
            "median_upside_pct": round(median(upsides), 4) if upsides else None,
            "sample_size":      len(upsides),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--lookback-days", type=int, default=30)
    ap.add_argument("--skip-analyst", action="store_true",
                    help="Skip analyst grades-consensus + price-target-consensus passes (saves ~111 calls)")
    ap.add_argument("--skip-grades", action="store_true",
                    help="Alias for --skip-analyst (deprecated)")
    args = ap.parse_args()

    skip_analyst = args.skip_analyst or args.skip_grades

    as_of = args.date
    from_d, _ = lookback_window(as_of, args.lookback_days)

    print(f"[fetch_earnings_pulse] window={from_d}..{as_of}", file=sys.stderr)
    rows = fetch_earnings_window(from_d, as_of)
    print(f"[fetch_earnings_pulse] earnings-calendar rows: {len(rows)}", file=sys.stderr)

    pulse = aggregate_pulse(rows)

    if not skip_analyst:
        print("[fetch_earnings_pulse] fetching grades-consensus for SECTOR_TOP_5...", file=sys.stderr)
        grades = fetch_grades_consensus_for_sectors()
        for sec, net in grades.items():
            if sec in pulse:
                pulse[sec]["analyst_revision_net"] = net

        print("[fetch_earnings_pulse] fetching price-target-consensus for SECTOR_TOP_5...", file=sys.stderr)
        pt = fetch_pt_upside_for_sectors()
        for sec, info in pt.items():
            if sec in pulse:
                pulse[sec]["analyst_pt_upside_median_pct"] = info["median_upside_pct"]
                pulse[sec]["pt_sample_size"] = info["sample_size"]

    payload = {
        "as_of_date": as_of,
        "lookback_days": args.lookback_days,
        "schema_version": "V1.4",
        "universe_size": sum(len(v) for v in SECTOR_UNIVERSE.values()),
        "sectors": pulse,
    }

    out_path = cache_path("sector_earnings_pulse", as_of)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    total_reports = sum(s["report_count"] for s in pulse.values())
    print(f"[fetch_earnings_pulse] wrote {out_path} — "
          f"{len(pulse)} sectors, {total_reports} mega-cap reports in {args.lookback_days}d",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

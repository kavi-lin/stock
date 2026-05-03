"""Sector smart-money signals (V1.4 P3 hard-required).

Output: sector/cache/sector_smart_money_<DATE>.json. Hard-fails on FMP error.
詳見 sector/scripts/README.md (form13f deferral 也在 BACKLOG.md)。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from statistics import median

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sector.lib.date_utils import cutoff_date, latest_complete_13f_quarter  # noqa: E402
from sector.lib.fmp_client import (  # noqa: E402
    SECTOR_UNIVERSE,
    TICKER_TO_SECTOR,
    cache_path,
    fmp_get,
)


def fetch_insider_stats_for_sector(symbols: list) -> dict:
    """Aggregate most-recent-quarter acquired/disposed counts."""
    acquired = 0
    disposed = 0
    sample_size = 0
    for sym in symbols:
        rows = fmp_get("/stable/insider-trading/statistics", {"symbol": sym})
        if not isinstance(rows, list) or not rows:
            continue
        latest = rows[0]
        try:
            a = int(latest.get("acquiredTransactions") or 0)
            d = int(latest.get("disposedTransactions") or 0)
        except (TypeError, ValueError):
            continue
        acquired += a
        disposed += d
        sample_size += 1
    return {"acquired": acquired, "disposed": disposed, "sample_size": sample_size}


def fetch_senate_window(lookback_days: int) -> list:
    cutoff = cutoff_date(lookback_days)
    out = []
    for page in range(0, 10):
        rows = fmp_get("/stable/senate-latest", {"page": page, "limit": 100})
        if not isinstance(rows, list) or not rows:
            break
        out.extend(rows)
        oldest = min((r.get("transactionDate") or "") for r in rows)
        if oldest and oldest < cutoff:
            break
    return out


def aggregate_senate_by_sector(rows: list, lookback_days: int) -> dict:
    cutoff = cutoff_date(lookback_days)
    by_sector: dict = {sec: {"purchases": 0, "sales": 0} for sec in SECTOR_UNIVERSE}
    for r in rows:
        sym = r.get("symbol")
        sec = TICKER_TO_SECTOR.get(sym)
        if not sec:
            continue
        td = r.get("transactionDate") or ""
        if td < cutoff:
            continue
        ttype = (r.get("type") or "").lower()
        if "purchase" in ttype:
            by_sector[sec]["purchases"] += 1
        elif "sale" in ttype:
            by_sector[sec]["sales"] += 1
    return by_sector


def fetch_institutional_summary_for_sector(symbols: list, year: int, quarter: int) -> dict:
    """Aggregate Q-on-Q 13F institutional positions across mega-cap symbols.

    Returns: {holders_qoq_delta_sum, ownership_pct_delta_median, sample_size}.
    Soft-fail per ticker (skip tickers that 4xx or have missing data).
    """
    holders_deltas: list[int] = []
    pct_deltas: list[float] = []
    for sym in symbols:
        rows = fmp_get(
            "/stable/institutional-ownership/symbol-positions-summary",
            {"symbol": sym, "year": year, "quarter": quarter},
            hard_fail=False,
            timeout=10,
        )
        if not isinstance(rows, list) or not rows:
            continue
        row = rows[0]
        try:
            holders_deltas.append(int(row.get("investorsHoldingChange") or 0))
        except (TypeError, ValueError):
            pass
        try:
            pct = row.get("ownershipPercentChange")
            if pct is not None:
                pct_deltas.append(float(pct))
        except (TypeError, ValueError):
            pass
    return {
        "holders_qoq_delta_sum":      sum(holders_deltas) if holders_deltas else None,
        "ownership_pct_delta_median": round(median(pct_deltas), 4) if pct_deltas else None,
        "sample_size":                len(holders_deltas),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--lookback-days", type=int, default=30)
    ap.add_argument("--skip-institutional", action="store_true",
                    help="Skip institutional-ownership Q-on-Q pass (saves ~131 calls)")
    args = ap.parse_args()

    as_of = args.date
    print(f"[fetch_smart_money] as_of={as_of} lookback={args.lookback_days}d", file=sys.stderr)

    print("[fetch_smart_money] fetching insider-trading/statistics for "
          f"{sum(len(v) for v in SECTOR_UNIVERSE.values())} mega-cap tickers...",
          file=sys.stderr)
    insider_by_sector = {}
    for sec, syms in SECTOR_UNIVERSE.items():
        insider_by_sector[sec] = fetch_insider_stats_for_sector(syms)

    print("[fetch_smart_money] fetching senate-latest...", file=sys.stderr)
    senate_rows = fetch_senate_window(args.lookback_days)
    senate_by_sector = aggregate_senate_by_sector(senate_rows, args.lookback_days)

    institutional_quarter = None
    institutional_by_sector: dict = {}
    if not args.skip_institutional:
        year, quarter = latest_complete_13f_quarter(as_of)
        institutional_quarter = f"{year}Q{quarter}"
        print(f"[fetch_smart_money] fetching institutional-ownership Q-on-Q ({institutional_quarter})...",
              file=sys.stderr)
        for sec, syms in SECTOR_UNIVERSE.items():
            institutional_by_sector[sec] = fetch_institutional_summary_for_sector(syms, year, quarter)

    sectors_out: dict = {}
    for sec in SECTOR_UNIVERSE:
        ins = insider_by_sector.get(sec, {})
        a = ins.get("acquired", 0)
        d = ins.get("disposed", 0)
        # < 0.5 = bearish, > 1.0 = bullish; 99.99 sentinel = all-acquired with no disposals
        ratio = round(a / d, 3) if d > 0 else (None if a == 0 else 99.99)

        sen = senate_by_sector.get(sec, {})
        purchases = sen.get("purchases", 0)
        sales = sen.get("sales", 0)
        net_buy = purchases - sales

        inst = institutional_by_sector.get(sec, {})

        sectors_out[sec] = {
            "insider_acquired_q":              a,
            "insider_disposed_q":              d,
            "insider_acquired_disposed_ratio_q": ratio,
            "insider_sample_size":             ins.get("sample_size", 0),
            "senate_purchases_30d":            purchases,
            "senate_sales_30d":                sales,
            "senate_net_buy_30d":              net_buy,
            "institutional_holders_qoq_delta": inst.get("holders_qoq_delta_sum"),
            "institutional_ownership_pct_delta": inst.get("ownership_pct_delta_median"),
            "institutional_sample_size":       inst.get("sample_size", 0),
            "form13f_top10_delta":             None,
        }

    payload = {
        "as_of_date":              as_of,
        "schema_version":          "V1.4",
        "lookback_days":           args.lookback_days,
        "universe_size":           sum(len(v) for v in SECTOR_UNIVERSE.values()),
        "senate_rows_in_window":   len(senate_rows),
        "institutional_quarter":   institutional_quarter,
        "sectors":                 sectors_out,
    }

    out_path = cache_path("sector_smart_money", as_of)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"[fetch_smart_money] wrote {out_path} — {len(sectors_out)} sectors",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

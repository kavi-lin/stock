"""Sector valuation fetcher (V1.4 hard-required).

Output: sector/cache/sector_valuation_<DATE>.json. Hard-fails on FMP error.
詳見 sector/scripts/README.md。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from statistics import mean, pstdev

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sector.lib.fmp_client import cache_path, fmp_get  # noqa: E402

FMP_TO_PROJECT = {
    "Basic Materials":        "Materials",
    "Communication Services": "Communication",
    "Consumer Cyclical":      "Consumer_Discretionary",
    "Consumer Defensive":     "Consumer_Staples",
    "Energy":                 "Energy",
    "Financial Services":     "Financials",
    "Healthcare":             "Healthcare",
    "Industrials":            "Industrials",
    "Real Estate":            "Real_Estate",
    "Technology":             "Technology",
    "Utilities":              "Utilities",
}

SECTOR_ETF = {
    "Technology":             "XLK",
    "Healthcare":              "XLV",
    "Energy":                  "XLE",
    "Financials":              "XLF",
    "Consumer_Discretionary":  "XLY",
    "Consumer_Staples":        "XLP",
    "Industrials":             "XLI",
    "Materials":               "XLB",
    "Utilities":               "XLU",
    "Real_Estate":             "XLRE",
    "Communication":           "XLC",
}

EXCHANGES = ["NASDAQ", "NYSE"]


def fetch_pe_snapshot(d: str) -> dict:
    out: dict = {v: {} for v in FMP_TO_PROJECT.values()}
    for exch in EXCHANGES:
        rows = fmp_get("/stable/sector-pe-snapshot", {"date": d, "exchange": exch}, timeout=15)
        if not isinstance(rows, list) or not rows:
            sys.exit(f"[ERROR] FMP sector-pe-snapshot returned empty for {d}/{exch}")
        for row in rows:
            proj = FMP_TO_PROJECT.get(row.get("sector"))
            if proj:
                out[proj][exch] = float(row["pe"])
    return out


def fetch_pe_history(from_d: str, to_d: str) -> dict:
    out: dict = {v: {"NASDAQ": [], "NYSE": []} for v in FMP_TO_PROJECT.values()}
    for fmp_name, proj in FMP_TO_PROJECT.items():
        for exch in EXCHANGES:
            rows = fmp_get(
                "/stable/historical-sector-pe",
                {"sector": fmp_name, "from": from_d, "to": to_d, "exchange": exch},
                timeout=15,
            )
            if not isinstance(rows, list) or not rows:
                sys.exit(f"[ERROR] FMP historical-sector-pe empty for {fmp_name}/{exch}")
            out[proj][exch] = [float(r["pe"]) for r in rows if r.get("pe") is not None]
    return out


def fetch_eod_chart(symbol: str, from_d: str, to_d: str) -> list:
    rows = fmp_get(
        "/stable/historical-price-eod/light",
        {"symbol": symbol, "from": from_d, "to": to_d},
        timeout=15,
    )
    if not isinstance(rows, list) or not rows:
        sys.exit(f"[ERROR] FMP historical-price-eod/light empty for {symbol}")
    return sorted(rows, key=lambda r: r["date"])


def compute_zscore(current: float, history: list[float]) -> float | None:
    if not history or len(history) < 30:
        return None
    mu = mean(history)
    sd = pstdev(history)
    if sd == 0:
        return 0.0
    return round((current - mu) / sd, 3)


def compute_3m_return(rows: list) -> float | None:
    # 3M ≈ 63 trading days. Falls back to longest available if shorter.
    if not rows or len(rows) < 30:
        return None
    end = float(rows[-1]["price"])
    idx = max(0, len(rows) - 64)
    start = float(rows[idx]["price"])
    if start == 0:
        return None
    return round(end / start - 1, 4)


def compute_n_day_return(rows: list, n: int) -> float | None:
    """N-trading-day return; None if fewer than n+1 rows available."""
    if not rows or len(rows) < n + 1:
        return None
    end = float(rows[-1]["price"])
    start = float(rows[-(n + 1)]["price"])
    if start == 0:
        return None
    return round(end / start - 1, 4)


def compute_volume_ratio_20d(rows: list) -> float | None:
    if not rows or len(rows) < 21:
        return None
    today_vol = float(rows[-1]["volume"])
    avg_20 = mean(float(r["volume"]) for r in rows[-21:-1])
    if avg_20 == 0:
        return None
    return round(today_vol / avg_20, 3)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()

    as_of = args.date
    one_year_ago = (datetime.strptime(as_of, "%Y-%m-%d").date() - timedelta(days=400)).isoformat()
    three_m_ago = (datetime.strptime(as_of, "%Y-%m-%d").date() - timedelta(days=120)).isoformat()

    print(f"[fetch_sector_valuation] as_of={as_of}", file=sys.stderr)

    pe_snap = fetch_pe_snapshot(as_of)
    pe_hist = fetch_pe_history(one_year_ago, as_of)

    spy_chart = fetch_eod_chart("SPY", three_m_ago, as_of)
    spy_3m_ret = compute_3m_return(spy_chart)
    if spy_3m_ret is None:
        sys.exit("[ERROR] Could not compute SPY 3M return — insufficient EOD bars")
    spy_5d_ret = compute_n_day_return(spy_chart, 5)
    spy_20d_ret = compute_n_day_return(spy_chart, 20)

    sectors_out: dict = {}
    for proj_name, etf in SECTOR_ETF.items():
        snap = pe_snap.get(proj_name, {})
        nasdaq_pe = snap.get("NASDAQ")
        nyse_pe = snap.get("NYSE")
        pe_avg = mean([v for v in (nasdaq_pe, nyse_pe) if v is not None]) if (nasdaq_pe or nyse_pe) else None

        hist = pe_hist.get(proj_name, {})
        z_nasdaq = compute_zscore(nasdaq_pe, hist.get("NASDAQ", [])) if nasdaq_pe is not None else None
        z_nyse = compute_zscore(nyse_pe, hist.get("NYSE", [])) if nyse_pe is not None else None
        zs = [z for z in (z_nasdaq, z_nyse) if z is not None]
        pe_z = round(mean(zs), 3) if zs else None

        etf_chart = fetch_eod_chart(etf, three_m_ago, as_of)
        etf_3m_ret = compute_3m_return(etf_chart)
        rs_vs_spy = round(etf_3m_ret - spy_3m_ret, 4) if etf_3m_ret is not None else None
        etf_5d_ret = compute_n_day_return(etf_chart, 5)
        rs_vs_spy_5d = (round(etf_5d_ret - spy_5d_ret, 4)
                        if (etf_5d_ret is not None and spy_5d_ret is not None) else None)
        etf_20d_ret = compute_n_day_return(etf_chart, 20)
        rs_vs_spy_20d = (round(etf_20d_ret - spy_20d_ret, 4)
                         if (etf_20d_ret is not None and spy_20d_ret is not None) else None)
        vol_ratio = compute_volume_ratio_20d(etf_chart)

        sectors_out[proj_name] = {
            "etf": etf,
            "pe_ttm_nasdaq": round(nasdaq_pe, 2) if nasdaq_pe is not None else None,
            "pe_ttm_nyse":   round(nyse_pe, 2) if nyse_pe is not None else None,
            "pe_ttm":        round(pe_avg, 2) if pe_avg is not None else None,
            "pe_zscore_1y":  pe_z,
            "rs_vs_spy_3m":  rs_vs_spy,
            "rs_vs_spy_20d": rs_vs_spy_20d,
            "rs_vs_spy_5d":  rs_vs_spy_5d,
            "etf_volume_ratio_20d": vol_ratio,
        }

    payload = {
        "as_of_date": as_of,
        "schema_version": "V1.4",
        "spy_3m_return": spy_3m_ret,
        "sectors": sectors_out,
    }

    out_path = cache_path("sector_valuation", as_of)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"[fetch_sector_valuation] wrote {out_path} — {len(sectors_out)} sectors", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

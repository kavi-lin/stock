"""
Sector Valuation Fetcher (V1.4 hard-required)

Pulls per-sector PE TTM, 1y PE z-score, RS vs SPY 3M, ETF 20d volume ratio
via FMP HTTP REST (FMP MCP is the design reference; HTTP is the runtime path
because Python scripts cannot call MCP tools directly).

Output: sector/cache/sector_valuation_<DATE>.json

Hard fail (sys.exit(1)) on any FMP error per V1.4 protocol decision —
no graceful fallback. Fix MCP/API key and re-run.

Usage:
    python3 sector/scripts/fetch_sector_valuation.py [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from statistics import mean, pstdev

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "sector", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# FMP "sector" string → project canonical sector name
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

# Project sector → SPDR ETF
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
FMP_BASE = "https://financialmodelingprep.com"


def _fmp_get(path: str, params: dict, *, retries: int = 2, timeout: int = 15):
    """GET with light retry. Hard-fail on persistent error."""
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        sys.exit("[ERROR] FMP_API_KEY not set — sector valuation cannot be computed.")
    url = f"{FMP_BASE}{path}"
    full = {**params, "apikey": api_key}
    last_exc = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=full, timeout=timeout)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_exc = e
            time.sleep(0.5)
    sys.exit(f"[ERROR] FMP {path} failed after {retries+1} tries: {last_exc}")


def fetch_pe_snapshot(d: str) -> dict:
    """Returns {project_sector: {'NASDAQ': pe, 'NYSE': pe}}."""
    out: dict = {v: {} for v in FMP_TO_PROJECT.values()}
    for exch in EXCHANGES:
        rows = _fmp_get("/stable/sector-pe-snapshot", {"date": d, "exchange": exch})
        if not isinstance(rows, list) or not rows:
            sys.exit(f"[ERROR] FMP sector-pe-snapshot returned empty for {d}/{exch}")
        for row in rows:
            proj = FMP_TO_PROJECT.get(row.get("sector"))
            if proj:
                out[proj][exch] = float(row["pe"])
    return out


def fetch_pe_history(from_d: str, to_d: str) -> dict:
    """Returns {project_sector: {'NASDAQ': [pe...], 'NYSE': [pe...]}} (1y daily)."""
    out: dict = {v: {"NASDAQ": [], "NYSE": []} for v in FMP_TO_PROJECT.values()}
    for fmp_name, proj in FMP_TO_PROJECT.items():
        for exch in EXCHANGES:
            rows = _fmp_get(
                "/stable/historical-sector-pe",
                {"sector": fmp_name, "from": from_d, "to": to_d, "exchange": exch},
            )
            if not isinstance(rows, list) or not rows:
                sys.exit(f"[ERROR] FMP historical-sector-pe empty for {fmp_name}/{exch}")
            out[proj][exch] = [float(r["pe"]) for r in rows if r.get("pe") is not None]
    return out


def fetch_eod_chart(symbol: str, from_d: str, to_d: str) -> list:
    """Returns list of {'date','price','volume'} sorted oldest→newest."""
    rows = _fmp_get(
        "/stable/historical-price-eod/light",
        {"symbol": symbol, "from": from_d, "to": to_d},
    )
    if not isinstance(rows, list) or not rows:
        sys.exit(f"[ERROR] FMP historical-price-eod/light empty for {symbol}")
    rows = sorted(rows, key=lambda r: r["date"])
    return rows


def compute_zscore(current: float, history: list[float]) -> float | None:
    if not history or len(history) < 30:
        return None
    mu = mean(history)
    sd = pstdev(history)
    if sd == 0:
        return 0.0
    return round((current - mu) / sd, 3)


def compute_3m_return(rows: list) -> float | None:
    """3M ≈ 63 trading days. Falls back to longest available if shorter."""
    if not rows or len(rows) < 30:
        return None
    end = float(rows[-1]["price"])
    idx = max(0, len(rows) - 64)  # 63 bars back ≈ today's close vs 63d ago
    start = float(rows[idx]["price"])
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

    # 1) Current PE snapshot (2 calls: NASDAQ + NYSE)
    pe_snap = fetch_pe_snapshot(as_of)

    # 2) 1y PE history (22 calls: 11 sectors × 2 exchanges)
    pe_hist = fetch_pe_history(one_year_ago, as_of)

    # 3) ETF + SPY 3M EOD (12 calls)
    spy_chart = fetch_eod_chart("SPY", three_m_ago, as_of)
    spy_3m_ret = compute_3m_return(spy_chart)
    if spy_3m_ret is None:
        sys.exit("[ERROR] Could not compute SPY 3M return — insufficient EOD bars")

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
        vol_ratio = compute_volume_ratio_20d(etf_chart)

        sectors_out[proj_name] = {
            "etf": etf,
            "pe_ttm_nasdaq": round(nasdaq_pe, 2) if nasdaq_pe is not None else None,
            "pe_ttm_nyse":   round(nyse_pe, 2) if nyse_pe is not None else None,
            "pe_ttm":        round(pe_avg, 2) if pe_avg is not None else None,
            "pe_zscore_1y":  pe_z,
            "rs_vs_spy_3m":  rs_vs_spy,
            "etf_volume_ratio_20d": vol_ratio,
        }

    payload = {
        "as_of_date": as_of,
        "schema_version": "V1.4",
        "spy_3m_return": spy_3m_ret,
        "sectors": sectors_out,
    }

    out_path = os.path.join(CACHE_DIR, f"sector_valuation_{as_of}.json")
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"[fetch_sector_valuation] wrote {out_path} — {len(sectors_out)} sectors", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

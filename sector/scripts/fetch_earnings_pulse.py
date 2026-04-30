"""
Sector Earnings Pulse Fetcher (V1.4 P2 hard-required)

Aggregates last-30d EPS beat/miss + surprise across mega-cap members of each sector
via FMP /stable/earnings-calendar. Writes per-sector pulse to:
  sector/cache/sector_earnings_pulse_<DATE>.json

Hard fail (sys.exit(1)) on FMP error per V1.4 protocol.

Note: V1.4 P2 ships with `beat_rate_30d` + `surprise_score_avg` only.
`analyst_revision_net` deferred (per-ticker historical-grades cost too high
on free FMP tier). Future work: integrate `mcp__fmp__analyst grades-summary`
batch when paid plan / cache layer added.

Universe: hardcoded mega-cap members per project sector (covers SPDR sector ETF
top holdings; ~75 tickers total). Other sectors' tickers in the 30d window are
ignored — small-cap noise would distort the beat rate.

Usage:
    python3 sector/scripts/fetch_earnings_pulse.py [--date YYYY-MM-DD] [--lookback-days 30]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from statistics import mean

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(BASE_DIR, "sector", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

FMP_BASE = "https://financialmodelingprep.com"

# Mega-cap universe per project sector (SPDR ETF top-10ish + obvious peers).
# Designed to capture earnings sentiment for the sector without small-cap noise.
SECTOR_UNIVERSE = {
    "Technology":             ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "ADBE",
                                "AMD", "INTC", "CSCO", "IBM", "QCOM", "TXN", "NOW", "INTU", "AMAT"],
    "Healthcare":             ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "PFE",
                                "DHR", "BMY", "AMGN", "ELV", "GILD"],
    "Energy":                 ["XOM", "CVX", "COP", "EOG", "SLB", "OXY", "PXD", "PSX",
                                "MPC", "VLO", "KMI", "WMB"],
    "Financials":             ["BRK-B", "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK",
                                "SCHW", "AXP", "SPGI", "PGR", "CB"],
    "Consumer_Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "TJX", "SBUX",
                                "BKNG", "CMG", "F", "GM"],
    "Consumer_Staples":       ["PG", "COST", "KO", "PEP", "WMT", "PM", "MO", "MDLZ",
                                "CL", "KMB", "GIS", "TGT"],
    "Industrials":            ["GE", "CAT", "RTX", "HON", "UNP", "BA", "LMT", "DE",
                                "UPS", "ETN", "ADP", "MMM"],
    "Materials":              ["LIN", "SHW", "FCX", "APD", "ECL", "NEM", "DOW", "DD",
                                "NUE", "PPG"],
    "Utilities":              ["NEE", "SO", "DUK", "AEP", "SRE", "D", "EXC", "XEL",
                                "PCG", "WEC"],
    "Real_Estate":            ["PLD", "AMT", "EQIX", "WELL", "CCI", "PSA", "SPG", "O",
                                "DLR", "EXR"],
    "Communication":          ["GOOGL", "GOOG", "META", "NFLX", "DIS", "CMCSA", "TMUS",
                                "VZ", "T", "CHTR", "WBD"],
}

# Build reverse lookup ticker → sector
TICKER_TO_SECTOR: dict = {}
for sec, syms in SECTOR_UNIVERSE.items():
    for s in syms:
        TICKER_TO_SECTOR[s] = sec


def _fmp_get(path: str, params: dict, *, retries: int = 2, timeout: int = 20):
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        sys.exit("[ERROR] FMP_API_KEY not set — earnings pulse cannot be computed.")
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


def fetch_earnings_window(from_d: str, to_d: str) -> list:
    rows = _fmp_get("/stable/earnings-calendar", {"from": from_d, "to": to_d})
    if not isinstance(rows, list):
        sys.exit(f"[ERROR] FMP earnings-calendar non-list response for {from_d}..{to_d}")
    return rows


def aggregate_pulse(rows: list) -> dict:
    """Return {sector: {beat_rate_30d, surprise_score_avg, report_count, beats, misses, in_line}}."""
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
            continue  # cannot compute surprise%

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
            "beat_rate_30d":      beat_rate,        # beats / (beats + misses)
            "surprise_score_avg": surprise_avg,     # mean of (actual - est)/|est|
            "analyst_revision_net": None,           # V1.4 P2.5 future work
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--lookback-days", type=int, default=30)
    args = ap.parse_args()

    as_of = args.date
    from_d = (datetime.strptime(as_of, "%Y-%m-%d").date() - timedelta(days=args.lookback_days)).isoformat()

    print(f"[fetch_earnings_pulse] window={from_d}..{as_of}", file=sys.stderr)
    rows = fetch_earnings_window(from_d, as_of)
    print(f"[fetch_earnings_pulse] earnings-calendar rows: {len(rows)}", file=sys.stderr)

    pulse = aggregate_pulse(rows)

    payload = {
        "as_of_date": as_of,
        "lookback_days": args.lookback_days,
        "schema_version": "V1.4",
        "universe_size": sum(len(v) for v in SECTOR_UNIVERSE.values()),
        "sectors": pulse,
    }

    out_path = os.path.join(CACHE_DIR, f"sector_earnings_pulse_{as_of}.json")
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    total_reports = sum(s["report_count"] for s in pulse.values())
    print(f"[fetch_earnings_pulse] wrote {out_path} — "
          f"{len(pulse)} sectors, {total_reports} mega-cap reports in {args.lookback_days}d",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

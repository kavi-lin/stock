#!/usr/bin/env python3
"""
Dual-fetch tool — pull canonical fields from Finnhub (scoring) + FMP (audit).

Output structure enforces physical separation:
  - "scoring": Finnhub-sourced values, intended for LLM context / scoring inputs
  - "_audit":  FMP-sourced values + cross-provider diff, NEVER passed to LLM

Discipline: downstream code MAY ONLY read scoring.*. The leading underscore
on _audit is a python-style "private" flag for code review and grep.

Usage:
  python3 dual_fetch.py --tickers AAPL,MSFT
  python3 dual_fetch.py --tickers AAPL --output-dir /tmp
  python3 dual_fetch.py --no-cache

As library:
  from dual_fetch import fetch_dual
  bundle = fetch_dual("AAPL", finnhub_client, fmp_key)
  # bundle["scoring"]  -> pass to LLM
  # bundle["_audit"]   -> log/audit only
"""
import os
import sys
import json
import argparse
import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests library not found. pip install requests", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from finnhub_client import FinnhubClient, FinnhubError
import adapters

DEFAULT_TICKERS = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMD",
    "META", "JPM", "XOM", "SPY", "QQQ",
]
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CANONICAL_FIELDS = [
    "price", "previousClose", "dayHigh", "dayLow",
    "mktCap", "peRatio", "epsTTM",
    "dividendYield", "priceToBookRatio",
]


def fetch_finnhub(ticker, client):
    """Tier 1 / scoring source."""
    out = {"_source": "finnhub"}
    try:
        q = adapters.quote_to_fmp(client.quote(ticker), ticker)
        if q:
            qd = q[0]
            out["price"] = qd.get("price")
            out["previousClose"] = qd.get("previousClose")
            out["dayHigh"] = qd.get("dayHigh")
            out["dayLow"] = qd.get("dayLow")
    except FinnhubError as e:
        print(f"WARN: Finnhub quote {ticker}: {e}", file=sys.stderr)

    try:
        prof = adapters.profile_to_fmp(client.profile(ticker))
        if prof:
            out["mktCap"] = prof.get("mktCap")
    except FinnhubError as e:
        print(f"WARN: Finnhub profile {ticker}: {e}", file=sys.stderr)

    try:
        km = adapters.metric_to_fmp_key_metrics(client.metric(ticker))
        if km:
            m = km[0]
            out["peRatio"] = m.get("peRatio")
            out["epsTTM"] = m.get("epsTTM")
            out["dividendYield"] = m.get("dividendYield")
            out["priceToBookRatio"] = m.get("priceToBookRatio")
    except FinnhubError as e:
        print(f"WARN: Finnhub metric {ticker}: {e}", file=sys.stderr)

    return out


def fetch_fmp(ticker, api_key, session):
    """Audit-only source. Returns (data_dict, status_str)."""
    out = {"_source": "fmp"}
    base = "https://financialmodelingprep.com/stable"
    status = "ok"

    def _get(path, params=None):
        nonlocal status
        params = dict(params or {})
        params["apikey"] = api_key
        try:
            r = session.get(f"{base}/{path}", params=params, timeout=30)
            if r.status_code == 402:
                status = "quota_exceeded"
                return None
            if r.status_code in (401, 403):
                status = "unauthorized"
                return None
            if r.status_code != 200:
                status = f"http_{r.status_code}"
                return None
            return r.json()
        except requests.exceptions.RequestException:
            status = "network_error"
            return None

    q = _get("quote", {"symbol": ticker})
    if isinstance(q, list) and q:
        out["price"] = q[0].get("price")
        out["previousClose"] = q[0].get("previousClose")
        out["dayHigh"] = q[0].get("dayHigh")
        out["dayLow"] = q[0].get("dayLow")
        out["mktCap"] = q[0].get("marketCap")

    rt = _get("ratios-ttm", {"symbol": ticker, "limit": 1})
    if isinstance(rt, list) and rt:
        m = rt[0]
        if m.get("priceToEarningsRatioTTM") is not None:
            out["peRatio"] = m["priceToEarningsRatioTTM"]
        if m.get("priceToBookRatioTTM") is not None:
            out["priceToBookRatio"] = m["priceToBookRatioTTM"]
        if m.get("netIncomePerShareTTM") is not None:
            out["epsTTM"] = m["netIncomePerShareTTM"]
        # FMP returns decimal (0.0038); Finnhub returns percent (0.38). Scale to match.
        if m.get("dividendYieldTTM") is not None:
            out["dividendYield"] = m["dividendYieldTTM"] * 100

    return out, status


def compute_diff(scoring, fmp):
    """Per-field % diff (fmp relative to finnhub/scoring)."""
    out = {}
    for f in CANONICAL_FIELDS:
        s = scoring.get(f)
        fv = fmp.get(f)
        if s is None or fv is None:
            continue
        try:
            s_n = float(s)
            f_n = float(fv)
        except (TypeError, ValueError):
            continue
        if s_n == 0:
            continue
        out[f"{f}_pct"] = (f_n - s_n) / abs(s_n) * 100
    return out


def fetch_dual(ticker, finnhub_client, fmp_api_key, fmp_session=None):
    """
    Library entrypoint.

    Returns a bundle dict where scoring.* is safe to pass to LLM and
    _audit.* is for human / drift-checker consumption only.
    """
    if fmp_session is None:
        fmp_session = requests.Session()
    scoring = fetch_finnhub(ticker, finnhub_client)
    fmp_data, fmp_status = fetch_fmp(ticker, fmp_api_key, fmp_session)
    diff = compute_diff(scoring, fmp_data) if fmp_status == "ok" else {}
    return {
        "ticker": ticker.upper(),
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        "scoring": scoring,
        "_audit": {
            "fmp": fmp_data,
            "diff": diff,
            "fmp_status": fmp_status,
        },
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--tickers", default=",".join(DEFAULT_TICKERS),
                    help="Comma-separated tickers (default: 10 reference tickers)")
    ap.add_argument("--output-dir", default=None,
                    help="Override default data/YYYY-MM-DD/ output dir")
    ap.add_argument("--no-cache", action="store_true",
                    help="Bypass Finnhub local cache (always live)")
    args = ap.parse_args()

    fmp_key = os.getenv("FMP_API_KEY")
    if not fmp_key:
        print("ERROR: FMP_API_KEY not set (audit side disabled)", file=sys.stderr)
        sys.exit(2)

    try:
        client = FinnhubClient(use_cache=not args.no_cache)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    fmp_session = requests.Session()
    when = datetime.date.today()
    out_dir = Path(args.output_dir) if args.output_dir else (
        DATA_DIR / when.isoformat()
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    for t in tickers:
        print(f"... {t}", file=sys.stderr)
        bundle = fetch_dual(t, client, fmp_key, fmp_session)
        path = out_dir / f"{t}.json"
        path.write_text(json.dumps(bundle, indent=2, default=str))

    print(f"\nWrote {len(tickers)} files to {out_dir}", file=sys.stderr)
    print(f"Finnhub stats: {client.stats()}", file=sys.stderr)


if __name__ == "__main__":
    main()

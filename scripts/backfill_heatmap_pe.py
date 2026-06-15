#!/usr/bin/env python3
"""V3.25.2 — one-off backfill for Dashboard/heatmap.json valuation fields.

The dashboard_server runs `_heatmap_refresh_pe_universe()` exactly once on
startup, with a 24h TTL. When the server has been up for days without a
restart (or the warm-up errored mid-run), the PE / EV-EBITDA / forward-EPS
fields end up `null` for every ticker. Downstream consumers (bridge.py
momentum-screen joiner, /api/heatmap/data) then surface "—" everywhere.

This script does the same fetch as the server daemon but out-of-band:
parallel-fetch ratios-ttm + key-metrics-ttm + analyst-estimates per ticker,
write the values back into heatmap.json in place. After running, re-run
bridge.py to rebuild Dashboard/data.json so the momentum table picks the
P/E up immediately. The next dashboard_server start will repopulate its
in-memory cache from heatmap.json on startup.

Usage:
    python3 scripts/backfill_heatmap_pe.py                    # full universe
    python3 scripts/backfill_heatmap_pe.py --limit 50         # smoke run
    python3 scripts/backfill_heatmap_pe.py --workers 20       # tune pool
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

try:
    import requests
except ImportError:
    sys.exit("[backfill_heatmap_pe] requests missing — pip install requests")

REPO_ROOT  = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
HEATMAP    = os.path.join(REPO_ROOT, "Dashboard", "heatmap.json")
FMP_BASE   = "https://financialmodelingprep.com/stable"


def _safe_round(v, n=2):
    try:
        return round(float(v), n) if v is not None else None
    except (TypeError, ValueError):
        return None


def fetch_valuation(ticker: str, api_key: str, timeout: int = 12) -> dict:
    """Mirror dashboard_server._fetch_pe_ttm — returns pe_ttm + ev_ebitda + fwd_eps."""
    out = {"pe_ttm": None, "ev_ebitda": None, "fwd_eps": None}
    try:
        r = requests.get(f"{FMP_BASE}/ratios-ttm",
                         params={"symbol": ticker, "apikey": api_key},
                         timeout=timeout)
        if r.ok:
            rows = r.json() or []
            if isinstance(rows, list) and rows:
                out["pe_ttm"] = _safe_round(rows[0].get("priceToEarningsRatioTTM"), 2)
    except Exception:
        pass
    try:
        r = requests.get(f"{FMP_BASE}/key-metrics-ttm",
                         params={"symbol": ticker, "apikey": api_key},
                         timeout=timeout)
        if r.ok:
            rows = r.json() or []
            if isinstance(rows, list) and rows:
                out["ev_ebitda"] = _safe_round(rows[0].get("evToEBITDATTM"), 2)
    except Exception:
        pass
    try:
        r = requests.get(f"{FMP_BASE}/analyst-estimates",
                         params={"symbol": ticker, "period": "annual",
                                 "limit": 4, "apikey": api_key},
                         timeout=timeout)
        if r.ok:
            rows = r.json() or []
            if isinstance(rows, list) and rows:
                today_iso = date.today().isoformat()
                future = sorted(
                    [r for r in rows if (r.get("date") or "") > today_iso],
                    key=lambda r: r.get("date") or "",
                )
                if future:
                    out["fwd_eps"] = _safe_round(future[0].get("epsAvg"), 4)
    except Exception:
        pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=15)
    ap.add_argument("--limit", type=int, default=None,
                    help="Cap tickers (smoke / partial backfill)")
    args = ap.parse_args()

    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        sys.exit("[backfill_heatmap_pe] FMP_API_KEY not set")

    if not os.path.exists(HEATMAP):
        sys.exit(f"[backfill_heatmap_pe] not found: {HEATMAP}")

    with open(HEATMAP, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    tickers = data.get("tickers") or []
    if not tickers:
        sys.exit("[backfill_heatmap_pe] heatmap.json has no tickers")

    todo = tickers[: args.limit] if args.limit else tickers
    syms = [t.get("ticker") for t in todo if t.get("ticker")]
    print(f"[backfill_heatmap_pe] fetching {len(syms)} tickers "
          f"(workers={args.workers})")

    t0 = time.time()
    results = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_valuation, s, api_key): s for s in syms}
        done = 0
        for fut in as_completed(futs):
            sym = futs[fut]
            try:
                results[sym] = fut.result()
            except Exception:
                results[sym] = {"pe_ttm": None, "ev_ebitda": None, "fwd_eps": None}
            done += 1
            if done % 50 == 0 or done == len(syms):
                elapsed = int(time.time() - t0)
                print(f"[backfill_heatmap_pe] {done}/{len(syms)} ({elapsed}s)")

    # Patch heatmap.json in place. forward_pe = price / fwd_eps (mirrors the
    # live computation in dashboard_server's quote refresh).
    filled_pe = filled_fwd = filled_ev = 0
    for row in tickers:
        sym = row.get("ticker")
        if sym not in results:
            continue
        v = results[sym]
        if v.get("pe_ttm") is not None:
            row["pe"] = v["pe_ttm"]; filled_pe += 1
        if v.get("ev_ebitda") is not None:
            row["ev_ebitda"] = v["ev_ebitda"]; filled_ev += 1
        if v.get("fwd_eps") is not None:
            price = row.get("price") or row.get("last_price")
            try:
                if price and v["fwd_eps"]:
                    row["forward_pe"] = _safe_round(float(price) / float(v["fwd_eps"]), 2)
                    filled_fwd += 1
            except (TypeError, ValueError, ZeroDivisionError):
                pass

    # Atomic write
    tmp = HEATMAP + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False)
    os.replace(tmp, HEATMAP)

    elapsed = int(time.time() - t0)
    print(f"[backfill_heatmap_pe] done in {elapsed}s — "
          f"pe={filled_pe}/{len(syms)}, fwd_pe={filled_fwd}, ev_ebitda={filled_ev}")
    print(f"[backfill_heatmap_pe] next step: python3 bridge.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

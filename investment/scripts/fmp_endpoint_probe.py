#!/usr/bin/env python3
"""
FMP Endpoint Probe — gate decisions for FMP_強化分析 P3/P4 features.

Probes endpoints reported as "uncertain free vs paid" in FMP_強化分析.md
Section 4 + 5 against AAPL. Records HTTP status + sample size to
investment/fmp_probe_<DATE>.json so subsequent bumps can read result.

NO secrets are written; only field names + counts.

Run: python3 investment/scripts/fmp_endpoint_probe.py
"""
from __future__ import annotations
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent.parent
OUT_DIR = BASE / "investment"
OUT_DIR.mkdir(exist_ok=True, parents=True)

TICKER = "AAPL"

# (path, params, label, blocker_class)
_TODAY_PARAM = date.today().isoformat()

PROBES = [
    ("financial-scores",                  {"symbol": TICKER}, "altman_z + piotroski_f", "P0"),
    ("owner-earnings",                    {"symbol": TICKER}, "buffett owner earnings", "P0"),
    ("insider-trading/statistics",        {"symbol": TICKER, "limit": 4}, "insider quarterly stats", "P1"),
    ("institutional-ownership/symbol-positions-summary",
                                          {"symbol": TICKER, "year": 2025, "quarter": 4},
                                          "institutional QoQ", "P2"),
    ("senate-trades",                     {"symbol": TICKER}, "senate trades", "P3"),
    ("house-trades",                      {"symbol": TICKER}, "house trades", "P3"),
    ("mergers-acquisitions-latest",       {"limit": 5},   "M&A latest", "P3"),
    ("sec-filings-8k",                    {"symbol": TICKER, "limit": 5}, "8-K filings", "P2"),
    ("news/stock",                        {"symbols": TICKER, "limit": 5}, "FMP stock news", "P2"),
    ("news/press-releases",               {"symbol": TICKER, "limit": 5}, "press releases", "P2"),
    ("industry-performance-snapshot",     {"date": _TODAY_PARAM}, "industry perf snapshot", "P1"),
    ("historical-industry-performance",   {"industry": "Software", "from": "2026-01-01"},
                                          "industry perf historical", "P1"),
    ("sector-performance-snapshot",       {"date": _TODAY_PARAM}, "sector perf snapshot", "P1"),
    ("historical-chart/1hour",            {"symbol": TICKER}, "intraday 1h bars", "P4"),
    ("esg-ratings",                       {"symbol": TICKER}, "ESG rating", "P4"),
    ("esg-disclosures",                   {"symbol": TICKER}, "ESG disclosures", "P4"),
    ("analyst-estimates",                 {"symbol": TICKER, "period": "annual", "limit": 3},
                                          "analyst estimates annual", "P4"),
    ("commitment-of-traders-analysis",    {}, "COT analysis", "P4"),
]


def probe(path: str, params: dict) -> dict:
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return {"status": -1, "error": "FMP_API_KEY not set"}
    url = f"https://financialmodelingprep.com/stable/{path}"
    try:
        r = requests.get(url, params={**params, "apikey": api_key}, timeout=15)
    except Exception as e:
        return {"status": -2, "error": f"network: {e}"}
    out: dict = {"status": r.status_code}
    try:
        body = r.json()
    except Exception:
        out["error"] = "non-json body"
        out["body_head"] = r.text[:200]
        return out
    if isinstance(body, list):
        out["count"] = len(body)
        if body and isinstance(body[0], dict):
            out["sample_keys"] = sorted(list(body[0].keys()))[:20]
    elif isinstance(body, dict):
        out["count"] = 1
        out["sample_keys"] = sorted(list(body.keys()))[:20]
        if body.get("Error Message"):
            out["error_msg"] = body["Error Message"][:200]
    else:
        out["count"] = 0
    return out


def main() -> int:
    out: dict = {
        "as_of":      datetime.utcnow().isoformat() + "Z",
        "ticker":     TICKER,
        "probes":     {},
        "_summary":   {},
    }

    pass_, fail = [], []
    for path, params, label, cls in PROBES:
        result = probe(path, params)
        result["label"] = label
        result["class"] = cls
        out["probes"][path] = result
        ok = result.get("status") == 200 and (result.get("count") or 0) > 0 \
             and not result.get("error_msg")
        (pass_ if ok else fail).append((path, cls, result.get("status"),
                                        result.get("count"), result.get("error_msg") or ""))

    out["_summary"] = {
        "pass": [p[0] for p in pass_],
        "fail": [{"path": p[0], "class": p[1], "status": p[2],
                  "count": p[3], "err": p[4]} for p in fail],
        "pass_count": len(pass_),
        "fail_count": len(fail),
    }

    out_path = OUT_DIR / f"fmp_probe_{date.today().isoformat()}.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"PASS: {len(pass_)} / {len(PROBES)}", file=sys.stderr)
    for p in pass_:
        print(f"  ✓ {p[0]:55s} count={p[3]}", file=sys.stderr)
    print(f"FAIL: {len(fail)}", file=sys.stderr)
    for p in fail:
        print(f"  ✗ {p[0]:55s} status={p[2]} {p[4][:50]}", file=sys.stderr)
    print(f"Written: {out_path.relative_to(BASE)}", file=sys.stderr)
    return 0 if fail == [] else 0  # never block downstream; report-only


if __name__ == "__main__":
    sys.exit(main())

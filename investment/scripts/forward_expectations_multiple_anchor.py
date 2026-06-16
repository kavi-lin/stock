#!/usr/bin/env python3
"""Historical multiple-regime anchor for the Future Price Range (EXP-R1).

Breaks the derived-band tautology. The previous price-range default set
`base_multiple = current_price / forward_eps`, forcing the base target back to
today's price (range degraded to a +/-15% volatility band, not a forecast).

This module supplies a multiple anchor that is INDEPENDENT of today's price: the
ticker's own historical valuation regime from FMP `ratios` annual history. Each
year's ratio uses that year's price, so the median/p25/p75 band describes "what
multiple this name actually trades at", not what it trades at today.

Robustness: a metric's regime is only `usable` when it has >= MIN_POINTS years and
its p75/p25 dispersion is <= MAX_DISPERSION. This auto-rejects unstable regimes
(e.g. a hyper-growth name's wild trailing P/E) so the price-range builder can
prefer a stabler metric (e.g. P/S) or honestly degrade to an advisory band.

SHADOW ONLY — never feeds live fair_value_summary, decision_lock, or sizing.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

ENGINE_VERSION = "forward_expectations_multiple_anchor.py v1.0"

MAX_HISTORY = 6        # most recent annual ratio rows to consider
MIN_POINTS = 2         # need at least this many positive years for a regime
MAX_DISPERSION = 3.0   # reject a regime whose p75/p25 exceeds this (too noisy)

# price-range metric key -> FMP `ratios` field
FIELD_MAP = {
    "pe": "priceToEarningsRatio",
    "ps": "priceToSalesRatio",
    "pfcf": "priceToFreeCashFlowRatio",
}


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _pos(value):
    value = _num(value)
    return value if value is not None and value > 0 else None


def _pct(vals, q):
    s = sorted(vals)
    if not s:
        return None
    k = (len(s) - 1) * q
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def _regime_band(values: list, source: str):
    pos = [v for v in (_pos(x) for x in values) if v is not None]
    if len(pos) < MIN_POINTS:
        return {"usable": False, "n": len(pos), "reason": "insufficient_history"}
    p25, p50, p75 = _pct(pos, 0.25), _pct(pos, 0.50), _pct(pos, 0.75)
    dispersion = (p75 / p25) if (p25 and p25 > 0) else None
    usable = dispersion is not None and dispersion <= MAX_DISPERSION
    return {
        "usable": usable,
        "n": len(pos),
        "p25": round(p25, 4),
        "p50": round(p50, 4),
        "p75": round(p75, 4),
        "dispersion_ratio": round(dispersion, 3) if dispersion is not None else None,
        "source": source,
        "reason": None if usable else "dispersion_too_high",
    }


def _default_fetch(ticker: str):
    """Fetch FMP annual ratios history. Isolated so tests can inject rows."""
    try:
        from scripts._shared import fmp_pool
    except Exception:
        return None
    rows = fmp_pool.get("ratios", {"symbol": ticker, "limit": MAX_HISTORY},
                        stable=True, retries=1, timeout=20, hard_fail=False)
    return rows if isinstance(rows, list) else None


def build_multiple_anchor(ticker: str, no_fetch: bool = False, fetch_fn=None) -> dict:
    base = {
        "engine": ENGINE_VERSION,
        "ticker": ticker,
        "available": False,
        "anchor_independent_of_current_price": True,
        "source": None,
        "history_points": 0,
        "by_metric": {},
        "warnings": [],
        "policy": "Historical valuation regime; shadow-only multiple anchor.",
    }
    if no_fetch:
        return {**base, "warnings": ["no_fetch_historical_multiple_skipped"]}

    rows = (fetch_fn or _default_fetch)(ticker)
    if not isinstance(rows, list) or not rows:
        return {**base, "warnings": ["historical_ratios_unavailable"]}

    rows = sorted([r for r in rows if isinstance(r, dict) and r.get("date")],
                  key=lambda r: r["date"])[-MAX_HISTORY:]
    if not rows:
        return {**base, "warnings": ["historical_ratios_unavailable"]}

    by_metric = {}
    for key, field in FIELD_MAP.items():
        by_metric[key] = _regime_band(
            [row.get(field) for row in rows], f"fmp_ratios_annual_history:{field}"
        )
    available = any(band.get("usable") for band in by_metric.values())
    warnings = []
    if not available:
        warnings.append("no_usable_historical_multiple_regime")
    return {
        **base,
        "available": available,
        "source": "fmp_ratios_annual_history",
        "history_points": len(rows),
        "by_metric": by_metric,
        "warnings": warnings,
    }


def main():
    ap = argparse.ArgumentParser(description="Historical multiple-regime anchor (EXP-R1)")
    ap.add_argument("ticker")
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    result = build_multiple_anchor(args.ticker.upper(), no_fetch=args.no_fetch)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

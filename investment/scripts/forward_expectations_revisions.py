"""Point-in-time analyst estimate / rating revision snapshot.

The current earnings cache stores latest annual estimates and monthly analyst
ratings, not historical estimate versions. This module therefore records a
point-in-time consensus snapshot plus rating momentum and dispersion. Estimate
revision deltas require comparing future ledger snapshots.
"""
from __future__ import annotations

import argparse
import json
import math
import sys


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _pos(value):
    value = _num(value)
    return value if value is not None and value > 0 else None


def _spread_pct(low, high, avg):
    low, high, avg = _pos(low), _pos(high), _pos(avg)
    if low is None or high is None or avg is None:
        return None
    return round((high - low) / avg * 100, 2)


def _estimate_rows(earnings_cache: dict) -> list[dict]:
    rows = earnings_cache.get("annual_estimates")
    if not isinstance(rows, list):
        return []
    return sorted([row for row in rows if row.get("date")], key=lambda row: row["date"])


def estimate_snapshot(earnings_cache: dict) -> dict:
    rows = _estimate_rows(earnings_cache)
    entries = []
    for row in rows:
        entries.append({
            "date": row.get("date"),
            "revenue_avg": row.get("revenue_avg"),
            "revenue_low": row.get("revenue_low"),
            "revenue_high": row.get("revenue_high"),
            "revenue_spread_pct": _spread_pct(
                row.get("revenue_low"), row.get("revenue_high"), row.get("revenue_avg"),
            ),
            "eps_avg": row.get("eps_avg"),
            "eps_low": row.get("eps_low"),
            "eps_high": row.get("eps_high"),
            "eps_spread_pct": _spread_pct(row.get("eps_low"), row.get("eps_high"), row.get("eps_avg")),
            "num_analysts_revenue": row.get("num_analysts_revenue"),
            "num_analysts_eps": row.get("num_analysts_eps"),
        })
    return {
        "available": bool(entries),
        "window_from": entries[0]["date"] if entries else None,
        "window_to": entries[-1]["date"] if entries else None,
        "entries": entries,
    }


def _net_bull(row: dict) -> float | None:
    strong_buy = row.get("analystRatingsStrongBuy") or 0
    buy = row.get("analystRatingsBuy") or 0
    hold = row.get("analystRatingsHold") or 0
    sell = row.get("analystRatingsSell") or 0
    strong_sell = row.get("analystRatingsStrongSell") or 0
    total = strong_buy + buy + hold + sell + strong_sell
    if total <= 0:
        return None
    return (strong_buy + buy - sell - strong_sell) / total


def rating_momentum(earnings_cache: dict) -> dict:
    grades = earnings_cache.get("analyst_grades")
    if not isinstance(grades, list) or len(grades) < 2:
        return {"available": False, "direction": None, "delta": None, "reason": "analyst_grades_missing_or_sparse"}
    rows = sorted([row for row in grades if row.get("date")], key=lambda row: row["date"])
    if len(rows) < 2:
        return {"available": False, "direction": None, "delta": None, "reason": "dated_grades_missing"}
    old, new = rows[0], rows[-1]
    old_score, new_score = _net_bull(old), _net_bull(new)
    if old_score is None or new_score is None:
        return {"available": False, "direction": None, "delta": None, "reason": "ratings_count_missing"}
    delta = new_score - old_score
    direction = "UP" if delta > 0.03 else "DOWN" if delta < -0.03 else "FLAT"
    return {
        "available": True,
        "from": old.get("date"),
        "to": new.get("date"),
        "net_bull_from": round(old_score, 4),
        "net_bull_to": round(new_score, 4),
        "delta": round(delta, 4),
        "direction": direction,
    }


def build_revision_snapshot(ticker: str, earnings_cache: dict, generated_at: str | None = None) -> dict:
    estimates = estimate_snapshot(earnings_cache)
    ratings = rating_momentum(earnings_cache)
    latest = estimates["entries"][0] if estimates["entries"] else {}
    return {
        "ticker": ticker.upper(),
        "generated_at": generated_at,
        "available": estimates["available"] or ratings["available"],
        "estimate_revision_delta_available": False,
        "estimate_revision_delta_reason": "annual_estimates cache has latest forward curve only; compare future ledger snapshots for deltas",
        "annual_estimate_snapshot": estimates,
        "latest_year": latest,
        "rating_momentum": ratings,
        "policy": "This is a point-in-time market-expectations snapshot, not a live valuation input.",
    }


def main():
    ap = argparse.ArgumentParser(description="Build analyst estimate revision snapshot")
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--earnings-cache-file", required=True)
    args = ap.parse_args()
    try:
        with open(args.earnings_cache_file, encoding="utf-8") as handle:
            earnings_cache = json.load(handle)
    except Exception as exc:
        print(json.dumps({"error": f"unparseable earnings cache file: {exc}"}))
        sys.exit(1)
    print(json.dumps(build_revision_snapshot(args.ticker, earnings_cache), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

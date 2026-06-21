"""Read-only calibration scaffold for Forward Expectations.

Compares immutable forecast snapshots with later earnings-analyst caches when
actuals are available. This does not tune parameters, change live decisions, or
rank lanes as superior with small samples.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SNAPSHOT_DIR = os.path.join(BASE_DIR, "investment", "invest_logs", "forward_expectations")
EARNINGS_CACHE_DIR = os.path.join(BASE_DIR, "skills", "earnings-analyst", "cache")
MIN_CALIBRATION_N = 15


def _read_json(path: str):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _abs_pct_error(forecast, actual):
    forecast, actual = _num(forecast), _num(actual)
    if forecast is None or actual is None or actual == 0:
        return None
    return abs(forecast - actual) / abs(actual)


def _direction(value):
    value = _num(value)
    if value is None:
        return None
    return "up" if value > 0 else "down" if value < 0 else "flat"


def _direction_hit(forecast, actual):
    f, a = _direction(forecast), _direction(actual)
    return None if f is None or a is None else f == a


def _snapshot_files(snapshot_dir: str = SNAPSHOT_DIR) -> list[str]:
    return sorted(glob.glob(os.path.join(snapshot_dir, "*.json")))


def _earnings_cache_for(ticker: str, earnings_cache_dir: str = EARNINGS_CACHE_DIR) -> dict | None:
    files = sorted(glob.glob(os.path.join(earnings_cache_dir, f"{ticker.upper()}_*.json")))
    files = [path for path in files if not path.endswith(".infographic.json")]
    if not files:
        return None
    return _read_json(files[-1])


def _year(value):
    try:
        return int(str(value)[:4])
    except (ValueError, TypeError):
        return None


def _geomean_cagr(yoy_growths: list) -> float | None:
    """Annualized rate from a sequence of single-year YoY growths (same basis as a
    consensus estimate-window CAGR). Returns None if any year swings through ≤ -100%
    (sign flip / loss year) where a geometric mean is undefined."""
    factors = [1.0 + g for g in yoy_growths]
    if not factors or any(f <= 0 for f in factors):
        return None
    product = 1.0
    for f in factors:
        product *= f
    return product ** (1.0 / len(factors)) - 1.0


def _annual_growth_index(earnings_cache: dict | None, metric: str) -> dict:
    """{fiscal_year:int -> realized YoY growth} from the cache's realized annual_growth.
    EPS uses netIncomeGrowth as a same-basis proxy (no realized per-share series in cache)."""
    field = "revenueGrowth" if metric == "revenue_growth" else "netIncomeGrowth"
    out = {}
    for row in (earnings_cache or {}).get("annual_growth") or []:
        if not isinstance(row, dict):
            continue
        year = _year(row.get("date")) or _year(row.get("fiscalYear"))
        growth = _num(row.get(field))
        if year is not None and growth is not None:
            out[year] = growth
    return out


def _realized_window_cagr(earnings_cache: dict | None, window_from, window_to, metric):
    """Realized annualized growth over the SAME [window_from, window_to] the forecast
    CAGR spans — built from realized per-FY YoY growths. Returns (cagr, status):
      actual_not_comparable_yet  — forecast horizon has not elapsed (window_to > latest realized FY)
      actual_basis_unavailable   — elapsed but a window FY is missing / sign-flips
      comparable                 — every window FY realized → same-basis realized CAGR
    Deliberately NOT a trailing-1yr YoY (the previous apples-to-oranges bug)."""
    year_from, year_to = _year(window_from), _year(window_to)
    if year_from is None or year_to is None or year_to <= year_from:
        return None, "window_unparseable"
    index = _annual_growth_index(earnings_cache, metric)
    if not index:
        return None, "actual_basis_unavailable"
    if year_to > max(index):
        return None, "actual_not_comparable_yet"
    growths = []
    for year in range(year_from + 1, year_to + 1):
        if year not in index:
            return None, "actual_basis_unavailable"
        growths.append(index[year])
    cagr = _geomean_cagr(growths)
    if cagr is None:
        return None, "actual_basis_unavailable"
    return cagr, "comparable"


def _forecast_points(snapshot: dict) -> list[dict]:
    points = []
    consensus = snapshot.get("consensus_lane") or {}
    if consensus.get("revenue_cagr") is not None:
        points.append({
            "lane": "consensus",
            "metric": "revenue_growth",
            "forecast_value": consensus.get("revenue_cagr"),
            "forecast_basis": "estimate_window_cagr",
            "window_from": consensus.get("window_from"),
            "window_to": consensus.get("window_to"),
        })
    if consensus.get("eps_cagr") is not None:
        points.append({
            "lane": "consensus",
            "metric": "eps_growth",
            "forecast_value": consensus.get("eps_cagr"),
            "forecast_basis": "estimate_window_cagr",
            "window_from": consensus.get("window_from"),
            "window_to": consensus.get("window_to"),
        })
    revision = snapshot.get("estimate_revision_snapshot") or {}
    latest = revision.get("latest_year") or {}
    for metric, actual_metric in (("revenue", "revenue_growth"), ("eps", "eps_growth")):
        avg = latest.get(f"{metric}_avg")
        if avg is not None:
            points.append({
                "lane": "consensus_revision",
                "metric": actual_metric,
                "forecast_value": avg,
                "forecast_basis": "future_level_snapshot",
                "window_to": latest.get("date"),
            })
    return points


def evaluate_snapshot(snapshot: dict, earnings_cache: dict | None = None) -> dict:
    ticker = snapshot.get("ticker")
    as_of = (earnings_cache or {}).get("as_of_date") or (earnings_cache or {}).get("last_earnings_date")
    rows = []
    for point in _forecast_points(snapshot):
        actual_value = direction_hit = ape = None
        actual_basis = None
        if point["forecast_basis"] != "estimate_window_cagr":
            # future-level snapshots have no realized same-basis actual to score against.
            status = "actual_not_comparable_yet"
        else:
            actual_value, status = _realized_window_cagr(
                earnings_cache, point.get("window_from"), point.get("window_to"), point["metric"],
            )
            if status == "window_unparseable":
                status = "actual_basis_unavailable"
            if status == "comparable":
                actual_basis = "realized_window_cagr"
                ape = _abs_pct_error(point["forecast_value"], actual_value)
                direction_hit = _direction_hit(point["forecast_value"], actual_value)
            else:
                actual_value = None
        rows.append({
            **point,
            "actual_value": actual_value,
            "actual_basis": actual_basis,
            "actual_as_of": as_of,
            "status": status,
            "absolute_pct_error": round(ape, 4) if ape is not None else None,
            "direction_hit": direction_hit,
        })
    return {
        "ticker": ticker,
        "snapshot_id": snapshot.get("run_id") or snapshot.get("as_of_earnings_date"),
        "snapshot_generated_at": snapshot.get("generated_at"),
        "rows": rows,
    }


def summarize(rows: list[dict], min_n: int = MIN_CALIBRATION_N) -> dict:
    comparable = [row for row in rows if row.get("status") == "comparable"]
    by_lane = defaultdict(list)
    for row in comparable:
        by_lane[(row["lane"], row["metric"])].append(row)
    lane_summaries = []
    for (lane, metric), group in sorted(by_lane.items()):
        errors = [row["absolute_pct_error"] for row in group if row.get("absolute_pct_error") is not None]
        hits = [row["direction_hit"] for row in group if row.get("direction_hit") is not None]
        n = len(group)
        lane_summaries.append({
            "lane": lane,
            "metric": metric,
            "n": n,
            "status": "calibratable" if n >= min_n else "insufficient_sample",
            "wape_proxy": round(sum(errors) / len(errors), 4) if errors else None,
            "directional_accuracy": round(sum(1 for hit in hits if hit) / len(hits), 4) if hits else None,
            "min_required_n": min_n,
        })
    return {
        "total_rows": len(rows),
        "comparable_count": len(comparable),
        "status": "calibratable" if len(comparable) >= min_n else "insufficient_sample",
        "min_required_n": min_n,
        "lane_summaries": lane_summaries,
        "policy": "Small samples are directional only and must not change live decisions.",
    }


def _latest_snapshot_per_ticker(snapshot_dir: str) -> list[dict]:
    """Re-running the engine on the same ticker writes many near-identical snapshots; counting
    each as an independent forecast inflated the sample (8 AAPL re-runs → 8 rows). Keep only the
    latest snapshot per ticker so the calibration sample reflects true breadth, not re-run count."""
    latest = {}
    for path in _snapshot_files(snapshot_dir):
        snapshot = _read_json(path)
        if not isinstance(snapshot, dict):
            continue
        ticker = (snapshot.get("ticker") or "").upper()
        if not ticker:
            continue
        stamp = snapshot.get("generated_at") or snapshot.get("run_id") or os.path.basename(path)
        if ticker not in latest or stamp > latest[ticker][0]:
            latest[ticker] = (stamp, snapshot)
    return [snapshot for _, snapshot in sorted(latest.values(), key=lambda item: item[0])]


def run_calibration(snapshot_dir: str = SNAPSHOT_DIR, earnings_cache_dir: str = EARNINGS_CACHE_DIR,
                    min_n: int = MIN_CALIBRATION_N) -> dict:
    evaluations = []
    all_rows = []
    snapshots = _latest_snapshot_per_ticker(snapshot_dir)
    for snapshot in snapshots:
        cache = _earnings_cache_for(snapshot.get("ticker") or "", earnings_cache_dir)
        evaluation = evaluate_snapshot(snapshot, cache)
        evaluations.append(evaluation)
        all_rows.extend(evaluation["rows"])
    return {
        "engine": "forward_expectations_calibration.py v2 (same-basis realized window + dedup)",
        "snapshot_count": len(evaluations),
        "deduped_from_files": len(_snapshot_files(snapshot_dir)),
        "summary": summarize(all_rows, min_n),
        "evaluations": evaluations,
    }


def main():
    ap = argparse.ArgumentParser(description="Forward Expectations forecast-vs-actual scaffold")
    ap.add_argument("--snapshot-dir", default=SNAPSHOT_DIR)
    ap.add_argument("--earnings-cache-dir", default=EARNINGS_CACHE_DIR)
    ap.add_argument("--min-n", type=int, default=MIN_CALIBRATION_N)
    args = ap.parse_args()
    print(json.dumps(
        run_calibration(args.snapshot_dir, args.earnings_cache_dir, args.min_n),
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    ))


if __name__ == "__main__":
    main()

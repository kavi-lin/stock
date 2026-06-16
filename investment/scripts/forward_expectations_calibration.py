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


def _actuals(earnings_cache: dict | None) -> dict:
    yoy = ((earnings_cache or {}).get("derived") or {}).get("yoy_growth") or {}
    return {
        "revenue_yoy": _num(yoy.get("revenue_yoy")),
        "eps_yoy": _num(yoy.get("earnings_yoy")),
        "as_of": (earnings_cache or {}).get("as_of_date") or (earnings_cache or {}).get("last_earnings_date"),
    }


def _forecast_points(snapshot: dict) -> list[dict]:
    points = []
    consensus = snapshot.get("consensus_lane") or {}
    if consensus.get("revenue_cagr") is not None:
        points.append({
            "lane": "consensus",
            "metric": "revenue_growth",
            "forecast_value": consensus.get("revenue_cagr"),
            "forecast_basis": "estimate_window_cagr",
            "window_to": consensus.get("window_to"),
        })
    if consensus.get("eps_cagr") is not None:
        points.append({
            "lane": "consensus",
            "metric": "eps_growth",
            "forecast_value": consensus.get("eps_cagr"),
            "forecast_basis": "estimate_window_cagr",
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
    actual = _actuals(earnings_cache)
    rows = []
    for point in _forecast_points(snapshot):
        actual_key = "revenue_yoy" if point["metric"] == "revenue_growth" else "eps_yoy"
        actual_value = actual.get(actual_key)
        if point["forecast_basis"] != "estimate_window_cagr":
            status = "actual_not_comparable_yet"
            ape = direction_hit = None
        elif actual_value is None:
            status = "actual_not_available"
            ape = direction_hit = None
        else:
            status = "comparable"
            ape = _abs_pct_error(point["forecast_value"], actual_value)
            direction_hit = _direction_hit(point["forecast_value"], actual_value)
        rows.append({
            **point,
            "actual_value": actual_value if point["forecast_basis"] == "estimate_window_cagr" else None,
            "actual_basis": "latest_yoy" if point["forecast_basis"] == "estimate_window_cagr" else None,
            "actual_as_of": actual.get("as_of"),
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


def run_calibration(snapshot_dir: str = SNAPSHOT_DIR, earnings_cache_dir: str = EARNINGS_CACHE_DIR,
                    min_n: int = MIN_CALIBRATION_N) -> dict:
    evaluations = []
    all_rows = []
    for path in _snapshot_files(snapshot_dir):
        snapshot = _read_json(path)
        if not isinstance(snapshot, dict):
            continue
        cache = _earnings_cache_for(snapshot.get("ticker") or "", earnings_cache_dir)
        evaluation = evaluate_snapshot(snapshot, cache)
        evaluations.append(evaluation)
        all_rows.extend(evaluation["rows"])
    return {
        "engine": "forward_expectations_calibration.py v1",
        "snapshot_count": len(evaluations),
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

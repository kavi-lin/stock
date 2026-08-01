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
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SNAPSHOT_DIR = os.path.join(BASE_DIR, "investment", "invest_logs", "forward_expectations")
EARNINGS_CACHE_DIR = os.path.join(BASE_DIR, "skills", "earnings-analyst", "cache")
MIN_CALIBRATION_N = 15

# Calibration scores two lanes and needs nothing else from a snapshot. The other
# ~22 keys (evidence_inventory, source_discovery, the unscored lanes …) are
# build-time pipeline output and audit evidence — 97% of the bytes, never read
# here. Caching this subset keeps a full-corpus scan flat as the corpus grows.
#
# The index is a CACHE, never a replacement: the raw snapshots stay the record
# (they are not regenerable, and single-snapshot entry points still read them in
# full). Widen INDEX_FIELDS — e.g. when base_rate_lane or market_implied_lane
# start being scored — and bump INDEX_SCHEMA so stale indexes rebuild themselves.
INDEX_SCHEMA = "fe_calibration_index.v1"
INDEX_FIELDS = ("ticker", "generated_at", "run_id", "as_of_earnings_date",
                "consensus_lane", "estimate_revision_snapshot")


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


def default_index_path(snapshot_dir: str = SNAPSHOT_DIR) -> str:
    """Index sits beside the snapshot directory, never inside it — a file within
    would be picked up by the *.json glob and parsed as a snapshot."""
    root = os.path.abspath(snapshot_dir).rstrip(os.sep)
    return root + "_calibration_index.json"


def _index_subset(snapshot: dict) -> dict:
    return {key: snapshot[key] for key in INDEX_FIELDS if key in snapshot}


def _read_index(path: str) -> dict:
    data = _read_json(path)
    if not isinstance(data, dict) or data.get("schema") != INDEX_SCHEMA:
        return {}
    if list(data.get("fields") or []) != list(INDEX_FIELDS):
        return {}  # the scored field set changed — rebuild rather than trust it
    entries = data.get("entries")
    return entries if isinstance(entries, dict) else {}


def _write_index(path: str, entries: dict) -> None:
    """Atomic replace. A cache that cannot be written must never fail a run."""
    tmp = f"{path}.tmp"
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump({"schema": INDEX_SCHEMA, "fields": list(INDEX_FIELDS),
                       "entries": entries}, handle, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _file_signature(path: str) -> list | None:
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return [int(stat.st_size), round(stat.st_mtime, 3)]


def load_snapshots(snapshot_dir: str = SNAPSHOT_DIR, *, use_index: bool = True,
                   index_path: str | None = None) -> list[dict]:
    """Snapshots reduced to the fields calibration scores.

    An index entry is reused only while the source file's size and mtime still
    match; anything missing or stale falls back to reading the raw snapshot, so
    the result is identical either way (asserted in
    test_forward_expectations_calibration.py).
    """
    files = _snapshot_files(snapshot_dir)
    if index_path is None:
        index_path = default_index_path(snapshot_dir)
    cached = _read_index(index_path) if use_index else {}
    entries: dict = {}
    snapshots: list[dict] = []
    stale = False
    for path in files:
        signature = _file_signature(path)
        if signature is None:
            continue
        key = os.path.basename(path)
        hit = cached.get(key)
        if isinstance(hit, dict) and hit.get("sig") == signature and isinstance(hit.get("snapshot"), dict):
            subset = hit["snapshot"]
        else:
            raw = _read_json(path)
            if not isinstance(raw, dict):
                continue
            subset = _index_subset(raw)
            stale = True
        entries[key] = {"sig": signature, "snapshot": subset}
        if subset.get("ticker"):
            snapshots.append(subset)
    if use_index and (stale or len(entries) != len(cached)):
        _write_index(index_path, entries)
    return snapshots


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


def _date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
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


def _realized_fiscal_levels(earnings_cache: dict | None) -> dict:
    """Aggregate completed Q1-Q4 fiscal years into realized revenue/EPS levels."""
    grouped = defaultdict(dict)
    for row in (earnings_cache or {}).get("quarterly_pnl") or []:
        if not isinstance(row, dict):
            continue
        year = _year(row.get("fiscalYear")) or _year(row.get("date"))
        period = str(row.get("period") or "").upper()
        if year is None or period not in {"Q1", "Q2", "Q3", "Q4"}:
            continue
        grouped[year][period] = row
    realized = {}
    for year, quarters in grouped.items():
        if set(quarters) != {"Q1", "Q2", "Q3", "Q4"}:
            continue
        revenue = [_num(quarters[q].get("revenue")) for q in ("Q1", "Q2", "Q3", "Q4")]
        eps = [_num(quarters[q].get("epsDiluted")) for q in ("Q1", "Q2", "Q3", "Q4")]
        realized[year] = {
            "revenue_level": sum(revenue) if all(v is not None for v in revenue) else None,
            "eps_level": sum(eps) if all(v is not None for v in eps) else None,
        }
    return realized


def _realized_fiscal_level(earnings_cache, target_date, metric, snapshot_generated_at):
    target = _date(target_date)
    generated = _date(snapshot_generated_at)
    if target is None:
        return None, "actual_basis_unavailable"
    # A forecast created on/after fiscal year-end is not an out-of-sample forecast.
    if generated is None or generated >= target:
        return None, "not_point_in_time_forecast"
    levels = _realized_fiscal_levels(earnings_cache)
    if target.year not in levels:
        return None, "actual_not_comparable_yet"
    value = levels[target.year].get(metric)
    return (value, "comparable") if value is not None else (None, "actual_basis_unavailable")


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
    for metric, actual_metric in (("revenue", "revenue_level"), ("eps", "eps_level")):
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
        if point["forecast_basis"] == "future_level_snapshot":
            actual_value, status = _realized_fiscal_level(
                earnings_cache, point.get("window_to"), point["metric"], snapshot.get("generated_at"),
            )
            if status == "comparable":
                actual_basis = "quarterly_pnl_q1_q4_fiscal_sum"
                ape = _abs_pct_error(point["forecast_value"], actual_value)
                # Direction on two positive level values is meaningless; score error only.
                direction_hit = None
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
            "ticker": ticker,
            "snapshot_generated_at": snapshot.get("generated_at"),
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


def _dedupe_forecast_rows(rows: list[dict]) -> list[dict]:
    """Keep the earliest archived forecast for each ticker/target/basis.

    Re-runs are correlated observations, and keeping only the latest run can erase the
    forecast immediately before it becomes measurable. Earliest-vintage selection is
    conservative and preserves a genuinely point-in-time out-of-sample forecast.
    """
    kept = {}
    for row in rows:
        key = (
            row.get("ticker"), row.get("lane"), row.get("metric"), row.get("forecast_basis"),
            row.get("window_from"), row.get("window_to"),
        )
        stamp = row.get("snapshot_generated_at") or "9999"
        if key not in kept or stamp < kept[key][0]:
            kept[key] = (stamp, row)
    return [item[1] for item in sorted(kept.values(), key=lambda item: item[0])]


def run_calibration(snapshot_dir: str = SNAPSHOT_DIR, earnings_cache_dir: str = EARNINGS_CACHE_DIR,
                    min_n: int = MIN_CALIBRATION_N, *, use_index: bool = True,
                    index_path: str | None = None) -> dict:
    evaluations = []
    all_rows = []
    earnings_by_ticker = {}
    snapshots = load_snapshots(snapshot_dir, use_index=use_index, index_path=index_path)
    for snapshot in snapshots:
        ticker = (snapshot.get("ticker") or "").upper()
        if ticker not in earnings_by_ticker:
            earnings_by_ticker[ticker] = _earnings_cache_for(ticker, earnings_cache_dir)
        cache = earnings_by_ticker[ticker]
        evaluation = evaluate_snapshot(snapshot, cache)
        evaluations.append(evaluation)
        all_rows.extend(evaluation["rows"])
    deduped_rows = _dedupe_forecast_rows(all_rows)
    return {
        "engine": "forward_expectations_calibration.py v3 (realized FY levels + earliest-vintage dedup)",
        "snapshot_count": len(evaluations),
        "forecast_point_count": len(deduped_rows),
        "deduped_from_rows": len(all_rows),
        "summary": summarize(deduped_rows, min_n),
        "evaluations": evaluations,
    }


def main():
    ap = argparse.ArgumentParser(description="Forward Expectations forecast-vs-actual scaffold")
    ap.add_argument("--snapshot-dir", default=SNAPSHOT_DIR)
    ap.add_argument("--earnings-cache-dir", default=EARNINGS_CACHE_DIR)
    ap.add_argument("--min-n", type=int, default=MIN_CALIBRATION_N)
    ap.add_argument("--index-path", default=None,
                    help="calibration index location (default: sibling of --snapshot-dir)")
    ap.add_argument("--no-index", action="store_true",
                    help="read every raw snapshot; use to verify the index agrees")
    args = ap.parse_args()
    print(json.dumps(
        run_calibration(args.snapshot_dir, args.earnings_cache_dir, args.min_n,
                        use_index=not args.no_index, index_path=args.index_path),
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    ))


if __name__ == "__main__":
    main()

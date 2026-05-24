#!/usr/bin/env python3
"""V3.17.3 — Composite calibration cohort runner.

Processes the 18-ticker historical cohort defined in cohort.yaml, looking up
each entry's earnings-analyst cache, re-running the analyzer if needed, and
scoring the V3.17 rubric against pre-recorded directional outcomes.

Design (per Wave 1 plan + Codex round-7 risk discussion):
  - Historical caches are NOT live-fetched. Runner reads whatever is present
    under skills/earnings-analyst/cache/<TICKER>_<DATE>.json that falls
    within ±90 days of the cohort's target_quarter_end.
  - Missing cache → status=MISSING_CACHE; sample reported but EXCLUDED from
    acceptance scoring (denominator = AVAILABLE samples, not total 18).
  - Acceptance fails soft (rc=0 + warning) when AVAILABLE < 6 or any gate
    is breached — V3.17.3 is a measurement layer, not an enforcement layer.
    User can re-baseline thresholds after observing real cohort outcomes.
  - Output: reports/calibration_<DATE>.md with per-ticker table +
    bucket aggregates + acceptance summary.

Usage:
    python3 skills/_shared/composite_calibration_cohort/runner.py
    python3 skills/_shared/composite_calibration_cohort/runner.py --output reports/calibration_<DATE>.md
    python3 skills/_shared/composite_calibration_cohort/runner.py --json   # machine-readable
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. pip install pyyaml", file=sys.stderr)
    sys.exit(2)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
EA_CACHE_DIR = REPO_ROOT / "skills" / "earnings-analyst" / "cache"
REPORTS_DIR = REPO_ROOT / "reports"

sys.path.insert(0, str(REPO_ROOT / "skills" / "earnings-analyst" / "scripts"))
from analyze import analyze  # noqa: E402


def load_cohort() -> dict:
    cohort_path = HERE / "cohort.yaml"
    with open(cohort_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _to_date(value) -> dt.date | None:
    """Coerce either an ISO-8601 string or a yaml-parsed date/datetime to dt.date."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def find_closest_cache(ticker: str, target_iso, window_days: int) -> str | None:
    """Locate the earnings-analyst cache file whose <DATE> is closest to
    target_iso, within ±window_days. Returns None if no cache fits."""
    target = _to_date(target_iso)
    if target is None:
        return None
    best_path = None
    best_delta_days = window_days + 1
    pattern = str(EA_CACHE_DIR / f"{ticker}_*.json")
    for fp in glob.glob(pattern):
        if fp.endswith(".infographic.json"):
            continue
        basename = os.path.basename(fp)
        # Expect format <TICKER>_<YYYY-MM-DD>.json
        parts = basename[:-len(".json")].split("_")
        if len(parts) < 2:
            continue
        date_str = parts[-1]
        try:
            d = dt.date.fromisoformat(date_str)
        except ValueError:
            continue
        delta = abs((d - target).days)
        if delta < best_delta_days:
            best_delta_days = delta
            best_path = fp
    return best_path


def score_directional(predicted_composite: int, expected: str) -> str:
    """Score a single sample directionally.

    Mapping rule (simplest realistic interpretation — refine after observing):
      composite >= 65  → predicts directional_up (SOLID/STRONG)
      35 <= composite < 65 → predicts directional_flat (MIXED/WEAK)
      composite < 35    → predicts directional_down (DETERIORATING)
    """
    if predicted_composite >= 65:
        predicted = "directional_up"
    elif predicted_composite >= 35:
        predicted = "directional_flat"
    else:
        predicted = "directional_down"

    if predicted == expected:
        return "CORRECT"
    # Half-credit: predicted_flat but actual up/down (still adjacent)
    if predicted == "directional_flat" and expected in {"directional_up", "directional_down"}:
        return "PARTIAL"
    if predicted in {"directional_up", "directional_down"} and expected == "directional_flat":
        return "PARTIAL"
    return "WRONG"


def process_entry(ticker: str, target_iso: str, expected: str,
                  bucket: str, window_days: int, v317_new_flags: set) -> dict:
    cache_path = find_closest_cache(ticker, target_iso, window_days)
    if cache_path is None:
        return {
            "ticker": ticker, "target": str(target_iso), "bucket": bucket,
            "expected": expected, "status": "MISSING_CACHE",
            "cache_path": None,
        }
    try:
        with open(cache_path, encoding="utf-8") as f:
            bundle = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return {
            "ticker": ticker, "target": str(target_iso), "bucket": bucket,
            "expected": expected, "status": "CACHE_READ_ERROR",
            "cache_path": cache_path, "error": str(e)[:120],
        }

    try:
        bundle = analyze(bundle)
    except Exception as e:
        return {
            "ticker": ticker, "target": str(target_iso), "bucket": bucket,
            "expected": expected, "status": "ANALYZE_ERROR",
            "cache_path": cache_path, "error": str(e)[:200],
        }

    composite = bundle.get("composite_score", 0)
    flags = bundle.get("quality_flags") or []
    cc_quality = bundle.get("cash_conversion_quality")
    transition_sig = bundle.get("transition_signature")
    mix_tier = (bundle.get("business_mix_shift_overlay") or {}).get("tier")

    v317_flag_hit = any(f in v317_new_flags for f in flags)
    cc_v317 = cc_quality in {"negative_accruals", "clean_positive_gap", "wc_driven"}
    transition_v317 = transition_sig in {"paradigm_only", "mix_only", "both"}
    any_v317_signal = v317_flag_hit or cc_v317 or transition_v317

    score = score_directional(composite, expected)
    cache_date = os.path.basename(cache_path).replace(f"{ticker}_", "").replace(".json", "")
    target_date = _to_date(target_iso)
    cache_delta = abs((dt.date.fromisoformat(cache_date) - target_date).days) if target_date else None

    return {
        "ticker":             ticker,
        "target":             str(target_iso),
        "bucket":             bucket,
        "expected":           expected,
        "status":             "OK",
        "cache_path":         cache_path,
        "cache_date":         cache_date,
        "cache_delta_days":   cache_delta,
        "composite":          composite,
        "verdict":            bundle.get("verdict"),
        "quality_flags":      flags,
        "cash_conversion_quality": cc_quality,
        "transition_signature":    transition_sig,
        "mix_tier":           mix_tier,
        "any_v317_signal":    any_v317_signal,
        "score":              score,
    }


def aggregate(results: list, acceptance: dict) -> dict:
    available = [r for r in results if r["status"] == "OK"]
    missing = [r for r in results if r["status"] == "MISSING_CACHE"]
    errors = [r for r in results if r["status"] in ("CACHE_READ_ERROR", "ANALYZE_ERROR")]

    correct = sum(1 for r in available if r["score"] == "CORRECT")
    partial = sum(1 for r in available if r["score"] == "PARTIAL")
    wrong = sum(1 for r in available if r["score"] == "WRONG")
    v317_hit = sum(1 for r in available if r["any_v317_signal"])

    n_avail = len(available)
    min_required = acceptance.get("min_available_for_scoring", 6)
    if n_avail < min_required:
        acceptance_status = "INSUFFICIENT_DATA"
        directional_ok = None
        flag_rate_ok = None
        directional_pct = None
        flag_rate = None
    else:
        directional_pct = correct / n_avail
        flag_rate = v317_hit / n_avail
        # V3.17.4 (Codex Finding 2) — rate-based, not absolute count.
        # Fallback to legacy `min_directionally_correct / 18` rate if the
        # rate key is absent (backward-compat for older cohort.yaml).
        min_rate = acceptance.get("min_directional_correct_rate")
        if min_rate is None:
            legacy_abs = acceptance.get("min_directionally_correct", 14)
            min_rate = legacy_abs / 18.0
        max_flag_rate = acceptance.get("max_new_flag_trigger_rate", 0.30)
        directional_ok = directional_pct >= min_rate
        flag_rate_ok = flag_rate <= max_flag_rate
        acceptance_status = "PASS" if (directional_ok and flag_rate_ok) else "FAIL"

    return {
        "n_total":             len(results),
        "n_available":         n_avail,
        "n_missing":           len(missing),
        "n_errors":            len(errors),
        "correct":             correct,
        "partial":             partial,
        "wrong":               wrong,
        "v317_signal_hit":     v317_hit,
        "directional_pct":     directional_pct,
        "new_flag_trigger_rate": flag_rate,
        "directional_ok":      directional_ok,
        "flag_rate_ok":        flag_rate_ok,
        "acceptance_status":   acceptance_status,
    }


def render_markdown(cohort: dict, results: list, agg: dict) -> str:
    today = dt.date.today().isoformat()
    md = [f"# Composite Calibration Cohort — {today}\n",
          f"> Runner: `skills/_shared/composite_calibration_cohort/runner.py` · "
          f"Cohort: {cohort.get('version', '?')}\n",
          "---\n",
          "## Acceptance Summary\n",
          f"| Metric | Value | Threshold | Pass |",
          f"|---|---|---|---|",
          f"| Available samples | {agg['n_available']} / {agg['n_total']} | "
          f"≥ {cohort['acceptance']['min_available_for_scoring']} | "
          f"{'✅' if agg['n_available'] >= cohort['acceptance']['min_available_for_scoring'] else '⚠'} |"]
    if agg["directional_pct"] is not None:
        # V3.17.4: display rate threshold (legacy abs fallback if older yaml)
        min_rate = cohort["acceptance"].get("min_directional_correct_rate")
        if min_rate is None:
            min_rate = cohort["acceptance"].get("min_directionally_correct", 14) / 18.0
        md.append(f"| Directional correctness | {agg['correct']}/{agg['n_available']} "
                  f"({agg['directional_pct']:.0%}) | ≥ {min_rate:.0%} | "
                  f"{'✅' if agg['directional_ok'] else '🔴'} |")
        md.append(f"| New V3.17 flag trigger rate | {agg['new_flag_trigger_rate']:.0%} | "
                  f"≤ {cohort['acceptance']['max_new_flag_trigger_rate']:.0%} | "
                  f"{'✅' if agg['flag_rate_ok'] else '🔴'} |")
    else:
        md.append(f"| Directional / Flag rate | INSUFFICIENT_DATA | — | ⚠ |")
    md.append("")
    md.append(f"**Overall**: `{agg['acceptance_status']}` "
              f"(missing={agg['n_missing']}, errors={agg['n_errors']})")
    md.append("")
    md.append("---\n")
    md.append("## Per-Ticker Results\n")
    md.append("| Ticker | Bucket | Target | Cache | Δd | Composite | Verdict | "
              "transition_sig | mix | cc_quality | Score | Expected |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        if r["status"] != "OK":
            md.append(f"| {r['ticker']} | {r['bucket']} | {r['target']} | "
                      f"— | — | — | `{r['status']}` | — | — | — | — | {r['expected']} |")
            continue
        score_icon = {"CORRECT": "✅", "PARTIAL": "🟡", "WRONG": "🔴"}.get(r["score"], "?")
        md.append(f"| {r['ticker']} | {r['bucket']} | {r['target']} | "
                  f"{r['cache_date']} | {r['cache_delta_days']} | {r['composite']} | "
                  f"{r['verdict']} | {r['transition_signature']} | {r['mix_tier']} | "
                  f"{r['cash_conversion_quality']} | {score_icon} {r['score']} | {r['expected']} |")
    md.append("")
    md.append("---\n")
    md.append("## Notes\n")
    md.append("- Directional mapping: composite ≥ 65 → directional_up, "
              "35-64 → directional_flat, < 35 → directional_down.")
    md.append("- Acceptance soft-fails (rc=0 + warning) when AVAILABLE < 6 — "
              "treat the cohort as a measurement layer, not an enforcement gate.")
    md.append("- Missing caches reported but excluded from scoring denominator. "
              "Populate caches manually via `python3 skills/earnings-analyst/scripts/fetch.py <T>` "
              "with the appropriate historical period.")
    md.append("- Stale-gate trigger rate is measured separately via "
              "`skills/earnings-analyst/tests/test_stale_gate_simulated.py` (fixture-based) "
              "rather than on historical cache mtime — local filesystem mtime ≠ financial event time.")
    return "\n".join(md)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="", help="markdown report output path (default: reports/calibration_<DATE>.md)")
    ap.add_argument("--json", action="store_true", help="print machine-readable JSON to stdout instead of markdown summary")
    args = ap.parse_args()

    cohort = load_cohort()
    window_days = cohort.get("target_quarter_window_days", 90)
    v317_new_flags = set(cohort.get("acceptance", {}).get("v317_new_flags", []))

    results = []
    for bucket_name, entries in (cohort.get("buckets") or {}).items():
        for entry in entries:
            r = process_entry(
                ticker=entry["ticker"],
                target_iso=entry["target_quarter_end"],
                expected=entry["expected_outcome"],
                bucket=bucket_name,
                window_days=window_days,
                v317_new_flags=v317_new_flags,
            )
            r["notes"] = entry.get("notes", "")
            results.append(r)

    agg = aggregate(results, cohort.get("acceptance") or {})

    if args.json:
        print(json.dumps({"cohort_version": cohort.get("version"),
                          "results": results, "aggregate": agg},
                          indent=2, default=str))
        return 0

    md = render_markdown(cohort, results, agg)
    out_path = args.output or str(REPORTS_DIR / f"calibration_{dt.date.today().isoformat()}.md")
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(md, encoding="utf-8")

    # stderr one-liner summary
    print(f"[calibration] cohort {cohort.get('version')} → {out_path}", file=sys.stderr)
    print(f"  available={agg['n_available']}/{agg['n_total']}  "
          f"missing={agg['n_missing']}  errors={agg['n_errors']}", file=sys.stderr)
    if agg["directional_pct"] is not None:
        print(f"  directional={agg['correct']}/{agg['n_available']} "
              f"({agg['directional_pct']:.0%})  "
              f"v317_flag_rate={agg['new_flag_trigger_rate']:.0%}  "
              f"acceptance={agg['acceptance_status']}", file=sys.stderr)
    else:
        print(f"  acceptance=INSUFFICIENT_DATA (need >= "
              f"{cohort['acceptance']['min_available_for_scoring']} available)", file=sys.stderr)
    return 0  # always soft-pass — see docstring


if __name__ == "__main__":
    sys.exit(main())

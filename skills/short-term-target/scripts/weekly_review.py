#!/usr/bin/env python3
"""
weekly_review — Read past N days of thematic-screener recommendations,
compare predictions to actual yfinance prices, suggest weights.yaml adjustments.

Per plan_short.md Step 7: tool gives suggestions, NEVER auto-overwrites config.
User reviews report, decides which suggestions to apply.

Usage:
  python3 weekly_review.py
  python3 weekly_review.py --days 14
  python3 weekly_review.py --output /tmp/review.md
"""
import os
import sys
import json
import glob
import argparse
import datetime
from pathlib import Path
from collections import defaultdict

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("ERROR: pip install yfinance pandas", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent.parent.parent
RECS_DIR = ROOT / "skills" / "thematic-screener" / "data" / "recommendations"
REPORTS_DIR = ROOT / "reports"
SKILL_DIR = Path(__file__).resolve().parent.parent
WEIGHTS_PATH = SKILL_DIR / "config" / "weights.yaml"


def load_recommendations(days):
    """Load past N days of recommendations files. Returns list of (date, data)."""
    today = datetime.date.today()
    out = []
    for offset in range(days):
        d = today - datetime.timedelta(days=offset)
        p = RECS_DIR / f"{d.isoformat()}.json"
        if p.exists():
            try:
                out.append((d, json.loads(p.read_text())))
            except Exception as e:
                print(f"WARN: failed to parse {p.name}: {e}", file=sys.stderr)
    return out


def fetch_actual_price(ticker, target_date):
    """Get actual close at or just after target_date. Returns float or None."""
    try:
        end = target_date + datetime.timedelta(days=5)
        h = yf.Ticker(ticker).history(
            start=target_date.isoformat(),
            end=end.isoformat(),
            auto_adjust=False,
        )
        if h.empty:
            return None
        return float(h["Close"].iloc[0])
    except Exception:
        return None


def compute_outcomes(rec_files):
    """For each prediction in each file, compute actual outcome.
    Returns list of dicts."""
    today = datetime.date.today()
    horizons_def = {"1d": 1, "5d": 5, "15d": 15}
    rows = []

    for rec_date, data in rec_files:
        for theme_block in data.get("themes", []):
            theme_name = theme_block["name"]
            for mover in theme_block.get("top_movers", []):
                ticker = mover["ticker"]
                st = mover.get("short_term", {})
                if st.get("error"):
                    continue
                current = st.get("current_price")
                horizons = st.get("horizons", {})
                if current is None:
                    continue

                for h, days in horizons_def.items():
                    pred = horizons.get(h, {})
                    if pred.get("status") != "ok":
                        continue
                    target_date = rec_date + datetime.timedelta(days=days)
                    if target_date > today:
                        # Window not elapsed yet
                        continue
                    actual = fetch_actual_price(ticker, target_date)
                    if actual is None:
                        continue
                    actual_pct = (actual / current - 1) * 100
                    pred_pct = pred.get("target_central_pct", 0)
                    error_pct = pred_pct - actual_pct
                    direction_correct = (pred_pct > 0 and actual_pct > 0) or \
                                       (pred_pct < 0 and actual_pct < 0) or \
                                       (abs(pred_pct) < 0.5 and abs(actual_pct) < 0.5)
                    # In-range: actual within [target_low, target_high]
                    in_range = pred.get("target_low", -999) <= actual <= pred.get("target_high", 999)

                    rows.append({
                        "rec_date": rec_date.isoformat(),
                        "ticker": ticker,
                        "theme": theme_name,
                        "horizon": h,
                        "horizon_days": days,
                        "current_price": current,
                        "actual_price": actual,
                        "actual_pct": actual_pct,
                        "pred_pct": pred_pct,
                        "error_pct": error_pct,
                        "direction_correct": direction_correct,
                        "in_range": in_range,
                        "confidence": pred.get("confidence"),
                        "drivers": pred.get("drivers", {}),
                        "weights_version": data.get("themes", [{}])[0].get("short_term", {}).get("weights_version", "unknown")
                                          if data.get("themes") else "unknown",
                    })
    return rows


def per_horizon_stats(rows):
    """Per-horizon hit rate + mean error."""
    by_h = defaultdict(list)
    for r in rows:
        by_h[r["horizon"]].append(r)
    out = {}
    for h, rs in by_h.items():
        n = len(rs)
        if n == 0:
            continue
        hit = sum(1 for r in rs if r["direction_correct"])
        in_range = sum(1 for r in rs if r["in_range"])
        mean_error = sum(r["error_pct"] for r in rs) / n
        mean_pred = sum(r["pred_pct"] for r in rs) / n
        mean_actual = sum(r["actual_pct"] for r in rs) / n
        bias = mean_pred - mean_actual
        out[h] = {
            "n": n,
            "hit_rate_pct": round(hit / n * 100, 1),
            "in_range_pct": round(in_range / n * 100, 1),
            "mean_error_pct": round(mean_error, 2),
            "mean_pred_pct": round(mean_pred, 2),
            "mean_actual_pct": round(mean_actual, 2),
            "directional_bias_pct": round(bias, 2),
        }
    return out


def per_theme_stats(rows):
    """Per-theme alpha (5d horizon only — easiest to evaluate)."""
    by_t = defaultdict(list)
    for r in rows:
        if r["horizon"] == "5d":
            by_t[r["theme"]].append(r)
    out = {}
    for t, rs in by_t.items():
        n = len(rs)
        if n == 0:
            continue
        hit = sum(1 for r in rs if r["direction_correct"])
        mean_actual = sum(r["actual_pct"] for r in rs) / n
        mean_pred = sum(r["pred_pct"] for r in rs) / n
        out[t] = {
            "n": n,
            "hit_rate_pct": round(hit / n * 100, 1),
            "mean_pred_pct": round(mean_pred, 2),
            "mean_actual_pct": round(mean_actual, 2),
            "model_bias_pct": round(mean_pred - mean_actual, 2),
        }
    return out


def failed_cases(rows, top_n=5):
    """Worst N predictions (largest absolute error)."""
    sorted_rows = sorted(rows, key=lambda r: abs(r["error_pct"]), reverse=True)
    return sorted_rows[:top_n]


def suggest_weight_adjustments(per_h, per_t):
    """v0.1 simple suggestions. Returns list of strings."""
    suggestions = []

    for h, stats in per_h.items():
        n = stats["n"]
        if n < 5:
            suggestions.append(
                f"⚠️ {h}: only {n} samples — collect more before any adjustment"
            )
            continue
        bias = stats["directional_bias_pct"]
        hit = stats["hit_rate_pct"]
        if hit < 50:
            suggestions.append(
                f"🔴 {h}: hit_rate {hit}% < 50% (random walk). Consider reducing all weights "
                f"for this horizon by 20-30% to dampen overconfidence"
            )
        elif hit > 70:
            suggestions.append(
                f"🟢 {h}: hit_rate {hit}% > 70% (good). Current weights working well"
            )
        if abs(bias) > 1.5:
            direction = "OVER-predicts" if bias > 0 else "UNDER-predicts"
            suggestions.append(
                f"🟡 {h}: model {direction} by {abs(bias):.1f}% on average. "
                f"Consider {'reducing' if bias > 0 else 'increasing'} alpha_news + gamma_momentum "
                f"weights for this horizon by ~10%"
            )

    # Per-theme: any theme with < 30% hit rate AND ≥ 5 samples → flag for removal
    for t, stats in per_t.items():
        if stats["n"] >= 5 and stats["hit_rate_pct"] < 30:
            suggestions.append(
                f"🔴 Theme '{t}' (5d): hit_rate {stats['hit_rate_pct']}% on {stats['n']} samples. "
                f"Consider removing from screener watchlist OR investigate driver mis-calibration"
            )

    if not suggestions:
        suggestions.append("✓ No systematic miscalibration detected at this sample size. Continue collecting.")
    return suggestions


def render_report(rows, days, run_date):
    if not rows:
        return "\n".join([
            f"# Short-Term Recommendation Weekly Review — {run_date}",
            "",
            f"**Window**: past {days} days",
            "",
            "## ⚠ No outcomes available",
            "",
            "Either no recommendations files exist, OR all predictions are still within their "
            "evaluation window (i.e., prediction date + horizon hasn't passed yet).",
            "",
            f"Check: `ls {RECS_DIR}/`",
            "",
            "Recommendations need at least:",
            "- 1 day elapsed for `1d` horizon evaluation",
            "- 5 days elapsed for `5d` horizon evaluation",
            "- 15 days elapsed for `15d` horizon evaluation",
        ])

    per_h = per_horizon_stats(rows)
    per_t = per_theme_stats(rows)
    fails = failed_cases(rows, top_n=5)
    suggestions = suggest_weight_adjustments(per_h, per_t)

    lines = [
        f"# Short-Term Recommendation Weekly Review — {run_date}",
        "",
        f"**Window**: past {days} days  |  **Total predictions evaluated**: {len(rows)}  |  "
        f"**Unique tickers**: {len(set(r['ticker'] for r in rows))}",
        "",
        "**Method**: For each prediction in `data/recommendations/<date>.json`, fetch actual "
        "yfinance close at `prediction_date + horizon_days`, compute hit/miss + range coverage + bias.",
        "",
        "---",
        "",
        "## 1. Per-horizon hit rate & bias",
        "",
        "| Horizon | N | Hit Rate (direction) | In-Range | Mean Pred | Mean Actual | Bias (pred-actual) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for h in ["1d", "5d", "15d"]:
        if h not in per_h:
            lines.append(f"| {h} | — | — | — | — | — | — |")
            continue
        s = per_h[h]
        lines.append(
            f"| {h} | {s['n']} | {s['hit_rate_pct']}% | {s['in_range_pct']}% | "
            f"{s['mean_pred_pct']:+.2f}% | {s['mean_actual_pct']:+.2f}% | {s['directional_bias_pct']:+.2f}% |"
        )

    lines += [
        "",
        "**Read this**:",
        "- `Hit Rate` < 50% = worse than random walk; > 70% = strong signal",
        "- `In-Range` = % of cases where actual price fell within [target_low, target_high]",
        "- `Bias` > 0 = model OVER-predicts (more bullish than reality); < 0 = UNDER-predicts",
        "",
        "---",
        "",
        "## 2. Per-theme 5d alpha breakdown",
        "",
        "| Theme | N | Hit Rate | Mean Pred | Mean Actual | Model Bias |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for t, s in sorted(per_t.items(), key=lambda kv: -kv[1]["n"]):
        lines.append(
            f"| {t} | {s['n']} | {s['hit_rate_pct']}% | "
            f"{s['mean_pred_pct']:+.2f}% | {s['mean_actual_pct']:+.2f}% | {s['model_bias_pct']:+.2f}% |"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. Worst 5 predictions (by absolute error)",
        "",
        "| Date | Ticker | Theme | Horizon | Pred | Actual | Error | Confidence |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for f in fails:
        lines.append(
            f"| {f['rec_date']} | {f['ticker']} | {f['theme'][:20]} | {f['horizon']} | "
            f"{f['pred_pct']:+.2f}% | {f['actual_pct']:+.2f}% | {f['error_pct']:+.2f}% | {f['confidence']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 4. Suggested adjustments",
        "",
        "**These are SUGGESTIONS only**. The tool does NOT auto-apply changes. ",
        f"Edit `{WEIGHTS_PATH.relative_to(ROOT)}` manually if you accept any.",
        "",
    ]
    for s in suggestions:
        lines.append(f"- {s}")

    lines += [
        "",
        "**To apply changes**:",
        "1. Edit `skills/short-term-target/config/weights.yaml`",
        "2. Bump `weights_version` field (e.g., `v0.1.0` → `v0.1.1`)",
        "3. Future predictions tagged with new version → enables before/after comparison",
        "",
        "---",
        "",
        "## 5. KPI gate (per plan_short.md §6 + §12.H)",
        "",
    ]
    # KPI check: 8-week hit rate < 50% OR median alpha < 0
    # For 5d horizon
    if "5d" in per_h:
        s5 = per_h["5d"]
        kpi_ok = s5["hit_rate_pct"] >= 50 and s5["mean_actual_pct"] >= 0
        status = "🟢 PASS" if kpi_ok else "🔴 FAIL"
        lines.append(f"**5d hit rate**: {s5['hit_rate_pct']}% (must be ≥ 50%)  →  {status}")
        lines.append(f"**5d realized**: {s5['mean_actual_pct']:+.2f}% (must be ≥ 0%)  →  "
                     f"{'🟢' if s5['mean_actual_pct'] >= 0 else '🔴'}")
        lines.append("")
        if not kpi_ok and s5["n"] >= 30:
            lines.append("⚠️ **KPI failed at N ≥ 30**. Per plan_short.md §6: consider retiring the system.")
        elif s5["n"] < 30:
            lines.append(f"📊 **N = {s5['n']}** — too few samples for KPI judgment (need ≥ 30). "
                         f"Continue collecting.")
    else:
        lines.append("**5d horizon**: insufficient data for KPI evaluation")

    lines += [
        "",
        "---",
        "",
        "*Generated by `weekly_review.py`. Tool location: `skills/short-term-target/scripts/`*",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7,
                    help="Window in days to scan (default 7)")
    ap.add_argument("--output", default=None,
                    help="Output path (default: reports/SHORT_TERM_WEEKLY_<DATE>.md)")
    args = ap.parse_args()

    print(f"Loading recommendations from past {args.days} days...", file=sys.stderr)
    rec_files = load_recommendations(args.days)
    print(f"Found {len(rec_files)} recommendation files", file=sys.stderr)

    if not rec_files:
        rows = []
    else:
        print("Computing outcomes (yfinance fetches)...", file=sys.stderr)
        rows = compute_outcomes(rec_files)
        print(f"Evaluated {len(rows)} predictions with elapsed window", file=sys.stderr)

    run_date = datetime.date.today().isoformat()
    report = render_report(rows, args.days, run_date)

    if args.output:
        out_path = Path(args.output)
    else:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = REPORTS_DIR / f"SHORT_TERM_WEEKLY_{run_date}.md"
    out_path.write_text(report)
    print(f"\nWrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

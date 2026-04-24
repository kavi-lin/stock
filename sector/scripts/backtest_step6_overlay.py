#!/usr/bin/env python3
"""
Backtest the Step 6 FRED Regime Overlay against historical sector_intel.json
runs and forward sector ETF returns.

Methodology:
  1. Walk every `sector_logs/*_sector_intel.json` (chronological)
  2. For each date D, fetch FRED snapshot via `fred-macro --asof D`
  3. Compute Step 6 multiplier for each sector via step6_overlay.compute_multiplier
  4. Pull D+30 / D+60 / D+90 forward returns of each sector's proxy_etf via yfinance
  5. Per-date, score top-vs-bottom spread:
       - spread_orig  = mean fwd return of top-3 scored sectors  − bottom-3
       - spread_step6 = mean fwd return of top-3 (score × step6) − bottom-3 (score × step6)
  6. Aggregate across dates → "Did overlay improve top-bottom spread?"

Run:
    python3 sector/scripts/backtest_step6_overlay.py
        --window 30 60 90    # forward windows (days)
        --min-fwd-days 30    # skip dates without sufficient forward data
        --csv backtest.csv   # optional CSV dump

Note: with only ~12 sessions of data this is more "smoke test + scaffold" than
proper backtest. As log accumulates the same script becomes statistically valid.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import statistics
import subprocess
import sys
from datetime import date, datetime, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "sector/scripts"))
from step6_overlay import compute_multiplier  # noqa: E402

LOGS_DIR  = os.path.join(ROOT, "sector/sector_logs")
FRED_SCRIPT = os.path.join(ROOT, "skills/fred-macro/scripts/fetch.py")


def parse_intel(path):
    with open(path) as f:
        d = json.load(f)
    sectors = []
    for s in d.get("sectors", []):
        if not s.get("proxy_etf"):
            continue
        sectors.append({
            "name":   s["name"],
            "etf":    s["proxy_etf"],
            "score":  s.get("composite_score", 0),
            "verdict": s.get("verdict"),
        })
    return d.get("verdict_date"), sectors


def fred_asof(asof_date):
    """Fetch FRED slim snapshot --asof DATE. Returns dict shaped like _phase0.fred_snapshot."""
    try:
        out = subprocess.run(
            ["python3", FRED_SCRIPT, "--asof", asof_date, "--no-cache", "--json-only"],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        full = json.loads(out.stdout)
    except Exception as e:
        print(f"  ⚠️ FRED fetch failed for {asof_date}: {e}", file=sys.stderr)
        return None
    rs = full.get("regime_signals") or {}
    sr = full.get("sector_rotation") or {}
    return {
        "regime_label":          full.get("regime_label"),
        "regime_confidence":     full.get("regime_confidence"),
        "yield_curve_inverted":  rs.get("yield_curve_inverted"),
        "credit_stress_elevated":rs.get("credit_stress_elevated"),
        "real_rate_preferred":   rs.get("real_rate_preferred"),
        "sector_rotation_favor": sr.get("favor", []),
        "sector_rotation_avoid": sr.get("avoid", []),
    }


def fwd_return_yf(etf, start_date, days):
    """Forward-return of `etf` from `start_date` over `days` calendar days. Uses yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        return None
    end_date = (datetime.fromisoformat(start_date) + timedelta(days=days + 5)).strftime("%Y-%m-%d")
    try:
        df = yf.download(etf, start=start_date, end=end_date, progress=False, auto_adjust=True)
        if df is None or df.empty or len(df) < 2:
            return None
        # yfinance may return MultiIndex columns when single ticker; flatten by taking ('Close', etf) or 'Close'.
        close = df["Close"]
        if hasattr(close, "columns"):  # DataFrame (multi-index case)
            close = close.iloc[:, 0]
        first = float(close.iloc[0])
        # Find closest trading day to start_date + days
        target = datetime.fromisoformat(start_date) + timedelta(days=days)
        idx = close.index.searchsorted(target)
        if idx >= len(close):
            idx = len(close) - 1
        last = float(close.iloc[idx])
        return round((last / first - 1.0) * 100, 2)
    except Exception as e:
        return None


def top_bottom_spread(scored_sectors, k=3):
    """Given list of (score, fwd_return), return mean(top-k) - mean(bottom-k)."""
    valid = [(s, r) for s, r in scored_sectors if r is not None]
    if len(valid) < 2 * k:
        return None
    valid.sort(key=lambda x: x[0], reverse=True)
    top    = [r for _, r in valid[:k]]
    bottom = [r for _, r in valid[-k:]]
    return round(statistics.mean(top) - statistics.mean(bottom), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, nargs="+", default=[30, 60, 90])
    ap.add_argument("--min-fwd-days", type=int, default=30,
                    help="skip dates where today - intel_date < min-fwd-days (insufficient forward window)")
    ap.add_argument("--csv", help="dump per-row backtest data to CSV")
    ap.add_argument("--limit", type=int, help="limit to N most recent dates (for quick smoke test)")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(LOGS_DIR, "*_sector_intel.json")))
    if args.limit:
        files = files[-args.limit:]
    if not files:
        print("No sector_intel.json files found.", file=sys.stderr)
        sys.exit(1)

    today = date.today()
    rows = []
    summary = {w: {"orig": [], "step6": []} for w in args.window}

    for path in files:
        intel_date, sectors = parse_intel(path)
        if not intel_date:
            continue
        try:
            d_obj = datetime.strptime(intel_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        max_window = max(args.window)
        days_elapsed = (today - d_obj).days
        if days_elapsed < args.min_fwd_days:
            print(f"⏭  {intel_date} — only {days_elapsed}d elapsed (< min-fwd-days {args.min_fwd_days}), skipping")
            continue

        print(f"\n=== {intel_date} ({len(sectors)} sectors) ===")
        snap = fred_asof(intel_date)
        if not snap:
            print(f"  ⚠️ no FRED snapshot — skipping")
            continue
        print(f"  FRED regime={snap['regime_label']}, conf={snap['regime_confidence']}")

        scored = []
        for s in sectors:
            mult = compute_multiplier(s["name"], snap)["effective"]
            adjusted = round(s["score"] * mult, 2)
            fwd = {}
            for w in args.window:
                if days_elapsed >= w:
                    fwd[w] = fwd_return_yf(s["etf"], intel_date, w)
                else:
                    fwd[w] = None
            scored.append({
                "name": s["name"], "etf": s["etf"],
                "score_orig": s["score"], "step6_mult": mult,
                "score_step6": adjusted, "fwd": fwd,
            })
            for w in args.window:
                rows.append({
                    "date": intel_date, "sector": s["name"], "etf": s["etf"],
                    "regime": snap["regime_label"],
                    "regime_conf": snap["regime_confidence"],
                    "score_orig": s["score"], "step6_mult": mult,
                    "score_step6": adjusted, "window_days": w, "fwd_return_pct": fwd[w],
                })

        # Spread analysis per window
        for w in args.window:
            sd_orig = top_bottom_spread(
                [(x["score_orig"],  x["fwd"][w]) for x in scored], k=3)
            sd_step6 = top_bottom_spread(
                [(x["score_step6"], x["fwd"][w]) for x in scored], k=3)
            if sd_orig is None or sd_step6 is None:
                continue
            summary[w]["orig"].append(sd_orig)
            summary[w]["step6"].append(sd_step6)
            improvement = sd_step6 - sd_orig
            print(f"  fwd-{w:>3}d  spread_orig={sd_orig:+.2f}%  spread_step6={sd_step6:+.2f}%  Δ={improvement:+.2f}pp")

    # Aggregate
    print("\n" + "=" * 60)
    print("AGGREGATE — Step 6 overlay impact (top-3 minus bottom-3 spread)")
    print("=" * 60)
    print(f"{'window':>10} {'n':>4} {'mean_orig%':>12} {'mean_step6%':>13} {'Δ pp':>8} {'n_wins':>8}")
    for w in args.window:
        orig = summary[w]["orig"]
        step6 = summary[w]["step6"]
        if not orig:
            print(f"{w:>10}d {0:>4}  insufficient forward data")
            continue
        n = len(orig)
        wins = sum(1 for o, s in zip(orig, step6) if s > o)
        print(f"{w:>10}d {n:>4} {statistics.mean(orig):>11.2f}% {statistics.mean(step6):>12.2f}% "
              f"{statistics.mean(step6) - statistics.mean(orig):>+7.2f} {wins:>4}/{n:<3}")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            if rows:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
        print(f"\nWrote {len(rows)} rows → {args.csv}")

    print("\nNote: with current sample (~12 sessions, weeks of forward data) results are")
    print("indicative only. Re-run as more sessions accumulate (target n ≥ 50).")


if __name__ == "__main__":
    main()

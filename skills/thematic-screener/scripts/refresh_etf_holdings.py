#!/usr/bin/env python3
"""
refresh_etf_holdings.py — Auto-refresh themes.yaml static_stocks from ETF top holdings.

For each theme in themes.yaml:
  1. Fetch top holdings from each proxy_etf via yfinance
  2. Union + dedup across that theme's ETFs
  3. Filter out non-US-tradeable tickers (.TA / .SW / .T / .HK / .PA / .SZ etc)
  4. Cap to top N by combined weight (default 25)
  5. Update theme.static_stocks + theme.universe_size_estimate

Bumps `etf_holdings_last_refreshed` in skills/thematic-screener/etf_meta.yaml.

Usage:
  python3 refresh_etf_holdings.py                 # actual refresh
  python3 refresh_etf_holdings.py --dry-run       # preview, no write
  python3 refresh_etf_holdings.py --top-n 30      # different cap
"""
import os
import sys
import argparse
import datetime
import re
from pathlib import Path
from collections import defaultdict

try:
    import yfinance as yf
    import yaml
except ImportError:
    print("ERROR: pip install yfinance pyyaml", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent.parent.parent
THEMES_YAML = Path(__file__).resolve().parent.parent.parent / "theme-detector" / "scripts" / "themes.yaml"
META_YAML = Path(__file__).resolve().parent.parent / "etf_meta.yaml"

# US-tradeable: no dot suffix in ticker (foreign listings use suffixes like
# .TA, .SS, .AX, .MC, .SA, .CO, .LS, .HK, .T, .L, etc.). Berkshire B is BRK-B
# (dash, not dot) in yfinance data, so this filter is safe.
def is_us_tradeable(ticker):
    """Filter out tickers with foreign-exchange suffix (any '.' in ticker)."""
    if "." in ticker:
        return False
    if ticker.replace("-", "").isdigit():
        return False
    return True


def fetch_etf_top_holdings(etf):
    """Return list of (ticker, weight) for ETF's top holdings (typically top 10)."""
    try:
        t = yf.Ticker(etf)
        fd = t.funds_data
        if not fd:
            return []
        th = fd.top_holdings
        if th is None or th.empty:
            return []
        out = []
        for ticker, row in th.iterrows():
            weight = row.get("Holding Percent", 0)
            out.append((str(ticker), float(weight) if weight else 0.0))
        return out
    except Exception as e:
        print(f"  ERR {etf}: {e}", file=sys.stderr)
        return []


def merge_theme_holdings(etfs, top_n):
    """For a theme's ETFs, fetch + merge + dedup + cap."""
    weight_map = defaultdict(float)
    appearance_count = defaultdict(int)
    raw_total = 0
    for etf in etfs:
        print(f"  ETF {etf}...", file=sys.stderr)
        holdings = fetch_etf_top_holdings(etf)
        raw_total += len(holdings)
        for ticker, weight in holdings:
            if not is_us_tradeable(ticker):
                continue
            # Sum weights across ETFs (a ticker in multiple ETFs gets weight sum)
            weight_map[ticker] += weight
            appearance_count[ticker] += 1
    # Sort by combined weight desc; tie-break by appearance count
    ranked = sorted(weight_map.items(), key=lambda kv: (-kv[1], -appearance_count[kv[0]]))
    selected = [t for t, w in ranked[:top_n]]
    return {
        "selected": selected,
        "n_unique_us": len(weight_map),
        "n_raw_holdings": raw_total,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Preview only, don't write")
    ap.add_argument("--top-n", type=int, default=25, help="Max stocks per theme (default 25)")
    args = ap.parse_args()

    if not THEMES_YAML.exists():
        print(f"ERROR: {THEMES_YAML} not found", file=sys.stderr)
        sys.exit(1)

    cfg = yaml.safe_load(THEMES_YAML.read_text())
    themes = cfg.get("cross_sector", [])
    print(f"Refreshing {len(themes)} themes from ETF holdings...", file=sys.stderr)
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'WRITE'}  |  top_n={args.top_n}\n", file=sys.stderr)

    refreshed_at = datetime.date.today().isoformat()
    summary = []

    for theme in themes:
        name = theme.get("theme_name")
        etfs = theme.get("proxy_etfs", []) or []
        if not etfs:
            print(f"[{name}] no proxy_etfs — skip", file=sys.stderr)
            summary.append({"name": name, "status": "no_etfs", "before": len(theme.get("static_stocks", [])), "after": None})
            continue

        print(f"[{name}] etfs={etfs}", file=sys.stderr)
        result = merge_theme_holdings(etfs, args.top_n)
        new_stocks = result["selected"]
        old_stocks = theme.get("static_stocks", [])
        n_kept_overlap = len(set(new_stocks) & set(old_stocks))

        # Update in-place
        if not args.dry_run:
            theme["static_stocks"] = new_stocks
            theme["universe_size_estimate"] = max(result["n_unique_us"], len(new_stocks))
            theme["etf_holdings_last_refreshed"] = refreshed_at

        summary.append({
            "name": name,
            "status": "ok",
            "before": len(old_stocks),
            "after": len(new_stocks),
            "overlap": n_kept_overlap,
            "universe": result["n_unique_us"],
        })
        print(f"  → {len(new_stocks)} stocks (was {len(old_stocks)}, overlap {n_kept_overlap}, universe ~{result['n_unique_us']})\n", file=sys.stderr)

    # Print summary
    print("\n" + "=" * 70, file=sys.stderr)
    print(f"{'Theme':<48} {'Before':>7} {'After':>6} {'Overlap':>8} {'Univ':>5}", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    for s in summary:
        if s["status"] == "ok":
            print(f"{s['name']:<48} {s['before']:>7} {s['after']:>6} {s['overlap']:>8} {s['universe']:>5}", file=sys.stderr)
        else:
            print(f"{s['name']:<48} ({s['status']})", file=sys.stderr)

    if args.dry_run:
        print("\nDRY-RUN — no files written.", file=sys.stderr)
        return

    # Write themes.yaml back
    THEMES_YAML.write_text(yaml.dump(cfg, sort_keys=False, allow_unicode=True))
    print(f"\n✓ Updated {THEMES_YAML}", file=sys.stderr)

    # Bump etf_meta.yaml
    META_YAML.parent.mkdir(parents=True, exist_ok=True)
    meta = {}
    if META_YAML.exists():
        try:
            meta = yaml.safe_load(META_YAML.read_text()) or {}
        except Exception:
            meta = {}
    meta["etf_holdings_last_refreshed"] = refreshed_at
    meta["last_refresh_summary"] = {
        "themes_refreshed": sum(1 for s in summary if s["status"] == "ok"),
        "themes_skipped":   sum(1 for s in summary if s["status"] != "ok"),
        "total_unique_tickers": sum(s.get("after", 0) for s in summary if s["status"] == "ok"),
    }
    META_YAML.write_text(yaml.dump(meta, sort_keys=False, allow_unicode=True))
    print(f"✓ Updated {META_YAML}", file=sys.stderr)


if __name__ == "__main__":
    main()

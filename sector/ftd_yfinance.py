#!/usr/bin/env python3
"""
FTD Detector — yfinance adapter

Replaces the FMP API client with yfinance so the existing ftd-detector
skill logic works without an FMP subscription.

Data fetched: ^GSPC (S&P 500) + QQQ — 100 trading days of OHLCV.

Usage:
    python3 sector/ftd_yfinance.py [--output-dir sector/ftd_cache/]

Output (same as original skill):
    ftd_cache/ftd_detector_YYYY-MM-DD_HHMMSS.json
    ftd_cache/ftd_detector_YYYY-MM-DD_HHMMSS.md
"""

import argparse
import os
import sys
from datetime import datetime

# ── yfinance ─────────────────────────────────────────────────────────────────
try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)

# ── inject skill path so we can reuse its analysis functions ─────────────────
SKILL_SCRIPTS = os.path.expanduser(
    "~/.claude/skills/ftd-detector/scripts"
)
if SKILL_SCRIPTS not in sys.path:
    sys.path.insert(0, SKILL_SCRIPTS)

try:
    from post_ftd_monitor import assess_post_ftd_health
    from rally_tracker import get_market_state
    from report_generator import generate_json_report, generate_markdown_report
except ImportError as e:
    print(f"ERROR: Cannot import ftd-detector skill: {e}", file=sys.stderr)
    print(f"  Expected skill at: {SKILL_SCRIPTS}", file=sys.stderr)
    sys.exit(1)


# ── yfinance → FMP-compatible list[dict] ─────────────────────────────────────

def fetch_history(ticker: str, days: int = 100) -> list[dict]:
    """Download OHLCV for `ticker`, return newest-first list of dicts."""
    period = f"{max(days + 30, 130)}d"   # buffer for weekends/holidays
    df = yf.download(ticker, period=period, auto_adjust=True,
                     progress=False, multi_level_index=False)
    if df.empty:
        return []
    # Flatten multi-level columns if present (e.g. ("Close","^GSPC") → "Close")
    if isinstance(df.columns, type(df.columns)) and hasattr(df.columns, 'levels'):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.tail(days)
    records = []
    for dt, row in df.iterrows():
        records.append({
            "date":   dt.strftime("%Y-%m-%d"),
            "open":   float(row["Open"]),
            "high":   float(row["High"]),
            "low":    float(row["Low"]),
            "close":  float(row["Close"]),
            "volume": int(row["Volume"]),
        })
    # Return newest-first (FMP convention)
    return list(reversed(records))


def fetch_quote(ticker: str) -> dict:
    """Return a minimal quote dict with 'price' key."""
    tk = yf.Ticker(ticker)
    info = tk.fast_info
    price = getattr(info, "last_price", None) or getattr(info, "regularMarketPrice", None)
    if price is None:
        hist = yf.download(ticker, period="2d", auto_adjust=True, progress=False)
        price = float(hist["Close"].iloc[-1]) if not hist.empty else 0.0
    return {"price": float(price)}


# ── _serialize_index (copied from ftd_detector.py) ───────────────────────────

def _serialize_index(idx_data: dict) -> dict:
    """Make index data JSON-serializable (mirrors original ftd_detector.py)."""
    result = {}
    for k, v in idx_data.items():
        if k == "history":
            continue   # skip raw history
        result[k] = v
    return result


# ── main ─────────────────────────────────────────────────────────────────────

def parse_arguments():
    p = argparse.ArgumentParser(description="FTD Detector (yfinance adapter)")
    p.add_argument("--output-dir", default=".", help="Output directory for reports")
    return p.parse_args()


def main():
    args = parse_arguments()
    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 70)
    print("FTD Detector (yfinance adapter)")
    print("Follow-Through Day Bottom Confirmation — Dual Index (SPY + QQQ)")
    print("=" * 70)

    # ── Step 1: Fetch data ────────────────────────────────────────────────
    print("\nStep 1: Fetching Market Data (yfinance)")
    print("-" * 70)

    print("  Fetching S&P 500 history (^GSPC)...", end=" ", flush=True)
    sp500_history = fetch_history("^GSPC", days=100)
    if not sp500_history:
        print("FAILED")
        print("ERROR: Cannot proceed without S&P 500 data", file=sys.stderr)
        sys.exit(1)
    print(f"OK ({len(sp500_history)} days, latest: {sp500_history[0]['date']})")

    print("  Fetching QQQ history...", end=" ", flush=True)
    qqq_history = fetch_history("QQQ", days=100)
    if qqq_history:
        print(f"OK ({len(qqq_history)} days)")
    else:
        print("WARN — QQQ unavailable, single-index mode")

    print("  Fetching S&P 500 quote...", end=" ", flush=True)
    sp500_quote = fetch_quote("^GSPC")
    print(f"OK (${sp500_quote['price']:.2f})")

    print("  Fetching QQQ quote...", end=" ", flush=True)
    qqq_quote = fetch_quote("QQQ")
    print(f"OK (${qqq_quote['price']:.2f})")

    # ── Step 2: State machine ─────────────────────────────────────────────
    print("\nStep 2: Analyzing Market State")
    print("-" * 70)

    market_state = get_market_state(sp500_history, qqq_history)

    print(f"  S&P 500 State: {market_state['sp500']['state']}")
    print(f"  NASDAQ State:  {market_state['nasdaq']['state']}")
    print(f"  Combined:      {market_state['combined_state']}")

    for label, idx in [("S&P 500", market_state["sp500"]), ("NASDAQ", market_state["nasdaq"])]:
        sw = idx.get("swing_low")
        if sw:
            print(f"  {label} Swing Low: {sw['swing_low_date']} "
                  f"(${sw['swing_low_price']:.2f}, {sw['decline_pct']:.1f}% decline)")
        ra = idx.get("rally_attempt")
        if ra and ra.get("day1_date"):
            print(f"  {label} Rally Day 1: {ra['day1_date']} (Day {ra['current_day_count']})")

    # ── Step 3: Post-FTD health ───────────────────────────────────────────
    print("\nStep 3: Post-FTD Health Assessment")
    print("-" * 70)

    sp500_chrono = list(reversed(sp500_history))
    qqq_chrono   = list(reversed(qqq_history)) if qqq_history else []
    market_state = assess_post_ftd_health(market_state, sp500_chrono, qqq_chrono)

    quality = market_state.get("quality_score", {})
    print(f"  Quality Score: {quality.get('total_score', 0)}/100")
    print(f"  Signal:        {quality.get('signal', 'N/A')}")
    print(f"  Guidance:      {quality.get('guidance', 'N/A')}")
    print(f"  Exposure:      {quality.get('exposure_range', 'N/A')}")

    pt   = market_state.get("power_trend", {})
    dist = market_state.get("post_ftd_distribution", {})
    inv  = market_state.get("ftd_invalidation", {})

    if pt:
        print(f"  Power Trend: {'YES' if pt.get('power_trend') else 'No'} "
              f"({pt.get('conditions_met', 0)}/3 conditions)")
    if dist:
        print(f"  Distribution Days: {dist.get('distribution_count', 0)} "
              f"(monitored {dist.get('days_monitored', 0)} days)")
    if inv and inv.get("invalidated"):
        print(f"  FTD INVALIDATED: {inv.get('invalidation_date')} "
              f"({inv.get('days_after_ftd')} days after FTD)")

    # ── Step 4: Generate reports ──────────────────────────────────────────
    print("\nStep 4: Generating Reports")
    print("-" * 70)

    analysis = {
        "metadata": {
            "generated_at":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_source":   "yfinance",
            "index_prices":  {
                "sp500": sp500_quote["price"],
                "qqq":   qqq_quote["price"],
            },
        },
        "market_state": {
            "combined_state":    market_state["combined_state"],
            "dual_confirmation": market_state["dual_confirmation"],
            "ftd_index":         market_state.get("ftd_index"),
        },
        "sp500":                 _serialize_index(market_state["sp500"]),
        "nasdaq":                _serialize_index(market_state["nasdaq"]),
        "quality_score":         quality,
        "post_ftd_distribution": dist,
        "ftd_invalidation":      inv,
        "power_trend":           pt,
    }

    ts        = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    json_file = os.path.join(args.output_dir, f"ftd_detector_{ts}.json")
    md_file   = os.path.join(args.output_dir, f"ftd_detector_{ts}.md")

    generate_json_report(analysis, json_file)
    generate_markdown_report(analysis, md_file)

    print()
    print("=" * 70)
    print("FTD Analysis Complete")
    print("=" * 70)
    print(f"  State:         {market_state['combined_state']}")
    print(f"  Quality Score: {quality.get('total_score', 0)}/100")
    print(f"  Signal:        {quality.get('signal', 'N/A')}")
    print(f"  JSON:          {json_file}")
    print(f"  Markdown:      {md_file}")


if __name__ == "__main__":
    main()

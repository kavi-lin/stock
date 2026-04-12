#!/usr/bin/env python3
"""
Market Top Detector — yfinance adapter

Replaces the FMP API client with yfinance so the existing market-top-detector
skill logic works without an FMP subscription.

Data fetched via yfinance: ^GSPC, QQQ, ^VIX, ^VIX3M, Leading ETFs, Sector ETFs.
200DMA breadth is auto-fetched from TraderMonty CSV (same as original skill).
breadth-50dma and put-call ratio passed as optional CLI args (gracefully omitted).

Usage:
    python3 sector/market_top_yfinance.py [--output-dir sector/market_top_cache/]
    python3 sector/market_top_yfinance.py --breadth-50dma 45.0 --put-call 0.72

Output (same as original skill):
    market_top_cache/market_top_YYYY-MM-DD_HHMMSS.json
    market_top_cache/market_top_YYYY-MM-DD_HHMMSS.md
"""

import argparse
import os
import sys
import time
from datetime import datetime
from typing import Optional

# ── yfinance ─────────────────────────────────────────────────────────────────
try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)

# ── inject skill path so we can reuse all analysis functions ─────────────────
SKILL_SCRIPTS = os.path.expanduser(
    "~/.claude/skills/market-top-detector/scripts"
)
if SKILL_SCRIPTS not in sys.path:
    sys.path.insert(0, SKILL_SCRIPTS)

try:
    from breadth_csv_client import fetch_breadth_200dma
    from calculators.breadth_calculator import calculate_breadth_divergence
    from calculators.defensive_rotation_calculator import (
        DEFENSIVE_ETFS, OFFENSIVE_ETFS, calculate_defensive_rotation,
    )
    from calculators.distribution_day_calculator import calculate_distribution_days
    from calculators.index_technical_calculator import calculate_index_technical
    from calculators.leading_stock_calculator import (
        CANDIDATE_POOL, LEADING_ETFS, calculate_leading_stock_health, select_dynamic_basket,
    )
    from calculators.sentiment_calculator import calculate_sentiment
    from historical_comparator import compare_to_historical
    from report_generator import generate_json_report, generate_markdown_report
    from scenario_engine import generate_scenarios
    from scorer import calculate_composite_score, detect_follow_through_day
except ImportError as e:
    print(f"ERROR: Cannot import market-top-detector skill: {e}", file=sys.stderr)
    print(f"  Expected skill at: {SKILL_SCRIPTS}", file=sys.stderr)
    sys.exit(1)


# ── yfinance helpers ──────────────────────────────────────────────────────────

def _fetch_history_df(ticker: str, days: int):
    """Download OHLCV DataFrame for ticker, returning enough trading days."""
    period = f"{max(days + 40, 150)}d"
    df = yf.download(ticker, period=period, auto_adjust=True,
                     progress=False, multi_level_index=False)
    if df.empty:
        return None
    # Keep only the last `days` rows
    df = df.tail(days)
    return df


def fetch_history(ticker: str, days: int = 260) -> list[dict]:
    """Download OHLCV, return newest-first list of dicts (FMP-compatible)."""
    df = _fetch_history_df(ticker, days)
    if df is None:
        return []
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
    return list(reversed(records))  # newest first


def fetch_quote(ticker: str, history: Optional[list[dict]] = None) -> Optional[dict]:
    """
    Return FMP-compatible quote dict with price, yearHigh, symbol.
    yearHigh is computed from supplied history (52-wk = ~252 days) or fetched fresh.
    """
    tk = yf.Ticker(ticker)
    info = tk.fast_info

    price = getattr(info, "last_price", None) or getattr(info, "regularMarketPrice", None)
    if price is None:
        # Fallback: read from most-recent bar in history
        if history:
            price = history[0].get("close", 0.0)
        else:
            return None

    # Compute yearHigh from history if available, else from fast_info
    year_high = None
    if history:
        # Use most recent 252 bars as proxy for 52-week window
        window = history[:252]
        year_high = max(d.get("high", 0) for d in window) if window else None
    if not year_high:
        year_high = getattr(info, "year_high", None)
    if not year_high:
        year_high = price  # safe fallback (distance = 0%)

    return {
        "symbol":  ticker,
        "price":   float(price),
        "yearHigh": float(year_high),
    }


# ── yfinance FMPClient drop-in replacement ────────────────────────────────────

class YFinanceClient:
    """
    Drop-in replacement for FMPClient using yfinance.
    Implements only the methods called by market_top_detector.py.
    """

    def __init__(self):
        self._history_cache: dict[str, list[dict]] = {}
        self._quote_cache: dict[str, dict] = {}
        self._fetch_count = 0

    # ── core fetch (with per-symbol cache) ───────────────────────────────────

    def _get_history(self, symbol: str, days: int) -> list[dict]:
        cache_key = f"{symbol}_{days}"
        if cache_key not in self._history_cache:
            print(f"    yfinance: {symbol} ({days}d)...", end=" ", flush=True)
            hist = fetch_history(symbol, days)
            self._history_cache[cache_key] = hist
            self._fetch_count += 1
            if hist:
                print(f"OK ({len(hist)} bars, latest: {hist[0]['date']})")
            else:
                print("FAILED (empty)")
        return self._history_cache[cache_key]

    def _get_quote(self, symbol: str, days_for_year_high: int = 260) -> Optional[dict]:
        if symbol not in self._quote_cache:
            hist = self._get_history(symbol, days_for_year_high)
            q = fetch_quote(symbol, hist)
            if q:
                self._quote_cache[symbol] = q
        return self._quote_cache.get(symbol)

    # ── FMPClient interface ───────────────────────────────────────────────────

    def get_quote(self, symbols: str) -> Optional[list[dict]]:
        """Supports comma-separated symbols. Returns list of quote dicts."""
        sym_list = [s.strip() for s in symbols.split(",")]
        results = []
        for s in sym_list:
            q = self._get_quote(s)
            if q:
                results.append(q)
        return results if results else None

    def get_historical_prices(self, symbol: str, days: int = 260) -> Optional[dict]:
        """Returns {"symbol": ..., "historical": [newest-first]}."""
        hist = self._get_history(symbol, days)
        if not hist:
            return None
        return {"symbol": symbol, "historical": hist}

    def get_batch_quotes(self, symbols: list[str]) -> dict[str, dict]:
        """Returns {symbol: quote_dict}."""
        results = {}
        for s in symbols:
            q = self._get_quote(s, days_for_year_high=60)
            if q:
                results[s] = q
        return results

    def get_batch_historical(self, symbols: list[str], days: int = 50) -> dict[str, list[dict]]:
        """Returns {symbol: [history_list newest-first]}."""
        results = {}
        for s in symbols:
            hist = self._get_history(s, days)
            if hist:
                results[s] = hist
        return results

    def get_vix_term_structure(self) -> Optional[dict]:
        """Auto-detect using ^VIX and ^VIX3M quotes."""
        vix_q  = self._get_quote("^VIX",  days_for_year_high=30)
        vix3m_q = self._get_quote("^VIX3M", days_for_year_high=30)
        if not vix_q or not vix3m_q:
            return None
        vix_price  = vix_q["price"]
        vix3m_price = vix3m_q["price"]
        if vix3m_price <= 0:
            return None
        ratio = vix_price / vix3m_price
        if ratio < 0.85:
            classification = "steep_contango"
        elif ratio < 0.95:
            classification = "contango"
        elif ratio <= 1.05:
            classification = "flat"
        else:
            classification = "backwardation"
        return {
            "vix":            round(vix_price, 2),
            "vix3m":          round(vix3m_price, 2),
            "ratio":          round(ratio, 3),
            "classification": classification,
        }

    def get_api_stats(self) -> dict:
        return {
            "api_calls_made": self._fetch_count,
            "cache_entries":  len(self._history_cache) + len(self._quote_cache),
            "rate_limit_reached": False,
        }


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_arguments():
    p = argparse.ArgumentParser(description="Market Top Detector (yfinance adapter)")
    p.add_argument("--breadth-50dma",    type=float, default=None,
                   help="% S&P 500 above 50DMA (optional, scored if provided)")
    p.add_argument("--put-call",         type=float, default=None,
                   help="CBOE equity put/call ratio (optional, scored if provided)")
    p.add_argument("--vix-term",
                   choices=["steep_contango", "contango", "flat", "backwardation"],
                   default=None, help="VIX term structure override")
    p.add_argument("--margin-debt-yoy",  type=float, default=None,
                   help="Margin debt YoY change % (optional)")
    p.add_argument("--no-auto-breadth",  action="store_true",
                   help="Disable auto-fetch of 200DMA breadth from TraderMonty CSV")
    p.add_argument("--static-basket",   action="store_true",
                   help="Use static ETF basket instead of dynamic selection")
    p.add_argument("--output-dir",       default=".",
                   help="Output directory for reports")
    return p.parse_args()


# ── _load_previous_report (same as original) ─────────────────────────────────

import glob as _glob
import json as _json


def _load_previous_report(output_dir: str) -> Optional[dict]:
    pattern = os.path.join(output_dir, "market_top_*.json")
    files = sorted(_glob.glob(pattern))
    if not files:
        return None
    try:
        with open(files[-1]) as f:
            return _json.load(f)
    except (_json.JSONDecodeError, OSError):
        return None


def _compute_deltas(current_scores: dict, previous_report: Optional[dict]) -> dict:
    component_keys = [
        "distribution_days", "leading_stocks", "defensive_rotation",
        "breadth_divergence", "index_technical", "sentiment",
    ]
    deltas = {}
    if previous_report is None:
        for key in component_keys:
            deltas[key] = {"delta": 0, "direction": "first_run"}
        return {"components": deltas, "composite_delta": 0,
                "composite_direction": "first_run", "previous_date": None}

    prev_components = previous_report.get("components", {})
    prev_composite  = previous_report.get("composite", {}).get("composite_score", 0)

    for key in component_keys:
        prev_score = prev_components.get(key, {}).get("score", 0)
        curr_score = current_scores.get(key, 0)
        delta = curr_score - prev_score
        if abs(delta) <= 3:
            direction = "stable"
        elif delta > 0:
            direction = "worsening"
        else:
            direction = "improving"
        deltas[key] = {"delta": round(delta, 1), "direction": direction, "previous": prev_score}

    prev_date = previous_report.get("metadata", {}).get("generated_at", None)
    return {"components": deltas, "composite_delta": 0,
            "composite_direction": "first_run", "previous_date": prev_date,
            "previous_composite": prev_composite}


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    args = parse_arguments()
    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 70)
    print("Market Top Detector (yfinance adapter)")
    print("O'Neil (Distribution) + Minervini (Leadership) + Monty (Rotation)")
    print("=" * 70)
    print()

    client = YFinanceClient()

    # ── Step 1: Fetch shared data ─────────────────────────────────────────────
    print("Step 1: Fetching Market Data (yfinance)")
    print("-" * 70)

    print("  S&P 500 (^GSPC):")
    sp500_quote_list = client.get_quote("^GSPC")
    sp500_quote      = sp500_quote_list[0] if sp500_quote_list else None
    sp500_hist_data  = client.get_historical_prices("^GSPC", days=260)
    sp500_history    = sp500_hist_data.get("historical", []) if sp500_hist_data else []
    if not sp500_history:
        print("ERROR: Cannot proceed without S&P 500 data", file=sys.stderr)
        sys.exit(1)
    print(f"    OK ({len(sp500_history)} bars)")

    print("  NASDAQ (QQQ):")
    qqq_quote_list = client.get_quote("QQQ")
    qqq_quote      = qqq_quote_list[0] if qqq_quote_list else None
    qqq_hist_data  = client.get_historical_prices("QQQ", days=260)
    qqq_history    = qqq_hist_data.get("historical", []) if qqq_hist_data else []
    if not qqq_history:
        print("    WARN — QQQ unavailable, single-index mode")

    print("  VIX (^VIX):")
    vix_quote_list = client.get_quote("^VIX")
    vix_quote      = vix_quote_list[0] if vix_quote_list else None
    vix_level      = vix_quote["price"] if vix_quote else None
    if vix_level:
        print(f"    OK ({vix_level:.2f})")
    else:
        print("    WARN — VIX unavailable")

    # VIX term structure
    effective_vix_term = args.vix_term
    vix_term_auto = None
    if effective_vix_term is None:
        print("  VIX term structure (^VIX3M):")
        vix_term_auto = client.get_vix_term_structure()
        if vix_term_auto:
            effective_vix_term = vix_term_auto["classification"]
            print(f"    OK ({effective_vix_term}, ratio={vix_term_auto['ratio']})")
        else:
            print("    WARN — VIX3M unavailable, omitting term structure")

    # Leading ETFs
    if args.static_basket:
        selected_basket = list(LEADING_ETFS)
        print(f"  Leading ETFs (static basket, {len(selected_basket)} ETFs):")
        leading_quotes    = client.get_batch_quotes(selected_basket)
        leading_historical = client.get_batch_historical(selected_basket, days=60)
    else:
        print(f"  Candidate pool quotes ({len(CANDIDATE_POOL)} ETFs):")
        candidate_quotes = client.get_batch_quotes(CANDIDATE_POOL)
        selected_basket  = select_dynamic_basket(candidate_quotes)
        print(f"  Selected dynamic basket: {selected_basket}")
        print("  Leading ETF history:")
        leading_quotes    = {s: candidate_quotes[s] for s in selected_basket
                             if s in candidate_quotes}
        leading_historical = client.get_batch_historical(selected_basket, days=60)
    print(f"    OK ({len(leading_quotes)} quotes, {len(leading_historical)} histories)")

    # Sector ETFs
    all_sector_etfs     = list(set(DEFENSIVE_ETFS + OFFENSIVE_ETFS))
    sector_etfs_to_fetch = [e for e in all_sector_etfs if e != "QQQ"]
    print("  Sector ETFs:")
    sector_historical = client.get_batch_historical(sector_etfs_to_fetch, days=50)
    if qqq_history:
        sector_historical["QQQ"] = qqq_history[:50]
    print(f"    OK ({len(sector_historical)} ETFs)")
    print()

    # ── Step 2: Calculate Components ─────────────────────────────────────────
    print("Step 2: Calculating Components")
    print("-" * 70)

    # Component 1: Distribution Days (25%)
    print("  [1/6] Distribution Day Count...", end=" ", flush=True)
    comp1 = calculate_distribution_days(sp500_history, qqq_history)
    print(f"Score: {comp1['score']} ({comp1['signal']})")

    # Component 2: Leading Stock Health (20%)
    print("  [2/6] Leading Stock Health...", end=" ", flush=True)
    comp2 = calculate_leading_stock_health(
        leading_quotes, leading_historical, etf_list=selected_basket
    )
    print(f"Score: {comp2['score']} ({comp2['signal']})")

    # Component 3: Defensive Rotation (15%)
    print("  [3/6] Defensive Sector Rotation...", end=" ", flush=True)
    comp3 = calculate_defensive_rotation(sector_historical)
    print(f"Score: {comp3['score']} ({comp3['signal']})")

    # Auto-fetch 200DMA breadth
    effective_breadth_200dma = None
    breadth_source = "none"
    breadth_auto_date = None

    if not args.no_auto_breadth:
        print("  Fetching 200DMA breadth from TraderMonty CSV...", end=" ", flush=True)
        auto_result = fetch_breadth_200dma()
        if auto_result is not None:
            effective_breadth_200dma = auto_result["value"]
            breadth_source = "auto"
            breadth_auto_date = auto_result["date"]
            fresh_str = ("fresh" if auto_result["is_fresh"]
                         else f"STALE ({auto_result['days_old']}d old)")
            print(f"OK ({effective_breadth_200dma}%, {auto_result['date']}, {fresh_str})")
        else:
            print("FAILED (will use neutral default)")

    # Component 4: Breadth Divergence (15%)
    print("  [4/6] Market Breadth Divergence...", end=" ", flush=True)
    sp500_year_high = sp500_quote.get("yearHigh", 0) if sp500_quote else 0
    sp500_price     = sp500_quote.get("price", 0)    if sp500_quote else 0
    index_dist = ((sp500_price - sp500_year_high) / sp500_year_high * 100
                  if sp500_year_high > 0 else 0)

    comp4 = calculate_breadth_divergence(
        breadth_200dma=effective_breadth_200dma,
        breadth_50dma=args.breadth_50dma,
        index_distance_from_high_pct=index_dist,
    )
    comp4["breadth_source"] = breadth_source
    if breadth_auto_date:
        comp4["breadth_auto_date"] = breadth_auto_date
    print(f"Score: {comp4['score']} ({comp4['signal']})")

    # Component 5: Index Technical (15%)
    print("  [5/6] Index Technical Condition...", end=" ", flush=True)
    comp5 = calculate_index_technical(
        sp500_history, qqq_history,
        sp500_quote=sp500_quote, nasdaq_quote=qqq_quote
    )
    print(f"Score: {comp5['score']} ({comp5['signal']})")

    # Component 6: Sentiment (10%)
    print("  [6/6] Sentiment & Speculation...", end=" ", flush=True)
    comp6 = calculate_sentiment(
        vix_level=vix_level,
        put_call_ratio=args.put_call,
        vix_term_structure=effective_vix_term,
        margin_debt_yoy_pct=args.margin_debt_yoy,
    )
    print(f"Score: {comp6['score']} ({comp6['signal']})")
    print()

    # ── Step 3: Composite Score ───────────────────────────────────────────────
    print("Step 3: Calculating Composite Score")
    print("-" * 70)

    component_scores = {
        "distribution_days": comp1["score"],
        "leading_stocks":    comp2["score"],
        "defensive_rotation": comp3["score"],
        "breadth_divergence": comp4["score"],
        "index_technical":   comp5["score"],
        "sentiment":         comp6["score"],
    }
    data_availability = {
        "distribution_days": True,
        "leading_stocks":    comp2.get("data_available", True),
        "defensive_rotation": comp3.get("data_available", True),
        "breadth_divergence": comp4.get("data_available", True),
        "index_technical":   comp5.get("data_available", True),
        "sentiment":         comp6.get("data_available", True),
    }

    composite = calculate_composite_score(component_scores, data_availability)
    print(f"  Composite Score: {composite['composite_score']}/100")
    print(f"  Risk Zone:       {composite['zone']}")
    print(f"  Risk Budget:     {composite['risk_budget']}")
    print(f"  Strongest Warning: {composite['strongest_warning']['label']} "
          f"({composite['strongest_warning']['score']})")

    # Delta tracking
    previous_report = _load_previous_report(args.output_dir)
    delta_info = _compute_deltas(component_scores, previous_report)
    if previous_report is not None:
        prev_composite = delta_info.get("previous_composite", 0)
        comp_delta = composite["composite_score"] - prev_composite
        delta_info["composite_delta"] = round(comp_delta, 1)
        delta_info["composite_direction"] = (
            "stable" if abs(comp_delta) <= 3
            else ("worsening" if comp_delta > 0 else "improving")
        )
        print(f"  vs Previous: {prev_composite} → {composite['composite_score']} "
              f"({delta_info['composite_delta']:+.1f})")
    else:
        print("  (First run — no comparison available)")
    print()

    # ── Step 4: Follow-Through Day Check ─────────────────────────────────────
    ftd = detect_follow_through_day(sp500_history, composite["composite_score"])
    if ftd.get("applicable"):
        print("Step 4: Follow-Through Day Monitor")
        print("-" * 70)
        print(f"  {ftd['reason']}")
        print()

    # ── Step 5: Historical Comparison & Scenarios ─────────────────────────────
    print("Step 5: Historical Comparison & Scenarios")
    print("-" * 70)
    historical_comparison = compare_to_historical(component_scores)
    print(f"  Closest historical pattern: {historical_comparison['closest_match']}")
    scenarios = generate_scenarios(component_scores, data_availability)
    print(f"  Generated {len(scenarios)} what-if scenarios")
    print()

    # ── Step 6: Generate Reports ──────────────────────────────────────────────
    print("Step 6: Generating Reports")
    print("-" * 70)

    analysis = {
        "metadata": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_mode":    "yfinance (no FMP API required)",
            "api_calls":    client.get_api_stats(),
            "cli_inputs": {
                "breadth_200dma":        effective_breadth_200dma,
                "breadth_200dma_source": breadth_source,
                "breadth_200dma_auto_date": breadth_auto_date,
                "breadth_50dma":         args.breadth_50dma,
                "put_call_ratio":        args.put_call,
                "vix_term_structure":    args.vix_term,
                "margin_debt_yoy_pct":   args.margin_debt_yoy,
            },
            "vix_term_auto": vix_term_auto,
            "index_data": {
                "sp500_price":                sp500_price,
                "sp500_year_high":            sp500_year_high,
                "sp500_distance_from_high_pct": round(index_dist, 2),
                "qqq_price":  qqq_quote["price"] if qqq_quote else None,
                "vix_level":  vix_level,
            },
        },
        "composite": composite,
        "components": {
            "distribution_days": comp1,
            "leading_stocks":    comp2,
            "defensive_rotation": comp3,
            "breadth_divergence": comp4,
            "index_technical":   comp5,
            "sentiment":         comp6,
        },
        "follow_through_day":    ftd,
        "historical_comparison": historical_comparison,
        "scenarios":             scenarios,
        "delta":                 delta_info,
    }

    ts        = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    json_file = os.path.join(args.output_dir, f"market_top_{ts}.json")
    md_file   = os.path.join(args.output_dir, f"market_top_{ts}.md")

    generate_json_report(analysis, json_file)
    generate_markdown_report(analysis, md_file)

    print()
    print("=" * 70)
    print("Market Top Detection Complete")
    print("=" * 70)
    print(f"  Composite Score: {composite['composite_score']}/100")
    print(f"  Risk Zone:       {composite['zone']}")
    print(f"  Risk Budget:     {composite['risk_budget']}")
    print(f"  JSON:            {json_file}")
    print(f"  Markdown:        {md_file}")
    print()


if __name__ == "__main__":
    main()

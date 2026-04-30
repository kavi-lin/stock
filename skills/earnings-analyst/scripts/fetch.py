"""
earnings-analyst — FMP fetch orchestrator (V1.0)

Pulls a per-ticker earnings analysis bundle from FMP HTTP REST and writes
to skills/earnings-analyst/cache/<TICKER>_<LAST_EARNINGS_DATE>.json.

Cache key: (TICKER, last_earnings_date). The latest income-statement.date
defines last_earnings_date; if the cache already has a file matching that
key (and it's < 90 days old) we skip all other FMP calls.

Hard-coded paid blockers (gracefully skipped, NOT hard fail):
  - /stable/key-metrics?period=quarter      → 402 (use TTM + derive from raw)
  - /stable/analyst-estimates?period=quarter → 402 (use earnings-valuation-forecaster fallback)
  - earningsTranscript / ESG                 → 402 (sections marked unavailable in render)

Usage:
    python3 skills/earnings-analyst/scripts/fetch.py NVDA
    python3 skills/earnings-analyst/scripts/fetch.py NVDA --force  # skip cache
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CACHE_DIR = os.path.join(BASE_DIR, "skills", "earnings-analyst", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

FMP_BASE = "https://financialmodelingprep.com"
CACHE_TTL_DAYS = 90  # hard upper limit even if last_earnings_date hasn't moved


def _fmp_get(path: str, params: dict, *, retries: int = 2, timeout: int = 20):
    """GET with retry. Returns parsed JSON. Returns None on 402 paid (graceful)."""
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        sys.exit("[ERROR] FMP_API_KEY not set — earnings-analyst cannot run.")
    url = f"{FMP_BASE}{path}"
    full = {**params, "apikey": api_key}
    last_exc = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=full, timeout=timeout)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 402:
                return None  # paid blocker — graceful
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_exc = e
            time.sleep(0.5)
    print(f"[fetch] WARN: FMP {path} failed after {retries+1} tries: {last_exc}", file=sys.stderr)
    return None


def find_existing_cache(ticker: str, latest_earnings_date: str) -> str | None:
    """Return cache path if a file matches (TICKER, latest_earnings_date) AND age < TTL."""
    expected = os.path.join(CACHE_DIR, f"{ticker}_{latest_earnings_date}.json")
    if not os.path.exists(expected):
        return None
    age_days = (time.time() - os.path.getmtime(expected)) / 86400
    if age_days > CACHE_TTL_DAYS:
        print(f"[fetch] cache file age {age_days:.1f}d exceeds {CACHE_TTL_DAYS}d TTL — invalidating",
              file=sys.stderr)
        return None
    return expected


def slim_income(rows: list) -> list:
    keep = ["date", "fiscalYear", "period", "revenue", "grossProfit", "operatingIncome",
            "netIncome", "eps", "epsDiluted", "researchAndDevelopmentExpenses",
            "sellingGeneralAndAdministrativeExpenses", "ebitda", "ebit",
            "weightedAverageShsOutDil"]
    return [{k: r.get(k) for k in keep} for r in rows]


def slim_balance(rows: list) -> list:
    keep = ["date", "period", "totalAssets", "totalLiabilities", "totalEquity",
            "totalCurrentAssets", "totalCurrentLiabilities",
            "cashAndCashEquivalents", "shortTermInvestments",
            "totalDebt", "longTermDebt", "shortTermDebt",
            "netReceivables", "inventory", "retainedEarnings"]
    return [{k: r.get(k) for k in keep} for r in rows]


def slim_cashflow(rows: list) -> list:
    keep = ["date", "period", "operatingCashFlow", "freeCashFlow", "capitalExpenditure",
            "stockBasedCompensation", "commonStockRepurchased", "commonDividendsPaid",
            "netIncome"]
    return [{k: r.get(k) for k in keep} for r in rows]


def slim_ttm_keymetrics(d: dict) -> dict:
    keep = ["marketCap", "freeCashFlowYieldTTM", "evToEBITDATTM",
            "currentRatioTTM", "netDebtToEBITDATTM", "incomeQualityTTM",
            "capexToOperatingCashFlowTTM", "daysOfSalesOutstandingTTM",
            "freeCashFlowToFirmTTM"]
    return {k: d.get(k) for k in keep}


def slim_ttm_ratios(d: dict) -> dict:
    keep = ["grossProfitMarginTTM", "operatingProfitMarginTTM", "netProfitMarginTTM",
            "ebitMarginTTM", "priceToEarningsRatioTTM", "priceToBookRatioTTM",
            "debtToEquityRatioTTM", "interestCoverageRatioTTM",
            "priceToFreeCashFlowRatioTTM"]
    return {k: d.get(k) for k in keep}


def slim_growth(rows: list) -> list:
    keep = ["fiscalYear", "date", "period", "revenueGrowth", "grossProfitGrowth",
            "operatingIncomeGrowth", "netIncomeGrowth", "freeCashFlowGrowth",
            "fiveYRevenueGrowthPerShare", "fiveYNetIncomeGrowthPerShare",
            "threeYRevenueGrowthPerShare", "threeYNetIncomeGrowthPerShare"]
    return [{k: r.get(k) for k in keep} for r in rows]


def slim_grades(rows: list) -> list:
    """grades-historical = monthly snapshots of buy/hold/sell counts."""
    keep = ["date", "analystRatingsStrongBuy", "analystRatingsBuy", "analystRatingsHold",
            "analystRatingsSell", "analystRatingsStrongSell"]
    return [{k: r.get(k) for k in keep} for r in rows]


def fetch_bundle(ticker: str) -> dict:
    """Run all FMP calls for one ticker. Returns the raw bundle ready to write."""
    print(f"[fetch] {ticker}: profile / income / balance / cashflow ...", file=sys.stderr)

    profile_raw = _fmp_get("/stable/profile", {"symbol": ticker}) or [{}]
    income = _fmp_get("/stable/income-statement",
                      {"symbol": ticker, "period": "quarter", "limit": 8}) or []
    if not income:
        sys.exit(f"[ERROR] No quarterly income-statement returned for {ticker}")
    balance = _fmp_get("/stable/balance-sheet-statement",
                       {"symbol": ticker, "period": "quarter", "limit": 8}) or []
    cashflow = _fmp_get("/stable/cash-flow-statement",
                        {"symbol": ticker, "period": "quarter", "limit": 8}) or []

    print(f"[fetch] {ticker}: ttm metrics / ratios / growth / EV ...", file=sys.stderr)
    km_ttm_raw = _fmp_get("/stable/key-metrics-ttm", {"symbol": ticker}) or [{}]
    rat_ttm_raw = _fmp_get("/stable/ratios-ttm", {"symbol": ticker}) or [{}]
    growth = _fmp_get("/stable/financial-growth",
                      {"symbol": ticker, "period": "annual", "limit": 5}) or []
    ev_raw = _fmp_get("/stable/enterprise-values",
                      {"symbol": ticker, "period": "quarter", "limit": 1}) or [{}]

    print(f"[fetch] {ticker}: DCF / price-target / ratings / grades ...", file=sys.stderr)
    dcf = _fmp_get("/stable/discounted-cash-flow", {"symbol": ticker}) or [{}]
    pt = _fmp_get("/stable/price-target-consensus", {"symbol": ticker}) or [{}]
    ratings = _fmp_get("/stable/ratings-snapshot", {"symbol": ticker}) or [{}]
    grades = _fmp_get("/stable/grades-historical", {"symbol": ticker, "limit": 6}) or []

    profile = profile_raw[0] if profile_raw else {}
    last_earnings_date = income[0].get("date")
    next_earnings_est = None
    if last_earnings_date:
        try:
            d = datetime.strptime(last_earnings_date, "%Y-%m-%d").date()
            next_earnings_est = (d + timedelta(days=91)).isoformat()
        except ValueError:
            pass

    bundle = {
        "ticker":             ticker,
        "as_of_date":         date.today().isoformat(),
        "last_earnings_date": last_earnings_date,
        "next_earnings_est":  next_earnings_est,
        "schema_version":     "V1.0",
        "data_source":        "FMP HTTP REST",

        "snapshot": {
            "companyName":       profile.get("companyName"),
            "sector":            profile.get("sector"),
            "industry":          profile.get("industry"),
            "price":             profile.get("price"),
            "marketCap":         profile.get("marketCap"),
            "ipoDate":           profile.get("ipoDate"),
            "ceo":               profile.get("ceo"),
            "fullTimeEmployees": profile.get("fullTimeEmployees"),
            "exchange":          profile.get("exchangeFullName"),
        },
        "quarterly_pnl": slim_income(income),
        "balance_sheet": slim_balance(balance),
        "cash_flow":     slim_cashflow(cashflow),
        "ttm_metrics": {
            "from_key_metrics_ttm": slim_ttm_keymetrics(km_ttm_raw[0] if km_ttm_raw else {}),
            "from_ratios_ttm":      slim_ttm_ratios(rat_ttm_raw[0] if rat_ttm_raw else {}),
        },
        "annual_growth":     slim_growth(growth),
        "enterprise_value":  ev_raw[0] if ev_raw else {},
        "valuation": {
            "dcf_intrinsic":          (dcf[0] or {}).get("dcf"),
            "price_target_consensus": (pt[0] or {}).get("targetConsensus"),
            "price_target_high":      (pt[0] or {}).get("targetHigh"),
            "price_target_low":       (pt[0] or {}).get("targetLow"),
            "price_target_median":    (pt[0] or {}).get("targetMedian"),
            "ratings_snapshot":       ratings[0] if ratings else {},
        },
        "analyst_grades": slim_grades(grades),

        "paid_blockers_skipped": [
            "/stable/key-metrics?period=quarter (402)",
            "/stable/analyst-estimates?period=quarter (402)",
            "earningsTranscript (402)",
            "ESG (402)",
        ],
    }
    return bundle


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker", type=str.upper)
    ap.add_argument("--force", action="store_true", help="bypass cache, re-fetch")
    args = ap.parse_args()

    ticker = args.ticker

    # Step 0: lightweight call to discover last_earnings_date
    pre = _fmp_get("/stable/income-statement",
                   {"symbol": ticker, "period": "quarter", "limit": 1})
    if not pre:
        sys.exit(f"[ERROR] {ticker}: no income-statement available — invalid ticker?")
    latest_date = pre[0].get("date")
    if not latest_date:
        sys.exit(f"[ERROR] {ticker}: latest income-statement missing 'date'")

    # Step 1: cache check
    if not args.force:
        existing = find_existing_cache(ticker, latest_date)
        if existing:
            print(f"[fetch] cache hit: {os.path.relpath(existing, BASE_DIR)} "
                  f"(last_earnings_date={latest_date})", file=sys.stderr)
            return 0

    # Step 2: full fetch
    bundle = fetch_bundle(ticker)

    out_path = os.path.join(CACHE_DIR, f"{ticker}_{latest_date}.json")
    with open(out_path, "w") as f:
        json.dump(bundle, f, indent=2)
    print(f"[fetch] wrote {os.path.relpath(out_path, BASE_DIR)} "
          f"({len(json.dumps(bundle)):,} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

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

# Shared company-context cache (single source of truth for /stable/profile across skills)
sys.path.insert(0, BASE_DIR)
from skills._shared.company_context import get_profile as _shared_get_profile  # noqa: E402

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
    keep = ["marketCap", "freeCashFlowYieldTTM",
            "evToEBITDATTM", "evToFreeCashFlowTTM", "evToSalesTTM",
            "currentRatioTTM", "netDebtToEBITDATTM", "incomeQualityTTM",
            "capexToOperatingCashFlowTTM", "daysOfSalesOutstandingTTM",
            "freeCashFlowToFirmTTM",
            "returnOnInvestedCapitalTTM", "returnOnCapitalEmployedTTM",
            "returnOnTangibleAssetsTTM"]
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


# ── V1.73 infographic-layer slim helpers ──────────────────────────────────
def slim_earnings_surprises(rows: list) -> list:
    """/stable/earnings → surprise + estimated rows. Keep most-recent 8."""
    keep = ["date", "epsActual", "epsEstimated", "revenueActual",
            "revenueEstimated", "lastUpdated"]
    return [{k: r.get(k) for k in keep} for r in (rows or [])[:8]]


def slim_segment_product(rows: list) -> list:
    """/stable/revenue-product-segmentation → FY annual product split (5 yrs)."""
    return [
        {"date": r.get("date"),
         "fiscal_year": r.get("fiscalYear"),
         "period": r.get("period"),
         "products": r.get("data") or {}}
        for r in (rows or [])[:5]
    ]


def slim_segment_geographic(rows: list) -> list:
    """/stable/revenue-geographic-segmentation → FY annual region split (5 yrs)."""
    return [
        {"date": r.get("date"),
         "fiscal_year": r.get("fiscalYear"),
         "period": r.get("period"),
         "regions": r.get("data") or {}}
        for r in (rows or [])[:5]
    ]


def slim_dividends(rows: list) -> list:
    """/stable/dividends → DPS history. Keep latest 8 entries."""
    keep = ["date", "recordDate", "paymentDate", "declarationDate",
            "adjDividend", "dividend", "frequency", "yield"]
    return [{k: r.get(k) for k in keep} for r in (rows or [])[:8]]


# ── V1.74 analyst-depth helpers ──────────────────────────────────────────────
def slim_pt_news(rows: list) -> list:
    """/stable/price-target-news → who changed PT and by how much."""
    keep = ["date", "analystCompany", "priceTarget", "adjPriceTarget", "publishedDate"]
    return [{k: r.get(k) for k in keep} for r in (rows or [])[:8]]


def slim_rating_history(rows: list) -> list:
    """/stable/rating-historical → composite rating time series (12 months)."""
    keep = ["date", "rating", "ratingScore"]
    return [{k: r.get(k) for k in keep} for r in (rows or [])[:12]]


def compute_rating_trend(history: list) -> str:
    """improving | stable | declining — ratingScore 1=Strong Buy, 5=Strong Sell (lower=better)."""
    scored = [r.get("ratingScore") for r in (history or []) if r.get("ratingScore") is not None]
    if len(scored) < 4:
        return "insufficient_data"
    recent_avg = sum(scored[:3]) / 3
    older_avg  = sum(scored[-3:]) / 3
    diff = older_avg - recent_avg  # positive → rating improved (older was worse/higher number)
    if diff > 0.25:
        return "improving"
    if diff < -0.25:
        return "declining"
    return "stable"


def slim_grades_news(rows: list) -> list:
    """/stable/grades-news → event-level upgrade/downgrade records."""
    keep = ["date", "gradingCompany", "previousGrade", "newGrade", "action"]
    return [{k: r.get(k) for k in keep} for r in (rows or [])[:10]]


def _slim_grades_summary(d: dict) -> dict:
    """/stable/grades-summary → buy/hold/sell counts + strong_buy_pct."""
    keys = ["strongBuy", "buy", "hold", "sell", "strongSell"]
    out = {k: d.get(k, 0) for k in keys}
    total = sum(v for v in out.values() if v)
    out["strong_buy_pct"] = round(out.get("strongBuy", 0) / total * 100, 1) if total else None
    out["total_analysts"] = total
    return out


def _compute_pt_dispersion(pt_d: dict) -> float | None:
    """(pt_high - pt_low) / pt_consensus × 100 — analyst disagreement measure."""
    try:
        return round(
            (float(pt_d["targetHigh"]) - float(pt_d["targetLow"])) / float(pt_d["targetConsensus"]) * 100, 1
        )
    except (KeyError, TypeError, ZeroDivisionError, ValueError):
        return None


def _resolve_transcript_q(ticker: str, last_earnings_date: str,
                          fiscal_year: str | int | None,
                          period: str | None) -> dict | None:
    """Locate the right transcript via 4-tier try-multi.

    1. Trust quarterly_pnl[0] fiscalYear+period (FMP fiscal labels).
    2. Infer calendar Q from last_earnings_date.
    3. Walk back one quarter (Q-1, with year rollover) for each candidate.
    Returns {year, quarter, date, content, source_q_offset} or None.
    """
    candidates: list[tuple[int, int]] = []
    # Tier 1
    if fiscal_year is not None and period and isinstance(period, str) and period.startswith("Q"):
        try:
            candidates.append((int(fiscal_year), int(period[1])))
        except (ValueError, IndexError):
            pass
    # Tier 2
    try:
        y_cal = int(last_earnings_date[:4])
        m_cal = int(last_earnings_date[5:7])
        q_cal = (m_cal - 1) // 3 + 1
        if (y_cal, q_cal) not in candidates:
            candidates.append((y_cal, q_cal))
    except (ValueError, IndexError, TypeError):
        pass
    # Tier 3 — append Q-1 of each existing candidate
    for (y, q) in list(candidates):
        prev_q = q - 1 if q > 1 else 4
        prev_y = y if q > 1 else y - 1
        if (prev_y, prev_q) not in candidates:
            candidates.append((prev_y, prev_q))

    for offset, (y, q) in enumerate(candidates):
        result = _fmp_get("/stable/earning-call-transcript",
                          {"symbol": ticker, "year": y, "quarter": q})
        if result and isinstance(result, list) and result and result[0].get("content"):
            return {
                "year": y,
                "quarter": q,
                "date": result[0].get("date"),
                "content": result[0].get("content"),
                "source_q_offset": offset,
            }
    return None


def fetch_bundle(ticker: str) -> dict:
    """Run all FMP calls for one ticker. Returns the raw bundle ready to write."""
    print(f"[fetch] {ticker}: profile / income / balance / cashflow ...", file=sys.stderr)

    # profile via skills/_shared/company_context (24h cache, shared with sector + protocol PEER_BUNDLE)
    profile = _shared_get_profile(ticker) or {}
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
    dcf          = _fmp_get("/stable/discounted-cash-flow", {"symbol": ticker}) or [{}]
    dcf_levered  = _fmp_get("/stable/levered-discounted-cash-flow", {"symbol": ticker}) or [{}]
    pt           = _fmp_get("/stable/price-target-consensus", {"symbol": ticker}) or [{}]
    ratings      = _fmp_get("/stable/ratings-snapshot", {"symbol": ticker}) or [{}]
    grades       = _fmp_get("/stable/grades-historical", {"symbol": ticker, "limit": 6}) or []

    print(f"[fetch] {ticker}: pt-news / rating-history / grades-ext ...", file=sys.stderr)
    pt_news_raw      = _fmp_get("/stable/price-target-news",  {"symbol": ticker, "limit": 8}) or []
    rating_history   = _fmp_get("/stable/rating-historical",  {"symbol": ticker, "limit": 12}) or []
    grades_summary_r = _fmp_get("/stable/grades-summary",     {"symbol": ticker}) or [{}]
    grades_news_raw  = _fmp_get("/stable/grades-news",        {"symbol": ticker, "limit": 10}) or []

    print(f"[fetch] {ticker}: surprise / segments / dividends / transcript ...", file=sys.stderr)
    earn_surprises = _fmp_get("/stable/earnings", {"symbol": ticker, "limit": 8}) or []
    seg_product    = _fmp_get("/stable/revenue-product-segmentation", {"symbol": ticker}) or []
    seg_geographic = _fmp_get("/stable/revenue-geographic-segmentation", {"symbol": ticker}) or []
    dividends      = _fmp_get("/stable/dividends", {"symbol": ticker, "limit": 8}) or []
    # V1.87 — annual analyst estimates (forward EPS / revenue / EBITDA consensus)
    annual_estimates = _fmp_get("/stable/analyst-estimates",
                                {"symbol": ticker, "period": "annual", "limit": 3}) or []

    last_earnings_date = income[0].get("date")

    # Real next earnings date from FMP /stable/earnings (already fetched into earn_surprises above).
    # Scan for first future-dated row; fall back to +91d heuristic if FMP has nothing.
    next_earnings_est = None
    next_earnings_source = None
    next_earnings_eps_estimate = None
    next_earnings_revenue_estimate = None

    today_iso = date.today().isoformat()
    future_rows = sorted(
        [r for r in (earn_surprises or []) if r.get("date") and r["date"] > today_iso],
        key=lambda r: r["date"],
    )
    if future_rows:
        nxt = future_rows[0]
        next_earnings_est              = nxt.get("date")
        next_earnings_source           = "fmp_confirmed"
        next_earnings_eps_estimate     = nxt.get("epsEstimated")
        next_earnings_revenue_estimate = nxt.get("revenueEstimated")
    elif last_earnings_date:
        try:
            d = datetime.strptime(last_earnings_date, "%Y-%m-%d").date()
            next_earnings_est    = (d + timedelta(days=91)).isoformat()
            next_earnings_source = "estimated_91d"
        except ValueError:
            pass

    # Resolve transcript via fiscal-Q try-multi (uses cache fiscal labels first)
    transcript_obj = _resolve_transcript_q(
        ticker,
        last_earnings_date or "",
        income[0].get("fiscalYear"),
        income[0].get("period"),
    )
    if transcript_obj:
        print(f"[fetch] {ticker}: transcript Y{transcript_obj['year']}Q{transcript_obj['quarter']} "
              f"offset={transcript_obj['source_q_offset']} "
              f"({len(transcript_obj['content']):,} chars)", file=sys.stderr)
    else:
        print(f"[fetch] {ticker}: transcript NOT FOUND after 4-tier fallback", file=sys.stderr)

    bundle = {
        "ticker":             ticker,
        "as_of_date":         date.today().isoformat(),
        "last_earnings_date": last_earnings_date,
        "next_earnings_est":              next_earnings_est,
        "next_earnings_source":           next_earnings_source,            # "fmp_confirmed" | "estimated_91d" | None
        "next_earnings_eps_estimate":     next_earnings_eps_estimate,
        "next_earnings_revenue_estimate": next_earnings_revenue_estimate,
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
            "dcf_levered_intrinsic":  (dcf_levered[0] or {}).get("dcf"),
            "price_target_consensus": (pt[0] or {}).get("targetConsensus"),
            "price_target_high":      (pt[0] or {}).get("targetHigh"),
            "price_target_low":       (pt[0] or {}).get("targetLow"),
            "price_target_median":    (pt[0] or {}).get("targetMedian"),
            "pt_dispersion_pct":      _compute_pt_dispersion(pt[0] if pt else {}),
            "pt_news":                slim_pt_news(pt_news_raw),
            "ratings_snapshot":       ratings[0] if ratings else {},
        },
        "analyst_grades": slim_grades(grades),
        "analyst": {
            "rating_history": slim_rating_history(rating_history),
            "rating_trend":   compute_rating_trend(rating_history),
            "grades_summary": _slim_grades_summary(grades_summary_r[0] if grades_summary_r else {}),
            "grades_news":    slim_grades_news(grades_news_raw),
        },

        # V1.73 — infographic data layer (additive, all optional)
        "earnings_surprises": slim_earnings_surprises(earn_surprises),
        "segments": {
            "product_fy":    slim_segment_product(seg_product),
            "geographic_fy": slim_segment_geographic(seg_geographic),
        },
        "dividends_history": slim_dividends(dividends),
        "transcript":        transcript_obj,
        "annual_estimates":  [{
            "date":             e.get("date"),
            "revenue_avg":      e.get("revenueAvg"),
            "revenue_low":      e.get("revenueLow"),
            "revenue_high":     e.get("revenueHigh"),
            "ebitda_avg":       e.get("ebitdaAvg"),
            "net_income_avg":   e.get("netIncomeAvg"),
            "eps_avg":          e.get("epsAvg"),
            "eps_low":          e.get("epsLow"),
            "eps_high":         e.get("epsHigh"),
            "num_analysts_revenue": e.get("numAnalystsRevenue"),
            "num_analysts_eps": e.get("numAnalystsEps"),
        } for e in annual_estimates] if annual_estimates else [],

        "paid_blockers_skipped": [
            "/stable/key-metrics?period=quarter (402)",
            "/stable/analyst-estimates?period=quarter (402; annual works → see annual_estimates)",
            "/stable/revenue-product-segmentation?period=quarter (402)",
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

    # Preserve analyzed fields written by analyze.py if cache file already exists.
    # Without this merge, --force re-fetch would clobber composite_score / verdict
    # / score_components / derived / quality_flags, leaving the cache in a
    # half-analyzed state (bridge.py:extract_earnings_analyses skips it).
    PRESERVE_KEYS = ("composite_score", "verdict", "score_components",
                     "derived", "quality_flags")
    if os.path.exists(out_path):
        try:
            with open(out_path, "r") as f:
                prev = json.load(f)
            preserved = {k: prev[k] for k in PRESERVE_KEYS if k in prev}
            if preserved:
                bundle.update(preserved)
                print(f"[fetch] merged {len(preserved)} analyzed field(s) from prior cache: "
                      f"{list(preserved.keys())}", file=sys.stderr)
        except Exception as e:
            print(f"[fetch] WARN: could not read prior cache for merge: {e}", file=sys.stderr)

    with open(out_path, "w") as f:
        json.dump(bundle, f, indent=2)
    print(f"[fetch] wrote {os.path.relpath(out_path, BASE_DIR)} "
          f"({len(json.dumps(bundle)):,} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

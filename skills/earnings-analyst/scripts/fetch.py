"""
earnings-analyst — FMP fetch orchestrator (V1.0)

Pulls a per-ticker earnings analysis bundle from FMP HTTP REST and writes
to skills/earnings-analyst/cache/<TICKER>_<LAST_EARNINGS_DATE>.json.

Cache key: (TICKER, last_earnings_date). The latest income-statement.date
defines last_earnings_date. Endpoint caches retain source clocks: financial
7 days, market 24 hours, quote 5 minutes. Every run confirms the latest quarter.

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
from earnings_history import earnings_context

from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CACHE_DIR = os.path.join(BASE_DIR, "skills", "earnings-analyst", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Shared company-context cache (single source of truth for /stable/profile across skills)
sys.path.insert(0, BASE_DIR)
from skills._shared.company_context import get_profile as _shared_get_profile  # noqa: E402

from skills._shared.investment_data import SourceCache
from investment.scripts.run_data import atomic_json, fresh, utcnow

CACHE_TTL_DAYS = 7
_SOURCE_CACHE = None


def _cache():
    global _SOURCE_CACHE
    if _SOURCE_CACHE is None:
        _SOURCE_CACHE = SourceCache(os.path.join(CACHE_DIR, "sources"))
    return _SOURCE_CACHE


def _fmp_get(path: str, params: dict, *, retries: int = 1, timeout: int = 20):
    return _cache().get(path, params, retries=retries, timeout=timeout)


def find_existing_cache(ticker: str, latest_earnings_date: str) -> str | None:
    """Only source timestamps count; analyze.py rewriting the file renews nothing."""
    expected = os.path.join(CACHE_DIR, f"{ticker}_{latest_earnings_date}.json")
    try:
        with open(expected) as f:
            bundle = json.load(f)
        sources = bundle.get("source_records") or {}
        if sources and all(fresh(r, period=latest_earnings_date) for r in sources.values()):
            return expected
    except (OSError, ValueError):
        pass
    return None


def slim_income(rows: list) -> list:
    # V3.17 — costOfRevenue added for DPO computation (DPO = AP / COGS × 91).
    keep = ["date", "fiscalYear", "period", "revenue", "costOfRevenue", "grossProfit",
            "operatingIncome", "netIncome", "eps", "epsDiluted",
            "researchAndDevelopmentExpenses",
            "sellingGeneralAndAdministrativeExpenses", "ebitda", "ebit",
            "weightedAverageShsOutDil", "reportedCurrency", "acceptedDate", "filingDate", "finalLink", "link"]
    return [{k: r.get(k) for k in keep} for r in rows]


def slim_balance(rows: list) -> list:
    # V3.17 — accountsPayable + otherCurrentLiabilities added for DPO computation.
    # FMP often omits accountsPayable for European ADRs (合併揭露 in otherCurrentLiabilities).
    # Downstream analyze.py uses a 3-tier DPO fallback (direct / estimated / unavailable).
    keep = ["date", "period", "totalAssets", "totalLiabilities", "totalEquity",
            "totalCurrentAssets", "totalCurrentLiabilities",
            "cashAndCashEquivalents", "shortTermInvestments",
            "totalDebt", "longTermDebt", "shortTermDebt",
            "netReceivables", "inventory", "retainedEarnings",
            "accountsPayable", "otherCurrentLiabilities", "reportedCurrency", "finalLink", "link"]
    return [{k: r.get(k) for k in keep} for r in rows]


def slim_cashflow(rows: list) -> list:
    keep = ["date", "period", "operatingCashFlow", "freeCashFlow", "capitalExpenditure",
            "stockBasedCompensation", "commonStockRepurchased", "commonDividendsPaid",
            "netIncome", "reportedCurrency", "finalLink", "link"]
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
    """Daily FMP financial ratings; ratingScore retains the local schema name."""
    return [{"date": r.get("date"), "rating": r.get("rating"),
             "ratingScore": r.get("overallScore")}
            for r in (rows or [])[:12]]


def compute_rating_trend(history: list) -> str:
    """Trend in FMP's financial overallScore (higher=better), not broker grades."""
    scored = [r["overallScore"] for r in (history or [])
              if isinstance(r.get("overallScore"), (int, float))
              and not isinstance(r["overallScore"], bool) and 1 <= r["overallScore"] <= 5]
    if len(scored) < 4:
        return "insufficient_data"
    recent_avg = sum(scored[:3]) / 3
    older_avg  = sum(scored[-3:]) / 3
    diff = recent_avg - older_avg
    if diff > 0.25:
        return "improving"
    if diff < -0.25:
        return "declining"
    return "stable"


def slim_grades_news(rows: list) -> list:
    """/stable/grades-news → event-level upgrade/downgrade records."""
    keep = ["gradingCompany", "previousGrade", "newGrade", "action"]
    return [{**{k: r.get(k) for k in keep},
             "date": (r.get("publishedDate") or r.get("date") or "")[:10] or None}
            for r in (rows or [])[:10]]


def _slim_grades_summary(d: dict) -> dict:
    """/stable/grades-consensus → buy/hold/sell counts + strong_buy_pct."""
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


def fetch_bundle(ticker: str, income: list | None = None) -> dict:
    """Run all FMP calls for one ticker (parallel batch). Returns the raw bundle ready to write.
    `income` lets main() pass its pre-fetched quarterly income-statement to avoid a duplicate call."""
    # profile via skills/_shared/company_context (24h cache, shared with sector + protocol PEER_BUNDLE)
    profile_rows = _fmp_get("/stable/profile", {"symbol": ticker}) or []
    profile = profile_rows[0] if profile_rows else {}
    quote_rows = _fmp_get("/stable/quote", {"symbol": ticker}) or []
    quote = quote_rows[0] if quote_rows else {}

    calls = {
        "income":           ("/stable/income-statement",        {"symbol": ticker, "period": "quarter", "limit": 8}),
        "balance":          ("/stable/balance-sheet-statement", {"symbol": ticker, "period": "quarter", "limit": 8}),
        "cashflow":         ("/stable/cash-flow-statement",     {"symbol": ticker, "period": "quarter", "limit": 8}),
        "km_ttm":           ("/stable/key-metrics-ttm",         {"symbol": ticker}),
        "rat_ttm":          ("/stable/ratios-ttm",              {"symbol": ticker}),
        "growth":           ("/stable/financial-growth",        {"symbol": ticker, "period": "annual", "limit": 5}),
        "ev":               ("/stable/enterprise-values",       {"symbol": ticker, "period": "quarter", "limit": 1}),
        "dcf":              ("/stable/discounted-cash-flow",    {"symbol": ticker}),
        "dcf_levered":      ("/stable/levered-discounted-cash-flow", {"symbol": ticker}),
        "pt":               ("/stable/price-target-consensus",  {"symbol": ticker}),
        "ratings":          ("/stable/ratings-snapshot",        {"symbol": ticker}),
        "grades":           ("/stable/grades-historical",       {"symbol": ticker, "limit": 6}),
        "pt_news":          ("/stable/price-target-news",       {"symbol": ticker, "limit": 8}),
        "rating_history":   ("/stable/ratings-historical",      {"symbol": ticker, "limit": 12}),
        "grades_summary":   ("/stable/grades-consensus",         {"symbol": ticker}),
        "grades_news":      ("/stable/grades-news",             {"symbol": ticker, "limit": 10}),
        "earn_surprises":   ("/stable/earnings",                {"symbol": ticker, "limit": 8}),
        "seg_product":      ("/stable/revenue-product-segmentation",    {"symbol": ticker}),
        "seg_geographic":   ("/stable/revenue-geographic-segmentation", {"symbol": ticker}),
        "dividends":        ("/stable/dividends",               {"symbol": ticker, "limit": 8}),
        # V1.87 — annual analyst estimates (forward EPS / revenue / EBITDA consensus)
        # V4.40.0 — limit 3→6: FMP sorts annual estimates DESCENDING (farthest-first),
        # so limit=3 silently dropped the well-covered near years (FY+1/FY+2) and kept
        # only the thin-coverage far tail. 6 reaches the near years for the trajectory.
        "annual_estimates": ("/stable/analyst-estimates",       {"symbol": ticker, "period": "annual", "limit": 6}),
    }
    if income:
        del calls["income"]
    print(f"[fetch] {ticker}: {len(calls)} FMP calls (parallel ×8) ...", file=sys.stderr)
    results = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(_fmp_get, path, params): key for key, (path, params) in calls.items()}
        for fut in as_completed(futs):
            results[futs[fut]] = fut.result()
    if income:
        results["income"] = income

    income = results.get("income") or []
    if not income:
        sys.exit(f"[ERROR] No quarterly income-statement returned for {ticker}")
    balance          = results.get("balance") or []
    cashflow         = results.get("cashflow") or []
    km_ttm_raw       = results.get("km_ttm") or [{}]
    rat_ttm_raw      = results.get("rat_ttm") or [{}]
    growth           = results.get("growth") or []
    ev_raw           = results.get("ev") or [{}]
    dcf              = results.get("dcf") or [{}]
    dcf_levered      = results.get("dcf_levered") or [{}]
    pt               = results.get("pt") or [{}]
    ratings          = results.get("ratings") or [{}]
    grades           = results.get("grades") or []
    pt_news_raw      = results.get("pt_news") or []
    rating_history   = results.get("rating_history") or []
    grades_summary_r = results.get("grades_summary") or [{}]
    grades_news_raw  = results.get("grades_news") or []
    earn_surprises   = results.get("earn_surprises") or []
    seg_product      = results.get("seg_product") or []
    seg_geographic   = results.get("seg_geographic") or []
    dividends        = results.get("dividends") or []
    annual_estimates = results.get("annual_estimates") or []

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
            "price":             quote.get("price"),
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
    bundle["source_records"] = dict(_cache().sources)
    bundle["source_telemetry"] = dict(_cache().metrics)
    bundle["assembled_at"] = utcnow()
    bundle["earnings_context"] = earnings_context(bundle)
    return bundle


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker", type=str.upper)
    ap.add_argument("--force", action="store_true", help="bypass cache, re-fetch")
    args = ap.parse_args()

    ticker = args.ticker

    global _SOURCE_CACHE
    _SOURCE_CACHE = SourceCache(os.path.join(CACHE_DIR, "sources"), force=args.force)
    pre = _cache().get("/stable/income-statement",
                       {"symbol": ticker, "period": "quarter", "limit": 8}, refresh=True)
    if not pre or not pre[0].get("date"):
        sys.exit(f"[ERROR] {ticker}: latest financial period unavailable")
    latest_date = pre[0]["date"]
    _cache().period = latest_date
    # The discovery request itself belongs to the newly confirmed period.
    for record in _cache().sources.values():
        record["financial_period"] = latest_date
    prior_path = os.path.join(CACHE_DIR, f"{ticker}_{latest_date}.json")
    if not args.force and os.path.exists(prior_path):
        print(f"[fetch] cache hit: financial period unchanged; reassemble market sources", file=sys.stderr)

    # Step 2: full fetch (reuses pre-fetched income)
    bundle = fetch_bundle(ticker, income=pre)

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

    atomic_json(out_path, bundle)
    print(f"[fetch] wrote {os.path.relpath(out_path, BASE_DIR)} "
          f"({len(json.dumps(bundle)):,} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

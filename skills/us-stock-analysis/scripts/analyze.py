#!/usr/bin/env python3
"""
us-stock-analysis — fundamentals snapshot for a single US ticker.

Produces the JSON consumed by investment_protocol_v4_8 Phase 2 Fundamentals
subagent. Six rubric fields: P/E vs sector, revenue YoY, FCF margin,
debt-to-equity, next earnings date, analyst consensus EPS growth.

Primary source is yfinance (no API key). FMP is consulted only for
sector-median P/E when an `FMP_API_KEY` is set and quota is available;
on 429 we short-circuit and leave that field null.

Usage:
    python3 analyze.py NVDA
    python3 analyze.py NVDA --json-only
    python3 analyze.py NVDA --no-fmp     # skip FMP probe entirely
"""
import argparse
import json
import os
import sys
from datetime import datetime, date, timezone

import yfinance as yf

try:
    import requests
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False


FMP_BASE = "https://financialmodelingprep.com"


# ── EARNINGS_ANALYST_BUNDLE bundle-first reader (v1.84) ────────────────────
def _bundle_path_for(ticker: str):
    """Locate latest earnings-analyst cache for ticker, if any.
    Format: skills/earnings-analyst/cache/<TICKER>_<DATE>.json
    """
    import glob
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    pat = os.path.join(repo_root, "skills", "earnings-analyst", "cache",
                       f"{ticker.upper()}_*.json")
    candidates = sorted([p for p in glob.glob(pat) if "infographic" not in p])
    return candidates[-1] if candidates else None


def _load_bundle(ticker: str):
    """Read and return latest earnings-analyst bundle, or None."""
    p = _bundle_path_for(ticker)
    if not p:
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return None


def _derive_from_bundle(bundle: dict) -> dict:
    """Map EARNINGS_ANALYST_BUNDLE fields onto the same shape that analyze()
    fills via yfinance. Used when bundle is fresh — avoids redundant yfinance
    network call for fields that earnings-analyst already cached.

    Returns a dict of {block_name: {field: value}} that can be merged into the
    normal analyze() output.
    """
    if not bundle:
        return {}
    q0 = (bundle.get("quarterly_pnl") or [{}])[0] if bundle.get("quarterly_pnl") else {}
    cf0 = (bundle.get("cash_flow") or [{}])[0] if bundle.get("cash_flow") else {}
    bs0 = (bundle.get("balance_sheet") or [{}])[0] if bundle.get("balance_sheet") else {}
    ttm = bundle.get("ttm_metrics", {}) or {}
    km  = ttm.get("from_key_metrics_ttm", {}) or {}
    rat = ttm.get("from_ratios_ttm", {}) or {}
    ev  = bundle.get("enterprise_value", {}) or {}
    # next_earnings_est is a string like "2026-06-27" in current schema
    nx_raw = bundle.get("next_earnings_est")
    nx_date = nx_raw if isinstance(nx_raw, str) else (nx_raw or {}).get("date")

    ev_to_ebitda = km.get("evToEBITDATTM") or rat.get("enterpriseValueMultipleTTM")
    pe          = rat.get("priceToEarningsRatioTTM")
    pb          = rat.get("priceToBookRatioTTM")
    dt_eq       = rat.get("debtToEquityRatioTTM")
    net_margin  = rat.get("netProfitMarginTTM")
    op_margin   = rat.get("operatingProfitMarginTTM")
    gross_margin = rat.get("grossProfitMarginTTM")
    fcf_yield_decimal = km.get("freeCashFlowYieldTTM")

    derived: dict = {
        "valuation": {
            "pe_ratio":  pe,
            "pb_ratio":  pb,
            "ev_ebitda": ev_to_ebitda,
        },
        "balance_sheet": {
            "debt_to_equity": dt_eq,
        },
        "margins_cash": {
            "gross_margin_pct":     round(gross_margin * 100, 2) if gross_margin else None,
            "operating_margin_pct": round(op_margin * 100, 2) if op_margin else None,
            "net_margin_pct":       round(net_margin * 100, 2) if net_margin else None,
            "fcf_yield_pct":        round(fcf_yield_decimal * 100, 2)
                                    if fcf_yield_decimal else None,
        },
        "earnings_calendar": {
            "next_earnings_date": nx_date,
        },
        "_bundle_meta": {
            "source": "EARNINGS_ANALYST_BUNDLE",
            "as_of": bundle.get("as_of_date") or bundle.get("last_earnings_date"),
            "ticker": bundle.get("ticker"),
        },
    }
    return derived


# ── FMP supplement (optional) ───────────────────────────────────────────
def _fmp_sector_pe(sector: str, api_key: str):
    """Return sector-median trailing P/E via FMP `/stable/sector-pe-snapshot`.
    Short-circuits on 429 so a blown quota doesn't stall the analyst.
    Returns None on any failure (subagent can web-search if it cares)."""
    if not sector or not HAS_REQUESTS or not api_key:
        return None
    try:
        url = f"{FMP_BASE}/stable/sector-pe-snapshot"
        r = requests.get(url, params={"apikey": api_key, "sector": sector}, timeout=8)
        if r.status_code == 429:
            return None   # short-circuit — caller should treat as missing
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, list) and data:
            pe = data[0].get("pe")
            return round(float(pe), 2) if pe is not None else None
    except Exception:
        pass
    return None


# ── yfinance extractors ─────────────────────────────────────────────────
def _safe_float(v):
    try:
        x = float(v)
        return x if x == x else None  # NaN check
    except (TypeError, ValueError):
        return None


def _price_block(tk, info: dict):
    return {
        "current":    _safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
        "market_cap": _safe_float(info.get("marketCap")),
        "52w_high":   _safe_float(info.get("fiftyTwoWeekHigh")),
        "52w_low":    _safe_float(info.get("fiftyTwoWeekLow")),
    }


def _valuation_block(info: dict, sector_pe):
    return {
        "pe_ratio":         _safe_float(info.get("trailingPE")),
        "pe_forward":       _safe_float(info.get("forwardPE")),
        "pe_sector_median": sector_pe,   # None if FMP unavailable
        "peg_ratio":        _safe_float(info.get("pegRatio")),
        "ev_ebitda":        _safe_float(info.get("enterpriseToEbitda")),
    }


def _growth_block(tk, info: dict):
    """Revenue YoY from income_stmt (more reliable than info.revenueGrowth for
    fiscal-year boundaries). Trailing-3y CAGR if enough history. Forward EPS
    growth from info.earningsGrowth (analyst consensus proxy)."""
    rev_yoy = _safe_float(info.get("revenueGrowth"))
    if rev_yoy is not None:
        rev_yoy *= 100   # info stores decimal (0.157 = 15.7%)

    rev_cagr_3y = None
    try:
        # income_stmt: columns = fiscal year dates, newest first
        inc = tk.income_stmt
        if inc is not None and not inc.empty and "Total Revenue" in inc.index:
            row = inc.loc["Total Revenue"].dropna()
            if len(row) >= 4:
                latest, three_ago = float(row.iloc[0]), float(row.iloc[3])
                if three_ago > 0:
                    rev_cagr_3y = ((latest / three_ago) ** (1 / 3) - 1) * 100
    except Exception:
        pass

    # earningsGrowth is YoY quarterly EPS — close enough proxy for consensus
    # forward growth. True analyst consensus EPS-growth-next-year needs FMP
    # analyst-estimates, which we treat as nice-to-have.
    eps_growth = _safe_float(info.get("earningsGrowth"))
    if eps_growth is not None:
        eps_growth *= 100

    return {
        "revenue_yoy_pct":          round(rev_yoy, 2) if rev_yoy is not None else None,
        "revenue_trailing_3y_cagr_pct": round(rev_cagr_3y, 2) if rev_cagr_3y is not None else None,
        "eps_growth_forward_consensus_pct": round(eps_growth, 2) if eps_growth is not None else None,
    }


def _margins_cash_block(info: dict):
    """yfinance quirk: freeCashflow sometimes wrong when OpCF is positive
    (e.g. KO reports -1.46B FCF despite +7.4B OpCF). Fall back to OpCF × 0.85
    which approximates a mature-company free cash flow."""
    fcf = _safe_float(info.get("freeCashflow"))
    op_cf = _safe_float(info.get("operatingCashflow"))
    if (fcf is None or fcf <= 0) and op_cf and op_cf > 0:
        fcf = op_cf * 0.85

    revenue = _safe_float(info.get("totalRevenue"))
    ev = _safe_float(info.get("enterpriseValue"))

    fcf_margin_pct = (fcf / revenue * 100) if (fcf and revenue and revenue > 0) else None
    fcf_yield_pct  = (fcf / ev      * 100) if (fcf and ev      and ev      > 0) else None

    return {
        "gross_margin_pct":     round(_safe_float(info.get("grossMargins")) * 100, 2) if info.get("grossMargins") else None,
        "operating_margin_pct": round(_safe_float(info.get("operatingMargins")) * 100, 2) if info.get("operatingMargins") else None,
        "fcf_margin_pct":       round(fcf_margin_pct, 2) if fcf_margin_pct is not None else None,
        "fcf_yield_pct":        round(fcf_yield_pct, 2)  if fcf_yield_pct  is not None else None,
    }


def _balance_sheet_block(info: dict):
    # yfinance debtToEquity is a PERCENT (102.6 means 102.6%). Normalize to ratio.
    de = _safe_float(info.get("debtToEquity"))
    if de is not None:
        de = round(de / 100, 3)

    cash = _safe_float(info.get("totalCash"))
    debt = _safe_float(info.get("totalDebt"))
    net_cash_positive = (cash is not None and debt is not None and cash > debt)

    return {
        "debt_to_equity":        de,
        "net_cash_positive":     net_cash_positive,
        "cash_and_equivalents":  int(cash) if cash else None,
        "total_debt":            int(debt) if debt else None,
    }


def _earnings_calendar_block(tk):
    try:
        cal = tk.calendar
    except Exception:
        return {"next_earnings_date": None, "days_until_earnings": None}

    if not cal:
        return {"next_earnings_date": None, "days_until_earnings": None}

    # `cal` is a dict in newer yfinance; 'Earnings Date' is a list of date objects
    earnings_dates = cal.get("Earnings Date") if isinstance(cal, dict) else None
    if not earnings_dates:
        return {"next_earnings_date": None, "days_until_earnings": None}

    # Pick the soonest future date
    today = date.today()
    future = [d for d in earnings_dates if isinstance(d, date) and d >= today]
    target = (future[0] if future else earnings_dates[0]) if earnings_dates else None
    if not isinstance(target, date):
        return {"next_earnings_date": None, "days_until_earnings": None}

    return {
        "next_earnings_date":  target.isoformat(),
        "days_until_earnings": (target - today).days,
    }


def _analyst_block(info: dict):
    rating  = info.get("recommendationKey")   # buy / hold / sell / strong_buy ...
    count   = info.get("numberOfAnalystOpinions")
    target  = _safe_float(info.get("targetMeanPrice"))
    current = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))

    upside = None
    if target and current and current > 0:
        upside = round((target / current - 1) * 100, 2)

    return {
        "consensus_rating":        rating.upper() if isinstance(rating, str) else None,
        "analyst_count":           int(count) if count else None,
        "price_target_mean":       round(target, 2) if target else None,
        "price_target_upside_pct": upside,
    }


# ── Warning flags ───────────────────────────────────────────────────────
def _warnings(margins: dict, valuation: dict, balance: dict, growth: dict):
    w = []
    if margins.get("fcf_margin_pct") is not None and margins["fcf_margin_pct"] < 0:
        w.append("negative_fcf_ttm")
    if valuation.get("pe_ratio") is not None and valuation["pe_ratio"] > 80:
        w.append("extreme_pe_above_80")
    if balance.get("debt_to_equity") is not None and balance["debt_to_equity"] > 3:
        w.append("very_high_leverage")
    if growth.get("revenue_yoy_pct") is not None and growth["revenue_yoy_pct"] < -10:
        w.append("revenue_contracting")
    return w


# ── Main ────────────────────────────────────────────────────────────────
def analyze(ticker: str, use_fmp: bool = True, use_bundle: bool = True):
    ticker = ticker.upper()
    bundle = _load_bundle(ticker) if use_bundle else None

    tk = yf.Ticker(ticker)
    info = tk.info or {}

    missing = []
    fmp_calls, fmp_failures = 0, 0
    sector_pe = None
    api_key = os.getenv("FMP_API_KEY")
    if use_fmp and api_key:
        sector = info.get("sector")
        if sector:
            fmp_calls = 1
            sector_pe = _fmp_sector_pe(sector, api_key)
            if sector_pe is None:
                fmp_failures = 1

    if sector_pe is None:
        missing.append("pe_sector_median")

    price     = _price_block(tk, info)
    valuation = _valuation_block(info, sector_pe)
    growth    = _growth_block(tk, info)
    margins   = _margins_cash_block(info)
    balance   = _balance_sheet_block(info)
    earnings  = _earnings_calendar_block(tk)
    analyst   = _analyst_block(info)

    # Bundle-first override: prefer EARNINGS_ANALYST_BUNDLE values where present,
    # since those are FMP-sourced canonical TTM metrics. yfinance still provides
    # fields the bundle doesn't carry (price block, growth/EPS forward, analyst).
    bundle_overrides = _derive_from_bundle(bundle) if bundle else {}
    if bundle_overrides:
        for block_name, block_data in bundle_overrides.items():
            if block_name.startswith("_"):
                continue
            target = locals().get(block_name)
            if isinstance(target, dict):
                for k, v in block_data.items():
                    if v is not None:
                        target[k] = v

    if growth.get("eps_growth_forward_consensus_pct") is None:
        missing.append("eps_growth_forward_consensus_pct")

    return {
        "ticker": ticker,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": "bundle+yfinance" if bundle else (
            "mixed" if (fmp_calls > 0 and fmp_failures == 0) else "yfinance"
        ),
        "price":              price,
        "valuation":          valuation,
        "growth":             growth,
        "margins_cash":       margins,
        "balance_sheet":      balance,
        "earnings_calendar":  earnings,
        "analyst":            analyst,
        "warnings":           _warnings(margins, valuation, balance, growth),
        "data_quality": {
            "fmp_calls":       fmp_calls,
            "fmp_failures":    fmp_failures,
            "yf_fallbacks":    1,
            "bundle_used":     bool(bundle),
            "bundle_meta":     bundle_overrides.get("_bundle_meta"),
            "missing_fields":  missing,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--json-only", action="store_true",
                    help="Output JSON only; no human summary")
    ap.add_argument("--no-fmp", action="store_true",
                    help="Skip FMP probe entirely (sector-median P/E will be null)")
    ap.add_argument("--no-bundle", action="store_true",
                    help="Skip EARNINGS_ANALYST_BUNDLE consult (force yfinance for all fields)")
    args = ap.parse_args()

    try:
        payload = analyze(args.ticker,
                          use_fmp=not args.no_fmp,
                          use_bundle=not args.no_bundle)
    except Exception as e:
        err = {"ticker": args.ticker.upper(), "error": f"{type(e).__name__}: {e}"}
        print(json.dumps(err, indent=2), file=sys.stdout)
        sys.exit(1)

    print(json.dumps(payload, indent=2, default=str))

    if args.json_only:
        return

    # Human summary (only when --json-only not passed)
    v, g, m = payload["valuation"], payload["growth"], payload["margins_cash"]
    b, e_cal, a = payload["balance_sheet"], payload["earnings_calendar"], payload["analyst"]
    print(f"\n=== {payload['ticker']} fundamentals summary ===", file=sys.stderr)
    print(f"  P/E: {v.get('pe_ratio')} (sector med: {v.get('pe_sector_median') or 'n/a'})", file=sys.stderr)
    print(f"  Rev YoY: {g.get('revenue_yoy_pct')}%   FCF margin: {m.get('fcf_margin_pct')}%   FCF yield: {m.get('fcf_yield_pct')}%", file=sys.stderr)
    print(f"  D/E: {b.get('debt_to_equity')}   Net cash: {b.get('net_cash_positive')}", file=sys.stderr)
    print(f"  Next earnings: {e_cal.get('next_earnings_date')} ({e_cal.get('days_until_earnings')}d)", file=sys.stderr)
    print(f"  Analyst: {a.get('consensus_rating')} ({a.get('analyst_count')} analysts, target ${a.get('price_target_mean')})", file=sys.stderr)
    if payload["warnings"]:
        print(f"  ⚠ {', '.join(payload['warnings'])}", file=sys.stderr)


if __name__ == "__main__":
    main()

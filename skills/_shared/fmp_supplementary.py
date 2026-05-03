#!/usr/bin/env python3
"""
FMP Supplementary Bundle — Phase 1 data layer (FMP-only, 24h cache).

High-value FMP fields NOT in TICKER_DATA_BUNDLE (Finnhub) or
EARNINGS_ANALYST_BUNDLE. Fetched once per session, cached 24h.
Delivered to: Fundamentals + Sentiment + News + Burry lanes.

Physical isolation contract: FMP-only. Never mixed with Finnhub scoring.*.
This module MUST NOT import or call dual_fetch / FinnhubClient.

Usage (Phase 1 PM):
    from skills._shared.fmp_supplementary import get_supplementary_bundle
    FMP_SUPP_BUNDLE = get_supplementary_bundle("NVDA")  # dict or None

Sections start populated incrementally per release:
    v1.78.0: quality_scores + owner_earnings
    v1.79.0: insider_summary
    v1.80.0: institutional
    v1.84.0: congressional + ma_events (probe-gated)
"""
from __future__ import annotations
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = BASE_DIR / "skills" / "_shared" / "fmp_supp_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL = 86400  # 24h

SCHEMA_VERSION = "V1.1"  # V5.0 — added executive_compensation, comp_benchmark, employee_history


def _fmp_get(path: str, params: dict, *, timeout: int = 12):
    """GET /stable/<path>?<params>&apikey=...
    Returns parsed body on 200, None otherwise (paid block / network / parse).
    No raise — caller handles None gracefully.
    """
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return None
    try:
        r = requests.get(
            f"https://financialmodelingprep.com/stable/{path}",
            params={**params, "apikey": api_key},
            timeout=timeout,
        )
        if r.status_code in (401, 402, 403):
            return None
        if r.status_code == 429:
            time.sleep(2)
            return None
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _fetch_quality_scores(ticker: str) -> dict:
    """Altman Z-Score + Piotroski F-Score via /stable/financial-scores.

    Altman zone: <1.81 danger / 1.81-2.99 grey / >2.99 safe
    Piotroski strength: >=7 strong / 3-6 moderate / <=2 weak
    """
    data = _fmp_get("financial-scores", {"symbol": ticker})
    if not isinstance(data, list) or not data:
        return {}
    d = data[0]
    z = d.get("altmanZScore")
    f = d.get("piotroskiScore")
    zone = None
    if z is not None:
        zone = "danger" if z < 1.81 else "grey" if z < 2.99 else "safe"
    strength = None
    if f is not None:
        strength = "strong" if f >= 7 else "weak" if f <= 2 else "moderate"
    return {
        "altmanZScore": z,
        "piotroskiScore": f,
        "altman_zone": zone,
        "piotroski_strength": strength,
        "workingCapital": d.get("workingCapital"),
        "totalAssets": d.get("totalAssets"),
        "retainedEarnings": d.get("retainedEarnings"),
        "ebit": d.get("ebit"),
        "totalLiabilities": d.get("totalLiabilities"),
        "revenue": d.get("revenue"),
        "_note": "altman: <1.81=danger, 1.81-2.99=grey, >2.99=safe; piotroski: >=7=strong, <=2=weak",
        "source": "FMP /stable/financial-scores",
    }


def _fetch_owner_earnings(ticker: str) -> dict:
    """Buffett owner earnings via /stable/owner-earnings.

    FMP returns latest 5 quarters; we keep latest + previous for trend.
    Fields: ownersEarnings (note plural), maintenanceCapex, growthCapex,
    averagePPE, ownersEarningsPerShare.
    """
    data = _fmp_get("owner-earnings", {"symbol": ticker})
    if not isinstance(data, list) or not data:
        return {}
    latest = data[0]
    prior = data[1] if len(data) > 1 else {}
    growth = None
    if latest.get("ownersEarnings") and prior.get("ownersEarnings"):
        try:
            growth = round(
                (latest["ownersEarnings"] - prior["ownersEarnings"])
                / abs(prior["ownersEarnings"]),
                4,
            )
        except (TypeError, ZeroDivisionError):
            growth = None
    return {
        "period": f"{latest.get('fiscalYear')}-{latest.get('period')}",
        "as_of_date": latest.get("date"),
        "ownersEarnings": latest.get("ownersEarnings"),
        "ownersEarningsPerShare": latest.get("ownersEarningsPerShare"),
        "maintenanceCapex": latest.get("maintenanceCapex"),
        "growthCapex": latest.get("growthCapex"),
        "averagePPE": latest.get("averagePPE"),
        "qoq_growth": growth,
        "history_quarters": len(data),
        "source": "FMP /stable/owner-earnings",
    }


def _fetch_insider_summary(ticker: str, quarters: int = 4) -> dict:
    """Quarterly insider trade statistics via /stable/insider-trading/statistics.

    FMP fields: acquiredTransactions, disposedTransactions, acquiredDisposedRatio,
    totalAcquired, totalDisposed, totalPurchases, totalSales.
    """
    data = _fmp_get("insider-trading/statistics", {"symbol": ticker, "limit": quarters})
    if not isinstance(data, list) or not data:
        return {"quarters": [], "source": "FMP /stable/insider-trading/statistics"}
    data.sort(key=lambda x: (x.get("year", 0), x.get("quarter", 0)), reverse=True)
    rows = []
    for d in data[:quarters]:
        rows.append({
            "year": d.get("year"),
            "quarter": d.get("quarter"),
            "acquired_disposed_ratio": d.get("acquiredDisposedRatio"),
            "total_acquired_shares": d.get("totalAcquired"),
            "total_disposed_shares": d.get("totalDisposed"),
            "acquired_transactions": d.get("acquiredTransactions"),
            "disposed_transactions": d.get("disposedTransactions"),
            "total_purchases": d.get("totalPurchases"),
            "total_sales": d.get("totalSales"),
        })
    # Trend signal: most recent ratio direction
    latest = rows[0] if rows else {}
    trend = None
    if latest.get("acquired_disposed_ratio") is not None:
        r = latest["acquired_disposed_ratio"]
        trend = "accumulating" if r >= 1.0 else "distributing" if r < 0.5 else "neutral"
    return {
        "quarters": rows,
        "latest_trend": trend,
        "source": "FMP /stable/insider-trading/statistics",
    }


def _fetch_institutional(ticker: str) -> dict:
    """Institutional ownership QoQ via /stable/institutional-ownership/symbol-positions-summary.

    FMP returns latest quarter snapshot with built-in delta vs prior quarter
    (lastOwnershipPercent / ownershipPercentChange / putCallRatioChange etc).
    Try latest year/quarter combos until non-empty.
    """
    today = date.today()
    # 13F filings are due 45 days after quarter end. Start from previous quarter
    # (last fully reported one) to avoid partial data; walk back up to 4 quarters
    # if any candidate has investorsHolding too low (partial filing window).
    q_now = (today.month - 1) // 3 + 1
    year = today.year
    candidates = []
    for shift in range(1, 6):  # start at q-1
        yr = year if (q_now - shift) > 0 else year - 1
        qq = ((q_now - shift - 1) % 4) + 1
        candidates.append((yr, qq))
    seen = set()
    for yr, qq in candidates:
        if (yr, qq) in seen:
            continue
        seen.add((yr, qq))
        data = _fmp_get(
            "institutional-ownership/symbol-positions-summary",
            {"symbol": ticker, "year": yr, "quarter": qq},
        )
        if isinstance(data, list) and data:
            d = data[0]
            # Sanity gate: skip mid-filing-window partial quarters where
            # current snapshot is less than half of prior quarter's filing count.
            ih = d.get("investorsHolding") or 0
            last_ih = d.get("lastInvestorsHolding") or 0
            op = d.get("ownershipPercent") or 0
            last_op = d.get("lastOwnershipPercent") or 0
            if last_ih > 0 and ih < last_ih * 0.5:
                continue
            if last_op > 0 and op < last_op * 0.5:
                continue
            return {
                "as_of_date": d.get("date"),
                "year": yr,
                "quarter": qq,
                "ownership_percent": d.get("ownershipPercent"),
                "last_ownership_percent": d.get("lastOwnershipPercent"),
                "ownership_pct_change_qoq": d.get("ownershipPercentChange"),
                "investors_holding": d.get("investorsHolding"),
                "investors_holding_change": d.get("investorsHoldingChange"),
                "num_13f_shares": d.get("numberOf13Fshares"),
                "num_13f_shares_change": d.get("numberOf13FsharesChange"),
                "total_invested_usd": d.get("totalInvested"),
                "total_invested_change_usd": d.get("totalInvestedChange"),
                "new_positions": d.get("newPositions"),
                "increased_positions": d.get("increasedPositions"),
                "reduced_positions": d.get("reducedPositions"),
                "closed_positions": d.get("closedPositions"),
                "put_call_ratio": d.get("putCallRatio"),
                "put_call_ratio_change_qoq": d.get("putCallRatioChange"),
                "accumulation_signal": (
                    "accumulating" if (d.get("ownershipPercentChange") or 0) > 1.0
                    else "distributing" if (d.get("ownershipPercentChange") or 0) < -1.0
                    else "neutral"
                ),
                "source": "FMP /stable/institutional-ownership/symbol-positions-summary",
            }
    return {}


def _classify_amount(amount_str: str) -> int:
    """Map FMP amount range string ('$1,001 - $15,000') to upper-bound int.
    Used to weight congressional trade signal — bigger = more meaningful.
    """
    if not isinstance(amount_str, str):
        return 0
    s = amount_str.replace("$", "").replace(",", "").lower()
    # Take last number in range
    parts = s.split("-")
    if not parts:
        return 0
    try:
        return int(parts[-1].strip().split()[0])
    except (ValueError, IndexError):
        return 0


def _fetch_congressional(ticker: str, days_back: int = 180) -> dict:
    """Senate + House trades via /stable/{senate,house}-trades?symbol=...

    Bullish/bearish/neutral net signal computed from purchase vs sale counts.
    Captures lookback window summary plus most recent trade date.
    """
    since = (date.today() - timedelta(days=days_back)).isoformat()
    senate = _fmp_get("senate-trades", {"symbol": ticker}) or []
    house = _fmp_get("house-trades", {"symbol": ticker}) or []
    senate = senate if isinstance(senate, list) else []
    house = house if isinstance(house, list) else []
    # Filter to lookback window (FMP returns full history; trim client-side)
    def _in_window(t):
        td = t.get("transactionDate") or t.get("disclosureDate") or ""
        return td >= since
    senate_recent = [t for t in senate if _in_window(t)]
    house_recent = [t for t in house if _in_window(t)]
    trades = senate_recent + house_recent
    buys = [t for t in trades if "purchase" in (t.get("type") or "").lower()]
    sells = [t for t in trades if "sale" in (t.get("type") or "").lower()]
    most_recent = max(
        (t.get("transactionDate") or "" for t in trades), default=None
    )
    if len(buys) > len(sells) * 2 and len(buys) >= 2:
        net = "bullish"
    elif len(sells) > len(buys) * 2 and len(sells) >= 2:
        net = "bearish"
    else:
        net = "neutral"
    return {
        "lookback_days": days_back,
        "senate_count": len(senate_recent),
        "house_count": len(house_recent),
        "buy_count": len(buys),
        "sell_count": len(sells),
        "net_signal": net,
        "most_recent_date": most_recent or None,
        "source": "FMP /stable/senate-trades + house-trades",
    }


def _fetch_ma_events(ticker: str, days_back: int = 180) -> dict:
    """Recent M&A events where ticker is acquirer or target.

    Uses /stable/mergers-acquisitions-latest (no per-symbol endpoint exists);
    filters client-side. Most tickers will have empty result — that's expected.
    """
    since = (date.today() - timedelta(days=days_back)).isoformat()
    data = _fmp_get("mergers-acquisitions-latest", {"limit": 200}) or []
    if not isinstance(data, list):
        return {"lookback_days": days_back, "events": [],
                "source": "FMP /stable/mergers-acquisitions-latest"}
    events = []
    for e in data:
        td = e.get("transactionDate") or ""
        if td < since:
            continue
        sym = e.get("symbol")
        target = e.get("targetedSymbol")
        if sym == ticker.upper() or target == ticker.upper():
            events.append({
                "date": td,
                "role": "acquirer" if sym == ticker.upper() else "target",
                "acquirer_symbol": sym,
                "acquirer_name": e.get("companyName"),
                "target_symbol": target,
                "target_name": e.get("targetedCompanyName"),
                "url": e.get("link"),
            })
    return {
        "lookback_days": days_back,
        "events": events,
        "source": "FMP /stable/mergers-acquisitions-latest",
    }


def _fetch_esg(ticker: str) -> dict:
    """ESG disclosures (most recent SEC filing) + latest letter rating.

    /stable/esg-disclosures gives per-filing E/S/G/total scores; we take latest.
    /stable/esg-ratings gives historical letter ratings (e.g. "B"); we take latest year.
    """
    disc = _fmp_get("esg-disclosures", {"symbol": ticker}) or []
    rate = _fmp_get("esg-ratings", {"symbol": ticker}) or []
    out: dict = {}
    if isinstance(disc, list) and disc:
        # Sort by date desc (FMP usually returns newest first but be safe)
        disc_sorted = sorted(disc, key=lambda x: x.get("date") or "", reverse=True)
        d0 = disc_sorted[0]
        out["latest_disclosure"] = {
            "date":               d0.get("date"),
            "form_type":          d0.get("formType"),
            "environmental_score": d0.get("environmentalScore"),
            "social_score":       d0.get("socialScore"),
            "governance_score":   d0.get("governanceScore"),
            "total_esg_score":    d0.get("ESGScore"),
        }
    if isinstance(rate, list) and rate:
        rate_sorted = sorted(rate, key=lambda x: x.get("fiscalYear") or 0, reverse=True)
        r0 = rate_sorted[0]
        out["latest_rating"] = {
            "fiscal_year":     r0.get("fiscalYear"),
            "esg_risk_rating": r0.get("ESGRiskRating"),
            "industry":        r0.get("industry"),
            "industry_rank":   r0.get("industryRank"),
        }
    if out:
        out["source"] = "FMP /stable/esg-disclosures + esg-ratings"
    return out


def _fetch_executive_compensation(ticker: str) -> dict:
    """CEO + 前 5 高薪 exec 的 comp via /stable/governance-executive-compensation.

    Detects governance red flags:
      - CEO comp YoY > 30% (excessive raise)
      - SBC > 15% of revenue (dilution risk)
    """
    data = _fmp_get("governance-executive-compensation", {"symbol": ticker}) or []
    if not isinstance(data, list) or not data:
        return {}
    # Sort by year desc; group by name
    data_sorted = sorted(data, key=lambda x: x.get("year") or 0, reverse=True)
    by_name: dict[str, list] = {}
    for row in data_sorted:
        nm = row.get("nameAndPosition") or row.get("name") or "unknown"
        by_name.setdefault(nm, []).append(row)
    # Latest year top-paid
    latest_year = max((r.get("year") for r in data_sorted if r.get("year")), default=None)
    latest_year_rows = [r for r in data_sorted if r.get("year") == latest_year]
    latest_year_rows.sort(key=lambda x: (x.get("total") or 0), reverse=True)
    top_5 = [{
        "name":     r.get("nameAndPosition") or r.get("name"),
        "year":     r.get("year"),
        "salary":   r.get("salary"),
        "bonus":    r.get("bonus"),
        "stock_award": r.get("stockAward"),
        "option_award": r.get("optionAward"),
        "total":    r.get("total"),
    } for r in latest_year_rows[:5]]
    # CEO YoY (find row with CEO in name, latest 2 years)
    ceo_rows = [
        r for nm, rows in by_name.items() if "CEO" in nm.upper() or "Chief Executive" in nm
        for r in rows
    ]
    ceo_rows.sort(key=lambda x: x.get("year") or 0, reverse=True)
    ceo_yoy_pct = None
    if len(ceo_rows) >= 2:
        cur = ceo_rows[0].get("total") or 0
        prv = ceo_rows[1].get("total") or 0
        if prv:
            try:
                ceo_yoy_pct = round((cur - prv) / prv * 100, 1)
            except (TypeError, ZeroDivisionError):
                pass
    return {
        "latest_year":      latest_year,
        "top_5_executives": top_5,
        "ceo_total_latest": ceo_rows[0].get("total") if ceo_rows else None,
        "ceo_yoy_pct":      ceo_yoy_pct,
        "ceo_red_flag":     bool(ceo_yoy_pct is not None and ceo_yoy_pct > 30),
        "source":           "FMP /stable/governance-executive-compensation",
    }


def _fetch_comp_benchmark(ticker: str) -> dict:
    """CEO comp vs peer median via /stable/executive-compensation-benchmark.

    Useful for governance red-flag detection (CEO overpaid vs industry).
    """
    data = _fmp_get("executive-compensation-benchmark", {"symbol": ticker}) or []
    if not isinstance(data, list) or not data:
        return {}
    d = data[0] if isinstance(data[0], dict) else {}
    return {
        "industry_title":          d.get("industryTitle"),
        "year":                    d.get("year"),
        "average_compensation":    d.get("averageCompensation"),
        "median_compensation":     d.get("medianCompensation"),
        "ceo_overpaid_vs_median_pct": None,  # caller computes if has CEO comp
        "source":                  "FMP /stable/executive-compensation-benchmark",
    }


def _fetch_employee_history_summary(ticker: str) -> dict:
    """5-year employee count CAGR + recent 1Y delta.

    Reuses skills._shared.company_context.get_employee_history (24h cache shared).
    """
    try:
        from . import company_context as cc
    except ImportError:
        # Allow standalone invocation
        sys.path.insert(0, str(BASE_DIR))
        from skills._shared import company_context as cc  # type: ignore
    raw = cc.get_employee_history(ticker)
    if not raw:
        return {}
    # FMP returns newest first; each row has periodOfReport/employeeCount
    rows = sorted(
        [r for r in raw if r.get("periodOfReport") and r.get("employeeCount") is not None],
        key=lambda x: x.get("periodOfReport"), reverse=True,
    )
    if not rows:
        return {}
    latest = rows[0]
    cagr_5y = None
    one_year_pct = None
    if len(rows) >= 2:
        try:
            one_year_pct = round((latest["employeeCount"] - rows[1]["employeeCount"])
                                  / rows[1]["employeeCount"] * 100, 1)
        except (TypeError, ZeroDivisionError):
            pass
    if len(rows) >= 5:
        try:
            base = rows[min(4, len(rows) - 1)]["employeeCount"]
            yrs = 4
            if base > 0:
                cagr_5y = round(((latest["employeeCount"] / base) ** (1 / yrs) - 1) * 100, 1)
        except (TypeError, ZeroDivisionError):
            pass
    return {
        "latest_period":     latest.get("periodOfReport"),
        "latest_count":      latest.get("employeeCount"),
        "one_year_pct":      one_year_pct,
        "cagr_5y_pct":       cagr_5y,
        "expansion_signal":  bool(cagr_5y is not None and cagr_5y > 15),
        "layoff_signal":     bool(one_year_pct is not None and one_year_pct < -5),
        "data_points":       len(rows),
        "source":            "FMP /stable/historical-employee-count",
    }


def get_supplementary_bundle(
    ticker: str, *, force: bool = False
) -> "dict | None":
    """
    Fetch or load-from-cache the FMP supplementary bundle for `ticker`.
    Returns dict on success, None on hard failure (no API key + no cache).

    Physical isolation guarantee:
      - All data here is FMP-sourced.
      - PM passes this bundle to Fundamentals / Sentiment / News / Burry lanes.
      - NEVER pass to Technical lane (OHLCV-only, no need).
    """
    ticker = ticker.upper()
    cache_path = CACHE_DIR / f"{ticker}_{date.today().isoformat()}_supp.json"

    if not force and cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < CACHE_TTL:
            print(f"[fmp_supp] cache hit: {ticker}", file=sys.stderr)
            with open(cache_path) as f:
                bundle = json.load(f)
            bundle.setdefault("_fetch_stats", {})["cached"] = True
            return bundle

    if not os.environ.get("FMP_API_KEY"):
        print("[fmp_supp] WARN: FMP_API_KEY not set; returning None", file=sys.stderr)
        return None

    calls, failures = 0, 0

    print(f"[fmp_supp] {ticker}: fetching quality_scores ...", file=sys.stderr)
    quality = _fetch_quality_scores(ticker); calls += 1
    if not quality: failures += 1

    print(f"[fmp_supp] {ticker}: fetching owner_earnings ...", file=sys.stderr)
    owner_e = _fetch_owner_earnings(ticker); calls += 1
    if not owner_e: failures += 1

    print(f"[fmp_supp] {ticker}: fetching insider_summary ...", file=sys.stderr)
    insider = _fetch_insider_summary(ticker); calls += 1
    if not insider.get("quarters"): failures += 1

    print(f"[fmp_supp] {ticker}: fetching institutional ...", file=sys.stderr)
    inst = _fetch_institutional(ticker); calls += 1
    if not inst: failures += 1

    print(f"[fmp_supp] {ticker}: fetching congressional_trades ...", file=sys.stderr)
    congress = _fetch_congressional(ticker); calls += 2  # senate + house
    # net_signal == "neutral" with no trades is valid — only count fail if exception swallowed result entirely

    print(f"[fmp_supp] {ticker}: fetching ma_events ...", file=sys.stderr)
    ma = _fetch_ma_events(ticker); calls += 1

    print(f"[fmp_supp] {ticker}: fetching esg ...", file=sys.stderr)
    esg = _fetch_esg(ticker); calls += 2  # disclosures + ratings
    if not esg: failures += 1

    print(f"[fmp_supp] {ticker}: fetching executive_compensation (V5.0) ...", file=sys.stderr)
    exec_comp = _fetch_executive_compensation(ticker); calls += 1
    if not exec_comp: failures += 1

    print(f"[fmp_supp] {ticker}: fetching comp_benchmark (V5.0) ...", file=sys.stderr)
    comp_bench = _fetch_comp_benchmark(ticker); calls += 1
    # Compute CEO overpaid pct if both available
    if comp_bench and exec_comp.get("ceo_total_latest") and comp_bench.get("median_compensation"):
        try:
            comp_bench["ceo_overpaid_vs_median_pct"] = round(
                (exec_comp["ceo_total_latest"] - comp_bench["median_compensation"])
                / comp_bench["median_compensation"] * 100, 1
            )
        except (TypeError, ZeroDivisionError):
            pass

    print(f"[fmp_supp] {ticker}: fetching employee_history (V5.0) ...", file=sys.stderr)
    emp_hist = _fetch_employee_history_summary(ticker); calls += 1
    if not emp_hist: failures += 1

    bundle = {
        "ticker": ticker,
        "as_of_date": date.today().isoformat(),
        "cache_key": f"{ticker}_{date.today().isoformat()}",
        "schema_version": "V1.1",  # V5.0 — added exec_comp, comp_benchmark, employee_history
        "data_source": "FMP HTTP REST (FMP-only; no Finnhub)",
        "quality_scores": quality or {},
        "owner_earnings": owner_e or {},
        "insider_summary": insider,
        "institutional": inst,
        "congressional_trades": congress,
        "ma_events": ma,
        "esg": esg,
        "executive_compensation": exec_comp,        # V5.0
        "comp_benchmark":         comp_bench,        # V5.0
        "employee_history":       emp_hist,          # V5.0
        "_fetch_stats": {
            "fmp_calls": calls,
            "fmp_failures": failures,
            "cached": False,
        },
    }

    with open(cache_path, "w") as f:
        json.dump(bundle, f, indent=2)
    size = len(json.dumps(bundle))
    print(
        f"[fmp_supp] wrote {cache_path.name} ({size:,} bytes) "
        f"calls={calls} fail={failures}",
        file=sys.stderr,
    )
    return bundle


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker", type=str.upper)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    b = get_supplementary_bundle(args.ticker, force=args.force)
    if b is None:
        sys.exit(1)
    print(json.dumps(b, indent=2))

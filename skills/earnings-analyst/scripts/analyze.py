"""
earnings-analyst — derived metrics + composite scoring (V1.0)

Reads skills/earnings-analyst/cache/<TICKER>_<DATE>.json (produced by fetch.py),
computes:
  - margins_8q (gross / operating / net per quarter)
  - yoy_growth (rev / ni / op + acceleration label)
  - balance_health (working_capital / current_ratio / D/E / net_cash)
  - cash_flow_quality (FCF margin / cash conversion / capex intensity)
  - quality_flags (deterministic — accruals / capex outpace / margin compress / DSO slow / etc.)
  - composite_score 0-100 + verdict (Quality 30 / Growth 30 / Valuation 25 / Analyst 15)

Writes augmented JSON in-place: cache file gains `derived`, `quality_flags`,
`composite_score`, `verdict`, `score_components`.

Usage:
    python3 skills/earnings-analyst/scripts/analyze.py NVDA
    python3 skills/earnings-analyst/scripts/analyze.py --json <path-to-cache.json>
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CACHE_DIR = os.path.join(BASE_DIR, "skills", "earnings-analyst", "cache")


def safe_div(a, b):
    if a is None or b is None:
        return None
    try:
        b = float(b)
        if b == 0:
            return None
        return float(a) / b
    except (TypeError, ValueError):
        return None


def latest_q(rows: list) -> dict:
    return rows[0] if rows else {}


def find_cache(ticker: str) -> str | None:
    files = sorted(glob.glob(os.path.join(CACHE_DIR, f"{ticker}_*.json")))
    return files[-1] if files else None


def compute_margins_8q(income: list) -> list:
    out = []
    for r in income:
        rev = r.get("revenue")
        out.append({
            "date":      r.get("date"),
            "period":    r.get("period"),
            "gross":     safe_div(r.get("grossProfit"), rev),
            "operating": safe_div(r.get("operatingIncome"), rev),
            "net":       safe_div(r.get("netIncome"), rev),
        })
    return out


def compute_yoy_growth(income: list) -> dict:
    """Latest Q vs same Q a year ago (idx 0 vs idx 4)."""
    if len(income) < 5:
        return {"revenue_yoy": None, "earnings_yoy": None, "operating_yoy": None,
                "revenue_qoq": None, "growth_acceleration": "insufficient_history"}
    cur = income[0]
    prior_y = income[4]
    prior_q = income[1]

    rev_yoy = safe_div(
        (cur.get("revenue") or 0) - (prior_y.get("revenue") or 0),
        prior_y.get("revenue"),
    )
    earn_yoy = safe_div(
        (cur.get("netIncome") or 0) - (prior_y.get("netIncome") or 0),
        abs(prior_y.get("netIncome") or 1) if prior_y.get("netIncome") else None,
    )
    op_yoy = safe_div(
        (cur.get("operatingIncome") or 0) - (prior_y.get("operatingIncome") or 0),
        abs(prior_y.get("operatingIncome") or 1) if prior_y.get("operatingIncome") else None,
    )
    rev_qoq = safe_div(
        (cur.get("revenue") or 0) - (prior_q.get("revenue") or 0),
        prior_q.get("revenue"),
    )

    # Acceleration: compare latest YoY vs prior-quarter YoY
    if len(income) >= 6:
        prior_y_for_q1 = income[5]  # Q-1 vs Q-5
        prior_q_yoy = safe_div(
            (prior_q.get("revenue") or 0) - (prior_y_for_q1.get("revenue") or 0),
            prior_y_for_q1.get("revenue"),
        )
        if rev_yoy is not None and prior_q_yoy is not None:
            delta = rev_yoy - prior_q_yoy
            if delta > 0.02:
                accel = "accelerating"
            elif delta < -0.02:
                accel = "decelerating"
            else:
                accel = "steady"
        else:
            accel = "insufficient_history"
    else:
        accel = "insufficient_history"

    return {
        "revenue_yoy":         round(rev_yoy, 4) if rev_yoy is not None else None,
        "earnings_yoy":        round(earn_yoy, 4) if earn_yoy is not None else None,
        "operating_yoy":       round(op_yoy, 4) if op_yoy is not None else None,
        "revenue_qoq":         round(rev_qoq, 4) if rev_qoq is not None else None,
        "growth_acceleration": accel,
    }


def compute_balance_health(balance: list) -> dict:
    if not balance:
        return {}
    cur = latest_q(balance)
    cash = (cur.get("cashAndCashEquivalents") or 0) + (cur.get("shortTermInvestments") or 0)
    debt = cur.get("totalDebt") or 0
    return {
        "working_capital":  (cur.get("totalCurrentAssets") or 0) - (cur.get("totalCurrentLiabilities") or 0),
        "current_ratio":    round(safe_div(cur.get("totalCurrentAssets"),
                                            cur.get("totalCurrentLiabilities")) or 0, 3),
        "debt_to_equity":   round(safe_div(cur.get("totalDebt"), cur.get("totalEquity")) or 0, 3),
        "net_cash":         cash - debt,
    }


def compute_cf_quality(cashflow: list, income: list) -> dict:
    if not cashflow or not income:
        return {}
    cur_cf = latest_q(cashflow)
    cur_in = latest_q(income)

    # TTM cash conversion = sum(OpCF[0..3]) / sum(NI[0..3])
    ocf_ttm = sum((r.get("operatingCashFlow") or 0) for r in cashflow[:4])
    ni_ttm = sum((r.get("netIncome") or 0) for r in income[:4])

    return {
        "fcf_margin":      round(safe_div(cur_cf.get("freeCashFlow"), cur_in.get("revenue")) or 0, 4),
        "cash_conversion": round(safe_div(ocf_ttm, ni_ttm) or 0, 3) if ni_ttm else None,
        "capex_intensity": round(safe_div(abs(cur_cf.get("capitalExpenditure") or 0),
                                          cur_in.get("revenue")) or 0, 4),
        "ocf_ttm":         ocf_ttm,
        "ni_ttm":          ni_ttm,
    }


def compute_quality_flags(income: list, balance: list, cashflow: list, cf_q: dict) -> list[str]:
    flags = []

    # 1. Accruals warning: |NI − OpCF| / |NI| > 0.30 (TTM)
    ni_ttm = cf_q.get("ni_ttm") or 0
    ocf_ttm = cf_q.get("ocf_ttm") or 0
    if ni_ttm and abs(ni_ttm - ocf_ttm) / abs(ni_ttm) > 0.30:
        flags.append("accruals_warning")

    # 2. Capex outpaces OCF (latest Q)
    if cashflow:
        capex = abs(cashflow[0].get("capitalExpenditure") or 0)
        ocf = cashflow[0].get("operatingCashFlow") or 0
        if capex > 0 and ocf > 0 and ocf / capex < 1.0:
            flags.append("capex_outpaces_ocf")

    # 3. Gross margin compression: 4 sequential drops (Q0 < Q1 < Q2 < Q3)
    if len(income) >= 4:
        margins = []
        for r in income[:4]:
            m = safe_div(r.get("grossProfit"), r.get("revenue"))
            if m is None:
                margins = []
                break
            margins.append(m)
        if margins and margins[0] < margins[1] < margins[2] < margins[3]:
            flags.append("gross_margin_compression")

    # 4. DSO slowdown: receivables/revenue×91 sequential up over 4 quarters
    if len(income) >= 4 and len(balance) >= 4:
        dsos = []
        for i in range(4):
            ar = balance[i].get("netReceivables")
            rev = income[i].get("revenue")
            d = safe_div(ar, rev)
            if d is None:
                dsos = []
                break
            dsos.append(d * 91)
        if dsos and dsos[0] > dsos[1] > dsos[2] > dsos[3]:
            flags.append("dso_slowdown")

    # 5. Negative FCF latest Q
    if cashflow and (cashflow[0].get("freeCashFlow") or 0) < 0:
        flags.append("negative_fcf")

    # 6. Debt buildup: totalDebt 環比增 > 15% 連 2 季
    if len(balance) >= 3:
        d0 = balance[0].get("totalDebt") or 0
        d1 = balance[1].get("totalDebt") or 0
        d2 = balance[2].get("totalDebt") or 0
        if d1 > 0 and d2 > 0:
            r01 = (d0 - d1) / d1
            r12 = (d1 - d2) / d2
            if r01 > 0.15 and r12 > 0.15:
                flags.append("debt_buildup")

    return flags


def score_quality(flags: list, ttm: dict, cf_q: dict) -> int:
    """0-30. Penalize flags; reward strong income quality + cash conversion."""
    base = 25
    base -= len(flags) * 4  # each flag −4
    iq = ttm.get("from_key_metrics_ttm", {}).get("incomeQualityTTM") or 0
    if iq > 1.1:
        base += 3
    cc = cf_q.get("cash_conversion") or 0
    if cc > 1.1:
        base += 2
    return max(0, min(30, base))


def score_growth(yoy: dict, growth: list) -> int:
    """0-30. Reward YoY revenue + acceleration + 5y CAGR."""
    base = 10
    rev_yoy = yoy.get("revenue_yoy")
    if rev_yoy is not None:
        if rev_yoy > 0.30: base += 10
        elif rev_yoy > 0.15: base += 7
        elif rev_yoy > 0.05: base += 4
        elif rev_yoy < 0: base -= 5

    accel = yoy.get("growth_acceleration")
    if accel == "accelerating": base += 5
    elif accel == "decelerating": base -= 3

    if growth:
        cagr5 = (growth[0] or {}).get("fiveYRevenueGrowthPerShare") or 0
        if cagr5 > 0.20: base += 5
        elif cagr5 > 0.10: base += 3
        elif cagr5 < 0: base -= 3

    return max(0, min(30, base))


def score_valuation(valuation: dict, ttm: dict, snapshot: dict) -> int:
    """0-25. DCF discount + FCF yield + EV/EBITDA + ratings overall."""
    base = 10
    price = snapshot.get("price")
    dcf = valuation.get("dcf_intrinsic")
    if dcf and price:
        upside = (dcf - price) / price
        if upside > 0.20: base += 6
        elif upside > 0.0: base += 3
        elif upside < -0.20: base -= 5

    fcfy = ttm.get("from_key_metrics_ttm", {}).get("freeCashFlowYieldTTM") or 0
    if fcfy > 0.05: base += 4
    elif fcfy > 0.03: base += 2
    elif fcfy < 0: base -= 3

    overall = (valuation.get("ratings_snapshot") or {}).get("overallScore")
    if overall in (4, 5): base += 3
    elif overall in (1, 2): base -= 3

    return max(0, min(25, base))


def score_analyst(valuation: dict, snapshot: dict, grades: list) -> int:
    """0-15. Price target upside + grades-historical net buy."""
    base = 5
    price = snapshot.get("price")
    pt = valuation.get("price_target_consensus")
    if pt and price:
        upside = (pt - price) / price
        if upside > 0.15: base += 5
        elif upside > 0.05: base += 3
        elif upside < -0.05: base -= 3

    if grades:
        latest = grades[0]
        buys = (latest.get("analystRatingsStrongBuy") or 0) + (latest.get("analystRatingsBuy") or 0)
        sells = (latest.get("analystRatingsSell") or 0) + (latest.get("analystRatingsStrongSell") or 0)
        total = buys + sells + (latest.get("analystRatingsHold") or 0)
        if total > 0:
            buy_pct = buys / total
            if buy_pct > 0.75: base += 5
            elif buy_pct > 0.55: base += 3
            elif buy_pct < 0.25: base -= 3

    return max(0, min(15, base))


def verdict_for(score: int) -> str:
    if score >= 80:  return "STRONG"
    if score >= 65:  return "SOLID"
    if score >= 50:  return "MIXED"
    if score >= 35:  return "WEAK"
    return "DETERIORATING"


def analyze(bundle: dict) -> dict:
    income = bundle.get("quarterly_pnl") or []
    balance = bundle.get("balance_sheet") or []
    cashflow = bundle.get("cash_flow") or []
    ttm = bundle.get("ttm_metrics") or {}
    growth = bundle.get("annual_growth") or []
    valuation = bundle.get("valuation") or {}
    snapshot = bundle.get("snapshot") or {}
    grades = bundle.get("analyst_grades") or []

    margins_8q = compute_margins_8q(income)
    yoy = compute_yoy_growth(income)
    bh = compute_balance_health(balance)
    cf_q = compute_cf_quality(cashflow, income)
    flags = compute_quality_flags(income, balance, cashflow, cf_q)

    sc_quality = score_quality(flags, ttm, cf_q)
    sc_growth = score_growth(yoy, growth)
    sc_valuation = score_valuation(valuation, ttm, snapshot)
    sc_analyst = score_analyst(valuation, snapshot, grades)
    composite = sc_quality + sc_growth + sc_valuation + sc_analyst

    # DCF / PT upside derived
    price = snapshot.get("price")
    dcf = valuation.get("dcf_intrinsic")
    pt = valuation.get("price_target_consensus")
    if price and dcf:
        valuation["dcf_vs_price_pct"] = round((dcf - price) / price, 4)
    if price and pt:
        valuation["pt_upside_pct"] = round((pt - price) / price, 4)

    bundle["derived"] = {
        "margins_8q":         margins_8q,
        "yoy_growth":         yoy,
        "balance_health":     bh,
        "cash_flow_quality":  cf_q,
    }
    bundle["quality_flags"]    = flags
    bundle["composite_score"]  = composite
    bundle["verdict"]          = verdict_for(composite)
    bundle["score_components"] = {
        "quality":   sc_quality,
        "growth":    sc_growth,
        "valuation": sc_valuation,
        "analyst":   sc_analyst,
    }
    return bundle


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker", nargs="?")
    ap.add_argument("--json", help="explicit cache path")
    args = ap.parse_args()

    if args.json:
        path = args.json
    else:
        if not args.ticker:
            sys.exit("Usage: analyze.py <TICKER>  (or --json <path>)")
        path = find_cache(args.ticker.upper())
        if not path:
            sys.exit(f"[ERROR] no cache for {args.ticker} — run fetch.py first")

    with open(path) as f:
        bundle = json.load(f)

    bundle = analyze(bundle)

    with open(path, "w") as f:
        json.dump(bundle, f, indent=2)

    print(f"[analyze] {bundle['ticker']}: composite={bundle['composite_score']}/100 "
          f"verdict={bundle['verdict']} "
          f"flags={bundle['quality_flags'] or 'clean'} "
          f"(Q{bundle['score_components']['quality']}/30 "
          f"G{bundle['score_components']['growth']}/30 "
          f"V{bundle['score_components']['valuation']}/25 "
          f"A{bundle['score_components']['analyst']}/15)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

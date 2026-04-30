"""
earnings-analyst — Markdown report renderer (V1.0)

Reads enriched cache JSON (post-analyze.py) and writes a 10-section earnings
analysis report to reports/<RUN_DATE>_<TICKER>_earnings.md.

Usage:
    python3 skills/earnings-analyst/scripts/render.py NVDA
    python3 skills/earnings-analyst/scripts/render.py --json <cache.json>
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CACHE_DIR = os.path.join(BASE_DIR, "skills", "earnings-analyst", "cache")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


def find_cache(ticker: str) -> str | None:
    files = sorted(glob.glob(os.path.join(CACHE_DIR, f"{ticker}_*.json")))
    return files[-1] if files else None


def fmt_money(v):
    if v is None: return "—"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(v) >= 1e9: return f"${v/1e9:,.2f}B"
    if abs(v) >= 1e6: return f"${v/1e6:,.1f}M"
    if abs(v) >= 1e3: return f"${v/1e3:,.1f}K"
    return f"${v:,.2f}"


def fmt_pct(v):
    if v is None: return "—"
    try: return f"{float(v)*100:+.1f}%"
    except (TypeError, ValueError): return "—"


def fmt_pct_abs(v):
    if v is None: return "—"
    try: return f"{float(v)*100:.1f}%"
    except (TypeError, ValueError): return "—"


def fmt_num(v, dp=2):
    if v is None: return "—"
    try: return f"{float(v):,.{dp}f}"
    except (TypeError, ValueError): return "—"


def render_header(d):
    snap = d.get("snapshot") or {}
    return [
        f"# {d['ticker']} 財報分析 — {snap.get('companyName') or d['ticker']}",
        "",
        f"> Run: {d['as_of_date']}  ·  Last Earnings: {d['last_earnings_date']} "
        f"({d.get('quarterly_pnl', [{}])[0].get('fiscalYear','?')} "
        f"{d.get('quarterly_pnl', [{}])[0].get('period','?')})  ·  "
        f"Next ≈ {d.get('next_earnings_est','?')}",
        f"> Source: FMP HTTP REST  ·  Schema {d.get('schema_version','V1.0')}",
        "",
    ]


def render_snapshot(d):
    s = d.get("snapshot") or {}
    return [
        "## 1. Snapshot",
        "",
        f"- **{s.get('companyName','?')}** ({s.get('exchange','?')}) — {s.get('sector','?')} / {s.get('industry','?')}",
        f"- Price: **{fmt_money(s.get('price'))}**  ·  Market Cap: {fmt_money(s.get('marketCap'))}",
        f"- CEO: {s.get('ceo','—')}  ·  Employees: {s.get('fullTimeEmployees','—')}  ·  IPO: {s.get('ipoDate','—')}",
        "",
    ]


def render_pnl(d):
    pnl = d.get("quarterly_pnl") or []
    if not pnl: return []
    margins = (d.get("derived") or {}).get("margins_8q") or []
    margin_by_date = {m["date"]: m for m in margins}

    lines = [
        "## 2. Quarterly P&L Trend (last 8 Q)",
        "",
        "| Q | Period | Revenue | Gross | Op Inc | Net Inc | EPS | GM | OM | NM |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in pnl:
        m = margin_by_date.get(r["date"], {})
        lines.append(
            f"| {r['date']} | {r.get('fiscalYear','?')} {r.get('period','?')} "
            f"| {fmt_money(r.get('revenue'))} "
            f"| {fmt_money(r.get('grossProfit'))} "
            f"| {fmt_money(r.get('operatingIncome'))} "
            f"| {fmt_money(r.get('netIncome'))} "
            f"| ${fmt_num(r.get('epsDiluted') or r.get('eps'))} "
            f"| {fmt_pct_abs(m.get('gross'))} "
            f"| {fmt_pct_abs(m.get('operating'))} "
            f"| {fmt_pct_abs(m.get('net'))} |"
        )

    yoy = (d.get("derived") or {}).get("yoy_growth") or {}
    lines += [
        "",
        f"**YoY**: revenue {fmt_pct(yoy.get('revenue_yoy'))}  ·  "
        f"operating {fmt_pct(yoy.get('operating_yoy'))}  ·  "
        f"earnings {fmt_pct(yoy.get('earnings_yoy'))}",
        f"**QoQ**: revenue {fmt_pct(yoy.get('revenue_qoq'))}  ·  "
        f"acceleration: **{yoy.get('growth_acceleration','?')}**",
        "",
    ]
    return lines


def render_balance(d):
    bs = d.get("balance_sheet") or []
    if not bs: return []
    bh = (d.get("derived") or {}).get("balance_health") or {}
    cur = bs[0]
    lines = [
        "## 3. Balance Sheet Health (latest Q)",
        "",
        f"- Total Assets: **{fmt_money(cur.get('totalAssets'))}**  ·  "
        f"Total Liabilities: {fmt_money(cur.get('totalLiabilities'))}  ·  "
        f"Total Equity: {fmt_money(cur.get('totalEquity'))}",
        f"- Working Capital: **{fmt_money(bh.get('working_capital'))}**  ·  "
        f"Current Ratio: {fmt_num(bh.get('current_ratio'))}",
        f"- Total Debt: {fmt_money(cur.get('totalDebt'))}  ·  "
        f"D/E: **{fmt_num(bh.get('debt_to_equity'))}**  ·  "
        f"Net Cash (cash+ST inv − debt): **{fmt_money(bh.get('net_cash'))}**",
        f"- Cash + ST Investments: {fmt_money((cur.get('cashAndCashEquivalents') or 0) + (cur.get('shortTermInvestments') or 0))}  ·  "
        f"Inventory: {fmt_money(cur.get('inventory'))}  ·  "
        f"Receivables: {fmt_money(cur.get('netReceivables'))}",
        "",
    ]
    return lines


def render_cashflow(d):
    cf = d.get("cash_flow") or []
    if not cf: return []
    cfq = (d.get("derived") or {}).get("cash_flow_quality") or {}
    lines = [
        "## 4. Cash Flow Quality",
        "",
        f"- Latest Q: OpCF {fmt_money(cf[0].get('operatingCashFlow'))}  ·  "
        f"FCF **{fmt_money(cf[0].get('freeCashFlow'))}**  ·  "
        f"CapEx {fmt_money(cf[0].get('capitalExpenditure'))}",
        f"- TTM: OpCF {fmt_money(cfq.get('ocf_ttm'))}  ·  NI {fmt_money(cfq.get('ni_ttm'))}",
        f"- **FCF Margin (latest Q)**: {fmt_pct_abs(cfq.get('fcf_margin'))}  ·  "
        f"**Cash Conversion (TTM OpCF/NI)**: {fmt_num(cfq.get('cash_conversion'))}  ·  "
        f"CapEx Intensity: {fmt_pct_abs(cfq.get('capex_intensity'))}",
        f"- Stock Buybacks (latest Q): {fmt_money(cf[0].get('commonStockRepurchased'))}  ·  "
        f"Dividends: {fmt_money(cf[0].get('commonDividendsPaid'))}",
        f"- SBC (latest Q): {fmt_money(cf[0].get('stockBasedCompensation'))}",
        "",
    ]
    return lines


def render_profitability(d):
    margins = (d.get("derived") or {}).get("margins_8q") or []
    if not margins: return []
    ttm = (d.get("ttm_metrics") or {}).get("from_ratios_ttm") or {}
    km = (d.get("ttm_metrics") or {}).get("from_key_metrics_ttm") or {}
    lines = [
        "## 5. Profitability & Efficiency",
        "",
        "8Q margin trend (newest → oldest):",
        "",
        "| Q | Gross | Operating | Net |",
        "|---|---|---|---|",
    ]
    for m in margins:
        lines.append(f"| {m['date']} {m.get('period','')} | "
                     f"{fmt_pct_abs(m.get('gross'))} | "
                     f"{fmt_pct_abs(m.get('operating'))} | "
                     f"{fmt_pct_abs(m.get('net'))} |")

    lines += [
        "",
        f"**TTM Ratios** — Gross {fmt_pct_abs(ttm.get('grossProfitMarginTTM'))}  ·  "
        f"Operating {fmt_pct_abs(ttm.get('operatingProfitMarginTTM'))}  ·  "
        f"Net {fmt_pct_abs(ttm.get('netProfitMarginTTM'))}  ·  "
        f"EBIT {fmt_pct_abs(ttm.get('ebitMarginTTM'))}",
        f"**Capital Efficiency** — Income Quality TTM: {fmt_num(km.get('incomeQualityTTM'))}  ·  "
        f"FCF Yield: {fmt_pct_abs(km.get('freeCashFlowYieldTTM'))}  ·  "
        f"CapEx/OCF: {fmt_pct_abs(km.get('capexToOperatingCashFlowTTM'))}  ·  "
        f"DSO: {fmt_num(km.get('daysOfSalesOutstandingTTM'), 1)}d",
        "",
    ]
    return lines


def render_growth(d):
    yoy = (d.get("derived") or {}).get("yoy_growth") or {}
    growth = d.get("annual_growth") or []
    lines = [
        "## 6. Growth Trajectory",
        "",
        f"- **Latest YoY**: revenue {fmt_pct(yoy.get('revenue_yoy'))}  ·  "
        f"earnings {fmt_pct(yoy.get('earnings_yoy'))}  ·  "
        f"operating {fmt_pct(yoy.get('operating_yoy'))}",
        f"- Acceleration: **{yoy.get('growth_acceleration','?')}** (vs prior-Q YoY)",
        "",
    ]
    if growth:
        lines.append("Annual growth rates (newest → oldest):")
        lines.append("")
        lines.append("| FY | Revenue | NetIncome | OpIncome | FCF |")
        lines.append("|---|---|---|---|---|")
        for g in growth:
            lines.append(
                f"| {g.get('fiscalYear','?')} "
                f"| {fmt_pct(g.get('revenueGrowth'))} "
                f"| {fmt_pct(g.get('netIncomeGrowth'))} "
                f"| {fmt_pct(g.get('operatingIncomeGrowth'))} "
                f"| {fmt_pct(g.get('freeCashFlowGrowth'))} |"
            )
        lines.append("")
        latest = growth[0]
        lines.append(
            f"**Per-share CAGR** — 3y rev: {fmt_pct(latest.get('threeYRevenueGrowthPerShare'))}  ·  "
            f"5y rev: {fmt_pct(latest.get('fiveYRevenueGrowthPerShare'))}  ·  "
            f"5y NI: {fmt_pct(latest.get('fiveYNetIncomeGrowthPerShare'))}"
        )
        lines.append("")
    return lines


def render_valuation(d):
    val = d.get("valuation") or {}
    snap = d.get("snapshot") or {}
    ttm = (d.get("ttm_metrics") or {}).get("from_ratios_ttm") or {}
    km = (d.get("ttm_metrics") or {}).get("from_key_metrics_ttm") or {}
    rs = val.get("ratings_snapshot") or {}
    lines = [
        "## 7. Valuation",
        "",
        f"- Price: **{fmt_money(snap.get('price'))}**  ·  "
        f"PE TTM: {fmt_num(ttm.get('priceToEarningsRatioTTM'))}  ·  "
        f"PB TTM: {fmt_num(ttm.get('priceToBookRatioTTM'))}",
        f"- EV/EBITDA TTM: {fmt_num(km.get('evToEBITDATTM'))}  ·  "
        f"P/FCF TTM: {fmt_num(ttm.get('priceToFreeCashFlowRatioTTM'))}  ·  "
        f"Net Debt/EBITDA TTM: {fmt_num(km.get('netDebtToEBITDATTM'))}",
        f"- **DCF Intrinsic**: {fmt_money(val.get('dcf_intrinsic'))}  ·  "
        f"Upside vs Price: **{fmt_pct(val.get('dcf_vs_price_pct'))}**",
        f"- FCF Yield TTM: {fmt_pct_abs(km.get('freeCashFlowYieldTTM'))}",
        "",
        f"**Ratings Snapshot** (FMP composite, 1-5):",
        f"- Overall: **{rs.get('rating','?')}** ({rs.get('overallScore','?')}/5)",
        f"- DCF: {rs.get('discountedCashFlowScore','?')}/5  ·  "
        f"PE: {rs.get('priceToEarningsScore','?')}/5  ·  "
        f"PB: {rs.get('priceToBookScore','?')}/5  ·  "
        f"D/E: {rs.get('debtToEquityScore','?')}/5  ·  "
        f"ROE: {rs.get('returnOnEquityScore','?')}/5  ·  "
        f"ROA: {rs.get('returnOnAssetsScore','?')}/5",
        "",
    ]
    return lines


def render_analyst(d):
    val = d.get("valuation") or {}
    grades = d.get("analyst_grades") or []
    snap = d.get("snapshot") or {}
    lines = [
        "## 8. Analyst Consensus",
        "",
        f"- Price: {fmt_money(snap.get('price'))}  →  "
        f"PT consensus **{fmt_money(val.get('price_target_consensus'))}** "
        f"(median {fmt_money(val.get('price_target_median'))}, "
        f"high {fmt_money(val.get('price_target_high'))}, "
        f"low {fmt_money(val.get('price_target_low'))})",
        f"- **PT Upside vs Price**: {fmt_pct(val.get('pt_upside_pct'))}",
        "",
    ]
    if grades:
        lines.append("Monthly grades trend (newest → oldest):")
        lines.append("")
        lines.append("| Date | StrongBuy | Buy | Hold | Sell | StrongSell |")
        lines.append("|---|---|---|---|---|---|")
        for g in grades:
            lines.append(
                f"| {g.get('date','?')} "
                f"| {g.get('analystRatingsStrongBuy','—')} "
                f"| {g.get('analystRatingsBuy','—')} "
                f"| {g.get('analystRatingsHold','—')} "
                f"| {g.get('analystRatingsSell','—')} "
                f"| {g.get('analystRatingsStrongSell','—')} |"
            )
        lines.append("")
    lines.append("> Forward EPS estimate: paid-plan only;use `skills/earnings-valuation-forecaster` 3-method 自算可補(若需)。")
    lines.append("")
    return lines


def render_quality_flags(d):
    flags = d.get("quality_flags") or []
    lines = ["## 9. Quality Flags(deterministic)", ""]
    if not flags:
        lines.append("✅ **No flags raised** — accruals / capex coverage / margins / DSO / FCF / debt 全部乾淨。")
    else:
        flag_desc = {
            "accruals_warning":         "🟡 **Accruals warning** — TTM \\|NI − OpCF\\| / \\|NI\\| > 30%(盈餘品質可疑)",
            "capex_outpaces_ocf":       "🔴 **CapEx outpaces OCF** — 最新 Q OpCF 不夠覆蓋 CapEx(燒錢)",
            "gross_margin_compression": "🟠 **Gross margin compression** — 最新 4 季毛利率連續下滑",
            "dso_slowdown":             "🟠 **DSO slowdown** — 應收帳款天數連 4 季上升(收款放緩)",
            "negative_fcf":             "🔴 **Negative FCF** — 最新 Q 自由現金流為負",
            "debt_buildup":             "🟠 **Debt buildup** — 總債務環比連 2 季 > 15%",
        }
        for f in flags:
            lines.append(f"- {flag_desc.get(f, f)}")
    lines.append("")
    return lines


def render_bottom_line(d):
    sc = d.get("score_components") or {}
    composite = d.get("composite_score", 0)
    verdict = d.get("verdict", "—")

    verdict_emoji = {
        "STRONG":         "🟢",
        "SOLID":          "🟢",
        "MIXED":          "🟡",
        "WEAK":           "🟠",
        "DETERIORATING":  "🔴",
    }.get(verdict, "❓")

    return [
        "## 10. Bottom Line",
        "",
        f"### {verdict_emoji} **{verdict}** — Composite Score: **{composite}/100**",
        "",
        "| 元件 | 分數 | 滿分 |",
        "|---|---|---|",
        f"| Quality | {sc.get('quality',0)} | 30 |",
        f"| Growth | {sc.get('growth',0)} | 30 |",
        f"| Valuation | {sc.get('valuation',0)} | 25 |",
        f"| Analyst | {sc.get('analyst',0)} | 15 |",
        f"| **Total** | **{composite}** | **100** |",
        "",
        f"> Verdict 對照: 80+ STRONG / 65+ SOLID / 50+ MIXED / 35+ WEAK / <35 DETERIORATING",
        "",
        "---",
        "",
        f"> Generated by `skills/earnings-analyst` from FMP HTTP REST."
        f"  Cache: `skills/earnings-analyst/cache/{d['ticker']}_{d['last_earnings_date']}.json`",
        "",
    ]


def render(d):
    blocks = [
        render_header(d),
        render_snapshot(d),
        render_pnl(d),
        render_balance(d),
        render_cashflow(d),
        render_profitability(d),
        render_growth(d),
        render_valuation(d),
        render_analyst(d),
        render_quality_flags(d),
        render_bottom_line(d),
    ]
    return "\n".join("\n".join(b) for b in blocks if b)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker", nargs="?")
    ap.add_argument("--json", help="explicit cache path")
    ap.add_argument("--out",  help="explicit output md path")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    if args.json:
        path = args.json
    else:
        if not args.ticker:
            sys.exit("Usage: render.py <TICKER>  (or --json <path>)")
        path = find_cache(args.ticker.upper())
        if not path:
            sys.exit(f"[ERROR] no cache for {args.ticker} — run fetch.py + analyze.py first")

    with open(path) as f:
        d = json.load(f)

    if "composite_score" not in d:
        sys.exit(f"[ERROR] cache not analyzed yet — run analyze.py first")

    md = render(d)

    if args.stdout:
        sys.stdout.write(md)
        return 0

    out = args.out or os.path.join(REPORTS_DIR, f"{date.today().isoformat()}_{d['ticker']}_earnings.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(md)

    print(f"[render] wrote {os.path.relpath(out, BASE_DIR)} "
          f"({len(md):,} bytes, {len(md.splitlines())} lines)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

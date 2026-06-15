#!/usr/bin/env python3
"""compose.py — Deterministic fact_pack → IC Memo Markdown renderer.

V1.0.0: ZERO LLM calls. Pure data → table → MD rendering.
Future V1.1+ may add --llm-polish (stub raises NotImplementedError).

Usage:
  python3 compose.py CRWD                       # uses latest fact_pack in cache
  python3 compose.py --fact-pack <path>         # explicit fact_pack
  python3 compose.py CRWD --output-dir reports/

Exit codes:
  0  ok
  1  fact_pack not found
  2  fact_pack schema mismatch
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

EXPECTED_SCHEMA = "1.0"


def fmt_money(v, *, default="—"):
    if v is None:
        return default
    try:
        v = float(v)
    except (TypeError, ValueError):
        return default
    if abs(v) >= 1e12:
        return f"${v/1e12:.2f}T"
    if abs(v) >= 1e9:
        return f"${v/1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.1f}M"
    return f"${v:,.2f}"


def fmt_price_range(v, *, default="—"):
    if v is None:
        return default
    if isinstance(v, (list, tuple)):
        vals = [x for x in v if x is not None]
        if len(vals) >= 2:
            return f"{fmt_money(vals[0])} - {fmt_money(vals[1])}"
        if len(vals) == 1:
            return fmt_money(vals[0])
        return default
    if isinstance(v, dict):
        low = v.get("low") or v.get("min") or v.get("from")
        high = v.get("high") or v.get("max") or v.get("to")
        if low is None and "range" in v:
            return fmt_price_range(v.get("range"), default=default)
        if low is not None and high is not None:
            return f"{fmt_money(low)} - {fmt_money(high)}"
        return fmt_money(low if low is not None else high, default=default)
    return fmt_money(v, default=default)


def fmt_num(v, *, default="—", pct=False, places=2):
    if v is None:
        return default
    try:
        v = float(v)
    except (TypeError, ValueError):
        return default
    s = f"{v:,.{places}f}"
    return s + "%" if pct else s


def fmt_share(v):
    if v is None:
        return "—"
    try:
        return f"{float(v) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _safe_float(v):
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def md_table(headers: list, rows: list) -> str:
    if not rows:
        return "_(no data)_"
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) if c is not None else "—" for c in r) + " |")
    return "\n".join(out)


def _segment_keys(entry: dict) -> set[str]:
    return set((entry.get("products") or {}).keys())


def _jaccard_distance(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return 1.0 - (len(a & b) / max(1, len(a | b)))


def _render_product_segment_table(entries: list[dict], product_keys: list[str] | None = None) -> str:
    if not entries:
        return "_(no data)_"
    keys = product_keys or sorted({k for entry in entries for k in (entry.get("products") or {}).keys()})
    rows = []
    for entry in entries:
        row = [entry.get("date") or entry.get("fiscal_year") or "—"]
        total = sum((entry.get("products") or {}).values()) or 1
        for pk in keys:
            val = (entry.get("products") or {}).get(pk)
            if val is None:
                row.append("—")
            else:
                row.append(f"${val/1e9:.2f}B ({val/total*100:.0f}%)")
        rows.append(row)
    return md_table(["FY"] + keys, rows)


def _split_segment_discontinuity(prod: list[dict]) -> tuple[list[dict], list[dict], bool]:
    if len(prod) < 2:
        return prod, [], False
    first_keys = _segment_keys(prod[0])
    legacy: list[dict] = []
    current: list[dict] = []
    discontinuity = False
    for entry in prod:
        dist = _jaccard_distance(first_keys, _segment_keys(entry))
        if dist >= 0.7:
            discontinuity = True
            legacy.append(entry)
        else:
            current.append(entry)
    if not discontinuity or not current or not legacy:
        return prod, [], False
    return current, legacy, True


def _render_pct(v):
    num = _safe_float(v)
    if num is None:
        return "—"
    return f"{num * 100:.1f}%"


def _render_structural_shift(ss: dict) -> str:
    tier = ss.get("tier") or "—"
    signals = ss.get("signals") or {}
    active = [k for k, v in signals.items() if v]
    metrics = ss.get("metrics") or {}
    gm_z = _safe_float(metrics.get("gm_z_score"))
    bits = [
        f"tier={tier}",
        "signals=" + (", ".join(active) if active else "—"),
    ]
    if gm_z is not None:
        bits.append(f"gm_z={gm_z:.2f}")
    if metrics.get("eps_qoq") is not None:
        bits.append(f"eps_qoq={_render_pct(metrics.get('eps_qoq'))}")
    if metrics.get("rev_yoy") is not None:
        bits.append(f"rev_yoy={_render_pct(metrics.get('rev_yoy'))}")
    return "; ".join(bits)


def render_sec_1(f1: dict, f12: dict) -> str:
    """§1 一頁摘要"""
    rows = [
        ("Final Action", f"**{f1.get('final_action') or '—'}**"),
        ("Confidence", f"{fmt_num(f1.get('decision_confidence_pct'), places=0)}%"),
        ("Position Size", f"{fmt_num(f1.get('position_size_pct'), places=2)}%"),
        ("Entry (aggr / cons)", f"{fmt_price_range(f1.get('entry_aggressive'))} / {fmt_price_range(f1.get('entry_conservative'))}"),
        ("Stop Loss", fmt_money(f1.get("stop_loss"))),
        ("Take Profit", fmt_money(f1.get("take_profit"))),
        ("Risk/Reward", f"{fmt_num(f1.get('risk_reward_ratio'))}x" if f1.get("risk_reward_ratio") else "—"),
        ("Time Horizon", f1.get("time_horizon") or "—"),
        ("Fragility", f1.get("fragility_label") or "—"),
    ]
    return "## §1 一頁摘要\n\n" + md_table(["Field", "Value"], rows) + "\n\n<!-- src: protocol.history.phase5 -->"


def render_sec_2(f2: dict) -> str:
    desc = (f2.get("description") or "").strip()
    if not desc:
        desc = "_(profile description unavailable)_"
    meta = (
        f"- **CEO**: {f2.get('ceo') or '—'}\n"
        f"- **Employees**: {fmt_num(f2.get('full_time_employees'), places=0)}\n"
        f"- **IPO**: {f2.get('ipo_date') or '—'}\n"
        f"- **HQ**: {f2.get('city') or '—'}, {f2.get('state') or '—'}, {f2.get('country') or '—'}\n"
        f"- **Website**: {f2.get('website') or '—'}\n"
    )
    return "## §2 公司與商業模式\n\n" + desc + "\n\n" + meta + "\n<!-- src: profile.live -->"


def render_sec_3(f3: dict) -> str:
    if f3.get("_stub"):
        return (
            "## §3 收入結構與成長驅動\n\n"
            "_(資料待補：跑 `財報 <TICKER>` 補 earnings-analyst cache)_\n\n"
            "<!-- src: earnings_analyst.cache (MISSING) -->"
        )

    parts = ["## §3 收入結構與成長驅動", ""]

    # Product segments
    prod = f3.get("product_fy") or []
    if prod:
        parts.append("### Product Segment (FY trend)")
        parts.append("")
        current, legacy, split = _split_segment_discontinuity(prod[:5])
        if split:
            current_year = current[0].get("fiscal_year") or current[0].get("date") or "latest"
            legacy_year = legacy[0].get("fiscal_year") or legacy[0].get("date") or "prior"
            parts.append(f"### Current Structure (FY{current_year}+)")
            parts.append("")
            parts.append(_render_product_segment_table(current))
            parts.append("")
            parts.append(f"### Legacy Segments (FY{legacy_year} and prior)")
            parts.append("")
            parts.append(_render_product_segment_table(legacy))
            parts.append("")
            parts.append("- **Note**: Segment presentation changed across fiscal years; current and legacy structures are shown separately to avoid sparse crosswalk columns.")
        else:
            parts.append(_render_product_segment_table(prod[:5]))
        parts.append("")

    # Geographic segments
    geo = f3.get("geographic_fy") or []
    if geo:
        parts.append("### Geographic Segment (FY trend)")
        parts.append("")
        region_keys = sorted({k for entry in geo for k in (entry.get("regions") or {}).keys()})
        rows = []
        for entry in geo[:5]:
            row = [entry.get("date") or entry.get("fiscal_year") or "—"]
            total = sum((entry.get("regions") or {}).values()) or 1
            for rk in region_keys:
                val = (entry.get("regions") or {}).get(rk)
                if val is None:
                    row.append("—")
                else:
                    row.append(f"${val/1e9:.2f}B ({val/total*100:.0f}%)")
            rows.append(row)
        parts.append(md_table(["FY"] + region_keys, rows))
        parts.append("")

    # Business mix overlay
    overlay = f3.get("business_mix_overlay") or {}
    if overlay:
        parts.append("### Business Mix Shift")
        parts.append("")
        ns = overlay.get("new_segment") or {}
        parts.append(f"- **Tier**: {overlay.get('tier') or '—'}")
        parts.append(f"- **New segment**: {ns.get('name') or '—'} (share {fmt_share(ns.get('share_of_revenue'))}, YoY {fmt_share(ns.get('yoy_growth'))})")
        if overlay.get("data_quality_note"):
            parts.append(f"- **Note**: {overlay.get('data_quality_note')}")
        parts.append("")

    parts.append("<!-- src: earnings_analyst.cache -->")
    return "\n".join(parts)


def render_sec_4(f4: dict) -> str:
    parts = ["## §4 客戶 / 供應商 / 競爭格局", ""]

    # Moat
    parts.append("### Moat")
    parts.append("")
    parts.append(f"- **Level**: {f4.get('moat_level') or '—'}")
    parts.append(f"- **Type**: {f4.get('moat_type') or '—'}")
    parts.append(f"- **Evidence**: {f4.get('moat_evidence') or '—'}")
    parts.append("")

    # Peers
    parts.append("### Peers Comparison")
    parts.append("")
    peers = f4.get("peers") or []
    descriptor = (f4.get("peer_descriptor") or {}).get("peers") or {}
    if peers:
        rows = []
        for p in peers[:10]:
            if isinstance(p, dict):
                ticker = p.get("ticker") or "—"
                name = p.get("name") or ticker
                rows.append([ticker, name, p.get("role") or "—"])
            else:
                desc = descriptor.get(p) or {}
                rows.append([
                    p,
                    desc.get("focus_area") or "—",
                    desc.get("market_share_note") or "—",
                ])
        if any(isinstance(p, dict) for p in peers):
            parts.append(md_table(["Ticker", "Name", "Role"], rows))
        else:
            parts.append(md_table(["Ticker", "Focus Area", "Market Share Note"], rows))
        parts.append("")
        descriptor_status = (f4.get("peer_descriptor") or {}).get("status")
        if descriptor_status == "stub_no_llm" and not any(isinstance(p, dict) for p in peers):
            parts.append("> _Focus Area / Market Share descriptor 為 V1.0 stub。Phase A.5 將以 Haiku 4.5 batch call 補。_")
            parts.append("")
    else:
        parts.append("_(peers list unavailable)_")
        parts.append("")

    src = "peers.local_roster" if f4.get("peer_source") == "local_roster" else "peers.live_fmp"
    parts.append(f"<!-- src: {src} + llm_synth.peer_descriptor (stub) -->")
    return "\n".join(parts)


def render_sec_5(f5: dict) -> str:
    if f5.get("_stub"):
        return (
            "## §5 最新財務與申報重點\n\n"
            "_(資料待補：跑 `財報 <TICKER>`)_\n\n"
            "<!-- src: earnings_analyst.cache (MISSING) -->"
        )
    parts = ["## §5 最新財務與申報重點", ""]
    qpnl = f5.get("quarterly_pnl") or []
    if qpnl:
        parts.append("### Latest Quarter")
        parts.append("")
        rows = []
        for q in qpnl[:1]:
            rows.append([
                q.get("date") or "—",
                fmt_money(q.get("revenue")),
                fmt_money(q.get("operatingIncome") or q.get("operating_income")),
                fmt_money(q.get("netIncome") or q.get("net_income")),
                fmt_num(q.get("eps")),
            ])
        parts.append(md_table(["Date", "Revenue", "Op Income", "Net Income", "EPS"], rows))
        parts.append("")
    ttm = f5.get("ttm_metrics") or {}
    if ttm:
        parts.append("### TTM Metrics")
        parts.append("")
        rows = [
            ("Revenue TTM", fmt_money(ttm.get("revenue_ttm") or ttm.get("revenue"))),
            ("Gross Margin", fmt_share(ttm.get("gross_margin"))),
            ("Operating Margin", fmt_share(ttm.get("operating_margin"))),
            ("FCF TTM", fmt_money(ttm.get("fcf_ttm") or ttm.get("fcf"))),
            ("Net Income TTM", fmt_money(ttm.get("net_income_ttm") or ttm.get("net_income"))),
        ]
        parts.append(md_table(["Metric", "Value"], rows))
        parts.append("")
    surprises = f5.get("earnings_surprises") or []
    if surprises:
        parts.append("### Earnings Surprises (recent)")
        parts.append("")
        rows = []
        for s in surprises[:4]:
            rows.append([
                s.get("date") or "—",
                fmt_num(s.get("epsActual") or s.get("eps_actual")),
                fmt_num(s.get("epsEstimated") or s.get("eps_estimated")),
                fmt_num(s.get("surprise_pct") or s.get("surprisePercentage"), places=1) + "%" if (s.get("surprise_pct") or s.get("surprisePercentage")) is not None else "—",
            ])
        parts.append(md_table(["Date", "EPS Actual", "EPS Est", "Surprise %"], rows))
        parts.append("")
    parts.append("<!-- src: earnings_analyst.cache -->")
    return "\n".join(parts)


def render_sec_6(f6: dict) -> str:
    if f6.get("_stub"):
        return "## §6 資產負債表與現金流品質\n\n_(資料待補：跑 `財報 <TICKER>`)_\n\n<!-- src: earnings_analyst.cache (MISSING) -->"
    parts = ["## §6 資產負債表與現金流品質", ""]
    bs = (f6.get("balance_sheet") or [])
    if bs:
        b = bs[0]
        parts.append("### Balance Sheet (latest)")
        parts.append("")
        rows = [
            ("Cash & ST Investments", fmt_money(b.get("cash_and_st_investments") or b.get("cashAndShortTermInvestments") or b.get("cash"))),
            ("Total Debt", fmt_money(b.get("totalDebt") or b.get("total_debt"))),
            ("Stockholders Equity", fmt_money(b.get("total_stockholders_equity") or b.get("totalStockholdersEquity") or b.get("stockholders_equity") or b.get("totalEquity"))),
            ("Retained Earnings", fmt_money(b.get("retainedEarnings") or b.get("retained_earnings"))),
        ]
        parts.append(md_table(["Metric", "Value"], rows))
        parts.append("")
    parts.append("### Cash Flow Quality")
    parts.append("")
    parts.append(f"- **Cash conversion**: {f6.get('cash_conversion_quality') or '—'}")
    # quality_flags: earnings-analyst writes list[str]; older caches had dict — handle both
    qf = f6.get("quality_flags") or {}
    if isinstance(qf, list):
        if qf:
            parts.append(f"- **Quality flags**: {', '.join(str(x) for x in qf[:6])}")
    elif isinstance(qf, dict) and qf:
        parts.append(f"- **Quality flags**: {', '.join(f'{k}={v}' for k, v in list(qf.items())[:6])}")
    parts.append("")
    parts.append("<!-- src: earnings_analyst.cache -->")
    return "\n".join(parts)


def render_sec_7(f7: dict) -> str:
    if f7.get("_stub"):
        return "## §7 盈利能力與 2-3 年模型\n\n_(資料待補：跑 `財報 <TICKER>`)_\n\n<!-- src: earnings_analyst.cache (MISSING) -->"
    parts = ["## §7 盈利能力與 2-3 年模型", ""]
    ag = f7.get("annual_growth")
    # annual_growth is a list of per-FY dicts in earnings-analyst cache
    if isinstance(ag, list) and ag:
        parts.append("### Annual Growth (last 5 FY)")
        parts.append("")
        rows = []
        for entry in ag[:5]:
            rows.append([
                entry.get("date") or entry.get("fiscalYear") or "—",
                fmt_share(entry.get("revenueGrowth")),
                fmt_share(entry.get("grossProfitGrowth")),
                fmt_share(entry.get("operatingIncomeGrowth")),
                fmt_share(entry.get("netIncomeGrowth")),
                fmt_share(entry.get("freeCashFlowGrowth")),
            ])
        parts.append(md_table(["FY", "Rev YoY", "GP YoY", "OpInc YoY", "NI YoY", "FCF YoY"], rows))
        parts.append("")
    elif isinstance(ag, dict) and ag:
        parts.append("### Annual Growth")
        parts.append("")
        rows = [[k, fmt_share(v) if isinstance(v, (int, float)) else str(v)] for k, v in list(ag.items())[:8]]
        parts.append(md_table(["Metric", "Value"], rows))
        parts.append("")
    parts.append(f"- **Transition signature**: {f7.get('transition_signature') or '—'}")
    ss = f7.get("structural_shift") or {}
    if ss:
        parts.append(f"- **Structural shift**: {_render_structural_shift(ss)}")
    ae = f7.get("annual_estimates") or []
    if ae:
        parts.append("")
        parts.append("### Forward Estimates")
        parts.append("")
        rows = []
        for e in ae[:3]:
            rows.append([
                e.get("date") or e.get("fiscalYear") or "—",
                fmt_money(e.get("revenue_estimate") or e.get("revenue_avg") or e.get("revenueAvg")),
                fmt_num(e.get("eps_estimate") or e.get("eps_avg") or e.get("epsAvg")),
            ])
        parts.append(md_table(["Period", "Revenue Est", "EPS Est"], rows))
        parts.append("")
    parts.append("<!-- src: earnings_analyst.cache -->")
    return "\n".join(parts)


def render_sec_8(f8: dict) -> str:
    parts = ["## §8 估值：DCF + Multiples + Analyst PT", ""]
    fv = f8.get("fair_value_summary") or {}
    parts.append("### Fair Value 6-Anchor Blend")
    parts.append("")
    anchors = fv.get("anchors") or {}
    weights = fv.get("weights_used") or {}
    rows = []
    for anchor_name in ("dcf_unlevered", "dcf_levered", "analyst_pt_consensus",
                        "peer_pe_implied", "owner_earnings_mult", "forecaster_blend"):
        a = anchors.get(anchor_name)
        w = weights.get(anchor_name)
        rows.append([
            anchor_name,
            fmt_money(a),
            fmt_share(w) if w is not None else "—",
        ])
    parts.append(md_table(["Anchor", "Value", "Weight"], rows))
    parts.append("")
    parts.append(f"- **Weighted FV**: {fmt_money(fv.get('weighted_fair_value'))}")
    sec_1 = f8.get("_sec_1") or {}
    live_spot = sec_1.get("live_spot") or sec_1.get("current_price")
    fv_live_pct = sec_1.get("fv_vs_live_pct")
    parts.append(f"- **Analysis Price**: {fmt_money(fv.get('current_price'))}")
    parts.append(f"- **vs Analysis Price**: {fmt_num(fv.get('vs_current_pct'), places=2)}% ({fv.get('verdict_band') or '—'})")
    if live_spot is not None:
        parts.append(f"- **Live Spot**: {fmt_money(live_spot)}")
        parts.append(f"- **vs Live Spot**: {fmt_num(fv_live_pct, places=2)}%")
    parts.append(f"- **Confidence**: {fv.get('confidence') or '—'} ({fv.get('anchors_available') or 0}/6 anchors)")
    if fv.get("methodology_note"):
        parts.append(f"- **Methodology**: {fv.get('methodology_note')}")
    parts.append("")

    # V3.49.0 — anchor 分布區間（V3.45.1+；舊 entry 缺 → 整段略過）
    fvr = f8.get("fair_value_range") or {}
    if fvr.get("p50") is not None:
        parts.append("### Fair Value Range（anchor 分布，advisory）")
        parts.append("")
        parts.append(f"- **P25 / P50 / P75**: {fmt_money(fvr.get('p25'))} / "
                     f"{fmt_money(fvr.get('p50'))} / {fmt_money(fvr.get('p75'))}"
                     f"（min {fmt_money(fvr.get('min_anchor'))} – max {fmt_money(fvr.get('max_anchor'))}）")
        parts.append(f"- **Range verdict**: {fvr.get('range_verdict') or '—'}；"
                     f"**錨一致度**: {fvr.get('agreement_grade') or '—'}"
                     f"（CV {fmt_num(fvr.get('anchor_dispersion_cv'), places=3)}）")
        parts.append("")

    # V3.49.0 — reverse DCF 隱含預期（V3.45.1+）
    ie = f8.get("implied_expectations") or {}
    if ie.get("implied_5y_fcf_cagr") is not None:
        pct = ie["implied_5y_fcf_cagr"] * 100
        oor = "（⚠ 解超出 clamp 邊界）" if ie.get("implied_out_of_range") else ""
        parts.append("### Reverse DCF — 現價隱含預期")
        parts.append("")
        parts.append(f"- **隱含 5Y FCF CAGR**: {pct:.0f}%{oor}")
        if ie.get("sanity_note"):
            parts.append(f"- {ie['sanity_note']}")
        parts.append("")

    # V3.49.0 — Multi-Horizon 三框（V5.1+）
    mh = f8.get("multi_horizon") or {}
    st, mt, cv = mh.get("short_term_5d") or {}, mh.get("mid_term_60d") or {}, mh.get("convergence") or {}
    if st.get("band_capped"):
        b = st["band_capped"]
        parts.append("### Multi-Horizon 三時間框架")
        parts.append("")
        parts.append(f"- **5 日帶**: {fmt_money(b[0])} / {fmt_money(b[1])} / {fmt_money(b[2])}"
                     f"（conf {st.get('confidence') or '—'}）")
        if mt.get("mid_target") is not None:
            parts.append(f"- **60 日 target**: {fmt_money(mt.get('mid_target'))}"
                         f"（{mt.get('reality_check_note') or ''}）")
        if cv.get("mhp_signal"):
            parts.append(f"- **收斂訊號**: `{cv['mhp_signal']}` — {cv.get('signal_note') or ''}")
        parts.append("")

    # V3.49.0 — archetype shadow（V3.46.0+；shadow-only 標示）
    ash = f8.get("archetype_shadow") or {}
    if ash.get("archetype") and ash.get("archetype") != "balanced":
        flip = "⚠ **與 live verdict 不同**" if ash.get("flip_vs_live") else "與 live 一致"
        parts.append(f"> Archetype shadow（僅觀察，不影響決策）：`{ash['archetype']}` 權重下 "
                     f"FV {fmt_money(ash.get('weighted_fair_value_shadow'))} "
                     f"（{ash.get('verdict_band_shadow') or '—'}，{flip}）")
        parts.append("")

    pt_news = f8.get("pt_news") or []
    if pt_news:
        parts.append("### Individual Analyst PT")
        parts.append("")
        rows = []
        for p in pt_news[:8]:
            rows.append([
                p.get("publishedDate", "")[:10] or "—",
                p.get("analystCompany") or "—",
                fmt_money(p.get("priceTarget") or p.get("adjPriceTarget")),
            ])
        parts.append(md_table(["Date", "Analyst", "PT"], rows))
        parts.append("")

    parts.append("<!-- src: protocol.history.phase4_5 + earnings_analyst.cache.valuation -->")
    return "\n".join(parts)


def render_sec_9(f9: dict) -> str:
    parts = ["## §9 催化劑與風險", ""]
    cats = f9.get("near_term_catalysts") or []
    if cats:
        parts.append("### Catalysts")
        parts.append("")
        rows = []
        for c in cats[:8]:
            rows.append([
                c.get("date") or "—",
                c.get("type") or "—",
                c.get("impact") or "—",
                (c.get("description") or "")[:120],
            ])
        parts.append(md_table(["Date", "Type", "Impact", "Description"], rows))
        parts.append("")
    spill = f9.get("cross_asset_spillover") or []
    if spill:
        parts.append("### Cross-Asset Spillover")
        parts.append("")
        rows = []
        for s in spill[:6]:
            rows.append([
                s.get("asset") or "—",
                s.get("direction") or "—",
                (s.get("mechanism") or "")[:100],
            ])
        parts.append(md_table(["Asset", "Direction", "Mechanism"], rows))
        parts.append("")
    risks = f9.get("key_risks") or []
    if risks:
        parts.append("### Key Risks")
        parts.append("")
        for r in risks[:10]:
            parts.append(f"- {r}")
        parts.append("")
    dpd = f9.get("decision_point_days")
    if dpd is not None:
        parts.append(f"**Days to next binary**: {dpd}d")
        parts.append("")
    parts.append("<!-- src: protocol.history.phase2 -->")
    return "\n".join(parts)


def _fmt_odds(v) -> str:
    if v is None:
        return "—"
    s = str(v).strip()
    return s if s.endswith("%") or s == "—" else f"{s}%"


def render_sec_10(f10: dict) -> str:
    parts = ["## §10 Bull / Bear / Base case", ""]
    so = f10.get("scenario_odds")
    so = so if isinstance(so, dict) else {}
    parts.append("### Scenario Odds")
    parts.append("")
    parts.append(md_table(
        ["Scenario", "Odds"],
        [["Bull", _fmt_odds(so.get("bull"))], ["Base", _fmt_odds(so.get("base"))], ["Bear", _fmt_odds(so.get("bear"))]],
    ))
    parts.append("")
    rt = f10.get("red_team_counter_thesis") or ""
    if rt:
        parts.append("### Red Team Counter Thesis")
        parts.append("")
        parts.append(rt)
        parts.append("")
    kc = f10.get("red_team_kill_conditions") or []
    if kc:
        parts.append("### Kill Conditions")
        parts.append("")
        for c in kc[:8]:
            parts.append(f"- {c}")
        parts.append("")
    parts.append("<!-- src: protocol.history.red_team -->")
    return "\n".join(parts)


def render_sec_11(f11: dict) -> str:
    """§11 — verbatim 自 protocol.history.phase5。

    decision_lock 保護：此 section 的所有 verbatim 欄位必須與 fact_pack._protocol_decision_lock.payload 完全一致。
    """
    parts = ["## §11 委員會結論", ""]
    parts.append("> _此章節 verbatim 來自 protocol.history.phase5，受 decision_lock hash 保護。_")
    parts.append("")
    parts.append("### 當下動作")
    parts.append("")
    parts.append(f"**{f11.get('final_action') or '—'}** — {f11.get('final_decision') or '—'}")
    parts.append("")
    parts.append("### 進場計畫")
    parts.append("")
    parts.append(f"- Entry (aggressive): {fmt_price_range(f11.get('entry_aggressive'))}")
    parts.append(f"- Entry (conservative): {fmt_price_range(f11.get('entry_conservative'))}")
    parts.append(f"- Stop Loss: {fmt_money(f11.get('stop_loss'))}")
    parts.append(f"- Take Profit: {fmt_money(f11.get('take_profit'))}")
    parts.append(f"- Position Size: {fmt_num(f11.get('position_size_pct'), places=2)}% ({f11.get('position_size_method') or '—'})")
    parts.append(f"- Staged Split: {f11.get('staged_split') or '—'}")
    parts.append("")
    # watch_conditions is LLM-written + lock-protected (data stays verbatim);
    # only the DISPLAY tolerates dict/list/str shape drift here.
    wc = f11.get("watch_conditions") or {}
    if wc:
        parts.append("### Watch / Re-eval 條件")
        parts.append("")
        if isinstance(wc, dict):
            rows = [[k, v] for k, v in wc.items()]
        elif isinstance(wc, list):
            rows = [[str(x), ""] for x in wc]
        else:
            rows = [[str(wc), ""]]
        parts.append(md_table(["Trigger", "Metric"], rows))
        parts.append("")
    parts.append("<!-- src: protocol.history.phase5 (decision-locked) -->")
    return "\n".join(parts)


def render_sec_12(f12: dict, fact_pack: dict, validator_rc: int | None = None) -> str:
    parts = ["## §12 附錄", ""]
    ls = f12.get("lane_scores") or {}
    if ls:
        parts.append("### Lane Scores")
        parts.append("")
        rows = [[k, str(v)] for k, v in ls.items()]
        parts.append(md_table(["Lane", "Score"], rows))
        parts.append(f"- Decision confidence: {fmt_num(f12.get('decision_confidence_pct'), places=0)}%")
        parts.append("")

    parts.append("### Provenance Roster")
    parts.append("")
    prov = f12.get("provenance") or {}
    rows = []
    for sec_name, info in prov.items():
        path = info.get("path") or "—"
        meta_bits = []
        if "stale_days" in info and info["stale_days"] is not None:
            meta_bits.append(f"stale {info['stale_days']}d")
        if "session_date" in info and info["session_date"]:
            meta_bits.append(f"session {info['session_date']}")
        if "status" in info and info["status"]:
            meta_bits.append(info["status"])
        if "count" in info:
            meta_bits.append(f"n={info['count']}")
        rows.append([sec_name, info.get("type") or "—", path, ", ".join(meta_bits) or "—"])
    parts.append(md_table(["Source", "Type", "Path", "Meta"], rows))
    parts.append("")

    deg = f12.get("degraded_sections") or []
    parts.append("### Degraded Sections")
    parts.append("")
    if deg:
        for d in deg:
            parts.append(f"- {d}")
    else:
        parts.append("_(none)_")
    parts.append("")

    parts.append("### Validator")
    parts.append("")
    if validator_rc is None:
        parts.append("- rc: _(not yet run; see compose --validate or run validate_ic_memo.py)_")
    else:
        parts.append(f"- rc: {validator_rc}")
    lock = fact_pack.get("_protocol_decision_lock") or {}
    parts.append(f"- decision_lock_hash: `{lock.get('hash', '—')[:24]}...`")
    parts.append(f"- fact_pack_hash: `{fact_pack.get('fact_pack_hash', '—')[:24]}...`")
    parts.append("")
    parts.append("<!-- src: meta.composed -->")
    return "\n".join(parts)


def render_header(fact_pack: dict) -> str:
    facts = fact_pack["facts"]
    f1 = facts["sec_1"]
    f2 = facts["sec_2"]
    rng = (f1.get("range") or "").split("-")
    low = rng[0].strip() if len(rng) > 0 else "—"
    high = rng[1].strip() if len(rng) > 1 else "—"
    sess_date = ((fact_pack.get("sources") or {}).get("protocol_history") or {}).get("session_date") or "—"
    analysis_price = f1.get("analysis_price")
    live_spot = f1.get("live_spot") or f1.get("current_price")
    fv_vs_analysis = f1.get("fv_vs_analysis_pct") if f1.get("fv_vs_analysis_pct") is not None else f1.get("fv_vs_current_pct")
    fv_vs_live = f1.get("fv_vs_live_pct")
    return (
        f"# {f1.get('ticker')} ({f1.get('company_name')}) — IC Memo\n\n"
        f"- **Date**: {fact_pack.get('as_of')}\n"
        f"- **Live Spot**: {fmt_money(live_spot)} | 52w: ${low} – ${high}\n"
        f"- **Analysis Price**: {fmt_money(analysis_price)} (protocol session {sess_date})\n"
        f"- **Market Cap**: {fmt_money(f1.get('market_cap'))}\n"
        f"- **Sector / Industry**: {f1.get('sector') or '—'} / {f1.get('industry') or '—'}\n"
        f"- **Final Action**: **{f1.get('final_action') or '—'}** | Verdict: {f1.get('verdict_band') or '—'} | "
        f"FV {fmt_money(f1.get('weighted_fair_value'))} "
        f"({fmt_num(fv_vs_analysis, places=2)}% vs analysis; {fmt_num(fv_vs_live, places=2)}% vs live)\n"
        f"- **Source**: investment_protocol V5.0 session {sess_date} | Memo composer V1.0.0\n\n"
        "<!-- src: profile.live + protocol.history.phase5 -->"
    )


def compose(fact_pack: dict, *, validator_rc: int | None = None, llm_polish: bool = False) -> str:
    if llm_polish:
        raise NotImplementedError("--llm-polish reserved for V1.1+. Deterministic-only in V1.0.")
    if fact_pack.get("schema_version") != EXPECTED_SCHEMA:
        raise ValueError(
            f"fact_pack schema_version mismatch: expected {EXPECTED_SCHEMA}, got {fact_pack.get('schema_version')}"
        )

    facts = fact_pack["facts"]
    sec_8 = dict(facts["sec_8"])
    sec_8["_sec_1"] = facts["sec_1"]
    sections = [
        render_header(fact_pack),
        render_sec_1(facts["sec_1"], facts["sec_12"]),
        render_sec_2(facts["sec_2"]),
        render_sec_3(facts["sec_3"]),
        render_sec_4(facts["sec_4"]),
        render_sec_5(facts["sec_5"]),
        render_sec_6(facts["sec_6"]),
        render_sec_7(facts["sec_7"]),
        render_sec_8(sec_8),
        render_sec_9(facts["sec_9"]),
        render_sec_10(facts["sec_10"]),
        render_sec_11(facts["sec_11"]),
        render_sec_12(facts["sec_12"], fact_pack, validator_rc=validator_rc),
    ]
    body = "\n\n---\n\n".join(sections)
    footer = (
        f"\n\n---\n\n*Composed by ic-memo-writer V1.0.0 (deterministic, 0 LLM call) — "
        f"fact_pack hash {fact_pack.get('fact_pack_hash', '—')[:16]}...*\n"
    )
    return body + footer


def locate_latest_fact_pack(ticker: str) -> Path | None:
    pat = str(CACHE_DIR / f"{ticker}_*_fact_pack.json")
    files = sorted(glob.glob(pat))
    return Path(files[-1]) if files else None


def main():
    ap = argparse.ArgumentParser(description="Deterministic IC Memo composer.")
    ap.add_argument("ticker", nargs="?", help="Ticker (auto-locates latest fact_pack)")
    ap.add_argument("--fact-pack", type=Path, help="Explicit fact_pack JSON path")
    ap.add_argument("--output-dir", type=Path, default=ROOT / "reports", help="Output dir (default: reports/)")
    ap.add_argument("--llm-polish", action="store_true", help="Reserved for V1.1+ (raises NotImplementedError)")
    args = ap.parse_args()

    if args.fact_pack:
        fp_path = args.fact_pack
    elif args.ticker:
        fp_path = locate_latest_fact_pack(args.ticker.upper())
        if fp_path is None:
            print(f"[ic-memo] fact_pack not found for {args.ticker}. Run build_fact_pack.py first.", file=sys.stderr)
            sys.exit(1)
    else:
        ap.error("Provide either ticker or --fact-pack")

    if not fp_path.exists():
        print(f"[ic-memo] fact_pack file not found: {fp_path}", file=sys.stderr)
        sys.exit(1)
    try:
        fp = json.loads(fp_path.read_text())
    except Exception as exc:
        print(f"[ic-memo] fact_pack parse error: {exc}", file=sys.stderr)
        sys.exit(2)

    md = compose(fp, llm_polish=args.llm_polish)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    out_path = args.output_dir / f"{date_str}_{fp['ticker']}_ic_memo.md"
    out_path.write_text(md)
    print(f"[ic-memo] memo written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

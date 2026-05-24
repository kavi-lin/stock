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


def compute_structural_shift(income: list, margins_8q: list) -> dict:
    """Detect paradigm-shift earnings: EPS QoQ jump + GM σ-breakout + revenue accel.

    CANDIDATE: ≥2 of 3 signals satisfied in latest quarter.
    CONFIRMED: latest quarter CANDIDATE AND prior quarter also CANDIDATE.

    Tier consumed by investment_protocol Phase 3 to dampen valuation/red-team
    backward-looking attacks during super-cycles (V2.18.0).
    """
    def _signals_for_idx(idx: int) -> dict:
        if idx + 4 >= len(income) or idx >= len(margins_8q):
            return {"candidate": False, "signals": {}, "metrics": {}}
        cur = income[idx]
        prior_q = income[idx + 1] if idx + 1 < len(income) else None
        prior_y = income[idx + 4] if idx + 4 < len(income) else None

        eps_qoq = None
        if prior_q:
            cur_eps = cur.get("epsDiluted") if cur.get("epsDiluted") is not None else cur.get("eps")
            pq_eps = prior_q.get("epsDiluted") if prior_q.get("epsDiluted") is not None else prior_q.get("eps")
            if cur_eps is not None and pq_eps is not None and pq_eps > 0:
                eps_qoq = (cur_eps - pq_eps) / pq_eps
        sig_a = eps_qoq is not None and eps_qoq >= 0.30

        cur_gm = margins_8q[idx].get("gross") if idx < len(margins_8q) else None
        hist_gms = [m.get("gross") for m in margins_8q[idx + 1: idx + 9] if m.get("gross") is not None]
        gm_mean = gm_std = gm_z = None
        if cur_gm is not None and len(hist_gms) >= 3:
            gm_mean = sum(hist_gms) / len(hist_gms)
            var = sum((x - gm_mean) ** 2 for x in hist_gms) / len(hist_gms)
            gm_std = var ** 0.5
            gm_z = (cur_gm - gm_mean) / gm_std if gm_std > 0 else 0.0
        sig_b = gm_z is not None and gm_z >= 2.0

        rev_yoy = None
        if prior_y and (prior_y.get("revenue") or 0) > 0:
            rev_yoy = ((cur.get("revenue") or 0) - prior_y.get("revenue")) / prior_y.get("revenue")
        prior_q_yoy = None
        if idx + 5 < len(income) and prior_q:
            pqy = income[idx + 5]
            if (pqy.get("revenue") or 0) > 0:
                prior_q_yoy = ((prior_q.get("revenue") or 0) - pqy.get("revenue")) / pqy.get("revenue")
        sig_c = (rev_yoy is not None and rev_yoy >= 0.25
                 and prior_q_yoy is not None and rev_yoy > prior_q_yoy + 0.05)

        return {
            "candidate": sum([sig_a, sig_b, sig_c]) >= 2,
            "signals": {"eps_qoq_jump": sig_a, "gm_breakout": sig_b, "rev_accel": sig_c},
            "metrics": {
                "eps_qoq":      round(eps_qoq, 4)     if eps_qoq is not None else None,
                "gm_latest":    round(cur_gm, 4)      if cur_gm is not None else None,
                "gm_hist_mean": round(gm_mean, 4)     if gm_mean is not None else None,
                "gm_hist_std":  round(gm_std, 4)      if gm_std is not None else None,
                "gm_z_score":   round(gm_z, 2)        if gm_z is not None else None,
                "rev_yoy":      round(rev_yoy, 4)     if rev_yoy is not None else None,
                "prior_q_yoy":  round(prior_q_yoy, 4) if prior_q_yoy is not None else None,
            },
        }

    if len(income) < 5 or len(margins_8q) < 5:
        return {
            "tier": "INSUFFICIENT_DATA",
            "candidate": False,
            "signals": {},
            "metrics": {},
            "prior_quarter_candidate": False,
        }

    latest = _signals_for_idx(0)
    prior = _signals_for_idx(1) if len(income) >= 6 else {"candidate": False}

    if latest["candidate"] and prior.get("candidate"):
        tier = "CONFIRMED"
    elif latest["candidate"]:
        tier = "CANDIDATE"
    else:
        tier = "NONE"

    return {
        "tier": tier,
        "candidate": tier in ("CANDIDATE", "CONFIRMED"),
        "signals": latest["signals"],
        "metrics": latest["metrics"],
        "prior_quarter_candidate": prior.get("candidate", False),
    }


def compute_wc_diagnostics(income: list, balance: list) -> dict:
    """V3.17 (Codex review) — 4-quarter DSO / DIO / DPO trend + DPO fallback method.

    Returns dict with trends + dpo_method + flag_estimate. Consumed by:
      - compute_quality_flags() to disambiguate cash_conversion_positive_gap
        between clean vs WC-driven
      - investment_protocol_v5_0 Phase 1 EARNINGS_ANALYST_BUNDLE

    DPO fallback (M3 / G3):
      - direct: accountsPayable / costOfRevenue × 91
      - estimated: 0.6 × otherCurrentLiabilities / COGS × 91 (foreign-ADR fallback)
      - unavailable: returns None
    """
    def _q_trend(values: list) -> str:
        """4Q trend label. Returns rising / declining / stable / insufficient."""
        if len(values) < 4 or any(v is None for v in values):
            return "insufficient"
        # values are newest-first (idx 0 = latest)
        oldest_to_newest = list(reversed(values))
        # Monotonic check
        if all(oldest_to_newest[i] < oldest_to_newest[i + 1] for i in range(3)):
            return "rising"
        if all(oldest_to_newest[i] > oldest_to_newest[i + 1] for i in range(3)):
            return "declining"
        return "stable"

    def _q_deteriorating(values: list) -> bool:
        """M3 — WC indicator 'deteriorating' = monotonic rising over 4Q
        AND latest Q > 4Q_avg × 1.15."""
        if len(values) < 4 or any(v is None for v in values):
            return False
        oldest_to_newest = list(reversed(values))
        monotonic = all(oldest_to_newest[i] < oldest_to_newest[i + 1] for i in range(3))
        if not monotonic:
            return False
        avg = sum(values[:4]) / 4
        return values[0] > avg * 1.15

    dso_q = []
    dio_q = []
    dpo_q = []
    dpo_method_latest = "unavailable"
    flag_estimate_latest = False

    for i in range(min(4, len(income), len(balance))):
        rev = income[i].get("revenue")
        cogs = income[i].get("costOfRevenue")
        ar = balance[i].get("netReceivables")
        inv = balance[i].get("inventory")
        ap = balance[i].get("accountsPayable")
        ocl = balance[i].get("otherCurrentLiabilities")

        # DSO = AR / revenue × 91
        if ar is not None and rev and rev > 0:
            dso_q.append(ar / rev * 91)
        else:
            dso_q.append(None)

        # DIO = inventory / COGS × 91 (fall back to revenue × 0.6 as COGS proxy if missing)
        cogs_for_dio = cogs if (cogs and cogs > 0) else (rev * 0.6 if rev else None)
        if inv is not None and cogs_for_dio and cogs_for_dio > 0:
            dio_q.append(inv / cogs_for_dio * 91)
        else:
            dio_q.append(None)

        # DPO fallback cascade
        cogs_for_dpo = cogs if (cogs and cogs > 0) else (rev * 0.6 if rev else None)
        if ap is not None and ap > 0 and cogs_for_dpo:
            dpo_q.append(ap / cogs_for_dpo * 91)
            if i == 0:
                dpo_method_latest = "direct"
                flag_estimate_latest = False
        elif ocl and ocl > 0 and cogs_for_dpo:
            dpo_q.append(0.6 * ocl / cogs_for_dpo * 91)
            if i == 0:
                dpo_method_latest = "estimated_from_other_cl"
                flag_estimate_latest = True
        else:
            dpo_q.append(None)
            if i == 0:
                dpo_method_latest = "unavailable"

    return {
        "dso_q4":               [round(v, 1) if v is not None else None for v in dso_q],
        "dio_q4":               [round(v, 1) if v is not None else None for v in dio_q],
        "dpo_q4":               [round(v, 1) if v is not None else None for v in dpo_q],
        "dso_q4_trend":         _q_trend(dso_q),
        "dio_q4_trend":         _q_trend(dio_q),
        "dpo_q4_trend":         _q_trend(dpo_q),
        "dso_deteriorating":    _q_deteriorating(dso_q),
        "dio_deteriorating":    _q_deteriorating(dio_q),
        "dpo_deteriorating":    _q_deteriorating(dpo_q),
        "dpo_method":           dpo_method_latest,
        "flag_estimate":        flag_estimate_latest,
        "wc_deteriorating":     (
            # WC惡化 = any DSO/DIO 惡化, OR (DPO 惡化 AND method=direct)
            # estimated DPO 不能單獨觸發 (G3 fix) — 必須 DSO 或 DIO 同時命中才可
            _q_deteriorating(dso_q)
            or _q_deteriorating(dio_q)
            or (_q_deteriorating(dpo_q) and dpo_method_latest == "direct")
        ),
    }


def _identify_new_segment(segments: dict, annual_growth: list) -> dict | None:
    """V3.17 (M1) — pick the single 'new segment' for business_mix_shift_overlay.

    Definition: argmax over reported segments of
        (segment_5y_CAGR_per_share - consolidated_5y_CAGR_per_share)
      AND segment_latest_YoY > 0

    Returns dict {name, share_of_revenue, yoy_growth, five_y_cagr,
                  data_mode} or None when insufficient data.

    Data mode:
      - quarterly: per-quarter segment breakdown available (FMP paid tier)
      - fy_fallback: only FY segment data (free tier — tier ceiling is EMERGING)
      - unavailable: no segment data at all
    """
    if not segments or not isinstance(segments, dict):
        return None

    # Pick the richer of product_fy vs geographic_fy
    product_fy = segments.get("product_fy") or []
    geographic_fy = segments.get("geographic_fy") or []
    src = product_fy if len(product_fy) >= len(geographic_fy) else geographic_fy
    src_kind = "product" if src is product_fy else "geographic"
    if not src or len(src) < 2:
        return None

    # Each row is a year with multiple segment keys + 'date'
    # Compute per-segment latest share, YoY, 5y CAGR
    latest_row = src[0]
    prior_row = src[1] if len(src) >= 2 else None
    five_y_row = src[4] if len(src) >= 5 else (src[-1] if src else None)

    if not isinstance(latest_row, dict) or not isinstance(prior_row, dict):
        return None

    seg_keys = [k for k in latest_row.keys()
                if k not in ("date", "period", "fiscalYear")
                and isinstance(latest_row.get(k), (int, float))]
    if not seg_keys:
        return None

    total_latest = sum(latest_row.get(k) or 0 for k in seg_keys)
    if total_latest <= 0:
        return None

    # Consolidated 5y CAGR per share (from annual_growth if available)
    cons_5y_cagr = None
    if annual_growth and isinstance(annual_growth[0], dict):
        cons_5y_cagr = annual_growth[0].get("fiveYRevenueGrowthPerShare")
    cons_5y_cagr = cons_5y_cagr if cons_5y_cagr is not None else 0.0

    candidates = []
    for k in seg_keys:
        latest = latest_row.get(k) or 0
        prior = prior_row.get(k) or 0
        five_y = (five_y_row.get(k) if isinstance(five_y_row, dict) else None) or 0
        share = latest / total_latest if total_latest > 0 else 0
        yoy = (latest - prior) / prior if prior > 0 else None
        # 5y CAGR (assume 4 year span between idx 0 and idx 4)
        if five_y > 0 and latest > 0 and len(src) >= 5:
            cagr = (latest / five_y) ** (1 / 4) - 1
        else:
            cagr = None
        if yoy is None or yoy <= 0:
            continue
        rel_cagr = (cagr - cons_5y_cagr) if cagr is not None else None
        candidates.append({
            "name": k,
            "share": share,
            "yoy": yoy,
            "five_y_cagr": cagr,
            "relative_cagr": rel_cagr,
        })

    if not candidates:
        return None
    # Pick top-1 by relative_cagr (fall back to yoy if cagr unavailable)
    candidates.sort(
        key=lambda c: (c["relative_cagr"] if c["relative_cagr"] is not None else c["yoy"]),
        reverse=True,
    )
    top = candidates[0]
    return {
        "name":              top["name"],
        "share_of_revenue":  round(top["share"], 4),
        "yoy_growth":        round(top["yoy"], 4),
        "five_y_cagr":       round(top["five_y_cagr"], 4) if top["five_y_cagr"] is not None else None,
        "relative_cagr":     round(top["relative_cagr"], 4) if top["relative_cagr"] is not None else None,
        "data_mode":         "fy_fallback",   # quarterly unavailable on FMP free tier
        "data_kind":         src_kind,
    }


def compute_business_mix_shift_overlay(segments: dict, annual_growth: list,
                                       margins_8q: list) -> dict:
    """V3.17 (Codex v5 + Gemini G1) — business mix shift detector.

    Tier definitions (M1 + M2):
      NO_DATA      — cannot identify new_segment from available data
      STABLE       — new_segment identified but below EMERGING thresholds
      EMERGING     — new_segment_share ∈ [10%, 25%]
                     AND new_segment_yoy ≥ 15%
                     AND new_segment_5y_cagr > consolidated_5y_cagr + 10pp
      ESTABLISHED  — new_segment_share ≥ 25%
                     AND new_segment_operating_income_share ≥ 40%
                     AND condition sustained for 4+ quarters (proxy: 2 consecutive FY)

    Data boundary: FY-fallback mode caps tier at EMERGING (Codex v3 — paid-tier
    quarterly segment OI required for ESTABLISHED).
    """
    new_seg = _identify_new_segment(segments, annual_growth)
    if new_seg is None:
        return {
            "tier":              "NO_DATA",
            "new_segment":       None,
            "segment_data_mode": "unavailable",
            "data_quality_note": "no segment data available (FMP paid tier required for quarterly product mix)",
        }

    share = new_seg["share_of_revenue"]
    yoy = new_seg["yoy_growth"]
    rel_cagr = new_seg.get("relative_cagr") or 0.0
    data_mode = new_seg.get("data_mode", "fy_fallback")

    # Tier decision
    tier = "STABLE"
    emerging_share_ok = 0.10 <= share < 0.25
    emerging_growth_ok = yoy >= 0.15
    emerging_cagr_ok = rel_cagr >= 0.10
    if emerging_share_ok and emerging_growth_ok and emerging_cagr_ok:
        tier = "EMERGING"

    # ESTABLISHED requires quarterly segment OI — NOT achievable on FY fallback
    if data_mode == "quarterly" and share >= 0.25:
        # Would need new_segment_operating_income_share ≥ 40% + 4Q persistence;
        # paid-tier check deferred to a future fetch.py change.
        # For now, only FY data → capped at EMERGING.
        pass

    note = None
    if data_mode == "fy_fallback":
        note = "tier capped at EMERGING — quarterly segment operating income unavailable on FMP free tier"

    return {
        "tier":              tier,
        "new_segment":       new_seg,
        "segment_data_mode": data_mode,
        "data_quality_note": note,
    }


def compute_transition_signature(structural_shift: dict,
                                 mix_overlay: dict) -> str:
    """V3.17 (round-2 Q1) — integrate paradigm shift (structural_shift) +
    business mix shift into a single downstream signature.

    Consumed by:
      - forecaster transition_case priority cascade (first match wins)
      - investment_protocol_v5_0 Phase 3 Step 2 penalty cascade rule #2

    Returns one of:
      paradigm_only — structural_shift CANDIDATE/CONFIRMED, mix STABLE/NO_DATA
      mix_only      — structural_shift NONE/INSUFFICIENT_DATA, mix EMERGING/ESTABLISHED
      both          — both signals positive
      neither       — neither
    """
    paradigm = (structural_shift or {}).get("tier") in {"CANDIDATE", "CONFIRMED"}
    mix = (mix_overlay or {}).get("tier") in {"EMERGING", "ESTABLISHED"}
    if paradigm and mix:
        return "both"
    if paradigm:
        return "paradigm_only"
    if mix:
        return "mix_only"
    return "neither"


def derive_cash_conversion_quality(flags: list) -> str:
    """V3.17 — collapse the cash conversion flag triplet into a single enum
    value for EARNINGS_ANALYST_BUNDLE consumers (investment_protocol M5)."""
    if "accruals_warning_negative" in flags:
        return "negative_accruals"
    if "cash_conversion_wc_driven" in flags:
        return "wc_driven"
    if "cash_conversion_positive_gap_clean" in flags:
        return "clean_positive_gap"
    return "n_a"


def compute_quality_flags(income: list, balance: list, cashflow: list, cf_q: dict,
                          wc_diag: dict | None = None) -> list[str]:
    """V3.17 (Codex review) — refactored to emit directional cash_conversion_*
    flags instead of single monolithic accruals_warning. Adds working-capital
    second-pass to disambiguate clean vs WC-driven positive cash conversion."""
    flags = []

    # 1. Cash conversion 3-tier flag (V3.17 Codex review #1):
    #    Replaces the legacy monolithic `accruals_warning` with directional
    #    flags that distinguish negative accruals (red flag) from positive
    #    cash conversion gaps (which were previously mis-penalized).
    ni_ttm = cf_q.get("ni_ttm") or 0
    ocf_ttm = cf_q.get("ocf_ttm") or 0
    if ni_ttm and abs(ni_ttm) > 0:
        gap_ratio = abs(ni_ttm - ocf_ttm) / abs(ni_ttm)
        if gap_ratio > 0.30:
            # Directional split based on sign of (OCF - NI)
            if ocf_ttm < ni_ttm:
                # NI > OpCF — earnings outrunning cash, classic red flag
                flags.append("accruals_warning_negative")
            else:
                # OCF > NI — investigate via WC second-pass
                wc_driven = bool(wc_diag and wc_diag.get("wc_deteriorating"))
                if wc_driven:
                    flags.append("cash_conversion_wc_driven")
                else:
                    flags.append("cash_conversion_positive_gap_clean")

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
    """0-30. V3.17 (Codex review #1) — directional cash-conversion flag scoring.

    Per-flag penalty:
      -4: standard red flag (accruals_warning_negative, capex_outpaces_ocf,
          gross_margin_compression, dso_slowdown, negative_fcf, debt_buildup)
      -2: cash_conversion_wc_driven (half penalty — WC-driven positive gap is
          ambiguous, not a hard red flag)
       0: cash_conversion_positive_gap_clean (purely informational — no penalty;
          replaces the legacy accruals_warning miscategorization where OCF >> NI
          was treated identically to NI > OCF)

    Max remains 30 to avoid composite-score inflation per round-2 review feedback.
    """
    base = 25
    half_penalty_flags = {"cash_conversion_wc_driven"}
    zero_penalty_flags = {"cash_conversion_positive_gap_clean"}
    for f in flags:
        if f in zero_penalty_flags:
            continue
        if f in half_penalty_flags:
            base -= 2
        else:
            base -= 4
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

    segments = bundle.get("segments") or {}

    margins_8q = compute_margins_8q(income)
    yoy = compute_yoy_growth(income)
    bh = compute_balance_health(balance)
    cf_q = compute_cf_quality(cashflow, income)
    # V3.17 — WC diagnostics computed first, then fed into compute_quality_flags
    # so the directional cash_conversion_* flags can be assigned with WC context.
    wc_diag = compute_wc_diagnostics(income, balance)
    flags = compute_quality_flags(income, balance, cashflow, cf_q, wc_diag=wc_diag)
    structural = compute_structural_shift(income, margins_8q)
    mix_overlay = compute_business_mix_shift_overlay(segments, growth, margins_8q)
    transition_signature = compute_transition_signature(structural, mix_overlay)
    cash_conversion_quality = derive_cash_conversion_quality(flags)

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
        "margins_8q":             margins_8q,
        "yoy_growth":             yoy,
        "balance_health":         bh,
        "cash_flow_quality":      cf_q,
        "working_capital_diagnostics": wc_diag,
    }
    bundle["quality_flags"]    = flags
    bundle["structural_shift"] = structural
    # V3.17 — new fields consumed by investment_protocol Phase 1
    # EARNINGS_ANALYST_BUNDLE + forecaster transition cascade.
    bundle["business_mix_shift_overlay"] = mix_overlay
    bundle["transition_signature"]       = transition_signature
    bundle["cash_conversion_quality"]    = cash_conversion_quality
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
          f"shift={bundle['structural_shift']['tier']} "
          f"mix={bundle['business_mix_shift_overlay']['tier']} "
          f"transition_sig={bundle['transition_signature']} "
          f"cc={bundle['cash_conversion_quality']} "
          f"flags={bundle['quality_flags'] or 'clean'} "
          f"(Q{bundle['score_components']['quality']}/30 "
          f"G{bundle['score_components']['growth']}/30 "
          f"V{bundle['score_components']['valuation']}/25 "
          f"A{bundle['score_components']['analyst']}/15)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""compute_price_framework.py — V3.45.3 deterministic price framework engine.

Computes the ENTIRE Phase 4.5 price stack in one call (0 LLM arithmetic):
  1. fair_value_summary        — 6-anchor weighted blend (V5.0 algorithm, unchanged)
  2. fair_value_range          — anchor distribution P25/P50/P75 + range_verdict +
                                 dispersion CV + owner-earnings multiple shadow (V3.45.1)
  3. multi_horizon_price_framework — 5d volatility band / 60d target / long-term ref /
                                 convergence mhp_signal (V5.1)
  4. implied_expectations      — reverse DCF implied 5Y FCF CAGR (V3.45.1)

Why a script: the V3.45.x spec accumulated math an LLM cannot reliably do inline
(weighted percentiles, CV, iterative reverse-DCF solve). Protocol discipline says
"禁止 LLM 重新評估數字" — this engine enforces it. PM calls this at Phase 3 Step 0
(all inputs are ready at end of Phase 2) and copies the output verbatim.

Volatility inputs (sigma_daily / atr_14 / momentum_20d_pct) are computed HERE from
FMP OHLCV when --ticker is given (eliminates LLM transcription risk); explicit
values in the input file override the fetch.

Usage:
  python3 investment/scripts/compute_price_framework.py --from-file /tmp/nvda_pf.json
  cat inputs.json | python3 investment/scripts/compute_price_framework.py
  python3 investment/scripts/compute_price_framework.py --from-file f.json --no-fetch

Input JSON shape (all price-level fields in the SAME per-share unit):
{
  "ticker": "NVDA",
  "current_price": 455.07,                  # required
  "anchors": {                              # Phase 2 Valuation Specialist values
    "dcf_unlevered": 495.8, "dcf_levered": null, "analyst_pt_consensus": 525.0,
    "peer_pe_implied": 480.0, "owner_earnings_mult": 410.0, "forecaster_blend": null
  },
  "volatility": {                           # optional — overrides FMP fetch
    "sigma_daily": 0.028, "atr_14": 12.5, "momentum_20d_pct": 8.2
  },
  "key_levels": {"support": 415.0, "resistance": 500.0, "pivot": 460.0},
  "pattern_taxonomy": "pullback_in_uptrend",
  "smart_money_label": "accumulating",
  "immediate_catalyst_5d": {"event": "Q2 earnings", "date": "2026-08-13",
                            "direction_lean": "BULLISH", "expected_move_pct": 5.5},
  "fred": {"treasury_10y": 0.041, "treasury_10y_real": 0.018},   # decimals
  "reverse_dcf": {                          # optional block
    "fcf_base_per_share": 14.2,             # owner earnings per share (Burry rule 3)
    "actual_3y_fcf_cagr": 0.14, "lane_fcf_estimate": 0.18
  }
}

Output: single JSON object on stdout with the 4 blocks + engine stamp. rc=0 even
when sub-blocks degrade to null (degradation is data, not failure); rc=1 only on
unusable input (missing current_price / unparseable JSON).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

ENGINE_VERSION = "compute_price_framework.py v1.1 (V4.46.0)"

# ── Constants (B3 — 兩組常數用途不同，集中定義並註明) ─────────────────────────
# WACC for reverse DCF: nominal 10Y + full equity risk premium (discounting nominal FCF).
ERP_WACC = 0.045
WACC_FALLBACK_RF = 0.045        # FRED unavailable → long-run nominal 10Y proxy
# Required earnings yield for owner-earnings multiple shadow: REAL 10Y + a lower
# premium (owner earnings already grow with inflation, so the real rate is the
# correct base and the premium excludes the inflation-compensation component).
ERP_EARNINGS_YIELD = 0.04

TERMINAL_GROWTH = 0.025
IMPLIED_CAGR_CLAMP = (-0.20, 0.60)
OE_MULT_CLAMP = (10.0, 22.0)

ANCHOR_WEIGHTS = {
    "dcf_unlevered": 0.30,
    "dcf_levered": 0.15,
    "analyst_pt_consensus": 0.20,
    "peer_pe_implied": 0.20,
    "owner_earnings_mult": 0.10,
    "forecaster_blend": 0.05,
}

DRIFT_BY_PATTERN = {
    "uptrend_breakout": 0.30,
    "uptrend_continuation": 0.20,
    "pullback_in_uptrend": 0.10,
    "oversold_bounce_attempt": 0.10,
    "consolidation": 0.00,
    "false_breakout": -0.20,
    "topping_pattern": -0.30,
    "downtrend": -0.50,
}
SMART_MONEY_NUDGE = {"accumulating": 0.10, "distributing": -0.10, "mixed": 0.0, "neutral": 0.0}
DRIFT_CLAMP = (-0.60, 0.50)
Z80 = 1.28
SQRT5 = math.sqrt(5)

MID_WEIGHTS = {"momentum": 0.40, "pt_60d": 0.35, "earnings_revision": 0.25}
MOMENTUM_DECAY = 0.50
PT_PULL_FACTOR = 1.00

# ── V3.46.0 — Valuation archetype (shadow-only; live weights untouched) ──────
# 判定門檻（初值，#3b 切換前用累積數據校準）
HYPERGROWTH_REV_YOY = 0.25       # rev YoY > 25%
MATURE_FCF_MARGIN = 0.08         # FCF margin > 8%
MATURE_REV_YOY = 0.15            # rev YoY < 15%
CYCLICAL_MARGIN_SIGMA_PP = 5.0   # 8Q 淨利率 σ > 5pp
CYCLICAL_SECTORS = ("Technology", "Energy", "Basic Materials", "Materials", "Industrials")
FINANCIAL_SECTORS = ("Financial Services", "Financials")

# 9-anchor 池 archetype 權重表（shadow blend 用）。balanced = live 權重 + 新 anchor 0
ARCHETYPE_WEIGHTS = {
    "mature_cashflow": {
        "dcf_unlevered": 0.30, "dcf_levered": 0.10, "analyst_pt_consensus": 0.15,
        "peer_pe_implied": 0.15, "owner_earnings_mult": 0.15, "forecaster_blend": 0.05,
        "peer_ev_ebitda_implied": 0.10, "peer_ev_sales_implied": 0.0, "pb_roe_justified": 0.0,
    },
    "hypergrowth": {
        "dcf_unlevered": 0.10, "dcf_levered": 0.05, "analyst_pt_consensus": 0.25,
        "peer_pe_implied": 0.0, "owner_earnings_mult": 0.0, "forecaster_blend": 0.15,
        "peer_ev_ebitda_implied": 0.15, "peer_ev_sales_implied": 0.30, "pb_roe_justified": 0.0,
    },
    "cyclical": {
        "dcf_unlevered": 0.25, "dcf_levered": 0.10, "analyst_pt_consensus": 0.15,
        "peer_pe_implied": 0.10, "owner_earnings_mult": 0.10, "forecaster_blend": 0.05,
        "peer_ev_ebitda_implied": 0.25, "peer_ev_sales_implied": 0.0, "pb_roe_justified": 0.0,
    },
    "financial": {
        "dcf_unlevered": 0.05, "dcf_levered": 0.05, "analyst_pt_consensus": 0.30,
        "peer_pe_implied": 0.20, "owner_earnings_mult": 0.0, "forecaster_blend": 0.05,
        "peer_ev_ebitda_implied": 0.0, "peer_ev_sales_implied": 0.0, "pb_roe_justified": 0.35,
    },
    "balanced": {**ANCHOR_WEIGHTS, "peer_ev_ebitda_implied": 0.0,
                 "peer_ev_sales_implied": 0.0, "pb_roe_justified": 0.0},
}


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def _pos(x):
    v = _num(x)
    return v if v is not None and v > 0 else None


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ── Weighted statistics ───────────────────────────────────────────────────────
def weighted_mean(vals, wts):
    s = sum(wts)
    return sum(v * w for v, w in zip(vals, wts)) / s if s else None


def weighted_std(vals, wts):
    m = weighted_mean(vals, wts)
    if m is None:
        return None
    s = sum(wts)
    var = sum(w * (v - m) ** 2 for v, w in zip(vals, wts)) / s
    return math.sqrt(var)


def weighted_percentile(vals, wts, q):
    """Weighted percentile via cumulative-weight interpolation on sorted values."""
    pairs = sorted(zip(vals, wts))
    total = sum(w for _, w in pairs)
    if total <= 0:
        return None
    cum, points = 0.0, []
    for v, w in pairs:
        points.append((cum + w / 2, v))   # midpoint convention
        cum += w
    target = q * total
    if target <= points[0][0]:
        return points[0][1]
    if target >= points[-1][0]:
        return points[-1][1]
    for (c0, v0), (c1, v1) in zip(points, points[1:]):
        if c0 <= target <= c1:
            t = (target - c0) / (c1 - c0) if c1 > c0 else 0.0
            return v0 + t * (v1 - v0)
    return points[-1][1]


def median(vals):
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _verdict_band(vs_pct: float) -> str:
    if vs_pct >= 30:
        return "extreme_undervalued"
    if vs_pct >= 10:
        return "undervalued"
    if vs_pct >= -10:
        return "fairly_valued"
    if vs_pct >= -30:
        return "overvalued"
    return "extreme_overvalued"


# ── Block 1: fair_value_summary (V5.0 algorithm, byte-identical semantics) ────
def compute_fair_value_summary(anchors: dict, current_price: float) -> dict:
    available = {k: _pos(anchors.get(k)) for k in ANCHOR_WEIGHTS}
    available = {k: v for k, v in available.items() if v is not None}
    out = {
        "anchors": {k: _pos(anchors.get(k)) for k in ANCHOR_WEIGHTS},
        "weights_used": {},
        "weighted_fair_value": None,
        "current_price": current_price,
        "vs_current_pct": None,
        "verdict_band": None,
        "confidence": "low",
        "anchors_available": len(available),
        "methodology_note": "",
    }
    if not available:
        out["methodology_note"] = "0/6 anchors available"
        return out
    total_w = sum(ANCHOR_WEIGHTS[k] for k in available)
    weights_norm = {k: ANCHOR_WEIGHTS[k] / total_w for k in available}
    wfv = sum(weights_norm[k] * available[k] for k in available)
    vs_pct = (wfv - current_price) / current_price * 100
    band = _verdict_band(vs_pct)
    n = len(available)
    conf = "high" if n >= 5 else "medium" if n >= 3 else "low"
    missing = [k for k in ANCHOR_WEIGHTS if k not in available]
    out.update({
        "weights_used": {k: round(w, 4) for k, w in weights_norm.items()},
        "weighted_fair_value": round(wfv, 2),
        "vs_current_pct": round(vs_pct, 2),
        "verdict_band": band,
        "confidence": conf,
        "methodology_note": (
            f"{n}/6 anchors used"
            + (f"; {', '.join(missing)} unavailable, weight redistributed" if missing else "")
        ),
    })
    return out


# ── Block 2: fair_value_range (V3.45.1) ──────────────────────────────────────
def compute_fair_value_range(anchors: dict, current_price: float, fred: dict) -> dict:
    available = {k: _pos(anchors.get(k)) for k in ANCHOR_WEIGHTS}
    available = {k: v for k, v in available.items() if v is not None}
    vals = list(available.values())
    total_w = sum(ANCHOR_WEIGHTS[k] for k in available) or 1.0
    wts = [ANCHOR_WEIGHTS[k] / total_w for k in available]
    n = len(vals)

    if n >= 4:
        range_method = "weighted_percentile"
        p25 = weighted_percentile(vals, wts, 0.25)
        p50 = weighted_percentile(vals, wts, 0.50)
        p75 = weighted_percentile(vals, wts, 0.75)
    elif n >= 2:
        range_method = "minmax_fallback"
        p25, p50, p75 = min(vals), median(vals), max(vals)
    else:
        range_method = None
        p25 = p50 = p75 = None

    min_a, max_a = (min(vals), max(vals)) if n else (None, None)

    if p25 is None:
        range_verdict = None
    elif current_price > max_a:
        range_verdict = "extreme_overvalued"
    elif current_price < min_a:
        range_verdict = "extreme_undervalued"
    elif current_price > p75:
        range_verdict = "overvalued_zone"
    elif current_price < p25:
        range_verdict = "undervalued_zone"
    else:
        range_verdict = "fair_zone"

    if n >= 2:
        wmean = weighted_mean(vals, wts)
        wstd = weighted_std(vals, wts)
        cv = (wstd / wmean) if wmean else None
        grade = None if cv is None else ("high" if cv < 0.15 else "medium" if cv < 0.35 else "low")
    else:
        cv, grade = None, None

    real10 = _num((fred or {}).get("treasury_10y_real"))
    if real10 is not None:
        req_yield = real10 + ERP_EARNINGS_YIELD
        oe_linked = clamp(1.0 / req_yield, *OE_MULT_CLAMP) if req_yield > 0 else None
    else:
        req_yield, oe_linked = None, None

    # max/min spread — plain-language dispersion signal for the UI ("anchors span N×")
    disp_ratio = round(max_a / min_a, 2) if (min_a and min_a > 0 and max_a is not None) else None

    return {
        "range_method": range_method,
        "p25": round(p25, 2) if p25 is not None else None,
        "p50": round(p50, 2) if p50 is not None else None,
        "p75": round(p75, 2) if p75 is not None else None,
        "min_anchor": round(min_a, 2) if min_a is not None else None,
        "max_anchor": round(max_a, 2) if max_a is not None else None,
        "dispersion_ratio": disp_ratio,
        "range_verdict": range_verdict,
        "anchor_dispersion_cv": round(cv, 4) if cv is not None else None,
        "agreement_grade": grade,
        "anchors_used_n": n,
        "owner_earnings_multiple_shadow": {
            "oe_mult_static": 15.0,
            "oe_mult_rate_linked": round(oe_linked, 2) if oe_linked is not None else None,
            "required_yield": round(req_yield, 4) if req_yield is not None else None,
        },
    }


# ── V4.46.0 — confidence ← anchor dispersion (general, all tickers) ──────────
_CONF_ORDER = {"low": 0, "medium": 1, "high": 2}
# Two-tier cv cap (decoupled from agreement_grade, which is a blunt 0.35 cliff:
# owner_earnings_mult is a structural low outlier across the tech universe, so
# grade=low fires almost everywhere). These give confidence some discrimination:
# extreme dispersion -> low, moderate -> medium, tight -> untouched.
CONF_CAP_CV_LOW = 0.60       # cv >= this -> cap confidence at "low"
CONF_CAP_CV_MEDIUM = 0.35    # cv >= this (and < LOW) -> cap at "medium"


def reconcile_confidence(fvs: dict, frange: dict) -> None:
    """Cap fair_value_summary.confidence by anchor dispersion (cv), in place.

    Pre-V4.46.0 `confidence` was set purely from how many anchors *returned a
    number* (n>=5 -> high), ignoring whether they *agreed*. A blend of anchors
    spanning 50x (e.g. ARM: $3.17-$163.75, cv=1.20) was still labelled "high".
    The dispersion cv already lives in fair_value_range; here we feed it back so
    the point estimate can't claim more confidence than the anchors support.
    Tight anchors (cv < 0.35) are untouched.
    """
    cv = frange.get("anchor_dispersion_cv")
    cur = fvs.get("confidence")
    if cv is None or cur not in _CONF_ORDER:
        return
    if cv >= CONF_CAP_CV_LOW:
        cap, thr = "low", CONF_CAP_CV_LOW
    elif cv >= CONF_CAP_CV_MEDIUM:
        cap, thr = "medium", CONF_CAP_CV_MEDIUM
    else:
        return
    if _CONF_ORDER[cap] < _CONF_ORDER[cur]:
        fvs["confidence_count_based"] = cur
        fvs["confidence"] = cap
        fvs["confidence_capped_by"] = (
            f"anchor_dispersion cv={cv} (>= {thr}) -> {cap}; "
            f"span={frange.get('dispersion_ratio')}x"
        )


# ── Block 3: multi_horizon_price_framework (V5.1) ────────────────────────────
def compute_mhp(inp: dict, fvs: dict) -> dict:
    cp = inp["current_price"]
    vol = inp.get("volatility") or {}
    sigma = _pos(vol.get("sigma_daily"))
    atr = _pos(vol.get("atr_14"))
    confidence = "high"
    if sigma is None and atr is not None:
        sigma = atr / cp          # ATR 反推
        confidence = "medium"
    if sigma is None:
        sigma, confidence = 0.0, "low"

    pattern = inp.get("pattern_taxonomy")
    sm = inp.get("smart_money_label")
    drift = DRIFT_BY_PATTERN.get(pattern, 0.0) + SMART_MONEY_NUDGE.get(sm, 0.0)
    drift = clamp(drift, *DRIFT_CLAMP)

    center_ret = drift * sigma * SQRT5
    half_width = Z80 * sigma * SQRT5
    catalyst_widened = False

    cat = inp.get("immediate_catalyst_5d")
    if isinstance(cat, dict) and _pos(cat.get("expected_move_pct")):
        half_width += cat["expected_move_pct"] / 100.0
        if cat.get("direction_lean") == "NEUTRAL":
            center_ret = 0.0
        confidence = "low"
        catalyst_widened = True

    band_lower = cp * (1 + center_ret - half_width)
    band_point = cp * (1 + center_ret)
    band_upper = cp * (1 + center_ret + half_width)

    kl = inp.get("key_levels") or {}
    support, resistance = _pos(kl.get("support")), _pos(kl.get("resistance"))
    lower_capped = max(band_lower, support) if support is not None else band_lower
    upper_capped = min(band_upper, resistance) if resistance is not None else band_upper
    notes = []
    if support is not None and band_lower < support:
        notes.append(f"下界受 support ${support:g} 撐住（原始 ${band_lower:.2f}）")
    if resistance is not None and band_upper > resistance:
        notes.append(f"上界受 resistance ${resistance:g} 壓制（原始 ${band_upper:.2f}）")
    key_level_note = "；".join(notes) or "帶未觸及 key levels"

    short_term = {
        "band": [round(band_lower, 2), round(band_point, 2), round(band_upper, 2)],
        "band_capped": [round(lower_capped, 2), round(band_point, 2), round(upper_capped, 2)],
        "drift_sigma": round(drift, 2),
        "sigma_daily": round(sigma, 5) if sigma else None,
        "atr_14": atr,
        "confidence": confidence,
        "catalyst_widened": catalyst_widened,
        "key_level_note": key_level_note,
    }

    # mid-term 60d
    mom_pct = _num(vol.get("momentum_20d_pct"))
    anchors = fvs["anchors"]
    analyst_pt = _pos(anchors.get("analyst_pt_consensus"))
    forecaster = _pos(anchors.get("forecaster_blend"))
    momentum_target = cp * (1 + (mom_pct / 100) * MOMENTUM_DECAY) if mom_pct is not None else None
    pt_60d = cp + (analyst_pt - cp) * (60 / 365) * PT_PULL_FACTOR if analyst_pt else None
    # V3.48.0 #8a: forecaster_blend 是長期錨，原直接當 60d 成分 = horizon mismatch
    # （等於假設 60 天走完通往長期合理價全程）→ 折算 60/250 交易日
    earnings_revision = cp + (forecaster - cp) * (60 / 250) if forecaster else None
    parts = {"momentum": momentum_target, "pt_60d": pt_60d, "earnings_revision": earnings_revision}
    avail = {k: v for k, v in parts.items() if _pos(v)}
    if avail:
        wsum = sum(MID_WEIGHTS[k] for k in avail)
        mid_target = sum((MID_WEIGHTS[k] / wsum) * avail[k] for k in avail)
        weights_used = {k: round(MID_WEIGHTS[k] / wsum, 4) for k in avail}
    else:
        mid_target, weights_used = None, {}
    reality = []
    if mid_target is not None and resistance is not None and mid_target > resistance:
        reality.append(f"需突破 ${resistance:g} 才成立")
    if mid_target is not None and support is not None and mid_target < support:
        reality.append(f"需跌破 ${support:g} 才成立")
    mid_term = {
        "momentum_target": round(momentum_target, 2) if momentum_target is not None else None,
        "pt_60d": round(pt_60d, 2) if pt_60d is not None else None,
        "earnings_revision": round(earnings_revision, 2) if earnings_revision is not None else None,
        "weights_used": weights_used,
        "mid_target": round(mid_target, 2) if mid_target is not None else None,
        "reality_check_note": "；".join(reality) or "mid_target 在 key levels 區間內",
    }

    # convergence (V3.45.1 #7 fix logic)
    LT = fvs.get("weighted_fair_value")
    mt = mid_term["mid_target"]
    if LT is None:
        signal, note = None, "長期 FV 不可得，convergence 跳過"
    elif lower_capped > LT:
        signal = "wait_for_pullback"
        note = f"5d 帶下界 ${lower_capped:.2f} > 長期FV ${LT:.2f} → 短期超漲、長期偏貴，等回檔"
    elif band_point < LT and mt is not None and mt > cp and cp < LT * 0.9:
        signal = "high_conviction_long_zone"
        note = f"現價 ${cp:.2f} < 0.9×FV ${LT:.2f}、mid ${mt:.2f} 向上、短期點估仍低於FV → 三框一致看多"
    elif mt is not None and mt > cp > LT:
        signal = "momentum_not_value"
        note = f"mid ${mt:.2f} > 現價 ${cp:.2f} > FV ${LT:.2f} → 動能交易非價值持有"
    else:
        signal = "neutral_aligned"
        note = "三框無顯著背離"

    if signal and fvs.get("confidence") == "low":
        note += "（長期FV 信心 low，訊號僅供參考）"

    return {
        "short_term_5d": short_term,
        "mid_term_60d": mid_term,
        "long_term_ref": {
            "weighted_fair_value": fvs.get("weighted_fair_value"),
            "verdict_band": fvs.get("verdict_band"),
            "confidence": fvs.get("confidence"),
        },
        "convergence": {"mhp_signal": signal, "signal_note": note},
        "engine": ENGINE_VERSION,
    }


# ── Block 4: implied_expectations (reverse DCF, V3.45.1) ─────────────────────
def _dcf_pv(fcf0: float, g: float, wacc: float, gt: float) -> float:
    pv = sum(fcf0 * (1 + g) ** t / (1 + wacc) ** t for t in range(1, 6))
    tv = fcf0 * (1 + g) ** 5 * (1 + gt) / (wacc - gt)
    return pv + tv / (1 + wacc) ** 5


def compute_implied_expectations(inp: dict) -> dict:
    cp = inp["current_price"]
    rdcf = inp.get("reverse_dcf") or {}
    fcf_ps = _num(rdcf.get("fcf_base_per_share"))
    fred = inp.get("fred") or {}
    t10 = _num(fred.get("treasury_10y"))
    if t10 is not None:
        wacc, wacc_source = t10 + ERP_WACC, "fred_10y"
    else:
        wacc, wacc_source = WACC_FALLBACK_RF + ERP_WACC, "fallback_fixed"

    out = {
        "implied_5y_fcf_cagr": None,
        "implied_out_of_range": False,
        "wacc_used": round(wacc, 4),
        "wacc_source": wacc_source,
        "fcf_base": fcf_ps,
        "fcf_base_source": "owner_earnings",
        "terminal_growth": TERMINAL_GROWTH,
        "actual_3y_fcf_cagr": _num(rdcf.get("actual_3y_fcf_cagr")),
        "lane_fcf_estimate": _num(rdcf.get("lane_fcf_estimate")),
        "sanity_note": "",
        "red_team_kill_seed": "",
    }
    if fcf_ps is None or fcf_ps <= 0:
        out["sanity_note"] = "FCF base ≤ 0 或缺，reverse DCF 不適用"
        return out
    if wacc <= TERMINAL_GROWTH:
        out["sanity_note"] = f"WACC {wacc:.3f} ≤ terminal growth，模型退化，跳過"
        return out

    # bisection: PV(g) 對 g 單調遞增，解 PV = current_price
    lo, hi = -0.90, 3.00
    if _dcf_pv(fcf_ps, hi, wacc, TERMINAL_GROWTH) < cp:
        raw = hi
    elif _dcf_pv(fcf_ps, lo, wacc, TERMINAL_GROWTH) > cp:
        raw = lo
    else:
        for _ in range(80):
            mid = (lo + hi) / 2
            if _dcf_pv(fcf_ps, mid, wacc, TERMINAL_GROWTH) < cp:
                lo = mid
            else:
                hi = mid
        raw = (lo + hi) / 2

    clamped = clamp(raw, *IMPLIED_CAGR_CLAMP)
    out["implied_5y_fcf_cagr"] = round(clamped, 4)
    out["implied_out_of_range"] = bool(raw < IMPLIED_CAGR_CLAMP[0] or raw > IMPLIED_CAGR_CLAMP[1])

    act, est = out["actual_3y_fcf_cagr"], out["lane_fcf_estimate"]
    cmp_parts = [f"現價 ${cp:g} 隱含 5Y FCF CAGR {clamped * 100:.0f}%"]
    if act is not None:
        cmp_parts.append(f"過去 3 年實際 {act * 100:.0f}%")
    if est is not None:
        cmp_parts.append(f"lane 估 {est * 100:.0f}%")
    verdict = ""
    ref = est if est is not None else act
    if ref is not None:
        ratio = (clamped / ref) if ref else None
        if ratio is not None and ratio > 1.5:
            verdict = " → 隱含預期顯著高於現實，過度樂觀"
        elif ratio is not None and ratio < 0.7:
            verdict = " → 隱含預期低於現實，市場悲觀定價"
    out["sanity_note"] = "；".join(cmp_parts) + verdict
    out["red_team_kill_seed"] = (
        f"IF 未來 2 季 FCF 年化增速 < {clamped * 100 / 2:.0f}%（隱含值一半）THEN 現價估值論點破滅"
    )
    return out


# ── V3.46.0: Valuation archetype shadow（live fair_value_summary 不動）────────
def classify_archetype(ai: dict | None) -> dict:
    """Deterministic archetype classification — 按序首中。缺判定輸入 → 該規則跳過。"""
    if not isinstance(ai, dict):
        return {"archetype": "balanced", "rule_hit": "no_inputs", "missing_inputs": ["archetype_inputs"]}
    sector = ai.get("sector")
    rev_yoy = _num(ai.get("revenue_yoy"))           # decimal, e.g. 0.32
    fcf_margin = _num(ai.get("fcf_margin"))         # decimal
    eps_ttm = _num(ai.get("eps_ttm"))
    sigma_pp = _num(ai.get("margin_sigma_pp"))      # 8Q 淨利率 σ（pp）；可直接給
    m8 = ai.get("margins_8q_net")                   # 或給 8Q 淨利率 list（decimal）
    if sigma_pp is None and isinstance(m8, list):
        vals = [v for v in m8 if isinstance(v, (int, float))]
        if len(vals) >= 4:
            mu = sum(vals) / len(vals)
            sigma_pp = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5 * 100

    missing = [k for k, v in (("sector", sector), ("revenue_yoy", rev_yoy),
                              ("fcf_margin", fcf_margin), ("eps_ttm", eps_ttm),
                              ("margin_sigma_pp", sigma_pp)) if v is None]
    if sector in FINANCIAL_SECTORS:
        hit = ("financial", f"sector={sector}")
    elif (rev_yoy is not None and rev_yoy > HYPERGROWTH_REV_YOY) or \
         (eps_ttm is not None and eps_ttm <= 0):
        hit = ("hypergrowth", f"rev_yoy={rev_yoy} / eps_ttm={eps_ttm}")
    elif sector in CYCLICAL_SECTORS and sigma_pp is not None and sigma_pp > CYCLICAL_MARGIN_SIGMA_PP:
        hit = ("cyclical", f"sector={sector} + margin_sigma={sigma_pp:.1f}pp")
    elif fcf_margin is not None and fcf_margin > MATURE_FCF_MARGIN and \
         rev_yoy is not None and rev_yoy < MATURE_REV_YOY:
        hit = ("mature_cashflow", f"fcf_margin={fcf_margin} + rev_yoy={rev_yoy}")
    else:
        hit = ("balanced", "fallback")
    return {"archetype": hit[0], "rule_hit": hit[1], "missing_inputs": missing}


def compute_new_anchors(inp: dict) -> dict:
    """3 新 anchor（per-share fair price）。資料不足 → null（重分配照舊）。

    EV implied 用精確數學：implied_EV = peer_median × self_metric_absolute，
    self_metric 由 self multiple 反推（EBITDA = EV / ev_ebitda；Sales = EV / ev_sales），
    equity = implied_EV − net_debt，price = equity / shares。
    """
    pr = inp.get("peer_ratios") or {}
    sr = inp.get("self_ratios") or {}
    evb = inp.get("ev_block") or {}
    ev, nd, sh = _pos(evb.get("enterprise_value")), _num(evb.get("net_debt")), _pos(evb.get("shares"))

    def _ev_implied(peer_med, self_mult):
        if not all(isinstance(x, (int, float)) for x in (peer_med or 0, self_mult or 0)):
            return None
        if not (peer_med and self_mult and self_mult > 0 and ev and sh):
            return None
        metric = ev / self_mult                       # EBITDA or Sales (absolute)
        equity = peer_med * metric - (nd or 0.0)
        return round(equity / sh, 2) if equity > 0 else None

    ev_ebitda = _ev_implied(_pos(pr.get("peer_ev_ebitda_median")), _pos(sr.get("ev_to_ebitda_ttm")))
    ev_sales = _ev_implied(_pos(pr.get("peer_ev_sales_median")), _pos(sr.get("ev_to_sales_ttm")))

    # pb_roe_justified: justified P/B = (ROE − g)/(r − g)，r = 10Y + beta×ERP
    roe, bvps = _num(sr.get("roe_ttm")), _pos(sr.get("book_value_per_share_ttm"))
    beta = _num(inp.get("beta"))
    t10 = _num((inp.get("fred") or {}).get("treasury_10y"))
    pb_roe = None
    if roe and bvps and roe > TERMINAL_GROWTH:
        r = (t10 if t10 is not None else WACC_FALLBACK_RF) + (beta if beta is not None else 1.0) * ERP_WACC
        if r > TERMINAL_GROWTH:
            jpb = clamp((roe - TERMINAL_GROWTH) / (r - TERMINAL_GROWTH), 0.2, 15.0)
            pb_roe = round(jpb * bvps, 2)

    return {"peer_ev_ebitda_implied": ev_ebitda,
            "peer_ev_sales_implied": ev_sales,
            "pb_roe_justified": pb_roe}


def compute_archetype_shadow(inp: dict, fvs: dict) -> dict:
    """Shadow blend：9-anchor 池 × archetype 權重。live fair_value_summary 不動。"""
    cp = inp["current_price"]
    cls = classify_archetype(inp.get("archetype_inputs"))
    new_anchors = compute_new_anchors(inp)
    anchors_full = {**(fvs.get("anchors") or {}), **new_anchors}
    weights = ARCHETYPE_WEIGHTS[cls["archetype"]]
    available = {k: _pos(anchors_full.get(k)) for k, w in weights.items() if w > 0}
    available = {k: v for k, v in available.items() if v is not None}
    if available:
        tw = sum(weights[k] for k in available)
        wn = {k: weights[k] / tw for k in available}
        wfv_s = sum(wn[k] * available[k] for k in available)
        vs_s = (wfv_s - cp) / cp * 100
        verdict_s = _verdict_band(vs_s)
        flip = verdict_s != fvs.get("verdict_band")
        weights_used = {k: round(v, 4) for k, v in wn.items()}
    else:
        wfv_s = vs_s = verdict_s = None
        flip, weights_used = None, {}
    return {
        "archetype": cls["archetype"],
        "rule_hit": cls["rule_hit"],
        "missing_inputs": cls["missing_inputs"],
        "new_anchors": new_anchors,
        "anchors_used_n": len(available),
        "weights_used": weights_used,
        "weighted_fair_value_shadow": round(wfv_s, 2) if wfv_s is not None else None,
        "vs_current_pct_shadow": round(vs_s, 2) if vs_s is not None else None,
        "verdict_band_shadow": verdict_s,
        "flip_vs_live": flip,
        "note": "shadow-only — live fair_value_summary 權重/verdict 不受影響（#3b 切換待 ≥20 session 翻轉率報告）",
    }


# ── Volatility fetch (FMP OHLCV → sigma/atr/momentum；LLM 抄寫風險消除) ───────
def fetch_volatility(ticker: str) -> dict:
    from scripts._shared import fmp_pool
    rows = fmp_pool.get(
        "historical-price-eod/full",
        {"symbol": ticker},
        stable=True, retries=2, timeout=20, hard_fail=False,
    )
    if not isinstance(rows, list) or len(rows) < 25:
        return {}
    rows = sorted(rows, key=lambda r: r.get("date", ""))[-60:]
    closes = [_num(r.get("close")) for r in rows]
    highs = [_num(r.get("high")) for r in rows]
    lows = [_num(r.get("low")) for r in rows]
    if any(c is None for c in closes[-21:]):
        return {}
    rets = [closes[i] / closes[i - 1] - 1 for i in range(len(closes) - 20, len(closes))
            if closes[i - 1]]
    m = sum(rets) / len(rets)
    sigma = math.sqrt(sum((r - m) ** 2 for r in rets) / len(rets))
    trs = []
    for i in range(len(rows) - 14, len(rows)):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        if None in (h, l, pc):
            continue
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = sum(trs) / len(trs) if trs else None
    mom = (closes[-1] / closes[-21] - 1) * 100 if closes[-21] else None
    return {
        "sigma_daily": round(sigma, 5),
        "atr_14": round(atr, 4) if atr is not None else None,
        "momentum_20d_pct": round(mom, 2) if mom is not None else None,
        "source": "fmp_historical_price_eod",
    }


# ── V3.48.0: self-assemble — quant inputs 由 engine 直接讀 cache/bundle，0 LLM 抄寫 ──
def _latest_earnings_cache(ticker: str) -> dict | None:
    import glob as _glob
    files = sorted(_glob.glob(os.path.join(
        BASE_DIR, "skills", "earnings-analyst", "cache", f"{ticker.upper()}_*.json")))
    if not files:
        return None
    try:
        with open(files[-1], encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def assemble_inputs(ticker: str, inp: dict) -> list:
    """Fill ONLY missing fields from deterministic sources（input file 永遠優先）。
    Returns list of assembled field paths（audit 用）。

    來源：earnings-analyst cache（DCF/PT/EV/archetype 原料）、FMP quote（price/epsTTM）、
    phase1_factpack peer bundle（peer medians + self ratios + beta）、fmp_supplementary
    （owner earnings per share）、forecaster cache（expected_value）、phase0 snapshot
    （real rate；nominal 10Y 無乾淨快取源 → 缺則 engine 自動 fallback_fixed）。
    """
    import glob as _glob
    filled = []

    def _fill(path: str, value):
        if value is None:
            return
        parts = path.split(".")
        d = inp
        for p in parts[:-1]:
            d = d.setdefault(p, {})
        if d.get(parts[-1]) is None:
            d[parts[-1]] = value
            filled.append(path)

    ec = _latest_earnings_cache(ticker) or {}
    val = ec.get("valuation") or {}
    _fill("anchors.dcf_unlevered", _pos(val.get("dcf_intrinsic")))
    _fill("anchors.dcf_levered", _pos(val.get("dcf_levered_intrinsic")))
    _fill("anchors.analyst_pt_consensus", _pos(val.get("price_target_consensus")))
    ev = ec.get("enterprise_value") or {}
    _fill("ev_block.enterprise_value", _pos(ev.get("enterpriseValue")))
    _fill("ev_block.shares", _pos(ev.get("numberOfShares")))
    if _num(ev.get("addTotalDebt")) is not None and _num(ev.get("minusCashAndCashEquivalents")) is not None:
        _fill("ev_block.net_debt", ev["addTotalDebt"] - ev["minusCashAndCashEquivalents"])
    der = ec.get("derived") or {}
    _fill("archetype_inputs.sector", (ec.get("snapshot") or {}).get("sector"))
    _fill("archetype_inputs.revenue_yoy", _num((der.get("yoy_growth") or {}).get("revenue_yoy")))
    _fill("archetype_inputs.fcf_margin", _num((der.get("cash_flow_quality") or {}).get("fcf_margin")))
    m8 = der.get("margins_8q")
    if isinstance(m8, list):
        nets = [r.get("net") for r in m8 if isinstance(r, dict) and isinstance(r.get("net"), (int, float))]
        if len(nets) >= 4:
            _fill("archetype_inputs.margins_8q_net", nets)

    # quote: current_price（stable quote 無 eps 欄 — eps 由 ratios-ttm P/E 反推，見下）
    try:
        from scripts._shared import fmp_pool
        q = fmp_pool.get("quote", {"symbol": ticker}, stable=True, retries=1, timeout=15, hard_fail=False)
        row = q[0] if isinstance(q, list) and q else (q if isinstance(q, dict) else {})
        _fill("current_price", _pos(row.get("price")))
    except Exception:
        pass
    eps_ttm = None

    # peer bundle: peer_pe_median × epsTTM、peer ratio medians、self ratios、beta
    try:
        sys.path.insert(0, os.path.join(BASE_DIR, "investment", "scripts"))
        from phase1_factpack import load_peer_bundle
        pb = load_peer_bundle(ticker) or {}
        if pb.get("status") == "ok":
            sr = pb.get("self_ratios_ttm") or {}
            # eps_ttm = price / pe_ttm 反推（stable quote 無 eps）。pe ≤ 0 / null（虧損股）→
            # eps_ttm 保持 None：hypergrowth 規則退化為只看 rev_yoy（限制，文件已註）
            pe_self = _num(sr.get("pe_ttm"))
            cp_now = _pos(inp.get("current_price"))
            if pe_self and pe_self > 0 and cp_now:
                eps_ttm = round(cp_now / pe_self, 4)
                _fill("archetype_inputs.eps_ttm", eps_ttm)
            pe_med = _pos(pb.get("peer_pe_median"))
            if pe_med and eps_ttm and eps_ttm > 0:
                _fill("anchors.peer_pe_implied", round(pe_med * eps_ttm, 2))
            _fill("peer_ratios.peer_ev_ebitda_median", _pos(pb.get("peer_ev_ebitda_median")))
            _fill("peer_ratios.peer_ev_sales_median", _pos(pb.get("peer_ev_sales_median")))
            _fill("peer_ratios.peer_pb_median", _pos(pb.get("peer_pb_median")))
            for k in ("ev_to_ebitda_ttm", "ev_to_sales_ttm", "roe_ttm", "book_value_per_share_ttm"):
                _fill(f"self_ratios.{k}", _num(sr.get(k)))
        from skills._shared.company_context import get_profile
        prof = get_profile(ticker) or {}
        _fill("beta", _num(prof.get("beta")))
    except Exception:
        pass

    # owner earnings per share → ×15 anchor + reverse DCF fcf base
    try:
        from skills._shared.fmp_supplementary import get_supplementary_bundle
        supp = get_supplementary_bundle(ticker) or {}
        oeps = _num((supp.get("owner_earnings") or {}).get("ownersEarningsPerShare"))
        if oeps and oeps > 0:
            _fill("anchors.owner_earnings_mult", round(oeps * 15, 2))
            _fill("reverse_dcf.fcf_base_per_share", oeps)
    except Exception:
        pass

    # forecaster cache（不 subprocess 跑 — 只讀 cache；缺/stale → null）
    fc_path = os.path.join(BASE_DIR, "skills", "earnings-valuation-forecaster", "cache",
                           f"{ticker.upper()}.json")
    if os.path.exists(fc_path):
        try:
            with open(fc_path, encoding="utf-8") as f:
                _fill("anchors.forecaster_blend", _pos(json.load(f).get("expected_value")))
        except Exception:
            pass

    # phase0 snapshot: real rate（nominal 10Y 留 input file / fallback）
    p0 = sorted(_glob.glob(os.path.join(BASE_DIR, "investment", "invest_logs", "*phase0*.json")))
    if p0:
        try:
            with open(p0[-1], encoding="utf-8") as f:
                rr = _num((json.load(f).get("fred_snapshot") or {}).get("real_rate_preferred"))
            if rr is not None:
                _fill("fred.treasury_10y_real", rr / 100.0)
        except Exception:
            pass

    return filled


def main():
    ap = argparse.ArgumentParser(description="Deterministic price framework engine (V3.45.3)")
    ap.add_argument("--from-file", help="input JSON path (default: stdin)")
    ap.add_argument("--no-fetch", action="store_true",
                    help="skip FMP volatility fetch even if volatility absent")
    ap.add_argument("--self-assemble", action="store_true",
                    help="V3.48.0: quant inputs 自組（earnings cache / peer bundle / supp / "
                         "forecaster cache / phase0）。input file 給的欄位永遠優先；"
                         "qualitative 欄（pattern/key_levels/catalyst）仍須 LLM lane 提供")
    args = ap.parse_args()

    try:
        raw = open(args.from_file).read() if args.from_file else sys.stdin.read()
        inp = json.loads(raw)
    except Exception as e:
        print(json.dumps({"error": f"unparseable input: {e}"}))
        sys.exit(1)

    assembled = []
    if args.self_assemble:
        t = inp.get("ticker")
        if not t:
            print(json.dumps({"error": "--self-assemble requires ticker in input"}))
            sys.exit(1)
        assembled = assemble_inputs(t, inp)

    cp = _pos(inp.get("current_price"))
    if cp is None:
        print(json.dumps({"error": "current_price required and must be > 0"}))
        sys.exit(1)
    inp["current_price"] = cp

    vol = inp.get("volatility") or {}
    if _pos(vol.get("sigma_daily")) is None and not args.no_fetch and inp.get("ticker"):
        fetched = fetch_volatility(inp["ticker"])
        merged = dict(fetched)
        merged.update({k: v for k, v in vol.items() if v is not None})
        inp["volatility"] = merged

    anchors = inp.get("anchors") or {}
    fred = inp.get("fred") or {}
    fvs = compute_fair_value_summary(anchors, cp)
    frange = compute_fair_value_range(anchors, cp, fred)
    reconcile_confidence(fvs, frange)   # confidence can't exceed anchor agreement
    out = {
        "engine": ENGINE_VERSION,
        "ticker": inp.get("ticker"),
        "fair_value_summary": fvs,
        "fair_value_range": frange,
        "multi_horizon_price_framework": compute_mhp(inp, fvs),
        "implied_expectations": compute_implied_expectations(inp),
        "valuation_archetype_shadow": compute_archetype_shadow(inp, fvs),
    }
    if assembled:
        out["self_assembled_fields"] = assembled   # audit：哪些欄位由 engine 自組（非 LLM 提供）
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()

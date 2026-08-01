#!/usr/bin/env python3
"""compute_price_framework.py — V3.45.3 deterministic price framework engine.

Computes the ENTIRE Phase 4.5 price stack in one call (0 LLM arithmetic):
  1. fair_value_summary        — 8-anchor weighted blend (V4.69.0: +dcf_self_built
                                 +comps_implied，來源 skills/valuation-modeler)
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
  "anchors": {                              # deterministic source values (prefer --self-assemble)
    "dcf_unlevered": 495.8, "dcf_levered": null, "analyst_pt_consensus": 525.0,
    "peer_pe_implied": 480.0, "owner_earnings_mult": 410.0, "forecaster_blend": null
  },
  "anchor_meta": {                          # live eligibility requires provenance + as_of
    "dcf_unlevered": {"provenance": "earnings_analyst_bundle", "as_of": "2026-07-01"}
  },
  "structural_shift": {                     # optional typed gate; incomplete = advisory only
    "status": "CONFIRMED", "evidence_date": "2026-07-15", "provenance": "filing"
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

Output: single JSON object on stdout with canonical valuation_pack + projections/advisory blocks. rc=0 even
when sub-blocks degrade to null (degradation is data, not failure); rc=1 only on
unusable input (missing current_price / unparseable JSON).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

ENGINE_VERSION = "compute_price_framework.py v2.2 (V4.76.0)"

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

# V4.72.1 (user 核准 2026-07-16) — agreement_grade 門檻改歷史 33/66 percentile。
# 原初值 0.15/0.35 把 28/30 session 判 low（歷史 cv 中位數 0.45，8 個異方法錨對
# 科技股天生散）——93% 時間亮的警示燈無資訊量。SHADOW_REPORT_2026-07-16 校準：
# n=67，P33=0.3751 / P66=0.5207。⚠ 此校準基於「修剪前」anchors；P0-3 trim 上線後
# cv 分佈會左移（NVDA 例 0.341→0.188），累積 ≥20 筆修剪後 session 需重新校準（TODO）。
AGREEMENT_GRADE_HIGH_CV = 0.375   # cv < this → high
AGREEMENT_GRADE_LOW_CV = 0.52     # cv >= this → low；中間 → medium

# V4.69.0 — 8 anchors。家族層權重不變（DCF 族 0.45 / 倍數族 0.30 / 市場預期 0.25），
# 只動族內拆分：新增 dcf_self_built（valuation-modeler 自建 driver-based DCF）與
# comps_implied（EV/EBITDA + EV/Sales + PEG implied 中位數；P/E 排除防與
# peer_pe_implied 重複計權）。兩個新 anchor 缺值時照舊重分配。
ANCHOR_WEIGHTS = {
    "dcf_unlevered": 0.20,
    "dcf_levered": 0.10,
    "dcf_self_built": 0.15,
    "analyst_pt_consensus": 0.20,
    "peer_pe_implied": 0.15,
    "comps_implied": 0.10,
    "owner_earnings_mult": 0.05,
    "forecaster_blend": 0.05,
}

# Canonical valuation topology.  Anchor-level weights above remain as legacy
# audit metadata; live aggregation happens group -> family -> portfolio so
# correlated methods do not receive independent votes.
ANCHOR_TOPOLOGY = {
    "dcf_unlevered": ("fundamental", "cashflow_intrinsic"),
    "dcf_levered": ("fundamental", "cashflow_intrinsic"),
    "dcf_self_built": ("fundamental", "cashflow_intrinsic"),
    "owner_earnings_mult": ("fundamental", "cashflow_intrinsic"),
    "forecaster_blend": ("fundamental", "earnings_projection"),
    "peer_pe_implied": ("relative", "peer_relative"),
    "comps_implied": ("relative", "peer_relative"),
    "analyst_pt_consensus": ("external_expectations", "external_pt"),
}
FAMILY_WEIGHTS = {
    "fundamental": 0.55,
    "relative": 0.25,
    "external_expectations": 0.20,
}
VALUATION_PACK_SCHEMA = "valuation_pack.v1"
PT_MAX_AGE_DAYS = 180

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

# 11-anchor 池 archetype 權重表（shadow blend 用；V4.69.0 起含 dcf_self_built /
# comps_implied 兩個 live 新 anchor）。balanced = live 權重 + shadow-only anchor 0。
# financial 的兩個新 anchor 刻意 0：FCFF DCF 對金融股無意義、comps 的 EV 指標同理。
ARCHETYPE_WEIGHTS = {
    "mature_cashflow": {
        "dcf_unlevered": 0.20, "dcf_levered": 0.10, "dcf_self_built": 0.10,
        "analyst_pt_consensus": 0.15, "peer_pe_implied": 0.10, "comps_implied": 0.05,
        "owner_earnings_mult": 0.15, "forecaster_blend": 0.05,
        "peer_ev_ebitda_implied": 0.10, "peer_ev_sales_implied": 0.0, "pb_roe_justified": 0.0,
    },
    "hypergrowth": {
        "dcf_unlevered": 0.10, "dcf_levered": 0.05, "dcf_self_built": 0.10,
        "analyst_pt_consensus": 0.20, "peer_pe_implied": 0.0, "comps_implied": 0.10,
        "owner_earnings_mult": 0.0, "forecaster_blend": 0.10,
        "peer_ev_ebitda_implied": 0.15, "peer_ev_sales_implied": 0.20, "pb_roe_justified": 0.0,
    },
    "cyclical": {
        "dcf_unlevered": 0.15, "dcf_levered": 0.10, "dcf_self_built": 0.10,
        "analyst_pt_consensus": 0.15, "peer_pe_implied": 0.10, "comps_implied": 0.05,
        "owner_earnings_mult": 0.10, "forecaster_blend": 0.05,
        "peer_ev_ebitda_implied": 0.20, "peer_ev_sales_implied": 0.0, "pb_roe_justified": 0.0,
    },
    "financial": {
        "dcf_unlevered": 0.05, "dcf_levered": 0.05, "dcf_self_built": 0.0,
        "analyst_pt_consensus": 0.30, "peer_pe_implied": 0.20, "comps_implied": 0.0,
        "owner_earnings_mult": 0.0, "forecaster_blend": 0.05,
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


def _valuation_score(vs_pct: float | None, family_values: dict) -> float | None:
    """Deterministic -3..+3 score with independent-family guard."""
    if vs_pct is None:
        return None
    if vs_pct >= 30:
        score = 3.0
    elif vs_pct >= 20:
        score = 2.0
    elif vs_pct >= 10:
        score = 1.0
    elif vs_pct <= -30:
        score = -3.0
    elif vs_pct <= -20:
        score = -2.0
    elif vs_pct <= -10:
        score = -1.0
    else:
        score = 0.0
    votes = [1 if v >= 1.10 else -1 if v <= 0.90 else 0
             for v in family_values.values()]
    same_direction = votes.count(1) if score > 0 else votes.count(-1)
    if abs(score) >= 2 and same_direction < 2:
        score = 1.0 if score > 0 else -1.0
    return score


def _stable_hash(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def _anchor_eligibility(name: str, value, meta: dict, structural_shift: dict,
                        strict_metadata: bool) -> tuple[bool, str | None]:
    if _pos(value) is None:
        return False, meta.get("reason") or "missing_or_nonpositive_value"
    provenance, as_of = meta.get("provenance"), meta.get("as_of")
    if strict_metadata and not provenance:
        return False, "missing_provenance"
    if strict_metadata and not as_of:
        return False, "missing_as_of"
    if meta.get("eligible") is False:
        return False, meta.get("reason") or "source_marked_ineligible"
    model = meta.get("model_eligibility") or {}
    if model.get("eligible") is False:
        return False, model.get("reason") or "model_ineligible"
    if name == "forecaster_blend":
        if str(meta.get("confidence") or "").upper() == "LOW":
            return False, "low_forecast_confidence"
        if _num(meta.get("usable_methods")) is not None and meta["usable_methods"] < 2:
            return False, "fewer_than_2_usable_methods"
        if meta.get("transition_case") is True:
            return False, "transition_without_safe_model"
    if name in ("peer_pe_implied", "comps_implied"):
        pc = _num(meta.get("peer_count"))
        if strict_metadata and pc is None:
            return False, "missing_peer_count"
        if pc is not None and pc < 3:
            return False, "fewer_than_3_exact_industry_peers"
    if name == "analyst_pt_consensus" and strict_metadata:
        try:
            pt_date = dt.date.fromisoformat(str(as_of)[:10])
        except (TypeError, ValueError):
            return False, "invalid_pt_as_of"
        if (dt.date.today() - pt_date).days > PT_MAX_AGE_DAYS:
            return False, "stale_analyst_pt"
    if name == "analyst_pt_consensus" and isinstance(structural_shift, dict):
        confirmed = (structural_shift.get("confirmed") is True or
                     str(structural_shift.get("status") or "").upper() == "CONFIRMED")
        evidence_date = str(structural_shift.get("evidence_date") or "")[:10]
        shift_prov = structural_shift.get("provenance")
        # Incomplete shift evidence is advisory and cannot suppress a live PT.
        if confirmed and evidence_date and shift_prov and as_of:
            if str(as_of)[:10] <= evidence_date:
                return False, "predates_structural_shift"
    return True, None


def build_valuation_pack(anchors: dict, current_price: float, *,
                         anchor_meta: dict | None = None,
                         structural_shift: dict | None = None,
                         strict_metadata: bool = True) -> dict:
    """Build the single authoritative valuation result for a session."""
    anchor_meta = anchor_meta or {}
    structural_shift = structural_shift or {}
    entries = {}
    grouped: dict[str, dict[str, list[float]]] = {}
    group_members: dict[str, list[str]] = {}
    for name in ANCHOR_WEIGHTS:
        value = _pos((anchors or {}).get(name))
        meta = dict(anchor_meta.get(name) or {})
        family, base_group = ANCHOR_TOPOLOGY[name]
        assumption_inputs = meta.get("assumption_inputs")
        assumption_hash_inputs = {
            "as_of": meta.get("as_of"),
            "provenance": meta.get("provenance"),
            "inputs": assumption_inputs,
        }
        # Legacy pure-function callers have no metadata. Preserve their former
        # per-anchor behavior without weakening live strict-mode correlation.
        if not strict_metadata:
            assumption_hash_inputs["legacy_anchor"] = name
        assumption_set_id = meta.get("assumption_set_id") or _stable_hash(assumption_hash_inputs)
        # Explicit lineage lets sibling anchors share a group; otherwise the
        # fixed mapping supplies the conservative correlation bucket.
        lineage_group = meta.get("correlation_key")
        correlation_group = f"{base_group}:{lineage_group or assumption_set_id}"
        eligible, reason = _anchor_eligibility(
            name, value, meta, structural_shift, strict_metadata,
        )
        status = "eligible" if eligible else "ineligible"
        entries[name] = {
            "value": value,
            "family": family,
            "correlation_group": correlation_group,
            "assumption_set_id": assumption_set_id,
            "provenance": meta.get("provenance"),
            "as_of": meta.get("as_of"),
            "input_lineage_ids": meta.get("input_lineage_ids") or [],
            "status": status,
            "reason": reason,
            "weight_raw": ANCHOR_WEIGHTS[name],
            "weight_effective": 0.0,
            "projection_mode": meta.get("projection_mode"),
            "sensitivity_low": _pos(meta.get("sensitivity_low")),
            "sensitivity_high": _pos(meta.get("sensitivity_high")),
        }
        if eligible:
            grouped.setdefault(family, {}).setdefault(correlation_group, []).append(value)
            group_members.setdefault(correlation_group, []).append(name)

    families = {}
    for family, groups in grouped.items():
        reps = {group: median(values) for group, values in groups.items()}
        families[family] = {
            "groups": {g: {"value": round(v, 2), "members": group_members[g]}
                       for g, v in reps.items()},
            "representative": median(list(reps.values())),
            "weight_raw": FAMILY_WEIGHTS[family],
            "weight_effective": 0.0,
        }

    covered_weight = sum(FAMILY_WEIGHTS[f] for f in families)
    if families:
        # Complete coverage uses configured weights.  In a degraded 1/2-family
        # case, missing-family weight is not transferred to a particular
        # survivor; each independent family gets one equal vote instead.
        complete = len(families) == len(FAMILY_WEIGHTS)
        for family, detail in families.items():
            detail["weight_effective"] = (
                FAMILY_WEIGHTS[family] if complete else 1.0 / len(families)
            )
        family_fair_value = sum(d["representative"] * d["weight_effective"]
                                for d in families.values())
    else:
        family_fair_value = None
    for family, detail in families.items():
        family_share = detail["weight_effective"]
        groups_n = max(len(detail["groups"]), 1)
        for group, gd in detail["groups"].items():
            member_share = family_share / groups_n / max(len(gd["members"]), 1)
            for name in gd["members"]:
                entries[name]["weight_effective"] = round(member_share, 6)

    # A validated structural-shift DCF is the primary intrinsic-value answer.
    # Other independent methods explain the range; they do not average the
    # through-cycle model away into a synthetic price no method actually owns.
    dcf_entry = entries.get("dcf_self_built") or {}
    dcf_primary = (dcf_entry.get("status") == "eligible" and
                   dcf_entry.get("projection_mode") == "structural_shift_through_cycle")
    if dcf_primary:
        fair_value = dcf_entry["value"]
        for entry in entries.values():
            entry["weight_effective"] = 0.0
        dcf_entry["weight_effective"] = 1.0
    else:
        fair_value = family_fair_value

    fv = round(fair_value, 2) if fair_value is not None else None
    vs_pct = ((fair_value - current_price) / current_price * 100
              if fair_value is not None else None)
    family_ratios = {f: d["representative"] / current_price for f, d in families.items()}
    score = _valuation_score(vs_pct, family_ratios)
    family_count = len(families)
    confidence = "high" if family_count == 3 else "medium" if family_count == 2 else "low"
    return {
        "schema": VALUATION_PACK_SCHEMA,
        "engine": ENGINE_VERSION,
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "current_price": current_price,
        "anchors": entries,
        "families": families,
        "families_present": sorted(families),
        "family_coverage_weight": round(covered_weight, 4),
        "aggregation_mode": ("dcf_primary_anchor_range" if dcf_primary
                             else "complete_fixed_family_weights" if len(families) == 3
                             else "degraded_equal_family_votes" if families else "unavailable"),
        "primary_method": "dcf_self_built" if dcf_primary else "family_aggregation",
        "family_blended_fair_value": (round(family_fair_value, 2)
                                      if family_fair_value is not None else None),
        "weighted_fair_value": fv,
        "vs_current_pct": round(vs_pct, 2) if vs_pct is not None else None,
        "verdict_band": _verdict_band(vs_pct) if vs_pct is not None else None,
        "score": score,
        "confidence": confidence,
        "structural_shift": structural_shift,
    }


# ── Block 1: fair_value_summary — projection of canonical valuation_pack ────
def fair_value_summary_from_pack(pack: dict) -> dict:
    eligible = {k: v for k, v in pack["anchors"].items() if v["status"] == "eligible"}
    excluded = {k: v["reason"] for k, v in pack["anchors"].items()
                if v["status"] != "eligible"}
    return {
        "anchors": {k: v["value"] for k, v in pack["anchors"].items()},
        "anchors_effective": {
            k: v["value"] if v["status"] == "eligible" else None
            for k, v in pack["anchors"].items()
        },
        "weights_used": {k: v["weight_effective"] for k, v in eligible.items()},
        "weighted_fair_value": pack["weighted_fair_value"],
        "current_price": pack["current_price"],
        "vs_current_pct": pack["vs_current_pct"],
        "verdict_band": pack["verdict_band"],
        "score": pack["score"],
        "confidence": pack["confidence"],
        "anchors_available": len(eligible),
        "families_present": pack["families_present"],
        "family_coverage_weight": pack["family_coverage_weight"],
        "excluded_anchors": excluded,
        "valuation_pack_schema": pack["schema"],
        "primary_method": pack.get("primary_method"),
        "family_blended_fair_value": pack.get("family_blended_fair_value"),
        "methodology_note": (
            f"{'DCF primary with anchor range' if pack.get('primary_method') == 'dcf_self_built' else 'canonical family aggregation'}; "
            f"mode={pack.get('aggregation_mode')}; {len(eligible)}/{len(ANCHOR_WEIGHTS)} anchors; "
            f"families={','.join(pack['families_present']) or 'none'}"
        ),
    }


def build_explained_valuation_range(pack: dict, scenarios: dict | None = None) -> dict:
    """DCF-primary interval with explicit no-peer / with-peer scenario points."""
    scenarios = scenarios or {}
    dcf = (pack.get("anchors") or {}).get("dcf_self_built") or {}
    if pack.get("primary_method") != "dcf_self_built" or dcf.get("status") != "eligible":
        return {"available": False, "reason": "no_eligible_structural_dcf_primary"}

    primary = dcf.get("value")
    fundamental = ((pack.get("families") or {}).get("fundamental") or {}).get("representative")
    without_peer = round(fundamental, 2) if _pos(fundamental) else primary
    peer = scenarios.get("peer_pe_range") or {}
    peer_value = _pos(peer.get("value")) if peer.get("eligible") else None
    with_peer = round((without_peer + peer_value) / 2, 2) if peer_value else None
    other_eligible = {
        name: entry.get("value")
        for name, entry in (pack.get("anchors") or {}).items()
        if name != "dcf_self_built" and entry.get("status") == "eligible"
        and _pos(entry.get("value"))
    }
    sensitivity_low = dcf.get("sensitivity_low") or primary
    sensitivity_high = dcf.get("sensitivity_high") or primary
    named_points = {
        "dcf_sensitivity_low": sensitivity_low,
        "dcf_primary": primary,
        "fundamental_without_peer": without_peer,
        "dcf_sensitivity_high": sensitivity_high,
    }
    if with_peer:
        named_points["two_family_with_peer"] = with_peer
    named_points.update({f"anchor:{name}": value for name, value in other_eligible.items()})
    named_points = {name: value for name, value in named_points.items() if _pos(value)}
    range_low_driver = min(named_points, key=named_points.get)
    range_high_driver = max(named_points, key=named_points.get)
    return {
        "available": True,
        "primary_fv": primary,
        "primary_method": "structural_shift_through_cycle_dcf",
        "primary_sensitivity": {
            "low": round(sensitivity_low, 2), "high": round(sensitivity_high, 2),
        },
        "scenario_without_peer": without_peer,
        "scenario_with_peer": with_peer,
        "peer_pe_range_anchor": peer_value,
        "range_low": round(named_points[range_low_driver], 2),
        "range_high": round(named_points[range_high_driver], 2),
        "range_low_driver": range_low_driver,
        "range_high_driver": range_high_driver,
        "peer_scope": peer.get("scope"),
        "peer_count": peer.get("peer_count", 0),
        "peer_symbols": sorted((peer.get("peers") or {}).keys()),
        "other_eligible_anchors": other_eligible,
        "interpretation": (
            f"DCF is the primary FV; low={range_low_driver}; high={range_high_driver}. "
            "Range-only peers explain a scenario and never replace the primary."
        ),
        "limitations": peer.get("limitations") or [],
    }


def compute_fair_value_summary(anchors: dict, current_price: float) -> dict:
    """Backward-compatible pure-function entry; uses the canonical builder."""
    pack = build_valuation_pack(anchors, current_price, strict_metadata=False)
    return fair_value_summary_from_pack(pack)


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
        grade = None if cv is None else (
            "high" if cv < AGREEMENT_GRADE_HIGH_CV
            else "medium" if cv < AGREEMENT_GRADE_LOW_CV else "low")
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


# ── V4.70.0 — anchor outlier trim (P0-3 audit fix) ───────────────────────────
# 審計實證（AUDIT_2026-07-16）：owner_earnings×15 對高成長 archetype 產出如 NVDA
# $31.80（vs 錨中位數 $258）仍以 0.05 權重進 weighted_fair_value，anchors 離散 11.6x
# 照樣加權。修剪規則刻意相對「錨共識」而非相對現價：全體 anchors 一致偏低（真高估）
# 時中位數同步下移，不會誤剪。
TRIM_MIN_ANCHORS = 4          # n<4 不修剪（樣本太少，中位數不穩）
TRIM_FACTOR = 3.0             # 錨值落在 [median/3, median×3] 之外 → 剔除
TRIM_KEEP_FLOOR = 2           # 修剪後剩餘 <2 錨 → 放棄修剪（避免自砍到無法估值）


def trim_anchor_outliers(anchors: dict) -> tuple:
    """Drop anchors wildly inconsistent with the anchor-consensus median.

    Returns (anchors_effective, trimmed_log). anchors_effective 與輸入同 shape，
    被剔除的 anchor 置 None（下游 weight 重分配照舊機制走）。不修改輸入 dict。
    """
    avail = {k: _pos(anchors.get(k)) for k in ANCHOR_WEIGHTS}
    avail = {k: v for k, v in avail.items() if v is not None}
    if len(avail) < TRIM_MIN_ANCHORS:
        return dict(anchors), []
    med = median(list(avail.values()))
    lo, hi = med / TRIM_FACTOR, med * TRIM_FACTOR
    out_keys = [k for k, v in avail.items() if not (lo <= v <= hi)]
    if not out_keys or len(avail) - len(out_keys) < TRIM_KEEP_FLOOR:
        return dict(anchors), []
    eff = dict(anchors)
    trimmed = []
    for k in out_keys:
        trimmed.append({
            "anchor": k, "value": avail[k],
            "reason": f"outside [{lo:.2f}, {hi:.2f}] (median {med:.2f} × 1/{TRIM_FACTOR:g}..{TRIM_FACTOR:g})",
        })
        eff[k] = None
    return eff, trimmed


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
    anchors = fvs.get("anchors_effective") or fvs["anchors"]
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
            payload = json.load(f)
        if isinstance(payload, dict):
            payload["_cache_path"] = files[-1]
        return payload
    except Exception:
        return None


def _block_manual_anchor_overrides(inp: dict) -> list[str]:
    """Remove input-file values/meta for engine-owned live anchors.

    Qualitative lane inputs may still come from an LLM, but live valuation anchors
    are authoritative only when reassembled from deterministic cache/API sources.
    """
    anchors = inp.setdefault("anchors", {})
    anchor_meta = inp.setdefault("anchor_meta", {})
    blocked = []
    for name in ANCHOR_WEIGHTS:
        supplied = anchors.get(name) is not None or bool(anchor_meta.get(name))
        if supplied:
            blocked.append(name)
        anchors[name] = None
        anchor_meta[name] = {}
    inp["blocked_anchor_overrides"] = blocked
    return blocked


def _supersede_vendor_dcf(anchor_meta: dict, dcf_payload: dict) -> list[str]:
    """Demote opaque vendor DCFs when the auditable shift model is live.

    Values and lineage remain in the pack for audit.  They simply stop casting
    duplicate cash-flow votes after a structurally normalized self-built DCF
    passes its own eligibility gate.
    """
    model = dcf_payload.get("model_eligibility") or {}
    mode = ((dcf_payload.get("dcf") or {}).get("projection_mode") or
            dcf_payload.get("projection_mode"))
    if model.get("eligible") is not True or mode != "structural_shift_through_cycle":
        return []
    superseded = []
    for name in ("dcf_unlevered", "dcf_levered"):
        meta = anchor_meta.setdefault(name, {})
        meta["eligible"] = False
        meta["reason"] = "superseded_by_auditable_through_cycle_dcf"
        meta["superseded_by"] = "dcf_self_built"
        superseded.append(name)
    return superseded


def assemble_inputs(ticker: str, inp: dict, *, authoritative_anchors: bool = False) -> list:
    """Fill missing fields from deterministic sources.

    With ``authoritative_anchors=True`` (the CLI ``--self-assemble`` path), all
    engine-owned anchor values and metadata from the input file are discarded
    before assembly so an LLM cannot inject a live valuation number.
    Returns list of assembled field paths（audit 用）。

    來源：earnings-analyst cache（DCF/PT/EV/archetype 原料）、FMP quote（price/epsTTM）、
    phase1_factpack peer bundle（peer medians + self ratios + beta）、fmp_supplementary
    （owner earnings per share）、valuation-modeler payloads、forecaster cache，並為每個
    anchor 寫入 provenance/as_of/eligibility。nominal 10Y 直接重用 valuation-modeler
    的 FRED cache adapter。
    """
    import glob as _glob
    filled = []

    if authoritative_anchors:
        blocked = _block_manual_anchor_overrides(inp)
        filled.extend(f"blocked_anchor_override.{name}" for name in blocked)

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

    def _meta(anchor: str, **values):
        block = inp.setdefault("anchor_meta", {}).setdefault(anchor, {})
        for key, value in values.items():
            if value is not None and block.get(key) is None:
                block[key] = value

    today = dt.date.today().isoformat()

    ec = _latest_earnings_cache(ticker) or {}
    val = ec.get("valuation") or {}
    _fill("anchors.dcf_unlevered", _pos(val.get("dcf_intrinsic")))
    _fill("anchors.dcf_levered", _pos(val.get("dcf_levered_intrinsic")))
    _fill("anchors.analyst_pt_consensus", _pos(val.get("price_target_consensus")))
    earnings_asof = ec.get("last_earnings_date") or ec.get("as_of_date")
    earnings_lineage = f"earnings_analyst:{ticker.upper()}:{earnings_asof or 'unknown'}"
    for name in ("dcf_unlevered", "dcf_levered"):
        _meta(name, provenance="earnings_analyst_bundle", as_of=earnings_asof,
              correlation_key=earnings_lineage, input_lineage_ids=[earnings_lineage])
    pt_dates = [str(row.get("publishedDate"))[:10] for row in (val.get("pt_news") or [])
                if isinstance(row, dict) and row.get("publishedDate")]
    pt_asof = max(pt_dates) if pt_dates else None
    _meta("analyst_pt_consensus", provenance="earnings_analyst_bundle.pt_news",
          as_of=pt_asof, correlation_key=f"analyst_pt:{ticker.upper()}:{pt_asof or 'unknown'}",
          input_lineage_ids=[f"analyst_pt:{ticker.upper()}:{pt_asof or 'unknown'}"])
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
                peer_ids = sorted(pb.get("peers") or [])
                peer_key = f"peers:{_stable_hash(peer_ids)}:{today}"
                _meta("peer_pe_implied", provenance=pb.get("peer_selector") or "peer_bundle",
                      as_of=today, peer_count=len(peer_ids), correlation_key=peer_key,
                      input_lineage_ids=peer_ids)
            _fill("peer_ratios.peer_ev_ebitda_median", _pos(pb.get("peer_ev_ebitda_median")))
            _fill("peer_ratios.peer_ev_sales_median", _pos(pb.get("peer_ev_sales_median")))
            _fill("peer_ratios.peer_pb_median", _pos(pb.get("peer_pb_median")))
            for k in ("ev_to_ebitda_ttm", "ev_to_sales_ttm", "roe_ttm", "book_value_per_share_ttm"):
                _fill(f"self_ratios.{k}", _num(sr.get(k)))
        pb_range = pb.get("range_peer_scenario") or {}
        if pb_range.get("eligible") and _pos(pb_range.get("value")):
            inp.setdefault("valuation_scenarios", {})["peer_pe_range"] = pb_range
            filled.append("valuation_scenarios.peer_pe_range")
        from skills._shared.company_context import get_profile
        prof = get_profile(ticker) or {}
        _fill("beta", _num(prof.get("beta")))
    except Exception:
        pass

    # valuation-modeler payloads are first-class deterministic anchor inputs.
    vm_cache = os.path.join(BASE_DIR, "skills", "valuation-modeler", "cache")
    dcf_path = os.path.join(vm_cache, f"{ticker.upper()}_dcf_payload.json")
    if os.path.exists(dcf_path):
        try:
            with open(dcf_path, encoding="utf-8") as f:
                dcf_payload = json.load(f)
            _fill("anchors.dcf_self_built", _pos(dcf_payload.get("fair_value_per_share")))
            model = dcf_payload.get("model_eligibility") or {}
            _meta("dcf_self_built", provenance="valuation_modeler.dcf",
                  as_of=dcf_payload.get("asof"), model_eligibility=model,
                  eligible=model.get("eligible"), reason=model.get("reason"),
                  projection_mode=(dcf_payload.get("dcf") or {}).get("projection_mode"),
                  sensitivity_low=min(
                      (v for row in (dcf_payload.get("sensitivity") or {}).get("grid", [])
                       for v in row if _pos(v)), default=None),
                  sensitivity_high=max(
                      (v for row in (dcf_payload.get("sensitivity") or {}).get("grid", [])
                       for v in row if _pos(v)), default=None),
                  correlation_key=f"dcf_self:{ticker.upper()}:{dcf_payload.get('asof')}",
                  input_lineage_ids=[os.path.relpath(dcf_path, BASE_DIR)])
            superseded = _supersede_vendor_dcf(inp.setdefault("anchor_meta", {}), dcf_payload)
            filled.extend(f"superseded_anchor.{name}" for name in superseded)
        except Exception:
            pass
    comps_path = os.path.join(vm_cache, f"{ticker.upper()}_comps_payload.json")
    if os.path.exists(comps_path):
        try:
            with open(comps_path, encoding="utf-8") as f:
                comps_payload = json.load(f)
            universe = comps_payload.get("universe") or {}
            model = comps_payload.get("model_eligibility") or {}
            _fill("anchors.comps_implied", _pos(comps_payload.get("comps_implied_value")))
            peer_ids = sorted((universe.get("peers") or {}).keys())
            _meta("comps_implied", provenance="valuation_modeler.comps",
                  as_of=comps_payload.get("asof"), model_eligibility=model,
                  eligible=model.get("eligible"), reason=model.get("reason"),
                  peer_count=universe.get("peer_count_used"),
                  correlation_key=f"peers:{_stable_hash(peer_ids)}:{comps_payload.get('asof')}",
                  input_lineage_ids=[os.path.relpath(comps_path, BASE_DIR), *peer_ids])
            range_scenario = comps_payload.get("peer_pe_range_scenario") or {}
            if range_scenario.get("eligible") and _pos(range_scenario.get("value")):
                inp.setdefault("valuation_scenarios", {})["peer_pe_range"] = range_scenario
                filled.append("valuation_scenarios.peer_pe_range")
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
            owner_asof = supp.get("as_of") or supp.get("generated_at") or today
            _meta("owner_earnings_mult", provenance="fmp_supplementary.owner_earnings",
                  as_of=str(owner_asof)[:10],
                  correlation_key=f"owner_earnings:{ticker.upper()}:{str(owner_asof)[:10]}",
                  input_lineage_ids=[f"owner_earnings:{ticker.upper()}:{str(owner_asof)[:10]}"])
    except Exception:
        pass

    # forecaster cache（不 subprocess 跑 — 只讀 cache；缺/stale → null）
    fc_path = os.path.join(BASE_DIR, "skills", "earnings-valuation-forecaster", "cache",
                           f"{ticker.upper()}.json")
    if os.path.exists(fc_path):
        try:
            with open(fc_path, encoding="utf-8") as f:
                fc = json.load(f)
            _fill("anchors.forecaster_blend", _pos(fc.get("expected_value")))
            live = fc.get("live_eligibility") or {}
            methods = (fc.get("forward_eps") or {}).get("methods") or {}
            usable_methods = sum(
                1 for key in ("cagr", "consensus", "trend")
                if _pos(methods.get(key)) is not None
            )
            transition = (fc.get("transition_case") or {}).get("transition_case") is True
            _meta("forecaster_blend", provenance="earnings_valuation_forecaster",
                  as_of=str(fc.get("generated_at") or "")[:10] or None,
                  confidence=(fc.get("forward_eps") or {}).get("confidence"),
                  usable_methods=live.get("usable_methods") if live else usable_methods,
                  transition_case=transition,
                  eligible=live.get("eligible") if live else None,
                  reason=",".join(live.get("reasons") or []) or None,
                  correlation_key=f"forecaster:{ticker.upper()}:{str(fc.get('generated_at') or '')[:10]}",
                  input_lineage_ids=[os.path.relpath(fc_path, BASE_DIR)])
        except Exception:
            pass

    # phase0 snapshot: real rate
    p0 = sorted(_glob.glob(os.path.join(BASE_DIR, "investment", "invest_logs", "*phase0*.json")))
    if p0:
        try:
            with open(p0[-1], encoding="utf-8") as f:
                rr = _num((json.load(f).get("fred_snapshot") or {}).get("real_rate_preferred"))
            if rr is not None:
                _fill("fred.treasury_10y_real", rr / 100.0)
        except Exception:
            pass

    # Nominal 10Y for reverse DCF: same FRED cache adapter used by dcf.py.
    try:
        vm_scripts = os.path.join(BASE_DIR, "skills", "valuation-modeler", "scripts")
        if vm_scripts not in sys.path:
            sys.path.insert(0, vm_scripts)
        import fmp_client as vm_fmp_client
        rf, rf_source = vm_fmp_client.risk_free_rate()
        if rf_source and str(rf_source).startswith("fred"):
            _fill("fred.treasury_10y", _num(rf))
            _fill("fred.treasury_10y_source", rf_source)
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
        assembled = assemble_inputs(t, inp, authoritative_anchors=True)

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

    anchors_raw = inp.get("anchors") or {}
    fred = inp.get("fred") or {}
    # Median outlier detection remains diagnostic only.  A correlated majority
    # must not be allowed to erase a legitimate dissenting valuation method.
    _, outlier_diagnostics = trim_anchor_outliers(anchors_raw)
    pack = build_valuation_pack(
        anchors_raw, cp,
        anchor_meta=inp.get("anchor_meta") or {},
        structural_shift=inp.get("structural_shift") or {},
        strict_metadata=True,
    )
    effective_anchors = {
        name: detail["value"] if detail["status"] == "eligible" else None
        for name, detail in pack["anchors"].items()
    }
    fvs = fair_value_summary_from_pack(pack)
    frange = compute_fair_value_range(effective_anchors, cp, fred)
    reconcile_confidence(fvs, frange)
    pack["confidence"] = fvs["confidence"]
    if outlier_diagnostics:
        pack["outlier_diagnostics"] = outlier_diagnostics
        fvs["outlier_diagnostics"] = outlier_diagnostics
    inp_effective = dict(inp)
    inp_effective["anchors"] = effective_anchors
    out = {
        "engine": ENGINE_VERSION,
        "ticker": inp.get("ticker"),
        "valuation_pack": pack,
        "fair_value_summary": fvs,
        "fair_value_range": frange,
        "multi_horizon_price_framework": compute_mhp(inp_effective, fvs),
        "implied_expectations": compute_implied_expectations(inp),
        "valuation_archetype_shadow": compute_archetype_shadow(inp, fvs),
        "valuation_explained_range": build_explained_valuation_range(
            pack, inp.get("valuation_scenarios") or {}),
    }
    if assembled:
        out["self_assembled_fields"] = assembled   # audit：哪些欄位由 engine 自組（非 LLM 提供）
    if inp.get("blocked_anchor_overrides"):
        out["blocked_anchor_overrides"] = inp["blocked_anchor_overrides"]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()

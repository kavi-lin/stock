#!/usr/bin/env python3
"""decision_engine.py — V4.80.0 deterministic Phase 3 decision engine (0 LLM arithmetic).

Computes the ENTIRE Phase 3 decision stack in one call:
  Step 1   — weighted raw_total with V4.70.0 three-tier C_eff quantisation
  Step 1.5 — structural-shift modulation (shift_macro_floor / position cap / mr block)
  Step 1.7 — lane polarization modulation (imports apply_det_shadow.compute_polarization)
  Step 2   — Red-Team-gated bonus / 5-level priority penalty cascade (first match wins)
  Step 3   — directional macro multiplier (ALIGNED × mult / CONTRARIAN passthrough)
  Step 4   — V2.20.0 dynamic threshold + decision band
  Rec 11   — hot-zone probe judgment tree + tier split (TODO-001/002/015)
  Gates    — Auto REJECT hard gates, applied above the probe exception

Plus a SEPARATE entry point for Phase 4.6 decision cap (`apply_decision_cap`), which
runs after Phase 4 sizing — see `--phase 4.6`.

Why a script: Phase 3 is pure arithmetic with branch precedence an LLM cannot execute
reliably inline (three-tier C_eff, 5-level cascade, 4-tier polarization × threshold
matrix, probe judgment tree, hard-gate ordering). Protocol discipline is「數字全走
script 禁手算」— this engine is the execution authority; the protocol prose is the spec.

Single source of truth: polarization and Red Team basis are IMPORTED from
`apply_det_shadow.py` — never re-implemented here.

Usage:
  python3 investment/scripts/decision_engine.py --from-file /tmp/<T>_p3.json
  cat p3.json | python3 investment/scripts/decision_engine.py
  python3 investment/scripts/decision_engine.py --phase 4.6 --from-file /tmp/<T>_p46.json

Phase 3 input JSON shape (qualitative fields — institutional_lens / scenario_odds /
action_label — stay with the PM and are NOT engine inputs):
{
  "ticker": "MU",
  "lane_scores":     {"fundamentals": 1.5, "sentiment": -0.04, "news": -0.5, "technical": -2.5},
  "lane_confidence": {"fundamentals": 0.6, "sentiment": 0.55, "news": 0.6,
                      "technical": 0.7, "valuation": 0.62},
  "valuation_lane":  {"score": -1.5, "confidence": 0.62},   # score also accepted here
  "weights": null,                                          # optional override of defaults
  "structural_shift": {"tier": "CONFIRMED"},                # NONE|CANDIDATE|CONFIRMED|INSUFFICIENT_DATA|null
  "red_team": {
    "verdict": "STRONG_COUNTER",                            # NO_VIABLE_COUNTER|MODERATE_COUNTER|STRONG_COUNTER
    "counter_thesis": "…", "kill_conditions": ["…"],        # classifier haystack
    "basis": null,                                          # optional override of classifier
    "counter_evidence_strength": 5,                         # int 1-5 (rule 4 grading)
    "thesis_break_probability": 0.68                        # recorded only, never in decision math
  },
  "transition": {                                           # V3.17 rule-2 inputs (all optional)
    "transition_signature": "mix_only",                     # mix_only|both|margin_only|none|null
    "transition_signature_mtime": "2026-08-02T04:00:00",
    "forecaster_transition_case": true,
    "forecaster_transition_case_mtime": "2026-08-02T05:00:00",
    "valuation_cited_transition_overlay": true,
    "valuation_transition_dissent_basis": "peer_multiple"
  },
  "macro": {"macro_multiplier": 0.9, "macro_backdrop_score": 0.5, "market_regime": "SIDEWAYS"},
  "burry": {"score": 37.1, "veto_flag": false},
  "gates": {
    "proceed_to_phase3": true, "risk_reward_ratio": 2.4,
    "binary_classification": "positive", "binary_event_within_48h": false,
    "mandatory_risk_flags": [], "phase2_fanout_mode": "PARALLEL_SUBAGENT"
  },
  "hot_zone": {"industry_top_30pct": true},
  "decision_cap": {"anchors_available": 5, "fair_value_confidence": "medium",
                   "lane_data_quality_low": false}
}

Output: single JSON object on stdout carrying the full `calculation_steps` block the
PM copies verbatim into the Phase 5 export. rc=0 on success, rc=1 on unusable input.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_det_shadow import (  # noqa: E402
    classify_red_team_basis,
    compute_polarization,
)

ENGINE_VERSION = "1.0.0"
ENGINE_LABEL = f"decision_engine.py v{ENGINE_VERSION} (V4.80.0)"

LANE_KEYS = ("fundamentals", "sentiment", "news", "technical", "valuation")
LANE_LABELS = {"fundamentals": "Fundamentals", "sentiment": "Sentiment",
               "news": "News", "technical": "Technical", "valuation": "Valuation"}
STEP1_KEYS = {"fundamentals": "fund", "sentiment": "sent", "news": "news",
              "technical": "tech", "valuation": "val"}
DEFAULT_WEIGHTS = {"fundamentals": 0.25, "sentiment": 0.15, "news": 0.20,
                   "technical": 0.25, "valuation": 0.15}

# Step 1.7 exception + Rec 11 regime guard use the same verified-bull regime set.
BULL_REGIMES = ("RISK_ON", "BULL")

CAP_REASONS = ("insufficient_anchors", "low_valuation_confidence", "low_data_quality")


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _num(x: Any) -> str:
    """Compact number rendering for the calculation_steps strings (1.5 not 1.50).

    Never emits scientific notation — the step strings are re-parsed by the validator
    and the replay harness, and `4e-05` would read as unparseable.
    """
    if isinstance(x, float) and x == int(x):
        return str(int(x))
    return f"{x:.10f}".rstrip("0")


def _f(x: Any) -> float | None:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return float(x)


def _sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def _parse_ts(v: Any) -> float | None:
    """Accept epoch seconds or ISO 8601 string; return epoch seconds."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and v.strip():
        import datetime as _dt
        try:
            return _dt.datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def c_eff(raw_conf: float | None) -> float | None:
    """V4.70.0 P0-4 — three-tier confidence quantisation used by decision math only.

    Centres come from the measured historical distribution (scale-preserving, so
    buy_threshold needs no recalibration). Raw confidence still ships in the export.
    """
    if raw_conf is None:
        return None
    if raw_conf < 0.45:
        return 0.35
    if raw_conf < 0.675:
        return 0.60
    return 0.72


# ---------------------------------------------------------------------------
# Step 1 — weighted raw total
# ---------------------------------------------------------------------------

def compute_step1(lane_scores: dict, lane_conf: dict, weights: dict) -> dict:
    """Returns {steps:{fund..val}, raw_total, missing_lanes, c_eff_used, avg_confidence_raw}."""
    steps: dict[str, Any] = {}
    total = 0.0
    missing: list[str] = []
    ce_used: dict[str, float] = {}
    raw_confs: list[float] = []

    for lane in LANE_KEYS:
        w = weights[lane]
        s = _f(lane_scores.get(lane))
        rc = _f(lane_conf.get(lane))
        key = STEP1_KEYS[lane]
        if s is None:
            missing.append(lane)
            steps[key] = f"{w:.2f} × MISSING = 0.0000  // lane score absent, weight NOT redistributed"
            continue
        if rc is None:
            missing.append(f"{lane}:confidence")
            steps[key] = f"{w:.2f} × {_num(s)} × MISSING = 0.0000  // lane confidence absent"
            continue
        raw_confs.append(rc)
        ce = c_eff(rc)
        ce_used[lane] = ce
        contrib = w * s * ce
        total += contrib
        steps[key] = f"{w:.2f} × {_num(s)} × {ce:.2f} = {contrib:.4f}"

    return {
        "steps": steps,
        "raw_total": total,
        "missing_lanes": missing,
        "c_eff_used": ce_used,
        "avg_confidence_raw": (sum(raw_confs) / len(raw_confs)) if raw_confs else None,
    }


# ---------------------------------------------------------------------------
# Step 1.5 — structural shift modulation
# ---------------------------------------------------------------------------

def compute_step1_5(tier: str | None) -> dict:
    t = (tier or "NONE").upper()
    if t == "CONFIRMED":
        return {
            "tier": "CONFIRMED",
            "applied_adjustments": [
                "Red Team mean-reversion attack BLOCKED (cascade rule #1 downgrades mr/contaminated STRONG_COUNTER)",
                "shift_macro_floor = 1.00 (sector_avoid 對個股失效)",
                "position_size_cap_pct = 100",
            ],
            "shift_macro_floor": 1.00,
            "position_size_cap_pct": 100,
            "red_team_mean_reversion_blocked": True,
        }
    if t == "CANDIDATE":
        return {
            "tier": "CANDIDATE",
            "applied_adjustments": [
                "Red Team STRONG_COUNTER penalty 折半 (0.85 → 0.925, cascade rule #3)",
                "shift_macro_floor = 0.95",
                "position_size_cap_pct = 50 (強制半倉)",
            ],
            "shift_macro_floor": 0.95,
            "position_size_cap_pct": 50,
            "red_team_mean_reversion_blocked": False,
        }
    return {
        "tier": tier if tier in ("NONE", "INSUFFICIENT_DATA") else (tier or None),
        "applied_adjustments": ["no modulation — standard rules apply"],
        "shift_macro_floor": 0.0,
        "position_size_cap_pct": 100,
        "red_team_mean_reversion_blocked": False,
    }


# ---------------------------------------------------------------------------
# Step 1.7 — lane polarization modulation
# ---------------------------------------------------------------------------

def _outlier_lane_id(lane_scores: dict, val_score: float | None) -> str | None:
    """Which lane sits on the minority side (label only; never enters decision math)."""
    pairs = []
    for lane in LANE_KEYS:
        s = _f(val_score) if lane == "valuation" else _f(lane_scores.get(lane))
        if s is not None:
            pairs.append((lane, s))
    pos = [p for p in pairs if p[1] > 0]
    neg = [p for p in pairs if p[1] < 0]
    if not pos or not neg:
        return None
    if len(pos) != len(neg):
        minority = pos if len(pos) < len(neg) else neg
    else:
        pos_strong = sum(1 for _, s in pos if s >= 1.0)
        neg_strong = sum(1 for _, s in neg if s <= -1.0)
        if pos_strong != neg_strong:
            minority = pos if pos_strong < neg_strong else neg
        else:
            # last tie-break: the side whose extreme is smaller in magnitude
            minority = pos if max(abs(s) for _, s in pos) <= max(abs(s) for _, s in neg) else neg
    best = max(minority, key=lambda p: (abs(p[1]), -LANE_KEYS.index(p[0])))
    return LANE_LABELS[best[0]]


def compute_step1_7(lane_scores: dict, val_score: float | None,
                    shift_tier: str | None, market_regime: str | None) -> dict:
    """4-tier polarization → confidence multiplier + polar position cap + band rule."""
    detail = compute_polarization(lane_scores, val_score)
    label = detail.get("label")
    adjustments: list[str] = []
    mult = 1.0
    cap = 100
    force_buy_downgrade = False

    if label == "BIPOLAR":
        bull = (market_regime or "").upper() in BULL_REGIMES
        if (shift_tier or "").upper() == "CONFIRMED" and bull:
            mult = 0.7
            adjustments.append(
                "BIPOLAR 例外：structural_shift=CONFIRMED + bull regime → avg_confidence × 0.7")
        else:
            mult = 0.5
            adjustments.append("avg_confidence × 0.5")
        cap = 25
        force_buy_downgrade = True
        adjustments.append("position_size_cap_pct = min(cap, 25)")
        adjustments.append("decision band: BUY → STAGED_ENTRY 強制降階")
    elif label == "OUTLIER":
        mult = 0.85
        adjustments.append("avg_confidence × 0.85")
        adjustments.append("position cap 不動")
    elif label == "MIXED":
        mult = 0.75
        adjustments.append("avg_confidence × 0.75")
        adjustments.append("position cap 不動")
    elif label == "ALIGNED":
        adjustments.append("no modulation")
    else:
        adjustments.append(
            f"polarization unavailable ({detail.get('reason')}) — no modulation applied")

    return {
        "label": label,
        "lane_range": detail.get("range"),
        "pos_strong": detail.get("pos_strong"),
        "neg_strong": detail.get("neg_strong"),
        "outlier_lane_id": _outlier_lane_id(lane_scores, val_score) if label == "OUTLIER" else None,
        "applied_adjustments": adjustments,
        "confidence_multiplier": mult,
        "position_cap_after": cap,
        "force_buy_downgrade": force_buy_downgrade,
        "missing_lanes": detail.get("missing_lanes", []),
    }


# ---------------------------------------------------------------------------
# Step 2 — Red-Team-gated bonus / 5-level penalty cascade
# ---------------------------------------------------------------------------

def compute_transition_gate(transition: dict, val_score: float | None) -> dict:
    """V3.17 rule-2 gate + V3.17.1 staleness cross-check.

    valuation_confirmed_transition requires the forecaster to see a transition case,
    the Valuation Specialist to cite the overlay, and its dissent basis to be anything
    other than `thesis_fundamental`. A null dissent basis with a negative valuation lane
    score is treated as `thesis_fundamental` (conservative default per spec).
    """
    sig = transition.get("transition_signature")
    case = transition.get("forecaster_transition_case")
    cited = transition.get("valuation_cited_transition_overlay")
    dissent = transition.get("valuation_transition_dissent_basis")

    if dissent is None and (_f(val_score) is not None and _f(val_score) < 0):
        dissent_effective = "thesis_fundamental"
    else:
        dissent_effective = dissent
    confirmed = (case is True and cited is True and dissent_effective != "thesis_fundamental")

    stale = False
    alerts: list[dict] = []
    t_sig = _parse_ts(transition.get("transition_signature_mtime"))
    t_case = _parse_ts(transition.get("forecaster_transition_case_mtime"))
    if t_sig is not None and t_case is not None and abs(t_sig - t_case) > 6 * 3600:
        stale = True
        alerts.append({"level": "HIGH", "kind": "transition_mtime_skew",
                       "bundle_mtime": t_sig, "forecaster_mtime": t_case,
                       "delta_seconds": round(abs(t_sig - t_case), 1)})
    sig_says = sig not in (None, "", "none", "NONE")
    if case is not None and sig_says != bool(case):
        stale = True
        alerts.append({"level": "HIGH", "kind": "transition_signature_inconsistent",
                       "transition_signature": sig, "forecaster_transition_case": case})

    return {
        "valuation_confirmed_transition": confirmed,
        "dissent_basis_effective": dissent_effective,
        "transition_softening_disabled": stale,
        "transition_data_stale_or_inconsistent": stale,
        "alerts": alerts,
    }


def compute_step2(raw_total: float, lane_scores: dict, val_score: float | None,
                  red_team: dict, shift_tier: str | None, transition_gate: dict,
                  burry_veto: bool) -> dict:
    """5-level priority cascade, first match wins. Returns cascade + raw_after_bonus."""
    verdict = red_team.get("verdict")
    basis = red_team.get("basis")
    if basis is None:
        basis = classify_red_team_basis(red_team.get("counter_thesis") or "",
                                        red_team.get("kill_conditions") or [])
    strength = red_team.get("counter_evidence_strength")
    tier = (shift_tier or "NONE").upper()

    all_scores = [_f(lane_scores.get(k)) for k in LANE_KEYS[:4]] + [_f(val_score)]
    complete = all(s is not None for s in all_scores)
    same_direction = complete and (all(s > 0 for s in all_scores) or all(s < 0 for s in all_scores))

    out = {
        "red_team_basis": basis,
        "red_team_verdict": verdict,
        "effective_verdict": verdict,
        "red_team_auto_downgrade": False,
        "bonus_applied": False,
        "penalty_applied": False,
        "penalty_value": None,
        "cascade_rule_applied": "no_penalty",
        "all_lanes_same_direction": same_direction,
    }

    if same_direction and not burry_veto and verdict == "NO_VIABLE_COUNTER":
        out["bonus_applied"] = True
        out["cascade_rule_applied"] = "consensus_bonus"
        out["raw_after_bonus"] = raw_total * 1.15
        return out

    if verdict != "STRONG_COUNTER":
        out["raw_after_bonus"] = raw_total
        return out

    if tier == "CONFIRMED" and basis in ("pure_mean_reversion", "contaminated"):
        # Rule #1 — mr 一票否決：CONFIRMED paradigm shift 期間不接受 mean-reversion 攻擊
        out.update(effective_verdict="MODERATE_COUNTER", red_team_auto_downgrade=True,
                   penalty_value=0.925, cascade_rule_applied="rule_1_paradigm_confirmed_mr_downgrade")
    elif (not transition_gate["transition_softening_disabled"]
          and red_team.get("_transition_signature") in ("mix_only", "both")
          and transition_gate["valuation_confirmed_transition"]
          and basis == "pure_mean_reversion"):
        # Rule #2 — business-mix transition + Valuation confirms + purely mr attack
        out.update(penalty_value=0.95, cascade_rule_applied="rule_2_transition_signature_mr_soften")
    elif tier == "CANDIDATE":
        out.update(penalty_value=0.925, cascade_rule_applied="rule_3_paradigm_candidate")
    elif basis == "pure_forward":
        # V4.70.0 P0-2 — only ≥2-independent-source counter evidence (=5) keeps the heavy penalty
        out.update(penalty_value=0.85 if strength == 5 else 0.925,
                   cascade_rule_applied="rule_4_pure_forward")
    else:
        # Rule #5 — unclassified STRONG_COUNTER: 0.95 (V4.70.0 downgraded from 0.85)
        out.update(penalty_value=0.95, cascade_rule_applied="rule_5_default_strong_counter")

    out["penalty_applied"] = True
    out["raw_after_bonus"] = raw_total * out["penalty_value"]
    return out


# ---------------------------------------------------------------------------
# Step 3 — directional macro multiplier
# ---------------------------------------------------------------------------

def compute_step3(raw_after_bonus: float, macro_multiplier: float | None,
                  macro_backdrop_score: float | None, shift_macro_floor: float) -> dict:
    mm = _f(macro_multiplier)
    mm = 1.0 if mm is None else mm
    effective = max(mm, shift_macro_floor)
    backdrop = _f(macro_backdrop_score)
    # Spec is literally `sign(raw_after_bonus) == sign(macro_backdrop_score)`, so a
    # 0/0 pair is ALIGNED. Label-only at that point (0 × mult = 0), but the validator
    # re-derives this exact rule, so the two must agree.
    aligned = backdrop is not None and _sign(raw_after_bonus) == _sign(backdrop)
    return {
        "macro_multiplier": mm,
        "effective_macro_mult": effective,
        "macro_alignment": "ALIGNED" if aligned else "CONTRARIAN",
        "final_score": raw_after_bonus * effective if aligned else raw_after_bonus,
    }


# ---------------------------------------------------------------------------
# Step 4 — dynamic threshold + decision band
# ---------------------------------------------------------------------------

def compute_dynamic_threshold(shift_tier: str | None, polarization: str | None) -> dict:
    tier = (shift_tier or "NONE").upper()
    if tier == "CONFIRMED" and polarization == "ALIGNED":
        buy, why = 1.0, "CONFIRMED+ALIGNED → 1.0"
    elif tier == "CANDIDATE" and polarization == "ALIGNED":
        buy, why = 1.1, "CANDIDATE+ALIGNED → 1.1"
    elif polarization == "BIPOLAR":
        buy, why = 1.5, "BIPOLAR → 1.5"
    elif polarization == "OUTLIER":
        buy, why = 1.3, "OUTLIER → 1.3"
    else:
        buy, why = 1.2, f"default 1.2 (tier={tier}, polarization={polarization})"
    staged = max(0.6, round(buy - 0.4, 10))
    return {"buy_threshold": buy, "staged_threshold": staged, "rationale": why}


def decision_band(final_score: float, buy: float, staged: float) -> str:
    """First-match-wins so the table's shared boundaries stay symmetric:
    +staged → STAGED_ENTRY, −staged → STAGED_EXIT."""
    if final_score >= buy:
        return "BUY"
    if final_score >= staged:
        return "STAGED_ENTRY"
    if final_score > -staged:
        return "HOLD"
    if final_score > -buy:
        return "STAGED_EXIT"
    return "SELL"


# ---------------------------------------------------------------------------
# Auto REJECT hard gates
# ---------------------------------------------------------------------------

def evaluate_auto_reject(gates: dict, burry: dict, banded: str) -> dict:
    """Hard gates. All of them outrank the Rec 11 probe exception.

    A triggered gate forces any BUY-side decision down to HOLD; SELL-side decisions
    are untouched (rejecting an exit is not a thing the protocol asks for).
    """
    reasons: list[str] = []
    rr = _f(gates.get("risk_reward_ratio"))
    if banded in ("BUY", "STAGED_ENTRY") and rr is not None and rr < 2.0:
        reasons.append(f"risk_reward_ratio {rr} < 2.0")
    if gates.get("proceed_to_phase3") is False:
        reasons.append("proceed_to_phase3 = false")
    if (gates.get("binary_classification") in ("unknown", "negative")
            and gates.get("binary_event_within_48h") is True):
        reasons.append(
            f"binary risk {gates.get('binary_classification')} with event < 48h")
    systemic = [f for f in (gates.get("mandatory_risk_flags") or [])
                if isinstance(f, str) and "systemic" in f.lower()]
    if systemic:
        reasons.append(f"mandatory_risk_flags systemic: {systemic}")
    if (gates.get("phase2_fanout_mode") == "FULL_FALLBACK"
            and banded in ("BUY", "STAGED_ENTRY")):
        reasons.append("phase2_fanout_summary.mode = FULL_FALLBACK with BUY-side decision")
    bs = _f(burry.get("score"))
    if burry.get("veto_flag") is True or (bs is not None and bs < 20):
        reasons.append(f"Burry T4_VETO (score={bs})")
    return {"triggered": bool(reasons), "reasons": reasons}


# ---------------------------------------------------------------------------
# Rec 11 — hot zone probe
# ---------------------------------------------------------------------------

def evaluate_hot_zone(final_score: float, staged_threshold: float, hot_zone: dict,
                      market_regime: str | None, cap_active: bool,
                      mandatory_risk_flags: list, auto_reject_triggered: bool) -> dict:
    """TODO-015 judgment tree — top-down, first match wins. Always emitted."""
    qualifying = (
        0.0 <= final_score < staged_threshold
        and hot_zone.get("industry_top_30pct") is True
        and (market_regime or "").upper() in BULL_REGIMES
    )
    if not qualifying:
        return {"hot_zone_eval": "not_qualifying", "hot_zone_probe": False,
                "hot_zone_probe_tier": None, "hot_zone_position_size_cap": None,
                "hot_zone_qualifying": False}
    if cap_active:
        return {"hot_zone_eval": "suppressed_by_cap", "hot_zone_probe": False,
                "hot_zone_probe_tier": None, "hot_zone_position_size_cap": None,
                "hot_zone_qualifying": True}
    if (mandatory_risk_flags or []) or auto_reject_triggered:
        return {"hot_zone_eval": "suppressed_by_risk_flag", "hot_zone_probe": False,
                "hot_zone_probe_tier": None, "hot_zone_position_size_cap": None,
                "hot_zone_qualifying": True}
    # V4.70.0 P0-1 — score-tiered probe size: upper half of the fuzzy band earns 30bps
    if final_score >= 0.4:
        tier, cap = "t2_30bps", 0.003
    else:
        tier, cap = "t1_15bps", 0.0015
    return {"hot_zone_eval": "fired", "hot_zone_probe": True,
            "hot_zone_probe_tier": tier, "hot_zone_position_size_cap": cap,
            "hot_zone_qualifying": True}


# ---------------------------------------------------------------------------
# Phase 4.6 — decision cap triggers
# ---------------------------------------------------------------------------

def evaluate_decision_cap_triggers(cap_in: dict | None) -> dict:
    """Trigger evaluation only — every input is already known at Phase 3 time, which is
    why the Rec 11 tree can reference `decision_cap_active` without circularity."""
    if not isinstance(cap_in, dict) or not cap_in:
        return {"decision_cap_active": False, "decision_cap_reason": None,
                "evaluated": False}
    anchors = cap_in.get("anchors_available")
    if isinstance(anchors, int) and not isinstance(anchors, bool) and anchors < 2:
        return {"decision_cap_active": True, "decision_cap_reason": "insufficient_anchors",
                "evaluated": True}
    if cap_in.get("fair_value_confidence") == "low":
        return {"decision_cap_active": True,
                "decision_cap_reason": "low_valuation_confidence", "evaluated": True}
    if cap_in.get("lane_data_quality_low") is True:
        return {"decision_cap_active": True, "decision_cap_reason": "low_data_quality",
                "evaluated": True}
    return {"decision_cap_active": False, "decision_cap_reason": None, "evaluated": True}


def apply_decision_cap(payload: dict) -> dict:
    """Phase 4.6 entry point — runs AFTER Phase 4 sizing, before Phase 5 export.

    Input: {"decision_cap": {...triggers...} | "decision_cap_active"/"decision_cap_reason",
            "final_decision": ..., "avg_confidence": ..., "position_size_pct": ...,
            "final_action": ..., "hot_zone_probe": bool, "cap_override_reason": str|null}

    Rules 1-6 of the protocol §PHASE 4.6. Without `cap_override_reason` a BUY drops to
    HOLD; with one it may stay STAGED_ENTRY. The override never lifts the size or
    confidence caps.

    Note on rule 6's hot-zone exception: validator §11 makes `hot_zone_probe=true` and
    `decision_cap_active=true` mutually exclusive, and Phase 3 already suppresses the
    probe when the cap is active (`suppressed_by_cap`). So the exception can never fire
    inside an active decision cap; it is reported as inapplicable rather than silently
    dropped.
    """
    if "decision_cap_active" in payload:
        trig = {"decision_cap_active": bool(payload.get("decision_cap_active")),
                "decision_cap_reason": payload.get("decision_cap_reason"),
                "evaluated": True}
    else:
        trig = evaluate_decision_cap_triggers(payload.get("decision_cap"))

    decision = payload.get("final_decision")
    action = payload.get("final_action")
    conf = _f(payload.get("avg_confidence"))
    size = _f(payload.get("position_size_pct"))
    override = payload.get("cap_override_reason")
    adjustments: list[str] = []

    out = {
        "phase": 4.6,
        "engine": ENGINE_LABEL,
        "decision_cap_active": trig["decision_cap_active"],
        "decision_cap_reason": trig["decision_cap_reason"],
        "cap_override_reason": override if trig["decision_cap_active"] else None,
        "final_decision": decision,
        "avg_confidence": conf,
        "position_size_pct": size,
        "final_action": action,
        "hot_zone_probe": payload.get("hot_zone_probe") is True,
        "hot_zone_exception_applicable": False,
        "adjustments": adjustments,
        "warnings": [],
    }
    if not trig["decision_cap_active"]:
        adjustments.append("decision cap not triggered — Phase 4 values pass through unchanged")
        return out

    if trig["decision_cap_reason"] not in CAP_REASONS:
        out["warnings"].append(
            f"decision_cap_reason {trig['decision_cap_reason']!r} outside {CAP_REASONS}")

    if decision == "BUY":
        out["final_decision"] = "STAGED_ENTRY" if override else "HOLD"
        adjustments.append(
            f"BUY forbidden under cap → {out['final_decision']}"
            + (" (cap_override_reason present)" if override else " (no override)"))

    if conf is not None and conf > 0.65:
        out["avg_confidence"] = 0.65
        adjustments.append(f"avg_confidence {conf} → 0.65 (cap)")
    if size is not None and size > 0.003:
        out["position_size_pct"] = 0.003
        adjustments.append(f"position_size_pct {size} → 0.003 (30 bps cap)")

    if out["final_decision"] == "HOLD":
        out["final_action"] = "CANCEL"
        adjustments.append("final_action → CANCEL (decision fell to HOLD)")
    elif action == "EXECUTE":
        out["final_action"] = "STAGED"
        adjustments.append("final_action EXECUTE → STAGED (cap)")

    if out["hot_zone_probe"]:
        out["warnings"].append(
            "hot_zone_probe=true with decision_cap_active=true — validator §11 forbids "
            "this pairing; the Phase 3 tree should have emitted suppressed_by_cap")
    return out


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_phase3(inp: dict) -> dict:
    warnings: list[str] = []
    lane_scores = inp.get("lane_scores") or {}
    if not isinstance(lane_scores, dict):
        raise ValueError("lane_scores must be an object")

    val_lane = inp.get("valuation_lane") or {}
    val_score = _f(lane_scores.get("valuation"))
    if val_score is None:
        val_score = _f(val_lane.get("score"))

    lane_conf = dict(inp.get("lane_confidence") or {})
    if lane_conf.get("valuation") is None and _f(val_lane.get("confidence")) is not None:
        lane_conf["valuation"] = _f(val_lane.get("confidence"))

    weights = dict(DEFAULT_WEIGHTS)
    if isinstance(inp.get("weights"), dict):
        for k, v in inp["weights"].items():
            if k in weights and _f(v) is not None:
                weights[k] = _f(v)
        if weights != DEFAULT_WEIGHTS:
            warnings.append(f"non-default lane weights in use: {weights}")

    scores_for_step1 = dict(lane_scores)
    scores_for_step1["valuation"] = val_score

    s1 = compute_step1(scores_for_step1, lane_conf, weights)
    if s1["missing_lanes"]:
        # A deep-dive is a 5-lane vote. Weights are not redistributed, so a missing lane
        # silently understates raw_total — that is a broken decision, not a degraded one.
        # Fail loudly here rather than emitting a `MISSING` step string the PM would copy
        # into the export and the validator would then reject as unparseable.
        raise ValueError(
            f"lane inputs incomplete: {s1['missing_lanes']} — Phase 3 requires all 5 lane "
            "scores AND confidences (weights are never redistributed). Fix the input JSON; "
            "if a lane genuinely failed, resolve it in Phase 2 fan-in/inline fallback first.")

    shift_tier = (inp.get("structural_shift") or {}).get("tier")
    s1_5 = compute_step1_5(shift_tier)

    macro = inp.get("macro") or {}
    regime = macro.get("market_regime")
    s1_7 = compute_step1_7(lane_scores, val_score, shift_tier, regime)

    red_team = dict(inp.get("red_team") or {})
    transition = inp.get("transition") or {}
    red_team["_transition_signature"] = transition.get("transition_signature")
    tgate = compute_transition_gate(transition, val_score)

    burry = inp.get("burry") or {}
    s2 = compute_step2(s1["raw_total"], lane_scores, val_score, red_team, shift_tier,
                       tgate, burry.get("veto_flag") is True)

    s3 = compute_step3(s2["raw_after_bonus"], macro.get("macro_multiplier"),
                       macro.get("macro_backdrop_score"), s1_5["shift_macro_floor"])

    dyn = compute_dynamic_threshold(shift_tier, s1_7["label"])
    final_score = round(s3["final_score"], 4)
    banded = decision_band(final_score, dyn["buy_threshold"], dyn["staged_threshold"])

    decision = banded
    band_adjustments: list[str] = []
    if s1_7["force_buy_downgrade"] and decision == "BUY":
        decision = "STAGED_ENTRY"
        band_adjustments.append("BIPOLAR: BUY → STAGED_ENTRY 強制降階 (Step 1.7)")

    gates = inp.get("gates") or {}
    auto_reject = evaluate_auto_reject(gates, burry, decision)
    if auto_reject["triggered"] and decision in ("BUY", "STAGED_ENTRY"):
        decision = "HOLD"
        band_adjustments.append(f"Auto REJECT → HOLD ({'; '.join(auto_reject['reasons'])})")
    auto_reject["forced_decision"] = "HOLD" if (
        auto_reject["triggered"] and banded in ("BUY", "STAGED_ENTRY")) else None

    # Two Auto REJECT gates (R/R < 2.0, FULL_FALLBACK) are conditional on the decision
    # being BUY-side, so evaluating them against a banded HOLD says nothing about whether
    # the Rec 11 probe may open a position. Spec: 硬閘優先於熱區例外 — so re-run the gates
    # against the decision the probe WOULD produce before letting it fire.
    probe_gate = evaluate_auto_reject(gates, burry, "STAGED_ENTRY")
    auto_reject["probe_prospective_triggered"] = probe_gate["triggered"]
    auto_reject["probe_prospective_reasons"] = probe_gate["reasons"]

    cap_trig = evaluate_decision_cap_triggers(inp.get("decision_cap"))
    if not cap_trig["evaluated"]:
        warnings.append(
            "decision_cap inputs absent — cap treated as inactive; Rec 11 tree cannot "
            "return suppressed_by_cap")

    hz = evaluate_hot_zone(final_score, dyn["staged_threshold"], inp.get("hot_zone") or {},
                           regime, cap_trig["decision_cap_active"],
                           gates.get("mandatory_risk_flags") or [],
                           auto_reject["triggered"] or probe_gate["triggered"])
    if hz["hot_zone_probe"]:
        decision = "STAGED_ENTRY"
        band_adjustments.append(
            f"Rec 11 hot zone probe fired ({hz['hot_zone_probe_tier']}): HOLD → STAGED_ENTRY")

    avg_conf_raw = s1["avg_confidence_raw"]
    avg_conf = (round(avg_conf_raw * s1_7["confidence_multiplier"], 4)
                if avg_conf_raw is not None else None)

    calculation_steps: dict[str, Any] = dict(s1["steps"])
    calculation_steps.update({
        "raw_total": round(s1["raw_total"], 4),
        "structural_shift_modulation": {
            "tier": s1_5["tier"],
            "applied_adjustments": s1_5["applied_adjustments"],
            "shift_macro_floor": s1_5["shift_macro_floor"],
            "position_size_cap_pct": s1_5["position_size_cap_pct"],
            "red_team_mean_reversion_blocked": s1_5["red_team_mean_reversion_blocked"],
        },
        "polarization_modulation": {
            "label": s1_7["label"],
            "lane_range": s1_7["lane_range"],
            "pos_strong": s1_7["pos_strong"],
            "neg_strong": s1_7["neg_strong"],
            "outlier_lane_id": s1_7["outlier_lane_id"],
            "applied_adjustments": s1_7["applied_adjustments"],
            "confidence_multiplier": s1_7["confidence_multiplier"],
            "position_cap_after": s1_7["position_cap_after"],
        },
        "red_team_basis": s2["red_team_basis"],
        "red_team_auto_downgrade": s2["red_team_auto_downgrade"],
        "cascade_rule_applied": s2["cascade_rule_applied"],
        "dynamic_threshold": dyn,
        "red_team_verdict": s2["red_team_verdict"],
        "red_team_effective_verdict": s2["effective_verdict"],
        "red_team_counter_evidence_strength": red_team.get("counter_evidence_strength"),
        "red_team_thesis_break_probability": red_team.get("thesis_break_probability"),
        "bonus_applied": s2["bonus_applied"],
        "penalty_applied": s2["penalty_applied"],
        "penalty_value": s2["penalty_value"],
        "raw_after_bonus": round(s2["raw_after_bonus"], 5),
        "macro_multiplier": s3["macro_multiplier"],
        "macro_alignment": s3["macro_alignment"],
        "effective_macro_mult": s3["effective_macro_mult"],
        "final_score": final_score,
    })

    return {
        "phase": 3,
        "engine": ENGINE_LABEL,
        "decision_engine_version": ENGINE_VERSION,
        "ticker": inp.get("ticker"),
        "calculation_steps": calculation_steps,
        "avg_confidence": avg_conf,
        "avg_confidence_raw": round(avg_conf_raw, 4) if avg_conf_raw is not None else None,
        "final_score": final_score,
        "final_decision": decision,
        "decision_band_before_adjustments": banded,
        "band_adjustments": band_adjustments,
        "decision_margin": (
            f"final_score {final_score:+.4f} vs buy {dyn['buy_threshold']} / "
            f"staged {dyn['staged_threshold']} → {decision} "
            f"(margin_to_buy {final_score - dyn['buy_threshold']:+.4f})"),
        "hot_zone_probe": hz["hot_zone_probe"],
        "hot_zone_probe_tier": hz["hot_zone_probe_tier"],
        "hot_zone_eval": hz["hot_zone_eval"],
        "hot_zone_position_size_cap": hz["hot_zone_position_size_cap"],
        "auto_reject": auto_reject,
        "decision_cap_active": cap_trig["decision_cap_active"],
        "decision_cap_reason": cap_trig["decision_cap_reason"],
        "position_size_cap_pct": s1_5["position_size_cap_pct"],
        "polar_position_cap_pct": s1_7["position_cap_after"],
        "transition_data_stale_or_inconsistent": tgate["transition_data_stale_or_inconsistent"],
        "alerts": tgate["alerts"],
        "warnings": warnings,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic Phase 3 decision engine")
    ap.add_argument("--from-file", help="input JSON path (default: stdin)")
    ap.add_argument("--phase", default="3", choices=("3", "4.6"),
                    help="3 = decision engine (default); 4.6 = decision cap application")
    args = ap.parse_args(argv)

    if args.from_file:
        with open(args.from_file, encoding="utf-8") as fp:
            raw = fp.read()
    else:
        raw = sys.stdin.read()
    try:
        inp = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"unparseable input: {e}"}))
        return 1
    if not isinstance(inp, dict):
        print(json.dumps({"error": "input must be a JSON object"}))
        return 1

    try:
        out = apply_decision_cap(inp) if args.phase == "4.6" else run_phase3(inp)
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        return 1

    print(json.dumps(out, ensure_ascii=False, indent=2))
    for w in out.get("warnings") or []:
        print(f"[decision_engine] ⚠ {w}", file=sys.stderr)
    for a in out.get("alerts") or []:
        print(f"[decision_engine] ‼ {a.get('level')} {a.get('kind')}: {a}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

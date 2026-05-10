"""V2.10.0 — apply deterministic shadow + polarization label to session_export JSON.

Reads a session_export.json (or a single trade entry), computes:
  - signal_polarization : ALIGNED | MIXED | BIPOLAR  (from lane scores)
  - valuation_score_det : -1 | -0.5 | 0 | +0.5 | +1   (from FV vs price)
  - val_agreement       : AGREE | DRIFT | DISAGREE   (LLM val vs det)
  - red_team_verdict_det: NONE | MODERATE_COUNTER | STRONG_COUNTER  (from kill triggers)
  - red_team_agreement  : AGREE | DISAGREE          (LLM red_team vs det)

LLM's main scores (final_score, lane_scores, valuation_lane.score, red_team_verdict)
are NEVER overwritten — det fields are sidecar metadata for sanity check + UX badge.

Usage:
  python3 investment/scripts/apply_det_shadow.py SESSION_EXPORT.json
  python3 investment/scripts/apply_det_shadow.py --inplace SESSION_EXPORT.json
  python3 investment/scripts/apply_det_shadow.py --dry-run SESSION_EXPORT.json   # print only

詳見 investment/phase5_export_schema.md V2.10 章節。
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any


# ---------------------------------------------------------------------------
# (1) Polarization detection — pure from LLM lane scores
# ---------------------------------------------------------------------------

def compute_polarization(lane_scores: dict, val_score: float | None) -> dict:
    """Returns {label, range, max, min, missing_lanes, lane_score_array}.

    Rule (V2.19 — asymmetric threshold):
      - BIPOLAR  : range >= 4 AND any >= +2 AND any <= -2
                   AND >= 2 lanes >= +1 AND >= 2 lanes <= -1
                   (real conflict: both sides have weight, not 4-vs-1 outlier)
      - OUTLIER  : range >= 4 AND has extreme but minority side has only 1 lane
                   (e.g. [+4,+3,+3,+2,-2] — single dissenter, not deadlock)
      - MIXED    : range >= 3 AND has positive AND has negative (no extremes)
      - ALIGNED  : everything else

    OUTLIER is V2.19-new; sits between BIPOLAR (×0.5 confidence) and ALIGNED (×1.0).
    Phase 3 Step 1.7 maps: BIPOLAR ×0.5 / OUTLIER ×0.85 / MIXED ×0.75 / ALIGNED ×1.0.
    """
    scores = []
    missing = []
    for k in ("fundamentals", "sentiment", "news", "technical"):
        v = lane_scores.get(k) if isinstance(lane_scores, dict) else None
        if isinstance(v, (int, float)):
            scores.append(float(v))
        else:
            missing.append(k)
    if isinstance(val_score, (int, float)):
        scores.append(float(val_score))
    else:
        missing.append("valuation")

    if len(scores) < 3:
        return {"label": None, "reason": "insufficient_lane_data",
                "missing_lanes": missing}

    mx, mn = max(scores), min(scores)
    rng = mx - mn
    has_pos2 = any(s >= 2.0 for s in scores)
    has_neg2 = any(s <= -2.0 for s in scores)
    pos_strong = sum(1 for s in scores if s >= 1.0)
    neg_strong = sum(1 for s in scores if s <= -1.0)

    if rng >= 4.0 and has_pos2 and has_neg2 and pos_strong >= 2 and neg_strong >= 2:
        label = "BIPOLAR"
    elif rng >= 4.0 and (has_pos2 or has_neg2):
        label = "OUTLIER"
    elif rng >= 3.0 and any(s > 0 for s in scores) and any(s < 0 for s in scores):
        label = "MIXED"
    else:
        label = "ALIGNED"

    return {
        "label":         label,
        "range":         round(rng, 2),
        "max":           round(mx, 2),
        "min":           round(mn, 2),
        "pos_strong":    pos_strong,
        "neg_strong":    neg_strong,
        "missing_lanes": missing,
    }


# ---------------------------------------------------------------------------
# (1b) V2.19 — Red Team basis classifier (anti-spoofing)
# ---------------------------------------------------------------------------

# Mean-reversion attack keywords (Chinese + English).
# 一旦出現任何一個 → mr_hits ≥ 1 → 視為 backward-looking attack。
MR_KEYWORDS = (
    "歷史均值", "mean revert", "mean reversion", "週期見頂", "週期峰值",
    "週期高點", "Peak Cycle", "P/E ceiling", "回到歷史中位", "歷史毛利",
    "historical median", "cycle peak", "regression to mean", "歷史平均",
    "回歸到歷史", "歷史 P/E", "歷史本益比", "週期頂部",
)

# Forward mechanism breakage keywords — describe future-state catalysts.
FW_KEYWORDS = (
    "competitor", "客戶庫存", "supply addition", "量產", "需求飽和",
    "技術替代", "demand saturation", "capacity addition", "inventory days",
    "下游庫存", "新進入者", "next-gen", "庫存日數", "替代技術",
    "新產能", "新對手", "市佔流失", "share loss",
)


def classify_red_team_basis(counter_thesis: str, kill_conditions: list) -> str:
    """V2.19 — classify Red Team attack basis (anti-spoofing).

    Returns one of:
      - pure_forward          : fw_hits >= 1 AND mr_hits == 0
                                (唯一可保 STRONG_COUNTER 殺傷力)
      - pure_mean_reversion   : mr_hits >= 1 AND fw_hits == 0
                                (純歷史攻擊，CONFIRMED tier 下自動降級)
      - contaminated          : mr_hits >= 1 AND fw_hits >= 1
                                (LLM 偷渡 mr — fw 救不回否決權，視同 mr)
      - unclassified          : mr_hits == 0 AND fw_hits == 0
                                (無關鍵字命中，退回原 verdict 邏輯)

    Design: "contaminated" 不是 "mixed" — 命名強調污染而非平衡。
    LLM 在 contamination case 下塞 1 個 fw 關鍵字無法救回 mr 否決權。
    """
    haystack_parts = []
    if isinstance(counter_thesis, str):
        haystack_parts.append(counter_thesis)
    if isinstance(kill_conditions, list):
        for kc in kill_conditions:
            if isinstance(kc, str):
                haystack_parts.append(kc)
            elif isinstance(kc, dict):
                # kill_condition entries may be {if:..., then:...} dicts
                for v in kc.values():
                    if isinstance(v, str):
                        haystack_parts.append(v)

    haystack = "\n".join(haystack_parts).lower()
    mr_hits = sum(1 for kw in MR_KEYWORDS if kw.lower() in haystack)
    fw_hits = sum(1 for kw in FW_KEYWORDS if kw.lower() in haystack)

    if mr_hits == 0 and fw_hits == 0:
        return "unclassified"
    if mr_hits == 0 and fw_hits >= 1:
        return "pure_forward"
    if mr_hits >= 1 and fw_hits == 0:
        return "pure_mean_reversion"
    return "contaminated"


# ---------------------------------------------------------------------------
# (2) Deterministic Valuation shadow — from FV vs price
# ---------------------------------------------------------------------------

def compute_val_det(weighted_fair_value: float | None,
                     vs_current_pct: float | None) -> float | None:
    """Map upside % to discrete score [-1, +1] in 0.5 steps.

    vs_current_pct is in percent units (4.5 means +4.5% upside).
    Threshold table:
      >= +30%  → +1.0  (BUY strong)
      >= +10%  → +0.5  (BUY)
      >=  -5%  →  0    (HOLD neutral)
      >= -20%  → -0.5  (HOLD bearish)
      <  -20%  → -1.0  (SELL)
    """
    if not isinstance(vs_current_pct, (int, float)):
        return None
    u = float(vs_current_pct) / 100.0
    if u >= 0.30:
        return 1.0
    if u >= 0.10:
        return 0.5
    if u >= -0.05:
        return 0.0
    if u >= -0.20:
        return -0.5
    return -1.0


def compute_val_agreement(llm_score: float | None, det_score: float | None) -> str | None:
    if llm_score is None or det_score is None:
        return None
    diff = abs(float(llm_score) - float(det_score))
    if diff <= 0.25:
        return "AGREE"
    if diff <= 0.75:
        return "DRIFT"
    return "DISAGREE"


# ---------------------------------------------------------------------------
# (3) Deterministic Red Team — from kill triggers
# ---------------------------------------------------------------------------

KILL_TRIGGER_THRESHOLDS = {
    "altman_z":          ("<", 1.8,   "Altman Z < 1.8 (financial distress zone)"),
    "debt_to_equity":    (">", 5.0,   "D/E > 5.0 (high leverage)"),
    "fcf_yield":         ("<", 0.0,   "FCF yield < 0 (cash burn)"),
    "insider_ratio_q":   ("<", 0.3,   "Insider acq/disp ratio < 0.3 (heavy distribution)"),
    "short_interest_pct": (">", 20.0, "Short interest > 20% (crowded short)"),
    "fred_in_sector_avoid": ("==", True, "FRED regime sector_avoid"),
}


def compute_red_team_det(det_inputs: dict) -> dict:
    """Returns {verdict, kill_count, triggered, missing}.

    verdict mapping:
      kill_count >= 5 → STRONG_COUNTER
      kill_count >= 3 → MODERATE_COUNTER
      else            → NONE  (NO_VIABLE_COUNTER)
    """
    if not isinstance(det_inputs, dict):
        return {"verdict": None, "reason": "no_det_inputs",
                "kill_count": None, "triggered": [], "missing": list(KILL_TRIGGER_THRESHOLDS)}

    triggered = []
    missing = []
    for field, (op, thr, label) in KILL_TRIGGER_THRESHOLDS.items():
        v = det_inputs.get(field)
        if v is None:
            missing.append(field)
            continue
        try:
            if op == "<" and float(v) < thr:
                triggered.append(field)
            elif op == ">" and float(v) > thr:
                triggered.append(field)
            elif op == "==" and bool(v) == bool(thr):
                triggered.append(field)
        except (TypeError, ValueError):
            missing.append(field)

    kill_count = len(triggered)
    valid_count = len(KILL_TRIGGER_THRESHOLDS) - len(missing)

    # If too many fields missing, can't make confident judgment
    if valid_count < 3:
        return {"verdict": None, "reason": "insufficient_inputs",
                "kill_count": kill_count, "triggered": triggered, "missing": missing}

    if kill_count >= 5:
        verdict = "STRONG_COUNTER"
    elif kill_count >= 3:
        verdict = "MODERATE_COUNTER"
    else:
        verdict = "NO_VIABLE_COUNTER"

    return {"verdict": verdict, "kill_count": kill_count,
            "triggered": triggered, "missing": missing}


def compute_red_team_agreement(llm_verdict: str | None, det_verdict: str | None) -> str | None:
    if llm_verdict is None or det_verdict is None:
        return None
    # Normalize "NONE" / "NO_VIABLE_COUNTER" as same
    norm = {"NONE": "NO_VIABLE_COUNTER"}
    a = norm.get(llm_verdict, llm_verdict)
    b = norm.get(det_verdict, det_verdict)
    return "AGREE" if a == b else "DISAGREE"


# ---------------------------------------------------------------------------
# Apply to a single trade entry
# ---------------------------------------------------------------------------

def apply_to_trade(trade: dict) -> dict:
    """Compute and attach det_shadow block to a trades_this_session[] entry.
    Returns the (mutated) entry."""
    val_lane = trade.get("valuation_lane") or {}
    lane_scores = trade.get("lane_scores") or {}
    det_inputs  = trade.get("det_inputs")  or {}

    polar = compute_polarization(lane_scores, val_lane.get("score"))
    val_det = compute_val_det(val_lane.get("weighted_fair_value"),
                                val_lane.get("vs_current_pct"))
    val_agree = compute_val_agreement(val_lane.get("score"), val_det)

    rt_det = compute_red_team_det(det_inputs)
    rt_agree = compute_red_team_agreement(trade.get("red_team_verdict"),
                                            rt_det.get("verdict"))

    # V2.19 — Red Team basis classifier (anti-spoofing post-filter)
    rt_basis = classify_red_team_basis(
        trade.get("red_team_counter_thesis") or trade.get("counter_thesis") or "",
        trade.get("red_team_kill_conditions") or trade.get("kill_conditions") or [],
    )

    trade["det_shadow"] = {
        "version":              "V2.19.0",
        "signal_polarization":  polar.get("label"),
        "polarization_detail":  polar,
        "valuation_score_det":  val_det,
        "val_agreement":        val_agree,
        "red_team_verdict_det": rt_det.get("verdict"),
        "red_team_detail":      rt_det,
        "red_team_agreement":   rt_agree,
        "red_team_basis":       rt_basis,
    }
    return trade


def apply_to_session_export(payload: dict) -> dict:
    """Mutate a session_export.json (V4.6+ format) to attach det_shadow on each trade."""
    trades = payload.get("trades_this_session") or []
    for t in trades:
        if isinstance(t, dict):
            apply_to_trade(t)
    return payload


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="Path to session_export.json or history.json entry")
    ap.add_argument("--inplace", action="store_true",
                    help="Write back to the same file (default: print to stdout)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Compute and print det_shadow only; don't write")
    args = ap.parse_args()

    with open(args.path) as f:
        payload = json.load(f)

    if isinstance(payload, dict) and "trades_this_session" in payload:
        apply_to_session_export(payload)
    elif isinstance(payload, dict) and "valuation_lane" in payload:
        # Single trade entry (e.g. one history.json item)
        apply_to_trade(payload)
    elif isinstance(payload, list):
        # history.json full file
        for entry in payload:
            if isinstance(entry, dict):
                apply_to_session_export(entry)
    else:
        sys.exit(f"[ERROR] Unrecognized JSON shape at {args.path}")

    if args.dry_run:
        # Print just the det_shadow blocks
        if isinstance(payload, dict) and "trades_this_session" in payload:
            for t in payload["trades_this_session"]:
                print(json.dumps(t.get("det_shadow", {}), indent=2, ensure_ascii=False))
        elif isinstance(payload, dict):
            print(json.dumps(payload.get("det_shadow", {}), indent=2, ensure_ascii=False))
        return 0

    if args.inplace:
        with open(args.path, "w") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"[apply_det_shadow] wrote in-place: {args.path}", file=sys.stderr)
    else:
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        print()  # trailing newline
    return 0


if __name__ == "__main__":
    sys.exit(main())

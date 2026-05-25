#!/usr/bin/env python3
"""
narrative-pulse-detector — stage classifier (1-5) + R/R scenarios.

Reads stage_weights.yaml + components dict → emits stage / confidence /
scenarios / expected_return / recommended_action.

Pure function: classify(components, weights_cfg) → dict.
"""
import math
from pathlib import Path
from typing import Optional

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "stage_weights.yaml"


def load_weights(path: Optional[Path] = None) -> dict:
    fp = path or CONFIG_PATH
    with open(fp, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Rule evaluator (mini-DSL,limit to safe ops) ────────────────────────
def _eval_rule(rule: str, components: dict) -> bool:
    """Evaluate a YAML rule string like 'rsi_overbought_days >= 10' against
    components dict. Uses Python eval with restricted globals.

    Supports: <, <=, >, >=, ==, !=, and, or, not, +, -, *, /, max(), min(), abs(), parens.

    Missing-value semantics (Codex review #2 fix): None is preserved verbatim
    so YAML rules can guard with `is not None`. Any arithmetic/comparison op
    that touches None raises TypeError, which we catch and return False — so
    a rule like `breadth_200dma_pct <= 30` evaluates False when breadth is
    missing rather than silently treating None as 0. To explicitly opt into
    the "missing == 0" behavior, write `(breadth_200dma_pct or 0) <= 30`.
    """
    if not rule or not isinstance(rule, str):
        return False
    safe_globals = {
        "__builtins__": {},
        "max": max, "min": min, "abs": abs, "round": round,
        "True": True, "False": False, "None": None,
    }
    # Preserve None — do NOT coerce to 0. Rules must guard explicitly.
    safe_locals = dict(components)
    try:
        return bool(eval(rule, safe_globals, safe_locals))
    except (TypeError, ValueError, NameError, AttributeError):
        # Missing key, None arithmetic, malformed rule → treat as not-triggered
        return False
    except Exception:
        return False


def _bounded_normalize(probs: list[float], lo: float, hi: float,
                       max_iter: int = 50, tol: float = 1e-9) -> tuple[list[float], bool]:
    """Project probs onto the simplex Σp = 1 subject to lo ≤ p ≤ hi.

    Water-filling iteration: at each step add/remove the deficit/excess
    proportional to each scenario's headroom in the needed direction
    (toward `hi` when adding, toward `lo` when removing). Saturated
    scenarios stop receiving / giving.

    Feasibility (n*lo ≤ 1 ≤ n*hi) is the caller's responsibility; for
    Stage 1/2 (3 scenarios, clamp [0.05, 0.80]): 3*0.05=0.15 ≤ 1 ≤ 3*0.80=2.40 ✓
    Stage 4/5 (4 scenarios): 4*0.05=0.20 ≤ 1 ≤ 4*0.80=3.20 ✓.

    Returns (projected_probs, converged_bool). If infeasible or saturated,
    returns best-effort and converged=False (caller can log).
    """
    p = [max(lo, min(hi, x)) for x in probs]
    n = len(p)
    if n == 0:
        return p, True

    for _ in range(max_iter):
        total = sum(p)
        diff = 1.0 - total
        if abs(diff) <= tol:
            return p, True
        if diff > 0:
            # need to add — distribute proportional to upward headroom
            cap = [hi - x for x in p]
        else:
            # need to remove — distribute proportional to downward headroom
            cap = [x - lo for x in p]
        total_cap = sum(cap)
        if total_cap <= tol:
            # all saturated in the needed direction — cannot satisfy Σ=1 inside bounds
            return p, False
        share_factor = abs(diff) / total_cap
        for i in range(n):
            if diff > 0:
                p[i] = min(hi, p[i] + cap[i] * share_factor)
            else:
                p[i] = max(lo, p[i] - cap[i] * share_factor)
    return p, False


# Stage_num → adjustment block key (matches scenario_adjustments top-level keys)
_STAGE_KEY_BY_NUM = {
    1: "brewing",
    2: "ignition",
    3: "acceleration",   # 註:V1.1 不為 Stage 3 提供 adjustment block,空 dict
    4: "euphoria",
    5: "distribution",
}


def _apply_scenario_adjustments(
    stage_num: int,
    scenarios_in: list,
    components: dict,
    adjust_cfg: dict,
) -> tuple[list[dict], float, float]:
    """V1.1 per-ticker scenario adjustment layer.

    Inputs:
      stage_num — int 1-5
      scenarios_in — list of {label, label_en, prob, target_pct} from stage_weights.yaml
      components — ticker features dict (used by rule conditions)
      adjust_cfg — top-level `scenario_adjustments` block from YAML

    Returns:
      (adjusted_scenarios, expected_return_base, expected_return_adjusted)
        adjusted_scenarios — list of scenario dicts with prob_base / prob /
                             prob_breakdown / target_pct_base / target_pct /
                             target_breakdown
        expected_return_base — V1.0 prior Σ(prob_base × target_pct_base)
        expected_return_adjusted — V1.1 Σ(prob × target_pct) post-adjustment

    Pipeline per scenario:
      1. prob_raw = prob_base + Σ delta where condition fires
      2. clamp prob_raw to [global.prob_clamp[0], global.prob_clamp[1]]
      3. target = target_base + Σ target_delta where condition fires
    Across all scenarios:
      4. Normalize probs to sum=1.0 (proportional scaling); append _normalize
         entry to each scenario's prob_breakdown.

    Stage 3 (acceleration) — adjust_cfg may have no entry; in that case each
    scenario's prob_breakdown and target_breakdown are [] and prob/target ==
    base. expected_return_base == expected_return_adjusted.
    """
    stage_key = _STAGE_KEY_BY_NUM.get(stage_num)
    stage_block = (adjust_cfg or {}).get(stage_key) if stage_key else None
    global_cfg = (adjust_cfg or {}).get("global") or {}
    clamp = global_cfg.get("prob_clamp") or [0.0, 1.0]
    clamp_lo, clamp_hi = float(clamp[0]), float(clamp[1])
    do_normalize = bool(global_cfg.get("normalize", True))

    adjusted = []
    er_base = 0.0
    for s in scenarios_in:
        prob_base = float(s.get("prob", 0.0))
        tgt_base = float(s.get("target_pct", 0.0))
        er_base += prob_base * tgt_base

        scen_block = (stage_block or {}).get(s.get("label_en")) or {}
        prob_deltas_cfg = scen_block.get("prob_deltas") or []
        target_deltas_cfg = scen_block.get("target_deltas") or []

        prob_breakdown = []
        target_breakdown = []

        # ── prob deltas
        prob_raw = prob_base
        for rule in prob_deltas_cfg:
            cond = rule.get("condition", "")
            delta = float(rule.get("delta", 0.0))
            if delta == 0.0:
                # skip neutralized rules (5/31 review 可能把 delta 改 0 回 V1.0)
                continue
            if _eval_rule(cond, components):
                prob_raw += delta
                prob_breakdown.append({
                    "rule": rule.get("name"),
                    "delta": round(delta, 4),
                    "note": rule.get("note", ""),
                })

        # ── clamp
        prob_clamped = max(clamp_lo, min(clamp_hi, prob_raw))
        if prob_clamped != prob_raw:
            prob_breakdown.append({
                "rule": "_clamp",
                "delta": round(prob_clamped - prob_raw, 4),
                "note": f"clamped to [{clamp_lo}, {clamp_hi}]",
            })

        # ── target deltas
        tgt_final = tgt_base
        for rule in target_deltas_cfg:
            cond = rule.get("condition", "")
            delta = float(rule.get("delta", 0.0))
            if delta == 0.0:
                continue
            if _eval_rule(cond, components):
                tgt_final += delta
                target_breakdown.append({
                    "rule": rule.get("name"),
                    "delta": round(delta, 4),
                    "note": rule.get("note", ""),
                })

        adjusted.append({
            "label": s.get("label"),
            "label_en": s.get("label_en"),
            "prob_base": round(prob_base, 4),
            "prob": prob_clamped,   # finalized below by normalize step
            "prob_breakdown": prob_breakdown,
            "target_pct_base": round(tgt_base, 2),
            "target_pct": round(tgt_final, 2),
            "target_breakdown": target_breakdown,
        })

    # ── bounded normalize across scenarios (V1.1.1: respects clamp) ───
    # Codex finding #2 fix: previous simple proportional scaling could push a
    # clamped 0.80 above the upper bound (e.g. [0.80, 0.05, 0.05] / 0.90 →
    # 0.889). _bounded_normalize uses water-filling so post-normalize values
    # respect [clamp_lo, clamp_hi] AND Σ = 1.
    if do_normalize and adjusted:
        pre_probs = [item["prob"] for item in adjusted]
        post_probs, converged = _bounded_normalize(pre_probs, clamp_lo, clamp_hi)
        for i, item in enumerate(adjusted):
            delta_norm = post_probs[i] - pre_probs[i]
            item["prob"] = post_probs[i]
            if abs(delta_norm) > 1e-9:
                item["prob_breakdown"].append({
                    "rule": "_normalize",
                    "delta": round(delta_norm, 4),
                    "note": f"bounded water-fill to Σ=1 within [{clamp_lo}, {clamp_hi}]"
                            + ("" if converged else " (NOT converged — bounds tight)"),
                })

    # Round prob to 4dp for stable JSON output
    for item in adjusted:
        item["prob"] = round(item["prob"], 4)

    er_adjusted = sum(item["prob"] * item["target_pct"] for item in adjusted)
    return adjusted, round(er_base, 2), round(er_adjusted, 2)


def _evaluate_stage(stage_key: str, stage_cfg: dict, components: dict) -> tuple[float, list[str]]:
    """Return (confidence_sum, triggered_condition_names) for one stage."""
    conditions = stage_cfg.get("conditions") or {}
    confidence = 0.0
    triggered = []
    for cond_name, cond in conditions.items():
        rule = cond.get("rule", "")
        weight = float(cond.get("weight", 0.0))
        if _eval_rule(rule, components):
            confidence += weight
            triggered.append(f"{cond_name}: {rule}")
    return round(confidence, 3), triggered


def classify(components: dict, weights_cfg: Optional[dict] = None) -> dict:
    """Main classifier. Iterates stages 5 → 1 (first stage with confidence >= threshold wins)."""
    cfg = weights_cfg or load_weights()
    stages_cfg = cfg.get("stages") or {}
    min_conf = float(cfg.get("min_confidence_for_stage", 0.6))

    # Stage 5 → 1 evaluation order — first match wins (Stage 5 is most specific)
    stage_order = ["distribution", "euphoria", "acceleration", "ignition", "brewing"]

    best_stage_key = None
    best_stage_cfg = None
    best_confidence = 0.0
    best_triggered: list[str] = []
    all_scores = {}

    for skey in stage_order:
        if skey not in stages_cfg:
            continue
        scfg = stages_cfg[skey]
        conf, trig = _evaluate_stage(skey, scfg, components)
        all_scores[skey] = {"confidence": conf, "triggered": trig}
        if conf >= min_conf and best_stage_key is None:
            best_stage_key = skey
            best_stage_cfg = scfg
            best_confidence = conf
            best_triggered = trig

    if best_stage_key is None:
        # Codex review #1 fix: previously fell back to max() which picked
        # `distribution` (Stage 5 — first dict key) when ALL stage scores were 0.
        # That mis-labelled empty / failed-input tickers as "exit candidate".
        # New behavior: if no stage clears `min_confidence_for_stage`, refuse
        # to classify — return insufficient_data and let the caller surface
        # the input_health flags so the user knows what data was missing.
        max_conf = max((sd["confidence"] for sd in all_scores.values()), default=0.0)
        return {
            "stage": None,
            "stage_label_zh": "資料不足 / 訊號模糊",
            "stage_label_en": "Insufficient",
            "stage_confidence": round(max_conf, 3),
            "scenarios": [],
            "expected_return_pct": 0.0,
            "expected_return_pct_pre_macro": 0.0,
            "expected_return_pct_base": 0.0,
            "macro_adjustments_applied": [],
            "scenario_model_version": "v1.1_declarative",
            "recommended_action": "insufficient_data",
            "next_warning_condition": "supply enough inputs to clear "
                                      f"min_confidence={min_conf} on at least one stage",
            "stage_components_triggered": [],
            "all_stage_scores": all_scores,
            "weights_version": cfg.get("weights_version", "v1.0"),
        }

    # Build scenarios + price targets (target_pct already relative to current price)
    scenarios_in = best_stage_cfg.get("scenarios") or []
    stage_num = int(best_stage_cfg.get("stage_num"))
    price_for_target = components.get("__price_for_target__")  # explicit override

    # ── V1.1: per-ticker scenario adjustment layer ────────────────────
    adjust_cfg = cfg.get("scenario_adjustments") or {}
    adjusted_scenarios, er_base, er_pre_macro = _apply_scenario_adjustments(
        stage_num, scenarios_in, components, adjust_cfg,
    )

    # Compute target_price per scenario (using FINAL target_pct,not base)
    for item in adjusted_scenarios:
        if price_for_target:
            item["target_price"] = round(
                price_for_target * (1 + item["target_pct"] / 100), 2
            )
        else:
            item["target_price"] = None

    # ── Macro overrides (post-classification adjust to E[R]) ──────────
    macro_adjustments_applied = []
    expected_return = er_pre_macro
    macro_cfg = cfg.get("macro_overrides") or {}
    for override_name, override in macro_cfg.items():
        affected = override.get("affected_stages") or []
        if stage_num not in affected:
            continue
        if not _eval_rule(override.get("condition", ""), components):
            continue
        delta = float(override.get("expected_return_adjustment_pct", 0.0))
        expected_return += delta
        macro_adjustments_applied.append({
            "name": override_name,
            "delta_pct": delta,
            "note": override.get("note", ""),
        })

    return {
        "stage": stage_num,
        "stage_label_zh": best_stage_cfg.get("label_zh"),
        "stage_label_en": best_stage_cfg.get("label_en"),
        "stage_confidence": round(best_confidence, 3),
        "scenarios": adjusted_scenarios,
        # ── three-layer E[R] (V1.1 schema) ────────────────────────────
        # base:     V1.0 prior, no ticker delta, no macro (control for 5/31)
        # pre_macro: V1.1 ticker-adjusted scenario sum, NO macro
        # final:    pre_macro + Σ macro_delta (Dashboard 顯這個)
        # NOTE: V1.0 expected_return_pct_pre_macro 語義 = raw stage prior
        #       V1.1 改為 ticker-adjusted (不含 macro)。原語義搬到 _base 欄位。
        #       CHANGELOG 已記為 breaking schema change。
        "expected_return_pct": round(expected_return, 2),
        "expected_return_pct_pre_macro": er_pre_macro,
        "expected_return_pct_base": er_base,
        "macro_adjustments_applied": macro_adjustments_applied,
        "scenario_model_version": "v1.1_declarative",
        "recommended_action": best_stage_cfg.get("recommended_action"),
        "next_warning_condition": best_stage_cfg.get("next_warning_condition"),
        "stage_components_triggered": best_triggered,
        "all_stage_scores": all_scores,
        "weights_version": cfg.get("weights_version", "v1.0"),
    }


if __name__ == "__main__":
    import json
    import sys
    # Smoke test: read components from stdin JSON
    data = json.load(sys.stdin)
    components = data.get("components") if "components" in data else data
    # If quote.price provided, inject for target_price computation
    if "quote" in data and isinstance(data["quote"], dict):
        components["__price_for_target__"] = data["quote"].get("price")
    out = classify(components)
    print(json.dumps(out, indent=2, ensure_ascii=False))

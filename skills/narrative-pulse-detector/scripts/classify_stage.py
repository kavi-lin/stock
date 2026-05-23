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
            "macro_adjustments_applied": [],
            "recommended_action": "insufficient_data",
            "next_warning_condition": "supply enough inputs to clear "
                                      f"min_confidence={min_conf} on at least one stage",
            "stage_components_triggered": [],
            "all_stage_scores": all_scores,
            "weights_version": cfg.get("weights_version", "v1.0"),
        }

    # Build scenarios + price targets (target_pct already relative to current price)
    scenarios_in = best_stage_cfg.get("scenarios") or []
    price = components.get("price") or components.get("price_to_sma200_ratio")  # fallback
    # price 從 quote 來的話會在外層放;這裡用 price_to_sma200_ratio * sma200 推不到原價
    # 所以 price 必須由 caller 從 quote 餵進來 — pulse.py 會處理
    price_for_target = components.get("__price_for_target__")  # explicit override

    scenarios_out = []
    expected_return = 0.0
    for s in scenarios_in:
        prob = float(s.get("prob", 0.0))
        tgt_pct = float(s.get("target_pct", 0.0))
        scenarios_out.append({
            "label": s.get("label"),
            "label_en": s.get("label_en"),
            "prob": prob,
            "target_pct": tgt_pct,
            "target_price": round(price_for_target * (1 + tgt_pct / 100), 2)
                           if price_for_target else None,
        })
        expected_return += prob * tgt_pct

    # ── Macro overrides (V1.1 post-classification adjust) ──────────────
    stage_num = int(best_stage_cfg.get("stage_num"))
    macro_adjustments_applied = []
    expected_return_raw = round(expected_return, 2)
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
        "scenarios": scenarios_out,
        "expected_return_pct": round(expected_return, 2),
        "expected_return_pct_pre_macro": expected_return_raw,
        "macro_adjustments_applied": macro_adjustments_applied,
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

"""Deterministic News Arbiter verdict semantics shared by producer/validator."""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_HALF_UP

ARBITER_RULE_VERSION = "V2.3"
DIRECTIONAL_THRESHOLD = 0.75
LANES = ("bull", "bear", "sector", "macro")
WEIGHTS = {
    "monetary_policy": {"bull": .15, "bear": .15, "sector": .20, "macro": .50},
    "macro_data": {"bull": .15, "bear": .15, "sector": .20, "macro": .50},
    "geopolitical": {"bull": .15, "bear": .30, "sector": .15, "macro": .40},
    "earnings": {"bull": .25, "bear": .25, "sector": .40, "macro": .10},
    "corporate": {"bull": .25, "bear": .25, "sector": .40, "macro": .10},
    "sector_news": {"bull": .20, "bear": .20, "sector": .50, "macro": .10},
    "sentiment": {"bull": .30, "bear": .30, "sector": .15, "macro": .25},
    "default": {"bull": .25, "bear": .25, "sector": .25, "macro": .25},
}


def directional_bias(net_impact_score: float) -> str:
    """Map a finite -5..+5 score to its directional label."""
    score = float(net_impact_score)
    if not math.isfinite(score) or not -5.0 <= score <= 5.0:
        raise ValueError("net_impact_score must be finite and within -5..+5")
    if score >= DIRECTIONAL_THRESHOLD:
        return "BULLISH"
    if score <= -DIRECTIONAL_THRESHOLD:
        return "BEARISH"
    return "NEUTRAL"


def classify_verdict(net_impact_score: float, binary_risk: bool) -> str:
    """BINARY is an event property; lane score spread is not one."""
    if type(binary_risk) is not bool:
        raise ValueError("binary_risk must be a JSON boolean")
    return "BINARY" if binary_risk else directional_bias(net_impact_score)


def compute_net_impact(
    scores: dict[str, float],
    news_type: str,
    source_credibility: str = "MEDIUM",
    fanout_mode: str = "PER_AGENT_BATCH",
) -> tuple[float, dict[str, float]]:
    """Apply shared weighting, rounding, and deterministic safety caps."""
    if not isinstance(scores, dict) or any(lane not in scores for lane in LANES):
        raise ValueError(f"scores must contain {LANES}")
    weights = WEIGHTS.get(news_type, WEIGHTS["default"])
    total = Decimal("0")
    for lane in LANES:
        value = scores[lane]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"scores.{lane} must be numeric")
        value = float(value)
        if not math.isfinite(value) or not -5 <= value <= 5:
            raise ValueError(f"scores.{lane} must be finite and within -5..+5")
        total += Decimal(str(value)) * Decimal(str(weights[lane]))
    score = float(total.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    if source_credibility == "LOW" and abs(score) > 3:
        score = math.copysign(2.0, score)
    if fanout_mode == "FULL_FALLBACK" and score >= DIRECTIONAL_THRESHOLD:
        score = min(score, 0.7)
    return score, weights

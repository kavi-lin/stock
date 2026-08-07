import pytest

from news.arbiter_rules import classify_verdict, compute_net_impact, directional_bias
from news.scripts.validate_digest_output import _arbiter_semantic_errors


@pytest.mark.parametrize(
    ("score", "expected"),
    [(3.0, "BULLISH"), (0.75, "BULLISH"), (0.74, "NEUTRAL"),
     (-0.74, "NEUTRAL"), (-0.75, "BEARISH"), (-4.0, "BEARISH")],
)
def test_directional_thresholds(score, expected):
    assert directional_bias(score) == expected
    assert classify_verdict(score, False) == expected


def test_binary_is_event_property_not_score_spread():
    assert classify_verdict(0.2, True) == "BINARY"
    assert classify_verdict(3.5, False) == "BULLISH"


def test_shared_weighting_and_safety_caps():
    scores = {"bull": 4, "bear": -2, "sector": 3, "macro": 0}
    assert compute_net_impact(scores, "earnings")[0] == 1.7
    assert compute_net_impact({k: 5 for k in scores}, "default", "LOW")[0] == 2.0
    assert compute_net_impact(scores, "earnings", fanout_mode="FULL_FALLBACK")[0] == 0.7


def _semantic_verdict(**overrides):
    data = {
        "news_id": "n0001", "event_id": "news_0123456789abcdef",
        "verdict": "BULLISH", "net_impact_score": 1.0,
        "binary_risk": False, "binary_event_date": None,
        "news_type": "default", "source_credibility": "HIGH",
        "lane_scores": {"bull": 4, "bear": -2, "sector": 1, "macro": 1},
        "lane_confidences": {"bull": .8, "bear": .7, "sector": .8, "macro": .7},
        "weights_used": {"bull": .25, "bear": .25, "sector": .25, "macro": .25},
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -5.1, 5.1])
def test_non_finite_or_out_of_range_score_rejected(bad):
    with pytest.raises(ValueError):
        directional_bias(bad)


def test_validator_rejects_legacy_binary_collapse():
    errors = _arbiter_semantic_errors(_semantic_verdict(
        verdict="BINARY",
        binary_risk=False,
    ))
    assert any("requires 'BULLISH'" in e for e in errors)


def test_validator_accepts_explicit_binary_with_bias_and_date():
    errors = _arbiter_semantic_errors(_semantic_verdict(
        news_id="n0002",
        verdict="BINARY",
        net_impact_score=-1.0,
        binary_risk=True,
        directional_bias="BEARISH",
        binary_event_date="2026-08-08",
        lane_scores={"bull": 1, "bear": -5, "sector": -1, "macro": 1},
    ))
    assert errors == []


def test_validator_requires_binary_metadata():
    errors = _arbiter_semantic_errors(_semantic_verdict(
        news_id="n0003",
        verdict="BINARY",
        binary_risk=True,
        directional_bias="BEARISH",
        binary_event_date=None,
    ))
    assert any("directional_bias" in e for e in errors)
    assert any("binary_event_date" in e for e in errors)

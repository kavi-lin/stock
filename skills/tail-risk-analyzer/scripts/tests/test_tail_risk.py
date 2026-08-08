#!/usr/bin/env python3
"""tail_risk.py — fragility bands, weights, and the <30-bar degradation contract.

Zero network: patches `tail_risk.fetch_history` — the price path moved to
technical_core in V4.113.3, so patching `yf.Ticker` no longer intercepts anything.

The 30/60 bands and the .10/.10/.15/.30/.35 weights asserted here are mirrored in
`trade_plan_builder.py:102`, `validate_session_export.py:386` + the §14b enum gate, and
`replay_trade_plan.py`. A change that turns these tests red is a change that has to land
in all of those at once.
"""
import json
import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tail_risk as tr  # noqa: E402


def _prices_from_returns(rets, start=100.0):
    px, cur = [start], start
    for r in rets:
        cur *= (1 + r)
        px.append(cur)
    return px


def _fake_fetch(closes=None, empty=False):
    """Stand-in for technical_core.fetch_history: returns (hist_df, yf_handle).

    V4.113.3 moved the price path here from `yf.Ticker(...).history(...)`. Patching
    `yf.Ticker` no longer intercepts anything — the old tests kept passing while making
    live network calls (the suite went from <1s to 72s), which is exactly the failure
    mode MAINTENANCE §2c exists to catch.
    """
    df = pd.DataFrame() if empty else pd.DataFrame({"Close": closes})
    return lambda *a, **k: (df, MagicMock())


def _run(closes):
    with patch.object(tr, "fetch_history", side_effect=_fake_fetch(closes)):
        return tr.compute("TEST", "1y")


# ── degradation contract ────────────────────────────────────────────────────

def test_empty_history_raises():
    with patch.object(tr, "fetch_history", side_effect=_fake_fetch(empty=True)):
        with pytest.raises(ValueError, match="insufficient data"):
            tr.compute("TEST", "1y")


@pytest.mark.parametrize("n_bars", [0, 1, 29])
def test_under_thirty_bars_raises(n_bars):
    """The floor is 30 bars. Below it the script must refuse rather than emit a label —
    the consumer then takes MODERATE ×0.75, never ROBUST (protocol :1310-1313)."""
    with patch.object(tr, "fetch_history", side_effect=_fake_fetch([100.0] * n_bars)):
        with pytest.raises(ValueError, match="insufficient data"):
            tr.compute("TEST", "1y")


def test_thirty_bars_is_accepted():
    """Exactly at the boundary the script produces a real result — off-by-one here would
    silently degrade every short-history ticker."""
    out = _run([100.0 + i * 0.1 for i in range(30)])
    assert out["sample_days"] == 29        # pct_change drops the first bar
    assert out["fragility_label"] in ("ROBUST", "MODERATE", "FRAGILE")


def test_main_emits_error_json_and_exit_1(capsys):
    """The degradation path the consumer parses: {"error", "ticker"} on stdout, rc=1."""
    argv = ["tail_risk.py", "TEST", "--json-only"]
    with patch.object(sys, "argv", argv), \
         patch.object(tr, "fetch_history", side_effect=_fake_fetch(empty=True)):
        with pytest.raises(SystemExit) as exc:
            tr.main()

    assert exc.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ticker"] == "TEST"
    assert "insufficient data" in payload["error"]


# ── fragility bands (mirrored in three downstream files) ────────────────────

@pytest.mark.parametrize("score,label,mult", [
    (0.0, "ROBUST", 1.0), (29.9, "ROBUST", 1.0),
    (30.0, "MODERATE", 0.75), (59.9, "MODERATE", 0.75),
    (60.0, "FRAGILE", 0.5), (100.0, "FRAGILE", 0.5),
])
def test_fragility_bands(score, label, mult):
    """30 and 60 are inclusive-lower. SKILL.md claimed 35/65 until V4.111.7; no code or
    consumer ever used those numbers."""
    assert tr.fragility_for(score) == (label, mult)


def test_fragility_bands_cover_every_score_exactly_once():
    """No gap and no overlap across 0-100 — a hole here would return None and crash
    compute() at the tuple unpack."""
    for tenth in range(0, 1001):
        assert tr.fragility_for(tenth / 10.0) is not None


def test_compute_uses_the_band_table():
    """The table is not decorative: compute() must route through it, so a change to
    FRAGILITY_BANDS actually moves the emitted label."""
    closes = [100.0 + i * 0.1 for i in range(200)]
    out = _run(closes)
    assert (out["fragility_label"], out["position_multiplier"]) == \
        tr.fragility_for(out["tail_risk_score"])


def test_label_and_multiplier_never_disagree():
    """trade_plan_builder trusts the label and cross-checks the score against its band."""
    table = {"ROBUST": (0, 30, 1.0), "MODERATE": (30, 60, 0.75), "FRAGILE": (60, 101, 0.5)}
    for closes in ([100.0 + i * 0.05 for i in range(250)],
                   _prices_from_returns([0.05, -0.06] * 125)):
        out = _run(closes)
        lo, hi, mult = table[out["fragility_label"]]
        assert lo <= out["tail_risk_score"] < hi
        assert out["position_multiplier"] == mult


def test_calm_series_is_robust_and_wild_series_is_fragile():
    """End-to-end sanity: the score must actually discriminate, not just stay in range."""
    calm = _run([100.0 + i * 0.01 for i in range(250)])
    wild = _run(_prices_from_returns([0.08, -0.09] * 125))

    assert calm["fragility_label"] == "ROBUST"
    assert wild["fragility_label"] == "FRAGILE"
    assert calm["tail_risk_score"] < wild["tail_risk_score"]


# ── weights (SKILL.md was wrong about these until V4.111.7) ─────────────────

def test_component_weights_are_the_documented_ones(monkeypatch):
    """Drive each normalizer to a known value and confirm the blend is
    .10 kurt / .10 skew / .15 var / .30 dd / .35 vol — NOT the 30/20/20/20/10 the SKILL.md
    used to claim. Feeding 100 through one component at a time reads its weight directly."""
    closes = [100.0 + i * 0.1 for i in range(250)]
    weights = {}
    for idx, name in enumerate(["kurt", "skew", "var", "dd", "vol"]):
        calls = {"n": 0}

        def fake_clamp(v, lo=0, hi=100, _idx=idx, _calls=calls):
            # compute() calls clamp() five times in order: kurt, skew, var, dd, vol
            out = 100.0 if _calls["n"] == _idx else 0.0
            _calls["n"] += 1
            return out

        # No raising=False: `clamp` is module-level now, so a rename must blow up loudly
        # here rather than silently create an unused attribute and leave this test inert.
        monkeypatch.setattr(tr, "clamp", fake_clamp)
        weights[name] = _run(closes)["tail_risk_score"] / 100.0

    assert weights == pytest.approx(
        {"kurt": 0.10, "skew": 0.10, "var": 0.15, "dd": 0.30, "vol": 0.35}, abs=1e-6)
    assert sum(weights.values()) == pytest.approx(1.0)


def _expected_score(out, skew_contributes=True):
    """Recompute the score from the emitted raw metrics using the documented normalizers
    and weights. Comparing this to `tail_risk_score` locks the whole blend at once —
    including the rule that only *negative* skew contributes."""
    sk = out["skewness"]
    n_skew = tr.clamp(-sk * 40) if (skew_contributes and sk < 0) else 0
    return round(
        tr.clamp(out["excess_kurtosis"] * 8) * 0.10
        + n_skew * 0.10
        + tr.clamp(out["var_95"] * 15) * 0.15
        + tr.clamp(out["max_drawdown"] * 2) * 0.30
        + tr.clamp(out["ann_vol"] * 1.5) * 0.35,
        1,
    )


@pytest.mark.parametrize("closes", [
    [100.0 + i * 0.01 for i in range(250)],
    [100.0 + i * 0.1 for i in range(250)],
    _prices_from_returns([0.05, -0.06] * 125),
    _prices_from_returns([-0.12] + [0.004] * 200),
])
def test_score_matches_the_documented_formula(closes):
    """Rounding in the emitted metrics costs a little precision, hence the tolerance."""
    out = _run(closes)
    assert out["tail_risk_score"] == pytest.approx(_expected_score(out), abs=0.5)


def test_positive_skew_contributes_nothing():
    """`n_skew = -skew×40 if skew < 0 else 0`. For a right-skewed series the skew term must
    be exactly zero — treating |skew| as fragility would penalize big *up* days."""
    out = _run(_prices_from_returns([0.12] + [-0.004] * 200))
    assert out["skewness"] > 0
    # With positive skew, the skew_contributes flag makes no difference at all.
    assert _expected_score(out, skew_contributes=True) == _expected_score(out, skew_contributes=False)
    assert out["tail_risk_score"] == pytest.approx(_expected_score(out), abs=0.5)


def test_negative_skew_does_contribute():
    """The mirror of the above: a left-tailed series must score strictly higher than it
    would with the skew term switched off, or the component is dead."""
    out = _run(_prices_from_returns([-0.12] + [0.004] * 200))
    assert out["skewness"] < 0
    assert _expected_score(out, skew_contributes=True) > _expected_score(out, skew_contributes=False)


def test_clamp_bounds_each_component():
    assert tr.clamp(-50) == 0
    assert tr.clamp(150) == 100
    assert tr.clamp(42.5) == 42.5


# ── metric correctness ──────────────────────────────────────────────────────

def test_max_drawdown_matches_a_hand_computed_path():
    """+10% then -50% then flat: peak 110, trough 55 → 50% drawdown."""
    closes = _prices_from_returns([0.10, -0.50, 0.0, 0.0] + [0.0] * 40)
    out = _run(closes)
    assert out["max_drawdown"] == pytest.approx(50.0, abs=0.5)


def test_var95_is_reported_as_a_positive_loss():
    """var_95 is `-percentile(rets, 5) × 100` — a loss is a positive number in this schema."""
    out = _run(_prices_from_returns([-0.03] * 20 + [0.01] * 200))
    assert out["var_95"] > 0


def test_flat_series_has_zero_dispersion():
    """std == 0 must not divide by zero in the kurtosis/skew expressions."""
    out = _run([100.0] * 250)
    assert out["excess_kurtosis"] == 0.0
    assert out["skewness"] == 0.0
    assert out["ann_vol"] == 0.0
    assert out["fragility_label"] == "ROBUST"


def test_downside_deviation_with_one_negative_day_is_not_nan():
    """B7 regression: pandas std is ddof=1, so a single negative return divides by zero
    and yields NaN. json.dumps writes that as the bare literal `NaN` — not valid strict
    JSON, so any consumer using a strict parser would choke on the payload.

    Seeding the bug back (`len(neg) > 0`) turns this red.
    """
    closes = _prices_from_returns([0.01] * 100 + [-0.02] + [0.01] * 100)
    out = _run(closes)

    assert out["downside_deviation"] == 0.0
    assert not math.isnan(out["downside_deviation"])
    json.dumps(out, allow_nan=False)          # strict mode: raises if any NaN survived


def test_downside_deviation_is_real_with_two_or_more_negative_days():
    """The guard must not swallow the genuine statistic — two negative days is enough."""
    closes = _prices_from_returns([0.01] * 100 + [-0.02, -0.03] + [0.01] * 100)
    out = _run(closes)

    assert out["downside_deviation"] > 0.0


def test_no_output_field_is_nan():
    """Nothing else in the payload may leak NaN either — strict json.dumps over a range
    of shapes, including the degenerate flat series."""
    for closes in ([100.0] * 250,
                   [100.0 + i * 0.1 for i in range(250)],
                   _prices_from_returns([0.01] * 100 + [-0.02] + [0.01] * 100),
                   _prices_from_returns([0.08, -0.09] * 125)):
        json.dumps(_run(closes), allow_nan=False)


def test_sample_days_counts_returns_not_bars():
    out = _run([100.0 + i * 0.1 for i in range(250)])
    assert out["sample_days"] == 249


# ── output shape (golden keys) ──────────────────────────────────────────────

def test_output_golden_keys():
    out = _run([100.0 + i * 0.1 for i in range(250)])
    assert set(out) == {
        "ticker", "generated_at", "lookback", "sample_days", "excess_kurtosis",
        "skewness", "var_95", "max_drawdown", "ann_vol", "downside_deviation",
        "tail_risk_score", "fragility_label", "position_multiplier",
    }
    assert all(isinstance(out[k], float) or math.isnan(out[k]) for k in
               ("excess_kurtosis", "skewness", "var_95", "max_drawdown", "ann_vol"))


def test_fragility_label_stays_inside_the_validator_enum():
    """§14b (validate_session_export.py:1545-1549) rejects anything outside these three.
    History holds RESILIENT / EXTREMELY FRAGILE from older builds; the script must never
    emit a fourth value again."""
    for closes in ([100.0] * 250,
                   [100.0 + i * 0.1 for i in range(250)],
                   _prices_from_returns([0.08, -0.09] * 125)):
        assert _run(closes)["fragility_label"] in ("ROBUST", "MODERATE", "FRAGILE")


def test_ticker_is_uppercased():
    with patch.object(tr, "fetch_history", side_effect=_fake_fetch([100.0 + i * 0.1 for i in range(250)])):
        assert tr.compute("spy", "1y")["ticker"] == "SPY"

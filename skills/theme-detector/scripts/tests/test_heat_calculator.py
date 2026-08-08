"""Tests for calculators/heat_calculator.py — Theme Heat Score (0-100).

**Rewritten V4.113.2.** The previous version was failing 22/24 because it pinned the
V2.18-era formulas while commit 3afa76d (V2.19.2) replaced every one of them:

| function | old (what the tests asserted) | current |
|---|---|---|
| `momentum_strength_score` | plain sigmoid `100/(1+exp(-0.15*(|wr|-5)))` | log-sigmoid, midpoint 15% |
| `volume_intensity_score`  | linear `(ratio-0.8)*250`, ceiling at 1.2 | sqrt scaling, ceiling at 2.0 |
| `uptrend_signal_score`    | discrete 80/60/60/20 buckets | continuous `min(80, ratio*100)` + bonuses |
| `breadth_signal_score`    | linear | power curve `ratio^2.5 * 80` + count bonus |

`uptrend_signal_score` also changed its **input convention**: `ratio` is now a 0-1
fraction (the code multiplies by 100), where the old tests passed percentages like 50.

Expected values below are derived from each function's documented formula, not copied
from its current output — otherwise this file would just rubber-stamp whatever the code
happens to do. Midpoints and clamps are asserted by construction.
"""

import math

import pytest
from calculators.heat_calculator import (
    HEAT_WEIGHTS,
    breadth_signal_score,
    calculate_theme_heat,
    momentum_strength_score,
    structural_shift_bonus,
    uptrend_signal_score,
    volume_intensity_score,
)


# ── momentum_strength_score ──────────────────────────────────────────
# 100 / (1 + exp(-2.0 * (ln(1+|wr|) - ln(16))))   midpoint at |wr| = 15%

def _momentum_ref(wr):
    return 100.0 / (1.0 + math.exp(-2.0 * (math.log(1.0 + abs(wr)) - math.log(16.0))))


class TestMomentumStrengthScore:

    def test_midpoint_is_fifteen_percent(self):
        """The one design intent stated in the docstring: |wr| = 15% scores exactly 50.
        ln(1+15) == ln(16), so the exponent is 0 by construction."""
        assert momentum_strength_score(15.0) == pytest.approx(50.0, abs=1e-9)

    @pytest.mark.parametrize("wr", [0.0, 5.0, 15.0, 30.0, 50.0, 100.0])
    def test_matches_the_documented_formula(self, wr):
        assert momentum_strength_score(wr) == pytest.approx(_momentum_ref(wr), abs=1e-9)

    @pytest.mark.parametrize("wr,expected", [
        (0.0, 0.4), (5.0, 12.3), (15.0, 50.0), (30.0, 79.0), (50.0, 91.0),
    ])
    def test_docstring_examples_are_accurate(self, wr, expected):
        """Guards the exact staleness found in V4.113.2: the docstring listed
        ~3 / ~27 / 50 / ~73 / ~86 — values from a gentler slope than the -2.0 the code
        uses. Only the midpoint was right. If the slope is retuned, this fails and the
        docstring has to be recomputed with it."""
        assert momentum_strength_score(wr) == pytest.approx(expected, abs=0.05)

    def test_is_symmetric_in_sign(self):
        """Score is on |wr| — a -20% move is as 'strong' as +20%. Direction lives in
        the uptrend component, not here."""
        assert momentum_strength_score(-20.0) == pytest.approx(momentum_strength_score(20.0))

    def test_is_monotonic_increasing(self):
        vals = [momentum_strength_score(x) for x in (0, 1, 5, 10, 15, 25, 40, 80)]
        assert vals == sorted(vals)

    def test_stays_inside_the_scale(self):
        assert 0.0 <= momentum_strength_score(0.0) <= 100.0
        assert 0.0 <= momentum_strength_score(10_000.0) <= 100.0

    def test_returns_float(self):
        assert isinstance(momentum_strength_score(3.0), float)


# ── volume_intensity_score ───────────────────────────────────────────
# min(100, sqrt(max(0, ratio - 0.8)) / sqrt(1.2) * 100)   ceiling at ratio 2.0

class TestVolumeIntensityScore:

    def test_floor_at_ratio_0_8(self):
        """Below 0.8 the surge signal is absent, not negative."""
        assert volume_intensity_score(80.0, 100.0) == pytest.approx(0.0)

    def test_ceiling_reached_at_ratio_2_0(self):
        """sqrt(2.0-0.8)/sqrt(1.2) == 1 exactly — the ceiling is by construction, not a clamp."""
        assert volume_intensity_score(200.0, 100.0) == pytest.approx(100.0)

    @pytest.mark.parametrize("ratio,expected", [
        (1.0, 40.82), (1.2, 57.74), (1.5, 76.38), (2.0, 100.0),
    ])
    def test_matches_the_documented_curve(self, ratio, expected):
        assert volume_intensity_score(ratio * 100.0, 100.0) == pytest.approx(expected, abs=0.05)

    def test_below_floor_is_clamped_not_negative(self):
        assert volume_intensity_score(50.0, 100.0) == pytest.approx(0.0)

    def test_above_ceiling_is_clamped(self):
        assert volume_intensity_score(500.0, 100.0) == pytest.approx(100.0)

    def test_is_monotonic_increasing(self):
        vals = [volume_intensity_score(r * 100.0, 100.0)
                for r in (0.8, 0.9, 1.0, 1.3, 1.7, 2.0)]
        assert vals == sorted(vals)

    @pytest.mark.parametrize("a,b", [(None, 100.0), (100.0, None), (100.0, 0.0)])
    def test_unknown_inputs_score_neutral_not_zero(self, a, b):
        """50 = 'no information'. Returning 0 would read as 'volume is dead' and drag
        the weighted heat down on a data gap."""
        assert volume_intensity_score(a, b) == pytest.approx(50.0)


# ── uptrend_signal_score ─────────────────────────────────────────────
# per sector: min(80, ratio*100) + 10*(ratio>ma_10) + 10*(slope>0), weighted mean

class TestUptrendSignalScore:

    def _sector(self, ratio, ma_10, slope, weight=1.0):
        return {"sector": "test", "ratio": ratio, "ma_10": ma_10,
                "slope": slope, "weight": weight}

    def test_ratio_is_a_fraction_not_a_percentage(self):
        """Input convention changed in V2.19.2: the code does `ratio * 100`, so 0.5 means
        50% of constituents in an uptrend. Passing 50 here saturates the base at 80."""
        assert uptrend_signal_score(
            [self._sector(ratio=0.5, ma_10=1.0, slope=-1.0)], is_bearish=False
        ) == pytest.approx(50.0)

    def test_base_saturates_at_eighty(self):
        assert uptrend_signal_score(
            [self._sector(ratio=1.0, ma_10=1.0, slope=-1.0)], is_bearish=False
        ) == pytest.approx(80.0)

    def test_both_bonuses_reach_one_hundred(self):
        assert uptrend_signal_score(
            [self._sector(ratio=1.0, ma_10=0.4, slope=0.5)], is_bearish=False
        ) == pytest.approx(100.0)

    def test_ma_bonus_only(self):
        assert uptrend_signal_score(
            [self._sector(ratio=0.5, ma_10=0.4, slope=-0.1)], is_bearish=False
        ) == pytest.approx(60.0)

    def test_slope_bonus_only(self):
        assert uptrend_signal_score(
            [self._sector(ratio=0.3, ma_10=0.4, slope=0.5)], is_bearish=False
        ) == pytest.approx(40.0)

    def test_no_bonus(self):
        assert uptrend_signal_score(
            [self._sector(ratio=0.3, ma_10=0.4, slope=-0.1)], is_bearish=False
        ) == pytest.approx(30.0)

    def test_weighted_average_across_sectors(self):
        data = [self._sector(ratio=0.8, ma_10=0.4, slope=0.5, weight=3.0),   # 80+10+10=100
                self._sector(ratio=0.2, ma_10=0.4, slope=-0.1, weight=1.0)]  # 20
        assert uptrend_signal_score(data, is_bearish=False) == pytest.approx(
            (100.0 * 3 + 20.0 * 1) / 4)

    def test_bearish_inverts(self):
        data = [self._sector(ratio=0.8, ma_10=0.4, slope=0.5)]   # 100 bullish
        assert uptrend_signal_score(data, is_bearish=True) == pytest.approx(0.0)

    def test_empty_is_neutral(self):
        assert uptrend_signal_score([], is_bearish=False) == pytest.approx(50.0)

    def test_explicit_zero_weight_is_silently_treated_as_one(self):
        """**Documents a quirk, does not endorse it** (found V4.113.2).

        `weight = entry.get("weight") or 1.0` — 0.0 is falsy, so an explicitly-zeroed
        sector comes back at full weight instead of being excluded. Same family as the
        V4.111.7 burry bug: a falsy-coalescing idiom swallowing a meaningful zero.

        Consequence: the `if total_weight == 0: return 50.0` guard below is unreachable
        (the empty-list case is already handled at the top), so this test pins 70.0 —
        what the code does — rather than 50.0, what the guard suggests it would do.
        Changing this moves theme heat scores, so it is filed rather than fixed here.
        """
        assert uptrend_signal_score(
            [self._sector(ratio=0.5, ma_10=0.4, slope=0.5, weight=0.0)], is_bearish=False
        ) == pytest.approx(70.0)      # 50 base + 10 ma bonus + 10 slope bonus, weight→1.0

    def test_none_fields_are_treated_as_zero(self):
        data = [{"sector": "x", "ratio": None, "ma_10": None, "slope": None, "weight": None}]
        # ratio 0 → base 0; ratio > ma_10 is False (0 > 0); slope > 0 is False → 0
        assert uptrend_signal_score(data, is_bearish=False) == pytest.approx(0.0)


# ── breadth_signal_score ─────────────────────────────────────────────
# min(100, ratio^2.5 * 80 + min(20, industry_count * 2))

class TestBreadthSignalScore:

    @pytest.mark.parametrize("ratio,expected", [
        (0.5, 14.14), (0.7, 32.80), (0.9, 61.47), (1.0, 80.0),
    ])
    def test_matches_the_documented_power_curve(self, ratio, expected):
        assert breadth_signal_score(ratio) == pytest.approx(expected, abs=0.05)

    def test_power_curve_suppresses_low_ratios(self):
        """Exponent 2.5 is the point: half the industries positive is weak, not average."""
        assert breadth_signal_score(0.5) < 0.5 * 80

    def test_industry_count_bonus_caps_at_twenty(self):
        assert breadth_signal_score(1.0, industry_count=3) == pytest.approx(86.0)
        assert breadth_signal_score(1.0, industry_count=10) == pytest.approx(100.0)
        assert breadth_signal_score(1.0, industry_count=50) == pytest.approx(100.0)

    def test_result_is_clamped_to_one_hundred(self):
        assert breadth_signal_score(1.0, industry_count=999) == 100.0

    def test_negative_ratio_floors_at_the_bonus(self):
        assert breadth_signal_score(-0.5, industry_count=2) == pytest.approx(4.0)

    def test_none_is_neutral(self):
        assert breadth_signal_score(None) == pytest.approx(50.0)

    def test_none_ignores_the_count_bonus(self):
        """Unknown breadth must stay neutral — the bonus must not leak a signal in."""
        assert breadth_signal_score(None, industry_count=10) == pytest.approx(50.0)


# ── structural_shift_bonus (V2.19.2) ─────────────────────────────────

class TestStructuralShiftBonus:

    @pytest.mark.parametrize("hits,expected", [
        ({}, 0.0),
        ({"CANDIDATE": 1}, 5.0),
        ({"CANDIDATE": 9}, 5.0),                        # candidates do not stack
        ({"CONFIRMED": 1}, 10.0),
        ({"CONFIRMED": 2}, 15.0),                       # +5 for breadth beyond the first
        ({"CONFIRMED": 9}, 15.0),                       # capped
        ({"CONFIRMED": 1, "CANDIDATE": 5}, 10.0),       # CONFIRMED wins the elif
    ])
    def test_bonus_table(self, hits, expected):
        assert structural_shift_bonus(hits) == pytest.approx(expected)

    def test_cap_is_fifteen(self):
        """Capped so an earnings-momentum signal cannot drown out price/volume."""
        assert structural_shift_bonus({"CONFIRMED": 100, "CANDIDATE": 100}) == 15.0

    @pytest.mark.parametrize("bad", [None, "x", 42, []])
    def test_malformed_input_scores_zero(self, bad):
        assert structural_shift_bonus(bad) == pytest.approx(0.0)


# ── calculate_theme_heat ─────────────────────────────────────────────

class TestCalculateThemeHeat:

    def test_weights_sum_to_one(self):
        """Otherwise the composite silently leaves the 0-100 scale."""
        assert sum(HEAT_WEIGHTS.values()) == pytest.approx(1.0)

    def test_weighted_sum(self):
        out = calculate_theme_heat(momentum=100.0, volume=0.0, uptrend=100.0, breadth=0.0)
        assert out == pytest.approx(
            100 * HEAT_WEIGHTS["momentum"] + 100 * HEAT_WEIGHTS["uptrend"])

    def test_all_none_is_neutral(self):
        assert calculate_theme_heat(None, None, None, None) == pytest.approx(50.0)

    @pytest.mark.parametrize("key", ["momentum", "volume", "uptrend", "breadth"])
    def test_each_none_defaults_to_fifty(self, key):
        kwargs = dict(momentum=100.0, volume=100.0, uptrend=100.0, breadth=100.0)
        kwargs[key] = None
        expected = 100.0 - 50.0 * HEAT_WEIGHTS[key]
        assert calculate_theme_heat(**kwargs) == pytest.approx(expected)

    def test_structural_bonus_is_additive(self):
        base = calculate_theme_heat(50.0, 50.0, 50.0, 50.0)
        with_bonus = calculate_theme_heat(50.0, 50.0, 50.0, 50.0,
                                          structural_tier_hits={"CONFIRMED": 1})
        assert with_bonus - base == pytest.approx(10.0)

    def test_bonus_cannot_push_past_one_hundred(self):
        assert calculate_theme_heat(100.0, 100.0, 100.0, 100.0,
                                    structural_tier_hits={"CONFIRMED": 5}) == 100.0

    def test_falsy_tier_hits_add_nothing(self):
        base = calculate_theme_heat(50.0, 50.0, 50.0, 50.0)
        assert calculate_theme_heat(50.0, 50.0, 50.0, 50.0,
                                    structural_tier_hits={}) == pytest.approx(base)

    def test_output_is_clamped_to_the_scale(self):
        assert calculate_theme_heat(0.0, 0.0, 0.0, 0.0) == 0.0
        assert calculate_theme_heat(100.0, 100.0, 100.0, 100.0) == 100.0

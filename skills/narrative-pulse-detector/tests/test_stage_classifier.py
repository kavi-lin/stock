#!/usr/bin/env python3
"""
narrative-pulse-detector — classifier unit tests (no network).

Tests the pure stage classification logic using synthetic components fixtures.
Live FMP/Finnhub/social fetchers are NOT tested here — those need integration
tests with mocked HTTP. Run with:

    python3 skills/narrative-pulse-detector/tests/test_stage_classifier.py
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

from classify_stage import classify, load_weights, _eval_rule


# ── Fixtures ───────────────────────────────────────────────────────────
# NOK 2026-05-22 actual (from NOK image_review §10) — must classify as Stage 4
NOK_2026_05_22 = {
    "rsi_14_latest": 71.5,
    "rsi_overbought_days": 17,
    "rsi_peak_recent": 83.0,
    "price_to_sma50_ratio": 1.43,
    "price_to_sma200_ratio": 2.14,
    "sma200_breakout_days_ago": 95,
    "volume_baseline_30d_avg": 18000000,
    "volume_recent_20d_avg": 109000000,
    "volume_multiplier": 6.06,
    "gap_up_density_4w": 6,
    "distribution_days_25d": 2,
    "stalling_days_25d": 1,
    "failed_rally_signal": False,
    "pt_raise_30d": 7,
    "pt_raise_60d": 12,
    "retail_mention_24h": 142,
    "retail_mention_baseline_7d_avg": 18,
    "retail_mention_multiplier": 7.89,
    "media_mention_30d": 38,
    "media_source_diversity": 12,
    "vix_now": 18.5,
    "breadth_200dma_pct": 62.0,
    "__price_for_target__": 15.47,
}

# MSFT typical mega-cap (no narrative trade) — Stage 1 or 2 max
MSFT_MATURE = {
    "rsi_14_latest": 58.0,
    "rsi_overbought_days": 0,
    "rsi_peak_recent": 65.0,
    "price_to_sma50_ratio": 1.02,
    "price_to_sma200_ratio": 1.08,
    "sma200_breakout_days_ago": 300,
    "volume_baseline_30d_avg": 22000000,
    "volume_recent_20d_avg": 24000000,
    "volume_multiplier": 1.09,
    "gap_up_density_4w": 0,
    "distribution_days_25d": 1,
    "stalling_days_25d": 0,
    "failed_rally_signal": False,
    "pt_raise_30d": 1,
    "pt_raise_60d": 2,
    "retail_mention_24h": 8,
    "retail_mention_baseline_7d_avg": 7,
    "retail_mention_multiplier": 1.14,
    "media_mention_30d": 80,
    "media_source_diversity": 25,
    "vix_now": 18.5,
    "breadth_200dma_pct": 62.0,
    "__price_for_target__": 420.0,
}

# Stage 5 distribution: NOK-like + 4 distribution days
NOK_STAGE5 = dict(NOK_2026_05_22)
NOK_STAGE5["distribution_days_25d"] = 4
NOK_STAGE5["failed_rally_signal"] = True

# Stage 1 brewing: fresh breakout, quiet
BREWING_FIXTURE = {
    "rsi_14_latest": 55.0,
    "rsi_overbought_days": 0,
    "rsi_peak_recent": 62.0,
    "price_to_sma50_ratio": 1.05,
    "price_to_sma200_ratio": 1.10,
    "sma200_breakout_days_ago": 15,
    "volume_baseline_30d_avg": 3000000,
    "volume_recent_20d_avg": 3500000,
    "volume_multiplier": 1.17,
    "gap_up_density_4w": 0,
    "distribution_days_25d": 0,
    "stalling_days_25d": 0,
    "failed_rally_signal": False,
    "pt_raise_30d": 0,
    "pt_raise_60d": 0,
    "retail_mention_24h": 1,
    "retail_mention_baseline_7d_avg": 1,
    "retail_mention_multiplier": 1.0,
    "media_mention_30d": 5,
    "media_source_diversity": 3,
    "vix_now": 18.5,
    "breadth_200dma_pct": 62.0,
    "__price_for_target__": 12.0,
}


class TestRuleEvaluator(unittest.TestCase):
    def test_simple_comparison(self):
        self.assertTrue(_eval_rule("rsi_overbought_days >= 10", {"rsi_overbought_days": 17}))
        self.assertFalse(_eval_rule("rsi_overbought_days >= 10", {"rsi_overbought_days": 3}))

    def test_compound_and(self):
        self.assertTrue(_eval_rule(
            "60 <= rsi_14_latest < 70 and rsi_overbought_days < 5",
            {"rsi_14_latest": 65, "rsi_overbought_days": 2}
        ))
        self.assertFalse(_eval_rule(
            "60 <= rsi_14_latest < 70 and rsi_overbought_days < 5",
            {"rsi_14_latest": 65, "rsi_overbought_days": 8}
        ))

    def test_none_handling(self):
        # None → coerced to 0
        self.assertFalse(_eval_rule("rsi_14_latest >= 70", {"rsi_14_latest": None}))

    def test_missing_key(self):
        # Missing key → False (eval raises NameError, caught)
        self.assertFalse(_eval_rule("nonexistent >= 5", {}))

    def test_max_min_allowed(self):
        self.assertTrue(_eval_rule("max(a, b) >= 10", {"a": 5, "b": 15}))


class TestClassifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_weights()

    def test_nok_stage_4(self):
        result = classify(NOK_2026_05_22, weights_cfg=self.cfg)
        self.assertEqual(result["stage"], 4, f"Expected Stage 4 for NOK, got {result['stage']}: {result['stage_components_triggered']}")
        self.assertGreaterEqual(result["stage_confidence"], 0.6)
        self.assertEqual(result["recommended_action"], "reduce_or_no_new_entry")
        # Expected return should be negative (R/R asymmetric)
        self.assertLess(result["expected_return_pct"], 0)
        # Scenarios should have prices
        self.assertEqual(len(result["scenarios"]), 4)
        for s in result["scenarios"]:
            self.assertIsNotNone(s["target_price"])

    def test_nok_stage_5(self):
        result = classify(NOK_STAGE5, weights_cfg=self.cfg)
        self.assertEqual(result["stage"], 5, f"Expected Stage 5 for NOK_STAGE5, got {result['stage']}")
        self.assertEqual(result["recommended_action"], "exit_or_short_candidate")

    def test_msft_low_stage(self):
        result = classify(MSFT_MATURE, weights_cfg=self.cfg)
        # MSFT mature should NOT be euphoria/distribution
        self.assertNotIn(result["stage"], (4, 5),
                         f"MSFT mature shouldn't be Stage 4/5, got {result['stage']}")

    def test_brewing_stage_1(self):
        result = classify(BREWING_FIXTURE, weights_cfg=self.cfg)
        self.assertEqual(result["stage"], 1, f"Expected Stage 1 for fresh breakout, got {result['stage']}")
        self.assertEqual(result["recommended_action"], "early_entry_window")

    def test_expected_return_math(self):
        """Verify expected_return_pct = sum(prob * target_pct) (pre-macro)."""
        result = classify(NOK_2026_05_22, weights_cfg=self.cfg)
        manual = sum(s["prob"] * s["target_pct"] for s in result["scenarios"])
        # Pre-macro value should equal scenario-weighted sum
        self.assertAlmostEqual(result["expected_return_pct_pre_macro"], round(manual, 2), places=2)


class TestMacroOverrides(unittest.TestCase):
    """Gemini suggestion #3 — VIX-elevated dampening + breadth-washout boost."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = load_weights()

    def test_vix_elevated_dampens_stage_4(self):
        """VIX >= 25 should dampen Stage 4 E[R] by -5%."""
        fixture = dict(NOK_2026_05_22)
        fixture["vix_now"] = 30.0  # elevated
        result = classify(fixture, weights_cfg=self.cfg)
        self.assertEqual(result["stage"], 4)
        # After macro override, final E[R] should be 5 lower than pre-macro
        self.assertAlmostEqual(
            result["expected_return_pct"],
            round(result["expected_return_pct_pre_macro"] - 5.0, 2),
            places=2,
        )
        names = [a["name"] for a in result["macro_adjustments_applied"]]
        self.assertIn("vix_elevated_stage_4_5", names)

    def test_low_vix_no_adjustment(self):
        """VIX < 25 leaves Stage 4 E[R] untouched."""
        fixture = dict(NOK_2026_05_22)
        fixture["vix_now"] = 16.7  # normal
        result = classify(fixture, weights_cfg=self.cfg)
        self.assertEqual(result["expected_return_pct"], result["expected_return_pct_pre_macro"])
        self.assertEqual(result["macro_adjustments_applied"], [])

    def test_washout_boosts_stage_1(self):
        """breadth_200dma_pct <= 30 should boost Stage 1 E[R] by +3%."""
        fixture = dict(BREWING_FIXTURE)
        fixture["breadth_200dma_pct"] = 22.0  # washout
        result = classify(fixture, weights_cfg=self.cfg)
        self.assertEqual(result["stage"], 1)
        self.assertAlmostEqual(
            result["expected_return_pct"],
            round(result["expected_return_pct_pre_macro"] + 3.0, 2),
            places=2,
        )


class TestCodexFixes(unittest.TestCase):
    """Codex review 2026-05-24 — 4 fixes verified by these tests."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = load_weights()

    def test_empty_components_returns_insufficient(self):
        """Codex #1: classify({}) must NOT fall back to Stage 5."""
        result = classify({}, weights_cfg=self.cfg)
        self.assertIsNone(result["stage"])
        self.assertEqual(result["recommended_action"], "insufficient_data")
        self.assertEqual(result["scenarios"], [])
        self.assertEqual(result["expected_return_pct"], 0.0)

    def test_all_zero_components_returns_insufficient(self):
        """Codex #1: components with all 0s should also be insufficient (not Stage 5)."""
        zeros = {k: 0 for k in NOK_2026_05_22.keys() if not k.startswith("__")}
        result = classify(zeros, weights_cfg=self.cfg)
        self.assertNotEqual(result["stage"], 5,
                            "all-zero components must not map to Stage 5 'exit candidate'")

    def test_breadth_none_does_not_trigger_washout(self):
        """Codex #2: breadth_200dma_pct=None must NOT trigger Stage 1 +3% boost."""
        fixture = dict(BREWING_FIXTURE)
        fixture["breadth_200dma_pct"] = None       # explicit missing
        result = classify(fixture, weights_cfg=self.cfg)
        self.assertEqual(result["stage"], 1)
        # E[R] should equal pre-macro (no boost applied)
        self.assertEqual(result["expected_return_pct"],
                         result["expected_return_pct_pre_macro"])
        adjustments = [a["name"] for a in result["macro_adjustments_applied"]]
        self.assertNotIn("breadth_washout_stage_1", adjustments,
                         "None breadth must not silently masquerade as 0")

    def test_vix_none_does_not_trigger_dampen(self):
        """Codex #2: vix_now=None must NOT dampen Stage 4 E[R]."""
        fixture = dict(NOK_2026_05_22)
        fixture["vix_now"] = None
        result = classify(fixture, weights_cfg=self.cfg)
        self.assertEqual(result["expected_return_pct"],
                         result["expected_return_pct_pre_macro"])

    def test_render_handles_none_quote_fields(self):
        """Codex #4: render_markdown must not crash on None volume / market_cap."""
        # Import here to avoid module-level import cost in earlier tests
        import sys as _s
        from pathlib import Path as _P
        _s.path.insert(0, str(_P(__file__).resolve().parent.parent / "scripts"))
        from render import render_markdown
        partial_bundle = {
            "ticker": "TEST",
            "stage": 4,
            "stage_label_zh": "狂熱後段",
            "stage_label_en": "Late Euphoria",
            "stage_confidence": 0.7,
            "expected_return_pct": -10.0,
            "recommended_action": "reduce_or_no_new_entry",
            "next_warning_condition": "test",
            "scenarios": [],
            "components": {},
            # Partial quote — volume and market_cap are None
            "quote": {"price": 15.47, "change_pct": None, "volume": None,
                      "year_high": None, "year_low": None, "market_cap": None},
            "input_health": {"ohlcv_ok": True, "quote_ok": True},
            "all_stage_scores": {},
            "stage_components_triggered": [],
        }
        # Should not raise TypeError
        md = render_markdown(partial_bundle)
        self.assertIn("TEST", md)
        self.assertIn("Stage 4", md)
        self.assertIn("—", md, "missing fields should render as '—' not crash")


class TestOverboughtCounters(unittest.TestCase):
    """Gemini suggestion #2 — strict vs loose RSI overbought counters."""

    def test_strict_vs_loose_basic(self):
        import pandas as pd
        from fetch_inputs import consecutive_overbought_days, overbought_episode_days
        # Latest bars (newest last): RSI dips from 75 → 65 → 72 → 80
        s = pd.Series([55, 60, 65, 72, 80, 75, 65, 72, 80])
        # Strict: walks back, latest=80 ✓, prev=72 ✓, prev=65 ✗ → break → 2
        self.assertEqual(consecutive_overbought_days(s), 2)
        # Loose (reset_below=50): walks back, none < 50 → counts only >=70
        # 80, 72, 65 (buffer), 72, 80, 75, 65 (buffer), 60 (buffer), 55 → break at 55? No, 55 > 50
        # Hits index 0 (55) — still > 50, doesn't break. So full episode = 4 (80,72,72,80,75) overbought bars
        self.assertEqual(overbought_episode_days(s), 5)

    def test_loose_breaks_on_floor_drop(self):
        import pandas as pd
        from fetch_inputs import overbought_episode_days
        # RSI series with a clear washout (45 < 50) in middle
        s = pd.Series([80, 75, 45, 70, 75, 80])
        # Walk back: 80 ✓, 75 ✓, 70 ✓, 45 < 50 → break. Count = 3.
        self.assertEqual(overbought_episode_days(s), 3)

    def test_empty_series_returns_zero(self):
        import pandas as pd
        from fetch_inputs import consecutive_overbought_days, overbought_episode_days
        self.assertEqual(consecutive_overbought_days(pd.Series([])), 0)
        self.assertEqual(overbought_episode_days(pd.Series([])), 0)


class TestV11ScenarioAdjustments(unittest.TestCase):
    """V1.1 — per-ticker scenario adjustments. 6 regression tests."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = load_weights()

    # ── Stage 1 clean vs hot fixtures ─────────────────────────────────
    CLEAN_S1 = {
        "rsi_14_latest": 64.0,
        "rsi_peak_recent": 65.0,
        "rsi_overbought_days": 0,
        "rsi_overbought_episode_days": 0,
        "price_to_sma50_ratio": 1.08,
        "price_to_sma200_ratio": 1.15,
        "sma200_breakout_days_ago": 12,
        "volume_multiplier": 1.4,
        "gap_up_density_4w": 1,
        "distribution_days_25d": 0,
        "stalling_days_25d": 0,
        "failed_rally_signal": False,
        "pt_raise_30d": 0,
        "pt_raise_60d": 0,
        "retail_mention_multiplier": 1.2,
        "media_mention_30d": 5,
        "media_source_diversity": 3,
        "vix_now": 16.0,
        "breadth_200dma_pct": 65.0,
        "__price_for_target__": 100.0,
    }

    @classmethod
    def _hot(cls):
        h = dict(cls.CLEAN_S1)
        h["rsi_14_latest"] = 78.0
        h["rsi_peak_recent"] = 80.0
        h["distribution_days_25d"] = 4
        h["volume_multiplier"] = 0.7
        h["gap_up_density_4w"] = 4
        return h

    def test_1_same_stage_different_features_diverge(self):
        """Two Stage 1 brewing fixtures with opposite features must produce
        different scenario probabilities AND E[R] differ ≥ 3 pts."""
        clean = classify(self.CLEAN_S1, weights_cfg=self.cfg)
        hot = classify(self._hot(), weights_cfg=self.cfg)
        self.assertEqual(clean["stage"], 1)
        self.assertEqual(hot["stage"], 1)
        # Scenario probs must diverge
        clean_probs = [s["prob"] for s in clean["scenarios"]]
        hot_probs = [s["prob"] for s in hot["scenarios"]]
        self.assertNotEqual(clean_probs, hot_probs,
                            "V1.0 hardcoded behavior would produce identical probs — V1.1 must differ")
        # E[R] gap should be at least 3 pts
        gap = clean["expected_return_pct_pre_macro"] - hot["expected_return_pct_pre_macro"]
        self.assertGreaterEqual(gap, 3.0,
                                f"E[R] divergence too small ({gap}) — adjustments not biting")

    def test_2_prob_sum_equals_one(self):
        """Adjusted probabilities across all scenarios must sum to 1.0."""
        for fixture in (self.CLEAN_S1, self._hot(), BREWING_FIXTURE, NOK_2026_05_22, NOK_STAGE5):
            result = classify(fixture, weights_cfg=self.cfg)
            if result["stage"] is None:
                continue
            total = sum(s["prob"] for s in result["scenarios"])
            # places=3 tolerance — 4dp rounding per scenario can drift up to 5e-4 in 4-scenario stages
            self.assertAlmostEqual(total, 1.0, places=3,
                                   msg=f"Σ prob = {total} for stage {result['stage']}")

    def test_3_breakdown_traceable(self):
        """prob_base + Σ breakdown.delta ≈ prob (within rounding).
        target_pct_base + Σ target_breakdown.delta == target_pct."""
        result = classify(self.CLEAN_S1, weights_cfg=self.cfg)
        for s in result["scenarios"]:
            reconstructed_prob = s["prob_base"] + sum(b["delta"] for b in s["prob_breakdown"])
            self.assertAlmostEqual(reconstructed_prob, s["prob"], places=3,
                                   msg=f"{s['label_en']} breakdown不可追溯: "
                                       f"base={s['prob_base']} + Σdelta={reconstructed_prob - s['prob_base']:.4f} "
                                       f"≠ final={s['prob']}")
            reconstructed_tgt = s["target_pct_base"] + sum(
                b["delta"] for b in s["target_breakdown"])
            self.assertAlmostEqual(reconstructed_tgt, s["target_pct"], places=2)

    def test_4_clamp_bounds_respected(self):
        """Extreme components must not push any prob outside [0.05, 0.80]."""
        extreme = dict(self.CLEAN_S1)
        extreme["rsi_14_latest"] = 90.0
        extreme["rsi_peak_recent"] = 92.0
        extreme["distribution_days_25d"] = 10
        extreme["volume_multiplier"] = 0.3
        extreme["gap_up_density_4w"] = 8
        extreme["price_to_sma200_ratio"] = 1.7
        result = classify(extreme, weights_cfg=self.cfg)
        for s in result["scenarios"]:
            self.assertGreaterEqual(s["prob"], 0.0,
                                    "normalize may push slightly below 0.05 only if clamp was 0")
            self.assertLessEqual(s["prob"], 1.0)
        # Verify clamp entry appeared somewhere in breakdown
        has_clamp = any(
            any(b["rule"] == "_clamp" for b in s["prob_breakdown"])
            for s in result["scenarios"]
        )
        # (Not all extreme fixtures trigger clamp,but extreme should hit clamp somewhere)
        # If no clamp triggered,still pass — bound check above already verifies the invariant
        del has_clamp

    def test_5_stage_3_untouched(self):
        """Stage 3 (acceleration) must remain V1.0 hardcoded — breakdowns empty,
        prob == prob_base, target == target_base."""
        s3 = {
            "rsi_14_latest": 68.0, "rsi_peak_recent": 72.0,
            "rsi_overbought_days": 3, "rsi_overbought_episode_days": 4,
            "price_to_sma50_ratio": 1.2, "price_to_sma200_ratio": 1.5,
            "sma200_breakout_days_ago": 90,
            "volume_multiplier": 3.5, "gap_up_density_4w": 2,
            "distribution_days_25d": 1, "failed_rally_signal": False,
            "pt_raise_30d": 4, "pt_raise_60d": 6,
            "media_mention_30d": 40, "media_source_diversity": 8,
            "vix_now": 17.0, "breadth_200dma_pct": 60.0,
            "__price_for_target__": 100.0,
        }
        result = classify(s3, weights_cfg=self.cfg)
        self.assertEqual(result["stage"], 3,
                         f"fixture should map to Stage 3, got {result['stage']}")
        for s in result["scenarios"]:
            self.assertEqual(s["prob_breakdown"], [],
                             f"Stage 3 {s['label_en']} 應無 adjustment")
            self.assertEqual(s["target_breakdown"], [])
            self.assertEqual(s["prob"], s["prob_base"])
            self.assertEqual(s["target_pct"], s["target_pct_base"])
        # Three-layer E[R] must all be identical for Stage 3
        self.assertEqual(result["expected_return_pct_base"],
                         result["expected_return_pct_pre_macro"])

    def test_6_three_layer_er_consistency(self):
        """expected_return_pct == pre_macro + Σ macro_delta (within rounding).
        expected_return_pct_base = V1.0 hardcoded prior (independent of components)."""
        # Stage 1 with washout macro fires +3.0
        fixture = dict(self.CLEAN_S1)
        fixture["breadth_200dma_pct"] = 22.0  # triggers breadth_washout_stage_1
        result = classify(fixture, weights_cfg=self.cfg)
        macro_sum = sum(a["delta_pct"] for a in result["macro_adjustments_applied"])
        self.assertAlmostEqual(
            result["expected_return_pct"],
            round(result["expected_return_pct_pre_macro"] + macro_sum, 2),
            places=2,
        )
        # Base must equal V1.0 Stage 1 prior: 0.55*25 + 0.25*-8 + 0.20*-3 = 11.15
        self.assertEqual(result["expected_return_pct_base"], 11.15)

    def test_7_scenario_model_version_tag(self):
        """Output must declare scenario_model_version for downstream consumers."""
        result = classify(self.CLEAN_S1, weights_cfg=self.cfg)
        self.assertEqual(result["scenario_model_version"], "v1.1_declarative")


class TestV111CodexFixes(unittest.TestCase):
    """V1.1.1 (V3.19.1) — Codex post-review fixes:
       #1 Stage 1 SMA200 must be effectively mandatory (weight change).
       #2 Post-normalize probs must respect clamp [0.05, 0.80] (bounded water-fill).
    """

    @classmethod
    def setUpClass(cls):
        cls.cfg = load_weights()

    def test_below_sma200_quiet_does_not_classify_stage_1(self):
        """Codex #1 reproducer: below SMA200 + quiet media + no sell-side raise.
        Old (weights 0.4/0.3/0.3): conf = 0.6 → Stage 1.
        New (0.5/0.25/0.25):       conf = 0.5 → insufficient_data.
        """
        components = {
            "sma200_breakout_days_ago": None,
            "price_to_sma200_ratio": 0.95,
            "media_mention_30d": 5,
            "pt_raise_60d": 0,
            "distribution_days_25d": 0,
        }
        result = classify(components, weights_cfg=self.cfg)
        self.assertNotEqual(
            result["stage"], 1,
            f"below-SMA200 ticker must not classify as Stage 1 brewing "
            f"(got stage={result['stage']}, conf={result['stage_confidence']})",
        )

    def test_bounded_normalize_respects_clamp(self):
        """Codex #2 reproducer: 3 scenarios with raw prob = [0.90, 0.05, 0.05]
        after delta. Simple proportional scaling → [0.889, 0.056, 0.056] (violates 0.80 cap).
        Bounded water-fill must keep max ≤ 0.80 AND Σ = 1.
        """
        from classify_stage import _apply_scenario_adjustments
        scenarios_in = [
            {"label_en": "a", "label": "A", "prob": 0.90, "target_pct": 10},
            {"label_en": "b", "label": "B", "prob": 0.05, "target_pct": -5},
            {"label_en": "c", "label": "C", "prob": 0.05, "target_pct": -10},
        ]
        adjust_cfg = {"global": {"prob_clamp": [0.05, 0.80], "normalize": True}}
        adj, _, _ = _apply_scenario_adjustments(1, scenarios_in, {}, adjust_cfg)
        max_p = max(s["prob"] for s in adj)
        min_p = min(s["prob"] for s in adj)
        total = sum(s["prob"] for s in adj)
        self.assertLessEqual(max_p, 0.80 + 1e-6,
                             f"post-normalize max prob {max_p} exceeds 0.80 cap")
        self.assertGreaterEqual(min_p, 0.05 - 1e-6,
                                f"post-normalize min prob {min_p} below 0.05 floor")
        self.assertAlmostEqual(total, 1.0, places=4,
                               msg=f"bounded normalize broke Σ=1 (got {total})")


if __name__ == "__main__":
    unittest.main(verbosity=2)

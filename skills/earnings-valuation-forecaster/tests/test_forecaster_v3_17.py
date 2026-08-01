#!/usr/bin/env python3
"""V3.17 (Wave 1) — smoke tests for forecaster transition_case + matrix.

Run:
  python3 skills/earnings-valuation-forecaster/tests/test_forecaster_v3_17.py
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

from forecast import (
    _determine_transition_case,
    build_revenue_margin_matrix,
    build_scenarios,
    live_anchor_eligibility,
    to_markdown,
)


class TestTransitionCascade(unittest.TestCase):
    def test_signature_triggers_first(self):
        """Rule #1: signature beats numeric anomaly."""
        bundle = {
            "transition_signature": "mix_only",
            "business_mix_shift_overlay": {"tier": "EMERGING"},
        }
        out = _determine_transition_case(bundle, current_price=100,
                                          income_q=[], ratios_a=[])
        self.assertTrue(out["transition_case"])
        self.assertEqual(out["reason"], "signature_mix_only")

    def test_numeric_anomaly_when_no_signature(self):
        """Rule #2: annual PE > 50 + DCF/price < 0.5 + 5y CAGR < 5% + seg growth > 30%."""
        bundle = {
            "transition_signature": "neither",
            "business_mix_shift_overlay": {
                "tier": "STABLE",
                "new_segment": {"yoy_growth": 0.45},  # 45% > 30%
            },
            "annual_growth": [{"fiveYRevenueGrowthPerShare": 0.02}],  # 2% < 5%
            "valuation": {"dcf_intrinsic": 30},  # DCF/100 = 0.30 < 0.5
        }
        ratios_a = [{"priceToEarningsRatio": 75}]  # 75 > 50
        out = _determine_transition_case(bundle, current_price=100,
                                          income_q=[], ratios_a=ratios_a)
        self.assertTrue(out["transition_case"])
        self.assertEqual(out["reason"], "numeric_anomaly")
        self.assertEqual(out["metrics"]["latest_annual_pe"], 75)
        self.assertEqual(out["metrics"]["segment_yoy_growth"], 0.45)

    def test_false_when_neither_triggers(self):
        bundle = {
            "transition_signature": "neither",
            "business_mix_shift_overlay": {"tier": "STABLE"},
            "annual_growth": [{"fiveYRevenueGrowthPerShare": 0.10}],  # 10% > 5%
            "valuation": {"dcf_intrinsic": 90},  # DCF/100 = 0.90 > 0.5
        }
        ratios_a = [{"priceToEarningsRatio": 30}]  # 30 < 50
        out = _determine_transition_case(bundle, current_price=100,
                                          income_q=[], ratios_a=ratios_a)
        self.assertFalse(out["transition_case"])
        self.assertIsNone(out["reason"])

    def test_live_gate_rejects_low_confidence(self):
        out = live_anchor_eligibility(
            {"cagr": 8.1, "consensus": 154.7, "trend": 2.5},
            "LOW", {"transition_case": False},
        )
        self.assertFalse(out["eligible"])
        self.assertIn("low_forecast_confidence", out["reasons"])

    def test_live_gate_rejects_transition(self):
        out = live_anchor_eligibility(
            {"cagr": 8.1, "trend": 9.0}, "MEDIUM", {"transition_case": True},
        )
        self.assertFalse(out["eligible"])
        self.assertIn("transition_without_safe_model", out["reasons"])

    def test_live_gate_accepts_two_methods(self):
        out = live_anchor_eligibility(
            {"cagr": 8.1, "trend": 9.0}, "MEDIUM", {"transition_case": False},
        )
        self.assertTrue(out["eligible"])
        self.assertEqual(out["reasons"], [])

    def test_no_bundle_returns_false(self):
        """Backward compat: missing earnings-analyst bundle → transition_case=False."""
        out = _determine_transition_case(None, current_price=100,
                                          income_q=[], ratios_a=[])
        self.assertFalse(out["transition_case"])


class TestRevenueMarginMatrix(unittest.TestCase):
    def test_emerging_matrix_4_cells(self):
        info = {"transition_case": True, "reason": "signature_mix_only",
                "mix_tier": "EMERGING"}
        income_q = [
            {"revenue": 1000, "operatingIncome": 80},   # latest
            {"revenue": 950, "operatingIncome": 70},
            {"revenue": 900, "operatingIncome": 65},
            {"revenue": 880, "operatingIncome": 60},
            {"revenue": 850, "operatingIncome": 55},    # prior year
        ]
        matrix = build_revenue_margin_matrix(info, income_q, current_price=100)
        self.assertIsNotNone(matrix)
        self.assertEqual(matrix["matrix_version"], "emerging_v1")
        self.assertEqual(len(matrix["cells"]), 4)
        labels_en = [c["label_en"] for c in matrix["cells"]]
        self.assertEqual(labels_en, ["volume_driven", "margin_driven", "balanced", "bear_reset"])

    def test_established_matrix_4_cells_different_labels(self):
        info = {"transition_case": True, "reason": "signature_both",
                "mix_tier": "ESTABLISHED"}
        income_q = [
            {"revenue": 1000, "operatingIncome": 200},
            {"revenue": 950, "operatingIncome": 180},
            {"revenue": 900, "operatingIncome": 170},
            {"revenue": 880, "operatingIncome": 160},
            {"revenue": 850, "operatingIncome": 150},
        ]
        matrix = build_revenue_margin_matrix(info, income_q, current_price=100)
        self.assertIsNotNone(matrix)
        self.assertEqual(matrix["matrix_version"], "established_v1")
        labels_en = [c["label_en"] for c in matrix["cells"]]
        self.assertEqual(labels_en, ["market_share_consolidation", "moat_validation",
                                     "pricing_power", "disruption_threat"])
        # M4 rename verification — must NOT contain "regime_break"
        self.assertNotIn("regime_break", labels_en)

    def test_matrix_none_when_transition_false(self):
        info = {"transition_case": False, "mix_tier": "STABLE"}
        self.assertIsNone(build_revenue_margin_matrix(info, [], current_price=100))

    def test_cell_has_dual_field_achieves_if(self):
        info = {"transition_case": True, "reason": "signature_mix_only",
                "mix_tier": "EMERGING"}
        income_q = [{"revenue": 1000, "operatingIncome": 80}] * 5
        matrix = build_revenue_margin_matrix(info, income_q, current_price=100)
        for cell in matrix["cells"]:
            self.assertIn("achieves_if_text", cell)
            self.assertIn("achieves_if_struct", cell)
            self.assertIn("revenue_growth_pct", cell["achieves_if_struct"])
            self.assertIn("operating_margin_pct", cell["achieves_if_struct"])
            self.assertIn("narrative", cell["achieves_if_struct"])


class TestBuildScenariosDualField(unittest.TestCase):
    def test_scenarios_have_dual_field(self):
        pe_range = {"pe_p25": 15, "pe_p50": 20, "pe_p75": 25}
        scenarios, grid = build_scenarios(forward_eps=5.0, pe_range=pe_range,
                                           current_price=100)
        for case in ("bear", "base", "bull"):
            s = scenarios[case]
            self.assertIn("achieves_if", s, "legacy field preserved")
            self.assertIn("achieves_if_text", s, "new text field present")
            self.assertIn("achieves_if_struct", s, "new struct field present")
            self.assertEqual(s["achieves_if"], s["achieves_if_text"],
                             "legacy field should mirror text field")
            self.assertIn("eps_delta_pct", s["achieves_if_struct"])
            self.assertIn("pe_percentile", s["achieves_if_struct"])
            self.assertIn("required_eps", s["achieves_if_struct"])


class TestMarkdownRendering(unittest.TestCase):
    def test_transition_matrix_renders_in_markdown(self):
        scenarios, grid = build_scenarios(
            forward_eps=5.0,
            pe_range={"pe_p25": 15, "pe_p50": 20, "pe_p75": 25},
            current_price=100,
        )
        matrix = build_revenue_margin_matrix(
            {"transition_case": True, "reason": "signature_mix_only",
             "mix_tier": "EMERGING"},
            [{"revenue": 1000, "operatingIncome": 80}] * 5,
            current_price=100,
        )
        payload = {
            "ticker": "TEST",
            "current_price": 100,
            "signal": "HOLD",
            "ttm_eps": 4.5,
            "forward_eps": {
                "value": 5.0,
                "confidence": "high",
                "spread_pct": 4.0,
                "methods": {"consensus": 5.0},
            },
            "expected_value": None,
            "expected_value_upside_pct": None,
            "generated_at": "2026-05-24T00:00:00",
            "scenarios": scenarios,
            "revenue_margin_matrix": matrix,
            "sensitivity_grid": grid,
            "sensitivity_axes": {
                "rows": ["PE p25", "PE p50", "PE p75"],
                "cols": ["EPS -15%", "EPS base", "EPS +15%"],
            },
            "multiple_range": {"pe_p25": 15, "pe_p50": 20, "pe_p75": 25,
                               "window_years": 5},
            "multiple_range_effective": {"pe_p25": 15, "pe_p50": 20, "pe_p75": 25},
            "peer_pe_info": {},
            "rate_context": {},
            "caveats": [],
        }
        md = to_markdown(payload)
        self.assertIn("## Revenue-Margin Matrix", md)
        self.assertIn("volume_driven", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)

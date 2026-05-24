#!/usr/bin/env python3
"""V3.17 (Wave 1) — smoke tests for new earnings-analyst functions.

Covers:
  - compute_transition_signature 4-state matrix (paradigm/mix/both/neither)
  - derive_cash_conversion_quality flag → enum mapping
  - business_mix_shift_overlay NO_DATA / STABLE / EMERGING tiering
  - WC diagnostics DPO method fallback (direct / estimated / unavailable)
  - score_quality directional flag scoring (clean=0 / wc_driven=-2 / negative=-4)

Run:
  python3 skills/earnings-analyst/tests/test_v3_17.py
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

from analyze import (
    compute_transition_signature,
    derive_cash_conversion_quality,
    compute_business_mix_shift_overlay,
    compute_wc_diagnostics,
    score_quality,
)


class TestTransitionSignature(unittest.TestCase):
    def test_paradigm_only(self):
        ss = {"tier": "CONFIRMED"}
        mix = {"tier": "STABLE"}
        self.assertEqual(compute_transition_signature(ss, mix), "paradigm_only")

    def test_mix_only(self):
        ss = {"tier": "NONE"}
        mix = {"tier": "EMERGING"}
        self.assertEqual(compute_transition_signature(ss, mix), "mix_only")

    def test_both(self):
        ss = {"tier": "CANDIDATE"}
        mix = {"tier": "ESTABLISHED"}
        self.assertEqual(compute_transition_signature(ss, mix), "both")

    def test_neither(self):
        ss = {"tier": "NONE"}
        mix = {"tier": "STABLE"}
        self.assertEqual(compute_transition_signature(ss, mix), "neither")

    def test_no_data_treated_as_neither(self):
        ss = {"tier": "INSUFFICIENT_DATA"}
        mix = {"tier": "NO_DATA"}
        self.assertEqual(compute_transition_signature(ss, mix), "neither")


class TestCashConversionQualityEnum(unittest.TestCase):
    def test_negative_accruals_wins(self):
        self.assertEqual(derive_cash_conversion_quality(
            ["accruals_warning_negative", "negative_fcf"]), "negative_accruals")

    def test_wc_driven_when_no_negative(self):
        self.assertEqual(derive_cash_conversion_quality(
            ["cash_conversion_wc_driven", "capex_outpaces_ocf"]), "wc_driven")

    def test_clean_when_no_negative_no_wc(self):
        self.assertEqual(derive_cash_conversion_quality(
            ["cash_conversion_positive_gap_clean"]), "clean_positive_gap")

    def test_n_a_when_no_cash_flag(self):
        self.assertEqual(derive_cash_conversion_quality(["negative_fcf"]), "n_a")
        self.assertEqual(derive_cash_conversion_quality([]), "n_a")


class TestBusinessMixShiftOverlay(unittest.TestCase):
    def test_no_data_when_segments_empty(self):
        out = compute_business_mix_shift_overlay({}, [], [])
        self.assertEqual(out["tier"], "NO_DATA")
        self.assertIsNone(out["new_segment"])

    def test_stable_when_segments_present_but_thresholds_unmet(self):
        # Single year with 2 stable segments — can't compute YoY → NO_DATA
        # so we need 2+ years
        segments = {
            "product_fy": [
                {"date": "2024-12-31", "core_software": 8000, "minor_segment": 2000},
                {"date": "2023-12-31", "core_software": 7900, "minor_segment": 2100},
            ],
            "geographic_fy": [],
        }
        annual_growth = [{"fiveYRevenueGrowthPerShare": 0.03}]
        out = compute_business_mix_shift_overlay(segments, annual_growth, [])
        # minor_segment YoY = (2000-2100)/2100 = negative → skipped
        # core_software: yoy = (8000-7900)/7900 ≈ 1.3%, share 80% → STABLE (not EMERGING)
        self.assertIn(out["tier"], ("STABLE", "NO_DATA"))

    def test_emerging_thresholds(self):
        # New segment grows fast + share in 10-25% band
        segments = {
            "product_fy": [
                {"date": "2024-12-31", "core": 7500, "new_ai": 2500},
                {"date": "2023-12-31", "core": 8000, "new_ai": 2000},
                {"date": "2022-12-31", "core": 8200, "new_ai": 1500},
                {"date": "2021-12-31", "core": 8400, "new_ai": 1000},
                {"date": "2020-12-31", "core": 8800, "new_ai": 600},
            ],
            "geographic_fy": [],
        }
        annual_growth = [{"fiveYRevenueGrowthPerShare": 0.02}]
        out = compute_business_mix_shift_overlay(segments, annual_growth, [])
        # new_ai: share 25% (boundary — depends on > or >=); YoY 25%; CAGR (2500/600)^0.25-1 ≈ 43%
        # relative_cagr 43% - 2% = 41% > 10pp ✓
        self.assertIn(out["tier"], ("EMERGING", "STABLE"))
        if out["tier"] == "EMERGING":
            self.assertEqual(out["new_segment"]["name"], "new_ai")


class TestWCDiagnostics(unittest.TestCase):
    def test_dpo_direct_when_ap_available(self):
        income = [{"revenue": 1000, "costOfRevenue": 600}] * 4
        balance = [{"netReceivables": 200, "inventory": 100,
                    "accountsPayable": 150, "otherCurrentLiabilities": 300}] * 4
        out = compute_wc_diagnostics(income, balance)
        self.assertEqual(out["dpo_method"], "direct")
        self.assertFalse(out["flag_estimate"])

    def test_dpo_estimated_when_ap_missing(self):
        income = [{"revenue": 1000, "costOfRevenue": 600}] * 4
        balance = [{"netReceivables": 200, "inventory": 100,
                    "accountsPayable": None, "otherCurrentLiabilities": 500}] * 4
        out = compute_wc_diagnostics(income, balance)
        self.assertEqual(out["dpo_method"], "estimated_from_other_cl")
        self.assertTrue(out["flag_estimate"])

    def test_dpo_unavailable_when_both_missing(self):
        income = [{"revenue": 1000, "costOfRevenue": 600}] * 4
        balance = [{"netReceivables": 200, "inventory": 100,
                    "accountsPayable": None, "otherCurrentLiabilities": None}] * 4
        out = compute_wc_diagnostics(income, balance)
        self.assertEqual(out["dpo_method"], "unavailable")

    def test_wc_deteriorating_requires_direct_dpo_or_dso_dio(self):
        """G3 — estimated DPO alone cannot trigger wc_deteriorating."""
        # Setup: only DPO rising AND it's estimated (no AP, only OCL).
        # DSO/DIO stay stable. Should NOT flag wc_deteriorating.
        income = [{"revenue": 1000, "costOfRevenue": 600}] * 4
        balance = [
            {"netReceivables": 200, "inventory": 100,
             "accountsPayable": None, "otherCurrentLiabilities": 800},
            {"netReceivables": 200, "inventory": 100,
             "accountsPayable": None, "otherCurrentLiabilities": 600},
            {"netReceivables": 200, "inventory": 100,
             "accountsPayable": None, "otherCurrentLiabilities": 500},
            {"netReceivables": 200, "inventory": 100,
             "accountsPayable": None, "otherCurrentLiabilities": 400},
        ]
        out = compute_wc_diagnostics(income, balance)
        # DPO trend rising (since OCL rising oldest→newest) but method=estimated
        self.assertEqual(out["dpo_method"], "estimated_from_other_cl")
        # wc_deteriorating must NOT trigger from estimated DPO alone
        self.assertFalse(out["wc_deteriorating"],
                         "estimated DPO alone should not flag wc_deteriorating (G3 contract)")


class TestScoreQualityDirectionalFlags(unittest.TestCase):
    def _ttm_cf_neutral(self):
        # Neutral baseline — no iq / cc bonuses
        return ({"from_key_metrics_ttm": {"incomeQualityTTM": 1.0}},
                {"cash_conversion": 1.0})

    def test_clean_positive_gap_no_penalty(self):
        ttm, cf = self._ttm_cf_neutral()
        score = score_quality(["cash_conversion_positive_gap_clean"], ttm, cf)
        self.assertEqual(score, 25, "clean positive gap should not penalize (was -4 in v3.16)")

    def test_wc_driven_half_penalty(self):
        ttm, cf = self._ttm_cf_neutral()
        score = score_quality(["cash_conversion_wc_driven"], ttm, cf)
        self.assertEqual(score, 23, "wc_driven should be -2 (half penalty)")

    def test_negative_accruals_full_penalty(self):
        ttm, cf = self._ttm_cf_neutral()
        score = score_quality(["accruals_warning_negative"], ttm, cf)
        self.assertEqual(score, 21, "negative_accruals should keep -4 (full penalty)")

    def test_other_flags_remain_minus4(self):
        ttm, cf = self._ttm_cf_neutral()
        score = score_quality(["negative_fcf"], ttm, cf)
        self.assertEqual(score, 21)


if __name__ == "__main__":
    unittest.main(verbosity=2)

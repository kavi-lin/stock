#!/usr/bin/env python3
"""V3.17.2 — Contract test: fetch.py schema → analyze.py assumption alignment.

Root cause this guards against:
  V3.17.0 implementation of `_identify_new_segment` and `_segment_values`
  read fetch.py's `slim_segment_product` / `slim_segment_geographic` output
  ASSUMING segments rows were flat `{segment_name: revenue}` dicts. The real
  shape (since fetch.py:147-168) is nested:
      {"date": "...", "fiscal_year": 2025, "period": "FY",
       "products": {"Data Center": 100, ...}}
      {"date": "...", "fiscal_year": 2025, "period": "FY",
       "regions":  {"EMEA": 80, ...}}
  Treating the row's top-level keys as segment names made `fiscal_year` (an
  integer metadata key in snake_case) the highest-CAGR "segment" candidate,
  guaranteed to win for any NVDA / AAPL / AMD cache.

  Codex review caught this in V3.17.1 by introducing the `_segment_values`
  helper that picks `products` / `regions` when present and excludes the
  metadata keys. This test file freezes that contract so any future
  fetch.py schema migration cannot silently re-break the analyzer.

Run:
  python3 skills/earnings-analyst/tests/test_fetch_schema_contract.py
  python3 -m pytest skills/earnings-analyst/tests/test_fetch_schema_contract.py
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

from analyze import (
    _segment_values,
    _identify_new_segment,
    compute_business_mix_shift_overlay,
    compute_wc_diagnostics,
)
# V3.17.2 (Codex Finding 3) — round-trip raw FMP → slim_* → analyze so future
# fetch.py schema drift fails this contract instead of silently passing.
from fetch import (
    slim_segment_product,
    slim_segment_geographic,
    slim_balance,
    slim_income,
)


# ── Real-shape fixtures (truncated samples from actual cache files) ──────

# Shape A: nested `products` (current fetch.py for product_fy)
# Mirrors skills/earnings-analyst/cache/AMD_2026-03-28.json:segments.product_fy[0]
NESTED_PRODUCTS_FY = [
    {
        "date": "2026-03-28", "fiscal_year": 2026, "period": "FY",
        "products": {
            "Data Center": 30000,
            "Client and Gaming": 12000,
            "Embedded": 5000,
            "Gaming": 3000,
        },
    },
    {
        "date": "2025-03-28", "fiscal_year": 2025, "period": "FY",
        "products": {
            "Data Center": 18000,
            "Client and Gaming": 11000,
            "Embedded": 6000,
            "Gaming": 3500,
        },
    },
    {
        "date": "2024-03-28", "fiscal_year": 2024, "period": "FY",
        "products": {
            "Data Center": 12000,
            "Client and Gaming": 10500,
            "Embedded": 7000,
            "Gaming": 4000,
        },
    },
    {
        "date": "2023-03-28", "fiscal_year": 2023, "period": "FY",
        "products": {"Data Center": 8000, "Client and Gaming": 10000,
                     "Embedded": 7500, "Gaming": 4500},
    },
    {
        "date": "2022-03-28", "fiscal_year": 2022, "period": "FY",
        "products": {"Data Center": 5000, "Client and Gaming": 9500,
                     "Embedded": 6500, "Gaming": 4800},
    },
]

# Shape B: nested `regions` (current fetch.py for geographic_fy)
# Mirrors NOK cache:segments.geographic_fy[0]
NESTED_REGIONS_FY = [
    {
        "date": "2025-12-31", "fiscal_year": 2025, "period": "FY",
        "regions": {
            "Americas": 6985, "Asia Pacific": 4639, "EMEA Region": 8265,
            "Europe": 6165, "Greater China": 913, "India region": 1534,
        },
    },
    {
        "date": "2024-12-31", "fiscal_year": 2024, "period": "FY",
        "regions": {"Americas": 6500, "Asia Pacific": 4200, "EMEA Region": 7800},
    },
]

# Shape C: legacy flat — `{date, fiscalYear, segment_name: revenue}` (defensive,
# in case any future fetch.py revision emits flat rows). All non-metadata keys
# must still be picked as segment candidates.
LEGACY_FLAT_FY = [
    {"date": "2025-12-31", "fiscalYear": 2025, "period": "FY",
     "core_software": 8000, "new_ai": 2500},
    {"date": "2024-12-31", "fiscalYear": 2024, "period": "FY",
     "core_software": 7900, "new_ai": 2100},
]

# Shape D: pure metadata row (degenerate — should return empty dict not crash)
METADATA_ONLY_ROW = {"date": "2025-12-31", "fiscal_year": 2025, "period": "FY"}


class TestSegmentValues(unittest.TestCase):
    """Contract: _segment_values must flatten nested + exclude all metadata."""

    def test_nested_products_returns_inner_dict(self):
        row = NESTED_PRODUCTS_FY[0]
        out = _segment_values(row, "product")
        self.assertEqual(set(out.keys()),
                         {"Data Center", "Client and Gaming", "Embedded", "Gaming"})
        self.assertEqual(out["Data Center"], 30000)

    def test_nested_regions_returns_inner_dict(self):
        row = NESTED_REGIONS_FY[0]
        out = _segment_values(row, "geographic")
        self.assertIn("EMEA Region", out)
        self.assertEqual(out["Americas"], 6985)
        # Metadata MUST NOT leak in
        self.assertNotIn("fiscal_year", out)
        self.assertNotIn("date", out)
        self.assertNotIn("period", out)

    def test_legacy_flat_falls_back_to_top_level_keys(self):
        row = LEGACY_FLAT_FY[0]
        out = _segment_values(row, "product")
        self.assertEqual(set(out.keys()), {"core_software", "new_ai"})

    def test_metadata_blacklist_excludes_fiscal_year_snake_case(self):
        # The original V3.17.0 bug: `fiscal_year` (snake_case) was not in the
        # metadata blacklist (only `fiscalYear` was), so it survived as a
        # numeric "segment".
        row = {"date": "2025-12-31", "fiscal_year": 2025,
               "period": "FY", "products": {"AI": 100}}
        out = _segment_values(row, "product")
        self.assertNotIn("fiscal_year", out)
        self.assertNotIn("fiscalYear", out)
        self.assertNotIn("date", out)
        self.assertNotIn("period", out)
        self.assertEqual(out, {"AI": 100})

    def test_metadata_blacklist_excludes_fiscal_year_camel_case(self):
        # Defensive: even if a future fetch.py revision switches back to
        # camelCase fiscalYear, the metadata key must not appear as a segment.
        row = {"date": "2025-12-31", "fiscalYear": 2025, "period": "FY",
               "core": 100, "new": 50}
        out = _segment_values(row, "product")
        self.assertNotIn("fiscalYear", out)
        self.assertEqual(out, {"core": 100, "new": 50})

    def test_metadata_only_row_returns_empty(self):
        # Row with no segment values (only metadata) must return {} cleanly.
        out = _segment_values(METADATA_ONLY_ROW, "product")
        self.assertEqual(out, {})

    def test_invalid_input_returns_empty(self):
        self.assertEqual(_segment_values(None, "product"), {})
        self.assertEqual(_segment_values("not_a_dict", "product"), {})
        self.assertEqual(_segment_values([], "product"), {})


class TestIdentifyNewSegment(unittest.TestCase):
    """Contract: _identify_new_segment must NOT nominate metadata as new_segment."""

    def test_nested_products_picks_real_segment_not_metadata(self):
        # This is the exact V3.17.0 -> V3.17.1 regression test. Without
        # _segment_values flatten + blacklist, the AMD-like fixture would
        # nominate `fiscal_year` (integer) as the highest-CAGR "segment".
        # Post-fix: must pick a real product segment name.
        annual_growth = [{"fiveYRevenueGrowthPerShare": 0.05}]
        segments = {"product_fy": NESTED_PRODUCTS_FY, "geographic_fy": []}
        out = _identify_new_segment(segments, annual_growth)
        self.assertIsNotNone(out)
        self.assertIn(out["name"], {"Data Center", "Client and Gaming",
                                     "Embedded", "Gaming"})
        # The exact name should be Data Center (fastest growing in fixture:
        # 5000 → 30000 over 4y vs Client/Gaming ramping slower)
        self.assertEqual(out["name"], "Data Center")
        # Critical: must NOT be a metadata key
        self.assertNotIn(out["name"], {"fiscal_year", "fiscalYear", "date", "period"})

    def test_nested_regions_picks_real_region_not_metadata(self):
        annual_growth = [{"fiveYRevenueGrowthPerShare": 0.02}]
        segments = {"product_fy": [], "geographic_fy": NESTED_REGIONS_FY}
        out = _identify_new_segment(segments, annual_growth)
        # NOK regions fixture: Americas / EMEA / Asia all grow modestly.
        # Whichever wins, must be a region name not metadata.
        if out is not None:
            self.assertNotIn(out["name"], {"fiscal_year", "date", "period"})

    def test_legacy_flat_still_works(self):
        # Defensive: legacy flat shape still selectable.
        annual_growth = [{"fiveYRevenueGrowthPerShare": 0.03}]
        segments = {"product_fy": LEGACY_FLAT_FY, "geographic_fy": []}
        out = _identify_new_segment(segments, annual_growth)
        if out is not None:
            self.assertIn(out["name"], {"core_software", "new_ai"})

    def test_empty_segments_returns_none(self):
        self.assertIsNone(_identify_new_segment({}, []))
        self.assertIsNone(_identify_new_segment(
            {"product_fy": [], "geographic_fy": []}, []))

    def test_metadata_only_rows_returns_none(self):
        # Row exists but has no segment values (only date/period/fiscal_year)
        out = _identify_new_segment(
            {"product_fy": [METADATA_ONLY_ROW, METADATA_ONLY_ROW],
             "geographic_fy": []},
            [])
        self.assertIsNone(out)


class TestBusinessMixShiftOverlayContract(unittest.TestCase):
    """Contract: business_mix_shift_overlay must not crash on real fetch.py shapes."""

    def test_amd_like_fixture_classifies_emerging_strict(self):
        # Data Center share: 30000/50000=60% latest, yoy=(30000-18000)/18000=66%,
        # 5y_cagr=(30000/5000)^0.25 - 1 = 56% (vs consolidated_5y_cagr=0.05)
        # → relative_cagr ≈ 51pp > 10pp ✓
        # Share 60% > 25% → ESTABLISHED candidate, but FY fallback caps at
        # EMERGING because quarterly segment OI is unavailable on FMP free tier.
        #
        # V3.17.2 Codex review fix: assertion was originally
        # `assertIn(tier, {EMERGING, ESTABLISHED, STABLE})` which silently
        # masked the bug where FY-fallback high-share segments stayed STABLE.
        # Now strictly require EMERGING.
        annual_growth = [{"fiveYRevenueGrowthPerShare": 0.05}]
        segments = {"product_fy": NESTED_PRODUCTS_FY, "geographic_fy": []}
        out = compute_business_mix_shift_overlay(segments, annual_growth, [])
        self.assertEqual(out["tier"], "EMERGING",
                         f"Expected EMERGING (share=60% high-growth FY-fallback caps at EMERGING), "
                         f"got {out['tier']} — Codex Finding 1 regression?")
        self.assertEqual(out["new_segment"]["name"], "Data Center")
        self.assertNotIn(out["new_segment"]["name"],
                         {"fiscal_year", "date", "period"})

    def test_fy_fallback_caps_at_emerging(self):
        # Even when share >= 25%, FY-only data must cap tier at EMERGING
        # (per Codex v5 — quarterly segment OI required for ESTABLISHED).
        annual_growth = [{"fiveYRevenueGrowthPerShare": 0.05}]
        segments = {"product_fy": NESTED_PRODUCTS_FY, "geographic_fy": []}
        out = compute_business_mix_shift_overlay(segments, annual_growth, [])
        # FY-fallback mode → tier MUST NOT exceed EMERGING
        self.assertNotEqual(out["tier"], "ESTABLISHED",
                            "FY-fallback cannot reach ESTABLISHED without quarterly OI")
        # And for this high-conviction fixture, FY-fallback MUST reach EMERGING
        # (cannot silently drop to STABLE).
        self.assertEqual(out["tier"], "EMERGING")
        # data_quality_note flags the FY-fallback ceiling
        self.assertIsNotNone(out.get("data_quality_note"))
        note_lower = out["data_quality_note"].lower()
        self.assertTrue(
            any(kw in note_lower for kw in ("quarterly", "emerging", "fmp")),
            f"data_quality_note should mention the ceiling reason; got: {note_lower!r}",
        )

    def test_low_share_high_growth_stays_stable(self):
        # Sanity: if share < 10% even with high growth, tier should be STABLE
        # (10% lower bound is the EMERGING floor).
        low_share_segments = {"product_fy": [
            {"date": "2026-01-01", "fiscal_year": 2026, "period": "FY",
             "products": {"established_core": 9500, "tiny_ai": 500}},
            {"date": "2025-01-01", "fiscal_year": 2025, "period": "FY",
             "products": {"established_core": 9700, "tiny_ai": 300}},
            {"date": "2024-01-01", "fiscal_year": 2024, "period": "FY",
             "products": {"established_core": 9800, "tiny_ai": 200}},
            {"date": "2023-01-01", "fiscal_year": 2023, "period": "FY",
             "products": {"established_core": 9850, "tiny_ai": 150}},
            {"date": "2022-01-01", "fiscal_year": 2022, "period": "FY",
             "products": {"established_core": 9900, "tiny_ai": 100}},
        ], "geographic_fy": []}
        annual_growth = [{"fiveYRevenueGrowthPerShare": 0.01}]
        out = compute_business_mix_shift_overlay(low_share_segments, annual_growth, [])
        # tiny_ai share = 500/10000 = 5% < 10% → STABLE
        self.assertEqual(out["tier"], "STABLE")


class TestWCDiagnosticsBalanceSheetContract(unittest.TestCase):
    """Contract: WC diagnostics must handle the V3.17 slim_balance optional
    fields (accountsPayable / otherCurrentLiabilities) gracefully across the
    three real-world cases:
      - both present (current fetch.py default for new caches)
      - AP missing, OCL present (foreign ADR / pre-V3.17 cache w/ recent re-fetch)
      - both missing (legacy pre-V3.17 cache, never re-fetched)
    """

    def _income_q4(self):
        # Stable revenue + COGS series, 4 quarters newest-first
        return [{"revenue": 1000, "costOfRevenue": 600}] * 4

    def test_ap_present_yields_direct_dpo(self):
        income = self._income_q4()
        balance = [{"netReceivables": 200, "inventory": 100,
                    "accountsPayable": 150,
                    "otherCurrentLiabilities": 300}] * 4
        out = compute_wc_diagnostics(income, balance)
        self.assertEqual(out["dpo_method"], "direct")
        self.assertFalse(out["flag_estimate"])
        self.assertIsNotNone(out["dpo_q4"][0])

    def test_ap_missing_ocl_present_yields_estimated_dpo(self):
        income = self._income_q4()
        balance = [{"netReceivables": 200, "inventory": 100,
                    "accountsPayable": None,
                    "otherCurrentLiabilities": 500}] * 4
        out = compute_wc_diagnostics(income, balance)
        self.assertEqual(out["dpo_method"], "estimated_from_other_cl")
        self.assertTrue(out["flag_estimate"])

    def test_both_missing_yields_unavailable(self):
        # Legacy pre-V3.17 cache shape — neither field exists in slim_balance.
        # Must NOT crash, must classify as "unavailable", DSO/DIO still work.
        income = self._income_q4()
        balance = [{"netReceivables": 200, "inventory": 100}] * 4  # no AP, no OCL
        out = compute_wc_diagnostics(income, balance)
        self.assertEqual(out["dpo_method"], "unavailable")
        # DSO/DIO must still compute from netReceivables / inventory
        self.assertIsNotNone(out["dso_q4"][0])
        self.assertIsNotNone(out["dio_q4"][0])

    def test_ap_zero_treated_as_missing(self):
        # Some FMP responses return AP=0 (not None) when合併揭露.
        # The `accounts_payable > 0` guard means 0 falls through to OCL path.
        income = self._income_q4()
        balance = [{"netReceivables": 200, "inventory": 100,
                    "accountsPayable": 0,
                    "otherCurrentLiabilities": 500}] * 4
        out = compute_wc_diagnostics(income, balance)
        # AP=0 → fall through to estimated path
        self.assertEqual(out["dpo_method"], "estimated_from_other_cl")

    def test_estimated_dpo_alone_cannot_flag_wc_driven(self):
        # G3 contract: estimated DPO trend rising must NOT trigger
        # wc_deteriorating unless DSO or DIO also deteriorates.
        income = self._income_q4()
        # AP missing → DPO=estimated; OCL rising (oldest→newest) so DPO trend rising
        # DSO/DIO stable (constant netReceivables / inventory)
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
        self.assertEqual(out["dpo_method"], "estimated_from_other_cl")
        # WC must NOT flag deteriorating — estimated DPO alone is insufficient
        self.assertFalse(out["wc_deteriorating"])

    def test_dso_deterioration_alone_can_flag_wc_driven(self):
        # Conversely, DSO rising sharply WITHOUT AP/DPO data must still
        # trigger wc_deteriorating (DSO/DIO direct + sustained).
        income = self._income_q4()
        # netReceivables rising: 100 → 150 → 220 → 350 (latest = 350, monotonic up,
        # latest 350 vs 4Q avg (350+220+150+100)/4=205 → 350/205=1.70 > 1.15 ✓
        balance = [
            {"netReceivables": 350, "inventory": 100},   # latest
            {"netReceivables": 220, "inventory": 100},
            {"netReceivables": 150, "inventory": 100},
            {"netReceivables": 100, "inventory": 100},
        ]
        out = compute_wc_diagnostics(income, balance)
        self.assertEqual(out["dso_q4_trend"], "rising")
        self.assertTrue(out["dso_deteriorating"])
        self.assertTrue(out["wc_deteriorating"])


class TestRealFixtureSmoke(unittest.TestCase):
    """One-shot smoke: known real shapes must not crash any of the V3.17
    pipeline functions. Catches contract drift if any helper grows a new
    assumption about row shape that the production cache doesn't satisfy."""

    def test_nok_geographic_only_smoke(self):
        # NOK actual shape: only geographic_fy populated (regions nested),
        # product_fy = [] (FMP free tier). Must produce a clean overlay
        # without crashing — historically this was the path that exposed
        # the V3.17.0 fiscal_year bug.
        segments = {"product_fy": [], "geographic_fy": NESTED_REGIONS_FY}
        annual_growth = [{"fiveYRevenueGrowthPerShare": 0.02}]
        out = compute_business_mix_shift_overlay(segments, annual_growth, [])
        self.assertIn(out["tier"],
                      {"NO_DATA", "STABLE", "EMERGING", "ESTABLISHED"})

    def test_amd_product_only_smoke(self):
        segments = {"product_fy": NESTED_PRODUCTS_FY, "geographic_fy": []}
        annual_growth = [{"fiveYRevenueGrowthPerShare": 0.05}]
        out = compute_business_mix_shift_overlay(segments, annual_growth, [])
        self.assertIsNotNone(out)


class TestFetchSlimRoundTripContract(unittest.TestCase):
    """V3.17.2 (Codex Finding 3) — round-trip through fetch.py slim_* helpers.

    The earlier TestSegmentValues / TestIdentifyNewSegment fixtures were
    hand-crafted to mirror what we believed fetch.py would emit. But that
    makes them aligned with our assumption rather than with fetch.py's
    actual contract — a future refactor that renames `products` → `lines`
    in slim_segment_product would not break those tests because they never
    invoked the slim helper.

    This class closes that gap by feeding raw FMP-shaped rows through the
    real slim helpers and asserting that the analyzer can consume the
    output without losing the segment signal.

    Raw FMP shape (per fetch.py:153-171):
      product:    {date, fiscalYear (camel), period, data: {seg: revenue}}
      geographic: same shape with `data: {region: revenue}`
    slim helpers translate this to nested products/regions (snake_case
    fiscal_year). If that contract ever drifts, the assertion below will
    catch it.
    """

    def _raw_product_rows(self):
        """5 FY rows, AMD-like Data Center ramp 5000 → 30000 across 5 years."""
        return [
            {"date": "2026-03-28", "fiscalYear": 2026, "period": "FY",
             "data": {"Data Center": 30000, "Client and Gaming": 12000,
                      "Embedded": 5000, "Gaming": 3000}},
            {"date": "2025-03-28", "fiscalYear": 2025, "period": "FY",
             "data": {"Data Center": 18000, "Client and Gaming": 11000,
                      "Embedded": 6000, "Gaming": 3500}},
            {"date": "2024-03-28", "fiscalYear": 2024, "period": "FY",
             "data": {"Data Center": 12000, "Client and Gaming": 10500,
                      "Embedded": 7000, "Gaming": 4000}},
            {"date": "2023-03-28", "fiscalYear": 2023, "period": "FY",
             "data": {"Data Center": 8000, "Client and Gaming": 10000,
                      "Embedded": 7500, "Gaming": 4500}},
            {"date": "2022-03-28", "fiscalYear": 2022, "period": "FY",
             "data": {"Data Center": 5000, "Client and Gaming": 9500,
                      "Embedded": 6500, "Gaming": 4800}},
        ]

    def _raw_geographic_rows(self):
        """NOK-like region split."""
        return [
            {"date": "2025-12-31", "fiscalYear": 2025, "period": "FY",
             "data": {"Americas": 6985, "Asia Pacific": 4639,
                      "EMEA Region": 8265, "Europe": 6165}},
            {"date": "2024-12-31", "fiscalYear": 2024, "period": "FY",
             "data": {"Americas": 6500, "Asia Pacific": 4200,
                      "EMEA Region": 7800}},
        ]

    def test_slim_segment_product_shape_contract(self):
        """slim_segment_product MUST emit {date, fiscal_year (snake), period,
        products: {...}} — analyze.py / _segment_values rely on this."""
        out = slim_segment_product(self._raw_product_rows())
        self.assertEqual(len(out), 5)
        first = out[0]
        # Required keys
        self.assertIn("date", first)
        self.assertIn("fiscal_year", first, "snake_case fiscal_year required")
        self.assertIn("period", first)
        self.assertIn("products", first, "nested `products` key required")
        # MUST be the nested dict, not flat-merged
        self.assertIsInstance(first["products"], dict)
        self.assertIn("Data Center", first["products"])
        # MUST NOT carry camelCase fiscalYear (would create double metadata)
        self.assertNotIn("fiscalYear", first)

    def test_slim_segment_geographic_shape_contract(self):
        out = slim_segment_geographic(self._raw_geographic_rows())
        self.assertEqual(len(out), 2)
        first = out[0]
        self.assertIn("regions", first, "nested `regions` key required")
        self.assertIsInstance(first["regions"], dict)
        self.assertIn("EMEA Region", first["regions"])
        self.assertIn("fiscal_year", first)
        self.assertNotIn("fiscalYear", first)

    def test_round_trip_analyzer_picks_correct_segment(self):
        """End-to-end: raw FMP rows → slim_segment_product → compute_business_mix_shift_overlay.

        Hard-fails if any link in this chain drifts in a way that lets a
        metadata key (fiscal_year) win selection or that downgrades a
        high-conviction segment back to STABLE.
        """
        slimmed_products = slim_segment_product(self._raw_product_rows())
        slimmed_geographic = slim_segment_geographic([])  # empty
        segments = {"product_fy": slimmed_products,
                    "geographic_fy": slimmed_geographic}
        annual_growth = [{"fiveYRevenueGrowthPerShare": 0.05}]
        out = compute_business_mix_shift_overlay(segments, annual_growth, [])
        # Strict: must reach EMERGING (FY fallback ceiling for share=60% high-growth)
        self.assertEqual(out["tier"], "EMERGING",
                         "Round-trip through fetch.py slim must preserve EMERGING tier")
        # Must pick Data Center (real segment), not fiscal_year (metadata)
        self.assertEqual(out["new_segment"]["name"], "Data Center")

    def test_round_trip_balance_with_ap_yields_direct_dpo(self):
        """Round-trip raw balance row through slim_balance → compute_wc_diagnostics.

        Ensures slim_balance still emits accountsPayable + otherCurrentLiabilities
        (V3.17 addition). If a future refactor drops these from `keep`, the
        DPO fallback regresses to `unavailable` silently — this test catches it.
        """
        raw_balance = [{
            "date": "2026-03-31", "period": "Q1",
            "totalAssets": 10000, "totalLiabilities": 4000, "totalEquity": 6000,
            "totalCurrentAssets": 3000, "totalCurrentLiabilities": 1500,
            "cashAndCashEquivalents": 500, "shortTermInvestments": 300,
            "totalDebt": 1000, "longTermDebt": 800, "shortTermDebt": 200,
            "netReceivables": 600, "inventory": 400, "retainedEarnings": 5000,
            "accountsPayable": 300, "otherCurrentLiabilities": 800,
        }] * 4
        raw_income = [{
            "date": "2026-03-31", "fiscalYear": 2026, "period": "Q1",
            "revenue": 2000, "costOfRevenue": 1200, "grossProfit": 800,
            "operatingIncome": 200, "netIncome": 150, "eps": 0.5, "epsDiluted": 0.5,
            "researchAndDevelopmentExpenses": 100,
            "sellingGeneralAndAdministrativeExpenses": 200,
            "ebitda": 250, "ebit": 220, "weightedAverageShsOutDil": 1000,
        }] * 4
        slim_b = slim_balance(raw_balance)
        slim_i = slim_income(raw_income)
        # V3.17 contract: slim_balance must include AP + OCL
        self.assertIn("accountsPayable", slim_b[0],
                      "slim_balance must keep accountsPayable for DPO direct path")
        self.assertIn("otherCurrentLiabilities", slim_b[0],
                      "slim_balance must keep otherCurrentLiabilities for DPO fallback")
        # V3.17 contract: slim_income must include costOfRevenue (DPO denominator)
        self.assertIn("costOfRevenue", slim_i[0],
                      "slim_income must keep costOfRevenue for DPO computation")

        out = compute_wc_diagnostics(slim_i, slim_b)
        self.assertEqual(out["dpo_method"], "direct",
                         "round-trip with AP present must yield direct DPO method")


if __name__ == "__main__":
    unittest.main(verbosity=2)

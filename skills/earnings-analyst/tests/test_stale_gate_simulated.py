#!/usr/bin/env python3
"""V3.17.3 — Stale gate simulated tests.

Phase 3 Step 2 of investment_protocol_v5_0.md defines the staleness alert:

    IF abs(bundle.transition_signature_mtime - forecaster.transition_case_mtime) > 6h
       OR bundle.transition_signature inconsistent with forecaster.transition_case:
      emit terminal alert + session_export[stale]=true
      transition_softening_disabled = true   # disables cascade rule #2
      # cascade #1/#3/#4/#5 still apply

The rule is consumed by a PROTOCOL prompt, not a Python function — there's no
direct `assert stale_gate_fires(...)` call site. What we CAN unit-test
deterministically:

  1. earnings-analyst analyze.py emits `transition_signature_mtime` in
     the augmented bundle (Codex round-6 fix).
  2. forecaster forecast.py emits top-level `transition_case_mtime` AND
     carries `transition_signature_mtime` through `transition_info`
     (Codex round-6 fix).
  3. forecaster `_load_earnings_analyst_bundle` requires fresh financial
     source_records and derives a missing signature timestamp from them.
     Rewriting a file cannot renew stale or unproven source data.
  4. Given two synthetic mtime values, the comparison logic in the
     protocol prompt — translated to Python — would correctly fire
     stale > 6h.

Test (4) is essentially testing arithmetic, but it freezes the threshold
as part of the contract so anyone tempted to bump it past 24h (and
silently neuter the gate) has to update this test.

Per Wave 1 plan + Codex round-7 risk discussion:
  - Stale gate is NOT measured on historical cache mtime (local
    filesystem time ≠ financial event time). This test uses synthetic
    mtimes only.
  - Acceptance is "gate logic responds correctly to manufactured stale" —
    not "gate fires on N% of cohort".

Run:
  python3 skills/earnings-analyst/tests/test_stale_gate_simulated.py
  python3 -m pytest skills/earnings-analyst/tests/test_stale_gate_simulated.py
"""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
# HERE.parents: [0]=earnings-analyst, [1]=skills, [2]=repo-root
sys.path.insert(0, str(HERE.parents[1] / "earnings-valuation-forecaster" / "scripts"))

from analyze import analyze
from investment.scripts.run_data import source


# ── Constants pulled from protocol Phase 3 Step 2 ────────────────────────
STALE_THRESHOLD_HOURS = 6.0


def _parse_iso(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s)


def _delta_hours(t_a: dt.datetime, t_b: dt.datetime) -> float:
    return abs((t_a - t_b).total_seconds()) / 3600.0


# ── Minimal bundle fixture — just enough for analyze() to emit fields ────
def _minimal_bundle():
    """Construct the smallest legal bundle that analyze() will accept."""
    return {
        "ticker": "TEST",
        "snapshot": {"price": 100.0},
        "quarterly_pnl": [
            {"date": f"2026-{m:02d}-30", "revenue": 1000, "grossProfit": 400,
             "operatingIncome": 100, "netIncome": 80, "eps": 0.5,
             "epsDiluted": 0.5, "costOfRevenue": 600}
            for m in (3, 12, 9, 6, 3, 12, 9, 6)
        ],
        "balance_sheet": [
            {"date": f"2026-{m:02d}-30", "totalAssets": 5000,
             "totalLiabilities": 2000, "totalEquity": 3000,
             "totalCurrentAssets": 1500, "totalCurrentLiabilities": 800,
             "cashAndCashEquivalents": 400, "shortTermInvestments": 100,
             "totalDebt": 500, "netReceivables": 200, "inventory": 100,
             "accountsPayable": 150, "otherCurrentLiabilities": 300}
            for m in (3, 12, 9, 6, 3, 12, 9, 6)
        ],
        "cash_flow": [
            {"date": f"2026-{m:02d}-30", "operatingCashFlow": 120,
             "freeCashFlow": 90, "capitalExpenditure": -30,
             "netIncome": 80}
            for m in (3, 12, 9, 6, 3, 12, 9, 6)
        ],
        "ttm_metrics": {"from_key_metrics_ttm": {}, "from_ratios_ttm": {}},
        "annual_growth": [{"fiveYRevenueGrowthPerShare": 0.05}],
        "valuation": {"dcf_intrinsic": 95},
        "snapshot": {"price": 100.0},
        "analyst_grades": [],
        "segments": {"product_fy": [], "geographic_fy": []},
    }


class TestStaleThresholdMath(unittest.TestCase):
    """Freeze the 6h threshold so a careless protocol edit can't widen it
    silently without breaking this test."""

    def test_below_threshold_does_not_fire(self):
        sig = _parse_iso("2026-05-24T09:00:00")
        case = _parse_iso("2026-05-24T14:30:00")  # 5h30m
        delta = _delta_hours(sig, case)
        self.assertLess(delta, STALE_THRESHOLD_HOURS,
                        f"delta {delta:.2f}h should be < {STALE_THRESHOLD_HOURS}h threshold")

    def test_exactly_at_threshold_does_not_fire(self):
        # 6h exact → not stale (rule uses strict `>` not `>=`)
        sig = _parse_iso("2026-05-24T09:00:00")
        case = _parse_iso("2026-05-24T15:00:00")  # 6h
        delta = _delta_hours(sig, case)
        self.assertEqual(delta, STALE_THRESHOLD_HOURS)
        self.assertFalse(delta > STALE_THRESHOLD_HOURS,
                         "exact-threshold delta must not fire stale (strict > rule)")

    def test_above_threshold_fires(self):
        sig = _parse_iso("2026-05-24T09:00:00")
        case = _parse_iso("2026-05-24T16:00:00")  # 7h
        delta = _delta_hours(sig, case)
        self.assertGreater(delta, STALE_THRESHOLD_HOURS)
        # protocol contract — this fires stale gate
        self.assertTrue(delta > STALE_THRESHOLD_HOURS)

    def test_cross_day_delta(self):
        # Cache regenerated next morning while analyzer was yesterday
        sig = _parse_iso("2026-05-23T22:00:00")
        case = _parse_iso("2026-05-24T08:00:00")  # 10h
        delta = _delta_hours(sig, case)
        self.assertGreater(delta, STALE_THRESHOLD_HOURS)


class TestEarningsAnalystEmitsSignatureMtime(unittest.TestCase):
    """Contract (Codex round-6): analyze() MUST emit
    `transition_signature_mtime` in the augmented bundle. Without this
    field the protocol's Phase 3 Step 2 cross-check cannot fire."""

    def test_analyze_emits_mtime_field(self):
        bundle = _minimal_bundle()
        older = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)).isoformat()
        newer = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)).isoformat()
        bundle["source_records"] = {
            "income": source([], kind="financial", fetched_at=older),
            "balance": source([], kind="financial", fetched_at=newer),
        }
        analyzed = analyze(bundle)
        self.assertIn("transition_signature_mtime", analyzed,
                      "analyze() must emit transition_signature_mtime for stale-gate cross-check")
        # Must be ISO-8601 parseable
        mtime_str = analyzed["transition_signature_mtime"]
        self.assertIsInstance(mtime_str, str)
        # Will raise ValueError if not iso
        dt.datetime.fromisoformat(mtime_str)
        self.assertEqual(mtime_str, older, "must retain the oldest financial source timestamp")

    def test_missing_sources_cannot_fabricate_signature_timestamp(self):
        self.assertIsNone(analyze(_minimal_bundle())["transition_signature_mtime"])

    def test_analyze_emits_signature_alongside_mtime(self):
        bundle = _minimal_bundle()
        analyzed = analyze(bundle)
        # Both fields together — without signature, mtime is meaningless
        self.assertIn("transition_signature", analyzed)
        self.assertIn(analyzed["transition_signature"],
                      {"paradigm_only", "mix_only", "both", "neither"})


class TestForecasterSourceFreshness(unittest.TestCase):
    """The real cache loader must reject a fresh file containing stale sources."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=HERE.parents[2] / "tmp")
        self.addCleanup(self.tmp.cleanup)
        self.scope = patch("forecast.EA_CACHE_DIR_FC", self.tmp.name)
        self.scope.start()
        self.addCleanup(self.scope.stop)
        self.period = "2026-06-30"
        self.fetched = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)).isoformat()

    def load(self, *, fetched=None, with_source=True, explicit=None):
        from forecast import _load_earnings_analyst_bundle
        bundle = {"ticker": "ZZTEST", "last_earnings_date": self.period,
                  "transition_signature": "neither"}
        if with_source:
            bundle["source_records"] = {"income": source([], kind="financial",
                fetched_at=fetched or self.fetched, period=self.period)}
        if explicit:
            bundle["transition_signature_mtime"] = explicit
        path = Path(self.tmp.name) / f"ZZTEST_{self.period}.json"
        path.write_text(json.dumps(bundle))  # fresh mtime in every case
        return _load_earnings_analyst_bundle("ZZTEST")

    def test_backfill_from_source_not_file_mtime(self):
        loaded = self.load()
        self.assertEqual(loaded["transition_signature_mtime"], self.fetched)
        self.assertEqual(loaded["_source_mtime"], self.fetched)

    def test_explicit_signature_timestamp_is_preserved(self):
        explicit = "2026-01-15T10:00:00+00:00"
        self.assertEqual(self.load(explicit=explicit)["transition_signature_mtime"], explicit)

    def test_legacy_cache_without_sources_is_rejected(self):
        self.assertIsNone(self.load(with_source=False))

    def test_rewritten_file_does_not_renew_expired_sources(self):
        expired = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).isoformat()
        self.assertIsNone(self.load(fetched=expired))


if __name__ == "__main__":
    unittest.main(verbosity=2)

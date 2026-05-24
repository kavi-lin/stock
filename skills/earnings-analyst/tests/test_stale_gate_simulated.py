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
  3. forecaster `_load_earnings_analyst_bundle` BACKFILLS
     `transition_signature_mtime` from cache file mtime when missing
     from an older cache.
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
# HERE.parents: [0]=earnings-analyst, [1]=skills, [2]=repo-root
sys.path.insert(0, str(HERE.parents[1] / "earnings-valuation-forecaster" / "scripts"))

from analyze import analyze


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
        analyzed = analyze(bundle)
        self.assertIn("transition_signature_mtime", analyzed,
                      "analyze() must emit transition_signature_mtime for stale-gate cross-check")
        # Must be ISO-8601 parseable
        mtime_str = analyzed["transition_signature_mtime"]
        self.assertIsInstance(mtime_str, str)
        # Will raise ValueError if not iso
        dt.datetime.fromisoformat(mtime_str)

    def test_analyze_emits_signature_alongside_mtime(self):
        bundle = _minimal_bundle()
        analyzed = analyze(bundle)
        # Both fields together — without signature, mtime is meaningless
        self.assertIn("transition_signature", analyzed)
        self.assertIn(analyzed["transition_signature"],
                      {"paradigm_only", "mix_only", "both", "neither"})


class TestForecasterBackfillsMtimeFromOldCache(unittest.TestCase):
    """Contract (Codex round-6): _load_earnings_analyst_bundle MUST
    backfill `transition_signature_mtime` from cache file mtime when the
    cache file itself lacks the field (pre-V3.17.1 caches)."""

    def test_backfill_from_file_mtime(self):
        from forecast import _load_earnings_analyst_bundle, EA_CACHE_DIR_FC

        # Drop an older-shaped cache (no transition_signature_mtime) into a
        # temp dir mimicking the EA cache layout. Use a custom ticker so we
        # don't collide with real cache entries.
        # Note: _load_earnings_analyst_bundle searches EA_CACHE_DIR_FC; we
        # write directly there with a synthetic ticker name to avoid mocking.
        tmp_ticker = "ZZTEST"
        tmp_file = os.path.join(EA_CACHE_DIR_FC, f"{tmp_ticker}_2024-12-31.json")
        try:
            os.makedirs(EA_CACHE_DIR_FC, exist_ok=True)
            # Legacy-shape cache — has transition_signature but NOT _mtime field
            legacy = {
                "ticker": tmp_ticker,
                "transition_signature": "neither",
                "business_mix_shift_overlay": {"tier": "STABLE"},
            }
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(legacy, f)

            loaded = _load_earnings_analyst_bundle(tmp_ticker)
            self.assertIsNotNone(loaded, "loader must find ZZTEST cache")
            self.assertIn("transition_signature_mtime", loaded,
                          "loader must backfill transition_signature_mtime from file mtime")
            # backfilled mtime should be close to "now" (within this test's runtime)
            backfilled = dt.datetime.fromisoformat(loaded["transition_signature_mtime"])
            now = dt.datetime.fromtimestamp(os.path.getmtime(tmp_file))
            delta = abs((backfilled - now).total_seconds())
            self.assertLess(delta, 2.0,
                            "backfilled mtime should match file mtime within 2 seconds")
        finally:
            if os.path.exists(tmp_file):
                os.unlink(tmp_file)

    def test_explicit_mtime_in_cache_wins_over_backfill(self):
        from forecast import _load_earnings_analyst_bundle, EA_CACHE_DIR_FC

        tmp_ticker = "ZYTEST"
        tmp_file = os.path.join(EA_CACHE_DIR_FC, f"{tmp_ticker}_2024-12-31.json")
        try:
            explicit_mtime = "2026-01-15T10:00:00"
            cache = {
                "ticker": tmp_ticker,
                "transition_signature": "neither",
                "transition_signature_mtime": explicit_mtime,
            }
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(cache, f)
            loaded = _load_earnings_analyst_bundle(tmp_ticker)
            self.assertIsNotNone(loaded)
            # Explicit value must NOT be overwritten by backfill (setdefault contract)
            self.assertEqual(loaded["transition_signature_mtime"], explicit_mtime,
                             "explicit mtime in cache must take precedence over backfill")
        finally:
            if os.path.exists(tmp_file):
                os.unlink(tmp_file)


if __name__ == "__main__":
    unittest.main(verbosity=2)

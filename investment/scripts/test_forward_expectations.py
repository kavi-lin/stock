#!/usr/bin/env python3
"""Golden-fixture regression for forward_expectations.py (Phase 1 shadow).

Deterministic — uses fixed in-memory inputs and --no-fetch semantics (no FMP calls),
so it runs offline and gives stable numbers. Run after any engine edit:

  python3 investment/scripts/test_forward_expectations.py     # rc=0 = pass
"""
import os
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import forward_expectations as fe  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want, tol=None):
    global PASS, FAIL
    ok = (abs(got - want) <= tol) if (tol is not None and got is not None) else (got == want)
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print(f"  ✗ {label}: got {got!r}, want {want!r}" + (f" (±{tol})" if tol else ""))


# ── Fixture A: hypergrowth-shaped — consensus 41% vs market-implied (clamped 60%) ──
EC_A = {
    "as_of_date": "2026-05-07",
    "annual_estimates": [
        {"date": "2030-03-31", "revenue_avg": 2000, "eps_avg": 4.0,
         "eps_low": 3.5, "eps_high": 4.5, "num_analysts_eps": 8, "num_analysts_revenue": 11},
        {"date": "2028-03-31", "revenue_avg": 1000, "eps_avg": 2.0,
         "eps_low": 1.8, "eps_high": 2.2, "num_analysts_eps": 10, "num_analysts_revenue": 12},
    ],
    "analyst_grades": [
        {"date": "2026-01-01", "analystRatingsStrongBuy": 5, "analystRatingsBuy": 10,
         "analystRatingsHold": 5, "analystRatingsSell": 2, "analystRatingsStrongSell": 1},
        {"date": "2026-05-01", "analystRatingsStrongBuy": 8, "analystRatingsBuy": 12,
         "analystRatingsHold": 4, "analystRatingsSell": 1, "analystRatingsStrongSell": 0},
    ],
    "derived": {"yoy_growth": {"revenue_yoy": 0.30, "growth_acceleration": "decelerating"}},
}
INP_A = {"current_price": 100.0, "reverse_dcf": {"fcf_base_per_share": 0.10},
         "fred": {"treasury_10y": 0.045}}   # low FCF base → implied CAGR hits 0.60 clamp

print("Fixture A (hypergrowth gap):")
cons = fe.consensus_lane(EC_A)
check("consensus.available", cons["available"], True)
check("consensus.revenue_cagr", cons["revenue_cagr"], 0.4142, tol=0.001)   # 2000/1000 ^(1/2)-1
check("consensus.eps_cagr", cons["eps_cagr"], 0.4142, tol=0.001)           # 4/2 ^(1/2)-1
check("consensus.eps_spread_pct", cons["eps_spread_pct"], 25.0, tol=0.1)   # (4.5-3.5)/4.0
check("consensus.num_analysts_eps", cons["num_analysts_eps"], 8)
check("consensus.analyst_rating_direction", cons["analyst_rating_direction"], "UP")

market = fe.market_implied_lane("TESTA", INP_A, no_fetch=True)
check("market.available", market["available"], True)
check("market.required_fcf_cagr", market["required_fcf_cagr"], 0.6, tol=1e-9)  # clamp ceiling
check("market.out_of_range", market["out_of_range"], True)

base = fe.base_rate_lane("TESTA", EC_A, no_fetch=True)
check("base.available(no_fetch)", base["available"], False)
check("base.self_revenue_yoy", base["self_revenue_yoy"], 0.30, tol=1e-9)

matrix = fe.assemble_expectations_matrix(cons, market, base)
check("matrix.cross_metric_verdict", matrix["verdict"], "comparison_unavailable")
check("matrix.cross_metric_has_no_gap", matrix["same_metric_comparisons"], [])
check("matrix.fcf_market_implied", matrix["metrics"]["fcf_cagr"]["market_implied"], 0.6)
check("matrix.eps_consensus", matrix["metrics"]["eps_cagr"]["consensus"], 0.4142, tol=0.001)

# EXP-1.2: consensus is an INDEPENDENT lane — a divergent base-rate median must NOT
# overwrite the consensus revenue CAGR; it may only sit beside it as a comparator.
low_base = {"available": True, "peer_rev_cagr_median": 0.05}
m12 = fe.assemble_expectations_matrix(cons, market, low_base)
check("EXP-1.2 consensus preserved (not base-rate median)", m12["metrics"]["revenue_cagr"]["consensus"], cons["revenue_cagr"])
check("EXP-1.2 base-rate sits in its own column", m12["metrics"]["revenue_cagr"]["base_rate"], 0.05)
check("EXP-1.2 divergence emitted as descriptive comparison, not override",
      m12["same_metric_comparisons"][0]["verdict"], "consensus_above_base_rate")

# ── Fixture B: consensus only, no reverse DCF → insufficient_forward_data ──
EC_B = {
    "as_of_date": "2026-01-01",
    "annual_estimates": [
        {"date": "2029-12-31", "revenue_avg": 1500, "eps_avg": 6.0,
         "eps_low": 5.8, "eps_high": 6.2, "num_analysts_eps": 20, "num_analysts_revenue": 22},
        {"date": "2027-12-31", "revenue_avg": 1300, "eps_avg": 5.0,
         "eps_low": 4.9, "eps_high": 5.1, "num_analysts_eps": 25, "num_analysts_revenue": 26},
    ],
}
INP_B = {"current_price": 120.0}   # no reverse_dcf → market lane unavailable

print("Fixture B (consensus only / mature):")
cons_b = fe.consensus_lane(EC_B)
check("consensus_b.available", cons_b["available"], True)
check("consensus_b.analyst_rating_direction(no grades)", cons_b["analyst_rating_direction"], None)
market_b = fe.market_implied_lane("TESTB", INP_B, no_fetch=True)
check("market_b.available", market_b["available"], False)
matrix_b = fe.assemble_expectations_matrix(cons_b, market_b, fe.base_rate_lane("TESTB", EC_B, no_fetch=True))
check("matrix_b.verdict", matrix_b["verdict"], "comparison_unavailable")

print("Fixture B1 (unqualified raw peers stay advisory-only):")
raw_only = fe._select_base_rate_distribution(
    {"available": False, "member_count": 1}, [0.05, 0.10, 0.20], ["A", "B", "C"],
)
check("raw_only unavailable", raw_only["available"], False)
check("raw_only no numeric median", raw_only.get("peer_rev_cagr_median"), None)
check("raw_only distribution disclosed", raw_only["raw_peer_distribution"]["median"], 0.10)
check("raw_only basis", raw_only["basis"], "raw_peers_advisory_only")
curated = fe._curated_business_cohort(
    {"name": "memory_storage", "comparison_scope": "range_only", "limitations": ["cycle"]},
    [{"ticker": "SNDK", "revenue_cagr": 0.10}, {"ticker": "WDC", "revenue_cagr": 0.20},
     {"ticker": "STX", "revenue_cagr": 0.30}],
)
check("range-only cohort not auto-promoted to growth", curated["available"], False)
check("range-only scope mismatch explicit", curated["status"], "scope_not_approved_for_growth")
check("curated business median", curated["distribution"]["median"], 0.20)
check("curated membership fixed before values", curated["rationale"]["anti_cherry_pick"],
      "Candidate membership is loaded before any revenue CAGR is fetched.")
curated_disclosure = fe._select_base_rate_distribution(
    curated, [0.10, 0.20, 0.30], ["SNDK", "WDC", "STX"],
)
check("range-only selection unavailable", curated_disclosure["available"], False)
check("range-only selection basis", curated_disclosure["basis"], "curated_cohort_scope_mismatch")
curated_growth = fe._curated_business_cohort(
    {"name": "memory_storage", "comparison_scope": "growth_base_rate"},
    [{"ticker": "SNDK", "revenue_cagr": 0.10}, {"ticker": "WDC", "revenue_cagr": 0.20},
     {"ticker": "STX", "revenue_cagr": 0.30}],
)
check("growth-approved cohort can become numeric", curated_growth["available"], True)

# A promoted cohort must say how it was actually selected. The two builders earn trust
# differently, so a note crediting the wrong one is a provenance error, not a wording nit.
promoted_note = fe._select_base_rate_distribution(
    curated_growth, [0.10, 0.20, 0.30], ["SNDK", "WDC", "STX"],
)["note"]
check("promoted curated cohort is credited as human-approved",
      "human-approved cohort" in promoted_note, True)
check("promoted curated cohort names its approved scope",
      "growth_base_rate" in promoted_note, True)
check("promoted curated cohort does not claim tier matching",
      "±1 tier" in promoted_note, False)
algo_cohort = {
    "available": True, "member_count": 4,
    "distribution": {"median": 0.13, "p25": 0.10, "p75": 0.20},
    "members": [{"ticker": t} for t in ("AAA", "BBB", "CCC", "DDD")],
    "rationale": {"criteria": ["sector(exact)", "growth_stage(+/-1)", "margin_tier(+/-1)"]},
}
algo_note = fe._select_base_rate_distribution(algo_cohort, [0.1] * 4, ["AAA"])["note"]
check("algorithmic cohort still describes its own criteria",
      "sector(exact)" in algo_note and "演算法 cohort" in algo_note, True)
check("algorithmic cohort not mislabelled human-approved",
      "human-approved" in algo_note, False)
check("cohort with no recorded rationale says so",
      "未記錄選取理由" in fe._cohort_selection_note({"member_count": 3}), True)

# Point-in-time guard: already-reported FY rows must not inflate the forward CAGR.
print("Fixture B2 (exclude elapsed estimate rows):")
ec_b2 = {
    "as_of_date": "2026-06-30",
    "annual_estimates": [
        {"date": "2025-12-31", "revenue_avg": 100, "eps_avg": 1},
        {"date": "2027-12-31", "revenue_avg": 200, "eps_avg": 2},
        {"date": "2028-12-31", "revenue_avg": 220, "eps_avg": 2.2},
    ],
}
cons_b2 = fe.consensus_lane(ec_b2)
check("consensus_b2 excludes one elapsed row", cons_b2["excluded_nonforward_rows"], 1)
check("consensus_b2 window starts in future", cons_b2["window_from"], "2027-12-31")
check("consensus_b2 revenue uses future curve only", cons_b2["revenue_cagr"], 0.10, tol=0.001)

# ── Fixture C: empty estimates → consensus lane degrades cleanly ──
print("Fixture C (no estimates):")
cons_c = fe.consensus_lane({"annual_estimates": []})
check("consensus_c.available", cons_c["available"], False)
check("consensus_c.eps_cagr", cons_c["eps_cagr"], None)

# ── Fixture D: only same-metric values can create a numeric comparison ───────
print("Fixture D (same-metric comparison):")
base_d = {"peer_rev_cagr_median": 0.10}
matrix_d = fe.assemble_expectations_matrix(cons, market, base_d)
check("matrix_d.verdict", matrix_d["verdict"], "same_metric_gap_available")
check("matrix_d.comparison.metric", matrix_d["same_metric_comparisons"][0]["metric"], "revenue_cagr")
check("matrix_d.comparison.delta", matrix_d["same_metric_comparisons"][0]["delta"], 0.3142, tol=0.001)
check("matrix_d.no_market_minus_consensus", "market_minus_consensus" in matrix_d, False)

independent_d = {"available": True, "revenue_cagr": 0.25}
matrix_ind = fe.assemble_expectations_matrix(cons, market, base_d, independent_d)
check("matrix_ind.value", matrix_ind["metrics"]["revenue_cagr"]["independent"], 0.25)
check("matrix_ind.same_metric_count", len(matrix_ind["same_metric_comparisons"]), 3)
check("matrix_ind.consensus_delta", matrix_ind["same_metric_comparisons"][1]["delta"], -0.1642, tol=0.001)

# ── Fixture E: evidence gate rejects unknown and missing-source values ────────
print("Fixture E (evidence contract):")
now = "2026-06-15T00:00:00+00:00"
good = fe.evidence_record("revenue_cagr", 0.2, "ratio", "consensus", "fmp", "annual_estimates",
                          "2026-05-01", now)
unknown = fe.evidence_record("royalty_rate", None, "ratio", "unknown", "company_filing", "ARM 10-K",
                             "2026-05-01", now)
missing_source = fe.evidence_record("margin", 0.4, "ratio", "assumption", "committee", None,
                                    "2026-05-01", now)
evidence = fe.validate_evidence([good, unknown, missing_source])
check("evidence.status", evidence["status"], "degraded")
check("evidence.accepted_count", evidence["accepted_count"], 1)
check("evidence.rejected_count", evidence["rejected_count"], 2)

# ── Fixture F: snapshots are immutable and run-id addressed ──────────────────
print("Fixture F (immutable ledger):")
old_dir = fe.SNAPSHOT_DIR
with tempfile.TemporaryDirectory() as tmp:
    fe.SNAPSHOT_DIR = tmp
    payload = {"ticker": "TEST", "run_id": "20260615T000000000000Z", "generated_at": now}
    first = fe.write_snapshot(payload)
    second = fe.write_snapshot(payload)
    check("snapshot.first_written", bool(first and os.path.exists(first)), True)
    check("snapshot.second_rejected", second, None)
fe.SNAPSHOT_DIR = old_dir

print("Fixture G (document acquisition stays opt-in through CLI boundary):")
with patch("forward_expectations_document_acquisition.acquire_documents") as mocked:
    # Direct engine helper tests cover acquisition behavior. This assertion keeps
    # the core import path available without turning ordinary lane tests into CLI
    # subprocess tests.
    check("doc_acquisition_importable", callable(mocked), True)

print("Fixture H (financial bridge import stays isolated from lane math):")
from forward_expectations_financial_bridge import build_financial_bridge  # noqa: E402
bridge_h = build_financial_bridge(EC_A)
check("financial_bridge_importable", isinstance(bridge_h, dict), True)
check("financial_bridge_shadow_policy", "live decisions" in bridge_h["policy"], True)

print("Fixture I (expectations gap import stays shadow-only):")
from forward_expectations_gap import build_expectations_gap  # noqa: E402
gap_i = build_expectations_gap(cons, market, independent_d, base_d, bridge_h)
check("expectations_gap_importable", isinstance(gap_i, dict), True)
check("expectations_gap_shadow_policy", "fair value" in gap_i["policy"], True)

print("Fixture J (scenario policy import blocks unsupported numeric scenarios):")
from forward_expectations_scenario_policy import build_scenario_policy  # noqa: E402
scenario_j = build_scenario_policy(cons, {"available": False, "reason": "missing"}, {}, bridge_h, {})
check("scenario_policy_importable", isinstance(scenario_j, dict), True)
check("scenario_policy_no_fixed_pct", "fixed_pct_eps_pe_haircut" in scenario_j["forbidden_methods"], True)

print("Fixture K (scenario builder import stays shadow-only):")
from forward_expectations_scenario_builder import build_operating_driver_scenarios  # noqa: E402
builder_k = build_operating_driver_scenarios(scenario_j, {"available": False}, {}, bridge_h, {})
check("scenario_builder_importable", isinstance(builder_k, dict), True)
check("scenario_builder_shadow_only", builder_k["valuation_output"], False)

print("Fixture L (future price range import stays shadow-only):")
from forward_expectations_price_range import build_future_price_range  # noqa: E402
price_l = build_future_price_range("TEST", 100, {
    "historical_conversion": {"diluted_share_count": 100},
    "rows": [{"date": "2028-12-31", "eps_consensus": {"point": 5, "low": 4, "high": 6}}],
}, {}, {"pe_range": {"p25": 15, "p50": 20, "p75": 25}})
check("future_price_importable", isinstance(price_l, dict), True)
check("future_price_available", price_l["available"], True)
check("future_price_shadow_only", price_l["changes_live_decision"], False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

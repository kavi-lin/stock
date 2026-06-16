#!/usr/bin/env python3
"""Golden fixtures for Forward Expectations scenario policy."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_scenario_policy as sp  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}")


CONSENSUS = {"revenue_cagr": 0.30, "eps_cagr": 0.40}
BRIDGE = {"available": True, "rows": [{"date": "2028-12-31"}]}

print("Fixture A (missing drivers -> range/overlay only, no numeric scenario):")
missing = sp.build_scenario_policy(
    CONSENSUS,
    {"available": False, "reason": "insufficient_evidence", "missing_numeric_drivers": ["units", "rate"]},
    {"selected_adapter": {"transmission_graph": {"numeric_eligible_count": 0}}},
    BRIDGE,
    {},
)
check("missing.status", missing["status"], "range_or_overlay_only")
check("missing.driver_gate", missing["gates"]["driver_evidence"]["status"], "fail")
check("missing.conversion_gate", missing["gates"]["conversion_method"]["status"], "fail")
check("missing.numeric_allowed", any(m["mode"] == "driver_numeric_bear_base_bull" for m in missing["allowed_modes"]), False)

print("Fixture B (complete independent driver -> numeric scenario allowed):")
complete = sp.build_scenario_policy(
    CONSENSUS,
    {"available": True, "revenue_cagr": 0.24, "numeric_transmission_paths": 1},
    {"selected_adapter": {"transmission_graph": {"numeric_eligible_count": 1}}},
    BRIDGE,
    {},
)
check("complete.status", complete["status"], "numeric_scenario_allowed")
check("complete.driver_gate", complete["gates"]["driver_evidence"]["status"], "pass")
check("complete.conversion_gate", complete["gates"]["conversion_method"]["status"], "pass")

print("Fixture C (guidance overlay preserves range):")
guidance = sp.build_scenario_policy(
    CONSENSUS,
    {"available": False, "reason": "no_matched_adapter"},
    {},
    BRIDGE,
    {"promoted": [{"metric": "revenue", "value": {"low": 900, "high": 1100, "midpoint": 1000}}]},
)
check("guidance.status", guidance["status"], "range_or_overlay_only")
overlay = [m for m in guidance["allowed_modes"] if m["mode"] == "management_guidance_overlay"][0]
check("guidance.range_required", overlay["range_required"], True)

print("Fixture D (bridge unavailable but base metric exists -> qualitative only):")
qual = sp.build_scenario_policy(CONSENSUS, {"available": False}, {}, {"available": False, "status": "insufficient_inputs"}, {})
check("qual.status", qual["status"], "qualitative_only")
check("qual.bridge_gate", qual["gates"]["bridge"]["status"], "fail")

print("Fixture E (no base metric -> insufficient inputs):")
empty = sp.build_scenario_policy({}, {}, {}, {}, {})
check("empty.available", empty["available"], False)
check("empty.status", empty["status"], "insufficient_inputs")
check("empty.base_gate", empty["gates"]["base_metric"]["status"], "fail")

print("Fixture F (forbidden methods are explicit):")
check("forbidden.fixed_pct", "fixed_pct_eps_pe_haircut" in complete["forbidden_methods"], True)
check("policy.shadow", "shadow-only" in complete["policy"], True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

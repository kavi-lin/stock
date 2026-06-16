#!/usr/bin/env python3
"""Golden fixtures for Forward Expectations operating-driver scenario builder."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_scenario_builder as sb  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}")


POLICY_NUMERIC = {
    "status": "numeric_scenario_allowed",
    "allowed_modes": [{"mode": "driver_numeric_bear_base_bull"}],
    "gates": {
        "driver_evidence": {"status": "pass"},
        "conversion_method": {"status": "pass"},
    },
}
INDEPENDENT_NUMERIC = {
    "available": True,
    "revenue_cagr": 0.24,
    "driver_evidence_refs": {"revenue_cagr": ["ev-rev-cagr"]},
}
ADAPTER_NUMERIC = {
    "selected_adapter": {
        "adapter_id": "royalty_ip",
        "transmission_graph": {"numeric_eligible_count": 1, "paths": []},
    }
}

print("Fixture A (numeric scenario allowed -> driver cases):")
numeric = sb.build_operating_driver_scenarios(POLICY_NUMERIC, INDEPENDENT_NUMERIC, ADAPTER_NUMERIC, {}, {})
check("numeric.available", numeric["available"], True)
check("numeric.mode", numeric["mode"], "driver_numeric_bear_base_bull")
check("numeric.case_count", len(numeric["cases"]), 3)
check("numeric.bear_cagr", numeric["cases"][0]["operating_drivers"]["revenue_cagr"], 0.19)
check("numeric.base_cagr", numeric["cases"][1]["operating_drivers"]["revenue_cagr"], 0.24)
check("numeric.bull_cagr", numeric["cases"][2]["operating_drivers"]["revenue_cagr"], 0.29)
check("numeric.no_valuation_output", numeric["valuation_output"], False)
check("numeric.no_live_decision", numeric["changes_live_decision"], False)

print("Fixture A2 (Royalty/IP driver-level scenario cases):")
driver_model_adapter = {
    "selected_adapter": {
        "adapter_id": "royalty_ip",
        "driver_model": {
            "available": True,
            "business_model": "royalty_ip",
            "case_driver_keys": [
                "royalty_bearing_units",
                "royalty_rate_or_value_per_unit",
                "license_pipeline_conversion",
                "data_center_segment_exposure",
                "revenue_cagr",
            ],
            "drivers": {
                "royalty_bearing_units": {"value": 100, "evidence_refs": ["units"]},
                "royalty_rate_or_value_per_unit": {"value": 0.025, "evidence_refs": ["rate"]},
                "license_pipeline_conversion": {"value": 0.40, "evidence_refs": ["license"]},
                "data_center_segment_exposure": {"value": 0.18, "evidence_refs": ["dc"]},
                "revenue_cagr": {"value": 0.24, "evidence_refs": ["cagr"]},
            },
        },
    }
}
driver_level = sb.build_operating_driver_scenarios(POLICY_NUMERIC, INDEPENDENT_NUMERIC, driver_model_adapter, {}, {})
check("driver_level.mode", driver_level["mode"], "driver_numeric_bear_base_bull")
check("driver_level.bear.units", driver_level["cases"][0]["operating_drivers"]["royalty_bearing_units"], 90.0)
check("driver_level.base.rate", driver_level["cases"][1]["operating_drivers"]["royalty_rate_or_value_per_unit"], 0.025)
check("driver_level.bull.license", driver_level["cases"][2]["operating_drivers"]["license_pipeline_conversion"], 0.44)
check("driver_level.bull.dc", driver_level["cases"][2]["operating_drivers"]["data_center_segment_exposure"], 0.198)
check("driver_level.method", driver_level["cases"][0]["driver_changes"][0]["method"], "driver_level_bounded_sensitivity")

print("Fixture B (policy numeric but independent base driver missing):")
missing_base = sb.build_operating_driver_scenarios(POLICY_NUMERIC, {"available": True}, ADAPTER_NUMERIC, {}, {})
check("missing.status", missing_base["status"], "numeric_inputs_incomplete")
check("missing.mode", missing_base["mode"], "qualitative_driver_watchlist")

print("Fixture C (guidance overlay only preserves range):")
policy_overlay = {
    "status": "range_or_overlay_only",
    "allowed_modes": [{"mode": "management_guidance_overlay", "range_required": True}],
    "gates": {"driver_evidence": {"status": "fail"}, "conversion_method": {"status": "fail"}},
}
guidance = {
    "promoted": [{
        "metric": "revenue",
        "value": {"low": 900, "high": 1100, "midpoint": 1000},
        "unit": "USDm",
        "source_ref": "FY outlook",
    }]
}
overlay = sb.build_operating_driver_scenarios(policy_overlay, {}, {}, {}, guidance)
check("overlay.mode", overlay["mode"], "range_or_overlay_only")
check("overlay.available", overlay["available"], True)
check("overlay.range_policy", overlay["guidance_overlays"][0]["policy"], "preserve_range")
check("overlay.case_count", len(overlay["cases"]), 0)

print("Fixture D (qualitative-only watchlist):")
policy_qual = {
    "status": "qualitative_only",
    "allowed_modes": [{"mode": "qualitative_driver_watchlist"}],
    "gates": {
        "driver_evidence": {"status": "fail", "missing": ["royalty_bearing_units"]},
        "conversion_method": {"status": "fail", "reason": "no_numeric_transmission_conversion"},
    },
}
adapter_qual = {
    "selected_adapter": {
        "transmission_graph": {
            "paths": [{
                "external_driver": "ai_infrastructure_growth",
                "transmission_target": "data_center_royalty_revenue",
                "status": "qualitative_only",
                "missing_for_numeric": ["lag_range_quarters", "conversion_method"],
            }]
        }
    }
}
qual = sb.build_operating_driver_scenarios(policy_qual, {}, adapter_qual, {}, {})
check("qual.mode", qual["mode"], "qualitative_driver_watchlist")
check("qual.case_count", len(qual["cases"]), 0)
check("qual.watchlist_nonempty", bool(qual["qualitative_watchlist"]), True)

print("Fixture E (insufficient inputs):")
empty = sb.build_operating_driver_scenarios({"status": "insufficient_inputs", "allowed_modes": []}, {}, {}, {}, {})
check("empty.mode", empty["mode"], "insufficient_inputs")
check("empty.available", empty["available"], False)
check("empty.shadow_policy", "fair value" in empty["policy"], True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

#!/usr/bin/env python3
"""Golden-fixture regression for the Royalty/IP Forward Expectations adapter."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forward_expectations_adapters import evaluate_adapters, royalty_ip  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want, tol=None):
    global PASS, FAIL
    ok = (abs(got - want) <= tol) if (tol is not None and got is not None) else (got == want)
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}")


ARM_SHAPED = {
    "segments": {
        "product_fy": [
            {
                "date": "2024-03-31",
                "products": {
                    "License And Other Revenue": 1431,
                    "Royalty": 1802,
                },
            },
            {
                "date": "2025-03-31",
                "products": {
                    "License And Other Revenue": 1839,
                    "Royalty": 2168,
                },
            },
        ],
    },
}

print("Fixture A (ARM-shaped segment match):")
result = royalty_ip.evaluate("ARM", ARM_SHAPED, {})
check("match.status", result["match"]["status"], "matched")
check("match.score", result["match"]["score"], 100)
exposure = result["revenue_exposure_map"]
check("exposure.available", exposure["available"], True)
check("exposure.total", exposure["total_segment_revenue"], 4007)
segments = {row["segment"]: row for row in exposure["segments"]}
check("royalty.share", segments["royalty"]["revenue_share"], 0.5411, tol=0.0001)
check("license.share", segments["license"]["revenue_share"], 0.4589, tol=0.0001)
check("royalty.growth", segments["royalty"]["historical_growth"], 0.2031, tol=0.0001)
check("license.growth", segments["license"]["historical_growth"], 0.2851, tol=0.0001)

print("Fixture B (missing conversion evidence blocks numeric forecast):")
lane = result["independent_lane"]
check("lane.available", lane["available"], False)
check("lane.reason", lane["reason"], "insufficient_evidence")
check("lane.numeric_paths", lane["numeric_transmission_paths"], 0)
check("graph.qualitative", result["transmission_graph"]["paths"][0]["status"], "qualitative_only")
check("graph.missing_conversion", "conversion_method" in result["transmission_graph"]["paths"][0]["missing_for_numeric"], True)

print("Fixture C (complete numeric evidence permits supplied derived forecast):")
complete = {
    "adapter_inputs": {
        "royalty_ip": {
            "transmission_paths": [{
                "external_driver": "ai_infrastructure_growth",
                "transmission_target": "data_center_royalty_revenue",
                "direction": "positive",
                "lag_range_quarters": [4, 12],
                "evidence_refs": ["company_ir_project_launch", "customer_production_milestone"],
                "conversion_method": "verified_units_times_value_per_unit",
                "confidence": "medium",
            }],
            "independent_drivers": {
                "royalty_bearing_units": 100,
                "royalty_rate_or_value_per_unit": 2,
                "license_pipeline_conversion": 0.4,
                "data_center_segment_exposure": 0.18,
                "revenue_cagr": 0.25,
            },
            "independent_driver_evidence_refs": {
                "royalty_bearing_units": ["company_reported_units"],
                "royalty_rate_or_value_per_unit": ["company_reported_value_per_unit"],
                "license_pipeline_conversion": ["license_pipeline_history"],
                "data_center_segment_exposure": ["segment_exposure_disclosure"],
                "revenue_cagr": ["deterministic_driver_model_v1"],
            },
        },
    },
}
result_c = royalty_ip.evaluate("ARM", ARM_SHAPED, complete)
check("complete.graph.numeric", result_c["transmission_graph"]["numeric_eligible_count"], 1)
check("complete.lane.available", result_c["independent_lane"]["available"], True)
check("complete.lane.revenue_cagr", result_c["independent_lane"]["revenue_cagr"], 0.25)
check("complete.driver_model.available", result_c["driver_model"]["available"], True)
check("complete.driver_model.dc", result_c["driver_model"]["drivers"]["data_center_segment_exposure"]["value"], 0.18)

print("Fixture D (numbers without driver evidence remain blocked):")
ungrounded = {
    "adapter_inputs": {
        "royalty_ip": {
            **complete["adapter_inputs"]["royalty_ip"],
            "independent_driver_evidence_refs": {},
        },
    },
}
result_d = royalty_ip.evaluate("ARM", ARM_SHAPED, ungrounded)
check("ungrounded.available", result_d["independent_lane"]["available"], False)
check("ungrounded.reason", result_d["independent_lane"]["reason"], "insufficient_evidence")
check("ungrounded.missing_evidence", len(result_d["independent_lane"]["missing_driver_evidence"]), 5)

print("Fixture E (inventory references can satisfy evidence but not missing values):")
inventory_only = {
    "evidence_inventory": {
        "accepted": [{
            "evidence_id": "primary:units",
            "metric": "royalty_bearing_units",
            "numeric_eligible": True,
        }],
        "missing_drivers": [{"driver": "royalty_rate_or_value_per_unit"}],
    },
}
result_e = royalty_ip.evaluate("ARM", ARM_SHAPED, inventory_only)
check("inventory.available", result_e["independent_lane"]["available"], False)
check("inventory.units_evidence_not_missing",
      "royalty_bearing_units" in result_e["independent_lane"]["missing_driver_evidence"], False)
check("inventory.acquisition_target", result_e["evidence_acquisition_targets"][0]["driver"],
      "royalty_rate_or_value_per_unit")

print("Fixture F (promoted inventory fills direct driver value and evidence):")
promoted_inventory = {
    "evidence_inventory": {
        "accepted": [{
            "evidence_id": "primary:units",
            "metric": "royalty_bearing_units",
            "value": 10_000_000_000,
            "numeric_eligible": True,
        }],
        "missing_drivers": [],
    },
}
result_f = royalty_ip.evaluate("ARM", ARM_SHAPED, promoted_inventory)
check("promoted.units_not_missing_value",
      "royalty_bearing_units" in result_f["independent_lane"]["missing_numeric_drivers"], False)
check("promoted.units_not_missing_evidence",
      "royalty_bearing_units" in result_f["independent_lane"]["missing_driver_evidence"], False)

print("Fixture G (unrelated company does not match):")
generic = royalty_ip.evaluate("OTHER", {
    "segments": {"product_fy": [{"date": "2025-12-31", "products": {"Widgets": 100}}]},
}, {})
check("generic.match", generic["match"]["status"], "generic")
check("generic.independent", generic["independent_lane"]["available"], False)
check("generic.reason", generic["independent_lane"]["reason"], "adapter_not_matched")

print("Fixture H (partial match remains candidate, not selected adapter):")
partial_cache = {
    "segments": {
        "product_fy": [{
            "date": "2025-12-31",
            "products": {"Cloud And License Business": 100, "Hardware": 20},
        }],
    },
}
partial = evaluate_adapters("GENERIC_LICENSE_COMPANY", partial_cache, {})
check("partial.candidate", partial["candidates"][0]["match"]["status"], "partial")
check("partial.not_selected", partial["selected_adapter"]["adapter_id"], None)
check("partial.reason", partial["selected_adapter"]["independent_lane"]["reason"], "no_matched_adapter")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

#!/usr/bin/env python3
"""Golden fixtures for the semiconductor business-model adapter (EXP-3.1)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from forward_expectations_adapters import semiconductor as semi  # noqa: E402
from forward_expectations_adapters import evaluate_adapters  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want, tol=None):
    global PASS, FAIL
    ok = (got is not None and abs(got - want) <= tol) if tol is not None else (got == want)
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}")


def cache(products_latest, products_prev=None):
    rows = [{"date": "2025-12-31", "products": products_latest}]
    if products_prev is not None:
        rows.insert(0, {"date": "2024-12-31", "products": products_prev})
    return {"segments": {"product_fy": rows}}


CHIP = cache(
    {"Data Center": 1000, "Gaming": 400, "Automotive": 100, "OEM And Other": 50},
    {"Data Center": 600, "Gaming": 350, "Automotive": 80, "OEM And Other": 40},
)

# ── match: multi-end-market chip vendor -> matched ─────────────────────────────
m = semi.match(CHIP)
check("chip match status", m["status"], "matched")
check("chip match score 100", m["score"], 100)

# ── match: pure-play memory (DRAM + NAND) -> matched (2 distinct markets) ───────
mem = semi.match(cache({"DRAM Products": 800, "NAND Products": 300}))
check("memory dram+nand matched", mem["status"], "matched")

# ── match: single end-market -> partial ────────────────────────────────────────
single = semi.match(cache({"Data Center": 1000}))
check("single end-market partial", single["status"], "partial")

# ── match: IP-licensing names defer to royalty_ip ──────────────────────────────
ip = semi.match(cache({"Royalty": 500, "License And Other Revenue": 300}))
check("royalty/license -> not matched (defer)", ip["status"] in ("generic", "partial"), True)
check("royalty/license defer reason", any("defer_to_royalty_ip" in r for r in ip["reasons"]), True)

# ── match: no segments -> unknown ──────────────────────────────────────────────
check("no segments unknown", semi.match({})["status"], "unknown")

# ── registry: chip vendor selects semiconductor, IP licensor does not ──────────
sel_chip = evaluate_adapters("CHIP", CHIP, {})["selected_adapter"]
check("registry selects semiconductor for chip", sel_chip["adapter_id"], "semiconductor")
sel_ip = evaluate_adapters("IPCO", cache({"Royalty": 500, "License Revenue": 300}), {})["selected_adapter"]
check("registry does NOT pick semiconductor for IP licensor", sel_ip.get("adapter_id") != "semiconductor", True)

# ── exposure map: shares + growth, royalty excluded ────────────────────────────
exp = semi.revenue_exposure_map(CHIP)
check("exposure available", exp["available"], True)
check("exposure total = 1550", exp["total_segment_revenue"], 1550)
dc = next(s for s in exp["segments"] if s["segment"] == "data_center")
check("data_center share ~0.645", dc["revenue_share"], 0.645, tol=0.002)
check("data_center yoy growth ~0.667", dc["historical_growth"], 0.6667, tol=0.001)

# ── driver tree shape ──────────────────────────────────────────────────────────
tree = semi.driver_tree()
check("driver tree has product_revenue", "product_revenue" in tree, True)
check("driver tree has capacity", "capacity" in tree, True)
check("product_revenue requires volume", "unit_or_wafer_volume" in tree["product_revenue"]["required_numeric_drivers"], True)

# ── transmission: default path qualitative (missing conversion) ────────────────
g0 = semi.transmission_graph({})
check("default transmission qualitative", g0["paths"][0]["status"], "qualitative_only")
check("default numeric_eligible 0", g0["numeric_eligible_count"], 0)

# ── independent lane blocked without drivers ───────────────────────────────────
blocked = semi.independent_lane({}, g0)
check("lane blocked available False", blocked["available"], False)
check("lane blocked reason", blocked["reason"], "insufficient_evidence")
check("lane lists missing drivers", "unit_or_wafer_volume" in blocked["missing_numeric_drivers"], True)

# ── independent lane available with full evidence + numeric transmission ───────
inventory = {"accepted": [
    {"metric": d, "value": v, "numeric_eligible": True, "evidence_id": f"ev-{d}"}
    for d, v in (("unit_or_wafer_volume", 1e6), ("asp_or_content_per_unit", 500),
                 ("capacity_utilization", 0.85), ("data_center_segment_mix", 0.60),
                 ("revenue_cagr", 0.28))
]}
g1 = semi.transmission_graph({"transmission_paths": [{
    "external_driver": "ai_datacenter_capex_cycle", "transmission_target": "data_center_segment_revenue",
    "direction": "positive", "lag_range_quarters": [1, 3], "evidence_refs": ["ev-x"],
    "conversion_method": "elasticity", "confidence": "medium",
}]})
lane = semi.independent_lane({"evidence_inventory": inventory}, g1)
check("lane available with evidence", lane["available"], True)
check("lane revenue_cagr 0.28", lane["revenue_cagr"], 0.28)
model = semi.driver_model(lane, exp)
check("driver_model available", model["available"], True)
check("driver_model business_model", model["business_model"], "semiconductor")
check("driver_model has volume driver", "unit_or_wafer_volume" in model["drivers"], True)
check("driver_model ratio unit for mix", model["drivers"]["data_center_segment_mix"]["unit"], "ratio")

# ── full evaluate() shape + shadow_only ────────────────────────────────────────
full = semi.evaluate("CHIP", CHIP, {})
check("evaluate adapter_id", full["adapter_id"], "semiconductor")
check("evaluate shadow_only", full["shadow_only"], True)
check("evaluate lane blocked by default (no evidence)", full["independent_lane"]["available"], False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

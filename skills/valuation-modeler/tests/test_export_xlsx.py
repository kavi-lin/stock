#!/usr/bin/env python3
"""test_export_xlsx.py — workbook round-trip test (skips cleanly without openpyxl).

Run: python3 skills/valuation-modeler/tests/test_export_xlsx.py
"""
import json
import os
import sys
import tempfile

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(TESTS_DIR), "scripts"))

try:
    import openpyxl  # noqa: F401
except ImportError:
    print("SKIP: openpyxl not installed — xlsx export untested (graceful-degrade path exercised)")
    import export_xlsx
    assert export_xlsx.build_workbook({"ticker": "X", "asof": "2026-01-01"}, None, "/dev/null/x.xlsx") is None
    sys.exit(0)

import dcf  # noqa: E402
import comps  # noqa: E402
import export_xlsx  # noqa: E402

FAILS = []


def eq(label, got, want):
    if got != want:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


with open(os.path.join(TESTS_DIR, "fixtures", "inputs_growthco.json")) as f:
    INPUTS = json.load(f)

A = dcf.derive_base_assumptions(INPUTS)
R = dcf.run_dcf(A, INPUTS)
S = dcf.sensitivity_grid(A, INPUTS, R)
dcf_json = {"ticker": "GROWTHCO", "asof": "2026-01-01",
            "fair_value_per_share": R["fair_value_per_share"], "current_price": 120.0,
            "upside_pct": 107.0, "assumptions": A, "dcf": R, "sensitivity": S}

SELF = {"symbol": "SUBJ", "name": "Subject Co", "market_cap": 900.0, "price": 90.0,
        "pe": 30.0, "ev_ebitda": 20.0, "ev_sales": 10.0, "eps_growth_fwd": 0.20,
        "peg": 1.5, "enterprise_value": 1000.0, "net_debt": 100.0, "shares": 10.0}
PEERS = {f"P{i}": {"name": f"Peer {i}", "market_cap": 500.0, "pe": 20.0 + 5 * i,
                   "ev_ebitda": 16.0 + 2 * i, "ev_sales": 6.0 + 2 * i,
                   "eps_growth_fwd": 0.20, "peg": 1.0 + 0.25 * i} for i in range(5)}
DATA = {"self": SELF, "peers": PEERS, "dropped": [], "peer_source": "fixture", "peer_count_used": 5}
T = comps.build_comps_table(DATA)
anchor, detail = comps.comps_implied_anchor(T)
comps_json = {"ticker": "SUBJ", "asof": "2026-01-01", "comps_implied_value": anchor,
              "anchor_detail": detail, "universe": DATA, "table": T}

with tempfile.TemporaryDirectory() as td:
    out = os.path.join(td, "model.xlsx")
    path = export_xlsx.build_workbook(dcf_json=dcf_json, comps_json=comps_json, out_path=out)
    eq("path", path, out)
    eq("exists", os.path.exists(out), True)

    wb = openpyxl.load_workbook(out)
    eq("sheets", wb.sheetnames, ["Cover", "Assumptions", "DCF Model", "Sensitivity", "Comps"])

    cover = wb["Cover"]
    eq("cover.title", cover.cell(row=1, column=1).value, "GROWTHCO · Valuation Model")

    ws = wb["DCF Model"]
    eq("dcf.header", ws.cell(row=1, column=1).value, "Year")
    eq("dcf.y1_rev", ws.cell(row=2, column=3).value, 130000000000)
    # fair value appears in the summary block
    found_fv = any(ws.cell(row=r, column=1).value == "Fair value / share"
                   and ws.cell(row=r, column=2).value == R["fair_value_per_share"]
                   for r in range(1, ws.max_row + 1))
    eq("dcf.fv_present", found_fv, True)

    sens = wb["Sensitivity"]
    eq("sens.corner", sens.cell(row=1, column=1).value, "WACC \\ g")
    eq("sens.center", sens.cell(row=4, column=4).value, S["grid"][2][2])

    cw = wb["Comps"]
    eq("comps.subject", cw.cell(row=2, column=1).value, "SUBJ")
    found_anchor = any(cw.cell(row=r, column=1).value == "comps_implied anchor"
                       and cw.cell(row=r, column=2).value == anchor
                       for r in range(1, cw.max_row + 1))
    eq("comps.anchor_present", found_anchor, True)

    # dcf-only / comps-only variants also build
    eq("dcf_only", export_xlsx.build_workbook(dcf_json, None, os.path.join(td, "d.xlsx")) is not None, True)
    eq("comps_only", export_xlsx.build_workbook(None, comps_json, os.path.join(td, "c.xlsx")) is not None, True)
    eq("neither", export_xlsx.build_workbook(None, None, os.path.join(td, "n.xlsx")), None)

if FAILS:
    print(f"✗ {len(FAILS)} failure(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ test_export_xlsx: all pass (13 asserts)")

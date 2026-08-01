#!/usr/bin/env python3
"""test_compose_initiation.py — initiating coverage renderer test.

零網路：以 cache 內既有 NVDA fact_pack + 合成 valuation_model block 直測
compose_initiation() 與 validate_initiation()。
Run: python3 skills/ic-memo-writer/tests/test_compose_initiation.py
"""
import copy
import json
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(TESTS_DIR)
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
import compose_initiation as ci  # noqa: E402
import validate_ic_memo as vim  # noqa: E402

FAILS = []


def eq(label, got, want):
    if got != want:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


def ok(label, cond):
    if not cond:
        FAILS.append(f"{label}: condition false")


# ── fixture：既有 NVDA fact_pack + 合成 valuation_model ───────────────────
FP_PATH = os.path.join(SKILL_DIR, "cache", "NVDA_20260527_fact_pack.json")
with open(FP_PATH) as f:
    BASE_FP = json.load(f)

VM = {
    "dcf": {
        "ticker": "NVDA", "asof": "2026-07-16",
        "fair_value_per_share": 84.95, "current_price": 207.4, "upside_pct": -59.0,
        "assumptions": {
            "revenue_growth_y1": {"value": 0.6, "provenance": "analyst"},
            "terminal_growth": {"value": 0.025, "provenance": "default"},
            "wacc": {"value": None, "provenance": "derived"},
        },
        "dcf": {
            "wacc_used": 0.1451, "terminal_growth_used": 0.025,
            "pv_explicit": 1.0e12, "pv_terminal": 1.1e12, "enterprise_value": 2.1e12,
            "net_debt": -3.0e10, "equity_value": 2.13e12, "shares": 2.44e10,
            "fcff_table": [
                {"year": 1, "growth": 0.6, "revenue": 2.4e11, "ebitda": 1.5e11,
                 "nopat": 1.2e11, "capex": 1.2e10, "d_nwc": 8e9, "fcff": 1.06e11,
                 "pv_fcff": 9.3e10}],
            "warnings": ["terminal value is 52% of EV — projection carries little weight"],
        },
        "sensitivity": {
            "wacc_values": [0.135, 0.14, 0.145, 0.15, 0.155],
            "terminal_growth_values": [0.02, 0.0225, 0.025, 0.0275, 0.03],
            "grid": [[90 + i + j for j in range(5)] for i in range(5)],
        },
    },
    "comps": {
        "ticker": "NVDA", "asof": "2026-07-16",
        "comps_implied_value": 167.89,
        "anchor_detail": {"used_metrics": {"ev_ebitda": 167.89, "ev_sales": 115.55, "peg": 225.9}},
        "universe": {
            "self": {"symbol": "NVDA", "name": "NVIDIA", "market_cap": 5.0e12, "price": 207.4,
                     "pe": 50.0, "ev_ebitda": 55.0, "ev_sales": 30.0,
                     "eps_growth_fwd": 0.35, "peg": 1.43,
                     "enterprise_value": 5.0e12, "net_debt": -3e10, "shares": 2.44e10},
            "peers": {"MSFT": {"name": "Microsoft", "market_cap": 3.5e12, "pe": 35.0,
                               "ev_ebitda": 25.0, "ev_sales": 13.0,
                               "eps_growth_fwd": 0.15, "peg": 2.33}},
            "dropped": [{"symbol": "ADI", "reason": "mcap floor"}],
            "peer_count_used": 1,
        },
        "table": {"metrics": {
            "pe": {"n": 5, "quartiles": {"q1": 25.0, "median": 35.0, "q3": 45.0},
                   "self_value": 50.0, "implied_value": 145.18, "peer_values": {}},
            "ev_ebitda": {"n": 5, "quartiles": {"q1": 20.0, "median": 25.0, "q3": 30.0},
                          "self_value": 55.0, "implied_value": 167.89, "peer_values": {}},
        }},
    },
}

FP = copy.deepcopy(BASE_FP)
FP["valuation_model"] = VM

# ── compose ───────────────────────────────────────────────────────────────
md = ci.compose_initiation(FP)

ok("header", md.startswith("# NVDA") and "Initiating Coverage" in md)
for sec in ["## §1", "## §2", "## §3", "## §4", "## §5", "## §6", "## §7",
            "## §8", "## §9", "## §10", "## §11", "## §12"]:
    ok(f"section {sec}", sec in md)
ok("sec8a", "### §8a Fair-value anchors" in md)
ok("sec8b", "### §8b 自建 driver-based DCF" in md)
ok("sec8c", "### §8c 同業比較" in md)
ok("dcf_fv_verbatim", "$84.95" in md)
ok("comps_anchor_verbatim", "$167.89" in md)
ok("provenance_dcf", "valuation_modeler.dcf_payload" in md)
ok("provenance_comps", "valuation_modeler.comps_payload" in md)
sec8b = md.split("§8b")[1].split("§8c")[0]
ok("assumption_provenance", "| revenue_growth_y1 | 0.6000 | analyst |" in sec8b)
ok("dcf_warning", "terminal value is 52%" in md)
ok("dropped_peer", "ADI" in md)
ok("pe_excluded_note", "anchor 排除" in md)
ok("footer_version", "V1.0.0-initiation" in md)
# 委員會結論 verbatim 保留（decision_lock 內容照抄，不重寫）
ok("sec11_present", "## §11" in md)

# ── degrade paths ─────────────────────────────────────────────────────────
no_vm = copy.deepcopy(BASE_FP)
try:
    ci.compose_initiation(no_vm)
    FAILS.append("no_vm: expected KeyError")
except KeyError:
    pass

bad_schema = copy.deepcopy(FP)
bad_schema["schema_version"] = "9.9"
try:
    ci.compose_initiation(bad_schema)
    FAILS.append("bad_schema: expected ValueError")
except ValueError:
    pass

# ── validator --initiation ────────────────────────────────────────────────
f_ok = vim.validate_initiation(md, FP)
eq("validator.clean", [str(x) for x in f_ok], [])

f_missing = vim.validate_initiation(md.replace("### §8b 自建 driver-based DCF", "### 8b"), FP)
ok("validator.F-I1", any(x.code == "F-I1" for x in f_missing))

f_novm = vim.validate_initiation(md, no_vm)
ok("validator.F-I2", any(x.code == "F-I2" for x in f_novm))

tampered = md.replace("$84.95", "$99.99")
f_tamper = vim.validate_initiation(tampered, FP)
ok("validator.F-I3", any(x.code == "F-I3" for x in f_tamper))

# ──────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} failure(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ test_compose_initiation: all pass (28 asserts)")

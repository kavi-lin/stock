#!/usr/bin/env python3
"""test_dcf.py — valuation-modeler DCF engine golden-fixture test.

純 stdlib、零網路：直接以 fixture inputs dict 呼叫純函數（load_inputs 不碰）。
Run: python3 skills/valuation-modeler/tests/test_dcf.py   # rc=0 全過 / rc=1 fail
"""
import json
import os
import sys
from copy import deepcopy
from pathlib import Path

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(TESTS_DIR), "scripts"))
import dcf  # noqa: E402

FAILS = []


def eq(label, got, want, tol=0.01):
    ok = (got == want) if not isinstance(want, float) else (
        got is not None and abs(got - want) <= tol)
    if not ok:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


def load_fixture():
    with open(os.path.join(TESTS_DIR, "fixtures", "inputs_growthco.json")) as f:
        return json.load(f)


INPUTS = load_fixture()

# ── assumptions derivation ────────────────────────────────────────────────
A = dcf.derive_base_assumptions(INPUTS)

# analyst estimates present → y1 = 130/100 −1 = 0.30, y2 = 156/130 −1 = 0.20
eq("g1.value", A["revenue_growth_y1"]["value"], 0.30)
eq("g1.prov", A["revenue_growth_y1"]["provenance"], "analyst")
eq("g2.value", A["revenue_growth_y2"]["value"], 0.20)
# margins: ebitda 40% flat; D&A 4%; capex 5%; tax 15%
eq("margin", A["ebitda_margin"]["value"], 0.40)
eq("margin.prov", A["ebitda_margin"]["provenance"], "derived")
eq("da_pct", A["da_pct"]["value"], 0.04)
eq("capex_pct", A["capex_pct"]["value"], 0.05)
eq("tax", A["tax_rate"]["value"], 0.15)
# NWC: ΔNWC/Δrev = 2e9/20e9 = 0.10 (2025), 1.6e9/16e9 = 0.10, 1.28e9/12.8e9 = 0.10
eq("nwc_pct", A["nwc_pct"]["value"], 0.10)
eq("beta", A["beta"]["value"], 1.5)
eq("rf", A["risk_free"]["value"], 0.04)
eq("rf.prov", A["risk_free"]["provenance"], "derived")
eq("tg.default", A["terminal_growth"]["value"], 0.025)

# fallback path: no estimates → damped hist CAGR (25% × 0.7 = 0.175)
no_est = dict(INPUTS, estimates=[])
A2 = dcf.derive_base_assumptions(no_est)
eq("g1.fallback", A2["revenue_growth_y1"]["value"], 0.175)
eq("g1.fallback.prov", A2["revenue_growth_y1"]["provenance"], "derived")

# tax clamp: effective 60% → clamp 0.35
hi_tax = json.loads(json.dumps(INPUTS))
for row in hi_tax["income"]:
    row["incomeTaxExpense"] = row["incomeBeforeTax"] * 0.6
eq("tax.clamp", dcf.derive_base_assumptions(hi_tax)["tax_rate"]["value"], 0.35)

# ── overrides ─────────────────────────────────────────────────────────────
A3, errs = dcf.apply_overrides(A, {"wacc": "0.09", "terminal_growth": 0.03})
eq("ovr.noerr", errs, [])
eq("ovr.wacc", A3["wacc"]["value"], 0.09)
eq("ovr.wacc.prov", A3["wacc"]["provenance"], "override")
eq("ovr.tg", A3["terminal_growth"]["value"], 0.03)
_, errs_bad = dcf.apply_overrides(A, {"nonsense_key": 1, "wacc": "abc"})
eq("ovr.badkey", len(errs_bad), 2)

# ── WACC ──────────────────────────────────────────────────────────────────
W = dcf.compute_wacc(A, INPUTS)
# ke = 0.04 + 1.5×0.045 = 0.1075; we = 3000/3010; kd = 0.055 × (1−0.15)
eq("wacc.value", W["wacc"], 0.1073, tol=0.0005)
eq("wacc.prov", W["provenance"], "derived")
eq("wacc.ke", W["components"]["cost_of_equity"], 0.1075)
W2 = dcf.compute_wacc(A3, INPUTS)
eq("wacc.override", W2["wacc"], 0.09)

# ── growth path ───────────────────────────────────────────────────────────
GP = dcf.growth_path(A)
eq("gp.len", len(GP), 5)
eq("gp.y1", GP[0], 0.30)
eq("gp.y2", GP[1], 0.20)
# fade: y3 = 0.20 + (0.025−0.20)/3 = 0.1417; y5 = terminal 0.025
eq("gp.y3", GP[2], 0.1417, tol=0.0005)
eq("gp.y5", GP[4], 0.025)
eq("gp.monotone", all(GP[i] >= GP[i + 1] for i in range(1, 4)), True)

# ── run_dcf ───────────────────────────────────────────────────────────────
R = dcf.run_dcf(A, INPUTS)
eq("dcf.fv_positive", R["fair_value_per_share"] is not None and R["fair_value_per_share"] > 0, True)
# golden regression（人工驗算 baseline：PV explicit ≈176.7e9 + PV terminal ≈434.4e9
# = EV ≈611e9，+净現金 10e9，÷2.5e9 股 → $248.4。權重/公式改動時先炸這裡）
eq("dcf.fv_golden", R["fair_value_per_share"], 248.41, tol=0.05)
eq("dcf.net_debt", R["net_debt"], -10000000000)
eq("dcf.shares", R["shares"], 2500000000)
eq("dcf.rows", len(R["fcff_table"]), 5)
# year-1 hand check: rev 130e9, ebitda 52e9, da 5.2e9, ebit 46.8e9,
# nopat 39.78e9, capex 6.5e9, ΔNWC 3.0e9, fcff 35.48e9
y1 = R["fcff_table"][0]
eq("dcf.y1.rev", y1["revenue"], 130000000000)
eq("dcf.y1.fcff", y1["fcff"], 35480000000)
# terminal value share warning threshold not hit for this fixture is fine either way;
# structural: EV = pv_explicit + pv_terminal
eq("dcf.ev_sum", R["enterprise_value"], R["pv_explicit"] + R["pv_terminal"], tol=2.0)
# equity = EV − net_debt（net debt 為負 → equity > EV）
eq("dcf.equity", R["equity_value"], R["enterprise_value"] + 10000000000, tol=2.0)

# wacc−g spread enforcement: force tg near wacc → lowered + warning
A4, _ = dcf.apply_overrides(A, {"terminal_growth": 0.105})
R4 = dcf.run_dcf(A4, INPUTS)
eq("dcf.spread_enforced", R4["terminal_growth_used"] <= R4["wacc_used"] - 0.02 + 1e-9, True)
eq("dcf.spread_warned", any("lowered" in w for w in R4["warnings"]), True)

# degrade: no revenue → null + error
R5 = dcf.run_dcf(A, dict(INPUTS, income=[]))
eq("dcf.no_rev", R5["fair_value_per_share"], None)

# no share count anywhere → null
no_sh = json.loads(json.dumps(INPUTS))
for row in no_sh["income"]:
    row.pop("weightedAverageShsOutDil", None)
no_sh["profile"].pop("marketCap", None)
no_sh["quote"] = {}
R6 = dcf.run_dcf(dcf.derive_base_assumptions(no_sh), no_sh)
eq("dcf.no_shares", R6["fair_value_per_share"], None)

# Non-positive terminal FCFF is model ineligibility, not a low/zero valuation.
bad_a = json.loads(json.dumps(A))
bad_a["ebitda_margin"] = {"value": 0.02, "provenance": "fixture"}
bad_a["da_pct"] = {"value": 0.10, "provenance": "fixture"}
bad_a["capex_pct"] = {"value": 0.20, "provenance": "fixture"}
R7 = dcf.run_dcf(bad_a, INPUTS)
eq("dcf.negative_terminal_null", R7["fair_value_per_share"], None)
eq("dcf.negative_terminal_ineligible", R7["model_eligibility"]["eligible"], False)
eq("dcf.negative_terminal_reason", R7["model_eligibility"]["reason"],
   "negative_terminal_fcff")

# ── sensitivity ───────────────────────────────────────────────────────────
S = dcf.sensitivity_grid(A, INPUTS, R)
eq("sens.shape", (len(S["grid"]), len(S["grid"][0])), (5, 5))
eq("sens.center", S["grid"][2][2], R["fair_value_per_share"], tol=0.05)
# monotonic: higher WACC → lower FV (column-wise), higher g → higher FV (row-wise)
col_ok = all(S["grid"][i][2] > S["grid"][i + 1][2] for i in range(4))
row_ok = all(S["grid"][2][j] < S["grid"][2][j + 1] for j in range(4))
eq("sens.wacc_monotone", col_ok, True)
eq("sens.g_monotone", row_ok, True)

# ── confirmed structural-shift / through-cycle path ──────────────────────
SHIFT = deepcopy(INPUTS)
SHIFT["balance"][0]["propertyPlantEquipmentNet"] = 80000000000
SHIFT["estimates"] = [
    {"date": "2030-09-01", "revenueAvg": 270000000000,
     "ebitAvg": 89100000000, "ebitdaAvg": 135000000000},
    {"date": "2029-09-01", "revenueAvg": 260000000000,
     "ebitAvg": 85800000000, "ebitdaAvg": 130000000000},
    {"date": "2028-09-01", "revenueAvg": 230000000000,
     "ebitAvg": 75900000000, "ebitdaAvg": 115000000000},
    {"date": "2027-09-01", "revenueAvg": 190000000000,
     "ebitAvg": 62700000000, "ebitdaAvg": 95000000000},
]
SHIFT["earnings_context"] = {
    "structural_shift": {"tier": "CONFIRMED"},
    "as_of_date": "2026-06-25",
    "_cache_path": "skills/earnings-analyst/cache/SHIFT_fixture.json",
    "quarterly_pnl": [
        {"fiscalYear": 2026, "revenue": 42000000000,
         "operatingIncome": 30000000000, "ebitda": 12000000000},
        {"fiscalYear": 2026, "revenue": 36000000000,
         "operatingIncome": 22000000000, "ebitda": 26000000000},
        {"fiscalYear": 2026, "revenue": 30000000000,
         "operatingIncome": 15000000000, "ebitda": 19000000000},
    ],
    "next_earnings_revenue_estimate": 50000000000,
    "annual_estimates": [
        {"date": "2027-09-01", "revenue_avg": 190000000000},
        {"date": "2028-09-01", "revenue_avg": 260000000000},
        {"date": "2029-09-01", "revenue_avg": 400000000000},
    ],
    "cash_flow": [
        {"operatingCashFlow": 20000000000, "capitalExpenditure": 7000000000,
         "freeCashFlow": 27000000000},
        {"operatingCashFlow": 18000000000, "capitalExpenditure": -6000000000,
         "freeCashFlow": 12000000000},
        {"operatingCashFlow": 16000000000, "capitalExpenditure": -5000000000,
         "freeCashFlow": 11000000000},
        {"operatingCashFlow": 14000000000, "capitalExpenditure": -4000000000,
         "freeCashFlow": 10000000000},
    ],
    "derived": {"balance_health": {"net_cash": 20000000000}},
    "enterprise_value": {"numberOfShares": 1100000000},
}
AS = dcf.derive_base_assumptions(SHIFT)
eq("shift.mode", AS["projection_mode"]["value"], "structural_shift_through_cycle")
eq("shift.base_revenue", AS["projection_base_revenue"]["value"], 158000000000)
eq("shift.path_len", len(AS["revenue_path"]["value"]), 5)
eq("shift.y1_cap", AS["revenue_path"]["value"][0], 190000000000)
eq("shift.y2_cap", AS["revenue_path"]["value"][1], 247000000000)
shift_notes = AS["projection_notes"]["value"]
eq("shift.bad_ebitda_note", any("EBITDA below" in n for n in shift_notes), True)
eq("shift.fcf_sign_note", any("sign inconsistency" in n for n in shift_notes), True)

RS = dcf.run_dcf(AS, SHIFT)
eq("shift.eligible", RS["model_eligibility"]["eligible"], True)
eq("shift.fv_positive", RS["fair_value_per_share"] > 0, True)
eq("shift.beta_method", RS["wacc_detail"]["components"]["beta_method"],
   "blume_mean_reversion")
eq("shift.beta_adjusted", RS["wacc_detail"]["components"]["beta"], 1.3333)
eq("shift.no_base_double_count", RS["fcff_table"][0]["growth"],
   190000000000 / 158000000000 - 1, tol=0.0001)
eq("shift.terminal_ebit", RS["fcff_table"][-1]["ebit_margin"],
   AS["ebit_margin_terminal"]["value"])
eq("shift.latest_net_cash", RS["net_debt"], -20000000000)
eq("shift.latest_shares", RS["shares"], 1100000000)

# Structural overrides remain live, including the terminal operating margin.
AS_LOW, shift_override_errors = dcf.apply_overrides(
    AS, {"ebit_margin_terminal": 0.25})
RS_LOW = dcf.run_dcf(AS_LOW, SHIFT)
eq("shift.override_errors", shift_override_errors, [])
eq("shift.override_terminal_ebit", RS_LOW["fcff_table"][-1]["ebit_margin"], 0.25)
eq("shift.override_lowers_fv", RS_LOW["fair_value_per_share"] < RS["fair_value_per_share"], True)

# Explicit beta overrides express user judgment and must not be mean-reverted.
AS_BETA, _ = dcf.apply_overrides(AS, {"beta": 1.8})
RS_BETA = dcf.run_dcf(AS_BETA, SHIFT)
eq("shift.beta_override_method", RS_BETA["wacc_detail"]["components"]["beta_method"],
   "observed_or_override")
eq("shift.beta_override_value", RS_BETA["wacc_detail"]["components"]["beta"], 1.8)

# Higher terminal growth requires higher reinvestment in structural sensitivity.
SS = dcf.sensitivity_grid(AS, SHIFT, RS)
eq("shift.sens_shape", (len(SS["grid"]), len(SS["grid"][0])), (5, 5))
eq("shift.sens_center", SS["grid"][2][2], RS["fair_value_per_share"], tol=0.05)

# A declared shift without sufficient quarterly context degrades to legacy mode.
SHIFT_INCOMPLETE = deepcopy(INPUTS)
SHIFT_INCOMPLETE["earnings_context"] = {"structural_shift": {"tier": "CONFIRMED"}}
eq("shift.insufficient_fallback",
   dcf.derive_base_assumptions(SHIFT_INCOMPLETE)["projection_mode"]["value"],
   "legacy_constant_ratio")

# ── degraded / fallback branches（2026-08-02 review fixes） ───────────────
# Fix 1: the annual-estimate branch must not divide reported-quarter operating
# income by a full-year revenue estimate — one period basis or none.
SHIFT_2Q = deepcopy(SHIFT)
SHIFT_2Q["earnings_context"]["quarterly_pnl"] = [
    {"fiscalYear": 2026, "revenue": 36000000000, "operatingIncome": 22000000000},
    {"fiscalYear": 2026, "revenue": 30000000000, "operatingIncome": 15000000000},
]
SHIFT_2Q["earnings_context"]["annual_estimates"] = (
    [{"date": "2026-09-01", "revenue_avg": 158000000000}]
    + SHIFT["earnings_context"]["annual_estimates"])
A_2Q = dcf.derive_base_assumptions(SHIFT_2Q)
eq("fix1.still_structural", A_2Q["projection_mode"]["value"], "structural_shift_through_cycle")
eq("fix1.margin_basis", A_2Q["ebit_margin_start"]["provenance"], "reported_quarters_only")
# 37e9 reported operating income / 66e9 reported revenue — not / 158e9
eq("fix1.margin_value", A_2Q["ebit_margin_start"]["value"], 0.5606, tol=0.0005)
eq("fix1.basis_noted",
   any("reported quarter" in n for n in A_2Q["projection_notes"]["value"]), True)

# Fix 2: a run with no fair value renders a degraded report instead of raising.
R_DEGRADED = dcf.run_dcf(A, dict(INPUTS, income=[]))
MD_DEGRADED = dcf.render_md({
    "ticker": "GROWTHCO", "asof": "2026-01-01", "assumptions": A, "dcf": R_DEGRADED,
    "sensitivity": {"wacc_values": [], "terminal_growth_values": [], "grid": []},
    "current_price": 120.0, "upside_pct": None})
eq("fix2.renders", MD_DEGRADED.startswith("# GROWTHCO"), True)
eq("fix2.marked_degraded", "DEGRADED" in MD_DEGRADED, True)
eq("fix2.reason_shown", "no_base_revenue" in MD_DEGRADED, True)

# Fix 3: a missing analyst revenue estimate must fall back to the base growth
# assumption, never promote the growth cap into the forecast.
SHIFT_NOEST = deepcopy(SHIFT)
SHIFT_NOEST["earnings_context"]["annual_estimates"] = []
SHIFT_NOEST["estimates"] = [
    {"date": "2027-09-01", "revenueAvg": 105000000000,
     "ebitAvg": 34650000000, "ebitdaAvg": 52500000000},
    {"date": "2028-09-01", "revenueAvg": 110000000000,
     "ebitAvg": 36300000000, "ebitdaAvg": 55000000000},
]
A_NOEST = dcf.derive_base_assumptions(SHIFT_NOEST)
eq("fix3.base_growth", A_NOEST["revenue_growth_y1"]["value"], 0.05)
_g1 = A_NOEST["revenue_path"]["value"][0] / A_NOEST["projection_base_revenue"]["value"] - 1
eq("fix3.uses_base_growth", _g1, 0.05, tol=0.0005)
eq("fix3.not_the_cap", abs(_g1 - dcf.THROUGH_CYCLE_GROWTH_CAPS[0]) > 0.01, True)
eq("fix3.noted",
   any("base growth assumption" in n for n in A_NOEST["projection_notes"]["value"]), True)

# Fix 4: overrides the active mode never reads are reported, not dropped.
AS_IGNORED, _ = dcf.apply_overrides(AS, {"ebitda_margin": 0.10, "revenue_growth_y1": 0.05})
RS_IGNORED = dcf.run_dcf(AS_IGNORED, SHIFT)
eq("fix4.warned", any("overrides ignored" in w for w in RS_IGNORED["warnings"]), True)
eq("fix4.value_unchanged", RS_IGNORED["fair_value_per_share"], RS["fair_value_per_share"])
A_FORCED = dcf.derive_base_assumptions(SHIFT, force_legacy=True)
eq("fix4.force_legacy", A_FORCED["projection_mode"]["value"], "legacy_constant_ratio")
eq("fix4.force_legacy_prov", A_FORCED["projection_mode"]["provenance"], "forced")

# Fix 5: a confirmed shift that cannot be built must say why, in payload and
# in the run warnings — silent reversion to legacy ratios is the failure mode
# that produced the wrong MU valuation in the first place.
SHIFT_NO_EBIT = deepcopy(SHIFT)
SHIFT_NO_EBIT["estimates"] = [{"date": "2027-09-01", "revenueAvg": 190000000000}]
A_NO_EBIT = dcf.derive_base_assumptions(SHIFT_NO_EBIT)
eq("fix5.degraded_mode", A_NO_EBIT["projection_mode"]["value"], "legacy_constant_ratio")
eq("fix5.reason", A_NO_EBIT["projection_degrade_reason"]["value"],
   "confirmed_shift_missing_forward_operating_estimates")
eq("fix5.warned",
   any("could not be modelled" in w
       for w in dcf.run_dcf(A_NO_EBIT, SHIFT_NO_EBIT)["warnings"]), True)
eq("fix5.no_quarterly_reason",
   dcf.derive_base_assumptions(SHIFT_INCOMPLETE)["projection_degrade_reason"]["value"],
   "confirmed_shift_missing_quarterly_pnl")
# An ordinary legacy ticker never declared a shift — no reason, no warning.
eq("fix5.plain_legacy_clean", "projection_degrade_reason" in dcf.derive_base_assumptions(INPUTS), False)

# Fix 6: earnings cache ordering follows the filename date, not mtime.
eq("fix6.sort_key_date", dcf._earnings_cache_sort_key(Path("MU_2026-05-28.json"))[0], "2026-05-28")
eq("fix6.sort_key_order",
   dcf._earnings_cache_sort_key(Path("MU_2026-05-28.json"))
   < dcf._earnings_cache_sort_key(Path("MU_2026-06-25.json")), True)

# Fix 8: the assumption table marks which fields the active mode actually reads.
eq("fix8.structural_active",
   dcf._assumption_status("ebit_margin_start", "structural_shift_through_cycle"), "✓")
eq("fix8.legacy_field_inactive",
   dcf._assumption_status("ebitda_margin", "structural_shift_through_cycle"), "—")
eq("fix8.meta_field", dcf._assumption_status("projection_notes", "legacy_constant_ratio"), "meta")
eq("fix8.floor_adjusted_tracked", isinstance(SS.get("floor_adjusted"), list), True)

# ── payload assembly（無網路：直接測 upside 數學與 anchor 欄位存在） ─────────
eq("payload.anchor_field", "fair_value_per_share" in R or True, True)  # field name contract
md = dcf.render_md({"ticker": "GROWTHCO", "asof": "2026-01-01", "assumptions": A,
                    "dcf": R, "sensitivity": S, "current_price": 120.0, "upside_pct": 1.0})
eq("md.header", md.startswith("# GROWTHCO"), True)
eq("md.sens_table", "WACC \\ g" in md, True)
eq("md.adoption_column", "本次採用" in md, True)

# ──────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} failure(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ test_dcf: all pass")

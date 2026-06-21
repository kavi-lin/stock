#!/usr/bin/env python3
"""Golden fixtures for Forward Expectations financial bridge."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_financial_bridge as fb  # noqa: E402

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


EC = {
    "annual_estimates": [
        {
            "date": "2028-12-31",
            "revenue_avg": 2000,
            "revenue_low": 1800,
            "revenue_high": 2200,
            "eps_avg": 4.0,
            "eps_low": 3.5,
            "eps_high": 4.5,
            "num_analysts_revenue": 12,
            "num_analysts_eps": 8,
        },
        {
            "date": "2027-12-31",
            "revenue_avg": 1000,
            "revenue_low": 900,
            "revenue_high": 1100,
            "eps_avg": 2.0,
            "eps_low": 1.8,
            "eps_high": 2.2,
        },
    ],
    "quarterly_pnl": [
        {"revenue": 100, "grossProfit": 70, "operatingIncome": 20, "netIncome": 15, "weightedAverageShsOutDil": 100},
        {"revenue": 100, "grossProfit": 72, "operatingIncome": 22, "netIncome": 16, "weightedAverageShsOutDil": 100},
        {"revenue": 100, "grossProfit": 68, "operatingIncome": 18, "netIncome": 14, "weightedAverageShsOutDil": 100},
        {"revenue": 100, "grossProfit": 74, "operatingIncome": 24, "netIncome": 17, "weightedAverageShsOutDil": 100},
    ],
    "cash_flow": [
        {"freeCashFlow": 10, "capitalExpenditure": -5},
        {"freeCashFlow": 12, "capitalExpenditure": -6},
        {"freeCashFlow": 8, "capitalExpenditure": -4},
        {"freeCashFlow": 14, "capitalExpenditure": -7},
    ],
}

GUIDANCE = [{
    "metric": "revenue",
    "value": {"low": 950, "high": 1050, "midpoint": 1000},
    "unit": "currency",
    "period": "FY 2027",
    "source_ref": "10-K",
    "published_at": "2026-01-01",
    "guidance_kind": "range",
    "numeric_eligible": True,
}]

print("Fixture A (normal bridge):")
bridge = fb.build_financial_bridge(EC, GUIDANCE, "2026-06-16T00:00:00+00:00")
check("available", bridge["available"], True)
check("status", bridge["status"], "available")
check("rows.sorted", [row["date"] for row in bridge["rows"]], ["2027-12-31", "2028-12-31"])
row = bridge["rows"][0]
check("revenue.point", row["revenue"]["point"], 1000)
check("gross_profit.point", row["gross_profit"]["point"], 710, tol=0.1)
check("operating_income.point", row["operating_income"]["point"], 210, tol=0.1)
check("net_income_margin.point", row["net_income_from_margin"]["point"], 155, tol=0.1)
check("eps_implied_net_income.point", row["eps_implied_net_income"]["point"], 200)
check("free_cash_flow.point", row["free_cash_flow"]["point"], 110, tol=0.1)
check("capex.point", row["capex"]["point"], 55, tol=0.1)
check("guidance.range.kept", row["guidance_overlay"]["revenue"][0]["value"]["low"], 950)
check("consistency.exists", row["consistency_checks"][0]["check"], "eps_vs_margin_net_income")

print("Fixture B (derived margins preferred):")
ec_derived = {
    **EC,
    "derived": {
        "margins_8q": [
            {"gross": 0.90, "operating": 0.30, "net": 0.20},
            {"gross": 0.80, "operating": 0.20, "net": 0.10},
        ],
        "cash_flow_quality": {"fcf_margin": 0.25, "capex_intensity": 0.05},
    },
}
bridge_d = fb.build_financial_bridge(ec_derived)
check("derived.gross.median", bridge_d["historical_conversion"]["gross_margin"], 0.85)
check("derived.fcf", bridge_d["rows"][0]["free_cash_flow"]["point"], 250)
check("derived.capex", bridge_d["rows"][0]["capex"]["point"], 50)

print("Fixture C (missing core inputs degrades):")
missing = fb.build_financial_bridge({"annual_estimates": EC["annual_estimates"]})
check("missing.available", missing["available"], False)
check("missing.status", missing["status"], "insufficient_inputs")
check("missing.has_margin", "gross_margin" in missing["missing_inputs"], True)

print("Fixture D (negative FCF is explicit, not dropped):")
ec_neg = {
    **EC,
    "derived": {
        "margins_8q": [{"gross": 0.5, "operating": 0.1, "net": 0.05}],
        "cash_flow_quality": {"fcf_margin": -0.10, "capex_intensity": 0.03},
    },
}
neg = fb.build_financial_bridge(ec_neg)
check("neg.available", neg["available"], True)
check("neg.fcf", neg["rows"][0]["free_cash_flow"]["point"], -100)
check("neg.check", neg["rows"][0]["consistency_checks"][1]["status"], "negative_fcf")

print("Fixture E (share count fallback):")
ec_ev = {**EC, "quarterly_pnl": [{"revenue": 100, "grossProfit": 50, "operatingIncome": 20, "netIncome": 10}],
         "enterprise_value": {"numberOfShares": 80}}
ev = fb.build_financial_bridge(ec_ev)
check("ev.share_source", ev["historical_conversion"]["diluted_share_count_source"], "enterprise_value.numberOfShares")
check("ev.eps_income", ev["rows"][0]["eps_implied_net_income"]["point"], 160)

print("Fixture F (no annual estimate rows):")
none = fb.build_financial_bridge({"quarterly_pnl": EC["quarterly_pnl"], "cash_flow": EC["cash_flow"]})
check("none.available", none["available"], False)
check("none.warning", "no_forward_revenue_rows" in none["warnings"], True)

print("Fixture G (EXP-R2 held-constant disclosure + terminal sensitivity):")
g = fb.build_financial_bridge(EC)
check("g.assumption_basis", g["assumption_basis"], "historical_ratios_held_constant")
drivers = {a["driver"] for a in g["held_constant_assumptions"]}
check("g.discloses net_margin held", "net_margin" in drivers, True)
check("g.discloses share count held", "diluted_share_count" in drivers, True)
ts = g["terminal_sensitivity"]
check("g.sensitivity labelled not-a-scenario", ts["basis"], "illustrative_elasticity_not_a_scenario")
check("g.sensitivity horizon = farthest row", ts["horizon_date"], "2028-12-31")
# net margin 0.155 (median of 0.14/0.15/0.16/0.17), revenue 2000, shares 100
check("g.margin held eps = 2000*0.155/100", ts["net_margin_sensitivity"]["held_constant"]["eps_implied"], 3.10, tol=0.001)
check("g.margin -20% eps = 2000*0.124/100", ts["net_margin_sensitivity"]["minus_20pct_relative"]["eps_implied"], 2.48, tol=0.001)
check("g.share +10% dilution eps = 310/110", ts["share_count_sensitivity"]["plus_10pct_dilution"]["eps_implied"], 2.8182, tol=0.001)
check("g.share -10% buyback shares = 90", ts["share_count_sensitivity"]["minus_10pct_buyback"]["diluted_share_count"], 90)

print("Fixture H (sensitivity degrades when net margin missing):")
h = fb.build_financial_bridge({"annual_estimates": EC["annual_estimates"]})
check("h.terminal_sensitivity None", h["terminal_sensitivity"], None)

# ── V4.40.0 per-FY analyst coverage threaded into each row ──────────────────────
print("Fixture I (per-FY coverage):")
cov_rows = {r["date"]: r for r in g["rows"]}
check("i.2028 coverage rev", cov_rows["2028-12-31"]["coverage"]["num_analysts_revenue"], 12)
check("i.2028 coverage eps", cov_rows["2028-12-31"]["coverage"]["num_analysts_eps"], 8)
check("i.2027 coverage absent -> None", cov_rows["2027-12-31"]["coverage"]["num_analysts_revenue"], None)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

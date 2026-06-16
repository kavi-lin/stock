#!/usr/bin/env python3
"""Golden fixtures for the historical multiple-regime anchor (EXP-R1).

No network: a stub fetch_fn injects FMP-shaped `ratios` rows.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_multiple_anchor as anchor  # noqa: E402

PASS = 0
FAIL = 0


def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}")


def rows(pe_series, ps_series, pfcf_series):
    out = []
    for i, (pe, ps, pfcf) in enumerate(zip(pe_series, ps_series, pfcf_series)):
        out.append({
            "date": f"202{i}-03-31",
            "priceToEarningsRatio": pe,
            "priceToSalesRatio": ps,
            "priceToFreeCashFlowRatio": pfcf,
        })
    return out


# ── stable regime: tight dispersion -> usable ──────────────────────────────────
stable = rows([20, 22, 24, 21, 23], [6, 7, 6.5, 7.2, 6.8], [30, 32, 31, 29, 33])
a = anchor.build_multiple_anchor("TEST", fetch_fn=lambda t: stable)
check("stable: available", a["available"] is True)
check("stable: price-independent flag", a["anchor_independent_of_current_price"] is True)
check("stable: pe usable", a["by_metric"]["pe"]["usable"] is True)
check("stable: pe p50 ~22", abs(a["by_metric"]["pe"]["p50"] - 22) <= 1.5)
check("stable: ps usable", a["by_metric"]["ps"]["usable"] is True)
check("stable: history points 5", a["history_points"] == 5)
check("stable: source labelled", a["source"] == "fmp_ratios_annual_history")

# ── noisy regime: p75/p25 > MAX_DISPERSION -> rejected ─────────────────────────
noisy = rows([10, 200, 15, 400, 12], [6, 7, 6.5, 7.2, 6.8], [30, 31, 32, 29, 33])
b = anchor.build_multiple_anchor("TEST", fetch_fn=lambda t: noisy)
check("noisy: pe rejected (dispersion)", b["by_metric"]["pe"]["usable"] is False)
check("noisy: pe reason dispersion", b["by_metric"]["pe"]["reason"] == "dispersion_too_high")
check("noisy: ps still usable", b["by_metric"]["ps"]["usable"] is True)
check("noisy: overall available via ps", b["available"] is True)

# ── insufficient history: < MIN_POINTS positive years ──────────────────────────
thin = [{"date": "2025-03-31", "priceToEarningsRatio": 20, "priceToSalesRatio": 6, "priceToFreeCashFlowRatio": 30}]
c = anchor.build_multiple_anchor("TEST", fetch_fn=lambda t: thin)
check("thin: pe not usable", c["by_metric"]["pe"]["usable"] is False)
check("thin: pe reason insufficient", c["by_metric"]["pe"]["reason"] == "insufficient_history")
check("thin: overall unavailable", c["available"] is False)
check("thin: warns no_usable_regime", "no_usable_historical_multiple_regime" in c["warnings"])

# ── negative / zero ratios filtered (loss years) ───────────────────────────────
neg = rows([-50, 20, 22, 24, 21], [6, 7, 6.5, 7.2, 6.8], [0, 30, 31, 29, 33])
d = anchor.build_multiple_anchor("TEST", fetch_fn=lambda t: neg)
check("neg: pe drops negative year (n=4)", d["by_metric"]["pe"]["n"] == 4)
check("neg: pfcf drops zero year (n=4)", d["by_metric"]["pfcf"]["n"] == 4)

# ── no_fetch + empty fetch degrade cleanly ─────────────────────────────────────
nf = anchor.build_multiple_anchor("TEST", no_fetch=True)
check("no_fetch: unavailable", nf["available"] is False)
check("no_fetch: warns skipped", "no_fetch_historical_multiple_skipped" in nf["warnings"])
empty = anchor.build_multiple_anchor("TEST", fetch_fn=lambda t: None)
check("empty fetch: unavailable", empty["available"] is False)
check("empty fetch: warns unavailable", "historical_ratios_unavailable" in empty["warnings"])

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

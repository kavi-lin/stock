#!/usr/bin/env python3
"""Golden fixtures for the margin-normalization path (EXP-3.4b)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_margin_normalization as mn  # noqa: E402

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


def bridge(net_margin, shares, rev_low, rev_base, rev_high):
    return {
        "historical_conversion": {"net_margin": net_margin, "diluted_share_count": shares},
        "rows": [{"date": "2031-01-25", "revenue": {"low": rev_low, "point": rev_base, "high": rev_high}}],
    }


SHARES = 24.4e9
NVDA = bridge(0.60, SHARES, 461e9, 585e9, 695e9)

# ── supernormal margin -> normalization applies, retention path ────────────────
r = mn.build_margin_normalization(NVDA, own_hist_net_margin=0.56)
check("applied", r["applied"], True)
check("held margin echoed", r["held_net_margin"], 0.60, tol=0.001)
check("bear margin = 0.62x held", r["scenario_net_margins"]["bear"], 0.372, tol=0.002)
check("base margin = 0.80x held", r["scenario_net_margins"]["base"], 0.48, tol=0.003)
check("bull margin = held (monopoly persists)", r["scenario_net_margins"]["bull"], 0.60, tol=0.001)
# base eps = rev_base * base_margin / shares = 585e9 * 0.48 / 24.4e9
check("normalized base EPS", r["normalized_eps"]["point"], 585e9 * 0.48 / SHARES, tol=0.05)
check("normalized bear EPS uses rev_low", r["normalized_eps"]["low"], 461e9 * 0.372 / SHARES, tol=0.05)
check("normalized bull EPS uses rev_high", r["normalized_eps"]["high"], 695e9 * 0.60 / SHARES, tol=0.05)
check("held-margin base eps higher than normalized", r["held_margin_eps_base"] > r["normalized_eps"]["point"], True)
check("method is retention path not sector mean", r["method"], "durable_platform_retention_path")

# ── normal margin -> NOT normalized (no mechanical reversion of healthy co) ─────
normal = mn.build_margin_normalization(bridge(0.25, SHARES, 100e9, 130e9, 160e9), own_hist_net_margin=0.24)
check("normal margin not applied", normal["applied"], False)
check("normal reason", normal["reason"], "margin_not_supernormal_no_normalization")

# ── floor protects a structurally high-margin franchise (own history high) ─────
durable = mn.build_margin_normalization(bridge(0.60, SHARES, 461e9, 585e9, 695e9), own_hist_net_margin=0.70)
# floor = 0.70 * 0.85 = 0.595; base retention would give 0.48 -> lifted to floor 0.595
check("floor set from own history", durable["floor_net_margin"], 0.595, tol=0.002)
check("base lifted to floor (not over-normalized)", durable["scenario_net_margins"]["base"], 0.595, tol=0.002)

# ── no own history -> no floor, plain retention ────────────────────────────────
no_hist = mn.build_margin_normalization(NVDA, own_hist_net_margin=None)
check("no floor when no history", no_hist["floor_net_margin"], None)
check("base = plain 0.80x held", no_hist["scenario_net_margins"]["base"], 0.48, tol=0.003)

# ── insufficient bridge -> not applied ─────────────────────────────────────────
bad = mn.build_margin_normalization({"historical_conversion": {}, "rows": []})
check("insufficient not applied", bad["applied"], False)
check("insufficient reason", bad["reason"], "insufficient_bridge_inputs")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

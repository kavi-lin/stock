#!/usr/bin/env python3
"""Numeric-safety golden fixtures (EXP-R4).

Guards against division-by-zero, negative denominators, and NaN/Inf leaking into
JSON. Every shadow output must survive json.dumps(allow_nan=False) — invalid JSON
(Infinity/NaN tokens) would crash downstream parsers.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_gap as gap  # noqa: E402
import forward_expectations_price_range as pr  # noqa: E402

PASS = 0
FAIL = 0


def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}")


def serializable(obj):
    """True iff obj has no NaN/Inf (the allow_nan=False contract)."""
    try:
        json.dumps(obj, allow_nan=False)
        return True
    except (ValueError, TypeError):
        return False


# ── gap._compare: zero / None denominators must not raise or emit Inf ──────────
zero_den = gap._compare("revenue_cagr", "consensus", 0.30, "base_rate", 0.0)
check("compare: zero right_value -> ratio None", zero_den is not None and zero_den["ratio"] is None)
check("compare: zero right_value still serializable", serializable(zero_den))

none_den = gap._compare("revenue_cagr", "consensus", 0.30, "base_rate", None)
check("compare: None right_value -> whole row None", none_den is None)

neg_den = gap._compare("revenue_cagr", "independent", 0.10, "consensus", -0.20)
check("compare: negative denominator does not crash + finite ratio", neg_den is not None and math.isfinite(neg_den["ratio"]))
check("compare: negative denominator serializable", serializable(neg_den))


# ── price range: pathological bridge rows must degrade, never crash or emit Inf ─
def bridge(eps_point, eps_low=None, eps_high=None, rev_point=900):
    return {
        "available": True,
        "historical_conversion": {"diluted_share_count": 100},
        "rows": [{
            "date": "2027-12-31",
            "revenue": {"point": rev_point, "low": rev_point, "high": rev_point},
            "eps_consensus": {"point": eps_point, "low": eps_low if eps_low is not None else eps_point,
                              "high": eps_high if eps_high is not None else eps_point},
            "free_cash_flow": {"point": None, "low": None, "high": None},
        }],
    }


# zero forward EPS -> derived P/E band would divide by zero; must fall through, not crash
zero_eps = pr.build_future_price_range("ZERO", 100.0, bridge(0.0), {}, {})
check("price_range: zero EPS does not raise", isinstance(zero_eps, dict))
check("price_range: zero EPS no Inf in output", serializable(zero_eps))
check("price_range: zero EPS falls through to revenue path or unavailable",
      zero_eps.get("method") in ("revenue_per_share_x_ps", None))

# negative forward EPS -> _pos() rejects it as a base; must not produce a bogus multiple
neg_eps = pr.build_future_price_range("NEG", 100.0, bridge(-2.0), {}, {})
check("price_range: negative EPS no Inf/NaN", serializable(neg_eps))

# zero current price -> upside divide-by-zero guard
zero_px = pr.build_future_price_range("ZPX", 0.0, bridge(4.0), {}, {})
check("price_range: zero current price flagged, not crash",
      zero_px.get("available") is False and "current_price_missing" in zero_px.get("warnings", []))
check("price_range: zero current price serializable", serializable(zero_px))

# valid case stays serializable under allow_nan=False
valid = pr.build_future_price_range("OK", 80.0, bridge(4.0, 3.0, 5.0), {}, {})
check("price_range: valid case available", valid.get("available") is True)
check("price_range: valid case serializable", serializable(valid))


# ── sanity: the guard is real — a NaN payload must be rejected ─────────────────
check("guard: NaN payload rejected by allow_nan=False", not serializable({"x": float("nan")}))
check("guard: Inf payload rejected by allow_nan=False", not serializable({"x": float("inf")}))


print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

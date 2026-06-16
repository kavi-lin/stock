#!/usr/bin/env python3
"""Golden fixtures for Forward Expectations future price range mapper."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_price_range as pr  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want, tol=None):
    global PASS, FAIL
    ok = (abs(got - want) <= tol) if (tol is not None and got is not None) else (got == want)
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}" + (f" (±{tol})" if tol else ""))


BRIDGE = {
    "available": True,
    "historical_conversion": {"diluted_share_count": 100},
    "rows": [
        {
            "date": "2027-12-31",
            "revenue": {"point": 900, "low": 800, "high": 1000},
            "eps_consensus": {"point": 4.0, "low": 3.0, "high": 5.0},
            "free_cash_flow": {"point": 120, "low": 90, "high": 150},
        },
        {
            "date": "2028-12-31",
            "revenue": {"point": 1200, "low": 1000, "high": 1400},
            "eps_consensus": {"point": 5.0, "low": 4.0, "high": 6.0},
            "free_cash_flow": {"point": 180, "low": 140, "high": 220},
        },
    ],
}

print("Fixture A (EPS x explicit PE range):")
eps = pr.build_future_price_range(
    "TEST", 100, BRIDGE, {}, {"pe_range": {"p25": 15, "p50": 20, "p75": 25, "source": "fixture_pe"}}
)
check("eps.available", eps["available"], True)
check("eps.horizon", eps["horizon_date"], "2028-12-31")
check("eps.method", eps["method"], "eps_x_pe")
check("eps.bear", eps["cases"]["bear"]["target_price"], 60.0)
check("eps.base", eps["cases"]["base"]["target_price"], 100.0)
check("eps.bull", eps["cases"]["bull"]["target_price"], 150.0)
check("eps.upside", eps["cases"]["bull"]["upside_pct"], 50.0)
check("eps.shadow", eps["changes_live_decision"], False)

print("Fixture B (EPS path derives current market multiple band):")
derived = pr.build_future_price_range("TEST", 100, BRIDGE, {}, {})
check("derived.available", derived["available"], True)
check("derived.multiple_method", derived["multiple_range"]["method"], "current_market_multiple_band")
check("derived.warning", "derived_current_market_multiple_used" in derived["warnings"], True)

print("Fixture C (Revenue x P/S fallback when EPS unavailable):")
bridge_no_eps = {**BRIDGE, "rows": [{**BRIDGE["rows"][-1], "eps_consensus": {"point": None}}]}
rev = pr.build_future_price_range(
    "TEST", 100, bridge_no_eps, {"snapshot": {"marketCap": 10000}},
    {"ps_range": {"p25": 6, "p50": 8, "p75": 10}},
)
check("rev.method", rev["method"], "revenue_per_share_x_ps")
check("rev.base", rev["cases"]["base"]["target_price"], 96.0)

print("Fixture D (FCF x P/FCF fallback when EPS/revenue unavailable):")
bridge_fcf = {
    **BRIDGE,
    "rows": [{
        "date": "2028-12-31",
        "revenue": {"point": None},
        "eps_consensus": {"point": None},
        "free_cash_flow": {"point": 180, "low": 140, "high": 220},
    }],
}
fcf = pr.build_future_price_range("TEST", 100, bridge_fcf, {}, {"pfcf_range": {"p25": 30, "p50": 40, "p75": 50}})
check("fcf.method", fcf["method"], "fcf_per_share_x_pfcf")
check("fcf.base", fcf["cases"]["base"]["target_price"], 72.0)

print("Fixture F (historical anchor breaks the tautology — base != current):")
# anchor with usable PE regime p50=18 (independent of the 100 current price)
ANCHOR = {"by_metric": {"pe": {"usable": True, "p25": 15, "p50": 18, "p75": 22, "n": 5,
                               "dispersion_ratio": 1.47, "source": "fmp_ratios_annual_history:priceToEarningsRatio"}}}
fcast = pr.build_future_price_range("TEST", 100, BRIDGE, {}, {}, ANCHOR)
check("anchor.status available (forecast)", fcast["status"], "available")
check("anchor.quality historical", fcast["multiple_quality"], "historical")
check("anchor.multiple_method", fcast["multiple_range"]["method"], "historical_multiple_regime")
check("anchor.base = fwd_eps5 * p50 = 5*18 = 90 (NOT current 100)", fcast["cases"]["base"]["target_price"], 90.0)
check("anchor.no derived warning", "derived_current_market_multiple_used" in fcast["warnings"], False)

print("Fixture G (unusable anchor -> honest advisory band, not silent forecast):")
BAD_ANCHOR = {"by_metric": {"pe": {"usable": False, "reason": "dispersion_too_high"}},
              "warnings": ["no_usable_historical_multiple_regime"]}
adv = pr.build_future_price_range("TEST", 100, BRIDGE, {}, {}, BAD_ANCHOR)
check("advisory.status advisory_band_only", adv["status"], "advisory_band_only")
check("advisory.quality derived", adv["multiple_quality"], "derived")
check("advisory.base == current (tautology, labelled)", adv["cases"]["base"]["target_price"], 100.0)
check("advisory.not_forecast warning", "current_price_volatility_band_not_forecast" in adv["warnings"], True)
check("advisory.still available range", adv["available"], True)

print("Fixture H (anchor present but explicit input still wins):")
exp_win = pr.build_future_price_range(
    "TEST", 100, BRIDGE, {}, {"pe_range": {"p25": 15, "p50": 20, "p75": 25}}, ANCHOR
)
check("explicit beats anchor (quality explicit)", exp_win["multiple_quality"], "explicit")
check("explicit base = 5*20 = 100", exp_win["cases"]["base"]["target_price"], 100.0)

print("Fixture E (insufficient inputs degrade):")
empty = pr.build_future_price_range("TEST", 100, {"rows": []}, {}, {})
check("empty.available", empty["available"], False)
check("empty.warning", empty["warnings"][0], "forward_financial_bridge_rows_missing")
no_price = pr.build_future_price_range("TEST", None, BRIDGE, {}, {})
check("no_price.available", no_price["available"], False)
check("no_price.warning", no_price["warnings"][0], "current_price_missing")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

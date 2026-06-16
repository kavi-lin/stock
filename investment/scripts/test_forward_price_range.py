#!/usr/bin/env python3
"""Golden fixtures for ticker-facing forward_price_range.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_price_range as fpr  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}")


SNAPSHOT = {
    "ticker": "ARM",
    "current_price": 237.3,
    "future_price_range": {
        "available": True,
        "status": "available",
        "ticker": "ARM",
        "horizon_date": "2030-03-31",
        "method": "eps_x_pe",
        "range": {"low": 197.52, "base": 237.3, "high": 280.14},
        "cases": {
            "bear": {"upside_pct": -16.8},
            "base": {"upside_pct": 0.0},
            "bull": {"upside_pct": 18.1},
        },
        "warnings": ["derived_current_market_multiple_used"],
        "policy": "shadow-only",
    },
}

print("Fixture A (extract available range):")
summary = fpr.extract_range(SNAPSHOT)
check("summary.available", summary["available"], True)
check("summary.ticker", summary["ticker"], "ARM")
check("summary.current", summary["current_price"], 237.3)
check("summary.bear", summary["range"]["bear"], 197.52)
check("summary.base_upside", summary["upside_pct"]["base"], 0.0)
check("summary.warning", summary["warnings"][0], "derived_current_market_multiple_used")

print("Fixture B (format text):")
text = fpr.format_text(summary)
check("text.heading", "ARM Future Price Range" in text, True)
check("text.base", "- Base: $237.3 (+0.0%)" in text, True)
check("text.policy", "shadow-only" in text, True)

print("Fixture C (missing range block degrades):")
missing = fpr.extract_range({"ticker": "NOPE"})
check("missing.available", missing["available"], False)
check("missing.status", missing["status"], "missing_future_price_range")
check("missing.warning", missing["warnings"][0], "forward_expectations_output_missing_future_price_range")
missing_text = fpr.format_text(missing)
check("missing_text", "NOPE future price range unavailable" in missing_text, True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

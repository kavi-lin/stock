#!/usr/bin/env python3
"""Golden fixtures for analyst estimate / rating revision snapshots."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_revisions as rv  # noqa: E402

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


EARNINGS = {
    "annual_estimates": [
        {
            "date": "2028-12-31",
            "revenue_avg": 200,
            "revenue_low": 180,
            "revenue_high": 220,
            "eps_avg": 4,
            "eps_low": 3,
            "eps_high": 5,
            "num_analysts_revenue": 12,
            "num_analysts_eps": 10,
        },
        {
            "date": "2027-12-31",
            "revenue_avg": 100,
            "revenue_low": 95,
            "revenue_high": 105,
            "eps_avg": 2,
            "eps_low": 1.8,
            "eps_high": 2.2,
            "num_analysts_revenue": 15,
            "num_analysts_eps": 14,
        },
    ],
    "analyst_grades": [
        {
            "date": "2026-01-01",
            "analystRatingsStrongBuy": 2,
            "analystRatingsBuy": 4,
            "analystRatingsHold": 4,
            "analystRatingsSell": 1,
            "analystRatingsStrongSell": 1,
        },
        {
            "date": "2026-05-01",
            "analystRatingsStrongBuy": 4,
            "analystRatingsBuy": 6,
            "analystRatingsHold": 2,
            "analystRatingsSell": 0,
            "analystRatingsStrongSell": 0,
        },
    ],
}

print("Fixture A (estimate snapshot sorts dates and computes dispersion):")
snap = rv.build_revision_snapshot("TEST", EARNINGS, "2026-06-16T00:00:00+00:00")
check("available", snap["available"], True)
check("window_from", snap["annual_estimate_snapshot"]["window_from"], "2027-12-31")
check("window_to", snap["annual_estimate_snapshot"]["window_to"], "2028-12-31")
entries = snap["annual_estimate_snapshot"]["entries"]
check("near.revenue_spread", entries[0]["revenue_spread_pct"], 10.0)
check("far.eps_spread", entries[1]["eps_spread_pct"], 50.0)
check("latest_year.near", snap["latest_year"]["date"], "2027-12-31")

print("Fixture B (rating momentum direction up):")
rating = snap["rating_momentum"]
check("rating.available", rating["available"], True)
check("rating.direction", rating["direction"], "UP")
check("rating.delta", rating["delta"], 0.5, tol=1e-9)

print("Fixture C (rating momentum flat):")
flat = rv.rating_momentum({
    "analyst_grades": [
        {"date": "2026-01-01", "analystRatingsStrongBuy": 1, "analystRatingsBuy": 1,
         "analystRatingsHold": 2, "analystRatingsSell": 0, "analystRatingsStrongSell": 0},
        {"date": "2026-02-01", "analystRatingsStrongBuy": 1, "analystRatingsBuy": 1,
         "analystRatingsHold": 2, "analystRatingsSell": 0, "analystRatingsStrongSell": 0},
    ],
})
check("flat.direction", flat["direction"], "FLAT")

print("Fixture D (sparse data degrades cleanly):")
empty = rv.build_revision_snapshot("EMPTY", {}, None)
check("empty.available", empty["available"], False)
check("empty.entries", empty["annual_estimate_snapshot"]["entries"], [])
check("empty.rating_reason", empty["rating_momentum"]["reason"], "analyst_grades_missing_or_sparse")

print("Fixture E (delta truthfully unavailable without historical estimate versions):")
check("delta.available", snap["estimate_revision_delta_available"], False)
check("delta.reason", "latest forward curve only" in snap["estimate_revision_delta_reason"], True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

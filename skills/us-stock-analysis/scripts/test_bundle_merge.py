#!/usr/bin/env python3
"""test_bundle_merge.py — locks the EARNINGS_ANALYST_BUNDLE → output-block merge.

Two failure modes this guards, both silent by nature:

1. Block-name drift. The merge used to resolve targets via `locals().get(name)`, so a
   bundle key only landed if it happened to equal the local variable name. `margins_cash`
   (local `margins`) and `earnings_calendar` (local `earnings`) never matched — the
   overrides were computed and thrown away, and FMP-canonical TTM margins lost to
   yfinance on every run. Nothing failed; the numbers were just quietly wrong.

2. Growth falling back to yfinance. `info.revenueGrowth` lags the release: on
   2026-08-07 AAOI read +51.4% (Q1) while FMP already had Q2 at +86.4%. Revenue YoY
   must come from the same bundle quarter as the rest of the block.

Run: python3 skills/us-stock-analysis/scripts/test_bundle_merge.py   (rc=0 required)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze  # noqa: E402

FAILURES = []


def check(label, got, want):
    ok = got == want
    if not ok:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")
    print(f"  {'✓' if ok else '✗'} {label}")


# A bundle shaped like skills/earnings-analyst/cache/<T>_<DATE>.json, values chosen so
# every assertion below is unambiguous about which source won.
BUNDLE = {
    "ticker": "AAOI",
    "as_of_date": "2026-08-07",
    "last_earnings_date": "2026-06-30",
    "next_earnings_est": "2026-09-29",
    "quarterly_pnl": [{"date": "2026-06-30", "revenue": 191_900_000}],
    "cash_flow": [{"date": "2026-06-30"}],
    "balance_sheet": [{"date": "2026-06-30"}],
    "enterprise_value": {"enterpriseValue": 9_919_047_517, "numberOfShares": 80_242_767},
    "ttm_metrics": {
        "from_ratios_ttm": {
            "grossProfitMarginTTM": 0.2892,
            "operatingProfitMarginTTM": -0.1131,
            "netProfitMarginTTM": -0.0957,
            "priceToEarningsRatioTTM": None,
            "debtToEquityRatioTTM": 0.16,
        },
        "from_key_metrics_ttm": {},
    },
    "derived": {"yoy_growth": {"revenue_yoy": 0.8642, "revenue_qoq": 0.2698}},
}


def main():
    print("── _derive_from_bundle ──")
    d = analyze._derive_from_bundle(BUNDLE)

    check("emits a growth block", "growth" in d, True)
    check("revenue_yoy_pct is bundle-sourced, in percent",
          d["growth"]["revenue_yoy_pct"], 86.42)
    check("margins_cash block present", "margins_cash" in d, True)
    check("gross margin from FMP ratios-ttm",
          d["margins_cash"]["gross_margin_pct"], 28.92)
    check("earnings_calendar block present", "earnings_calendar" in d, True)
    check("next earnings from bundle",
          d["earnings_calendar"]["next_earnings_date"], "2026-09-29")

    # A bundle with no derived block must not fabricate a growth number.
    thin = {k: v for k, v in BUNDLE.items() if k != "derived"}
    check("missing derived → revenue_yoy_pct None",
          analyze._derive_from_bundle(thin)["growth"]["revenue_yoy_pct"], None)
    check("empty bundle → {}", analyze._derive_from_bundle({}), {})

    print("── merge registry covers every emitted block ──")
    # The registry lives inside analyze(); mirror its keys here so a rename on either
    # side trips this test rather than silently dropping a block at runtime.
    registry_keys = {"price", "valuation", "growth", "margins_cash",
                     "balance_sheet", "earnings_calendar", "analyst"}
    emitted = {k for k in d if not k.startswith("_")}
    orphans = emitted - registry_keys
    check("no emitted block lacks a merge target", orphans, set())

    # Comments are stripped first: the prose below explains the old locals() form, and
    # matching against it would make this assertion pass on the very bug it guards.
    raw = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyze.py")).read()
    src = "\n".join(l for l in raw.splitlines() if not l.lstrip().startswith("#"))
    check("merge no longer resolves targets via locals()",
          "locals().get(block_name)" in src, False)
    for key in sorted(emitted):
        check(f"registry declares {key!r}", f'"{key}":' in src, True)

    print()
    if FAILURES:
        print(f"✗ {len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(f"   - {f}")
        return 1
    print("✓ bundle→block merge contract holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())

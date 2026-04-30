"""
earnings-analyst — JSON schema validator (V1.0)

Verifies that a cache file (post-fetch + post-analyze) has all required
top-level keys, derived blocks, and scoring fields per schema.md.

Usage:
    python3 skills/earnings-analyst/scripts/validate.py NVDA
        rc=0  → pass
        rc=1  → schema drift / missing fields — see stderr
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CACHE_DIR = os.path.join(BASE_DIR, "skills", "earnings-analyst", "cache")
EXPECTED_VERSION = "V1.0"

TOP_REQUIRED = [
    "ticker", "as_of_date", "last_earnings_date", "schema_version", "data_source",
    "snapshot", "quarterly_pnl", "balance_sheet", "cash_flow",
    "ttm_metrics", "annual_growth", "valuation", "analyst_grades",
    # post-analyze
    "derived", "quality_flags", "composite_score", "verdict", "score_components",
]

SNAPSHOT_REQUIRED = ["companyName", "sector", "industry", "price", "marketCap"]

DERIVED_REQUIRED = ["margins_8q", "yoy_growth", "balance_health", "cash_flow_quality"]

SCORE_COMPONENTS_REQUIRED = ["quality", "growth", "valuation", "analyst"]

VALID_VERDICTS = {"STRONG", "SOLID", "MIXED", "WEAK", "DETERIORATING"}


def find_cache(ticker: str) -> str | None:
    files = sorted(glob.glob(os.path.join(CACHE_DIR, f"{ticker}_*.json")))
    return files[-1] if files else None


def fail(errors: list):
    print(f"[validate] ✗ schema drift (expected {EXPECTED_VERSION}):", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker", nargs="?")
    ap.add_argument("--json", help="explicit cache path")
    args = ap.parse_args()

    if args.json:
        path = args.json
    else:
        if not args.ticker:
            sys.exit("Usage: validate.py <TICKER>  (or --json <path>)")
        path = find_cache(args.ticker.upper())
        if not path:
            fail([f"no cache for {args.ticker} under {CACHE_DIR}"])

    with open(path) as f:
        d = json.load(f)

    errors = []

    # 1. Top-level keys
    for k in TOP_REQUIRED:
        if k not in d:
            errors.append(f"missing top-level key: {k}")

    # 2. Schema version
    if d.get("schema_version") != EXPECTED_VERSION:
        errors.append(f"schema_version = {d.get('schema_version')!r}, expected {EXPECTED_VERSION!r}")

    # 3. snapshot
    snap = d.get("snapshot") or {}
    for k in SNAPSHOT_REQUIRED:
        if k not in snap:
            errors.append(f"snapshot missing {k}")

    # 4. quarterly_pnl shape
    qp = d.get("quarterly_pnl") or []
    if not isinstance(qp, list) or len(qp) < 4:
        errors.append(f"quarterly_pnl must have ≥ 4 entries (got {len(qp) if isinstance(qp, list) else 0})")
    else:
        for i, r in enumerate(qp[:4]):
            for k in ("date", "revenue", "netIncome"):
                if k not in r:
                    errors.append(f"quarterly_pnl[{i}] missing {k}")

    # 5. balance_sheet / cash_flow non-empty
    if not (d.get("balance_sheet") or []):
        errors.append("balance_sheet empty")
    if not (d.get("cash_flow") or []):
        errors.append("cash_flow empty")

    # 6. derived block
    derived = d.get("derived") or {}
    for k in DERIVED_REQUIRED:
        if k not in derived:
            errors.append(f"derived missing {k}")

    # 7. composite_score range + verdict
    cs = d.get("composite_score")
    if not isinstance(cs, int) or not (0 <= cs <= 100):
        errors.append(f"composite_score must be int in [0, 100] (got {cs!r})")
    verdict = d.get("verdict")
    if verdict not in VALID_VERDICTS:
        errors.append(f"verdict={verdict!r} must be one of {sorted(VALID_VERDICTS)}")

    # 8. score_components
    sc = d.get("score_components") or {}
    for k in SCORE_COMPONENTS_REQUIRED:
        if k not in sc:
            errors.append(f"score_components missing {k}")
    # Sub-component bounds
    bounds = {"quality": 30, "growth": 30, "valuation": 25, "analyst": 15}
    for k, mx in bounds.items():
        v = sc.get(k)
        if v is not None and not (0 <= v <= mx):
            errors.append(f"score_components.{k}={v} out of [0, {mx}]")

    # 9. quality_flags is list
    qf = d.get("quality_flags")
    if not isinstance(qf, list):
        errors.append(f"quality_flags must be list (got {type(qf).__name__})")

    if errors:
        fail(errors)

    flags_str = ",".join(qf) if qf else "clean"
    print(f"[validate] ✓ {EXPECTED_VERSION} compliant — {d['ticker']} "
          f"composite={cs} verdict={verdict} flags={flags_str}")
    return 0


if __name__ == "__main__":
    main()

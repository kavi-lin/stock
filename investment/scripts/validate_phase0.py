#!/usr/bin/env python3
"""
Validate the most recent `invest_logs/YYYY-MM-DD_phase0_TICKER.json` for
V4.9 FRED compliance — checks that LLM actually fetched FRED Layer E and
recorded the snapshot, not just skipped.

Invocation (from investment protocol Phase 0 末尾):
    python3 investment/scripts/validate_phase0.py [--ticker TICKER]
        rc=0 → pass
        rc=1 → schema drift / FRED missing — see stderr

What this catches (production failure modes):
  1. fred_available missing entirely (LLM forgot V4.9 L4)
  2. fred_available=true but fred_snapshot null/missing
  3. fred_snapshot present but missing required fields (regime_label / signals)
  4. macro_multiplier_rationale missing (audit trail required by V4.9)
  5. fred_available=true but macro_multiplier_rationale doesn't reference FRED
"""
import argparse
import glob
import json
import os
import sys

ROOT     = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS_DIR = os.path.join(ROOT, "investment/invest_logs")

REQUIRED_TOP = [
    "fred_available",
    "phase3_macro_multiplier",
    "macro_multiplier_rationale",
]

FRED_SNAPSHOT_REQUIRED = [
    "regime_label", "yield_curve_inverted", "credit_stress_elevated",
    "financial_stress_above_avg", "fed_rate_direction",
]

VALID_REGIMES = {
    "Goldilocks", "Soft Landing", "Reflation", "Benign Easing", "Overheating",
    "Late Cycle Tightening", "Stagflation", "Recession Easing", "Recession Risk",
    "Transitional",
}


def find_latest(ticker=None):
    if ticker:
        pattern = f"*_phase0_{ticker.lower()}.json"
    else:
        pattern = "*_phase0_*.json"
    files = sorted(glob.glob(os.path.join(LOGS_DIR, pattern)))
    return files[-1] if files else None


def fail(path, errors):
    print(f"[validate_phase0] ✗ {os.path.relpath(path, ROOT)} fails V4.9 FRED gate:", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    print(
        "\nFix: re-run protocol Phase 0 L4 (`python3 skills/fred-macro/scripts/fetch.py "
        "--json-only`), populate fred_snapshot + macro_multiplier_rationale per V4.9 spec, "
        "then re-run this validator.",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", help="restrict to a specific ticker's phase0 file")
    args = ap.parse_args()

    path = find_latest(args.ticker)
    if not path:
        print(
            f"[validate_phase0] ✗ no *_phase0_*.json found under {LOGS_DIR}"
            + (f" for ticker={args.ticker}" if args.ticker else ""),
            file=sys.stderr,
        )
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    errors = []

    # 1. Top-level required keys
    for k in REQUIRED_TOP:
        if k not in data:
            errors.append(f"missing top-level key: {k}")

    fred_avail = data.get("fred_available")
    if fred_avail is True:
        # 2. fred_snapshot must exist and be a dict
        fs = data.get("fred_snapshot")
        if not isinstance(fs, dict):
            errors.append("fred_available=true but fred_snapshot missing or not a dict")
        else:
            # 3. Required fields inside fred_snapshot
            for k in FRED_SNAPSHOT_REQUIRED:
                if k not in fs:
                    errors.append(f"fred_snapshot missing field: {k}")
            # regime_label sanity
            rl = fs.get("regime_label")
            if rl is not None and rl not in VALID_REGIMES:
                errors.append(
                    f"fred_snapshot.regime_label={rl!r} not in {sorted(VALID_REGIMES)}"
                )
        # 4. Audit trail in rationale
        rationale = (data.get("macro_multiplier_rationale") or "").lower()
        if rationale and "fred" not in rationale and "yield" not in rationale \
                    and "real_rate" not in rationale and "nfci" not in rationale \
                    and "credit" not in rationale and "regime" not in rationale:
            errors.append(
                "macro_multiplier_rationale doesn't reference FRED data "
                "(must mention one of: FRED / yield / real_rate / nfci / credit / regime)"
            )
    elif fred_avail is False:
        # acceptable — degraded mode. Rationale should say so explicitly.
        rationale = (data.get("macro_multiplier_rationale") or "").lower()
        if rationale and "fred" not in rationale and "unavailable" not in rationale:
            errors.append(
                "fred_available=false but macro_multiplier_rationale doesn't note "
                "FRED degraded fallback (should mention 'FRED unavailable' or similar)"
            )
    elif fred_avail is None:
        errors.append("fred_available is missing — V4.9 L4 was skipped (MUST-run)")
    else:
        errors.append(f"fred_available must be true/false bool (got {fred_avail!r})")

    if errors:
        fail(path, errors)

    fs = data.get("fred_snapshot") or {}
    summary = (
        f"regime={fs.get('regime_label', 'n/a')}"
        f" · multiplier={data.get('phase3_macro_multiplier', '?')}"
        f" · fred_available={fred_avail}"
    )
    print(
        f"[validate_phase0] ✓ {os.path.relpath(path, ROOT)} V4.9 compliant — {summary}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()

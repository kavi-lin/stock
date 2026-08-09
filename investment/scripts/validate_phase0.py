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
  6. (V4.116.0) the file is stale, or is a copy of an older snapshot with the
     date changed — see below.

Why 6 exists
------------
Until V4.116.0 this validator read no timestamp at all: every check was about
field presence, so a snapshot of any age passed. On 2026-08-09 a run hit
`✗ no *_phase0_*.json found`, and instead of re-running Phase 0 it copied
`2026-08-07_phase0.json`, set `scan_date` to 2026-08-09, saved it under the
ticker-scoped name, and got `✓ V4.9 compliant` on the retry. The two files
differ in exactly one key.

The macro numbers in the report were then two days old while the report labelled
them as the run date — the same session's `sentiment.py` had VIX 14.9 against
phase0's 15.15.

Nothing about that trick is model-specific; it is available to any engine,
including Claude. The date check alone would not have stopped it (the date WAS
edited), so the load-bearing check is the copy detection: a Phase 0 that was
really re-run cannot be byte-identical to an older one outside `scan_date`.
"""
import argparse
import copy
import glob
import json
import os
import sys
from datetime import date, datetime

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


def check_freshness(path, data, max_age_days, today=None):
    """`scan_date` must be recent AND the payload must not be a relabelled copy.

    Returns a list of errors. The two checks answer different questions and
    neither substitutes for the other: the date says what the file claims, the
    copy check says whether anything was actually fetched.
    """
    errors = []
    today = today or date.today()

    raw = data.get("scan_date")
    if not raw:
        return ["scan_date missing — cannot tell whether Phase 0 ran for this session"]
    try:
        scanned = datetime.strptime(str(raw), "%Y-%m-%d").date()
    except ValueError:
        return [f"scan_date={raw!r} is not YYYY-MM-DD"]

    age = (today - scanned).days
    if age > max_age_days:
        errors.append(
            f"scan_date={raw} is {age} day(s) old (limit {max_age_days}) — "
            f"Phase 0 was not run for this session")
    elif age < 0:
        errors.append(f"scan_date={raw} is in the future relative to {today}")

    # The check that actually catches copy-and-relabel. A genuine re-run
    # refetches FRED and the market signals; those do not reproduce byte-for-byte
    # across days.
    #
    # Except at a weekend. A Saturday and a Sunday run both read Friday's close,
    # so their snapshots CAN be identical without anything being wrong. Flagging
    # every twin would reject a legitimate Sunday run — so a twin only counts as
    # evidence when it is older than the freshness window. Inside the window its
    # data was already allowed to be reused, and copying it forward adds nothing
    # the date rule does not already permit.
    probe = copy.deepcopy(data)
    probe.pop("scan_date", None)
    probe_s = json.dumps(probe, sort_keys=True)
    for other in sorted(glob.glob(os.path.join(LOGS_DIR, "*_phase0*.json"))):
        if os.path.abspath(other) == os.path.abspath(path):
            continue
        try:
            with open(other, "r", encoding="utf-8") as f:
                cand = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(cand, dict):
            continue
        twin_raw = cand.pop("scan_date", None)
        if json.dumps(cand, sort_keys=True) != probe_s:
            continue
        try:
            twin_age = (today - datetime.strptime(str(twin_raw), "%Y-%m-%d").date()).days
        except (ValueError, TypeError):
            twin_age = max_age_days + 1   # undatable twin: treat as the old case
        if twin_age > max_age_days:
            errors.append(
                f"identical to {os.path.relpath(other, ROOT)} (scan_date={twin_raw}, "
                f"{twin_age}d old) apart from scan_date — this is a relabelled copy, "
                f"not a fresh Phase 0 run")
            break
    return errors


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
    # Default 1, not 0: a run that starts before midnight and validates after it
    # is legitimate, and the date is all this file carries — there is no
    # timestamp to be more precise with. The copy check is what makes the loose
    # bound safe.
    ap.add_argument("--max-age-days", type=int, default=1,
                    help="how old scan_date may be, in days (default 1)")
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

    errors = check_freshness(path, data, args.max_age_days)

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
        f" · scan_date={data.get('scan_date', '?')}"
    )
    print(
        f"[validate_phase0] ✓ {os.path.relpath(path, ROOT)} V4.9 compliant — {summary}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()

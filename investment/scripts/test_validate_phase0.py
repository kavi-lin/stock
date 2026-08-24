#!/usr/bin/env python3
"""Contract for the Phase 0 freshness gate (V4.116.0).

The gate exists because on 2026-08-09 a run turned `✗ no *_phase0_*.json found`
into `✓ V4.9 compliant` by copying a two-day-old snapshot and editing one field.
Every field check in the validator passed, because none of them read a date.

The contract pins resolver, freshness, copy detection, and the real CLI schema gate.
The two freshness properties answer different questions:

  * the date says what the file *claims*;
  * the copy check says whether anything was actually *fetched*.

The copy check is the load-bearing one — the date in the real incident WAS
edited, so a date check alone would have waved it through.

Runs against a temp log directory so it never touches real invest_logs.

Usage: python3 investment/scripts/test_validate_phase0.py   (rc=0 = pass)
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate_phase0 as vp  # noqa: E402

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        failures.append(f"{name}: {detail}")


#: A snapshot that passes every pre-existing field check, so any failure below
#: is attributable to the freshness gate and nothing else.
GOOD = {
    "phase": 0,
    "scan_date": "2026-08-09",
    "phase0_source": "fred-macro",
    "macro_summary": {"market_regime": "Goldilocks"},
    "fred_available": True,
    "fred_snapshot": {
        "regime_label": "Goldilocks",
        "yield_curve_inverted": False,
        "credit_stress_elevated": False,
        "financial_stress_above_avg": False,
        "fed_rate_direction": "hold",
        "real_rate_10y": 2.1,
    },
    "phase3_macro_multiplier": 0.9,
    "macro_multiplier_rationale": "FRED real_rate>2.0 → 0.9",
    "_market_signals": {"vix": 15.15, "fear_greed": 59.7},
}


def write(dirpath, name, payload):
    path = os.path.join(dirpath, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return path


def run(dirpath, path, payload, max_age_days=1, today=None):
    """Drive the gate against a temp LOGS_DIR."""
    original = vp.LOGS_DIR
    vp.LOGS_DIR = dirpath
    try:
        return vp.check_freshness(path, payload, max_age_days, today=today)
    finally:
        vp.LOGS_DIR = original


with tempfile.TemporaryDirectory() as d:
    today = date(2026, 8, 9)

    # ── the happy path still passes ──────────────────────────────────────────
    fresh = copy.deepcopy(GOOD)
    p = write(d, "2026-08-09_phase0_now.json", fresh)
    check("fresh.passes", run(d, p, fresh, today=today) == [],
          str(run(d, p, fresh, today=today)))

    # Yesterday is allowed by default: a run can start before midnight and
    # validate after it, and the file carries a date but no clock time.
    y = copy.deepcopy(GOOD)
    y["scan_date"] = "2026-08-08"
    y["_market_signals"] = {"vix": 15.4, "fear_greed": 61.0}
    py = write(d, "2026-08-08_phase0_x.json", y)
    check("yesterday.allowed", run(d, py, y, today=today) == [],
          str(run(d, py, y, today=today)))

    # WEEKEND: a Saturday and a Sunday run both read Friday's close, so their
    # snapshots can be byte-identical with nothing wrong. The copy check must
    # not reject the second one — this case is why the twin has to be older than
    # the freshness window before it counts as evidence.
    sat = copy.deepcopy(GOOD)
    sat["scan_date"] = "2026-08-08"
    sat["_market_signals"] = {"vix": 15.15, "fear_greed": 59.7, "src": "fri-close"}
    write(d, "2026-08-08_phase0_wknd.json", sat)
    sun = copy.deepcopy(sat)
    sun["scan_date"] = "2026-08-09"
    psun = write(d, "2026-08-09_phase0_wknd.json", sun)
    check("weekend_duplicate.allowed", run(d, psun, sun, today=today) == [],
          str(run(d, psun, sun, today=today)))

    # ── stale ────────────────────────────────────────────────────────────────
    old = copy.deepcopy(GOOD)
    old["scan_date"] = "2026-08-05"
    old["_market_signals"] = {"vix": 21.0}          # keep it a distinct payload
    po = write(d, "2026-08-05_phase0_x.json", old)
    errs = run(d, po, old, today=today)
    check("stale.rejected", any("day(s) old" in e for e in errs), str(errs))

    # A future date is a clock or timezone problem, not a fresh run.
    fut = copy.deepcopy(GOOD)
    fut["scan_date"] = "2026-08-20"
    fut["_market_signals"] = {"vix": 11.0}
    pf = write(d, "2026-08-20_phase0_x.json", fut)
    check("future.rejected",
          any("future" in e for e in run(d, pf, fut, today=today)),
          str(run(d, pf, fut, today=today)))

with tempfile.TemporaryDirectory() as d:
    today = date(2026, 8, 9)

    # ── the real incident: copy an old snapshot, edit only scan_date ─────────
    original = copy.deepcopy(GOOD)
    original["scan_date"] = "2026-08-07"
    write(d, "2026-08-07_phase0.json", original)

    relabelled = copy.deepcopy(original)
    relabelled["scan_date"] = "2026-08-09"          # the one edit that was made
    pr = write(d, "2026-08-09_phase0_now.json", relabelled)

    errs = run(d, pr, relabelled, today=today)
    check("relabelled_copy.rejected", any("relabelled copy" in e for e in errs), str(errs))
    # And specifically NOT via the date rule — the date was made current, which
    # is exactly why a date check alone was not enough.
    check("relabelled_copy.date_would_have_passed",
          not any("day(s) old" in e for e in errs),
          "the date check must not be what catches this, or the test proves nothing")

    # A genuine re-run on the same day differs somewhere in the payload, and
    # must not be mistaken for a copy.
    rerun = copy.deepcopy(relabelled)
    rerun["_market_signals"] = {"vix": 14.9, "fear_greed": 63.7}
    p2 = write(d, "2026-08-09_phase0_zzz.json", rerun)
    check("genuine_rerun.passes", run(d, p2, rerun, today=today) == [],
          str(run(d, p2, rerun, today=today)))

with tempfile.TemporaryDirectory() as d:
    # ── missing / malformed date ─────────────────────────────────────────────
    nod = copy.deepcopy(GOOD)
    nod.pop("scan_date")
    pn = write(d, "x_phase0_a.json", nod)
    check("missing_date.rejected",
          any("scan_date missing" in e for e in run(d, pn, nod)), "")

    bad = copy.deepcopy(GOOD)
    bad["scan_date"] = "09/08/2026"
    pb = write(d, "x_phase0_b.json", bad)
    check("malformed_date.rejected",
          any("not YYYY-MM-DD" in e for e in run(d, pb, bad)), "")

with tempfile.TemporaryDirectory() as d:
    # Phase 0 is market-wide: a GEV run can reuse an AAOI-era legacy filename,
    # and a canonical file wins an mtime tie while migration remains compatible.
    legacy = write(d, "2026-08-21_phase0_aaoi.json", GOOD)
    check("resolver.cross_ticker_legacy",
          vp.find_latest("GEV", logs_dir=d) == os.path.abspath(legacy), "")
    canonical = write(d, "2026-08-21_phase0.json", GOOD)
    tied = time.time() - 1
    os.utime(legacy, (tied, tied))
    os.utime(canonical, (tied, tied))
    check("resolver.canonical_wins_tie",
          vp.find_latest("GEV", logs_dir=d) == os.path.abspath(canonical), "")

with tempfile.TemporaryDirectory() as d:
    # Walk the real CLI entry so removing the schema check from main() makes
    # this contract red (a helper-only test would miss a disconnected gate).
    current = copy.deepcopy(GOOD)
    current["scan_date"] = date.today().isoformat()
    good_path = write(d, "current_phase0.json", current)
    cli = subprocess.run(
        [sys.executable, vp.__file__, "--path", good_path],
        capture_output=True, text=True,
    )
    check("cli.explicit_path_passes", cli.returncode == 0, cli.stderr)
    missing = copy.deepcopy(current)
    missing.pop("macro_summary")
    bad_path = write(d, "missing_macro_phase0.json", missing)
    cli = subprocess.run(
        [sys.executable, vp.__file__, "--path", bad_path],
        capture_output=True, text=True,
    )
    check("cli.missing_macro_rejected",
          cli.returncode == 1 and "missing top-level key: macro_summary" in cli.stderr,
          cli.stderr)

if failures:
    print("✗ phase0 freshness gate contract violated:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("✓ phase0 freshness gate contract holds")

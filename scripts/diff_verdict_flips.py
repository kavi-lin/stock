#!/usr/bin/env python3
"""Verdict flip-rate tracker across event_index snapshots (TODO-010).

Question: when a decision's evaluation window is still incomplete
(`reality_at_eval.window_complete_pct < 100`), is its verdict.label already
stable, or does it flip once the window completes? A high flip rate means early
(provisional) verdicts are unreliable and Pattern statistics should exclude /
flag them.

Method (deterministic, 0 LLM):
  1. Load every dated snapshot `event_index_YYYY-MM-DD.json` in the review dir
     (skips `*latest*` / `*bak*` — those duplicate a dated snapshot).
  2. Per decision_id build a timeline of (snapshot_date, window_complete_pct,
     verdict_label).
  3. A *transition* = a decision that is observed with a DECIDED verdict while
     the window is <100% complete, AND later observed at 100% complete. We take
     the LAST incomplete reading before the first complete reading.
  4. flip = the decided label changed between those two readings.
  5. flip_rate = flips / transitions.

Bands (per TODO-010 target_action):
  flip_rate < 0.10  → close (early verdicts stable enough; non-issue)
  0.10–0.20         → observe (re-check next round)
  >= 0.20           → provisional: surface `provisional:true` for <100% verdicts
                      in build_event_index.py; Pattern stats count only 100%.

Usage:
  python3 scripts/diff_verdict_flips.py                  # human summary
  python3 scripts/diff_verdict_flips.py --json           # machine output
  python3 scripts/diff_verdict_flips.py --show-flips      # list every flip
  python3 scripts/diff_verdict_flips.py --dir <path>     # custom snapshot dir

rc: 0 always (read-only diagnostic). Exits 2 only on <2 usable snapshots.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DECIDED = {"hit", "miss", "neutral"}
SNAP_RE = re.compile(r"event_index_(\d{4}-\d{2}-\d{2})\.json$")
DEFAULT_DIR = Path(__file__).resolve().parents[1] / "reports" / "decision_review"


def _load_snapshots(snap_dir: Path) -> list[tuple[str, dict]]:
    """Return [(date_str, index_dict), ...] sorted by date. Dated files only."""
    out = []
    for p in sorted(snap_dir.glob("event_index_*.json")):
        m = SNAP_RE.search(p.name)
        if not m:                       # skips *latest* / *bak* / *.bak2*
            continue
        try:
            out.append((m.group(1), json.loads(p.read_text(encoding="utf-8"))))
        except Exception as e:          # pragma: no cover
            print(f"WARN skip {p.name}: {e}", file=sys.stderr)
    out.sort(key=lambda t: t[0])
    return out


def _records(index: dict) -> list[dict]:
    return index.get("decisions") or index.get("records") or []


def _window_pct(rec: dict):
    rae = rec.get("reality_at_eval") or {}
    return rae.get("window_complete_pct")


def _label(rec: dict):
    v = rec.get("verdict") or {}
    return v.get("label")


def compute_flips(snapshots: list[tuple[str, dict]]) -> dict:
    """Build per-decision timelines and measure incomplete→complete flips."""
    # decision_id -> ordered list of {date, wpct, label}
    timelines: dict[str, list[dict]] = {}
    for date, index in snapshots:
        for rec in _records(index):
            did = rec.get("decision_id")
            if not did:
                continue
            timelines.setdefault(did, []).append(
                {"date": date, "wpct": _window_pct(rec), "label": _label(rec)}
            )

    transitions = []  # each: {decision_id, incomplete_*, complete_*}
    for did, tl in timelines.items():
        # first reading where window is fully complete
        first_complete = next(
            (r for r in tl if r["wpct"] == 100 and r["label"] in DECIDED), None
        )
        if not first_complete:
            continue
        # last DECIDED reading before completion while window was still <100%
        incomplete = None
        for r in tl:
            if r["date"] >= first_complete["date"]:
                break
            if (
                r["wpct"] is not None
                and r["wpct"] < 100
                and r["label"] in DECIDED
            ):
                incomplete = r
        if not incomplete:
            continue
        transitions.append(
            {
                "decision_id": did,
                "incomplete_date": incomplete["date"],
                "incomplete_wpct": incomplete["wpct"],
                "incomplete_label": incomplete["label"],
                "complete_date": first_complete["date"],
                "complete_label": first_complete["label"],
                "flipped": incomplete["label"] != first_complete["label"],
            }
        )

    flips = [t for t in transitions if t["flipped"]]
    n = len(transitions)
    flip_rate = round(len(flips) / n, 4) if n else None
    if flip_rate is None:
        band = "no_data"
    elif flip_rate < 0.10:
        band = "close"
    elif flip_rate < 0.20:
        band = "observe"
    else:
        band = "provisional"

    return {
        "snapshots_used": [d for d, _ in snapshots],
        "decisions_tracked": len(timelines),
        "transitions": n,
        "flips": len(flips),
        "flip_rate": flip_rate,
        "band": band,
        "flip_detail": flips,
        "all_transitions": transitions,
    }


def _print_human(res: dict, show_flips: bool) -> None:
    band_note = {
        "close": "< 0.10 → 早期 verdict 夠穩，close 為非問題",
        "observe": "0.10–0.20 → observe band，下輪再看是否漂移",
        "provisional": ">= 0.20 → 在 build_event_index.py 為 <100% verdict 加 provisional:true，Pattern 只計 100%",
        "no_data": "無 transition 樣本",
    }[res["band"]]
    print("# Verdict Flip-Rate (TODO-010)\n")
    print(f"snapshots_used   : {len(res['snapshots_used'])} "
          f"({res['snapshots_used'][0]} … {res['snapshots_used'][-1]})")
    print(f"decisions_tracked: {res['decisions_tracked']}")
    print(f"transitions      : {res['transitions']}  (incomplete<100% → complete=100%, both DECIDED)")
    print(f"flips            : {res['flips']}")
    fr = res["flip_rate"]
    print(f"flip_rate        : {fr if fr is None else f'{fr:.1%}'}")
    print(f"band             : {res['band'].upper()}  — {band_note}")
    if show_flips and res["flip_detail"]:
        print("\n## Flips")
        for t in res["flip_detail"]:
            print(f"- {t['decision_id']}: {t['incomplete_label']} "
                  f"(@{t['incomplete_date']} wpct={t['incomplete_wpct']}) "
                  f"→ {t['complete_label']} (@{t['complete_date']})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verdict flip-rate across event_index snapshots (TODO-010)")
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR,
                    help="snapshot directory (default reports/decision_review/)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of human summary")
    ap.add_argument("--show-flips", action="store_true", help="list every flipped decision")
    args = ap.parse_args(argv)

    snapshots = _load_snapshots(args.dir)
    if len(snapshots) < 2:
        print(f"ERROR: need >=2 dated snapshots in {args.dir}, found {len(snapshots)}",
              file=sys.stderr)
        return 2

    res = compute_flips(snapshots)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        _print_human(res, args.show_flips)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

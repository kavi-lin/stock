"""Schema lint for break-news item JSON files.

Non-blocking; intended as an ops sanity check. Returns rc=0 if every file
satisfies the required schema, rc=1 otherwise. Each violation is printed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STORE_DIR = ROOT / "news" / "break_news_logs"

REQUIRED_TOP_KEYS = {
    "news_id", "schema_version", "state", "fetched_at", "source",
    "headline", "raw_summary", "triage", "thread", "errors", "graph_status",
}
REQUIRED_SOURCE_KEYS = {"name", "credibility", "url"}
REQUIRED_TRIAGE_KEYS = {
    "news_type", "shallow_score", "binary_flag", "advance_reason",
    "bull_case", "bear_case", "sector_view", "macro_view",
}
VALID_STATES = {
    "pending_debate", "debating", "closed", "partial_closed", "failed", "gated_cost",
}
REQUIRED_COMMENT_KEYS = {
    "comment_id", "agent", "round", "ts", "parsed", "parse_status", "exit_code",
}


def validate_file(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return [f"{path.name}: cannot read: {e}"]

    miss = REQUIRED_TOP_KEYS - set(d.keys())
    if miss:
        issues.append(f"{path.name}: missing top keys: {sorted(miss)}")

    if d.get("state") not in VALID_STATES:
        issues.append(f"{path.name}: invalid state: {d.get('state')!r}")

    src = d.get("source") or {}
    miss = REQUIRED_SOURCE_KEYS - set(src.keys())
    if miss:
        issues.append(f"{path.name}: missing source keys: {sorted(miss)}")

    tri = d.get("triage") or {}
    miss = REQUIRED_TRIAGE_KEYS - set(tri.keys())
    if miss:
        issues.append(f"{path.name}: missing triage keys: {sorted(miss)}")

    thread = d.get("thread") or []
    last_round = -1
    for i, c in enumerate(thread):
        miss = REQUIRED_COMMENT_KEYS - set(c.keys())
        if miss:
            issues.append(f"{path.name}: thread[{i}] missing keys: {sorted(miss)}")
        if c.get("comment_id") != f"c{i}":
            issues.append(f"{path.name}: thread[{i}].comment_id != c{i}")
        rnd = c.get("round", -1)
        if rnd < last_round:
            issues.append(
                f"{path.name}: thread[{i}].round={rnd} decreasing (prev={last_round})")
        last_round = max(last_round, rnd)

    if d.get("state") in ("closed", "partial_closed") and not d.get("summary"):
        issues.append(f"{path.name}: state={d['state']} but summary is empty")

    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(STORE_DIR))
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    p = Path(args.dir)
    files = sorted(p.glob("bn_*.json"))
    if not files:
        print(f"no bn_*.json found in {p}")
        return 0

    all_issues: list[str] = []
    for f in files:
        all_issues.extend(validate_file(f))

    if not all_issues:
        if not args.quiet:
            print(f"OK: {len(files)} file(s) validated")
        return 0
    for line in all_issues:
        print(line)
    print(f"FAIL: {len(all_issues)} issue(s) across {len(files)} file(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())

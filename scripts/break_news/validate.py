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

    # Determine strict mode based on date >= 2026-06-20
    news_id = d.get("news_id") or ""
    date_str = ""
    if d.get("fetched_at"):
        date_str = d.get("fetched_at")[:10].replace("-", "")
    elif news_id.startswith("bn_") and len(news_id) >= 11:
        date_str = news_id[3:11]

    is_strict = False
    if date_str and len(date_str) == 8 and date_str.isdigit():
        if date_str >= "20260620":
            is_strict = True

    thread = d.get("thread") or []
    last_round = -1
    for i, c in enumerate(thread):
        miss = REQUIRED_COMMENT_KEYS - set(c.keys())
        if miss:
            issues.append(f"{path.name}: thread[{i}] missing keys: {sorted(miss)}")
        if c.get("comment_id") != f"c{i}":
            issues.append(f"{path.name}: thread[{i}].comment_id != c{i}")
        rnd = c.get("round", -1)
        if rnd < last_round and is_strict:
            issues.append(
                f"{path.name}: thread[{i}].round={rnd} decreasing (prev={last_round})")
        last_round = max(last_round, rnd)

    if d.get("state") in ("closed", "partial_closed"):
        summary = d.get("summary")
        if not summary:
            issues.append(f"{path.name}: state={d['state']} but summary is empty")
        else:
            if is_strict:
                if "final_takes_by_round" not in summary or not isinstance(summary["final_takes_by_round"], list):
                    issues.append(f"{path.name}: strict V2 gate failed: missing or invalid final_takes_by_round in summary")
                
                merged_relations = summary.get("merged_relations") or []
                if not isinstance(merged_relations, list):
                    issues.append(f"{path.name}: strict V2 gate failed: merged_relations is not a list")
                else:
                    for i, rel in enumerate(merged_relations):
                        if not isinstance(rel, dict):
                            issues.append(f"{path.name}: merged_relations[{i}] is not a dict")
                            continue
                        required_rel_keys = {"support_count", "source_agents", "source_rounds", "evidence_snippets", "provisional"}
                        miss_rel = required_rel_keys - set(rel.keys())
                        if miss_rel:
                            issues.append(f"{path.name}: strict V2 gate failed: merged_relations[{i}] missing keys: {sorted(miss_rel)}")
                        if "confidence_avg" not in rel:
                            issues.append(f"{path.name}: strict V2 gate failed: merged_relations[{i}] missing confidence_avg key")

    return issues


def validate_clusters(path: Path) -> list[str]:
    """Light lint over _clusters.json (V6 event clustering store)."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return [f"{path.name}: cannot read: {e}"]
    issues: list[str] = []
    clusters = d.get("clusters")
    if not isinstance(clusters, list):
        return [f"{path.name}: 'clusters' is not a list"]
    required = {"cluster_id", "created_at", "last_seen", "news_type",
                "rep_headline", "echo_count"}
    for i, c in enumerate(clusters):
        if not isinstance(c, dict):
            issues.append(f"{path.name}: clusters[{i}] not a dict")
            continue
        miss = required - set(c.keys())
        if miss:
            issues.append(f"{path.name}: clusters[{i}] missing: {sorted(miss)}")
        if not isinstance(c.get("echo_count"), int) or c.get("echo_count", 0) < 1:
            issues.append(f"{path.name}: clusters[{i}].echo_count invalid")
    return issues


def validate_brief(path: Path) -> list[str]:
    """Light lint over _market_brief.json."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return [f"{path.name}: cannot read: {e}"]
    issues: list[str] = []
    cur = d.get("current")
    if cur is not None:
        for k in ("generated_at", "brief_text", "regime"):
            if k not in cur:
                issues.append(f"{path.name}: current missing '{k}'")
    if not isinstance(d.get("history", []), list):
        issues.append(f"{path.name}: history is not a list")
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
    all_issues.extend(validate_clusters(p / "_clusters.json"))
    all_issues.extend(validate_brief(p / "_market_brief.json"))

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

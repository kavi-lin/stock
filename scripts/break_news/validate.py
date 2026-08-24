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
sys.path.insert(0, str(ROOT))

from scripts.break_news import schema as agent_schema  # noqa: E402

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
LINK_DIGEST_TOP_KEYS = {
    "news_id", "schema_version", "state", "fetched_at", "source",
    "headline", "summary", "origin",
}
LINK_DIGEST_SUMMARY_KEYS = {
    "consensus_verdict", "merged_entities", "merged_relations",
    "bull_summary", "bear_summary", "final_take", "final_take_by",
    "rounds_completed", "closed_at", "close_reason", "divergence_note",
}


def _validate_merged_relations(path: Path, relations, label: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(relations, list):
        return [f"{path.name}: {label} is not a list"]
    required = {
        "support_count", "source_agents", "source_rounds",
        "evidence_snippets", "provisional", "confidence_avg",
    }
    for i, rel in enumerate(relations):
        if not isinstance(rel, dict):
            issues.append(f"{path.name}: {label}[{i}] is not a dict")
            continue
        missing = required - set(rel)
        if missing:
            issues.append(f"{path.name}: {label}[{i}] missing keys: {sorted(missing)}")
    return issues


def _validate_link_digest(path: Path, payload: dict) -> list[str]:
    """Validate the deterministic Link Digest projection stored beside debates."""
    issues: list[str] = []
    missing = LINK_DIGEST_TOP_KEYS - set(payload)
    if missing:
        issues.append(f"{path.name}: link_digest missing top keys: {sorted(missing)}")
    if payload.get("state") != "closed":
        issues.append(f"{path.name}: link_digest state must be 'closed'")
    source = payload.get("source") or {}
    missing = REQUIRED_SOURCE_KEYS - set(source)
    if missing:
        issues.append(f"{path.name}: link_digest source missing keys: {sorted(missing)}")
    summary = payload.get("summary") or {}
    missing = LINK_DIGEST_SUMMARY_KEYS - set(summary)
    if missing:
        issues.append(f"{path.name}: link_digest summary missing keys: {sorted(missing)}")
    issues.extend(_validate_merged_relations(
        path, summary.get("merged_relations"), "link_digest merged_relations"))
    return issues


def validate_file(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return [f"{path.name}: cannot read: {e}"]

    # Link Digest writes a deterministic summary projection into the same
    # directory but has no agent thread by design.  It needs a separate schema,
    # otherwise the main validator is permanently red on a valid non-debate.
    if d.get("origin") == "link_digest":
        return _validate_link_digest(path, d)

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
    raw_payload_schema_version = (
        (d.get("summary") or {}).get("agent_payload_schema_version"))
    if raw_payload_schema_version is None:
        payload_schema_version = 0
    elif isinstance(raw_payload_schema_version, bool) or not isinstance(
            raw_payload_schema_version, int):
        issues.append(
            f"{path.name}: summary.agent_payload_schema_version must be integer")
        payload_schema_version = agent_schema.AGENT_PAYLOAD_SCHEMA_VERSION
    else:
        payload_schema_version = raw_payload_schema_version
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

        if payload_schema_version >= agent_schema.AGENT_PAYLOAD_SCHEMA_VERSION:
            parse_status = c.get("parse_status")
            if parse_status not in {"ok", "failed", "schema_failed"}:
                issues.append(
                    f"{path.name}: thread[{i}].parse_status invalid: {parse_status!r}")
            if parse_status == "ok":
                if c.get("exit_code") != 0:
                    issues.append(
                        f"{path.name}: thread[{i}] exit_code!=0 cannot have parse_status='ok'")
                if c.get("schema_errors"):
                    issues.append(
                        f"{path.name}: thread[{i}] parse_status='ok' cannot have schema_errors")
                # V4.132.0 — round alone no longer identifies the payload: round
                # 0 side B answers A's opener, and side C arbitrates. One
                # exception the side cannot express: when A's opener failed, B
                # fell back to a blind `opening`, which `assessments` tells apart.
                side = c.get("side")
                kind = None
                if side == "B" and rnd == 0 and isinstance(c.get("parsed"), dict) \
                        and "assessments" not in c["parsed"]:
                    kind = "opening"
                for issue in agent_schema.validate_payload(
                        c.get("parsed"), rnd, side, kind):
                    issues.append(f"{path.name}: thread[{i}].parsed: {issue}")
            else:
                if c.get("parsed") is not None:
                    issues.append(
                        f"{path.name}: thread[{i}] parse_status={parse_status!r} "
                        "must have parsed=null")
                if not c.get("schema_errors"):
                    issues.append(
                        f"{path.name}: thread[{i}] parse_status={parse_status!r} "
                        "missing schema_errors")

    if d.get("state") in ("closed", "partial_closed"):
        summary = d.get("summary")
        if not summary:
            issues.append(f"{path.name}: state={d['state']} but summary is empty")
        else:
            if is_strict:
                if "final_takes_by_round" not in summary or not isinstance(summary["final_takes_by_round"], list):
                    issues.append(f"{path.name}: strict V2 gate failed: missing or invalid final_takes_by_round in summary")
                
                issues.extend(_validate_merged_relations(
                    path, summary.get("merged_relations"), "merged_relations"))

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

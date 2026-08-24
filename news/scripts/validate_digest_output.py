#!/usr/bin/env python3
"""
Validate the most recent `news_logs/YYYY-MM-DD_digest.json` against the schema
documented in `news/digest_output_schema.md`.

Invocation (from protocol Phase 4 末尾):
    python3 news/scripts/validate_digest_output.py
        rc=0  → pass
        rc=1  → schema drift detected — see stderr

What this catches:
  1. Legacy V1 shape (items/summary instead of verdicts)
  2. Missing top-level keys (fanout_mode, degraded_agents introduced in V2.1)
  3. Deep verdicts missing Arbiter fields (arbiter_reasoning, debate_note)
  4. FLASH mode with wrong review_status / cache_updated flags
  5. DIGEST mode dropping shallow verdicts (common laziness)
  6. fanout_mode inconsistency (PER_AGENT_BATCH but subagent_isolated=false)
"""
import glob
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from news.arbiter_rules import ARBITER_RULE_VERSION, classify_verdict, compute_net_impact, directional_bias
    from news.scripts.news_event_store import build_projection, load_events
except ModuleNotFoundError:  # direct: python3 news/scripts/validate_digest_output.py
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from news.arbiter_rules import ARBITER_RULE_VERSION, classify_verdict, compute_net_impact, directional_bias
    from news.scripts.news_event_store import build_projection, load_events

ROOT     = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS_DIR = os.path.join(ROOT, "news/news_logs")
EXPECTED_SCHEMA_VER = "V2.3"
ARBITER_ROLLOUT_DATE = "2026-08-06"

TOP_REQUIRED = [
    "timestamp", "mode", "stage1_count", "stage2_count",
    "fanout_mode", "degraded_agents",
    "verdicts", "session_macro_delta",
]
VERDICT_REQUIRED_COMMON = [
    "news_id", "depth", "review_status",
    "headline", "headline_zh", "source_label", "news_type", "published",
    "bull_case", "bear_case", "sector_view", "macro_view",
    "net_impact_score",
    "binary_risk", "binary_event_date", "within_48h",
    "cache_updated", "affected_sectors", "tickers_mentioned",
]
VERDICT_DEEP_EXTRA = [
    "verdict", "arbiter_reasoning", "debate_note", "subagent_isolated",
]


def fail(errors, header=None):
    # The first line is the only one that reliably survives: dashboard_server
    # joins the first five and the UI shows roughly the first 60 characters, so
    # a caller whose diagnosis differs from "schema drift" must say so here
    # rather than in errors[0] (2026-08-14: a missing digest surfaced as
    # "schema drift (expected V2.3):; - FR").
    print(header or f"[validate_digest_output] ✗ schema drift (expected {EXPECTED_SCHEMA_VER}):", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    print(
        "\nFix: rewrite the most recent news_logs/*_digest.json to match "
        "news/digest_output_schema.md then re-run this validator.",
        file=sys.stderr,
    )
    sys.exit(1)


def find_latest_digest():
    files = sorted(glob.glob(os.path.join(LOGS_DIR, "*_digest.json")))
    return files[-1] if files else None


def _verdict_event_type(verdict: dict, projection_mode: str) -> str:
    """Return the record-level mode, falling back for legacy non-event digests."""
    event_type = verdict.get("event_type")
    if event_type in ("DIGEST", "FLASH", "REVIEW", "LINK_DIGEST"):
        return event_type
    return projection_mode


def _verdict_fanout_mode(verdict: dict, projection_mode: str, projection_fanout: str) -> str:
    """Resolve fan-out per record; mixed FLASH records are always inline."""
    if verdict.get("fanout_mode"):
        return verdict["fanout_mode"]
    if _verdict_event_type(verdict, projection_mode) in ("FLASH", "LINK_DIGEST"):
        return "INLINE"
    return projection_fanout


def _arbiter_semantic_errors(
    verdict: dict,
    index: int = 0,
    fanout_mode: str = "PER_AGENT_BATCH",
    degraded_agents: list | None = None,
) -> list[str]:
    """Validate V2.3 verdict semantics without file/freshness side effects."""
    errors = []
    news_id = verdict.get("news_id", "?")
    score = verdict.get("net_impact_score")
    binary = verdict.get("binary_risk")
    actual = verdict.get("verdict")
    event_id = verdict.get("event_id")
    if not isinstance(event_id, str) or not event_id.startswith("news_"):
        errors.append(f"verdicts[{index}] deep ({news_id}): event_id must start with 'news_'")
    lane_scores = verdict.get("lane_scores")
    weights_used = verdict.get("weights_used")
    confidences = verdict.get("lane_confidences")
    if not isinstance(confidences, dict) or any(lane not in confidences for lane in ("bull", "bear", "sector", "macro")):
        errors.append(f"verdicts[{index}] deep ({news_id}): lane_confidences must contain four lanes")
    else:
        degraded_lanes = {
            str(name).lower().replace("_analyst", "").replace(" analyst", "").strip()
            for name in (degraded_agents or [])
        }
        for lane, value in confidences.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                errors.append(f"verdicts[{index}] deep ({news_id}): lane_confidences.{lane} must be within 0..1")
            elif verdict.get("source_credibility") == "LOW" and value > 0.5:
                errors.append(f"verdicts[{index}] deep ({news_id}): LOW source confidence exceeds 0.5")
            elif lane in degraded_lanes and value > 0.5:
                errors.append(f"verdicts[{index}] deep ({news_id}): degraded {lane} confidence exceeds 0.5")
    try:
        expected_score, expected_weights = compute_net_impact(
            lane_scores,
            verdict.get("news_type"),
            verdict.get("source_credibility", "MEDIUM"),
            fanout_mode,
        )
    except (TypeError, ValueError) as e:
        errors.append(f"verdicts[{index}] deep ({news_id}): invalid lane scoring: {e}")
    else:
        if score != expected_score:
            errors.append(
                f"verdicts[{index}] deep ({news_id}): net_impact_score={score!r}, "
                f"shared weighting requires {expected_score!r}"
            )
        if weights_used != expected_weights:
            errors.append(f"verdicts[{index}] deep ({news_id}): weights_used does not match news_type")
    try:
        expected = classify_verdict(score, binary)
    except (TypeError, ValueError) as e:
        return [f"verdicts[{index}] deep ({news_id}): invalid Arbiter inputs: {e}"]
    if actual != expected:
        errors.append(
            f"verdicts[{index}] deep ({news_id}): verdict={actual!r} "
            f"but deterministic {ARBITER_RULE_VERSION} rule requires {expected!r}"
        )
    if binary:
        expected_bias = directional_bias(score)
        if verdict.get("directional_bias") != expected_bias:
            errors.append(
                f"verdicts[{index}] deep ({news_id}): BINARY "
                f"directional_bias={verdict.get('directional_bias')!r}, expected {expected_bias!r}"
            )
        if not verdict.get("binary_event_date"):
            errors.append(
                f"verdicts[{index}] deep ({news_id}): "
                "binary_risk=true requires binary_event_date"
            )
    return errors


def _earlier_run_event_ids(date, triage, digest_path):
    """event_ids already in the store before this run's Stage 1 snapshot.

    A date can hold more than one DIGEST run (news_event_store._cap_shallow
    documents 2026-08-06's three). The event store is append-only, but Stage 1
    is not: a second run refetches, `news_id` is renumbered by position, and
    the earlier run's ids disappear from triage.stage2_items — on 2026-08-16
    n0087 was Natera at 14:36 and "Why Is Everyone Talking About AMD Stock?"
    at 22:10. finalize writes the union projection of the day's events, so
    those earlier deeps are legitimately in the digest with ids the current
    triage no longer knows.

    Matching is by `event_id` (URL/headline-derived, stable across runs), never
    by `news_id`, precisely because news_id is the thing that moved.

    Only events recorded *before* the current triage qualify. A verdict
    hand-added to the digest has no store record at all, so the laziness
    pattern this cross-check exists for still fires.

    Returns None when the answer cannot be established — no store file, no
    parseable timestamp on either side. The caller must then stay strict:
    "cannot tell" is not "allowed".
    """
    stamp = str(triage.get("timestamp") or "").strip()
    if not stamp:
        return None
    try:
        cutoff = datetime.fromisoformat(stamp)
    except ValueError:
        return None

    store_path = Path(os.path.dirname(digest_path)) / "news_events.jsonl"
    if not store_path.exists():
        return None
    try:
        events = load_events(store_path)
    except Exception:  # noqa: BLE001 — an unreadable store means "cannot tell"
        return None

    earlier = set()
    for event in events:
        if event.get("effective_date") != date:
            continue
        recorded = str(event.get("recorded_at") or "").strip()
        if not recorded:
            continue
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                when = datetime.strptime(recorded, fmt)
                break
            except ValueError:
                when = None
        if when is None:
            try:
                when = datetime.fromisoformat(recorded)
            except ValueError:
                continue
        if when < cutoff and event.get("event_id"):
            earlier.add(event["event_id"])
    return earlier


def _cross_check_files(digest, digest_path):
    """Cross-check today's digest against its sibling triage.json.

    Catches the laziness pattern where digest.stage1_count claims one number
    but the on-disk triage shows another, or deep verdict news_ids do not
    appear in triage.stage2_items at all (i.e. Stage 1 was never re-run for
    this date and the digest was hand-edited).

    Soft behaviour: when triage.json is missing for that date, we record an
    INFO note and skip — protocol pre-v3.14.3 didn't always persist a
    matching triage file, so making this hard-fail would break historical
    digests. Today's run (NEWS_RUN_START_MS set) bumps it to hard-fail.
    """
    if digest.get("mode") not in (None, "DIGEST"):
        return []
    base = os.path.basename(digest_path)
    # Strip trailing _digest.json
    date = base[: -len("_digest.json")] if base.endswith("_digest.json") else base
    triage_path = os.path.join(os.path.dirname(digest_path), f"{date}_triage.json")

    if not os.path.exists(triage_path):
        if os.environ.get("NEWS_RUN_START_MS"):
            return [
                f"triage.json missing alongside digest: {triage_path} — "
                "Stage 1 triage was not persisted for this run "
                "(STRICT mode — env NEWS_RUN_START_MS set)."
            ]
        # Loose mode: legacy digests without triage are tolerated.
        print(
            f"[validate_digest_output] note: no {date}_triage.json found "
            "— skipping cross-check (loose mode).",
            file=sys.stderr,
        )
        return []

    try:
        with open(triage_path, "r", encoding="utf-8") as fp:
            triage = json.load(fp)
    except (OSError, json.JSONDecodeError) as e:
        return [f"triage.json unreadable {triage_path}: {e}"]

    errors = []

    shallow_n = len(triage.get("shallow_verdicts") or [])
    digest_s1 = digest.get("stage1_count")
    if isinstance(digest_s1, int) and digest_s1 != shallow_n:
        errors.append(
            f"stage1_count mismatch: digest claims {digest_s1} but "
            f"{date}_triage.json shallow_verdicts has {shallow_n} entries"
        )

    triage_stage2_ids = {
        x.get("news_id")
        for x in (triage.get("stage2_items") or [])
        if isinstance(x, dict)
    }
    deep_verdicts = [
        v
        for v in (digest.get("verdicts") or [])
        if isinstance(v, dict) and v.get("depth") == "deep"
        and v.get("event_type", "DIGEST") == "DIGEST"
    ]
    unmatched = [
        v for v in deep_verdicts
        if v.get("news_id") and v["news_id"] not in triage_stage2_ids
    ]
    if unmatched:
        # Not every unmatched id is drift: an earlier DIGEST run on the same
        # date leaves deeps whose news_id this run's Stage 1 renumbered away.
        earlier = _earlier_run_event_ids(date, triage, digest_path)
        if earlier is None:
            orphans = sorted({v["news_id"] for v in unmatched})
            tail = "and the event store cannot confirm an earlier run for this date"
        else:
            orphans = sorted({
                v["news_id"] for v in unmatched
                if v.get("event_id") not in earlier
            })
            tail = "and no event recorded before this run's Stage 1 backs them"
        if orphans:
            errors.append(
                f"deep verdicts not in triage.stage2_items: {orphans} — "
                f"digest cites news_ids that Stage 1 did not advance, {tail}"
            )

    # Telemetry sanity (P0a/P0b): triage should carry blocked_counts /
    # template_dedup_dropped fields once v3.14.3 stage1 runs in production.
    # We don't fail when they're missing (pre-v3.14.3 runs) but surface them.
    if "blocked_counts" not in triage or "template_dedup_dropped" not in triage:
        print(
            "[validate_digest_output] note: triage.json missing v3.14.3 "
            "telemetry (blocked_counts / template_dedup_dropped) — "
            "stage1_triage may be pre-v3.14.3.",
            file=sys.stderr,
        )

    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--path", help="validate this digest instead of latest news_logs file")
    args, _ = parser.parse_known_args(argv)
    path = os.path.abspath(args.path) if args.path else find_latest_digest()
    if not path:
        fail([f"no *_digest.json found under {LOGS_DIR}"])

    # Distinct from schema drift: nothing was written for today at all, so the
    # glob fell back to an older file. The shape of that file is irrelevant —
    # the run died upstream, and the message has to point there.
    today_iso = datetime.now().strftime("%Y-%m-%d")
    today_path = os.path.join(LOGS_DIR, f"{today_iso}_digest.json")
    if not args.path and not os.path.exists(today_path):
        fail(
            [
                f"expected news/news_logs/{today_iso}_digest.json — Phase 4 never wrote it.",
                f"latest digest on disk: {os.path.basename(path)}",
                "Check news/scan_logs/ for the last non-zero rc — finalize_digest.py "
                "runs before this validator and refuses to assemble on bad input.",
            ],
            header=f"[validate_digest_output] ✗ 今日無 digest（{today_iso}）：Phase 4 未產出",
        )

    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    errors = []

    # ── 0. Freshness gate — digest.json must be rewritten THIS run ────────
    # Prevents Claude from "passing" validator by leaving previous digest
    # untouched. Two-level check:
    #  (a) Default: timestamp must be today + mtime < 2h (loose).
    #  (b) Strict mode: env NEWS_RUN_START_MS set → mtime must be ≥ start.
    #      Server-triggered runs always use strict mode. Manual invocations
    #      (e.g. post-salvage) use loose mode.
    import os as _os, time as _t
    ts_str = (data.get("timestamp") or "").strip()
    if not ts_str.startswith(today_iso):
        fail([
            f"FRESHNESS FAIL: digest.json timestamp={ts_str!r} is not from today ({today_iso}).",
            "Claude must rewrite news_logs/YYYY-MM-DD_digest.json with today's Phase 4 output.",
            "Check: Stage 1 triage + Stage 2 four-subagent debate must run before Phase 4.",
        ])
    mtime_sec = _os.path.getmtime(path)
    mtime_age_sec = _t.time() - mtime_sec
    run_start_ms = _os.environ.get("NEWS_RUN_START_MS")
    arbiter_v23 = data.get("arbiter_rule_version") == ARBITER_RULE_VERSION
    if run_start_ms and ts_str[:10] >= ARBITER_ROLLOUT_DATE and not arbiter_v23:
        errors.append(
            f"arbiter_rule_version must be {ARBITER_RULE_VERSION!r} for "
            f"new strict runs dated {ARBITER_ROLLOUT_DATE} or later"
        )
    elif ts_str[:10] >= ARBITER_ROLLOUT_DATE and not arbiter_v23:
        print(
            f"[validate_digest_output] note: legacy same-day artifact has no "
            f"arbiter_rule_version={ARBITER_RULE_VERSION}; V2.3 semantic checks skipped "
            "in loose mode.",
            file=sys.stderr,
        )
    if run_start_ms:
        try:
            run_start_sec = int(run_start_ms) / 1000.0
            if mtime_sec < run_start_sec - 5:  # 5s grace
                delta_min = (run_start_sec - mtime_sec) / 60
                fail([
                    f"STRICT FRESHNESS FAIL: digest.json mtime is {delta_min:.1f} min BEFORE run start.",
                    "This run did not rewrite digest.json → Claude likely skipped Stage 1 or Stage 2.",
                    f"Required: Stage 1 RSS triage (≥20 shallow) + Stage 2 four-subagent debate + Phase 4 Write.",
                ])
        except ValueError:
            pass
    elif mtime_age_sec > 7200:  # 2 hours loose mode
        fail([
            f"FRESHNESS FAIL: digest.json mtime is {int(mtime_age_sec/60)} min old (>2h).",
            "The file must be written by this run, not a stale previous artifact.",
        ])

    # ── 1. Legacy V1 shape ────────────────────────────────────────────────
    if "items" in data and "verdicts" not in data:
        fail([
            "DETECTED LEGACY V1 SHAPE — 'items' array without 'verdicts'.",
            "V2+ uses `verdicts[]` with per-news per-agent analysis. See schema.",
        ])

    # ── 2. Top-level required keys ────────────────────────────────────────
    for k in TOP_REQUIRED:
        if k not in data:
            errors.append(f"missing top-level key: {k}")

    mode = data.get("mode")
    if mode not in ("DIGEST", "FLASH", "REVIEW"):
        errors.append(f"invalid mode: {mode!r} (must be DIGEST / FLASH / REVIEW)")

    verdicts = data.get("verdicts", [])
    if not isinstance(verdicts, list) or not verdicts:
        errors.append("verdicts must be a non-empty array")
        fail(errors)

    # ── 3. Per-verdict checks ─────────────────────────────────────────────
    deep_count  = 0
    shallow_count = 0
    for i, v in enumerate(verdicts):
        for k in VERDICT_REQUIRED_COMMON:
            if k not in v:
                errors.append(f"verdicts[{i}] ({v.get('news_id','?')}): missing key {k}")
        published = v.get("published")
        if not isinstance(published, str) or not published.strip():
            errors.append(f"verdicts[{i}] ({v.get('news_id','?')}): published must be a non-empty ISO timestamp")
        else:
            try:
                datetime.fromisoformat(published.strip().replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"verdicts[{i}] ({v.get('news_id','?')}): published is not valid ISO-8601: {published!r}")
        depth = v.get("depth")
        if depth not in ("shallow", "deep"):
            errors.append(f"verdicts[{i}]: invalid depth {depth!r} (must be 'shallow' or 'deep')")
            continue
        if depth == "deep":
            deep_count += 1
            for k in VERDICT_DEEP_EXTRA:
                if k not in v:
                    errors.append(f"verdicts[{i}] deep ({v.get('news_id','?')}): missing {k}")
            # Deep: arbiter_reasoning must be non-empty string
            ar = v.get("arbiter_reasoning")
            if not isinstance(ar, str) or len(ar.strip()) < 30:
                errors.append(f"verdicts[{i}] deep ({v.get('news_id','?')}): arbiter_reasoning must be ≥30 chars (got {type(ar).__name__} len={len(ar) if isinstance(ar, str) else 0})")
            # Deep: verdict must be one of the four
            verd = v.get("verdict")
            if verd not in ("BULLISH", "BEARISH", "BINARY", "NEUTRAL"):
                errors.append(f"verdicts[{i}] deep ({v.get('news_id','?')}): verdict={verd!r} must be BULLISH/BEARISH/BINARY/NEUTRAL")
            # Deep: tickers_mentioned must be list (possibly empty — but not missing)
            if not isinstance(v.get("tickers_mentioned"), list):
                errors.append(f"verdicts[{i}] deep ({v.get('news_id','?')}): tickers_mentioned must be array (use [] if none)")
            verdict_type = _verdict_event_type(v, mode)
            verdict_fanout = _verdict_fanout_mode(
                v, mode, data.get("fanout_mode")
            )
            if arbiter_v23 and v.get("event_type", "DIGEST") != "LINK_DIGEST":
                errors.extend(_arbiter_semantic_errors(
                    v, i, verdict_fanout,
                    v.get("degraded_agents") or data.get("degraded_agents"),
                ))
            if verdict_type == "FLASH":
                if v.get("review_status") != "pending":
                    errors.append(
                        f"verdicts[{i}] FLASH ({v.get('news_id','?')}): "
                        f"review_status must be 'pending' (got {v.get('review_status')!r})"
                    )
                if v.get("cache_updated") is not False:
                    errors.append(
                        f"verdicts[{i}] FLASH ({v.get('news_id','?')}): cache_updated must be false"
                    )
            elif verdict_type in ("DIGEST", "REVIEW"):
                if v.get("review_status") != "reviewed":
                    errors.append(
                        f"verdicts[{i}] {verdict_type} ({v.get('news_id','?')}): "
                        f"review_status must be 'reviewed' (got {v.get('review_status')!r})"
                    )
                if v.get("cache_updated") is not True:
                    errors.append(
                        f"verdicts[{i}] {verdict_type} ({v.get('news_id','?')}): cache_updated must be true"
                    )
        else:
            shallow_count += 1

    # ── 4. Mode-specific rules ────────────────────────────────────────────
    is_event_projection = data.get("event_projection_version") == 1
    if mode == "FLASH" and not is_event_projection:
        if shallow_count != 0 or deep_count != 1:
            errors.append(f"FLASH mode must have 0 shallow + 1 deep verdict (got {shallow_count}/{deep_count})")
        dv = next((v for v in verdicts if v.get("depth") == "deep"), None)
        if dv:
            if dv.get("review_status") != "pending":
                errors.append(f"FLASH verdict review_status must be 'pending' (got {dv.get('review_status')!r})")
            if dv.get("cache_updated"):
                errors.append("FLASH verdict cache_updated must be false (FLASH doesn't patch cache)")

    elif mode == "REVIEW" and not is_event_projection:
        if shallow_count != 0 or deep_count != 1:
            errors.append(f"REVIEW mode must have 0 shallow + 1 deep verdict (got {shallow_count}/{deep_count})")
        dv = next((v for v in verdicts if v.get("depth") == "deep"), None)
        if dv:
            if dv.get("review_status") != "reviewed":
                errors.append(f"REVIEW verdict review_status must be 'reviewed' (got {dv.get('review_status')!r})")
            if dv.get("event_type") != "LINK_DIGEST" and dv.get("cache_updated") is not True:
                errors.append("REVIEW verdict cache_updated must be true")

    elif mode == "DIGEST":
        # Shallow is capped at top 10 by |shallow_score| (see news_protocol_v2.md Phase 4).
        # Rationale: 34KB JSON → 3-min Write + retry; 10KB JSON → <1-min Write.
        # MD report's Shallow Digest may still show top 20 (reader-facing only).
        s1 = data.get("stage1_count", 0)
        s2 = data.get("stage2_count", 0)
        if deep_count != s2:
            errors.append(f"DIGEST deep count mismatch: stage2_count={s2} but verdicts[].filter(deep) = {deep_count}")
        expected_shallow = min(10, max(0, s1 - s2))
        if shallow_count < expected_shallow:
            errors.append(
                f"DIGEST shallow under-cap: stage1_count={s1}, stage2_count={s2} "
                f"→ expect ≥ min(10, s1−s2)={expected_shallow} shallow verdicts, got {shallow_count}. "
                f"Write top-{expected_shallow} by |shallow_score|."
            )
        # Hard ceiling to enforce the cap (reject bloat that slows Write)
        if shallow_count > 15:
            errors.append(
                f"DIGEST shallow over-cap: got {shallow_count} shallow verdicts, max allowed = 15 "
                f"(soft target 10). Trim to top 10 by |shallow_score|."
            )

    # ── 5. fanout_mode consistency (V2.1) ────────────────────────────────
    fm = data.get("fanout_mode")
    valid_fm = ("PER_AGENT_BATCH", "PARTIAL_FALLBACK", "FULL_FALLBACK", "INLINE")
    if fm not in valid_fm:
        errors.append(f"fanout_mode must be one of {valid_fm} (got {fm!r})")
    for i, v in enumerate(verdicts):
        if v.get("depth") != "deep":
            continue
        verdict_fm = _verdict_fanout_mode(v, mode, fm)
        if verdict_fm not in valid_fm:
            errors.append(
                f"verdicts[{i}] ({v.get('news_id','?')}): fanout_mode must be one of "
                f"{valid_fm} (got {verdict_fm!r})"
            )
        elif verdict_fm == "PER_AGENT_BATCH" and v.get("subagent_isolated") is not True:
            errors.append(
                f"verdicts[{i}] ({v.get('news_id','?')}): fanout_mode=PER_AGENT_BATCH "
                "requires subagent_isolated=true"
            )

    # ── 6. v3.14.3 — cross-check digest against sibling triage.json ──────
    errors.extend(_cross_check_files(data, path))

    # ── 7. Event-store projection integrity ──────────────────────────────
    if data.get("event_projection_version") == 1:
        event_path = os.path.join(os.path.dirname(path), "news_events.jsonl")
        try:
            projection_date = data.get("projection_date") or os.path.basename(path)[:10]
            expected = build_projection(load_events(Path(event_path)), projection_date)
        except Exception as exc:
            errors.append(f"event projection cannot be rebuilt: {exc}")
        else:
            if expected != data:
                errors.append("digest.json differs from deterministic news_events.jsonl projection")

    if errors:
        fail(errors)

    print(f"[validate_digest_output] ✓ {EXPECTED_SCHEMA_VER} schema compliant — "
          f"mode={mode}, {shallow_count} shallow + {deep_count} deep, fanout={fm}")
    sys.exit(0)


if __name__ == "__main__":
    main()

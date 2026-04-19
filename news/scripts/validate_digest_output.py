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
import json
import os
import sys
from datetime import datetime

ROOT     = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS_DIR = os.path.join(ROOT, "news/news_logs")
EXPECTED_SCHEMA_VER = "V2.1"

TOP_REQUIRED = [
    "timestamp", "mode", "stage1_count", "stage2_count",
    "fanout_mode", "degraded_agents",
    "verdicts", "session_macro_delta",
]
VERDICT_REQUIRED_COMMON = [
    "news_id", "depth", "review_status",
    "headline", "headline_zh", "source_label", "news_type",
    "bull_case", "bear_case", "sector_view", "macro_view",
    "net_impact_score",
    "binary_risk", "binary_event_date", "within_48h",
    "cache_updated", "affected_sectors", "tickers_mentioned",
]
VERDICT_DEEP_EXTRA = [
    "verdict", "arbiter_reasoning", "debate_note", "subagent_isolated",
]


def fail(errors):
    print(f"[validate_digest_output] ✗ schema drift (expected {EXPECTED_SCHEMA_VER}):", file=sys.stderr)
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


def main():
    path = find_latest_digest()
    if not path:
        fail([f"no *_digest.json found under {LOGS_DIR}"])

    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    errors = []

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
        else:
            shallow_count += 1

    # ── 4. Mode-specific rules ────────────────────────────────────────────
    if mode == "FLASH":
        if shallow_count != 0 or deep_count != 1:
            errors.append(f"FLASH mode must have 0 shallow + 1 deep verdict (got {shallow_count}/{deep_count})")
        dv = next((v for v in verdicts if v.get("depth") == "deep"), None)
        if dv:
            if dv.get("review_status") != "pending":
                errors.append(f"FLASH verdict review_status must be 'pending' (got {dv.get('review_status')!r})")
            if dv.get("cache_updated"):
                errors.append("FLASH verdict cache_updated must be false (FLASH doesn't patch cache)")

    elif mode == "REVIEW":
        if shallow_count != 0 or deep_count != 1:
            errors.append(f"REVIEW mode must have 0 shallow + 1 deep verdict (got {shallow_count}/{deep_count})")
        dv = next((v for v in verdicts if v.get("depth") == "deep"), None)
        if dv:
            if dv.get("review_status") != "reviewed":
                errors.append(f"REVIEW verdict review_status must be 'reviewed' (got {dv.get('review_status')!r})")

    elif mode == "DIGEST":
        # Common laziness: dropping shallow — check that stage1_count matches
        s1 = data.get("stage1_count", 0)
        s2 = data.get("stage2_count", 0)
        if s1 > 0 and shallow_count + deep_count < s1:
            errors.append(f"DIGEST dropped shallow verdicts: stage1_count={s1}, stage2_count={s2}, but verdicts[] only has {shallow_count + deep_count} entries — shallow not persisted?")
        if deep_count != s2:
            errors.append(f"DIGEST deep count mismatch: stage2_count={s2} but verdicts[].filter(deep) = {deep_count}")

    # ── 5. fanout_mode consistency (V2.1) ────────────────────────────────
    fm = data.get("fanout_mode")
    valid_fm = ("PER_AGENT_BATCH", "PARTIAL_FALLBACK", "FULL_FALLBACK", "INLINE")
    if fm not in valid_fm:
        errors.append(f"fanout_mode must be one of {valid_fm} (got {fm!r})")
    if fm == "PER_AGENT_BATCH":
        # All deep verdicts should have subagent_isolated=true
        bad = [v.get("news_id") for v in verdicts if v.get("depth") == "deep" and v.get("subagent_isolated") is not True]
        if bad:
            errors.append(f"fanout_mode=PER_AGENT_BATCH but these deep verdicts have subagent_isolated!=true: {bad}")

    if errors:
        fail(errors)

    print(f"[validate_digest_output] ✓ {EXPECTED_SCHEMA_VER} schema compliant — "
          f"mode={mode}, {shallow_count} shallow + {deep_count} deep, fanout={fm}")
    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Validate the most recent `sector_logs/YYYY-MM-DD_sector_intel.json` against
the schema documented in `sector/schema.md`.

Invocation (from Phase 5 末尾):
    python3 sector/scripts/validate_sector_intel.py
        rc=0  → pass
        rc=1  → schema drift detected — see stderr

What this catches (bridge.py depends on these):
  1. Wrong protocol_version (must be V1.3 for sector v1.3)
  2. Missing `_phase0` / `_phase1` / `_phase3` sub-objects (bridge.py keys)
  3. Phase 0 synthesized_exposure / signal_conflict / ftd / market_top missing
  4. Phase 1 sectors[] empty or missing uptrend_ratio per sector
  5. Phase 3 top_catalysts < 5 entries (protocol requires ≥ 5)
  6. V1.3 fan-out metadata: phase4_fanout_mode / degraded_agents
  7. HOT sector without proxy_etf (bridge.py uses this for Dashboard)
  8. sectors[] verdict values outside {HOT, WARM, COLD, AVOID}
"""
import glob
import json
import os
import sys

ROOT     = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS_DIR = os.path.join(ROOT, "sector/sector_logs")
EXPECTED_VERSION = "V1.3"

TOP_REQUIRED = [
    "verdict_date", "protocol_version", "generated_at",
    "market_regime", "exposure_ceiling", "synthesized_exposure", "cycle_phase",
    "_phase0", "_phase1", "_phase3",
    "sentiment_snapshot", "sectors", "summary",
    "political_risk_summary", "actionable_themes", "session_notes",
    # V1.3 additions (fan-out metadata)
    "phase4_fanout_mode", "degraded_agents",
]

PHASE0_REQUIRED = [
    "phase", "breadth_source", "breadth_score", "breadth_zone",
    "market_regime", "cycle_phase", "uptrend_ratio_overall",
    "warning_flags", "exposure_ceiling", "regime_confidence",
    "ftd", "market_top", "synthesized_exposure", "signal_conflict",
]

PHASE1_REQUIRED = ["phase", "sectors"]
PHASE3_REQUIRED = ["phase", "top_catalysts", "political_overlay"]

VALID_VERDICTS   = {"HOT", "WARM", "COLD", "AVOID"}
VALID_STANCES    = {"AGGRESSIVE", "NEUTRAL", "DEFENSIVE"}
VALID_FANOUT     = {"PARALLEL_SUBAGENT", "PARTIAL_FALLBACK", "FULL_FALLBACK", "INLINE"}


def fail(errors):
    print(f"[validate_sector_intel] ✗ schema drift (expected {EXPECTED_VERSION}):", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    print(
        "\nFix: rewrite the most recent sector_logs/*_sector_intel.json to match "
        "sector/schema.md then re-run this validator.",
        file=sys.stderr,
    )
    sys.exit(1)


def find_latest_sector_intel():
    files = sorted(glob.glob(os.path.join(LOGS_DIR, "*_sector_intel.json")))
    return files[-1] if files else None


def main():
    path = find_latest_sector_intel()
    if not path:
        fail([f"no *_sector_intel.json found under {LOGS_DIR}"])

    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    errors = []

    # ── 1. Version ────────────────────────────────────────────────────────
    ver = data.get("protocol_version")
    if ver != EXPECTED_VERSION:
        errors.append(f"protocol_version = {ver!r}, expected {EXPECTED_VERSION!r}")

    # ── 2. Top-level required keys ────────────────────────────────────────
    for k in TOP_REQUIRED:
        if k not in data:
            errors.append(f"missing top-level key: {k}")

    # ── 3. _phase0 structure ──────────────────────────────────────────────
    p0 = data.get("_phase0", {})
    for k in PHASE0_REQUIRED:
        if k not in p0:
            errors.append(f"_phase0 missing key: {k}")
    if isinstance(p0, dict):
        ftd = p0.get("ftd") or {}
        if not ftd or "state" not in ftd or "quality_score" not in ftd:
            errors.append("_phase0.ftd missing state/quality_score (Global Rule 2 requires cache refresh)")
        mt = p0.get("market_top") or {}
        if not mt or "composite_score" not in mt or "zone" not in mt:
            errors.append("_phase0.market_top missing composite_score/zone")

    # ── 4. _phase1 structure ──────────────────────────────────────────────
    p1 = data.get("_phase1", {})
    for k in PHASE1_REQUIRED:
        if k not in p1:
            errors.append(f"_phase1 missing key: {k}")
    sectors1 = p1.get("sectors") if isinstance(p1, dict) else None
    if not isinstance(sectors1, list) or len(sectors1) == 0:
        errors.append("_phase1.sectors must be a non-empty array")
    else:
        for i, s in enumerate(sectors1):
            for req in ("name", "uptrend_ratio", "rotation_signal"):
                if req not in s:
                    errors.append(f"_phase1.sectors[{i}] ({s.get('name','?')}): missing {req}")

    # ── 5. _phase3 structure ──────────────────────────────────────────────
    p3 = data.get("_phase3", {})
    for k in PHASE3_REQUIRED:
        if k not in p3:
            errors.append(f"_phase3 missing key: {k}")
    tc = p3.get("top_catalysts") if isinstance(p3, dict) else None
    if not isinstance(tc, list) or len(tc) < 5:
        errors.append(f"_phase3.top_catalysts must have ≥ 5 entries (protocol requirement) — got {len(tc) if isinstance(tc, list) else 0}")

    # ── 6. V1.3 fan-out metadata ──────────────────────────────────────────
    fm = data.get("phase4_fanout_mode")
    if fm not in VALID_FANOUT:
        errors.append(f"phase4_fanout_mode must be one of {VALID_FANOUT} (got {fm!r})")
    da = data.get("degraded_agents")
    if not isinstance(da, list):
        errors.append(f"degraded_agents must be an array (got {type(da).__name__})")

    # ── 7. sectors[] final verdict quality ────────────────────────────────
    sectors = data.get("sectors") or []
    if not isinstance(sectors, list) or not sectors:
        errors.append("top-level sectors[] must be non-empty")
    else:
        for i, s in enumerate(sectors):
            verd = s.get("verdict")
            if verd not in VALID_VERDICTS:
                errors.append(f"sectors[{i}] ({s.get('name','?')}): verdict={verd!r} must be one of {VALID_VERDICTS}")
            if verd == "HOT" and not s.get("proxy_etf"):
                errors.append(f"sectors[{i}] ({s.get('name','?')}): HOT verdict requires proxy_etf (bridge.py uses this for Dashboard)")
            cs = s.get("composite_score")
            if cs is None or not (0 <= float(cs) <= 100):
                errors.append(f"sectors[{i}] ({s.get('name','?')}): composite_score must be in [0, 100] (got {cs!r})")

    # ── 8. summary consistency ────────────────────────────────────────────
    summary = data.get("summary", {})
    for key in ("hot_sectors", "warm_sectors", "cold_sectors", "avoid_sectors"):
        if key not in summary:
            errors.append(f"summary missing {key}")

    if errors:
        fail(errors)

    hot = summary.get("hot_sectors", [])
    cold = summary.get("cold_sectors", [])
    print(f"[validate_sector_intel] ✓ {EXPECTED_VERSION} schema compliant — "
          f"{len(sectors)} sectors, {len(hot)} HOT / {len(cold)} COLD, fanout={fm}")
    sys.exit(0)


if __name__ == "__main__":
    main()

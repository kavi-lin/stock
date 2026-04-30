#!/usr/bin/env python3
"""
Validate the most recent `sector_logs/YYYY-MM-DD_sector_intel.json` against
the schema documented in `sector/schema.md`.

Invocation (from Phase 5 末尾):
    python3 sector/scripts/validate_sector_intel.py
        rc=0  → pass
        rc=1  → schema drift detected — see stderr

What this catches (bridge.py depends on these):
  1. Wrong protocol_version (must be V1.4 for sector v1.4)
  2. Missing `_phase0` / `_phase1` / `_phase3` sub-objects (bridge.py keys)
  3. Phase 0 synthesized_exposure / signal_conflict / ftd / market_top missing
  4. Phase 1 sectors[] empty or missing uptrend_ratio per sector
  5. Phase 3 top_catalysts < 5 entries (protocol requires ≥ 5)
  6. V1.3 fan-out metadata: phase4_fanout_mode / degraded_agents
  7. HOT sector without proxy_etf (bridge.py uses this for Dashboard)
  8. sectors[] verdict values outside {HOT, WARM, COLD, AVOID}
  9. V1.4 sector_valuation block on each _phase1.sectors[] (FMP MCP hard-required)
 10. V1.4 score_components.valuation_penalty on each top-level sectors[]
"""
import glob
import json
import os
import sys

ROOT     = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS_DIR = os.path.join(ROOT, "sector/sector_logs")
EXPECTED_VERSION = "V1.4"

# V1.4 — sector valuation block required on each _phase1.sectors[]
SECTOR_VALUATION_REQUIRED = [
    "pe_ttm", "pe_zscore_1y", "rs_vs_spy_3m", "etf_volume_ratio_20d",
]

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
    # V1.4 — FRED Layer E (MUST-run)
    "fred_available",
]

FRED_SLIM_REQUIRED = [
    "regime_label", "regime_confidence", "macro_scores_composite",
    "yield_curve_inverted", "credit_stress_elevated", "financial_stress_above_avg",
    "fed_rate_direction", "real_rate_preferred",
    "sector_rotation_favor", "sector_rotation_avoid",
]
VALID_REGIMES = {
    "Goldilocks", "Soft Landing", "Reflation", "Benign Easing", "Overheating",
    "Late Cycle Tightening", "Stagflation", "Recession Easing", "Recession Risk",
    "Transitional",
}

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

        # V1.4 — FRED Layer E slim snapshot
        fred_avail = p0.get("fred_available")
        if fred_avail is True:
            fs = p0.get("fred_snapshot")
            if not isinstance(fs, dict):
                errors.append("_phase0.fred_available=true but fred_snapshot missing or not dict")
            else:
                for k in FRED_SLIM_REQUIRED:
                    if k not in fs:
                        errors.append(f"_phase0.fred_snapshot missing {k}")
                rl = fs.get("regime_label")
                if rl is not None and rl not in VALID_REGIMES:
                    errors.append(f"_phase0.fred_snapshot.regime_label={rl!r} not in {sorted(VALID_REGIMES)}")
                rc = fs.get("regime_confidence")
                if rc is not None and not (0.0 <= float(rc) <= 1.0):
                    errors.append(f"_phase0.fred_snapshot.regime_confidence={rc!r} must be 0.0-1.0")
                for lst_key in ("sector_rotation_favor", "sector_rotation_avoid"):
                    if lst_key in fs and not isinstance(fs[lst_key], list):
                        errors.append(f"_phase0.fred_snapshot.{lst_key} must be array")
        elif fred_avail is False:
            # fallback acceptable; snapshot can be null
            pass
        else:
            errors.append(f"_phase0.fred_available must be true/false bool (got {fred_avail!r})")

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
            # V1.4 — sector_valuation block (FMP MCP hard-required, no graceful fallback)
            sv = s.get("sector_valuation")
            if not isinstance(sv, dict):
                errors.append(
                    f"_phase1.sectors[{i}] ({s.get('name','?')}): missing sector_valuation block "
                    f"(V1.4 hard-required — run sector/scripts/fetch_sector_valuation.py)"
                )
            else:
                for k in SECTOR_VALUATION_REQUIRED:
                    if k not in sv:
                        errors.append(
                            f"_phase1.sectors[{i}] ({s.get('name','?')}): "
                            f"sector_valuation missing {k}"
                        )

    # ── 5. _phase3 structure ──────────────────────────────────────────────
    p3 = data.get("_phase3", {})
    for k in PHASE3_REQUIRED:
        if k not in p3:
            errors.append(f"_phase3 missing key: {k}")
    tc = p3.get("top_catalysts") if isinstance(p3, dict) else None
    if not isinstance(tc, list) or len(tc) < 5:
        errors.append(f"_phase3.top_catalysts must have ≥ 5 entries (protocol requirement) — got {len(tc) if isinstance(tc, list) else 0}")
    # V1.4 — sector_earnings_pulse hard-required
    sep = p3.get("sector_earnings_pulse") if isinstance(p3, dict) else None
    if not isinstance(sep, dict) or not sep:
        errors.append(
            "_phase3.sector_earnings_pulse missing (V1.4 hard-required — "
            "run sector/scripts/fetch_earnings_pulse.py)"
        )
    elif isinstance(sep, dict):
        for sec_name, blk in sep.items():
            if not isinstance(blk, dict):
                errors.append(f"_phase3.sector_earnings_pulse[{sec_name}] must be dict")
                continue
            for k in ("report_count", "beat_rate_30d", "surprise_score_avg"):
                if k not in blk:
                    errors.append(f"_phase3.sector_earnings_pulse[{sec_name}] missing {k}")
    # V1.4 — smart_money_signals hard-required
    sms = p3.get("smart_money_signals") if isinstance(p3, dict) else None
    if not isinstance(sms, dict) or not sms:
        errors.append(
            "_phase3.smart_money_signals missing (V1.4 hard-required — "
            "run sector/scripts/fetch_smart_money.py)"
        )
    elif isinstance(sms, dict):
        for sec_name, blk in sms.items():
            if not isinstance(blk, dict):
                errors.append(f"_phase3.smart_money_signals[{sec_name}] must be dict")
                continue
            for k in ("insider_acquired_disposed_ratio_q", "senate_net_buy_30d"):
                if k not in blk:
                    errors.append(f"_phase3.smart_money_signals[{sec_name}] missing {k}")

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
            # V1.4 — score_components.valuation_penalty hard-required
            sc = s.get("score_components") or {}
            if "valuation_penalty" not in sc:
                errors.append(
                    f"sectors[{i}] ({s.get('name','?')}): score_components.valuation_penalty "
                    f"missing (V1.4 hard-required)"
                )

    # ── 8. summary consistency ────────────────────────────────────────────
    summary = data.get("summary", {})
    for key in ("hot_sectors", "warm_sectors", "cold_sectors", "avoid_sectors"):
        if key not in summary:
            errors.append(f"summary missing {key}")

    # ── 9. today_verdict (V1.4) — warn-only so older caches don't break ──
    # Once all new scans produce this, we'll tighten to hard error.
    warnings = []
    p4c = data.get("_phase4c") or {}
    tv = p4c.get("today_verdict")
    if not isinstance(tv, dict):
        warnings.append("_phase4c missing today_verdict (required from V1.4 on; Dashboard hero card will fall back to session_notes)")
    else:
        for req in ("headline", "stance", "one_liner", "key_takeaways", "sector_actions", "watch_next"):
            if req not in tv:
                warnings.append(f"_phase4c.today_verdict missing {req}")
        if isinstance(tv.get("key_takeaways"), list) and len(tv["key_takeaways"]) < 3:
            warnings.append("_phase4c.today_verdict.key_takeaways should have ≥ 3 entries")
        if isinstance(tv.get("sector_actions"), list) and len(tv["sector_actions"]) < 3:
            warnings.append("_phase4c.today_verdict.sector_actions should have ≥ 3 entries")

    if errors:
        fail(errors)

    for w in warnings:
        print(f"[validate_sector_intel] ⚠ {w}", file=sys.stderr)

    hot = summary.get("hot_sectors", [])
    cold = summary.get("cold_sectors", [])
    print(f"[validate_sector_intel] ✓ {EXPECTED_VERSION} schema compliant — "
          f"{len(sectors)} sectors, {len(hot)} HOT / {len(cold)} COLD, fanout={fm}")
    sys.exit(0)


if __name__ == "__main__":
    main()

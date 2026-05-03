#!/usr/bin/env python3
"""
Validate the most recent `history.json` entry against the Phase 5 schema
documented in `investment/phase5_export_schema.md`.

Invocation (from protocol Phase 5 末尾):
    python3 investment/scripts/validate_session_export.py
        rc=0  → pass
        rc=1  → schema drift detected — see stderr for specifics

What this catches (main failure modes seen in production):
  1. Legacy flat shape `{ticker, metadata:{}}` without `trades_this_session`
  2. Missing `session_export_version` or wrong version
  3. HOLD/CANCEL sessions that omit observation fields (watch_conditions,
     macro_alignment, fragility_label, time_horizon, binary_classification,
     trade_metadata) — these are REQUIRED regardless of decision
  4. BUY / STAGED_ENTRY with null `risk_reward_ratio` (should be ≥ 2.0)

Does NOT validate analysis quality — only schema compliance.
"""
import json
import os
import sys

ROOT         = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HISTORY_JSON = os.path.join(ROOT, "investment/invest_logs/history.json")
# V5.0+: accept V4.8 (legacy) and V5.0 (current) — V4.8 lives until pre-V5.0 entries decay
ACCEPTED_VERSIONS = ("V4.8", "V5.0")
CURRENT_VERSION   = "V5.0"

TOP_REQUIRED = [
    "session_export_version", "export_date", "ticker", "final_action",
    "phase0_macro_snapshot", "trades_this_session",
    "active_weights_end_of_session", "bias_notes", "last_outcome",
]

TRADE_REQUIRED = [
    # identity + decision
    "ticker", "final_action", "final_decision", "final_score",
    # Phase 3 provenance
    "consensus_bonus_applied", "macro_alignment", "avg_confidence",
    # Red Team (V4.7+)
    "red_team_verdict", "red_team_counter_thesis", "red_team_kill_conditions",
    "red_team_execution_failed",
    # Phase 2 fan-out (V4.8)
    "phase2_fanout_mode", "degraded_analysts",
    # Burry
    "burry_score", "burry_override_active", "burry_override_recheck_date",
    # Trade plan (HOLD may have nulls, but keys must exist)
    "entry_aggressive", "entry_conservative", "take_profit", "stop_loss",
    "risk_reward_ratio", "position_size_pct", "staged_split", "position_size_method",
    # Observation fields — MUST be filled even for HOLD / CANCEL
    "fragility_label", "binary_classification", "time_horizon",
    "macro_context", "watch_conditions", "key_risks", "devils_advocate_filed",
    "trade_metadata",
    # Price snapshot at decision time (V4.8+)
    "analysis_price",
]

# V5.0+ additional required fields (only enforced when entry is V5.0)
TRADE_REQUIRED_V5 = [
    "valuation_lane",       # 5th lane (Valuation Specialist) output
    "fair_value_summary",   # Phase 4.5 deterministic anchor blend
]


def fail(errors):
    print("[validate_session_export] ✗ schema drift:", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    print(
        "\nFix: rewrite the last history.json entry to match "
        "investment/phase5_export_schema.md then re-run this validator.",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    if not os.path.exists(HISTORY_JSON):
        fail([f"history.json not found at {HISTORY_JSON}"])

    with open(HISTORY_JSON, "r", encoding="utf-8") as fp:
        hist = json.load(fp)

    if not isinstance(hist, list) or not hist:
        fail(["history.json is empty or not a JSON array"])

    entry = hist[-1]
    errors = []

    # ── 1. Legacy shape detection ────────────────────────────────────────
    is_legacy_flat = (
        "trades_this_session" not in entry
        and "metadata" in entry
        and isinstance(entry.get("metadata"), dict)
    )
    if is_legacy_flat:
        fail([
            "DETECTED LEGACY V4.3 SHAPE `{ticker, metadata:{}}` — forbidden in V4.8.",
            "The new entry must wrap trade fields in `trades_this_session[0]` and "
            "include `session_export_version`, `phase0_macro_snapshot`, etc.",
            "See investment/phase5_export_schema.md → FULL EXAMPLE.",
        ])

    # ── 2. Version check ─────────────────────────────────────────────────
    ver = entry.get("session_export_version")
    if ver not in ACCEPTED_VERSIONS:
        errors.append(f"session_export_version = {ver!r}, expected one of {ACCEPTED_VERSIONS}")

    # ── 3. Top-level required keys ───────────────────────────────────────
    for k in TOP_REQUIRED:
        if k not in entry:
            errors.append(f"missing top-level key: {k}")

    # ── 4. trades_this_session structure ─────────────────────────────────
    trades = entry.get("trades_this_session")
    if not isinstance(trades, list) or not trades:
        errors.append("trades_this_session must be a non-empty array")
        fail(errors)

    trade = trades[0]
    if not isinstance(trade, dict):
        errors.append("trades_this_session[0] must be an object")
        fail(errors)

    # ── 5. Required trade keys ───────────────────────────────────────────
    for k in TRADE_REQUIRED:
        if k not in trade:
            errors.append(f"trades_this_session[0]: missing key {k}")

    # V5.0+ requires fair_value_summary + valuation_lane
    if ver == "V5.0":
        for k in TRADE_REQUIRED_V5:
            if k not in trade:
                errors.append(f"trades_this_session[0]: missing V5.0 key {k}")
        # Validate fair_value_summary structure
        fvs = trade.get("fair_value_summary")
        if isinstance(fvs, dict):
            for k in ("anchors", "weighted_fair_value", "current_price",
                      "vs_current_pct", "verdict_band", "confidence", "anchors_available"):
                if k not in fvs:
                    errors.append(f"fair_value_summary: missing key {k}")
            vb = fvs.get("verdict_band")
            if vb not in (None, "extreme_undervalued", "undervalued", "fairly_valued",
                          "overvalued", "extreme_overvalued"):
                errors.append(f"fair_value_summary.verdict_band invalid: {vb!r}")
            conf = fvs.get("confidence")
            if conf not in (None, "high", "medium", "low"):
                errors.append(f"fair_value_summary.confidence invalid: {conf!r}")
        # Validate valuation_lane structure
        vl = trade.get("valuation_lane")
        if isinstance(vl, dict):
            for k in ("signal", "score", "confidence"):
                if k not in vl:
                    errors.append(f"valuation_lane: missing key {k}")
        # Validate active_weights includes Valuation
        weights = entry.get("active_weights_end_of_session") or {}
        if "Valuation" not in weights:
            errors.append("active_weights_end_of_session: missing Valuation weight (V5.0 5-lane requirement)")

    # ── 6. Observation fields must be non-null even for HOLD ─────────────
    for k in ("macro_alignment", "fragility_label", "binary_classification",
              "time_horizon", "trade_metadata"):
        if trade.get(k) in (None, ""):
            errors.append(f"trades_this_session[0].{k} must be non-null (required for all decisions, including HOLD/CANCEL)")

    wc = trade.get("watch_conditions")
    if not isinstance(wc, dict) or len(wc) < 3:
        errors.append(f"trades_this_session[0].watch_conditions must be an object with ≥ 3 trigger entries (got: {type(wc).__name__} len={len(wc) if isinstance(wc, dict) else 0})")

    # ── 7. BUY / STAGED_ENTRY must have R/R ≥ 2.0 ────────────────────────
    fd = trade.get("final_decision")
    rr = trade.get("risk_reward_ratio")
    if fd in ("BUY", "STAGED_ENTRY"):
        if rr is None:
            errors.append(f"final_decision={fd} requires risk_reward_ratio (non-null, ≥ 2.0)")
        elif isinstance(rr, (int, float)) and rr < 2.0:
            errors.append(f"final_decision={fd} but risk_reward_ratio={rr} < 2.0 — auto-REJECT would fire")

    # ── 8. Consistency between top-level mirror fields ───────────────────
    if entry.get("ticker") != trade.get("ticker"):
        errors.append(f"top-level ticker ({entry.get('ticker')!r}) differs from trades_this_session[0].ticker ({trade.get('ticker')!r})")
    if entry.get("final_action") != trade.get("final_action"):
        errors.append(f"top-level final_action ({entry.get('final_action')!r}) differs from trades_this_session[0].final_action ({trade.get('final_action')!r})")

    if errors:
        fail(errors)

    ticker = trade.get("ticker", "?")
    decision = trade.get("final_decision", "?")
    print(f"[validate_session_export] ✓ {ver} schema compliant — {ticker} / {decision}")
    sys.exit(0)


if __name__ == "__main__":
    main()

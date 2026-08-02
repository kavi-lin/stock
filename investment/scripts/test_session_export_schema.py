#!/usr/bin/env python3
"""test_session_export_schema.py — V4.81.0 schema-version gate contract.

What this locks down, in order of how easily it rots:

1. **The doc is the fixture.** Every case is built from the `FULL EXAMPLE` block in
   `phase5_export_schema.md`, so an example that drifts out of schema compliance turns
   this test red instead of silently teaching the next Phase 5 export a broken shape.
   (It has drifted before: through v4.80.1 the header said V5.0 while the JSON stamped
   `V4.8` and carried `valuation_lane` — copying it verbatim tripped the §2b guard.)

2. **The version gate cuts both ways.** A `V5.1` entry missing either half of the engine
   block fails; the same entry stamped `V5.0` and dated before the cutover passes. That
   asymmetry is the whole point of keying on schema version rather than `export_date` —
   backfilling an old analysis must not be held to today's bar.

3. **The bypasses stay shut.** Three of them: stamp an old version to dodge the version
   gate (date backstop), stamp `V5.0` while carrying `decision_engine_version` (§2c),
   stamp `V4.8` while carrying V5.0-only fields (§2b).

4. **§13 catches lies, not just typos.** The tamper battery mutates a valid chain one
   field at a time — including the *labels* (`cascade_rule_applied`, polarization) and
   not only the arithmetic, since a mislabelled chain re-derives perfectly.

Usage:  python3 investment/scripts/test_session_export_schema.py
        rc=0 → contract holds;  rc=1 → see the failure list on stdout
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decision_engine import run_phase3  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCHEMA_MD = os.path.join(ROOT, "investment/phase5_export_schema.md")
VALIDATOR = os.path.join(ROOT, "investment/scripts/validate_session_export.py")

FAILS: list[str] = []

# The FULL EXAMPLE is what the PM writes; `det_shadow` is appended afterwards by
# apply_det_shadow.py (the doc marks it "post-processor 寫入，LLM 不寫"). Inject a block
# consistent with the example's lane scores so the fixture represents a post-processed
# entry — otherwise every case would fail on "det_shadow missing" instead of on the
# thing it is testing.
DET_SHADOW = {
    "version": "V3.45.4",
    "signal_polarization": "ALIGNED",
    "polarization_detail": {"label": "ALIGNED", "range": 3.0, "max": 4.0, "min": 1.0,
                            "pos_strong": 5, "neg_strong": 0, "missing_lanes": []},
    "valuation_score_det": 1.0,
    "val_agreement": "AGREE",
    "valuation_source": "valuation_pack",
    "red_team_verdict_det": "STRONG_COUNTER",
    "red_team_agreement": "AGREE",
    "red_team_basis": "unclassified",
    "news_pt_leakage": False,
}


def extract_full_example() -> dict:
    text = open(SCHEMA_MD, encoding="utf-8").read()
    start = text.index("## FULL EXAMPLE")
    fence = text.index("```json", start) + len("```json")
    end = text.index("```", fence)
    entry = json.loads(text[fence:end])
    entry["trades_this_session"][0].setdefault("det_shadow", copy.deepcopy(DET_SHADOW))
    return entry


def run(entry: dict, label: str, want_rc: int, want_substr: str | None = None) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as fp:
        json.dump([entry], fp, ensure_ascii=False)
        path = fp.name
    try:
        p = subprocess.run([sys.executable, VALIDATOR, "--history", path],
                           capture_output=True, text=True)
        out = (p.stdout + p.stderr).strip()
        if p.returncode != want_rc:
            FAILS.append(f"{label}: rc={p.returncode}, want {want_rc}\n      {out[:300]}")
        elif want_substr and want_substr not in out:
            FAILS.append(f"{label}: rc ok but message missing {want_substr!r}\n      {out[:300]}")
        else:
            print(f"  ok  {label} (rc={p.returncode})")
    finally:
        os.unlink(path)


def without(entry: dict, *keys: str) -> dict:
    e = copy.deepcopy(entry)
    for k in keys:
        e["trades_this_session"][0].pop(k, None)
    return e


# The doc example is a *penalised* chain (rule_5 × 0.95), so it can only exercise the
# penalty half of the cascade-label check. Generate the bonus half from the engine rather
# than hand-writing it — a hardcoded chain would go stale the moment the rules move.
BONUS_INPUT = {
    "ticker": "MU",
    "lane_scores": {"fundamentals": 4.0, "sentiment": 3.0, "news": 3.0,
                    "technical": 4.0, "valuation": 1.0},
    "lane_confidence": {"fundamentals": 0.8, "sentiment": 0.75, "news": 0.7,
                        "technical": 0.8, "valuation": 0.7},
    "structural_shift": {"tier": "NONE"},
    "red_team": {"verdict": "NO_VIABLE_COUNTER", "basis": "unclassified"},
    "macro": {"macro_multiplier": 0.9, "macro_backdrop_score": -1.0, "market_regime": "RISK_ON"},
    "burry": {"score": 37.1, "veto_flag": False},
    "gates": {"proceed_to_phase3": True, "mandatory_risk_flags": [],
              "phase2_fanout_mode": "PARALLEL_SUBAGENT", "risk_reward_ratio": 2.13},
    "hot_zone": {"industry_top_30pct": True},
    "decision_cap": {"anchors_available": 6, "fair_value_confidence": "high",
                     "lane_data_quality_low": False},
}


def bonus_entry(ex: dict) -> dict:
    """The doc example re-scored as a consensus-bonus chain (engine output spliced in)."""
    r = run_phase3(copy.deepcopy(BONUS_INPUT))
    e = copy.deepcopy(ex)
    tr = e["trades_this_session"][0]
    tr["calculation_steps"] = r["calculation_steps"]
    tr["decision_engine_version"] = r["decision_engine_version"]
    for k in ("final_score", "final_decision", "avg_confidence", "hot_zone_probe",
              "hot_zone_eval", "decision_cap_active"):
        if k in r:
            tr[k] = r[k]
    tr["consensus_bonus_applied"] = r["calculation_steps"].get("bonus_applied", False)
    return e


def main() -> int:
    ex = extract_full_example()
    ver = ex.get("session_export_version")
    print(f"[fixture] phase5_export_schema.md FULL EXAMPLE — version={ver!r}")
    if ver != "V5.1":
        FAILS.append(f"FULL EXAMPLE stamps {ver!r}; the doc's Schema Version is V5.1")

    print("[version gate]")
    run(ex, "V5.1 full example", 0)
    run(without(ex, "calculation_steps", "decision_engine_version"),
        "V5.1 minus calculation_steps", 1, "calculation_steps missing")
    run(without(ex, "decision_engine_version"),
        "V5.1 minus decision_engine_version", 1, "decision_engine_version missing")

    # Back-compat: the 78 pre-existing V5.0 entries must never need a backfill.
    legacy = without(ex, "calculation_steps", "decision_engine_version")
    legacy["session_export_version"] = "V5.0"
    run(legacy, "V5.0 legacy, pre-cutover, no engine block", 0)

    print("[bypass guards]")
    # Backstop: stamping an old version after the cutover must not open the gate.
    e = copy.deepcopy(legacy)
    e["export_date"] = e["date"] = "2026-08-05"
    run(e, "V5.0 stamp after cutover (date backstop)", 1, "2026-08-03")

    e = copy.deepcopy(ex)
    e["session_export_version"] = "V5.0"
    run(e, "V5.0 stamp carrying decision_engine_version (§2c)", 1,
        "entry carries decision_engine_version")

    e = copy.deepcopy(ex)
    e["session_export_version"] = "V4.8"
    run(e, "V4.8 stamp carrying V5.0-only fields (§2b)", 1, "stamping bug")

    e = copy.deepcopy(ex)
    e["session_export_version"] = "V5.2"
    run(e, "unknown version rejected", 1, "expected one of")

    # ── §13 tamper battery ──────────────────────────────────────────────────
    # NB on the band cases: banded-BUY → HOLD is a *legal* path (Auto REJECT / decision
    # cap), so the out-of-band tamper has to claim BUY off a below-threshold chain.
    tampers = [
        ("step product wrong",
         lambda tr: tr["calculation_steps"].__setitem__("fund", "0.25 × 4 × 0.72 = 0.9000")),
        ("raw_total wrong",
         lambda tr: tr["calculation_steps"].__setitem__("raw_total", 3.0)),
        ("raw_after_bonus wrong",
         lambda tr: tr["calculation_steps"].__setitem__("raw_after_bonus", 2.5)),
        ("final_score mirror drift",
         lambda tr: tr.__setitem__("final_score", 1.9)),
        ("penalty_value off the rule table",
         lambda tr: tr["calculation_steps"].__setitem__("penalty_value", 0.77)),
        ("cascade label vs penalty_applied",
         lambda tr: tr["calculation_steps"].__setitem__("cascade_rule_applied", "no_penalty")),
        ("C_eff not quantised",
         lambda tr: tr["calculation_steps"].__setitem__("fund", "0.25 × 4 × 0.69 = 0.6900")),
        ("threshold off the matrix",
         lambda tr: tr["calculation_steps"]["dynamic_threshold"].__setitem__("buy_threshold", 0.5)),
        ("effective_macro_mult ignores floor",
         lambda tr: tr["calculation_steps"].__setitem__("effective_macro_mult", 1.2)),
        ("polarization label lie",
         lambda tr: tr["calculation_steps"]["polarization_modulation"].__setitem__("label", "BIPOLAR")),
        ("decision above band", lambda tr: (
            tr["calculation_steps"].__setitem__(
                "dynamic_threshold", {"buy_threshold": 2.5, "staged_threshold": 2.0,
                                      "rationale": "tampered"}),
            tr.__setitem__("final_decision", "BUY"))),
    ]
    print("[§13 tamper battery]")
    for name, mutate in tampers:
        e = copy.deepcopy(ex)
        mutate(e["trades_this_session"][0])
        run(e, f"tamper: {name}", 1)

    # ── cascade label, bonus side ───────────────────────────────────────────
    # Mirror of "cascade label vs penalty_applied". Relabelling a ×1.15 consensus chain
    # `no_penalty` leaves both the arithmetic and `bonus_applied` intact, so only the
    # label check can catch it — it passed until V4.81.0.
    print("[cascade label — bonus side]")
    bonus = bonus_entry(ex)
    bcs = bonus["trades_this_session"][0]["calculation_steps"]
    if bcs.get("bonus_applied") is not True or bcs.get("cascade_rule_applied") != "consensus_bonus":
        FAILS.append("bonus fixture: engine did not produce a consensus_bonus chain "
                     f"(bonus_applied={bcs.get('bonus_applied')!r}, "
                     f"rule={bcs.get('cascade_rule_applied')!r})")
    run(bonus, "consensus_bonus chain (engine output)", 0)

    e = copy.deepcopy(bonus)
    e["trades_this_session"][0]["calculation_steps"]["cascade_rule_applied"] = "no_penalty"
    run(e, "tamper: bonus chain relabelled no_penalty", 1, "bonus_applied=true")

    e = copy.deepcopy(bonus)
    e["trades_this_session"][0]["calculation_steps"]["bonus_applied"] = False
    run(e, "tamper: consensus_bonus label without the flag", 1, "bonus_applied=False")

    print()
    if FAILS:
        print(f"✗ {len(FAILS)} failure(s):")
        for f in FAILS:
            print("  - " + f)
        return 1
    print("✓ session export schema contract holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())

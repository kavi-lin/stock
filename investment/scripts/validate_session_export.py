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
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_det_shadow import compute_polarization  # noqa: E402
from decision_engine import compute_dynamic_threshold, decision_band  # noqa: E402

ROOT         = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HISTORY_JSON = os.path.join(ROOT, "investment/invest_logs/history.json")
# Accepted schema versions, oldest → newest. V4.8 (4-lane legacy) lives until pre-V5.0
# entries decay; V5.0 opened the 5-lane era; V5.1 makes the Phase 3 engine block mandatory;
# V5.2 does the same for the Phase 4 engine block.
ACCEPTED_VERSIONS = ("V4.8", "V5.0", "V5.1", "V5.2")
CURRENT_VERSION   = "V5.2"
# 5-lane era — valuation_lane / fair_value_summary required, Rec 11 + MHP instrumented.
V5_VERSIONS = ("V5.0", "V5.1", "V5.2")
# Versions whose entries MUST carry the Phase 3 engine output (`calculation_steps` +
# `decision_engine_version`). Version-keyed rather than date-keyed so a backfilled entry
# stamped V5.1 is held to exactly the same bar as one exported today.
CALC_STEPS_REQUIRED_VERSIONS = ("V5.1", "V5.2")
# Versions whose entries MUST carry the Phase 4 engine output (`risk_audit` +
# `trade_plan_builder_version` + `mandatory_risk_flags`). Same version-keyed discipline.
RISK_AUDIT_REQUIRED_VERSIONS = ("V5.2",)

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

# V5.0+ additional required fields (only enforced when entry is in V5_VERSIONS)
TRADE_REQUIRED_V5 = [
    "valuation_lane",       # 5th lane (Valuation Specialist) output
    "fair_value_summary",   # Phase 4.5 deterministic anchor blend
]

# V2.14.0+ optional thesis lifecycle fields (Phase 5.5 trader-memory-core register)
# Not in TRADE_REQUIRED — protocol may skip register step gracefully.
TRADE_OPTIONAL_THESIS = ("thesis_id", "thesis_registered_at")


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


def _same_number(a, b, tol=0.011):
    return (isinstance(a, (int, float)) and not isinstance(a, bool)
            and isinstance(b, (int, float)) and not isinstance(b, bool)
            and abs(float(a) - float(b)) <= tol)


def _numf(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return float(x)


# V4.80.0 §13 — Phase 3 arithmetic re-derivation
_STEP_RE = re.compile(
    r"^\s*([\d.]+)\s*×\s*([+\-−–]?[\d.]+)\s*×\s*([\d.]+)\s*=\s*([+\-−–]?[\d.]+)")
_STEP_LANES = {"fund": "fundamentals", "sent": "sentiment", "news": "news",
               "tech": "technical", "val": "valuation"}
_CASCADE_PENALTY = {
    "rule_1_paradigm_confirmed_mr_downgrade": (0.925,),
    "rule_2_transition_signature_mr_soften": (0.95,),
    "rule_3_paradigm_candidate": (0.925,),
    "rule_4_pure_forward": (0.85, 0.925),
    "rule_5_default_strong_counter": (0.95,),
}
_KNOWN_MULTIPLIERS = (1.0, 1.15, 0.85, 0.925, 0.95)

# §13 must not be bypassable by simply omitting the block. The primary gate is now
# version-keyed (CALC_STEPS_REQUIRED_VERSIONS); this date threshold stays as the backstop
# that catches the mis-stamp bypass — an entry exported after the cutover but stamped with
# an older version precisely to dodge the version gate.
CALC_STEPS_REQUIRED_FROM = "2026-08-03"


def _dash(s):
    return float(str(s).replace("−", "-").replace("–", "-"))


def check_phase3_arithmetic(entry, trade, errors, warnings):
    """Re-derive the Phase 3 chain from the exported `calculation_steps`.

    Tier A (any entry carrying calculation_steps) — timeless arithmetic: each Step 1
    product, their sum, the bonus/penalty multiplication, the macro step, the threshold
    formula, and the decision band. These catch a hand-written or hallucinated number
    regardless of which rule version produced the entry.

    Tier B (entries stamped `decision_engine_version`) — rule-table conformance that only
    holds for V4.70.0+ math: C_eff quantisation, cascade→penalty mapping, the dynamic
    threshold matrix, and the mandatory Rec 11 instrumentation.

    Entries with neither block are skipped entirely (pre-V4.80.0 back-compat, rc=0) —
    unless the entry is stamped a version in CALC_STEPS_REQUIRED_VERSIONS, where both
    blocks are mandatory and their absence is rc=1.
    """
    cs = trade.get("calculation_steps")
    engine_ver = trade.get("decision_engine_version")
    ver = entry.get("session_export_version")
    _ENGINE_CMD = ("`python3 investment/scripts/decision_engine.py --from-file "
                   "/tmp/<T>_p3.json` 的 calculation_steps 整塊 verbatim 抄寫")
    if not isinstance(cs, dict):
        if engine_ver:
            errors.append(
                f"decision_engine_version={engine_ver!r} present but calculation_steps is "
                "missing — the engine emits both; do not hand-assemble the Phase 3 block")
        elif ver in CALC_STEPS_REQUIRED_VERSIONS:
            errors.append(
                f"calculation_steps missing — session_export_version={ver!r} 的 entry 必須帶 "
                f"Phase 3 engine 輸出（{_ENGINE_CMD}）。省略此欄等同繞過 §13 算術硬閘")
        elif (entry.get("export_date") or entry.get("date") or "") >= CALC_STEPS_REQUIRED_FROM:
            errors.append(
                f"calculation_steps missing — {CALC_STEPS_REQUIRED_FROM} 起的 entry 必須帶 "
                f"Phase 3 engine 輸出（{_ENGINE_CMD}）。省略此欄等同繞過 §13 算術硬閘")
        return

    # V5.1+ — the engine stamp is required alongside the block, so Tier B (rule-table
    # conformance) can never be skipped by exporting calculation_steps unstamped.
    if ver in CALC_STEPS_REQUIRED_VERSIONS and not engine_ver:
        errors.append(
            f"decision_engine_version missing — session_export_version={ver!r} 的 entry 必須連 "
            "engine 版號一起抄（engine 兩者同時輸出）；缺版號會讓 §13 Tier B 規則表驗證整段跳過")

    # ── Tier A.1 — Step 1 products and their sum ─────────────────────────────
    lane_scores, ceffs, contribs = {}, {}, []
    for key, lane in _STEP_LANES.items():
        raw = cs.get(key)
        if not isinstance(raw, str):
            errors.append(f"calculation_steps.{key} must be the engine's step string, got {raw!r}")
            continue
        m = _STEP_RE.match(raw)
        if not m:
            if "MISSING" in raw:
                errors.append(
                    f"calculation_steps.{key}: lane input missing ({raw!r}) — Phase 3 需要"
                    "五個 lane 都有 score 與 confidence（權重不重分配）。先補 Phase 2 "
                    "fan-in/inline fallback 再重跑 decision_engine.py，不要匯出殘缺的鏈")
            else:
                errors.append(f"calculation_steps.{key} unparseable: {raw!r} "
                              "(expected 'W × score × C_eff = result')")
            continue
        w, s, ce, res = (_dash(m.group(1)), _dash(m.group(2)),
                         _dash(m.group(3)), _dash(m.group(4)))
        if abs(w * s * ce - res) > 5e-4:
            errors.append(f"calculation_steps.{key}: {w} × {s} × {ce} = {w * s * ce:.4f}, "
                          f"but the entry states {res} — Phase 3 手算，重跑 decision_engine.py")
        lane_scores[lane], ceffs[lane] = s, ce
        contribs.append(res)

    raw_total = _numf(cs.get("raw_total"))
    if raw_total is not None and len(contribs) == len(_STEP_LANES):
        if abs(sum(contribs) - raw_total) > 5e-4:
            errors.append(f"calculation_steps.raw_total={raw_total} != Σ lane contributions "
                          f"{sum(contribs):.4f}")

    # ── Tier A.2 — bonus / penalty multiplication ────────────────────────────
    rab = _numf(cs.get("raw_after_bonus"))
    pv = _numf(cs.get("penalty_value"))
    rule = cs.get("cascade_rule_applied") or cs.get("penalty_rule")
    if raw_total is not None and rab is not None:
        if cs.get("bonus_applied") is True:
            expected = 1.15
        elif cs.get("penalty_applied") is True:
            expected = pv
        else:
            expected = 1.0
        if expected is None:
            ratio = rab / raw_total if raw_total else None
            if ratio is None or not any(abs(ratio - k) <= 1e-3 for k in _KNOWN_MULTIPLIERS):
                errors.append(
                    f"calculation_steps: penalty_applied=true but penalty_value missing and the "
                    f"implied multiplier {ratio} is not one of {_KNOWN_MULTIPLIERS}")
        elif abs(raw_total * expected - rab) > 5e-4:
            errors.append(f"calculation_steps.raw_after_bonus={rab} != raw_total {raw_total} "
                          f"× {expected}")

    # ── Tier A.3 — macro step ────────────────────────────────────────────────
    mm = _numf(cs.get("macro_multiplier"))
    floor = _numf((cs.get("structural_shift_modulation") or {}).get("shift_macro_floor"))
    eff = _numf(cs.get("effective_macro_mult"))
    if mm is not None and floor is not None and eff is not None:
        if abs(max(mm, floor) - eff) > 1e-6:
            errors.append(f"calculation_steps.effective_macro_mult={eff} != "
                          f"max(macro_multiplier {mm}, shift_macro_floor {floor})")
    align = cs.get("macro_alignment")
    backdrop = _numf((entry.get("phase0_macro_snapshot") or {}).get("macro_backdrop_score"))
    if rab is not None and backdrop is not None and align in ("ALIGNED", "CONTRARIAN"):
        _sgn = lambda v: (1 if v > 0 else (-1 if v < 0 else 0))  # noqa: E731
        same = _sgn(rab) == _sgn(backdrop)   # spec-literal, matches decision_engine.compute_step3
        if same != (align == "ALIGNED"):
            errors.append(
                f"calculation_steps.macro_alignment={align} contradicts sign(raw_after_bonus "
                f"{rab}) vs sign(macro_backdrop_score {backdrop})")
    fs_cs = _numf(cs.get("final_score"))
    if rab is not None and eff is not None and fs_cs is not None and align:
        expected_fs = rab * eff if align == "ALIGNED" else rab
        if abs(expected_fs - fs_cs) > 5e-4:
            errors.append(f"calculation_steps.final_score={fs_cs} != {expected_fs:.4f} "
                          f"(raw_after_bonus × effective_macro_mult under {align})")
    if fs_cs is not None and not _same_number(fs_cs, trade.get("final_score"), tol=5e-4):
        errors.append(f"trades_this_session[0].final_score={trade.get('final_score')} != "
                      f"calculation_steps.final_score={fs_cs}")

    # ── Tier A.4 — threshold formula, polarization label, decision band ──────
    dt = cs.get("dynamic_threshold") or {}
    buy, staged = _numf(dt.get("buy_threshold")), _numf(dt.get("staged_threshold"))
    if buy is not None and staged is not None:
        if abs(max(0.6, round(buy - 0.4, 10)) - staged) > 1e-6:
            errors.append(f"dynamic_threshold.staged_threshold={staged} != "
                          f"max(0.6, buy_threshold {buy} − 0.4)")

    polar = cs.get("polarization_modulation") or {}
    if len(lane_scores) == len(_STEP_LANES) and polar.get("label"):
        recomputed = compute_polarization(lane_scores, lane_scores.get("valuation"))
        if recomputed.get("label") and recomputed["label"] != polar.get("label"):
            errors.append(
                f"polarization_modulation.label={polar.get('label')!r} but the lane scores in "
                f"calculation_steps recompute to {recomputed['label']!r}")
        for fld, key in (("lane_range", "range"), ("pos_strong", "pos_strong"),
                         ("neg_strong", "neg_strong")):
            got, want = polar.get(fld), recomputed.get(key)
            if got is not None and want is not None and not _same_number(got, want, tol=1e-6):
                errors.append(f"polarization_modulation.{fld}={got} != recomputed {want}")

    fd = trade.get("final_decision")
    if fs_cs is not None and buy is not None and staged is not None and fd:
        banded = decision_band(fs_cs, buy, staged)
        allowed = {banded}
        if banded == "BUY" and polar.get("label") == "BIPOLAR":
            allowed.add("STAGED_ENTRY")          # Step 1.7 forced downgrade
        if banded == "BUY" and trade.get("decision_cap_active") is True \
                and trade.get("cap_override_reason"):
            allowed.add("STAGED_ENTRY")          # Phase 4.6 cap + override（不退到 HOLD）
        if banded in ("BUY", "STAGED_ENTRY"):
            allowed.add("HOLD")                  # Auto REJECT / decision cap
        if banded == "HOLD" and trade.get("hot_zone_probe") is True:
            allowed.add("STAGED_ENTRY")          # Rec 11 probe
        if fd not in allowed:
            errors.append(
                f"final_decision={fd!r} is not reachable from final_score {fs_cs} with "
                f"buy={buy}/staged={staged} (band → {banded}, allowed {sorted(allowed)})")

    # ── Tier B — rule-table conformance (V4.70.0+ entries only) ──────────────
    if not engine_ver:
        return
    for lane, ce in ceffs.items():
        if ce not in (0.35, 0.60, 0.72):
            errors.append(f"calculation_steps: {lane} C_eff={ce} outside the V4.70.0 "
                          "three-tier set (0.35/0.60/0.72)")
    if rule in _CASCADE_PENALTY:
        allowed_pv = _CASCADE_PENALTY[rule]
        if pv is None:
            errors.append(f"cascade_rule_applied={rule!r} requires penalty_value "
                          f"(one of {allowed_pv})")
        elif not any(abs(pv - k) <= 1e-9 for k in allowed_pv):
            errors.append(f"cascade_rule_applied={rule!r} implies penalty_value in "
                          f"{allowed_pv}, got {pv}")
    elif rule not in (None, "no_penalty", "consensus_bonus"):
        warnings.append(f"cascade_rule_applied={rule!r} is not a known V4.70.0 cascade rule")
    # V4.81.0 — the label must agree with what the chain actually did, in both
    # directions and on both sides. Without this, relabelling a penalised chain
    # `no_penalty` passes: the arithmetic still multiplies by 0.95, and the
    # rule→penalty_value table above only fires on rule_* names. Tier A.2 treats
    # bonus/penalty as mutually exclusive branches (bonus wins), so each flag pins
    # exactly one label family.
    if cs.get("penalty_applied") is True and rule in (None, "no_penalty", "consensus_bonus"):
        errors.append(
            f"calculation_steps: penalty_applied=true but cascade_rule_applied={rule!r} — "
            "a penalised chain must name the rule that penalised it (rule_1..5_*)")
    if cs.get("penalty_applied") is not True and rule in _CASCADE_PENALTY:
        errors.append(
            f"calculation_steps: cascade_rule_applied={rule!r} is a penalty rule but "
            f"penalty_applied={cs.get('penalty_applied')!r}")
    if cs.get("bonus_applied") is True and rule != "consensus_bonus":
        errors.append(
            f"calculation_steps: bonus_applied=true but cascade_rule_applied={rule!r} — "
            "a ×1.15 consensus chain must be labelled 'consensus_bonus'")
    if cs.get("bonus_applied") is not True and rule == "consensus_bonus":
        errors.append(
            "calculation_steps: cascade_rule_applied='consensus_bonus' but "
            f"bonus_applied={cs.get('bonus_applied')!r}")

    tier = (cs.get("structural_shift_modulation") or {}).get("tier")
    if polar.get("label") and buy is not None:
        want = compute_dynamic_threshold(tier, polar.get("label"))
        if abs(want["buy_threshold"] - buy) > 1e-9:
            errors.append(
                f"dynamic_threshold.buy_threshold={buy} but tier={tier!r} × "
                f"polarization={polar.get('label')!r} maps to {want['buy_threshold']}")
    if trade.get("hot_zone_eval") is None:
        errors.append("hot_zone_eval missing — TODO-015 要求每筆 engine-scored deep-dive 必填")


# ---------------------------------------------------------------------------
# V4.82.0 §14 — Phase 4 sizing-chain re-derivation (trade_plan_builder parity)
# ---------------------------------------------------------------------------
_FRAGILITY_MULT = {"ROBUST": 1.0, "MODERATE": 0.75, "FRAGILE": 0.5}
_MACRO_CAP_LIMIT = 0.03
_MACRO_CAP_TRIGGER = -3.0
# (stage, sector_class) → (multiplier, stop_loss_adjustment_pp)
_FTD_TABLE = {
    ("prime", "cyclical"): (1.00, 0), ("prime", "defensive"): (1.00, 0),
    ("standard", "cyclical"): (0.90, 0), ("standard", "defensive"): (1.00, 0),
    ("late_cycle", "cyclical"): (0.75, -1), ("late_cycle", "defensive"): (0.95, 0),
    ("exhausted", "cyclical"): (0.50, -2), ("exhausted", "defensive"): (0.85, 0),
}
_HZ_TIER_CAPS = {"t1_15bps": 0.0015, "t2_30bps": 0.003}


def _chain_step(chain, prev_key, key, factor, label, errors):
    """One multiplicative link of the Step 4 chain: chain[key] == chain[prev_key] × factor."""
    prev, got = _numf(chain.get(prev_key)), _numf(chain.get(key))
    if prev is None or got is None or factor is None:
        return
    want = prev * factor
    # The engine rounds each stage to 6dp, so the tolerance has to clear one rounding
    # step at each end rather than assume exact equality.
    if abs(want - got) > 1.5e-6:
        errors.append(f"sizing_chain.{key}={got} != {prev_key} {prev} × {label} {factor} "
                      f"= {want:.8f} — Phase 4 手算，重跑 trade_plan_builder.py")


def check_phase4_sizing(entry, trade, errors, warnings):
    """Re-derive the Phase 4 sizing chain from the exported `risk_audit`.

    Tier A (any entry carrying sizing_chain) — timeless arithmetic: each multiplicative
    link, the macro cap's min() semantics, the STAGED halving, and agreement between the
    chain tail and the exported `position_size_pct`.

    Tier B (entries stamped `trade_plan_builder_version`) — rule-table conformance that
    only holds for V4.82.0+ math: the fragility table, the FTD stage × sector_class table,
    F1's two-valued multiplier, and the REJECTED ⇒ zero-size invariant.

    Entries with neither block are skipped entirely (pre-V4.82.0 back-compat, rc=0) —
    unless the entry is stamped a version in RISK_AUDIT_REQUIRED_VERSIONS, where the whole
    block is mandatory and its absence is rc=1.
    """
    ra = trade.get("risk_audit")
    builder_ver = trade.get("trade_plan_builder_version")
    ver = entry.get("session_export_version")
    _CMD = ("`python3 investment/scripts/trade_plan_builder.py --from-file "
            "/tmp/<T>_p4.json` 的 trade_plan + risk_audit 整塊 verbatim 抄寫")

    if not isinstance(ra, dict):
        if builder_ver:
            errors.append(
                f"trade_plan_builder_version={builder_ver!r} present but risk_audit is "
                "missing — the engine emits both; do not hand-assemble the Phase 4 block")
        elif ver in RISK_AUDIT_REQUIRED_VERSIONS:
            errors.append(
                f"risk_audit missing — session_export_version={ver!r} 的 entry 必須帶 "
                f"Phase 4 engine 輸出（{_CMD}）。省略此欄等同繞過 §14 算術硬閘")
        return

    if ver in RISK_AUDIT_REQUIRED_VERSIONS:
        if not builder_ver:
            errors.append(
                f"trade_plan_builder_version missing — session_export_version={ver!r} 的 entry "
                "必須連 engine 版號一起抄（engine 兩者同時輸出）；缺版號會讓 §14 Tier B 規則表"
                "驗證整段跳過")
        if not isinstance(trade.get("mandatory_risk_flags"), list):
            errors.append(
                "mandatory_risk_flags missing or not an array — V5.2 起必填（正常情況空陣列）。"
                "此欄是 Phase 3 Auto REJECT 與 Rec 11 probe 抑制的輸入，缺它 replay 只能靠假設")

    chain = ra.get("sizing_chain")
    if not isinstance(chain, dict):
        if ver in RISK_AUDIT_REQUIRED_VERSIONS:
            errors.append("risk_audit.sizing_chain missing — §14 無法重算九段乘法鏈")
        return

    # ── Tier A.1 — fragility link ────────────────────────────────────────────
    label = ((ra.get("tail_risk") or {}).get("fragility_label"))
    frag_mult = _FRAGILITY_MULT.get(label)
    _chain_step(chain, "base", "tail_adj", frag_mult, "fragility", errors)

    # ── Tier A.2 — macro cap is a min(), not a multiplication ────────────────
    backdrop = _numf((entry.get("phase0_macro_snapshot") or {}).get("macro_backdrop_score"))
    tail_adj, macro_cap = _numf(chain.get("tail_adj")), _numf(chain.get("macro_cap"))
    if tail_adj is not None and macro_cap is not None and backdrop is not None:
        want = min(tail_adj, _MACRO_CAP_LIMIT) if backdrop < _MACRO_CAP_TRIGGER else tail_adj
        if abs(want - macro_cap) > 1.5e-6:
            errors.append(
                f"sizing_chain.macro_cap={macro_cap} != {want:.8f} — macro_backdrop_score "
                f"{backdrop} {'<' if backdrop < _MACRO_CAP_TRIGGER else '≥'} "
                f"{_MACRO_CAP_TRIGGER} 時規則是 "
                f"{'min(tail_adj, 0.03)' if backdrop < _MACRO_CAP_TRIGGER else 'tail_adj 原值'}")

    # ── Tier A.3 — the remaining multiplicative links ───────────────────────
    _chain_step(chain, "macro_cap", "binary_adj", _numf(chain.get("binary_multiplier")),
                "binary", errors)
    _chain_step(chain, "binary_adj", "burry_override_adj",
                _numf(chain.get("burry_override_multiplier")), "burry_override", errors)
    ftd_mult = _numf((ra.get("ftd_timeline_gate") or {}).get("multiplier"))
    _chain_step(chain, "burry_override_adj", "ftd_adj", ftd_mult, "ftd_timeline", errors)
    f1_mult = _numf(chain.get("f1_multiplier"))
    if f1_mult is None:
        f1_mult = _numf((ra.get("sector_concentration_f1") or {}).get("multiplier"))
    _chain_step(chain, "ftd_adj", "f1_adj", f1_mult, "v20_f1", errors)

    # The two Phase 3 caps are percentages; they are mirrored on the trade so the chain
    # can be re-derived without re-reading the Phase 3 engine output.
    shift_cap = _numf((trade.get("calculation_steps") or {})
                      .get("structural_shift_modulation", {}).get("position_size_cap_pct"))
    polar_cap = _numf((trade.get("calculation_steps") or {})
                      .get("polarization_modulation", {}).get("position_cap_after"))
    if shift_cap is not None:
        _chain_step(chain, "f1_adj", "shift_adj", shift_cap / 100.0, "structural_shift_cap",
                    errors)
    if polar_cap is not None:
        _chain_step(chain, "shift_adj", "polar_adj", polar_cap / 100.0, "polarization_cap",
                    errors)

    # ── Tier A.4 — STAGED halving + chain tail vs exported size ─────────────
    fd = trade.get("final_decision")
    # The halving belongs to the decision Phase 4 SIZED against, not to whatever the
    # export finally says: Phase 4.6 runs after Phase 4 and can rewrite BUY → HOLD /
    # STAGED_ENTRY, at which point `final_decision` no longer explains the chain.
    # `sized_for_decision` is the engine's record of its own input (V4.86.0); older
    # entries fall back to `final_decision`, which is correct whenever no cap fired.
    sized_for = ra.get("sized_for_decision") or fd
    polar_adj, final_size = _numf(chain.get("polar_adj")), _numf(chain.get("final_position_size"))
    if polar_adj is not None and final_size is not None and sized_for:
        want = polar_adj * 0.5 if sized_for == "STAGED_ENTRY" else polar_adj
        if abs(want - final_size) > 1.5e-6:
            errors.append(
                f"sizing_chain.final_position_size={final_size} != {want:.8f} — "
                f"sized_for_decision={sized_for!r} "
                f"{'須折半 (× 0.5)' if sized_for == 'STAGED_ENTRY' else '不折半'}")

    size = _numf(trade.get("position_size_pct"))
    approval = ra.get("approval")
    probe_capped = ra.get("hot_zone_probe_capped") is True
    cap_on = trade.get("decision_cap_active") is True
    if size is not None and final_size is not None:
        # The exported size may sit BELOW the chain tail for exactly four reasons, in
        # precedence order. Anything else means the number was edited after the engine
        # produced it. Modelling these explicitly is what keeps the gate from rejecting
        # a legitimately-capped export.
        #
        # V4.86.0 — `decision_cap_active` was missing from this list, which made §14
        # reject every Phase 4.6 outcome: the cap runs AFTER Phase 4 sizing (protocol
        # §PHASE 4.6 / decision_engine.apply_decision_cap), clamps the size to 30bps and
        # may drop BUY to HOLD *while leaving a live probe-sized position*. Both of those
        # tripped the "not BUY-side ⇒ 0" and "size == chain tail" branches below.
        if approval == "REJECTED":
            if abs(size) > 1e-9:
                errors.append(f"position_size_pct={size} but approval=REJECTED — "
                              "被否決的計畫必須是 0 倉位")
        elif cap_on:
            # Phase 4.6 only ever reduces. §10 separately enforces the 30bps ceiling.
            if size > final_size + 1.5e-6:
                errors.append(
                    f"position_size_pct={size} > sizing_chain tail {final_size} with "
                    "decision_cap_active=true — Phase 4.6 cap 只會縮小倉位，不會放大")
        elif fd not in ("BUY", "STAGED_ENTRY"):
            if abs(size) > 1e-9:
                errors.append(
                    f"position_size_pct={size} but final_decision={fd!r} — "
                    "不可執行的決策必須是 0 倉位（除非 decision_cap_active=true，"
                    "Phase 4.6 允許 cap 後保留 ≤30bps 的試水倉）")
        elif probe_capped:
            if size > final_size + 1.5e-6:
                errors.append(f"position_size_pct={size} > sizing_chain tail {final_size} "
                              "even though hot_zone_probe_capped=true (cap 只會變小)")
        elif abs(size - final_size) > 1.5e-6:
            errors.append(
                f"position_size_pct={size} != sizing_chain.final_position_size={final_size} — "
                "兩者必須一致，除非 approval=REJECTED / decision_cap_active=true / "
                "hot_zone_probe_capped=true")

    # ── Tier B — rule-table conformance (V4.82.0+ entries only) ─────────────
    if not builder_ver:
        return

    if label not in _FRAGILITY_MULT:
        errors.append(
            f"risk_audit.tail_risk.fragility_label={label!r} outside the protocol set "
            f"{sorted(_FRAGILITY_MULT)} — Step 3 表只有這三格")
    if trade.get("fragility_label") != label:
        errors.append(
            f"trades_this_session[0].fragility_label={trade.get('fragility_label')!r} != "
            f"risk_audit.tail_risk.fragility_label={label!r} — projection drift")

    gate = ra.get("ftd_timeline_gate") or {}
    if gate.get("applied") is True:
        keyed = (gate.get("stage"), gate.get("sector_class"))
        want = _FTD_TABLE.get(keyed)
        if want is None:
            errors.append(f"ftd_timeline_gate stage/sector_class {keyed} 不在 Step 3.5 表上")
        else:
            if ftd_mult is not None and abs(ftd_mult - want[0]) > 1e-9:
                errors.append(f"ftd_timeline_gate.multiplier={ftd_mult} but {keyed} maps to "
                              f"{want[0]} in the Step 3.5 table")
            got_pp = gate.get("stop_loss_adjustment_pp")
            if got_pp is not None and got_pp != want[1]:
                errors.append(f"ftd_timeline_gate.stop_loss_adjustment_pp={got_pp} but "
                              f"{keyed} maps to {want[1]}")
    elif gate.get("applied") is False and ftd_mult is not None and abs(ftd_mult - 1.0) > 1e-9:
        errors.append(f"ftd_timeline_gate.applied=false requires multiplier 1.0, got {ftd_mult}")

    f1 = ra.get("sector_concentration_f1") or {}
    if f1:
        applied, mult = f1.get("applied"), _numf(f1.get("multiplier"))
        if mult is not None and mult not in (0.5, 1.0):
            errors.append(f"sector_concentration_f1.multiplier={mult} — V20-F1 只有 0.5 / 1.0")
        if applied is True and mult is not None and abs(mult - 0.5) > 1e-9:
            errors.append("sector_concentration_f1.applied=true requires multiplier 0.5")
        if applied is not True and mult is not None and abs(mult - 1.0) > 1e-9:
            errors.append("sector_concentration_f1.applied=false requires multiplier 1.0")
        if f1.get("active_same_sector_confirmed") is None and applied is True:
            errors.append(
                "sector_concentration_f1.applied=true with active_same_sector_confirmed=null "
                "— 未評估的 concentration 不得減倉")

    if approval not in ("APPROVED", "REJECTED"):
        errors.append(f"risk_audit.approval={approval!r} must be APPROVED or REJECTED")
    if approval == "REJECTED":
        if not ra.get("rejection_reason"):
            errors.append("risk_audit.approval=REJECTED requires a rejection_reason")
        if fd in ("BUY", "STAGED_ENTRY"):
            errors.append(
                f"risk_audit.approval=REJECTED but final_decision={fd!r} — REJECTED 的計畫"
                "必須降級到 HOLD")

    method = ra.get("position_size_method")
    vol_limit = ra.get("vol_adjusted_limit_pct")
    if method == "VOL_ADJUSTED" and vol_limit is None:
        errors.append("position_size_method='VOL_ADJUSTED' but vol_adjusted_limit_pct is null")
    if method == "RULE_BASED" and vol_limit is not None:
        errors.append(f"position_size_method='RULE_BASED' but vol_adjusted_limit_pct="
                      f"{vol_limit} — 有 vol cap 就不該走 RULE_BASED")
    if trade.get("position_size_method") != method:
        errors.append(
            f"trades_this_session[0].position_size_method={trade.get('position_size_method')!r}"
            f" != risk_audit.position_size_method={method!r} — projection drift")

    if trade.get("hot_zone_probe") is True:
        tier_cap = _HZ_TIER_CAPS.get(trade.get("hot_zone_probe_tier"))
        if tier_cap is not None and size is not None and size > tier_cap + 1e-9:
            errors.append(f"hot_zone_probe tier cap {tier_cap} exceeded by "
                          f"position_size_pct={size} — Phase 4 必須 cap 在 Phase 3 給的上限")

    stop_pct = _numf(ra.get("final_stop_loss_pct"))
    if stop_pct is not None:
        if stop_pct > 0:
            errors.append(f"risk_audit.final_stop_loss_pct={stop_pct} must be ≤ 0 (它是跌幅)")
        if stop_pct < -10.0 - 1e-9:
            errors.append(f"risk_audit.final_stop_loss_pct={stop_pct} 超過 -10% 上限")
        mirrored = _numf(trade.get("final_stop_loss_pct"))
        if mirrored is not None and not _same_number(mirrored, stop_pct, tol=5e-4):
            errors.append(f"trades_this_session[0].final_stop_loss_pct={mirrored} != "
                          f"risk_audit.final_stop_loss_pct={stop_pct} — projection drift")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate latest investment session export")
    ap.add_argument("--history", default=HISTORY_JSON,
                    help="history JSON path (default: investment/invest_logs/history.json)")
    args = ap.parse_args(argv)
    history_path = args.history
    if not os.path.exists(history_path):
        fail([f"history.json not found at {history_path}"])

    with open(history_path, "r", encoding="utf-8") as fp:
        hist = json.load(fp)

    if not isinstance(hist, list) or not hist:
        fail(["history.json is empty or not a JSON array"])

    entry = hist[-1]
    errors = []
    warnings = []  # advisory-only findings — printed but never fail the gate

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
        errors.append(
            f"session_export_version = {ver!r}, expected one of {ACCEPTED_VERSIONS} "
            f"(new exports stamp {CURRENT_VERSION!r})")

    # ── 2b. V4.8 mis-stamp guard (V2.17.8) ───────────────────────────────
    # If entry has V5.0-only fields (valuation_lane / fair_value_summary) but
    # is stamped V4.8, that's a stamping bug — Claude wrote the wrong version
    # in Phase 5. V4.8 schema doesn't include these fields by definition.
    if ver == "V4.8":
        trade_first = ((entry.get("trades_this_session") or [{}])[0]) or {}
        v5_only_fields = [k for k in ("valuation_lane", "fair_value_summary")
                          if trade_first.get(k)]
        if v5_only_fields:
            errors.append(
                f"session_export_version='V4.8' but entry has V5.0-only fields {v5_only_fields} — "
                f"this is a Phase 5 stamping bug. Patch session_export_version to "
                f"{CURRENT_VERSION!r} (or 'V5.0' if the entry carries no Phase 3 engine block)."
            )

    # ── 2c. V5.0 mis-stamp guard (V4.81.0) ───────────────────────────────
    # Mirror of 2b one version up: `decision_engine_version` only exists on entries the
    # Phase 3 engine produced, which is exactly what V5.1 makes mandatory. Stamping such
    # an entry V5.0 would route it round the version gate in §13.
    if ver == "V5.0":
        trade_first = ((entry.get("trades_this_session") or [{}])[0]) or {}
        if trade_first.get("decision_engine_version"):
            errors.append(
                "session_export_version='V5.0' but entry carries decision_engine_version — "
                "Phase 3 engine output stamps 'V5.1' or newer. Patch the version field; "
                "keeping V5.0 bypasses the §13 calculation_steps gate."
            )

    # ── 2d. V5.1 mis-stamp guard (V4.82.0) ───────────────────────────────
    # Mirror of 2c one version up: `trade_plan_builder_version` only exists on entries the
    # Phase 4 engine produced, which is exactly what V5.2 makes mandatory. Stamping such an
    # entry V5.0/V5.1 would route it round the version gate in §14.
    if ver in ("V4.8", "V5.0", "V5.1"):
        trade_first = ((entry.get("trades_this_session") or [{}])[0]) or {}
        if trade_first.get("trade_plan_builder_version"):
            errors.append(
                f"session_export_version={ver!r} but entry carries trade_plan_builder_version "
                f"— Phase 4 engine output stamps {CURRENT_VERSION!r}. Patch the version field; "
                f"keeping {ver} bypasses the §14 risk_audit gate."
            )

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
    if ver in V5_VERSIONS:
        for k in TRADE_REQUIRED_V5:
            if k not in trade:
                errors.append(f"trades_this_session[0]: missing V5.0+ key {k}")
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
            # V4.69.0 — anchors 集合容錯：6-key（舊）與 8-key（+dcf_self_built/
            # comps_implied）都合法；集合外的 key 只 warning 不 error（前向相容）
            known_anchors = {"dcf_unlevered", "dcf_levered", "dcf_self_built",
                             "analyst_pt_consensus", "peer_pe_implied", "comps_implied",
                             "owner_earnings_mult", "forecaster_blend"}
            anchors = fvs.get("anchors")
            if isinstance(anchors, dict):
                unknown = set(anchors) - known_anchors
                if unknown:
                    warnings.append(
                        f"fair_value_summary.anchors unknown keys (accepted): {sorted(unknown)}")
                na = fvs.get("anchors_available")
                if isinstance(na, int) and not (0 <= na <= len(known_anchors)):
                    errors.append(f"fair_value_summary.anchors_available out of range: {na}")
            # Canonical valuation pack: all legacy fields are projections and
            # therefore must be numerically identical, not merely plausible.
            pack = trade.get("valuation_pack")
            if fvs.get("valuation_pack_schema") and not isinstance(pack, dict):
                errors.append(
                    "fair_value_summary declares valuation_pack_schema but valuation_pack is missing"
                )
            if isinstance(pack, dict):
                if pack.get("schema") != "valuation_pack.v1":
                    errors.append(f"valuation_pack.schema invalid: {pack.get('schema')!r}")
                for field in ("weighted_fair_value", "vs_current_pct"):
                    if not _same_number(pack.get(field), fvs.get(field)):
                        errors.append(
                            f"valuation_pack.{field} != fair_value_summary.{field} — projection drift"
                        )
                for field in ("verdict_band", "confidence"):
                    if pack.get(field) != fvs.get(field):
                        errors.append(
                            f"valuation_pack.{field} != fair_value_summary.{field} — projection drift"
                        )
                if not _same_number(pack.get("current_price"), trade.get("analysis_price")):
                    errors.append("valuation_pack.current_price != analysis_price")
                if len(pack.get("families_present") or []) < 2 and abs(pack.get("score") or 0) >= 2:
                    errors.append("valuation_pack: <2 families cannot emit |score| >= 2")
                for name, detail in (pack.get("anchors") or {}).items():
                    if not isinstance(detail, dict):
                        errors.append(f"valuation_pack.anchors.{name} must be an object")
                        continue
                    if detail.get("status") == "eligible" and (
                            not detail.get("provenance") or not detail.get("as_of")):
                        errors.append(
                            f"valuation_pack.anchors.{name}: eligible anchor missing provenance/as_of"
                        )
        # Validate valuation_lane structure
        vl = trade.get("valuation_lane")
        if isinstance(vl, dict):
            for k in ("signal", "score", "confidence"):
                if k not in vl:
                    errors.append(f"valuation_lane: missing key {k}")
            pack = trade.get("valuation_pack")
            if isinstance(pack, dict):
                for field in ("weighted_fair_value", "vs_current_pct", "score"):
                    if field in vl and not _same_number(vl.get(field), pack.get(field)):
                        errors.append(f"valuation_lane.{field} != valuation_pack.{field}")
        # Validate active_weights includes Valuation
        weights = entry.get("active_weights_end_of_session") or {}
        if "Valuation" not in weights:
            errors.append("active_weights_end_of_session: missing Valuation weight (V5.0 5-lane requirement)")

    # ── 5c. V2.19.0 — det_shadow polarization + red_team_basis ───────────
    # 後處理 (apply_det_shadow.py) 必跑；缺欄 → schema fail
    ds = trade.get("det_shadow")
    if ds is None:
        errors.append("det_shadow missing — run apply_det_shadow.py post-process before export (V2.19+)")
    elif isinstance(ds, dict):
        if isinstance(trade.get("valuation_pack"), dict) and ds.get("valuation_source") != "valuation_pack":
            errors.append(
                "det_shadow.valuation_source must be 'valuation_pack' when canonical pack exists"
            )
        sp = ds.get("signal_polarization")
        if sp not in (None, "ALIGNED", "MIXED", "OUTLIER", "BIPOLAR"):
            errors.append(f"det_shadow.signal_polarization invalid (V2.19 4-tier): {sp!r}")
        rtb = ds.get("red_team_basis")
        if rtb not in (None, "pure_forward", "pure_mean_reversion", "contaminated", "unclassified"):
            errors.append(
                f"det_shadow.red_team_basis invalid (V2.19): {rtb!r} — "
                "expected pure_forward / pure_mean_reversion / contaminated / unclassified"
            )

    # ── 5b. V2.14.0 optional thesis lifecycle type checks ────────────────
    # If present, enforce type contract. Absence is OK (Phase 5.5 may have skipped).
    tid = trade.get("thesis_id")
    if tid is not None and not isinstance(tid, str):
        errors.append(f"thesis_id must be string or null, got {type(tid).__name__}")
    tra = trade.get("thesis_registered_at")
    if tra is not None and not isinstance(tra, str):
        errors.append(f"thesis_registered_at must be ISO 8601 string or null, got {type(tra).__name__}")

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

    # ── 9. V5.0.x — cross-field consistency (A1) ─────────────────────────
    # CANCEL execution cannot coexist with a BUY-side thesis. Either the
    # thesis is wrong or the execution choice is. Caller must reconcile.
    fa = trade.get("final_action")
    if fa == "CANCEL" and fd in ("BUY", "STAGED_ENTRY"):
        errors.append(
            f"final_action='CANCEL' incompatible with final_decision={fd!r} — "
            "WAIT/CANCEL execution cannot coexist with BUY-side thesis. "
            "Use HOLD/STAGED_EXIT/SELL, or change final_action to EXECUTE/STAGED."
        )

    # ── 10. V5.0.x — Phase 4.6 decision-cap rules (A2) ───────────────────
    # Optional fields (back-compat with pre-V5.0.x entries). When the cap is
    # active, enforce: no BUY, confidence ≤ 0.65, position ≤ 30bps, and a
    # reason from the controlled enum.
    cap_active = trade.get("decision_cap_active")
    if cap_active is True:
        valid_reasons = ("insufficient_anchors", "low_valuation_confidence", "low_data_quality")
        cr = trade.get("decision_cap_reason")
        if cr not in valid_reasons:
            errors.append(
                f"decision_cap_active=true requires decision_cap_reason in {valid_reasons}, got {cr!r}"
            )
        if fd == "BUY":
            errors.append("decision_cap_active=true forbids final_decision='BUY'; use STAGED_ENTRY/HOLD")
        ac = trade.get("avg_confidence")
        if isinstance(ac, (int, float)) and ac > 0.65:
            errors.append(
                f"decision_cap_active=true requires avg_confidence ≤ 0.65, got {ac}"
            )
        ps = trade.get("position_size_pct")
        if isinstance(ps, (int, float)) and ps > 0.003:
            errors.append(
                f"decision_cap_active=true requires position_size_pct ≤ 0.003 (30bps), got {ps}"
            )

    # ── 11. V5.0.x — Rec 11 hot-zone probe rules (TODO-001+002) ──────────
    # When the hot-zone conservative-loosening exception fires, enforce:
    # STAGED_ENTRY decision, ≤15bps size, and mutual exclusion with the
    # valuation decision-cap (hard gates take precedence over the probe).
    if trade.get("hot_zone_probe") is True:
        if fd != "STAGED_ENTRY":
            errors.append(
                f"hot_zone_probe=true requires final_decision='STAGED_ENTRY', got {fd!r}"
            )
        # V4.70.0 (P0-1) — 分數分層 probe size：t2_30bps（score ≥ 0.4）/ t1_15bps。
        # tier 缺失（V4.70.0 前的 entry）→ warning + 沿用舊 15bps 上限。
        tier = trade.get("hot_zone_probe_tier")
        _TIER_CAPS = {"t1_15bps": 0.0015, "t2_30bps": 0.003}
        if tier is None:
            warnings.append(
                "hot_zone_probe_tier absent — V4.70.0 起 probe 應填 tier"
                "（t1_15bps / t2_30bps）；以 legacy 15bps 上限檢查"
            )
            tier_cap = 0.0015
        elif tier not in _TIER_CAPS:
            errors.append(
                f"hot_zone_probe_tier must be one of {sorted(_TIER_CAPS)}, got {tier!r}"
            )
            tier_cap = 0.003
        else:
            tier_cap = _TIER_CAPS[tier]
        hp = trade.get("position_size_pct")
        if isinstance(hp, (int, float)) and hp > tier_cap:
            errors.append(
                f"hot_zone_probe=true (tier={tier or 'legacy'}) requires "
                f"position_size_pct ≤ {tier_cap}, got {hp}"
            )
        if cap_active is True:
            errors.append(
                "hot_zone_probe=true incompatible with decision_cap_active=true — "
                "valuation cap is a hard gate and takes precedence over the probe"
            )

    # ── 12. V4.72.0 — P2-11 數值界限/加總檢查（AUDIT_2026-07-16 F6 #3）─────────
    # 動機：歷史出現 VRT final_score=6.72（超出理論量表上限 ~4.35：5×0.72 C_eff
    # ×1.15 bonus ×1.05 macro bonus）且 lane_scores=None 仍 rc=0 過關。
    fs = trade.get("final_score")
    if isinstance(fs, (int, float)) and abs(fs) > 4.5:
        errors.append(
            f"final_score {fs} outside sane bounds ±4.5 "
            "(theoretical max ≈ 4.35 = 5 × C_eff 0.72 × 1.15 × 1.05×macro) — "
            "計算鏈出錯或 LLM 手填，重跑 Phase 3"
        )
    so = trade.get("scenario_odds")
    if isinstance(so, dict) and so:
        vals = [v for v in so.values() if isinstance(v, (int, float))]
        if len(vals) == len(so) and sum(vals) != 100:
            errors.append(
                f"scenario_odds must sum to 100, got {sum(vals)} ({so})"
            )
    ls = trade.get("lane_scores")
    if isinstance(ls, dict):
        for k, v in ls.items():
            if isinstance(v, (int, float)) and not -5 <= v <= 5:
                errors.append(f"lane_scores.{k}={v} outside protocol scale -5..+5")
    vl_score = (trade.get("valuation_lane") or {}).get("score") \
        if isinstance(trade.get("valuation_lane"), dict) else None
    if isinstance(vl_score, (int, float)) and not -5 <= vl_score <= 5:
        errors.append(f"valuation_lane.score={vl_score} outside protocol scale -5..+5")
    ac_v = trade.get("avg_confidence")
    if isinstance(ac_v, (int, float)) and not 0.0 <= ac_v <= 1.0:
        errors.append(f"avg_confidence={ac_v} outside 0-1")

    # ── 11c. V4.70.0 — P0-2 red team 分級/校準欄位（值域檢查；缺欄 = 舊 entry OK）──
    rts = trade.get("red_team_counter_evidence_strength")
    if rts is not None and (not isinstance(rts, int) or isinstance(rts, bool)
                            or not 1 <= rts <= 5):
        errors.append(
            f"red_team_counter_evidence_strength must be int 1-5, got {rts!r}"
        )
    rtp = trade.get("red_team_thesis_break_probability")
    if rtp is not None and (not isinstance(rtp, (int, float)) or isinstance(rtp, bool)
                            or not 0.0 <= rtp <= 1.0):
        errors.append(
            f"red_team_thesis_break_probability must be float 0-1, got {rtp!r}"
        )

    # ── 11b. V5.0.x — Rec 11 hot_zone_eval instrumentation (TODO-015) ────
    # Always-recorded enum lets the weekly REVIEW tell "evaluated then
    # suppressed" from "rule never ran". Hard-error on enum/consistency when
    # present; absence is a warning only (pre-V5.0 entries predate the field).
    _HZ_EVAL_ENUM = {"fired", "suppressed_by_risk_flag",
                     "suppressed_by_cap", "not_qualifying"}
    hze = trade.get("hot_zone_eval")
    if hze is not None:
        if hze not in _HZ_EVAL_ENUM:
            errors.append(
                f"hot_zone_eval must be one of {sorted(_HZ_EVAL_ENUM)}, got {hze!r}"
            )
        elif (hze == "fired") != (trade.get("hot_zone_probe") is True):
            errors.append(
                "hot_zone_eval must equal 'fired' iff hot_zone_probe=true "
                f"(got eval={hze!r}, probe={trade.get('hot_zone_probe')!r})"
            )

    # ── 5d. Phase 4.5 Multi-Horizon Price Framework (advisory, warning-only) ─
    # MHP is derived/advisory: it feeds reasoning + trade_plan provenance but
    # NOT decision math and NOT the 11-field decision_lock. Absence (V5.0 back-
    # compat) or partial fill must NEVER fail the gate — emit warnings, keep rc=0.
    # （warnings list 建立於 main() 開頭，V4.69.0 anchor 容錯亦寫入同一 list）
    # TODO-015 — hot_zone_eval required on V5.0.x+; silent on pre-V5.0 (the field
    # postdates them). The pre-V4.81.0 form was `ver != "V5.0"`, i.e. exactly inverted:
    # it nagged the legacy entries that cannot have the field and never fired on the
    # modern ones that must.
    if trade.get("hot_zone_eval") is None and ver in V5_VERSIONS:
        warnings.append(
            "hot_zone_eval absent — TODO-015 要求每筆 deep-dive 寫出 Rec 11 評估結果"
            "（fired/suppressed_by_risk_flag/suppressed_by_cap/not_qualifying）"
        )
    mhp = trade.get("multi_horizon_price_framework")
    if mhp is None:
        if ver in V5_VERSIONS:
            warnings.append(
                "multi_horizon_price_framework absent — Phase 4.5 三框架未填（不擋 gate，"
                "新分析建議補上 short_term_5d / mid_term_60d / convergence）"
            )
    elif isinstance(mhp, dict):
        for k in ("short_term_5d", "mid_term_60d", "long_term_ref", "convergence"):
            if k not in mhp:
                warnings.append(f"multi_horizon_price_framework: missing sub-block {k} (degraded)")
        conv = mhp.get("convergence")
        if isinstance(conv, dict):
            sig = conv.get("mhp_signal")
            if sig not in (None, "wait_for_pullback", "high_conviction_long_zone",
                           "momentum_not_value", "neutral_aligned"):
                warnings.append(f"multi_horizon_price_framework.convergence.mhp_signal invalid: {sig!r}")
        lt = mhp.get("long_term_ref")
        fvs_ok = trade.get("fair_value_summary") or {}
        if isinstance(lt, dict) and "weighted_fair_value" in lt and "weighted_fair_value" in fvs_ok:
            if not _same_number(lt.get("weighted_fair_value"), fvs_ok.get("weighted_fair_value")):
                errors.append(
                    "multi_horizon_price_framework.long_term_ref.weighted_fair_value != "
                    "fair_value_summary.weighted_fair_value — 長期層應引用不重算"
                )
    else:
        warnings.append("multi_horizon_price_framework must be an object when present")

    # ── 5e. V3.45.1 — fair_value_range (advisory sibling, warning-only) ───
    # Anchor 分布區間。fair_value_summary 不變、仍是決策數字唯一來源；range 純呈現。
    # 缺/不全 NEVER fail gate — emit warnings, keep rc=0.
    fvr = trade.get("fair_value_range")
    if isinstance(fvr, dict):
        rm = fvr.get("range_method")
        if rm not in (None, "weighted_percentile", "minmax_fallback"):
            warnings.append(f"fair_value_range.range_method invalid: {rm!r}")
        rv = fvr.get("range_verdict")
        if rv not in (None, "undervalued_zone", "fair_zone", "overvalued_zone",
                      "extreme_undervalued", "extreme_overvalued"):
            warnings.append(f"fair_value_range.range_verdict invalid: {rv!r}")
        ag = fvr.get("agreement_grade")
        if ag not in (None, "high", "medium", "low"):
            warnings.append(f"fair_value_range.agreement_grade invalid: {ag!r}")
    elif fvr is not None:
        warnings.append("fair_value_range must be an object when present")

    # ── 5f. V3.45.1 — implied_expectations (reverse DCF, warning-only) ────
    # 掛 valuation_lane 或 trade 頂層皆可；不進加權/lane score/decision_lock。
    ie = trade.get("implied_expectations") or (trade.get("valuation_lane") or {}).get("implied_expectations")
    if isinstance(ie, dict):
        if ie.get("fcf_base_source") not in (None, "owner_earnings"):
            warnings.append(
                f"implied_expectations.fcf_base_source should be 'owner_earnings' (Burry rule 3 一致), "
                f"got {ie.get('fcf_base_source')!r}"
            )
        fb = ie.get("fcf_base")
        if isinstance(fb, (int, float)) and fb <= 0 and ie.get("implied_5y_fcf_cagr") is not None:
            warnings.append(
                "implied_expectations: fcf_base ≤ 0 但 implied_5y_fcf_cagr 非 null — "
                "FCF ≤ 0 應設 null 不硬解（V3.45.1 spec）"
            )
    elif ie is not None:
        warnings.append("implied_expectations must be an object when present")

    # ── 5g. V3.45.4 — news_lane PT 去重欄位（warning-only） ────────────────
    # reasoning_one_line / key_factors = pt_leakage classifier haystack；
    # pt_revision_momentum = PT level 剝離後的方向性替代訊號。舊 entry 缺欄不擋。
    nl = trade.get("news_lane")
    if isinstance(nl, dict):
        if "reasoning_one_line" not in nl or "key_factors" not in nl:
            warnings.append(
                "news_lane: missing reasoning_one_line / key_factors (V3.45.4 必填 — "
                "pt_leakage classifier 無 haystack；舊 entry 可接受)"
            )
        prm = nl.get("pt_revision_momentum")
        if isinstance(prm, dict):
            d = prm.get("direction")
            if d not in (None, "UP", "DOWN", "FLAT", "UNKNOWN"):
                warnings.append(f"news_lane.pt_revision_momentum.direction invalid: {d!r}")
        elif prm is not None:
            warnings.append("news_lane.pt_revision_momentum must be an object when present")
    ds_leak = (trade.get("det_shadow") or {}).get("news_pt_leakage")
    if ds_leak not in (None, True, False):
        warnings.append(f"det_shadow.news_pt_leakage must be bool|null, got {ds_leak!r}")

    # ── 5h. V3.46.0 — valuation_archetype_shadow（warning-only） ───────────
    # shadow-only：live fair_value_summary 不動；缺 block / 缺欄不擋（舊 entry 相容）
    vas = trade.get("valuation_archetype_shadow")
    if isinstance(vas, dict):
        at = vas.get("archetype")
        if at not in (None, "financial", "hypergrowth", "cyclical", "mature_cashflow", "balanced"):
            warnings.append(f"valuation_archetype_shadow.archetype invalid: {at!r}")
        vbs = vas.get("verdict_band_shadow")
        if vbs not in (None, "extreme_undervalued", "undervalued", "fairly_valued",
                       "overvalued", "extreme_overvalued"):
            warnings.append(f"valuation_archetype_shadow.verdict_band_shadow invalid: {vbs!r}")
        if vas.get("flip_vs_live") not in (None, True, False):
            warnings.append("valuation_archetype_shadow.flip_vs_live must be bool|null")
    elif vas is not None:
        warnings.append("valuation_archetype_shadow must be an object when present")

    # ── 13. V4.80.0 — Phase 3 arithmetic re-derivation (decision_engine parity) ──
    # 舊 entry（無 calculation_steps 也無 decision_engine_version）整段跳過 → 向後相容。
    check_phase3_arithmetic(entry, trade, errors, warnings)

    # ── 14. V4.82.0 — Phase 4 sizing re-derivation (trade_plan_builder parity) ──
    # 舊 entry（無 risk_audit 也無 trade_plan_builder_version）整段跳過 → 向後相容。
    check_phase4_sizing(entry, trade, errors, warnings)

    # ── 14b. V4.82.0 — fragility_label enum ──────────────────────────────
    # replay_trade_plan.py 的 sizing cohort 發現歷史上有 6 筆用了 protocol 表外的標籤
    # （`RESILIENT` / `MEDIUM`），Step 3 乘數因此無從對應。§6 只驗非 null，補上值域。
    # Validator 只看最後一筆，所以對新 export 設 error 不會誤傷既有 history。
    _frag = trade.get("fragility_label")
    if _frag is not None and _frag not in ("ROBUST", "MODERATE", "FRAGILE"):
        errors.append(
            f"fragility_label={_frag!r} outside the Step 3 table (ROBUST/MODERATE/FRAGILE) — "
            "tail-risk-analyzer 只輸出這三值；表外標籤讓 Phase 4 乘數無從對應")

    if errors:
        fail(errors)

    ticker = trade.get("ticker", "?")
    decision = trade.get("final_decision", "?")
    print(f"[validate_session_export] ✓ {ver} schema compliant — {ticker} / {decision}")
    for w in warnings:
        print(f"[validate_session_export] ⚠ degraded: {w}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Validate one isolated session object (or the latest legacy `history.json` entry)
against the Phase 5 schema documented in `investment/phase5_export_schema.md`.

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
import time
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# The digest function is imported, not restated: this side must canonicalise
# byte-for-byte the way the writer did, and two copies of that rule would drift
# into a gate that reds on correct entries.
import append_session_export  # noqa: E402
from apply_det_shadow import (  # noqa: E402
    ANALYSIS_MODES,
    LANE_CONTRACT_VERSIONS,
    LANE_FIELDS,
    LANE_NAMES,
    LLM_PROVENANCE,
    PROVENANCE_VALUES,
    authoritative_valuation_score,
    compute_polarization,
)
from decision_engine import (  # noqa: E402
    ENGINE_ARTIFACT as DECISION_ENGINE_ARTIFACT,
    SPECULATIVE_CONFIDENCE_CAP,
    SPECULATIVE_REASONS,
    SPECULATIVE_SIZE_CAP_PCT,
    compute_dynamic_threshold,
    decision_band,
)
# The gate below and the marker that sets it must never drift apart, so the
# reason string and the command table are imported rather than restated.
#: `skills/technical-analyst/scripts/analyze.py` persists its payload here since
#: V4.116.3, which is what turns `rubric_hint` from something the lane says about
#: itself into evidence a validator can read.
TECHNICAL_PAYLOAD = "skills/technical-analyst/cache/{t}_technical_payload.json"
TECHNICAL_PAYLOAD_MAX_AGE_DAYS = 1
#: `"0 to +1 (basing — wait for confirmation)"` → (0.0, 1.0). The parenthetical
#: is commentary; only the leading band is a constraint.
_RUBRIC_RE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*to\s*([+-]?\d+(?:\.\d+)?)")


def _check_technical_rubric(entry, trade, errors, warnings):
    """The Technical lane may not out-score its own script without saying so.

    `analyze.py` turns the stage structure into a score band (`rubric_hint`).
    A lane that returns more than the band is overriding the rubric, which is a
    legitimate thing to do and an illegitimate thing to do silently — on
    2026-08-09 one engine returned +2.5 and then +2.0 against `0 to +1` on two
    consecutive runs of the same ticker, while another returned exactly +1.0 on
    the same hint. Either would have flipped the final decision.

    Deviation stays available through `technical_lane.rubric_override_reason`;
    the requirement is that it be declared, not that it be forbidden.

    Silent when no fresh artifact exists: the run may predate the cache, and a
    missing artifact is the `script_not_run` family's business, not this check's.
    """
    # Read from the entry rather than a caller's locals: this check must work
    # wherever it is invoked from, and `lane_scores` has been protocol-mandatory
    # since V2.10.0.
    scores = trade.get("lane_scores")
    score = scores.get("technical") if isinstance(scores, dict) else None
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return
    ticker = str(trade.get("ticker") or entry.get("ticker") or "").strip().upper()
    if not ticker:
        return
    path = os.path.join(ROOT, TECHNICAL_PAYLOAD.format(t=ticker))
    try:
        if (time.time() - os.path.getmtime(path)) > TECHNICAL_PAYLOAD_MAX_AGE_DAYS * 86400:
            return
        with open(path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except (OSError, json.JSONDecodeError):
        return
    if str((payload or {}).get("ticker") or "").upper() != ticker:
        return
    hint = ((payload.get("signal_hints") or {}).get("rubric_hint") or "")
    m = _RUBRIC_RE.match(str(hint))
    if not m:
        warnings.append(f"technical rubric_hint unparseable: {hint!r}")
        return
    lo, hi = sorted((float(m.group(1)), float(m.group(2))))
    if lo <= score <= hi:
        return
    override = ((trade.get("technical_lane") or {}) if isinstance(
        trade.get("technical_lane"), dict) else {}).get("rubric_override_reason")
    if isinstance(override, str) and override.strip():
        warnings.append(
            f"technical score {score} outside rubric_hint [{lo}, {hi}] — declared: "
            f"{override.strip()[:120]}")
        return
    errors.append(
        f"technical lane score {score} is outside its own script's rubric_hint "
        f"[{lo}, {hi}] ({hint!r}) with no `technical_lane.rubric_override_reason`. "
        f"Score inside the band, or state why the stage read does not apply")


#: Sessions exported on/after this date must carry `valuation_reviewer_gate`.
#: A date rather than a schema-version bump: the requirement is about operator
#: discipline from a point in time, not about the export's shape, and bumping
#: the version would cascade into the replay coverage checks for no benefit.
VALUATION_GATE_REQUIRED_FROM = "2026-08-09"

#: Sessions exported on/after this date must have been written by
#: `append_session_export.py` and left alone afterwards, and must resolve
#: `news_lane.pt_revision_momentum` explicitly. Same date-keyed rationale as
#: `VALUATION_GATE_REQUIRED_FROM`.
#:
#: Next day rather than same day, unlike V4.116.3. That gate could be satisfied
#: retroactively — re-run the script, refill the block, re-export. This one
#: cannot: an entry already on disk has no stamp and no way to acquire one
#: short of a re-append, so a same-day cutoff would leave the newest entry
#: permanently red and the validator reading red until the next session. A gate
#: whose red state is unfixable teaches people to ignore it.
PROVENANCE_REQUIRED_FROM = "2026-08-09"
PT_MOMENTUM_REQUIRED_FROM = "2026-08-09"

#: `decision_engine.py` persists its Phase 3 output there since V4.117.0; the
#: path is imported above rather than restated, because a gate that reads a
#: path the producer no longer writes goes silent instead of red.
DECISION_ENGINE_ARTIFACT_MAX_AGE_DAYS = 1
#: Sub-blocks of `calculation_steps` that the engine derives wholesale. Compared
#: recursively; everything else in the block is compared as a scalar.
_PT_DIRECTIONS = ("UP", "DOWN", "FLAT", "UNKNOWN")


def _check_export_provenance(entry, errors, warnings):
    """history.json is append_session_export.py's to write, and nobody else's.

    On 2026-08-09 one engine hit a validator failure and resolved it by editing
    the decision record in place — `t['final_score'] = 1.0558` plus a retyped
    `calculation_steps` block — and, on an earlier run of the same ticker,
    popped entries off the list with an ad-hoc `json.dump` when a gate went red.
    Both produced a green validator. Nothing in the schema could tell, because
    a hand-written entry and a script-written one are the same JSON.

    The stamp is a content digest rather than a marker, so the check survives
    the obvious next step of typing the marker by hand: writing the entry
    yourself means you have no digest, and editing it after append means the
    digest no longer describes it. The sanctioned chain
    (`apply_det_shadow --inplace`, `register_thesis`) writes only fields the
    digest excludes, so it round-trips.

    Fixing a bad entry stays possible — it just has to go back through the
    script, which is the point: a re-append re-derives the digest, an in-place
    edit does not.
    """
    export_date = str(entry.get("export_date") or "")
    prov = entry.get("export_provenance")
    if not isinstance(prov, dict):
        if export_date >= PROVENANCE_REQUIRED_FROM:
            errors.append(
                "export_provenance missing — 這筆 entry 不是 "
                "`append_session_export.py` 寫的。history.json 只由該 script 追加；"
                "手寫 / json.dump 覆蓋會讓決策紀錄失去可稽核性。修法：把 entry 存成 "
                "檔案後 `python3 investment/scripts/append_session_export.py "
                "--from-file <path>`，不要就地改 history.json")
        elif prov is not None:
            warnings.append("export_provenance must be an object when present")
        return
    if prov.get("schema") != append_session_export.PROVENANCE_SCHEMA:
        warnings.append(
            f"export_provenance.schema unexpected: {prov.get('schema')!r}")
    stamped = prov.get("entry_digest")
    actual = append_session_export.entry_digest(entry)
    if not isinstance(stamped, str) or not stamped:
        errors.append("export_provenance.entry_digest missing — stamp 沒有內容摘要就"
                      "只是一句宣稱，擋不住 append 之後的就地修改")
        return
    if stamped != actual:
        errors.append(
            f"export_provenance.entry_digest 不符 — entry 在 append 之後被就地改過。"
            f"stamped={stamped[:23]}… actual={actual[:23]}… "
            f"（合法的 apply_det_shadow / register_thesis 只寫 det_shadow / "
            f"lane_contract / thesis_id，不會動到摘要）。要改決策數字，重跑產生它的 "
            f"engine 再重新 append，不要改檔")


def _check_pt_revision_momentum(entry, trade, errors, warnings):
    """The News lane must say what the PT revision signal was, or that it had none.

    protocol §PHASE 2 scores this field: `direction=UP` with `delta_1m > +3%` is
    worth +0.5~+1, `DOWN` below −3% the same in reverse. The validator only
    type-checked it when present, so `null` was free — and on 2026-08-09 an
    export carried `-2.94% 1m` in the lane's prose risk flag while the
    structured field stayed null. The score happened to be unaffected (−2.94%
    is inside the ±3% band), which is exactly why it went unnoticed: the
    audit chain broke without the number moving.

    `UNKNOWN` + a reason is a first-class answer. The requirement is that the
    lane resolve the field, not that the data exist.
    """
    if str(entry.get("export_date") or "") < PT_MOMENTUM_REQUIRED_FROM:
        return
    nl = trade.get("news_lane")
    if not isinstance(nl, dict):
        # A gate that a null parent switches off is not a gate. The lane having
        # scored is the evidence that it ran, so that is what the requirement
        # keys on — a genuinely absent lane (no score) stays silent.
        news_score = (trade.get("lane_scores") or {}).get("news") \
            if isinstance(trade.get("lane_scores"), dict) else None
        if isinstance(news_score, (int, float)) and not isinstance(news_score, bool):
            errors.append(
                f"news_lane 缺漏但 lane_scores.news={news_score} —— lane 有評分就代表它跑過，"
                f"V2.13.0 起這個 block 必填（含 pt_revision_momentum）。沒跑就把 "
                f"lane_scores.news 設 null，不要讓評分留著、依據消失")
        return
    prm = nl.get("pt_revision_momentum")
    if not isinstance(prm, dict):
        errors.append(
            "news_lane.pt_revision_momentum missing — protocol §PHASE 2 用 direction + "
            "delta_1m 給 ±0.5~1 分，null 等於把計分依據留在散文裡。抓不到資料就明寫 "
            '{"direction": "UNKNOWN", "unavailable_reason": "<為什麼>"}')
        return
    direction = prm.get("direction")
    if direction not in _PT_DIRECTIONS:
        errors.append(
            f"news_lane.pt_revision_momentum.direction={direction!r} — 只認 "
            f"{list(_PT_DIRECTIONS)}")
        return
    if direction == "UNKNOWN":
        reason = prm.get("unavailable_reason")
        if not (isinstance(reason, str) and reason.strip()):
            errors.append(
                "news_lane.pt_revision_momentum.direction=UNKNOWN 需要 "
                "`unavailable_reason` —— 沒有理由的 UNKNOWN 與漏填無法區分")
        return
    if direction == "FLAT":
        return
    # UP / DOWN 是有方向的宣稱，就必須帶得出讓 ±3% 規則能套的幅度。
    d1m = prm.get("consensus_delta_pct_1m")
    if isinstance(d1m, bool) or not isinstance(d1m, (int, float)):
        errors.append(
            f"news_lane.pt_revision_momentum.direction={direction} 但 "
            f"consensus_delta_pct_1m={d1m!r} 不是數字 —— ±3% 門檻無從套用，"
            f"方向宣稱就不可稽核")


def _check_calculation_steps_parity(entry, trade, errors, warnings):
    """What was exported must be what the engine actually last returned.

    §13 already re-derives the arithmetic, which proves the block is
    self-consistent — it cannot tell that the block belongs to a *superseded*
    run. On 2026-08-09 an export carried `calculation_steps` from a run with
    valuation −1.5 while the entry's own valuation lane said −3.0; the fix
    cycle then hand-edited numbers in both directions before finally re-running
    the engine. A block that was retyped rather than re-derived is the same
    shape as a correct one.

    Silent without a fresh matching artifact: the run may predate the persist,
    and a missing artifact belongs to the `script_not_run` family.
    """
    steps = trade.get("calculation_steps")
    if not isinstance(steps, dict):
        return
    ticker = str(trade.get("ticker") or entry.get("ticker") or "").strip().upper()
    if not ticker:
        return
    path = os.path.join(ROOT, DECISION_ENGINE_ARTIFACT.format(t=ticker))
    try:
        age = time.time() - os.path.getmtime(path)
        if age > DECISION_ENGINE_ARTIFACT_MAX_AGE_DAYS * 86400:
            return
        with open(path, "r", encoding="utf-8") as fp:
            art = json.load(fp)
    except (OSError, json.JSONDecodeError):
        return
    if str((art or {}).get("ticker") or "").upper() != ticker:
        return
    ref = art.get("calculation_steps")
    if not isinstance(ref, dict):
        return
    diffs = _diff_steps(ref, steps)
    if not diffs:
        return
    shown = "；".join(diffs[:6]) + (f"（另 {len(diffs) - 6} 處）" if len(diffs) > 6 else "")
    errors.append(
        f"calculation_steps 與 decision_engine.py 最後一次的輸出不符：{shown}。"
        f"這個 block 是 engine 的產出、不是可以手抄的欄位 —— 以 "
        f"{DECISION_ENGINE_ARTIFACT.format(t=ticker)} 為準重寫，或改對輸入重跑 engine "
        f"讓兩者同源")


def _diff_steps(ref, got, prefix=""):
    """Field paths where the export disagrees with the engine artifact.

    Only walks keys the engine emitted — extra keys in the export are somebody
    else's schema business, not a parity failure.
    """
    out = []
    for k, rv in ref.items():
        path = f"{prefix}{k}"
        if k not in got:
            out.append(f"{path} 缺漏")
            continue
        gv = got[k]
        if isinstance(rv, dict) and isinstance(gv, dict):
            out.extend(_diff_steps(rv, gv, prefix=f"{path}."))
        elif isinstance(rv, (int, float)) and not isinstance(rv, bool) \
                and isinstance(gv, (int, float)) and not isinstance(gv, bool):
            # Tolerance covers re-serialisation only; a real transcription slip
            # is orders of magnitude larger than this.
            if abs(float(rv) - float(gv)) > 1e-6:
                out.append(f"{path} {gv!r} vs engine {rv!r}")
        elif rv != gv:
            out.append(f"{path} {gv!r} vs engine {rv!r}")
    return out

from compute_price_framework import (  # noqa: E402
    ANCHOR_DROPPED_VALUE,
    FORWARD_VALIDATION_SCHEMA,
    SCRIPT_NOT_RUN,
    SCRIPT_SOURCED_ANCHORS,
    compute_forward_validation,
)

ROOT         = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HISTORY_JSON = os.path.join(ROOT, "investment/invest_logs/history.json")
# Accepted schema versions, oldest → newest. V4.8 (4-lane legacy) lives until pre-V5.0
# entries decay; V5.0 opened the 5-lane era; V5.1 makes the Phase 3 engine block mandatory;
# V5.2 does the same for the Phase 4 engine block.
ACCEPTED_VERSIONS = ("V4.8", "V5.0", "V5.1", "V5.2", "V5.3", "V5.4")
CURRENT_VERSION   = "V5.4"
# 5-lane era — valuation_lane / fair_value_summary required, Rec 11 + MHP instrumented.
V5_VERSIONS = ("V5.0", "V5.1", "V5.2", "V5.3", "V5.4")
# Versions whose entries MUST carry the Phase 3 engine output (`calculation_steps` +
# `decision_engine_version`). Version-keyed rather than date-keyed so a backfilled entry
# stamped V5.1 is held to exactly the same bar as one exported today.
CALC_STEPS_REQUIRED_VERSIONS = ("V5.1", "V5.2", "V5.3", "V5.4")
# Versions whose entries MUST carry the Phase 4 engine output (`risk_audit` +
# `trade_plan_builder_version` + `mandatory_risk_flags`). Same version-keyed discipline.
RISK_AUDIT_REQUIRED_VERSIONS = ("V5.2", "V5.3", "V5.4")
# Versions whose entries MUST carry the C1 lane contract (`lane_contract`).
# 值域與形狀的單一事實來源在 apply_det_shadow.py（producer），這裡只 import 不複製。
LANE_CONTRACT_REQUIRED_VERSIONS = LANE_CONTRACT_VERSIONS

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
        "\nFix: rebuild the isolated session export to match "
        "investment/phase5_export_schema.md, then re-run this validator.",
        file=sys.stderr,
    )
    sys.exit(1)


def _same_number(a, b, tol=0.011):
    return (isinstance(a, (int, float)) and not isinstance(a, bool)
            and isinstance(b, (int, float)) and not isinstance(b, bool)
            and abs(float(a) - float(b)) <= tol)


def _same_projection(a, b, tol=0.011):
    """Projection equality that treats null==null as agreement, not drift.

    A 0-anchor valuation pack emits null for weighted_fair_value / vs_current_pct /
    verdict_band, and every downstream projection faithfully carries the same null.
    `_same_number` rejects (None, None) because neither side is numeric, which turned
    a correctly-propagated "unavailable" into a schema-drift error (first hit: AAOI
    2026-08-07, the first session where all 8 anchors were ineligible). Only both-null
    is exempted — null on one side and a number on the other is still real drift.
    """
    if a is None and b is None:
        return True
    return _same_number(a, b, tol=tol)


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
        t5_step = cs.get("t5_forward_validation") or {}
        if t5_step.get("downgrade_applied") is True:
            allowed.add(t5_step.get("decision_after"))  # engine 1.1.0 T5 downgrade
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
        # V4.86.1 — the schema marks this required, so enforce it. Silently falling back
        # to `final_decision` on a capped entry resurrects the false "沒折半" error and
        # points the PM at the wrong field: the fault is a missing column, not bad math.
        if not ra.get("sized_for_decision"):
            errors.append(
                "risk_audit.sized_for_decision missing — V5.2 起必填。§14 用它判斷 "
                "STAGED_ENTRY 折半該不該套；缺欄時退回 final_decision，capped entry 會被"
                "誤判成『鏈沒折半』")

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

    # V4.86.1 — the field must not become the escape hatch. Because it *overrides* the
    # halving rule, declaring `sized_for_decision="BUY"` on a STAGED_ENTRY export waves
    # through a chain at twice the correct size. There are exactly two things that can
    # legitimately rewrite the decision after Phase 4 sized against it, so anything else
    # must agree with `final_decision`.
    _DECISIONS = ("BUY", "STAGED_ENTRY", "HOLD", "STAGED_EXIT", "SELL")
    declared = ra.get("sized_for_decision")
    if declared is not None and declared not in _DECISIONS:
        errors.append(f"risk_audit.sized_for_decision={declared!r} must be one of {_DECISIONS}")
    elif declared is not None and fd and declared != fd:
        # REJECTED  → Phase 4 itself downgraded the plan to HOLD
        # cap active → Phase 4.6 rewrote BUY into HOLD / STAGED_ENTRY
        if not (ra.get("approval") == "REJECTED" or trade.get("decision_cap_active") is True):
            errors.append(
                f"risk_audit.sized_for_decision={declared!r} != final_decision={fd!r} without "
                "approval=REJECTED or decision_cap_active=true — 只有這兩者能在 Phase 4 "
                "定倉之後改寫決策；否則本欄等於繞過 STAGED_ENTRY 折半檢查")
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
        elif trade.get("speculative_grade") is True:
            # V4.108.0 — speculative governor 與 decision cap 同一個時序位置（Phase 4
            # 定倉之後），同樣只會縮小。少了這條，虧損題材股的 export 會在 §14 被判
            # 「倉位不等於鏈尾」——決策放行了卻無法通過 Phase 5，等於白做。
            if size > final_size + 1.5e-6:
                errors.append(
                    f"position_size_pct={size} > sizing_chain tail {final_size} with "
                    "speculative_grade=true — governor 只會縮小倉位，不會放大")
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


# ---------------------------------------------------------------------------
# V4.90.0 §15 — C1 統一 lane 資料契約 (`lane_contract`) + lane 區塊形狀鎖
# ---------------------------------------------------------------------------

# C1 決策 3：五個 lane 的質性區塊在真實 entry 之間形狀不一（`moat_assessment` 忽 dict 忽
# string、`smart_money_analysis` 的正文欄位忽 `narrative` 忽 `note`、`immediate_catalyst_5d`
# 忽 dict 忽 null）。每個消費端各自寫相容碼是不可持續的（renderer 現在就有三處）。
# 這裡把形狀定死，**只對 V5.3+ 生效** —— 舊 entry 照當年規則驗，renderer 的相容碼因此
# 必須留著（它讀得到 181 筆舊 entry），等舊 entry 淡出 render 路徑才談刪除。
#   欄位 → (期望型別, 期望正文欄位或 None, 是否允許 null)
LANE_SHAPE_LOCKS = (
    ("fundamentals_lane", "moat_assessment",      None,        False),
    ("technical_lane",    "smart_money_analysis", "narrative", False),
    ("news_lane",         "immediate_catalyst_5d", None,       True),
)


def check_lane_contract(entry, trade, errors, warnings):
    """§15 — 驗 `lane_contract` 形狀、值域、與 `det_shadow` 的一致性。

    舊 entry（版號不在 `LANE_CONTRACT_REQUIRED_VERSIONS`）**整段跳過**，向後相容；
    「戳舊版號卻帶契約」的繞道由 §2e 擋，兩邊合起來才是完整的版本閘。
    """
    ver = entry.get("session_export_version")
    if ver not in LANE_CONTRACT_REQUIRED_VERSIONS:
        return

    lc = trade.get("lane_contract")
    if lc is None:
        errors.append(
            "lane_contract missing — run apply_det_shadow.py post-process before export "
            f"(C1 契約自 {CURRENT_VERSION} 起必填)")
        return
    if not isinstance(lc, dict):
        errors.append(f"lane_contract must be an object, got {type(lc).__name__}")
        return

    if not isinstance(lc.get("contract_version"), str) or not lc.get("contract_version"):
        errors.append("lane_contract.contract_version must be a non-empty string")

    # `lane_scores` 自 V2.10.0 起就是 protocol 必填，但 validator 從未強制。C1 讓它變成
    # 硬性要求：契約用「這個 lane 有沒有分數」推導 `provenance: absent`，所以整塊省略
    # 會讓四個跑過的 lane 被標成「本回合沒產出」—— 省略一個欄位就偽造了 provenance。
    _lane_scores = trade.get("lane_scores")
    if not isinstance(_lane_scores, dict):
        errors.append(
            "lane_scores missing or not an object — C1 契約用它推導哪些 lane 有產出；"
            "整塊省略會把四個跑過的 lane 標成 provenance='absent'（偽造 provenance）")
    else:
        # 四個 key 必須都在（值可為 null）。只擋「整塊省略」不夠：`{"fundamentals": 4}`
        # 會讓另外三個 lane 一樣被推成 absent，而 producer 與 validator 會一致同意 →
        # 全綠。契約要求六個 lane 全列、缺席明寫 absent，它所依據的 lane_scores 就不能
        # 允許部分省略——省略與「跑了但沒記」在事後同樣無法區分。
        _missing_keys = [k for k in ("fundamentals", "sentiment", "news", "technical")
                         if k not in _lane_scores]
        if _missing_keys:
            errors.append(
                f"lane_scores missing key(s): {_missing_keys} — 四個 lane 一律列出，"
                "沒產出的填 null（省略會讓契約把它推成 provenance='absent'，"
                "與『跑了但沒記』無法區分）")
    mode = lc.get("analysis_mode")
    if mode not in ANALYSIS_MODES:
        errors.append(f"lane_contract.analysis_mode invalid: {mode!r} — "
                      f"expected one of {list(ANALYSIS_MODES)}")

    lanes = lc.get("lanes")
    if not isinstance(lanes, dict):
        errors.append("lane_contract.lanes must be an object keyed by lane name")
        return
    absent_lanes = [n for n in LANE_NAMES if n not in lanes]
    if absent_lanes:
        errors.append(
            f"lane_contract.lanes missing lane(s): {absent_lanes} — 六個 lane 一律列出，"
            "沒跑的填 provenance='absent'。省略與『跑了但沒記』無法區分，Phase 6 分層會把"
            "兩者混為一談")
    unknown = [n for n in lanes if n not in LANE_NAMES]
    if unknown:
        errors.append(f"lane_contract.lanes has unknown lane(s): {unknown} — "
                      f"expected exactly {list(LANE_NAMES)}")

    # provenance 與實際訊號的一致性基準。**兩個函式都 import 自 producer**（不是重寫一份）：
    # 取值順序或 missing 判定哪天改了，producer 與 validator 一起改，不會出現「validator
    # 對合法 entry 報錯」的漂移。
    _ls = trade.get("lane_scores")
    derived_missing = set(compute_polarization(
        _ls if isinstance(_ls, dict) else {},
        authoritative_valuation_score(trade)).get("missing_lanes") or [])

    for name in LANE_NAMES:
        if name not in lanes:
            continue                      # 已由 absent_lanes 報過
        blk = lanes[name]
        if not isinstance(blk, dict):
            # 含 null：`"sentiment": null` 若只 continue，五個欄位檢查整組被跳過，
            # 而 session 清單只要跟著把它列進 skipped 就全綠 —— 一個 null 換一次靜默偽造。
            errors.append(f"lane_contract.lanes.{name} must be an object, got "
                          f"{type(blk).__name__}")
            continue
        for f in LANE_FIELDS:
            if f not in blk:
                errors.append(f"lane_contract.lanes.{name}: missing field {f}")

        prov = blk.get("provenance")
        if prov not in PROVENANCE_VALUES:
            errors.append(f"lane_contract.lanes.{name}.provenance invalid: {prov!r} — "
                          f"expected one of {list(PROVENANCE_VALUES)}")
        elif name != "red_team":
            # absent ⟺ 該 lane 真的沒有分數。少了這條，有分數的 lane 手改成 absent
            # 一樣全綠 —— Phase 6 分層會把它從 LLM 池靜默剔除（selection bias 向量）。
            if prov == "absent" and name not in derived_missing:
                errors.append(
                    f"lane_contract.lanes.{name}.provenance='absent' 但該 lane 有分數 — "
                    "有產出的 lane 不得自稱缺席；重跑 apply_det_shadow.py")
            elif prov != "absent" and name in derived_missing:
                errors.append(
                    f"lane_contract.lanes.{name}.provenance={prov!r} 但該 lane 無分數 — "
                    "無產出的 lane 應為 'absent'；分數真的存在的話先修 lane_scores")
        else:
            # RT 的缺席由 red_team_execution_failed 決定，兩個方向都鎖：
            # 失敗卻標有產出（既有檢查涵蓋 llm；這裡連 deterministic 一起擋），
            # 或沒失敗卻標 absent（RT verdict 明明在 entry 裡）。
            rt_failed = bool(trade.get("red_team_execution_failed"))
            if prov == "absent" and not rt_failed:
                errors.append(
                    "lane_contract.lanes.red_team.provenance='absent' 但 "
                    "red_team_execution_failed=false — RT 有跑就不得自稱缺席")
            elif prov != "absent" and rt_failed:
                errors.append(
                    f"lane_contract.lanes.red_team.provenance={prov!r} 但 "
                    "red_team_execution_failed=true — RT 失敗時 provenance 應為 'absent'")
        inv = blk.get("llm_invoked")
        if not isinstance(inv, bool):
            errors.append(f"lane_contract.lanes.{name}.llm_invoked must be bool, got {inv!r}")
        elif prov in PROVENANCE_VALUES and inv != (prov in LLM_PROVENANCE):
            errors.append(
                f"lane_contract.lanes.{name}: llm_invoked={inv} contradicts "
                f"provenance={prov!r}（llm/hybrid ⇒ true；deterministic/absent ⇒ false）")

        pver = blk.get("producer_version")
        if pver is not None and not isinstance(pver, str):
            errors.append(f"lane_contract.lanes.{name}.producer_version must be string|null, "
                          f"got {type(pver).__name__}")
        elif prov in ("deterministic", "hybrid") and not pver:
            errors.append(
                f"lane_contract.lanes.{name}.producer_version required when "
                f"provenance={prov!r} — Phase 6 按 producer 版號分層校準，不具名的 det lane "
                "無法歸屬到任何一版公式")

        ih = blk.get("input_hash")
        if ih is not None and not isinstance(ih, str):
            errors.append(f"lane_contract.lanes.{name}.input_hash must be string|null, "
                          f"got {type(ih).__name__}")
        ss = blk.get("shadow_score")
        if ss is not None and (isinstance(ss, bool) or not isinstance(ss, (int, float))):
            errors.append(f"lane_contract.lanes.{name}.shadow_score must be number|null, "
                          f"got {ss!r}")

    # ── session 層兩個清單必須是六個 lane 的分割，且與 per-lane llm_invoked 一致 ──
    inv_list, skip_list = lc.get("llm_invoked_lanes"), lc.get("llm_skipped_lanes")
    for label, val in (("llm_invoked_lanes", inv_list), ("llm_skipped_lanes", skip_list)):
        if not isinstance(val, list) or any(not isinstance(x, str) for x in val):
            errors.append(f"lane_contract.{label} must be an array of lane names")
    if isinstance(inv_list, list) and isinstance(skip_list, list):
        if sorted(str(x) for x in inv_list + skip_list) != sorted(LANE_NAMES):
            errors.append(
                "lane_contract: llm_invoked_lanes + llm_skipped_lanes 必須剛好分割六個 lane "
                f"（got invoked={inv_list}, skipped={skip_list}）")
        else:
            derived = sorted(n for n in LANE_NAMES
                             if isinstance(lanes.get(n), dict)
                             and lanes[n].get("llm_invoked") is True)
            if sorted(str(x) for x in inv_list) != derived:
                errors.append(
                    f"lane_contract.llm_invoked_lanes={sorted(inv_list)} 與 per-lane "
                    f"llm_invoked 推導值 {derived} 不符 — session 層清單是 per-lane 的投影，"
                    "不是獨立事實")

    # ── 吸收閘：契約的 valuation.shadow_score 與 det_shadow.valuation_score_det 同源 ──
    # 兩者由 apply_to_trade() 的同一次計算寫出，永不可能自然漂移；不等 = 有人事後手改
    # 其中一處，那正是 C1「勿兩套並存」要擋的失效模式。
    val_blk, ds = lanes.get("valuation"), trade.get("det_shadow")
    if isinstance(val_blk, dict) and isinstance(ds, dict):
        a, b = val_blk.get("shadow_score"), ds.get("valuation_score_det")
        same = (a is None and b is None) or _same_number(a, b, tol=1e-9)
        if not same:
            errors.append(
                f"lane_contract.lanes.valuation.shadow_score={a!r} != "
                f"det_shadow.valuation_score_det={b!r} — 同一次計算的兩個落點，"
                "不一致代表其中一處被事後編輯；重跑 apply_det_shadow.py")

    # ── Red Team：執行失敗就不可能有 LLM 產出 ──
    rt = lanes.get("red_team")
    if isinstance(rt, dict) and trade.get("red_team_execution_failed") and \
            rt.get("llm_invoked") is True:
        errors.append(
            "lane_contract.lanes.red_team.llm_invoked=true 但 red_team_execution_failed=true "
            "— 兩者矛盾；RT 失敗時 provenance 應為 'absent'")

    # ── lane 區塊形狀鎖（C1 決策 3；只對 V5.3+ 生效） ──
    for lane_key, field, body_key, allow_null in LANE_SHAPE_LOCKS:
        lane_blk = trade.get(lane_key)
        if not isinstance(lane_blk, dict) or field not in lane_blk:
            continue
        val = lane_blk[field]
        if val is None:
            if not allow_null:
                errors.append(f"{lane_key}.{field} must be an object (C1 形狀鎖；null 不接受)")
            continue
        if not isinstance(val, dict):
            errors.append(
                f"{lane_key}.{field} must be an object, got {type(val).__name__} — "
                "C1 形狀鎖：字串形態已落日，改填結構化 dict（舊 entry 不受影響）")
            continue
        if body_key and body_key not in val and "note" in val:
            errors.append(
                f"{lane_key}.{field}: 正文欄位請用 {body_key!r}（本筆用了 'note'）— "
                "C1 統一命名，消費端不再各寫 fallback")


# ---------------------------------------------------------------------------
# V4.131.13 — extreme-DCF forward validation
# ---------------------------------------------------------------------------
FORWARD_VALIDATION_STATUSES = ("NOT_APPLICABLE", "NO_DATA", "PASS", "STRETCHED", "FAIL")


def _engine_version_at_least(value, floor):
    try:
        got = tuple(int(x) for x in str(value).split("."))
        want = tuple(int(x) for x in str(floor).split("."))
        return got >= want
    except (TypeError, ValueError):
        return False


def check_forward_validation(trade, errors, warnings):
    """Require and rederive the forward block for decision engine 1.1.0+."""
    engine_ver = trade.get("decision_engine_version")
    required = _engine_version_at_least(engine_ver, "1.1.0")
    fv = trade.get("forward_validation")
    if not isinstance(fv, dict):
        if required:
            errors.append(
                "forward_validation missing — decision_engine 1.1.0+ 的 T5 必須讀 pf_quant "
                "forward_validation.v1，不得在資料缺漏時猜 FAIL")
        elif fv is not None:
            warnings.append("forward_validation must be an object when present")
        return
    if fv.get("schema") != FORWARD_VALIDATION_SCHEMA:
        errors.append(f"forward_validation.schema={fv.get('schema')!r}; expected "
                      f"{FORWARD_VALIDATION_SCHEMA!r}")
    if fv.get("status") not in FORWARD_VALIDATION_STATUSES:
        errors.append(f"forward_validation.status={fv.get('status')!r}; expected one of "
                      f"{list(FORWARD_VALIDATION_STATUSES)}")

    pack = trade.get("valuation_pack")
    implied = trade.get("implied_expectations")
    shadow = trade.get("valuation_archetype_shadow")
    if not all(isinstance(x, dict) for x in (pack, implied, shadow)):
        errors.append("forward_validation cannot be rederived: valuation_pack / "
                      "implied_expectations / valuation_archetype_shadow must all be objects")
        return
    raw_pack = dict(pack)
    raw_pack["score"] = pack.get("score_before_forward_validation", pack.get("score"))
    expected = compute_forward_validation(raw_pack, implied, shadow)
    diffs = _diff_steps(expected, fv)
    if diffs:
        errors.append("forward_validation 與 deterministic re-derivation 不符: "
                      + "; ".join(diffs[:8]))
    for field, want in (
            ("score_before_forward_validation", fv.get("valuation_score_before")),
            ("score", fv.get("valuation_score_effective")),
            ("forward_validation_status", fv.get("status"))):
        got = pack.get(field)
        same = (_same_number(got, want, tol=1e-9)
                if isinstance(want, (int, float)) and not isinstance(want, bool)
                else got == want)
        if not same:
            errors.append(f"valuation_pack.{field}={got!r} != forward_validation {want!r}")
    fvs = trade.get("fair_value_summary") or {}
    for field, want in (
            ("score_before_forward_validation", fv.get("valuation_score_before")),
            ("score", fv.get("valuation_score_effective")),
            ("forward_validation_status", fv.get("status"))):
        got = fvs.get(field)
        same = (_same_number(got, want, tol=1e-9)
                if isinstance(want, (int, float)) and not isinstance(want, bool)
                else got == want)
        if not same:
            errors.append(f"fair_value_summary.{field}={got!r} != forward_validation {want!r}")

    val_score = ((trade.get("lane_scores") or {}).get("valuation")
                 if isinstance(trade.get("lane_scores"), dict) else None)
    if required and not _same_number(val_score, fv.get("valuation_score_effective"), tol=1e-9):
        errors.append(f"lane_scores.valuation={val_score!r} != forward_validation."
                      f"valuation_score_effective={fv.get('valuation_score_effective')!r}")
    t5 = (trade.get("calculation_steps") or {}).get("t5_forward_validation")
    if required and not isinstance(t5, dict):
        errors.append("calculation_steps.t5_forward_validation missing for decision_engine 1.1.0+")
    elif isinstance(t5, dict):
        if t5.get("forward_validation_status") != fv.get("status"):
            errors.append("calculation_steps.t5_forward_validation status != forward_validation.status")
        if not _same_number(t5.get("valuation_score"), fv.get("valuation_score_effective"),
                            tol=1e-9):
            errors.append("calculation_steps.t5_forward_validation.valuation_score != "
                          "forward_validation.valuation_score_effective")


# ---------------------------------------------------------------------------
# V4.122.0 §16 — Phase 2.5 CONFLICT & BIAS (`conflict_bias`)
# ---------------------------------------------------------------------------
# V4.122.0 前，Phase 2.5 會改決策卻不留紀錄；189 筆 history 無法追查 T1–T5。
# V4.131.13 再把 T5 接到 forward_validation producer + decision engine 1.1.0。
#
# 本節做**紀錄與重算**；決策後果由 decision engine 執行：
#   - T1–T4 是精確不等式；T5 另要求 forward_validation=FAIL。validator 重算後與
#     export 宣稱的 `triggers_fired` 比對，不符 rc=1。自陳「沒觸發」不再是免費的。
#   - 重算吃的輸入盡量錨在**偽造者改不動的欄位**上（§15 的紀律）：`lane_scores` 受 §13
#     算術鏈保護、valuation 受 pack 一致性硬閘保護、`macro_backdrop_score` 進 §14 的
#     macro_cap 重算、`burry_score` 是 schema 必填。
#   - 兩個新的自陳輸入（`lane_signals` / `tentative_decision`）沒有現成錨，所以各自補一道
#     對錨的一致性檢查：signal 不得與同 lane 的 score 反向；`OVERRIDE_BURRY` 必須對上
#     `burry_override_active`，而那個布林餵 trade_plan_builder 的 ×0.5，受 §14 重算。
#     少了這兩道，新欄位就只是「模型打字出來的」，重算會退化成自己跟自己比對。
#
# 刻意不硬驗 Anti-Bias 的「5 lane 同向」：protocol 沒定義同向是看 score 正負還是看 signal，
#      把一句沒定義過的話變成 rc=1 是單方面收緊。這裡用 score 正負當定義、只出 warning，
#      並把定義寫進 schema 文件等拍板。

CONFLICT_BIAS_REQUIRED_FROM = "2026-08-10"
CONFLICT_BIAS_SCHEMA = "conflict_bias.v1"
#: 精確不等式，進硬性重算比對。ANTI_BIAS 不在內（定義未拍板，見上）。
CONFLICT_HARD_TRIGGERS = ("T1", "T2", "T3", "T4", "T5")
CONFLICT_TRIGGERS = CONFLICT_HARD_TRIGGERS + ("ANTI_BIAS",)
CONFLICT_LANES = ("fundamentals", "sentiment", "news", "technical", "valuation")
LANE_SIGNAL_VALUES = ("BUY", "HOLD", "SELL")
T4_RESOLUTIONS = ("CANCEL", "DOWNGRADE_DECISION", "OVERRIDE_BURRY")
TENTATIVE_DECISIONS = ("BUY", "STAGED_ENTRY", "HOLD", "STAGED_EXIT", "SELL")
BURRY_VETO_BELOW = 20.0          # protocol §PHASE 2 末段：burry_score < 20 → veto_flag
T5_VALUATION_WARN = -2.0         # T5 觸發門檻
T5_EXTREME_BAND = -3.0           # T5 hard downgrade 門檻（engine 1.1.0+）


def _conflict_lane_scores(trade):
    """五個 lane 的 raw score。valuation 以 `lane_scores` 為先、`valuation_lane` 為後。

    兩處都可能是權威：新 entry 的 `lane_scores` 已含 valuation（NOW 2026-08-09），
    舊 entry 只有 `valuation_lane.score`。兩個都在而且不一致時取 `lane_scores` 並回報
    —— 不一致本身就是別節（§13 lane 一致性）的業務，這裡不重複紅。
    """
    ls = trade.get("lane_scores")
    ls = ls if isinstance(ls, dict) else {}
    out = {lane: _numf(ls.get(lane)) for lane in CONFLICT_LANES}
    if out["valuation"] is None:
        vl = trade.get("valuation_lane")
        if isinstance(vl, dict):
            out["valuation"] = _numf(vl.get("score"))
    return out


def evaluate_conflict_triggers(scores, signals, macro, burry, tentative,
                               forward_validation=None):
    """重算 T1–T5 + ANTI_BIAS。值為 True / False / None（None = 輸入缺，無法判定）。

    None 而不是 False：缺輸入時判 False 等於「猜它沒觸發」，而 T4/T5 沒觸發正是最需要
    證據的那一側。缺輸入的 trigger 退出硬性比對並留 warning —— 與 valuation_reviewer_gate
    的「gate 讀不到權威輸入時不得猜」同一條紀律。灌 null 繞過本節不划算：這幾個輸入
    分別是 §13 / §14 / §15 與 schema 必填的守備範圍，拿掉會在別處紅。
    """
    def _some(*vals):
        return None if any(v is None for v in vals) else True

    out = {}

    # T1 — Sentiment 過熱 vs Fundamentals 轉負
    out["T1"] = (None if _some(scores["sentiment"], scores["fundamentals"]) is None
                 else bool(scores["sentiment"] > 3 and scores["fundamentals"] < 0))

    # T2 — News 重挫但 Technical 仍喊進
    out["T2"] = (None if _some(scores["news"], signals.get("technical")) is None
                 else bool(scores["news"] < -3 and signals.get("technical") == "BUY"))

    # T3 — macro 逆風下仍有 lane 高分喊進
    if macro is None:
        out["T3"] = None
    else:
        pairs = [(signals.get(l), scores[l]) for l in CONFLICT_LANES]
        if any(sig is None or sc is None for sig, sc in pairs):
            out["T3"] = None
        else:
            out["T3"] = bool(macro < -3
                             and any(sig == "BUY" and sc > 3 for sig, sc in pairs))

    # T4 — Burry veto 撞上 tentative BUY
    out["T4"] = (None if _some(burry, tentative) is None
                 else bool(burry < BURRY_VETO_BELOW and tentative == "BUY"))

    # T5 — 只有 extreme valuation 通過 deterministic forward block 判 FAIL 才觸發。
    # PASS/STRETCHED 已由 producer 將 score 軟化；NO_DATA 不得被猜成 FAIL。
    t5_candidate = (None if _some(scores["valuation"], tentative) is None
                    else bool(scores["valuation"] <= T5_VALUATION_WARN
                              and tentative in ("BUY", "STAGED_ENTRY")))
    if t5_candidate is not True:
        out["T5"] = t5_candidate
    elif not isinstance(forward_validation, dict):
        out["T5"] = None
    else:
        out["T5"] = forward_validation.get("status") == "FAIL"

    # Anti-Bias — 五 lane 同向（本版定義：score 正負一致；warning-only）
    vals = [scores[l] for l in CONFLICT_LANES]
    out["ANTI_BIAS"] = (None if any(v is None for v in vals)
                        else bool(all(v > 0 for v in vals) or all(v < 0 for v in vals)))
    return out


def check_conflict_bias(entry, trade, errors, warnings):
    """§16 — Phase 2.5 的 `conflict_bias` block：形狀、重算比對、後果錨。

    `CONFLICT_BIAS_REQUIRED_FROM` 之前的 entry 整段跳過（189 筆歷史 entry 一筆都沒有它，
    回填等於在稽核軌跡放假證據 —— 同 §15「為什麼舊 entry 不回填」）。
    日期閘而非版本閘：沿用 V4.116.3 `valuation_reviewer_gate` 的前例，這是一塊純紀錄
    區塊，不值得為它擴一版 session_export_version 並牽動 producer / renderer。
    """
    export_date = str(entry.get("export_date") or entry.get("date") or "")
    cb = trade.get("conflict_bias")

    if cb is None:
        if export_date >= CONFLICT_BIAS_REQUIRED_FROM:
            errors.append(
                f"conflict_bias missing — {CONFLICT_BIAS_REQUIRED_FROM} 起的 entry 必須帶 "
                "Phase 2.5 的輸出（T1–T5 觸發集合 + 裁決）。protocol §PHASE 2.5 一直要求 "
                "PM 產這塊 JSON，過去沒有任何欄位接住它，189 筆歷史 entry 因此一筆紀錄都沒有")
        return
    if not isinstance(cb, dict):
        errors.append(f"conflict_bias must be an object, got {type(cb).__name__}")
        return

    if cb.get("schema") != CONFLICT_BIAS_SCHEMA:
        errors.append(f"conflict_bias.schema={cb.get('schema')!r} — 只認 "
                      f"{CONFLICT_BIAS_SCHEMA!r}")

    # ── 形狀 ───────────────────────────────────────────────────────────────
    tentative = cb.get("tentative_decision")
    if tentative not in TENTATIVE_DECISIONS:
        errors.append(f"conflict_bias.tentative_decision={tentative!r} — "
                      f"expected one of {list(TENTATIVE_DECISIONS)}")
        tentative = None

    signals = {}
    raw_signals = cb.get("lane_signals")
    if not isinstance(raw_signals, dict):
        errors.append("conflict_bias.lane_signals must be an object keyed by lane name — "
                      "T2/T3 的條件寫在 signal 上，沒有它就沒得重算")
    else:
        missing = [l for l in CONFLICT_LANES if l not in raw_signals]
        if missing:
            errors.append(
                f"conflict_bias.lane_signals missing lane(s): {missing} — 五個 lane 一律列出，"
                "沒跑的填 null（省略與『跑了但沒記』事後無法區分，同 C1 契約紀律）")
        for lane in CONFLICT_LANES:
            sig = raw_signals.get(lane)
            if sig is None or lane not in raw_signals:
                continue
            if sig not in LANE_SIGNAL_VALUES:
                errors.append(f"conflict_bias.lane_signals.{lane}={sig!r} — "
                              f"expected one of {list(LANE_SIGNAL_VALUES)} or null")
            else:
                signals[lane] = sig

    proceed = cb.get("proceed_to_phase3")
    if not isinstance(proceed, bool):
        errors.append(f"conflict_bias.proceed_to_phase3={proceed!r} must be a boolean")

    summary = cb.get("conflict_summary")
    if summary is not None and not isinstance(summary, str):
        errors.append("conflict_bias.conflict_summary must be a string when present")

    claimed = cb.get("triggers_fired")
    if not isinstance(claimed, list) or any(not isinstance(t, str) for t in claimed):
        errors.append("conflict_bias.triggers_fired must be an array of strings")
        return
    unknown = [t for t in claimed if t not in CONFLICT_TRIGGERS]
    if unknown:
        errors.append(f"conflict_bias.triggers_fired has unknown trigger(s): {unknown} — "
                      f"只認 {list(CONFLICT_TRIGGERS)}")
    claimed_set = {t for t in claimed if t in CONFLICT_TRIGGERS}
    if len(claimed) != len(set(claimed)):
        errors.append("conflict_bias.triggers_fired has duplicates")

    # ── signal × score 反向矛盾（把新自陳欄位錨回 §13 保護的 lane_scores）────
    scores = _conflict_lane_scores(trade)
    for lane, sig in signals.items():
        sc = scores.get(lane)
        if sc is None:
            continue
        if (sig == "BUY" and sc < 0) or (sig == "SELL" and sc > 0):
            errors.append(
                f"conflict_bias.lane_signals.{lane}={sig!r} 與 lane score {sc} 反向 — "
                "signal 是本節唯一沒有既有錨的輸入，與 score 矛盾時無法判斷哪個才是"
                "這一輪真正的 lane 輸出（score 受 §13 算術鏈保護，signal 不受）")

    # valuation 那一格有現成的權威副本（`valuation_lane.signal`，V5.0+ 必填且與
    # `valuation_pack` 綁死）。五個 signal 裡唯一錨得死的一格，不用白不用。
    _vl = trade.get("valuation_lane")
    if isinstance(_vl, dict) and "valuation" in signals and _vl.get("signal") is not None:
        if signals["valuation"] != _vl.get("signal"):
            errors.append(
                f"conflict_bias.lane_signals.valuation={signals['valuation']!r} != "
                f"valuation_lane.signal={_vl.get('signal')!r} — 同一個 lane 的同一個欄位")

    # ── 重算應觸發集合 ─────────────────────────────────────────────────────
    macro = _numf((entry.get("phase0_macro_snapshot") or {}).get("macro_backdrop_score"))
    burry = _numf(trade.get("burry_score"))
    expected = evaluate_conflict_triggers(
        scores, signals, macro, burry, tentative, trade.get("forward_validation"))

    undecidable = [t for t in CONFLICT_HARD_TRIGGERS if expected[t] is None]
    if undecidable:
        warnings.append(
            f"conflict_bias: {undecidable} 無法重算（缺 lane score / signal / macro / "
            "burry_score / tentative_decision 之一）—— 這幾個 trigger 這一筆只有自陳，"
            "沒有獨立驗證")
    should = {t for t in CONFLICT_HARD_TRIGGERS if expected[t] is True}
    got = {t for t in claimed_set if t in CONFLICT_HARD_TRIGGERS}
    decidable = {t for t in CONFLICT_HARD_TRIGGERS if expected[t] is not None}
    miss = sorted(should - got)
    extra = sorted((got - should) & decidable)
    if miss:
        errors.append(
            f"conflict_bias.triggers_fired 少了 {miss} —— 依 export 自己的欄位重算，"
            f"這些 trigger 的條件成立（lane_scores={ {k: v for k, v in scores.items()} }, "
            f"macro_backdrop_score={macro}, burry_score={burry}, "
            f"tentative_decision={tentative!r}）。protocol §PHASE 2.5 的 T1–T5 是精確"
            "不等式，觸發與否不是判斷題")
    if extra:
        errors.append(
            f"conflict_bias.triggers_fired 多報了 {extra} —— 依 export 自己的欄位重算，"
            "這些 trigger 的條件不成立")

    if claimed_set and not (isinstance(summary, str) and summary.strip()):
        warnings.append(
            "conflict_bias: 有 trigger 觸發但 conflict_summary 是空的 — 觸發集合說得出"
            "「哪一條」，說不出「當下看到什麼」，而後者正是 ≥20 場後要拿來校準的東西")

    # Anti-Bias：定義未拍板，只出 warning（見本節開頭）。
    if expected["ANTI_BIAS"] is True and "ANTI_BIAS" not in claimed_set:
        warnings.append(
            "conflict_bias: 五個 lane score 同向但 triggers_fired 沒有 ANTI_BIAS — "
            "protocol 要求 News 追加 devils_advocate[]（同向的定義未拍板，本節只提醒）")
    if "ANTI_BIAS" in claimed_set and trade.get("devils_advocate_filed") is not True:
        warnings.append(
            "conflict_bias: ANTI_BIAS 觸發但 devils_advocate_filed 不是 true — "
            "Anti-Bias 的唯一產物就是那份 devils_advocate[]")

    # ── 後果錨：只驗有真實產生器、且錨得住的那幾條 ─────────────────────────
    t4 = cb.get("t4_detail")
    if "T4" in claimed_set:
        if not isinstance(t4, dict):
            errors.append("conflict_bias.t4_detail required when T4 fired — "
                          "T4 是唯一能 CANCEL 的仲裁，裁決過程必須留下")
        else:
            resolution = t4.get("resolution")
            if resolution not in T4_RESOLUTIONS:
                errors.append(f"conflict_bias.t4_detail.resolution={resolution!r} — "
                              f"expected one of {list(T4_RESOLUTIONS)}")
            if resolution == "OVERRIDE_BURRY":
                just = t4.get("override_justification")
                if not isinstance(just, str) or len(just.strip()) < 20:
                    errors.append(
                        "conflict_bias.t4_detail.override_justification 需 ≥20 字並具體引用 "
                        "Phase 2 某 analyst 的證據 — protocol 給 OVERRIDE_BURRY 開的三項"
                        "自動成本之一")
                if not t4.get("override_recheck_date"):
                    errors.append("conflict_bias.t4_detail.override_recheck_date 必填 "
                                  "(交易日 + 5 個交易日) — OVERRIDE_BURRY 的三項成本之一")
    elif t4 is not None:
        errors.append("conflict_bias.t4_detail must be null when T4 did not fire")

    # OVERRIDE_BURRY ⟺ burry_override_active，雙向鎖。
    # 這個布林餵 trade_plan_builder 的 ×0.5，鏈尾受 §14 重算 —— 是本節唯一一條錨在
    # 「已經在改倉位的數字」上的後果檢查，也是 T4 這條軌真正硬的地方。
    override_claimed = isinstance(t4, dict) and t4.get("resolution") == "OVERRIDE_BURRY"
    override_active = trade.get("burry_override_active") is True
    if override_claimed and not override_active:
        errors.append(
            "conflict_bias.t4_detail.resolution=OVERRIDE_BURRY 但 burry_override_active "
            "不是 true — override 的第一項成本是 Phase 4 倉位 ×0.5，那條乘數讀的是這個布林")
    if override_active and not override_claimed:
        errors.append(
            "burry_override_active=true 但 conflict_bias 沒有記錄 T4 的 OVERRIDE_BURRY 裁決 — "
            "倉位已經被 ×0.5，決定這麼做的那一步卻沒有留下裁決紀錄")

    t5 = cb.get("t5_detail")
    if "T5" in claimed_set:
        if not isinstance(t5, dict):
            errors.append("conflict_bias.t5_detail required when T5 fired")
        elif not isinstance(t5.get("downgrade_applied"), bool):
            errors.append("conflict_bias.t5_detail.downgrade_applied must be a boolean")
    elif t5 is not None:
        errors.append("conflict_bias.t5_detail must be null when T5 did not fire")

    # 1.1.0 起 T5 有 deterministic producer + engine 後果；舊 engine 保留 warning-only。
    val_score = scores.get("valuation")
    engine_t5 = (trade.get("calculation_steps") or {}).get("t5_forward_validation")
    if _engine_version_at_least(trade.get("decision_engine_version"), "1.1.0"):
        if "T5" in claimed_set and isinstance(t5, dict) and isinstance(engine_t5, dict):
            diffs = _diff_steps(engine_t5, t5)
            if diffs:
                errors.append("conflict_bias.t5_detail != decision engine T5 output: "
                              + "; ".join(diffs[:6]))
        if isinstance(engine_t5, dict) and engine_t5.get("hard_downgrade_eligible") is True \
                and engine_t5.get("downgrade_applied") is not True:
            errors.append("T5 hard downgrade eligible but decision_engine did not apply downgrade")
    elif (val_score is not None and val_score <= T5_EXTREME_BAND
          and trade.get("final_decision") in ("BUY", "STAGED_ENTRY")):
        warnings.append(
            f"conflict_bias: valuation score {val_score} ≤ {T5_EXTREME_BAND} 而 final_decision="
            f"{trade.get('final_decision')!r} — protocol T5 宣稱此時自動降階，但 "
            "這是 decision_engine 1.0.x 的 legacy entry；當時 T5 尚無 producer，故僅留 warning。"
            "1.1.0+ 必須帶 forward_validation 並由 engine 執行後果")

    # proceed_to_phase3=false → protocol 明寫「跳 Phase 5 輸出 CANCEL」，而
    # decision_engine.py 也把它當 Auto REJECT 的一條理由，兩邊都錨得住。
    if proceed is False and trade.get("final_action") != "CANCEL":
        errors.append(
            f"conflict_bias.proceed_to_phase3=false 但 final_action="
            f"{trade.get('final_action')!r} — protocol §PHASE 2.5：不進 Phase 3 就是 CANCEL"
            "（decision_engine.py 也把它列為 Auto REJECT 的觸發理由）")


# ---------------------------------------------------------------------------
# V4.122.0 §17 — Phase 2 FAN-IN 紀律（inline fallback 的 confidence cap）
# ---------------------------------------------------------------------------
# protocol §PHASE 2「Fan-In 驗證 + Inline Fallback」自 V4.8 就寫著「單一 subagent 失敗 →
# PM inline 該 lane；confidence cap 0.6」。validator 過去只收 `phase2_fanout_mode` 與
# `degraded_analysts` 兩個欄位、沒有任何一處驗算那個 cap —— 又一條「規則寫了但沒接線」。
#
# 沒接線的直接後果是欄位自己爛掉：188 筆 export 裡，`degraded_analysts` 用過 **10 種寫法
# 指涉 5 個 lane**（`News` / `News (skill fallback to web)` / `Valuation` /
# `Valuation_Specialist` / `Valuation_Specialist_low_anchor_count_3of6` …），`phase2_fanout_mode`
# 出現過表外值 `FULL`。**沒有任何消費端讀得動它**，所以 cap 想接也接不上去——這正是
# 「欄位存在」與「欄位可用」的差別。
#
# cap 怎麼驗：`c_eff()` 把 raw confidence 量化成三檔（<0.45→0.35 / <0.675→0.60 / else 0.72），
# 所以「confidence ≤ 0.6」等價於「C_eff 不得為 0.72」——0.6 落在 0.60 那一檔，合規的 lane
# 不可能顯示 0.72，零偽陽。C_eff 取自 `calculation_steps` 的 step 字串（`W × score × C_eff`），
# 那塊受 §13 重算與 §5l 的 engine artifact parity 保護，是偽造者改不動的錨。

FANIN_REQUIRED_FROM = "2026-08-10"
FANOUT_MODES = ("PARALLEL_SUBAGENT", "PARTIAL_FALLBACK", "FULL_FALLBACK")
#: 「inline fallback confidence cap 0.6」→ 量化後的上限檔位。
DEGRADED_MAX_CEFF = 0.60


def resolve_degraded_lane(label):
    """free-form 的 degraded 標籤 → canonical lane 名；解析不出回 None。

    刻意用**前綴**比對而不是完全相等：歷史上那 10 種寫法全部是「canonical 名 + 附註」
    （`News (skill fallback to web)`、`Valuation_Specialist_low_anchor_count_3of6`），
    附註帶著真資訊，不該為了機器可讀把它砍掉。要求的只是**開頭必須是 lane 名**，
    這樣既保留註記又讓每個元素解析得回唯一一個 lane。
    """
    s = str(label).strip().lower()
    hits = [lane for lane in CONFLICT_LANES if s.startswith(lane)]
    return hits[0] if len(hits) == 1 else None


def _step_ceffs(cs):
    """從 `calculation_steps` 的 step 字串取每個 lane 的 C_eff。

    重用 §13 的 `_STEP_RE` / `_STEP_LANES`，不另寫一份 parser —— 同一個字串格式兩處各
    解析一次，任一方改動後另一方會走「解析不出就靜默」分支（§2c 成員 #8）。
    """
    out = {}
    if not isinstance(cs, dict):
        return out
    for key, lane in _STEP_LANES.items():
        raw = cs.get(key)
        if not isinstance(raw, str):
            continue
        m = _STEP_RE.match(raw)
        if m:
            out[lane] = _dash(m.group(3))
    return out


def check_fanin_discipline(entry, trade, errors, warnings):
    """§17 — fan-out mode 值域、degraded lane 可解析性、inline fallback 的 confidence cap。

    分兩層時效：**cap 與 FULL_FALLBACK 一致性是 V4.8 就存在的規則**，只要輸入齊備就驗
    （degraded 為空時自然完全靜默，那是絕大多數場次）；**「名稱必須可解析」與 mode 值域是
    V4.122.0 新增的要求**，只對 `FANIN_REQUIRED_FROM` 之後的 entry 為 error，之前留 warning
    —— 舊 entry 的 10 種寫法是既成事實，回頭紅它們沒有意義。
    """
    export_date = str(entry.get("export_date") or entry.get("date") or "")
    strict = export_date >= FANIN_REQUIRED_FROM
    emit = errors if strict else warnings

    mode = trade.get("phase2_fanout_mode")
    if mode is not None and mode not in FANOUT_MODES:
        emit.append(f"phase2_fanout_mode={mode!r} outside {list(FANOUT_MODES)} — "
                    "歷史上出現過表外值 `FULL`，值域從未被驗過")

    raw_degraded = trade.get("degraded_analysts")
    if raw_degraded is None:
        return
    if not isinstance(raw_degraded, list):
        errors.append(f"degraded_analysts must be an array, got "
                      f"{type(raw_degraded).__name__}")
        return

    resolved, unresolved = [], []
    for item in raw_degraded:
        lane = resolve_degraded_lane(item) if isinstance(item, str) else None
        (resolved.append((lane, item)) if lane else unresolved.append(item))
    if unresolved:
        emit.append(
            f"degraded_analysts 有無法解析回 lane 名的元素: {unresolved} — 每個元素必須"
            f"以 {list(CONFLICT_LANES)} 之一開頭（後面可接附註，如 "
            "'News (skill fallback to web)'）。解析不回 lane 的標籤讓 confidence cap "
            "無從對應，這正是 cap 從 V4.8 起沒被驗過的原因")

    lanes = [lane for lane, _ in resolved]
    dupes = sorted({x for x in lanes if lanes.count(x) > 1})
    if dupes:
        errors.append(f"degraded_analysts 同一個 lane 出現多次: {dupes}")

    # ── 真正的 cap：inline fallback 的 lane 不得帶滿檔信心 ────────────────
    ceffs = _step_ceffs(trade.get("calculation_steps"))
    for lane, label in resolved:
        ce = ceffs.get(lane)
        if ce is None:
            continue
        if ce > DEGRADED_MAX_CEFF + 1e-9:
            errors.append(
                f"degraded lane {label!r} 的 C_eff={ce} 超過 inline fallback 的 "
                f"confidence cap 0.6（量化後上限 {DEGRADED_MAX_CEFF}）— protocol "
                "§PHASE 2 Fan-In：subagent 失敗改由 PM inline 的 lane，confidence 一律 "
                "cap 在 0.6。降級的 lane 帶滿檔信心進加權，等於失敗反而加重它的話語權")

    n = len(raw_degraded)
    if n >= 2 and mode not in ("PARTIAL_FALLBACK", "FULL_FALLBACK"):
        emit.append(
            f"degraded_analysts 有 {n} 個 lane 但 phase2_fanout_mode={mode!r} — "
            "protocol Fan-In 表：2-4 個失敗 = PARTIAL_FALLBACK、5 個 = FULL_FALLBACK")
    if n == 1 and mode == "PARALLEL_SUBAGENT":
        warnings.append(
            "degraded_analysts 只有 1 個 lane 而 mode 仍是 PARALLEL_SUBAGENT — "
            "protocol Fan-In 表沒有定義單一失敗時的 mode，本節不當錯處理（定義待拍板）")

    if mode == "FULL_FALLBACK":
        if n != 5:
            errors.append(f"phase2_fanout_mode=FULL_FALLBACK 但 degraded_analysts 有 {n} "
                          "個 lane — FULL_FALLBACK 的定義就是 5 個 subagent 全失敗")
        rtv = trade.get("red_team_verdict")
        if rtv != "STRONG_COUNTER":
            errors.append(
                f"phase2_fanout_mode=FULL_FALLBACK 但 red_team_verdict={rtv!r} — "
                "protocol §PHASE 2.8：FULL_FALLBACK 時 Red Team 強制 STRONG_COUNTER"
                "（五個 lane 全是 PM inline，沒有獨立證據可供反駁）")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate latest investment session export")
    ap.add_argument("--history", default=HISTORY_JSON,
                    help="history JSON path (default: investment/invest_logs/history.json)")
    ap.add_argument("--require-committed-to",
                    help="also require this session digest to exist in the named history array")
    args = ap.parse_args(argv)
    history_path = args.history
    if not os.path.exists(history_path):
        fail([f"history.json not found at {history_path}"])

    with open(history_path, "r", encoding="utf-8") as fp:
        hist = json.load(fp)

    if isinstance(hist, dict):
        # Parallel invest runs validate their isolated session export. The
        # committed history remains a list for every existing consumer.
        entry = hist
    elif isinstance(hist, list) and hist:
        entry = hist[-1]
    else:
        fail(["session export must be an object or a non-empty history array"])
    errors = []
    warnings = []  # advisory-only findings — printed but never fail the gate

    if args.require_committed_to:
        try:
            with open(args.require_committed_to, "r", encoding="utf-8") as fp:
                committed = json.load(fp)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"committed history unreadable: {args.require_committed_to}: {exc}")
            committed = None
        target_provenance = entry.get("export_provenance")
        target_digest = (target_provenance.get("entry_digest")
                         if isinstance(target_provenance, dict) else None)
        if not target_digest:
            errors.append("cannot verify history commit: isolated session has no provenance digest")
        elif not isinstance(committed, list):
            if committed is not None:
                errors.append("committed history must be a JSON array")
        elif not any(
            isinstance(item.get("export_provenance"), dict)
            and item["export_provenance"].get("entry_digest") == target_digest
            for item in committed if isinstance(item, dict)
        ):
            errors.append(
                f"validated session was not committed to {args.require_committed_to} "
                f"(digest {target_digest[:20]}… missing)")

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

    # ── 2e. V5.2 mis-stamp guard (V4.90.0) ───────────────────────────────
    # Mirror of 2d one version up: `lane_contract` only exists on entries the C1
    # post-processor wrote, which is exactly what V5.3 makes mandatory. Stamping such an
    # entry older would route it round the version gate in §15 — and would also plant a
    # provenance record on an entry whose lanes were never produced under the contract.
    if ver not in LANE_CONTRACT_REQUIRED_VERSIONS:
        trade_first = ((entry.get("trades_this_session") or [{}])[0]) or {}
        if trade_first.get("lane_contract") is not None:
            errors.append(
                f"session_export_version={ver!r} but entry carries lane_contract — "
                f"C1 contract output stamps {CURRENT_VERSION!r}. Patch the version field; "
                f"keeping {ver} bypasses the §15 lane_contract gate."
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
            # V4.108.0 — 第 9 根 fwd_earnings_discounted（虧損題材股專用條件錨）
            known_anchors = {"dcf_unlevered", "dcf_levered", "dcf_self_built",
                             "analyst_pt_consensus", "peer_pe_implied", "comps_implied",
                             "owner_earnings_mult", "forecaster_blend",
                             "fwd_earnings_discounted"}
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
                    if not _same_projection(pack.get(field), fvs.get(field)):
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
                    # V4.116.0 — Phase 1.5's script-sourced anchors are mandatory.
                    # `script_not_run` is set by
                    # `compute_price_framework.mark_unrun_anchor_scripts` when the
                    # anchor has no value AND the script's artifact is absent or
                    # stale, which is a different thing from the script running and
                    # having nothing usable to say.
                    #
                    # This is fatal rather than a warning because of what skipping
                    # costs: on 2026-08-09 NOW, `dcf_self_built` and `comps_implied`
                    # were both never run, the fundamental family collapsed to two
                    # correlation groups, and `owner_earnings_mult` — an anchor the
                    # engine had itself flagged as an outlier — carried an effective
                    # weight of 0.275 against a raw 0.05 and produced the
                    # `extreme_overvalued` verdict single-handedly. The protocol
                    # already called these mandatory; until now nothing enforced it.
                    if detail.get("reason") in (SCRIPT_NOT_RUN, ANCHOR_DROPPED_VALUE):
                        spec = SCRIPT_SOURCED_ANCHORS.get(name) or {}
                        cmd = spec.get("command") or ""
                        ticker = str(trade.get("ticker") or entry.get("ticker") or "<T>")
                        if detail.get("reason") == SCRIPT_NOT_RUN:
                            errors.append(
                                f"valuation_pack.anchors.{name}: mandatory Phase 1.5 script "
                                f"produced no credible artifact — it was not run, or its "
                                f"output is stale/malformed"
                                + (f". Run `{cmd.format(t=ticker.upper())}`" if cmd else "")
                            )
                        else:
                            # Wiring bug, not a skipped step: the artifact holds a
                            # usable number the anchor never received.
                            errors.append(
                                f"valuation_pack.anchors.{name}: the script's artifact carries a "
                                f"usable {spec.get('value_key')} but the anchor is empty — the "
                                f"value was computed and then dropped before the pack"
                            )
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
                    if field not in vl:
                        continue
                    # pack field null = nothing to project. Protocol「缺 anchor 處理」puts
                    # the lane on the INSUFFICIENT_DATA path, where it emits its own bounded
                    # |score| < 2 at confidence=low instead of mirroring the pack. Enforce
                    # that bound here rather than demanding a projection that cannot exist.
                    if pack.get(field) is None:
                        if field == "score" and isinstance(vl.get(field), (int, float)) \
                                and abs(float(vl[field])) >= 2:
                            errors.append(
                                "valuation_lane.score: valuation_pack.score is null "
                                "(INSUFFICIENT_DATA path) — |score| must stay < 2"
                            )
                        continue
                    if not _same_number(vl.get(field), pack.get(field)):
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

    # ── 10b. V4.108.0 — speculative governor（第 9 根錨解鎖後的籌碼限制）─────
    # 設計意圖：fwd_earnings_discounted 讓虧損題材股重新拿得到估值、decision cap 解除；
    # 這裡確保「解鎖」不會偷渡成正常倉位。兩條 integrity 檢查是關鍵——只要 export 裡
    # 出現 pre-profit 錨或 sell-side-only 證據，speculative_grade 就必須是 true，
    # 否則 PM 可以用新錨解鎖決策卻不掛 governor。
    spec_grade = trade.get("speculative_grade")
    pack_for_spec = trade.get("valuation_pack")
    fwd_live = sell_side_only = False
    if isinstance(pack_for_spec, dict):
        fwd_detail = (pack_for_spec.get("anchors") or {}).get("fwd_earnings_discounted")
        fwd_live = isinstance(fwd_detail, dict) and fwd_detail.get("status") == "eligible"
        sell_side_only = (
            (pack_for_spec.get("evidence_independence") or {}).get("sell_side_only") is True)
    if (fwd_live or sell_side_only) and spec_grade is not True:
        errors.append(
            "valuation_pack 顯示 "
            + ("pre-profit 錨 live" if fwd_live else "")
            + (" + " if fwd_live and sell_side_only else "")
            + ("賣方預估是唯一證據" if sell_side_only else "")
            + " — 必須同時設 speculative_grade=true（Phase 4.6 governor）"
        )
    if spec_grade is True:
        # enum 與兩個上限都從 decision_engine import——governor 與它的驗收共用同一組
        # 常數，改一邊而忘了另一邊的漂移在此結構性不可能發生。
        sr = trade.get("speculative_reasons")
        if not isinstance(sr, list) or not sr:
            errors.append("speculative_grade=true requires a non-empty speculative_reasons list")
        elif any(r not in SPECULATIVE_REASONS for r in sr):
            errors.append(
                f"speculative_reasons must be a subset of {SPECULATIVE_REASONS}, got {sr!r}")
        sps = trade.get("position_size_pct")
        if isinstance(sps, (int, float)) and sps > SPECULATIVE_SIZE_CAP_PCT:
            errors.append(
                f"speculative_grade=true requires position_size_pct ≤ "
                f"{SPECULATIVE_SIZE_CAP_PCT} ({SPECULATIVE_SIZE_CAP_PCT:.0%}), got {sps}")
        sac = trade.get("avg_confidence")
        if isinstance(sac, (int, float)) and sac > SPECULATIVE_CONFIDENCE_CAP:
            errors.append(
                f"speculative_grade=true requires avg_confidence ≤ "
                f"{SPECULATIVE_CONFIDENCE_CAP}, got {sac}")

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
            if not _same_projection(lt.get("weighted_fair_value"), fvs_ok.get("weighted_fair_value")):
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
        # V4.117.0 起這欄由 §5g-bis 硬性驗；這裡只留給 cutoff 之前的舊 entry，
        # 否則同一個問題會同時吐 warning 和 error。
        if str(entry.get("export_date") or "") < PT_MOMENTUM_REQUIRED_FROM:
            prm = nl.get("pt_revision_momentum")
            if isinstance(prm, dict):
                d = prm.get("direction")
                if d not in (None, "UP", "DOWN", "FLAT", "UNKNOWN"):
                    warnings.append(f"news_lane.pt_revision_momentum.direction invalid: {d!r}")
            elif prm is not None:
                warnings.append("news_lane.pt_revision_momentum must be an object when present")

    # ── 5g-bis. V4.117.0 — News lane 必須解析 pt_revision_momentum ────────────
    _check_pt_revision_momentum(entry, trade, errors, warnings)
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

    # ── 5i. V4.89.0 — valuation_reviewer_gate（shadow-only）───────────────────
    # 缺 block 對**舊** entry 完全靜默：172 筆歷史 entry 都沒有它，warning 會變成
    # 純噪音。
    #
    # V4.116.3：對 `VALUATION_GATE_REQUIRED_FROM` 之後的 session 改成 error。
    # protocol §PHASE 2 早就寫著這個 block「寫進 session export」，但 validator 只在
    # 它出現時才驗——於是它實際上是選配的。2026-08-09 的兩次實測把後果攤開：codex
    # 跑了 gate 並帶進 export，agy 一次都沒跑，兩者都 rc=0。**有閘的都做了、沒閘的
    # 照樣跳過**，這個對照本身就是紀律靠閘不靠叮嚀的證據。
    #
    # 這個 block 是 shadow 樣本的唯一來源；不跑它，將來要不要讓 gate 生效這個決定
    # 就永遠沒有資料可依據——損失是靜默且累積的。
    # ── 5i-bis. V4.116.3 — Technical lane 不得超出自家 script 的 rubric ────────
    _check_technical_rubric(entry, trade, errors, warnings)

    # ── 5k. V4.117.0 — history.json 只由 append_session_export.py 寫 ──────────
    _check_export_provenance(entry, errors, warnings)

    # ── 5l. V4.117.0 — calculation_steps 必須等於 engine 最後一次的輸出 ────────
    _check_calculation_steps_parity(entry, trade, errors, warnings)

    vrg = trade.get("valuation_reviewer_gate")
    if not isinstance(vrg, dict):
        export_date = str(entry.get("export_date") or "")
        if export_date >= VALUATION_GATE_REQUIRED_FROM:
            errors.append(
                f"valuation_reviewer_gate missing — protocol §PHASE 2 要求跑 "
                f"`python3 investment/scripts/valuation_reviewer_gate.py --from-quant "
                f"investment/invest_logs/{export_date}_{entry.get('ticker', '<T>')}"
                f"_pf_quant.json` 並把 {{would_invoke, triggers_fired, shadow_only}} "
                f"寫進 export")
    if isinstance(vrg, dict):
        known = {"transition_case_active", "no_peer_cohort", "structural_shift_typed",
                 "anchor_conflict_severe", "low_quality_possible_buy"}
        fired = vrg.get("triggers_fired")
        if fired is None:
            warnings.append("valuation_reviewer_gate.triggers_fired missing")
        elif not isinstance(fired, list) or any(t not in known for t in fired):
            warnings.append(f"valuation_reviewer_gate.triggers_fired invalid: {fired!r}")
        wi = vrg.get("would_invoke")
        if wi not in (None, True, False):
            warnings.append("valuation_reviewer_gate.would_invoke must be bool|null")
        elif isinstance(fired, list) and wi is not None and wi != bool(fired):
            warnings.append(
                f"valuation_reviewer_gate.would_invoke={wi} contradicts triggers_fired={fired}")
        shadow_only = vrg.get("shadow_only")
        if shadow_only is True:
            pass
        elif shadow_only is None:
            # gate 永遠會寫這個欄位；缺欄本身即異常，否則省略它就是繞過下面那條 error。
            warnings.append("valuation_reviewer_gate.shadow_only missing")
        else:
            # 只認 JSON true。`is False` 版本讓 0／"false" 只拿 warning —— 對「守翻預設
            # 大門」的欄位，任何非 true 的值都等同宣告 gate 生效過，一律 error。
            errors.append(f"valuation_reviewer_gate.shadow_only={shadow_only!r} — 只認 true；"
                          "翻預設需使用者拍板，session 不得自行讓 gate 生效")
    elif vrg is not None:
        warnings.append("valuation_reviewer_gate must be an object when present")

    # ── 5j. V4.91.0 — sentiment_det（L5 shadow-only，warning-only）──────────
    # 缺 block 完全靜默：舊 entry 沒有它，warning 會變成純噪音（同 5i gate 前例）。
    # 但 shadow_only=false 要擋 —— 那代表有人讓 det 分數真的取代了 LLM lane，而翻預設
    # 需要使用者拍板 + weight 凍結窗，不是任一 session 可以自行決定的事。
    sdt = trade.get("sentiment_det")
    if isinstance(sdt, dict):
        sdt_shadow = sdt.get("shadow_only")
        if sdt_shadow is True:
            pass
        elif sdt_shadow is None:
            warnings.append("sentiment_det.shadow_only missing")
        else:
            # 同 5i：只認 JSON true，0／"false" 不得靠型別繞成 warning。
            errors.append(f"sentiment_det.shadow_only={sdt_shadow!r} — 只認 true；"
                          "L5 翻預設需使用者拍板，session 不得自行讓 det 分數取代 LLM lane")
        sc = sdt.get("score")
        if sc is not None and (isinstance(sc, bool) or not isinstance(sc, (int, float))):
            warnings.append(f"sentiment_det.score must be number|null, got {sc!r}")
        elif isinstance(sc, (int, float)) and not isinstance(sc, bool) and not -3.0 <= sc <= 3.0:
            warnings.append(f"sentiment_det.score={sc} outside the lane range [-3, +3]")
        if sc is None and not sdt.get("degraded_reason"):
            warnings.append("sentiment_det.score is null but degraded_reason is empty — "
                            "算不出分數必須說明原因（缺市場層 / 缺輸入）")
        if not isinstance(sdt.get("producer_version"), str) or not sdt.get("producer_version"):
            warnings.append("sentiment_det.producer_version missing — shadow 樣本必須可歸屬"
                            "到產生它的公式版本，否則翻預設時不知道累積的是哪一版的數據")
        # 契約那一格是 validator 驗過的權威副本；不一致代表 block 或契約被事後改過。
        _sent_slot = ((trade.get("lane_contract") or {}).get("lanes") or {}).get("sentiment")
        if isinstance(_sent_slot, dict):
            _slot_score = _sent_slot.get("shadow_score")
            _same = (_slot_score is None and sc is None) or _same_number(_slot_score, sc, tol=1e-9)
            if not _same:
                warnings.append(
                    f"lane_contract.lanes.sentiment.shadow_score={_slot_score!r} != "
                    f"sentiment_det.score={sc!r} — 重跑 apply_det_shadow.py")
    elif sdt is not None:
        warnings.append("sentiment_det must be an object when present")

    # ── 13. V4.80.0 — Phase 3 arithmetic re-derivation (decision_engine parity) ──
    # 舊 entry（無 calculation_steps 也無 decision_engine_version）整段跳過 → 向後相容。
    check_forward_validation(trade, errors, warnings)
    check_phase3_arithmetic(entry, trade, errors, warnings)

    # ── 14. V4.82.0 — Phase 4 sizing re-derivation (trade_plan_builder parity) ──
    # 舊 entry（無 risk_audit 也無 trade_plan_builder_version）整段跳過 → 向後相容。
    check_phase4_sizing(entry, trade, errors, warnings)

    # ── 15. V4.90.0 — C1 統一 lane 資料契約 + lane 區塊形狀鎖 ──
    # 版號不在 LANE_CONTRACT_REQUIRED_VERSIONS 的 entry 整段跳過 → 向後相容。
    check_lane_contract(entry, trade, errors, warnings)

    # ── 16. V4.122.0 — Phase 2.5 conflict & bias（重算應觸發集合）──
    # CONFLICT_BIAS_REQUIRED_FROM 之前的 entry 整段跳過 → 舊 entry 不回填。
    check_conflict_bias(entry, trade, errors, warnings)

    # ── 17. V4.122.0 — Phase 2 fan-in 紀律（inline fallback 的 confidence cap）──
    # cap 與 FULL_FALLBACK 一致性只要輸入齊備就驗；名稱可解析性與 mode 值域
    # 對 FANIN_REQUIRED_FROM 之前的 entry 只給 warning。
    check_fanin_discipline(entry, trade, errors, warnings)

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

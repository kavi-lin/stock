#!/usr/bin/env python3
"""build_session_export.py — Phase 5 Step 1 assembler (V4.126.0, 0 LLM).

Replaces the throwaway `build_<TICKER>_session.py` the PM used to hand-write on every
run. Reads the artifacts each earlier phase already left on disk, takes ONE
model-authored qualitative file for the parts no script can derive, and emits BOTH
Phase 5 inputs:

  * the session export entry  → stdout, or `--session-out` for parallel runs
  * the phase_inputs bundle   → `invest_logs/phase_inputs/<DATE>_<TICKER>.json`

Why this exists
---------------
V4.117.0 made the export's *content* tool-produced (provenance digest, engine parity).
Its *assembly* stayed hand-typed, so every run re-invented ~130 lines of literals. On
2026-08-10 a META run's assembler died on `KeyError: 'avg_confidence'` after 7.4M input
tokens — it had read the engine artifact as if it were the full Phase 3 output. That
particular trap is closed (V4.126.0 persists all 24 fields), but the class is not: a
hand-typed assembler can mistype any of ~140 fields and nothing catches it until the
validator, or worse, until the number is wrong but plausible.

The closed-schema rule
----------------------
`QUALITATIVE_ONLY` is exhaustive and `DERIVED_KEYS` is rejected on sight. A qualitative
file carrying `final_score` is an ERROR, not a merge — the whole point is that the model
cannot hand-type a number a script can compute. Without that rule the file grows back
into the 130-line literal blob it replaced.

Single-sourcing
---------------
Per-lane `score` / `signal` are given ONCE under `lanes.<name>`. `lane_scores`,
`conflict_bias.lane_signals` and the bundle's `lanes` block are all derived from that
one place, so they cannot drift apart — a whole family of §16 contradictions
("signal 與同 lane score 反向", "lane_signals.valuation != valuation_lane.signal")
becomes unrepresentable rather than merely validated.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

import validate_phase0 as phase0_gate

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

SCHEMA = "p5-qualitative/1.0"
BUNDLE_VERSION = "P5-INPUTS/1.0"
SESSION_EXPORT_VERSION = "V5.4"
LANES = ("fundamentals", "sentiment", "news", "technical", "valuation")

# Keys the PM may supply. Anything outside this set is rejected, so the file cannot
# silently regrow into a hand-typed export.
QUALITATIVE_ONLY = {
    "schema", "ticker", "date",
    "lanes",                    # per-lane signal/score/confidence/key_factors/risk_flags
    "red_team",                 # verdict + prose + the two graded numbers
    "burry_narrative",
    "conflict_bias",            # tentative_decision / conflict_summary / t4_t5 detail
    "macro_context", "watch_conditions", "key_risks", "bias_notes",
    "phase2_fanout_mode", "degraded_analysts",
    "decision_point_days",
    "devils_advocate_filed",
    "trade_metadata",
    "lane_detail",
    "last_outcome",
}

# Derivable from an artifact on disk. Present in the qualitative file → rc=1.
DERIVED_KEYS = {
    "final_score", "final_decision", "final_action", "calculation_steps",
    "avg_confidence", "avg_confidence_raw", "decision_engine_version",
    "hot_zone_probe", "hot_zone_probe_tier", "hot_zone_eval",
    "decision_cap_active", "decision_cap_reason",
    "lane_scores", "lane_signals",
    "macro_multiplier", "macro_backdrop_score", "macro_alignment",
    "phase0_macro_snapshot", "phase0_file",
    "burry_score", "burry_override_active",
    "entry_aggressive", "entry_conservative", "take_profit", "stop_loss",
    "risk_reward_ratio", "position_size_pct", "staged_split", "risk_audit",
    "trade_plan_builder_version", "mandatory_risk_flags", "time_horizon",
    "valuation_pack", "fair_value_summary", "fair_value_range",
    "implied_expectations", "valuation_archetype_shadow", "forward_validation",
    "valuation_explained_range",
    "valuation_reviewer_gate", "analysis_price",
    "consensus_bonus_applied", "transition_data_stale_or_inconsistent",
    "det_shadow", "lane_contract", "provenance", "producer_version",
    "export_provenance", "session_export_version",
    "multi_horizon_price_framework", "burry_score",
}

RED_TEAM_REQUIRED = {"verdict", "counter_thesis", "kill_conditions",
                     "counter_evidence_strength", "thesis_break_probability"}
LANE_REQUIRED = {"signal", "key_factors", "risk_flags"}
# Rejected INSIDE lanes.<name>: the phase-3 engine input already persists the exact
# score/confidence the decision math consumed. Retyping them is the two-source drift
# render_investment_report.check_consistency() exists to catch — on 2026-08-10 it did.
LANE_REJECTED = {"score", "confidence"}


def _engine_version_at_least(value, floor):
    try:
        return tuple(map(int, str(value).split("."))) >= tuple(map(int, floor.split(".")))
    except (TypeError, ValueError):
        return False


class BuildError(SystemExit):
    def __init__(self, msg):
        super().__init__(f"[build_session_export] ✗ {msg}")


# ---------------------------------------------------------------------------
# artifact loading — every path is named, nothing is guessed or defaulted
# ---------------------------------------------------------------------------
def _read_json(path, what):
    if not os.path.exists(path):
        raise BuildError(
            f"{what} 不存在: {os.path.relpath(path, ROOT)}\n"
            f"         這一包是前面某個 phase 應該落地的產出物。**不要手補**——"
            f"回去把那個 phase 跑完，或確認它為什麼沒寫檔。")
    try:
        with open(path, encoding="utf-8") as fp:
            return json.load(fp)
    except json.JSONDecodeError as e:
        raise BuildError(f"{what} 不是合法 JSON ({os.path.relpath(path, ROOT)}): {e}")


def _run_json(args, what):
    try:
        p = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    except OSError as e:
        raise BuildError(f"{what} 無法執行: {e}")
    if p.returncode != 0:
        raise BuildError(f"{what} rc={p.returncode}，停止組裝（V4.116.1 閘門紀律）\n"
                         f"         stderr: {(p.stderr or '').strip()[:400]}")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError as e:
        raise BuildError(f"{what} 的輸出不是合法 JSON: {e}")


def _resolve_phase0_path(ticker, supplied=None):
    """Resolve the shared snapshot once; an explicit factpack path always wins."""
    if supplied:
        return supplied if os.path.isabs(supplied) else os.path.join(ROOT, supplied)
    path = phase0_gate.find_latest(
        ticker, logs_dir=os.path.join(ROOT, "investment/invest_logs"))
    if not path:
        raise BuildError(
            "找不到 shared Phase 0 snapshot。重跑 Phase 0，產生 "
            "investment/invest_logs/YYYY-MM-DD_phase0.json。")
    return path


def load_artifacts(ticker, date, *, p3_input, p4_input, quant_path=None, phase0_path=None):
    """Collect every deterministic input. Missing artifact → rc=1 naming the file."""
    t = ticker.upper()
    quant_path = quant_path or os.path.join(
        ROOT, f"investment/invest_logs/{date}_{t}_pf_quant.json")
    phase0_path = _resolve_phase0_path(t, phase0_path)
    engine_path = os.path.join(
        ROOT, f"investment/invest_logs/decision_engine/{t}_decision_engine.json")

    engine = _read_json(engine_path, "decision_engine artifact")
    if str(engine.get("ticker", "")).upper() != t:
        raise BuildError(
            f"decision_engine artifact 是 {engine.get('ticker')!r} 的，不是 {t} 的。"
            f"單槽快取被別支股票蓋掉了 —— 重跑 `decision_engine.py --phase 3`。")
    # V4.126.0 persists the full phase-3 output; a 6-key artifact is a pre-fix leftover.
    missing_engine = [k for k in ("avg_confidence", "hot_zone_eval", "calculation_steps")
                      if k not in engine]
    if missing_engine:
        raise BuildError(
            f"decision_engine artifact 缺 {missing_engine} —— 這是 V4.126.0 之前的舊檔"
            f"（只存 6 欄）。重跑 `decision_engine.py --phase 3` 產生完整版。")

    p3 = _read_json(os.path.join(ROOT, p3_input) if not os.path.isabs(p3_input) else p3_input,
                    "phase-3 engine 輸入")
    p4 = _read_json(os.path.join(ROOT, p4_input) if not os.path.isabs(p4_input) else p4_input,
                    "phase-4 trade_plan 輸入")
    quant = _read_json(quant_path, "pf_quant artifact")
    for f in ("lane_scores", "lane_confidence"):
        if not isinstance(p3.get(f), dict):
            raise BuildError(f"phase-3 engine 輸入缺 {f}（或不是 object）")
    if _engine_version_at_least(engine.get("decision_engine_version"), "1.1.0"):
        expected_forward = (quant.get("quant_blocks") or {}).get("forward_validation")
        if not isinstance(expected_forward, dict):
            raise BuildError("pf_quant artifact 缺 forward_validation（decision engine 1.1.0 必填）")
        if p3.get("forward_validation") != expected_forward:
            raise BuildError(
                "phase-3 engine 輸入的 forward_validation 不是 pf_quant artifact 原樣副本")
        if engine.get("forward_validation") != expected_forward:
            raise BuildError(
                "decision_engine artifact 的 forward_validation 與 pf_quant artifact 不一致；"
                "用同一份 p3 input 重跑 decision_engine.py")

    return {
        "engine": engine,
        "p3": p3,
        "p4": p4,
        "quant": quant,
        "phase0": _read_json(phase0_path, "phase0 artifact"),
        "phase0_path": phase0_path,
        "plan": _run_json(["python3", "investment/scripts/trade_plan_builder.py",
                           "--from-file", p4_input], "trade_plan_builder.py"),
        "gate": _run_json(["python3", "investment/scripts/valuation_reviewer_gate.py",
                           "--from-quant", os.path.relpath(quant_path, ROOT)],
                          "valuation_reviewer_gate.py"),
    }


# ---------------------------------------------------------------------------
# qualitative payload — closed schema
# ---------------------------------------------------------------------------
def load_qualitative(path, ticker, date):
    q = _read_json(path, "qualitative 檔")
    if not isinstance(q, dict):
        raise BuildError("qualitative 檔必須是 JSON object")
    if q.get("schema") != SCHEMA:
        raise BuildError(f"qualitative schema 必須是 {SCHEMA!r}，收到 {q.get('schema')!r}")

    leaked = sorted(set(q) & DERIVED_KEYS)
    if leaked:
        raise BuildError(
            f"qualitative 檔含 script 導得出來的欄位：{leaked}\n"
            f"         這些一律由本 script 從 artifact 取值，手填等於重新引入打字錯誤。"
            f"刪掉它們再跑。")
    unknown = sorted(set(q) - QUALITATIVE_ONLY)
    if unknown:
        raise BuildError(
            f"qualitative 檔含未知欄位：{unknown}\n"
            f"         schema 是封閉的。要新增欄位得先改 QUALITATIVE_ONLY 並說明為什麼"
            f"script 導不出來。")

    if str(q.get("ticker", "")).upper() != ticker.upper():
        raise BuildError(f"qualitative.ticker={q.get('ticker')!r} 與 --ticker {ticker} 不符")
    if str(q.get("date", "")) != date:
        raise BuildError(f"qualitative.date={q.get('date')!r} 與 --date {date} 不符")

    lanes = q.get("lanes")
    if not isinstance(lanes, dict) or set(lanes) != set(LANES):
        raise BuildError(f"lanes 必須剛好five個: {sorted(LANES)}；收到 {sorted(lanes or [])}")
    for name, lane in lanes.items():
        if not isinstance(lane, dict):
            raise BuildError(f"lanes.{name} 必須是 object")
        bad = sorted(set(lane) & LANE_REJECTED)
        if bad:
            raise BuildError(
                f"lanes.{name} 含 {bad} —— 這兩個由 phase-3 engine 輸入決定，"
                f"不是質性判斷。手填會與 calculation_steps 分岔（renderer 的一致性閘會擋）。")
        miss = sorted(LANE_REQUIRED - set(lane))
        if miss:
            raise BuildError(f"lanes.{name} 缺 {miss}")
        for f in ("key_factors", "risk_flags"):
            if not isinstance(lane[f], list):
                raise BuildError(f"lanes.{name}.{f} 必須是 list")

    wc = q.get("watch_conditions")
    if not isinstance(wc, dict) or len(wc) < 3:
        raise BuildError(
            f"watch_conditions 必須是 object 且至少 3 條（key: snake_case 識別名 → "
            f"value: 繁中描述）；收到 {type(wc).__name__} len="
            f"{len(wc) if hasattr(wc, '__len__') else '?'}")
    if q.get("trade_metadata") is None:
        raise BuildError("trade_metadata 必填且不得為 null（所有 decision 都要，含 HOLD/CANCEL）")

    rt = q.get("red_team")
    if not isinstance(rt, dict):
        raise BuildError("red_team 必填（object）")
    miss = sorted(RED_TEAM_REQUIRED - set(rt))
    if miss:
        raise BuildError(f"red_team 缺 {miss}")
    if not isinstance(rt["kill_conditions"], list) or not rt["kill_conditions"]:
        raise BuildError("red_team.kill_conditions 必須是非空 list")
    return q


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------
def _lane_block(qual, art, name):
    """Merge the model's qualitative half with the engine input's numeric half.

    score/confidence are read from the phase-3 input — the record of what the decision
    math actually consumed — so the bundle can never argue for a different number than
    `calculation_steps` reports.
    """
    lane = dict(qual["lanes"][name])
    p3 = art["p3"]
    block = {
        "signal": lane.get("signal"),
        "score": (p3.get("lane_scores") or {}).get(name),
        "confidence": (p3.get("lane_confidence") or {}).get(name),
        "key_factors": lane.get("key_factors") or [],
        "risk_flags": lane.get("risk_flags") or [],
    }
    detail = (qual.get("lane_detail") or {}).get(name)
    if isinstance(detail, dict):
        block.update(detail)
    return block


def _sig_of(lane):
    return lane.get("signal")


def build_bundle(qual, art, ticker, date):
    p0 = art["phase0"]
    ms = p0.get("macro_summary") or {}
    sig = p0.get("_market_signals") or {}
    fred = p0.get("fred_snapshot") or {}
    eng = art["engine"]
    plan = art["plan"]
    tp = plan.get("trade_plan") or {}

    return {
        "bundle_version": BUNDLE_VERSION,
        "ticker": ticker,
        "date": date,
        "phase0": {
            "regime_confidence": ms.get("regime_confidence"),
            "market_top_zone": sig.get("market_top_zone"),
            "ftd_state": sig.get("ftd_status"),
            "breadth_composite": sig.get("breadth_composite"),
            "vix": sig.get("vix_current"),
            "fred_verdict": fred.get("regime_label"),
            "real_rate_pct": fred.get("real_rate_10y_estimate"),
            "hot_sectors": ms.get("hot_sectors") or [],
            "cold_sectors": ms.get("cold_sectors") or [],
        },
        "lanes": {n: _lane_block(qual, art, n) for n in LANES},
        "burry": {
            "score": _burry_score(art),
            "narrative": qual.get("burry_narrative"),
        },
        "phase3": {
            "final_score": eng.get("final_score"),
            "final_decision": eng.get("final_decision"),
            "final_action": _final_action(eng, plan),
        },
        "phase4": {
            "position_size_pct": _position_size(plan),
            # Same source as the entry's analysis_price. Deriving the two from
            # different places is exactly the drift check_consistency() rejects —
            # it caught this during V4.126.0 bring-up (596.55 vs 592.10).
            "analysis_price": ((art["quant"].get("quant_blocks") or {})
                               .get("valuation_pack") or {}).get("current_price"),
        },
        "red_team": {"verdict": qual["red_team"].get("verdict")},
    }


def _burry_score(art):
    """From the phase-3 engine input, not a re-run of burry_score.py.

    Same rule as the lane numbers: the input is the record of what the decision math
    actually consumed. Re-running the skill could return a different score (prices
    move) and would silently disagree with `calculation_steps`.
    """
    return ((art["p3"].get("burry") or {}).get("score"))


def _position_size(plan):
    tp = plan.get("trade_plan") or {}
    for k in ("position_size_pct", "final_position_size_pct"):
        if k in tp:
            return tp[k]
        if k in plan:
            return plan[k]
    return None


def _final_action(eng, plan):
    """CANCEL when the plan has no size; otherwise mirror the engine decision."""
    size = _position_size(plan)
    if size in (0, 0.0):
        return "CANCEL"
    return "EXECUTE" if eng.get("final_decision") in ("BUY", "STAGED_ENTRY") else "CANCEL"


def build_entry(qual, art, ticker, date):
    eng = art["engine"]
    plan = art["plan"]
    tp = plan.get("trade_plan") or {}
    qb = art["quant"].get("quant_blocks") or {}
    p0 = art["phase0"]
    ms = p0.get("macro_summary") or {}
    cs = eng.get("calculation_steps") or {}
    lanes = qual["lanes"]
    rt = qual["red_team"]

    # Single-sourced from lanes → cannot drift apart.
    p3in = art["p3"]
    lane_scores = {n: (p3in.get("lane_scores") or {}).get(n) for n in LANES}
    lane_signals = {n: _sig_of(lanes[n]) for n in LANES}
    ra = plan.get("risk_audit") or {}
    vpack = qb.get("valuation_pack") or {}

    cb = dict(qual.get("conflict_bias") or {})
    cb.setdefault("schema", "conflict_bias.v1")
    cb["lane_signals"] = lane_signals
    if isinstance(cs.get("t5_forward_validation"), dict):
        cb["t5_detail"] = (cs["t5_forward_validation"]
                           if "T5" in (cb.get("triggers_fired") or []) else None)

    trade = {
        "ticker": ticker,
        "final_action": _final_action(eng, plan),
        "final_score": eng.get("final_score"),
        "final_decision": eng.get("final_decision"),
        "decision_engine_version": eng.get("decision_engine_version"),
        "calculation_steps": cs,
        "avg_confidence": eng.get("avg_confidence"),
        "consensus_bonus_applied": cs.get("bonus_applied"),
        "macro_alignment": cs.get("macro_alignment"),
        "hot_zone_probe": eng.get("hot_zone_probe"),
        "hot_zone_probe_tier": eng.get("hot_zone_probe_tier"),
        "hot_zone_eval": eng.get("hot_zone_eval"),
        "decision_cap_active": eng.get("decision_cap_active"),
        "decision_cap_reason": eng.get("decision_cap_reason"),
        "transition_data_stale_or_inconsistent":
            eng.get("transition_data_stale_or_inconsistent"),

        "red_team_verdict": rt.get("verdict"),
        "red_team_counter_thesis": rt.get("counter_thesis"),
        "red_team_kill_conditions": rt.get("kill_conditions"),
        "red_team_execution_failed": bool(rt.get("execution_failed", False)),
        "red_team_counter_evidence_strength": rt.get("counter_evidence_strength"),
        "red_team_thesis_break_probability": rt.get("thesis_break_probability"),

        "phase2_fanout_mode": qual.get("phase2_fanout_mode"),
        "degraded_analysts": qual.get("degraded_analysts") or [],
        "lane_scores": lane_scores,
        "conflict_bias": cb,

        "burry_score": _burry_score(art),
        "burry_override_active": False,
        "burry_override_recheck_date": None,

        "trade_plan_builder_version": plan.get("trade_plan_builder_version"),
        "mandatory_risk_flags": plan.get("mandatory_risk_flags"),
        "entry_aggressive": tp.get("entry_aggressive"),
        "entry_conservative": tp.get("entry_conservative"),
        "take_profit": tp.get("take_profit"),
        "stop_loss": tp.get("stop_loss"),
        "risk_reward_ratio": tp.get("risk_reward_ratio"),
        "position_size_pct": _position_size(plan),
        "risk_audit": ra,
        "time_horizon": tp.get("time_horizon"),
        # valuation_pack.current_price, not the plan's entry reference: the validator
        # cross-checks these two and the pack is the priced-at-analysis-time authority.
        "analysis_price": vpack.get("current_price"),
        "staged_split": ra.get("staged_entry_split"),
        "position_size_method": ra.get("position_size_method"),
        "final_stop_loss_pct": ra.get("final_stop_loss_pct"),
        "fragility_label": (ra.get("tail_risk") or {}).get("fragility_label"),
        "binary_classification": ra.get("binary_classification"),
        "ftd_timeline_gate": ra.get("ftd_timeline_gate"),

        "valuation_pack": qb.get("valuation_pack"),
        "fair_value_summary": qb.get("fair_value_summary"),
        "fair_value_range": qb.get("fair_value_range"),
        "implied_expectations": qb.get("implied_expectations"),
        "valuation_archetype_shadow": qb.get("valuation_archetype_shadow"),
        "forward_validation": qb.get("forward_validation"),
        "valuation_explained_range": qb.get("valuation_explained_range"),
        "valuation_reviewer_gate": {
            k: art["gate"].get(k)
            for k in ("schema", "ticker", "would_invoke", "mandatory_fired",
                      "triggers_fired", "shadow_only")},
        "valuation_lane": _lane_block(qual, art, "valuation"),

        "fundamentals_lane": _lane_block(qual, art, "fundamentals"),
        "sentiment_lane": _lane_block(qual, art, "sentiment"),
        "news_lane": _lane_block(qual, art, "news"),
        "technical_lane": _lane_block(qual, art, "technical"),

        "multi_horizon_price_framework": art["p4"].get("multi_horizon_price_framework"),

        "macro_context": qual.get("macro_context"),
        "watch_conditions": qual.get("watch_conditions") or [],
        "key_risks": qual.get("key_risks") or [],
        "devils_advocate_filed": bool(qual.get("devils_advocate_filed", False)),
        "decision_point_days": qual.get("decision_point_days"),
    }
    trade["trade_metadata"] = qual["trade_metadata"]

    return {
        "session_export_version": SESSION_EXPORT_VERSION,
        "export_date": date,
        "date": date,
        "ticker": ticker,
        "final_action": trade["final_action"],
        "phase0_file": "./" + os.path.relpath(art["phase0_path"],
                                              os.path.join(ROOT, "investment")),
        "phase0_macro_snapshot": {
            "market_regime": ms.get("market_regime"),
            "macro_backdrop_score": ms.get("macro_backdrop_score"),
            "macro_multiplier": p0.get("phase3_macro_multiplier"),
            "key_themes": ms.get("key_themes") or [],
        },
        "trades_this_session": [trade],
        "active_weights_end_of_session": _weights_from_steps(cs),
        "bias_notes": qual.get("bias_notes"),
        "last_outcome": qual.get("last_outcome", "UNKNOWN"),
    }


_STEP_W = re.compile(r"^\s*(-?[\d.]+)\s*×")


def _weights_from_steps(cs):
    """Recover the live weights from the engine's own step strings.

    Reading them back off `calculation_steps` rather than restating a constant means
    the exported weights are the ones the score was actually computed with; a weight
    table edited in one place and not the other cannot produce a silently wrong export.
    """
    out = {}
    for key, label in (("fund", "Fundamentals"), ("sent", "Sentiment"),
                       ("news", "News"), ("tech", "Technical"), ("val", "Valuation")):
        m = _STEP_W.match(str(cs.get(key) or ""))
        if m:
            out[label] = float(m.group(1))
    return out


# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Phase 5 Step 1 assembler — isolated export entry + phase_inputs bundle")
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--qualitative", required=True, help="PM 寫的質性檔")
    ap.add_argument("--p3-input", required=True, help="decision_engine 的輸入 JSON（lane 數字的權威來源）")
    ap.add_argument("--p4-input", required=True, help="trade_plan_builder 的輸入 JSON")
    ap.add_argument("--quant", help="覆寫 pf_quant 路徑")
    ap.add_argument("--phase0", help="覆寫 phase0 路徑")
    ap.add_argument("--bundle-out", help="覆寫 bundle 輸出路徑")
    ap.add_argument("--session-out",
                    help="原子寫入獨立 session object（代替 stdout）")
    ap.add_argument("--no-bundle", action="store_true",
                    help="只印 export entry，不寫 bundle（測試用）")
    args = ap.parse_args(argv)

    ticker = args.ticker.upper()
    if not re.fullmatch(r"[A-Z0-9.\-]{1,12}", ticker):
        raise BuildError(f"ticker 形狀不合法: {ticker!r}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        raise BuildError(f"--date 必須是 YYYY-MM-DD，收到 {args.date!r}")

    art = load_artifacts(ticker, args.date, p3_input=args.p3_input, p4_input=args.p4_input,
                         quant_path=args.quant, phase0_path=args.phase0)
    qual = load_qualitative(args.qualitative, ticker, args.date)

    entry = build_entry(qual, art, ticker, args.date)
    bundle = build_bundle(qual, art, ticker, args.date)

    if not args.no_bundle:
        out = args.bundle_out or os.path.join(
            ROOT, f"investment/invest_logs/phase_inputs/{args.date}_{ticker}.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fp:
            json.dump(bundle, fp, ensure_ascii=False, indent=1)
        print(f"[build_session_export] bundle → {os.path.relpath(out, ROOT)}",
              file=sys.stderr)

    if args.session_out:
        out = os.path.abspath(args.session_out)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False,
            dir=os.path.dirname(out), prefix=f".{os.path.basename(out)}.", suffix=".tmp",
        )
        try:
            json.dump(entry, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, out)
        except Exception:
            try:
                tmp.close()
            except Exception:
                pass
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            raise
        print(f"[build_session_export] session → {os.path.relpath(out, ROOT)}",
              file=sys.stderr)

    if not args.session_out:
        json.dump(entry, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

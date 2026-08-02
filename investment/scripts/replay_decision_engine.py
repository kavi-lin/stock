#!/usr/bin/env python3
"""replay_decision_engine.py — V4.80.0 history replay + mismatch triage for decision_engine.

Re-runs `decision_engine.run_phase3()` over every `history.json` trade and compares the
replayed `final_score` / `final_decision` against what was stored, so a regression in the
engine shows up as a diff against the production record rather than against itself.

Three disciplines this harness holds to:

1. **No silent caps.** Every trade that cannot be replayed appears in the exclusion table
   with a machine-readable reason. Coverage numbers always reconcile: eligible + excluded
   = total.

2. **No silent assumptions.** History does not persist every Phase 3 input (structural
   shift tier, counter-evidence strength, rule-2 transition metadata, binary-event
   timing). Instead of guessing, the harness enumerates the unknown discrete inputs and
   replays every combination. If `final_score` and `final_decision` are invariant across
   the whole sweep, the unknown provably does not matter and the trade stays eligible.
   If they are not, the trade is excluded as `decision_sensitive_unknown` naming the
   fields responsible.

3. **Rule era is not engine error.** V4.70.0 (2026-07-16) rewrote the Phase 3 math —
   three-tier C_eff, graded cascade rules 4/5, tiered hot-zone probe. Entries decided
   before that ran under different rules, so a diff there measures rule drift, not an
   engine defect. Those trades are replayed and reported separately, auto-classified
   `rule_version_drift`, and never counted as parity failures.

Mismatches in the current-rule cohort come out as `NEEDS_TRIAGE` with a full input dump,
for manual classification into `engine_bug` / `historical_llm_arithmetic_error` /
`unrecorded_gate_input`.

Usage:
  python3 investment/scripts/replay_decision_engine.py
  python3 investment/scripts/replay_decision_engine.py --json /tmp/replay.json --tol 0.005
  python3 investment/scripts/replay_decision_engine.py --out reports/decision_review/X.md

rc=0 always for the pre-4.70 cohort (drift is expected); rc=1 when a current-rule trade
mismatches, so this can be wired into CI once enough post-V4.70.0 entries accumulate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from itertools import product

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decision_engine import apply_decision_cap, run_phase3  # noqa: E402
# Schema versions live in the validator — importing keeps replay coverage from silently
# shrinking to zero the next time the export schema is bumped.
from validate_session_export import V5_VERSIONS as FIVE_LANE_VERSIONS  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HISTORY_JSON = os.path.join(ROOT, "investment/invest_logs/history.json")
EVENT_INDEX = os.path.join(ROOT, "reports/decision_review/event_index_latest.json")
REPORTS_DIR = os.path.join(ROOT, "reports")
OUT_DIR = os.path.join(ROOT, "reports/decision_review")

# V4.70.0 — P0 決策品質修正 (CHANGELOG 4.70.0, 2026-07-16). Trades decided on or after
# this date ran under the rules this engine implements.
CURRENT_RULES_SINCE = "2026-07-16"

LANES = ("fundamentals", "sentiment", "news", "technical", "valuation")
REPORT_LANE_NAMES = {"Fundamentals": "fundamentals", "Sentiment": "sentiment",
                     "News": "news", "Technical": "technical", "Valuation": "valuation"}
EVENT_LANE_NAMES = {"Fundamentals": "fundamentals", "Sentiment": "sentiment",
                    "News": "news", "Technical": "technical", "Valuation": "valuation",
                    "Valuation Specialist": "valuation"}

_HEAD_RE = re.compile(
    r"^###\s*(Fundamentals|Sentiment|News|Technical|Valuation)(?:\s+Specialist)?\s*[（(](?P<tail>.+)$",
    re.MULTILINE)
_SCORE_RE = re.compile(r"Score[:：]?\s*([+\-−–]?\d+(?:\.\d+)?)", re.IGNORECASE)
_CONF_RE = re.compile(r"Conf(?:idence)?[:：]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
_STEP_RE = re.compile(r"^\s*([\d.]+)\s*×\s*([+\-−–]?[\d.]+)\s*×\s*([\d.]+)")
STEP_KEYS = {"fund": "fundamentals", "sent": "sentiment", "news": "news",
             "tech": "technical", "val": "valuation"}


def _f(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return float(x)


def _num(s: str) -> float:
    return float(s.replace("−", "-").replace("–", "-"))


# ---------------------------------------------------------------------------
# lane input sourcing — three sources, most authoritative first
# ---------------------------------------------------------------------------

def lanes_from_calculation_steps(trade: dict):
    """The stored Step 1 strings record the exact score and C_eff that were weighted."""
    cs = trade.get("calculation_steps")
    if not isinstance(cs, dict):
        return None
    scores, ceffs = {}, {}
    for key, lane in STEP_KEYS.items():
        m = _STEP_RE.match(str(cs.get(key) or ""))
        if not m:
            return None
        scores[lane] = _num(m.group(2))
        ceffs[lane] = float(m.group(3))
    # invert the three-tier quantisation to a representative raw confidence
    conf = {lane: {0.35: 0.40, 0.60: 0.55, 0.72: 0.75}.get(ce) for lane, ce in ceffs.items()}
    if any(c is None for c in conf.values()):
        return None
    return {"scores": scores, "confidence": conf, "source": "calculation_steps"}


def lanes_from_event_index(decision: dict | None):
    if not decision:
        return None
    scores, conf = {}, {}
    for a in decision.get("agent_breakdown") or []:
        lane = EVENT_LANE_NAMES.get(a.get("agent"))
        if lane is None:
            continue
        s, c = _f(a.get("score")), _f(a.get("confidence"))
        if s is None or c is None:
            continue
        scores[lane], conf[lane] = s, c
    if len(scores) < len(LANES):
        return None
    return {"scores": scores, "confidence": conf, "source": "event_index"}


def lanes_from_report(date: str, ticker: str, reports_dir: str):
    path = os.path.join(reports_dir, f"{date.replace('-', '')}_{ticker}.md")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fp:
        text = fp.read()
    scores, conf = {}, {}
    for m in _HEAD_RE.finditer(text):
        lane = REPORT_LANE_NAMES[m.group(1)]
        tail = m.group("tail")
        sm, cm = _SCORE_RE.search(tail), _CONF_RE.search(tail)
        if not sm or not cm:
            continue
        scores[lane], conf[lane] = _num(sm.group(1)), float(cm.group(1))
    if len(scores) < len(LANES):
        return None
    return {"scores": scores, "confidence": conf, "source": f"report:{os.path.basename(path)}"}


def source_lanes(trade, decision, date, ticker, reports_dir):
    for fn in (lambda: lanes_from_calculation_steps(trade),
               lambda: lanes_from_event_index(decision),
               lambda: lanes_from_report(date, ticker, reports_dir)):
        got = fn()
        if got:
            return got
    return None


# ---------------------------------------------------------------------------
# input assembly + unknown enumeration
# ---------------------------------------------------------------------------

def build_base_input(entry, trade, decision, lanes):
    snap = entry.get("phase0_macro_snapshot") or {}
    cs = trade.get("calculation_steps") if isinstance(trade.get("calculation_steps"), dict) else {}
    hooks = (decision or {}).get("tuning_hooks") or {}
    heat = hooks.get("sub_industry_heat") or {}
    fvs = trade.get("fair_value_summary") or {}

    cap_block = None
    if trade.get("decision_cap_active") is not None:
        cap_block = {"_explicit": True}
    elif fvs:
        cap_block = {"anchors_available": fvs.get("anchors_available"),
                     "fair_value_confidence": fvs.get("confidence"),
                     "lane_data_quality_low": bool(trade.get("degraded_analysts"))}

    return {
        "ticker": trade.get("ticker"),
        "lane_scores": dict(lanes["scores"]),
        "lane_confidence": dict(lanes["confidence"]),
        "structural_shift": {"tier": (cs.get("structural_shift_modulation") or {}).get("tier")},
        "red_team": {
            "verdict": trade.get("red_team_verdict"),
            "basis": (trade.get("det_shadow") or {}).get("red_team_basis"),
            "counter_evidence_strength": trade.get("red_team_counter_evidence_strength"),
            "thesis_break_probability": trade.get("red_team_thesis_break_probability"),
        },
        "transition": {},
        "macro": {
            "macro_multiplier": snap.get("macro_multiplier"),
            "macro_backdrop_score": snap.get("macro_backdrop_score"),
            "market_regime": snap.get("market_regime"),
        },
        "burry": {"score": trade.get("burry_score"), "veto_flag": False},
        "gates": {
            "proceed_to_phase3": True,   # inferred: the session reached Phase 3 and decided
            "risk_reward_ratio": trade.get("risk_reward_ratio"),
            "binary_classification": trade.get("binary_classification"),
            "mandatory_risk_flags": [],  # never persisted — declared assumption, see report
            "phase2_fanout_mode": trade.get("phase2_fanout_mode"),
        },
        "hot_zone": {"industry_top_30pct": heat.get("industry_top_30pct")},
        "decision_cap": (
            {"_explicit": True} if cap_block and cap_block.get("_explicit") else cap_block),
    }, {"decision_cap_active": trade.get("decision_cap_active"),
        "decision_cap_reason": trade.get("decision_cap_reason")}


def enumerate_unknowns(base, cap_explicit):
    """Return (dimension_names, list_of_override_dicts). Only dimensions that can
    plausibly change the outcome are enumerated, keeping the sweep bounded.

    The FIRST choice of every dimension is its spec default, so `variants[0]` is always
    the default-assumption replay used for the advisory line on sensitive trades."""
    dims, choices = [], []

    if base["structural_shift"]["tier"] is None:
        dims.append("structural_shift.tier")
        choices.append(["NONE", "CANDIDATE", "CONFIRMED"])

    rt = base["red_team"]
    strong = rt.get("verdict") == "STRONG_COUNTER"
    if strong and rt.get("basis") == "pure_forward" and rt.get("counter_evidence_strength") is None:
        dims.append("red_team.counter_evidence_strength")
        choices.append([4, 5])
    if strong and rt.get("basis") == "pure_mean_reversion":
        dims.append("transition.rule2_eligible")
        choices.append([False, True])
    if base["gates"].get("binary_classification") in ("unknown", "negative"):
        dims.append("gates.binary_event_within_48h")
        choices.append([False, True])

    variants = []
    for combo in product(*choices) if choices else [()]:
        v = json.loads(json.dumps(base))
        # The entry recorded the cap outcome directly — reproduce that state rather than
        # re-deriving it from anchors that may since have been re-computed.
        if cap_explicit["decision_cap_active"] is True:
            v["decision_cap"] = {"anchors_available": 0}
        elif cap_explicit["decision_cap_active"] is False:
            v["decision_cap"] = {"anchors_available": 5, "fair_value_confidence": "medium",
                                 "lane_data_quality_low": False}
        for name, val in zip(dims, combo):
            if name == "structural_shift.tier":
                v["structural_shift"]["tier"] = val
            elif name == "red_team.counter_evidence_strength":
                v["red_team"]["counter_evidence_strength"] = val
            elif name == "transition.rule2_eligible":
                v["transition"] = ({"transition_signature": "mix_only",
                                    "forecaster_transition_case": True,
                                    "valuation_cited_transition_overlay": True,
                                    "valuation_transition_dissent_basis": "peer_multiple"}
                                   if val else {})
            elif name == "gates.binary_event_within_48h":
                v["gates"]["binary_event_within_48h"] = val
        variants.append((dict(zip(dims, combo)), v))
    return dims, variants


# ---------------------------------------------------------------------------
# replay
# ---------------------------------------------------------------------------

def replay_trade(entry, trade, decision, reports_dir, tol):
    date = entry.get("date") or entry.get("export_date")
    ticker = trade.get("ticker")
    ver = entry.get("session_export_version")
    era = "current" if (date or "") >= CURRENT_RULES_SINCE else "pre_v4_70"
    row = {"date": date, "ticker": ticker, "version": ver, "rule_era": era}

    if ver not in FIVE_LANE_VERSIONS:
        row.update(status="excluded", reason="pre_v5_four_lane_schema",
                   detail=f"session_export_version={ver!r} predates the 5-lane weighting "
                          f"(replayable: {', '.join(FIVE_LANE_VERSIONS)})")
        return row

    lanes = source_lanes(trade, decision, date, ticker, reports_dir)
    if not lanes:
        row.update(status="excluded", reason="lane_inputs_unavailable",
                   detail="no source carries all 5 lane scores + confidences "
                          "(calculation_steps / event_index / MD report)")
        return row
    row["lane_source"] = lanes["source"]

    snap = entry.get("phase0_macro_snapshot") or {}
    if snap.get("macro_multiplier") is None or snap.get("macro_backdrop_score") is None:
        row.update(status="excluded", reason="macro_inputs_unavailable",
                   detail="phase0_macro_snapshot missing macro_multiplier/backdrop_score")
        return row

    stored_score = _f(trade.get("final_score"))
    stored_decision = trade.get("final_decision")
    if stored_score is None or not stored_decision:
        row.update(status="excluded", reason="stored_outcome_missing",
                   detail="final_score or final_decision absent from the entry")
        return row

    base, cap_explicit = build_base_input(entry, trade, decision, lanes)
    dims, variants = enumerate_unknowns(base, cap_explicit)
    row["unknown_dimensions"] = dims

    results = []
    for combo, payload in variants:
        out = run_phase3(payload)
        # The stored `final_decision` is the POST-Phase-4.6 value, so a Phase 3 output must
        # go through the cap before it is comparable. Without this, any capped entry would
        # surface as a phantom NEEDS_TRIAGE. (0 rows affected in today's cohort.)
        decision = out["final_decision"]
        if out["decision_cap_active"]:
            decision = apply_decision_cap({
                "decision_cap_active": True,
                "decision_cap_reason": out["decision_cap_reason"],
                "final_decision": decision,
                "avg_confidence": out["avg_confidence"],
                "position_size_pct": _f(trade.get("position_size_pct")),
                "final_action": trade.get("final_action"),
                "cap_override_reason": trade.get("cap_override_reason"),
            })["final_decision"]
        results.append((combo, out["final_score"], decision))

    scores = {r[1] for r in results}
    decisions = {r[2] for r in results}
    if len(scores) > 1 or len(decisions) > 1:
        # Not parity-eligible — but the spec-default variant is still worth reporting as
        # an explicitly-labelled advisory so 38 exclusions are not 38 dead ends.
        adv_score, adv_decision = results[0][1], results[0][2]
        row.update(status="excluded", reason="decision_sensitive_unknown",
                   sensitive_dimensions=dims,
                   detail=f"unknown inputs {dims} change the outcome "
                          f"(scores={sorted(scores)}, decisions={sorted(decisions)})",
                   advisory_default_score=adv_score,
                   advisory_default_decision=adv_decision,
                   advisory_default_combo=results[0][0],
                   advisory_score_delta=round(adv_score - stored_score, 4),
                   advisory_match=(abs(adv_score - stored_score) <= tol
                                   and adv_decision == stored_decision),
                   stored_score=stored_score, stored_decision=stored_decision)
        return row

    replay_score, replay_decision = results[0][1], results[0][2]
    score_match = abs(replay_score - stored_score) <= tol
    decision_match = replay_decision == stored_decision
    row.update(status="replayed",
               stored_score=stored_score, replay_score=replay_score,
               stored_decision=stored_decision, replay_decision=replay_decision,
               score_delta=round(replay_score - stored_score, 4),
               score_match=score_match, decision_match=decision_match,
               match=bool(score_match and decision_match))
    if not row["match"]:
        row["triage"] = "rule_version_drift" if era == "pre_v4_70" else "NEEDS_TRIAGE"
        row["diff_inputs"] = {
            "lane_scores": base["lane_scores"], "lane_confidence": base["lane_confidence"],
            "red_team": base["red_team"], "macro": base["macro"],
            "structural_shift": base["structural_shift"],
            "gates": base["gates"], "unknowns_swept": dims,
        }
    else:
        row["triage"] = None
    return row


def build_report(rows, tol, as_of):
    total = len(rows)
    replayed = [r for r in rows if r["status"] == "replayed"]
    excluded = [r for r in rows if r["status"] == "excluded"]
    cur = [r for r in replayed if r["rule_era"] == "current"]
    old = [r for r in replayed if r["rule_era"] == "pre_v4_70"]
    cur_ok = [r for r in cur if r["match"]]
    cur_bad = [r for r in cur if not r["match"]]
    old_ok = [r for r in old if r["match"]]
    old_bad = [r for r in old if not r["match"]]

    reasons = {}
    for r in excluded:
        reasons.setdefault(r["reason"], []).append(r)

    L = []
    A = L.append
    A(f"# Decision Engine Replay — {as_of}")
    A("")
    A(f"> Engine: `investment/scripts/decision_engine.py` · harness: "
      f"`investment/scripts/replay_decision_engine.py` · score tolerance ±{tol}")
    A(f"> Current-rule cutoff: decisions on/after **{CURRENT_RULES_SINCE}** (V4.70.0) "
      f"run the math this engine implements; earlier entries are rule-drift measurement only.")
    A("")
    A("## 1. Coverage（eligible + excluded = total，無隱藏截斷）")
    A("")
    A("| 分類 | 筆數 |")
    A("|---|---|")
    A(f"| history trades 總數 | {total} |")
    A(f"| replayed（current rules） | {len(cur)} |")
    A(f"| replayed（pre-V4.70.0 rules，drift 量測） | {len(old)} |")
    A(f"| excluded | {len(excluded)} |")
    A(f"| **合計** | **{len(cur) + len(old) + len(excluded)}** |")
    A("")
    A("## 2. Parity verdict（current rules）")
    A("")
    if not cur:
        A("**無可判定樣本。** 沒有任何 history trade 同時滿足「決策日 ≥ "
          f"{CURRENT_RULES_SINCE}」與「5 lane score + confidence 可取得」。")
        A("")
        A("這不是 harness 失敗，是史料限制：V4.70.0 之後累積的 deep-dive 筆數尚少，且 "
          "per-lane confidence 從未寫進 `history.json`（只能從 `calculation_steps`、"
          "event_index `agent_breakdown` 或 MD 報告表頭回收）。engine 的 spec parity "
          "由 `test_decision_engine.py` 的 fixture 與 MU 2026-08-02 golden replay 擔保；"
          "本 harness 隨新 session 累積自動變成真實 parity gate。")
    else:
        A(f"- match: **{len(cur_ok)}/{len(cur)}**")
        A(f"- mismatch: **{len(cur_bad)}** → 需逐筆 triage")
    A("")
    if cur:
        A("| date | ticker | lane source | stored score | replay score | Δ | stored decision | replay decision | verdict |")
        A("|---|---|---|---|---|---|---|---|---|")
        for r in sorted(cur, key=lambda x: (x["date"], x["ticker"])):
            A(f"| {r['date']} | {r['ticker']} | `{r.get('lane_source')}` | "
              f"{r['stored_score']:+.4f} | "
              f"{r['replay_score']:+.4f} | {r['score_delta']:+.4f} | {r['stored_decision']} | "
              f"{r['replay_decision']} | {'✓ match' if r['match'] else '✗ ' + r['triage']} |")
        A("")

    cur_sens = [r for r in excluded
                if r["reason"] == "decision_sensitive_unknown" and r["rule_era"] == "current"]
    if cur_sens:
        A("**當期規則但因未記錄輸入而排除的筆數（advisory 對照，非 parity 證據）**")
        A("")
        A(f"這 {len(cur_sens)} 筆決策日 ≥ {CURRENT_RULES_SINCE}、lane 輸入齊全，只因 "
          "`structural_shift.tier` 等欄位未持久化、且 sweep 顯示會改變結果而排除。"
          "取 spec 預設值重算的結果列於下——一致代表 engine 與當時 PM 手算同號，"
          "但因假設成立與否無法證實，不計入 §2 的 parity 分母。")
        A("")
        A("| date | ticker | lane source | stored → advisory score | Δ | decision | 一致 |")
        A("|---|---|---|---|---|---|---|")
        for r in sorted(cur_sens, key=lambda x: (x["date"], x["ticker"])):
            A(f"| {r['date']} | {r['ticker']} | `{r.get('lane_source')}` | "
              f"{r['stored_score']:+.4f} → {r['advisory_default_score']:+.4f} | "
              f"{r['advisory_score_delta']:+.4f} | {r['stored_decision']} → "
              f"{r['advisory_default_decision']} | "
              f"{'✓' if r['advisory_match'] else '✗'} |")
        A("")

    A("## 3. Rule-version drift（pre-V4.70.0 cohort — 不計入 parity）")
    A("")
    if old:
        A(f"- 同號: {len(old_ok)}/{len(old)}；差異: {len(old_bad)}")
        A("- 全部自動歸類 `rule_version_drift`：這些 entry 當時走連續 confidence 乘項與"
          "未分級的 cascade 懲罰，用今天的規則重算本來就會不同。差異幅度即 V4.70.0 的實際衝擊。")
        A("")
        deltas = sorted(abs(r["score_delta"]) for r in old)
        if deltas:
            mid = deltas[len(deltas) // 2]
            A(f"- |Δfinal_score| 中位數 {mid:.4f}、最大 {deltas[-1]:.4f}；"
              f"decision 改變 {sum(1 for r in old if not r['decision_match'])} 筆")
        A("")
        A("| date | ticker | stored → replay score | Δ | stored → replay decision |")
        A("|---|---|---|---|---|")
        for r in sorted(old, key=lambda x: (x["date"], x["ticker"])):
            A(f"| {r['date']} | {r['ticker']} | {r['stored_score']:+.4f} → "
              f"{r['replay_score']:+.4f} | {r['score_delta']:+.4f} | "
              f"{r['stored_decision']} → {r['replay_decision']} |")
    else:
        A("（無）")
    A("")

    A("## 4. Exclusions（逐筆列出，無 silent cap）")
    A("")
    for reason, group in sorted(reasons.items(), key=lambda kv: -len(kv[1])):
        A(f"### `{reason}` — {len(group)} 筆")
        A("")
        if reason == "decision_sensitive_unknown":
            dim_freq = {}
            for r in group:
                for d in r.get("sensitive_dimensions") or []:
                    dim_freq[d] = dim_freq.get(d, 0) + 1
            A("> 未持久化的 Phase 3 輸入在這些 entry 上**真的會改變結果**，故不列入 parity。"
              "下表另附「spec 預設值」replay 作為 advisory（明確標示為假設，不是 parity 證據）。")
            A("")
            A("| 被掃描的未知欄位 | 出現於幾筆 |")
            A("|---|---|")
            for d, n in sorted(dim_freq.items(), key=lambda kv: -kv[1]):
                A(f"| `{d}` | {n} |")
            A("")
            adv_ok = sum(1 for r in group if r.get("advisory_match"))
            A(f"- advisory（全部未知取 spec 預設：tier=NONE / strength=4 / rule2=off / "
              f"binary_event=off）與存檔一致：**{adv_ok}/{len(group)}**")
            A("")
            A("| date | ticker | stored → advisory score | Δ | stored → advisory decision | 一致 |")
            A("|---|---|---|---|---|---|")
            for r in sorted(group, key=lambda x: (x["date"] or "", x["ticker"] or "")):
                A(f"| {r['date']} | {r['ticker']} | {r['stored_score']:+.4f} → "
                  f"{r['advisory_default_score']:+.4f} | {r['advisory_score_delta']:+.4f} | "
                  f"{r['stored_decision']} → {r['advisory_default_decision']} | "
                  f"{'✓' if r['advisory_match'] else '✗'} |")
            A("")
            continue
        A(f"> {group[0].get('detail', '')}")
        A("")
        if reason == "pre_v5_four_lane_schema":
            # 94 identical rows would be noise — same information, compact rendering,
            # still one token per excluded trade.
            by_ver = {}
            for r in group:
                by_ver.setdefault(r["version"], []).append(f"{r['date']}/{r['ticker']}")
            for ver_k, items in sorted(by_ver.items()):
                A(f"- **{ver_k}**（{len(items)} 筆）：{', '.join(sorted(items))}")
            A("")
            continue
        A("| date | ticker | version | detail |")
        A("|---|---|---|---|")
        for r in sorted(group, key=lambda x: (x["date"] or "", x["ticker"] or "")):
            A(f"| {r['date']} | {r['ticker']} | {r['version']} | {r.get('detail', '')} |")
        A("")

    A("## 5. Declared assumptions（會影響判讀，明寫不藏）")
    A("")
    A("1. `proceed_to_phase3=true` — 由「session 走到 Phase 3 並產出決策」反推，非猜測。")
    A("2. `mandatory_risk_flags=[]` — 此欄從未寫進 history。若某筆 replay 給 BUY-side 而"
      "存檔是 HOLD，`unrecorded_gate_input` 是合法 triage 結論。")
    A("3. `industry_top_30pct` 取自 event_index `sub_industry_heat`，那是**產生索引當下**"
      "的熱度、非決策當下；只影響 Rec 11 hot-zone 判定。")
    A("4. `calculation_steps` 來源的 lane confidence 由 C_eff 反推代表值"
      "（0.35→0.40 / 0.60→0.55 / 0.72→0.75）——decision 數學只吃 C_eff，故無損；"
      "但 `avg_confidence` 不在本 harness 的比對範圍內。")
    A("5. Phase 4.6 decision cap：entry 有存 `decision_cap_active` 時直接沿用該結果，"
      "否則由 `fair_value_summary` 的 anchors/confidence 與 `degraded_analysts` 重推。")
    A("6. `lane_source=calculation_steps` 的筆數獨立性較弱——輸入取自同一 entry 的 Step 1 "
      "字串、輸出比對 `final_score`/`final_decision` 兩個獨立欄位，能抓「鏈中段算錯」"
      "但抓不到「輸入本身抄錯」。`event_index` / `report` 來源沒有這個限制。")
    A("")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Replay decision_engine over history.json")
    ap.add_argument("--history", default=HISTORY_JSON)
    ap.add_argument("--event-index", default=EVENT_INDEX)
    ap.add_argument("--reports-dir", default=REPORTS_DIR)
    ap.add_argument("--out", default=None, help="MD report path (default: reports/decision_review/)")
    ap.add_argument("--json", dest="json_out", default=None, help="also dump raw rows as JSON")
    ap.add_argument("--tol", type=float, default=0.005,
                    help="final_score tolerance (default 0.005 — absorbs 3dp stored rounding)")
    args = ap.parse_args(argv)

    with open(args.history, encoding="utf-8") as fp:
        hist = json.load(fp)
    decisions = {}
    if os.path.exists(args.event_index):
        with open(args.event_index, encoding="utf-8") as fp:
            ei = json.load(fp)
        for d in ei.get("decisions") or []:
            if d.get("source") == "deep-dive" and d.get("tickers"):
                decisions[(d.get("decision_date"), d["tickers"][0])] = d

    rows = []
    for entry in hist:
        for trade in entry.get("trades_this_session") or []:
            key = (entry.get("date"), trade.get("ticker"))
            rows.append(replay_trade(entry, trade, decisions.get(key),
                                     args.reports_dir, args.tol))

    as_of = dt.date.today().isoformat()
    out_path = args.out or os.path.join(OUT_DIR, f"DECISION_ENGINE_REPLAY_{as_of}.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write(build_report(rows, args.tol, as_of))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fp:
            json.dump(rows, fp, ensure_ascii=False, indent=2)

    cur_bad = [r for r in rows if r["status"] == "replayed"
               and r["rule_era"] == "current" and not r["match"]]
    cur_n = sum(1 for r in rows if r["status"] == "replayed" and r["rule_era"] == "current")
    old_n = sum(1 for r in rows if r["status"] == "replayed" and r["rule_era"] == "pre_v4_70")
    exc_n = sum(1 for r in rows if r["status"] == "excluded")
    print(f"[replay] trades={len(rows)} current={cur_n} pre_4.70={old_n} excluded={exc_n}")
    print(f"[replay] report → {os.path.relpath(out_path, ROOT)}")
    if cur_bad:
        print(f"[replay] ✗ {len(cur_bad)} current-rule mismatch(es) need triage:", file=sys.stderr)
        for r in cur_bad:
            print(f"  - {r['date']} {r['ticker']}: stored {r['stored_score']} / "
                  f"{r['stored_decision']} vs replay {r['replay_score']} / "
                  f"{r['replay_decision']}", file=sys.stderr)
        return 1
    print("[replay] ✓ no current-rule mismatch")
    return 0


if __name__ == "__main__":
    sys.exit(main())

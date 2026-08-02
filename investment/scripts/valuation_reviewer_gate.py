#!/usr/bin/env python3
"""valuation_reviewer_gate.py — V4.89.0 條件式 Valuation Specialist 觸發判定（shadow-only）。

判斷「這個 session 該不該跑 Valuation Specialist LLM lane」。**本版一律 shadow**：
`would_invoke` 只被記錄，PM 照跑 lane、決策數字一個都不動。累積 shadow 樣本後由使用者
拍板是否翻預設（skip 生效）——那是下一版的事，不在本檔範圍。

零新計算：所有 quant 訊號直接讀 Phase 1.5 quant artifact（V4.88.0
`compute_price_framework.py --stage quant` 的輸出），gate 不重算任何估值數字。

Triggers（任一命中 → would_invoke=true）:
  1. transition_case_active   ← **mandatory**，不可被 shadow 統計說服關掉。
     decision_engine.compute_transition_gate() 吃兩個純 LLM 欄位
     （cited_transition_overlay / transition_dissent_basis）；lane 不跑 → cited 缺
     → valuation_confirmed_transition=False → Phase 3 cascade rule #2 的 ×0.95 軟化
     不觸發，落回 ×0.85。方向雖保守，但那是**改了決策數字**，違反本功能的前提。
  2. no_peer_cohort           ← 無 curated 也無未過期 discovered cohort
  3. structural_shift_typed   ← typed shift input 齊備（估值敘事需要人看）
  4. anchor_conflict_severe   ← cv / agreement_grade / dispersion 任一達門檻
  5. low_quality_possible_buy ← 資料品質低但 pack 不在高估側（proxy，見下）

`low_quality_possible_buy` 的 proxy 說明：Phase 2 時點還沒有 tentative decision（Phase 3
才有），所以用 pack 自身當「可能 BUY」的替身 —— `verdict_band` 不在高估側 或
`vs_current_pct > 0`。刻意不改成 Phase 3 後補跑第二輪：那會打破 Phase 2 平行 fan-out 的結構。

Usage:
  python3 investment/scripts/valuation_reviewer_gate.py \
      --from-quant investment/invest_logs/<DATE>_<TICKER>_pf_quant.json
  python3 investment/scripts/valuation_reviewer_gate.py --from-quant f.json --ticker NVDA

rc=0 正常（含 would_invoke=false）；rc=1 只在 artifact 不可用（缺檔 / schema 不符 /
缺 quant block）—— gate 讀不到權威輸入時不得猜，否則 shadow 統計會混進假樣本。
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GATE_VERSION = "valuation_reviewer_gate.py v1.0 (V4.89.0)"
GATE_SCHEMA = "valuation_reviewer_gate.v1"

# anchor 衝突門檻 — 與 compute_price_framework 的 confidence cap 對齊，不另立一套。
CONFLICT_CV = 0.60               # == CONF_CAP_CV_LOW
CONFLICT_DISPERSION_RATIO = 5.0  # max/min 錨值跨度
LOW_QUALITY_MIN_ANCHORS = 4      # < 這個數 = 資料品質低
OVERVALUED_BANDS = ("overvalued", "extreme_overvalued")

TRANSITION_SIGNATURES = ("paradigm_only", "mix_only", "both")

# gate 實際讀到的每一個 leaf key。只驗 block 存在是不夠的：producer 掉了某個 key 時
# `_num(...) or 0` 會把「欄位不存在」讀成 0 → 判成低品質 → shadow 統計被無聲灌水。
# 缺 key 一律 rc=1，與「gate 讀不到權威輸入時不得猜」同一條紀律。
REQUIRED_LEAF_KEYS = {
    "valuation_pack": ("structural_shift", "verdict_band", "vs_current_pct"),
    "fair_value_summary": ("confidence", "anchors_available"),
    "fair_value_range": ("anchor_dispersion_cv", "dispersion_ratio", "agreement_grade"),
}


class GateInputError(Exception):
    """Artifact 不可用 — main() 轉成 {"error": ...} + rc=1。"""


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def load_quant_artifact(path: str) -> dict:
    """讀 Phase 1.5 artifact。壞掉一律 raise —— gate 不得用猜的輸入產 shadow 樣本。"""
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        raise GateInputError(f"unreadable --from-quant artifact: {e}")
    if not isinstance(payload, dict) or payload.get("schema") != "price_framework_quant.v1":
        raise GateInputError("--from-quant artifact is not price_framework_quant.v1")
    blocks = payload.get("quant_blocks")
    if not isinstance(blocks, dict):
        raise GateInputError("--from-quant artifact missing quant_blocks")
    missing = []
    for block, keys in REQUIRED_LEAF_KEYS.items():
        detail = blocks.get(block)
        if not isinstance(detail, dict):
            missing.append(f"quant_blocks.{block}")
            continue
        # 驗「key 在不在」而非「值是不是 null」——verdict_band / agreement_grade 等
        # 在無 eligible anchor 時合法為 null，那是資料不是缺料。
        missing.extend(f"quant_blocks.{block}.{k}" for k in keys if k not in detail)
    if missing:
        raise GateInputError(f"--from-quant artifact missing {', '.join(missing)}")
    return payload


def _latest_earnings_cache(ticker: str) -> dict:
    files = sorted(glob.glob(os.path.join(
        BASE_DIR, "skills", "earnings-analyst", "cache", f"{ticker.upper()}_*.json")))
    if not files:
        return {}
    try:
        with open(files[-1], encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _forecaster_cache(ticker: str) -> dict:
    path = os.path.join(BASE_DIR, "skills", "earnings-valuation-forecaster", "cache",
                        f"{ticker.upper()}.json")
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def peer_cohort_availability(ticker: str, *, today: dt.date | None = None) -> dict:
    """curated > discovered > none。valuation-modeler 目錄名有連字號，照 engine 既有作法
    掛 sys.path 再 import；模組不可用時 fail-loud（gate 不得把它當成「沒有 peers」）。"""
    vm_scripts = os.path.join(BASE_DIR, "skills", "valuation-modeler", "scripts")
    if vm_scripts not in sys.path:
        sys.path.insert(0, vm_scripts)
    try:
        import peer_cohorts
    except Exception as e:
        raise GateInputError(f"peer_cohorts module unavailable: {e}")
    return peer_cohorts.resolve_cohort_availability(ticker, today=today)


def read_transition_state(ticker: str) -> dict:
    """Phase 3 transition gate 的兩個上游訊號（與 decision_engine 同源）。"""
    ec = _latest_earnings_cache(ticker)
    signature = ec.get("transition_signature")
    if isinstance(signature, dict):
        signature = signature.get("signature") or signature.get("tier")
    fc = _forecaster_cache(ticker)
    case = (fc.get("transition_case") or {})
    case_flag = case.get("transition_case") if isinstance(case, dict) else None
    return {
        "transition_signature": signature,
        "forecaster_transition_case": case_flag is True,
        "earnings_cache_found": bool(ec),
        "forecaster_cache_found": bool(fc),
    }


def evaluate_triggers(quant: dict, *, ticker: str, transition: dict,
                      peer_availability: dict) -> list:
    """回傳 5 條 trigger 的完整評估（含未命中者與判定依據）。"""
    blocks = quant["quant_blocks"]
    pack = blocks["valuation_pack"]
    fvs = blocks["fair_value_summary"]
    frange = blocks["fair_value_range"]

    results = []

    # 1 — transition case（mandatory）
    signature = transition.get("transition_signature")
    sig_hit = str(signature or "") in TRANSITION_SIGNATURES
    case_hit = transition.get("forecaster_transition_case") is True
    results.append({
        "trigger": "transition_case_active",
        "mandatory": True,
        "fired": bool(sig_hit or case_hit),
        "why": ("decision_engine 的 valuation_confirmed_transition 吃 lane 的 "
                "cited_transition_overlay / transition_dissent_basis；lane 不跑會讓 "
                "cascade rule #2 的 ×0.95 軟化失效（落回 ×0.85）"),
        "evidence": {"transition_signature": signature,
                     "forecaster_transition_case": case_hit},
    })

    # 2 — peer cohort 可用性
    results.append({
        "trigger": "no_peer_cohort",
        "mandatory": False,
        "fired": not peer_availability.get("available"),
        "why": "無 curated 也無未過期 discovered cohort → 需要 reviewer 提 peers",
        "evidence": {k: peer_availability.get(k) for k in
                     ("available", "provenance", "peer_count", "expires_on", "reason")},
    })

    # 3 — structural shift typed input
    shift = pack.get("structural_shift") or {}
    confirmed = (shift.get("confirmed") is True
                 or str(shift.get("status") or "").upper() == "CONFIRMED")
    typed_complete = bool(confirmed and shift.get("evidence_date") and shift.get("provenance"))
    results.append({
        "trigger": "structural_shift_typed",
        "mandatory": False,
        "fired": typed_complete,
        "why": "typed shift 齊備時估值敘事會壓過歷史錨，需要人看解釋",
        "evidence": {"confirmed": confirmed,
                     "evidence_date": shift.get("evidence_date"),
                     "provenance": shift.get("provenance")},
    })

    # 4 — anchor 嚴重衝突
    cv = _num(frange.get("anchor_dispersion_cv"))
    ratio = _num(frange.get("dispersion_ratio"))
    grade = frange.get("agreement_grade")
    conflict = bool((cv is not None and cv >= CONFLICT_CV)
                    or (ratio is not None and ratio >= CONFLICT_DISPERSION_RATIO)
                    or grade == "low")
    results.append({
        "trigger": "anchor_conflict_severe",
        "mandatory": False,
        "fired": conflict,
        "why": f"cv≥{CONFLICT_CV} / span≥{CONFLICT_DISPERSION_RATIO}x / agreement_grade=low",
        "evidence": {"anchor_dispersion_cv": cv, "dispersion_ratio": ratio,
                     "agreement_grade": grade},
    })

    # 5 — 資料品質低但可能 BUY（proxy：Phase 2 時點無 tentative decision）
    # load_quant_artifact 已保證 key 存在；null 是「算不出來」= 最低品質，與缺 key 不同。
    anchors_available = _num(fvs.get("anchors_available"))
    confidence = fvs.get("confidence")
    low_quality = bool(confidence == "low" or anchors_available is None
                       or anchors_available < LOW_QUALITY_MIN_ANCHORS)
    verdict = pack.get("verdict_band")
    vs_pct = _num(pack.get("vs_current_pct"))
    # verdict 未知（無 eligible anchor → pack 算不出 verdict）算「不在高估側」：
    # 資料品質低 + 估值完全未知，正是最該叫 reviewer 的情形。判 False 會讓
    # 最不確定的 session 反而跳過人看，方向錯的。
    possible_buy = bool(verdict not in OVERVALUED_BANDS
                        or (vs_pct is not None and vs_pct > 0))
    results.append({
        "trigger": "low_quality_possible_buy",
        "mandatory": False,
        "fired": bool(low_quality and possible_buy),
        "why": ("資料品質低卻不在高估側 → 誤判成本不對稱；possible_buy 是 pack proxy，"
                "Phase 2 時點尚無 tentative decision"),
        "evidence": {"confidence": confidence, "anchors_available": anchors_available,
                     "verdict_band": verdict, "vs_current_pct": vs_pct,
                     "low_quality": low_quality, "possible_buy": possible_buy},
    })
    return results


def build_gate_record(quant: dict, *, ticker: str | None = None,
                      today: dt.date | None = None,
                      peer_availability: dict | None = None,
                      transition: dict | None = None) -> dict:
    """peer_availability / transition 可注入（測試用）；預設走真實 cache。"""
    symbol = str(ticker or quant.get("ticker") or "").upper()
    if not symbol:
        raise GateInputError("ticker required (artifact has none; pass --ticker)")

    if peer_availability is None:
        peer_availability = peer_cohort_availability(symbol, today=today)
    if transition is None:
        transition = read_transition_state(symbol)
    triggers = evaluate_triggers(quant, ticker=symbol, transition=transition,
                                 peer_availability=peer_availability)
    fired = [t for t in triggers if t["fired"]]
    return {
        "schema": GATE_SCHEMA,
        "engine": GATE_VERSION,
        "ticker": symbol,
        "evaluated_at": (today or dt.date.today()).isoformat(),
        "shadow_only": True,
        "would_invoke": bool(fired),
        "mandatory_fired": any(t["mandatory"] for t in fired),
        "triggers_fired": [t["trigger"] for t in fired],
        "triggers": triggers,
        "inputs_used": {
            "quant_artifact_engine": quant.get("engine"),
            "quant_artifact_persisted_to": quant.get("persisted_to"),
            "peer_cohort_provenance": peer_availability.get("provenance"),
            "earnings_cache_found": transition.get("earnings_cache_found"),
            "forecaster_cache_found": transition.get("forecaster_cache_found"),
        },
        "note": ("shadow-only — PM 照跑 Valuation Specialist；本紀錄不改任何決策數字。"
                 "翻預設需使用者拍板（見 protocol §PHASE 2 Valuation Specialist）"),
    }


def main():
    ap = argparse.ArgumentParser(description="Valuation Specialist 條件式觸發 gate (shadow-only)")
    ap.add_argument("--from-quant", required=True, help="Phase 1.5 quant artifact 路徑")
    ap.add_argument("--ticker", help="artifact 無 ticker 時指定")
    args = ap.parse_args()
    try:
        record = build_gate_record(load_quant_artifact(args.from_quant), ticker=args.ticker)
    except GateInputError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()

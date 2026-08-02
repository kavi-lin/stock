#!/usr/bin/env python3
"""test_lane_contract.py — V4.90.0 C1 統一 lane 資料契約。

分兩半：

**A. Producer**（`apply_det_shadow.build_lane_contract` / `apply_to_trade`）
   契約的價值全押在「誰產的」這件事上，所以 producer 最容易出的錯不是形狀，而是
   **把別人已經填好的 provenance 覆寫回 LLM 預設**。L5 / L6 / L8 都會在自己的 phase 先寫
   自己那個 lane，post-processor 事後才跑到；保留規則一旦破掉，這三項全部靜默失效——
   契約還在、值域還對、驗證還綠，只是每個 lane 都變成 `llm`。所以保留規則的 case 最多。

   版本閘同理：`--inplace history.json` 會走過 181 筆舊 entry，producer 若不看版號就會
   給 V4.6 的四 lane session 補一份六 lane provenance ——「看起來很完整」的假證據，而
   Phase 6 按 provenance 分層時會直接吃到它。

**B. Validator §15** — tamper battery。每個值域 / 一致性規則各壞一次，確認 rc=1。
   session 層兩個清單是 per-lane 的投影而不是獨立事實，所以「清單與 per-lane 不符」
   必須擋——否則手改清單就能偽造「這個 lane 沒跑 LLM」。

Usage:  python3 investment/scripts/test_lane_contract.py
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
from apply_det_shadow import (  # noqa: E402
    ANALYSIS_MODES,
    LANE_FIELDS,
    LANE_NAMES,
    apply_to_session_export,
    apply_to_trade,
    build_lane_contract,
    protocol_version,
)
from test_session_export_schema import extract_full_example  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VALIDATOR = os.path.join(ROOT, "investment/scripts/validate_session_export.py")

FAILS: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    if cond:
        print(f"  ok  {label}")
    else:
        FAILS.append(f"{label}{': ' + detail if detail else ''}")


def run_validator(entry: dict, label: str, want_rc: int,
                  want_substr: str | None = None) -> None:
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


def mutate(entry: dict, fn) -> dict:
    """deepcopy the fixture, hand `lane_contract` to `fn`, return the entry."""
    e = copy.deepcopy(entry)
    fn(e["trades_this_session"][0]["lane_contract"])
    return e


# ═══════════════════════════════════════════════════════════════════════════
# A. Producer
# ═══════════════════════════════════════════════════════════════════════════

def test_producer_defaults() -> None:
    print("[producer — 預設：今天六個 lane 都是 LLM 產出]")
    lc = build_lane_contract({}, val_det=0.5)

    check(list(lc["lanes"]) == list(LANE_NAMES),
          "六個 lane 全列且順序固定", str(list(lc["lanes"])))
    check(all(set(b) == set(LANE_FIELDS) for b in lc["lanes"].values()),
          "每個 lane 剛好五個契約欄位")
    check(all(b["provenance"] == "llm" for b in lc["lanes"].values()),
          "無 producer 認領 → provenance=llm")
    check(all(b["llm_invoked"] is True for b in lc["lanes"].values()),
          "llm ⇒ llm_invoked=True")
    check(all(b["producer_version"] == f"protocol:{protocol_version()}"
              for b in lc["lanes"].values()),
          "LLM lane 的 producer_version 綁 repo VERSION")
    check(all(b["input_hash"] is None for b in lc["lanes"].values()),
          "input_hash 今天恆 null（L9 才會填）")
    check(lc["lanes"]["valuation"]["shadow_score"] == 0.5,
          "valuation 的 shadow_score 吃傳入的 val_det")
    check(all(lc["lanes"][n]["shadow_score"] is None
              for n in LANE_NAMES if n != "valuation"),
          "其餘 lane 尚無 det producer → shadow_score=null")
    check(lc["analysis_mode"] == "FULL_IC", "analysis_mode 預設 FULL_IC")
    check(sorted(lc["llm_invoked_lanes"]) == sorted(LANE_NAMES)
          and lc["llm_skipped_lanes"] == [],
          "session 層清單 = per-lane 投影")
    check(lc["contract_version"] == "C1/1.0", "contract_version 戳記")


def test_producer_absent() -> None:
    print("[producer — 缺席的 lane]")
    lc = build_lane_contract({}, missing_lanes=["sentiment", "technical"])
    for n in ("sentiment", "technical"):
        b = lc["lanes"][n]
        check(b["provenance"] == "absent" and b["llm_invoked"] is False,
              f"{n} 無分數 → absent / llm_invoked=False", json.dumps(b))
        check(b["producer_version"] is None,
              f"{n} absent → 不編造 producer_version")
    check(sorted(lc["llm_skipped_lanes"]) == ["sentiment", "technical"],
          "llm_skipped_lanes 反映缺席 lane")

    rt = build_lane_contract({"red_team_execution_failed": True})["lanes"]["red_team"]
    check(rt["provenance"] == "absent" and rt["llm_invoked"] is False,
          "red_team_execution_failed → red_team absent", json.dumps(rt))
    # missing_lanes 只講五個分析 lane；RT 的缺席訊號是自己的旗標，兩者不可互相汙染。
    rt2 = build_lane_contract({}, missing_lanes=["red_team"])["lanes"]["red_team"]
    check(rt2["provenance"] == "llm",
          "RT 不看 missing_lanes（它的缺席由 red_team_execution_failed 決定）")


def test_producer_preserves() -> None:
    print("[producer — 保留規則（L5 / L6 / L8 的生死線）]")
    trade = {
        "lane_contract": {
            "analysis_mode": "LEAN",
            "lanes": {
                "sentiment": {
                    "provenance":       "deterministic",
                    "llm_invoked":      False,
                    "producer_version": "sentiment_det.py v1.0",
                    "input_hash":       "sha256:abc",
                    "shadow_score":     0.0,
                },
                "valuation": {"provenance": "hybrid", "shadow_score": -1.0},
            },
        }
    }
    lc = build_lane_contract(copy.deepcopy(trade), val_det=0.5)

    s = lc["lanes"]["sentiment"]
    check(s["provenance"] == "deterministic", "det lane 的 provenance 不被覆寫回 llm")
    check(s["llm_invoked"] is False,
          "llm_invoked=False 由 provenance 推導（4.90.4 起恆為投影，不吃保留值）",
          json.dumps(s))
    check(s["producer_version"] == "sentiment_det.py v1.0",
          "det producer 的版號不被 protocol: 版號蓋掉")
    check(s["input_hash"] == "sha256:abc", "input_hash 保留")
    check(s["shadow_score"] == 0.0,
          "shadow_score=0.0 被保留（0.0 不是空值）", json.dumps(s))

    v = lc["lanes"]["valuation"]
    check(v["provenance"] == "hybrid" and v["llm_invoked"] is True,
          "hybrid ⇒ llm_invoked=True")
    check(v["shadow_score"] == 0.5,
          "valuation 例外：本次重算的 val_det 勝過既有值（同 producer）", json.dumps(v))
    check(v["producer_version"] == f"protocol:{protocol_version()}",
          "hybrid 缺 producer_version → 補 protocol 版號（不留空觸發 validator）")

    check(lc["analysis_mode"] == "LEAN", "既有 analysis_mode 保留")
    check(lc["llm_skipped_lanes"] == ["sentiment"],
          "session 清單跟著保留值重算", json.dumps(lc["llm_skipped_lanes"]))

    bad = build_lane_contract({"lane_contract": {"analysis_mode": "TURBO"}})
    check(bad["analysis_mode"] == "FULL_IC",
          f"值域外的 analysis_mode 落回 FULL_IC（值域 {list(ANALYSIS_MODES)}）")


def test_producer_idempotent() -> None:
    print("[producer — 冪等]")
    t = {"valuation_pack": {"score": 1.0, "weighted_fair_value": 120.0,
                            "vs_current_pct": 20.0}}
    once = copy.deepcopy(apply_to_trade(copy.deepcopy(t))["lane_contract"])
    twice = apply_to_trade({**copy.deepcopy(t), "lane_contract": copy.deepcopy(once)})
    check(twice["lane_contract"] == once,
          "重跑 post-processor 產出 bitwise 相同的契約")


def test_producer_version_gate() -> None:
    print("[producer — 版本閘：舊 entry 不回填]")
    t = apply_to_trade({}, entry_version="V5.0")
    check("lane_contract" not in t, "V5.0 entry 不寫契約")
    check(isinstance(t.get("det_shadow"), dict), "但 det_shadow 照舊寫（既有行為不變）")
    check("lane_contract" in apply_to_trade({}, entry_version="V5.3"), "V5.3 entry 寫契約")
    check("lane_contract" in apply_to_trade({}), "無 entry 外殼（單筆 trade CLI 路徑）→ 寫契約")

    payload_old = {"session_export_version": "V5.0", "export_date": "2026-04-18",
                   "trades_this_session": [{}]}
    payload_new = {"session_export_version": "V5.3", "export_date": "2026-08-03",
                   "trades_this_session": [{}]}
    apply_to_session_export(payload_old)
    apply_to_session_export(payload_new)
    check("lane_contract" not in payload_old["trades_this_session"][0],
          "走 history list 時舊 entry 原封不動")
    check("lane_contract" in payload_new["trades_this_session"][0],
          "同一次 --inplace 仍會寫新 entry")

    # 有外殼卻缺版號 = 壞掉的 entry，不是「無版號的 trade」。兩個 None 來源必須分開處理，
    # 否則漏一個欄位就換來一份契約（§2e 之後也會擋，但 producer 先別寫比較乾淨）。
    payload_nover = {"export_date": "2026-08-03", "trades_this_session": [{}]}
    apply_to_session_export(payload_nover)
    check("lane_contract" not in payload_nover["trades_this_session"][0],
          "session-export 外殼缺 session_export_version → 不寫契約")
    check(isinstance(payload_nover["trades_this_session"][0].get("det_shadow"), dict),
          "但 det_shadow 照舊寫（既有行為不變）")


def test_derivation_domain_reconverges() -> None:
    """4.90.4 回歸 —— P2 的病往旁邊一格：`provenance` 的 llm/absent 與 `llm_invoked`
    也是 post-processor 自己的推導域，套保留規則就是同款死結。

    實錘的真實序列（非 tamper）：PM 漏填 sentiment 的 lane score → Step 1.5 推成
    absent → validator 報 lane_scores 缺 key → PM 補分數 → 重跑 Step 1.5 →
    4.90.4 前上一輪的 absent 被自己保留住，§15 報「重跑可修」而重跑永遠修不好。
    """
    print("[producer — 推導域重算贏（4.90.4 回歸）]")
    t = {"lane_scores": {"fundamentals": 4, "news": 3, "technical": 4},
         "valuation_pack": {"score": 1.0, "weighted_fair_value": 120.0,
                            "vs_current_pct": 20.0}}
    apply_to_trade(t)
    check(t["lane_contract"]["lanes"]["sentiment"]["provenance"] == "absent",
          "漏填的 lane 先被推成 absent（此時 validator 會擋 lane_scores 缺 key）")
    t["lane_scores"]["sentiment"] = 3
    apply_to_trade(t)
    check(t["lane_contract"]["lanes"]["sentiment"]["provenance"] == "llm",
          "補上分數重跑 → absent 重推成 llm（4.90.4 前被保留規則鎖死）")

    t["lane_contract"]["lanes"]["news"]["llm_invoked"] = False   # corrupt
    apply_to_trade(t)
    check(t["lane_contract"]["lanes"]["news"]["llm_invoked"] is True,
          "corrupt 的 llm_invoked 重跑即修復（恆為 provenance 投影）")

    # 界線的另一側：外來聲明不因此被掃掉。
    t2 = {"lane_scores": {"fundamentals": 4, "sentiment": 3, "news": 3, "technical": 4},
          "valuation_pack": {"score": 0.5, "weighted_fair_value": 110.0,
                             "vs_current_pct": 10.0},
          "lane_contract": {"lanes": {
              "sentiment": {"provenance": "deterministic", "llm_invoked": False,
                            "producer_version": "sentiment_det.py v1.0",
                            "input_hash": "sha256:abc", "shadow_score": 0.0}}}}
    apply_to_trade(t2)
    s = t2["lane_contract"]["lanes"]["sentiment"]
    check(s["provenance"] == "deterministic" and s["input_hash"] == "sha256:abc"
          and s["shadow_score"] == 0.0,
          "EXTERNAL_PROVENANCE（det/hybrid）與其欄位仍完整保留")

    # L5 shadow 期的形態：provenance=llm + 外來 shadow_score / producer_version —— 保留。
    t3 = {"lane_scores": {"fundamentals": 4, "sentiment": 3, "news": 3, "technical": 4},
          "valuation_pack": {"score": 0.5, "weighted_fair_value": 110.0,
                             "vs_current_pct": 10.0},
          "lane_contract": {"lanes": {"sentiment": {"shadow_score": -1.0}}}}
    apply_to_trade(t3)
    s = t3["lane_contract"]["lanes"]["sentiment"]
    check(s["provenance"] == "llm" and s["shadow_score"] == -1.0,
          "L5 shadow 形態：provenance 推導為 llm、外來 shadow_score 保留")


def test_absorb_never_diverges() -> None:
    """保留規則 × 吸收閘的邊界（4.90.1 回歸）。

    `valuation.shadow_score` 的 producer 是 `apply_to_trade()` 自己，`det_shadow` 那塊又是
    每次整塊重建。4.90.0 對這欄套了保留規則，於是上游 pack 一改就兩邊分歧、§15 永久 rc=1，
    而錯誤訊息叫人重跑 post-processor —— 重跑修不好，因為保留規則會繼續保住舊值。
    這裡對「值變了」與「值變回 None」兩支都鎖死重算贏。
    """
    print("[producer — 吸收閘不可能被保留規則卡死（4.90.1 回歸）]")

    def both(t):
        return (t["lane_contract"]["lanes"]["valuation"]["shadow_score"],
                t["det_shadow"]["valuation_score_det"])

    t = {"valuation_pack": {"score": 1.0, "weighted_fair_value": 120.0,
                            "vs_current_pct": 20.0}}
    apply_to_trade(t)
    check(both(t) == (1.0, 1.0), "首跑兩邊同值", str(both(t)))
    t["valuation_pack"]["score"] = -0.5
    apply_to_trade(t)
    check(both(t) == (-0.5, -0.5),
          "上游 pack 改了 → 重跑收斂，不是分歧", str(both(t)))

    t2 = {"valuation_pack": {"score": 1.0, "weighted_fair_value": 120.0,
                             "vs_current_pct": 20.0}}
    apply_to_trade(t2)
    t2.pop("valuation_pack")
    apply_to_trade(t2)
    check(both(t2) == (None, None),
          "val_det 變回 None → 契約跟著清空（保留舊值一樣會卡死閘）", str(both(t2)))

    # 其餘 lane 的保留規則不受影響——這條界線就是 P2 的根因所在。
    keep = build_lane_contract(
        {"lane_contract": {"lanes": {"sentiment": {
            "provenance": "deterministic", "llm_invoked": False,
            "producer_version": "sentiment_det.py v1.0", "shadow_score": 0.0}}}},
        val_det=1.0)
    check(keep["lanes"]["sentiment"]["shadow_score"] == 0.0,
          "非 valuation lane 的 shadow_score 仍受保留規則保護")


def test_absorb() -> None:
    print("[producer — 吸收：契約與 det_shadow 同源]")
    t = apply_to_trade({"valuation_pack": {"score": -0.5, "weighted_fair_value": 80.0,
                                           "vs_current_pct": -12.0}})
    check(t["lane_contract"]["lanes"]["valuation"]["shadow_score"]
          == t["det_shadow"]["valuation_score_det"] == -0.5,
          "canonical pack：兩處同值", json.dumps(t["det_shadow"]["valuation_score_det"]))
    # 無 pack 的 legacy 路徑走 FV-vs-price 映射，吸收關係一樣要成立。
    t2 = apply_to_trade({"fair_value_summary": {"weighted_fair_value": 130.0,
                                                "vs_current_pct": 30.0}})
    check(t2["lane_contract"]["lanes"]["valuation"]["shadow_score"]
          == t2["det_shadow"]["valuation_score_det"] == 1.0,
          "legacy FV 路徑：兩處同值")


# ═══════════════════════════════════════════════════════════════════════════
# B. Validator §15
# ═══════════════════════════════════════════════════════════════════════════

def test_validator(ex: dict) -> None:
    print("[validator §15 — 值域]")
    run_validator(ex, "V5.3 fixture with contract", 0)
    run_validator(mutate(ex, lambda lc: lc["lanes"]["news"].update(provenance="magic")),
                  "tamper: provenance off the enum", 1, "provenance invalid")
    run_validator(mutate(ex, lambda lc: lc.update(analysis_mode="TURBO")),
                  "tamper: analysis_mode off the enum", 1, "analysis_mode invalid")
    run_validator(mutate(ex, lambda lc: lc["lanes"]["news"].update(shadow_score="0.5")),
                  "tamper: shadow_score as string", 1, "shadow_score must be number")
    run_validator(mutate(ex, lambda lc: lc["lanes"]["news"].pop("input_hash")),
                  "tamper: contract field dropped", 1, "missing field input_hash")

    print("[validator §15 — 一致性]")
    run_validator(
        mutate(ex, lambda lc: lc["lanes"]["news"].update(llm_invoked=False)),
        "tamper: llm_invoked contradicts provenance", 1, "contradicts provenance")
    run_validator(
        mutate(ex, lambda lc: lc["lanes"]["sentiment"].update(
            provenance="deterministic", llm_invoked=False, producer_version=None)),
        "tamper: deterministic lane with no producer_version", 1,
        "producer_version required")
    run_validator(mutate(ex, lambda lc: lc["lanes"].pop("technical")),
                  "tamper: a lane omitted instead of marked absent", 1,
                  "missing lane(s)")
    run_validator(mutate(ex, lambda lc: lc["lanes"].update(burry={})),
                  "tamper: unknown lane in the contract", 1, "unknown lane(s)")

    print("[validator §15 — 4.90.2 回歸：兩條實錘過的繞道]")
    # (A) lane block 塞 null + session 清單配合對齊 —— 4.90.2 前 rc=0：
    # `if blk is None: continue` 的註解說「已由 absent_lanes 報過」，但那只抓缺 key，
    # 抓不到 key 在、值為 null，五個欄位檢查整組被跳過。
    e = mutate(ex, lambda lc: (lc["lanes"].update(sentiment=None),
                               lc["llm_invoked_lanes"].remove("sentiment"),
                               lc["llm_skipped_lanes"].append("sentiment")))
    run_validator(e, "tamper: lane block nulled with lists aligned (4.90.2 前全綠)", 1,
                  "must be an object")
    # (B) 有分數的 lane 手改 absent —— 4.90.2 前 rc=0：provenance 一致性只驗過
    # llm_invoked，沒驗過實際訊號。Phase 6 會把這筆從 LLM 池靜默剔除。
    e = mutate(ex, lambda lc: (lc["lanes"]["sentiment"].update(
                                   provenance="absent", llm_invoked=False,
                                   producer_version=None),
                               lc["llm_invoked_lanes"].remove("sentiment"),
                               lc["llm_skipped_lanes"].append("sentiment")))
    run_validator(e, "tamper: scored lane marked absent (4.90.2 前全綠)", 1,
                  "有分數")
    # (B 反向) 分數不見了卻仍標 llm —— 沒產出的 lane 不得自稱有產出。
    e = copy.deepcopy(ex)
    e["trades_this_session"][0]["lane_scores"].pop("sentiment")
    run_validator(e, "tamper: score removed but lane still claims llm", 1, "無分數")
    # (RT 反向) RT 沒失敗卻標 absent。
    e = mutate(ex, lambda lc: (lc["lanes"]["red_team"].update(
                                   provenance="absent", llm_invoked=False,
                                   producer_version=None),
                               lc["llm_invoked_lanes"].remove("red_team"),
                               lc["llm_skipped_lanes"].append("red_team")))
    run_validator(e, "tamper: red_team marked absent though it ran", 1,
                  "不得自稱缺席")

    print("[validator §15 — session 清單是投影，不是獨立事實]")
    run_validator(mutate(ex, lambda lc: lc["llm_invoked_lanes"].remove("sentiment")),
                  "tamper: lane dropped from both lists (not a partition)", 1,
                  "剛好分割六個 lane")
    run_validator(
        mutate(ex, lambda lc: (lc["llm_invoked_lanes"].remove("sentiment"),
                               lc["llm_skipped_lanes"].append("sentiment"))),
        "tamper: lane moved to skipped while per-lane says invoked", 1,
        "不符 — session 層清單是 per-lane 的投影")

    print("[validator §15 — lane_scores 是 provenance 的推導基礎]")
    # 省略 lane_scores 會讓四個跑過的 lane 被推成 absent —— 用「少寫一個欄位」偽造
    # provenance，而且事後從 entry 完全看不出來。C1 起這是 error。
    e = copy.deepcopy(ex)
    e["trades_this_session"][0].pop("lane_scores")
    run_validator(e, "tamper: lane_scores omitted (silently marks 4 lanes absent)", 1,
                  "偽造 provenance")
    # 部分省略 = 同一個洞的零售版（4.90.2 前 rc=0）：producer 與 validator 會一致同意
    # 那三個 lane 缺席，所以「兩邊一致」在這裡完全不是保護。
    e = copy.deepcopy(ex)
    e["trades_this_session"][0]["lane_scores"] = {"fundamentals": 4}
    run_validator(e, "tamper: lane_scores partially omitted (3 lanes → absent)", 1,
                  "missing key(s)")
    # 明寫 null 是合法的「這個 lane 沒產出」宣告——擋的是省略，不是缺席本身。
    e = copy.deepcopy(ex)
    e["trades_this_session"][0]["lane_scores"]["sentiment"] = None
    e["trades_this_session"][0]["lane_contract"]["lanes"]["sentiment"].update(
        provenance="absent", llm_invoked=False, producer_version=None)
    lists = e["trades_this_session"][0]["lane_contract"]
    lists["llm_invoked_lanes"].remove("sentiment")
    lists["llm_skipped_lanes"].append("sentiment")
    run_validator(e, "lane_scores.sentiment=null + contract says absent (legal)", 0)

    print("[validator §15 — 吸收閘 + RT]")
    run_validator(
        mutate(ex, lambda lc: lc["lanes"]["valuation"].update(shadow_score=-1.0)),
        "tamper: contract shadow edited away from det_shadow", 1,
        "det_shadow.valuation_score_det")
    e = copy.deepcopy(ex)
    e["trades_this_session"][0]["red_team_execution_failed"] = True
    run_validator(e, "tamper: RT execution failed but contract says llm_invoked", 1,
                  "red_team_execution_failed=true")

    print("[validator §15 — lane 區塊形狀鎖]")
    for lane_key, field, bad, msg in (
            ("fundamentals_lane", "moat_assessment", "Wide moat, 10y runway",
             "must be an object"),
            ("news_lane", "immediate_catalyst_5d", "earnings 8/28", "must be an object"),
            ("technical_lane", "smart_money_analysis", "accumulation", "must be an object"),
    ):
        e = copy.deepcopy(ex)
        e["trades_this_session"][0][lane_key] = {field: bad}
        run_validator(e, f"tamper: {lane_key}.{field} as string", 1, msg)

    e = copy.deepcopy(ex)
    e["trades_this_session"][0]["technical_lane"] = {
        "smart_money_analysis": {"label": "ACCUMULATION", "note": "OBV rising"}}
    run_validator(e, "tamper: smart_money body under the retired 'note' key", 1,
                  "正文欄位請用")

    e = copy.deepcopy(ex)
    e["trades_this_session"][0]["news_lane"] = {"immediate_catalyst_5d": None}
    run_validator(e, "immediate_catalyst_5d=null is legal (no catalyst)", 0)

    # 形狀鎖對舊 entry 靜默：V5.2 的字串 moat 不該因為今天的規則變成錯誤。
    e = copy.deepcopy(ex)
    e["session_export_version"] = "V5.2"
    e["trades_this_session"][0].pop("lane_contract")
    e["trades_this_session"][0]["fundamentals_lane"] = {"moat_assessment": "Wide moat"}
    run_validator(e, "V5.2 entry keeps the legacy string shape", 0)


def main() -> int:
    test_producer_defaults()
    test_producer_absent()
    test_producer_preserves()
    test_producer_idempotent()
    test_producer_version_gate()
    test_derivation_domain_reconverges()
    test_absorb_never_diverges()
    test_absorb()
    test_validator(extract_full_example())

    if FAILS:
        print(f"\n✗ {len(FAILS)} contract failure(s):")
        for f in FAILS:
            print("  - " + f)
        return 1
    print("\n✓ C1 lane contract holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())

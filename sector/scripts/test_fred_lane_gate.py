#!/usr/bin/env python3
"""test_fred_lane_gate.py — SE5 FRED lane 條件式 gate 回歸測試（shadow-only）。

鎖住四件事：
  1. **`adjustments_active` 是唯一 mandatory**：adjustments 空 → 靜默（RULE 4「base map
     valid as-is」，step6_overlay 已 deterministic 套完 favor）；非空 → 必觸發，因為
     lane 是 RULE 1/2 的唯一執行者。
  2. 其餘三條 trigger 各自獨立命中，且各自的否定案例不誤觸發。
  3. **低信心不是 trigger**，只是 note —— 低信心時 step6 的 confidence gating 已把乘數
     壓回 1.0 附近，lane 增量更低，把它當觸發條件方向是反的。
  4. **shadow_only 恆為 true**：翻預設是使用者拍板的事，任一場不得自行決定。

純 stdlib、零網路、不碰真實 cache（全部走 tmpdir）。
Run: python3 sector/scripts/test_fred_lane_gate.py   # rc=0 全過 / rc=1 fail
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fred_lane_gate import (  # noqa: E402
    GATE_SCHEMA,
    GateInputError,
    build_gate_record,
    collect_gate_status,
    evaluate_triggers,
    load_fred,
    previous_regime_label,
    write_gate_record,
)

FAILS = []
DATE = "2026-08-03"


def eq(label, got, want):
    if got != want:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


def fred(*, adjustments=None, avoid=None, favor=None, label="Soft Landing",
         confidence=0.7, real_rate=1.2):
    return {
        "generated_at": "2026-08-03T00:00:00+00:00",
        "regime_label": label, "regime_confidence": confidence,
        "macro_scores": {"composite": 68},
        "regime_signals": {"yield_curve_value": 0.8, "yield_curve_inverted": False,
                           "credit_stress_elevated": False,
                           "financial_stress_above_avg": False,
                           "fed_rate_direction": "flat",
                           "real_rate_preferred": real_rate},
        "sector_rotation": {"regime": label,
                            "favor": favor if favor is not None else ["Technology"],
                            "avoid": avoid if avoid is not None else [],
                            "adjustments": adjustments if adjustments is not None else []},
        "change_velocity": {},
    }


ADJ_REAL_RATE = {"factor": "real_rate_high", "value": 2.41,
                 "lower": ["Technology", "Real Estate"],
                 "raise": ["Financials", "Energy"]}
ADJ_CREDIT = {"factor": "credit_stress", "value": 1.0,
              "lower": ["Financials"], "raise": ["Consumer Staples"]}

# ── 1. adjustments 空 → 靜默（lane 只會覆述 step6 已算過的 favor）───────────
r = evaluate_triggers(fred(), hot_sectors=["Technology"], prev_regime="Soft Landing")
eq("quiet.would_invoke", r["would_invoke"], False)
eq("quiet.no_triggers", r["triggers_fired"], [])
eq("quiet.no_gap_note", r["notes"], [])

# ── 2. adjustments 非空 → mandatory ─────────────────────────────────────────
r = evaluate_triggers(fred(adjustments=[ADJ_REAL_RATE]),
                      hot_sectors=[], prev_regime="Soft Landing")
eq("adj.fires", r["would_invoke"], True)
eq("adj.mandatory", r["mandatory_fired"], ["adjustments_active"])
eq("adj.factor_cited", "real_rate_high" in r["triggers"][0]["detail"], True)
# 既有缺口（lane 收不到 adjustments）必須被標出來
eq("adj.gap_note_present", any("slim 11 欄不含" in n for n in r["notes"]), True)

# ── 3. adjustment_conflict（RULE 2 仲裁）────────────────────────────────────
# real_rate_high raise Financials；credit_stress lower Financials → 同一 sector 衝突
r = evaluate_triggers(fred(adjustments=[ADJ_REAL_RATE, ADJ_CREDIT]),
                      hot_sectors=[], prev_regime="Soft Landing")
eq("conflict.fires", "adjustment_conflict" in r["triggers_fired"], True)
detail = next(t["detail"] for t in r["triggers"] if t["name"] == "adjustment_conflict")
eq("conflict.names_sector", "Financials" in detail, True)
eq("conflict.not_mandatory",
   next(t["mandatory"] for t in r["triggers"] if t["name"] == "adjustment_conflict"), False)
# 單一 adjustment 內的 raise/lower 不互相衝突
r = evaluate_triggers(fred(adjustments=[ADJ_REAL_RATE]),
                      hot_sectors=[], prev_regime="Soft Landing")
eq("conflict.single_adj_no_conflict", "adjustment_conflict" in r["triggers_fired"], False)

# ── 4. macro_theme_conflict ────────────────────────────────────────────────
r = evaluate_triggers(fred(avoid=["Utilities"]),
                      hot_sectors=["Utilities"], prev_regime="Soft Landing")
eq("clash.avoid_fires", "macro_theme_conflict" in r["triggers_fired"], True)
r = evaluate_triggers(fred(adjustments=[ADJ_REAL_RATE]),
                      hot_sectors=["Technology"], prev_regime="Soft Landing")
eq("clash.lower_fires", "macro_theme_conflict" in r["triggers_fired"], True)
# HOT 與 macro 同向 → 不觸發這條
r = evaluate_triggers(fred(adjustments=[ADJ_REAL_RATE]),
                      hot_sectors=["Financials"], prev_regime="Soft Landing")
eq("clash.aligned_quiet", "macro_theme_conflict" in r["triggers_fired"], False)
# 沒給 --hot 時不得憑空觸發
r = evaluate_triggers(fred(avoid=["Utilities"]), hot_sectors=[], prev_regime="Soft Landing")
eq("clash.no_hot_no_trigger", "macro_theme_conflict" in r["triggers_fired"], False)
# sector 名稱正規化（"Real Estate" vs canonical "Real_Estate"）
r = evaluate_triggers(fred(adjustments=[ADJ_REAL_RATE]),
                      hot_sectors=["Real_Estate"], prev_regime="Soft Landing")
eq("clash.canonicalized", "macro_theme_conflict" in r["triggers_fired"], True)

# ── 5. regime_transition ───────────────────────────────────────────────────
r = evaluate_triggers(fred(label="Stagflation"),
                      hot_sectors=[], prev_regime="Soft Landing")
eq("regime.change_fires", "regime_transition" in r["triggers_fired"], True)
r = evaluate_triggers(fred(label="Soft Landing"),
                      hot_sectors=[], prev_regime="Soft Landing")
eq("regime.same_quiet", "regime_transition" in r["triggers_fired"], False)
r = evaluate_triggers(fred(label="Soft Landing"), hot_sectors=[], prev_regime=None)
eq("regime.no_history_quiet", "regime_transition" in r["triggers_fired"], False)

# ── 6. 低信心是 note，不是 trigger ─────────────────────────────────────────
r = evaluate_triggers(fred(confidence=0.25), hot_sectors=[], prev_regime="Soft Landing")
eq("lowconf.not_a_trigger", r["would_invoke"], False)
eq("lowconf.noted", any("regime_confidence" in n for n in r["notes"]), True)
# 邊界：恰好 0.40 不算低信心
r = evaluate_triggers(fred(confidence=0.40), hot_sectors=[], prev_regime="Soft Landing")
eq("lowconf.boundary", r["notes"], [])

# ── 7. 壞形狀不得誤判 ───────────────────────────────────────────────────────
bad = fred(); bad["sector_rotation"] = None
r = evaluate_triggers(bad, hot_sectors=["Technology"], prev_regime="Soft Landing")
eq("robust.null_rotation_quiet", r["would_invoke"], False)
bad = fred(); bad["sector_rotation"]["adjustments"] = "not-a-list"
r = evaluate_triggers(bad, hot_sectors=[], prev_regime="Soft Landing")
eq("robust.bad_adjustments_type", r["would_invoke"], False)
bad = fred(adjustments=[ADJ_REAL_RATE, "junk", None])
r = evaluate_triggers(bad, hot_sectors=[], prev_regime="Soft Landing")
eq("robust.mixed_adjustment_items", r["mandatory_fired"], ["adjustments_active"])
# `_slim_fred` 依賴端的同型元素層（4.95.3）：change_velocity 的值、macro_scores
# 是 truthy 非 dict 時，`(info or {}).get` / `(... or {}).get` 照樣 AttributeError
bad = fred()
bad["change_velocity"] = {"T10Y2Y": "fast", "DGS10": None}
bad["macro_scores"] = "high"
r = evaluate_triggers(bad, hot_sectors=["Technology"], prev_regime="Soft Landing")
eq("robust.bad_cv_and_macro_scores_no_crash", r["would_invoke"], False)

# 7b. raise/lower **元素層**的型別（原本只守到 adjustments 頂層）
#     非字串元素會讓 canonicalize 直接 AttributeError（rc=1 但 stdout 空，
#     違反本檔「rc=1 只在 fred 不可讀」的契約）
bad = fred(adjustments=[{"factor": "credit_stress", "raise": [123],
                         "lower": ["Technology"]}])
r = evaluate_triggers(bad, hot_sectors=["Technology"], prev_regime="Soft Landing")
eq("robust.non_str_element_no_crash", r["mandatory_fired"], ["adjustments_active"])
eq("robust.non_str_element_noted", any("形狀異常" in n for n in r["notes"]), True)

# 字串值會被逐字元迭代，產生單字元「板塊」污染 conflict 統計
bad = fred(adjustments=[{"factor": "credit_stress", "raise": "Energy",
                         "lower": "Real Estate"}])
r = evaluate_triggers(bad, hot_sectors=[], prev_regime="Soft Landing")
eq("robust.str_value_no_char_sectors", "adjustment_conflict" in r["triggers_fired"], False)
eq("robust.str_value_noted", any("形狀異常" in n for n in r["notes"]), True)

# 7b-ii. avoid 的形狀同樣要守 + 留痕（4.95.2）：它是 macro_theme_conflict 的
# 判定輸入，靜默丟掉的元素若不留痕，「資料壞了」會被讀成「HOT 沒撞上 avoid」
bad = fred(avoid="Utilities")           # 字串 → 舊版逐字元迭代成單字元「板塊」
r = evaluate_triggers(bad, hot_sectors=["Utilities"], prev_regime="Soft Landing")
eq("robust.str_avoid_no_conflict", "macro_theme_conflict" in r["triggers_fired"], False)
eq("robust.str_avoid_noted",
   any("sector_rotation.avoid" in n for n in r["notes"]), True)
bad = fred(avoid=["Utilities", 123])    # 非字串元素略過，但合法元素照判
r = evaluate_triggers(bad, hot_sectors=["Utilities"], prev_regime="Soft Landing")
eq("robust.mixed_avoid_still_fires", "macro_theme_conflict" in r["triggers_fired"], True)
eq("robust.mixed_avoid_noted",
   any("sector_rotation.avoid" in n for n in r["notes"]), True)

# ── 7c. 舊形狀 cache：sector_rotation 巢狀在 market_implications 底下 ────────
# _slim_fred() 對舊形狀有 fallback，本檔的 adjustments 讀取**必須走同一條路徑**。
# 否則舊形狀 cache 會讓唯一的 mandatory trigger 靜默不觸發、gap note 一併消失，
# rc=0 無警告 —— shadow 統計就這樣累積出假的 skip 票。
old_shape = {
    "generated_at": "2026-08-03T00:00:00+00:00",
    "regime_signals": {"real_rate_preferred": 1.2},
    "market_implications": {
        "sector_rotation": {"favor": ["Technology"], "avoid": ["Utilities"],
                            "adjustments": [ADJ_REAL_RATE]},
    },
}
r = evaluate_triggers(old_shape, hot_sectors=["Technology"], prev_regime=None)
eq("oldshape.mandatory_fires", r["mandatory_fired"], ["adjustments_active"])
eq("oldshape.would_invoke", r["would_invoke"], True)
eq("oldshape.adjustment_count", r["context"]["adjustment_count"], 1)
eq("oldshape.gap_note_present", any("既有缺口" in n for n in r["notes"]), True)
# 舊形狀下派生的判定也要跟著回來，不是只有 mandatory 那一條
eq("oldshape.factor_cited", any("real_rate_high" in t["detail"] for t in r["triggers"]), True)
eq("oldshape.lower_clashes_with_hot", "macro_theme_conflict" in r["triggers_fired"], True)


def _legacy(f):
    """把 sector_rotation 搬進 market_implications（舊形狀）以便新舊對照。"""
    f = copy.deepcopy(f)
    f["market_implications"] = {"sector_rotation": f.pop("sector_rotation")}
    return f


r = evaluate_triggers(_legacy(fred(adjustments=[ADJ_REAL_RATE, ADJ_CREDIT])),
                      hot_sectors=[], prev_regime="Soft Landing")
eq("oldshape.conflict_fires", "adjustment_conflict" in r["triggers_fired"], True)
# fallback 不得無中生有：舊形狀但 adjustments 空 → 仍舊安靜
r = evaluate_triggers(_legacy(fred()), hot_sectors=["Technology"], prev_regime="Soft Landing")
eq("oldshape.empty_stays_quiet", r["would_invoke"], False)
eq("oldshape.empty_no_gap_note", r["notes"], [])
# 新舊形狀等價：同一份 rotation 內容，triggers 必須逐字相同
_f = fred(adjustments=[ADJ_REAL_RATE], avoid=["Utilities"])
eq("oldshape.equivalent_to_new_shape",
   evaluate_triggers(_legacy(_f), hot_sectors=["Technology"],
                     prev_regime="Soft Landing")["triggers"],
   evaluate_triggers(copy.deepcopy(_f), hot_sectors=["Technology"],
                     prev_regime="Soft Landing")["triggers"])
# 兩層都有 → 取頂層（與 `_slim_fred()` 的 `or` 順序一致，否則 avoid 與
# adjustments 會來自不同來源）
both = fred(adjustments=[ADJ_REAL_RATE])
both["market_implications"] = {"sector_rotation": {"favor": [], "avoid": [],
                                                   "adjustments": [ADJ_CREDIT]}}
r = evaluate_triggers(both, hot_sectors=[], prev_regime="Soft Landing")
eq("oldshape.top_level_wins",
   any("real_rate_high" in t["detail"] for t in r["triggers"]), True)

# ── 8. 落盤 / 讀出 / shadow_only ───────────────────────────────────────────
tmp = tempfile.mkdtemp(prefix="se5_")
try:
    rec = build_gate_record(fred(adjustments=[ADJ_REAL_RATE]), scan_date=DATE,
                            hot_sectors=["Technology"], prev_regime="Soft Landing",
                            prev_source="x.json")
    eq("record.shadow_only", rec["shadow_only"], True)
    eq("record.schema", rec["schema"], GATE_SCHEMA)
    write_gate_record(rec, cache_dir=tmp)

    quiet = build_gate_record(fred(), scan_date="2026-08-04", hot_sectors=[],
                              prev_regime="Soft Landing", prev_source="x.json")
    eq("record.quiet_shadow_only_too", quiet["shadow_only"], True)
    write_gate_record(quiet, cache_dir=tmp)

    st = collect_gate_status(tmp)
    eq("status.sessions", st["sessions"], 2)
    eq("status.invoke_count", st["would_invoke"], 1)
    eq("status.skip_count", st["would_skip"], 1)
    eq("status.rate", st["invoke_rate"], 0.5)
    eq("status.freq_top", st["trigger_frequency"].get("adjustments_active"), 1)

    # 壞檔不得被算成有效樣本
    with open(os.path.join(tmp, "fred_lane_gate_2026-08-05.json"), "w") as fh:
        fh.write("{broken")
    st = collect_gate_status(tmp)
    eq("status.malformed_excluded", st["sessions"], 2)
    eq("status.malformed_surfaced", len(st["malformed_files"]), 1)

    # would_invoke=null 不得記成一張 skip 票（「檔案壞了」≠「判定為 skip」，4.95.3）
    with open(os.path.join(tmp, "fred_lane_gate_2026-08-06.json"), "w") as fh:
        json.dump({"schema": GATE_SCHEMA, "scan_date": "2026-08-06",
                   "would_invoke": None, "triggers_fired": []}, fh)
    st = collect_gate_status(tmp)
    eq("status.null_invoke_not_a_skip_vote", st["sessions"], 2)
    eq("status.null_invoke_surfaced", len(st["malformed_files"]), 2)
    eq("status.skip_count_unchanged", st["would_skip"], 1)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ── 9. fred 不可用 → rc=1（不得靜默回 would_invoke=false）──────────────────
tmp2 = tempfile.mkdtemp(prefix="se5_err_")
try:
    try:
        load_fred(os.path.join(tmp2, "nope.json"))
        eq("err.missing_raises", "no_raise", "GateInputError")
    except GateInputError:
        eq("err.missing_raises", True, True)

    broken = os.path.join(tmp2, "broken.json")
    with open(broken, "w") as fh:
        fh.write("{not json")
    try:
        load_fred(broken)
        eq("err.unreadable_raises", "no_raise", "GateInputError")
    except GateInputError:
        eq("err.unreadable_raises", True, True)

    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "fred_lane_gate.py"), "--date", DATE,
         "--fred", os.path.join(tmp2, "nope.json")],
        capture_output=True, text=True)
    eq("cli.missing_fred_rc", proc.returncode, 1)
    eq("cli.missing_fred_error", "error" in proc.stdout, True)

    # 正常路徑 rc=0
    good = os.path.join(tmp2, "fred.json")
    with open(good, "w") as fh:
        json.dump(fred(), fh)
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "fred_lane_gate.py"), "--date", DATE,
         "--fred", good, "--logs-dir", tmp2],
        capture_output=True, text=True)
    eq("cli.ok_rc", proc.returncode, 0)
    eq("cli.ok_shadow_only", json.loads(proc.stdout)["shadow_only"], True)

    # 沒有歷史 intel → prev_regime=None，不得炸
    eq("prev.no_logs", previous_regime_label(tmp2), (None, None))

    # 壞形狀歷史 intel（頂層 list、_phase0 是字串、label 非字串）不得讓 gate
    # traceback（rc 契約：rc=1 只在 fred cache 不可讀），也不得擋住更早的好檔
    for name, payload in [
        ("2026-08-01_sector_intel.json",
         {"_phase0": {"fred_snapshot": {"regime_label": "Soft Landing"}}}),
        ("2026-08-02_sector_intel.json", ["not", "an", "object"]),
        ("2026-08-03_sector_intel.json", {"_phase0": "boom"}),
        ("2026-08-04_sector_intel.json",
         {"_phase0": {"fred_snapshot": {"regime_label": {"not": "a str"}}}}),
    ]:
        with open(os.path.join(tmp2, name), "w") as fh:
            json.dump(payload, fh)
    eq("prev.bad_shapes_skipped_to_good",
       previous_regime_label(tmp2), ("Soft Landing", "2026-08-01_sector_intel.json"))
    # CLI 全程走一次：壞歷史檔在場時 rc 仍為 0（gate 不得被歷史檔拖死）
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "fred_lane_gate.py"), "--date", DATE,
         "--fred", good, "--logs-dir", tmp2],
        capture_output=True, text=True)
    eq("cli.bad_history_rc", proc.returncode, 0)
    eq("cli.bad_history_prev_found",
       json.loads(proc.stdout)["context"]["previous_regime_label"], "Soft Landing")

    # 非 ISO 日期要在 argparse 層擋掉（4.95.3）：`--date 8/3/2026` 會被塞進檔名，
    # --write 靜默寫出 fred_lane_gate_8/3/ 子目錄，--status 的 glob 永遠看不到
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "fred_lane_gate.py"),
         "--date", "8/3/2026", "--fred", good, "--cache-dir", tmp2, "--write"],
        capture_output=True, text=True)
    eq("cli.bad_date_rejected", proc.returncode != 0, True)
    eq("cli.bad_date_message", "YYYY-MM-DD" in proc.stderr, True)
    eq("cli.bad_date_no_subdir",
       os.path.isdir(os.path.join(tmp2, "fred_lane_gate_8")), False)
finally:
    shutil.rmtree(tmp2, ignore_errors=True)

# ── 10. 純函式性 ────────────────────────────────────────────────────────────
f = fred(adjustments=[ADJ_REAL_RATE, ADJ_CREDIT], avoid=["Utilities"])
eq("pure.deterministic",
   evaluate_triggers(copy.deepcopy(f), hot_sectors=["Technology"], prev_regime="X"),
   evaluate_triggers(copy.deepcopy(f), hot_sectors=["Technology"], prev_regime="X"))

# ──────────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} regression(s):")
    for f_ in FAILS:
        print("  -", f_)
    sys.exit(1)
print("✓ SE5 FRED lane gate fixtures pass")

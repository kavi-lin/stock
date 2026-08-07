#!/usr/bin/env python3
"""test_sector_score_calculator.py — SE1 shadow 落盤 + 覆蓋率回歸測試。

鎖住四件事：
  1. **Step 5 乘數偵測但不重算**（SE1 動手時被實測推翻的假設）：33 筆歷史樣本中 31 筆
     證明 LLM 是把 ×0.70 烙進 `score_components` 後才寫下的，calculator 再乘一次就是
     雙重計分、會把那 31 筆全打成 hard diff。含 2026-07-31 Energy 的真實回歸樣本。
  2. **cycle 條件的成立範圍**：fred_available=true 時 Step 6 已取代 Step 1/STEP C，
     條件不成立；非 Late/Recession 不觸發。
  3. **算不出 ≠ 算錯**：無法複算的板塊不計入 diff，改讓整場 sample_valid=false。
  4. **割接統計的分母紀律**：只數 sample_valid 的場次；累計 soft diff 上限與混版本會擋；
     歷史 audit 不得混進 live 分母。
  5. **shadow 不得影響主流程**：落盤丟例外時 `build_sector_intel.build()` 仍要跑完並
     回傳完整 intel，且警告要印出來（不得靜默吞掉）。

純 stdlib、零網路、不碰真實 cache（全部走 tmpdir）。
Run: python3 sector/scripts/test_sector_score_calculator.py   # rc=0 全過 / rc=1 fail
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from sector_score_calculator import (  # noqa: E402
    CALCULATOR_VERSION,
    SHADOW_SCHEMA,
    _round_half_up,
    audit_decision_files,
    build_shadow_report,
    collect_cutover_status,
    compute_deterministic_valuation_penalty,
    detect_step5_conditions,
    run_shadow_score_check,
    verify_session_dual_run,
    write_shadow_report,
)

FAILS = []


def eq(label, got, want):
    if got != want:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


def sector(name="Technology", *, components=(20, 20, 20, 20), penalty=0,
           composite=None, mult=None, flags=None, kind=None, uptrend=None):
    bm, th, nc, rs = components
    s = {
        "name": name,
        "score_components": {
            "breadth_momentum": bm, "theme_heat": th,
            "news_catalyst": nc, "rotation_signal": rs,
            "valuation_penalty": penalty,
        },
        "risk_flags": list(flags or []),
    }
    if composite is not None:
        s["composite_score"] = composite
    if mult is not None:
        s["step6_fred_multiplier"] = mult
    if kind is not None:
        s["cyclical_or_defensive"] = kind
    if uptrend is not None:
        s["uptrend_ratio"] = uptrend
    return s


FRED_ON = {"cycle_phase": "Late", "fred_available": True}
FRED_OFF = {"cycle_phase": "Late", "fred_available": False}
MID_CYCLE_OFF = {"cycle_phase": "Mid", "fred_available": False}

# ── 1. 基本對照 ───────────────────────────────────────────────────────────────
r = run_shadow_score_check(sector(composite=80, mult=1.0), None, FRED_ON)
eq("base.exact_match.diff", r["diff"], 0.0)
eq("base.exact_match.reproducible", r["reproducible"], True)
eq("base.base_score", r["base_score"], 80)

# soft diff（0.5 < d <= 1.0）: 80 × 1.0 = 80，LLM 寫 81 → diff 1.0
r = run_shadow_score_check(sector(composite=81, mult=1.0), None, FRED_ON)
eq("base.soft_diff", r["diff"], 1.0)
ok, msg = verify_session_dual_run([r])
eq("base.soft_diff.session_pass", ok, True)          # 單場 soft ≤ 2 仍 PASS
eq("base.soft_diff.counted", "Soft diff" in msg, True)

# hard diff（> 1.0）
r = run_shadow_score_check(sector(composite=90, mult=1.0), None, FRED_ON)
eq("base.hard_diff", r["diff"], 10.0)
ok, _ = verify_session_dual_run([r])
eq("base.hard_diff.session_fail", ok, False)

# ── 2. SE1 核心：Step 5 偵測「不套用」（重算 = 雙重計分）────────────────────
# 實測 33 筆歷史樣本：31 筆的 sum(components) × step6 == composite，證明 LLM 是把
# ×0.70 烙進分項後才寫下 score_components。calculator 再乘一次會把這 31 筆全打成
# hard diff —— 所以這裡鎖「偵測到、但分數不動」。
s = sector(composite=80, mult=1.0, flags=["binary_risk_within_48h"])
r = run_shadow_score_check(s, None, FRED_ON)
eq("step5.binary.detected",
   [m["name"] for m in r["step5_conditions"]], ["binary_risk_within_48h"])
eq("step5.binary.expected_mult",
   r["step5_conditions"][0]["expected_multiplier"], 0.7)
eq("step5.binary.NOT_applied_to_score", r["pre_step6_score"], 80)   # ← 雙重計分防線
eq("step5.binary.no_false_diff", r["diff"], 0.0)
eq("step5.binary.marked_unverified", r["unverified_steps"], ["binary_risk_within_48h"])
# 沒有旗標就不該偵測到
r = run_shadow_score_check(sector(composite=80, mult=1.0), None, FRED_ON)
eq("step5.binary.not_detected_without_flag", r["step5_conditions"], [])
eq("step5.binary.no_unverified", r["unverified_steps"], [])

# 真實回歸樣本（2026-07-31 Energy）：分項已含 ×0.70，64.3 × 1.035 = 66.5 → 67
energy = sector("Energy", components=(20.2, 3.9, 20.0, 20.2), composite=67,
                mult=1.035, kind="cyclical", flags=["binary_risk_within_48h"])
r = run_shadow_score_check(energy, None, {"cycle_phase": "Early", "fred_available": True})
eq("step5.regression.energy_0731_no_diff", r["diff"], 0.0)

# ── 3. Step 5 cycle 條件偵測 + 雙重計分防線 ──────────────────────────────────
r = run_shadow_score_check(sector(composite=80, kind="cyclical"), None, FRED_OFF)
eq("step5.cycle.cyclical_detected",
   [m["name"] for m in r["step5_conditions"]], ["cycle_late_cyclical"])
eq("step5.cycle.NOT_applied", r["pre_step6_score"], 80)
r = run_shadow_score_check(sector(composite=80, kind="defensive"), None, FRED_OFF)
eq("step5.cycle.defensive_detected",
   [m["name"] for m in r["step5_conditions"]], ["cycle_late_defensive"])
# fred 可用時 Step 6 取代 Step 1/STEP C → 條件本來就不成立
r = run_shadow_score_check(sector(composite=80, kind="cyclical", mult=1.0), None, FRED_ON)
eq("step5.cycle.not_detected_when_fred_available", r["step5_conditions"], [])
# 非 Late/Recession 不觸發
r = run_shadow_score_check(sector(composite=80, kind="cyclical"), None, MID_CYCLE_OFF)
eq("step5.cycle.not_detected_when_mid", r["step5_conditions"], [])
# 兩條可同時偵測到，分數仍不動
s = sector(composite=80, kind="cyclical", flags=["binary_risk_within_48h"])
r = run_shadow_score_check(s, None, FRED_OFF)
eq("step5.stacked.both_detected", len(r["step5_conditions"]), 2)
eq("step5.stacked.score_untouched", r["pre_step6_score"], 80)

# ── 3b. 捨入慣例：half-up，不可用 Python 內建 round()（銀行家捨入）──────────
# 42.5 這種邊界：round(42.5)==42 但 protocol 慣例是 43（473 筆歷史樣本中 3 個 .5
# 邊界，LLM 三次都進位）。用錯會造成整批 ±1 的系統性 soft diff。
r = run_shadow_score_check(sector(components=(10.5, 10.5, 10.5, 11.0), composite=43,
                                  mult=1.0), None, FRED_ON)
eq("round.half_up_42_5", r["calculated_post_score"], 43)
r = run_shadow_score_check(sector(components=(13.5, 13.5, 13.5, 14.0), composite=55,
                                  mult=1.0), None, FRED_ON)
eq("round.half_up_54_5", r["calculated_post_score"], 55)
# 非邊界不受影響
r = run_shadow_score_check(sector(components=(10.0, 10.0, 10.0, 10.4), composite=40,
                                  mult=1.0), None, FRED_ON)
eq("round.half_up_40_4_down", r["calculated_post_score"], 40)

# 3b-ii. 乘法後的浮點雜訊：50.0 × 1.15 == 57.49999999999999（真值恰 57.5），
#        裸 floor(v+0.5) 會給 57。_ROUND_EPS 負責把它拉回 58。
r = run_shadow_score_check(sector(components=(12.5, 12.5, 12.5, 12.5), composite=58,
                                  mult=1.15), None, FRED_ON)
eq("round.float_noise_boundary_up", r["calculated_post_score"], 58)

# 3b-iii. **不得雙重捨入**：舊版先 round(pre*mult, 2) 再 half-up ——
#         64.25 × 1.035 = 66.49875 → 2dp 銀行家捨入 66.5 → 67，但真 half-up 是 66。
r = run_shadow_score_check(sector(components=(16.0, 16.0, 16.0, 16.25), composite=66,
                                  mult=1.035), None, FRED_ON)
eq("round.no_double_rounding", r["calculated_post_score"], 66)

# 3b-iv. 有無 mult 不得產生兩種捨法（舊版只有 mult 路徑走 2dp 預捨入）
a = run_shadow_score_check(sector(components=(16.0, 16.0, 16.0, 16.25), composite=66,
                                  mult=1.0), None, FRED_ON)["calculated_post_score"]
b = run_shadow_score_check(sector(components=(16.0, 16.0, 16.0, 16.25), composite=66),
                           None, MID_CYCLE_OFF)["calculated_post_score"]
eq("round.mult_and_no_mult_agree", a, b)

# 3b-v. half-up 的負數語意是 away-from-zero（目前 clamp 擋在前面，這裡直接鎖 helper）
eq("round.negative_half_away_from_zero", _round_half_up(-2.5), -3)
eq("round.positive_half_up", _round_half_up(2.5), 3)

# ── 4. context 省略 = 舊行為（既有呼叫端不會壞）────────────────────────────
r = run_shadow_score_check(sector(composite=80, kind="cyclical"), None)
eq("compat.no_context_no_cycle_condition", r["step5_conditions"], [])

# ── 5. Valuation penalty（Step 5b）────────────────────────────────────────────
eq("penalty.overbought", compute_deterministic_valuation_penalty(2.5, 0.8), -10)
eq("penalty.oversold", compute_deterministic_valuation_penalty(-1.5, 0.2), 5)
eq("penalty.neutral", compute_deterministic_valuation_penalty(0.0, 0.5), 0)
eq("penalty.none_input", compute_deterministic_valuation_penalty(None, 0.5), 0)
eq("penalty.bool_not_number", compute_deterministic_valuation_penalty(True, 0.8), 0)

# drift：cache 說該 −10，LLM 寫 0
val_cache = {"Technology": {"pe_zscore_1y": 2.5}}
s = sector(composite=80, mult=1.0, penalty=0, uptrend=0.8)
r = run_shadow_score_check(s, val_cache, FRED_ON)
eq("penalty.drift_detected", r["penalty_drift"], True)
ok, _ = verify_session_dual_run([r])
eq("penalty.drift_fails_session", ok, False)
# 一致 → 無 drift；80 − 10 = 70
s = sector(composite=70, mult=1.0, penalty=-10, uptrend=0.8)
r = run_shadow_score_check(s, val_cache, FRED_ON)
eq("penalty.no_drift", r["penalty_drift"], False)
eq("penalty.applied_to_base", r["pre_step6_score"], 70)

# penalty 加在分項和之上（Step 5 乘數已在分項內，不重複套）：80 − 10 = 70
s = sector(composite=70, mult=1.0, penalty=-10, uptrend=0.8,
           flags=["binary_risk_within_48h"])
r = run_shadow_score_check(s, val_cache, FRED_ON)
eq("order.penalty_on_component_sum", r["diff"], 0.0)

# ── 6. 算不出 ≠ 算錯 ─────────────────────────────────────────────────────────
s = sector(composite=80)                      # fred 可用卻沒記 step6 multiplier
r = run_shadow_score_check(s, None, FRED_ON)
eq("unrepro.missing_mult.flagged", r["reproducible"], False)
eq("unrepro.missing_mult.reason",
   r["unreproducible_reasons"], ["missing_step6_multiplier_with_fred_available"])
ok, msg = verify_session_dual_run([r])
eq("unrepro.not_counted_as_diff", ok, True)     # 不得因「算不出」判 FAIL
eq("unrepro.listed_as_skipped", "SKIPPED" in msg, True)

no_comp = {"name": "Energy", "composite_score": 50}
r = run_shadow_score_check(no_comp, None, FRED_ON)
eq("unrepro.missing_components", r["reproducible"], False)
eq("unrepro.missing_components.no_fake_diff", r["diff"], 0.0)

# 6b. **單一**分項缺失/null 也算「算不出」——舊版 `_num(...) or 0` 會靜默當 0，
#     於是 theme_heat: null 產生 diff=20 的**假 hard diff** 且 reproducible=True，
#     一筆就永久擋死 SE2（累計上限 0 hard），而且擋的理由是假的。
for bad_val, tag in ((None, "null"), ("20", "str"), (float("nan"), "nan")):
    s_bad = sector(composite=80, mult=1.0)
    s_bad["score_components"]["theme_heat"] = bad_val
    r = run_shadow_score_check(s_bad, None, FRED_ON)
    eq(f"unrepro.component_{tag}.flagged", r["reproducible"], False)
    eq(f"unrepro.component_{tag}.reason",
       r["unreproducible_reasons"], ["missing_score_component:theme_heat"])
    eq(f"unrepro.component_{tag}.no_fake_diff", r["diff"], 0.0)

s_bad = sector(composite=80, mult=1.0)
del s_bad["score_components"]["valuation_penalty"]
r = run_shadow_score_check(s_bad, None, FRED_ON)
eq("unrepro.component_missing_key.flagged", r["reproducible"], False)
ok, msg = verify_session_dual_run([r])
eq("unrepro.component.not_counted_as_diff", ok, True)

# 分項為 0 是合法值，不得被當成缺失（`or 0` 那版無法分辨這兩者）
r = run_shadow_score_check(sector(components=(0, 0, 0, 0), composite=0, mult=1.0),
                           None, FRED_ON)
eq("unrepro.zero_components_are_valid", r["reproducible"], True)
eq("unrepro.zero_components_score", r["calculated_post_score"], 0)

# fred 不可用時缺 multiplier 是正常的，不該標成無法複算
r = run_shadow_score_check(sector(composite=80), None, MID_CYCLE_OFF)
eq("unrepro.fred_off_no_mult_ok", r["reproducible"], True)

# ── 7. 報告落盤 + sample_valid ───────────────────────────────────────────────
good = [run_shadow_score_check(sector(n, composite=80, mult=1.0), None, FRED_ON)
        for n in ("Technology", "Energy")]
rep = build_shadow_report(good, scan_date="2026-08-03", context=FRED_ON)
eq("report.schema", rep["schema"], SHADOW_SCHEMA)
eq("report.version", rep["calculator_version"], CALCULATOR_VERSION)
eq("report.sample_valid", rep["session"]["sample_valid"], True)
eq("report.status", rep["session"]["status"], "PASS")
eq("report.coverage_declared", "modeled" in rep["coverage"], True)
eq("report.context_carried", rep["context"]["fred_available"], True)

mixed = good + [run_shadow_score_check(sector("Utilities", composite=80), None, FRED_ON)]
rep_bad = build_shadow_report(mixed, scan_date="2026-08-04", context=FRED_ON)
eq("report.sample_invalid_when_unreproducible", rep_bad["session"]["sample_valid"], False)
eq("report.unreproducible_listed",
   [u["sector"] for u in rep_bad["session"]["unreproducible"]], ["Utilities"])
eq("report.invalid_reason_unreproducible",
   rep_bad["session"]["invalid_reasons"], ["unreproducible_sectors"])

# 7b. 回填（重跑過去日期）不得計入 live 割接分母 —— 那種場次的 _phase0 讀的是
#     **今天**的 cache，證據等級等同 --audit-decisions 的歷史重放。
rep_bf = build_shadow_report(good, scan_date="2026-05-18", context=FRED_ON, backfill=True)
eq("report.backfill_flagged", rep_bf["backfill"], True)
eq("report.backfill_not_valid_sample", rep_bf["session"]["sample_valid"], False)
eq("report.backfill_reason", rep_bf["session"]["invalid_reasons"], ["backfill_rebuild"])
eq("report.backfill_status_still_computed", rep_bf["session"]["status"], "PASS")
eq("report.live_run_not_backfill", rep["backfill"], False)

# 7c. 零板塊不是「全部相符」，是沒有樣本 —— 不擋掉會讓 N=5 用空場次湊滿
rep_empty = build_shadow_report([], scan_date="2026-08-05", context=FRED_ON)
eq("report.empty_not_valid_sample", rep_empty["session"]["sample_valid"], False)
eq("report.empty_reason", rep_empty["session"]["invalid_reasons"], ["empty_report"])

# ── 8. 割接統計（讀出端）─────────────────────────────────────────────────────
tmp = tempfile.mkdtemp(prefix="se1_shadow_")
try:
    def emit(date, *, hard=0, soft=0, drift=0, valid=True, version=CALCULATOR_VERSION):
        rp = {
            "schema": SHADOW_SCHEMA, "calculator_version": version,
            "scan_date": date, "generated_at": "x",
            "coverage": {}, "context": {},
            "session": {"sample_valid": valid, "unreproducible": []
                        if valid else [{"sector": "X", "reasons": ["r"]}],
                        "sector_count": 11, "hard_diffs": hard, "soft_diffs": soft,
                        "penalty_drifts": drift,
                        "status": "PASS" if not (hard or soft > 2 or drift) else "FAIL"},
            "sectors": [],
        }
        write_shadow_report(rp, cache_dir=tmp)

    # 4 場有效 → 未達 N=5
    for i in range(4):
        emit(f"2026-08-0{i + 1}")
    st = collect_cutover_status(tmp)
    eq("cutover.four_sessions_not_eligible", st["cutover_eligible"], False)
    eq("cutover.valid_count", st["valid_sessions"], 4)

    # 第 5 場但 sample_valid=false → 不計入分母
    emit("2026-08-05", valid=False)
    st = collect_cutover_status(tmp)
    eq("cutover.invalid_excluded_from_denominator", st["valid_sessions"], 4)
    eq("cutover.invalid_listed", len(st["invalid_sessions"]), 1)
    eq("cutover.still_not_eligible", st["cutover_eligible"], False)

    # 補到 5 場有效 → 達標
    emit("2026-08-06")
    st = collect_cutover_status(tmp)
    eq("cutover.five_valid_eligible", st["cutover_eligible"], True)
    eq("cutover.no_unmet", st["unmet"], [])

    # 累計 soft diff 超過上限（跨場累計語意，比單場 ≤2 嚴）→ 擋
    emit("2026-08-07", soft=3)
    st = collect_cutover_status(tmp)
    eq("cutover.cumulative_soft_blocks", st["cutover_eligible"], False)
    eq("cutover.cumulative_soft_counted", st["cumulative"]["soft_diffs"], 3)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# 混版本要擋：calculator 改過覆蓋率後，舊樣本的 diff 不是同一個基準
tmp2 = tempfile.mkdtemp(prefix="se1_shadow_ver_")
try:
    for i in range(5):
        v = CALCULATOR_VERSION if i < 3 else "sector_score_calculator.py v1.0 (old)"
        write_shadow_report({
            "schema": SHADOW_SCHEMA, "calculator_version": v,
            "scan_date": f"2026-07-0{i + 1}", "generated_at": "x",
            "coverage": {}, "context": {},
            "session": {"sample_valid": True, "unreproducible": [], "sector_count": 11,
                        "hard_diffs": 0, "soft_diffs": 0, "penalty_drifts": 0,
                        "status": "PASS"},
            "sectors": [],
        }, cache_dir=tmp2)
    st = collect_cutover_status(tmp2)
    eq("cutover.mixed_versions_block", st["cutover_eligible"], False)
    eq("cutover.mixed_versions_reason",
       any("mixed calculator versions" in u for u in st["unmet"]), True)
finally:
    shutil.rmtree(tmp2, ignore_errors=True)

# 壞檔不得靜默當成有效樣本
tmp3 = tempfile.mkdtemp(prefix="se1_shadow_bad_")
try:
    with open(os.path.join(tmp3, "shadow_score_2026-07-09.json"), "w") as fh:
        fh.write("{not json")
    with open(os.path.join(tmp3, "shadow_score_2026-07-10.json"), "w") as fh:
        json.dump({"schema": "something_else"}, fh)
    st = collect_cutover_status(tmp3)
    eq("cutover.malformed_not_counted", st["valid_sessions"], 0)
    eq("cutover.malformed_surfaced", len(st["malformed_files"]), 2)
finally:
    shutil.rmtree(tmp3, ignore_errors=True)

# 8a-ii. 讀出端的兩個繞道：計數欄位是 null、版號缺失
tmp3b = tempfile.mkdtemp(prefix="se1_shadow_edge_")
try:
    def emit_raw(date, session, *, version=CALCULATOR_VERSION):
        payload = {"schema": SHADOW_SCHEMA, "scan_date": date, "generated_at": "x",
                   "coverage": {}, "context": {}, "session": session, "sectors": []}
        if version is not None:
            payload["calculator_version"] = version
        write_shadow_report(payload, cache_dir=tmp3b)

    base = {"sample_valid": True, "unreproducible": [], "sector_count": 11,
            "hard_diffs": 0, "soft_diffs": 0, "penalty_drifts": 0, "status": "PASS"}
    # hard_diffs=null：`.get(k, 0)` 只在 key 不存在時給預設，null 會原樣回 None
    # 並在 sum() 時 TypeError 掛掉整份報告
    emit_raw("2026-07-20", {**base, "hard_diffs": None})
    st = collect_cutover_status(tmp3b)
    eq("cutover.null_counter_is_malformed", st["valid_sessions"], 0)
    eq("cutover.null_counter_surfaced", len(st["malformed_files"]), 1)

    # 版號缺失：舊版用 falsy 過濾 → 既繞過混版本檢查又照算有效場次
    for i in range(4):
        emit_raw(f"2026-07-2{i + 1}", dict(base))
    emit_raw("2026-07-25", dict(base), version=None)
    st = collect_cutover_status(tmp3b)
    eq("cutover.versionless_counted", st["valid_sessions"], 5)
    eq("cutover.versionless_triggers_mixed_check",
       any("mixed calculator versions" in u for u in st["unmet"]), True)
    eq("cutover.versionless_blocks_cutover", st["cutover_eligible"], False)
finally:
    shutil.rmtree(tmp3b, ignore_errors=True)

# 8a-iii. 讀出端再往下一層（4.95.2）：.prev 備份檔、非字串版號、sample_valid 髒值
tmp3c = tempfile.mkdtemp(prefix="se1_shadow_edge2_")
try:
    def emit3(name, payload):
        with open(os.path.join(tmp3c, name), "w") as fh:
            json.dump(payload, fh)

    base_rep = {"schema": SHADOW_SCHEMA, "calculator_version": CALCULATOR_VERSION,
                "generated_at": "x", "coverage": {}, "context": {}, "sectors": [],
                "session": {"sample_valid": True, "unreproducible": [],
                            "sector_count": 11, "hard_diffs": 0, "soft_diffs": 0,
                            "penalty_drifts": 0, "status": "PASS"}}
    for i in range(5):
        emit3(f"shadow_score_2026-06-0{i + 1}.json",
              {**base_rep, "scan_date": f"2026-06-0{i + 1}"})
    st = collect_cutover_status(tmp3c)
    eq("cutover.edge2_baseline_valid", st["valid_sessions"], 5)
    eq("cutover.edge2_baseline_eligible", st["cutover_eligible"], True)

    # .prev 手動備份檔匹配得到 glob（shadow_score_*.json）→ 舊版把同一場數兩次，
    # 灌水割接分母。audit 端（audit_decision_files）早就跳過，讀出端要一致。
    emit3("shadow_score_2026-06-01.prev.json", {**base_rep, "scan_date": "2026-06-01"})
    st = collect_cutover_status(tmp3c)
    eq("cutover.prev_backup_skipped", st["valid_sessions"], 5)
    eq("cutover.prev_backup_not_malformed", st["malformed_files"], [])

    # 非字串版號：舊版 `or UNKNOWN` 放行 float → `sorted()` 混型 TypeError，
    # --status 整份掛掉。改判 <unknown> 自成一格 → 觸發混版本檢查。
    emit3("shadow_score_2026-06-06.json",
          {**base_rep, "scan_date": "2026-06-06", "calculator_version": 4.95})
    st = collect_cutover_status(tmp3c)          # 不得 raise
    eq("cutover.numeric_version_counted", st["valid_sessions"], 6)
    eq("cutover.numeric_version_triggers_mixed",
       any("mixed calculator versions" in u for u in st["unmet"]), True)
    os.unlink(os.path.join(tmp3c, "shadow_score_2026-06-06.json"))

    # sample_valid 髒值：字串 "false" 是 truthy，舊版照算進割接分母
    emit3("shadow_score_2026-06-07.json",
          {**base_rep, "scan_date": "2026-06-07",
           "session": {**base_rep["session"], "sample_valid": "false"}})
    st = collect_cutover_status(tmp3c)
    eq("cutover.string_sample_valid_excluded", st["valid_sessions"], 5)
    eq("cutover.string_sample_valid_listed", len(st["invalid_sessions"]), 1)
    os.unlink(os.path.join(tmp3c, "shadow_score_2026-06-07.json"))

    # 負數計數器（4.95.3）：割接判準是跨場 sum，一筆 hard_diffs=-2 能把別場的真
    # hard diff 從累計裡抵銷掉 —— 判 malformed，不進分母也不進 sum
    emit3("shadow_score_2026-06-08.json",
          {**base_rep, "scan_date": "2026-06-08",
           "session": {**base_rep["session"], "hard_diffs": -2}})
    st = collect_cutover_status(tmp3c)
    eq("cutover.negative_counter_is_malformed", st["valid_sessions"], 5)
    eq("cutover.negative_counter_not_in_sum", st["cumulative"]["hard_diffs"], 0)
    eq("cutover.negative_counter_surfaced", len(st["malformed_files"]), 1)
finally:
    shutil.rmtree(tmp3c, ignore_errors=True)

# ── 8b. 歷史 audit 與 live shadow 分母嚴格分離 ──────────────────────────────
tmp4 = tempfile.mkdtemp(prefix="se1_audit_")
try:
    # 一場乾淨、一場帶 hard diff 的 decision 檔
    json.dump({"verdict_date": "2026-06-01", "cycle_phase": "Mid", "sectors": [
        {"name": "Technology", "composite_score": 80, "step6_fred_multiplier": 1.0,
         "score_components": {"breadth_momentum": 20, "theme_heat": 20,
                              "news_catalyst": 20, "rotation_signal": 20,
                              "valuation_penalty": 0}}]},
        open(os.path.join(tmp4, "sector_decision_2026-06-01.json"), "w"))
    json.dump({"verdict_date": "2026-06-02", "cycle_phase": "Mid", "sectors": [
        {"name": "Energy", "composite_score": 95, "step6_fred_multiplier": 1.0,
         "score_components": {"breadth_momentum": 20, "theme_heat": 20,
                              "news_catalyst": 20, "rotation_signal": 20,
                              "valuation_penalty": 0}}]},
        open(os.path.join(tmp4, "sector_decision_2026-06-02.json"), "w"))
    # 手動備份檔不得被當成正式場次
    json.dump({"verdict_date": "2026-06-02", "cycle_phase": "Mid", "sectors": []},
              open(os.path.join(tmp4, "sector_decision_2026-06-02.prev-0101.json"), "w"))

    a = audit_decision_files(tmp4)
    eq("audit.sessions_counted", a["sessions_audited"], 2)      # .prev 被排除
    eq("audit.clean_count", a["sessions_clean"], 1)
    eq("audit.hard_diff_found", a["total_hard_diffs"], 1)
    eq("audit.offender_named",
       [o["sector"] for s in a["sessions"] for o in s.get("offenders", [])], ["Energy"])
    # **不得**寫出任何 shadow 樣本 → --status 的分母仍是 0
    eq("audit.writes_no_shadow_sample", collect_cutover_status(tmp4)["valid_sessions"], 0)
finally:
    shutil.rmtree(tmp4, ignore_errors=True)

# ── 9. 純函式性（同輸入同輸出，shadow 樣本可重放）────────────────────────────
s = sector(composite=80, mult=1.0, flags=["binary_risk_within_48h"])
eq("pure.deterministic",
   run_shadow_score_check(dict(s), None, dict(FRED_ON)),
   run_shadow_score_check(dict(s), None, dict(FRED_ON)))
eq("pure.step5_deterministic",
   detect_step5_conditions(dict(s), dict(FRED_OFF)),
   detect_step5_conditions(dict(s), dict(FRED_OFF)))

# ── 10. shadow 落盤失敗不得中斷正式 build ────────────────────────────────────
# shadow 是探索層，正式 intel 才是主流程產出。裸呼叫 write_shadow_report() 會讓
# cache 唯讀／磁碟滿／權限不足一路拋到 main()，整場產業掃描因為一個對照檔寫不出來
# 而沒有 intel —— 用探索層的失敗換掉決策層的產出，方向剛好相反。
import build_sector_intel as bsi  # noqa: E402

BUILD_DATE = "2026-08-03"
BUILD_SECTOR = "Technology"


def _write_build_fixture(cache: Path) -> Path:
    """build() 要求的三份 cache + 一份 decision，全部走 tmpdir。"""
    for label, payload in (
        ("sector_valuation", {"sectors": {BUILD_SECTOR: {"pe_zscore_1y": 0.0}}}),
        ("sector_earnings_pulse", {"sectors": {BUILD_SECTOR: {"pulse": "flat"}}}),
        ("sector_smart_money", {"sectors": {BUILD_SECTOR: {"flow": "neutral"}}}),
    ):
        (cache / f"{label}_{BUILD_DATE}.json").write_text(
            json.dumps(payload), encoding="utf-8")

    decision = {
        "verdict_date": BUILD_DATE, "market_regime": "Neutral", "cycle_phase": "Mid",
        "exposure_ceiling": 70, "synthesized_exposure": 60,
        "phase4_fanout_mode": "full", "regime_stance": "neutral",
        "today_verdict": {"headline": "test"},
        "political_overlay": {"fear_greed_index": 50},
        "top_catalysts": [{"headline": f"c{i}"} for i in range(5)],
        "summary": {"hot_sectors": [], "cold_sectors": []},
        "political_risk_summary": "test", "actionable_themes": [],
        "session_notes": "test",
        "sectors": [{
            "name": BUILD_SECTOR, "verdict": "WARM", "composite_score": 80,
            "uptrend_ratio": 0.5, "rotation_signal": "neutral",
            "cyclical_or_defensive": "cyclical", "step6_fred_multiplier": 1.0,
            "score_components": {"breadth_momentum": 20, "theme_heat": 20,
                                 "news_catalyst": 20, "rotation_signal": 20,
                                 "valuation_penalty": 0},
            "key_reasons": ["test"],
        }],
    }
    dec_path = cache / f"sector_decision_{BUILD_DATE}.json"
    dec_path.write_text(json.dumps(decision), encoding="utf-8")
    return dec_path


def _run_build(cache: Path, dec_path: Path, writer):
    """在 tmpdir 沙箱裡跑 build()，回傳 (結果, SystemExit 與否, stderr)。

    `build_phase0` 一併換掉：它會 subprocess 去讀**真實** FRED/breadth cache，
    那是網路/環境相依，與本檔「純 stdlib、零網路」的紀律衝突。
    `write_shadow_report` 也一定要換掉 —— 真實實作會寫進 sector/cache，測試不得
    在正式割接證據池裡留下假樣本。
    """
    saved = (bsi.CACHE_DIR, bsi.build_phase0, bsi.write_shadow_report)
    bsi.CACHE_DIR = cache
    bsi.build_phase0 = lambda d: {"phase": 0, "scan_date": d, "cycle_phase": None,
                                  "fred_available": True, "warning_flags": []}
    bsi.write_shadow_report = writer
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            return bsi.build(BUILD_DATE, dec_path), False, err.getvalue()
    except SystemExit:
        return None, True, err.getvalue()
    finally:
        bsi.CACHE_DIR, bsi.build_phase0, bsi.write_shadow_report = saved


tmp5 = Path(tempfile.mkdtemp(prefix="se1_build_"))
try:
    dec = _write_build_fixture(tmp5)

    # 對照組：落盤成功時 build 正常回傳（確認 fixture 本身是會過的）
    wrote = []
    out, exited, err = _run_build(
        tmp5, dec, lambda rep, **kw: wrote.append(rep) or "/fake/shadow.json")
    eq("build.happy_path_no_exit", exited, False)
    eq("build.happy_path_sectors", len(out["sectors"]) if out else None, 1)
    eq("build.happy_path_wrote_shadow", len(wrote), 1)
    eq("build.happy_path_logs_path", "/fake/shadow.json" in err, True)

    # 主案：落盤丟 OSError（唯讀 FS／磁碟滿／權限）→ build 必須跑完
    def _boom_os(rep, **kw):
        raise OSError(28, "No space left on device")

    out, exited, err = _run_build(tmp5, dec, _boom_os)
    eq("build.write_oserror_no_exit", exited, False)
    eq("build.write_oserror_still_returns_intel", out is not None, True)
    eq("build.write_oserror_sectors_intact", len(out["sectors"]) if out else None, 1)
    eq("build.write_oserror_verdict_date", out["verdict_date"] if out else None, BUILD_DATE)
    # 不得靜默吞掉：警告要有，且要帶例外內容
    eq("build.write_oserror_warns", "落盤失敗" in err, True)
    eq("build.write_oserror_warn_has_detail", "No space left on device" in err, True)
    # 落盤失敗時不得再印出「shadow report → <path>」那行（shadow_path 未定義）
    eq("build.write_oserror_no_success_log", "shadow report →" not in err, True)

    # 非 IO 例外（例：序列化失敗）同樣不得中斷 —— 判準是「shadow 不影響主流程」，
    # 不是「哪幾種例外該原諒」。
    def _boom_type(rep, **kw):
        raise TypeError("Object of type set is not JSON serializable")

    out, exited, err = _run_build(tmp5, dec, _boom_type)
    eq("build.write_typeerror_no_exit", exited, False)
    eq("build.write_typeerror_still_returns_intel", out is not None, True)
    eq("build.write_typeerror_warns", "TypeError" in err, True)
finally:
    shutil.rmtree(tmp5, ignore_errors=True)

# ── 10b. 部分缺欄的板塊必須整場退出割接分母（端到端串一次）──────────────────
# 分項缺一格 → reproducible=false → sample_valid=false → --status 不計入分母。
# 這條鏈只要斷任何一節，假 hard diff 就會混進 N=5 的證據池。
partial = sector("Utilities", composite=80, mult=1.0)
partial["score_components"]["rotation_signal"] = "N/A"     # 非數值字串
r_partial = run_shadow_score_check(partial, None, FRED_ON)
eq("denom.partial_unreproducible", r_partial["reproducible"], False)
eq("denom.partial_no_diff", r_partial["diff"], 0.0)

tmp6 = tempfile.mkdtemp(prefix="se1_denom_")
try:
    rep_partial = build_shadow_report([r_partial], scan_date="2026-08-08",
                                      context=FRED_ON)
    eq("denom.partial_session_invalid", rep_partial["session"]["sample_valid"], False)
    eq("denom.partial_invalid_reason",
       rep_partial["session"]["invalid_reasons"], ["unreproducible_sectors"])
    write_shadow_report(rep_partial, cache_dir=tmp6)
    st = collect_cutover_status(tmp6)
    eq("denom.partial_excluded_from_denominator", st["valid_sessions"], 0)
    eq("denom.partial_listed_as_invalid", len(st["invalid_sessions"]), 1)
    eq("denom.partial_hard_diffs_zero", st["cumulative"]["hard_diffs"], 0)
finally:
    shutil.rmtree(tmp6, ignore_errors=True)

# ──────────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} regression(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ SE1 sector score shadow calculator fixtures pass")

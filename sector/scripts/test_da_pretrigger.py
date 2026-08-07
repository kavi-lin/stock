#!/usr/bin/env python3
"""test_da_pretrigger.py — SE3 R4–R7 預判回歸測試。

鎖住四件事：
  1. 四條規則各自獨立命中 + 各自的 sample-size / 方向性 gate（R5 institutional n≥3、
     R6 pt_sample≥3、R7 三窗口必須反向）。
  2. **「資料缺席」與「沒觸發」嚴格分離**：FRED 不可用時 R4 是 `available=false`，
     prompt_block 必須明說「未能判定 ≠ 未觸發」。把未知講成安全是這支 script 最危險
     的失敗模式 —— DA 會少發該發的 challenge，而且全鏈路無人察覺。
  3. **HARD cache 缺席一律 rc=1**，不得回「沒有觸發」。
  4. R5 的 consensus 一致豁免要被記錄成 exempt（有判過），不是靜默消失。

純 stdlib、零網路、不碰真實 cache（全部走 tmpdir）。
Run: python3 sector/scripts/test_da_pretrigger.py   # rc=0 全過 / rc=1 fail
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from da_pretrigger import (  # noqa: E402
    NO_TRIGGER_TEXT,
    PretriggerInputError,
    build_prompt_block,
    eval_r4,
    eval_r5,
    eval_r6,
    eval_r7,
    run,
)

FAILS = []
DATE = "2026-08-03"
FRED_GENERATED_AT = "2026-08-03T00:02:09+00:00"


def eq(label, got, want):
    if got != want:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


def hits(rule):
    return [h["sector"] for h in rule["sectors"]]


QUIET_FRED = {
    "regime_label": "Soft Landing", "regime_confidence": 0.7,
    "yield_curve_value": 0.8, "yield_curve_inverted": False,
    "credit_stress_elevated": False, "financial_stress_above_avg": False,
    "real_rate_preferred": 1.2,
    "sector_rotation_favor": ["Technology"], "sector_rotation_avoid": [],
}
HOT = ["Technology", "Energy"]

# ── R4 ───────────────────────────────────────────────────────────────────────
eq("r4.quiet", eval_r4(HOT, dict(QUIET_FRED), None)["fired"], False)

for field, val, label in [("credit_stress_elevated", True, "credit"),
                          ("yield_curve_inverted", True, "curve"),
                          ("financial_stress_above_avg", True, "finstress")]:
    f = dict(QUIET_FRED); f[field] = val
    r = eval_r4(HOT, f, None)
    eq(f"r4.{label}.fired", r["fired"], True)
    eq(f"r4.{label}.all_hot", hits(r), HOT)          # session 層條件 → 全部 HOT 命中

f = dict(QUIET_FRED); f["real_rate_preferred"] = 2.41
r = eval_r4(HOT, f, None)
eq("r4.real_rate.fired", r["fired"], True)
eq("r4.real_rate.cite_has_number",
   "2.41" in r["sectors"][0]["evidence"][0]["cite"], True)
# 邊界：恰好 2.0 不觸發（規則是 > 不是 >=）
f = dict(QUIET_FRED); f["real_rate_preferred"] = 2.0
eq("r4.real_rate.boundary_exclusive", eval_r4(HOT, f, None)["fired"], False)

f = dict(QUIET_FRED); f["regime_label"] = "Stagflation"
eq("r4.adverse_regime", eval_r4(HOT, f, None)["fired"], True)
f = dict(QUIET_FRED); f["regime_label"] = "Goldilocks"
eq("r4.benign_regime_quiet", eval_r4(HOT, f, None)["fired"], False)

# per-sector：只有在 avoid 名單裡的那個命中
f = dict(QUIET_FRED); f["sector_rotation_avoid"] = ["Energy"]
r = eval_r4(HOT, f, None)
eq("r4.avoid_per_sector", hits(r), ["Energy"])

# 優先序：credit_stress 必須排在 real_rate 前面（DA 引主證據時照這個順序）
f = dict(QUIET_FRED); f["credit_stress_elevated"] = True; f["real_rate_preferred"] = 2.5
r = eval_r4(HOT, f, None)
eq("r4.priority_order",
   [e["field"] for e in r["sectors"][0]["evidence"]],
   ["credit_stress_elevated", "real_rate_preferred"])

# **資料缺席 ≠ 沒觸發**
r = eval_r4(HOT, None, "fred cache missing: /x")
eq("r4.unavailable.not_fired", r["fired"], False)
eq("r4.unavailable.flagged", r["available"], False)
eq("r4.unavailable.reason_kept", r["unavailable_reason"], "fred cache missing: /x")

# ── R5 ───────────────────────────────────────────────────────────────────────
SM_QUIET = {"Technology": {"insider_acquired_disposed_ratio_q": 1.2,
                           "senate_net_buy_30d": 0,
                           "institutional_holders_qoq_delta": 5,
                           "institutional_ownership_pct_delta": 0.1,
                           "institutional_sample_size": 10}}
r = eval_r5(["Technology"], SM_QUIET)
eq("r5.quiet.not_fired", r["fired"], False)
eq("r5.quiet.recorded_exempt", len(r["exempt"]), 1)   # 判過且豁免，不是靜默

sm = {"Technology": dict(SM_QUIET["Technology"],
                         insider_acquired_disposed_ratio_q=0.462)}
r = eval_r5(["Technology"], sm)
eq("r5.insider.fired", r["fired"], True)
eq("r5.insider.cite", "0.462" in r["sectors"][0]["evidence"][0]["cite"], True)

sm = {"Technology": dict(SM_QUIET["Technology"], senate_net_buy_30d=-3)}
eq("r5.senate.fired", eval_r5(["Technology"], sm)["fired"], True)

# institutional 三條件同時成立才算，且 n>=3
sm = {"Technology": dict(SM_QUIET["Technology"],
                         institutional_holders_qoq_delta=-12,
                         institutional_ownership_pct_delta=-0.45,
                         institutional_sample_size=5)}
eq("r5.institutional.fired", eval_r5(["Technology"], sm)["fired"], True)
sm = {"Technology": dict(SM_QUIET["Technology"],
                         institutional_holders_qoq_delta=-12,
                         institutional_ownership_pct_delta=-0.45,
                         institutional_sample_size=2)}
eq("r5.institutional.sample_gate", eval_r5(["Technology"], sm)["fired"], False)
# 只有一邊為負 → 不觸發
sm = {"Technology": dict(SM_QUIET["Technology"],
                         institutional_holders_qoq_delta=-12,
                         institutional_ownership_pct_delta=0.3,
                         institutional_sample_size=9)}
eq("r5.institutional.needs_both", eval_r5(["Technology"], sm)["fired"], False)
# null 欄位（真實 cache 常見）不得被當成 0 而誤觸發
sm = {"Technology": {"insider_acquired_disposed_ratio_q": None,
                     "senate_net_buy_30d": None,
                     "institutional_holders_qoq_delta": None,
                     "institutional_ownership_pct_delta": None,
                     "institutional_sample_size": 0}}
eq("r5.nulls_do_not_fire", eval_r5(["Technology"], sm)["fired"], False)

# ── R6 ───────────────────────────────────────────────────────────────────────
eq("r6.fired", eval_r6(["Technology"], {"Technology": {
    "analyst_pt_upside_median_pct": 0.018, "pt_sample_size": 5}})["fired"], True)
eq("r6.sample_gate", eval_r6(["Technology"], {"Technology": {
    "analyst_pt_upside_median_pct": 0.018, "pt_sample_size": 2}})["fired"], False)
eq("r6.above_threshold", eval_r6(["Technology"], {"Technology": {
    "analyst_pt_upside_median_pct": 0.09, "pt_sample_size": 8}})["fired"], False)
eq("r6.null_upside", eval_r6(["Technology"], {"Technology": {
    "analyst_pt_upside_median_pct": None, "pt_sample_size": 0}})["fired"], False)

# ── R7 ───────────────────────────────────────────────────────────────────────
r = eval_r7(["Technology"], {"Technology": {
    "rs_vs_spy_3m": 0.062, "rs_vs_spy_20d": -0.030, "rs_vs_spy_5d": -0.012}})
eq("r7.fired", r["fired"], True)
eq("r7.cite_three_windows",
   all(x in r["sectors"][0]["evidence"][0]["cite"] for x in ("3M", "20d", "5d")), True)
# 三窗口同向 → 不挑
eq("r7.aligned_not_fired", eval_r7(["Technology"], {"Technology": {
    "rs_vs_spy_3m": 0.062, "rs_vs_spy_20d": 0.02, "rs_vs_spy_5d": 0.01}})["fired"], False)
# 3M 未達門檻
eq("r7.weak_3m", eval_r7(["Technology"], {"Technology": {
    "rs_vs_spy_3m": 0.01, "rs_vs_spy_20d": -0.03, "rs_vs_spy_5d": -0.01}})["fired"], False)
eq("r7.missing_window", eval_r7(["Technology"], {"Technology": {
    "rs_vs_spy_3m": 0.062, "rs_vs_spy_20d": None, "rs_vs_spy_5d": -0.01}})["fired"], False)

# per-sector 缺席（cache 在、但某個 HOT sector 不在它的 key 裡）：缺席要登記，
# 且不得混進 exempt（exempt 是「判過且乾淨」的宣稱，缺席是「沒判過」）
r = eval_r5(HOT, SM_QUIET)                       # SM_QUIET 只收錄 Technology
eq("r5.uncovered_listed", r["uncovered"], ["Energy"])
eq("r5.uncovered_not_counted_as_exempt",
   [e["sector"] for e in r["exempt"]], ["Technology"])
# 全覆蓋時不得留下假警語（警語太常出現就沒人看了）
eq("r5.no_false_uncovered", eval_r5(["Technology"], SM_QUIET)["uncovered"], [])

# 值層覆蓋（4.95.2）：key 在、值判不了 —— key 層擋掉後同一類 bug 在值層復發。
# `{"Utilities": null}` 或訊號欄位全 null 的板塊是「沒資料」，不是「查過了、乾淨」
eq("cover2.null_entry",
   eval_r5(["Technology"], {"Technology": None})["uncovered"], ["Technology"])
eq("cover2.all_null_signals",
   eval_r5(["Technology"], {"Technology": {
       "insider_acquired_disposed_ratio_q": None, "senate_net_buy_30d": None,
       "institutional_holders_qoq_delta": None,
       "institutional_ownership_pct_delta": None,
       "institutional_sample_size": 5}})["uncovered"], ["Technology"])
# R5 任一訊號欄位有值 → 判得了（partial 資料不算缺席，避免警語氾濫）
eq("cover2.partial_signal_covered",
   eval_r5(["Technology"], {"Technology": {
       "insider_acquired_disposed_ratio_q": 1.2}})["uncovered"], [])
# R6 的訊號欄位（upside）null → 未判定；R7 三窗口缺任一格 → 未判定
eq("cover2.r6_null_upside",
   eval_r6(["Technology"], {"Technology": {
       "analyst_pt_upside_median_pct": None,
       "pt_sample_size": 5}})["uncovered"], ["Technology"])
eq("cover2.r7_partial_window",
   eval_r7(["Technology"], {"Technology": {
       "rs_vs_spy_3m": 0.062, "rs_vs_spy_20d": None,
       "rs_vs_spy_5d": -0.01}})["uncovered"], ["Technology"])
# 型別髒值（字串數字）＝判不了：build 端 gate 用 `is None` 擋缺格，字串會過那關，
# 到這裡必須被 `_num()` 擋下並標未判定，而不是靜默讀成「沒觸發」
eq("cover2.string_values_uncovered",
   eval_r7(["Technology"], {"Technology": {
       "rs_vs_spy_3m": "0.062", "rs_vs_spy_20d": "-0.03",
       "rs_vs_spy_5d": "-0.01"}})["uncovered"], ["Technology"])

# ── RULE_LIBRARY 門檻由常數插值（4.95.3）─────────────────────────────────────
# 這幾條 assert 靠「測試 import 的常數」與「規則原文」綁在一起：改常數而沒改
# 插值的話原文不會跟上，這裡就會紅 —— DA 只看得到原文，脫鉤即假規則。
from da_pretrigger import (  # noqa: E402
    R4_REAL_RATE_THRESHOLD, R5_INSIDER_RATIO_THRESHOLD,
    R6_PT_UPSIDE_THRESHOLD, RULE_LIBRARY,
)
eq("library.r4_threshold_interpolated",
   f"{R4_REAL_RATE_THRESHOLD}% threshold" in RULE_LIBRARY["R4"], True)
eq("library.r5_threshold_interpolated",
   f"< {R5_INSIDER_RATIO_THRESHOLD}" in RULE_LIBRARY["R5"], True)
eq("library.r6_threshold_interpolated",
   f"< {R6_PT_UPSIDE_THRESHOLD * 100:.0f}%" in RULE_LIBRARY["R6"], True)

# ── prompt_block ─────────────────────────────────────────────────────────────
quiet_rules = {r: {"fired": False, "available": True, "unavailable_reason": None,
                   "sectors": []} for r in ("R4", "R5", "R6", "R7")}
eq("prompt.quiet_uses_canonical_text", build_prompt_block(quiet_rules), NO_TRIGGER_TEXT)

rules = dict(quiet_rules)
rules["R7"] = {"fired": True, "available": True, "unavailable_reason": None,
               "sectors": [{"sector": "Technology",
                            "evidence": [{"field": "rs", "value": 1, "cite": "3M +6.2% but 20d -3.0%"}]}]}
block = build_prompt_block(rules)
eq("prompt.fired_rule_included", "momentum_exhaustion" in block, True)
eq("prompt.hit_values_included", "3M +6.2% but 20d -3.0%" in block, True)
eq("prompt.unfired_rules_excluded", "smart_money_divergence" in block, False)

rules_unavail = dict(quiet_rules)
rules_unavail["R4"] = {"fired": False, "available": False,
                       "unavailable_reason": "fred cache missing", "sectors": []}
block = build_prompt_block(rules_unavail)
eq("prompt.unavailable_surfaced", "未能判定" in block, True)
eq("prompt.unavailable_not_silent", "R4" in block, True)

# R4 fired 時 FRED snapshot 的資料時點要跟著上 prompt（4.95.3）——
# --prompt-only 是 PS 實際 paste 的那條路，只寫進 JSON 等於沒說
rules_r4 = dict(quiet_rules)
rules_r4["R4"] = {"fired": True, "available": True, "unavailable_reason": None,
                  "sectors": [{"sector": "Technology",
                               "evidence": [{"field": "real_rate_preferred",
                                             "value": 2.41,
                                             "cite": "real_rate 2.41% > 2.0% threshold"}]}]}
eq("prompt.r4_carries_generated_at",
   FRED_GENERATED_AT in build_prompt_block(rules_r4, FRED_GENERATED_AT), True)
eq("prompt.no_generated_at_no_stub",
   "generated_at" in build_prompt_block(rules_r4), False)
eq("prompt.non_r4_not_stamped",
   "generated_at" in build_prompt_block(rules, FRED_GENERATED_AT), False)

# 逐板塊缺席也必須進 prompt —— DA 只看得到 prompt，光寫進 JSON 等於沒說
rules_uncovered = dict(quiet_rules)
rules_uncovered["R6"] = dict(quiet_rules["R6"], uncovered=["Energy"])
block = build_prompt_block(rules_uncovered)
eq("prompt.uncovered_surfaced", "未能判定" in block, True)
eq("prompt.uncovered_names_rule_and_sector",
   "R6" in block and "Energy" in block, True)
# 沒觸發那句仍要在（缺席是附加警語，不是取代判定結果）
eq("prompt.uncovered_keeps_no_trigger_text", NO_TRIGGER_TEXT in block, True)

# ── HARD cache 缺席 → rc=1，不得靜默回「沒觸發」────────────────────────────
tmp = tempfile.mkdtemp(prefix="se3_")
try:
    def write_caches(**overrides):
        payloads = {
            "sector_smart_money": SM_QUIET,
            "sector_earnings_pulse": {"Technology": {"analyst_pt_upside_median_pct": 0.5,
                                                     "pt_sample_size": 5}},
            "sector_valuation": {"Technology": {"rs_vs_spy_3m": 0.01,
                                                "rs_vs_spy_20d": 0.01,
                                                "rs_vs_spy_5d": 0.01}},
        }
        payloads.update(overrides)
        for stem, sectors in payloads.items():
            if sectors is None:
                continue
            with open(os.path.join(tmp, f"{stem}_{DATE}.json"), "w") as fh:
                json.dump({"as_of_date": DATE, "sectors": sectors}, fh)

    fred_path = os.path.join(tmp, "fred.json")
    with open(fred_path, "w") as fh:
        json.dump({"generated_at": FRED_GENERATED_AT,
                   "regime_label": "Soft Landing", "regime_confidence": 0.7,
                   "regime_signals": {"real_rate_preferred": 1.0,
                                      "yield_curve_inverted": False},
                   "sector_rotation": {"favor": [], "avoid": []}}, fh)

    write_caches()
    rec = run(["Technology"], scan_date=DATE, cache_dir=tmp, fred_path=fred_path)
    eq("run.quiet_no_triggers", rec["any_fired"], False)
    eq("run.quiet_prompt", rec["prompt_block"], NO_TRIGGER_TEXT)

    # 缺 smart_money → raise（不是回「沒觸發」）
    os.unlink(os.path.join(tmp, f"sector_smart_money_{DATE}.json"))
    try:
        run(["Technology"], scan_date=DATE, cache_dir=tmp, fred_path=fred_path)
        eq("run.missing_hard_cache_raises", "no_raise", "PretriggerInputError")
    except PretriggerInputError as e:
        eq("run.missing_hard_cache_raises", "smart_money" in str(e), True)

    # CLI 層同樣 rc=1
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "da_pretrigger.py"), "--date", DATE,
         "--hot", "Technology", "--cache-dir", tmp, "--fred", fred_path],
        capture_output=True, text=True)
    eq("cli.missing_hard_cache_rc", proc.returncode, 1)
    # 錯誤走 stderr，stdout 必須乾淨 —— stdout 的契約是「逐字 paste 進 DA prompt」，
    # 忘了看 rc 的 pipeline 會把 {"error": ...} 貼進 <TRIGGERED_DIVERGENCE_RULES>。
    eq("cli.missing_hard_cache_reports_error", "error" in proc.stderr, True)
    eq("cli.missing_hard_cache_stdout_clean", proc.stdout.strip(), "")

    # FRED 缺席不是錯誤：rc=0，但 R4 標 unavailable
    write_caches()
    rec = run(["Technology"], scan_date=DATE, cache_dir=tmp,
              fred_path=os.path.join(tmp, "nope.json"))
    eq("run.fred_absent_ok", rec["rules"]["R4"]["available"], False)
    eq("run.fred_absent_not_fired", rec["rules"]["R4"]["fired"], False)
    eq("run.fred_absent_surfaced", "未能判定" in rec["prompt_block"], True)

    # sector 名稱正規化（帶空格的寫法要對得上 cache 的 canonical key）
    write_caches(sector_valuation={"Consumer_Discretionary": {
        "rs_vs_spy_3m": 0.08, "rs_vs_spy_20d": -0.02, "rs_vs_spy_5d": -0.01}})
    rec = run(["Consumer Discretionary"], scan_date=DATE, cache_dir=tmp,
              fred_path=fred_path)
    eq("run.canonicalizes_sector", rec["hot_sectors"], ["Consumer_Discretionary"])
    eq("run.canonical_match_fires_r7", rec["rules"]["R7"]["fired"], True)

    # ── per-sector 覆蓋：「這個板塊沒資料」≠「這個板塊沒觸發」──────────────
    # 整檔缺席已由 _load_hard_cache 擋成 rc=1；這裡鎖的是逐板塊那一層。
    # 舊版 `cache.get(s) or {}` → 全欄位 None → 不觸發且 available=true，
    # 於是截斷的 cache 或打錯的 sector 名會回報「查過了，沒事」。
    write_caches()
    rec = run(["Technology", "Utilities"], scan_date=DATE, cache_dir=tmp,
              fred_path=fred_path)
    eq("cover.uncovered_listed", rec["rules"]["R5"]["uncovered"], ["Utilities"])
    eq("cover.covered_not_listed", "Technology" in rec["rules"]["R5"]["uncovered"], False)
    eq("cover.surfaced_in_prompt", "未能判定" in rec["prompt_block"], True)
    eq("cover.prompt_names_sector", "Utilities" in rec["prompt_block"], True)

    # --prompt-only 是 PS 實際 paste 的那條路徑：缺席警語必須出現在 stdout，
    # 且 stdout 只有 prompt block（rc=0 時不得混入 JSON 或警告）
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "da_pretrigger.py"), "--date", DATE,
         "--hot", "Technology,Utilities", "--cache-dir", tmp, "--fred", fred_path,
         "--prompt-only"], capture_output=True, text=True)
    eq("cli.prompt_only_rc", proc.returncode, 0)
    eq("cli.prompt_only_stdout_is_prompt_block",
       proc.stdout.strip(), rec["prompt_block"].strip())
    eq("cli.prompt_only_uncovered_visible",
       "Utilities" in proc.stdout and "未能判定" in proc.stdout, True)
    eq("cli.prompt_only_no_json_leak", '"schema"' in proc.stdout, False)
    eq("cli.prompt_only_stderr_clean", proc.stderr.strip(), "")

    # 空 sectors 的 cache（形狀合法但沒有任何板塊）不得讀成「沒觸發」
    write_caches(sector_smart_money={}, sector_earnings_pulse={}, sector_valuation={})
    rec = run(["Technology"], scan_date=DATE, cache_dir=tmp, fred_path=fred_path)
    eq("cover.empty_cache_not_silent", rec["rules"]["R6"]["uncovered"], ["Technology"])
    eq("cover.empty_cache_surfaced", "未能判定" in rec["prompt_block"], True)
    eq("cover.empty_cache_not_no_trigger_text",
       rec["prompt_block"].strip() == NO_TRIGGER_TEXT, False)

    # null 佔位（值層）同樣不得讀成「查過了、乾淨」——warning 要一路走到 prompt
    write_caches(sector_smart_money={"Technology": None})
    rec = run(["Technology"], scan_date=DATE, cache_dir=tmp, fred_path=fred_path)
    eq("cover.null_entry_uncovered_r5", rec["rules"]["R5"]["uncovered"], ["Technology"])
    eq("cover.null_entry_surfaced", "未能判定" in rec["prompt_block"], True)

    # fred avoid 的元素層髒值走 `_slim_fred` 消毒（4.95.2）：非字串元素不得讓
    # R4 直接 AttributeError（rc=1 且 stdout 空），合法元素照判
    fred_bad = os.path.join(tmp, "fred_bad.json")
    with open(fred_bad, "w") as fh:
        json.dump({"generated_at": FRED_GENERATED_AT,
                   "regime_label": "Soft Landing", "regime_confidence": 0.7,
                   "regime_signals": {"real_rate_preferred": 1.0,
                                      "yield_curve_inverted": False},
                   "sector_rotation": {"favor": [], "avoid": ["Technology", 5]}}, fh)
    write_caches()
    rec = run(["Technology"], scan_date=DATE, cache_dir=tmp, fred_path=fred_bad)
    eq("fredshape.mixed_avoid_no_crash", rec["rules"]["R4"]["fired"], True)
    eq("fredshape.valid_element_still_judged",
       hits(rec["rules"]["R4"]), ["Technology"])

    # 非 GICS / 打錯字的 sector 名：canonicalize 靜默 fallback 成原字串，
    # 三份 cache 都不認得 → 必須有明確訊號
    write_caches()
    rec = run(["Semiconductors"], scan_date=DATE, cache_dir=tmp, fred_path=fred_path)
    eq("cover.unknown_sector_flagged", rec["unknown_sectors"], ["Semiconductors"])
    eq("cover.unknown_sector_uncovered_r7", rec["rules"]["R7"]["uncovered"],
       ["Semiconductors"])

    # FRED snapshot 與 --date 沒有綁定關係（讀的是 fred_latest.json），
    # 稽核檔必須記下實際用的那一份是哪時候產的
    eq("audit.fred_generated_at_recorded", rec["fred_generated_at"], FRED_GENERATED_AT)

    # run() 接線層：R4 fired → generated_at 出現在 prompt_block（4.95.3）
    fred_hot = os.path.join(tmp, "fred_hot.json")
    with open(fred_hot, "w") as fh:
        json.dump({"generated_at": FRED_GENERATED_AT,
                   "regime_label": "Soft Landing", "regime_confidence": 0.7,
                   "regime_signals": {"real_rate_preferred": 2.41,
                                      "yield_curve_inverted": False},
                   "sector_rotation": {"favor": [], "avoid": []}}, fh)
    write_caches()
    rec = run(["Technology"], scan_date=DATE, cache_dir=tmp, fred_path=fred_hot)
    eq("audit.generated_at_on_prompt_path",
       FRED_GENERATED_AT in rec["prompt_block"], True)

    # R5 豁免不得用缺席的 13F 欄位湊成立 —— 豁免是對 DA 宣稱「查過了、乾淨」
    write_caches(sector_smart_money={"Technology": {
        "insider_acquired_disposed_ratio_q": 1.2}})       # senate / holders_qoq 皆缺
    rec = run(["Technology"], scan_date=DATE, cache_dir=tmp, fred_path=fred_path)
    eq("r5.exempt_requires_all_three", rec["rules"]["R5"]["exempt"], [])
    write_caches(sector_smart_money={"Technology": {
        "insider_acquired_disposed_ratio_q": 1.2, "senate_net_buy_30d": 0,
        "institutional_holders_qoq_delta": 1}})
    rec = run(["Technology"], scan_date=DATE, cache_dir=tmp, fred_path=fred_path)
    eq("r5.exempt_when_all_present",
       [e["sector"] for e in rec["rules"]["R5"]["exempt"]], ["Technology"])

    # 純函式：同輸入同輸出
    write_caches()
    a = run(["Technology"], scan_date=DATE, cache_dir=tmp, fred_path=fred_path)
    b = run(["Technology"], scan_date=DATE, cache_dir=tmp, fred_path=fred_path)
    eq("run.deterministic", a, b)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ──────────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} regression(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ SE3 DA pre-trigger fixtures pass")

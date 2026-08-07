#!/usr/bin/env python3
"""sector_score_calculator.py — 產業掃描分數 deterministic 複算 + shadow 落盤（SE1）。

用途：把 `sector_protocol_main.md` 的 Scoring Rubric 用程式重算一次，與 LLM 寫進
`sector_decision_<DATE>.json` 的分數對照，累積 Phase 4c 割接（SE2）所需的證據。

**本檔 shadow-only**：`build_sector_intel.py` 預設不因對照失敗中止（唯一例外是
`SECTOR_CALC_STRICT=1`）。分數權威仍在 LLM，本檔只記錄。

SE1 修掉的兩個問題
------------------
1. **結果沒落盤**：舊版只把摘要印到 stderr。protocol 跑完 stderr 就沒了，於是
   「shadow 跑了幾個月」等於沒有樣本 —— 割接判準（N=5 場）無從累計。現在每場寫
   `sector/cache/shadow_score_<DATE>.json`，並由 `--status` 統計進度。
2. **覆蓋範圍沒寫進報告**：讀報告的人無從知道 PASS 涵蓋了什麼。現在每份報告自帶
   `coverage.modeled` / `coverage.not_modeled`，並逐板塊標出「偵測到但無法驗證」的步驟。

Step 5 特殊乘數為何**不重算**（動手前先查了 33 筆歷史樣本）
----------------------------------------------------------
SE1 原本打算補模 Step 5（binary_risk ×0.70、Late/Recession cyclical ×0.85），假設
「LLM 套了、calculator 沒套 → 假 hard diff」。**實測推翻了這個假設**：掃過全部歷史
decision 檔中帶 `binary_risk_within_48h` 的 33 筆，其中 **31 筆**的
`sum(score_components) × step6_mult` 直接等於 `composite_score` —— 也就是 LLM 是把
Step 5 乘數**烙進四個分項之後**才寫下 `score_components`（例：2026-07-31 Energy 的
`key_reasons` 明寫「已因 OPEC 會議套用 binary ×0.70（91.8 → 64.3）」，而 64.3 正是
四個分項的和）。這也與 `sector_protocol_review.md` 的階段合約一致：
「`pre_step6_score` … 與 LLM 在 decision.json 中的 `score_components` 加總基準對比」。

所以在這裡再乘一次 0.70 = **雙重計分**，會把 31 筆本來正確的樣本全打成 hard diff。
正確做法是**偵測不重算**：記下 Step 5 條件存在、標為「本檔無法驗證」，因為乘數已烙進
calculator 無法獨立反解的分項裡。SE2 割接後 engine 從原始分項算起，這步才會變成可驗證的。

分數階段合約（沿用 `sector_protocol_review.md` 的定義）
------------------------------------------------------
    base_score      = breadth_momentum + theme_heat + news_catalyst + rotation_signal
                      （Step 1–4 權重乘數與 Step 5 特殊乘數**皆已內含**在 LLM 寫下的
                        四個分項裡，不在本檔重算 —— 那是階段合約的定義，不是漏模）
    pre_step6_score = clamp(base_score + valuation_penalty)       ← Step 5b
    post_step6_score= clamp(pre_step6_score × step6_fred_multiplier)
                      ↑ 與頂層 composite_score 對照

Usage
-----
    # 讀出端：統計割接進度（掃 sector/cache/shadow_score_*.json）
    python3 sector/scripts/sector_score_calculator.py --status
    python3 sector/scripts/sector_score_calculator.py --status --json

    # 歷史重放：把既有 sector_decision_*.json 全部對照一次（唯讀，不產 shadow 樣本）
    python3 sector/scripts/sector_score_calculator.py --audit-decisions

build_sector_intel.py 匯入 `run_shadow_score_check` / `verify_session_dual_run` /
`build_shadow_report` / `write_shadow_report`。
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
from datetime import datetime, timezone

CALCULATOR_VERSION = "sector_score_calculator.py v1.2 (V4.95.1)"
SHADOW_SCHEMA = "sector_shadow_score.v1"
UNKNOWN_VERSION = "<unknown>"

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(ROOT, "sector", "cache")

# ── 割接判準（來源：sector_protocol_review.md §3 Dual-Run 割接達標基準）────────
# 注意兩種語意的差別，這正是會導致誤判割接的地方：
#   - verify_session_dual_run() 的 soft ≤ 2 是 **per-session**（沿用舊行為，不改）
#   - CUTOVER_MAX_SOFT_DIFFS 是 **跨場累計**（review 原文「累計執行 N=5 次…≤2 個
#     soft diff」）。累計較嚴，割接與否以它為準。
CUTOVER_MIN_SESSIONS = 5
CUTOVER_MAX_HARD_DIFFS = 0
CUTOVER_MAX_SOFT_DIFFS = 2
CUTOVER_MAX_PENALTY_DRIFTS = 0

HARD_DIFF_THRESHOLD = 1.0
SOFT_DIFF_THRESHOLD = 0.5

# 複算所需的分項。少任何一格 = 這筆算不出來（不是算出 0 分），見
# `run_shadow_score_check` 的逐欄位守衛。
BASE_SCORE_COMPONENTS = ("breadth_momentum", "theme_heat", "news_catalyst", "rotation_signal")
REQUIRED_SCORE_COMPONENTS = BASE_SCORE_COMPONENTS + ("valuation_penalty",)

# Step 5 特殊乘數（sector_protocol_main.md Step 5 / phase_4-5.md STEP C·E）
BINARY_RISK_MULTIPLIER = 0.70
CYCLE_CYCLICAL_MULTIPLIER = 0.85
CYCLE_DEFENSIVE_MULTIPLIER = 1.10
CYCLE_PENALTY_PHASES = ("late", "recession")
BINARY_RISK_FLAG = "binary_risk_within_48h"

# 報告裡明寫覆蓋範圍 —— 讀報告的人（或 SE2 割接時的自己）不必去讀原始碼才知道
# 哪些步驟被模了、哪些沒有。
COVERAGE_MODELED = [
    "base_score (四分項加總)",
    "Step 5b valuation_penalty overlay（含 cache 對照的 penalty drift 偵測）",
    "Step 6 FRED regime multiplier (取 decision 已寫入的 step6_fred_multiplier)",
]
COVERAGE_NOT_MODELED = [
    "Step 1-4 動態權重乘數（依階段合約已內含在 LLM 寫下的四個分項，無法反解）",
    "Step 5 特殊乘數 binary_risk ×0.70 / cycle ×0.85·×1.10"
    "（同樣已烙進分項；本檔只**偵測條件存在**並標為 unverified，重算會變雙重計分。"
    "SE2 割接後 engine 從原始分項算起，此步才可驗證）",
    "Phase 4c STEP D/G/G.5 verdict 降級（改 label 不改分數，不影響本對照）",
    "Phase 4c STEP F/G.5 regime_confidence 乘數（不改 composite_score）",
    "Phase 4c STEP A/B/H stance 與文字欄位",
]


def _num(x):
    """只認真正的**有限**數字；bool 是 int 的子類，必須擋掉。

    NaN/inf 也一律擋掉：NaN 的所有比較都回 False，混進來會讓 diff 判定靜默失效
    （`abs(nan - x) > 1.0` 是 False，於是一筆爛資料會顯示成「完全相符」）。
    JSON 的 `NaN` / `Infinity` 是 Python parser 接受的合法字面值，擋在這裡最省事。
    """
    if not isinstance(x, (int, float)) or isinstance(x, bool):
        return None
    return x if math.isfinite(x) else None


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


# 浮點雜訊容差：見 `_round_half_up` docstring。0-100 的分數尺度上，float64 的雜訊
# 約 1e-14，1e-9 足以吸收又遠小於任何有意義的分數差。
_ROUND_EPS = 1e-9


def _round_half_up(v: float) -> int:
    """0.5 一律進位（負數則 half-away-from-zero）。

    **不可用內建 `round()`**：Python 用銀行家捨入（`round(42.5) == 42`），而 protocol
    的 score 是給人看的整數分，慣例是 half-up。實測 473 筆歷史樣本，half-up 相符率
    92.2% 對 banker's 91.5%，差的 3 筆全部是 `.5` 邊界（42.5→43、54.5→55、46.5→47），
    LLM 三次都進位。

    **為什麼要加 `_ROUND_EPS`**：Step 6 的乘法會讓真值恰為 `.5` 的結果落在邊界下方，
    例如 `50.0 × 1.15 == 57.49999999999999`（真值 57.5），裸的 `floor(v + 0.5)` 會給 57
    而正確答案是 58。實際乘數表（0.85/0.90/0.95/1.05/1.10/1.15）× 0.5 為間隔的分數共
    掃出 3 個這種案例。加 eps 之後兩類邊界都對。
    """
    if v < 0:
        return -math.floor(-v + 0.5 + _ROUND_EPS)
    return math.floor(v + 0.5 + _ROUND_EPS)


def compute_deterministic_valuation_penalty(pe_zscore_1y, uptrend_ratio) -> int:
    """Step 5b Valuation Penalty Overlay（sector_protocol_main.md）:
    - pe_zscore_1y > 2.0 且 uptrend_ratio > 0.7 → −10（overbought distribution risk）
    - pe_zscore_1y < −1.0 且 uptrend_ratio < 0.3 → +5（oversold value opportunity）
    - 其他 → 0
    """
    pe_z = _num(pe_zscore_1y)
    ur = _num(uptrend_ratio)
    if pe_z is None or ur is None:
        return 0
    if pe_z > 2.0 and ur > 0.7:
        return -10
    if pe_z < -1.0 and ur < 0.3:
        return 5
    return 0


def detect_step5_conditions(sector_data: dict, context: dict | None) -> list[dict]:
    """偵測 Step 5 特殊乘數的**觸發條件**，回傳 [{name, expected_multiplier, basis}]。

    ⚠️ **偵測，不套用**。乘數已烙進 LLM 寫下的 `score_components`（見檔頭 33 筆實測），
    在這裡再乘一次就是雙重計分。這個回傳值的用途是把該板塊標成
    「有本檔無法驗證的步驟」，讓 SE2 割接時知道哪些樣本的證據強度較弱。

    兩條規則都只依已在手的欄位判定，不重算任何上游數字：
      - binary risk：LLM 已把 `binary_risk_within_48h` 寫進 risk_flags（STEP E 要求）
      - cycle：`cycle_phase ∈ {Late, Recession}` 且 `fred_available=false`
        （fred 可用時 Step 1/STEP C 由 Step 6 取代，本來就不該套）
    """
    ctx = context or {}
    out = []

    flags = sector_data.get("risk_flags") or []
    if isinstance(flags, list) and BINARY_RISK_FLAG in flags:
        out.append({
            "name": "binary_risk_within_48h",
            "expected_multiplier": BINARY_RISK_MULTIPLIER,
            "basis": f"risk_flags 含 {BINARY_RISK_FLAG}",
        })

    cycle_phase = str(ctx.get("cycle_phase") or "").strip().lower()
    if cycle_phase in CYCLE_PENALTY_PHASES and ctx.get("fred_available") is False:
        kind = str(sector_data.get("cyclical_or_defensive") or "").strip().lower()
        if kind == "cyclical":
            out.append({
                "name": "cycle_late_cyclical",
                "expected_multiplier": CYCLE_CYCLICAL_MULTIPLIER,
                "basis": f"cycle_phase={ctx.get('cycle_phase')} + cyclical + fred_available=false",
            })
        elif kind == "defensive":
            out.append({
                "name": "cycle_late_defensive",
                "expected_multiplier": CYCLE_DEFENSIVE_MULTIPLIER,
                "basis": f"cycle_phase={ctx.get('cycle_phase')} + defensive + fred_available=false",
            })
    return out


def _unreproducible_report(name: str, sector_data: dict, reasons: list[str]) -> dict:
    """「這筆算不出來」的統一形狀。

    關鍵是 `diff=0.0` + `reproducible=False`：算不出來的板塊不得貢獻 diff（那是假
    FAIL），改為讓整場 `sample_valid=false` 退出割接證據池。
    """
    return {
        "name": name,
        "base_score": None,
        "expected_valuation_penalty": 0,
        "llm_valuation_penalty": None,
        "step5_conditions": [],
        "unverified_steps": [],
        "pre_step6_score": None,
        "step6_fred_multiplier": _num(sector_data.get("step6_fred_multiplier")),
        "calculated_post_score": None,
        "llm_composite_score": _num(sector_data.get("composite_score")),
        "diff": 0.0,
        "penalty_drift": False,
        "reproducible": False,
        "unreproducible_reasons": reasons,
    }


def run_shadow_score_check(sector_data: dict, valuation_cache: dict | None,
                           context: dict | None = None) -> dict:
    """單一板塊的雙軌對照。`context` 可選（{cycle_phase, fred_available}）；
    不傳 = 退回舊行為（不模 cycle 乘數），既有呼叫端不會壞。"""
    name = sector_data.get("name", "Unknown")
    sc = sector_data.get("score_components")
    unreproducible = []

    if not isinstance(sc, dict) or not sc:
        # 無分項 = 這筆無法複算。不能當成 0 分算出一個「差異很大」的結論。
        return _unreproducible_report(name, sector_data, ["missing_score_components"])

    # 逐欄位檢查，缺一格就整筆退出證據池。
    #
    # 舊版是 `_num(sc.get(k)) or 0` —— 缺欄位、null、字串全部靜默變 0，於是一筆
    # `theme_heat: null` 會算出 base 少 20 分、diff=20 的**假 hard diff**，而且
    # `reproducible=True` 讓它堂堂進入割接證據池。割接判準是累計 0 hard diff，
    # 一筆這種樣本就永久擋死 SE2，且擋的理由是假的。
    # 「算不出」與「算錯」要分開 —— 這條規則本來只實作在整個 dict 缺席的層級。
    components = {}
    missing = []
    for key in REQUIRED_SCORE_COMPONENTS:
        v = _num(sc.get(key)) if key in sc else None
        if v is None:
            missing.append(key)
        components[key] = v
    if missing:
        return _unreproducible_report(
            name, sector_data,
            [f"missing_score_component:{k}" for k in missing])

    llm_penalty = components["valuation_penalty"]
    base_score = _clamp(sum(components[k] for k in BASE_SCORE_COMPONENTS))

    # ── Step 5 特殊乘數：偵測不套用（重算 = 雙重計分，見檔頭）──────────────
    step5 = detect_step5_conditions(sector_data, context)

    # ── Step 5b Valuation Penalty ──────────────────────────────────────────
    expected_penalty = 0
    if valuation_cache:
        sv = valuation_cache.get(name) or {}
        expected_penalty = compute_deterministic_valuation_penalty(
            sv.get("pe_zscore_1y"), sector_data.get("uptrend_ratio"))

    pre_step6_score = _clamp(base_score + llm_penalty)

    # ── Step 6 FRED overlay ────────────────────────────────────────────────
    mult = _num(sector_data.get("step6_fred_multiplier"))
    ctx = context or {}
    if mult is not None:
        # 一步到位交給 `_round_half_up`，不先 round(...,2)。
        # 中間那道 2 位小數的 round 是**銀行家捨入**，會造成雙重捨入：
        # 64.25 × 1.035 = 66.49875 → round(,2)=66.5 → 67，但真 half-up 是 66。
        # 它原本的用途（吸收浮點雜訊）已由 `_ROUND_EPS` 接手，且順帶消掉
        # 「有 mult 走 2dp、無 mult 不走」造成的同值兩種捨法。
        post = _clamp(pre_step6_score * mult)
    else:
        post = pre_step6_score
        if ctx.get("fred_available") is True:
            # fred 可用卻沒記 multiplier → 我們算不出 LLM 當時用了什麼乘數，
            # 這筆的 diff 沒有意義，不得計入割接證據。
            unreproducible.append("missing_step6_multiplier_with_fred_available")

    calculated_post = _round_half_up(post)
    llm_composite = _num(sector_data.get("composite_score"))
    diff = abs(llm_composite - calculated_post) if llm_composite is not None else 0.0
    if llm_composite is None:
        unreproducible.append("missing_composite_score")

    return {
        "name": name,
        "base_score": base_score,
        "expected_valuation_penalty": expected_penalty,
        "llm_valuation_penalty": llm_penalty,
        # 偵測到但本檔驗不了的步驟 —— 不影響 diff，只標示這筆證據的強度
        "step5_conditions": step5,
        "unverified_steps": [m["name"] for m in step5],
        "pre_step6_score": pre_step6_score,
        "step6_fred_multiplier": mult,
        "calculated_post_score": calculated_post,
        "llm_composite_score": llm_composite,
        "diff": diff,
        "penalty_drift": expected_penalty != llm_penalty,
        "reproducible": not unreproducible,
        "unreproducible_reasons": unreproducible,
    }


def verify_session_dual_run(sectors_report: list[dict]) -> tuple[bool, str]:
    """單場 PASS/FAIL 判定（語意沿用舊版，`SECTOR_CALC_STRICT=1` 仍吃這個回傳值）。

    唯一改動：`reproducible=false` 的板塊不計入 diff 統計 —— 算不出來不等於算錯，
    把它當 diff 會製造假 FAIL。這些板塊改為讓整場 `sample_valid=false`（見
    `build_shadow_report`），也就是這場不能當割接證據，比假 FAIL 誠實。
    """
    hard_errors = 0
    soft_errors = 0
    penalty_drifts = 0
    skipped = 0
    details = []

    for r in sectors_report:
        name = r.get("name", "Unknown")
        if not r.get("reproducible", True):
            skipped += 1
            reasons = ", ".join(r.get("unreproducible_reasons") or []) or "unknown"
            details.append(f"  - {name}: SKIPPED (無法複算: {reasons})")
            continue

        if r.get("penalty_drift"):
            penalty_drifts += 1
            details.append(
                f"  - {name}: Valuation Penalty drifted! Expected "
                f"{r['expected_valuation_penalty']}, got {r['llm_valuation_penalty']}")

        diff = r.get("diff") or 0.0
        if diff > HARD_DIFF_THRESHOLD:
            hard_errors += 1
            details.append(
                f"  - {name}: Hard diff! Calculated {r['calculated_post_score']}, "
                f"LLM got {r['llm_composite_score']} (diff={diff:.2f})")
        elif SOFT_DIFF_THRESHOLD < diff <= HARD_DIFF_THRESHOLD:
            soft_errors += 1
            details.append(
                f"  - {name}: Soft diff. Calculated {r['calculated_post_score']}, "
                f"LLM got {r['llm_composite_score']} (diff={diff:.2f})")

    is_ok = (hard_errors == 0) and (soft_errors <= 2) and (penalty_drifts == 0)

    summary_msg = (
        f"[Calculator Dual-Run Check] Hard diffs: {hard_errors}, Soft diffs: {soft_errors}, "
        f"Penalty drifts: {penalty_drifts}, Skipped: {skipped}. "
        f"Status: {'✅ PASS' if is_ok else '❌ FAIL'}"
    )
    if details:
        summary_msg += "\n" + "\n".join(details)
    return is_ok, summary_msg


def build_shadow_report(sectors_report: list[dict], *, scan_date: str,
                        context: dict | None = None,
                        backfill: bool = False) -> dict:
    """組本場 shadow 報告（落盤用）。

    `backfill=True` = 這不是當天實跑（例：`build_sector_intel.py --date <過去日期>`
    重建舊場次）。此時 `_phase0` 讀到的是**今天**的 FRED/breadth cache，`context`
    反映的不是掃描日的狀態，證據等級與 `--audit-decisions` 的歷史重放相同，因此
    一律 `sample_valid=false` —— 否則就是 audit/live 分離做在正門、後門敞開。
    """
    ctx = context or {}
    hard = sum(1 for r in sectors_report
               if r.get("reproducible", True) and (r.get("diff") or 0) > HARD_DIFF_THRESHOLD)
    soft = sum(1 for r in sectors_report
               if r.get("reproducible", True)
               and SOFT_DIFF_THRESHOLD < (r.get("diff") or 0) <= HARD_DIFF_THRESHOLD)
    drift = sum(1 for r in sectors_report
                if r.get("reproducible", True) and r.get("penalty_drift"))
    unreproducible = [
        {"sector": r.get("name"), "reasons": r.get("unreproducible_reasons") or []}
        for r in sectors_report if not r.get("reproducible", True)
    ]
    # 有 unverified 步驟不代表這場作廢（分項→composite 的算術仍驗過），但證據強度較弱，
    # SE2 割接時要知道有多少樣本落在這一類。
    unverified = [
        {"sector": r.get("name"), "steps": r.get("unverified_steps") or []}
        for r in sectors_report if r.get("unverified_steps")
    ]
    is_ok, _ = verify_session_dual_run(sectors_report)

    invalid_reasons = []
    if unreproducible:
        invalid_reasons.append("unreproducible_sectors")
    if not sectors_report:
        # 零板塊的報告不是「全部相符」，是沒有樣本。不擋掉會讓 N=5 用空場次湊滿。
        invalid_reasons.append("empty_report")
    if backfill:
        invalid_reasons.append("backfill_rebuild")

    return {
        "schema": SHADOW_SCHEMA,
        "calculator_version": CALCULATOR_VERSION,
        "scan_date": scan_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "backfill": backfill,
        "coverage": {"modeled": COVERAGE_MODELED, "not_modeled": COVERAGE_NOT_MODELED},
        "context": {
            "cycle_phase": ctx.get("cycle_phase"),
            "fred_available": ctx.get("fred_available"),
        },
        "session": {
            # sample_valid=false → 這場不計入割接證據（不是「算錯」，是「算不出」）
            "sample_valid": not invalid_reasons,
            "invalid_reasons": invalid_reasons,
            "unreproducible": unreproducible,
            "unverified_steps": unverified,
            "sector_count": len(sectors_report),
            "hard_diffs": hard,
            "soft_diffs": soft,
            "penalty_drifts": drift,
            "status": "PASS" if is_ok else "FAIL",
        },
        "sectors": sectors_report,
    }


def shadow_report_path(scan_date: str, cache_dir: str | None = None) -> str:
    return os.path.join(cache_dir or CACHE_DIR, f"shadow_score_{scan_date}.json")


def write_shadow_report(report: dict, *, cache_dir: str | None = None) -> str:
    path = shadow_report_path(report["scan_date"], cache_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 原子寫入：中途死掉的半份 JSON 會在 --status 變 malformed 噪音；.tmp 不會
    # 被 shadow_score_*.json 的 glob 撈到。
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=2)
        fp.write("\n")
    os.replace(tmp, path)
    return path


# ── 讀出端：割接進度（SE2 的前置判準）────────────────────────────────────────
def collect_cutover_status(cache_dir: str | None = None) -> dict:
    """掃所有 shadow 報告，統計割接達標進度。

    只有 `sample_valid=true` 的場次計入分母 —— 與 invest 端 replay 的 cohort 紀律
    一致：算不出來的樣本要被排除且逐筆列出，不能混進統計裡充數。
    """
    pattern = os.path.join(cache_dir or CACHE_DIR, "shadow_score_*.json")
    sessions, invalid, malformed = [], [], []

    for path in sorted(glob.glob(pattern)):
        base = os.path.basename(path)
        if ".prev" in base:          # 手動備份檔，不是正式場次（同 audit 端）
            continue
        try:
            with open(path, encoding="utf-8") as fp:
                rep = json.load(fp)
        except Exception as e:
            malformed.append({"file": base, "error": str(e)})
            continue
        if not isinstance(rep, dict) or rep.get("schema") != SHADOW_SCHEMA:
            malformed.append({"file": base, "error": "schema mismatch"})
            continue
        sess = rep.get("session") or {}
        # 計數欄位必須是真數字。`.get(k, 0)` 只在 key **不存在**時給預設，
        # `"hard_diffs": null` 會原樣回 None 並在下面 sum() 時 TypeError 掛掉。
        counts = {k: _num(sess.get(k)) for k in
                  ("hard_diffs", "soft_diffs", "penalty_drifts")}
        # 負數也判 malformed：割接判準是**跨場 sum**，一筆 `hard_diffs: -2` 能把
        # 別場的真 hard diff 從累計裡抵銷掉。
        bad = [k for k, v in counts.items() if v is None or v < 0]
        if bad:
            malformed.append({"file": base,
                              "error": f"invalid session counters: {', '.join(bad)}"})
            continue
        # 版號缺失或非字串一律自成一格 —— None 會在下面的混版本檢查被 falsy 濾掉
        # （繞過檢查又照算有效場次）；非字串（數字版號）會讓 `sorted()` 混型
        # TypeError，整份 --status 掛掉。
        ver = rep.get("calculator_version")
        row = {
            "scan_date": rep.get("scan_date"),
            "file": base,
            "calculator_version": ver if isinstance(ver, str) and ver else UNKNOWN_VERSION,
            **counts,
            "status": sess.get("status"),
        }
        # 有效場次是割接分母，只認 JSON true —— truthiness 會把字串 "false"、
        # 數字 1 之類的髒值也放進分母。
        if sess.get("sample_valid") is True:
            sessions.append(row)
        else:
            row["unreproducible"] = sess.get("unreproducible") or []
            row["invalid_reasons"] = sess.get("invalid_reasons") or []
            invalid.append(row)

    hard = sum(s["hard_diffs"] for s in sessions)
    soft = sum(s["soft_diffs"] for s in sessions)
    drift = sum(s["penalty_drifts"] for s in sessions)
    n = len(sessions)

    unmet = []
    if n < CUTOVER_MIN_SESSIONS:
        unmet.append(f"valid sessions {n} < {CUTOVER_MIN_SESSIONS}")
    if hard > CUTOVER_MAX_HARD_DIFFS:
        unmet.append(f"cumulative hard diffs {hard} > {CUTOVER_MAX_HARD_DIFFS}")
    if soft > CUTOVER_MAX_SOFT_DIFFS:
        unmet.append(f"cumulative soft diffs {soft} > {CUTOVER_MAX_SOFT_DIFFS}")
    if drift > CUTOVER_MAX_PENALTY_DRIFTS:
        unmet.append(f"cumulative penalty drifts {drift} > {CUTOVER_MAX_PENALTY_DRIFTS}")

    # 混版本的樣本要提醒：calculator 改過覆蓋率之後，舊版樣本的 diff 不同基準。
    versions = sorted({s["calculator_version"] for s in sessions})
    if len(versions) > 1:
        unmet.append(f"mixed calculator versions across valid sessions: {versions}")

    return {
        "schema": "sector_shadow_cutover_status.v1",
        "criteria": {
            "min_sessions": CUTOVER_MIN_SESSIONS,
            "max_hard_diffs": CUTOVER_MAX_HARD_DIFFS,
            "max_soft_diffs_cumulative": CUTOVER_MAX_SOFT_DIFFS,
            "max_penalty_drifts": CUTOVER_MAX_PENALTY_DRIFTS,
        },
        "valid_sessions": n,
        "cumulative": {"hard_diffs": hard, "soft_diffs": soft, "penalty_drifts": drift},
        "cutover_eligible": not unmet,
        "unmet": unmet,
        "sessions": sessions,
        "invalid_sessions": invalid,
        "malformed_files": malformed,
    }


# ── 歷史審計：把既有 decision 檔重放一次（唯讀，不產 shadow 樣本）──────────────
def audit_decision_files(cache_dir: str | None = None) -> dict:
    """對 `sector_decision_<DATE>.json` 全部重放對照。

    為什麼要有這個：shadow 落盤只對**未來**的場次生效，而 SE2 的割接判準要 5 場。
    歷史 decision 檔就在硬碟上，重放它們等於立刻拿到數十場證據 —— 這是 invest L1
    （4.80.0）用 replay 取代 live 累積的同一招。

    **刻意不寫進 shadow_score_*.json**：這些場次的 `_phase0` 已不可考（cycle_phase
    取自 decision 檔本身、fred_available 由 step6 乘數存在與否反推），與實跑樣本不是
    同一等級的證據。混進去就是在稽核軌跡放假樣本（C1 的教訓）。
    """
    cdir = cache_dir or CACHE_DIR
    sessions = []
    for path in sorted(glob.glob(os.path.join(cdir, "sector_decision_*.json"))):
        base = os.path.basename(path)
        if ".prev" in base:          # 手動備份檔，不是正式場次
            continue
        try:
            with open(path, encoding="utf-8") as fp:
                dec = json.load(fp)
        except Exception as e:
            sessions.append({"file": base, "error": str(e)})
            continue

        date = dec.get("verdict_date") or base[len("sector_decision_"):-len(".json")]
        sectors = dec.get("sectors") or []
        # fred_available 反推：Step 6 有寫乘數 = 當時 fred 可用
        fred_available = any(_num(s.get("step6_fred_multiplier")) is not None for s in sectors)
        ctx = {"cycle_phase": dec.get("cycle_phase"), "fred_available": fred_available}

        val_path = os.path.join(cdir, f"sector_valuation_{date}.json")
        val_sectors = None
        if os.path.exists(val_path):
            try:
                with open(val_path, encoding="utf-8") as fp:
                    val_sectors = (json.load(fp) or {}).get("sectors")
            except Exception:
                val_sectors = None

        reports = [run_shadow_score_check(s, val_sectors, ctx) for s in sectors]
        rep = build_shadow_report(reports, scan_date=date, context=ctx)
        sess = rep["session"]
        sessions.append({
            "scan_date": date, "file": base,
            "valuation_cache": val_sectors is not None,
            "sector_count": sess["sector_count"],
            "hard_diffs": sess["hard_diffs"], "soft_diffs": sess["soft_diffs"],
            "penalty_drifts": sess["penalty_drifts"],
            "sample_valid": sess["sample_valid"], "status": sess["status"],
            "offenders": [
                {"sector": r["name"], "calculated": r["calculated_post_score"],
                 "llm": r["llm_composite_score"], "diff": r["diff"],
                 "penalty_drift": r["penalty_drift"],
                 "unverified_steps": r.get("unverified_steps") or []}
                for r in reports
                if r.get("reproducible", True)
                and ((r.get("diff") or 0) > SOFT_DIFF_THRESHOLD or r.get("penalty_drift"))
            ],
        })

    ok = [s for s in sessions if "error" not in s]
    clean = [s for s in ok if s["hard_diffs"] == 0 and s["penalty_drifts"] == 0]
    return {
        "schema": "sector_shadow_audit.v1",
        "calculator_version": CALCULATOR_VERSION,
        "note": "歷史重放，非 live shadow 樣本；不計入 --status 的割接分母",
        "sessions_audited": len(ok),
        "sessions_clean": len(clean),
        "total_hard_diffs": sum(s["hard_diffs"] for s in ok),
        "total_soft_diffs": sum(s["soft_diffs"] for s in ok),
        "total_penalty_drifts": sum(s["penalty_drifts"] for s in ok),
        "sessions": sessions,
    }


def _print_audit(a: dict) -> None:
    print(f"Sector decision 歷史重放審計 — {a['calculator_version']}")
    print(f"  ⚠ {a['note']}\n")
    print(f"  場次        : {a['sessions_audited']}（全乾淨 {a['sessions_clean']}）")
    print(f"  hard diffs  : {a['total_hard_diffs']}")
    print(f"  soft diffs  : {a['total_soft_diffs']}")
    print(f"  penalty drift: {a['total_penalty_drifts']}\n")
    for s in a["sessions"]:
        if "error" in s:
            print(f"  ⚠ {s['file']}: {s['error']}")
            continue
        if not s["offenders"]:
            continue
        print(f"  {s['scan_date']} [{s['status']}]")
        for o in s["offenders"]:
            tag = " penalty_drift" if o["penalty_drift"] else ""
            unv = f" (unverified: {','.join(o['unverified_steps'])})" if o["unverified_steps"] else ""
            print(f"    - {o['sector']:24} calc={o['calculated']} llm={o['llm']} "
                  f"diff={o['diff']:.2f}{tag}{unv}")


def _print_status(st: dict) -> None:
    print(f"Sector Phase 4c 割接進度（SE2 前置） — {CALCULATOR_VERSION}")
    print(f"  有效場次 : {st['valid_sessions']} / {st['criteria']['min_sessions']}")
    c = st["cumulative"]
    print(f"  累計 hard diff   : {c['hard_diffs']} (上限 {st['criteria']['max_hard_diffs']})")
    print(f"  累計 soft diff   : {c['soft_diffs']} (上限 {st['criteria']['max_soft_diffs_cumulative']})")
    print(f"  累計 penalty drift: {c['penalty_drifts']} (上限 {st['criteria']['max_penalty_drifts']})")
    if st["invalid_sessions"]:
        print(f"  排除（不計入分母）: {len(st['invalid_sessions'])} 場")
        for s in st["invalid_sessions"]:
            names = ", ".join(u.get("sector", "?") for u in s.get("unreproducible", []))
            why = ", ".join(s.get("invalid_reasons") or []) or "unknown"
            print(f"    - {s['scan_date']}: {why}{f'（{names}）' if names else ''}")
    if st["malformed_files"]:
        for m in st["malformed_files"]:
            print(f"  ⚠ 壞檔 {m['file']}: {m['error']}")
    print(f"\n  割接資格: {'✅ 達標' if st['cutover_eligible'] else '❌ 未達標'}")
    for u in st["unmet"]:
        print(f"    - {u}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Sector score shadow calculator / cutover status")
    ap.add_argument("--status", action="store_true",
                    help="統計 shadow_score_*.json 的割接達標進度")
    ap.add_argument("--audit-decisions", action="store_true",
                    help="重放既有 sector_decision_*.json（唯讀；不寫 shadow 樣本）")
    ap.add_argument("--json", action="store_true", help="輸出 JSON")
    ap.add_argument("--cache-dir", default=None, help="覆寫 sector/cache 路徑（測試用）")
    args = ap.parse_args()

    if args.audit_decisions:
        a = audit_decision_files(args.cache_dir)
        print(json.dumps(a, ensure_ascii=False, indent=2) if args.json else "", end="")
        if not args.json:
            _print_audit(a)
        return 0

    if not args.status:
        ap.print_help()
        return 0

    st = collect_cutover_status(args.cache_dir)
    if args.json:
        print(json.dumps(st, ensure_ascii=False, indent=2))
    else:
        _print_status(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())

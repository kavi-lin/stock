#!/usr/bin/env python3
"""da_pretrigger.py — Phase 4b Devil's Advocate 的 R4–R7 結構性 divergence 預判（SE3）。

V4.12.2 已經把 R4–R7 的規則全文移出 DA prompt（只 paste 當日 fired 的），但**判定本身
仍是 PS 用手上 cache 逐條比 threshold**：4 條規則 × N 個 HOT sector 的純數值比對，正是
LLM 最容易出錯、又最不值得花 token 的形態。本檔把那段搬成 script。

**零新計算**（照 `valuation_reviewer_gate.py` 的模式）：所有數字直接讀 Phase 1/3 已經
落地的 cache，不打任何 API、不重算任何上游指標。

輸出兩塊：
  1. 結構化 JSON（誰觸發、引哪個數值） — 給稽核與日後統計
  2. `prompt_block` — 可**逐字 paste** 進 DA prompt 的 `<TRIGGERED_DIVERGENCE_RULES>`
     placeholder，含 fired 規則的原文與命中數值。沒觸發就是那句 "(無結構性 divergence
     觸發 …)"。PS 不需要再自己組字。

Usage
-----
    python3 sector/scripts/da_pretrigger.py --date 2026-08-03 --hot "Technology,Energy"
    python3 sector/scripts/da_pretrigger.py --date 2026-08-03 --hot "Technology" --prompt-only

rc 契約
-------
  rc=0  正常（含「四條都沒觸發」）
  rc=1  **HARD cache 讀不到**（valuation / smart_money / earnings_pulse）。這三個在
        protocol 裡是 HARD FAIL 層級，缺了就無法判定 R5/R6/R7 —— 此時**不得**回
        「沒有觸發」，那會把 DA 該發的 challenge 靜默關掉，比報錯危險得多。
  FRED 缺席不是錯誤：protocol 允許 `fred_available=false`（graceful optional），
  此時 R4 標 `available=false` + 原因，與「R4 沒觸發」在輸出上嚴格區分。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date as _date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sector.lib.sector_utils import canonicalize_sector_name  # noqa: E402
from phase0_read_caches import _slim_fred  # noqa: E402  (單一 slim 來源，不複製邏輯)

PRODUCER_VERSION = "da_pretrigger.py v1.2 (V4.95.3)"
SCHEMA = "sector_da_pretrigger.v1"

CACHE_DIR = os.path.join(ROOT, "sector", "cache")
FRED_CACHE = os.path.join(ROOT, "skills", "fred-macro", "cache", "fred_latest.json")

# ── 門檻常數（唯一事實來源；改規則只改這裡）──────────────────────────────────
R4_REAL_RATE_THRESHOLD = 2.0
R4_ADVERSE_REGIMES = (
    "Late Cycle Tightening", "Stagflation", "Recession Risk", "Recession Easing",
)
R5_INSIDER_RATIO_THRESHOLD = 0.5
R5_INSIDER_ALIGNED_RATIO = 0.8          # 與 consensus 一致 → 豁免，不挑
R5_INSTITUTIONAL_MIN_SAMPLE = 3
R6_PT_UPSIDE_THRESHOLD = 0.03
R6_PT_MIN_SAMPLE = 3
R7_RS_3M_THRESHOLD = 0.05

# 各規則實際讀的訊號欄位 —— 覆蓋判定（_uncovered）的唯一依據。
# R5 任一欄有值即可判（三個訊號各自獨立成立）；R6/R7 的觸發條件需要全部欄位
# 同時有值才判得了「有／沒有」，缺任何一格都是「未能判定」。
R5_SIGNAL_FIELDS = ("insider_acquired_disposed_ratio_q", "senate_net_buy_30d",
                    "institutional_holders_qoq_delta",
                    "institutional_ownership_pct_delta")
R6_SIGNAL_FIELDS = ("analyst_pt_upside_median_pct",)
R7_SIGNAL_FIELDS = ("rs_vs_spy_3m", "rs_vs_spy_20d", "rs_vs_spy_5d")

# R4 內部優先序（phase_4-5.md R4：credit_stress > yield_curve_inverted >
# real_rate_high > yield_curve_steep）。DA 引數值時要照這個順序挑主證據。
R4_PRIORITY = ("credit_stress_elevated", "yield_curve_inverted",
               "real_rate_preferred", "financial_stress_above_avg",
               "regime_label", "sector_rotation_avoid")

# 規則原文 —— 與 `phase_4-5.md` 的 R4–R7 library 對應。fired 才 paste。
# **所有門檻數字一律由常數插值**（示例的命中值如 1.92/0.41 可寫死）—— 寫死門檻
# 會在改常數時讓 paste 進 prompt 的規則原文與 script 實際判定脫鉤（DA 只看得到前者）。
RULE_LIBRARY = {
    "R4": ("**R4 FRED 衝突**：→ MUST 構造 kill_conditions 引用**具體 FRED 數值**"
           f"（\"real_rate 1.92% > {R4_REAL_RATE_THRESHOLD}% threshold\"），"
           "不可寫 vague「macro 轉差」。"
           "優先序：credit_stress > yield_curve_inverted > real_rate_high > yield_curve_steep。"),
    "R5": ("**R5 smart_money_divergence**：→ MUST 在 `challenge_targets` 加 "
           "**smart_money_divergence** challenge，counter_evidence 引具體數值"
           f"（\"insider ratio 0.41 < {R5_INSIDER_RATIO_THRESHOLD}; "
           "senate net −3 in 30d; 13F holders QoQ −12, "
           "ownership % −0.45\"）。smart money 與 consensus 一致"
           f"（ratio>{R5_INSIDER_ALIGNED_RATIO} 且 senate≥0 且 holders_qoq≥0，"
           "三者皆須有值）→ 不挑。"),
    "R6": ("**R6 pt_target_exhausted**：→ MUST 加 **pt_target_exhausted** challenge，"
           "counter_evidence 引數值（\"PT median upside 1.8% < "
           f"{R6_PT_UPSIDE_THRESHOLD * 100:.0f}% across 5 mega-caps\"）。"),
    "R7": ("**R7 momentum_exhaustion**：→ MUST 加 **momentum_exhaustion** challenge，"
           "counter_evidence 引數值（\"3M RS +8.1% but 20d −2.3% / 5d −0.7% — "
           "short-term reversal\"）。三窗口同向 → 不挑。"),
}

NO_TRIGGER_TEXT = "(無結構性 divergence 觸發 — 專注 R1-R3 + tail-risk)"


class PretriggerInputError(Exception):
    """HARD cache 不可用 —— main() 轉成 {"error": ...} + rc=1。"""


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _pct(x, digits=2):
    n = _num(x)
    return "n/a" if n is None else f"{n * 100:+.{digits}f}%"


def _load_hard_cache(path: str, label: str) -> dict:
    """HARD cache：讀不到一律 raise。gate 讀不到權威輸入時不得猜。"""
    if not os.path.exists(path):
        raise PretriggerInputError(f"{label} cache missing: {path}")
    try:
        with open(path, encoding="utf-8") as fp:
            payload = json.load(fp)
    except Exception as e:
        raise PretriggerInputError(f"{label} cache unreadable ({path}): {e}")
    sectors = payload.get("sectors")
    if not isinstance(sectors, dict):
        raise PretriggerInputError(f"{label} cache has no `sectors` object: {path}")
    return sectors


def load_fred_snapshot(path: str | None = None) -> tuple[dict | None, str | None, str | None]:
    """回傳 (slim snapshot, unavailable_reason, generated_at)。

    FRED 缺席是合法狀態，不 raise。`generated_at` 一定要回傳並寫進輸出 —— 這支
    script 讀的是 `fred_latest.json`（**沒有日期版本**），跟 `--date` 沒有綁定關係：
    重放舊日期時用的是今天的 snapshot，而 daemon 停擺時用的是前幾天的。稽核檔不記
    這個時間就無法重現，也看不出 R4 是用哪一份資料判的。
    """
    p = path or FRED_CACHE
    if not os.path.exists(p):
        return None, f"fred cache missing: {p}", None
    try:
        with open(p, encoding="utf-8") as fp:
            raw = json.load(fp)
    except Exception as e:
        return None, f"fred cache unreadable: {e}", None
    if not isinstance(raw, dict):
        return None, "fred cache is not an object", None
    gen = raw.get("generated_at")
    return _slim_fred(raw), None, gen if isinstance(gen, str) else None


# ── 規則判定 ─────────────────────────────────────────────────────────────────
def eval_r4(hot: list[str], fred: dict | None, reason: str | None) -> dict:
    if fred is None:
        return {"fired": False, "available": False, "unavailable_reason": reason,
                "sectors": []}

    avoid = {canonicalize_sector_name(s, silent=True)
             for s in (fred.get("sector_rotation_avoid") or [])}

    # session 層條件：一旦成立，對**所有** HOT sector 都算 R4 衝突
    session_ev = []
    if fred.get("credit_stress_elevated") is True:
        session_ev.append({"field": "credit_stress_elevated", "value": True,
                           "cite": "credit_stress_elevated = true"})
    if fred.get("yield_curve_inverted") is True:
        yc = _num(fred.get("yield_curve_value"))
        session_ev.append({"field": "yield_curve_inverted", "value": True,
                           "cite": f"yield curve inverted (value {yc})"})
    rr = _num(fred.get("real_rate_preferred"))
    if rr is not None and rr > R4_REAL_RATE_THRESHOLD:
        session_ev.append({"field": "real_rate_preferred", "value": rr,
                           "cite": f"real_rate {rr}% > {R4_REAL_RATE_THRESHOLD}% threshold"})
    if fred.get("financial_stress_above_avg") is True:
        session_ev.append({"field": "financial_stress_above_avg", "value": True,
                           "cite": "financial_stress_above_avg = true"})
    label = fred.get("regime_label")
    if label in R4_ADVERSE_REGIMES:
        session_ev.append({"field": "regime_label", "value": label,
                           "cite": f"regime_label = {label}"})

    out = []
    for s in hot:
        ev = list(session_ev)
        if s in avoid:
            ev.append({"field": "sector_rotation_avoid", "value": s,
                       "cite": f"{s} ∈ FRED sector_rotation_avoid"})
        if ev:
            ev.sort(key=lambda e: R4_PRIORITY.index(e["field"])
                    if e["field"] in R4_PRIORITY else 99)
            out.append({"sector": s, "evidence": ev})
    return {"fired": bool(out), "available": True, "unavailable_reason": None,
            "sectors": out}


def _uncovered(hot: list[str], cache: dict, fields: tuple[str, ...],
               *, require_all: bool = False) -> list[str]:
    """HOT 裡這份 cache「未能判定」的板塊 —— key 層與值層一起看。

    **「這個板塊沒資料」與「這個板塊沒觸發」在輸出上必須分得出來。** 舊版一律
    `cache.get(s) or {}` → 全欄位 None → 不觸發、`available=true`，於是：
      - cache 被截斷或只含部分板塊 → 少發 challenge，全鏈路無人察覺
      - `--hot` 打錯字（"Tecnology"）或給了非 GICS 名（"Semiconductors"）→
        canonicalize 靜默 fallback 成原字串 → 三條規則全部回報「查過了，沒事」
    4.95.1 只擋到 key 層，同一類 bug 在值層復發（4.95.2）：`{"Utilities": null}`
    或訊號欄位全 null 的板塊，key 在、值判不了，一樣被讀成「查過了、乾淨」。
    所以覆蓋判定下沉到欄位層：entry 不是 object、或該規則實際讀的訊號欄位無一
    有效（`require_all` 時任一無效）→ 未能判定。
    整檔缺席已由 `_load_hard_cache` 擋成 rc=1；這裡補的是逐板塊、逐欄位兩層。
    """
    out = []
    for s in hot:
        d = cache.get(s)
        if not isinstance(d, dict):
            out.append(s)
            continue
        vals = [_num(d.get(f)) for f in fields]
        ok = (all(v is not None for v in vals) if require_all
              else any(v is not None for v in vals))
        if not ok:
            out.append(s)
    return out


def eval_r5(hot: list[str], smart: dict) -> dict:
    uncovered = _uncovered(hot, smart, R5_SIGNAL_FIELDS)
    out = []
    for s in hot:
        if s in uncovered:
            continue
        d = smart[s]
        ratio = _num(d.get("insider_acquired_disposed_ratio_q"))
        senate = _num(d.get("senate_net_buy_30d"))
        h_qoq = _num(d.get("institutional_holders_qoq_delta"))
        o_pct = _num(d.get("institutional_ownership_pct_delta"))
        n_inst = _num(d.get("institutional_sample_size")) or 0

        ev = []
        if ratio is not None and ratio < R5_INSIDER_RATIO_THRESHOLD:
            ev.append({"field": "insider_acquired_disposed_ratio_q", "value": ratio,
                       "cite": f"insider ratio {ratio} < {R5_INSIDER_RATIO_THRESHOLD}"})
        if senate is not None and senate < 0:
            ev.append({"field": "senate_net_buy_30d", "value": senate,
                       "cite": f"senate net {senate:+g} in 30d"})
        if (h_qoq is not None and h_qoq < 0 and o_pct is not None and o_pct < 0
                and n_inst >= R5_INSTITUTIONAL_MIN_SAMPLE):
            ev.append({"field": "institutional_qoq", "value": [h_qoq, o_pct, n_inst],
                       "cite": f"13F holders QoQ {h_qoq:+g}, ownership % {o_pct:+g} "
                               f"(n={int(n_inst)})"})

        # 與 consensus 一致 → 明確豁免（記錄下來，不是「沒資料」）
        # 缺席的欄位不得充當「已滿足」：豁免是一個對 DA 說「這裡查過了、確實乾淨」
        # 的宣稱，用不可知的 13F 欄位湊出來就是假證據（規則原文是三個條件皆須成立）。
        aligned = (ratio is not None and ratio > R5_INSIDER_ALIGNED_RATIO
                   and senate is not None and senate >= 0
                   and h_qoq is not None and h_qoq >= 0)
        if ev:
            out.append({"sector": s, "evidence": ev})
        elif aligned:
            out.append({"sector": s, "exempt": "smart money 與 consensus 一致（不挑）",
                        "evidence": []})
    fired = [o for o in out if o.get("evidence")]
    return {"fired": bool(fired), "available": True, "unavailable_reason": None,
            "sectors": fired,
            "uncovered": uncovered,
            "exempt": [o for o in out if not o.get("evidence")]}


def eval_r6(hot: list[str], pulse: dict) -> dict:
    uncovered = _uncovered(hot, pulse, R6_SIGNAL_FIELDS, require_all=True)
    out = []
    for s in hot:
        if s in uncovered:
            continue
        d = pulse[s]
        upside = _num(d.get("analyst_pt_upside_median_pct"))
        n = _num(d.get("pt_sample_size")) or 0
        if upside is not None and upside < R6_PT_UPSIDE_THRESHOLD and n >= R6_PT_MIN_SAMPLE:
            out.append({"sector": s, "evidence": [{
                "field": "analyst_pt_upside_median_pct", "value": upside,
                "cite": f"PT median upside {_pct(upside, 1)} < "
                        f"{R6_PT_UPSIDE_THRESHOLD * 100:.0f}% across {int(n)} names"}]})
    return {"fired": bool(out), "available": True, "unavailable_reason": None,
            "sectors": out, "uncovered": uncovered}


def eval_r7(hot: list[str], val: dict) -> dict:
    # R7 需要三個窗口同時有值才判得了「有／沒有」反轉 —— 缺任何一格都是未判定。
    uncovered = _uncovered(hot, val, R7_SIGNAL_FIELDS, require_all=True)
    out = []
    for s in hot:
        if s in uncovered:
            continue
        d = val[s]
        m3 = _num(d.get("rs_vs_spy_3m"))
        d20 = _num(d.get("rs_vs_spy_20d"))
        d5 = _num(d.get("rs_vs_spy_5d"))
        if m3 is not None and d20 is not None and d5 is not None \
                and m3 > R7_RS_3M_THRESHOLD and d20 < 0 and d5 < 0:
            out.append({"sector": s, "evidence": [{
                "field": "rs_multi_window", "value": [m3, d20, d5],
                "cite": f"3M RS {_pct(m3, 1)} but 20d {_pct(d20, 1)} / "
                        f"5d {_pct(d5, 1)} — short-term reversal"}]})
    return {"fired": bool(out), "available": True, "unavailable_reason": None,
            "sectors": out, "uncovered": uncovered}


def build_prompt_block(rules: dict, fred_generated_at: str | None = None) -> str:
    """組可逐字 paste 的 `<TRIGGERED_DIVERGENCE_RULES>` 內容。"""
    parts = []
    for rid in ("R4", "R5", "R6", "R7"):
        r = rules[rid]
        if not r["fired"]:
            continue
        lines = [RULE_LIBRARY[rid], "  命中："]
        for hit in r["sectors"]:
            cites = "；".join(e["cite"] for e in hit["evidence"])
            lines.append(f"    - {hit['sector']}: {cites}")
        if rid == "R4" and fred_generated_at:
            # `fred_latest.json` 沒有日期版本、與掃描日無綁定 —— R4 引了它的數值，
            # 資料時點就要跟著上 prompt。--prompt-only 是 PS 實際 paste 的那條路，
            # 只寫進 JSON 等於沒說。
            lines.append(f"  （判定用 FRED snapshot generated_at={fred_generated_at}）")
        parts.append("\n".join(lines))

    unavailable = [rid for rid in ("R4", "R5", "R6", "R7") if not rules[rid]["available"]]
    # 逐板塊缺資料：整條規則仍 available，但某些 HOT sector 根本不在 cache 裡。
    uncovered = {rid: rules[rid].get("uncovered") or []
                 for rid in ("R4", "R5", "R6", "R7")}
    uncovered = {k: v for k, v in uncovered.items() if v}

    if not parts:
        body = NO_TRIGGER_TEXT
    else:
        body = "\n\n".join(parts)
    if unavailable:
        # 「資料缺席」與「沒觸發」必須讓 DA 分得出來 —— 前者是未知，不是安全。
        body += ("\n\n⚠️ 下列規則因資料缺席**未能判定**（不等於未觸發）："
                 + "、".join(f"{r}（{rules[r]['unavailable_reason']}）" for r in unavailable))
    if uncovered:
        body += ("\n\n⚠️ 下列 HOT sector 在對應 cache 中**無可判定資料**（板塊缺席、"
                 "null 佔位、或該規則的訊號欄位缺格），該規則對它**未能判定**"
                 "（不等於未觸發；先確認 sector 名稱是否正確、cache 是否完整）："
                 + "；".join(f"{rid}: {', '.join(v)}" for rid, v in uncovered.items()))
    return body


def run(hot_sectors: list[str], *, scan_date: str, cache_dir: str | None = None,
        fred_path: str | None = None) -> dict:
    cdir = cache_dir or CACHE_DIR
    hot = []
    for s in hot_sectors:
        c = canonicalize_sector_name(s, silent=True)
        if c not in hot:
            hot.append(c)

    smart = _load_hard_cache(os.path.join(cdir, f"sector_smart_money_{scan_date}.json"),
                             "smart_money")
    pulse = _load_hard_cache(os.path.join(cdir, f"sector_earnings_pulse_{scan_date}.json"),
                             "earnings_pulse")
    val = _load_hard_cache(os.path.join(cdir, f"sector_valuation_{scan_date}.json"),
                           "valuation")
    fred, fred_reason, fred_generated_at = load_fred_snapshot(fred_path)

    rules = {
        "R4": eval_r4(hot, fred, fred_reason),
        "R5": eval_r5(hot, smart),
        "R6": eval_r6(hot, pulse),
        "R7": eval_r7(hot, val),
    }
    fired_ids = [r for r in ("R4", "R5", "R6", "R7") if rules[r]["fired"]]
    # HOT 名字打錯／非 GICS 名的訊號：三份 cache 都不認得它。
    unknown_sectors = sorted({s for s in hot
                              if s not in smart and s not in pulse and s not in val})
    return {
        "schema": SCHEMA,
        "producer_version": PRODUCER_VERSION,
        "scan_date": scan_date,
        "hot_sectors": hot,
        "unknown_sectors": unknown_sectors,
        # fred_latest.json 沒有日期版本，與 scan_date 無綁定關係 —— 記下實際用的
        # 那一份是哪時候產的，稽核檔才重現得出 R4 的判定。
        "fred_generated_at": fred_generated_at,
        "rules": rules,
        "triggers_fired": fired_ids,
        "any_fired": bool(fired_ids),
        "prompt_block": build_prompt_block(rules, fred_generated_at),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Phase 4b DA 的 R4–R7 結構性 divergence 預判（零新計算）")
    ap.add_argument("--date", default=_date.today().isoformat(), help="YYYY-MM-DD")
    ap.add_argument("--hot", required=True,
                    help="Phase 4a 提出的 HOT sectors，逗號分隔")
    ap.add_argument("--cache-dir", default=None, help="覆寫 sector/cache（測試用）")
    ap.add_argument("--fred", default=None, help="覆寫 fred_latest.json 路徑")
    ap.add_argument("--prompt-only", action="store_true",
                    help="只印 prompt_block（可直接 paste 進 DA prompt）")
    args = ap.parse_args()

    hot = [s.strip() for s in args.hot.split(",") if s.strip()]
    if not hot:
        # 錯誤一律走 stderr：stdout 的契約是「逐字 paste 進 DA prompt」，
        # 忘了看 rc 的 pipeline 會把錯誤 JSON 貼進 <TRIGGERED_DIVERGENCE_RULES>。
        print(json.dumps({"error": "--hot 不得為空"}, ensure_ascii=False), file=sys.stderr)
        return 1

    try:
        rec = run(hot, scan_date=args.date, cache_dir=args.cache_dir, fred_path=args.fred)
    except PretriggerInputError as e:
        print(json.dumps({"error": str(e), "schema": SCHEMA}, ensure_ascii=False),
              file=sys.stderr)
        return 1

    if args.prompt_only:
        print(rec["prompt_block"])
    else:
        print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

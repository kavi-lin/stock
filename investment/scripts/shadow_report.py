#!/usr/bin/env python3
"""shadow_report.py — V3.46.1 shadow-experiment readout + dispersion backfill.

V3.45.x–3.46.0 建了 3 個 shadow 實驗，退出條件都是「≥N session 後出報告 → user 拍 → 切 live」，
但之前沒有任何 script 會算這個報告 — 本檔補上讀出端（#10 anchor 校準 cron 的前半身）：

  1. #2  dispersion backfill — 對歷史 entries 的 fair_value_summary.anchors 重算 CV 分布
         → 用真實分布校準 agreement_grade 門檻（取代拍腦袋的 0.15/0.35）。**立刻有數據**（不用等累積）。
  2. #6  oe_mult shadow    — 若 live 改用 oe_mult_rate_linked，verdict_band 翻轉率（checkpoint: 20 session, <15% 切換）
  3. #3  archetype shadow  — valuation_archetype_shadow.flip_vs_live 翻轉率（checkpoint: 20 session）
  4. #4  news PT 去重監測  — news_score 分布 vs baseline {-1:1,0:2,1:6,2:18,3:4} + pt_leakage 累積率（凍結窗: 10 session）

數學 import 自 compute_price_framework（單一事實來源，不複製公式）。
唯讀：不碰 history.json、不碰任何 locked 欄位。輸出 stdout 摘要 + reports/SHADOW_REPORT_<date>.md。

Usage:
  python3 investment/scripts/shadow_report.py            # stdout + MD report
  python3 investment/scripts/shadow_report.py --json     # machine-readable JSON to stdout
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE, "investment", "scripts"))
INVEST_LOGS = os.path.join(BASE, "investment", "invest_logs")
HISTORY_JSON = os.path.join(INVEST_LOGS, "history.json")
REPORTS_DIR = os.path.join(BASE, "reports")

from compute_price_framework import (  # noqa: E402 — single source of truth
    ANCHOR_WEIGHTS,
    FWD_PE_CLAMP,
    _pos,
    _verdict_band,
    weighted_mean,
    weighted_std,
)

NEWS_BASELINE = {-1: 1, 0: 2, 1: 6, 2: 18, 3: 4}   # n=31 @ V3.45.4 切換前
OE_CHECKPOINT_N, OE_FLIP_MAX = 20, 0.15
ARCHETYPE_CHECKPOINT_N = 20
NEWS_FREEZE_N = 10
OE_STATIC_MULT = 15.0
# L5（V4.91.0）— Sentiment det producer 的停止規則。形狀照 ARCHETYPE_CHECKPOINT_N：
# 具名常數，不是「跑一跑再看感覺」。Sentiment 沒有 L4b 那種 discovery 暖機問題
# （輸入全部來自既有 bundle，第一個 session 就是穩態），所以直接數 session 數即可。
SENTIMENT_CHECKPOINT_N = 20
# 翻預設的門檻：det 與 LLM 的 signal 方向（正/中性/負）不一致率。分數本身有連續值差異
# 是預期的（det 拿掉了 LLM 的規則表外因子），真正要問的是「方向會不會翻」。
SENTIMENT_DIRECTION_FLIP_MAX = 0.20
# 中性帶：|score| ≤ 此值視為 NEUTRAL。這同樣是 L5「填規格空白」的一格 —— 而且是直接
# 決定翻轉率（＝翻預設判準的分子）的那一格，所以與 STOCK_CLAMP 同級待遇：具名、可
# 一行改、有測試釘住。留成 magic number 等於讓判準的一半沒人看得見（4.95.1 review）。
SENTIMENT_NEUTRAL_BAND = 0.5
# V4.108.0 — FWD_PE_CLAMP 校準的最小樣本。比其他 checkpoint 小得多，因為母體不是
# 「累積的 session」而是「已分析過的標的」——pf_quant 每次 Phase 1.5 都產出，包含
# shadow 狀態的觀測，所以第一天就有數字可看。5 檔以下不出判準，避免單一標的主導。
FWD_PE_CALIB_MIN_N = 5


def _trades(history):
    for e in history:
        for t in (e.get("trades_this_session") or []):
            yield e.get("date") or e.get("session_date"), t


def _blend(anchors: dict):
    """V5.0 blend (weights redistribution) → (wfv, verdict) or (None, None)."""
    avail = {k: _pos(anchors.get(k)) for k in ANCHOR_WEIGHTS}
    avail = {k: v for k, v in avail.items() if v is not None}
    if not avail:
        return None, None
    tw = sum(ANCHOR_WEIGHTS[k] for k in avail)
    wfv = sum(ANCHOR_WEIGHTS[k] / tw * avail[k] for k in avail)
    return wfv, None  # verdict needs price — caller computes


def section_dispersion(history) -> dict:
    """#2 backfill — CV over every historical entry that has anchors."""
    rows = []
    for d, t in _trades(history):
        fvs = t.get("fair_value_summary") or {}
        anchors = fvs.get("anchors")
        if not isinstance(anchors, dict):
            continue
        avail = {k: _pos(anchors.get(k)) for k in ANCHOR_WEIGHTS}
        avail = {k: v for k, v in avail.items() if v is not None}
        if len(avail) < 2:
            continue
        tw = sum(ANCHOR_WEIGHTS[k] for k in avail)
        vals = list(avail.values())
        wts = [ANCHOR_WEIGHTS[k] / tw for k in avail]
        m = weighted_mean(vals, wts)
        s = weighted_std(vals, wts)
        cv = s / m if m else None
        if cv is not None:
            rows.append({"date": d, "ticker": t.get("ticker"), "cv": round(cv, 4),
                         "n_anchors": len(avail)})
    cvs = sorted(r["cv"] for r in rows)

    def _pct(q):
        if not cvs:
            return None
        i = q * (len(cvs) - 1)
        lo = int(i)
        return round(cvs[lo] + (cvs[min(lo + 1, len(cvs) - 1)] - cvs[lo]) * (i - lo), 4)

    return {
        "n": len(rows),
        "cv_min": cvs[0] if cvs else None,
        "cv_p33": _pct(1 / 3),
        "cv_median": _pct(0.5),
        "cv_p66": _pct(2 / 3),
        "cv_max": cvs[-1] if cvs else None,
        "current_thresholds": {"high_below": 0.15, "low_above": 0.35},
        "suggested_thresholds": {"high_below": _pct(1 / 3), "low_above": _pct(2 / 3)},
        "rows": rows,
        "note": "建議門檻 = 歷史 CV 33/66 percentile（三等分 high/medium/low）。#2 cap 接線前由 user 核可。",
    }


def section_oe_shadow(history) -> dict:
    """#6 — 重 blend：owner_earnings anchor 換 rate_linked 倍數 → verdict 翻轉率。"""
    rows, flips = [], 0
    for d, t in _trades(history):
        fvr = t.get("fair_value_range") or {}
        sh = fvr.get("owner_earnings_multiple_shadow") or {}
        m_linked = _pos(sh.get("oe_mult_rate_linked"))
        fvs = t.get("fair_value_summary") or {}
        anchors = fvs.get("anchors")
        cp = _pos(fvs.get("current_price"))
        oe_anchor = _pos((anchors or {}).get("owner_earnings_mult"))
        live_verdict = fvs.get("verdict_band")
        if not (m_linked and isinstance(anchors, dict) and cp and oe_anchor and live_verdict):
            continue
        relinked = dict(anchors)
        relinked["owner_earnings_mult"] = oe_anchor / OE_STATIC_MULT * m_linked
        wfv, _ = _blend(relinked)
        if wfv is None:
            continue
        v2 = _verdict_band((wfv - cp) / cp * 100)
        flip = v2 != live_verdict
        flips += flip
        rows.append({"date": d, "ticker": t.get("ticker"), "live": live_verdict,
                     "rate_linked": v2, "flip": flip})
    n = len(rows)
    rate = round(flips / n, 4) if n else None
    return {
        "n": n, "checkpoint_n": OE_CHECKPOINT_N, "flips": flips, "flip_rate": rate,
        "decision": (None if n < OE_CHECKPOINT_N else
                     ("propose_switch" if rate < OE_FLIP_MAX else "keep_static_pending_backtest")),
        "rows": rows,
        "note": f"checkpoint: ≥{OE_CHECKPOINT_N} session 且翻轉率 <{OE_FLIP_MAX:.0%} → 切換提案",
    }


def section_archetype(history) -> dict:
    """#3 — flip_vs_live 累積 + archetype 分布。"""
    rows = []
    arch_counter, flips = Counter(), 0
    for d, t in _trades(history):
        vas = t.get("valuation_archetype_shadow")
        if not isinstance(vas, dict) or vas.get("flip_vs_live") is None:
            continue
        arch_counter[vas.get("archetype")] += 1
        flips += bool(vas["flip_vs_live"])
        rows.append({"date": d, "ticker": t.get("ticker"), "archetype": vas.get("archetype"),
                     "live": (t.get("fair_value_summary") or {}).get("verdict_band"),
                     "shadow": vas.get("verdict_band_shadow"), "flip": vas["flip_vs_live"]})
    n = len(rows)
    return {
        "n": n, "checkpoint_n": ARCHETYPE_CHECKPOINT_N,
        "flips": flips, "flip_rate": round(flips / n, 4) if n else None,
        "archetype_distribution": dict(arch_counter),
        "rows": rows,
        "note": f"checkpoint: ≥{ARCHETYPE_CHECKPOINT_N} session → 翻轉率報告 → user 拍 → #3b 切 live（含 cap/T5 接線）",
    }


def section_news(history) -> dict:
    """#4 — post-切換 news_score 分布 vs baseline + leakage 率 + 凍結窗進度。"""
    post_scores, leak_hits, leak_scanned = [], 0, 0
    for d, t in _trades(history):
        nl = t.get("news_lane") or {}
        is_post = isinstance(nl.get("pt_revision_momentum"), dict)   # 3.45.4 之後才有
        ds = t.get("det_shadow") or {}
        if ds.get("news_pt_leakage") is not None:
            leak_scanned += 1
            leak_hits += bool(ds["news_pt_leakage"])
        if is_post and isinstance((t.get("lane_scores") or {}).get("news"), int):
            post_scores.append(t["lane_scores"]["news"])
    dist = dict(sorted(Counter(post_scores).items()))
    n = len(post_scores)
    base_n = sum(NEWS_BASELINE.values())
    base_mean = sum(k * v for k, v in NEWS_BASELINE.items()) / base_n
    post_mean = round(sum(post_scores) / n, 3) if n else None
    return {
        "n_post": n, "freeze_window_n": NEWS_FREEZE_N,
        "freeze_remaining": max(0, NEWS_FREEZE_N - n),
        "baseline_distribution": {str(k): v for k, v in NEWS_BASELINE.items()},
        "baseline_mean": round(base_mean, 3),
        "post_distribution": {str(k): v for k, v in dist.items()},
        "post_mean": post_mean,
        "mean_shift": round(post_mean - base_mean, 3) if post_mean is not None else None,
        "leakage_scanned": leak_scanned, "leakage_hits": leak_hits,
        "leakage_rate": round(leak_hits / leak_scanned, 4) if leak_scanned else None,
        "note": "預期 post mean 較 baseline 下移（PT +1 源移除）；下移 ≈ 證實 PT 曾在計分。凍結窗滿後恢復 News weight 調整。",
    }


def _direction(x):
    """分數 → 方向。翻預設看的是方向翻轉率而不是分數差：det 拿掉了 LLM 的規則表外
    因子，連續值本來就會差，但「該不該偏多」翻掉才是決策層真的會感覺到的事。"""
    # bool 也是 int —— 契約那格若被寫成 True，`True > 0.5` 會安靜地判成 POS 並進樣本。
    # NaN 的兩個帶寬比較都回 False → 會判成假 NEUTRAL 進樣本，同樣擋掉。
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        return None
    if x > SENTIMENT_NEUTRAL_BAND:
        return "POS"
    if x < -SENTIMENT_NEUTRAL_BAND:
        return "NEG"
    return "NEUTRAL"


def section_sentiment_det(history) -> dict:
    """L5 — Sentiment det producer vs LLM lane score（shadow 累積）。

    樣本來源刻意用 `lane_contract.lanes.sentiment.shadow_score` 而不是 `sentiment_det`
    block：契約那一格是 validator 驗過的（§15 值域 + 保留域），block 是 PM 抄進去的原始
    輸出。兩者相等時無差別，不等時該信驗過的那個。
    """
    rows, flips, band_mismatches = [], 0, 0
    for d, t in _trades(history):
        lc = t.get("lane_contract")
        if not isinstance(lc, dict):
            continue
        sent = (lc.get("lanes") or {}).get("sentiment")
        det = (sent or {}).get("shadow_score") if isinstance(sent, dict) else None
        llm = (t.get("lane_scores") or {}).get("sentiment")
        # bool 一律排除（`isinstance(True, int)` 為真）、NaN/inf 一律排除（NaN 會在
        # `_direction` 變假 NEUTRAL）：混進來都是方向可疑的樣本，而樣本數正是翻預設
        # 判準的分母。
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) for v in (det, llm)):
            continue
        d_dir, l_dir = _direction(det), _direction(llm)
        # 「方向翻轉」只數真的對翻（POS↔NEG）。LLM lane score 是整數（±1 起跳，
        # 除 0 外必落在中性帶外），det 是連續值——「LLM +1 vs det +0.45」這種溫和
        # 同向若也算翻轉，溫和情緒的個股會單靠帶寬把翻轉率頂在門檻上方，判準量到
        # 的變成帶寬而不是方向。NEUTRAL↔方向性是帶寬層的不一致，另計
        # `band_mismatch`：報表看得到、不進翻預設判準的分子。
        flip = d_dir != l_dir and "NEUTRAL" not in (d_dir, l_dir)
        band_mismatch = d_dir != l_dir and not flip
        flips += flip
        band_mismatches += band_mismatch
        sd = t.get("sentiment_det") or {}
        rows.append({"date": d, "ticker": t.get("ticker"),
                     "llm": llm, "det": round(float(det), 4),
                     "delta": round(float(det) - float(llm), 4),
                     "llm_dir": l_dir, "det_dir": d_dir, "flip": flip,
                     "band_mismatch": band_mismatch,
                     "missing_inputs": len(sd.get("missing_inputs") or [])})
    n = len(rows)
    rate = round(flips / n, 4) if n else None
    deltas = [abs(r["delta"]) for r in rows]
    return {
        "n": n, "checkpoint_n": SENTIMENT_CHECKPOINT_N,
        "direction_flips": flips, "direction_flip_rate": rate,
        "band_mismatches": band_mismatches,
        "band_mismatch_rate": round(band_mismatches / n, 4) if n else None,
        "flip_max": SENTIMENT_DIRECTION_FLIP_MAX,
        "mean_abs_delta": round(sum(deltas) / n, 3) if n else None,
        "max_abs_delta": round(max(deltas), 3) if deltas else None,
        "decision": (None if n < SENTIMENT_CHECKPOINT_N else
                     ("propose_switch" if rate is not None and rate < SENTIMENT_DIRECTION_FLIP_MAX
                      else "keep_llm_pending_review")),
        "rows": rows,
        "note": (f"checkpoint: ≥{SENTIMENT_CHECKPOINT_N} 筆 shadow 樣本（1 筆 = 一支個股的"
                 f"一次分析，非 session 數）且方向翻轉率（POS↔NEG 對翻）"
                 f"<{SENTIMENT_DIRECTION_FLIP_MAX:.0%} → 翻預設提案（**需使用者拍板**）。"
                 "翻後照 V3.45.4 News 前例上 weight 凍結窗。det 拿掉了 LLM 的規則表外因子，"
                 "分數差異是預期的；band_mismatch（NEUTRAL↔方向性）另列——它量的是帶寬"
                 "不是方向，集中出現時該檢討 SENTIMENT_NEUTRAL_BAND 而不是擋翻預設。"
                 "另看 missing_inputs 是否集中在同幾檔。"),
    }


def section_fwd_pe_calibration(artifact_dir: str = INVEST_LOGS) -> dict:
    """V4.108.0 — `FWD_PE_CLAMP` 上限的校準讀出端。

    **反解**每檔標的的市場隱含 justified PE：把 anchor 公式倒過來，
        implied_pe = price × (1 + discount_rate)^horizon_years ÷ target_eps
    ——同一個目標年度 EPS、同一個折現率下，市場實際付的倍數是多少。

    為什麼不讀 history.json（其餘 section 都讀它）：那要等 session 累積，而這個問題
    **今天**就該有答案。`<DATE>_<TICKER>_pf_quant.json` 在每次 Phase 1.5 都會產出，
    且對 shadow（ineligible）狀態的 anchor 一樣留有完整 calibration——那正是我們要的
    母體：live 與 shadow 的觀測都是「市場付多少倍」的有效樣本。

    為什麼不能用「錨自己的輸出分布」來校準（#2 dispersion 那套 percentile 手法在此
    不適用）：`agreement_grade` 的門檻是描述性的，切在它所描述的那個分布上；PE clamp
    是**因果**參數，直接決定輸出——拿它自己的輸出來校準它會循環。市場隱含 PE 是外生的，
    所以它才是合法的校準標的。

    ⚠ 限制：`market_implied_pe` 是「**在我們假設的折現率下**市場付的倍數」，不是無假設
    的市場觀測——折現率變了它就跟著變（SPCX 的 beta 修正把 r 從 10% 拉到 16.9%，隱含 PE
    同步 38.8→45.3）。所以這個量尺隔離的是**倍數假設**，前提是折現率假設另外成立；
    折現率本身要看 `beta_fallback_rate` 與 `discount_clamp_binding_n` 兩個欄位。
    """
    rows = []
    try:
        files = sorted(f for f in os.listdir(artifact_dir) if f.endswith("_pf_quant.json"))
    except OSError:
        files = []
    for fname in files:
        try:
            with open(os.path.join(artifact_dir, fname), encoding="utf-8") as f:
                art = json.load(f)
            pack = (art.get("quant_blocks") or {}).get("valuation_pack") or {}
            entry = (pack.get("anchors") or {}).get("fwd_earnings_discounted") or {}
            cal = entry.get("calibration") or {}
            price = _pos(pack.get("current_price"))
            eps = _pos(cal.get("target_eps"))
            r, hz = cal.get("discount_rate"), cal.get("horizon_years")
        except Exception:
            continue
        if not (price and eps and isinstance(r, (int, float)) and isinstance(hz, (int, float))):
            continue
        rows.append({
            "ticker": art.get("ticker") or fname.split("_")[1],
            "date": fname[:10],
            "status": entry.get("status"),
            "target_fy": cal.get("target_fiscal_year"),
            "market_implied_pe": round(price * (1 + r) ** hz / eps, 1),
            "our_pe": cal.get("justified_pe"),
            "pe_raw": cal.get("justified_pe_raw"),
            "clamp": cal.get("pe_clamp_binding"),
            "beta_used": cal.get("beta_used"),
            "beta_source": cal.get("beta_source"),
            "r_clamp": cal.get("discount_clamp_binding"),
            "anchor_value": entry.get("value"),
            "price": price,
        })
    # 同一檔多天重跑只留最新一筆，否則常分析的標的會主導母體
    latest = {}
    for r in sorted(rows, key=lambda x: x["date"]):
        latest[r["ticker"]] = r
    rows = sorted(latest.values(), key=lambda x: x["ticker"])

    lo_c, hi_c = FWD_PE_CLAMP

    def _cohort(subset: list) -> dict:
        pes = sorted(r["market_implied_pe"] for r in subset)

        def _pct(q):
            if not pes:
                return None
            i = q * (len(pes) - 1)
            lo = int(i)
            return round(pes[lo] + (pes[min(lo + 1, len(pes) - 1)] - pes[lo]) * (i - lo), 1)

        return {
            "n": len(pes),
            "implied_pe_min": pes[0] if pes else None,
            "implied_pe_p33": _pct(1 / 3),
            "implied_pe_median": _pct(0.5),
            "implied_pe_p66": _pct(2 / 3),
            "implied_pe_max": pes[-1] if pes else None,
            "in_band": sum(1 for p in pes if lo_c <= p <= hi_c),
            "above_upper": sum(1 for p in pes if p > hi_c),
            "below_lower": sum(1 for p in pes if p < lo_c),
        }

    live_rows = [r for r in rows if r["status"] == "eligible"]
    all_c, live_c = _cohort(rows), _cohort(live_rows)
    upper_hits = sum(1 for r in rows if r["clamp"] == "upper")

    # 判準只看 live cohort。全母體混了 archetype——MSFT 與 NET 的隱含倍數差一個量級，
    # 混在一起的分位數沒有意義。archetype 欄位不能拿來分層：它依賴 earnings-analyst
    # cache，實測 11 檔有 6 檔是 `balanced / rule=no_inputs`（缺輸入，不是真的不屬於
    # hypergrowth），拿它過濾會靜默丟掉多數樣本。anchor 自己的 scope 判定則是引擎算的、
    # 必然存在，而且定義上就等於「這根錨真正服務的母體」。
    verdict = None
    if live_c["n"] >= FWD_PE_CALIB_MIN_N:
        if hi_c < live_c["implied_pe_p33"]:
            verdict = "upper_clamp_structurally_bearish"
        elif hi_c > live_c["implied_pe_p66"]:
            verdict = "upper_clamp_structurally_bullish"
        else:
            verdict = "upper_clamp_centered"
    # beta fallback 率是資料品質訊號，不是校準參數：它數的是「FMP 給不出可用 beta」
    # 的頻率（新上市標的居多）。偏高代表這根錨的折現率有相當比例是靠母體中位數撐的，
    # 那時該回頭重新量測 FWD_BETA_FALLBACK，而不是繼續沿用舊值。
    beta_fb = sum(1 for r in rows if r["beta_source"] == "population_median_fallback")
    r_clamp_hits = sum(1 for r in rows if r["r_clamp"])
    return {
        "n": len(rows), "n_live": live_c["n"],
        "all_cohort": all_c, "live_cohort": live_c,
        "current_clamp": {"lower": lo_c, "upper": hi_c},
        "upper_clamp_binding_n": upper_hits,
        "upper_clamp_binding_rate": round(upper_hits / len(rows), 4) if rows else None,
        "beta_fallback_n": beta_fb,
        "beta_fallback_rate": round(beta_fb / len(rows), 4) if rows else None,
        "discount_clamp_binding_n": r_clamp_hits,
        "suggested_upper": live_c["implied_pe_median"],
        "verdict": verdict,
        "min_n_for_verdict": FWD_PE_CALIB_MIN_N,
        "rows": rows,
        "note": ("上限校準判準 = **live cohort** 的市場隱含 PE P33–P66 是否包住現行上限"
                 "（包住 = 對中位數標的不帶方向）。全母體那組只是背景脈絡，混了 archetype，"
                 "不可當校準目標。**不可自動跟隨中位數**：泡沫期中位數上移、上限跟著上移，"
                 "錨就永遠不會說貴——與 agreement_grade 同紀律，改值一律 user 核准。"),
    }


def section_lane_sentinel(history) -> dict:
    """V4.0.0 — model 分層哨兵：近 10 session lane score 分布 vs 全歷史 baseline +
    det_shadow agreement 異常率。Sent/News/Tech 降 Sonnet 後盯這段。"""
    rows = []
    for d, t in _trades(history):
        ls = t.get("lane_scores")
        if not isinstance(ls, dict):
            continue
        ds = t.get("det_shadow") or {}
        rows.append({"date": d, "scores": ls,
                     "val_agree": ds.get("val_agreement"),
                     "polar": ds.get("signal_polarization")})
    recent, base = rows[-10:], rows
    out = {"n_recent": len(recent), "n_baseline": len(base), "lanes": {}}
    for lane in ("fundamentals", "sentiment", "news", "technical"):
        bvals = [r["scores"].get(lane) for r in base if isinstance(r["scores"].get(lane), (int, float))]
        rvals = [r["scores"].get(lane) for r in recent if isinstance(r["scores"].get(lane), (int, float))]
        bm = round(sum(bvals) / len(bvals), 2) if bvals else None
        rm = round(sum(rvals) / len(rvals), 2) if rvals else None
        out["lanes"][lane] = {
            "baseline_mean": bm, "recent10_mean": rm,
            "drift": round(rm - bm, 2) if bm is not None and rm is not None else None,
        }
    bad_agree = sum(1 for r in recent if r["val_agree"] == "DISAGREE")
    bad_polar = sum(1 for r in recent if r["polar"] in ("BIPOLAR", "OUTLIER"))
    out["recent10_val_disagree"] = bad_agree
    out["recent10_polar_anomaly"] = bad_polar
    out["note"] = ("哨兵規則：降級 lane 的 |drift| 明顯 > 其他 lane、或 DISAGREE/BIPOLAR 率"
                   "較歷史升 → 該 lane 改回 inherit（V4.0.0 Phase 2 model 分層表）")
    return out


def render_md(rep: dict) -> str:
    d, oe, ar, nw = rep["dispersion"], rep["oe_shadow"], rep["archetype_shadow"], rep["news_pt_dedup"]
    L = [f"# Shadow Report — {rep['generated']}", "",
         f"> 唯讀讀出端。history entries scanned: {rep['entries_scanned']}。", "",
         "## #2 Anchor Dispersion（backfill — 立即可用）", "",
         f"- 樣本 n={d['n']}，CV min/P33/median/P66/max = "
         f"{d['cv_min']} / {d['cv_p33']} / {d['cv_median']} / {d['cv_p66']} / {d['cv_max']}",
         f"- 現行門檻 high<{d['current_thresholds']['high_below']} / low>{d['current_thresholds']['low_above']}（拍腦袋初值）",
         f"- **建議門檻（33/66 pct）**: high<{d['suggested_thresholds']['high_below']} / low>{d['suggested_thresholds']['low_above']}",
         f"- {d['note']}", "",
         "## #6 Owner-Earnings 倍數 shadow", "",
         f"- 累積 {oe['n']}/{oe['checkpoint_n']} session；翻轉 {oe['flips']} 筆"
         f"（rate={oe['flip_rate']}）；decision: **{oe['decision'] or 'accumulating'}**",
         f"- {oe['note']}", "",
         "## #3 Valuation Archetype shadow", "",
         f"- 累積 {ar['n']}/{ar['checkpoint_n']} session；翻轉率 {ar['flip_rate']}；"
         f"archetype 分布 {ar['archetype_distribution']}",
         f"- {ar['note']}", "",
         "## #4 News PT 去重監測", "",
         f"- post-切換 {nw['n_post']} session（凍結窗剩 {nw['freeze_remaining']}）",
         f"- baseline mean {nw['baseline_mean']} → post mean {nw['post_mean']}（shift {nw['mean_shift']}）",
         f"- 分布 baseline {nw['baseline_distribution']} → post {nw['post_distribution']}",
         f"- leakage: {nw['leakage_hits']}/{nw['leakage_scanned']}（rate={nw['leakage_rate']}）",
         f"- {nw['note']}", ""]
    sd = rep.get("sentiment_det") or {}
    if sd:
        L += ["## L5 Sentiment deterministic shadow", "",
              f"- 累積 {sd['n']}/{sd['checkpoint_n']} 筆樣本；方向翻轉 {sd['direction_flips']} 筆"
              f"（rate={sd['direction_flip_rate']}，門檻 <{sd['flip_max']:.0%}）；"
              f"decision: **{sd['decision'] or 'accumulating'}**",
              f"- |det − LLM| 平均 {sd['mean_abs_delta']}／最大 {sd['max_abs_delta']}",
              f"- {sd['note']}", ""]
        if sd["rows"]:
            L += ["| 日期 | ticker | LLM | det | Δ | 方向 | missing |", "|---|---|---|---|---|---|---|"]
            L += [f"| {r['date']} | {r['ticker']} | {r['llm']} | {r['det']} | {r['delta']:+} "
                  f"| {r['llm_dir']}→{r['det_dir']}{' ⚠' if r['flip'] else ''} | {r['missing_inputs']} |"
                  for r in sd["rows"][-15:]]
            L += [""]

    fp = rep.get("fwd_pe_calibration") or {}
    if fp:
        fp_verdict = (fp["verdict"] or
                      f"accumulating（live cohort {fp['n_live']}/{fp['min_n_for_verdict']}）")
        ac, lc = fp["all_cohort"], fp["live_cohort"]
        L += ["## FWD_PE_CLAMP 校準（V4.108.0 — 反解市場隱含 PE，立即可用）", "",
              f"- 來源 `*_pf_quant.json`（同標的取最新一次）；全母體 n={fp['n']}，"
              f"其中 anchor live **n={fp['n_live']}**",
              f"- **live cohort**（判準來源）隱含 PE min/P33/median/P66/max = "
              f"{lc['implied_pe_min']} / {lc['implied_pe_p33']} / {lc['implied_pe_median']} / "
              f"{lc['implied_pe_p66']} / {lc['implied_pe_max']}",
              f"- 全母體（背景脈絡，混 archetype，**不是**校準目標）= {ac['implied_pe_min']} / "
              f"{ac['implied_pe_p33']} / {ac['implied_pe_median']} / {ac['implied_pe_p66']} / "
              f"{ac['implied_pe_max']}；帶內 {ac['in_band']}/{ac['n']}，"
              f"高於上限 {ac['above_upper']}，低於下限 {ac['below_lower']}",
              f"- 現行 clamp [{fp['current_clamp']['lower']}, {fp['current_clamp']['upper']}]；"
              f"上限實際綁到 {fp['upper_clamp_binding_n']}/{fp['n']}"
              f"（rate={fp['upper_clamp_binding_rate']}）",
              f"- 折現率：beta fallback {fp['beta_fallback_n']}/{fp['n']}"
              f"（rate={fp['beta_fallback_rate']}，資料品質訊號——偏高就該重量 "
              "`FWD_BETA_FALLBACK`）；折現率 clamp 綁到 "
              f"{fp['discount_clamp_binding_n']}/{fp['n']}",
              f"- **判準**: {fp_verdict}"
              + (f"；若要改，live 中位數 {fp['suggested_upper']} 是參考值"
                 if fp["verdict"] else ""),
              f"- {fp['note']}", ""]
        if fp["rows"]:
            L += ["| ticker | 狀態 | 目標年 | 市場隱含 PE | 我們給的 PE | 未夾前 | clamp | anchor | 價 |",
                  "|---|---|---|---:|---:|---:|---|---:|---:|"]
            L += [f"| {r['ticker']} | {r['status']} | {(r['target_fy'] or '')[:7]} "
                  f"| {r['market_implied_pe']} | {r['our_pe']} | {r['pe_raw']} "
                  f"| {r['clamp'] or '—'} | {r['anchor_value']} | {r['price']} |"
                  for r in fp["rows"]]
            L += [""]

    sn = rep.get("lane_sentinel") or {}
    if sn:
        L += ["## Lane Model 分層哨兵（V4.0.0 — Sent/News/Tech → Sonnet 監測）", "",
              f"- 近 10 session（baseline n={sn['n_baseline']}）lane mean drift："]
        for lane, v in (sn.get("lanes") or {}).items():
            L.append(f"  - {lane}: baseline {v['baseline_mean']} → recent {v['recent10_mean']}"
                     f"（drift {v['drift']}）")
        L += [f"- 近 10 val DISAGREE: {sn['recent10_val_disagree']}；polarization 異常: {sn['recent10_polar_anomaly']}",
              f"- {sn['note']}", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Shadow experiment readout (V3.46.1, read-only)")
    ap.add_argument("--json", action="store_true", help="JSON to stdout, skip MD file")
    args = ap.parse_args()

    if not os.path.exists(HISTORY_JSON):
        print(json.dumps({"error": f"history.json not found: {HISTORY_JSON}"}))
        sys.exit(1)
    with open(HISTORY_JSON, encoding="utf-8") as f:
        history = json.load(f)

    rep = {
        "generated": date.today().isoformat(),
        "entries_scanned": len(history),
        "dispersion": section_dispersion(history),
        "oe_shadow": section_oe_shadow(history),
        "archetype_shadow": section_archetype(history),
        "news_pt_dedup": section_news(history),
        "sentiment_det": section_sentiment_det(history),
        "fwd_pe_calibration": section_fwd_pe_calibration(),
        "lane_sentinel": section_lane_sentinel(history),
    }

    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return

    md = render_md(rep)
    print(md)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    out = os.path.join(REPORTS_DIR, f"SHADOW_REPORT_{rep['generated']}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[shadow_report] written: {out}")


if __name__ == "__main__":
    main()

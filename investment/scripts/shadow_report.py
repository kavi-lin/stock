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
import os
import sys
from collections import Counter
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE, "investment", "scripts"))
HISTORY_JSON = os.path.join(BASE, "investment", "invest_logs", "history.json")
REPORTS_DIR = os.path.join(BASE, "reports")

from compute_price_framework import (  # noqa: E402 — single source of truth
    ANCHOR_WEIGHTS,
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

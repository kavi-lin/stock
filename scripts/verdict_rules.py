"""Verdict computation per source.

Maps (decision snapshot, reality measurement) -> {label, rationale}.
Each source has its own "did the call work" rule, but all collapse to
hit | miss | neutral | pending | n/a so the calendar UI is uniform.

Eval window per source (days):
"""

from __future__ import annotations
from typing import Any

EVAL_WINDOW_DAYS = {
    "deep-dive": 30,
    "sector-scan": 20,
    "news-digest": 5,
    "theme-detector": 10,
    "momentum-screen": 10,
    "thematic-screener": 5,
    "earnings-analyzer": 5,
    "short-term-weekly": 5,
    "postmortem": 0,
}

HIT_THRESHOLD_PCT = 2.0
MISS_THRESHOLD_PCT = -2.0

# TODO-011 (REVIEW_2026-05-24/05-31 盲點). News-digest scores a market-wide call
# against SPY, where the ±2.0% single-stock band is structurally unreachable in
# the digest window → every strong call got pinned to neutral (0% hit). Index-
# level band. Stopgap value (±1.0%): on the 7 strong-delta samples it recovers
# the one unambiguous correct call (2026-05-14 bearish, SPY −1.93%) without
# manufacturing false misses from sub-1% noise (±0.5% did). Re-calibrate once
# N≥15 strong-delta digests accumulate. Does NOT touch deep-dive's 2.0%.
NEWS_HIT_THRESHOLD_PCT = 1.0

# H-D (REVIEW_2026-06-13). The magnitude gate above pins 5/9 strong-delta digests
# to neutral because SPY rarely clears ±1% inside the digest window — so the bug is
# "magnitude vs direction", structural and independent of N. Noise floor below which
# SPY has no readable direction. Used ONLY by verdict_news_digest_directional (shadow).
NEWS_NOISE_FLOOR_PCT = 0.3


def _verdict_directional(direction: str, return_pct: float, threshold: float = HIT_THRESHOLD_PCT) -> tuple[str, str]:
    """Generic directional verdict for long/short calls."""
    direction = (direction or "").lower()
    if direction in ("buy", "long", "bullish"):
        if return_pct > threshold:
            return "hit", f"看多 → 實際 {return_pct:+.2f}%, 命中"
        if return_pct < -threshold:
            return "miss", f"看多 → 實際 {return_pct:+.2f}%, 反向"
        return "neutral", f"看多 → 實際 {return_pct:+.2f}%, 區間內未確認"
    if direction in ("sell", "short", "bearish"):
        if return_pct < -threshold:
            return "hit", f"看空 → 實際 {return_pct:+.2f}%, 命中"
        if return_pct > threshold:
            return "miss", f"看空 → 實際 {return_pct:+.2f}%, 反向"
        return "neutral", f"看空 → 實際 {return_pct:+.2f}%, 區間內未確認"
    if direction in ("hold", "cancel", "neutral"):
        if return_pct > threshold:
            return "miss", f"觀望/CANCEL → 實際 {return_pct:+.2f}%, 錯過上漲"
        if return_pct < -threshold:
            return "hit", f"觀望/CANCEL → 實際 {return_pct:+.2f}%, 避開下跌"
        return "hit", f"觀望 → 實際 {return_pct:+.2f}% 區間內, 判讀一致"
    return "neutral", f"未知方向 → 實際 {return_pct:+.2f}%"


# ────────────────────────────────────────────────────────────────────
# Per-source verdict computation
# ────────────────────────────────────────────────────────────────────

def verdict_deep_dive(decision_content: dict, reality: dict | None) -> dict:
    """Deep-dive: BUY/HOLD/SELL × actual return → directional verdict.

    Trader proposal entry/TP/SL also evaluated as informational rationale.
    """
    if reality is None or reality.get("return_pct") is None:
        return {"label": "pending", "rationale": "尚未取得 eval 價格"}

    ret = reality["return_pct"]
    final_action = (decision_content.get("final_action") or decision_content.get("decision") or "").upper()

    # V2.17.26 — V5.0 動詞型 action 顯式對映：
    #   STAGED_ENTRY / EXECUTE / STAGED  → 看多進場（bullish）
    #   STAGED_EXIT                       → 看空出場（bearish）
    # 舊版關鍵字 BUY/SELL/HOLD/CANCEL 仍用 substring 兜底
    BUY_ACTIONS  = {"BUY", "LONG", "EXECUTE", "STAGED_ENTRY", "STAGED"}
    SELL_ACTIONS = {"SELL", "SHORT", "STAGED_EXIT"}

    if final_action in BUY_ACTIONS or "BUY" in final_action or "LONG" in final_action:
        direction = "buy"
    elif final_action in SELL_ACTIONS or "SELL" in final_action or "SHORT" in final_action:
        direction = "sell"
    else:
        direction = "hold"   # HOLD / CANCEL / unknown 都歸觀望

    label, rationale = _verdict_directional(direction, ret, threshold=HIT_THRESHOLD_PCT)

    # 加入 trader proposal 觸發狀態
    tp = decision_content.get("trader_proposal") or {}
    if tp and reality.get("max_runup_since") is not None and reality.get("max_drawdown_since") is not None:
        triggers = []
        if tp.get("tp") and reality["max_runup_since"] >= tp["tp"]:
            triggers.append("TP 觸發")
        if tp.get("sl") and reality["max_drawdown_since"] <= tp["sl"]:
            triggers.append("SL 觸發")
        if tp.get("entry") and reality["max_drawdown_since"] <= tp["entry"]:
            triggers.append("entry 條件達成")
        if triggers:
            rationale += f"｜trader 條件: {' / '.join(triggers)}"

    return {"label": label, "rationale": rationale}


def verdict_sector_scan(decision_content: dict, sector_returns: dict | None) -> dict:
    """Sector-scan: HOT/WARM/COLD ratings × sector ETF return vs SPY.

    sector_returns: {ticker: return_pct} for the rated ETFs.
    """
    if not sector_returns:
        return {"label": "pending", "rationale": "尚未取得 ETF 報酬"}

    ratings = decision_content.get("sector_ratings") or []
    if not ratings:
        return {"label": "n/a", "rationale": "無 sector 評級資料"}

    spy_ret = sector_returns.get("SPY", 0.0)
    hits = []
    misses = []
    for r in ratings:
        etf = r.get("etf")
        rating = (r.get("rating") or "").upper()
        if not etf or etf not in sector_returns:
            continue
        rel = sector_returns[etf] - spy_ret
        if rating in ("HOT", "WARM"):
            if rel > 0:
                hits.append(f"{etf}({rating}) +{rel:.2f}%")
            else:
                misses.append(f"{etf}({rating}) {rel:.2f}%")
        elif rating == "COLD":
            if rel < 0:
                hits.append(f"{etf}({rating}) {rel:.2f}%")
            else:
                misses.append(f"{etf}({rating}) +{rel:.2f}%")

    total = len(hits) + len(misses)
    if total == 0:
        return {"label": "pending", "rationale": "ETF 報酬不完整"}
    hit_rate = len(hits) / total

    if hit_rate >= 0.6:
        return {"label": "hit", "rationale": f"sector 評級 {len(hits)}/{total} 對 (vs SPY)"}
    if hit_rate <= 0.4:
        return {"label": "miss", "rationale": f"sector 評級僅 {len(hits)}/{total} 對 (vs SPY)"}
    return {"label": "neutral", "rationale": f"sector 評級 {len(hits)}/{total} 對, 接近隨機"}


def verdict_news_digest(decision_content: dict, spy_return_pct: float | None) -> dict:
    """News-digest: macro_delta sign vs SPY direction over digest window."""
    if spy_return_pct is None:
        return {"label": "pending", "rationale": "尚未取得 SPY 報酬"}

    delta = decision_content.get("macro_delta")
    if delta is None:
        return {"label": "n/a", "rationale": "digest 未提供 macro_delta"}

    th = NEWS_HIT_THRESHOLD_PCT  # index-level band, not the single-stock 2.0%
    if delta < -0.5 and spy_return_pct < -th:
        return {"label": "hit", "rationale": f"digest 看空 ({delta:+.1f}) → SPY {spy_return_pct:+.2f}%"}
    if delta > 0.5 and spy_return_pct > th:
        return {"label": "hit", "rationale": f"digest 看多 ({delta:+.1f}) → SPY {spy_return_pct:+.2f}%"}
    if delta < -0.5 and spy_return_pct > th:
        return {"label": "miss", "rationale": f"digest 看空 ({delta:+.1f}) 但 SPY {spy_return_pct:+.2f}%"}
    if delta > 0.5 and spy_return_pct < -th:
        return {"label": "miss", "rationale": f"digest 看多 ({delta:+.1f}) 但 SPY {spy_return_pct:+.2f}%"}
    return {"label": "neutral", "rationale": f"digest delta {delta:+.1f} / SPY {spy_return_pct:+.2f}%, 不顯著"}


def verdict_news_digest_directional(decision_content: dict, spy_return_pct: float | None) -> dict:
    """SHADOW verdict (H-D / TODO-011, REVIEW_2026-06-13). Scores news-digest by
    sign(macro_delta)==sign(SPY) beyond a small noise floor instead of the ±1.0%
    magnitude band. Same |delta|>0.5 strong-signal gate as the primary so the two
    are directly comparable. NOT in VERDICT_DISPATCH — never drives the calendar
    label; build_event_index attaches it as `verdict.shadow_directional` so REVIEW
    can re-baseline before promoting/retiring the magnitude method."""
    if spy_return_pct is None:
        return {"label": "pending", "rationale": "尚未取得 SPY 報酬"}
    delta = decision_content.get("macro_delta")
    if delta is None:
        return {"label": "n/a", "rationale": "digest 未提供 macro_delta"}
    if abs(delta) < 0.5:
        return {"label": "neutral", "rationale": f"digest delta {delta:+.1f} 弱訊號, 不評分"}
    nf = NEWS_NOISE_FLOOR_PCT
    if abs(spy_return_pct) < nf:
        return {"label": "neutral", "rationale": f"SPY {spy_return_pct:+.2f}% 在雜訊地板 ±{nf}% 內"}
    same_dir = (delta > 0) == (spy_return_pct > 0)
    if same_dir:
        return {"label": "hit", "rationale": f"digest {delta:+.1f} 方向 → SPY {spy_return_pct:+.2f}% 同向"}
    return {"label": "miss", "rationale": f"digest {delta:+.1f} 方向 → SPY {spy_return_pct:+.2f}% 反向"}


def verdict_theme_detector(decision_content: dict, etf_returns: dict | None) -> dict:
    """Theme-detector: bullish (LEAD) themes' proxy ETF should outperform SPY."""
    if not etf_returns:
        return {"label": "pending", "rationale": "尚未取得 ETF 報酬"}

    themes = decision_content.get("themes") or []
    spy_ret = etf_returns.get("SPY", 0.0)
    hits, misses = [], []
    for t in themes:
        if (t.get("direction") or "").upper() != "LEAD":
            continue
        for etf in (t.get("proxy_etfs") or []):
            if etf in etf_returns:
                rel = etf_returns[etf] - spy_ret
                tag = f"{t.get('name','?')[:18]} {etf} {rel:+.2f}%"
                (hits if rel > 0 else misses).append(tag)

    total = len(hits) + len(misses)
    if total == 0:
        return {"label": "pending", "rationale": "代表 ETF 無報酬資料"}
    hit_rate = len(hits) / total
    if hit_rate >= 0.6:
        return {"label": "hit", "rationale": f"LEAD 主題 {len(hits)}/{total} 跑贏 SPY"}
    if hit_rate <= 0.4:
        return {"label": "miss", "rationale": f"LEAD 主題僅 {len(hits)}/{total} 跑贏 SPY"}
    return {"label": "neutral", "rationale": f"LEAD 主題 {len(hits)}/{total} 跑贏 SPY"}


def momentum_aggregate_metrics(per_ticker_verdicts: list[dict]) -> dict:
    """Return richer per-ticker stats for momentum screen-run review.

    The aggregate verdict remains intentionally coarse for the calendar UI, but
    review needs the per-ticker hit/miss/neutral split so neutral-heavy runs are
    not mistaken for outright directional failure.
    """
    counts = {"hit": 0, "miss": 0, "neutral": 0, "pending": 0, "n/a": 0}
    returns = []
    for v in per_ticker_verdicts:
        label = v.get("verdict") or v.get("label") or "n/a"
        counts[label] = counts.get(label, 0) + 1
        ret = v.get("return_pct")
        if isinstance(ret, (int, float)):
            returns.append(float(ret))

    n_evaluable = counts["hit"] + counts["miss"] + counts["neutral"]
    directional = counts["hit"] + counts["miss"]
    sorted_returns = sorted(returns)
    median_return = None
    if sorted_returns:
        mid = len(sorted_returns) // 2
        if len(sorted_returns) % 2:
            median_return = sorted_returns[mid]
        else:
            median_return = (sorted_returns[mid - 1] + sorted_returns[mid]) / 2

    return {
        "counts": counts,
        "n_evaluable": n_evaluable,
        "hit_rate_with_neutral": (counts["hit"] / n_evaluable) if n_evaluable else None,
        "miss_rate_with_neutral": (counts["miss"] / n_evaluable) if n_evaluable else None,
        "hit_rate_ex_neutral": (counts["hit"] / directional) if directional else None,
        "neutral_rate": (counts["neutral"] / n_evaluable) if n_evaluable else None,
        "mean_return_pct": round(sum(returns) / len(returns), 3) if returns else None,
        "median_return_pct": round(median_return, 3) if median_return is not None else None,
    }


def verdict_momentum_aggregate(per_ticker_verdicts: list[dict]) -> dict:
    """聚合 per-ticker verdicts 成 hit rate 為基準的 aggregate verdict.

    per_ticker_verdicts 每筆有 'verdict' 欄位 (str), 例如 'hit'/'miss'/...
    """
    metrics = momentum_aggregate_metrics(per_ticker_verdicts)
    counts = metrics["counts"]
    n_evaluable = metrics["n_evaluable"]
    if n_evaluable == 0:
        return {"label": "pending",
                "rationale": f"無 evaluable ticker (pending: {counts['pending']})",
                "metrics": metrics}
    hit_rate = metrics["hit_rate_with_neutral"]
    directional_txt = "n/a"
    if metrics["hit_rate_ex_neutral"] is not None:
        directional_txt = f"{metrics['hit_rate_ex_neutral']:.0%} ex-neutral"
    rationale = (
        f"{counts['hit']}/{n_evaluable} hit "
        f"(miss {counts['miss']}, neutral {counts['neutral']}; {directional_txt})"
    )
    if hit_rate >= 0.55:
        return {"label": "hit", "rationale": rationale, "metrics": metrics}
    if hit_rate <= 0.35:
        return {"label": "miss", "rationale": rationale, "metrics": metrics}
    return {"label": "neutral", "rationale": rationale, "metrics": metrics}


def verdict_momentum(decision_content: dict, reality: dict | None) -> dict:
    """Momentum-screen: BULLISH score → expect positive return; warnings flag downside."""
    if reality is None or reality.get("return_pct") is None:
        return {"label": "pending", "rationale": "尚未取得 eval 價格"}

    ret = reality["return_pct"]
    label_in = (decision_content.get("label") or "").upper()
    score = decision_content.get("score") or 0
    warnings = decision_content.get("warnings") or []

    if label_in == "BULLISH" or score >= 70:
        # warnings 越多, 容忍度越緊
        threshold_adj = max(0, len(warnings)) * 0.5
        if ret > HIT_THRESHOLD_PCT - threshold_adj:
            return {"label": "hit", "rationale": f"BULLISH ({score}) → {ret:+.2f}%"}
        if ret < -HIT_THRESHOLD_PCT:
            tag = f"，warnings={warnings}" if warnings else ""
            return {"label": "miss", "rationale": f"BULLISH ({score}) → {ret:+.2f}%{tag}"}
        return {"label": "neutral", "rationale": f"BULLISH ({score}) → {ret:+.2f}% 持平"}

    return {"label": "n/a", "rationale": f"label={label_in} 不評估"}


def verdict_thematic_screener(decision_content: dict, mover_returns: dict | None) -> dict:
    """Thematic-screener radar: top movers' realized return vs predicted target.

    For each top mover, compare actual_5d vs target_central_pct (5d horizon).
    """
    if not mover_returns:
        return {"label": "pending", "rationale": "eval window 未到 (5d)"}

    movers = decision_content.get("top_movers") or []
    hits, misses = [], []
    for m in movers:
        ticker = m.get("ticker")
        target_pct = m.get("target_5d_pct")
        if not ticker or ticker not in mover_returns or target_pct is None:
            continue
        actual = mover_returns[ticker]
        if (target_pct > 0 and actual > 0) or (target_pct < 0 and actual < 0):
            hits.append(f"{ticker} target {target_pct:+.2f}% / actual {actual:+.2f}%")
        else:
            misses.append(f"{ticker} target {target_pct:+.2f}% / actual {actual:+.2f}%")

    total = len(hits) + len(misses)
    if total == 0:
        return {"label": "pending", "rationale": "movers 無報酬資料"}
    hit_rate = len(hits) / total
    if hit_rate >= 0.6:
        return {"label": "hit", "rationale": f"movers {len(hits)}/{total} 方向對"}
    if hit_rate <= 0.4:
        return {"label": "miss", "rationale": f"movers 僅 {len(hits)}/{total} 方向對"}
    return {"label": "neutral", "rationale": f"movers {len(hits)}/{total} 方向對"}


def verdict_earnings_analyzer(decision_content: dict, ticker_returns: dict | None) -> dict:
    """Earnings-analyzer: A/B grade → expect post-earnings 5d > +2%."""
    if not ticker_returns:
        return {"label": "pending", "rationale": "eval window 未到 (5d post-earnings)"}

    results = decision_content.get("results") or []
    hits, misses = [], []
    for r in results:
        sym = r.get("symbol")
        grade = (r.get("grade") or "").upper()
        if not sym or sym not in ticker_returns:
            continue
        ret = ticker_returns[sym]
        if grade in ("A", "B"):
            if ret > HIT_THRESHOLD_PCT:
                hits.append(f"{sym}({grade}) {ret:+.2f}%")
            elif ret < -HIT_THRESHOLD_PCT:
                misses.append(f"{sym}({grade}) {ret:+.2f}%")
        elif grade == "D":
            if ret < 0:
                hits.append(f"{sym}({grade}) {ret:+.2f}%")
            else:
                misses.append(f"{sym}({grade}) {ret:+.2f}%")

    total = len(hits) + len(misses)
    if total == 0:
        return {"label": "pending", "rationale": "ticker 報酬不足"}
    hit_rate = len(hits) / total
    if hit_rate >= 0.6:
        return {"label": "hit", "rationale": f"grade-based {len(hits)}/{total} 對"}
    if hit_rate <= 0.4:
        return {"label": "miss", "rationale": f"grade-based 僅 {len(hits)}/{total} 對"}
    return {"label": "neutral", "rationale": f"grade-based {len(hits)}/{total} 對"}


def verdict_short_term_weekly(decision_content: dict, _ignored: Any = None) -> dict:
    """Weekly review 本身就是 retrospective, 直接讀 hit_rate / alpha 摘要。"""
    hit_rate = decision_content.get("hit_rate")
    alpha = decision_content.get("avg_alpha_pct")
    if hit_rate is None and alpha is None:
        return {"label": "n/a", "rationale": "weekly 無資料 (window 未到)"}
    parts = []
    if hit_rate is not None:
        parts.append(f"hit_rate={hit_rate:.0%}")
    if alpha is not None:
        parts.append(f"alpha={alpha:+.2f}%")
    return {"label": "n/a", "rationale": "已是 retrospective 摘要｜" + " / ".join(parts)}


def verdict_postmortem(_decision: dict, _ignored: Any = None) -> dict:
    return {"label": "n/a", "rationale": "postmortem 本身即為回顧, 不再評估"}


VERDICT_DISPATCH = {
    "deep-dive": verdict_deep_dive,
    "sector-scan": verdict_sector_scan,
    "news-digest": verdict_news_digest,
    "theme-detector": verdict_theme_detector,
    "momentum-screen": verdict_momentum,
    "thematic-screener": verdict_thematic_screener,
    "earnings-analyzer": verdict_earnings_analyzer,
    "short-term-weekly": verdict_short_term_weekly,
    "postmortem": verdict_postmortem,
}

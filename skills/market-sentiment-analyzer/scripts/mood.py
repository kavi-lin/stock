#!/usr/bin/env python3
"""
market-sentiment-analyzer/mood — signed Market Mood producer for the Dashboard.

Writes Dashboard/market_mood.json: an options-implied bull/bear read built from
free market-wide signals (CBOE put/call ratio, VIX + ^VIX3M term structure,
^SKEW tail-hedging, CNN Fear&Greed + 7 sub-indices) blended into a single signed
-100..+100 "mood" score for the new 市場氛圍 page.

Why a separate script from sentiment.py: sentiment.py's 0-100 composite + 15-min
cache is consumed by the investment protocol — we must not change its schema or
serve its stale cache here. mood.py imports sentiment.py's pure helpers
(normalize_*, pct_rank, label_for, fetch_cnn_fg) and computes everything fresh.

Deterministic, no LLM. Every source degrades gracefully (never raises); on total
failure it still writes a {"_partial": true, "mood": {"score": null}} skeleton so
the page shows "data unavailable" instead of erroring.

Usage:
    python3 mood.py --output Dashboard/market_mood.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone

import requests
import yfinance as yf
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))

# Import sentiment.py's pure helpers (same dir, no package).
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import sentiment  # noqa: E402  (fetch_cnn_fg, normalize_vix/pcr/ma, pct_rank, label_for)

TIMEOUT = 10
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


# ── NaN-safe helpers (data.json is written with allow_nan=False) ─────────────
def _f(v):
    """float|None, scrubbing NaN/inf."""
    try:
        x = float(v)
        return None if math.isnan(x) or math.isinf(x) else x
    except (TypeError, ValueError):
        return None


def _round(v, n=2):
    x = _f(v)
    return round(x, n) if x is not None else None


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ── Data fetchers (each best-effort, never raise) ────────────────────────────
def fetch_yf_batch():
    """One batched download for ^VIX / ^VIX3M / ^SKEW / SPY (1y daily).
    Returns dict[symbol] -> close Series (may be empty if a symbol is sparse)."""
    out = {s: pd.Series(dtype="float64") for s in ("^VIX", "^VIX3M", "^SKEW", "SPY")}
    try:
        data = yf.download(["^VIX", "^VIX3M", "^SKEW", "SPY"], period="1y",
                           interval="1d", auto_adjust=True, progress=False, group_by="ticker")
        for s in out:
            try:
                out[s] = data[s]["Close"].dropna()
            except Exception:
                pass
    except Exception as e:
        print(f"[mood] yf batch failed: {e}", file=sys.stderr)
    # Per-symbol fallback for anything still empty.
    for s in out:
        if out[s].empty:
            try:
                out[s] = yf.Ticker(s).history(period="1y")["Close"].dropna()
            except Exception:
                pass
    return out


def _cboe_last(url):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        rows = data.get("data") if isinstance(data, dict) else None
        if rows:
            last = rows[-1]
            return _f(last.get("close") if last.get("close") is not None else last.get("value")), last.get("date")
    except Exception:
        pass
    return None, None


def fetch_pcr_robust():
    """Market put/call ratio with fallbacks. Returns {value, source, asof} | None.
    CBOE total → CBOE equity → yfinance ^CPC → None. Never raises."""
    base = "https://cdn.cboe.com/api/global/us_indices/daily_prices"
    val, asof = _cboe_last(f"{base}/_totalpc_daily_price_history.json")
    if val is not None:
        return {"value": val, "source": "CBOE total", "asof": asof}
    val, asof = _cboe_last(f"{base}/_equitypc_daily_price_history.json")
    if val is not None:
        return {"value": val, "source": "CBOE equity", "asof": asof}
    try:
        s = yf.Ticker("^CPC").history(period="1mo")["Close"].dropna()
        if not s.empty:
            return {"value": _f(s.iloc[-1]), "source": "yfinance ^CPC",
                    "asof": str(s.index[-1].date())}
    except Exception:
        pass
    return None


def fetch_cnn_fg_full():
    """CNN Fear&Greed headline score + 7 sub-indices. Returns {index, sub_indices} | None."""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        d = r.json()
        idx = _f((d.get("fear_and_greed") or {}).get("score"))
        subs = {}
        for k in ("market_momentum_sp500", "stock_price_strength", "stock_price_breadth",
                  "put_call_options", "market_volatility_vix", "safe_haven_demand",
                  "junk_bond_demand"):
            node = d.get(k)
            if isinstance(node, dict):
                subs[k] = _round(node.get("score"), 1)
        return {"index": idx, "sub_indices": subs}
    except Exception:
        return None


def fetch_fmp_megacap_pcr():
    """Optional corroboration: per-stock institutional put/call ratio for a few
    mega caps via the central FMP pool. Quarterly + lagged → corroboration only.
    Returns list (possibly empty); silent skip when no FMP key."""
    if not os.getenv("FMP_API_KEY"):
        return []
    try:
        if _ROOT not in sys.path:
            sys.path.insert(0, _ROOT)
        from scripts._shared import fmp_pool
    except Exception:
        return []
    tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "QQQ"]
    reqs = [{"path": "institutional-ownership/symbol-positions-summary",
             "params": {"symbol": t, "limit": 1}, "stable": True} for t in tickers]
    out = []
    try:
        for t, res in zip(tickers, fmp_pool.fetch_many(reqs, max_workers=8)):
            row = res[0] if isinstance(res, list) and res else (res if isinstance(res, dict) else None)
            if not row:
                continue
            pcr = _f(row.get("putCallRatio"))
            if pcr is not None:
                out.append({"ticker": t, "put_call_ratio": round(pcr, 2),
                            "asof_quarter": row.get("date")})
    except Exception:
        pass
    return out


# ── Mood composition ─────────────────────────────────────────────────────────
def _mood_label(score):
    if score is None:
        return ("Unknown", "資料缺")
    if score >= 50:  return ("Extreme Greed", "強烈樂觀")
    if score >= 20:  return ("Greed", "偏樂觀")
    if score > -20:  return ("Neutral", "中性")
    if score > -50:  return ("Fear", "偏恐慌")
    return ("Extreme Fear", "強烈恐慌")


def _fg_internal_quality_score(subs):
    """Signed market quality from F&G internals.

    The headline F&G score can stay neutral while the internals are poor
    (weak breadth/strength or collapsing junk-bond demand). Treat those as
    separate quality signals so a single bullish put/call proxy cannot dominate.
    """
    keys = ("stock_price_strength", "stock_price_breadth", "junk_bond_demand")
    vals = [_f(subs.get(k)) for k in keys if _f(subs.get(k)) is not None]
    if not vals:
        return None
    signed = [((v - 50) * 2) for v in vals]
    return round(sum(signed) / len(signed), 1)


def build_mood():
    series = fetch_yf_batch()
    vix_s, vix3m_s, skew_s, spy_s = series["^VIX"], series["^VIX3M"], series["^SKEW"], series["SPY"]
    health = {}

    # VIX block
    vix_now = vix_pct = vix_regime = None
    if not vix_s.empty:
        vix_now = _f(vix_s.iloc[-1])
        vix_pct = _round(sentiment.pct_rank(vix_s, vix_now), 1)
        vix_regime = ("LOW" if vix_now < 15 else "NORMAL" if vix_now < 22
                      else "ELEVATED" if vix_now < 32 else "CRISIS")
        health["vix"] = "ok"
    else:
        health["vix"] = "missing"

    # VIX term structure (^VIX3M)
    vix3m = term_diff = term_struct = None
    if not vix3m_s.empty and vix_now is not None:
        vix3m = _f(vix3m_s.iloc[-1])
        if vix3m is not None:
            term_diff = round(vix3m - vix_now, 2)
            term_struct = ("contango" if term_diff > 0.3 else
                           "backwardation" if term_diff < -0.3 else "flat")
            health["vix3m"] = "ok"
    if vix3m is None:
        health["vix3m"] = "missing"
        term_struct = "unknown"

    # SKEW
    skew_now = skew_pct = skew_label = None
    if not skew_s.empty:
        skew_now = _f(skew_s.iloc[-1])
        skew_pct = _round(sentiment.pct_rank(skew_s, skew_now), 1)
        skew_label = ("high" if skew_now > 135 else "elevated" if skew_now > 125 else "normal")
        health["skew"] = "ok"
    else:
        health["skew"] = "missing"

    # SPY momentum (for display)
    spy_rsi = pct_ma50 = pct_ma200 = None
    if not spy_s.empty and len(spy_s) > 50:
        spy_now = _f(spy_s.iloc[-1])
        ma50 = _f(spy_s.rolling(50).mean().iloc[-1])
        ma200 = _f(spy_s.rolling(200).mean().iloc[-1]) if len(spy_s) >= 200 else None
        spy_rsi = _round(sentiment.rsi(spy_s, 14), 1)
        if spy_now and ma50:
            pct_ma50 = round((spy_now / ma50 - 1) * 100, 2)
        if spy_now and ma200:
            pct_ma200 = round((spy_now / ma200 - 1) * 100, 2)

    # Put/call (raw ratio). CBOE CDN is frequently 403-blocked; fall back below
    # to CNN's put_call_options sub-index so the options angle still contributes.
    pcr_info = fetch_pcr_robust()
    pcr = pcr_info["value"] if pcr_info else None

    # Fear & Greed (+ put_call_options sub-index used as PCR proxy when raw is missing)
    fg_info = fetch_cnn_fg_full()
    fg = fg_info["index"] if fg_info else None
    health["fg"] = "ok" if fg is not None else "missing"
    pc_subidx = (fg_info or {}).get("sub_indices", {}).get("put_call_options")  # 0-100, high=bullish
    fg_quality_score = _fg_internal_quality_score((fg_info or {}).get("sub_indices", {}))
    pc_is_proxy = False
    if pcr is not None:
        health["pcr"] = pcr_info["source"]
        pc_score = round(_clamp((0.9 - pcr) / 0.4 * 100, -100, 100), 1)  # bull positive
    elif pc_subidx is not None:
        health["pcr"] = "CNN put_call_options sub-index"
        # Proxy only: CNN's sub-index is already part of F&G and is not a raw
        # ratio. Cap it so it cannot overpower weak breadth / credit internals.
        pc_score = round(_clamp((pc_subidx - 50) * 2, -50, 50), 1)
        pc_is_proxy = True
    else:
        health["pcr"] = "missing"
        pc_score = None

    # ── signed components (bull positive, -100..+100) + weights ──
    comp = {}
    weights = {}
    if fg is not None:
        comp["fg_signed"] = round((fg - 50) * 2, 1); weights["fg_signed"] = 0.20
    if fg_quality_score is not None:
        comp["fg_quality_signed"] = fg_quality_score; weights["fg_quality_signed"] = 0.15
    if pc_score is not None:
        comp["pc_signed"] = pc_score; weights["pc_signed"] = 0.10 if pc_is_proxy else 0.20
    if vix_now is not None:
        comp["vix_signed"] = round((sentiment.normalize_vix(vix_now) - 50) * 2, 1); weights["vix_signed"] = 0.20
    if skew_now is not None:
        comp["skew_signed"] = round(-_clamp((skew_now - 125) / 15 * 100, -100, 100), 1); weights["skew_signed"] = 0.15
    if term_diff is not None:
        comp["term_signed"] = round(_clamp(term_diff / 3 * 100, -100, 100), 1); weights["term_signed"] = 0.10

    score = None
    if comp:
        wsum = sum(weights.values())
        score = round(sum(comp[k] * weights[k] for k in comp) / wsum)
    label_en, label_zh = _mood_label(score)

    # Options tilt (headline-facing). Prefer the raw ratio; otherwise read the
    # CNN put_call_options sub-index proxy; otherwise unknown.
    tilt_signed = pc_score
    if pcr is not None:
        tilt = "bull" if pcr < 0.9 else "bear" if pcr > 1.0 else "neutral"
        opt_interp = f"Put/Call {pcr:.2f}，" + {
            "bull": "偏多（賣權需求低）", "bear": "偏空（避險買權升高）",
            "neutral": "中性區間"}[tilt]
    elif pc_score is not None:
        tilt = "bull" if pc_score > 15 else "bear" if pc_score < -15 else "neutral"
        opt_interp = "期權傾向（CNN put/call 子指標）：" + {
            "bull": "偏多（賣權需求偏低）", "bear": "偏空（避險買權升高）",
            "neutral": "中性"}[tilt]
    else:
        tilt = "unknown"
        opt_interp = "Put/Call 資料缺，無法判斷期權傾向"

    vix_interp = None
    if vix_now is not None:
        vix_interp = (f"VIX {vix_now:.1f} {vix_regime}，期限結構 {term_struct}"
                      + ("（市場平靜）" if term_struct == "contango"
                         else "（壓力升高）" if term_struct == "backwardation" else ""))
    skew_interp = None
    if skew_now is not None:
        skew_interp = (f"SKEW {skew_now:.0f} {skew_label}"
                       + ("：機構在買尾部避險" if skew_label == "high" else ""))

    partial = any(v in ("missing",) for v in (health.get("vix"), health.get("fg"))) or score is None

    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mood": {
            "score": score,
            "label": label_en, "label_zh": label_zh,
            "components_used": list(comp.keys()),
            "component_scores": comp,
        },
        "options": {
            "put_call_ratio": _round(pcr, 2),
            "source": health.get("pcr"),
            "asof": pcr_info["asof"] if pcr_info else None,
            "tilt": tilt, "tilt_signed": tilt_signed,
            "interpretation_zh": opt_interp,
            "fmp_megacap": fetch_fmp_megacap_pcr(),
        },
        "vix": {
            "current": _round(vix_now, 2), "percentile_1y": vix_pct, "regime": vix_regime,
            "vix3m": _round(vix3m, 2), "term_structure": term_struct, "term_diff": term_diff,
            "interpretation_zh": vix_interp,
        },
        "skew": {
            "current": _round(skew_now, 1), "percentile_1y": skew_pct,
            "label": skew_label, "interpretation_zh": skew_interp,
        },
        "fear_greed": {
            "index": _round(fg, 1),
            "label": sentiment.label_for(fg) if fg is not None else None,
            "sub_indices": (fg_info or {}).get("sub_indices", {}),
        },
        "spy_momentum": {
            "rsi_14": spy_rsi, "pct_above_ma50": pct_ma50, "pct_above_ma200": pct_ma200,
        },
        "_source_health": health,
        "_partial": partial,
    }


def _write_atomic(path, payload):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, allow_nan=False)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description="Market Mood producer")
    ap.add_argument("--output", default=os.path.join(_ROOT, "Dashboard", "market_mood.json"))
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()

    try:
        payload = build_mood()
    except Exception as e:
        # Total failure → still write a skeleton so the page degrades gracefully.
        print(f"[mood] build failed: {e}", file=sys.stderr)
        payload = {
            "version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mood": {"score": None, "label": "Unknown", "label_zh": "資料缺",
                     "components_used": [], "component_scores": {}},
            "_source_health": {"error": str(e)}, "_partial": True,
        }

    _write_atomic(args.output, payload)
    m = payload.get("mood", {})
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not args.json_only:
        print(f"\n→ Market Mood {m.get('score')} ({m.get('label_zh')}) "
              f"│ partial={payload.get('_partial')} │ → {args.output}", file=sys.stderr)
    # rc=2 on total-failure skeleton so daily_update Step 9.3 shows ⚠️ not ✅
    return 2 if payload.get("_partial") else 0


if __name__ == "__main__":
    sys.exit(main())

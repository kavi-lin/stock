#!/usr/bin/env python3
"""
retail-sector-pulse — per-sector retail-perspective sentiment aggregator.

V3.20.0 daily-only entry. Reads:
  - news/news_logs/*_digest.json (last 72h) → news sentiment per sector
  - skills/narrative-pulse-detector/cache/<T>_<DATE>.json → retail mention multiplier
  - skills/short-term-target/scripts/predict.py (subprocess per ticker) → 5d direction

Writes Dashboard/retail_sector_pulse.json with 11 sector records.

CLI:
  python3 skills/retail-sector-pulse/scripts/aggregate.py
  python3 skills/retail-sector-pulse/scripts/aggregate.py --date 2026-05-25
  python3 skills/retail-sector-pulse/scripts/aggregate.py --output /tmp/rsp.json
  python3 skills/retail-sector-pulse/scripts/aggregate.py --skip-predict   # smoke
  python3 skills/retail-sector-pulse/scripts/aggregate.py --sector-override Energy=insufficient_data
"""
import argparse
import glob
import json
import math
import os
import statistics
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "skills" / "_shared"))

from company_context import SECTOR_TOP_5  # noqa: E402

CONFIG_PATH = HERE.parent / "config" / "weights.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "Dashboard" / "retail_sector_pulse.json"
DEFAULT_TRENDING_PATH = REPO_ROOT / "Dashboard" / "trending_tickers.json"
NEWS_LOG_DIR = REPO_ROOT / "news" / "news_logs"
NPD_CACHE_DIR = REPO_ROOT / "skills" / "narrative-pulse-detector" / "cache"
PREDICT_SCRIPT = REPO_ROOT / "skills" / "short-term-target" / "scripts" / "predict.py"


# ── Config loader ──────────────────────────────────────────────────────
def load_config(path: Optional[Path] = None) -> dict:
    fp = path or CONFIG_PATH
    with open(fp, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── News sentiment ─────────────────────────────────────────────────────
def _parse_published(s: str) -> Optional[datetime]:
    """Tolerate multiple ISO formats. Return None if unparseable."""
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            d = datetime.strptime(s.replace("Z", "+0000") if s.endswith("Z") else s, fmt)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d
        except ValueError:
            continue
    return None


def load_news_verdicts(hours_back: int = 72) -> list[dict]:
    """Walk news_logs/*_digest.json for files newer than cutoff; return flat list of
    verdicts with `published` parsed + `_source_file` annotated for debugging."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    out = []
    files = sorted(glob.glob(str(NEWS_LOG_DIR / "*_digest.json")), reverse=True)
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        for v in d.get("verdicts", []) or []:
            pub = _parse_published(v.get("published", ""))
            if pub is None:
                # fall back to file's date if verdict has no published timestamp
                base = Path(fp).stem.split("_digest")[0]
                pub = _parse_published(base + "T12:00:00")
            if pub is None or pub < cutoff:
                continue
            v2 = dict(v)
            v2["_published_dt"] = pub
            v2["_source_file"] = Path(fp).name
            out.append(v2)
    return out


def normalize_sector_name(raw: str, alias_map: dict) -> Optional[str]:
    """Map messy digest sector string to canonical SECTOR_UNIVERSE key, or None
    if unknown (caller silently drops)."""
    if not raw:
        return None
    return alias_map.get(raw) or alias_map.get(raw.strip()) or alias_map.get(raw.strip().title())


def aggregate_news_sentiment(
    sector_canonical: str, verdicts: list[dict], cfg: dict
) -> dict:
    """Per-sector weighted mean of net_impact_score (exp half-life decay)."""
    half_life = float(cfg.get("news_decay_half_life_hours", 12))
    alias_map = cfg.get("sector_aliases", {}) or {}
    now = datetime.now(timezone.utc)

    relevant = []
    for v in verdicts:
        sectors = v.get("affected_sectors") or []
        for s in sectors:
            sec_raw = s.get("sector") if isinstance(s, dict) else None
            canon = normalize_sector_name(sec_raw, alias_map)
            if canon == sector_canonical:
                relevant.append(v)
                break  # don't double-count if a verdict tags the same sector twice

    if not relevant:
        return {
            "score": None, "label": "neutral", "count": 0, "breadth": "narrow",
            "key_headlines": [],
        }

    # Weighted mean
    weighted_sum = 0.0
    weight_total = 0.0
    for v in relevant:
        age_h = (now - v["_published_dt"]).total_seconds() / 3600.0
        w = 0.5 ** (age_h / half_life)
        nis = float(v.get("net_impact_score") or 0.0)
        weighted_sum += w * nis
        weight_total += w
    score = weighted_sum / weight_total if weight_total > 0 else 0.0

    sources = {v.get("source_label") or "unknown" for v in relevant}
    breadth = "wide" if len(sources) >= 3 else "narrow"

    # Top 3 headlines by abs(net_impact_score)
    sorted_v = sorted(relevant, key=lambda v: -abs(float(v.get("net_impact_score") or 0)))[:3]
    key_headlines = [
        {
            "published": v["_published_dt"].isoformat(),
            "source": v.get("source_label") or "unknown",
            "headline": v.get("headline") or v.get("headline_zh") or "",
            "verdict": v.get("verdict"),
            "net_impact_score": float(v.get("net_impact_score") or 0),
        }
        for v in sorted_v
    ]

    return {
        "score": round(score, 2),
        "label": bucket_label(score, cfg.get("news_sentiment_labels", [])),
        "count": len(relevant),
        "breadth": breadth,
        "key_headlines": key_headlines,
    }


# ── V3.20.1: Trending tickers input (new primary retail source) ───────
def load_trending_tickers(path: Optional[Path] = None) -> Optional[dict]:
    """Load Dashboard/trending_tickers.json produced by trending_tickers.py.
    Returns full payload dict, or None if missing/parse error."""
    fp = path or DEFAULT_TRENDING_PATH
    if not Path(fp).exists():
        return None
    try:
        with open(fp, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def aggregate_retail_from_trending(sector_name: str, trending: dict, cfg: dict) -> dict:
    """V3.20.1: per-sector retail polarity + engagement + top tickers + sample
    posts, sourced from trending_tickers.json instead of NPD cache.

    Returns:
      polarity_score [-1,+1] · engagement_score (raw) · top_tickers · sample_posts
      · matched_terms_summary · label (volume bucket) · ok (data_health)
    """
    if not trending:
        return {"polarity_score": None, "engagement_score": None,
                "top_tickers": [], "sample_posts": [], "matched_terms_summary": {},
                "label": "calm", "ok": False}

    # Find this sector's rollup
    sector_rec = next((s for s in trending.get("sectors", [])
                       if s.get("sector") == sector_name), None)
    if not sector_rec or sector_rec.get("ticker_count", 0) == 0:
        return {"polarity_score": None, "engagement_score": None,
                "top_tickers": [], "sample_posts": [], "matched_terms_summary": {},
                "label": "calm", "ok": False}

    polarity = float(sector_rec.get("polarity_score") or 0.0)
    engagement = float(sector_rec.get("engagement_score") or 0.0)
    top_t = sector_rec.get("top_tickers", []) or []

    # Volume label from yaml
    label = bucket_label(engagement / 10.0,  # rough scale; engagement 10 ≈ multiplier ~1
                         cfg.get("retail_volume_labels", []))

    # Pull sample posts + matched terms from the per-ticker section of trending
    by_ticker = {t["ticker"]: t for t in (trending.get("tickers", []) or [])}
    sample_posts = []
    matched_terms_summary: dict[str, str] = {}   # term → side
    for top in top_t[:5]:
        full = by_ticker.get(top["ticker"])
        if not full:
            continue
        for sp in (full.get("sample_posts", []) or [])[:2]:
            sample_posts.append({"ticker": top["ticker"], **sp})
        for mt in full.get("matched_terms", []) or []:
            matched_terms_summary[mt["term"]] = mt["side"]
    sample_posts.sort(key=lambda p: -p.get("engagement", 0))
    sample_posts = sample_posts[:6]

    return {
        "polarity_score": round(polarity, 4),
        "engagement_score": round(engagement, 2),
        "top_tickers": top_t,
        "sample_posts": sample_posts,
        "matched_terms_summary": matched_terms_summary,
        "label": label,
        "ok": True,
    }


# ── (Legacy V3.20.0) Retail volume from NPD cache — kept as fallback ───
def load_npd_cache_for(ticker: str, max_age_hours: int = 24) -> Optional[dict]:
    """Find newest NPD cache for ticker; return dict or None if stale/missing."""
    pat = str(NPD_CACHE_DIR / f"{ticker}_*.json")
    files = sorted(glob.glob(pat), reverse=True)
    if not files:
        return None
    fp = files[0]
    age_h = (datetime.now().timestamp() - os.path.getmtime(fp)) / 3600.0
    if age_h > max_age_hours:
        return None
    try:
        with open(fp, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def aggregate_retail_volume(tickers: list[str], cfg: dict) -> dict:
    """Per-sector retail mention multiplier aggregate."""
    mults = []
    for t in tickers:
        npd = load_npd_cache_for(t)
        if not npd:
            continue
        comp = npd.get("components") or {}
        mult = comp.get("retail_mention_multiplier")
        if mult is None:
            continue
        try:
            mults.append((t, float(mult)))
        except (TypeError, ValueError):
            continue

    if not mults:
        return {"score": None, "label": "calm", "top_ticker": None,
                "top_mult": None, "sample_size": 0}

    median = statistics.median(m for _, m in mults)
    top_t, top_m = max(mults, key=lambda x: x[1])
    return {
        "score": round(median, 2),
        "label": bucket_label(median, cfg.get("retail_volume_labels", [])),
        "top_ticker": top_t,
        "top_mult": round(top_m, 2),
        "sample_size": len(mults),
    }


# ── 5d predictions (subprocess per ticker) ──────────────────────────────
def run_predict(ticker: str, horizon: str = "5d", timeout: int = 60) -> Optional[dict]:
    """Subprocess call to short-term-target/predict.py. Returns
    horizons.<horizon> dict if status=ok, else None."""
    try:
        r = subprocess.run(
            [sys.executable, str(PREDICT_SCRIPT), ticker, "--json-only"],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None

    horizons = data.get("horizons") or {}
    pred = horizons.get(horizon) or {}
    if pred.get("status") != "ok":
        return None
    return {
        "ticker": ticker,
        "target_central_pct": float(pred.get("target_central_pct") or 0),
        "confidence": float(pred.get("confidence") or 0),
    }


def aggregate_predictions(
    tickers: list[str], cfg: dict, skip_predict: bool = False
) -> dict:
    """Run predict.py per ticker; aggregate 5d direction."""
    if skip_predict:
        return {
            "median_pct": None, "bullish_breadth_pct": None, "avg_confidence": None,
            "label": "neutral", "per_ticker": [], "ok_count": 0,
        }

    horizon = cfg.get("predict_horizon", "5d")
    results = []
    for t in tickers:
        r = run_predict(t, horizon=horizon)
        if r is not None:
            results.append(r)

    min_ok = int(cfg.get("min_predict_ok_per_sector", 3))
    if len(results) < min_ok:
        return {
            "median_pct": None, "bullish_breadth_pct": None, "avg_confidence": None,
            "label": "neutral", "per_ticker": results, "ok_count": len(results),
        }

    pcts = [r["target_central_pct"] for r in results]
    confs = [r["confidence"] for r in results]
    median_pct = statistics.median(pcts)
    bullish_n = sum(1 for p in pcts if p > 0)
    bullish_breadth = 100.0 * bullish_n / len(pcts)
    avg_conf = statistics.mean(confs)
    return {
        "median_pct": round(median_pct, 2),
        "bullish_breadth_pct": round(bullish_breadth, 1),
        "avg_confidence": round(avg_conf, 3),
        "label": bucket_label(median_pct, cfg.get("predicted_5d_labels", [])),
        "per_ticker": results,
        "ok_count": len(results),
    }


# ── Composite + framing ───────────────────────────────────────────────
def bucket_label(value: Optional[float], buckets: list[dict]) -> str:
    """First-match (lo, hi] semantics. Returns first bucket's name if value is None."""
    if value is None and buckets:
        # Pick the neutral-ish bucket if exists; else first
        for b in buckets:
            if "neutral" in b.get("name", ""):
                return b["name"]
        return buckets[0].get("name", "unknown")
    for b in buckets:
        lo, hi = b["range"]
        if lo <= value < hi:
            return b["name"]
    return buckets[-1].get("name", "unknown") if buckets else "unknown"


def _sign(x: Optional[float]) -> int:
    if x is None:
        return 0
    return 1 if x > 0 else (-1 if x < 0 else 0)


def composite_score(predicted_pct: Optional[float],
                    retail_polarity: Optional[float],
                    retail_engagement: Optional[float],
                    cfg: dict) -> Optional[float]:
    """V3.20.1 three-lane composite per weights.yaml v1.1:
       price_5d_norm (0.30) + retail_polarity_signed (0.50) + retail_attention_signed (0.20)

    Lanes with None values are dropped; remaining weights re-normalize.
    """
    comp_cfg = cfg.get("composite", {})
    parts = []  # list of (weight, value) — value normalized to [-1, +1]

    if predicted_pct is not None:
        norm = max(-1.0, min(1.0, predicted_pct / 5.0))
        parts.append((float(comp_cfg["price_5d_norm"]["weight"]), norm))

    if retail_polarity is not None:
        # Already in [-1, +1] from post polarity formula
        parts.append((float(comp_cfg["retail_polarity_signed"]["weight"]), retail_polarity))

    if retail_engagement is not None and retail_polarity is not None:
        # Attention only contributes a sign when polarity defines direction
        attention_norm = (min(retail_engagement, 50.0) / 50.0) * _sign(retail_polarity)
        parts.append((float(comp_cfg["retail_attention_signed"]["weight"]), attention_norm))

    if not parts:
        return None
    total_w = sum(w for w, _ in parts)
    if total_w <= 0:
        return None
    raw = sum(w * v for w, v in parts) / total_w
    return round(max(-1.0, min(1.0, raw)), 3)


def make_framing_v2(composite_label: str, news: dict, retail: dict,
                    pred: dict, cfg: dict) -> dict:
    """V3.20.1 three-lane framing (price / retail polarity / news as context).

    Output style: '價格 5d 中位 +1.8% (3/5 看漲);散戶 polarity +0.46 (狂噴 NVDA);
                   新聞 7 篇偏多。訊號一致。'
    """
    # Price lane
    pred_med = pred.get("median_pct")
    total_preds = pred.get("ok_count", 0)
    bullish_count = round((pred.get("bullish_breadth_pct") or 0) * total_preds / 100) if total_preds else 0
    pred_sign = "+" if pred_med is not None and pred_med >= 0 else ""
    pred_med_str = f"{pred_med:.1f}" if pred_med is not None else "—"

    # Retail polarity lane
    pol = retail.get("polarity_score")
    pol_sign = "+" if pol is not None and pol >= 0 else ""
    pol_str = f"{pol:+.2f}" if pol is not None else "—"
    top_tickers_str = ""
    tops = retail.get("top_tickers") or []
    if tops:
        top_tickers_str = ", ".join(t["ticker"] for t in tops[:3])

    # News lane (display only)
    news_count = news.get("count", 0)
    news_label = news.get("label", "neutral")
    label_map = {
        "strong_bull": ("強烈看漲", "strongly bullish"),
        "mod_bull": ("偏多", "mostly bullish"),
        "neutral": ("中性", "neutral"),
        "mod_bear": ("偏空", "mostly bearish"),
        "strong_bear": ("強烈看空", "strongly bearish"),
    }
    news_zh, news_en = label_map.get(news_label, (news_label, news_label))

    # Conflict heuristic: agree if price + polarity same sign
    s_price = _sign(pred_med)
    s_pol = _sign(pol)
    if s_price == 0 or s_pol == 0:
        conflict_zh = "資料部分缺。"
        conflict_en = "Partial data."
    elif s_price == s_pol:
        conflict_zh = "訊號一致。"
        conflict_en = "Signals align."
    else:
        conflict_zh = "訊號分歧。"
        conflict_en = "Signals diverge."

    # Build framing string
    zh_parts = []
    if pred_med is not None:
        zh_parts.append(f"5天中位 {pred_sign}{pred_med_str}% ({bullish_count}/{total_preds} 看漲)")
    if pol is not None:
        zh_parts.append(f"散戶 polarity {pol_str}" +
                        (f" ({top_tickers_str})" if top_tickers_str else ""))
    if news_count > 0:
        zh_parts.append(f"新聞 {news_count} 篇{news_zh}")

    zh = "; ".join(zh_parts) + "。" + conflict_zh if zh_parts else "資料不足。"

    en_parts = []
    if pred_med is not None:
        en_parts.append(f"5d med {pred_sign}{pred_med_str}% ({bullish_count}/{total_preds} bull)")
    if pol is not None:
        en_parts.append(f"retail polarity {pol_str}" +
                        (f" ({top_tickers_str})" if top_tickers_str else ""))
    if news_count > 0:
        en_parts.append(f"news {news_count} {news_en}")
    en = "; ".join(en_parts) + ". " + conflict_en if en_parts else "Insufficient data."

    return {"zh": zh, "en": en}


def make_framing(sector_label: str, news: dict, retail: dict, pred: dict, cfg: dict) -> dict:
    """Render rule-based zh + en framing strings."""
    fcfg = cfg.get("framing", {})
    labels = fcfg.get("label_translations", {}) or {}
    rules = fcfg.get("conflict_rules", {}) or {}

    news_label = news.get("label", "neutral")
    news_label_zh = labels.get(news_label, {}).get("zh", news_label)
    news_label_en = labels.get(news_label, {}).get("en", news_label)
    news_count = news.get("count", 0)

    top_ticker = retail.get("top_ticker") or "—"
    top_mult = retail.get("top_mult") or 0.0
    top_mult_label_key = retail.get("label") or "calm"
    top_mult_label_zh = labels.get(top_mult_label_key, {}).get("zh", top_mult_label_key)
    top_mult_label_en = labels.get(top_mult_label_key, {}).get("en", top_mult_label_key)

    pred_median = pred.get("median_pct")
    total_preds = pred.get("ok_count", 0)
    bullish_count = round((pred.get("bullish_breadth_pct") or 0) * total_preds / 100) if total_preds else 0
    pred_sign = "+" if pred_median is not None and pred_median >= 0 else ""

    # Conflict heuristic
    s_news = _sign(news.get("score"))
    s_pred = _sign(pred_median)
    if s_news == 0 or s_pred == 0:
        conflict_zh = rules.get("partial_zh", "")
        conflict_en = rules.get("partial_en", "")
    elif s_news == s_pred:
        conflict_zh = rules.get("align_zh", "")
        conflict_en = rules.get("align_en", "")
    else:
        conflict_zh = rules.get("diverge_zh", "")
        conflict_en = rules.get("diverge_en", "")

    fmt_kwargs = dict(
        news_count=news_count,
        news_label_zh=news_label_zh,
        news_label_en=news_label_en,
        top_ticker=top_ticker,
        top_mult=top_mult,
        top_mult_label=top_mult_label_zh,  # reused; en template can override per-template
        bullish_count=bullish_count,
        total_preds=total_preds,
        pred_sign=pred_sign,
        pred_median=pred_median if pred_median is not None else 0.0,
        conflict_note=conflict_zh,
    )
    try:
        zh = fcfg.get("zh_template", "").format(**fmt_kwargs)
    except Exception as e:
        zh = f"[framing error: {e}]"

    fmt_kwargs_en = dict(fmt_kwargs)
    fmt_kwargs_en["top_mult_label"] = top_mult_label_en
    fmt_kwargs_en["news_label_zh"] = news_label_en  # unused in en template,but symmetric
    fmt_kwargs_en["conflict_note"] = conflict_en
    try:
        en = fcfg.get("en_template", "").format(**fmt_kwargs_en)
    except Exception as e:
        en = f"[framing error: {e}]"

    return {"zh": zh, "en": en}


# ── Per-sector aggregator (V3.20.1 three-lane) ────────────────────────
def aggregate_sector(sector_name: str, tickers: list[str], verdicts: list[dict],
                     trending: Optional[dict], cfg: dict,
                     skip_predict: bool = False,
                     override: Optional[str] = None) -> dict:
    """Compute one sector record.

    V3.20.1 changes:
      - Retail layer now sourced from trending_tickers.json (sector rollup of
        Reddit/HN/Bluesky/Trends posts with engagement-weighted polarity), NOT
        from NPD cache.
      - Three-lane composite: price_5d_norm + retail_polarity_signed +
        retail_attention_signed (per weights.yaml v1.1).
      - News sentiment now a SECONDARY display attribute (kept on card but
        does NOT enter composite formula).
    """
    proxy = cfg.get("proxy_etfs", {}).get(sector_name)

    if override == "insufficient_data":
        return {
            "sector": sector_name, "proxy_etf": proxy,
            "data_health": {"news_72h_ok": False, "retail_signals_ok": False,
                            "predict_5d_ok": False, "all_ok": False},
            "composite_score": None, "composite_direction": "neutral_mixed",
            "framing_zh": "資料不足。", "framing_en": "Insufficient data.",
            "news_sentiment_score": None, "news_label": "neutral", "news_count_72h": 0,
            "news_breadth": "narrow",
            "retail_polarity_score": None, "retail_engagement_score": None,
            "retail_volume_label": "calm",
            "retail_top_tickers": [], "sample_posts": [], "matched_terms_summary": {},
            "predicted_5d_median_pct": None, "predicted_5d_bullish_breadth_pct": None,
            "predicted_5d_avg_confidence": None, "predicted_5d_label": "neutral",
            "key_tickers": [], "key_headlines": [],
            "signal_lanes": {"price_5d_norm": None,
                             "retail_polarity": None,
                             "retail_attention": None},
        }

    news = aggregate_news_sentiment(sector_name, verdicts, cfg)
    retail = aggregate_retail_from_trending(sector_name, trending, cfg)
    pred = aggregate_predictions(tickers, cfg, skip_predict=skip_predict)

    # ── V3.20.1 three-lane composite ──────────────────────────────────
    comp_score = composite_score(
        predicted_pct=pred.get("median_pct"),
        retail_polarity=retail.get("polarity_score"),
        retail_engagement=retail.get("engagement_score"),
        cfg=cfg,
    )
    comp_label = bucket_label(comp_score if comp_score is not None else 0.0,
                              cfg.get("direction_labels", []))

    # Record the normalized lane values for transparency (V3.20.1 audit)
    pred_med = pred.get("median_pct")
    price_norm = (max(-1.0, min(1.0, pred_med / 5.0))
                  if pred_med is not None else None)
    pol_score = retail.get("polarity_score")
    eng_score = retail.get("engagement_score")
    attention_norm = (
        (min(eng_score, 50.0) / 50.0) * _sign(pol_score)
        if pol_score is not None and eng_score is not None else None
    )

    framing = make_framing_v2(comp_label, news, retail, pred, cfg)

    # Key tickers: top 3 predictions by abs(target_central_pct × confidence)
    per_t = pred.get("per_ticker") or []
    key_tickers = sorted(per_t, key=lambda x: -abs(x["target_central_pct"] * x["confidence"]))[:3]

    data_health = {
        "news_72h_ok": news.get("count", 0) > 0,
        "retail_signals_ok": bool(retail.get("ok")),
        "predict_5d_ok": pred.get("ok_count", 0) >= int(cfg.get("min_predict_ok_per_sector", 3)),
    }
    data_health["all_ok"] = all(data_health.values())

    return {
        "sector": sector_name,
        "proxy_etf": proxy,

        # News lane (display only — NOT in composite in V3.20.1)
        "news_sentiment_score": news.get("score"),
        "news_label": news.get("label"),
        "news_count_72h": news.get("count"),
        "news_breadth": news.get("breadth"),

        # Retail lane (V3.20.1 — from trending_tickers.json)
        "retail_polarity_score": retail.get("polarity_score"),
        "retail_engagement_score": retail.get("engagement_score"),
        "retail_volume_label": retail.get("label"),
        "retail_top_tickers": retail.get("top_tickers", []),
        "sample_posts": retail.get("sample_posts", []),
        "matched_terms_summary": retail.get("matched_terms_summary", {}),

        # Price lane (predict.py 5d)
        "predicted_5d_median_pct": pred.get("median_pct"),
        "predicted_5d_bullish_breadth_pct": pred.get("bullish_breadth_pct"),
        "predicted_5d_avg_confidence": pred.get("avg_confidence"),
        "predicted_5d_label": pred.get("label"),

        # Composite (3-lane)
        "composite_score": comp_score,
        "composite_direction": comp_label,
        "signal_lanes": {
            "price_5d_norm": round(price_norm, 4) if price_norm is not None else None,
            "retail_polarity": round(pol_score, 4) if pol_score is not None else None,
            "retail_attention": round(attention_norm, 4) if attention_norm is not None else None,
        },

        "framing_zh": framing["zh"],
        "framing_en": framing["en"],

        "key_tickers": key_tickers,
        "key_headlines": news.get("key_headlines"),

        "data_health": data_health,
    }


# ── Main entry ────────────────────────────────────────────────────────
def run(skip_predict: bool = False, override_map: Optional[dict] = None,
        trending_path: Optional[Path] = None) -> dict:
    """Top-level orchestration. Returns the full payload dict.

    V3.20.1: loads Dashboard/trending_tickers.json (or custom path) for the
    retail layer. If missing, retail signals are None for all sectors and
    composite falls back to price-only.
    """
    cfg = load_config()
    lookback_h = int(cfg.get("lookback_hours", 72))
    verdicts = load_news_verdicts(hours_back=lookback_h)
    trending = load_trending_tickers(trending_path)

    sectors_out = []
    for sector_name, tickers in SECTOR_TOP_5.items():
        override = (override_map or {}).get(sector_name)
        record = aggregate_sector(
            sector_name, tickers, verdicts, trending, cfg,
            skip_predict=skip_predict, override=override,
        )
        sectors_out.append(record)

    # Surface market_wide_buzz from trending into top-level output
    market_wide = (trending or {}).get("market_wide_buzz", []) or []
    trending_meta = {
        "available": trending is not None,
        "lexicon_version": (trending or {}).get("lexicon_version"),
        "post_count": (trending or {}).get("post_count"),
        "as_of": (trending or {}).get("as_of"),
        "source_stats": (trending or {}).get("source_stats", {}),
    }

    return {
        "version": "1.1",
        "schema_note": "V3.20.1 — 3-lane composite (price/polarity/attention); retail sourced from trending_tickers.json",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "weights_version": cfg.get("weights_version", "unknown"),
        "lookback_hours": lookback_h,
        "horizon": cfg.get("predict_horizon", "5d"),
        "universe_size": sum(len(v) for v in SECTOR_TOP_5.values()),
        "sectors": sectors_out,
        "market_wide_buzz": market_wide,
        "trending_meta": trending_meta,
    }


def main():
    ap = argparse.ArgumentParser(description="retail-sector-pulse aggregator")
    ap.add_argument("--date", help="(unused in v1; placeholder for backfill)")
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    ap.add_argument("--trending-input", default=None,
                    help="Path to trending_tickers.json (default: Dashboard/trending_tickers.json)")
    ap.add_argument("--skip-predict", action="store_true",
                    help="Skip predict.py subprocess (smoke / dev)")
    ap.add_argument("--sector-override", action="append", default=[],
                    help="Force a sector to insufficient_data. Format: Sector=insufficient_data")
    args = ap.parse_args()

    override_map = {}
    for ov in args.sector_override:
        if "=" in ov:
            k, v = ov.split("=", 1)
            override_map[k.strip()] = v.strip()

    trending_path = Path(args.trending_input) if args.trending_input else None
    payload = run(skip_predict=args.skip_predict, override_map=override_map,
                  trending_path=trending_path)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    print(f"[retail-sector-pulse] wrote {out_path} ({len(payload['sectors'])} sectors)",
          file=sys.stderr)


if __name__ == "__main__":
    main()

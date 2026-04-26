#!/usr/bin/env python3
"""
short-term-target — 1d / 5d / 15d directional projection ("Tactical Opportunity Radar").

Honest about its limits:
  - Output is a SHORT-TERM PROJECTION, not a guarantee.
  - Each horizon has independent weights (per plan_short.md §12.A).
  - Hard-clamped to prevent cold-start absurd predictions (§11.A).
  - Refuses to project when source data is stale (§11.C insufficient_data).
  - Confidence is broken down per contributor for auditability (§12.C).
  - Benchmark-relative output exposes alpha vs sector ETF (§12.B).
  - Trading meta gives stop / position-size hint / tx cost / exit trigger (§12.I).

All tunable parameters live in config/weights.yaml (hand-edit, bump weights_version).

Usage:
  python3 predict.py NVDA
  python3 predict.py AMD --json-only
"""
import os
import sys
import json
import argparse
import datetime
from pathlib import Path

try:
    import yfinance as yf
    import yaml
    import numpy as np
except ImportError:
    print("ERROR: pip install yfinance pyyaml numpy", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent.parent.parent
SKILL_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = SKILL_DIR / "cache"
CONFIG_PATH = SKILL_DIR / "config" / "weights.yaml"
DUAL_FETCH_DIR = ROOT / "skills" / "finnhub-client" / "data"
SECTOR_LOG_DIR = ROOT / "sector" / "sector_logs"

DEFAULT_CONFIG = {
    "weights_version": "v0.1.0-builtin",
    "horizon_weights": {
        "1d": {"alpha_news": 0.6, "beta_sector_heat": 0.1, "gamma_momentum": 0.3, "atr_multiplier": 1.0},
        "5d": {"alpha_news": 0.3, "beta_sector_heat": 0.3, "gamma_momentum": 0.4, "atr_multiplier": 1.8},
        "15d": {"alpha_news": 0.1, "beta_sector_heat": 0.4, "gamma_momentum": 0.3, "atr_multiplier": 3.5},
    },
    "max_pct_by_horizon": {"1d": 5.0, "5d": 15.0, "15d": 30.0},
    "freshness_thresholds": {
        "1d": {"quote_min": 60, "news_hr": 8, "atr_min_days": 5},
        "5d": {"quote_min": 240, "news_hr": 24, "sector_hr": 72, "ohlcv_min_days": 5, "atr_min_days": 14},
        "15d": {"quote_min": 1440, "news_hr": 168, "sector_hr": 168, "ohlcv_min_days": 15, "atr_min_days": 14},
    },
    "benchmark_map": {"_default": "SPY"},
}


# --------- config / data fetch ---------

def load_config():
    """Load weights.yaml; deep-merge over DEFAULT_CONFIG."""
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG
    try:
        user_cfg = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    except Exception as e:
        print(f"WARN: weights.yaml parse failed ({e}); using built-in defaults", file=sys.stderr)
        return DEFAULT_CONFIG
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    for k, v in user_cfg.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    return cfg


def fetch_ohlcv(ticker, days=60):
    """yfinance OHLCV. Returns dict or None."""
    try:
        h = yf.Ticker(ticker).history(period=f"{days}d", auto_adjust=False)
        if h.empty:
            return None
        return {
            "closes": h["Close"].values,
            "highs": h["High"].values,
            "lows": h["Low"].values,
            "vols": h["Volume"].values,
            "dates": [d.strftime("%Y-%m-%d") for d in h.index],
        }
    except Exception as e:
        print(f"WARN: yfinance {ticker}: {e}", file=sys.stderr)
        return None


def fetch_benchmark_realized(etf, n_days):
    """N-day realized return of benchmark ETF, or None."""
    try:
        h = yf.Ticker(etf).history(period=f"{n_days + 7}d", auto_adjust=False)
        if h.empty or len(h) < n_days + 1:
            return None
        return (h["Close"].iloc[-1] / h["Close"].iloc[-(n_days + 1)] - 1) * 100
    except Exception:
        return None


def get_dual_fetch_scoring(ticker):
    """Read scoring from latest dual_fetch snapshot. Returns (scoring_dict_or_None, status)."""
    today_dir = DUAL_FETCH_DIR / datetime.date.today().isoformat()
    if not today_dir.is_dir():
        return None, "no_today_dir"
    p = today_dir / f"{ticker}.json"
    if not p.exists():
        return None, "no_ticker_file"
    try:
        b = json.loads(p.read_text())
        return b.get("scoring"), "ok"   # _audit MUST never be touched here
    except Exception:
        return None, "parse_error"


def get_sector_heat(ticker):
    """Read latest sector_intel cache. Returns (heat_0_to_1, age_hr, status)."""
    files = sorted(SECTOR_LOG_DIR.glob("*_sector_intel.json"), reverse=True)
    if not files:
        return None, None, "no_cache"
    latest = files[0]
    age_hr = (datetime.datetime.now().timestamp() - latest.stat().st_mtime) / 3600
    try:
        d = json.loads(latest.read_text())
    except Exception:
        return None, age_hr, "parse_error"

    themes = d.get("actionable_themes") or []
    import re
    heats = []
    for t in themes:
        if isinstance(t, str):
            m = re.search(r"heat\s*([\d.]+)", t, re.I)
            if m:
                heats.append(float(m.group(1)))
    if heats:
        median_heat = sorted(heats)[len(heats) // 2]
        return median_heat / 100.0, age_hr, "ok_proxy_median"
    return None, age_hr, "no_themes_parsed"


# --------- driver computations ---------

def compute_atr_pct(ohlcv, n=14):
    if not ohlcv or len(ohlcv["closes"]) < n + 1:
        return None
    closes, highs, lows = ohlcv["closes"], ohlcv["highs"], ohlcv["lows"]
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if len(trs) < n:
        return None
    atr = sum(trs[-n:]) / n
    current = closes[-1]
    return (atr / current) * 100 if current > 0 else None


def compute_momentum_score(ohlcv):
    """Returns (score in [-1, +1], label string)."""
    if not ohlcv or len(ohlcv["closes"]) < 50:
        return 0.0, "insufficient_history"
    closes = np.asarray(ohlcv["closes"], dtype=float)

    deltas = np.diff(closes[-15:])
    gains = np.where(deltas > 0, deltas, 0).mean() if len(deltas) else 0
    losses = np.where(deltas < 0, -deltas, 0).mean() if len(deltas) else 0
    rs = gains / losses if losses > 0 else 100.0
    rsi = 100 - (100 / (1 + rs))

    ma20 = closes[-20:].mean()
    ma50 = closes[-50:].mean()
    current = closes[-1]

    if rsi >= 90:
        rsi_score = 0.3
    elif rsi >= 70:
        rsi_score = (rsi - 50) / 40
    elif rsi >= 30:
        rsi_score = (rsi - 50) / 40
    else:
        rsi_score = -0.5

    if current > ma20 > ma50:
        ma_score = 0.3
    elif current < ma20 < ma50:
        ma_score = -0.3
    else:
        ma_score = 0.0

    score = max(-1.0, min(1.0, rsi_score + ma_score))
    label = f"RSI={rsi:.0f}, current{'>' if current > ma20 else '<'}MA20{'>' if ma20 > ma50 else '<'}MA50"
    return score, label


import re

# ── Sentiment lexicon (finance-tuned, v0.2.1) ──────────────
STRONG_POS = [
    r'beats?', r'crushed?', r'crushes?', r'surge[ds]?', r'soars?', r'soared',
    r'rally(?:ing)?', r'rallied', r'breakthrough', r'record high', r'all-time high',
    r'raises? guidance', r'raised guidance', r'strong demand', r'wins? contract',
    r'wins? deal', r'wins? approval', r'blockbuster', r'upgrade[ds]?',
    r'outperform', r'strong buy', r'fda approv', r'approved by fda',
    r'beats? estimate', r'beat estimate', r'beats? expectation',
    r'raised dividend', r'dividend hike', r'buyback announc', r'authorized buyback',
    r'accelerat(?:e|ed|ing)', r'positive surprise', r'tops estimate',
]
STRONG_NEG = [
    r'miss(?:es|ed)?', r'downgrade[ds]?', r'plunge[ds]?', r'plunged',
    r'crash(?:ed|ing)?', r'fraud', r'lawsuit', r'recall(?:ed)?',
    r'cuts? guidance', r'cut guidance', r'weak demand', r'investigation',
    r'probe', r'restated?', r'fired', r'bankruptcy', r'delisted?',
    r'sec charge', r'fda reject', r'misses? estimate', r'underperform',
    r'sell rating', r'short seller', r'dividend cut', r'cut dividend',
    r'estimates miss', r'misses? expectation', r'guidance cut',
    r'flopped?', r'disappointed?', r'sell pressure', r'distribution day',
]
MILD_POS = [
    r'rises?', r'gains?', r'positive', r'growth', r'expansion', r'momentum',
    r'rebounds?', r'recovers?', r'improves?', r'improved', r'advance[ds]?',
    r'climbs?', r'jumps?', r'tailwind', r'accumulat',
]
MILD_NEG = [
    r'falls?', r'falling', r'concerns?', r'warning', r'declines?', r'losses',
    r'pressure', r'slumps?', r'drops?', r'slides?', r'tumbles?', r'sluggish',
    r'hesitancy', r'hesitant', r'headwind', r'cautious', r'lagg(?:ed|ing)?',
    # v0.2.2 verb-variation fixes
    r'slips?', r'slipped', r'slipping', r'lags?', r'dips?', r'dipped',
    r'sinks?', r'sank', r'wanes?', r'struggles?', r'struggling', r'soft(?:ens|ened)',
]
NEG_MARKERS = [r'\bnot ', r'\bno beat\b', r'\bno growth\b', r'\bno gain\b',
               r'\bfails? to ', r'\bunable to ', r'\bdenies? ']

# Question form: news framed as a question is NOT a sentiment claim → halve score
QUESTION_PREFIXES = re.compile(r'^\s*(is|are|should|will|can|could|does|do|why|how|what|which|will)\s+', re.I)

MAG_BEAT_PCT = re.compile(r'beats?[\w \-,]{0,30}by\s+(\d{1,2})%', re.I)
MAG_RAISE_GUIDANCE = re.compile(r'rais(?:es|ed)\s+guidance', re.I)
MAG_CUT_GUIDANCE = re.compile(r'cuts?\s+(?:guidance|outlook|forecast)', re.I)

# Low-quality news sources (SEO mills / opinion-only / aggregators)
SOURCE_BLACKLIST = {'simplywall.st', 'fool.com', 'zacks.com'}


def _score_text_block(text, has_negation):
    """Score one text block (headline OR summary). Asymmetric negation:
    only POS words flip on negation (per v0.2.2 fix — see 'Why X Flopped' bug)."""
    score = 0.0
    sign_pos = -1 if has_negation else 1
    for w in STRONG_POS:
        if re.search(rf'\b{w}\b', text):
            score += 0.5 * sign_pos
    for w in STRONG_NEG:
        # v0.2.2: NEG words ignore negation (false-positive risk too high;
        # 'flopped' + 'might not be realized' should NOT flip flopped to positive)
        if re.search(rf'\b{w}\b', text):
            score -= 0.5
    for w in MILD_POS:
        if re.search(rf'\b{w}\b', text):
            score += 0.2 * sign_pos
    for w in MILD_NEG:
        if re.search(rf'\b{w}\b', text):
            score -= 0.2
    m = MAG_BEAT_PCT.search(text)
    if m:
        pct = int(m.group(1))
        score += min(pct / 25, 0.5) * sign_pos
    if MAG_RAISE_GUIDANCE.search(text):
        score += 0.3 * sign_pos
    if MAG_CUT_GUIDANCE.search(text):
        score -= 0.3
    return score


def score_one_article(article):
    """Score one news item from -1 to +1.
    Per v0.2.2: headline weighted 0.7, summary 0.3 (headline is editor-curated;
    summary often contains caveats that mislead bag-of-words scoring)."""
    raw_title = article.get('headline') or ''
    title = raw_title.lower()
    summary = (article.get('summary') or '').lower()
    # Negation flag: per-block (don't let summary "not" flip headline strong words)
    title_neg = any(re.search(p, title) for p in NEG_MARKERS)
    summary_neg = any(re.search(p, summary) for p in NEG_MARKERS)
    title_score = _score_text_block(title, title_neg) if title else 0.0
    summary_score = _score_text_block(summary, summary_neg) if summary else 0.0
    # If summary missing, headline carries full weight
    score = title_score * 0.7 + summary_score * 0.3 if summary else title_score
    # Question-form discount on headline only
    if '?' in raw_title or QUESTION_PREFIXES.match(raw_title):
        score *= 0.5
    return max(-1.0, min(1.0, score))


def get_company_short_name(ticker, client):
    """Use Finnhub profile to extract a relevance-matchable short name.
    e.g. NVDA → 'NVIDIA', LLY → 'Eli Lilly', JPM → 'JPMorgan Chase'."""
    SUFFIXES = {'inc', 'inc.', 'corp', 'corp.', 'corporation', 'ltd', 'ltd.',
                'limited', 'co', 'co.', 'llc', 'plc', 'nv', 'ag', 'sa',
                'holdings', 'group', 'class', 'company', '&', 'and'}
    try:
        profile = client.profile(ticker)
        full = (profile.get('name') if profile else '') or ''
    except Exception:
        return None
    if not full:
        return None
    parts = full.split()
    while parts and parts[-1].lower().rstrip('.,') in SUFFIXES:
        parts.pop()
    return ' '.join(parts[:2]) if parts else None


def is_relevant_article(article, ticker, short_name):
    """Article is RELEVANT if ticker symbol OR company short name appears in
    headline (the 'who is this article about' check)."""
    raw_title = article.get('headline') or ''
    if not raw_title:
        return False
    upper = raw_title.upper()
    if re.search(rf'\b{re.escape(ticker.upper())}\b', upper):
        return True
    if short_name and short_name.lower() in raw_title.lower():
        return True
    return False


def get_news_driver_v2(ticker):
    """v0.2: Finnhub /company-news + keyword+magnitude+negation scoring.
    Returns (score, label, source_tag, n_articles, news_age_hr).
    n_articles=0 / source='proxy_fallback' → caller should use proxy."""
    sys.path.insert(0, str(ROOT / "skills" / "finnhub-client" / "scripts"))
    try:
        from finnhub_client import FinnhubClient, FinnhubError
    except ImportError:
        return None
    try:
        client = FinnhubClient()
        end_d = datetime.date.today().isoformat()
        start_d = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
        articles = client.company_news(ticker, start_d, end_d)
    except FinnhubError as e:
        print(f"WARN: Finnhub news {ticker}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"WARN: Finnhub news {ticker}: {e}", file=sys.stderr)
        return None
    if not articles:
        return {"score": 0.0, "label": "no_news_48h", "source": "finnhub_v2_empty",
                "n_articles": 0, "age_hr": None}

    # v0.2.1 fix: get company short name for relevance filter
    short_name = get_company_short_name(ticker, client)

    cutoff = datetime.datetime.now().timestamp() - 172800
    candidates = []
    n_dropped_relevance = 0
    n_dropped_blacklist = 0
    n_dropped_old = 0
    newest_ts = 0
    for art in articles:
        ts = art.get('datetime', 0)
        if ts:
            if ts < cutoff:
                n_dropped_old += 1
                continue
        src = (art.get('source') or '').lower()
        if any(b in src for b in SOURCE_BLACKLIST):
            n_dropped_blacklist += 1
            continue
        # v0.2.1 fix: relevance filter — article must be ABOUT this ticker
        if not is_relevant_article(art, ticker, short_name):
            n_dropped_relevance += 1
            continue
        candidates.append((ts, art, src))

    # v0.2.1 fix: cap at top 20 by recency (avoid noise dilution)
    candidates.sort(key=lambda x: -(x[0] or 0))
    candidates = candidates[:20]

    if not candidates:
        meta_label = (f"raw={len(articles)} dropped(rel={n_dropped_relevance}, "
                      f"src={n_dropped_blacklist}, old={n_dropped_old})")
        return {"score": 0.0, "label": f"no_quality_news_48h ({meta_label})",
                "source": "finnhub_v2_filtered", "n_articles": 0, "age_hr": None}

    scored = []
    for ts, art, src in candidates:
        s = score_one_article(art)
        scored.append((s, art.get('headline', '')[:80], src))
        if ts:
            newest_ts = max(newest_ts, ts)

    avg = sum(s[0] for s in scored) / len(scored)
    conf_factor = min(1.0, len(scored) / 5)
    final = max(-1.0, min(1.0, avg * conf_factor))
    age_hr = (datetime.datetime.now().timestamp() - newest_ts) / 3600 if newest_ts else None
    label = (f"{len(scored)} relevant/48h (raw {len(articles)}, "
             f"-{n_dropped_relevance}rel, -{n_dropped_blacklist}src), "
             f"avg {avg:+.2f} (conf×{conf_factor:.1f}); "
             f"matched as: {short_name or ticker}")
    return {"score": final, "label": label, "source": "finnhub_v2_keyword",
            "n_articles": len(scored), "n_raw": len(articles),
            "n_dropped_relevance": n_dropped_relevance,
            "company_short_name": short_name,
            "age_hr": round(age_hr, 1) if age_hr else None,
            "examples": [{"score": round(s, 2), "headline": h, "source": src} for s, h, src in scored[:5]]}


def get_news_driver(ohlcv, ticker=None):
    """v0.2 wrapper: try Finnhub /company-news first, fallback to v0.1 proxy."""
    # Try Finnhub method 2 first (if ticker provided)
    if ticker:
        v2 = get_news_driver_v2(ticker)
        if v2 is not None and v2.get("n_articles", 0) > 0:
            return v2["score"], v2["label"], v2["source"]
    # Fallback to v0.1 proxy (volume × gap)
    if not ohlcv or len(ohlcv["closes"]) < 21:
        return 0.0, "insufficient", "proxy_volume_gap"
    vols = np.asarray(ohlcv["vols"], dtype=float)
    closes = np.asarray(ohlcv["closes"], dtype=float)
    recent_vol = vols[-1]
    avg_vol = vols[-21:-1].mean()
    if avg_vol == 0:
        return 0.0, "no_volume_data", "proxy_volume_gap"
    vol_ratio = recent_vol / avg_vol
    gap_pct = (closes[-1] / closes[-2] - 1) * 100 if len(closes) >= 2 else 0
    if vol_ratio > 1.5:
        score = (gap_pct / 5) * min(vol_ratio - 1, 1.5)
        score = max(-1.0, min(1.0, score))
        label = f"vol {vol_ratio:.1f}× avg, gap {gap_pct:+.1f}%"
    else:
        score = 0.0
        label = f"normal vol ({vol_ratio:.1f}×)"
    return score, label, "proxy_volume_gap_fallback"


# --------- prediction ---------

def map_benchmark(sub_industry, benchmark_map):
    if sub_industry and sub_industry in benchmark_map:
        return benchmark_map[sub_industry]
    return benchmark_map.get("_default", "SPY")


def compute_confidence(news_conf, heat_persistence, atr_pct, days_horizon, was_clamped, data_complete):
    """Per §12.C transparent breakdown."""
    base = 0.50
    news_freshness = (news_conf - 0.5) * 0.4 if news_conf is not None else 0.0
    sector_persistence = (heat_persistence or 0.0) * 0.15
    atr_penalty = -((atr_pct or 3.0) - 3.0) / 10.0
    horizon_penalty = -(days_horizon / 100.0)
    completeness_bonus = 0.02 if data_complete else 0.0
    clamp_penalty = -0.15 if was_clamped else 0.0
    total = base + news_freshness + sector_persistence + atr_penalty + horizon_penalty + completeness_bonus + clamp_penalty
    total = max(0.0, min(0.95, total))
    return total, {
        "base": base,
        "news_freshness": round(news_freshness, 3),
        "sector_heat_persistence": round(sector_persistence, 3),
        "atr_penalty": round(atr_penalty, 3),
        "horizon_penalty": round(horizon_penalty, 3),
        "data_completeness_bonus": round(completeness_bonus, 3),
        "model_clamped_penalty": round(clamp_penalty, 3),
    }


def check_sufficiency(horizon, ohlcv, news_age_hr, sector_age_hr, atr_pct, freshness_th):
    rules = freshness_th.get(horizon, {})
    missing = []
    n_ohlcv = len(ohlcv["closes"]) if ohlcv else 0
    details = {
        "ohlcv_days": n_ohlcv,
        "news_age_hr": round(news_age_hr, 2) if news_age_hr is not None else None,
        "sector_age_hr": round(sector_age_hr, 2) if sector_age_hr is not None else None,
        "atr_pct": round(atr_pct, 2) if atr_pct is not None else None,
    }
    if rules.get("ohlcv_min_days") and n_ohlcv < rules["ohlcv_min_days"]:
        missing.append(f"ohlcv<{rules['ohlcv_min_days']}d")
    if rules.get("atr_min_days") and (atr_pct is None or n_ohlcv < rules["atr_min_days"] + 1):
        missing.append(f"atr_sample<{rules['atr_min_days']}d")
    if rules.get("news_hr") and news_age_hr is not None and news_age_hr > rules["news_hr"]:
        missing.append(f"news>{rules['news_hr']}h_old")
    if rules.get("sector_hr") and sector_age_hr is not None and sector_age_hr > rules["sector_hr"]:
        missing.append(f"sector>{rules['sector_hr']}h_old")
    if missing:
        return {
            "status": "insufficient_data",
            "missing": missing,
            "would_need": "Refresh stale sources OR wait for sufficient OHLCV history",
            "details": details,
        }
    return {"status": "ok", "missing": [], "would_need": None, "details": details}


def predict_horizon(horizon, days, current, news, heat, momentum, atr_pct,
                    ohlcv, news_age_hr, sector_age_hr, freshness_th, weights, max_cap):
    suff = check_sufficiency(horizon, ohlcv, news_age_hr, sector_age_hr, atr_pct, freshness_th)
    if suff["status"] != "ok":
        return {
            "status": "insufficient_data",
            "missing": suff["missing"],
            "would_need": suff["would_need"],
            "data_sufficiency": suff["details"],
        }

    w = weights[horizon]
    shift_pct = (
        w.get("alpha_news", 0) * (news or 0) * 5.0
        + w.get("beta_sector_heat", 0) * ((heat or 0.5) - 0.5) * 8.0
        + w.get("gamma_momentum", 0) * (momentum or 0) * 6.0
    )
    cap = max_cap[horizon]
    was_clamped = abs(shift_pct) > cap
    if was_clamped:
        shift_pct = max(-cap, min(cap, shift_pct))

    target_central = current * (1 + shift_pct / 100)
    range_half = (atr_pct or 3.0) / 100 * current * w.get("atr_multiplier", 1.0)
    target_low = target_central - range_half
    target_high = target_central + range_half

    news_conf = 0.7 if news is not None else 0.4
    heat_persistence = heat if heat is not None else 0.0
    confidence, breakdown = compute_confidence(
        news_conf, heat_persistence, atr_pct, days, was_clamped, suff["status"] == "ok"
    )

    return {
        "status": "ok",
        "target_central": round(target_central, 2),
        "target_low": round(target_low, 2),
        "target_high": round(target_high, 2),
        "target_central_pct": round((target_central / current - 1) * 100, 2),
        "confidence": round(confidence, 2),
        "confidence_breakdown": breakdown,
        "drivers": {
            "news_score": round(news or 0, 2),
            "sector_heat": round(heat or 0, 2),
            "momentum_score": round(momentum or 0, 2),
            "atr_pct": round(atr_pct or 0, 2),
        },
        "model_clamped": was_clamped,
        "data_sufficiency": suff["details"],
        "weights_applied": w,
    }


def trading_meta(current, atr_pct, predictions):
    if atr_pct is None:
        return {"insufficient_data": "atr_pct unavailable"}
    stop = current * (1 - 1.5 * atr_pct / 100)
    pos_pct = max(0.5, min(5.0, 0.33 / (atr_pct / 100.0)))
    exit_target = predictions.get("5d", {}).get("target_central")
    return {
        "stop_suggestion": round(stop, 2),
        "stop_distance_pct": round(1.5 * atr_pct, 2),
        "position_size_hint_pct": round(pos_pct, 2),
        "tx_cost_estimate_pct": 0.05,
        "min_holding_days": 1,
        "exit_trigger": (
            f"Close < {round(stop, 2)} OR target {exit_target} reached "
            f"OR confidence drops < 0.4"
        ),
        "exit_trigger_zh": (
            f"收盤 < {round(stop, 2)} 或 目標價 {exit_target} 達成 "
            f"或 信心降至 < 0.4"
        ),
    }


# --------- main ---------

CACHE_TTL_SEC = 4 * 3600   # 4-hour cache per ticker


def cache_path_for(ticker):
    return CACHE_DIR / f"{ticker.upper()}.json"


def load_from_cache(ticker):
    """Return cached prediction if fresh, else None."""
    p = cache_path_for(ticker)
    if not p.exists():
        return None
    age_sec = datetime.datetime.now().timestamp() - p.stat().st_mtime
    if age_sec > CACHE_TTL_SEC:
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def save_to_cache(ticker, payload):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path_for(ticker).write_text(json.dumps(payload, indent=2, default=str))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--json-only", action="store_true",
                    help="Compact JSON (no indent)")
    ap.add_argument("--no-cache", action="store_true",
                    help="Skip cache; force fresh prediction")
    args = ap.parse_args()

    ticker = args.ticker.upper()

    # Cache check (per §plan_short Q3 — predict cache layer to reduce screener wall time)
    if not args.no_cache:
        cached = load_from_cache(ticker)
        if cached is not None:
            cached.setdefault("metadata", {})["from_cache"] = True
            print(json.dumps(cached, indent=2 if not args.json_only else None, default=str))
            return

    cfg = load_config()

    ohlcv = fetch_ohlcv(ticker, days=60)
    if not ohlcv:
        print(json.dumps({"ticker": ticker, "error": "ohlcv_fetch_failed"}))
        sys.exit(1)
    current = float(ohlcv["closes"][-1])

    atr_pct = compute_atr_pct(ohlcv, n=14)
    momentum, momentum_label = compute_momentum_score(ohlcv)
    news, news_label, news_meta = get_news_driver(ohlcv, ticker=ticker)
    heat, sector_age_hr, sector_status = get_sector_heat(ticker)
    dual_scoring, dual_status = get_dual_fetch_scoring(ticker)
    news_age_hr = 0.5  # v1 proxy; treat volume signal as "live"

    horizons_def = {"1d": 1, "5d": 5, "15d": 15}
    predictions = {}
    for h, days in horizons_def.items():
        predictions[h] = predict_horizon(
            h, days, current, news, heat, momentum, atr_pct,
            ohlcv, news_age_hr, sector_age_hr,
            cfg["freshness_thresholds"], cfg["horizon_weights"], cfg["max_pct_by_horizon"],
        )
        if predictions[h]["status"] == "ok":
            predictions[h]["driver_labels"] = {
                "momentum": momentum_label,
                "news": news_label,
                "sector_status": sector_status,
            }

    # Benchmark relative
    sub_ind = None  # GICS lookup deferred to v2
    bench = map_benchmark(sub_ind, cfg["benchmark_map"])
    for h, days in horizons_def.items():
        if predictions[h]["status"] != "ok":
            continue
        bench_realized = fetch_benchmark_realized(bench, days)
        predictions[h]["benchmark_etf"] = bench
        predictions[h]["benchmark_realized_pct"] = round(bench_realized, 2) if bench_realized is not None else None
        if bench_realized is not None:
            predictions[h]["implied_alpha_pct"] = round(
                predictions[h]["target_central_pct"] - bench_realized, 2
            )

    tm = trading_meta(current, atr_pct, predictions)

    if predictions.get("5d", {}).get("status") == "ok":
        invalidation = (
            f"Close < {tm.get('stop_suggestion')} "
            f"OR sector heat downgrades by 0.2 "
            f"OR ATR jumps > 50% from {atr_pct:.1f}%"
        )
        invalidation_zh = (
            f"收盤 < {tm.get('stop_suggestion')} "
            f"或 產業熱度下滑 0.2 "
            f"或 ATR 從 {atr_pct:.1f}% 跳升 > 50%"
        )
    else:
        invalidation = "5d insufficient_data; no actionable invalidation"
        invalidation_zh = "5d 資料不足；無可執行失效條件"

    out = {
        "ticker": ticker,
        "as_of": datetime.datetime.utcnow().isoformat() + "Z",
        "current_price": round(current, 2),
        "weights_version": cfg.get("weights_version", "unknown"),
        "horizons": predictions,
        "trading_meta": tm,
        "invalidation": invalidation,
        "invalidation_zh": invalidation_zh,
        "metadata": {
            "dual_fetch_status": dual_status,
            "sector_heat_status": sector_status,
            "news_driver_kind": news_meta,
            "experimental": True,
            "framework": "Tactical Opportunity Radar v0.1",
            "benchmark_etf": bench,
        },
        "global_warnings": [],
    }
    if news_meta == "proxy_volume_gap_fallback":
        out["global_warnings"].append(
            "Finnhub /company-news unavailable; news driver fell back to v0.1 volume/gap proxy"
        )
    elif news_meta in ("finnhub_v2_empty", "finnhub_v2_filtered"):
        out["global_warnings"].append(
            "Finnhub /company-news returned no usable articles in 48h; news driver = 0"
        )
    if dual_status != "ok":
        out["global_warnings"].append(f"dual_fetch unavailable ({dual_status}); using yfinance only")
    if sub_ind is None:
        out["global_warnings"].append("sub_industry GICS lookup deferred; benchmark defaulted")

    # Cache write (4h TTL — for screener batch reuse)
    out.setdefault("metadata", {})["from_cache"] = False
    save_to_cache(ticker, out)

    print(json.dumps(out, indent=2 if not args.json_only else None, default=str))


if __name__ == "__main__":
    main()

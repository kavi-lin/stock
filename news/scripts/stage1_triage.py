#!/usr/bin/env python3
"""
Stage 1 deterministic triage — directional scoring plus event materiality.

v3.14.3 additions
-----------------
- Hard-block low-signal templates (law-firm class-action solicitations, single-
  project real-estate PR, personal-finance advice columns) **before** scoring
  so they cannot leak into Stage 2 deep debate.
- Headline-template dedup: identical templates across multiple tickers
  (`Johnson Fistel Investigates Losses at NVDA/TSLA/AMD`) collapse to one entry,
  preventing N independent advancements.
- Content-aware credibility downgrade: provider HIGH × press-release / column /
  advertorial markers → effective MEDIUM or LOW. Advancement gate uses the
  effective credibility, not the raw provider tag.
- `NEWS_STAGE1_MAX_ITEMS` env (default 800) replaces the hard 313 cap that was
  silently dropping the tail of the raw pool.
- Rule-based `classify_news_type` with priority order: earnings > monetary
  policy > macro data > geopolitical > corporate action > sector > general.
  Legacy keyword maps remain as final fallback.
- `headline_zh` set to None at this stage — the downstream digest LLM step
  fills the field for top-N items only (cheaper than translating 300+).
- Telemetry: triage.json now carries `blocked_counts` and
  `template_dedup_dropped` so the validator can spot quiet regressions.

Public interface (consumed by scripts/break_news/poller.py and others):
    classify_news_type(headline, summary)
    calc_shallow_score(headline, summary, news_type)
    gen_4view_snaps(headline, news_type)
    BINARY_KEYS
These signatures are preserved.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent.parent
RAW_FILE = HERE / "news_logs" / f"{datetime.now().strftime('%Y-%m-%d')}_raw.json"

STAGE1_MAX_ITEMS = int(os.environ.get("NEWS_STAGE1_MAX_ITEMS", "800"))

# ── Legacy keyword maps (kept as fallback to the new rule-based classifier) ──
KEYWORDS = {
    "earnings": ["earnings", "earnings report", "q[0-9] results", "guidance", "guidance raised", "guidance cut", "eps"],
    "monetary_policy": ["fed", "fomc", "interest rate", "rate decision", "rate hike", "rate cut", "monetary policy"],
    "macro_data": ["cpi", "inflation", "gdp", "unemployment", "pce", "jobs report", "payroll"],
    "geopolitical": ["china", "russia", "ukraine", "taiwan", "trump", "election", "trade war", "tariff"],
    "corporate": ["acquisition", "merger", "buyback", "dividend", "ceo", "restructure", "layoff", "offering"],
    "sector_news": ["sector", "industry", "rally", "selloff", "rebound", "weakness"],
    "sentiment": ["rally", "crash", "surge", "plunge", "bubble", "panic", "fear", "greed"],
}

POSITIVE_KEYS = ["bull", "gain", "raise", "strong", "beat", "rally", "surge", "upgrade", "win", "bullish"]
NEGATIVE_KEYS = ["bear", "loss", "cut", "weak", "miss", "crash", "plunge", "downgrade", "risk", "bearish", "decline"]
BINARY_KEYS = ["election", "vote", "decision", "merger", "acquisition", "bankruptcy"]

STAGE2_MAX_ITEMS = 5
STAGE2_MATERIALITY_MIN = 4.5

_SOURCE_MATERIALITY = {
    "official_regulator": 3.0,
    "official_macro": 3.0,
    "company_filing": 2.5,
    "wire": 2.0,
    "publisher": 1.0,
    "aggregator": 0.25,
    "press_release": -1.0,
    "social": -1.5,
    "unknown": 0.0,
}

_TYPE_MATERIALITY = {
    "monetary_policy": 2.0,
    "macro_data": 2.0,
    "geopolitical": 2.0,
    "earnings": 1.5,
    "corporate": 1.5,
    "sector_news": 1.0,
    "sentiment": 0.25,
}

_GENRE_RULES = [
    ("routine_regulatory", re.compile(
        r"\bannounces? approval of the application by\b|"
        r"\bnotice of (?:filing|effectiveness)\b|"
        # Personnel-level enforcement. Fed/OCC/FDIC publish these continuously
        # and the subject is one individual's conduct, not the institution —
        # zero market content, but source_kind=official_macro + monetary_policy
        # alone clears STAGE2_MATERIALITY_MIN, so without a genre penalty they
        # advance ahead of real news (2026-08-14: a former Regions Bank employee
        # notice ranked #1 of the day and stalled the whole digest).
        # Institution-level actions do NOT match: the subject qualifier is
        # required, and those headlines carry the entity plus a penalty amount.
        r"\b(?:issues?|announces?|takes?)\s+(?:an?\s+)?(?:enforcement action|consent order|"
        r"cease[- ]and[- ]desist(?:\s+order)?|prohibition order|civil money penalt(?:y|ies))\b"
        r"[^\n]{0,80}\b(?:former|individual|employee|institution-affiliated)\b|"
        r"\benforcement action\s+(?:with|against)\s+(?:an?\s+|the\s+)?(?:former|individual)\b",
        re.I,
    )),
    ("filing_notice", re.compile(r"^\s*\[?8-k\]?[^:]*:\s*8-k\b|^\s*\[8-k\]", re.I)),
    ("analyst_rating", re.compile(
        r"\b(?:upgraded?|downgraded?)\s+to\s+(?:strong\s+)?(?:buy|sell|hold)\b|"
        r"\b(?:raises?|cuts?|lowers?)\s+(?:the\s+)?(?:price\s+)?target\b|"
        r"\banalyst\s+(?:upgrade|downgrade|rating)\b",
        re.I,
    )),
    ("listicle", re.compile(
        r"\b(?:top|best|these|tap)\s+\d+\b[^\n]{0,35}\bstocks?\b|"
        r"\bstocks?\s+to\s+(?:buy|sell|watch)\b|"
        r"\bchatgpt\s+(?:picks?|names?)\b|"
        r"\bhere(?:'|’)s\s+what\s+you\s+should\s+know\b|"
        r"\bbargain stocks?\b|\btoo cheap to ignore\b",
        re.I,
    )),
    ("earnings_preview", re.compile(r"\bearnings preview\b|\bwhat to expect\b", re.I)),
    ("opinion", re.compile(
        r"^(?:opinion|commentary)\s*:|\bI(?:'|’)m\s+(?:more\s+)?bullish\b|"
        r"\bwhy\s+I\s+(?:bought|sold|like|avoid)\b|\block in gains\b|"
        r"\bwe(?:'|’)re\s+(?:trimming|buying|selling)\b",
        re.I,
    )),
    ("market_recap", re.compile(
        r"\blive\s+(?:nasdaq|s&p|dow)\b|\bmarket recap\b|"
        r"\bstocks?\s+(?:today|close)\b|"
        r"\b(?:index|tsx|nasdaq|s&p|dow)\s+(?:hits|closes|rises|falls|jumps|surges|plunges)\b",
        re.I,
    )),
]

_GENRE_PENALTY = {
    "straight_news": 0.0,
    "market_recap": 1.25,
    "opinion": 2.0,
    "earnings_preview": 2.0,
    "analyst_rating": 3.0,
    "listicle": 4.0,
    "press_release": 2.0,
    "research_commentary": 1.75,
    "filing_notice": 2.0,
    "routine_regulatory": 3.0,
}

_COMMENTARY_SOURCES = {
    "24/7 Wall Street", "247 Wall St", "Finbold", "FXEmpire", "GuruFocus",
    "Invezz", "Motley Fool", "Seeking Alpha", "The Motley Fool",
    "Zacks Investment Research",
}

_MATERIAL_EVENT_RE = re.compile(
    r"\b(?:reports?|beats?|misses?|raises?|cuts?|lowers?)\s+(?:q[1-4]\s+|fy\d{2,4}\s+)?"
    r"(?:earnings|eps|revenue|guidance|forecast|outlook)|"
    r"\b(?:announces?|approves?|rejects?|files?|launches?)\s+(?:a\s+|the\s+)?"
    r"(?:merger|acquisition|buyback|offering|tariff|sanctions?|bankruptcy)|"
    r"\b(?:fomc|fed)\s+(?:raises?|cuts?|holds?)\b|"
    r"\b(?:cpi|pce|gdp|payrolls?|unemployment)\b[^\n]{0,35}\b(?:rises?|falls?|prints?|at)\b",
    re.I,
)
_MARKET_MOVE_RE = re.compile(r"\b(?:surges?|plunges?|jumps?|dives?|falls?|rises?)\s+\d+(?:\.\d+)?%", re.I)
_MAGNITUDE_RE = re.compile(r"(?:\$\s?\d|\b\d+(?:\.\d+)?\s?(?:%|bp|bps|billion|million)\b)", re.I)
_BINARY_EVENT_RE = re.compile(
    r"\b(?:fda|pdufa|court|jury|shareholder|regulator|commission)\b[^\n]{0,60}"
    r"\b(?:decision|ruling|verdict|vote|approval|approve|reject)\b|"
    r"\b(?:merger|acquisition)\b[^\n]{0,60}\b(?:vote|approval|approve|reject|deadline)\b|"
    r"\b(?:referendum|election result|rate decision)\b",
    re.I,
)
_BINARY_PENDING_RE = re.compile(
    r"\b(?:awaits?|awaiting|due|expected|pending|scheduled|set(?:\s+for)?|"
    r"will\s+(?:decide|rule|vote)|to\s+vote|deadline|before)\b",
    re.I,
)
_EVENT_STOPWORDS = {
    "after", "amid", "and", "are", "as", "at", "before", "by", "for", "from",
    "in", "into", "is", "its", "new", "of", "on", "or", "says", "the", "to",
    "with", "why", "what", "stock", "stocks", "shares", "market", "markets",
}


# ─── P0a — hard-block negative-content patterns ──────────────────────────────
# Matching headlines/summaries are dropped at the loop's first step: they never
# enter `verdicts`, never reach `stage2_items`, and never get exported. The
# advancement gate (P0c) is therefore never tempted to elevate them via the
# `credibility=HIGH × |score|≥0.5` short-circuit.
_BLOCK_PATTERNS = {
    # Law-firm class-action solicitations (template letters re-emitted per
    # ticker; pure noise for an investment desk). Pattern matches either a
    # known plaintiff-side firm name OR the generic solicitation phrasing.
    "law_firm_solicitation": re.compile(
        r"\b("
        r"Johnson Fistel|Schall Law|Rosen Law|Robbins LLP|Levi & Korsinsky|"
        r"Hagens Berman|Kuznicki Law|Bragar Eagel|Glancy Prongay|Pomerantz|"
        r"Kessler Topaz|Faruqi & Faruqi|Block & Leviton"
        r"|investigate(?:s|d)?\b[^.\n]{0,40}\b(?:claim|breach|misleading|fraud)"
        r"|securities (?:class action|fraud) investigation"
        r"|encouraged to (?:reach out|contact)[^.\n]{0,40}(?:loss|recover)"
        r"|reach out (?:to|for)[^.\n]{0,40}(?:loss|recover)"
        r")",
        re.I,
    ),
    # Single-project real-estate / luxury PR
    "real_estate_pr": re.compile(
        r"\b(?:Condominium|Condominiums|Penthouse|Luxury (?:Tower|Residence)s?)\b"
        r"[^.\n]{0,40}\b(?:Debuts?|Launches?|Grand Opening|Now Selling|Coming Soon|"
        r"Unveil(?:s|ed)?)\b",
        re.I,
    ),
    # Personal finance advice columns (mostly Yahoo/MarketWatch lifestyle filler)
    "personal_finance_advice": re.compile(
        r"^\s*(?:I (?:inherited|just|own|sold|have|got|made)\b"
        r"|Should I\b"
        r"|My (?:husband|wife|spouse|parents|mother|father|kid|daughter|son|boss)\b"
        r"|We have \$\d"
        r"|Dear (?:Penny|Reader|Annie|Abby)\b"
        r"|Ask (?:the Expert|an Advisor)\b)",
        re.I,
    ),
    # HK-listed China-tech reports (NetEase / Bilibili 港股表述) — Futu Push
    # surfaces RMB-denominated Q-results and HK-index breakdowns that don't
    # move the US session this committee tracks. Block by Chinese company
    # name + Latin variants. ADR coverage (NTES / BILI tickers) is preserved
    # — the regex only fires on the Chinese company name, so English wires
    # citing NTES/BILI still flow through normally.
    "hk_china_listing_chatter": re.compile(
        r"網易|嗶哩嗶哩|bilibili|netease|163\.com",
        re.I,
    ),
}


def _is_blocked(headline: str, summary: str) -> tuple[bool, str | None]:
    """Return (True, reason) if any block pattern hits.

    Patterns are evaluated in dict order; first hit wins so the telemetry
    `blocked_counts` aggregates by primary reason.
    """
    text = f"{headline or ''}\n{summary or ''}"
    for reason, pat in _BLOCK_PATTERNS.items():
        if pat.search(text):
            return True, reason
    return False, None


# ─── P0b — headline-template dedup ───────────────────────────────────────────
# Strip tickers / dollar figures / dates / day-of-week so functionally identical
# template letters across many tickers collapse to one key. Keeps the first
# instance, drops the rest, increments `template_dedup_dropped`.
_RE_TICKER     = re.compile(r"\b[A-Z]{2,5}\b")
_RE_MONEY      = re.compile(r"\$[\d,.]+(?:[BMK]|\s*(?:billion|million|thousand))?", re.I)
_RE_DATE       = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2}\b", re.I)
_RE_DOW        = re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)(?:day)?\b", re.I)
_RE_WHITESPACE = re.compile(r"\s+")


def _headline_template_key(headline: str) -> str:
    s = headline or ""
    s = _RE_TICKER.sub("TICKER", s)
    s = _RE_MONEY.sub("MONEY", s)
    s = _RE_DATE.sub("DATE", s)
    s = _RE_DOW.sub("DOW", s)
    s = _RE_WHITESPACE.sub(" ", s.lower()).strip()
    return s[:120]


# ─── P0c — content-aware credibility downgrade ───────────────────────────────
_PRESS_RELEASE_RE = re.compile(
    r"\b(press release|sponsored content|advertorial|paid post|"
    r"company announces|announces[^.\n]{0,30}\bdebut|unveils|"
    r"now available|introducing)\b",
    re.I,
)
_OPINION_RE = re.compile(
    r"\b(opinion|column(?:ist)?|editorial|guest post|personal finance|"
    r"my take|i think|i believe)\b",
    re.I,
)


def effective_credibility(item: dict, headline: str = "", summary: str = "") -> str:
    """Provider tag adjusted by content markers.

    HIGH provider × press-release marker → MEDIUM (not LOW — provider verified
    the wire, just not the content quality).
    MEDIUM provider × press-release marker → LOW.
    Opinion / personal-finance markers → LOW outright.
    """
    provider = (item or {}).get("source_credibility", "MEDIUM")
    text = f"{headline or ''}\n{summary or ''}"
    if _OPINION_RE.search(text):
        return "LOW"
    if _PRESS_RELEASE_RE.search(text):
        if provider == "HIGH":
            return "MEDIUM"
        return "LOW"
    return provider


def classify_content_genre(item: dict, headline: str = "", summary: str = "") -> str:
    """Classify article form separately from event type.

    A reliable publisher can still publish a low-materiality rating note or
    listicle. Keeping genre separate prevents provider credibility from
    promoting that content into Stage 2.
    """
    if (item or {}).get("source_kind") == "press_release":
        return "press_release"
    text = f"{headline or ''}\n{summary or ''}"
    for genre, pattern in _GENRE_RULES:
        if pattern.search(text):
            return genre
    if (item or {}).get("source") in _COMMENTARY_SOURCES:
        return "research_commentary"
    return "straight_news"


def detect_binary_event(headline: str, summary: str = "") -> bool:
    """Return true only for an explicit outcome-dependent event.

    Generic words such as ``decision`` or ``merger`` are intentionally not
    sufficient. Those broad keywords caused routine earnings and corporate
    stories to enter the binary path.
    """
    text = f"{headline or ''}\n{summary or ''}"
    return bool(_BINARY_EVENT_RE.search(text) and _BINARY_PENDING_RE.search(text))


def calc_materiality_score(
    item: dict,
    headline: str,
    summary: str,
    news_type: str,
    shallow_score: float,
    effective_cred: str,
    genre: str,
) -> float:
    """Score event importance independently from directional sentiment."""
    source_kind = (item or {}).get("source_kind", "unknown")
    score = _SOURCE_MATERIALITY.get(source_kind, 0.0)
    score += _TYPE_MATERIALITY.get(news_type, 0.0)
    score += min(abs(float(shallow_score)), 4.0) * 0.35

    text = f"{headline or ''}\n{summary or ''}"
    if _MATERIAL_EVENT_RE.search(text):
        score += 1.5
    elif _MARKET_MOVE_RE.search(text):
        score += 1.0
    if _MAGNITUDE_RE.search(text):
        score += 0.5

    score += {"HIGH": 0.5, "MEDIUM": 0.0, "LOW": -0.75}.get(effective_cred, 0.0)
    score -= _GENRE_PENALTY.get(genre, 0.0)
    return round(max(0.0, min(10.0, score)), 2)


def _event_tokens(headline: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", (headline or "").lower())
    return {
        token for token in tokens
        if token not in _EVENT_STOPWORDS and len(token) > 2 and not token.isdigit()
    }


def _event_subject(headline: str) -> str:
    for token in re.findall(r"[a-z0-9]+", (headline or "").lower()):
        if token not in _EVENT_STOPWORDS and len(token) > 2 and not token.isdigit():
            return token
    return ""


def _same_event(a: dict, b: dict) -> bool:
    """Conservative headline similarity used only for Stage 2 diversity."""
    if _event_subject(a.get("headline", "")) != _event_subject(b.get("headline", "")):
        return False
    left = _event_tokens(a.get("headline", ""))
    right = _event_tokens(b.get("headline", ""))
    if not left or not right:
        return False
    overlap = len(left & right) / min(len(left), len(right))
    return overlap >= 0.60


def select_stage2_items(verdicts: list[dict], limit: int = STAGE2_MAX_ITEMS) -> list[dict]:
    """Select material, diverse events without forcing the daily quota full."""
    selected: list[dict] = []
    source_counts: dict[str, int] = {}
    for verdict in verdicts:
        if len(selected) >= limit:
            break
        if not verdict.get("binary_flag") and verdict.get("materiality_score", 0) < STAGE2_MATERIALITY_MIN:
            verdict["advance_to_stage2"] = False
            verdict["advance_reason"] = None
            continue
        if any(_same_event(verdict, existing) for existing in selected):
            verdict["advance_to_stage2"] = False
            verdict["advance_reason"] = "duplicate_event"
            continue
        source = verdict.get("source") or "Unknown"
        source_cap = 3 if verdict.get("source_kind") == "wire" else 2
        if verdict.get("content_genre") in {"analyst_rating", "listicle", "research_commentary"}:
            source_cap = 1
        if source_counts.get(source, 0) >= source_cap:
            verdict["advance_to_stage2"] = False
            verdict["advance_reason"] = "source_diversity"
            continue
        verdict["advance_to_stage2"] = True
        verdict["advance_reason"] = "binary" if verdict.get("binary_flag") else "materiality"
        verdict["_stage2_rank"] = len(selected) + 1
        selected.append(verdict)
        source_counts[source] = source_counts.get(source, 0) + 1
    return selected


# ─── P1b — rule-based news_type classifier (priority-ordered) ────────────────
_CLASS_RULES = [
    # Order matters: first match wins. Concrete corporate disclosures rank
    # above broader macro/policy because a CPI mention in an earnings call
    # release should still classify as earnings.
    ("earnings", re.compile(
        r"\b(earnings|eps|revenue|guidance|q[1-4]\s|fy20\d{2}|"
        r"quarterly results|fiscal (?:year|q\d)|"
        r"misses?\s+(?:on|estimates)|beats?\s+(?:on|estimates))\b",
        re.I,
    )),
    ("corporate", re.compile(
        r"\b(merger|acquisition|takeover|buyback|repurchase program|"
        r"dividend (?:hike|increase|cut|suspended)|stock split|spin-off|"
        r"divestiture|secondary offering|tender offer)\b",
        re.I,
    )),
    ("monetary_policy", re.compile(
        r"\b(fomc|federal reserve|fed (?:funds rate|chair)|"
        r"powell|rate (?:hike|cut|decision|outlook|path)|"
        r"monetary policy|qt\b|quantitative (?:tightening|easing))\b",
        re.I,
    )),
    ("macro_data", re.compile(
        r"\b(cpi|core cpi|pce|core pce|ppi|jobs report|"
        r"non-?farm payroll|payrolls?|unemployment rate|"
        r"gdp(?:\s+growth)?|ism (?:manufacturing|services)|pmi|"
        r"retail sales|consumer (?:confidence|sentiment))\b",
        re.I,
    )),
    ("geopolitical", re.compile(
        r"\b(tariff|sanctions|trade war|export controls?|"
        r"iran|ukraine|russia|china (?:tension|response)|"
        r"taiwan|hormuz|red sea|north korea|"
        r"election (?:result|outcome)|policy shift)\b",
        re.I,
    )),
    ("sector_news", re.compile(
        r"\b(sector (?:rotation|rally|selloff|weakness)|"
        r"industry (?:trend|outlook)|cyclical (?:rotation|laggards))\b",
        re.I,
    )),
]


def classify_news_type(headline: str, summary: str = "") -> str:
    """Priority-ordered news-type classifier.

    Returns one of: earnings, corporate, monetary_policy, macro_data,
    geopolitical, sector_news, sentiment (catch-all). Uses regex rules first;
    falls back to the legacy keyword-count tally so existing callers that
    expect the historical buckets still get them for edge cases.
    """
    text = f"{headline or ''}\n{summary or ''}"

    # 8-K filings — concrete corporate disclosure
    if re.search(r"\b8-k\b", text, re.I) or re.search(r"\bitem \d", text, re.I):
        return "corporate"

    for label, pat in _CLASS_RULES:
        if pat.search(text):
            return label

    # Legacy fallback (keyword-count max). Keeps backward-compat for break_news
    # poller which has been calling this for months on raw social headlines.
    lower = text.lower()
    scores = {k: sum(1 for kw in kws if re.search(kw, lower)) for k, kws in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "sentiment"


def calc_shallow_score(headline: str, summary: str, news_type: str) -> float:
    """Simple -5 to +5 keyword tally (unchanged signature)."""
    text = (headline + " " + summary).lower()
    positive = sum(1 for kw in POSITIVE_KEYS if kw in text)
    negative = sum(1 for kw in NEGATIVE_KEYS if kw in text)

    # 8-K filings get a baseline score based on the embedded item type
    if "8-k" in text:
        if any(x in text for x in ["acquisition", "merger", "dividend", "guidance"]):
            return 1.5
        elif any(x in text for x in ["departure", "termination", "loss"]):
            return -1.0
        else:
            return 0.2

    if news_type in ["earnings", "corporate"]:
        pos_weight, neg_weight = 1.5, 1.5
    elif news_type in ["monetary_policy", "macro_data"]:
        pos_weight, neg_weight = 2.0, 2.0
    else:
        pos_weight, neg_weight = 1.0, 1.0

    score = (positive * pos_weight - negative * neg_weight)
    return max(-5, min(5, round(score, 1)))


def gen_4view_snaps(headline: str, news_type: str) -> tuple[str, str, str, str]:
    """Return (bull, bear, sector, macro) one-liner ≤30-char snaps."""
    text_lower = headline.lower()

    if news_type == "earnings":
        if "raise" in text_lower or "beat" in text_lower:
            return ("收益超預期提振前景", "高基期+競爭加劇", "受惠產業擴張", "利率敏感性降低")
        return ("現金流改善空間", "成長放緩風險", "行業內相對強弱", "成本控制關鍵")
    if news_type == "monetary_policy":
        if "cut" in text_lower or "lower" in text_lower:
            return ("流動性寬鬆刺激增長", "通膨風險捲土重來", "防守股受惠", "美元走弱利美股")
        return ("成本壓力升高", "通膨抑制買氣", "週期股承壓", "實質利率抬升")
    if news_type == "macro_data":
        if "strong" in text_lower or "beat" in text_lower:
            return ("經濟韌性超預期", "過熱通膨風險", "景氣敏感股利多", "軟著陸概率升高")
        return ("經濟動能疲軟", "衰退擔憂加重", "防守股相對強勢", "降息預期升溫")
    if news_type == "geopolitical":
        return ("地緣套利機會", "供應鏈中斷風險", "能源相關板塊波動", "避險資產需求增加")
    if news_type == "corporate":
        if "acquisition" in text_lower or "merger" in text_lower:
            return ("整合效益釋放", "交易風險存在", "產業整併加速", "槓桿率抬升")
        return ("營運效率改善", "股權稀釋隱憂", "同業估值參考", "現金使用決策")
    if news_type == "sector_news":
        return ("板塊動能向上", "個股分化加劇", "輪動信號出現", "相對強度追蹤")
    return ("市場情緒轉好", "情緒反轉風險", "板塊追漲機會", "風險偏好提升")


def _build_verdict(idx: int, item: dict) -> dict:
    """One-shot verdict construction (shared between batch + single-item callers)."""
    news_id   = f"n{idx + 1:04d}"
    headline  = item.get("headline", "") or ""
    summary   = item.get("raw_summary", "") or ""
    source    = item.get("source", "Unknown")
    published = item.get("published", "")
    news_type = classify_news_type(headline, summary)
    shallow_score = calc_shallow_score(headline, summary, news_type)
    bull, bear, sector_view, macro_view = gen_4view_snaps(headline, news_type)
    cred_eff = effective_credibility(item, headline, summary)
    genre = classify_content_genre(item, headline, summary)
    materiality_score = calc_materiality_score(
        item, headline, summary, news_type, shallow_score, cred_eff, genre,
    )
    binary = detect_binary_event(headline, summary)
    advance = binary or materiality_score >= STAGE2_MATERIALITY_MIN
    return {
        "news_id":             news_id,
        "headline":            headline[:150],
        "headline_zh":         None,  # P0f — digest LLM fills top-N later
        "source":              source,
        "url":                 item.get("url", ""),
        "source_credibility":  item.get("source_credibility", "MEDIUM"),
        "source_kind":         item.get("source_kind", "unknown"),
        "effective_credibility": cred_eff,
        "content_genre":        genre,
        "raw_summary":         (summary or "")[:200],
        "news_type":           news_type,
        "bull_case":           bull,
        "bear_case":           bear,
        "sector_view":         sector_view,
        "macro_view":          macro_view,
        "shallow_score":       shallow_score,
        "materiality_score":   materiality_score,
        "binary_flag":         binary,
        "advance_to_stage2":   advance,
        "advance_reason":      "binary" if binary else ("materiality" if advance else None),
        "published":           published,
    }


def main() -> int:
    if not RAW_FILE.exists():
        print(f"ERROR: {RAW_FILE} not found", file=sys.stderr)
        return 1

    with open(RAW_FILE) as f:
        raw_data = json.load(f)

    items = raw_data.get("items", [])
    print(f"Processing up to {STAGE1_MAX_ITEMS} of {len(items)} raw items...")

    blocked_counts: dict[str, int] = {}
    template_seen: set[str] = set()
    template_dedup_dropped = 0
    items_blocked = 0
    items_dedup   = 0

    verdicts: list[dict] = []
    for i, item in enumerate(items[:STAGE1_MAX_ITEMS]):
        headline = item.get("headline", "") or ""
        summary  = item.get("raw_summary", "") or ""

        # P0a — drop hard-block templates before any scoring
        blocked, reason = _is_blocked(headline, summary)
        if blocked:
            blocked_counts[reason] = blocked_counts.get(reason, 0) + 1
            items_blocked += 1
            continue

        # P0b — collapse identical headline templates across tickers
        template_key = _headline_template_key(headline)
        if template_key and template_key in template_seen:
            template_dedup_dropped += 1
            items_dedup += 1
            continue
        if template_key:
            template_seen.add(template_key)

        verdicts.append(_build_verdict(i, item))

    # Materiality determines scarce Stage 2 budget; shallow_score remains a
    # directional signal only. A quiet day is allowed to advance fewer than 5.
    verdicts.sort(
        key=lambda x: (x["materiality_score"], abs(x["shallow_score"])),
        reverse=True,
    )
    stage2_items = select_stage2_items(verdicts)
    stage2_count = len(stage2_items)

    output = {
        "phase":                  "stage1_triage",
        "timestamp":              datetime.now().isoformat(),
        "raw_count":              len(items),
        "items_scored":           len(verdicts),
        "items_blocked":          items_blocked,
        "items_dedup_dropped":    items_dedup,
        "blocked_counts":         blocked_counts,
        "template_dedup_dropped": template_dedup_dropped,
        "shallow_verdicts":       verdicts[:50],   # Export top 50 for dashboard
        "advanced_count":         stage2_count,
        "stage2_items":           stage2_items,
        "stage1_max_items":       STAGE1_MAX_ITEMS,
    }

    out_path = HERE / "news_logs" / f"{datetime.now().strftime('%Y-%m-%d')}_triage.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(
        f"✅ Stage 1 triage complete: scored={len(verdicts)} "
        f"blocked={items_blocked} dedup={items_dedup} → "
        f"{stage2_count} advanced to Stage 2"
    )
    if blocked_counts:
        print(f"   blocked_counts: {blocked_counts}")
    print(f"   Written to {out_path}")

    # Triage table preview
    print("\nNEWS TRIAGE TABLE:")
    print("─" * 100)
    for v in verdicts[:25]:
        tag = "✅ DEEP" if v["advance_to_stage2"] else "❌ SKIP"
        print(
            f"{tag:10} {v['news_id']:6} [D={v['shallow_score']:+.1f} M={v['materiality_score']:.2f}] "
            f"{v['headline'][:60]:60} {v['news_type']:15}"
        )
    print("─" * 100)
    print(f"Showing 25 of {min(50, len(verdicts))} exported ({len(verdicts)} total scored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

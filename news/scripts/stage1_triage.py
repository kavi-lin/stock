#!/usr/bin/env python3
"""
Stage 1 shallow triage — keyword-based scoring for the day's raw news pool.

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
    binary = (
        any(kw in headline.lower() for kw in BINARY_KEYS)
        and "election" not in headline.lower()
    )
    # Advancement gate — uses effective credibility, not raw provider
    advance = (
        abs(shallow_score) >= 1.5
        or (cred_eff == "HIGH" and abs(shallow_score) >= 0.5)
        or binary
    )
    if abs(shallow_score) >= 3:
        advance_reason = "score"
    elif binary:
        advance_reason = "binary"
    elif cred_eff == "HIGH" and abs(shallow_score) >= 0.5:
        advance_reason = "credibility"
    else:
        advance_reason = None
    return {
        "news_id":             news_id,
        "headline":            headline[:150],
        "headline_zh":         None,  # P0f — digest LLM fills top-N later
        "source":              source,
        "source_credibility":  item.get("source_credibility", "MEDIUM"),
        "effective_credibility": cred_eff,
        "raw_summary":         (summary or "")[:200],
        "news_type":           news_type,
        "bull_case":           bull,
        "bear_case":           bear,
        "sector_view":         sector_view,
        "macro_view":          macro_view,
        "shallow_score":       shallow_score,
        "binary_flag":         binary,
        "advance_to_stage2":   advance,
        "advance_reason":      advance_reason,
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

    # Sort by |shallow_score| desc and pick top-5 for Stage 2
    verdicts.sort(key=lambda x: abs(x["shallow_score"]), reverse=True)
    stage2_count = sum(1 for v in verdicts if v["advance_to_stage2"])
    stage2_count = min(stage2_count, 5)
    for i, v in enumerate(verdicts):
        if i < stage2_count and v["advance_to_stage2"]:
            v["_stage2_rank"] = i + 1
        else:
            v["advance_to_stage2"] = False

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
        "stage2_items":           [v for v in verdicts if v["advance_to_stage2"]],
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
            f"{tag:10} {v['news_id']:6} [{v['shallow_score']:+.1f}] "
            f"{v['headline'][:60]:60} {v['news_type']:15}"
        )
    print("─" * 100)
    print(f"Showing 25 of {min(50, len(verdicts))} exported ({len(verdicts)} total scored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

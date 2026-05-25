#!/usr/bin/env python3
"""
retail-sector-pulse — V3.20.1 trending ticker discovery.

Reads Reddit / HN / Bluesky / Google Trends via scripts/break_news/
social_sources.py; extracts $TICKER + naked-ticker mentions with strict
disambiguation; runs span-masked lexicon match for bull/bear polarity;
aggregates engagement-weighted polarity per ticker → per sector;
buckets sectorless macro posts into market_wide_buzz.

Output: Dashboard/trending_tickers.json (consumed by aggregate.py).

CLI:
  python3 skills/retail-sector-pulse/scripts/trending_tickers.py
  python3 skills/retail-sector-pulse/scripts/trending_tickers.py --window-hours 24 --output /tmp/trending.json
  python3 skills/retail-sector-pulse/scripts/trending_tickers.py --no-fetch --input /tmp/social_items.json   # test mode
"""
import argparse
import json
import math
import re
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "skills" / "_shared"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "break_news"))

from company_context import SECTOR_UNIVERSE, TICKER_TO_SECTOR  # noqa: E402

LEXICON_PATH = HERE.parent / "config" / "retail_lexicon.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "Dashboard" / "trending_tickers.json"


# ── Lexicon loader ───────────────────────────────────────────────────
def load_lexicon(path: Optional[Path] = None) -> dict:
    fp = path or LEXICON_PATH
    with open(fp, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── V3.20.2 helpers — extended sector map + broad ETF set ─────────────
def build_extended_sector_map(lex: dict) -> dict[str, str]:
    """Merge company_context.TICKER_TO_SECTOR (11 mega-cap sector universe)
    with retail_only_sector_overrides from lexicon. Retail-only entries take
    precedence for tickers not in mega-cap universe; mega-cap entries kept
    when both define a ticker (defensive — should be rare)."""
    extended = dict(TICKER_TO_SECTOR)
    overrides = lex.get("retail_only_sector_overrides", {}) or {}
    for sector, tickers in overrides.items():
        for t in (tickers or []):
            if t not in extended:
                extended[t] = sector
    return extended


def get_broad_etf_set(lex: dict) -> set[str]:
    """Tickers in this set are routed to market_wide_buzz instead of any
    individual sector rollup (V3.20.2 Codex feedback)."""
    return set(lex.get("broad_market_etfs", []) or [])


# ── V3.20.3 Truth Social filter ──────────────────────────────────────
def apply_truth_social_filter(post: dict, lex: dict) -> Optional[dict]:
    """Truth Social posts dominate by Trump signatures + political endorsements.
    Strategy:
      1. Strip signatures from text (prevent DJT ticker false-positive from sig)
      2. Relevance check: post text MUST mention economy/markets/macro keyword
         OR one of macro_wide.topic_lexicon entries. Otherwise drop entire post.
    Returns: modified post dict (signature stripped) OR None if dropped.
    Non-Truth-Social posts pass through unchanged.
    """
    platform = (post.get("_source_meta") or {}).get("platform")
    if platform != "truth_social":
        return post

    tsf = lex.get("truth_social_filter", {}) or {}
    if not tsf.get("enabled", True):
        return post

    import re as _re
    headline = post.get("headline") or ""
    summary = post.get("raw_summary") or ""

    # Step 1: strip signatures
    for pat in tsf.get("signature_patterns", []) or []:
        headline = _re.sub(pat, "", headline).strip()
        summary = _re.sub(pat, "", summary).strip()

    # Step 2: relevance check — must hit at least one macro/economic keyword
    text_l = (headline + "\n" + summary).lower()
    extra_kw = [k.lower() for k in (tsf.get("extra_relevance_keywords") or [])]

    # Also include macro_wide.topic_lexicon entries
    mw_lex = (lex.get("market_wide", {}) or {}).get("topic_lexicon", {}) or {}
    macro_terms = [term.lower() for terms in mw_lex.values() for term in (terms or [])]

    all_relevance = extra_kw + macro_terms
    has_relevance = any(kw in text_l for kw in all_relevance)

    if not has_relevance and tsf.get("drop_if_irrelevant", True):
        return None   # caller skips this post

    # Return modified post (signatures stripped)
    return {
        **post,
        "headline": headline,
        "raw_summary": summary,
        "_truth_social_filtered": True,    # debugging marker
    }


# ── Ticker extraction (Codex finding #1: disambiguation) ─────────────
CASHTAG_RE = re.compile(r"\$([A-Z]{1,5})\b")
NAKED_RE = re.compile(r"\b([A-Z]{2,5})\b")


def extract_tickers(text: str, lex: dict) -> tuple[list[str], list[str]]:
    """Extract (qualified_tickers, raw_candidates_rejected) from text.

    Rules per lexicon:
      - $TICKER cashtag always accepted UNLESS in ticker_blocklist
      - Naked TICKER accepted iff:
          * length >= naked_min_length OR in high_liquidity_naked_whitelist
          * NOT in cashtag_only_tickers (unless whitelist override)
          * NOT in ticker_blocklist
    """
    te = lex.get("ticker_extraction", {}) or {}
    blocklist = set(te.get("ticker_blocklist", []) or [])
    cashtag_only = set(te.get("cashtag_only_tickers", []) or [])
    whitelist = set(te.get("high_liquidity_naked_whitelist", []) or [])
    naked_min = int(te.get("naked_min_length", 3))

    qualified: list[str] = []
    rejected: list[str] = []
    seen_in_text = set()  # per-text dedup,1 ticker = 1 mention regardless of repeat

    # Pass 1: cashtags (highest priority)
    for m in CASHTAG_RE.finditer(text):
        t = m.group(1).upper()
        if t in blocklist:
            rejected.append(f"${t}")
            continue
        if t in seen_in_text:
            continue
        seen_in_text.add(t)
        qualified.append(t)

    # Pass 2: naked tickers (gated by rules)
    for m in NAKED_RE.finditer(text):
        t = m.group(1).upper()
        if t in seen_in_text:
            continue
        if t in blocklist:
            rejected.append(t)
            continue
        # whitelist overrides everything
        if t in whitelist:
            seen_in_text.add(t)
            qualified.append(t)
            continue
        # length gate
        if len(t) < naked_min:
            rejected.append(t)
            continue
        # cashtag-only gate
        if t in cashtag_only:
            rejected.append(t)
            continue
        seen_in_text.add(t)
        qualified.append(t)

    return qualified, rejected


# ── Polarity scoring (span-masked, Codex must-fix #2) ────────────────
def compute_polarity(text: str, lex: dict) -> dict:
    """Span-masked polarity computation:
      1. Sort all (term, side) by len(term) DESC
      2. Walk in order; for each term find all non-overlapping occurrences
         within UNCONSUMED spans; mark hit span as consumed
      3. Short terms (e.g. 'short', 'pump') can NOT match inside already-
         consumed spans (e.g. 'short squeeze', 'pump and dump')
    Returns: {polarity, bull_hits, bear_hits, matched_terms}
    """
    if not text:
        return {"polarity": 0.0, "bull_hits": 0, "bear_hits": 0, "matched_terms": []}

    text_l = text.lower()
    n = len(text_l)
    consumed = [False] * n   # per-character consumed mask

    bull_terms = lex.get("bull_terms", []) or []
    bear_terms = lex.get("bear_terms", []) or []
    # tag each term with side then sort by length DESC (LONGEST FIRST)
    candidates = [(t.lower(), "bull") for t in bull_terms] + \
                 [(t.lower(), "bear") for t in bear_terms]
    candidates.sort(key=lambda x: -len(x[0]))

    bull_hits = 0
    bear_hits = 0
    matched: list[tuple[str, str]] = []

    for term, side in candidates:
        if not term:
            continue
        start = 0
        hit_this_term = False
        while True:
            idx = text_l.find(term, start)
            if idx < 0:
                break
            end = idx + len(term)
            # span unconsumed?
            if any(consumed[i] for i in range(idx, end)):
                start = idx + 1
                continue
            # Word-boundary check for ASCII alphanumeric terms — avoid matching
            # 'short' inside 'shortcoming'. CJK / emoji not affected.
            term_first_alnum = term[0].isalnum() and term[0].isascii()
            term_last_alnum = term[-1].isalnum() and term[-1].isascii()
            left_ok = (not term_first_alnum) or idx == 0 or \
                      not text_l[idx - 1].isalnum()
            right_ok = (not term_last_alnum) or end == n or \
                       not text_l[end].isalnum()
            if not (left_ok and right_ok):
                start = idx + 1
                continue
            # accept hit + mask span
            for i in range(idx, end):
                consumed[i] = True
            if not hit_this_term:
                # 1 hit per (term, post) — defends against spam repetition
                if side == "bull":
                    bull_hits += 1
                else:
                    bear_hits += 1
                matched.append((term, side))
                hit_this_term = True
            start = end

    denom = bull_hits + bear_hits + 1
    polarity = (bull_hits - bear_hits) / denom
    return {
        "polarity": round(polarity, 4),
        "bull_hits": bull_hits,
        "bear_hits": bear_hits,
        "matched_terms": [{"term": t, "side": s} for t, s in matched],
    }


# ── Engagement scoring ───────────────────────────────────────────────
def compute_engagement(post: dict) -> float:
    """log-scale engagement. Sources with explicit upvotes/comments use them;
    others fall back to 1.0 (one-post-one-vote)."""
    meta = post.get("_source_meta") or {}
    platform = meta.get("platform")

    if platform == "hacker_news":
        pts = float(meta.get("points") or 0)
        com = float(meta.get("comments") or 0)
        return math.log(pts + 1.0) + math.log(com + 1.0)

    if platform == "bluesky":
        # bsky.app post.likeCount / replyCount not exposed in current adapter;
        # fallback to 1.0 until adapter upgrade.
        return 1.0

    if platform == "reddit":
        # Reddit RSS does not return upvote count.
        return 1.0

    if platform == "google_trends":
        # Trends RSS is just topic existence; treat as flat.
        return 1.0

    return 1.0


# ── Per-post processing ──────────────────────────────────────────────
def process_post(post: dict, lex: dict) -> dict:
    """Annotate one social post with tickers + polarity + engagement."""
    headline = post.get("headline") or ""
    summary = post.get("raw_summary") or ""
    text = f"{headline}\n{summary}"
    tickers, rejected = extract_tickers(text, lex)
    pol = compute_polarity(text, lex)
    eng = compute_engagement(post)
    return {
        "headline": headline,
        "url": post.get("url"),
        "source": post.get("source"),
        "platform": (post.get("_source_meta") or {}).get("platform"),
        "published": post.get("published"),
        "tickers": tickers,
        "rejected_tickers": rejected,
        "engagement": round(eng, 3),
        "polarity": pol["polarity"],
        "bull_hits": pol["bull_hits"],
        "bear_hits": pol["bear_hits"],
        "matched_terms": pol["matched_terms"],
    }


# ── Ticker aggregation (V3.20.2 dual-gate + ETF routing) ──────────────
def aggregate_tickers(processed: list[dict], lex: dict
                      ) -> tuple[list[dict], list[dict], list[dict]]:
    """Roll up per-ticker stats. V3.20.2 changes:
      - Broad-market ETFs (SPY/QQQ/etc.) extracted into separate
        `broad_etf_mentions` return value → caller routes to market_wide bucket
      - Dual-gate thresholds:
          known_sector (in extended sector map) → relaxed (1 mention, eng 1.0)
          unknown_sector (no sector mapping)    → strict   (3 mentions, eng 8.0)
        防止 unknown ticker (例如 lexicon 漏網的假 ticker) 進 sector rollup。

    Returns: (qualified, low_confidence, broad_etf_mentions)
    """
    sector_map = build_extended_sector_map(lex)
    broad_etf_set = get_broad_etf_set(lex)
    by_ticker: dict[str, dict] = {}
    broad_etf_posts: list[dict] = []   # raw posts mentioning ETFs (passed to market_wide)

    for p in processed:
        # Filter ETFs out at intake — they don't enter per-ticker rollup at all
        non_etf_tickers = [t for t in p["tickers"] if t not in broad_etf_set]
        if len(non_etf_tickers) < len(p["tickers"]):
            # Post mentioned at least one broad ETF — annotate + pass to market_wide
            broad_etf_posts.append({
                **p,
                "broad_etfs_mentioned": [t for t in p["tickers"] if t in broad_etf_set],
            })

        for t in non_etf_tickers:
            agg = by_ticker.setdefault(t, {
                "ticker": t,
                "sector": sector_map.get(t),
                "mention_count": 0,
                "engagement_sum": 0.0,
                "polarity_weighted_num": 0.0,   # Σ(engagement × polarity)
                "polarity_weighted_den": 0.0,
                "bull_hits_sum": 0,
                "bear_hits_sum": 0,
                "matched_terms": {},
                "sample_posts": [],
            })
            agg["mention_count"] += 1
            agg["engagement_sum"] += p["engagement"]
            agg["polarity_weighted_num"] += p["engagement"] * p["polarity"]
            agg["polarity_weighted_den"] += p["engagement"]
            agg["bull_hits_sum"] += p["bull_hits"]
            agg["bear_hits_sum"] += p["bear_hits"]
            for mt in p["matched_terms"]:
                agg["matched_terms"][mt["term"]] = mt["side"]
            agg["sample_posts"].append({
                "headline": p["headline"][:200],
                "url": p["url"],
                "source": p["source"],
                "engagement": p["engagement"],
                "polarity": p["polarity"],
                "matched_terms": [mt["term"] for mt in p["matched_terms"]][:10],
            })

    # Finalize each ticker
    for t, agg in by_ticker.items():
        agg["polarity_score"] = round(
            agg["polarity_weighted_num"] / agg["polarity_weighted_den"], 4
        ) if agg["polarity_weighted_den"] > 0 else 0.0
        agg["engagement_score"] = round(agg["engagement_sum"], 3)
        agg.pop("polarity_weighted_num")
        agg.pop("polarity_weighted_den")
        agg.pop("engagement_sum")
        agg["sample_posts"].sort(key=lambda s: -s["engagement"])
        agg["sample_posts"] = agg["sample_posts"][:3]
        agg["matched_terms"] = [{"term": t_, "side": s_}
                                for t_, s_ in agg["matched_terms"].items()]

    # ── Dual-gate thresholds (V3.20.2) ─────────────────────────────────
    inc = lex.get("ticker_inclusion", {}) or {}
    known_gate = inc.get("known_sector") or {}
    unk_gate = inc.get("unknown_sector") or {}
    # Backward-compat: if old single-gate config used, fall back to it
    legacy_min_m = inc.get("min_mention_count")
    legacy_min_e = inc.get("min_total_engagement")
    if legacy_min_m is not None and legacy_min_e is not None and not known_gate:
        known_gate = {"min_mention_count": int(legacy_min_m),
                      "min_total_engagement": float(legacy_min_e)}
        unk_gate = dict(known_gate)

    known_m = int(known_gate.get("min_mention_count", 1))
    known_e = float(known_gate.get("min_total_engagement", 1.0))
    unk_m = int(unk_gate.get("min_mention_count", 3))
    unk_e = float(unk_gate.get("min_total_engagement", 8.0))
    max_low_conf = int(inc.get("max_low_confidence_kept", 30))

    qualified = []
    low_conf = []
    for agg in by_ticker.values():
        has_sector = agg.get("sector") is not None
        m_min = known_m if has_sector else unk_m
        e_min = known_e if has_sector else unk_e
        agg["_gate"] = "known" if has_sector else "unknown"  # for audit
        if agg["mention_count"] >= m_min and agg["engagement_score"] >= e_min:
            qualified.append(agg)
        else:
            low_conf.append(agg)

    qualified.sort(key=lambda a: -a["engagement_score"])
    low_conf.sort(key=lambda a: -a["engagement_score"])
    return qualified, low_conf[:max_low_conf], broad_etf_posts


# ── Sector rollup ────────────────────────────────────────────────────
def aggregate_sectors(qualified: list[dict], lex: dict) -> list[dict]:
    """Sector-level rollup from qualified tickers.

    V3.20.2: per-ticker `sector` is set from extended sector map (mega-cap
    universe + retail_only_sector_overrides) in aggregate_tickers,所以這裡
    直接讀 t['sector'] 即可。Unknown-sector qualified tickers (跨過 unknown
    gate 的) 在這裡 still 沒 sector → skip rollup,留在 qualified 給 audit。
    """
    inc = lex.get("ticker_inclusion", {}) or {}
    max_top = int(inc.get("max_tickers_per_sector", 8))

    by_sector: dict[str, dict] = {}
    for t in qualified:
        sec = t.get("sector")
        if not sec:
            continue  # unknown-sector qualified tickers stay in `tickers[]` only
        agg = by_sector.setdefault(sec, {
            "sector": sec,
            "ticker_count": 0,
            "engagement_score": 0.0,
            "polarity_weighted_num": 0.0,
            "polarity_weighted_den": 0.0,
            "bull_hits_sum": 0,
            "bear_hits_sum": 0,
            "top_tickers": [],
        })
        agg["ticker_count"] += 1
        agg["engagement_score"] += t["engagement_score"]
        agg["polarity_weighted_num"] += t["polarity_score"] * t["engagement_score"]
        agg["polarity_weighted_den"] += t["engagement_score"]
        agg["bull_hits_sum"] += t["bull_hits_sum"]
        agg["bear_hits_sum"] += t["bear_hits_sum"]
        agg["top_tickers"].append({
            "ticker": t["ticker"],
            "engagement_score": t["engagement_score"],
            "polarity_score": t["polarity_score"],
            "mention_count": t["mention_count"],
        })

    out = []
    for sec, agg in by_sector.items():
        agg["polarity_score"] = round(
            agg["polarity_weighted_num"] / agg["polarity_weighted_den"], 4
        ) if agg["polarity_weighted_den"] > 0 else 0.0
        agg["engagement_score"] = round(agg["engagement_score"], 3)
        agg.pop("polarity_weighted_num")
        agg.pop("polarity_weighted_den")
        agg["top_tickers"].sort(key=lambda x: -x["engagement_score"])
        agg["top_tickers"] = agg["top_tickers"][:max_top]
        out.append(agg)

    # Ensure all 11 sectors present (empty if no qualified tickers)
    for sec in SECTOR_UNIVERSE.keys():
        if sec not in by_sector:
            out.append({
                "sector": sec, "ticker_count": 0, "engagement_score": 0.0,
                "polarity_score": 0.0, "bull_hits_sum": 0, "bear_hits_sum": 0,
                "top_tickers": [],
            })

    out.sort(key=lambda s: -s["engagement_score"])
    return out


# ── Market-wide buzz (Codex finding #3 + V3.20.2 broad ETF routing) ──
def aggregate_market_wide(processed: list[dict], lex: dict,
                          broad_etf_posts: Optional[list[dict]] = None
                          ) -> list[dict]:
    """Posts with NO ticker (or >5 tickers — broad-market) get classified by
    macro topic lexicon. Returns top topics by engagement.

    V3.20.2: posts mentioning broad-market ETFs (SPY/QQQ/IWM/DIA/...) are also
    routed here under a synthetic 'broad_etf' topic — these don't belong to a
    single GICS sector and should be displayed at market-wide level.
    """
    mw_cfg = lex.get("market_wide", {}) or {}
    if not mw_cfg.get("collect"):
        return []
    trigger = mw_cfg.get("trigger", {}) or {}
    no_ticker_trigger = bool(trigger.get("no_ticker_extracted", True))
    too_many = int(trigger.get("ticker_count_above", 5))
    topic_lex = mw_cfg.get("topic_lexicon", {}) or {}
    min_eng = float(mw_cfg.get("min_topic_engagement", 5.0))
    max_topics = int(mw_cfg.get("max_topics_displayed", 6))

    # For matching, build flat (topic, term) list sorted by len DESC
    flat = [(topic, term.lower())
            for topic, terms in topic_lex.items() for term in (terms or [])]
    flat.sort(key=lambda x: -len(x[1]))

    by_topic: dict[str, dict] = {}

    def _accum_topic(topic: str, p: dict):
        agg = by_topic.setdefault(topic, {
            "topic": topic, "post_count": 0,
            "engagement_score": 0.0,
            "polarity_weighted_num": 0.0, "polarity_weighted_den": 0.0,
            "sample_posts": [],
        })
        agg["post_count"] += 1
        agg["engagement_score"] += p["engagement"]
        agg["polarity_weighted_num"] += p["engagement"] * p["polarity"]
        agg["polarity_weighted_den"] += p["engagement"]
        agg["sample_posts"].append({
            "headline": p["headline"][:200], "url": p.get("url"),
            "source": p.get("source"), "engagement": p["engagement"],
            "polarity": p["polarity"],
        })

    # Pass 1: broad-content posts (no ticker or > 5 tickers) → topic_lexicon match
    for p in processed:
        nt = len(p["tickers"])
        broad = (no_ticker_trigger and nt == 0) or nt > too_many
        if not broad:
            continue
        text_l = (p["headline"] + "\n" + (p.get("source") or "")).lower()
        matched_topics = set()
        for topic, term in flat:
            if term in text_l:
                matched_topics.add(topic)
        for topic in matched_topics:
            _accum_topic(topic, p)

    # Pass 2 (V3.20.2): posts mentioning broad-market ETFs → synthetic
    # 'broad_etf' topic + 'market_direction' (since SPY/QQQ proxies the broad market)
    for p in (broad_etf_posts or []):
        _accum_topic("broad_etf", p)
        _accum_topic("market_direction", p)

    out = []
    for topic, agg in by_topic.items():
        if agg["engagement_score"] < min_eng:
            continue
        agg["polarity_score"] = round(
            agg["polarity_weighted_num"] / agg["polarity_weighted_den"], 4
        ) if agg["polarity_weighted_den"] > 0 else 0.0
        agg["engagement_score"] = round(agg["engagement_score"], 3)
        agg.pop("polarity_weighted_num")
        agg.pop("polarity_weighted_den")
        agg["sample_posts"].sort(key=lambda s: -s["engagement"])
        agg["sample_posts"] = agg["sample_posts"][:3]
        out.append(agg)

    out.sort(key=lambda x: -x["engagement_score"])
    return out[:max_topics]


# ── Source stats ─────────────────────────────────────────────────────
def compute_source_stats(processed: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for p in processed:
        plat = p.get("platform") or "unknown"
        counts[plat] = counts.get(plat, 0) + 1
    return counts


# ── Main entry ───────────────────────────────────────────────────────
def run(window_hours: int = 24, social_items: Optional[list[dict]] = None) -> dict:
    """Top-level orchestration. If `social_items` is None, fetch live.
    Returns full payload dict.
    """
    lex = load_lexicon()

    # 1. Fetch posts (or use provided fixture)
    if social_items is None:
        from social_sources import fetch_social_items  # break_news/social_sources.py
        social_items, _stats = fetch_social_items(window_hours=window_hours)

    # 1b. V3.20.3: Truth Social relevance filter + signature strip
    #     drops political-only posts; strips "President DJT" signatures
    filtered_items = []
    truth_social_dropped = 0
    for p in social_items:
        filtered = apply_truth_social_filter(p, lex)
        if filtered is None:
            truth_social_dropped += 1
            continue
        filtered_items.append(filtered)

    # 2. Per-post processing
    processed = [process_post(p, lex) for p in filtered_items]

    # 3. Ticker aggregation + thresholds
    qualified, low_conf, broad_etf_posts = aggregate_tickers(processed, lex)

    # 4. Sector rollup
    sectors = aggregate_sectors(qualified, lex)

    # 5. Market-wide buzz
    market_wide = aggregate_market_wide(processed, lex, broad_etf_posts=broad_etf_posts)

    # 6. Source stats
    source_stats = compute_source_stats(processed)

    return {
        "version": "1.0",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "lookback_hours": window_hours,
        "lexicon_version": lex.get("lexicon_version", "unknown"),
        "post_count": len(processed),
        "truth_social_dropped": truth_social_dropped,
        "source_stats": source_stats,
        "tickers": qualified,
        "low_confidence": low_conf,
        "sectors": sectors,
        "market_wide_buzz": market_wide,
    }


def main():
    ap = argparse.ArgumentParser(description="retail-sector-pulse trending ticker discovery")
    ap.add_argument("--window-hours", type=int, default=24)
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    ap.add_argument("--input", help="(test mode) read social items from JSON file instead of fetching")
    ap.add_argument("--no-fetch", action="store_true",
                    help="Alias for --input; expects --input fixture path")
    args = ap.parse_args()

    social_items = None
    if args.input:
        with open(args.input, encoding="utf-8") as f:
            social_items = json.load(f)
        if isinstance(social_items, dict) and "items" in social_items:
            social_items = social_items["items"]

    payload = run(window_hours=args.window_hours, social_items=social_items)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

    print(
        f"[trending-tickers] wrote {out_path} "
        f"(posts={payload['post_count']}, tickers={len(payload['tickers'])}, "
        f"low_conf={len(payload['low_confidence'])}, sectors_with_data="
        f"{sum(1 for s in payload['sectors'] if s['ticker_count'] > 0)}, "
        f"market_wide_topics={len(payload['market_wide_buzz'])})",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()

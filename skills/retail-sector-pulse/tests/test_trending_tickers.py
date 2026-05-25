#!/usr/bin/env python3
"""
retail-sector-pulse — V3.20.1 unit tests for trending_tickers.py.

Codex must-fix verification:
  #1 ticker disambiguation (cashtag-only / blocklist / whitelist)
  #2 span-masked polarity (short squeeze ≠ short, pump and dump ≠ pump+dump)
  #3 market-wide buzz bucket for sectorless posts
  + inclusion thresholds + engagement aggregation + lexicon_version pass-through
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

from trending_tickers import (  # noqa: E402
    load_lexicon,
    extract_tickers,
    compute_polarity,
    compute_engagement,
    aggregate_tickers,
    aggregate_sectors,
    aggregate_market_wide,
    run,
)


def _post(headline: str, *, source: str = "Reddit:r/wallstreetbets",
          platform: str = "reddit", points: int = None, comments: int = None,
          summary: str = "") -> dict:
    """Build a synthetic social post dict matching social_sources schema."""
    meta = {"platform": platform}
    if points is not None:
        meta["points"] = points
    if comments is not None:
        meta["comments"] = comments
    return {
        "headline": headline,
        "raw_summary": summary,
        "source": source,
        "url": f"https://example.com/{abs(hash(headline)) % 100000}",
        "published": "2026-05-25T10:00:00+00:00",
        "_source_meta": meta,
    }


class TestTickerDisambiguation(unittest.TestCase):
    """Codex must-fix #1."""

    def setUp(self):
        self.lex = load_lexicon()

    def test_cashtag_always_wins(self):
        q, _ = extract_tickers("$NVDA to the moon!", self.lex)
        self.assertIn("NVDA", q)

    def test_naked_whitelist(self):
        # NVDA / TSLA / AAPL / AMD / SMCI / PLTR allowed naked
        q, _ = extract_tickers("NVDA TSLA AAPL AMD SMCI PLTR all ripping", self.lex)
        for t in ("NVDA", "TSLA", "AAPL", "AMD", "SMCI", "PLTR"):
            self.assertIn(t, q, f"{t} must match naked via whitelist")

    def test_naked_short_ticker_rejected(self):
        # ON / IT / AI / X / BE in cashtag-only — naked rejected
        for word in ("ON", "IT", "AI", "BE"):
            text = f"Fed cuts {word} Wednesday rates"
            q, r = extract_tickers(text, self.lex)
            self.assertNotIn(word, q, f"naked '{word}' must be rejected (cashtag-only)")

    def test_cashtag_bypasses_cashtag_only(self):
        # $AI should accept because cashtag wins, but $IPO blocklisted
        q, _ = extract_tickers("$AI rocketing today", self.lex)
        self.assertIn("AI", q)

    def test_blocklist_rejects_even_cashtag(self):
        # IPO / FED / CPI in blocklist — even $IPO must be rejected
        q, r = extract_tickers("$IPO market is hot", self.lex)
        self.assertNotIn("IPO", q)
        self.assertIn("$IPO", r)

    def test_naked_min_length(self):
        # Length 2 tickers not in whitelist must be rejected
        q, _ = extract_tickers("AB CD EF the quick brown fox", self.lex)
        # None of AB/CD/EF are in known list AND length<3 OR cashtag-only → rejected
        self.assertEqual(q, [])

    def test_dedup_within_text(self):
        # NVDA mentioned 3 times → counted only once per post
        q, _ = extract_tickers("$NVDA $NVDA NVDA going up", self.lex)
        self.assertEqual(q.count("NVDA"), 1)


class TestSpanMaskedPolarity(unittest.TestCase):
    """Codex must-fix #2."""

    def setUp(self):
        self.lex = load_lexicon()

    def test_short_squeeze_not_short(self):
        """`short squeeze` must register as bull, NOT also fire `short` as bear."""
        p = compute_polarity("NVDA short squeeze incoming", self.lex)
        self.assertEqual(p["bull_hits"], 1)
        self.assertEqual(p["bear_hits"], 0)
        terms = [m["term"] for m in p["matched_terms"]]
        self.assertIn("short squeeze", terms)
        self.assertNotIn("short", terms)

    def test_pump_and_dump_not_pump_and_dump(self):
        """`pump and dump` must register as bear, NOT also fire `pump` (bull) + `dump` (bear)."""
        p = compute_polarity("classic pump and dump scheme", self.lex)
        self.assertEqual(p["bull_hits"], 0)
        self.assertEqual(p["bear_hits"], 1)
        terms = [m["term"] for m in p["matched_terms"]]
        self.assertIn("pump and dump", terms)
        self.assertNotIn("pump", terms)
        self.assertNotIn("dump", terms)

    def test_to_the_moon_not_moon(self):
        """`to the moon` longest first; should not double-count `moon` separately."""
        p = compute_polarity("NVDA to the moon", self.lex)
        terms = [m["term"] for m in p["matched_terms"]]
        self.assertIn("to the moon", terms)
        self.assertNotIn("moon", terms)
        self.assertEqual(p["bull_hits"], 1)

    def test_mixed_bull_bear(self):
        """A post with both bull + bear keywords must show both."""
        p = compute_polarity("TSLA puts printing, diamond hands selling pressure",
                             self.lex)
        # diamond hands = bull, puts printing = bear, selling pressure = bear
        self.assertEqual(p["bull_hits"], 1)
        self.assertEqual(p["bear_hits"], 2)
        # polarity = (1-2)/(1+2+1) = -0.25
        self.assertAlmostEqual(p["polarity"], -0.25, places=3)

    def test_chinese_terms(self):
        p = compute_polarity("看漲 NVDA 強烈 抄底", self.lex)
        self.assertGreater(p["bull_hits"], 0)

    def test_yazuo_in_bear(self):
        """軋多 must be in bear list (Codex fix — was wrongly in bull V1.0 draft)."""
        p = compute_polarity("NVDA 軋多 殺多了", self.lex)
        self.assertEqual(p["bear_hits"], 1)
        self.assertEqual(p["bull_hits"], 0)

    def test_repeated_term_counted_once_per_term(self):
        """`moon moon moon` repeats `moon` 3 times but should fire bull_hits=1
        (per-term-once-per-post defense against spam repetition)."""
        p = compute_polarity("moon moon moon", self.lex)
        self.assertEqual(p["bull_hits"], 1)
        # But distinct terms ("to the moon" + "moon") DO each fire — they're
        # separate dictionary entries by design.
        p2 = compute_polarity("moon moon to the moon", self.lex)
        self.assertEqual(p2["bull_hits"], 2,
                         "to the moon AND naked moon are separate lexicon entries → 2 hits")

    def test_word_boundary(self):
        """`shortcoming` must NOT match `short`."""
        p = compute_polarity("the shortcoming was minor", self.lex)
        self.assertEqual(p["bear_hits"], 0)

    def test_neutral_text(self):
        p = compute_polarity("Just a regular news headline", self.lex)
        self.assertEqual(p["polarity"], 0.0)
        self.assertEqual(p["bull_hits"], 0)
        self.assertEqual(p["bear_hits"], 0)


class TestEngagement(unittest.TestCase):
    def test_hn_with_points_comments(self):
        post = _post("test", platform="hacker_news", points=100, comments=50)
        # log(101) + log(51) ≈ 4.62 + 3.93 ≈ 8.55
        eng = compute_engagement(post)
        self.assertAlmostEqual(eng, 8.55, places=1)

    def test_reddit_fallback_one(self):
        post = _post("test", platform="reddit")
        self.assertEqual(compute_engagement(post), 1.0)

    def test_unknown_platform_fallback(self):
        post = _post("test", platform="something_new")
        self.assertEqual(compute_engagement(post), 1.0)


class TestThresholds(unittest.TestCase):
    def setUp(self):
        self.lex = load_lexicon()

    def test_known_sector_single_mention_passes(self):
        """V3.20.2: known-sector ticker (NVDA in TICKER_TO_SECTOR) with 1 Reddit
        mention (eng=1.0) PASSES the relaxed known-sector gate."""
        posts = [_post("$NVDA looking good", platform="reddit")]
        from trending_tickers import process_post
        processed = [process_post(p, self.lex) for p in posts]
        qual, low, _etfs = aggregate_tickers(processed, self.lex)
        self.assertEqual(len(qual), 1,
                         "V3.20.2 known-sector gate (1 mention, 1.0 eng) accepts NVDA")
        self.assertEqual(qual[0]["ticker"], "NVDA")

    def test_high_engagement_single_mention_qualifies(self):
        """V3.20.2: HN 1000pts + 500 comments single mention passes known gate."""
        posts = [_post("$NVDA breakout", platform="hacker_news",
                       points=1000, comments=500)]
        from trending_tickers import process_post
        processed = [process_post(p, self.lex) for p in posts]
        qual, low, _etfs = aggregate_tickers(processed, self.lex)
        self.assertEqual(len(qual), 1,
                         "V3.20.2: known sector + 1 mention OK regardless of engagement floor")

    def test_two_mentions_high_engagement_qualifies(self):
        posts = [
            _post("$NVDA breakout", platform="hacker_news", points=200, comments=100),
            _post("$NVDA earnings beat", platform="reddit"),
        ]
        from trending_tickers import process_post
        processed = [process_post(p, self.lex) for p in posts]
        qual, _, _etfs = aggregate_tickers(processed, self.lex)
        self.assertEqual(len(qual), 1)
        self.assertEqual(qual[0]["ticker"], "NVDA")
        self.assertEqual(qual[0]["mention_count"], 2)


class TestSectorRollup(unittest.TestCase):
    def setUp(self):
        self.lex = load_lexicon()

    def test_qualified_tickers_grouped_by_sector(self):
        """Tickers outside SECTOR_TOP_5 should still rollup if they're in TICKER_TO_SECTOR."""
        from trending_tickers import process_post
        posts = [
            _post("$NVDA bull", platform="hacker_news", points=200, comments=100),
            _post("$NVDA breakout", platform="reddit"),
            _post("$AMD calls", platform="hacker_news", points=150, comments=80),
            _post("$AMD ripping", platform="reddit"),
        ]
        processed = [process_post(p, self.lex) for p in posts]
        qual, _, _etfs = aggregate_tickers(processed, self.lex)
        sectors = aggregate_sectors(qual, self.lex)
        tech = [s for s in sectors if s["sector"] == "Technology"][0]
        self.assertEqual(tech["ticker_count"], 2)
        self.assertGreater(tech["engagement_score"], 5.0)

    def test_all_11_sectors_present(self):
        sectors = aggregate_sectors([], self.lex)
        names = {s["sector"] for s in sectors}
        for required in ("Technology", "Healthcare", "Energy", "Financials",
                         "Consumer_Discretionary", "Consumer_Staples",
                         "Industrials", "Materials", "Utilities",
                         "Real_Estate", "Communication"):
            self.assertIn(required, names)


class TestMarketWideBuzz(unittest.TestCase):
    """Codex must-fix #3 — sectorless macro posts go to market_wide bucket."""

    def setUp(self):
        self.lex = load_lexicon()

    def test_no_ticker_post_classifies_as_topic(self):
        """A post mentioning Fed but no ticker → market_wide_buzz.fed"""
        from trending_tickers import process_post
        posts = [
            _post("Fed cuts rates next week, Powell pivot",
                  platform="hacker_news", points=200, comments=100,
                  summary="rate cut imminent FOMC dovish"),
        ]
        processed = [process_post(p, self.lex) for p in posts]
        # Confirm no tickers extracted
        self.assertEqual(processed[0]["tickers"], [])
        mw = aggregate_market_wide(processed, self.lex)
        topics = {m["topic"] for m in mw}
        self.assertIn("fed", topics)

    def test_too_many_tickers_post_goes_market_wide(self):
        """Post mentioning 6+ tickers (broad-market sweep) goes to market_wide bucket too."""
        from trending_tickers import process_post
        posts = [
            _post("$NVDA $TSLA $AAPL $AMD $MSFT $GOOGL $META all rally — bull market",
                  platform="hacker_news", points=300, comments=150),
        ]
        processed = [process_post(p, self.lex) for p in posts]
        self.assertGreater(len(processed[0]["tickers"]), 5)
        mw = aggregate_market_wide(processed, self.lex)
        topics = {m["topic"] for m in mw}
        self.assertIn("market_direction", topics)


class TestLexiconVersionPropagation(unittest.TestCase):
    def test_lexicon_version_in_payload(self):
        payload = run(window_hours=24, social_items=[])
        # v1.2: V3.20.2 dual-gate + retail overrides + broad ETF routing
        self.assertEqual(payload["lexicon_version"], "v1.2")
        self.assertEqual(payload["version"], "1.0")  # output schema version,not lexicon
        # Should always return 11 sectors even with no data
        self.assertEqual(len(payload["sectors"]), 11)


class TestV202DualGate(unittest.TestCase):
    """V3.20.2 Codex review — dual-gate (known vs unknown sector) + retail
    override + broad ETF routing to market_wide bucket."""

    def setUp(self):
        self.lex = load_lexicon()

    def test_v202_blocklist_extensions(self):
        """LONG/CALLS/EARLY/GPU/NYSE/TRUMP/NIFTY/RINOS must be blocklisted."""
        for word in ("LONG", "CALLS", "EARLY", "GPU", "NYSE", "TRUMP",
                     "NIFTY", "RINOS"):
            text = f"watch ${word} ripping today"
            q, r = extract_tickers(text, self.lex)
            self.assertNotIn(word, q,
                             f"v1.2 blocklist must reject naked '{word}'")
            self.assertIn(f"${word}", r,
                          f"v1.2 blocklist must reject ${word} cashtag")

    def test_known_sector_relaxed_gate(self):
        """Single Reddit mention of NVDA (eng=1.0) should pass known-sector gate."""
        posts = [_post("$NVDA looking good", platform="reddit")]
        from trending_tickers import process_post
        processed = [process_post(p, self.lex) for p in posts]
        qual, low, _etfs = aggregate_tickers(processed, self.lex)
        nvda = [t for t in qual if t["ticker"] == "NVDA"]
        self.assertEqual(len(nvda), 1,
                         "NVDA known-sector should pass relaxed gate (1 mention, 1.0 eng)")
        self.assertEqual(nvda[0].get("_gate"), "known")

    def test_unknown_sector_strict_gate(self):
        """Single mention of unknown ticker (e.g. SXC) → low_confidence."""
        posts = [_post("$SXC moving today", platform="reddit")]
        from trending_tickers import process_post
        processed = [process_post(p, self.lex) for p in posts]
        qual, low, _etfs = aggregate_tickers(processed, self.lex)
        sxc_qual = [t for t in qual if t["ticker"] == "SXC"]
        sxc_low = [t for t in low if t["ticker"] == "SXC"]
        self.assertEqual(len(sxc_qual), 0,
                         "SXC (no sector mapping) must NOT pass unknown gate with 1 mention")
        self.assertEqual(len(sxc_low), 1)
        self.assertEqual(sxc_low[0].get("_gate"), "unknown")

    def test_retail_only_sector_override(self):
        """DJT (not in SECTOR_UNIVERSE) should be mapped to Consumer_Discretionary
        via retail_only_sector_overrides + pass known-sector gate."""
        posts = [_post("$DJT mooning today", platform="reddit")]
        from trending_tickers import process_post
        processed = [process_post(p, self.lex) for p in posts]
        qual, _low, _etfs = aggregate_tickers(processed, self.lex)
        djt = [t for t in qual if t["ticker"] == "DJT"]
        self.assertEqual(len(djt), 1, "DJT must qualify via retail override")
        self.assertEqual(djt[0]["sector"], "Consumer_Discretionary")
        self.assertEqual(djt[0].get("_gate"), "known")

    def test_broad_etf_routes_to_market_wide(self):
        """SPY / QQQ mentions should NOT enter per-ticker rollup; should appear
        as broad_etf_posts return value (3rd tuple element) instead."""
        posts = [
            _post("$SPY breaking out, going to all-time high",
                  platform="hacker_news", points=200, comments=100),
            _post("$QQQ leading market direction",
                  platform="reddit"),
        ]
        from trending_tickers import process_post
        processed = [process_post(p, self.lex) for p in posts]
        qual, low, etfs = aggregate_tickers(processed, self.lex)
        # SPY/QQQ must NOT be in qual or low — they're filtered out entirely
        tickers_in_pipeline = {t["ticker"] for t in qual} | {t["ticker"] for t in low}
        self.assertNotIn("SPY", tickers_in_pipeline)
        self.assertNotIn("QQQ", tickers_in_pipeline)
        # ETF posts captured for market_wide routing
        self.assertEqual(len(etfs), 2)
        etfs_seen = {t for p in etfs for t in p["broad_etfs_mentioned"]}
        self.assertIn("SPY", etfs_seen)
        self.assertIn("QQQ", etfs_seen)

    def test_broad_etf_appears_in_market_wide_buzz(self):
        """End-to-end: SPY mention → market_wide_buzz topic = 'broad_etf' or
        'market_direction'."""
        posts = [
            _post("$SPY new all-time high",
                  platform="hacker_news", points=500, comments=200),
        ]
        payload = run(window_hours=24, social_items=posts)
        topics = {m["topic"] for m in payload["market_wide_buzz"]}
        self.assertTrue("broad_etf" in topics or "market_direction" in topics,
                        f"SPY post must show up in market_wide_buzz; got topics: {topics}")

    def test_legacy_single_gate_backward_compat(self):
        """If a user-edited lexicon uses old single-gate config (V3.20.0 style),
        aggregate_tickers must still work (use legacy fields as fallback)."""
        legacy_lex = dict(self.lex)
        legacy_lex["ticker_inclusion"] = {
            "min_mention_count": 2,
            "min_total_engagement": 5.0,
        }
        posts = [_post("$NVDA up", platform="hacker_news", points=200, comments=100)]
        from trending_tickers import process_post
        processed = [process_post(p, legacy_lex) for p in posts]
        # Should still run without crashing (returns 3-tuple)
        qual, low, etfs = aggregate_tickers(processed, legacy_lex)
        # NVDA: 1 mention,fails legacy min=2
        self.assertEqual(len(qual), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

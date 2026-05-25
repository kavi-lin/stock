#!/usr/bin/env python3
"""
retail-sector-pulse — unit tests for aggregate.py (no network, no predict.py subprocess).
"""
import json
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

from aggregate import (  # noqa: E402
    bucket_label,
    composite_score,
    aggregate_news_sentiment,
    aggregate_retail_volume,
    aggregate_predictions,
    make_framing,
    make_framing_v2,
    normalize_sector_name,
    load_config,
)


def _verdict(score: float, sectors_list: list[str], age_hours: float = 1.0,
             headline: str = "test", source: str = "CNBC", verdict: str = "NEUTRAL") -> dict:
    """Build a synthetic verdict with `_published_dt` pre-parsed."""
    return {
        "verdict": verdict,
        "net_impact_score": score,
        "affected_sectors": [{"sector": s, "direction": "bullish"} for s in sectors_list],
        "tickers_mentioned": [],
        "headline": headline,
        "source_label": source,
        "published": (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat(),
        "_published_dt": datetime.now(timezone.utc) - timedelta(hours=age_hours),
        "_source_file": "test",
    }


class TestNormalizeSectorName(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config()
        self.aliases = self.cfg.get("sector_aliases", {})

    def test_canonical_passes_through(self):
        self.assertEqual(normalize_sector_name("Technology", self.aliases), "Technology")
        self.assertEqual(normalize_sector_name("Real_Estate", self.aliases), "Real_Estate")

    def test_messy_variants_normalized(self):
        # Codex finding: digest sector strings are messy
        self.assertEqual(normalize_sector_name("Tech", self.aliases), "Technology")
        self.assertEqual(normalize_sector_name("Semiconductors", self.aliases), "Technology")
        self.assertEqual(normalize_sector_name("Real Estate", self.aliases), "Real_Estate")
        self.assertEqual(normalize_sector_name("Real-estate", self.aliases), "Real_Estate")
        self.assertEqual(normalize_sector_name("Health Care", self.aliases), "Healthcare")
        self.assertEqual(normalize_sector_name("Defense", self.aliases), "Industrials")
        self.assertEqual(normalize_sector_name("Consumer Discretionary", self.aliases),
                         "Consumer_Discretionary")

    def test_unknown_returns_none(self):
        self.assertIsNone(normalize_sector_name("Crypto", self.aliases))
        self.assertIsNone(normalize_sector_name("", self.aliases))
        self.assertIsNone(normalize_sector_name(None, self.aliases))


class TestBucketLabel(unittest.TestCase):
    def setUp(self):
        self.dir_buckets = load_config()["direction_labels"]
        self.news_buckets = load_config()["news_sentiment_labels"]

    def test_direction_buckets(self):
        self.assertEqual(bucket_label( 0.75, self.dir_buckets), "strong_bull")
        self.assertEqual(bucket_label( 0.30, self.dir_buckets), "mod_bull")
        self.assertEqual(bucket_label( 0.0,  self.dir_buckets), "neutral_mixed")
        self.assertEqual(bucket_label(-0.30, self.dir_buckets), "mod_bear")
        self.assertEqual(bucket_label(-0.75, self.dir_buckets), "strong_bear")

    def test_edge_at_lo_bound_inclusive(self):
        # (lo, hi] semantics: lo is inclusive
        self.assertEqual(bucket_label(0.20, self.dir_buckets), "mod_bull")

    def test_news_bucket_strong_bear(self):
        self.assertEqual(bucket_label(-3.5, self.news_buckets), "strong_bear")
        self.assertEqual(bucket_label(-1.5, self.news_buckets), "mod_bear")


class TestNewsSentimentWeightedAvg(unittest.TestCase):
    """Test 1: news weighted mean with 12h half-life decay."""

    def setUp(self):
        self.cfg = load_config()

    def test_single_fresh_verdict(self):
        verdicts = [_verdict(+2.0, ["Technology"], age_hours=0.0)]
        r = aggregate_news_sentiment("Technology", verdicts, self.cfg)
        self.assertEqual(r["count"], 1)
        self.assertAlmostEqual(r["score"], 2.0, places=1)
        self.assertEqual(r["label"], "mod_bull")

    def test_multiple_with_decay(self):
        # Fresh +2 (full weight ~1.0), old -2 at 24h (weight = 0.5^(24/12)=0.25),
        # mid +3 at 12h (weight 0.5)
        # weighted = (1.0*2 + 0.5*3 + 0.25*-2) / (1.0+0.5+0.25) = 3.0/1.75 ≈ 1.71
        verdicts = [
            _verdict(+2.0, ["Technology"], age_hours=0.0),
            _verdict(+3.0, ["Technology"], age_hours=12.0),
            _verdict(-2.0, ["Technology"], age_hours=24.0),
        ]
        r = aggregate_news_sentiment("Technology", verdicts, self.cfg)
        self.assertEqual(r["count"], 3)
        self.assertAlmostEqual(r["score"], 1.71, places=1)

    def test_no_match_returns_none(self):
        verdicts = [_verdict(+2.0, ["Energy"], age_hours=1.0)]
        r = aggregate_news_sentiment("Technology", verdicts, self.cfg)
        self.assertIsNone(r["score"])
        self.assertEqual(r["count"], 0)

    def test_alias_match(self):
        # Digest uses "Tech" but our canonical is "Technology"
        v = _verdict(+1.5, ["Tech"], age_hours=1.0)
        r = aggregate_news_sentiment("Technology", [v], self.cfg)
        self.assertEqual(r["count"], 1)
        self.assertAlmostEqual(r["score"], 1.5, places=1)

    def test_breadth_wide_vs_narrow(self):
        v1 = _verdict(+1.0, ["Technology"], source="CNBC")
        v2 = _verdict(+1.0, ["Technology"], source="Bloomberg")
        v3 = _verdict(+1.0, ["Technology"], source="WSJ")
        r_wide = aggregate_news_sentiment("Technology", [v1, v2, v3], self.cfg)
        self.assertEqual(r_wide["breadth"], "wide")
        r_narrow = aggregate_news_sentiment("Technology", [v1, v2], self.cfg)
        self.assertEqual(r_narrow["breadth"], "narrow")


class TestRetailVolume(unittest.TestCase):
    """Test 2: retail volume median + max ticker (uses real NPD cache or skips)."""

    def test_no_cache_returns_none(self):
        # Pick a ticker we know doesn't exist
        cfg = load_config()
        r = aggregate_retail_volume(["XYZNOEXIST"], cfg)
        self.assertIsNone(r["score"])
        self.assertEqual(r["sample_size"], 0)
        self.assertEqual(r["label"], "calm")


class TestPredictionAggregation(unittest.TestCase):
    """Test 3: 5d prediction aggregation (uses skip_predict for unit test)."""

    def test_skip_predict_returns_none(self):
        cfg = load_config()
        r = aggregate_predictions(["AAPL", "MSFT"], cfg, skip_predict=True)
        self.assertIsNone(r["median_pct"])
        self.assertEqual(r["ok_count"], 0)


class TestCompositeFormula(unittest.TestCase):
    """Test 4: V3.20.1 three-lane composite per weights.yaml v1.1:
       price_5d_norm (0.30) + retail_polarity_signed (0.50) + retail_attention_signed (0.20)
    """

    def setUp(self):
        self.cfg = load_config()

    def test_all_signals_present(self):
        # price=+1% → normalize 0.2
        # polarity=+0.5 → already in [-1,+1]
        # engagement=25 with +polarity sign → 25/50 * 1 = 0.5
        # weighted = (0.30*0.2 + 0.50*0.5 + 0.20*0.5) / 1.0 = 0.06+0.25+0.10 = 0.41
        c = composite_score(predicted_pct=1.0, retail_polarity=0.5,
                            retail_engagement=25.0, cfg=self.cfg)
        self.assertAlmostEqual(c, 0.41, places=2)

    def test_partial_signals_renormalize(self):
        # Only polarity present (no price, no engagement)
        c = composite_score(predicted_pct=None, retail_polarity=0.5,
                            retail_engagement=None, cfg=self.cfg)
        # weight 0.50 alone; re-norm → 0.5 (the polarity value itself)
        self.assertAlmostEqual(c, 0.5, places=2)

    def test_no_signals_returns_none(self):
        c = composite_score(None, None, None, self.cfg)
        self.assertIsNone(c)

    def test_attention_requires_polarity_sign(self):
        # Engagement without polarity → attention lane dropped (no direction)
        # Only price contributes
        c = composite_score(predicted_pct=2.0, retail_polarity=None,
                            retail_engagement=30.0, cfg=self.cfg)
        # price_norm = 2/5 = 0.4; weight 0.30 alone → re-norm = 0.4
        self.assertAlmostEqual(c, 0.4, places=2)

    def test_clamp_to_unit_range(self):
        # Extreme price=+10% normalized clamped to +1.0
        # polarity=+1.0 (max), engagement=100 (capped 50/50=1)
        c = composite_score(predicted_pct=10.0, retail_polarity=1.0,
                            retail_engagement=100.0, cfg=self.cfg)
        # (0.30*1.0 + 0.50*1.0 + 0.20*1.0) / 1.0 = 1.0
        self.assertEqual(c, 1.0)


class TestInsufficientDataFallback(unittest.TestCase):
    """Test 5: when ok_count < min_predict_ok_per_sector, predict aggregation returns None."""

    def test_below_min_returns_none(self):
        cfg = load_config()
        # min_predict_ok_per_sector = 3 default
        r = aggregate_predictions([], cfg, skip_predict=True)
        self.assertIsNone(r["median_pct"])


class TestFramingTemplateV2(unittest.TestCase):
    """V3.20.1 — three-lane framing with retail polarity primary."""

    def setUp(self):
        self.cfg = load_config()

    def test_align_signals(self):
        """Price +1.8% AND retail polarity +0.6 → 訊號一致"""
        news = {"score": 2.0, "label": "mod_bull", "count": 5,
                "breadth": "wide", "key_headlines": []}
        retail = {"polarity_score": 0.6, "engagement_score": 20.0,
                  "top_tickers": [{"ticker": "NVDA"}, {"ticker": "AVGO"}],
                  "label": "elevated", "ok": True}
        pred = {"median_pct": 1.8, "bullish_breadth_pct": 80.0,
                "avg_confidence": 0.54, "label": "mod_bull",
                "per_ticker": [], "ok_count": 5}
        f = make_framing_v2("mod_bull", news, retail, pred, self.cfg)
        self.assertIn("1.8", f["zh"])
        self.assertIn("NVDA", f["zh"])
        self.assertIn("訊號一致", f["zh"])
        self.assertIn("align", f["en"].lower())

    def test_diverge_signals(self):
        """Price +1.5% but polarity -0.5 → 訊號分歧"""
        news = {"score": -2.0, "label": "mod_bear", "count": 3,
                "breadth": "wide", "key_headlines": []}
        retail = {"polarity_score": -0.5, "engagement_score": 15.0,
                  "top_tickers": [{"ticker": "MSFT"}],
                  "label": "normal", "ok": True}
        pred = {"median_pct": 1.5, "bullish_breadth_pct": 60.0,
                "avg_confidence": 0.5, "label": "mod_bull",
                "per_ticker": [], "ok_count": 5}
        f = make_framing_v2("neutral_mixed", news, retail, pred, self.cfg)
        self.assertIn("分歧", f["zh"])
        self.assertIn("diverge", f["en"].lower())

    def test_partial_data(self):
        """No retail polarity → 資料部分缺"""
        news = {"score": None, "label": "neutral", "count": 0,
                "breadth": "narrow", "key_headlines": []}
        retail = {"polarity_score": None, "engagement_score": None,
                  "top_tickers": [], "label": "calm", "ok": False}
        pred = {"median_pct": 0.5, "bullish_breadth_pct": 60.0,
                "avg_confidence": 0.5, "label": "neutral",
                "per_ticker": [], "ok_count": 5}
        f = make_framing_v2("neutral_mixed", news, retail, pred, self.cfg)
        self.assertIn("部分缺", f["zh"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

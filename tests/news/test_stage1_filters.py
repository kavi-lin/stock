"""Unit tests for the v3.14.3 Stage 1 quality gates.

Covers:
- _is_blocked() — law-firm solicitation / real-estate PR / personal finance
- _headline_template_key() — cross-ticker template collapse
- effective_credibility() — provider × content marker
- classify_news_type() — priority-ordered rules
- _build_verdict() — full pipeline integration (block + dedup not enforced here;
  see test_pipeline_regression.py for the loop-level assertions)
"""
import sys
from pathlib import Path

# Make the project root importable so `news.scripts.stage1_triage` resolves
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from news.scripts.stage1_triage import (   # noqa: E402
    _is_blocked,
    _headline_template_key,
    effective_credibility,
    classify_news_type,
    classify_content_genre,
    detect_binary_event,
    select_stage2_items,
    _build_verdict,
)


# ── _is_blocked ───────────────────────────────────────────────────────────────

class TestIsBlocked:
    def test_law_firm_named_blocks(self):
        b, r = _is_blocked(
            "Johnson Fistel Investigates Shareholder Losses at NVDA", ""
        )
        assert b is True
        assert r == "law_firm_solicitation"

    def test_law_firm_generic_solicitation_blocks(self):
        b, r = _is_blocked(
            "Investors Encouraged to Reach Out for Loss Recovery on FLGT",
            "Securities class action investigation underway",
        )
        assert b is True
        assert r == "law_firm_solicitation"

    def test_law_firm_schall_law_blocks(self):
        b, r = _is_blocked(
            "Schall Law Firm Announces Investigation of TSLA Shareholders", ""
        )
        assert b is True
        assert r == "law_firm_solicitation"

    def test_law_firm_legitimate_earnings_passes(self):
        b, _ = _is_blocked(
            "NVDA reports Q3 earnings beat, raises guidance", ""
        )
        assert b is False

    def test_law_firm_fed_news_passes(self):
        b, _ = _is_blocked(
            "FOMC raises rate by 25bp; Powell signals further hikes", ""
        )
        assert b is False

    def test_real_estate_condominium_debuts_blocks(self):
        b, r = _is_blocked(
            "THE PARISIAN Condominium Debuts in Astoria", ""
        )
        assert b is True
        assert r == "real_estate_pr"

    def test_real_estate_penthouse_launches_blocks(self):
        b, r = _is_blocked(
            "Luxury Penthouse Launches at One57", ""
        )
        assert b is True
        assert r == "real_estate_pr"

    def test_real_estate_legitimate_real_estate_stock_passes(self):
        # Single-project PR pattern requires both "Condominium" and a launch verb
        b, _ = _is_blocked(
            "Real estate sector rallies on lower rates", ""
        )
        assert b is False

    def test_personal_finance_inheritance_blocks(self):
        b, r = _is_blocked(
            "I inherited a house. Should I sell it now?", ""
        )
        assert b is True
        assert r == "personal_finance_advice"

    def test_personal_finance_dear_penny_blocks(self):
        b, r = _is_blocked(
            "Dear Penny: My husband won't budget. What do I do?", ""
        )
        assert b is True
        assert r == "personal_finance_advice"

    def test_personal_finance_should_i_blocks(self):
        b, r = _is_blocked(
            "Should I sell my Tesla stock before earnings?", ""
        )
        assert b is True
        assert r == "personal_finance_advice"

    def test_personal_finance_legitimate_my_keyword_passes(self):
        # "my" mid-headline (not as opener) should not trigger
        b, _ = _is_blocked(
            "Analyst raises TSLA target citing solid execution by my team", ""
        )
        assert b is False


class TestHkChinaListingChatter:
    """v3.14.9 — block NetEase / Bilibili HK-listed chatter that Futu Push
    surfaces. US committee scope: keep ADR English mentions (NTES / BILI
    tickers); drop Chinese company-name reports and English wires citing the
    company by name (user wants these companies out of the LLM debate queue
    entirely)."""

    def test_chinese_netease_q_results_block(self):
        b, r = _is_blocked("網易Q1淨收入306億元，去年同期爲288億元", "")
        assert b is True
        assert r == "hk_china_listing_chatter"

    def test_chinese_bilibili_index_breakdown_block(self):
        b, r = _is_blocked(
            "三大指數齊跌，科指跌2.15%，科網股走弱，嗶哩嗶哩跌超7%", "",
        )
        assert b is True
        assert r == "hk_china_listing_chatter"

    def test_english_bilibili_name_block(self):
        b, r = _is_blocked("Bilibili reports Q1 revenue beat", "")
        assert b is True
        assert r == "hk_china_listing_chatter"

    def test_english_netease_name_block(self):
        b, r = _is_blocked("NetEase Q1 results from Hong Kong listing", "")
        assert b is True
        assert r == "hk_china_listing_chatter"

    def test_163_com_url_marker_block(self):
        b, r = _is_blocked(
            "Tech news roundup", "source: money.163.com/finance",
        )
        assert b is True
        assert r == "hk_china_listing_chatter"

    # Negative — must NOT block US-only / ADR-only news
    def test_pure_ntes_adr_english_passes(self):
        b, _ = _is_blocked(
            "NTES ADR rises 4% on China iGaming approvals", "",
        )
        assert b is False

    def test_pure_bili_adr_english_passes(self):
        b, _ = _is_blocked(
            "BILI gains on US ADR upgrade by Morgan Stanley", "",
        )
        assert b is False

    def test_unrelated_us_stock_passes(self):
        b, _ = _is_blocked("NVDA reports Q3 earnings beat", "")
        assert b is False


# ── _headline_template_key ────────────────────────────────────────────────────

class TestHeadlineTemplateKey:
    def test_multi_ticker_law_firm_collapses(self):
        keys = [
            _headline_template_key("Johnson Fistel Investigates Losses at NVDA"),
            _headline_template_key("Johnson Fistel Investigates Losses at TSLA"),
            _headline_template_key("Johnson Fistel Investigates Losses at AMD"),
        ]
        assert keys[0] == keys[1] == keys[2]

    def test_different_template_different_key(self):
        a = _headline_template_key("NVDA beats Q3 earnings estimates")
        b = _headline_template_key("Fed raises rate by 25bp")
        assert a != b

    def test_money_normalized(self):
        a = _headline_template_key("AAPL announces $90 billion buyback")
        b = _headline_template_key("AAPL announces $110 billion buyback")
        # Money values normalized to MONEY → same template
        assert a == b

    def test_dates_normalized(self):
        a = _headline_template_key("AAPL Q3 results 2026-05-20")
        b = _headline_template_key("AAPL Q3 results 2026-05-21")
        assert a == b


# ── effective_credibility ─────────────────────────────────────────────────────

class TestEffectiveCredibility:
    def test_high_provider_with_press_release_marker_downgrades_to_medium(self):
        eff = effective_credibility(
            {"source_credibility": "HIGH"},
            "Press Release: TechCorp announces new product launch", "",
        )
        assert eff == "MEDIUM"

    def test_medium_provider_with_press_release_marker_downgrades_to_low(self):
        eff = effective_credibility(
            {"source_credibility": "MEDIUM"},
            "Company announces debut of new flagship", "",
        )
        assert eff == "LOW"

    def test_high_provider_legitimate_news_stays_high(self):
        eff = effective_credibility(
            {"source_credibility": "HIGH"},
            "NVDA Q3 Earnings: Revenue $32.5B, EPS $0.81", "",
        )
        assert eff == "HIGH"

    def test_opinion_marker_forces_low(self):
        eff = effective_credibility(
            {"source_credibility": "HIGH"},
            "Opinion: Why I think Tesla is undervalued", "",
        )
        assert eff == "LOW"

    def test_personal_finance_marker_forces_low(self):
        eff = effective_credibility(
            {"source_credibility": "MEDIUM"},
            "Personal Finance: Best ETFs for retirees", "",
        )
        assert eff == "LOW"


# ── classify_news_type (priority-ordered) ─────────────────────────────────────

class TestClassifyNewsType:
    def test_earnings_wins_over_loss_keyword(self):
        # Old code: "loss" → bear → monetary_policy via fallback.
        # New code: priority pins earnings rule first.
        nt = classify_news_type(
            "Q3 EPS misses estimates, NVDA reports revenue weakness", "",
        )
        assert nt == "earnings"

    def test_law_firm_news_does_not_become_monetary_policy(self):
        # The original bug: FLGT shareholder loss was classified monetary_policy.
        # Item is blocked at _is_blocked, but classifier should also be sane.
        nt = classify_news_type(
            "Fulgent Genetics Shareholders Encouraged to Reach Out for Loss Recovery",
            "Johnson Fistel investigates securities fraud claim",
        )
        assert nt != "monetary_policy"

    def test_fomc_rate_decision_is_monetary_policy(self):
        nt = classify_news_type(
            "FOMC raises rate by 25bp", "Powell signals further hikes",
        )
        assert nt == "monetary_policy"

    def test_cpi_release_is_macro_data(self):
        nt = classify_news_type(
            "May CPI prints at 3.2% YoY, above forecast", "",
        )
        assert nt == "macro_data"

    def test_tariff_news_is_geopolitical(self):
        nt = classify_news_type(
            "Trump announces 25% tariff on imported steel", "",
        )
        assert nt == "geopolitical"

    def test_buyback_is_corporate(self):
        nt = classify_news_type(
            "AAPL announces $90 billion stock buyback program", "",
        )
        assert nt == "corporate"

    def test_8k_filing_is_corporate(self):
        nt = classify_news_type(
            "TSLA files 8-K disclosing executive departure", "",
        )
        assert nt == "corporate"

    def test_unclassifiable_falls_back(self):
        # Generic sentiment — should fall back via legacy keyword tally
        nt = classify_news_type("Markets rally on no news in particular", "")
        assert nt in ("sentiment", "sector_news")


# ── _build_verdict (integration of helpers) ───────────────────────────────────

class TestBuildVerdict:
    def test_verdict_has_effective_credibility_field(self):
        v = _build_verdict(0, {
            "headline": "AAPL Q3 Earnings beat",
            "raw_summary": "Revenue up 12%",
            "source": "FMP",
            "url": "https://example.com/aapl-earnings",
            "source_credibility": "HIGH",
            "published": "2026-05-20T13:00:00Z",
        })
        assert "effective_credibility" in v
        assert v["effective_credibility"] == "HIGH"
        assert v["url"] == "https://example.com/aapl-earnings"
        # headline_zh is null in stage 1 now
        assert v["headline_zh"] is None

    def test_verdict_preserves_source_kind(self):
        v = _build_verdict(0, {
            "headline": "SEC announces a new market structure rule",
            "source": "SEC Press",
            "source_credibility": "HIGH",
            "source_kind": "official_regulator",
        })
        assert v["source_kind"] == "official_regulator"

    def test_verdict_press_release_downgraded(self):
        v = _build_verdict(0, {
            "headline": "Press Release: TinyCo announces product launch",
            "raw_summary": "",
            "source": "PR Newswire",
            "source_credibility": "HIGH",
            "published": "",
        })
        # HIGH provider × press_release marker → MEDIUM
        assert v["effective_credibility"] == "MEDIUM"
        # Should NOT advance via the cred=HIGH × |score|≥0.5 shortcut
        # (still might advance via |score|>=1.5 or binary, but the cred path is closed)
        if abs(v["shallow_score"]) < 1.5 and not v["binary_flag"]:
            assert v["advance_to_stage2"] is False


class TestMaterialitySelection:
    def test_rating_article_does_not_advance_on_sentiment_words(self):
        v = _build_verdict(0, {
            "headline": "Cinemark upgraded to Strong Buy: Here's What You Should Know",
            "raw_summary": "Analysts see strong gains after an earnings beat",
            "source": "Zacks Investment Research",
            "source_kind": "publisher",
            "source_credibility": "HIGH",
        })
        assert v["content_genre"] == "analyst_rating"
        assert v["shallow_score"] > 0
        assert v["materiality_score"] < 4.5
        assert select_stage2_items([v]) == []

    def test_first_party_earnings_event_outranks_listicle(self):
        event = _build_verdict(0, {
            "headline": "Eli Lilly tops quarterly estimates and raises 2026 outlook",
            "raw_summary": "Revenue rose 18% to $12.4 billion",
            "source": "Reuters",
            "source_kind": "wire",
            "source_credibility": "HIGH",
        })
        listicle = _build_verdict(1, {
            "headline": "ChatGPT picks 3 stocks to buy after strong earnings",
            "raw_summary": "Three bargain stocks could surge",
            "source": "Finbold",
            "source_kind": "publisher",
            "source_credibility": "HIGH",
        })
        verdicts = sorted(
            [listicle, event],
            key=lambda x: (x["materiality_score"], abs(x["shallow_score"])),
            reverse=True,
        )
        selected = select_stage2_items(verdicts)
        assert [v["news_id"] for v in selected] == [event["news_id"]]

    def test_source_diversity_caps_one_publisher_at_two(self):
        verdicts = []
        for i, company in enumerate(("Alpha", "Beta", "Gamma")):
            verdicts.append({
                "news_id": f"n{i:04d}",
                "headline": f"{company} reports earnings and raises guidance {10+i}%",
                "source": "Same Publisher",
                "materiality_score": 7.0 - i,
                "shallow_score": 3.0,
                "binary_flag": False,
                "advance_to_stage2": True,
            })
        selected = select_stage2_items(verdicts)
        assert len(selected) == 2
        assert verdicts[2]["advance_reason"] == "source_diversity"

    def test_similar_headlines_collapse_to_one_event(self):
        a = {
            "news_id": "n0001", "headline": "AMD reports Q2 earnings beat and raises guidance",
            "source": "Reuters", "materiality_score": 7.0, "shallow_score": 3.0,
            "binary_flag": False, "advance_to_stage2": True,
        }
        b = {
            "news_id": "n0002", "headline": "AMD Q2 earnings beat estimates, guidance raised",
            "source": "CNBC", "materiality_score": 6.5, "shallow_score": 3.0,
            "binary_flag": False, "advance_to_stage2": True,
        }
        selected = select_stage2_items([a, b])
        assert [v["news_id"] for v in selected] == ["n0001"]
        assert b["advance_reason"] == "duplicate_event"


class TestBinaryDetection:
    def test_generic_merger_story_is_not_automatically_binary(self):
        assert detect_binary_event("Company announces acquisition of a smaller rival") is False

    def test_explicit_merger_vote_is_binary(self):
        assert detect_binary_event("Shareholders set merger approval vote for Friday") is True

    def test_fda_decision_is_binary(self):
        assert detect_binary_event("FDA decision on DrugCo treatment due Friday") is True

    def test_completed_rate_decision_is_not_binary(self):
        assert detect_binary_event("Fed rate decision rocks Wall Street inflation fears") is False

    def test_completed_panel_vote_is_not_binary(self):
        assert detect_binary_event("Biotech soars 132% after key FDA panel vote") is False

    def test_genre_classifier_marks_market_recap(self):
        assert classify_content_genre({}, "TSX Hits Record High; Shopify Surges 17%", "") == "market_recap"

    def test_investment_club_trade_note_is_opinion(self):
        assert classify_content_genre({}, "We're trimming a rallying stock before earnings", "") == "opinion"

    def test_commentary_source_is_not_straight_news(self):
        assert classify_content_genre(
            {"source": "24/7 Wall Street"}, "GLP-1 drove record earnings", "",
        ) == "research_commentary"

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
            "source_credibility": "HIGH",
            "published": "2026-05-20T13:00:00Z",
        })
        assert "effective_credibility" in v
        assert v["effective_credibility"] == "HIGH"
        # headline_zh is null in stage 1 now
        assert v["headline_zh"] is None

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

"""Regression tests for REVIEW_2026-05-24 extractor fixes (v3.18.0).

Covers:
  - news_digest: backtick+bold+equals macro_delta form (2026-05-18 gap)
  - deep_dive: V5.0 Final Visualization Table 5-lane parser (Pattern G)
  - deep_dive: Phase 0 cache cross-file injection for macro_regime (Pattern H)
  - deep_dive: final_action paren modifier preservation (Codex review #6)
  - back-compat: V4.x agent parsing not regressed
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "extractors"))

import deep_dive_extractor as dde  # noqa: E402
from deep_dive_extractor import extract, _find_decision, _find_macro_regime  # noqa: E402
from deep_dive_extractor import _find_hot_zone  # noqa: E402
from news_digest_extractor import _find_macro_delta  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# news_digest macro_delta
# ─────────────────────────────────────────────────────────────────────────────

def test_news_digest_backtick_bold_equals():
    """2026-05-18 form: `session_macro_delta` = **-0.5** (Rec 4 殘留)."""
    text = "Status: `session_macro_delta` = **-0.5** today\n"
    assert _find_macro_delta(text) == -0.5


def test_news_digest_backtick_bold_equals_positive():
    text = "Macro shift: `session_macro_delta` = **+0.25** confirmed.\n"
    assert _find_macro_delta(text) == 0.25


def test_news_digest_parenthetical_backcompat():
    """Existing parenthetical form must not regress."""
    text = "Backdrop session_macro_delta(+0.2) — bullish.\n"
    assert _find_macro_delta(text) == 0.2


def test_news_digest_greek_delta_backcompat():
    text = "**Macro Backdrop Δ**: -0.10 today\n"
    assert _find_macro_delta(text) == -0.10


# ─────────────────────────────────────────────────────────────────────────────
# deep_dive V5.0 lane parsing
# ─────────────────────────────────────────────────────────────────────────────

NOK_REPORT = REPO_ROOT / "reports" / "20260523_NOK.md"
NVDA_REPORT = REPO_ROOT / "reports" / "20260511_NVDA.md"
GOOGL_REPORT = REPO_ROOT / "reports" / "20260520_GOOGL.md"
MU_REPORT = REPO_ROOT / "reports" / "20260516_MU.md"
NBIS_REPORT = REPO_ROOT / "reports" / "20260408_NBIS.md"   # V4.4 JSON-block era


@pytest.mark.skipif(not NOK_REPORT.exists(), reason="fixture report missing")
def test_deep_dive_v50_table_5lane():
    """NOK 2026-05-23: 5 lanes incl Valuation, all with real confidence.
    Manual calc:
      Fundamentals HOLD -1.5 × 0.70 = 1.05
      Sentiment    BUY  +2.2 × 0.65 = 1.43
      News         BUY  +1.5 × 0.65 = 0.975
      Technical    BUY  +3.0 × 0.70 = 2.10  ← max
      Valuation    SELL -3.0 × 0.55 = 1.65
    """
    rec = extract(NOK_REPORT)
    names = [a["agent"] for a in rec["agent_breakdown"]]
    assert "Valuation" in names, f"Valuation lane missing: {names}"
    assert len(rec["agent_breakdown"]) == 5
    # Every lane has real confidence (came from Visualization Table)
    assert all("confidence" in a for a in rec["agent_breakdown"])
    assert rec["tuning_hooks"]["decisive_agent"] == "Technical"
    assert rec["tuning_hooks"]["decisive_agent_method"] == "score_x_confidence"
    assert rec["tuning_hooks"]["agent_confidence_count"] == 5
    assert rec["tuning_hooks"]["min_agent_confidence"] == 0.55
    assert rec["tuning_hooks"]["max_agent_confidence"] == 0.70


@pytest.mark.skipif(not NVDA_REPORT.exists(), reason="fixture report missing")
def test_deep_dive_v50_lane_variants_L_prefix_specialist():
    """NVDA 2026-05-11: L1/L5 prefix + 'Specialist' suffix must both normalize."""
    rec = extract(NVDA_REPORT)
    names = [a["agent"] for a in rec["agent_breakdown"]]
    assert "Fundamentals" in names, f"L1 prefix not stripped: {names}"
    assert "Valuation" in names, f"L5+Specialist not stripped: {names}"


@pytest.mark.skipif(not GOOGL_REPORT.exists(), reason="fixture report missing")
def test_deep_dive_v50_conf_column_alias():
    """GOOGL uses 'Conf' (not 'Confidence') column — regex must still match."""
    rec = extract(GOOGL_REPORT)
    assert len(rec["agent_breakdown"]) == 5
    assert all("confidence" in a for a in rec["agent_breakdown"])


def test_deep_dive_v50_heading_fallback_no_confidence(tmp_path: Path):
    """Heading-only form: lanes parse but confidence column absent.
    decisive_agent falls back to max(|score|), method tag reflects this.
    """
    md = (
        "# 20260524_TEST 報告\n\n"
        "### Fundamentals — HOLD / -1.5\n\n"
        "### Sentiment — BUY / 2.2\n\n"
        "### News — BUY / 1.5\n\n"
        "### Technical — BUY / 3.0\n\n"
        "### Valuation — SELL / -3.0\n\n"
        "| **Final Decision** | HOLD |\n"
    )
    fixture = tmp_path / "20260524_TEST.md"
    fixture.write_text(md, encoding="utf-8")
    rec = extract(fixture)
    assert len(rec["agent_breakdown"]) == 5
    # NO confidence injected from heading-only source (Codex review #2)
    assert all("confidence" not in a for a in rec["agent_breakdown"])
    assert rec["tuning_hooks"]["agent_confidence_count"] == 0
    assert rec["tuning_hooks"]["min_agent_confidence"] is None
    assert rec["tuning_hooks"]["max_agent_confidence"] is None
    # max |score| → Technical or Valuation (both 3.0). seen-set order ⇒ Technical wins
    assert rec["tuning_hooks"]["decisive_agent"] in ("Technical", "Valuation")
    assert rec["tuning_hooks"]["decisive_agent_method"] == "max_abs_score"


@pytest.mark.skipif(not NBIS_REPORT.exists(), reason="fixture report missing")
def test_deep_dive_v44_json_block_backcompat():
    """Pre-V5 V4.4 JSON-block agent format must still parse + carry confidence."""
    rec = extract(NBIS_REPORT)
    assert len(rec["agent_breakdown"]) >= 4
    # All V4.4 agents have confidence baked into JSON block
    assert all("confidence" in a for a in rec["agent_breakdown"])
    assert rec["tuning_hooks"]["min_agent_confidence"] is not None
    assert rec["tuning_hooks"]["max_agent_confidence"] is not None
    # decisive_agent must remain non-null
    assert rec["tuning_hooks"]["decisive_agent"] is not None
    assert rec["tuning_hooks"]["decisive_agent_method"] == "score_x_confidence"


# ─────────────────────────────────────────────────────────────────────────────
# macro_regime Phase 0 cache injection
# ─────────────────────────────────────────────────────────────────────────────

def test_macro_regime_from_phase0_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Phase 0 cache should be authoritative for V5.0 macro_regime."""
    fake_root = tmp_path
    (fake_root / "investment" / "invest_logs").mkdir(parents=True)
    cache_payload = {
        "phase1": {"market_regime": "RISK_ON", "regime_confidence": 0.55},
        "phase3_macro_multiplier": 0.9,
    }
    (fake_root / "investment" / "invest_logs"
                / "2026-05-23_phase0_nok.json").write_text(
        json.dumps(cache_payload), encoding="utf-8"
    )
    monkeypatch.setattr(dde, "ROOT", fake_root)

    out = _find_macro_regime("", decision_date="2026-05-23", ticker="NOK")
    assert out["market_regime"] == "RISK_ON"
    assert out["macro_multiplier"] == 0.9
    assert out["source"] == "phase0_cache"


def test_macro_regime_date_level_cache_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Ticker-specific cache absent → fall back to date-level phase0 cache."""
    fake_root = tmp_path
    (fake_root / "investment" / "invest_logs").mkdir(parents=True)
    cache_payload = {"market_regime": "VOLATILE", "macro_multiplier": 0.7}
    (fake_root / "investment" / "invest_logs"
                / "2026-04-22_phase0.json").write_text(
        json.dumps(cache_payload), encoding="utf-8"
    )
    monkeypatch.setattr(dde, "ROOT", fake_root)

    out = _find_macro_regime("", decision_date="2026-04-22", ticker="AAPL")
    assert out["market_regime"] == "VOLATILE"
    assert out["macro_multiplier"] == 0.7
    assert out["source"] == "phase0_cache"


def test_macro_regime_md_regex_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Both caches missing → MD regex fallback should still work for V4.x reports."""
    monkeypatch.setattr(dde, "ROOT", tmp_path)
    md = '**market_regime** = VOLATILE — risk-off mode\n'
    out = _find_macro_regime(md, decision_date="2026-01-01", ticker="XYZ")
    assert out["market_regime"] == "VOLATILE"
    assert out["source"] == "md_regex"


def test_macro_regime_double_miss(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Cache absent + MD has nothing → graceful None, no crash."""
    monkeypatch.setattr(dde, "ROOT", tmp_path)
    out = _find_macro_regime("totally unrelated text",
                             decision_date="2026-01-01", ticker="XYZ")
    assert out["market_regime"] is None
    assert out["macro_multiplier"] is None
    assert out["source"] is None


# ─────────────────────────────────────────────────────────────────────────────
# final_action paren modifier
# ─────────────────────────────────────────────────────────────────────────────

def test_final_action_paren_modifier_defensive():
    """NOK form: HOLD (DEFENSIVE) → verb='HOLD', modifier='DEFENSIVE'."""
    md = "| **Final Decision** | **HOLD (DEFENSIVE)** |\n"
    verb, modifier = _find_decision(md)
    assert verb == "HOLD"
    assert modifier == "DEFENSIVE"


def test_final_action_paren_modifier_with_trailing_text():
    """Codex flagged 'DEFENSIVE — 不建倉' style — first token only."""
    md = "| **Final Decision** | **HOLD (CANCEL — 不建倉)** |\n"
    verb, modifier = _find_decision(md)
    assert verb == "HOLD"
    assert modifier == "CANCEL"


def test_final_action_no_modifier_backcompat():
    """MU / GOOGL form: bare HOLD → modifier is None."""
    md = "| **最終決議** | HOLD |\n"
    verb, modifier = _find_decision(md)
    assert verb == "HOLD"
    assert modifier is None


def test_final_action_json_form_backcompat():
    md = '{"final_action": "EXECUTE", "score": 2.5}'
    verb, modifier = _find_decision(md)
    assert verb == "EXECUTE"
    assert modifier is None


def test_final_action_modifier_with_keyed_paren():
    """NVDA form: '(action_label: **WAIT** — Burry WARNING + ...)' → WAIT."""
    md = ("| Final Decision | BUY (action_label: **WAIT** — "
          "Burry WARNING + binary earnings 9d + top-tick) |\n")
    verb, modifier = _find_decision(md)
    assert verb == "BUY"
    assert modifier == "WAIT"


def test_final_action_unbolded_row_label():
    """NVDA form: row label '| Final Decision | ...' without bold wrapper."""
    md = "| Final Decision | HOLD (DEFENSIVE) |\n"
    verb, modifier = _find_decision(md)
    assert verb == "HOLD"
    assert modifier == "DEFENSIVE"


# ─────────────────────────────────────────────────────────────────────────────
# Codex round-2 review fixes (3.18.1)
# ─────────────────────────────────────────────────────────────────────────────

def test_final_action_three_row_aggregation_mu_format():
    """MU 20260510 三 row form — Final Decision + Final Action + Action Label。
    早期 extractor 第一個 hit 就 return,丟掉 CANCEL/DEFENSIVE。修復後 modifier 應該
    取 Final Action (CANCEL) 為優先 (比 Action Label 具體)。"""
    md = (
        "| **Final Decision** | HOLD |\n"
        "| **Final Action** | CANCEL |\n"
        "| **Final Score** | 1.194 / 3.0 |\n"
        "| Position Size | 0% |\n"
        "| Action Label | DEFENSIVE |\n"
    )
    verb, modifier = _find_decision(md)
    assert verb == "HOLD"
    assert modifier == "CANCEL", \
        f"expected CANCEL (Final Action wins over Action Label); got {modifier}"


def test_final_action_action_label_only_fallback():
    """無 Final Action row → fallback Action Label。"""
    md = (
        "| **Final Decision** | HOLD |\n"
        "| **Action Label** | DEFENSIVE |\n"
    )
    verb, modifier = _find_decision(md)
    assert verb == "HOLD"
    assert modifier == "DEFENSIVE"


def test_final_action_paren_modifier_beats_other_rows():
    """Paren modifier in Final Decision row 應該 beat Action Label row。"""
    md = (
        "| **Final Decision** | HOLD (WAIT) |\n"
        "| **Action Label** | DEFENSIVE |\n"
    )
    verb, modifier = _find_decision(md)
    assert verb == "HOLD"
    assert modifier == "WAIT", \
        f"paren modifier should win; got {modifier}"


def test_normalize_modifier_rejects_titlecase():
    """GLW form: 'HOLD (Auto REJECT)' — 'Auto' 不是 ALL-CAPS,應該跳到 'REJECT'。"""
    md = "| **Final Decision** | HOLD (Auto REJECT) |\n"
    verb, modifier = _find_decision(md)
    assert verb == "HOLD"
    assert modifier == "REJECT", \
        f"should skip title-case 'Auto', pick 'REJECT'; got {modifier}"


TSM_REPORT = REPO_ROOT / "reports" / "20260510_TSM.md"


@pytest.mark.skipif(not TSM_REPORT.exists(), reason="fixture report missing")
def test_v50_table_score_signal_inverted_column_order():
    """TSM 20260510 form: '| Lane | Score | Signal | Confidence | …' (Score/Signal 對調).
    Before fix: agent_count=0 (column order assumption broken). After: 5 lanes parsed."""
    rec = extract(TSM_REPORT)
    names = [a["agent"] for a in rec["agent_breakdown"]]
    assert "Fundamentals" in names, f"inverted column order should parse; got {names}"
    fund = next(a for a in rec["agent_breakdown"] if a["agent"] == "Fundamentals")
    assert fund["score"] == 3.0
    assert fund["signal"] == "BUY"
    assert fund["confidence"] == 0.88
    assert rec["tuning_hooks"]["decisive_agent"] is not None
    assert rec["tuning_hooks"]["decisive_agent_method"] == "score_x_confidence"


def test_v50_heading_score_first_inline():
    """TSM inline heading: '### Fundamentals — Score 3 | BUY | conf 0.88'."""
    md = (
        "# 20260524_TST report\n\n"
        "### Fundamentals — Score 3 | BUY | conf 0.88\n\n"
        "### Sentiment — Score 1 | HOLD | conf 0.55\n\n"
        "### News — Score 2 | BUY | conf 0.70\n\n"
        "### Technical — Score -1 | SELL | conf 0.60\n\n"
        "### Valuation — Score 0 | HOLD | conf 0.50\n\n"
        "| Final Decision | HOLD |\n"
    )
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False,
        prefix="20260524_TST_",
    ) as f:
        f.write(md)
        path = Path(f.name)
    renamed = path.parent / "20260524_TST.md"
    path.rename(renamed)
    try:
        rec = extract(renamed)
        names = [a["agent"] for a in rec["agent_breakdown"]]
        assert "Fundamentals" in names
        assert len(rec["agent_breakdown"]) == 5
        assert all("confidence" in a for a in rec["agent_breakdown"])
    finally:
        renamed.unlink()


def test_v50_table_score_with_capped_annotation():
    """MU 20260510 form: '| Fundamentals | BUY | 4 (capped +3) | 0.82 | …'
    Trailing '(capped +3)' 之前會 break score cell 導致整 row drop。"""
    md = (
        "## Final Visualization Table\n\n"
        "| Lane | Signal | Score | Conf | 摘要 |\n"
        "|---|---|---|---|---|\n"
        "| Fundamentals | BUY | 4 (capped +3) | 0.82 | rev YoY +196% |\n"
        "| Sentiment | HOLD | 1 | 0.55 | greed |\n"
        "| News | BUY | 3 | 0.72 | analyst pos |\n"
        "| Technical | HOLD | 1 | 0.70 | stretched |\n"
        "| Valuation | SELL | -2 | 0.70 | overvalued |\n"
    )
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False,
        prefix="20260524_TEST_",
    ) as f:
        f.write(md)
        path = Path(f.name)
    # rename to matching FILENAME_RE pattern
    renamed = path.parent / "20260524_TST.md"
    path.rename(renamed)
    try:
        rec = extract(renamed)
        names = [a["agent"] for a in rec["agent_breakdown"]]
        assert "Fundamentals" in names, \
            f"Fundamentals row with '(capped +3)' should parse; got {names}"
        fund = next(a for a in rec["agent_breakdown"] if a["agent"] == "Fundamentals")
        assert fund["score"] == 4.0, f"score should be 4 (annotation ignored); got {fund['score']}"
        assert fund["confidence"] == 0.82
    finally:
        renamed.unlink()


# ─────────────────────────────────────────────────────────────────────────────
# TODO-015 (REVIEW_2026-06-28) — Rec 11 hot_zone_eval shadow derivation
# ─────────────────────────────────────────────────────────────────────────────

def _hz(score, regime, top30, decision="HOLD", text="", position=None,
        agents=None, date="2026-06-22"):
    return _find_hot_zone(
        text, final_score=score, decision=decision, position=position,
        macro_regime=regime, top30=top30, agents=agents or [],
        decision_date=date)


def test_hot_zone_not_qualifying_wrong_regime():
    assert _hz(0.3, "RISK_OFF", True)["hot_zone_eval_derived"] == "not_qualifying"


def test_hot_zone_not_qualifying_not_top30():
    assert _hz(0.3, "RISK_ON", False)["hot_zone_eval_derived"] == "not_qualifying"


def test_hot_zone_not_qualifying_score_in_staged_band():
    # score ≥ default staged 0.8 → already STAGED band, not the hot-zone HOLD band
    assert _hz(0.9, "RISK_ON", True)["hot_zone_eval_derived"] == "not_qualifying"


def test_hot_zone_suppressed_by_valuation_sell():
    agents = [{"agent": "Valuation", "signal": "SELL", "score": -3.0}]
    r = _hz(0.047, "RISK_ON", True, agents=agents)
    assert r["hot_zone_qualifying"] is True
    assert r["hot_zone_eval_derived"] == "suppressed_by_risk_flag"


def test_hot_zone_suppressed_by_burry_warning():
    text = "| **Burry Score** | WARNING | **20.5 / 100** |"
    r = _hz(0.4, "BULL", True, text=text)
    assert r["hot_zone_eval_derived"] == "suppressed_by_risk_flag"


def test_hot_zone_suppressed_by_cap():
    text = '"decision_cap_active": true'
    r = _hz(0.4, "RISK_ON", True, text=text)
    assert r["hot_zone_eval_derived"] == "suppressed_by_cap"


def test_hot_zone_fired():
    r = _hz(0.4, "RISK_ON", True, decision="STAGED_ENTRY", position=0.0015)
    assert r["hot_zone_eval_derived"] == "fired"


def test_hot_zone_qualifying_unexplained_is_bug_signal_post_golive():
    # qualifying, still HOLD, no suppressor, dated after go-live → the alarm
    r = _hz(0.4, "RISK_ON", True, decision="HOLD", date="2026-06-20")
    assert r["hot_zone_eval_derived"] == "qualifying_unexplained"


def test_hot_zone_pre_golive_not_flagged_as_bug():
    # same shape but before Rec 11 existed → expected, not a bug
    r = _hz(0.4, "RISK_ON", True, decision="HOLD", date="2026-05-10")
    assert r["hot_zone_eval_derived"] == "not_evaluated_pre_rec11"


def test_hot_zone_authoritative_md_fields_win():
    text = 'hot_zone_probe: true\nhot_zone_eval: fired'
    r = _hz(0.4, "RISK_ON", True, decision="STAGED_ENTRY", position=0.0015, text=text)
    assert r["hot_zone_probe"] is True
    assert r["hot_zone_eval"] == "fired"

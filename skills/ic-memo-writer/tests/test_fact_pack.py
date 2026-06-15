#!/usr/bin/env python3
"""test_fact_pack.py — Fact pack builder behavior tests.

Uses NVDA fixture (minimal history + minimal earnings cache) to verify:
  - section assemblers produce expected structures
  - degraded_sections logic correctly triggers when cache absent
  - decision_lock hash deterministic across rebuilds
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = ROOT / "skills" / "ic-memo-writer"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build_mod = _load("build_fact_pack")


def _load_trade():
    return json.loads((FIXTURES / "nvda_history_minimal.json").read_text())[0]["trades_this_session"][0]


def _load_earnings():
    return json.loads((FIXTURES / "nvda_earnings_minimal.json").read_text())


def test_compute_decision_lock_hash_stable():
    trade = _load_trade()
    a = build_mod.compute_decision_lock(trade)
    b = build_mod.compute_decision_lock(copy.deepcopy(trade))
    assert a["hash"] == b["hash"]
    assert a["fields"] == build_mod.LOCK_FIELDS


def test_decision_lock_payload_only_lock_fields():
    trade = _load_trade()
    payload = build_mod.compute_decision_lock(trade)["payload"]
    for k in payload:
        assert k in build_mod.LOCK_FIELDS, f"unexpected field in payload: {k}"


def test_decision_lock_changes_when_lane_scores_mutated():
    trade = _load_trade()
    h_before = build_mod.compute_decision_lock(trade)["hash"]
    trade_mut = copy.deepcopy(trade)
    ls = dict(trade_mut.get("lane_scores") or {})
    ls["fundamentals"] = (ls.get("fundamentals") or 0) + 999
    trade_mut["lane_scores"] = ls
    h_after = build_mod.compute_decision_lock(trade_mut)["hash"]
    assert h_before != h_after


def test_section_3_extracts_segments_from_earnings_cache():
    earnings = _load_earnings()
    sec = build_mod.section_3_revenue(earnings)
    assert "_stub" not in sec or not sec.get("_stub")
    assert isinstance(sec.get("product_fy"), list) and len(sec["product_fy"]) > 0
    assert isinstance(sec.get("geographic_fy"), list)


def test_section_3_stub_when_no_earnings_cache():
    sec = build_mod.section_3_revenue(None)
    assert sec.get("_stub") is True


def test_section_5_stub_when_no_earnings_cache():
    sec = build_mod.section_5_financials(None)
    assert sec.get("_stub") is True


def test_section_5_flattens_ttm_and_derives_surprise_pct():
    earnings = {
        "quarterly_pnl": [
            {"revenue": 10, "netIncome": 2},
            {"revenue": 20, "netIncome": 3},
            {"revenue": 30, "netIncome": 4},
            {"revenue": 40, "netIncome": 5},
        ],
        "cash_flow": [
            {"freeCashFlow": 1},
            {"freeCashFlow": 2},
            {"freeCashFlow": 3},
            {"freeCashFlow": 4},
        ],
        "ttm_metrics": {
            "from_ratios_ttm": {
                "grossProfitMarginTTM": 0.58,
                "operatingProfitMarginTTM": 0.49,
            },
            "from_key_metrics_ttm": {"freeCashFlowYieldTTM": 0.02},
        },
        "earnings_surprises": [{"epsActual": 12.2, "epsEstimated": 9.19}],
    }
    sec = build_mod.section_5_financials(earnings)
    assert sec["ttm_metrics"]["gross_margin"] == 0.58
    assert sec["ttm_metrics"]["operating_margin"] == 0.49
    assert sec["ttm_metrics"]["revenue_ttm"] == 100
    assert sec["ttm_metrics"]["net_income_ttm"] == 14
    assert sec["ttm_metrics"]["fcf_ttm"] == 10
    assert sec["earnings_surprises"][0]["surprise_pct"] == 32.75


def test_section_6_stub_when_no_earnings_cache():
    sec = build_mod.section_6_balance_cash(None)
    assert sec.get("_stub") is True


def test_section_6_aliases_cash_and_equity():
    sec = build_mod.section_6_balance_cash({
        "balance_sheet": [{
            "cashAndCashEquivalents": 10,
            "shortTermInvestments": 5,
            "totalEquity": 42,
        }],
        "cash_flow": [],
    })
    row = sec["balance_sheet"][0]
    assert row["cash_and_st_investments"] == 15
    assert row["total_stockholders_equity"] == 42


def test_section_7_stub_when_no_earnings_cache():
    sec = build_mod.section_7_profitability(None)
    assert sec.get("_stub") is True


def test_section_8_uses_phase45_fair_value():
    trade = _load_trade()
    earnings = _load_earnings()
    sec = build_mod.section_8_valuation(trade, earnings)
    fv = sec.get("fair_value_summary") or {}
    assert "weighted_fair_value" in fv
    assert sec.get("pt_news") is not None  # earnings cache has it (may be empty list)


def test_section_10_does_not_emit_dead_consensus_fields():
    sec = build_mod.section_10_scenarios(_load_trade())
    assert "consensus_view" not in sec
    assert "differentiated_view" not in sec


def test_section_4_uses_local_peer_roster_for_mu():
    sec = build_mod.section_4_competitive({"ticker": "MU"}, ["AMAT"], {"status": "stub_no_llm"}, ticker="MU")
    assert sec["peer_source"] == "local_roster"
    assert sec["peers"][0]["ticker"] == "WDC"
    assert any(p["name"] == "SK Hynix" for p in sec["peers"])


def test_section_11_pulls_only_decision_fields():
    trade = _load_trade()
    sec = build_mod.section_11_decision(trade)
    expected_keys = {
        "final_action", "final_decision", "entry_aggressive", "entry_conservative",
        "stop_loss", "take_profit", "position_size_pct", "position_size_method",
        "staged_split", "watch_conditions",
    }
    assert expected_keys.issubset(sec.keys())


def test_round_floats_handles_nested():
    obj = {"a": 1.123456789, "b": [2.987654321, {"c": 3.141592653}]}
    rounded = build_mod._round_floats(obj)
    assert rounded["a"] == 1.1235
    assert rounded["b"][0] == 2.9877
    assert rounded["b"][1]["c"] == 3.1416

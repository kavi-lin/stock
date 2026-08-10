#!/usr/bin/env python3
"""Focused deterministic tests for market_atmosphere.py."""
import importlib.util
from pathlib import Path


PATH = Path(__file__).with_name("market_atmosphere.py")
spec = importlib.util.spec_from_file_location("market_atmosphere", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def rec(key, value):
    return {"key": key, "value": value, "available": value is not None}


def test_threshold_classifier():
    assert mod.classify_indicator(26, red_if=lambda x: x > 25) == "red"
    assert mod.classify_indicator(22, red_if=lambda x: x > 25, yellow_if=lambda x: x >= 20) == "yellow"
    assert mod.classify_indicator(None, red_if=lambda x: x > 25) == "gray"


def test_public_source_parsers():
    finra = (
        "Jun-26 1,502,072 217,441 223,412 "
        "May-26 1,415,557 206,600 217,256"
    )
    rows = mod._parse_finra_margin_debt(finra)
    assert rows[-1] == {"date": "2026-06-30", "value": 1_502_072}

    assert mod._parse_margin_gdp(
        "FINRA Investor Margin Debt Relative to GDP : 4.71% (As of 2026-06-01)"
    ) == 4.71
    assert mod._parse_gurufocus_ratio(
        "Insider Buy/Sell Ratio - USA Overall Market: 0.23 (Jul 2026)"
    ) == 0.23

    ipo = mod._parse_ipo_stats(
        "There have been 99 IPOs priced this year, a -23.8% change from last year. "
        "Total proceeds raised were $145.3 bil this year, a +588.1% change from last year."
    )
    assert ipo == {
        "count": 99,
        "count_change_pct": -23.8,
        "proceeds_bil": 145.3,
        "proceeds_change_pct": 588.1,
    }

    bofa = mod._parse_bofa_bull_bear(
        "CIO INVESTMENT DASHBOARD AS OF JULY 7, 2026. "
        "The BofA Bull & Bear Indicator remained above its sell signal at 9.1."
    )
    assert bofa == {"value": 9.1, "date": "2026-07-07"}


def test_hard_triggers_only_count_explicit_evidence():
    records = [
        rec("vix", 27), rec("margin_debt", 90), rec("hy_spread", 4.8),
        rec("fear_greed", 45), rec("ad_line", None), rec("bofa_bull_bear", 8.5),
        rec("insider_ratio", .12),
    ]
    records[4]["available"] = False
    history = [
        {"vix": 26, "margin_debt": 100, "fear_greed": 80},
        {"vix": 27, "margin_debt": 95, "fear_greed": 82},
        {"vix": 28, "margin_debt": 92, "fear_greed": 78},
    ]
    triggers = mod.evaluate_hard_triggers(records, history)
    by_key = {x["key"]: x for x in triggers}
    assert by_key["vix"]["triggered"] is True
    assert by_key["margin_debt"]["triggered"] is True
    assert by_key["hy_spread"]["triggered"] is True
    assert by_key["fear_greed"]["triggered"] is True
    assert by_key["bofa_bull_bear"]["triggered"] is True
    assert by_key["insider_ratio"]["triggered"] is True
    assert by_key["ad_line"]["triggered"] is False
    assert sum(x["triggered"] for x in triggers) == 6


if __name__ == "__main__":
    test_threshold_classifier()
    test_hard_triggers_only_count_explicit_evidence()
    print("market atmosphere tests: OK")

#!/usr/bin/env python3
"""burry_score.py — scoring bands, weight renormalization, and the V4.111.7 regression.

Zero network: every test patches `burry_score.yf.Ticker`, which is the object the module
actually calls (`compute()` line 1). Patching anything else would let the real yfinance
through — this repo has shipped a suite that mocked `session.get` while the code went
through `fmp_pool`, and it silently hit the live network for weeks.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import burry_score as bs  # noqa: E402


# ── fixtures ────────────────────────────────────────────────────────────────

def _fake_ticker(info=None, closes=None, insider=None, history_raises=False):
    """A yf.Ticker stand-in. `closes` is the 1y Close series; None + history_raises=True
    reproduces a price-fetch outage."""
    tk = MagicMock()
    tk.info = info if info is not None else {}
    if history_raises:
        tk.history.side_effect = RuntimeError("yfinance: connection reset")
    else:
        series = closes if closes is not None else [100.0] * 250
        tk.history.return_value = pd.DataFrame({"Close": series})
    tk.insider_transactions = insider
    return tk


HEALTHY_INFO = {
    "freeCashflow": 5_000_000_000,
    "operatingCashflow": 6_000_000_000,
    "enterpriseValue": 100_000_000_000,
    "ebitda": 8_000_000_000,
    "debtToEquity": 50.0,          # yfinance reports pct → 0.50 ratio
}


# ── component scorers (pure, no mocking needed) ─────────────────────────────

@pytest.mark.parametrize("pct_below,expected", [
    (0.0, 20.0), (4.9, 20.0),          # at the high → harshest band
    (5.0, 20.0), (20.0, 60.0),         # 5→20 ramps 20→60
    (30.0, 75.0), (40.0, 90.0),        # 20→40 ramps 60→90
    (80.0, 90.0),                      # saturates
])
def test_score_52w_bands(pct_below, expected):
    assert bs.score_52w(pct_below) == pytest.approx(expected)


def test_score_52w_none_is_none():
    """A1 regression guard: score_52w must survive None rather than TypeError on `None < 5`."""
    assert bs.score_52w(None) is None


@pytest.mark.parametrize("net,expected", [
    ("BUY", 80), ("NEUTRAL", 50), ("SELL", 20), ("UNKNOWN", None),
])
def test_score_insider(net, expected):
    assert bs.score_insider(net) == expected


def test_score_insider_never_returns_zero():
    """protocol :722 keyed a rule off `component_scores.insider == 0`, which this scorer
    cannot emit — the rule was dead. It now keys off insider_net == "SELL" instead."""
    assert 0 not in [bs.score_insider(n) for n in ("BUY", "NEUTRAL", "SELL")]


@pytest.mark.parametrize("ev_ebit,expected", [
    (5.0, 90.0), (8.0, 90.0), (15.0, 50.0), (30.0, 10.0), (50.0, 10.0),
])
def test_score_ev_ebit_bands(ev_ebit, expected):
    assert bs.score_ev_ebit(ev_ebit) == pytest.approx(expected)


@pytest.mark.parametrize("bad", [None, 0, -5.0])
def test_score_ev_ebit_rejects_nonpositive(bad):
    assert bs.score_ev_ebit(bad) is None


# ── A1 REGRESSION: price fetch failure must not fabricate a veto ────────────

def test_price_fetch_failure_renormalizes_instead_of_scoring_zero():
    """THE bug this batch exists for. Pre-V4.111.7 a failed fetch set pct_below_high=0.0,
    which maps to score_52w's harshest band (20) and entered the weighted average as if it
    were real data — a network blip could manufacture a WARNING or a T4_VETO out of nothing,
    from an agent that holds veto power.

    Seeding the bug back (`pct_below_high = 0.0` in the except branch) turns this red:
    weights_active regains 'pct_below_52w_high' and burry_score drops.
    """
    tk = _fake_ticker(info=HEALTHY_INFO, history_raises=True)
    with patch.object(bs.yf, "Ticker", return_value=tk):
        out = bs.compute("TEST")

    assert out["components"]["pct_below_52w_high"] is None
    assert out["component_scores"]["pct_below_52w_high"] is None
    assert "pct_below_52w_high" not in out["weights_active"]
    assert "52wH n/a" in out["reasoning"]


def test_price_fetch_failure_does_not_change_the_other_components():
    """The surviving components must score identically whether or not price was fetched —
    only the renormalized denominator differs."""
    healthy = _fake_ticker(info=HEALTHY_INFO, closes=[100.0] * 250)
    broken = _fake_ticker(info=HEALTHY_INFO, history_raises=True)

    with patch.object(bs.yf, "Ticker", return_value=healthy):
        ok = bs.compute("TEST")
    with patch.object(bs.yf, "Ticker", return_value=broken):
        degraded = bs.compute("TEST")

    for key in ("fcf_yield", "ev_ebit", "debt_to_equity"):
        assert ok["component_scores"][key] == degraded["component_scores"][key]


def test_flat_price_series_is_not_confused_with_a_failure():
    """A genuinely-at-the-high stock (0% below) still scores 20 and still counts. Only an
    *absent* read renormalizes out — otherwise the fix would erase a real signal."""
    tk = _fake_ticker(info=HEALTHY_INFO, closes=[100.0] * 250)
    with patch.object(bs.yf, "Ticker", return_value=tk):
        out = bs.compute("TEST")

    assert out["components"]["pct_below_52w_high"] == 0.0
    assert out["component_scores"]["pct_below_52w_high"] == 20.0
    assert "pct_below_52w_high" in out["weights_active"]


# ── weight renormalization ──────────────────────────────────────────────────

WEIGHTS = {"fcf_yield": 0.35, "ev_ebit": 0.25, "debt_to_equity": 0.15,
           "pct_below_52w_high": 0.15, "insider": 0.10}


def test_score_is_renormalized_over_active_weights_only():
    """With components missing, the surviving raw weights sum to < 1 (here 0.40), so the
    score must divide by that partial total. Dividing by 1.0 instead would drag every
    incomplete ticker toward 0 — straight into the T4_VETO band."""
    tk = _fake_ticker(info={"enterpriseValue": 100e9, "ebitda": 8e9}, closes=[100.0] * 250)
    with patch.object(bs.yf, "Ticker", return_value=tk):
        out = bs.compute("TEST")

    active = out["weights_active"]
    assert set(active) == {"ev_ebit", "pct_below_52w_high"}
    total_w = sum(WEIGHTS[k] for k in active)
    assert total_w == pytest.approx(0.40)

    expected = sum(out["component_scores"][k] * WEIGHTS[k] for k in active) / total_w
    assert out["burry_score"] == pytest.approx(round(expected, 1))
    # A proper weighted average never escapes the range of its inputs.
    scores = [out["component_scores"][k] for k in active]
    assert min(scores) <= out["burry_score"] <= max(scores)


def test_score_uses_full_weights_when_nothing_is_missing():
    tk = _fake_ticker(
        info={**HEALTHY_INFO, "debtToEquity": 50.0},
        closes=[100.0] * 250,
        insider=pd.DataFrame({"Transaction": ["Purchase"] * 5, "Shares": [100] * 5}),
    )
    with patch.object(bs.yf, "Ticker", return_value=tk):
        out = bs.compute("TEST")

    assert set(out["weights_active"]) == set(WEIGHTS)
    assert sum(WEIGHTS[k] for k in out["weights_active"]) == pytest.approx(1.0)
    expected = sum(out["component_scores"][k] * WEIGHTS[k] for k in WEIGHTS)
    assert out["burry_score"] == pytest.approx(round(expected, 1))


def test_all_components_missing_yields_null_score_not_a_veto():
    """No data must read as UNKNOWN, never as T4_VETO — protocol :793 excludes UNKNOWN
    from T4 precisely so a data outage cannot force a HOLD."""
    tk = _fake_ticker(info={}, history_raises=True)
    with patch.object(bs.yf, "Ticker", return_value=tk):
        out = bs.compute("TEST")

    assert out["burry_score"] is None
    assert out["verdict"] == "UNKNOWN"
    assert out["weights_active"] == []


# ── verdict bands ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("score,expected", [
    (0.0, "T4_VETO"), (19.9, "T4_VETO"),
    (20.0, "WARNING"), (34.9, "WARNING"),
    (35.0, "NEUTRAL"), (59.9, "NEUTRAL"),
    (60.0, "VALUE_BONUS"), (100.0, "VALUE_BONUS"),
])
def test_verdict_bands(score, expected, monkeypatch):
    """Boundaries are exact: 20/35/60 are inclusive-lower. Drive `compute` to a known score
    by making every component report that score."""
    for fn in ("score_fcf_yield", "score_ev_ebit", "score_de", "score_52w"):
        monkeypatch.setattr(bs, fn, lambda *_a, _s=score: _s)
    monkeypatch.setattr(bs, "score_insider", lambda *_a, _s=score: _s)

    tk = _fake_ticker(info=HEALTHY_INFO, closes=[100.0] * 250)
    with patch.object(bs.yf, "Ticker", return_value=tk):
        out = bs.compute("TEST")

    assert out["burry_score"] == pytest.approx(score)
    assert out["verdict"] == expected


# ── output shape (golden keys — downstream reads these by name) ─────────────

def test_output_golden_keys():
    tk = _fake_ticker(info=HEALTHY_INFO, closes=[100.0] * 250)
    with patch.object(bs.yf, "Ticker", return_value=tk):
        out = bs.compute("test")

    assert set(out) == {
        "ticker", "generated_at", "burry_score", "verdict", "components",
        "component_scores", "weights_active", "reasoning",
    }
    assert set(out["components"]) == {
        "fcf_yield_pct", "ev_ebit", "debt_to_equity", "pct_below_52w_high", "insider_net",
    }
    assert set(out["component_scores"]) == {
        "fcf_yield", "ev_ebit", "debt_to_equity", "pct_below_52w_high", "insider",
    }
    assert out["ticker"] == "TEST"


def test_ev_ebit_key_is_really_ebitda():
    """The key is frozen for history.json compatibility even though yfinance exposes no
    EBIT — the reasoning string is where the honest label lives. Renaming the key breaks
    stored sessions; this test is here to make that trade-off explicit rather than a bug."""
    tk = _fake_ticker(info=HEALTHY_INFO, closes=[100.0] * 250)
    with patch.object(bs.yf, "Ticker", return_value=tk):
        out = bs.compute("TEST")

    assert out["components"]["ev_ebit"] == pytest.approx(100e9 / 8e9, abs=0.01)
    assert "EV/EBITDA" in out["reasoning"]


# ── input quirks the script deliberately handles ────────────────────────────

def test_debt_to_equity_is_divided_by_one_hundred():
    """yfinance reports D/E as a percentage (KO=139.79). Forgetting the /100 would push
    every leveraged name into the >2 → 10 band."""
    tk = _fake_ticker(info={**HEALTHY_INFO, "debtToEquity": 139.79}, closes=[100.0] * 250)
    with patch.object(bs.yf, "Ticker", return_value=tk):
        out = bs.compute("TEST")

    assert out["components"]["debt_to_equity"] == pytest.approx(1.40, abs=0.01)


def test_negative_fcf_falls_back_to_operating_cashflow():
    """yfinance's freeCashflow is sometimes wrong (KO reported -1.46B against OpCF +7.4B)."""
    info = {**HEALTHY_INFO, "freeCashflow": -1_460_000_000, "operatingCashflow": 7_400_000_000}
    tk = _fake_ticker(info=info, closes=[100.0] * 250)
    with patch.object(bs.yf, "Ticker", return_value=tk):
        out = bs.compute("TEST")

    expected_yield = (7_400_000_000 * 0.85 / 100_000_000_000) * 100
    assert out["components"]["fcf_yield_pct"] == pytest.approx(expected_yield, abs=0.01)


def test_insider_sniffing_failure_is_fail_safe():
    """The insider read parses free-text yfinance rows and is expected to break; it must
    degrade to UNKNOWN (renormalized out), never to a score."""
    tk = _fake_ticker(info=HEALTHY_INFO, closes=[100.0] * 250)
    type(tk).insider_transactions = property(
        lambda _self: (_ for _ in ()).throw(RuntimeError("schema changed")))

    with patch.object(bs.yf, "Ticker", return_value=tk):
        out = bs.compute("TEST")

    assert out["components"]["insider_net"] == "UNKNOWN"
    assert "insider" not in out["weights_active"]

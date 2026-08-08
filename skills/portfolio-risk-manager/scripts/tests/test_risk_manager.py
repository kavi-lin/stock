#!/usr/bin/env python3
"""risk_manager.py — position loading, correlation bands, and the sector-denominator fix.

Zero network: patches `risk_manager.yf.Ticker` and `risk_manager.yf.download`, the two
entry points the module actually uses. `fetch_history()` calls `yf.download`; everything
else goes through `yf.Ticker`.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import risk_manager as rm  # noqa: E402


# ── fixtures ────────────────────────────────────────────────────────────────

def _price_series(n=150, daily_vol=0.02, seed=0):
    """A deterministic random walk with a target daily vol."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(0, daily_vol, n)
    return list(100 * np.cumprod(1 + rets))


def _ticker(closes=None, sector="Technology", history_raises=False, info_raises=False):
    tk = MagicMock()
    if info_raises:
        type(tk).info = property(lambda _s: (_ for _ in ()).throw(RuntimeError("info down")))
    else:
        tk.info = {"sector": sector}
    if history_raises:
        tk.history.side_effect = RuntimeError("yfinance: connection reset")
    else:
        tk.history.return_value = pd.DataFrame({"Close": closes if closes is not None else _price_series()})
    return tk


def _positions_file(tmp_path, entries):
    p = tmp_path / "positions.json"
    p.write_text(json.dumps(entries))
    return p


# ── load_positions ──────────────────────────────────────────────────────────

def test_load_positions_missing_file_is_empty(tmp_path):
    assert rm.load_positions(tmp_path / "nope.json") == []


def test_load_positions_accepts_list_and_both_wrapper_keys(tmp_path):
    entry = [{"ticker": "AAPL", "shares": 10, "entry_price": 150}]
    for payload in (entry, {"positions": entry}, {"holdings": entry}):
        p = tmp_path / "p.json"
        p.write_text(json.dumps(payload))
        assert [x["ticker"] for x in rm.load_positions(p)] == ["AAPL"]


def test_load_positions_skips_closed_and_exited(tmp_path):
    p = _positions_file(tmp_path, [
        {"ticker": "AAPL", "shares": 10, "status": "open"},
        {"ticker": "MSFT", "shares": 5, "status": "closed"},
        {"ticker": "GOOG", "shares": 5, "status": "exited"},
        {"ticker": "AMZN", "shares": 5},                      # status absent → open
    ])
    assert {x["ticker"] for x in rm.load_positions(p)} == {"AAPL", "AMZN"}


def test_load_positions_tolerates_junk_rows(tmp_path):
    p = _positions_file(tmp_path, [
        "not-a-dict", {"no_ticker": 1}, {"symbol": "nvda", "shares": 3},
    ])
    loaded = rm.load_positions(p)
    assert len(loaded) == 1
    assert loaded[0]["ticker"] == "NVDA"          # `symbol` alias, uppercased


# ── correlation multiplier bands ────────────────────────────────────────────

@pytest.mark.parametrize("corr,expected", [
    (0.0, 1.00), (0.29, 1.00),
    (0.30, 0.85), (0.59, 0.85),
    (0.60, 0.70), (0.79, 0.70),
    (0.80, 0.55), (1.00, 0.55),
])
def test_correlation_multiplier_bands(corr, expected):
    """Lower bound inclusive. With vol-scaling saturated at the 20% ceiling (see P1), this
    multiplier is the only live differentiator in the whole script — the bands matter."""
    assert rm.correlation_multiplier(corr) == expected


@pytest.mark.parametrize("corr", [-0.29, -0.35, -0.65, -0.85, -1.0])
def test_correlation_multiplier_uses_absolute_value(corr):
    """An inverse relationship is still concentration risk: |−0.85| lands where +0.85 does."""
    assert rm.correlation_multiplier(corr) == rm.correlation_multiplier(abs(corr))


def test_correlation_bands_cover_every_input():
    """No gap → never returns None (which would crash the `raw_cap * corr_mult` product)."""
    for hundredth in range(-100, 101):
        assert rm.correlation_multiplier(hundredth / 100.0) is not None


def test_perfectly_correlated_holding_lands_in_the_tightest_band(tmp_path):
    """End-to-end through the real correlation path: identical price series → corr 1.0."""
    p = _positions_file(tmp_path, [{"ticker": "AAPL", "shares": 10}])
    closes = _price_series()
    hist = pd.DataFrame({"NVDA": closes, "AAPL": closes})

    with patch.object(rm.yf, "Ticker", return_value=_ticker(closes)), \
         patch.object(rm, "fetch_history", return_value=hist):
        out = rm.compute("NVDA", p, 0.6)

    assert out["ticker_stats"]["avg_correlation_with_portfolio"] == pytest.approx(1.0)
    assert out["correlation_multiplier"] == 0.55


def test_compute_routes_through_the_band_table(tmp_path):
    """The table is not decorative — compute() must use it."""
    p = _positions_file(tmp_path, [{"ticker": "AAPL", "shares": 10}])
    closes = _price_series()
    hist = pd.DataFrame({"NVDA": closes, "AAPL": list(reversed(closes))})

    with patch.object(rm.yf, "Ticker", return_value=_ticker(closes)), \
         patch.object(rm, "fetch_history", return_value=hist):
        out = rm.compute("NVDA", p, 0.6)

    assert out["correlation_multiplier"] == rm.correlation_multiplier(
        out["ticker_stats"]["avg_correlation_with_portfolio"])


# ── A2b REGRESSION: a failed holding must not shrink the denominator ────────

def test_unpriceable_holding_disarms_the_sector_check(tmp_path):
    """THE bug this batch exists for. Pre-V4.111.7 the loop did `except: continue`, which
    dropped the failed holding from `portfolio_value` while any *successful* same-sector
    holding stayed in `sector_exposure` — the ratio inflated toward 1.0 and could fire the
    ×0.5 penalty on a portfolio nowhere near 30% concentrated.

    Here: 1 tech holding worth 10k prices fine, 3 non-tech holdings worth 90k all fail.
    True tech exposure is 10%. The old code computed 10k/10k = 100% → penalty. The fix
    disarms the check and says so in warnings[].

    Seeding the bug back (`except: continue`, no `failed` list) turns this red.
    """
    p = _positions_file(tmp_path, [
        {"ticker": "AAPL", "shares": 100, "entry_price": 100},   # tech, prices OK
        {"ticker": "XOM", "shares": 300, "entry_price": 100},    # fails
        {"ticker": "JNJ", "shares": 300, "entry_price": 100},    # fails
        {"ticker": "PG", "shares": 300, "entry_price": 100},     # fails
    ])
    candidate_closes = _price_series()

    def fake_ticker(sym):
        if sym == "NVDA":
            return _ticker(candidate_closes, sector="Technology")
        if sym == "AAPL":
            return _ticker([100.0] * 5, sector="Technology")
        return _ticker(history_raises=True, sector="Energy")

    with patch.object(rm.yf, "Ticker", side_effect=fake_ticker), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        out = rm.compute("NVDA", p, 0.6)

    assert out["sector_cap_triggered"] is False
    assert "warnings" in out
    assert "3/4" in out["warnings"][0]
    for t in ("XOM", "JNJ", "PG"):
        assert t in out["warnings"][0]
    # No ×0.5 was applied.
    assert out["final_position_cap_pct"] == pytest.approx(
        out["raw_vol_adjusted_cap_pct"] * out["correlation_multiplier"], abs=0.01)


def test_sector_cap_still_fires_when_every_holding_prices(tmp_path):
    """The fix must not neuter the check — a genuinely concentrated portfolio with clean
    data still gets the ×0.5."""
    p = _positions_file(tmp_path, [
        {"ticker": "AAPL", "shares": 100},      # tech 10k
        {"ticker": "MSFT", "shares": 100},      # tech 10k
        {"ticker": "XOM", "shares": 50},        # energy 5k → tech = 80%
    ])

    def fake_ticker(sym):
        if sym == "NVDA":
            return _ticker(_price_series(), sector="Technology")
        sector = "Energy" if sym == "XOM" else "Technology"
        return _ticker([100.0] * 5, sector=sector)

    with patch.object(rm.yf, "Ticker", side_effect=fake_ticker), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        out = rm.compute("NVDA", p, 0.6)

    assert out["sector_cap_triggered"] is True
    assert "warnings" not in out
    assert out["final_position_cap_pct"] == pytest.approx(
        out["raw_vol_adjusted_cap_pct"] * out["correlation_multiplier"] * 0.5, abs=0.01)


def test_sector_cap_does_not_fire_just_under_the_threshold(tmp_path):
    """30% is the trigger and it is strictly greater-than: exactly 30% must not fire."""
    p = _positions_file(tmp_path, [
        {"ticker": "AAPL", "shares": 30},       # tech 3k
        {"ticker": "XOM", "shares": 70},        # energy 7k → tech = exactly 30%
    ])

    def fake_ticker(sym):
        if sym == "NVDA":
            return _ticker(_price_series(), sector="Technology")
        return _ticker([100.0] * 5, sector=("Energy" if sym == "XOM" else "Technology"))

    with patch.object(rm.yf, "Ticker", side_effect=fake_ticker), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        out = rm.compute("NVDA", p, 0.6)

    assert out["sector_cap_triggered"] is False


def test_warnings_key_absent_on_the_clean_path(tmp_path):
    """`warnings` must appear ONLY when something degraded — otherwise every stored
    session export gains a key and the success-path shape is no longer stable."""
    p = _positions_file(tmp_path, [{"ticker": "AAPL", "shares": 10}])

    def fake_ticker(sym):
        return _ticker(_price_series() if sym == "NVDA" else [100.0] * 5)

    with patch.object(rm.yf, "Ticker", side_effect=fake_ticker), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        out = rm.compute("NVDA", p, 0.6)

    assert "warnings" not in out


def test_unknown_candidate_sector_skips_the_check_silently(tmp_path):
    """No sector for the candidate → nothing to compare against; not a degradation."""
    p = _positions_file(tmp_path, [{"ticker": "AAPL", "shares": 10}])

    def fake_ticker(sym):
        return _ticker(_price_series() if sym == "NVDA" else [100.0] * 5, info_raises=(sym == "NVDA"))

    with patch.object(rm.yf, "Ticker", side_effect=fake_ticker), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        out = rm.compute("NVDA", p, 0.6)

    assert out["inputs"]["candidate_sector"] == "Unknown"
    assert out["sector_cap_triggered"] is False
    assert "warnings" not in out


# ── vol-adjusted cap ────────────────────────────────────────────────────────

def test_raw_cap_is_clipped_at_twenty_percent(tmp_path):
    """The documented P1 limitation, pinned so a future change is deliberate: at the
    default 0.6% budget anything with daily vol ≤ 3% pins to exactly 20.0."""
    p = tmp_path / "none.json"
    with patch.object(rm.yf, "Ticker", return_value=_ticker(_price_series(daily_vol=0.02))), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        out = rm.compute("NVDA", p, 0.6)

    assert out["ticker_stats"]["daily_vol_pct"] < 3.0
    assert out["raw_vol_adjusted_cap_pct"] == 20.0


def test_high_vol_ticker_falls_below_the_ceiling(tmp_path):
    """Above ~3% daily vol the scaling does bite — proof the formula is wired, just
    saturated for normal names."""
    p = tmp_path / "none.json"
    with patch.object(rm.yf, "Ticker", return_value=_ticker(_price_series(daily_vol=0.09, seed=7))), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        out = rm.compute("NVDA", p, 0.6)

    assert out["ticker_stats"]["daily_vol_pct"] > 3.0
    assert out["raw_vol_adjusted_cap_pct"] < 20.0


def test_max_cap_default_is_unchanged_at_twenty(tmp_path):
    """B1 zero-behaviour-change guard: parameterizing the ceiling must not move the
    default. A regression here silently resizes every position the protocol takes."""
    assert rm.DEFAULT_MAX_CAP_PCT == 20.0

    p = tmp_path / "none.json"
    with patch.object(rm.yf, "Ticker", return_value=_ticker(_price_series(daily_vol=0.02))), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        out = rm.compute("NVDA", p, 0.6)          # max_cap omitted → default

    assert out["inputs"]["max_cap_pct"] == 20.0
    assert out["raw_vol_adjusted_cap_pct"] == 20.0


def test_lower_max_cap_binds(tmp_path):
    p = tmp_path / "none.json"
    with patch.object(rm.yf, "Ticker", return_value=_ticker(_price_series(daily_vol=0.02))), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        out = rm.compute("NVDA", p, 0.6, max_cap=10.0)

    assert out["inputs"]["max_cap_pct"] == 10.0
    assert out["raw_vol_adjusted_cap_pct"] == 10.0


def test_raising_max_cap_hands_control_back_to_the_vol_formula(tmp_path):
    """With the ceiling out of the way the cap becomes vol_budget/daily_vol*100 — i.e. the
    scaling that has been dormant. This is the observability the parameter exists for."""
    p = tmp_path / "none.json"
    with patch.object(rm.yf, "Ticker", return_value=_ticker(_price_series(daily_vol=0.02))), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        out = rm.compute("NVDA", p, 0.6, max_cap=1000.0)

    dv = out["ticker_stats"]["daily_vol_pct"]
    assert out["raw_vol_adjusted_cap_pct"] == pytest.approx(round(0.6 / dv * 100, 2), abs=0.02)
    assert out["raw_vol_adjusted_cap_pct"] > 20.0        # ceiling was the only thing binding


def test_max_cap_flag_reaches_compute(tmp_path, capsys):
    """The CLI flag must actually be threaded through — a parameter that main() drops
    would pass every unit test above and still do nothing in production."""
    argv = ["risk_manager.py", "NVDA", "--positions", str(tmp_path / "none.json"),
            "--max-cap", "7.5", "--json-only"]
    with patch.object(sys, "argv", argv), \
         patch.object(rm.yf, "Ticker", return_value=_ticker(_price_series(daily_vol=0.02))), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        rm.main()

    out = json.loads(capsys.readouterr().out)
    assert out["inputs"]["max_cap_pct"] == 7.5
    assert out["raw_vol_adjusted_cap_pct"] == 7.5


def test_vol_budget_scales_the_cap(tmp_path):
    p = tmp_path / "none.json"
    caps = []
    for budget in (0.6, 2.0):
        with patch.object(rm.yf, "Ticker", return_value=_ticker(_price_series(daily_vol=0.09, seed=7))), \
             patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
            caps.append(rm.compute("NVDA", p, budget)["raw_vol_adjusted_cap_pct"])
    assert caps[1] > caps[0]


# ── degradation contract ────────────────────────────────────────────────────

def test_short_history_raises(tmp_path):
    with patch.object(rm.yf, "Ticker", return_value=_ticker([100.0] * 29)):
        with pytest.raises(ValueError, match="insufficient data"):
            rm.compute("NVDA", tmp_path / "none.json", 0.6)


def test_main_emits_error_json_and_exit_1(tmp_path, capsys):
    """A2a: before this, an exception escaped as a traceback with empty stdout and the
    consumer had no reason string. trade_plan_builder.compute_step2 reads this shape."""
    argv = ["risk_manager.py", "NVDA", "--positions", str(tmp_path / "none.json"), "--json-only"]
    with patch.object(sys, "argv", argv), \
         patch.object(rm.yf, "Ticker", side_effect=RuntimeError("yfinance exploded")):
        with pytest.raises(SystemExit) as exc:
            rm.main()

    assert exc.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ticker"] == "NVDA"
    assert "yfinance exploded" in payload["error"]


def test_positions_default_resolves_against_the_repo_root():
    """A2c: the default used to be CWD-relative, so a run from a subdirectory silently
    saw an empty portfolio (no correlation, no sector check) instead of the real one."""
    assert rm.ROOT.name == "ai-investment-committee"
    assert (rm.ROOT / "positions.json").exists()


# ── output shape (golden keys — trade_plan_builder reads these by name) ─────

def test_output_golden_keys(tmp_path):
    p = tmp_path / "none.json"
    with patch.object(rm.yf, "Ticker", return_value=_ticker(_price_series())), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        out = rm.compute("nvda", p, 0.6)

    assert set(out) == {
        "ticker", "generated_at", "inputs", "ticker_stats", "raw_vol_adjusted_cap_pct",
        "correlation_multiplier", "sector_cap_triggered", "final_position_cap_pct",
        "reasoning",
    }
    # `max_cap_pct` added V4.112.0 (B1) — the sole success-path shape change in that wave.
    assert set(out["inputs"]) == {"vol_budget_pct", "max_cap_pct", "positions_loaded",
                                  "candidate_sector"}
    assert set(out["ticker_stats"]) == {
        "daily_vol_pct", "ann_vol_pct", "avg_correlation_with_portfolio"}
    assert out["ticker"] == "NVDA"


def test_portfolio_size_is_gone(tmp_path):
    """A2d: `--portfolio-size` was read and echoed but never used in any calculation.
    Zero programmatic consumers read `inputs.portfolio_size_usd`."""
    p = tmp_path / "none.json"
    with patch.object(rm.yf, "Ticker", return_value=_ticker(_price_series())), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        out = rm.compute("NVDA", p, 0.6)

    assert "portfolio_size_usd" not in out["inputs"]

    argv = ["risk_manager.py", "NVDA", "--portfolio-size", "50000"]
    with patch.object(sys, "argv", argv):
        with pytest.raises(SystemExit):          # argparse rejects the removed flag
            rm.main()


def test_final_cap_is_the_product_of_its_stages(tmp_path):
    """final = raw × corr_mult (× 0.5 when the sector cap fires). trade_plan_builder feeds
    `final_position_cap_pct` straight in as the Step 2 base, so this product is the contract."""
    p = tmp_path / "none.json"
    with patch.object(rm.yf, "Ticker", return_value=_ticker(_price_series())), \
         patch.object(rm, "fetch_history", return_value=pd.DataFrame()):
        out = rm.compute("NVDA", p, 0.6)

    assert out["final_position_cap_pct"] == pytest.approx(
        round(out["raw_vol_adjusted_cap_pct"] * out["correlation_multiplier"], 2), abs=0.01)


def test_candidate_is_excluded_from_its_own_correlation_set(tmp_path):
    """An already-held candidate must not be correlated against itself (corr 1.0 would
    force the 0.55 band every time)."""
    p = _positions_file(tmp_path, [{"ticker": "NVDA", "shares": 10}, {"ticker": "AAPL", "shares": 10}])
    seen = {}

    def fake_fetch(tickers, period):
        seen["tickers"] = list(tickers)
        return pd.DataFrame()

    with patch.object(rm.yf, "Ticker", return_value=_ticker(_price_series())), \
         patch.object(rm, "fetch_history", side_effect=fake_fetch):
        rm.compute("NVDA", p, 0.6)

    assert seen["tickers"].count("NVDA") == 1     # present as candidate, not as a holding

#!/usr/bin/env python3
"""technical_core.fetch_history — the FMP→yfinance price path contract.

This path had ZERO test coverage before V4.113.0 while feeding five consumers
(technical-analyst, momentum-monitor, quant-backtest ×2, kill_trigger_monitor).

Mocks land on `fmp_pool.get` — the real transport the module calls — not on `requests`
or a session object. This repo has shipped a suite that mocked `session.get` while the
code had already moved to `fmp_pool`, and it silently hit the live network for weeks.

The central assertion here is the **adjustment-convention contract**: the FMP endpoint is
the dividend-adjusted one AND the yfinance fallback passes auto_adjust=True. If those two
ever disagree, the series a caller receives depends on whether FMP happened to fail —
which is exactly the bug V4.113.0 removed.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from skills._shared import technical_core as tc  # noqa: E402


# FMP returns newest-first; adjOHLC field names; volume unprefixed.
def _fmp_rows(n=60, start_price=100.0):
    return [
        {
            "symbol": "TEST",
            "date": f"2026-{6 + (i // 30):02d}-{(i % 30) + 1:02d}",
            "adjOpen": start_price + i,
            "adjHigh": start_price + i + 2,
            "adjLow": start_price + i - 2,
            "adjClose": start_price + i + 1,
            "volume": 1_000_000 + i,
        }
        for i in range(n - 1, -1, -1)          # newest-first
    ]


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    """_fetch_fmp_ohlc short-circuits to None without a key."""
    monkeypatch.setenv("FMP_API_KEY", "test-key")


# ── endpoint identity ───────────────────────────────────────────────────────

def test_endpoint_constant_is_the_dividend_adjusted_one():
    """Half of the V4.113.0 contract. The other half is the auto_adjust assertion below.
    `historical-price-eod/full` returns split-adjusted-but-NOT-dividend-adjusted close,
    which made every ex-dividend date look like a real down day."""
    assert tc._FMP_OHLC_ENDPOINT == "historical-price-eod/dividend-adjusted"


def test_fetch_calls_the_constant_not_a_hardcoded_string():
    """Patching the constant must actually redirect the call — this is what lets a shadow
    run both conventions in one process."""
    seen = {}

    def fake_get(endpoint, params, **kw):
        seen["endpoint"] = endpoint
        seen["params"] = params
        return _fmp_rows()

    with patch.object(tc, "_FMP_OHLC_ENDPOINT", "sentinel/endpoint"), \
         patch("scripts._shared.fmp_pool.get", side_effect=fake_get):
        tc._fetch_fmp_ohlc("TEST", "1y")

    assert seen["endpoint"] == "sentinel/endpoint"


def test_from_and_to_are_passed():
    """The endpoint honours from/to (unlike `full`, which ignores `timeseries` and returns
    all history — V4.111.6). Dropping them would pull ~5 years per call."""
    seen = {}
    with patch("scripts._shared.fmp_pool.get",
               side_effect=lambda e, p, **kw: seen.update(p) or _fmp_rows()):
        tc._fetch_fmp_ohlc("TEST", "1y")

    assert seen["symbol"] == "TEST"
    assert "from" in seen and "to" in seen
    assert seen["from"] < seen["to"]


# ── column mapping (the V4.113.0 rename) ────────────────────────────────────

def test_adj_columns_map_to_the_yfinance_schema():
    """adjOpen/adjHigh/adjLow/adjClose → Open/High/Low/Close, volume → Volume.

    Seeding the bug back (renaming from `close` instead of `adjClose`) turns this red:
    the payload has no `close` key, so Close never materializes.
    """
    with patch("scripts._shared.fmp_pool.get", return_value=_fmp_rows()):
        df = tc._fetch_fmp_ohlc("TEST", "1y")

    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert not df.isnull().any().any()
    # adjClose = start + i + 1; oldest row is i=0 → 101.0
    assert df["Close"].iloc[0] == 101.0
    assert df["Open"].iloc[0] == 100.0
    assert df["Volume"].iloc[0] == 1_000_000


def test_rows_are_sorted_oldest_first():
    """FMP ships newest-first; every downstream indicator (MA, RSI, drawdown) assumes
    ascending dates. Reversing this silently inverts every trend signal."""
    with patch("scripts._shared.fmp_pool.get", return_value=_fmp_rows()):
        df = tc._fetch_fmp_ohlc("TEST", "1y")

    assert df.index.is_monotonic_increasing
    assert df["Close"].iloc[0] < df["Close"].iloc[-1]      # synthetic series rises


# ── degradation → fallback ──────────────────────────────────────────────────

@pytest.mark.parametrize("bad", [None, [], {}, "error", [{"no_date": 1}]])
def test_malformed_fmp_payload_returns_none(bad):
    """None is the signal for `fetch_history` to fall back; an exception would crash."""
    with patch("scripts._shared.fmp_pool.get", return_value=bad):
        assert tc._fetch_fmp_ohlc("TEST", "1y") is None


def test_fmp_exception_returns_none():
    with patch("scripts._shared.fmp_pool.get", side_effect=RuntimeError("pool down")):
        assert tc._fetch_fmp_ohlc("TEST", "1y") is None


def test_missing_api_key_returns_none(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY")
    assert tc._fetch_fmp_ohlc("TEST", "1y") is None


# ── THE contract: both paths dividend-adjusted ──────────────────────────────

def test_fallback_passes_auto_adjust_true():
    """The other half of the V4.113.0 contract, and the reason this test exists.

    The FMP side is dividend-adjusted by endpoint choice; yfinance is dividend-adjusted
    only if auto_adjust=True is passed. Drop that kwarg and the two providers disagree
    again — and because the failover is silent, nobody would notice that the numbers now
    depend on FMP's uptime.

    NOTE what this does and does not prove: it asserts the *parameter* is passed, not that
    the two providers' outputs match numerically. Only the shadow (docs/plan_technical_core
    _adjclose.md §5b/§5c) can establish the latter, and it cannot be done offline.
    """
    tk = MagicMock()
    tk.history.return_value = pd.DataFrame({"Close": [1.0, 2.0, 3.0]})

    with patch.object(tc, "_fetch_fmp_ohlc", return_value=None), \
         patch.object(tc.yf, "Ticker", return_value=tk):
        tc.fetch_history("TEST", "1y")

    tk.history.assert_called_once()
    assert tk.history.call_args.kwargs.get("auto_adjust") is True


def test_fmp_success_skips_yfinance_history():
    """When FMP answers, the yfinance handle is still returned (callers read metadata off
    it) but no price call is made — otherwise every fetch would cost two round trips."""
    tk = MagicMock()
    df = pd.DataFrame({"Open": [1.0], "High": [1.0], "Low": [1.0],
                       "Close": [1.0], "Volume": [1]})

    with patch.object(tc, "_fetch_fmp_ohlc", return_value=df), \
         patch.object(tc.yf, "Ticker", return_value=tk):
        hist, handle = tc.fetch_history("TEST", "1y")

    tk.history.assert_not_called()
    assert handle is tk
    assert hist.equals(df)


def test_both_providers_failing_raises():
    tk = MagicMock()
    tk.history.return_value = pd.DataFrame()

    with patch.object(tc, "_fetch_fmp_ohlc", return_value=None), \
         patch.object(tc.yf, "Ticker", return_value=tk):
        with pytest.raises(RuntimeError, match="no history data"):
            tc.fetch_history("TEST", "1y")


def test_empty_fmp_frame_falls_through_to_yfinance():
    """An empty (not None) frame must also trigger the fallback."""
    tk = MagicMock()
    tk.history.return_value = pd.DataFrame({"Close": [1.0, 2.0]})

    with patch.object(tc, "_fetch_fmp_ohlc", return_value=pd.DataFrame()), \
         patch.object(tc.yf, "Ticker", return_value=tk):
        hist, _ = tc.fetch_history("TEST", "1y")

    tk.history.assert_called_once()
    assert not hist.empty

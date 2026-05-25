#!/usr/bin/env python3
"""
narrative-pulse-detector — fetch_inputs SMA200 breakout semantics tests (V1.1).

Synthetic OHLCV — no network. Verifies the V1.1 fix to
fetch_price_volume.sma200_breakout_days_ago:
  - close < sma200 at latest bar → None (was 0, mis-fired Stage 1 brewing gate)
  - close > sma200 streak → integer streak length
  - len(close) < 200 → None
"""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "momentum-monitor" / "scripts"))

import fetch_inputs


def _make_hist(close_values: list[float]) -> pd.DataFrame:
    """Build minimal OHLCV DataFrame from a close series."""
    idx = pd.date_range("2024-01-01", periods=len(close_values), freq="B")
    df = pd.DataFrame(
        {
            "Open": close_values,
            "High": [c * 1.01 for c in close_values],
            "Low": [c * 0.99 for c in close_values],
            "Close": close_values,
            "Volume": [1_000_000] * len(close_values),
        },
        index=idx,
    )
    return df


def _stub_technical_core(hist: pd.DataFrame):
    """Return a stub technical_core module with fetch_history / rsi_14 / ma_structure
    backed by the supplied synthetic hist."""
    mod = types.ModuleType("technical_core")
    mod.fetch_history = lambda ticker, period="1y": (hist, None)
    mod.rsi_14 = lambda close, period=14: pd.Series([50.0] * len(close), index=close.index)
    mod.ma_structure = lambda hist_df: {"trend": "synthetic"}
    return mod


class TestSMA200BreakoutSemantics(unittest.TestCase):
    def _run(self, close_values: list[float]):
        hist = _make_hist(close_values)
        stub = _stub_technical_core(hist)
        with patch.dict(sys.modules, {"technical_core": stub}):
            return fetch_inputs.fetch_price_volume("SYNTH")

    def test_below_sma200_returns_none(self):
        """250 根:前 200 根遞增 (100→200),最後 50 根下跌至 close < sma200。
        當前 close 應低於 SMA200 → sma200_breakout_days_ago is None。
        """
        rising = [100.0 + i * 0.5 for i in range(200)]   # 100 → 199.5
        falling = [199.5 - i * 2.0 for i in range(50)]   # 197.5 → 99.5 (well below sma200)
        result = self._run(rising + falling)
        self.assertTrue(result["ok"])
        self.assertIsNone(
            result["sma200_breakout_days_ago"],
            "close < sma200 at latest bar must yield None (was 0 in v1.0, mis-fired Stage 1)",
        )

    def test_above_sma200_streak_15(self):
        """前 235 根穩定低 (close=100),後 15 根拉升至 close=150 (高於 sma200)。
        最後 15 根連續站上 SMA200 → sma200_breakout_days_ago == 15。
        """
        low = [100.0] * 235
        # SMA200 over last bar = mean(last 200) — needs to be < 150 for above check
        # mean of (35 of low=100) + (15 of high=150) ≈ slightly above 100. 150 > that.
        # Actually for above-checks we look at rolling(200).mean over entire window
        # The last bar's SMA200 = mean of bars 50..249. Bars 50..234 are 100, bars 235..249 are 150.
        # = (185*100 + 15*150)/200 = (18500+2250)/200 = 103.75. close 150 > 103.75 ✓.
        # For bar 234: SMA200 = mean of bars 35..234, all 100 → 100. close=100, NOT above (strict >).
        # So streak = 15.
        high = [150.0] * 15
        result = self._run(low + high)
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["sma200_breakout_days_ago"],
            15,
            f"expected streak=15, got {result['sma200_breakout_days_ago']}",
        )

    def test_insufficient_history_returns_none(self):
        """只有 150 根 close < 200 sample size → None。"""
        close = [100.0 + i * 0.1 for i in range(150)]
        result = self._run(close)
        self.assertTrue(result["ok"])
        self.assertIsNone(result["sma200_breakout_days_ago"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

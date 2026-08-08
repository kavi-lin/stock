"""technical_core.rsi_14 — Wilder RSI, with the V4.113.2 no-losses fix.

`rsi_14` feeds nine consumers (technical-analyst, momentum-monitor, thematic-screener,
market-sentiment-analyzer, theme-detector, short-term-target, quant-backtest ×2,
kill_trigger_monitor), and had no direct test coverage before this file.

The bug this pins: `avg_loss.replace(0, np.nan)` dodges a divide-by-zero, but turned the
no-losses case into NaN — which `rsi_state()` reports as zone "unknown". The mirror case
worked (all losses → RSI 0 → "oversold"), so the asymmetry never showed up: a ticker up
14 straight sessions returned "no reading" for precisely the condition the overbought
zone exists to catch.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from skills._shared.technical_core import rsi_14, rsi_state  # noqa: E402


def _series(vals):
    return pd.Series([float(v) for v in vals])


def _hist(vals):
    return pd.DataFrame({"Close": _series(vals)})


# ── the fix ─────────────────────────────────────────────────────────────────

def test_monotonic_gains_score_one_hundred():
    """No losses in the window → RSI is 100 by definition, not undefined.

    Seeding the bug back (dropping the `.mask(...)`) turns this red with NaN.
    """
    assert rsi_14(_series(range(1, 20)), period=14).iloc[-1] == pytest.approx(100.0)


def test_gains_then_a_flat_day_still_scores_one_hundred():
    """avg_loss stays exactly 0 through flat days too — this is the realistic shape
    (a run of up days broken by an unchanged close), not just the synthetic ramp."""
    assert rsi_14(_series([100 + i for i in range(14)] + [113.0]),
                  period=14).iloc[-1] == pytest.approx(100.0)


def test_maximally_overbought_reports_overbought_not_unknown():
    """The consumer-visible symptom. rsi_state maps NaN → zone 'unknown'."""
    assert rsi_state(_hist(range(1, 20)))["zone"] == "overbought"
    assert rsi_state(_hist(range(1, 20)))["rsi_14"] == pytest.approx(100.0)


# ── the mirror case, which always worked — guards against fixing one side only ──

def test_monotonic_losses_score_zero():
    assert rsi_14(_series(range(20, 1, -1)), period=14).iloc[-1] == pytest.approx(0.0)


def test_maximally_oversold_reports_oversold():
    assert rsi_state(_hist(range(20, 1, -1)))["zone"] == "oversold"


def test_the_two_extremes_are_symmetric():
    """Up-only and down-only must sit at opposite ends of the same scale."""
    up = rsi_14(_series(range(1, 20)), period=14).iloc[-1]
    down = rsi_14(_series(range(20, 1, -1)), period=14).iloc[-1]
    assert up + down == pytest.approx(100.0)


# ── cases that must NOT change ──────────────────────────────────────────────

def test_flat_series_stays_undefined():
    """No movement at all → RSI genuinely has no value. The fix requires a positive
    gain, so this must stay NaN rather than being swept to 100."""
    assert pd.isna(rsi_14(_series([100.0] * 19), period=14).iloc[-1])
    assert rsi_state(_hist([100.0] * 19))["zone"] == "unknown"


def test_warm_up_period_is_still_nan():
    """min_periods=14 — the first 14 rows have no reading. NaN == 0 is False, so the
    mask cannot accidentally fill them."""
    out = rsi_14(_series(range(1, 20)), period=14)
    assert out.iloc[:14].isna().all()
    assert out.iloc[14:].notna().all()


def test_ordinary_oscillation_is_unaffected():
    """The common path must be bit-identical to pre-fix behaviour."""
    prices = [100, 101, 99, 102, 98, 103, 97, 104, 96, 105, 95, 106, 94, 107, 93, 108,
              92, 109, 91]
    assert rsi_14(_series(prices), period=14).iloc[-1] == pytest.approx(47.6038, abs=1e-3)


def test_output_is_aligned_with_the_input_index():
    prices = _series(range(1, 30))
    out = rsi_14(prices, period=14)
    assert len(out) == len(prices)
    assert out.index.equals(prices.index)


@pytest.mark.parametrize("period", [2, 7, 14, 21])
def test_result_stays_inside_zero_to_one_hundred(period):
    """Series is long enough for every period under test — min_periods=period means a
    20-point series produces nothing at all at period=21 (the first version of this test
    asserted on an empty frame)."""
    base = [100, 105, 98, 110, 95, 120, 90, 130, 85, 140,
            80, 150, 75, 160, 70, 170, 65, 180, 60, 190]
    prices = _series(base * 3)                       # 60 points
    out = rsi_14(prices, period=period).dropna()
    assert len(out) == len(prices) - period
    assert out.between(0.0, 100.0).all()

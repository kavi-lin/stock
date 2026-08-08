"""Tests for FMPClient's endpoint chain (market-top-detector), response normalization and shape guards.

**Rewritten V4.113.2.** The previous version was stale in two independent ways and had
been failing 11/55 while silently hitting the live network:

1. **Wrong mock target.** It patched `client.session.get`, but the 2026-08-08 `fmp_pool`
   refactor moved the transport to `fmp_pool.get_url` (`fmp_client.py:103`). `self.session`
   still exists as a leftover, so the patch "succeeded" and did nothing — every test made a
   real HTTP call. Symptom: the suite took 12s. Mocks now land on
   `fmp_client.fmp_pool.get_url`, the function the client actually calls, and return
   **already-parsed payloads** (that is what `get_url` returns — not a Response object).

2. **Asserted a fallback chain that no longer exists.** V4.111.6 deleted the v3 leg after
   measuring it 403 on every endpoint; `_FMP_ENDPOINTS` now holds exactly one URL per key.
   Tests named `..._falls_back_to_v3` asserting `call_count == 2` were pinning deleted
   behaviour. The rejection paths they covered are still real and still worth testing —
   they now assert the honest outcome: **reject → None, exactly one call.**

Payload shapes reflect the current stable endpoints: `quote` returns a flat list;
`historical-price-eod/full` returns a flat list of bars (newest-first) which the client
normalizes to `{"symbol", "historical"}`.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import fmp_client  # noqa: E402
from fmp_client import FMPClient  # noqa: E402


def _make_client():
    client = FMPClient(api_key="test_key")
    client.RATE_LIMIT_DELAY = 0
    return client


def _patch_pool(*payloads):
    """Patch the real transport. Each call pops the next payload; None = failed request
    (which is exactly what get_url returns on network/auth failure)."""
    return patch.object(fmp_client.fmp_pool, "get_url",
                        MagicMock(side_effect=list(payloads)))


BARS = [{"symbol": "^GSPC", "date": "2026-03-20", "close": 5500.0}]
QUOTE = [{"symbol": "^GSPC", "price": 5500.0}]


# =========================================================================
# Transport wiring — the regression that let the old suite hit the network
# =========================================================================

class TestTransportWiring:

    def test_client_calls_fmp_pool_not_its_own_session(self):
        """The guard against this file going stale again: if the transport moves,
        this fails loudly instead of the suite silently making real requests."""
        client = _make_client()
        with _patch_pool(QUOTE) as mocked:
            client.get_quote("^GSPC")
        assert mocked.call_count == 1

    def test_api_key_is_forwarded_to_the_pool(self):
        """The pool injects apikey into params; the client's session header does not
        travel with it, so the key has to be passed explicitly."""
        client = _make_client()
        with _patch_pool(QUOTE) as mocked:
            client.get_quote("^GSPC")
        assert mocked.call_args.kwargs.get("api_key") == "test_key"

    def test_call_counter_tracks_real_requests(self):
        client = _make_client()
        with _patch_pool(QUOTE, BARS):
            client.get_quote("^GSPC")
            client.get_historical_prices("^GSPC", days=80)
        assert client.api_calls_made == 2


# =========================================================================
# Endpoint chain — stable-only since V4.111.6
# =========================================================================

class TestEndpointChain:

    def test_quote_success_makes_exactly_one_call(self):
        client = _make_client()
        with _patch_pool(QUOTE) as mocked:
            assert client.get_quote("^GSPC") == QUOTE
        assert mocked.call_count == 1

    def test_quote_failure_returns_none_without_retrying_a_second_endpoint(self):
        """V4.111.6 removed the v3 leg (403 on every endpoint when measured). A failed
        request is now terminal — no second URL to try."""
        client = _make_client()
        with _patch_pool(None) as mocked:
            assert client.get_quote("^GSPC") is None
        assert mocked.call_count == 1

    def test_historical_failure_returns_none(self):
        client = _make_client()
        with _patch_pool(None) as mocked:
            assert client.get_historical_prices("^GSPC", days=80) is None
        assert mocked.call_count == 1

    def test_stable_quote_url_is_used(self):
        client = _make_client()
        with _patch_pool(QUOTE) as mocked:
            client.get_quote("^GSPC")
        assert mocked.call_args.args[0] == "https://financialmodelingprep.com/stable/quote"

    def test_stable_historical_url_is_used(self):
        client = _make_client()
        with _patch_pool(BARS) as mocked:
            client.get_historical_prices("^GSPC", days=80)
        url = mocked.call_args.args[0]
        assert url == "https://financialmodelingprep.com/stable/historical-price-eod/full"


# =========================================================================
# Response normalization — flat list → {"symbol", "historical"}
# =========================================================================

class TestResponseNormalization:

    def test_flat_bar_list_is_normalized_to_the_consumer_shape(self):
        """The stable endpoint returns a flat list; every downstream consumer still
        expects the old {"symbol", "historical"} dict."""
        client = _make_client()
        with _patch_pool(BARS):
            result = client.get_historical_prices("^GSPC", days=80)

        assert result == {"symbol": "^GSPC", "historical": BARS}

    def test_timeseries_truncates_because_the_endpoint_ignores_it(self):
        """`historical-price-eod/full` ignores the `timeseries` parameter and returns the
        full history regardless (measured V4.111.6: timeseries=2 still returned 287KB).
        The client truncates client-side to keep the old contract."""
        many = [{"symbol": "^GSPC", "date": f"2026-03-{i:02d}", "close": 5500.0 + i}
                for i in range(1, 21)]
        client = _make_client()
        with _patch_pool(many):
            result = client.get_historical_prices("^GSPC", days=5)

        assert len(result["historical"]) == 5
        assert result["historical"] == many[:5]        # newest-first preserved

    def test_historical_stock_list_batch_shape_is_still_handled(self):
        client = _make_client()
        batch = {"historicalStockList": [
            {"symbol": "^GSPC", "historical": [{"date": "2026-03-20", "close": 5500.0}]}]}
        with _patch_pool(batch):
            result = client.get_historical_prices("^GSPC", days=80)

        assert result["symbol"] == "^GSPC"
        assert result["historical"] == [{"date": "2026-03-20", "close": 5500.0}]

    def test_batch_shape_without_a_matching_symbol_returns_none(self):
        client = _make_client()
        batch = {"historicalStockList": [
            {"symbol": "SPY", "historical": [{"date": "2026-03-20", "close": 500.0}]}]}
        with _patch_pool(batch) as mocked:
            assert client.get_historical_prices("^GSPC", days=80) is None
        assert mocked.call_count == 1


# =========================================================================
# Shape guards — truthy but wrong is still wrong
# =========================================================================

class TestShapeValidation:

    def test_quote_rejects_a_dict_payload(self):
        """FMP returns {"Error Message": ...} with HTTP 200. Truthy, and the wrong shape —
        without this guard it would flow downstream as if it were quote data."""
        client = _make_client()
        with _patch_pool({"Error Message": "Invalid API call"}):
            assert client.get_quote("^GSPC") is None

    def test_quote_rejects_an_empty_list(self):
        client = _make_client()
        with _patch_pool([]):
            assert client.get_quote("^GSPC") is None

    def test_historical_rejects_a_scalar_list(self):
        client = _make_client()
        with _patch_pool([1, 2, 3]):
            assert client.get_historical_prices("^GSPC", days=80) is None

    def test_historical_rejects_a_dict_without_historical_key(self):
        client = _make_client()
        with _patch_pool({"symbol": "^GSPC"}):
            assert client.get_historical_prices("^GSPC", days=80) is None


# =========================================================================
# Symbol mismatch — FMP sometimes answers with a different ticker
# =========================================================================

class TestSymbolMismatch:

    def test_single_quote_with_the_wrong_symbol_is_rejected(self):
        client = _make_client()
        with _patch_pool([{"symbol": "SPY", "price": 500.0}]):
            assert client.get_quote("^GSPC") is None

    def test_single_historical_with_the_wrong_symbol_is_rejected(self):
        client = _make_client()
        with _patch_pool([{"symbol": "SPY", "date": "2026-03-20", "close": 500.0}]):
            assert client.get_historical_prices("^GSPC", days=80) is None

    def test_batch_quote_skips_the_symbol_check(self):
        """Multi-symbol requests legitimately return other tickers, so the single-symbol
        guard must not fire — otherwise every batch call would be rejected."""
        client = _make_client()
        batch = [{"symbol": "^GSPC", "price": 5000}, {"symbol": "SPY", "price": 500}]
        with _patch_pool(batch):
            assert client.get_quote("^GSPC,SPY") == batch

    def test_dash_and_dot_ticker_forms_are_treated_as_equal(self):
        """BRK-B vs BRK.B: FMP is inconsistent across endpoints, so the comparison
        normalizes before rejecting."""
        client = _make_client()
        with _patch_pool([{"symbol": "BRK.B", "price": 400.0}]):
            assert client.get_quote("BRK-B") == [{"symbol": "BRK.B", "price": 400.0}]


# =========================================================================
# Caching
# =========================================================================

class TestCaching:

    def test_repeated_quote_hits_the_cache(self):
        client = _make_client()
        with _patch_pool(QUOTE) as mocked:
            client.get_quote("^GSPC")
            client.get_quote("^GSPC")
        assert mocked.call_count == 1

    def test_failed_fetch_is_not_cached(self):
        """Caching a None would make one transient failure permanent for the process."""
        client = _make_client()
        with _patch_pool(None, QUOTE) as mocked:
            assert client.get_quote("^GSPC") is None
            assert client.get_quote("^GSPC") == QUOTE
        assert mocked.call_count == 2

    def test_different_day_counts_are_cached_separately(self):
        client = _make_client()
        with _patch_pool(BARS, BARS) as mocked:
            client.get_historical_prices("^GSPC", days=80)
            client.get_historical_prices("^GSPC", days=200)
        assert mocked.call_count == 2


# =========================================================================
# Constructor
# =========================================================================

class TestConstructor:

    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("FMP_API_KEY", raising=False)
        with pytest.raises(ValueError, match="FMP API key required"):
            FMPClient(api_key=None)

    def test_key_is_read_from_the_environment(self, monkeypatch):
        monkeypatch.setenv("FMP_API_KEY", "env_key")
        assert FMPClient().api_key == "env_key"


# =========================================================================
# VIX term structure — market-top only
# =========================================================================

class TestVixTermStructure:

    def _q(self, sym, price):
        return [{"symbol": sym, "price": price}]

    @pytest.mark.parametrize("vix,vix3m,expected", [
        (10.0, 20.0, "steep_contango"),      # ratio 0.50
        (16.9, 20.0, "steep_contango"),      # 0.845 — just under 0.85
        (17.0, 20.0, "contango"),            # 0.85  — boundary is inclusive-lower
        (18.9, 20.0, "contango"),            # 0.945
        (19.0, 20.0, "flat"),                # 0.95
        (21.0, 20.0, "flat"),                # 1.05  — upper bound inclusive
        (21.1, 20.0, "backwardation"),       # 1.055
        (30.0, 20.0, "backwardation"),
    ])
    def test_classification_bands(self, vix, vix3m, expected):
        """0.85 / 0.95 / 1.05 boundaries. Backwardation is the risk-off signal the
        detector keys off, so the top bound matters."""
        client = _make_client()
        with _patch_pool(self._q("^VIX", vix), self._q("^VIX3M", vix3m)):
            out = client.get_vix_term_structure()

        assert out["classification"] == expected
        assert out["ratio"] == pytest.approx(round(vix / vix3m, 3))
        assert out["vix"] == round(vix, 2)
        assert out["vix3m"] == round(vix3m, 2)

    def test_missing_vix3m_returns_none(self):
        """VIX3M is the leg most often unavailable; without it there is no term
        structure to report — must not fall back to a single-leg guess."""
        client = _make_client()
        with _patch_pool(self._q("^VIX", 20.0), None):
            assert client.get_vix_term_structure() is None

    def test_missing_vix_returns_none(self):
        client = _make_client()
        with _patch_pool(None, self._q("^VIX3M", 20.0)):
            assert client.get_vix_term_structure() is None

    def test_zero_vix3m_returns_none_instead_of_dividing_by_zero(self):
        client = _make_client()
        with _patch_pool(self._q("^VIX", 20.0), self._q("^VIX3M", 0.0)):
            assert client.get_vix_term_structure() is None

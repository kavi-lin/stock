#!/usr/bin/env python3
"""
FMP API Client for Market Top Detector

Provides rate-limited access to Financial Modeling Prep API endpoints
for market top detection analysis.

Features:
- Rate limiting (0.3s between requests)
- Automatic retry on 429 errors
- Session caching for duplicate requests
- Batch quote support for ETF baskets
"""

import os
import sys
import time
from datetime import date, timedelta
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: requests library not found. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

# Central cross-process rate pool (shared 250/min budget). Pacing/429-backoff
# now live there; this client keeps its stable endpoint chain + caching.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from scripts._shared import fmp_pool  # noqa: E402


# --- FMP endpoint fallback: stable (new users) -> v3 (legacy users) ---


def _stable_quote_url(base, symbols_str, params):
    """stable/quote?symbol=^GSPC"""
    params["symbol"] = symbols_str
    return base, params


def _stable_hist_url(base, symbols_str, params):
    """stable/historical-price-eod/full?symbol=^GSPC&from=...（flat list）"""
    params["symbol"] = symbols_str
    ts = params.get("timeseries")
    if ts:
        try:
            days = int(ts)
            params["from"] = (date.today() - timedelta(days=days * 2 + 10)).isoformat()
        except (TypeError, ValueError):
            pass
    return base, params


# stable only（2026-08-08 對齊上游 v3 清理）：v3 全端點 legacy 403、
# stable/historical-price-full 404 — 舊 fallback 鏈兩條都死。historical 改走
# stable/historical-price-eod/full（flat list、newest-first、忽略 timeseries），
# _request_with_fallback 內 normalizer 還原 {"symbol","historical"} 並截斷到 N。
_FMP_ENDPOINTS = {
    "quote": [
        ("https://financialmodelingprep.com/stable/quote", _stable_quote_url),
    ],
    "historical": [
        ("https://financialmodelingprep.com/stable/historical-price-eod/full", _stable_hist_url),
    ],
}


class FMPClient:
    """Client for Financial Modeling Prep API with rate limiting and caching"""

    RATE_LIMIT_DELAY = 0.3  # 300ms between requests

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FMP_API_KEY")
        if not self.api_key:
            raise ValueError(
                "FMP API key required. Set FMP_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.session = requests.Session()
        self.session.headers.update({"apikey": self.api_key})
        self.cache = {}
        self.last_call_time = 0
        self.rate_limit_reached = False
        self.retry_count = 0
        self.max_retries = 1
        self.api_calls_made = 0

    def _rate_limited_get(
        self, url: str, params: Optional[dict] = None, quiet: bool = False
    ) -> Optional[dict]:
        if self.rate_limit_reached:
            return None

        if params is None:
            params = {}

        # Rate pacing + 429 backoff handled by the central pool. apikey is
        # injected by get_url (this client otherwise sets it as a session
        # header, which the pool's per-request transport does not carry).
        # With the pool keeping us under 250/min, a persistent None is a genuine
        # network/auth failure (no longer a quota wall), so we no longer
        # short-circuit the whole run — each call independently retries.
        self.api_calls_made += 1
        data = fmp_pool.get_url(url, params, timeout=30, api_key=self.api_key)
        if data is not None:
            self.retry_count = 0
            return data
        if not quiet:
            print("ERROR: FMP request failed (network/auth)", file=sys.stderr)
        return None

    def _request_with_fallback(self, endpoint_key, symbols_str, extra_params=None):
        """Run the (stable-only) endpoint chain and normalize the response shape.

        Returns parsed JSON in the legacy consumer shape, or None if all fail.
        """
        params = dict(extra_params) if extra_params else {}
        endpoints = _FMP_ENDPOINTS[endpoint_key]
        is_single = "," not in symbols_str

        for i, (base_url, url_builder) in enumerate(endpoints):
            url, final_params = url_builder(base_url, symbols_str, dict(params))
            is_last = i == len(endpoints) - 1
            data = self._rate_limited_get(url, final_params, quiet=not is_last)
            if not data:  # falsy (None, [], {}) — try next endpoint
                continue

            # Shape validation: reject truthy-but-wrong-shape responses
            if endpoint_key == "quote":
                if not isinstance(data, list) or len(data) == 0:
                    continue  # callers expect non-empty list
                # Single-symbol: verify returned symbol matches request
                if is_single and not any(
                    q.get("symbol", "").replace("-", ".") == symbols_str.replace("-", ".")
                    for q in data
                ):
                    continue

            if endpoint_key == "historical":
                # stable/historical-price-eod/full returns a flat list of bars
                # (newest-first) and ignores timeseries — normalize back to the
                # {"symbol", "historical"} shape consumers expect, truncated to N.
                if isinstance(data, list):
                    bars = [b for b in data if isinstance(b, dict)]
                    if not bars:
                        continue
                    if is_single and bars[0].get("symbol"):
                        if bars[0]["symbol"].replace("-", ".") != symbols_str.replace("-", "."):
                            continue
                    n = params.get("timeseries")
                    try:
                        n = int(n) if n else None
                    except (TypeError, ValueError):
                        n = None
                    return {"symbol": symbols_str, "historical": bars[:n] if n else bars}
                if not isinstance(data, dict):
                    continue  # callers expect dict with .get("historical")
                if "historicalStockList" in data:
                    # stable batch format -> v3 single format (exact match only)
                    norm = symbols_str.replace("-", ".")
                    for entry in data["historicalStockList"]:
                        if entry.get("symbol", "").replace("-", ".") == norm:
                            return {
                                "symbol": entry.get("symbol"),
                                "historical": entry.get("historical", []),
                            }
                    # Symbol not found — this endpoint is no good, try next
                    continue
                elif "historical" not in data:
                    continue  # truthy dict but missing expected key
                # Single-symbol: verify returned symbol matches request
                elif is_single and data.get("symbol"):
                    if data["symbol"].replace("-", ".") != symbols_str.replace("-", "."):
                        continue

            return data
        return None

    def get_quote(self, symbols: str) -> Optional[list[dict]]:
        """Fetch real-time quote data for one or more symbols (comma-separated)"""
        cache_key = f"quote_{symbols}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        data = self._request_with_fallback("quote", symbols)
        if data:
            self.cache[cache_key] = data
        return data

    def get_historical_prices(self, symbol: str, days: int = 365) -> Optional[dict]:
        """Fetch historical daily OHLCV data"""
        cache_key = f"prices_{symbol}_{days}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        data = self._request_with_fallback("historical", symbol, {"timeseries": days})
        if data:
            self.cache[cache_key] = data
        return data

    def get_batch_quotes(self, symbols: list[str]) -> dict[str, dict]:
        """Fetch quotes for a list of symbols, batching up to 5 per request"""
        results = {}
        # FMP supports comma-separated symbols in quote endpoint
        batch_size = 5
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]
            batch_str = ",".join(batch)
            quotes = self.get_quote(batch_str)
            if quotes:
                for q in quotes:
                    results[q["symbol"]] = q
        return results

    def get_batch_historical(self, symbols: list[str], days: int = 50) -> dict[str, list[dict]]:
        """Fetch historical prices for multiple symbols"""
        results = {}
        for symbol in symbols:
            data = self.get_historical_prices(symbol, days=days)
            if data and "historical" in data:
                results[symbol] = data["historical"]
        return results

    def calculate_ema(self, prices: list[float], period: int) -> float:
        """Calculate EMA (thin wrapper around math_utils for backward compat)."""
        from calculators.math_utils import calc_ema

        return calc_ema(prices, period)

    def calculate_sma(self, prices: list[float], period: int) -> float:
        """Calculate SMA (thin wrapper around math_utils for backward compat)."""
        from calculators.math_utils import calc_sma

        return calc_sma(prices, period)

    def get_vix_term_structure(self) -> Optional[dict]:
        """
        Auto-detect VIX term structure by comparing VIX to VIX3M.

        Returns:
            Dict with ratio, classification, or None if VIX3M unavailable.
        """
        vix_quotes = self.get_quote("^VIX")
        vix3m_quotes = self.get_quote("^VIX3M")

        if not vix_quotes or not vix3m_quotes:
            return None

        vix_price = vix_quotes[0].get("price", 0)
        vix3m_price = vix3m_quotes[0].get("price", 0)

        if vix3m_price <= 0:
            return None

        ratio = vix_price / vix3m_price

        if ratio < 0.85:
            classification = "steep_contango"
        elif ratio < 0.95:
            classification = "contango"
        elif ratio <= 1.05:
            classification = "flat"
        else:
            classification = "backwardation"

        return {
            "vix": round(vix_price, 2),
            "vix3m": round(vix3m_price, 2),
            "ratio": round(ratio, 3),
            "classification": classification,
        }

    def get_api_stats(self) -> dict:
        return {
            "cache_entries": len(self.cache),
            "api_calls_made": self.api_calls_made,
            "rate_limit_reached": self.rate_limit_reached,
        }

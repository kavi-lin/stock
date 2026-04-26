#!/usr/bin/env python3
"""
Finnhub API Client

Shared infrastructure for AI Investment Committee skills. Provides:
- 60/min throttle (matches free-tier rate limit, with 5% safety margin)
- File-based cache with per-method TTL (mtime-based, mirrors fmp_client pattern)
- Exponential backoff retry on 429/5xx (max 3 attempts)
- 17 endpoint methods covering quotes, OHLCV, fundamentals, calendars,
  insider, recommendations, dividends/splits, IPOs, SEC filings.

Free-tier limitations (HTTP 403 = FinnhubPremiumRequired will be raised):
- /stock/candle          → PREMIUM ONLY. Use yfinance for historical OHLCV.
- /calendar/economic     → PREMIUM ONLY.
- /stock/social-sentiment→ PREMIUM ONLY.
- /news-sentiment        → PREMIUM ONLY.
- /stock/institutional-ownership → PREMIUM ONLY.

Free endpoints: quote, profile2, metric, financials-reported, filings,
  company-news, calendar/earnings, stock/earnings, insider-transactions,
  stock/recommendation, stock/price-target, stock/upgrade-downgrade,
  stock/dividend2, stock/splits, calendar/ipo.
"""
import os
import sys
import json
import time
import hashlib
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests library not found. pip install requests", file=sys.stderr)
    sys.exit(1)


BASE_URL = "https://finnhub.io/api/v1"
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

_TTL = {
    "quote": 5 * 60,
    "candle": 6 * 3600,
    "profile": 7 * 86400,
    "metric": 86400,
    "financials": 86400,
    "filings": 6 * 3600,
    "company_news": 3600,
    "earnings_calendar": 6 * 3600,
    "earnings_surprise": 86400,
    "insider_tx": 86400,
    "insider_sent": 86400,
    "recommendation": 86400,
    "price_target": 86400,
    "upgrade_downgrade": 6 * 3600,
    "dividends": 86400,
    "splits": 7 * 86400,
    "ipo_calendar": 6 * 3600,
}


class FinnhubError(Exception):
    """Base class for Finnhub client errors."""


class FinnhubRateLimit(FinnhubError):
    """Raised after MAX_RETRIES 429 responses."""


class FinnhubPremiumRequired(FinnhubError):
    """Raised when an endpoint requires a paid Finnhub plan."""


class FinnhubClient:
    """Throttled, cached client for Finnhub free-tier endpoints."""

    BASE_URL = BASE_URL
    MIN_INTERVAL = 1.05  # seconds between requests (60/min + 5% safety margin)
    MAX_RETRIES = 3

    def __init__(self, api_key=None, cache_dir=None, use_cache=True):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Finnhub API key required. Set FINNHUB_API_KEY env var "
                "or pass api_key parameter."
            )
        self.session = requests.Session()
        self.session.headers.update({"X-Finnhub-Token": self.api_key})
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self.use_cache = use_cache
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_call = 0.0
        self.api_calls_made = 0
        self.cache_hits = 0

    # ---------------- internal ----------------

    def _cache_path(self, kind, key):
        digest = hashlib.md5(key.encode()).hexdigest()[:12]
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in key)[:60]
        return self.cache_dir / f"{kind}__{safe}__{digest}.json"

    def _cache_read(self, kind, key):
        if not self.use_cache:
            return None
        path = self._cache_path(kind, key)
        if not path.exists():
            return None
        ttl = _TTL.get(kind, 3600)
        if time.time() - path.stat().st_mtime > ttl:
            return None
        try:
            with open(path) as f:
                self.cache_hits += 1
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def _cache_write(self, kind, key, data):
        if not self.use_cache:
            return
        path = self._cache_path(kind, key)
        try:
            with open(path, "w") as f:
                json.dump(data, f)
        except OSError as e:
            print(f"WARN: cache write failed: {e}", file=sys.stderr)

    def _throttle(self):
        elapsed = time.time() - self._last_call
        if elapsed < self.MIN_INTERVAL:
            time.sleep(self.MIN_INTERVAL - elapsed)

    def _request(self, path, params=None, attempt=1):
        self._throttle()
        url = f"{self.BASE_URL}{path}"
        params = dict(params or {})
        try:
            r = self.session.get(url, params=params, timeout=30)
        except requests.exceptions.RequestException as e:
            if attempt < self.MAX_RETRIES:
                time.sleep(2 ** attempt)
                return self._request(path, params, attempt + 1)
            raise FinnhubError(f"Network error: {e}") from e

        self._last_call = time.time()
        self.api_calls_made += 1

        if r.status_code == 200:
            try:
                return r.json()
            except json.JSONDecodeError as e:
                raise FinnhubError(f"Invalid JSON: {e}") from e

        if r.status_code == 429:
            if attempt >= self.MAX_RETRIES:
                raise FinnhubRateLimit(
                    f"Rate limit exceeded after {self.MAX_RETRIES} attempts"
                )
            wait = int(r.headers.get("Retry-After", 60))
            print(
                f"WARN: Finnhub 429 rate-limited; sleeping {wait}s (attempt {attempt})",
                file=sys.stderr,
            )
            time.sleep(wait)
            return self._request(path, params, attempt + 1)

        if r.status_code == 403:
            raise FinnhubPremiumRequired(
                f"Endpoint '{path}' requires a paid Finnhub plan (HTTP 403).\n"
                f"  → Free alternatives: use yfinance for OHLCV candles, FMP for financials.\n"
                f"  → Upgrade: https://finnhub.io/pricing\n"
                f"  Response: {r.text[:120]}"
            )

        if r.status_code == 401:
            raise FinnhubError(f"Auth error 401: bad API key ({r.text[:120]})")

        if 500 <= r.status_code < 600:
            if attempt < self.MAX_RETRIES:
                time.sleep(2 ** attempt)
                return self._request(path, params, attempt + 1)
            raise FinnhubError(f"Server error {r.status_code} after retries")

        raise FinnhubError(f"HTTP {r.status_code}: {r.text[:200]}")

    def _get(self, kind, cache_key, path, params=None):
        cached = self._cache_read(kind, cache_key)
        if cached is not None:
            return cached
        data = self._request(path, params)
        if data is not None:
            self._cache_write(kind, cache_key, data)
        return data

    # ---------------- public endpoints ----------------

    def quote(self, ticker):
        """Real-time quote: c/h/l/o/pc/t fields."""
        return self._get("quote", f"q_{ticker}", "/quote", {"symbol": ticker})

    def candle(self, ticker, days=365, resolution="D"):
        """Historical OHLCV candles.

        NOTE: /stock/candle is PREMIUM ONLY on Finnhub free tier (returns HTTP 403).
        This method will raise FinnhubPremiumRequired if your plan doesn't include it.
        Use yfinance as a free alternative:
            import yfinance as yf
            df = yf.Ticker(ticker).history(period="1y")
        """
        end = int(time.time())
        start = end - days * 86400
        # Cache key bucketed by hour to avoid identical-second cache thrashing
        key = f"c_{ticker}_{resolution}_{days}_{end // 3600}"
        try:
            return self._get(
                "candle",
                key,
                "/stock/candle",
                {"symbol": ticker, "resolution": resolution, "from": start, "to": end},
            )
        except FinnhubPremiumRequired:
            print(
                f"WARN: finnhub candle({ticker}) requires paid plan — "
                f"/stock/candle is premium-only. Use yfinance for free OHLCV data.",
                file=sys.stderr,
            )
            raise

    def profile(self, ticker):
        """Company profile (basic v2, free)."""
        return self._get(
            "profile", f"p_{ticker}", "/stock/profile2", {"symbol": ticker}
        )

    def metric(self, ticker):
        """Key metrics: P/E, ROE, debt/equity, etc."""
        return self._get(
            "metric",
            f"m_{ticker}",
            "/stock/metric",
            {"symbol": ticker, "metric": "all"},
        )

    def financials_reported(self, ticker, freq="quarterly"):
        """Raw SEC-reported financials."""
        return self._get(
            "financials",
            f"f_{ticker}_{freq}",
            "/stock/financials-reported",
            {"symbol": ticker, "freq": freq},
        )

    def filings(self, ticker, form=None):
        """SEC filings list. Optional `form` filter (e.g. '10-K', '8-K')."""
        params = {"symbol": ticker}
        if form:
            params["form"] = form
        key = f"fi_{ticker}_{form or 'all'}"
        return self._get("filings", key, "/stock/filings", params)

    def company_news(self, ticker, start, end):
        """Company news between YYYY-MM-DD dates."""
        return self._get(
            "company_news",
            f"n_{ticker}_{start}_{end}",
            "/company-news",
            {"symbol": ticker, "from": start, "to": end},
        )

    def earnings_calendar(self, start, end, ticker=None):
        """Earnings calendar between YYYY-MM-DD dates. Optional ticker filter."""
        params = {"from": start, "to": end}
        if ticker:
            params["symbol"] = ticker
        key = f"ec_{ticker or 'ALL'}_{start}_{end}"
        return self._get("earnings_calendar", key, "/calendar/earnings", params)

    def earnings_surprise(self, ticker, limit=4):
        """Last N quarterly earnings surprises (actual vs estimate)."""
        return self._get(
            "earnings_surprise",
            f"es_{ticker}_{limit}",
            "/stock/earnings",
            {"symbol": ticker, "limit": limit},
        )

    def insider_transactions(self, ticker, start=None, end=None):
        """SEC Form 4 insider transactions."""
        params = {"symbol": ticker}
        if start:
            params["from"] = start
        if end:
            params["to"] = end
        key = f"it_{ticker}_{start or '_'}_{end or '_'}"
        return self._get("insider_tx", key, "/stock/insider-transactions", params)

    def insider_sentiment(self, ticker, start, end):
        """Aggregated monthly insider sentiment (MSPR score)."""
        return self._get(
            "insider_sent",
            f"is_{ticker}_{start}_{end}",
            "/stock/insider-sentiment",
            {"symbol": ticker, "from": start, "to": end},
        )

    def recommendation(self, ticker):
        """Buy/Hold/Sell recommendation history (monthly)."""
        return self._get(
            "recommendation",
            f"r_{ticker}",
            "/stock/recommendation",
            {"symbol": ticker},
        )

    def price_target(self, ticker):
        """Analyst price target: high / low / median / mean."""
        return self._get(
            "price_target",
            f"pt_{ticker}",
            "/stock/price-target",
            {"symbol": ticker},
        )

    def upgrade_downgrade(self, ticker):
        """Upgrade/downgrade event stream."""
        return self._get(
            "upgrade_downgrade",
            f"ud_{ticker}",
            "/stock/upgrade-downgrade",
            {"symbol": ticker},
        )

    def dividends(self, ticker, start, end):
        """Dividend history between dates."""
        return self._get(
            "dividends",
            f"d_{ticker}_{start}_{end}",
            "/stock/dividend2",
            {"symbol": ticker, "from": start, "to": end},
        )

    def splits(self, ticker, start, end):
        """Stock splits history between dates."""
        return self._get(
            "splits",
            f"sp_{ticker}_{start}_{end}",
            "/stock/splits",
            {"symbol": ticker, "from": start, "to": end},
        )

    def ipo_calendar(self, start, end):
        """IPO calendar between dates."""
        return self._get(
            "ipo_calendar",
            f"ipo_{start}_{end}",
            "/calendar/ipo",
            {"from": start, "to": end},
        )

    def stats(self):
        return {
            "api_calls_made": self.api_calls_made,
            "cache_hits": self.cache_hits,
            "cache_dir": str(self.cache_dir),
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Finnhub client smoke test")
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()
    c = FinnhubClient(use_cache=not args.no_cache)
    print("=== quote ===")
    print(json.dumps(c.quote(args.ticker), indent=2))
    print("=== profile (truncated) ===")
    p = c.profile(args.ticker)
    print(json.dumps(p, indent=2)[:600] if p else "None")
    print("=== stats ===")
    print(c.stats())

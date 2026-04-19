---
name: market-sentiment-analyzer
description: Provides market sentiment composite score (0-100) combining VIX, SPY RSI, Put/Call ratio, and CNN Fear & Greed index. Use when user asks about market sentiment, fear and greed, VIX level, or needs a sentiment-based fallback for investment/sector protocols. Minimal local implementation — replaces web search for F&G.
market: us-equity
scope: market-level
data_sources: [yfinance (VIX/SPY), CNN F&G]
---

# Market Sentiment Analyzer

## Purpose
Replaces "Web search: CNN Fear Greed Index today" used by older protocols.
Returns a composite sentiment score (0-100) from multiple technical sentiment inputs,
so the investment and sector protocols can consume one stable JSON structure.

## Usage
```bash
python3 skills/market-sentiment-analyzer/scripts/sentiment.py                 # uses 15-min cache if fresh
python3 skills/market-sentiment-analyzer/scripts/sentiment.py --json-only
python3 skills/market-sentiment-analyzer/scripts/sentiment.py --no-cache      # force fresh compute
python3 skills/market-sentiment-analyzer/scripts/sentiment.py --max-age 300   # custom TTL seconds
```

No API key required. Uses `yfinance` (VIX, SPY, SPY puts/calls proxy) and
`requests` to fetch CNN Fear & Greed from the public alternative.me endpoint
(crypto F&G as proxy) AND attempts the CNN backend JSON endpoint.

## Caching (default behavior)
Market sentiment is ticker-agnostic — when the investment protocol analyses
several different tickers in one session, every Sentiment subagent would
otherwise call this script fresh. Results are cached to
`skills/market-sentiment-analyzer/cache/sentiment_latest.json` with a default
TTL of **900 seconds (15 min)**. Within that window the full JSON (including
`cache_hit: true` and `cache_age_sec`) is returned immediately — no network
calls, no yfinance download. Override with `--no-cache` for truly-live values.

## Output schema

```json
{
  "generated_at": "ISO8601",
  "composite_score": "float 0-100 (0=extreme fear, 100=extreme greed)",
  "label": "Extreme Fear | Fear | Neutral | Greed | Extreme Greed",
  "vix": {
    "current": "float",
    "percentile_1y": "float 0-100",
    "regime": "LOW | NORMAL | ELEVATED | CRISIS"
  },
  "spy_momentum": {
    "rsi_14": "float",
    "pct_above_ma50": "float",
    "pct_above_ma200": "float"
  },
  "put_call_ratio": "float (null if fetch failed)",
  "fear_greed_index": "float 0-100 (null if fetch failed — fall back to composite)",
  "components_used": ["vix", "spy_rsi", "pct_above_ma", "pcr", "fg"],
  "extreme_sentiment_triggered": "true | false (composite > 80 or < 20)",
  "cache_hit":      "true | false (added by cache layer)",
  "cache_age_sec":  "int — seconds since cache was written (0 on fresh compute)"
}
```

## Composite calculation
Equal-weight average of available normalized components. Each component maps to 0-100:
- VIX: inverted — lower VIX = higher greed. VIX 12 → 90, 20 → 50, 35 → 15
- SPY RSI(14): linear — RSI 30 → 30, 50 → 50, 70 → 70
- SPY vs MA200: 0% → 50, +10% → 80, -10% → 20
- Put/Call ratio: inverted — 1.2 → 20, 0.9 → 50, 0.6 → 85
- CNN F&G: direct passthrough

Missing components are dropped from the average (not imputed).

## Extreme sentiment trigger
`composite_score > 80` → Greed extreme → sector/investment protocols add `extreme_sentiment` risk flag
`composite_score < 20` → Fear extreme → contrarian long opportunities flagged

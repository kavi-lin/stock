---
name: market-sentiment-analyzer
description: Provides market sentiment composite score (0-100) combining VIX, SPY RSI, Put/Call ratio, and CNN Fear & Greed index. Use when user asks about market sentiment, fear and greed, VIX level, or needs a sentiment-based fallback for investment/sector protocols. Minimal local implementation — replaces web search for F&G.
market: us-equity
scope: market-level
data_sources: [yfinance (VIX/SPY), CNN F&G]
---

> **Upstream note**: 專案原生 skill（上游 [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills) 無對應）。2026-08-08（V4.111.6）隨上游 v3 稽核移除 `intraday.py` 的死 v3 historical fallback（legacy 403，永不成功）。

# Market Sentiment Analyzer

## Companion engines (separate outputs, NOT consumed by protocols)
- **`scripts/mood.py`** → `Dashboard/market_mood.json` — signed −100..+100 options-implied 市場氛圍 (VIX/SKEW/PCR/F&G; daily, slow). Page: `mood.html`.
- **`scripts/intraday.py`** → `Dashboard/intraday_mood.json` — signed −100..+100 **盤中評估** (V4.48.0). Deterministic, 0 LLM. Reads FMP intraday 5-min bars + ~60 daily sessions for SPY/QQQ/IWM and flags **破底** (today's low pierces 5d/20d/50d low), **止跌** (intraday reversal off the low / pierced-then-reclaimed), **高開低走** (gap-up fade), **量增價跌** (RVOL surge on a down move), VWAP loss, MA/down-streak/O'Neil distribution days. Negative score = breaking down on volume. **V4.48.1 — live-quote hybrid**: `build()` also fetches FMP `quote` (`_fetch_live_quote`) and overrides spot price / session high-low / day volume / prev close (the last closed 5-min bar lags ~5-6 min; quote is ~2s fresh), so 破底/止跌 detection is second-level. VWAP + intrabar pattern still come from the 5-min bars; each ticker carries `data_source` (`live_quote+5min`/`5min`) + `quote_timestamp`. 1-min bars are unavailable on stable (returns None) → 5-min is the floor for shape signals. **V4.49.0 — MACD/KDJ confluence layer**: pure-python `compute_macd`/`compute_kdj` on BOTH daily (regime) + intraday 5-min (timing, bar-count guarded) → flags **下殺** (`momentum_breakdown`: intraday KDJ death-cross in overbought, or MACD death-cross + below VWAP) and **反轉** (`momentum_reversal`: intraday KDJ golden-cross in oversold, or daily MACD histogram turning up after weakness), plus `macd_daily` regime context. Oscillators are **flags-only — they never move the −100..+100 score** (they whipsaw on intraday); each ticker exposes the raw `momentum` values regardless. Periods/OB-OS thresholds (`MACD_*`/`KDJ_*`/`KDJ_OB`/`KDJ_OS`) are module constants. Tuning knobs (`UNIVERSE`/`WEIGHTS`/thresholds) are module constants. Refreshed by dashboard_server's `intraday_mood_poll_loop` every `INTRADAY_MOOD_INTERVAL_SEC` (default 300s) during US market hours + one post-close snapshot; `daily_update.sh` Step 9.35 writes a baseline. Page: `intraday-mood.html`. APIs: GET `/api/intraday-mood/{data,state}`, POST `/api/intraday-mood/refresh`. FMP-only — Finnhub `/stock/candle` is premium-gated. Test: `python3 skills/market-sentiment-analyzer/scripts/test_intraday.py` (34 asserts; must stay rc=0 after engine edits). **探索層**，不入 investment_protocol 決策。

- **`scripts/intraday_spikes.py`** → `Dashboard/intraday_spikes.json` — **個股急拉/急殺 fast lane** (V4.50.0). Separate lane from the FMP market read: reads **Alpaca 1-minute bars** (free IEX feed) for the `config/spike_watchlist.txt` watchlist and flags 急拉 (spike) / 急殺 (drop) — `detect_spikes()` scans the last 5 min, qualifies on `|1-min| ≥ 1%` OR `|3-min| ≥ 2%`, severity high/med, volume surge (≥3× trailing avg-min) as a **secondary** confirmation only. Price-led because the free IEX feed understates volume (full volume needs paid SIP, `ALPACA_FEED=sip`). **V4.51.0** — each detection adds a **MACD/KDJ/量 confirmation layer** (reuses `intraday.compute_macd`/`compute_kdj` on the same 1-min bars; spike up needs DIF>DEA/golden/hist>0 + K>D, down the inverse, + volume ≥3×): `confirmations` array + `confirmed` (price + ≥2 of MACD/KDJ/量) + `macd`/`kdj` readouts; fetch window 90 min so 1-min MACD is stable. Money-flow / 大單 order-size breakdown is NOT included (needs tick data — Futu OpenAPI or Alpaca SIP). REST-polled (not WebSocket) by dashboard_server's `intraday_spikes_poll_loop` every `INTRADAY_SPIKES_INTERVAL_SEC` (default 60s) during market hours. Graceful no-op without `ALPACA_API_KEY`/`ALPACA_SECRET_KEY`. Page: section on `intraday-mood.html`. API: GET `/api/intraday-spikes/data`. Test: `test_intraday_spikes.py`. **探索層**，不入 investment_protocol 決策。

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

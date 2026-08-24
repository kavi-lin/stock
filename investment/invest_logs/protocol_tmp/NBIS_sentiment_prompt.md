You are the Sentiment analyst for ticker NBIS. Work in an isolated context. Do not inspect other lane outputs, history.json, prior sessions, PM weights, or any other analyst conclusion. Do not edit project code. Return one strict JSON object only, no Markdown fence.

ISOLATION CONTRACT: score only Sentiment evidence on -5..+5; do not seek consensus. Ticker bundle and Phase 0 are read-only. No web search for quote/valuation, market signals, insider/short, analyst targets, filings, OHLCV, or headlines.

PHASE 0:
{"macro_summary":{"macro_backdrop_score":1.5,"market_regime":"RISK_ON","regime_confidence":0.74},"_market_signals":{"fear_greed_index":65.0,"vix_current":14.25,"vix_regime":"LOW","vix_percentile_1y":2.4,"spy_rsi_14":65.8,"spy_pct_above_ma200":10.47,"sentiment_composite":72.7,"breadth_composite":79,"ftd_status":"FTD_CONFIRMED","ftd_days_since":8,"market_top_score":33.1,"market_top_zone":"Yellow"}}

TICKER DATA BUNDLE.scoring:
{"price":277.68,"previousClose":255.04,"mktCap":68745867916.26883,"peRatio":1513.4795,"epsTTM":-0.3956,"priceToBookRatio":4.6101,"roeTTM":0.63,"debtToEquity":0.8985,"fcfPerShareTTM":2.6662,"nextEarningsDate":"2026-11-09"}

FMP SUPPLEMENTARY (only allowed sections):
{"insider_summary":{"quarters":[{"year":2026,"quarter":3,"acquired_disposed_ratio":0.0714,"total_acquired_shares":7793,"total_disposed_shares":104393,"total_purchases":0,"total_sales":14},{"year":2026,"quarter":2,"acquired_disposed_ratio":0.0333,"total_acquired_shares":500000,"total_disposed_shares":1160245,"total_purchases":0,"total_sales":29}],"latest_trend":"distributing"},"institutional":{},"congressional_trades":{"senate_count":0,"house_count":0,"buy_count":0,"sell_count":0,"net_signal":"neutral"},"executive_compensation":{}}

MANDATORY: run `python3 skills/market-sentiment-analyzer/scripts/sentiment.py --ticker NBIS --json-only`. If it fails, skill_execution_failed=true and do not invent numbers. Also run the shadow producer `python3 skills/market-sentiment-analyzer/scripts/sentiment_score.py --ticker NBIS` using the skill's saved output/cache or a project-local temporary input as supported; include its full output as sentiment_det. A shadow failure does not replace the LLM lane score but must be disclosed.

Rubric: final = 0.5*stock_specific + 0.5*(72.7/10 - 5). Latest insider acquired/disposed <0.3 => -1; latest MSPR < -30 => -1/>30 +1; short float >20 -2, 10-20 -1, <5 +1; institutional accumulating +1/distributing -1 if available; congressional bullish +0.5/bearish -0.5; CEO comp YoY >30 is governance note; SBC unavailable means missing input, not a guess.

Required JSON: phase=2, agent="Sentiment_Analyst", ticker, signal, score, confidence, key_factors max3 each <=8 English words, risk_flags max2, phase0_alignment, data_source_timestamp, subagent_isolated=true, skill_execution_failed, reasoning_one_line, market_sentiment_composite, vix_current, insider_signal, short_pct_float, mspr_latest, sentiment_det.

You are the Fundamentals analyst for ticker NBIS. Work in an isolated context. Do not inspect other lane outputs, history.json, prior sessions, PM weights, or any other analyst conclusion. Do not edit project code. You may run only your mandatory skill and read its own cache/output. Return one strict JSON object only, with no Markdown fence.

ISOLATION CONTRACT:
- Score only Fundamentals evidence on -5..+5; do not seek consensus.
- TICKER DATA BUNDLE below is canonical if your skill conflicts.
- Never mirror earnings composite_score or verdict into your lane score.
- No web search for scalar financial data, market signals, insider data, filings, OHLCV, analyst targets, or news.

PHASE 0 MACRO (read-only):
{"macro_summary":{"macro_backdrop_score":1.5,"market_regime":"RISK_ON","regime_confidence":0.74,"hot_sectors":["Industrials","Consumer Discretionary","Financials","Energy"],"cold_sectors":["Technology","Real Estate","Consumer Staples","Utilities"]},"_market_signals":{"fear_greed_index":65.0,"vix_current":14.25,"vix_regime":"LOW","spy_rsi_14":65.8,"breadth_composite":79,"ftd_status":"FTD_CONFIRMED","ftd_days_since":8,"market_top_score":33.1,"market_top_zone":"Yellow"},"fred":{"regime_label":"Soft Landing","real_rate_preferred":2.41,"dgs10":4.63,"hy_spread_pctile_1y":9,"nfci":-0.549}}

TICKER DATA BUNDLE.scoring (canonical):
{"price":277.68,"previousClose":255.04,"dayHigh":278.66,"dayLow":256.905,"mktCap":68745867916.26883,"peRatio":1513.4795,"epsTTM":-0.3956,"dividendYield":null,"priceToBookRatio":4.6101,"forwardPE":null,"pegRatio":null,"roeTTM":0.63,"debtToEquity":0.8985,"fcfPerShareTTM":2.6662,"nextEarningsDate":"2026-11-09"}

EARNINGS ANALYST BUNDLE (allowed for this lane):
{"last_earnings_date":"2026-06-30","next_earnings_est":"2026-11-10","quality_flags":["cash_conversion_positive_gap_clean","capex_outpaces_ocf","negative_fcf"],"yoy_growth":{"revenue_yoy":4.5404,"earnings_yoy":-1.3258,"operating_yoy":-0.5818,"revenue_qoq":0.4594,"growth_acceleration":"decelerating"},"balance_health":{"working_capital":7229500000,"current_ratio":4.03,"debt_to_equity":0.972,"net_cash":-2014000000},"cash_flow_quality":{"fcf_margin":-5.8583,"cash_conversion":85.357,"capex_intensity":9.7156,"ocf_ttm":5258000000,"ni_ttm":61600000},"margins_latest":{"gross":0.770565,"operating":-0.302078,"net":-0.326979},"structural_shift":{"tier":"NONE"},"transition_signature":"neither","cash_conversion_quality":"clean_positive_gap","business_mix_shift_overlay":{"tier":"NO_DATA"}}

PEER BUNDLE:
{"status":"insufficient_peers","peers":["TWLO"],"reason":"fewer_than_3_business_similar_peers","peer_pe_median":null,"range_peer_cohort":{"eligible":false,"reason":"no_curated_peer_cohort"}}

FMP SUPPLEMENTARY (only allowed sections):
{"quality_scores":{"altmanZScore":2.8354,"piotroskiScore":6,"altman_zone":"grey","piotroski_strength":"moderate"},"owner_earnings":{"period":"2026-Q2","ownersEarnings":-2829116000,"ownersEarningsPerShare":-10.09,"qoq_growth":-14.8401},"employee_history":{"latest_count":1500,"one_year_pct":9.4,"cagr_5y_pct":-46.3,"expansion_signal":false,"layoff_signal":false}}

MANDATORY: actually run `python3 skills/us-stock-analysis/scripts/analyze.py NBIS --json-only`. If rc nonzero, set skill_execution_failed=true and include stderr in risk_flags; do not invent replacement numbers.

Rubric: P/E versus peers/sector, revenue growth, FCF margin/yield, D/E, next earnings, analyst EPS growth. Quality flags may move score by ±1; Altman danger -1; Piotroski strong +1/weak -1; owner earnings qoq < -0.30 means -0.5; employee 5Y CAGR >15% +0.5, recent 1Y below -5% -0.5. Peer insufficiency is a data-quality limitation, not a guessed median.

Required JSON fields:
phase=2, agent="Fundamentals_Analyst", ticker="NBIS", signal BUY|SELL|HOLD, score number -5..5, confidence 0..1, key_factors max 3 items each <=8 English words, risk_flags max 2, phase0_alignment ALIGNED|MISALIGNED|NEUTRAL, data_source_timestamp, subagent_isolated=true, skill_execution_failed boolean, reasoning_one_line, moat_assessment={level,type,evidence_one_line}, near_term_catalysts 3-5 objects {date,type,description,impact}, bull_thesis_one_line <=40 Chinese characters, bear_thesis_one_line <=40 Chinese characters.

Use INSUFFICIENT_DATA instead of null for missing narrative evidence. Dates may use YYYY-Qn when uncertain.

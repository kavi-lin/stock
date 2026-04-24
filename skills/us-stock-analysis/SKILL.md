---
name: us-stock-analysis
description: Comprehensive US stock analysis including fundamental analysis (financial metrics, business quality, valuation), technical analysis (indicators, chart patterns, support/resistance), stock comparisons, and investment report generation. Use when user requests analysis of US stock tickers (e.g., "analyze AAPL", "compare TSLA vs NVDA", "give me a report on Microsoft"), evaluation of financial metrics, technical chart analysis, or investment recommendations for American stocks.
market: us-equity
scope: single-ticker
data_sources: [yfinance, FMP API]
---

# US Stock Analysis

Comprehensive single-ticker US equity analysis — fundamentals, technicals, valuation, comparison, investment reports. See `README.md` for tone / formatting pedagogy and example queries.

## Data Sources

Fetch via web search tools (always verify recency — prefer last quarter):

1. **Trading data** — price, volume, 52-week range, YTD
2. **Financial statements** — income / balance sheet / cash flow
3. **Key metrics** — P/E, EPS, revenue, margins, debt
4. **Analyst ratings + price targets**
5. **Recent news / catalysts**
6. **Peer / competitor data** (for comparisons)
7. **Technical data** — MAs, RSI, MACD

Search patterns: `{ticker} {specific metric}`, earnings reports, 10-K / 10-Q for deep financials.

Quality sources (tier order): Yahoo Finance, Google Finance, MarketWatch, Bloomberg, CNBC, Seeking Alpha; company IR pages; SEC EDGAR (filings); TradingView / StockCharts (technicals).

## Analysis Types

Decide which based on user ask:

1. **Basic Info** — quick overview, key metrics
2. **Fundamental** — financials, business quality, valuation
3. **Technical** — charts, indicators, trend
4. **Comprehensive** — all of the above + recommendation

## Workflows

### 1. Basic Stock Information

**Steps**:
1. Fetch current data (price, volume, market cap)
2. Key metrics (P/E, EPS, revenue growth, margins)
3. 52-week range + YTD performance
4. Recent news / major developments
5. Present concise summary

**Output**: company description (1-2 sentences) → current price / trading metrics → valuation metrics table → recent performance → notable news (if any).

### 2. Fundamental Analysis

**Steps**:
1. Gather financials — revenue / earnings / cash flow (3-5y trends), balance sheet (debt, cash, WC), profitability (margins, ROE, ROIC)
2. **Read `references/fundamental-analysis.md`** (framework)
3. **Read `references/financial-metrics.md`** (metric definitions + formulas)
4. Analyze business quality — moats, management, industry position
5. Valuation — P/E, PEG, P/B, EV/EBITDA vs historical avg + peers → fair value range
6. Risks — company-specific, market/macro, red flags from financials
7. **Generate output per `references/report-template.md`**

**Critical checks**:
- Profitability trends (improving / declining margins)
- Cash flow quality (FCF vs earnings)
- Balance sheet strength (debt levels, liquidity)
- Growth sustainability
- Valuation vs peers + historical average

### 3. Technical Analysis

**Steps**:
1. Gather technical data — price action, volume trends, MAs (20/50/200d), indicators (RSI, MACD, Bollinger)
2. **Read `references/technical-analysis.md`** (indicator definitions + patterns)
3. Identify trend — up / down / sideways + strength
4. Find support / resistance — recent H/L, MA levels, round numbers
5. Analyze indicators:
   - RSI: Overbought (>70) / Oversold (<30)
   - MACD: crossovers + divergences
   - Volume: confirmation vs divergence
   - Bollinger: squeeze vs expansion
6. Identify patterns — reversal (H&S, double top/bottom), continuation (flags, triangles)
7. Generate outlook — trend assessment, key levels, risk/reward, short+medium-term view

**Interpretation**:
- Confirm signals with multiple indicators
- Volume for validation
- Note divergences between price and indicators
- Always identify stop-loss levels

### 4. Comprehensive Investment Report

**Steps**:
1. Data gathering (as Basic)
2. Execute Fundamental workflow
3. Execute Technical workflow
4. **Read `references/report-template.md`** (full structure)
5. Synthesize — integrate F+T, develop bull + bear cases, risk/reward
6. Recommend — Buy / Hold / Sell + target + timeframe + conviction + entry strategy
7. Format per template

**Report sections required**: Executive summary (w/ recommendation) → Company overview → Investment thesis (bull + bear) → Fundamental analysis → Technical analysis → Valuation → Risk assessment → Catalysts + timeline → Conclusion.

## Stock Comparison

**Triggers**: "compare AAPL vs MSFT", "TSLA vs NVDA which is better"

**Steps**:
1. Data gathering for each ticker (same timeframes)
2. **Read `references/fundamental-analysis.md`** + `references/financial-metrics.md`
3. Side-by-side comparison tables: business models, financial metrics, valuation, growth rates, profitability, balance sheet
4. Identify relative strengths (quantified advantages per company)
5. Technical comparison — relative strength, momentum, better technical setup
6. Recommend — which is more attractive + portfolio allocation + risk-adjusted return

**Output**: follow "Comparison Report Structure" in `references/report-template.md`.

## Reference Files

Load conditionally based on workflow:

| File | When | Contains |
|---|---|---|
| `references/technical-analysis.md` | Technical workflow | Indicator definitions, chart patterns, S/R concepts |
| `references/fundamental-analysis.md` | Fundamental / Comparison | Business quality, financial health, valuation frameworks, red flags |
| `references/financial-metrics.md` | Any metric calc needed | All ratios + formulas (profitability, valuation, growth, liquidity, leverage, efficiency, cash flow) |
| `references/report-template.md` | Comprehensive / Comparison report | Full report structure, section templates, comparison format |

## Output Format (Core Rules)

- Tables for financial data + comparisons (easy to scan)
- Quantify whenever possible (%, $B, $M)
- Present bull + bear perspectives
- Be clear about assumptions + uncertainties
- Objective, balanced tone — no hyperbole
- Always include data sources + dates

(Extended style guidance + tone examples in `README.md`.)

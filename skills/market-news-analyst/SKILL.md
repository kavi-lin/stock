---
name: market-news-analyst
description: This skill should be used when analyzing recent market-moving news events and their impact on equity markets and commodities. Use this skill when the user requests analysis of major financial news from the past 10 days, wants to understand market reactions to monetary policy decisions (FOMC, ECB, BOJ), needs assessment of geopolitical events' impact on commodities, or requires comprehensive review of earnings announcements from mega-cap stocks. The skill automatically collects news using WebSearch/WebFetch tools and produces impact-ranked analysis reports. All analysis thinking and output are conducted in English.
market: us-equity
scope: news-scan
data_sources: [WebSearch, WebFetch]
---

# Market News Analyst

Analyse 10-day market-moving news → impact-ranked English Markdown report. All thinking + output in English. See `README.md` for principles, pitfalls, and pedagogy.

## Prerequisites

WebSearch + WebFetch available. No API keys.

## When to Use

User asks for: recent market news analysis, FOMC / ECB / BOJ decision impact, mega-cap earnings review, geopolitical → commodity reactions, or "past 10 days of market-moving events".

## Analysis Workflow (6 Steps)

### Step 1: News Collection (WebSearch + WebFetch)

Execute parallel searches across these categories:

| Category | Query examples |
|---|---|
| Monetary policy | "FOMC meeting past 10 days", "Federal Reserve interest rate", "ECB policy decision", "Bank of Japan" |
| Inflation / econ data | "CPI inflation [month]", "NFP jobs report", "GDP data", "PPI producer prices" |
| Mega-cap earnings | "Apple earnings [quarter]", "MSFT earnings", "NVDA earnings", "AMZN", "TSLA", "META", "GOOGL" |
| Geopolitics | "Middle East conflict oil", "Ukraine war", "US China tensions", "tariffs" |
| Commodities | "oil prices past week", "gold prices", "OPEC meeting", "natural gas", "copper" |
| Corporate | "major M&A", "bank earnings", "bankruptcy", "credit rating downgrade" |

**Source priority** (highest → lowest):
1. Official: FederalReserve.gov, SEC.gov (EDGAR), Treasury.gov, BLS.gov
2. Tier 1 press: Bloomberg, Reuters, WSJ, Financial Times
3. Tier 2: CNBC (realtime), MarketWatch, S&P Global Platts (commodities)

Full tier list: `references/trusted_news_sources.md`.

**Filter**: drop stock-specific small-caps, minor product updates, routine filings. Only keep news with clear market impact (price move, volume spike).

Capture per item: date+time, event type, source tier, initial reaction.

### Step 2: Load Knowledge Base References

**Always load**:
- `references/market_event_patterns.md`
- `references/trusted_news_sources.md`

**Conditionally load** (based on news types collected):

| News type | Load | Focus sections |
|---|---|---|
| Monetary policy | market_event_patterns.md | Central Bank Monetary Policy Events |
| Geopolitical | geopolitical_commodity_correlations.md | Energy, Precious Metals, matching region |
| Mega-cap earnings | corporate_news_impact.md | Specific company sections, sector contagion |
| Commodity news | geopolitical_commodity_correlations.md | Oil / Gold / Copper / etc. |

**Use references to**: predict expected reaction, identify anomalies (reaction differed from historical pattern), assess typical vs outsized magnitude, check if contagion spread as expected.

### Step 3: Impact Magnitude Assessment

Score each news item across 3 dimensions.

**1. Asset Price Impact (primary, 1-10 points)**:

Equity — index level (S&P 500 / Nasdaq / Dow):
- Severe ≥ ±2% → 10 pts
- Major ±1-2% → 7 pts
- Moderate ±0.5-1% → 4 pts
- Minor ±0.2-0.5% → 2 pts
- Negligible <0.2% → 1 pt

Equity — sector ETF: Severe ±5%+ / Major ±3-5% / Moderate ±1-3%
Equity — mega-cap stock: Severe ±10%+ / Major ±5-10% / Moderate ±2-5%

Commodities:
- Oil (WTI/Brent): Severe ±5%+ / Major ±3-5% / Moderate ±1-3%
- Gold: Severe ±3%+ / Major ±1.5-3% / Moderate ±0.5-1.5%
- Base metals: Severe ±4%+ / Major ±2-4% / Moderate ±1-2%

Bonds — 10Y Treasury yield: Severe ±20bps+ / Major ±10-20bps / Moderate ±5-10bps
FX — DXY: Severe ±1.5%+ / Major ±0.75-1.5% / Moderate ±0.3-0.75%

**2. Breadth Multiplier**:
- Systemic (3×): multiple asset classes, global markets — FOMC surprise, banking crisis, war outbreak
- Cross-asset (2×): equities + commodities, or equities + bonds — inflation surprise, geopolitical supply shock
- Sector-wide (1.5×): entire sector / related sectors — tech earnings cluster, energy policy
- Stock-specific (1×): single company (unless mega-cap moves index)

**3. Forward-Looking Modifier**:
- Regime change: +50% — Fed pivot, major geopolitical realignment
- Trend confirmation: +25% — consecutive strong inflation prints, sustained earnings beats
- Isolated event: 0% — single data point within range, company-specific
- Contrary signal: −25% — good news ignored, bad news rallied

**Formula**: `Impact Score = (Price Impact × Breadth Multiplier) × (1 + Forward Modifier)`

Examples:
- FOMC 75bps hawkish + S&P −2.5% systemic, trend-confirm: (10 × 3) × 1.25 = **37.5**
- NVDA earnings beat + NDQ +1.5% sector-wide, trend-confirm: (10 × 1.5) × 1.25 = **18.75**
- Middle East flare, oil +8% / S&P −1.2% cross-asset isolated: (10 × 2) × 1.0 = **20**

Rank all items by score desc → determines report ordering.

### Step 4: Market Reaction Analysis

For each item with score > 5, track reaction across assets:

**Equities**: index perf (S&P / Nasdaq / Dow / Russell 2000), sector rotation, mega-cap moves, Growth vs Value, Large vs Small.
**Fixed income**: 2Y / 10Y / 30Y yields, curve shape, credit spreads (IG, HY), TIPS breakevens.
**Commodities**: energy (WTI/Brent/NG), precious metals, base metals, ags (if relevant).
**FX**: DXY, EUR/USD, USD/JPY, GBP/USD, EM currencies, safe havens (JPY, CHF).
**Derivatives**: VIX, put/call ratio, unusual options volume, futures positioning.

**Pattern comparison vs knowledge base**:
- Consistent — matched historical pattern
- Amplified — reaction > typical (investigate: positioning, sentiment, cumulative factors)
- Dampened — reaction < typical (investigate: already priced in, offsetting factors)
- Inverse — opposite direction (investigate: "good news is bad news", Fed pivot hopes)

**Anomaly flags**: market shrugged off market-moving news / overreaction to minor news / contagion failed to spread / safe havens broke correlations.

**Sentiment indicators**: risk-on vs risk-off regime, crowded-trade unwinds, follow-through vs reversal.

### Step 5: Correlation and Causation Assessment

**Multi-event interaction**:
- Reinforcing — same direction (hawkish FOMC + hot CPI → amplified bearish, often non-linear)
- Offsetting — opposite directions (good earnings + geopolitical risk → muted net; identify dominant factor)
- Sequential — prior event primes next (first hike modest / second hike severe due to cumulative tightening)
- Coincidental — unrelated but simultaneous (note attribution uncertainty)

**Geopolitical ↔ commodity correlation** (use `geopolitical_commodity_correlations.md`):
- Energy: map conflict/sanction → supply disruption risk → actual vs feared impact → temporary spike vs sustained
- Precious metals: safe-haven flows vs real-rate drivers, central bank buying
- Industrial metals: demand destruction from slowdown fears, China factor
- Ags: Black Sea grain (Russia-Ukraine), weather overlays, food security policy

**Transmission channels**:
- Direct: News → immediate price (OPEC cut → oil up)
- Indirect: News → economic effect → price (rate hike → mortgage rates → housing → homebuilders)
- Sentiment: News → risk appetite shift → reallocation (banking crisis → flight to quality)
- Feedback loop: selloff → margin calls → forced selling → deeper selloff

### Step 6: Report Generation

Output English Markdown report. Section skeleton (fill all sections, skip only if N/A):

```markdown
# Market News Analysis Report — [Date Range]

## Executive Summary
[3-4 sentences: period, event count, dominant theme/regime, top 1-2 highest-impact events]

## Market Impact Rankings
| Rank | Event | Date | Impact Score | Assets Affected | Reaction |

## Detailed Event Analysis
### [Rank]. [Event Name] (Impact Score: [X])
**Event Date** / **Event Type** / **Source**

#### Event Summary
[3-4 sentences: what happened, context (expected vs surprise), forward guidance]

#### Market Reaction
**Immediate (day-of)**:
- Equities: S&P [±%], NDQ [±%], sector rotation
- Bonds: 10Y yield [change], credit spreads
- Commodities: Oil/Gold/Copper [±%] (if relevant)
- FX: USD [±%], relevant pairs
- Volatility: VIX level/change

**Follow-through**: sustained / reversed / consolidated

**Pattern comparison**: expected vs actual (consistent / amplified / dampened / inverse) + explanation

#### Impact Assessment Detail
- Asset Price Impact: [severity] — justification
- Breadth: [systemic/cross-asset/sector/stock-specific] — affected markets
- Forward Significance: [regime change / trend confirm / isolated / contrary]
- **Score**: (Price × Breadth) × (1 + Forward) = [total]

#### Sector-Specific Impacts (if relevant)
[Sector: impact + reason, e.g. Tech −3% rate sensitivity, Energy +5% oil spillover]

#### Geopolitical-Commodity Correlation (geopolitical events only)
Commodity price move / supply-demand mechanism / historical precedent / expected duration

[Repeat per event in rank order]

## Thematic Synthesis
### Dominant Market Narrative
[Overarching theme across 10-day window]

### Interconnected Events
[How events related/compounded, sequential causation]

### Market Regime Assessment
Risk appetite: [Risk-On / Risk-Off / Mixed]
Evidence: sector performance, safe-haven flows, credit spreads, VIX
Sector rotation: Growth vs Value, Cyclicals vs Defensives, out/underperformers

### Anomalies and Surprises
[Unexpected reactions + likely explanation]

## Commodity Market Deep Dive
### Energy: WTI/Brent price level, % change, drivers; Natural Gas if significant
### Precious Metals: Gold/Silver level, drivers (rates, safe haven, central banks)
### Base Metals: Copper/Aluminum if significant
### Agricultural: if relevant

## Forward-Looking Implications
### Market Positioning Insights
[What this analysis suggests for positioning: overweight/underweight, defensive posture]

### Upcoming Catalysts
[Near-term events that may drive markets — next FOMC, CPI, earnings clusters]

### Risk Scenarios
[Downside + upside scenarios with probability-weighted impacts]

## Data Sources and Methodology
- News sources consulted: [list]
- Analysis period: [exact date range]
- Market data: [data sources used]
- Knowledge base references loaded: [which references]
```

**Tone**: rigorous, quantified, English. Avoid vague words ("significant", "large") — always use numbers (%, bps).

## Resources

### references/
- `market_event_patterns.md` — central bank decisions, inflation/jobs data, geopolitical events, earnings, credit events, commodity events, recession indicators, historical case studies, pattern-recognition framework
- `geopolitical_commodity_correlations.md` — energy/precious metals/base metals/ags correlations with geopolitical conflicts, rare earths, regional frameworks (Middle East / Russia-Europe / Asia-Pacific / LatAm), time-horizon guidance
- `corporate_news_impact.md` — Magnificent 7, financial mega-caps, healthcare mega-caps, energy mega-caps, consumer staples, industrial mega-caps, earnings/product launch/M&A frameworks, sector contagion
- `trusted_news_sources.md` — tier 1-4 source map, search strategies, red-flag sources to avoid

## Important Notes

- All thinking + output in English
- WebSearch/WebFetch only — no API keys
- Filter: Tier 1 market-moving events only
- Rank by impact score (Price × Breadth × (1+Forward))
- Target period: past 10 days from current date
- FOMC / central bank decisions get highest priority
- Distinguish correlation from causation rigorously
- Quantify all market reactions with specific %, bps
- Conditionally load references based on news types

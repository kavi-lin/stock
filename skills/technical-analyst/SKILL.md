---
name: technical-analyst
description: This skill should be used when analyzing weekly price charts for stocks, stock indices, cryptocurrencies, or forex pairs. Use this skill when the user provides chart images and requests technical analysis, trend identification, support/resistance levels, scenario planning, or probability assessments based purely on chart data without consideration of news or fundamental factors.
market: market-agnostic
scope: single-ticker
data_sources: [chart image or yfinance]
---

# Technical Analyst

Weekly-chart-driven technical analysis → probabilistic scenarios + structured report. Pure chart analysis, no news/fundamental input. See `README.md` for example usage scenarios and pedagogy.

## Core Principles

1. **Pure chart analysis** — conclusions from observable chart data only
2. **Systematic approach** — follow the workflow steps, don't skip
3. **Objective** — avoid subjective bias, present both bull + bear possibilities
4. **Probabilistic scenarios** — express future as probability-weighted outcomes (not a single prediction)
5. **Sequential processing** — analyze each chart individually, save each report before moving to the next

## Analysis Workflow

### Step 1: Receive Chart Images

Confirm receipt, count charts, note any user-requested focus areas. Process sequentially.

### Step 2: Load Framework

**Read `references/technical_analysis_framework.md`** — covers trend classification, S/R identification, MA interpretation, volume analysis, chart patterns, scenario probability framework, objectivity discipline.

### Step 3: Per-Chart Systematic Analysis

#### 3.1 Trend
- Direction: uptrend / downtrend / sideways
- Strength: strong / moderate / weak
- Duration + potential exhaustion signals
- Higher highs/lows vs lower highs/lows pattern

#### 3.2 Support / Resistance
- Horizontal support levels
- Horizontal resistance levels
- Trendline S/R
- S/R role reversals
- Confluence zones (multiple levels aligning)

#### 3.3 Moving Averages
- Price vs 20W / 50W / 200W MAs
- Alignment: bullish / bearish / neutral configuration
- Slope: rising / falling / flat
- Recent or pending crossovers
- MAs as dynamic S/R

#### 3.4 Volume
- Trend: increasing / decreasing / stable
- Spikes + context (at S/R? on breakout?)
- Confirmation vs divergence with price
- Climax / exhaustion patterns

#### 3.5 Patterns + Price Action
- Reversal patterns (hammers, shooting stars, engulfing, H&S, double top/bottom)
- Continuation patterns (flags, triangles)
- Significant candlestick formations
- Recent breakouts / breakdowns

#### 3.6 Synthesize
- Integrate all elements into coherent current assessment
- Most significant factors
- Conflicting signals or ambiguity
- Key levels that will determine direction

### Step 4: Probabilistic Scenarios (2-4)

Each scenario must include:
1. **Name** — descriptive (e.g. "Bull Case: Breakout Above Resistance")
2. **Probability** — % likelihood (all scenarios must sum to 100%)
3. **Description** — what this scenario entails + how it unfolds
4. **Supporting factors** — technical evidence (min 2-3 factors)
5. **Target levels** — expected price levels if scenario plays out
6. **Invalidation level** — specific price that negates this scenario

**Typical framework**:
- Base Case (40-60%): most likely from current structure
- Bull Case (20-40%): upside breakout scenario
- Bear Case (20-40%): downside breakdown scenario
- Alternative (5-15%): lower-probability but plausible

Adjust probabilities by strength of supporting factors. Probabilities must sum to 100%.

### Step 5: Generate Report

**Read `assets/analysis_template.md`** and populate all sections:
1. Chart Overview
2. Trend Analysis
3. Support and Resistance Levels
4. Moving Average Analysis
5. Volume Analysis
6. Chart Patterns and Price Action
7. Current Market Assessment
8. Scenario Analysis (2-4 scenarios with probabilities)
9. Summary
10. Disclaimer

**File naming**: `[SYMBOL]_technical_analysis_[YYYY-MM-DD].md` (e.g. `SPY_technical_analysis_2025-11-02.md`)

### Step 6: Multiple Charts

Complete full workflow + save report per chart **before** moving to next. Do not batch. Notify user when all charts done.

## Quality Standards

**Objectivity**:
- Strictly observable chart data only
- No external info (news / fundamentals / sentiment)
- No subjective language ("I think", "I feel")
- Express uncertainty clearly when signals ambiguous
- Always show both bull + bear possibilities

**Completeness**:
- Cover every section of the template
- Specific price levels for support / resistance / targets (no vague descriptions)
- Justify probability estimates with technical factors
- Include invalidation levels per scenario
- Note limitations / caveats

**Clarity**:
- Precise technical terminology, correctly used
- Professional tone
- Logical structure
- Specific price levels (no vague descriptions)
- Scenarios distinct and mutually exclusive

## Resources

| File | When | Contains |
|---|---|---|
| `references/technical_analysis_framework.md` | Always, before analysis | Full methodology (trend / S/R / MA / volume / patterns / scenario framework / objectivity discipline) |
| `assets/analysis_template.md` | Every report | Full report structure with required sections |

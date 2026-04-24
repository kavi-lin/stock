# technical-analyst — Background & Example Scenarios

Accompanies `SKILL.md` (execution rules). Extended example usage scenarios + design rationale live here.

---

## Example Usage Scenarios

### Example 1: Single Chart Analysis

```
User: "Please analyze this weekly chart of the S&P 500"
[Provides chart image]

Analyst:
1. Confirms receipt of chart image
2. Reads technical_analysis_framework.md for methodology
3. Conducts systematic analysis (trend, S/R, MA, volume, patterns)
4. Develops 3 scenarios with probabilities
   (e.g. 55% bullish continuation, 30% consolidation, 15% reversal)
5. Generates comprehensive analysis report using template
6. Saves as SPY_technical_analysis_2025-11-02.md
```

### Example 2: Multiple Chart Analysis

```
User: "Analyze these three charts: Bitcoin, Ethereum, and Nasdaq"
[Provides 3 chart images]

Analyst:
1. Confirms receipt of 3 charts
2. Reads technical_analysis_framework.md (once, reused across charts)
3. Analyzes Bitcoin → saves BTC_technical_analysis_2025-11-02.md
4. Analyzes Ethereum → saves ETH_technical_analysis_2025-11-02.md
5. Analyzes Nasdaq → saves NDX_technical_analysis_2025-11-02.md
6. Notifies user that all three analyses are complete
```

### Example 3: Focused Analysis Request

```
User: "I'm particularly interested in whether this stock will break above resistance.
       Analyze the chart."
[Provides chart image]

Analyst:
1. Conducts full systematic analysis (all 6 subsections)
2. Pays special attention to resistance levels and breakout probability
3. Develops scenarios with emphasis on breakout vs rejection
4. Assigns probabilities based on volume, trend strength, proximity to resistance
5. Generates complete report with focused scenario analysis
```

---

## Design Rationale

### Why weekly charts only?

Daily charts have too much noise for structural trend analysis; monthly charts lag too much for actionable scenarios. Weekly strikes the balance — noise-filtered but still responsive.

### Why "pure chart analysis"?

This skill is intentionally narrow. It's designed to be combined with other skills (market-news-analyst, us-stock-analysis for fundamentals) by upstream protocols (investment V4.8 Phase 2). Keeping it "pure" means the subagent's output is easy to audit and doesn't double-count news factors already captured by another subagent.

### Why probability-weighted scenarios instead of one prediction?

Point predictions create false precision. Scenarios with probabilities force the analyst to acknowledge the alternative paths and their triggers (invalidation levels). Forces honest calibration.

### Why save per-chart report before next chart?

Two reasons:
1. Avoids context contamination — prior chart's analysis bleeding into the next
2. Partial progress is preserved if analysis is interrupted mid-batch

---

## Used By

- **`investment_protocol_v4_8.md`** — Phase 2 Technical blind-analyst subagent
- Standalone user requests with chart images

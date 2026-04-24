# us-stock-analysis — Background & Pedagogy

Accompanies `SKILL.md` (execution rules). This file holds extended output / formatting guidance and example queries that help humans understand what this skill does and produces, but which Claude doesn't need loaded during execution.

---

## Output Guidelines (Extended)

### General Principles

- **Use tables** for financial data and comparisons — they're easier to scan than prose
- **Bold** key metrics and findings
- **Include data sources and dates** — reproducibility
- **Quantify** whenever possible — numbers beat adjectives
- **Present both bull and bear perspectives** — balance
- **Be clear about assumptions and uncertainties** — don't pretend more confidence than you have

### Formatting

- **Headers** for clear section separation
- **Tables** for metrics, comparisons, historical data
- **Bullet points** for lists, factors, risks
- **Bold text** for key findings, important metrics
- **Percentages** for growth rates, returns, margins
- **Currency formatted consistently** — `$B` for billions, `$M` for millions, keep it consistent through the doc

### Tone

- Objective and balanced
- Acknowledge uncertainty (don't pretend you know the future)
- Support claims with data (no bare assertions)
- Avoid hyperbole ("best stock ever" → red flag)
- Present risks clearly — downside scenarios with specifics

---

## Example Queries (What This Skill Handles)

### Basic Info
- "What's the current price of AAPL?"
- "Give me key metrics for Tesla"
- "Quick overview of Microsoft stock"

### Fundamental
- "Analyze NVDA's financials"
- "Is Amazon overvalued?"
- "Evaluate Apple's business quality"
- "What's Google's debt situation?"

### Technical
- "Technical analysis of TSLA"
- "Is Netflix oversold?"
- "Show me support levels for AAPL"
- "What's the trend for AMD?"

### Comprehensive
- "Complete analysis of Microsoft"
- "Give me a full report on AAPL"
- "Should I invest in Tesla? Give me detailed analysis"

### Comparison
- "Compare AAPL vs MSFT"
- "Tesla vs Nvidia — which is better?"
- "Analyze Meta vs Google"

---

## Why Conditional Reference Loading

The `references/` folder has 4 files totalling ~1100 lines of methodology. Loading all of them for a simple "what's AAPL price?" query wastes tokens. `SKILL.md` uses a conditional load table so Claude pulls only what's needed:

| User ask pattern | What gets loaded |
|---|---|
| Basic / quick overview | Nothing beyond SKILL.md |
| "Analyze X financially" | fundamental-analysis.md + financial-metrics.md |
| "Technical analysis" / "TA" | technical-analysis.md |
| "Full report" / "complete analysis" | All 4 references |
| "Compare X vs Y" | fundamental-analysis.md + financial-metrics.md + report-template.md (comparison section) |

---

## Used By

This skill is invoked from:
- **`investment_protocol_v4_8.md`** — Phase 2 Fundamentals blind-analyst subagent
- Direct user requests — `/stock-analysis AAPL`, "analyze NVDA"
- Other skills that need per-ticker fundamentals as a prerequisite

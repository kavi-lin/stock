# market-news-analyst — Background & Pedagogy

Accompanies `SKILL.md` (execution rules + rubric). This file holds the principles, common pitfalls, and verbose report guidance that were trimmed out for token efficiency but are valuable for human understanding and auditing.

---

## Key Analysis Principles

When conducting market news analysis, apply these 10 principles:

1. **Impact Over Noise** — Focus on truly market-moving news, filter out minor events
2. **Multi-Asset Perspective** — Analyze across equities / bonds / commodities / FX to understand full impact
3. **Pattern Recognition** — Compare against historical precedents while noting unique aspects
4. **Causation Discipline** — Be rigorous about attributing market moves to specific news vs coincidental timing
5. **Forward-Looking** — Emphasize implications for future market behavior, not just backward-looking description
6. **Objectivity** — Separate market reaction (what happened) from personal view (what should happen)
7. **Quantification** — Use specific numbers (%, bps) rather than vague terms ("significant", "large")
8. **Source Credibility** — Weight official sources and Tier 1 news over rumors and unverified reports
9. **Breadth Analysis** — Individual stock moves only significant if mega-cap or systemic signal
10. **English Consistency** — All thinking, analysis, output in English for consistency

---

## Common Pitfalls to Avoid

### Over-Attribution
Not every market move is news-driven. Technicals, flows, month-end rebalancing all exist. **Acknowledge when attribution is uncertain**. If a news item coincides with a macro rotation already in motion, the news might just be the excuse, not the cause.

### Recency Bias
Latest news isn't always most important. **Rank by actual impact, not chronological order**. A CPI print from 9 days ago that shifted the Fed's trajectory outranks yesterday's minor earnings miss.

### Hindsight Bias
Distinguish "obvious in retrospect" from "surprising at the time". **Note consensus expectations vs actual outcomes**. A +0.3% CPI surprise that now seems inevitable may have been genuinely shocking pre-release.

### Single-Factor Analysis
Markets respond to multiple factors simultaneously. **Acknowledge interaction effects**. A stock selloff attributed solely to earnings may also involve positioning, sector rotation, or macro backdrop.

### Ignoring Magnitude
A "hot" CPI that's 0.1% above consensus is different from 0.5% above. **Quantify surprise factor**. The magnitude of surprise, not just its direction, drives reaction.

---

## Report Section — Detailed Guidance

`SKILL.md` Step 6 ships a compact section skeleton. This section expands on what each sub-section is trying to accomplish and what Claude should emphasize.

### Executive Summary (3-4 sentences)
The "elevator pitch" — a reader who only reads this should know: the period covered, how many significant events fired, the dominant regime (risk-on/off, sector rotation direction), and the 1-2 highest-impact events. Avoid listing — synthesize.

### Market Impact Rankings (table)
Sort descending by impact score. Row count: typically 5-15 events for a 10-day window; drop Impact < 5 to keep signal-to-noise high.

### Detailed Event Analysis (per event)

**Event Summary** — 3-4 sentences on *what happened*:
- Key details: rate decision magnitude, earnings beat/miss size, conflict developments
- Context: was this expected or a surprise? What was consensus going in?
- Forward guidance: what did policymakers / CEOs / etc. say about the future?

**Market Reaction** — split into two time frames:
- *Immediate (day-of)*: intraday moves across all asset classes
- *Follow-through*: did subsequent sessions sustain, reverse, or consolidate the move?

**Pattern Comparison** — the core analytical step. Pull expected reaction from references, compare to actual:
- **Consistent**: reaction matched pattern (e.g. Fed hike → tech down, USD up)
- **Amplified**: reaction exceeded pattern (e.g. inflation +0.3% surprise → 2× typical selloff — investigate positioning, sentiment, cumulative factors)
- **Dampened**: reaction below pattern (e.g. geopolitical event → oil barely moved — investigate: already priced in? offsetting factors?)
- **Inverse**: opposite direction (e.g. good news ignored, bad news rallied — investigate "good news is bad news" dynamics, Fed pivot hopes)

**Impact Assessment Detail** — show your work:
- State the Price Impact category and why (cite specific % moves)
- State Breadth multiplier and which markets were touched
- State Forward-Looking modifier and rationale (regime change? trend continuation?)
- Compute the score: `(Price × Breadth) × (1 + Forward)`

**Sector-Specific Impacts** — only when relevant:
- Which sectors amplified the move, which sectors diverged
- Explain the mechanism (e.g. "Tech −3% on rate sensitivity", "Energy +5% on oil spillover")

**Geopolitical-Commodity Correlation** — only for geopolitical events:
- Which commodity was affected, supply/demand mechanism, historical precedent (cite reference), expected duration (temporary shock vs sustained)

### Thematic Synthesis

Stitch events into a narrative:
- **Dominant Narrative**: e.g. "Persistent inflation concerns dominated despite mixed economic data"
- **Interconnected Events**: Event A + Event B → combined impact; sequential causation if applicable
- **Market Regime Assessment**: risk appetite, supporting evidence (sector perf, safe-haven flows, credit spreads, VIX); sector rotation direction
- **Anomalies**: reactions that deviated from expected patterns — flag them and attempt explanation

### Commodity Deep Dive

Relevant when geopolitical / energy / supply events were in the period. Cover energy, precious metals, base metals, ags as relevant. Always tie back to the macro event that drove the commodity move.

### Forward-Looking Implications

Three things:
1. **Market positioning insights** — overweight / underweight / defensive posture
2. **Upcoming catalysts** — next FOMC, CPI, earnings clusters
3. **Risk scenarios** — downside + upside scenarios with probability-weighted impacts

### Data Sources and Methodology

Reproducibility: list news sources consulted, exact date range, market data sources, which reference files were loaded.

---

## Why 6 Steps in That Order

- **Step 1 (collect)** before anything — you can't rank what you haven't seen
- **Step 2 (load references)** after collection because what to load depends on what you collected
- **Step 3 (score)** before **Step 4 (analyze reaction)** — you need to know which events matter enough to warrant deep reaction analysis (cutoff is Impact > 5)
- **Step 4 (reaction)** before **Step 5 (correlation)** — you need individual event reactions before you can compare across events
- **Step 6 (report)** last — report structure follows the analytical hierarchy, not the temporal order of events

---

## English-Only Rationale

All references, patterns, and historical case studies are documented in English. Keeping the analysis chain (thinking → references → report) in a single language avoids translation artifacts when matching observed market reactions to historical patterns. Non-English user prompts are fine — the *output* stays English.

---

## Historical Context

- This skill was built to cover the 10-day market retrospective use case, not realtime alerts
- It complements `market-sentiment-analyzer` (realtime F&G / VIX) and `sector-analyst` (weekly sector rotation)
- Used inside `news_protocol_v2.md` Phase 3 (news catalyst collection) and investment protocol V4.8 Phase 2 News subagent

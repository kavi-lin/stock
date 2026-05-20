---
name: supply-chain-event-analyst
description: Map up/downstream dependencies (suppliers/customers), identify critical bottlenecks, and correlate historical events (disruptions, contracts) with price action for Technology/Semis, Industrial, Energy, and Chemical stocks. Use when user asks for 產業鏈, 供應鏈, 上下游, supply chain analysis, key customers, major suppliers, or dependencies for a ticker.
market: us-equity
scope: sector-logic-driven
data_sources: [WebSearch, yfinance, FMP, dependency_logic.json]
---

# Supply-Chain Event Analyst

> ## ⚠️ DEPRECATED (v3.14.2)
>
> This skill has been **superseded** by `scripts/nexus/supply_chain.py`, the
> Nexus knowledge-graph supply-chain generator. The legacy `chain_mapper.py`
> stub here only resolves FMP profile data; it never did the WebSearch-heavy
> ecosystem mapping the SKILL.md prescribed. Production paths (Nexus Tier-1
> loader, supply-chain page, `/api/supply-chain/generate`) all use the Nexus
> generator now.
>
> **Replacements:**
> - **Generate a supply chain for a theme/ticker** →
>   `python3 scripts/nexus/supply_chain.py <theme_or_ticker>`
>   (router-driven; codex / claude / gemini all work).
> - **Quick supplier/customer probe** → call FMP `/company/profile/<TICKER>`
>   directly, or keep using `chain_mapper.py` (2.7 KB stub) for the same data.
>
> This SKILL.md + `chain_mapper.py` are retained as read-only reference for
> the dependency_logic.json schema and historical context. **No new feature
> work will land here.** New callers should target the Nexus path.

## Purpose
Deconstruct a company's ecosystem to identify vulnerability to external shocks (raw material prices, customer demand shifts, geopolitical disruptions). This skill bridges the gap between macro sector trends and individual ticker performance by tracing **value transmission**.

## Methodology

### Step 1: Ecosystem Mapping
1.  Run `python3 skills/supply-chain-event-analyst/scripts/chain_mapper.py <TICKER>` to get basic sector info and check for existing cache.
2.  If cache is missing or FMP data is empty, perform targeted **Web Searches**:
    *   `[TICKER] major suppliers 2024-2026 revenue exposure`
    *   `[TICKER] largest customers list annual report`
    *   `[TICKER] key raw materials and component dependencies`
3.  Reference `skills/supply-chain-event-analyst/references/dependency_logic.json` to identify which nodes in the sector value chain are most critical.

### Step 2: Historical Event Correlation
1.  Search for major news events in the last 24 months involving these keywords:
    *   `supply chain disruption`, `factory shutdown`, `key contract win`, `supplier bankruptcy`, `price hike`, `tariff impact`.
2.  Correlate event dates with **price action (via yfinance)**.
    *   *Example*: Did a supplier's profit warning cause a same-day drop in the subject ticker? (Lead-lag analysis).

### Step 3: Risk & Opportunity Score
Assign a **Dependency Score (1-10)**:
*   **High (8-10)**: Concentrated customer base (e.g., >20% revenue from 1 client) or single-sourced critical components (e.g., ASML for Lithography).
*   **Med (4-7)**: Diversified suppliers but subject to common commodity prices (e.g., Energy/Chemicals).
*   **Low (1-3)**: High vertical integration or massive supplier redundancy.

## Sector-Specific Guidance

| Sector | Focus Nodes | Key Warning Signals |
|---|---|---|
| **Semiconductors** | EDA -> Equipment -> Foundry -> OSAT | Lead time increases, TSM utilization, Export curbs |
| **Energy** | E&P -> Refining -> Storage | WTI/Brent spread, Inventory builds, Regional conflict |
| **Industrial** | Raw Materials -> Components -> Assembly | Freight rates, Order backlog, PMI New Orders |
| **Chemicals** | Feedstock -> Speciality -> Application | Natural Gas prices, Feedstock costs, Environmental reg |

## Output Format

### [TICKER] Ecosystem Report
1.  **Upstream (Suppliers)**: List top 3-5 with dependency level.
2.  **Downstream (Customers)**: List top 3-5 with revenue impact.
3.  **Historical Event Matrix**: (Date | Event | Impact on Price | Duration).
4.  **Transmission Alert**: Current status of supply chain (Healthy / Stressed / Fragile).
5.  **Skill Cross-check**: How this affects `earnings-valuation-forecaster` (e.g., Adjusting EPS growth down if input costs rise).

## Usage
*   Natural language: 「分析 TSLA 的產業鏈上下游」「NVDA 供應商有哪些」「Energy 產業鏈風險」
*   Command: `python3 skills/supply-chain-event-analyst/scripts/chain_mapper.py <TICKER>`

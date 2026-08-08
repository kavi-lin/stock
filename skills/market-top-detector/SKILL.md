---
name: market-top-detector
description: Detects market top probability using O'Neil Distribution Days, Minervini Leading Stock Deterioration, and Monty Defensive Sector Rotation. Generates a 0-100 composite score with risk zone classification. Use when user asks about market top risk, distribution days, defensive rotation, leadership breakdown, or whether to reduce equity exposure. Focuses on 2-8 week tactical timing signals for 10-20% corrections.
market: us-equity
scope: market-level
data_sources: [yfinance]
---

> **Upstream alignment**: fork 自 [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills)（2026-04）。最近對齊審查 **2026-08-08**（V4.111.6）：回灌 v3 清理 — quote/historical 鏈移除死的 v3 fallback（全端點 legacy 403），historical 遷 `stable/historical-price-eod/full` + flat-list normalizer + timeseries 截斷（對應上游 c54959e / 20a9a1 / 3776da1）。sector daily 路徑（`sector/market_top_yfinance.py`）不受影響。

# Market Top Detector Skill

## Purpose

Detect the probability of a market top formation using a quantitative 6-component scoring system (0-100). Integrates three proven market top detection methodologies:

1. **O'Neil** - Distribution Day accumulation (institutional selling)
2. **Minervini** - Leading stock deterioration pattern
3. **Monty** - Defensive sector rotation signal

Unlike the Bubble Detector (macro/multi-month evaluation), this skill focuses on **tactical 2-8 week timing signals** that precede 10-20% market corrections.

## When to Use This Skill

**English:**
- User asks "Is the market topping?" or "Are we near a top?"
- User notices distribution days accumulating
- User observes defensive sectors outperforming growth
- User sees leading stocks breaking down while indices hold
- User asks about reducing equity exposure timing
- User wants to assess correction probability for the next 2-8 weeks

**Japanese:**
- 「天井が近い？」「今は利確すべき？」
- ディストリビューションデーの蓄積を懸念
- ディフェンシブセクターがグロースをアウトパフォーム
- 先導株が崩れ始めているが指数はまだ持ちこたえている
- エクスポージャー縮小のタイミング判断
- 今後2〜8週間の調整確率を評価したい

## Prerequisites

**Required:**
- **yfinance** (no key). Canonical production path uses `sector/market_top_yfinance.py`, which reuses every analysis function from this skill but swaps the FMP client for yfinance — no API key, no WebSearch required. Works under Claude / Codex / Gemini / cron equally.

**Optional (improves sentiment + breadth scoring; missing → recorded in `data_quality.missing_optional`):**
- **50DMA breadth** (S&P 500 % above 50DMA): `--breadth-50dma <pct>` `--breadth-50dma-date <YYYY-MM-DD>`
- **CBOE Put/Call ratio**: `--put-call <ratio>` `--put-call-date <YYYY-MM-DD>`
- **Margin debt YoY**: `--margin-debt-yoy <pct>` `--margin-debt-date <YYYY-MM-DD>`
- **VIX term structure**: `--vix-term {steep_contango|contango|flat|backwardation}` (auto-detected from yfinance ^VIX/^VIX3M if not supplied)

> **Codex compatibility note (v3.14.2)**: The original SKILL spec mandated WebSearch to fetch the optional metrics above. That requirement is now downgraded — the script falls back to yfinance + TraderMonty breadth (auto-fetched) when those flags are absent, and reports the missing inputs in `data_quality.missing_optional`. Claude users can still WebSearch + supply the flags for higher accuracy; Codex / cron users get a graceful degraded score.

**Data Freshness:** All optional inputs should be from the most recent 3 business days for accurate analysis.

## Difference from Bubble Detector

| Aspect | Market Top Detector | Bubble Detector |
|--------|-------------------|-----------------|
| Timeframe | 2-8 weeks | Months to years |
| Target | 10-20% correction | Bubble collapse (30%+) |
| Methodology | O'Neil/Minervini/Monty | Minsky/Kindleberger |
| Data | Price/Volume + Breadth | Valuation + Sentiment + Social |
| Score Range | 0-100 composite | 0-15 points |

---

## Execution Workflow

### Canonical entry — `sector/market_top_yfinance.py` (production / cron / Codex)

```bash
python3 sector/market_top_yfinance.py --output-dir sector/market_top_cache/

# With optional sentiment / breadth inputs (Claude WebSearch may supply these):
python3 sector/market_top_yfinance.py \
  --output-dir sector/market_top_cache/ \
  --breadth-50dma 45.0 --breadth-50dma-date 2026-05-19 \
  --put-call 0.72  --put-call-date  2026-05-19 \
  --margin-debt-yoy 5.2 --margin-debt-date 2026-04-30 \
  --vix-term contango
```

This is the entry used by `daily_update.sh` Step 3 and by `bridge.py`. It:

1. Pulls ^GSPC / QQQ / ^VIX / ^VIX3M / Leading ETFs / Sector ETFs via **yfinance** (no key).
2. Auto-fetches 200DMA breadth from TraderMonty CSV (override `--breadth-200dma`, disable `--no-auto-breadth`).
3. Reuses every calculator in `skills/market-top-detector/scripts/` (composite scoring, distribution days, leading-stock health, defensive rotation, breadth divergence, index technical, sentiment, follow-through-day, historical comparator, scenario engine).
4. Records any missing optional flag in `data_quality.missing_optional` instead of failing.

### Optional Claude-only enhancement — WebSearch supplements

When running under Claude (with WebSearch / WebFetch tools available), the model may collect the four optional inputs and pass them as flags above for a higher-confidence score:

```
1. S&P 500 50DMA breadth      — "S&P 500 percent stocks above 50 day moving average"
2. CBOE equity Put/Call ratio — "CBOE equity put call ratio today"
3. Margin debt YoY            — "FINRA margin debt latest year over year"
4. VIX term structure         — usually auto-detected from ^VIX3M; WebSearch only when yfinance fails
```

Codex / cron callers skip this step entirely — the script falls back to yfinance + TraderMonty breadth and reports `data_quality.missing_optional`.

### Legacy entry (deprecated) — `scripts/market_top_detector.py`

The original FMP-based entry `python3 skills/market-top-detector/scripts/market_top_detector.py --api-key $FMP_API_KEY ...` still works but requires FMP. Production switched to the yfinance adapter above in v3.x because FMP-only blocked Codex / cron runs. Keep using `sector/market_top_yfinance.py` unless you specifically need FMP data lineage.

### Present Results

Present the generated Markdown report to the user, highlighting:
- Composite score and risk zone
- Data freshness warnings (if any data older than 3 days)
- Strongest warning signal (highest component score)
- Historical comparison (closest past top pattern)
- What-if scenarios (sensitivity to key changes)
- Recommended actions based on risk zone
- Follow-Through Day status (if applicable)
- Delta vs previous run (if prior report exists)

---

## 6-Component Scoring System

| # | Component | Weight | Data Source | Key Signal |
|---|-----------|--------|-------------|------------|
| 1 | Distribution Day Count | **25%** | FMP API | Institutional selling in last 25 trading days |
| 2 | Leading Stock Health | **20%** | FMP API | Growth ETF basket deterioration |
| 3 | Defensive Sector Rotation | **15%** | FMP API | Defensive vs Growth relative performance |
| 4 | Market Breadth Divergence | **15%** | Auto (CSV) + optional CLI | 200DMA (auto from TraderMonty) / 50DMA (optional `--breadth-50dma`) breadth vs index level |
| 5 | Index Technical Condition | **15%** | FMP API | MA structure, failed rallies, lower highs |
| 6 | Sentiment & Speculation | **10%** | yfinance + optional CLI | VIX (yfinance), Put/Call + term structure (optional `--put-call` / `--vix-term`) |

## Risk Zone Mapping

| Score | Zone | Risk Budget | Action |
|-------|------|-------------|--------|
| 0-20 | Green (Normal) | 100% | Normal operations |
| 21-40 | Yellow (Early Warning) | 80-90% | Tighten stops, reduce new entries |
| 41-60 | Orange (Elevated Risk) | 60-75% | Profit-taking on weak positions |
| 61-80 | Red (High Probability Top) | 40-55% | Aggressive profit-taking |
| 81-100 | Critical (Top Formation) | 20-35% | Maximum defense, hedging |

---

## API Requirements

**Required:** none — yfinance is keyless. Canonical entry `sector/market_top_yfinance.py`.
**Optional:** Claude WebSearch (to supply 50DMA breadth / Put-Call / margin debt as CLI flags); legacy FMP path for `scripts/market_top_detector.py`. Both improve accuracy when available; absence is logged in `data_quality.missing_optional`, never fails.

## Output Files

- JSON: `market_top_YYYY-MM-DD_HHMMSS.json`
- Markdown: `market_top_YYYY-MM-DD_HHMMSS.md`

## Reference Documents

### `references/market_top_methodology.md`
- Full methodology with O'Neil, Minervini, and Monty frameworks
- Component scoring details and thresholds
- Historical validation notes

### `references/distribution_day_guide.md`
- Detailed O'Neil Distribution Day rules
- Stalling day identification
- Follow-Through Day (FTD) mechanics

### `references/historical_tops.md`
- Analysis of 2000, 2007, 2018, 2022 market tops
- Component score patterns during historical tops
- Lessons learned and calibration data

### When to Load References
- **First use:** Load `market_top_methodology.md` for full framework understanding
- **Distribution day questions:** Load `distribution_day_guide.md`
- **Historical context:** Load `historical_tops.md`
- **Regular execution:** References not needed - script handles scoring

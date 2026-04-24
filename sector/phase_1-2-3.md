# Phase 1–3 執行細節

---

## PHASE 1 — SECTOR ROTATION SCAN

**Agent**: Sector Rotation Analyst
**資料來源**: `sector-analyst` CSV（不需 API key）

> Phase 1 完成後，將各產業 `uptrend_ratio` 的平均值回填至 `_phase0.uptrend_ratio_overall`。

**JSON Schema** → 見 `schema.md` Phase 1

---

## PHASE 2 — THEME INTELLIGENCE

**Agent**: Theme Intelligence Analyst

**執行指令**（script 自管 cache freshness，無需手動 check mtime）：

```bash
python3 skills/theme-detector/scripts/theme_detector.py --skip-if-fresh 10800
```

- Cache < 3h → script 立即 exit 0（< 1 秒），agent 讀 `skills/theme-detector/cache/theme_detector_*.json` 最新檔（`theme_source: THEME_CACHE`）
- Cache stale 或缺失 → 正常執行 140–180 秒，新 cache 寫入 `skills/theme-detector/cache/`，再讀最新檔

> ⚠️ Cache stale 時 FINVIZ scrape 約 **140-180s**。**禁止 `timeout < 240`**（會被殺 retry）。

> Phase 2 與 Phase 3 完全獨立 → 並行執行。

**JSON Schema** → 見 `schema.md` Phase 2

---

## PHASE 3 — NEWS CATALYST REVIEW

**Agent**: News Catalyst Analyst
**資料來源**: `market-sentiment-analyzer` + `economic-calendar-fetcher` + `earnings-calendar` + WebSearch（≤ 5 個，narrative 類）

### ⚠️ 執行順序（強制）

```
Step 1  market-sentiment-analyzer   → fear_greed / VIX / RSI / Put-Call
Step 2  economic-calendar-fetcher   → FOMC / CPI / NFP / GDP 日期
Step 3  earnings-calendar           → 本週 mid+ 大型股財報日
Step 4  reuse _phase0.fred_snapshot → fed_rate_direction / yield (不再 search)
Step 5  WebSearch HARD CAP ≤ 5     → 見 query 範本
```

> **禁止**用 WebSearch 抓 Step 1-4 已有的（FOMC/財報日期、利率、F&G、VIX）。
> **禁止**同主題 ≥ 2 個查詢。

### Step 5 WebSearch Query 範本（最多 5 個）

```
1. "stock market news today {DATE} S&P 500 close" — 當日 narrative（必）
2. "Trump tariff statement {DATE} sector" — 若 named_targets 非空
3. "Iran Israel oil news {DATE}" — 若 Energy/Defense ∈ HOT/WARM
4. "this week mega cap earnings beat miss" — 財報 surprise narrative
5. (預留給當日突發)
```

> 禁止查：Russia/Ukraine、FDA PDUFA、bank earnings dates、copper price、AI capex、DOJ Powell（個股層級，不在 sector 範圍）。

### 情緒數值提取（填入 `political_overlay`）

從 `market-sentiment-analyzer` 輸出提取：
- `composite_score` → `fear_greed_index`
- `composite_score label` → `fear_greed_label`
- `vix.current` → `vix_current`
- `put_call_ratio.equity_pc_ratio` → `put_call_ratio`
- `spy_momentum.rsi_14` → `spy_rsi`

**extreme_sentiment 判斷**：`composite_score > 80 OR composite_score < 20` → `extreme_sentiment_triggered = true`

---

## Extreme Sentiment Playbook

> 當 `extreme_sentiment_triggered = true` 時的級聯效應，依 Greed / Fear 分兩案處理。

### Case 1: Extreme Greed（composite_score > 80）

```
Trigger 條件：
  composite_score > 80
  OR (VIX < 15 AND Put/Call < 0.6 AND SPY RSI > 70)

級聯動作：
  1. 所有 HOT 產業 → risk_flags += "extreme_greed_warning"

  2. Phase 4b Devil's Advocate 義務：
     → 必須對至少 2 個 HOT 板塊提出「獲利了結/泡沫破裂」反方論點
     → tail-risk-analyzer 優先覆蓋前 3 個 HOT（效率上限不變，維持前 3）

  3. Phase 4c 強制：
     → HOT 板塊 composite_score < 80 → 降為 WARM
     → final_regime_stance 不得為 AGGRESSIVE，最高 NEUTRAL

  4. HANDOFF：明確提及「極度樂觀環境，謹慎進場」
```

### Case 2: Extreme Fear（composite_score < 20）

```
Trigger 條件：
  composite_score < 20
  OR (VIX > 30 AND Put/Call > 1.2 AND SPY RSI < 30)

級聯動作：
  1. COLD/AVOID 產業：評估升級機會
     IF (COLD AND uptrend_ratio > 0.5 AND tail_risk < 40)
       → 標記 "fear_capitulation_opportunity"

  2. Phase 4c：cyclical COLD 板塊 composite_score × 1.10
     （前提：基本面未惡化）

  3. Devil's Advocate 義務軟化：
     → 不必強制挑戰 COLD 板塊
     → 改為尋找「恐慌被過度反應」的機會板塊

  4. Phase 4c：可升級 final_regime_stance 為 AGGRESSIVE
     （條件：FTD 確認 + synthesized_exposure > 50%）

  5. HANDOFF：提及「極度恐慌環境，高風險但機會浮現」
```

---

### Phase 3 預算

| Step | Tool | 耗時 |
|---|---|---|
| 1 | `market-sentiment-analyzer` script | ~6s |
| 2 | `economic-calendar-fetcher` script | ~5s |
| 3 | `~/.claude/skills/earnings-calendar/scripts/fetch_earnings_fmp.py` | ~5s |
| 4 | reuse `_phase0.fred_snapshot` | 0s |
| 5 | WebSearch ≤ 5 | ~50s |

**總預算 ≤ 80s**

**JSON Schema** → 見 `schema.md` Phase 3

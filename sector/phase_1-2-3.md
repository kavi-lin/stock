# Phase 1–3 執行細節

---

## PHASE 1 — SECTOR ROTATION SCAN

**Agent**: Sector Rotation Analyst
**資料來源**: `sector-analyst` CSV（不需 API key）+ FMP 估值層（V1.4，FMP HTTP REST，hard-required）

### Step 1 — uptrend_ratio (CSV)

> Phase 1 完成 CSV pass 後，將各產業 `uptrend_ratio` 的平均值回填至 `_phase0.uptrend_ratio_overall`。

### Step 2 — Sector Valuation Layer（V1.4 必跑）

執行：

```bash
python3 sector/scripts/fetch_sector_valuation.py --date {SCAN_DATE}
```

- 輸出：`sector/cache/sector_valuation_<DATE>.json`
- 失敗 = **HARD FAIL**：腳本 `sys.exit(1)` 並印 `[ERROR] FMP ...`。**Phase 1 中止，不繼續 Phase 2/3/4/5**。
  - Fix：檢查 `$FMP_API_KEY`、FMP 服務狀態、rate limit。修好後重跑整個 protocol。
- 成功後將每個 sector 的 valuation block（`pe_ttm` / `pe_zscore_1y` / `rs_vs_spy_3m` / `rs_vs_spy_20d` / `rs_vs_spy_5d` / `etf_volume_ratio_20d` / `etf` 等）寫入 `_phase1.sectors[i].sector_valuation`（schema.md 已定義）。
- **V2.9.0 多週期 RS 用法**：3M 強但 5d/20d 同向轉弱 → 動能耗盡訊號（給 Phase 4b divergence 提示，不改 score）。零新增 API call（重用既有 3M chart）。

> ⚠️ V1.4 的 FMP 估值層**不**像 FRED Layer E 是 graceful optional —— 缺它就無 valuation_penalty，最終 verdict 會缺 overbought/oversold 對照。protocol 必須 abort，由人介入。

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
- **Default `--max-themes=25` / `--max-stocks-per-theme=25`** 與 `daily_update.sh` 對齊（避免 sector protocol 觸發重跑時降回 10 themes 鎖住下游 thematic-screener）

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
Step 3b sector-earnings-pulse       → 過去 30d sector beat_rate / surprise (V1.4 必跑)
Step 3c sector-smart-money          → insider / senate signals (V1.4 必跑)
Step 3d sector-news-cache           → FMP /news/stock per-sector top 10 (V1.4 必跑;取代 WebSearch 主力)
Step 3e general-news-cache          → FMP /news/general-latest 20 articles (V1.71+ soft;narrative 補位)
Step 4  reuse _phase0.fred_snapshot → fed_rate_direction / yield (不再 search)
Step 5  WebSearch HARD CAP（依 Step 3e available 動態）→ 僅補 narrative 突發,不抓 Step 3d/3e 已有的
```

### Step 1 — Market Sentiment

```bash
python3 skills/market-sentiment-analyzer/scripts/sentiment.py --json
```

- 輸出 stdout JSON：`composite_score` / `label` / `vix` / `put_call_ratio` / `spy_momentum.rsi_14` 等。
- 失敗 = soft（缺值，後續 `political_overlay` 各欄位填 null，extreme_sentiment_triggered 視為 false）。

### Step 2 — Economic Calendar

```bash
python3 ~/.claude/skills/economic-calendar-fetcher/scripts/get_economic_calendar.py \
  --from {SCAN_DATE} --to {SCAN_DATE+7d} --format json
```

- argparse 介面（**不**支援 `--json` / `--days N`，會 unrecognized arguments）。
- 輸出 stdout JSON：本週 FOMC / CPI / NFP / GDP / PMI 等事件。
- 失敗 = soft（缺 macro 事件，依賴 WebSearch 補；不 abort protocol）。

### Step 3 — Earnings Calendar

```bash
python3 ~/.claude/skills/earnings-calendar/scripts/fetch_earnings_fmp.py {SCAN_DATE} {SCAN_DATE+7d}
```

- **位置參數**（**不**支援 `--json` / `--days N` / `--from` / `--to`，會 `Invalid start date format` 報錯）。
- 第三位置參數可選 API key（預設讀 `$FMP_API_KEY`）。
- 輸出 stdout JSON：本週 mid+ 大型股財報日（含 EPS estimate / market cap）。
- 失敗 = soft（缺 earnings catalyst，Phase 3 可繼續；不 abort protocol）。

### Step 3b — Sector Earnings Pulse（V1.4 必跑）

```bash
python3 sector/scripts/fetch_earnings_pulse.py --date {SCAN_DATE}
```

- 輸出：`sector/cache/sector_earnings_pulse_<DATE>.json`
- 失敗 = HARD FAIL（earnings calendar 段；analyst 段為 SOFT，失敗欄位 null）。中止 protocol 僅在 earnings calendar 失敗。
- 成功後將 `sectors` block 寫入 `_phase3.sector_earnings_pulse`。
- **Rubric 用法**：`news_catalyst` 元件 ±5
  - `beat_rate_30d > 0.7 AND surprise_score_avg > 0`（且 report_count ≥ 5）→ +5
  - `beat_rate_30d < 0.4`（且 report_count ≥ 5）→ −5
  - `report_count < 5` → 樣本不足，skip 不調分
- **V2.9.0 PT 訊號用法**（不改 rubric，給 Phase 4b 提示）：
  - HOT consensus + `analyst_pt_upside_median_pct < 0.03` AND `pt_sample_size >= 3` → 「目標價已被消化」divergence challenge
- 想省 ~111 calls（grades + PT consensus）可加 `--skip-analyst`（V2.9.0+；舊 `--skip-grades` 仍接受 alias）

### Step 3c — Smart Money Signals（V1.4 必跑）

```bash
python3 sector/scripts/fetch_smart_money.py --date {SCAN_DATE}
```

- 輸出：`sector/cache/sector_smart_money_<DATE>.json`
- 失敗 = HARD FAIL（insider/senate 段；institutional 段為 SOFT）。
- 成功後將 `sectors` block 寫入 `_phase3.smart_money_signals`。
- **Phase 4b 用法**：HOT consensus + insider ratio < 0.5 + senate net buy < 0 → 強制 divergence challenge（見 `phase_4-5.md` Step 2 規則 5）。
- **V2.9.0 institutional Q-on-Q 用法**（不改 rubric，給 Phase 4b 提示）：
  - HOT consensus + `institutional_holders_qoq_delta < 0` AND `institutional_ownership_pct_delta < 0` AND `institutional_sample_size >= 3` → 「機構淨流出」divergence challenge
- 想省 ~131 calls（institutional Q-on-Q）可加 `--skip-institutional`（V2.9.0+）

### Step 3d — Sector News Cache（V1.4 必跑;取代 WebSearch 主力）

```bash
python3 sector/scripts/fetch_sector_news.py --date {SCAN_DATE} --lookback-days 2
```

- 輸出：`sector/cache/sector_news_<DATE>.json`(11 sectors × top 10 articles)
- 失敗 = HARD FAIL。
- 此 cache 是 `top_catalysts` 的主資料源 — 從每 sector 的 articles 抽取 catalyst 事件,引用 `url`/`publisher` 為 source
- WebSearch step 5 縮減到 ≤2 query 只用於補 narrative-class(整體市場情緒、突發事件未被 FMP 索引)。**禁止**用 WebSearch 抓 Step 3d 已有的個股新聞

### Step 3e — General Narrative News Cache（V1.71+ soft）

```bash
python3 sector/scripts/fetch_general_news.py --date {SCAN_DATE}
```

- 輸出：`sector/cache/general_news_<DATE>.json`（FMP `/stable/news/general-latest`，limit=20）
- 失敗 = SOFT；寫 `{available: false, reason: ...}`，protocol 不中斷
- 用途：補 Phase 3 Step 5 「broader market narrative」query。如果 `available=true`，protocol 從這個 cache 抽取「當日 S&P 500 narrative」；Step 5 WebSearch budget 從 ≤2 降到 ≤1（只留給突發事件）

> **禁止**用 WebSearch 抓 Step 1-4 / Step 3d-3e 已有的（FOMC/財報日期、利率、F&G、VIX、個股新聞、broader narrative）。
> **禁止**同主題 ≥ 2 個查詢。

### Step 5 WebSearch Query 範本（V1.71+：依 Step 3e available 動態調整）

**Case A — `general_news.available = true`**（HARD CAP ≤ 1）

```
1. (僅當日突發、且 general_news cache 確實沒提及 — 例：盤中突發 Trump tariff、地緣政治、macro surprise)
```

> 若無突發、cache 已涵蓋當日 narrative，**可跳過**整個 Step 5。

**Case B — `general_news.available = false`**（HARD CAP ≤ 2，回退原 V1.4 規則）

```
1. "stock market news today {DATE} S&P 500 close" — 當日 narrative（必）
2. (預留給當日突發 — Trump tariff / 地緣政治 / 突發 macro)
```

> 禁止查：個股新聞（已在 Step 3d sector_news cache）；當日 broader narrative（已在 Step 3e general_news cache，Case A）；FOMC/財報日期/利率/F&G/VIX（已在 Step 1-4）；Russia/Ukraine、FDA PDUFA、bank earnings dates、copper price、AI capex、DOJ Powell（個股層級，不在 sector 範圍）。

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
| 3b | `sector/scripts/fetch_earnings_pulse.py`（含 grades-summary） | ~30s |
| 3c | `sector/scripts/fetch_smart_money.py` | ~25s |
| 3d | `sector/scripts/fetch_sector_news.py` | ~10s |
| 3e | `sector/scripts/fetch_general_news.py`（soft） | ~3s |
| 4 | reuse `_phase0.fred_snapshot` | 0s |
| 5 | WebSearch ≤ 1（Case A）/ ≤ 2（Case B） | ~10–20s |

**總預算 ≤ 110s**

**JSON Schema** → 見 `schema.md` Phase 3

---

### Step 6 — 輸出 `_phase3.upcoming_events[]`

從 Step 1-5 結果生成統一 schema 事件清單。**完整欄位定義** → `schema.md` Phase 3 + `reports/decision_review/UPCOMING_EVENTS_SCHEMA.md`。

**必填**：`id` / `date` / `category` / `title` / `tickers` / `sectors` / `impact` / `is_binary` / `within_48h`

**三個易踩坑**：
- `title` ≤ 36 字短標；**禁止**塞「（binary；看多/看空 X、Y）」括號補述（補述放 `description`，sector 名單放 `sectors`）
- `tickers[]` 只填**真實股票代號**；`DOJ` `FOMC` `CPI` `PMI` `NFP` 等機關/指標縮寫**禁止**塞 ticker（市場事件留空）
- `sectors[]` 用 GICS 英文加底線：`Technology` / `Real_Estate` / `Consumer_Discretionary` / `Communication`，**不寫中文**

**衍生 `upcoming_binary_risks[]`**（向後相容，bridge.py 優先讀新欄位）：對 `upcoming_events` 中 `is_binary=true` 的每筆，輸出 `{event: title, date, affected_sectors: sectors, within_48h}`。

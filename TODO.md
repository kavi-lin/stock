# INTEL COMMAND — Backlog & Tasks

> **Last Updated**: 2026-04-30 (v1.71.3 — Preflight popup 對齊 sidebar：sector/news 看內部 timestamp 不看 mtime)

---

## 🎯 活動 Backlog

### 路線 F — Finnhub 整合（提升吞吐量 + 補三大缺口）
**狀態**：PR-1/2/3 完成（雙抓架構落地），等實際整合到 investment_protocol 才進 PR-5/6。
- [x] ~~**[F-PR1]** `skills/finnhub-client/`：60/min throttle + cache + retry + 17 endpoints + 5 個 FMP-shape adapter~~
- [x] ~~**[F-PR2]** `skills/finnhub-client/scripts/diff_tool.py` + `run_diff.sh`：Finnhub vs FMP 9 欄位 × 10 ticker side-by-side 對照~~
- [x] ~~**[F-PR3]** 修正 FMP v3→stable 端點 + adapter peTTM 順序 + 新增 `dual_fetch.py`/`audit_drift_check.py`/`run_dual_fetch.sh`：採用 Finnhub canonical + FMP audit 雙抓設計，物理隔離 `_audit.*`~~
- [ ] **[F-PR4]** `skills/data-client/`：按資料種類路由 provider（market→Finnhub / financials→FMP / events→Finnhub-only / econ→FMP-only），加 `_source` tagging + conflict detection
- [x] ~~**[F-PR4.5]** 把 dual_fetch 接進 investment_protocol Phase 1（V4.8.1）：PM inline run + Phase 2 共通 prompt 加 TICKER DATA BUNDLE 段 + Fundamentals subagent 9 scalar 使用規則~~
- [x] ~~**[F-PR4.6]** 端到端驗證：跑 `分析 AMD` 驗證 dual_fetch 整合，7/7 條件全 PASS，subagent 正確引用 bundle 欄位且未洩漏 `_audit`~~

### 路線 ST — Short-Term Recommendation System (plan_short.md)
**狀態**：Step 1 完成（v1.46.0），Step 2-7 排程中。
- [x] ~~**[ST-Step1]** `skills/short-term-target/` skill：1d/5d/15d 預測，per-horizon weights、hard clamp、insufficient_data 規則、benchmark relative、trading_meta、weights.yaml 手動可調~~
- [x] ~~**[ST-Step2]** 加新主題到 `cross_sector_themes.md`（17→21）：Space / Quantum / Robotics / Utilities Defensive。Nuclear 已存在跳過；Healthcare Defensive 與既有 Healthcare & Pharma 重複跳過~~
- [x] ~~**[ST-Step3]** `thematic-screener` skill：串 theme-detector + short-term-target，含 concentration WARNING（不 REMOVE）~~
- [x] ~~**[ST-Step5]** Outcome tracking log：`data/recommendations/<DATE>.json` 含 regime snapshot — Step 3 內含實作~~
- [x] ~~**[ST-Step4]** Dashboard `radar.html` 「短期雷達」頁完成：bridge.py 注入 data.tactical + 雙分區（中期主題 + 短期 movers）+ 強制 §11.D 顯示規則（range/confidence breakdown/drivers/invalidation/concentration/trading meta）+ 桌面為主、預設展第 1 個~~

**🎉 plan_short.md 全 7 個 Step 完成** — Tactical Opportunity Radar v0.1 production-ready。後續觀察 outcome log 累積（3-4 週後達 N≥30 觸發 Step 7 KPI gate 評估）。
- [x] ~~**[ST-Step6]** `daily_update.sh` 整合 thematic-screener 自動跑（含 cache freshness 檢查 + 失敗不致命）~~
- [x] ~~**[ST-Step7]** `weekly_review.py` 每週末手動 recalibration tool，產生 `reports/SHORT_TERM_WEEKLY_<DATE>.md` 含 per-horizon stats + per-theme alpha + worst-cases + suggested adjustments + KPI gate（不自動覆蓋 config）~~
- [ ] **[F-PR5]** 遷移 `ftd-detector` 到 data-client（最低風險 pilot）
- [ ] **[F-PR6]** 遷移 `market-top-detector` + `us-stock-analysis`
- [ ] **[F-PR7]** 啟用新功能：`earnings-calendar` skill 修好（Finnhub `/calendar/earnings`）、`pead-screener` 啟動（`/stock/earnings` surprise）、新增 `insider-monitor` skill


### 路線 S — Skill 最小替代實作 + Review
**狀態**：4 個 missing skill 已建立最小可行實作並通過 smoke test，但需實戰驗證與閾值調整。
- [x] ~~**[S-BUILD-01]** `skills/market-sentiment-analyzer/` — yfinance VIX/SPY RSI + CNN F&G backend + PCR（~150 行）~~
- [x] ~~**[S-BUILD-02]** `skills/tail-risk-analyzer/` — 1y daily returns → kurt/skew/VaR/DD → fragility label（~120 行）~~
- [x] ~~**[S-BUILD-03]** `skills/portfolio-risk-manager/` — vol scaling + correlation + sector cap（~180 行）~~
- [x] ~~**[S-BUILD-04]** `skills/short-contrarian-analyst/` — Burry Score + T4 veto（~180 行）~~
- [x] ~~**[S-COPY]** 複製 9 個現有 skill 到 `skills/`~~
- [x] ~~**[S-REVIEW-01]** market-sentiment-analyzer 驗證：composite 63.9 (Greed)，VIX 18.2 NORMAL，CNN F&G backend 成功回傳 56.5；PCR endpoint 當前 null（CBOE JSON 不穩）— 可接受 fallback~~
- [x] ~~**[S-REVIEW-02]** tail-risk-analyzer 閾值校準完成：跑 7 檔 SPY/TLT/NVDA/TSLA/COIN/RIVN/BTC；重新加權 kurt 10% / skew 10% / var 15% / DD 30% / vol 35%（原本 kurt 30% 過高）；校準後 SPY/TLT=ROBUST, NVDA/TSLA=MODERATE, COIN/RIVN/BTC=FRAGILE ✓~~
- [x] ~~**[S-REVIEW-03]** portfolio-risk-manager 驗證：讀取 positions.json (3 筆) 成功，avg_corr=0.393 合理，Tech sector cap 正確觸發 → final cap 8.5%~~
- [x] ~~**[S-REVIEW-04]** short-contrarian-analyst 修正完成：~~
  - ~~D/E 單位：yf 一致返回 percentage（NVDA 7.26, KO 139.79, PG 68.72）→ 改為 always `/100`，NVDA 現在正確顯示 0.07~~
  - ~~FCF fallback：KO `freeCashflow` 回傳 -1.46B 錯誤，`operatingCashflow` 正確 7.4B → 加入 `if FCF<=0 and OpCF>0: FCF = OpCF * 0.85` fallback~~
  - ~~7 檔測試（NVDA/KO/PG/JNJ/TSLA/RIVN/COIN）Burry Score 分布 25-45 合理~~
- [x] ~~**[S-REVIEW-05]** 4 skill 整合測試完成：以 NVDA 為目標按 investment_protocol_v4_6 Phase 2/Phase 4 序列呼叫 4 skill，全部回傳合法 JSON，串接計算 final_position=4.46%（8.5% × 0.75 fragility × 0.7 Burry WARNING）。protocol 需手動指示 Claude 執行 `python3 skills/<name>/scripts/...` 而非自行模擬~~

### 路線 N — News Protocol V2（RSS 兩階段 + 4 Agent 圓桌 + Dashboard 整合）
- [x] ~~**[N-PROTO]** 草擬 `news/news_protocol_v2.md`~~
  - 兩階段漏斗：Stage 1 RSS shallow triage → Stage 2 WebFetch deep debate
  - Team 從 3 人擴至 5 人：News Collector + Bull + Bear + **Sector Analyst** + **Macro/Policy Expert** + Arbiter
  - Arbiter 加權：平權 25/25/25/25，或依新聞類型動態（FOMC→Macro 40%, Earnings→Sector 40%）
  - Stage 1 晉級門檻：`|score|≥3` OR `binary+within_48h` OR `HIGH credibility + |score|≥2`；硬上限 5 則
  - Stage 1 輸出「Triage 篩選表」給人類審核（可手動加選）
  - 只有 Stage 2 才能 patch `sector_intel.json` / `phase0.json`
  - `news_logs` verdict 新增欄位：`depth: shallow|deep`、`tickers_mentioned[]`、`sector_view`、`macro_view`
  - FLASH mode 保持單階段 deep
- [x] ~~**[N-RSS]** 撰寫 `news/fetch_news_rss.py`~~
  - 來源：Reuters / Bloomberg / Yahoo Finance / MarketWatch / CNBC RSS
  - 輸出：`news/news_logs/YYYY-MM-DD_raw.json`（標題 + 摘要 + source + timestamp + url）
  - 去重（headline 相似度）、時間視窗參數（default 24h）
- [x] ~~**[N-ARCHIVE]** `news_protocol_v1.md` 移至 `archive/old_protocols/news/`~~
- [x] ~~**[N-CLAUDEMD]** `CLAUDE.md` 更新 news protocol 路徑 → v2 + VERSION bump 1.7.0~~
- [x] ~~**[N-DASH-BTN]** `page-decisions.js` 每張卡 footer 新增 📰 FLASH 按鈕 → 複製單股 prompt 到剪貼簿 + toast~~
- [x] ~~**[N-DASH-NEWS]** `page-news.js` 更新按鈕合併 reload + 複製「新聞分析 DIGEST」prompt + toast~~
- [x] ~~**[N-TOAST]** `utils.js` 新增 `UI.showToast()` + `UI.copyToClipboard()` 共用元件~~
- [x] ~~**[N-I18N]** `i18n.js` 新增 `flash_btn` / `flash_toast` / `digest_toast` 鍵值（中英雙語）~~
- [x] ~~**[N-BRIDGE]** `bridge.py` 過濾 v2 `depth=shallow`；支援 `tickers_mentioned` / `sector_view` / `macro_view` / `news_type` 新欄位~~

### 路線 B — Calendar 頁面（事件日曆 + 決策回顧 hub）
- [ ] **[B-BRIDGE]** `bridge.py` 導出 `upcoming_binary_risks[]` + `sector_news_sentiment{}` 至 data.json 頂層
- [ ] **[B-PAGE]** 建立 `calendar.html`
  - 月曆視圖，顯示財報日期、FOMC、地緣政治 binary events
  - 每個事件顯示受影響產業 + direction（bullish/bearish/binary）
  - 資料來源：`_phase3.upcoming_binary_risks` + `earnings-calendar` skill
  - **右側 7-day 旗標** + **每格決策 badges (📈/🎯/💪/📊/📰/💼/🏛️)**
  - 點擊格子 → drawer 顯示該日所有 decisions 的回顧卡片（決策 vs 現實 + verdict + tuning_hooks）
  - **右上角按鈕「🤖 Ask LLM to Review」** → 複製 `reports/decision_review/REVIEW_PROMPT.md` + 最新 `event_index_*.json` 到 clipboard
- [ ] **[B-SKILL]** 整合 `earnings-calendar` skill（FMP API），產出 JSON cache 讓 bridge 讀取
- [x] ~~**[B-MILESTONE1]** Event index milestone 1：17 樣本 extractor + verdict + tuning_hooks（中繼檔已刪），保留 extractors + REVIEW_PROMPT~~
- [x] ~~**[B-INDEXER]** 全量 indexer：掃所有 60+ deep-dive / sector / news / momentum / theme / radar / earnings / weekly / postmortem，產出 `reports/decision_review/event_index_<DATE>.json` + `event_index_latest.json`~~
- [ ] **[B-DAILY]** `daily_update.sh` 加 Step 7：跑 indexer + render markdown
- [x] ~~**[B-SCHEMA]** UpcomingEvent 統一 schema (`reports/decision_review/UPCOMING_EVENTS_SCHEMA.md`)；bridge.py 加 `aggregate_upcoming_events()` 接 sector-protocol；page-calendar.js 改 fetch `data.json.upcoming_events`；news.html 移除 binary-risks sidebar~~
- [x] ~~**[B-PROMPT]** Sector-protocol prompt 改寫：`sector/phase_1-2-3.md` 加 Step 6 指示 LLM 直接吐符合 UPCOMING_EVENTS_SCHEMA 的 `_phase3.upcoming_events[]`；`sector/schema.md` 補欄位定義；`sector/phase_4-5.md` 內部引用改 `upcoming_events.is_binary` filter。`bridge.py:_from_sector_protocol_new()` 優先讀新欄位，舊欄位 fallback 走 legacy regex cleaner~~

**Upcoming events feeds — 補充 sector-protocol 之外的事件源（豐富即將發生）**

> 評估：以現有資源能讓「即將發生」7d 涵蓋率從 ~4 → 20+ 筆。FRED 不適合當事件源（給歷史/即時數據，非未來事件）；yfinance 純價格無 metadata；scenario-analyzer 是分析非資料源。

Tier 1（高 ROI、3 個全做估 1 天工作）：
- [x] ~~**[B-FEED-FED-YAML]** `config/fed_calendar.yaml`：2026 8 次 FOMC + 7 份 Minutes 釋出日 + Jackson Hole；bridge.py:_from_fed_calendar()~~
- [x] ~~**[B-FEED-EARNINGS]** **FMP** `/stable/earnings-calendar`：bridge.py:_from_fmp_earnings() (Finnhub 在實測中漏 CVX/XOM/V/MA 等大咖, 改用 FMP); revenueEstimated >= $500M filter; impact 由 revenue 決定 (>=$10B→high, $1-10B→med, else low); is_binary 由 _BINARY_TICKERS whitelist 決定 (~50 tickers Mag-7 + 大型 financial/pharma/energy/staples)~~
- [x] ~~**[B-FEED-ECON]** FMP stable `/economic-calendar`：bridge.py:_from_fmp_econ() 只保留 high impact；過濾舊月份修正資料 + 模糊 dedupe 同日同名事件；is_binary 對 CPI/PCE/NFP/FOMC/GDP/ISM 自動觸發。FMP v3 已 deprecated 改用 stable 端點~~

> 結果：upcoming_events 從 4 → **29 筆**（next 7d = 18 筆）。FMP econ 同 FOMC 日仍會出現「Fed Interest Rate Decision / FOMC Economic Projections / Fed Press Conference / Press Conference」4 筆相關 event 沒完全合併，可後續再優化。

Tier 2（中 ROI、純算式無 API）：
- [ ] **[B-FEED-OPEX]** Options expiry calendar（每月第三個週五 + quarterly）→ 純算式生成，category=`system`，impact=`med`，給 risk_flags 用
- [ ] **[B-FEED-INDEX]** Index rebalance dates（S&P 季末 / Russell 6 月）→ 硬編，category=`system`

Tier 3（情境性，等需求出現再做）：
- [ ] **[B-FEED-TREASURY]** Treasury auctions（FMP 或財政部 RSS）— 做 fixed income / 殖利率部位才補
- [ ] **[B-FEED-DIVIDENDS]** Finnhub `/calendar/dividends` — kanchi-dividend-sop 已用，整合進 upcoming_events
- [ ] **[B-FEED-IPO]** Finnhub `/calendar/ipo` — IPO 投機部位才補
- [ ] **[B-FEED-FED-WEB]** WebFetch Fed 官網 `/newsevents/calendar.htm` — 比 YAML 更即時（YAML 補不到的臨時 speeches）
- [ ] **[B-FEED-POLICY]** WebFetch 白宮/USTR 公告 — tariff / executive order（sector-protocol Phase 3 已有 WebSearch 抓部分）

### 路線 P — 富途牛牛推播即時整合
**狀態**：v1.58.0 完成。lazy-fetch 版本（無背景 thread），5s cache。
- [x] ~~**[P-TICKER]** `scripts/parse_futu_notifications.py`：中文股名 dict (~70 筆) + 英文 ticker regex + stopword 過濾。新增 `load_notifications()` / `is_available()` / `extract_tickers()` 純資料函式 + `--json` flag~~
- [x] ~~**[P-BACKEND]** `dashboard_server.py`：`GET /api/futu-notifications?limit=5` lazy fetch + 5s 記憶體 cache（取消原規劃的背景 thread 設計）~~
- [x] ~~**[P-CARD]** `Dashboard/index.html` Layer 5 卡片 + `script.js` IIFE：相對時間 + ticker pills + 60s 自動重整。Ticker pill 點擊只 prefill Quick Launch input（不直接入隊燒 token）~~

### 路線 C — Positions Tracker 強化
- [ ] **[C-IMPORT]** `import_firstrade_csv.py` — 解析 Firstrade 月結單 CSV → `positions.json`（避免手動輸入，安全方式取代非官方 API）
- [ ] **[C-CLOSE]** Dashboard 新增「平倉」動作：將 position status 改 closed，自動記錄 exit_price + realized_pl
- [ ] **[C-ADD]** 同一 ticker 加碼時提示「併入現有 avg cost」vs「另開 lot」兩個選項
- ❌ **[C-FT-PHASE1]** ~~`scripts/parse_firstrade_notifications.py` v0.1 discovery~~ — **已放棄**（v1.60.2）。Phase 1 跑出來 macOS NotificationCenter 30 天只 11 筆系統推播，Firstrade iPhone push 沒鏡像 (iOS 對金融類 app 不 relay 給 Continuity)；fallback Gmail MCP 也卡 insufficient auth scope。User 決定不繼續這條路線。Script 留在 repo（純讀 NC DB 工具，無副作用）作參考。
- ❌ **[C-FT-PHASE2]** ~~watch/parser 自動 sync positions.json~~ — 隨 PHASE1 一同放棄

### 路線 I — Invest Protocol V4.8 Refactor（移除多餘 + WebFetch→API）
**狀態**：Review 完成（v1.61.x），plan 寫在 `~/.claude/plans/`。Smoke test 跑完，feasibility 已確認。
**目標**：Phase 2 各 lane 把 web search 改 FMP/Finnhub API、Phase 1 dual_fetch 擴充欄位讓 Fundamentals lane 不重抓。每次 invest 從 30-45 min 降到 18-25 min。

**API Smoke test 結果**（2026-04-30 測 NVDA，FMP 升 Starter 後）：

| 廠商 | 可用 | 不可用 | 影響 |
|---|---|---|---|
| Finnhub free | quote / profile2 / metric / insider-transactions / insider-sentiment / recommendation / earnings(surprise) / calendar/earnings / company-news / splits / financials-reported | upgrade-downgrade / price-target / candle / dividend2（PREMIUM） | upgrade-downgrade + price-target 改用 FMP `/stable/` 替代 |
| FMP Starter | `/stable/profile / key-metrics-ttm / key-metrics / ratios-ttm / income-statement / balance-sheet / cash-flow / earnings-calendar / economic-calendar / shares-float`、`grades-historical / grades-consensus / grades-news / price-target-consensus / price-target-summary`、**`insider-trading/latest` / `insider-trading/statistics`**、**`historical-price-eod/light`+`full`**、`historical-chart/1hour`、`news/stock`、`senate-trades`、`quote / quote-short` | `/api/v3/*` + `/api/v4/*` 全是 **Legacy 永遠拿不到**；`/stable/short-interest`/`short-volume` 仍 Premium-only | short interest 必須 fallback yfinance；其他全部有 stable 替代 |

**子任務**：
- [x] ~~**[I-PA]** dual_fetch.py 9 → 15 scalar：加 `forwardPE`/`pegRatio`/`roeTTM`/`debtToEquity`/`fcfPerShareTTM`（Finnhub `/stock/metric` 內已有）+ `nextEarningsDate`（Finnhub `/calendar/earnings`）。Fundamentals lane rubric 改「以 bundle 為權威，skill 只算衍生指標」。**~80 行 / 風險低**~~ ✅ v1.62.0
- [x] ~~**[I-PB]** Sentiment lane 個股層 web search → 結構化 API：
  - **Insider 季度統計（主）**：FMP Starter `/stable/insider-trading/statistics` — 給 `acquiredDisposedRatio` / `totalAcquired` / `totalDisposed` / `acquiredTransactions` / `disposedTransactions` 季度統計（NVDA Q1 ratio=0.163 即「insider 主要在賣」），signal 直接可用
  - Insider 逐筆細節（補充）：Finnhub `/stock/insider-transactions`（free ✅）+ `/stock/insider-sentiment`（free ✅ MSPR score）
  - **Short interest fallback**：FMP Starter 仍無 `/short-interest`；改 yfinance `info.shortPercentOfFloat`（bi-monthly 更新但免費）
  - Reddit/X narrative 保留 web search（≤ 1 次，僅取 tone）
  - **~120 行 / 風險低**~~ ✅ v1.64.0
- [x] ~~**[I-PC]** News lane analyst rating → FMP `/stable/` 替代（Finnhub upgrade/price-target 都 PREMIUM）：
  - Upgrade/downgrade：FMP `/stable/grades-historical`（含 newGrade/previousGrade/action/analyst）
  - Price target：FMP `/stable/price-target-consensus`（high/low/median/consensus）+ `/stable/price-target-summary`（月/季/年 trend）
  - Recommendation：FMP `/stable/grades-consensus`（strongBuy/buy/hold/sell/strongSell counts）
  - Company news：Finnhub `/company-news`（free，含 sentiment/category）
  - Grade news：FMP `/stable/grades-news`（補充）
  - **~100 行 / 風險低**~~ ✅ v1.65.0
- [x] ~~**[I-PD]** Phase 0 L3 fallback web search → skill chain（market-sentiment + market-breadth + ftd + market-top）。`investment_protocol_v4_8.md` 行 33-35 重寫。**~50 行 / 風險中（Phase 0 是 critical path）**~~ ✅ v1.66.0
- [x] ~~**[I-PE]** Phase 0 schema 明列 `fear_greed_index` / `vix_current` / `spy_rsi_14` / `top_catalysts[]`；Phase 2 共通 prompt 直接 inline pass，避免 Phase 2 重抓。**~40 行 / 風險低**~~ ✅ v1.67.0
- [x] ~~**[I-PF]** Phase 2 共通 prompt 加「FORBID raw web search」白名單：list 哪些事情必須用 bundle/API，僅哪些少數例外才能 web search（management commentary / supply chain rumors / Reddit narrative）。**~20 行 / 風險低**~~ ✅ v1.68.0
- [x] ~~**[I-PG]** Technical lane 把 yfinance daily OHLC 換成 FMP `/stable/historical-price-eod/full`（Starter 解鎖）。優點：含 `vwap` 跟預算的 `change%`、結構化 API 比 scraping 穩、Starter 配額充裕。yfinance 保留作 fallback。**~40 行 / 風險低**~~ ✅ v1.63.0

**API call budget per protocol**（單 ticker）：

| Phase | 元件 | Finnhub calls | FMP calls | yfinance calls |
|---|---|---|---|---|
| Phase 0 | fred-macro / breadth / ftd / market-top | 0 | 0 | 5+（free） |
| Phase 0 | market-sentiment-analyzer (15min cache) | 0 | 0 | 1（共用） |
| Phase 1 | dual_fetch（既有 + I-PA 擴充） | 3（quote + metric + calendar/earnings） | 2（profile + key-metrics-ttm） | 0 |
| Phase 2 Fundamentals | I-PA 改後讀 bundle | 0 | 0 | 0 |
| Phase 2 Sentiment | I-PB | 1（insider-sentiment MSPR） | 1（insider-trading/statistics） | 1（shortPercentOfFloat） |
| Phase 2 News | I-PC | 1（company-news） | 4（grades-hist + price-target-consensus + grades-consensus + grades-news） | 0 |
| Phase 2 Technical | technical-analyst (I-PG 改後) | 0 | 1（historical-price-eod/full） | 0（fallback） |
| Phase 4 | risk_manager + tail_risk | 0 | 0 | 1（共用） |
| **Total** | — | **6** | **7** | **8** |

**配額限制**：
- Finnhub free 60 calls/min：6/ticker → 同時 10 ticker 才會撞 → **充裕**
- FMP free 250 calls/day：6/ticker → 每天最多 ~40 ticker → **正常使用沒問題，週末批次掃要注意**
- yfinance：無配額但有 IP rate limit，已有 cache 機制

**改進效果預估**：
- 每次 invest 時間 30-45 min → 18-25 min（Phase 2 lane 平行內 lane 自身省時）
- 結構化資料替代 web search 結果，subagent 數字 hallucination 風險大幅降低
- regression test：v1.39 既有 ticker 跑出來的 final_score 不變超過 ±0.5

### 路線 FE — Fincept Strategy Extraction（短期訊號強化）
**背景**：從 `Fincept_enhance/FinceptTerminal` 掃描出可直接提取的短期交易算法，分三組工作：
(A) Renaissance 動能/均值回歸算法 → 整合進 `short-term-target`
(B) PLAN.md 原定的 Earnings Quality Analyzer → 整合進 Burry Agent
(C) 純算式 indicators 補齊 `short-term-target` 特徵集

**Source files**：
- `Fincept_enhance/FinceptTerminal/fincept-qt/scripts/agents/hedgeFundAgents/renaissance_technologies_hedge_fund_agent/strategies/`
- `Fincept_enhance/FinceptTerminal/fincept-qt/scripts/strategies/MACDTrendAlgorithm.py`
- `Fincept_enhance/FinceptTerminal/fincept-qt/scripts/algo_trading/indicators.py`
- `Fincept_enhance/PLAN.md`（Beneish M-Score 等算法規格）

#### Group A — 短期訊號算法（接進 short-term-target）
- [ ] **[FE-A1]** 提取 `momentum.py` 三層訊號：Optimal Lookback（5/10/20/40/60d Sharpe-like）、Trend Strength（R²）、Acceleration（short 5d − long 20d momentum）→ 包成 `skills/short-term-target/scripts/momentum_signals.py`，輸出 `{"acceleration": float, "trend_r2": float, "optimal_lookback": int, "signal": -1|0|1}`
- [ ] **[FE-A2]** 提取 `mean_reversion.py` 三層指標：Z-score（60d mean/std）、Hurst exponent、OU half-life → 包成 `skills/short-term-target/scripts/mean_reversion_signals.py`，輸出 `{"z_score": float, "hurst": float, "half_life_days": float|null, "is_mean_reverting": bool}`
- [ ] **[FE-A3]** 整合 A1+A2 到 `predict.py`：新增 `fincept_momentum` + `fincept_mean_reversion` 兩個 feature，並在 `weights.yaml` 加入對應權重欄位（預設 0，等 outcome log 累積後校準）
- [ ] **[FE-A4]** `statistical_arbitrage.py` regime detector → 接進 `predict.py` regime filter：regime=BULL 升 momentum 權重、regime=SIDEWAYS 升 mean_reversion 權重

#### Group B — Earnings Quality Analyzer（接進 Burry Agent）
> 延續 `Fincept_enhance/PLAN.md` 原定計畫，已確認 source 算法位置

- [ ] **[FE-B1]** 實作 `skills/earnings-quality-analyzer/scripts/quality.py`：提取 Beneish M-Score（8 factor）、Accrual Ratio（NI-OCF/TA）、CFO/NI、FCF/NI、Intangible Concentration、DSO 六個指標；FMP-native 無 BaseAnalyzer 依賴；輸出 JSON + `quality_label: CLEAN|CAUTION|RED_FLAG`
- [ ] **[FE-B2]** 實作 `skills/earnings-quality-analyzer/scripts/ratios.py`：多年度 key metrics 陣列（Revenue CAGR、GM%趨勢、ROIC 趨勢）；與 quality.py 共用 FMP raw cache
- [ ] **[FE-B3]** Protocol 整合：Phase 2 Burry inline 新增 `quality_label` 欄位；`macro_multiplier_rationale` 遇 RED_FLAG 時強制 Burry score penalty

#### Group C — 待評估（低優先）
- [ ] **[FE-C1]** 評估 `indicators.py` 的 Hurst + RSI + ADX 組合是否值得直接接進 `technical-analyst` skill（替換或補充 yfinance TA-Lib 輸出）

### 路線 D — 效能優化（低優先）
- [ ] **[ARCH-11]** `lucide.createIcons()` debounce（`requestAnimationFrame` 批次）
- [ ] **[ARCH-12]** Chart.js 惰性載入（只在 sector.html 載入）
- [ ] **[ARCH-13]** marked.js 惰性載入（viewReport 觸發時才載）
- [ ] **[ARCH-14]** `innerHTML` XSS 防護（`escapeHTML()` helper，已有 `UI.escapeHTML`，套用到剩餘欄位）

---

## ✅ 已完成歷史紀錄

- **V4.6 投資協議**：雙軌 entry、STAGED 狀態、Consensus bonus、移除 VOLATILE 雙重懲罰。
- **Sector Protocol V1.2**：主子檔拆分、三層訊號合成、決策樹 STEP A-G。
- **Dashboard 整合**：合併 decisions.html、ARCH-4/5 DataStore、ARCH-7/8/9/10Presenter 抽出。
- **Server 與 Infrastructure**：dashboard_server.py、Position modal、bridge.py 整合 positions.json、自動 mtime cache-busting。
- **文件整理**：歸檔至 `archive/`、README 對齊、CLAUDE.md 更新。

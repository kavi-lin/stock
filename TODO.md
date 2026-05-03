# INTEL COMMAND — Backlog & Tasks

> **Last Updated**: 2026-05-03 (v2.12.0)

---

## 🎯 活動 Backlog (Pending)

### 路線 H — thematic-screener v0.3 enrichment 後續
- [ ] **[H-1]** Backtest v0.2 vs v0.3：過去 30d/60d 推薦在 5d realized return / hit-rate 上差異
- [ ] **[H-2]** 加 Finnhub `/stock/recommendation-trends` 補充 grades-historical（更詳細買賣評等 distribution）
- [ ] **[H-3]** 加 short interest / days-to-cover label（目前只用 quality 不看 short crowding）
- [ ] **[H-4]** Tune `enrichment_multiplier` 加成係數 — 目前憑直覺設（earnings ×0.5 / quality ×0.6 / insider ×1.3 等），backtest 後校準

### 路線 G — FMP catalog 二階強化（v2.11.0 後續）
- [ ] **[G-1]** theme-detector 切 FMP-primary：`theme_detector.py:479` import 改 `fmp_industry_perf_client` 為主、`finviz_performance_client` 為 Tier C fallback。先 user review `skills/theme-detector/scripts/industry_name_mapping.yaml` accuracy。
- [ ] **[G-2]** FMP industry rolling perf 多週期 (1m/3m/6m/1y/ytd) — 改用 `historical-industry-performance` per industry 取代每日 snapshot 累積（API call 從 ~252 降到 ~128，且支援 compound 而非 sum）
- [ ] **[G-3]** sector-analyst overlay 進 sector_protocol Phase 4 估值面 rubric — 目前 `fmp_overlay` 只是輸出，未進決策邏輯
- [ ] **[G-4]** 71 finviz-only industries 二次審視 — Internet Retail / Department Stores / Confectioners / Beverages-Brewers / Textile / Pharmaceutical Retailers 等可能 FMP 用其他名稱包進去（如 "Software - Services" 包 Amazon？）
- [ ] **[G-5]** technicalIndicators FMP 整合 — momentum-monitor + technical-analyst 改吃 FMP RSI/SMA/EMA/ADX 直接結果，省 OHLC fetch + 跨 skill 一致性
- [ ] **[G-6]** commitmentOfTraders macro overlay → sector Phase 0（期貨籌碼信號目前完全空白）
- [ ] **[G-7]** marketHours 預檢 → `daily_update.sh` 跳過 NYSE 假日（目前盲跑）

### 路線 F — Finnhub 整合
- [ ] **[F-PR4]** `skills/data-client/`：按資料種類路由 provider（market→Finnhub / financials→FMP / events→Finnhub-only / econ→FMP-only），加 `_source` tagging + conflict detection
- [ ] **[F-PR5]** 遷移 `ftd-detector` 到 data-client（最低風險 pilot）
- [ ] **[F-PR6]** 遷移 `market-top-detector` + `us-stock-analysis`
- [ ] **[F-PR7]** 啟用新功能：`earnings-calendar` skill 修好（Finnhub `/calendar/earnings`）、`pead-screener` 啟動（`/stock/earnings` surprise）、新增 `insider-monitor` skill

### 路線 B — Calendar 頁面（事件日曆補充與自動化）
- [ ] **[B-DAILY]** `daily_update.sh` 加 Step 7：跑 indexer + render markdown

**Upcoming events feeds — 補充事件源（Tier 2 & 3）**
- [ ] **[B-FEED-OPEX]** Options expiry calendar（每月第三個週五 + quarterly）→ 純算式生成，category=`system`，impact=`med`，給 risk_flags 用
- [ ] **[B-FEED-INDEX]** Index rebalance dates（S&P 季末 / Russell 6 月）→ 硬編，category=`system`
- [ ] **[B-FEED-TREASURY]** Treasury auctions（FMP 或財政部 RSS）— 做 fixed income / 殖利率部位才補
- [ ] **[B-FEED-DIVIDENDS]** Finnhub `/calendar/dividends` — kanchi-dividend-sop 已用，整合進 upcoming_events
- [ ] **[B-FEED-IPO]** Finnhub `/calendar/ipo` — IPO 投機部位才補
- [ ] **[B-FEED-FED-WEB]** WebFetch Fed 官網 `/newsevents/calendar.htm` — 比 YAML 更即時（YAML 補不到的臨時 speeches）
- [ ] **[B-FEED-POLICY]** WebFetch 白宮/USTR 公告 — tariff / executive order

### 路線 C — Positions Tracker 強化
- [ ] **[C-IMPORT]** `import_firstrade_csv.py` — 解析 Firstrade 月結單 CSV → `positions.json`
- [ ] **[C-ADD]** 同一 ticker 加碼時提示「併入現有 avg cost」vs「另開 lot」兩個選項

### 路線 FE — Fincept Strategy Extraction（短期訊號強化）
- [ ] **[FE-A1]** 提取 `momentum.py` 三層訊號：Optimal Lookback、Trend Strength、Acceleration → `skills/short-term-target/scripts/momentum_signals.py`
- [ ] **[FE-A2]** 提取 `mean_reversion.py` 三層指標：Z-score、Hurst exponent、OU half-life → `skills/short-term-target/scripts/mean_reversion_signals.py`
- [ ] **[FE-A3]** 整合 A1+A2 到 `predict.py`：新增 `fincept_momentum` + `fincept_mean_reversion` 特徵與權重
- [ ] **[FE-A4]** `statistical_arbitrage.py` regime detector → 接進 `predict.py` regime filter
- [ ] **[FE-B1]** 實作 `skills/earnings-quality-analyzer/scripts/quality.py`：Beneish M-Score、Accrual Ratio 等 6 指標
- [ ] **[FE-B2]** 實作 `skills/earnings-quality-analyzer/scripts/ratios.py`：多年度 key metrics 趨勢
- [ ] **[FE-B3]** Protocol 整合：Phase 2 Burry inline 新增 `quality_label` 欄位與罰則
- [ ] **[FE-C1]** 評估 `indicators.py` 的 Hurst + RSI + ADX 是否接進 `technical-analyst`

### 路線 D — 效能優化（低優先）
- [ ] **[ARCH-11]** `lucide.createIcons()` debounce（`requestAnimationFrame` 批次）
- [ ] **[ARCH-12]** Chart.js 惰性載入
- [ ] **[ARCH-13]** marked.js 惰性載入
- [ ] **[ARCH-14]** `innerHTML` XSS 防護全面套用

---

## 📦 已完成任務詳情 (Archived Tasks)

### 路線 F — Finnhub 雙抓架構
- [x] ~~**[F-PR1]** `skills/finnhub-client/`：60/min throttle + cache + retry + 17 endpoints + 5 個 FMP-shape adapter~~
- [x] ~~**[F-PR2]** `skills/finnhub-client/scripts/diff_tool.py` + `run_diff.sh`：Finnhub vs FMP 對照~~
- [x] ~~**[F-PR3]** 修正 FMP v3→stable 端點 + adapter + dual_fetch.py 設計~~
- [x] ~~**[F-PR4.5]** 把 dual_fetch 接進 investment_protocol Phase 1 (V4.8.1)~~
- [x] ~~**[F-PR4.6]** 端到端驗證：AMD 分析驗證，7/7 條件全 PASS~~

### 路線 ST — Short-Term Target System
- [x] ~~**[ST-Step1]** `short-term-target` skill：1d/5d/15d 預測模型與權重配置~~
- [x] ~~**[ST-Step2]** 加新主題到 `cross_sector_themes.md` (17→21)~~
- [x] ~~**[ST-Step3]** `thematic-screener` skill 實作~~
- [x] ~~**[ST-Step4]** Dashboard `radar.html` 短期雷達頁完成~~
- [x] ~~**[ST-Step5]** Outcome tracking log 自動化儲存~~
- [x] ~~**[ST-Step6]** `daily_update.sh` 整合自動跑~~
- [x] ~~**[ST-Step7]** `weekly_review.py` 每週末校準工具~~

### 路線 S — Skill 建立與 Review
- [x] ~~**[S-BUILD-01~04]** 建立 Sentiment, Tail-Risk, Portfolio, Burry 4 個核心 Skill~~
- [x] ~~**[S-COPY]** 遷移既有 Skill 至 `skills/` 目錄~~
- [x] ~~**[S-REVIEW-01~05]** 全量 Skill 驗證與閾值校準，完成 NVDA 整合測試~~

### 路線 N — News Protocol V2
- [x] ~~**[N-PROTO]** 草擬 `news_protocol_v2.md` (RSS 兩階段漏斗 + 5 Agent)~~
- [x] ~~**[N-RSS]** 撰寫 `fetch_news_rss.py` (去重 + 多源)~~
- [x] ~~**[N-ARCHIVE]** 歸檔 V1 協議~~
- [x] ~~**[N-CLAUDEMD]** 更新 `CLAUDE.md` 版本至 1.7.0~~
- [x] ~~**[N-DASH-BTN/NEWS]** Dashboard 整合 FLASH 按鈕與 DIGEST 複製功能~~
- [x] ~~**[N-TOAST/I18N/BRIDGE]** 支援 Toast 通知、多語系與 bridge.py v2 欄位~~

### 路線 B — Calendar 頁面與 Feed
- [x] ~~**[B-BRIDGE]** `bridge.py` 整合 `aggregate_upcoming_events`~~
- [x] ~~**[B-PAGE]** 建立 `calendar.html` 月曆、詳情面板與 LLM Review~~
- [x] ~~**[B-SKILL]** 整合 `earnings-calendar` (FMP API) 至 bridge~~
- [x] ~~**[B-MILESTONE1]** Event index milestone 1 樣本提取與規則~~
- [x] ~~**[B-INDEXER]** 全量 indexer `build_event_index.py` 實作~~
- [x] ~~**[B-SCHEMA]** UpcomingEvent 統一 schema 與跨頁面整合~~
- [x] ~~**[B-PROMPT]** Sector-protocol prompt 改寫與 `upcoming_events` 輸出~~
- [x] ~~**[B-FEED-FED-YAML]** 整合 FED FOMC 日曆~~
- [x] ~~**[B-FEED-EARNINGS]** 整合 FMP 財報日曆 (Top 50 tickers + $500M filter)~~
- [x] ~~**[B-FEED-ECON]** 整合 FMP 經濟指標日曆 (High Impact Only)~~

### 路線 P — 富途牛牛推播整合
- [x] ~~**[P-TICKER]** `parse_futu_notifications.py` 實作~~
- [x] ~~**[P-BACKEND]** Server lazy-fetch + 5s cache 實作~~
- [x] ~~**[P-CARD]** Dashboard 即時通知卡片實作~~

### 路線 C — Positions Tracker 強化
- [x] ~~**[C-CLOSE]** Dashboard 平倉動作實作 (exit_price + realized_pl 紀錄)~~

### 路線 I — Invest Protocol V4.8 (API 化)
- [x] ~~**[I-PA]** dual_fetch.py 擴充至 15 scalar 欄位~~
- [x] ~~**[I-PB]** Sentiment lane：Insider 統計與 Short Interest 介接~~
- [x] ~~**[I-PC]** News lane：Analyst Ratings & Price Targets 結構化 API~~
- [x] ~~**[I-PD]** Phase 0 L3 Fallback 改用 Skill Chain~~
- [x] ~~**[I-PE]** Phase 0 Schema 明列關鍵指標，減少 Phase 2 重抓~~
- [x] ~~**[I-PF]** Phase 2 共通 prompt 導入 Web Search 白名單~~
- [x] ~~**[I-PG]** Technical lane：yfinance OHLC 換成 FMP stable API~~

---

## ✅ 已完成歷史紀錄 (Summary)

- **Dashboard 強化**：`calendar.html` 全功能實作、`page-decisions.js` 平倉邏輯。
- **Data Feeds**：FMP API 全面替代 WebFetch、Upcoming events 統一 Schema 化。
- **Tactical Radar**：1d/5d/15d 短期預測系統上線。
- **V4.6 投資協議**：雙軌 entry、STAGED 狀態、Consensus bonus。
- **Sector Protocol V1.2**：主子檔拆分、三層訊號合成、決策樹。
- **Server 與 Infrastructure**：dashboard_server.py CRUD、自動 mtime cache-busting。

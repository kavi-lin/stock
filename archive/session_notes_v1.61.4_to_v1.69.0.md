# Session Notes 歸檔 v1.61.4 → v1.69.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v1.69.0) — Sector V1.4: FMP estructured layer (P1-P4)

### 改動
依 `~/.claude/plans/sector-protocol-fmp-precious-cake.md` 落地 P1-P4(Plan 在 FMP MCP 401 卡關後恢復;此 session 完成全部實作):

**新增 fetch scripts(全走 FMP HTTP REST + `$FMP_API_KEY`,hard-fail)**:
- `sector/scripts/fetch_sector_valuation.py`(~210 行)— P1:11 sector × NASDAQ+NYSE PE TTM,1y daily PE z-score(雙 exchange 平均),sector ETF 3M return - SPY 3M(用 chart light EOD,因 batch-quote 402),20d ETF volume ratio
- `sector/scripts/fetch_earnings_pulse.py`(~160 行)— P2:131 mega-cap 30d earnings beat/miss/in-line + clipped surprise%(±100% cap 防 INTC 0.019 estimate 拉爆 avg);analyst_revision_net 延後到 P2.5
- `sector/scripts/fetch_smart_money.py`(~190 行)— P3:per-symbol insider acquired/disposed quarterly ratio + senate-latest 30d window aggregated by sector;form13f_top10_delta 延後到 P3.5(industry-summary 402)
- `sector/scripts/fetch_sector_news.py`(~120 行)— P4:per-sector top-5 mega-cap × `news/stock` 結構化 headline,取代 WebSearch ≤5 → ≤2

**Validator + schema V1.4 hard-fail gates**:
- `_phase1.sectors[].sector_valuation`(pe_ttm / pe_zscore_1y / rs_vs_spy_3m / etf_volume_ratio_20d)
- `_phase3.sector_earnings_pulse`(report_count / beat_rate_30d / surprise_score_avg)
- `_phase3.smart_money_signals`(insider_acquired_disposed_ratio_q / senate_net_buy_30d)
- `sectors[].score_components.valuation_penalty`(deterministic ±10/+5 overlay)

**Protocol 文件**:
- `sector_protocol_main.md` V1.3 → V1.4,加 Step 5b Valuation Penalty Overlay
- `phase_1-2-3.md` Phase 1 加 Step 2 sector valuation;Phase 3 加 Step 3b/3c/3d (earnings pulse / smart money / news cache);WebSearch ≤5 → ≤2
- `phase_4-5.md` Phase 4b Devil's Advocate 加規則 5 — smart money divergence 強制檢查
- `render_sector_report.py` 加 Sector Valuation Snapshot 節(自動標 🔴 OVERBOUGHT / 🟢 OVERSOLD VALUE)

**FMP MCP 探測結果**(blocker 已修;此 session 開頭):
- ✅ `marketPerformance/sector-PE-snapshot`、`historical-sector-pe`、`sector-performance-snapshot`、`chart/historical-price-eod-light`、`quote/quote`(single)、`calendar/earnings-calendar`、`insiderTrades/insider-trade-statistics`、`senate-latest`、`news/search-stock-news`
- ❌ 402 paid plan(已迴避):`quote/batch-quote`、`form13F/industry-summary`

**驗證**:V1.4 round-trip(載 2026-04-29 真實 cache 補強舊 log 模擬 V1.4)→ validator rc=0 + render rc=0(8.2KB md,Healthcare 自動 🟢 OVERSOLD VALUE)

### 已知限制
- `analyst_revision_net`(P2)、`form13f_top10_delta`(P3)目前都 null,需 paid plan/額外 cache layer
- mega-cap universe (~131 ticker)是手動硬編碼的;sector 變動或新 IPO 需手動加
- Phase 1 sector valuation 一次跑要 ~36 calls;FMP free tier 250/day 仍可承受 daily 但需注意 rate limit

### 接續工作(若想做)
1. 把 4 支 fetch script 加入 `daily_update.sh` 使早晨自動 prefetch cache
2. 寫 `backtest_valuation_overlay.py` 驗證 valuation_penalty 是否提升歷史 alpha
3. P2.5 / P3.5 paid-plan 補回 analyst_revision_net + form13f_top10_delta

## 🟢 Session Note (v1.68.0) — I-PF: Phase 2 共通 prompt 加 FORBID web search 白名單

### 改動
`investment/investment_protocol_v4_8.md` Phase 2 共通 subagent prompt 模板（行 308 後）加新區塊 `DATA SOURCE DISCIPLINE`：

**❌ FORBIDDEN（禁 web search 重抓）**：
- Quote / Valuation: price/peRatio/forwardPE/pegRatio/epsTTM/mktCap/dividendYield/priceToBookRatio
- Quality / Forward: roeTTM/debtToEquity/fcfPerShareTTM/nextEarningsDate
- Market signals: VIX/F&G/SPY RSI/breadth/FTD/market_top_score
- Insider / short: 所有 insider 數字、MSPR、short_pct_float
- Analyst: rating consensus / price target / upgrade-downgrade history
- Filings: 10-K/Q/8-K
- Company news headlines（fetch.py 已涵蓋 3 來源 deduped）
- OHLC / RSI / MACD / MA

**✅ ALLOWED ≤ 1 web search call（僅 narrative tone）**：
- Reddit/X/StockTwits sentiment narrative
- Conference call transcript / management commentary
- Supply chain rumors / 地緣政治
- 競爭格局 / market share narrative
- Product reviews

**違規處理**：subagent 引用 web search 數字而非結構化 source → PM 在 Phase 2.5 自動扣 confidence 0.2；連續 3 次該 lane degraded。

## 🟢 Session Note (v1.67.0) — I-PE: Phase 0 schema 加 `_market_signals` + Phase 2 共通 prompt 直接 inline pass

### 改動
- `investment/investment_protocol_v4_8.md` Phase 0 JSON schema 新增 `_market_signals` block：
  - `fear_greed_index` / `vix_current` / `vix_regime` / `spy_rsi_14` / `spy_pct_above_ma200`
  - `breadth_composite` / `ftd_status` / `ftd_days_since` / `market_top_score`
  - `top_catalysts[]`（從 sector_intel 注入）
- Phase 2 共通 prompt 段落更新：`PHASE 0 MACRO CONTEXT` 區塊 inline paste 包含 `_market_signals`
- Sentiment lane rubric 改寫：**「優先讀 Phase 0 `_market_signals`」**；只有缺欄位時才跑 sentiment.py 抓市場層
- News lane rubric 改寫：**「優先檢查 Phase 0 `_market_signals.top_catalysts[]`」**；只有沒涵蓋或需 24h 內最新才跑 fetch.py

### 效益
- Sentiment lane 多 ticker 連續跑：第 2 個 ticker 開始市場層直接 inline 不用 yfinance call（~省 1.5 min/ticker）
- News lane 多 ticker 連續跑：top_catalysts 已 cover 的 ticker 可直接引用（fetch.py call 變可選）
- Phase 2 共通 prompt 多了 ~200 tokens 的 _market_signals JSON 但省下 4 lane 各自 fetch 的 LLM token 跟時間

## 🟢 Session Note (v1.66.0) — I-PD: Phase 0 L3 fallback 從 web search 改 skill chain

### 改動
`investment/investment_protocol_v4_8.md` Phase 0 三層 cache L3 重寫：
- **舊** (v4.8)：「皆 STALE 或缺失 → 執行 market-news-analyst skill（或 web search），寫入 phase0.json」 — 模糊，容易 fallback web search
- **新** (v4.9 / I-PD)：「皆 STALE 或缺失 → 跑 4 個 skill chain」：
  ```bash
  python3 skills/market-sentiment-analyzer/scripts/sentiment.py
  python3 skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py
  python3 sector/ftd_yfinance.py
  python3 sector/market_top_yfinance.py
  ```
  合成 4 個 skill 輸出 + L4 fred-macro → `phase0.json` (`phase0_source: SKILL_CHAIN`)。
- LLM web search 只留給 `key_themes` / `bullish_signals` / `bearish_signals` 敘事面（VIX/F&G/breadth/FTD/market-top 數字一律 API）。
- ≥ 2 個 skill 失敗才退回 web search，標 `phase0_source: WEB_SEARCH_FALLBACK`

### 效益
- 同 ticker 兩次跑得到 deterministic 數字（VIX 18.72 不變）
- 省 LLM token（web search 一次 ~5K tokens）
- 跨 session 可重現（regression test 友善）

## 🟢 Session Note (v1.65.0) — I-PC: News lane 加 FMP analyst grades / price-target / Finnhub company-news

### 改動
- `skills/market-news-analyst/scripts/fetch.py` 加 5 個 FMP `/stable/*` endpoints + 1 個 Finnhub:
  - **FMP `/stable/grades-historical`** → `analyst_actions[]` 過去 30d upgrade/downgrade（含 action/firm/newGrade/previousGrade/url）
  - **FMP `/stable/grades-consensus`** → `analyst_consensus` 當前 strong_buy/buy/hold/sell/strong_sell 分布
  - **FMP `/stable/price-target-consensus` + `/price-target-summary`** → `price_target` 高/低/median/consensus + 月/季/年 trend
  - **FMP `/stable/grades-news`** → `analyst_news[]` 評等變動相關新聞
  - **FMP `/stable/sec-filings-financials`** → `sec_filings_recent[]`（取代壞掉的 `/api/v3/sec_filings` Legacy 403）
  - **Finnhub `/company-news`** → 補進 headlines pool（含 category + sentiment 欄位）
- `analyst_actions` 來源策略：FMP grades-historical（主）→ finvizfinance（fallback 當 FMP 空）
- `data_quality` block 加 `fmp_calls` / `fmp_failures` / `finnhub_news_count` / `fmp_grades_count` 等診斷欄位
- `investment/investment_protocol_v4_8.md` Phase 2 News rubric 改寫：列出新增的 4 個結構化 fields，subagent 必須優先用、禁止 web search 重抓 analyst rating 數字

### Smoke test (NVDA, 168h)
```
headlines: 129 (finviz 100 + yfinance 10 + Finnhub 25, deduped)
analyst_actions: 1 (source=fmp_grades_historical)
consensus: {strong_buy:2, buy:58, hold:16, sell:3, strong_sell:0, consensus:"Buy"}
price_target: {high:400, low:140, consensus:279.96, median:275, last_quarter_count:11 avg=290.27}
fmp_calls: 6, fmp_failures: 0
```

### 替代了什麼
- finvizfinance scraping（脆弱、layout 改 break）→ FMP `/grades-historical` 結構化
- LLM 從新聞文字「猜」price target → FMP `/price-target-consensus` 數字
- analyst rating 從 web search 推論 → FMP `/grades-consensus` 結構化分布
- Legacy FMP `/api/v3/sec_filings` 403 → `/stable/sec-filings-financials`

## 🟢 Session Note (v1.64.0) — I-PB: Sentiment lane 個股層 web search → 結構化 API

### 改動
- `skills/market-sentiment-analyzer/scripts/sentiment.py` 加 `--ticker X` 參數：
  - FMP `/stable/insider-trading/statistics` → 最近 4 季 acquired/disposed 統計（`acquired_disposed_ratio` 是按 transaction 個數的比，非股數）
  - Finnhub `/stock/insider-sentiment` → 最近 6 個月每月 MSPR（小型股可能 sparse → null acceptable）
  - yfinance `info.shortPercentOfFloat` → short interest fallback（FINRA bi-monthly snapshot）
- 輸出 JSON 加 `ticker_signals` block：`insider_stats[]` / `insider_sentiment.latest_mspr` / `short_pct_float`
- 市場層仍維持 15 min cache；個股層 per-ticker fresh
- `investment/investment_protocol_v4_8.md` Phase 2 Sentiment rubric 改寫：
  - 一個指令 `sentiment.py --ticker X` 同時拿市場層 + 個股層
  - **禁止 web search Reddit/X/insider/short 數字**；只能保留 ≤ 1 次 Reddit/X narrative tone search
  - 融合公式從 `0.4×stock + 0.6×market` 改成 `0.5×stock + 0.5×market`（個股層權重提高，因為訊號變結構化更可信）
  - 個股 stock_specific 打分規則明列（insider ratio / MSPR / short %）

### Smoke test (NVDA)
```
ticker_signals.insider_stats Q1/2026: ratio=0.163, acq=60M, dis=31M shares, 15 acq tx vs 92 dis tx → 顯著賣壓
ticker_signals.insider_sentiment.latest_mspr: None (NVDA 該月無 insider transaction)
ticker_signals.short_pct_float: 1.22% (yfinance / FINRA bi-monthly)
```

### 替代了什麼 web search
- 「web search Reddit/X」→ 仍允許 narrative tone（無 API 等價）
- 「web search short interest」→ FMP/Finnhub 都沒 free tier endpoint，yfinance 是合理 fallback
- 「web search insider activity」→ FMP `/insider-trading/statistics` 結構化、可比較

## 🟢 Session Note (v1.63.0) — I-PG: Technical lane OHLC FMP-primary

### 改動
- `skills/momentum-monitor/scripts/technical_core.py` `fetch_history()` 改成 FMP-primary：
  - 加 `_fetch_fmp_ohlc(ticker, period)` 用 FMP `/stable/historical-price-eod/full`，回 yfinance schema 的 DataFrame（OHLCV 大寫欄位、DatetimeIndex 升序）
  - `fetch_history()` 邏輯：先嘗試 FMP（FMP_API_KEY 設定 + 200 OK + 非空），失敗才 fallback yfinance
  - 仍回 `(hist, yf.Ticker)` tuple — yf.Ticker handle lazy 不打 API，給 momentum.py `_short_interest_block(t.info)` 用
- 同時影響 `technical-analyst` 跟 `momentum-monitor` 兩個 skill（都共用 technical_core）

### 跨 provider 差異
- FMP `/historical-price-eod/full` 是 split-adjusted（不含 dividend adjust），yfinance auto_adjust=True 是 dividend-adjusted
- 對 RSI/MA/MACD pattern recognition 影響 < 1-2%（累積股息），不影響技術訊號
- 配息股（KO/JNJ/PG）MA 數值會比 yfinance 略高，acceptable

### Smoke test
```
NVDA 1y → 254 rows OHLCV
technical-analyst: price=208.94, MA stage=Stage 2 uptrend, RSI=65 bullish, MACD hist=1.784
momentum-monitor: composite=58.8, signals=[stage2_uptrend_intact, low_short_interest, fresh_golden_cross_20_50]
```

### 效益
- yfinance scraping fragility 解決（Yahoo 偶爾擋 IP / schema 變動）
- FMP `/historical-price-eod/full` 多含 `vwap` / `change` / `changePercent`（目前未用，可未來擴展）
- Starter rate limit 充裕（300/min vs yfinance IP-based）

## 🟢 Session Note (v1.62.0) — I-PA: dual_fetch 9 → 15 scalar (Invest Protocol Refactor 第 1 步)

### 改動
- `skills/finnhub-client/scripts/dual_fetch.py`：CANONICAL_FIELDS 從 9 → 15，新增 6 個欄位 (`forwardPE`, `pegRatio`, `roeTTM`, `debtToEquity`, `fcfPerShareTTM`, `nextEarningsDate`)
- Finnhub side：從現有 `/stock/metric` 抽 `forwardPE` / `pegTTM` / `roeTTM` / `totalDebt/totalEquityAnnual`；fcfPerShare 從 `pfcfShareTTM` 推導 (price / pfcfShareTTM)；nextEarningsDate 走 `/calendar/earnings`（多 1 個 API call）
- FMP side：擴充 `/stable/ratios-ttm` 取 `debtToEquityRatioTTM` / `freeCashFlowPerShareTTM` / `forwardPriceToEarningsGrowthRatioTTM`（forward PEG）；nextEarningsDate 走 `/stable/earnings-calendar` filter
- `compute_diff` 加 DATE_FIELDS 集合，date 欄位用 match/mismatch boolean 不算 %
- `investment/investment_protocol_v4_8.md` Phase 2 Fundamentals lane TICKER_DATA_BUNDLE 規則：列 15 個 scalar、加 6 個新欄位的估值打分規則（forwardPE / pegRatio / roeTTM / debtToEquity / fcfPerShareTTM / nextEarningsDate 用法）

### 跨 provider 預期 diff
NVDA smoke test：
- price/previousClose/dayHigh/dayLow：< 0.25%（intraday tick noise）
- 大多估值欄位：< 4%
- **pegRatio**：85% diff（Finnhub trailing PEG 0.66 vs FMP forward PEG 1.22 — 不同方法論）
- **debtToEquity**：35% diff（Finnhub annual 0.054 vs FMP TTM 0.073 — 不同 time frame）
- pegRatio + debtToEquity 的 audit diff **預期會大**，是 expected behavior，不是 bug

### Smoke test
```
python3 skills/finnhub-client/scripts/dual_fetch.py --tickers NVDA --output-dir /tmp/dual_test
→ scoring 含全部 15 scalar；_audit.fmp 含對應 audit 值；_audit.diff 12 個 %（3 個 fields FMP 沒提供）
```

### Phase 2 Fundamentals lane 預期效益
- us-stock-analysis 改成「讀 bundle 不重抓」 → 省 ~2-3 次 API call
- 新增 forwardPE / fcfPerShareTTM 直接給 subagent 估值打分用，省一次 yfinance / FMP fetch
- nextEarningsDate ≤ 7 天觸發 conviction 自動降權，避免 earnings whipsaw

### Note：FMP API key rotation
User 升 Starter plan 後 FMP rotate 了 API key。`.zshrc` 已更新新 key (SyJJzDfG...)。所有後續 Bash 開頭 `source ~/.zshrc` 才會抓到新值。

## 🟢 Session Note (v1.61.5) — 修嚴重 bug：cancel 後整條 queue 卡死

### 災情
User triage 跑卡了，按 Cancel 後 status=cancelled。但後面 enqueue 的 invest (MRVL, CRWV) 永遠不開始跑。

### 根因
`cancel_protocol()` 只設 `status="cancelled"`，**沒設 `ended_at`**。依賴 `_run` thread 的 post-wait block 設 ended_at，但這次該 thread 沒走到（可能 reader thread / lf.close 卡住、或 SIGTERM 被 claude CLI 吞掉）。

Worker dispatch 後等待回收的 loop：
```python
if s != "running" and ended:   # ← ended is None → 條件 False → 死循環
    break
```

### 修
1. **`cancel_protocol()`**：cancel 時立即設 `ended_at` + `elapsed_sec`，不再依賴 _run thread post-wait
2. **Recovery path**：如果第二次 cancel 看到「status=cancelled 但 ended_at=None」（previously cancelled but stuck），主動補設 ended_at + 清 `_protocol_proc["p"]` 給 caller
3. **Worker wait loop**：放寬條件為 `s in ("done","error","cancelled","idle")`，不再檢 ended_at（防禦縱深）

### 用戶需要
- **重啟** dashboard_server.py 才會載入新邏輯
- 重啟後 queue 會空（in-memory），MRVL + CRWV 要從 Quick Launch / decisions 重新點分析

## 🟢 Session Note (v1.61.4) — Triage 燈號 tooltip 修：native title 太小看不到 → 改 CSS group-hover

### 問題
v1.61.3 用 native HTML `title` attribute 寫 tooltip，但 dot 只有 10px (w-2.5 h-2.5) 在 macOS Safari 上 hover 不太可靠/根本不顯示。

### 修
- 把 dot 跟「3h」age string 包進同一個 `relative group inline-flex` 容器擴大 hover 命中範圍
- tooltip 改 CSS-only：absolute hidden `group-hover:block`，用 `whitespace-pre-line` 處理多行
- 加 `cursor-help` 視覺暗示
- 移除舊 `title` attribute（雙重設置反而干擾）

### 結果視覺
```
🗂 Stage 1 RSS Triage    30 則    ● 3h    [↻ 更新 RSS 源]
                                  ↑ hover 此區塊跳 320px 寬 tooltip
```

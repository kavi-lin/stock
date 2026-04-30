# INTEL COMMAND — Session Notes & System State

> **Last Updated**: 2026-04-30 (v1.71.3)
> **Role**: This file serves as the "Short-term Memory" and "Handoff Cache" for AI Agents. It contains market regime states, token optimization logs, and data integrity notes. **Task backlog has been moved to TODO.md; full version history to CHANGELOG.md.**



## 🟢 Session Note (v1.71.3) — Preflight popup 對齊 sidebar：sector/news 也讀內部 timestamp

### 動機
v1.71.2 修了 sector protocol 自己的 cache rule（看 generated_at）+ runPreflightQueue 切頁不斷。但 user 觀察到新矛盾：「盤前狀態檢查 popup 顯示『產業情報 ✓ 3h 前』，但 sidebar 橘燈說『產業掃描 29h 前』— 同一個檔到底新還舊？」

### 根因
Popup 跟 sidebar 讀同一個 `sector_intel.json` 但**不同欄位**：
- **Popup** (`dashboard_server.py:735` `preflight_check()`)：用 `os.path.getmtime()` → 20:34（news Phase 4 patch top_catalysts 時 touch 的）
- **Sidebar** (`Dashboard/script.js:583`)：用內部 `generated_at` → `2026-04-29 18:21`

這是 v1.71.2 漏掉的對稱修：sector protocol 自己看 generated_at 了，但 dashboard 的監控層還在看 mtime。

### 改動
**`dashboard_server.py` 加 `_content_timestamp_for(key, path)` helper**
- 對 `key in ('sector', 'news')`：讀檔內部 `generated_at` (sector) 或 `timestamp` (news digest)，parse 失敗 fallback 到 mtime
- 其他 key (breadth/ftd/market_top/rss)：仍用 mtime（這些是 yfinance/RSS script 寫的 fresh 檔，mtime 跟內容時間一致，無 false-FRESH 風險）
- 支援多種 timestamp 格式：ISO with/without tz、`YYYY-MM-DD HH:MM:SS`、`YYYY-MM-DD HH:MM`、`YYYY-MM-DD`

`preflight_check()` 把原本 `age_sec = now - mtime` 改成 `age_sec = now - _content_timestamp_for(key, path)`。

### 驗證
跑 `python3 -c "import dashboard_server; ds.preflight_check()"`：
```
sector  產業情報   STALE  age=29.2h   ← 之前是 FRESH 3h
news    新聞 DIGEST STALE age=11.1h   ← 之前是 FRESH 32min（patch 了 top_catalysts 那刻）
```
跟 sidebar 橘燈所見完全一致。

### 不在範圍
- 不改前端 `script.js:583` 的 source timestamps array（既已正確讀 generated_at）
- 不改其他 4 項 free 的 mtime 邏輯（沒有 cross-protocol patch 風險）
- 不解決「news Phase 4 為什麼要 patch sector_intel.json」這個更深的架構問題（屬下一輪 refactor）


## 🟢 Session Note (v1.71.2) — 「更新全部過期」三 bug 串連修

### 動機
User 觀察「點盤前檢查 → 更新全部過期 → news 跑了但 sector 沒跑，sidebar sync 燈一直橘」。Forensic 三個 bug 疊加：

1. **Frontend for-loop 切頁就斷**（`script.js:runPreflightQueue`）：原本 `POST /api/run-protocol` + `await waitForProtocolDone()`，news 跑 17min 期間 user 切頁/關 tab → JS Promise 死 → sector POST 從未發出。
2. **Sector prompt 缺「非互動模式」**（`dashboard_server.py:88` 原本只是裸字串「產業掃描」）：手動跑 sector 時 Claude 會主動停下「準備好進入 Phase X 嗎？」等 user reply，浪費 ~$1 / 9k tokens 只讀檔思考然後卡住。
3. **Sector cache freshness 用 mtime 誤判**（`sector_protocol_main.md` GLOBAL RULES #2）：news protocol Phase 4 patch `top_catalysts` 進 `sector_intel.json` 會 touch mtime 但不動 `generated_at` → sector cache rule 看 mtime < 3h 誤判 FRESH → 跳過 Phase 0-1 → 但內部 `generated_at` 還是昨天。

證據：sector_20260430_210533.log 開頭 Claude 自己點出矛盾「mtime 32min 前 FRESH，但 generated_at 2026-04-29 18:21」然後就停下問了。

### 改動

**1. `Dashboard/script.js:972-1017` `runPreflightQueue` 改 server-side queue**
- 從「for loop POST `/api/run-protocol` + await waitForProtocolDone」改成「全部一口氣 POST `/api/protocol-queue`，server FIFO 自己序列跑」
- Frontend 只負責提交，不需要等。切頁/關 tab/重整都不影響 — server 持續跑
- 一次 toast 報「已排入 N 個 protocol：news → sector，server 序列執行」
- 沿用既有 `pollLaunchStatus` banner 顯示進度

**2. `dashboard_server.py:88` sector prompt 加非互動模式 + cache 衝突自動處理**
```
非互動模式：依 sector_protocol_main.md GLOBAL RULES 直接執行 Phase 0→5 完整流程，
不要輸出「準備好進入 Phase X 嗎？」「請確認」這類停頓等候，一個 turn 完整收尾。
Cache 衝突自動處理：若 sector_intel.json 的 mtime 看起來新但內部 `generated_at` 距今 ≥ 3 小時
（通常是 news protocol Phase 4 patch top_catalysts 造成的 mtime touch），
視為 STALE 必須重跑 Phase 0–1，不要當成 FRESH 跳過。
```

**3. `sector/sector_protocol_main.md` GLOBAL RULES #2 重寫 cache freshness rule**
- 從「FRESH = mtime < 3h」改成「FRESH = `generated_at` 距今 < 3h」
- 明確說「以內部 `generated_at` 為準，不看 mtime」
- 加註 false-FRESH 來源（news Phase 4 patch top_catalysts）
- `generated_at` parse 失敗 → 視為 STALE

### 驗證
- `node -c script.js` + `python3 -c "import dashboard_server"` 都過
- `dashboard_server.PROTOCOL_PROMPTS["sector"]` 含「非互動模式」+「generated_at」字串
- `sector_protocol_main.md` 含 3 處 `generated_at` references（GLOBAL RULES + 兩處說明）

### 注意事項
- **要重啟 `dashboard_server.py`** prompt 改動才生效
- 既有 `runPreflightQueue` 同事流程不再需要 `waitForProtocolDone` — 但函數本身留著（其他 caller 可能還用，未動）
- News Phase 4 patch sector_intel.json 的設計沒動（屬另一個架構議題：news/sector cache 責任邊界）— 但 sector cache rule 改用 generated_at 已能避開誤判


## 🟢 Session Note (v1.71.1) — earnings 頁 UX redesign + markdown viewer 修復

### 動機
v1.71.0 落地的 earnings 頁是基本 grid card,user 反映:
1. **看報告按鈕變成下載** — `window.open('/${path}','_blank')` 開 `.md` 被 SimpleHTTPRequestHandler 預設 MIME 當下載
2. **頁面太 generic** — 缺視覺層次 / 節奏 / 特色

User 要求用 frontend-design skill 重做 UX。本 session 在 **不改資料邏輯** 前提下,重構 layout + 美學語彙 + 修 markdown render。

### 改動

**1. Markdown viewer 接線(原本卡的就是這個)**
- `Dashboard/earnings.html` 加 `<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js">` + 完整 `report-modal` markup(複用 `decisions.html:179-189` 結構)
- `Dashboard/page-earnings.js` 加 `wireReportModal()`(close button + click backdrop + ESC 關閉);看報告按鈕從 `window.open()` 改 `window.UI.viewReport(path)`
- **零 server / MIME 改動** — 純複用 `utils.js:322-344` 既有 `UI.viewReport()`(fetch md → marked.parse → 套 prose theme dark/light 自動切)

**2. UX redesign — Editorial × Financial Terminal 美學**
- `Dashboard/earnings.html` 重寫(186 → 326 行,內含 ~290 行 inline `<style>` block .ea-* 命名)
- `Dashboard/page-earnings.js` 重寫(248 → 415 行,模組化成 7 個 render 函式 + filter/animation 邏輯)
- 美學決策:
  - **Typography**: JetBrains Mono 加重(score 用 64px 900 weight, ticker 24px 800),Inter 維持 body 字
  - **配色**:不引新色,強化 5 verdict 漸層 stripe + glow(STRONG 帶 inner-glow shadow)
  - **背景**:subtle dotted grid pattern(18px / 6% opacity),邊緣 fade
  - **動效**:cards stagger reveal(60ms 間隔),hero stats 計數 0→真值動畫(480ms),score 數字用 IntersectionObserver 進入視窗才 count up(避免初始 jank)

**3. 新元素**
- **Hero Stat Strip**(4 tile):Total / Avg score / STRONG count / Risk Watch count,各帶 verdict-color accent strip,進場有計數動畫
- **Command Bar**:`›` prompt 字符 + JetBrains Mono 大字 input + recent ticker chips(localStorage 記 5 個);placeholder 每 3.5s 輪播 NVDA/AAPL/MSFT/AVGO/META
- **Filter Chip Bar** 取代 3 個 select:
  - Sort:segmented control(Score↓/↑/Recent/A→Z)
  - Verdict:5 個 toggle chip 各帶 verdict 色,active 反白
  - Flags:`✅ Clean` / `⚠️ Has Flags` 互斥 chip
  - Reset 按鈕 + 即時 match count(`12 / 24` 風格)
- **Asymmetric Card** layout(左 145px score column + 右 data column):
  - 左:64px JetBrains Mono 900 score 數字、verdict pill、4px 漸層 stripe(STRONG/WEAK 加 glow)
  - 右上:ticker(24px)+ company truncate + sector/industry/date pills
  - 右中:**8Q gross margin sparkline**(SVG inline polyline + fill + delta label),trend up/down 自動染色
  - 右下:4 個 component horizontal mini bar(Quality/Growth/Valuation/Analyst,各 max bar 寬一致),verdict-tinted gradient fill
  - 底部:freshness dot(綠<14d / 黃<45d / 紅≥45d)+ 看報告 / 重跑 buttons
- **Empty State**:大 icon + title + 3 個 sample ticker quick-start chip
- **Filter persistence**:sort / verdicts / flags 寫 localStorage,reload 還原

**4. bridge.py 擴 schema(支援 sparkline)**
- `extract_earnings_analyses()` 加 `margins_8q` 欄位(每 ticker 8 個 {date, gross} 點)— 16 floats × N tickers 額外體積可忽略
- 既有結構 100% 向下相容(只是多一個欄位)

**5. utils.js**
- 唯一改動:VERSION 1.71.0 → 1.71.1

### 不影響範圍
- `dashboard_server.py` 完全不動(no MIME 設定,no 新 endpoint)
- `utils.js`:`UI.viewReport()` 不改,直接重用
- 其他頁面零變動
- earnings-analyst skill 本身(scripts/, schema)不動

### 驗證
- `bridge.py` rc=0,`data.earnings_analyses[]` 含 margins_8q(NVDA/MSFT/AAPL 各 8 點)
- `node -c page-earnings.js` syntax OK
- 手動瀏覽 earnings.html:
  - hero stats 計數動畫 ✓
  - command bar `>` prefix + placeholder 輪播 ✓
  - filter chips 點擊切 verdict / flags 即時更新 + match count 同步 ✓
  - reset 還原 + localStorage 持久化 ✓
  - card stagger reveal + sparkline + component bars + verdict glow ✓
  - 點 📄 看報告 → modal 開 markdown(prose theme dark/light 跟主題切換)+ ESC/close 關閉 ✓
  - empty state(濾掉所有結果)→ 友善 quick-start ✓
  - dark / light 切換無破口 ✓

### 重啟需求
- **必須重啟 dashboard_server** 因為 PROTOCOL_PROMPTS earnings 條目在 v1.71.0 加,還沒 reload(若還沒重啟過)
- 已自動跑 `bridge.py`,data.json 含新 schema,重新整理頁面即看到 sparkline


## 🟢 Session Note (v1.71.0) — earnings-analyst 全面整合(calendar UI + 獨立頁 + 投資協議 Tier 2)

### 動機
v1.70.0 已落地 `skills/earnings-analyst` 但屬孤立 skill(只能 CLI 跑)。User 要求:(1) calendar 點財報事件 → 一鍵觸發;(2) 想清楚怎麼跟其他 protocol 整合。本 session 補完整合三層 — UI 觸發 + 獨立 Dashboard 頁 + investment_protocol Phase 2 機會式讀取。

### 改動

**1. Backend(`dashboard_server.py`)**
- `PROTOCOL_PROMPTS["earnings"]` 新增,prompt 強制 fetch+analyze+validate+render 4 步驟非互動執行
- `PROTOCOL_LOG_DIRS["earnings"]` = `skills/earnings-analyst/cache`
- `enqueue_protocol()` 加 earnings ticker dedup(running/queued 同 ticker 拒絕)
- `_label_for()` 加 `📊 Earnings <ticker>` queue label
- 新 GET 端點 `/api/earnings-cache/:ticker` — 回 cache 狀態(cached / composite_score / verdict / quality_flags / report_path / cache_age_days)

**2. Calendar UI(`Dashboard/page-calendar.js` + `style.css`)**
- 載 `data.earnings_analyses[]` 進 `earningsCacheMap` 供 inline 查詢
- `renderUpcomingCard()`:earnings event 自動加 action row
  - **已 cache**:`<verdict 顏色 chip> <📄 看報告 button> <🔄 重新分析 button>`
  - **無 cache**:`<📊 跑財報分析 button>`
- 點按 → `window.runEarningsAnalysis(ticker)` POST `/api/protocol-queue {name:"earnings",ticker}`
- 加 6 個 CSS class:`cal-earnings-action-row` / `cal-earnings-btn` / `cal-earnings-btn-run` / `cal-earnings-btn-refresh` / `cal-earnings-cached-badge`

**3. Bridge 索引(`bridge.py`)**
- 新 `extract_earnings_analyses()`:scan `skills/earnings-analyst/cache/*.json`,過濾 90d TTL + composite_score 已寫入,emit thin summary list(ticker / verdict / score / flags / score_components / report_path / company_name / sector / industry / price)
- `data["earnings_analyses"]` 寫入 data.json(daily bridge.py 跑時自動 refresh)

**4. Dashboard 獨立頁(`Dashboard/earnings.html` + `page-earnings.js`)**
- nav 加新 entry `📊 財報分析`(`utils.js` NAV_ITEMS;`i18n.js` zh/en 兩處 nav 字典)
- 主頁 layout:trigger 輸入框(任意 ticker)+ 排序/filter 列(score/date/ticker × verdict × flags clean)+ 卡片格(每個 cached ticker 一張卡)
- 卡片內容:ticker / company / sector / industry / score / verdict / quality_flags / 4 個 score components / last+next earnings date / 看報告/重新分析/cache age 工具列

**5. Investment Protocol Phase 2 整合(`investment/investment_protocol_v4_8.md`)**
- Phase 1 加新 sub-section「Phase 1 資料層(V1.71)— Earnings-Analyst Cache 機會式讀取」:PM 檢查 cache 是否存在 + 90d 新鮮度 → 抽 thin EARNINGS_ANALYST_BUNDLE(margins_8q / yoy_growth / balance_health / cash_flow_quality / valuation / quality_flags)
- Phase 2 共通 prompt 模板加 `EARNINGS-ANALYST BUNDLE` 段(僅 Fundamentals lane,其他 3 lane 不含)
- Fundamentals subagent rubric 加「EARNINGS_ANALYST_BUNDLE 使用規則」:
  - 引用 8Q margin trend 等深層證據
  - quality_flags 觸發 ±1 分強訊號(accruals/negative_fcf/capex_outpaces 至少 -1;乾淨 + composite ≥ 80 至少 +1)
  - DCF intrinsic 與 dual-fetch peRatio 互相校驗
  - **絕對禁止**直接 mirror composite_score 為 lane score

**整合資料流**:
```
calendar 點按 / earnings 頁點按 → POST /api/protocol-queue
   ↓
queue worker 跑 PROTOCOL_PROMPTS["earnings"] = "財報 {ticker}"
   ↓
Claude Code → fetch+analyze+validate+render 4 步驟
   ↓
skills/earnings-analyst/cache/<T>_<DATE>.json + reports/<DATE>_<T>_earnings.md
   ↓ (next bridge.py run)
data.earnings_analyses[] → Dashboard 全面可見
   ↓ (next 分析 [TICKER])
investment Phase 1 PM 抽 thin bundle → Phase 2 Fundamentals 深層證據
```

### 驗證
- `bridge.extract_earnings_analyses()` rc=0 → 3 entries(NVDA STRONG / MSFT SOLID + accruals_warning / AAPL SOLID)
- `/api/earnings-cache/<ticker>` 4 ticker 測試:NVDA/MSFT/AAPL 全 cached + report_path 正確,ZZZZ 回 cached:false
- 6 個 JS 檔 syntax check 全 OK
- dashboard_server / bridge import OK

### 重啟需求
- **必須 restart `dashboard_server.py`** 新 PROTOCOL_PROMPTS["earnings"] / GET endpoint / dedup 邏輯才生效
- bridge.py 需重跑一次 → data.json 出 `earnings_analyses[]` 後 Dashboard 才看得到 inline cached chip / earnings.html 才有資料

### 已知限制
- bridge index 僅在 daily `bridge.py` 跑時 refresh;若中途跑了新財報分析,需手動 `python3 bridge.py` 才會反映到 Dashboard(或寫個 watch + auto-refresh,留作後續)
- earnings.html 的「重新分析」按鈕會繞過 cache 但仍走 queue;若 cache hit 時 fetch.py 自己會 skip 11 個 endpoint,所以重複按其實只跑 1 個 income-statement check + analyze + render(快)
- Phase 2 Fundamentals lane 引用 EARNINGS_ANALYST_BUNDLE 的成本是 +500-800 tokens 給 subagent prompt,但僅當 cache 命中(< 90d)時觸發

### 不影響範圍
- 其他 3 個 Phase 2 lane(Sentiment / News / Technical)prompt 不變
- daily protocol 不會自動 enqueue earnings 分析(必須 user 主動觸發 via UI 或 CLI)
- sector / news / triage protocol 不變


## 🟢 Session Note (v1.70.0) — 新 skill: earnings-analyst(`財報 [TICKER]`)+ Skills FMP 遷移盤點

### 動機
User 想要兩件事:(1) 盤點 21 個 skill 哪些值得從 yfinance 遷到 FMP;(2) 補上「個股財報深度分析」(目前 `分析 [TICKER]` 是「監控層級」非「財報層級」,缺逐季三表趨勢、品質 flag、cash flow quality)。

User 點出關鍵 cache 觀察:**財報是季度事件,daily 跑 `分析 [TICKER]` 不應重抓三表**。

### 改動

**1. 新 skill `skills/earnings-analyst/`**(`財報 [TICKER]` 觸發):
- `scripts/fetch.py`(~210 行)— 12 個 FMP HTTP REST 端點 orchestrator,cache key `(TICKER, last_earnings_date)`,TTL 90d 上限。Step 0 先用便宜 income-statement?limit=1 查 last_earnings_date,若 cache 已有同 date 檔且 < 90d → skip 11 個 endpoint
- `scripts/analyze.py`(~270 行)— derive margins_8q / yoy_growth(含加速度) / balance_health / cf_quality;6 個 deterministic quality_flag(accruals/capex outpace/margin compress/DSO slow/negative FCF/debt buildup);composite 0-100(Quality 30 / Growth 30 / Valuation 25 / Analyst 15)
- `scripts/render.py`(~280 行)— 10-section Markdown report → `reports/<DATE>_<TICKER>_earnings.md`
- `scripts/validate.py`(~115 行)— V1.0 schema gate
- `SKILL.md` + `schema.md` 文件化

**2. 觸發整合**:
- `CLAUDE.md` Protocol Triggers 加 `財報 [TICKER]` 列
- `skills/MARKET_INDEX.md` 加新 skill 進 single-ticker 區

**3. FMP 端點探測結果**(關鍵 ✅/❌):
- ✅ /stable/profile / income-statement / balance-sheet-statement / cash-flow-statement(period=quarter limit=8)
- ✅ /stable/key-metrics-ttm / ratios-ttm / financial-growth(period=annual)/ enterprise-values
- ✅ /stable/discounted-cash-flow / price-target-consensus / ratings-snapshot / grades-historical
- ❌ /stable/key-metrics?period=quarter(402 paid;TTM 替代)
- ❌ /stable/analyst-estimates?period=quarter(402 paid;earnings-valuation-forecaster 自算 forward EPS 替代)
- ❌ earningsTranscript / ESG(402 paid;graceful skip)
- ❌ /api/v3/key-metrics, /api/v3/ratios(legacy 端點,2025-08 後不可用)

**4. Skills FMP 遷移盤點**(本 session 只交付盤點,不改 code)

| 排序 | Skill | 預期效益 | 難度 |
|---|---|---|---|
| 1 | momentum-monitor | yfinance OHLC → FMP chart;加 earnings surprise + insider 信號 | 中 |
| 2 | us-stock-analysis | yfinance TTM 概要 → FMP 三表 quarterly 細節 | 中 |
| 3 | ftd-detector | yfinance OHLC → FMP chart EOD,精度與 sector cache 一致 | 低 |

不建議遷移:fred-macro(FRED 是官方源)/ market-breadth-analyzer / sector-analyst(TraderMonty CSV 優於 API)/ tail-risk-analyzer / portfolio-risk-manager(純計算)/ market-news-analyst(web native)/ technical-analyst(chart-native)。

### 驗證
3 個 ticker end-to-end 跑通:
- **NVDA** Q4 FY26: 86/100 STRONG, clean flags(rev +73% YoY accelerating, 75% GM, $51B net cash, FCF margin 51%)
- **AAPL** Q1 FY26 (2025-12-27): 77/100 SOLID, clean flags(Q30/G27/V7/A13)
- **MSFT** Q1 FY26 (2026-03-31): 71/100 SOLID, **accruals_warning flag fired**(說明 deterministic 邏輯有效)

cache hit/miss 測試 OK:首次 12 calls 寫 cache,重跑 1 call(income-statement?limit=1)→ skip。`--force` 繞過 cache。

### 已知限制
- forward EPS 估計需另外呼叫 `earnings-valuation-forecaster`(此 skill 不自動接)
- per-Q 細部 metrics(GAAP-NonGAAP reconciliation、segment revenue)需 paid plan
- mega-cap universe 不限定,任何有 FMP 三表的 ticker 都可跑
- DSO 計算用簡化(receivables/revenue × 91d)

### 不影響範圍
- 不改 `分析 [TICKER]` Phase 2 流程 — earnings-analyst 是獨立深度層,不自動掛 daily protocol(避免 token 浪費)
- 不寫 `data.json` / 不影響 Dashboard
- 3 個 yfinance→FMP 遷移候選(momentum-monitor / us-stock-analysis / ftd-detector)留作後續獨立 PR


## 🟢 Session Note (v1.70.0 補2) — Triage UI: dot 對齊 feed freshness + tooltip 改 fixed/z9999

### 動機
v1.70.0 補1 加了多源整合後，user 看到「dot 顯示 12m 前更新，但下面 feed 都是 16h 前」— 矛盾感非常強。原因：dot 讀的是 **raw.json mtime**（剛 fetch_all_news 抓完所以 12m），但 feed 是 **shallow_news[]**（昨晚 triage.json 結果，published 都是 16h 前）。raw 抓完後 user 還沒重跑 triage，UI 給的訊號就騙人。

另外 tooltip 用 `position:absolute` + Tailwind `hidden group-hover:block` 被 glass-card 的 stacking context 截斷，蓋不住下方 cards。

### 改動（`Dashboard/page-news.js`）

**1. Dot freshness 改讀 feed 自身**
- 原本：`/api/preflight` → raw.json mtime
- 現在：`max(items.published)` from shallow_news — 永遠跟 feed top 第一則一致
- 4-tier 顏色保持但門檻調整：<1h 🟢 / <3h 🟡 / <6h 🟠 / ≥6h 🔴

**2. 新增 stale-cache warning**
- Raw.json 比 feed 新 ≥30min → dot 旁加黃色 ⚠ 圖示
- Tooltip 內加完整警語：「新聞源已更新（X 前），但下面 feed 是上次 triage 結果（Y 前）— 點「更新新聞源」重跑 Stage 1 才會反映新內容」
- 解決「raw 抓了但 triage 還沒重跑」的隱形矛盾

**3. Tooltip 改用 utils.js canonical pattern**
- 從 `position:absolute` + `hidden group-hover:block`（被 glass-card stacking 截斷）
- 改成 `position:fixed; z-index:9999` + JS 動態 `getBoundingClientRect()` 定位（仿 `applySyncLight()`）
- 共用 `#_news_tooltip` element，hover dot 觸發 inject HTML
- 邏輯：preferred top below dot；若會超出 viewport bottom 則翻到 dot 上方
- 與 sidebar sync dot tooltip 視覺一致（同樣 #18181b 底 + #3f3f46 邊框 + 10px font）

### 驗證
- `node -c page-news.js` syntax OK
- 當前 shallow_news：feed top = 0.5h ago（Caterpillar），oldest = 19.3h ago → dot 會顯示「30m ago」+ stale-cache ⚠（因為 raw.json 剛被 fetch_all_news 更新，但 triage 沒重跑）
- 重整 page → tooltip 浮在 dot 下方、不被 cards 蓋

### 設計取捨
- **不用 `applySyncLight()` 直接呼叫**：那個 helper 設計給「資料同步狀態」(綠/橘/黃/紅 + 4 級門檻)，與 triage 的「feed freshness + 可選 stale-cache 警告」邏輯不同。我複用它的 fixed/z9999 tooltip 模式，但內容自製
- **不顯示「最新一則 Xh 前」雙指標**：user 之前明確說過下面排序看得到了不需要。所以 dot 上的數字就是 feed 最新一則的 age


## 🟢 Session Note (v1.70.0 補1) — News Stage 1 多源整合：RSS + Finnhub + FMP + SEC EDGAR

### 動機
User 觀察：「新聞 triage 跑完，最新一則 7h 前」。8 個 RSS feed 本身的「freshness 上限」就被卡在 1-6h（CNBC / MarketWatch RSS index 推送頻率本身慢），勤抓也榨不出新東西。要破這道牆只有加新源。

### 改動
**新增 4 個 fetcher + 1 orchestrator（`news/`）**：
- `fetch_finnhub_news.py` — Finnhub `/news?category=general`（複用 `skills/finnhub-client/scripts/finnhub_client.py` 的 `_request`）。1-5 min latency
- `fetch_fmp_news.py` — FMP `/stable/news/general-latest` + `/stable/news/stock-latest`（注意 endpoint 是斜線分隔不是 hyphen，曾踩坑抓 0 筆）。5-30 min latency
- `fetch_sec_edgar.py` — SEC EDGAR 8-K Atom feed（`?action=getcurrent&type=8-K&output=atom`），需 User-Agent 帶 email（讀 `EDGAR_UA` env，否則 fallback default）。0-15 min material event
- `fetch_news_rss.py` — `FEEDS` list 加 PR Newswire（financial-services-latest）
- `fetch_all_news.py`（orchestrator）— `concurrent.futures` 平行跑 4 個 subprocess，timeout 120s，任一失敗不影響其他源；產 intermediate `*_<provider>_raw.json` 保留 audit，最後合併寫 canonical `*_raw.json`，URL fingerprint + headline tokens 雙層 dedupe，HIGH credibility 優先

**Triage prompt 改源**（`dashboard_server.py:88-94`）：
- `triage` / `news` 兩個 prompt 從 call `fetch_news_rss.py` 改成 call `fetch_all_news.py`

**UI button 改名**（`Dashboard/i18n.js` + `page-news.js`）：
- 「更新 RSS 源」→「更新新聞源」（en: Refresh RSS → Refresh News）
- Section title 加 `(RSS + Finnhub + FMP + SEC EDGAR)`
- Tooltip 提全 4 源 + dedupe 規則
- Confirm dialog 從「重抓 RSS（~30s）+ 60+ 則」改成「平行重抓 4 個源 + 100+ 則」、預估時間 5-8 → 6-10 min

**Protocol 文件更新**（`news/news_protocol_v2.md` Stage 1 段落）— 列出 4 個 fetcher 名稱 + latency + key 需求 + graceful degradation 規則

### 驗證
跑一次 `fetch_all_news.py --hours 24`：
- 4 個源全 OK，412 raw → 393 dedupe（overlap 只 5%，覆蓋互補）
- 最新 12 則 timestamps：0.9m / 4.5m / 6.2m / 6.5m × 2 / 6.8m / 6.9m / 7.4m / 8.9m / 9.4m / 9.7m / 10.9m
- 25 則 < 1h、37 則 < 3h、145 則 < 6h（之前是「最新 7h 前」）
- 393 筆全有 `news_id` + `published`，bridge.py raw_pub_map join 不需改

### 不在範圍
- UI 不加「最新一則 Xh 前」雙指標（user 說下面排序看得到了不需要）
- 沒做：Twitter/X、Cboe options flow、Bloomberg/Reuters terminal feed（成本/接入難度高）

### 注意事項
- **要重啟 `dashboard_server.py`** triage prompt 改動才生效
- 重抓時間從 ~30s（單 RSS）→ ~30-45s（4 平行）；triage shallow snap 工作量隨 raw 量翻倍（88 → 393）會拖長至 ~8-12 min；token 估從 $0.5 → $0.8
- FMP endpoint 路徑陷阱：`news/general-latest`（斜線）不是 `news-general-latest`（hyphen）— 後者靜默回 []


## 🟢 Session Note (v1.69.2) — Triage feed sort: published desc (freshest first)

User follow-up：「triage 的新聞頁面必須按照時間近到遠排序」。

### 改動
`bridge.py:1622-1628` `extract_shallow_news()` 排序由 `(|score|, date) desc` 改成 `(published, |score|) desc`：
- Primary: `published` ISO timestamp 字串字典序倒排 = 時序倒排
- Secondary: `|score|` 同 timestamp 時用衝擊度當 tie-breaker
- 沒 `published` 的（極少數舊資料）`""` 沉到最底

### 為什麼改
v1.69.1 加了 freshness pill 後 user 一眼就能看每則新舊，但 feed 順序仍按 |score| desc — 結果「分數高的舊聞」浮在「剛發生的小事」上面，違反 triage 直覺：分流第一原則就是新的先看。

### 驗證
- Top 5 published：18:07 → 18:05 → 18:03 → 18:03 → 18:02 ✓
- Bottom 3：16:00 同 timestamp，secondary 用 score 排序 ✓

---

## 🟢 Session Note (v1.69.1) — News triage freshness pill + protocol-queue KeyError fix

### 動機
跑 6 分鐘 news triage 後 UI 看不出哪些新聞是新的、哪些已在富途看過 — triage（分流）的核心就是 freshness 判斷，缺了相對時間標籤等於沒做 triage。順便修了今天觸發 triage 時 protocol-queue thread 直接炸 `KeyError: '\n  "timestamp"'` 的 bug。

### 改動
**1. `dashboard_server.py:316-323` — 修 KeyError**
- `PROTOCOL_PROMPTS["triage"]` 內含 JSON schema 範例（字面 `{...}`），原本 `.format(**params)` 把它當 placeholder 解析炸掉
- 改成 manual token replace：`prompt.replace("{" + k + "}", str(v))`，只替換 known params (`ticker` / `headline` / `risk_tolerance`)，字面大括號保留

**2. `bridge.py:54-75` — 提升 `_raw_pub_map()` 到 module 層**
- 原本只在 `extract_shallow_news()` 內部 closure；deep 路徑想用就 copy-paste
- 提到模組層共用，single source of truth

**3. `bridge.py:1438-1492` `extract_news()` — Deep verdict 也 join `published`**
- 對 digest.json verdict 走 `pub_map.get(news_id)` fallback 補 `published` 欄位
- 驗證：17 筆 deep news 16 筆有 published（1 筆 fallback 沒對應 raw.json，UI graceful fallback 到 date）

**4. `Dashboard/page-news.js` — Freshness pill 三處生效**
- L8-21：把 `relTime()` 提到 DOMContentLoaded scope（共享 helper），加 `if (!isFinite)` / `if (diff < 0) return 'now'` 邊界保護
- L778-786：刪掉 `initFutuPush()` IIFE 內重複定義（走 closure 到 outer）
- Triage card (L430+)：在 score badge 旁加「12m ago」pill，4 級顏色（<1h emerald / <6h zinc-400 / <12h zinc-500 / ≥12h zinc-600），中英隨 `UI.currentLang` 切「前/ago」
- Deep verdict card (L178+)：右上 date block 升級為「Xh ago / YYYY-MM-DD」雙行，hover 顯示完整 ISO

**5. `dashboard_server.py:87-95` — Protocol prompts 加 `published` 寫入要求**
- `news` (DIGEST)：第 8 條硬規定，「verdict 必須帶 published 欄位」
- `flash_text` (FLASH from Futu push)：verdict 欄位列表加 `published (ISO timestamp — 用 WebFetch 取得的原始發布時間)`
- `review`：覆寫 verdict 時保留 `published`，缺則從 raw.json 補
- 未來新跑的 verdict 自帶 published，bridge 不必依賴 raw.json join；舊資料 fallback 到 join

### 驗證
- `python3 bridge.py` rc=0 → `data.json` 中 `news[].published` 16/17、`shallow_news[].published` 60/60
- `node -c page-news.js` syntax OK；`python3 -c "import dashboard_server"` OK
- 前端：點 News tab → Triage 子 tab，每張 card 標題列有彩色「Xm/Xh ago」pill；點全部/已審核/待審核 deep verdict 同樣顯示

### 不在範圍（user 明確選不做）
- 按 published desc 自動排序 freshest first
- 「< 6h only」過濾 toggle / localStorage dismiss 已讀
- RSS 源檢討、加 Twitter/X / SEC EDGAR real-time / cron pre-warm RSS（速度不是這次主軸）

### 使用須知
- **要重啟 `dashboard_server.py`** prompt + KeyError 修補才生效
- 既有 digest.json（v1.69.1 之前產生的）verdict 沒寫 published，靠 bridge join raw.json 補；未來新跑的會自帶
- `relTime()` 是純前端即時計算，reload 一次相對時間就會更新

---

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


## 🟢 Session Note (v1.61.3) — Triage 燈號改成 RSS 源層級（單顆）+ 按鈕改名「更新 RSS 源」

### 修正：v1.61.2 我做錯
v1.61.2 我把 freshness dot 加到「每張 card」(per-headline) 並加 tier 計數摘要。User 真實要求是：
- **一顆**燈號（不是每張都一顆），代表 **RSS 源最後抓取時間**（不是每則新聞發布時間）
- 燈號**位置**：放在 Triage tab header 的「更新 RSS 源」按鈕**旁邊**
- Button 改名：原「跑新 Triage」/「Run new Triage」→「更新 RSS 源」/「Refresh RSS」
- Tooltip：hover 燈號或按鈕都顯示詳細

### 修
- `Dashboard/page-news.js`：
  - 撤掉 `_freshness()` per-card helper、撤掉 tier 計數摘要、撤掉每張 card 的圓點與相對時間欄
  - `renderTriageFeed()` 開頭 `await fetch('/api/preflight')` 拿 `rss` 項的 `age_sec`，4-tier 算單顆燈號 class
  - 燈號 + 按鈕都掛同一份 tooltip（文字含上次抓取時間 + 規則 + 按下按鈕的副作用說明）
- `Dashboard/i18n.js`：`triage_run_btn` 中文「更新 RSS 源」/ 英文「Refresh RSS」；`triage_no_data` 對應改字
- `Dashboard/page-news.js` 確認對話框文字也對齊：「更新 RSS 源？會重抓 RSS（~30s）+ 對 60+ 則跑 Stage 1 shallow snap」

### 行為
- Section header：`🗂 Stage 1 RSS Triage  | 30 則  ●  [更新 RSS 源]`
- 燈號顏色（4-tier）依 raw.json mtime（preflight rss item）：
  - <1h 🟢 / <3h 🟡 / <5h 🟠 / ≥5h 🔴 / missing ⚪
- Tooltip（hover 燈號 / 按鈕）：
  ```
  RSS 源上次抓取：3h 前
  狀態：偏舊 (FRESH)
  規則：<1h 🟢 / <3h 🟡 / <5h 🟠 / ≥5h 🔴
  按「更新 RSS 源」會重抓 + 跑 Stage 1 shallow snap
  ```

### 殘留
- `bridge.py` v1.61.2 加的 `published` 欄位仍保留（從 raw.json join），目前未用，留作未來可能用途；若後續確認不會用可一併移除（~10 行）


## 🟢 Session Note (v1.61.2) — Triage tab freshness 4-tier 燈號 + tooltip + tier 計數摘要

### 改動
- `bridge.py`：`extract_shallow_news()` 新增 raw.json `news_id → published` map（per-date cache），每筆 shallow 注入 `published` ISO timestamp。30/30 命中（raw.json 完整 cover）
- `dashboard_server.py`：`triage` prompt 加要求 verdict 含 `published`（從 raw.json 抄），未來 user 跑 triage protocol 也會帶
- `Dashboard/page-news.js`：
  - 新增 `_freshness(publishedIso)` 4-tier helper：<1h 🟢 / <3h 🟡 / <5h 🟠 / ≥5h 🔴；missing → ⚪ 灰
  - 每張 triage card 左上加圓點（dot）+ 相對時間 (Xm/Xh/Xd)，hover 顯示 tooltip 含真實時間 + 來源 + 規則
  - Section header 加 tier 計數摘要（🟢 N · 🟡 N · 🟠 N · 🔴 N）
  - 切回 Triage tab 強制 re-render（避免相對時間過期，移除 dataset.rendered guard）

### Tooltip 格式
```
5m 前發布
📡 CNBC Top
🕒 04/29 03:29
規則：<1h 🟢 / <3h 🟡 / <5h 🟠 / ≥5h 🔴
```

### 設計取捨
- 4-tier 不 5-tier：avoiding 5-10h 中間色彩管理；≥5h 一律 🔴 反映「動能多半 priced in」
- 用 RSS 真實 `published` 不用 file timestamp：UI 反映新聞實際發布年齡，不被 DIGEST 跑時間污染
- 強制重 render：避免長時間打開 tab 時相對時間鎖死


## 🟢 Session Note (v1.61.1) — Protocol confirm 對話框加 daily_update.sh 上次更新時間

### 動機
User 點 invest / sector / DIGEST / FLASH / REVIEW 前忘記跑 `daily_update.sh` → 分析吃舊 macro/breadth/sector_intel cache。要在 confirm() 文字最前面加上「上次跑 daily_update 是多久前」做提醒。

### 修
- `Dashboard/utils.js` 新增 `UI.dailyUpdatePrefix()` async helper：fetch `/api/preflight`、抓 `breadth` cache age（daily_update.sh 第一步）作為 proxy；回傳：
  - 正常：`📌 daily_update：{age_str} 前\n\n`（中）/ `📌 daily_update: {age_str} ago\n\n`（英）
  - cache MISSING：`⚠️ daily_update 未跑過`
  - fetch 失敗：空字串（不污染 confirm）
- 5 個 confirm dialog 接上 prefix（皆加 `await UI.dailyUpdatePrefix()` + 字串前綴）：
  - `Dashboard/script.js:674` — Quick Launch invest
  - `Dashboard/page-decisions.js:567` — `goFlash` (FLASH from card)
  - `Dashboard/page-decisions.js:1109` — `refreshTicker` (re-analyze invest)
  - `Dashboard/page-news.js:445` — REVIEW (`copyReviewPrompt`)
  - `Dashboard/page-news.js:456` — flash_text (`goFlashText`)
  - `Dashboard/page-news.js:709` — DIGEST (`refresh-news` 按鈕)
  - `Dashboard/page-sector.js:851` — `triggerSectorScan`

### 不加範圍
- **Triage** (`page-news.js:407`)：自己 fetch RSS、跑 shallow snap，不依賴 daily_update.sh 任何輸出
- **動能** / **delete position** 等：無 daily_update 依賴
- 7 個 confirm dialog 共動 5 個檔


## 🟢 Session Note (v1.61.0) — Unified protocol queue：news/flash/triage 不再被 invest 擋

### Bug：news.html 按 Triage 跳「another protocol is running: invest」
- 原因：`dashboard_server.py:run_protocol()` 全域單一 `_protocol_state` lock。invest（10-15min）跑時 news/flash/triage/review 全被擋 (409)。
- 既有 `_analyze_queue` 是 invest 專用。news 系列沒有 queue，撞到 lock 就 reject。

### 修：擴展為 unified `_protocol_queue`
- `dashboard_server.py`：rename `_analyze_queue` → `_protocol_queue`；新增通用 `enqueue_protocol(name, params, source)` 接所有 protocol；entry 含 `id`/`label`/`name`/`params`；保留 `enqueue_analysis()` 為 invest-only backward-compat wrapper
- 3-min cooldown 只在連續兩個 invest 之間生效（`last_finished_name == "invest" and name == "invest"`），news 系列背靠背跑無 cooldown
- 新 endpoint：`POST /api/protocol-queue` 接所有 protocol；`DELETE /api/protocol-queue/{id}` 取消 queued entry
- 舊 `/api/analyze-queue` (GET/POST/DELETE-by-ticker) 全保留，沿用 wrapper

### Frontend：toast 取代立即 banner
- `Dashboard/page-news.js` `triggerProtocol()` 改 POST `/api/protocol-queue`：
  - `total_ahead === 0` → 立即 showRunBanner（會在 ~2s 內開跑）
  - `total_ahead > 0` → 只 toast：「⚡ FLASH «headline» 已排隊（第 3 個，前面 2 個進行/排隊中）」
  - 新增 `pollForMyJob(myId, title)` poller：以 `_activeQueueId` 為 gate，當 status.queue_id 等於 my id 才 showRunBanner（之前 banner 隱藏中）
- `Dashboard/analyze-queue.js` widget filter：`/api/analyze-queue` 回傳的 queue 現在含所有 protocol，widget 只 keep invest entries（widget 是 index.html invest queue 的視覺，不該污染 triage/flash）

### 設計取捨
- **單一 queue**：user 明確要求；簡化 lock 邏輯；不會兩 protocol 同時燒 token
- **延遲 banner**：避免 user 一按就看到「Claude 處理中」但實際在排隊（誤導）
- **toast 顯示完整位置**：第 N 個 / 前面 X 個進行/排隊中 — user 知道要等多久
- **invest 仍保 cooldown**：5-hour token 限制現實，連續兩個 invest 還是要 3min 緩衝

### Smoke test
- `enqueue_analysis('NVDA')`（legacy）+ `enqueue_protocol('triage')` + `enqueue_protocol('flash_text', {headline})` → 3 entries 全進同 queue，position 正確 1/2/3
- `enqueue_protocol('invest', {ticker:'NVDA'})` 對既有 NVDA 重複 → 拒絕 (duplicate_pending)
- `remove_from_queue(id)` 正確移除 by id

### User 動作
- 重啟 dashboard_server.py 載入新 queue 邏輯
- 之後 invest 跑時可同時點 Triage / FLASH，會 toast「已排隊（第 N 個）」，invest 跑完才開始


## 🟢 Session Note (v1.60.2) — Firstrade 自動記錄 Phase 1：macOS NotificationCenter discovery script

### 確認的事實
- 富途 push DB（v1.58.0 已接）只有市場新聞 bot 兩個 sender (10025/10027)，掃 400 筆 zero Firstrade 內容 → 「既然能收推播」這個前提僅對市場新聞成立
- User 確認 Firstrade trade confirmation 是走 macOS 系統推播（iPhone Continuity 鏡像到 Mac），落點 `~/Library/Group Containers/group.com.apple.usernoted/db2/db`（438KB SQLite）
- 該 DB 被 TCC 鎖住，Bash sandbox `unable to open database file` — Apple 規定 Terminal/Python 要加「Full Disk Access」
- DB schema：`record.data` 是 binary plist（NSKeyedArchiver wrap），需 plistlib + 處理 `$objects` list

### 兩階段策略
卡點：「不知道 Firstrade push 在 DB 裡長什麼樣」+「TCC 必須先授權」。所以拆兩階段：
- **Phase 1 (本 session)**：Discovery 腳本，user 跑一次告訴我真實格式
- **Phase 2 (待 Phase 1 feedback)**：寫 watch / parser / dashboard_server thread / 自動 sync positions.json

### Phase 1 script — `scripts/parse_firstrade_notifications.py` v0.1
- 讀 NotificationCenter DB：先 `shutil.copy` 到 tmp 避免 -wal/-shm journal 卡
- `sqlite3` URI 用 `mode=ro` 唯讀打開
- Output：(1) 最近 N 小時各 app push 計數（標 `← FIRSTRADE 命中` / `可疑（含 fst/trade/broker）`）；(2) 最近 limit 筆 sample 含 title/body/subtitle/uuid
- `_extract_title_body()` 兩條解碼路徑：`req` 直接 dict（早期 macOS）OR `$objects` NSKeyedArchiver 字串列（新版）
- TCC 阻擋時印中文錯誤 + 修法步驟（避免 user 不知所措）
- 用法：`python3 scripts/parse_firstrade_notifications.py -k firstrade --hours 720 -n 50`

### User 待辦
1. macOS System Settings → Privacy & Security → Full Disk Access → 加 Terminal.app → 重啟 Terminal
2. 跑 `python3 scripts/parse_firstrade_notifications.py --hours 168 -n 30` 看 app 清單
3. 鎖定 firstrade：`python3 scripts/parse_firstrade_notifications.py -k firstrade --hours 720`
4. 把命中的 bundle id + 1-2 筆 title/body 樣本貼給我 → 我寫 Phase 2 parser

### Fallback
- 若 NotificationCenter 真找不到 Firstrade（iPhone push 沒開 / Continuity 沒鏡像）→ 改走 Gmail MCP 讀 Trade Confirmation email
- 若 plist 解碼太複雜 → 用 `bpylist2` pip package


## 🟢 Session Note (v1.60.1) — 即時動態 banner：重新整理按鈕只在 done/error 才出現

### Bug：跑 protocol 時計時器持續累加，user 不該能按重新整理（會中斷觀察進度）
- 修：`news.html` 重新整理按鈕預設加 `hidden` class
- `showRunBanner()` running 狀態主動 `add('hidden')`
- `setRunBannerDone` / `setRunBannerError` 會 `remove('hidden')` 讓按鈕浮現
- 行為：跑著時 banner 只有 [展開][CANCEL][✕]；done 後變成 [展開][🔄 重新整理][✕]


## 🟢 Session Note (v1.60.0) — Triage tab：Stage 1 RSS triage 獨立檢視 + per-card Phase 2 按鈕

### 新增 `triage` protocol mode（`dashboard_server.py`）
- PROTOCOL_PROMPTS 加 `triage`：(1) 必須先跑 `python3 news/fetch_news_rss.py --hours 24` 重撈 RSS；(2) 對 raw.json 60+ 條跑 30 字 shallow snap；(3) 寫 `news_logs/YYYY-MM-DD_triage.json` (格式同 digest.json verdicts schema)；(4) 禁止跑 Stage 2 / 寫 digest.json / patch caches
- LOG_DIRS / TIMEOUT_OVERRIDES 對應補上（10 min timeout）

### 新 data feed：`shallow_news[]`（`bridge.py`）
- 加 `extract_shallow_news()` 函式：合併最近 3 份 `*_digest.json` 的 `depth: shallow` 項目 + 最近 3 份 `*_triage.json` 全部項目，dedupe by headline，按 `|score|` desc 排序取前 60
- `data.shallow_news` 注入 data.json，原 `data.news` 行為不動（只有 deep verdicts）

### Triage tab UI（`Dashboard/news.html` + `Dashboard/page-news.js`）
- filter tabs 加第 4 顆 `data-filter="triage"`，與 All/Reviewed/Pending 用分隔線隔開（**不在 All 內**）
- `<div id="news-triage-feed">` 獨立容器，跟既有 `#news-feed-detailed` 並列在 flex-1 包裝下
- `applyNewsFilter()` 切到 triage 時 hide deep feed / show triage feed（含 lazy render）
- `renderTriageFeed()` 渲 compact card：score badge + binary flag + source tag (digest/triage) + 截 3 sectors + 截 5 tickers + ⚡ Phase 2 按鈕
- 區塊 header 有「⚡ 跑新 Triage」按鈕：confirm（~30s RSS + 5-8min snap / ~$0.5 tokens）→ `triggerProtocol('triage', {}, ...)`
- per-card「⚡ Phase 2」按鈕 → 直接呼叫既有 `goFlashText(headline)`（複用 flash_text mode，append pending verdict 到 digest.json）

### i18n
- 加 `triage_tab` / `triage_section_title` / `triage_run_btn` / `triage_phase2_btn` / `triage_no_data`（中英）

### 設計取捨
- **Triage 不入 All**：避免 60+ 條 shallow 沖淡主 feed 的 deep verdict 視覺
- **dedupe by headline**：同一篇若 digest 跟 triage 都有，digest 優先（已過 4-subagent debate 的更可信）
- **不開 triage.json schema 文件**：完全沿用 digest.json verdicts schema，prompt 內 inline 描述
- **「跑新 Triage」每次強制重撈 RSS**：避免吃舊 raw.json，user 確認 Q2 是要新鮮資料

### Smoke test
- `python3 -c "import dashboard_server"` confirm `triage` 載入到 PROTOCOL_PROMPTS
- `python3 bridge.py` confirm `[OK] Shallow triage: 30 items`（從現有 digest.json 撈出）
- `node --check page-news.js` ok
- ⚠️ User 需重啟 dashboard_server.py 才會載到 `triage` mode


## 🟢 Session Note (v1.59.2) — flash_text 修「沒寫 digest.json」漏洞 + reload 後 banner 不再彈回

### Bug A：flash_text FLASH 跑完後 news.html 看不到 card
- 原因：v1.59.0 寫的 `flash_text` prompt 只叫 Claude 「產 reports/*_news_flash.md」，沒提示「也要 append verdict 到 news_logs/YYYY-MM-DD_digest.json」
- bridge.py 的 news cards 是從 `digest.json.verdicts[]` 抽，所以只有 MD 就等於 Dashboard 看不見
- 修：`PROTOCOL_PROMPTS["flash_text"]` step 4 改為「**必須產兩個檔（缺一不可）**」，明列 digest.json 的 schema 欄位（news_id, depth, review_status: pending, headline, headline_zh, source_label, news_type, bull/bear/sector/macro_case, verdict, net_impact_score, arbiter_reasoning, binary_risk, within_48h, affected_sectors, tickers_mentioned）
- 已對 22:17 OpenAI 那次 FLASH 手動補 patch（從 MD 萃 verdict 寫進 digest.json `n077`，重跑 bridge.py）— user 不用花 $1 重跑
- ⚠️ 概念澄清：FLASH 結果在「**待審核**」tab（review_status: pending），不在「已審核」。要進 已審核 需手動按卡片上「送審」按鈕觸發 `review` protocol 升級

### Bug B：點「重新整理」後 banner 又自動彈回
- 原因：page-news.js 第 458-479 行 resume IIFE 在 reload 後檢測到 protocol status=done within 5min，強制重新顯示 banner
- 修：reload 按鈕 click handler 額外寫 `sessionStorage.setItem('news_banner_dismissed', Date.now())`；resume IIFE 讀到 30s 內標記就跳過 done/error 重顯（running 仍會 resume，避免 user 在 active job 中誤點 reload 後沒進度可看）
- one-shot：標記讀完即 `removeItem`，不影響後續切頁

### Files
- `dashboard_server.py` — flash_text prompt
- `Dashboard/page-news.js` — reload click handler + resume IIFE skip 邏輯
- `news/news_logs/2026-04-28_digest.json` — 手動 append n077 verdict（含 .bak）

### 後續驗證（user）
- 開 `localhost:8080/news.html` → 看到「OpenAI 業務「運轉良好」」⏳ PENDING 卡片（在 待審核 tab）
- 重啟 dashboard_server.py 後再跑一次 flash_text → 確認 digest.json 自動更新（不再要手動 patch）
- 點 banner ✕ / 重新整理 → 頁面重整後 banner 不再彈回


## 🟢 Session Note (v1.59.1) — News banner 加重新整理按鈕 + 修 done 後 detail 殘留 bug

### Bug：banner 在 done 狀態下同時顯示矛盾文案
- title 被 `setRunBannerDone` 改成「分析完成，資料已更新」
- 但 `news-run-detail` 還是 `showRunBanner` 留下的「Claude 正在處理中...」沒清
- 修：`setRunBannerDone` / `setRunBannerError` 都加上 `detailEl.textContent = ''`

### 加 `news-run-reload` 按鈕
- `news.html` banner 右側 expand/cancel 之間加 `<button id="news-run-reload">🔄 重新整理</button>`，總是可見（不管 running/done/error）
- `page-news.js` 綁 click → `location.reload()`
- 用途：`pollNewsRunStatus` done 後雖然會自動 `loadNews()` 2s 後重撈，但 `bridge.py` 可能還沒跑完 / cache 沒同步，這個按鈕讓 user 在他想看到的時機強制硬重整


## 🟢 Session Note (v1.59.0) — 富途推播搬到 news.html + 每筆加 FLASH 按鈕

### 1) Backend 加 `flash_text` mode（`dashboard_server.py`）
- `PROTOCOL_PROMPTS` 新增 entry：prompt 接 `{headline}`（非 `{ticker}`），指示 LLM 抽事件主體 → WebFetch 補上下文 → 4 視角 inline 辯論 → 產 `reports/YYYY-MM-DD_HHMM_news_flash.md` (review_status: pending)
- `PROTOCOL_LOG_DIRS` / `PROTOCOL_TIMEOUT_OVERRIDES` 對應補上（10 min timeout，env override `FLASH_TEXT_TIMEOUT_SEC`）
- `run_protocol()` 第 263-266 行 `{headline}` validation 已存在（review 用），自動沿用

### 2) 卡片從 index.html 搬到 news.html
- `Dashboard/index.html` 移除 Layer 5 富途 card 與相關 IIFE
- `Dashboard/script.js` 移除 `initFutuPush()` IIFE + i18n 白名單條目（共 ~80 行）
- `Dashboard/news.html` 在 `<div class="p-8">` 起手、stats grid 之前插入 `id="futu-card"` glass-card（與舊版同結構，但新增 filter-stats span）

### 3) page-news.js 加 IIFE + handler
- 加 `window.goFlashText(headline)`：confirm 對話 → `triggerProtocol('flash_text', { headline }, '...')`，token 警告寫 `~$0.5-1` / 5-10 分鐘
- 加 `initFutuPush` IIFE：每筆 row 移除 ticker pill click（純顯示徽章），新增右側 `⚡ FLASH` 按鈕，點擊 → `goFlashText(rawText)`
- 新增 `filter-stats` 顯示「已過濾 N 則 HK/A 股」（從 `/api/futu-notifications` 回傳的 `filtered_count` 取）
- `applyTranslations()` 加 overview.futu_* 三鍵 lookup（避免切語言時富途標題不譯）
- 第 462 行 `isNews` 判斷加上 `'flash_text'`，使切回 news.html 時能 resume banner

### 設計取捨
- **不另開 protocol 檔**：news_protocol_v2.md L21/L394 已寫 FLASH 接「貼標題/連結」 — 原生支援 free text，只動 dashboard_server.py prompt template 即可
- **不從推播抽 ticker 走 `flash` (ticker) 路徑**：那會讓 FLASH 變成 generic ticker 新聞掃描，弱化「對這則推播事件本身分析」的核心
- **ticker pill 改純顯示**：news.html 沒 Quick Launch input，原 prefill 行為失效；主互動讓給 ⚡ FLASH 按鈕
- **FLASH 按鈕 inline confirm**：跟 page-decisions.js `goFlash` 對齊樣式，先 confirm 再送，避免誤觸 ~$1 token 燒

### Smoke test
- `python3 -c "import dashboard_server"` confirm `flash_text` 載入到 PROTOCOL_PROMPTS / LOG_DIRS / TIMEOUT_OVERRIDES
- `node --check Dashboard/page-news.js` / `script.js` 皆 ok
- `curl /news.html | grep futu-card` → 1（已加入）；`curl / | grep futu-card` → 0（已移除）
- ⚠️ User 9:27am 啟動的 dashboard_server.py 需手動重啟才會載到 `flash_text` mode（舊 process 不認）

### 後續驗證（user 自行）
- 重啟 dashboard_server.py
- 開 `localhost:8080/news.html`，確認最上方有富途 card + ⚡ FLASH 按鈕
- 點某筆 ⚡ FLASH → 對話 → OK → 看 `news/scan_logs/flash_text_*.log` + 5-10 分鐘後 `reports/*_news_flash.md`


## 🟢 Session Note (v1.58.1) — 富途 HK/A 股過濾 + 決策日曆 today 動態化

### A) Futu push HK/A 股過濾（`scripts/parse_futu_notifications.py` + `dashboard_server.py`）
- 加 `_HK_CN_HARD_KEYWORDS` (~25 個：港股/恒生/A股/滬深/上證/科創板/港元/南向資金/.HK/.SH/.SZ 等)
- 加 `_HK_CN_ONLY_NAMES` (~50 個：騰訊/美團/小米/中國移動/工商銀行/中國平安/寧德時代/茅台/萬科/京東方/海康威視/藥明康德 等)
- 加 HK 5 位代碼 + CN 6 位代碼 regex
- `load_notifications()` 加 `filter_hk_cn=True` 與 `return_stats=True` 參數；endpoint 預設過濾並回傳 `filtered_count`
- CLI 加 `--no-filter` opt-out
- 200 筆樣本驗證：精準抓出 41 筆 HK/CN（涵蓋恒指/南向資金/中國平安/寧德時代/中信證券 等樣式），美股相關全部保留

### B) 決策日曆 today hardcode 修正（`Dashboard/page-calendar.js`）
- Bug：`todayIso` 之前吃 event_index.json 的 `j.today`，indexer 沒重跑時鎖在 2026-04-26；月份預設亦 hardcode `new Date(2026, 3, 1)`；7-day 視窗 fallback `'2026-04-26'`
- 修：加 `browserTodayIso()` helper，`todayIso` 始終取瀏覽器當天；`currentMonth` 預設改成當天月份；indexer 的 `j.today` 改名 `indexedAt`，僅在 stats 行顯示供 staleness 提示（`today=YYYY-MM-DD · indexed=YYYY-MM-DD`）
- 移除所有 `2026-04-26` / `new Date(2026, 3, 1)` hardcode


## 🟢 Session Note (v1.58.0) — 路線 P 富途即時推播整合（lazy fetch + ticker 辨識）

把 macOS 富途牛牛客戶端 IM SQLite (`msg_0.db`) 推播接進 Dashboard，5 筆顯示在 index.html Layer 5。

### 1) `scripts/parse_futu_notifications.py` 重寫
- 新增 `load_notifications(limit, keyword, with_tickers)` 純資料函式 + `is_available()` + `extract_tickers(text)`
- 中文公司名 → US ticker dict（~70 筆，Mag-7 / 半導體 / SaaS / 中概 ADR / 金融 / 能源 / 民生 / 醫藥 / crypto）
- 英文 ticker regex `[A-Z]{2,5}` + stopword 過濾（避免 AI/CEO/RAS/NEW 等誤判）
- 加 `--json` flag；保留原 CLI 列表行為

### 2) `dashboard_server.py` 新增 endpoint
- `GET /api/futu-notifications?limit=5`：lazy fetch（無背景 thread），5s 記憶體 cache 防抖
- DB 找不到 → `{available:false}`，client 顯示「客戶端未安裝」
- script lazy import `parse_futu_notifications`，模組載入失敗也不影響 server 啟動

### 3) `Dashboard/index.html` 加 Layer 5 卡片
- glass-card「富途即時推播」全寬，含 reload 按鈕 + 5 筆 list 容器

### 4) `Dashboard/script.js` 新增 IIFE renderer
- 每筆顯示相對時間（`Xs/Xm/Xh`）+ ticker pills + 推播全文
- 點 ticker pill → 預填 Quick Launch input + scroll + toast（不直接入隊，避免誤觸燒 token）
- 60s 自動重整；reload 按鈕手動觸發

### 5) `Dashboard/i18n.js` 新增 5 個鍵
- `futu_push_title / futu_reload / futu_loading / futu_no_data / futu_unavailable`（中英）

### 設計取捨
- **不放背景 thread**：用戶不在 Dashboard 時不需要查 DB，lazy fetch + 5s cache 已足
- **ticker pill 不直接入隊**：只 prefill ticker-input，最終由 user 手動點「分析」決定是否花 ~$4 tokens
- **不動 daily_update.sh**：富途推播是純查詢層，不影響 protocol 流水線

### Smoke test
- `python3 scripts/parse_futu_notifications.py --json -n 5` 正確輸出 ticker（NVDA/BTC/GOOGL/POET 等）
- `curl /api/futu-notifications?limit=3` 200 OK，2nd hit 0.6ms（cache 命中）
- index.html 含 `futu-card` + `futu_push_title` 元素

### TODO 進度
- [P-TICKER] / [P-BACKEND] / [P-CARD] 全部完成


## 🟢 Session Note (v1.57.0) — Tooltip 升級 Wave 2：radar / momentum 全頁套上 stages-with-action 風格

延續 v1.56.0 (sector pill rich tooltip)，這版把同樣的 stage-row + action-verb 解說方法擴到 radar 與 momentum 頁面。

### Radar (`page-radar.js` + `style.css`)

**內容升級** — 給 9 個關鍵 metric 加 `stages` 陣列（每階段含 dot + range + tag + action verb + detail）：
- mid_heat（3 階段：熱/溫/冷）
- short_bull（4 階段：unanimous/majority/split/bearish）
- avg_conv（3 階段：高/中/低）
- confidence（3 階段：強/中/弱）
- driver_atr（3 階段：高/中/低 → 倉位反向）
- factor（3 階段：amplify/normal/dampen）
- spy_rsi（5 階段：含逆向 contrarian 訊號）
- vix（5 階段：calm/normal/elevated/high/panic）
- yield_curve（3 階段：含倒掛衰退預警）
- credit_spread（3 階段：寬鬆/正常/緊縮）

**引擎升級** — `showRadarTip` 加上：
- `RADAR_STAGE_DOTS` map（41 個 stage key 對應 dot）
- `classifyRadarStage(stages, value)` helper（依 `data-tip-value` 屬性 highlight 對應 row）
- `renderRadarStageRows()` mirror style.css 的 `.stt-stage-row` 視覺
- `entry.stages` 自動 render 為 `.rtt-stages` 區塊

**CSS** — `style.css#radar-term-tooltip`：max-width 320→360px，加 `.rtt-stages / .rtt-stage-row / .rtt-stage-active / .rtt-stage-dot / .rtt-stage-range / .rtt-stage-tag / .rtt-stage-action / .rtt-stage-detail` 全套樣式，hint 改用 dashed top border 對齊 signal-tip。

### Momentum (`page-momentum.js` + `momentum.html` 內聯 CSS)

**內容升級** — 給 8 個歧義度高的 signal/warning 加 `tiers` 陣列（3 行 scenario matrix：strong / standard / weak 對應的解讀）：

Signals: `high_short_interest`、`squeeze_candidate`、`oversold_rsi`、`macd_bullish_cross`
Warnings: `overbought_rsi`、`parabolic_blowoff_risk`、`stage4_downtrend`、（macd_bearish_cross 既存）

每個 tier 含 `{ dot, label, text }` — 例：`oversold_rsi` 在 Stage 2 + 量縮是 🟢 (健康回檔買點)，但在 Stage 3-4 是 🟠 (弱勢延續訊號，**不是機會**)。明確告訴 user「同一訊號在不同 context 下意義完全不同」。

**引擎升級** — `_renderSignalTip()` 加 `_renderTierRows()` helper，當 `entry.tiers` 存在時 render `.mpt-tiers` 區塊。

**CSS** — `momentum.html` 內聯：max-width 320→360px、加 `.mpt-tiers / .mpt-tier-row / .mpt-tier-dot / .mpt-tier-text` 樣式對齊 `#signal-tip-tooltip` 視覺，hint 改用 dashed top border。

### 風格一致性

三套 tooltip 引擎（signal-tip-tooltip / radar-term-tooltip / mom-pill-tooltip）現在視覺上幾乎不可區分：
- max-width 360px
- 12.5px bold title + 11.5px desc + 10.5px stage rows
- dashed top border for hint
- 🟢🟡🟠🔴 dot system 統一

**驗證**：`node -e new Function()` 4 檔（radar / momentum / decisions / utils）syntax 全 pass。

VERSION 1.56.2 → **1.57.0**（minor — UX consistency wave 完成）。

> 後續可選：(a) 給 radar render 補 `data-tip-value` 屬性以便 live highlight 對應 stage row；(b) 為剩下不歧義的 momentum signals 簡單加 tier 也可（fresh_golden_cross_20_50 / 50_200、stage2_uptrend_intact、volume_expansion 等）。



## 🟢 Session Note (v1.56.2) — 決策中心 risk pill 溢出卡片修補

User 反映 BE 個股分析有條 risk「FRED Overheating + Sector Rotation Avoid Technology — BE 雖歸 Industrials 但 AI Data Center 本質為高久期」溢出卡片。

**根因**：`page-decisions.js:315` `riskTag()` pill 用 `whitespace-nowrap`，搭配 `flex flex-wrap` 父容器只允許 pill 之間換行，pill **內部**長文字會直接溢出。

**附帶 bug**：原本 `replace(/\b\w/g, c => c.toUpperCase())` 在 CJK / 拉丁混合字串上會在 unicode word boundary 處強制 title case，混成奇怪的大小寫。改成 `/\b[a-zA-Z]/g` 只針對 ASCII。

**修法**：
- 移除 `whitespace-nowrap`，加 `leading-relaxed max-w-full break-words` 讓長 risk 在 pill 內自然換行。
- title case regex 限定 ASCII 字元，避免影響中文。

VERSION 1.56.1 → **1.56.2**（patch — UX bug fix）。

> ⚠ Wave 2 進行中（CSS for radar-term-tooltip 已升級，RADAR_TERMS stages content 編寫中被中斷）— 本 session 完成此 BE bug 後等下一輪指示再續做。



## 🟢 Session Note (v1.56.1) — sector pill hover 視覺修補：背景消失 → 3D 浮起

User 反映 Wave 1 後 sector 7 顆 pill hover 時「背景消失、變純文字」。

**根因**：`style.css:588` 有條全域規則 `[data-signal-tip]:hover { background-color: rgba(255,255,255,0.025); border-radius: 6px; }`，原本設計給 index 頁無背景的 verdict pill 加 hover 提示。但 sector pill 本來有 `background: var(--bg-card)` 實心卡片底色，被這條 0.025 半透明白覆蓋後反而變得「沒底」。

**修法**（sector.html 內聯 style，~12 行）：
- `.status-pill` 加 `transition`（transform/shadow/border 0.15s）。
- `.status-pill[data-signal-tip]:hover` (specificity 0,3,0 > 全域 0,2,0) 蓋過去：
  - `background: var(--bg-card)`（強制保留實心底）
  - `border-color: rgba(255,255,255,0.20)`（微亮邊框做 affordance）
  - `transform: translateY(-1px)` + `box-shadow: 0 6px 14px rgba(0,0,0,0.32)` → 3D 浮起
- light theme 同步：邊框與 shadow 改成深色變體。

VERSION 1.56.0 → **1.56.1**（patch — UX 修正）。



## 🟢 Session Note (v1.56.0) — Tooltip 升級 Wave 1：Sector page 7 顆 pill 套上「AI 裁決區風格」rich tooltip

User 反映「sector 頁面的 pill hover 看不懂」。診斷後發現：
1. **UX bug**：sector.html 7 顆 pill 用簡易 `pill-tooltip` 引擎（單行解釋），但 i18n 字典根本沒有 `breadth/ftd/regime/exposure/fg/cycle/vix` 對應條目 → fallback 顯示字面 key（"breadth"），近乎壞掉。
2. **架構限制**：index 頁的「AI 裁決區」rich tooltip engine（`signal-tip-tooltip` + `SIGNAL_TIPS`）寫在 `script.js`，只有 index 頁載入 → 其他頁面拿不到。

**Wave 1 改法**（4 檔，~440 行 diff）：
- **`utils.js`**（+475 行）：新增 IIFE `initSharedSignalTipEngine()`，整段 engine + 9 個 SIGNAL_TIPS bundles（沿用 `breadth/ftd/market_top/synth` + 新增 `regime/exposure/fg/cycle/vix`）。Live builders 涵蓋類別型訊號（regime/cycle 用 keyMap 對應 stage）與字串範圍（exposure 用 regex parse "60-75%" 取中位數）。Engine init 用 `DOMContentLoaded` guard 因為 utils.js 在 <head> 載入時 `#signal-tip-tooltip` 還不存在。
- **`script.js`**（−275 行）：刪除 lines 1083-1356 重複的 engine block（功能已搬到 utils.js）。簡易 `pill-tooltip` engine 保留（給 sector 頁的其他 risk-flag tag 用）。
- **`sector.html`**（+1 行 + 7 處改）：加 `<div id="signal-tip-tooltip">`；7 顆 pill 從 `data-tip-key="X"` 改 `data-signal-tip="X"`。
- **`page-sector.js`**（+25 行）：`renderStatusStrip` 在每顆 pill 上 setAttribute 寫入 live data 屬性（`data-regime`, `data-br-score`, `data-ftd-date` …），讓共用 engine 的 live banner 能讀到當前值並 highlight 對應 stage。

**新 5 個 SIGNAL_TIPS 內容設計**（每個含 zh+en × ~30 行）：
- `regime`：4 種 posture（RISK_ON/NEUTRAL/VOLATILE/RISK_OFF）對應的進攻/防禦操作。
- `exposure`：85+/60-85/30-60/0-30 四級 cash 比例與選股紀律。
- `fg`：Fear&Greed 5 級含逆向訊號詮釋（極度恐慌 = 🟢 buy, 極度貪婪 = 🔴 trim）。
- `cycle`：Early/Mid/Late/Distribution 4 階段對應動作。
- `vix`：< 15 / 15-20 / 20-30 / 30-40 / 40+ 五級波動環境策略。

每個 stage row 含：dot（🟢🟡🟠🔴）+ range_label + tag + action verb + detail（為何要這樣做）。

**驗證**：`node -e new Function(code)` 三檔 syntax check 全 pass：utils.js 1078 行、script.js 1082 行、page-sector.js 943 行。

VERSION 1.55.9 → **1.56.0**（minor — UX 升級 + 引擎共用化）。

> Wave 2 待批：momentum / radar 各自有自家 tip system（`data-sig-tip`, `data-warn-tip`, `data-radar-tip`），文案要重寫，user 看完 Wave 1 再決定。



## 🟢 Session Note (v1.55.9) — Dashboard 動能選股 整合 SOX：UI filter button + scan coverage 補齊

延續 v1.55.8 的 SOX universe（CLI 層），這版把它打通到 dashboard。User 反映「動能選股看不到費半」，診斷後發現兩個問題：

**A. UX bug**：Dashboard 的「Universe 範圍」filter 是 client-side post-scan filter，UI 寫死只有 All/SP500/NDX100 三鈕，沒有 SOX。
**B. Coverage bug**：Dashboard scan 跑 `screen.py --universe all` 等於 sp500 ∪ nasdaq100，30 檔 SOX 中有 9 檔（TSM, AZTA, ENTG, IPGP, ONTO, QRVO, RMBS, SLAB, WOLF）根本不在 union 內、永遠不會出現在 scan 結果。

**改法**（4 檔 ~25 行）：
- `screen.py`：CSV 多 `in_sox` 欄；`_row_from_payload` 加 `sox_set` 參數；`--universe all` 改成 `sp500 ∪ nasdaq100 ∪ sox` union（universe_desc 同步更新）；watchlist merge 條件加 `sox`。
- `bridge.py`：`_build_row` 把 `in_sox` 從 CSV 帶進 `data.json.momentum_screen.rows[]`（fallback 到 `"0"` 兼容舊 CSV）。
- `Dashboard/momentum.html`：segmented-control 加第 4 顆 `<button data-value="sox">費半 SOX</button>`。
- `Dashboard/page-momentum.js`：filter 加 `if (f.universe === 'sox' && !r.in_sox) return false;`；`isWatchlistOnly` / `isWatchlist` 都從「不在 sp500 也不在 ndx」改成「三個 reference 都不在」（避免 SOX-only ticker 如 TSM/WOLF 被誤判為 watchlist）；i18n label 加 `費半 SOX` / `PHLX SOX`。

**端到端驗證**：
- 跑 `screen.py` → CSV 第一行欄位含 `in_sox`，scan 536 tickers（含 9 SOX-only 新增）。
- `bridge.py` → `data.json.momentum_screen.rows[]` 30 列 `in_sox=true`。
- 9 個 SOX-only ticker 全部 in_sp500=False, in_nasdaq100=False, in_sox=True ✓。
- ARM(NDX+SOX)、ON(SP+SOX)、MU(SP+NDX+SOX)、RMBS(SOX-only) 4 種覆蓋情境分布正確 ✓。

VERSION 1.55.8 → **1.55.9**（patch — UI button + 1 個新欄位 + universe union 擴充，無 schema 破壞性變更）。



## 🟢 Session Note (v1.55.8) — momentum screener 加 SOX (費半) universe

User 想用短期動能掃描費半 30 檔成份股。`skills/momentum-monitor/scripts/screen.py` 已支援 universe 模式（檔名約定 `universes/{name}.txt` + 可選 `{name}_sectors.json`），純加檔即可：

- **新增** `universes/sox.txt`：30 檔 PHLX Semiconductor Index 成份（含 2 檔 ADR：TSM、ASML — user 確認要含）。
- **新增** `universes/sox_sectors.json`：30 檔 GICS sector 對應（全 Information Technology；既有 `_load_sector_map()` 會自動 merge 所有 `*_sectors.json`，無須改 loader）。
- **改** `screen.py` usage 範例 + `--universe` help 列舉 `sox`。

Smoke test：`screen._load_universe('sox')` 載入 30 檔、TSM/ASML 在內、sector map 合併後 530 entries（sp500=503 + sox 新增 27 檔不重複）。

用法：`python3 skills/momentum-monitor/scripts/screen.py --universe sox --min-score 60`。

VERSION 1.55.7 → **1.55.8**（patch — 純新增 universe，無 schema/API 變更）。



## 🟢 Session Note (v1.55.7) — 盤前檢查「更新全部過期」改 sequential queue + 修依賴順序

**症狀**：User 按 Dashboard 首頁「盤前檢查 → 更新全部過期」，confirm dialog 列出 sector + news 兩項說會跑，但切到 news.html / sector.html 兩個分頁都看不到 running banner。

**根因 1（單啟動 bug）**：`Dashboard/script.js` preflight-run-all handler 對 staleToken loop 只 POST 第一個就 `break`（comment 寫 "single-job lock — only start one"）。第二個 protocol 永遠沒被啟動，user 看到的 confirm dialog 是空頭支票。

**根因 2（依賴順序錯）**：`/api/preflight` 回傳順序剛好是 sector 先、news 後。即使修好「啟動兩個」，也會讓 sector 先跑、引用上一輪舊的 news_protocol_v2 catalysts（驗證：`sector/sector_logs/*_sector_intel.json` `top_catalysts[]` 帶 `"source": "news_protocol_v2"`）。

**改法**（單檔 ~80 行）：
- 新增 `waitForProtocolDone()` helper，輪詢 `/api/run-protocol/status` 直到非 running。
- 新增 `runPreflightQueue(items, isZh)`：sequential async loop，每輪 POST 完等 backend single-job lock 釋放再進下一輪；toast 顯示 `執行 1/2: 新聞 DIGEST（排隊中: 產業情報）`。
- 新增 `PREFLIGHT_ORDER = ['news', 'sector']` 常數，queue 強制依此排序，與 `/api/preflight` 順序解耦。
- 重用既有 `_launchPollTimer` + `pollLaunchStatus()` 維持 index 頁 launch-status banner；page-sector.js / page-news.js 自身的 resume IIFE 自動處理對應分頁的 running banner 顯示（無須改）。

**重要**：後端 `_protocol_lock`（single-job 互斥）保持不變 — lock 是正確設計，client queue 是合適的解法層級。

VERSION 1.55.6 → **1.55.7**（patch — bug fix + 依賴順序修正）。



## 🟢 Session Note (v1.55.6) — 決策日曆改 inline detail panel（取代 bottom drawer）

User 反映「點日曆任何東西都不該用 drawer 彈出，他會蓋掉下面的東西」。原本 `#cal-drawer` 是 `fixed inset-x-0 bottom-0 max-h-[70vh]`，從畫面底部滑上來，直接遮住日曆下半 + filter bar + aggregate panel，無法對照其他日期。

**改法**（option B：inline detail panel）：
- `calendar.html`：把 drawer 容器從 `<body>` 底搬進 `#cal-main` 裡，放在 `#cal-grid` 之後 / `#cal-filterbar` 之前；移掉 `fixed/inset/bottom/z-30/max-h/shadow-2xl`，改為 inline `<div id="cal-detail" class="cal-detail-panel">`。
- `page-calendar.js`：`openDrawer/closeDrawer` → `openDetailPanel/closeDetailPanel`；新增 `selectedDate` state；點被選格子再次 → toggle 收起；切月/ESC 也收起；切換 selected 時舊格 ring 移除、新格加 `cal-cell-selected`；開啟後 `scrollIntoView({block:'nearest'})` 讓 panel 自然進視野。
- `style.css`：替換 `#cal-drawer` 樣式為 `.cal-detail-panel`（max-height + opacity + translateY 摺疊動畫，dark/light 兩套底色）；新增 `.cal-cell-selected` emerald ring（與 today-cell 區分但同色系）；`#cal-drawer table` selector 改 `#cal-detail table`；`.cal-drawer-section*` class 保留（被 inline panel 重用）。

**效果**：日曆 grid 永遠 100% 在視野上，點任一格詳情長在下方、可連點不同日期比對，filter bar / aggregate panel 都不再被遮。

VERSION 1.55.5 → **1.55.6**（patch — UI 互動改善）。



## 🟢 Session Note (v1.55.5) — 修短期雷達 themes 鎖在 10 個的衝突

User 反映「全部主題又變回只有十個」，疑似 skill 衝突。診斷：

**症狀**：theme-detector cache 4/25 還有 20 themes，4/26 12:17 後降到 10。下游 thematic-screener / radar 全部跟著掉。

**根因**：兩條 call path 對 `theme_detector.py` 給的 `--max-themes` 不一致：
- `daily_update.sh`: `--max-themes 25 --max-stocks-per-theme 25` (顯式)
- `sector/phase_1-2-3.md` Phase 2 (產業掃描)：沒帶 `--max-themes`，吃 default **10**

當 user 在 daily_update 跑完之後又跑「產業掃描」→ Phase 2 重觸發 theme-detector 用 default 10 → cache 從 20 降到 10 → `--skip-if-fresh 10800` 鎖住降級狀態，後面 daily_update 想恢復 25 也跳過。

**修法**：把 `theme_detector.py` 的 `--max-themes` default 從 10 → **25**（與 daily_update 對齊），`--max-stocks-per-theme` 同樣 10 → 25。再跑一次 theme-detector 重生 cache 確認 → **20 themes**（25 是上限，theme universe 實際只有 20）。

**同步改 phase_1-2-3.md**：在 Phase 2 段落加註明 default 已對齊 25，避免將來有人「以為要降回 10」。

**驗證**：theme cache 從 10 → 20。下游 thematic-screener + bridge 重跑後 data.json `tactical.themes` 應該也回到 20（pipeline 跑 ~90s 完整跑完）。

VERSION 1.55.4 → **1.55.5**（patch — config 衝突修補）。



## 🟢 Session Note (v1.55.4) — 綜合曝險 (Synthesized Ceiling) 也加 tooltip

延續同 dispatcher 模式補齊四顆 pill 的 tooltip：

**SIGNAL_TIPS.synth**：
- desc 講三訊號合成邏輯（min 規則）+ 為什麼這樣設計（衝突時偏向最保守）+ 個股實際倉位還會再乘其他乘數
- 4 stage（Aggressive 75+ / Standard 50-75 / Defensive 25-50 / Crisis < 25）
- live banner 多一行 source breakdown：`廣度 60-75% · FTD 75-100% · 頂部 80-90%`（讓 user 一眼看出是哪個訊號在拖底）
- hint：直接寫公式 `min( breadth_ceiling_mid, ftd_range_mid, market_top_budget_mid )`

**新增 CSS**：`.stt-live-sources` — JetBrains Mono 小字、灰色、縮在 live banner 底下顯示來源拆解

**新 STAGE_DOTS**：sy_aggressive / sy_standard / sy_defensive / sy_crisis（4 個）

VERSION 1.55.3 → **1.55.4**（patch — 補齊四顆 pill 的 tooltip 完整性）。



## 🟢 Session Note (v1.55.3) — Breadth + Market Top 也加 hover tooltip

延續 v1.55.2 的 FTD tooltip 風格，把另兩個 macro signal pill（市場廣度 / 頂部風險）也接同套 UX：

**重構**：把原本只支援 FTD 的 `buildFtdTipHTML` → 改成 dispatcher `buildSignalTipHTML(el, lang)`：
- `LIVE_BUILDERS` map：`{ ftd, breadth, market_top }` 各自定義 live banner 邏輯
- `renderStageRows` 抽出共用 stage list 渲染
- `STAGE_DOTS` 集中管理三組 stage key → emoji dot

**SIGNAL_TIPS 新增 2 entry**：
- `breadth` — 5 stage（Strong / Healthy / Neutral / Weakening / Critical）by score thresholds 0-100，每個 stage 都有「行動取向」action label（全力進攻 / 標準參與 / 選股降倉 / 防禦為主 / 退守 cash）
- `market_top` — 5 stage（Normal / Early Warning / Elevated / High / Top Formed）by composite_score thresholds，action label（可進攻 / 留意 / 降倉收緊 / 撤退中 / Cash 優先）

**desc 寫法刻意不對稱**：
- breadth desc 強調「現在健康嗎」+ 列出組成（200 MA / 8 MA / 突破家數 / A-D 差）
- market_top desc 強調「快崩了嗎」+ 列出組成（distribution day / leadership / defensive rotation / 新高萎縮 / R2K vs SPY）
- 並在 market_top desc 末尾加一句「與 breadth 互補」幫 user 理解兩者差異

**pill HTML**：breadth + market_top wrapper 各加 3 個 data attrs（score / zone / ceiling-or-budget），同套 hover behavior（無 cursor 變化、淡 bg highlight）

VERSION 1.55.2 → **1.55.3**（patch — UX 擴充，沿用同模式）。



## 🟢 Session Note (v1.55.2) — FTD tooltip 文案重寫（去 jargon、行動取向）

User 反饋三點：
1. 「late but valid 是啥」→ 階段名太 jargon，看不懂
2. 「不要這麼技術，加說明指標怎麼產生 + 各階段意義（可以買 / 要等 / 太晚）」
3. 「Phase 4 那個不用寫進去」+「滑鼠移上去不要變問號」

### 改動

**內部 enum rename**：`late_valid` → `standard`（涉及 script.js + investment_protocol_v4_8.md Phase 4 Step 3.5 + risk_audit schema）

**Tooltip 文案重寫**（zh / en 雙語）：
- title: `FTD · Follow-Through Day` → `FTD · 市場底部確認訊號`
- desc: 用大白話解釋 rally day 計數 + 4-7 天條件 + 為什麼越早越好（不講 O'Neil 名詞）
- 每個 stage 4 個欄位：`range_label`（day 1-5）/ `tag`（黃金期）/ `action`（可以買）/ `detail`（一句話講原因）
- 行動取向標籤：黃金期·可以買 / 主升期·仍可參與 / 補漲期·晚但仍有機會 / 過熱期·等下一輪
- 移除原本的 hint「Phase 4 Step 3.5 ...」與底部 status text（過於技術）
- 新 hint 改成 reset 條件提醒（user 上一條問過的東西）

**視覺**：
- Stage row 改成 grid 三欄（dot · range · tag · action）+ 第二行 detail 撐底
- 當前 stage 整 row 加綠色 tinted 底（`rgba(16, 185, 129, 0.08)`）+ tag 變綠
- Live banner 顯示「📅 ftd_date · 已過 N 天 · stage tag — action」
- 拿掉 `cursor: help`（user 抱怨變問號），改純 hover bg 變化作 affordance

VERSION 1.55.1 → **1.55.2**（patch — UX 文案修補）。



## 🟢 Session Note (v1.55.1) — Index 卡 FTD pill 加 hover tooltip + 解 user 「為什麼 baseline 是 4/8」

### Q&A 記錄
- **「FTD 是個股不同嗎？」** → 否，FTD 是市場級訊號（S&P 500 + NASDAQ 條件），所有股票共享同一個 ftd_date
- **「為什麼 baseline 是 4/8？」** → O'Neil 4 條件第一個全中的日子。3/31~4/2 太早；4/6 +0.44%、4/7 +0.08% 漲幅不夠；4/8 +2.51% 量增 29.6% 雙指數確認 → 鎖定
- **「4/27 後若再符合會重算嗎？」** → 否，FTD 一旦確認就鎖，只有 invalidation（跌破 swing low / 累積 6+ distribution day）或新 swing low 才會 reset

### 改動：FTD pill tooltip
原本 v1.55.0 只用 `title=""` 屬性顯示 ftd_status_text，UX 太陽春。改成跟 radar 頁同款的 hover tooltip：

- **index.html**: 加 `<div id="signal-tip-tooltip">` 容器
- **style.css**: 加 `#signal-tip-tooltip` + `.stt-title` / `.stt-desc` / `.stt-live` / `.stt-stages` / `[data-signal-tip]` (clone 自 #radar-term-tooltip 風格)
- **script.js**:
  - FTD pill wrapper 加 `data-signal-tip="ftd"` + 4 個 data attributes (state/date/day/status)
  - 新增 `initSignalTipTooltip` IIFE：包含 SIGNAL_TIPS 字典 (zh/en) + classifyStage (用 Phase 4 Step 3.5 同樣 4 階段分類) + buildFtdTipHTML + showSignalTip/hideSignalTip
  - mouseover delegate 在 document level，hover 100ms 後 show，leave 80ms 後 hide

**Tooltip 內容** (3 段)：
1. Title + 概念解釋（O'Neil + invalidation 規則）
2. Live 區：`📅 2026-04-08 · 已過 12d · Late but valid`（current stage 高亮）
3. Stage 對照：4 種階段全列出，當前 stage 加粗白色，其他灰色
4. Hint: 「Phase 4 Step 3.5 FTD timeline gate 依此 stage 套用倉位乘數」

VERSION 1.55.0 → **1.55.1**（patch — UX polish）。



## 🟢 Session Note (v1.55.0) — Investment Protocol V4.9：FTD Timeline Gate

User 看完 BUG-006 修補 + FTD 解釋後決定把 FTD timeline 接進個股決策流程。同時補上 Dashboard 顯示。

**為什麼**：FTD 是市場級訊號（不分個股），但「FTD 後第幾天進場」對 cyclical leaders 勝率影響大 — O'Neil 統計：第 1-5 天 prime window vs 第 13+ 天「補漲」失敗率約 2x。

### 三個改動

**1. bridge.py — 把 `ftd_timeline.*` 帶進 data.json**
- `extract_ftd_data` 新讀 `raw["ftd_timeline"]` → 輸出 `data.ftd.days_since_ftd` / `ftd_status_text`
- 跑了一次 `ftd_yfinance.py` 重生 cache（舊 cache 沒新欄位，自然 None）
- 驗證 data.json：`days_since_ftd=12, ftd_status_text="FTD CONFIRMED, day 12 post-confirmation (rally-day 18; FTD originally confirmed on rally-day 6)"`

**2. Dashboard `index.html` FTD pill — 露出 date + day**
- `script.js` Phase 0 macro composite pill 加一行：`2026-04-08 · day 12`（hover tooltip 顯示完整 ftd_status_text）
- 字小、放在 quality_score 下方，視覺不搶 focus

**3. invest_protocol_v4_8.md — 加 Phase 4 Step 3.5 FTD Timeline Gate（V4.9）**

Lookup 表：

| `days_since_ftd` | O'Neil 階段 | Cyclical | Defensive | 停損調整 |
|---|---|---|---|---|
| 1-5  | Prime entry | ×1.0 | ×1.0 | 標準 |
| 6-12 | Late but valid | ×0.90 | ×1.0 | 標準 |
| 13-20 | Late cycle / distribution risk | **×0.75** | ×0.95 | **-1pp（cyclical only）** |
| 21+  | FTD exhausted | **×0.50 OR REJECT** | ×0.85 | **-2pp（cyclical only）** |

Day 21+ reject 條件（cyclical only）：`RS_rating < 90 OR distance_50ma > 15%` → final_decision = REJECT。

Schema 改動：
- `risk_audit.ftd_timeline_gate` 新增 7 個 sub-field（applied / days_since_ftd / stage / sector_class / multiplier / stop_loss_adjustment_pp / rejection_triggered）
- `phase5_export_schema.md` 對應 row 加上去
- Phase 0 mtime cache 讀取必抓 `_phase0.ftd.days_since_ftd` 供 Phase 4 用
- validator 暫不加入 required（保持 backward compat，等 V4.9 session 累積夠多再啟用 hard check）

### FTD 是個股不同嗎？— ❌ 不是

回應 user 提問：FTD 是市場級訊號（S&P 500 + NASDAQ 反彈日量價條件），所有股票共享同一個 ftd_date。個股差別在「對 FTD 的反應強度」（領導股 vs 補漲股 vs 落後股），但 FTD signal 本身只有一個。

### 後續可能的延伸（暫不做）
- #2 FRED regime ticker-level multiplier
- #3 Theme exhaustion warning
- 等 V4.9 session 累積後啟用 validator hard check

VERSION 1.54.1 → **1.55.0**（minor — 新功能 + protocol 大版本 V4.8 → V4.9）。



## 🟢 Session Note (v1.54.1) — events_archive.json 持久化過去事件

User 反映「4/27 的財報，4/28 也要在 calendar 上看得到」。問題：bridge.py 每次都從 FMP/Fed/sector-protocol 重撈 forward-only feeds，過去事件就被沖掉。

**修法**：
- 新增 `events_archive.json` 持久化檔（BASE_DIR），schema：`{schema_version, updated_at, events: [...]}`
- `aggregate_upcoming_events()` 流程：
  1. Load archive（過去 + 已知未來）
  2. 撈 fresh feeds（sector-protocol + Fed + FMP econ + FMP earnings）
  3. Concat archive + fresh，按 `_event_dedupe_key` dedupe（fresh 覆蓋 archive，新資料更準）
  4. 既有 cross-category merge & 排序維持原樣
  5. **每筆 event 都重算 `within_48h`** 從當下日期判斷（archive 裡的 stale flag 自動更正）
  6. 寫回 archive（atomic `.tmp` → `os.replace`）
- `.gitignore` 加 `events_archive.json`（accumulates daily，regenerable，不該污染 commit）

**驗證**：
- 第一次跑：archive 從 0 → 61 筆（今日 + 未來）
- 手動注入過去事件 (TEST_PAST_EVENT @ 2026-04-25, within_48h=True stale) → 跑 bridge → data.json 含該筆，within_48h 自動修正為 False ✓
- 清理測試事件 → 61 筆 ✓

**檔案**：`bridge.py` (+~50 行：`EVENTS_ARCHIVE_FILE` const + `_load_events_archive` / `_save_events_archive` + 改 `aggregate_upcoming_events`) / `.gitignore` (+1 行)

**前端不用改** — calendar 已經會在過去日期 cell 渲染 chip（v1.53.4 改的 `cal-cell-events` 對 past dates 也有效），只是過去 archive 沒餵資料。

VERSION 1.54.0 → **1.54.1**（patch — bug fix 性質：原本就應該 persist 但漏了）。



## 🟢 Session Note (v1.54.0) — 決策日曆 filter bar（preset + 三維 toggle）

把 v1.53.4 的「Sources / Verdicts」靜態 legend 改成 **互動 filter bar**，新增 Events 維度：

**4 row layout**：
1. **Mode**：3 個 preset 按鈕
   - `All` — 全部開（預設）
   - `Analysis` — 只看過去決策（all sources + verdicts on，events off）
   - `Up-Event` — 只看未來事件（sources + verdicts off，all events on）
2. **Sources**：9 個來源各自 toggle（deep-dive / sector-scan / news / theme / momentum / radar / earnings / weekly / postmortem）
3. **Verdicts**：5 個判讀各自 toggle（hit / miss / neutral / pending / n/a）
4. **Events**：7 個 category（earnings / Fed/macro / econ / binary / geo / watchlist / system）

**過濾邏輯**：
- Decisions：`source ∈ activeSources AND verdict ∈ activeVerdicts`（兩維 intersect，內部 OR）
- Events：`category ∈ activeEventCats`（獨立維度）
- 任一 set 為空 → 該類別全部不顯示（這正是 preset 切換 events-only / analysis-only 的機制）

**互動**：
- 任何 pill 或 preset click → 立即 `rerenderAll()`：grid + aggregate 同步更新
- 當 filterState 與某 preset 完全一致 → 該 preset 顯示綠色 active 邊框
- 用戶手動 toggle 某個 pill 後 → preset active 自動消失

**檔案**：`calendar.html`（替換 legend block）/ `page-calendar.js`（+~150 行：filterState、applyPreset、toggleFilter、rebuildFilterBar、wireFilterBar）/ `style.css`（+~120 行：`.cal-filterbar` / `.cal-filter-pill[.is-on]` / `.cal-filter-preset[.is-active]`）

驗證：dashboard server (port 8080) 已在跑，refresh `http://localhost:8080/calendar.html`，預設應看到所有 pill 綠色 on，All preset active；點任一 pill 立即看到 calendar grid 對應日期的 chip 消失/出現。



## 🟢 Session Note (v1.53.4) — 決策日曆 events 內聯到儲存格

User 反映 FMP 整合後 `upcoming_events` 暴增到 61 筆 / 12 dates（最高一天 19 筆），右側「即將發生」rail 太長。

**處理**：
- 把 events 用 **category-grouped chip** 形式塞回每格儲存格底部，與決策指標 (`cal-badge-row`) **分行**：
  - 每格按 category 群組，顯示 icon + count（例：💼3 📊5 ⚠1）
  - binary / high impact 用紅 / 黃 tinted 樣式凸顯
  - 最多顯示 4 種 category，超過 +N 收尾
  - hover 顯示完整 title list（含 ticker prefix）
- 右側 rail panel `cal-upcoming-rail` 加 `hidden` class（保留 DOM 與 `renderUpcoming()` 不刪，未來要恢復改一個 class toggle 就好）
- `cal-main` grid 從 `lg:grid-cols-[1fr_280px]` 改成單欄全寬
- Drawer 點擊任一格時，事件 section 渲染在 decisions section **之前**（重用 `renderUpcomingCard()` 不重寫）
- CSS 新增 `.cal-cell-events` (`margin-top: auto` 推到底部) + `.cal-cell-event-chip` 三色變體 (`-high` / `-binary` / 預設)

**檔案**：`page-calendar.js` (+~80 行) / `calendar.html` (2 處小改) / `style.css` (+~60 行新樣式)

驗證方式：dashboard_server (port 8080) 已在跑，refresh `http://localhost:8080/calendar.html` 即可看到新 layout。



## 🟢 Session Note (v1.53.3) — ARCHITECTURE_DIAGRAM.md 重寫為 4 視角

原本一張平鋪 5 層 DAG，user 反映「mermaid 不太好懂、call stack 看不出時序」。重寫成 4 個視角各解一個問題：

- **A. 系統地圖**：保留 flowchart 但加 subgraph 分層 + 觸發點顏色標記（藍=自動 / 綠=用戶 protocol / 橘=手動工具）+ 粗線 / 虛線 / 細線區分觸發鏈、Skill 呼叫、cache 寫入。
- **B. Tier 1 daily pipeline 時序**：sequenceDiagram 顯示 Step 1-6 的順序、寫哪個 cache、bridge 怎麼吃進去。
- **C. Tier 2 三大 protocol call stack**（Sector V1.4 / Investment V4.8 / News V2.1）：sequenceDiagram 顯示 Phase 順序 + subagent 平行 fan-out（`par`/`and` block）+ 各 phase 讀寫的檔案 + 關鍵紀律。
- **D. Bridge 聚合表 + Cache 目錄樹 + Skill 依賴表**：解「data.json 某欄位是哪來的」、「某個 cache 在哪」、「哪些 skill 在哪個 phase 平行/序列」。

加碼：失敗診斷小抄（症狀 → 先看哪），把 BUG-002 atomic write、BUG-006 ftd_status_text 等紀律寫進來，下次出問題能快速定位。

454 行（從 103 行擴 4×）。



## 🟢 Session Note (v1.53.2) — BUG-006 修補 + FRED fetch.py None 比較 fix

**兩個 bug，當天解：**

### 1. `skills/fred-macro/scripts/fetch.py:1054` TypeError
`hy_pct = rs.get("credit_spread_pctile_1y", 50)` 在 key 存在但值為 `None` 時 `dict.get` 不會回 default，導致 `hy_pct > 45` 比較炸掉。改成 `rs.get(...) or 50`。`daily_update.sh` Step 4 解鎖。

### 2. BUG-006 — sector_protocol FTD day-counter 幻覺
Gemini 報「4/22 報告抄 4/21 範本，忽略 breadth 36.8 → 42.4」。實際根因不一樣：
- Breadth 4/21=42.4 / 4/22=42.4 是因 TraderMonty CSV 上游早上沒更新（晚上才有 4/21 收盤），不是 AI 抄。
- 真正幻覺：4/21 報告寫 "FTD Day 14"，4/22 寫 "FTD day 6" — 兩天 AI 抓 ftd_cache 不同欄位（`current_day_count` vs `quality_score.breakdown.base "Day 6 FTD"`）。

**修法 V1.5 schema bump**：
- `sector/ftd_yfinance.py` 加 `ftd_timeline` block（含 `ftd_status_text` canonical 字串 + `days_since_ftd` / `rally_day_count` / `ftd_day_number` 三個明確 day-counter + `_help` 註解）
- `sector/phase_0.md` 層 C 加反幻覺規則（必引用 `ftd_status_text` 原文）
- `sector/schema.md` Phase 0 / Phase 5 ftd block 補新欄位

**驗證輸出（4/26 跑）**：
```
FTD Timeline: FTD CONFIRMED, day 12 post-confirmation (rally-day 18; FTD originally confirmed on rally-day 6)
```
ftd_date 4/8 + 12 trading days = 4/24 ✓；rally_low 3/31 + 18 trading days = 4/24 ✓

**後續觀察**：4/27 跑 sector_protocol 時看 AI 是否引用新 `ftd_status_text` 原文；如果還寫成「FTD Day N」要再強化 phase_4-5.md 內的 prompt 引用語法。



## 🟢 Session Note (v1.53.0) — News Driver v0.2.1（兌現 Finnhub /company-news + sentiment）

從 v1.46-v1.52 的 News driver 一直是 v0.1 volume/gap proxy（雖然 SKILL.md / global_warnings 一直寫「v0.2 will integrate Finnhub」）。User 提醒後實作。

**Method 4 個方案評估**：
1. Pure keyword（粗糙）
2. Keyword + magnitude + negation（finance-tuned，0 cost）— 採用
3. Finnhub `/news-sentiment` endpoint — 測試 **403 premium-only 不能用**
4. LLM scoring — $1-2/day cost，先不上

**v0.2 第一版實作後 5-ticker test 找到 5 critical bug**：
- NVDA 248 articles 多數 tangentially-related 噪音（"Walmart's investment in Mexico" 被當 NVDA news）
- 問句被當 sentiment claim（"Is X a Buy?" → +0.5）
- "Lockheed Martin Shares Are Falling" 沒抓到（"falling" 不在詞庫）
- "Insiders Sold Suggesting Hesitancy" 沒抓到
- 248 articles 全平均 → 訊號被噪音稀釋

**v0.2.1 修正**：
1. **Headline relevance filter**：Finnhub profile 抓 company short name → 標題沒有 ticker 也沒 short name → 過濾
2. **問句 ×0.5**：標題含 `?` 或 `Is/Why/Should/Will/Can` 開頭 → score halved
3. **Cap top 20 by recency**
4. **+25 個新詞彙**：falling/hesitancy/flopped/buyback/dividend cut/sluggish 等
5. **Source blacklist**：simplywall.st / fool.com / zacks.com

**測試結果（v0.2 → v0.2.1）**：
| Ticker | v0.2 | v0.2.1 | 變化 |
|---|---|---|---|
| NVDA | 248→+0.152 | 20 of 249→+0.250 | 噪音砍 92% |
| LMT | 47→-0.011 | 20 of 92→-0.045 | 抓到 Q1 miss |
| LLY | 36→+0.033 | 10 of 49→**-0.055** | **翻轉成負**（GLP-1 壓力） |
| JPM | 42→+0.031 | 1 of 52→-0.040 | 41 篇 commentary noise 砍 |

**Fallback 設計**：Finnhub 失敗或無相關文章 → 降回 v0.1 proxy + warning 標明

**整合**：predict.py 主流程自動用 v0.2.1（清 cache 後第一輪 fresh prediction 都用新算法）。daily_update.sh thematic-screener 跑時自動生效。

**已知殘留小 bug**（v0.2.2 修）：
- "Why X Flopped" 顯示 +0.25 應 -0.25（summary 某詞蓋過 — 待 trace）
- 動詞變化漏：slips / lag / lags 詞庫沒有

## 🟢 Session Note (v1.52.0) — Radar v0.4: ETF holdings universe + auto-refresh

修正 user 點出來的兩個 fundamental issue：(1) static_stocks 只有手選 10 個 → universe 太窄、(2) 「top 5」semantic 錯（top 5 of 10 不是 top 5 of universe）。

### 核心改動：ETF holdings 取代手選 universe

**之前**：每主題 themes.yaml 寫死 10 個我手挑的 static_stocks
**現在**：每主題的 proxy_etfs (e.g. SOXX/QTUM/BOTZ) 抓 yfinance top 10 holdings → 跨 ETF dedup → 過濾非美股 → cap 25 → 寫進 themes.yaml

結果：
- 270+ 個 unique US-tradeable tickers（vs 之前 171）
- 17 主題從 10 → 16-25 stocks
- 4 主題真實 universe 小（保留 5-12）：Gold, Uranium, Real Estate, Utilities Defensive
- Quantum 17 stocks，**重疊 0** vs 我手選名單 → 證明 ETF 比手選代表性高

### 新增基礎設施

- **`skills/thematic-screener/scripts/refresh_etf_holdings.py`**（150 行）：完全自動化 — 用 yfinance 抓 ETF top holdings、dedup、過濾非美股、寫回 themes.yaml + bump etf_meta.yaml `last_refreshed` timestamp
- **`skills/thematic-screener/etf_meta.yaml`**：紀錄 last_refreshed + summary stats
- **`daily_update.sh` Step 5.5**：每天檢查 etf_meta，60 天內 fresh 顯示 ✅，60-90 天黃色提示，**90 天自動觸發 refresh + 同步重跑 theme-detector**

### Refresh 自動化頻率（per user 確認）

90 天自動 refresh 對應 ETF rebalance 季度週期。ARK 系列雖可日動但 top 25 一季內幅度<5 個是常態 → 90d 是合理 cadence。
**完全本地、0 token 成本**（yfinance 免費 + Python 腳本，不調 LLM）。

### 真實 breadth 結果驗證

```
AI & Semiconductors             N=22  95% bullish (21/22) — 真強勢
Financial Services & Banks      N=25  80→84→88% — 漸強
Defense & Aerospace             N=18  33→38→44% — 短空長中性
Oil & Gas (Energy)              N=25  32→36→36% — 失寵
Utilities Defensive             N=12  41→50→50% — 中性偏空
```

對比 v0.3：之前 top-5 預先 selection → 多數主題假性 100% bullish。現在跨 universe 平均，breadth 真實反映「主題內多少股看多」。

### 工作流程
- **每天**：daily_update.sh 自動跑 → etf_meta < 60d 顯示綠燈、< 90d 黃燈、≥ 90d 自動 refresh
- **使用者 0 維護**：完全 set-and-forget；季度自動 refresh
- **Manual override**：`python3 skills/thematic-screener/scripts/refresh_etf_holdings.py --top-n 25` 隨時可跑

### 延後的事
- **primary_theme tagging（解重複）**：原 plan 的 step 5 還沒做。NVDA 仍同時在 AI/Quantum/Robotics 都算。等使用 1-2 週看是否 visually 困擾再決定要不要做
- **動態 ETF API**：v0.5 才考慮（手動 quarterly refresh 已夠用）

## 🟢 Session Note (v1.51.0) — Radar v0.3 horizon switcher + breadth 算法修正

兩個 user feedback 觸發的 critical 修正：

### 1. Breadth 算法 bug 修正（嚴重）
**之前**：bullish_breadth_pct 是基於「top 5 movers」算的 → 都被 ranked by score×conv 預先 selected → 必然 100% bullish 大概率 → metric 失去意義
**修正**：改成對主題的**全部 representative_stocks (10 名)** 算 breadth → 得到真實「主題內多少股看多」

修正後例：
- Defense & Aerospace: 1d 10% (1/10) → 5d 20% (2/10) → 15d 30% (3/10) — **真實短空長多 pattern**
- Robotics: 100% (9/9) all horizons — 真強勢
- Cybersecurity: 66% → 77% → 88% — 漸強
- Cloud: 40% → 50% → 50% — 混雜
- Obesity & GLP-1: 22% → 33% → 44% — 短期偏空

### 2. 1d/5d/15d Horizon Switcher
- screen.py `compute_theme_short_term` 重寫：回傳 `{n_total_constituents, primary_horizon, by_horizon: {1d/5d/15d: {bullish_breadth_pct, avg_conviction, n_valid_predictions, n_bullish, mean_target_pct}}, components}`
- page-radar.js 加 `_currentHorizon` state + 3 個 button (1d / 5d ★ / 15d)
- Theme card 顯示「SHORT bull [5d] 80% (8/10)」格式 — 含當前 horizon 標示 + bullish/valid 計數
- 切換 horizon 自動重排 + 重 render

### 3. 額外 polish（同輪）
- Tooltip CSS 改用 theme variables (`var(--bg-card)`、`var(--text-main)`、`var(--secondary)` 等) → light/dark 自適應
- Cursor 從 `cursor: help` 改 `inherit`（不再變問號游標）
- Theme card 多顯示「constituents: N」讓 user 知道分母是多少

**Output schema 變化**（v0.3 vs v0.2）：
- `short_term.bullish_breadth_pct` → `short_term.by_horizon.<h>.bullish_breadth_pct`
- 加入 `n_total_constituents`、`n_valid_predictions`、`n_bullish` 透明化分母

**plan_short.md 全進度**（**整套 v0.3 production**）：
- Step 1-7 ✅ + 文件 ✅ + Step 4 v0.1 dual-section ✅ + v0.2 all-themes-grid ✅ + **v0.3 horizon switcher + breadth 修正 ✅ v1.51.0**

## 🟢 Session Note (v1.50.0) — Tactical Radar v0.2 重設計（all themes grid + regime layer + predict cache）

User feedback「不直覺」+「想看全部主題 + 點開 movers」+「regime 是市場主導力」的 3 個訴求一次落地。

**結構性重設計**：
1. **Theme runtime sync**（修我之前 Step 2 的 bug）：themes.yaml + default_theme_config.py 同步加 5 個新主題（Nuclear Energy / Uranium / Space Economy / Quantum Computing / Robotics & Automation / Utilities Defensive / Obesity & GLP-1），15 → 21 themes
2. **Theme-detector 重跑**：max-themes 25 → 偵測到 20 主題（含 5 個新加 + 4 auto-discovered sector concentration）
3. **predict.py 加 4h cache**：cache hit 1.7s → 0.4s。171 unique tickers 全跑也只需單次（之後 4h 內全 hit）
4. **screen.py v0.2 重寫**：
   - 移除 top_themes 限制 → **顯示全部 20 主題**
   - 每主題加 short_term { bullish_breadth_pct, avg_conviction, components }
   - 加 regime layer：2 獨立 badges (RSI + VIX) + factor (取 max 偏離度)
   - regime factor 自動 dampen bullish_breadth (今天 0.9× 因為 SPY RSI 87)
   - 排序預設 by short bullish_breadth_pct desc
   - 同時收集 components 欄位給 v0.2 後續用
5. **radar.html v0.2**：grid 6 cols + sort toggle (Short/Mid) + regime badges 區 + expanded movers panel
6. **page-radar.js v0.2**：~360 行重寫，theme grid 點擊展開單一主題 movers，sort 即時切換，badges 中英雙語

**Regime layer 設計**（per user 確認 2 badges + 1 factor）：
- RSI > 85 → 「極端超買 — mean reversion 風險」(factor 0.90)
- RSI < 25 → 「極端超賣 — 反彈燃料」(factor 1.10)
- VIX > 25 → 「緊張 — caution」(factor 0.92)
- VIX > 35 → 「恐慌 — 防禦」(factor 0.85)
- VIX > 40 → 「投降底 — contrarian buy」(factor 1.15)
- 取「max 偏離度」當 factor，不 double-count

**今天實際狀態**（驗證 4 象限）：SPY RSI 87.4 + VIX 18.7 → 「**複雜頂**」象限
- ✅ RSI badge fired: "SPY RSI 87.4 極端超買"
- 🟢 VIX badge silent (VIX 18.7 沒進極端區)
- 數字 factor: 0.90 (rsi_87_overbought)

**Bridge 注入結構**：data.tactical.{themes[20], regime_snapshot, regime_badges, regime_factor, screener_params}

**設計分區決定的修正**：
- 之前 Step 4 的「2 分區強迫看」改成「1 grid + click 展開」(per user 不直覺反饋)
- Movers 不再預設展開，使用者主動點才看詳細
- Cool 主題 (mid_heat < 30) 透明度 0.7 區分但不隱藏（per user「全部顯示」訴求）

**plan_short.md 全進度**：
- Step 1-7 ✅ + 文件刷新 ✅ + Step 4 v1（雙分區）✅ → **v0.2 全 grid 重設計 ✅ v1.50.0**

整套 Tactical Opportunity Radar v0.2 production-ready。

## 🟢 Session Note (v1.49.0) — plan_short Step 4 完成（Dashboard「短期雷達」頁）

落地 Tactical Opportunity Radar 的視覺化層。**plan_short.md 全部 7 個 Step 完成**。

**架構決策**：
- 走方案 B：**新頁面 `radar.html`**（不擴充 momentum）— sidebar 加「短期雷達」icon=radar
- 走方案 A 資料流：**`bridge.py` 注入 `data.tactical` sub-key**（單一 fetch，不破壞既有 data.json 模型）
- 桌面 only，預設展開第 1 個主題卡

**完成檔案**：
- `bridge.py` +35 行：`load_tactical_recommendations()` + 注入 `data["tactical"]` + import time
- `Dashboard/utils.js`：NAV_ITEMS 加 radar entry
- `Dashboard/i18n.js`：zh/en nav.radar + 完整 radar 頁面字串（~40 entries × 2 langs）
- `Dashboard/style.css` +120 行：experimental-badge / regime-banner / heat-bar / horizon-bar / driver-row / invalidation-box / concentration-warning / confidence-breakdown 等 radar 專屬類別
- `Dashboard/radar.html`（85 行 NEW）：頁面骨架 — header + EXPERIMENTAL badge + regime banner + section A (主題卡) + section B (movers)
- `Dashboard/page-radar.js`（260 行 NEW）：render 邏輯 — 嚴格遵守 plan_short §11.D 顯示規則（range / confidence / drivers / invalidation / concentration / trading_meta 全顯示）

**§11.D 顯示規則檢核**（強制）：
- ✅ EXPERIMENTAL badge（橘色，header 內）
- ✅ Range（每個 horizon 都顯示 $low – $high，不只 mid 點）
- ✅ Confidence + breakdown（collapsible，7 contributors 展開）
- ✅ Drivers（4 sources：news / sector / momentum / atr）
- ✅ Invalidation box（紅色左 border）
- ✅ Concentration warning（橘色左 border，列出 co-recs）
- ✅ Trading meta（stop / pos% / tx / exit trigger）
- ✅ FRED regime banner（頂部，含 SPY/RSI/VIX/yield curve/credit spread）
- ✅ 累積天數提示（header）+ KPI gate hint

**Smoke test**：
- node syntax 通過
- HTML id 全 18 個 ✓ 對應 JS reference
- bridge.py 注入成功：`tactical.status: success / 3 themes / 9 movers`
- Dashboard server 已在跑（pgrep 確認）

**plan_short.md 全進度**：
- Step 1 short-term-target ✅ v1.46.0
- Step 2 4 themes ✅ v1.46.1
- Step 3 thematic-screener ✅ v1.47.0
- Step 5 outcome log（Step 3 內含）✅ v1.47.0
- Step 6 daily_update.sh 整合 ✅ v1.48.0
- Step 7 weekly_review.py ✅ v1.48.0
- 文件刷新 ✅ v1.48.1
- **Step 4 Dashboard「短期雷達」 ✅ v1.49.0 ← 全 plan 收尾**

整個 Tactical Opportunity Radar v0.1 系統 production-ready。

## 🟢 Session Note (v1.48.1) — 文件刷新（README.md + CLAUDE.md）

把短期戰術層的整套變更**反映到使用者日常文件**。

### README.md 改動
- **頂部**：新增「三層時間維度設計」說明（長期/中期/短期）
- **常用指令表**：加 description 欄位、補 `動能 [TICKER]`
- **每日工作流程**：從原本 4 step 重寫成 **Tier 1/2/3/4 結構**：
  - Tier 1 自動：daily_update.sh 6 step（含新 Step 6 thematic-screener）
  - Tier 2 每日手動：開 Dashboard / 看 recommendations / 視需求做深度分析
  - Tier 3 每週末手動：weekly_review.py
  - Tier 4 不定期：分析、產業掃描、dual_fetch、postmortem 等
- **腳本用途速查（新增）**：4 個分類 × 共 ~20 個 .py 一覽，每個含「用途」「觸發」
- **Tactical Opportunity Radar 章節（新增）**：架構圖 + 與既有系統關係表 + KPI gate

### CLAUDE.md 改動
- **Protocol Triggers 表**：標註 V4.8.1 dual_fetch + 各 protocol 內容
- **新增「Tactical Opportunity Radar」section**：說明戰術層自動產出位置 + 紀律「不影響 protocol 決策、永不自動覆寫 config」
- **Ops Shortcuts**：從單行擴成 4 個常用指令（含 weekly_review、predict、dual_fetch、audit_drift_check、backtest_postmortem）

### 今日完整 plan_short 進度
- Step 1 short-term-target ✅ v1.46.0
- Step 2 4 themes ✅ v1.46.1
- Step 3 thematic-screener ✅ v1.47.0
- Step 5 outcome log（Step 3 內含）✅ v1.47.0
- Step 6 daily_update 整合 ✅ v1.48.0
- Step 7 weekly_review.py ✅ v1.48.0
- **文件刷新 ✅ v1.48.1**
- Step 4 Dashboard ⏳ 唯一剩下

## 🟢 Session Note (v1.48.0) — plan_short Step 6 + Step 7（自動化 + 週末校準工具）

把每日推薦生成自動化 (Step 6) 並建立每週手動校準工具 (Step 7)。**day-1 logging 機制現在每天會自動運轉**。

### Step 6 — `daily_update.sh` 加入 thematic-screener
新增第 6 步驟：
- 檢查 `theme-detector` cache 存在性 + 新鮮度（> 7 天 → 跳過警示，不報錯）
- 用 `set +e` 包覆 thematic-screener 執行，**失敗不中止整體 daily flow**
- 顯示輸出檔大小確認成功
- 加提示「每週末跑 weekly_review.py」

### Step 7 — `skills/short-term-target/scripts/weekly_review.py`（330 行）

每週末手動跑，**不自動覆寫任何 config**。輸出 `reports/SHORT_TERM_WEEKLY_<DATE>.md` 含：
1. **Per-horizon 統計**：1d / 5d / 15d 各別 hit rate / in-range / mean error / directional bias
2. **Per-theme 5d alpha 分解**：哪個主題的推薦最準 / 最不準
3. **Worst 5 cases**：最大絕對誤差案例 + driver 細節
4. **Suggested adjustments**：基於 hit rate 與 bias 的具體建議（reduce α/γ 等）
5. **KPI gate**：對照 plan_short §6 + §12.H 的失敗判定（hit rate < 50% AND mean alpha < 0% on N≥30 → 整套退役）

**重要紀律**：Tool 只給建議，**完全由使用者決定**要不要 edit `config/weights.yaml`。每次調整需手動 bump `weights_version`，未來預測自動 tag 版本，可做 before/after 比較。

### Smoke test
- `daily_update.sh` syntax check 通過
- `weekly_review.py` 跑通：找到 1 個 recommendations file（今天的），0 預測達到 evaluation window（horizons 都還沒到期）→ 正確顯示 "No outcomes available" graceful message

### plan_short.md 進度
- Step 1（short-term-target）✅ v1.46.0
- Step 2（4 themes）✅ v1.46.1
- Step 3（thematic-screener）✅ v1.47.0
- Step 5（outcome log）✅ v1.47.0（內含於 Step 3）
- **Step 6（daily_update 整合）✅ v1.48.0**
- **Step 7（weekly_review tool）✅ v1.48.0**
- Step 4（Dashboard）⏳ 唯一剩下

### 系統現狀（每天運轉中）

```
每天 daily_update.sh:
  Step 1-5 (廣度/FTD/Top/FRED/bridge) — 既有
  Step 6 thematic-screener → data/recommendations/<DATE>.json — 新增

每週末手動:
  python3 skills/short-term-target/scripts/weekly_review.py
  → reports/SHORT_TERM_WEEKLY_<DATE>.md
  → user 決定是否 edit weights.yaml + bump weights_version
```

從今天起，每跑一次 daily_update.sh 就累積一筆推薦樣本。**約 7-10 天後 1d/5d 就有可評估資料；3-4 週後達到 N≥30 KPI gate 門檻**。

## 🟢 Session Note (v1.47.0) — thematic-screener skill v0.1（plan_short Step 3 + Step 5 內含）

新增 `skills/thematic-screener/` — Tactical Opportunity Radar 的聚合層，把 theme-detector（中期主題熱度）與 short-term-target（1d/5d/15d 個股預測）串成每日推薦輸出。

**架構決策**：
- **Subprocess 呼叫 short-term-target**（不 import） — 保持 skill 獨立性。N×M tickers × ~5-15s/call 是可接受的日 cadence
- **Theme-detector 已提供 `representative_stocks` per theme** — 不需 parse cross_sector_themes.md
- **Concentration 是 WARNING 不是 REMOVE**（per §11.B 修正）— 同主題 ≥2 picks → 加 flag 但都保留，使用者決定
- **無 FRED → theme scoring**（per §12.E 硬版拒絕）— 只記錄 FRED 狀態到 regime_snapshot
- **Day-1 outcome log 寫入機制**（per Step 5）— 每次 run 寫 `data/recommendations/<DATE>.json`，含完整 regime context (SPY/RSI/MA50/VIX/FRED)，未來 Step 7 weekly_review 可直接 cross-tab

**完成檔案**：
- `scripts/screen.py`（230 行）— 主聚合腳本
- `SKILL.md` / `README.md` / `CHANGELOG.md`
- `data/recommendations/.gitignore` + `cache/.gitignore`

**Smoke test**（2x2 = 4 calls，~30s）：
- ✅ theme-detector cache 載入正確
- ✅ Top 5 themes 排序正確（Clean Energy 67.4 / Defense 66.0 / Materials 64.3）
- ✅ short-term-target subprocess 對每個 ticker 回傳完整 JSON
- ✅ concentration_flag 觸發正確（同主題 2 picks → 都標警示）
- ✅ regime_snapshot 完整（SPY=713.94 RSI=87.4 VIX=18.71 FRED=expansion）

**真實 run**（3x3 = 9 calls，~90s）：成功寫入 60KB recommendations log

**plan_short.md 進度**：
- Step 1（short-term-target）✅ v1.46.0
- Step 2（4 themes）✅ v1.46.1
- **Step 3（thematic-screener，含 Step 5 log writer）✅ v1.47.0**
- Step 4（Dashboard 兩分區）⏳
- Step 6（daily_update.sh 整合）⏳
- Step 7（weekly_review.py）⏳

**值得注意**：今天 SPY RSI 87.4 是極端區。所有今日推薦的 regime context 都記錄了這個事實，未來 backtest 可以分析「在 SPY RSI > 80 時，模型表現如何」這類問題。

**設計亮點 — Day-1 logging 已運轉**：
從這一刻起，每次 thematic-screener 執行（手動或未來 daily_update.sh 自動）都會留下完整的「當下推薦 + 當下市場狀態」紀錄。3-4 週後就有 N≥30 樣本可供 Step 7 weekly_review 評估。**這比「先做 7 個 step 再驗證」省 3-4 週**。

## 🟢 Session Note (v1.46.1) — plan_short Step 2 完成（4 個新主題）

`cross_sector_themes.md` 17 → **21 主題**。實作前盤點發現原計畫的 6 個新主題實際只該加 4 個：
- **Nuclear Energy 已存在**（既有第 15 主題，含 CCJ/CEG/VST/OKLO 等）→ skip
- **Healthcare Defensive 與既有 Healthcare & Pharma 重複**（UNH/JNJ/LLY/PFE 已涵蓋）→ skip

**新增主題**：
- **Space Economy**（從 Defense 拆 RKLB；ROKT/ARKX/UFO ETFs；14 名）
- **Quantum Computing**（IONQ/RGTI/QBTS/QUBT pure-plays + IBM/GOOGL/MSFT/NVDA mega-cap dilution；11 名；標明 pure-plays ATR ~8%）
- **Robotics & Automation**（ISRG/TER/ONTO/ABBN/FANUY/ROK；BOTZ/ROBO/IRBO/ARKQ ETFs；15 名）
- **Utilities Defensive**（NEE/DUK/SO/AEP/XEL；XLU/IDU/VPU/FUTY；15 名；明示與 Nuclear Energy 區別 — Nuclear 是 offense，這個是 defense）

**附帶調整**：
- Defense & Aerospace 移除 RKLB（補 TXT），ETFs 從 4 → 2（ROKT/ARKX 移到 Space）
- Overlap Matrix 加 8 行（含 BWXT 三重歸屬：Defense + Nuclear + Space 都正確）
- Summary Table N=21

**plan_short.md 進度**：
- Step 1（short-term-target）✅ v1.46.0
- Step 2（4 themes）✅ v1.46.1
- Step 3-7 ⏳

## 🟢 Session Note (v1.46.0) — short-term-target skill v0.1（plan_short Step 1）

承接從 backtest 反思 + Gemini/ChatGPT 雙 review 整合的 plan_short.md，落地 Step 1：建立 `skills/short-term-target/` skill 提供 1d/5d/15d 短期目標價預測（"Tactical Opportunity Radar" framework）。

**架構決策（從 plan_short 帶入）**：
- 每 horizon 獨立權重（1d news-heavy、5d momentum-heavy、15d sector-persistence-heavy），不共用 α/β/γ
- Hard clamp（1d ±5%、5d ±15%、15d ±30%）防冷啟動爆走，clamped 預測 confidence 自動 -0.15
- Confidence breakdown 7 項貢獻全透明，sum 等於 final
- Benchmark-relative output（ETF realized + implied_alpha），預設 SPY
- Refuses to fabricate：source 過舊 → `status: insufficient_data` 含 missing/would_need
- Trading meta（stop = 1.5×ATR、pos% = 0.33/ATR%、tx_cost、exit_trigger）
- weights.yaml 手動編輯，每次調整 bump weights_version（搭配未來 Step 7 weekly_review）

**完成**：
- `skills/short-term-target/scripts/predict.py`（385 行）— 主腳本含全部上述規則
- `skills/short-term-target/config/weights.yaml`— 可手動編輯參數
- `skills/short-term-target/SKILL.md`— 形式 spec
- `skills/short-term-target/README.md`— 使用 + 詮釋指引
- `skills/short-term-target/CHANGELOG.md`— v0.1.0 紀錄含 smoke test 結果
- `cache/`、`data/` 目錄含 .gitignore

**Smoke test（3 ticker，全通過）**：
- AMD（Stage 2 + 量增）：1d conf 0.59、5d target +3.28%、News 抓到 +13.9% gap
- CEG（低波動 utility）：1d conf 0.61、5d +1.52%、預測平緩
- IONQ（高波動 quantum，ATR 8.18%）：1d conf 0.17、15d conf 0.03（"沒意見"）— 高 ATR 自動降信心驗證 OK

**plan_short.md 進度**：
- Step 1（short-term-target）✅ 完成（v1.46.0）
- Step 2（4-6 個新主題到 cross_sector_themes.md）⏳
- Step 3（thematic-screener skill）⏳
- Step 4（Dashboard 兩分區）⏳
- Step 5（outcome tracking log）⏳
- Step 6（daily_update.sh 整合）⏳
- Step 7（weekly_review.py 手動 recalibration tool）⏳

**v0.1 已知限制**（README 已詳載）：
- News driver 是 volume/gap proxy，非真實 Finnhub /company-news（v0.2 升級）
- GICS sub-industry lookup 未做，benchmark 全部 default SPY
- 沒做 cache layer，每次 hit yfinance
- dual_fetch consumption 是 best-effort（read 不到不報錯）
- 未做 outcome 驗證（從 day 1 累積 + Step 7 評估）

**設計帶入的 backtest lessons**：
- News lane r=+0.373 的發現 → 1d horizon 給 news 0.6 最高權重
- 高 ATR 在 backtest 中是 outcome 變異最大來源 → 直接做進 confidence penalty
- 「不要在 1 個 regime 上過擬合」 → 整套設計接受失靈 + Step 7 手動 recalibration（user 拍板）

## 🟢 Session Note (v1.45.0) — Investment Protocol V4.8.1 Dual-Fetch 整合

把 v1.44 的 dual_fetch 接進 `investment_protocol_v4_8.md`。設計討論時排除了兩個明顯路線（Phase 1 加 subagent 做判斷 / 4 個 Phase 2 subagent 各自 call dual_fetch），採第三路：**PM inline 一次抓、4 個 subagent 共享 snapshot**。理由：(1) 同 session 同 snapshot，cross-lane 資料一致；(2) 不增 subagent，Phase 1 維持輕量；(3) `_audit.*` 隔離紀律集中守在 PM 一處 paste 動作。

**完成**：
- **`investment_protocol_v4_8.md` Phase 1**：新增「Phase 1 資料層 (V4.8.1)」段落，PM MUST 執行 `run_dual_fetch.sh`、讀取 `bundle["scoring"]`、絕對禁止讀寫 `_audit.*`（違反→當前 ticker 作廢、重啟 Phase 1）
- **Phase 2 共通 prompt 模板**：在 PHASE 0 MACRO CONTEXT 之後插入 `TICKER DATA BUNDLE` 段落（與 macro 同樣 read-only / shared-across-analysts 的 pattern）
- **Fundamentals subagent rubric**：新增 9 scalar 使用規則。重點：
  - bundle 為 9 欄位權威來源；與 us-stock-analysis 衝突 > 1% 採 bundle 並註記原因
  - `priceToBookRatio` 視為近似值，估值權重低於 P/E（已知跨 provider 10-30% 差）
  - `dividendYield` 單位 = percent / indicated annual（前瞻）
  - bundle 缺欄位 → 用 us-stock-analysis 補；皆無 → 排除於評分，不得猜
- **`investment/README.md`**：開頭新增 V4.8.1 增量變更段落
- **失敗模式**：FMP audit 失敗（quota / 401 / 403）不算失敗，scoring 仍完整；只有 Finnhub 全失敗才標 `data_bundle_available: false`，subagent 走 fallback

**未做（暫不動）**：
- 不修改 `us-stock-analysis` skill 內部 fetch 邏輯（仍會自己抓 FMP）。當前 bundle + skill 雙抓共存，由 subagent 在 prompt 規則裡仲裁衝突。未來可優化為 skill 接受 `--data-bundle` 參數跳過自抓
- 其他 3 個 lane（Sentiment / News / Technical）資料需求與 bundle 9 個 scalar 不重疊，本次不變更
- 未跑端到端 protocol 測試（需要使用者實際 `分析 [TICKER]` 才能驗證 PM inline 是否正確執行 dual_fetch）

## 🟢 Session Note (v1.44.0) — Finnhub Dual-Fetch + Audit Drift Monitor

承接 v1.43 的 diff 結果，把「驗證工具」升級成「常態雙抓 + 物理隔離」。先用 diff_tool 跑出 FMP stable 端點問題（v3 全 403、QQQ 402、`key-metrics-ttm` 欄位搬到 `ratios-ttm`、`peNormalizedAnnual` 與 `peTTM` 定義不同），逐一修完後得到完整 diff 報告，發現 `dividendYield` 5-7% 與 `priceToBookRatio` 12-38% 是**結構性方法論差異**，不是哪家錯。

**架構決策**：採用「Finnhub canonical, FMP audit」雙抓設計而非 fallback。理由：fallback 會讓同一支股票今天用 Finnhub、明天 quota 切 FMP 時 scoring 漂移、且漂移無法歸因；雙抓則保證 scoring 永遠來自 Finnhub（可重現），同時 FMP 平行抓取保留觀測能力（drift monitoring）。物理隔離靠 `_audit` 底線前綴慣例，禁止進入 LLM prompt。

**完成**：
- **`scripts/dual_fetch.py`（200 行）**：library + CLI 雙模式。輸出 `data/YYYY-MM-DD/{TICKER}.json`，頂層 `scoring`（Finnhub）+ `_audit`（FMP + diff + status）
- **`scripts/audit_drift_check.py`（110 行）**：掃過去 N 天 audit 紀錄，找出 `(ticker, field)` 在 >= MIN_HITS 天內 diff 超過 threshold 的持續性漂移，輸出 markdown 報告
- **`scripts/run_dual_fetch.sh`**：wrapper（檢查兩個 API key）
- **`README.md`**：三 script 用法（dual_fetch 日常 / audit_drift_check 週檢 / diff_tool 一次性 spot check），含 fmp_status 對照與 library 用法
- **`CHANGELOG.md`**：v1.1.0 紀錄含架構決策表
- **`SKILL.md`**：新增 § Dual-Fetch Discipline，明訂 `_audit.*` 不得進 prompt 的硬規則；Architecture Role 表把 simple metrics 從 TBD 改成 Finnhub canonical + FMP audit
- **修正 `diff_tool.py` + `adapters.py`**：v3 → stable 端點遷移、`peTTM` 提到 `peNormalizedAnnual` 之前

**未做（後續 PR）**：
- 不動 `investment_protocol_v4_8.md`，scoring/audit 整合進 protocol 是下一個獨立決策（PR-5/6 範圍）
- 不動既有下游 skill（ftd-detector / market-top-detector / us-stock-analysis）

## 🟡 Session Note (v1.43.0) — Finnhub Client + Diff Tool（PR-1 + PR-2）

新增 `skills/finnhub-client/` 作為共用基礎設施。背景：審計後發現 FMP free 250/day 配額會卡死 batch screening + Phase 3 自動化，且專案缺三個重大資料源（earnings calendar / earnings surprise / insider transactions）。Finnhub free 60/min ≈ 300× FMP 吞吐量，剛好補洞。

**完成**：
- **finnhub_client.py（359 行）**：60/min token-bucket throttle + file cache (per-method TTL) + exp backoff retry + 17 endpoints (quote / candle / profile / metric / financials-reported / filings / company-news / earnings-calendar / earnings-surprise / insider-tx / insider-sent / recommendation / price-target / upgrade-downgrade / dividends / splits / ipo-calendar)
- **adapters.py（171 行）**：5 個 Finnhub→FMP shape 轉換器；financials_to_fmp_income 標 `_lossy: True`（concept 對應不完整，僅供 raw filing reference）
- **diff_tool.py + run_diff.sh（374 行）**：side-by-side 比對 9 欄位 × 10 ticker，PASS<2% / WARN 2-5% / FAIL>5% 三級評分，輸出 `diff_reports/YYYYMMDD.md`

**架構修訂（吸收 ChatGPT review feedback）**：原方案「Finnhub Tier 1 包含 financials」改為**按資料種類分層**：
- 市場/事件層 → Finnhub primary（quote / OHLCV / profile / 4 種事件流）
- 財報真實層 → **FMP primary**（income/balance/cashflow，避免 Finnhub raw XBRL 漂移 quality model 的 CFO/NI/share count）
- 經濟/forward EPS → FMP only
- 簡易 metrics（P/E、ROE、div yield、P/B）→ PR-3 跑 5-7 天 diff 後再決定

**接下來**：使用者跑 `bash skills/finnhub-client/scripts/run_diff.sh`（需先 `export FINNHUB_API_KEY=...` 和 `export FMP_API_KEY=...`），連跑 5-7 天累積 diff 報告 → 決定 PR-4 data-client 抽象層的 routing 規則。

## 🟢 Previous Session Note (v1.42.2) — Sector Protocol 文字瘦身 R2

第二輪 trim — v1.42.0/v1.42.1 加進去的 FRED 解說文字現在搬到 README。原則：
- protocol 檔只留 LLM 執行所需（規則 / schema / 命令）
- 「為什麼這樣設計」「歷史教訓」「比舊版快多少」全部 → README 設計理由區

砍掉：Step 1 vs Step 6 解釋、confidence gating 教學、Renderer 給 user 的提示、
1999 dotcom/2021 SPAC 歷史教訓、Phase 3 「vs 舊流程 200 秒」對比、STEP C.6 timing 對比、
today_verdict bilingual 解說 + 中文範例、4-25 run 觀察記錄。

Phase 2 同時併入 user 的優化：theme_detector 改用 `--skip-if-fresh 10800` flag，script 自管 cache，LLM 不需要再 stat mtime。

統計：protocol 檔 1464 → 1423 行（-3%）；README 補上 5 個新 rationale 區塊。每次 sector 掃描 LLM 載入量都減一點。

## 🟢 Session Note (v1.42.1) — Sector Protocol 提速

4-25 跑 sector scan 仍 20 分鐘（v1.42.0 砍了 5 分但還可降）。Phase-by-phase 拆解後三個瓶頸都改掉：

- **Phase 3** 19 個 WebSearch 砍到 ≤ 5。強制走 `market-sentiment-analyzer` + `economic-calendar-fetcher` + `~/.claude/skills/earnings-calendar` + reuse `_phase0.fred_snapshot`。WebSearch 限 5 個 narrative，給了具體 query 範本與 ban list（Russia/Ukraine、FDA PDUFA、bank earnings dates、copper price、AI capex、DOJ Powell — 不是 sector-level 該管的）。
- **Phase 2** theme_detector 跑兩次浪費 145s（第一次 `timeout 150` 殺掉 retry）。Phase_1-2-3.md 加 runtime 提示：正常 140-180s，禁止 `timeout < 240` 包裝。
- **Phase 4c** Step 6 LLM 心算 11 sectors 改用 `step6_overlay.py --input` CLI，純 Python <1s 出 JSON 直接 paste。

**Phase 4a 4-lane 平行確認 OK**：4 個 Agent 都在 `msg_01U6D4...` 同一訊息，wall-clock = max lane = 109s（vs 序列 372s）。

預計 4-26 跑 sector scan：20 分 → ~14-15 分。

## 🟢 Session Note (v1.42.0) — FRED 整合

8 個改動全做完（P0-P3）。背景：審計發現 v4.9 spec 寫 fred-macro MUST-run 但 7/7 近期 invest 跑都跳過。Sector 完全沒接 FRED。

**完成**：
- **fred-macro**: composite score 改 latency-weighted（real-time tier 1.0 / employment 0.7 / inflation 0.5），解決 Lag Trap。composite 60→62。
- **Sector Phase 0**: 新增 Layer E (FRED MUST-run)。schema `_phase0.fred_snapshot` slim 11 欄位。validator 強制檢查。
- **Sector Phase 4a**: 新增第 4 lane `FRED_Macro_Analyst`，讀 `SECTOR_ROTATION_GUIDE`。
- **Sector Phase 4b DA + Investment Phase 2.8 Red Team**: 兩個 prompt 都加 FRED slim paste + 衝突規則（必須引用具體數值，不可寫 vague「macro 轉差」）。
- **Sector Phase 4c STEP G.5**: Macro/Theme 衝突 → cap WARM + `macro_theme_divergence` flag。Anti-1999/2021 泡沫頂規則。
- **Sector Step 6**: FRED regime overlay 取代 Step 1（不疊加）+ regime_confidence gating。`step6_fred_multiplier` 寫入每 sector，`step6_overlay` block 寫頂層。renderer 新增 FRED× 欄位。
- **`step6_overlay.py`**: deterministic Python 計算器（10 regimes × cyclical/defensive matrix + favor/avoid override + confidence gating）。
- **`backtest_step6_overlay.py`**: 用 `fred-macro --asof` + yfinance 回測 top-3 vs bottom-3 spread。目前 n=5 樣本太小（每個 sector 才 12 天 history），smoke test 跑通；data 累積到 50+ 才有統計意義。
- **`investment/scripts/validate_phase0.py`**: V4.9 mini-gate 抓 LLM 漏填 fred_available / fred_snapshot / rationale。

**今日 sector_intel.json** 已 backfill FRED slim snapshot + Step 6 multipliers。`reports/2026-04-24_sector_report.md` 已重 render 含 FRED× 欄位 + Step 6 區塊。`validate_sector_intel.py` rc=0。

**下次跑投資 protocol 預期變化**：
1. LLM 必須跑 fred-macro fetch（會被 validate_phase0.py 抓）
2. Red Team subagent 收 FRED slim paste，產出 kill_conditions 會引用具體 FRED 數值
3. macro_multiplier_rationale 必須提到 FRED / yield / real_rate / nfci / credit / regime 之一

**下次跑產業掃描預期變化**：
1. Phase 0 多 Layer E（fred-macro fetch + slim snapshot 寫入 _phase0）
2. Phase 4a 多第 4 lane（FRED_Macro_Analyst subagent）
3. Phase 4b DA 收 FRED snapshot，可量化反論
4. Phase 4c 仲裁可能觸發 STEP G.5（FRED-avoid sector 被 theme 推 HOT → cap WARM）
5. Phase 5 evaluator 跑前算 step6_multiplier 寫入每 sector
6. 報告含 FRED× 欄位 + Step 6 overlay 區塊

## 🟢 Session Note (v1.41.1)
- **Protocol 檔案瘦身**：`sector_protocol_main.md` / `phase_0.md` / `phase_1-2-3.md` / `phase_4-5.md` 全部清掉人類向敘述、計算範例、歷史沿革，只留 LLM 執行所需。702 → 641 行。
- **README 吸收**：被移走的內容（Phase 0 計算範例 ×2、Phase 5 機械化動機、V1.4 changelog）全部進 `sector/README.md`。
- **新原則寫入 README**：protocol 檔只給 LLM 看（緊湊、機械、可驗證），README 只給人看（背景、設計理由、debug）。Protocol 是 source of truth，README 註明 pointer 即可，避免雙邊漂移。

## 🟢 Session Note (v1.41.0)
- **(1) 產業掃描 Phase 5 機械化**：新增 `sector/scripts/render_sector_report.py`，從 `_sector_intel.json` 直接渲染 markdown 報告（7 段：Verdict / Macro / Today's Verdict / DA Challenges / Divergence / Themes / Handoff）。
- **(2) Protocol V1.4**：`sector/phase_4-5.md` Phase 5 重寫為 4 步機械流程（寫 JSON → validator → renderer → ≤10 行 summary）。PS **禁止**用 Write 手寫 markdown；`_phase4c.today_verdict` 所有欄位為必填（renderer 的文字來源）。
- **(3) 動機**：今日 `產業掃描` 跑 26 分鐘（`sector_20260424_210620.log`）。時間軸拆解顯示 Phase 5 markdown 生成 663s + 最終 summary 225s 共 15 分鐘純模型輸出，內容與 `today_verdict` 完全重疊 → 全部改機械渲染。
- **(4) 今日 markdown 已用新 renderer 回寫**：`reports/2026-04-24_sector_report.md` 現為 102 行 / 5.2KB，比原 71 行版本多出 Macro Context / Sector Divergence Watch / 完整 Actionable Themes 區塊。

## 🟢 Session Note (v1.40.0)
- **(6) 宏觀資料官方化**：新增 `fred-macro` skill 抓 12 條 FRED 官方 series（利率 / 通膨 / 就業 / 信用 / 壓力）；投資 protocol Phase 0 新 L4 layer 永遠跑（MUST-run）；`fred_snapshot` 輸入 multiplier 雙向 blending（LLM baseline × FRED caps 取 min，全 clear 時 × 1.05 bonus）。
- **(5) Dashboard 自動刷新**：`dashboard_server.py` 新 `fred_refresh_loop` daemon 每 15 min 重抓 cache；`bridge.py` 注入 `data.fred_macro` 到前端 data.json。
- **(4) MACD UI 完整**：點擊 MACD 欄跳 RSI 同風格 click popup — zero-axis bar + 4-regime quadrant map (strongest_bull / weakening_bull / reversal_bull / strongest_bear) + personalised advice。Preset buttons 加 hover tooltip（criteria / strategy / action 三段式，紫色 accent）。Signal/warning pills 也改自訂 hover tooltip，取代原生 title=。
- **(3) 前次累積**：跨頁導航 scan banner `Ended_at` 時間戳（5 分鐘效期）；AnalyzeQueue 解決重複分析；`i18n.js` `scan_confirm` preflight 時間預告。

---

## 🔵 Momentum Context (Multi-Universe)
**動能選股 Universe 整合機制**。
- **(1) 市場狀態**：目前預設掃描 `all` (SP500 + Nasdaq 100 + Watchlist)，總數 527 檔。
- **(5) 數據結構**：CSV/JSON 新增 `in_nasdaq100` 布林欄位。
- **(4) UI 連動**：Dashboard 預設顯示 Top 200，但透過 `isWatchlist` 邏輯，自選股不受 Universe 篩選器影響，始終顯示。

---

> **📜 完整版本歷史已移至 [`CHANGELOG.md`](./CHANGELOG.md)** — 自 v1.0.0（2026-04-09 初始）至目前全部 entries，含 git commit 引用與 evolution highlights。

---

## 📋 Bridge 資料流對照（System Manifest）

| Protocol | 輸出 Log | Bridge 讀取欄位 | Dashboard 顯示 |
|---|---|---|---|
| `investment_v4_8` | `invest_logs/history.json` | `final_decision`, `score`, `macro_alignment`, `key_risks` | decisions 頁全部 |
| `sector_v1.3` | `sector_logs/*_intel.json` | `market_regime`, `_phase0` (breadth/FTD/MT), `today_verdict` | index + sector |
| `news_v2.1` | `news_logs/*_digest.json` | `verdicts[]`, `trump_signals`, `catalysts` | news 頁 + sidebar |
| `breadth_analyzer`| `breadth_cache/*.json` | 6 組件 breadth + trend | index 廣度 gauge |
| `positions.json`  | — | lots → avg_cost / live_position | decisions 持倉 |

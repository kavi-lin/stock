# Session Notes 歸檔 v1.69.1 → v1.71.4（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v1.71.4) — Earnings sparkline 黑底破圖修

User 截圖顯示 NVDA earnings card「毛利率 8Q -3.4 PTS」sparkline 呈現整片黑色三角形（應該是淡紅 fill + 紅線）。

### 根因
`Dashboard/earnings.html:332` CSS：
```css
.ea-sparkline path { fill: none; stroke-width: 1.6; }
```
Selector 只 catch `<path>`，但 `page-earnings.js:484` 渲染的是 `<polyline>` — CSS 沒套到 → polyline 用 SVG 預設 `fill: black` → 黑色三角形蓋掉下面 `.ea-sparkline-fill` polygon (opacity 0.18 淡紅) 的視覺。

### 改動
CSS selector 加 `polyline`：
```css
.ea-sparkline path,
.ea-sparkline polyline { fill: none; stroke-width: 1.6; }
```
一行加完，整個 sparkline 立即恢復「淡色背景區塊 + 趨勢線」應有樣貌。

### 驗證
Hard reload `earnings.html`，sparkline 應顯示淡紅 fill (trend down) / 淡綠 (up) / 灰 (flat) + 對應顏色的折線。

---

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
-  const VERSION = 'V3.13.0';

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

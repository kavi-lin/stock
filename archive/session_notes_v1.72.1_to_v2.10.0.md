# Session Notes 歸檔 v1.72.1 → v2.10.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v2.10.0 → v2.11.0) — earnings real next-date + EV ratios + theme-detector mapping + sector-analyst FMP overlay

User 起點：「earnings dashboard 上的 🔮 下次財報日是猜的」。修完發現 earnings-analyst 早就 fetch FMP /stable/earnings limit=8 用做 surprise，response 含 1 個未來 row — **資料早在記憶體只是沒用**。改 scan future row + 加 `next_earnings_source` 後，6 個 cached tickers 全 `fmp_confirmed`（NVDA 從過期 +91d 的 2026-04-26 → 正確 2026-05-20）。Frontend 依 source 切 📅↔🔮，向後相容（舊 cache 自動 fallback 🔮）。

順手做完 user 要求的全 skill × FMP catalog 盤點：FMP_強化分析.md 2025-01-30 提的 P0/P1/P2 大部分都 ship 了（financial-scores / owner-earnings / institutional / senate+house / M&A / ESG / news-stock / sec-8k 在 `_shared/fmp_supplementary.py`）。剩 (1) `evToEBITTTM` 漏 — 實測 FMP 沒此欄位（ghost field），改補 `evToFreeCashFlowTTM` + `evToSalesTTM`；(2) theme-detector 仍 finviz primary；(3) sector-analyst 完全沒 FMP overlay。

Theme-detector dry-run 揭露兩個關鍵：finviz 資料 ~50% 損壞（HARD_CAPS 註解已認證 — 看到 ±98% 不可能值）但 finviz vs FMP 只 73/144 (51%) name overlap。手工建 `industry_name_mapping.yaml`（47 rename + 8 collapse + 16 finviz_only + 6 fmp_only = 100% finviz coverage），但**未啟用**（`theme_detector.py:479` 還 import finviz）— 等 user 確認 mapping accuracy 再切 primary。

Sector-analyst 因 TraderMonty CSV uptrend ratio 是 breadth metric（FMP 沒此概念）→ 不能 1:1 替換 → 改加 FMP `sector-pe-snapshot` + `sector-performance-snapshot` 為 overlay（11 sector PE + 1d/5d perf，跨 exchange 平均 + Financial Services→Financial rename 對齊 TraderMonty）。`format_json` 加 `fmp_overlay` field，human format 末尾追加表格。No FMP key 時 graceful no-op。

Files：earnings-analyst/fetch.py + render.py + bridge.py + Dashboard/page-earnings.js + theme-detector/dry_run_compare.py + theme-detector/industry_name_mapping.yaml + sector-analyst/analyze_sector_rotation.py。

下一個自然 follow-up（**留 BACKLOG**）：(1) theme-detector 切 FMP-primary（mapping 已備；先 user review YAML 再切）；(2) sector-analyst overlay 整合進 sector_protocol Phase 4 估值面 rubric；(3) 71 finviz-only 中疑似 FMP 有等價名（Internet Retail 等）二次審視。

## 🟢 Session Note (v2.9.1 → v2.10.0) — invest protocol det-shadow + polarization

CRWV 2026-05-03 同日重跑兩次，final_score 從 −0.055 跳到 −0.481（verdict CANCEL ↔ HOLD 翻面）。診斷出主因：5 個 lane 的獨立 LLM subagent 在 −2/−3 邊界各自抽到不同邊（Fund/Sent 兩 lane 同向 ±1 notch ≈ ±0.40 final_score），架構正常 noise 但 user 體感很怪。V2.10 不改 LLM 主分數（保留 nuance），加三層 sidecar：(1) `signal_polarization`（純看 5 lane 分布，CRWV 兩 run 都判 BIPOLAR — 跨 run 一致 label）；(2) deterministic Valuation shadow（純算 FV/price 閾值表）；(3) deterministic Red Team shadow（6 條 quant kill triggers 數量決定 verdict）。新增 `apply_det_shadow.py` post-processor + Phase 5 Step 1.5 強制跑；schema 新增 `lane_scores` / `det_inputs` / `det_shadow`；bridge + Dashboard pills 帶到 UI（BIPOLAR / RT DISAGREE / VAL DISAGREE 三個 badge）。歷史 CRWV 兩 run 已 backfill 驗證對應預期：Run 1 BIPOLAR + AGREE + DRIFT；Run 2 BIPOLAR + DISAGREE + DISAGREE（完美揭露 LLM 比 quant 寬容了）。

## 🟢 Session Note (v2.8.2 → v2.9.0) — sector protocol 三個新 FMP 訊號

對照 V2.8.2 整理的 FMP MCP 完整清單，發現 sector protocol 還有三個高價值訊號沒納入。**(1) institutional Q-on-Q**：`fetch_smart_money.py` 加 `/stable/institutional-ownership/symbol-positions-summary` 對全 SECTOR_UNIVERSE aggregate，新欄位 `institutional_holders_qoq_delta` / `institutional_ownership_pct_delta` — 真正補上 V1.4 欠下的 form13F 坑（free tier 可用）。**(2) Forward valuation**：`fetch_earnings_pulse.py` 加 `/stable/price-target-consensus` + `batch-quote-short`，新欄位 `analyst_pt_upside_median_pct`。**(3) 多週期 RS**：`fetch_sector_valuation.py` 重用既有 3M chart 算 5d/20d，零新增 API call；既有 `rs_vs_spy_3m` 對 V2.8.x cache **byte-identical**。三個都 soft-fail；rubric 不動，新訊號只進 Phase 4b divergence challenge（規則 5 擴充 + 規則 6/7 新增，皆有量化 threshold 避免 LLM 自由發揮）。原本提案的 `acquisition-of-beneficial-ownership` 實測 mega-cap 太稀疏（最近 180d 全 0），rationale 留在 BACKLOG。

## 🟢 Session Note (v2.7.18 → v2.8.0) — sector protocol DRY refactor + FMP 補位

四份 sector fetch 腳本（valuation/earnings_pulse/smart_money/sector_news）的 `_fmp_get` 抽到 `sector/lib/fmp_client.py`（含 4xx 不重試早退）；docstring 砍到 2-3 行，背景搬 `sector/BACKLOG.md` + `sector/scripts/README.md`。新增 `fetch_general_news.py`（FMP `/stable/news/general-latest`，soft-fail）作 Phase 3 narrative 補位 — `general_news.available=true` 時 Step 5 WebSearch budget 從 ≤2 降到 ≤1，**WebSearch fallback 永遠保留**。`fetch_earnings_pulse.py` 加 `/stable/grades-consensus` 填滿 `analyst_revision_net`（之前永遠 null，現在 11 sectors 都有值）。Refactor 行為對舊 cache byte-identical；驗證器 rc=0。Schema/rubric/render/daily_update.sh/Dashboard 都不動。

## 🟢 Session Note (v1.76.0 → v1.87.0) — FMP 強化分析 12-bump 串接

### 動機
User 提交 `investment/FMP_強化分析.md` 報告，列出 invest_protocol V4.10 全鏈 FMP API 強化機會 (Web-Fetch 替換 / Burry 確定性規則 / Sentiment+News 新訊號 / FMP_SUPPLEMENTARY_BUNDLE 新增)。要求按主要功能切版本 bump 不要擠一筆，autonomous 跑完 + 跑測試 + AAPL benchmark 對比。

### 12 個 bump 結構
| Version | Feature | Files | 風險 |
|---|---|---|---|
| v1.76.0 | earnings-analyst slim_ttm_keymetrics +3 capital efficiency 欄位 (ROIC/ROCE/ROTA) | 1 | 低 |
| v1.77.0 | FMP endpoint probe script (17/18 PASS, 1 skip) | 2 | 無 |
| v1.78.0 | `skills/_shared/fmp_supplementary.py` skeleton + quality_scores + owner_earnings + protocol Phase 1 整合 V4.11 | 3 | 中 |
| v1.79.0 | FMP_SUPP.insider_summary + sentiment skill bundle-first | 2 | 中 |
| v1.80.0 | FMP_SUPP.institutional QoQ (mid-filing-window sanity gate) | 1 | 低 |
| v1.81.0 | theme-detector FMP industry perf cross-check (不替換 finviz) | 1 | 低 |
| v1.82.0 | market-news-analyst FMP news/stock + press-releases (PRIMARY 4-source dedup) + finviz_analyst_actions tzinfo bug fix | 1 | 中 |
| v1.83.0 | News lane sec-filings-search/symbol → 8-K filter | 1 | 低 |
| v1.84.0 | us-stock-analysis bundle-first (EARNINGS_ANALYST_BUNDLE override yfinance) | 1 | 中 |
| v1.85.0 | protocol V4.11 — 4 lane (Burry+Fundamentals+Sentiment+News) FMP_SUPP rules | 1 (protocol) | 中 |
| v1.86.0 | FMP_SUPP.congressional_trades + ma_events | 1 | 低 |
| v1.87.0 | annual analyst-estimates 加入 EARNINGS_ANALYST_BUNDLE + FMP_SUPP.esg | 2 | 低 |

### AAPL benchmark — final integration test 結果
**FMP_SUPP_BUNDLE V1.0** (AAPL_2026-05-02_supp.json, 4082 bytes, 9 FMP calls):
- `quality_scores`: altmanZ=11.64 (safe) / piotroski=9 (strong) → Burry rubric V4.11 規則：safe + strong → +1 score
- `owner_earnings`: $28.86B latest, qoq=-46.7% → Fundamentals -0.5 narrative trigger
- `insider_summary`: 4Q latest_trend=distributing (acq/dis ratio=0.18) → Burry voice 加註，Sentiment lane 已從 bundle 讀
- `institutional`: 64.60% ownership, +3.03% QoQ → accumulation_signal=accumulating → Sentiment +1
- `congressional_trades`: 30 trades 180d (15 buy / 15 sell) → neutral
- `ma_events`: 0（mega cap 通常 0，schema 正確）
- `esg`: total 56.79, rating B (2025)

**us-stock-analysis bundle-first**:
- bundle path P/E 33.89 (FMP TTM canonical) vs no-bundle P/E 35.74 (yfinance) — 5.2% drift
- EV/EBITDA 25.59 (bundle) vs 24.98 (yfinance) — 2.4% drift
- next_earnings 2026-07-31 from bundle vs unknown from yfinance

**News 4-source dedup**:
- FMP news/stock=30, press_releases=2, finviz=100, yfinance=10, finnhub=25
- 5-source dedup → 149 unique headlines, primary_source=fmp_news_stock
- 8-K filings: 2 件 (30d window)

**theme-detector FMP cross-check**:
- 128 industries × 5 trading days, top 5d perf: Manufacturing-Metal Fabrication +13.82%, Software-Services +11.58%, Personal Products +10.10%
- 不替換 finviz，scorer 後續可選用 cross-validate

### 物理隔離契約 (V4.11)
FMP_SUPP_BUNDLE 為 FMP-only。fmp_supplementary.py 模組**不得**import dual_fetch / FinnhubClient。Bundle 經 Phase 1 PM 路由到 4 個 lane（Fundamentals / Sentiment / News / Burry），Technical lane 不收（OHLCV-only）。Sentiment skill bundle-first + skill self-fetch fallback：bundle 命中時 0 額外 FMP call，bundle 缺時 skill 獨立可用。

### 注意事項與決策記錄
- 決策 B：Burry 規則只調 score (±1/±2)、不強制 verdict (LLM 收尾權保留)
- 決策 C：theme-detector option-3，FMP 為新欄位、不替換 finviz
- 決策 D：news 5-source dedup（FMP primary + finviz/yf/finnhub/press fallback）
- 決策 E：sentiment bundle-first + skill fallback
- 決策 F：us-stock-analysis bundle-first + yfinance fallback (--no-bundle 旗標保留)
- 決策 G：沿用檔名 `investment_protocol_v4_8.md`，內文 V4.11 章節
- 決策 H：獨立 cache `skills/_shared/fmp_supp_cache/`

### Endpoint 修正記錄
- ❌ `/stable/news-stock` → ✅ `/stable/news/stock`
- ❌ `/stable/news-press-release` → ✅ `/stable/news/press-releases`
- ❌ `/stable/sec-filings-8k` (ignores symbol filter) → ✅ `/stable/sec-filings-search/symbol` + 客端 filter formType=8-K
- ❌ `/stable/intraday-1hour` → ✅ `/stable/historical-chart/1hour`
- `historical-industry-performance` 200 但 count=0；改用 industry-performance-snapshot rolling sum

### 既有 bug fix
- `_finviz_analyst_actions:97-104` `replace(tzinfo=)` 對 numpy datetime64 失敗 → 加 `isinstance(d, datetime)` gate (v1.82.0)
- `_derive_from_bundle` next_earnings_est schema：bundle 給 string `"YYYY-MM-DD"` 而不是 dict → 加 isinstance check (v1.84.0)

### 改動清單（v1.76.0 → v1.87.0 累計）
**新檔**：
- `skills/_shared/fmp_supplementary.py` (~340 行 V1.0 schema + 7 fetch helpers)
- `investment/scripts/fmp_endpoint_probe.py` (~110 行)
- `investment/fmp_probe_2026-05-02.json` (probe 結果)
- `skills/theme-detector/scripts/fmp_industry_perf_client.py` (~150 行)

**改動檔**：
- `skills/earnings-analyst/scripts/fetch.py` (slim +3 fields, +annual_estimates)
- `skills/market-sentiment-analyzer/scripts/sentiment.py` (bundle-first insider)
- `skills/market-news-analyst/scripts/fetch.py` (FMP news/stock + press + 8-K + tzinfo fix)
- `skills/us-stock-analysis/scripts/analyze.py` (bundle-first override)
- `investment/investment_protocol_v4_8.md` (V4.11 — Phase 1 + 4 lane FMP_SUPP 規則)

### 驗證
- 6 個 integration test 全綠：FMP_SUPP_BUNDLE / us-stock-analysis / news / sentiment / earnings / theme-detector
- `validate_session_export.py` 對既有 AAPL session export ✓ V4.8 schema compliant
- 無 protocol contract 破壞（dual-fetch isolation 保留）

---

## 🟢 Session Note (v1.75.0) — 決策中心 (decisions.html) Invest Cmdbar + 視覺布局重組

### 動機
User 比對 earnings.html 的 cmdbar 體驗(terminal-style ticker input + 快速跑 protocol),希望 decisions.html (決策中心) 也加同款,但 trigger **invest protocol** (`分析 [TICKER]` V4.10 委員會深度分析) — 與決策中心語意一致。順便做視覺布局重組:summary stats / 卡片 hover state 微調。

### 實作重點
- **Cmdbar HTML** (decisions.html `<header>` 下方): prompt `›` + input + RISK hint + 分析 btn + recent chips,套既有 `.ea-cmdbar*` class
- **Risk tolerance**: 用全局 `UI.riskTolerance` (utils.js:474 getter,localStorage `dash_risk_tolerance`,sidebar `#risk-chip` 可切換),cmdbar 只顯示「RISK: MEDIUM」hint,不重複暴露切換 UI(避免 multi-source-of-truth)
- **runInvest 邏輯**: POST `/api/protocol-queue` flat payload `{name:'invest', ticker, risk_tolerance}` (與 script.js:1094 / page-radar.js:843 一致),202 → recent chip + toast + clear input;409 → duplicate toast
- **Recent chips**: localStorage `dc_recent_invest_tickers` max 5,點擊重跑同一 ticker
- **css 提升**: `.ea-cmdbar*` 從 earnings.html L64-119 inline 拷貝到 `Dashboard/style.css` 共用區(+90 行),earnings inline 保留作 graceful fallback;decisions 直接用 shared
- **視覺 polish**: `.dc-summary-tile` hover lift + `.dc-summary-num` (32px JetBrains Mono),conf/RR 兩格加 blue/violet 4px left-border;`.dc-card-hover` 卡片 emerald border + lift

### 既有 utility 重用
- `UI.riskTolerance` (utils.js:474), `UI.escapeHTML`, `UI.boot('decisions', ...)`, `UI.showToast`
- `.ea-cmdbar*` / `.ea-recent-chip` (earnings.html → style.css 提升共用)
- POST `/api/protocol-queue` invest payload pattern (analyze-queue.js:60 / script.js:1094 / page-radar.js:843 既有)

### 注意:`refreshTicker` 已在跑 invest
卡片右上「refresh-cw」按鈕 (page-decisions.js:1108 `refreshTicker`) 既有就走 `AnalyzeQueue.enqueue` invest,不是 FLASH。Plan 探索期 explorer 誤判;**本次未動該函式**。卡片底部的 FLASH 按鈕走 `goFlash` (新聞快訊),那是刻意的二次選項,保留不動。

### 改動清單
- `Dashboard/decisions.html` (~30 行 add/edit) — cmdbar HTML + summary tile classes
- `Dashboard/page-decisions.js` (~110 行 add) — dcRunInvest + recent chips + wireCmdbar + applyTranslations 擴充 + buildCard 加 dc-card-hover class
- `Dashboard/style.css` (~90 行 add) — `.ea-cmdbar*` 共用 + `.dc-summary-tile` / `.dc-summary-num` / `.dc-card-hover`
- `Dashboard/i18n.js` (~30 行 add) — `decisions.cmdbar_*` zh/en 雙語 7 keys
- `Dashboard/utils.js`, `VERSION`, `CHANGELOG.md`, `SESSION_NOTES.md`, `TODO.md` — version bump 1.74.0 → 1.75.0

### 不在範圍
- 持倉 modal / 平倉 modal / 持倉 table 結構
- bridge.py extract_audit_history 邏輯
- 卡片內部 layout (target/stop/risk-reward)
- `?ticker=X` deep-link 自動鑽取 (known UX debt)
- 完全移除 FLASH news 入口 (仍可從卡片底部 goFlash 觸發 / news.html)

---

## 🟢 Session Note (v1.74.0) — FMP company API Bucket A (shared profile cache + peer bundle)

### 動機
分析計畫 `/Users/kavi/.claude/plans/3-fluffy-moonbeam.md`:9 個 FMP `mcp__fmp__company` 方法中只 2 個高 ROI(stock_peers + profile)。Bucket A1+A2+A3 一次落地。

### 落地三件事
1. **共用模組** `skills/_shared/company_context.py`(NEW ~250 行)+ `__init__.py` + `cache/` dir
   - 常數:`SECTOR_UNIVERSE` / `TICKER_TO_SECTOR` / `SECTOR_TOP_5`(sector scripts 共用唯一真相源)
   - 函式:`get_profile / get_peers / get_market_cap_history / get_employee_history / get_profiles_bulk`(24h TTL,402 graceful)
2. **sector 3 script 去重** ~75 行:`fetch_earnings_pulse.py` / `fetch_smart_money.py` / `fetch_sector_news.py` 改 `from skills._shared.company_context import ...`
3. **earnings-analyst fetch.py** profile 走共用 cache(同 ticker 24h 內 0 重複 FMP call)
4. **investment_protocol_v4_8.md** Phase 1 末段新增 PEER_BUNDLE step;Fundamentals + Burry lane rubric 加 relative valuation 規則(P/E 差 > 30% → ±1,> 50% → ±2)

### 端對端驗證
- `python3 sector/scripts/fetch_earnings_pulse.py --date 2026-05-01` rc=0,輸出 `92 mega-cap reports in 30d`(數字與 v1.73.6 一致,行為 zero-regression)
- `python3 skills/_shared/company_context.py AAPL --peers` → AAPL profile.sector=Technology,marketCap=$4.2T,peers=['GOOGL','META','MSFT','NVDA','NXT','RIME','SONY','TBCH','TSM']
- `python3 skills/earnings-analyst/scripts/fetch.py AAPL`(no --force)→ cache hit,新 import path 通
- 三個 sector script importlib smoke test 全 OK

### 風險與後續
- **下次跑 `分析 [TICKER]` 才會真正觸發 PEER_BUNDLE 路徑**:目前只完成 spec + 模組,實際 Phase 2 lane subagent 是否正確消費 PEER_BUNDLE 需 user 跑一次 `分析 NVDA` 等高 P/E 票觀察 lane 輸出
- Bucket B(theme-detector dict 拋棄 + Burry historical_employee_count 訊號)未做,等 Bucket A 用一陣子再評
- shared cache `skills/_shared/cache/` 已 .gitkeep 佔位,內容由 runtime 生成不入版控(後續 .gitignore 視需要加)

---

## 🟢 Session Note (v1.73.7) — sector Phase 3 Step 1/2/3 補 explicit bash block

### 問題
scan log `sector_20260501_213508.log` 顯示 sector Phase 3 agent 對 Step 2 (`get_economic_calendar.py`) / Step 3 (`fetch_earnings_fmp.py`) 連續 retry 錯誤 flag：
- `--json --days 7` ❌ unrecognized / `Invalid start date format`
- `--from --to --format json` ✅ (Step 2 econ calendar argparse)
- positional `2026-05-01 2026-05-08` ✅ (Step 3 earnings)

每次 retry 浪費 5-15s + tokens。

### 根因
`sector/phase_1-2-3.md` Phase 3 執行順序 block 只列 step 名沒 bash 指令。Step 3b/3c/3d 有 explicit `python3 ... --date {SCAN_DATE}` 範例所以 agent 不 guess; Step 1/2/3 漏掉。

### Fix
`sector/phase_1-2-3.md` 第 71 行後新增三個 sub-section：
- Step 1 — Market Sentiment (`sentiment.py --json` 已 work, 補完整性)
- Step 2 — Economic Calendar (argparse: `--from --to --format json`，明示**不**支援 `--json`/`--days`)
- Step 3 — Earnings Calendar (positional: `START_DATE END_DATE [API_KEY]`，明示**不**支援 flag 形式)

每段含失敗策略 (soft fail / 不 abort protocol)。

---

## 🟢 Session Note (v1.73.0) — 個股財報 Infographic 風格頁面（取代「看報告」markdown modal）

### 動機
User 看到 AAPL FY26 Q2 財報視覺化 infographic（公司 hero + 4 主指標 actual vs estimate ✓✗ + 6 segment grid + 資本回報 + CEO 引述 + Key Highlights + 重點總結），希望 `財報 [TICKER]` 個股報告改這個樣式。原 markdown 報告退為新頁面內 `<details>` collapse 區塊作 reference。

### 端對端驗證（AAPL Q2 FY26）
- 跑 `fetch.py --force` → 17 endpoints 全成功（含 transcript Y2026Q2 offset=0, 48,024 chars）
- `analyze.py` → composite=72 verdict=SOLID flags=clean
- `validate.py` rc=0
- **Step 4 LLM narrate phase**：Claude in-conversation 讀 cache + transcript content，Write `AAPL_2026-03-28.infographic.json`（含 6 segments + 6 highlights + 4 summary + Tim Cook quote 講 Greater China +28%）
- `render.py` → `reports/2026-05-01_AAPL_earnings.md`（既有 markdown 不變）
- `validate_infographic.py` rc=0：「✓ V1.0 compliant — AAPL FY26 Q2 ✓ transcript segs=6 highlights=6 summary=4」
- `bridge.py --no-fetch` → `data.earnings_analyses[ticker=AAPL].has_infographic=true`，其他 3 ticker (GOOGL/MSFT/NVDA) 為 false 直到重跑

### 技術重點
- **資料層雙 cache 並存**：原 `<TICKER>_<DATE>.json`（V1.0 quantitative）不動；新增 `<TICKER>_<DATE>.infographic.json`（V1.0 narrative，schema_kind="infographic"）；bridge.py 與 `/api/earnings-cache/*` 已加 glob 過濾排除 `.infographic.json` sibling
- **Transcript fiscal-Q resolver 4-tier**：用 cache 內 fiscalYear+period (FMP fiscal labels) → calendar Q → walk back Q-1 with year rollover；最差 4 calls，AAPL 0 offset 命中
- **季度分部來源**：FMP `period=quarter` 全 402 付費，改由 LLM 從 transcript CFO 段抽（infographic 上的 569.9/309.8 億等本來就是這樣來的）
- **Page 切換**：earnings card 「看報告」按鈕改為「📊 Infographic」連到 `earnings-detail.html?ticker=X`；markdown 退為頁內 `<details>` lazy load

### 改動清單
- `skills/earnings-analyst/scripts/fetch.py` — +5 endpoints + 4 slim helpers + transcript resolver (~110 lines)
- `skills/earnings-analyst/scripts/validate_infographic.py` — NEW (~80 lines)
- `skills/earnings-analyst/SKILL.md` — 4 → 6 steps doc
- `skills/earnings-analyst/schema.md` — 追加 V1.73 cache 新欄位 + Infographic schema 完整文件
- `dashboard_server.py` — `/api/earnings-infographic/<T>` + 6-step PROTOCOL_PROMPTS + glob filter fix
- `bridge.py` — `has_infographic` 欄位 + glob filter
- `Dashboard/earnings-detail.html` — NEW (~150 行)
- `Dashboard/page-earnings-detail.js` — NEW (~340 行)
- `Dashboard/page-earnings.js` — view → infographic action
- `Dashboard/style.css` — `.ed-*` namespace ~180 行
- `Dashboard/i18n.js` — `earnings_detail.*` 29 keys × zh/en

### 不在範圍
- 季度 segmentation 付費 endpoint
- Backfill 既有 GOOGL/MSFT/NVDA 必須手動 `財報 X` 觸發 LLM narrate phase
- 多季比較頁（只渲最新一季）

---

## 🟢 Session Note (v1.72.1) — Journal Stats 修復 + 今日未跑提示 Banner

### 問題
- `screen.py --journal` 只寫入 `journal.jsonl`，但從未自動呼叫 `journal.py stats`
- 結果 `stats.json` 不存在 → `bridge.py` 回傳 `journal.stats=null` → 頁面 journal 區塊空白
- 16,043 entries 已存在但頁面看不到任何資料

### 修改

**`dashboard_server.py`** — `_worker()` 在 screen.py 成功且 `--journal` flag 為 true 時，自動呼叫 `journal.py stats`（timeout=120s），phase label 更新為「computing journal stats…」

**`bridge.py`** — binary seek 讀 `journal.jsonl` 最後 4KB，提取 `last_snap_date`，加入 `journal` dict 供前端判斷今日是否已跑

**`Dashboard/momentum.html`** — 新增 `#journal-stale-banner`（amber 色）在 journal-section 頂部

**`Dashboard/page-momentum.js`** — 新增 `renderJournalStaleBanner()` + `runJournalNow()`；比對 `last_snap_date` vs 今天，若過期顯示 banner 及「立即執行」按鈕

**`Dashboard/style.css`** — sidebar brand text 移除 `overflow:hidden` / `min-width:0`，加 `flex-shrink:0`，修正 INTELCOMMAND D 被截斷問題

### 動機
User 看 index.html 的 48 小時二元風險條幅下方四個 ⚠ label —「空頭信號啟動 / 廣度跌破 200MA / 歷史低百分位 / 弱化區間」。其中後三項都是同一個廣度指標的不同切面（`ma_crossover.gap` / `historical_percentile` / `composite.zone`），會綁在一起亮（今天 4 個全觸發、breadth_score=33.1）。原本扁平 flex pill 用 regex 區分紅/黃，視覺權重均等，看不出哪個是真正獨立信號。

### 改動

**bridge.py** — `extract_breadth_from_analyzer` 並列輸出新 schema `warning_flags_v2`（object[]，含 `key/severity/metric_value`），舊 `warning_flags: string[]` 保留以維持 `page-sector.js` 相容。

**Dashboard/style.css** — 新增 `.risk-overview` / `.risk-flag-card`（3 種 severity variants：critical 🔴 / warning 🟠 / caution 🟡）/ `.modal-scroll-shadow`（純 CSS sticky pseudo-element fade）/ `.cta-launch`（Quick Launch button glow）/ `.ticker-input-wrap`（input search-icon prefix）/ `.focus-ticker-promoted` ::after 漸層。

**Dashboard/index.html** — Layer 2a (Binary Alert) + Layer 2b (Warning Flags) 包進共同父層 `<section id="risk-overview">` 加標題 "風險總覽" + count badge。`#focus-ticker-card` 從 Momentum 卡內抽出，提權為 Layer 2 之後的全寬 attention strip。Quick Launch input 加 search icon prefix；button 套 `.cta-launch`。Modal `#preflight-body` + `#report-content` 加 `.modal-scroll-shadow`。

**Dashboard/script.js**:
- 重寫 `renderWarningFlagsIndex` — 用 severity tier 渲染 `.risk-flag-card`，dot + 左邊框 + name + metric chip；自動排序 critical→warning→caution；schema fallback 兼容舊 string[]
- 加 `updateRiskOverviewVisibility()` 協調 #risk-overview 父層顯隱（兩個 child 都空才隱藏）
- 擴充 `#pill-tooltip` engine — `data-tip-key="warning_flag"` 走專屬路徑，從 `i18n.warnings.tooltips.<flag_key>` 組 severity-tinted title + definition + metric chip + remediation hint
- Hero `renderThreeSignalMini` 4 欄各加 10-cell `.score-battery`（複用 Momentum teaser 同款）
- 五區 (`renderBinaryAlertIndex` / `renderHotSectorsTeaser` / `renderNewsVerdictsTeaser` / `renderMomentumTeaser` / `renderFocusTicker`) 全面套 `UI.escapeHTML()`，封死 innerHTML XSS [ARCH-14]
- focus-ticker enqueue 用白名單 `[A-Za-z0-9.\-]` 過濾 ticker，防止 inline `onclick` 注入

**Dashboard/i18n.js** — 追加 `warnings.severity` (critical/warning/caution) + `warnings.risk_overview_title` + `warnings.tooltips.<flag_key>` (definition + hint) zh/en 雙語；新增 `Critical_Zone`、`Early_Warning_Divergence` flag 名稱翻譯。

**Dashboard/page-sector.js** — `warning_flags` consumer 加 schema fallback：兼容 `string[]` 與 `{ key, severity, metric_value }[]` 兩種輸入。

### 驗證
- `python3 bridge.py --no-fetch` → data.json 正確產出 `warning_flags_v2`（4 項：critical 1 / warning 2 / caution 1）
- `node` 語法檢查 script.js / page-sector.js / utils.js / i18n.js 全部通過
- 視覺驗證（user 端）：開 index.html 應看到 1 紅 + 2 橘 + 1 黃 順序排列；hover 各 card 顯示 severity-tinted tooltip 含 `gap −2.83%` / `pct 25%` / `score 33.1` / `risk 25` 等具體數值與 remediation hint。

### 不在範圍
- Sidebar nav 結構不變
- market-breadth-analyzer skill 內部不動（只動 bridge.py glue layer）
- decisions.html `?ticker=XXX` deep-link 仍是 known UX debt
- 其他 page 視覺改動（除 page-sector.js 防禦性 fallback）

---

# Skills Market Index

> Source of truth for `market` / `scope` classification + 接線狀態 of every skill in
> `skills/`. 26 skills + `_shared`. Rewritten 2026-06-11 (V4.5 audit cleanup)；2026-07-03 補 quant-backtest；2026-07-16 補 valuation-modeler (V4.69.0)；2026-08-08 econ-calendar 修復移回 Protocol lane (V4.111.5)。
> 最新接線稽核：[2026-10-04 endpoint audit](../reports/SKILLS_ENDPOINT_AUDIT_2026-10-04.json)；修復驗收：[fix evidence](../reports/SKILLS_ENDPOINT_FIX_2026-10-04.json)。26 個 skill 的保留／整併評估見下方「生命週期評估」。

`market` values:
- **us-equity** — hard-coded to US data sources (FMP, Finnhub, GICS, TraderMonty CSV, etc.); not reusable for other markets without rewrite
- **market-agnostic** — pure technical / math logic; reusable for any equity market if you supply the universe / data feed
- **global-macro** — macro events / series with global reach (Fed + ECB + BOJ etc.)

`scope` values: `single-ticker` / `universe-scan` / `sector-level` / `market-level` / `portfolio-level` / `event-scan` / `news-scan` / `theme-scan`

---

## 🟢 Daily pipeline（daily_update.sh 自動跑）

| Skill | Market | Scope | Data sources | 接線 |
|---|---|---|---|---|
| `market-breadth-analyzer` | us-equity | market-level | TraderMonty CSV | Step 1（non-fatal since V4.4）+ sector Phase 0 層 A |
| `fred-macro` | global-macro | market-level | FRED API (17 series, 1h TTL) | Step 4；degraded → rc=2（V4.4）|
| `theme-detector` | us-equity | theme-scan | FMP / finviz-performance / yfinance ETFs | Step 6 前置（季度 universe 重跑 Step 5.5）+ sector Phase 4a |
| `thematic-screener` | us-equity | theme-scan | theme-detector cache + short-term-target (in-process V4.5) | Step 6 → `data/recommendations/<DATE>.json` → radar.html |
| `short-term-target` | us-equity | single-ticker | yfinance + finnhub dual-fetch + sector logs | Step 6 經 thematic 呼叫；ad-hoc `predict.py <T>`；週末 `weekly_review.py` |
| `retail-sector-pulse` | us-equity | sector-level | news digests + predict 5d（ThreadPool×8）| Step 9.5 → `Dashboard/retail_sector_pulse.json`（retail volume 元件已隨 narrative-pulse 退役，graceful None）|
| `market-sentiment-analyzer` | us-equity | market-level | yfinance (VIX/SPY) + CNN F&G | Step 9.3 mood；degraded → rc=2（V4.4）|
| `momentum-monitor` | market-agnostic | universe-scan | **FMP 主源** + yfinance fallback；.info 24h sidecar | Step 9.7 screen + `動能 [TICKER]` + Dashboard momentum.html |
| `ftd-detector` | us-equity | market-level | yfinance | daily 實跑 `sector/ftd_yfinance.py`（yfinance adapter，V4.72.0 起 import **repo 內** skill scripts 為 canonical，env `SKILL_SCRIPTS_PATH_FTD` 可覆寫）；skill 內 fmp_client 僅供有 FMP 訂閱時直跑 |
| `market-top-detector` | us-equity | market-level | yfinance | 同上 — daily 實跑 `sector/market_top_yfinance.py`（repo canonical，env `SKILL_SCRIPTS_PATH` 覆寫） |

## 🔵 Protocol lane（`分析` / `產業掃描` / `財報` / `ic-memo` 觸發）

| Skill | Market | Scope | Data sources | 接線 |
|---|---|---|---|---|
| `earnings-analyst` | us-equity | single-ticker | FMP /stable（20 call 並行 ×8, V4.5）| `財報 [TICKER]`；cache key (TICKER, last_earnings_date) |
| `earnings-valuation-forecaster` | us-equity | single-ticker | FMP /stable | `財報前瞻 [TICKER]`（V2.15 起 Dashboard earnings/calendar 卡片自動 morph button）+ 12M scenario |
| `ic-memo-writer` | us-equity | single-ticker | protocol history + earnings cache + company_context | `ic-memo [TICKER]` / `分析 --memo`（V3.25 deterministic 0-LLM renderer）；V4.69.0 `首次覆蓋 [TICKER]` → compose_initiation |
| `valuation-modeler` | us-equity | single-ticker | FMP /stable + FRED cache（fmp_pool 限流）| V4.69.0 新增：`估值模型`/`同業比較 [TICKER]`；餵 protocol `dcf_self_built`(0.15)/`comps_implied`(0.10) anchor；`--xlsx` 出 Excel workbook |
| `finnhub-client` | us-equity | single-ticker | Finnhub + FMP dual fetch（calendar memoized V4.4）| protocol quant 輸入 canonical snapshot + drift audit |
| `us-stock-analysis` | us-equity | single-ticker | FMP（analyze.py；web search 違規已修 V4.4）| investment Fundamentals lane |
| `short-contrarian-analyst` | us-equity | single-ticker | yfinance（V4.111.7 更正：從無 FMP 呼叫）| investment Phase 2 第 5 lane（Burry）；T4 仲裁刻度已修 V4.4 |
| `technical-analyst` | market-agnostic | single-ticker | shared technical_core（FMP 主源）；chart 圖片為獨立模式 | investment Phase 2 Technical lane（`analyze.py --json-only`）|
| `tail-risk-analyzer` | market-agnostic | single-ticker | yfinance | investment Phase 4 Step 3、sector Phase 4b |
| `portfolio-risk-manager` | market-agnostic | portfolio-level | positions.json + shared technical_core（FMP 主源） | investment Phase 4 Step 2 |
| `dual-axis-skill-reviewer` | market-agnostic | tooling | 無外部資料源（讀 `skills/*/SKILL.md` + 跑該 skill 測試）| **dev 工具，不接 protocol**。V4.113.4 自上游引入（`b814274`，程式碼未改）。auto 軸的結構檢查對應上游 SKILL.md 模板，與本 repo 風格不同——讀 breakdown 而非總分，見該 SKILL.md 頂部注意事項 |
| `sector-analyst` | us-equity | sector-level | TraderMonty CSV + FMP sector valuation（protocol Phase 1）| sector protocol core；見 `sector/phase_1-2-3.md` |
| `market-news-analyst` | us-equity | news-scan | protocol lane 實跑 `fetch.py`（FMP per-ticker 48h）；SKILL.md 的 WebSearch 宏觀流程為獨立模式 | investment News lane + sector Phase 3 |
| `quant-backtest` | market-agnostic | single-ticker | technical_core 價格資料 + 11 策略模板 registry | `回測 [TICKER]`（dashboard SCRIPT_PROTOCOLS subprocess，0 LLM）；探索層，不入 investment_protocol 決策 |
| `weekly-tech-playbook` | us-equity | portfolio-level | FMP + 既有 skill caches + Codex Review（可選第二意見） | 「投資方案」/「週選方案」UI 觸發（dashboard PROTOCOL_MODEL `playbook` claude turn） |
| `economic-calendar-fetcher` | global-macro | event-scan | FMP `/stable/economic-calendar`（fmp_pool；2026-08-08 起，legacy v3 403 解除） | `產業掃描` FAST PATH `phase_prefetch.py` SOFT task `econ_calendar`（stdout inline 進 /tmp bundle）；`bridge.py` 另有獨立 inline 版 |

## 接線狀態（2026-10-04）

| 範圍 | 已確認狀態 / 處置 |
|---|---|
| Dashboard → data providers / breadth | 修正 launchd 未繼承呼叫端 API 環境；使用私有 socket 傳遞、不存 key；缺 FMP 時不停止既有 server。Preflight 改用 repo canonical breadth。Intraday partial 必揭露錯誤。|
| earnings / news / thematic / fundamentals | 修正 `ratings-historical`、`grades-consensus`、`overallScore`／`publishedDate` 欄位；事件使用 `grades`，月度推薦數仍用 `grades-historical`；sector PE 必帶日期並處理非交易日。|
| Finnhub | 拆股使用 `stock/split`；本帳戶 price-target、upgrade-downgrade、dividend2、split 仍為 403，屬權限限制，不算已恢復。|
| 其他供應商限制 | FMP 6 個選配端點 402（詳 audit）；CNN 418、CBOE PCR 403、Yahoo `^CPC` 無資料。保留 degraded／fallback，不以空值宣稱健康，不自動升級訂閱。|

> 已刪：`supply-chain-event-analyst`（V4.4，被 Nexus 取代）、`earnings-trade-analyzer`（V4.5.1，0 接線；歷史 artifact `reports/earnings_trade_analyzer_2026-04-26_*` 仍由 event index extractor 讀取）

## 生命週期評估（2026-10-04）

**結論：22 個保留現有角色、2 個適合整併、2 個降為選配。沒有證據支持直接刪除整批 skills。** 下表為架構建議；本次只修接線，未移除任何 skill、改 protocol 路由或調整權重。依據是現行 script／Dashboard／protocol 消費關係，不以「沒有 Python import」推斷無用，也不以歷史 artifact 數量推斷使用頻率。

| Skill | 建議 | 原因、替代方式與保留契約 |
|---|---|---|
| `dual-axis-skill-reviewer` | **降為選配；最先停止例行維護** | Dev 工具，沒有 daily／protocol 消費者；其 auto 軸依上游 SKILL 模板打分，不能代表本 repo 功能品質。日常檢查可用 `check_skills.py --strict` + 對應測試 + endpoint contract；質性評估仍需人工，不宣稱完全等價。|
| `weekly-tech-playbook` | **降為選配** | UI 明確按需觸發的 LLM 三籃方案；若只要觀察清單，radar + momentum + 既有委員會結果已涵蓋大部分用途。只有需要三組完整配置時才跑；第二模型意見維持 opt-in。退役前需處理 `dashboard_server.py` 的 playbook registry／UI。|
| `economic-calendar-fetcher` | **優先整併** | `sector/scripts/phase_prefetch.py` 仍呼叫它，但 `bridge.py` 另有 economic-calendar inline 取資料。可抽單一 shared calendar service，保留 CLI／日期與時區／輸出契約；FRED 時間序列不能取代未來事件日曆。|
| `retail-sector-pulse` | **第二順位整併** | daily Step 9.5、bridge、首頁與 mood 仍讀取。可併入 market-sentiment 資料層，保留 `retail_sector_pulse.json`、`trending_tickers.json` 與缺值狀態；不能因舊 retail-volume 元件退役就刪整個 skill。|
| `earnings-analyst` | 保留 | 財報分析與跨季歷史主入口；前瞻／memo／Dashboard 依賴其 cache 和來源時鐘。|
| `earnings-valuation-forecaster` | 保留；可共用估值取數 | 與 valuation-modeler 部分重疊，但 `compute_price_framework.py` 仍使用 `forecaster_blend`，Phase 1 prewarm 與 reviewer gate 亦依賴它。需先驗 anchor／transition_case／preview parity 才能替換，不能直接下架。|
| `valuation-modeler` | 保留 | DCF／comps 正式估值錨及 initiation memo 的輸入；與前瞻 scenario 角色不同。|
| `us-stock-analysis` | 保留 | Investment Fundamentals lane；可共用 FMP 取數，不能用 forecaster 替代財務品質判讀。|
| `market-news-analyst` | 保留接線；宏觀獨立流程可收斂 | Investment News lane 實跑 per-ticker `fetch.py`；泛宏觀 WebSearch 可交 news protocol，但現行事件／filings payload 仍須保留。|
| `short-contrarian-analyst` | 保留 | Protocol Phase 2 的 Burry lane／veto 檢查，有文字流程呼叫；不能以沒有直接 import 判成未使用。|
| `technical-analyst` | 保留 | Investment 技術 lane 的單股契約；底層已共享 `technical_core`，與 universe screen 不等價。|
| `portfolio-risk-manager` | 保留 | Phase 4 部位／組合風控與 `trade_plan_builder.py` 的依賴。|
| `tail-risk-analyzer` | 保留 | Investment／sector 尾部風險及交易計畫約束；一般 volatility 無法直接替代。|
| `sector-analyst` | 保留 | Sector Phase 1 產業輪動判讀；protocol 文字接線仍有效。與 theme-detector 的主題辨識不同。|
| `ic-memo-writer` | 保留按需 | 0-LLM 的報告 renderer；protocol 明確 build→compose→validate，有低維護成本與獨立輸出用途。|
| `finnhub-client` | 保留；只縮減不可用選配端點 | Canonical dual-fetch／drift 與 per-ticker news 共用依賴；少數 403 不代表 quote／metric／calendar 等整個 client 無用。|
| `fred-macro` | 保留 | Macro／regime／kill-trigger／估值折現基準；非日曆替代品。|
| `market-breadth-analyzer` | 保留 | Daily 與 sector Phase 0；提供市場參與廣度，無法用 SPY 單一報酬替代。|
| `market-sentiment-analyzer` | 保留；整併的承接者 | Daily mood／intraday 與 Investment sentiment。不可用情緒來源要揭露缺值，不能捏造中性。|
| `ftd-detector` | 保留運算核心 | `sector/ftd_yfinance.py` 真正 import repo skill；可精簡重複 fetch wrapper，不能刪 FTD 引擎。|
| `market-top-detector` | 保留運算核心 | `sector/market_top_yfinance.py` 真正 import repo skill；與 FTD 看相反市場階段，非重複訊號。|
| `theme-detector` | 保留 | 主題／產業 universe producer，被 sector、thematic、news 等消費。|
| `thematic-screener` | 保留探索層 | 把 theme cache 與短期預測組成 radar recommendations；不是 theme-detector 的同義輸出。|
| `short-term-target` | 保留探索層 | thematic in-process 與 retail pulse 仍依賴 5d 方向；可共享技術因子，移除前必須遷移這些消費者。`weights.yaml` 維持使用者手動校準。|
| `momentum-monitor` | 保留 | Daily universe screen、個股 momentum、journal 與 Dashboard；不等同單股技術 lane。|
| `quant-backtest` | 保留按需探索層 | Dashboard subprocess，0 LLM 的策略驗證；可按需求降低維護順位，但沒有已接好的等價替代入口。|

**建議實作順序**：先將 dual-axis／playbook 標為選配，再收斂 calendar 取數，最後整併 retail 的資料層。每次整併需以舊／新相同輸入比對 payload、freshness、降級狀態與 Dashboard 消費者；完成遷移後才考慮刪目錄。Thematic／短期目標／回測／playbook 維持探索層，不進委員會 buy_threshold、position_size 或 verdict。

## 🧰 `_shared`（非 skill — 跨 skill 共用模組）

| Module | 內容 |
|---|---|
| `company_context.py` | FMP company metadata 單一源（profile/peers/market-cap/employee, 24h cache）+ `SECTOR_UNIVERSE`/`SECTOR_TOP_5` |
| `fmp_supplementary.py` | quality scores / owner earnings / insider / institutional（24h cache）|
| `technical_core.py` | **V4.5 起單一源**：`fetch_history`（FMP 主 + yfinance fallback）+ `rsi_14`（Wilder）+ MA/MACD/stage/crosses。momentum-monitor 舊路徑留 shim；etf_scanner / sentiment / screen / predict 全部改 import 此處 |

---

## 市場劃分的使用方式

當未來要新增第二個市場（例：台股）時：

1. **`market-agnostic` 類**：檢視即可直接套用，頂多換 universe 檔
2. **`us-equity` 類**：每個都要寫一個 `tw-equity` 對應版本（資料源、GICS → GICS-TW 等）
3. **`global-macro` 類**：看需求，可能共用一個，或切分 `us-macro` / `tw-macro`

Protocol 檔案內用 `[framework]` / `[domain:us-equity]` HTML 註解標註哪些段落通用、哪些綁美股 — 切新市場時直接依註解替換對應段落。

---

## 維護規則

- 每加新 skill / 改接線必須同步更新此索引（`python3 scripts/check_skills.py` 會掃 cross-ref）
- **上游對齊**：9 個 fork 系 skill（源頭 [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills)，2026-04 fork）的對齊紀錄寫在各自 SKILL.md 頂部 blockquote；最近一輪全面審查 2026-08-08（V4.111.6，v3 legacy 清理批）
- 改動分類（例如原本 `us-equity` 被抽象成 `market-agnostic`）時，必須同步檢查 CLAUDE.md 對應章節
- 接線證據過時時重跑稽核（grep daily_update.sh / dashboard_server.py / protocol 文件）

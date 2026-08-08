# Skills Market Index

> Source of truth for `market` / `scope` classification + 接線狀態 of every skill in
> `skills/`. 26 skills + `_shared`. Rewritten 2026-06-11 (V4.5 audit cleanup)；2026-07-03 補 quant-backtest；2026-07-16 補 valuation-modeler (V4.69.0)；2026-08-08 econ-calendar 修復移回 Protocol lane (V4.111.5)。
> 接線證據見 `reports/SKILLS_AUDIT_2026-06-11.md`。

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
| `sector-analyst` | us-equity | sector-level | finvizfinance, yfinance | sector protocol core |
| `market-news-analyst` | us-equity | news-scan | protocol lane 實跑 `fetch.py`（FMP per-ticker 48h）；SKILL.md 的 WebSearch 宏觀流程為獨立模式 | investment News lane + sector Phase 3 |
| `quant-backtest` | market-agnostic | single-ticker | technical_core 價格資料 + 11 策略模板 registry | `回測 [TICKER]`（dashboard SCRIPT_PROTOCOLS subprocess，0 LLM）；探索層，不入 investment_protocol 決策 |
| `weekly-tech-playbook` | us-equity | portfolio-level | FMP + 既有 skill caches + Codex Review（可選第二意見） | 「投資方案」/「週選方案」UI 觸發（dashboard PROTOCOL_MODEL `playbook` claude turn） |
| `economic-calendar-fetcher` | global-macro | event-scan | FMP `/stable/economic-calendar`（fmp_pool；2026-08-08 起，legacy v3 403 解除） | `產業掃描` FAST PATH `phase_prefetch.py` SOFT task `econ_calendar`（stdout inline 進 /tmp bundle）；`bridge.py` 另有獨立 inline 版 |

## ⚠ 待處置 / 壞掉

（目前無。econ-calendar 的 legacy v3 403 已於 2026-08-08 fmp_pool 重構修復 — 實測 `/stable/economic-calendar` 回 477 筆事件，條目移回上方 Protocol lane。）

> 已刪：`supply-chain-event-analyst`（V4.4，被 Nexus 取代）、`earnings-trade-analyzer`（V4.5.1，0 接線；歷史 artifact `reports/earnings_trade_analyzer_2026-04-26_*` 仍由 event index extractor 讀取）

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

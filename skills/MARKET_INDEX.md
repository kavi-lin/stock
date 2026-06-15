# Skills Market Index

> Source of truth for `market` / `scope` classification + 接線狀態 of every skill in
> `skills/`. 23 skills + `_shared`. Rewritten 2026-06-11 (V4.5 audit cleanup)。
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
| `ftd-detector` | us-equity | market-level | yfinance | ⚠ daily 實跑 `sector/ftd_yfinance.py`（複製改寫版，引用 user-level skills 路徑）；skill 內 fmp 版閒置 — 整併 backlog |
| `market-top-detector` | us-equity | market-level | yfinance | ⚠ 同上 — daily 實跑 `sector/market_top_yfinance.py` |

## 🔵 Protocol lane（`分析` / `產業掃描` / `財報` / `ic-memo` 觸發）

| Skill | Market | Scope | Data sources | 接線 |
|---|---|---|---|---|
| `earnings-analyst` | us-equity | single-ticker | FMP /stable（20 call 並行 ×8, V4.5）| `財報 [TICKER]`；cache key (TICKER, last_earnings_date) |
| `earnings-valuation-forecaster` | us-equity | single-ticker | FMP /stable | `財報前瞻 [TICKER]`（V2.15 起 Dashboard earnings/calendar 卡片自動 morph button）+ 12M scenario |
| `ic-memo-writer` | us-equity | single-ticker | protocol history + earnings cache + company_context | `ic-memo [TICKER]` / `分析 --memo`（V3.25 deterministic 0-LLM renderer）|
| `finnhub-client` | us-equity | single-ticker | Finnhub + FMP dual fetch（calendar memoized V4.4）| protocol quant 輸入 canonical snapshot + drift audit |
| `us-stock-analysis` | us-equity | single-ticker | FMP（analyze.py；web search 違規已修 V4.4）| investment Fundamentals lane |
| `short-contrarian-analyst` | us-equity | single-ticker | FMP, yfinance | investment Phase 2 第 5 lane（Burry）；T4 仲裁刻度已修 V4.4 |
| `technical-analyst` | market-agnostic | single-ticker | shared technical_core（FMP 主源）；chart 圖片為獨立模式 | investment Phase 2 Technical lane（`analyze.py --json-only`）|
| `tail-risk-analyzer` | market-agnostic | single-ticker | yfinance | investment Phase 4 Step 3、sector Phase 4b |
| `portfolio-risk-manager` | market-agnostic | portfolio-level | positions.json, yfinance | investment Phase 4 Step 2 |
| `sector-analyst` | us-equity | sector-level | finvizfinance, yfinance | sector protocol core |
| `market-news-analyst` | us-equity | news-scan | protocol lane 實跑 `fetch.py`（FMP per-ticker 48h）；SKILL.md 的 WebSearch 宏觀流程為獨立模式 | investment News lane + sector Phase 3 |

## ⚠ 待處置 / 壞掉

| Skill | 狀態 |
|---|---|
| `economic-calendar-fetcher` | 上游壞：FMP econ-calendar legacy endpoint 403（見 memory `project_fmp_legacy_calendar_deprecated`）。sector Step 2/3 因此 silent SOFT fail — 修復 backlog |

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
- 改動分類（例如原本 `us-equity` 被抽象成 `market-agnostic`）時，必須同步檢查 CLAUDE.md 對應章節
- 接線證據過時時重跑稽核（grep daily_update.sh / dashboard_server.py / protocol 文件）

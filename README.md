# AI 投資委員會

多 Agent 投資分析系統，由三個 Claude Code protocol + 本地 Dashboard 組成。

---

## 快速開始

```bash
./open_dashboard.sh       # 啟動 Dashboard + positions API + 定時刷新
```
→ `http://localhost:8080/decisions.html`

### 常用指令（在 Claude Code 內）

| 指令 | 執行 |
|---|---|
| `產業掃描` | `sector/sector_protocol_main.md` |
| `分析 [TICKER]` | `investment/investment_protocol_v4_8.md` |
| `新聞分析 DIGEST` | `news/news_protocol_v1.md` (DIGEST mode) |
| `新聞分析 FLASH [新聞內容]` | `news/news_protocol_v1.md` (FLASH mode) |

---

## 專案結構

```
AI投資委員會/
├── bridge.py                  ← 整合所有 cache 輸出至 Dashboard/data.json
├── dashboard_server.py        ← Dashboard HTTP server + /api/positions + mtime 自動刷新
├── open_dashboard.sh          ← 一鍵啟動腳本
├── daily_update.sh            ← 每日開盤前資料更新流程
├── positions.json             ← 使用者手動持倉記錄（透過 Dashboard 表單維護）
│
├── Dashboard/                 ← Pure HTML/JS Dashboard（無框架）
│   ├── index.html             │ 總體儀表板
│   ├── decisions.html         │ 決策中心（watchlist + history + positions 整合）
│   ├── sector.html            │ 產業掃描
│   ├── news.html              │ 新聞戰情室
│   └── *.js / style.css       │ presenter / utils / i18n / data-store
│
├── investment/                ← 個股分析 protocol + logs
│   ├── investment_protocol_v4_8.md   ← V4.8 (current)
│   ├── README.md
│   └── invest_logs/
│       ├── history.json       │ 所有 session exports
│       └── YYYY-MM-DD_phase0.json
│
├── sector/                    ← 產業掃描 protocol + scripts + cache
│   ├── sector_protocol_main.md        ← V1.2 multi-file 主檔（current）
│   ├── phase_0.md / phase_1-2-3.md / phase_4-5.md / schema.md
│   ├── README.md
│   ├── ftd_yfinance.py                │ FTD 偵測
│   ├── market_top_yfinance.py         │ 市場頂部偵測
│   ├── breadth_cache/                 │ market-breadth-analyzer 輸出
│   ├── ftd_cache/                     │ ftd_yfinance 輸出
│   ├── market_top_cache/              │ market_top_yfinance 輸出
│   └── sector_logs/                   │ 產業掃描最終 JSON
│
├── news/                      ← 新聞分析 protocol + logs
│   ├── news_protocol_v1.md    ← V1 (current)
│   ├── README.md
│   └── news_logs/
│
├── reports/                   ← 所有最終 MD 報告（audit trail）
│   ├── YYYYMMDD_TICKER.md             │ 個股分析
│   ├── YYYY-MM-DD_sector_report.md    │ 產業掃描
│   └── YYYY-MM-DD_news_digest.md      │ 新聞 DIGEST
│
├── skills/                    ← Claude Code skills cache
│   └── theme-detector/cache/
│
└── archive/                   ← 歷史版本歸檔（下方說明）
```

---

## 每日開盤前流程

```bash
# Step 1  廣度數據（TraderMonty CSV，免 API key）
python3 ~/.claude/skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py \
  --output-dir sector/breadth_cache/

# Step 2  FTD 偵測（yfinance）
python3 sector/ftd_yfinance.py --output-dir sector/ftd_cache/

# Step 3  市場頂部偵測（yfinance）
python3 sector/market_top_yfinance.py --output-dir sector/market_top_cache/

# Step 4  整合 → Dashboard/data.json
python3 bridge.py
```

或執行整合的 `daily_update.sh`。

> **各產業上升趨勢比例** 沒有獨立腳本，必須透過 Claude 執行「產業掃描」後再跑 `bridge.py`。

---

## Dashboard Positions Tracker

透過 `decisions.html` 的 **+ 新增持倉** 按鈕記錄實際成交：

- 支援多筆 lots（同一 ticker 可多次進場）
- `dashboard_server.py` 寫入 `positions.json` 後自動觸發 `bridge.py`
- Card 上即時顯示 `avg_cost` / `unrealized_pct` / `lots` 數
- `bridge.py` 透過 yfinance `fast_info.last_price` 取得即時報價
- 預設每 5 分鐘自動刷新（可用 `DASH_REFRESH_SEC` 環境變數覆蓋）

---

## Archive 資料夾

```
archive/
├── old_protocols/
│   ├── investment/  ← v4_3 / v4_4 / v4_5
│   └── sector/      ← v1 / v1_1 / v1_2 / v1_2_optimized
├── old_reports/optimized/   ← 早期 optimization 實驗稿
├── old_invest_logs/         ← 舊 session_export / phase0 快取
├── old_docs/                ← 過期 Dashboard ARCHITECTURE_REVIEW / CHANGELOG
├── root_stray/              ← 早期散落在根目錄的 cache / history.md
└── breadth_page_artifacts/  ← breadth page 早期 .md 輸出
```

Archive 只保留備查，不再活動。新一代 protocol 以對應 README 為準。

---

## 環境需求

```
Python 3.9+ (建議用系統內建 /usr/bin/python3)
依賴：requests, beautifulsoup4, lxml, pandas, numpy, yfinance, finvizfinance
瀏覽器：任一現代瀏覽器（Dashboard 純靜態 HTML/JS）
Claude Code CLI（執行 3 個 protocol）
```

---

## 文件索引

- `CLAUDE.md` — Claude Code 專案 context（觸發條件、輸出路徑、工作流規則）— 精簡執行面
- `todolist.md` — 當前 backlog + session note
- `investment/README.md` — 個股分析 protocol 說明
- `sector/README.md` — 產業掃描 protocol 說明
- `news/README.md` — 新聞分析 protocol 說明
- `skills/MARKET_INDEX.md` — Skill 市場分類唯一事實來源

---

## 市場分類

目前所有 protocol 均針對美股（US equity）。Skills 依綁定程度分三類：

| 類別 | Skills | 說明 |
|---|---|---|
| 🇺🇸 **us-equity**（9） | us-stock-analysis / short-contrarian-analyst / sector-analyst / market-breadth-analyzer / market-sentiment-analyzer / market-news-analyst / theme-detector / ftd-detector / market-top-detector | 綁定美股資料源（FMP / FINRA / GICS / TraderMonty 等），換市場需重寫 |
| 🌐 **market-agnostic**（4） | momentum-monitor / technical-analyst / tail-risk-analyzer / portfolio-risk-manager | 邏輯通用，未來可原樣套用台股 / 加密 |
| 🌍 **global-macro**（1） | economic-calendar-fetcher | FMP 全球央行事件 |

Protocol 內用 `<!-- [framework] -->` / `<!-- [domain:us-equity] -->` HTML 註解標示 phase 屬框架層還是美股專屬。新增第二市場：複製整份 protocol → 替換 `[domain:us-equity]` 段落 → 新市場版本。

---

## Protocol 版本演進

| Protocol | Current | 路徑 | 主要變動 |
|---|---|---|---|
| 新聞分析 | V2.1 | `news/news_protocol_v2.md` | V2.0 基礎 + Stage 2 / REVIEW 四 agent 改 per-agent batch subagent（isolation + fanout_mode ladder）+ Phase 4 schema 抽離 + validator gate |
| 產業掃描 | V1.3 | `sector/sector_protocol_main.md` | V1.2 多檔案架構 + Phase 4a 三 agent 提案改 parallel subagent + Phase 4b Devil's Advocate 獨立 subagent + Phase 5 validator gate |
| 個股分析 | V4.8 | `investment/investment_protocol_v4_8.md` | Parallel blind analyst subagents（Phase 2 四 analyst 平行真獨立 + fallback + degraded_mode）；繼承 V4.7 Red-Team-gated bonus / Phase 2.8 adversary / Burry OVERRIDE 成本 |

**舊版本已歸檔**至 `archive/old_protocols/`：news V1.0；sector V1.0 / V1.1 / V1.2（單一檔） / V1.2 optimized；investment V4.3 / V4.4 / V4.5 / V4.6 / V4.7。

### V4.5 / V1.2 新增能力速查

| 新 Skill / 改動 | 在哪裡執行 | 作用 |
|---|---|---|
| `short-contrarian-analyst` | investment Phase 2（第五 Agent） | Burry Score 估值錨，觸發 T4 veto |
| `market-sentiment-analyzer` | investment Phase 2 Sentiment fallback；sector Phase 3 F&G | 取代 web search，提供 VIX + composite score |
| `portfolio-risk-manager` | investment Phase 4 Step 2 | Vol-adjusted 倉位上限 + correlation multiplier |
| `tail-risk-analyzer` | investment Phase 4 Step 3；sector Phase 4b Devil's Advocate（上限前 3） | 個股脆弱性評分，自動觸發產業降級 |
| `market-breadth-analyzer` | sector Phase 0 層 A（優先） | TraderMonty CSV 6 組件廣度評分，取代 AI 估算值 |
| FTD + market_top 三訊號合成 | sector Phase 0 層 C/D → `synthesized_exposure` | 最保守曝險上限，接入 Phase 4c 仲裁規則 |

---

## Dashboard 各指標資料來源

| Dashboard 指標 | 資料來源 | 更新指令 |
|---|---|---|
| 廣度綜合分數 | market-breadth-analyzer | Step 1 → Step 4 |
| FTD 信號 / 品質分數 | ftd_yfinance.py | Step 2 → Step 4 |
| 頂部風險分數 | market_top_yfinance.py | Step 3 → Step 4 |
| 市場體制 / Fear & Greed | 產業掃描 Protocol → `sector_intel.json` | `產業掃描` → Step 4 |
| 各產業上升趨勢比例 | 產業掃描 Phase 1 → `sector_intel.json` | `產業掃描` → Step 4 |

Step 1–4 指「每日開盤前流程」章節的四個 Python 指令。

---

## 工作流規則（背景與理由）

以下規則的**執行面**寫在 `CLAUDE.md`（Claude Code 每次 session 啟動會自動讀取），本節補述**理由與設計邊界**。

### 實作前確認規則

觸發條件是 ≥ 2 檔 或 單檔 ≥ 50 行。用意是讓使用者在 Claude 動手前看到改動規模、決定要不要繼續 — 避免中途才發現範圍比預期大。

**摘要表範例**：

```
## 實作計畫確認

| # | 檔案 | 動作 | 預估行數 | 說明 |
|---|------|------|----------|------|
| 1 | path/to/file.py   | 修改 | ~80 行  | 說明改什麼 |
| 2 | path/to/file.html | 修改 | ~200 行 | 說明改什麼 |
| 3 | path/to/new.sh    | 新增 | ~40 行  | 說明用途 |

總計：X 個檔案，約 Y 行，預估消耗 ~Z k tokens
設計確認後開始實作，是否繼續？
```

**行數估算粗略即可**（±30% 可接受）；**token 估算**：100 行 ≈ 1k tokens，大 HTML/JS ≈ 3–5k tokens。使用者已在指令中明說所有細節（如「只改這一行」）可跳過。

**排除**：protocol 自動產生的輸出（`reports/YYYYMMDD_TICKER.md`、`history.json` append、`invest_logs/` cache 等）是 protocol 正常流程副產品，**不計入**觸發條件，Protocol subagent 亦**不得**在 reverse-call 場景下反問使用者。

### Session 進度追蹤 + VERSION bump

**Session 定義**：使用者明確要求的 code change / 文件重構 / UX bug fix 完成一次，算一個 session。此時收尾：
- bump 整體 VERSION（大改動 → minor；小改動 → patch），同步 `VERSION` 檔 + `Dashboard/utils.js` 的 `VERSION` 常數
- `todolist.md` 頂部更新：勾 `[x]` + `Last Updated` 改今天 + `Last Session Note:` 一行摘要，新發現 bug 寫進 TODO

用意：下個 session 開始時，讀 `todolist.md` 前 30 行即可掌握進度。

**🚫 排除（Protocol 執行不算 session）**：
- 「產業掃描」「新聞分析 DIGEST / FLASH / 審核」「分析 [TICKER]」等 protocol 執行
- 跑 `bridge.py` / validator / skill script 等運維操作
- Dashboard 後端 worker 自動觸發的 protocol run

理由：protocol 產出 `reports/*.md` / `*_logs/*.json` / `Dashboard/data.json` 是**正常運作副產品**，不是使用者要求的 code change，不構成「一次 session」。Protocol subagent 在 Phase 5 / validator rc=0 / bridge 成功後直接結束，禁止反手去改 VERSION / todolist（這條規則是 2026-04-21 補的 — 當時產業掃描 subagent 誤把 protocol run 判成 session 結束，Edit VERSION 失敗導致 rc=1 鬼打牆）。

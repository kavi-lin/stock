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
| `分析 [TICKER]` | `investment/investment_protocol_v4_6.md` |
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
│   ├── investment_protocol_v4_6.md   ← V4.6 (current)
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

- `CLAUDE.md` — Claude Code 專案 context（觸發條件、新功能速查）
- `todolist.md` — 當前 backlog + session note
- `investment/README.md` — 個股分析 protocol 說明
- `sector/README.md` — 產業掃描 protocol 說明
- `news/README.md` — 新聞分析 protocol 說明

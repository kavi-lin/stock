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
| `新聞分析 DIGEST` | `news/news_protocol_v2.md` |
| `動能選股` | `skills/momentum-monitor/scripts/screen.py` |

---

## 專案結構

```
AI投資委員會/
├── bridge.py                  ← 整合所有 cache 輸出至 Dashboard/data.json
├── dashboard_server.py        ← Dashboard HTTP server + /api/positions + mtime 自動刷新
├── daily_update.sh            ← 每日開盤前資料更新流程 (核心運維)
├── positions.json             ← 使用者手動持倉記錄
│
├── Dashboard/                 ← Pure HTML/JS Dashboard (index/decisions/sector/news)
├── investment/                ← 個股分析 protocol + logs
├── sector/                    ← 產業掃描 protocol + scripts + cache
├── news/                      ← 新聞分析 protocol + logs
├── reports/                   ← 所有最終 MD 報告 (audit trail)
├── skills/                    ← Claude Code skills (momentum/valuation/supply-chain/etc)
└── archive/                   ← 歷史版本歸檔
```

---

## 每日盤前流程 (Daily Ops)

建議依序執行以下指令（或直接跑 `./daily_update.sh`）：

1.  **廣度數據**：`python3 ~/.claude/skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py --output-dir sector/breadth_cache/`
2.  **FTD 偵測**：`python3 sector/ftd_yfinance.py --output-dir sector/ftd_cache/`
3.  **頂部偵測**：`python3 sector/market_top_yfinance.py --output-dir sector/market_top_cache/`
4.  **整合數據**：`python3 bridge.py`

> **注意**：市場體制與產業趨勢比例需透過 `產業掃描` protocol 產出 `sector_intel.json` 後，再跑 `bridge.py` 才會反映在 Dashboard。

---

## 環境需求

- **Runtime**: Python 3.9.6+ (系統路徑 `/usr/bin/python3`)
- **Dependencies**: `requests`, `beautifulsoup4`, `lxml`, `pandas`, `numpy`, `yfinance`, `finvizfinance`
- **Frontend**: 現代瀏覽器（Dashboard 為純靜態 HTML/JS/CSS）
- **Tooling**: Claude Code CLI / Gemini CLI

---

## 工作流規則與設計哲學

### 1. 實作前確認 (Pre-implementation Confirmation)
**用意**：確保大規模改動前使用者已知悉影響範圍。
- **觸發**：涉及 ≥ 2 個檔案或單一檔案改動 ≥ 50 行。
- **摘要表**：必須包含「檔案、動作、預估行數、說明」。
- **排除**：`reports/` 報告、`*_logs/` 緩存 JSON、`Dashboard/data.json` 等自動化產出不計入。

### 2. Session 進度追蹤與版本管理
**Session 定義**：一次完整的人為需求開發（功能、重構、Bug fix）。
- **收尾動作**：
    1.  **Bump VERSION**：同步 `VERSION` 檔與 `Dashboard/utils.js`。
    2.  **更新 SESSION_NOTES.md 與 TODO.md**：更新市場/系統狀態、標註完成項、撰寫 `Last Session Note`。
- **🚫 排除範圍**：
    - 所有 Protocol (`產業掃描`, `新聞分析`, `分析 [TICKER]`) 的正常執行。
    - 運維指令 (`bridge.py`, `validator`, `daily_update`)。
    - 理由：Protocol run 是系統運作的副產品，不應自動觸發版本跳號或修改進度表，以防 Agent 陷入自我編輯的無限循環。

---

## 市場分類與 Skills 索引

詳細 Skill 清單、類別 (us-equity/market-agnostic) 與整合位置見 `skills/MARKET_INDEX.md`。

---

## 文件索引

- `CLAUDE.md` — Agent 核心執行規範（極簡）
- `SESSION_NOTES.md` — 市場體制狀態 + Token 優化紀錄 + AI 短期記憶
- `TODO.md` — 當前任務 backlog + 歷史進度
- `investment/README.md` — 個股分析詳解
- `sector/README.md` — 產業掃描詳解
- `news/README.md` — 新聞分析詳解

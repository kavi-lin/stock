# AI 投資委員會

多 Agent 投資分析系統，由三個 Claude Code protocol + 短期戰術層 + 本地 Dashboard 組成。

**三層時間維度設計**：
- **長期 (12 月)**：`earnings-valuation-forecaster`（基本面合理價）
- **中期 (3-6 月)**：`investment_protocol_v4_8.md`（多 lane 委員會辯論 → BUY/HOLD/SELL）
- **短期 (1-15 天)**：`thematic-screener` + `short-term-target`（**Tactical Opportunity Radar**）

---

## 快速開始

```bash
./open_dashboard.sh       # 啟動 Dashboard + positions API + 定時刷新
```
→ `http://localhost:8080/decisions.html`

### 常用指令（在 Claude Code 內）

| 指令 | 執行 | 用途 |
|---|---|---|
| `產業掃描` | `sector/sector_protocol_main.md` | 產業熱度 + macro regime → sector_intel.json |
| `分析 [TICKER]` | `investment/investment_protocol_v4_8.md` | 中期深度委員會分析（4 subagent + Burry + Red Team） |
| `新聞分析 DIGEST` | `news/news_protocol_v2.md` | RSS 新聞篩選 + 辯論 |
| `動能 [TICKER]` | `skills/momentum-monitor/scripts/momentum.py` | 個股動能評分 |
| `動能選股` | `skills/momentum-monitor/scripts/screen.py` | S&P500 動能掃描 |

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

## 每日工作流程 (Daily Workflow)

### Tier 1 — 自動化（每日早上跑一次）

```bash
./daily_update.sh   # 6 個 step，全程約 3-5 分鐘
```

| Step | 動作 | 輸出 |
|---|---|---|
| 1 | 市場廣度分析（TraderMonty CSV） | `sector/breadth_cache/` |
| 2 | FTD 偵測（yfinance） | `sector/ftd_cache/` |
| 3 | 市場頂部偵測（yfinance） | `sector/market_top_cache/` |
| 4 | FRED 宏觀數據（利率/通膨/就業/信用） | `skills/fred-macro/cache/` |
| 5 | 整合所有 cache → Dashboard | `Dashboard/data.json` |
| 6 | **Thematic Screener**（Tactical Opportunity Radar） | `skills/thematic-screener/data/recommendations/<DATE>.json` |

> **依賴**：Step 6 需要 `theme-detector` cache 存在（透過 `產業掃描` protocol 產生）。Cache > 7 天舊會跳過。

### Tier 2 — 每日手動（瀏覽推薦 + 視需求深度分析）

1. **開 Dashboard**：`./open_dashboard.sh` → `http://localhost:8080`
2. **看 Tactical 推薦**：`cat skills/thematic-screener/data/recommendations/<DATE>.json | jq` 或在 Claude Code 內請我整理
3. **想做交易**：對特定 ticker 跑 `分析 [TICKER]`（中期委員會視角）或讀短期推薦的 `trading_meta`（stop / position size / exit trigger）
4. **想看市場狀態**：`產業掃描` 重新跑或讀 latest `sector_intel.json`

### Tier 3 — 每週末手動（戰術層校準）

```bash
python3 skills/short-term-target/scripts/weekly_review.py
```
→ `reports/SHORT_TERM_WEEKLY_<DATE>.md`

報告包含：per-horizon hit rate / per-theme alpha / worst cases / suggested weights 調整。

**規則**：tool **永不**自動覆寫 config。看完報告，決定是否手動編輯 `skills/short-term-target/config/weights.yaml` 並 bump `weights_version`。

### Tier 4 — 不定期（手動）

| 指令 | 用途 |
|---|---|
| `分析 [TICKER]` | 中期深度委員會分析（5-10 分鐘 + tokens） |
| `產業掃描` | 重新跑全市場產業掃描（更新 sector_intel + theme-detector） |
| `python3 skills/finnhub-client/scripts/run_dual_fetch.sh --tickers X` | 手動補 dual-fetch snapshot（投資協議自動會跑） |
| `python3 investment/scripts/backtest_postmortem.py` | 手動回測既有 reports 的決策準確度 |
| `python3 skills/finnhub-client/scripts/audit_drift_check.py` | 檢查 Finnhub vs FMP 跨 provider drift |

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
- `plan_short.md` — 短期戰術系統規劃（含 Gemini/ChatGPT review 整合）
- `investment/README.md` — 個股分析詳解
- `sector/README.md` — 產業掃描詳解
- `news/README.md` — 新聞分析詳解
- `skills/short-term-target/README.md` — 短期目標價 skill 詮釋指引
- `skills/thematic-screener/README.md` — 戰術推薦聚合 skill 用法
- `skills/finnhub-client/README.md` — dual-fetch + audit drift 用法

---

## 腳本用途速查（Script Index）

### Ops / 自動化（被 daily_update.sh 串起）

| 腳本 | 用途 | 觸發 |
|---|---|---|
| `daily_update.sh` | 6 step 全自動 daily refresh | 每日早上手動或 cron |
| `bridge.py` | 整合所有 cache → `Dashboard/data.json` | daily_update.sh Step 5 |
| `dashboard_server.py` | Local HTTP server + positions API + mtime auto-refresh | `./open_dashboard.sh` |
| `sector/ftd_yfinance.py` | Follow-Through Day 偵測 | daily_update.sh Step 2 |
| `sector/market_top_yfinance.py` | 市場頂部偵測 | daily_update.sh Step 3 |
| `skills/fred-macro/scripts/fetch.py` | FRED 12+ series + regime signals | daily_update.sh Step 4 |
| `skills/thematic-screener/scripts/screen.py` | Top N themes × Top M movers → recommendations log | daily_update.sh Step 6 |

### 戰術層（Tactical Opportunity Radar）— 1d/5d/15d 視角

| 腳本 | 用途 | 觸發 |
|---|---|---|
| `skills/short-term-target/scripts/predict.py <TICKER>` | 單股 1d/5d/15d 目標價 + confidence breakdown + trading meta | 手動 OR 被 thematic-screener 呼叫 |
| `skills/short-term-target/scripts/weekly_review.py` | 週末校準報告（hit rate / alpha / 建議 weights 調整） | 每週末手動 |
| `skills/short-term-target/config/weights.yaml` | 手動可編輯的 α/β/γ 權重 + freshness threshold + benchmark map | 手動編輯 |

### 投資協議層（中期 3-6 月）— `分析 [TICKER]` 內部使用

| 腳本 | 用途 | 觸發 |
|---|---|---|
| `investment/scripts/validate_phase0.py` | Phase 0 macro JSON 校驗 gate | protocol Phase 0 末段 |
| `investment/scripts/validate_session_export.py` | Phase 5 export JSON 校驗 gate | protocol Phase 5 末段 |
| `investment/scripts/backtest_postmortem.py` | 掃 reports/ 過去 N 天，比對 yfinance 實際走勢 → 找 phase 失準點 | 手動，回顧時用 |
| `skills/finnhub-client/scripts/dual_fetch.py` | 同時抓 Finnhub (scoring) + FMP (audit)，物理隔離 _audit | protocol Phase 1 PM inline |
| `skills/finnhub-client/scripts/diff_tool.py` | Finnhub vs FMP side-by-side 9 欄位 diff | 手動 ad-hoc |
| `skills/finnhub-client/scripts/audit_drift_check.py` | 掃過去 N 天 _audit log，找系統性 provider drift | 每週手動 |
| `skills/finnhub-client/scripts/finnhub_client.py` | 共用 Finnhub API client（throttle/cache/retry） | 被其他 finnhub-* 腳本 import |

### 動能 / 主題層

| 腳本 | 用途 | 觸發 |
|---|---|---|
| `skills/momentum-monitor/scripts/momentum.py <TICKER>` | 個股動能 0-100 分 + 訊號清單 | `動能 [TICKER]` |
| `skills/momentum-monitor/scripts/screen.py` | S&P500 動能批次掃描 | `動能選股` |
| `skills/momentum-monitor/scripts/journal.py` | 5/20/60d forward return 追蹤 | `更新 journal` |
| `skills/theme-detector/scripts/theme_detector.py` | 17 主題（v0.2 後 21 個）熱度 + lifecycle 偵測 | 自動由 sector protocol 觸發；可獨立跑 |
| `skills/earnings-valuation-forecaster/scripts/forecast.py` | 12 個月基本面合理價 (Bull/Base/Bear) | 手動 |

---

## Tactical Opportunity Radar — 短期戰術層說明

**目的**：補足 investment_protocol 的 1-15 天空白。**完全並行運作不影響投資協議決策**。

```
每天 (auto):
  daily_update.sh Step 6
    → thematic-screener
        → 讀 theme-detector cache (Top 5 themes by heat)
        → 對每個 theme 的 representative_stocks
            → 呼叫 short-term-target.predict() (subprocess)
        → 加 concentration WARNING (同主題 ≥2 picks → 標警示，**不移除**)
        → 加 regime snapshot (SPY/RSI/MA50/VIX/FRED)
    → 寫 data/recommendations/<DATE>.json

每週末 (manual):
  weekly_review.py
    → 讀過去 7 天 recommendations
    → 抓 yfinance 實際走勢
    → 算 per-horizon hit rate + per-theme alpha + worst cases
    → 給 suggested weights 調整建議（不自動套用）
    → 輸出 reports/SHORT_TERM_WEEKLY_<DATE>.md

校準（你手動決定）:
  edit skills/short-term-target/config/weights.yaml
  → bump weights_version (e.g. v0.1.0 → v0.1.1)
  → 未來預測自動 tag 新版本，可做 before/after 比較
```

### 與既有系統的關係

| 系統 | 關係 |
|---|---|
| `investment_protocol_v4_8.md` | **完全不影響**。並行運作 |
| `theme-detector` | 上游：thematic-screener 讀其 cache |
| `fred-macro` | 上游：thematic-screener 讀其 cache 做 regime snapshot |
| `dual_fetch.py` | 兄弟：thematic-screener 也會嘗試讀其 scoring snapshot（best-effort） |
| `momentum-monitor` | 獨立並行：仍可獨立用，但不再是主推薦來源 |
| `earnings-valuation-forecaster` | 互補時間維度：12mo vs 1-15d |

### KPI gate（自我退役機制）

連續 8 週 5d hit rate < 50% **OR** 中位 alpha vs benchmark < 0% (N≥30) → 整套 thematic-screener 退役。Per `plan_short.md §6 + §12.H`。

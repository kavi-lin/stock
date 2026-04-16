# AI 投資委員會 — Claude Code Project Context

> **系統版本：v1.7.0**（實際值以根目錄 `VERSION` 檔與 `Dashboard/utils.js` 的 `VERSION` 常數為準；兩者必須同步；每個 session 結束必須 bump）

## 專案說明
這是一套多 Agent 投資分析系統，包含三個 protocol。

## Protocol 檔案位置
- **新聞分析**: `news/news_protocol_v2.md` ← V2.0（RSS 兩階段漏斗 + 5 agent 圓桌 + Triage 人類審核 + Shallow Digest 保留）
- **產業掃描**: `sector/sector_protocol_main.md` ← V1.2（多檔案架構；子檔案：`phase_0.md` / `phase_1-2-3.md` / `phase_4-5.md` / `schema.md`）
- **個股分析**: `investment/investment_protocol_v4_6.md` ← V4.6（anti-conservatism：雙軌 entry + STAGED_ENTRY + consensus bonus + directional macro + 移除 VOLATILE 重複懲罰）

### 舊版本（已歸檔至 `archive/old_protocols/`）
- `archive/old_protocols/news/` — V1.0
- `archive/old_protocols/sector/` — V1.0 / V1.1 / V1.2（單一檔版）/ V1.2 optimized
- `archive/old_protocols/investment/` — V4.3 / V4.4 / V4.5

## 觸發方式
- 「新聞分析 DIGEST」→ 執行 news_protocol_v2，MODE: DIGEST（先跑 `news/fetch_news_rss.py` 產 raw.json → Stage 1 triage → Stage 2 deep ≤5 則 → `review_status: reviewed`）
- 「新聞分析 FLASH [新聞內容]」→ 執行 news_protocol_v2，MODE: FLASH（跳過 Stage 1，直接 Deep Debate → `review_status: pending`，不 patch cache）
- 「新聞分析 審核 [headline]」→ 執行 news_protocol_v2，MODE: REVIEW（擴展 FLASH 辯論 → `review_status: reviewed` + patch cache）
- 「產業掃描」→ 執行 sector_protocol_main（先讀主檔，再按需載入子檔）
- 「分析 [TICKER]」→ 執行 investment_protocol_v4_6

## V4.5 / V1.2 新增能力速查
| 新 Skill / 改動 | 在哪裡執行 | 作用 |
|---|---|---|
| `short-contrarian-analyst` | investment Phase 2（第五 Agent）| Burry Score 估值錨，觸發 T4 veto |
| `market-sentiment-analyzer` | investment Phase 2 Sentiment fallback；sector Phase 3 F&G | 取代 web search，提供 VIX + composite score |
| `portfolio-risk-manager` | investment Phase 4 Step 2 | Vol-adjusted 倉位上限 + correlation multiplier |
| `tail-risk-analyzer` | investment Phase 4 Step 3；sector Phase 4b Devil's Advocate（上限前 3） | 個股脆弱性評分，自動觸發產業降級 |
| `market-breadth-analyzer` | sector Phase 0 層 A（優先）| TraderMonty CSV 6組件廣度評分，取代 AI 估算值 |
| FTD + market_top 三訊號合成 | sector Phase 0 層 C/D → `synthesized_exposure` | 最保守曝險上限，接入 Phase 4c 仲裁規則 |

## 檔案路徑規則
**最終報告（MD）→ 統一存放於 `reports/`**
- `reports/YYYYMMDD_TICKER.md` — 個股分析完整報告
- `reports/YYYY-MM-DD_sector_report.md` — 產業掃描最終報告
- `reports/YYYY-MM-DD_news_digest.md` — 新聞 DIGEST 彙整報告
- `reports/YYYY-MM-DD_HHMM_news_flash.md` — 新聞 FLASH 單則報告
- `reports/YYYYMMDD_theme_detector_*.md` — 主題偵測最終報告

**中繼 Cache（JSON）→ 各模組的 `_logs/` / `cache/` 目錄**
- `sector/sector_logs/YYYY-MM-DD_sector_intel.json` — 產業 cache
- `sector/breadth_cache/market_breadth_YYYY-MM-DD_*.json` — 廣度分析 cache（market-breadth-analyzer 輸出）
- `sector/breadth_cache/market_breadth_history.json` — 廣度歷史趨勢（滾動 20 筆）
- `sector/ftd_cache/ftd_detector_YYYY-MM-DD_*.json` — FTD 偵測 cache（ftd_yfinance.py 輸出）
- `sector/market_top_cache/market_top_YYYY-MM-DD_*.json` — 市場頂部偵測 cache（market_top_yfinance.py 輸出）
- `investment/invest_logs/YYYY-MM-DD_phase0.json` — 個股 macro cache
- `investment/invest_logs/history.json` — 歷史 session 記錄
- `news/news_logs/YYYY-MM-DD_digest.json` — 新聞 cache
- `skills/theme-detector/cache/theme_detector_YYYY-MM-DD_*.json` — 主題偵測 JSON cache

## Scripts & 常用指令

### 每日標準流程（開盤前依序執行）

> 產業上升趨勢比例需額外執行「產業掃描」才會更新（見下方）

```bash
# Step 1｜廣度數據（TraderMonty CSV，免 API key）
python3 ~/.claude/skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py \
  --output-dir sector/breadth_cache/

# Step 2｜FTD 偵測（yfinance，免 API key）
python3 sector/ftd_yfinance.py --output-dir sector/ftd_cache/

# Step 3｜市場頂部偵測（yfinance，免 API key）
python3 sector/market_top_yfinance.py --output-dir sector/market_top_cache/

# Step 4｜整合所有 cache → Dashboard/data.json
python3 bridge.py
```

#### 各指標資料來源速查
| Dashboard 指標 | 資料來源 | 更新指令 |
|---|---|---|
| 廣度綜合分數 | market-breadth-analyzer | Step 1 → Step 4 |
| FTD 信號 / 品質分數 | ftd_yfinance.py | Step 2 → Step 4 |
| 頂部風險分數 | market_top_yfinance.py | Step 3 → Step 4 |
| 市場體制 / Fear&Greed | 產業掃描 Protocol → sector_intel.json | `產業掃描` → Step 4 |
| **各產業上升趨勢比例** | 產業掃描 Phase 1 → sector_intel.json | `產業掃描` → Step 4 |

> **注意**：各產業上升趨勢比例無獨立腳本，必須透過 Claude 執行「產業掃描」後再跑 `bridge.py`。

### 其他腳本
- `scripts/` — Python 輔助腳本（yfinance, finvizfinance, pandas）

## 環境
- Python: `/usr/bin/python3` (3.9.6)
- 已安裝: requests, beautifulsoup4, lxml, pandas, numpy, yfinance, finvizfinance

## 實作前確認規則（大量改動必須遵守）

**觸發條件**：預計改動 ≥ 2 個檔案，或單檔改動 ≥ 50 行時，必須在實作前輸出一張改動摘要表，等待確認後才開始動手。

**摘要表格式**：

```
## 實作計畫確認

| # | 檔案 | 動作 | 預估行數 | 說明 |
|---|------|------|----------|------|
| 1 | path/to/file.py | 修改 | ~80 行 | 說明改什麼 |
| 2 | path/to/file.html | 修改 | ~200 行 | 說明改什麼 |
| 3 | path/to/new.sh | 新增 | ~40 行 | 說明用途 |

總計：X 個檔案，約 Y 行，預估消耗 ~Z k tokens
設計確認後開始實作，是否繼續？
```

**規則細節**：
- 改動行數為估算值（±30% 均可接受），重點是讓使用者知道規模
- Token 估算粗略即可：100 行 ≈ 1k tokens，大型 HTML/JS 檔案 ≈ 3–5k tokens
- 使用者回覆「繼續」「ok」「確認」或任何肯定語意 → 才開始實作
- 若使用者已在指令中明確說明所有細節（如「只改這一行」）→ 可跳過此步驟

---

## Session 進度追蹤規則
**每個 session 結束前，必須更新 `todolist.md`：**
1. 將本次完成的項目標記為 `[x]`（並加上刪除線）
2. 在檔案頂部 `> Last Updated:` 更新為今天日期
3. 若有新發現的工作或 bug，加入對應路線的 TODO 清單
4. **在檔案頂部加入 `> Last Session Note:`，一行摘要說明本次做到哪邊**

目的：下一個 session 開始時，先讀 `todolist.md` 前 30 行，即可掌握目前進度。

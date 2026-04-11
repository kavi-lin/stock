# AI 投資委員會 — Claude Code Project Context

## 專案說明
這是一套多 Agent 投資分析系統，包含三個 protocol。

## Protocol 檔案位置
- **新聞分析**: `news/news_protocol_v1.md`
- **產業掃描**: `sector/sector_protocol_v1_1.md` ← V1.1（新增 market-sentiment-analyzer + tail-risk）
- **個股分析**: `investment/investment_protocol_v4_5.md` ← V4.5（新增 Contrarian Agent + vol-sizing + tail-risk）

### 舊版本（保留備查）
- `sector/sector_protocol_v1.md` — V1.0
- `investment/investment_protocol_v4_4.md` — V4.4

## 觸發方式
- 「新聞分析 DIGEST」→ 執行 news_protocol，MODE: DIGEST
- 「新聞分析 FLASH [新聞內容]」→ 執行 news_protocol，MODE: FLASH
- 「產業掃描」→ 執行 sector_protocol_v1_1
- 「分析 [TICKER]」→ 執行 investment_protocol_v4_5

## V4.5 / V1.1 新增能力速查
| 新 Skill | 在哪裡執行 | 作用 |
|---|---|---|
| `short-contrarian-analyst` | investment Phase 2（第五 Agent）| Burry Score 估值錨，觸發 T4 veto |
| `market-sentiment-analyzer` | investment Phase 2 Sentiment fallback；sector Phase 3 F&G | 取代 web search，提供 VIX + composite score |
| `portfolio-risk-manager` | investment Phase 4 Step 2 | Vol-adjusted 倉位上限 + correlation multiplier |
| `tail-risk-analyzer` | investment Phase 4 Step 3；sector Phase 4b Devil's Advocate | 個股脆弱性評分，自動觸發產業降級 |

## 檔案路徑規則
**最終報告（MD）→ 統一存放於 `reports/`**
- `reports/YYYYMMDD_TICKER.md` — 個股分析完整報告
- `reports/YYYY-MM-DD_sector_report.md` — 產業掃描最終報告
- `reports/YYYY-MM-DD_news_digest.md` — 新聞 DIGEST 彙整報告
- `reports/YYYY-MM-DD_HHMM_news_flash.md` — 新聞 FLASH 單則報告
- `reports/YYYYMMDD_theme_detector_*.md` — 主題偵測最終報告

**中繼 Cache（JSON）→ 各模組的 `_logs/` 目錄**
- `sector/sector_logs/YYYY-MM-DD_sector_intel.json` — 產業 cache
- `investment/invest_logs/YYYY-MM-DD_phase0.json` — 個股 macro cache
- `investment/invest_logs/history.json` — 歷史 session 記錄
- `news/news_logs/YYYY-MM-DD_digest.json` — 新聞 cache
- `skills/theme-detector/cache/theme_detector_YYYY-MM-DD_*.json` — 主題偵測 JSON cache

## Scripts
- `scripts/` — Python 輔助腳本（yfinance, finvizfinance, pandas）

## 環境
- Python: `/usr/bin/python3` (3.9.6)
- 已安裝: requests, beautifulsoup4, lxml, pandas, numpy, yfinance, finvizfinance

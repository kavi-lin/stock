# AI 投資委員會 — Claude Code Project Context

> **系統版本**：權威值在根目錄 `VERSION` 檔 + `Dashboard/utils.js` 的 `VERSION` 常數，兩者必須同步。專案背景、市場分類、版本演進見 `README.md`。

## Protocol 觸發

| 使用者輸入 | 執行檔 | 備註 |
|---|---|---|
| `產業掃描` | `sector/sector_protocol_main.md`（V1.3） | 先讀主檔，按需載入 `phase_0.md` / `phase_1-2-3.md` / `phase_4-5.md` / `schema.md` |
| `分析 [TICKER]` | `investment/investment_protocol_v4_8.md` | Phase 5 export shape: `investment/phase5_export_schema.md` |
| `新聞分析 DIGEST` | `news/news_protocol_v2.md`（MODE: DIGEST） | 先跑 `news/fetch_news_rss.py` → Stage 1 triage → Stage 2 deep ≤5 則 → `review_status: reviewed` |
| `新聞分析 FLASH [新聞內容]` | `news/news_protocol_v2.md`（MODE: FLASH） | 跳過 Stage 1 直接 Deep Debate，`review_status: pending`，不 patch cache |
| `新聞分析 審核 [headline]` | `news/news_protocol_v2.md`（MODE: REVIEW） | 擴展 FLASH 辯論 → `review_status: reviewed` + patch cache |
| `動能 [TICKER]` / `momentum [TICKER]` / `/momentum-monitor [TICKER]` | `skills/momentum-monitor/scripts/momentum.py` | MD 表格（volume / MA cross / short interest / composite score） |
| `動能選股` / `momentum screen` / `/momentum-screen [args]` | `skills/momentum-monitor/scripts/screen.py` | 批次掃描 universe（預設 S&P 500）→ MD 表格 + CSV |
| `更新 journal` / `journal stats` / `/momentum-journal <snapshot\|update\|stats>` | `skills/momentum-monitor/scripts/journal.py` | 累積 screen 結果 + 前向收益 → 信號勝率 |

Skill 市場分類（us-equity / market-agnostic / global-macro）見 `skills/MARKET_INDEX.md`。

## Validator Gate（必須 rc=0 才算完成）

| Protocol | Validator | Schema |
|---|---|---|
| 新聞 Phase 4 | `news/scripts/validate_digest_output.py` | `news/digest_output_schema.md` |
| 產業 Phase 5 | `sector/scripts/validate_sector_intel.py` | `sector/schema.md` |
| 個股 Phase 5 | `investment/scripts/validate_session_export.py` | `investment/phase5_export_schema.md` |

## 輸出路徑

**最終 MD → `reports/`**
- `YYYYMMDD_TICKER.md` — 個股分析
- `YYYY-MM-DD_sector_report.md` — 產業掃描
- `YYYY-MM-DD_news_digest.md` / `YYYY-MM-DD_HHMM_news_flash.md` — 新聞 DIGEST / FLASH
- `YYYYMMDD_theme_detector_*.md` — 主題偵測

**Cache JSON → 各模組目錄**
- `sector/sector_logs/` / `sector/breadth_cache/`（含 `market_breadth_history.json` 滾動 20 筆） / `sector/ftd_cache/` / `sector/market_top_cache/`
- `investment/invest_logs/`（含 `history.json`）
- `news/news_logs/`
- `skills/theme-detector/cache/` / `skills/momentum-monitor/cache/` / `skills/momentum-monitor/journal/`（`journal.jsonl` + `stats.json`）

## 每日盤前指令（開盤前依序）

```bash
python3 ~/.claude/skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py --output-dir sector/breadth_cache/
python3 sector/ftd_yfinance.py --output-dir sector/ftd_cache/
python3 sector/market_top_yfinance.py --output-dir sector/market_top_cache/
python3 bridge.py   # 整合所有 cache → Dashboard/data.json
```

各產業上升趨勢比例 + 市場體制 / F&G 須透過 Claude 執行「產業掃描」protocol 寫入 `sector_intel.json`，再跑 `bridge.py` 才會進 Dashboard。

## 環境

Python `/usr/bin/python3` 3.9.6。已裝：requests / beautifulsoup4 / lxml / pandas / numpy / yfinance / finvizfinance。

---

## 實作前確認規則

**觸發**：使用者要求的 code change / 文件重構，預計 ≥ 2 檔 或 單檔 ≥ 50 行時，實作前先輸出摘要表：

```
| # | 檔案 | 動作 | 預估行數 | 說明 |
|---|------|------|----------|------|
| 1 | path/to/file | 修改/新增 | ~N 行 | 改什麼 |
```

加一句「總計 X 檔、~Y 行、~Z k tokens — 確認後開始實作？」，待使用者「繼續」/「ok」/「確認」才動手。

**排除**：protocol 自動產出（`reports/*.md` / `*_logs/*.json` / `Dashboard/data.json`）不計入觸發，也不得反問使用者。

細則：行數 ±30% 可接受；100 行 ≈ 1k tokens、大 HTML/JS ≈ 3–5k；使用者已明確說「只改這一行」可跳過。

## Session 進度追蹤規則

Session 結束 = **使用者要求的 code change / 文件重構 / bug fix 完成**。此時：
1. bump VERSION（大改動 → minor；小改動 → patch），同步 `VERSION` 檔 + `Dashboard/utils.js`
2. 更新 `todolist.md`：勾 `[x]` 完成項 + 更新 `Last Updated` + 寫 `Last Session Note:` 一行摘要（新發現 bug 加到對應 TODO 清單）

**🚫 排除**：「產業掃描」/「新聞分析 DIGEST|FLASH|審核」/「分析 [TICKER]」等 protocol 執行、`bridge.py` / validator / skill script 運維操作、Dashboard 後端觸發的 protocol run 都 **不算 session** — 禁止 bump VERSION、禁止改 todolist。Protocol subagent 在 validator rc=0 + bridge 成功後直接結束。

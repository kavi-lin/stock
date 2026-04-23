# INTEL COMMAND — Session Notes & System State

> **Last Updated**: 2026-04-23
> **Role**: This file serves as the "Short-term Memory" and "Handoff Cache" for AI Agents. It contains market regime states, token optimization logs, and data integrity notes. **Task backlog has been moved to TODO.md.**

---

## 🟢 Latest Session Note
**修正 Leader 按鈕錯誤 + 補上 MACD 欄位**（2026-04-23）。
- **(1) Bug Fix**：`matchesFilter` 的 `onlyHotSectors` 邏輯呼叫不存在的 `DataStore.getCached()`，導致「真動能領航者」按鈕彈出 TypeError。改為在 `loadMomentumData` 時將 `data.market` 存入 `_state.market`，過濾時直接讀取。
- **(2) i18n Fix**：`preset_leaders` 標籤在 `i18n.js` 中英文皆缺失，導致按鈕無文字。補上兩個語系的 label + tooltip。
- **(3) MACD 欄位**：`screen.py` `_row_from_payload` 新增五個欄位（`macd_line`, `macd_signal`, `macd_hist`, `macd_bullish_cross`, `macd_bearish_cross`）。Dashboard 新增 `macdCell()` 與 MACD 表頭欄，以 `▲/▼` 顯示方向、`⚡` 標記當日交叉。需重新執行 `動能選股` 才能更新快取。
- **(4) 系統版本**：bump VERSION 1.37.0 → **1.38.0**。

---

## 🟡 Previous Session Note
- **(5) 數據完整性**：修正跨頁導航導致的 scan banner 丟失問題。`page-sector.js` 增加 `Ended_at` 時間戳檢查（5 分鐘效期）。
- **(4) 決策路由**：AnalyzeQueue 整合完成，正式解決重複分析請求問題。
- **(3) UX 優化**：更新 `i18n.js` 中的 `scan_confirm` 文案，明確預告 Preflight 階段所需時間（1-3 分鐘）。

---

## 🔵 Momentum Context (Multi-Universe)
**動能選股 Universe 整合機制**。
- **(1) 市場狀態**：目前預設掃描 `all` (SP500 + Nasdaq 100 + Watchlist)，總數 527 檔。
- **(5) 數據結構**：CSV/JSON 新增 `in_nasdaq100` 布林欄位。
- **(4) UI 連動**：Dashboard 預設顯示 Top 200，但透過 `isWatchlist` 邏輯，自選股不受 Universe 篩選器影響，始終顯示。

---

<details>
<summary>📜 <strong>Older system history</strong> (collapsed summary)</summary>

- **v1.36.1**: bug.md 四張票一次清（橫幅、並發、Preflight）。
- **v1.35.0**: 動能選股盤中量能污染修正（intraday partial-bar scale-up）。
- **v1.32.0**: Dashboard 大改版 M1+M2+M3（今日裁決 Hero + 跨模組智能訊號 ⭐）。
- **v1.28.0**: 產業頁 Today's Verdict 結構化物件產出。
- **v1.20.0**: 動能選股加入 GICS 產業分類維度。
- **v1.17.0**: 動能選股改為客戶端即時篩選（Top-N 下放）。
- **v1.10.0**: 引入 `momentum-monitor` 新 skill。
- **v1.3.0**: Sector Protocol V1.3 架構補齊（平行 Subagent + Validator）。

</details>

---

## 📋 Bridge 資料流對照（System Manifest）

| Protocol | 輸出 Log | Bridge 讀取欄位 | Dashboard 顯示 |
|---|---|---|---|
| `investment_v4_8` | `invest_logs/history.json` | `final_decision`, `score`, `macro_alignment`, `key_risks` | decisions 頁全部 |
| `sector_v1.3` | `sector_logs/*_intel.json` | `market_regime`, `_phase0` (breadth/FTD/MT), `today_verdict` | index + sector |
| `news_v2.1` | `news_logs/*_digest.json` | `verdicts[]`, `trump_signals`, `catalysts` | news 頁 + sidebar |
| `breadth_analyzer`| `breadth_cache/*.json` | 6 組件 breadth + trend | index 廣度 gauge |
| `positions.json`  | — | lots → avg_cost / live_position | decisions 持倉 |

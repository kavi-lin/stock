# INTEL COMMAND — Todo List
> Last Updated: 2026-04-13
> Last Session Note: 路線C 全部完成 — C-BREADTH ✅ C-FTD ✅ C-TOP ✅；market_top_yfinance.py 寫好，bridge.py 加入 data.market_top{}，breadth.html 新增 Row 6 Market Top Detector 區塊

---

## ✅ 已完成

- [x] Dashboard 基本頁面架構（index / sector / news / history）
- [x] CSS 變數主題系統（dark/light mode）
- [x] i18n 雙語支援（zh/en）
- [x] `bridge.py` 雛形（讀取 invest_logs + news_logs → data.json）
- [x] `viewReport()` 彈窗支援 .md 和 .html 報告
- [x] System Logs debug console
- [x] `ARCHITECTURE_REVIEW.md` 架構分析文件
- [x] **[BRIDGE-1]** 修復 `fear_greed` 擷取路徑 bug（`_phase3.political_overlay.fear_greed_index`，值 15）
- [x] **[BRIDGE-2]** 新增 `sectors[]` 陣列擷取，`sector.html` 改從 `data.json.sectors` 讀取
- [x] **[BRIDGE-3]** 新增 warm / cold / avoid sectors 至 market summary
- [x] **[BRIDGE-4]** 新增 `macro_multiplier` 和 `exposure_ceiling`（sector.html 顯示真實值）
- [x] **[SECTOR-1/2/3]** Sector heatmap 改用真實資料，verdict badge + proxy_etf + risk_flags
- [x] **[LAUNCH-1]** 快速啟動引擎：輸入 ticker → `分析 TICKER` 指令 + copy-to-clipboard
- [x] **[LAUNCH-2]** 修正 `index.html` 導航 `href="#"` → `href="history.html"`

---

## 🚀 路線 A — 現有資料補完（零新 skill，純利用 logs）

### A1 · `watchlist.html` 進場雷達（新頁面）

- [x] ~~**[A1-BRIDGE]** `bridge.py` 補出 watchlist 專用欄位~~
  - ~~`watch_conditions` (entry_A/B/C) → `recent_analysis[].watch_conditions`~~
  - ~~`key_risks[]`, `risk_reward_ratio`, `position_size_pct`, `avg_confidence`, `time_horizon`~~
  - ~~新增 `binary_risks[]`, `divergence_watch[]`, `breadth{}` 欄位~~

- [x] ~~**[A1-PAGE]** 建立 `watchlist.html`~~
  - ~~分兩區：ACTIVE（EXECUTE）/ WAITING（watch_conditions）~~
  - ~~每張卡：entry_A/B/C 觸發條件 + key_risks 標籤 + R/R + 信心指數 + DA badge~~
  - ~~Filter tabs (ALL / ACTIVE / WAITING)、Summary stats row~~

- [x] ~~**[A1-NAV]** 所有頁面 sidebar 加入「進場雷達」導航（radar 圖示）~~

### A2 · 強化 `index.html` 主儀表板

- [x] ~~**[A2-WARN]** `_phase0.warning_flags` 頂部警告 banner~~
  - ~~Death_Cross / Extreme_Fear 旗幟顯示，附 Uptrend Ratio 百分比~~
- [x] ~~**[A2-BREADTH]** `uptrend_ratio_overall` mini gauge（Market Regime 卡底部橫條）~~

### A3 · 強化 `sector.html` 產業掃描

- [x] ~~**[A3-ROTATION]** Sector tile 加入 `rotation_signal`（▲INFLOW / ▼OUTFLOW）+ uptrend bar~~
- [x] ~~**[A3-DIVERGE]** 底部新增 `sector_divergence_watch` 區塊（signal + action + description）~~
- [x] ~~**[A3-NOTES]** Strategy Notes 改從真實資料生成（HOT/COLD sector key_reason + DA note）~~

### A4 · 強化 `news.html` 即時新聞

- [x] ~~**[A4-CALENDAR]** 右側欄 `upcoming_binary_risks` 倒數（T-Xd + 受影響產業 tags）~~
- [x] ~~**[A4-TRUMP]** `trump_trade_signals[]` 政策交易信號卡片（右側欄新增 Policy Trade Signals 區塊）~~

### A5 · 強化 `history.html` 決策歷史

- [x] ~~**[A5-RISKS]** 每張卡展開顯示 `key_risks[]` 標籤~~
- [x] ~~**[A5-COND]** 顯示 `watch_conditions.entry_A/B/C` 觸發條件（CANCEL 卡才顯示）~~

---

## 📅 路線 B — `calendar.html` 財報 & 事件日曆

- [ ] **[B-BRIDGE]** `bridge.py` 導出 `upcoming_binary_risks[]` + `sector_news_sentiment{}`
- [ ] **[B-PAGE]** 建立 `calendar.html`
  - 週曆視圖，顯示財報日期、FOMC、地緣政治 binary events
  - 每個事件顯示受影響產業 + direction（bullish/bearish/binary）
  - 資料來源：`_phase3.upcoming_binary_risks`（已有）+ `earnings-calendar` skill（補完）
- [ ] **[B-SKILL]** 整合 `earnings-calendar` skill（FMP API），產出 JSON cache 讓 bridge 讀取

---

## 📊 路線 C — `breadth.html` 市場廣度雷達

- [x] ~~**[C-BRIDGE]** `bridge.py` 導出 `_phase0` 完整廣度資料~~
  - ~~`breadth_components{}`, `warning_flags[]`, `uptrend_ratio_overall`, `cycle_phase`, `regime_confidence`~~
  - ~~新增 `data.breadth{}` 子物件供 breadth.html 專用~~
- [x] ~~**[C-PAGE]** 建立 `breadth.html`（386 行）~~
  - ~~廣度綜合儀表（0–100 semicircle gauge）~~
  - ~~4 個分量 bar：`overall_breadth`, `sector_participation`, `momentum`, `mean_reversion_risk`~~
  - ~~Warning flags 視覺化（badge grid）~~
  - ~~`uptrend_ratio` per sector（來自 `data.sectors[]`，依比例排序）~~
  - ~~Regime confidence bar、Cycle phase、Exposure ceiling stat cards~~
  - ~~Analyst Notes 區塊（選填）~~
- [x] ~~**[C-FTD]** 整合 `ftd-detector` skill 產出，顯示 FTD 狀態 + Distribution Days~~
  - ~~FMP endpoint 已停用，改寫 `sector/ftd_yfinance.py` yfinance 轉接器，重用 skill 原有分析邏輯~~
  - ~~bridge.py 新增 `load_ftd_cache()` + `extract_ftd_data()`，輸出 `data.ftd{}`~~
  - ~~breadth.html 新增 FTD Detector 區塊：State/Quality/Exposure + FTD Event + Post-FTD Health 三欄~~
  - ~~cache 路徑：`sector/ftd_cache/ftd_detector_YYYY-MM-DD_*.json`~~
- [x] ~~**[C-TOP]** 整合 `market-top-detector` skill，顯示市場頂部概率~~
  - ~~`sector/market_top_yfinance.py` yfinance 轉接器，`YFinanceClient` drop-in 替代 FMPClient~~
  - ~~bridge.py 新增 `load_market_top_cache()` + `extract_market_top_data()`，輸出 `data.market_top{}`~~
  - ~~breadth.html 新增 Market Top Detector 區塊（Row 6）：Top Probability score + zone badge + 6 components bar + actions + FTD monitor~~
  - ~~cache 路徑：`sector/market_top_cache/market_top_YYYY-MM-DD_*.json`~~
- [x] ~~**[C-BREADTH]** 整合 `market-breadth-analyzer` skill（Monty's CSV），取代 phase0 的估算值~~
  - ~~sector_protocol_v1_1.md Phase 0 加入 script 執行 + cache 邏輯 + 欄位映射表~~
  - ~~bridge.py 新增 `load_breadth_cache()` + `extract_breadth_from_analyzer()`~~
  - ~~data.breadth 新增 `components_full`（6組件）、`zone`、`trend_direction`、`actions`、`key_levels`、`current_8ma/200ma`~~
  - ~~breadth.html 升級：6組件 bar（含 weight + signal）、zone badge、trend badge、actions、Key Levels 區塊~~
  - ~~cache 路徑：`sector/breadth_cache/market_breadth_YYYY-MM-DD_*.json`~~

---

## 🏗️ 架構債（待辦，優先度較低）

- [ ] **[BRIDGE-5]** 自動觸發機制：`run_bridge.sh` 或 `.claude` post-analysis hook
- [ ] **[JS-1]** 建立 `core.js`，統一 `initTheme` / `toggleTheme` / `logToUI`（目前三份重複）
- [ ] **[SIDEBAR-1]** Sidebar 組件化，消除四頁重複 HTML

---

## 🔁 Bridge 雙向架構（最終目標）

```
Dashboard [watchlist.html]
    輸入 Ticker → copy 指令 → Claude Code 終端機
                                    ↓
              investment_protocol_v4_5 執行
                                    ↓
                    invest_logs/history.json  +  reports/
                                    ↓  (bridge.py 自動觸發)
                              data.json 更新
                                    ↓  (60s polling)
        Dashboard 所有頁面自動刷新顯示最新結果
```

### Protocol → Log → Dashboard 對應表

| Protocol | 產出 Log | Bridge 讀取 | Dashboard 顯示 |
|----------|---------|------------|----------------|
| `investment_protocol_v4_5` | `invest_logs/history.json` | final_action, score, entry/tp/sl, **watch_conditions**, **key_risks** | history + **watchlist** |
| `sector_protocol_v1_1` | `sector_logs/*_sector_intel.json` | market_regime, sectors[], themes, fear_greed, **_phase0 breadth**, **_phase3 binary_risks** | sector + index + **breadth** + **calendar** |
| `news_protocol_v1` | `news_logs/*_digest.json` | verdicts[], **trump_signals**, **upcoming_events** | news + **calendar** |
| `theme-detector` skill | `skills/theme-detector/cache/*.json` | themes[], heat_scores, stocks | index themes（待加強） |

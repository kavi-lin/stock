# INTEL COMMAND — Todo List

> **Last Updated**: 2026-04-18
> **Last Session Note**: 持久化 Debug Log — `Dashboard/utils.js` 加 localStorage ring buffer（cap 300）取代純 DOM log；換頁 / 重載不再消失。DOMContentLoaded auto-replay。新增：(1) bridge.py handshake monitor（5s poll /api/refresh_status，last_ok/last_error 變化時入日誌）；(2) protocol handshake monitor（3s poll /api/run-protocol/status，running→done/error 轉變時入日誌，含 elapsed 時間）；(3) 動態注入 Clear 按鈕到 debug console header；(4) 每行 log 加 [page] 前綴。bump VERSION → 1.9.4。另修：awaitBridgeAndReload（平倉 / 加倉 / 刪倉改為 poll /api/refresh_status 等 bridge.py 完成才 reload，取代 1.5s 固定 race）；drill overlay card 加 2-layer shadow + 細邊框（scoped to #history-drill-rail，GPU 友善）。
> **Last Session Note (prev)**: market-sentiment-analyzer 加 file-based cache（TTL 15min），多 ticker 同 session 共用市場層，每 ticker 省 ~$0.1。bump VERSION → 1.9.3。
> **Last Session Note (prev)**: V4.8 TSLA 實測 11:23 / $4.00 / 31 turns。改動：PROTOCOL_TIMEOUT_SEC 600 → 1500；Dashboard confirm dialog 改 10-15min & ~$4；Phase 5 MD 報告委派 Sonnet 4.6 subagent（純排版、禁改決策數值）每次省 ~$0.5。bump VERSION → 1.9.2。
> **Last Session Note (prev)**: 決策中心 UX 升級：點卡片 → 橫向 scroll overlay 顯示該 ticker 所有歷次分析（buildCard 複用、日期近到遠、ESC/背景/✕ 關閉）；每張 card 右上 refresh icon + 計時；Global UI lock（server singleton → 所有 refresh/FLASH 按鈕同步鎖定）。bump VERSION → 1.9.1。
> **Last Session Note (prev)**: Investment Protocol V4.7 → V4.8 Parallel Blind Analyst Subagents（D）：Phase 2 四個 analyst 改 4 個 Agent subagent 平行；Burry 保留 inline；Isolation contract + subagent_isolated sentinel + PARTIAL/FULL_FALLBACK 階梯。bump VERSION → 1.9.0。
> **Last Session Note (prev)**: Investment Protocol V4.6 → V4.7 Anti-Self-Deception Patch（ABC）：Consensus Bonus 改 Red-Team-gated（NO_VIABLE_COUNTER 才 ×1.15、STRONG_COUNTER ×0.85）、新增 Phase 2.8 Red Team Adversary、Burry OVERRIDE_BURRY 強制成本化。另修 dashboard_server.py 漏 `import glob` 導致盤前檢查 500。bump VERSION → 1.8.0
> **Last Session Note (prev)**: 產業掃描 2026-04-18 → NEUTRAL 0.68；HOT=Industrials only (78)；Materials+Tech 雙雙 tail-risk 降級 HOT→WARM（consensus_warning + AI/Semis EXHAUSTING + SPY RSI 96.9 extreme）。Synthesized 60-75%（breadth 最保守）。bump VERSION → 1.7.2
> **Last Session Note (prev)**: 分析 BAC → STAGED_ENTRY 7%（雙軌 3.5/3.5）final_score +1.110；四 Agent 一致看多 + Burry WARNING 20.4 ×0.7；R/R 2.05。打破連續半導體集中。bump VERSION → 1.7.1
> **Last Session Note (prev)**: 啟動 News Protocol V2 重構（RSS 兩階段漏斗 + 4 agent 圓桌 + Dashboard 個股新聞按鈕）— 草擬中
> **Last Session Note (prev)**: 資料夾大整理 — archive/ 分類建立、過期 protocol/doc/log 歸檔、根目錄清潔；5 個 README + todolist 對齊 V4.6 現況；V4.6 session 前半段已完成雙軌 entry / STAGED_ENTRY / consensus bonus / directional macro / dashboard_server 定時刷新 / positions tracker / decisions.html 整合 / server-side mtime cache-busting

---

## Current State (2026-04-15)

- **Investment Protocol**: V4.8（V4.7 基礎 + Phase 2 四 analyst 平行 subagent 真獨立 + fallback 階梯 + degraded_mode 保護）
- **Sector Protocol**: V1.2（multi-file: main + phase_0/1-2-3/4-5/schema）
- **News Protocol**: V2（RSS 兩階段漏斗 + 5 agent 圓桌 + FLASH/DIGEST/REVIEW 三模式）
- **Dashboard**: index / decisions / sector / news 四頁（watchlist + history 已合併至 decisions；news 新增 reviewed/pending 切換 + 送審按鈕）
- **Positions Tracker**: `dashboard_server.py` + `/api/positions` + modal form + live_position overlay
- **Cache-Busting**: server-side mtime 自動注入（不再需要手動 bump `?v=`）
- **Auto Refresh**: `bridge.py` 每 5 分鐘背景刷新（可用 `DASH_REFRESH_SEC` 覆蓋）

---

## 🎯 活動 Backlog

### 路線 S — Skill 最小替代實作 + Review
**狀態**：4 個 missing skill 已建立最小可行實作並通過 smoke test，但需實戰驗證與閾值調整。
- [x] ~~**[S-BUILD-01]** `skills/market-sentiment-analyzer/` — yfinance VIX/SPY RSI + CNN F&G backend + PCR（~150 行）~~
- [x] ~~**[S-BUILD-02]** `skills/tail-risk-analyzer/` — 1y daily returns → kurt/skew/VaR/DD → fragility label（~120 行）~~
- [x] ~~**[S-BUILD-03]** `skills/portfolio-risk-manager/` — vol scaling + correlation + sector cap（~180 行）~~
- [x] ~~**[S-BUILD-04]** `skills/short-contrarian-analyst/` — Burry Score + T4 veto（~180 行）~~
- [x] ~~**[S-COPY]** 複製 9 個現有 skill 到 `skills/`~~
- [x] ~~**[S-REVIEW-01]** market-sentiment-analyzer 驗證：composite 63.9 (Greed)，VIX 18.2 NORMAL，CNN F&G backend 成功回傳 56.5；PCR endpoint 當前 null（CBOE JSON 不穩）— 可接受 fallback~~
- [x] ~~**[S-REVIEW-02]** tail-risk-analyzer 閾值校準完成：跑 7 檔 SPY/TLT/NVDA/TSLA/COIN/RIVN/BTC；重新加權 kurt 10% / skew 10% / var 15% / DD 30% / vol 35%（原本 kurt 30% 過高）；校準後 SPY/TLT=ROBUST, NVDA/TSLA=MODERATE, COIN/RIVN/BTC=FRAGILE ✓~~
- [x] ~~**[S-REVIEW-03]** portfolio-risk-manager 驗證：讀取 positions.json (3 筆) 成功，avg_corr=0.393 合理，Tech sector cap 正確觸發 → final cap 8.5%~~
- [x] ~~**[S-REVIEW-04]** short-contrarian-analyst 修正完成：~~
  - ~~D/E 單位：yf 一致返回 percentage（NVDA 7.26, KO 139.79, PG 68.72）→ 改為 always `/100`，NVDA 現在正確顯示 0.07~~
  - ~~FCF fallback：KO `freeCashflow` 回傳 -1.46B 錯誤，`operatingCashflow` 正確 7.4B → 加入 `if FCF<=0 and OpCF>0: FCF = OpCF * 0.85` fallback~~
  - ~~7 檔測試（NVDA/KO/PG/JNJ/TSLA/RIVN/COIN）Burry Score 分布 25-45 合理~~
- [x] ~~**[S-REVIEW-05]** 4 skill 整合測試完成：以 NVDA 為目標按 investment_protocol_v4_6 Phase 2/Phase 4 序列呼叫 4 skill，全部回傳合法 JSON，串接計算 final_position=4.46%（8.5% × 0.75 fragility × 0.7 Burry WARNING）。protocol 需手動指示 Claude 執行 `python3 skills/<name>/scripts/...` 而非自行模擬~~

### 路線 N — News Protocol V2（RSS 兩階段 + 4 Agent 圓桌 + Dashboard 整合）
- [x] ~~**[N-PROTO]** 草擬 `news/news_protocol_v2.md`~~
  - 兩階段漏斗：Stage 1 RSS shallow triage → Stage 2 WebFetch deep debate
  - Team 從 3 人擴至 5 人：News Collector + Bull + Bear + **Sector Analyst** + **Macro/Policy Expert** + Arbiter
  - Arbiter 加權：平權 25/25/25/25，或依新聞類型動態（FOMC→Macro 40%, Earnings→Sector 40%）
  - Stage 1 晉級門檻：`|score|≥3` OR `binary+within_48h` OR `HIGH credibility + |score|≥2`；硬上限 5 則
  - Stage 1 輸出「Triage 篩選表」給人類審核（可手動加選）
  - 只有 Stage 2 才能 patch `sector_intel.json` / `phase0.json`
  - `news_logs` verdict 新增欄位：`depth: shallow|deep`、`tickers_mentioned[]`、`sector_view`、`macro_view`
  - FLASH mode 保持單階段 deep
- [x] ~~**[N-RSS]** 撰寫 `news/fetch_news_rss.py`~~
  - 來源：Reuters / Bloomberg / Yahoo Finance / MarketWatch / CNBC RSS
  - 輸出：`news/news_logs/YYYY-MM-DD_raw.json`（標題 + 摘要 + source + timestamp + url）
  - 去重（headline 相似度）、時間視窗參數（default 24h）
- [x] ~~**[N-ARCHIVE]** `news_protocol_v1.md` 移至 `archive/old_protocols/news/`~~
- [x] ~~**[N-CLAUDEMD]** `CLAUDE.md` 更新 news protocol 路徑 → v2 + VERSION bump 1.7.0~~
- [x] ~~**[N-DASH-BTN]** `page-decisions.js` 每張卡 footer 新增 📰 FLASH 按鈕 → 複製單股 prompt 到剪貼簿 + toast~~
- [x] ~~**[N-DASH-NEWS]** `page-news.js` 更新按鈕合併 reload + 複製「新聞分析 DIGEST」prompt + toast~~
- [x] ~~**[N-TOAST]** `utils.js` 新增 `UI.showToast()` + `UI.copyToClipboard()` 共用元件~~
- [x] ~~**[N-I18N]** `i18n.js` 新增 `flash_btn` / `flash_toast` / `digest_toast` 鍵值（中英雙語）~~
- [x] ~~**[N-BRIDGE]** `bridge.py` 過濾 v2 `depth=shallow`；支援 `tickers_mentioned` / `sector_view` / `macro_view` / `news_type` 新欄位~~

### 路線 B — Calendar 頁面（財報 & 事件日曆）
- [ ] **[B-BRIDGE]** `bridge.py` 導出 `upcoming_binary_risks[]` + `sector_news_sentiment{}` 至 data.json 頂層
- [ ] **[B-PAGE]** 建立 `calendar.html`
  - 週曆視圖，顯示財報日期、FOMC、地緣政治 binary events
  - 每個事件顯示受影響產業 + direction（bullish/bearish/binary）
  - 資料來源：`_phase3.upcoming_binary_risks` + `earnings-calendar` skill
- [ ] **[B-SKILL]** 整合 `earnings-calendar` skill（FMP API），產出 JSON cache 讓 bridge 讀取

### 路線 C — Positions Tracker 強化
- [ ] **[C-IMPORT]** `import_firstrade_csv.py` — 解析 Firstrade 月結單 CSV → `positions.json`（避免手動輸入，安全方式取代非官方 API）
- [ ] **[C-CLOSE]** Dashboard 新增「平倉」動作：將 position status 改 closed，自動記錄 exit_price + realized_pl
- [ ] **[C-ADD]** 同一 ticker 加碼時提示「併入現有 avg cost」vs「另開 lot」兩個選項

### 路線 D — 效能優化（低優先）
- [ ] **[ARCH-11]** `lucide.createIcons()` debounce（`requestAnimationFrame` 批次）
- [ ] **[ARCH-12]** Chart.js 惰性載入（只在 sector.html 載入）
- [ ] **[ARCH-13]** marked.js 惰性載入（viewReport 觸發時才載）
- [ ] **[ARCH-14]** `innerHTML` XSS 防護（`escapeHTML()` helper，已有 `UI.escapeHTML`，套用到剩餘欄位）

---

## ✅ 已完成（session 2026-04-12 to 2026-04-15）

### V4.6 投資協議
- [x] 雙軌 entry（aggressive + conservative ranges）
- [x] STAGED_ENTRY / STAGED_EXIT 決策狀態
- [x] Consensus bonus ×1.15（4 agent 同向 + Burry 不 veto）
- [x] Directional macro multiplier（只作用於同向訊號）
- [x] 移除 Phase 3 VOLATILE × 0.85 雙重懲罰
- [x] HOLD 不再強制 Auto-REJECT，改交由 Phase 4 dual-track 彈性處理
- [x] Binary risk 三分類（positive / unknown / negative）
- [x] README + todolist 對齊 V4.6
- [x] `CLAUDE.md` protocol 路徑更新

### Sector Protocol V1.2
- [x] 主檔案 + 4 子檔拆分（main / phase_0 / phase_1-2-3 / phase_4-5 / schema）
- [x] 三層訊號合成（breadth + FTD + market_top → synthesized_exposure）
- [x] Phase 4c 決策樹 STEP A-G
- [x] Extreme Sentiment Playbook（Greed 防守 / Fear 逆向）
- [x] consensus_warning 三條件精確定義

### Dashboard 整合
- [x] 合併 watchlist.html + history.html → `decisions.html`（5 filter tabs: all/active/waiting/historical/positions）
- [x] Sidebar 更新（watch_radar + audit_history → decisions）
- [x] `decisions.html?view=...` URL 深連結支援
- [x] ARCH-4/5 DataStore singleton + 各頁改用 DataStore.get()
- [x] ARCH-7/8/9/10 各頁 inline script 抽出為 `page-*.js`（presenter 層）

### Server 與 Infrastructure
- [x] `dashboard_server.py` — static file server + `/api/positions` GET/POST/DELETE
- [x] Position modal form（ticker/date/price/shares/track/status/notes + delete per lot）
- [x] `bridge.py` 整合 positions.json：`live_position` overlay + yfinance 即時報價
- [x] Server-side mtime cache-busting（移除所有 HTML 的 `?v=` 硬編碼）
- [x] `bridge.py` 每 5 分鐘定時刷新（背景 daemon thread）
- [x] `open_dashboard.sh` 整合跑 `dashboard_server.py`

### 文件整理（2026-04-15）
- [x] 根目錄 stray 檔歸檔 → `archive/root_stray/`
- [x] 舊 investment protocols (v4_3/v4_4/v4_5) → `archive/old_protocols/investment/`
- [x] 舊 sector protocols (v1/v1_1/v1_2/v1_2_optimized) → `archive/old_protocols/sector/`
- [x] `reports/optimized/` → `archive/old_reports/`
- [x] `Dashboard/ARCHITECTURE_REVIEW.md` + `CHANGELOG.md` → `archive/old_docs/`
- [x] 舊 `session_export_*` + phase0 cache → `archive/old_invest_logs/`
- [x] 5 個 README 改寫對齊（root + investment + sector + news 已更新；CLAUDE.md 已對齊）

---

## 📋 Bridge 資料流對照（current）

| Protocol | 輸出 Log | Bridge 讀取欄位 | Dashboard 顯示 |
|---|---|---|---|
| `investment_protocol_v4_8` | `invest_logs/history.json` | `final_action`, `final_decision`, `final_score`, `entry_aggressive/conservative`, `consensus_bonus_applied`, `red_team_verdict`, `burry_override_active`, `phase2_fanout_mode`, `degraded_analysts`, `macro_alignment`, `staged_split`, `binary_classification`, `key_risks` | decisions 頁全部 tabs |
| `sector_protocol_main` (V1.2) | `sector_logs/*_sector_intel.json` | `market_regime`, `_phase0` (breadth/FTD/MT synth), `_phase1` (sectors[]), `_phase3` (binary_risks/trump_signals), `hot_sectors/cold_sectors` | index + sector + news binary sidebar |
| `news_protocol_v1` | `news_logs/*_digest.json` | `verdicts[]`, `trump_signals`, `upcoming_events` | news 頁 |
| `market-breadth-analyzer` | `breadth_cache/*.json` | 6 組件 breadth + trend | index 廣度 gauge |
| `ftd_yfinance.py` | `ftd_cache/*.json` | FTD state + quality score | index FTD card |
| `market_top_yfinance.py` | `market_top_cache/*.json` | top_score + zone + budget | index 頂部風險 card |
| `positions.json` | — | lots → avg_cost / unrealized_pct / live_position | decisions 持倉頁 + watchlist overlay |

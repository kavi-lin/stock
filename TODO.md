# INTEL COMMAND — Backlog & Tasks

> **Last Updated**: 2026-04-23

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

## ✅ 已完成歷史紀錄

- **V4.6 投資協議**：雙軌 entry、STAGED 狀態、Consensus bonus、移除 VOLATILE 雙重懲罰。
- **Sector Protocol V1.2**：主子檔拆分、三層訊號合成、決策樹 STEP A-G。
- **Dashboard 整合**：合併 decisions.html、ARCH-4/5 DataStore、ARCH-7/8/9/10Presenter 抽出。
- **Server 與 Infrastructure**：dashboard_server.py、Position modal、bridge.py 整合 positions.json、自動 mtime cache-busting。
- **文件整理**：歸檔至 `archive/`、README 對齊、CLAUDE.md 更新。

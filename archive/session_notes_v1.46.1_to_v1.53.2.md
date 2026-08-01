# Session Notes 歸檔 v1.46.1 → v1.53.2（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v1.53.2) — BUG-006 修補 + FRED fetch.py None 比較 fix

**兩個 bug，當天解：**

### 1. `skills/fred-macro/scripts/fetch.py:1054` TypeError
`hy_pct = rs.get("credit_spread_pctile_1y", 50)` 在 key 存在但值為 `None` 時 `dict.get` 不會回 default，導致 `hy_pct > 45` 比較炸掉。改成 `rs.get(...) or 50`。`daily_update.sh` Step 4 解鎖。

### 2. BUG-006 — sector_protocol FTD day-counter 幻覺
Gemini 報「4/22 報告抄 4/21 範本，忽略 breadth 36.8 → 42.4」。實際根因不一樣：
- Breadth 4/21=42.4 / 4/22=42.4 是因 TraderMonty CSV 上游早上沒更新（晚上才有 4/21 收盤），不是 AI 抄。
- 真正幻覺：4/21 報告寫 "FTD Day 14"，4/22 寫 "FTD day 6" — 兩天 AI 抓 ftd_cache 不同欄位（`current_day_count` vs `quality_score.breakdown.base "Day 6 FTD"`）。

**修法 V1.5 schema bump**：
- `sector/ftd_yfinance.py` 加 `ftd_timeline` block（含 `ftd_status_text` canonical 字串 + `days_since_ftd` / `rally_day_count` / `ftd_day_number` 三個明確 day-counter + `_help` 註解）
- `sector/phase_0.md` 層 C 加反幻覺規則（必引用 `ftd_status_text` 原文）
- `sector/schema.md` Phase 0 / Phase 5 ftd block 補新欄位

**驗證輸出（4/26 跑）**：
```
FTD Timeline: FTD CONFIRMED, day 12 post-confirmation (rally-day 18; FTD originally confirmed on rally-day 6)
```
ftd_date 4/8 + 12 trading days = 4/24 ✓；rally_low 3/31 + 18 trading days = 4/24 ✓

**後續觀察**：4/27 跑 sector_protocol 時看 AI 是否引用新 `ftd_status_text` 原文；如果還寫成「FTD Day N」要再強化 phase_4-5.md 內的 prompt 引用語法。

## 🟢 Session Note (v1.53.0) — News Driver v0.2.1（兌現 Finnhub /company-news + sentiment）

從 v1.46-v1.52 的 News driver 一直是 v0.1 volume/gap proxy（雖然 SKILL.md / global_warnings 一直寫「v0.2 will integrate Finnhub」）。User 提醒後實作。

**Method 4 個方案評估**：
1. Pure keyword（粗糙）
2. Keyword + magnitude + negation（finance-tuned，0 cost）— 採用
3. Finnhub `/news-sentiment` endpoint — 測試 **403 premium-only 不能用**
4. LLM scoring — $1-2/day cost，先不上

**v0.2 第一版實作後 5-ticker test 找到 5 critical bug**：
- NVDA 248 articles 多數 tangentially-related 噪音（"Walmart's investment in Mexico" 被當 NVDA news）
- 問句被當 sentiment claim（"Is X a Buy?" → +0.5）
- "Lockheed Martin Shares Are Falling" 沒抓到（"falling" 不在詞庫）
- "Insiders Sold Suggesting Hesitancy" 沒抓到
- 248 articles 全平均 → 訊號被噪音稀釋

**v0.2.1 修正**：
1. **Headline relevance filter**：Finnhub profile 抓 company short name → 標題沒有 ticker 也沒 short name → 過濾
2. **問句 ×0.5**：標題含 `?` 或 `Is/Why/Should/Will/Can` 開頭 → score halved
3. **Cap top 20 by recency**
4. **+25 個新詞彙**：falling/hesitancy/flopped/buyback/dividend cut/sluggish 等
5. **Source blacklist**：simplywall.st / fool.com / zacks.com

**測試結果（v0.2 → v0.2.1）**：
| Ticker | v0.2 | v0.2.1 | 變化 |
|---|---|---|---|
| NVDA | 248→+0.152 | 20 of 249→+0.250 | 噪音砍 92% |
| LMT | 47→-0.011 | 20 of 92→-0.045 | 抓到 Q1 miss |
| LLY | 36→+0.033 | 10 of 49→**-0.055** | **翻轉成負**（GLP-1 壓力） |
| JPM | 42→+0.031 | 1 of 52→-0.040 | 41 篇 commentary noise 砍 |

**Fallback 設計**：Finnhub 失敗或無相關文章 → 降回 v0.1 proxy + warning 標明

**整合**：predict.py 主流程自動用 v0.2.1（清 cache 後第一輪 fresh prediction 都用新算法）。daily_update.sh thematic-screener 跑時自動生效。

**已知殘留小 bug**（v0.2.2 修）：
- "Why X Flopped" 顯示 +0.25 應 -0.25（summary 某詞蓋過 — 待 trace）
- 動詞變化漏：slips / lag / lags 詞庫沒有

## 🟢 Session Note (v1.52.0) — Radar v0.4: ETF holdings universe + auto-refresh

修正 user 點出來的兩個 fundamental issue：(1) static_stocks 只有手選 10 個 → universe 太窄、(2) 「top 5」semantic 錯（top 5 of 10 不是 top 5 of universe）。

### 核心改動：ETF holdings 取代手選 universe

**之前**：每主題 themes.yaml 寫死 10 個我手挑的 static_stocks
**現在**：每主題的 proxy_etfs (e.g. SOXX/QTUM/BOTZ) 抓 yfinance top 10 holdings → 跨 ETF dedup → 過濾非美股 → cap 25 → 寫進 themes.yaml

結果：
- 270+ 個 unique US-tradeable tickers（vs 之前 171）
- 17 主題從 10 → 16-25 stocks
- 4 主題真實 universe 小（保留 5-12）：Gold, Uranium, Real Estate, Utilities Defensive
- Quantum 17 stocks，**重疊 0** vs 我手選名單 → 證明 ETF 比手選代表性高

### 新增基礎設施

- **`skills/thematic-screener/scripts/refresh_etf_holdings.py`**（150 行）：完全自動化 — 用 yfinance 抓 ETF top holdings、dedup、過濾非美股、寫回 themes.yaml + bump etf_meta.yaml `last_refreshed` timestamp
- **`skills/thematic-screener/etf_meta.yaml`**：紀錄 last_refreshed + summary stats
- **`daily_update.sh` Step 5.5**：每天檢查 etf_meta，60 天內 fresh 顯示 ✅，60-90 天黃色提示，**90 天自動觸發 refresh + 同步重跑 theme-detector**

### Refresh 自動化頻率（per user 確認）

90 天自動 refresh 對應 ETF rebalance 季度週期。ARK 系列雖可日動但 top 25 一季內幅度<5 個是常態 → 90d 是合理 cadence。
**完全本地、0 token 成本**（yfinance 免費 + Python 腳本，不調 LLM）。

### 真實 breadth 結果驗證

```
AI & Semiconductors             N=22  95% bullish (21/22) — 真強勢
Financial Services & Banks      N=25  80→84→88% — 漸強
Defense & Aerospace             N=18  33→38→44% — 短空長中性
Oil & Gas (Energy)              N=25  32→36→36% — 失寵
Utilities Defensive             N=12  41→50→50% — 中性偏空
```

對比 v0.3：之前 top-5 預先 selection → 多數主題假性 100% bullish。現在跨 universe 平均，breadth 真實反映「主題內多少股看多」。

### 工作流程
- **每天**：daily_update.sh 自動跑 → etf_meta < 60d 顯示綠燈、< 90d 黃燈、≥ 90d 自動 refresh
- **使用者 0 維護**：完全 set-and-forget；季度自動 refresh
- **Manual override**：`python3 skills/thematic-screener/scripts/refresh_etf_holdings.py --top-n 25` 隨時可跑

### 延後的事
- **primary_theme tagging（解重複）**：原 plan 的 step 5 還沒做。NVDA 仍同時在 AI/Quantum/Robotics 都算。等使用 1-2 週看是否 visually 困擾再決定要不要做
- **動態 ETF API**：v0.5 才考慮（手動 quarterly refresh 已夠用）

## 🟢 Session Note (v1.51.0) — Radar v0.3 horizon switcher + breadth 算法修正

兩個 user feedback 觸發的 critical 修正：

### 1. Breadth 算法 bug 修正（嚴重）
**之前**：bullish_breadth_pct 是基於「top 5 movers」算的 → 都被 ranked by score×conv 預先 selected → 必然 100% bullish 大概率 → metric 失去意義
**修正**：改成對主題的**全部 representative_stocks (10 名)** 算 breadth → 得到真實「主題內多少股看多」

修正後例：
- Defense & Aerospace: 1d 10% (1/10) → 5d 20% (2/10) → 15d 30% (3/10) — **真實短空長多 pattern**
- Robotics: 100% (9/9) all horizons — 真強勢
- Cybersecurity: 66% → 77% → 88% — 漸強
- Cloud: 40% → 50% → 50% — 混雜
- Obesity & GLP-1: 22% → 33% → 44% — 短期偏空

### 2. 1d/5d/15d Horizon Switcher
- screen.py `compute_theme_short_term` 重寫：回傳 `{n_total_constituents, primary_horizon, by_horizon: {1d/5d/15d: {bullish_breadth_pct, avg_conviction, n_valid_predictions, n_bullish, mean_target_pct}}, components}`
- page-radar.js 加 `_currentHorizon` state + 3 個 button (1d / 5d ★ / 15d)
- Theme card 顯示「SHORT bull [5d] 80% (8/10)」格式 — 含當前 horizon 標示 + bullish/valid 計數
- 切換 horizon 自動重排 + 重 render

### 3. 額外 polish（同輪）
- Tooltip CSS 改用 theme variables (`var(--bg-card)`、`var(--text-main)`、`var(--secondary)` 等) → light/dark 自適應
- Cursor 從 `cursor: help` 改 `inherit`（不再變問號游標）
- Theme card 多顯示「constituents: N」讓 user 知道分母是多少

**Output schema 變化**（v0.3 vs v0.2）：
- `short_term.bullish_breadth_pct` → `short_term.by_horizon.<h>.bullish_breadth_pct`
- 加入 `n_total_constituents`、`n_valid_predictions`、`n_bullish` 透明化分母

**plan_short.md 全進度**（**整套 v0.3 production**）：
- Step 1-7 ✅ + 文件 ✅ + Step 4 v0.1 dual-section ✅ + v0.2 all-themes-grid ✅ + **v0.3 horizon switcher + breadth 修正 ✅ v1.51.0**

## 🟢 Session Note (v1.50.0) — Tactical Radar v0.2 重設計（all themes grid + regime layer + predict cache）

User feedback「不直覺」+「想看全部主題 + 點開 movers」+「regime 是市場主導力」的 3 個訴求一次落地。

**結構性重設計**：
1. **Theme runtime sync**（修我之前 Step 2 的 bug）：themes.yaml + default_theme_config.py 同步加 5 個新主題（Nuclear Energy / Uranium / Space Economy / Quantum Computing / Robotics & Automation / Utilities Defensive / Obesity & GLP-1），15 → 21 themes
2. **Theme-detector 重跑**：max-themes 25 → 偵測到 20 主題（含 5 個新加 + 4 auto-discovered sector concentration）
3. **predict.py 加 4h cache**：cache hit 1.7s → 0.4s。171 unique tickers 全跑也只需單次（之後 4h 內全 hit）
4. **screen.py v0.2 重寫**：
   - 移除 top_themes 限制 → **顯示全部 20 主題**
   - 每主題加 short_term { bullish_breadth_pct, avg_conviction, components }
   - 加 regime layer：2 獨立 badges (RSI + VIX) + factor (取 max 偏離度)
   - regime factor 自動 dampen bullish_breadth (今天 0.9× 因為 SPY RSI 87)
   - 排序預設 by short bullish_breadth_pct desc
   - 同時收集 components 欄位給 v0.2 後續用
5. **radar.html v0.2**：grid 6 cols + sort toggle (Short/Mid) + regime badges 區 + expanded movers panel
6. **page-radar.js v0.2**：~360 行重寫，theme grid 點擊展開單一主題 movers，sort 即時切換，badges 中英雙語

**Regime layer 設計**（per user 確認 2 badges + 1 factor）：
- RSI > 85 → 「極端超買 — mean reversion 風險」(factor 0.90)
- RSI < 25 → 「極端超賣 — 反彈燃料」(factor 1.10)
- VIX > 25 → 「緊張 — caution」(factor 0.92)
- VIX > 35 → 「恐慌 — 防禦」(factor 0.85)
- VIX > 40 → 「投降底 — contrarian buy」(factor 1.15)
- 取「max 偏離度」當 factor，不 double-count

**今天實際狀態**（驗證 4 象限）：SPY RSI 87.4 + VIX 18.7 → 「**複雜頂**」象限
- ✅ RSI badge fired: "SPY RSI 87.4 極端超買"
- 🟢 VIX badge silent (VIX 18.7 沒進極端區)
- 數字 factor: 0.90 (rsi_87_overbought)

**Bridge 注入結構**：data.tactical.{themes[20], regime_snapshot, regime_badges, regime_factor, screener_params}

**設計分區決定的修正**：
- 之前 Step 4 的「2 分區強迫看」改成「1 grid + click 展開」(per user 不直覺反饋)
- Movers 不再預設展開，使用者主動點才看詳細
- Cool 主題 (mid_heat < 30) 透明度 0.7 區分但不隱藏（per user「全部顯示」訴求）

**plan_short.md 全進度**：
- Step 1-7 ✅ + 文件刷新 ✅ + Step 4 v1（雙分區）✅ → **v0.2 全 grid 重設計 ✅ v1.50.0**

整套 Tactical Opportunity Radar v0.2 production-ready。

## 🟢 Session Note (v1.49.0) — plan_short Step 4 完成（Dashboard「短期雷達」頁）

落地 Tactical Opportunity Radar 的視覺化層。**plan_short.md 全部 7 個 Step 完成**。

**架構決策**：
- 走方案 B：**新頁面 `radar.html`**（不擴充 momentum）— sidebar 加「短期雷達」icon=radar
- 走方案 A 資料流：**`bridge.py` 注入 `data.tactical` sub-key**（單一 fetch，不破壞既有 data.json 模型）
- 桌面 only，預設展開第 1 個主題卡

**完成檔案**：
- `bridge.py` +35 行：`load_tactical_recommendations()` + 注入 `data["tactical"]` + import time
- `Dashboard/utils.js`：NAV_ITEMS 加 radar entry
- `Dashboard/i18n.js`：zh/en nav.radar + 完整 radar 頁面字串（~40 entries × 2 langs）
- `Dashboard/style.css` +120 行：experimental-badge / regime-banner / heat-bar / horizon-bar / driver-row / invalidation-box / concentration-warning / confidence-breakdown 等 radar 專屬類別
- `Dashboard/radar.html`（85 行 NEW）：頁面骨架 — header + EXPERIMENTAL badge + regime banner + section A (主題卡) + section B (movers)
- `Dashboard/page-radar.js`（260 行 NEW）：render 邏輯 — 嚴格遵守 plan_short §11.D 顯示規則（range / confidence / drivers / invalidation / concentration / trading_meta 全顯示）

**§11.D 顯示規則檢核**（強制）：
- ✅ EXPERIMENTAL badge（橘色，header 內）
- ✅ Range（每個 horizon 都顯示 $low – $high，不只 mid 點）
- ✅ Confidence + breakdown（collapsible，7 contributors 展開）
- ✅ Drivers（4 sources：news / sector / momentum / atr）
- ✅ Invalidation box（紅色左 border）
- ✅ Concentration warning（橘色左 border，列出 co-recs）
- ✅ Trading meta（stop / pos% / tx / exit trigger）
- ✅ FRED regime banner（頂部，含 SPY/RSI/VIX/yield curve/credit spread）
- ✅ 累積天數提示（header）+ KPI gate hint

**Smoke test**：
- node syntax 通過
- HTML id 全 18 個 ✓ 對應 JS reference
- bridge.py 注入成功：`tactical.status: success / 3 themes / 9 movers`
- Dashboard server 已在跑（pgrep 確認）

**plan_short.md 全進度**：
- Step 1 short-term-target ✅ v1.46.0
- Step 2 4 themes ✅ v1.46.1
- Step 3 thematic-screener ✅ v1.47.0
- Step 5 outcome log（Step 3 內含）✅ v1.47.0
- Step 6 daily_update.sh 整合 ✅ v1.48.0
- Step 7 weekly_review.py ✅ v1.48.0
- 文件刷新 ✅ v1.48.1
- **Step 4 Dashboard「短期雷達」 ✅ v1.49.0 ← 全 plan 收尾**

整個 Tactical Opportunity Radar v0.1 系統 production-ready。

## 🟢 Session Note (v1.48.1) — 文件刷新（README.md + CLAUDE.md）

把短期戰術層的整套變更**反映到使用者日常文件**。

### README.md 改動
- **頂部**：新增「三層時間維度設計」說明（長期/中期/短期）
- **常用指令表**：加 description 欄位、補 `動能 [TICKER]`
- **每日工作流程**：從原本 4 step 重寫成 **Tier 1/2/3/4 結構**：
  - Tier 1 自動：daily_update.sh 6 step（含新 Step 6 thematic-screener）
  - Tier 2 每日手動：開 Dashboard / 看 recommendations / 視需求做深度分析
  - Tier 3 每週末手動：weekly_review.py
  - Tier 4 不定期：分析、產業掃描、dual_fetch、postmortem 等
- **腳本用途速查（新增）**：4 個分類 × 共 ~20 個 .py 一覽，每個含「用途」「觸發」
- **Tactical Opportunity Radar 章節（新增）**：架構圖 + 與既有系統關係表 + KPI gate

### CLAUDE.md 改動
- **Protocol Triggers 表**：標註 V4.8.1 dual_fetch + 各 protocol 內容
- **新增「Tactical Opportunity Radar」section**：說明戰術層自動產出位置 + 紀律「不影響 protocol 決策、永不自動覆寫 config」
- **Ops Shortcuts**：從單行擴成 4 個常用指令（含 weekly_review、predict、dual_fetch、audit_drift_check、backtest_postmortem）

### 今日完整 plan_short 進度
- Step 1 short-term-target ✅ v1.46.0
- Step 2 4 themes ✅ v1.46.1
- Step 3 thematic-screener ✅ v1.47.0
- Step 5 outcome log（Step 3 內含）✅ v1.47.0
- Step 6 daily_update 整合 ✅ v1.48.0
- Step 7 weekly_review.py ✅ v1.48.0
- **文件刷新 ✅ v1.48.1**
- Step 4 Dashboard ⏳ 唯一剩下

## 🟢 Session Note (v1.48.0) — plan_short Step 6 + Step 7（自動化 + 週末校準工具）

把每日推薦生成自動化 (Step 6) 並建立每週手動校準工具 (Step 7)。**day-1 logging 機制現在每天會自動運轉**。

### Step 6 — `daily_update.sh` 加入 thematic-screener
新增第 6 步驟：
- 檢查 `theme-detector` cache 存在性 + 新鮮度（> 7 天 → 跳過警示，不報錯）
- 用 `set +e` 包覆 thematic-screener 執行，**失敗不中止整體 daily flow**
- 顯示輸出檔大小確認成功
- 加提示「每週末跑 weekly_review.py」

### Step 7 — `skills/short-term-target/scripts/weekly_review.py`（330 行）

每週末手動跑，**不自動覆寫任何 config**。輸出 `reports/SHORT_TERM_WEEKLY_<DATE>.md` 含：
1. **Per-horizon 統計**：1d / 5d / 15d 各別 hit rate / in-range / mean error / directional bias
2. **Per-theme 5d alpha 分解**：哪個主題的推薦最準 / 最不準
3. **Worst 5 cases**：最大絕對誤差案例 + driver 細節
4. **Suggested adjustments**：基於 hit rate 與 bias 的具體建議（reduce α/γ 等）
5. **KPI gate**：對照 plan_short §6 + §12.H 的失敗判定（hit rate < 50% AND mean alpha < 0% on N≥30 → 整套退役）

**重要紀律**：Tool 只給建議，**完全由使用者決定**要不要 edit `config/weights.yaml`。每次調整需手動 bump `weights_version`，未來預測自動 tag 版本，可做 before/after 比較。

### Smoke test
- `daily_update.sh` syntax check 通過
- `weekly_review.py` 跑通：找到 1 個 recommendations file（今天的），0 預測達到 evaluation window（horizons 都還沒到期）→ 正確顯示 "No outcomes available" graceful message

### plan_short.md 進度
- Step 1（short-term-target）✅ v1.46.0
- Step 2（4 themes）✅ v1.46.1
- Step 3（thematic-screener）✅ v1.47.0
- Step 5（outcome log）✅ v1.47.0（內含於 Step 3）
- **Step 6（daily_update 整合）✅ v1.48.0**
- **Step 7（weekly_review tool）✅ v1.48.0**
- Step 4（Dashboard）⏳ 唯一剩下

### 系統現狀（每天運轉中）

```
每天 daily_update.sh:
  Step 1-5 (廣度/FTD/Top/FRED/bridge) — 既有
  Step 6 thematic-screener → data/recommendations/<DATE>.json — 新增

每週末手動:
  python3 skills/short-term-target/scripts/weekly_review.py
  → reports/SHORT_TERM_WEEKLY_<DATE>.md
  → user 決定是否 edit weights.yaml + bump weights_version
```

從今天起，每跑一次 daily_update.sh 就累積一筆推薦樣本。**約 7-10 天後 1d/5d 就有可評估資料；3-4 週後達到 N≥30 KPI gate 門檻**。

## 🟢 Session Note (v1.47.0) — thematic-screener skill v0.1（plan_short Step 3 + Step 5 內含）

新增 `skills/thematic-screener/` — Tactical Opportunity Radar 的聚合層，把 theme-detector（中期主題熱度）與 short-term-target（1d/5d/15d 個股預測）串成每日推薦輸出。

**架構決策**：
- **Subprocess 呼叫 short-term-target**（不 import） — 保持 skill 獨立性。N×M tickers × ~5-15s/call 是可接受的日 cadence
- **Theme-detector 已提供 `representative_stocks` per theme** — 不需 parse cross_sector_themes.md
- **Concentration 是 WARNING 不是 REMOVE**（per §11.B 修正）— 同主題 ≥2 picks → 加 flag 但都保留，使用者決定
- **無 FRED → theme scoring**（per §12.E 硬版拒絕）— 只記錄 FRED 狀態到 regime_snapshot
- **Day-1 outcome log 寫入機制**（per Step 5）— 每次 run 寫 `data/recommendations/<DATE>.json`，含完整 regime context (SPY/RSI/MA50/VIX/FRED)，未來 Step 7 weekly_review 可直接 cross-tab

**完成檔案**：
- `scripts/screen.py`（230 行）— 主聚合腳本
- `SKILL.md` / `README.md` / `CHANGELOG.md`
- `data/recommendations/.gitignore` + `cache/.gitignore`

**Smoke test**（2x2 = 4 calls，~30s）：
- ✅ theme-detector cache 載入正確
- ✅ Top 5 themes 排序正確（Clean Energy 67.4 / Defense 66.0 / Materials 64.3）
- ✅ short-term-target subprocess 對每個 ticker 回傳完整 JSON
- ✅ concentration_flag 觸發正確（同主題 2 picks → 都標警示）
- ✅ regime_snapshot 完整（SPY=713.94 RSI=87.4 VIX=18.71 FRED=expansion）

**真實 run**（3x3 = 9 calls，~90s）：成功寫入 60KB recommendations log

**plan_short.md 進度**：
- Step 1（short-term-target）✅ v1.46.0
- Step 2（4 themes）✅ v1.46.1
- **Step 3（thematic-screener，含 Step 5 log writer）✅ v1.47.0**
- Step 4（Dashboard 兩分區）⏳
- Step 6（daily_update.sh 整合）⏳
- Step 7（weekly_review.py）⏳

**值得注意**：今天 SPY RSI 87.4 是極端區。所有今日推薦的 regime context 都記錄了這個事實，未來 backtest 可以分析「在 SPY RSI > 80 時，模型表現如何」這類問題。

**設計亮點 — Day-1 logging 已運轉**：
從這一刻起，每次 thematic-screener 執行（手動或未來 daily_update.sh 自動）都會留下完整的「當下推薦 + 當下市場狀態」紀錄。3-4 週後就有 N≥30 樣本可供 Step 7 weekly_review 評估。**這比「先做 7 個 step 再驗證」省 3-4 週**。

## 🟢 Session Note (v1.46.1) — plan_short Step 2 完成（4 個新主題）

`cross_sector_themes.md` 17 → **21 主題**。實作前盤點發現原計畫的 6 個新主題實際只該加 4 個：
- **Nuclear Energy 已存在**（既有第 15 主題，含 CCJ/CEG/VST/OKLO 等）→ skip
- **Healthcare Defensive 與既有 Healthcare & Pharma 重複**（UNH/JNJ/LLY/PFE 已涵蓋）→ skip

**新增主題**：
- **Space Economy**（從 Defense 拆 RKLB；ROKT/ARKX/UFO ETFs；14 名）
- **Quantum Computing**（IONQ/RGTI/QBTS/QUBT pure-plays + IBM/GOOGL/MSFT/NVDA mega-cap dilution；11 名；標明 pure-plays ATR ~8%）
- **Robotics & Automation**（ISRG/TER/ONTO/ABBN/FANUY/ROK；BOTZ/ROBO/IRBO/ARKQ ETFs；15 名）
- **Utilities Defensive**（NEE/DUK/SO/AEP/XEL；XLU/IDU/VPU/FUTY；15 名；明示與 Nuclear Energy 區別 — Nuclear 是 offense，這個是 defense）

**附帶調整**：
- Defense & Aerospace 移除 RKLB（補 TXT），ETFs 從 4 → 2（ROKT/ARKX 移到 Space）
- Overlap Matrix 加 8 行（含 BWXT 三重歸屬：Defense + Nuclear + Space 都正確）
- Summary Table N=21

**plan_short.md 進度**：
- Step 1（short-term-target）✅ v1.46.0
- Step 2（4 themes）✅ v1.46.1
- Step 3-7 ⏳

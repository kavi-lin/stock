# CHANGELOG — fred-macro

## v1.13.0 — 2026-04-24

### Added
- **`RSXFS` series** — Retail Sales Excluding Food Services（月頻消費需求指標）
  - `regime_signals` 新增 `retail_contracting`（MoM < 0 **且** trend_30d == "falling"，雙條件避免單月雜訊）+ `retail_sales_mom_pct`
  - `_macro_scores` employment 分支：`retail_contracting` 觸發 **-10** penalty
  - `_top_risks`：零售收縮時插入消費需求風險條目
  - **設計選擇**：只用 MoM 方向，不用絕對值（名目數字含通膨，直接比較無意義）；雙條件觸發防止單月噪音



## v1.12.0 — 2026-04-24

### Added
- **`T10Y3M` series** — 10Y-3M Treasury spread，Fed 研究體系偏好的衰退預測指標
  - 加入 `DEFAULT_SERIES` + `RATE_SERIES`（享有 `value_smooth_3d` 平滑）
  - `regime_signals` 新增欄位：`yield_curve_10y3m` / `yield_curve_10y2y` / `yield_curve_10y3m_inverted` / `yield_curve_10y2y_inverted`
  - **`yield_curve_inverted` 改為 OR 邏輯**：T10Y3M 或 T10Y2Y 任一倒掛即觸發（更保守，不漏信號）
  - **`yield_curve_value` 改指 T10Y3M**（學術主數值）；T10Y2Y 保留於 `yield_curve_10y2y`（市場溝通）
  - `yield_curve_steep` 同樣改為 OR 邏輯

### Design rationale
- T10Y3M：3M 利率緊貼 Fed Funds Rate，倒掛直接反映政策過度緊縮；Estrella & Mishkin 1998 實證 R² 優於 T10Y2Y
- T10Y2Y：市場流動性最高，反映市場預期的政策轉向時間點；保留作為 forward guidance 維度
- 並存優於取代：兩個 spread 捕捉不同維度，OR 邏輯讓衰退偵測更敏感而不漏報



## v1.11.0 — 2026-04-24

### Added
- **`SAHMREALTIME` series** — Sahm Rule Real-Time Recession Indicator (FRED official)
  - `regime_signals` 新增 `sahm_value` + `sahm_triggered`（≥ 0.5 = true）
  - `_macro_scores`: 觸發時 `employment_score` **-20**（非強制 cap，保留多指標修正空間）
  - `_top_risks`: 觸發時插入第一條風險（最高優先）並標注 `⚠️`
  - 設計選擇：-20 penalty 而非 hard override，原因是 2024/8 假觸發事件（後疫情勞動力異常）顯示指標可靠性在特殊期間下降



## v1.10.0 — 2026-04-24

### Added
- **Retry with exponential backoff** in `_fetch_series()`
  - 3 attempts per series (configurable via `retries` param)
  - Backoff: 2s → 4s → 8s between attempts
  - HTTP 429 rate-limit handled separately with longer wait
  - Non-network errors (bad JSON, etc.) raise immediately without retry
- **Stale cache fallback** in `fetch()`
  - If ALL series fail (network down / FRED outage), returns existing `fred_latest.json` with `degraded_mode: true` and `degraded_reason` field
  - Downstream protocols receive valid JSON and can continue with `fred_available: false`

### Changed
- `FRED_REFRESH_SEC` default 900 → **3600** (1 hour) in `dashboard_server.py` — daily series update at most once/day; 15 min was wasteful
- `DEFAULT_TTL_SEC` 900 → **3600** in `fetch.py` — cache TTL aligned with refresh interval
- `daily_update.sh` 4 steps → **5 steps**: Step 4 adds `fetch.py --no-cache` to force FRED refresh on each daily run (skips gracefully if `FRED_API_KEY` not set)



## v1.9.0 — 2026-04-24

### Added
- **NFCI WoW monitoring** — `_derive_stats` 非 rate 系列新增 `wow_change`（7 日前對比）
  - `_regime_signals` 新增 `nfci_wow_change` + `nfci_deteriorating_fast`（WoW > +0.15）
  - `_macro_scores` financial_conditions 分支：`nfci_deteriorating_fast` 觸發 -15 分 penalty
  - 歷史根據：2007 / 2020 危機前夕 NFCI 絕對值仍負，但 WoW 加速是領先信號

- **Delta Reporting** — 跨快照增量對比
  - `fred_prev.json` — 每次 fetch 前，若 `fred_latest.json` 超過 1 小時，自動 rotate 為 prev
  - `_load_prev()` + `_compute_delta(current, prev)` — 比對 regime_label / confidence / real_rate / curve / composite
  - `main()` summary 末尾加 `── Δ vs prev snapshot ──` 區塊，僅在有實質變化（≥0.01 / ≥3pp）時顯示

- **Stale flag** — 月更指標 velocity 過期標記
  - `_derive_stats` 兩種分支均加入 `data_freshness_days`（最新 obs 距今天數）
  - `_change_velocity` 非 rate 系列：`freshness > 35` 時加 `"stale": true`
  - `main()` summary 顯示 `Stale: CPIAUCSL, UNRATE velocity may reflect prior release`



## v1.8.0 — 2026-04-24

### Added
- **`DFII10` series** (10-Year Real Interest Rate, TIPS-implied) added to `DEFAULT_SERIES` + `RATE_SERIES`
  - Market-derived daily series — no CPI publication lag
  - `regime_signals` now exposes three real-rate fields:
    - `real_rate_dfii10` — TIPS-implied (preferred; null if DFII10 fails to fetch)
    - `real_rate_10y_estimate` — legacy DGS10 - CPI YoY (backward compatible)
    - `real_rate_preferred` — dfii10 when available, else estimate; all downstream functions use this

- **`value_smooth_3d`** field on all `RATE_SERIES` entries
  - 3-observation average of the most recent daily readings
  - `_regime_signals` uses `value_smooth_3d` (via `_smooth()` helper) for T10Y2Y, DGS10, DFF, DFII10
  - Prevents score cliff-effects when a daily value crosses a hard threshold by ±1 bp (e.g. T10Y2Y 0.01 → -0.01 flipping `rates_score` from 45 → 20)
  - Monthly series (UNRATE, CPI, PCE) unaffected — smoothing only applies to daily rate series

### Changed
- All internal functions (`_macro_scores`, `_regime_label`, `_sector_rotation`, `_top_risks`, `_regime_confidence`, `_market_implications`, `_change_velocity`) now use `real_rate_preferred` with `real_rate_10y_estimate` as fallback
- Summary output now shows both `real(TIPS)=X%` and `real(est)=Y%` for comparison

### Current live divergence (2026-04-24)
- DFII10: **1.92%** vs DGS10-CPI estimate: **1.00%** — 92 bps gap due to CPI lag at current inflation turning point



## v1.7.0 — 2026-06-24

### Added
- **`macro_posture_guidance`** — 體制驅動的方向性倉位建議（`equity_exposure`, `bond_duration`, `cash_level`），附 `note` 免責聲明。不是執行指令，是 macro 訊號的定性翻譯。
- **`top_risks`** — 最多 5 條尾端風險字串，由 15+ 條件規則生成。條件涵蓋通膨 / 就業 / 信用 / 利率曲線 / 實際利率；各 regime 均有結構性兜底風險確保非空。
- **`--asof YYYY-MM-DD` backtest mode** — 以 FRED `observation_end` 拉歷史截面資料 → 分析 regime → 用 yfinance 驗證 3m 後 SPY 報酬及產業 ETF 相對表現。輸出 `backtest` 欄位含 `spy_3m_pct`, `regime_direction_correct`, `base_map`, `net_map_after_overlay`，附 `⚠️ n=1` 警告。

### Changed
- `main()` 全面重寫：`--asof` 分支獨立流程；live 模式 summary 加入 posture / risks / overlay 行；移除冗餘的 Favor/Avoid/Why 區塊。
- `_top_risks()` 增加 `REGIME_STRUCTURAL` dict 兜底，確保高風險 regime（Overheating / Late Cycle / Stagflation / Recession Easing / Transitional）必回傳至少一條風險。



## v1.6.0 — 2026-04-24

### Changed
- **`Easing Cycle` 拆分為兩個 regime**
  - `Benign Easing` — 就業穩健的保險性降息（emp_score ≥ 45 且無 credit stress + emp < 60）→ bullish，favor 成長 / 長存續期
  - `Recession Easing` — 就業 / 信用惡化的救火式降息 → bearish，防禦三角優先
  - 判斷邏輯：`emp_score < 45` 主條件；`credit_stress + emp_score < 60` 早期預警補強（信用利差領先就業 4-6 週）
- `_regime_confidence` bullish/bearish set 更新：`Benign Easing` → bullish；`Recession Easing` → bearish
- `_SECTOR_ROTATION_MAP` 新增兩個 entry，移除 `Easing Cycle`
- `_market_implications` regime_tips 更新對應兩條說明



### Added
- **`sector_rotation` dynamic overlay** — `adjustments` 欄位，由連續型 macro 變數動態計算，疊加在靜態 base map 之上
  - `real_rate_high`（>2.0%）：lower Tech / REIT，raise Financials / Energy
  - `real_rate_high` severe（>3.0%）：額外 lower Consumer Discretionary
  - `credit_stress_elevated`（HY >75th pctile）：lower Financials / Discretionary，raise Defensives
  - `yield_curve_inverted`：lower Industrials / Materials，raise Utilities / Staples
  - `yield_curve_steep`（>1.0%）：lower Utilities，raise Financials / Industrials
- **`skills/fred-macro/SECTOR_ROTATION_GUIDE.md`** — Protocol 必讀文件
  - 說明 `favor`（base）vs `adjustments`（overlay）的差異與使用時機
  - 衝突處理規則：credit stress > real rate 優先
  - 範例：Soft Landing × real_rate 3.1% 的完整推論鏈
  - 觸發條件速查表

### Changed
- `_sector_rotation(regime_label, rs=None)` 新增 `rs` 參數，backward compatible（`rs=None` 時回傳純 base）
- `sector_rotation` 輸出新增 `adjustments` list（空 list = 無 overlay 觸發）



### Added
- **`_regime_confidence` data freshness penalty** — 在既有 signal agreement 基礎上，加乘 freshness factor
  - 只懲罰「超過預期更新周期」的序列（e.g. CPI 45d 內 = 正常，54d = 超期 9d → 小扣分）
  - `EXPECTED_LAG` 表：日度（DFF/T10Y2Y/DGS* 2d）→ 週度（ICSA 9d）→ 月度（UNRATE 40d / CPI 45d / PCE 50d）
  - 每超期 30 天扣 5%（per-series 上限 15%，全局 freshness floor 70%，最終 confidence 下限仍 0.20）
  - 範例：`PCEPILFE` 82d（超期 32d）haircut 5.3%；`CPIAUCSL` 54d（超期 9d）haircut 1.5%
- `_regime_confidence(series=None)` 新增 `series` 參數（backward compatible，None 時跳過 freshness）



### Changed (breaking for rate series output schema)
- **Rate series 改用 bps 表達變動量** — `DGS10` / `DGS2` / `T10Y2Y` / `DFF` / `BAMLH0A0HYM2` 不再輸出 `yoy_change_pct` / `mom_change_pct`，改為 `delta_bps_1m` / `delta_bps_3m` / `delta_bps_1y`
  - 例：DGS10 4.3% → 4.0% 舊版輸出 -7%，新版輸出 -30 bps（市場慣用語）
- **`trend_30d` / `trend_90d` 閾值分離** — rate series 改用 ±10 bps 判斷漲跌，非利率序列保持 ±2%
- **`_regime_signals` Fed 方向判斷改用 `delta_bps_3m`** — 閾值從 ±5% 改為 ±25 bps（一個 25bp 升降息）
- **`_change_velocity` rate series** — velocity 比較改為 `delta_bps_1m` vs `delta_bps_1y / 12`（月均 bps 基準），輸出 `monthly_baseline_bps`

### Added
- `RATE_SERIES` 全局常數（set），集中管理利率 / 利差序列清單
- `_derive_stats(obs, series_id=None)` — 新增 `series_id` 參數，自動切換 bps / pct 輸出模式



### Fixed (critical)
- **`_derive_stats` 窗口計算全面修正** — 原本 `obs[:30]` / `obs[:365]` 是「最近 N 筆觀測值」，對月度序列（UNRATE / PAYEMS / CPI）等於 2.5 年 / 30 年，完全錯誤。全部改用 **calendar days 過濾**（`_window(days)` helper），確保日度 / 週度 / 月度序列使用同一時間標準

### Changed
- `percentile_1y` — 改為「過去 365 個曆日內的觀測值」排名，不再以觀測筆數計
- `trend_30d` — 改為「過去 30 個曆日」端點漲跌幅，不再是「最近 30 筆觀測值」

### Added
- **`trend_90d`** — 新增 90 曆日中期趨勢欄位（`rising` / `falling` / `stable`），與 `trend_30d` 搭配可判斷短期反彈 vs 中期走勢背離（e.g. `T10Y2Y` 30d=rising 但 90d=falling → 曲線短期反彈中仍處中期下行）



### Added
- **`macro_scores`** — 6 維度百分制評分（`rates` / `inflation` / `employment` / `credit` / `financial_conditions` / `composite`），讓下游 Protocol 可做數值比較，不再依賴文字訊號
- **`regime_label`** — 9 種市場體制標籤（Goldilocks / Soft Landing / Reflation / Easing Cycle / Overheating / Late Cycle Tightening / Stagflation / Recession Risk / Transitional）
- **`regime_confidence`** — 體制標籤可信度分數 0.20–0.95，按多指標一致性加權計算
- **`market_implications`** — 每個體制對應的市場含義文字清單，可直接貼入報告
- **`change_velocity`** — 每個關鍵序列的加速度（`accelerating` / `decelerating` / `stable`），比較 MoM vs YoY/12 月均基準
- **`sector_rotation`** — 當前體制對應的偏多 / 偏空產業清單 + 中文理由

### Fixed
- **`inf_ref` truthiness bug** — `inf_ref = core_pce or core_cpi or cpi_yoy` 當通縮邊際 `core_pce = 0.0` 時被視為 falsy 而 fallback 到次選。改用 `is not None` 鏈式判斷
- **`_change_velocity` 循環邏輯** — 原本比較 MoM vs `trend_30d`（同一視窗，自我比較無意義）。改為 MoM vs `yoy / 12`（年化月均基準），ratio > 1.2 → accelerating，< 0.8 → decelerating
- **`_regime_label` Reflation 條件過寬** — `fed_dir flat + composite ≥ 55` 幾乎匹配所有正常市場。收緊為「Fed 不升 + 通膨低基期（inf_score ≥ 45）+ composite < 55（仍在恢復）」才觸發 Reflation
- **Goldilocks vs Soft Landing 判斷順序** — Goldilocks 是 Soft Landing 的強化版（更嚴格條件），移到 Soft Landing 之前優先匹配，避免 Goldilocks 永遠被 Soft Landing 攔截
- **PAYEMS 就業評分** — PAYEMS 是累積型 level series，percentile_1y 永遠近 100 無意義。改為加入 PAYEMS YoY growth rate：< 0% 扣 10 分，> 1.5% 加 5 分
- **cache-hit summary** — `main()` cache hit 路徑補印新欄位（regime / confidence）

### Changed
- `fetch()` payload 新增 6 個頂層欄位：`macro_scores` / `regime_label` / `regime_confidence` / `market_implications` / `change_velocity` / `sector_rotation`
- `main()` human summary 重構，首行顯示 Regime + confidence；新增 macro scores / sector rotation 區塊

---

## v1.0.0 — 2026-04 (initial)

### Added
- 13 個 FRED 序列並行拉取（ThreadPoolExecutor × 6）
- Per-series 統計：`value` / `date` / `yoy_change_pct` / `mom_change_pct` / `percentile_1y` / `trend_30d`
- `regime_signals` 衍生訊號：yield curve inversion / steep / Fed direction / real rate / credit stress / financial stress
- 15 分鐘 TTL cache（`cache/fred_latest.json`）
- `--json-only` / `--no-cache` / `--series` / `--max-age` CLI 參數
- SSL-safe：以 `requests` library 取代 `urllib`（Python 3.11 macOS cert 問題）

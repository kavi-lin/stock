# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + [SemVer](https://semver.org).
Single source of truth for version history. Current version authority is `VERSION` file + `Dashboard/utils.js`.

> **Purpose**: Let future Claude sessions (and humans) understand the evolution
> of the system — what changed, where to look, why. Entries link back to git
> commits where applicable; for un-committed work, dates reflect local VERSION
> bump time.

---

## [2.13.0] — 2026-05-03
### Added — invest protocol V5.0 subagent 對齊「外部專業分析師 prompt 模板」+ 新 PM 整合層欄位

**動機**：user 看了一份外部分享的 4 套「專業分析師」prompt 模板（技術 / 基本面 / AI 交易決策整合 / 市場消息），對照 V5.0 protocol 找出可優化或缺失的部分。實測 V5.0 結構上已覆蓋 70-75%，剩 25% 是 output JSON 欄位缺漏，不需要新 lane / 不動 score 公式。

**設計原則**（沿用 V2.10 哲學）：純加 narrative / metadata 欄位；final_score 公式不變；schema validator 不擋；舊報告分數可重現。

**Phase A — Technical lane 補三件**（對應外部模板 A）：
- `smart_money_analysis`（label + narrative）— 從 insider Q ratio + 量價背離 + analyst sell-side flow 綜合判
- `pattern_taxonomy`（8 種強制分類）— breakout / consolidation / pullback / false_breakout / topping / downtrend / oversold_bounce 等 + 確認條件 1 句
- 三件套 output：`market_strength` (STRONG/NEUTRAL/WEAK) / `key_levels` ({support, resistance, pivot}) / `high_prob_scenario` (1 句帶價位 + 觸發條件)

**Phase B — Fundamentals lane 補兩件**（對應外部模板 B）：
- `moat_assessment`：WIDE/NARROW/ERODING/NONE + type (brand/IP/switching cost...) + 1 行依據
- `near_term_catalysts[]`：3-5 筆 {date, type, description, impact}
- `bull_thesis_one_line` / `bear_thesis_one_line`：≤ 40 字二元對偶 narrative

**Phase C — News lane 補時間軸**（對應外部模板 D）：
- `immediate_catalyst_5d`：5 天內 binary 事件物件或 null
- `medium_term_shift_20d`：5-20 天 narrative 移轉預期
- `decision_point_days`：下次重新評估的天數
- `cross_asset_spillover[]`：受影響的非個股市場（treasury_10y / DXY / oil / sector_ETF...）+ 傳導機制

**Phase D — Phase 3 PM 整合層補 4 欄位**（對應外部模板 C）：
- `institutional_lens`：1-2 句機構流向整合 narrative（綜合 Sentiment.institutional + Congress trades + FTD + V2.9.0 institutional_holders_qoq_delta）
- `decision_confidence_pct`：int 0-100，與既有 avg_confidence (0-1) 共存
- `scenario_odds`：{bull, base, bear} int 加總 100，三劇本機率
- `action_label`：ATTACK / WAIT / DEFENSIVE，與既有 final_action (BUY/STAGED/HOLD/SELL) **並存補強**，不取代

**Phase F — 同步 surfacing**：
- `bridge.py` 把 7 個新欄位帶進 `recent_analysis[]`
- `Dashboard/page-decisions.js` 加 5 種新 pill：action_label 三色（ATTACK 橙 / WAIT 黃 / DEFENSIVE 灰）/ moat (WIDE 金 / NARROW 銀 / ERODING 紅) / pattern_taxonomy / market_strength / decision_confidence_pct

**Files**:
- 修改：`investment/investment_protocol_v5_0.md`（Phase 2 三 lane prompt 補強約 80 行；Phase 3 PM 整合段補 4 欄位）
- 修改：`investment/phase5_export_schema.md`（V2.13 章節 + REQUIRED table 加 7 個必填欄位）
- 修改：`bridge.py`（meta.get + audits.append 各加 7 行）
- 修改：`Dashboard/page-decisions.js`（buildV48StatusPills 加 5 種 pill）

**Phase E（historical_analog）**：規劃中未做。需要建 historical FRED 月度 vector 表 + cosine similarity；工程量大，等其他 phase 跑一陣子有數據再評估。

### Why
- V5.0 五個 lane 的內部分析其實 ≥90% 已經對齊外部模板，差別只是輸出 schema 沒結構化欄位 — 補欄位 ROI 高
- 跨 V2.10（det_shadow）+ V2.13（lane outputs + PM lens）後，每筆 invest 報告會有 ~20 個結構化 narrative 欄位，給 Dashboard / 回測 / debug 都好用
- `action_label` 與 `final_action` 並存讓「BUY 但 WAIT」這種「等條件」的細微決策可以表達；既有 5 級 final_action 不破壞回測

### Caveats
- LLM 對新 prompt 是否真的填欄位需累積 5-10 個 ticker run 才能評估；Protocol prompt 已加「**必填**，缺資料寫 `INSUFFICIENT_DATA` 而非 null」
- `near_term_catalysts[]` 與 `_phase3.upcoming_events[]` 視角不同：前者限該 ticker 自己的事件，後者跨 sector — 不衝突
- Validator V2.13 新欄位**不**列為 hard-required（informational 階段，累積 30+ run 後再評估提升）
- Dashboard pill 數可能變多（最多 +5）—visual density 升高；如果太擠可後續整併到 expander
- Phase E historical_analog 留待後續

---

## [2.12.0] — 2026-05-03
### Added — radar 頁加 per-theme mini heatmap (intraday) + click→K-line drill + top 5 movers 意義說明

**動機**：user 看 radar 頁覺得「全 theme grid 沒視覺衝擊」，想要每個 theme 自己的 finviz 風 mini heatmap（半導體 theme 內的 TSM/NVDA/AMD 用顏色顯示當日漲跌+成交量）；同時不知道 expanded panel 的 top 5 movers 是怎麼挑出來的。極短期（intraday，今天）vs 短期（thematic-screener 5d horizon）兩個視角分工清楚。

> **設計 pivot**：第一版誤做成全市場 sector heatmap（與 sector.html 重複，517 ticker 巨大 SVG 拖累 radar 頁載入）。User 反饋後改正為 per-theme mini heatmap：每個 theme card 內嵌一個小 D3 treemap，僅該 theme 的 representative_stocks（typically 5-25 ticker / theme）。

**1. Per-theme mini heatmap**（極短期 intraday 視角）
- 每個 theme card 內嵌 110px 高的 D3 mini treemap（不是整頁一個大 heatmap）
- 新後端 `GET /api/theme-heatmap`：讀 `skills/theme-detector/cache/theme_detector_*.json` 拿每 theme 的 `representative_stocks` (~25 ticker)，join `_heatmap_state.tickers`（既有 517-ticker 3min thread）拼出 quote — **零新增 FMP 呼叫**
- 17 themes，16 有 ≥ 3 個 ticker 覆蓋（少數小型 theme 涵蓋率較低）
- Tile 大小依 √(market_cap)（避免 mega-cap 完全壓死小型股）；顏色依當日 % change（紅 ↔ 灰 ↔ 綠 ±3% saturation）
- Hover tooltip：sector / industry / 現價 / 漲跌 / 市值 / 日內區間 / 成交量
- Theme grid 從 6-col 改 4-col 配合 mini heatmap 寬度
- Server-side cache 3min；前端 polling 3min visibility-aware（hidden tab 暫停）

**2. Click → K-line drill**（極短期 5min OHLCV）
- 新 backend endpoint `GET /api/heatmap/intraday/<TICKER>`：FMP `/stable/historical-chart/5min`，cache TTL 15s 開盤 / 5min 收盤
- 點 heatmap tile → K-line panel 在 heatmap 上方滑入（`#radar-kline-panel`）
- Chart.js: 上方 line chart 顯示 close price，下方 bar chart 顯示 volume（顏色：bar 跟前一根 close 比，綠/紅）
- Polling 15s（盤中）/ 5min（盤後），visibility-aware；切 tab 暫停
- 「同時只追蹤 1 個 ticker」設計：新點擊取代舊計時器，避免 quota 累加

**3. Top 5 movers 意義說明**（low-effort fix）
- `renderExpanded()` 加 inline 解釋 banner：「模型對該主題內個股的『未來 5 日預期報酬 × 信心度』由高到低排序，取前 5」
- 雙語（中文 / English）依 `UI.currentLang` 切換
- 對應原始 logic：`skills/thematic-screener/scripts/screen.py:select_top_movers_ranked()` 的 `score = target_central_pct × confidence` desc

**Files**：
- 修改：`dashboard_server.py`（+ `_build_theme_heatmap_payload()` + `_fetch_heatmap_intraday()` + 2 個新 endpoint + import `date`）
- 修改：`Dashboard/radar.html`（+ D3 + Chart.js CDN + theme grid 4-col + K-line panel + tooltip）
- 修改：`Dashboard/page-radar.js`（+ mini heatmap renderer + K-line + explanation banner；theme card markup 加 mini-heatmap-slot）

**FMP 用量**：
- Heatmap quotes：背景 thread 3min/次，多 user 共用（既有，無新增）
- K-line drill：1 watcher × 4 calls/min；server cache 15s 收容多分頁；總 ≤ 5 calls/min ≪ 250 free tier

### Why
- Sector heatmap 補位 finviz-like 「市場全景」視角；theme grid 保留為跨 sector 的「主題切片」視角，兩者互補
- D3 + Chart.js 既有頁面用過（`sector.html` 與 `momentum.html`），CDN 引入零成本
- 後端用既有 `/api/heatmap/data` 基礎建設（517 ticker × 11 sector × 3min thread + heatmap.json 持久化）— 不重造輪子
- Top 5 movers 意義不明只是 UI 缺解釋，1 行 banner 解掉

### Caveats
- Heatmap K-line 用 line chart（非完整 candlestick）— Chart.js 原生不支援 OHLC，要 candlestick 需 `chartjs-chart-financial` 套件；先用 close-line + volume bar，視覺夠用
- 收盤後 K-line panel 仍可開但 bar 不再變動；header 標 `收盤 · 5min 更新`
- mega-cap 視覺壟斷（NVDA / AAPL / MSFT 占大塊）— 與 finviz 同行為，未限制 max-width；user 反饋再加
- 既有 `Dashboard/sector.html` 的 heatmap 邏輯**沒被影響**（純複製到 radar，namespace 隔離）

### Added — thematic-screener v0.3 enrichment（market_cap_tier + earnings/quality/smart-money/analyst guardrails）

**動機**：user 反饋「thematic-screener 推薦本來就很不準」+ 想看到小型股出現在 top 5 時被特別標出。盤點發現原 screener 只用「`5d target_pct × confidence`」排序，無 event 過濾、無 quality gate、無籌碼確認 — 容易推薦進財報前夜或財務岌岌可危的股票。

**新檔**：`skills/thematic-screener/scripts/enrich.py`
- 讀 3 個既有 cache（**零新 API call**）：`_shared/cache/<TICKER>_profile.json` (marketCap) + `earnings-analyst/cache/<TICKER>_*.json` (next_earnings_est) + `_shared/fmp_supp_cache/<TICKER>_*_supp.json` (Altman Z, Piotroski F, insider, institutional)
- 2 個新 FMP HTTP 端點：`/stable/price-target-consensus` (PT upside) + `/stable/grades-historical` (recent upgrades / downgrades 30d)
- 6h TTL per-ticker cache 在 `skills/thematic-screener/cache/enrich/`
- 算每 ticker 的 `enrichment_multiplier`（事件砍半 / 品質紅旗砍 40% / insider 買加 30% / 機構加碼加 20% / PT upside ±30% 範圍 / 評等升加 15%）

**Wire**：`skills/thematic-screener/scripts/screen.py`
- import enrich + 在 prediction 收集後對所有 ok ticker 一次 batch enrich
- `select_top_movers_ranked` 改用 `target_pct × confidence × enrichment_multiplier` 排序
- 每個 mover 輸出加 `enrichment` / `raw_score` / `final_score` 三 field
- framework version v0.2 → v0.3

**Market cap tier 分類**：large_cap (≥$10B) / mid_cap ($2-10B) / small_cap ($300M-$2B) / micro_cap (<$300M) / unknown

**Dashboard radar UI**：`Dashboard/page-radar.js` `renderEnrichmentPills()` 新函式
- 每 mover card 上端加 pill row：market_cap_tier (小型/微型用警告色 ⚡)、earnings within 5d/10d (📅紅/橘)、quality red_flag/premium (⚠/✓)、insider buying/selling (💰/↓)、institutional accumulation (🏦)、analyst PT upside ±%、recent upgrades (↑)、score multiplier (×N.NN)
- `Dashboard/style.css` 加 `.enr-pill` style

### Why (v0.3 enrichment)
- 原 screener 純技術 prediction → 加上 fundamental + event guardrails 後，理論上 false positive 大降（待 backtest 驗證）
- 小型股 user 想多注意 → 用 ⚡ 與警告配色 + market_cap_usd tooltip 直接顯示
- 90% 資料來自既有 cache → 加成本只有 PT + grades (≤2 calls/ticker)，全 17 themes ~80 ticker 也只 ~160 額外 call

### Tests (v0.3 enrichment)
- `python3 skills/thematic-screener/scripts/enrich.py AAPL` → tier=large_cap, MC=$4.1T, earnings 88d 安全, quality_premium (Z=11.6 F=9), PT upside +13.04%, multiplier=1.28
- screen.py smoke run 進行中：1 個 batch enrich 對所有 themes ok-ticker

### Out of scope (留 BACKLOG)
- backtest 比較 v0.2 vs v0.3 推薦在歷史 hit-rate / 5d realized return 上的差異
- 加 Finnhub `/stock/recommendation-trends` 補充 grades-historical（更詳細的買賣評等 distribution）
- 加 short interest / days-to-cover 標籤（目前只用 quality 不看 short crowding）

---

## [2.11.1] — 2026-05-03
### Fixed — proto-pill 殘留前次 invest ticker（"news · CRWV" 假象）

**問題**：user 按「盤前檢查」啟動 news + sector chain，proto-pill 顯示「news · CRWV」（CRWV 是上一次 `分析 CRWV` 的 ticker）。news DIGEST 本身沒有 ticker 概念。

**根因**（`dashboard_server.py:692-693`）：
```python
with _protocol_lock:
    if name == "invest":
        _protocol_state["analyze_ticker"] = params.get("ticker")
```
`analyze_ticker` 只在 invest 啟動時被設值，其他 protocol（news / sector / triage / flash_text / review）啟動時不動到。invest CRWV 跑完後 `analyze_ticker="CRWV"` 殘留；下一個 news 啟動 → `_protocol_state.name = "news"` 但 `analyze_ticker` 還是 "CRWV"。`get_queue_state()` 不論 name 都回傳 `analyze_ticker` → proto-pill 拼成「news · CRWV」。

**Fix**：dispatch 時無條件覆寫，ticker-less protocol 寫 None：
```python
_protocol_state["analyze_ticker"] = params.get("ticker")  # None for DIGEST/sector
```
- earnings/flash 等也有 ticker 的 protocol 反而修對了（之前是看起來對是因為 invest 殘留剛好相同 ticker）
- invest dedup 不影響（`_currently_analyzing_ticker` 已用 `name == "invest"` gate）

### Action required
restart `dashboard_server.py` 才會生效（執行中 process 還持有舊代碼）。

---

## [2.11.0] — 2026-05-03
### Added — earnings real next-date + EV ratios + theme-detector mapping + sector-analyst FMP overlay

**動機**：本 session 涵蓋 4 個獨立小強化：(1) earnings dashboard 「下次財報」一直是 +91d 猜測（用 🔮 icon 暗示）— 改用 FMP 實際日期；(2) FMP_強化分析.md 留下的 `evToEBITTTM` 坑實測 FMP 沒此欄位 — 改補 `evToFreeCashFlowTTM` + `evToSalesTTM`；(3) 全 skill × FMP catalog 盤點顯示 theme-detector 仍 finviz 為主 + sector-analyst 完全沒 FMP overlay；(4) 為 theme-detector FMP-primary 遷移建好 industry name mapping table。

### Added
- **`skills/earnings-analyst/scripts/fetch.py`** — 取代 +91d 猜測：scan 現有 `earn_surprises`（FMP /stable/earnings limit=8）找未來日期，補 `next_earnings_source`（`fmp_confirmed` / `estimated_91d`）+ `next_earnings_eps_estimate` + `next_earnings_revenue_estimate`。fallback 保留向後相容。
- **`skills/earnings-analyst/scripts/fetch.py`** `slim_ttm_keymetrics` 加 `evToFreeCashFlowTTM` + `evToSalesTTM`（FMP 沒 evToEBITTTM，走實際存在的 EV ratio 補 Burry/value 視角）。`render.py` Valuation block 同步顯示。
- **`bridge.py`** L1592 區塊 pass-through 新增 4 個 next_earnings_* 欄位到 `Dashboard/data.json`。
- **`Dashboard/page-earnings.js`** L435-453 — 依 `next_earnings_source` 切 icon：`fmp_confirmed` → 📅「下次財報」+ EPS/Rev tooltip；fallback → 🔮「下次預估」（無 source 欄位的舊 cache 自動 fallback）。
- **`skills/theme-detector/scripts/dry_run_compare.py`** — Finviz vs FMP industry 對比 dry-run（read-only，no writes to themes.yaml/cache）。輸出 `reports/theme_dry_run_<DATE>.md`。
- **`skills/theme-detector/scripts/industry_name_mapping.yaml`** — 47 rename + 8 collapse + 16 finviz_only + 6 fmp_only，把原 51% string-overlap 提升到 100% finviz coverage（migration 預備工，未啟用）。
- **`skills/sector-analyst/scripts/analyze_sector_rotation.py`** — `fetch_fmp_sector_overlay()` 新函式：FMP `sector-pe-snapshot` + `sector-performance-snapshot` 兩端點，11 sector PE + 1d / rolling 5d perf，跨 exchange 平均 + `Financial Services` → `Financial` rename 對齊 TraderMonty taxonomy。`format_json` 加 `fmp_overlay` field；human format 末尾加 Valuation+Perf 表格。No FMP key 時 graceful no-op，舊 schema 不變。

### Why
1. **next_earnings real date**：TEAM 原顯示 2026-07-30 (猜)，實際 2026-08-06。NVDA 原顯示 2026-04-26 (已過期 +91d) ，實際 2026-05-20。6 個 cached tickers 全部 `fmp_confirmed`。
2. **EV ratios**：原 `slim_ttm_keymetrics` 只有 `evToEBITDATTM` — Burry rubric 需要更多估值維度。FMP probe 證實 `evToEBITTTM` 為 ghost field（不存在），改走 `evToFreeCashFlowTTM` + `evToSalesTTM`（real fields，AAPL 驗證 OK）。
3. **theme-detector dry-run**：finviz 資料品質 ~50% 損壞（HARD_CAPS 註解已認證），FMP 完全乾淨。但 finviz 144 vs FMP 128 industries name overlap 只 51%。Mapping YAML 為日後切 primary 準備但**未啟用**（`theme_detector.py:479` 仍 import finviz_performance_client）。
4. **sector-analyst overlay**：原 skill 只用 TraderMonty CSV 的 uptrend ratio（breadth metric）— 缺估值與價格動能視角。FMP overlay 補上 PE + 5d perf，TraderMonty 仍 canonical。Investment / sector protocol 可參考新欄位但尚未強制使用。

### Tests
- `python3 skills/earnings-analyst/scripts/fetch.py TEAM --force` → cache JSON 含 `next_earnings_source: fmp_confirmed`, `next_earnings_est: 2026-08-06`, EPS est 1.14
- 6 cached tickers (TEAM/NVDA/MU/MSFT/GOOGL/AAPL) `--force` 重抓 + `python3 bridge.py` → data.json 全 `fmp_confirmed`
- AAPL re-fetch → `evToFreeCashFlowTTM=31.50, evToSalesTTM=9.01`
- `python3 skills/theme-detector/scripts/dry_run_compare.py --out reports/theme_dry_run_2026-05-03.md` → 73 matched / 71 finviz-only / 55 fmp-only
- `python3 skills/sector-analyst/scripts/analyze_sector_rotation.py --json` → `fmp_overlay` 含 11 sector PE + 11 sector perf；human format 末尾 Valuation+Perf 表格出現

### Out of scope (留 BACKLOG)
- theme-detector 切 FMP-primary（mapping YAML 已備但 `theme_detector.py:479` 未動）
- sector-analyst overlay 整合進 sector_protocol Phase 4 估值面決策（目前只是輸出，未進 rubric）
- 71 finviz-only 中部分（如 Internet Retail）值得二次審視 — 可能 FMP 用其他名稱包進去

---

## [2.10.0] — 2026-05-03
### Added — invest protocol det-shadow + polarization 標籤（保留 LLM，加 quant sanity check）

**動機**：CRWV 2026-05-03 同日重跑兩次，final_score 從 −0.055（CANCEL）跳到 −0.481（HOLD），verdict 跨 band 翻面。診斷發現主因是 5 lane 的獨立 LLM subagent 在 −2/−3 邊界各自抽到不同邊（Fund/Sent 兩 lane 同向 ±1 notch ≈ ±0.40 final_score）。架構上正常 noise 但 user 體感很怪。

**設計**：保留 LLM 判斷主分數（不犧牲 nuance），加 deterministic shadow 與 polarization label 做平行 sanity check：

**1. Polarization detection**（純 LLM lane scores 算，無新依賴）
- `signal_polarization`: `BIPOLAR` (range ≥ 4 + 任一 lane ≥ +2 + 任一 ≤ −2) / `MIXED` (range ≥ 3 一正一負) / `ALIGNED`
- 跨 run 一致：CRWV 兩 run 都判 BIPOLAR，user 一眼就知道「這股本來就會晃」

**2. Deterministic Valuation shadow**（從 weighted_fair_value vs price 算）
- `valuation_score_det`：閾值表 ≥+30%→+1 / ≥+10%→+0.5 / ≥−5%→0 / ≥−20%→−0.5 / <−20%→−1
- `val_agreement`：AGREE (|Δ|≤0.25) / DRIFT (≤0.75) / DISAGREE (>0.75)

**3. Deterministic Red Team shadow**（6 條 quant kill triggers）
- 觸發條件：`Altman Z<1.8 / D/E>5 / FCF<0 / insider<0.3 / short>20% / FRED sector_avoid`
- count ≥ 5 → STRONG_COUNTER；≥ 3 → MODERATE_COUNTER；否則 NO_VIABLE_COUNTER
- `red_team_agreement`：LLM verdict vs det 對照

**CRWV 案例驗證**（apply 在歷史兩 run 上）：

| | Run 1 (CANCEL, −0.055) | Run 2 (HOLD, −0.481) |
|---|---|---|
| signal_polarization | **BIPOLAR** | **BIPOLAR**（兩 run 一致 ✓） |
| valuation_score_det | 0 | 0 |
| val_agreement | DRIFT | **DISAGREE** |
| red_team_verdict_det | STRONG_COUNTER | STRONG_COUNTER |
| red_team_agreement | AGREE | **DISAGREE** ⚠ |

→ Run 2 雙 DISAGREE flag 揭露「LLM 比 quant 寬容了」，這是 final_score 之外的關鍵資訊維度。

**Files**:
- 新增 `investment/scripts/apply_det_shadow.py`（pure-python post-processor，無新 API call）
- 新增 schema 欄位（trades_this_session[]）：`lane_scores` / `det_inputs` / `det_shadow`
- 修改 `investment/phase5_export_schema.md`（V2.10 章節）/ `investment/investment_protocol_v5_0.md`（Phase 5 加 Step 1.5）
- `bridge.py` 把 `det_shadow` 帶進 `recent_analysis[]`
- `Dashboard/page-decisions.js` 加 BIPOLAR / MIXED / RT DISAGREE / VAL DISAGREE 四個 pill（hover tip 解釋）
- 歷史 CRWV 2026-05-03 兩 run 已 backfill `lane_scores` + `det_inputs` + `det_shadow`（從 bias_notes 與 fmp_supp_cache 重建）

### Why
final_score noise（±0.3-0.5）在 BIPOLAR 兩極股本來就是架構天然上限（5 個獨立 LLM subagent），改全 deterministic 會犧牲 LLM 看軟訊號的能力（如 "Microsoft $10B 合約" 這種 quant rule 看不到的事）。V2.10 走中間路線：LLM 主分數不變，加 sidecar 顯示「LLM 跟 quant 是否一致」+「股票本身是否兩極化」。痛點被打到（CRWV 重跑 verdict 翻面看起來矛盾 → 加 BIPOLAR badge 後 user 預期管理對了），同時保留 LLM 彈性。

### Caveats
- `lane_scores` / `det_inputs` 必須由 LLM 在 Phase 5 Step 1 寫入（protocol 已加註）；否則 polarization/red_team_det 各自 graceful skip，不影響其他欄位
- val_det 只看 FV vs price ratio（純算數），不考慮 distress / FCF quality 等軟訊號 — 這是設計（要的就是 quant baseline）；若 LLM 加分 distress 因素到 −1，shadow 顯示 DISAGREE 是預期行為，user 知道 LLM 多扣分了
- Threshold（kill trigger 數 ≥5 / ≥3、val 分數閾值）目前是 Day-1 拍腦袋值；累積 30+ ticker 數據後可校準

---

## [2.9.1] — 2026-05-03
### Added — earnings card 4 score bar tooltip + fiscal-aware 日期 + next earnings

**問題**：User NVDA card 截圖回報三點 (V2.8.x 殘留)：
1. Quality / Growth / Value / Analyst 四 bar 看不出含義 + 視覺上「都滿的」
2. `2026-01-25` 看不出意思（應為 Q4 FY26）
3. 沒有下次財報日 + 哪季

**Fix**：
1. **Bar tooltip**：每 bar 加 `data-signal-tip="ed_score_<key>"`，hover 出 sector-style rich card 解釋該分項組成（Quality 4 子項、Growth 4 子項、Value 4 子項、Analyst 4 子項）+ how-to-read tip。`Dashboard/utils.js` 加 4 個 SIGNAL_TIPS entries (zh+en)
2. **Bar pct 顯示**：`25/30 → 25/30 · 83%`，VALUE 16/25 立刻看出 64% 比 GROWTH 100% 短
3. **Last earnings pill 加 fiscal**：`📅 2026-01-25` → `📅 Q4 FY26 · 2026-01-25`（無 fiscal_label fallback to date only）
4. **Next earnings pill 新增**：`🔮 Q1 FY27 · 2026-04-26`，fiscal 自動 +1 quarter
5. `bridge.py:extract_earnings_analyses` 讀 sibling `<TICKER>_<DATE>.infographic.json` 取 `fiscal_label` 注入 listing payload；無 infographic 則 None

### Files changed
- `bridge.py` — `extract_earnings_analyses` 加 lazy load `fiscal_label` from infographic
- `Dashboard/utils.js` — 加 4 SIGNAL_TIPS (`ed_score_quality / growth / value / analyst`)
- `Dashboard/page-earnings.js` — `renderComponentBars` 加 `data-signal-tip` + pct%；`renderCard` 用 fiscal_label 包 last earnings pill + 新增 next earnings pill
- `Dashboard/earnings.html` — body 加 `<div id="signal-tip-tooltip">`、新 `.ea-pill-date-next` (purple dashed) + `.ea-comp` hover tint

### 驗證
- 5/6 tickers 有 infographic → fiscal_label 正確顯示（AAPL FY26 Q2 / MSFT FY26 Q3 / GOOGL FY26 Q1 / TEAM FY26 Q3 / MU FY26 Q2）
- NVDA 無 infographic → 退化為 `📅 2026-01-25` + `🔮 2026-04-26`（無 fiscal prefix）
- Hover 任 bar → tooltip 出現解釋

---

## [2.9.0] — 2026-05-03
### Added — sector protocol 三個新 FMP 訊號（不改 rubric，純 Phase 4b divergence 提示）

**動機**：對照 V2.8.2 整理的 FMP MCP 完整清單，sector protocol 還有三個高價值訊號沒納入：(1) `form13f_top10_delta` 一直是 null；(2) sector 層級沒有 forward valuation 訊號；(3) 動能訊號只有 3M 一個視窗。

**1. Institutional Q-on-Q（取代 form13F）**：`sector/scripts/fetch_smart_money.py` 加 `/stable/institutional-ownership/symbol-positions-summary` 對 SECTOR_UNIVERSE 全 ticker aggregate
- 新欄位：`institutional_holders_qoq_delta`（13F filer 數 QoQ 增減 sum）+ `institutional_ownership_pct_delta`（機構持股 % QoQ 變化 median）+ `institutional_sample_size`
- 頂層 metadata `institutional_quarter`（如 `"2025Q4"`）
- helper `latest_complete_13f_quarter()` 加進 `sector/lib/date_utils.py`（13F 申報截止 45 天 lag rule）
- soft-fail per ticker；`--skip-institutional` 旗標可省 ~131 calls
- `form13f_top10_delta` 欄位保留向後相容，永遠 null（已被取代）

**2. Forward valuation via PT consensus**：`sector/scripts/fetch_earnings_pulse.py` 加 `/stable/price-target-consensus` 對 SECTOR_TOP_5 + 單一 batch 拉 55 ticker 當前價（`/stable/batch-quote-short`）
- 新欄位：`analyst_pt_upside_median_pct`（中位 PT 上行空間，0.05 = 5% upside）+ `pt_sample_size`
- soft-fail；CLI flag `--skip-grades` → `--skip-analyst`（同時跳過 grades + PT），舊 flag alias 向後相容

**3. 多週期 RS（零新增 API call）**：`sector/scripts/fetch_sector_valuation.py` 重用既有 3M ETF chart 計算 5d / 20d
- 新欄位：`rs_vs_spy_5d` / `rs_vs_spy_20d`（既有 `rs_vs_spy_3m` 對 V2.8.x cache **byte-identical**）
- 用法：3M 強但 5d/20d 同向轉弱 = 動能耗盡訊號

**Phase 4b 新規則**（不寫進 score 公式，只給 LLM divergence challenge 用）：
- 規則 5 擴充：HOT + 13F holders QoQ < 0 AND ownership % QoQ < 0 AND sample_size >= 3 → smart_money_divergence
- 規則 6 新增：HOT + PT upside median < 3% AND pt_sample_size >= 3 → pt_target_exhausted
- 規則 7 新增：HOT + 3M RS > +5% AND 5d/20d 皆 < 0 → momentum_exhaustion

**Files changed**：
- 新增 fields 不動 schema 結構：`sector/scripts/fetch_smart_money.py` / `fetch_earnings_pulse.py` / `fetch_sector_valuation.py` / `sector/lib/date_utils.py`
- Doc 同步：`sector/schema.md`（V2.9.0 changelog block + Validator Coverage 註記）/ `sector/scripts/README.md`（endpoint 表 + skip flag）/ `sector/BACKLOG.md`（form13F 段更新 + acquisition-ownership 已評估不採用 rationale）/ `sector/phase_1-2-3.md`（Step 2/3b/3c 加新訊號用法）/ `sector/phase_4-5.md`（Phase 4b 規則 5 擴充 + 規則 6/7 新增）

### Why
sector protocol 的 verdict 公式不動（向後相容；舊報告分數可重現），新訊號只進入 Phase 4b 強制 divergence challenge — 三個都有量化 threshold，避免 LLM 自由發揮。多週期 RS 零新增 API call 是 hidden bonus；institutional Q-on-Q 是真正補上 V1.4 規劃時欠下的 form13F 坑（用 free tier 可用的端點實現）。

### Bonus — `acquisition-of-beneficial-ownership` 已評估、不採用
原本 plan 要用此 endpoint 補 13D/13G 訊號，curl 實測 mega-cap 數據過時（AAPL/NVDA/META 等最近 180 天皆 0 filing），signal 對 sector aggregate 太稀疏。改走 institutional-ownership/symbol-positions-summary（涵蓋全部 13F holder 的 Q-on-Q 變動）。rationale 留在 `sector/BACKLOG.md`。

---

## [2.8.2] — 2026-05-03
### Added — FMP MCP 中文參考文件
- 新增 `reference/fmpstab/FMP_MCP_TOOLS_中文參考.md`：透過 Claude Code 載入的 27 個 `mcp__fmp__*` tool schema 整理成中文索引（~230 endpoints），每個 endpoint 帶簡短中文說明 + 必要參數 + 用途
- 含 HTTP path ↔ MCP tool 對照表，提醒「腳本走 HTTP / LLM 對話走 MCP」的分工
- 來源：`claude mcp list` ✓ Connected `https://financialmodelingprep.com/mcp?apikey=...`

### Why
之前的 `FMP_API_中文參考.md` 是 HTTP REST 視角；MCP 連線後 LLM 在對話中可以直接呼叫工具，需要一份「MCP tool/endpoint 名稱」對照才好查。這份文件補位，未來 endpoint 增減重跑 ToolSearch 即可重生。

---

## [2.8.1] — 2026-05-03
### Changed — earnings-detail chart 整合：取消 ? icon、disable Chart.js 原生 tooltip、加 always-visible inline 數據

**問題**：V2.7.18 用 `?` icon 分離兩種 tooltip，user 拒絕（不想 ? 干擾視覺）。雙 tooltip（card-level signal-tip + bar-level Chart.js dark popover）仍會疊。

**新方案**：單一 tooltip + 永遠可見的 inline 數據。
- HTML：移除 `?` icon button，還原 `data-signal-tip` 到整個 chart card；canvas 下方加 `<div class="ed-chart-summary">`
- JS：6 個 chart `plugins.tooltip.enabled = false`（Chart.js 原生 dark popover 全關），渲染後 populate inline summary：
  - Revenue/NI: `Revenue $111B · Net Income $30B · YoY Rev +X%`
  - EPS: `Latest $2.02 · 5Q $1.57–$2.85 · YoY +22%`
  - OCF/FCF: `OCF $28.7B · FCF $26.7B · FCF margin 24.0%`
  - GM/OM: `GM 49.3% · OM 32.3% · GM Δ -0.5pp`
  - Segment: `iPhone +21.7% · Services +16.3% · Mac +5.7% · ...`
  - Geo: `USA +85% · TW +25% · CN -8% · APAC +45% · ...`
  - 顏色：positive 綠 / negative 紅 / neutral 主色
- CSS：刪 `.ed-chart-help` / `.ed-chart-title-row`（unused），新 `.ed-chart-summary` + `.ed-chart-summary-item` + `.ed-chart-summary-label`，dashed top-border 與 chart 視覺分離

### 行為
- Hover chart card → ONE signal-tip card 解說（bar hover 不再跳第二 tooltip）
- 精確數值看 canvas 下方 inline 一行（永遠可見、wrap 自適應）

### Files changed
- `Dashboard/earnings-detail.html` — 6 card 移除 `?` button + 加 `<div class="ed-chart-summary">`
- `Dashboard/page-earnings-detail.js` — 全 chart `tooltip: { enabled: false }`；新 `_setChartSummary / _summaryItem` helper；6 chart 各加 summary 計算 ~80 行
- `Dashboard/style.css` — 刪 ~30 行 unused styles + 新 `.ed-chart-summary` block

### Why
解決連兩版（V2.7.16 雙 tooltip 撞 + V2.7.18 ? icon 不滿意）的反饋：要單一 tooltip + 數字一目了然。

---

## [2.8.0] — 2026-05-03
### Changed — sector protocol fetch 層 DRY refactor + 註解外移

**動機**：sector/scripts 4 份 fetch 腳本 `_fmp_get` 邏輯重複 4 次（4 × ~20 行），docstring 把「為何 hard-fail / form13F 緩議 / analyst_revision 緩議」這類背景資訊寫在 code 裡，每次改腳本都要繞過長 header；同時 `reference/fmpstab/FMP_API_中文參考.md` 還有 free-tier 可用、但沒納入的 endpoint。

**Refactor**：
- 新增 `sector/lib/{__init__.py, fmp_client.py, date_utils.py}`，集中：`fmp_get()`（含 429 退避 + 4xx 不重試）、`cache_path()`、`SECTOR_UNIVERSE/TICKER_TO_SECTOR/SECTOR_TOP_5` re-export、`lookback_window()/cutoff_date()`
- 4 份 fetch 腳本（`fetch_sector_valuation.py` / `fetch_earnings_pulse.py` / `fetch_smart_money.py` / `fetch_sector_news.py`）移除自家 `_fmp_get`、改 import lib；docstring 縮為 2–3 行；行為對前 cache 檔 byte-identical（`sector_valuation_2026-05-01.json` 與 `sector_earnings_pulse_2026-05-02.json --skip-grades` diff = 空）
- `validate_sector_intel.py` header 從 22 行縮為 5 行；驗證項目搬到 `sector/schema.md` 新增的「Validator Coverage」section

**註解外移**：
- 新增 `sector/BACKLOG.md`（form13f / analyst_revision deferred / MCP-vs-HTTP 路徑）
- 新增 `sector/scripts/README.md`（hardness 表、retry 策略、執行範例）

### Added — Phase 3 補位 endpoints（並行、不取代 WebSearch）
- 新增 `sector/scripts/fetch_general_news.py`（FMP `/stable/news/general-latest`，limit=20）— **soft-fail**（失敗寫 `{available: false}`，protocol 不中斷）
- `phase_1-2-3.md` 新增 Step 3e（fetch_general_news）；Step 5 WebSearch budget 依 `general_news.available` 動態調整：true → ≤1 query（純突發）；false → ≤2 query（回退原 V1.4 規則）— **WebSearch fallback 永遠保留**
- `fetch_earnings_pulse.py` 加 `fetch_grades_consensus_for_sectors()`：對 `SECTOR_TOP_5` 各 ticker 呼叫 `/stable/grades-consensus` 加總 `(strongBuy+buy)−(sell+strongSell)` 填 `analyst_revision_net`（之前永遠為 null）— soft-fail per ticker，整體失敗欄位回 null；新加 `--skip-grades` 旗標可省 55 calls

### Fixed — `fmp_client.fmp_get` 4xx 不重試
4xx（除 429）為永久 client error，原 retry logic 浪費 3 × 0.5s。新增 `400 ≤ status_code < 500` early-break，避免 endpoint 不存在或 ticker 無資料時的無謂等待。

### Files changed
- 新增：`sector/lib/__init__.py`、`sector/lib/fmp_client.py`、`sector/lib/date_utils.py`、`sector/BACKLOG.md`、`sector/scripts/README.md`、`sector/scripts/fetch_general_news.py`
- 修改：`sector/scripts/fetch_sector_valuation.py`、`sector/scripts/fetch_earnings_pulse.py`、`sector/scripts/fetch_smart_money.py`、`sector/scripts/fetch_sector_news.py`、`sector/scripts/validate_sector_intel.py`、`sector/phase_1-2-3.md`、`sector/schema.md`
- 不動：`sector/sector_protocol_main.md`（rubric 維持原樣）、`render_sector_report.py`、`step6_overlay.py`、Dashboard、bridge.py、daily_update.sh

### Why
WebSearch 在 Phase 3 narrative 是刻意保留的 fallback，不該被取代只該被「補位」。Refactor 行為對舊 cache byte-identical 確保 V1.4 報告輸出不變；新增 grades-consensus / general-news 都是 soft-fail，FMP 故障時自動回退到既有 WebSearch 預算。

---

## [2.7.18] — 2026-05-03
### Fixed — 快速啟動引擎 widget 沒區分 protocol type 導致 user 誤把財報當成投資分析

**問題**：index.html 「快速啟動引擎」widget 的「最近」行顯示 `✓MU`，user 以為 MU 是投資深度分析（決策中心應顯示），但其實是 earnings 跑的（5/3 10:36 完成）→ 「決策中心」沒有 5/3 MU = 對的。

**Fix** (`Dashboard/analyze-queue.js`)：
- 新 `_protoMeta(name)` mapping：invest=🔬分析 / earnings=📊財報 / news=📰新聞 / sector=🌐產業 / llm_review=🤖檢討 / flash=⚡ / triage=🔍
- Active 行：`🔬 QCOM` (含 icon)
- Recent 行：`✓📊MU · ✓🔬AAPL` 每筆前綴 protocol icon + status icon
- Pending queue pill：同樣加 icon
- title 屬性帶 `分析 QCOM` / `財報 MU` 等中文 label，hover 確認

### Why
User 截圖顯示 widget 的「分析中 QCOM」+「最近 ✓MU」，沒辦法區分 QCOM 是 invest deep-dive、MU 是 earnings analysis。視覺上看起來像「同類任務」造成決策中心查無 MU 的混淆。

---

## [2.7.17] — 2026-05-03
### Added — 盤前檢查 chain：daily_update + news 平行 → sector → AI 裁決自動刷新

**問題**：原盤前檢查只跑 4 個 free shell + news/sector 序列，**沒呼叫 daily_update.sh**，user 須手動跑兩次。daily_update 內含 FRED / bridge / thematic-screener 等 preflight 完全不管的步驟。

**設計**（user 確認）：
- **Phase 1 平行**：`bash daily_update.sh` (~10 min) + `news` Claude protocol (~12 min) — 兩者無 file 相依，平行省 ~10 min
- **Phase 2 序列**：`sector` Claude protocol（讀 news digest + breadth/ftd/market_top cache）
- **Phase 3 自動**：bridge.py 在 protocol worker 內建跑 → data.json 更新 → index.html 4 pills 自動 reload（無新 Claude call）

### Files changed
- `daily_update.sh` — 標準化所有 step 標籤為 `[N/6]`（原本 mix `[N/5]` + `[5/6]`），給 backend stdout parser 抓進度
- `dashboard_server.py` — 新 `_daily_update_state` dict + `run_daily_update()` runner（Popen + line-by-line stdout 解析 `[N/6]` 更新 `current_step`）+ `POST /api/run-daily-update` + `GET /api/run-daily-update/status` 兩 endpoint
- `Dashboard/index.html` — `#preflight-modal` 內加 `#preflight-chain` 三 phase 區塊（daily_update / news / sector / AI 裁決 4 row 含 progress bar）+ 新主按鈕「開始盤前檢查」；既有 free/all-stale 按鈕降為次要（向下相容）
- `Dashboard/script.js` — 新 `runPremarketChain()` orchestrator + `_pollDailyUpdate()` + `_pollProtoForChain()` + `_maybeStartPhase2()` + `_finalizeChain()` + DOM helpers `_setRow / _fmtSec`
- `Dashboard/style.css` — 新 `.preflight-phase` / `.preflight-row` / `.preflight-row-bar` 全套樣式
- `Dashboard/i18n.js` — 加 `preflight.{run_chain, phase1_title, phase1_hint, phase2_title, phase2_hint, phase3_title, phase3_hint, waiting_phase1, waiting_phase2, ai_verdict}` 10 keys × zh/en

### 驗證
- `curl -X POST /api/run-daily-update` → 202 + job_id
- `curl /api/run-daily-update/status` → status=running, current_step=3/6, elapsed_sec=13s（parser 正確抓 `[ 3/6 ]` echo）
- 不含 cancel button — user 確認任意中斷 = 關 modal 即可（背景 subprocess + Claude queue 繼續）
- Progress UI = bar + N/6（user 確認）；無 step 名稱

### 不做
- 不改 daily_update.sh 內部執行邏輯
- 不引入並行 Claude（既有 _analyze_worker 仍 single-threaded FIFO；news + sector 仍序列，但 daily_update.sh 是 shell 平行於 Claude queue）
- 不為 earnings/momentum/radar 加 phase
- 不刪 /api/preflight/run-free（向下相容）

---

## [2.7.16] — 2026-05-03
### Added — chart i18n + sector-style tooltip + 全域 protocol status pill

**改動 1：chart 翻譯 + sector-style tooltip**
- 中文模式 chart legend：Revenue→營收、Net Income→淨利、OCF/FCF/GM/OM 縮寫保留 + 中文長標題
- 每個 chart card 加 `data-signal-tip="ed_chart_<x>"`，hover 出 sector page 同款 rich tooltip：title + 多段 desc（解釋 OCF / FCF / GM / OM / Net Income / EPS 是什麼、看點、watch threshold）+ hint
- 6 個 tip 條目：`ed_chart_revenue_ni` / `_eps` / `_cashflow` / `_margins` / `_segment_growth` / `_geo_growth`，全部 zh + en
- earnings-detail.html 加 `<div id="signal-tip-tooltip">` 啟用 utils.js 既有 tooltip engine

**改動 2：全域 protocol 狀態 pill**

**問題**：user 在 earnings page 觸發財報分析任務（POST /api/protocol-queue），看到 toast 確認入排，但切到其他頁面（index / calendar）後**任何狀態都消失**，不知道任務還在不在跑。其他頁面也沒地方顯示 active job。

**Fix**：utils.js 加 `pollProtoPill` 每 5 秒 GET `/api/protocol-queue`，根據 `active` + `queue.length` 動態 render 一個 fixed bottom-right pill，跨頁持續顯示：
- Idle → 隱藏
- Running → indigo pulse 邊框 + 自旋 🔄 + `<protocol> · <ticker> · 2m 12s` + queue count
- Click chevron → expand 詳情：active job + queue list (max 5 rows)
- 利用 `utils.js` 已存在每頁載入 → 自動跨頁可見，無需每頁手動加

### Files changed
- `Dashboard/utils.js` — 加 6 個 SIGNAL_TIPS chart entries + `ensureProtoPill / pollProtoPill / fmtElapsed` 三個 helper + 5s 輪詢
- `Dashboard/earnings-detail.html` — 6 chart card 加 `data-signal-tip` attribute + body 加 `#signal-tip-tooltip` div
- `Dashboard/page-earnings-detail.js` — chart legend labels 改用 `i18n.legend_*` 變數
- `Dashboard/i18n.js` — 加 8 個 `legend_*` key（zh/en）+ 改 `chart_eps/cashflow` 中文標題用全名
- `Dashboard/style.css` — 加 `.proto-status-pill` 全套樣式（fixed bottom-right、indigo pulse、spin icon、expandable detail panel）

### Why
chart 上線後 user 反映：(a) 中文模式 OCF/FCF/GM/OM 應翻譯、(b) 不知道每個 chart 在看什麼、(c) earnings 觸發任務後切頁失蹤。三點一次解。

---

## [2.7.15] — 2026-05-03
### Added — earnings-detail page 加 6 chart 趨勢圖區塊（Chart.js）

**動機**：既有 detail page 只看當季數字 + segment 卡片，沒歷史趨勢視覺。User 提供 reference image 要 5Q bar/line chart 風格。

**整合決定**：純新增不取代 — 既有 metric card / segment grid / geographic cell 全保留（資訊密度高），上方加 chart row 提供 5Q 趨勢視角。

**新增 6 charts**：
1. Revenue + Net Income bars × 5Q
2. EPS line × 5Q
3. OCF + FCF bars × 5Q
4. Gross + Operating Margin lines × 5Q
5. Segment YoY Growth horizontal bars
6. Geography YoY Growth horizontal bars（AAPL 為 FY-only fallback → 該卡片自動隱藏）

**FMP API 限制**：geographic Q-level YoY FMP 不提供（只 FY annual），唯一管道 = earnings transcript LLM 抽（infographic.geographic_q.yoy_pct）。AAPL 目前 yoy_pct=null → frontend 隱藏該 chart card。Phase 2 可改 protocol prompt narrate phase 強制從 transcript CFO 段抽 region YoY。

### Files changed
- `dashboard_server.py:1703-1736` — `/api/earnings-infographic/<TICKER>` payload `cache` subset 加三個 trend slice：`quarterly_pnl[:8]` / `cash_flow[:8]` / `margins_8q[:8]`（slim shape，只取 chart 需要欄位）
- `Dashboard/earnings-detail.html` — 加 Chart.js CDN script tag + 新 `<section class="ed-charts-section">` 含 6 個 `<canvas>`，插在 metric cards 後 segments 前
- `Dashboard/page-earnings-detail.js` — 新 `renderTrendCharts(payload)` 共 ~250 行（含 `chartTheme` / `makeChart` helper / 6 個 chart configs）；`renderAll` 加 call
- `Dashboard/style.css` — 新 `.ed-charts-grid` (2-col responsive) + `.ed-chart-card` + `.ed-chart-canvas-wrap` (200px height)
- `Dashboard/i18n.js` — 加 7 個翻譯 key（zh/en）：`section_trends` / `section_trends_hint` / `chart_*` ×6

### Why
User 提供 iOS-widget 風格 infographic 圖；既有 page 缺歷史趨勢。Chart.js 70KB 引入比手刻 SVG 動畫漂亮 + 維護成本低。

---

## [2.7.14] — 2026-05-03
### Fixed — earnings-analyst `fetch.py --force` 洗掉 analyzed fields；AAPL 補回

**問題現場**：dashboard `earnings_analyses` 只見 MSFT/GOOGL/NVDA 三筆，AAPL 不見。

**追因鏈**：
1. 5/2 01:41 有人跑 `python3 skills/earnings-analyst/scripts/fetch.py AAPL --force`（SESSION_NOTES line 189 紀錄為 transcript 測試）
2. `fetch.py` 第 451-453 行直接 `json.dump(bundle, f)` 整檔覆寫 cache JSON
3. analyze.py 之前寫進去的 5 個 fields（`composite_score` / `verdict` / `score_components` / `derived` / `quality_flags`）全洗掉
4. analyze.py 沒被接著跑 → cache 留半殘狀態
5. `bridge.py:extract_earnings_analyses:1551` `if "composite_score" not in d: continue` → 跳過 AAPL
6. data.json 缺 AAPL，dashboard 顯示也缺

**為何 UI 路徑沒問題**：dashboard「跑財報分析」按鈕走 `/api/protocol-queue {name:'earnings'}`，protocol prompt 強制 6 步驟（fetch→analyze→validate→narrate→render→validate_infographic），analyze 一定接 fetch。問題只發生在 user/dev terminal 直接 `fetch.py --force` 略過 chain。

**Fix**：
1. **`skills/earnings-analyst/scripts/fetch.py:448-470`** — overwrite 前先 `read` 既存 cache，preserve `composite_score / verdict / score_components / derived / quality_flags` 5 keys 並 stderr log 「merged N analyzed field(s)」。`--force` 不再洗 analyzed 結果。
2. **AAPL recovery** — 跑 `python3 skills/earnings-analyst/scripts/analyze.py AAPL` → composite=70/100 verdict=SOLID
3. **bridge refresh** — `python3 bridge.py` → earnings_analyses 從 3 筆變 4 筆，AAPL SOLID 70 上線

### Files changed
- `skills/earnings-analyst/scripts/fetch.py` — 加 PRESERVE_KEYS merge 邏輯（~15 行）
- (recovery actions) `skills/earnings-analyst/cache/AAPL_2026-03-28.json` 由 analyze.py 重補
- (recovery actions) `Dashboard/data.json` 由 bridge.py 重產

### Why
未來若 dev 直接終端跑 `fetch.py --force` 測試，不會再連帶把分析結果洗掉。安全網。

---

## [2.7.13] — 2026-05-02
### Added — 每週日早 6:00 自動跑 LLM Review (launchd plist)

**動機**：V2.7.11/12 落 backend queue + indexer freshness gate 後，缺定期觸發。User 要每週固定一次，避免人工健忘。

**作法**：macOS launchd `~/Library/LaunchAgents/com.kavi.aicommittee.llm-review.plist`
- `StartCalendarInterval`：Weekday=0、Hour=6、Minute=0（週日早 6:00）
- 動作：先 health-check `http://localhost:8080/api/refresh_status` (HTTP 200 才繼續) → POST `/api/protocol-queue {name:'llm_review'}`
- Log：`~/Library/Logs/llm-review-weekly.log`

**已驗證**：
- `plutil -lint` OK
- `launchctl load` 無錯
- 手動 `launchctl start` → log 寫 HTTP 200 + queue position 1（順便補 4/27→5/2 缺漏 review）

**限制**：
- Mac 6am 週日 sleep 中 → launchd 不補跑
- dashboard_server 沒在跑 → log 顯 "SKIP: not reachable"，跳過該週
- plist 在 user space (`~/Library/LaunchAgents/`)，不污染 git status

### Files added
- `~/Library/LaunchAgents/com.kavi.aicommittee.llm-review.plist`（OS-level，repo 外）

### Files changed
- `VERSION`、`Dashboard/utils.js`、`CHANGELOG.md` — 版本同步（僅 metadata，無 code）

---

## [2.7.12] — 2026-05-02
### Fixed — LLM Review event_index staleness + 收合 + 標 technical

**Issue 1**：上次 review 跑出來漏掉 4/29 NVDA / TSM 兩筆 deep-dive。根因：`event_index_latest.json` 是 4/26 11:25 indexer 跑出來的，6 天沒 rebuild。LLM Review 直接讀那份 stale 索引 → 看不到 4/27+ 的決策。

**Fix 1**：`llm_review` protocol prompt 加 Step 0 — `python3 scripts/build_event_index.py`，rc=0 才繼續。每次 review 自帶 freshness。Step 2 也加上 `generated_at == today` 檢查，否則 abort。

**Issue 2**：`REVIEW_<DATE>.md` 內容是 protocol-tuning meta-feedback（pattern stats / agent 權重建議 / score 閾值微調），給 maintainer + LLM 下次 protocol 升級時讀，不是 daily user reading。但上版直接在 calendar 攤開 13KB markdown → 用戶被迫滑過去。

**Fix 2**：`#cal-llm-review-section` 改 `<details>` 預設收合，summary 行加 `technical · protocol-tuning` tag 暗示這不是 daily report。Summary 行同時抽 `_decisions_analyzed` + pattern count + recommendation count 顯示在 meta 字串：`2026-05-02 · 56 decisions · 4 patterns · 7 recs`，user 不展開也能掌握 review 規模。

### Files changed
- `dashboard_server.py`：`PROTOCOL_PROMPTS["llm_review"]` 加 Step 0 indexer rebuild + Step 2 freshness check
- `Dashboard/calendar.html`：`#cal-llm-review-section` 從 `<section>` 改 `<details>`，summary 加 chevron + tech tag + refresh button stop-propagation
- `Dashboard/page-calendar.js`：`loadLatestReview()` 用 regex 抽 `_decisions_analyzed` / `### .+(n=N` / Adjustment Recommendations 區內 `###` 數量，組成 meta 字串
- `Dashboard/style.css`：`.cal-llm-review-details` collapsed/expanded 樣式 + `.cal-llm-review-tech-tag` chip + `.cal-llm-review-chevron` rotate

### Why
User 質問為何 4/29 兩筆深度分析被漏掉，並指出 REVIEW_*.md 內容「不是 user 該看的」。第一個是 indexer 沒自動跑的根因；第二個是把 protocol-tuning artifact 跟 daily UI 混在一起的設計錯誤。

---

## [2.7.11] — 2026-05-02
### Changed — 「請 LLM 檢討」改為 backend queue（取代 clipboard copy）

**問題**：原本 button 是把 prompt + event_index 複製到 clipboard，要 user 自己貼到外部 Claude 跑。流程斷裂、Safari 還會擋 clipboard 寫入。User 要的是：點按鈕 → 自動排隊 → 跑完結果直接顯示在頁面上。

**設計**：

1. **Backend 新 protocol `llm_review`**（`dashboard_server.py`）：
   - `PROTOCOL_PROMPTS["llm_review"]` — 指示 Claude 讀 `REVIEW_PROMPT.md` + `event_index_latest.json` → 三步驟（pattern detection / root cause / adjustments）→ 寫 `reports/decision_review/REVIEW_<TODAY>.md`
   - `PROTOCOL_LOG_DIRS["llm_review"] = "reports/decision_review"`
   - `PROTOCOL_TIMEOUT_OVERRIDES["llm_review"] = 900`（15 min）
   - 既有 `/api/protocol-queue` POST handler 自動接受新 name，無需新 endpoint

2. **Frontend click handler 重寫**（`Dashboard/page-calendar.js`）：
   - 刪舊 `prebuildLlmBundle / legacyCopyFallback / copyLlmReviewBundle`（V2.7.9 clipboard 邏輯）
   - 新 `requestLlmReview()`：`window.confirm()` 二次確認（含 「~10-15 min + Claude tokens」警示）→ POST `/api/protocol-queue { name: 'llm_review' }` → toast 顯示 queue position；409 duplicate 也照常啟動 polling
   - 新 `pollLlmReviewStatus()`：每 3s `/api/run-protocol/status`，當 `name=llm_review` 時更新 button label `檢討中… Ns`，status=done → 觸發 `loadLatestReview()`，error → toast log_tail
   - 新 `loadLatestReview()`：fetch `/decision_review/REVIEW_<TODAY>.md`，404 fallback 往前找 14 天最新存在的
   - 新 `renderReviewMarkdown()`：手刻 regex（headers `#/##/###` + bullets `-/*` + bold `**` + italic `_` + inline code `` ` `` + hr `---`），HTML escape 安全
   - 新 `checkLlmReviewRunning()`：page load 時若已在跑，自動接續 polling

3. **UI 新 section**（`Dashboard/calendar.html`）：在 `#cal-aggregate` 上方加 `#cal-llm-review-section`，含標題 + 產出日期 meta + refresh icon button + render 區塊

4. **Button 狀態**（`Dashboard/style.css`）：
   - Idle → 既有 emerald style
   - Running → indigo `cal-llm-review-running` class，pulse animation `cal-llm-pulse 1.6s`，label 動態 `檢討中… Ns`
   - Refresh icon button 同樣 disabled
   - Markdown render 樣式：h1/h2/h3 emerald + indigo 階層；code chip indigo；hr dashed

### Files changed
- `dashboard_server.py`：3 dict 各加 1 entry
- `Dashboard/page-calendar.js`：clipboard 邏輯換成 queue/poll/render（~150 lines 替換）
- `Dashboard/calendar.html`：新 section 區塊
- `Dashboard/style.css`：~120 lines `cal-llm-review-*` 樣式 + pulse keyframe

### Why
User 直接要求：「請 LLM 檢討應該透過 bridge 發到 Claude 處理 + 加到 queue + 結束後自動更新到日曆頁面」。clipboard 流程不符合 dashboard 一鍵化操作的設計目標，且 Safari clipboard 限制（V2.7.9 已 patch 過一次）說明這條路本來就不該走。

---

## [2.7.10] — 2026-05-02
### Changed — Heatmap palette: light-gray center + fluorescent extremes

User 不喜歡原本 zinc-900 深底，改成淺灰中心。新 7-stop divergent scale：

| pct | 色 | 對應 |
|-----|----|----|
| -3% | 螢光紅 `#ef4444` (red-500) | 兩端 saturate |
| -2% | 紅 `#fca5a5` (red-300) | 中段 |
| -1% | 紅淺灰 過渡到 zinc-300 | 接近中心 |
|  0% | 淺灰 `#d4d4d8` (zinc-300) | 中心 |
| +1% | 綠淺灰 過渡到 emerald | 接近中心 |
| +2% | 綠 `#86efac` (green-300) | 中段 |
| +3% | 螢光綠 `#10b981` (emerald-500) | 兩端 saturate |

**算法**：兩段 piecewise linear（center → mid 在 0..0.5、mid → peak 在 0.5..1）讓接近 0% 的 cell 真的看起來像「沒動」（淺灰），±1% 才開始顯色，±2% 強烈。

**Text color**：因為大部分 cell 現在是淺底，threshold 從 0.5% 拉到 1.8% 才換成白字；其餘用 zinc-900 深字確保對比。

**Legend gradient** 也同步換成新 5-stop（red-500 / red-300 / zinc-300 / green-300 / emerald-500）。

---

## [2.7.9] — 2026-05-02
### Fixed — 決策日曆「請 LLM 檢討」按鈕在 Safari 出現 `Copy failed: The request is not allowed by the user agent` 錯誤

**根因**：Safari 嚴格要求 `navigator.clipboard.writeText` 必須在 user-gesture 同步流程內呼叫。原本 click handler `await fetch(REVIEW_PROMPT.md) + await fetch(event_index)` 才寫 clipboard → 兩個 await 之後 gesture context 已失效 → Safari 拒絕複製。

**Fix**（兩段式）：
1. **Pre-build bundle on page load**：`loadAndRender()` 結尾 fire-and-forget `prebuildLlmBundle()` 預先 fetch + 拼接，存到 module-level `llmBundleText`
2. **Click handler 改為純 sync**：用 `document.execCommand('copy')` 配 hidden textarea（legacy 但仍 work，gesture-safe）為主要路徑；`navigator.clipboard.writeText` 為 fallback
3. Bundle 尚未載入完成時點按鈕 → toast 提示 + 觸發再 fetch，下次點即可
4. 全失敗 → toast 引導用戶手動下載 event_index_latest.json

### Why
User 在決策日曆按「請 LLM 檢討」收到 Safari 標準錯誤訊息。標準 web API 限制，必須 sync write。

---

## [2.7.8] — 2026-05-02
### Changed — 決策日曆改為「點擊浮動 modal」交互；移除 hover tooltip

**問題**：上版 hover tooltip 即使重做成 sector-style rich card，hover 區大易誤觸；inline detail panel 又在月曆下方 → 點 cell 後要捲到 panel、視覺和被點 cell 失聯。

**新交互**：
1. 點任一 cell → backdrop（rgba(0,0,0,0.55) + blur(4px)）覆蓋 viewport + 浮動 card 視窗置中（720×80vh, scale-in 18ms cubic-bezier）
2. 關閉路徑：backdrop click / Esc / card 右上 × — 三條都保留；不保留「再點同 cell toggle」
3. 點不同 cell → 直接替換 card 內容，不需先關
4. body scroll lock（`body.cal-detail-locked`）防止月曆背景同步捲動
5. Card 內容 `overflow-y: auto`，max 80vh — 處理 5/29 那種 30+ ticker case
6. **完全移除 hover tooltip**：刪除 `#cal-tooltip` element / CSS（~80 行）/ `wireCellTooltip()` JS（~75 行）/ event row 的 `data-cal-tip` attribute
7. event row hover affordance：保留 `cursor: pointer`，cell 整體已有 hover lift 樣式

### Files changed
- `Dashboard/calendar.html`：`#cal-detail` 加上 `.cal-detail-card` 子層 + 新 `#cal-detail-backdrop`；刪 `#cal-tooltip`
- `Dashboard/page-calendar.js`：openDetailPanel/closeDetailPanel 多 backdrop show/hide + body scroll lock；wireControls 加 backdrop click → close；刪 wireCellTooltip + bootstrap call + renderEventLogoGroup 內 data-cal-tip
- `Dashboard/style.css`：`.cal-detail-panel` 改為 fixed inset 0 flex center + `.cal-detail-card` 720×80vh scale-in；新 `.cal-detail-backdrop`；新 `body.cal-detail-locked`；刪整段 `#cal-tooltip` 規則；event row `cursor: pointer`

### Why
User 直接要求：「點單日會展開一個新的 cardview float 在 calendar 上顯示當天所有的內容；取消 tooltip」。這把資訊密度交給點擊互動而非 hover，讓月曆瀏覽更乾淨。

---

## [2.7.7] — 2026-05-02
### Changed — Decision card tooltips upgraded to rich pill-popover style

**Problem**: User 嫌 native `title` tooltip 樣醜（系統預設黑底）+ `cursor-help` 變成 `?` 游標破壞流暢感。

**Fix**: 把 `Dashboard/page-decisions.js` 內所有 pill 的 hover 解釋改成 sector page 同款 rich tooltip：

1. **新 `DECISION_TIPS` map**（zh + en）— 12 個 entry：tp_sl / dual_track / da_filed / contrarian / pos_binary / neg_binary / consensus / fragility_robust / fragility_moderate / fragility_fragile / phase2_fanout / degraded_lanes / burry_override
2. **每個 tip 含 title / desc / scale 三層** — title bold (CJK 800 weight)、desc 段落說明、scale 用 emoji + 縮排列出狀態階梯（如 fragility 的 🟢/🟡/🔴 三檔）
3. **`#decision-tip` 元素** 加到 `decisions.html` `</main>` 後面，CSS 抽到 `style.css`（`#decision-tip` + `.tip-title/.tip-desc/.tip-scale` 全域共用）
4. **`initDecisionTip()`** mouseover/mouseout 偵測 `[data-tip-key]`，定位邏輯（top-flip below if cramped, horizontal clamp）跟 sector page 完全一致
5. **替換**：所有 `title="..."` + `cursor-help` → `data-tip-key="..."`。`cursor-help` 全部移除（不再有 `?` 游標）
6. **TP/SL 區塊** 整塊綁 `data-tip-key="tp_sl"`，hover 兩個值都會顯示同一個 rich tooltip
7. **Dual-Track 標題列** 綁 `data-tip-key="dual_track"`，hover 解釋 AGG/CONS 概念

### Why
User 截圖比較 native title vs rich pill tooltip — native 看起來像 1995 年瀏覽器警告框，rich 版有 title/desc/scale 三層結構、跟 sector page 已存在的 regime/breadth/exposure pill tooltip 風格統一。`cursor-help` 的 `?` 也跟整體 UX 不搭。

---

## [2.7.6] — 2026-05-02
### Fixed — 日曆 cell ticker 字對比 + tooltip 改為 sector page 同款卡片視覺

**問題**：
1. cell 內 ticker 文字（NVDA / NTRS · NVTS · APLD 等）`color: var(--text)` 太淡，淺色模式幾乎看不到
2. 上版 cal-tooltip 雖然用 var(--bg-card) 但只是單調深底 + 平鋪每行，跟 sector / news page 用的 signal-tip-tooltip rich card style 不像

**Fix**：
1. `.cal-cell-decision-tickers` / `.cal-cell-event-tickers` / `.cal-cell-event-text`：font-weight 800、size 10.5px、letter-spacing 0.03em，加 light/dark 主題對比色（light=zinc-900、dark=zinc-200）；high impact 黃、binary 紅
2. `#cal-tooltip` rebuild：
   - title row 含 category icon + 大標 + 右側 count（`💼 財報  · 13 件`）
   - rows 用 grid-cols `auto auto 1fr`（icon / ticker / event title），奇數 row 淡灰底
   - footer line 列 ⚠️ binary risk / 🟡 high impact flag
   - light theme 白底（rgba(255,255,255,0.98)）+ subtle shadow；dark theme 維持 var(--bg-card)
   - Ticker 用 teal 強調色（light=teal-700, dark=teal-300），跟 sector page tooltip ticker 風格一致
   - max-height 360px + scroll 處理 30+ ticker 場景
3. JS `buildTipHtml` 帶 `catMeta` icon dictionary，emit grid layout

### Why
User 截圖比較自家 sector page tooltip（`market_breadth · 33.1 · score 75+ 健康強勢` 那種 rich card 配色）vs 我寫的單調 dark pill — 要求視覺一致 + ticker 文字加深。

---

## [2.7.5] — 2026-05-02
### Changed — 決策日曆 cell tooltip 改為 custom rich tooltip

**問題**：cell 內 future-event row hover 出來的是 native browser `title=` tooltip — 醜（深灰扁長條）、被瀏覽器決定何時顯示、event 全部擠成一行 ` · ` 串接、不能格式化 ticker。

**Fix**：
1. 新增 `#cal-tooltip` 浮動元素（HTML），CSS 用 signal-tip-tooltip 同款（`var(--bg-card)` + `var(--border-hover)` + `backdrop-filter: blur(8px)`）
2. 每 row 用 `data-cal-tip` 帶 JSON payload（icon / ticker / title / impact / is_binary）
3. JS delegated `mousemove` 在 `#cal-grid` 偵測 hover，跟隨鼠標位置（自動避免超出 viewport）
4. Tooltip 內容：標題 `[category] · N`，每事件一行：`icon ticker title`，impact=high 黃字、binary 紅字
5. 移除 row 上的 native `title=` 屬性避免雙重 tooltip

### Why
User 截圖 5/29 cell hover 跑出 native tooltip 把 30+ 個 ticker 擠成一團，要求「跟其他頁面 tooltip 風格一樣，一行一行列出來，icon/name/event」。

---

## [2.7.4] — 2026-05-02
### Fixed — Decision card light-mode contrast + missing tooltips + translations

**Light-mode 對比 (Red Team block)**：
- thesis 內文 / kill conditions / summary text：原本 `text-zinc-300/400` 在白底幾乎不可見 → 改用 `style="color:var(--text-main)"`（自動跟主題切換）+ `text-zinc-700 dark:text-zinc-300`
- Failed warning：`text-amber-400` → `text-amber-600 dark:text-amber-400`
- Counter thesis summary 文字加粗 + 字級 10px → 11px

**新增 hover tooltips**（用 native `title`，與 V5.0 anchor chip 一致）：
- `DA Filed` / 反向論點已提交：解釋 PM Devils Advocate 流程（書面記錄反 thesis 的論述，quality flag）
- `CONTRARIAN` / 逆勢訊號：解釋此分析違反當下 macro regime 體制
- `POS BINARY` / 正向二元事件：48h 內確定 catalyst（財報/法規/併購）
- `NEG BINARY` / 負向二元事件：48h 內確定下行 catalyst
- `×1.15 CONSENSUS`：四個分析師同向 → 模型分數加權
- `FRAGILE / MODERATE / ROBUST`：Tail-risk 三維評估（穩健 / 中等脆弱 / 脆弱）
- `Phase2 fanout` 降級警示：subagent 部分失敗
- `Degraded` lane 計數：列出哪些 lane 沒成
- `BURRY OVERRIDE`：Burry 模型推翻共識 BUY → 倉位減半 + recheck
- `TP / SL` 區塊：止盈止損定義 + R/R 計算公式
- `Dual-Track Entry`：AGG/CONS 雙軌進場意義（搶趨勢 + 等回測，降低 timing 風險）

**翻譯**：
- `FRAGILE` → 「脆弱」、`MODERATE` → 「中等脆弱」、`ROBUST/RESILIENT` → 「穩健」（zh 模式）
- `FLASH` 按鈕（zh）→ 改名為「即時新聞」（更直覺）

### Why
User 看到白天模式 NVDA Red Team 反向論點區塊「文字幾乎隱形」、status pills 縮寫看不懂意思（FRAGILE / 逆勢訊號 / DA Filed 沒解釋）、TP/SL/AGG/CONS 在卡上頻繁出現但對非交易員 user 抽象。一次性補完所有 hover 解釋，並修白天模式對比。

---

## [2.7.3] — 2026-05-02
### Fixed — Cell dashed-line baseline 對齊

**問題**：Layer B（未來事件區）高度依事件數量伸縮，1 row vs 2 row → dashed line 在不同 cell 出現在不同 y 位置（看起來歪歪的）。

**Fix**：
1. `.cal-cell-event-rows { min-height: 50px }` — 固定 2 行 slot 高度
2. 無事件 cell 也 render `<div class="cal-cell-event-rows is-empty">` placeholder（dashed line 顏色降淡）→ 整月所有 cell 的 dashed line 都在同一 y

### Why
User 截圖顯示 5/27 (1 row VZ) vs 5/28 (2 row GM·KO·V + CB) 的 dashed line 高度差很大、整體不齊。

---

## [2.7.2] — 2026-05-02
### Fixed — 決策日曆 cell 排版微調

1. **Layer A 固定高度（22px）**：過去決策列即使空白也保留 slot → 未來 earnings 永遠錨在 cell 底部、不再因為當日無分析而上浮
2. **Cell min-height 96px → 144px**：拉高 ~2 行，雙層 logo + 2 行 event rows 不再互相擠
3. **Cell padding 收窄**：`8px 10px` → `6px 9px 8px`，視覺更緊湊
4. **日曆 main container padding**：`p-6` → `px-6 pt-2 pb-6`、`space-y-5` → `space-y-4`，星期 header 上方空白少 ~20px
5. **Day-of-week header padding**：`8px 0` → `4px 0 6px`

### Why
User 跑了一輪實際看到 5 月 cell 後回報：「過去分析高度不固定 → 未來財報往上擠」+「上面星期 padding 太多」+「cell 可以拉高兩行 (Mac Safari 不會蓋到)」。

---

## [2.7.1] — 2026-05-02
### Changed — Decision card header de-clutter

**Problem**: V5.0 卡 header 大標題行同時擠了 ticker / sector chip / current price，再加 metadata 行的 date / @analysis_price / +5 history，加上右上角 V5.0 bookmark + refresh + 「執行建倉」status pill — 整個視覺爭注意力。

**Changes**:
- **Sector chip 從大標題行移到 metadata 行**：跟 date / @ 分析價 / +N history pill 並排，整體歸為「次要資訊」一條
- **Bookmark V5.0 縮小** + 透明度降到 0.85：`9px → 8px font`、`padding 3/9/4 → 2/7/3`、`right 18px → 8px`、`box-shadow` 也縮小，不再跟綠色 status pill 搶眼
- **Current price 字級** `text-sm → text-base`：頭排只留 ticker + 價格，反而 prominence 拉起來
- **price 跟 drift % 之間** 加 `ml-1` 微距，避免黏太緊

### Why
User 回報「視覺好擁擠」附 NVDA 卡截圖。三軌：(1) 把 sector chip 等 metadata 統一到第二行；(2) bookmark 視覺重要性降一級；(3) 大標題行只剩兩件事（ticker + price），讀起來輕鬆很多。

---

## [2.7.0] — 2026-05-02
### Changed — 決策日曆 (calendar.html) 重新設計：logo 疊合 + 雙層 cell + 底部摘要

**問題**：日曆讀 `event_index_latest.json`（last indexed 2026-04-26 stale 6 天），新分析（5/1、5/2 NVDA/TEAM/VRT/LLY 等）看不到；cell 只顯示 source icon badge 看不到 ticker；下方「依來源彙總」9 stat tile 視覺嘈雜且和「過去決策 + 未來事件」narrative 無關。

**設計**（採用 iOS 通話 widget 風格 logo 疊合 pattern）：

1. **資料源切換（核心修復）**：calendar 改讀 `data.json:recent_analysis[]` 為主，`event_index.decisions[]` 降為 verdict overlay（by `(date, ticker)` key）→ 即時看到當日分析，無 indexer 等待
2. **雙層 cell**（min-height 96px）：
   - Layer A 過去決策：logo stack（圓形 ticker logo 重疊 + verdict ring）+ ticker 文字
   - Layer B 未來事件：每 category 一行（`💼 logo-stack AMD·ET`、`🏛️ FOMC`），同 icon 不重複
3. **Logo + monogram fallback**：FMP CDN deterministic URL `images.financialmodelingprep.com/symbol/<TICKER>.png`，404 onerror → 首兩字母 monogram 圓點（hash 出穩定背景色）
4. **底部 panel** 取代「依來源彙總」：
   - **Past 30 Days** ticker pill cloud（按 decision 顏色：EXECUTE 綠 / STAGED 琥珀 / CANCEL 紅），點 pill 開 report
   - **Coming Up Next 7 Days** 時序 strip（按日期 + category 分組）
   - **Verdict Review by Source**（原 aggregate）降級為 collapsible `<details>`，預設收合
5. **密度切換**：filter bar 加 `[High + Watchlist] / [All earnings]` 切換鈕（壓掉 2351/14d earnings 雜訊），預設 high impact ∪ watchlist；偏好存 localStorage

### Files changed
- `bridge.py`：`extract_audit_history()` + `aggregate_upcoming_events()` 加 `profile_image` 欄位（synthesize FMP CDN URL，零成本）
- `Dashboard/page-calendar.js`：新 loader merge `recent_analysis[]` ∪ `indexDecisions[]`；新 `renderTickerLogo` / `renderLogoStack` / `renderDecisionLogoGroup` / `renderEventLogoGroup` / `renderMonthlySummary` / `renderUpcomingStrip`；`renderDecisionCard` + `renderUpcomingCard` header 加 logo
- `Dashboard/calendar.html`：`#cal-aggregate` 改為 `<details>` 收合；新增 `#cal-monthly-summary` + `#cal-upcoming-strip` + `#cal-density-toggle`
- `Dashboard/style.css`：新 `.cal-ticker-logo` / `.cal-logo-stack` / `.cal-monogram-fallback` / `.cal-cell-decision-row` / `.cal-cell-event-rows` / `.cal-bottom-section` / `.cal-monthly-pill` / `.cal-up-strip-*` / `.cal-aggregate-details`

### Why
User 直接回報：「最近做過的分析都沒在 calendar」+「沒辦法一目瞭然知道哪些公司有分析」+「下方來源匯總 ui 很奇怪」。重設目標：一頁看到「過去做過的公司 + 未來重要 earnings」，保持月曆排版緊湊感。

---

## [2.6.1] — 2026-05-02
### Fixed — V5.0 decision card UX polish

1. **`<details>` 點擊被 history drilldown 攔截**：`page-decisions.js` 的 grid click delegation 把 `summary, details` 加入 ignore selector，反向論點現在點一下就展開（原本要點兩下）
2. **Valuation 區塊文字太淡**：label `text-[8px] text-zinc-500` → `text-[10px] text-zinc-300`；anchor chip text `text-zinc-400` → `text-zinc-100`、bg `bg-zinc-800/60` → `bg-zinc-800`、border `border-zinc-700/50` → `border-zinc-600`；methodology note `zinc-500` → `zinc-400`
3. **Anchor chip 加 hover tooltip**：新增 `ANCHOR_INFO` 常數，6 種估值錨點（DCF-U / DCF-L / Analyst PT / Peer P/E / Owner E. / Forecaster）都有中英解釋，hover chip 即顯示 native tooltip。`cursor-help` 視覺暗示

### Why
昨天上線 V5.0 卡後 user 試用回報三點：細節點不開、label 看不清、chip 縮寫看不懂意思。

---

## [2.6.0] — 2026-05-02
### Added — Version-aware decision card UI (V5.0 / V4.8 / V4.7 / V4.6 / Legacy)

**新功能：決策中心個股卡片改成「按 protocol 版本顯示對應欄位」**

**右上角 bookmark 標籤**：每張卡都有一個從卡頂垂下的小 tab 標 `V5.0` / `V4.8` / `V4.7` / `V4.6` / `ARCHIVE`，配色：
- V5.0 = 綠（emerald，最新）
- V4.8 = 藍 (主流)
- V4.7 = 琥珀 
- V4.6 / V4.5 = 灰
- legacy / 無版本 = 暗灰 ARCHIVE

**版本特定區塊**：
- **V5.0**：`Valuation · Fair Value` 區塊 — 顯示 `weighted_fair_value` / `vs_current_pct` / `confidence` / `verdict_band` (極度低估/低估/合理/高估/極度高估，色條配對) + 6 個 anchor chips (DCF-U/DCF-L/Analyst PT/Peer P/E/Owner E./Forecaster) + methodology note
- **V5.0/V4.8/V4.7**：`Red Team 反向挑戰` 區塊 — verdict pill (NO_VIABLE / MODERATE / STRONG)、counter thesis (collapsed `<details>` 展開)、kill conditions 編號清單 (前 3)
- **V4.8 status pills**（加在 badges 列）：fragility (ROBUST/MODERATE/FRAGILE)、phase2_fanout_mode 非 PARALLEL 時警示、degraded_analysts 數量、burry override + recheck date
- **V4.6 / V4.5 / Legacy**：保留現有最簡卡片 + bookmark 標版本

**bridge.py**：plumb 9 個版本欄位進 `recent_analysis[]`：`protocol_version`, `fragility_label`, `red_team_*` (4), `phase2_fanout_mode`, `degraded_analysts`, `burry_override*`, `ftd_timeline_gate`, `valuation_lane`, `fair_value_summary`

**i18n**：新增 ~25 組 zh + en 字串 (`fv_*`, `rt_*`, `degraded_lanes`, `burry_override`)

### Why
原本 buildCard 對所有版本一視同仁渲染，新版 protocol 加的欄位 (V5.0 fair value、V4.8 red team / degraded lanes) 沒被顯示，等於 protocol 升級了 dashboard 看不出來。改成版本感知後：(1) 升級新欄位自動冒出來；(2) 老資料 graceful degrade，仍可讀；(3) bookmark 一眼看出每筆是哪版分析的，方便對照解讀深度。

---

## [2.5.1] — 2026-05-02
### Added — Momentum filter chips: rich tooltips for V2.1 signals + new presets

**User feedback**: 新加的 chips 沒 tooltip — 點 dual_engine / nh_leaders 等 V2.2 preset 跟 hover V2.1 signal chips (vcp_compressed / rs_leader_3m / dtc_squeeze_candidate ...) 都沒大型解釋 tooltip。

**Root causes**:
1. `Dashboard/page-momentum.js` `SIG_DESC_ZH` / `SIG_DESC_EN` 只有 V2.0 11 個 signal，缺 V2.1 7 個 leader-finder signal description
2. `PRESET_DETAIL_ZH` / `PRESET_DETAIL_EN` 還是 V2.0 9 個舊 preset 內容，沒 V2.2 11 個新 preset entry → 點 dual_engine 等找不到 tooltip data
3. `renderSignalChips()` / `renderWarningChips()` / `renderRequiredWarningChips()` 只有 native `title` attribute（淺顯），沒 `data-sig-tip` / `data-warn-tip` → 不會觸發 mom-pill-tooltip 大 tooltip 機制

**Fixes**:
- 新加 7 個 V2.1 signals 的 SIG_DESC_ZH/EN（含 desc、tiers 分級、hint）：`at_52w_new_high`, `near_52w_high`, `rs_leader_3m`, `vcp_compressed`, `vol_dryup_spike`, `eps_accelerating`, `dtc_squeeze_candidate`
- PRESET_DETAIL_ZH/EN 整個 rewrite：11 個 V2.2 preset 各含 criteria（filter 規則）+ strategy（市場意圖）+ action（如何用）三段式內容
- filter chips 加 `data-sig-tip` / `data-warn-tip` attribute，hover 觸發 mom-pill-tooltip 大型 tooltip（含 tiers 分級表 + hint）

### Why
- chip 上方 hover 才看得到完整解釋（V2.1 新 signals 對 user 是陌生概念，必須有解釋才會用）；舊 chip 也順帶升級到大 tooltip

---

## [2.5.0] — 2026-05-02
### Changed — Heatmap UX polish (top placement, brighter colors, more tickers)

- **Position**：`heatmap-section` 從 verdict matrix 下方移到 `sector.html` 最上面（剛進頁面就是視覺焦點）
- **配色**：從 zinc-500 中性灰改為 zinc-900 深底，配上 emerald-500 / red-500 鮮色 — 解決原本「整體偏灰偏髒」的觀感
- **Ticker 顯示密度大幅提升**：移除原本 `width > 30 && height > 22` 的高 threshold，改為「能塞水平就水平、塞不下但夠高就轉 90°」邏輯。窄高 cell 用垂直 ticker
- **標籤截斷**：sector / industry 標籤照 box 寬度估算可容納字數截斷加 `…`，box 太小直接隱藏 — 修正原本標籤從 box 溢出到背景的鬼字（"ology Set..."、"kers"）
- **i18n 修正**：`heatmap_*` keys 原本誤加在 `i18n.zh.sector_page` 第一個 block，但被同檔後面第二個 sector_page block override，導致 zh 模式 tooltip label 顯示英文 fallback。已搬到正確的 winning block，zh 模式 tooltip 現在正確顯示「現價 / 漲跌 / 市值 / 日內區間 / 成交量」
- **Color legend gradient** 同步更新成新配色（dc2626 → 27272a → 16a34a）

### Why
盤後測試時 user 回報觀感問題：（1）顏色看起來髒、（2）很多 cell 沒 ticker 但其實裝得下、（3）背景出現詭異殘字、（4）tooltip 標籤沒翻成中文、（5）想看熱力圖要先滑過 verdict matrix。一次性修完。

---

## [2.4.1] — 2026-05-02
### Fixed — Momentum preset chip active-state mis-highlight

**Bug**: 點 `dual_engine`（💎 加速雙引擎）後 active highlight 跳回 `nh_leaders`（🚀 新高領航者）。其他 V2.1 preset 也有此 bug。

**Root cause**: `_activePresetKey()` 只比對 V2.0 fields (minScore / stage / label / onlyHotSectors / requiredSignals / excludedWarnings)。新 V2.1 preset 的 V2.0 簽名常相同（都 stage='Stage 2 uptrend' + 0 signals），導致迴圈第一個 hit 永遠是 FEATURED_PRESETS[0] = nh_leaders。實際 filter state 套對，只是 chip 高亮錯位。

**Fix**: `Dashboard/page-momentum.js:_activePresetKey()` 加 V2.1 fields 比對 (`minNhp`, `minRs`, `minRs3mPct`, `minDtc`, `minEpsYoy`, `minRsi`, `maxRsi`, `topSectors`, `requireVcp`, `requireVolDryupSpike`, `requireEpsAccel`)。`_numEq` helper 處理 null/number 對等。

---

## [2.4.0] — 2026-05-02
### Added — Dashboard Momentum UI: V2.1 leader-finder 完整整合 + preset 重設計

**Problem**: V2.1 加了 7 個 leader-finder 指標到 momentum.py / screen.py，CSV 已有 10+ 新欄位，但 Dashboard 整條 stack 沒接 — 進階篩選 0 個新 input、PRESETS chips 仍 V2.0 過嚴 criteria、signals chips 0 個新項、i18n 0 翻譯。

**4-layer integration**:
- **`bridge.py`**：`_build_row()` 加 15 個 V2.1 欄位 + `_load_sector_rs_rank()` 新函式（GICS canonical 名 alias map：`Information Technology` ↔ sector_intel `Technology`）→ 注入每行 `sector_rs_rank`
- **`Dashboard/page-momentum.js`**：`defaultFilter()` 加 9 個 V2.1 fields + `matchesFilter()` 加 9 條 filter chain + `PRESETS` 整個 rewrite（11 個新 preset：5 featured + 6 secondary）+ `FILTER_SIGNALS` 加 7 個 V2.1 signals + `renderFilterPanel()` 8 個新 control binding
- **`Dashboard/momentum.html`**：新 「🚀 Leader Finder (V2.1)」section（5 input + 3 checkbox）
- **`Dashboard/i18n.js`**：signals_map 加 7 個 V2.1 翻譯 + 11 個 preset label/tip + 9 個 filter 控制 key（zh + en 雙語）

**Featured presets (top rail)**:
1. 🚀 新高領航者 (`nh_leaders`) — RS≥75 + NHP≥-5 + Stage 2 + Top 4 sectors
2. 🎯 VCP 突破前夕 (`vcp_setup`) — VCP compressed + dry-up spike
3. 💎 加速雙引擎 (`dual_engine`) — EPS accelerating + RS≥60 + Stage 2
4. 🔥 強勢突破 (`breakout`) — fresh GC + 量能擴張 (保留)
5. ⚡ 軋空潛伏 (`dtc_squeeze`) — DTC≥5 + 站上 50MA

**Secondary (expand)**: 🎢 強勢回檔買點 / 📈 52w 高點池 / 🎯 無過熱精選 / 📊 MACD 突破確認 / ⚡ MACD 動能加速 / 📊 全部

**砍舊 preset**：`leaders` (過嚴 onlyHotSectors), `uptrend` (與 safe_quality 重疊), `pullback` (純 oversold 太鬆), `squeeze` (高短利率太罕見), `macd_reversal` (用太少)

### Verified
- bridge.py + sector_intel mapping：NVDA/WOLF/MU (Tech) → sector_rs_rank=1；GNRC (Industrials) → 4；XOM (Energy) → 3
- 完整 stack 通到 `data.json.momentum_screen.rows[]` (528 rows，全 V2.1 欄位 populated)

### Why
- V2.1 算了一堆指標但 user 在 Dashboard 看不到等於白做
- 取代過嚴 / lagging 的舊 preset（原 leaders 用 score≥75 + onlyHotSectors 過嚴；原 breakout 用 fresh_golden_cross_50_200 lagging 30-60 天；新 preset 用 RS / NHP / VCP 早期信號）

---

## [2.3.0] — 2026-05-02
### Fixed — Heatmap startup behavior on after-hours / weekend

- 加入 `_heatmap_load_from_cache()`：server 重啟時先讀 `Dashboard/heatmap.json` 把 in-memory state warm up，避免 endpoint 回傳空 ticker 名單
- 加入 `_heatmap_has_quote_data()`：判斷是否需要強制 startup quote refresh
- 修正 startup 邏輯：若無快取資料則無視 market hours gate 強制做 1 次 quote refresh（FMP 盤後仍回傳上次收盤價 + 當日 % change，正是 heatmap 該顯示的）
- 之後在 loop 內維持原本邏輯（盤中才 3 分鐘 refresh，盤後保留最後 snapshot）

**Why**：原本盤後 startup 只 build universe（拿到 ticker 但 `market_cap=0`、`price=null`），前端 `market_cap > 0` filter 把全部 box 濾掉導致空白。新邏輯確保任何時候啟動 server 後都立即有可顯示的資料。

---

## [2.2.0] — 2026-05-02
### Added — Live Market Heatmap (S&P 500 + NDX 100)

**新功能：sector.html 加入即時熱力圖**
- Treemap：Sector → subSector → Ticker，大小 = market cap，顏色 = 當日 % change（-3% red ↔ +3% green）
- Universe = S&P 500 ∪ NDX 100（去重 ~517 ticker），用 FMP `/stable/sp500-constituent` + `/stable/nasdaq-constituent`，每 18h 重建一次
- Quote refresh：FMP `/stable/batch-quote?symbols=...`，200 ticker/call、3 calls/refresh、~4 sec 完成
- 後端 polling thread 住在 `dashboard_server.py` 同 process（盤中每 3 分鐘，`./open_dashboard.sh` 啟動 / 結束自動同步）
- 前端 D3 v7 treemap，layout cache 機制：universe 不變只 update 顏色（~10ms），visibility-aware polling 切 tab 自動暫停
- Hover tooltip 立即顯示快取資料（價、漲跌、市值、日內 range、成交量）；停留 **3 秒**後才打 `/api/heatmap/news/<TICKER>` 抓 1-2 則新聞 headline（user-confirmed debounce）
- 兩個新 endpoint：`/api/heatmap/data`（前端 polling）、`/api/heatmap/news/<TICKER>`（lazy news with 30 min server cache）
- API budget：~840 calls/day，FMP Starter 配額 10%

### Changed
- `Dashboard/sector.html`：加 D3 v7 CDN + heatmap section + tooltip element
- `Dashboard/page-sector.js`：+220 行 heatmap render / tooltip / polling 邏輯
- `Dashboard/i18n.js`：加 11 個 heatmap_* 字串（zh + en）
- `dashboard_server.py`：+200 行（state、4 個 helper、polling thread、2 個 endpoint）

### Why
原本 sector.html 只有 Phase 1-5 中期視角（rotation / breadth / sentiment）。加入即時熱力圖補完「當日 intra-day」這層，雙層視角（中期 ↔ 當日）在同一頁。Heatmap 自成 sub-system（獨立 polling、獨立 JSON、獨立 endpoint），不和 bridge.py / data.json pipeline 耦合。

---

## [2.1.0] — 2026-05-02
### Added — Momentum Screener V2.1: 7 leader-finder indicators

**Problem**: 既有 `動能選股` filter criteria 過嚴 (composite ≥70 + Stage 2 精確 match + parabolic_blowoff 排除 above-200 > 50%) 把真正 leader 全砍掉；signals 用 lagging 信號（fresh_golden_cross_50_200 慢 30-60d）+ 過鬆 vol 門檻 (ratio_20d ≥ 1.3)。

**Added 7 new indicators in `skills/momentum-monitor/scripts/momentum.py`**:
1. **NHP** (52w New-High Proximity)：`pct_from_52w_high` + `is_new_high` + `weeks_since_high`。signal `at_52w_new_high` (≤0.5%) / `near_52w_high` (≤5%)
2. **RS vs SPY** (3M / 6M)：`rs_3m_pct` / `rs_6m_pct` / `rs_rating` (0-99)。signal `rs_leader_3m` (rs_3m ≥ +15pp)。Module-level SPY hist cache 1h，避免 N×SPY fetch
3. **VCP Compression** (Minervini)：4w/12w range ratio。signal `vcp_compressed` (< 0.55)
4. **Volume Dry-up Spike**：5D/20D < 0.75 (dry up) AND today/20D > 1.5 (spike)。signal `vol_dryup_spike`
5. **EPS Acceleration** (CAN SLIM C)：opt-in 讀 `earnings-analyst/cache/<T>_*.json`（cache miss 0 cost）→ `latest_q_yoy_pct` + `growth_acceleration`。signal `eps_accelerating`
6. **Days-to-Cover** tier：`none/low/moderate/elevated/high`。signal `dtc_squeeze_candidate` (DTC ≥ 5 + above MA50)
7. **Sector RS pre-filter** (`screen.py`)：從 `sector/sector_logs/*_sector_intel.json` 讀 top-N sectors by composite_score → `--top-sectors N`

**`skills/momentum-monitor/scripts/screen.py` new CLI flags**:
- `--min-nhp N` / `--min-rs N` / `--min-rs-3m-pct N`
- `--require-vcp` / `--require-volume-dryup-spike`
- `--min-eps-yoy N` / `--require-eps-accelerating`
- `--min-dtc N` / `--top-sectors N`

CSV columns + MD table 加 NHP / RS3M / VCP / EPS YoY / DTC 欄位。

**Cache invalidation**: `schema_version: "v2.1"` field bumped；舊 cache 自動 stale 重抓。

**SKILL.md 更新**: filter flags table 加 V2.1 leader-finder section + 3 個範例 (leader-hunter / VCP-setup / squeeze-candidate)

### Why
- 真正 momentum leader (NVDA / VRT / MU) 通常 above_ma200 50-100%，被 `parabolic_blowoff_risk` 過嚴排除
- 「Stage 2 uptrend」字串 match miss 掉 Stage 1→2 過渡期突破前的 setup
- O'Neil RS rating + Minervini VCP + CAN SLIM EPS acceleration 都是經典 leader-finder 指標，repo 既有資料源（yfinance hist + earnings-analyst cache + sector_intel.json）就能 derive，0 額外 cost
- Sector RS pre-filter 避免在弱勢 sector 找動能（強勢 sector 內找強勢股勝率高）

### Test
- SOX 30 → 18 matched with `--min-nhp -10 --min-rs 60`
- SP500 503 → 26 matched with `--top-sectors 4 --min-rs 75`
- WOLF 觸發 `dtc_squeeze_candidate` (DTC 6.5d + MA50)，APA 觸發 `vcp_compressed` (ratio 0.541)

---

## [2.0.1] — 2026-05-02

### Changed
- 將三個第三方 git repo (`finance-skills/`, `fmpstab/`, `Fincept_enhance/`) 統一移入 `reference/`
- 將鬆散文件 (`ARCHITECTURE_DIAGRAM.md`, `bug.md`, `plan_short.md`) 移入 `docs/`
- `CLAUDE.md`：更新 `plan_short.md` 路徑參考 → `docs/plan_short.md`
- `.gitignore`：`Fincept_enhance/` → `reference/`（整體 ignore 第三方 repos）

### Why
根目錄過度雜亂，三個純參考用的 nested git repo 與核心 protocol 檔案混在一起。整理後 core ops 與外部參考資料有清楚分層，不影響任何 protocol/skill 運作。

---

## [2.0.0] — 2026-05-02
### Major — Investment Protocol V5.0 (5-lane + Fair Value Estimation)

**Protocol restructure**:
- **`investment/investment_protocol_v5_0.md`** (NEW)：精簡版主文（867 行 vs V4.8 1278 行 = -32%），砍 V4.7-V4.11 沿革說明、整合 PM MUST/MUST NOT cheatsheet
- **`investment/protocol_appendix_fmp_bundles.md`** (NEW, 155 行)：把 EARNINGS_ANALYST_BUNDLE / PEER_BUNDLE / FMP_SUPP_BUNDLE 三層 bundle 詳細 schema + injection rules 從主文挪出

**新監管者：Valuation Specialist (第 5 lane)**:
- Phase 2 從 4 lane parallel → **5 lane parallel subagent**
- 獨立估值維度：收 6 個 anchor (DCF unlevered/levered, analyst PT, peer PE implied, owner earnings × 15, forecaster blend)
- 加權合理價 vs current price → score -5/+5（折溢價分級）
- 預設 weights：Fund 0.25 / Sent 0.15 / News 0.20 / Tech 0.25 / **Valuation 0.15**
- Phase 2.5 新增 **T5 trigger**：Valuation -3 (extreme overvalued) AND tentative=BUY → 自動 downgrade

**Phase 4.5 — Fair Value Summary (V5.0 NEW)**:
- PM **inline deterministic 計算**（禁 LLM 重評），把 Valuation Specialist 的 6 anchor 用權重 blend
- 缺 anchor 時 weight 重分配（< 3 anchor → confidence=low）
- 輸出 `verdict_band` (extreme_undervalued / undervalued / fairly_valued / overvalued / extreme_overvalued) + `confidence` (high/medium/low)
- Phase 5 MD 報告新增「合理股價估算」section

**FMP API 整合**:
- `executive_compensation` (`/governance-executive-compensation`) → `fmp_supplementary.executive_compensation`：CEO comp YoY > 30% → 治理紅旗
- `comp_benchmark` (`/executive-compensation-benchmark`) → CEO 薪酬 vs 行業中位數
- `employee_history` (`/historical-employee-count`)：5Y CAGR > 15% → 擴張訊號；1Y < -5% → 裁員訊號
- 整合到 Fundamentals + Sentiment + Burry lane rubric

**Schema + Validator 升級**:
- `investment/phase5_export_schema.md`: 加 `valuation_lane` + `fair_value_summary` 必填欄位；version V4.8 → V5.0
- `validate_session_export.py`: 接受 V4.8 (legacy) + V5.0；V5.0 entry 必須含 `fair_value_summary` + `valuation_lane` + `Valuation` weight；驗 verdict_band + confidence enum
- `validate_markdown_export.py`: V5.0 entry 必須在 MD 含「合理股價」section + `weighted_fair_value` 標示

**MD report**:
- Final Visualization Table 加第 5 lane (Valuation) row
- 新「合理股價估算」table（6 anchor + weighted + verdict + confidence）

### Breaking Changes
- `分析 [TICKER]` 觸發從 V4.8 protocol 切到 V5.0 — Phase 2 多 1 個 subagent (~+25% token cost per analysis)
- 新 protocol run 必須產 V5.0 schema entry；舊 V4.8 entries 仍 valid（backward compatible）

### Why
- VRT vs TEAM 分數對比顯示「估值維度」在現有 4 lane 被分散到 Fundamentals 而導致估值警告被稀釋。獨立 Valuation Specialist 給專門 weight + 合理股價 anchor blend 讓 user 一眼看到「這檔現價 vs 合理價」的數字判斷
- V4.8 protocol 1278 行混雜大量歷史變更說明，新 PM session load 時讀不必要 context；V5.0 砍歷史保留 execution 必須資訊

---

## [1.88.1] — 2026-05-02
### Added — Phase 5 markdown score-scale 強制驗證
- **`investment/scripts/validate_markdown_export.py`**: 新檔，post-format gate（rc=0/1）。檢查 Final Score `/3.0`、Burry `/100`，禁 `/5.0` `/10` `/12` drift。可獨立用 `--report <path>` audit。
- **`investment/investment_protocol_v4_8.md`**：
  - Sonnet MD subagent prompt HARD CONSTRAINTS 加 score scale 規範（Final Score `X / 3.0`、4 lane 0-3 裸數字、Burry `/100`、Red Team `N/5`），含正反範例
  - Phase 5 新增 Step 5 markdown validation gate：rc=1 → retry Sonnet 一次，再失敗 PM inline 覆寫 + 重跑 validator
- **驗證結果**：73 份 V4.8 standard 報告 pass；21 份 4/14-4/19 早期 V4.6/V4.7 報告 fail（合理偵測 `/12` Burry bug 等早期 drift）；outlier 全擋（VRT `/10`、MRVL `/5.0`）

### Why
- VRT 報告 freestyle `/10` scale 跟 MRVL `/5.0` scale 是 LLM 在 Sonnet formatter 失敗時手動 fallback 跑掉的結果。Schema 沒強制 → 報告無法跨檔比較分數高低（同 raw consensus 看起來一個 6.72、一個 1.609 完全不同數量級，視覺幻覺）。validator + prompt 雙層強制統一 scale，未來新報告 100% `/3.0`

---

## [1.88.0] — 2026-05-02
### Added — FMP Valuation & Analyst API 深度整合 (Tier 1+2)
- **`skills/earnings-analyst/scripts/fetch.py`**: 新增 6 個 FMP 呼叫 + 5 個 slim helpers
  - `levered_discounted_cash_flow` → `valuation.dcf_levered_intrinsic`（FCFE 模型，補充現有 FCFF DCF）
  - `price_target_news?limit=8` → `valuation.pt_news[]`（機構 PT 調整事件：誰、何時、從X調到Y）
  - `rating_historical?limit=12` → `analyst.rating_history[]` + 計算 `analyst.rating_trend`（improving/stable/declining）
  - `grades_summary` → `analyst.grades_summary`（strongBuy%, total_analysts，比 snapshot 更豐富）
  - `grades_news?limit=10` → `analyst.grades_news[]`（事件級升降評：機構名稱+評級+日期）
  - `_compute_pt_dispersion` 衍生欄位 `valuation.pt_dispersion_pct`（分析師分歧度，>40% 觸發警示）
- **`skills/earnings-analyst/schema.md`**: 新增 V1.74 欄位文件 + Protocol 引用規則說明
- **`investment/investment_protocol_v4_8.md`**：
  - Phase 1 EARNINGS_ANALYST_BUNDLE 加入 `dcf_levered_intrinsic`、`pt_dispersion_pct`、`pt_news`、`analyst` 子區塊
  - Fundamentals lane V1.74 規則：`rating_trend` 取代舊「升評 +0.5」邏輯、`grades_news` 升降評計數信號、`pt_news` 方向信號
  - Burry lane 第 5 規則：levered vs unlevered DCF 差距 > 20% → 資本結構警告 narrative

### Why
- FMP MCP API 審查後，6 個新 endpoint 填補現有「分析師動態」盲點（grades_news 是事件級，grades-historical 只有月分佈）；levered DCF 對高槓桿公司（銀行/REITs/重資本科技）更準確。Tier 3 APIs (custom DCF/market_risk_premium) 需手動參數或用途有限，暫跳過。

---

## [1.87.0] — 2026-05-02
### Added — annual analyst estimates + ESG into bundles
- **`skills/earnings-analyst/scripts/fetch.py`**: `/stable/analyst-estimates?period=annual&limit=3` 加入 EARNINGS_ANALYST_BUNDLE 為 `annual_estimates[]`，含 revenue_avg/low/high + EPS_avg/low/high + ebitda_avg + net_income_avg + num_analysts_revenue/eps。AAPL 確認 3 fiscal year 2028-2030 estimates，eps_avg 從 10.36 → 13.07
- **`skills/_shared/fmp_supplementary.py`**: 新 `_fetch_esg`，從 `/stable/esg-disclosures` 取最新 SEC filing 的 E/S/G/總分，從 `/stable/esg-ratings` 取最新年度 letter rating（B/A/C 等）。AAPL 結果：環保 66.29 / 社會 45.21 / 治理 58.87 / 總 56.79，2025 letter B
- 跳過 COT integration（per-stock protocol 內無相關 instrument，COT 為期貨層級資料；後續若 sector_protocol 需要可獨立加入）
- bundle 體積最終 ~4.4KB（v1.78 起累計）

### Why
- FMP_強化分析.md Section 4.6 + 4.7 + 4.8 P3/P4 工作項。Probe v1.77 已確認三項都免費；annual estimates 補 EARNINGS_ANALYST_BUNDLE 的 forward consensus 缺口（quarterly 為 paid blocker），ESG 補 sentiment / risk lane 的 governance flag

### Out of Scope
- COT report（Section 4.8）— 期貨層級宏觀，不在 invest_protocol 個股分析範圍；若做 sector_protocol macro 章節再加
- Burry rubric 接入 ESG governance score（後續可加，governance score < 50 → SBC 風險加成警示）

---

## [1.86.0] — 2026-05-02
### Added — FMP_SUPP_BUNDLE.congressional_trades + ma_events
- **`skills/_shared/fmp_supplementary.py`**: 新 `_fetch_congressional` (senate-trades + house-trades by symbol，180d window，client-filter) + `_fetch_ma_events` (mergers-acquisitions-latest 200 row 全市場 → client-filter ticker 為 acquirer or target)
- 派生欄位：`congressional_trades.net_signal` ∈ {bullish > 2× sells, bearish > 2× buys, neutral}；`ma_events.events[].role` ∈ {acquirer, target}
- **AAPL 180d**：senate=12, house=18, buys=15 vs sells=15 → neutral；most_recent 2026-04-08。M&A events=0（AAPL 期間無）
- bundle 體積從 ~2.3KB 增至 ~3.8KB

### Why
- v1.85 已 protocol Sentiment+News lane 寫好接收規則；本 bump 把實際資料填進 bundle。Probe v1.77 確認 endpoint 免費。M&A endpoint 無 per-symbol API，只能全市場 + client filter（200 records 約 13 月窗）— mid/small cap 命中率高，mega cap 通常 0 events 為正常

### Out of Scope
- congressional 金額加權（FMP 給的是 range string `"$1,001-$15,000"`，後續可加 `_classify_amount` 已有 helper 待用）
- M&A 全市場 200-record 上限（FMP 沒 from/to 參數）— 罕見的 13 月以外 events 不會抓到，OK

---

## [1.85.0] — 2026-05-02
### Changed — `investment/investment_protocol_v4_8.md` V4.11 — 4 個 lane 接入 FMP_SUPP_BUNDLE 規則
- **Burry lane**（`Phase 2 末段 Burry inline`）：新增 4 條確定性規則
  - Altman Z danger → score -2，grey → -1
  - Piotroski F ≥ 7 → +1（不強制 verdict，保 LLM 收尾權）
  - Owner earnings vs GAAP FCF > 30% 差異 → narrative 標註
  - insider trend accumulating → 允許 insider_pts 升至 1
  - 任何單一規則 ±2 上限；FMP_SUPP_BUNDLE 缺則整條 skip
- **Fundamentals lane**：FMP_SUPP_BUNDLE.quality_scores → score ±1；owner_earnings.qoq_growth < -30% → -0.5
- **Sentiment lane**：FMP_SUPP_BUNDLE.institutional.accumulation_signal ±1；put_call_ratio_change > 0.2 → -0.5；congressional_trades.net_signal ±0.5（v1.86 啟用）
- **News lane**：sec_8k_filings 必看 + 30d window 觸發 ±0.5；FMP_SUPP_BUNDLE.ma_events 強訊號（v1.86 啟用）
- 決策 B 採「只調 score、不強制 verdict」立場 — Piotroski weak 不強制 PASS，避免 LLM 收尾權被剝奪

### Why
- FMP_強化分析.md Section 6.5「Phase 2 Burry Lane 新增規則」+ 4 個 lane 接入 supplementary bundle。前述 v1.78-v1.84 都是資料層；本 bump 把資料 wired 進 protocol prompt，讓 4 個 subagent 真的看得到並按確定性規則計分。決策 B 規定不強制 verdict（避免機械化過頭）

### Out of Scope
- congressional_trades / ma_events 的 fmp_supplementary 實作（v1.86.0 處理；目前 protocol 規則已寫好等資料）

---

## [1.84.0] — 2026-05-02
### Changed — `skills/us-stock-analysis/scripts/analyze.py` bundle-first
- 新增 `_load_bundle(ticker)` 從 `skills/earnings-analyst/cache/<TICKER>_<DATE>.json` 讀最新 bundle；新增 `_derive_from_bundle(bundle)` 把 EARNINGS_ANALYST_BUNDLE TTM ratios + key-metrics 對映到 valuation/balance_sheet/margins_cash/earnings_calendar 的同樣 schema
- `analyze()` 改 bundle-first：bundle 命中時 FMP-sourced TTM canonical 值 override yfinance 同名欄位（pe_ratio / pb_ratio / ev_ebitda / debt_to_equity / margins / fcf_yield / next_earnings_date）；缺值仍 fallback yfinance
- output `data_source` 標 "bundle+yfinance"，`data_quality.bundle_used` + `bundle_meta` 追蹤源頭
- 加 `--no-bundle` flag 維持 skill 獨立 yfinance-only mode 可用
- **AAPL 對比**：bundle path P/E 33.91（FMP TTM canonical）vs yfinance 35.71；EV/EBITDA 25.60 vs 24.98；next_earnings 2026-07-31 vs unknown

### Why
- FMP_強化分析.md Section 1.3 + 5 P2 工作項。Bundle 已存在則重打 yfinance 是浪費 + 數值不一致（yfinance trailing fields lag、FMP TTM 為 canonical）。決策 F：bundle-first 但保 fallback / 獨立可用，無 protocol 流程破壞

### Out of Scope
- yfinance 完全淘汰（growth_yoy / EPS forward / analyst recommendation 仍 yfinance only，bundle 沒這些）

---

## [1.83.0] — 2026-05-02
### Added — News lane 8-K material event filings
- **`skills/market-news-analyst/scripts/fetch.py`**: 新 `_fmp_sec_8k_filings` 用 `/stable/sec-filings-search/symbol?from=...&to=...` 客端 filter formType=8-K（注：`/stable/sec-filings-8k` 端點不支 symbol filter；`sec-filings-search/symbol` 才正確）。返回 30 日內 AAPL 2 件 8-K
- output 新增 `sec_8k_filings` array + `data_quality.fmp_sec_8k_count`。fmp_calls 9 → 9（+1）

### Why
- FMP_強化分析.md Section 3.3 + 5 P2 工作項。`sec-filings-financials` 只回 10-K/Q 財報，重大事件（M&A、CEO 更替、訴訟、重組）走 8-K，原 News lane 漏這層

### Out of Scope
- 8-K item code 解析（事件分類後續可補；現階段 News lane subagent 由 LLM 從 finalLink URL 推測即可）

---

## [1.82.0] — 2026-05-02
### Added — market-news-analyst FMP news/stock + press-releases (PRIMARY headlines source)
- **`skills/market-news-analyst/scripts/fetch.py`**: 新增 `_fmp_news_stock` (`/stable/news/stock?limit=30`) + `_fmp_press_releases` (`/stable/news/press-releases?limit=10`)。fetch() 把這兩個放在 4-way dedup 鏈條最前（FMP 為 PRIMARY, finviz/yfinance/Finnhub fallback）。output `data_quality.headlines_primary_source` 表明來源
- **AAPL 168h test**：FMP=30 + press=2 + finviz=100 + yf=10 + finnhub=25 → dedup 149 headlines；fmp_calls 從 6 → 8
- **`_finviz_analyst_actions:97-104` pre-existing TypeError fix**：`replace(tzinfo=_UTC)` 對 numpy datetime64 失敗，改 `isinstance(d, datetime)` gate；前段 `tz_localize` 嘗試包進 try/except 避免破壞流程

### Why
- FMP_強化分析.md Section 1.2 + 5 P2 工作項。決策 D 採 4 源 dedup（FMP primary + finviz/yf/finnhub fallback）。FMP REST 比 finviz HTML 穩定，新增 press-releases 為高訊號補充（公司官方發布）

### Out of Scope
- FMP `sentiment` 欄位（實測 response 無此欄位，報告 1.2 描述有誤；後續若 FMP 加上再接）
- News lane prompt 規則調整（headline source 的權重等待 v1.84 後 protocol 整合）

---

## [1.81.0] — 2026-05-02
### Added — `skills/theme-detector/scripts/fmp_industry_perf_client.py` (FMP industry perf cross-check)
- 新檔 `fmp_industry_perf_client.py` (~150 行) 從 `/stable/industry-performance-snapshot` 抓最近 5 個營業日的 industry-level `averageChange`，建立 per-industry `perf_1d_pct` + `perf_rolling_pct`（arithmetic sum）+ `_per_day_avg` 序列。每天 cache 6h 至 `skills/theme-detector/cache/fmp_industry/snapshot_<DATE>.json`
- **不**替換 `finviz_performance_client.py`（決策 C：cross-check 不替換）。FMP 為新欄位，scorer 後續可選擇性使用做 sanity check（finviz HTML breakage 偵測 / 雙來源 cross-validate）
- 128 industries × 5 days probe 確認 OK，CLI 可 `python3 fmp_industry_perf_client.py --days-back 5 --head 10` 查 top/bottom

### Why
- FMP_強化分析.md Section 1.1 + 5 P1 工作項。finviz HTML 爬取偶發 breakage，FMP REST 為更穩定的 cross-check 來源。決策 C 採 option-3：FMP 為新欄位、不破壞既有 finviz 流程，theme-detector scorer 與下游報告可選擇性消費

### Out of Scope
- theme-detector `scorer.py` 整合（保持 finviz 為主，FMP 純 cross-check）— 後續 minor bump 或選用時再接入
- `historical-industry-performance` endpoint：實測 200 但 count=0，跳過

---

## [1.80.0] — 2026-05-02
### Added — FMP_SUPP_BUNDLE.institutional (法人 QoQ 籌碼變化)
- **`skills/_shared/fmp_supplementary.py`** `_fetch_institutional`：從 `/stable/institutional-ownership/symbol-positions-summary` 抓最近一季完整 13F filing。從 `q-1` 開始往前 walk back（避免 mid-filing-window partial data，sanity gate: 跳過 investorsHolding 或 ownershipPercent 不到上季 50% 的 partial quarter）
- 派生 `accumulation_signal` ∈ {accumulating > +1%, distributing < -1%, neutral} from `ownershipPercentChange`
- 14 raw fields 攜帶（investors_holding, num_13f_shares, total_invested_usd, new_positions, increased_positions, reduced_positions, put_call_ratio + 對應 last/change 欄位）
- **AAPL probe**：2025 Q4 snapshot — investorsHolding=6288, ownership_percent=64.60%, QoQ change +3.03% → accumulation_signal=accumulating

### Why
- FMP_強化分析.md Section 4.3 P2 工作項。Sentiment lane 缺機構籌碼面 QoQ 訊號（13F summary 已含 last/change 欄位省 2 次抓取）；mid-filing-window 防呆是必要的，否則 Q1 2026 看到 3.32% 會誤判 distributing

### Out of Scope
- Sentiment lane prompt 接入規則（v1.81.0 protocol 改動處理）

---

## [1.79.0] — 2026-05-02
### Added — FMP_SUPP_BUNDLE.insider_summary + sentiment skill bundle-first
- **`skills/_shared/fmp_supplementary.py`**: 新增 `_fetch_insider_summary(ticker)`，從 `/stable/insider-trading/statistics?limit=4` 抓最近 4 季資料；派生 `latest_trend` ∈ {accumulating ≥ 1.0, distributing < 0.5, neutral 0.5-1.0}
- **`skills/market-sentiment-analyzer/scripts/sentiment.py`**: `_fetch_ticker_signals` 改為 bundle-first。先嘗試從 `FMP_SUPP_BUNDLE.insider_summary.quarters` 讀，命中標 `insider_stats_source: "FMP_SUPP_BUNDLE"`；miss 才走原來 FMP direct 抓（標 `"FMP direct"`），維持 skill 獨立可用性
- **AAPL probe 確認**：4 quarters, latest_trend=distributing（acq/dis ratio = 0.18），bundle-first source 正確標示

### Why
- FMP_強化分析.md Section 3.5 + 5「P1 — insider_stats[] 移入 Phase 1 FMP_SUPP_BUNDLE」。原架構 insider 只在 Sentiment lane skill 內部抓，Burry inline lane（Phase 2 末段）讀不到。改放共用 bundle 後 Burry 也可消費；同時 Sentiment skill 不再每次重打 FMP（同 ticker 同日 0 額外 call）
- bundle-first + skill self-fetch fallback 雙路：(a) protocol 整合場景走 bundle 省 call；(b) skill 獨立執行（user 直接跑）仍可用

### Out of Scope
- Burry lane prompt 接入 insider_summary（v1.81.0 burry 規則化處理）

---

## [1.78.0] — 2026-05-02
### Added — `skills/_shared/fmp_supplementary.py` (FMP_SUPP_BUNDLE V1.0) + protocol Phase 1 整合
- **新檔 `skills/_shared/fmp_supplementary.py`** (~180 行): `get_supplementary_bundle(ticker)` 24h cache @ `skills/_shared/fmp_supp_cache/<TICKER>_<DATE>_supp.json`，FMP-only，與 dual_fetch / FinnhubClient 物理隔離
- **首批 sections 填入**: `quality_scores`（Altman Z + Piotroski F + 派生 zone/strength + 7 個 raw 欄位）、`owner_earnings`（latest quarter + qoq_growth + maintenance/growth capex split）。其他 sections（insider_summary / institutional / congressional / ma_events）保留 `{}` 待後續 bump 填
- **`investment/investment_protocol_v4_8.md`**: Phase 1 末段新增「Phase 1 資料層（V4.11 新增）— FMP Supplementary Bundle」節（~30 行）。注入規則：Fundamentals + Burry 收 quality_scores + owner_earnings；Sentiment + News 收對應 sections；Technical 不收
- **AAPL probe 確認**：altmanZScore=11.64 (safe zone), piotroskiScore=9 (strong), ownersEarnings=$28.86B, qoq_growth=-46.7%

### Why
- FMP_強化分析.md Section 6 提案。Burry rubric 缺確定性數值（Altman Z / Piotroski F），目前依賴 LLM 對 debt/asset 比值的定性判斷。將高價值 FMP 欄位集中放 FMP-only bundle，4 lane 共用，避免每個 lane skill 各自重打 FMP（同 ticker 同日 0 額外 call）。物理隔離契約防止 cross-lane anchoring 與 Finnhub/FMP 混淆

### Out of Scope
- Burry rubric 規則化（v1.81.0 處理）
- Sentiment skill bundle-first（v1.79.0 處理）
- 其他 FMP_SUPP sections 填值（後續 bumps）

---

## [1.77.0] — 2026-05-02
### Added — `investment/scripts/fmp_endpoint_probe.py` + `investment/fmp_probe_2026-05-02.json`
- 18 endpoint probe vs AAPL，17/18 PASS（含 ESG / COT / annual analyst estimates 等先前疑慮 paid blocker）。Result file `investment/fmp_probe_<DATE>.json` 後續 v1.78+ bumps 讀取以 gate P3/P4 features
- **PASS endpoints**: financial-scores, owner-earnings, insider-trading/statistics, institutional-ownership/symbol-positions-summary, senate-trades, house-trades, mergers-acquisitions-latest, sec-filings-8k, news/stock, news/press-releases, industry-performance-snapshot, sector-performance-snapshot, historical-chart/1hour, esg-ratings, esg-disclosures, analyst-estimates(annual), commitment-of-traders-analysis
- **FAIL**: historical-industry-performance（200 但 count=0；需特定 industry 名稱 + 日期範圍）→ 後續用 snapshot 取代

### Why
- FMP_強化分析.md Section 4 + 5 列出多項「需驗證是否免費」的 endpoint。實作前先做一輪可重現 probe，免得 v1.78+ bumps 寫進 code 才發現 402 要 rollback。Probe 採只記欄位名稱 / count（不寫 secret）。

### Out of Scope
- historical-industry-performance 的正確 industry 名稱字典（snapshot 已足夠 cross-check 用）
- 任何 endpoint 的下游接入（v1.78+ 處理）

---

## [1.76.0] — 2026-05-02
### Added — earnings-analyst slim_ttm_keymetrics +3 capital efficiency fields
- **`skills/earnings-analyst/scripts/fetch.py:105` slim_ttm_keymetrics**: keep list +3 → `returnOnInvestedCapitalTTM` (ROIC), `returnOnCapitalEmployedTTM` (ROCE), `returnOnTangibleAssetsTTM` (ROTA)。從 `/stable/key-metrics-ttm` 直接拿。AAPL probe 確認三欄位回傳值（ROIC=0.513 / ROCE=0.623 / ROTA=0.350）

### Why
- FMP_強化分析.md Section 3.1 + 4.1 P0 工作項：Burry rubric 缺資本效率指標。`evToEBITTTM` 在 FMP stable 不存在(實測 None)，改採 ROIC + ROCE + ROTA 三個資本回報率欄位。Slim 列加 3 字段，bundle 體積增 ~60 bytes，下游 Fundamentals + Burry lane 立即可用，無 schema 破壞。

### Out of Scope
- evToEBIT 直接欄位（FMP stable 未提供，後續可用 EV / income 推算）
- bundle 消費端 protocol prompt 改動（v1.81.0 Burry 規則化時一併處理）

---

## [1.75.0] — 2026-05-02
### Added — 決策中心 (decisions.html) Invest Cmdbar + 視覺布局重組
- **`Dashboard/decisions.html`**: header 下方新增 `.ea-cmdbar` (terminal-style quick-launch) — 含 prompt `›` + ticker input + 全局 RISK hint + 分析 button + recent chips 條;summary 4 stats 加 `.dc-summary-tile` hover lift + `.dc-summary-num` (32px JetBrains Mono),avg conf/RR 兩格加 blue/violet 4px left-border (彩色一致);整體 grid 從 `space-y-8` 改為 `space-y-6` 為 cmdbar 騰出視覺空間
- **`Dashboard/page-decisions.js`**: 新 `dcRunInvest(ticker)` (POST `/api/protocol-queue` `{name:'invest', ticker, risk_tolerance: UI.riskTolerance}`) + `dcGetRecent/dcSetRecent/dcPushRecent/dcRenderRecent` localStorage 5-slot recent chips (`dc_recent_invest_tickers`) + `dcRefreshRiskHint` 跟 sidebar `#risk-chip` 同步;wire input/Enter/btn/recent-click + window.focus 自動 refresh risk hint;`applyTranslations` 擴充 `decisions.cmdbar_*` keys;`buildCard` 加 `.dc-card-hover` class
- **`Dashboard/style.css`**: `.ea-cmdbar*` 從 earnings.html L64-119 inline 提升為共用 css block (`Dashboard/style.css` 末尾 +90 行,earnings.html inline 保留無風險),decisions/earnings 兩頁共用;新增 `.dc-summary-tile` / `.dc-summary-num` / `.dc-card-hover` 視覺 polish class
- **`Dashboard/i18n.js`**: 新增 `decisions: {cmdbar_run / cmdbar_placeholder / cmdbar_recent_label / cmdbar_risk_hint / cmdbar_queued / cmdbar_duplicate / cmdbar_empty}` zh+en 雙語 7 keys (parity 驗證 OK)
- **`Dashboard/utils.js`**: `VERSION = 'V1.75.0'`

### Why
- 用戶比對 earnings.html 的 cmdbar 體驗(輸入 ticker → 快速跑分析),要求 decisions 同款。決策中心是 invest protocol 的天然 surface(深度委員會分析 → 對應決策追蹤),但既有頁面只能透過個股卡片右上 refresh icon 觸發,沒有 quick-launch entry,要憑空跑新 ticker 必須去 index.html 或 radar.html
- Risk tolerance 已是全局狀態(`UI.riskTolerance` getter 讀 `localStorage.dash_risk_tolerance`,sidebar `#risk-chip` 可切換),cmdbar 只顯示當前值不重複暴露切換 UI,避免 multi-source-of-truth
- `.ea-cmdbar*` 提升為共用 css 是因為 visually identical,複製整段到 decisions inline 會造成兩處 drift;earnings 的 inline 保留作 graceful fallback (即使 style.css load 失敗 earnings 仍能顯示)
- 視覺 polish 控制在 hover/colour 微調,不動 modal / positions table / 卡片內部欄位 layout / bridge.py — 純前端視覺改動,沒有 schema / API 風險

### Out of Scope
- 持倉 modal / 平倉 modal / 持倉 table 結構
- `bridge.py extract_audit_history` 邏輯
- 卡片內部 layout (target/stop/risk-reward 等保持原樣)
- `?ticker=X` deep-link 自動鑽取 (known UX debt)
- Sidebar `#risk-chip` 結構

---

## [1.74.0] — 2026-05-01
### Added — `skills/_shared/company_context.py` 共用 FMP 公司層 metadata cache
- **新檔 `skills/_shared/__init__.py`** + **`skills/_shared/company_context.py`**(~250 行):提供 `SECTOR_UNIVERSE` / `TICKER_TO_SECTOR` / `SECTOR_TOP_5` 三個常數作為 sector 名單單一真相源,以及 `get_profile/get_peers/get_market_cap_history/get_employee_history/get_profiles_bulk` 五個 24h-TTL cache 函式。Cache 路徑 `skills/_shared/cache/<TICKER>_<KIND>.json`。402 paid blocker 回 None 不 abort。

### Changed — sector 三個 fetch script 改 import 共用模組（去重複 ~75 行）
- **`sector/scripts/fetch_earnings_pulse.py`**: 刪本檔 `SECTOR_UNIVERSE` (~24 行) + `TICKER_TO_SECTOR` reverse build (~4 行),改 `from skills._shared.company_context import SECTOR_UNIVERSE, TICKER_TO_SECTOR`
- **`sector/scripts/fetch_smart_money.py`**: 同上 pattern
- **`sector/scripts/fetch_sector_news.py`**: 刪本檔 `SECTOR_TOP_5` (~14 行),改 import shared `SECTOR_TOP_5`(保留 hand-tuned Communication 差異:GOOGL/META/NFLX/DIS/TMUS,**不**用 SECTOR_UNIVERSE[:5])

### Changed — `skills/earnings-analyst/scripts/fetch.py` profile 走共用 cache
- 刪 `_fmp_get("/stable/profile", ...)` 直接呼叫,改 `from skills._shared.company_context import get_profile as _shared_get_profile`,在 `fetch_bundle()` 起頭單行 `profile = _shared_get_profile(ticker) or {}`
- 與 sector scripts 共用 24h cache → 同 ticker 一天內第二次跑(產業掃描 + 分析 [TICKER])0 重複 FMP call

### Changed — `investment/investment_protocol_v4_8.md` Phase 1 新增 PEER_BUNDLE,Fundamentals + Burry lane 加 relative valuation rubric
- **Phase 1 末段**新增 sub-section「Phase 1 資料層（V4.10 新增）— Peer Comparison Bundle」(~50 行):PM MUST 呼叫 `skills/_shared/company_context.get_peers(TICKER)[:5]` + `get_profile(p)`,計算 `peer_pe_median / peer_market_cap_median / peer_beta_median`,注入 PEER_BUNDLE 到 Fundamentals + Burry lane prompt(Sentiment/News/Technical 不得包含,避免 cross-lane anchoring)
- **Fundamentals lane rubric** 新增 PEER_BUNDLE 使用規則:`peRatio` vs `peer_pe_median` 差 > 30% → score ±1,> 50% → ±2;論述格式從「貴」改寫為「P/E 35× vs peer median 22× = +59% premium」
- **Burry inline** 新增 PEER_BUNDLE 額外校驗:EV/EBIT > peer median × 1.5 → 在 `burry_voice` 加 narrative 註記,**禁止**因此調整 burry_score(保 deterministic)
- 失敗策略:`len(peers) < 3` → `PEER_BUNDLE.status = insufficient_peers`,fallback 既有 sector median rubric;**不**中止 protocol

### Changed — `CLAUDE.md` 同步 protocol triggers + 新增 Shared Modules section
- `分析 [TICKER]` row 從 V4.8.1 → V4.10(含 PEER_BUNDLE 註記)
- Ad-hoc 區加 `python3 skills/_shared/company_context.py <TICKER> --peers` smoke test 指令
- 新增 `## Shared Modules` section 說明 `_shared/company_context` 是 mega-cap 名單修改唯一入口

### Why
- Bucket A1 + A2 + A3 來自 `/Users/kavi/.claude/plans/3-fluffy-moonbeam.md` 分析:9 個 FMP company API 方法中只 2 個高 ROI(`stock_peers` + `profile` 共用 cache)。本次一次落地全部 Bucket A,削掉 sector 3 份重複名單,給 protocol lane 加量化 peer comparison
- LLM 判斷增益:Burry / Bear lane 從「貴」變成「P/E 35× vs peer median 22× = +59% premium」,可 reproducible
- API 成本:同 ticker 24h 內第二次呼叫 0 FMP call(原本 earnings-analyst + Phase 1 PEER_BUNDLE 會打兩次 /profile)

---

## [1.73.7] — 2026-05-01
### Fixed — sector Phase 3 Step 1/2/3 缺 explicit bash block,agent guess flag 浪費 retry
- **`sector/phase_1-2-3.md`**: Phase 3 執行順序 block 後新增 Step 1 (`market-sentiment-analyzer/scripts/sentiment.py --json`) / Step 2 (`economic-calendar-fetcher/scripts/get_economic_calendar.py --from --to --format json`) / Step 3 (`earnings-calendar/scripts/fetch_earnings_fmp.py {SCAN_DATE} {SCAN_DATE+7d}` 位置參數) 三個 bash 範例,明示 argparse vs 位置參數差異

### Why
- scan log `sector_20260501_213508.log` 顯示 agent 對 Step 2/3 連續 retry `--json --days 7` → `--from --to --format json` → 讀 `--help` → 才用對的 positional/argparse 介面,每次浪費 ~5-15s + tokens
- Step 3b/3c/3d 早就有 explicit `python3 ...` 範例所以 agent 不 guess,Step 1/2/3 漏掉
- 加範例後 future protocol run 直接 copy-paste 不 hallucinate flag

---

## [1.73.6] — 2026-05-01
### Changed — sector 頁面去重: 移除 Today's Verdict card
- **`Dashboard/sector.html`**: 移除 `#today-verdict-card` 完整 card HTML; 改為單行 hidden stub + tv-* 子元素 hidden stubs (供 `Components.renderTodayVerdict` / page-sector.js `set()` 呼叫不報錯); `Components.renderTodayVerdict` 已有 `if (!card || !market) return` 保護

---

## [1.73.5] — 2026-05-01
### Changed — sector 頁面去重: 移除廣度/三訊號面板
- **`Dashboard/sector.html`**: 移除 Three-Signal Synthesis col (COL 1); 底部格線改 `lg:grid-cols-3` → `lg:grid-cols-2`; binary-alert/warning-flags stubs 縮短為單行
- **`Dashboard/page-sector.js`**: 移除 `three-signal-title` i18n set 呼叫 (`renderThreeSignal` 本身已有 `if (!container) return` 保護)

---

## [1.73.4] — 2026-05-01
### Changed — 反向去重:把 sector 的 8 gauges + binary-adaptive + warning flags 整批搬到 dashboard,sector 留乾淨 sector-only 內容
- **`Dashboard/style.css`**(+170 行):從 sector.html `<style>` block 升級 `.sector-status-row` / `.sector-gauge*` / `.sector-gauge-seg*` / `.sector-gauge-unit` / `.binary-adaptive*` / `.risk-flag-card.risk-flag-sector` 為共用樣式,index 與 sector 共用
- **`Dashboard/index.html`**:
  - 移除 Today's Verdict 卡內 `<div id="three-signal-mini">` 4-bar render 點(stub 隱藏保留以免 script.js 報錯)
  - 加新 `<div id="binary-alert-section">` 用 `.binary-adaptive` 結構(取代舊的 `.binary-alert px-4 py-3` 簡單 list)
  - `<section id="risk-overview">` 改成 `.sector-status-row` 容器,內含 8 個 pill div(`pill-breadth/ftd/marketop/fg/regime/cycle/exposure/vix`)+ warning-flags-row
- **`Dashboard/script.js`**:
  - 加 `_gaugeColor()` / `_gaugeHTML()` / `_gaugeSegmentedHTML()` helper(從 page-sector.js port)
  - 加 `renderSectorStatusStrip(data)`:渲染 4 numeric gauges(Breadth/FTD/Market Top amber/F&G amber-bell)+ 4 categorical/scaled gauges(Regime 4-seg pie / Cycle 4-seg pie / Exposure range gauge / VIX max=40)+ setAttrs for signal-tip engine
  - 重寫 `renderBinaryAlertIndex()` 為 adaptive density(≤2 inline / 3-5 grid / ≥6 collapsible 含 `<details>` toggle)
  - `renderWarningFlagsIndex()` 加 `REDUNDANT_FLAGS_DASH` 過濾(Below_200MA / Critical_Zone / Weakening_Zone — Breadth gauge 已表達)+ `FLAG_TIP_KEY_DASH` 路由到 `#signal-tip-tooltip` 共用引擎(same as sector page V1.72.8)
  - `renderThreeSignalMini` 不再從 main render path 呼叫(stub 函式留著向下相容)
  - `updateRiskOverviewVisibility()` 簡化:gauges 永遠可見,不再 gate
- **`Dashboard/sector.html`**:
  - 移除 `<div class="sector-status-row">` 容器(8 pill divs + warning-flags-row)
  - 移除 `<div id="binary-alert-section">` 完整 markup(只留 stub `<div id="binary-alert-section" class="hidden">`)
  - 移除 inline `<style>` block 中所有 `.sector-status-row` / `.sector-gauge*` / `.sector-chip*` / `.binary-adaptive*` 樣式(~200 行,改用 shared style.css)
- **`Dashboard/page-sector.js`**:
  - 刪除 `_gaugeColor` / `_gaugeHTML` / `_gaugeSegmentedHTML` helpers(~80 行)
  - 刪除 `renderStatusStrip()` 完整 body(~220 行)、`renderBinaryAlert()` 完整 body(~70 行)
  - 兩個 function 改為 no-op stub,既有 `loadSectorData()` 呼叫不報錯
- **`Dashboard/utils.js`**:`V1.73.4`
### Why
- 用戶比對 image 2(sector hero)vs image 3(dashboard DEFENSIVE 卡 4-bar):核心市場指標(Breadth/FTD/Market Top + 廣度等 warning flags)在兩頁看到 2 次 = 認知冗餘
- 反向決策:dashboard 是「市場層級 hero」自然位置,sector 是「sector-specific 深潛」,把所有市場指標集中在 dashboard,sector 頁聚焦 verdict + matrix + 三 col
- Dashboard 4-bar 是舊版視覺(progress bars no ceiling),取代為 8-gauge circular pies — 跟 sector V1.72.x 系列建立的 visual language 統一(verdict-color discipline + amber palette for warning indicators)

---

## [1.73.3] — 2026-05-01
### Changed — Sector status row 去除跟 index.html 重複的 3 個指標
- **`Dashboard/sector.html`**:status row 移除 `<div id="pill-breadth">` / `<div id="pill-ftd">` / `<div id="pill-marketop">` 3 個 wrapper(留下 5 個 sector-specific:F&G / Regime / Cycle / Exposure / VIX + warning-flags-row)
- **`Dashboard/page-sector.js`** `renderStatusStrip()`:
  - 刪除 Breadth / FTD / Market Top 的 `_gaugeHTML` render block(~30 行)
  - `setAttrs` 對應 3 個 pill 的呼叫一併移除
- **`Dashboard/utils.js`**:`V1.73.3`
### Why
- 用戶比對 index.html dashboard DEFENSIVE 卡的 4-bar 區塊(市場廣度 33.1 / FTD 訊號 100 / 頂部風險 31.2 / 綜合曝險 50%)跟 sector.html 前 3 個 circular gauge 完全重複
- 跨頁面看到同一份指標 2 次 = 認知冗餘;dashboard 已是市場層級總覽的合理位置,sector 頁聚焦在 sector-specific context(情緒、體制、週期、本身曝險、波動)
- Sector matrix / Today's Verdict / Three-Signal Synthesis 等下方區塊不動

---

## [1.73.2] — 2026-05-01
### Fixed — Protocol 完成後外面財報卡片不自動刷新
- **`Dashboard/utils.js`** (`pollProtocolStateMonitor`, line ~603): 偵測到 `status === 'done'` 時加 `setTimeout(() => window.DataStore?.refresh(), 3000)`
- **Root cause**: `run_bridge()` 在 protocol 完成後於 background thread 更新 `data.json`，但 DataStore TTL=60s — 前端最多需等 60 秒才能看到新資料。加入 3s 延遲後強制 refresh，讓外面卡片立即反映最新 score/verdict。3s 延遲目的是讓 bridge.py 有時間寫完 data.json。

---

## [1.73.1] — 2026-05-01
### Fixed — earnings-detail empty-state 重跑按鈕「Failed: missing ticker」
- **`Dashboard/page-earnings-detail.js`** (`renderEmptyState` 重跑 button onclick): POST `/api/protocol-queue` 的 payload 從巢狀 `{name:'earnings', params:{ticker}}` 改為扁平 `{name:'earnings', ticker}`
### Why
- `dashboard_server.py:1576` 處理 `/api/protocol-queue` POST 時用 `params = {k:v for k,v in body.items() if k != "name"}`,把所有 top-level key 當作 params。送巢狀 `{params:{ticker:X}}` 會導致 server 收到 `params={"params":{"ticker":X}}`,`params.get("ticker")=None` → `enqueue_protocol` 回 "missing ticker"
- `page-earnings.js` 既有的「重跑」按鈕用扁平 `{name:'earnings', ticker}` 是對的;新頁複製時誤包進巢狀 `params{}`

---

## [1.73.0] — 2026-05-01
### Added — 個股財報 Infographic 風格頁面（取代「看報告」markdown modal）
- **`Dashboard/earnings-detail.html`** (NEW): standalone page `?ticker=X`，公司 hero + 4 主指標 actual vs estimated ✓✗ + 6-segment grid + 地理分部（≥3 regions 才渲）+ 資本回報 card + CEO blockquote + Key Highlights 雙欄 + 重點總結 list + 詳細 markdown `<details>` collapse + empty state
- **`Dashboard/page-earnings-detail.js`** (NEW, ~340 行): page boot + 8 render 函式 (`renderHero/MetricCards/Segments/Geographic/CapitalReturn/Quote/Highlights/Summary`) + lazy markdown collapse + empty-state re-run button (POST `/api/protocol-queue`) + 全程 `UI.escapeHTML`
- **`skills/earnings-analyst/scripts/validate_infographic.py`** (NEW, ~80 行): schema gate（`schema_kind=='infographic'`、`SUMMARY_MIN=2`、`HIGHLIGHT_MIN=3`、`ceo_quote` gated on `transcript_used==true`）

### Changed — earnings-analyst skill 擴充至 6-step protocol
- **`skills/earnings-analyst/scripts/fetch.py`**: 加 5 個 `/stable/` 免費 endpoint（`earnings` / `revenue-product-segmentation` / `revenue-geographic-segmentation` / `dividends` / `earning-call-transcript`）+ 4 個 slim helpers + `_resolve_transcript_q()` 4-tier fiscal-Q resolver（先用 cache 內 fiscalYear+period，再退化 calendar Q，再 Q-1 walk back）→ bundle 新增 `earnings_surprises` / `segments.product_fy` / `segments.geographic_fy` / `dividends_history` / `transcript`
- **`skills/earnings-analyst/SKILL.md`**: 4 steps → **6 steps**，第 4 步 NEW LLM narrate phase（Claude Code in-conversation 讀 cache + ~50K 字 transcript content，Write `<TICKER>_<DATE>.infographic.json`）
- **`skills/earnings-analyst/schema.md`**: 追加「Cache 檔 V1.73 新增欄位」+「Infographic Cache (V1.0)」section（含完整 JSON 範例 + fallback 行為文件化）
- **`dashboard_server.py`**: 新 `/api/earnings-infographic/<TICKER>` route 回傳 merged `{infographic, cache subset, report_path}`；`PROTOCOL_PROMPTS["earnings"]` 4 steps → 6 steps（加 narrate phase prompt 細節）；既有 `/api/earnings-cache/` glob 過濾 `.infographic.json` sibling
- **`bridge.py`**: `extract_earnings_analyses()` glob 排除 `.infographic.json`；每筆加 `has_infographic: bool` 欄位（Dashboard 卡片可選擇性顯示「Infographic ready」標記）
- **`Dashboard/earnings.html` 卡片按鈕**: 「看報告」(markdown modal) 改為「📊 Infographic」(navigate 到 detail page)；markdown 退為 detail page 內 `<details>` lazy load
- **`Dashboard/page-earnings.js`**: action handler `view` → `infographic`，handler 改 `window.location.href = 'earnings-detail.html?ticker=X'`
- **`Dashboard/style.css`**: 新增 `.ed-*` namespace ~180 行（hero / metric grid / segment grid / capital card / quote card / highlights & summary lists / detail collapse / empty state）全用 CSS 變數 light/dark adaptive
- **`Dashboard/i18n.js`**: 追加 `earnings_detail.*` zh/en 雙語 29 個 keys (section labels / metric labels / beat-miss / FY fallback / no dividend / capital labels / loading / error)

### Why
- User 看到 AAPL Q2 風格 infographic（公司 hero + 4 主指標 + segment + 資本回報 + CEO + highlights + summary），希望 `財報 [TICKER]` 改這個樣式
- 實測 5 個 `/stable/` 免費 endpoint 全可用（含 transcript ~48-53K 字）；唯一缺口「季度分部數字」無法從 paid endpoint 取得（402），改由 LLM 從 transcript 抽 CFO 段落獲得（infographic 上的 569.9/309.8 億等數字本來就是這樣來的）
- 新 schema 採 **兩個 cache 檔並存**（`<TICKER>_<DATE>.json` V1.0 不動 + `<TICKER>_<DATE>.infographic.json` V1.0 narrative 層），完全 backward compatible，舊 cache 仍能用，新頁面 404 時走 empty state
- 端到端驗證通過（AAPL Q2 FY26）：`fetch → analyze → validate → narrate(LLM) → render → validate_infographic` 6 phase 全 rc=0；`Dashboard/data.json` `earnings_analyses[ticker=AAPL].has_infographic=true`；其他 3 ticker (GOOGL/MSFT/NVDA) 須手動重跑 `財報 X` 才會生成

### Out of Scope
- Quarterly product/geographic segmentation 付費 endpoint（FMP `period=quarter` 全 402）
- 其他 dashboard 頁面視覺
- 其他 protocol triggers
- LLM provider 替換（沿用 Claude Code in-conversation）
- 多季 history 比較頁（只渲最新一季）

---

## [1.72.9] — 2026-05-01
### Added — Browser tab favicon:AUGUR diamond logo
- **`Dashboard/favicon.svg`**(新檔):24x24 SVG inline gradient(emerald → lime → amber)+ 旋轉鑽石 + 羅盤十字 + 占卜師之眼(同心圓 emerald 瞳 + 琥珀眼神反光)— 跟 sidebar logo mark 視覺一致
- **8 個 HTML 頁面**(`calendar.html` / `decisions.html` / `earnings.html` / `index.html` / `momentum.html` / `news.html` / `radar.html` / `sector.html`):`<title>` 後注入 `<link rel="icon" type="image/svg+xml" href="favicon.svg">`
- **`Dashboard/utils.js`** VERSION:`V1.72.9`
### Why
- 用戶反映 browser tab 顯示預設 "L"(本機 host favicon fallback),要換成 AUGUR diamond logo
- SVG favicon 跨主流瀏覽器(Chrome/Firefox/Safari/Edge)都支援,且向量縮放清晰;沒有 png/ico 多尺寸需求

---

## [1.72.8] — 2026-05-01
### Fixed — Sector warning flags:tooltip 風格統一 + 取消 `?` 游標
- **`Dashboard/utils.js`** SIGNAL_TIPS engine:
  - 新增 3 個 warning flag 條目:`bearish_signal` / `low_historical_percentile` / `divergence`(zh+en 雙語 title + desc + hint,`stages: []`)
  - 新增 `_flagMetricLive(emoji)` factory 產生 LIVE_BUILDERS for 3 個 key,讀 `data-flag-metric` 渲染 single-line 警示 banner(🚨 / 📊 / ↘)
- **`Dashboard/page-sector.js`** `renderStatusStrip()` warning-flags 渲染:
  - 加 `FLAG_TIP_KEY` 映射:`Bearish_Signal_Active → bearish_signal`、`Low_Historical_Percentile → low_historical_percentile`、`Early_Warning_Divergence → divergence`
  - 從 `data-tip-key="warning_flag"`(舊 #pill-tooltip,只在 index.html script.js 有引擎)→ `data-signal-tip="<key>"`(共用 #signal-tip-tooltip engine,所有頁面通用)
  - 加 `risk-flag-sector` class 區隔 sector 頁專屬樣式
- **`Dashboard/sector.html`** `<style>`:加 `.risk-flag-card.risk-flag-sector { cursor: default; }` override 共用 `style.css:1877` 的 `cursor: help` — sector 頁不要 `?` 游標
- **`Dashboard/utils.js`** VERSION:`V1.72.8`
### Why
- 用戶反映 2 個 warning flag 顯示 `?` 游標、且 tooltip 風格跟同頁面其他 8 個 gauge 不一致(實際上 sector 頁根本沒有 #pill-tooltip 引擎,所以舊 tooltip 完全沒出來)
- 直接接到 #signal-tip-tooltip 共用引擎,跨 8 gauge + 3 warning flag 全部 hover tooltip 視覺一致(title + desc + live banner + hint)
- 提供完整指標說明而非只是 metric 數值,讓使用者一眼懂「為何這個 flag 重要」+「該怎麼應對」

---

## [1.72.7] — 2026-05-01
### Changed — Sector warning flags:升級 severity-tier card + 過濾跟 Breadth gauge 重複的 flag
- **`Dashboard/page-sector.js`** `renderStatusStrip()` warning-flags-row 區段重寫:
  - 從舊 `text-yellow-500 px-2 py-1 border` 簡單黃色 pill → **共用 `.risk-flag-card`** 樣式(已在 `style.css:1869` 定義)+ severity 分層 (`sev-critical` 紅 / `sev-warning` 橙 / `sev-caution` 黃)
  - **過濾重複 flag**:`REDUNDANT_FLAGS = {Below_200MA, Critical_Zone, Weakening_Zone}` — 這 3 個 flag 的訊息已被 Breadth circular gauge 完整表達(Below_200MA 是 ma_crossover gap = breadth 4 大 component 之一;Critical_Zone / Weakening_Zone 等於 Breadth score 的 zone label,gauge 顏色已染)
  - 保留獨立 flag:`Bearish_Signal_Active`(critical)、`Low_Historical_Percentile`(warning,顯 percentile %)、`Early_Warning_Divergence`(warning,顯 signal 名)
  - 偏好 `warning_flags_v2`(含 `severity` + `metric_value`)+ 舊 `string[]` schema fallback;按 severity rank 排序
  - 加 `_formatFlagMetric()` helper 對齊 index.html 同名函式行為
  - 加 `data-tip-key="warning_flag"` + `data-flag-*` 屬性,讓既有 `#pill-tooltip` 引擎可顯 severity-tinted tooltip(definition + metric chip + remediation hint)
- **`Dashboard/utils.js`**:`V1.72.7`
### Why
- 用戶反映 sector page 4 個 warning flag 跟 Breadth gauge 視覺/語意可能重複
- 分析後確認 3 個 flag(Below_200MA / Critical_Zone / Weakening_Zone)100% 重複(都是 breadth score 的衍生分量),保留只會稀釋訊號
- 改 risk-flag-card 樣式跟 index.html 對齊,跨頁面 design language 一致;severity 分層讓使用者一眼分辨「critical 必看 / warning 注意 / caution 知道就好」

---

## [1.72.6] — 2026-05-01
### Fixed — Sector status row:曝險上限換行 + 取消 `?` 游標
- **`Dashboard/sector.html`** `<style>`:
  - 加 `.sector-gauge-unit`(`display:block` + 9px JetBrains Mono + 0.55 opacity)讓單位 `%` 換行到第二行 + 字體變小
  - `.sector-gauge` / `.sector-chip` 的 `cursor: help` → `cursor: default`(取消滑鼠變成 `?` 樣)
- **`Dashboard/page-sector.js`** Exposure gauge:`displayStr` 從 `"40-60%"` 改 `"40-60<span class='sector-gauge-unit'>%</span>"`(`<span display:block>` 強制換行)
- **`Dashboard/utils.js`**:`V1.72.6`
### Why
- 「40-60%」5 字符在 64px 圓內擠到邊緣,蓋到 gauge 弧線;拆 2 行(數字大、單位小)更清楚
- `cursor: help` 在 macOS / Windows 都顯示成 `?` 樣式滑鼠 — 用戶覺得干擾視覺,改 default(普通箭頭),tooltip 仍然 hover 觸發

---

## [1.72.5] — 2026-05-01
### Fixed — Sector status row:Market Top tooltip + 移除冗餘 suffix
- **`Dashboard/sector.html`**:`#pill-marketop` 的 `data-signal-tip` 從 `"marketop"` → `"market_top"`(對齊 `utils.js:631` SIGNAL_TIPS engine 註冊的 key — 之前命名不一致 → 完全沒 tooltip 出現)
- **`Dashboard/page-sector.js`** `renderStatusStrip()`:移除 FTD / Market Top / F&G 的 `suffix` 參數(`Yellow (Ea...` zone 字串會 overflow + 重複下方 label;FTD state abbrev 雙引信也冗餘),所有 gauge 中央只顯數值,文字描述交給 hover tooltip
- **`Dashboard/utils.js`**:`V1.72.5`
### Why
- 用戶反映 Market Top hover 沒 tooltip(其他 7 個都有)— root cause 是 data-signal-tip key 字串不對,引擎 silent 跳過
- Suffix 文字被截斷顯「Yellow (Ea」誤解為「?」字符 + 視覺 noise(label 已在最下面),移除後 gauge 視覺更乾淨
- gauge 圓圈本身就是「上限 vs 目前」直覺指示,不需文字補強

---

## [1.72.4] — 2026-05-01
### Fixed — Sector status row:8 個指標**全部圓形化** + 修問號 + 琥珀色 palette
- **問題**:V1.72.2 後 4 個 categorical chip 仍是矩形,看不到圓形;Market Top / F&G 用綠紅切換不符警示性質;部分 pill 顯示「?」(em dash `—` 在 system font fallback 下渲染失敗)
- **`Dashboard/sector.html`** (`<style>` block):
  - 加 `.sector-gauge-seg` / `.sector-gauge-seg.active`(分段 pie,butt linecap + drop-shadow halo on active 段)
  - 加 `.sector-gauge-value-sm` / `-md` 字體大小 modifier(短文字用 sm 11px,中文字用 md 14px)
- **`Dashboard/page-sector.js`**:
  - `_gaugeColor` 加 2 種 polarity:`'amber'`(Market Top:純琥珀 light→mid→dark 三段,#fbbf24/#f59e0b/#d97706)+ `'amber-bell'`(F&G:兩端 #d97706 / 偏 #f59e0b / 中性 #fbbf24)
  - `_gaugeHTML` 加 `max` 參數(支援 VIX 0-40 scale)+ `displaySize` 參數(sm/md/lg);**修 fallback 字符** `—`(U+2014 em dash 字體缺字會渲染成 ?)→ `--`(雙連字符,universal)
  - 新增 `_gaugeSegmentedHTML({segments, activeIndex, label, valueDisplay, color, displaySize})`:N 段 SVG circle 用 `stroke-dasharray` + `stroke-dashoffset` 切割成等分扇形,active 段染 verdict 色 + drop-shadow halo,inactive 灰色
  - **Regime** 改 4-segment pie(BULL / SIDEWAYS / VOLATILE / BEAR;RISK_ON→BULL、RISK_OFF→BEAR 映射),active 段顯該 regime 色
  - **Cycle** 改 4-segment pie(Early / Mid / Late / Recession,色階 emerald → lime → amber → red 表現週期推進)
  - **Exposure** 改 circular gauge — 解析 `"60-75%"` 取 mid → 0-100 環形,中央顯原始 range 字串,固定 violet `#a78bfa`
  - **VIX** 改 circular gauge `max=40`,< 18 emerald / 18-25 amber / >= 25 red,中央 mono 字
  - **Market Top** 改 amber 三段(原 negative polarity)— 不再綠紅切換,純警示色階
  - **F&G** 改 amber-bell 三段 — 中性琥珀,偏向兩端漸深
  - 多欄位 fallback:`mt.composite_score ?? mt.score ?? m.market_top_score`、`m.fear_greed ?? m.fear_greed_index`(防止 schema drift 顯 ?)
- **`Dashboard/utils.js`**:`V1.72.4`
### Why
- 用戶反映 sector 狀態列「Market Top 顯問號 + 旁邊 4 格沒圓形」+「Market Top 應該是琥珀色 / F&G 也是」
- Market Top 是「警示指標」(高 = 高風險)而非「成長指標」,綠紅切換誤導使用者判讀;琥珀色階符合警示語義
- F&G 同屬警示性質(極端兩端都危險),amber bell 配色反映「中性 = 安全」直覺
- 8 個指標全部 circular 達成視覺一致性,離散分類用 segment pie 同樣呈現「上限 vs 目前」結構

---

## [1.72.3] — 2026-05-01
### Added — 動能選股列表可收折
- **`Dashboard/momentum.html`**: 新增 `#table-section` wrapper，包含 `#table-collapse-btn`（含 chevron icon + 「選股結果（N 筆）」標題）和原 `#table-wrap`；toggle bar 採用 glass-card 樣式，頂部 border-radius 連接底部 table
- **`Dashboard/page-momentum.js`**:
  - `toggleMomTable()`: 切換 `#table-wrap` hidden，旋轉 chevron，狀態存入 `localStorage('mom_table_collapsed')`
  - `_syncTableCollapseLabel()`: 從 localStorage 還原 collapsed 狀態（預設展開）
  - `renderTable()` 末尾自動更新標題為「選股結果（N 筆）」
  - `loadMomentumData()` / `showEmptyState()` 改用 `#table-section` 控制顯隱（原 `#table-wrap`）

---

## [1.72.2] — 2026-05-01
### Changed — Sector 頁 UX:圓形 gauge / Binary 自適應 / Today's Verdict 去重
- **`Dashboard/sector.html`** (`<style>` block + body L235-289):
  - 加 `.sector-status-row` / `.sector-gauge` / `.sector-chip` / `.binary-adaptive` 系列 CSS(~150 行 SVG circular-gauge spec + 自適應 binary container)
  - Status pill row 從 7 個 vertical text pill → **4 個 circular gauges(Breadth / FTD / Market Top / F&G,SVG stroke-dasharray + verdict-color drop-shadow)+ 4 個 categorical chips(Regime / Cycle / Exposure / VIX)**
  - Binary alert 區改 `binary-adaptive`,容器內 list 用 `data-density` 控制三段:`compact`(≤2)/ `grid`(3-5)/ `compact + <details> collapsible`(≥6)
  - Today's Verdict 從 3-col 改 **2-col**(takeaways / watch_next),刪除 `tv-actions` 欄位視覺(legacy stub 隱藏保留以免 Components 報錯)— 因為下方 Sector Matrix 已完整列出 HOT/WARM/COLD/AVOID 分組
- **`Dashboard/page-sector.js`**:
  - 新加 `_gaugeColor(score, polarity)`:三 polarity 規則(positive 高=好 / negative 高=差 / bell 兩端=差),配 emerald/amber/red 三色染
  - 新加 `_gaugeHTML({value, label, suffix, color, valueDisplay})` SVG inline gauge renderer(circumference 264,stroke-dasharray 動態繪弧)
  - 新加 `_chipHTML({value, label, color, mono})` categorical chip renderer
  - 重寫 `renderStatusStrip()` 為 4 gauge + 4 chip 結構,**保留 `setAttrs` 邏輯**讓 utils.js 的 signal-tip tooltip 引擎不破
  - 重寫 `renderBinaryAlert()` 含 adaptive 三段邏輯 + `<details>` toggle 動態切換「展開/收合」label
- **`Dashboard/utils.js`**: `const VERSION = 'V1.72.2'`
### Why
- 用戶反映 sector 頁「資訊很多但很雜」+ 部分資料重複(Today's Verdict 的 sector_actions 跟下方 matrix 100% 重疊)+ 7 個指標 pill 看不出「上限 vs 目前」距離
- 圓形 gauge 一眼看到佔比(空圈 vs 滿圈),配 verdict 色三段染色降低視覺認知負擔
- Binary risks 48h 在 0/1/6+ 事件量級下視覺一致性差(空時還佔 ~80px / 多時爆長),adaptive 自動調密度
- 確保不動 sector matrix 內部結構(verdict-group / score-ring / risk_flags / handoff)— 純上方 hero 區重塑

---

## [1.72.2] — 2026-05-01
### Fixed — Journal 統計顯示空白（hasData 邏輯錯誤）+ 新增「更新收益」按鈕
- **Root cause**: `hasData` 硬判 `20d?.n > 0`，但 20d 需等 ~20 個交易日，目前只有 5d 填入（12,342 fills）→ 統計區塊永遠空白
- **`Dashboard/page-momentum.js`**:
  - `renderJournalStats()`: 改為自動偵測最佳 horizon（fills['20d'] > 0 → '20d'，否則 '5d'），`hasData` 判斷基於 bestHorizon
  - by-signal 表格 & 標題（"By signal (5d win rate)"）動態帶入 bestHorizon
  - fills label 顯示三個 horizon 的填充數
  - 空白狀態提示文字說明原因（「fills=0 → 需跑 journal update」）
  - 新增 `updateJournalReturns()` + `_pollJournalUpdate()`：呼叫 `/api/journal-update`，每 4s 輪詢進度，完成後自動重新載入資料
- **`Dashboard/momentum.html`**: journal section 標題列加「更新收益」按鈕（`#journal-update-btn`），點擊後顯示 phase 進度
- **`dashboard_server.py`**: 新增 `run_journal_update()` + `_journal_update_state`；POST `/api/journal-update` 在背景 thread 依序執行 `journal.py update` → `journal.py stats` → `bridge.py`；GET `/api/journal-update/status` 回傳即時 phase
### Note
- 「今日快照」按鈕（stale banner）= 今天還沒拍 screen snapshot → 正確，今天已拍所以隱藏
- 「更新收益」按鈕 = 填入 forward returns 並重算統計，隨時可按

---

## [1.72.1] — 2026-05-01
### Fixed — Journal 統計頁面空白 + 今日未跑提示 Banner
- **Root cause**: `journal.py stats` 從未被自動呼叫 → `stats.json` 不存在 → `bridge.py` 回傳 `journal.stats=null` → momentum 頁 journal 區塊空白（16,043 entries 存在但前端看不到）
- **`dashboard_server.py`** (`_worker()`, ~line 986-998): `--journal` flag 為 true 且 screen.py 成功後，自動呼叫 `journal.py stats`（timeout=120s）；phase label 期間改為「computing journal stats…」
- **`bridge.py`** (`ingest_momentum_screen()`, ~line 1904-1935): binary seek 讀 `journal.jsonl` 末尾 4KB，提取最後一筆 `snap_date`，以 `journal.last_snap_date` 暴露給前端
- **`Dashboard/momentum.html`** (line ~1059): 新增 `#journal-stale-banner`（amber 色 flex row），內含 `#journal-stale-text` + `#journal-run-btn`，預設 hidden
- **`Dashboard/page-momentum.js`** (~line 1939 + 2019-2059): `renderJournalStats()` 開頭呼叫 `renderJournalStaleBanner(journal)`；新增 `renderJournalStaleBanner()` 比對 `last_snap_date` vs 今日 ISO date，stale 時顯示 banner；新增 `runJournalNow()` POST 至 `/api/run-momentum-screen` with `{journal:true}`
- **`Dashboard/style.css`** (`.sidebar-brand` / `.sidebar-brand-text`): 移除 `min-width:0` / `overflow:hidden` / `text-overflow:ellipsis`，改為 `flex-shrink:0`，修正左上角 INTELCOMMAND 末尾「D」被截斷問題
### Why
- 用戶手動跑 `screen.py --journal` 後 CSV 產出但頁面 journal section 仍空白；根因是 stats.json 從未生成
- 需要一個明確 UI 提示告知今日尚未記錄快照，避免靜默遺漏

---

## [1.72.0] — 2026-05-01
### Changed — index.html Risk Overview 重設計（severity-tier warnings + Focus Ticker 提權 + XSS pass）
- **`bridge.py`** (`extract_breadth_from_analyzer`, ~line 249-263 + assignment ~line 1992): 並列輸出新 schema `warning_flags_v2: object[]`（含 `key/severity/metric_value`），舊 `warning_flags: string[]` 保留以維持 `Dashboard/page-sector.js` 相容。每個 flag 帶確切數值（gap_pct / percentile / breadth_score / bearish_score / divergence signal）。
- **`Dashboard/index.html`**:
  - Layer 2a (Binary Alert) + Layer 2b (Warning Flags) 包進共同 `<section id="risk-overview">` 父層，加標題「風險總覽 / Risk Overview」+ count badge；兩個 child 都空才隱藏。
  - `#focus-ticker-card` 從 Momentum 卡子層抽出，提權為 Layer 2 之後的全寬 attention strip（套 `.focus-ticker-promoted`）。
  - Quick Launch input 改用 `.ticker-input-wrap` 加 `lucide:search` prefix icon；button 套 `.cta-launch`（hover glow）。
  - Modal `#preflight-body` + `#report-content` 加 `.modal-scroll-shadow` class（純 CSS sticky pseudo-element fade）。
- **`Dashboard/style.css`** (~80 lines added): 新增 `.risk-overview` / `.risk-overview-title` / `.risk-flag-card`（3 種 severity variants：critical 🔴 / warning 🟠 / caution 🟡，dot + 3px 左邊框 + name + metric chip）+ `#pill-tooltip` 子元素 (`.rft-title-*` / `.rft-metric-row` / `.rft-hint`) + `.modal-scroll-shadow` + `.cta-launch` + `.ticker-input-wrap` + `#focus-ticker-card.focus-ticker-promoted` ::after 漸層。
- **`Dashboard/script.js`**:
  - 重寫 `renderWarningFlagsIndex` (~80 lines)：用 `warning_flags_v2` 渲染，severity tier 自動排序 critical→warning→caution，每張卡掛 `data-tip-key="warning_flag"` + `data-flag-*` 屬性；schema fallback 兼容舊 string[]。
  - 加 `updateRiskOverviewVisibility()` 統籌 `#risk-overview` 父層顯隱 + 翻譯 + count badge。
  - 擴充 `#pill-tooltip` engine (line 1028-1095)：`data-tip-key="warning_flag"` 走專屬路徑，從 `i18n.warnings.tooltips.<flag_key>` 組 severity-tinted title + definition + metric chip + remediation hint。
  - Hero `renderThreeSignalMini` 4 欄各加 10-cell `.score-battery`（複用 Momentum teaser 同款元件 line ~520）。
  - 五個 teaser render 區塊（binary alert / hot sectors / news verdicts / momentum / focus ticker）全面套 `UI.escapeHTML()`，封死 innerHTML XSS [ARCH-14]；focus-ticker enqueue 改用白名單 `[A-Za-z0-9.\-]` 過濾 ticker 防止 inline `onclick` 注入。
- **`Dashboard/i18n.js`** (zh + en 雙語追加): `warnings.severity` (critical/warning/caution) + `warnings.risk_overview_title` + `warnings.tooltips.<flag_key>` (definition + hint，6 個 flag key) + 補 `warnings.flags.Critical_Zone` / `Early_Warning_Divergence` 翻譯。
- **`Dashboard/page-sector.js`** (~line 264): `warning_flags` consumer 加 schema fallback —`(typeof f === 'string') ? f : f?.key`，兼容兩種輸入避免新 schema 上線後 sector page 渲染壞掉。
### Why
- User 觀察 index.html 的 48 小時二元風險條幅下方四個 ⚠ label —「空頭信號啟動 / 廣度跌破 200MA / 歷史低百分位 / 弱化區間」。其中後三項都是同一個廣度指標的不同切面（`ma_crossover.gap` / `historical_percentile` / `composite.zone`），會綁在一起亮（今天 4 個全觸發、breadth_score=33.1）。原本扁平 flex pill 用 regex 區分紅/黃，視覺權重均等，看不出哪個是真正獨立信號（Bearish_Signal 是複合 RSI/價格/MA 維度，與廣度不重疊）。
- 順手解決長期 UX debt：Focus Ticker 藏在 Momentum 卡內易被忽視、modal 長內容無滾動指示、innerHTML XSS 系統性未修。
- Schema 採並列 v1/v2 而非取代，因為 `page-sector.js` 也消費 `market.warning_flags`；不破壞既有頁面的前提下逐步遷移。

---

## [1.42.2] — 2026-04-25
### Changed — Sector protocol token diet (round 2)
- **`sector_protocol_main.md`**: Step 1 / Step 6 sections trimmed of explanatory parentheticals (confidence-gating tutorial, replaces-Step-1 rationale, renderer note for users). Step 6 now points to `step6_overlay.py` script as authoritative; spec table compressed (10 regimes → 8 rows by grouping equal weights).
- **`sector/phase_0.md`**: (already lean — script `--skip-if-fresh 10800` flag adopted in protocol so LLM no longer needs to compare mtime manually).
- **`sector/phase_1-2-3.md`**:
  - Phase 2: replaced manual mtime check with `theme_detector.py --skip-if-fresh 10800` (script self-manages cache); trimmed historical 4-25 observation comment.
  - Phase 3: collapsed step descriptions, dropped budget comparison footnote.
- **`sector/phase_4-5.md`**:
  - Phase 4a Fan-In rules + FRED Macro Lane Prompt: removed parenthetical explanations.
  - Phase 4b consensus_warning: tighter table form.
  - Phase 4c STEP C.6: dropped "比 LLM 心算快 1 分鐘" timing footnote.
  - Phase 4c STEP G.5: removed dotcom/SPAC historical lesson narrative.
  - Phase 4c STEP H today_verdict: dropped Dashboard localization explanation paragraph + concrete chinese examples; kept rules + schema only.
- **`sector/README.md`**: absorbed all moved rationale into 5 new sections (Step 1 vs Step 6 / confidence gating / G.5 historical evidence / Phase 3 budget origin / Phase 4c Step 6 script / theme_detector timeout warning).
### Why
- Each `產業掃描` run loads sector_protocol_main + phase_0 + phase_1-2-3 + phase_4-5 + schema (~1300 lines). Every removed line × every run = real LLM token savings.
- This is the second pass after v1.41.1 (which moved older v1.2/v1.3 narrative). v1.42.0/v1.42.1 added FRED-related explanations that needed similar treatment.
- Net change: protocol files 1464→1423 lines (-3%, -41 lines) but ~70 lines of explanation moved out of LLM hot path → README.

---

## [1.42.1] — 2026-04-25
### Changed — Sector protocol speed pass (3 bottlenecks)
- **Phase 3 web fetch budget**: 4-25 run did 19 WebSearch in a subagent. New rule forces structured tools first (`market-sentiment-analyzer` → `economic-calendar-fetcher` → `earnings-calendar` → reuse `_phase0.fred_snapshot`), then HARD CAP ≤ 5 narrative WebSearch. Provided exact 5-query template + ban list (Russia/Ukraine, FDA PDUFA, bank earnings dates, copper price, AI capex, DOJ Powell — out of sector-level scope). Expected: 3.5min → 1.5min.
- **Phase 2 theme_detector runtime documented**: Added explicit warning that script needs 140-180s; ban `timeout < 240` wrappers (4-25 run wasted 145s on a `timeout 150` kill+retry); ban `--output-dir reports/` + cp dance. Expected: 3.3min → 0.8min.
- **Phase 4c Step 6 multiplier via script** (not LLM hand-computation): `step6_overlay.py` got a real CLI (`--input "Sector:Score,..."`). Phase 4c protocol now MANDATES script execution — paste JSON output directly into `sectors[].step6_fred_multiplier`. Expected: 6.9min → 5.9min.
### Why
- 4-25 sector scan ran 20 min. Phase-by-phase decomposition: Phase 0=63s / Phase 1=52s / Phase 2=3m17s / Phase 3=3m34s (subagent + 19 WebSearch) / Phase 4a=109s (verified parallel via single-message agent calls) / Phase 4b=2m7s / Phase 4c=6m52s (LLM thinking + 27KB JSON write) / Phase 5=18s.
- Phase 4a parallelism confirmed working (4 lanes in `msg_01U6D4...` single message, wall-clock = max lane = 109s vs sequential 372s).
- Estimated combined impact: 20min → ~14-15min after these 3 changes land.

---

## [1.42.0] — 2026-04-25
### Added — FRED 整合（兩 protocol + 強化 Red Team）
- **`sector/scripts/step6_overlay.py`**: deterministic Step 6 multiplier calculator. Base regime × cyclical/defensive matrix (10 regimes) + sector-specific favor/avoid override + regime_confidence gating (`effective = 1.0 + (raw − 1.0) × confidence`). Used by patcher, renderer, backtest harness.
- **`sector/scripts/backtest_step6_overlay.py`**: backtest harness using `fred-macro --asof DATE` + yfinance forward returns. Top-3 vs bottom-3 spread comparison with/without Step 6 multiplier. Currently smoke-test (n≈5 sessions) — becomes statistically valid as logs accumulate (target n ≥ 50).
- **`investment/scripts/validate_phase0.py`**: V4.9 mini-gate. Catches LLM skipping FRED L4 (most common drift mode). Checks `fred_available` / `fred_snapshot.regime_label` / `macro_multiplier_rationale` references FRED.
- **Sector Phase 4a 4th lane (`FRED_Macro_Analyst`)**: parallel subagent reads `_phase0.fred_snapshot` + `SECTOR_ROTATION_GUIDE.md`, proposes favor/avoid per regime.
- **Sector Phase 4c STEP G.5 — Macro/Theme conflict**: when FRED-Avoid sector is HOT-promoted by Theme/Rotation lane → cap WARM, +`macro_theme_divergence` flag, ×0.90 confidence. Anti-1999-dotcom/2021-SPAC rule (theme heat + macro warning = bubble top).
- **Sector Phase 4b DA prompt**: now receives slim FRED snapshot. Conflict rule: yield_curve_inverted / real_rate>2 / credit_stress / Recession-Risk regime / sector ∈ avoid → MUST construct kill_conditions citing **specific FRED values**, not vague "macro 轉差".
- **Investment Phase 2.8 Red Team prompt**: same slim FRED paste + same conflict rule. `counter_evidence_strength` ≥ 4 auto-applied when ≥ 2 FRED conflict signals trip.
- **Sector schema**: `_phase0.fred_snapshot` slim (11 fields) + `sectors[].step6_fred_multiplier` + top-level `step6_overlay` block.
- **Sector renderer**: new `FRED×` column in FINAL VERDICT TABLE (when overlay applied) + new "Step 6 — FRED Regime Overlay" section.
- **Sector validator**: enforces `_phase0.fred_available` + `fred_snapshot` slim shape compliance.
### Changed
- **`skills/fred-macro/scripts/fetch.py`**: composite score now uses **latency-weighted** average. Real-time series (rates / credit / NFCI) weight 1.0; ICSA-mixed employment 0.7; CPI/PCE inflation 0.5. Solves the "Lag Trap" (54-day-stale CPI driving today's regime overlay). composite changed 60→62 in current snapshot (negative inflation_score down-weighted).
- **Sector Step 1 cycle_phase multiplier**: now SKIPPED when `fred_available=true` (Step 6 takes over). Avoids double-counting regime via two LLM heuristics.
- **Sector Phase 0**: new Layer E (FRED MUST-run) parallel to A-D.
### Why
- Audit revealed: across 7 recent investment runs (4-23 to 4-24), **0/7** populated `fred_available` / `fred_snapshot` / `macro_multiplier_rationale` despite V4.9 spec marking these MUST-run. `validate_session_export.py` only checks Phase 5 export, never gates phase0.
- Sector protocol had **zero** FRED integration. Today's run produced HOT for Industrials and WARM for Tech while FRED simultaneously flagged "Overheating regime, avoid Tech/Real Estate/Cons Disc" — major macro-vs-sector divergence with no mechanism to surface it.
- Gemini review caught Lag Trap + double-count + token bloat issues; partially adopted (lagging-tier weighting fix; Step 6 replaces Step 1; slim FRED paste). Disagreed on lane-conflict resolution (Gemini wanted theme to override macro; reversed direction per dotcom/SPAC history).

---

## [1.41.1] — 2026-04-24
### Changed
- **Sector protocol 檔案瘦身**：`sector_protocol_main.md` / `phase_0.md` / `phase_1-2-3.md` / `phase_4-5.md` 全面移除人類向敘述、計算範例、歷史沿革，僅保留 LLM 執行所需的規則與步驟。Protocol 總行數 702 → 641（-9%）。
- **`sector/README.md` 擴充**：吸收移走的內容（Phase 0 三訊號合成計算範例 ×2、Phase 5 機械化背景與動機、文檔分工說明、V1.4 changelog 條目）。檔案分工原則寫入 README 開頭：protocol 檔只給 LLM 看，README 只給人看，避免雙邊漂移。

---

## [1.41.0] — 2026-04-24
### Added
- **`sector/scripts/render_sector_report.py`** — deterministic JSON→Markdown renderer for Phase 5. Reads latest `sector_logs/*_sector_intel.json`, emits `reports/YYYY-MM-DD_sector_report.md` with 7 sections (Verdict table, Macro, Today's Verdict, DA challenges, Divergence, Themes, Handoff). Zero LLM calls.
### Changed
- **Sector protocol V1.4**: Phase 5 is now a mechanical step (JSON write → validator → renderer → user summary). Portfolio Strategist MUST NOT rewrite markdown; if output is wrong, fix the JSON or the renderer.
- `sector/phase_4-5.md` Phase 5 section rewritten with 4 discrete steps and an explicit "≤ 10 行 summary, do not repeat today_verdict" instruction to the model.
- `sector/sector_protocol_main.md` Rule 5 updated to reflect renderer ownership of markdown output.
### Why
- Today's sector scan took 26 min (`sector/scan_logs/sector_20260424_210620.log`). Timeline reconstruction showed 663s of pure LLM generation for Phase 5 markdown + 225s for the final summary — both redundant because `_phase4c.today_verdict` already carries the zh-TW narrative. Rendering from JSON reclaims ~15 min per run.

---

## [1.40.0] — 2026-04-24
### Added
- **Phase 0 L4 FRED integration** in `investment_protocol_v4_8.md` — MUST-run `fred-macro` skill alongside existing 3-layer cache cascade, outputs `fred_snapshot` block with 12 official series (rates / inflation / employment / credit / stress).
- **Macro multiplier blending rules** — LLM baseline from headline-score table + up to 4 FRED-derived caps (yield_curve_inverted 0.75 / credit_stress 0.85 / NFCI>0 0.9 / real_rate>2 0.9) taking min. All-clear bonus × 1.05.
- **`macro_multiplier_rationale` field** (mandatory) documenting the blend decision per run.
- **Dashboard FRED refresh thread** — `dashboard_server.py` adds `fred_refresh_loop` daemon at 15-min cadence (`FRED_REFRESH_SEC=900`), independent of the 5-min bridge loop.
- **`bridge.py` injects `fred_macro` into `data.json`** so Dashboard pages have access without each page re-fetching.
### Changed
- GLOBAL RULES §8 MUST-run list adds `fred-macro` (failure non-blocking; `fred_available=false` continues flow).

---

## [1.39.0] — 2026-04-24
### Added
- **`fred-macro` skill** (`skills/fred-macro/`) — fetches 12 key FRED series via free API (120 req/min, no daily cap). Output: per-series `{value, date, yoy/mom change, percentile_1y, trend_30d}` + aggregate `regime_signals` (yield curve, fed direction, real rate estimate, credit stress).
- Parallel fetch via `ThreadPoolExecutor(6)` → 2-second run for 12 series.
- 15-minute atomic-write cache at `skills/fred-macro/cache/fred_latest.json`.

---

## [1.38.4] — 2026-04-24
### Changed
- Preset tooltip criteria now show translated label (`強多` not `STRONGLY_BULLISH`) and clarify that "Hot Sector" (dynamic from sector scan) differs from the manual "Sector" dropdown (page-momentum.js).

## [1.38.3] — 2026-04-24
### Added
- **Preset-button hover tooltip** — reuses existing pill-tooltip system; new `PRESET_DETAIL_ZH/EN` dicts with 3-section layout (criteria / strategy / action) for all 10 presets.
- `data-preset-tip` attribute + purple accent CSS class.

## [1.38.2] — 2026-04-24
### Added
- **MACD column click popup** mirrors RSI popup structure — header values + zero-axis position bar + 4-quadrant regime map (strongest_bull / weakening_bull / reversal_bull / strongest_bear) + personalised advice.
### Changed
- MACD cell: removed native `title=` tooltip, cell is now clickable.

## [1.38.1] — 2026-04-24
### Added
- MACD column sortable (`data-sort="macd_hist"`).
- **Custom pill hover tooltip** for 11 signals + 7 warnings — replaces ugly native `title=` with a themed card (green for signals, red for warnings), each with description + actionable hint.

## [1.38.0] — 2026-04-23 (commit 4ff7849)
### Added
- Leader button + i18n fixes; MACD column first appearance.
- Earlier (commit f07847c): MACD field wiring in momentum-monitor — `compute_macd()` added to `technical_core.py`; `screen.py` CSV columns + bridge.py + Dashboard row render pipeline.

---

## [1.37.0] — 2026-04-23
### Changed
- **SKILL.md slim** (3 files): `market-news-analyst` 727 → 253 lines, `us-stock-analysis` 297 → 137, `technical-analyst` 241 → 137. Pedagogy / tone / example queries moved to new per-skill `README.md` (3 new files).
- **`technical_core.py` extracted** as shared module between `momentum-monitor` and `technical-analyst` (Option C refactor — no duplication of MA / RSI / volume / stage / crosses primitives).
- **New `us-stock-analysis/scripts/analyze.py`** (fundamentals), **`market-news-analyst/scripts/fetch.py`** (news + analyst actions via finvizfinance), **`technical-analyst/scripts/analyze.py`** (adds MACD + swing-pivot S/R on top of shared core) — addressed "missing script" bug that caused V4.8 Phase 2 subagents to fall back to 30-min WebSearch loops.
### Fixed
- **FMP 429 short-circuit** (3 skills): `theme-detector/etf_scanner.py` + `market-top-detector/fmp_client.py` + `earnings-valuation-forecaster/forecast.py` — first 429 sets flag, subsequent calls skip HTTP. Removes 60-second retry sleep and infinite recursion.
- `theme-detector` daemon-thread timeout for `batch_stock_metrics` (replaces ThreadPoolExecutor which waited on exit).

## [1.36.1] — 2026-04-22 (commit f9caed0)
### Fixed
- **`bug.md` four tickets cleared**: scan banner lost on cross-page nav (sector + news resume covers running/done/error states within 5-min window); `bridge.py` `data.json` writes now atomic (`os.replace`); `scan_confirm` dialog notes preflight phase timing; `AnalyzeQueue` closes BUG-004.
### Added
- `supply-chain-event-analyst` skill.

## [1.36.0] — 2026-04-22
### Added
- **Momentum watchlist feature** — `universes/watchlist.txt` for non-SP500 tickers (APLD / ALAB / RKLB seed), merged automatically when `--universe sp500`; CSV `in_sp500` flag.
- Three REST endpoints on `dashboard_server.py`: `GET/POST/DELETE /api/momentum-watchlist`; atomic file write + `_TICKER_RE` regex validation.
- `momentum.html` ⭐ button + modal with chip list (add/remove with ×) + filter panel "Watchlist 範圍" three-way chip; purple accent row tint for non-SP500.

## [1.35.0] — 2026-04-22
### Fixed
- **Intraday volume pollution** — `momentum.py:_volume_block` used yfinance's partial-day bar directly, triggering `volume_dry_up` on ~500 tickers when scanning during session hours. New `_intraday_state(hist)` three-way classifier (`complete` / `partial` / `too_early`); partial scales `today_v × 390/elapsed_min` to project full-day equivalent; too_early suppresses volume signals entirely.
- `volume_trend` v5/v10 comparison now uses prior-days-only to avoid intraday drift.

## [1.34.x] — 2026-04-21
### Added
- **Protocol-run session exclusion** rule in CLAUDE.md — sector scan / news / invest protocols do NOT trigger VERSION bump or todolist update (root-caused a stuck subagent rc=1 loop).
- CLAUDE.md slim (165 → 81 lines); README expanded (148 → 244 lines) absorbing market classification / protocol evolution / rule rationale.
- Sector banner UI: title/status/latest-log wrapped in `flex-1 min-w-0 overflow-hidden` container; long 401 JSON no longer deforms card.

## [1.32.0] — 2026-04-21
### Changed
- **Dashboard M1+M2+M3 overhaul**: Layer 1 hero = Today's Verdict (stance + headline + 3-col takeaways/sector_actions/watch_next); Layer 2 binary-risk banner + warning_flags strip; Layer 3 three-column teaser (HOT sectors / reviewed news / momentum top 3); cross-module ⭐ intersection signals (`recent_analysis.decision ∈ {BUY,EXECUTE} ∩ momentum top 30`).

## [1.30.0] — 2026-04-19 (commit 02162a9)
### Added
- **Global analyze queue** (`AnalyzeQueue` module) — per-ticker 🔍 button enqueues ticker; background worker thread runs `run_protocol("invest")` serially; dedupe active/pending; decisions page widget shows NOW ANALYZING / QUEUE / RECENT history.
- Market-hours-aware cache freshness (`_market_minutes_between` helper; weekend / post-close cache stays FRESH).
- Deep-links from sector card → momentum page with sector filter pre-applied.

## [1.28.0] — 2026-04-20
### Added
- Today's Verdict structured object on sector page (stance + confidence + key_takeaways + sector_actions + watch_next) — consumed later by index dashboard.

## [1.27.0] — 2026-04-19
### Changed
- Three-page scan log UI unified — inline glass-card with expandable live-log, replaces fixed banner / compact pill. Live stderr tail via new `log_tail` field in status endpoint.

## [1.23.0] — 2026-04-19 (commit 38ce105)
### Added
- Momentum screener Dashboard first ship — covers v1.13 → v1.23 (new `momentum-monitor` skill, full momentum page, filter panel with 6 presets, score battery UI, stage/rsi/volume popups, GICS sector dimension, intraday volume projection).

## [1.22.x] — 2026-04-18
### Added
- RSI column clickable popup (blood bar + zone legend + personalised advice).
- Stage classification popup (MA stack visualization + rule checklist + transition conditions).

## [1.21.0] — 2026-04-18
### Fixed
- **Volume ratio intraday projection** — clickable popup shows "projected full-day volume" when ET 9:30-16:00; `_avg_prev(n)` excludes today to avoid self-dilution.

## [1.20.0] — 2026-04-18
### Added
- **GICS sector dimension** in momentum selector — `sp500_sectors.json` from Wikipedia S&P 500 list (503 tickers × 11 sectors); sector subscript on ticker cell + filter dropdown.

## [1.18.x] — 2026-04-18
### Fixed
- JSON.parse NaN bug — `momentum.py` / `bridge.py` sanitize NaN → None; `json.dump(allow_nan=False)`.
- Scan real-time progress via `Popen` + background reader thread parsing `screen.py` stderr.

## [1.17.0] — 2026-04-18
### Changed
- Momentum to **client-side real-time filtering** (previously server-side `min_score=60`) — backend returns all 503 rows, client filters live. Enables instant slider changes without rescan.

## [1.15.0–1.16.0] — 2026-04-17
### Added
- RSI-14 (Wilder smoothing) in `momentum.py`.
- 10-cell battery UI for score display.
- `ThreadingHTTPServer` to prevent scan blocking other requests.

## [1.13.0] — 2026-04-17 (commit 38ce105 begins)
### Added
- `momentum-monitor` skill (per-ticker volume / MA / short interest / composite score 0-100) + CLI + cache.

---

## [1.12.0] — 2026-04-16
### Added
- `feat: V4.8 protocol` (commit b955a5c) — **Parallel Blind Analyst Subagents** (4 Phase 2 analysts now run in single-message parallel Agent tool calls with `subagent_isolated:true` sentinel).
- Per-card refresh on decisions page.
- `market-sentiment-analyzer` skill file-based cache (15-min TTL).

## [1.11.0] — 2026-04-16
### Added
- Pre-market preflight cache health modal (`/api/preflight`, `/api/preflight/run-free`) — one-click refresh for stale breadth/FTD/market-top caches.
- Reverse-call from Dashboard to Claude CLI (`/api/run-protocol` covering invest/flash/digest/review).

## [1.10.0] — 2026-04-16 (commit 0f3bcd2)
### Added
- **News review workflow** — REVIEW mode + Dashboard `reviewed` / `pending` filter pills + submit-for-review button.
- FLASH/DIGEST buttons on Dashboard news page trigger reverse-call.

## [1.9.0] — 2026-04-16 (commit 62fdabe)
### Added
- News V2 protocol — RSS two-stage funnel + 4-agent roundtable (Bull/Bear/Sector/Macro).
- 4 missing skills added; protocol MUST-run rules; calibration doc.

## [1.5.0–1.8.0] — 2026-04-13 (commits d34f2b1, b03f806, 90e6034, 54bc9a0)
### Added
- `market-breadth-analyzer` skill (C-BREADTH) with TraderMonty CSV data source — 6-component 0-100 composite.
- `ftd-detector` skill (C-FTD) via yfinance adapter — dual-index tracking (S&P 500 + NASDAQ), rally-attempt state machine.
- `market-top-detector` skill (C-TOP) — O'Neil Distribution Days + Minervini leadership deterioration + Monty defensive rotation.
- Hover tooltip explanations on `breadth.html` indicator cells.

## [1.3.0–1.4.0] — 2026-04-12 (commits 304da30, 062bdee, dd61383)
### Added
- 4 risk/sentiment skills integrated into protocols (V4.5 / V1.1):
  `short-contrarian-analyst` (Burry) / `market-sentiment-analyzer` / `portfolio-risk-manager` (vol-adjusted caps) / `tail-risk-analyzer`.
- Historical, news, sector pages added to Dashboard.
### Fixed
- Safari compatibility; UI icon issues; dash logic bugs.

## [1.2.0] — 2026-04-11 (commit 35d23f6)
### Changed
- Project structure reorganization; protocol upgrades (Sector V1.2 multi-file + Investment V4.4).

## [1.1.0] — 2026-04-11
### Added
- `investment/` / `sector/` / `news/` protocol directories with per-module README.

## [1.0.0] — 2026-04-09 (commit 98cce74)
### Added
- **Initial commit**: AI投資委員會 multi-protocol investment system.
  - `investment_protocol_v4_3`: individual stock analysis with 8-agent debate.
  - `sector_protocol_v1`: pre-market sector intelligence with bull/bear debate.
  - `news_protocol_v1`: real-time news analysis with cache patching.
  - Three-layer Phase 0 cache: sector_intel → phase0 → web search.
  - Skills: `us-stock-analysis`, `market-news-analyst`, `technical-analyst`.

---

## Evolution highlights

For quick orientation of future Claude sessions:

- **Weeks 1-2** (v1.0 → v1.12): foundational skills + protocols; sector/news/invest three-way split; Dashboard first pages.
- **Week 3** (v1.13 → v1.30): momentum-monitor ecosystem (screener + journal + live Dashboard page with every interaction clickable); analyze queue; watchlist.
- **Week 4** (v1.31 → v1.38): UX polish phase — banner layout, MACD/RSI/Stage popups, preset strategy tooltips, custom tooltip system; bug.md triage.
- **Week 5** (v1.39 → v1.40): macro data enrichment — FRED API integration for authoritative rates/inflation/employment/credit feed into Phase 0 multiplier calibration.

Protocol evolution: investment V4.3 → V4.8 (parallel blind analysts); sector V1 → V1.3 (multi-file with Phase 0-5 split + validator gate); news V1 → V2.1 (RSS two-stage + 4-agent roundtable + per-agent batch subagent).

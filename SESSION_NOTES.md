# INTEL COMMAND — Session Notes & System State

> **Last Updated**: 2026-04-25
> **Role**: This file serves as the "Short-term Memory" and "Handoff Cache" for AI Agents. It contains market regime states, token optimization logs, and data integrity notes. **Task backlog has been moved to TODO.md; full version history to CHANGELOG.md.**



## 🟡 Previous Session Note (v1.42.2) — Sector Protocol 文字瘦身 R2

第二輪 trim — v1.42.0/v1.42.1 加進去的 FRED 解說文字現在搬到 README。原則：
- protocol 檔只留 LLM 執行所需（規則 / schema / 命令）
- 「為什麼這樣設計」「歷史教訓」「比舊版快多少」全部 → README 設計理由區

砍掉：Step 1 vs Step 6 解釋、confidence gating 教學、Renderer 給 user 的提示、
1999 dotcom/2021 SPAC 歷史教訓、Phase 3 「vs 舊流程 200 秒」對比、STEP C.6 timing 對比、
today_verdict bilingual 解說 + 中文範例、4-25 run 觀察記錄。

Phase 2 同時併入 user 的優化：theme_detector 改用 `--skip-if-fresh 10800` flag，script 自管 cache，LLM 不需要再 stat mtime。

統計：protocol 檔 1464 → 1423 行（-3%）；README 補上 5 個新 rationale 區塊。每次 sector 掃描 LLM 載入量都減一點。

## 🟢 Session Note (v1.42.1) — Sector Protocol 提速

4-25 跑 sector scan 仍 20 分鐘（v1.42.0 砍了 5 分但還可降）。Phase-by-phase 拆解後三個瓶頸都改掉：

- **Phase 3** 19 個 WebSearch 砍到 ≤ 5。強制走 `market-sentiment-analyzer` + `economic-calendar-fetcher` + `~/.claude/skills/earnings-calendar` + reuse `_phase0.fred_snapshot`。WebSearch 限 5 個 narrative，給了具體 query 範本與 ban list（Russia/Ukraine、FDA PDUFA、bank earnings dates、copper price、AI capex、DOJ Powell — 不是 sector-level 該管的）。
- **Phase 2** theme_detector 跑兩次浪費 145s（第一次 `timeout 150` 殺掉 retry）。Phase_1-2-3.md 加 runtime 提示：正常 140-180s，禁止 `timeout < 240` 包裝。
- **Phase 4c** Step 6 LLM 心算 11 sectors 改用 `step6_overlay.py --input` CLI，純 Python <1s 出 JSON 直接 paste。

**Phase 4a 4-lane 平行確認 OK**：4 個 Agent 都在 `msg_01U6D4...` 同一訊息，wall-clock = max lane = 109s（vs 序列 372s）。

預計 4-26 跑 sector scan：20 分 → ~14-15 分。

## 🟢 Session Note (v1.42.0) — FRED 整合

8 個改動全做完（P0-P3）。背景：審計發現 v4.9 spec 寫 fred-macro MUST-run 但 7/7 近期 invest 跑都跳過。Sector 完全沒接 FRED。

**完成**：
- **fred-macro**: composite score 改 latency-weighted（real-time tier 1.0 / employment 0.7 / inflation 0.5），解決 Lag Trap。composite 60→62。
- **Sector Phase 0**: 新增 Layer E (FRED MUST-run)。schema `_phase0.fred_snapshot` slim 11 欄位。validator 強制檢查。
- **Sector Phase 4a**: 新增第 4 lane `FRED_Macro_Analyst`，讀 `SECTOR_ROTATION_GUIDE`。
- **Sector Phase 4b DA + Investment Phase 2.8 Red Team**: 兩個 prompt 都加 FRED slim paste + 衝突規則（必須引用具體數值，不可寫 vague「macro 轉差」）。
- **Sector Phase 4c STEP G.5**: Macro/Theme 衝突 → cap WARM + `macro_theme_divergence` flag。Anti-1999/2021 泡沫頂規則。
- **Sector Step 6**: FRED regime overlay 取代 Step 1（不疊加）+ regime_confidence gating。`step6_fred_multiplier` 寫入每 sector，`step6_overlay` block 寫頂層。renderer 新增 FRED× 欄位。
- **`step6_overlay.py`**: deterministic Python 計算器（10 regimes × cyclical/defensive matrix + favor/avoid override + confidence gating）。
- **`backtest_step6_overlay.py`**: 用 `fred-macro --asof` + yfinance 回測 top-3 vs bottom-3 spread。目前 n=5 樣本太小（每個 sector 才 12 天 history），smoke test 跑通；data 累積到 50+ 才有統計意義。
- **`investment/scripts/validate_phase0.py`**: V4.9 mini-gate 抓 LLM 漏填 fred_available / fred_snapshot / rationale。

**今日 sector_intel.json** 已 backfill FRED slim snapshot + Step 6 multipliers。`reports/2026-04-24_sector_report.md` 已重 render 含 FRED× 欄位 + Step 6 區塊。`validate_sector_intel.py` rc=0。

**下次跑投資 protocol 預期變化**：
1. LLM 必須跑 fred-macro fetch（會被 validate_phase0.py 抓）
2. Red Team subagent 收 FRED slim paste，產出 kill_conditions 會引用具體 FRED 數值
3. macro_multiplier_rationale 必須提到 FRED / yield / real_rate / nfci / credit / regime 之一

**下次跑產業掃描預期變化**：
1. Phase 0 多 Layer E（fred-macro fetch + slim snapshot 寫入 _phase0）
2. Phase 4a 多第 4 lane（FRED_Macro_Analyst subagent）
3. Phase 4b DA 收 FRED snapshot，可量化反論
4. Phase 4c 仲裁可能觸發 STEP G.5（FRED-avoid sector 被 theme 推 HOT → cap WARM）
5. Phase 5 evaluator 跑前算 step6_multiplier 寫入每 sector
6. 報告含 FRED× 欄位 + Step 6 overlay 區塊

## 🟢 Session Note (v1.41.1)
- **Protocol 檔案瘦身**：`sector_protocol_main.md` / `phase_0.md` / `phase_1-2-3.md` / `phase_4-5.md` 全部清掉人類向敘述、計算範例、歷史沿革，只留 LLM 執行所需。702 → 641 行。
- **README 吸收**：被移走的內容（Phase 0 計算範例 ×2、Phase 5 機械化動機、V1.4 changelog）全部進 `sector/README.md`。
- **新原則寫入 README**：protocol 檔只給 LLM 看（緊湊、機械、可驗證），README 只給人看（背景、設計理由、debug）。Protocol 是 source of truth，README 註明 pointer 即可，避免雙邊漂移。

## 🟢 Session Note (v1.41.0)
- **(1) 產業掃描 Phase 5 機械化**：新增 `sector/scripts/render_sector_report.py`，從 `_sector_intel.json` 直接渲染 markdown 報告（7 段：Verdict / Macro / Today's Verdict / DA Challenges / Divergence / Themes / Handoff）。
- **(2) Protocol V1.4**：`sector/phase_4-5.md` Phase 5 重寫為 4 步機械流程（寫 JSON → validator → renderer → ≤10 行 summary）。PS **禁止**用 Write 手寫 markdown；`_phase4c.today_verdict` 所有欄位為必填（renderer 的文字來源）。
- **(3) 動機**：今日 `產業掃描` 跑 26 分鐘（`sector_20260424_210620.log`）。時間軸拆解顯示 Phase 5 markdown 生成 663s + 最終 summary 225s 共 15 分鐘純模型輸出，內容與 `today_verdict` 完全重疊 → 全部改機械渲染。
- **(4) 今日 markdown 已用新 renderer 回寫**：`reports/2026-04-24_sector_report.md` 現為 102 行 / 5.2KB，比原 71 行版本多出 Macro Context / Sector Divergence Watch / 完整 Actionable Themes 區塊。

## 🟢 Session Note (v1.40.0)
- **(6) 宏觀資料官方化**：新增 `fred-macro` skill 抓 12 條 FRED 官方 series（利率 / 通膨 / 就業 / 信用 / 壓力）；投資 protocol Phase 0 新 L4 layer 永遠跑（MUST-run）；`fred_snapshot` 輸入 multiplier 雙向 blending（LLM baseline × FRED caps 取 min，全 clear 時 × 1.05 bonus）。
- **(5) Dashboard 自動刷新**：`dashboard_server.py` 新 `fred_refresh_loop` daemon 每 15 min 重抓 cache；`bridge.py` 注入 `data.fred_macro` 到前端 data.json。
- **(4) MACD UI 完整**：點擊 MACD 欄跳 RSI 同風格 click popup — zero-axis bar + 4-regime quadrant map (strongest_bull / weakening_bull / reversal_bull / strongest_bear) + personalised advice。Preset buttons 加 hover tooltip（criteria / strategy / action 三段式，紫色 accent）。Signal/warning pills 也改自訂 hover tooltip，取代原生 title=。
- **(3) 前次累積**：跨頁導航 scan banner `Ended_at` 時間戳（5 分鐘效期）；AnalyzeQueue 解決重複分析；`i18n.js` `scan_confirm` preflight 時間預告。

---

## 🔵 Momentum Context (Multi-Universe)
**動能選股 Universe 整合機制**。
- **(1) 市場狀態**：目前預設掃描 `all` (SP500 + Nasdaq 100 + Watchlist)，總數 527 檔。
- **(5) 數據結構**：CSV/JSON 新增 `in_nasdaq100` 布林欄位。
- **(4) UI 連動**：Dashboard 預設顯示 Top 200，但透過 `isWatchlist` 邏輯，自選股不受 Universe 篩選器影響，始終顯示。

---

> **📜 完整版本歷史已移至 [`CHANGELOG.md`](./CHANGELOG.md)** — 自 v1.0.0（2026-04-09 初始）至目前全部 entries，含 git commit 引用與 evolution highlights。

---

## 📋 Bridge 資料流對照（System Manifest）

| Protocol | 輸出 Log | Bridge 讀取欄位 | Dashboard 顯示 |
|---|---|---|---|
| `investment_v4_8` | `invest_logs/history.json` | `final_decision`, `score`, `macro_alignment`, `key_risks` | decisions 頁全部 |
| `sector_v1.3` | `sector_logs/*_intel.json` | `market_regime`, `_phase0` (breadth/FTD/MT), `today_verdict` | index + sector |
| `news_v2.1` | `news_logs/*_digest.json` | `verdicts[]`, `trump_signals`, `catalysts` | news 頁 + sidebar |
| `breadth_analyzer`| `breadth_cache/*.json` | 6 組件 breadth + trend | index 廣度 gauge |
| `positions.json`  | — | lots → avg_cost / live_position | decisions 持倉 |

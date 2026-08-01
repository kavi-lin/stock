# Session Notes 歸檔 v1.40.0 → v1.46.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v1.46.0) — short-term-target skill v0.1（plan_short Step 1）

承接從 backtest 反思 + Gemini/ChatGPT 雙 review 整合的 plan_short.md，落地 Step 1：建立 `skills/short-term-target/` skill 提供 1d/5d/15d 短期目標價預測（"Tactical Opportunity Radar" framework）。

**架構決策（從 plan_short 帶入）**：
- 每 horizon 獨立權重（1d news-heavy、5d momentum-heavy、15d sector-persistence-heavy），不共用 α/β/γ
- Hard clamp（1d ±5%、5d ±15%、15d ±30%）防冷啟動爆走，clamped 預測 confidence 自動 -0.15
- Confidence breakdown 7 項貢獻全透明，sum 等於 final
- Benchmark-relative output（ETF realized + implied_alpha），預設 SPY
- Refuses to fabricate：source 過舊 → `status: insufficient_data` 含 missing/would_need
- Trading meta（stop = 1.5×ATR、pos% = 0.33/ATR%、tx_cost、exit_trigger）
- weights.yaml 手動編輯，每次調整 bump weights_version（搭配未來 Step 7 weekly_review）

**完成**：
- `skills/short-term-target/scripts/predict.py`（385 行）— 主腳本含全部上述規則
- `skills/short-term-target/config/weights.yaml`— 可手動編輯參數
- `skills/short-term-target/SKILL.md`— 形式 spec
- `skills/short-term-target/README.md`— 使用 + 詮釋指引
- `skills/short-term-target/CHANGELOG.md`— v0.1.0 紀錄含 smoke test 結果
- `cache/`、`data/` 目錄含 .gitignore

**Smoke test（3 ticker，全通過）**：
- AMD（Stage 2 + 量增）：1d conf 0.59、5d target +3.28%、News 抓到 +13.9% gap
- CEG（低波動 utility）：1d conf 0.61、5d +1.52%、預測平緩
- IONQ（高波動 quantum，ATR 8.18%）：1d conf 0.17、15d conf 0.03（"沒意見"）— 高 ATR 自動降信心驗證 OK

**plan_short.md 進度**：
- Step 1（short-term-target）✅ 完成（v1.46.0）
- Step 2（4-6 個新主題到 cross_sector_themes.md）⏳
- Step 3（thematic-screener skill）⏳
- Step 4（Dashboard 兩分區）⏳
- Step 5（outcome tracking log）⏳
- Step 6（daily_update.sh 整合）⏳
- Step 7（weekly_review.py 手動 recalibration tool）⏳

**v0.1 已知限制**（README 已詳載）：
- News driver 是 volume/gap proxy，非真實 Finnhub /company-news（v0.2 升級）
- GICS sub-industry lookup 未做，benchmark 全部 default SPY
- 沒做 cache layer，每次 hit yfinance
- dual_fetch consumption 是 best-effort（read 不到不報錯）
- 未做 outcome 驗證（從 day 1 累積 + Step 7 評估）

**設計帶入的 backtest lessons**：
- News lane r=+0.373 的發現 → 1d horizon 給 news 0.6 最高權重
- 高 ATR 在 backtest 中是 outcome 變異最大來源 → 直接做進 confidence penalty
- 「不要在 1 個 regime 上過擬合」 → 整套設計接受失靈 + Step 7 手動 recalibration（user 拍板）

## 🟢 Session Note (v1.45.0) — Investment Protocol V4.8.1 Dual-Fetch 整合

把 v1.44 的 dual_fetch 接進 `investment_protocol_v4_8.md`。設計討論時排除了兩個明顯路線（Phase 1 加 subagent 做判斷 / 4 個 Phase 2 subagent 各自 call dual_fetch），採第三路：**PM inline 一次抓、4 個 subagent 共享 snapshot**。理由：(1) 同 session 同 snapshot，cross-lane 資料一致；(2) 不增 subagent，Phase 1 維持輕量；(3) `_audit.*` 隔離紀律集中守在 PM 一處 paste 動作。

**完成**：
- **`investment_protocol_v4_8.md` Phase 1**：新增「Phase 1 資料層 (V4.8.1)」段落，PM MUST 執行 `run_dual_fetch.sh`、讀取 `bundle["scoring"]`、絕對禁止讀寫 `_audit.*`（違反→當前 ticker 作廢、重啟 Phase 1）
- **Phase 2 共通 prompt 模板**：在 PHASE 0 MACRO CONTEXT 之後插入 `TICKER DATA BUNDLE` 段落（與 macro 同樣 read-only / shared-across-analysts 的 pattern）
- **Fundamentals subagent rubric**：新增 9 scalar 使用規則。重點：
  - bundle 為 9 欄位權威來源；與 us-stock-analysis 衝突 > 1% 採 bundle 並註記原因
  - `priceToBookRatio` 視為近似值，估值權重低於 P/E（已知跨 provider 10-30% 差）
  - `dividendYield` 單位 = percent / indicated annual（前瞻）
  - bundle 缺欄位 → 用 us-stock-analysis 補；皆無 → 排除於評分，不得猜
- **`investment/README.md`**：開頭新增 V4.8.1 增量變更段落
- **失敗模式**：FMP audit 失敗（quota / 401 / 403）不算失敗，scoring 仍完整；只有 Finnhub 全失敗才標 `data_bundle_available: false`，subagent 走 fallback

**未做（暫不動）**：
- 不修改 `us-stock-analysis` skill 內部 fetch 邏輯（仍會自己抓 FMP）。當前 bundle + skill 雙抓共存，由 subagent 在 prompt 規則裡仲裁衝突。未來可優化為 skill 接受 `--data-bundle` 參數跳過自抓
- 其他 3 個 lane（Sentiment / News / Technical）資料需求與 bundle 9 個 scalar 不重疊，本次不變更
- 未跑端到端 protocol 測試（需要使用者實際 `分析 [TICKER]` 才能驗證 PM inline 是否正確執行 dual_fetch）

## 🟢 Session Note (v1.44.0) — Finnhub Dual-Fetch + Audit Drift Monitor

承接 v1.43 的 diff 結果，把「驗證工具」升級成「常態雙抓 + 物理隔離」。先用 diff_tool 跑出 FMP stable 端點問題（v3 全 403、QQQ 402、`key-metrics-ttm` 欄位搬到 `ratios-ttm`、`peNormalizedAnnual` 與 `peTTM` 定義不同），逐一修完後得到完整 diff 報告，發現 `dividendYield` 5-7% 與 `priceToBookRatio` 12-38% 是**結構性方法論差異**，不是哪家錯。

**架構決策**：採用「Finnhub canonical, FMP audit」雙抓設計而非 fallback。理由：fallback 會讓同一支股票今天用 Finnhub、明天 quota 切 FMP 時 scoring 漂移、且漂移無法歸因；雙抓則保證 scoring 永遠來自 Finnhub（可重現），同時 FMP 平行抓取保留觀測能力（drift monitoring）。物理隔離靠 `_audit` 底線前綴慣例，禁止進入 LLM prompt。

**完成**：
- **`scripts/dual_fetch.py`（200 行）**：library + CLI 雙模式。輸出 `data/YYYY-MM-DD/{TICKER}.json`，頂層 `scoring`（Finnhub）+ `_audit`（FMP + diff + status）
- **`scripts/audit_drift_check.py`（110 行）**：掃過去 N 天 audit 紀錄，找出 `(ticker, field)` 在 >= MIN_HITS 天內 diff 超過 threshold 的持續性漂移，輸出 markdown 報告
- **`scripts/run_dual_fetch.sh`**：wrapper（檢查兩個 API key）
- **`README.md`**：三 script 用法（dual_fetch 日常 / audit_drift_check 週檢 / diff_tool 一次性 spot check），含 fmp_status 對照與 library 用法
- **`CHANGELOG.md`**：v1.1.0 紀錄含架構決策表
- **`SKILL.md`**：新增 § Dual-Fetch Discipline，明訂 `_audit.*` 不得進 prompt 的硬規則；Architecture Role 表把 simple metrics 從 TBD 改成 Finnhub canonical + FMP audit
- **修正 `diff_tool.py` + `adapters.py`**：v3 → stable 端點遷移、`peTTM` 提到 `peNormalizedAnnual` 之前

**未做（後續 PR）**：
- 不動 `investment_protocol_v4_8.md`，scoring/audit 整合進 protocol 是下一個獨立決策（PR-5/6 範圍）
- 不動既有下游 skill（ftd-detector / market-top-detector / us-stock-analysis）

## 🟡 Session Note (v1.43.0) — Finnhub Client + Diff Tool（PR-1 + PR-2）

新增 `skills/finnhub-client/` 作為共用基礎設施。背景：審計後發現 FMP free 250/day 配額會卡死 batch screening + Phase 3 自動化，且專案缺三個重大資料源（earnings calendar / earnings surprise / insider transactions）。Finnhub free 60/min ≈ 300× FMP 吞吐量，剛好補洞。

**完成**：
- **finnhub_client.py（359 行）**：60/min token-bucket throttle + file cache (per-method TTL) + exp backoff retry + 17 endpoints (quote / candle / profile / metric / financials-reported / filings / company-news / earnings-calendar / earnings-surprise / insider-tx / insider-sent / recommendation / price-target / upgrade-downgrade / dividends / splits / ipo-calendar)
- **adapters.py（171 行）**：5 個 Finnhub→FMP shape 轉換器；financials_to_fmp_income 標 `_lossy: True`（concept 對應不完整，僅供 raw filing reference）
- **diff_tool.py + run_diff.sh（374 行）**：side-by-side 比對 9 欄位 × 10 ticker，PASS<2% / WARN 2-5% / FAIL>5% 三級評分，輸出 `diff_reports/YYYYMMDD.md`

**架構修訂（吸收 ChatGPT review feedback）**：原方案「Finnhub Tier 1 包含 financials」改為**按資料種類分層**：
- 市場/事件層 → Finnhub primary（quote / OHLCV / profile / 4 種事件流）
- 財報真實層 → **FMP primary**（income/balance/cashflow，避免 Finnhub raw XBRL 漂移 quality model 的 CFO/NI/share count）
- 經濟/forward EPS → FMP only
- 簡易 metrics（P/E、ROE、div yield、P/B）→ PR-3 跑 5-7 天 diff 後再決定

**接下來**：使用者跑 `bash skills/finnhub-client/scripts/run_diff.sh`（需先 `export FINNHUB_API_KEY=...` 和 `export FMP_API_KEY=...`），連跑 5-7 天累積 diff 報告 → 決定 PR-4 data-client 抽象層的 routing 規則。

## 🟢 Previous Session Note (v1.42.2) — Sector Protocol 文字瘦身 R2

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

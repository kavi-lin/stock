# INTEL COMMAND — Backlog & Tasks

> **Last Updated**: 2026-08-02 (v4.86.2)

---

## ✅ Done (v4.86.2) — 4.82–4.85 review 的 P3 尾款（明細見 CHANGELOG）

- [x] `trade_plan_builder.classify_sector()` 補 FMP `profile.sector` 四個拼法（`Consumer Defensive` 原本被誤類成 cyclical，不只是噪音）。
- [x] `replay_trade_plan.replay_sizing()` 反解納入兩個 Phase 3 倉位 cap（V5.1+ 從 `calculation_steps` 取；讀不到 → 退出 cohort；pre-V5.1 的 1.0 假設改具名 factor）。
- [x] `investment_protocol_v5_0.md` 補回 `stop_buffer_pct` 預設 1.0% 與算式（此前只有 engine 知道）。
- [x] `_fetch_pe_ttm` 拆出 `PE_ABSENT` 三態 + warm-up 空資料 symbol 隔離，解掉 backoff 被永久空 ticker 釘死、`return not failed` 失去意義的問題。

## ✅ Done (v4.79.0) — 4.78.0 review 的 P1 + 三項 P2

- [x] **P1**：archive 最新 MU snapshot 生成於兩個 commit 之間、仍帶被晉升的 -9% cohort median；已重跑並以新 snapshot 蓋過（`ce59d45`）。
- [x] **P2-1**：promoted cohort 的 note 改由 `rationale.criteria` 動態產生（`_cohort_selection_note`），演算法與 human-approved 兩種出處不再混淆。
- [x] **P2-2**：window-CAGR 路徑補 point-in-time gate；`generated_at ≥ window_to` 拒收，`≥ window_from` 標 `point_in_time_caveat` 但仍計分。實測新增拒收 0 筆（無回歸），19 筆 legacy row 帶 caveat。
- [x] **P2-3**：CLI 改印 `summary` + `forecast_points`，`evaluations` 改由 `--full-evaluations` 取得（1.82 MB → 54 KB）。
- [x] **`_signed_bias` 繞過 dedup** — 已於 v4.79.1 修正（改吃 `forecast_points`，criterion 加 `bias_basis`；無 identity 的 rows 不硬去重以免塌縮）。

## ✅ Done (v4.78.1) — Calibration index

- [x] calibration 改讀 6 欄位 derived index（685 快照 362 ms → 29 ms，12.5x），輸出與 `--no-index` 全量掃描逐字相同。
- [x] 索引綁 size+mtime 失效、schema/欄位集變更自動重建；Fixture H 斷言等價性與失效行為。
- **刻意不做**：壓縮歸檔（tar.gz 只省空間不省時間，且解不了線性成長）；不動原始 ledger。
- [x] **索引欄位不用人記**（v4.79.0 Fixture I）：測試 AST 掃描 calibration 讀到的 snapshot 欄位，與 `INDEX_FIELDS` 雙向比對，漏了就 rc=1 並指名欄位。日後評分 `base_rate_lane` 等 lane 時會自動被擋，不需要事前記得。
- [x] **既有死碼已清**（v4.79.0）：`_latest_snapshot_per_ticker` 與 Fixture F 移除。

## ✅ Done (v4.78.0) — Forward Expectations 前瞻預測可信度修正

- [x] annual estimates 依 point-in-time cutoff 排除 elapsed FY，consensus/revision/financial bridge 同源。
- [x] terminal range 與 12m target 語意分離，輸出年化報酬；coverage <20 降低信心。
- [x] calibration 支援完整 Q1–Q4 FY level、out-of-sample 時點 gate、earliest-vintage dedup。
- [x] broad raw peers 與 metric scope 不符的 cohort 只揭露；numeric base-rate 需 ≥3 members 且明確核准 `growth_base_rate`。
- [ ] **校準觀察點**：累積 ≥15 個真正成熟 comparable points 後，才評估 growth/margin/multiple 規則；未達門檻不得升格 live。
- 三項 P2 已於 v4.79.0 完成，明細見該區塊。

## 📋 Backlog — Protocol Lean 化：「保留 5 個 lane score，不保留 5 次固定 LLM」（2026-08-02 共識定案）

> 共識五點：(1) 5 score ≠ 5 LLM，決策層 schema 不動；(2) 先 script 化決策數學，再談條件式跳過；(3) 改變 score 生產方式必 shadow-first；(4) Sentiment deterministic 化優於 News/Sentiment 合併；(5) LLM 集中在 Fundamentals / News / 條件式 Valuation reviewer / Red Team。
> 驗證分流：搬公式 → spec parity + replay triage；改 score 生產 → shadow + weight 凍結窗；換格式 → golden file + validator；重排 → JSON regression equivalence。**每項獨立 bump 一版**（三處同步 + CHANGELOG + validator 向後相容），回滾邊界一項一版。

- [x] **L1 — `decision_engine.py`（Phase 3 script 化）** — v4.80.0 完成。engine + `test_decision_engine.py`（spec parity，含 MU golden replay）+ `replay_decision_engine.py`；protocol Phase 3 / 4.6 改 script call；validator §13 硬閘（舊 entry 跳過）。
  - **replay 實測與原假設不同**：可做 parity 的歷史樣本 **1 筆**（非 111）。per-lane confidence 從未寫進 `history.json`，V4.70.0（2026-07-16）之後累積的 deep-dive 又只有 4 筆——那 4 筆全部逐點相符（1 筆嚴格 parity + 3 筆在 spec 預設假設下 |Δ| ≤ 0.0003）。94 筆 pre-V5.0 四 lane、38 筆 `decision_sensitive_unknown`、37 筆 lane 輸入缺失，全部逐筆列在報告裡。
  - **衍生待辦（下次動 Phase 3 export 時一併做）**：`structural_shift.tier` 出現在 38 筆的敏感度掃描裡卻從未持久化 → 應寫進 `calculation_steps` 以外的欄位；`mandatory_risk_flags` 同理（現在 replay 只能宣告假設）。補了之後 replay 的 parity 分母才會真正長大。
  - v4.80.1 收掉 review 的 2 P1 + 2 P2（probe 逃過硬閘、validator 判死 cap override 路徑、§13 可繞過、MISSING lane 死路）；明細見 CHANGELOG。

- [x] **L1b — `session_export_version` bump 到 V5.1（schema 遷移）** — v4.81.0 完成。§13 門檻改綁版本集合（`CALC_STEPS_REQUIRED_VERSIONS`），日期閘留任 mis-stamp 後衛；`V5_VERSIONS` 取代全部 `ver == "V5.0"` 單值比較。
  - **TODO 原本漏列的兩處**：`validate_markdown_export.py` 是隱藏消費端（新版 entry 會整段跳過「合理股價」檢查）；`Dashboard/page-decisions.js` 的 `detectProtocolVersion()` 已把 `'V5.1'` token 用在 trajectory 啟發式上 → 改成戳記優先、啟發式降 fallback。下游兩支現在 **import** validator 的版本集合，升版只改一處。
  - **順手修掉兩個實測出來的洞**：`hot_zone_eval` warning 條件寫反（只對舊 entry 發、對現行 export 恆不發）；§13 Tier B 可把已套懲罰的鏈條改標 `no_penalty` 過閘（cascade 標籤與 `penalty_applied` 現在雙向一致性檢查）。
  - **`phase5_export_schema.md` FULL EXAMPLE 已改為實跑 engine 的完整 V5.1 範例**，驗收 fixture 直接從 doc 解析 → doc 再壞掉測試會紅。
- [x] **L2 — `trade_plan_builder.py`（Phase 4 script 化）**：entry band / TP / SL / staged split / R/R / final sizing 組裝（risk_manager / tail_risk 已 script）。**4.82.0 完成**：engine + `test_trade_plan_builder.py`（17 fixture）+ `replay_trade_plan.py`（3 cohort）+ validator §14 + schema V5.2。
  - 未做（刻意留下）：**Trader LLM 觸發條件 deterministic 定義**（option hedge / portfolio conflict / 跨週期多 catalysts）—— 這三個情境目前 protocol 完全沒有 spec 可 script 化，硬定會是憑空發明規則而非 script 化既有規則。要做需先累積實例並由使用者定調，另開項目。
- [x] **L3 — Phase 5 deterministic renderer** — **4.87.0 完成**。`render_investment_report.py`（雙輸入：history 末筆 + `invest_logs/phase_inputs/<DATE>_<TICKER>.json`）+ `test_render_investment_report.py`（A-F 六組）；Phase 5 Step 4 的 Sonnet formatter Agent call 移除，Step 4.5 injection 併入（六個 FACTS 區塊改 **import** `inject_report_facts.py` 的同一組 renderer，不複製）。
  - **動工時發現原假設錯**：「history entry → MD」做不到——§5 五個 lane 的 key_factors / risk_flags、sentiment lane 整塊、per-lane raw signal/confidence 都沒持久化，走單輸入會讓報告掉約 80 行。改雙輸入，bundle 落地存檔（不是 `/tmp` 即棄），並補**重疊欄位硬閘**：不符 rc=1 不產檔。
  - **`--polish` 預設 OFF**，只動五段純敘事；三道守衛全 fail-open（結構 / 數字圍堵 / model_router 記帳 + footer provenance）。CI 測的永遠是 0-LLM 那條路徑，不需要 mock LLM。
- [ ] **L4 — Valuation quant 提前 Phase 1.5**：`compute_price_framework --self-assemble` quant pack 移到 Phase 1.5；Phase 2.4 只組 MHP / 5d band / 60d target（吃 technical/news qualitative）。驗收 = 重排前後 valuation_pack regression 完全一致；修 protocol「Phase 2 lane 依賴 2.4 pack」時序矛盾文字。
- [ ] **L4b — Valuation Specialist 改條件式 reviewer**（依賴 L4，shadow-first）：觸發條件 deterministic（no curated peers / structural shift / anchor 嚴重衝突 / data quality 低但可能 BUY）；peer discovery 30-90d cache。
- [ ] **L5 — Sentiment lane deterministic 化**（shadow-first）：公式已寫死（0.5×stock + 0.5×(market/10−5) + 規則表）→ det producer script；先 shadow N session 過 `shadow_report.py` 哨兵再翻預設；翻後 weight 凍結窗（照 V3.45.4 News 前例）。**統一 lane 契約第一個落地點**（見橫切 C1），動工前先定案 det_shadow 收斂。
- [ ] **L6 — Technical deterministic-first**（shadow-first）：det score producer（technical_core 為基）；LLM reviewer 觸發規則化（指標矛盾 / gap / parabolic / det score 落 threshold ±band）；qualitative 欄位（pattern_taxonomy / smart_money / key_levels → MHP 依賴）需 det 版或觸發 LLM 時才產。shadow + weight 凍結窗。
- [ ] **L7 — Red Team evidence ledger**：Python 壓 ledger（consensus_thesis / claims / negative_evidence / valuation_assumptions / implied_expectations / dq_flags / unresolved_conflicts）；RT prompt 改吃 ledger（先縮 prompt，不跳過）；classifier haystack 欄位保留。
- [ ] **L8 — RT decision-invariant skip**（依賴 L1）：bounded simulation 窮舉 verdict × strength × basis × shift-tier，final action / cap / size tier / risk flags 全不變才 skip；skip = 跳過推理**不跳過產出物**——kill_conditions ← det kill triggers 生成、counter_thesis 模板化、`red_team_provenance: deterministic_skip`；decision_lock / Dashboard kill_triggers 相容。
- [ ] **L9 — Refresh / content-hash mode**：factpack 加 `content_hash` + `material_change_since_last`；`analysis_mode: LEAN|FULL_IC|REFRESH` + LEAN→FULL_IC 升級規則 deterministic 寫進 protocol 正文（首次覆蓋 / structural shift / 高信心可行動決策必升）；refresh entry 的 history/Phase 6 語意定義。
- [ ] **C1（橫切）— 統一 lane 資料契約**：per-lane `{provenance, llm_invoked, producer_version, input_hash, shadow_score}` + session 層 `{llm_invoked_lanes[], llm_skipped_lanes[], analysis_mode}`；**取代並吸收既有 det_shadow block**（`apply_det_shadow.py` 改為新契約 producer，勿兩套並存）——L5 動工前定案；validator + 舊 entry 向後相容；Phase 6 校準按 provenance 分層（防 selection bias）。
  - **design 輸入 — 4.87.0 實測盤點的持久化缺口**（L3 動工時逐筆驗過 MSFT/MU 2026-08-02 兩筆真 entry）。C1 定案時要回答的是「這些哪些進 history、哪些留在 `phase_inputs` artifact」：
    1. **`sentiment_lane` 整塊不存在** —— schema 從來沒有這個 key，Sentiment 只在 `lane_scores.sentiment` 有一個數字，沒有任何質性欄位。
    2. **四個 lane 的 `key_factors` / `risk_flags` 從未持久化** —— 只有 `news_lane.key_factors`（V3.45.4 加的）有；`risk_flags` **五個 lane 全部沒有**。這是報告 §5 人真正在讀的證據段。
    3. **per-lane raw `signal` / `confidence` / `phase0_alignment` 只有 valuation 有** —— `valuation_lane` 存了 `{signal, score, confidence}`，其餘四個 lane 的 signal 與 confidence 只活在 Phase 3 的 `calculation_steps` 字串裡（且是 c_eff 量化後的值，raw 值不可回推）。
    4. **`macro_context` 只有 ~384 bytes** —— 報告 §3 的宏觀段實際來自 Phase 0 JSON，history 只留一段摘要。
    5. **lane 區塊形狀在真實 entry 之間不一致** —— `moat_assessment` 有時是 dict 有時是字串；`smart_money_analysis` 的正文欄位有時叫 `narrative` 有時叫 `note`；`immediate_catalyst_5d` 有時是 dict 有時是 null。C1 的契約要把形狀定死，否則每個消費端都要各自寫相容碼（renderer 現在就寫了三處）。
  - **`phase_inputs/` 那批檔案就是 C1 的實測樣本** —— 累積幾份後可直接回答「哪些欄位每次都在、哪些其實沒人用」，不必憑空設計。
- [ ] **C2（橫切）— factpack per-lane slim views**：`phase1_factpack.py` 直接產五個 lane view + Phase 0 lane-specific macro view，PM 不再手動切片（消 cross-anchor 抄錯面）。驗收 = view 欄位覆蓋現行注入規則的 JSON equivalence。
- [ ] **C3（backlog，非 quick win）— Fundamentals 瘦身走消費者 audit**：catalysts 移交 News 需連動 ic-memo `build_fact_pack.py` / `compose.py` / Dashboard `page-decisions.js` / schema / fallback；`moat_assessment` 有消費者必留。程序 = producer/consumer 搜尋 → 保留/移交/落日，禁憑直覺刪。

## ✅ Done (v4.77.0) — 估值引擎 review 修正（degraded path 治理）

- 12 項 review 發現全數修正：期間對齊的 start EBIT margin、degraded 報告不再 crash、缺估計時成長種子不再套 cap、structural shift 降級必附 reason、無效 override 出聲、`_eps_growth` 只取最近兩個未來 FY。
- 新增 `--projection-mode auto|legacy`、cohort schema 驗證與 `pe_min/max` 離散度、canonical peer 健康時不渲染第二張 peer 表。
- MU 迴歸逐項一致（`$762.13` / WACC `12.49%` / `$693.74–853.60`）；新增 27 條 regression assert。
- **待使用者決定**：範圍 B（`SKILL.md`、`config/peer_cohorts.json`、`comps.py`、`peer_cohorts.py`、`export_xlsx.py`、2 支測試）仍 untracked，需與 `4e54e79` 一起 commit 才能解掉「單獨 checkout A 時 `--xlsx` ImportError」的根因。
- **後續校準**：累積更多非 3 季 / 缺 `ebitAvg` 的實際 ticker 後，回頭檢查 `reported_quarters_only` margin 基礎與 degrade reason 的覆蓋是否夠用。

## ✅ Done (v4.76.0) — DCF-primary + audited peer range

- LLM/manual 只發現 candidate；Python ratio adapter、≥3 正值與 range-only gate 已落地。
- Structural DCF 為主 FV；without/with-peer、DCF sensitivity 與其他 eligible anchors 形成 explained range。
- **後續校準**：累積跨週期 outcome 後檢查 adjacent storage cohort 是否系統性高估；未達樣本門檻前不得升格 live peer anchor。

## ✅ Done (v4.75.1) — MU structural-shift DCF 重建

- current-FY roll-forward、bounded growth、normalized operating/reinvestment path、mean-reverting beta 與 latest balance/share inputs 已落地。
- MU DCF `$762.13`，敏感度 `$693.74–853.60`；eligible 新 DCF 會 supersede opaque vendor DCF，但保留 lineage 稽核。
- **後續校準**：累積 structural-shift 案例後回測 growth caps、terminal margin 與 beta adjustment；不得依單一 MU 現價反推參數。

## ✅ Done (v4.75.0) — 個股估值可信度修正

- 唯一 canonical valuation pack、三 family/correlation 去重、eligibility-before-aggregation、下游 hard consistency 已落地。
- 關閉 LLM/input-file live anchor 注入；DCF、forecaster、peer/comps、analyst PT 改 fail-closed；Reverse DCF 僅 diagnostic。
- MU audit、完整 regression tests、invest validator 與同 session Claude Fable 5 code review 均完成；最終 review `ACCEPT`。
- **後續校準**：累積足夠 outcome 後再校準 PT 180 天 freshness 與 family weights；校準前不得憑 LLM 判斷改 live 數字。

## ✅ Done (v4.70.0 → v4.72.0) — 分析協議審計 + P0/P1/P2 全系列改制

- 審計報告 `reports/decision_review/AUDIT_2026-07-16_protocol_v5.md`；三波全落地：P0（probe 分層 / Red Team 懲罰分級 / anchor 修剪 / confidence 三檔）、P1（shadow 落日 / 欄位瘦身 / 5d 降級 / Phase 0 caps；P1-6 依消費者證據收窄、regime 規則表化依校準否決）、P2（parabolic 斷鏈 / forecaster 聲明 / validator §12 界限檢查 / ftd 路徑整併）。
- **⏳ 待 user 決策**：
  - [x] dispersion 門檻改 0.375/0.52 — **已核准並落地（v4.72.1）**
  - [ ] archetype shadow：翻轉率 22.6% ≥15% → 按規則不切（2026-07-16 檢視：7 筆翻轉 100% 集中 hypergrowth、方向雙向 4/3 = 把極端 band 往中間拉；有 outcome 的僅 1 筆無從判定）。**檢查點重置**：P0-3 trim 已改變 live 行為，pre-trim 翻轉率過時——累積 ≥20 筆修剪後 session 重測；屆時若仍 ≥15% → 對翻轉案例跑方向性 backtest（live vs shadow band 誰更能預測 30/60d 前瞻報酬），並評估 **hypergrowth-only 局部切換**（balanced/cyclical 零翻轉不需動）
- **📊 校準債（有截止條件）**：`red_team_counter_evidence_strength` × `thesis_break_probability` 累積 ≥20 session 後跑 outcome 校準（無鑑別度 → 分級懲罰再降）；probe tier 首 4 週盯 t2 命中率；oe shadow 11/20 累積中；**agreement_grade 門檻再校準**——P0-3 trim 使 cv 左移，累積 ≥20 筆修剪後 session 由 shadow_report.py 重出分佈再議 0.375/0.52。
- **🔍 下次 `分析 [TICKER]` 實戰驗證清單**：Red Team strength/probability 兩新欄、C_eff 三檔量化、rationale 機械格式、anchor 修剪、hot_zone_probe_tier。

---

## ✅ Done (v4.64.0) — Agent 治理層（CLAUDE.md 瘦身 + docs/agent-ops/）

- CLAUDE.md 178→74 行純路由；父層指標化；`docs/agent-ops/` 8 檔（診斷/指令總表/模型調度/判斷 rubric/派工模板/維護協議/教訓/交接信）；v4_8 歸檔+引用清零；MARKET_INDEX 補齊 24 skills；AGENTS/GEMINI 去重。對抗審查 13 findings 全修。
- **⏳ 待 user**：`CLAUDE拷貝.md` 確認後刪除（備份在 `docs/agent-ops/backups/`）。
- ✅ SESSION_NOTES 歸檔完成（v4.64.1）：保留最近 10 個 Session Note，236 個搬 `archive/session_notes_archive.md`（4754→~100 行）。
- ✅ CLAUDE拷貝.md 已由使用者刪除（2026-07-03）。
- ✅ daily health 摘要完成（v4.65.0）：`scripts/daily_health.py` + daily_update.sh 收尾自動印表。
- ✅ 報告決策數字 script 注入完成（v4.66.0）：`inject_report_facts.py` + protocol Step 4.5，6 區塊佔位符制，33-assert golden fixture。**⏳ 待實戰**：下次跑 `分析 [TICKER]` 驗證一輪佔位符流程。
- ✅ 2+1 評審制接線完成（v4.67.0）：Red Team + Arbiter 降級補償寫入兩 protocol 本文，schema 零改動。**⏳ 待實測**：首次在無高階檔環境跑 protocol 時盯 referee 是否守三問制。
- **⏳ Backlog（詳見 docs/agent-ops/LETTER.md 交接表）**：llm_review 300KB 索引預切段（script 先切段統計、模型只看摘要層）。

---

## ✅ Done (v4.62.0) — 量化策略回測頁（quant-backtest）

- **`skills/quant-backtest/`** — 0-LLM 回測引擎（momentum 計分規則 5-10y 重放 + ma_cross）+ 29-assert golden fixture + SKILL.md；`backtest.html` 新頁（tiles/權益/進出場/回撤/分數/Sharpe 熱力圖/逐年/交易）；server `quant_backtest` SCRIPT_PROTOCOLS + `GET /api/backtest/{list,result}`。探索層，不入委員會決策。
- **⏳ 待 user**：重啟 dashboard_server 生效後實機開 `/backtest.html` 看渲染。
- **⏳ V2 候選**：多 ticker 組合、walk-forward 分段、自家訊號源（journal/thematic recommendations）接入回測、股息調整報酬。

---

## ✅ Done (v4.54.1) — 修逆勢假反轉(MU) + 訊號流收合

- **`apply_trend_context(rv, tr)`** — 反轉撞嚴格反向均線排列 → `counter_trend`/`alert=False`/「逆勢反彈·回測」;`build()` 套用,前端不當頭條。修 MU 空頭排列急跌卻爆「反轉向上」。
- **`_collapse_flow()`** — 訊號流連續同向收一筆(spike 保留 ⚡),`max_events` 4→3,不再連三次。
- **+4 case**(逆勢降級/同向保留/無趨勢保留/flow 收合)。
- **⏳ 已知取捨**：counter_trend 僅嚴格對向排列觸發;tr=None 時逆勢反轉仍報。

---

## ✅ Done (v4.54.0) — 個股急拉/急殺：加「順勢續攻/續跌」趨勢延續 STATE 偵測器

- **`detect_trend()`**（intraday_spikes.py，0 LLM）— 狀態型偵測,補 spike(暴衝)/reversal(剛交叉) 抓不到的「均線多頭排列順勢創高」。多頭 = 嚴格 ma5>ma10>ma20 + 收≥ma5 + ma5 上揚 + KDJ K>D & K≥50 + 貼近 20 根窗高;空頭鏡像。payload 1.3→1.4,reading 掛 `trend` + top-level `trends[]`。前端狀態行優先序 反轉>趨勢>尚無訊號,趨勢卡左緣色條。+5 case/+19 asserts。Live：12 檔全無訊號 → 6 檔跳順勢訊號。
- **⏳ 可調**：render 把非 alert 小反轉排在 strong 趨勢前,若要 strong 趨勢優先可調;`TREND_K_MIN`/`TREND_HIGH_WINDOW`/`TREND_HIGH_TOL` tuning。

---

## ✅ Done (v4.51.0) — 急拉/急殺加 MACD/KDJ/量 確認層

- **`detect_spikes()`** 重用 `intraday.compute_macd`/`compute_kdj` → confirmations + confirmed(價 + ≥2)；fetch 40→90 分；chip 加 ✓badge + ★。24 asserts。
- **⏳ 資金流向/特大單（待 user 選）**：(a) Futu OpenAPI/OpenD（確切特大單，免費 user Futu 帳號，需裝 futu-api + 跑 OpenD）/ (b) Alpaca SIP $99 tick 自分類 / (c) 免費 bar 近似（OBV/上下量比，只有方向）。

---

## ✅ Done (v4.50.0) — 個股急拉/急殺快線（Alpaca 1 分鐘，獨立 lane）

- **`intraday_spikes.py`**（0 LLM）— Alpaca 1min REST 多檔一次抓 + `detect_spikes()`：近 5 分鐘 `|1分|≥1%` / `|3分|≥2%` → 急拉/急殺，severity + 量增 3× 次要確認。`config/spike_watchlist.txt` 可手編。
- **接線**：`intraday_spikes_poll_loop`（60s，盤中）+ GET `/api/intraday-spikes/data` + intraday 頁頂部區塊。無 Alpaca key graceful no-op。`test_intraday_spikes.py` 18 asserts。
- **⏳ 待 user**：alpaca.markets 免費註冊 → 設 `ALPACA_API_KEY`/`ALPACA_SECRET_KEY`。`ALPACA_FEED=sip`（$99/mo）才有準確量；免費 IEX 量低估，偵測以價格為主。

---

## ✅ Done (v4.49.x) — 盤中評估：MACD/KDJ 動能層 + 即時 quote + 修側欄

- v4.49.1 修 `intraday-mood.html` 漏 `UI.boot('intraday')` → 左側欄不 render（已修）。
## ✅ Done (v4.49.0) — 盤中評估：MACD/KDJ 動能確認層

- **`intraday.py`** pure-python `compute_macd`/`compute_kdj`（末根交叉 + bar 數守門）→ 日線(regime)+5min(時機) 雙框。
- **旗標（只確認層、不動分數）**：下殺=盤中 KDJ 高檔死叉 / MACD 死叉+跌破VWAP；反轉=盤中 KDJ 低檔金叉 / 日線 MACD 柱轉升；macd_daily=日線金叉死叉。confluence-gated 擋 5min whipsaw。
- 每檔 `momentum` 數值透出；卡片加 MACD/KDJ 讀數+交叉箭頭。`MACD_*`/`KDJ_*`/`KDJ_OB`/`KDJ_OS` 檔頭可調。`test_intraday.py` 47 asserts。

---

## ✅ Done (v4.48.1) — 盤中評估：即時 quote 混合

- **`intraday.py`** `assess(live=)` + `_fetch_live_quote`：FMP `quote` 覆蓋 spot/當日高低/量/昨收（~2s 新），破底/止跌秒級化；5-min K 仍管 VWAP+型態。每檔 `data_source`+`quote_timestamp`，頁面 pill「· 即時報價」。`test_intraday.py` 34 asserts。
- **1min 不可用**（stable 回 None）→ 型態最細 5-min。

### ⏳ 盤中評估候選增強（user 待決，Tier-1）
- 盤中 VIX context 分量（`quote ^VIX`）、類股輪動快照（`sector-performance-snapshot`）、HYG 信用佐證（同 assess 跑 HYG）、時段化 RVOL 曲線（修早盤線性外推噪音）。皆走既有 quote/5min 端點。

---

## ✅ Done (v4.48.0) — 盤中評估引擎（Intraday weakness tape）

- **`intraday.py`**（0 LLM）— FMP 5-min bars + ~60 日 daily → SPY/QQQ/IWM signed −100..+100 盤中評估。破底(5/20/50d)/止跌/高開低走/量增價跌(RVOL)/VWAP/MA20/連跌/出貨日。`UNIVERSE`/`WEIGHTS`/門檻 = 檔頭常數可調。
- **接線**：dashboard_server `intraday_mood_poll_loop`（盤中 300s + 開機 + 收盤快照）+ GET `/api/intraday-mood/{data,state}` + POST `/refresh`；`intraday-mood.html` 獨立面板；utils.js nav；index.html mini-strip；daily_update Step 9.35；`test_intraday.py` 26 asserts。
- **踩雷**：stable daily 端點 = `historical-price-eod/full`（`historical-price-full` 回 None）。
- **可調項（user 探索期）**：universe 增減（如加 ^VIX 盤中）、poll 間隔、score 取向（目前 負=破底）、各 WEIGHTS/門檻。
- **紀律**：探索層，**不**入 investment_protocol。

---

## ✅ Done (v4.47.2) — weekly-tech-playbook：Codex Review 整合優化

- **P1 解耦（關鍵）**：`render.py` `codex_review` 改可選——缺它 rc=0 仍生成（原 fatal、依賴反轉破壞可重跑）。
- **P2 去自打臉**：非 blind review 不再 by-default degraded；只在宣稱 blind 時要求 `blind_artifact`。
- **P4 公平性**：`review.py` Codex sleeve 標 `deployed_pct`/`cash_pct`（部署 75%），alpha 非同 beta 比較已標示。
- **SKILL.md** Step 2.5「必填」→「可選」對齊 code。
- **保留 Codex 好設計**：committee-blind pack（反 anchoring）、現金當 sleeve、降權抛物線股、檢討加 QQQ/SOXX+回撤。
- **待 user 決定**：P3 `codex_review` 欄位泛化為 `independent_review`+`reviewer` meta；P5 render 職責拆分；P6 codex 標的若不在三籃內無進場價。

---

## ✅ Done (v4.47.1) — weekly-tech-playbook：下週 LLM 檢討機制

- **`scripts/review.py`**（0 LLM）— 過去某週方案 vs 檢討日收盤:每檔報酬、每籃 vs SPY alpha、命中率、kill 觸發偵測、三籃排名 → `reports/<REVIEW>_TECH_PLAYBOOK_REVIEW.md`（含空白「🧠 LLM 檢討」段）+ `Dashboard/playbook_review.json`。觸發詞「投資方案檢討」。
- **`render.py`** 加寫 immutable dated snapshot `data/playbook_<DATE>.json`（進場錨點,可回放）。
- **`page-playbook.js`** 頂「上週方案檢討」橫幅（讀 playbook_review.json,僅 entry≠review 日顯示）。
- **兩段式**:review.py 算硬數據(0 LLM,永不自動覆寫) → Claude turn 讀填質性判讀 → 改下週 selections。
- **用法**:下週同日 `python3 skills/weekly-tech-playbook/scripts/review.py --date 2026-06-22 --asof <下週日>`。

---

## ✅ Done (v4.47.0) — weekly-tech-playbook：三籃子 $100k 科技投資方案 + Dashboard 頁

- **新 skill `skills/weekly-tech-playbook/`** — build_pack（0 LLM 組 regime+熱題+委員會 verdict+報價）→ LLM 選股 selections JSON → render（0 LLM 算股數/驗證每籃=$100k，rc 0/1/2）→ `Dashboard/playbook.json` + `reports/<DATE>_TECH_PLAYBOOK.md`。
- **三籃子設計** — 保險/激進/混合各 $100k，信心分級（核心 $15k×3 / 標準 $10k×4 / 輕倉 $5k×3）；混合 = 65% 保險 sleeve + 35% 激進 sleeve。
- **Dashboard** — 新增 `/playbook.html` + `page-playbook.js`，sidebar「投資方案」（portfolio group），三籃可切換 + 檢討 scaffold。
- **本週首版** selections_2026-06-22.json 已產，render rc=0。
- **待 user**：重啟 dashboard_server 開 `/playbook.html`；下週同日跑檢討；考慮 `/schedule` 每週一自動 build_pack+render。
- **後續可選**：build_pack 委員會 scraper 會抓「最近 14d 內」報告，可能含較舊/不同價基的 FV（如 AMD 6/14 FV $142）→ 之後可加 freshness 標記或只取 ≤7d；render 可加 `--refresh-prices` 重抓 yfinance。

---

## ✅ Done (v4.45.0) — 供應鏈 Wave B：UI 下鑽 + budget tiering + node 校正

- **#7 UI 下鑽** — edge `direction` chip（衝突/確認）+ node `stale`/`user_status` 視覺標記進 card+detail（Wave A 訊號終於可見）。
- **#5 FMP budget tiering** — priority(spine/ticker/≥2 downstream) 先驗；headroom<0.5 週邊只服務 cache + 跳 name-search；profile TTL 7d→30d。
- **#8 node override** — `overrides/<slug>.json` sidecar（不改 LLM YAML）+ `POST /api/supply-chain/<slug>/override` + detail panel ✓確認/⚑標記/清除 button。enrich merge 修正欄位優先。
- **#9 測試** — 5 新 test，全檔 23 pass。
- **供應鏈 8 gap 全收口（Wave A+B）**。後續可選：override field-edit 表單 UI（現 field 修正僅 API）；relation source clickable 連回新聞流。
- **待 user**：重啟 dashboard_server → 開 `/supply-chain.html`，點 node 試「✓確認/⚑標記」確認框線變化與 detail；觀察 edge `方向衝突/確認` chip 是否在有 Nexus 有向邊的 pair 出現。

---

## ✅ Done (v4.44.0) — 供應鏈 Wave A：方向校驗 + 回寫閉環 + stale/relative-heat/ADR

- **#1 edge 方向校驗** — `_direction_check()`：co-mention 對稱只證相關非方向，改用 Nexus directed edge 校驗 LLM 箭頭；corroborated 但方向矛盾 → weight 0.5 + `relation_evidence.direction`。
- **#2 corroborated 回寫閉環** — `export_corroborated_edges()` + CLI `--export-edges`：digest-corroborated 方向乾淨 edge → `bn_*.json` 餵 Nexus tier-1。opt-in，不在 enrich serve 路徑；source 標 `supply_chain` 防增強迴圈。
- **#3 stale flag** — node `stale`/`stale_reason`（age>45d 且無 live 訊號）；`data_quality.stale_node_count`/`chain_age_days`。FMP-off 不算 stale。
- **#6 relative heat** — heat 改 chain 內 33/67 百分位 + 絕對 floor 8；<4 active node fallback 絕對。
- **#4 foreign ADR 補全** — foreign node name-match 命中 US 交易所 → 升 `adr_ticker` → 可交易 proxy。
- **#9 測試** — 7 新 golden test，`tests/test_supply_chain_enrichment.py` 全檔 18 pass。
- **Wave B 待辦**（下次）：#5 FMP budget tiering（spine/investable 先驗、週邊 lazy）、#7 UI edge 下鑽到 `relation_evidence.sources`、#8 node override（標錯/確認 → override file → enrich merge）。
- **待 user**：可選跑 `python3 scripts/nexus/supply_chain.py --export-edges --export-graph-refresh` 把現有 chain 的 corroborated edge 灌回 KG；開 `/supply-chain.html` 確認 heat 分級與既有頁面無 regression。

---

## ✅ Done (v4.43.5) — 供應鏈 freshness + incremental rerun metadata

- 供應鏈頁右側 meta 顯示 Fresh/Aging/Stale、生成 LLM、完整/增量模式與生成時間 tooltip。
- Rerun 會把前一版 YAML 傳給 LLM 作 baseline，要求保留有效結構並以最新 local context / 可用 public sources 增量更新。
- YAML metadata 新增 `refresh_mode/source_scope/previous_generated_at/previous_generated_by`；CLI 支援 `--rerun`。
- **待 user**：重啟/刷新 `/supply-chain.html` 後，選既有主題確認右上 freshness badge；按 `Rerun` 後新版應顯示 `增量更新` 與當日生成時間。

---

## ✅ Done (v4.43.4) — 供應鏈頁主題 Rerun

- 供應鏈頁選定既有主題後可按 `Rerun`，用同一 theme 重新排入 `supply_chain_generate`，完成後覆寫同 slug YAML 並自動輪詢載入新版。
- Generate / Rerun 共用 queue helper；未選 chain 時 Rerun disabled。
- **待 user**：重啟 dashboard_server 後開 `/supply-chain.html`，選 MLCC 或既有主題按 `Rerun`，右下角 protocol pill 應顯示進度，完成後圖譜刷新。

---

## ✅ Done (v4.43.3) — 供應鏈探索：材料型產業 prompt 稽核強化

- 供應鏈生成 prompt 對 MLCC/電池/基板/光學/化學品等材料/製程型主題新增完整拆鏈要求：上游材料、受限添加物/礦物、製程設備、產品等級、下游需求週期、替代技術。
- MLCC 類主題新增規格分層與成本驅動紀律，避免把 AI server 高階料缺貨外推到全 MLCC，或把現代 MLCC 成本粗糙連到白銀。
- evidence 暫以 `note` 標 `confirmed` / `industry_report` / `inferred` / `stale` / `contested`；未改 YAML schema。
- **待 user**：重新用 supply-chain generator 產一條 `MLCC` 鏈，檢查是否展開材料/設備/替代技術與規格分層；若效果仍不夠，再升級成獨立 reviewer/validator pass。

---

## ✅ Done (v4.43.1) — 供應鏈外股常見公司 backfill

- 舊 YAML 只有 `foreign_listed` 時，常見外股供應鏈公司自動補 `TW/KR/JP/EU + local_ticker + ADR` 顯示；人工欄位不覆蓋。
- **待 user**：重啟 dashboard_server 後重新開 `/supply-chain.html`，常見 TSMC/Samsung/Tokyo Electron 等應不再顯示 `FOREIGN`。

---

## ✅ Done (v4.43.0) — 供應鏈頁外股標示 + 上下游投資摘要

- 台股/韓股/日股等非美上市節點新增 `market/local_ticker/adr_ticker/investability`，Dashboard 卡片不再把外股誤顯為未上市。
- 供應鏈頁新增 deterministic「上下游投資摘要」：可投資標的、瓶頸/槓桿節點、私有公司 proxy、高信心關係。
- **待 user**：重啟 dashboard_server 後打開 `/supply-chain.html` 實看既有鏈條；舊 YAML 若要完整顯示台/韓/日代號，可逐步補 `market/local_ticker/adr_ticker`。

---

## ✅ Done (v4.10.0) — 決策中心 RWD + 三層卡片 + V3.45+ 估值欄位接通

- RWD（4K 4 欄滿版、drill overlay 改 wrap grid、<860px sidebar 收合全站生效）+ 卡片三層化（結論 strip / 理由 collapse / 證據 collapse）+ bridge.py 接 8 個 V3.45+/V5.0.x 欄位（CAP/PROBE pills 立即可見）。
- **待 user**：①實機 4K 開 decisions.html 確認無橫捲 + 欄數；②MRVL/PANW/CRWD 卡確認 ⛔ CAP pill + tooltip；③下次跑 `分析 [TICKER]`（V3.45+ engine）後確認 Layer 3 內 Range/5D Band/Implied CAGR/Archetype 4 行 advisory 出現。

---

## ✅ Done (v4.9.0) — 市場氛圍頁重設計：決策漏斗 + 川普政策雷達

- mood.html/page-mood.js 重寫：判定帶（確定性公式 0 LLM）+ Market Brief 導讀 + 3 天趨勢/regime 時間軸/每日錨點 + 盤中即時（heatmap 聚合）+ 社群貼文 feed + 川普政策雷達（TACO lexicon + 辯論 verdict 掛載）+ 辯論訊號 + 產業排行。儀表移除。brief API `?history=1`、feed projection 加 final_take。server 已重啟。
- **待 user**：①開盤時段（美東 09:30-16:00）開 mood.html 確認 LIVE 模式：判定帶出現「盤面」分項、盤中區自動展開、3 分鐘輪詢。②判定權重/±0.15 門檻若要調，改 `page-mood.js` 頂部 `VERDICT_WEIGHTS_*` 常數即可。③川普雷達目前 48h 內僅非政策類帖文 — 等有 tariff/Fed 類帖文時確認高亮 + ⚠️ flag 正確觸發。

---

## ✅ Done (v4.8.0) — Break News V6：event clustering + 嚴格 gate + Market Brief

- `cluster.py` 事件聚類（0 LLM）：echo 不重辯、sentiment 類只計數、milestone 增量追辯；debater max_rounds 3→2 + gate 只認真衝突 + `single_voice`；`market_brief.py` 每 2h 1 call 產市場現況導讀（UI 頂部面板）。估 ~261 → ~60-75 call/天（▼70%+）。
- **待 user**：①重啟 dashboard_server（新 module + brief loop + 新 API）。②**codex CLI 壞掉**（probe rc=1 `Reading additional input from stdin...`）— 修好前 break news 辯論都走 single_voice；可暫改 `llm_config.json` break_news.secondary=claude。③跑幾天後覆核 `_state.json` 的 `items_echo_merged`/`items_sentiment_clustered` 與每日 call 數，視情況調 `BREAK_NEWS_CLUSTER_SIM`（0.55）/ `BREAK_NEWS_SENTIMENT_MIN_SCORE`（3）。

---

## ✅ Done (v4.7.0) — News Protocol V2.2：script-first triage 省 token

- Stage 1 接上 `stage1_triage.py` deterministic triage（LLM 禁讀 raw.json 全文）；Stage 2 bundle 每篇 cap 5000 chars；MD shallow 20→10；protocol 563→361 行。DIGEST ~110K → ~35-40K tokens、TRIAGE ~75K → ~5K。
- server `news` / `triage` prompts 同步改 script-first（修 triage `verdicts` shape 與 validator 衝突）。
- **待 user**：重啟 dashboard_server（PROTOCOL_PROMPTS 改動）；下次 DIGEST 覆核實耗 token + shallow snaps（script template）可讀性，不滿意可開 top-10 LLM refine。

---

## ✅ Done (v4.6.2) — 取消 LLM Fallback 機制

- 取消了 `scripts/_shared/model_router.py` 中的 LLM fallback，避免在指定的 LLM 或預設 primary LLM 出現 quota 不足或錯誤時，默默回退到不符預期的模型（如 claude）。
- 同步在 `scripts/break_news/poller.py` 中更新了 `_voice_order`，以及在 `scripts/break_news/llm_drivers.py` 中更新了預設與回退配置。
- 將 `config/llm_config.json` 的 `primary` 預設配置設為 `gemini`。

---

## ✅ Done (v4.6.0) — 工作流導向 Dashboard 三 phase

- Today 工作台（/api/today + today-panel.js）/ 產出閉環（5 報告 type + Ledger panel）/ 節奏自動化（ops_auto_loop + ▶ 一鍵）全上。
- **待 user**：重啟 dashboard_server（新端點 + auto daemon）；實看 index 三卡 / ops ▶ / decisions Ledger panel。
- **未來選項（明確此輪不做）**：earnings×2 / graph vs supply-chain / news×3 頁面合併瘦身。
- **kill-trigger v2 候選**（沿 v4.5）：sector RS 謂詞、ic-memo §11 條件同步。

---

## ✅ Done (v4.5.0) — Kill-Trigger Monitor + 稽核餘留批

- **Kill-trigger monitor 上線**：`scripts/kill_trigger_monitor.py`（0 LLM）每日重檢 Red Team 推翻條件 → `Dashboard/kill_triggers.json` + index.html 紅/琥珀 banner + daily Step 9.9。**待 user 實看 banner**（今日資料：0 triggered / 3 armed / 60 manual）。
- 稽核餘留全清：thematic in-process predict ✓、earnings fetch 並行 ✓、weekly_review weights_version ✓（+ per-version 報告段）、RSI 5→1 統一 ✓、technical_core 升 _shared ✓、MARKET_INDEX 重寫 ✓。
- ~~earnings-trade-analyzer 處置~~ → **已刪（v4.5.1，user 拍板）**；event index extractor 留（讀歷史 artifact）。
- **仍待**：
  - econ-calendar 修復（FMP legacy 403；連帶發現 `/stable/rating-historical` + `/stable/grades-summary` 也 404 — earnings bundle 的 rating_history/grades_summary 長期全零）。
  - ftd/market-top 三頭 lineage 整併（sector/*_yfinance.py ↔ skills 目錄 ↔ ~/.claude 路徑）。
  - kill-trigger v2 候選：sector RS 謂詞（需 sector_intel 數值欄）、predict 端 invalidation 接入、ic-memo §11 條件同步。

## ✅ Done (v4.4.0) — Skills 稽核修復批

- 7 真 bug（ic-memo crash / decision_lock 錯 ticker / T4 不可達 / news 新鮮度閘 / retail 比對 / flag 描述 / 2 份 SKILL.md lane 契約）+ 靜默失敗 5 處 + 殭屍刪除 + 效能 5 處 + cache prune。

## ✅ Done (v4.3.0) — 知識圖譜重構：theme hub-and-spoke + 聚焦模式

- CO_THEME clique（262/280 邊）→ ~30 個 theme hub + spoke，邊 −70%；點擊改 ego 聚焦（1/2 hop）；zoom 修復（user 動手後永不 auto-fit、移除每幀漸層特效）。
- **待**：user 實測點擊聚焦 / hover tooltip / 搜尋自動完成；若主題 hub 數量仍嫌多可把 per-ticker themes 取 top-1。

---

## ✅ Done (v4.2.0) — 產業掃描頁重設計：結論→辯論→證據

- sector_intel 先前被 bridge 丟掉的 2/3 產出全部上畫面：委員會 4 lane 投票矩陣、Red Team IF/THEN 推翻條件、量化證據熱力表（PE z1y / RS 多週期 / beat rate / insider / 情緒 / FRED×）、宏觀 overlay chips + 地緣風險。
- Today's Verdict hero 補上 sector.html（原 hidden stub）；heatmap 移頁尾。
- **待**：user 瀏覽器實看驗收；下次跑「產業掃描」後確認新區塊隨新 intel 正常刷新。

---

## ✅ Done (v3.40.8) — Market Mood scoring 修正

- mood page 並非沒更新；根因是 CNN put/call fallback 被當成 raw put/call 強訊號，讓頁面長期偏樂觀。
- 已將 CNN `put_call_options` proxy cap 到 ±50 並降權，新增 F&G internals quality（breadth/strength/junk bond demand）扣分。
- 今日重產後 `Dashboard/data.json.market_mood.mood.score = 2 Neutral`。

## ✅ Done (v3.40.4) — 短期雷達：產業趨勢榜可點 → 列出**完整**成分股（finvizfinance）

- radar 產業趨勢榜每列可點 → 彈 `#ind-stock-panel` 列該 finviz 產業**完整**成分股（含小中型）。
- server 新 `GET /api/industry/<name>` → `finvizfinance` Screener by-industry（免 key）+ 12h TTL 快取 + lazy import + 驗證。
- `page-radar.js` showIndustryStocks 主打此 endpoint，heatmap 當 fallback；chip 沿用 analyze-ticker-btn；`radar.html` 加面板。
- 效果：Comm Equip 7→44 / Solar 1→22 / 半導體設備 0→29。**user server 需重啟**才有新 route；需實點驗收。

## ✅ Done (v3.40.2) — 動能選股 Journal 統計區：中文化 + 點訊號→篩選 + unknown 說明

- Journal 統計區全繁中（i18n zh+en 補 8 key + renderStats）：標題後綴 / Filled / 等待20d / Signal 表頭 /
  量能 regime trend(vol_trend_map)+stage+空狀態。
- unknown：stages_map.unknown→「資料不足」+ 主表 stage cell hover 原因（歷史<200日）。sector 已「未分類」。
  根因：stage=MA NaN（technical_core.py:259）/ sector=不在三大名單（screen.py:409）。
- 點 by-signal 績效列（已按勝率降序）→ toggle 進主表 filter（複用 filter-chip 路徑）+ 捲動 + ✓/取消。
- 純前端、零後端。驗證 node --check / 200 / data.json stats 齊全。
- **待**：user 瀏覽器實點驗收；若主表/filter 另有英文殘留補圖再翻。

## ✅ Done (v3.40.0) — AI 辦公室翻案：自主多角色協作（砍掉 3.38 PTY terminal）

- **砍 3.38 PTY 路線**（破碎 + 方向錯）。改用既有 `llm_drivers`(`-p`) + `model_router`（日預算/cooldown/fallback）→
  零新增計費面、破碎問題根除。
- `scripts/office/`：`roles.py`（Lead/Critic/Verifier = claude/gemini/codex）、`store.py`（run 生命週期 + JSONL 事件）、
  `orchestrator.py`（round-robin 自動收斂 + Lead compose 交付物 + 合作式 stop）。
- server：`/api/office/{token,runs,run/<id>,run/<id>/stream(SSE),run(POST 202),run/<id>/stop}`，single-active 409、token+Origin gate。
- `office.html` + `page-office.js`：任務輸入 → 啟動 → SSE live 角色卡 → 交付物面板 + 歷史 replay。
- 全 stub/HTTP/SSE live test 綠。
- **待辦**：(a) ⚠️ **尚未對真 CLI 跑端到端** — 要實跑驗 agy/codex 吐得出可解析 JSON envelope（否則該角色 fallback 換引擎）;
  (b) 量真實 per-run 呼叫數/耗時/預算;(c) phase-2：mid-run interject、角色 YAML、多 run 並行。

## ✅ Done (v3.38.0) — AI 辦公室 · Claude member v1（Route A persistent PTY terminal，已於 3.39 移除）

- 新 `/office.html` xterm.js terminal viewport + 後端 PTY raw byte relay（spec `docs/office_claude_route_a.md`）。
- `scripts/office/`：`pty_session.py`（互動式 claude 無 -p / sanitize env / 無 MCP config / scrollback /
  resize / lifecycle / 日界 rollover）、`ws.py`（純 stdlib 手寫 RFC6455）、`preflight_smoke.py`（Gate1 auto + Gate2 billing 手動）。
- `dashboard_server.py` office routes（token mint / status / WS relay / message·resize·lifecycle）+ token+Origin gate。
- 側欄 `工具/OPS` group + `AI 辦公室` nav。全 HTTP/WS live test 綠（cat 替身）。
- **待辦/phase-2**：(a) ⚠️ **billing gate 未實測**（RFC §1，上線前須對真帳號跑 preflight Gate2）;
  (b) 尚未對真 `claude` 跑 preflight（只測過 relay）;(c) 多行 bracketed paste;(d) 乾淨 transcript parser;
  (e) Codex/Gemini member。

## ✅ Done (v3.37.0) — 新聞 digest 全面 zh-TW（補 bridge 缺口 + 自動翻譯 hook）

- 修 3.36 隱性 bug：`bridge.extract_news` 沒帶 `*_zh` → 翻譯到不了前端。已補 6 欄。
- `news/scripts/translate_digest.py`（agy 翻 deep verdicts，idempotent + CJK-skip）+ server hook
  （news/flash_text/flash/review rc=0 後自動翻、再 bridge）。
- 查證：每日 digest 本來就中文，只翻英文 straggler；CJK-skip 讓中文 digest ~0 agy 成本。
- Follow-ups:(a) link_digest 報告 MD 仍英文;(b) 翻譯無 cache;(c) sector_view/macro_view 已備 `_zh`
  但 news 卡未渲染;(d) en 語系下 native-zh verdict 仍中文（pre-existing）。

## ✅ Done (v3.36.0) — Link Digest zh-TW 在地化（gemini/agy 翻譯）

- `scripts/link_digest/translate.py`（agy EN→zh-TW，env-gated，非致命）+ build_artifacts 接 `*_zh`
  + page-news.js news 卡依語系渲染 `_zh || base`。實打 agy 驗過。
- Follow-ups:(a) 每日 **news digest 本身仍英文**（bull_case/arbiter）— 要全站中文化需改 `news` protocol
  或加共用翻譯 pass;(b) link_digest **報告 MD 仍英文**（只翻卡片結構化欄位）;(c) sector_view/macro_view
  已翻 `_zh` 但 news 卡沒渲染這兩欄;(d) 翻譯每次跑一次 agy call（~1 call/link_digest）— 量大可考慮 cache。

## ✅ Done (v3.35.0) — Link Digest（URL → 讀全文 + 上網找相關 → 判斷 digest → 報告/新聞/KG）

- News 頁 URL 輸入框 → `link_digest` protocol（claude turn，WebFetch+WebSearch）→ 4 視角辯論
  → 同時產 reports md + digest.json verdict + bn_*.json（KG entities+relations）。
- 新檔：`news/link_digest_protocol.md`（spec）、`scripts/link_digest/build_artifacts.py`（deterministic 寫手）。
- 改：dashboard_server 註冊、news.html/page-news.js/i18n.js UI。
- web-search 廣度耦合供應鏈 edge：relation 被 ≥2 源佐證 → support_count≥2 → Nexus directed edge。
- Follow-ups:(a) 還沒實跑一條真 URL（需 tokens；寫手 e2e 已驗 rc=0）;(b) link_digest 不 patch
  sector_intel/phase0（探索層）;(c) 早於 morning news DIGEST 寫 bn 時，news run 會覆寫 digest.json（KG 不受影響）;
  (d) judgment.json `<id>` 由 LLM 命名，build_artifacts 不強制檢查 id 一致性（容錯）;(e) 可考慮 link_digest
  也吐到 trader-memory thesis registry / decisions（目前只到新聞層）。

## ✅ Done (v3.34.0) — Narrative Pulse 完整退役

- 提前退役(週末無新 sample):刪 daily `step9_narrative()`、server `/api/narrative-pulse/*`
  + SCRIPT_PROTOCOLS、`Dashboard/narrative_pulse.json`、整個 `skills/narrative-pulse-detector/`。
- 副作用:mood.html 每產業「散戶量能」label 恆 `calm`(retail aggregate.py 的 legacy NPD
  fallback 缺 cache → graceful;主 composite 不受影響)。
- Follow-ups:(a) 可順手清 `retail-sector-pulse/aggregate.py` 的 `load_npd_cache_for`/
  `aggregate_retail_volume` + SKILL.md 對 narrative 的 doc 引用(無害留著);(b) style.css
  殘留 `npd-*` class 可清。

## ✅ Done (v3.33.0) — 退役 Narrative Pulse UI + 移除散戶視角 + index 產業趨勢 mini

- index Zone B「Narrative 焦點」→ 真實「產業趨勢」mini(`renderIndustryMini`,讀
  `data.industry_trend`);移除 index 內 narrative fetch IIFE。
- radar 刪 `#npd-section` + page-radar.js NPD IIFE 死碼;刪散戶視角 `#radar-retail-sector-pulse`
  + page-radar.js retail 全套 + render 呼叫 + tooltip。mood.html 接手散戶,不受影響。
- 保留 narrative generator + server route + json(觀察期到 2026-05-31)。
- Follow-ups:(a) 觀察期 5/31 過後可決定整 feature(generator+route+json)退役;(b) index
  產業趨勢 mini 目前固定 perf_1w,可考慮跟 radar 一樣加區間 toggle;(c) style.css 殘留
  `npd-*`/`rsp-*` class 無害,日後可順手清。

## ✅ Done (v3.32.0) — Dashboard 4-zone 重構 + AI 裁決漸進揭露 + 今日焦點改造

- **index.html 4-zone**:9 stack → Zone A 指令 / Zone B `#signals-band` 3-up(合併 3 薄 strip)/ Zone C teasers / Zone D action;Structural Watchlist body 摺疊。所有依賴 ID 保留。
- **decisions.html AI 裁決卡片**:V5/Red Team/進場條件 `<details>` 漸進揭露 + Model Score 降階 + risk cap 4 + mobile grid。卡片 >800px → 大幅縮短。
- **今日焦點**:判斷=真訊號但 framing 誤導 → Top 3 + 過熱守衛 + 中性 CTA + graceful empty。
- Follow-ups:(a) decisions badge row 多 badge 仍可能 wrap,本次未 cap(保留 tooltip 綁定),需要再做 `<details>` 收納;(b) index 可考慮把 teasers + recent 進一步左欄 stack 成真 2-col(本次保留 full-width 3-up 避免左欄過擠);(c) 今日焦點守衛閾值(RSI80 / Stage3)hardcoded,日後可移 config。

## ✅ Done (v3.31.0) — 個股動向 row 可點 → inline 動能明細 + K線

- `renderStockDetail()` + `_miniSparkline()`:點 row/弱中強 chip → 區塊下方展開明細
  (30日 score sparkline + 均線排列 + RSI/MACD/RS/距高 + signals/warnings) + 看 K線
  + 完整分析 button。純讀既有 `momentum_screen` row + `history_by_ticker`,零 backend。
- Follow-ups:(a) 明細卡的「完整分析」走 protocol queue —— 留意 cost;(b) sparkline 目前
  只畫 score,可考慮加 price overlay;(c) 仍受 momentum_screen ~529 宇宙限制(小型題材股
  漏,見 v3.30 follow-up)。

## ✅ Done (v3.30.0) — 短期雷達「個股動向」panel

- radar 新 `#radar-stock-movers` 區塊 + `renderStockMovers()`:對稱領漲個股↔走弱
  個股 + 🔥強勢產業中走弱 strip。純讀既有 `data.json.momentum_screen.rows[]`
  (Weinstein stage + RS + warnings),零 backend 改動。
- 走弱判定用「Stage3/4 OR WEAK/BEARISH」(非 RS<0,避免強 SPY 盤誤標 80% 宇宙);
  弱中強用 `sector_rs_rank≤3`。
- Follow-ups:(a) momentum_screen 宇宙 ~529 (sp500/n100/sox/watchlist),小型題材股
  (含部分光通名)可能漏 — 要更廣需擴 universe 或補 thematic theme laggard_movers;
  (b) 可考慮點走弱股 drill 出 K 線 / 動能細節 (radar 已有 kline panel 可重用);
  (c) sector 縮寫對映 momentum_screen 用 GICS 名,`_SECTOR_ABBR` 是 finviz 名,部分
  GICS sector (Information Technology/Health Care/Financials) 落 fallback slice(0,4),
  顯示堪用但未完全在地化。

## ✅ Done (v3.29.0) — 短期雷達改用真實近期趨勢

- radar headline 改「產業趨勢榜 領漲↔領跌」(`#radar-industry-board` +
  `renderIndustryBoard`):真實 finviz 產業 trailing perf (theme-detector cache
  `industry_rankings`,既有但棄置) + 1週/1月/3月 toggle + 11-sector uptrend strip。
- theme card 顯示指標 forward `bullish_breadth_pct` → 真實「真實上漲率」
  (`trailing_breadth_5d_pct`) +「中位漲幅」(median 5d) + 看多/看空 badge。可看空。
- `predict.py` 加 `trailing_return_5d_pct/_20d_pct`;`screen.py` 加 `trailing` 區塊;
  `bridge.py` 加 `load_industry_trend()` → `data['industry_trend']`。
- Narrative Pulse 從 radar UI 隱藏 (`NPD_RADAR_ENABLED=false`),generator 保留。
- Follow-ups:(a) theme-detector cache 非每日強制重跑 (≤7天舊),趨勢榜目前帶
  freshness badge — 若要每日新鮮可在 daily Step6 強制 refresh;(b) Narrative Pulse
  觀察期 2026-05-31 到期後決定 generator 去留 (見 memory project note);(c) laggards
  排序目前 client 端按 active horizon,bottom list 來源是 momentum_score blend。

## ✅ Done (v3.28.0) — Market Mood 市場氛圍 page

- New page `mood.html`/`page-mood.js`: hero composite gauge + options/VIX-SKEW/F&G
  tiles + retail hot-stock strip + sentiment-first sector grid.
- `mood.py` → `market_mood.json` (VIX term structure + SKEW + put/call + F&G 7 subs).
- StockTwits social source + wider subreddits → retail coverage 41→110 posts/day.
- bridge merges `market_mood` + slim `tactical.trending`; daily step 9.3.
- Follow-ups: CBOE put/call CDN is 403-blocked (using CNN put_call sub-index
  proxy) — revisit if a clean market-wide put/call feed becomes available; wire
  StockTwits native Bull/Bear tag into trending_tickers polarity (currently in
  meta only); FMP per-stock putCallRatio corroboration tile (deferred).

## ✅ Done (v3.27.0) — Pre-Market Pipeline Redesign (FMP 250/min)

- Central cross-process FMP rate pool `scripts/_shared/fmp_pool.py`
  (flock sliding-window @ 220/min; `get`/`get_url`/`fetch_many`/`acquire_slot`).
- All 6+ FMP clients delegate pacing to the pool (300ms throttles removed,
  signatures/caches unchanged); supply_chain + dashboard count via `acquire_slot()`.
- `daily_update.sh` FMP lane parallelized (thematic ∥ momentum), workers 6→20/16.
- Morning brief `scripts/premarket/morning_brief.py` → `reports/PREMARKET_<DATE>.md`
  (step 9.8). §3 movers ranks the curated mega-cap universe (SECTOR_UNIVERSE,
  131 names, price≥$5) — drops the noisy market-wide biggest-gainers feed.
  Follow-up: optional `--llm` narrative summary.

## 📋 Open

- [ ] **[V325.X-ICMEMO-PHASE-A5] IC Memo peer_descriptor LLM swap** — replace
  the V1.0 stub at `skills/ic-memo-writer/scripts/fetch_peer_descriptor.py`
  with a real Haiku 4.5 one-shot batch call (~5-10 peers per prompt). Output
  per-peer `{focus_area, market_share_note}` written to
  `skills/ic-memo-writer/cache/peer_descriptor/<T>.json` with `status: ok`,
  TTL 14d. Trigger only when shipping/testing on 3-5 real tickers shows the
  §4 ticker-only peer table is genuinely unhelpful. Keep the shared
  `_shared/cache/` deterministic — LLM output stays in the skill's own
  cache directory.

- [ ] 🟡 **[V325.X-ICMEMO-PHASE-B] IC Memo Dashboard view（部分完成）** — `Dashboard/stock-detail.html`
  that renders the latest ic_memo MD + live FMP quote + 6-anchor bar chart
  + peer comp click-through (Nexus graph integration optional). Wait for at
  least 3 successful IC Memo runs on real tickers before designing the
  layout — current Dashboard pages tend to over-fit early use cases.
  **Partially superseded by V3.26.0 Reports Center** (`/reports.html` now
  renders IC memo MD with verdict badge + decision_lock chip + degraded
  banner + TOC). Remaining scope: live FMP quote refresh + 6-anchor bar
  chart + peer click-through.

- [ ] **[V322.X-MOM-PR2] Momentum Fundamentals PR2** — follow-up slice of
  the V3.22 fundamentals layer. Adds: ATR-normalized Gap Up detector
  (`gap_pct >= max(2%, 0.5 * ATR14 / close)` + `open > prev_high` confirm),
  `Catalyst Gap-Up` preset, sector-relative P/S percentile column,
  optional Pocket Pivot detector. Plan to ship after 1-2 weeks of PR1
  screen output so the GM% / P/S thresholds in Value Momentum can be
  calibrated against actual hit rates.

- [x] **[V321.X-ROUTER] Model router 5hr-window counter** — 4.84.0 完成。
  `call_timestamps[]` + `window_max_calls`/`window_hours`（claude 120/5h、
  codex 80/5h；gemini/grok 是 per-minute rate limit 不設 window）。與 daily
  budget 兩道獨立閘，headroom 取較緊者。**時間戳不隨 UTC 換日歸零**——session
  window 不理會午夜。順手修 `load_llm_config()` 白名單漏掉新 budget key（cap
  原本完全不生效）。

- [x] **[V325.X-PE-WARMUP-RETRY] heatmap PE warm-up should retry on failure** —
  4.85.0 完成。失敗不進快取（既有好值原地保留）、部分成功保留、殘餘下輪補抓、
  指數 backoff（5 分→1 小時）、429 熔斷不計失敗批次、loop 內補呼叫 warm-up。
  實測比 TODO 描述更糟：`_fetch_pe_ttm` 在熔斷期回傳全 None 的 **dict**，通過了
  `isinstance(v[1], dict)` 檢查，於是失敗值被當事實**蓋掉既有好值**。已改為回
  `None`。`scripts/backfill_heatmap_pe.py` 手動救援保留但常態不該再需要。

## ✅ Recently Completed

> 完成項詳見 `CHANGELOG.md`（version history 權威來源）+ 頂部「✅ Done (vX)」區塊；更舊細項見本檔末「📦 已完成任務詳情」。此區先前逐條 [x] 清單與上述兩處重複，已整併移除。

---

## 🎯 活動 Backlog (Pending)

### 路線 EXP — Forward Expectations Engine（未來營運預測 → 預期估值）

> **目的**：讓 AI Investment Committee 能回答「未來價值由什麼驅動、目前市場已反映什麼、委員會與市場差在哪、哪些未來數據能驗證 thesis」，而非只用 trailing 財務數據外推。
>
> **治理原則**：shadow-first；初期不得修改 live `fair_value_summary`、`decision_lock`、買進門檻或部位 sizing。所有預測必須保存 point-in-time 來源、時間戳與假設，不得虛構 TAM、guidance 或 analyst estimate。
>
> **既有零件優先復用**：`earnings-analyst` 的 8Q 財報／segment／transcript／annual estimates、`earnings-valuation-forecaster` 的 12M forecast、`compute_implied_expectations()` reverse DCF、archetype 與現有估值錨。

#### 🩺 系統健康度快照（V4.30.0 code review）

> 治理層 A（shadow-only / evidence contract / same-metric gate / immutable ledger / 0-LLM / 19 golden test 全綠）。
> **交付層 C→B（V4.34.0）**：P0 robustness gate (R1~R4 + 0.4 + 1.2) 全清。`future_price_range` 套套邏輯已破（接歷史 multiple regime），scenario 分歧度 evidence 化，成功標準 gate 上線（現況 insufficient_evidence、shadow→live 仍誠實擋住，待樣本累積）。EXP-4.5 升 live 前須 `success_criteria` verdict=pass + user 批准。
>
> 已知致命/重大問題（review 實測 ARM base +0.0% / NVDA base +0.0%）：
> 1. ~~**套套邏輯**：無 explicit forward multiple 時 base target ≡ current price~~ → **✅ V4.31.0 EXP-R1 修復**：接歷史 multiple regime anchor（price-independent），無 anchor 時誠實標 advisory band。
> 2. ~~**bridge 凍結 margin/share**~~ → **✅ V4.32.0 EXP-R2 修復**：揭露 held-constant 假設 + terminal sensitivity（margin±20% / share±10% 彈性）。
> 3. ~~**scenario 固定 ±10% step**~~ → **✅ V4.33.0 EXP-R3 修復**：bear/bull 改由 consensus low/high envelope 推導，缺 dispersion 即降級，不捏造固定 step。
> 4. ~~**inf/NaN 序列化**~~ → **✅ V4.30.1 EXP-R4 修復**：全線 `allow_nan=False` + 除法 guard + safety test。
> 5. **覆蓋率**：只有 `royalty_ip` 1 個 adapter，僅 ARM 走得通 independent lane；其餘 ticker 全掉回 consensus + 套套邏輯 band。→ P1 EXP-3.1
> 6. **全部 uncommit**：~4363 行 / 17 script / 16 test 零 commit，工作區已 bump 4.30.0。→ EXP-R0

#### 🔴 P0 — Robustness Gate（必須全清才可談 shadow→live；engine 變更後跑對應 golden test rc=0）

- [x] **[EXP-R0] 落地 commit 現有未來估值系統** — V4.30.0：2 commit（`fad6359` engine+adapter+16 test+2 schema / `f9c55bb` version+protocol+TODO），runtime ledger 不入 git；無關 dashboard 改動未動。
- [x] **[EXP-R1] 打破 derived-band 套套邏輯（致命）** — V4.31.0：新增 `forward_expectations_multiple_anchor.py` 自身歷史 multiple regime（FMP `ratios` annual P/E/P/S/P/FCF，price-independent；dispersion ≤3.0 gate）。倍數優先序 explicit → historical → derived；只剩 derived 時 status `advisory_band_only` + warning + CLI ⚠️ disclaimer。ARM `--fetch` base 由 ≡現價 變 forward EPS×歷史 P/E（實測 base $870 vs 現價 $402）。**Tier2 peer forward P/E 暫緩**（N peer × estimates 太重），無歷史/no-fetch 時誠實降級 advisory band。
- [x] **[EXP-R2] forward bridge 假設透明化 + 敏感度** — V4.32.0：bridge 加 `assumption_basis` + `held_constant_assumptions`（逐項揭露 margin/fcf/capex/share/tax 皆 held-constant）+ `terminal_sensitivity`（net-margin ±20% / share ±10% 對 net income/EPS 彈性，標 `illustrative_elasticity_not_a_scenario`）；report 同步呈現給人讀。`eps_implied_net_income` vs `net_income_from_margin` 既有 consistency check 保留（V4.23）。
- [x] **[EXP-R3] scenario driver step 改由 evidence 決定** — V4.33.0：builder v2.0 移除固定 ±0.05/±0.10 step；bear/bull 改由 consensus 營收 low/high envelope 推 CAGR band（真 dispersion）。driver-level driver 無 per-driver dispersion evidence → `base_operating_drivers_held`（揭露不捏造）。缺 evidence dispersion（無 2-row 跨度/無 low<high）→ 降級 qualitative + 標 `no_evidence_based_dispersion_for_scenario_spread`。test 26→33 asserts。**未做**：guidance-range 直接當 driver dispersion 來源（目前只用 consensus envelope）+ price_range 倍數壓縮 scenario（ARM $870 過樂觀，留待 forecast-to-valuation EXP-3.4）。
- [x] **[EXP-R4] 數值安全：除零 + NaN/Inf** — V4.30.1：12 script data-output `json.dumps` 全加 `allow_nan=False`（NaN/Inf 序列化即 fail-fast）；確認 `gap._compare`（`right_value not in (None,0)`）、scenario `change_vs_base`（`if value`）、`_ratio_upside`（`_pos` 現價）、bridge margin（`_pos` revenue / tax `<=0`）除法均已 guard；新增 `test_forward_expectations_numeric_safety.py` 15 asserts 覆蓋 0/負分母/零現價/零 EPS。
- [x] **[EXP-0.4] 定義成功標準（前置 gate）** — V4.34.0：`forward_expectations_success_criteria.py` 8 條 falsifiable criteria（sample/WAPE≤0.30/directional≥0.60/|bias|≤0.20/explainability/source/gap/非估值膨脹）+ `shadow_to_live_gate`（僅 pass 為 true、且必要非充分）。實測 n=3<15 → insufficient_evidence、gate False。19 asserts。
- [x] **[EXP-1.2] 修正 consensus 被歷史方法壓制** — V4.34.0 驗證：現設計 matrix 已把 consensus 與 base_rate 分欄，divergent base-rate median 不覆蓋 consensus，只並列為 comparator。補 falsifiable guard test（core 45→48 asserts）。

#### 🟡 P1 — 覆蓋率與 driver 深度（P0 清完後）

- [ ] **[EXP-3.1] 建立 business-model driver template library** — V4.15.0 `royalty_ip`（ARM）+ **V4.36.0 `semiconductor`**（NVDA/AMD/MU end-market driver tree，刻意讓 royalty 給 royalty_ip，30 asserts）。**待擴**：SaaS（MSFT/ORCL/NOW，ARR/NRR/Rule-of-40）、銀行（NIM/loan growth/credit）、零售、工業。非 adapter 命中股仍靠 consensus + 歷史 multiple regime（V4.31.0，已非套套邏輯）。
- [x] **[EXP-3.2] 建立 Base-rate cohort library** — V4.35.0：`forward_expectations_cohort.py` 依 sector(exact)+growth/margin/size(±1 tier, ≥2/3) 選 cohort，記錄 criteria/tolerance/每名 match reasons（防 cherry-pick）。`base_rate_lane` 改用 cohort（fallback raw peers），近乎零額外 fetch。ARM→9 名 Tech cohort median 0.135。23 asserts。**未做**：cross-sector supply-chain cohort、cohort 隨時間 drift 追蹤。
- [ ] **[EXP-2.1] 擴充 ARM driver tree** — V4.20.0 已能 discovery + opt-in 下載 allowlisted SEC filing 正規化文字 → promotion gate；待擴 filing 內 ARM driver pattern（units / rate / license conversion / data-center exposure）。
- [ ] **[EXP-2.2] 產生 Consensus／Independent／Base-rate 三條 3–5Y lane** — 每條保留獨立假設、輸出與信心，不先 blend 成單一數字。
- [ ] **[EXP-1.1] 補齊資料 inventory 介面** — 待接 structural shift、12M forecaster 與 implied expectations（其餘來源 V4.21.0 已串）。
- [x] **[EXP-3.4] forecast-to-valuation mapping（倍數壓縮）** — V4.38.0：`forward_expectations_multiple_compression.py` 成長分級壓縮歷史 regime（factor × historical + P/E 絕對上限等比例縮放）。consensus CAGR 低 → 倍數收斂 mature。實測 NVDA $776→$298 base、ARM $870→$317。流入 L1 卡。
- [x] **[EXP-3.4b] Margin 正常化 path** — V4.39.0：`forward_expectations_margin_normalization.py` durable-platform retention（bear 0.62/base 0.80/bull 1.00，非 sector 均值回歸），>40% margin 才觸發 + own-history floor 保護平台 franchise。EPS path 用 normalized EPS。實測 NVDA held 60%→37/48/60%，**base $252(+21%)/bear $115(-45%)/bull $473(+126% tail)**（user 校準後目標 $220-260 命中）。18 asserts。**未做**：adapter-specific 估值法選擇；margin path 與 R2 sensitivity 整合成單一 driver 樹。
- [ ] **[EXP-3.5] 延後 full forward DCF 自由假設模型** — Independent lane 校準前不加大量成長期 / margin normalization / terminal multiple 自由參數。

#### 🔵 決策中心整合（L1 done / L2 gated）

- [x] **[EXP-INT-1] L1 advisory 顯示** — V4.37.0：`bridge.py load_forward_outlook()` 掛 `forward_expectations` 到決策 item（option b auto-fetch + TTL + budget），`page-decisions.js` Layer-3 加 Forward row（FORECAST/⚠advisory badge + shadow-only）。純顯示，**不**進 score/verdict/blend/sizing。
- [ ] **[EXP-INT-2] L2 接決策（gated，禁現在做）** — forward 進 fair_value blend / 改 verdict / 改 sizing。前提全清才可：`success_criteria` verdict=pass（需 EXP-4.4 樣本 ≥15 + EXP-2.x independent lane 真 available）+ EXP-4.5 升級報告 + **user 批准**。先以 risk-flag 形式（如 forward gap 過大→⚠），不直接動 sizing。

#### 🟢 P2 — 校準與上線門檻（P0+P1 清完後）

- [ ] **[EXP-4.4] 設定最小驗證樣本** — ARM pilot 通過後擴至不同 archetype；樣本不足不得宣稱某 lane 優於現行系統。
- [ ] **[EXP-4.5] 提出 shadow → live 升級報告** — 比較現行估值、Forward Expectations shadow、翻轉率與實際預測誤差；**前提：EXP-R1~R4 + EXP-0.4 全清**；僅在 user 批准後接入 live。

#### ✅ EXP 已完成（V4.14–4.30；歷史紀錄）

- [x] **[EXP-0.1]** schema：同口徑 matrix + evidence contract + source lineage + freshness + unknown rejection（V4.14.0）
- [x] **[EXP-0.2]** 三 lane 角色 + 禁混合規則（FCF／EPS／營收 CAGR 不互減）（V4.14.0）
- [x] **[EXP-0.3]** shadow 輸出 + live 升級治理（V4.14.0）
- [x] **[EXP-1.3]** management guidance 結構化抽取（range 保持 range）（V4.20.0）
- [x] **[EXP-1.4]** analyst estimate revision snapshot（單 cache 標 `delta unavailable`）（V4.21.0）
- [x] **[EXP-2.3]** 簡化 forward financial bridge（⚠️ 見 EXP-R2 凍結假設問題）（V4.23.0）
- [x] **[EXP-2.4a]** operating-driver scenario builder shadow（⚠️ 見 EXP-R3 固定 step）（V4.27.0）
- [x] **[EXP-2.4b]** Royalty/IP driver-level scenario cases（V4.28.0）
- [x] **[EXP-2.5]** Expectations Gap shadow scaffold（同口徑比較）（V4.24.0）
- [x] **[EXP-2.6]** shadow report renderer `forward_expectations_report.py`（V4.25.0）
- [x] **[EXP-3.1a]** Sector／Supply-chain Transmission Graph gate（V4.15.0）
- [x] **[EXP-3.3]** scenario 約束 + 缺資料降級規則（policy gates）（V4.26.0）
- [x] **[EXP-3.4a]** shadow future price range mapper（⚠️ 見 EXP-R1 套套邏輯）（V4.29.0）
- [x] **[EXP-3.4b]** ticker → future price range 驗收入口 `forward_price_range.py`（⚠️ 同 R1）（V4.30.0）
- [x] **[EXP-4.1]** point-in-time Forecast Ledger（UTC run_id + exclusive-create）（V4.14.0）
- [x] **[EXP-4.2]** 財報後 actual vs forecast scaffold（V4.22.0）
- [x] **[EXP-4.3]** 校準指標 scaffold（WAPE proxy / directional / `insufficient_sample`）（V4.22.0）

#### EXP 明確非目標

- 不把 analyst price target 同時當作預測輸入與成功驗證標準。
- 不以調高成長股 fair value 為成功；高估、低估或資訊不足都必須能被誠實輸出。
- 不在 EXP 初期混入 anchor eligibility gate、live blend 權重修改或 CV 校準；這些維持為獨立估值治理工作。

### 路線 RSP — Retail Sector Pulse 後續

- [x] ~~**[RSP-1] 擴 NPD universe 含 SECTOR_TOP_5**~~ — 廢棄：依賴 narrative-pulse `batch_scan.py`，該 skill 已於 v3.34.0 整套退役/刪除，項目無效。
- [ ] **[RSP-2] V3.21 — Intraday 4h refresh daemon** — dashboard_server.py 加
  daemon thread 每 4h 重跑 `aggregate.py`。沿用 break_news daemon pattern。
  V3.20 跑 1-2 週後評估必要性再做。
- [ ] **[RSP-3] V3.22 — LLM-enriched framing** — Haiku 4.5 對 rule-based
  framing 做一句潤色(11 call/day,~$0.01)。權衡:LLM dependency vs 自然語感。
- [ ] **[RSP-4] V3.23 — Per-sector FTD pattern** — sector ETF (XLK/XLF/...)
  FTD state machine,類似 SPY ftd_yfinance.py。 sector 級 "follow-through
  day" 信號。
- [ ] **[RSP-5] Weekly review hit rate** — `scripts/retail_sector_pulse_review.py`
  比 composite_score 預測方向 vs 後續 5d sector ETF 實際 return,計算 IC。

### 路線 NP — Narrative Pulse V1.1 後續 ⚪ 整路線廢棄

> narrative-pulse-detector 已於 **v3.34.0 整套退役/刪除**（skill 目錄、generator、route、snapshots 全清；memory 註記「勿重啟」）。以下三項全讀已不存在的檔，永久無效。

- [x] ~~**[NP-1]** Dashboard hover tooltip（prob/target breakdown）~~ — radar NPD UI 已清。
- [x] ~~**[NP-2]** 5/31 review script（讀 narrative-pulse snapshots）~~ — 目錄已刪、不再產 sample。
- [x] ~~**[NP-3]** Stage 2/4/5 adjustment 校準~~ — feature 不存在。

### 路線 BN — Break News source expansion

- [ ] **[BN-1]** Optional paid/token adapters：X recent search / Product Hunt / official Google Trends API alpha。只在 user 提供 token 或明確接受成本後接入。
- [x] **[BN-2]** ~~Stocktwits adapter~~：V3.40.7 移除（噪訊比過低，~5% 才成 primary source）。改補 Fed Press / Nasdaq Markets / Benzinga RSS。
- [ ] **[BN-3]** Social source quality backtest：比較社群 raw item 被手動辯論後的 verdict hit-rate，調 `BREAK_NEWS_SOCIAL_GATE_MIN_SCORE`。

### 路線 V20 — V2.20 規劃 ⭐ 焦點

**前提**：V2.18 (Structural Shift Modulation) + V2.19 (Lane Cross-Talk Wiring) + V2.19.1 (Watchlist Archival) + V2.19.2 (UI ⚡ + Backtest forward returns + Theme heat bonus) 已完工。下一階段 **聚焦 UI 補齊 + Backtest 深化**，**不搶做需 backtest 結果的功能**。

#### V2.20.0 — 1-2 週可做（低風險）

##### A. UI Decision Layer 完整化

- [x] **[V20-A1]** Polarization 4-tier badge in `decisions.html` — **更早版本就已做掉**（badge + `SIGNAL_TIPS` 皆在；`ALIGNED` 刻意不發 badge，同 `macro_alignment` 慣例）。4.83.0 改吃 A5 的攤平欄位
- [x] **[V20-A2]** Red Team basis badge in `decisions.html` — **更早版本就已做掉**（`unclassified` 刻意不發 badge）。4.83.0 改吃 A5 的攤平欄位
- [ ] **[V20-A3]** structural_shift tier badge in earnings card (`page-earnings.js`) — CANDIDATE/CONFIRMED 視覺化
- [ ] **[V20-A4]** Theme-detector structural_shift override icon in `sector.html` — `tier_counts` 已寫進 theme JSON
- [x] **[V20-A5]** `bridge.py` 加 polarization / red_team_basis 注入 `recent_analysis[]`（4.83.0）— 不只是省一層 `.det_shadow`：renderer 原本只讀 shadow，V5.1+ entry 的決策時真值（`calculation_steps`）沒被看到。附 `*_source` / `*_disagrees` 與兩個 SPLIT badge

##### B. Backtest 深化（先補分析維度，accrual 等不及）

- [ ] **[V20-B1]** Random sector baseline 對照 — 現在 alpha vs SPY 看起來好 (+18.4% mean) 但可能只是 Memory Semi sector momentum，需 random 同 sector 5 ticker baseline 驗證 watchlist 真的 outperform
- [ ] **[V20-B2]** Per-keyword breakdown — 14 個 keyword 哪幾個是 noise (e.g. "supply tight" 通用)？哪幾個是 signal (e.g. "supercycle" 罕見)？砍 noise 提訊噪比
- [ ] **[V20-B3]** Per-credibility 切片 — HIGH 命中 alpha vs MEDIUM 有差嗎？沒差 → credibility 是 false signal
- [ ] **[V20-B4]** Time-window sweep — 5d/15d/45d/90d 哪窗 alpha 最高 → 決定 optimal hold horizon

##### C. Decision Logic 小修

- [ ] **[V20-C1]** Dynamic decision threshold — BUY≥1.2 / STAGED≥0.8 是死的。CONFIRMED + ALIGNED → BUY 降到 1.0；BIPOLAR + chaotic → BUY 拉到 1.5
- [ ] **[V20-C2]** (可延後) Lane freshness weighting — News 48h vs Earnings 80d 同權重不對；lane cache mtime > N 天 → confidence ×0.8

##### D. UX 補齊

- [ ] **[V20-D1]** Watchlist tile 顯示 lifecycle 軌跡（first_seen / 已 graduated / evicted）— 給 user 一目了然每個 watchlist ticker 軌跡
- [ ] **[V20-D2]** `backtest_watchlist.py` 加 `--dry-run` flag

#### V2.20.X — 3-4 週後可做（需 watchlist accrual）

##### E. Backtest 真實驗證（必須等 lifecycle log 累積）

- [ ] **[V20-E1]** lifecycle ≥ 30 events，覆蓋 ≥ 3 sector → 跑完整 backtest 驗 signal 非 lookback bias
- [ ] **[V20-E2]** ≥ 5 個 evicted_no_graduation 樣本 → 算 false positive rate；rate > 50% → 砍 keyword whitelist 或廢 watchlist 概念
- [ ] **[V20-E3]** ≥ 3 個 自然 graduated_confirmed → 算真 lead time（不是 lookback 假 17 天）

##### F. Phase 5.5 Cross-Protocol Wiring

- [x] **[V20-F1]** `thesis_registry` concentration check — Phase 4 sizing：同 sector ≥3 active CONFIRMED → 第 4 個減半。防 sector concentration risk（4.82.0 隨 `trade_plan_builder.py` 落地；registry 不可得時標 `source=registry_unavailable` 不當作 0 部位）
- [ ] **[V20-F2]** Sector protocol 讀 thesis_registry 反向加權 — `sector_intel.json` 加 `active_thesis_count[sector]`，下次 sector 跑時 sector heat 拉

#### V2.21+ — 大改，**不要塞 V2.20**

- [ ] **[V21-G1]** News provisional → 直接驅動 tier modulation — 必須先 V2.20.X backtest 證明 watchlist signal 質量
- [ ] **[V21-G2]** Modulation 參數 auto-calibration（V2.18 ×0.3 PT / 0.5 RT 折半 / 0.95 floor / 50% cap 全是猜）— 需 backtest sample n>50
- [ ] **[V21-G3]** macro_multiplier sector × duration sensitivity matrix — 5+ 年 macro/sector data + multicollinearity 處理，**不是兩週工作量**
- [ ] **[V21-G4]** Position size 連續 sizing（取代 binary tier cap）— 需 G2 結果
- [ ] **[V21-G5]** Phase 3 Step 1.5 + 1.7 modulation cap 改 backtest 校準值 — 需 G2

#### 紀律提醒

1. **V2.20 不能塞 News provisional → tier modulation**（G1）— V2.18+V2.19 anti-spoofing 鐵律寫過：未經 backtest 驗證的 leading signal 不能進決策層
2. **V2.20 不能搶 parameter calibration**（G2）— sample 不足會把噪音當 signal 寫進公式
3. **V2.20 焦點 = UI surface + backtest signal 拆解**

### 路線 H — thematic-screener v0.3 enrichment 後續
- [ ] **[H-1]** Backtest v0.2 vs v0.3：過去 30d/60d 推薦在 5d realized return / hit-rate 上差異
- [ ] **[H-2]** 加 Finnhub `/stock/recommendation-trends` 補充 grades-historical（更詳細買賣評等 distribution）
- [ ] **[H-3]** 加 short interest / days-to-cover label（目前只用 quality 不看 short crowding）
- [ ] **[H-4]** Tune `enrichment_multiplier` 加成係數 — 目前憑直覺設（earnings ×0.5 / quality ×0.6 / insider ×1.3 等），backtest 後校準

### 路線 G — FMP catalog 二階強化（v2.11.0 後續）
- [ ] **[G-1]** theme-detector 切 FMP-primary：`theme_detector.py:479` import 改 `fmp_industry_perf_client` 為主、`finviz_performance_client` 為 Tier C fallback。先 user review `skills/theme-detector/scripts/industry_name_mapping.yaml` accuracy。
- [ ] **[G-2]** FMP industry rolling perf 多週期 (1m/3m/6m/1y/ytd) — 改用 `historical-industry-performance` per industry 取代每日 snapshot 累積（API call 從 ~252 降到 ~128，且支援 compound 而非 sum）
- [ ] **[G-3]** sector-analyst overlay 進 sector_protocol Phase 4 估值面 rubric — 目前 `fmp_overlay` 只是輸出，未進決策邏輯
- [ ] **[G-4]** 71 finviz-only industries 二次審視 — Internet Retail / Department Stores / Confectioners / Beverages-Brewers / Textile / Pharmaceutical Retailers 等可能 FMP 用其他名稱包進去（如 "Software - Services" 包 Amazon？）
- [ ] **[G-5]** technicalIndicators FMP 整合 — momentum-monitor + technical-analyst 改吃 FMP RSI/SMA/EMA/ADX 直接結果，省 OHLC fetch + 跨 skill 一致性
- [ ] **[G-6]** commitmentOfTraders macro overlay → sector Phase 0（期貨籌碼信號目前完全空白）
- [ ] **[G-7]** marketHours 預檢 → `daily_update.sh` 跳過 NYSE 假日（目前盲跑）

### 路線 F — Finnhub 整合
- [ ] **[F-PR4]** `skills/data-client/`：按資料種類路由 provider（market→Finnhub / financials→FMP / events→Finnhub-only / econ→FMP-only），加 `_source` tagging + conflict detection
- [ ] **[F-PR5]** 遷移 `ftd-detector` 到 data-client（最低風險 pilot）
- [ ] **[F-PR6]** 遷移 `market-top-detector` + `us-stock-analysis`
- [ ] **[F-PR7]** 啟用新功能：`earnings-calendar` skill 修好（Finnhub `/calendar/earnings`）、`pead-screener` 啟動（`/stock/earnings` surprise）、新增 `insider-monitor` skill

### 路線 B — Calendar 頁面（事件日曆補充與自動化）
- [ ] **[B-DAILY]** `daily_update.sh` 加 Step 7：跑 indexer + render markdown

**Upcoming events feeds — 補充事件源（Tier 2 & 3）**
- [ ] **[B-FEED-OPEX]** Options expiry calendar（每月第三個週五 + quarterly）→ 純算式生成，category=`system`，impact=`med`，給 risk_flags 用
- [ ] **[B-FEED-INDEX]** Index rebalance dates（S&P 季末 / Russell 6 月）→ 硬編，category=`system`
- [ ] **[B-FEED-TREASURY]** Treasury auctions（FMP 或財政部 RSS）— 做 fixed income / 殖利率部位才補
- [ ] **[B-FEED-DIVIDENDS]** Finnhub `/calendar/dividends` — kanchi-dividend-sop 已用，整合進 upcoming_events
- [ ] **[B-FEED-IPO]** Finnhub `/calendar/ipo` — IPO 投機部位才補
- [ ] **[B-FEED-FED-WEB]** WebFetch Fed 官網 `/newsevents/calendar.htm` — 比 YAML 更即時（YAML 補不到的臨時 speeches）
- [ ] **[B-FEED-POLICY]** WebFetch 白宮/USTR 公告 — tariff / executive order

### 路線 C — Positions Tracker 強化
- [ ] **[C-IMPORT]** `import_firstrade_csv.py` — 解析 Firstrade 月結單 CSV → `positions.json`
- [ ] **[C-ADD]** 同一 ticker 加碼時提示「併入現有 avg cost」vs「另開 lot」兩個選項

### 路線 FE — Fincept Strategy Extraction（短期訊號強化）
- [ ] **[FE-A1]** 提取 `momentum.py` 三層訊號：Optimal Lookback、Trend Strength、Acceleration → `skills/short-term-target/scripts/momentum_signals.py`
- [ ] **[FE-A2]** 提取 `mean_reversion.py` 三層指標：Z-score、Hurst exponent、OU half-life → `skills/short-term-target/scripts/mean_reversion_signals.py`
- [ ] **[FE-A3]** 整合 A1+A2 到 `predict.py`：新增 `fincept_momentum` + `fincept_mean_reversion` 特徵與權重
- [ ] **[FE-A4]** `statistical_arbitrage.py` regime detector → 接進 `predict.py` regime filter
- [ ] **[FE-B1]** 實作 `skills/earnings-quality-analyzer/scripts/quality.py`：Beneish M-Score、Accrual Ratio 等 6 指標
- [ ] **[FE-B2]** 實作 `skills/earnings-quality-analyzer/scripts/ratios.py`：多年度 key metrics 趨勢
- [ ] **[FE-B3]** Protocol 整合：Phase 2 Burry inline 新增 `quality_label` 欄位與罰則
- [ ] **[FE-C1]** 評估 `indicators.py` 的 Hurst + RSI + ADX 是否接進 `technical-analyst`

### 路線 D — 效能優化（低優先）
- [ ] **[ARCH-11]** `lucide.createIcons()` debounce（`requestAnimationFrame` 批次）
- [ ] **[ARCH-12]** Chart.js 惰性載入
- [ ] **[ARCH-13]** marked.js 惰性載入
- [ ] **[ARCH-14]** `innerHTML` XSS 防護全面套用

---

## 📦 已完成任務詳情 (Archived Tasks)

### 路線 SS — Structural Shift Modulation (V2.18 → V2.19.2)
- [x] ~~**[SS-V2.18-EARNINGS]** `earnings-analyst/scripts/analyze.py` `compute_structural_shift()` — EPS QoQ ≥30% + GM ≥hist+2σ + rev YoY accel → tier NONE/CANDIDATE/CONFIRMED~~
- [x] ~~**[SS-V2.18-PHASE3]** Phase 3 Step 1.5 modulation：CONFIRMED 解除 analyst-PT/sector_avoid/RT mean-reversion；CANDIDATE 折半 + cap 50%~~
- [x] ~~**[SS-V2.18-THEME]** theme-detector `lifecycle_calculator.classify_stage` 加 `fundamental_override`：paradigm-shift sector 不誤判 Exhausting~~
- [x] ~~**[SS-V2.18-REGISTRY]** `register_thesis.py` 接收 structural_shift 進 thesis_data~~
- [x] ~~**[SS-V2.19-POLAR]** `compute_polarization` 升 4-tier (BIPOLAR/OUTLIER/MIXED/ALIGNED)，BIPOLAR 加 direction count 條件防 4-vs-1 outlier 誤判（Gemini case `[+4,+3,+3,+2,-2]`）~~
- [x] ~~**[SS-V2.19-RTBASIS]** Red Team anti-spoofing classifier：pure_forward / pure_mean_reversion / contaminated / unclassified；CONFIRMED 下 contaminated 視同 mr 觸發降級~~
- [x] ~~**[SS-V2.19-PHASE3-1.7]** Phase 3 Step 1.7 polarization modulation：BIPOLAR ×0.5 conf+cap25 / OUTLIER ×0.85 / MIXED ×0.75~~
- [x] ~~**[SS-V2.19-RTPROMPT]** Phase 2.8 Red Team prompt 加 STRUCTURAL_SHIFT_TIER input + 條件指令~~
- [x] ~~**[SS-V2.19-WATCHLIST]** News Phase 4.5 structural_watchlist：14d hit window + 21d eviction + ≥2 sources gate + dedup~~
- [x] ~~**[SS-V2.19-DAILY]** `daily_update.sh` Step 7 接線~~
- [x] ~~**[SS-V2.19-VALIDATOR]** `validate_v219.py` 16 fixture (含 Gemini outlier + contamination spoof)；`validate_session_export.py` 加 polarization + red_team_basis enum 檢查~~
- [x] ~~**[SS-V2.19.1-ARCHIVAL]** `build_structural_watchlist.py` 加 daily snapshot (`watchlist_history/`) + append-only `watchlist_lifecycle.jsonl` + 5-event enum (first_seen/continued/evicted/graduated_candidate/graduated_confirmed)~~
- [x] ~~**[SS-V2.19.1-BRIDGE]** `bridge.py` `load_structural_watchlist()` 注入 `data.json.structural_watchlist`~~
- [x] ~~**[SS-V2.19.1-UI]** Dashboard `index.html` Layer 5 watchlist tile + `script.js` `renderStructuralWatchlist()` + audit card ⚡ badge + i18n 4 label~~
- [x] ~~**[SS-V2.19.1-BACKTEST-SKEL]** `backtest_watchlist.py` skeleton：tier graduation rate + lead time stats + outcome 4-classify~~
- [x] ~~**[SS-V2.19.2-UIBADGE]** decisions.html / earnings.html 個股名旁 ⚡ amber badge if ticker ∈ watchlist~~
- [x] ~~**[SS-V2.19.2-FORWARD-RETURNS]** `backtest_watchlist.py` 補完 forward returns：FMP `/stable/historical-price-eod/light` + SECTOR_ETF_MAP (13 sector) + α_SPY + α_sector + 4 horizon (5/15/45/90d) + 15d alpha aggregate~~
- [x] ~~**[SS-V2.19.2-HEAT]** theme-detector `calculate_theme_heat` 加 `structural_shift_bonus` (+0/+5/+10/+15)，AI&Semis heat 52.8→62.8 + ranking 動 (V2.18 只動 stage label)~~

### 路線 F — Finnhub 雙抓架構
- [x] ~~**[F-PR1]** `skills/finnhub-client/`：60/min throttle + cache + retry + 17 endpoints + 5 個 FMP-shape adapter~~
- [x] ~~**[F-PR2]** `skills/finnhub-client/scripts/diff_tool.py` + `run_diff.sh`：Finnhub vs FMP 對照~~
- [x] ~~**[F-PR3]** 修正 FMP v3→stable 端點 + adapter + dual_fetch.py 設計~~
- [x] ~~**[F-PR4.5]** 把 dual_fetch 接進 investment_protocol Phase 1 (V4.8.1)~~
- [x] ~~**[F-PR4.6]** 端到端驗證：AMD 分析驗證，7/7 條件全 PASS~~

### 路線 ST — Short-Term Target System
- [x] ~~**[ST-Step1]** `short-term-target` skill：1d/5d/15d 預測模型與權重配置~~
- [x] ~~**[ST-Step2]** 加新主題到 `cross_sector_themes.md` (17→21)~~
- [x] ~~**[ST-Step3]** `thematic-screener` skill 實作~~
- [x] ~~**[ST-Step4]** Dashboard `radar.html` 短期雷達頁完成~~
- [x] ~~**[ST-Step5]** Outcome tracking log 自動化儲存~~
- [x] ~~**[ST-Step6]** `daily_update.sh` 整合自動跑~~
- [x] ~~**[ST-Step7]** `weekly_review.py` 每週末校準工具~~

### 路線 S — Skill 建立與 Review
- [x] ~~**[S-BUILD-01~04]** 建立 Sentiment, Tail-Risk, Portfolio, Burry 4 個核心 Skill~~
- [x] ~~**[S-COPY]** 遷移既有 Skill 至 `skills/` 目錄~~
- [x] ~~**[S-REVIEW-01~05]** 全量 Skill 驗證與閾值校準，完成 NVDA 整合測試~~

### 路線 N — News Protocol V2
- [x] ~~**[N-PROTO]** 草擬 `news_protocol_v2.md` (RSS 兩階段漏斗 + 5 Agent)~~
- [x] ~~**[N-RSS]** 撰寫 `fetch_news_rss.py` (去重 + 多源)~~
- [x] ~~**[N-ARCHIVE]** 歸檔 V1 協議~~
- [x] ~~**[N-CLAUDEMD]** 更新 `CLAUDE.md` 版本至 1.7.0~~
- [x] ~~**[N-DASH-BTN/NEWS]** Dashboard 整合 FLASH 按鈕與 DIGEST 複製功能~~
- [x] ~~**[N-TOAST/I18N/BRIDGE]** 支援 Toast 通知、多語系與 bridge.py v2 欄位~~

### 路線 B — Calendar 頁面與 Feed
- [x] ~~**[B-BRIDGE]** `bridge.py` 整合 `aggregate_upcoming_events`~~
- [x] ~~**[B-PAGE]** 建立 `calendar.html` 月曆、詳情面板與 LLM Review~~
- [x] ~~**[B-SKILL]** 整合 `earnings-calendar` (FMP API) 至 bridge~~
- [x] ~~**[B-MILESTONE1]** Event index milestone 1 樣本提取與規則~~
- [x] ~~**[B-INDEXER]** 全量 indexer `build_event_index.py` 實作~~
- [x] ~~**[B-SCHEMA]** UpcomingEvent 統一 schema 與跨頁面整合~~
- [x] ~~**[B-PROMPT]** Sector-protocol prompt 改寫與 `upcoming_events` 輸出~~
- [x] ~~**[B-FEED-FED-YAML]** 整合 FED FOMC 日曆~~
- [x] ~~**[B-FEED-EARNINGS]** 整合 FMP 財報日曆 (Top 50 tickers + $500M filter)~~
- [x] ~~**[B-FEED-ECON]** 整合 FMP 經濟指標日曆 (High Impact Only)~~

### 路線 P — 富途牛牛推播整合
- [x] ~~**[P-TICKER]** `parse_futu_notifications.py` 實作~~
- [x] ~~**[P-BACKEND]** Server lazy-fetch + 5s cache 實作~~
- [x] ~~**[P-CARD]** Dashboard 即時通知卡片實作~~

### 路線 C — Positions Tracker 強化
- [x] ~~**[C-CLOSE]** Dashboard 平倉動作實作 (exit_price + realized_pl 紀錄)~~

### 路線 I — Invest Protocol V4.8 (API 化)
- [x] ~~**[I-PA]** dual_fetch.py 擴充至 15 scalar 欄位~~
- [x] ~~**[I-PB]** Sentiment lane：Insider 統計與 Short Interest 介接~~
- [x] ~~**[I-PC]** News lane：Analyst Ratings & Price Targets 結構化 API~~
- [x] ~~**[I-PD]** Phase 0 L3 Fallback 改用 Skill Chain~~
- [x] ~~**[I-PE]** Phase 0 Schema 明列關鍵指標，減少 Phase 2 重抓~~
- [x] ~~**[I-PF]** Phase 2 共通 prompt 導入 Web Search 白名單~~
- [x] ~~**[I-PG]** Technical lane：yfinance OHLC 換成 FMP stable API~~

---

## ✅ 已完成歷史紀錄 (Summary)

- **Dashboard 強化**：`calendar.html` 全功能實作、`page-decisions.js` 平倉邏輯。
- **Data Feeds**：FMP API 全面替代 WebFetch、Upcoming events 統一 Schema 化。
- **Tactical Radar**：1d/5d/15d 短期預測系統上線。
- **V4.6 投資協議**：雙軌 entry、STAGED 狀態、Consensus bonus。
- **Sector Protocol V1.2**：主子檔拆分、三層訊號合成、決策樹。
- **Server 與 Infrastructure**：dashboard_server.py CRUD、自動 mtime cache-busting。
- **V2.18 Structural Shift Modulation**：MU/QCOM 超級週期錯失 systemic fix；earnings tier (NONE/CANDIDATE/CONFIRMED) → Phase 3 Step 1.5 modulation 解除 backward-looking lane 三重壓制。
- **V2.19 Lane Cross-Talk Wiring**：polarization 4-tier (含 OUTLIER 防 4-vs-1 誤判) → Step 1.7 modulation；Red Team anti-spoofing classifier (contaminated 不是 mixed) → mr 一票否決；structural_watchlist 14d/21d decay。
- **V2.19.1 Watchlist Archival**：daily snapshot + append-only lifecycle log（5 event enum），建立 backtest 基礎建設。
- **V2.19.2 UI + Backtest Forward Returns**：⚡ badge 跨 3 頁；FMP price + SPY/sector ETF α；theme heat bonus 動 ranking（不只 stage label）。

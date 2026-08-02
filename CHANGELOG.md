# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + [SemVer](https://semver.org).
Single source of truth for version history. Current version authority is `VERSION` file + `Dashboard/utils.js`.

> **Purpose**: Let future Claude sessions (and humans) understand the evolution
> of the system — what changed, where to look, why. Entries link back to git
> commits where applicable; for un-committed work, dates reflect local VERSION
> bump time.

## [4.83.0] — 2026-08-02 — decision card 的 polarization / RT basis 改吃決策時真值（V20-A5）

### Added
- **`bridge.py` `extract_audit_history()` 攤平兩個 badge 欄位**（V20-A5）：`signal_polarization` / `red_team_basis` 直接進 `recent_analysis[]`，附 `*_source`（`calculation_steps` | `det_shadow` | null）與 `*_disagrees`。取值優先序 = **決策時 `calculation_steps` > 後處理 `det_shadow`** —— 前者是真的動了分數的值（confidence 乘數 / position cap / buy_threshold / cascade 罰則），後者是 `apply_det_shadow.py` 事後補寫的 shadow。
- **兩個新 badge + tooltip**（`page-decisions.js`）：`POLAR SPLIT` / `RT BASIS SPLIT`，在同一筆 entry 兩個來源不一致時亮。兩者由同一支 classifier 產出，理應相同；不同代表後處理看到的 lane scores / counter_thesis 文字跟決策當下不一樣（entry 被事後編輯過）。與既有 `RT DISAGREE` / `VAL DISAGREE` 同一套視覺語言。

### Changed
- **`page-decisions.js` badge renderer 改讀攤平欄位**，`det_shadow` 保留為 fallback —— 尚未重跑 bridge 的 `data.json` 仍能正常渲染。

### Why
- V20-A1 / A2（polarization 4-tier badge、RT basis 4-tier badge）**在更早的版本就已經做掉了**，TODO 上的「UI 沒秀」已經過期；badge 與 `SIGNAL_TIPS` 兩邊都在（`ALIGNED` / `unclassified` 這兩個良性值刻意不發 badge，與 `macro_alignment` 只標 CONTRARIAN 同一慣例）。真正還沒做的是 A5 —— 而它不只是「省一層 `.det_shadow`」：renderer 原本**只**讀 shadow，V5.1+ entry 的決策時真值根本沒被看到。現行 172 筆中 2 筆有 `calculation_steps`（往後每筆都會有），0 筆不一致。

## [4.82.0] — 2026-08-02 — Phase 4 script 化：`trade_plan_builder.py` + §14 sizing 硬閘（TODO L2）

### Added
- **`investment/scripts/trade_plan_builder.py`**（新，~700 行）：Phase 4 全部算術的執行權威，`decision_engine.py` 之於 Phase 3 的對應物。一個 Bash call 收全部 —— Step 1 dual-track entry/TP/SL（吃 Phase 2.4 MHP `band_capped` / `mid_target`，TP cap 在 resistance、SL 取 `min(band_lower, support)` 與 Step 4 百分比停損的**較保守者**）、Step 2/3 內部 subprocess 呼叫 `risk_manager.py` / `tail_risk.py`、Step 3.5 FTD timeline gate（sector 分類 + stage 表 + day-21 cyclical reject）、Step 4 九段 sizing 乘法鏈 + `final_stop_loss_pct`。PM 只組 input JSON 與 verbatim 抄寫，**禁手算**。
- **V20-F1 sector concentration**（TODO 勾銷）：同 sector ≥3 active CONFIRMED → ×0.5，插在 `ftd_adj` 之後、兩個 Phase 3 cap 之前（F1 與 FTD 同屬倉位側煞車；V2.18/V2.19 兩個 cap 依設計是倉位的最後一句話）。三種輸入形式（明確計數 / `active_theses[]` / thesis registry `_index.json`），三者皆不可得時 multiplier 維持 1.0 但標 `source=registry_unavailable` —— **絕不當作「已確認 0 個同 sector 部位」**。
- **`test_trade_plan_builder.py`**（新，~330 行 / 17 組 fixture）：sizing 鏈逐段邊界、FTD 表 8×2 全格、fragility 表、staged split、F1 三種輸入、R/R 降級路徑、停損 −10% 上下界，加 MU golden replay（重現 schema FULL EXAMPLE 的 `position_size_pct=0.0203`）。
- **`replay_trade_plan.py`**（新，~330 行）：歷史 mismatch triage，照 `replay_decision_engine` 三紀律。三個 cohort 各有分母：`trade_plan` 20/172 eligible、`risk_reward` 76/172、`sizing` 47/172，排除原因全部列表且 eligible+excluded=total 對得起來。
- **validator §14**（`validate_session_export.py`，~200 行）：Tier A 重算九段鏈（含 macro cap 的 `min()` 語意）、Tier B 驗規則表（fragility / FTD stage×sector_class / F1 二值 / `REJECTED ⇒ 0 倉位` / probe tier 上限 / 停損 −10%）。`test_session_export_schema.py` 加 18 個 §14 tamper case，全部 rc=1。

### Changed
- **`session_export_version` 升 `V5.2`**：新增三個必填欄 `trade_plan_builder_version` / `risk_audit` / `mandatory_risk_flags`（缺任一 rc=1）。門檻綁 schema 版本（`RISK_AUDIT_REQUIRED_VERSIONS`）而非日期，既有 V5.0/V5.1 entry 不需回填。新增 §2d 反向 mis-stamp guard：戳 V5.1/V5.0/V4.8 卻帶 `trade_plan_builder_version` → rc=1。
- **`mandatory_risk_flags` 首次持久化**：這是 Phase 3 Auto REJECT 與 Rec 11 probe 抑制的輸入，過去從未寫進 history，`replay_decision_engine.py` 只能宣告 `[]` 當假設（declared assumption #2）。現在 replay 讀真值，assumption #2 降級為「僅適用 V5.2 之前的 entry」。
- **`investment_protocol_v5_0.md` §PHASE 4 改寫**：Step 1–4 降為 engine 的 spec 參照，前置「組 JSON → 一個 Bash call → verbatim 抄寫」；補上原文未明定的三處（`base_stop_pct` 的定義、binary `× 0.5-0.7` 區間一律取保守端 0.5、R/R 不足時「收緊 entry」的確定性順序）。

### Fixed
- **entry 區間上下界可能顛倒**（`trade_plan_builder.py`，由 replay 抓到）：`band_capped` 是 `[max(band_lower, support), band_point, min(band_upper, resistance)]`，support 高過 band_point 時（歷史上 AAPL/PLTR/TSM 三筆）兩軌會產出 `[高, 低]`。改為排序並在 `provenance_notes` 標記「區間極窄請人工複核」。
- **`fragility_label` 值域未驗**（`validate_session_export.py` §14b）：§6 只驗非 null，歷史上有 6 筆用了表外標籤（`RESILIENT` / `MEDIUM`），Step 3 乘數因此無從對應。補上 enum error（validator 只看最後一筆，不誤傷既有 history）。
- **R/R 不足時的補救順序原本無定義**：protocol 只寫「收緊 entry 或降級 HOLD」，沒說收到哪。engine 依序試 aggressive 中點 → conservative 中點 → conservative 下界，全部不過才降 HOLD；採用哪一軌寫在 `entry_track_used`、嘗試序寫在 `rr_solve_trace`。

### Why
- Phase 4 是 Phase 3 之後最後一塊仍靠 LLM 手算的決策數學：九段乘法鏈 + 兩張查表 + 一個條件 reject + 兩個獨立導出的停損價要調和。`replay_trade_plan.py` 的 `trade_plan` cohort 顯示 20 筆可比對中 16 筆與 MHP 導出值不符（全部歸類 `rule_version_drift`，因為 V4.82.0 前沒有任何 script 強制 entry = band）—— 那 16 筆正是本版要消除的漂移。
- 決策 tail：`vol_adjusted_limit_pct` 在 172 筆歷史中持久化 **0 筆**，所以 sizing 鏈無法前向 replay。改用 inverse solve（把已知乘數除回去、檢查隱含 base 落在 (0, 20%] 的可行區間），47/172 全部通過；命中 macro cap 的 trade 因 `min()` 不可逆而整批排除，不硬解。存 `sizing_chain.steps[]` 就是為了讓未來的 entry 不必再走這條退路。

## [4.81.0] — 2026-08-02 — `session_export_version` 升 V5.1：§13 硬閘改綁 schema 版本（TODO L1b）

### Changed
- **§13 門檻由日期改綁版本**（`validate_session_export.py`）：`ACCEPTED_VERSIONS` 加入 `V5.1`、`CURRENT_VERSION` 指向它，新增 `V5_VERSIONS`（5-lane 世代）與 `CALC_STEPS_REQUIRED_VERSIONS`（engine block 必填的版本集合）。戳 `V5.1` 的 entry 缺 `calculation_steps` **或** `decision_engine_version` → rc=1。4.80.1 的 `export_date ≥ 2026-08-03` 日期閘留任後衛，專擋「cutover 後刻意戳舊版號繞過版本閘」。既有 78 筆 V5.0 entry 不需回填，照當年規則驗。
- **版本條件式全面改吃集合**：`ver == "V5.0"` 型的單值比較在下次升版時會靜默失效，已改 `ver in V5_VERSIONS` —— 命中 V5.0+ 必填欄檢查（`valuation_lane` / `fair_value_summary`）與 MHP warning 兩處。
- **`replay_decision_engine.py` / `validate_markdown_export.py` 改 import validator 的版本集合**：兩者原本各自硬寫 `"V5.0"`，升版時會一個把新 entry 全判成 `pre_v5_four_lane_schema` 排除（replay 覆蓋歸零）、一個整段跳過「合理股價」section 檢查。現在新增版號只改 validator 一處。
- **`Dashboard/page-decisions.js` 解 V5.1 token 撞名**：`detectProtocolVersion()` 原本讓 `forward_expectations.trajectory` 啟發式先於 bridge 傳來的 `protocol_version` 回傳 `'V5.1'`；`V5.1` 現在是真的 schema 版號，改為**戳記優先、啟發式降為無版號時的 fallback**。副作用：舊的「有 trajectory 但 stamped V5.0」卡片 badge 由 V5.1 變回 V5.0（純 UI）。`version_v51` tooltip 改寫為 schema 語意。

### Fixed
- **`hot_zone_eval` warning 條件寫反**（`validate_session_export.py`）：`ver != "V5.0"` 讓警告只對**不可能有該欄**的 pre-V5.0 舊 entry 觸發，對**必須有該欄**的現行 export 恆不觸發（REVIEW_2026-07-31 記錄的 75 筆全 None 即此因）。改為 `ver in V5_VERSIONS`。
- **`cascade_rule_applied` 標籤可與實際懲罰／加成脫鉤**（§13 Tier B）：把已套 0.95 懲罰的鏈條改標 `no_penalty` 原本能過閘 —— rule→`penalty_value` 對照表只在 `rule_*` 名稱上生效，`no_penalty` 落進 else 分支只發 warning。補**兩側各雙向**的一致性檢查：`penalty_applied=true` 必須指名 `rule_1..5_*` / penalty rule 必須配 `penalty_applied=true`；`bonus_applied=true` 必須標 `consensus_bonus` / `consensus_bonus` 必須配 `bonus_applied=true`（bonus 側是 review 抓到的對稱遺漏，同款改標實測原本 errors=0）。影響僅 trace label，決策數學不變。
- **`phase5_export_schema.md` FULL EXAMPLE 版本戳過期**：header 寫 V5.0、JSON 卻戳 `V4.8`，而範例含 `valuation_lane` —— 照抄會直接撞上 §2b mis-stamp guard。改為完整 V5.1 範例，Phase 3 數字改用 `decision_engine.py` 實跑輸出（含 `calculation_steps` / `hot_zone_eval` / `decision_cap_active`），補 post-processor 的 `det_shadow` 後可直接過 validator。

### Added
- **V5.0 mis-stamp guard**（§2c，仿 §2b 上移一版）：戳 `V5.0` 卻帶 `decision_engine_version` → rc=1 並提示改戳 `V5.1`。`decision_engine_version` 只有 engine 產得出來，而那正是 V5.1 要求的東西。
- `investment/scripts/test_session_export_schema.py` — 版本閘契約測試（23 條）：版本閘雙向、三個 mis-stamp bypass、11 條 §13 tamper、cascade 標籤 bonus 側 3 條。**fixture 直接從 `phase5_export_schema.md` 的 FULL EXAMPLE 解析**（doc 再度過期就會紅）；bonus 鏈由 `run_phase3()` 現跑產生而非寫死，規則移動時不會變成過期 fixture。已進 `OPS_COMMANDS.md` §7。

### Why
- 日期閘擋得住「今天手算」，擋不住「回填一筆舊分析」——後者會被今天的門檻誤傷，而繞道只要把版號寫成 `V5.0` 就成立。版本閘讓「這筆 entry 該用哪套規則驗」由 entry 自己宣告，回填與新做各歸各的規則。
- 收尾用一組 20 條的驗收 battery（fixture 直接從 schema doc 的 FULL EXAMPLE 解析，doc 本身即受測）：舊 V5.0 rc=0、V5.1 缺兩欄各 rc=1、日期後衛 rc=1、兩個 mis-stamp guard rc=1、11 條 §13 tamper 全 rc=1、replay 覆蓋維持 172=1+2+169。

## [4.80.1] — 2026-08-02 — 4.80.0 review 的 2 個 P1 + 2 個 P2

### Fixed
- **P1-1 熱區 probe 逃過 Auto REJECT**（`decision_engine.py`）：`risk_reward_ratio < 2.0` 與 `FULL_FALLBACK` 兩條硬閘是決策側條件式的，而 probe 觸發前的 banded 決策是 HOLD → 兩條恆不觸發，probe 因此能帶著 R/R 1.5 或 FULL_FALLBACK 開倉（實測 `hot_zone_eval=fired`、`final_decision=STAGED_ENTRY`、`auto_reject=false`），且 validator §13 的可達集恰好放行 `HOLD → STAGED_ENTRY`，下游也攔不住。改為 fire 之前以假設決策 `STAGED_ENTRY` 重跑硬閘，觸發即 `suppressed_by_risk_flag`；trace 落 `auto_reject.probe_prospective_reasons`。
- **P1-2 validator 判死 cap override 路徑**（`validate_session_export.py`）：banded `BUY` + cap 觸發 + `cap_override_reason` → `STAGED_ENTRY` 是 4.80.0 才在 protocol 定案的合法路徑，卻不在 §13 band 可達集內（實測 rc=1）。第一筆真的走 override 的 BUY 會卡死在收尾，而 PM 依規禁止手改。可達集補上該條並在 schema doc 列表格。
- **P2-1 §13 可整段繞過**：跳過條件原本是「`calculation_steps` 缺席」，等於手算並省略該欄即可通過。改為 `export_date ≥ 2026-08-03` 缺此欄直接 rc=1（綁 schema 版本需 bump V5.1，另開一版）。
- **P2-2 MISSING lane 契約不一致**：engine 缺 lane 只 warn 並輸出 `… × MISSING = 0.0000`，PM 抄進 export 後 validator 報「unparseable」形成死路。改為 `run_phase3` 直接 raise（deep-dive 本就要求 5 lane、權重從不重分配），validator 對 MISSING 形式給明確指引。
- P3 小修：`_num` 不再輸出科學記號（`4e-05` 會讓 step-string regex 解不開）；replay 比對前先套 `apply_decision_cap`（存檔的 `final_decision` 是 post-4.6 值，否則未來 capped entry 會出偽 NEEDS_TRIAGE）；`macro_alignment` 的 sign 規則 engine 與 validator 統一為 spec 原文（0/0 → ALIGNED）；weights 覆寫值等同預設時不再誤發 warning；`open()` 補 context manager。

### Why
- P1-1 在真金白銀的決策路徑上：規則寫「硬閘優先於熱區例外」，實作卻讓例外繞過了兩道閘。單元層的 `reject.rr_irrelevant_for_hold` / `reject.full_fallback_hold_ok` 各自沒錯，缺的是「HOLD × probe」的組合 fixture——已補 4 條（含 R/R 2.5 仍應 fire 的反向斷言）。

## [4.80.0] — 2026-08-02 — Phase 3 決策數學 script 化（TODO L1）

### Added
- `investment/scripts/decision_engine.py` — Phase 3 全數學單一執行來源：Step 1 加權（三檔 C_eff）/ 1.5 structural shift / 1.7 polarization / 2 五級 cascade（first match wins）/ 3 directional macro / 4 dynamic threshold + decision band / Rec 11 熱區判定樹與 15-30 bps 分層 / Auto REJECT 硬閘。`--phase 4.6` 為獨立 entry point，收 Phase 4 sizing 後套 decision cap。polarization 與 red_team_basis 直接 import `apply_det_shadow.py`，不複製實作。
- `investment/scripts/test_decision_engine.py` — spec parity 契約：C_eff 邊界、cascade 全 5 rule + bonus/veto 路徑、polarization 4 tier + BIPOLAR 例外、threshold 矩陣 5 值、band 正負對稱邊界、熱區 4 種 eval + 0.4 tier 分界、Auto REJECT 逐條、Phase 4.6 cap 與 override，外加 2026-08-02 MU entry 的 golden replay（5 條 Step 1 字串與全部下游數字逐字相符）。
- `investment/scripts/replay_decision_engine.py` — engine × `history.json` 全量 replay。未持久化的輸入不用猜：列舉未知離散欄位跑全組合，結果不變才算 eligible，會變則列 `decision_sensitive_unknown` 並附「spec 預設值」advisory。報告 → `reports/decision_review/DECISION_ENGINE_REPLAY_<date>.md`。

### Changed
- `investment_protocol_v5_0.md` Phase 3 改「組 input JSON → 一個 Bash call → verbatim 抄寫」，公式降為 spec 參照；質性欄（`institutional_lens` / `scenario_odds` / `action_label` / `decision_confidence_pct`）仍由 PM 自寫。Phase 4.6 指向 engine cap entry point。
- `validate_session_export.py` 新增 §13：有 `calculation_steps` → 硬驗算術鏈（乘積、Σ、bonus/penalty、macro 步、threshold 公式、polarization 重算、band 可達性）；再有 `decision_engine_version` → 加驗 V4.70.0 規則表。兩者皆無的舊 entry 整段跳過，rc=0 不溯及。
- `phase5_export_schema.md` 補 `calculation_steps` / `decision_engine_version` 契約段。

### Fixed
- Phase 4.6 rule 6 的「熱區例外」與 validator §11 互斥規則矛盾：例外在 decision_cap 路徑上恆不成立（Phase 3 判定樹已先出 `suppressed_by_cap`）。engine 回報 `hot_zone_exception_applicable: false`，protocol 加註說明。
- Phase 4.6 cap 對 `BUY` 的落點原文未明確：定案為無 override 退 `HOLD`、有 override 退 `STAGED_ENTRY`，與歷史 23 筆 cap entry 一致。

### Why
- Phase 3 是「LLM 手算最容易錯、錯了最貴」的一段：三檔量化、5 級 cascade 優先序、4 tier × threshold 矩陣、熱區判定樹、硬閘優先序全靠 prompt 紀律維持。搬進 script 後，spec 由測試鎖住、產出由 validator 擋住。
- Replay 的實測結論寫進報告：能做 parity 的歷史樣本只有 1 筆（+3 筆在預設假設下逐點相符），因為 per-lane confidence 從未寫進 `history.json`，且 V4.70.0 之後的 deep-dive 累積筆數還少。harness 會隨新 session 自動變成真的 parity gate。

## [4.79.1] — 2026-08-02 — signed bias 改用去重集合（重跑不再放大樣本）

### Fixed
- `forward_expectations_success_criteria.py` 的 `_signed_bias` 原本直接迭代 `evaluations` 全量 rows，而 `summary` 用的是去重後的集合——同一個預測重跑 N 次會被當成 N 個獨立觀測。改吃 v4 新增的 `forecast_points`（新增 `_bias_rows`）。實測對照：一個樂觀預測重跑 20 次 + 一個準確預測，未去重 bias 為 `1.905`，去重後 `1.0`——差距純由重跑次數造成。今天 comparable=0 故 live 輸出不變。

### Changed
- `forecast_bias` criterion 新增 `bias_basis`，記錄實際採用的來源：`deduped_forecast_points`（v4+）／`deduped_legacy_evaluations`（v3 檔，rows 帶 identity）／`raw_evaluations_not_deduped`（無 identity）／`no_rows`。舊 payload 因此無法冒充已去重。
- 無 `ticker` 的 rows 不做去重。dedup key 是預測身分，pre-v3 與手工 rows 全部 hash 到同一 key，硬去重會把整組塌縮成 1 筆——比它要修的重跑計數更失真。改為原樣計分並如實標示。

### Why
- 4.79.0 review 期間發現、記在 TODO 的項目。`_signed_bias` 是 shadow→live gate 的四個誤差判準之一，若讓重跑次數左右它，等於讓「跑幾次」影響升格判斷。
- 20 支 fe regression rc=0（success_criteria 27 asserts，新增 9 條）；真實語料 `bias_basis: deduped_forecast_points`、verdict 維持 `insufficient_evidence`。Shadow-only。

## [4.79.0] — 2026-08-02 — Forward Expectations review 三項 P2 收尾

### Fixed
- `forward_expectations.py`：promoted cohort 的 `note` 改由 `rationale.criteria` 動態產生（新增 `_cohort_selection_note`）。原本寫死「同 sector + growth/margin/size ±1 tier」，一旦 curated cohort 取得 `growth_base_rate` 核准而晉升，出處會被標成演算法選取而非 human-approved。演算法 cohort 現在如實列出自己比對到的 criteria，human-approved cohort 則標出 cohort 名稱與核准 scope。
- `forward_expectations_calibration.py`：window-CAGR 路徑補上與 level 路徑對等的 point-in-time gate（`_cagr_point_in_time`）。`generated_at ≥ window_to` 判定為 `not_point_in_time_forecast`（整段 window 已結束，根本不是預測）；`generated_at ≥ window_from` 但未達 window_to 者仍可計分，但帶 `point_in_time_caveat: base_fiscal_year_elapsed_at_forecast_time`。

### Changed
- calibration summary 拆成 `scored_with_point_in_time_caveat` / `pending_with_point_in_time_caveat` / `not_point_in_time_count` 三個欄位。單一計數會在「已標記但尚未成熟」時顯示 0，讀起來像沒有 caveat——實際語料有 19 筆待成熟。
- **索引欄位改由測試守門，不再靠人記**（Fixture I）：AST 掃描 `forward_expectations_calibration.py` 取出所有 `snapshot.get("…")` / `snapshot["…"]` 讀到的 key，與 `INDEX_FIELDS` 雙向比對——有讀但沒進索引就 rc=1 並指名該欄位，有進索引但沒人讀也會被指出。偵測器本身用合成程式碼測過（確認 `.get()` 與 `[]` 兩種寫法都抓得到），避免變成永不觸發的裝飾。**動機**：4.78.1 的索引只快取 6 個已評分欄位，若日後開始評 `base_rate_lane` 等 lane 卻忘了擴充，`.get()` 會回 `None` → 該 lane 靜默零計分且不報錯。實測在 calibration 內加一行 `snapshot.get("base_rate_lane")` 後測試如預期失敗。

### Removed
- `_latest_snapshot_per_ticker`（v2「每檔留最新一筆」邏輯）及其 Fixture F。v3 改用 earliest-vintage dedup 後就沒有 production 呼叫端，只剩自己的測試在跑；已確認全 repo（排除 archive／CHANGELOG 的歷史敘述）無其他引用。
- CLI 預設不再印 `evaluations`，改印 `summary` + 新增的 `forecast_points`（真正被計分的去重集合），並以 `evaluations_omitted` 揭露丟掉幾列與 `--full-evaluations` 還原方式。in-process 回傳值不變，`forward_expectations_success_criteria.py` 讀 `evaluations` 算 signed bias 不受影響。

### Why
- 三項都是 4.78.0 review 記在 TODO 的 P2。實測 685 份 snapshot：CAGR gate 新增拒收 0 筆（無回歸，符合 review 預估），19 筆 legacy row 帶上 caveat；CLI 輸出 1.82 MB → 54 KB（3.0%），且不再隨 ledger 線性成長。
- 20 支 forward-expectations 迴歸腳本 rc=0（calibration 65 asserts、核心 68 asserts）；`success_criteria` verdict 維持 `insufficient_evidence`。Shadow-only，未動 DCF、fair value 或決策輸出。

## [4.78.1] — 2026-08-02 — Calibration index（全語料掃描 12.5x）

### Added
- `forward_expectations_calibration.py` 新增 derived index：只快取它實際評分的 6 個欄位（`ticker` / `generated_at` / `run_id` / `as_of_earnings_date` / `consensus_lane` / `estimate_revision_snapshot`）。索引放 ledger 目錄**旁**（放目錄內會被 `*.json` glob 當快照解析）。
- CLI `--no-index`（強制全量掃描核對）與 `--index-path`。

### Why
- 單份快照 97% 體積是 evidence/provenance 與尚未評分的 lane（`evidence_inventory` 佔 41%），calibration 從不讀；但它是唯一掃描整個 ledger 的消費者，成本隨語料線性成長。684 檔已需 0.36–0.64 s，依現行約 31 檔/日推算 1 年 3.2 s、5 年 13.5 s。
- 不改用壓縮歸檔：實測 tar.gz 只快取空間（9.6x）不快取時間（反而慢 7%），且解不了線性成長。索引則把同樣 5 年規模壓到 0.31 s。

### Discipline
- 索引是**快取**，ledger 才是紀錄。快照無法重新產生（vintage 依賴當日分析師估計），任何情況不得為索引刪除原始檔；單檔入口（`--snapshot-file`）與人工稽核仍讀完整快照。
- 每筆條目綁 source 檔 size+mtime，簽章不符即回讀原始檔；schema/欄位集變更時舊索引自動重建。
- 之後若開始評分 `base_rate_lane` / `market_implied_lane` 等目前未計分的 lane，需擴充 `INDEX_FIELDS` 並 bump `INDEX_SCHEMA`。

### Validation
- 全語料 685 快照：indexed 輸出與 `--no-index` 全量掃描 **逐字相同**；362 ms → 29 ms（12.5x）。
- `test_forward_expectations_calibration.py` 42 asserts（新增 Fixture H：索引等價、只存已評分欄位、改寫快照使簽章失效、schema 不符時重建）；20 支 forward-expectations regression rc=0。

## [4.78.0] — 2026-08-02 — Forward Expectations point-in-time 與終端區間治理

### Fixed
- Consensus、revision snapshot、financial bridge 共用 future-only annual-estimate selector；依 earnings cache cutoff 排除已公布年度，避免週期低基期重複灌入 forward CAGR。MU revenue/EPS CAGR 由 `66.72%/100.90%` 修正為 `41.34%/40.40%`。
- Future Price Range 明示為 3–5 年 terminal value、各 case 新增年化報酬；終端 analyst coverage <20 降為 `low_confidence_terminal_range`，不再把薄樣本多年累積漲幅呈現成一般 12m target。
- Calibration v3 可用完整 Q1–Q4 實績核對 point-in-time revenue/EPS level，拒絕財年結束後建立的假預測，並以 ticker/target/basis 最早 vintage 去除重跑膨脹。
- Base-rate lane 僅允許 ≥3 名且 scope 明確核准 `growth_base_rate` 的 business peers 進 numeric comparison；broad raw peers 與 MU 現有 `range_only` P/E cohort 均僅揭露，不自動擴權。

### Validation
- Forward Expectations 全套 23 支 golden/regression scripts rc=0；核心新增測試後：main 55、calibration 33、financial bridge 41、price range 61、revisions 16 asserts 全過；`py_compile`、`git diff --check` rc=0。
- 682 份歷史 snapshot 去重為 99 個 forecast points；目前 0 個真正到期且 point-in-time 可比樣本，維持 `insufficient_sample`，不以事後資料補數。

### Why
- 原引擎同時有 period leakage、終端/12m 語意混淆、薄 coverage 未降級、校準永遠不可成熟與 broad peer fallback 五種前瞻偏誤。修正以「時間點正確、同口徑、可校準、低信心出聲」為原則，仍維持 shadow-only，不改 live decision。

## [4.77.0] — 2026-08-02 — 估值引擎 review 修正（degraded path 治理）

### Fixed
- `dcf.py` start EBIT margin 期間錯配：走 `annual_analyst_estimate` 分支時，分子（已公布季度營業利益）除以全年營收估計會嚴重低估起始利潤率。改為同期基礎，provenance 區分 `quarterly_rollforward` / `reported_quarters_only`。MU 走 3 季 roll-forward，輸出不變。
- `dcf.py` degraded payload 渲染崩潰：`run_dcf` 早退分支（no base revenue / invalid revenue path / no share count）缺 `wacc_used`，`render_md` 直接 TypeError。新增 `_render_degraded_md`，標 `DEGRADED` + reason，rc 維持 1。
- `dcf.py` 缺 analyst 估計時的成長 fallback：原本整條 path 直接套成長上限表（45/30/20/12/8），把「上界」當成「預設」。改用 base growth 假設當種子再受 cap 約束。
- `dcf.py` confirmed structural shift 靜默降級 legacy：新增 `projection_degrade_reason`（5 種 reason）寫入 payload 並在 run warnings 出現。
- `dcf.py` structural mode 下 `--set revenue_growth_y1/ebitda_margin/da_pct/capex_pct` 靜默無效：改列入 warnings。
- `dcf.py` earnings cache 以 mtime 排序（git checkout 會重置）→ 改 parse 檔名日期。
- `comps.py` `_eps_growth` 年度選取污染 PEG：(a) 不過濾歷史年度，歷史成長可冒充 forward；(b) 最近年度成長超出 clamp 時靜默改抓更後面成長更高的配對。改為只取最近兩個未來會計年度、超 clamp 回 None。快取宇宙 25 檔中僅 CSCO 受影響（11.95% → 10.15%，修正值）。

### Added
- `dcf.py --projection-mode auto|legacy`：可強制 constant-ratio 模式做對照。
- DCF 報告假設表新增「本次採用」欄（✓ / — / meta），區分當前 mode 實際讀取的欄位；sensitivity 受 `wacc−g ≥ 2%` 下限調整的 cell 加註實際 WACC。
- `peer_cohorts.py` cohort `schema` 版本驗證（不符回 `unsupported_cohort_schema`）＋ `pe_min`/`pe_max`／scenario `value_low`/`value_high`（3 檔樣本無法 winsorize，改公開離散度）。
- comps 報告在 canonical peer set eligible 時不再渲染第二張 range-only peer 表（payload 保留供審計），避免讀者混用兩個 peer universe。
- `--xlsx` 對缺席的 `export_xlsx` 模組改為 graceful skip。

### Validation
- `test_dcf` 104 asserts / `test_comps` 52 asserts / `test_export_xlsx` 13 asserts 全 rc=0；`test_compute_price_framework.py` + `test_valuation_pack_consistency.py` + `check_skills.py` rc=0。
- MU 迴歸：FV `$762.13`、WACC `12.49%`、sensitivity `$693.74–853.60` 與 4.76.0 逐項一致。

### Why
- 2026-08-02 估值 review 找到 12 項問題，全部集中在 degraded / fallback 分支：MU 剛好走 happy path，但下一個「非 3 季、缺 ebitAvg、缺年度估計」的 ticker 會拿到低估或過度樂觀的 anchor 而毫無警示。修法一律是「缺資料 → 保守且出聲」，不是「缺資料 → 套最寬鬆的合法上界」。

## [4.76.0] — 2026-08-02 — DCF-primary FV + audited peer range

### Changed
- Eligible structural-shift self DCF 成為 primary FV；family blend 保留為 audit/scenario，不再把 DCF 與高週期相對估值平均成另一個單點。
- `peer_cohorts.py` + audited config 支援 LLM/manual candidate discovery；倍數一律由 deterministic adapter 重抓、≥3 正 P/E、`range_only`，不得補 live peer anchor。
- 新增 `valuation_explained_range`：DCF sensitivity、without-peer、with-peer、其他 eligible anchors、range drivers 與 limitations；報告 injector 以 DCF 主 FV + 解釋帶呈現。

### Validation
- MU @ `$812`：primary DCF `$762.13`（`-6.14%`）；DCF sensitivity `$693.74–853.60`；without-peer `$797.32`；SNDK/WDC/STX peer P/E scenario `$1,785.39`、with-peer `$1,291.36`；完整 anchor 解釋帶 `$693.74–1,468.26`（上緣 driver=analyst PT）。

## [4.75.1] — 2026-08-02 — MU structural-shift DCF 重建

### Changed
- `valuation-modeler/dcf.py` 新增 confirmed structural-shift through-cycle 模式：current-FY quarterly roll-forward、逐年成長上限、EBIT/D&A/capex 正常化、terminal reinvestment、最新季度淨現金/股數與異常欄位品質閘門。
- through-cycle WACC 對 observed beta 採 Blume mean reversion；敏感度中的 terminal growth 同步改變 reinvestment，避免高成長零成本。
- canonical pack 在新 DCF eligible 時保留但停用 opaque vendor DCF，避免同一 cash-flow family 重複投票；legacy/failed self DCF 不會壓掉 vendor source。

### Validation
- MU DCF `$762.13`、WACC `12.49%`、terminal g `2.5%`；vs cached close `$823.03` 為 `-7.4%`（vs user quote `$812` 約 `-6.1%`），5×5 sensitivity `$693.74–$853.60`。
- DCF 與 canonical framework regression、py_compile、invest validator 與版本同步均通過。

## [4.75.0] — 2026-08-02 — 個股估值改為 canonical family aggregation

### Changed
- `compute_price_framework.py` 建立唯一權威 `valuation_pack`：anchor 先做 eligibility，再按 correlation group 去重、三個獨立 family 聚合；summary、MHP、deterministic shadow 全部只讀 pack projection，少於兩個 family 禁止強分數。
- `--self-assemble` 改為 engine 擁有八個 live anchors；輸入檔同名 value/meta 會被清除並留下 audit，阻斷 LLM 注入估值。
- DCF 負 terminal FCFF、LOW/transition/少於兩法 forecaster、少於三個 business-similar peers、缺 peer count、過期或結構轉折前 analyst PT 全部 fail-closed；Reverse DCF 維持 diagnostic-only。
- peer selection 統一到 exact-industry + business-model selector；Phase 1、comps 與 forecaster 共用相同來源。
- invest validator 新增 pack↔summary↔lane↔MHP hard consistency；新增 canonical consistency、eligibility 與注入防護 regression tests。

### Validation
- MU 重跑：FV `$623.79`、vs current `-24.21%`、score `-1`、confidence `low`；完整 lineage/排除原因在 `reports/20260802_MU_valuation_pack_audit.md`。
- 同一個 Claude Fable 5 session 完成兩輪 code review；F1–F5 全部 resolved，最終明確 `ACCEPT`。

## [4.74.1] — 2026-07-21 — 專案全面更名為英文（AI投資委員會 → ai-investment-committee），保留中文顯示名稱

### Changed
- 專案資料夾實體搬遷：`/Users/kavi/Developer/Claude/Projects/AI投資委員會` → `/Users/kavi/Developer/Claude/Projects/ai-investment-committee`（`mv`，git 歷史完整保留）
- 重新指向並 reload 現行 launchd job `com.kavi.aicommittee.premarket`（原本指向舊中文路徑的 plist，含 repo 內 `scripts/premarket/com.kavi.aicommittee.premarket.plist` 與 `~/Library/LaunchAgents/` 安裝副本兩處）
- 修正 `scripts/premarket/premarket_cron.sh`、`scripts/run_weekly_review.sh`、`reports/decision_review/{p0_param_replay_2026-07-16,audit_stats_2026-07-16}.py` 的硬編路徑
- 修正 `docs/agent-ops/{DELEGATION_TEMPLATES,MAINTENANCE}.md`、`docs/ARCHITECTURE_DIAGRAM.md` 治理文件內的專案根目錄路徑
- 各活文件（README/CLAUDE/AGENTS/GEMINI/TODO/sector/docs/news/daily_update.sh/REVIEW_PROMPT）標題與內文的專案名稱由中文改為英文 "AI Investment Committee"；README.md、CLAUDE.md、AGENTS.md、GEMINI.md 標題保留中文為副標（使用者指定保留位置）；Dashboard UI 顯示文字維持中文不動（使用者指定保留位置）
- 歸檔內容（`archive/**`）、已封存的個股/週報 `reports/*.md`（`SHORT_TERM_WEEKLY_2026-07-15.md` 因仍是近 6 天內最新一份、含可執行 `ls` 指令而一併修正路徑，其餘維持原樣）、`skills/weekly-tech-playbook/data/*2026-06-22*.json`、`CHANGELOG.md` 既有歷史條目維持原樣不改寫（歷史紀錄不可回寫）

### Fixed
- `scripts/extractors/{thematic_screener_extractor,earnings_analyzer_extractor}.py` 的 `str(path).split("AI投資委員會/")[-1]` 硬編舊資料夾名稱——搬遷後若不修正會讓 `raw_path` 欄位 split 失敗、整段路徑洩漏

### Why
- 使用者要求專案全面更名為英文（含實體路徑），但保留中文名稱於指定位置作為專案説明副標
- `docs/agent-ops/MAINTENANCE.md` 自身即記載舊路徑為 `Documents/Claude/Projects/...`，與實際 `Developer/Claude/Projects/...` 不符（既有文件漂移），此次一併修正並回寫 `LESSONS.md`

## [4.74.0] — 2026-07-17 — AI 辦公室辯論機制 v2：四方平行辯論 pipeline + 修復 Claude 無輸出

### Fixed
- Lead (Claude) 連續 `(no output)`：headless `claude -p` 在專案根目錄會進入 agentic 模式（載 CLAUDE.md/MCP/工具）跑超過 180s timeout 被砍。`llm_drivers.run_claude` 新增 `model` / `max_turns` / `strict_mcp` / `no_tools` 參數，辯論 turn 走 text-only（`--max-turns 1 --strict-mcp-config --tools ""` + 固定 model + **`--system-prompt` 整個取代內建 Claude Code prompt**——只關工具不換 prompt 時模型仍會幻覺文字版工具呼叫 `**Tool: read**`；壓測 3/3 clean），並加一次 transient 失敗 retry
- `model_router._run_chain` ALL_FAILED 路徑誤標 `fell_back=True`（UI 顯示「↩ 已 fallback」但實際沒有任何模型成功）

### Changed
- `scripts/office/orchestrator.py` + `roles.py` 重寫為四階段平行辯論 pipeline，取代 round-robin 全 transcript 重讀（token O(輪²) → O(分歧數)）：
  0. **資料蒐集（Researcher，固定 gemini）**：起草前先跑一輪 facts-only 蒐集——gemini 強項是檢索不是激進論點（使用者定調）；agentic 讀 repo 新鮮 caches（market_mood / data.json / breadth_cache…），輸出 ≤12 條帶數字、日期、出處的 fact pack + gaps，發給所有起草席與終局裁決作共同依據（同一份中性事實，不破壞獨立性）；失敗時優雅降級、起草照跑；`OFFICE_RESEARCH_TIMEOUT_SEC` 預設 240s
  1. 獨立觀點：四席平行起草（Lead / Critic / Verifier / **Trader 盤面派**）——**Lead 固定 claude sonnet；Critic 只派 codex/grok（gemini 實測激進主張讓步率 3/5 最高，排除出攻擊席）；Verifier/Trader 在剩餘引擎隨機**（`roles.random_team()`；席位↔引擎解耦，meta.roles 記錄每 run 分配供後續統計讓步率），互不可見 → cross-read token = 0、分歧不被首發言者錨定；grok 對 JSON 紀律較鬆——`_call_role` 對所有引擎加一次 parse 失敗重試；grok 小 prompt 也常要 90-150s，另給 `OFFICE_GROK_TIMEOUT_SEC`（預設 300s，按引擎不按席位）；任一稿失敗時 pipeline 以 ≥2 稿續行
  2. 分歧萃取：一次結構化 pass 產出共識清單 + 編號分歧表（≤ `OFFICE_MAX_DISAGREEMENTS`，預設 5）
  3. 定點交鋒：每個分歧只發給持立場的角色，context 只含該分歧點（maintain/revise/concede + 證據）
  4. 終局裁決：強模型（`OFFICE_STRONG_MODEL`，預設 opus）讀濃縮包、逐分歧裁決並寫交付物；失敗時 deterministic fallback 組裝
- `Dashboard/page-office.js` / `office.html`：四段式展示（觀點卡 → 分歧表 → 交鋒嵌在分歧卡下 → 交付物）；保留舊 run 的輪次事件相容渲染；移除輪數選擇器
- 新 env：`OFFICE_CLAUDE_MODEL`（草稿用，預設 sonnet）、`OFFICE_STRONG_MODEL`（裁決用，預設 opus）、`OFFICE_MAX_DISAGREEMENTS`、`OFFICE_VERDICT_TIMEOUT_SEC`（預設 300）

### Why
- 7/17 使用者實跑：Lead 兩輪空白、Critic 花整輪評論「Lead 沒交東西」——順序制一來一往 token 貴且價值密度低；分歧才是這系統的訊號，改成只在分歧點上花 token

## [4.73.0] — 2026-07-17 — 新增 Grok CLI 進 LLM 治理鏈（第 4 個可選模型）

### Added
- `scripts/break_news/llm_drivers.py`：`run_grok()`（`grok -p --output-format json --permission-mode dontAsk --disable-web-search --no-subagents`；envelope `{"text":...,"usage":{...}}`）+ `GROK_BIN` 常數；註冊進 `_RUNNERS` / `VALID_MODELS`；`_DEFAULT_CONFIG.enabled/budgets` 加 grok（daily_max_calls=100，保守值）
- `config/llm_config.json`：`enabled.grok: true`、`budgets.grok.daily_max_calls: 100`
- `dashboard_server.py` `/api/llm-config`：`valid` 集合加 `"grok"`
- `Dashboard/utils.js`：側邊欄 LLM 設定下拉選單 + usage 面板加 `grok` 選項

### Why
- 使用者本機已裝 grok CLI（已測試可用，`grok-4.5`，session auth）；納入治理鏈後可被 budget/cooldown 治理、可在 Dashboard 手動選入 primary/secondary/tertiary 或 break_news 配對
- 刻意**不**動預設 `primary/secondary/tertiary`（維持 codex→claude→gemini）與 `dashboard_server.py` 的 `_protocol_command`（整段 protocol 執行器是更大決定）——grok 目前只是「可被選、可被治理」，是否拉進實際 routing 鏈由使用者手動決定

## [4.72.1] — 2026-07-16 — agreement_grade 門檻校準（0.15/0.35 → 0.375/0.52，user 核准）

### Changed
- `compute_price_framework.py` `AGREEMENT_GRADE_HIGH_CV/LOW_CV` 常數化並改 0.375/0.52（SHADOW_REPORT_2026-07-16 n=67 歷史 cv 的 33/66 percentile）；appendix spec 同步
- 效果：歷史分級 28/30 low（93% 亮燈無鑑別度）→ 4 high / 6 medium / 20 low；真極端（PLTR cv 1.26 / ARM 1.20）兩制皆 low 不受影響
- 只影響展示標籤；`reconcile_confidence` 的 0.35/0.60 confidence caps（決策鏈）不動

### Why
- 拍腦袋初值讓「錨一致度」標籤失去功能。⚠ 再校準檢查點：本校準基於修剪前 anchors，P0-3 trim 使 cv 左移（NVDA 0.341→0.188），累積 ≥20 筆修剪後 session 重出分佈再議（TODO 📊）

## [4.72.0] — 2026-07-16 — P2 斷鏈修補 + validator 補強（AUDIT F6 收尾）

### Fixed
- **P2-9** `large_cap_parabolic` 斷鏈：判定抽到 `skills/_shared/technical_core.parabolic_severity_tag`（單一源），momentum.py 原地改用、technical-analyst analyze.py 新增產出（marketCap 走 company_context 24h cache，`marketCap`/`mktCap` 容錯同 momentum.py:522）——protocol Technical lane 規則引用的 flag 現由該 lane 自己的 MANDATORY script 產出。函式測試 6/6、NVDA 實跑兩 skill 皆過
- **P2-10** forecaster SKILL.md「not auto-wired」聲明與實作矛盾修正：明示 soft-wired（engine `--self-assemble` 讀 cache 填 `forecaster_blend` anchor 0.05；缺 cache → null 重分配不失敗）
- **P2-12** `sector/ftd_yfinance.py` hardcode `~/.claude/skills/` user-level 路徑改 repo 內 canonical（env `SKILL_SCRIPTS_PATH_FTD` 可覆寫，同 market_top_yfinance.py 既有模式）；diff 確認兩份未漂移後切換；兩 adapter 實跑 rc=0；MARKET_INDEX ⚠ 整併備註解除
- **schema 文件錯誤**：`lane_scores` 註記 −3..+3 與協議 Phase 2 量表（−5..+5）矛盾（歷史 9 筆合法 ±4 分被舊註記誤標越界）——修正為 −5..+5

### Added
- **P2-11** validator §12 數值界限/加總檢查（hard error）：`final_score` ±4.5 sane bound（理論上限 ≈4.35；防 VRT 6.72 類）、`scenario_odds` 加總=100、`lane_scores`/`valuation_lane.score` 值域 ±5、`avg_confidence` 0-1。合成壞 entry 四類違規全抓 rc=1；現任 history rc=0

### Why
- AUDIT_2026-07-16 F6 文件↔實作斷鏈四項全數收尾；validator 從純 schema 檢查升級為含決策數字 sanity gate

## [4.71.0] — 2026-07-16 — P1 砍白產（shadow 落日 + 欄位瘦身 + 5d 降級 + Phase 0 caps）

### Removed（落日條款，AUDIT_2026-07-16 F5 為據）
- **P1-5** `systemic_backdrop` stub（V3.17 起全 null、宣稱的填值從未實作、零消費者）— protocol Phase 0 shape 移除
- **P1-6** `market_position`（TAM/CAGR/市占 sub-block）與 `medium_term_shift_20d` — 消費者掃描證實零渲染/零決策用途（Dashboard 決策頁、ic-memo fact pack、score 公式皆不用）；TAM 類同時是最大無來源數字幻覺面。`moat_assessment`/`institutional_lens`/`cross_asset_spillover` 等**保留**（有 Dashboard/ic-memo 渲染）——原審計 P1-6 範圍依消費者證據收窄
- Forward Expectations 35 行版本演進段移出協議本文 → `protocol_appendix_price_framework.md` §Forward-Expectations（協議本文留 8 行指標；工具改 on-demand，不在 分析 預設 flow）

### Changed
- **P1-7** `short-term-target/predict.py`：sector_intel 過期從硬拒改優雅降級（β 項歸零 + `degraded_sources` 標記 + confidence ×0.8）；news/ohlcv/atr 過期仍硬拒。根因：5d 預測 84% 被拒，其中 96% 只因 sector>72h（手動 產業掃描 更新頻率使然）。合成測試 6 asserts + 實跑 NVDA 三 horizon ok
- **P1-8** Phase 0 `macro_backdrop_score` 新增確定性一致性 caps（market_top Orange/Red → ≤0、vix ELEVATED → ≤0、CRISIS → ≤−2、breadth<30+FTD 惡化 → ≤−1，同 FRED caps 模式先於查表套用）；`macro_multiplier_rationale` 改機械式 trace 格式禁自由散文（歷史 76 份模板化重複）
- **market_regime 規則表化提案否決（校準結果）**：76 個 phase0 訊號×標籤 joint 分佈顯示存檔量化訊號無法重建 LLM regime 標籤（breadth 中位數 SIDEWAYS 50 > BULL 32；VIX 各 regime 15-19 無差），而該標籤已有 outcome 鑑別力（BULL +27.6% vs RISK_OFF −19.8%）——規則替換 = 拿未驗證分類器換有效分類器，不做；決策記錄於協議 Phase 0 caps 段

### Why
- 審計 F5 白產清單的落日執行 + F4 偽變數的低成本 bound；每項處置皆先掃消費者/跑校準，兩項原提案（P1-6 全砍敘事、regime 規則化）依證據收窄或否決

## [4.70.0] — 2026-07-16 — P0 決策品質修正（AUDIT_2026-07-16 四項對症改制）

### Added
- `reports/decision_review/AUDIT_2026-07-16_protocol_v5.md` — 分析協議全面審計：168 筆歷史 + 兩個新統計檢驗（Red Team verdict × 30d outcome 零相關 p=0.689；confidence 0.6/0.7 bucket 命中率同為 67%）；重現腳本 `audit_stats_2026-07-16.py` + `p0_param_replay_2026-07-16.py` 同目錄
- Phase 2.8 新輸出欄：`red_team_counter_evidence_strength`（進 export）+ `red_team_thesis_break_probability`（僅記錄，≥20 session 後校準用）；validator 11c 值域檢查
- `compute_price_framework.py` v1.2：`trim_anchor_outliers()`（P0-3）— n≥4 時錨值落在錨中位數 ×1/3..×3 外剔除不進加權（相對錨共識非現價，全體偏低不誤剪）；`fair_value_summary.anchors_trimmed` 記錄、raw 值保留；golden test +10 asserts（7 fixtures 61 asserts，NVDA-like 案例修剪後 $272→$296 手工驗算）

### Changed（決策路徑，AUDIT 數據為據）
- **P0-1** Rec 11 熱區 probe 分數分層：`final_score ≥ 0.4` → t2（≤30bps）/ `< 0.4` → t1（≤15bps 原上限）。replay：上半帶觀望 mean +17.6%（up 10/15，dd −7.1%）vs 下半帶 [0,0.2) −1.2%——上半帶錯過實質上漲。新欄 `hot_zone_probe_tier`，validator §11 按 tier 強制
- **P0-2** Red Team 懲罰分級：rule 4 pure_forward 只有 strength=5（≥2 獨立資料源）保留 ×0.85，strength=4 → ×0.925；rule 5 default（unclassified）×0.85 → ×0.95。依據檢驗 A：STRONG_COUNTER 佔 80.4% 且與 outcome 零相關（STRONG 組 30d +12.52% vs 對照 +8.64%；被否決且 CANCEL 的 60 筆 57% 照漲）——blanket 重懲無資訊基礎且加重保守偏誤
- **P0-4** Phase 3 Step 1 lane confidence 改三檔量化 C_eff（<0.45→0.35 / <0.675→0.60 / ≥0.675→0.72）：校準檢驗證實 0.5–0.7 核心帶無鑑別度、唯一訊號在低尾；111 筆 what-if rho +0.127 vs 連續 +0.117，flips 8 筆方向中性；檔位中心=歷史分佈均值（scale-preserving，buy_threshold 免重校準）。raw conf 照舊 export
- protocol 本文 + price_framework appendix（outlier 修剪段取代「winsorize 留 P2」）+ phase5_export_schema（3 新欄 + anchors_trimmed）+ validator（§11 tier / §11c 值域；既有 history 實測 rc=0，舊 entry 僅 warning）

### Why
- 審計證實：60% 決策 CANCEL 且 conservative miss 46.3% vs active 22.2%（錯過 +28% runup 而非避開 −5% dd）；四項全部對症「系統性向下壓分」的無資訊環節，每項參數皆由 134 筆已完成 30d 窗口的 replay 選定

## [4.69.0] — 2026-07-16 — valuation-modeler：自建 DCF/comps + 8-anchor + 首次覆蓋報告

### Added
- `skills/valuation-modeler/`（第 25 個 skill）— 對照 Anthropic「Claude for Financial Services」官方套件差距分析後，把四個缺口以原生 deterministic engine 移植（官方 LLM prompt 包手算數字，違反本專案 script 定值紀律）：
  - `dcf.py`：driver-based 5 年 FCFF DCF——假設自動推導（analyst estimates / 歷史均值，每欄帶 provenance）可 `--set`/`--overrides` 覆寫；CAPM WACC（beta=FMP profile、rf=fred-macro cache）；5×5 WACC × terminal growth sensitivity；golden test 43 asserts（baseline $248.41 人工驗算）
  - `comps.py`：多指標同業比較（P/E / EV/EBITDA / EV/Sales / PEG，IQR winsorize + quartiles + implied per-share，EV 數學同 compute_price_framework）；24 asserts
  - `export_xlsx.py`：`--xlsx` 出 5-sheet Excel workbook（openpyxl，graceful degrade）；13 asserts
- 首次覆蓋 Initiating Coverage：`ic-memo-writer` 新增 `compose_initiation.py` + `template_initiation.md` + `build_fact_pack.py --initiation`（嵌 valuation_model block，缺 cache rc=4 印補跑指令）+ `validate_ic_memo.py --initiation`（F-I1/I2/I3：區塊齊全 + 數字 verbatim 一致）；觸發 `首次覆蓋 [TICKER]`；28 asserts + NVDA 端到端 rc=2（僅既有 peer_descriptor stub）

### Changed（決策路徑，使用者已核准）
- fair_value_summary 6 anchor → **8 anchor**：+`dcf_self_built`(0.15) +`comps_implied`(0.10)；家族層權重不變（DCF 族 0.45 / 倍數族 0.30 / 市場預期 0.25），族內拆分調整；comps anchor 排除 P/E 防與 `peer_pe_implied` 重複計權
- confidence 門檻 high ≥6 / medium 4-5 / low <4（原 ≥5/≥3）；ARCHETYPE_WEIGHTS 11-anchor 池重配平（financial 的新 anchor 刻意 0）；golden test 全數按新權重人工重驗算（6 fixtures 51 asserts）
- protocol 本文 + price_framework / fmp_bundles appendix（新增 §4 VALUATION_MODEL_BUNDLE）+ phase5_export_schema 同步；validator 加 anchors 容錯（舊 6-key entry 天然相容，實測既有 history rc=0）

### Why
- 官方套件真正缺口 = 可審計自建 DCF、完整 comps table、首次覆蓋格式、xlsx 交付物；已有且更嚴謹的（earnings/sector/news/ic-memo/screening）不取代。連接器（S&P/FactSet/Daloopa 等）需付費訂閱不引入，FMP+Finnhub 等效

## [4.68.1] — 2026-07-16 — 盤前 launchd 排程補跑機制（電池闔蓋喚醒失效修復）

### Fixed
- 盤前 4:30 launchd 任務在「Mac 電池供電＋闔蓋過夜」時整天不執行：`pmset` 的 4:27 排程喚醒在該狀態下被 macOS 跳過（只剩幾秒的 DarkWake，GUI LaunchAgent 不會跑），launchd 醒來後也沒有補跑 missed calendar job（實測 2026-07-16 全程未執行）
- `scripts/premarket/com.kavi.aicommittee.premarket.plist`：`StartCalendarInterval` 從單一 04:30 擴成 04:30 / 05:00 / 06:00 / 07:00 / 08:00 五個時段（週一~五）——早上任何時間開蓋，下一個時段就會補跑
- `scripts/premarket/premarket_cron.sh`：加 already-succeeded-today guard（當日 log 已有 `daily_update.sh rc=0` 就記一行 skip 後退出），多時段不會重複做工

### Why
- 排程喚醒只有接電源才保證生效；補跑機制讓「沒插電過夜」從整天漏更新降級為「開蓋後最多等到下一個整點」

## [4.68.0] — 2026-07-03 — SESSION_NOTES 批次輪替制 + rotate script

### Added
- `scripts/rotate_session_notes.py`（0 LLM）— 批次輪替：主檔 >20 個 Session Note 時自動把最舊 10 個切成 `archive/session_notes_v<最舊>_to_v<最新>.md`（批內新在上；≤20 no-op；目標檔已存在不覆蓋 rc=1）；`--split-legacy` 一次性拆舊式 rolling archive。版號 regex 支援 `(v4.63.0)` 與範圍式 `(v2.10.0 → v2.11.0)` 標題

### Changed
- 舊 `archive/session_notes_archive.md`（239 note）拆成 **24 個版號範圍批次檔**（v1.40.0 → v4.54.2），總數驗證無遺失；原檔備份 `docs/agent-ops/backups/session_notes_archive.md.bak-20260703`
- MAINTENANCE §3 輪替規則改批次制（不再每 session 手搬一個）；SESSION_NOTES 指標註解、OPS_COMMANDS §1 同步

### Why
- 使用者定案：查歷史時按版號範圍直接開對應批次檔，比單一大 archive 好找；輪替動作 script 化後弱模型只需跑一條命令，不可能搬壞

## [4.67.0] — 2026-07-03 — 2+1 評審制接線進 protocol 本文（最強檔不可用時的判斷節點補償）

### Added
- `investment_protocol_v5_0.md` 新小節「最強檔不可用時的 2+1 補償」：Phase 2.8 Red Team 在 Agent tool `model` 可用值無高於 sonnet 檔位時，改為盲開 2 個獨立 Red Team + 1 個 referee subagent（fresh context，只做矛盾比對/證據強度/選優補條，禁重寫）；輸出維持單份 red team JSON，schema/validator 不變；分歧摘要以 `[2+1: …]` 附加於 counter_thesis 文末
- `sector/phase_4-5.md` V4.67.0 Arbiter 降級模式註記：Phase 4c 同判準下盲開 2 個獨立 Arbiter + referee 選優；分歧寫進既有 rationale 欄位，不動 sector schema
- `docs/agent-ops/MODEL_DISPATCH.md` §6 標註已接線＋指向兩處小節

### Why
- 高判斷節點（對抗推理、跨 lane 仲裁）原本靠 opus 檔位，未來若最高檔只剩 Sonnet 級沒有補償機制。2 個中階獨立作答 + 1 個評審 ≈ 1 個高階的穩定度；觸發判準寫成可觀測條件（Agent tool model 清單），有高階檔的現在零成本零行為改變

## [4.66.0] — 2026-07-03 — Phase 5 報告決策數字改 script 注入（Formatter 只寫佔位符）

### Added
- `investment/scripts/inject_report_facts.py`（0 LLM）— Sonnet MD Formatter 對 6 個決策關鍵區塊只寫 `<!--INJECT:*-->` 佔位符（decision_summary / lane_scores / fair_value_anchors / kill_conditions / key_risks / watch_conditions），本 script 從 history.json 末筆 verbatim 注入。`<!--FACTS:*-->` 標記包裹 → 重跑 idempotent 刷新；HOLD/CANCEL 的 None entry/TP/SL 渲染 N/A；未知 placeholder / 殘留 token rc=1
- `investment/scripts/test_inject_report_facts.py` — 33-assert golden fixture（注入完整性、數值 verbatim、N/A-safe、idempotent 刷新、錯誤路徑、與 `validate_markdown_export.py` 相容）
- `investment_protocol_v5_0.md` Step 4 prompt 增佔位符強制 + 新 Step 4.5（注入步，在 Step 5 score-scale validator 之前）

### Changed
- `docs/agent-ops/DIAGNOSIS.md` §三.1 定位修正：原診斷指 ic-memo §11，覆查發現該處已由 `compose.py` deterministic 渲染；真正的 LLM 手抄暴露點是 Step 4 Formatter（validator 只驗刻度格式、值抄錯照樣過）。教訓入 LESSONS.md

### Why
- 「叫 LLM 精確抄寫數字」是弱模型最典型的失敗模式，且原 gate 抓不到值漂移。與既有「禁止手算」哲學一致：verbatim 複製就是一種算術，全部走 script。5 日/60 日 advisory 數字仍由 Formatter 轉寫（漂移非致命），決策關鍵數字已 100% script 化

## [4.65.0] — 2026-07-03 — 資料源健康檢查：daily_update.sh 收尾自動印 artifact 新鮮度表

### Added
- `scripts/daily_health.py`（0 LLM）— 17 個資料源的 artifact 存在＋mtime 年齡檢查：14 個 auto 源（daily 應每日刷新，超齡 3x → FAIL）+ 3 個 manual 源（產業掃描/新聞分析/economic-calendar，只 WARN/MISS 不 FAIL）。`--strict` 有 FAIL 時 rc=1、`--json` 機器可讀。分支邏輯 6 條路徑（OK/WARN/FAIL/manual 降級/missing auto/missing manual）以受控 mtime 測試通過
- `daily_update.sh` 收尾（final banner 前）自動跑健檢，非致命

### Why
- economic-calendar FMP 403 之後 sector Phase 3 一直 silent SOFT fail——step「成功」但下游沿用舊 cache 沒人喊。rc 只能抓「本次失敗」，artifact 年齡連「連續失敗中/從未產出」都抓得到；弱模型不會「覺得怪」，所以斷供必須自己大聲。首跑即揪出 economic-calendar cache 從未產出（MISS）

## [4.64.1] — 2026-07-03 — SESSION_NOTES 輪替：只保留最近 10 個 Session Note

### Changed
- `SESSION_NOTES.md` 4754→~100 行：保留最近 10 個 Session Note 區塊 + 尾部 2 個常駐狀態區塊（Momentum Context、Bridge 資料流對照）；其餘 236 個區塊以 script 機械搬移至 `archive/session_notes_archive.md`（最新在上，查舊版本用 Grep 版號）。搬移前備份 `docs/agent-ops/backups/SESSION_NOTES.md.bak-20260703`
- `docs/agent-ops/MAINTENANCE.md` §3 輪替規則定案：每次收尾新增 Session Note 後，把第 11 個搬 archive（使用者 2026-07-03 定案「保留 10 個」）
- Bridge 資料流對照表的 `investment_v4_8` 標籤更新為 `investment_v5_0`

### Why
- SESSION_NOTES 雖非自動載入，但被讀時弱模型容易整檔 Read（一次數萬 token）；「檔案本身只有 ~100 行」是比「請帶 limit 讀」更可靠的結構性保險。

## [4.64.0] — 2026-07-03 — Agent 治理層：CLAUDE.md 瘦身 + docs/agent-ops/ 全套（弱模型時代保品質）

### Added
- `docs/agent-ops/` 新目錄：`DIAGNOSIS.md`（harness 三大漏洞診斷）、`OPS_COMMANDS.md`（指令總表，含「改哪個引擎跑哪組測試」對照）、`MODEL_DISPATCH.md`（指揮官不下場/派工三件套/升降級路徑/驗證不自驗/2+1 評審制）、`JUDGMENT.md`（升級時機/完成判準/該問人時機/方向錯誤訊號/品質底線，各附正反例）、`DELEGATION_TEMPLATES.md`（T1-T5 派工模板）、`MAINTENANCE.md`（治理檔權限分級/版本同步驗證命令/巨檔讀寫與輪替規則/LESSONS 格式）、`LESSONS.md`、`LETTER.md`（交接與制度退化預防）
- `skills/MARKET_INDEX.md` 補列 `quant-backtest`、`weekly-tech-playbook`（索引 drift 修復，24 skills 齊）

### Changed
- `CLAUDE.md` 178→74 行：只留路由與紀律，Ops 指令抽到 OPS_COMMANDS.md，刪全部版號歷史敘述；Workflow Rules 增「已授權自主作業免確認」例外、收尾增版本同步驗證命令
- 父層 `/Users/kavi/Documents/CLAUDE.md` 改為 ≤10 行指標檔（原為過期舊拷貝，與專案版雙載且矛盾）
- `AGENTS.md` / `GEMINI.md` 去重：trigger 表與 Workflow Rules 只留指向 CLAUDE.md 的引用，不再複製
- `investment/investment_protocol_v4_8.md` → `investment/archive/`；全 repo 16 條活文件 v4_8 引用改指 v5_0（skills/sector/news README、SKILL.md、plan_short.md、.py docstring）

### Fixed
- 對抗審查（fresh-context agent）找出 13 個問題全數修正：MARKET_INDEX 漏 weekly-tech-playbook、AGENTS.md provisional 規則指向撲空、OPS_COMMANDS assert 數過期（26→實測 38，改為 rc=0 為準）、DIAGNOSIS/MAINTENANCE 輪替門檻數字打架、GEMINI.md 第三入口規則複製等

### Why
- 未來若只有 Sonnet/Opus/Haiku 級模型，品質靠「拆小任務+明確驗收+獨立驗證」的結構而非單一強模型；先修掉每 session ~35KB 的雙 CLAUDE.md 載入與 changelog 式膨脹，再把調度/判斷/維護規則外化成弱模型可執行的判準。舊 CLAUDE.md 備份於 `docs/agent-ops/backups/`。

## [4.63.0] — 2026-07-02 — 回測策略模板擴至 11 個（20 候選實測取前 10 + 自家引擎）＋策略卡片選擇 dialog

### Added
- **`skills/quant-backtest/scripts/backtest.py` — STRATEGIES registry（11 模板）**：原 `momentum` / `ma_cross` 之外新增 `roc_trend`（TSMOM 時序動能）、`donchian`（唐奇安/海龜通道）、`obv_trend`（OBV 量能趨勢確認）、`boll_reversion`（MA200 過濾布林回歸）、`supertrend`（ATR 通道翻轉）、`triple_ma`（三均線多頭排列）、`rsi_reversion`（RSI14 超賣反轉）、`high_52w`（52 週新高動能）、`keltner`（肯特納通道突破）。每模板含中文 label、預設參數、參數掃描格、無效組合驗證；新增 `--params-json` 通用參數通道（舊 `--entry-score/--exit-score/--fast/--slow` flags 保留相容）+ `resolve_params()` 型別轉型。
- **模板選型方法學**：先以 20 個候選策略（含 chandelier / RSI2-Connors / KD / z-score / 布林突破 / ADX / MACD / 趨勢回檔 / 量能突破等）對 12 檔（SPY、QQQ + 跨產業 mega-cap 10 檔）跑 5y / 單邊 10 bps 同一基準，以**跨標的中位數 Sharpe** 排名，取前 10 名 + 自家 momentum 引擎入 registry；落選 9 個（中位 Sharpe 0.42→0.09）不提供。
- **`scripts/rank_strategies.py`（新）** — 基準排名 runner → `data/strategy_rank.json`（含 methodology / universe / 每模板中位 Sharpe/CAGR/MaxDD/交易數/贏過 B&H 比例），供卡片 badge 與重跑再生。
- **`Dashboard/backtest.html` + `page-backtest.js` — 策略卡片選擇 UI**：`<select>` 換成觸發按鈕 + popup dialog（backdrop blur、ESC/backdrop 關閉、鍵盤可選）；11 張卡片各含 lucide icon、中英名、分類 badge（趨勢跟蹤/均值回歸/量價確認/自家引擎）、**一句白話策略說明**、**迷你 SVG 訊號示意圖**、基準績效 badge（rank + Sharpe + CAGR）。參數表單改由 TEMPLATES spec 動態渲染；載入歷史結果自動同步模板與參數；bench 值烘焙於 JS 並在載入時以 `GET /api/backtest/strategies` 最新 artifact 覆蓋。
- `dashboard_server.py` — `GET /api/backtest/strategies`（serve strategy_rank.json）；`QUANT_BACKTEST_TEMPLATES` 白名單（11 keys，result API 檔名驗證）；`/api/backtest/list` 跳過非回測 artifact 並帶 `template_label`。

### Changed
- **訊號改在完整抓取歷史上計算後才切回測窗**（`backtest.py` + `run_sweep` 簽名 `(template, full, window_bars, params, cost_bps)`）— 修正原 `ma_cross` MA200 warmup 被窗口吃掉、新模板 252 日 lookback 損失一年的問題。
- `SCRIPT_PROTOCOLS.quant_backtest` cmd 改 `--params-json {params_json}`（requires: ticker/template/period/cost_bps/params_json）；requires 檢查改「只擋 None/空字串」— `cost_bps=0` 等合法 0 值不再被誤擋。
- `test_backtest.py` 29 → 68 asserts：registry 完整性、resolve_params 轉型、全模板訊號互斥煙霧、新模板合成序列決定性行為、warmup 保留驗證。

### Why
- 使用者要求：策略模板太少 → 從已知策略庫選 20 種**先實測回測再取前 10**，並把下拉選單升級為淺顯易懂的卡片 + popup dialog 選擇器。排名用中位數（抗單一標的離群）+ 統一成本假設，卡片 badge 直接標示實測基準讓選擇有依據。**探索層紀律不變**：結果不入 investment_protocol 決策。

## [4.62.0] — 2026-07-02 — 量化策略回測頁（quant-backtest）：動能規則 5-10 年歷史重放 + 參數掃描熱力圖

### Added
- **`skills/quant-backtest/`（新 skill）** — deterministic 0-LLM 回測引擎：
  - `scripts/backtest.py` — 兩個策略模板：`momentum`（momentum-monitor `_composite` 計分規則**逐日向量化重放**，口徑鎖定 `momentum.py`；short_squeeze 組件因歷史 short interest 不可得固定中性 40 分並寫入 data_caveats）與 `ma_cross`（MA fast/slow 交叉）。訊號日收盤成交、單邊 cost_bps 內建、3y/5y/10y 窗口（多抓一段供 MA200 warmup）。輸出 metrics（total/CAGR/Sharpe/MaxDD/exposure/勝率）+ 逐年表 + 交易清單 + **參數掃描格**（momentum 6×6 entry×exit、ma_cross 3×3 fast×slow — 防過擬合：看高原不看尖峰）+ series → `skills/quant-backtest/data/<TICKER>_<template>.json`（gitignored）。每次 momentum 跑自動比對 live cache 的 ma_stage / trend_acceleration / stage 口徑（`validation_vs_live_cache`）。rc: 0 ok / 1 fatal / 2 degraded（<252 bars）。
  - `scripts/test_backtest.py` — golden-fixture 回歸測試（29 asserts：組件分數轉折點 / 持倉狀態機 / 手算 metrics / 成本入帳 / sweep 形狀），改 engine 後必跑 rc=0。
- **`Dashboard/backtest.html` + `page-backtest.js`（新頁「策略回測」，NAV stock 群組）** — 參數表單（ticker/模板/窗口/閾值/成本）→ POST `/api/protocol-queue` `{name:'quant_backtest'}`（SCRIPT_PROTOCOLS subprocess 路徑，0 LLM 0 Claude turn）→ 輪詢 → 渲染：6 指標 tiles、權益曲線（log，策略 vs B&H）、價格+進出場三角標記、雙回撤、動能分+持倉底色圖、**Sharpe 熱力圖**（發散色階，紫框標當前參數）、逐年報酬表、交易清單、歷史結果 chips。data_caveats + 重放口徑驗證 badge 常駐顯示。
- `dashboard_server.py` — `SCRIPT_PROTOCOLS.quant_backtest`（requires 列出全部 8 參數防 placeholder 殘留；timeout 300s）+ `PROTOCOL_LOG_DIRS` + 只讀 `GET /api/backtest/list`、`GET /api/backtest/result?ticker=&template=`（ticker regex + template 白名單防路徑遍歷）。

### Why
- 使用者要「視覺化制定策略 + 回測 3 年歷史」。自家訊號歷史僅 2-3 個月（journal 2026-04 起），但 momentum 計分是純算術 → 可在 FMP 10 年日線上**重放**，成為第一個可完整回測的策略；PoC 已驗證重放與 live cache 口徑一致、NVDA 5y 跑出誠實結果（跑輸 B&H 但 MaxDD 砍半、2022 熊市 -10.7% vs -50.3%）。UI 刻意做成「模板+參數格」而非自由策略編輯器，配合掃描熱力圖與逐年表對抗曲線擬合。**探索層紀律**：結果不入 investment_protocol 決策。

## [4.61.0] — 2026-07-02 — 盤中頁整合（盤中評估＋盤中策略 → 單一「盤中」頁分頁）＋全中文化 hover 解釋

### Changed
- **兩個盤中頁合併為單一「盤中」頁**（`Dashboard/intraday-eval.html`）：頂部 Tab 切換「策略」（regime／曝險紀律＋策略卡＋產業情緒排行＋族群輪動＋個股點子）與「評估」（個股急拉/急殺＋大盤盤中綜合＋逐檔價量體檢＋今日 K 線 modal）。原「盤中評估」內容原封移植為第二分頁的獨立 IIFE（scope 隔離，不改資料流／API）。策略／評估各自的 status＋refresh toolbar 隨分頁切換。
- `Dashboard/utils.js` NAV：移除 `intraday`（盤中評估）項，保留單一 `intraday-eval` 項、標籤由「盤中策略」改為「盤中」。`i18n.js` 同步（zh「盤中」/ en「Intraday」）。
- `Dashboard/intraday-mood.html` 改為 redirect stub（`→ intraday-eval.html#mood`），保留舊網址／書籤相容；`page-index-extra.js` 盤中異動帶卡片連結同步改指 `intraday-eval.html#mood`。分頁初始狀態：`#mood` 優先，其次 `localStorage` 記憶上次分頁。

### Fixed
- 盤中策略頁英文標籤全中文化：`verdict`（FAVOR/WARM/HOT/NEUTRAL/AVOID → 偏多/溫和/強勢/中性/迴避）、`vix_regime`（NORMAL/ELEVATED… → 正常/偏高…）、`skew_label`、`fear_greed_label`（Fear/Greed → 恐懼/貪婪）。
- 氛圍條 8 格（盤中分數／市寬／SPY／QQQ／IWM／VIX／SKEW／F&G）＋產業評等徽章＋逐檔體檢欄位（RVOL／VWAP乖離／MA20／出貨日／型態／MACD/KDJ）全數加上 hover 白話 tooltip 解釋術語。

### Why
- 「盤中評估」與「盤中策略」頂部氛圍資訊高度重疊、且產業情緒排行只存在於策略頁，兩頁並列造成導覽冗餘。合併為單一入口＋分頁後，可行動策略與價量體檢一站可達。原本大量英文原始標籤（FAVOR/Fear/NORMAL…）與未解釋縮寫（SKEW/F&G/RVOL）對讀者不友善，全面中文化＋hover 說明降低理解門檻。

## [4.60.0] — 2026-07-02 — 盤中策略樞紐（Intraday Evaluation hub）：每 10 分鐘統整 + 策略卡 + 重複策略特效 + 新頁面

### Added
- `scripts/intraday_eval/`（新模組）— 盤中**統一資料樞紐**：一條 worker 統整 `docs/STOCK_DATA_FETCH_INVENTORY.md` 下所有盤中產物（heatmap / intraday_mood / market_mood / intraday_spikes / retail_sector_pulse / thematic / sector_report），下游只透過**單一 accessor**（`get_snapshot()` / `/api/intraday-eval/data`）讀取，不再各自打 API（0 額外 API call，純讀既有快照）。
  - `engine.py` — `load_sources()` 統整入口 + `evaluate()` 0-LLM 規則引擎：regime + 曝險紀律、市寬、半導體/軟體/加密族群輪動、產業排序（今日 breadth + 5d 前瞻）、個股點子、**9 條策略卡規則**（stable id）。
  - `history.py` — 每 10 分鐘視窗記錄 `intraday_eval_history_<DATE>.json`，算每策略 **連續 streak** + **當日累計次數**（rapid /refresh 有 240s dedupe）。
  - `narrate.py` — change-gated LLM 導讀（走 `model_router`，signature 未變則重用快取，TTL 30 分；失敗降級為規則式 fallback）。
  - `test_engine.py` — golden-fixture 回歸（24 asserts，改 engine 後必跑 rc=0）。
- `dashboard_server.py` — soft-import 樞紐 + `intraday_eval_poll_loop`（開機常駐 daemon，美股時段每 600s + 收盤後一次快照）+ 路由 `GET /api/intraday-eval/{data,history,state}`、`POST /api/intraday-eval/refresh`。
- `Dashboard/intraday-eval.html` + `page-intraday-eval.js`（新頁「盤中策略」）— regime banner + 導讀 + mood 條 + 策略卡 + 產業排序條 + 族群輪動 + 個股點子表 + **策略重複時間軸**。
- `Dashboard/style.css` — `.ie-*` 頁面樣式 + **重複策略特效**：連續 ≥2 視窗 `iePulse` 發光、≥3 `iePulseStrong`、當日累計 `×N` echo 徽章、≥3 次「全日主旋律」橘徽章（沿用 intraday-mood iaPulse / break-news echo 慣例）。

### Changed
- `Dashboard/utils.js` — NAV_ITEMS 新增「盤中策略」入口（id `intraday-eval`，icon `crosshair`）；`VERSION` → V4.60.0。
- `Dashboard/i18n.js` — 補 `nav.intraday` / `nav.intraday_eval`（zh/en）。

### Why
- 使用者要一條盤中 worker 每 10 分鐘統整現狀、簡報策略，並在「同一策略連續數個視窗或整日反覆出現」時加特效視覺化。核心紀律：**統整一次、單一 function 供下游撈，不讓每個 feature 各自撈**；引擎 0-LLM 可測試可回歸，LLM 只做導讀且 change-gated 省 quota。屬**探索層**，**不**進入 investment_protocol 決策。
- 註：既有 3 條盤中 daemon 未重寫，樞紐疊在其輸出之上做統整（避免高風險重構）。新路由/daemon 需重啟 `dashboard_server` 生效；重啟前新頁以 static-file fallback 唯讀可用。

## [4.59.3] — 2026-06-30 — K 線彈窗載入加速：前端短快取 + 拉長盤中伺服器 TTL

### Changed
- `Dashboard/intraday-mood.html` — 新增前端記憶體快取 `_klCache`（45s TTL）+ `_klFetch()` helper，`openKline` 改走它；連點同一檔在 45 秒內直接用快取秒開，不再每次重打 `/api/heatmap/intraday`。只快取「有 bars」的成功回應，避免把暫時性錯誤快取住。
- `dashboard_server.py` — `HEATMAP_INTRADAY_TTL_SEC_OPEN` 預設 `15` → `60`，減少盤中每次點擊都重新跟 FMP 抓 + 排在 ~500 檔背景 fan-out 後面等限流池 slot 的卡頓。

### Why
- 改 1 分 K 後使用者反映彈窗「載入好久」。實測 FMP 單日 1min 僅 0.83s / 39 根，取得本身不慢；真正延遲來自盤中只有 15s 快取 + 與背景大批 quote fan-out 共用 `fmp_pool.acquire_slot` 限流池而排隊。前端快取 + 拉長伺服器 TTL 直接消掉重複往返。純呈現/取得層調整，**不影響** investment_protocol 決策。

## [4.59.2] — 2026-06-30 — 盤中個股小卡 K 線彈窗：單擊觸發 + 1 分 K + 移除 TradingView 浮水印

### Changed
- `Dashboard/intraday-mood.html` — 個股急拉/急殺小卡的今日 K 線彈窗改為**單擊**觸發（原為 `dblclick`，L373），tooltip 文案同步改 `點擊看今日 K 線`（L486）。
- `Dashboard/intraday-mood.html` — lightweight-charts `layout` 加 `attributionLogo:false`（L317），移除右下角 TradingView 浮水印 logo（4.2.0 原生支援）。
- `dashboard_server.py` `_fetch_heatmap_intraday` — FMP endpoint `historical-chart/5min` → `1min`（含 7 日 fallback 與 docstring），彈窗改顯示 1 分 K；前端 meta 標籤 `5分K` → `1分K`（L308/356）。

### Why
- 使用者要求：互動上單擊比雙擊直覺；盤中想看更細的 1 分 K 顆粒度；TradingView 浮水印視覺干擾。三項皆為純呈現層調整，**不影響** investment_protocol 決策、不碰評分。

## [4.59.1] — 2026-06-30 — 推播去雜訊：區間盤整的反轉不再推，只推有方向 / 真突破

### Changed
- **`Dashboard/intraday-mood.html` — 桌面推播 + 翻轉 banner 加方向過濾**。新增 `isDirectionalAlert()`：KDJ+MACD 同向翻轉若發生在「10 分鐘 regime = 區間」且無真實 spike 佐證，視為震盪雜訊**不推播 / 不上 banner**；只有 regime 為多頭/空頭（趨勢中）或有 non-suppressed 的 high/breakout spike 突破區間時才放行。每張卡的反轉狀態仍照常顯示（只是不再打擾你）。banner 文案改「N 檔有方向翻轉」。

### Why
使用者反映推播雜訊仍多——「很多都是區間的但也推播」。區間裡 KDJ/MACD 會來回交叉產生大量假反轉。承接已具備的 10 分鐘 regime，把推播門檻提高到「真正有方向或突破」的訊號，cards 仍保留完整資訊。

## [4.59.0] — 2026-06-30 — 雙擊個股小卡 → 今日 K 線彈窗（lightweight-charts）

### Added
- **`Dashboard/intraday-mood.html` — 雙擊個股急拉/急殺小卡開「今日 K 線」站內彈窗**。用 TradingView 免費 **lightweight-charts@4.2.0**（CDN，~50KB）畫蠟燭圖 + 量能 histogram，深色玻璃風與 dashboard 一致。
  - **後端 0 改動**：重用既有 `GET /api/heatmap/intraday/<TICKER>`（FMP 5 分 OHLCV，已快取，盤中 15s / 收盤 5min TTL）。
  - 前端只取**最新交易日**那一段（端點盤中回今日、盤前回 7 天 fallback），永遠呈現乾淨單一 session；標頭顯示日期 + 根數 + 收盤 + 當日淨變化%。
  - FMP 的 ET wall-clock 時間以 UTC 解讀，讓時間軸直接印 ET 時鐘（09:35…）。
  - 互動：卡片 `cursor:pointer` + `title="雙擊看今日 K 線"`；事件委派在 `#ia-spikes-body`（poll 重繪不掉監聽）；背景點擊 / ✕ / Esc 關閉；`ResizeObserver` 自適應寬度；每次開窗重建 chart 避免殘留。

### Why
使用者希望「雙擊小卡直接開今天的 K 線」。沿用既有 5 分 OHLCV 端點 + 站內輕量蠟燭圖庫，避免外連 iframe（資料外洩 / 風格不一 / 連線受限）。屬探索層，**不**進入 investment_protocol 決策。

## [4.58.2] — 2026-06-30 — 卡片標頭漲跌改「近10分淨變化」對齊走勢線 + 牛皮股 sparkline 壓平

### Changed
- **`Dashboard/intraday-mood.html` — 卡片標頭 % 從「單分鐘 m1」改為「近 10 分鐘淨變化」**（`cx.spark` 首尾比），與走勢線同尺度。解決 GLW 那種「線在漲、標頭卻 -0.16%」的時間尺度違和——線往上→標頭綠、往下→標頭紅，內部自洽。無 10 分脈絡時退回 m1。前端從 `cx.spark` 推導，**0 引擎改動**。
- **`sparkSVG()` 自動縮放壓平**：近乎平盤的序列不再被 min–max 拉滿。10 分總幅度 < `FLAT_FLOOR=0.3%` 時，線往中線收斂（`amp = min(1, pctRange/0.3)`），牛皮股畫出來就是平的，不會假裝成一波趨勢。

### Why
使用者反映「1 分鐘漲跌對我沒意義、應該 match 線」，且牛皮股（GLW）的 sparkline 被自動縮放放大、~0.1% 總幅看起來像大漲，與「區間 / 微跌」標籤違和。當下這分鐘的脈動已由 σ 倍數表達，標頭改放與線同尺度的 10 分淨變化更一致。

## [4.58.1] — 2026-06-30 — σ 倍數依大小分色

### Changed
- **`Dashboard/intraday-mood.html`** — σ 倍數標籤（regime 脈絡列 + 急拉/急殺 chip）依大小分色，一眼判斷大小：`<1×` 灰（雜訊）· `1–2×` 橘（一般）· `≥2×` 紅（罕見大動作）。新增 `sigColor()` helper。

### Why
使用者希望 σ 倍數的數字本身帶顏色分級，不用讀數字就能看出「這分鐘相對自己波動算不算大」。

## [4.58.0] — 2026-06-30 — 個股急拉卡片視覺化：移除無意義的時間戳訊號流，改 10 分鐘走勢 sparkline

### Changed
- **`Dashboard/intraday-mood.html` — 每張卡最下行從「時間戳訊號流」改為「10 分鐘走勢 sparkline」**。舊版顯示 `訊號流 ↗13:37 ↘13:30 ↗13:25`（某分上、某分下的歷史交叉時間戳）——無幅度、無「現在重不重要」，對 5 張 `尚無訊號` 的卡更是整張只剩這行噪音。新版改為：
  - **regime 配色迷你走勢圖**（inline SVG `sparkSVG()`）— 直接畫出最近 10 根收盤的形狀，綠=多頭 / 紅=空頭 / 灰=區間，末點加圓點。
  - **精簡 regime 標籤** `▲多頭 σ0.8×`（hover 顯示 `距高 -0.2%`）。
  - 每張卡（含 `尚無訊號`）都恆顯示中期姿態，回答「這檔現在處於什麼狀態」而非「歷史上哪幾分鐘交叉」。

### Added
- **`skills/market-sentiment-analyzer/scripts/intraday_spikes.py` — `regime_context(bars)`**：always-on 10 分鐘姿態（regime + 距高/低 + 現分 σ 倍數 + `spark` 收盤序列），錨定在 NOW（最後一根）而非 spike。`build()` 為每檔 reading 掛 `rd["context"]`（取代原 `rd["flow"]` 掛載；`build_signal_flow` 函式保留供未來使用）。σ 倍數上限 50× 防死水標的爆數字。
- **`test_intraday_spikes.py`** — 新增 2 個 golden test（regime_context 上升序列 + bar 數不足），全檔 31 assertions ALL PASS。

### Why
使用者看實際 UI 後反映「告訴我幾分鐘上、幾分鐘下沒意義」並要求「更視覺化」。承接 v4.57.0 引擎已具備的 10 分鐘 regime/σ 脈絡，把卡片底行從孤立的單分鐘箭頭時間戳，換成一眼看懂趨勢形狀的 sparkline + 中期姿態標籤。屬探索層，**不**進入 investment_protocol 決策。

## [4.57.0] — 2026-06-30 — 盤中急拉擊殺去雜訊：10 分鐘 regime 脈絡 + σ 自適應門檻 + 急拉擊殺型態

### Changed
- **`skills/market-sentiment-analyzer/scripts/intraday_spikes.py` — `detect_spikes()` 從「單根固定門檻」升級為「10 分鐘脈絡感知」**。過去只看最近幾根的 `|1分|≥1%` / `|3分|≥2%` 絕對門檻，對高 β 名字（1%/分是日常呼吸）狂噴假訊號、對牛皮股漏接真突破。新增四層（資料沿用既有 90 分鐘 1 分線，**0 額外 API**）：
  1. **σ 自適應**（`compute_baseline`）— 算 spike 前 10 根 1 分報酬的標準差 σ，輸出 `sigma_mult = |本分動能| / σ`。高波動股 σ 大、門檻自動拉高；牛皮股 σ 小、真突破才過。
  2. **10 分鐘 regime 脈絡**（`_linreg` 斜率 + R²）— 分 up / down / range，將進來的這分鐘標為 `順勢急拉`(降級) / `逆勢急拉`(軋空嫌疑·升級) / `突破急拉`(橫盤衝破區間·最高價值) / `區間急拉`(雜訊嫌疑)，鏡像同理急殺側。
  3. **持續性** — spike bar 須收在自身全距上/下 1/3（`sustained`），砍掉單根長影線瞬閃。
  4. **複合分數 `score` 0–100** — σ 倍數 + 脈絡加權 + MACD/KDJ/量確認數 + 持續性。前端依分數排序/過濾，不再每根過門檻都塞進來。
  - **`suppressed` 雜訊閘**：sub-σ（`< NOISE_SIGMA_K=2.0`）+ 無確認 + 順勢/區間 → 標記抑制、severity `low`、從 headline `spikes[]` 移除（仍掛在 reading 卡片）。突破 / 逆勢 / confirmed 永不抑制。
  - **向後相容**：序列 < `BASELINE_MIN=15` 走 legacy 路徑（行為與舊版完全一致，新欄位為 None / False）。

### Added
- **`detect_pump_fade()` — 急拉擊殺 / 急殺反軋合成型態**。急拉 leg ≥ `PF_PUMP_PCT=1.5%` 後於 `PF_FADE_WIN` 根內被急殺回吐 ≥ `PF_FADE_RETRACE=50%`（拉高出貨/誘多被殺）＋鏡像急殺反軋（誘空被軋）。此型態跨多根、單根 `detect_spikes` 結構上看不到，需滾動窗。輸出 `pump_fades[]`。
- **`Dashboard/intraday-mood.html`** — 卡片新增脈絡標籤行（`⚡ 突破急拉 · 分+2.0% · σ19.5× · 分數81`）；新增急拉擊殺 banner（`🎯 N 檔急拉擊殺/反軋`）。被抑制的雜訊 spike 不顯示 chip。
- **`test_intraday_spikes.py`** — 新增 7 個 golden test（突破 / 逆勢 / σ 抑制 / legacy 不變 / 急拉擊殺 / 急殺反軋 / 無 fade），全檔 27 assertions ALL PASS。

### Why
使用者反映盤中「急拉擊殺只記當下這一根 tick 的狀況、雜訊偏多」，並建議先統計連續 10 分鐘線的趨勢、再判斷這分鐘進來的急拉。固定絕對 % 門檻無法區分「跟著趨勢的續攻 / 橫盤裡來回甩的雜波 / 從安靜基底突然啟動」三者，且對不同波動度標的不公平。此版把判斷從「孤立單根」改為「相對 10 分鐘 regime + 自身 σ」，並補上字面上的「急拉擊殺」拉高出貨型態。屬探索層，**不**進入 investment_protocol 決策。

## [4.56.0] — 2026-06-28 — 投資方案頁可一鍵產生：playbook protocol + 「產生本週方案」按鈕

### Added
- **`playbook` protocol（dashboard_server.py）**— 把 weekly-tech-playbook 生成流程接成可從 UI 一鍵觸發的 Claude turn。新增四處 dict 條目：`PROTOCOL_MODEL`（opus，三籃選股判斷）、`PROTOCOL_TIMEOUT_OVERRIDES`（30 分鐘；env `PLAYBOOK_TIMEOUT_SEC`）、`PROTOCOL_PROMPTS`（完整流程：`build_pack.py` 抓報價 → 讀 pack → 三籃各選 10 檔寫 selections → `render.py --validate-only` 自我修正迴圈 → 正式 render）、`PROTOCOL_LOG_DIRS`。`_label_for` 加「📋 本週方案」、`enqueue_protocol` 加 playbook 無參數去重（running/queued 各擋一次）。沿用既有 `/api/protocol-queue` 端點與統一 FIFO 佇列，**未新增端點**。
- **`Dashboard/playbook.html`**— header 加「🔄 產生本週方案」按鈕；空狀態卡片改為一鍵產生按鈕（取代原本只印手動指令）。
- **`Dashboard/page-playbook.js`**— `generatePlaybook()`（confirm 對話框告知約 10–20 分鐘 / ~$4 tokens → `POST /api/protocol-queue {name:'playbook'}`）+ `pollGenStatus()`（輪詢 `/api/protocol-queue`：running 顯示經過時間、queued 顯示排隊中、完成自動 reload `playbook.json` + toast；重開頁面會接續顯示進行中的生成）。
- **`Dashboard/i18n.js`**— 新增 `playbook_page` 區段（zh + en）：generate / generating / confirm / toast_queued / toast_dup / toast_done / toast_fail。

### Why
使用者反映「投資方案沒有從 UI 網頁上可以產生」。先前 `/playbook.html` 只**呈現** `playbook.json`，產生一份新方案得手動跑 `build_pack.py` → Claude 選股 → `render.py` 三步。此版把整條流程封裝成 `playbook` protocol，讓使用者在頁面上一鍵生成本週三籃 $100k 方案。屬前瞻探索層，**不**進入也不回寫 investment_protocol 決策。

## [4.55.0] — 2026-06-28 — 總體儀表板「全新資訊架構」重設計：6 個最新資料源上首頁 + 修 F&G/VIX 量表讀舊欄位

### Changed
- **`Dashboard/index.html` 全面重排為 top-down 決策漏斗 6 段資訊架構**：① VERDICT（委員會今日裁決）→ ② STATE（市場狀態：工作台 + 二元風險 + 8 量表）→ ③ MOOD & TAPE（情緒與盤中）→ ④ SECTORS & THEMES（產業與題材）→ ⑤ IDEAS（可執行想法）→ ⑥ DESK（工作台與探索）。所有既有 live element ID 原封保留，既有 render 函式（verdict / 8 量表 / teasers / audit / watchlist）不受影響。
- 移除已被取代的舊 `intraday-mini-strip` inline script（功能併入新「盤中異動帶」widget）。

### Added
- **`Dashboard/page-index-extra.js`（新檔）**— 把先前在首頁「完全沒有出現」的 6 個最新資料源接成正確綁定的視覺化 widget：
  - 市場氛圍（`data.market_mood`：composite score + VIX/SKEW/F&G/期權傾向 sub-readings）
  - 社群熱度（`trending_tickers.json`：gated tickers + market-wide buzz topics）
  - 盤中異動帶（`intraday_mood.json` headline + `intraday_spikes.json` spikes/reversals，附 live dot）
  - 零售產業脈動（`retail_sector_pulse.json`：依預測 5 日 outlook 排序，news_sentiment 著色 bar）
  - 本週投資方案（`playbook.json`：保險/混合/激進三籃 + Codex review verdict）
  - 知識圖譜 / 供應鏈探索導引卡
  - 純讀取呈現層；自行 fetch feed，non-blocking；每次 `updateDashboard()` 末尾呼叫 `IndexExtras.render(data)`。
- `Dashboard/style.css` 新增 `.ix-*` widget 樣式（section label / mood bar / buzz row / tape / pulse bar / playbook basket / explore card）。

### Fixed
- **首頁 F&G 與 VIX 量表讀到 stale 欄位**：`pill-fg` 原讀 `data.market.fear_greed`（漂移為 49.8「Neutral」），實際 `market_mood.json` 為 25.5「Fear」；`pill-vix` 原讀 `data.market_top.vix_level`。兩者改優先讀 `data.market_mood`（fear_greed.index / vix.current），tooltip data-attrs 同步。市場處於 Fear 時不再誤顯示 Neutral。

### Why
使用者反映「已經有很多新功能，但最新資料沒有正確反映到總體儀表板上」。盤點後確認 6 個每日/即時產出的 feed（mood / 社群 / 盤中 spikes / 零售脈動 / playbook / 圖譜）在首頁無任何露出，且情緒量表綁到會漂移的舊欄位。重設計把首頁改成符合每日讀盤心智模型的 6 段漏斗，並把所有最新資料源以正確綁定的方式視覺化呈現。

## [4.54.2] — 2026-06-28 — REVIEW_2026-06-28 收尾：Rec 11 hot_zone_eval instrumentation (TODO-015) + carry-over 清理

### Added
- **Rec 11 `hot_zone_eval` instrumentation**（TODO-015，本週最高風險盲點）：決策層 Rec 11（熱區保守性鬆綁）上線 21 天，首個 qualifying 場景 **TXN 06-22** 出現卻**無任何欄位**可確認規則是否被評估（`hot_zone_probe` extractor=0/160），無法區分「評估後被 risk_flag 正確抑制」vs「規則根本沒被評估」。修正：
  - `investment/investment_protocol_v5_0.md` Rec 11 段 + export JSON：每筆 deep-dive **強制**寫出 `hot_zone_eval` enum（`fired`/`suppressed_by_risk_flag`/`suppressed_by_cap`/`not_qualifying`），判定樹明列；`hot_zone_probe=true ⟺ eval=fired`。
  - `scripts/extractors/deep_dive_extractor.py`：讀權威 `hot_zone_probe`/`hot_zone_eval`，並對缺欄歷史報告**反推** `hot_zone_eval_derived`（多一個 `qualifying_unexplained` 告警值＝gate 符合但仍 HOLD 且查無抑制源＝真 bug 訊號），160 份歷史報告即時回填。
  - `investment/scripts/validate_session_export.py` §11b：`hot_zone_eval` enum + `probe⟺fired` 強制（present 時 hard error；legacy/V5.0 缺欄僅 warning，不破 rc=0 gate）。
  - `investment/scripts/replay_rec11.py`：risk_flag/cap gate 從 docstring 自承的「assume-pass」改為讀 `hot_zone_eval` → `suppressed_*` 不計入「would fire」（TXN 不再被誤算成觸發）。
  - `investment/phase5_export_schema.md`：補 `hot_zone_eval` 欄定義。

### Changed
- **REVIEW carry-over 清理**（`reports/decision_review/REVIEW_TODO.md`）：append TODO-015(done)；TODO-013 → **done (hypothesis refuted)**（agent_score_stdev 全樣本兩輪一致否證「高 dispersion 降倉」）；TODO-004 → **dropped**（modifier 欄 6 輪乾淨，輕量欄已足）；TODO-006 → **休眠**（殘量凍結老報告，無回推需求）。

### Why
- REVIEW_2026-06-28 點名「決策層最高風險 Rec 上線、首個 qualifying 場景出現，卻無欄位可確認規則是否被評估 → 驗收盲飛」為本週最重要盲點。TXN 反推為 `suppressed_by_risk_flag`（Valuation SELL −3.0 + Burry WARNING）證實規則有評估且正確抑制（TXN 後續 −14.1%，HOLD 對）。此修正**純 instrumentation + 文件 + bookkeeping，零下單/評分邏輯改動**，解鎖 TODO-012（Rec 11 真驗收）。extractor 25 test 通過（news_digest 1 筆 fail 為 pre-existing，與本案無關）。

## [4.54.1] — 2026-06-27 — 修逆勢假反轉(MU 急跌爆「反轉向上」) + 訊號流收合

### Fixed
- **逆勢假反轉**（`intraday_spikes.py`）：`detect_reversal` 在清楚的下跌趨勢裡會把超賣區的 1 分線 KDJ/MACD 小金叉（dead-cat bounce）報成「反轉向上」並升 alert —— user 實例：MU 均線空頭排列、破低急跌，卡片卻爆綠「★⤴ 反轉向上」。新增 `apply_trend_context(rv, tr)`：當反轉方向與**嚴格均線排列趨勢**（`detect_trend`）相反 → 標 `counter_trend`、`alert=False`、改稱「逆勢反彈/回測」；`build()` 對每檔套用。前端 `intraday-mood.html` 狀態行對 `counter_trend` 反轉不當頭條，落回主導趨勢（如 MU → ▼順勢續跌），漲跌色/卡片高亮同步。

### Changed
- **訊號流收合**（`build_signal_flow` + 新 `_collapse_flow`）：連續同向事件收合成一筆（取該 run 最新時間，spike 在 run 內則保留 ⚡），不再「連三次 ⤴ ⤴ ⤴」；`max_events` 4→**3**。merged label 留作 hover tooltip。回應 user「卡片不要連三次訊號流,提醒就好」。

### Why
- 承 4.54.0：趨勢偵測器上線後，反轉與趨勢的優先序衝突現形 —— 逆勢 oscillator 交叉是反彈不是反轉，對趨勢中的個股喊反向是假訊號。以「嚴格排列趨勢」作脈絡閘 demote 逆勢反轉，讓主導趨勢說話；同時把訊號流去重，UX 從「重複洗版」改為「一次提醒」。`test_intraday_spikes.py` +4 case（逆勢降級/同向保留/無趨勢保留/flow 收合）。仍為探索層，不入 investment_protocol。

## [4.54.0] — 2026-06-27 — 個股急拉/急殺：加「順勢續攻/續跌」趨勢延續 STATE 偵測器

### Added
- **`intraday_spikes.py`** 趨勢延續偵測層（payload version 1.3→**1.4**）：
  - `detect_trend()` — **狀態型**偵測器（非事件型）：當乾淨趨勢「持續中」就觸發，補上 `detect_spikes`（暴衝）與 `detect_reversal`（剛交叉）都抓不到的「均線多頭排列順勢創高」缺口。多頭條件 = **嚴格疊排 ma5>ma10>ma20** + 收盤 ≥ ma5 + ma5 上揚 + KDJ `K>D 且 K≥TREND_K_MIN`(=50) + 收盤貼近近 `TREND_HIGH_WINDOW`(=20) 根窗高（`TREND_HIGH_TOL`=0.1%）；空頭為嚴格鏡像。`strength=strong` 當 K 深入趨勢區（≥70 / ≤30）。輸出 `ma`/`k`/`d`/`basis`/`direction`/`dir_zh`。
  - `_sma()` 簡單均線 helper。
  - `build()` 每檔 reading 掛 `trend`；新增 top-level `trends[]`（strong 優先、再依 |K−D| 排序）。
- **`intraday-mood.html`** 個股卡片狀態行優先序改為 **反轉 > 順勢趨勢 > 尚無訊號**：有趨勢無反轉時顯示「▲順勢續攻 / ▼順勢續跌 + basis（均線排列·KDJ·創高貼價）+ ET 時間」，卡片左緣穩定色條高亮（`.ia-scard.trend`，非 pulse — 它是狀態不是事件）。價格漲跌色亦反映趨勢方向。
- **`test_intraday_spikes.py`** +5 case（多頭續攻 / 空頭續跌 / 盤整 None / bar 不足 / 回落破排列），共 +19 asserts。

### Why
- User 指出「個股急拉/急殺」面板對一張明顯多頭續攻的分鐘圖（均線多頭排列 + KDJ 高檔順勢金叉 + 創高）仍顯示「尚無訊號」。經 review：面板原本只有兩個**瞬間變化**偵測器 —— 急拉/急殺需 |1分|≥1% 或 |3分|≥2%（平滑緩漲碰不到）、反轉需近 3 根內**新**交叉（順勢延續時交叉早過期）。缺的是**狀態型**「趨勢仍在續攻」偵測。本版補 `detect_trend()`，多頭排列採嚴格疊排（訊號少而準）。Live 驗證：原 12 檔全「尚無訊號」→ 6 檔跳出順勢訊號（GOOGL/META 續攻、AVGO/AAPL/NVDA/TSLA 續跌）。仍為探索層，不入 investment_protocol。

## [4.53.0] — 2026-06-26 — 個股急拉/急殺：反轉偵測 + 每檔訊號流卡片 + KDJ+MACD 同向 alert

### Added
- **`intraday_spikes.py`** 反轉偵測層（payload version 1.2→**1.3**）：
  - `detect_reversal()` — 純動能轉折（雙向）：近 `REVERSAL_LOOKBACK`(=3) 根內 KDJ K×D 交叉 **或** MACD 轉向（金叉/死叉、柱 sign-flip、DIF 零軸穿越）即算「正在反轉」。**`alert`** = KDJ 交叉 + MACD 同向轉折（user 的 SNDK 範例：KDJ 剛上翻 + MACD 轉正 → 趕快提示），標 `strength=strong`。KDJ 超賣翻揚/超買翻落 zone 註記。
  - `build_signal_flow()` — 從 bar window 重建每檔近 30 分「訊號流」：所有 KDJ/MACD 交叉 + 急拉/急殺事件，各帶 bar 時間，新到舊，cap 4 筆（stateless）。
  - `_macd_turn_recent()` / `_kdj_cross_recent()` recency 掃描 helper。
  - `build()` 每檔 reading 掛 `reversal`/`flow`/`alert`；新增 top-level `alerts[]`。build ~1.1s（12 檔）。
- **`intraday-mood.html`** UX 重做為**每檔一張緊湊卡片（placeholder）**（CSS grid，固定順序不每分鐘 reshuffle）：卡頭現價 + 即時 1分%；第二行當前反轉狀態（⤴/⤵ + dir_zh + basis + ET 時間，alert 卡綠/紅發光 pulse + ★）；第三行橫向訊號流（icon+時間）。頂部 alert banner 列出 KDJ+MACD 同向翻轉的檔。新增「🔔 提示」桌面通知 opt-in（permission gesture + 去重推播）。時間一律顯示 **ET**（盤中時區，原本 UTC 18:08 易混淆）。
- **`test_intraday_spikes.py`** +3 case（反轉 alert / 平盤 None / 訊號流排序），共 33 asserts。

### Why
- 承 4.52.0：user 反映「每檔即時 % + 0.X% 噪音」不是訊號,且不要每分鐘亂跳;要「真的篩出正在反轉的股票」。經確認 = **純動能交叉、雙向**,核心情境是 SNDK「KDJ 剛上翻 + MACD 轉正 → 趕快提示」。再經確認 UX = **每檔一張卡片 + 橫向訊號流 + 對應時間**。本版把面板從「過門檻才亮的 chip 清單」改成「每檔常駐卡片、攤出訊號流時間軸」,並把 KDJ+MACD 同向翻轉升為發光 alert + 桌面推播。1 分線粒度下交叉最快 ~1 分偵測到;要 sub-minute 需 Alpaca SIP tick feed。仍為探索層,不入 investment_protocol。

## [4.52.0] — 2026-06-26 — 個股急拉/急殺：每檔獨立訊號 + UI 可編輯名單

### Added
- **`intraday_spikes.py`** `latest_reading()` — 每檔監控標的算最近一根完成 bar 的即時 1分/3分 % 變動 + last price + `spiking` flag（不論是否過門檻），寫進 payload 新欄位 `readings[]` 與 `watchlist[]`。payload version 1.0→**1.1**。新增 `save_watchlist()`（驗證 `^[A-Z][A-Z0-9.\-]{0,9}$`、dedupe、≤50、保留檔頭註解、atomic write）+ public alias `load_watchlist`。
- **`dashboard_server.py`** `GET /api/intraday-spikes/watchlist`（讀名單）+ `POST /api/intraday-spikes/watchlist`（`{tickers:[...]}` → 驗證/存檔 → 背景觸發 `_intraday_spikes_refresh`）。
- **`intraday-mood.html`** 急拉/急殺面板改為**每檔一個獨立訊號 chip**：spiking 高亮（⚡ + 顏色邊框 + ✓MACD/✓KDJ/✓量 + ★），未過門檻者淡色顯示即時 1分/3分 變動，無資料者標「無資料」。新增「✎ 編輯名單」inline textarea 編輯器 → 儲存即 POST + 重新偵測。

### Why
- user 看富途某檔明顯急拉卻沒被標,問「目前監控哪 10 檔」「這樣不算急拉嗎」。根因：面板只在**過門檻**時才顯示 chip,平時只露「監控 N 檔」計數,看不到在監控誰、也看不到「有動但未達 ±1%/±2% 門檻」的即時狀態,且名單只能手改 `spike_watchlist.txt`。本版讓**每檔都是常駐的獨立訊號**（看得到每檔即時 %）,把名單攤在 UI 上,並可直接在面板增刪。注意：Alpaca 免費 IEX 僅覆蓋**美股**——港股/陸股那類標的這條 lane 抓不到,需另接資料源。

## [4.51.0] — 2026-06-26 — 急拉/急殺加 MACD/KDJ/量 確認層

### Added
- **`intraday_spikes.py`** `detect_spikes()` — 價格 % 觸發後,在**同一批 1 分鐘 bar**上重用 `intraday.compute_macd`/`compute_kdj`（pure-python）算動能確認：急拉看 DIF>DEA/金叉/hist>0 + K>D、急殺看 DIF<DEA/死叉/hist<0 + K<D,加上量增 ≥3×。`confirmations`（MACD/KDJ/量陣列）+ `confirmed`（價格 + ≥2 項同向）+ severity 確認即升 high。每筆附 `macd`/`kdj` 讀數。Alpaca 抓取窗口 40→**90 分鐘**（1 分 MACD 需 ~35 根才穩）。
- **`intraday-mood.html`** spike chip 顯示 ✓MACD/✓KDJ/✓量 badge + ★（≥2 確認）。
- **`test_intraday_spikes.py`** +6 asserts（長上升序列 → MACD+KDJ confirmed → high）,共 24 asserts。

### Why
- user 看富途 SNDK 急拉範例,要「**MACD or KDJ 加上量**去判斷現在是否急拉/急殺」。原本只看價格 %；本版疊上動能確認層——交叉/方向須與急拉同向、量須放大才標 confirmed（★）,降低單看 % 的假訊號。**資金流向/特大單**那塊（tick 級按單大小）另議：免費 IEX 給不了,需 Futu OpenAPI 或 Alpaca SIP。

## [4.50.0] — 2026-06-26 — 個股急拉/急殺快線（Alpaca 1 分鐘線，獨立 lane）

### Added
- **`intraday_spikes.py`**（0 LLM，deterministic）— 與 FMP 5min 大盤引擎並行的**獨立 lane**：讀 **Alpaca 1 分鐘 bar**（free IEX feed）對自訂 watchlist 偵測**急拉/急殺**。純核心 `detect_spikes()` 掃最近 5 分鐘：`|1分| ≥ 1%` 或 `|3分| ≥ 2%` 觸發,severity high/med,量增（this-min vol ≥ 3× 均量）為**次要確認**。為何 Alpaca：FMP 1min REST 被 402 鎖、Polygon 免費無即時 WS;Alpaca 免費層即有即時 1min。
- **`config/spike_watchlist.txt`** — 一行一 ticker、`#` 註解的可手編名單（種子 10 檔 mega-cap）。
- **接法 = REST 輪詢**（非 WebSocket）：`dashboard_server` `intraday_spikes_poll_loop` 每 `INTRADAY_SPIKES_INTERVAL_SEC`（預設 **60s**）盤中多檔一次抓 + 開機快照;GET `/api/intraday-spikes/data`;`intraday-mood.html` 頂部新增「個股急拉/急殺」區塊（▲▲ 綠 / ▼ 紅 chip + 時間 + 量增）。
- **`test_intraday_spikes.py`** — 18-assert golden（急拉/急殺/3分累積/量增/資料不足/watchlist 解析）。

### Why
- user 要對**個股**抓 1 分鐘級急拉/急殺,大盤其餘維持 FMP 5min。Alpaca 免費 IEX 是唯一 $0 拿到即時 1min 的路。
- **IEX 量能限制（誠實標註）**：免費 IEX 單一交易所、量被系統性低估,故偵測**以價格 % 為主**、量僅次要確認、非硬門檻;要準量需 Alpaca 付費 SIP（$99/mo,`ALPACA_FEED=sip`）。
- 無 `ALPACA_API_KEY`/`ALPACA_SECRET_KEY` 時 graceful no-op,面板顯示提示。**探索層,不**入 investment_protocol 決策。

## [4.49.1] — 2026-06-26 — 修：盤中評估頁左側欄不見

### Fixed
- **`intraday-mood.html`** — 頁面用 inline script 但漏呼叫 `UI.boot('intraday')`，導致 `<aside id="sidebar">` 從未 render、整條左側導覽列消失。補上 boot 呼叫（每頁必呼，否則 sidebar 空白）。`utils.js` NAV_ITEMS 的 `intraday` 項已存在，現在 active 高亮也正確。

## [4.49.0] — 2026-06-26 — 盤中評估：MACD/KDJ 動能確認層（下殺/反轉提示）

### Added
- **`intraday.py`** — pure-python `compute_macd`（DIF/DEA/hist + 末根交叉）+ `compute_kdj`（RSV→K/D/J + 末根交叉），對 SPY/QQQ/IWM 各算**雙時間框**：日線（regime，~60 根永遠夠）+ 盤中 5min（時機，bar 數不足回 None 守門 → 早盤不噴垃圾）。
- **新旗標（confluence-gated，只當確認層）**：
  - **下殺** `momentum_breakdown`：盤中 KDJ 高檔死叉（K_prev≥70 或 J≥90）**或** 盤中 MACD 死叉 **且** 跌破 VWAP。
  - **反轉** `momentum_reversal`：盤中 KDJ 低檔金叉（K_prev≤30 或 J≤10）**或** 日線 MACD 柱狀體由負轉升（且有破底/連跌弱勢脈絡）→ 強化既有價格行為「止跌」。
  - **`macd_daily`**：日線 MACD 金叉/死叉 regime context（low/info）。
- 每檔輸出加 `momentum`（macd_5m/kdj_5m/macd_1d/kdj_1d 數值，**永遠透出**）；`intraday-mood.html` 卡片加一行 MACD/KDJ 讀數 + 交叉箭頭。週期/超買超賣門檻（`MACD_*`/`KDJ_*`/`KDJ_OB`/`KDJ_OS`）皆檔頭常數可調。
- **`test_intraday.py`** — +13 asserts（helper 守門、KDJ 死叉@超買 / 金叉@超賣、下殺/反轉旗標整合、MACD 結構），共 47 asserts。

### Why
- user 問「即時化有沒有 MACD/KDJ 反轉/下殺提示」。本來只有純價格行為（破底/止跌/VWAP）。加震盪指標當**確認層**——交叉須與價量同向（KDJ 須在超買/超賣區、MACD 死叉須配跌破 VWAP）才升級提示，刻意 gate 掉 5min 上的 whipsaw 假訊號。**依 user 指定：只出旗標、不動綜合分數**（震盪指標假訊號不汙染 −100..+100）。日線負責 regime、5min 負責時機。

## [4.48.1] — 2026-06-26 — 盤中評估：即時 quote 混合（破底偵測秒級化）

### Changed
- **`intraday.py`** — `assess()` 新增 `live=` 參數 + `build()` 多抓一次 FMP `quote`（`_fetch_live_quote`）。最後一根收掉的 5-min K 棒最多落後約 5–6 分鐘（實測：12:30 K vs 12:36 quote），破底/急殺剛好發生在那幾分鐘。現在用即時 quote（~2 秒新）覆蓋 **spot 價 / 當日最高最低 / 當日量 / 昨收**——讓 **破底/止跌偵測**從「最多延遲 6 分鐘」變秒級，當日量改用官方累計值（原本是已收 5-min K 量加總、會少算最後幾分鐘）。**VWAP 與型態（高開低走等）仍用 5-min K**（quote 無 bar 歷史）。
- 每檔輸出加 `data_source`（`live_quote+5min` / `5min`）+ `quote_timestamp`；`intraday-mood.html` 市場 pill 顯示「· 即時報價」。
- **`test_intraday.py`** — 加 live-override 測試（8 asserts：live day_low 觸發破底、官方量覆蓋、timestamp 透出），共 34 asserts。
- 註：1min K 在 stable 端點回 `None`（不可用），型態類訊號最細粒度維持 5-min。

### Why
- user 問「盤中評估是不是可以拿 FMP 即時 K 棒判斷」。確認本來就是用 5-min K，但點出「最後一根未收的 K」延遲問題。混合即時 quote 後，價量判斷對齊真實盤面，不再被 bar 邊界拖慢。

## [4.48.0] — 2026-06-26 — 盤中評估引擎（Intraday weakness tape：破底/止跌/量價）

### Added
- **`skills/market-sentiment-analyzer/scripts/intraday.py`**（0 LLM，deterministic）— market_mood.py 的盤中快訊姊妹引擎。讀 FMP 盤中 5-min bars（量能 + VWAP）+ 近 ~60 日 daily bars，對 SPY/QQQ/IWM 算 signed −100..+100 盤中評估分（負=破底偏空）。偵測 **破底**（今日低跌破 5d/20d/50d 低，分級）、**止跌**（日內自低點反彈 / 跌破後收復＝假跌破）、**高開低走**、**量增價跌**（RVOL surge on down move）、跌破 VWAP、MA20 偏離、連跌天數、O'Neil 出貨日。`UNIVERSE`/`WEIGHTS`/門檻皆為檔頭常數可調。輸出 `Dashboard/intraday_mood.json`。
- **`scripts/test_intraday.py`** — 26-assert golden-fixture（破底20日+量增價跌 / 止跌收復 / 高開低走 / 強勢 / 空資料 / aggregate / risk_label 邊界），network-free，改引擎必跑 rc=0。
- **`dashboard_server.py`** — 常駐 `intraday_mood_poll_loop` daemon：美股盤中每 `INTRADAY_MOOD_INTERVAL_SEC`（預設 300s）重算 + 開機 1 張 + 每日收盤後 1 張快照（過夜不 stale）；獨立於 `_protocol_lock`／break_news。新 API GET `/api/intraday-mood/{data,state}` + POST `/api/intraday-mood/refresh`（背景跑）。
- **`Dashboard/intraday-mood.html`** — 獨立「盤中評估」面板：綜合分量表 + 觸發旗標（severity 配色 + 影響標的）+ 每檔卡片（現價/昨收報酬、日內區間位置條、RVOL、VWAP 乖離、MA20、連跌/出貨、破底/止跌/型態）。`utils.js` sidebar 加「盤中評估」nav；`index.html` signals-band 加 mini-strip。
- **`daily_update.sh` Step 9.35** — 寫盤中評估基線（非致命）。

### Why
- user 指出市場氛圍只看波動率情緒（VIX/SKEW/PCR/F&G），缺「盤中即時 + 近幾天走勢 + 成交量」與破底/止跌類訊號。本版補上一條**盤中價量探索層**：FMP 盤中分鐘 K + 量能（Finnhub 盤中 K 為付費故未用）→ deterministic 算破底/止跌/高開低走/量增價跌。與 market_mood 並列、互不汙染。**探索層，不**進入 investment_protocol 決策。

## [4.47.2] — 2026-06-22 — weekly-tech-playbook：Codex Review 整合的優化（解耦 + 去自打臉 nag）

### Changed
- **`render.py` `validate_codex_review`** — `codex_review` 改為**可選**:缺它不再 fatal、weekly 生成器可獨立重跑（原本缺 review 會 rc=1、不出任何檔，依賴反轉）。提供時才驗證結構。
- **去除自打臉 degraded**:原邏輯「非 committee-blind → degraded」對每份非盲評 review 都報 rc=2（含 Codex 自己的非盲評產出）。改為只在**明確宣稱** `review_mode=committee_blind_then_reconcile` 時才要求 `blind_artifact`（fatal），不再 by-default 扣分。
- **`review.py`** — Codex 替代配置（含 25% 現金）新增 `deployed_pct`/`cash_pct`,排名/MD/CLI 標示「部署 75%」,避免其 vs SPY alpha 被誤讀為同 beta 比較。
- **`SKILL.md`** — Step 2.5 從「（必填）」改為「（建議；對生成可選）」,與 code 一致。

### Why
- Codex review 的**內容**是強的第二意見（抓到原三籃 ~100% 部署 vs macro 建議 60–75% 的矛盾、降權抛物線動能股、檢討加 QQQ/SOXX+回撤、committee-blind 反 anchoring）——全部保留。但**工程整合**把 review 變成生成器的 fatal 必填（破壞可重跑性）且 blind-mode 檢查自打臉。本版只修這兩個 gating bug + 一個比較公平性標示,不動 Codex 的好設計。P3（schema 欄位寫死 `codex_review` 綁工具名）留待後續決定是否泛化為 `independent_review`。

## [4.47.1] — 2026-06-22 — weekly-tech-playbook：下週 LLM 檢討機制

### Added
- **`scripts/review.py`**（0 LLM）— 把過去某週方案對「檢討日收盤」評分:每檔 進場→現價 報酬、每籃加權報酬 + vs SPY alpha + 命中率、kill 觸發偵測（從 kill 文字擷取門檻價,現價跌破標 🔴）、三籃排名。輸出 `reports/<REVIEW_DATE>_TECH_PLAYBOOK_REVIEW.md`（含空白「🧠 LLM 檢討」段供 Claude turn 填質性判讀）+ `Dashboard/playbook_review.json`。觸發詞「投資方案檢討」。
- **`render.py`** 加寫 immutable dated snapshot `data/playbook_<DATE>.json` — 進場錨點,故 `Dashboard/playbook.json` 被下週覆寫後仍可回放檢討。
- **`page-playbook.js`** 頂部「上週方案檢討」橫幅 — 讀 `playbook_review.json`,顯示三籃報酬/alpha/命中率/觸發 kill;僅在 entry≠review 日顯示（避開同日 0% 退化）。

### Why
- user 要求「請 LLM 檢討的機制也寫上」。原本只有靜態 scaffold 表,無實際機制。改成兩段式:`review.py` 算硬數據（0 LLM,比照 short-term weekly_review 永不自動覆寫 config）→ Claude turn 讀數據填質性判讀並可據此改下週 selections。檢討為前瞻探索層,不回寫 investment_protocol。

## [4.47.0] — 2026-06-22 — weekly-tech-playbook skill：三籃子 $100k 科技投資方案 + Dashboard 頁

### Added
- **`skills/weekly-tech-playbook/`** — 把「從本週系統分析擬下週投資方案」固化成可重跑 skill。每次產三個各 $100k 籃子（🛡️保險 / 🔥激進 / ⚖️混合），信心分級配重（核心 $15k×3 / 標準 $10k×4 / 輕倉 $5k×3），搭最夯題材，附理由+數據+kill trigger。
  - `scripts/build_pack.py`（0 LLM 資料層）：regime（market_mood + thematic）+ 熱題排序（thematic-screener）+ 近 14 天委員會 verdict 解析（reports/<DATE>_<TICKER>.md 的 Final Score / fair value / band / decision cap）+ yfinance 報價+動能 → `data/pack_<DATE>.json`。
  - `scripts/render.py`（0 LLM）：selections → 股數+成本配重、驗證每籃 = $100k（rc 0/1/2）→ `Dashboard/playbook.json` + `reports/<DATE>_TECH_PLAYBOOK.md`（含下週檢討 scaffold）。
  - `data/selections_2026-06-22.json`：本週首版三籃實際選股。
- **`Dashboard/playbook.html` + `page-playbook.js`** — sidebar 新增「投資方案」頁，三籃可切換，顯示分級配重 / 股數 / 理由+數據 / kill / 動能 chips / 檢討 scaffold。

### Changed
- `Dashboard/utils.js`：NAV_ITEMS 加 `playbook`（portfolio group）；VERSION → V4.47.0。
- `Dashboard/i18n.js`：nav `playbook` zh/en。

### Why
- user 要把「保險 100% / 激進 100% / 混合 100% 各投 $100k 假設、附理由數據、供下週 LLM 檢討」變成常駐工具而非一次性報告。流程拆成 0-LLM 資料層 + LLM 選股 + 0-LLM 渲染驗證，可每週重跑且結果可追蹤。前瞻探索層，不入 investment_protocol 決策。

## [4.46.0] — 2026-06-20 — 現值估值 confidence 接錨點一致性（破假精確；全標的通用）

### Changed
- `investment/scripts/compute_price_framework.py` — 新增 `reconcile_confidence(fvs, frange)`：`fair_value_summary.confidence` 不再只看「有幾個錨點回傳數字」(n≥5→high)，改以**錨點離散 cv 兩段式封頂**：`cv≥0.60→low`、`0.35≤cv<0.60→medium`、`<0.35` 不動（門檻常數 `CONF_CAP_CV_LOW` / `CONF_CAP_CV_MEDIUM`）。count-based 仍存進 `confidence_count_based`，封頂原因記 `confidence_capped_by`。`compute_fair_value_range` 新增 `dispersion_ratio`（max/min 錨點倍數）。`main()` 在 MHP/archetype 之前 reconcile。`ENGINE_VERSION` → v1.1 (V4.46.0)。
- `Dashboard/page-decisions.js` `buildFvExtras` Track A（現值估值）— `anchor_dispersion_cv≥0.60` 時：FV 點改灰、非 strong、label `FV ~$X` + tooltip「單點不可靠，看區間」；caption 加 `⚠ 錨點分散 N×，單點 FV 不可靠`（橙、雙語 tooltip）。**刻意不綁 `agreement_grade`**（grade 在 cv≥0.35 即 low，因 owner_earnings_mult 是全科技股結構性低離群值會整片誤報）；cv<0.60 的中度分散維持正常單點 + MEDIUM 標示。
- `investment/scripts/test_compute_price_framework.py` — 新增 Fixture 5：三層 cv（ARM 1.20→low / AAPL 0.45→medium / tight <0.35→不動）+ dispersion_ratio。**5 fixtures, 38 asserts**。
- `Dashboard/data.json` — 一次性 backfill 既有現值 snapshot：13 筆補 `dispersion_ratio`，8 筆 confidence 重算（cv≥0.6→low：TSM/ARM/AMD/PLTR/GOOGL；0.35–0.6→medium：AAPL/NOK/MU）。

### Why
- ARM 案例：6 錨點 $3.17–$163.75（DCF/owner-earnings 把前瞻成長股當成熟現金流公司估，崩到 $3–$12），加權成單點 $52 卻標 `confidence: high`、`extreme_overvalued`。confidence 舊邏輯只數「有幾個錨點」不看「是否一致」，對輸入分散 50× 的 blend 是假精確。引擎其實已在 `fair_value_range` 算出 cv=1.20，只是沒回灌。
- **校準關鍵**：backfill dry-run 發現 12 筆有 grade 的 snapshot **全部 grade=low**（含 AAPL）—— 因 `owner_earnings_mult` 對幾乎所有科技股都是結構性低離群值，cv 普遍 >0.35。直接綁 grade 會讓科技股 confidence 一律 low、失去鑑別度。故改 cv 兩段式：極端分散（ARM 50×、PLTR）→low，中度分散（AAPL 11×）→medium。
- **通用、非 per-ticker**。不自動剔除「垃圾錨點」（median-ratio 會誤殺 ARM 的 analyst PT），重新加權交給 `hypergrowth` archetype（已存在，shadow-only 待 ≥20 session 翻轉率報告才 live）。

## [4.45.1] — 2026-06-20 — Forward glide 標籤自解釋（hover affordance + 雙語 tooltip）

### Changed
- `Dashboard/page-decisions.js` `buildFvExtras` Track B caption row：jargon chip（`glide ±N%/yr` / `FORECAST` / `ADVISORY BAND` / `<tier>↓` 倍數壓縮 / `margin↓` / `shadow-only`）改走共用 `jt()` helper — 加 dotted-underline + `cursor:help` 視覺提示，並掛**繁中/英雙語白話 tooltip**。`shadow-only` 先前無 tooltip 現補上。

### Why
- TSM 等卡片前瞻區的縮寫標籤（peg_terminal↓ / margin↓ / glide）對使用者過於 cryptic，且「逐年下降」易被誤讀為基本面衰退。tooltip 點出真正機制：**終期倍數按成長降速壓縮 + 淨利率正常化**，逐年數字是沿單一年化 glide 內插（非每年重估），且 **shadow-only 不入 live 決策**。dotted underline 提示「可 hover 查定義」。

## [4.45.0] — 2026-06-20 — 供應鏈 Wave B：UI 訊號下鑽 + FMP budget tiering + node 人工校正

### Added
- `Dashboard/page-supply-chain.js` + `supply-chain.html`（#7 UI 下鑽）— detail panel edge row 新增 `direction` chip：`⚠ 方向衝突`（紅，Nexus 有向邊反向、信心已 1.0→0.5）/ `✓ 方向確認`（綠）。node card + detail 新增 `stale`（⏳ 半透明）、`user_status`（✓ confirmed 綠框 / ⚑ flagged 黃虛線框）視覺標記。Wave A 算出的 direction/stale 訊號終於進 UI。
- `scripts/nexus/supply_chain.py`（#8 node override）— `load_overrides()` / `save_override()` / `_apply_overrides()`：user 對 node 的修正存 `nexus/supply_chains/overrides/<slug>.json`（sidecar，**永不改寫 LLM YAML**），enrich() serve 時 merge（修正欄位優先、如同手動編輯，corrected ticker 會流經 grounding+FMP）。支援 status(confirmed/flagged/none) + field 修正(ticker/market/listing/adr_ticker/local_ticker/note/proxy_tickers) + note。清空（status=none 無 note/fields）自動移除 entry。
- `dashboard_server.py` — `POST /api/supply-chain/<slug>/override`（驗 slug + node_id 存在 → `save_override` → pop `_sc_cache[slug]` 強制重 enrich）。detail panel「✓ 確認 / ⚑ 標記問題 / 清除」button → POST → reload → 重開同 node panel。
- `data_quality` 新增 `override_count` / `fmp_peers_deferred` / `fmp_budget_headroom`。
- `tests/test_supply_chain_enrichment.py` — 5 個 Wave B test（override 修正+status、clear 移除、bad status reject、budget 低時週邊 node 跳過 name-search、budget 健康時允許）。全檔 **23 pass**。

### Changed
- `scripts/nexus/supply_chain.py` `enrich()`（#5 FMP budget tiering）— spine / 有 ticker / 高 fan-out(≥2 downstream) node 列為 priority 優先驗證；budget headroom <0.5 時週邊 node 只服務 peers cache（`_fetch_peers(allow_network=False)`）並跳過 name-search，確保結構關鍵 node 不因 budget 耗盡而失驗。profile cache TTL 7d→30d（profile 幾乎不變，省 budget）。
- `nexus/supply_chains/SCHEMA.md` — 補 override sidecar + budget tiering + `data_quality` 新欄位說明。

### Why
Wave A 把方向校驗/stale 算了出來但只在 JSON；Wave B 讓這些訊號進 UI 並補上前次規劃的三項：#5 budget tiering（避免 21 chains × 30 nodes 把 2000/day budget 燒乾後核心 node 全失驗）、#7 把 direction/stale 下鑽到 detail/card、#8 讓 user 不必開 YAML 就能確認/標記/修正 LLM 畫錯的 node（sidecar 不污染 LLM 草稿）。供應鏈 8 項 gap 分析至此 Wave A+B 全收口。

## [4.44.0] — 2026-06-20 — 供應鏈 Wave A：edge 方向校驗 + corroborated 回寫閉環 + stale flag + relative heat + ADR 補全

### Added
- `scripts/nexus/supply_chain.py` `_direction_check()` — edge 方向校驗（供應鏈 gap #1）。digest co-mention 是對稱訊號（只證「相關」非「誰供誰」），改用 Nexus *directed* SUPPLIES_TO / CONTRACT_MFG_FOR edge 校驗 LLM 畫的箭頭：`confirmed` / `conflict` / `unverified`。corroborated edge 若方向與 Nexus 矛盾 → weight 1.0→0.5 + `relation_evidence.direction` 標記。
- `scripts/nexus/supply_chain.py` `export_corroborated_edges()` + CLI `--export-edges [--chain SLUG] [--export-graph-refresh]`（#2 回寫閉環）。把 digest-corroborated、方向乾淨的 edge 升級成 `bn_*.json`（schema 對齊 `build_artifacts.py`），餵 Nexus tier-1 晉升 provisional 供應鏈 edge。**opt-in batch path，不在 `enrich()` serve 路徑**（serve 維持唯讀紀律）；source 標 `supply_chain`（非 `break_news:`）故下次 enrich 不會把自己當獨立 break-news 佐證 → 無增強迴圈。跨 chain dedup 取 max support_count + source 聯集。
- `scripts/nexus/supply_chain.py` `_heat_relative()` / `_percentile()`（#6）— heat 改相對該 chain 自身 mention 分布的 33/67 百分位分級，取代絕對 magic number（≥40 hot 等）；`_HEAT_HOT_FLOOR=8` 防低活躍 chain 憑單一 mention 造 hot；活躍節點 <4 時 fallback 絕對 `_heat`。
- node 新增 `stale` / `stale_reason`（#3）— llm_only grounding + 無 heat + verification llm_only 且 chain age > `SUPPLY_CHAIN_STALE_DAYS`(45) → flag（UI 灰用，**永不刪**，不與 FMP budget off 混淆）。`data_quality` 加 `stale_node_count` / `chain_age_days`。
- `tests/test_supply_chain_enrichment.py` — 7 個 Wave A golden test（direction confirmed/conflict、stale aged vs fresh、relative-heat 高 spread downgrade、foreign ADR 升級、corroborated relation payload、conflict 排除）。全檔 18 pass。

### Changed
- `scripts/nexus/supply_chain.py` `enrich()` name_match 分支（#4）— foreign_listed node 無 ticker 但 search-name 命中 US 交易所 symbol → 視為 ADR，補 `adr_ticker` → investability 由 opaque FOREIGN 升級成可交易 proxy。
- `nexus/supply_chains/SCHEMA.md` — 補記新 serve-time 計算欄位（`direction` / `stale` / `stale_reason` / `data_quality` 擴充）。

### Why
針對供應鏈系統 8 項 gap 分析，Wave A 收口純後端高 ROI 三組：方向校驗修核心語義錯（co-mention 對稱、LLM 箭頭可能反）、corroborated 回寫把白拿的高信心訊號送回 KG 形成閉環、stale/relative-heat/ADR 三項提升 grounding 準確度與覆蓋。Wave B（UI edge 下鑽 / budget tiering / node override）留待後續。relation co-mention 門檻刻意維持絕對值：相對門檻會讓 edge 信心取決於無關 node、破壞可重現性與 golden test。

## [4.43.6] — 2026-06-20 — Decision Review 優化：agent_score_stdev 落地 + accumulating_data stall 規則 + Rec 7 常設化

### Added
- `scripts/extractors/deep_dive_extractor.py` — deep-dive `tuning_hooks` 新增 `agent_score_stdev`（四 lane score 母體標準差）+ `agent_score_count`。解鎖 TODO-013：下輪 REVIEW 可把 0–1 分數帶拆成「弱訊號(低 stdev)」vs「agent 高分歧(高 stdev)」，判別 Pattern A 是「HOLD 閾值太鬆」還是「高分歧該降倉」。Shadow 欄位，<2 lane 時為 None。
- `scripts/diff_verdict_flips.py` (NEW) — 重建 TODO-010 的 verdict flip-rate 追蹤器（原報告誤稱已備、實際從未 commit）。讀 ≥2 個 `event_index_YYYY-MM-DD.json` snapshot，量「窗口未完成(<100%)→完成(100%)」時 verdict.label 翻轉率。本輪跑 N=194 / flip_rate **13.4%** 落 observe band（與 06-07 12% 一致）→ 不加 provisional。`--json` / `--show-flips` / `--dir`，唯讀 rc=0。

### Changed
- `reports/decision_review/REVIEW_PROMPT.md` — Step -1 carry-over 新增 `stalled` 狀態：`accumulating_data` 類樣本 N 連續 3 輪不增長 → 改「以現有 N 直接評估或 drop」，不再無限 still_waiting（修 accumulating_data 模型在上游停產時的死等缺陷）。
- `reports/decision_review/ADJUSTMENT_LEDGER.md` — Rec 7 加 `standing_monitor`：heat asymmetry gap 已穩定 ≥15pp，轉常設 tripwire（gap <15pp 連 3 週才 paused），移出 Active TODO 佇列。
- `reports/decision_review/REVIEW_TODO.md` — TODO-007 → `promoted-to-ledger`（轉 Rec 7 standing_monitor）；TODO-003 → `stalled`（momentum N=24 凍結 4 週，下輪以現 N 直接評或 drop）。

### Why
本週 LLM 檢討報告（REVIEW_2026-06-20）核心發現：保守決策 miss 率是進取的 ~3 倍（59% vs 20%）、半導體佔 51% miss，根因疑在 0–1 分數帶 default HOLD 過保守——但缺 `agent_score_stdev` 無法分離「弱訊號」與「agent 高分歧」兩種成因，所有後續修正都卡在此 instrumentation。先落地該欄位解鎖判別；同時清掉兩個流程缺陷（樣本凍結死等、已穩定 Rec 仍逐週佔 TODO slot）。

## [4.43.5] — 2026-06-20 — 供應鏈 Rerun：資料新鮮度、生成模型、增量更新

### Added
- **供應鏈頁 freshness metadata**：控制列右側顯示供應鏈 `generated_at` 的新鮮度 badge：
  Fresh `0-2D`、Aging `3-7D`、Stale `>7D · Rerun`，並顯示生成 LLM 與 full/incremental mode。
- **YAML metadata**：新生成鏈條寫入 `refresh_mode`、`source_scope`、`previous_generated_at`、
  `previous_generated_by`。既有 `generated_by` / `generated_at` 現在會在 UI 明確露出。
- **CLI rerun**：`python3 scripts/nexus/supply_chain.py --theme <T> --rerun` 會載入同 slug 既有 YAML
  作為 previous-chain context。

### Changed
- `Rerun` 不再等同整份重抓。後端會載入前一版 chain，傳給 LLM 當 baseline，要求保留仍有效的
  nodes/layers/modules/edges，只根據最新 local context / model 可用 public sources 做增量更新。
- `/api/supply-chain/generate` 接受 `rerun: true`；後端 protocol log 會記錄 rerun 與 previous 是否存在。
- `SCHEMA.md` 補充 `generated_at` 不是每個底層 source 的抓取時間；需搭配 `source_scope` 與 note evidence markers
  判斷資料新鮮度。

### Why
- 使用者需要知道圖譜是哪一天、哪個 LLM 生成，才能判斷是否需要重跑；同時 rerun 應該參考前版差異更新，
  不應每次從零重建造成結構漂移。

## [4.43.4] — 2026-06-20 — 供應鏈頁：主題 Rerun 重新抓取

### Added
- **供應鏈探索頁新增 `Rerun` 按鈕**：選定既有 supply-chain theme 後，可直接把同一主題重新送進
  `/api/supply-chain/generate` 佇列，完成後覆寫同一 slug YAML 並由前端輪詢載入新版。
- Rerun 按鈕會在未選擇 chain 時 disabled；選中後 tooltip 顯示將重新抓取的 theme。

### Changed
- `page-supply-chain.js` 將 Generate / Rerun 共用同一個 queue helper，保持既有 progress pill 與輪詢行為。
- 後端不新增 API；沿用既有 `supply_chain_generate` protocol。dedup 仍只擋同 slug active/pending，不擋已完成主題重跑。

### Why
- 使用者需要針對同一供應鏈主題重新抓最新 local context / Nexus / news 後重建圖譜，不必手動重打主題。

## [4.43.3] — 2026-06-20 — 供應鏈探索：材料型產業 prompt 稽核強化

### Changed
- **`supply_chain_system.md` 新增材料/製程型供應鏈規則**：MLCC、電池、基板、光學、化學品、
  power components 等主題不再只列 finished-component makers，需拆 upstream functional materials、
  constrained minerals/additives、製程/設備瓶頸、finished-component product tiers、downstream
  demand cycles 與 substitutes/package-level alternatives。
- **新增規格/需求分層要求**：以 MLCC 為例，要求區分 high-capacitance / high-voltage / low-ESL /
  automotive-grade / AI-server parts 與 commodity 0402/0603 consumer parts，避免把 AI server 缺料
  外推成全 MLCC 週期。
- **新增 cost-driver hygiene 與 source-confidence note**：MLCC 需區分 BaTiO3/陶瓷粉、鎳或 base-metal
  electrode、銅/錫端電極、貴金屬 exposure 僅限相關 noble-metal electrode 產品、稀土/摻雜與燒結能源成本；
  note 可標 `confirmed` / `industry_report` / `inferred` / `stale` / `contested`。
- **新增 Final Self-Review**：LLM 輸出前需自查是否漏上游材料/設備/替代技術、是否過度泛化單一熱門規格、
  是否亂填 ticker/listing/stage、是否混淆 customer/deployment/manufacturing/end market。

### Why
- MLCC 討論暴露原供應鏈探索容易抓到單一應用或 finished maker，卻漏掉材料、製程、規格分層與替代技術。
  本版先用 prompt 層強化探索紀律，不改 YAML schema、不改 Dashboard parser，降低破壞面。

## [4.43.2] — 2026-06-20 — Forward Expectations calibration 誠實化：修 gate 假性 fail（同口徑 + 已到期窗 + 去重）

### Fixed
- **`forward_expectations_calibration.py` v2 — 三個方法學缺陷讓 shadow→live gate 假性 fail**
  （WAPE 0.77 / bias −0.46 / n=100，全是 artifact，非引擎預測差）：
  - **基準錯配**：原本拿 consensus **多年 forward CAGR** 比 `derived.yoy_growth` 的**單年 trailing
    YoY**（蘋果比橘子；CAGR 內含減速 < 火熱單年 → 81/100 系統性偏低 → bias −0.46）。改為對
    **同窗 realized CAGR**：由 `annual_growth` 各 FY YoY 幾何平均出 [window_from, window_to] 同口徑
    年化率（`_realized_window_cagr` / `_geomean_cagr`，sign-flip 年回 None 不硬算）。
  - **未到期就計分**：forecast 窗 2027–2031，但 actual 取的是 2026 trailing。改為 `window_to >
    最新已實現 FY` → `actual_not_comparable_yet`（不計分）；已到期但缺窗內某 FY → `actual_basis_unavailable`
    （**不**退回 trailing YoY）。
  - **重複 snapshot 灌水 n**：同股 re-run 寫多份近似 snapshot（8× AAPL 算 8 row）。
    `_latest_snapshot_per_ticker` 只留每股最新（依 generated_at），sample 反映真實廣度。

### Changed
- 實測 gate 由 **fail (WAPE 0.77, n=100)** → **insufficient_evidence (comparable=0)**：56 snapshot
  檔 → 13 去重 ticker → 48 forecast row 全 `actual_not_comparable_yet`（最早窗 2027 > 最新實現 FY 2026）。
  仍誠實擋住 shadow→live，但理由正確（無已到期窗可計分，非引擎差）。calibration golden 9→25 asserts。

### Why
- gate 是 shadow→live 的唯一閘；它用錯指標就會永遠誤判，EXP-4.5 升 live 報告也建立在錯數據上。
  治本是「同口徑 + 只比已實現 + 去重」，讓 gate 反映事實：目前樣本不足（窗未到期），而非預測不準。
  待 2027+ 窗陸續到期，calibration 才會累積真正可計分的 comparable row。

## [4.43.1] — 2026-06-20 — 供應鏈外股常見公司 backfill

### Added
- `supply_chain.enrich()` 新增 deterministic 外股 backfill map：舊 YAML 只要有 `listing:
  foreign_listed` 且公司名命中常見台/韓/日/歐供應鏈公司，就自動補 `market/exchange/local_ticker/
  adr_ticker/country`。
- 初始覆蓋：TSMC、Samsung Electronics、SK hynix、Tokyo Electron、Advantest、Disco、
  Lasertec、Renesas、Murata、Ibiden、Shinko Electric、Hon Hai/Foxconn、Quanta、Wistron、
  Inventec、Pegatron、Wiwynn、Delta Electronics、MediaTek、ASE、GlobalWafers、Nanya、
  Winbond、ASML、ASM International、Infineon、STMicroelectronics。

### Fixed
- 舊供應鏈 YAML 未填 `market/local_ticker` 時，台股/韓股/日股節點會退回顯示 `FOREIGN`。
  現在常見名稱會直接顯示 `TW:2330`、`KR:005930`、`JP:8035` 等；人工填過的欄位不會被覆蓋。

### Why
- V4.43.0 已讓新生成供應鏈能填本地市場資訊，但既有鏈條仍缺 metadata。backfill 讓舊資料立即
  改善，不需要一次手改所有 YAML。

## [4.43.0] — 2026-06-20 — 供應鏈頁：外股市場標示 + 上下游投資摘要

### Added
- **供應鏈節點市場欄位**：YAML / generator schema 新增 `market`、`exchange`、`local_ticker`、
  `adr_ticker`、`country`、`investability`、`proxy_tickers`。台股/韓股/日股不再被壓成
  「未上市」；前端卡片可顯示 `TW:2330`、`KR:005930`、`JP:8035`、`ADR:TSM` 等。
- **`chain_report` deterministic 摘要**：`supply_chain.enrich()` 產出可投資節點、瓶頸/槓桿節點、
  私有/觀察節點與 proxy、關係信心統計、高信心上下游關係。0 LLM，僅使用現有 YAML、Nexus、
  digest relation evidence 與 FMP 公司 profile。
- **Dashboard 上下游投資摘要面板**：供應鏈圖上方新增「可投資標的 / 瓶頸節點 / 私有公司與替代標的 /
  高信心關係」四欄，讓頁面從純探索圖譜升級為可掃讀的上下游報告入口。

### Changed
- 供應鏈生成提示從「US-equity supply-chain analyst」改成「global supply-chain analyst for a
  US-focused investor」，明確要求外國上市公司填本地 market/ticker，且只在有明確重疊時列
  private/pre-IPO proxy。
- 供應鏈 detail panel 新增市場與可投資性，legend 將「外股」改為「台/韓/日等外股」。

### Why
- 原頁面把許多台股/韓股/日股節點和真正私有公司混在一起，容易把「非美上市」誤讀成「不可交易」。
  供應鏈投資決策需要先分清交易可及性、ADR/複委託需求與 private proxy。
- 單純節點圖回答的是「誰連到誰」，但投資上更需要「誰是瓶頸、誰有上下游槓桿、哪些關係有佐證、
  哪些私有公司可用上市替代標的觀察」。本版先用 deterministic report 做探索層摘要，不改
  investment protocol 的評分、門檻或部位規則。

## [4.42.0] — 2026-06-20 — Forward Expectations 貨幣正規化：修 ADR (TWD/EUR…) 前瞻股價 ~30× 爆衝

### Fixed
- **`forward_expectations_price_range.py` — reporting→trading 貨幣單位錯配（治本）**：
  FMP 對外國註冊 ADR（TSM→TWD、ASML/SAP→EUR…）的三表/估計用**記帳幣別**（TWD），
  但 ADR 股價 / 市值 / multiple anchor 是**交易幣別**（USD）。引擎把 TWD EPS 直接乘上
  USD P/E → 前瞻股價膨脹整整一個 FX 倍率（TSM base 從 broken **$11,491 (+2598%)** 變正常
  **$363**，對齊 blended FV）。新增 `reporting_to_trading_fx` 參數：EPS / revenue-per-share /
  fcf-per-share 在乘 price-currency multiple **前先 ÷ fx** 轉成 USD（含 derived band 自洽、
  trajectory consensus_eps 顯示）。
- 新增純函式 **`resolve_reporting_fx()`**（可離線測）：優先序 reportedCurrency==USD → 1.0；
  FMP forex `{CUR}USD` → 1/rate；否則由 statement TTM EPS vs ADR EPS 的 currency-scale ratio
  （>5×）反推；皆無 → parity。
- **Sanity gate（防護網）**：price-basis forecast 的 base target / 現價 **>6× 或 <1/6** 視為
  漏網的幣別錯配 → 退回自洽 advisory band（base≈現價，FX 抵消）並標 `currency_unit_suspect`
  warning，永不把爆炸值寫進卡片。anchor 可用導致無 derived 退路時，**動態合成** current-price
  derived band。

### Changed
- **`forward_expectations.py`** 新增 `_currency_normalization()`：fetch **income-statement
  `reportedCurrency`**（權威來源；**非** `profile.currency`，後者對 ADR 是 USD 交易幣別會誤判 parity）
  + forex pair + quote EPS，best-effort 餵 `resolve_reporting_fx()`；no-fetch / 失敗 → parity
  由 sanity gate 兜底。輸出新增 `currency_normalization` 節點。
- **`forward_expectations_margin_normalization.py`** 標 `value_currency_basis="reporting_currency"`
  註明 normalized_eps 為記帳幣別、轉換在 price_range 發生。

### Why
- TSM「未來前瞻」glide chart 對非 USD 記帳 ADR 直接畫衝天線（+2598%），雖屬 shadow-only **不污染**
  live 決策（buy_threshold / position_size 不受影響），但卡片數字為 garbage。`--no-fetch` advisory
  band 路徑（純現價 ±vol）因自洽而恰好遮住此 bug，須 fetch 歷史 multiple anchor 才暴露。
- 治本（FX 轉換）+ 防護網（sanity gate）雙層：FX 正確時 forecast 存活；FX 不明 / 偵測失敗時
  gate 仍保證不爆。新增 TSM TWD golden fixture（含 fx-applied 與 fx-unknown 兩路）防回歸。
- 連帶查證 live blend 的 `peer_pe_implied`（compute_price_framework）：`eps_ttm = 現價(USD)/pe_self(USD)`
  → **USD 自洽，無同款污染**；偏高純為 peer-multiple 失配，已由 LOW-agreement 折讓。

## [4.41.0] — 2026-06-18 — 決策卡 v5.1 估值區改 price-axis number-line 視覺化

### Changed
- **`page-decisions.js` `buildFvExtras` 全重寫**：原本 6 條扁平 monospace 文字列
  （Range / 5D Band / Implied CAGR / Archetype / Forward / Glide）改成兩條 CSS 定位的
  **price-axis number-line track**：
  - **Track A 現值估值** — p25–p75 range 著色帶（顏色=agreement grade）+ FV tick + 現價
    marker（現價>FV 紅、<FV 綠，spatially 讀出高估/低估）；caption 收 AGREE grade / anchor
    count / min–max anchor / range_verdict。
  - **Track B 未來前瞻 (shadow)** — **time×price 折線圖**（X=年、Y=推估價）：base glide line
    現價→horizon，terminal bear/bull 畫成 fan + %；下方保留每 FY「年→價」精確 chips。
    bear/base/bull 同屬一個 horizon 年，純價格軸無法表達「哪一年」，故改時間軸折線。
    caption 收 glide 年化%/yr / FORECAST·ADVISORY badge / compress·margin↓ / shadow-only。
  - momentum signal / implied 5Y FCF CAGR / archetype shadow 收成 track 下方 compact chips。
- 新增 helper **`buildValAxis(domLo, domHi, band, markers, h)`**（Track A，純 CSS price axis）
  + **`buildGlideChart(refPrice, traj, fe, zh)`**（Track B，inline SVG time×price 折線，
  overflow-visible labels），皆 themeable（`--text-main` / hex）。

### Why
- v5.1 卡估值資料很豐富（現值 vs 6-anchor range vs 5 年 forward vs glide），但原本全是
  等寬扁平文字列，沒有共同尺規、沒有視覺層次，掃讀時看不出「現在高估、未來大漲」這個
  present-vs-future 張力。改成同尺規 number-line 後一眼讀出各價位相對位置。
- 全 advisory / shadow-only 標籤、tooltip、版本閘行為不變；缺 block 的舊 entry 仍整段隱藏。

## [4.40.1] — 2026-06-17 — 修 V5.1 卡片整段空白（fair value + red team 被版本閘擋掉）

### Fixed
- **`page-decisions.js` V5.1 render 回歸**：4.40.0 新增 `detectProtocolVersion` → 有
  `forward_expectations.trajectory` 的卡判為 `'V5.1'`，但卡片組裝處 `v5Block` / `redTeamBlock`
  仍硬閘 `version === 'V5.0'`。結果 V5.1 卡**整段 fair value summary（6-anchor blend）+ Forward
  shadow row + Glide trajectory + Red Team block 全部不渲染** → 卡片看起來只剩 dual-track entry，
  資訊大幅消失。閘改為 `=== 'V5.0' || === 'V5.1'`，V5.1 完整繼承 V5.0 render path 再疊上前瞻列。

### Why
- 新版本徽章不該砍掉它本要「補強」的區塊。V5.1 = V5.0 + 前瞻估值，必須是**疊加**不是**取代**。

## [4.40.0] — 2026-06-17 — PEG terminal P/E + 近年年化 glide trajectory + 修 limit=3 估計截斷（EXP-3.5）

### Fixed
- **`fetch.py` annual estimates `limit` 3→6**：FMP `/stable/analyst-estimates?period=annual`
  以日期**降冪**回傳，`limit=3` 只拿到最遠 3 年（NVDA FY2029/30/31），把覆蓋最完整的近年
  （FY2027 39 analysts、FY2028 41）整批丟掉。連帶後果嚴重：截斷後的遠期營收看似**人為走平**
  （NVDA 584→529→585B ≈ 0% 成長），讓 EXP-3.4 把高成長股**誤判成 mature** → 壓到 22x →
  NVDA base ≈ $252（先前被當成「命中」的數字其實是壞資料假象）。`limit=6` 取回近年。

### Changed
- **EXP-3.5 PEG terminal P/E（`forward_expectations_multiple_compression.py` v1.1）**：P/E 壓縮
  由「成長 tier 絕對天花板」改為**綁定 terminal 成長**：`terminal_pe = clamp(2.2 ×
  terminal_growth_pct, 20, 60)`，歷史 band 拉到 `min(historical_p50, terminal_pe)` 並等比保留
  dispersion。`terminal_growth` = 進入終期年的營收 YoY，含**薄覆蓋雜訊守門**（終期年相對前一年
  re-accelerate 且 analyst<20 → 改用前一年 YoY，`terminal_growth_basis=prior_year_yoy_terminal_noise_guard`）。
  不再用固定 35x 砍掉 AI 基建複利股，也不凍結今天的高倍數。NVDA 57x→30x（13.7% 終期成長）、
  ARM 151x→60x（觸頂）。`compress_anchor` 因此移到 financial bridge 之後執行。
- **近年年化 glide trajectory（`forward_expectations_price_range.py` v1.1）**：新增 `trajectory[]`，
  逐 FY 給目標價 = 錨定 terminal target 的幾何 glide（`current ×(terminal/current)^(t/T)`，
  年化率沿途恆定），附 `years_out`/`coverage`/`thin_coverage`(<20)/`consensus_eps`/`is_terminal`。
  **不**用今天高倍數重估每年（避開 tautology 爆衝）。已申報/過去 FY（years_out≤0）剔除。headline
  `horizon_date` 維持 terminal（`horizon_basis=terminal_margin_normalized`），因 mature 倍數 +
  margin 正常化只在成長冷卻的終期成立。
- bridge row 加 `coverage`（per-FY analyst 數）；`forward_price_range.py` 文字輸出、`bridge.py`
  L1 payload、**`decisions.html` 決策卡新增「Glide」行**（`page-decisions.js`：base 年化 + 逐年
  chips + thin 標記 + hover cum%/ann%/coverage）+ Forward 行補 horizon 年數。
- **決策卡版號 badge 新增 `V5.1`**（`page-decisions.js` `detectProtocolVersion`）：卡的
  `forward_expectations.trajectory` 非空（= snapshot 已用 4.40 新引擎重生）→ 角落版號顯示
  teal `V5.1`，與舊 `V5.0`/`V4.x` 卡區別。舊 snapshot 無 trajectory → 維持原版號。系統全域
  VERSION 不動（V5.1 是 per-card protocol 標記，非系統版本）。

### Net effect (NVDA)
- terminal base $252（壞資料）/ $1024（正確資料 + 無壓縮）→ **$562**（PEG 30x，ann ~+24%/yr）。
- 年化 glide：FY2027 ~$237(+14%) → FY2028 ~$294(+42%) → terminal FY2031 $562(+171%)。

### Why
上個 session 驗證的 $252 是 `limit=3` 截斷造成的「假成熟」假象；修對資料後 NVDA 變回 hypergrowth
→ 55x → terminal $1024（定價完美、不可作 base）。根因是 EXP-3.4 用「到 horizon 的 CAGR」決定壓縮，
把「現在成長快」等同「terminal 該給高倍數」。改成 PEG-綁定 terminal 成長後，倍數隨成長降速自動壓縮，
且近年年化目標價直接呈現，解決「不該只看 4.6yr 單點」的問題。Shadow-only，不入 live 決策。

### Tests
- `test_forward_expectations_multiple_compression.py`（+PEG/noise-guard/clamp asserts）、
  `test_forward_expectations_price_range.py`（+glide trajectory）、
  `test_forward_expectations_financial_bridge.py`（+coverage）全綠；forward 全套 + adapter +
  framework golden rc=0。

## [4.39.0] — 2026-06-17 — Margin 正常化 path：去除凍結壟斷利潤率的樂觀（EXP-3.4b）

### Added
- `forward_expectations_margin_normalization.py`：forward bridge 把現行淨利率凍結到 horizon，對超常利潤率
  公司（NVDA ~60%，AI 加速器稀缺 + CUDA/networking/rack-scale 鎖定 + hyperscaler 急單）等於把壟斷經濟學
  灌進 headline EPS。本層**不做機械式 sector 均值回歸**（會低估真平台壟斷），改用 durable-platform **retention
  path**：bear 0.62 / base 0.80 / bull 1.00（bull 維持今日 margin = 壟斷持續 = tail）。bridge：forward 營收
  scenario × scenario margin → normalized NI → normalized EPS → 估值。只在 margin >40%（超常）才觸發；
  並設 floor（own recent margin × 0.85）保護結構性高 margin franchise（V/MA 類）不被過度壓縮。
- `test_forward_expectations_margin_normalization.py` 18 asserts。

### Changed
- `forward_expectations_price_range.py`：`build_future_price_range` 新增 `eps_override`；margin 正常化時
  EPS path 用 normalized EPS band（bear=rev.low×bear_margin、base=rev.base×base_margin、bull=rev.high×bull_margin），
  標 `eps_basis=margin_normalized` + warning。
- `forward_expectations.py` 算 margin_normalization（用 margins_8q net median 當 own-history floor）並注入 price_range；payload 加 `margin_normalization`。
- report / CLI / 決策卡 Forward row 顯示 margin path（held→bear/base/bull + `margin↓` tag）。

### Why
- user 校準（同意方向、修正力度）：NVDA $11.3T bull 是「高成長 × 60% margin 長維持 × 倍數不壓」三樂觀疊乘 → 該標 tail
  非 base。最大樂觀來源是凍結 60% margin（半導體常態 20-35%，但 NVDA 是 GPU+networking+system+CUDA 平台，合理
  normalized 不該回 25-35% 而是 bear 35-40/base 45-50/bull 55-60）。實作 retention path（非 sector reversion）後
  **NVDA bear $115(-45%)/base $252(+21%)/bull $473(+126% tail)** — base 落在 user 目標 $220-260。倍數(EXP-3.4)+margin
  (EXP-3.4b)兩軸都正常化，bull-tail 保留。仍 shadow-only，自動流入 L1 決策卡。

## [4.38.0] — 2026-06-17 — 倍數壓縮：前瞻價格區間去樂觀化（EXP-3.4）

### Added
- `forward_expectations_multiple_compression.py`：成長分級倍數壓縮。歷史 multiple regime 反映**過去**成長，
  套在 consensus 說已攤平的 horizon EPS 上會嚴重高估（NVDA 57×、ARM 151×）。本層把歷史倍數 haircut 到
  **前瞻成長**支撐的水準：`effective = historical × growth_factor`（跨 P/E·P/S·P/FCF 同口徑）；P/E 另加每階
  絕對上限（cap median + 等比例縮放 band 保留 dispersion）。成長訊號 = consensus estimate-window CAGR
  （eps→P/E、revenue→P/S）。階：hypergrowth ≥25%（×1.0/≤55×）→ mature <3%（×0.4/≤22×）。
- `test_forward_expectations_multiple_compression.py` 32 asserts。

### Changed
- `forward_expectations.py`：build_multiple_anchor 後接 compress_anchor（用 consensus eps/rev CAGR）再進 price_range。
- `forward_expectations_price_range.py`：multiple_range 帶 `compressed/growth_tier/compression_factor/historical_band`，
  compressed 時 method = `historical_regime_growth_compressed`。
- `forward_expectations_report.py` + `forward_price_range.py` CLI + 決策卡 Forward row 顯示壓縮（tier↓ + 歷史→套用 P/E）。

### Why
- EXP-3.4 / code review 缺點：NVDA 實測 base $776（+271%）、bull $1219（mcap ~$30T 物理不可能）；ARM base $870。
  原因是死守 hypergrowth 倍數。壓縮後 **NVDA bear $162(-23%)/base $298(+43%)/bull $468(+124%)**、
  **ARM bear $256/base $317/bull $373（全負，誠實標 ARM 即使用富裕前瞻倍數仍過貴）** — 可信且保留 dispersion。
  consensus 2029-2031 EPS CAGR 1.6% → mature tier → 57×→22×。仍 shadow-only，自動流入 L1 決策卡。

## [4.37.0] — 2026-06-17 — Forward Expectations 進決策中心（L1 advisory，option b auto-fetch）

### Added
- `bridge.py` `load_forward_outlook(ticker)`：決策中心每檔 ticker 掛 `forward_expectations` advisory block
  （future price range bear/base/bull + upside% + forecast/advisory_band 狀態 + expectations gap + cohort base-rate）。
  **option (b)**：無 fresh snapshot 時自動跑 `forward_expectations.py --ticker <T> --self-assemble`（含 fetch，
  即新分析的股自動有前瞻），TTL 快取（預設 20h，`FORWARD_OUTLOOK_TTL_SEC`）+ 每次 bridge run cold-fetch 預算
  上限（預設 8，`FORWARD_OUTLOOK_BUDGET`）+ 可關（`FORWARD_OUTLOOK_FETCH=0`）。失敗 non-fatal。
- `Dashboard/page-decisions.js` `buildFvExtras`：卡片 Layer-3 advisory 加 Forward row，FORECAST（綠）/
  ⚠ ADVISORY BAND（橘，非前瞻只是現價波動帶）badge + shadow-only 標記。

### Why
- 讓 forward 前瞻**出現在決策中心**供肉眼對照（protocol fair value vs forward price range），同時嚴守治理：
  純 advisory row，**不**進 score / verdict / fair_value blend / sizing。升到真正影響決策（L2）仍須
  `forward_expectations_success_criteria.py` verdict=pass + user 批准（現況 insufficient_evidence）。
  ARM 卡實測 Forward $702/$870/$1024（FORECAST, historical regime, shadow-only）。

### Ops
- 生效需重啟 dashboard_server 並重跑 bridge（或下次 `daily_update.sh` 自動跑）。冷啟動每 run 補 8 檔，數次跑滿。

## [4.36.0] — 2026-06-17 — Semiconductor business-model adapter（EXP-3.1 首個跨模式擴充）

### Added
- `forward_expectations_adapters/semiconductor.py`：產品/晶片廠 adapter（end-market 分類：Data Center /
  Gaming / Client / Automotive / Embedded / DRAM / NAND / Networking…）。exposure map + driver tree
  （unit/wafer volume × ASP × mix、utilization、capex cycle）+ transmission gate（AI datacenter capex →
  segment，需 conversion+evidence）+ independent lane（缺 driver/evidence 時 blocked）+ driver_model。
  **刻意把 royalty/license 名稱讓給 royalty_ip**（晶片廠出貨實體 unit；IP 授權收 royalty）。
- registry `ADAPTERS` 加入 semiconductor；evaluate_adapters 仍取最高信心 matched。
- `test_semiconductor_adapter.py` 30 asserts（match 分離、pure-play memory dram+nand、exposure、driver tree、
  transmission gate、lane blocked/available、registry 選擇）。

### Why
- EXP-3.1：原本只有 royalty_ip → 只有 ARM 走得到 independent lane，其餘半導體股全靠 consensus + 歷史
  multiple regime。本版補上 universe 最大宗的半導體模式，讓 NVDA/AMD/MU 等也有 end-market 結構化 driver
  tree 與 evidence 缺口清單（lane 仍誠實 blocked 直到 volume/ASP/utilization 證據到位）。仍 shadow-only。

## [4.35.0] — 2026-06-17 — Base-rate Cohort Library：可稽核同類群（EXP-3.2）

### Added
- `forward_expectations_cohort.py`：以**明確固定 criteria**（sector exact + growth stage / margin tier /
  size tier ±1 tier，≥2/3 graded dims）選 cohort，記錄選取理由 + 每名 member match reasons，防事後挑樣本。
  純 deterministic engine（0 LLM / 0 network）。
- `test_forward_expectations_cohort.py` 23 asserts（tier 分類、sector 必配、adjacency 計數、distribution、
  None-cagr 排除、insufficient 降級）。

### Changed
- `forward_expectations.py` `base_rate_lane`：改用 cohort 推 peer 營收 CAGR 分布（median/p25/p75），
  附 `cohort`（rationale + members + classification）與 `basis`（cohort / raw_peers_fallback）。
  cohort <3 名時 fallback 既有 raw-peer 邏輯。複用既有 income-statement 抓取 + 24h-cached profile，近乎零額外 fetch。
  實測 ARM → 9 名 Technology cohort、median CAGR 0.135（grounded anti-fantasy ceiling）。

### Why
- EXP-3.2：原 base-rate 直接吃 FMP raw peer list，混不同成長階段/margin/規模且易事後挑樣本。本版把 base-rate
  變成可稽核同類群：criteria 與 tolerance 在選取前固定、每名 member 記錄為何入選，提升「市場上同類公司實際成長」
  這個 anti-fantasy ceiling 的可信度。仍 shadow-only，不改 live 決策。

## [4.34.0] — 2026-06-16 — Forward 成功標準 gate + consensus lane 獨立性驗證（EXP-0.4 / EXP-1.2）

### Added
- `forward_expectations_success_criteria.py`：唯讀驗收尺 + EXP-4.5 shadow→live gate。八條 falsifiable
  criteria（sample 充足度 / WAPE ≤0.30 / directional ≥0.60 / |bias| ≤0.20 / driver explainability /
  source completeness / same-metric gap 可驗證 / **非估值膨脹**）。verdict pass/fail/insufficient_evidence；
  `shadow_to_live_gate` 僅 pass 時 true，且 pass 為必要非充分（仍需 user 批准）。實測現況 n=3<15 →
  insufficient_evidence、gate False（誠實擋住）。
- `test_forward_expectations_success_criteria.py` 19 asserts（樣本不足擋 promotion、達標 pass、WAPE 超標 fail、
  系統性樂觀 bias fail、rejected evidence fail、無 snapshot 不 silent pass）。
- `forward_expectations_schema.md` 新增 Success Criteria 章節。

### Changed
- `test_forward_expectations.py` 加 EXP-1.2 guard（45→48 asserts）：divergent base-rate median **不得**覆蓋
  consensus revenue CAGR，只能並列為 comparator（驗證 consensus 為獨立 lane）。

### Why
- EXP-0.4：R1 把 ARM future price 推到 $870，但沒有成功標準就無法判斷對錯。本版把「成功」定義成可驗證的
  預測品質 + 來源完整度 + 治理，明確排除「估值變高=成功」，並當成 shadow→live 硬門檻。
- EXP-1.2：明確驗證歷史 base-rate median 不會無條件壓過 analyst consensus（現設計已分離，補 falsifiable test）。

## [4.33.0] — 2026-06-16 — Scenario 分歧度改由 evidence 決定（EXP-R3）

### Changed
- `forward_expectations_scenario_builder.py` v2.0：移除固定 ±0.05 / ±0.10 step。bear/bull 改由
  **consensus 營收 low/high envelope** 推導 CAGR band（near→far bridge row 的 point/low/high 各算 CAGR）
  — 真 evidence dispersion，非寫死百分比。driver-level driver（royalty units/rate/…）因 spec 只有單點
  value、無 per-driver dispersion evidence，改為 `base_operating_drivers_held`（揭露但不捏造分歧），
  唯一 spread 來自 envelope CAGR。
- 缺 evidence dispersion（無 2-row 時間跨度 / 無 low<high）時 **降級 qualitative_driver_watchlist**，
  watchlist 標 `no_evidence_based_dispersion_for_scenario_spread`，不再用固定 step 偽裝 driver scenario。
- `test_forward_expectations_scenario_builder.py` 重寫（26→33 asserts），涵蓋 envelope band、held drivers、
  無 dispersion 降級、single-row 降級。

### Why
- V4.30.0 code review 缺點 #3：scenario 的 bear/base/bull 分歧度是寫死 ±10% / ±5pp，違背 EXP-2.4
  「scenario 必須改 driver、不得固定百分比加減」精神。本版把分歧度綁回 analyst 共識 low/high 實際
  dispersion，缺證據就降級，不捏造。仍 shadow-only，不產 fair value / target / verdict。

## [4.32.0] — 2026-06-16 — Forward Bridge 凍結假設透明化 + 敏感度（EXP-R2）

### Added
- `forward_expectations_financial_bridge.py`：top-level `assumption_basis: historical_ratios_held_constant`
  + `held_constant_assumptions`（逐項揭露 gross/operating/net margin、fcf margin、capex、share count、tax
  皆 held-constant 於歷史值）+ `terminal_sensitivity`（最遠 row 的 net-margin ±20% 與 share count ±10%
  對 net income / EPS 的彈性；明確標 `illustrative_elasticity_not_a_scenario`，非 bear/base/bull）。
- `forward_expectations_report.py` Financial Bridge Risk 區塊新增 held-constant 揭露 + sensitivity 行（人讀）。
- `test_forward_expectations_financial_bridge.py` 25→35 asserts。

### Why
- V4.30.0 code review 缺點 #2：bridge 把 margin/share 凍結於歷史值，forward net income =
  forward_revenue × 歷史 net margin 其實是恆等式、看似新資訊。本版不改演算法，而是**誠實揭露**這是
  held-constant 假設並量化它的敏感度，讓讀者知道數字對假設多脆弱。仍 shadow-only，不產 fair value。

## [4.31.0] — 2026-06-16 — 打破 Future Price Range 套套邏輯：歷史 multiple regime anchor（EXP-R1）

### Added
- `forward_expectations_multiple_anchor.py`：自身歷史估值 regime anchor。讀 FMP `ratios`
  annual P/E、P/S、P/FCF（每年用當年股價→與今日價無關），輸出 median/p25/p75 band。
  穩健 gate：每個 metric 須 ≥2 個正值年且 p75/p25 dispersion ≤ 3.0 才 `usable`，否則 reject
  → builder 自動改用較穩的 metric（如 ARM P/E 太噪時退 P/S）或誠實降級。
- `test_forward_expectations_multiple_anchor.py` 21 asserts（穩定/噪聲/樣本不足/負值年/no-fetch）。
- price_range golden fixture 擴至 31 asserts（historical anchor 破套套邏輯、advisory 降級、explicit 仍優先）。

### Changed
- `forward_expectations_price_range.py` 倍數優先序改為 **explicit → historical regime → derived band**，
  並標 `multiple_quality`（explicit/historical/derived）。只剩 derived band 時 status 改
  `advisory_band_only` + warning `current_price_volatility_band_not_forecast`（誠實標示 base≈現價、非前瞻）。
- `forward_expectations.py` fetch 段算 anchor 並傳入 price_range；payload 加 top-level `multiple_anchor`。
- `forward_price_range.py` CLI：`advisory_band_only` 時印 ⚠️ disclaimer + 提示 `--fetch`。
- `forward_expectations_schema.md` Future Price Range 章節改寫倍數優先序與 regime-persistence 說明。
- TODO `EXP-R1` 完成。

### Why
- V4.30.0 code review 致命缺點 #1：無 explicit forward multiple 時 `base_multiple = current_price /
  forward_eps`，使 base target ≡ current price（ARM/NVDA 實測 base +0.0%），future price range 退化成
  現價 ±15% 波動帶、看似 forecast 實非前瞻。本版接 price-independent 歷史 regime anchor 打破套套邏輯
  （ARM `--fetch` base 由 ≡現價 變成 forward EPS × 歷史 P/E 的真前瞻），無 anchor 時誠實標 advisory band。
  仍 shadow-only，不改 live `fair_value_summary` / `decision_lock` / threshold / sizing。

## [4.30.1] — 2026-06-16 — Forward Expectations 數值安全硬化（EXP-R4）

### Added
- `test_forward_expectations_numeric_safety.py` 15 asserts：除零 / 負分母 / 零現價 /
  零 forward EPS 的降級行為，並驗證每個 shadow 輸出都通過 `json.dumps(allow_nan=False)`。

### Changed
- Forward Expectations 全線 data-output `json.dumps` 加 `allow_nan=False`（12 個 script），
  任何 NaN/Inf 會在序列化當下 fail-fast，不吐 `Infinity`/`NaN` 非法 JSON token 炸下游 parser。

### Why
- V4.30.0 code review 發現 `gap._compare` / scenario `change_vs_base` / bridge margin 等除法雖多數
  已有 guard，但缺最後一道 `allow_nan=False` 防線。本版補上 durable guard + 回歸測試；
  仍 shadow-only，不改 live `fair_value_summary` / `decision_lock` / threshold / sizing。

## [4.30.0] — 2026-06-16 — Ticker Future Price Range CLI

### Added
- `forward_price_range.py`：ticker-facing wrapper，使用者輸入一個 ticker 即可直接看到
  current / horizon / bear-base-bull future price range / method / warnings。
- `test_forward_price_range.py` 13 asserts，覆蓋 range extraction、human-readable output
  與 missing future_price_range degradation。

### Changed
- TODO `EXP-3.4b` 完成：`python3 investment/scripts/forward_price_range.py ARM`
  已可直接輸出 ARM future price range。

### Why
- V4.29.0 已在完整 Forward Expectations JSON 中產生 `future_price_range`，但使用者驗收要求是
  「輸入一個 ticker，可以找到推估的未來價格區間」。本版補上直接入口，不需要翻完整 JSON。

## [4.29.0] — 2026-06-16 — Forward Future Price Range（shadow）

### Added
- `forward_expectations_price_range.py`：將 forward financial bridge 映射成
  `future_price_range`，支援 EPS×P/E、Revenue/share×P/S、FCF/share×P/FCF。
- `test_forward_expectations_price_range.py` 19 asserts，覆蓋 explicit multiple range、
  current-market derived multiple band、Revenue/P/S fallback、FCF/PFCF fallback 與
  insufficient inputs。

### Changed
- `forward_expectations.py` 新增 top-level `future_price_range` block。
- `forward_expectations_report.py` 新增 Future Price Range 區塊，顯示 bear/base/bull
  target price、upside、metric 與 multiple。
- `forward_expectations_schema.md` 正式定義 shadow `future_price_range` contract。
- TODO `EXP-3.4a` 完成；core golden fixture 擴至 45 asserts，report renderer 擴至 22 asserts。

### Why
- 使用者最終驗收是「輸入一個 ticker，可以找到推估的未來價格區間」。本版先把 forward layer
  接到 shadow future price range，仍不改 live `fair_value_summary`、decision lock、threshold 或 sizing。

## [4.28.0] — 2026-06-16 — Royalty/IP Driver-Level Scenarios（shadow）

### Added
- `royalty_ip` adapter 新增 `driver_model`，把 promoted primary-source drivers 整理成
  scenario builder 可消費的 driver-level contract。
- `test_forward_expectations_scenario_builder.py` 擴至 26 asserts，覆蓋 Royalty/IP
  driver-level bear/base/bull cases 與 aggregate revenue CAGR fallback。
- `test_royalty_ip_adapter.py` 擴至 32 asserts，覆蓋 data-center exposure gate 與
  driver model shape。

### Changed
- `data_center_segment_exposure` 納入 Royalty/IP numeric lane 必要 driver。
- `forward_expectations_scenario_builder.py` 優先使用 adapter `driver_model`，讓
  bear/base/bull 改變 royalty units、royalty rate/value per unit、license conversion、
  data-center exposure 與 revenue CAGR；缺 driver model 時才 fallback 到 aggregate
  revenue CAGR sensitivity。
- `forward_expectations_report.py` 的 scenario table 可呈現多 driver case。
- TODO `EXP-2.4b` 完成。

### Why
- V4.27.0 的 builder 已有安全 gate，但 numeric case 仍太粗，只是 revenue CAGR ±5pp。
  本版把 ARM Royalty/IP scenario 推到 explicit driver 層，仍維持 shadow-only，不產生
  fair value、target price、verdict、threshold 或 sizing。

## [4.27.0] — 2026-06-16 — Operating-Driver Scenario Builder（shadow）

### Added
- `forward_expectations_scenario_builder.py`：讀取 scenario policy，只有
  `numeric_scenario_allowed` 時才產生 bear/base/bull operating-driver cases。
- `test_forward_expectations_scenario_builder.py` 20 asserts，涵蓋 numeric allowed、
  policy allowed 但 base driver 缺失、guidance range overlay、qualitative watchlist
  與 insufficient inputs。

### Changed
- `forward_expectations.py` 新增 top-level `operating_driver_scenarios` shadow block。
- `forward_expectations_report.py` 新增 Operating-Driver Scenarios 區塊；numeric case 只顯示
  revenue CAGR driver，blocked case 顯示 guidance overlay 或 qualitative watchlist。
- TODO `EXP-2.4a` 完成；core golden fixture 擴至 42 asserts，report renderer 擴至 17 asserts。

### Why
- V4.26.0 已先定義 scenario gate；本版補上 gate 後面的最小 builder。輸出仍只描述營運 driver，
  不產生前瞻單點 fair value、target price、verdict、threshold 或 sizing。

## [4.26.0] — 2026-06-16 — Scenario Policy Gates（shadow）

### Added
- `forward_expectations_scenario_policy.py`：定義 bear/base/bull scenario 的 evidence gates，
  判斷目前只能 qualitative-only、range/overlay-only，或可允許 driver numeric scenario。
- `test_forward_expectations_scenario_policy.py` 16 asserts，涵蓋缺 driver、完整 numeric
  transmission、guidance range overlay、bridge unavailable、no base metric 與 forbidden methods。

### Changed
- `forward_expectations.py` 新增 top-level `scenario_policy` shadow block。
- TODO `EXP-3.3` scaffold 完成：缺可靠 driver / conversion method 時不得產生精確 scenario。

### Why
- 在建立 bear/base/bull 前，必須先把防幻覺規則寫死。此版不產生 scenario 數字，只授權哪些
  scenario mode 可以被後續 builder 使用。

## [4.25.0] — 2026-06-16 — Forward Expectations Shadow Report Renderer

### Added
- `forward_expectations_report.py`：將 Forward Expectations snapshot render 成人可讀 Markdown
  advisory section，包含 expectations matrix、expectations gap、financial bridge risk 與 policy footer。
- `test_forward_expectations_report.py` 12 asserts，涵蓋 bridge-risk-only、same-metric gap table、
  bridge unavailable 與 shadow-only policy。

### Changed
- TODO `EXP-2.6` scaffold 完成：Forward Expectations 已可輸出 MD 區塊，供個股報告 §6 advisory
  呈現，但不覆蓋 live fair value 或 verdict。
- `investment_protocol_v5_0.md` Forward Expectations 描述更新到 v4.25 功能邊界。

### Why
- v4.24 已有 JSON gap，但使用者實際讀的是個股報告。此版把 forward layer 轉成人可讀敘事，
  同時保留 shadow-only 治理。

## [4.24.0] — 2026-06-16 — Expectations Gap Engine（shadow）

### Added
- `forward_expectations_gap.py`：建立 market-implied、analyst consensus、committee independent
  與 base-rate 的 expectations gap scaffold；numeric gap 僅允許同 metric 比較。
- `test_forward_expectations_gap.py` 23 asserts，涵蓋 revenue same-metric gaps、FCF/EPS 跨口徑不比較、
  independent unavailable 降級、bridge risk only、negative FCF 與 no-data fallback。

### Changed
- `forward_expectations.py` 新增 top-level `expectations_gap` shadow block。
- TODO `EXP-2.5` scaffold 完成：目前可並列 expectations pressure 與財務敘事風險，但不產生 fair value
  或 live verdict。

### Why
- v4.23 已能產出 forward financial bridge；本版把不同 lane 的差異整理成可稽核 gap，避免回到
  FCF CAGR、EPS CAGR、營收 CAGR 跨口徑相減。

## [4.23.0] — 2026-06-16 — Forward Financial Bridge（shadow）

### Added
- `forward_expectations_financial_bridge.py`：ticker-neutral 簡化財務 bridge，將 sourced forward
  revenue/EPS expectations 映射到 revenue → gross profit → operating income →
  tax/other → net income → FCF / EPS implied net income。
- `test_forward_expectations_financial_bridge.py` 25 asserts，涵蓋正常 bridge、derived margin
  優先、缺核心輸入降級、負 FCF 保留、share count fallback、無 forward rows 降級。

### Changed
- `forward_expectations.py` 新增 top-level `forward_financial_bridge` shadow block。
- TODO `EXP-2.3` scaffold 完成：目前只做財務敘事自洽檢查，不產生 fair value、不改 live decision。

### Why
- Forward Expectations 已有 consensus/guidance/revision/calibration，但仍缺一張可檢查的未來財務表。
  此版把未來收入與 EPS 預期轉成 P&L/FCF bridge，讓後續 expectations gap 與 scenario 能檢查營運假設是否自洽。

## [4.22.0] — 2026-06-16 — Forecast Calibration Scaffold（read-only）

### Added
- `forward_expectations_calibration.py`：唯讀掃描 Forward Expectations immutable snapshots 與
  earnings-analyst cache actual，建立 forecast-vs-actual rows。
- 初始比較：`consensus.revenue_cagr` vs latest actual `revenue_yoy`、
  `consensus.eps_cagr` vs latest actual `earnings_yoy`。
- `test_forward_expectations_calibration.py` 19 asserts，涵蓋 comparable rows、future level 不可比、
  actual missing 降級、WAPE proxy、directional accuracy、insufficient sample。

### Changed
- TODO `EXP-4.2` / `EXP-4.3` scaffold 完成：已有 calibration output shape 與樣本不足紀律。

### Why
- Forward Expectations 已開始保存 consensus、guidance、revision snapshots；下一步必須建立驗證閉環。
  此版只產生 calibration scaffold，不調權重、不改 live 決策，避免樣本不足時把噪音寫進規則。

## [4.21.0] — 2026-06-16 — Analyst Estimate Revision Snapshot

### Added
- `forward_expectations_revisions.py`：建立 point-in-time analyst estimate / rating snapshot，
  保存 annual revenue／EPS consensus curve、low/high dispersion、analyst count 與 rating momentum。
- `test_forward_expectations_revisions.py` 15 asserts，涵蓋日期排序、dispersion、rating momentum
  UP/FLAT、缺資料降級、單一 snapshot 不可假造 estimate revision delta。

### Changed
- `forward_expectations.py` 新增 top-level `estimate_revision_snapshot` shadow block。
- `forward_expectations_evidence.py` 將 snapshot 轉成 `consensus_revision:revenue`、
  `consensus_revision:eps`、`consensus_revision:rating_momentum` accepted evidence。
- TODO `EXP-1.4` 完成：目前保存 point-in-time 市場預期；真正上修/下修 delta 留待未來 ledger snapshots
  累積後比較。

### Why
- 只有最新 consensus 不足以描述市場預期。此版先保存「當時市場預期曲線與分歧」，並誠實標示目前 cache
  沒有同一 estimate 的歷史版本，因此不得從單一 snapshot 假造 analyst up/down revision。

## [4.20.0] — 2026-06-16 — Management Guidance Extraction（range-preserving）

### Added
- `forward_expectations_guidance.py`：ticker-neutral management guidance extractor，從 primary-source
  documents 抽 revenue／EPS／gross margin／operating margin／FCF／capex 的明確 guidance / outlook。
- Guidance range contract：range 保持 `{low, high, midpoint}`，midpoint 僅為 derived helper，
  不代表管理層原始單點值。
- `test_forward_expectations_guidance.py` 22 asserts，涵蓋 revenue range、EPS point guidance、
  margin percentage range、缺日期/來源 provisional、unsupported narrative 不 promoted、歷史結果不抽。

### Changed
- `forward_expectations_primary_sources.py` 同時輸出 driver candidates 與 guidance candidates；
  兩者分開保存，避免 guidance 被誤當 adapter driver。
- `forward_expectations_evidence.py` 將 promoted guidance 納入 accepted inventory，metric 以
  `guidance:<metric>` 呈現，metadata 保留 `value_type=guided` 與 `guidance_kind`。
- `forward_expectations.py` 新增 top-level `guidance_extraction` shadow block。

### Why
- Document acquisition 已能產生可抽取文字，但 engine 仍缺「公司自己怎麼看未來」的結構化入口。
  此版把明確 management guidance 作為 point-in-time evidence 保存，同時避免把區間硬壓成單點估值或
  混入 live fair value。

## [4.19.0] — 2026-06-16 — Bounded SEC Document Acquisition / Normalization

### Added
- `forward_expectations_document_acquisition.py`：opt-in bounded acquisition，僅從 source discovery
  manifest 內的 allowlisted SEC filing document URL 下載 HTML/TXT，轉成 normalized text bundle。
- URL safety policy：只允許 `sec.gov` / `www.sec.gov` / `data.sec.gov`，且 SEC filing document
  必須在 `/Archives/edgar/data/` 並以 `.htm` / `.html` / `.txt` 結尾；`data.sec.gov`
  submissions manifest 保持 metadata-only，不當作文件證據。
- 30-day document cache、最大下載大小上限、EDGAR User-Agent、HTML script/style 清理。
- `test_forward_expectations_document_acquisition.py` 19 asserts，涵蓋 allowlist、拒絕任意網站、
  HTML 正規化、cache hit 避免網路、normalized text 不自動 promotion。

### Changed
- `forward_expectations.py` 新增 `--acquire-documents` / `--max-documents`；預設仍不抓文件。
- Acquired normalized documents 可併入 primary-source bundle，但仍須通過既有 promotion gate 才能
  進 accepted evidence 或 adapter driver。

### Why
- v4.18 只知道「去哪裡找」，還沒有安全地把 filing 轉成可抽取文字。此版補上最窄的 SEC 文件取得層，
  讓後續 guidance / driver extraction 有原文輸入，同時避免把任意網站、SEC manifest 或全文存在本身誤當證據。

## [4.18.0] — 2026-06-16 — Ticker-Neutral Primary Source Discovery Manifest

### Added
- `forward_expectations_source_discovery.py`：跨 ticker source manifest，從 shared company
  profile cache、CIK、company website、24h filing metadata cache、FMP filing metadata 與
  earnings transcript location 發現候選來源。
- Filing family classifier：依實際 metadata 分類 `10-K/20-F/40-F` annual、`10-Q` interim、
  `6-K` foreign-issuer report、current/proxy/registration/unknown；不按 ticker、國家、產業或
  adapter 猜測。
- `test_forward_expectations_source_discovery.py`：涵蓋美國發行人、外國發行人、未知表格、
  缺 CIK、去重、transcript 與 cache 避免 provider quota。

### Changed
- Forward Expectations shadow snapshot 新增 `source_discovery`；所有 discovered metadata 進
  Evidence Inventory 時固定 provisional、`numeric_eligible=false`。
- Filing metadata 使用 24 小時 cache；只有 cache miss 且允許 fetch 時才查 FMP。
- Adapter registry 只有 `matched` 可成為 selected adapter；`partial` 僅保留研究候選，避免
  ORCL 這類含 License 字樣但不是 Royalty/IP 模型的公司收到錯誤 driver acquisition targets。

### Why
- Primary-source promotion gate 已能防止幻覺，但缺少通用的「去哪裡取證」入口。Discovery 必須適用
  所有 ticker，且不能因 ARM 是外國發行人就硬編規則，也不能把 URL／filing metadata 誤當營運證據。

## [4.17.0] — 2026-06-16 — Cache-First Primary Source Acquisition + Promotion Gate

### Added
- `forward_expectations_primary_sources.py`：只讀既有 earnings transcript 或
  `--primary-source-file` 明確提供的 filing／IR／transcript text bundle；不主動上網、不使用 LLM。
- Royalty/IP deterministic candidate extraction：只認 units、royalty rate/value per unit、
  license conversion、data-center exposure 的明確數字句。
- Primary evidence promotion gate：候選必須同時具備 value、unit、period、published date、
  supported primary source type 與 source URL/ref；缺任一項保持 provisional。
- `test_forward_expectations_primary_sources.py` 19 asserts；Evidence Inventory 擴至 20 asserts；
  Royalty/IP adapter 擴至 27 asserts。

### Changed
- Promoted primary-source records進入 Evidence Inventory accepted 區，並可填入直接觀察的 adapter
  driver 值與 evidence ref；仍不得自行建立 revenue CAGR 或 transmission conversion。

### Why
- ARM 目前缺 transcript／filing／IR 原文，不能靠新聞、報告或 Nexus 敘事補 driver。此版先建立嚴格的
  cache-first 取證與 promotion 流程，讓未來取得 primary bundle 後可安全接入，而不是讓 AI 自由抽數字。

## [4.16.0] — 2026-06-16 — Point-in-Time Evidence Inventory + ARM Acquisition Targets

### Added
- `forward_expectations_evidence.py`：建立每次 run 的 point-in-time Evidence Inventory，分類
  `accepted / provisional / missing_sources / missing_drivers`，並保存至 immutable forecast ledger。
- Evidence promotion gate：structured company segment／financial facts與 analyst consensus 可 accepted；
  Nexus `CO_THEME`、非 causal relation、未受 corroboration 或缺 conversion method 的關係只能 provisional。
- Royalty/IP adapter acquisition targets：明列缺失 driver、用途、preferred primary source 與 promotion requirement。
- `test_forward_expectations_evidence.py` 17 asserts；Royalty/IP adapter 測試擴至 25 asserts。

### Changed
- `forward_expectations.py` v1.3 在 adapter 初次匹配後建立 inventory，再以 inventory evidence references
  重跑 selected adapter；inventory 可補來源引用，但不可補缺失 driver 數值。

### Why
- Repo 內 ARM 已有公司 segment 與共識資料，但 Nexus 只有 `CO_THEME` 關聯，沒有可量化 AI 基建傳導證據。
  本版將「目前有什麼、缺什麼、應向哪類 primary source 取得」結構化，防止敘事或共題材被誤當因果輸入。

## [4.15.0] — 2026-06-16 — Royalty/IP Adapter + ARM Revenue Exposure / Transmission Gate

### Added
- `forward_expectations_adapters/` registry 與首個 `royalty_ip` adapter：以 product segment
  deterministic match Royalty／License 商業模式，輸出 Revenue Exposure Map、歷史 segment growth、
  driver tree、supported/unsupported valuation methods。
- Supply-chain transmission gate：外部趨勢須具備 target、lag、evidence refs、conversion method 與
  confidence 才能 `numeric_eligible`；否則固定為 `qualitative_only`。
- Numeric Independent lane gate：營運 driver 與最終 revenue CAGR 均須有 evidence refs，缺任一項即
  `insufficient_evidence`，禁止用 explicit input 注入無來源預測。
- `test_royalty_ip_adapter.py` 22 asserts；core Forward Expectations 測試擴至 33 asserts。

### Changed
- `forward_expectations.py` v1.2 接入 adapter registry，輸出 `adapter_evaluation` 與
  `independent_lane`；只有通過 gate 的 Independent Revenue CAGR 才能進同口徑 expectations matrix。

### Why
- ARM 的現有 cache 足以證明 Royalty／License 收入結構，但不足以證明 AI 基建成長如何量化轉成 ARM
  收入。此版先建立可驗證的曝險與傳導骨架，明確把缺 conversion evidence 的 AI 路徑留在定性層。

## [4.14.0] — 2026-06-15 — Forward Expectations Foundation：同口徑比較 + Evidence Contract + Adapter Contract

### Changed
- `forward_expectations.py` v1.1 將 `expectations_gap` 改為同口徑 `expectations_matrix`：
  Revenue／EPS／FCF CAGR 僅能各自比較；跨口徑只並列描述，不再互減或產生市場高估／低估 verdict。
- Forecast snapshot 改用 UTC microsecond `run_id` + exclusive-create，避免同一 earnings date 重跑時覆寫歷史預測。
- `forecast.py::forward_eps_bundle` 恢復 governed live median／mean 採用規則；consensus-dominant 值只記為
  `shadow_consensus_dominant_candidate`，不再未經批准移動 live `forecaster_blend`。

### Added
- Forward Expectations Evidence Contract：每個數值保存 value type、source lineage、published/retrieved time
  與 confidence；`unknown` 或來源不完整的數值拒絕進入模型。
- `investment/forward_expectations_adapter_contract.md`：跨產業 Adapter、segment composition、
  supply-chain transmission gate、匹配與缺資料降級規則。
- Golden fixture 擴至 30 asserts，涵蓋禁止跨口徑 verdict、evidence rejection 與 immutable ledger。

### Why
- FCF CAGR 與 EPS／營收 CAGR 互減會製造沒有經濟意義的精確 verdict；未建立來源契約與產業 Adapter
  前，系統也無法可靠擴充至 ARM 供應鏈傳導、銀行或零售。此版先修正地基，維持全 shadow 治理。

## [4.13.0] — 2026-06-15 — Forward Expectations Layer Phase 1（shadow）+ forecaster 稀釋 bug 修

### Added
- `investment/scripts/forward_expectations.py` — V1.0 deterministic 前瞻預期引擎（0 LLM）。
  三條 grounded lane：① **consensus**（讀 earnings-analyst `annual_estimates` → estimate-window
  營收/EPS CAGR + 分析師離散 + rating 修正方向）② **market_implied**（reuse
  `compute_price_framework.compute_implied_expectations` reverse DCF）③ **base_rate**（同業歷史
  營收 CAGR 分布，防過度樂觀）→ `expectations_gap` + deterministic gap_assessment。每跑寫
  point-in-time 快照至 `investment/invest_logs/forward_expectations/`（**只存、不建校準引擎**）。
- `investment/forward_expectations_schema.md` — schema + 建模決策（estimate-window CAGR、
  跨口徑比較標註、base-rate anti-fantasy、margin-expansion flag）。
- `investment/scripts/test_forward_expectations.py` — golden fixture（19 asserts，3 fixtures）。
- `investment/investment_protocol_v5_0.md` Phase 4.5 — Forward Expectations advisory shadow 區塊說明。

### Fixed
- `skills/earnings-valuation-forecaster/scripts/forecast.py::forward_eps_bundle` — 稀釋 bug：
  舊 `median(vals)` 讓 2 個 trailing 外推法（cagr/trend）表決掉唯一前瞻法（consensus）。成長股
  trailing EPS 偏低時，真前瞻共識被丟棄（ARM consensus ~2.18 → 被壓到 ~0.92）。改為 consensus
  與 trailing 顯著背離（>15%）時 **consensus 主導**（0.6 floor）；方法一致（成熟股）維持 median
  → 對 live `forecaster_blend`（5% 錨）影響僅限病態背離情形。附 `adoption_rule` reason。

### Why
- 成長股 `fair_value_summary` 後視錨（trailing DCF / owner-earnings×15）把公允價壓到不可信
  （ARM「$8 DCF / FV $51 / 現價 −86%」）。Phase 1 不重寫 live blend、不輸出前瞻單點公允價（那需
  driver tree，押 Phase 2），而是用**已存在的真前瞻資料**（分析師多年估計、reverse DCF、同業歷史）
  產出「市場要求 vs 共識 vs 歷史 base-rate」的誠實對比。ARM 實跑：市場隱含 60% FCF CAGR（out_of_range）
  vs 共識 EPS CAGR 40% vs 同業 base-rate 13% → 「市場要求顯著高於共識與歷史達成率」，取代不可信幅度，
  保留「ARM 很貴」的合理判斷。全 shadow，不碰決策數學。

## [4.12.3] — 2026-06-15 — 決策中心卡片：Layer-3 估值改常駐不 fold（patch）

### Changed
- `Dashboard/page-decisions.js` — Layer-3「證據 · 估值」block 由 `<details class="dc-collapse">`
  改為常駐 `<div>`（不再折疊）。fair value / vs current / confidence / anchor chips +
  `buildFvExtras` 的 fair_value_range（Range p25/p50/p75）現在卡片上直接可見。

### Why
- 估值 + fair_value_range 原本藏在折疊 details 裡，要點開才看得到。常駐後與其上方常駐的
  dual-track entry（AGG/CONS 建倉推薦）並排，建倉區間 vs 公允價值區間可在同一張卡直接比對，
  不用展開折疊來回對照。

## [4.12.2] — 2026-06-15 — sector Phase 4b Devil's Advocate prompt 瘦身：結構性 divergence 規則改條件觸發（patch）

### Changed
- `sector/phase_4-5.md` Phase 4b — DA（Devil's Advocate）prompt 是 sector protocol 單一最肥
  subagent input。舊版每次無條件把 4 條結構性 divergence 規則（R4 FRED 衝突 / R5 smart money /
  R6 PT target exhausted / R7 動能耗盡）全文塞進 prompt，但這 4 條是 threshold 觸發型，多數日子
  根本沒命中。
- 新增「DA Pre-Trigger 計算」段：PS 在組 DA prompt 前，用已在手 cache（`_phase0.fred_snapshot` /
  `_phase3.smart_money_signals` / `_phase3.sector_earnings_pulse` / `_phase1.sectors[].sector_valuation`）
  對每個 HOT 提案 sector 逐條 threshold 比對，**只把 fired 的規則塊 + 命中 sector/數值** paste 進
  `<TRIGGERED_DIVERGENCE_RULES>` placeholder；全沒觸發則填一行 n/a。R4–R7 全文移到 spec 內的
  Rule Library 區（僅參考，不再無條件入 prompt）。
- DA prompt 的 smart-money 資料段也改成「僅 R5 觸發時才 paste」，未觸發填 `n/a`。

### Why
- 砍 DA subagent 每次 run 的 input token：沒觸發的規則本來就不會產 challenge，全文塞進去純浪費。
  正確性不變（fired 規則仍逐條 MUST 引具體數值）。R1–R3（consensus_warning / tail-risk /
  falsifiable）維持每次必跑。

### Fixed
- `dashboard_server.py` `_wait_protocol_completion()`：baseline 由「list 長度」改為「timestamp」。
  `_protocol_history` 受 `_PROTOCOL_HISTORY_MAX=10` 上限封頂（insert(0)+del[MAX:]），長度滿 10 後恆定不變；
  舊的 count-based 偵測 `history[: len-baseline]` 在滿載後永遠切成空集合 → 任何完成都偵測不到 →
  premarket chain 的 news/sector wait **必定**跑滿 1500s/1800s timeout，即使 protocol 早已完成。
  （2026-06-15：news 20:11 已寫 digest，但 chain 仍卡 `queued/elapsed=1500`，timeout 一觸發 sector 才於 20:26 啟動。）
  改成比對 `ended_at >= baseline_ts`（秒級對齊），完成立即偵測到。
- `dashboard_server.py` `_run_news()`：`_wait_protocol_completion` 改包進 try/except。
  `_run_news` 跑在獨立 thread，timeout 的 `RuntimeError` 原本會無聲逃逸 → `phase1_errors` 仍為空 →
  `t_news.join()` 乾淨返回 → chain 誤判 Phase 1 通過 → 假性推進到 Phase 2 sector。
  現在 timeout → 記 `news` item error + append `phase1_errors` → chain 正確中止。
- `dashboard_server.py` `_run_sector()`：sector wait timeout 時補設 sector item `status=error`
  （外層 try 本就會把 chain 設 error，但 item 會凍在 `queued`），UI 狀態一致。
- `bridge.py` `_extract_committee()`：容忍 `_phase4a` 兩種 shape。文件規格是 dict
  `{fanout_mode, proposals:[...]}`，但部分 PARALLEL_SUBAGENT run 直接把 proposals array 當 bare list
  輸出。舊 code 無條件 `p4a.get(...)` → `'list' object has no attribute 'get'` → sector ingest 整個
  try-block 中止 → `data.json.sectors` 變空 → 產業掃描報告**跑完且 validator rc=0，卻沒進網頁**。
  validator 不 gate `_phase4a` 內部 shape，故 bridge 須兩種都吃。2026-06-15 sector run 即中此。

### Why
Premarket chain（daily ∥ news → sector）的完成閘在 server 累積 ≥10 次 protocol 完成後整個失效：
news 實際跑完卻偵測不到、硬等到 timeout，且該 timeout 又被吞掉讓 chain 假性過關。
Root cause 是封頂 list 配 count-based baseline 的索引邏輯崩壞，非 enqueue duplicate。

## [4.12.0] — 2026-06-13 — Weekly REVIEW 改善：news-digest 方向法 shadow + Pattern C 自動化 + Rec 11 shadow-replay（minor）

### Added
- `scripts/verdict_rules.py`：`verdict_news_digest_directional()` + `NEWS_NOISE_FLOOR_PCT=0.3`
  — H-D（REVIEW_2026-06-13）news-digest 改 `sign(macro_delta)==sign(SPY)` 方向法（保留 0.3% 雜訊地板），
  解掉 ±1.0% magnitude gate 把強訊號壓 neutral 的結構 bug。**SHADOW only**，不進 VERDICT_DISPATCH、
  不改月曆 live label，供 REVIEW re-baseline 後再決定汰換 magnitude 法。
- `scripts/build_event_index.py`：news-digest verdict 掛 `shadow_directional` 欄；新增
  `_build_decisive_agent_split()` → payload `decisive_agent_split`（Pattern C / H-C 自動化：
  deep-dive miss 按 decisive_agent × action_class 拆，每週 REVIEW 直接讀，不再 ad-hoc 算）。
  event_index `version` 1.1 → 1.2。
- `investment/scripts/replay_rec11.py`（new，唯讀）：Rec 11 hot_zone_probe shadow-replay。
  strict-gate（live RISK_ON/BULL）+ ex-regime（放寬 what-if）雙 pass × 歷史 HOLD-miss，
  估合成 15bps NAV capture。TODO-012 合成驗收：Rec 11 規則 live dormant（6 月防禦）但歷史
  strict 會 fire 12/19 Semis（capture +0.62% NAV，avg dd −3.1%）→ 規則設計健全，dormancy 為 regime timing。

### Findings（不改決策，僅量測揭露）
- **H-C 收斂**：`decisive_agent_split` 證實 News-decisive 高 miss 是 action_class 驅動非 agent 驅動 —
  News conservative miss 68.8% vs active 26.7%；Fundamentals/Technical conservative 同樣 ~57% →
  miss 根因是保守性（Pattern A 同根），非 News-edge 衰減。
- **H-D 反轉**：shadow 顯示 9 筆強訊號 directional 為 hit 1 / miss 8 → magnitude gate 過去是**藏掉真 miss**
  非藏掉 hit，macro_delta 訊號方向校準本身偏弱。汰換 magnitude 前需重評 delta 來源。
- **Rec 11 gate 維持 RISK_ON/BULL**：ex-regime 放寬僅多 +0.35% 邊際 capture，承擔買進回檔風險不划算。

### Why
- 本週 weekly LLM REVIEW（REVIEW_2026-06-13）11 個 TODO 7 個卡資料門檻空轉。用 shadow 量測 +
  合成 replay 技法在不動決策層的前提下，把「等 live regime / 等 N≥15」的驗收提前解鎖。

## [4.11.0] — 2026-06-13 — Dashboard 協定 per-protocol model tiering（minor）

### Added
- `dashboard_server.py`：`PROTOCOL_MODEL` map + `_protocol_model_for()` —
  claude -p 協定路徑現在依協定性質選 Claude 模型 tier，不再全部吃 CLI 全域預設。
  - **opus**（深推理）：`invest`（分析，5-lane 辯論+估值+Red Team）、
    `llm_review`（300KB index 統計 pattern+root-cause）、`sector`（Phase 5 cross-sector synthesis）。
  - **sonnet**（省 token，無品質損失）：`news`/`flash`/`flash_text`/`review`/
    `link_digest`/`triage`/`earnings` — script-first 或結構化抽取，LLM 只補空缺。
  - 未列協定 fallback `PROTOCOL_MODEL_DEFAULT = "sonnet"`。
- `_protocol_command()` 加 `claude_model` 參數 → 注入 `claude --model`（接受 alias `opus`/`sonnet` 或 full id）。
- 單協定執行期覆寫：env `PROTOCOL_MODEL_<NAME>`（如 `PROTOCOL_MODEL_SECTOR=sonnet`；空字串 → 省略 `--model` 回退 CLI 預設）。

### Why
- 個股分析 / 決策 review 需深度判斷，產業掃描多走 script 但 Phase 5 要綜合 → 值得 opus。
- news/triage/earnings 已是 deterministic script-first，LLM 工作是結構化抽取，opus 是浪費 → sonnet 省 token。
- 不同協定不必同一模型；之前全吃 CLI 全域預設（手動 `/model` 切換、易忘）。
- Break News debater / supply_chain / office 走 model_router（primary=gemini），與此路徑獨立，不受影響。

## [4.10.0] — 2026-06-13 — 決策中心 RWD + 三層卡片 + V3.45+ 估值欄位接通（minor）

### Added
- **bridge.py 接通 8 個 V3.45+/V5.0.x 欄位**（extraction ~1536 + audits dict ~1640）：
  `multi_horizon_price_framework` / `fair_value_range` / `implied_expectations` /
  `valuation_archetype_shadow`（Phase 2.4 advisory blocks — 前端 `buildFvExtras()`
  V3.49.0 早已寫好但 data.json 從沒這些 key，永遠隱藏；本版補上斷鏈，下次跑
  `分析` 即自動顯示）+ `decision_cap_active` / `decision_cap_reason` /
  `cap_override_reason` / `hot_zone_probe`（Phase 4.6 — history.json 已有 11 筆
  cap 資料：MRVL/PANW/CRWD 立即可見）。
- **CAP / PROBE pills**（`page-decisions.js buildDecisionStrip`）：⛔ 估值上限 pill
  （紅，reason 映射 錨點不足/估值信心低/資料品質低，rich tooltip 說明 no-BUY /
  conf ≤0.65 / ≤30bps 語意）+ CAP OVERRIDE pill（amber，title 帶 PM 覆寫原文）+
  🧪 熱區試倉 pill（藍，STAGED_ENTRY ≤15bps）。DECISION_TIPS 加 `decision_cap` /
  `hot_zone_probe` 雙語 entry。
- **i18n** `watchlist` 加 `layer2_title` / `layer3_title` / `badge_cap` /
  `badge_cap_override` / `badge_probe`（zh + en）。

### Changed
- **決策卡改三層「結論 → 理由 → 證據」**（同 4.2.0 產業掃描頁哲學）：
  - **Layer 1 結論（常駐）**：新 `buildDecisionStrip()` — action_label 升主視覺
    （V2.20.0 WAIT+staged→部分建倉邏輯原樣搬移）+ decision_confidence_pct +
    CAP/PROBE/binary pills + `institutional_lens` 一句話理由（2 行 clamp、hover 全文，
    `.dc-lens-clamp` CSS）。score/meta、TP/SL、雙軌進場、持倉 overlay 留 Layer 1。
  - **Layer 2 理由（單一 collapse，summary 帶 Red Team verdict chip + 訊號數）**：
    其餘 pills（consensus/contrarian/fragility/polarization/moat/pattern/strength/
    fanout/degraded/burry）+ Red Team block（外層 details 拍平）+ 觸發條件 + key risks。
  - **Layer 3 證據（單一 collapse，summary 帶公允價值 band chip）**：估值 block
    （6-anchor + buildFvExtras advisory rows）。
  - `buildV48StatusPills` 改回傳 array（Layer 2 需要計數）；`buildV5ValuationBlock` /
    `buildRedTeamBlock` 改回傳 `{html, chip}` 讓 chip 上提到 summary。
- **RWD**：
  - 主 grid `lg:grid-cols-2` → 加 `2xl:grid-cols-3 min-[2200px]:grid-cols-4`，
    4K 滿版 4 欄不再兩張巨卡。
  - **歷史 drill overlay 從固定 420px 橫向 rail 改 wrap grid**
    （`grid-cols-[repeat(auto-fill,minmax(380px,1fr))]` + `overflow-y-auto`）—
    4K 橫向卷軸主因移除。
  - `<main>` 加 `min-w-0`（flex child overflow 防護）。
  - style.css 全站共用：`@media (max-width:860px)` sidebar 隱藏 + main `margin-left:0`
    （15 頁同 markup 一條規則全蓋）。

### Why
- User 4K 螢幕看決策中心要往右捲、卡片固定寬不跟視窗走；卡片 10+ pills 平鋪掃一眼
  看不出結論；invest protocol V3.45-V3.49 新增的估值產出（range/MHP/reverse DCF/
  archetype/decision cap）算了但 bridge 沒搬，「跑很貴、呈現缺一哩」。本版三件一次補齊。

## [4.9.0] — 2026-06-12 — 市場氛圍頁重設計：決策漏斗 + 川普政策雷達（minor）

### Changed
- **`Dashboard/mood.html` + `Dashboard/page-mood.js` 全面重寫**：從「儀表 + 散戶 strip + 11 張產業卡」改為上→下決策漏斗，回答「今天該不該進場？」。半圓 mood gauge 移除（Chart.js 依賴一併移除），Put/Call · VIX/SKEW · F&G 三 tile 降級為頁尾 compact strip。
  1. **判定帶**：確定性公式（0 LLM）算 偏多/偏空/觀望 — 開盤權重 盤面.35/新聞.25/辯論.20/情緒.20，收盤 新聞.35/辯論.30/情緒.35，±0.15 中性帶，缺項自動重新正規化，公式分項 chip 透明顯示；盤面 vs 消息面反向差 >0.5 → 分歧警示。旁掛 break-news Market Brief 繁中導讀 + drivers/bull/bear/watch 四欄（已付費 artifact，純讀取）。
  2. **近 3 天走向**：重用 `trend-chart.js`（72h 情緒指數）+ brief history regime 時間軸 pills + 每日錨點 chips（Breadth/FTD/Top Risk/FRED/SPY RSI·MA50）。
  3. **盤中即時**：client-side 聚合 heatmap.json（市值加權 % / 漲跌家數 / 最強最弱產業 / 成交熱門），開盤 3 分鐘輪詢、收盤收合成上一交易日一行摘要。
  4. **社群雷達**：ticker chips + buzz pills 保留，新增 Reddit/HN/Bluesky 貼文 feed（直讀 `trending_tickers.json` 全量版，含 source badge + engagement 排序 + polarity 色點，上限 14 列）。
  5. **川普政策雷達**（新）：`raw-stream` 過濾 Truth Social 帖文（48h），政策關鍵詞高亮 + 轉彎訊號 lexicon（pause/exempt/deal…）→ ⚠️ TACO flag；帖文若已被 break-news 辯論 → 直接掛 verdict + final_take。
  6. **突發辯論訊號**：10 列 closed debates（verdict badge + ×echo + credibility 點，點擊展開 final_take）+ 熱事件 cluster strip。
  7. **產業情緒**：11 張 3-lane 卡 → 單列排行（composite badge + polarity bar + 盤中 % + 新聞箭頭），點擊跳 sector.html。
- **`dashboard_server.py`**：`GET /api/break-news/brief` 新增 `?history=1` 回傳 history[]（預設回應不變，break-news.html 不受影響）。
- **`scripts/break_news/store.py`**：feed projection 新增截斷版 `final_take`（≤400 chars）。
- **`Dashboard/i18n.js`**：mood 區 zh/en 各 +~40 keys。

### Why
user 反映市場氛圍頁無法回答核心問題「目前市場走向、當下要不要投資」，產業情緒 grid 數字過密難讀；要求以散戶視角 + 最近三天趨勢為主、開盤含即時盤勢、多社群參考、且不增加 token 成本。重設計全部重用既有 artifact：market brief（2h 已付費導讀）、closed debates verdicts、72h trend rollup、heatmap 報價、trending_tickers 社群貼文 — 本頁 **0 新增 LLM call**，只 GET。Truth Social 依 user 指示獨立成政策雷達（只評估川普政策轉彎對盤勢影響），不混一般社群 feed。探索層紀律不變：不回饋 investment_protocol。

## [4.8.0] — 2026-06-12 — Break News V6：event clustering + 嚴格 divergence gate + Market Brief（minor）

### Added
- **`scripts/break_news/cluster.py`**：純 Python 事件聚類（0 LLM）。zh-aware token（en 輕量 stemming + 中文 bigram）Jaccard/containment ≥0.55 + 同 `news_type` 限定 + ticker overlap 加權 → 同事件多源重複報導合併為 echo（`echo_count+1`，不再各開辯論）。滾動 48h `_clusters.json`。Echo milestone (4/8/16/32) 且距上次辯論 ≥3h → **escalation**：開一場「增量追辯」，opener prompt 附前次結論（`prompts._escalation_block`），只辯新增資訊。
- **`scripts/break_news/market_brief.py`**：市場現況導讀。每 2h（`BREAK_NEWS_BRIEF_INTERVAL_SEC`）deterministic 聚合 24h clusters（heat = echo_count × |score|）+ closed debate verdicts + verdict tally → **1 次 LLM call** 產 200-300 字繁中導讀（regime / drivers / bull-bear pressure / watch），寫 `_market_brief.json`（含 12 筆歷史）。CLI：`--once / --force / --context`。
- **API**：`GET /api/break-news/brief`、`POST /api/break-news/brief/refresh`（背景產生）、`GET /api/break-news/clusters?hours=&min_echo=`。
- **UI**：break-news.html 頂部 Market Brief 面板（regime pill + 導讀 + drivers/bull/bear/watch 四欄 + 重產 button）；新聞卡 `×N` echo badge + `⤴ 升級追辯` badge。

### Changed
- **`debater.py` V5 → V6**：max_rounds 3 → 2（全部項目，含 high-priority）。divergence gate 收緊 — 只有「真衝突」（verdict BULLISH vs BEARISH 對立、或同 subject|object 關係極性相反）才開 rebuttal；confidence gap 從獨立觸發降為 high-priority 限定且門檻 0.4 → 0.65。新增 `single_voice` 收斂：單邊 CLI 掛掉時直接以健康方結論收 `partial_closed`，不再對 salvage record 燒 rebuttal。
- **`poller.py`**：接 cluster — echo（已有辯論的 cluster）gate 出局（`cluster_echo`）；sentiment 類非 binary / 非 HIGH cred / |score|<3 一律只聚類計數不辯論（`sentiment_cluster_only`，歷史佔總量 56%）；escalation 以 `advance_reason=cluster_escalation` 入場。`EST_CALLS_PER_DEBATE` 3 → 2。state 新欄位：`items_echo_merged` / `items_sentiment_clustered` / `items_escalated`。dry-run 維持零寫檔（cluster assign 跳過）。
- **`store.py`**：item 新增 optional `cluster` block（cluster_id / echo_count / escalated / prior_summary）；feed 摘要帶 `cluster_id` / `echo_count` / `escalated`。
- **`validate.py`**：新增 `_clusters.json` / `_market_brief.json` 輕量 lint。

### Why
2026-06-01~11 實測：650 件辯論、2,873 LLM call（4.4 call/件、~261 call/天），**69% 跑滿 3 輪**（V5 預期多數 round 1 收斂、實際僅 17%）— conf-gap 觸發太鬆；56% 是 sentiment 情緒標題且多為同事件跨源重複。V6 三刀：重複事件聚類去重、低值情緒類不辯、gate 只認真衝突 — 估 ~261 → ~60-75 call/天（▼70%+）。省下的預算改買一個真正可用的輸出：Market Brief 讓 user 不用逐卡讀辯論，先看導讀評估市場現況。

## [4.7.0] — 2026-06-12 — News Protocol V2.2：script-first triage 省 token（minor）

### Changed
- **`news/news_protocol_v2.md` V2.1 → V2.2**（563 → 361 行）：Stage 1 改由 `news/scripts/stage1_triage.py` deterministic 執行（block / template-dedup / credibility downgrade / news_type / score / 4-view snap / 晉級 gate 該 script v3.14.3 早已具備，protocol 一直沒接上）— LLM **禁讀 raw.json 全文**（當日 287KB ≈ 70K tokens），只讀 script stdout + triage.json `stage2_items` + `shallow_verdicts` top-25，補 top-15 `headline_zh`。Stage 2 bundle 每篇全文截 5000 chars（4 subagent 各收一份，重複成本 ×4）。MD 報告 Shallow Digest 20 → 10、snaps 照抄 triage.json 不重寫。Phase 4.5 structural watchlist 全節移至 `news/README.md`（純 script、daily 自動，LLM 從不執行）。
- **`dashboard_server.py` PROTOCOL_PROMPTS**：`news` prompt 改 script-first 流程（stage1_count = triage shallow_verdicts 長度、published 從 triage.json 抄）；`triage` prompt 改為「fetch → stage1_triage.py → LLM 只補 top-15 headline_zh 單次 Edit 寫回」— 順帶修正舊 prompt 要求的 `verdicts` shape 與 validator 期望的 `shallow_verdicts` shape 衝突。
- **`news/README.md`**：團隊表 / 流程圖 / token 預算表（DIGEST ~110K → ~35-40K、TRIAGE ~75K → ~5K）更新至 V2.2；刪除 stale「分塊 Write + digest_append_deep.py」段（與 protocol 現行單次 Write 規則矛盾）；新增 §Structural Watchlist（自 protocol 遷入）。
- **`news/digest_output_schema.md`**：shape 不變（schema 版本維持 V2.1，validator 不動）；註記 shallow snaps 來源為 script template、`stage1_count` 嚴格語義、DIGEST shallow top-10 cap 與 validator 上下限對齊。

### Why
DIGEST 單跑實際燒 ~110K+ tokens，其中 ~70K 是 LLM 把整包 raw.json 讀進 context 手工 triage — 而同等功能的 deterministic script（連 validator 的 triage cross-check）早已存在，protocol 文件卻仍指示 LLM 手跑。V2.2 把「可決定論的」全部下放 script，token 集中花在唯一不可替代的 Stage 2 四方深度辯論與 Arbiter 裁決上，分析品質核心不變。

## [4.6.2] — 2026-06-12 — 取消 LLM Fallback 機制（patch）

### Changed
- **取消 LLM Fallback 機制**：重構 `scripts/_shared/model_router.py` 中的 `_run_chain`，使其在指定或預選的模型失敗時不再 fallback 到其他備援模型。對齊修改 `scripts/break_news/llm_drivers.py` 中的預設 fallback 至 `gemini`，並在 `scripts/break_news/poller.py` 的 `_voice_order` 中同步取消 fallback 鏈的評估，以避免 poller 容載計算時混入其他備援額度。
- **預設主要模型變更**：更新 `config/llm_config.json` 與 `llm_drivers.py` 的 `_DEFAULT_CONFIG`，將 `primary` 改為 `gemini`（配合 sidebar 切換），`secondary` 為 `codex`，`tertiary` 為 `claude`。

### Why
使用者要求取消 fallback 機制，避免主要決策模型額度不足或失敗時，在背後默默回退到其他不符預期的模型（如 claude）。調整後，模型呼叫若不可用將直接顯式報錯。

## [4.6.1] — 2026-06-11 — ops glob 大小寫 + postmortem 資料修復（patch）

### Fixed
- **ops 檢查機制誤報 never_run**：registry glob `*postmortem*` 抓不到 `POSTMORTEM_*.md` — Python glob 在 macOS **大小寫敏感**（檔案系統不分但 fnmatch posix 分）。修 registry glob + `ops_scripts_status` 加 `_glob_ci()` case-insensitive fallback（滅整類）；sector_digest 標 stdout-only（glob 永遠空）
- **backtest_postmortem 三處壞數據**：(1) yfinance 尾端 NaN Close（同 V4.5 screen/predict 那隻）毒掉 ret_so_far → BUY/HOLD mean `+nan%`、4 lane pearson 全 `+nan` → compute_outcome 入口 dropna + 聚合/pearson 雙重 NaN 濾網；(2) parser 沒跟上 V4.x 報告加粗格式（`| **Final Score** | **1.5637 / 3.0** |`、`**3 / 5**`、`**Burry (Contrarian)**` 欄序）→ 5 月起 score/RT/burry 全 `—`，4 個 regex 補 `\*{0,2}` + 欄序變體；(3) RSI 加 prose fallback（`RSI 59.5`，需小數位防抓 `RSI 14`，排除 `SPY RSI`）。修後 N：score 49→94、RT 49→71、RSI 分桶 38→78

### Why
user 跑完回測但 Dashboard 仍標「從未執行」（glob 病）；報告半盲（NaN + 格式漂移）讓 §1/§8 結論不可讀。修後才能做有效 postmortem 分析。

## [4.6.0] — 2026-06-11 — 工作流導向 Dashboard：Today 工作台 + 產出閉環 + 節奏自動化（minor）

> 依 user 確認的三痛點（產出埋檔案系統 / 手動節奏記不住 / index 要一頁全貌）分三 phase 實作。
> 架構決定：聚合放 server 新端點 `/api/today`（即時 ms 級計算），不擴 bridge.py、data.json 不再膨脹。

### Added
- **Phase 1 — Today 工作台**：`/api/today`（due_actions = ops registry 到期 + sector/news protocol staleness；latest_outputs = 最新 10 份報告 + deterministic 關鍵行萃取 `_extract_report_summary`（ic_memo verdict / weekly hit-rate / premarket regime…，0 LLM，失敗回空）；morning_brief = 最新 PREMARKET md regime bullets + 領漲跌前 5 + 過期 flag）。前端新檔 `Dashboard/today-panel.js`（~250 行）三卡渲染進 index.html `#today-workbench`；index 加 盤前/盤中/盤後 分段標籤（**不動任何既有 DOM id**）
- **Phase 2 — 產出閉環**：reports 分類器 +5 type（shadow / premarket / postmortem / llm_review / ledger），`_list_reports_cached` 加掃 `reports/decision_review/`（只收 REVIEW_<date> + ADJUSTMENT_LEDGER，rel-path 入 filename）；`/api/reports/view/` 顯式 decision_review 白名單分支（regex 不鬆、`--path-as-is` 穿越測試 400）；reports 頁 TYPE_ORDER + 列表摘要行；新 `GET /api/adjustment-ledger`（md → 結構化 entries，mtime cache）+ decisions 頁唯讀 Ledger panel（只列 active，完整檔 deep-link reports 頁）
- **Phase 3 — 節奏自動化**：SCRIPT_PROTOCOLS +3（weekly_review 600s / shadow_report 300s / backtest_postmortem 900s，走既有 protocol queue FIFO + 無 ticker dedup 補強）；ops registry schema 加 `protocol_id` / `endpoint` / `auto` + 新 llm_review entry（launchd 週日 06:00 已自動，entry 供監控/手動補跑）；新 `ops_auto_loop` daemon（每 30 min，auto:true && due → enqueue；6h 防抖；LLM protocol 需 `OPS_AUTO_LLM=1` 雙重開關，預設永不自動花 LLM 錢）；ops 頁 ▶ 一鍵執行 + 🤖 自動 chip；Today 工作台 due 項同樣帶 ▶

### Why
盤點：16 頁前端運作正常但 weekly/shadow/REVIEW/ledger 等 6 類產出只活在檔案系統、手動 cadence 靠人記。工作流導向（user 選定）：早上開 index 一頁看完「該做什麼 + 系統產出了什麼 + 市場開盤前長怎樣」，到期的事自動跑或一鍵跑。頁面瘦身合併明確不做（探索期，三個新聞面節奏不同）。

### 驗證
curl smoke（/api/today、/api/reports counts +5 type、/api/adjustment-ledger 7 active、traversal 400）；headless 截圖 index 三卡 / reports 新 chips / decisions Ledger panel / ops ▶+🤖；auto loop 實測 touch 舊 mtime → 30s 內 enqueue → 跑完 badge 轉 fresh → **weights.yaml mtime 未變**；dedup duplicate_pending 擋連點。**user 的常駐 dashboard_server 需重啟**才吃到新端點。

## [4.5.1] — 2026-06-11 — 刪 earnings-trade-analyzer（patch）

### Changed
- **刪除 `skills/earnings-trade-analyzer/`**（user 拍板）：0 接線、最後活動 2026-04-27。連帶清 README / earnings-analyst SKILL.md / MARKET_INDEX 引用。check_skills 22 skills 0 warn
- `scripts/build_event_index.py` extractor **保留**：歷史 artifact `reports/earnings_trade_analyzer_2026-04-26_*.json` 仍進 decision-review event index（加註記）

### Why
稽核 §一 殭屍清單最後一項。5 因子評分若日後要用，git history 可復原（`git log -- skills/earnings-trade-analyzer`）。

## [4.5.0] — 2026-06-11 — Kill-Trigger Monitor + 稽核餘留批（minor）

### Added
- **Kill-Trigger Monitor（★★★ 新功能，委員會閉環）**：`scripts/kill_trigger_monitor.py` 每日 0-LLM 重檢所有 Red Team 推翻條件（investment `red_team_kill_conditions` 近 90d + sector `_phase4b.risk_scenario` 最新一份）。可解析謂詞（價格 / MA（支援 `200MA` 與 `MA200` 兩寫法）/ 量比 / VIX / SPY RSI / breadth / FRED DFII10 real rate）即時求值；`未能…WITHIN` 否定期限語義到期日才判定（防假紅 banner）；解析不了的標 `manual` + 到期倒數照樣上畫面。狀態：`triggered`/`armed`/`manual`/`expired`。輸出 `Dashboard/kill_triggers.json`；`daily_update.sh` 新 Step 9.9（非致命）；index.html 新 banner（紅=已觸發、琥珀=3 天內到期需人工複核，附 met-check chip）。實測 189 條件：3 armed / 60 manual / 126 expired
- `weekly_review.py` 新「per-weights-version comparison」報告段（>1 版本時出表）— weight bump 前後 hit rate 對比流程復活

### Changed
- **technical_core 升 `skills/_shared/`**（單一源）：`fetch_history` + `rsi_14` 等全搬；momentum-monitor 舊路徑留 shim（momentum.py / technical-analyst analyze.py 零改動）
- **RSI 5 實作 → 1**：etf_scanner（手寫 Wilder loop）、sentiment.py（rolling mean）、thematic screen.py（inline 15-bar mean）、predict.py（15-bar mean，影響 momentum_score 數值分布）全改 import `_shared.technical_core.rsi_14`（Wilder EMA）— 同 ticker 跨頁面 RSI 數字一致
- **thematic screener predict 改 in-process**：predict.py 抽出 `predict_ticker()` API，screen.py 直接 import（省 ~1-2s 直譯器+import × 100+ ticker/日）；subprocess 留 fallback
- **earnings-analyst fetch.py 並行**：20 個 FMP call ThreadPool×8（原 21 個純串行）；main 預抓 income limit 8 傳入 `fetch_bundle(income=)` 去除重複抓
- `weekly_review.py`：weights_version 讀對層級（`top_movers[].short_term`，原讀 theme 層永遠 unknown）+ 每 ticker 一次 yfinance 史料 memoize（原每 (date×ticker×horizon) 一次，476 列 → 138 fetch）
- `skills/MARKET_INDEX.md` 全量重寫：23 skills 全列（原 16）+ 接線狀態 + `_shared` 模組表；修 earnings-valuation-forecaster「未整合」等過時敘述

### Fixed
- thematic screen.py / predict.py：yfinance 偶發尾端 NaN Close row（2026-06-10 實測 SPY）→ dropna 防 NaN 寫進 recommendations JSON
- retail-sector-pulse SKILL.md：清掉已退役 narrative-pulse-detector 引用（check_skills WARN → 0）；aggregate.py docstring 註記 retail volume 元件 graceful 退化現況

### Why
稽核（`reports/SKILLS_AUDIT_2026-06-11.md`）§四之二餘留批 + §三 ★★★ 缺口。Red Team 條件自 V4.2 上畫面後一直沒人每天檢查 — 監控層補上後「決策→挑戰→驗證」閉環完成。RSI/price-history 統一消除同 ticker 跨頁數字不一致的根因。

### 註
- FMP `/stable/rating-historical` 與 `/stable/grades-summary` 已 404（pre-existing，HPE/AVGO 舊 cache 同樣全零）— 與 econ-calendar 同屬 legacy 退役系列，待處置
- earnings-trade-analyzer 處置（接 earnings 頁或刪）仍待 user 決定；econ-calendar 修復未排

## [4.4.0] — 2026-06-11 — Skills 稽核修復：7 真 bug + 靜默失敗 + 殭屍 + 效能（minor）

> 依 `reports/SKILLS_AUDIT_2026-06-11.md`（24 skills 全量稽核）執行批次修復。

### Fixed（🔴 真 bug）
- **ic-memo-writer**：`compose.py` render_sec_6 對 list 型 `quality_flags` 呼叫 `.items()`
  → 任何有品質 flag 的 ticker 必 crash（MSFT 實證修復，validator rc=2 degraded-usable）。
  `build_fact_pack.py` 移除 trades[0] fallback（找不到對應 trade 時會把**別家公司的決策**
  hash 進 decision_lock）；新增 `_as_dict/_as_list` 對 9 個 LLM-written 欄位做 shape 防護
  （moat string-drift 同類病）；render_sec_10/11 對 scenario_odds（`45%%` 雙百分號）與
  watch_conditions（list/str drift）加顯示層 guard（資料 verbatim 不動，lock 不受影響）。
- **investment_protocol_v5_0**：Burry lane JSON 契約改為腳本實際輸出鍵
  （`components{fcf_yield_pct,...}` + `component_scores{...}`，舊 `*_pts` 不存在）；
  T4 仲裁門檻從舊 0-12 刻度改 0-100（<10 CANCEL / 10-19 DOWNGRADE；舊文讓 CANCEL
  分支實質不可達）；補 `UNKNOWN` verdict 處理。
- **short-term-target**：`predict.py` news_age_hr 不再寫死 0.5 — v2 真實文章 age 傳through，
  news>8h/24h 新鮮度閘恢復可觸發（proxy fallback 維持 0.5h）。
- **retail-sector-pulse**：`trending_tickers.py` 宏觀話題比對改 headline+內文
  （原用 headline+**feed 名**：誤匹配 + 內文提及全漏）；process_post 帶 `summary` through。
- **earnings-analyst**：`render.py` §9 補 V3.17 新 flag 描述
  （accruals_warning_negative / cash_conversion_wc_driven / …_positive_gap_clean）。
- **us-stock-analysis / technical-analyst SKILL.md**：補「Investment-Protocol Lane Mode」
  契約段 — 前者原文教 lane 用 web search 抓 scalar（違反 protocol DATA SOURCE DISCIPLINE），
  後者整份只寫 chart-image 工作流、隻字未提 lane 實跑的 analyze.py 與必輸出欄位。

### Fixed（靜默失敗）
- **fred-macro**：all-series-failed stale fallback 改 rc=2 且不重寫 cache mtime
  （原 rc=0 → daily_update Step 4 永遠 ✅、stale 偽裝成 fresh）。
- **market-sentiment-analyzer**：`mood.py` total-failure `_partial` 骨架改 return 2。
- **daily_update.sh**：Step 1 breadth 改 non-fatal（bridge 本有 stale fallback，
  TraderMonty 掛掉不再中止整個 daily run）；Step 5.5 theme-detector 季度重跑補 rc 檢查
  （原 `>/dev/null 2>&1` 無檢查，失敗會讓舊 universe silent 沿用一季）。
- **earnings-valuation-forecaster**：`_load_real_rate` bare except 改 stderr WARN
  （fred cache 壞掉默默用 4.5% 會讓全部目標價偏低 ~18%）；順手修 0.0-falsy `or` 鏈。

### Removed
- **skills/supply-chain-event-analyst/** 整包刪除 — 0 接線，供應鏈頁實際走
  `scripts/nexus/supply_chain.py`，cache 僅一個誤跑 artifact。README /
  ARCHITECTURE_DIAGRAM / MARKET_INDEX 引用同步清除。

### Performance
- **momentum-monitor**：529 ticker × Yahoo `.info`（short interest 雙週才更新）
  → 24h sidecar cache（`cache/yf_info/`），日常 screen 省 529 次 quoteSummary。
- **short-term-target**：benchmark ETF 歷史改 in-process memo + 1h file cache
  （原每 ticker × 每 horizon 抓一次 SPY = 批次跑數百次）。
- **retail-sector-pulse**：`aggregate.py` 55 個 predict 子行程串行 → ThreadPool ×8；
  predict 失敗首例記 stderr（原全吞，壞掉只會默默全 sector neutral）。
- **finnhub-client**：`dual_fetch.py` 整市場 120 天 earnings calendar 每 ticker 抓
  → per-run memoize；calendar 失敗不再 poison 整筆 diff status。
- **Cache prune**：thematic enrich cache >7d 自動清（8,386 → 1,012 檔）+
  breadth cache keep-last-30（222 → 60 檔，history.json 明確排除）。

### Why
產業掃描/動能/戰術層每天跑，但稽核發現 bridge 之下一層的 skills 積了一批
「會 crash、會給錯資料、壞了看不見」的債 — 其中 ic-memo crash 與 decision_lock
錯 ticker 直接威脅決策可信度，T4 不可達讓 Red Team veto 機制空轉。本版全數修復
並驗證（golden 26 asserts、check_skills、MSFT ic-memo 全鏈、momentum/predict smoke）。

## [4.3.0] — 2026-06-11 — 知識圖譜重構：CO_THEME clique → theme hub-and-spoke（minor）

### Changed
- **圖結構重構**（`Dashboard/page-graph.js` 全面重寫，1046 → ~620 行）：
  CO_THEME 邊（280 條中佔 262，同主題 N² clique = hairball 根源）不再渲染；
  client-side 從 ticker.metadata.themes 合成 ~30 個一級 theme hub 節點（amber、
  恆顯 label），ticker→theme `MEMBER_OF` spoke 取代 mesh。邊數 280 → 85（−70%），
  力導向自動形成主題星系。結構邊（PEER_OF / SUPPLIES_TO …）保留 ticker↔ticker
  直連。<2 成員的 hub 與無任何連結的孤立 ticker 在全景自動隱藏（搜尋仍可達）。
- **點擊互動改聚焦模式**：thermographic 火焰特效 / ignition shockwave / aurora /
  全圖 dim 全部移除 → 點節點只留 1-2 hop ego 子圖重新佈局（深度按鈕 1/2 hop），
  頂部麵包屑顯示聚焦對象，ESC / 點背景 / ✕ 返回全景。點 theme hub = 看該主題
  全部成員。detail panel 瘦身：pagerank/提及/連結 + 主題 chip（可點跳轉）+
  近期新聞 + 關聯列表（關係類型中文標示）。
- **Zoom 修復**：移除三個互搶的 auto-zoomToFit timer（50/800/2500ms）與
  onEngineStop 重複 fit — wheel/pointerdown 後 `userInteracted` 永久擋掉自動 fit。
  每幀 radial-gradient hub glow、`lighter` 合成、strokeText、d3ReheatSimulation
  全部移除，painter 只剩 circle + fillText — zoom/pan 變純 transform。
- **Label 策略**：theme hub label 恆定螢幕大小（除以 zoom scale，任何縮放都可讀，
  作為地圖地標）；ticker label hover/聚焦時恆定螢幕大小、其餘 zoom ≥1.4 淡入。
- **控制台重排**（`graph.html`）：搜尋加 datalist 自動完成（Enter / 選取 → 直接
  聚焦）；「時間衰減倍率」slider 換成直白的「結構邊權重門檻」；節點類型
  checkbox 換成可點擊的關係類型 chip 開關；砍 provisional toggle（現 build 無
  provisional 節點）；說明文案更新。thermal/aurora CSS 全刪。

### Why
原版 93% 邊是合成 CO_THEME clique，95 個同色節點自由漂浮 — 看不出結構；
三個延遲 auto-fit 跟 user 搶縮放、每幀漸層特效拖累 zoom 流暢度。重構依 KG
基本原則：clique 該還原成 hub-and-spoke（一個 16 股主題 = 16 條邊而非 120 條），
主題即地標、點擊即聚焦、資訊漸進揭露。`nexus_graph.json` / build_graph.py 不動，
純呈現層重構，legacy 多型別 build 仍可載入（自動跳過合成）。

## [4.2.0] — 2026-06-11 — 產業掃描頁重設計：結論→辯論→證據三層（minor）

### Added
- **委員會決議矩陣**（`Dashboard/sector.html` + `page-sector.js renderCommittee`）：
  `_phase4a.proposals` 4 條 lane（輪動/主題/新聞/宏觀）各自 HOT/COLD conviction 上畫面 —
  11 板塊 × 4 lane ▲▼ 投票格，lane 意見相左行高亮標「分歧」，每 lane rationale
  收合展開。此資料先前完全沒 bridge、0% 呈現。
- **Red Team 推翻條件 panel**（`renderRedTeam`）：`_phase4b.challenge_targets` 完整
  反證 + `IF/THEN/WITHIN` 觸發條件（amber mono block、關鍵字加粗）+ DA confidence
  徽章 + accepted ✓ + tail_risk_note。卡片上原截斷一句的 DA note 改為 ⚔ marker
  （hover 看全文），完整內容歸 panel。
- **量化證據矩陣**（`renderQuantTable`）：11 板塊可排序熱力表 — verdict / score /
  輪動 / uptrend / PE z1y / RS 5d/20d/3m / 30d beat rate (n=) / 分析師淨上修 /
  insider 買賣比 (n=) / 新聞情緒 / FRED 乘數。合併 `_phase1.sector_valuation` +
  `_phase3.sector_earnings_pulse` + `smart_money_signals` + `sector_news_sentiment`，
  全部是先前掃描有算但從沒上頁面的欄位。
- **宏觀 Overlay 條**（`renderMacroOverlay`）：`_phase0.fred_snapshot` chips
  （regime/曲線/real rate >2.0 ⚠/Fed 方向/velocity ↑↓）+ `step6_overlay` 乘數套用
  理由 + `political_risk_summary` 地緣風險 level 徽章與摘要文。
- **Today's Verdict hero 上產業掃描頁**：sector.html 原本只有 hidden stub（真卡片
  只活在 index.html），掃描結論在掃描頁反而看不到。複製完整 markup 並把
  `renderHandoff` 改傳 full data，briefing signal grid（廣度/FTD/頂部/FRED）一併呈現。
- `bridge.py`：新增 `_extract_committee` / `_extract_da_challenges` /
  `_extract_fred_overlay` / `_slim_valuation` / `_slim_pulse` / `_slim_smart_money`，
  market 增 `committee` / `da_challenges` / `fred_overlay` / `political_risk`，
  sectors[] 增 `valuation` / `earnings_pulse` / `smart_money` / `news_sentiment` /
  `fred_multiplier`。

### Changed
- 頁面重排為「結論 → 辯論 → 證據」：verdict hero 最上 → 委員會矩陣 + Red Team →
  sector cards → 量化矩陣 → 宏觀 overlay → catalyst/divergence/themes →
  **heatmap 移到頁尾**（live 行情非掃描產出，先前霸佔頁首）。
- `SECTOR_ZH` 補 sector_intel 內部名別名（FINANCIALS / CONSUMER_STAPLES /
  CONSUMER_DISCRETIONARY / COMMUNICATION / MATERIALS）— 中文名先前 fallback 成英文。
- 新區塊文案採 `t()` key + isZh 雙語 inline fallback，i18n.js 未動也雙語可用。

### Why
產業掃描每次跑 4 lane subagent + DA 消耗大量 token，產出 ~1300 行 sector_intel.json，
但 bridge 層只搬約 1/3 上 Dashboard——委員會投票、Red Team 反證、估值/盈餘/內部人
證據全被丟掉，頁面看起來「跑很貴、呈現很簡單」。本版把有決策意義的產出
（誰投了什麼票、什麼條件下論點會被推翻、verdict 背後的量化證據）全部接上畫面。

## [4.1.0] — 2026-06-11 — Break News 辯論 V5：盲開局 + 分歧閘門（minor）

### Changed
- **Round 1 改雙盲並行**（`scripts/break_news/debater.py`）：A/B 同時各自獨立評（都吃 opener
  prompt，互不見對方）。省掉舊 B 開局的 followup context，且 divergence 變成真訊號
  （舊制 B 看完 A 再寫，分歧被稀釋）。
- **Deterministic divergence gate（0 LLM）**：Round 1 後程式判斷是否值得花 token 辯下去 —
  verdict 對立（BULLISH vs BEARISH relation 投票）/ 同 subject|object pair predicate 極性衝突 /
  confidence gap ≥ 0.4（`BREAK_NEWS_DIVERGENCE_CONF_GAP` 可調）。任一 `stance: concede` 直接收斂。
  無分歧 → 2 call 收場（`close_reason=converged_round1`）。舊 round-1 early-stop（無 ticker→ticker
  relation / NEUTRAL 無 universe ticker）保留併入。
- **Round 2+ 改 slim rebuttal**（`prompts.py` 新 `REBUTTAL_SYSTEM_PROMPT` + `rebuttal_user_prompt`）：
  prompt 只給 headline 一行 + known entities/relations 一行 + gate 算出的確切分歧點 + 雙方 stance
  compact JSON — 不重貼 news 全文 / URL / triage。Output 砍半：`commentary ≤60字` + `stance`
  (challenge/concede) + 只新增的 `relations` + `done`，不重抽 entities、不重產 bull/bear。
- **Round 3 只留給 high-priority 且 round 2 後仍分歧**的 item。
- **SYSTEM_PROMPT 瘦身** ~2.6k → ~1.3k chars（schema 欄位不變，UI / `build_summary_block` /
  Nexus merge 全相容）。刪除舊 `followup_user_prompt` + `compact_thread_formatter`（無其他引用）。
- **`poller.py` `BREAK_NEWS_EST_CALLS_PER_DEBATE` 預設 6 → 3**：admission 預算反映新均值
  （收斂 2 call / 分歧 4-6 call），同 LLM 預算可辯約 2 倍條數。
- 新增 `close_reason` 值：`converged_round1` / `divergence_resolved`；summary 新欄位
  `divergence_gate_note`（gate 判定原文，rebuttal prompt 餵同字串讓辯論聚焦衝突點）。

### Why
- 舊制 normal item 固定 4 call（~10k tok）、high 6 call（~15k），Round 2/3 output 大量重複
  Round 1 已有資訊（entities 重抽、commentary 重寫 200 字）。新制收斂 case（多數）~3k tok
  （−70%），分歧 case ~5-6k（−45%）；rebuttal 聚焦 gate 給的確切衝突點 — 辯論更有效而非更長。
- Mock 全流程驗證：converge 2 call / diverge+concede 4 call → `divergence_resolved` /
  high persist 6 call 3 rounds / 雙開局失敗 → `failed`。

## [4.0.0] — 2026-06-10 — Protocol token 瘦身 + Model 分層（major）

> Major bump 理由：protocol 結構重組（spec 外移）+ subagent model 治理首次入 protocol。

### Changed
- **B1 spec 外移**：Phase 4.5 全部演算法區（366 行 — 4.5.0~4.5.4 pseudocode / 權重表 / shadow
  退出條件）抽到新 **`investment/protocol_appendix_price_framework.md`**（audit 用，跑 protocol
  不需讀；engine + golden fixtures 才是事實來源）。Protocol Phase 4.5 縮成 ~25 行封裝呈現層
  （verbatim 抄寫 + 紀律速記 + 指路）。
- **B2 敘述清理**：Phase 2 Valuation Specialist 的 reverse DCF pseudocode（~50 行，engine 已接管）
  → 6 行指路；Phase 2.4 時點說明 4-bullet → 1 行。
- **合計**：protocol 1853 → 1471 行（**−382 行 ≈ −21%**，PM 每次 `分析` 省 ~8-10k input token）。
  Phase 0-6 全數完整、golden 26 asserts 過。
- **Model 分層第一批（V4.0.0 Phase 2 新表）**：Sentiment / News / Technical lane →
  Agent tool `model="sonnet"`（rubric 明確的結構化評分）；Fundamentals / Valuation Specialist
  inherit（第二批候選）；**Red Team 永不降級**；MD formatter 維持 Sonnet。
  粗估單次 `分析` LLM 成本 −35-50%（3 lanes Opus→Sonnet ≈ 1/5 價）。
- **`shadow_report.py` 加 lane 哨兵段**：近 10 session lane mean drift vs 全歷史 baseline +
  val DISAGREE / polarization 異常計數。降級後前 10 session 盯它；異常 → 該 lane 回 inherit。

### Why
- PM 每跑一次全讀 protocol，366 行 engine spec 是純 token 浪費（spec 給 audit 不給跑步）。
- 不是每步都需要 Opus/Fable：判斷密集（PM/Red Team/Fundamentals）留強，結構化抽取降 Sonnet，
  deterministic（engine/Burry/ic-memo）0 LLM。品質由現成 det_shadow 對照 + validator gate 兜底。

## [3.49.0] — 2026-06-10 — 估值新 block 呈現層（ic-memo + decisions 頁）+ moat 容錯修復

### Added
- **ic-memo §8 擴充**（`build_fact_pack.py` section_8 + `compose.py` render_sec_8）：
  Fair Value Range（P25/50/75 + min–max + range_verdict + 錨一致度 CV）、Reverse DCF 隱含預期
  （含 OOR 警示）、Multi-Horizon 三框（5d band / 60d target / mhp_signal）、Archetype shadow
  blockquote（標示 shadow-only + flip 警示）。舊 entry 缺 block → 整段 graceful skip，
  §11 decision_lock 不受影響（新 block 全 advisory、不在 11-field hash 內）。
- **decisions 頁 Valuation 卡擴充**（`page-decisions.js` 新 `buildFvExtras()`）：anchor chips 下加
  4 行 — Range（P25/**P50**/P75 + AGREE badge）、5D Band + 60D + mhp_signal badge（hover 看
  signal_note）、Implied 5Y FCF CAGR（hover sanity note）、Archetype shadow（flip 標橘 ⚠）。
  舊 entry 自動隱藏。

### Fixed
- **ic-memo 對近期 entries 直接 crash（pre-existing）**：MRVL/PLTR/PANW 等近期 entry 的
  `fundamentals_lane.moat_assessment` 被 LLM 寫成 string（schema 要 dict）→
  `section_4_competitive` AttributeError。容錯：string → 塞 evidence 欄、level/type 缺 →
  degraded 不 crash。實測 MRVL memo 重新可產（rc=2 degraded-usable，符合該 entry 資料現況）。

### Why
- range / implied / archetype 算了不呈現 = 白算。本版補齊「user 看得到」的最後一哩。

## [3.48.0] — 2026-06-10 — Engine self-assemble + #8a 折扣 + golden 測試 + peer_pe 既有 bug 修復

### Added
- **`compute_price_framework.py --self-assemble`（P2 — 殺最後 LLM 抄寫路徑）**：quant 欄位由
  engine 直接讀 deterministic 源自組 — anchors（earnings cache DCF/PT + peer bundle peer_pe ×
  eps_ttm + supp bundle owner earnings ×15 + forecaster cache expected_value）、ev_block、
  archetype_inputs、peer/self ratios、beta、fred real rate、reverse-DCF fcf base。
  input file 給的欄位永遠優先（qualitative 欄 pattern/key_levels/catalyst 仍由 LLM lane 提供）；
  輸出 `self_assembled_fields[]` audit。實測 AAPL：24 欄自組、5/6 anchor 齊。
  整條估值鏈 raw data → verdict **0 LLM 算術 + 0 LLM 抄寫**達成。
- **`test_compute_price_framework.py` golden-fixture 回歸測試**：4 fixtures × 26 asserts
  （hypergrowth / financial / reverse DCF / degraded，全部人工驗算過的 baseline）。改 engine 必跑。
  已入 ops 工具箱 registry + CLAUDE.md shortcuts。

### Fixed
- **peer_pe_median 既有 bug（FMP stable migration 遺留）**：`/stable/profile` 已無 `peRatio` →
  factpack `_med("peRatio")` 默默回 None → **peer_pe_implied anchor 失效已久**。修：fallback 用
  peer ratios-ttm `pe_ttm` median（`get_ratios_ttm` 新欄；舊 slim cache 自動補抓）。
  eps_ttm 同因（stable quote 無 eps）→ 改由 self `pe_ttm` 反推 `price/pe`；虧損股 PE null →
  eps_ttm None，hypergrowth 規則退化為只看 rev_yoy（已註記限制）。
- **#8a horizon mismatch**：60d 層 `earnings_revision` 原直接用 forecaster 長期錨（等於假設
  60 天走完全程）→ 折算 `current + (blend − current) × 60/250`。spec + engine 同步。

### Why
- 「禁止 LLM 重新評估數字」紀律完成最後一塊：3.45.3 殺算術、3.48.0 殺抄寫。
- peer_pe bug 是 self-assemble 實作時順藤摸瓜抓到 — 若無此輪重構不會發現 anchor 默默缺位。

## [3.47.0] — 2026-06-10 — Dashboard Script 工具箱（/ops.html）

### Added
- **`/ops.html` 新頁（sidebar OPS 群組）**：Ops script 清單面板 — 每支 script 顯示
  名稱/說明/指令（📋 複製）/節奏/**上次執行多久前**/**到期 badge**（🔴 due / 🟡 never_run /
  🟢 fresh / ⚪ on_demand，due 排最前）。唯讀 — 不在 UI 執行，執行走 terminal。
- **`/api/ops/scripts`**（dashboard_server）：registry + artifact-mtime 推斷 last run
  （零侵入，不要求 script 寫 run log）+ cadence 到期判定（daily 26h / weekly 8d / monthly 32d 寬限）。
- **`config/ops_scripts.json`** registry（11 支首發：daily_update / weekly_review / shadow_report /
  backtest_postmortem / momentum journal / drift 稽核 / skills linter / sector digest / predict /
  nexus rebuild / schema 驗證）。直接編輯增刪。
- i18n `nav.ops`（zh/en）+ NAV_ITEMS。

### Why
- user 要在面板上看到「有哪些 script、上次多久前用、現在需不需要跑」。實測立刻有訊號：
  weekly_review 46 天未跑 → due 紅標。

## [3.46.1] — 2026-06-10 — shadow_report.py 讀出端 + dispersion backfill

### Added
- **`investment/scripts/shadow_report.py`** — 3 個 shadow 實驗的讀出端（之前只有寫入沒有讀出，
  20-session checkpoint 到了只能手挖 history）。唯讀、一次算齊：
  - **#2 dispersion backfill**：歷史 entries anchors 重算 CV 分布 → 校準 agreement_grade 門檻
  - **#6 oe shadow**：owner_earnings anchor 換 rate_linked 倍數重 blend → verdict 翻轉率 + 20-session checkpoint decision
  - **#3 archetype shadow**：flip_vs_live 翻轉率 + archetype 分布
  - **#4 news 監測**：post-切換 news_score 分布 vs baseline（mean shift）+ leakage 累積率 + 凍結窗進度
  - 數學 import 自 `compute_price_framework`（單一事實來源）；輸出 stdout + `reports/SHADOW_REPORT_<date>.md`（`--json` 機讀）
- 此為 #10 anchor 校準 cron 的前半身（讀出邏輯就緒，cron 化留後續）。

### Why — backfill 立即發現
- **歷史 37 筆 CV 分布：median 0.46、P33 0.367、max 1.27** — 拍腦袋初值 0.15/0.35 會把幾乎全部
  session 判 low agreement。真實 anchor 分歧遠大於直覺 — 幸虧 3.45.1 當時只做展示沒接 cap。
  校準建議門檻（33/66 pct）：**high<0.367 / low>0.484**，#2 cap 接線前由 user 核可。

## [3.46.0] — 2026-06-10 — Valuation Archetype Shadow + 3 新 anchor（external review #3，shadow-only）

> 固定 anchor 權重一視同仁：DCF 0.45 對 FCF 負成長股是雜訊、peer_pe EPS≤0 失效、金融股無 P/B 維度
> → 原 6-anchor 池對未獲利成長股/金融股估值半殘。本版 archetype 動態權重 + 補 3 anchor，**全 shadow**。

### Added
- **`compute_price_framework.py` — `valuation_archetype_shadow`**：deterministic archetype 分類
  （financial → hypergrowth(rev>25% or EPS≤0) → cyclical(sector+8Q 淨利率 σ>5pp) → mature_cashflow
  (FCF>8%+rev<15%) → balanced fallback，按序首中）+ 9-anchor 池 archetype 權重 shadow blend +
  `flip_vs_live`。**live `fair_value_summary` 權重/verdict 完全不動**；balanced = live 權重 + 新 anchor 0
  （shadow==live 自驗路徑，實測 flip=false）。權重表 `ARCHETYPE_WEIGHTS` 單一事實來源。
- **3 新 anchor**：`peer_ev_ebitda_implied` / `peer_ev_sales_implied`（精確 EV 數學：
  `(peer_med × EV/self_mult − netDebt)/shares`）+ `pb_roe_justified`（`(ROE−g)/(r−g)×BVPS`，
  r=10Y+beta×ERP，justified P/B clamp [0.2,15]）。
- **`company_context.get_ratios_ttm()`**：key-metrics-ttm + ratios-ttm 雙 endpoint merge slim
  （ev_ebitda/ev_sales/roe/pb/bvps/net_margin），24h cache，2 call/ticker 首跑。
- **`phase1_factpack.py` PEER_BUNDLE 新欄**：`peer_ev_ebitda_median` / `peer_ev_sales_median` /
  `peer_pb_median` / `peer_ratios_n` / `self_ratios_ttm`。實測 AAPL：peer EV/EBITDA median 20.4 vs self 26.9。
- Protocol 4.5.0c 章 + Phase 2.4 input 欄位註記；schema `valuation_archetype_shadow` block；
  validator §5h（archetype/verdict enum + flip bool，warning-only rc=0）。

### Why
- 行為差異紀律（reviewer P2）：與 #6 oe shadow 同模式 — **退出條件 ≥20 session 翻轉率報告 → user 拍
  → #3b 切 live**（cap/T5 接線同步）。實測 hypergrowth case：live $225.7「overvalued」vs shadow
  $270.5「fairly_valued」（EV/Sales 0.30 主錨）— 正是要量化的型態差。
- Deferred：forward EPS 替換 peer_pe TTM、cyclical normalized-earnings anchor、cap/T5 接線（#3b）。

## [3.45.4] — 2026-06-10 — News lane PT 去重（external review #4）

> 同一 sell-side PT consensus 計分三次：Valuation anchor (0.20) + MHP 60d pt_60d (0.35) + News lane
> 「PT vs price 折溢價 ±1」— cross-lane anchoring，共識牛市系統性放大多頭。本版砍第三處。

### Changed
- **`skills/market-news-analyst/scripts/fetch.py` — PT 注入層剝離**：payload 移除 `price_target` block
  （target_high/low/consensus/median + avg targets 全部絕對 level），换成 `_pt_revision_momentum()`：
  30d/90d consensus PT **變動方向+幅度%**（UP/DOWN/FLAT/UNKNOWN + delta_1m/3m + 家數）。
  LLM 看不到 level 才真的不會計分（rubric 層刪行不夠 — 顯性規則會變隱性偏誤）。
  實測 AAPL：levels 全剝、momentum 有料（1m PT 下修 8% = 真 sell-side 行為訊號）。
- Protocol News rubric：刪「PT consensus vs price >20% 折溢價 ±1」，新增 `pt_revision_momentum`
  計分項（direction=UP 且 delta>3% → +0.5~+1；DOWN → -0.5~-1）— News lane 換到不重複的訊號，非淨損失。
- **news_lane 文字持久化（V3.45.4 必填第 5 欄）**：`reasoning_one_line` + `key_factors[]` 進 export —
  之前 News reasoning 不落地（0/134 entry 有 key_factors），post-hoc 防線沒有 haystack。
- **`apply_det_shadow.py` — `news_pt_leakage` classifier**（V2.19 red_team_basis 同模式）：
  掃 reasoning_one_line + key_factors 的「PT 折價/溢價/target vs price」措辭 → det_shadow flag
  （warning 級累積統計，不改 score）。「PT 上修/下修」revision 措辭合法不觸發。det_shadow version → V3.45.4。
- **Phase 6 News weight 凍結窗**：前 10 個含 News lane 的 session `weight_adjustment_delta.News` 強制 0
  （標 `news_weight_frozen_v3454`）— News score 分布將系統性下移（baseline {+2:18/31} 牛市偏高），
  防學習層把分布偏移誤判成 lane 失準。
- `validate_session_export.py` §5g：news_lane 新欄 + direction enum + leakage type，warning-only rc=0。

### Why
- 行為差異驗證：history 反事實跑不了（PT 子分數無獨立存、reasoning 不落地、per-entry threshold 不落地）→
  改前向監測：news_score 分布 vs baseline `{-1:1, 0:2, +1:6, +2:18, +3:4}` (n=31) + leakage 累積率。
  邊界脆弱集上界 8/31（default boundaries ±0.20），實際翻轉預期遠小（移除是向下推力）。
- 不做 double-shadow（News lane 跑兩次 = 2× LLM 成本）；PT [low/consensus/high] 三點化 anchor 拆給 #1 後續。

## [3.45.3] — 2026-06-10 — Price Framework Engine script 化 + Phase 2.4 時序修正

> Protocol review 發現 B1（P0 級）：V3.45.x 累積的數學（weighted percentile、CV、reverse DCF 迭代解）
> 超出 LLM inline 可靠範圍，但 spec 仍要求 PM「inline deterministic 計算」— 自相矛盾。
> 本版 script 化整包 price framework。版號 3.45.2 跳過（原配給 #4 PT 去重，order 對調後 #4 移後）。

### Added
- **`investment/scripts/compute_price_framework.py`（V3.45.3 engine）** — 一個 call 算完 4 個 block：
  `fair_value_summary`（V5.0 blend，演算法 byte-identical）+ `fair_value_range`（weighted percentile/CV/oe shadow）
  + `multi_horizon_price_framework`（5d band/60d target/convergence）+ `implied_expectations`（reverse DCF bisection 解）。
  input 含 ticker 且缺 volatility → 自抓 FMP OHLCV 算 sigma/atr/momentum（消除 LLM 抄寫風險）。
  缺料降級照 spec（degradation is data, not failure）→ rc=0；只有 unparseable input / 缺 current_price → rc=1。
  輸出含 `engine` stamp 供 audit。實測 full / degraded / live-fetch 三路徑 rc=0。
- **新 PHASE 2.4 — PRICE FRAMEWORK ENGINE**：phase order 改 `0→1→2→2.4→2.5→2.8→3→4→4.5→5`。
  時點選 2.4 的原因：T5（2.5）直接用 mhp_signal、Red Team（2.8）直接收 red_team_kill_seed、
  Phase 3/4/4.5 全引用既存輸出 — 一次解掉 V3.45.0 的「前向引用未來 phase 數字」時序 fudge（B2）。

### Changed
- Phase 4.5 改「封裝呈現層」：禁止 LLM 手算/重算，演算法區塊降格為 spec 文件（audit 用），實作以 script 為準。
- `implied_expectations` 計算歸屬：Valuation Specialist 手算 → Phase 2.4 engine（Specialist 只負責 anchors）。
- T5 MHP 強化措辭：移除「回頭補強」hack → 2.5 當下直接可用。
- Phase 4 trade_plan provenance：改「直接取 Phase 2.4 engine 輸出」。
- convergence degraded guard：`fair_value_summary.confidence==low` 時 signal_note 強制附「訊號僅供參考」（script+spec 同步）。
- **B3 常數註記**：earnings-yield premium（real 10Y + 0.04）vs reverse-DCF WACC（nominal 10Y + 0.045）
  用途不同非筆誤，集中定義於 script 頂部 `ERP_EARNINGS_YIELD` / `ERP_WACC`。
- CLAUDE.md Ops Shortcuts + schema 註記 engine 歸屬。

### Why
- 「禁止 LLM 重新評估數字」的紀律只有在數字不是 LLM 算的時候才成立。engine 把 deterministic
  計算真正 deterministic 化，同時讓三個下游（T5/Red Team/trade_plan）的引用全部合法化。

## [3.45.1] — 2026-06-10 — 估值層 P0+P1：dead-code 修復 + anchor 區間 + reverse DCF（external review batch 1）

> 外部 AI model review 10 點建議的 P0+P1 批次（全 advisory/sibling，零決策數學衝擊、零 decision_lock 破壞）。P2（改決策數學）逐項另議，#10 anchor 校準 cron 屬獨立 infra。

### Fixed
- **#7 convergence dead code** — `multi_horizon_price_framework.convergence` 的 `high_conviction_long_zone` 分支永不觸發：
  舊條件 `current < band_lower_capped`，但 band_lower 必 < current（half_width 1.28σ > drift clamp 0.6σ），
  capped=max(band_lower, support) 要 > current 需 support>current（反常）。改判定為
  `band_point < LT AND mid_target > current AND current < LT×0.9`（現價顯著低於長期FV + 中期動能向上 + 短期點估計仍低於FV）。

### Added
- **#1 `fair_value_range`（Phase 4.5.0b，advisory sibling）** — anchor 分布區間 P25/P50/P75 + min/max + `range_verdict`
  位置判定（undervalued_zone / fair_zone / overvalued_zone / extreme_*）。解決「加權平均 $215 沒人信、分歧被銷毀」。
  退化：n≥4 → weighted_percentile；2-3 → minmax_fallback；<2 → null。
- **#2-half 分歧度（純展示）** — `anchor_dispersion_cv` + `agreement_grade`（cv<0.15 high / <0.35 medium / else low）。
  3.45.1 起累積數據，**不**接 Phase 4.6 cap（接線 + winsorize 留 P2，待用歷史分布校準門檻）。
- **#5 `implied_expectations`（reverse DCF，Valuation Specialist 必填）** — 現價隱含 5Y FCF CAGR vs 實際 vs lane 估。
  輸入釘死：terminal_growth 2.5%、WACC=FRED 10Y+ERP 0.045（FRED 缺 → `wacc_source=fallback_fixed` 用 4.5%+ERP，不整組 null）、
  FCF base=owner earnings（Burry 規則 3 一致）、FCF≤0→null 不硬解、implied_growth clamp [-20%,+60%]（超界 `implied_out_of_range=true`）。
  **不**進加權/lane score/decision_lock；`red_team_kill_seed` 餵 Red Team subagent 當 kill condition 起點。
- **#6 owner-earnings 倍數 shadow（option a）** — `owner_earnings_multiple_shadow`：live anchor 仍 static ×15（weighted_fair_value 不變），
  另 shadow-log `oe_mult_rate_linked = clamp(1/(real_10y+0.04), 10, 22)`。**退出條件寫死**：≥20 session 後翻轉率 <15% → 切換提案；≥15% → 維持 static 待 backtest。

### Changed
- `phase5_export_schema.md` — 新 `fair_value_range` + `implied_expectations` block + 2 欄位 row。
- `validate_session_export.py` — 兩新 block warning-only 檢查（range_method/range_verdict/agreement_grade enum、
  implied fcf_base_source、FCF≤0 一致性）；缺/不全 rc 維持 0，向後相容。實測既有 V5.0 entry rc=0。
- Phase 5 MD §6 加「長期區間 + 隱含預期」兩行；Red Team subagent prompt 加 `IMPLIED_EXPECTATIONS` 輸入。

### Why
- 契約鐵律：`fair_value_summary`（含 weighted_fair_value/verdict_band/confidence）byte-for-byte 不動 →
  ic-memo 11-field decision_lock、apply_det_shadow val_det、validator、舊 history entry 全相容。
  新區間/隱含預期/分歧度一律另存 sibling，**不**進 decision_lock。verdict_band 原邏輯不碰，位置判定獨立用 `range_verdict`。

## [3.45.0] — 2026-06-10 — investment Phase 4.5 → Multi-Horizon Price Framework

### Added
- `investment/investment_protocol_v5_0.md` — Phase 4.5 從單一 `fair_value_summary` 升級成三時間框架
  Multi-Horizon Price Framework（仍 inline deterministic、0 LLM 重評）：
  - **4.5.1 Short-Term 5-Day Band**：波動率錨定機率帶。`band = current × (1 + drift_sigma·σ_daily·√5 ± 1.28·σ_daily·√5)`；
    drift 查表（pattern_taxonomy 8 型 + smart_money label，clamp [-0.6,+0.5]）；
    catalyst override（news_lane.immediate_catalyst_5d → 放大帶寬 + 降信心 + NEUTRAL 收 drift）；
    key_levels support/resistance 反射 capped 帶。
  - **4.5.2 Mid-Term 60-Day Target**：`0.40 momentum_target + 0.35 pt_60d + 0.25 earnings_revision`（缺項重分配）+ key_level reality check。
  - **4.5.3 Convergence**：三框相對位置 → `mhp_signal` ∈ {wait_for_pullback, high_conviction_long_zone, momentum_not_value, neutral_aligned}。
  - **4.5.0 Long-Term**：既有 6-anchor `fair_value_summary` 原封不動，當長期層；MHP `long_term_ref` 引用不重算。
- Phase 2 Technical lane 新增 `volatility` sub-block（`atr_14` / `hist_vol_20d_daily` / `momentum_20d_pct`，deterministic FMP read）。
- `investment/phase5_export_schema.md` — 新 `multi_horizon_price_framework` block + `technical_lane.volatility` sub-block + 欄位 row。

### Changed
- Phase 3 T5 仲裁：`mhp_signal` reasoning 強化（wait_for_pullback / momentum_not_value），**不改決策數學**。
- Phase 4 trade_plan：明定 entry/TP/SL provenance（補原 protocol 未定義缺口）— entry ← 5d band、TP ← 60d mid_target（cap at resistance）、SL ← min(band_lower, support)。
- Phase 5 MD §6 改成三框架表；§8 進場計畫標註取值來源。
- `investment/scripts/validate_session_export.py` — MHP advisory 檢查（warning-only，rc 維持 0；long_term_ref 一致性、mhp_signal enum、sub-block 完整度）。

### Why
- 單點合理價對 5 天尺度不誠實 — 短期是機率分布不是一個點。三框架各用該時間尺度合適方法，
  且三框相對位置自動產生交易語意，直接補上 protocol 原本未定義的 trade_plan TP/SL 來源。
- 契約零破壞：`fair_value_summary` key/shape 不動 → ic-memo 11-field decision_lock、apply_det_shadow `val_det`、
  既有 history entry、validator 全部相容；MHP 為 derived/advisory 不進 decision_lock。

## [3.44.1] — 2026-06-10 — FMP v3 calendar/profile 退役 → migrate /stable

### Fixed
- `~/.claude/skills/economic-calendar-fetcher/scripts/get_economic_calendar.py` —
  `/api/v3/economic_calendar`（legacy 403）→ `/stable/economic-calendar`，apikey 改 query param。
  欄位同形（date/country/event/currency/previous/estimate/actual/impact）。實測 543 events。
- `~/.claude/skills/earnings-calendar/scripts/fetch_earnings_fmp.py` —
  `/api/v3/earning_calendar`（403）→ `/stable/earnings-calendar`；profile enrichment 由
  `/api/v3/profile/{batch}`（403，stable 不支援逗號批次）→ per-symbol `/stable/profile`
  併發抓（ThreadPool 16）。欄位 rename `mktCap`→`marketCap`、`exchangeShortName`→`exchange`；
  stable 無 `time` 欄 → timing 默認 TAS。實測 21 家 US mid-cap+（cap filter + exchange + 富集正常）。

### Why
- V3.44.0 sector prefetch 暴露 econ/earnings calendar SOFT silent fail：FMP 對非 legacy key
  退役整批 v3 endpoint（含 profile），sector Phase 3 Step 2/3 拿到 null 被誤當「本週無事件」。
- 影響面：任何仍打 `/api/v3/{economic_calendar,earning_calendar,profile}` 的 skill 都會 403；
  專案內取數已走 `/stable/`（`sector/lib/fmp_client.py`），照此 migrate 即可。

## [3.44.0] — 2026-06-10 — sector protocol 三招砍 cache_read（prefetch + Sonnet lane + no-MCP）

### Added
- `sector/scripts/phase_prefetch.py`（NEW，read-only / 0-LLM）：並行跑 Phase 1 valuation +
  Phase 3 全部取數（`fetch_sector_valuation` / `fetch_earnings_pulse` / `fetch_smart_money` /
  `fetch_sector_news` / `fetch_general_news` / `sentiment` / econ+earnings calendar / `sector_digest`），
  寫 cache 的照寫、stdout-only 的 inline 進單一 `sector/cache/phase_prefetch_<D>.json`。
  `rc=1` 當任一 HARD task（valuation/earnings_pulse/smart_money/sector_news）失敗 → 維持原
  「valuation HARD FAIL → abort」契約。`SECTOR_PREFETCH_TIMEOUT_SEC`(預設 360) 罩住 smart_money
  的 ~131 ticker insider-stat 慢掃。複製 3.42.0 invest factpack 模式。

### Changed
- `sector/phase_1-2-3.md` Phase 3 加 **FAST PATH**：預設 1 turn 跑 `phase_prefetch.py` + Read JSON，
  取代原 ~9 個逐項 Bash/MCP turn（實測 sector run 24 Bash turn，cache_read 逐 turn 16K→131K
  雪球 = 89% 帳單）。逐 Step 規格保留為 fallback。
- `sector/phase_4-5.md` Phase 4a 的 4 個 lane subagent + Phase 4b Devil's Advocate 加
  `model="sonnet"`（有界 JSON 任務不需 Opus；**Arbiter/Phase 4c 留 Opus**）；harness 不支援
  `model=` 則忽略、退回繼承主模型。
- `sector/sector_protocol_main.md` GLOBAL RULES 加「不用 fmp MCP / 不 ToolSearch」：取數全走
  local scripts，禁為抓資料 ToolSearch `mcp__fmp__*`（省 discovery turn；實測有一個 t28→t31
  純 tool discovery 浪費）。唯一例外 Phase 3 Step 5 narrative WebSearch。

### Why
- 盤前 token 報表診斷出 sector run（$4.25 / 997s / 2.17M tok）成本主體是 **cache_read 雪球**：
  24 個循序取數 Bash turn，每 turn 重收漲大 context（per-turn cache_read 16K→131K 單調grow）。
  與 3.42.0 invest 同病。三招對症：**prefetch 砍 turn 數**（主菜）、**Sonnet lane 砍 fan-out 算力**、
  **no-MCP 砍 discovery turn**。
- 決策邏輯**零變動**：prefetch 純聚合既有 fetch script、不評分不寫 decision；Sonnet 只換 lane 算力，
  Arbiter 仍 Opus；no-MCP 只限制取數路徑。

## [3.43.0] — 2026-06-10 — per-model token 計量（call 數 → input/output/cache/$）

### Added
- `scripts/break_news/llm_drivers.py` — `LLMResult` 加 5 個 token 欄位
  (`input_tokens`/`output_tokens`/`cache_read_tokens`/`cache_write_tokens`/`cost_usd`)；
  `run_claude` 從 `--output-format json` envelope 抽 `usage`+`total_cost_usd`；
  新 `parse_stream_log_usage(path)` 解析 protocol 的 stream-json log 末尾 `result` event。
- `scripts/_shared/model_router.py` — usage state 加 per-model `tokens` dict
  (`_blank_tokens` + `_load_usage` 自動 migrate 舊檔)；`_accumulate_tokens()` 累加
  (容雙命名)；`_record`（per-call debate）+ `note_run(tokens=)`（protocol run）都累加；
  `model_status()` expose `tokens`。
- `dashboard_server.py` — `run_protocol` 結束時解析 stream-json log → 把該 run 的 token
  歸戶到 `proto_model`（透過 `note_run(tokens=)`）。
- `Dashboard/utils.js` + `style.css` — sidebar LLM 面板每個 model 下加一行
  `<總 tok> · in/out/cache · $<cost>`（`.sidebar-llm-tok`）。

### Why
- 盤前檢查 token 報表需求暴露盲點：系統只記每模型「call 數」，從不記 token。
  真 token 全在 agentic protocol（sector/news/invest）+ break-news debate，散在
  stream-json log 裡沒被聚合。此版把 token+成本歸戶持久化，sidebar 直接看當日用量。
- 本次盤前實測：news $2.75 + sector $4.25 = **claude 今日 $7.00**
  (in 27.8K / out 77.6K / cache_read 3.09M)。cache_read 佔 89% — 成本主要在
  cache_read（10% rate）與 output，fresh input 極小。

## [3.42.0] — 2026-06-09 — investment protocol Phase 1 取數合併（砍 cache_read 雪球）

### Added
- `investment/scripts/phase1_factpack.py`（NEW，read-only / 0-LLM）：Phase 0 cache 抽取 +
  4 個 Phase-1 bundle（`ticker_data` / `earnings_analyst` / `peer` / `fmp_supp`）一次聚合成
  單一 JSON（~2-3k token）。重用既有來源（`run_dual_fetch.sh` / `company_context.get_peers/get_profile`
  / `fmp_supplementary.get_supplementary_bundle` / earnings-analyst cache），剝除 dual_fetch
  `_audit`（Phase 1 isolation 契約），fail-soft 不中止 protocol。`phase0_source==STALE_NEEDS_L3`
  時不跑重 L3 skill chain，交還 protocol 判斷。
- `investment/investment_protocol_v5_0_DESIGN_NOTES.md`（NEW）：純人讀設計理由檔（runtime 不載入）。

### Changed
- `investment/investment_protocol_v5_0.md` Phase 1 加 **FAST PATH** 段：預設跑
  `phase1_factpack.py <TICKER> --out /tmp/<TICKER>_factpack.json` 一次取數，取代原本 ~13 個
  逐 bundle 的 Bash turn（每 turn 重收漲大的 context 為 cache_read）。原手動逐 bundle 流程保留為
  factpack 失敗時 fallback。
- 把 V2.18.0 / V2.19.0 設計理由 + V2.14.0 IC-memo 動機從 protocol 主文移到 DESIGN_NOTES.md，
  主文留一行指標；對應**操作規則**仍全數保留在 Phase 3 step 定義（已 grep 驗證重複）。

### Why
- 診斷上一個 5h 視窗撞限：單日 34M token，其中 `分析 MRVL` 一個 run = 9.9M，94% 是 cache_read。
  拆解發現主因不是 FMP bundle（全部 tool_result 才 29k），而是 **85 turn × 漲大的 context**，
  其中 ~13 個 turn 純做循序取數。合併成 1 call 預估每個 `分析` run 省 ~1.5M+ cache_read。
- 決策邏輯**零變動**：factpack 純聚合既有來源、不評分、不寫 history；設計理由抽離不動任何 step 規則。

## [3.41.0] — 2026-06-07 — Rec 11 熱區保守性鬆綁（首個決策層 weekly-review 調整）

### Changed
- `investment/investment_protocol_v5_0.md` decision band 加**熱區例外**：
  `final_score ∈ [0,+staged_threshold) ∧ industry_top_30pct ∧ macro_regime∈{RISK_ON,BULL}
  ∧ decision_cap_active!=true ∧ mandatory_risk_flags 空` → default HOLD 降為
  `STAGED_ENTRY (hot_zone_probe)`，`position_size_pct ≤ 0.0015`（15bps）。
- cap 規則第 6 點：熱區 probe 時保留 STAGED，不 force CANCEL（systemic/decision_cap 觸發的 cap 不適用此例外）。

### Added
- `investment/phase5_export_schema.md` 新增 `hot_zone_probe` bool 欄位。
- `investment/scripts/validate_session_export.py` § 11：hot_zone_probe enforcement
  （STAGED_ENTRY / ≤15bps / 與 decision_cap 互斥）。4-case smoke 全綠。
- `reports/decision_review/ADJUSTMENT_LEDGER.md` Rec 11（target_metric: Semis HOLD-miss<60%
  / CANCEL-miss<60% / deep-dive hit 不退；**Semis HOLD-miss 回升>70% → paused**）。

### Fixed
- `scripts/build_event_index.py:_load_adjustment_ledger` status 比對改 `startswith("active")`，
  補抓帶括號註記的 entry（Rec 10 `active（止血值…）`）。`adjustment_ledger_active` 7→8 筆。

### Why
- REVIEW_2026-06-07 量化確認 Pattern A（Semis HOLD-miss 86% N=22）+ Pattern B（CANCEL-miss 71% N=21）：
  miss avg runup +30.5% vs drawdown −3.2%（Rec 9 證實真錯過非避損，H1 確認 H3 否證）。正分模糊區
  熱門半導體 × 多頭 default 觀望系統性錯過平順上漲。
- promoted TODO-001 + TODO-002（連續 2 輪 REVIEW READY、blocker 已清）。**首個 investment_protocol
  決策層 weekly-review 調整**（前 10 Rec 皆 parser/verdict/instrumentation，零下單影響）。
- regime guard（只 RISK_ON/BULL）+ decision_cap/risk_flag 兩道硬保險 + 15bps 倉位上限三重 bound
  下檔風險；⚠️ 2026-06 中旬預期大幅回檔時規則應自動 dormant，首兩週加嚴觀察。

## [3.40.8] — 2026-06-05 — Market Mood 不再被 put/call proxy 永久拉多

### Fixed
- `skills/market-sentiment-analyzer/scripts/mood.py` 將 CNN `put_call_options` fallback 降為弱 proxy：
  不再用完整 raw put/call 權重，且 signed score capped at ±50。
- 新增 `fg_quality_signed`，把 Fear & Greed 內部的 stock price strength、stock price breadth、
  junk bond demand 轉成獨立市場品質訊號，讓廣度弱/信用弱能抵銷單一偏多期權 proxy。
- 重產 `Dashboard/market_mood.json` 與 `Dashboard/data.json`：今日 Market Mood 從 `+36 Greed/偏樂觀`
  修正為 `+2 Neutral/中性`。

### Why
- 原公式在抓不到 CBOE raw put/call 時，把 CNN 子指標 `96.6` 等同 raw put/call 強訊號，
  導致頁面即使 SKEW high、breadth/strength 弱、junk bond demand 極低，仍每天顯示偏樂觀。

## [3.40.7] — 2026-06-05 — Break News 源整理：移除 StockTwits + 新增 3 RSS

### Removed
- **StockTwits social source** (`scripts/break_news/social_sources.py`
  `fetch_stocktwits` + `STOCKTWITS_*` env vars + adapter-list entry)。實測每 cycle
  抓 ~35 則但只有 ~5%（63/1304 bn files）曾成為 primary source — 幾乎純雜訊進 Raw
  流。整段移除。

### Added
- **3 個新 RSS feed** 進 `news/fetch_news_rss.py` FEEDS（9→12）：
  - `Fed Press`（HIGH）`federalreserve.gov/feeds/press_all.xml` — 低量高衝擊 macro 源。
  - `Nasdaq Markets`（MEDIUM）`nasdaq.com/feed/rssoutbound?category=Markets`。
  - `Benzinga`（MEDIUM）`benzinga.com/feed`。
  - 三者皆經 `fetch_feed` live 驗證：HTTP 200 + 有效 item + 日期新鮮。

### Why
- StockTwits 非官方 API 噪訊比過低、user 判定無用。補上 Fed/Nasdaq/Benzinga 維持
  break-news 進料廣度（FEEDS 為 news protocol 與 break news 共用，兩邊同步受惠）。
- 已淘汰候選並記錄：WSJ Markets（`feeds.a.dj.com` item 全凍結在 2025-01-27，dead
  endpoint）、GlobeNewswire（法文/立陶宛文 micro-cap PR 噪訊）、Fool/FT（301）、SEC
  EDGAR（403）。

## [3.40.6] — 2026-06-03 — 動能頁「空方」欄數字對齊修正

### Fixed
- 動能 screener 表格「空方」欄數字靠左、與右對齊的 header 不對齊。`Dashboard/page-momentum.js:1589`
  的 cell class 只有 `col-fund text-xs`，缺 `text-right font-mono`（其他 numeric 欄 P/S、GM%、5D% 都有）。
  補上後與 header 及其他數值欄一致右對齊 + 等寬字體。

### Why
- 視覺 bug：數字歪斜影響可讀性，跟同列其他百分比欄不一致。

## [3.40.5] — 2026-05-31 — 新聞戰情室卡片可點開原文

### Fixed
- **新聞頁卡片現在可點「來源」→ 開原文 URL**（新分頁）。`url` 本來存在 `*_raw.json` 抓取階段，
  但 triage / digest 階段只保留 `news_id`、把 `url` 丟掉，導致卡片無連結。
- `bridge.py` `_raw_pub_map` 改回傳 `news_id → {published, url}`，`extract_news()` 用 `news_id`
  重新 join 回 url 並寫進 news item。
- `Dashboard/page-news.js` source_label 改 render 成 clickable `↗` link（`target=_blank` + `rel=noopener`）；
  舊 digest（該日無 `raw.json` 或無 `news_id`）無 url 時 graceful fallback 回純文字標籤。

### Why
- 使用者反映新聞戰情室「沒辦法點開看原文」。URL 一路被中間階段吞掉，只需在組 `data.json` 時用
  既有的 `news_id` 重新接回，無需改 digest schema。

## [3.40.4] — 2026-05-31 — 短期雷達：產業趨勢榜可點 → 列出**完整**成分股（finvizfinance）

### Added
- **產業趨勢榜（radar `產業趨勢榜`）每列可點 → 列出該 finviz 產業的完整成分股（含小中型）**。
  新 server route **`GET /api/industry/<name>`** 用 **`finvizfinance` Screener**（免 API key、公開爬，套件已裝）撈整個 finviz
  產業，回 `{ticker,company,sector,market_cap}` list + **12h TTL 快取**（`INDUSTRY_CACHE_TTL_SEC`，成分股不常變、避免每點都爬）+ lazy import 防呆 + 名稱 regex 驗證。
- `page-radar.js` `showIndustryStocks()` 主打此 endpoint（完整），**heatmap 當 fallback**（finviz 爬失敗才退回本地大型股）；
  每檔成分股 chip 沿用 `analyze-ticker-btn`（→ 深度分析）+「在 finviz 看全部 ↗」連結 + 樣本數/快取標示。
  `_industryRow` 加 `data-industry`+clickable、`radar.html` 加 `#ind-stock-panel`。
  chip 顯示**格式化市值**（`_fmtMktCap`：$X.XXB / $XXX.XM）；移除多餘的「在 finviz 看全部」按鈕（完整清單已在 app 內）；
  修 hover 把 ticker 洗成淡色看不見（ticker span 改 `var(--text-card-title)` 固定色）。

### Why
- 使用者要從產業榜 drill-down 到「這類**所有**股票」。先評估本地 heatmap 只大型股（Solar 1、半導體設備 0…），
  確認 `finvizfinance`（theme-detector 既有依賴）可免費撈完整 → 升級成完整版。
- 效果：Communication Equipment 7→**44**、Solar 1→**22**、Semiconductor Equipment & Materials 0→**29**。
- 成本/風險：cache miss 爬 finviz ~2-4s（之後 12h 快取即時）；finviz 偶爾擋爬 → 自動 fallback 本地大型股 + finviz 連結。

## [3.40.3] — 2026-05-31 — Rec 10 / TODO-011：news-digest verdict 門檻止血（單股 2.0% 誤套指數）

### Fixed
- **Rec 10 / TODO-011 — news-digest verdict 結構性 0% hit**：`verdict_news_digest`
  用 module 全域 `HIT_THRESHOLD_PCT=2.0`（為單股設計）評 SPY 市場級 call。SPY 窗口內
  幾乎不動 ±2% → 所有強訊號被壓成 neutral，news-digest hit_rate 結構性 0%（連兩週 0524/0531
  列盲點）。新增 `NEWS_HIT_THRESHOLD_PCT = 1.0` index-level 專屬門檻，`verdict_news_digest`
  改用之；**deep-dive 的 2.0% 不動**。

### Why
- 純回測 verdict 標籤規則，**不碰任何 live 決策 / protocol** → 零下單風險、可逆。root cause
  是確定的單位錯配 bug 非假設。±1.0% 經現有 7 筆強訊號驗算：救回唯一明確正確 call
  （2026-05-14 看空 SPY −1.93%），不像 ±0.5% 把 sub-1% 雜訊誤判成反向 miss。rebuild 後
  news-digest hit 0→1（miss 2 / neutral 35）。N≥15 強訊號累積後再精校門檻值（見 TODO-011）。

## [3.40.2] — 2026-05-31 — 動能選股 Journal 統計區：中文化 + 點訊號→篩選 + unknown 說明

### Changed
- **Journal 統計區塊全繁中**（`Dashboard/page-momentum.js` renderStats）：修掉殘留英文 —
  by-signal 標題後綴 `(20d win rate)`（原本在 zh 還重複疊一次）改成 `分組 · 20d 勝率`、`Filled:` 改用 `fills_label`、
  「等待 20d 回填」、「Signal」表頭、量能 regime 表的 `expanding/stable/contracting`（新 `vol_trend_map`）、
  stage（走 `stages_map` 全中文）、空狀態字串，皆改走 i18n（`Dashboard/i18n.js` zh+en 補 key）。
  **Volume Regime Alpha 表標題 + 7 個欄位表頭（Trend/Stage/Ratio/n/Win%/Mean/Median）亦翻**（th 補 id + renderJournalStats set）。
- **`unknown` 改可讀標籤 + 說明**：`stages_map.unknown` 「未知」→「資料不足」/ en「Insufficient data」；
  主表 stage cell 為 unknown 時 hover 出原因（`stage_unknown_note`：歷史<200日無法分類）。`sector` 已是「未分類」。

### Added
- **點訊號列 → 套用為主表篩選**：by-signal 績效列（已按勝率降序）變可點，點了把該訊號 toggle 進
  `_state.filter.requiredSignals`（複用 filter-chip 同一路徑）→ 重繪主表 + 捲到結果表；已選顯示 ✓，再點取消。
  列上方加提示文字（`journal_click_hint`）。CSS 補 `.stats-row.clickable` hover/active。

### Why
- 使用者反映 Journal 統計區是英文、看不懂 `unknown`、且希望「點高勝率訊號直接篩出選股」。
- 範圍刻意取輕量（純前端）：勝率沿用既有全史 `stats.json`（不新增近窗）、不做 Top-K preset、不動後端 sector 根因。
- 驗證：`node --check` 過；`/momentum.html` 200；data.json `by_signal`=17 / `by_volume_regime`=99 / 20d fills=16565；
  主表有 4 筆 unknown stage + 1 筆 Unknown sector 可驗 relabel/tooltip。

## [3.40.1] — 2026-05-31 — Weekly REVIEW 回測檢討：drawdown instrumentation + news-digest parser 修復

### Added
- **Rec 9 / TODO-005 — verdict path-aware drawdown surface**：`scripts/build_event_index.py`
  `compute_reality_for_ticker` 新增 `max_runup_pct` / `max_drawdown_pct`（從 decision price
  換算 pct；原 `max_*_since` 是絕對價格不可讀）。deep-dive verdict 物件注入兩欄；
  `_build_industry_rollup` miss 區新增 `avg_miss_drawdown_pct` / `worst_miss_drawdown_pct`。

### Fixed
- **Rec 4 / TODO-008 — news-digest macro_delta parser regression**：null 35% (14/40)。
  audit 14 筆找到 4 種未涵蓋 form（label 後直接 bold 無 separator、`**` 包 label、空格分詞 +
  大小寫、`:` 後 bold number）+ 短 form `Macro Δ`。`news_digest_extractor.py` 把 10-pattern
  ladder 換成單一 tolerant regex（label 變體 + backtick/bold wrapper + 選擇性 :/= +
  IGNORECASE）。null **35% → 2.5%** (14→1)，唯一殘留 2026-04-15 是 v1 protocol 無 delta
  概念之 legit n/a；previously-good 值零 regression。

### Why
- 0531 weekly REVIEW 的 READY items。TODO-005 是 Pattern A/B（non-committal HOLD/CANCEL
  系統性錯過上漲）決策 Rec 的**上線驗收 blocker** — 沒 drawdown 無法分辨「真錯過」vs「避損」。
  surface 後立刻解開負 avg_miss_return 之謎：semis HOLD/CANCEL miss avg_ret **+33.86%** vs
  avg_dd 僅 **-3.26%** → 真錯過，**H1 確認**。負 return bucket 是 BUY-miss 方向混算 artifact。
- **protocol decision threshold（TODO-001/002）本週照紀律不動** — 改 threshold 前須走完
  drawdown 資料 → 下週 REVIEW 重評 → promote-to-ledger 的迴圈，避免盲改誤殺避損 HOLD。
  decision band 位置已查明：`investment/investment_protocol_v5_0.md:851-857`。

## [3.40.0] — 2026-05-31 — AI 辦公室改版：自主多角色協作（取代 3.38 PTY terminal）

### Changed（方向性翻案）
- **砍掉 3.38.0 的 PTY terminal 路線**（`pty_session.py` / `ws.py` / `preflight_smoke.py` / `config/office_claude/`）。原因：(1) raw alt-screen relay 畫面**內建會破碎**且與 `claude 2.1.158` 渲染死綁，CLI 改版即破;(2) **方向錯了** — user 要的是「多角色自動協同工作」，terminal 只是錯誤載體，一個 claude TUI 表達不了 N 角色協作、也沒有結構化把手可編排。

### Added
- **`/office.html` 改成自主多角色協作看板**：輸入任務 → **Lead(claude 主筆) / Critic(gemini 挑戰) / Verifier(codex 佐證)** 三角色 round-robin 自動跑到收斂（全員 done / 輪數 / wall / 預算上限）→ Lead 整理出最終交付物 markdown。純觀察 + 全自動，回合事件以 **SSE** 串流（append-only，重整可 replay）。卡片旁附 **elapsed 計時器**（`claude -p` 一回合常 1-3 分，避免慢回合看起來像當掉）。
- **`scripts/office/orchestrator.py`**：協作迴圈，走 `model_router.run_with_fallback`（每角色固定引擎、引擎掛了才 fallback）→ **沿用 Break News 既有 `claude -p`/`agy --print`/`codex exec` driver + 每模型日預算/cooldown，零新增計費面**。每回合結構化 JSON envelope（summary/detail/concerns/done）。
- **`scripts/office/roles.py`**：3 個通用辦公角色（領域中立，可改 prompt/換引擎）+ 輸出契約。**強制全角色 + 交付物用繁體中文**（claude/codex 預設會跑英文，靠 ENVELOPE_SPEC + COMPOSE_SYSTEM 的 zh-TW 指令統一；改 prompt 後需重啟 server）。
- **`scripts/office/store.py`**：run 生命週期於 `reports/office/<run_id>/`（meta.json + events.jsonl append-only + deliverable.md），單一進行中 run 上限。
- **server routes**：`GET /api/office/{token,runs,run/<id>,run/<id>/stream(SSE)}` + `POST /api/office/{run,run/<id>/stop}`。沿用 token + Origin gate；`run` 有 409 single-active guard。

### Why
- 修正上一版把「手段（terminal）當成目標」。改用既有 programmatic 多 agent 引擎，破碎問題由結構化串流根除；多 CLI 真分歧（不同模型）才是 user 要的協作。
- **計費**：reuse 專案每日已在跑的 `-p` driver + model_router 日預算，**不**引入 3.38 RFC §1 擔心的新計費面；per-run 呼叫數在 UI 顯示。
- 驗證：roles/store/orchestrator import + 迴圈邏輯（stub 引擎：收斂/事件/交付物/spend/合作式 stop）+ 全 HTTP/SSE live test（token gate 403 / run 202 / dup 409 / SSE 全程 replay + end / 交付物 / runs list）全綠。**尚未對真 CLI 跑過端到端**（只用 stub 測編排）。

## [3.39.1] — 2026-05-31 — Calendar LLM Review silent-fail 修復 + agentic protocol claude-only

### Fixed
- **決策日曆「請 LLM 檢討」按下後從 queue 消失、頁面永遠不更新** — 根因是三個缺陷複合：
  1. **stuck cooldown**：claude 撞 Anthropic `529 rate_limit` 後，model_router 記 `cooldown_until`
     **固定 +4h**（`model_router.py:169`），不查實際 quota → 即使額度已恢復，user-clicked protocol
     仍被擋去降級模型。
  2. **gemini 跑不動 agentic prompt**：`pick_model("protocol")` 在 claude cooldown 時降級 gemini
     （`agy --print`），但這些 prompt 吃 project 相對路徑 + Read/Write/Agent 工具 → gemini `find`
     找錯副本、timeout、**沒寫 MD**，subprocess 卻仍 exit `rc=0`。
  3. **缺 artifact 把關**：`PROTOCOL_VALIDATORS` 只有 sector/news → llm_review rc=0 無檔被標 `done`
     → 前端 `loadLatestReview()` 撈不到今日檔，靜默回空狀態（`page-calendar.js`）。

### Changed
- **`dashboard_server.py` `_run()`**：Dashboard agentic protocol（PROTOCOL_PROMPTS，全為 claude-turn）
  dispatch 改 **claude-only**（`proto_model = "claude"`），不再走 `pick_model` 降級 gemini/codex，
  並 **bypass stale cooldown** — user 親手點的昂貴互動請求不該被 4h 啟發式 cooldown（本就不查真 quota）擋。
  真 529 仍由 `note_run` 記錄、由 rc/artifact gate 判 error。**break_news debater 多模型路徑不受影響**。
- **`config/llm_config.json`**：`budgets.claude.daily_max_calls` 200 → **300**。
- **`config/llm_usage.json`**：一次性清掉卡死的 `claude.cooldown_until`（→ null）。

### Added
- **`dashboard_server.py` `PROTOCOL_REQUIRED_ARTIFACTS` gate**：rc=0 + validator pass 後再檢查
  required artifact 存在且 mtime ≥ run start，否則降級 `error`（`llm_review` →
  `reports/decision_review/REVIEW_{today}.md`）。缺檔不再被誤判 done。
- **`Dashboard/page-calendar.js`**：`loadLatestReview(justRan)` — done 後若今日 MD 不存在，
  toast 警告「已完成但無今日輸出（模型異常未產檔）」而非靜默載入舊檔（修 #3 後多走 error 分支，此為雙保險）。

### Why
- 使用者回報「我有額度卻卡住」+「丟進 queue 就消失但頁面不更新」。三缺陷疊加：cooldown 不查真 quota →
  降級到跑不動這些 prompt 的模型 → 沒產出卻 rc=0 → 無 validator 把關 → 靜默 done。claude-only + bypass
  cooldown + artifact gate 三管齊下，根除靜默失敗並讓真失敗顯式報錯。

## [3.38.0] — 2026-05-30 — AI 辦公室 · Claude member v1（Route A — persistent PTY terminal）

### Added
- **新頁 `/office.html`**：drawer 內是真 **xterm.js terminal viewport**，後端純 PTY raw byte relay。`claude` 沒 inline mode（永遠 alt-screen TUI），只有真 terminal emulator 能正確 render — 所以走 viewport 而非 transcript scraper（spec：`docs/office_claude_route_a.md`）。
- **`scripts/office/pty_session.py`**：`PtySession` — 在 `pty.openpty()`+`Popen` 上起互動式 `claude`（**無 `-p`**），sanitized env（pop `CLAUDECODE*`/`CLAUDE_ENV`/`CLAUDE_CODE*` 防 nested）、注入 `CLAUDE_CONFIG_DIR=config/office_claude`（無 MCP，避免啟動卡 MCP auth）、trusted cwd。bounded scrollback（256 KB，reconnect replay）、`write` / `resize`(TIOCSWINSZ) / lifecycle clear·restart·stop、Asia/Taipei 日界 session key rollover。
- **`scripts/office/ws.py`**：純 stdlib 手寫 RFC6455 server（handshake + frame codec + 續傳重組 + thread-safe send），bolt 在既有 `ThreadingHTTPServer` 上，**無新依賴、無 async**。alt-screen 需有序低延遲雙向 bytes，故用 WebSocket 而非 SSE+POST。
- **`config/office_claude/settings.json`**：office 專用精簡 config（無 MCP、default permission mode）。
- **`scripts/office/preflight_smoke.py`**（RFC §3.4）：Gate 1 啟動健檢（PTY 起 claude → 達可輸入 → 確認不卡 trust/MCP/login）；Gate 2 **billing 手動 checklist**（**不** auto-pass）。
- **server 端 office routes**（`dashboard_server.py`）：`GET /api/office/token`（Origin-gated 秘鑰）/ `GET /api/office/status` / `GET /api/office/claude/ws`（WS relay）/ `POST /api/office/claude/{message,resize,lifecycle}`。lazy spawn（首次 attach 才起）。
- 側欄新增 `工具 / OPS` group + `AI 辦公室` nav（zh/en i18n）。

### Security（RFC §3.5）
- 127.0.0.1 bind（既有）+ per-process **session token**（`hmac.compare_digest`）+ **Origin allowlist**。預設**不** `bypassPermissions` — 權限 y/n 由 user 在 terminal pane 內回答。

### Why
- 把 Claude/Codex/Gemini 變成可在 Dashboard 直接互動的「辦公室成員」。v1 刻意只做 Claude member 的 terminal viewport；多行貼上（bracketed paste）、乾淨 transcript parser、Codex/Gemini member 延到 phase 2。
- ⚠️ **計費前提未驗證**（RFC §1）：互動式無 `-p` 走訂閱 flat-rate 是**設計方向**非已證實事實。preflight billing gate 未過不准正式上線；本次只交付程式碼 + smoke harness，**未宣稱 billing 已驗**。
- 驗證：`ws.py` frame round-trip + `PtySession`（cat 替身）lifecycle + 全 HTTP/WS live test（token mint / token gate 403 / origin gate 403 / WS 101 / 雙向 PTY echo / resize / lifecycle）全綠。

## [3.37.0] — 2026-05-30 — 新聞 digest 全面 zh-TW（每日 digest + bridge 傳遞 + 自動翻譯 hook）

### Fixed
- **修補 3.36 缺口**：`bridge.extract_news()` 原本只挑特定欄位組 news item，**沒帶 `*_zh`** → 3.36 的 link_digest 翻譯欄位根本到不了前端（永遠 fallback 英文）。bridge 補上 `bull_case_zh`/`bear_case_zh`/`sector_view_zh`/`macro_view_zh`/`arbiter_reasoning_zh`/`debate_note_zh` → data.json news[] 帶 zh，前端 `_zh || base` 才真正生效。

### Added
- `news/scripts/translate_digest.py` — 翻譯一份 digest 的 deep verdicts body 欄位 → `*_zh`（重用 `link_digest.translate.translate_to_zh`，單次批次 agy call，idempotent）。**CJK-skip**：欄位已是中文就跳過（每日 news protocol 本就輸出中文，只翻英文 straggler），避免浪費 agy。`--date`/explicit path/`--force`，best-effort 非致命。
- `dashboard_server.py` run_protocol：news/flash_text/flash/review 跑完 rc=0 後、bridge 前自動跑 translate_digest（agy localise 新 deep verdict）。

### Why
- 使用者要新聞流全中文。查證：每日 news digest（05-27/28/29）的 bull_case/arbiter **本來就是中文**（news protocol 中文輸出），只有偶發英文 verdict（今日 1 筆）+ link_digest/flash 是英文。所以不是「全部要翻」，而是「補英文 straggler + 確保 zh 欄位流到前端」。
- CJK-skip 讓 server hook 對中文 digest ~0 成本（每日跑跳過全部），只在真有英文時花 1 個 agy call。
- 驗證：bridge 補欄位後 data.json news item 帶 `bull_case_zh`（NVIDIA 卡 → `Vera Rubin 平台強迫資料中心電力進行結構性重寫…`）；今日 digest backfill 6/6 欄；05-29 native-zh → skip 0 翻（不燒 agy）；05-30 idempotent skip；全 py/js syntax 過。

## [3.36.0] — 2026-05-30 — Link Digest zh-TW 在地化（gemini/agy 翻譯）

### Added
- **Link Digest 中文化**：link_digest 的 claude turn 維持英文分析，`build_artifacts.py` 跑一道 **gemini(agy) 翻譯** 把 prose 欄位（bull/bear/sector/macro/arbiter/debate + headline）翻成 zh-TW，存 `*_zh` 進 digest verdict + `bn_*.json` summary。News 頁卡片在 zh 語系時渲染 `_zh`，否則 fallback 英文 base（既有每日 digest 無 `_zh` → 不受影響）。
- `scripts/link_digest/translate.py` — 重用 break-news `run_gemini`，單次批次 JSON in/out 翻譯；env `LINK_DIGEST_TRANSLATE`（預設開）；agy 缺/失敗回 `{}` 非致命（writer 降 rc=2，卡片顯英文）。

### Changed
- `scripts/link_digest/build_artifacts.py`：新增 `build_translations()` + verdict/bn 接 `*_zh`（headline_zh 優先 LLM 提供 > gemini 翻譯 > 原文）。
- `Dashboard/page-news.js`：news 卡 bull/bear/arbiter/debate 改 `_zh || base`（依 `UI.currentLang`）。
- `news/link_digest_protocol.md`：新增 Localisation 段，說明 prose 寫英文、writer 自動翻 zh-TW、MD 語系自選。

### Why
- 使用者反映 link_digest 產物全英文，但系統其他即時新聞（break-news 辯論）本來就是中文。選擇保留英文分析 + gemini 翻譯（而非 claude 直接寫中文）：分析忠於英文來源、翻譯交便宜的 gemini、`_zh` fallback 設計使既有 digest 零影響。
- 驗證：translate.py 實打 agy 回乾淨 zh-TW JSON；build_artifacts mock+真 validator e2e；env gate（關/空輸入）回 `{}`；4 支 JS / py syntax 過。

## [3.35.0] — 2026-05-30 — Link Digest：URL → 讀全文 + 上網找相關 → 判斷 digest（餵 KG/供應鏈）

### Added
- **Link Digest 新功能**：News 頁貼上一條文章 URL → claude turn（`--permission-mode bypassPermissions`，WebFetch+WebSearch 可用）讀全文 + WebSearch 找 3-5 篇相關報導 + 4 視角 inline 辯論 + Arbiter → 同時產 (a) `reports/<DATE>_<HHMM>_link_digest.md` 進報告中心、(b) digest.json verdict 進新聞流、(c) `break_news_logs/bn_*.json` entities+relations 餵 Nexus 知識圖譜 / 供應鏈頁。
- `news/link_digest_protocol.md` — protocol spec：5 步流程 + judgment.json schema + relation rubric（ticker↔ticker 供應鏈 predicate + corroborating_sources）。
- `scripts/link_digest/build_artifacts.py` — deterministic 0-LLM 寫手：judgment.json → append digest.json verdict（驗證安全：既有 DIGEST 檔 bump stage2_count 保持 deep==stage2；無檔則開 REVIEW/INLINE 1-deep）+ 寫 bn_*.json（`support_count=len(corroborating_sources)`，≥2 源 → Nexus Phase-2 directed 供應鏈 edge）+ 跑 validate_digest_output.py + 刷新 tier-1 graph。rc 0/1/2。
- `dashboard_server.py`：註冊 `link_digest`（PROTOCOL_PROMPTS `{url}` + 參數 guard + LOG_DIRS + 900s timeout + `_label_for` 🔗 + `_classify_report` `_link_digest.md`→「連結分析」）。
- `Dashboard/news.html` + `page-news.js`：URL 輸入框 + 「分析連結」button → `triggerProtocol('link_digest',{url})` + URL 驗證 + Enter 觸發 + resume banner 認 link_digest。`i18n.js` zh/en labels。

### Why
- 使用者要能丟一條特定連結，讓 LLM 讀完整文 + 上網交叉佐證後給判斷，且結果要能流進既有報告中心、新聞流與知識圖譜/供應鏈 — 不是另起一套孤立 UI。
- 重用既有 `flash_text` claude-turn pattern（已證明 WebFetch+雙檔寫入可行）+ Nexus Tier-1 ingestion 契約（digest.json + bn_*.json），新功能只寫進既有檔，KG/供應鏈按契約自動撿。
- KG schema 易錯（bn relation 的 `ticker:` 前綴、support_count 閾值）→ 用 deterministic build_artifacts.py 保證 schema（沿用 ic-memo deterministic-writer + validator-gate 文化），LLM 只負責讀/搜/判斷的 prose + judgment.json。
- 巧妙耦合：web-search 廣度直接決定供應鏈 edge — 一條 ticker↔ticker 關係被 ≥2 篇抓到的來源佐證，`support_count≥2` 剛好過 Nexus Phase-2 門檻晉升為 directed edge。

## [3.34.0] — 2026-05-30 — Narrative Pulse 完整退役（generator + route + skill）

### Removed

- **Narrative Pulse feature 整體退役**（接續 3.33.0 的 UI 移除）。觀察期原訂 2026-05-31，
  但 5/30–5/31 為週末、無新市場資料 → 不會再累積 sample（最後 sample 2026-05-29 週五），
  故提前退役：
  - `daily_update.sh`：刪 `step9_narrative()` 函式 + Phase 3 呼叫（不再每日跑 batch_scan）。
  - `dashboard_server.py`：刪 `SCRIPT_PROTOCOLS["narrative_pulse"]` + `/api/narrative-pulse/data`
    + `/api/narrative-pulse/ticker/<T>` 兩個 route handler。
  - 刪 `Dashboard/narrative_pulse.json` + 整個 `skills/narrative-pulse-detector/` skill 目錄
    （batch_scan / pulse / classify_stage / fetch_inputs / render / tests，git 保留歷史）。

### Note / 副作用

- `skills/retail-sector-pulse/scripts/aggregate.py` 的 `load_npd_cache_for` /
  `aggregate_retail_volume` 是 **legacy graceful fallback**（檔案註解標明 "kept as fallback"）。
  NPD cache 消失後它自動回 `{score:None, label:"calm"}` → `mood.html` 每產業「散戶量能」label
  恆顯 `calm`。**主 composite（price + trending polarity + attention）不受影響**。該 fallback
  程式碼留著（無害,glob 空→None）,日後可順手清。

### Why

使用者多次確認 narrative pulse「完全沒參考用處」,且週末不會有新 sample,觀察期提前作結。
generator 本身僅剩 retail 的 legacy fallback 在讀其 cache,而該 fallback 缺 cache 即 graceful,
故可安全整套退役。

## [3.33.0] — 2026-05-30 — 退役 Narrative Pulse UI + 移除散戶視角 + index 產業趨勢 mini

### Changed

- **index.html Zone B「Narrative 焦點」→ 真實「產業趨勢」mini**（`Dashboard/index.html`
  `#industry-mini-strip` + `Dashboard/script.js` `renderIndustryMini`）。舊 strip 連到已
  隱藏的 `radar.html#npd-section`（死連結）、資料是無參考價值的 narrative pulse。新 mini
  讀 `data.industry_trend`（V3.29.0 已在 data.json 的真實 finviz trailing perf），顯領漲
  前 3 + 領跌前 2（`perf_1w`），連到 radar.html。移除原 index 內 fetch
  `/api/narrative-pulse/data` 的 inline IIFE。

### Removed (UI only)

- **Narrative Pulse radar UI 全清**：`radar.html` 刪 `#npd-section`；`page-radar.js` 刪整個
  NPD self-contained IIFE（`NPD_RADAR_ENABLED` 那塊死碼，V3.29.0 已停用）。
- **散戶視角 Sector Pulse 從 radar 移除**：`radar.html` 刪 `#radar-retail-sector-pulse`；
  `page-radar.js` 刪 `renderRetailSectorPulse` + `renderMarketWideBuzz` + `buildRspCard` +
  `_rspLabelText` / `_rspMetricRow` / `_rspPolarityBar` + render 呼叫 + `retail_sector_pulse`
  tooltip entry。**`mood.html` 不受影響**（page-mood.js 自帶 `_rsp*` 副本），散戶視角由
  mood.html 接手。

### 不動（backend / 觀察期保留）

- `daily_update.sh` `batch_scan.py` generator、`dashboard_server.py` `/api/narrative-pulse/*`
  route、`narrative_pulse.json` 全留 —— narrative 觀察期到 2026-05-31，不破壞 memory 承諾。
- `bridge.py` 仍餵 `data.tactical.retail_sector_pulse`（mood.html 要用）。

### Why

使用者多次反映 narrative pulse「完全沒參考用處」、且 index 那格連結已死;散戶視角已被
mood.html 完整接手屬冗餘。把死/冗餘 UI 清掉，index 那格改放真實產業趨勢，版面與參考價值
雙升，同時保留 generator 讓觀察期跑完。

## [3.32.0] — 2026-05-30 — Dashboard 4-zone 重構 + AI 裁決卡片漸進揭露 + 今日焦點改造

### Changed
- **index.html 深度重構（9 stack → 4 zone）**：Zone A 指令區（verdict hero + binary + 8-gauge）、Zone B 訊號帶（sentiment / narrative / today-focus 三條薄 strip 合併成 1 個 3-up `#signals-band` grid）、Zone C intel teasers、Zone D action（recent + quick-launch）。實驗性 Structural Watchlist body 收進 `<details class="experimental-collapse">` 預設摺疊。所有 script.js / components.js 依賴的 element ID 原封保留（已逐一 verify）。
- **decisions.html AI 裁決卡片漸進揭露**：V5 估值 / Red Team / 進場觸發條件 block 改 `<details class="dc-collapse">` 預設摺疊，summary 仍露出 verdict chip（fair-value band / NO·MODERATE·STRONG_COUNTER / 條件數）。Model Score 由 `text-4xl` 降為 `text-2xl` 讓 decision / targets / risk 主導。key_risks 上限 4 顆 inline，其餘收進 "+N more"。估值 grid `grid-cols-3` → `grid-cols-1 sm:grid-cols-3` 改善 mobile。卡片高度由 >800px 大幅縮短。
- **index AI verdict hero 密度**：`tv-signal-grid` 卡片 `min-h-[76px]` → `min-h-[60px]`、padding/gap 收緊。
- **今日焦點（Today's Focus）改造保留**：單一 pick → **Top 3**；新增過熱守衛（`rsi_14≥80` / `rsi_zone==overbought` / `Stage 3 top` → amber「過熱」pill + 降透明度），把後段/parabolic 名單標示而非當買點；CTA 由買進暗示的紫色實心 `加入佇列` 改為中性 border `查看分析`；0 候選時改顯 graceful fallback line（不再整塊消失導致 Zone B 塌成 2 欄）。

### Added
- `style.css`：`.dc-collapse` / `.experimental-collapse` summary chevron（旋轉）、`.signals-band > *` 等高 flex。
- `index.html` inline style：`.focus-overheated-pill`。

### Why
- 主控台垂直 sprawl 嚴重、多條薄 strip 互搶注意力，層級弱 → 收斂成 4 個語意分區。
- AI 裁決卡片資訊密度過高（>800px、Model Score 喧賓奪主、pill wrap 亂）→ 漸進揭露讓 risk/decision/targets 先讀，細節按需展開（click handler 早已排除 `summary,details`，drill 不誤觸）。
- 今日焦點本身是真訊號（三軍同向、可重現），但單 pick + 買進式 CTA 會把 NTAP RSI 92 這種末段噴出當進場點 → 改為 Top 3 + 過熱標示 + 中性 CTA，焦點 ≠ 買進訊號。

## [3.31.0] — 2026-05-30 — 個股動向 row 可點 → inline 動能明細 + K線/完整分析

### Added

- **「個股動向」row 可點 → inline 動能明細**（`Dashboard/page-radar.js`
  `renderStockDetail` + `_miniSparkline`；`Dashboard/radar.html` `#sm-detail`）。
  點領漲/走弱 row（或弱中強 chip）→ 區塊下方就地展開該股明細，**純讀既有
  `momentum_screen` row + `history_by_ticker`，零 fetch、零 backend 改動**：
  - 30 日 composite-score **sparkline**（inline SVG polyline，趨勢上綠下紅，免 Chart.js）
  - 均線排列（價 vs MA20/50/200 的 `above_ma%`，綠/紅）
  - RSI-14 + zone、MACD 多/空頭、RS 3m/6m、距 52 週高 `nhp_pct`(+weeks_since_high)
  - signals（綠 chip）/ warnings（紅 chip）
  - 兩個 action：**📈 看即時 K 線**（`selectRadarKline` 開頂部 K線 panel +
    `scrollIntoView`，重用既有 `/api/heatmap/intraday|quote` 雙 polling）、
    **🔬 完整分析**（重用既有 `.analyze-ticker-btn` delegation → `analyzeTicker`）。
  - 再點同檔 / ✕ 收合。新 tooltip：個股 row 沿用 V3.30.0。

### Why

V3.30.0 的個股 row 是靜態的，看到走弱股無法就地深入。所需資料系統其實每日都算好且
已在 `data.json`（含 30 日 score 歷史），K線 panel 與 analyze queue 也都現成 —— 把
row 接上去即可一鍵從「個股走弱」鑽到 K 線 / 完整 protocol，不離開頁面。

## [3.30.0] — 2026-05-30 — 短期雷達加「個股動向」panel（領漲↔走弱 + 弱中強）

### Added

- **radar 新區塊「個股動向」** (`Dashboard/radar.html` `#radar-stock-movers` +
  `Dashboard/page-radar.js` `renderStockMovers`)，接在 V3.29.0 產業趨勢榜下方。補
  產業榜看不到的**個股級強弱分化**。資料源是 **既有但 radar 未用的**
  `data.json.momentum_screen.rows[]`（daily Step 9.7 momentum-monitor 掃描 ~529 檔
  sp500/n100/sox/watchlist，含 Weinstein stage + RS + warnings）。**零 backend 改動**。
  - 對稱兩欄：📈 領漲個股（Stage 2 上升 + RS≥70 / 創新高）↔ 📉 走弱個股
    （Stage 4 下降 / Stage 3 頭部 / WEAK·BEARISH），各取 top 12，走弱按 composite
    score 由低到高（最弱在前）。
  - **「🔥 強勢產業中走弱」highlight strip**：個股走弱但 `sector_rs_rank ≤ 3`
    （所屬 sector 最強前 3）。回應「產業在漲、這幾檔反而在跌」的個股掉隊痛點
    （光通 case）。用 row 內建 `sector_rs_rank` 避免 GICS↔finviz sector 名稱對映。
  - 每列：Weinstein stage chip（S1-S4）+ ticker + sector 縮寫 + warning dots
    （🔻stage4 ✗macd空頭 💀死亡交叉 🪫量縮）+ 主數字（走弱顯 5d 報酬 + 距 52w 高;
    領漲顯 5d + RS）。含 freshness badge + 兩個 tooltip（stock_movers / weak_in_strong）。

### Why

V3.29.0 把 headline 換成真實**產業級**趨勢，但使用者還要看**個股級分散**：強勢產業
裡哪幾檔在走弱。系統其實每日都算好個股 Weinstein stage / RS / Stage4 warning 且已在
`data.json`，只是 radar 沒用 —— 直接 surface 即可。走弱判定刻意用「結構性下降/頭部 OR
composite WEAK·BEARISH」而非「RS<0」（強 SPY 盤多數股會跑輸,RS<0 會誤標 ~80% 宇宙）。

## [3.29.0] — 2026-05-29 — 短期雷達改用真實近期趨勢（領漲↔領跌 + 對稱看多率）

### Changed

- **短期雷達 headline 改為「產業趨勢榜 領漲 ↔ 領跌」** (`Dashboard/radar.html`
  `#radar-industry-board` + `Dashboard/page-radar.js` `renderIndustryBoard`)。資料源
  是 **既有但從未被 radar 採用的** theme-detector cache `industry_rankings.top/bottom`
  ——140 個 finviz 產業的**真實 trailing** `perf_1w/1m/3m`。漲跌對稱、無 keyword
  lock，所以 AI server / Computer Hardware 巔峰與弱勢產業（如光通類）都會浮現。
  含 1週/1月/3月 區間 toggle + 11-sector uptrend strip + cache freshness badge。
- **Theme card 顯示指標由 forward `bullish_breadth_pct` 換成真實 trailing**
  「真實上漲率」(`trailing_breadth_5d_pct` = 成分股近 5 日**實際**上漲比例) +
  「中位漲幅」(`median_trailing_5d_pct`)。可低於 50、可讀作看空。卡片新增
  看多/看空 direction badge（theme-detector 早有 direction，舊版被偏多指標蓋住）。
  預設排序改用 trailing breadth。
- **`bridge.py`** 新增 `load_industry_trend()`，把 theme-detector cache 的
  `industry_rankings` / `sector_uptrend` / `summary` 餵到 `data['industry_trend']`。
- **`skills/short-term-target/scripts/predict.py`** 輸出新增 top-level
  `trailing_return_5d_pct` / `trailing_return_20d_pct`（純價格 trailing，可正可負）。
- **`skills/thematic-screener/scripts/screen.py`** `compute_theme_short_term`
  新增 `trailing` 區塊（`trailing_breadth_5d_pct` / `median_trailing_5d_pct` /
  `median_trailing_20d_pct` / `median_momentum_score`）。保留 `bullish_breadth_pct`
  不再當主顯示。

### Fixed

- **「短期看多率永遠 >50、看不到看空」**：根因是 forward 預測（predict.py shift
  公式 heat 缺值預設 0.5、momentum 結構偏多、news 量級太小翻不動），導致
  `bullish_breadth = count(target>0)/n` 結構性 >50 ——甚至 `direction=bearish`
  的主題（Obesity/GLP-1、Uranium…）也顯示 83/66%。改用真實 trailing 後，弱勢
  主題真的讀作看空。

### Removed (UI only)

- **Narrative Pulse 從 radar UI 隱藏** (`#npd-section` 設 hidden +
  `page-radar.js` `NPD_RADAR_ENABLED=false`，不再 fetch `/api/narrative-pulse`)。
  大多 `insufficient_data`、無參考價值。**generator (`daily_update.sh`
  `batch_scan.py`) 保留** 以維持觀察期到 2026-05-31 的 210-sample 承諾。

### Why

短期雷達原本只反映 forward 預測，三大痛點：narrative pulse 數據死板、看多率
結構性偏多看不到看空、看不出真實近期趨勢（SaaS/CPU/AI server 巔峰、光通走弱）。
修法核心是 surface 系統**早已算好但棄置**的真實 trailing 產業/個股表現，讓頁面
回到「看得出最近真正在漲什麼、跌什麼」。

## [3.28.0] — 2026-05-29 — Market Mood 市場氛圍 page + retail social expansion

### Added

- **New Dashboard page `市場氛圍 / Market Mood`** (`Dashboard/mood.html` +
  `Dashboard/page-mood.js`, nav group `market`). Fixes the complaint that the
  radar Sector Pulse felt purely technical (its 3-lane composite collapsed to
  the 5d price forecast whenever retail social data was null). Layout:
  - **Hero mood band**: a signed −100..+100 composite gauge (Chart.js semicircle
    + deterministic needle, no animation) with headline label, plus three signal
    tiles — Options put/call tilt, VIX+SKEW fear, Fear&Greed (with its 7
    sub-index mini-bars).
  - **Retail dynamics strip**: aggregate bull/bear tilt + hot-ticker chips
    (mention heat / 🚀💥 polarity / engagement bar / sample-post hover) +
    market-wide buzz pills.
  - **Sector mood grid**: reordered so retail polarity 💬 + news tone 📰 read
    first; the 5d technical lane 📈 is greyed (opacity 0.55) and labelled
    "技術面參考".
- **`skills/market-sentiment-analyzer/scripts/mood.py`** — deterministic Market
  Mood producer → `Dashboard/market_mood.json`. Imports sentiment.py's pure
  helpers; adds VIX term structure (`^VIX3M` contango/backwardation), `^SKEW`
  tail-hedging, a robust put/call read (CBOE total → CBOE equity → yfinance
  `^CPC` → **CNN `put_call_options` sub-index proxy** when CBOE is 403-blocked),
  CNN Fear&Greed + 7 sub-indices, and a signed weighted composite that
  re-normalizes weights when a source is missing. Always writes a graceful
  skeleton on total failure (`_partial`).
- **StockTwits social source** (`scripts/break_news/social_sources.py`
  `fetch_stocktwits`): free trending-symbols → per-symbol streams, native
  Bull/Bear tag passed through in meta. Env-gated, 429/403-graceful (additive,
  never breaks the Reddit/HN baseline).

### Changed

- `social_sources.py`: widened `DEFAULT_REDDIT_SUBS` (+StockMarket/Daytrading/
  thetagang), raised `MAX_TOTAL` 80→120 / `MAX_PER_SOURCE` 20→35 /
  `MAX_PER_QUERY` 5→8 — lifts retail-ticker coverage (verified: ~41 → ~110
  posts/day, `trending_tickers.json.tickers[]` 0 → 6+, most sectors now
  non-null `retail_polarity_score`). Aggregation contract (`_social_item` /
  `fetch_social_items`) unchanged → trending_tickers.py / aggregate.py untouched.
- `bridge.py`: `load_market_mood()` (→ `data.market_mood`) + `load_trending_slim()`
  (→ `data.tactical.trending`, slim top-15 projection to bound data.json growth;
  measured +7.7 KB).
- `daily_update.sh`: new non-fatal `step93_market_mood` in the Phase 2B lane.

### Why

- Options market-direction signal was requested but no live options chain / IV is
  available even on the FMP paid plan; the page uses free market-wide proxies
  (CBOE/CNN put-call, VIX term structure, SKEW, Fear&Greed) which are honest and
  refresh daily. The social expansion attacks the root cause of the "no 氛圍感"
  feel — the sentiment lanes were empty for lack of posts.

## [3.27.0] — 2026-05-29 — Pre-Market Pipeline Redesign (FMP 250/min) + Morning Brief

### Added

- `scripts/_shared/fmp_pool.py` — central, **cross-process** rate-governed FMP
  HTTP client. File-locked sliding-window limiter (`fcntl.flock` on a dedicated
  lockfile + JSON timestamp window in `~/.cache_bridge/fmp_pool_window.json`,
  target 220/min under the 250/min paid ceiling). Public API: `get` /
  `get_url` / `fetch_many` (threaded fan-out) / `acquire_slot` (reserve a slot
  without issuing HTTP, for callers that keep their own transport) / `build_url`.
  Lock is held only for the microsecond read-trim-write — never across the
  backoff sleep — so parallel subprocesses + threaded workers share one budget
  without serializing. Tuning: `FMP_TARGET_RPM`, `FMP_POOL_STATE`, `FMP_POOL_LOCK`.
- `scripts/premarket/morning_brief.py` — deterministic (0-LLM) pre-market digest
  → `reports/PREMARKET_<DATE>.md`. 10 sections: regime snapshot, overnight index
  moves, **large-cap movers** (ranks the curated ~131-name `SECTOR_UNIVERSE`
  mega caps, price≥$5 — deliberately not FMP's penny/ETN-heavy biggest-gainers
  feed), sector performance, today's earnings, economic events,
  watchlist overnight gaps, thematic radar, momentum leaders, ≤48h binary risks.
  Reuses warm caches (`Dashboard/data.json`, thematic recs, momentum CSV,
  structural_watchlist, breadth/FTD/top caches); fresh FMP limited to
  index/movers/sector/watchlist quotes (~5-25 small pooled calls). Graceful
  degradation when `FMP_API_KEY` unset (cache sections still render); 36h
  staleness guard flags old caches in the footer. Wired as `daily_update.sh`
  step 9.8 (non-fatal).

### Changed

- Refactored every FMP HTTP path to delegate pacing/429-backoff to `fmp_pool`,
  removing the per-client hard 300ms throttles built for the free tier — public
  signatures and caching unchanged: `sector/lib/fmp_client.py`,
  `skills/_shared/company_context.py`, `skills/_shared/fmp_supplementary.py`,
  `skills/{market-top-detector,ftd-detector,earnings-trade-analyzer}/scripts/fmp_client.py`,
  `skills/momentum-monitor/scripts/technical_core.py`. `scripts/nexus/supply_chain.py`
  gates its calls via `acquire_slot()` (preserves the `(raw, status)` tuple +
  `budget_exhausted` UI) and its per-day call-count cap raised 150 → 2000.
- `daily_update.sh`: Phase 2A FMP lane de-serialized into two parallel chains
  (thematic ∥ momentum) now that the pool enforces the 250/min ceiling centrally;
  `MOMENTUM_SCREEN_WORKERS` 6 → 20, `THEMATIC_PREDICT_WORKERS` 6 → 16.
- `dashboard_server.py`: the heatmap quote fan-out (`_fmp_get_json`) now calls
  `fmp_pool.acquire_slot()` before each request so the always-on server and a
  concurrent `daily_update.sh` run never collectively exceed FMP's limit;
  optional `FMP_DASHBOARD_RPM` soft sub-cap; existing 30-min 429 circuit breaker
  retained as backstop.

### Why

- The pipeline was tuned for the FMP **free** tier (serialized FMP lane, 300ms
  per-request sleeps, 150-call/day budgets, 6 workers) and left the **paid**
  250/min headroom unused while 6+ uncoordinated clients still risked collective
  429s. A single cross-process limiter makes aggressive parallelism safe, and the
  freed headroom funds a richer pre-open morning brief.

## [3.26.1] — 2026-05-28 — Break News Debate Scroll Reset

### Fixed

- `Dashboard/page-break-news.js`: switching to a different Break News item now
  resets the right-side debate thread panel to the top.
- Same-item detail polling keeps the current scroll position, so reading an
  active debate is not interrupted by the 5s refresh loop.

### Why

- The thread panel is a persistent scroll container. Re-rendering a different
  item replaced the content but inherited the previous item's `scrollTop`,
  making the next debate appear midway through the conversation.

## [3.26.0] — 2026-05-27 — Reports Center 投資報告中心

### Added

- New Dashboard page `/reports.html` — read-only browser over `reports/*.md`
  (251 files spanning IC memo, deep_dive, earnings, sector, news_digest,
  news_flash, pre_earnings, weekly, theme, sentiment, valuation, others).
- `dashboard_server.py`:
  - `GET /api/reports` — classified list with date/ticker/type/size, 60s
    in-memory cache invalidated by `reports/` mtime change.
  - `GET /api/reports/view/<filename>` — raw markdown serve, ASCII whitelist
    regex + traversal guard (blocks `..`, `/`, non-ASCII).
- `Dashboard/page-reports.js`: master-detail UI (search + type tabs + list →
  marked.js render + TOC + URL hash sync). IC-memo-specific post-processing:
  - Final verdict badge (BUY/HOLD/SELL/CANCEL → green/yellow/red/grey).
  - 🔒 `decision_lock` chip with tooltip explaining the 11-field SHA256 hash.
  - Degraded-sections yellow banner if footer flag present.
  - Summary card extracts YAML-ish header (Date / Live Spot / Analysis Price /
    Market Cap / Sector).
- `Dashboard/reports.html` — sidebar + master-detail layout, marked.js CDN.
- `Dashboard/style.css` — `report-list-item`, `report-type-tab`,
  `report-verdict-badge`, `report-decision-lock`, `report-degraded-banner`,
  `report-prose` typography (dark/light theme aware).
- `Dashboard/utils.js` NAV_ITEMS: new `reports` entry in `portfolio` group
  (icon `file-text`). i18n.js `zh.nav.reports` / `en.nav.reports`.

### Why

- IC memo writer (V3.25.0) produces 12-section MD reports but nothing in the
  Dashboard surfaced them — users had to grep `reports/` from the shell.
- Reports center makes the full output catalogue (251 MD) browsable in one
  place without changing any skill / protocol behavior. Pure viewer layer.
- Read-only by design: no edit, no delete, no regeneration. Same deterministic
  discipline as IC memo writer itself. Decision-lock hash verification stays
  with `validate_ic_memo.py` — this page only displays the lock badge.

## [3.25.10] — 2026-05-27 — Daily Update Hybrid Parallelism

### Changed

- `daily_update.sh`: Phase 1 now runs breadth, FTD, market-top, and FRED in
  parallel, then joins before `bridge.py`.
- Post-bridge work now uses a hybrid layout: FMP-heavy tasks stay serialized
  (`5.5 → 6 → 9.6 → 9.7`) while structural watchlist, Nexus, and trending
  discovery run in a parallel non-FMP lane.
- Added background-job logging helpers so parallel steps write isolated temp
  logs, dump them in stable order after `wait`, and report elapsed seconds per
  background job.
- Added daily momentum screen step `9.7` over the full momentum universe with
  `MOMENTUM_SCREEN_WORKERS` defaulting to `6`.
- Added a final lightweight `bridge.py` refresh so `Dashboard/data.json`
  includes fresh narrative, retail sector pulse, and momentum screen output
  from the same run.
- `skills/thematic-screener/scripts/screen.py`: added `--predict-workers`
  bounded fanout for per-ticker `predict.py` subprocesses. `daily_update.sh`
  uses `THEMATIC_PREDICT_WORKERS=6` by default.
- Live timing adjustment: Step 6 thematic refresh and Step 9.7 full momentum
  screen remain daily defaults. Operators can temporarily disable them with
  `DAILY_RUN_THEMATIC=0` / `DAILY_RUN_MOMENTUM_SCREEN=0`; `DAILY_FORCE_THEMATIC=1`
  still forces a same-day rerun when today's recommendation file exists.

### Why

- Keeps FMP usage below the 250 calls/minute ceiling by avoiding concurrent
  FMP-heavy scripts and reducing momentum screen worker burst risk.
- Cuts the daily update critical path without making stdout unreadable or
  weakening the existing fatal/non-fatal step boundaries.
- The first live run showed thematic screener itself can take ~16 minutes on
  a cold path. The prediction phase was purely sequential across ~239 tickers;
  bounded fanout keeps the daily signal while reducing wall-clock time without
  parallelizing the FMP-heavy enrichment phase.

## [3.25.9] — 2026-05-27 — Momentum 3D Volume Window

### Added

- `skills/momentum-monitor/scripts/momentum.py` (`_compute_dry_up_spike`):
  two new fields under the `volume_pattern` block — `avg_3d_vs_20d`
  (last-3-day avg volume / 20D avg, both excluding today) and
  `vol_3d_state` ∈ `{"expanding","neutral","drying_up"}`. Thresholds
  mirror the existing dry-up cutoff (0.75) and `volume_expansion`
  signal trigger (1.3). Schema bumped `v2.2 → v2.3` (cache invalidator
  in `_load_cache` updated; old caches refresh on next run).
- `skills/momentum-monitor/scripts/screen.py`: 2 appended CSV columns
  (`vol_3d_vs_20d`, `vol_3d_state`). State is a string passthrough.
- `bridge.py`: surfaces both fields into
  `data.json.momentum_screen.rows[]`. Legacy CSVs predating V3.25.9 get
  `None` for both — Dashboard renders the subscript area empty.
- `Dashboard/page-momentum.js`: new `_vol3dSubHTML(r)` helper renders a
  two-line subscript beneath the today × ratio in every vol-cell —
  `3D 1.32×` (dim) then a small colored state pill (`放量`/`中性`/`量縮`).
  `openVolumePopup()` also gains a "3D 均量 / 20D" row inside the modal
  so the click-through detail panel stays in sync.
- `Dashboard/momentum.html` (inline `<style>`): `.vol-3d` + `.vol-3d-state`
  rules (smaller font, dim base color, state-specific colors).
- `Dashboard/i18n.js`: 4 new keys per locale — `vol_3d_state_expanding`
  / `vol_3d_state_neutral` / `vol_3d_state_drying_up` /
  `vol_modal_3d_ratio`. `col_volume_tip` body extended with the 3D
  sub-line rules so users discover the indicator via header hover.

### Why

- User asked for a quick scan of "**最近 3 天是量縮或放量**" (last 3 days
  volume contraction vs expansion) without clicking into the per-ticker
  modal. The existing 量比 column only shows today vs 20D, which flips
  around on intraday noise; the 5D average already computed inside
  `_compute_dry_up_spike` is too smoothed for "recent" reading. 3D sits
  in the middle and filters the single-day jumps while still tracking
  multi-day pressure.
- Computation reuses the same look-ahead-safe slicing pattern
  (`iloc[-4:-1]`) and zero new data fetch — every consumer already has
  enough OHLCV history (1y default).
- Subscript placement (rather than a new column) keeps Tech tab at 12
  columns so the table doesn't widen.

## [3.25.8] — 2026-05-27 — IC Memo F-8 §1 Dedup

### Fixed

- `skills/ic-memo-writer/scripts/validate_ic_memo.py`: §1 entry-range F-8
  check moved out of the per-key for-loop so it fires exactly once across
  both `entry_aggressive` and `entry_conservative` rather than emitting
  duplicate findings. `__any_entry_set__` guard preserves the
  "don't fire when both keys are null" semantics.
- `skills/ic-memo-writer/tests/test_validator.py`: new
  `test_md_entry_range_sec1_finding_not_duplicated` asserts exactly one
  §1 F-8 finding when both entry keys are non-null and §1 row is broken.
  60 tests total now pass.

### Why

Identified during V3.25.7 code review. Cosmetic-tier (didn't affect rc
ladder or correctness) but emitted noise in validator output. No
LOCK_FIELDS or `compute_decision_lock` change → committee
`decision_lock_hash` invariance preserved.

## [3.25.7] — 2026-05-27 — IC Memo Validator Narrowing

### Fixed

- `skills/ic-memo-writer/scripts/validate_ic_memo.py`: narrowed D-6 raw
  structural-shift JSON detection to the §7 block and D-7 dead
  consensus/differentiated header detection to the §10 block. This avoids
  false positives from appendix examples, quoted text, or unrelated prose
  elsewhere in a memo.
- D-6 now catches both JSON-style `"tier"` and Python-dict-style `'tier'`
  raw dumps inside §7.
- `skills/ic-memo-writer/scripts/build_fact_pack.py`: logs when IC Memo
  falls back to shared FMP peers because no local roster exists.

### Why

The V3.25.4 quality checks were correct but too broad: full-text regexes are
good at catching regressions, but also good at catching unrelated examples.
Section-scoped checks preserve the guardrail without creating validator noise.

## [3.25.6] — 2026-05-27 — Column tooltips switched to styled card UI

### Changed

- `Dashboard/momentum.html`: every column header that previously bound a
  native `title="..."` attribute now carries `data-col-tip="<key>"`
  instead. Added inline `<style>` rules for `.mpt-col` (matching the
  existing `.mpt-preset` / `.mpt-signal` cards) and `.mpt-body`
  (white-space: pre-line so `\n` in i18n strings renders as breaks).
- `Dashboard/page-momentum.js`: new `_renderColTip(el)` resolves the
  `data-col-tip` key to `col_<key>` + `col_<key>_tip` i18n entries and
  hands HTML to the existing `showTip()` dispatcher. `SELECTOR` extended
  to include `[data-col-tip]`. Removed the old `setTitle` binding block
  — native title and the styled card were both firing on slow hovers,
  which looked broken.

### Why

- User explicitly asked the column tooltips to match the sector page's
  GOOGL-style tooltip (white card, rounded corners, structured layout) —
  not the OS native black tooltip. The styled card already exists in
  `#mom-pill-tooltip` for signal / preset hover; this PR just wires the
  column headers into the same component instead of building a parallel
  tooltip system.

## [3.25.5] — 2026-05-27 — Momentum column tooltips + i18n + full PE coverage

### Added

- `Dashboard/i18n.js`: 4 new Fund-tab column labels (`col_ps`, `col_gm`,
  `col_revyoy`, `col_r5d`) in both zh and en — previously hardcoded English
  in the HTML. Plus 9 new tooltip keys (`col_pe_tip`, `col_score_tip`,
  `col_rank_score_tip`, `col_volume_tip`, `col_short_tip`, `col_ps_tip`,
  `col_gm_tip`, `col_revyoy_tip`, `col_r5d_tip`) covering both lenses.
  Each tooltip uses the multi-line `\n` convention already established by
  `col_macd_tip`.
- `Dashboard/page-momentum.js`: applyLanguage now binds the 4 new Fund-tab
  `<th>` text labels and sets a `title="..."` attribute on every annotated
  header via a small `setTitle` helper. Browser renders native multi-line
  tooltips on hover — same inline-tooltip pattern the sector page uses on
  its valuation cells (see `page-sector.js` heatmap row tooltips, lines
  1295-1297). No new tooltip component or popup hydration needed.

### Fixed

- `scripts/backfill_heatmap_pe.py` first-pass run leaves ~250/517 tickers
  unfilled because of FMP transient errors / rate-limit hits under
  15-worker parallelism (the same alphabetic cluster — EQR…EXC for
  example — kept dropping out). Added a sequential second-pass workflow
  (see SESSION_NOTES; codified as `/tmp/seq_pe.py` template) that walks
  the still-missing list with 80ms pacing and `timeout=20`. Backfill is
  now 100% (`517/517` in heatmap.json, `515/528` in data.json — the
  small gap reflects ~13 tickers genuinely missing TTM PE from FMP, e.g.
  negative-earnings names). MU specifically now reports `pe=41.79`.

### Why

- User reported the Fund tab still showed "本益比" empty for `MU` even
  after V3.25.2's backfill, and that the new fundamentals columns (P/S,
  GM%, Rev YoY, 5D%) had no translation or tooltip explaining what they
  measured. The score / rank_score columns also lacked any in-UI hint of
  how they differ, which kept driving the same follow-up question.
- Tooltip pattern is intentionally lightweight — `title="..."` per
  header, native browser rendering, no JS popup. Matches the sector
  page's existing approach and keeps the momentum page from accumulating
  a third tooltip system (signal-pill + preset-rail + this).

## [3.25.4] — 2026-05-27 — IC Memo MU Data-Gap Patch

### Fixed

- `skills/ic-memo-writer/scripts/build_fact_pack.py` now carries both price
  bases: protocol `analysis_price` and live FMP `live_spot`. The MU memo no
  longer presents a protocol downside percentage next to a different live
  spot without labeling the denominator.
- `skills/ic-memo-writer/scripts/compose.py` renders entry zones from
  list/dict/scalar values via `fmt_price_range()`, fixing MU's
  `["668","692"]` and `["620","650"]` ranges that previously showed as `—`.
- IC Memo fact packs now flatten earnings-cache TTM aliases, derive EPS
  surprise %, alias cash + short-term investments and total equity, and read
  snake_case forward estimates. MU §5-§7 no longer lose populated cache data
  to key-name mismatch.
- MU product segments are split into current DRAM/NAND and legacy
  CNBU/MBU/EBU/SBU tables when segment keys discontinuously change across
  fiscal years.
- §7 structural-shift rendering now emits a compact narrative line instead
  of truncating raw JSON.
- §10 removed dead `Consensus View` / `Differentiated View` placeholders
  because protocol V5.0 does not emit those fields.

### Added

- `skills/ic-memo-writer/peer_rosters.py` — skill-local peer roster override
  for IC Memo only. MU now shows WDC, STX, Samsung Electronics, and SK Hynix
  with role labels, while `_shared.company_context.get_peers()` remains
  unchanged for other project consumers.
- `validate_ic_memo.py` gained MD-level regression checks for price-basis
  labeling, entry range render loss, raw structural-shift JSON fragments, and
  dead §10 headers.
- IC Memo tests now cover the MU regressions: 59 tests pass.

### Why

V3.25.0 proved the deterministic memo layer works, but MU exposed that hash
integrity alone is not enough: a memo can be tamper-proof while still hiding
entry ranges, mixing price denominators, or dropping populated cache fields.
This patch keeps the decision lock untouched and adds output-quality guardrails
around the human-readable layer.

## [3.25.3] — 2026-05-27 — Fund tab color parity with Tech tab

### Changed

- `Dashboard/momentum.html` (inline `<style>`): dropped the emerald
  `.col-fund` cell tint. Once V3.25.2 moved `score` and `signals` out of
  the anchor set, the Fund tab ended up showing alternating tint-by-column
  stripes (col-anchor cells stayed white, col-fund cells were tinted) —
  noisy and broken-looking instead of grouping. The active-tab pill above
  the table is now the only emerald accent on this page; lens identity
  lives in the tab control, not inside the column cells.

## [3.25.2] — 2026-05-27 — Momentum 2-Tab Refinements + P/E Backfill

### Changed

- `Dashboard/momentum.html` + `Dashboard/page-momentum.js`: moved `分數`
  (score battery) and `訊號` (signal pills) out of the anchor set and into
  `col-tech`. New anchor set is `# · ticker · price` only (3 cols). Tech
  view still 12 cols (3 anchor + 9 tech); Fund view tightens to 9 cols
  (3 anchor + 6 fund). Fund tab Count badge updated `11` → `9`. User
  wanted Fund lens to read as pure fundamentals — score and signals are
  technical-momentum constructs, not valuation context.

### Added

- `scripts/backfill_heatmap_pe.py`: one-off helper that re-populates
  P/E TTM + forward P/E + EV/EBITDA for every ticker in
  `Dashboard/heatmap.json` via three FMP calls per ticker
  (`/ratios-ttm`, `/key-metrics-ttm`, `/analyst-estimates`). Out-of-band
  equivalent of `dashboard_server._heatmap_refresh_pe_universe()`; useful
  when the server's once-per-startup warm-up failed or the 24h TTL window
  ran out without a restart. Atomic write back to heatmap.json + reminds
  the caller to re-run `bridge.py`.

### Fixed

- `Dashboard/data.json.momentum_screen.rows[].pe` had been `null` for
  every row because `Dashboard/heatmap.json` (the lookup source in
  `bridge.py:ingest_momentum_screen`) had 0/517 P/E entries filled — the
  in-process `_heatmap_pe_cache` on `dashboard_server` had never
  successfully refreshed. Backfilled 269/517 PE entries (the remaining
  ~half are negative-earnings tickers where FMP correctly returns no
  TTM PE). Fund tab's P/E column now renders real values where
  available.

## [3.25.1] — 2026-05-27 — Momentum Table 2-Tab Column View

### Changed

- `Dashboard/momentum.html`: replaced the boolean `#mom-col-toggle` button
  with a two-tab switcher (`📊 技術面 / Technical` and `💰 基本面 /
  Fundamentals`) styled to mirror the existing preset rail. Each tab carries
  a column-count badge (12 / 11). The `<table>` and `#table-wrap` now both
  carry `data-view="tech|fund"`; CSS gates `.col-tech` and `.col-fund` cells
  off that attribute. Anchor columns (`# · ticker · price · score · signals`)
  always render in both views so a row stays identifiable across lenses.
- `Dashboard/momentum.html` (inline `<style>`): dropped all `data-cols-extra`
  rules + `nth-child` hide rules + `.col-extra` class. New rule pair
  `[data-view="tech"] .col-fund { display: none }` and inverse for
  `.col-tech` is the entire visibility model. `.col-fnd` tint renamed to
  `.col-fund` and now also covers P/E + short-interest cells so the Fund
  lens reads as a unified group. Lag disclaimer (`#mom-fnd-note`) gated to
  `#table-wrap[data-view="fund"]` only.
- `Dashboard/page-momentum.js`: rewrote the toggle handler. Old key
  `momentum_cols_extra` is ignored; new key `momentum_table_view` ∈
  `{tech, fund}` (default `tech`). The handler swaps `data-view` on both
  `#mom-table` and `#table-wrap`, updates the `.active` class on the tab
  buttons, and writes localStorage. `rowHTML(r)` now tags every `<td>` with
  one of `col-anchor` / `col-tech` / `col-fund`; `_fundamentalsCellsHTML`
  emits `col-fund` (the old `col-extra col-fnd` pair is gone).
- `Dashboard/i18n.js`: added `momentum_view_tech` / `momentum_view_fund`
  (zh + en). The `applyLanguage` path in `page-momentum.js` now uses these
  keys instead of hardcoded OFF/ON label strings.

### Why

- After V3.22 added 4 Fundamentals columns (P/S · GM% · Rev YoY · 5D%) the
  "More columns" view became 18 wide and the default view hid the new work
  the user actually wanted to see. The boolean toggle no longer mapped onto
  the way the user reads the table — Tech and Fund are two different lenses,
  not "less / more" of the same lens.
- Class-based view hiding (no `nth-child` indexing) eliminates the
  column-reorder fragility that bit V3.22 (where appending columns at the
  end forced adding new `nth-child` hide rules).
- Anchors duplicated in both tabs preserves row identification — if Fund
  tab only showed P/S + GM% + …, a user couldn't tell which ticker they
  were reading without scrolling back to Tech.

## [3.25.0] — 2026-05-27 — IC Memo Writer (deterministic readable memo)

### Added

- `skills/ic-memo-writer/` — new skill producing 12-section high-readability IC
  Memo MD (`reports/<DATE>_<TICKER>_ic_memo.md`) by reusing existing protocol
  cache (no new analysis, no LLM call in V1.0). Triggers:
  - `ic-memo [TICKER]` — compose memo from existing cache (requires prior `分析 [TICKER]`)
  - `分析 [TICKER] --memo` — protocol hook after Phase 5.5 (non-fatal)
- `skills/ic-memo-writer/scripts/build_fact_pack.py` — aggregates `_shared`
  profile + `earnings-analyst/cache` + `investment/invest_logs/history.json`
  into a single `cache/<T>_<DATE>_fact_pack.json` with SHA256 `decision_lock`
  hash over **11 fields**: `final_decision`, `final_action`,
  `position_size_pct`, `analysis_price`, `fair_value_summary`,
  `scenario_odds`, `watch_conditions`, `key_risks`,
  `red_team_counter_thesis`, `red_team_kill_conditions`, `lane_scores`.
  Floats are `round(x, 4)` before canonicalization to avoid IEEE drift.
- `skills/ic-memo-writer/scripts/compose.py` — deterministic fact_pack → MD
  renderer. Zero LLM calls; `--llm-polish` flag reserved (raises
  `NotImplementedError`). Sections 3/5/6/7 degrade to "資料待補" stubs when
  earnings-analyst cache is missing; §11 verbatim from
  `_protocol_decision_lock.payload`.
- `skills/ic-memo-writer/scripts/validate_ic_memo.py` — integrity validator
  with `rc=0/1/2` ladder. Recomputes `decision_lock` hash from `history.json`
  and from fact_pack payload to detect tampering; validates §11 verbatim,
  §8 weighted_fair_value, Provenance Roster presence, forbidden re-scoring
  phrases, and 12-section header presence. `--no-history-check` for tests.
- `skills/ic-memo-writer/scripts/fetch_peer_descriptor.py` — V1.0 **stub** that
  writes empty `peer_descriptor/<T>.json` with `status: stub_no_llm`. Interface
  preserved for Phase A.5 swap to Haiku 4.5 one-shot batch call.
- `skills/ic-memo-writer/template.md` — 12-section reference skeleton.
- `skills/ic-memo-writer/SKILL.md` — protocol triggers, schema, decision_lock
  spec, rc tiers, deterministic-only declaration.
- `skills/ic-memo-writer/tests/` — 44 tests covering: (a) per-field
  decision_lock breach (all 11 fields parametrized), (b) §11 verbatim mismatch
  fatality, (c) MD-level forbidden phrase / FV mismatch / missing §11 fatals,
  (d) Provenance Roster degraded path, (e) compose determinism via SHA256 of
  rendered MD, (f) NotImplementedError on `--llm-polish`, (g) rc ladder.
  All 44 pass.

### Changed

- `investment/investment_protocol_v5_0.md` — added **Step 7 — IC Memo Hook**
  under PHASE 5 documenting the `--memo` flag behavior, decision_lock fields,
  rc ladder, and non-fatal contract (failure does NOT block Phase 5 done).
- `CLAUDE.md` — added `ic-memo [TICKER]` row to Protocol Triggers table; added
  three IC Memo CLI lines to Ops Shortcuts.

### Why

`分析 [TICKER]` produces an excellent committee decision record but reads like
a trade ticket, not a research memo. Long-form readers want narrative IC Memos
covering business mix, revenue segments, competitive landscape, scenarios, and
explicit fair-value derivation — the same data we already have in caches, just
presented differently. This skill adds the narrative layer without spending a
new LLM call per ticker, and the `decision_lock` SHA256 over 11 fields makes
it provably impossible for the memo composer to silently re-score or alter
the committee's verdict.

## [3.22.0] — 2026-05-27 — Momentum Fundamentals Layer (P/S, GM%, Rev YoY TTM)

### Added

- `skills/_shared/company_context.py`: new `get_quarterly_income(ticker, n=8)`
  helper hitting FMP `/stable/income-statement?period=quarter`. Output cached
  for 7 days at `skills/_shared/cache/quarterly_income/{TICKER}.json`. Used
  by momentum-monitor to derive TTM revenue / gross margin / Revenue YoY.
- `skills/momentum-monitor/scripts/momentum.py`: two new derive blocks under
  schema `v2.2` — `short_term_returns` (1D / 5D % from existing OHLCV) and
  `fundamentals` (P/S TTM, TTM GM%, TTM Rev YoY, TTM revenue USD, lag days).
  Both are None-safe: missing FMP key or paid blocker → fields = None, scan
  still completes. Cache entries pre-dating v2.2 are auto-invalidated.
- `skills/momentum-monitor/scripts/screen.py`: 7 appended CSV columns
  (`return_1d_pct`, `return_5d_pct`, `ps_ttm`, `gm_ttm_pct`, `rev_yoy_ttm_pct`,
  `ttm_revenue_usd`, `fundamentals_lag_days`) + 4 filter flags
  (`--max-ps`, `--min-gm`, `--min-rev-yoy`, `--min-return-5d`) + 2 presets
  (`--preset sales_breakout`, `--preset value_momentum`). Preset bundles
  only fill fields the user left at the argparse default — explicit CLI
  flags always win.
- `skills/momentum-monitor/scripts/prefetch_fundamentals.py`: new helper
  that walks the screener universe (`sp500 + nasdaq100 + sox` ≈ 532 unique
  tickers) and primes the shared 7-day cache. Non-fatal — exits 0 when
  `FMP_API_KEY` is unset so cron pipelines stay green.
- `daily_update.sh`: new Step 9.6 runs `prefetch_fundamentals.py` so the
  next ad-hoc `screen.py` is fully cache-hot. Failures are non-fatal (the
  screener falls back to lazy refetch).
- `Dashboard/momentum.html` + `Dashboard/page-momentum.js`: 4 new
  `col-extra col-fnd` table columns (P/S · GM% · Rev YoY · 5D%), hidden in
  compact mode and tinted as a Fundamentals group. Two new Featured preset
  tabs — `🚀 Sales Breakout` (Stage 2 + RS ≥ 80 + Rev YoY ≥ 15%, no P/S
  cap) and `💎 Value Momentum` (Stage 2 + Score ≥ 65 + P/S ≤ 5 + GM% ≥ 15).
- `Dashboard/i18n.js`: zh / en strings for both new presets plus a
  fundamentals lag disclaimer (`momentum_fnd_lag_note`) rendered under the
  screen table.

### Changed

- `bridge.py`: `_build_row()` now surfaces the 7 new CSV columns into
  `Dashboard/data.json.momentum_screen.rows[]`. Existing CSVs predating
  V3.22 simply pass `None` through `_safe_float()` — Dashboard renders "—"
  until the next screen run.
- `Dashboard/page-momentum.js`: FEATURED_PRESETS reshuffled to
  `[nh_leaders, sales_breakout, value_momentum, vcp_setup, breakout]` so
  the fundamentals-aware entry points get hero-row placement. `dtc_squeeze`
  pushed into Secondary. `_activePresetKey()` extended with maxPs / minGm /
  minRevYoy / minReturn5d numeric checks to disambiguate the two new
  presets from earlier ones.
- `Dashboard/momentum.html`: `<style>` block adds a class-based
  `tbody td.col-extra` hide rule alongside the legacy nth-child rules so
  newly appended columns don't drift the column-index map.

### Why

- Gemini Codex review of the original "P/S 加進動能" idea flagged two
  failure modes: (1) hard P/S caps on a breakout preset would silently
  strip the strongest leaders (NVDA / LLY) right at their thrust moment;
  (2) a naked low-P/S filter is a value trap without a gross-margin floor
  and a non-shrinking revenue check. Sales Breakout deliberately omits a
  P/S cap; Value Momentum stacks `Rev YoY > 0` + `GM% ≥ 15` on top of
  `P/S ≤ 5`. TTM (not single-quarter) figures everywhere to dampen lumpy
  revenue / margin noise.
- Fundamentals are **information-only** in the table — they do *not* feed
  the composite score or `rank_score`. Cross-industry P/S comparisons
  aren't meaningful enough to deserve weight in a momentum signal.
- 7-day cache TTL is the right granularity: quarterly filings move weekly
  at most, and a daily prefetch step (9.6) keeps the universe warm so
  ad-hoc `screen.py` runs are zero-extra-cost on the FMP side.

## [3.21.0] — 2026-05-27 — Break News Hourly Cap + Stale-Backlog Guard

### Changed

- `scripts/break_news/poller.py`: added rolling-1hr admission cap
  (`BREAK_NEWS_HOURLY_CAP=25`) with time-slot pacing (slot = 60/cap = 2.4 min)
  via new `_hourly_slot_capacity()`. Quiet periods accumulate slot tokens for
  catch-up; bursts still bounded by hourly_left. Wired into
  `_auto_budget_limit` as additional binding constraint alongside
  model-call-headroom and DAILY_MAX.
- `scripts/break_news/poller.py`: added freshness gate
  `BREAK_NEWS_BACKFILL_MINUTES=30` — debate candidates whose `published_dt`
  is older than 30 min are dropped from auto-admission and counted under
  `items_gated_backfill`. Raw stream UI feed is unaffected.
- `scripts/break_news/debater.py`: `scan_pending()` now honors
  `BREAK_NEWS_PENDING_MAX_AGE_HOURS=2`. Items older than the cutoff stay in
  `pending_debate` state but are skipped by the auto-loop, preventing
  queue-flood after long idle (e.g. user opens dashboard 10 hr later → no
  auto burst). Added `list_stale_pending()` helper for the UI.
- `scripts/break_news/store.py`: `list_items_by_state()` sort key changed
  from `last_activity_ts` to `fetched_at` so news ordering reflects arrival
  time, not debate activity (debating items no longer float to top).
- `Dashboard/page-break-news.js`: feed list explicitly sorts newest → oldest
  on `fetched_at`. Added "陳舊待辯論 / Stale Backlog" panel that calls
  `/api/break-news/stale-pending` and renders per-item 🔥 Debate button
  hitting the new `/debate-now` endpoint.
- `Dashboard/break-news.html`: added Stale Backlog collapse strip above the
  raw stream panel.

### Added

- `dashboard_server.py`: `GET /api/break-news/stale-pending` returns the
  stale `pending_debate` queue for UI manual triage.
- `dashboard_server.py`: `POST /api/break-news/item/<id>/debate-now` runs
  `debate_item(nid)` synchronously in a background thread, bypassing the
  scan_and_debate loop (which honors max-age). User opt-in budget spend on
  stale backlog.

### Why

V3.20.x burned the Anthropic 5hr quota window: ~106 break-news debates in
~6 hr × ~3 Claude rounds each = ~300+ `claude` CLI subprocess spawns,
plus 3 large protocol runs (`分析 CRWD` + `產業掃描` + `新聞分析`) → 5hr
session cap exhausted. Root cause: no rate limit at the admission stage and
auto-debate-on-startup re-processed every queued backlog item. V3.21 adds
hourly cap + freshness gate + stale-backlog manual-trigger UI to make the
explore layer self-throttling.

---

## [3.20.7] — 2026-05-26 — Momentum Volume Regime Alpha UI

### Added

- `skills/momentum-monitor/scripts/journal.py` now persists `volume_trend`
  and `ratio_20d_bucket` for new journal snapshots, and aggregates
  `by_volume_regime` as `volume_trend × stage × ratio_20d_bucket`.
- `journal.py stats` backfills old journal entries from matching
  `skills/momentum-monitor/cache/screen_*.csv` files at aggregation time, so
  historical samples can be cross-tabbed without rewriting `journal.jsonl`.
- `Dashboard/momentum.html` / `Dashboard/page-momentum.js` add a Journal
  `Volume Regime Alpha` table. It renders only exploratory cells passing
  `n>=5`, `20d win_rate>=55%`, and `20d median>=+2%`.

### Why

Volume direction is regime-dependent: blind score bonuses for expanding or
contracting volume mix accumulation with distribution. The UI now surfaces the
empirical cross-tab evidence in Journal stats while leaving composite score and
screener ranking unchanged.

## [3.20.6] — 2026-05-25 — Narrative Pulse 手動探測歷史持久化

### Added

- `Dashboard/page-radar.js` localStorage-backed probe history
  (`npd_probe_history_v1`, cap 10): 每次手動「探測」成功後寫入
  `{ticker, ts, stage, stage_label_zh}`
- `Dashboard/radar.html` 新增 `#npd-history-bar` chip 列
  (probe-bar 與三欄 ranking 之間)
- `Dashboard/style.css` 新增 `.npd-history-bar` / `.npd-hist-chip` /
  `.npd-hist-dot` / `.npd-hist-ticker` / `.npd-hist-stage` /
  `.npd-hist-age` / `.npd-hist-x` styles（dashed border + stage 色點 +
  hover 橙邊）
- `initNPD()` 啟動時 auto-replay 最新一筆 history（server cache 4h 內 hit
  即時），確保切頁回來不會消失。Chip click 也走同一條 `replayProbe()`

### Fixed

- 手動探測 NOK 後切到別頁再切回來，`#npd-detail-panel` 整段消失：
  原本 `probeTicker()` 結果只寫進 DOM `innerHTML`，page-radar.js IIFE
  在切頁重 mount 時只 fetch rankings，從不去讀 server cache
  (`skills/narrative-pulse-detector/cache/{T}_{date}.json`, TTL 4h)。
  新 history 機制讓 chip + 自動回放補上這條 gap

### Why

User 回報「按了 narrative pulse 搜出 NOK 第四階段，切換其他頁面再回來
就再也找不到」。同時確認 server-side probe 不會因切頁而 abort：
`dashboard_server.py:2926` 的 `subprocess.run()` 在 server thread 跑到底，
client AbortSignal 只 kill client fetch，pulse.py 一定寫 cache 完才結束 →
下次同 ticker 4h 內走 cache 秒回。所以 history chip click / auto-replay
通常 instant，只有 cache miss 才會觸發新一輪 pulse 探測。

## [3.20.5] — 2026-05-25 — Break News 第二位分析師缺席 bug 修復

### Fixed

- `scripts/break_news/prompts.py` `compact_thread_formatter()` 與
  `build_summary_block()` 在讀取已存 comment 的 `agent_role_label` 時
  crash:debater 從 V3.x 起寫入的是 `{en,zh}` dict (見
  `scripts/break_news/debater.py:55-57`),但 prompts 端仍當字串呼叫 `.upper()`
  / `set.add()` → side A (codex) 寫完後,side B (claude) 在組 followup prompt
  時 `AttributeError: 'dict' object has no attribute 'upper'` /
  `TypeError: unhashable type: 'dict'`,例外被 ThreadPoolExecutor 吞掉,
  state 卡在 `debating`,startup sweep 每次 server 重啟把它打回 `pending_debate`
  → 無窮迴圈,thread 永遠只有 c0 (Codex 那一條),Gemini/Claude 那邊 0 條
- 新增 `_comment_label(c, default)` helper:dict label → `en`/`zh` 字串,
  fallback 到 `agent` (model 名),確保 hashable + 可 `.upper()`

### Why

User 回報「最近的即時新聞辯論都沒有第二位分析師的回覆」。檢查
`news/break_news_logs/bn_*.json` 發現 58 筆 single-side-A thread + 多筆
`startup_sweep: reset from debating after Ns` 錯誤紀錄,證實 side B 從未跑到
`store.append_comment()`。Root cause 是 schema drift —— debater 把
`agent_role_label` 從 string 改成 `{en,zh}` dict 後,prompts 端沒同步。

修完後下一輪 debate scan 就會把 58 筆 stuck items 補上 side B 回覆
(同時會多出重複 side A 條目,因為 followup_user_prompt branch 是
`if not thread`,thread 已有 c0 → 進 followup,但 idx=0 還是 codex
→ 多寫一條 c0_round0_codex;非關鍵,human 可手動清。)。

## [3.20.4] — 2026-05-25 — Narrative Pulse UI Redesign

### Changed

- `Dashboard/radar.html` Narrative Pulse 區塊重新排版：
  - Title row 拆出 probe bar (`輸入 ticker → 探測`) 改放獨立一行,header 不再擠成一條
  - 三欄 (後段風險 / 早期機會 / 分配臨近) 從純文字變獨立 mini-card,
    各帶 accent stripe (橘 / 綠 / 紅)、icon、count chip 顯示當前 N 檔
- `Dashboard/page-radar.js` `rowHTML()` 改用 grid 三欄 (ticker chip / stage / ER),
  ticker chip 用 stage 顏色 + `color-mix` 半透明 fill。
  `renderRankings()` empty state 從 `—` 改成 `dot · 目前 0 檔 · ...` 描述句,
  click handler selector 同步改 `.npd-row-v2`。
- `Dashboard/style.css` 新增 `.npd-probe-bar` / `.npd-col` / `.npd-row-v2` /
  `.npd-empty` 規則 (~140 lines),全部走 `var(--text-main)` / `var(--border)`
  變數,light / dark theme 同支援。

### Why

V1.0 NPD 區塊原本三欄全擠在一行 (title + experimental badge + timestamp +
probe input + button + status),空欄只顯示「—」造成大片死空間,單一 TSLA
條目視覺上孤立。改完後三欄各自有獨立邊框 + 數量徽章,空欄改成有意義的
empty state,probe 區拉到獨立一行不再擠 header。Behavior / data shape /
API endpoint 全部未動,純 markup + 樣式。

### Files Touched

- `Dashboard/radar.html` — section 142-198 重排
- `Dashboard/page-radar.js` — `rowHTML` + `renderRankings` + click selector
- `Dashboard/style.css` — append NPD section (~140 lines)

---

## [3.20.3] — 2026-05-25 — Retail Sector Pulse: Truth Social Filter + Wire-News Polarity

### Fixed (post-V3.20.2 ship validation)

V3.20.2 live run showed polarity = 0 for all sectors even with 3 qualified
tickers (NVDA, RDDT, DJT). Diagnosis showed two root causes:

1. **Lexicon偏 WSB slang (moon/puts/diamond hands),但 RSS feed 抓到的多是
   wire-news 風格 (surge/plunge/dip/downside)**. The lexicon had 0 hits
   on 49 live posts. Sample post `"Is the recent dip in Reddit (RDDT) a
   great buying opportunity, or is there more downside ahead?"` should
   register both `buying opportunity` (bull) and `downside` (bear) but
   neither was in v1.2 lexicon.
2. **DJT qualified entirely from Trump Truth Social signatures**. Posts
   like `"Mike: Thank you for your nice words on Fox. — President DJT"`
   are pure political endorsements that don't reflect any market view,
   but the `DJT` ticker was extracted from the signature, falsely
   counting Trump's political activity as DJT (Trump Media) stock signal.

### Fix #1: Lexicon v1.2 → v1.3 wire-news vocabulary

- Bull adds (~37): `buying opportunity` / `upside potential` /
  `extends gains` / `outperforms` / `leads gains` / `broad-based rally` /
  `surge(s|d|ing)` / `soar(s|ed|ing)` / `jumps` / `climbs` / `advances` /
  `rebounds` / `recovers` / `gain(s|ed)` / `rises` / `rose`
- Bear adds (~43): `downside (risk)` / `to the downside` / `extends losses` /
  `underperforms` / `leads losses` / `broad-based selloff` /
  `headwind(s)` / `plunge(s|d|ing)` / `tumble(s|d|ing)` /
  `slump(s|ed|ing)` / `slides` / `slid` / `slip(ping|ped)` /
  `drops` / `dropped` / `declines` / `declined` / `declining` /
  `falls` / `fell` / `falling` / `sinks` / `sank` / `retreats` /
  `weakens` / `weakened`

Total polarity terms: 320 → 340.

### Fix #2: Truth Social relevance filter + DJT signature strip

New `truth_social_filter` block in lexicon yaml:

```yaml
truth_social_filter:
  enabled: true
  signature_patterns:                   # regex stripped before extraction
    - "(?i)\\s*[—\\-–]?\\s*President\\s+DJT\\s*$"
    - "(?i)\\s*[—\\-–]\\s*DJT\\s*$"
    - "(?i)RT\\s+@\\s*realDonaldTrump"
  extra_relevance_keywords:             # 38 economic/market keywords
    - "economy", "tariff", "fed", "powell", "stock", "earnings",
      "tax", "trade", "jobs", "wages", "boeing", "oil", "gold", ...
  drop_if_irrelevant: true              # drop post if no relevance hit
```

`trending_tickers.py` new `apply_truth_social_filter(post, lex)` called
between fetch and process_post. Two stages:
1. Strip "President DJT" / "RT @ realDonaldTrump" signatures from text
2. Relevance check — post text must hit ≥1 economic/macro/market keyword
   (from `extra_relevance_keywords` OR `market_wide.topic_lexicon`).
   Drop entire post if no hit.

Other source platforms (Reddit / HN / Bluesky / Trends) unchanged.

### Why "filter, not block"

Trump's economic / tariff / Fed / market posts carry real market-moving
weight and SHOULD inform retail sentiment. Pure political endorsements
("Mike thanks for your support") should not. The relevance filter
keeps the economic signal while dropping noise.

### Live verification (V3.20.2 → V3.20.3)

| Metric | V3.20.2 | V3.20.3 |
|---|---:|---:|
| Posts ingested | 49 | 41 |
| `truth_social_dropped` (new) | — | **7** |
| Qualified tickers | 3 | 2 |
| DJT false-positive | 4 mentions (all from signature) | **0** ✓ |
| RDDT post matched terms | `[]` | **`["great buying opportunity", "downside"]`** ✓ |

RDDT polarity still 0.0 because the single post hit both bull AND bear
terms (mathematically: `(1-1)/(1+1+1) = 0`). This is honest — author is
asking whether it's a buying opportunity OR more downside. Lexicon now
correctly reflects that ambiguity instead of falsely returning 0-hit.

### Test results

- `tests/test_aggregate.py` → 22 OK
- `tests/test_trending_tickers.py` → 39 OK (+5 V3.20.3 tests):
  political post dropped, economic post kept w/ signature stripped,
  signature strip prevents DJT false-positive, $DJT in body still
  extracts, wire-news polarity (surge/plunge/buying opportunity) fires

## [3.20.2] — 2026-05-25 — Retail Sector Pulse: Dual-Gate + Retail Override + Broad ETF Routing

### Fixed (Codex post-V3.20.1 review)

- **Lexicon polluted by English-word tickers.** V3.20.1 live run showed
  `LONG`/`CALLS`/`EARLY`/`GPU`/`NYSE`/`TRUMP`/`NIFTY`/`RINOS`/`FOSS`
  matching as tickers and crowding the `low_confidence[]` list while real
  tickers (NVDA, DJT, RDDT) were demoted by a uniform threshold. Added
  these to `ticker_blocklist` (now 50 entries).
- **Single uniform threshold demoted real tickers.** Per Codex feedback,
  splitting `ticker_inclusion` into `known_sector` (1 mention, 1.0
  engagement) vs `unknown_sector` (3 mentions, 8.0 engagement). NVDA
  single Reddit mention now qualifies via known-sector gate; unknown
  ticker SXC stays in `low_confidence` until it crosses the strict gate.
  Backward-compat shim handles legacy single-gate yaml.
- **Retail meme tickers not in `SECTOR_UNIVERSE` dropped silently.** New
  `retail_only_sector_overrides` block in `retail_lexicon.yaml` maps
  DJT / GME / AMC / HOOD / COIN / SOFI / SMCI / RDDT / ARM / MU / MARA /
  RIOT / OXY / MRNA to their natural GICS sector — **without** modifying
  `skills/_shared/company_context.py::SECTOR_UNIVERSE` (which other
  skills like narrative-pulse-detector read; we don't want pollution
  spreading across the codebase).
- **Broad-market ETFs polluted sector rollups.** `SPY` / `QQQ` / `IWM` /
  `DIA` / `VOO` / `VTI` / `TLT` / `VXX` / `UVXY` / `SQQQ` / `TQQQ` /
  `SPXS` / `SPXL` are broad indices, not single-sector. They now route
  to `market_wide_buzz` under `broad_etf` + `market_direction` topics
  instead of any individual sector.
- **Dashboard polarity row** now shows `· n=X` mention-count warning
  with dimmed text when total retail mentions for a sector card is
  below 5 — flags thin samples without burying them.

### Lexicon v1.2

- 50 blocklist entries (was 41 in v1.1)
- 137 cashtag-only tickers (unchanged)
- 12 high-liquidity naked whitelist (unchanged)
- 15 retail-only sector override tickers (new)
- 13 broad-market ETFs (new)
- bull/bear/macro term counts unchanged
- `lexicon_version: v1.1 → v1.2`

### Live verification (V3.20.1 → V3.20.2)

| Metric | V3.20.1 | V3.20.2 |
|---|---:|---:|
| Posts ingested | 44 | 49 |
| Qualified tickers | 0 | **3** (DJT, RDDT, NVDA) |
| Low-confidence | 14 (含 LONG/CALLS/NYSE/TRUMP 假) | 2 (純 unknown sector real ticker) |
| Sectors with retail data | 0 | **2** (Technology + Cons Disc) |

### Test Results

- `tests/test_aggregate.py` → 22 OK (unchanged)
- `tests/test_trending_tickers.py` → 34 OK (27 V3.20.1 + 7 new V3.20.2):
  blocklist verification, known-sector relaxed gate, unknown-sector
  strict gate, retail override (DJT → Cons Disc), broad ETF routing to
  market_wide, end-to-end SPY → market_direction topic, legacy
  single-gate backward compat

## [3.20.1] — 2026-05-25 — Retail Sector Pulse: Polarity-First 3-Lane

### Added

- **`skills/retail-sector-pulse/scripts/trending_tickers.py`** — new entry point
  consuming Reddit / HN / Bluesky / Google Trends via existing
  `scripts/break_news/social_sources.py`. Outputs
  `Dashboard/trending_tickers.json` with per-ticker engagement-weighted
  polarity, per-sector rollup, low-confidence list, and market-wide buzz
  bucket. 27 unit tests cover ticker disambiguation, span-masked polarity,
  engagement scoring, thresholds, sector rollup, market-wide bucketing,
  and lexicon-version propagation.
- **`config/retail_lexicon.yaml`** new file (~400 polarity terms + ~190 ticker
  rules). Bull (120) + bear (138) terms cover English / Chinese / WSB /
  PTT slang. Curated by Gemini suggestions filtered by Codex (skipped
  high-noise emoji 🔥💪🤡💩, ambiguous META/COIN naked whitelist, and
  substring-risk qt/qe). Cashtag-only list (137 tickers) and blocklist
  (41 acronyms) prevent AI/ON/X/IT/FOMO/YOLO false positives.
- **V3.20.1 polarity bar** on each radar sector card — visual −1 to +1
  indicator anchored at center. Green right, red left, stone-grey when
  within ±0.20. Tooltip on card hover shows `signal_lanes` breakdown
  (price/polarity/attention normalized values) plus top 3 sample posts
  for audit.
- **Market-wide buzz strip** at top of Sector Pulse section. Renders
  topic pills (`Fed +0.45`, `recession -0.55`, etc.) for posts that
  don't map to a single sector (no ticker, or 6+ tickers = broad sweep).
- **`daily_update.sh` Step 9.4** runs `trending_tickers.py` before
  Step 9.5 (`aggregate.py`). Step 9.5 reads
  `Dashboard/trending_tickers.json` automatically.

### Changed

- **`config/weights.yaml` v1.0 → v1.1** — composite formula refactored
  from 2-lane (news 0.4 / predicted 0.4 / retail_volume 0.2) to **3-lane
  polarity-first**: `price_5d_norm` (0.30) + `retail_polarity_signed`
  (0.50) + `retail_attention_signed` (0.20). News sentiment is now a
  secondary display attribute on the card but **does not enter the
  composite formula**. Reasoning: user wants to know what a retail
  investor would conclude from public info; news is context, retail
  polarity is the primary signal.
- **`scripts/aggregate.py`** — new `load_trending_tickers()` +
  `aggregate_retail_from_trending()` replace the old NPD-cache-based
  retail layer. New `make_framing_v2()` 3-lane framing. Output JSON
  schema bumped (`version: 1.1`) with new fields: `retail_polarity_score`,
  `retail_engagement_score`, `retail_top_tickers`, `sample_posts`,
  `matched_terms_summary`, `signal_lanes`. Top-level adds `market_wide_buzz`
  and `trending_meta`.
- **`Dashboard/page-radar.js`** — `buildRspCard()` renders new schema.
  Updated `RADAR_TERMS.retail_sector_pulse` tooltip to document 3-lane
  composite formula and polarity-first philosophy.
- **`Dashboard/radar.html`** — new `#rsp-market-wide-strip` element above
  the sector grid.

### Codex review fixes baked in

1. **Ticker disambiguation must be hard**:
   - `$NVDA` cashtag always wins
   - Naked NVDA / TSLA / etc. only when in `high_liquidity_naked_whitelist`
     (NVDA / TSLA / AAPL / AMD / SMCI / PLTR / MSFT / AMZN / GOOG / GOOGL /
     NFLX / BABA)
   - Short / English-word tickers (ON / IT / AI / X / BE / OK / NO / IF /
     PM / TV / etc.) forced to cashtag-only
   - Blocklist (USA / IPO / FED / CPI / ATH / FOMO / YOLO / FUD / DCA /
     GAAP / FCF / ROIC / ROE / NAV / ESG / CAGR / DCF / EPS / PE / PEG /
     YOY / QOQ / EBITDA / ECB / BOJ / OPEC / EIA / PMI / ISM / NFP / PBOC)
     rejected even with `$`
2. **Span-masked polarity matching** — long phrases sorted DESC by length;
   matched span consumed so `short squeeze` does not also fire `short`,
   `pump and dump` does not fire `pump` + `dump`. Word-boundary check for
   ASCII alphanumeric terms.
3. **Inclusion thresholds** prevent long-tail garbage — ticker must have
   `>= 2 mentions` AND `engagement_score >= 5.0` to qualify; sub-threshold
   tickers go to `low_confidence[]` for audit, not into sector rollup.
4. **Market-wide bucket** captures sectorless macro posts (no ticker or
   `> 5` ticker count) classified by 9-topic lexicon
   (fed / inflation / recession / jobs / trade / ai_capex / geopolitics /
   volatility / market_direction).
5. **軋多 corrected to bear** — was wrongly listed under bull in v1.0
   draft; is actually a long squeeze (bears killing longs).

### Why

- V3.20.0 retail layer was just `retail_mention_multiplier` (cashtag count)
  from NPD cache — volume only, no direction. User cannot tell from "Reddit
  NVDA 4.1x" whether retail is buying or selling. This patch infers
  direction from post-level keyword polarity (bull vs bear terms in title
  + summary), engagement-weighted across all posts mentioning each ticker.

### Schema Breaking Change

- `Dashboard/retail_sector_pulse.json` `version: 1.0 → 1.1`
- Per-sector fields removed: `retail_volume_score`, `retail_top_ticker`,
  `retail_top_multiplier`
- Per-sector fields added: `retail_polarity_score`, `retail_engagement_score`,
  `retail_top_tickers[]` (list with polarity + engagement per ticker),
  `sample_posts[]`, `matched_terms_summary{}`, `signal_lanes{}` (3 normalized
  lane values for audit)

### Test Results

- `python3 skills/retail-sector-pulse/tests/test_aggregate.py` → 22 OK
- `python3 skills/retail-sector-pulse/tests/test_trending_tickers.py` → 27 OK

## [3.20.0] — 2026-05-25 — Retail Sector Pulse: 散戶視角分產業 sentiment + 5d direction

### Added

- **New skill `skills/retail-sector-pulse/`** — daily aggregator that produces
  per-sector (11 GICS) retail-perspective sentiment cards for the Tactical
  Opportunity Radar. Inputs are all retail-accessible: deep-digest news
  verdicts (`net_impact_score` + `affected_sectors[]`), narrative-pulse cache
  `retail_mention_multiplier` (Reddit + HN cashtag volume), and
  `short-term-target/predict.py` 5d direction forecast. No new LLM calls.
- **`scripts/aggregate.py`** — main entry. CLI: `--output`, `--skip-predict`,
  `--sector-override Sector=insufficient_data` (for UI testing without
  touching real cache). Per-sector record carries `news_sentiment_score`
  (weighted 72h half-life decay), `retail_volume_score` (median NPD
  multiplier across `SECTOR_TOP_5`), `predicted_5d_median_pct` +
  `predicted_5d_bullish_breadth_pct`, plus rule-based `framing_zh` /
  `framing_en` one-liner.
- **`config/weights.yaml`** — declarative formulas: composite =
  0.4×news_norm + 0.4×predicted_norm + 0.2×retail_signed. 5-tier bucket
  labels for each signal + composite. `sector_aliases` map normalizes
  messy digest sector strings (`"Real Estate"` / `"Tech"` /
  `"Semiconductors"` / `"Defense"` → canonical
  `SECTOR_UNIVERSE` key). All user-tunable in yaml; bump `weights_version`
  after edits.
- **21 unit tests** in `tests/test_aggregate.py` — bucket boundaries,
  alias normalization, weighted mean decay, composite formula
  traceability, partial-signal re-normalization, framing template
  (align / diverge / partial).
- **`Dashboard/retail_sector_pulse.json`** — output artifact (auto-gen
  by Step 9.5).
- **`Dashboard/radar.html`** — new `<section id="radar-retail-sector-pulse">`
  above Narrative Pulse, hidden until data loads.
- **`Dashboard/page-radar.js`** — `renderRetailSectorPulse()` renders an
  11-card 4-column responsive grid. Each card shows sector + proxy ETF +
  composite pill, 3-line metrics (📰 news / 💬 retail / 📈 5d), framing
  line, and top key tickers footer. New `RADAR_TERMS.retail_sector_pulse`
  tooltip entry.
- **`bridge.py`** — new `load_retail_sector_pulse()` reads the JSON and
  nests under `data['tactical']['retail_sector_pulse']`. Non-fatal on
  missing file.
- **`daily_update.sh` Step 9.5** — runs `aggregate.py` after
  Narrative Pulse, before bridge. Non-fatal failure.

### Design

- **Daily only** for V1. Intraday 4h refresh deferred to V3.21+
  (avoids dashboard_server daemon + cache invalidation surface this round).
- **Rule-based framing** (no LLM). Templates in `config/weights.yaml` per
  language. Reasoning: Narrative Pulse V1.1 already validated that
  declarative-rule transparency beats black-box scoring for weekly
  calibration.
- **Retail Sector Pulse is exploratory display layer only** — does NOT
  influence `investment_protocol`, `momentum-monitor` ranking, or any
  auto-trade logic. composite_score is suggestion direction, not signal.

### Coverage Limitation (V3.20.1 backlog)

- `SECTOR_TOP_5` tickers (AAPL, LLY, XOM, BRK-B, AMZN, …) are mostly NOT
  in the narrative-pulse `batch_scan` universe today (which is
  thematic-screener top movers + structural watchlist). Result:
  `retail_mention_multiplier` defaults to None for most sectors on first
  ship. Aggregator handles gracefully (re-normalize composite weights to
  available signals). V3.20.1 plan: expand narrative-pulse universe to
  include SECTOR_TOP_5 ticker set so retail volume signal is always
  populated.

### Why

- Tactical Opportunity Radar V0.2 showed regime + per-ticker narrative
  pulse + theme heat, but lacked **per-sector retail-perspective signal**.
  User asked for "從散戶可以拿到的新聞 + 散戶可知資訊 + 市場情緒,分產業
  分析個股幾天內走向". V3.20.0 fills that gap with a single new aggregator
  and one new radar section.

## [3.19.1] — 2026-05-25 — Narrative Pulse V1.1.1: Codex review fixes

### Fixed

- **`weights_version: v1.1 → v1.1.1`** so existing per-ticker cache files
  (generated under the buggy V1.1 weights / normalize) are auto-invalidated by
  `pulse._cache_fresh()` on next run. Without this bump, cached classifications
  from the morning V1.1 run would silently survive into V1.1.1 evaluations.
- **Regenerated `Dashboard/narrative_pulse.json`** via a fresh
  `batch_scan.py --no-cache` so the live dashboard reflects V1.1.1 weights,
  bounded normalize, three-layer E[R], and the bumped batch schema `"version": "1.1"`.
- **Stage 1 SMA200 gate now effectively mandatory.**
  `skills/narrative-pulse-detector/config/stage_weights.yaml` — re-balanced
  Stage 1 brewing condition weights from `0.4 / 0.3 / 0.3` (breakout / media /
  no_sell_side) to `0.5 / 0.25 / 0.25`. Previously `media_quiet +
  no_sell_side_raise` summed to exactly `min_confidence_for_stage = 0.6`,
  so a below-SMA200 ticker that happened to be media-quiet with no
  sell-side raise would still classify as Stage 1 brewing — the
  SMA200 condition was a soft signal, not a gate. New weights make
  `media + no_sell_side = 0.50 < 0.60`, forcing the breakout signal to
  fire for a Stage 1 verdict.
- **Bounded normalize respects scenario clamp.**
  `skills/narrative-pulse-detector/scripts/classify_stage.py` — replaced
  the simple proportional `prob *= scale` with `_bounded_normalize()`
  (water-filling iteration). The previous step clamped each scenario to
  `[0.05, 0.80]` but the subsequent normalize-to-Σ-1 could re-inflate a
  clamped value above the cap (a `[0.80, 0.05, 0.05] / 0.90` case
  produced `[0.889, …]`). The new projection distributes the
  deficit/excess proportional to each scenario's headroom toward the
  bound, so post-normalize values respect `[clamp_lo, clamp_hi]` AND
  Σ = 1. The breakdown's `_normalize` entry now annotates
  `bounded water-fill to Σ=1 within [lo, hi]`.
- **Batch output schema version bumped + schema.md documented V1.1.**
  `batch_scan.py` now emits `"version": "1.1"` (was `"1.0"` despite
  breaking payload changes). `schema.md` documents the new
  `prob_base` / `prob_breakdown` / `target_pct_base` / `target_breakdown`
  fields, the `expected_return_pct_base` field, the shifted
  `expected_return_pct_pre_macro` semantics, and the snapshot archive
  path. Added a "V1.1 Breaking Schema Changes" section so downstream
  consumers can detect the contract change.

### Added

- 2 regression tests in `test_stage_classifier.py::TestV111CodexFixes`:
  - `test_below_sma200_quiet_does_not_classify_stage_1` reproduces Codex's
    finding #1 fixture and asserts Stage ≠ 1.
  - `test_bounded_normalize_respects_clamp` reproduces Codex's finding #2
    fixture (`[0.90, 0.05, 0.05]`) and asserts post-normalize max ≤ 0.80,
    min ≥ 0.05, Σ = 1.

### Why

- All three issues were real bugs introduced (or left unfixed) by V3.19.0.
  V1.1's transparency goal (formulas visible, deltas traceable) is
  undermined if the declared `[0.05, 0.80]` clamp can silently be
  violated by the normalize step, or if the SMA200 "hard gate" is
  documented as mandatory but is actually optional in practice. Schema
  staleness compounds the risk because downstream consumers cannot
  detect the V1.0→V1.1 contract change. Fixed in a single patch because
  all three sit on the V1.1 scenario-math pipeline and share the same
  test surface.

### Test Results

- `python3 skills/narrative-pulse-detector/tests/test_stage_classifier.py`
  → 30/30 OK (28 original + 2 new)
- `python3 skills/narrative-pulse-detector/tests/test_fetch_inputs.py`
  → 3/3 OK

## [3.19.0] — 2026-05-25 — Narrative Pulse V1.1: per-ticker scenario math

### Changed

- **`skills/narrative-pulse-detector/scripts/fetch_inputs.py`** — `sma200_breakout_days_ago`
  semantics fix: when latest close is below SMA200, return `None` instead of `0`.
  Old behavior had the function `break` on the first below-bar walking backwards,
  silently returning `0`, which satisfied the Stage 1 brewing rule
  `0 <= sma200_breakout_days_ago <= 30` and misclassified below-SMA200 tickers
  as "fresh breakout."
- **`skills/narrative-pulse-detector/config/stage_weights.yaml`** — bump
  `weights_version: v1.0 → v1.1` (auto-invalidates per-ticker cache).
  Stage 1 `sma200_breakout_recent` rule tightened with `is not None` guard +
  `price_to_sma200_ratio >= 1.0` hard gate. New `scenario_adjustments:` block
  declares per-ticker prob / target deltas for Stage 1 (brewing), Stage 2
  (ignition), Stage 4 (euphoria), Stage 5 (distribution). Stage 3 (acceleration)
  is intentionally NOT included — holding-period per-ticker tuning has low
  marginal value at this iteration. `global.prob_clamp: [0.05, 0.80]` +
  `normalize: true` enforce probability bounds and Σ = 1.
- **`skills/narrative-pulse-detector/scripts/classify_stage.py`** — new
  `_apply_scenario_adjustments()` reads the YAML adjustment block and applies
  bounded per-ticker prob/target deltas. Every applied rule is recorded in
  `prob_breakdown` / `target_breakdown` for full traceability — user reads the
  JSON to see exactly which condition fired with what delta. `_clamp` and
  `_normalize` synthetic entries are appended where they take effect.
- **`skills/narrative-pulse-detector/scripts/pulse.py`** + `batch_scan.py` —
  surface the three new E[R] layers in cache JSON and Dashboard output.
- **`skills/narrative-pulse-detector/scripts/batch_scan.py`** — every run now
  writes a snapshot copy to `snapshots/<YYYY-MM-DD>.json` for the 5/31
  observation-period review (join momentum-journal forward returns later).

### Added

- **Three-layer E[R] in output JSON** (per ticker):
  - `expected_return_pct_base` — V1.0 prior, no ticker delta, no macro. Control
    for 5/31 review.
  - `expected_return_pct_pre_macro` — V1.1 ticker-adjusted scenario sum, no macro.
    Isolates the per-ticker rule contribution.
  - `expected_return_pct` — final value (pre_macro + Σ macro_delta). Dashboard
    renders only this; the others are for downstream analytics.
- **`scenario_model_version: "v1.1_declarative"`** field on every classify
  result for downstream consumers to detect schema.
- **`skills/narrative-pulse-detector/snapshots/`** new directory with `.gitkeep`.
- **`skills/narrative-pulse-detector/tests/test_fetch_inputs.py`** — new test
  file. 3 synthetic-OHLCV tests verify the SMA200 breakout semantics fix at the
  fetch layer (below→None, above streak count, <200 bars→None).
- **`skills/narrative-pulse-detector/tests/test_stage_classifier.py`** — new
  `TestV11ScenarioAdjustments` class with 7 regression tests covering:
  same-stage divergence, Σ prob = 1, breakdown traceability, clamp bounds,
  Stage 3 untouched, three-layer E[R] consistency, model-version tag.

### Why

- V1.0 hardcoded scenario `prob` and `target_pct` as stage-level constants,
  so every Stage 1 brewing ticker showed identical `+11.15%` E[R]. Information
  density on the Dashboard was zero — same stage → same number → 8 rows that
  add nothing beyond what the stage label already tells you.
- User wants formula transparency: every probability movement should be
  traceable to a named, condition-guarded YAML rule that the user can edit
  during weekly calibration. V1.1 is intentionally heuristic-declarative,
  NOT logistic regression — sample size during the observation period
  (target ≥ 210 by 5/31) is too small to fit weights, and a black-box
  model wouldn't satisfy the "show me the math" requirement.
- The SMA200 breakout `0` vs `None` bug was a separate pre-existing issue
  that fed false fresh-breakout signals into Stage 1 brewing. Fixed in the
  same patch since it sits on the same gating logic.

### Breaking Schema Change

- **`expected_return_pct_pre_macro` semantics shifted.** In V1.0 it was the
  raw stage prior (no ticker delta, no macro). In V1.1 it is the
  ticker-adjusted scenario sum (no macro). The original V1.0 meaning has moved
  to the new `expected_return_pct_base` field. Downstream consumers that
  treated `pre_macro` as the V1.0 baseline must read `_base` instead.

### Rollback Plan (5/31 review)

- If the 5/31 review shows `pre_macro` IC / hit rate does NOT beat `base`,
  set every `scenario_adjustments.*.prob_deltas[].delta = 0` in the YAML.
  That is equivalent to falling back to V1.0 priors without touching code.
  No code rollback required.

## [3.18.4] — 2026-05-25 — Momentum rank-score UI wiring

### Changed

- `Dashboard/momentum.html` now has a dedicated calibrated rank-score column
  next to the raw momentum score.
- `Dashboard/page-momentum.js` defaults table sorting to `rank_score` while
  preserving the raw `score` slider as the quality threshold.
- `bridge.py` now carries `rank_score` from momentum CSV output into
  `data.json.momentum_screen.rows`.

### Why

- V3.18.2 introduced calibrated momentum ranking, but the dashboard still only
  surfaced raw `score`. This makes the improvement observable in the UI and
  separates "passes base quality" from "preferred by calibrated leader rank".

## [3.18.3] — 2026-05-24 — REVIEW carry-over queue (TODO 跨週傳遞)

### Added

- **`reports/decision_review/REVIEW_TODO.md`** — 新檔,專職 queue 裝跨週 carry-over
  todo。Schema 含 created_in / source_type (`accumulating_data` / `out_of_scope` /
  `instrumentation_gap`) / trigger_condition (量化) / target_action (附 file path) /
  review_count / status / last_check / evidence。Active Items + Closed Items 兩區段。
- **REVIEW_PROMPT.md Step -1 (preamble)** — 每週 LLM REVIEW 開頭先讀 REVIEW_TODO.md
  Active Items,逐筆 +1 review_count + 對照本週 event_index 判斷
  `ready` / `still_waiting` / `stale`,寫進輸出報告新增的 **「## 0. Carry-over
  from Previous REVIEWs」** 段。`ready` 項目在報告 Section 5 末尾再次拋出,讓
  user 跑完 REVIEW 後優先處理。
- **REVIEW_PROMPT.md Step 5 (postamble)** — REVIEW 結束時掃 Section 3「累積資料後再
  評估」+ Section 4 系統盲點 + 任何 instrumentation gap,append 新 item 到
  REVIEW_TODO.md Active Items (ID 連號)。已在 Active 的不重複 emit。
- **8 個 seed items** (TODO-001 ~ TODO-008) — 從 REVIEW_2026-05-24 + 3.18.x leftover
  人工 seed:
  - TODO-001: Pattern B (CANCEL miss) N≥20 重評 (3.18.1 抓到 11 個漏標 CANCEL,
    真實 N 應 ≥ 20)
  - TODO-002: Pattern A HOLD 集中 Semiconductors 等 V5 decisive_agent 累積驗證 H1/H3
  - TODO-003: momentum-screen verdict 規則重審 (跟 3.18.2 momentum calibration 互補)
  - TODO-004: 拆 `final_decision` / `final_action` 兩欄 full version
  - TODO-005: verdict 物件 surface max_drawdown / max_runup
  - TODO-006: pre-V5 era macro_regime null 29% 老報告無 phase0 cache
  - TODO-007: Rec 7 (sub_industry_heat) 連續 3 週 < 15pp 則 paused
  - TODO-008: news-digest 殘留 9 筆 macro_delta null 逐一檢視

### Why

3.18.0 + 3.18.1 修完 extractor 後識別出一堆「下次再做 / 累積後再評估 / 等修」項目,
**但這些 item 之前沒地方裝** — REVIEW_2026-05-24 寫了「out-of-scope」清單但下週 LLM
不會主動讀它,等於每週重新發明輪子或乾脆漏掉。`ADJUSTMENT_LEDGER.md` 只裝**已套用**
的 Rec (active/paused/rolled-back/superseded),不適合裝**待動**項目 (語意不對)。

新增 REVIEW_TODO.md 解這 gap:
- 跨週**持續可見** (每次 LLM REVIEW 必讀)
- review_count 自動 +1,4 週沒動會自動 `[stale]` 提醒 drop 或 promote
- `ready` 標記讓 user 跑完 REVIEW 後**有明確 next action**,不是 "讀完報告就忘"
- evidence 累積每週 N 值,trigger_condition 達成時 LLM 主動標 ready

跟 ADJUSTMENT_LEDGER 分工:
- ledger = **已套用** Rec,每週評估 metric 是否 still improving
- todo = **待決定 / 等資料 / 等修** 候選,評估前不算 Rec,trigger 達成才 promote

### Touched

- `reports/decision_review/REVIEW_TODO.md` (新檔,+200 行 schema + 8 seed items)
- `reports/decision_review/REVIEW_PROMPT.md` (+50 行,改任務從四步 → 六步,
  輸出格式加 Section 0 + Section 5)
- 不動 extractor / event_index / build pipeline

## [3.18.2] — 2026-05-24 — momentum-screen calibration + review metrics

### Changed

- `skills/momentum-monitor/scripts/screen.py`
  - Added `rank_score` alongside raw composite `score`; ranking now uses calibrated
    `rank_score` while preserving raw score in CSV/Markdown.
  - Added empirical signal adjustments: reward Stage 2 / RS leader / fresh 20-50
    cross / near-high strength; penalize squeeze, high short interest, VCP-only,
    death cross, MACD bearish, and extension warnings.
  - Added soft cooldown from recent journal Top-20 appearances via
    `--cooldown-snapshots` (default 3, disable with 0).
  - Fixed CLI mutually-exclusive default bug: `--tickers AAPL,MSFT` no longer gets
    overridden by implicit `--universe all`.
- `dashboard_server.py`
  - Dashboard momentum runs now default to a conservative leader preset:
    `min_score=65`, `min_rs=60`, `min_nhp=-10`, and exclusion of squeeze/death-cross
    names unless the caller passes explicit custom tickers.
- `scripts/verdict_rules.py` / `scripts/build_event_index.py`
  - Added momentum per-ticker aggregate metrics (`hit_rate_with_neutral`,
    `hit_rate_ex_neutral`, `neutral_rate`, mean/median return) so review reports can
    distinguish neutral-heavy screens from outright misses.
- `skills/momentum-monitor/scripts/journal.py` and
  `scripts/extractors/momentum_extractor.py`
  - Persist and propagate `rank_score` through CSV → journal → event_index.

### Validation

- `python3 -m py_compile scripts/verdict_rules.py scripts/build_event_index.py scripts/extractors/momentum_extractor.py skills/momentum-monitor/scripts/screen.py skills/momentum-monitor/scripts/journal.py dashboard_server.py`
- `python3 skills/momentum-monitor/scripts/screen.py --tickers AAPL,MSFT,NVDA --max-age 9999999 --output-dir /private/tmp --md-only --cooldown-snapshots 0 --top 3`
- Conservative filter smoke with custom tickers and cached data.

## [3.18.1] — 2026-05-24 — Codex round-2 review fixes (Pattern B 真正解鎖)

### Fixed

- **🔴 `_find_decision` 早 return 漏抓 Final Action / Action Label rows**
  (Codex round-2 review #1):
  V5.0 後期報告把 Final Decision / Final Action / Action Label 拆成三 row
  (`reports/20260510_MU.md:9-14`)。原 implementation 在第一條 hit (Final Decision=HOLD)
  就 return,丟掉 Final Action=CANCEL + Action Label=DEFENSIVE → `final_action_modifier=None`,
  defeats stated purpose of distinguishing 裸 HOLD vs HOLD+CANCEL。
  修復: `_find_decision()` 改 multi-pass aggregation:
    1. 掃 `_DECISION_ROW_FINAL` regex (verb + 可選 paren modifier)
    2. 掃 `_DECISION_ROW_ACTION` regex (Final Action row)
    3. 掃 `_DECISION_ROW_ACTION_LABEL` regex (Action Label row)
  Modifier priority chain: paren content > Final Action > Action Label。
  Side effect:**pre-V5 era 之前被當「裸 HOLD」的 12 個 case 現在正確標 `CANCEL`**,
  REVIEW Pattern B (CANCEL miss 78%) 的 N=9 樣本基數可能擴大,Pattern A
  (HOLD miss 24/43) 統計需重新分桶。

- **🔴 `AGENT_TABLE_V50_RE` score cell 太嚴 (Codex round-2 review #2)**:
  Score cell regex `([+\-]?\d+(?:\.\d+)?)\s*\|` 不容忍 trailing 註記如
  `4 (capped +3)` (`reports/20260510_MU.md:31`)。整 row drop → MU 20260510
  decisive_agent 變 News (錯誤,Fundamentals 才該 dominate)。修復: score cell
  改 `([+\-]?\d+(?:\.\d+)?)[^|]*?\|`,score 後吞 trailing 內容到下個 `|`。

- **🟡 `_normalize_modifier` 沒 enforce ALL-CAPS (Codex round-2 review #3)**:
  原 implementation 取第一 whitespace token 不過濾 case,GLW 20260427
  `HOLD (Auto REJECT)` → modifier="Auto" (title case)。修復: 改用
  `_MODIFIER_TOKEN_RE = r"[A-Z][A-Z_]{1,}"` 抓第一個 ALL-CAPS token ≥2 chars,
  跳過 "Auto" / "Forward" 等 title-case noise → modifier="REJECT"。

### Added

- **新增 V5.0 table variants for column-order resilience**:
  - `AGENT_TABLE_V50_INV_RE` — Score|Signal column order (TSM 20260510:
    `| Lane | Score | Signal | Confidence |`)
  - `AGENT_HEADING_V50_SCORE_FIRST_RE` — `### Lane — Score N | SIGNAL | conf X`
    heading variant
  - 修前 TSM 20260510 `agent_count=0`,所有 lane drop。修後 5 lanes 全抓,
    decisive_agent 正常。**V5 era null_decisive 9% → 0%**。

- **regression tests 從 19 → 26** (+7 covering Codex round-2 bugs):
  - `test_final_action_three_row_aggregation_mu_format`
  - `test_final_action_action_label_only_fallback`
  - `test_final_action_paren_modifier_beats_other_rows`
  - `test_normalize_modifier_rejects_titlecase`
  - `test_v50_table_score_with_capped_annotation`
  - `test_v50_table_score_signal_inverted_column_order`
  - `test_v50_heading_score_first_inline`

### Why

3.18.0 把 Pattern G/H 解鎖,但 Codex round-2 review 抓出 instrumentation 本身
有 4 個 bug (3 行為 + 1 hygiene),會污染下輪 REVIEW 的 root cause 分析。
最關鍵的 Bug A (Final Action row 沒抓) 直接影響 Pattern B 樣本基數 —
原 REVIEW 報 9 個 CANCEL,但實際有 12 個被縮成裸 HOLD,代表 Pattern B
真實 N 可能 ≥ 20。修完後下輪 REVIEW 可以信任 modifier 欄分桶。

### Backfill verification

| metric | 3.17.x (before) | 3.18.0 (round-1) | 3.18.1 (round-2) |
|---|---|---|---|
| V5 era null `decisive_agent` | 100% (33/33) | 9% (1/11) | **0% (0/11)** |
| V5 era null `macro_regime` | 100% (33/33) | 0% (0/11) | 0% (0/11) |
| V5 era `final_action_modifier` 有值 | n/a | 2/11 | **6/11** (DEFENSIVE 4, CANCEL 1, WAIT 1) |
| Pre-V5 `CANCEL` modifier 抓到數 | 0 | 0 | **11** |
| All-data action_modifiers 分佈 | n/a | 2 buckets | **6 buckets** (None/CANCEL/EXECUTE/REJECT/ATTACK/DEFENSIVE/WAIT) |

### Touched

- `scripts/extractors/deep_dive_extractor.py` (+95 行):
  - 新 regex `_DECISION_ROW_FINAL` / `_DECISION_ROW_ACTION` / `_DECISION_ROW_ACTION_LABEL`
    / `_MODIFIER_TOKEN_RE` / `AGENT_TABLE_V50_INV_RE` / `AGENT_HEADING_V50_SCORE_FIRST_RE`
  - `_find_decision()` 改 multi-pass aggregation,signature 改 `tuple[verb, modifier]`
  - `_normalize_modifier()` 改用 ALL-CAPS token regex
  - `AGENT_TABLE_V50_RE` score cell 放寬 (1 char `*?` 加入)
  - `_find_agent_breakdown()` priority chain 加 2 個 V5 variant patterns
- `scripts/extractors/tests/test_extractors_review_fixes.py` (+170 行,7 新 test)
- `scripts/extractors/tests/__pycache__/` 移除 (hygiene; .gitignore 已含)
- `reports/decision_review/event_index_latest.json` 三度 backfill
- 不動 V5.0 protocol / verdict 規則 / Dashboard UI

## [3.18.0] — 2026-05-24 — REVIEW_2026-05-24 extractor fixes (Patterns G/H/B 解鎖)

### Fixed

- **`tuning_hooks.decisive_agent` 100% null in V5 era → 9%** (REVIEW Pattern G):
  V5.0 5-lane subagent 用新 markdown 標題格式 (`### Fundamentals — HOLD / -1.5`)
  + Final Visualization Table (`| Lane | Signal | Score | Confidence | … |`),
  既有 `AGENT_RE_V46` / `AGENT_RE_V44` 不認 + `AGENT_NAMES` 沒列 `Valuation`
  (V5.0 新增 lane)。修復:
  - 新增 `AGENT_TABLE_V50_RE` (table-first parser,容忍 `L\d+` prefix + `Specialist`
    後綴 + `Conf`/`Confidence` column alias)
  - 新增 `AGENT_HEADING_V50_RE` (heading fallback,無 confidence 欄)
  - `AGENT_NAMES` 加 `Valuation`
  - `_find_agent_breakdown()` 重寫:5-stage priority chain (V5 table → V5 heading →
    V4.6 inline → V4.4 inline → V4.4 JSON-block),seen-set 防重複
  - 新增 `tuning_hooks.decisive_agent_method` (`score_x_confidence` / `max_abs_score`),
    讓下輪 REVIEW 能分辨「真 confidence 主導」vs「fallback 用 |score|」
- **`tuning_hooks.macro_regime` 100% null → 0%** (V5 era,REVIEW Pattern H):
  V5.0 deep-dive MD 報告**不**內嵌 regime 標籤,只存在 `investment/invest_logs/<date>_phase0[_<ticker>].json`
  裡。`_find_macro_regime()` 只讀 MD 看不到。修復:
  - 模組頂端 `ROOT = Path(__file__).resolve().parents[2]` (Codex review #4 —
    repo-root absolute,不依賴 cwd,pytest monkeypatch.chdir 不會誤判)
  - `_find_macro_regime()` 重寫:優先讀 phase0 JSON,多 key fallback
    (`macro_summary.market_regime` / `phase1.market_regime` / `phase0.market_regime`
    / 根 `market_regime` / `macro_regime` / `regime`),fail-soft 回退 MD regex
  - `extract()` 傳 `decision_date` + `ticker` 給 `_find_macro_regime()`
  - 新增 `tuning_hooks.macro_regime_source` (`phase0_cache` / `md_regex` / None)
- **`session_macro_delta` backtick+bold+equals form parser miss** (REVIEW Rec 4 殘留):
  2026-05-18 報告用 `` `session_macro_delta` = **-0.5** `` 形式,8 個既有 regex 全漏。
  修復:`_find_macro_delta()` patterns 首位加 `` `session_macro_delta`\s*=\s*\*\*([+-]?…)\*\* ``。

### Added

- **`final_action_modifier` 欄** (Codex review #6 輕量版): V5.0 報告
  `| Final Decision | HOLD (DEFENSIVE) |` 的 paren modifier (DEFENSIVE / OFFENSIVE /
  CANCEL / WAIT / 等) 之前被 `split("(")[0]` 吞掉。修復:
  - `_find_decision()` signature 改 return `tuple[verb, modifier]`
  - 加 `_normalize_modifier()` 處理 keyed paren (NVDA: `(action_label: **WAIT** — …)`
    → `WAIT`),strip bold + take first token after `:`
  - regex 容忍 row label 無 bold wrapper (`| Final Decision |` vs `| **Final Decision** |`)
  - `decision_content.final_action_modifier` 新欄,**不**動既有 `final_action` (back-compat)
  - 下輪 REVIEW 可用此欄重算 Pattern A/B 分桶,區分「裸 HOLD」/「HOLD+DEFENSIVE」/
    「HOLD+CANCEL」三種狀態,解決 HOLD-miss 24/43 樣本污染問題
- **`tuning_hooks.agent_confidence_count`** — 有真 confidence 的 lane 數 (V5 heading
  fallback 時為 0),讓下輪 REVIEW 能判斷哪些 decisive_agent 是 score×conf 算的、
  哪些只能用 |score| fallback
- **`scripts/extractors/tests/test_extractors_review_fixes.py`** — 19 個 pytest
  regression tests 覆蓋全部 4 個 fix + V4.x back-compat (table parser / heading
  fallback / phase0 cache / phase0 cache fail-soft / paren modifier 變體 / 中文
  modifier / keyed paren / unbolded row label / V4.4 JSON-block)
- **`scripts/extractors/tests/__init__.py`** — pytest discovery anchor

### Why

REVIEW_2026-05-24 Section 5 列出 instrumentation gap 阻擋了 H1 (HOLD 過嚴?) / H3
(Semiconductors agent 主導?) 兩條根因 hypothesis。Pattern G (decisive_agent 100% null)
+ Pattern H (macro_regime 100% null) 是 root blocker — 無 decisive_agent hook
就無法回答「是哪個 agent 主導 HOLD 決定」,無 macro_regime hook 就無法做
「VOLATILE regime 下 Technical 權重要不要降」這類 regime-conditioned 分析。

修完後:
- V5 era null_decisive **100% (33/33) → 9% (1/11)**
- V5 era null_regime **100% (33/33) → 0% (0/11)**
- Pre-V5 bonus: 71% (79/112) 老報告也接到 phase0 cache → 整體 regime null rate
  從 ~50%+ 降到 27% (33/123)
- final_action_modifier 第一次有資料 (V5 era 2/11 已抓到 DEFENSIVE / WAIT)

下輪 REVIEW (2026-05-31) 可直接用這些 hook 回答 H1/H3。

### 不破壞

- `event_index` schema **純 additive** — 新增 4 欄 (`decisive_agent_method` /
  `macro_regime_source` / `agent_confidence_count` / `final_action_modifier`)。
  `render_event_index.py` 既有 `decisive_agent` / `min_agent_confidence` /
  `max_agent_confidence` 讀法不變 (只是現在 V5 era 有值了)。
- `final_action` 欄保持 verb-only,paren modifier 走新欄 — 既有 verdict_rules
  / Pattern A/B 統計邏輯**不**受影響,下輪 REVIEW 才主動引用新欄重算分桶。
- V4.x 報告 (V4.4 JSON-block / V4.6 inline) parsing **不 regress** — 5-stage
  priority chain 把舊 regex 全部保留在 chain 後段。

### Touched

- `scripts/extractors/news_digest_extractor.py` (+5 行,1 regex)
- `scripts/extractors/deep_dive_extractor.py` (+120 行,2 新 regex + 5-stage parser
  重寫 + `_find_macro_regime` 重寫 + `_find_decision` tuple return + `_normalize_modifier`
  helper + `extract()` 4 新 hook 欄)
- `scripts/extractors/tests/__init__.py` (新空檔)
- `scripts/extractors/tests/test_extractors_review_fixes.py` (新檔,+260 行,19 tests)
- `reports/decision_review/event_index_latest.json` 全量 backfill (252 records,
  老檔備份 `event_index_latest.bak.json`)
- 不動 V5.0 protocol / verdict 規則 / Dashboard UI

## [3.17.6] — 2026-05-24 — thematic-screener enrich phase 加 progress log

### Changed

- `skills/thematic-screener/scripts/enrich.py` `enrich_movers()` — 加入時間節流
  progress log,預設每 30s 印一次 `[HH:MM:SS]   ... N/M enriched (elapsed Xs)` 到
  stderr,格式對齊 predict phase 的進度行。最後一個 ticker 強制 log。
- 新增 kwarg `progress_every_sec=30.0`,caller 可調整節奏。

### Why

daily_update.sh Step 6 thematic-screener 在 enrich 240 個 ticker 時冷跑 5-10 分鐘,
原本完全沒 progress 輸出,user 端看起來像 stuck (`Enriching N tickers...` 一行後
靜默)。實測 165/238 enriched 用時 5 分鐘,中間完全沒提示。30s 節流確保至少每分鐘
有 2 行進度,夠判斷是不是 hang 而不會洗版。

### Touched

- `skills/thematic-screener/scripts/enrich.py` (+22 lines,純加 log,**不**動 enrich_one
  邏輯 / FMP 呼叫 / cache schema)。
- screen.py 不用改,signature 向後相容(新 kwarg 有 default)。

## [3.17.5] — 2026-05-24 — Narrative Pulse UI: 中文化 + insufficient_data 進度條

### Changed

- `Dashboard/page-radar.js` — Narrative Pulse detail panel polish:
  - `recommended_action` enum 中文化 mapping (`early_entry_window` → 早期進場窗口 等 6 個值)。
  - `next_warning_condition` 中文化 (`supply enough inputs to clear min_confidence=0.6 …`
    → `任一 stage conf 需 ≥ 0.6 才會掛標 — 目前全部不過閘`;`distribution day count >= 4 / 25d`
    → `分配日 ≥ 4 / 25d`;OHLCV 失敗 reason 也轉中文)。
  - `stage===null` (insufficient_data) 時把空白 scenarios 表換成 5 列 stage conf 進度條
    (S1 蘊釀 … S5 分配),conf ≥ 閘值用 stage 顏色,否則灰色,讓使用者一眼看出
    距離哪個 stage 最接近。

### Why

NVDA / 中段訊號股探測時,UI 只顯示 `Stage null 資料不足/訊號模糊` + 空 scenarios 表,
看不出來「為什麼模糊」也看不出來離哪個 stage 最近。新 stage 進度條把 classifier 內部
`all_stage_scores` 視覺化,user 可立刻判斷:
- 接近 brewing (Stage 1) → 等媒體冷卻就會掛標
- 全部都 < 0.3 → 真的訊號雜訊比過低,放生
另外 `early_entry_window` 這種 enum 直接秀英文 string 在中文 UI 內有違和,順手 i18n。

### Touched

- `Dashboard/page-radar.js` (+60 lines,新增 `ACTION_ZH` map / `warnZh()` / `stageScoresHTML()`
  + `renderDetailFromCache()` 改走 isInsufficient 分支)
- 純前端,**不**動 `classify_stage.py` 邏輯 / `narrative_pulse.json` schema。

## [3.17.4] — 2026-05-24 — Codex round-8 review fixes: secret-leak + cohort rate gate

### Fixed

- **🔴 `audit_data_alignment.py` API key leak via exception URL** (Codex Finding 1):
  PATH_B (direct REST) put the API key in query params. On DNS / network
  failure, `requests.exceptions.ConnectionError` echoed the prepared URL —
  including `apikey=<value>` — into the exception message, which then
  flowed into the returned dict, the `--json` stdout, and the persisted
  markdown report. Reproduced with `FMP_STABLE_QUOTE` pointed at an
  unresolvable host: sentinel key appeared in `_error` field.
  Two-layer fix:
    1. PATH_B switched to **header auth** (`headers={"apikey": api_key}`,
       removed apikey from `params`). Matches the FMPClient pattern.
       Confirmed post-fix: failing URL now reads `/stable/quote?symbol=NVDA`
       — no apikey query, no secret in exception trace.
    2. New `_scrub_secret()` helper applied to **every** returned error
       string (both PATH_A + PATH_B), strips `apikey=...` query patterns
       (case-insensitive) AND the literal key value when supplied.
       Belt-and-braces: even if a future library logs the prepared
       request differently, the scrub catches it.
  6 new regression tests in `scripts/_shared/tests/test_audit_secret_scrub.py`
  including the original DNS-failure repro asserting sentinel never appears
  in the returned dict.
- **🟡 cohort runner acceptance gate used absolute count vs documented rate**
  (Codex Finding 2): `min_directionally_correct: 14` was compared as
  `correct >= 14` against a denominator that was documented as AVAILABLE
  samples (not total 18). Practical effect: 6/6 or 13/13 correct would
  have FAILed acceptance despite 100% directional correctness.
  Fix:
    - Replaced `min_directionally_correct: 14` with
      `min_directional_correct_rate: 0.78` (14/18 ≈ 0.78)
    - `aggregate()` evaluates `directional_pct >= min_rate`
    - Backward-compat: legacy `min_directionally_correct: <int>` still
      accepted; runner converts to `<int> / 18.0` rate.
  7 new regression tests in
  `skills/_shared/composite_calibration_cohort/tests/test_acceptance_rate.py`:
  6/6 PASS, 13/13 PASS, 14/18 strict FAIL (documents the boundary
  intentionally), insufficient data still INSUFFICIENT_DATA, flag rate
  independently gated, legacy abs-count config converts correctly.

### Verified

- `python3 -m pytest scripts/_shared/tests skills/_shared/composite_calibration_cohort/tests
  skills/earnings-analyst/tests skills/earnings-valuation-forecaster/tests
  skills/narrative-pulse-detector/tests`
  → **100 passed** (was 87 in V3.17.3; +6 secret scrub + 7 acceptance rate)
- DNS leak repro post-fix: sentinel `SENTINEL_SECRET_NEVER_VALID_V317` does
  NOT appear in `_path_b_rest_direct` error result; URL in trace is
  `/stable/quote?symbol=NVDA` (no apikey query)
- Live alignment still works: NVDA 0.00% diff path_a vs path_b
- Cohort runner: same 18/18 missing soft-pass behavior post-rate-conversion

---

## [3.17.3] — 2026-05-24 — Governance sub-wave: cohort + alignment + stale gate

### Added

- **`skills/_shared/composite_calibration_cohort/`** — V3.17 rubric calibration
  measurement layer (NOT enforcement). Three files:
    - `cohort.yaml` — 18-ticker manifest grouped into 6 buckets (hyper_growth_transition
      / mature_mega_cap_stable / value_trap / hype_bust / margin_recovery /
      cyclical_trough). Each entry: `{ticker, target_quarter_end,
      expected_outcome, notes}`. Acceptance gates pinned to ≥ 14/18 directional
      correctness + new-flag trigger rate ≤ 30%.
    - `runner.py` — reads cohort.yaml, finds the closest earnings-analyst
      cache within ±90 days of `target_quarter_end`, re-runs `analyze()`, scores
      each sample's composite vs hand-coded `expected_outcome`, aggregates,
      writes `reports/calibration_<DATE>.md`. **Always rc=0** (soft-pass) —
      missing caches counted but excluded from acceptance denominator. When
      AVAILABLE < 6 samples, acceptance = `INSUFFICIENT_DATA`.
    - `__init__.py` — package marker.
  Initial run: 0/18 AVAILABLE (no historical caches present yet). User can
  populate over time via `python3 skills/earnings-analyst/scripts/fetch.py
  <T>` with historical periods, or accept the skeleton as a future-baseline.
- **`scripts/_shared/audit_data_alignment.py`** — cross-validates two FMP
  read paths (`fmp_client.FMPClient.quote` vs direct `requests.get /stable/quote`)
  for 5 default mega-cap tickers, surfacing price / PE / market_cap divergences
  > 1%. Soft-fail rc=0 on FMP quota / unavailability. Substitutes for the
  original "MCP vs script alignment" spec because MCP tools only run inside
  Claude's harness — the two-path FMP check catches the same class of bugs
  (cache staleness, endpoint version drift). Live verification:
  NVDA/AAPL/MSFT all 0.00% diff.
- **`skills/earnings-analyst/tests/test_stale_gate_simulated.py`** — 8 unit
  tests freezing the V3.17.1 stale-gate contract from synthetic mtime fixtures:
    - 4 `TestStaleThresholdMath` — pin the 6h boundary (strict `>`)
    - 2 `TestEarningsAnalystEmitsSignatureMtime` — analyze() must emit
      `transition_signature_mtime` for the protocol's Phase 3 Step 2
      cross-check to be operational
    - 2 `TestForecasterBackfillsMtimeFromOldCache` — `_load_earnings_analyst_bundle`
      backfills `transition_signature_mtime` from cache file mtime for
      pre-V3.17.1 caches, but never overwrites an explicit value (setdefault)

### Why governance is a measurement layer, not a release gate

Per Codex round-7 risk discussion:
  - Historical earnings-analyst caches aren't guaranteed to exist for the
    18 cohort periods. Live-fetching them would couple the wave to FMP
    quota availability and historical data depth (the free tier exposes
    5 years of annuals + recent quarters only). Runner uses cached
    fixtures and reports `MISSING_CACHE` honestly.
  - Acceptance denominator = **AVAILABLE samples**, not total 18. A
    cohort with 8 available samples scoring 6 correct is `directional_pct = 75%`,
    not 6/18 = 33%. Otherwise sparse caches would automatically fail acceptance.
  - Stale-gate trigger rate is measured via fixture simulation
    (`test_stale_gate_simulated.py`), NOT on historical cache mtime. Local
    filesystem mtime ≠ financial event time, so historical cache mtimes
    would systematically misreport the gate.
  - Alignment audit soft-fails rc=0 on FMP unavailability. External-service
    flakiness must not block the governance wave.

### Verified

- `python3 -m pytest skills/earnings-analyst/tests skills/earnings-valuation-forecaster/tests skills/narrative-pulse-detector/tests`
  → **87 passed** (was 79 in V3.17.2; +8 stale gate)
- `python3 skills/_shared/composite_calibration_cohort/runner.py`
  → cohort v1.0 → reports/calibration_2026-05-24.md; available=0/18 missing=18
  errors=0; acceptance=INSUFFICIENT_DATA (rc=0 soft-pass — expected on first run)
- `python3 scripts/_shared/audit_data_alignment.py --tickers NVDA,AAPL,MSFT`
  → ok=3 alert=0 unavailable=0 threshold=1.0% (rc=0)

### Out of scope (deferred to V3.18+)

- Populating cohort with real historical fixtures (cohort runner is
  intentionally skeleton — user adds caches over time)
- Re-baselining acceptance thresholds (`min_directionally_correct=14`,
  `max_new_flag_trigger_rate=0.30`) after observing real cohort outcomes
- Wiring `audit_data_alignment.py` into daily_update.sh as a cron job
  (currently ad-hoc CLI only)

---

## [3.17.2] — 2026-05-24 — business_mix tier ceiling fix + slim_* round-trip contract

### Fixed

- **`compute_business_mix_shift_overlay` tier ceiling bug** (Codex Finding 1):
  segments with `share > 25%` + qualifying growth/CAGR silently stayed `STABLE`
  on FY-fallback caches because `emerging_share_ok` was `0.10 <= share <= 0.25`
  AND the ESTABLISHED branch only fired on `data_mode == "quarterly"`. The 25%
  upper bound was an implicit assumption that ESTABLISHED would catch any
  higher share — but ESTABLISHED is unreachable on FMP free tier (no quarterly
  segment OI). Result: AMD-like Data Center (60% share, 66% YoY, 51pp relative
  CAGR) FY-fallback fixture mis-labelled STABLE instead of EMERGING.
  Fixed semantics: `share_ok = share >= 0.10` (lower bound only) + growth +
  CAGR → at least EMERGING; ESTABLISHED upgrade path remains wired for V3.18+
  when quarterly segment OI lands.

### Improved

- **Tightened contract test assertion** (Codex Finding 2):
  `test_amd_like_fixture_classifies_emerging_or_better` was renamed to
  `test_amd_like_fixture_classifies_emerging_strict` with `assertEqual("EMERGING")`
  in place of the original `assertIn(..., {EMERGING, ESTABLISHED, STABLE})`
  which silently masked the Finding 1 bug. Also added
  `test_low_share_high_growth_stays_stable` to pin the EMERGING floor at 10%.

- **`TestFetchSlimRoundTripContract` added** (Codex Finding 3): 4 new cases
  that feed raw FMP-shaped rows through the real `fetch.py.slim_segment_product`
  / `slim_segment_geographic` / `slim_balance` / `slim_income` helpers before
  invoking the analyzer. This catches schema drift where the slim_* output
  shape changes (e.g. `products` → `lines`) but pre-shaped fixtures would
  still pass:
    - `test_slim_segment_product_shape_contract` — pins the `{date, fiscal_year,
      period, products: {...}}` output shape and snake_case fiscal_year
    - `test_slim_segment_geographic_shape_contract` — same for regions
    - `test_round_trip_analyzer_picks_correct_segment` — raw → slim → analyzer
      must reach EMERGING with `new_segment = Data Center`
    - `test_round_trip_balance_with_ap_yields_direct_dpo` — pins `slim_balance`
      keeps `accountsPayable` + `otherCurrentLiabilities` and `slim_income`
      keeps `costOfRevenue` (V3.17 additions); regression would drop DPO to
      `unavailable` silently

### Verified

- `python3 -m pytest skills/earnings-analyst/tests skills/earnings-valuation-forecaster/tests skills/narrative-pulse-detector/tests`
  → **79 passed** (31 V3.17 + 21 narrative-pulse + 27 contract — was 74 pre-fix)
- NOK live re-run: composite **47 unchanged**, mix=STABLE unchanged
  (NOK's geographic FY shape lacks any high-share high-growth new segment,
  so the bug fix has no impact on this ticker — confirming the fix is
  targeted at the AMD/NVDA Data Center class, not NOK)

### Why this slipped V3.17.1 review

The original `test_amd_like_fixture_classifies_emerging_or_better` accepted
`STABLE` as a valid outcome. Codex round-6 caught the segment parsing bug
(metadata key selection) but not the tier classification bug because the
test never asserted what the AMD-like fixture _should_ resolve to. The
revised assertion makes the contract explicit.

---

## [3.17.1] — 2026-05-24 — Transition overlay review fixes

### Fixed

- `earnings-analyst` now flattens `segments.product_fy[].products` and
  `segments.geographic_fy[].regions` before scoring business mix shift, so
  metadata fields like `fiscal_year` cannot be selected as the new segment.
- `business_mix_shift_overlay` now treats exactly 25% revenue share as
  `EMERGING`, matching the documented `[10%, 25%]` threshold.
- `earnings-valuation-forecaster` markdown output now renders the
  Revenue-Margin Matrix when `transition_case` is true.
- Transition staleness fields are now emitted: `transition_signature_mtime`
  from earnings analyst and top-level `transition_case_mtime` from the
  forecaster.
- Forecaster numeric anomaly wording now matches implementation:
  latest annual PE plus FY segment YoY growth, not true forward PE or quarterly
  segment growth.
- V3.17 test files were renamed to unique module names so combined `pytest`
  collection no longer fails with an import mismatch.

### Verified

- `python3 -m pytest skills/earnings-analyst/tests/test_earnings_analyst_v3_17.py skills/earnings-valuation-forecaster/tests/test_forecaster_v3_17.py`
- `python3 -m pytest skills/earnings-analyst/tests/test_earnings_analyst_v3_17.py skills/earnings-valuation-forecaster/tests/test_forecaster_v3_17.py skills/narrative-pulse-detector/tests/test_stage_classifier.py`

---

## [3.17.0] — 2026-05-24 — Skills/Protocol 泛化優化 Wave 1 (Codex 5-round + Gemini review)

### Added

- **`earnings-analyst` cash conversion 3-tier directional flag system** (`analyze.py`):
  - `accruals_warning_negative` — NI > OpCF, gap > 30% (red flag, −4)
  - `cash_conversion_positive_gap_clean` — OpCF > NI + WC 不惡化 (正向訊號, 0 penalty,
    replaces V3.16 monolithic accruals_warning miscategorization)
  - `cash_conversion_wc_driven` — OpCF > NI + WC 任一惡化 (ambiguous, −2 half penalty)
- **Working capital diagnostics 二階校對** (`compute_wc_diagnostics`):
  - DSO / DIO / DPO 4Q trend + deteriorating flag (rising trend + 最新 Q > 4Q_avg × 1.15)
  - DPO 3-tier fallback (G3 — Gemini): `direct` (有 accountsPayable) / `estimated_from_other_cl`
    (0.6 × OCL fallback for foreign ADRs) / `unavailable`
  - **Estimated DPO 不可單獨觸發 wc_driven** (避免 FMP schema 缺陷誤觸紅旗)
- **`business_mix_shift_overlay`** (`analyze.py` — Codex v5 + Gemini G1):
  - Quantified tier thresholds:
    - `EMERGING`: new_segment share ∈ [10%, 25%] AND YoY ≥ 15% AND relative CAGR > +10pp
    - `ESTABLISHED`: share ≥ 25% AND OI share ≥ 40% AND 連續 4 季 (FY-fallback caps at EMERGING)
  - `new_segment` 識別 (M1): argmax over segments of `(seg_5y_CAGR_per_share −
    consolidated_5y_CAGR_per_share)` AND `latest_YoY > 0` (top-1 only)
- **`transition_signature`** integrates `structural_shift` + `business_mix_shift_overlay`:
  `paradigm_only | mix_only | both | neither` — consumed by forecaster + protocol Phase 3
- **`earnings-valuation-forecaster` transition_case priority cascade** (`forecast.py`):
  1. `transition_signature ∈ {paradigm_only, mix_only, both}` → `reason=signature_*`
  2. Numeric anomaly: `latest annual PE > 50 AND DCF/price < 0.5 AND 5y_CAGR < 5% AND FY seg YoY growth > 30%`
  3. Otherwise `false`
- **Revenue-Margin trade-off matrix** — 2 versions:
  - EMERGING: `volume_driven / margin_driven / balanced / bear_reset`
  - ESTABLISHED: `market_share_consolidation / moat_validation / pricing_power / disruption_threat`
    (M4 — renamed from `regime_break` for ESTABLISHED case semantic clarity)
- **`achieves_if` dual-field** (Codex v5 + reviewer): `achieves_if_text` (str, backward
  compat) + `achieves_if_struct` (dict for protocol consumers); legacy `achieves_if` mirrors
  text field
- **`momentum-monitor` market-cap aware extension warnings** (`momentum.py`):
  - `large_cap_parabolic`: marketCap > $10B AND above_ma200_pct > 100
  - `mid_cap_extreme`: marketCap > $2B AND above_ma200_pct > 100
  - `microcap_extension`: small cap same condition
  - Preserves existing `parabolic_blowoff_risk` (am200 > 50); new tags are additive severity
- **`investment_protocol_v5_0.md` updates**:
  - Phase 0 `systemic_backdrop` stub schema (V0.1, values null — ready for V3.18 fill)
  - Phase 1 EARNINGS_ANALYST_BUNDLE adds 4 new fields documented in table
  - Valuation Specialist 必填 `cited_transition_overlay` + `transition_dissent_basis`
    (`macro_systemic | thesis_fundamental | valuation_anchor | null`) — Gemini G4 乾淨方案
  - Technical lane large_cap_parabolic ceiling: raw score ≤ +1 + 強寫 extension_penalty_note
  - Red Team prompt 加 V3.17 cash conversion 攻擊限制 + transition_signature 攻擊指引
  - **Phase 3 Step 2 — 5-level penalty cascade (first match wins)**:
    1. structural_shift CONFIRMED + mr/contaminated → 0.925 + downgrade
    2. transition_signature {mix_only, both} + valuation_confirmed_transition + mr → **0.95** (NEW)
    3. structural_shift CANDIDATE → 0.925
    4. STRONG_COUNTER + pure_forward → 0.85
    5. otherwise (catch-all STRONG_COUNTER) → 0.85
  - `valuation_confirmed_transition` deterministic gate (V3.17 — `lane_score` NOT a gate,
    uses `transition_dissent_basis != "thesis_fundamental"`)
  - Staleness alert: `abs(bundle.mtime − forecaster.mtime) > 6h` 或 inconsistent →
    terminal HIGH alert + `session_export.transition_data_stale_or_inconsistent=true` +
    禁用 cascade rule #2(其他規則照走 — 不全面退化 to NONE per Gemini G2 review)
- **`apply_det_shadow.py` 主邏輯不動** (Codex 反駁: sidecar metadata, line 11
  contract preserved); 不另立 valuation-anchor classifier class — 沿用既有
  `pure_mean_reversion / contaminated / pure_forward`
- **29 new unit tests**:
  - `skills/earnings-analyst/tests/test_v3_17.py` (20): transition_signature 5 態 + cash
    conversion enum 4 case + business_mix overlay 3 tier + WC diagnostics DPO 3 fallback +
    score_quality directional flags
  - `skills/earnings-valuation-forecaster/tests/test_v3_17.py` (9): transition cascade
    first match wins + EMERGING/ESTABLISHED matrix labels + dual-field achieves_if

### Why

NOK image_review session (`reports/2026-05-23_NOK_image_review.md`) 暴露的 3 類**通用**
系統盲點:
1. 現金流品質校對缺方向性 → narrative 股(OpCF >> NI)被錯誤扣分
2. 轉型估值用 EPS × PE 對 hyper-growth / business mix 改變的公司產出失真 PT
3. 動能 warning 對 +100% above SMA200 不分市值 → 大型股 crowded trade 風險被掩蓋

**This is NOT NOK-specific calibration.** 設計經 5 輪 Codex round-trip (v1→v5) +
Gemini 第三方 review + 我中介 review + 16 條議題收斂全部 settle。Cohort 18-ticker
calibration + MCP/script alignment audit defer to V3.17.1 (governance sub-wave).

### Verified

- 29 new tests pass + 21 existing narrative-pulse tests pass = **50/50 PASS**
- NOK live re-run on existing cache: composite **43 → 47** (quality 26→30, 因為 clean
  positive gap 不再被誤扣 −4),verdict 維持 WEAK (47 < 50),transition_signature=neither
  (NOK 在 FMP free-tier 拿不到 quarterly product segment,所以 mix=STABLE 合理)
- NOK forecaster: `transition_case=false` (mix=STABLE, signature=neither);scenarios dual-field 並存
- NOK momentum-monitor: `warnings = [..., 'parabolic_blowoff_risk', 'large_cap_parabolic']`
  ($83.5B market cap × am200=113.92% → triggered, 對齊設計)
- protocol .md prompt 改 — 全 syntax-valid (markdown 結構未破壞)

### Deferred (V3.17.1 governance sub-wave)

- 18-ticker calibration cohort (NVDA-2023 / META-2022 / SHOP-2020 / MSFT-2024 / JNJ-2023 /
  KO-2024 / INTC-2023 / VFC-2022 / WBA-2023 / PTON-2022 / RIVN-2023 / SPCE-2022 /
  SBUX-2022 / DIS-2023 / CRM-2022 / AMD-2019 / MU-2022 / FCX-2020)
- MCP/script alignment audit (5 ticker × {MCP, FMPClient} core metric diff > 1% alert)
- Acceptance criteria: ≥ 14/18 directionally correct + 新 flag 觸發率 < 30% +
  `transition_data_stale_or_inconsistent` 觸發率 < 5%

### Deferred (V3.18+)

- `systemic_backdrop` 完整 score (AI bubble proximity + VIX regime + Fed funds regime)
- Large-cap parabolic 閾值 backtest (50 sample 校準)
- `narrative-pulse-detector` news mention schema drift fix

---

## [3.16.2] — 2026-05-24 — Narrative Pulse: Codex review fixes

### Fixed

- **Codex #1 — `classify({})` no longer mis-labels as Stage 5.** When all stage
  confidences scored 0 (empty / failed inputs), the fallback used
  `max(all_scores)` which picked `distribution` (first dict key) as the winner
  — producing `stage=5, recommended_action=exit_or_short_candidate`. Now
  returns `stage=None, recommended_action=insufficient_data` with a
  `next_warning_condition` explaining what input gates failed.
- **Codex #2 — `None → 0` coercion in rule evaluator removed.** Previously
  `_eval_rule` did `{k: 0 if v is None else v}` for safety, but this silently
  turned `breadth_200dma_pct=None` into `0` and triggered the Stage 1 washout
  boost (rule was `breadth_200dma_pct is not None and breadth_200dma_pct <= 30`
  — `0 is not None` is True). Now None is preserved verbatim and any
  arithmetic/comparison touching None raises `TypeError`, caught and returned
  as `False`. Rules can still opt-in to "missing == 0" via
  `(field or 0) <= threshold`.
- **Codex #3 — cache invalidation now honors `weights_version`.** `pulse.py`'s
  `_cache_fresh()` and `dashboard_server.py`'s on-demand endpoint now compare
  the cached JSON's `weights_version` against the current `stage_weights.yaml`.
  Editing the YAML mid-day will refresh on next read instead of returning
  stale classifications. CHANGELOG promise (V3.16.0) now matches behavior.
- **Codex #4 — `render.py` partial-quote crash on `None` fields.** Replaced
  inline f-string formatting (`q.get('volume', '?'):,`) with None-safe helpers
  `_fmt_int / _fmt_money / _fmt_pct / _fmt_market_cap` — missing values render
  as `—` instead of raising `TypeError: unsupported format string passed to
  NoneType`.

### Improved

- **`pulse.py` critical-input gate:** OHLCV is the only truly required input.
  If `input_health.ohlcv_ok=False`, `pulse.py` now skips `classify()` entirely
  and writes a clear `insufficient_data` verdict + the original fetch failure
  reason. Previously partial bundles flowed into classify and emitted
  low-confidence guesses.
- **Codex #5 — `batch_scan.py` reads `weights_version` from `load_weights()`**
  instead of hardcoding `"v1.0"`. Dashboard's `last_updated` strip now reflects
  the actual config version after a `stage_weights.yaml` edit.
- **Codex #6 — `pt_raise_30d` semantic clarity.** `fetch_pt_cadence` uses
  Finnhub `/stock/upgrade-downgrade` which captures any positive analyst
  action (upgrade / raise / initiate-buy), not strictly a PT raise event.
  Bundle now emits both names — legacy `pt_raise_30d/60d` (kept for YAML
  rules + existing tests) and the more accurate
  `analyst_positive_actions_30d/60d` — with a code comment flagging future
  FMP `historical-grades` integration for true PT-raise event stream.

### Added

- **5 new unit tests** (16 → 21) covering all four Codex findings:
  `test_empty_components_returns_insufficient`,
  `test_all_zero_components_returns_insufficient`,
  `test_breadth_none_does_not_trigger_washout`,
  `test_vix_none_does_not_trigger_dampen`,
  `test_render_handles_none_quote_fields`.

### Deferred (Codex suggestions #7 + #8 — V1.2 scope)

- **stage_weights profile split (`default` + `high_beta_ai_infra`)**: the
  current single-profile thresholds were calibrated against NOK 5/22 and may
  be too sensitive for mature large caps or too lax for true meme stocks.
  Requires user input on which ticker classes to profile and which thresholds
  to relax/tighten — left for V1.2 after collecting more live samples.
- **`fundamental_overlay` (CF quality + valuation pressure + analyst PT vs
  price + recent-earnings narrative support)**: would let the skill say "tape
  says Stage 4 狂熱, but fundamentals justify multiples" — useful nuance, but
  conflates the pure tape/voice signal that V1.0 deliberately isolates. If
  added, must be a separate overlay layer, not folded into stage classifier.

### Verified

- 21/21 unit tests pass: `python3 skills/narrative-pulse-detector/tests/test_stage_classifier.py`
- Live NOK (with all fixes): Stage 4 狂熱, conf 0.70, E[R] -13.4% — **unchanged
  from pre-fix runs** confirming no regression
- Render markdown sample: `$15.47 / 9.10% / 126,178,313 / $15.78 / $4.00 / $83.6B`
  — None-safe formatters working

---

## [3.16.1] — 2026-05-23 — Narrative Pulse: Gemini review fixes

### Fixed

- **`consecutive_overbought_days` docstring vs implementation mismatch** (Gemini #2):
  the function declared a `reset_below=50.0` parameter and docstring claimed
  "Resets when RSI drops below `reset_below`", but the implementation simply
  `break`s on any `RSI < threshold`. Two metrics are now emitted explicitly:
  - `rsi_overbought_days` (strict consecutive — unchanged behavior, fixed docstring)
  - `rsi_overbought_episode_days` (new, loose count — tolerates 1-3 day buffer
    dips into the 50-70 zone, breaks only when RSI drops below `reset_below`)

  Both are written to `components` of every pulse cache. NOK 5/22 live values:
  strict=1 vs episode=21 — explains why NOK report §10.2's "連 17 日" intuition
  matched the loose count even though strict was much smaller.

### Added

- **Macro overrides** in `config/stage_weights.yaml` (Gemini #3): post-classification
  `expected_return_pct` adjustments based on bigger-picture macro state:
  - `vix_elevated_stage_4_5`: VIX ≥ 25 → dampen Stage 4/5 E[R] by -5%
  - `breadth_washout_stage_1`: breadth_200dma_pct ≤ 30 → boost Stage 1 E[R] by +3%

  `classify_stage.classify()` now applies any matching overrides and emits
  `expected_return_pct_pre_macro` + `macro_adjustments_applied` alongside the
  final `expected_return_pct` so audit trail is preserved. `pulse.py` propagates
  both fields to the cache JSON.

- **Stage 4 `rsi_overheated` condition** extended to use the new loose count
  as primary signal: `rsi_overbought_episode_days >= 10 or rsi_overbought_days
  >= 5 or rsi_peak_recent >= 80`. Three-way OR keeps detection robust whether
  the rally has been clean (high strict streak), choppy (high episode count),
  or just had a recent extreme spike.

- **6 new unit tests** (10 → 16): `test_vix_elevated_dampens_stage_4`,
  `test_low_vix_no_adjustment`, `test_washout_boosts_stage_1`,
  `test_strict_vs_loose_basic`, `test_loose_breaks_on_floor_drop`,
  `test_empty_series_returns_zero`.

### Not Changed (Gemini #1 was a false alarm)

Gemini suggested `dashboard_server.py`'s synchronous `subprocess.run` in
`/api/narrative-pulse/ticker/<T>` could block the whole Dashboard. Verified
that `dashboard_server.py:25` already imports `ThreadingHTTPServer` and
`:3804` instantiates the server with it — per-request threading is in place,
so the 120s timeout window cannot block parallel API calls. No change needed.

### Verified

- 16/16 unit tests pass
- Live NOK: Stage 4 狂熱, conf 0.70, E[R] -13.4% (unchanged — VIX 16.7 below
  25 threshold so no macro override applied, consistent with prior runs)
- Live NOK cache now carries `rsi_overbought_episode_days=21` (resolves the
  apparent inconsistency between the NOK report §10.2 claim and the strict
  streak of 1)

---

## [3.16.0] — 2026-05-23 — Narrative Pulse Detector V1.0

### Added

- **New skill `skills/narrative-pulse-detector/`** — 熱潮股 / 話題股短期上漲潛力探測器
  - `SKILL.md` + `schema.md` + `config/stage_weights.yaml` (5-stage thresholds, user-tunable)
  - `scripts/fetch_inputs.py` — 8-input integrator (5 reused + 3 new)
    - Reuses: `momentum-monitor.technical_core` (OHLCV/RSI/SMA), `market-top-detector.fmp_client` (quote),
      `market-top-detector.distribution_day_calculator` (forked per-stock), `finnhub-client.upgrade_downgrade`
      (PT cadence, graceful 403 fallback), `scripts/break_news/social_sources.fetch_reddit/fetch_hacker_news`
      ($TICKER cashtag filter)
    - New: consecutive RSI overbought days, close-to-close impulse density (4w), news mention aggregator
      (source diversity index), per-stock distribution day (O'Neil fork)
  - `scripts/classify_stage.py` — 5-stage classifier (蘊釀 → 啟動 → 加速 → 狂熱 → 分配) with R/R
    quantification; pure function + YAML-driven thresholds; mini-DSL rule evaluator
  - `scripts/pulse.py` — single-ticker CLI entry, 4h cache TTL
  - `scripts/batch_scan.py` — daily batch entry, pulls thematic-screener top movers
  - `scripts/render.py` — JSON → markdown report
  - `tests/test_stage_classifier.py` — 10 unit tests (NOK Stage 4, NOK_STAGE5, MSFT mature, brewing
    fixture, expected_return math)
- **Dashboard surface** (dual-track per user request):
  - `radar.html` — new `#npd-section` with 3-column rankings (top_risk / top_opportunity /
    watch_distribution_imminent), ad-hoc ticker input + 探測 button, side panel with full scenarios
  - `index.html` — Hero 下 mini-strip showing top 3 risk + top 2 opportunity, click → jump to
    `radar.html#npd-section`
- **Server endpoints** in `dashboard_server.py`:
  - `GET /api/narrative-pulse/data` — serves `Dashboard/narrative_pulse.json`
  - `GET /api/narrative-pulse/ticker/<T>` — on-demand single-ticker (cache hit if < 4h, else
    subprocess dispatch with 120s timeout)
  - `SCRIPT_PROTOCOLS["narrative_pulse"]` entry for protocol-style dispatch
- **`daily_update.sh` Step 9** — runs `batch_scan.py --top-n 30` → writes
  `Dashboard/narrative_pulse.json` (~5-10 min, non-fatal). `[8/8]` renamed to `[8/9]`.

### Why

NOK image_review report (`reports/2026-05-23_NOK_image_review.md` §10-11) surfaced 7 dimensions
that no existing tool tracked: 連續 RSI 超買日數、價/SMA200 拉伸倍數、impulse-day 密集度、
per-stock distribution day、sell-side PT raise 速度、retail $cashtag mention 量、media source
diversity + narrative stage 1-5 分類 + 4-scenario R/R 量化. Critical signals for judging whether
a hype stock's rally still has runway — but `momentum-monitor` covers tape flow,
`short-term-target` covers 1d/5d/15d tactical prediction, `thematic-screener` covers theme
rotation. None frame a single ticker against narrative trade lifecycle.

V1.0 ships as **exploratory tier** (same level as Nexus / Break News) — does **not** feed
`investment_protocol_v5_0` Arbiter, does **not** auto-adjust positions. Stage thresholds in
`config/stage_weights.yaml` are user-tunable per `feedback_exploration_phase.md` design principle.

### Verified

- 10/10 unit tests pass: `python3 skills/narrative-pulse-detector/tests/test_stage_classifier.py`
- Live NOK pulse: **Stage 4 狂熱後段, confidence 0.70, E[R] -13.4%** — matches NOK report §10 exactly
- Live batch_scan (3 tickers): NOK Stage 4, MSFT Stage 1, PLTR Stage 1; rankings populate correctly
- All 5 modified Python files + bash script + YAML config parse clean

### Errata

`reports/2026-05-23_NOK_image_review.md` §10.2's claim "連續 17 個交易日 RSI ≥ 70" was a manual
calculation error. Actual max RSI(14) streak ≥ 70 was the 5/1-5/6 window (~5 days, peak 83.0).
The Stage 4 conclusion remains correct — driven now by the `rsi_overheated` condition
(`rsi_overbought_days >= 5 OR rsi_peak_recent >= 80`), which the live pulse confirms via the peak
path.

---

## [3.15.2] — 2026-05-21 — Break News V4 final-gate polish

### Fixed

- Depth-policy `is_high_priority_item` `abs(shallow_score)` threshold dropped
  from `7.0` to `3.0`. The Stage 1 triage scorer emits values on a ~0–3 scale
  (`abs(s) >= 1.5` important, `>= 3` strong); the old gate never fired, so the
  shallow-score signal was silently ignored.
- Futu Push round-cap regression: `item.get("source") == "Futu Push"` compared
  a dict to a string, so the `MAX_ROUNDS_FUTU=2` cap never applied. Now reads
  `(item.get("source") or {}).get("name")`.
- Mega-cap ticker match in depth policy is now case-insensitive (`re.IGNORECASE`).
  Headlines occasionally render tickers as `Nvda`, which the strict pattern
  silently dropped from high-priority.

### Added

- `RELATION_EVIDENCE.break_news_provisional` style in `page-supply-chain.js`
  (amber icon `◐`, "突發暫定" label, BN source-count suffix) so V4 provisional
  edges render with their own badge instead of falling back to raw key text.

### Why

Final-gate review of the V4 → V4-review-fixes stack found four downstream gaps
that would have silently degraded the new depth policy and supply-chain UI.
None block release, but each subtracts signal from the V4 KG-first design.

---

## [3.15.1] — 2026-05-21 — Break News V4 review fixes

### Fixed

- Fixed Break News universe ticker loading for `Dashboard/heatmap_universe.json`
  dict-list shape, so neutral early-stop no longer treats tracked tickers as
  absent.
- Persisted provisional direct-edge metadata through Nexus `Edge.to_json()` and
  `merge_edges()`, including `is_break_news`, `provisional`, `support_count`,
  `cross_item_count`, and `confidence_avg`.
- Made supply-chain provisional evidence relation-aware and direction-aware:
  unrelated `COMPETES_WITH` / narrative edges or reversed `SUPPLIES_TO` edges no
  longer corroborate a YAML supply-chain hop.
- Restored transition fallback for legacy Break News relations missing
  `support_count` by treating them as support `1`.

### Added

- Added focused regression tests for Break News V4 summary aggregation, universe
  loading, direct-edge gating/metadata, Edge metadata preservation, and
  supply-chain provisional evidence compatibility.

### Why

Codex review found that the V4 data path could silently drop provisional
metadata and over-credit pair-only Nexus evidence. This patch keeps the KG
integration conservative while preserving the new richer debate summaries.

---

## [3.15.0] — 2026-05-21 — Break News Debate V4: KG-first & Supply-chain Integration

### Added

- **Phase 2 Direct Edge Loading**: Introduced a feature flag and CLI flag (`--enable-direct-edge` in `build_graph.py`) to support provisional direct ticker-to-ticker edge loading. This parses the structured `merged_relations` from debate logs, applies cross-item/same-item support count gates (`support_count >= 2` or `cross_item_counts >= 2`), normalizes direction (`CUSTOMER_OF` -> `SUPPLIES_TO`), caps weight at `0.15`, and tags edges as provisional break-news relations.
- **Three-Level Evidence Weights in Supply Chain**: Implemented a prioritised evidence ranking in `supply_chain.py`'s `enrich` logic: `corroborated_relation` (1.0 weight for digest co-mentions >= threshold) > `llm_relation` (0.4 weight for LLM drafted skeletons) > `break_news_provisional` (0.2 weight for provisional break news edges in the Nexus graph).

### Changed

- **Debate Prompt Compression & V4 Sliding Window**: Transitioned `prompts.py` to use a `compact_thread_formatter` sliding window (`kg_state` containing tickers, themes, relations, unresolved gaps, recent claims + full verbatim of each agent's last comment).
- **Summary Aggregation Metrics**: Upgraded `build_summary_block()` to perform advanced aggregation including `support_count`, null-safe `confidence_avg`, evidence snippet cropping (up to 3 distinct snippets sorted by confidence/round, each <= 200 chars), and round-by-round final take tracking (`final_takes_by_round`).
- **Dynamic Depth Policy & Early-Stop in `debater.py`**: Added an priority-aware depth control that defaults to 2 rounds (4 calls) for normal news and up to 3 rounds (6 calls) for high-priority news. High priority is dynamically triggered by source (Futu Push / Bloomberg / credibility == HIGH), high triage shallow score, binary flag, sector top 5 tickers, or domain pattern hits >= 2. Added dynamic early-stop at Round 1 on low relation density, consensus neutrality without universe tickers, or both done.
- **Strict V2 Gate Transition**: Updated `validate.py` to gracefully fallback for older records while strictly enforcing V2 schema validation (requiring V2 final takes, merged relations structures, confidence averages, etc.) on logs dated on or after `2026-06-20`.

### Why

Shifts the Break News debate framework from generic market commentary to a rigorous, quality-gated, and cost-controlled KG-first architecture that directly fuels the Knowledge Graph and Supply Chain pages without hallucination risk.

---

## [3.14.8] — 2026-05-21 — Supply-chain scrollbar polish

### Fixed — horizontal scrollbar height + always-visible scroll on supply-chain

- `Dashboard/style.css` `::-webkit-scrollbar` had `width: 6px` only, which applies
  to vertical bars. Horizontal bars fell back to the browser default (~16px on
  macOS / Chrome), looking chunky next to the slim vertical bar. Added
  `height: 6px` so both axes are 6px. Also added Firefox `scrollbar-width: thin`
  + `scrollbar-color` for parity.
- `Dashboard/supply-chain.html` `.sc-scroll` changed `overflow: auto` →
  `overflow: scroll` so both scrollbars are always visible. At narrow viewports
  the auto-hidden bars left users unable to tell the canvas could be scrolled
  — typical CPU-supply-chain layout extends well past viewport.
- Added `max-width: min(1400px, calc(100vw - 320px))` on `.sc-scroll` as a hard
  safety cap so the right-edge scrollbar never lands past the viewport even if
  the flex/max-w-1400 chain has a quirk at certain resolutions.

### Why

Visible-bar-mismatch (6 vs ~16) was jarring on supply-chain page. Auto-hide on
narrow viewports made users miss the "can scroll right" affordance entirely.
Both changes touch CSS only — no logic change.

---

## [3.14.7] — 2026-05-21 — Sector v3.14.6 follow-up: FTD source_file test coverage + log honesty

Codex follow-up on the v3.14.6 ship surfaced 3 more nits. All addressed.

### Added — Test coverage for FTD `source_file` path (P2)

The most critical correctness fix in v3.14.6 was switching the FTD verbatim
assert from "latest cache on disk" to "the specific cache file recorded at
build time". That logic was inline in `main()` with no unit-test coverage,
so a future agent could quietly revert to `sorted(glob)[-1]`.

- Extracted the verifier into `verify_ftd_verbatim(phase0_ftd, root)` —
  pure function, takes explicit phase0_ftd dict + repo root, returns
  `list[str]` of error strings.
- `tests/test_gics_sector_audit.py` `TestVerifyFtdVerbatim` adds 6 cases:
  match returns no errors / mismatch hallucination detection / **anti-regression
  for "must use source_file not latest cache"** / legacy soft-skip /
  missing-on-disk soft-skip / no-FTD-cache-at-all hard error.

### Fixed — Log honesty on builder strict mode (P2)

v3.14.6 changelog + SESSION_NOTES said "builder / validator / pytest pass
`strict=True`". Actual code: `build_sector_intel.py:289` calls
`canonicalize_sector_name(raw_name)` without `strict=True`. This is by
design — builder absorbs LLM-emitted aliases (`"Financial Services"` →
`"Financials"`) so downstream cache lookups hit; if the LLM emits an
uncanonicalizable name, the cache lookup hard-fails one line later. **The
validator is the schema gate that catches drift**, not the builder. Log
amended.

### Fixed — SESSION_NOTES test count (P3)

v3.14.6 SESSION_NOTES said `pytest tests/test_gics_sector_audit.py 4/4
pass`. Actual was 12/12 (was 2 before v3.14.6 + 10 new). v3.14.7 now reports
18/18 with the FTD source_file additions.

### Why

These are docs / tests, not functional code changes — but they materially
affect the next agent's ability to trust the prior changelog and to maintain
the v3.14.6 correctness fix without regression. Session notes are the
hand-off cache; precision matters.

---

## [3.14.6] — 2026-05-21 — Sector validator hardening + honesty fixes

Follow-up to v3.14.5 — codex review caught 4 issues. All addressed.

### Fixed — FTD validator now uses build-time source_file, not latest cache

- `build_sector_intel.py` records the actual FTD cache file consumed at build
  time into `_phase0.ftd.source_file` (repo-relative path from
  `phase0_read_caches.py` `layers.ftd.file`).
- `validate_sector_intel.py` reads **that** file for the verbatim assert, not
  the latest snapshot in `sector/ftd_cache/`. The FTD daemon writing a new
  snapshot between build and validate no longer flags a legitimate report as
  a "hallucination".
- Legacy reports without `source_file` get a stderr warning + skip (never
  hard-fail against a possibly-mismatched latest snapshot).

### Added — Validator canonicalizes sectors[].name (P2-1)

- `validate_sector_intel.py` now imports `sector_utils.canonicalize_sector_name`
  and runs it with `strict=True` on each `sectors[].name`. LLM emitting display
  / prose / whitespace-padded variants (`"Financial Services"`, `" Technology "`)
  trips a schema fail at the gate.
- Closes the loop on v3.14.5's alias module — the previous changelog claimed
  validator was canonicalized, but the diff didn't add the import. Fixed here.

### Added — `sector_utils` strict mode (P2-2)

- `canonicalize_sector_name(name, *, silent=False, strict=False)` — new
  `strict` kwarg raises `UnknownSectorError` instead of falling back.
  **Validator + pytest** pass `strict=True`. **Builder / digest / fetch keep
  lenient canonicalization by design** — builder absorbs LLM-emitted aliases
  (`"Financial Services"` → `"Financials"`) so that valuation cache lookups
  hit; if the LLM emits a name that doesn't even canonicalize cleanly, the
  cache lookup hard-fails one line later. Validator is the schema gate that
  catches drift LLM didn't pre-canonicalize.

### Fixed — Honesty on calculator dual-run promotion criteria (P1-2)

The v3.14.5 changelog cited "N=5 sessions, 0 hard diffs > 1.0, ≤2 soft diffs,
0 penalty drifts" as enforced criteria. The calculator only checks the
**current** run — there is no history persistence. Rewording (here and in
SESSION_NOTES.md) to say: "per-run shadow check; N=5 promotion thresholds are
documented but not persisted yet — implementing the history file is a future
patch." `SECTOR_CALC_STRICT=1` still fails-fast on the current run; it does
not aggregate across runs.

### Why

Codex review of the v3.14.5 ship surfaced two correctness issues (FTD
race-condition + validator canonicalize claim) and two overclaim issues
(N=5 criteria not persisted + sector_utils not actually fail-fast). v3.14.6
closes the loop on all four.

---

## [3.14.5] — 2026-05-21 — Sector protocol precision alias & score calculator shadow-run

### Added — Unified sector alias module (SECTOR_ALIASES)
- Created a shared explicit lookup module `sector/lib/sector_utils.py` mapping GICS prose names, display names, and FMP names to 11 Canonical Keys.
- Unified name canonicalization inside `sector_digest.py`, `build_sector_intel.py`, `step6_overlay.py`, and `fetch_sector_valuation.py` to eliminate name drift bugs (like Financials n/a).
  (Validator canonicalization shipped in v3.14.6 — the original v3.14.5 changelog incorrectly claimed it landed here.)

### Added — Score calculator with shadow run
- Implemented `sector_score_calculator.py` with multi-stage scoring verification: `base_score`, `pre_step6_score`, and `post_step6_score`. (**Note: This is Phase 1 = summation & post-scaling sanity check; Phase 2 is left for future Step 1-4 multiplier replication**).
- Added dynamic FRED cyclic skip rules and valuation penalty checks.
- Enabled Shadow Mode comparison inside `build_sector_intel.py`. **Per-run** check; the documented promotion thresholds (N=5 sessions, 0 hard diffs > 1.0, ≤2 soft diffs, 0 penalty drifts) are NOT persisted across runs in this version — history accumulation is a future patch (see v3.14.6 honesty note).

### Added — FTD verbatim assert and path safety
- Enriched `build_sector_intel.py` to bridge `ftd_timeline` into `_phase0.ftd`.
- Implemented precision string assertions in `validate_sector_intel.py` against disk FTD cache to prevent LLM hallucination and rewriting. (v3.14.6 changed this from "latest snapshot" to "build-time source_file" to avoid race conditions — see that section.)
- Fixed FRED cache path lookup in `step6_overlay.py` using repo-root locator.
- Added pytest skip-if-no-cache decorator in `tests/test_gics_sector_audit.py` to prevent CI failure on empty caches.

### Why
- Deterministic calculation prevents random LLM math drifts, while unified aliasing stops name mismatches. Skip-on-no-cache decorators maintain CI stability without requiring cached files.

---

## [3.14.4] — 2026-05-21 — Supply-chain FMP company verification + relation evidence


### Added — FMP company/ticker verification

- `scripts/nexus/supply_chain.py` now enriches supply-chain nodes at serve time with
  `verification_level`, `verification_reasons`, `fmp_profile`, `fmp_peers`, and
  `data_quality.verification_breakdown`.
- FMP verification is explicitly company-level only. It does not claim that a
  supplier/customer relation is verified.
- Added shared file-backed cache under
  `skills/_shared/fmp_supp_cache/supply_chain/`:
  `profile/<TICKER>.json` TTL 7d, `peers/<TICKER>.json` TTL 24h,
  `search_name/<sha12>.json` TTL 24h.

### Changed — Quota-safe lookup rules

- Profile lookup is batched, cache-first, and shared by ticker instead of chain.
- Daily budget gate defaults to `FMP_SUPP_DAILY_BUDGET=150`; the counter is
  persisted in `_budget_<YYYY-MM-DD>.json` and resets on UTC day boundary.
- API key absence, exhausted budget, 403/429, or network failure degrades to
  `fmp_unavailable` without breaking the page.
- Ticker disambiguation now uses US exchange allowlist plus hand aliases for ADR /
  class-share cases such as TSMC→TSM, GOOG/GOOGL, and BRK class shares.

### Added — Relation evidence track

- Supply-chain edges now get `relation_evidence` from strict 30-day digest
  co-mentions: both endpoint tickers must appear in the same verdict
  `tickers_mentioned[]`. Prose scanning is intentionally not used.
- Threshold is `>=3` co-mentions for `corroborated_relation`; below that remains
  `llm_relation` with UI wording that low-volume edges are not necessarily false.

### Changed — Dashboard verification UI

- Node cards show one primary company-verification badge. Existing grounding
  remains visible only in the detail panel to avoid duplicate/conflicting badges.
- Detail panel shows FMP profile summary, alias used, peers, verification reasons,
  and relation-evidence badges on upstream/downstream edges.
- Legend tooltips document the distinction between company verification and
  relation evidence.

### Tests

- Added `tests/test_supply_chain_enrichment.py` for no-key fallback, alias profile
  matching, budget exhaustion, name-match fallback, and strict digest co-mentions.

### Why

供應鏈 YAML 仍是 LLM 草稿;本版把「公司存在」與「關係佐證」拆成兩條清楚的 evidence track,
避免 FMP profile 被誤讀成 supply-chain relation verified，同時用 batch/cache/budget gate 防止
FMP quota 被一頁供應鏈燒光。

## [3.14.3] — 2026-05-21 — News pipeline Stage 1 quality + validator cross-check

### Added — Stage 1 hard-block negative content (P0a)

- `news/scripts/stage1_triage.py`:新 `_BLOCK_PATTERNS` 三類 regex,命中即 drop
  (不進 verdicts,不進 stage2_items,不進 export):
  - `law_firm_solicitation`:Johnson Fistel / Schall Law / Rosen / Hagens Berman …
    + 通用 `securities class action investigation` / `encouraged to reach out`
  - `real_estate_pr`:Condominium / Penthouse + Debuts / Launches / Grand Opening
  - `personal_finance_advice`:`I inherited|Should I|My (husband|wife|parents)|
    Dear (Penny|Reader)|Ask the Expert`
- 每次 stage1 run 在 triage.json 加 `blocked_counts` 計數 + `items_blocked` 總數,
  validator 後續可以用此偵測規律性失常。

### Added — Headline-template dedup (P0b)

- 同一律所/PR 模板橫跨 N 個 ticker(`Johnson Fistel Investigates Losses at
  NVDA/TSLA/AMD`)以前獨立打分、可能 N 條全進 stage 2。新 `_headline_template_key`
  把 ticker / 金額 / 日期 / 星期 normalize 後比對,只留第一條,後面 dedup。
- triage.json 加 `items_dedup_dropped` + `template_dedup_dropped`。

### Added — Content-aware credibility downgrade (P0c)

- `effective_credibility(item, headline, summary)`:provider HIGH × press-release
  marker → MEDIUM;MEDIUM × press-release → LOW;opinion / personal-finance
  marker → LOW outright。
- Advancement gate 改用 `effective_credibility`,不再被 raw provider HIGH 短路:
  律所新聞掛在 GlobeNewsWire 上拿 HIGH 也會被 content marker 降回 MEDIUM。
- 每個 verdict 加 `effective_credibility` 欄,validator 可後續加 enum check。

### Changed — Env-tunable stage1 cap (P0d)

- `STAGE1_MAX_ITEMS` env(default 800)取代硬寫 `items[:313]`。raw 397 → 全 394
  scored(3 個 blocked),不再丟掉尾端 84 條。

### Changed — Rule-based news_type classifier (P1b)

- 新 `_CLASS_RULES` priority-ordered regex(earnings → corporate → monetary_policy
  → macro_data → geopolitical → sector_news),fallback 才走舊 keyword tally。
  原 bug `FLGT shareholder loss → monetary_policy` 因 priority 修掉。
- 既有 `classify_news_type(headline, summary)` 簽名不變,break_news poller
  imports 沿用。

### Changed — `headline_zh` null in Stage 1 (P0f)

- Stage 1 不再做 `headline[:150]` 英文 placeholder 假譯;`headline_zh = None`。
- Downstream digest LLM step 才對 top-N 跑翻譯(Wave 2 任務,本 patch 未實作)。
- `digest_output_schema.md` 接受 null。

### Added — Validator cross-check raw / triage / digest (P0e)

- `news/scripts/validate_digest_output.py` `_cross_check_files()`:讀同日
  `<DATE>_triage.json`,assert `digest.stage1_count == len(triage.shallow_verdicts)`
  + `deep verdict news_ids ⊆ triage.stage2_items`。
- Loose mode(legacy digest 無對應 triage):print note 跳過,不 hard fail。
- Strict mode(`NEWS_RUN_START_MS` 設定 = 今日 run):missing triage 即 hard fail。
- 新增 v3.14.3 telemetry 缺失(`blocked_counts` / `template_dedup_dropped`)時
  print note,不擋。

### Deprecated — `assemble_digest.py` 歸檔 (P1a)

- `news/scripts/assemble_digest.py` → `news/scripts/archive/assemble_digest.py`
  (git mv 留 blame)。
- 新 `news/scripts/archive/README.md` 列出封存理由。
- `news/news_protocol_v2.md` Phase 4 DO-NOT 表加 footnote 指向 archive 目錄。

### Tests (真測,不假側)

- **`tests/news/test_stage1_filters.py`**:31 個 unit tests,涵蓋 _is_blocked
  (3 類 × ≥3 positive + 1 negative)、_headline_template_key、
  effective_credibility、classify_news_type priority、_build_verdict integration。
- **`tests/news/test_validator_crosscheck.py`**:6 個 tests 用 tmp_path fixture
  寫假 raw/triage/digest,驗 consistent / mismatch / missing_triage 三組 path
  (loose + strict mode)、unreadable 案例。
- **`tests/news/test_pipeline_regression.py`**:1 個 real-data test 拿
  `news/news_logs/2026-05-20_raw.json` 跑完整 stage1,assert blocked_counts ≥ 1
  per category、無 Johnson Fistel/condo 漏網、items_scored > 313 證實 cap 已開。
- `pytest tests/news/ -v` → 38/38 passed in 0.08s。

### Why

Codex 對 news 頁面 review 指出 7 個 issue,真正最大弱點是 Stage 1 選題品質:
律所徵案 / Astoria condo PR / 個人理財 fluff 經常 advance 到 Stage 2 deep
debate,4-agent debate 浪費最貴 token,還把垃圾新聞寫得像高價值分析。

具體案例(2026-05-20 production digest):
- `n0197` Johnson Fistel solicitation about FLGT → BEARISH -2.6 deep verdict
- `n0038` 「PARISIAN Condominium Debuts in Astoria」→ stage2 advanced
- `n0107`「I inherited a house, capital gains?」→ shallow_verdicts top 10

本 patch 在 Stage 1 入口 hard-block,真實重跑 2026-05-20 raw:
- 3 個 noise item 在 stage 1 即 dropped(law_firm/real_estate_pr/personal_finance 各 1)
- 2 / 5 stage2 deep slot 被換成 genuine signal(Dow -320pt / Schwab Q2 sentiment)
- items_scored 從 313 → 394,尾端 84 條尾巴項終於進 advancement gate

Wave 2(lane completeness validator + LLM 翻譯 top-10 digest)留下次。

Plan 全文:`~/.claude/plans/llm-llm-queue-pythone-script-whimsical-beacon.md`

---

## [3.14.2] — 2026-05-20 — Skills × Codex compatibility wave 1

### Changed — market-top-detector doc clean-up (Wave 1.1)

- `sector/market_top_yfinance.py`:sys.path 從 `~/.claude/skills/...` 改為 repo-local
  `skills/market-top-detector/scripts/`(同 v3.14.1 daily_update fix 的對應修正);
  新增 `SKILL_SCRIPTS_PATH` env override。
- `skills/market-top-detector/SKILL.md`:重寫「Execution Workflow」段,把
  canonical entry 改為 `sector/market_top_yfinance.py`(daily_update Step 3 早就
  在用)。WebSearch 從必需降為 optional CLI flags:`--breadth-50dma` / `--put-call`
  / `--margin-debt-yoy` / `--vix-term`,缺失欄位寫進 `data_quality.missing_optional`。
- Production / Codex / cron 不再需要 WebSearch 即可跑;Claude 仍可 WebSearch 補
  optional 提高精度。

### Added — theme-detector narrative confirmation sidecar (Wave 1.2,evidence-grounded)

- 新 script `skills/theme-detector/scripts/narrative_confirm.py`:
  - 走 `model_router.run_role("narrative_confirm", ...)`,codex/claude/gemini
    任一都能驅動。
  - **Evidence-grounded prompt**(codex review #1+#2 修正): 從
    `news/news_logs/*_digest.json` 最近 14 天 verdicts 撈出每個 theme 的候選
    evidence(按 representative_stocks ∩ tickers_mentioned 或 industries ∩
    affected_sectors),作為 LLM 的**封閉**候選集。Prompt 強制模型只能引用提供
    的 news_id,不可發明 URL。
  - **`primary_evidence_id` 必須存在於該 theme 的 allowed_ids set** 才能
    `confidence_bump=medium->high`;否則 validator 自動降為 `none` 並計入
    `dropped_bumps_no_evidence`。修掉了「模型靠記憶/幻覺 URL bump」的 P0 風險。
  - 讀最新 `theme_detector_*.json`,top-5 themes 跑 narrative 確認,寫 sidecar
    `theme_detector_<ts>.narrative.json`(`confirmations[]` + `narrate_mode` +
    `model_used` + `bumped_count` + `dropped_bumps_no_evidence`)。
  - Router 全失敗 → `narrate_mode=skipped`,輸出空 bump,不報錯。
- **`bridge.py` 接 sidecar consumer**(codex review #3 修正):
  - 新 `load_theme_narrative_bumps()` 讀 sidecar,輸出 `data["theme_narrative_bumps"]`
    給前端(`bumps_by_theme[theme_name] = {confidence_bump, rationale, primary_evidence_id}`)。
  - `load_theme_overrides()` 自動套用 bump:對 paradigm-shift 主題,有 bump 時
    輸出 `confidence: "High"` + `narrative_bumped: true`,沒 bump 維持 quant Medium。
  - Sidecar 不存在 = `status: "no_sidecar"`,絕不報錯。
- `skills/theme-detector/SKILL.md` Step 4 改成 optional sidecar 流程。
- **不進 daily_update.sh** — 每日跑會吃 LLM quota;週末 cron / manual 才跑。

### Deprecated — supply-chain-event-analyst (Wave 1.3)

- `skills/supply-chain-event-analyst/SKILL.md` 頂部加 DEPRECATED banner,指向
  `scripts/nexus/supply_chain.py`(已是 production path)。SKILL.md +
  `chain_mapper.py`(2.7 KB FMP stub)保留作 read-only reference,不再開發。

### Chore — untrack 29 stale `*.pyc` (codex review #4)

`__pycache__/*.pyc` 早已 commit 進 repo(在加 gitignore 前)。本輪一次
`git rm --cached` 29 個 .pyc,gitignore 已有 `__pycache__/` 規則,未來不會
再進 git。Daemon-state(Dashboard/data.json / nexus_graph.json /
config/llm_usage.json)維持 tracked,但不進此 commit 範圍 — 純源碼/文檔 commit。

### Why

Codex(替代 Claude 作 LLM driver)無法用 WebSearch / 不能 in-conversation Write,
原 SKILL.md 寫死 Claude-only primitives 導致 5 個關鍵 skill 在 Codex 下半殘。
Wave 1 是低風險前菜(2 doc 清理 + 1 sidecar 新增),全部走 `model_router`
fallback chain(V3.7.0)讓三模型統一驅動。Wave 2 將處理 market-news-analyst
fetch.py 主線化,Wave 3 處理 earnings-analyst narrate via router。

Codex 對 Wave 1 review 提出 4 點(2× P0 + 1× P1 + 1× P2)在本版 ship 前全部修完:
prompt 加 evidence-grounding、bump 強制需 `primary_evidence_id ∈ allowed_ids`、
bridge.py 接 sidecar consumer、commit scope 清乾淨。

Plan 全文:`~/.claude/plans/llm-llm-queue-pythone-script-whimsical-beacon.md`

---

## [3.14.1] — 2026-05-20 — daily_update.sh 可靠性修正

### Fixed — 4 priority issues

- **Step 1 改 repo-local skill**: `~/.claude/skills/market-breadth-analyzer/...`
  改成 `skills/market-breadth-analyzer/...`,避免跨機器/跨 agent 跑不同版本。
  `plan_support_codex.md` cleanup item。
- **Step 4 FRED 包 `set +e`**: 原 `if [ $? -eq 0 ]` 在 `set -e` 下是死碼 —
  python 一旦非零 shell 立刻 exit,「非致命」comment 是錯的。包成
  `set +e ... FRED_RC=$? ... set -e` 後才真的非致命。
- **Step 5.5 加 `set -o pipefail`**: 原 `python ... | tail -3` 讓 `$?` 拿
  tail 的 rc(永遠 0),ETF refresh 失敗訊號被吞。加 pipefail 後
  `REFRESH_RC` 正確反映 python rc。
- **Step 8 移除 `pip install networkx`**: cron 內 install 會卡網路 / 污染環境 /
  失敗訊號被吞;`build_graph.py` 本就有 `pagerank_lite` fallback,移除即可。

### Added — FRED 結尾提示對應實際狀態

- Step 4 用 `FRED_STATUS=ok/failed/skipped` 三態追蹤;
  結尾 banner 依狀態顯示對應提示,不再固定講「FRED 已更新」誤導。

### Why

Codex review 指出 daily_update.sh 在 cron 環境的 4 個可靠性問題:跨機器路徑漂移、
死碼 if 檢查、pipe 吃 rc、cron 內 pip install。本 patch 全修。
Helper 化(`run_hard_step`/`run_soft_step`)、Step 8 默認降級 tier 1+2、
run summary log 等 second-phase 優化留下次。

---

## [3.14.0] — 2026-05-20 — Nexus graph: ticker-centric

### Changed — Knowledge Graph 改 ticker-only

- **`scripts/nexus/build_graph.py`** 加 `_to_ticker_centric()` collapse 步驟:
  prune 後把所有 catalyst / theme / sector / narrative / thesis 鄰居的 metadata
  aggregated 進每個 ticker 的 `metadata.recent_news[]` / `themes[]` / `narratives[]`
  / `sector`,然後 filter 只留 ticker 節點 + ticker↔ticker 邊。內部 Tier 1/2/3
  pipeline 不動 — 只動最終 output shape。
- 合成 `CO_THEME` 邊:同主題 / 同 narrative 的 top-12 tickers 之間建立稀薄的
  ticker↔ticker 邊(每個 ticker 限 top-3 themes),把原本只能透過 theme hub 連
  的關係轉成直接 ticker 對。
- 新 config flag `ticker_centric: true`(default) + `ticker_centric_recent_news_per_ticker: 8`。
  Legacy 多型別 graph 仍可用 `ticker_centric: false` 跑(主要給 Tier 3 LLM NER 除錯)。
- 重算 centrality:collapse 後 degree / pagerank 用 ticker-only 拓樸,
  不再被 theme / catalyst hub 中介膨脹。

### Added — Ticker tooltip + 細節面板顯示新聞

- **`Dashboard/page-graph.js`** `buildNodeTooltip()`:hover ticker 卡片顯示
  最近 6 則新聞(headline / verdict 顏色 / net_impact / 日期)+ themes chips
  + narratives chips + sector。
- 點 ticker 後右側 detail panel 加 News / Themes / Narratives block,同步資料。
- 邊顏色依 edge type 區分:PEER_OF(藍)/ SUPPLIES_TO(綠深)/ COMPETES_WITH(紅)
  / CO_DEVELOPS_WITH(琥珀)/ CO_THEME(琥珀淡 — 合成邊)。idle 也有薄底
  讓拓撲可見,hover 強化。
- 過濾列在 ticker-only 模式下改成 edge type legend(同業 / 供應 / 競爭 / 同主題),
  不再顯示無意義的 ticker checkbox。

### Why

User 反映知識圖譜需要的是 ticker↔ticker 關係,news 是 ticker 的內部資訊
(tooltip 上看),不該當成圖譜節點。原 V3.0 multi-type graph 800 節點裡 328 是
catalyst (news) 節點,把 ticker 之間的訊號淹沒。改 ticker-centric 後節點數 ~204
(只有 ticker),邊 ~704(PEER_OF 111 + CO_THEME 593),JSON ~649 KB
(原 2.5 MB),載入更快、拓撲清楚、news 仍在 ticker tooltip 可查。

---

## [3.13.0] — 2026-05-20 — Migrate gemini CLI to agy CLI

### Changed — LLM Execution Track

- **CLI Engine**: 將專案中所有原本呼叫 `gemini` CLI 的地方全部遷移至 `agy` (Antigravity) CLI。
- **`llm_drivers.py`**:
  - `GEMINI_BIN` 重新定義為 `AGY_BIN` (預設 `agy`)。
  - `run_gemini` 內部指令改為 `agy --print` 並加上 `--dangerously-skip-permissions`。
  - 移除 `--output-format json`，解析邏輯調整為直接處理 stdout 內容（相容原有的 3-stage JSON extractor）。
- **`dashboard_server.py`**:
  - `_protocol_command` 針對 `gemini` 模型改用 `agy` 執行軌道。
  - 更新 `GEMINI_BIN` 全域變數為 `AGY_BIN`。

### Why

配合系統環境升級，將舊有的 `gemini` 執行層統一替換為功能更強大且與當前 Agent 深度整合的 `agy` CLI，確保指令執行的一致性與權限管理自動化。

## [3.12.0] — 2026-05-20 — Cerebras supply-chain grounding

### Added

- `cerebras.yaml` 補上 OpenAI 750MW inference capacity、AWS Bedrock / Trainium × CS-3
  disaggregated inference、AlphaSense、Cognition、Meta Llama API、OpenRouter、Hugging Face 等
  2026 年公開商業節點。
- Supply-chain generator 會把本地 Nexus / news / break-news / reports 相關片段注入 prompt，
  讓新生成主題能看到最近 30-45 天左右的上市、客戶與合作訊號。
- 生成後新增 warnings：近期 context 提到的重要實體被漏掉、上市公司 ticker/listing 不一致、
  下游 customer/channel 太稀疏、未公開關係卻標成非 unknown stage。

### Changed

- Supply-chain prompt 強化 company/ticker 主題規則：優先納入 anchor customers、hyperscaler、
  API/channel distribution、上市狀態與近期商業合作；推測性 upstream 關係需在 note 標明。
- `SCHEMA.md` 補 `stage` 欄位與 note evidence hygiene 規範，維持現有 YAML/API 相容。

### Why

Cerebras 生成圖原本偏向硬體製造與舊研究客戶，漏掉 OpenAI/AWS 這類 2026 年核心商業節點。
本版修正現有圖，也讓後續供應鏈生成更不容易忽略最近新聞與上市狀態。

## [3.11.0] — 2026-05-20 — Invest V5.0.x decision quality patch

### Fixed — UI / decision cross-field consistency (A1)

- `validate_session_export.py` §9：拒絕 `final_action="CANCEL"` 與 `final_decision in {BUY, STAGED_ENTRY}`
  並存。新 session 在 schema 層擋住,不允許 BUY-side thesis 配 WAIT execution。
- `Dashboard/page-decisions.js` `buildCard()`:對遺留歷史中的不一致組合,卡片改顯示
  muted gray + dual label `CANCEL / BUY thesis`,不再透出 BUY 的綠色。

### Added — Phase 4.6 Valuation Decision Cap (A2)

- 新 Phase 4.6 段落寫入 `investment_protocol_v5_0.md`。觸發條件:
  - `fair_value_summary.anchors_available < 2` → `decision_cap_reason="insufficient_anchors"`
  - `fair_value_summary.confidence == "low"` → `decision_cap_reason="low_valuation_confidence"`
  - lane data_quality low → `decision_cap_reason="low_data_quality"`
- Cap 規則:`final_decision` 不得 `BUY`、`avg_confidence ≤ 0.65`、`position_size_pct ≤ 0.003`(30 bps)。
- 例外保留 `cap_override_reason` 欄位讓 PM 在重大 catalyst 時保留 STAGED_ENTRY,
  但 size / confidence cap 不解除。
- Schema 加 `decision_cap_active` / `decision_cap_reason` / `cap_override_reason` 欄位
  (V5.0.x optional,既有 entry 不受影響)。`validate_session_export.py` §10 強制 cap rules。

### Changed — History append 改 script 化 (A3)

- 新 script `investment/scripts/append_session_export.py`:
  - 從 stdin / `--from-file` / `--from-arg` 讀 entry JSON
  - `fcntl.flock(LOCK_EX)` 序列化、tmp + atomic rename 寫入
  - 自動鏡射 top-level `ticker` / `final_action` / `date`
  - 最小 shape gate;完整 schema 仍由 `validate_session_export.py` 把關
- Phase 5 Step 1 改成「PM 用 Write 工具把 entry 存到暫存,呼叫 script 寫入」,
  prompt 不再內嵌巨大 JSON,大幅降低 output token 與 malformed-JSON 重試成本。
- `register_thesis.py` 保持不變;順序在 protocol 內 sequential
  (Step 1 append → Step 6 register),不會與 append 競爭。

### Why

`分析 [TICKER]` 過去常出現「Phase 4.5 anchors<2 仍給高信心 BUY」+「`final_action=WAIT`
與 `final_decision=BUY` 並存」等決策品質問題。本 patch 在 schema、protocol、UI 三層
分別擋住誤判,並把 Phase 5 PM 手寫巨大 JSON 的低品質環節 script 化。為 V5.1 mode
切換與 shadow 校準鋪路 — V5.1 plan 見 `~/.claude/plans/llm-llm-queue-pythone-script-whimsical-beacon.md`。

---

## [3.10.0] — 2026-05-20 — Supply-chain generation queue

### Added — Truth Social Raw source

- Break News social sources 新增 Truth Social adapter，預設追蹤
  `@realDonaldTrump`，寫入 Raw 流作為政策/市場 headline source。
- 新 env：`BREAK_NEWS_TRUTH_SOCIAL_ENABLED`、`BREAK_NEWS_TRUTH_SOCIAL_HANDLES`、
  `BREAK_NEWS_TRUTH_SOCIAL_MAX_PER_CYCLE`、`BREAK_NEWS_TRUTH_SOCIAL_BASE`。
- Truth Social item 標記為 social source，Raw 全收；auto-debate 仍走 social gate，
  避免純政治/轉貼噪音直接消耗 LLM quota。

### Changed — Break News admission counts fallback routes

- poller 的 model-aware admission 不再只看指定 A/B voice 的剩餘 call；現在會模擬
  `run_with_fallback(preferred)` 的 route，使用每個 voice 第一個可用且至少夠
  `BREAK_NEWS_EST_CALLS_PER_DEBATE` 的模型 headroom。
- 例如 Break News pair 是 `codex×gemini` 且 Codex 已滿，只要 Claude 可用，
  Codex 那一席會用 Claude 的 headroom 支撐 automatic admission。
- state 新增 `fallback_backed_capacity`，前端 tooltip 顯示 fallback-backed。

### Added — 供應鏈生成進入全域 queue

- `POST /api/supply-chain/generate` 改為 enqueue `supply_chain_generate` job，
  背景 worker 執行 `_sc.generate(theme)` + `_sc.enrich()`，避免切頁造成同步
  request abort。
- 供應鏈生成沿用 `/api/protocol-queue` 與右下角 global pill，可跨頁顯示
  active / queued 狀態。
- supply-chain 頁送出後顯示 queued 狀態；若仍停在本頁，完成後自動刷新 chain
  list 並載入新生成主題。
- `_json()` 對 `BrokenPipeError` 靜默處理，避免正常切頁/abort 噴 traceback。
- pill detail 改優先顯示 queue label，例如 `🔗 Supply TPU`。

---

## [3.9.5] — 2026-05-20 — Raw stream published-time ordering

### Fixed — 未閘 Raw 流排序

Raw stream 原本用 `fetched_at` 排序，同一輪 poll 抓到的 item 會有相同時間戳，
導致畫面看起來不是照新聞時間排列。本版改為讀取時與寫入時都用 `published`
近到遠排序，缺 `published` 才 fallback `fetched_at`。

---

## [3.9.4] — 2026-05-20 — Break News model-aware admission

### Fixed — 硬 cap 餓死 debater

Break News poller 原本用 `BREAK_NEWS_DAILY_MAX_DEBATES` 當全域每日 item cap，
會出現 dashboard 顯示「今日剩餘預算 0」，但 settings 裡 Claude/Gemini/Codex
仍有 quota 的矛盾。本版把 automatic debate admission 改成讀 multi-model
governor 的真實可用 call：

- capacity 綁 Break News A/B voice，而不是三模型總 quota；Codex 保留 fallback
  buffer，不拉低正常 Claude × Gemini 容量。
- 一則 debate 依 `BREAK_NEWS_EST_CALLS_PER_DEBATE`（預設 6 calls）估算，不再把
  1 則新聞錯算成 1 call。
- admission 會扣掉現有 `pending_debate` backlog，避免 poller 連續 cycle 超發。
- disabled / cooldown / over-budget 的 voice 會讓 automatic admission 歸 0；手動
  raw debate 仍可由使用者觸發。
- `BREAK_NEWS_SESSION_RESERVE` 改為 call reserve；預設 25 calls 約保留 4 則
  debate，若要保留約 25 則 debate 應設約 150 calls。
- `BREAK_NEWS_DAILY_MAX_DEBATES` 預設 0，僅在設成 >0 時作 emergency item
  ceiling。
- Break News UI 顯示 `admission/model_capacity`，tooltip 顯示 pair 與 calls/debate。

---

## [3.9.3] — 2026-05-19 — Market-wide 公司名誤中修正

### Fixed — Dollar / Dow / S&P 裸 token 誤判

V3.9.2 收窄多數 broad-market regex 後，仍保留少數裸 token 可能誤中公司名：
`Dollar General` / `Dollar Tree`、`Dow Inc`、`S&P Global`。本版改為只匹配明確
指數或宏觀語境：

- `dollar` → `US dollar` / `dollar index` / `DXY`
- `dow` → `Dow Jones` / `Dow futures` / `DJIA`
- `s&p` → `S&P 500` / `S&P futures` / `SPX` / `SPY`

---

## [3.9.2] — 2026-05-19 — Market-wide 判定收斂

### Changed — 收窄 Market Consensus 的 broad-market regex

V3.9.1 的方向修正有效，但 market-wide regex 仍有裸 `rates/oil/gold/war/yield`
等寬匹配，可能把 `price war`、油金個股財報、公司貸款利率等個股新聞拉回
Market Consensus。本版收窄為明確宏觀語境：

- `interest rates` / `fed rate` / `rate outlook` / `rate cut|hike`
- `Treasury yields/market/auction/selloff/retreat`
- `oil prices` / `crude oil`、`gold prices`
- `trade war`、`Iran war`、`Ukraine war`

### Fixed — digest market-wide 判定帶入 affected sectors

committee digest 本身有 `affected_sectors` / `tickers_mentioned`，但 V3.9.1 沒把
它傳給 `_is_market_wide()`，導致 digest 的 multi-sector `sector_news` 比
break-news debate 更難進 Market Consensus。本版把 digest sectors/tickers 包成
entities 傳入，讓 high-quality digest 與 debate 使用同一套判定。

驗證：最近 12h market events 維持精簡（10 筆），合計貢獻約 `-3.7`；未見裸
keyword 導致的個股噪音回流。

---

## [3.9.1] — 2026-05-19 — Break News Market Consensus 校準

### Fixed — 市場共識線被個股 bullish 新聞推得過高

V3.9.0 後圖上 `Market` 仍顯示高情緒，但當日大盤已連跌。診斷發現 trend rollup
有三個偏多來源：

- `_event_weight()` 用 signed score 算權重，`BEARISH -2` 被 clamp 成最低權重
  `-0.25`，低估負面事件。
- digest 有 signed `net_impact_score` 但 `verdict` 缺失時，原本 sign=0，導致
  「futures fall / oil-yield shocks」這類負面 headline 不入帳。
- `__ALL__` 把所有個股/小題材 closed debate 等權加到 market line，POET / INOD /
  target increase 類個股 bullish 新聞把大盤線推高。

修正：

- `_event_weight()` 改用 `abs(score)`；方向只由 verdict 或 signed impact 決定。
- digest verdict 缺失時 fallback `sign(net_impact_score)`。
- `__ALL__` 改為 Market Consensus，只吃 macro / monetary / geopolitical / broad
  market headline；個股新聞仍進 sector/theme，不再等權推高大盤線。
- closed debate 時間優先用 source `published`，缺失才 fallback `fetched_at`。
- `trend-chart.js` label 改成 Market Consensus / Raw Pulse，meta 顯示
  `market_event_count/log_count`。

驗證：最近 12h market events 由泛新聞 67 筆縮到 11 筆，合計貢獻 `-4.2`；
`__ALL__` 尾端從約 `+0.87` 轉為約 `-0.81`，方向與盤面壓力一致。

---

## [3.9.0] — 2026-05-19 — Break News quota pacing + Raw Pulse

### Added — Raw Pulse 即時脈搏線

Break News source 擴充後，raw stream 已能更快抓到市場訊號，但趨勢圖原本只吃
committee digest + closed debate，LLM quota 用完後半天情緒線就不動。本版新增
獨立 `__RAW_PULSE__` 線：

- `trend_rollup.py` 讀 `_raw_stream.json`，用 raw item 既有 signed `shallow_score`
  產生低權重即時脈搏。
- Raw Pulse 是獨立 `kind: pulse`，不混入 `__ALL__` market consensus，也不產
  sector/theme，避免雜訊污染權威辯論線與 EMA scale。
- raw headline fingerprint 若已被 committee digest 或 closed debate 覆蓋則跳過，
  避免 raw→debate 雙算。
- `trend-chart.js` 認 `kind: pulse`，full mode selector 永遠保留「即時脈搏 /
  Raw Pulse」選項；compact 首頁仍鎖定乾淨的 whole-market consensus。

### Changed — LLM debate admission 改成分數排序 + 美股時段保留

- `poller.py` 改兩段式 admission：第一段只收 raw entries + debate candidates；
  第二段依 priority 排序後才消耗 LLM 預算。priority = `abs(shallow_score)`、
  binary、source credibility、非社群優先、Futu tie-break、freshness。
- 新增 `BREAK_NEWS_SESSION_RESERVE=25`。非美股新聞時段最多使用
  `DAILY_MAX - reserve`，07:00-18:00 America/New_York 才釋放全日額度。
- poller state 新增 `debate_candidates`、`auto_budget_limit`、
  `session_reserve`、`us_news_window_open`，方便 debug 為何候選被擋。

### Changed — raw stream retention

- `_raw_stream.json` 保留期由 24h/150 筆改為可設定，預設
  `BREAK_NEWS_RAW_STREAM_MAX_AGE_H=72`、`BREAK_NEWS_RAW_STREAM_CAP=500`，
  讓 Raw Pulse 能覆蓋完整 3 日趨勢圖。

---

## [3.8.1] — 2026-05-19 — Break News 辯論氣泡左右/配色修正

### Fixed — codex ↔ gemini 辯論兩邊都靠右藍色

`renderThreadBubble` 用 `agent === 'claude'` 硬判左右與配色：只有 claude 走左側橘色，
其餘 model 全部右側藍色。當辯論配對非 claude（例如 codex ↔ gemini）時，兩邊都判為
非 claude → 都靠右、都藍色，看不出對話分側。

- **`scripts/break_news/debater.py`** comment record 新增 `side`（`"A"`/`"B"`）欄位，
  由 turn 位置決定（後端真相），與既有 `agent_role_label` 一致。
- **`Dashboard/news_components.js`** `renderThreadBubble` 改讀 `comment.side` 決定
  左右 + 配色（A=左/橘、B=右/藍）；舊資料無 `side` 時 fallback 解析 role label，
  再退回舊 claude heuristic。avatar 改用 model 查表（claude🤖 / gemini💎 / codex🧠）。

### Why

多模型治理層（V3.7.0）後辯論配對可為任意兩 model，前端仍假設 claude 必為一方，
側別判斷失效。side 應為後端位置真相，前端不該用 model 名重算。

---

## [3.8.0] — 2026-05-19 — Break News 免費社群/趨勢源

### Added — Reddit / Bluesky / Hacker News / Google Trends 探勘層

Break News 原本只有正式新聞 RSS + Futu 推播，缺少市場題材早期發酵訊號。本版新增
免費低摩擦 source adapter，保持探索層定位，不影響 investment protocol 決策。

- **`scripts/break_news/social_sources.py`** 新增 normalized adapters：
  Reddit subreddit RSS、HN Algolia、Google Trends RSS；Bluesky public search adapter 保留，
  但因目前 public endpoint 回 403，預設關閉，可用 `BREAK_NEWS_BLUESKY_ENABLED=1` 測試。
- **`poller.py`** 接入 `BREAK_NEWS_SOCIAL_ENABLED`，社群/趨勢來源會進未閘 Raw 流；
  自動辯論需通過較高的 `BREAK_NEWS_SOCIAL_GATE_MIN_SCORE`，避免社群雜訊吃掉每日預算。
- **source metadata** 寫入 raw entry：`is_social` / `source_meta`，Dashboard 現有 raw 卡可直接顯示來源標籤。
- **可觀測性**：poller state 新增 `items_added_social`、`social_enabled`、`feed_stats`。

### Deferred

X、Stocktwits、Product Hunt 暫不接入：X 為 pay-per-use；Stocktwits 新 app 註冊暫停；
Product Hunt 需 token 且有商用限制。保留為 optional adapters。

---

## [3.7.1] — 2026-05-18 — Break News 辯論獨立配對（codex review fix）

### Fixed — Break News 辯論改用自己的兩模型配對

V3.7.0 的治理層讓 Break News debater 與通用路由共用同一組 primary/secondary —
改 dashboard 設定會同時動到兩邊。codex code review 指出此漏洞,本版修正:

- **`config/llm_config.json`** 新增 `break_news: {primary, secondary}` 區段 —
  Break News 辯論的 A/B 兩位辯手,獨立於通用 primary/secondary/tertiary 鏈。
- **`llm_drivers.py`** — `load_llm_config()` 解析 `break_news`;新 helper
  `break_news_pair()`。`debater.py` `_turn_order()` 改讀此區段。
- **`POST /api/llm-config`** 接受 `break_news` 區段(merge,不影響通用設定)。
- **sidebar 設定面板** 加「突發辯論配對」子區:辯手 A / 辯手 B 兩個下拉,與
  通用 主要/次要/備援 分開。
- **辯論身分標籤修正** — debater turn 若 fallback 換了模型,改用實際模型
  (`res.model_used`)重貼 role label,避免「Analyst-A (Claude)」卻存成 gemini。
  side A/B 仍為位置固定。

### Why

Break News 的 Claude×Gemini 刻意分歧是核心設計,需要跟供應鏈 / 協定路由解耦 —
獨立配對讓使用者單獨調辯論雙方,不波及通用 fallback 鏈。

---

## [3.7.0] — 2026-05-18 — 多模型治理層（claude / gemini / codex）

### Added — model_router governor:角色路由 + 預算 + quota 自動降級

3 個模型 CLI(claude / gemini / codex)過去各自為政:無 fallback(debater 連 2
次 CLI 失敗直接 abort)、無預算/quota 感知、協定寫死 claude。claude 額度一用完,
趨勢圖 / 辯論 / 協定全停。

- **`scripts/_shared/model_router.py`(新)** — 治理層。`run_role()` /
  `run_with_fallback()` 走 fallback 鏈(primary → secondary → tertiary),跳過
  停用 / 超預算 / quota cooldown 的模型,失敗或撞 quota 自動降級。
  `config/llm_usage.json` 記每模型每日呼叫數 + cooldown(UTC 日界自動重置)。
  quota 偵測 = best-effort 比對 CLI 錯誤/stdout 的 rate-limit/429/quota 字樣 →
  該模型進 `cooldown_hours` 冷卻。`model_status()` 給 dashboard。
- **`config/llm_config.json` 擴充** — 加 `tertiary` / `enabled` / `budgets`
  (每模型 `daily_max_calls`)/ `cooldown_hours`。舊 `{primary,secondary}` 仍相容。
  `llm_drivers.load_llm_config()` 改回傳完整治理 config + `model_chain()`。
- **消費者接governor** — break-news `debater.py`(每回合 `run_with_fallback`,
  模型掛了自動換,不再整場 abort)、`supply_chain.py generate()`(`run_role`)。
- **協定路由** — `dashboard_server.run_protocol()` 改用 `model_router.pick_model()`
  選模型(claude 優先,gemini/codex 只在 claude 超額/冷卻時頂上),per-model
  指令建構器(`_protocol_command`),跑完 `note_run()` 記帳 + quota cooldown。
- **dashboard** — `GET /api/llm-config` 回傳 config + 即時 `model_status`;
  `POST` 接受擴充 schema(merge 不覆蓋 budgets);sidebar 設定面板加備援 LLM
  下拉 + 每模型 `calls/daily_max` + 冷卻/額度滿標示。Codex 選項解鎖。

### Why

claude quota 一掛全系統停擺。治理層讓三模型有統一的角色路由、每日預算、quota
自動降級 — 一個模型用完,工作自動流到下一個,不中斷。

---

## [3.6.3] — 2026-05-18 — 情緒趨勢圖：線寬 / 字級不隨寬度爆掉

### Fixed — 寬螢幕上線太粗、x 軸字太大且重疊

`trend-chart.js` 的 SVG viewBox 固定 760 寬,圖以 `width:100%` 撐滿 → 在寬容器
(~2000px)上整體放大 ~2.6×:`stroke-width:1.6` 變 ~4px、SVG `<text>` font 9
變 ~23px,且相鄰日期標籤互相重疊。

- **線**:所有 stroke 加 `vector-effect="non-scaling-stroke"` → 線寬恆為固定
  px(設 1.3),不隨縮放變粗。
- **x 軸 / 「現在」標籤**:從 SVG `<text>` 改為 HTML overlay span(`.trend-xaxis`
  / `.trend-xlabel` / `.trend-nowlabel`)→ 字級固定 9px / 8px,不隨 viewBox 縮放。
- **重疊**:日期標籤碰撞檢查 — 與前一個標籤距離 < 8% 就略過(分隔線仍畫)。
- now 圓點 r 2.8→2.2。

### Why

SVG viewBox 縮放會等比放大 stroke 與 `<text>`;在寬版面上線與字都失控。線用
non-scaling-stroke、文字改 HTML overlay 後,兩者皆為固定 px,任何寬度都一致。

---

## [3.6.2] — 2026-05-18 — 情緒趨勢圖 x 軸可讀性優化

### Changed — `Dashboard/trend-chart.js` x 軸改為按日分界

舊 x 軸把 4 個 tick 放在任意 1/3 位置 → 標籤落在隨機小時(`5/15 18h`、`5/16 18h`、
`5/17 17h`),小時是雜訊、最右標籤被裁掉、看不出日界。

- **按日分界**:走訪 `series_labels` 偵測本地午夜,每個日界畫一條極淡垂直分隔線
  + 標「日期 + 星期」(`5/16 六` / `5/16 Sat`)。新 helper `_dayTicks()` / `fmtDay()`。
- **參考格線**:±0.5 格線由 `rgba(255,255,255,0.05)`(淺色主題下白底白線看不見)改為
  theme-safe `rgba(128,128,128,0.12)`。
- 修正最右標籤裁切(估寬後 clamp 進繪圖區)。
- 最新點旁加極淡「現在 / now」標記。`padB` 16→20 給日期標籤留白。
- hover tooltip 時間格式 `13h` → `13:00`。

### Why

使用者反映 `5/15 18h` 很難看懂。按日分界 + 星期讓 3 日結構一眼可讀,且能看出
週末(低新聞量)。維持低調風格 — 線條 / 顏色 / 資料不變,只動軸與格線。

---

## [3.6.1] — 2026-05-18 — sector 協定 turn-bloat 重構

### Fixed — `產業掃描` 33 分 / 52 turn → 預期 ~20-25 turn

2026-05-18 一次 sector run 跑 33 分(52 turns)被 30 分 timeout 砍 — 但其實**已成功**
(rc=0、artifact 有效)。診斷:不是 429、不是子代理 — 是 parent agent turn 太碎:
手寫整個 15+ key 巢狀 `sector_intel.json`(實際還寫 `/tmp/build_intel.py` Edit ×2)、
逐檔 `python3 -c` peek cache、validator retry loop。

把機械組裝從 LLM 移進 committed 腳本:

- **`sector/scripts/build_sector_intel.py`(新)** — 從 phase cache + 一個精簡
  LLM-authored decision JSON 確定性組出完整 `sector_intel.json`。模型只寫判斷欄位
  (`sector/cache/sector_decision_<DATE>.json`),腳本自動填 `_phase0` / `_phase1`
  / `_phase3` / metadata / `_phase4c`。輸出設計上即過 `validate_sector_intel.py`
  → 消滅 validator retry loop。decision JSON schema 見腳本檔頭 docstring。
- **`sector/scripts/sector_digest.py`(新)** — 一次印出 macro header + 11-sector
  決策表(uptrend / PE / z-score / RS / theme heat / news / smart-money / beat
  rate),取代逐檔 ad-hoc peek。
- **協定 MD 改寫** — `phase_1-2-3.md`(不再手抄 valuation / earnings_pulse /
  smart_money 進 JSON)、`phase_4-5.md`(Phase 5 改「寫 decision JSON → 跑 build
  script」;Phase 4a 並行 launch 升級為硬規則 + 違規警告)、`sector_protocol_main.md`
  GLOBAL RULE 7、`phase_0.md` / `schema.md` 指向新腳本。
- **`SECTOR_TIMEOUT_SEC`** 1800 → 2700(45 分)— 慢但成功的 run 不再被砍。

### Why

慢的根因是 parent agent 步驟太碎;把 JSON 組裝與 cache 讀取交給確定性腳本後,模型
只做真正的分析判斷,turn 數大幅下降,也不再因手寫 JSON 不合 schema 而重試。

---

## [3.6.0] — 2026-05-18 — 可設定主要/次要 LLM(server config + sidebar 設定面板)

### Added — server-side LLM config

LLM CLI 選擇過去全 hard-code(`run_claude`/`run_gemini`、debater `TURN_ORDER`、
`supply_chain.generate`)。新增可設定的主要 / 次要 LLM。

- **`config/llm_config.json`(新)** — `{"primary":"claude","secondary":"gemini"}`。
  Server-side 檔(Python script 讀得到;localStorage 只在瀏覽器,scripts 讀不到)。
- **`scripts/break_news/llm_drivers.py`** — 新 `run_codex` graceful stub(codex CLI
  尚未接線,回傳 rc=1 LLMResult,不會 crash 呼叫端);`_RUNNERS` registry +
  `run_llm(model, …)` dispatcher;`load_llm_config()` / `primary_model()` /
  `secondary_model()`。

### Added — sidebar LLM 設定面板

- `dashboard_server.py` — `GET/POST /api/llm-config`(POST 驗證 ∈ {claude,gemini,codex},
  寫回 config 檔)。
- `Dashboard/utils.js` `renderSidebar()` footer — 可展開「⚙ 設定」面板:主要 / 次要
  LLM 下拉(Codex 為 disabled「即將支援」),change 即 POST + toast。`style.css` 加
  `.sidebar-settings` 等樣式。

### Changed — generation / debate 走 config

- `scripts/nexus/supply_chain.py` — `generate(theme, agent=None)`:未指定 agent 時
  用設定的 primary;新 `--agent claude|gemini|codex` CLI 旗標(納入 Gemini 的建議,
  泛化為讀共用 config)。`generated_by` 反映實際模型。
- `scripts/break_news/debater.py` — `TURN_ORDER` 改由 `load_llm_config()` 在每場
  辯論開始時解析為 `[primary, secondary]`,config 缺失時 fallback claude↔gemini。

### Why

使用者要能切換 LLM CLI,且次要 LLM 供辯論 / 未來 review 用。預設 config 與舊行為
完全一致(零回歸)。Codex 預留:stub + disabled 選項,日後填 CLI flags 即可啟用。
另註:Gemini 建議中的「bridge.py 即時新聞」項已過時略過 — `extract_shallow_news`
於 v3.4.0 移除,即時 raw 新聞已是 break-news「未閘 Raw 流」(v3.3.2)。

---

## [3.5.3] — 2026-05-18 — heatmap 429 熔斷器

### Fixed — heatmap 背景刷新狂噴 HTTP 429

`heatmap_refresh_loop`(常駐背景 daemon,與是否開啟 heatmap 頁無關 — 負責把
`heatmap.json` 保溫)在美股盤中每 `HEATMAP_REFRESH_SEC`(10 分)就 fan-out
~517 個 FMP `stable/quote` 單檔呼叫(20 workers)。FMP 方案撐不住 → 全部回
429,每輪在 log 噴 ~500 行 `[heatmap] HTTP error: 429`。

加 **429 熔斷器**(`dashboard_server.py`):

- `_fmp_get_json` 收到 429 → 設 `_heatmap_ratelimit_until = now + 1800`(30 分
  冷卻),且**只在首次跳閘時 log 一行**(原本每通呼叫各噴一行)。
- `_heatmap_refresh_quotes` / `_heatmap_refresh_pe_universe` 開頭檢查熔斷器,
  冷卻中直接跳過整批 fan-out(各只留一行 `skip … cooldown`)。
- fan-out 內 `_fetch_one` / `_fetch_pe_ttm` 逐一檢查熔斷器 — 跳閘後排隊中的
  symbol 直接略過,不再實際打 API。

效果:429 風暴從「每 10 分 ~500 行」降為「每 30 分冷卻窗 ~1-2 行」。冷卻期間
heatmap 用既有 `heatmap.json` 快取,過後自動重試。

### Why

背景保溫迴圈無 rate-limit 處理 → 一被限流就無腦重打 + 洗版 log,既吵又浪費
配額。熔斷器讓它限流時安靜退避。

---

## [3.5.2] — 2026-05-18 — 供應鏈節點卡 UI 修正

### Fixed — 卡片重疊 / 溢出類別框 / badge 語言不一致

供應鏈圖節點卡有三個問題:

- **卡片重疊 + 溢出 module 框** — 卡片用 `min-height: NODE_H`(68px),但 2 行
  role 文字 + badge 列實際把卡撐到 ~90px+;佈局卻以固定 68px 間距排版 →
  卡片互相重疊、並超出所屬 module 子面板。改:卡片改**固定** `height`,
  `NODE_H` 拉到 100;`.sc-role` 設 `flex:1`(吸收空隙)、`.sc-badges`
  `flex-shrink:0`(錨在底部)。卡片等高 → 間距一致、面板尺寸精準。
- **badge 中英不一致** — `grounding` / `heat` badge 顯示原始 enum
  (`LLM_ONLY` / `VERIFIED` / `WARM`),中文頁面也顯示英文,與圖例
  (追蹤中 / 有資料 / 僅 LLM)對不上。新增 `groundingLabel` / `heatLabel` /
  `listingLabel` 隨頁面語言切換;節點卡 + detail panel 全部本地化。
- **節點卡加寬** — `NODE_W` 174 → 198,減少公司名稱過度截斷
  (「NTT Innovativ…」等)。

### Why

固定卡高是讓兩層佈局(stage → module → node)間距精準、不重疊的前提;
badge 跟著頁面語言走才不會中英混雜。

---

## [3.5.1] — 2026-05-18 — 供應鏈圖例 hover 說明

### Added — 圖例 pill hover tooltip

供應鏈頁底部 9 個圖例 pill(US 上市 / 外股 / 擬上市 / 私有 / 追蹤中 / 有資料 /
僅 LLM / 熱度 / 商用階段)過去無說明。沿用 `sector.html` 的 pill tooltip 模式
(`#pill-tooltip` + `data-tip-key` + `tip-title/desc/scale`),hover 跳出標題 +
解釋 +(熱度 / 商用階段)等級說明。

- `supply-chain.html` — `#pill-tooltip` CSS + 元素;每個 `.sc-legend-item` 加
  `data-tip-key` + `cursor:help` + hover 邊框。
- `page-supply-chain.js` — `SC_PILL_TIPS`(zh/en × 9 項)+ `initPillTooltip()`
  (mouseover/out 委派、量高後翻轉定位,與 sector 一致)。

### Why

圖例符號無說明時使用者得猜;一致的 hover 說明讓 grounding / 熱度 / 商用階段的
語意一看就懂。

---

## [3.5.0] — 2026-05-18 — 供應鏈：商用化階段 stage 標記層 + 生成完整度

### Added — node 級 commercialization-stage 標記

供應鏈鏈圖過去無法表達「誰會先變 revenue customer」。新增 node 級 `stage` 欄,
值域 `design_partner → sampling → qualification → production → revenue`(+ `unknown`)。

- **`scripts/nexus/supply_chain.py`** — 新 `_STAGES` enum;`_normalise()` 保留並
  驗證 node `stage`,非法值 → `unknown`。
- **`prompts/supply_chain_system.md`** — node schema 加 `stage`;指示 LLM 僅在有
  公開證據時標,否則 `unknown`(高精度時效資訊,使用者再編 YAML 校正)。
- **`Dashboard/page-supply-chain.js`** — `STAGE` 色階(design 灰→sampling 藍→
  qual 黃→production 橘→revenue 綠);node 卡 badge + 詳情面板「商用階段」列。
- **`Dashboard/supply-chain.html`** — `.sc-stage` badge CSS + 圖例階段色階。

### Changed — 提高 LLM 生成完整度

供應鏈公司清單 100% 來自 LLM 草稿(專案 DB 不參與選公司)。原 prompt 硬上限
8–20 node + 「omit rather than guess」壓制廣度 → 量產 OEM / 客戶層常漏。

- `prompts/supply_chain_system.md` — node 上限 8–20 → 12–32;模塊 2–3 → 2–4;
  「omit rather than guess」限縮到上游 materials/IP 層;OEM 層 + 客戶/系統層
  改為要求合理完整(列出主要量產 OEM/ODM 與主要 hyperscaler 客戶)。

### Changed — POET 供應鏈鏈圖擴充

`nexus/supply_chains/poet.yaml` 由 20 node 擴為 27:補 NTT Innovative Devices、
Credo、Luxshare、Foxconn Interconnect、ASE、Google、AWS,並對每個 node 標 `stage`
(保守:5 design_partner / 2 production / 其餘 unknown,待手動校正)。新增
`advanced_packaging` 模塊。

### Why

外部檢討指出 POET 鏈缺量產 OEM/客戶且無「商用化階段」標記層 — 後者比塞更多
公司更有投資價值。診斷確認缺公司是**生成/分析缺口**(LLM 草稿被 prompt 上限與
保守規則壓制),非資料量不足:DB 從不參與選公司,只做事後 grounding。stage 層
讓鏈圖能標出 POET 股價催化路徑。

---

## [3.4.1] — 2026-05-17 — 供應鏈：stage 內模塊分組 + 邊線修正

### Added — 每個 stage 分 2-3 個產業模塊

供應鏈的 stage 過去是扁平一欄,使用者要求把同一 stage 分成 2-3 個產業模塊
(如 `silicon` → CPU / GPU加速器 / 記憶體 / 網通)。

- **資料模型** — YAML 新增 `modules: {layerId: [{id,label}]}`,每個 node 加
  `module` 欄。`supply_chain.py` `_normalise()` 解析 modules、驗證 node.module
  ∈ 該層模塊;舊 YAML 無 modules → 隱式單一 `_default`(向後相容)。
  生成 prompt 要求 LLM 每層產出 2-3 模塊並指派每個 node。
- **佈局** — `page-supply-chain.js` `layout()` 改兩層:stage 欄內以 module
  子面板垂直堆疊,欄頂對齊。`renderDiagram()` 畫帶框 `.sc-module` 子面板 +
  標籤;stage band 弱化為虛線外框,模塊面板成為視覺主體。
- 已重生 `cpo/hbm/openai/spacex` 四條鏈帶入模塊結構。

### Fixed — 供應鏈邊線兩個 bug

- **隱形 spine 線** — spine 邊共用一個 `objectBoundingBox` 漸層;邊完全水平時
  (兩端同 y)bounding box 高度 0 → 漸層退化 → stroke 不顯示,只剩會動的粒子
  (openai 鏈 `nvidia→microsoft`)。改 per-edge `userSpaceOnUse` 漸層,絕對
  座標不退化。
- **同 stage 邊鼓圈** — 同層兩 node 的邊原本從右緣拉出又繞回同欄,在區塊內鼓
  醜圈。新增 `sidePath()`:同欄邊改走欄位右側的 C 形連接器(細、虛線、低調),
  不穿過區塊。

### Why

把產業分好讓供應鏈一眼看出結構;邊線修正讓主流向乾淨可讀。

---

## [3.4.0] — 2026-05-17 — 新聞層整併 + 情緒趨勢上首頁 + 供應鏈佐證

### Changed — 移除 news.html Triage tab(消除冗餘的「未辯論新聞」第三面)

`news.html` 過去有 3 個未辯論新聞清單之一的 Triage tab(讀 `bridge.py
extract_shallow_news()`),與 break-news 的「未閘 Raw 流」重複,使用者少用。

- 移除 `news.html` 🗂 Triage tab + `#news-triage-feed`。
- `page-news.js` 刪 `renderTriageFeed()` / `wireTriageButtons()` / triage filter 分支(~270 行)。
- `bridge.py` 刪 `extract_shallow_news()` + `data["shallow_news"]`(`_raw_pub_map` 保留,`extract_news` 仍用)。
- `news.html` = 純委員會深度 digest;break-news「未閘 Raw 流」= 唯一未辯論新聞面。
- `triage` 協定本身保留(`新聞分析 TRIAGE` 文字指令仍可用),只移除 dashboard 按鈕。

### Added — 情緒趨勢圖抽成可重用 module + index.html 首頁精簡 widget

- **`Dashboard/trend-chart.js`(新)** — `window.TrendChart` module:`mount({root, compact,
  withSelector})`。自帶 CSS(注入 `<style id="trend-chart-css">`)+ i18n + 30s 共用 fetch
  cache。`compact` 模式只畫市場整體線、92px 矮圖、無 entity 選擇器。
- `page-break-news.js` / `break-news.html` 改用 module(完整模式:選擇器 + legend + hover)。
- `index.html` `#risk-overview` 下方新增精簡趨勢卡(連往 break-news.html),`script.js` boot 掛載。

### Added — 委員會 digest verdict 餵入情緒趨勢指數

`trend_rollup.py` `compute_trends()` 過去只讀 `bn_*.json`。現在也讀
`news_logs/*_digest.json`:deep verdict 權重 ×1.8、shallow ×1.0;以 headline
fingerprint 對 break-news 去重(digest 品質高者勝)。趨勢指數現反映委員會層。

### Added — 供應鏈邊「知識圖譜佐證」

`supply_chain.py` `enrich()` 新增讀 `nexus_graph.json` 的 ticker↔ticker **edges**
(已含 break-news 辯論抽出的 SUPPLIES_TO / BENEFITS_FROM 等關係)。每條 LLM 草擬
的供應鏈邊標 `corroboration`(佐證來源數 + nexus 關係型別 + sources)。
`page-supply-chain.js` 邊列加 `✓N` 綠色 badge。

### Why

新聞層有兩條平行 pipeline(委員會 digest / break-news 探索),Triage tab 是第三個
冗餘未辯論清單。整併後職責清楚:digest = 深度委員會、break-news raw 流 = 即時全量。
趨勢圖上首頁讓使用者快速一覽市場情緒;餵入 digest 讓指數涵蓋最深一層分析。
Nexus 早已吃 break-news 實體/關係 — 供應鏈佐證讓 LLM 草擬的價值鏈能被真實辯論交叉驗證。

---

## [3.3.2] — 2026-05-17 — Break News 未閘 Raw 流 + 手動辯論觸發

### Added — un-gated raw breaking-news stream on `break-news.html`

突發辯論室過去只顯示過了 score gate(`|shallow_score| ≥ 2`)的自動辯論項。
冷門時段(週末/盤後)沒新聞過閘 → 頁面空窗看似停擺。此版加一條**未閘 raw 流**:
poller 抓到的**全部** RSS 項(過閘 + 未閘)都進 `_raw_stream.json`,UI 即時呈現,
每則可手動「🔥 辯論」繞過 gate 升級成辯論項。

- **`scripts/break_news/store.py`** — 新 `RAW_STREAM_FILE` + `load_raw_stream()` /
  `save_raw_stream(cap=150, max_age_h=24)`(atomic、key dedupe、汰 24h、保留既有
  `news_id` promotion)/ `mark_raw_promoted(key, news_id)`。
- **`scripts/break_news/poller.py`** — `run_once` loop 對每則非重複 item 收集 raw
  entry(headline / source / score / gate 結果 / 完整 triage / `key` / `news_id`),
  poll 末 merge 寫 `_raw_stream.json`。bn-creation 上限由 `break` 改 `continue` —
  raw 捕捉不受 `MAX_ITEMS_PER_CYCLE` 截斷。state 加 `raw_stream_size`。
- **`dashboard_server.py`** — `GET /api/break-news/raw-stream?limit=N`;
  `POST /api/break-news/raw/debate`(body `{key}` → 查 entry → `init_item` 繞閘 →
  `pending_debate` + 背景 `_bn_kick_debate_scan` 立即起辯論)。
- **`Dashboard/break-news.html` + `page-break-news.js`** — trend strip 與雙欄之間
  插可收合「未閘 Raw 流」面板:每卡片 score badge / 過閘狀態 / age / 來源 +
  「🔥 辯論」鈕。`loadRawStream()` 納入 poll cycle。

### Why

冷門時段 break news 頁空窗,使用者以為壞了。Raw 流提供「全量可視 + 手動升級」
旁路 — score gate **保留**(自動辯論門檻不變),raw 流純探索層展示,不進
investment_protocol 決策。

---

## [3.3.1] — 2026-05-17 — Supply-Chain page visual polish

### Changed — frontend-design pass on `/supply-chain.html`

V3.3.0 shipped the page functional but visually weak. This pass aligns it to the
dashboard design system and turns the layered diagram into a polished centerpiece.

- **Dual-theme fix** — node cards hardcoded `rgba(24,24,27,…)` (dark only); now
  use `var(--bg-card)` / `color-mix()` tokens → light theme works.
- **Controls** — plain box → `.ea-cmdbar`-style command bar with `>` prompt
  glyph, mono theme input, `focus-within` emerald glow, mono Generate button.
- **Canvas** — dotted-grid backdrop; each layer = a tinted band column with a
  numbered header chip so upstream→downstream structure reads instantly.
- **Edges** — flat grey → spine edges get an emerald→amber gradient stroke +
  animated flow particles (`<animateMotion>`) travelling upstream→downstream.
- **Node cards** — gradient listing-color accent stripe, heat → outer glow
  (hot red / warm amber / cold blue), hover lift, staggered reveal animation,
  badges restyled to the 9–9.5px uppercase-pill convention.
- **Detail panel** — polished floating card with listing-color header stripe +
  styled upstream/downstream edge rows. Legend → clean pill row.

### Why

User found the page's colours off and the diagram flat. Visual quality matters
for a tool meant to be explored; the bold treatment (flow animation, layer
depth, heat glow) makes the supply chain legible at a glance.

---

## [3.3.0] — 2026-05-17 — Supply-Chain Explorer

### Added — theme-keyed US supply-chain maps on a new `/supply-chain.html` page

User found the Nexus knowledge graph (`/graph.html`) too messy (800 nodes /
3895 edges, `MENTIONED_IN` = 50% = hairball) and wanted instead to *explore
US-stock supply chains by theme* — e.g. the CPO (co-packaged optics)
upstream→downstream value chain. Nexus can't serve this: directional
supply-chain edges are absent (count 0) and private/foreign players never
enter the graph at all.

New separate **Supply-Chain Explorer** — LLM drafts the chain, existing data
grounds it, a clean layered diagram renders it. Nexus auto-graph untouched.

- **`scripts/nexus/supply_chain.py`(新)** — `generate(theme)` calls Claude (via
  reused `scripts/break_news/llm_drivers.py` `run_claude`) with
  `prompts/supply_chain_system.md` → drafts ordered layers, companies (honest
  `listing`, real tickers only), directional edges, a `spine` → saved as
  editable YAML in `nexus/supply_chains/<slug>.yaml`. `enrich()` adds live
  per-node `grounding` (verified = in `heatmap_universe.json` / seen = in
  `nexus_graph.json` / llm_only) + `heat` (from Nexus mention counts).
  `nexus_themes()` exposes Nexus theme/narrative labels as quick-picks.
- **`dashboard_server.py`** — `GET /api/supply-chain/{list,themes,<slug>}` (60s
  TTL cache) + `POST /api/supply-chain/generate {theme}` (synchronous LLM draft).
- **`Dashboard/supply-chain.html` + `page-supply-chain.js`(新)** — layered
  upstream→downstream diagram: each layer = a column, nodes = HTML cards over an
  SVG edge layer, directional bezier arrows, spine highlighted. Per-node badges:
  可投資性 (listing 色條) · 資料支持度 (grounding ✓◦⚠) · 供應鏈層級 (column) ·
  近期熱度 (heat dot). Chain selector + theme free-text/quick-pick + 生成 button.
  Node click → detail panel (role / upstream / downstream).
- **`utils.js` + `i18n.js`** — `供應鏈` sidebar nav entry (portfolio group).
- Seeded `nexus/supply_chains/cpo.yaml` (18 companies, 5 layers, 21 edges).

### Why

User wants to *know* supply chains, not untangle a log-derived hairball. LLM
drafts breadth fast; grounding against existing universe/Nexus data flags which
nodes are tradeable vs unverified LLM claims. Editable YAML accumulates a
reviewed library. Nexus stays the exploration layer — this is the curated view.

---

## [3.2.0] — 2026-05-15 — Break News 3-day sentiment-trend chart

### Added — rolling sentiment-index trajectory on break-news.html

突發新聞辯論室的辯論 log 過去是孤立快照,看不出敘事「方向」隨時間怎麼演化。
此版把每則 debate 當成帶正負號的事件,經時間衰減 EMA 串成一條情緒指數軌跡,
呈現在 `break-news.html` 頂部全寬面板:單一大圖 + 實體選擇器。一次畫一條線
(市場整體 / 某產業 / 某主題),避免多線疊圖糾纏。

- **`scripts/break_news/trend_rollup.py`(新)** — `compute_trends()` 唯讀掃
  `news/break_news_logs/bn_*.json`,只取 closed/partial_closed。
  - 每則 log = 事件:`sign` = BULLISH +1 / BEARISH −1 / NEUTRAL·SPLIT 0;
    `weight` = impact(`triage.shallow_score`/4,clamp 0.25–2.0)× 來源可信度
    (HIGH 1.0 / MED 0.7 / LOW 0.4);`貢獻 = sign × weight`。
  - 72 個每小時 bucket(3 日窗,直接走 UTC),時間衰減 EMA
    `S = S_prev × decay + Σ貢獻`,`decay` 由 12h half-life 推導。
  - 顯示值 = `tanh(S / scale)`,scale 為**每實體自適應**(該實體 peak 對應
    ~0.9,floor `_MIN_SCALE`)→ 每條線都用滿 [−1,+1],無新聞時自然衰回 0。
  - 實體層級:市場整體(全 log)/ 各 sector / 各 theme(theme 走輕量
    `ALIAS_MAP` 正規化)。sector/theme 需 ≥3 事件才可選,各 cap top 12。
- **`dashboard_server.py`** — 新 GET `/api/break-news/trends`,60s TTL cache
  (`_bn_trend_cache`),共用 `BREAK_NEWS_AVAILABLE` guard。
- **`Dashboard/break-news.html` + `page-break-news.js`** — 頂部 `.bn-trend-strip`
  面板:`<select>` 實體選擇器(optgroup 分 市場/產業/主題)+ 手刻 SVG area
  chart(零基線、綠上紅下填色 clipPath、4 個時間軸刻度)+ 即時數值讀數 +
  hover 游標(任一時點的時間與分數)。切換實體不重 fetch(所有 series 同
  payload)。隨既有 30s poll loop 更新。

### Why

使用者要的是「根據每次收到的新聞修正當下趨勢往上或往下」— 一條會穿越 0、隨
利多利空演化的軌跡,而非靜態的提及量排行。EMA 時間衰減讓指數有記憶但會遺忘,
符合「漂亮時高、利空連發跌破 0、無新聞慢慢衰回 0」的直覺。維持探索層紀律:
trend 面板不進 investment_protocol 決策。

---

## [3.1.2] — 2026-05-14 — Break News side-panel synthesis + categorized entities

### Added — bull/bear bullet synthesis + grouped entity sections + graph linkage

User feedback on V3.1.1 side panel (screenshot): `合議摘要` only showed
verdict enum + flat entity chip dump, no written bull/bear/conclusion and no
visible link to the knowledge graph. This release fixes all 3 with zero extra
LLM calls (schema extended on the existing per-turn JSON response).

- **`scripts/break_news/prompts.py` — schema additions**
  - `SYSTEM_PROMPT` now requires `bull_points: [str ≤3]`, `bear_points: [str ≤3]`,
    `final_take: str` (≤30字繁中) per agent response. Each side must give at
    least 1 point (forces balanced view even when agent leans strongly).
  - `build_summary_block` extended: returns `bull_summary[]`, `bear_summary[]`,
    `final_take`, `final_take_by`. Bull/Bear bullets merged across both agents
    with `_rough_dedup` using Jaccard ≥ 0.6 over zh-aware char-level tokens.
    `final_take` taken from latest comment with a non-empty value.
- **`Dashboard/news_components.js`**
  - New `renderEntityChipsGrouped(entities)` — 4 labeled sections with header
    + count badge (🏢 個股 / 🏭 產業 / 🔥 主題 / 🔬 技術節點) instead of
    flat chip dump. Lang-aware labels via `currentLang()`.
  - New `entityTotal(entities)` — `{tickers, sectors, themes, tech_keywords, total}`
    counts used by graph footer.
  - Existing `renderEntityChips` (flat) kept for per-comment thread bubbles.
- **`Dashboard/page-break-news.js:renderDetail`** — rewrite of summary panel:
  - Verdict header w/ rounds + close reason
  - 🎯 最終結論 line (with agent attribution)
  - 分歧 (divergence) line if predicates diverge
  - ✅ 正方意見 bullet list (green left-border accent)
  - ❌ 反方意見 bullet list (red left-border accent)
  - 🧩 萃取實體 categorized chip sections
  - 🌐 知識圖譜入口 footer: catalyst node id, edge counts, graph_status,
    link to `/graph.html`
  - Placeholder block for items still in `debating` / `pending_debate` state

### Backward compatibility

Old `bn_*.json` files without `bull_points` / `bear_points` / `final_take`
render gracefully: bull/bear sections suppressed, only verdict + entities
appear (same as V3.1.1). Replay (`⟳ 重跑`) regenerates with new fields.

### Verification

```bash
ITEM=$(ls news/break_news_logs/bn_*.json | head -1 | xargs basename | sed 's/.json//')
python3 -c "from scripts.break_news import store; store.set_state('$ITEM', 'pending_debate')"
python3 scripts/break_news/debater.py --news-id "$ITEM" --max-rounds 1 --verbose
jq '.summary | {consensus_verdict, bull_summary, bear_summary, final_take, final_take_by}' \
   news/break_news_logs/$ITEM.json
open http://localhost:8080/break-news.html   # side panel: bull/bear bullets + grouped chips + graph footer
```

---

## [3.1.1] — 2026-05-14 — Break News + Futu push channel

### Added

- **Futu 牛牛 push** as a second break-news source alongside the 9 RSS feeds.
  Pre-filter is strict: US ticker required, no HK/A-share, no ads/clickbait.
  Pushes feed `scripts/break_news/poller.py` via new
  `scripts.parse_futu_notifications.load_for_break_news(window_hours, max_items)`.
- `scripts/parse_futu_notifications.py`:
  - `_AD_HARD_KEYWORDS` — 富途早晚報 system notices, 開戶 / 贈金 promos,
    直播 / 課程 / 牛友圈 educational ads, 立即下載 / 掃碼 CTAs
  - `_HOWTO_PATTERNS` — `如何...？` / `教你...` / `一文讀懂...` clickbait regex
  - `_is_ad(text)` — predicate used by poller via `filter_ads=True`
  - `load_notifications(filter_ads=, require_us_ticker=, ...)` — backward
    compat; both flags default False so existing `/api/futu-notifications`
    endpoint behavior unchanged
  - `load_for_break_news()` — emits items in `fetch_news_rss.fetch_feed`
    shape (`headline, url, raw_summary, source="Futu Push", credibility="MEDIUM",
    published, _fp, _dt, tickers`)
  - `_futu_fingerprint(headline, tickers)` — sha1-based fp that survives zh-CN
    text (the RSS `headline_fingerprint` only keeps `[a-z0-9]` tokens, which
    collapsed every Futu zh push to "" or "20" → false dedupe)
- `scripts/break_news/poller.py`:
  - Lazy `import scripts.parse_futu_notifications as _futu`
  - `fetch_fresh_items()` merges Futu items with RSS items, time-window cutoff
    applied uniformly, dedupe ranks by credibility tier (HIGH > MEDIUM > LOW)
    and prefers non-Futu on tie (real URL beats synthetic `futu://`)
  - `run_once()` — Futu items skip the English-keyword score gate (would
    mis-score zh text) with `advance_reason="futu_news"`. Daily cap + per-cycle
    cap unchanged.
  - New counters: `items_added_futu`, `futu_enabled` in `_state.poller`
- Env vars: `BREAK_NEWS_FUTU_ENABLED` (default `1`),
  `BREAK_NEWS_FUTU_MAX_PER_CYCLE` (default `30`)

### Why

User explicitly asked: 「futu 牛牛的推播也要放入辯論, 美股限定, 中股港股不用,
廣告也不用, 新聞限定」. Futu push 是 zh-CN 速報，常比 RSS 早 5-30 分鐘出
（券商直連 Reuters/Bloomberg wire），加進辯論池可增加新聞覆蓋的及時性。

### Verification

```bash
python3 -c "from scripts.parse_futu_notifications import load_for_break_news; \
  items, stats = load_for_break_news(window_hours=6); print(stats); \
  [print(f'  [{\",\".join(i[\"tickers\"])}] {i[\"headline\"][:80]}') for i in items[:5]]"
python3 scripts/break_news/poller.py --once
jq '.poller | {items_added, items_added_futu, futu_enabled}' news/break_news_logs/_state.json
```

---

## [3.1.0] — 2026-05-14 — Break News (RSS + Dual-CLI Debate Layer)

### Added — Continuous short-cycle news with Claude × Gemini debate

- **`scripts/break_news/`** — new module: RSS poller + Claude/Gemini CLI debate orchestrator
  - `store.py` — atomic JSON store at `news/break_news_logs/<news_id>.json`, per-id
    in-process locks, `_seen_index.json` dedupe (sha1 of url+headline fingerprint),
    `_state.json` poller/debater health, startup sweep that resets `debating` items
    older than 15 min back to `pending_debate`
  - `poller.py` — pulls all 9 RSS feeds via `news/fetch_news_rss.py` parsers,
    in-process triage via `stage1_triage.classify_news_type` + `calc_shallow_score`,
    gate `|shallow_score| ≥ BREAK_NEWS_GATE_MIN_SCORE` OR HIGH credibility + |s|≥1
    OR binary event; daily cap `BREAK_NEWS_DAILY_MAX_DEBATES`; flags `--once --dry-run`
  - `llm_drivers.py` — subprocess wrappers for `claude` (envelope `.result`) and
    `gemini` (envelope `.response`); 3-stage JSON extraction (fenced → whole →
    brace-balanced); raw stdout dump on parse failure; default Gemini model is
    `gemini-2.5-flash-lite` (pro/2.5-pro/flash hit RESOURCE_EXHAUSTED on free tier)
  - `prompts.py` — strict SYSTEM_PROMPT requiring single fenced JSON output with
    schema `{commentary, entities, relations, done, confidence}`; opener + follow-up
    user prompts; `build_summary_block` merges entities/relations across the thread
  - `debater.py` — state machine `pending_debate → debating → closed/partial_closed/failed`;
    alternates Claude (Analyst-A) and Gemini (Analyst-B); both must signal
    `done:true` or `<DONE>` in commentary to close; max 3 rounds (env-overridable);
    480s wall-clock budget; partial close on timeout. Flags `--news-id`, `--scan`,
    `--workers`
  - `validate.py` — schema lint for break_news_logs/*.json (rc=0/1)
- **`Dashboard/break-news.html` + `page-break-news.js`** — new `/break-news.html`
  page; vertical card stream + side panel with Claude/Gemini bubble thread, entity
  chips (tickers, sectors, themes, tech-keywords), consensus summary block, replay
  button per item. 30s polling for feed + state, 5s polling for selected item
  while still debating
- **`Dashboard/news_components.js`** — shared primitives: `renderNewsCard`,
  `renderScoreBadge`, `renderSourcePill`, `renderAgePill`, `renderStatePill`,
  `renderEntityChips`, `renderThreadBubble`, `escapeHtml`, `relTime`
- **`dashboard_server.py`** — 2 daemon threads (`break_news_poll_loop`,
  `break_news_debate_loop`) modeled on `refresh_loop`; 5 routes
  (`GET /api/break-news/feed`, `/item/<id>`, `/state`; `POST /refresh`,
  `/item/<id>/replay`); new `GEMINI_BIN` constant; startup sweep call;
  separate `_break_news_dispatch_lock` so debates don't block `_protocol_lock`
  (normal `分析/產業掃描/新聞分析` keep running)
- **`Dashboard/utils.js`** — new `break-news` NAV_ITEM in MARKET group;
  VERSION bumped to V3.1.0
- **`Dashboard/i18n.js`** — `nav.break_news` zh + en keys

### Changed

- `dashboard_server.py` — `PORT` now reads `DASHBOARD_PORT` env var (still defaults
  to 8080); enables running an isolated test instance on a different port

### Why

The daily DIGEST pipeline (`news/news_protocol_v2.md`) runs on user trigger
once per day and produces a single batched verdict file. Market-moving news
during the trading day was being missed. The new Break News layer pulls RSS
every 10 minutes and runs an automated Claude × Gemini debate per item;
divergence between the two models surfaces uncertainty that single-model
arbitration hides. Entities + relations extracted from each comment feed into
the Knowledge Graph (V3.0) as a new data source so 2nd / 3rd-order
relationships build up faster.

### Env vars

```
BREAK_NEWS_INTERVAL_SEC=600         # poll cadence (10 min)
BREAK_NEWS_LLM_TIMEOUT_SEC=180      # per CLI turn
BREAK_NEWS_THREAD_TIMEOUT_SEC=480   # whole debate wall-clock
BREAK_NEWS_PARALLEL=2               # concurrent debates
BREAK_NEWS_DAILY_MAX_DEBATES=30     # cost cap
BREAK_NEWS_MAX_ROUNDS=3
BREAK_NEWS_GATE_MIN_SCORE=2
BREAK_NEWS_GEMINI_MODEL=gemini-2.5-flash-lite
CLAUDE_BIN, GEMINI_BIN              # binary path overrides
DASHBOARD_PORT=8080
```

### Verification

```bash
python3 scripts/break_news/poller.py --once --dry-run
python3 scripts/break_news/poller.py --once
python3 scripts/break_news/llm_drivers.py --probe --agent claude
python3 scripts/break_news/llm_drivers.py --probe --agent gemini
python3 scripts/break_news/debater.py --news-id <id> --max-rounds 1 --verbose
python3 scripts/break_news/validate.py
curl http://localhost:8080/api/break-news/state | jq .
curl http://localhost:8080/api/break-news/feed?limit=5 | jq .
open http://localhost:8080/break-news.html
```

---

## [3.0.0] — 2026-05-13 — Project Nexus (Knowledge Graph)

### Added — Major architectural layer: 1st/2nd/3rd-order relationship graph

- **`scripts/nexus/`** — new module tree implementing news + financial-analysis-driven
  knowledge graph extraction. Built atop existing V2.X analytical pipeline, does NOT
  alter decision layer (Arbiter wiring deferred to V3.1).
  - `schema.py` — Node/Edge dataclasses, NodeType + EdgeType enums, canonical id helpers
  - `config.yaml` — multi-dimensional decay strategies (catalyst 7d / narrative 21d /
    structural_shift 90d / supply_chain_hop 45d / outcome_for 30d), tier confidence
    multipliers (Tier 1: 1.0 / Tier 2: 0.7 / Tier 3: 0.85), alias map (TSM/NVDA/MSFT…),
    pruning thresholds, Tier 3 backfill limit
  - `tier1_loaders.py` — pre-structured JSON loaders (theme-detector cache,
    event_index, news_logs digests, thesis registry, Dashboard/data.json earnings)
  - `tier2_regex.py` — extends existing extractors with tech-node regex
    (HBM3e / N3P / CoWoS-L / Blackwell / Rubin / silicon photonics / GaN / SiC …)
    — these are leading-leading indicators surfacing in commentary weeks before
    financial confirmation. Emits SUPPLY_CHAIN_HOP edges via canonical narrative nodes
  - `tier3_llm_ner.py` — Haiku 4.5 batched LLM NER with prompt caching, SHA256
    per-document cache, two-stage alias canonicalization (hard alias map +
    ≥3-doc promotion guard for provisional narratives)
  - `pagerank_lite.py` — Power Iteration PageRank fallback when `networkx`
    unavailable; degree-centrality cheap fallback below that
  - `build_graph.py` — orchestrator: tier merge → multi-dim decay + confidence-weighted
    → networkx/lite centrality → leaf+cap prune → emit `Dashboard/nexus_graph.json`
    (<5MB hard cap, asserted)
  - `prompts/ner_system.md` — Haiku ontology + few-shot for triple extraction
- **`Dashboard/graph.html` + `Dashboard/page-graph.js`** — new `/graph.html` page
  rendering Obsidian-style force-directed graph via `force-graph@1.43` CDN.
  Monochrome by default, size = √(degree centrality), hover glows `--secondary`.
  **Narrative Flow path tracing**: click any node → BFS up to 3 hops → 1st/2nd/3rd
  order beneficiaries highlighted in blue gradient, animated link particles along
  active frontier. Side-panel lists ranked neighbors per hop with PageRank, plus
  source-document audit trail
- **`Dashboard/utils.js` NAV_ITEMS** — new `knowledge graph` nav item in PORTFOLIO group
- **`Dashboard/i18n.js`** — `nav.graph` zh/en keys
- **`daily_update.sh` Step 8** — Nexus build appended after Step 7 (Structural
  Watchlist); soft-installs `networkx` if missing; non-fatal failure mode
- **`dashboard_server.py`** — new `/api/graph/data` (serves cached JSON) and
  `/api/graph/centrality/<TICKER>` (per-ticker connected themes/catalysts/narratives/peers)
  read-only inspection endpoints. **No** Arbiter integration

### Why

Existing V2.X analyzes individual stocks well but lacks 全域空間感知. Daily news +
theme detector + sector intel + deep dives already produce structured artifacts —
what was missing is the edge layer surfacing 2nd-order beneficiaries (e.g. NVDA
capex story → VRT/COHR/GLW supply chain) and narrative共振 before financial outcomes
confirm them. Nexus introduces a graph-shaped entity store as a structural new
layer (hence major version jump) atop the analytical pipeline. Tier 3 LLM is the
heart, not a supplement — it reads the prose where 2nd/3rd-order relationships
actually live. MVP is visualization + centrality inspection only; Arbiter wiring
into investment_protocol Phase 3 (二階衍生推薦 + 紅隊打折) deferred to V3.1.

### Costs / Operations

- Daily Tier 1+2 build wall time: ~10–20s
- Tier 3 steady-state daily cost: ~$0.05 (40 MDs × ~3k tokens × Haiku 4.5,
  cache-hit ≥90%). First-day backfill capped at 10 MDs/run (~$0.03)
- Output: `Dashboard/nexus_graph.json` (~1.5MB Tier 1+2, ~3MB w/ Tier 3 full)
- Audit log: `scripts/nexus/cache/build_log_<DATE>.json` per build

---

## [2.20.2] — 2026-05-12
### Added — Sector protocol 加速 (A1 + B2) + 時間 timeout 拉到 30 min (V2.20.1)

### Added
- `sector/scripts/phase0_read_caches.py` (A1, 新檔):
  - Phase 0 unified cache reader — 一次跑取 5 層 cache (breadth / FTD / market_top / FRED) + 新鮮度判斷
  - stdout 輸出單一 JSON，取代過去 5+ 個 inline `python -c` bash call（每個 = 1 turn × LLM overhead）
  - slim_* 函式只保留 Phase 0 需要的欄位（FRED 11 fields, breadth/FTD/market_top 4 key blocks）
  - 預估省 **2-3 min** sector wall time（5-8 個 turn → 1 個 turn）
- `sector/phase_0.md` — 上面標示推薦使用 unified reader，舊流程改備援
- `sector/phase_1-2-3.md` — Step 3b/3c/3d/3e parallel mode（bash `&` + `wait`）：
  - 4 個 fetch_*.py (earnings_pulse / smart_money / sector_news / general_news) 平行跑
  - 過去 sequential ~6 min → parallel ~30s wall
  - 預估省 **3-4 min** sector wall time
- `dashboard_server.py` (V2.20.1):
  - Preflight chain sector wait timeout 1200s (20 min) → **1800s (30 min)**
  - `PROTOCOL_TIMEOUT_OVERRIDES` 加 sector override 1800s + `SECTOR_TIMEOUT_SEC` env var

### Why
- 用戶觀察 sector V1.4 PARALLEL_SUBAGENT 跑 ~17-21 min（p95 21 min），偶爾 hit 1200s preflight cap timeout
- 解兩個方向：
  1. **拉 timeout cap**：preflight 1200 → 1800，避免 false timeout
  2. **減 sector 實際耗時**：A1 + B2 應省 5-7 min (17.8 min → 11-13 min)
- 沒做 A3 (Devil's Advocate inline)、A2 (Phase 5 builder)：兩者需動 protocol 邏輯，風險 vs 收益不對等

### Smoke
- `python3 sector/scripts/phase0_read_caches.py` rc=0，輸出 4 layer (breadth/ftd/market_top stale, fred fresh)
- `python3 -m py_compile sector/scripts/phase0_read_caches.py` OK
- `python3 -m py_compile dashboard_server.py` OK

### Out of Scope (V2.20.3+)
- A2 — Phase 5 build_sector_intel.py 拆出獨立 script（需 Phase 4 lane outputs 先序列化到 disk）
- A3 — Devil's Advocate 從 Phase 4 獨立 subagent → Phase 2.5 inline（需動 protocol divergence 邏輯）
- B1 — 4 lane subagent 合併（Theme + News Catalyst）
- B3 — theme_detector `--skip-if-fresh` 邏輯確認（目前 cache hit < 3h 應該秒退，需 verify）

---

## [2.20.0] — 2026-05-10
### Added — V2.20.0：UI Decision Layer 完整化 + Backtest 深化 + Decision Logic 動態化

### Added (A — UI Decision Layer)
- `bridge.py` `extract_audit_history`：`recent_analysis[].det_shadow` 已含 polarization + red_team_basis（從 V2.19 history.json 經 apply_det_shadow 重跑後注入）
- `bridge.py` `extract_earnings_analyses`：每筆 entry 加 `structural_shift` 欄位（從 cache directly），給 earnings card badge 用
- `bridge.py` `load_theme_overrides()` (新)：讀 theme-detector cache 過濾出 `structural_shift_override=True` 的 themes，注入 `data.theme_overrides`
- `Dashboard/page-decisions.js`:
  - Polarization badge 升 4-tier (BIPOLAR / **OUTLIER** 新增 / MIXED / ALIGNED 不顯)
  - Red Team basis 4-tier badge：**RT MR-ONLY** 紅 / **RT CONTAM** 橘 / **RT FWD** 綠（pure_forward 健康才綠）/ unclassified 不顯
- `Dashboard/page-earnings.js`：earnings card 加 **SHIFT⚡⚡** (CONFIRMED 紅) / **SHIFT⚡** (CANDIDATE 黃) badge
- `Dashboard/page-sector.js` `renderThemes`：themes 列表加 ⚡ icon + tooltip（來自 `data.theme_overrides`，含 hits + bonus）

### Added (B — Backtest 深化)
- `investment/scripts/backtest_watchlist.py`:
  - `RANDOM_SECTOR_TICKERS`：14 sector ETF 各 5 個代表性 ticker（共 70 個 universe）
  - `compute_random_baseline()` (B1)：null hypothesis test — 比較 watchlist alpha vs random 同 sector 5 ticker 的 alpha
  - `compute_per_keyword()` (B2)：14 個 keyword 拆解 — 哪幾個 keyword 帶 signal、哪幾個是 noise
  - `compute_per_credibility()` (B3)：HIGH vs MEDIUM source 切片
  - `compute_horizon_sweep()` (B4)：5d/15d/45d/90d 全 horizon mean alpha + hit rate
  - render_markdown 4 個新區塊
  - `--dry-run` flag (D2)：純 stdout 不寫檔
- 今天跑出來：**watchlist +4.4pp 過 random sector baseline (35 samples)** → 證明非純 sector momentum；`super-cycle` keyword 最強 (+23.4% mean α)；`supply tight` 最弱 (+5.1% — 疑似 boilerplate)

### Added (C — Decision Logic)
- `investment/investment_protocol_v5_0.md` Phase 3 Step 4 — **Dynamic Decision Threshold**：
  - CONFIRMED + ALIGNED → buy_threshold 1.0（更敢進）
  - CANDIDATE + ALIGNED → 1.1
  - BIPOLAR → 1.5（更嚴）
  - OUTLIER → 1.3
  - default 1.2 （staged_threshold 永遠 = buy − 0.4）
- `investment/scripts/apply_det_shadow.py` `compute_lane_freshness_penalty()` (C2)：
  - 5 lane 各自 fresh window：news 2d / sentiment 1d / technical 1d / fundamentals 90d / valuation 90d
  - 4 級 multiplier：fresh ×1.0 / 1-2x ×0.9 / 2-3x ×0.8 / >3x ×0.7
  - 寫入 `det_shadow.lane_freshness` block
  - 114/123 historical entries 套上 freshness penalty (大多 sentiment/technical lane 略過 fresh window)
- `investment/scripts/apply_det_shadow.py` `classify_red_team_basis_detail()` (Gemini review #1)：
  - V2.20.0 metadata：mr_hits / fw_hits / mr_keywords / fw_keywords / mr_density / fw_density per 1000 chars
  - 不改 basis label binary 4-tier 契約，純為 V2.21+ density-weighted calibration 留資料

### Added (D — UX)
- `bridge.py` `load_structural_watchlist()` 加 trajectory：每個 candidate 帶 `n_events / first_seen_event / graduated_candidate / graduated_confirmed / continued_count`
- `Dashboard/script.js` `renderStructuralWatchlist`：加 lifecycle badge — **NEW** (≤2 events 綠) / **AGING** (≥5 continued 灰) / **CANDIDATE** (黃) / **CONFIRMED** (紅)

### Backfill (cumulative cross-version delta in this commit)
本 commit 也含 V2.19.1 + V2.19.2 在這些 file 累積的部分（無法乾淨切到前面 commit）：
- `bridge.py` V2.19.1 `load_structural_watchlist()` + V2.20.0 theme_overrides / trajectory / earnings shift
- `Dashboard/script.js` V2.19.1 `renderStructuralWatchlist` + V2.20.0 trajectory badges
- `Dashboard/page-decisions.js` V2.19.2 ⚡ + V2.20.0 OUTLIER + RT basis
- `Dashboard/page-earnings.js` V2.19.2 ⚡ + V2.20.0 SHIFT
- `investment/scripts/backtest_watchlist.py` V2.19.1 skeleton + V2.19.2 forward returns + V2.20.0 B1-B4 + dry-run

### Why
- V2.18+V2.19 加了 protocol 改動，但 UI 沒 surface → user 看不到 polarization / red_team_basis / structural_shift tier 起作用
- V2.20.0 把所有改動 surface 到 dashboard 三頁（decisions / earnings / sector），user 一目了然
- Backtest 從 V2.19.2 的「跑得起來」深化到「拆解 signal 來源」：random baseline 證明 watchlist 真有 edge，per-keyword 找出 noise vs signal
- Dynamic threshold 解決固定 1.2 對 paradigm-shift 太嚴、對 chaotic 太鬆的問題

### Smoke
- `python3 bridge.py` → `[OK] Theme overrides: 3 paradigm-shift themes` + watchlist 注入
- `python3 investment/scripts/apply_det_shadow.py --inplace history.json` → 114/123 entries 套 freshness penalty
- `python3 investment/scripts/backtest_watchlist.py` →
  - SOXX watchlist mean α 15d = +18.4% vs random baseline +14.0% = **+4.4pp edge**
  - Per-keyword: super-cycle +23.4%（5 hits）/ 供不應求 +18.4%（7 hits）/ supply tight +5.1%（3 hits）
  - Horizon: 5d +0.1% 沒動；15d peak +18.4%；45/90d 還沒到
- `python3 investment/scripts/backtest_watchlist.py --dry-run` → stdout 全 markdown，不寫檔

### Out of Scope (V2.20.X — 等 watchlist accrue)
- E1-E3 backtest 真實驗證（lifecycle ≥30 events / 3+ sector / 5+ evicted samples）
- F1 thesis_registry concentration check（Phase 4 sizing）
- F2 sector protocol 反向加權
- Lane-specific freshness mtime（Gemini review #2 — 取代 session-level penalty）

### Out of Scope (V2.21+ — 大改)
- News provisional → tier modulation（需 V2.20.X backtest 結果）
- Modulation 參數 auto-calibration（需 n>50 sample）
- macro_multiplier sector × duration sensitivity matrix

---

## [2.19.2] — 2026-05-10
### Added — V2.19.X 補強：⚡ badge 跨頁、backtest forward returns、theme heat bonus

### Added
- `Dashboard/page-decisions.js` + `page-earnings.js`:
  - 個股名旁 ⚡ amber lightning badge if ticker ∈ `data.structural_watchlist.candidates`
  - 兩頁各自在 data load 處 populate `window.UI.watchlistSet`
- `investment/scripts/backtest_watchlist.py`:
  - `_fetch_price_series()` — FMP `/stable/historical-price-eod/light` endpoint，cache by ticker
  - `_close_at_or_after()` — 跳過週末 / 假期，找下一個交易日
  - `fetch_forward_returns()` — 完整實作（取代 V2.19.1 stub）：
    - T+5d / T+15d / T+45d / T+90d 報酬
    - α_SPY (絕對 alpha vs SPY) + α_sector (相對 alpha vs sector ETF)
    - SECTOR_ETF_MAP：Memory Semis→SOXX、Energy→XLE、Healthcare→XLV…
    - 未到的 horizon 寫 None；status: ok / partial / no_data / api_unavailable
  - 改 `collapse_by_ticker` 用 `first_observed`（news 首次提及日）為 backtest anchor，不用 event date
  - render_markdown 加 forward returns table + 15d alpha aggregate (mean / hit_rate)
  - JSON 輸出 加 forward_returns block
- `skills/theme-detector/scripts/calculators/heat_calculator.py`:
  - `structural_shift_bonus()` — 加性 bonus +0/+5/+10/+15 cap
    - `+10` if 任一 rep stock CONFIRMED；`+5` if 多個 CONFIRMED stack；`+5` if CANDIDATE 但無 CONFIRMED
  - `calculate_theme_heat()` 加新參數 `structural_tier_hits` 並加進 final raw
- `skills/theme-detector/scripts/theme_detector.py`:
  - `_theme_has_structural_shift()` 改回傳 3-tuple 含 `tier_counts: {CONFIRMED, CANDIDATE}`
  - main scoring loop 把 tier_counts 餵 calculate_theme_heat → heat 真的會升
  - heat_breakdown 新欄位 `structural_shift_bonus` + `structural_tier_counts`
  - 移除舊 fundamental_override 重複 call（V2.18 寫了兩次）

### Why
- V2.18 只 hack lifecycle stage label，heat score 本身沒動 → ranking 沒反映 paradigm shift
- V2.19.2 直接動 heat → ranking 跟著改（AI&Semis 從第 3 升第 1，heat 52.8→62.8 +10 bonus）
- 個股 ⚡ badge 在 V2.19.1 只在 index.html audit cards 上，decisions/earnings 主頁面看不到 — 補完
- backtest forward returns 從 stub 變實做：今天就跑得出 directional sanity（n=7 17 天 mean SPY-alpha +18.4%）

### Smoke
- `python3 investment/scripts/backtest_watchlist.py` → 7 candidates 全 partial data，15d SPY-relative mean +18.4% hit_rate 7/7，sector-relative mean +4.6% hit_rate 4/7（caveat: n 小 + 單一 sector + lookback bias）
- `python3 skills/theme-detector/scripts/theme_detector.py` → AI&Semis heat 52.8→62.8 (+10 MU+NVDA bonus)、Quantum Computing 52.7→62.7 (+10 MU bonus)
- `python3 -m py_compile` 全 OK

---

## [2.19.1] — 2026-05-10
### Added — Structural Watchlist UI + archival 接線（為未來 backtest 準備）

### Added
- `news/scripts/build_structural_watchlist.py`:
  - `_write_history_snapshot()` — 每日寫 `news/news_logs/watchlist_history/<DATE>.json` snapshot（atomic）
  - `_emit_lifecycle_events()` — append-only `news/news_logs/watchlist_lifecycle.jsonl` 事件記錄
  - 事件 enum: `first_seen / continued / evicted / graduated_candidate / graduated_confirmed`
  - graduation 對 earnings-analyst cache `structural_shift.tier` 即時偵測（CANDIDATE/CONFIRMED）
- `bridge.py`:
  - `load_structural_watchlist()` — 讀 `news/news_logs/structural_watchlist.json`，注入 `data.json.structural_watchlist` (top 10 candidates + hot_sectors + decay_rules + freshness)
  - main flow Step 6 接線（Tactical Step 5 之後）
- `Dashboard/index.html`:
  - Layer 5 — `<section id="structural-watchlist">` 新增 watchlist tile（藏起來預設，data 有才秀）
  - i18n key: `watchlist_title / watchlist_badge / watchlist_subtitle / watchlist_disclaimer`（中英文）
- `Dashboard/script.js`:
  - `renderStructuralWatchlist(sw)` — 渲染 candidates 卡片（ticker / sector / hits / credibility / days_since_last / keywords / first_observed），點擊跳到 decisions.html
  - `decorate()` 擴充：crossSet ⭐ 之外加 `watchlistSet` ⚡ 黃色 lightning badge
- `Dashboard/i18n.js` — 中英 4 個 watchlist label
- `investment/scripts/backtest_watchlist.py` (新檔):
  - 讀 lifecycle.jsonl + earnings cache
  - `compute_tier_lead_time()` — first_seen → graduation lead time stats
  - 4 outcome 分類: confirmed / candidate / still_active / evicted_no_graduation
  - Forward return stub (V2.20 寫 FMP 整合)
  - 輸出 `reports/WATCHLIST_BACKTEST_<DATE>.md` + JSON

### Why
- V2.19.0 watchlist 每天 atomic rename 蓋掉舊檔 → 沒歷史資料 → 2 週後想 backtest 沒 raw data 可用
- V2.19.1 補 archival 緊急修補：每日 snapshot + append-only lifecycle log，**不做的話未來無法驗證 watchlist signal 質量**
- UI 接線：watchlist 從 metadata-only file 變成 dashboard 看板上的早警示，user 可以提早注意 paradigm shift 候選股
- backtest skeleton 兩週後就能跑：tier graduation rate（hit rate） + lead time（多早預警）+ 後續 V2.20 加 forward returns（alpha 對比 SPY/sector ETF）

### Smoke
- `python3 news/scripts/build_structural_watchlist.py` → 7 candidates / 1 hot sectors / 9 lifecycle events（含 NVDA→graduated_candidate / MU→graduated_confirmed）
- `python3 bridge.py` → `[OK] Watchlist: 7 candidates / 1 hot sectors (0.1h)` 注入 data.json
- `python3 investment/scripts/backtest_watchlist.py` → `7 tickers / 1 CONFIRMED / 1 CANDIDATE` rc=0
- compile-check：build_structural_watchlist.py + backtest_watchlist.py 全 OK

### Out of Scope (V2.20)
- backtest_watchlist.py forward returns 部分（FMP price fetch + SPY/sector ETF alpha）
- watchlist → earnings-analyst tier 觸發 tie-breaker（需先 backtest 證明 signal 質量）
- decisions.html / earnings.html 個股級 ⚡ badge（目前只在 index.html audit cards 上）

---

## [2.19.0] — 2026-05-10
### Added — Lane Cross-Talk Wiring (Phase 3 polarization + Red Team anti-spoof + News watchlist)

### Added
- `investment/scripts/apply_det_shadow.py`:
  - `compute_polarization()` 升 4-tier (BIPOLAR/OUTLIER/MIXED/ALIGNED)。BIPOLAR 規則加 `pos_strong ≥ 2 AND neg_strong ≥ 2` direction count，避免 4-vs-1 outlier 誤判（例 `[+4,+3,+3,+2,-2]` 修前 BIPOLAR、修後 OUTLIER）
  - `classify_red_team_basis()` — V2.19 anti-spoofing classifier。4-tier basis：`pure_forward / pure_mean_reversion / contaminated / unclassified`。LLM 偷渡 mr (塞 1 個 fw keyword 偽裝) → 標 `contaminated`，CONFIRMED tier 下視同純 mr 觸發降級
  - `apply_to_trade()` 寫 `red_team_basis` 入 det_shadow block
- `investment/scripts/validate_v219.py` — 16 fixture (10 polarization + 6 basis)，含 Gemini outlier case 與 contamination spoof test
- `investment/investment_protocol_v5_0.md`:
  - Phase 3 **Step 1.7** Lane Polarization Modulation (4-tier，BIPOLAR ×0.5 confidence + cap 25% + BUY→STAGED_ENTRY；OUTLIER ×0.85；MIXED ×0.75；ALIGNED 不動)
  - Phase 3 **Step 2** anti-spoofing 邏輯：CONFIRMED + (pure_mr OR contaminated) → STRONG_COUNTER auto-downgrade MODERATE + penalty 折半
  - Phase 2.8 Red Team prompt 加 `STRUCTURAL_SHIFT_TIER` input + 條件指令 (CONFIRMED 必引 forward mechanism)
  - Phase 4 Step 4 Sizing 加 `polar_adj` 串聯 (BIPOLAR 強制 ×0.25 跟 V2.18 shift_adj 串接)
  - Phase 3 JSON shape 加 `polarization_modulation` + `red_team_basis` + `red_team_auto_downgrade` 欄位
- `investment/phase5_export_schema.md`:
  - det_shadow 升 V2.19 schema：`signal_polarization` 4 值、`pos_strong/neg_strong`、`red_team_basis` 4-tier
  - 新增 Phase 3 Step 1.7 modulation 對照表 + Red Team basis 判定規則
- `investment/scripts/validate_session_export.py`:
  - 新增 `det_shadow.signal_polarization` enum 檢查（V2.19 4-tier）
  - 新增 `det_shadow.red_team_basis` enum 檢查
  - det_shadow 缺欄 → schema fail
- `news/news_protocol_v2.md` Phase 4.5 — Structural Watchlist 段落（schema、decay rules、daily cron 規範、V2.19 約束 metadata-only）
- `news/scripts/build_structural_watchlist.py` (新檔):
  - 14 keyword whitelist (sold out / capacity constrained / supercycle / 供不應求 ...)
  - 14d hit window + 21d eviction + ≥2 sources first-hit gate + url stem / 8-gram dedup
  - sector aggregation + atomic temp+rename + failure non-fatal
  - 已 smoke 跑通：7 candidates / 1 hot sector (TSM/MU/NVDA/ASML 在 Memory Semis)
- `daily_update.sh` — Step 7 接線 (1/6 → 1/7 全部更新)，failure non-fatal

### Why
- V2.18.0 解 MU/QCOM 超級週期錯失只是繃帶；user 反思指出「lanes 各自為政」病根沒治
- Gemini 三提案 critical eval：
  - **#1 News provisional 強版 REJECT** — IR boilerplate / reflexive loop / mosaic violation；輕量版 (watchlist metadata-only) DO
  - **#2 Cross-lane divergence DO 但簡化** — `compute_polarization` 已存在，Gemini stdev 提案是重造輪子
  - **#3 Red Team dynamic prompt DO 雙層** — prompt + post-filter classifier 防 LLM jailbreak
- V2.19 = wiring + hardening release，不是 feature release。把 V2.18 留下的 dangling hook (`red_team_basis="mean_reversion_only"` 行 604) + 現存沒接線的 `compute_polarization` 串起來
- 三條 anti-adversarial 鐵律：
  1. **mr 一票否決**：mean-reversion keyword 一旦出現都觸發 dampening（contaminated 不是 mixed）
  2. **OUTLIER 不誤殺**：4-vs-1 outlier 不是真衝突 (×0.85 不像 BIPOLAR 砍倉)
  3. **Watchlist 強制衰減**：14d/21d 防幽靈數據，single-source 不入榜

### Smoke
- `python3 investment/scripts/validate_v219.py` → PASSED 10 polarization + 6 basis fixtures (含 Gemini outlier + contamination spoof)
- `python3 news/scripts/build_structural_watchlist.py` → 7 candidates / 1 hot sector (Memory Semis: TSM/MU/NVDA/ASML)
- compile-check：apply_det_shadow.py / validate_v219.py / validate_session_export.py / build_structural_watchlist.py 全 OK

### Out of Scope (V2.20)
- News provisional → 直接驅動 tier modulation（須先 backtest watchlist 是否能可靠當 leading indicator）
- backtest 餵回 V2.18/V2.19 modulation 參數 auto-tune
- macro_multiplier 改 sector × duration sensitivity matrix
- Theme-detector heat 公式納入 sector aggregate EPS momentum (V2.18 只 hack lifecycle stage)

---

## [2.18.0] — 2026-05-10
### Added — Structural Shift Modulation: 解 MU/QCOM 超級週期錯失 systemic bug

### Added
- `skills/earnings-analyst/scripts/analyze.py` — `compute_structural_shift()`：偵測 EPS QoQ ≥30% / GM ≥ historical+2σ / revenue YoY ≥25% AND accelerating 三 signal，≥2 → CANDIDATE，連 2 季 → CONFIRMED。獨立 signal，不影響 composite_score
- `skills/earnings-analyst/schema.md` + `SKILL.md` — `structural_shift` 區塊文件化（tier / signals / metrics / 設計理由）
- `investment/scripts/register_thesis.py` — `_read_structural_shift()`：thesis registry 自動接收 latest earnings cache 的 structural_shift block，存入 thesis_data
- `investment/investment_protocol_v5_0.md` Phase 3 **Step 1.5 Structural Shift Modulation**：
  - CONFIRMED → analyst-PT weight ×0、Red Team mean-reversion attack BLOCKED、shift_macro_floor=1.00、position_cap=100%
  - CANDIDATE → analyst-PT ×0.3、STRONG_COUNTER penalty 折半、shift_macro_floor=0.95、position_cap=50%
  - NONE/INSUFFICIENT_DATA → 標準規則
- Phase 3 JSON shape 加 `calculation_steps.structural_shift_modulation`（tier/applied_adjustments/shift_macro_floor/position_size_cap_pct/red_team_mean_reversion_blocked）
- Phase 4 Step 4 Sizing 加入 `shift_adj = ftd_adj × (position_size_cap_pct/100)`，將 shift cap 套在所有其他乘數之後
- `skills/theme-detector/scripts/calculators/lifecycle_calculator.py` `classify_stage()` — 新增 `fundamental_override` param：true 時門檻整體往後拉（80→95 才算 Exhausting），避免 paradigm-shift sector 被技術面過熱誤判
- `skills/theme-detector/scripts/theme_detector.py` `_theme_has_structural_shift()` — 掃 representative stocks 的 earnings cache，命中 CANDIDATE/CONFIRMED 即觸發 fundamental_override；scored_theme 額外輸出 `structural_shift_override` + `structural_shift_hits`

### Why
- MU/QCOM 案例復盤：超級週期股票被三個 backward-looking 模型同時壓制 → DEFENSIVE HOLD，錯失主升段
  - Valuation lane：被滯後 analyst PT 拖累（MU 4/24 Q2 blowout 後 PT 還停在 $455 / 算出合理價 $549 vs 市價 $714）
  - Red Team：用「記憶體歷史 GM 30-35%、現在 74% 是 Peak Cycle」mean-reversion 攻擊
  - Macro：Theme Detector 把 Semis 標 Exhausting → Phase 0 sector_avoid → multiplier ×0.9
- 機制設計（不是 override，是 dampening）：
  - 1Q earnings blowout 即可觸發 CANDIDATE（避免 2Q 確認太慢，主升段已過）
  - 但 CANDIDATE position cap 50% 防止單季 noise 變 bubble-top BUY
  - CONFIRMED 才完全解除錨點，且 Red Team 必須 forward mechanism breakage 攻擊（不接受純歷史均值論證）
- 對稱性：missing top = bounded loss、buying top = unbounded loss → tier 階梯保護後者
- 校準：MU=CONFIRMED (eps_qoq +163%/gm z=4.18/rev_yoy +196%)、NVDA=CANDIDATE、AAPL/AMD/ARM=NONE

### Smoke
- `python3 skills/earnings-analyst/scripts/analyze.py MU` → composite=80/100 verdict=STRONG **shift=CONFIRMED**
- `python3 skills/earnings-analyst/scripts/analyze.py NVDA` → composite=86/100 verdict=STRONG **shift=CANDIDATE**
- `python3 skills/earnings-analyst/scripts/analyze.py AAPL` → composite=70/100 verdict=SOLID shift=NONE
- `_read_structural_shift()` & `_theme_has_structural_shift()` 直接 import 測通

---

## [2.17.26] — 2026-05-10
### Fixed — verdict_deep_dive 方向推論支援 V5.0 動詞 action（STAGED_ENTRY / EXECUTE）

### Fixed
- `scripts/verdict_rules.py` `verdict_deep_dive` — substring matching 換成 V5-aware 顯式 mapping：
  - **BUY 類**：`{BUY, LONG, EXECUTE, STAGED_ENTRY, STAGED}` → direction = "buy"
  - **SELL 類**：`{SELL, SHORT, STAGED_EXIT}` → direction = "sell"
  - **HOLD 類**：HOLD / CANCEL / unknown → direction = "hold"
  - 保留 substring 兜底（cover 多字串如 `BUY (T2)`）

### Smoke result
| metric | baseline | 修後 |
|---|---|---|
| MU 6 staged/execute records | all miss | all **hit** ✓ |
| STAGED_ENTRY miss_rate | 72% (21/29) | **17%** (5/29) ✓ |
| EXECUTE miss_rate | 75% (6/8) | **25%** (2/8) ✓ |
| 整體 deep-dive hit_rate | 40% (44/109) | **55%** (60/109) ✓ |
| 整體 deep-dive miss_rate | 54% (59/109) | **37%** (40/109) ✓ |

### Why
- User 觀察 MU 幾乎全 miss，例：2026-05-01 STAGED_ENTRY score 1.22 / 9 天 +37.73% 卻判 miss
- Root cause：V2.17.18 parser 修完後 final_action 正確帶到 V5 verbs，但 verdict 邏輯沒同步 — V5 verbs 不含 `BUY` substring，全 fallthrough 到 hold → 觀望 + 正報酬 = "錯過上漲" 假 miss
- 影響：REVIEW_2026-05-09 Pattern 1（mega-cap repeat-miss：AMD / MU / NBIS / GOOGL）有大半是這個 verdict bug 製造的 artifact，不是真策略失敗
- 修法：純 verdict label 邏輯，不動策略本身。下週 REVIEW Pattern 1 會大幅縮水，Hypothesis A（Bull regime under-call）需用乾淨資料重評

### Ledger
- `ADJUSTMENT_LEDGER.md` 新增 entry 追蹤本修法 metrics

---

## [2.17.25] — 2026-05-10
### Fixed — theme-detector extractor 升級到 header-name lookup（解決 0 themes detected）

### Fixed
- `scripts/extractors/theme_detector_extractor.py` `_find_themes` — 重寫成 header-driven column resolution：
  - 偵測 Theme Dashboard table 第一行 header
  - 用名稱映射（"theme"/"direction"/"heat"/"stage"/"confidence" + alias 如 "dir"）找到每個欄位的 cell 索引
  - 後續資料 row 用索引取值，不再依賴固定欄位順序
  - skip markdown separator row（`|---|---|...`）
- 新格式（V2 2026-04-23+）`Theme | Origin | Direction | Heat | Maturity | Stage | Confidence` 7 欄、無 # 索引
- 舊格式 V1 / 中英雙語 header `# | Theme 主題 | Dir 方向 | Heat 熱度 | Stage 階段 | Confidence 信心` 也通

### Smoke
| report | before | after |
|---|---|---|
| theme_detector_2026-04-11 | 0 themes | **10 themes** ✓ |
| theme_detector_2026-04-23_220833 | 0 themes | **10 themes** ✓ |
| theme_detector_2026-04-25_004154 | 0 themes | **10 themes** ✓ |

verdict 全 5 筆現在算出真實 hit/miss/neutral：4/11 miss (3/9 跑贏)、4/23 neutral 4/7、4/23 hit 6/9 ×2、4/25 hit 6/9。

### Why
- User 截圖：theme-detector drill 5 筆「0 themes detected」+ verdict 全 PENDING/MISS — root cause: extractor 寫死「第一格必須是數字 #」，新報告把 # 列拿掉 → 全 skip
- 修法：header-name 映射不依賴欄位順序 / 個數，未來 schema 再加欄位也不會破

### 規則重申（user 問）
- Window 10 個交易日
- 對每個 LEAD 主題：proxy_etf 5d/10d 跑贏 SPY → hit；輸 SPY → miss
- 聚合：hit_rate ≥ 60% HIT / ≤ 40% MISS / 中間 NEUTRAL
- LAG 主題（看空）目前 verdict 沒評，待後續加 symmetric check

---

## [2.17.24] — 2026-05-10
### Fixed — Drill row 現實行覆蓋更多 source（thematic / theme / momentum / earnings）

### Fixed
- `Dashboard/page-calendar.js` `_drillRealityLine` — 原本只處理 `ticker_reality` + `spy_return_pct`，多數 market-wide source 顯示「—」。新增分支：
  - `mover_returns`（thematic-screener）→ 顯示「X/Y 方向對」+ 前 5 檔 mover ±%（hit 綠 / miss 紅）
  - `etf_returns`（theme-detector / sector-scan）→ SPY 報酬 + 前 4 檔 ETF rel-to-SPY
  - `ticker_returns`（earnings-analyzer）→ 前 4 檔 ticker ±%
  - `per_ticker`（momentum-screen）→ N/總 命中比率（綠/黃/紅 by hit rate）
- 仍保留 `ticker_reality`（deep-dive）+ `spy_return_pct`（news-digest）+ pending fallback

### Why
- User 截圖：thematic-screener 5 筆 row「現實」全是「—」但 verdict 已是 NEUTRAL/MISS，讓人疑惑判定基礎
- root cause：mover_returns 已寫進 reality_at_eval（每筆 19-20 個 ticker），但 row renderer 沒讀
- 修後 row 直接顯示 movers 命中比 + 前 5 檔對齊狀況

### 雷達評斷規則（user 問）
- Window 5 個交易日
- 每檔 mover：target_5d_pct 方向 × actual_5d 方向 對 → hit
- 聚合：hit_rate ≥ 60% HIT / ≤ 40% MISS / 中間 NEUTRAL
- 只看方向不看幅度；mover_returns 缺 → PENDING

---

## [2.17.23] — 2026-05-10
### Fixed — Drill modal 改用 CSS vars 跟頁面 theme 連動（不再硬寫深色）

### Changed
- `Dashboard/style.css` drill modal CSS：
  - `cal-drill-shell` / `cal-drill-header` / `cal-drill-body` / `cal-drill-row` 全部從 hardcoded 顏色改成 `var(--bg-card)` / `var(--bg-main)` / `var(--bg-header)` / `var(--text-main)` / `var(--text-card-title)` / `var(--text-muted)` / `var(--border)` / `var(--border-hover)` / `var(--sidebar-active-bg)` / `var(--primary)` / `var(--danger)`
  - 移除所有 `!important` 硬蓋（不再需要對抗 page theme）
  - 移除 `.cal-drill-modal .text-zinc-* / text-green-400 / text-red-400` 強制改寫（既然跟 theme 連動就不需）
  - badge 顏色 layered：default 適合淺色背景的深綠/深紅/深琥珀（light theme readable），`[data-theme="dark"]` override 為亮綠/亮紅/亮黃（dark theme readable）
  - reason highlight box 顏色同樣 dual-theme：light 用 `#92400e` (amber-800)，dark 用 `#fde68a` (amber-200)，背景半透明 amber 對兩 theme 都通
  - heat chip 同 dual-theme handling

### Why
- User 反問：page 是 light theme 為什麼 modal 硬選深色？
- Root cause：先前修法為了解決「page color leak」直接 hardcode 深色 + `!important` 蓋掉，違反 theme 一致性 — light 頁面開深色 modal 視覺斷裂
- 正解：用 CSS vars，site theme 切換自動 propagate；保留先前的 layout 結構，只換顏色 token
- 副作用：dark mode 下會用 `[data-theme="dark"]` override 提供亮色 badge，light 不需 override 直接用 default

---

## [2.17.22] — 2026-05-10
### Fixed — Stale price → pending（不再誤判 HIT）+ drill modal 配色變淺更舒適

### Fixed
- `scripts/build_event_index.py` `compute_reality_for_ticker` — 偵測 yfinance fallback 把 eval bar 對齊到 decision-day 的情況（`e_key == d_key`）→ 回傳 None 強制下游 verdict 變 `pending`
  - 影響：本日後 deep-dive（window 未完成且無新 bar）不再被算成 +0% HIT；MU / CRWV / NEE 2026-05-08 三筆從 hit → pending（價格 746.81 → 746.81 0% 那種）
  - **報告本身也跟著更新**（event_index 重跑後所有 source 同步）；下週 REVIEW 跑 Step 0 protocol 會自動讀新 JSON

### Changed
- `Dashboard/style.css` drill modal 配色重設：
  - shell `#18181b` → `#2a2d36`（slate-tinted, 不再純黑）
  - row `#27272a` → `#383b46`（拉淺一階對比 shell）
  - row hover `#3f3f46` → `#43475a`
  - border `#3f3f46` → `#474b58`
  - reason 行字色 `#fbbf24` → `#fde68a`（柔和琥珀 amber-200）
  - tailwind utility hard-overrides 全部 +1 階亮度（zinc-400 → #b8bdc9 等）
  - backdrop 從 zinc → slate tint，blur 4 → 6px 更柔
  - header 用 slate gradient

### Why
- User 截圖 V2.17.21：MU/CRWV/NEE 2026-05-08 顯 ✅ HIT，實際 746.81 → 746.81 +0.00% 是 yfinance 沒新 bar → reuse decision-day price 假裝有 return
- Root cause：`closest_price(prices, eval_date, "before")` fallback 到最後一個有 bar 的日期；當 eval 在 today 且 today 沒收盤 → e_key == d_key
- 修法：data 層直接判 e_key==d_key → return None → 走 verdict_deep_dive 既有 None branch → pending
- 配色：原 #18181b/#27272a 太重，user feedback「底色太深」，改 slate-tinted 中間調

### Side effect
- aggregate 計數變動：deep-dive hit 50→44 / miss 60→59 / neutral 7→6 / pending 11→3（pending 集中到「真窗口未到」+「stale price 三筆」），餘 6 筆原 pending 為 parser 修好後可評估的，自動轉 hit/miss

---

## [2.17.21] — 2026-05-10
### Fixed — Drill-down row 顏色 cascade leak（rows 全部黑底看不見內容）

### Fixed
- `Dashboard/style.css`：
  - 所有 row selectors scope 加 `.cal-drill-modal` 前綴，阻擋 page light-mode 層級規則洩漏
  - `.cal-drill-shell` 加 `color: #e4e4e7` 強制 base text
  - row bg 從 `rgba(39,39,42,0.55)` 改 solid `#27272a`（zinc-800），跟 modal shell `#18181b` 對比夠
  - 所有 row 內 text-color rules 加 `!important` 抗 Tailwind utility（`text-zinc-*` / `text-green-400` / `text-red-400`）
  - row 加 `min-height: 86px` 避免 flex 收縮成幾乎不可見
  - reason 行新增 `background: rgba(251,191,36,0.08)` + 左 border 2px 變 highlight box
  - tailwind utility colors（`text-zinc-400/500/600` / `text-green-400` / `text-red-400`）在 modal 內 hard-override 為深色背景下看得到的色階

### Why
- User V2.17.20 截圖：modal 一片黑、128 row 縮成一條條細線、無 text 可見
- Root cause：page 在 light mode → body 套 `color: #18181b` 繼承到 modal；modal 用 dark bg 但 text 顏色被 page rule 蓋成黑色 → 黑底黑字
- row bg `rgba(39,39,42,0.55)` alpha 過低，跟 `#18181b` modal shell 視覺幾乎一致 → row 邊界看不清
- 解法：每條 rule 加 `.cal-drill-modal` scope + 文字 `!important`，CSS specificity 提升一級超過 page 規則

---

## [2.17.20] — 2026-05-10
### Fixed — Drill-down modal UI 重做（compact row, no raw button, prominent reason）

### Changed
- `Dashboard/page-calendar.js`：
  - 廢棄 `renderDecisionCard` reuse（cal-card light-mode 顏色在 dark modal 顯不出 + 帶 raw button）
  - 新增 `renderDrillRow(d)` + `_drillDecisionLine(d)` + `_drillRealityLine(d)` per-source 一行抽 decision / reality 摘要（9 source 全覆蓋）
  - 每筆 row：左色帶 + verdict pill badge + source icon + ticker logo + date + window 進度 + decision 行 + reality 行 + **reason 行（橘色 prominent）** + heat chip
  - 移除 raw 報告 link
- `Dashboard/style.css` — 新 `.cal-drill-row*` styles（自帶深色背景 + verdict badge 4 色 + reason 黃橘色強調行 + chip）

### Why
- User 截圖：reuse `renderDecisionCard` 後在 modal 顯示成「白色空 pill」— root cause: `cal-card` 用 `var(--bg-card)` 是頁面 theme 變數（light mode = white），dark modal 上看起來像空白；body text 顏色 inherit 也錯亂
- User 不需 raw button（占空間 + 干擾），但要看「簡單原因」 — verdict.rationale 提到 row 中央用橘色行顯示
- 每筆 row 高度約 90-110px，128 筆 dollar-friendly scroll；4 行布局 (head / decision / reality / reason / chip) 一眼看完

### Layout 規格（每筆）
```
║ [✅ HIT] 📈 [logo] AMD 2026-04-15           w 115% (23/20d)
   DECISION  BUY · score 1.21 · pos 5%
   REALITY   192.50 → 295.00  +53.20%   max +63 / dd -2
   REASON    return ≥ 30% within 20d → HIT
   🔥 Semiconductors · sector #1 · top 30%
```

---

## [2.17.19] — 2026-05-10
### Added — Decision-review category drill-down modal

### Added
- `Dashboard/calendar.html` — `<div id="cal-drill-modal">` 容器（modal shell + header + filter + sort + close + body）
- `Dashboard/style.css` — modal / backdrop / header / filter pill / sort dropdown / close button / heat chip styles（~135 行）
- `Dashboard/page-calendar.js`：
  - `cal-stat-tile` 加 `data-drill-source` + click/keyboard handler → `openDrillDown(source)`
  - `openDrillDown` / `closeDrillDown` / `renderDrillDown` / `wireDrillDown` — fullscreen modal with verdict filter pills、sort dropdown（date/return/score）、ESC + outside click close
  - `renderHeatChip` — V2.17.16 `sub_industry_heat` 取出 industry / sector_rank / top_30%? 視覺 chip（hot/cold 兩態），append 到每張 card 末
  - 直接 reuse 既有 `renderDecisionCard` → 9 source body 自動覆蓋（deep-dive / sector-scan / news-digest / theme-detector / momentum-screen / thematic-screener / earnings-analyzer / short-term-weekly / postmortem）

### Why
- User 看到「深度分析 128 筆」summary tile 想點進去看每筆當初決策 + 現實 + verdict
- 既有 `renderDecisionCard` 已含 verdict 色帶 + emoji badge + per-source body + raw_path link，drill-down 直接 reuse 不重寫；只補：modal shell / 篩選 pill / sort / 視覺化 industry heat chip
- chip 利用 V2.17.16 sub_industry_heat instrumentation：top 30% sub-industry 顯橘紅 🔥；其他 cool 灰，一眼看出是不是熱門族群的決策（可解釋 miss 為何集中）
- 9 類全自動覆蓋（不分流）— 任何新 source 接到 calendar 都自動有 drill-down

### 互動細節
- tile hover：浮起 + 陰影
- modal: backdrop blur, animate-in scale + slide
- filter pills 顯示 verdict count；count=0 自動隱藏（除 "all"）
- sort: date↓/↑、return↓/↑、score↓
- ESC / 點 backdrop / 點 ✕ 都關閉

---

## [2.17.18] — 2026-05-10
### Fixed — Decision-review parsers 跟上 V5.0 schema（Rec 1 + Rec 4）

### Fixed
- `scripts/extractors/deep_dive_extractor.py` `_find_decision` — 新增 V5.0 patterns：
  - `**Final Decision**` / `**最終決議**` 表頭（值可加粗或不加粗）
  - `**Action Label**`（DEFENSIVE / OFFENSIVE / NEUTRAL …）
  - 內文裸 `EXECUTE` / `STAGED_ENTRY` / `STAGED_EXIT` 動詞
  - parenthetical secondary action 自動剝（`HOLD (CANCEL)` → `HOLD`）
- `scripts/extractors/deep_dive_extractor.py` `_find_final_score` — 新增 V5 table row + case-insensitive body form + 全形冒號 + table cell `| final score | 2.055 |`
- `scripts/extractors/news_digest_extractor.py` `_find_macro_delta` — 新增 `(session_macro_delta +0.20)` parenthetical + JSON-ish 形式 + Greek `Δ` headers（May 2026+ digests 改用 Δ 不再是 "Delta"）

### Smoke result
| metric | baseline | 修後 |
|---|---|---|
| deep-dive `final_action is null` | 52% (58/112) | **2.7%** (3/112) ✓ |
| deep-dive `final_score is null` | ~16% (~18/112) | **6.2%** (7/112) ✓ |
| news `macro_delta is null` | 59% (13/22) | **27.3%** (6/22) ✓ |

殘留：3 筆 deep-dive + 6 筆 news 全屬 v1/legacy protocol 格式（legit n/a，非 parser bug）。

### Why
- REVIEW_2026-05-09 Hypothesis B + Rec 1 / Rec 4 標 high conf prerequisite — 不修這兩個解析器，所有 strategy-level pattern 數字都被污染（unknown 跟 n/a 拉爆 hit/miss 比率），無法評估 Rec 2 / 3.5 等策略 Rec 是否該 apply
- 純 instrumentation 修法：parser 跟上現實格式，**完全不動決策邏輯** → 下週 deep-dive / news-digest 報告**內容跟本週一樣**，但 REVIEW 看到的數字會是真的
- Ledger 新增 Rec 1 + Rec 4 entries，下週 REVIEW Step 0 會自動跑 evaluation_history 比對

---

## [2.17.17] — 2026-05-09
### Changed — `llm_review` protocol prompt 同步 4-step REVIEW flow

### Changed
- `dashboard_server.py` `SCRIPT_PROTOCOLS["llm_review"]` — protocol prompt 從「三步驟」改「四步驟」，明加 Step 0 Adjustment Evaluation；Step 1 加引用 `industry_rollup` + `sub_industry_heat`；Markdown 輸出 schema 加「## 0. Adjustment Evaluation」+「## Industry Rollup」表頭範本；Step 0 indexer rebuild 描述加 `industry_rollup` + `adjustment_ledger_active` 兩個新 top-level 欄位

### Why
- V2.17.16 改了 `REVIEW_PROMPT.md` 變 4-step 但 `dashboard_server.py` 內嵌的 protocol prompt 還寫「依 REVIEW_PROMPT 三步驟執行」 → 用戶按「請 LLM 檢討」按鈕觸發的 LLM 會跳過 Step 0 Adjustment Evaluation
- 兩處 prompt 必須同步，否則 ledger evaluation 形同虛設
- V2.17.17 後按按鈕 → server `subprocess` 跑 `build_event_index.py`（Step 0 已寫入 protocol）→ LLM 收 prompt 自動跑 4-step → write `REVIEW_<DATE>.md`，不需手動串接

---

## [2.17.16] — 2026-05-09
### Added — Decision review: sub_industry_heat + industry rollup + adjustment ledger

### Added
- `scripts/_sector_heat.py` (NEW) — `enrich_ticker_heat(ticker)` 共用 join helper：合 latest `sector_intel` (sector composite_score / rank) + `theme_detector` (theme heat / direction) + `fmp_industry/snapshot` (industry averageChange / rank) + `company_context.get_profile` (sector / industry resolve)
- `scripts/build_event_index.py` `_build_industry_rollup` — 把 deep-dive verdict 按 `tuning_hooks.sub_industry_heat.ticker_industry` 聚類，輸出 `event_index.industry_rollup`（n / hit / miss / miss_rate / avg_miss_return / industry_top_30pct）
- `scripts/build_event_index.py` `_load_adjustment_ledger` — parse `ADJUSTMENT_LEDGER.md` 中 `status: active` 的 Rec entries，注入 `event_index.adjustment_ledger_active`
- `reports/decision_review/ADJUSTMENT_LEDGER.md` (NEW) — 系統調整 ledger，含 Rec 7 / Rec 8 / Pill alignment 三筆 entry
- `reports/decision_review/ADJUSTMENT_LEDGER_SCHEMA.md` (NEW) — schema + 維護規範
- `event_index.json` schema bump v1.0 → v1.1（新增 industry_rollup + adjustment_ledger_active 兩個 top-level 欄位）

### Changed
- `scripts/extractors/deep_dive_extractor.py` — `tuning_hooks` 加 `sub_industry_heat` 欄位（fail-soft：若 join helper 失敗只寫 `{"error": "..."}`，不影響其他欄位）
- `reports/decision_review/REVIEW_PROMPT.md`：
  - 新增 Step 0「Adjustment Evaluation」— LLM 開頭先讀 ledger，對每筆 active Rec 比對 metric 變化下 improved / no_change / regressed 判斷
  - 輸出格式新增「## 0. Adjustment Evaluation」表 + 「## 1.5 Industry Rollup」表

### Why
- User 觀察：本週 CPU+memory 市場共識強 / 光通訊+SaaS 弱，但 REVIEW_2026-05-09 的 Pattern 1 只看 ticker（AMD/MU/INTC repeat-miss），沒做 sub-industry rollup → sector heat asymmetry 完全沒進系統考量
- Root cause：`tuning_hooks` 沒 industry context 欄位 → REVIEW 只能用 ticker 名單表達 pattern，無法量化 sector tail-wind 跟 deep-dive miss 的關聯
- Rec 7 補 instrumentation（純資料注入，不改決策邏輯），下週 REVIEW 即可跑 industry rollup
- Rec 8 把 rollup 做進 build_event_index post-process，讓 REVIEW 開段就能引用
- Adjustment Ledger 解決「系統調整不被回測」的 meta-bug — 之前 Rec 應用後沒檔案紀錄，每次 REVIEW 等於從零開始無法評估前次調整是否有效。Ledger 把每筆 Rec 變成可追溯的實驗（hypothesis + target_metric + evaluation_history）

### 樣本驗證（smoke）
- `python3 scripts/_sector_heat.py AMD MU` → 兩檔正確 resolve 為 Technology / Semiconductors / sector_top_3=true / industry_top_30pct=true
- `_build_industry_rollup` 用 fake records 測試：Semiconductors bucket n=2 miss_rate=1.0 avg_miss_return=50.45 ✓
- `_load_adjustment_ledger` 從 ADJUSTMENT_LEDGER.md parse 出 3 個 active entry ✓

---

## [2.17.15] — 2026-05-09
### Fixed — Sector pill ring 全面對齊 tooltip 5-tier 語義

### Fixed
- `Dashboard/script.js` `pill-marketop` — 改 inline 5-tier 對齊 tooltip：≥80 紅 / ≥65 橙 / ≥50 琥珀 / ≥30 黃 / <30 綠（原本 `'amber'` polarity 全 amber，0-29 normal 應綠卻黃、80+ top 應紅卻 amber）
- `Dashboard/script.js` `pill-fg` — 改 inline 5-tier contrarian：≥75 紅 / ≥55 橙 / ≥25 黃 / <25 綠（原本 `'amber-bell'` 全 amber，extreme_fear 應綠 contrarian buy / extreme_greed 應紅卻都 amber）
- `Dashboard/script.js` `pill-cycle` — Mid 顏色 `#84cc16` lime → `#eab308` yellow 對齊 cy_mid 🟡；新增 `map` 欄位，`Distribution` 為 canonical key（保留 `recession` legacy alias）；segment label `REC`→`DIST`
- `Dashboard/script.js` `pill-vix` — 3-tier (18/25) → 5-tier (20/30/40) 對齊 vx_calm/normal/elevated/high/panic：≥40 紅 / ≥30 橙 / ≥20 黃 / <20 綠（原本 VIX 19 應綠卻 amber、VIX 32 應 amber 卻紅）

### Why
- User 看到 33 廣度分（5/8 修）後追問「所有 pill 一起檢查」
- 全 audit 發現 4 個 pill colors 跟 tooltip dot 顏色（🟢🟡🟠🔴）不對齊
- `_gaugeColor(s, 'amber')` 對 marketop 來說語義錯：tooltip 兩端有 🟢 跟 🔴，但 'amber' polarity 永遠回 amber 系列
- `_gaugeColor(s, 'amber-bell')` 同問題：F&G 是 contrarian（fear=綠/buy, greed=紅/sell），bell-shape amber 把方向都丟了
- VIX tooltip 是 5-tier 但 code 只 3-tier，邊界值（VIX 17-19、30-39）顏色錯
- Cycle 的 `Recession` key 跟 tooltip `cy_distribution` 不對齊，data 帶 `Distribution` 進來時 segment 不會 highlight

### 已 OK（無改動）
- `pill-breadth`（V2.17.14 已修 `'positive'`）
- `pill-ftd`（FTD_STAGES 4-tier 對 prime/standard/late_cycle/exhausted ✓）
- `pill-regime`（4 segment 對 RISK_ON/NEUTRAL/VOLATILE/RISK_OFF ✓）
- `pill-exposure`（V2.17.14 hardcode 紫修為 4-tier ✓）

---

## [2.17.14] — 2026-05-09
### Fixed — 廣度分數 ring 顏色跟 tooltip 5-tier 不一致

### Fixed
- `Dashboard/script.js` `_gaugeColor` — 新增 `polarity === 'positive'` 分支，對齊 breadth tooltip 5-tier 語義：≥75 深綠 / ≥60 綠 / ≥40 黃 / ≥25 琥珀 / <25 紅
- 原本 `'positive'` 字串不匹配任何分支，fall through 到 default 3-tier（40 / 70）→ score 33.1 < 40 → 紅，但 tooltip 同樣 33.1 是 `br_weakening` 🟠 琥珀，視覺矛盾
- `Dashboard/script.js` `pill-exposure` — hardcoded `#a78bfa` 紫 → 改 4-tier 對齊 exposure tooltip：≥85 綠 / ≥60 黃 / ≥30 琥珀 / <30 紅（midPct=50 從紫變正確的琥珀）

### Why
- User 截圖：score 33.1 落在 25-40 「走弱中」（tooltip 🟠 琥珀），但卡片 ring 顯示紅色
- Root cause：`_gaugeColor(s, 'positive')` 在原 function 沒有對應 branch → 走 fallback `s>=70 綠 / s>=40 黃 / else 紅`，跟 5-tier tooltip thresholds 不對齊
- Exposure ring 一律紫色（hardcode）跟 tooltip 4-tier 完全不對齊，狀態看不出
- 影響範圍：只有 breadth + exposure 兩處 call

---

## [2.17.13] — 2026-05-08
### Fixed — Heatmap 全頁掛掉（FMP 402 Restricted Endpoint）

### Changed
- `dashboard_server.py` `_heatmap_build_universe` — 改 load `Dashboard/heatmap_universe.json`（static），不再呼叫 FMP `sp500-constituent` / `nasdaq-constituent`
- `dashboard_server.py` `_heatmap_refresh_quotes` — 改 ThreadPool fan-out single `stable/quote`（20 workers default），不再呼叫 `batch-quote`
- `HEATMAP_REFRESH_SEC` default 180 → 600（3 min → 10 min），降低 daily call 量
- 新增 env `HEATMAP_QUOTE_WORKERS`（default 20）

### Added
- `Dashboard/heatmap_universe.json` — 517 ticker static universe（symbol/name/sector/industry），bootstrapped from `Dashboard/heatmap.json` 既有 cache。季度手動 sync。

### Why
- FMP 把 `sp500-constituent` / `nasdaq-constituent` / `batch-quote` 移到高 tier plan → 當前 plan 直接 402 「Restricted Endpoint」，不是 quota 問題（FMP dashboard 看不到用量）
- v3 endpoints 也已 retired (2025-08-31, 403 Legacy)
- heatmap 完全跑不起來（universe 0 rows → quotes 0/517）
- Probe 結果：`stable/quote`（單檔）/ `ratios-ttm` / `key-metrics-ttm` / `analyst-estimates` / `news/stock` / `historical-chart/5min` 仍 200 → 改用 fan-out 可繼續用，PE warmup / news hover / radar K-line 不受影響
- 每 10 min × 6.5h × 517 ≈ 20k calls/day，落在合法 daily 範圍

---

## [2.17.12] — 2026-05-08
### Fixed — 短期雷達 bearish theme top movers 全是 + 預測（方向矛盾）

### Fixed
- `skills/thematic-screener/scripts/screen.py` `select_top_movers_ranked()` — 加 direction-aware 排序：
  - bullish theme → DESC（top-N **最正** target_pct，long candidates）← 既有行為
  - **bearish theme → ASC**（top-N **最負** target_pct，short candidates / 跌勢預期最強名單）← 新增
  - 其他（neutral / unknown）→ DESC

### Why
- User 觀察：「短期雷達的 1d 5d 15d 預測區間怎麼都是+的」— 270 筆預測 232 筆正、37 筆負（86% 正向）
- Root cause：`select_top_movers_ranked` 不論 theme direction 都 sort DESC → bearish 主題（Cybersecurity、Clean Energy & EV、Cloud / SaaS 等）的 top 5 movers **全是該主題裡 5d_pct 最高的**，跟 theme bearish call 自相矛盾
- 例：Clean Energy & EV `direction=bearish` 但 movers 全 + (ORA +1.75 / HASI +1.65 / FSLR +1.84 / ON +2.12 / RIO +1.06)
- 修後 bearish theme 會 surface 跌最兇的 representative_stocks，雷達會出現預期下行的 movers，方向跟主題對齊
- predict.py 模型本身偏多（gamma_momentum × 6 主導，stage 2 stocks 都會給正分）— 這是另一個議題；本 patch 先讓**選股階段**對齊主題方向，方向矛盾的視覺先解掉

---

## [2.17.11] — 2026-05-08
### Fixed — Chain pill terminal 後不消失

### Fixed
- `Dashboard/utils.js` `pollChainPill` — terminal grace 改成從 `s.ended_at` 直接算 age（每 3s tick 算一次），取代原 setTimeout-based 邏輯。原本 timer fire 後 hide pill，但下一次 poll 看到 `status='done'`（server 保留 terminal state 到下次 chain）就 unconditionally 把 `hidden` class 移除 → pill 又跳回來。改 server-side timestamp 算 age：`Date.now() - ended_at > 60000` → 永久 hide 直到下次 chain 跑

### Why
- User 反饋 chain 跑完 ✅ 都顯示完成後 pill 還在右下角不消失
- setTimeout 模型的 race：timer 一次性 fire，但 polling 每 3s 又 unconditionally re-show pill
- Server-side `ended_at` 是真理：以它為基準算 age，每次 poll 都計算同一答案，不需要客戶端 state 追蹤

---

## [2.17.10] — 2026-05-08
### Changed — FTD gauge 顯示 ACTIVE STAGE 取代靜態 100 + 綠圈

### Changed
- `Dashboard/script.js` `renderSectorStatusStrip` FTD gauge — 之前固定顯示 `quality_score=100` + 綠色滿環，user 看好幾天都一樣不知道 FTD 走到哪一段。改為依 `days_since_ftd` 分 4 stage：
  - **Day 1-5（黃金期 PRIME）** — 綠 #22c55e、ring 100%
  - **Day 6-12（主升期 STANDARD）** — 黃 #eab308、ring 78%
  - **Day 13-20（補漲期 LATE）** — 橘 #f97316、ring 52%
  - **Day 21+（過熱期 EXHAUSTED）** — 紅 #ef4444、ring 22%
- 主體顯示 `Day N` 取代 `100`（讓 user 直接看到 FTD 已過幾天）
- Suffix 顯示 stage tag（黃金期 / 主升期 / 補漲期 / 過熱期）
- `displaySize` 改 `md` 讓 `Day N` + suffix 兩行排得下
- 非 confirmed state 也分別處理：FTD_INVALIDATED → 紅色「失效」、RALLY_ATTEMPT → 灰色「Day N · 反彈中」、其他 → 灰「無 FTD」

### Why
- User 反饋：FTD gauge 永遠顯示 100 + 綠圈，看好幾天都不變，**沒辦法知道現在是黃金 / 主升 / 補漲 / 過熱期**。tooltip 內容對但 gauge 本體沒呼應 → 視覺被誤導
- `quality_score=100` 是 FTD detector 的 binary confidence (FTD 確認 = 100)，不適合直接餵 gauge — 真正動態資訊在 `days_since_ftd` 對應的 stage
- Ring 填滿百分比改 reflect「剩下多少 momentum window」（prime 100% → exhausted 22%），視覺上一眼看出能量衰減

---

## [2.17.9] — 2026-05-08
### Changed — Decisions page tooltip 統一 sector 視覺 + 重寫關鍵 chip 解釋

### Changed
- `Dashboard/decisions.html` — 移除 `<div id="decision-tip">`，改加 `<div id="signal-tip-tooltip" aria-hidden="true">` 跟 sector / index page 共用同一個 tooltip element
- `Dashboard/page-decisions.js` `initDecisionTip` — 改 render 進 `#signal-tip-tooltip`，使用 `.stt-title` / `.stt-desc` / `.stt-hint` classes 取代舊 `.tip-title` / `.tip-desc` / `.tip-scale`，並加 visible class 觸發顯示。新增 `_md()` helper 支援 `**bold**` + 換行 markdown
- `Dashboard/style.css` — 移除 `#decision-tip` + `.tip-*` legacy rules（已由 `#signal-tip-tooltip` + `.stt-*` 取代）
- `Dashboard/page-decisions.js` `DECISION_TIPS` — 重寫以下 chip 的 desc / scale 文字，用 user-facing 語言（操作建議、為什麼重要、警示）取代過去純定義式描述：
  - `contrarian` — 解釋方向 ≠ macro 的兩種 thesis 假設 + sizing 建議
  - `fragility_robust / moderate / fragile` — 三層級各自的「下一步怎麼操作」（standard cap / 降一檔 / 大砍 + OFFRAMP）
  - `signal_polarization_bipolar / mixed` — lane 共識度 + 為什麼 verdict 會晃 + sizing 對應
  - `red_team_disagree` — 解釋 LLM vs DET 雙路徑 + 6 條 kill trigger 細節
  - `val_disagree` — LLM > DET vs LLM < DET 各自的警示
  - `action_attack / wait / defensive` — 操作層判定（非 final_decision）+ 為什麼會 BUY + DEFENSIVE
  - `moat_narrow` — 為什麼 entry timing 比 WIDE 重要 + swing vs long-hold 操作差異
  - `pattern_false_breakout` — bull trap 機制 + 不追價規則 + 反指標
  - `market_weak` — institutional distribution 訊號 + 該怎麼處理已持有
  - `decision_confidence` — 70% 不是「會漲」是「重跑 100 次有 70 次同方向」+ 跟其他 chip 怎麼一起讀

### Why
- User 反饋 ALAB 卡片 chip 的 tooltip 風格沒跟 sector page 統一，且**解釋寫得太籠統 / 過於技術定義式**，看不出「我接下來該怎麼做」
- Visual：`#decision-tip` 跟 `#signal-tip-tooltip` 雖然 base 都是 `var(--bg-card)`，但 stt-* 系列 padding / radius / shadow / visible-class 都是 sector page 已調好的版本；統一可避免 cross-page 風格漂移
- 內容：原 desc 多是「Tail-risk 三維評估：論點建立在多支柱之上」這種定義句 — user 看完還是不知道倉位該不該降。重寫後每個 chip 都包 (1) 機制 / 為什麼觸發 (2) 對 sizing / 操作的具體含義 (3) 跟其他 chip 怎麼搭配看
- markdown helper 讓 desc 能用 `**bold**` 強調操作要點 + `\n\n` 段落分隔，可讀性大幅提升

---

## [2.17.8] — 2026-05-07
### Added — 決策日曆卡片 17 個 label 加 rich tooltip + 修 V4.8 mis-stamp guard

**動機**：User 觀察 TSM 卡片顯示「V4.8」標籤但專案已到 V5.0；卡片上「中等脆弱 / 訊號兩極 / Red Team 不一致」等 pill 用原生 `title=` 沒有富格式說明。

### Added
- `Dashboard/page-decisions.js` `DECISION_TIPS`：17 個新 entries（zh+en）涵蓋所有 pill：
  - **det_shadow**: signal_polarization_bipolar / mixed, red_team_disagree, val_disagree（4）
  - **action_label**: action_attack / action_wait / action_defensive（3）
  - **moat_assessment**: moat_wide / moat_narrow / moat_eroding / moat_none（4）
  - **technical pattern**: pattern_breakout / continuation / consolidation / pullback / false_breakout / topping / downtrend / oversold_bounce（8）
  - **market_strength**: market_strong / market_neutral / market_weak（3）
  - **decision_confidence_pct**: decision_confidence（1）
  - **protocol version bookmark**: version_v50 / v48 / v47 / v46 / legacy（5）
  - 每筆都含 `title` + `desc` + 可選 `scale` 三段（reuse 既有 `#decision-tip` rich tooltip render path，跟 fragility tip 同視覺）

### Changed
- `Dashboard/page-decisions.js` `buildV48StatusPills`：所有 native `title="..."` 換成 `data-tip-key="..."` reference 對應上述 entries
- `Dashboard/page-decisions.js` `buildVersionBookmark`：加 `tipKeyMap` 讓 V5.0 / V4.8 / V4.7 / V4.6 / LEGACY 各對應 rich tooltip + cursor:help
- `investment/scripts/validate_session_export.py`：新增 V4.8 mis-stamp guard — entry 若有 V5.0-only fields (`valuation_lane` / `fair_value_summary`) 但 stamp 為 `V4.8` → fail，附 patch 指示

### Fixed
- `investment/invest_logs/history.json` — 今天 TSM (2026-05-07) entry `session_export_version` `V4.8` → `V5.0`（entry 完整 V5.0 fields 都齊全，是 Phase 5 寫 history 時誤標）

### Why
- 每張 pill 都有清楚 scale + 量化邊界，user hover 一眼看完含義 + 何時該擔心；不再依賴記憶 / 翻 SKILL.md
- mis-stamp guard 是長期 hygiene：未來若 Claude 在 Phase 5 又寫錯版本，validator 會立刻擋下來（之前 V4.8 / V5.0 兩者都收 → 沒抓出來）
- 老 V4.8 真實 entries（71 筆 4/18-5/02）全部沒 V5.0 fields → 新 guard 不會誤殺

---

## [2.17.7] — 2026-05-07
### Fixed — Tooltip 內 `**bold**` markdown 真正渲染為粗體 + 段落分行

**動機**：User screenshot — earnings 頁 QUALITY tooltip 顯示 `**1. Margin 趨勢**` 字面 markdown，沒被解析為粗體；4 個 sub-component 也沒換行擠成連續一段。30+ 個 SIGNAL_TIPS 都受影響（FTD / Breadth / Market Top / 4 個 ed_score_* / EPS / Revenue / Geographic / Segment 等）。

### Fixed
- `Dashboard/utils.js` `buildSignalTipHTML`：
  - 新 `_renderTipMarkdown(s)` helper：先 escape HTML（defense-in-depth）→ 轉 `**bold**` 為 `<strong>`（non-greedy `[^*]+?` 避免跨段吃字）→ 拆 `\n\n` 為 `<p>...</p>` 段落 → 殘餘 `\n` 為 `<br>`
  - `t.desc` / `t.hint` 都套用此 helper（單行字串自動跳過 `<p>` wrap，不影響短描述）
- `Dashboard/style.css` `#signal-tip-tooltip`：新 `.stt-desc p` / `.stt-hint p` margin reset (0 0 6px 0, last-child 0)；`.stt-desc strong` / `.stt-hint strong` font-weight 700 + 同 var(--text-main) 顏色

### Verified
- helper 單元 case：`衡量公司**財報體質乾淨度**。\\n\\n**1. Margin 趨勢**：毛利率\\n**2. Accruals**：應計項` → `<p>衡量公司<strong>財報體質乾淨度</strong>。</p><p><strong>1. Margin 趨勢</strong>：毛利率<br><strong>2. Accruals</strong>：應計項</p>`
- JS syntax check rc=0
- 影響範圍：30+ 個 tooltip（涵蓋 index.html status pills、earnings.html 4 score bars、earnings-detail.html 8 chart tips）— **0 source string 重寫**

### Why
Source string 維持 markdown 風格易讀易維護；render layer 一處修補對所有 tooltip 生效，未來新加 tooltip 直接用同 markdown 風格 → 無需另寫 HTML escape boilerplate。

---

## [2.17.6] — 2026-05-07
### Fixed — 盤前檢查 Phase 1 真正並行 + modal 完成後自動關閉

**動機**：User 觀察 51m 53s 總時間 = 16:27 + 17:35 + 17:46，三段順序排隊（標籤雖寫「平行執行」實際 sequential）；且 chain 完成後 modal 不自動關閉，需手動 ESC。

### Fixed
- `dashboard_server.py` `run_premarket_chain._run()` Phase 1：改為 daily + news 兩 thread `start() + join()` 真正並行。`phase1_errors` list 收集兩條任一失敗 → raise 中止整 chain。Phase 2 sector 等兩條都結束才開始
- `Dashboard/script.js` `_pollPremarketChain` done 分支：updateDashboard + showToast 完成後再延遲 4s 自動 `closePreflight()`（user 來得及看 ✅ 結果再回正常 UI）

### Why
- daily_update.sh 抓 breadth/FTD/macro → 寫 data.json；news protocol 抓 RSS / Finnhub / FMP / SEC → 寫 digest.json。**兩者獨立**，sequential 等於浪費 wall-clock 時間
- daily 跟 news 用**不同 state machine**（`_daily_update_state` vs `_protocol_state`），並行無 lock conflict
- sector 真的 depend 兩者，必須等 Phase 1 全部完成才能跑

### Expected impact
- 之前：Phase 1 wall = daily 16m + news 17m = ~33min；總 chain ~51min
- 之後：Phase 1 wall ≈ max(daily, news) ≈ 17min；總 chain ≈ 17 + sector 18 = **~35min**（省 16 分鐘）

---

## [2.17.5] — 2026-05-07
### Added — 盤前檢查跨頁狀態 pill（atomic 三段式）

### Added
- `Dashboard/utils.js` — 新 `ensureChainPill()` + `pollChainPill()`：每 3s 拉 `/api/run-premarket-chain/status`，當 chain 非 idle 且 preflight modal **不在 open 狀態**時，於右下角浮出單一 pill；包含 daily / news / sector 三個 sub-row（icon + label + meta）。Terminal `done`/`error` 後 60s 自動消失
- `Dashboard/style.css` — `.chain-status-pill` + 配套 `.chain-pill-*` rules：amber 色框（呼應 📋 前瞻 button），固定底右 18px / 18px。當 `proto-status-pill` 同時可見，自動加 `.has-proto-pill` 抬到 92px 上方（疊接，不重疊）

### Why
- User reflow：盤前檢查 chain 跑 ~25-30 分鐘，user 不可能整段保持 modal 開。關掉 modal 後就「看不到 chain 在跑哪一段」。Pill 解決可視性
- **單一 pill 內含 3 行**而非 3 顆獨立 pill：chain 是 atomic operation（daily → news → sector 順序強制），不應允許 user 個別 dismiss / 誤判單段已結束 → 全 chain 結束才 auto-hide
- Modal 開時隱藏 pill 避免 UI 重複（modal 內已有完整 chain 列；pill 是 modal 關閉後的 fallback view）

---

## [2.17.4] — 2026-05-07
### Fixed — pre_earnings 報告在 recent_analysis 隱形

### Fixed
- `bridge.py` `extract_audit_history()` fallback scan — `*_pre_earnings.md` 檔現在用 compound dedupe key `(ticker, "pre_earnings", date)`，不再被同 ticker 既有 investment-protocol 條目蓋掉。新增 `decision: "PREVIEW"` + `report_type: "pre_earnings"` 標記
- `Dashboard/i18n.js` — 新增 `status.PREVIEW` 翻譯（zh: 「財報前瞻」/ en: 「PREVIEW」）
- `Dashboard/components.js` `renderAuditCard()` — 識別 `decision === 'PREVIEW'` 或 `report_type === 'pre_earnings'`，狀態色用 amber `#f59e0b`（與 📋 前瞻 button 視覺一致），不再跌回灰色 `var(--text-muted)`

### Why
- User 跑 CRWV / ARM 前瞻後產出 `reports/<DATE>_<T>_pre_earnings.md`，但 dashboard recent_analysis 都不顯示。Root cause：bridge fallback 用 `if t_part not in audit_map` 純 ticker key dedupe，CRWV 既有 history.json 條目 → pre_earnings 全被靜默丟棄
- Compound dedupe key 讓同 ticker 可同時保留 investment-protocol 決策 + pre_earnings 報告（多份 pre_earnings 也按日期分開保留）
- Amber 視覺色與既有 📋 前瞻 button 一致，user 一眼能分辨 PREVIEW 不是正式分析

---

## [2.17.3] — 2026-05-07
### Changed — Top 5 競品 row 改用 signal-tip 風格 rich tooltip

**動機**：v2.17.2 競品 row 用原生 `title=` 屬性，跟 sector page 其他元素（status pills / FTD / Breadth 等）的 frosted dark tooltip 視覺不一致。改為 reuse `#signal-tip-tooltip` element + `.stt-*` CSS classes。

### Changed
- `Dashboard/page-sector.js`:
  - 競品 row 移除 `title=`，改帶 `data-comp-tip="<json>"`（packed: ticker / company / industry / ceo / price / market_cap / sector / verdict）
  - 新 `initCompetitorTooltip()` IIFE 在檔尾：mouseover/mouseout listener `[data-comp-tip]` → 解析 JSON → 用 `.stt-title / .stt-desc / .stt-stages / .stt-hint` 結構 render → reuse `#signal-tip-tooltip` element + 同 CSS（dark frame + backdrop blur）
  - Position：偏好 row 右側 →（fallback above → fallback below），與其他 tooltip 行為一致
  - 與既有 SIGNAL_TIPS engine 不衝突：trigger 屬性不同（`data-comp-tip` vs `data-signal-tip`）

### Why
視覺一致性 — sector page 上 7 個 status pill + 競品 row 都用同一套 tooltip 樣式；無新增 DOM 元素 / 無新增 CSS（純 reuse）。

---

## [2.17.2] — 2026-05-07
### Added — Dashboard sector card 內嵌 Top 5 競品 collapsible

**動機**：v2.17.0 競品地圖只在 `reports/<DATE>_sector_report.md` MD 檔，user 要 surface 到 Dashboard sector page 卡片內方便瀏覽。

### Added
- `bridge.py` — 新 `_extract_sector_competitors()` (~50 行)：iterate `SECTOR_TOP_5` + reuse `get_profile()` (24h cache)，回傳 dict[sector → 5 × {ticker, company, market_cap, industry, ceo, price}]。`extract_sectors()` 把 `competitors[]` field 附到每個 sector entry → data.json
- `Dashboard/page-sector.js` `buildSectorCard` — 新 `competitorsBlock`：`<details>` 預設摺疊 + mini table（Ticker / Company / Market Cap），industry/CEO/price 進 row title tooltip。Click ticker `<a>` 跳 `momentum.html?sector=<gics>&ticker=<T>`，event.stopPropagation 避免觸發外層卡片 jump
- `Dashboard/sector.html` 內嵌 CSS — `.sec-comp*` mini-table style：dashed top border / amber summary chevron / row hover / ticker link 用 sector verdict color

### Why
- bridge 端 reuse 現成 24h profile cache，0 新 FMP call cost
- UI 端預設摺疊不佔卡片空間，點開才看；row tooltip 補完整 metadata（industry/CEO/price）避免 table 過寬
- 跳 momentum 沿用既有 `data-sector-jump` 模式 + 加 ticker query param

### Verified
- bridge.py 跑完 data.json Technology sector competitors 5 個 (AAPL $4.2T / MSFT $3.1T / NVDA $5.1T / AVGO $2.0T / ORCL $0.6T)
- JS syntax check rc=0

---

## [2.17.1] — 2026-05-07
### Fixed — preflight UI 計時、CRWV 財報日曆過濾、pre-earnings 資訊密度

### Fixed
- `dashboard_server.py` — `run_premarket_chain._run()` daily polling 改從 `_daily_update_state["started_at"]` 直接算 elapsed，不再依賴從未被寫入的 `elapsed_sec` 欄位（UI Phase 1 daily 卡 `0s` 不動）
- `dashboard_server.py` — `_wait_protocol_completion()` 同 pattern 修：news / sector phase 的 `_protocol_state["elapsed_sec"]` 只在收尾才寫，poller 改算 `started_at` diff
- `bridge.py` — `_load_calendar_universe()` 新增 `watchlist.txt` 為第 4 個 universe source；CRWV 等 IPO / out-of-index 名稱可手動 append 即被收進 earnings calendar，不再被 SP500∪Nasdaq100∪SOX gate 砍掉
- `skills/momentum-monitor/scripts/universes/watchlist.txt` — 建檔，預載 CRWV
- `skills/earnings-valuation-forecaster/scripts/forecast.py`：
  - `FMP.income_quarter` limit 5→8（pre-earnings watch_metrics 算 YoY 需 ≥5Q）
  - `_next_earnings_info()` 過濾條件 `date > today` → `date >= today AND epsActual is None`，**今日報財報的 ticker** consensus card 不再是空的
  - 新 `_watch_metrics_computed(income_q)` — 從 income_q 計算 **實值** Watch List：Revenue YoY + accel/decel、GM% 4Q trend + QoQ bps、OpM% trend、EPS trend；取代純文字 hint 模板
  - 新 `build_ps_scenarios()` — TTM EPS ≤ 0 時改用 P/S × forward revenue 法產 12M target（之前直接顯示「不適用 — 請改用 P/S 或 EV/Sales」全空）
  - 新 `_merged_watch_metrics()` — earnings-analyst cache（segments / quality flags） + computed real values 合併 dedupe，capped 6 chips
- `Dashboard/page-earnings.js`：
  - 12M target 區塊 method-aware label（PE 法 / P/S 法（負 EPS））+ TTM rev / 當前 P/S / 近期 YoY meta line
  - seasonality SVG GM% 標籤 collision 防撞：當 GM% circle 落在 bar top label 14px 內，label 自動 flip 到 circle 下方（之前 $1.21B 與 74% 重疊）

### Why
- Preflight UI 卡 `0s`：daily_update.sh 跑得好好的（log streaming 有 `[N/6]` step），但 `elapsed_sec` 從未被寫入 → user 以為 chain 卡死。Fix at consumer side（poller 自算）比加 ticker thread 簡單
- CRWV 2025-03 IPO，今天（2026-05-07）報財報但被 SP500∪Nasdaq100∪SOX universe gate 砍掉，calendar 看不到、財報分析輸入欄 filter 也濾掉。Watchlist mechanism 給 user 後續加 IPO / out-of-index 名稱的乾淨 override
- pre-earnings 卡片之前對 CRWV 顯示：consensus EPS/Rev = `—`、Watch List 全是 generic 模板字（「QoQ ±100bps 看 mix / pricing」沒實值）、12M target 全空。User 反饋「看不出資訊」。三個洞各自 fix：consensus filter、watch_metrics computed、P/S scenarios

---

## [2.17.0] — 2026-05-07
### Added — Phase D + B-2 batch（institutional format / TAM block / 競品地圖 / Write 隔離）

**動機**：Gemini cross-check 顯示 reference/financial-services 還有 4 個小強化點未做 — 機構級報告長度規範、個股 fundamentals lane TAM block、sector report 競品比較表、news subagent Write 隔離 doc。詳見 plan file Phase D。

### Added
- `skills/earnings-analyst/SKILL.md` — 「Institutional Format Standards」section：8-12 頁 / 3,000-5,000 字 / 1-3 summary tables / 8-12 charts / 24-48h turnaround / NEW info focus / format checklist（仿 reference equity-research/earnings-analysis SKILL.md）
- `investment/investment_protocol_v5_0.md` Phase 2 Fundamentals subagent — 新 V2.17.0 sub-block「TAM / Market Position」必填：tam_usd / industry_5y_cagr_pct / company_revenue_share_pct / position_label / competitive_moat_evidence。**禁止 LLM 自編 TAM 數字**，缺資料 → null + 註記
- `investment/phase5_export_schema.md` `fundamentals_lane.market_position` schema 新增（V2.17 optional，validator 不擋向下相容）
- `news/news_protocol_v2.md` — 新「TOOL BOUNDARIES — Write Isolation」section：tool 權限矩陣（triage / 4-view subagent reader-only，arbiter 持 Write）+ Agent tool prompt 強制首句約束 + PM 驗證機制
- `sector/scripts/render_sector_report.py` — 新 `render_competitive_landscape()`：reuse `SECTOR_TOP_5` + `get_profile()` (24h cache)，per-sector 渲染 top-5 比較表（Ticker / Company / Industry / Market Cap / Price / CEO / Differentiator placeholder）。Sector 顯示順序依 Phase 5 verdict score 由高到低。`_HAS_COMPETITIVE` graceful skip 若 company_context import 失敗

### Why
- D-1：reference earnings-analysis 是機構標準格式範本，加長度規範可讓 render.py 後續加 lint 檢查（未做）
- D-2：sector report 缺最後一塊「sector 內哪個 stock 大」直觀比較；reuse `SECTOR_TOP_5` 0 維護成本，0 額外 FMP call（cache 24h）
- D-3：fundamentals lane 之前只看 P/E + FCF + moat，**缺市場層級 sizing**（TAM / share），這正是 reference sector-overview pattern 的核心。加進去後 fundamentals lane 視野完整覆蓋公司 ↔ 產業
- B-2 #7：news 是攻擊面最大 protocol（untrusted RSS / scraped headlines），formalize Write 隔離 pattern 是長期 security 投資；當前實作無破壞性，純文件規範 + spawn-time prompt 約束

### Verified
- render_sector_report.py --stdout：11 sectors × 5 tickers 全 render（GOOGL Alphabet $4.81T / etc.），sector 排序依 verdict score
- 既有 sector validator 不需動（純 render 層改動）

### Phase D 完成度
- ✅ D-1 / D-2 / D-3 + B-2 #7 doc-level
- 待做：B-2 #7 真正 spawn Agent tool 時加 prompt 約束（在 news protocol 實際執行時生效，不需 code 改動）

---

## [2.16.0] — 2026-05-06
### Added — 財報前瞻 popup card modal（圖形化視覺優化）

**動機**：v2.15.3 「看前瞻報告」開新分頁顯示 raw MD，user 要 popup card view 易讀 + 圖形化。

### Added
- `dashboard_server.py` — 新 endpoint `GET /api/preview-cache/<TICKER>` 讀 forecaster cache JSON 回傳（404 若 cache 無 pre_earnings block；500 若 IO 錯誤）
- `Dashboard/earnings.html`:
  - 新 modal scaffold `#ea-preview-modal`（amber accent bar + close button + raw MD fallback link）
  - 內嵌 ~220 行 CSS：section card frame / header card / stats row / SVG chart frame / watch chips / 12M scenario columns / caveats `<details>` / responsive media query
- `Dashboard/page-earnings.js`:
  - `wirePreviewModal()` + `openPreviewModal(ticker)` + `closePreviewModal()`：fetch endpoint → render 5 sections
  - `renderPreviewModal()`：Header card（ticker + countdown badge today/明天/Xd + price）+ Consensus（EPS / Revenue 大數字並排）+ Seasonality（SVG bar chart + GM% line overlay）+ Watch chips（icon + title + hover hint）+ 12M Scenarios（bull/base/bear 3-col + target 大字 + upside %）+ Caveats `<details>` 預設摺疊
  - `renderSeasonalitySection()`：純 SVG 760×130，amber bars + emerald GM% polyline + dashed legend
  - `eaSetRunBannerDone` preview 分支：button onClick 改呼叫 `openPreviewModal()` 而非開新 tab；保留 raw MD fallback link 在 modal header

### Visual design
- amber `#fbbf24` accent（跟 morph button 一致辨識）
- bull `#10b981` / base `#a1a1aa` / bear `#f87171` 三色 scenario
- countdown badge：今天 = 紅 `#f87171`，> 0 天 = amber
- watch chip hover 變 amber outline + bg
- responsive：< 640px stats / scenarios 變 1-col stack

### Negative-EPS handle
12M section 顯示「⚠ TTM EPS ≤ 0，PE 估值不適用」灰色 placeholder，其他 section 照樣 render。

### Verified
- CRWV cache shape OK (`pre_earnings` block 含 next_earnings / seasonality_4q / watch_metrics / scenarios=null)
- JS syntax check rc=0

---

## [2.15.4] — 2026-05-06
### Fixed — 財報日曆 ARM missing + 過濾 SP500/Nasdaq100/SOX universe

**動機**：User 發現 FMP `/stable/earnings-calendar` 直接打有 ARM 5/6 row，但 Dashboard 財報日曆沒出現；且整體 2840 個 earnings events 太雜。Root cause 兩個 bug：

1. **Cache stale**：`.cache_bridge/fmp_earnings_<date>.json` 凌晨 00:03 抓的，FMP 後續才 add ARM 5/6 → cache 整天不更新 → ARM 永遠不在
2. **FMP 4000-row cap**：bridge 用 `from=today, to=today+14d` 14-day window 撞 FMP 響應 4000 行上限，**API 從最早日期開始截**（drop today/tomorrow），ARM 5/6 整段被 skip

### Changed
- `bridge.py` `_from_fmp_earnings`:
  - **Cache TTL 4h**（之前永久 day-key cache）— FMP 整天會陸續 add 新 ticker，4h 重 fetch 抓到 ARM 這類 last-minute add
  - **Chunked fetch 3 段**：`(today-1, today+4)` → `(today+5, today+9)` → `(today+10, today+horizon)`，dedup by `(symbol, date)`。每段遠低於 4000 cap → 完整覆蓋
  - **Universe filter**：新 `_load_calendar_universe()` 讀 `skills/momentum-monitor/scripts/universes/{sp500,nasdaq100,sox}.txt` (~530 unique tickers)，`symbol not in universe → skip`
- `bridge.py` `aggregate_upcoming_events`:
  - **Final universe gate**：archive 累積的歷史 events 也用同一 universe 過濾，避免舊 entry 漏網

### Verified
- 4000 raw rows → 93 fresh events → final 139 (含 archive)，下降 ~95%
- ARM 5/6 出現 in data.json upcoming_events ✓
- VZ / GM / KO / V / HOOD 等 blue chip 仍在 calendar

### Why
Universe sets 是現成 `momentum-monitor` 維護的官方 index 成員 list，零維護成本。chunking 一次 daily_update +3 calls 對 250/day FMP free tier 無壓力。

---

## [2.15.3] — 2026-05-06
### Changed — 財報前瞻 done banner 加「📄 看前瞻報告」link button

**動機**：v2.15.0 跑完前瞻 banner 雖 ✓ Done，但 user 看不到產出 MD（earnings 頁卡片只列 post-earnings cache，pre-earnings 寫到 `reports/<DATE>_<T>_pre_earnings.md` 後沒 surface）。

### Added
- `Dashboard/earnings.html` — 新 banner button `#ea-run-view-report`（amber `<a target=_blank>` link，預設 hidden）
- `Dashboard/page-earnings.js`:
  - 新 module-level state `_eaActiveMode`：`'earnings' | 'earnings_preview' | null`
  - `runEarningsPreview` / `runEarnings` 起跑時各自 set mode
  - `eaShowRunBanner` title 依 mode 切 `財報前瞻中` vs `財報分析中`
  - `eaSetRunBannerDone` 依 mode 分流 affordance：
    - preview → 顯示「📄 看前瞻報告」連到 `/reports/<TODAY YYYYMMDD>_<TICKER>_pre_earnings.md`
    - earnings → 維持「重新整理」button
  - poller done 分支：preview mode 不跑 `loadAndRender()`（earnings_analyses 不會更新）；earnings mode 仍 reload data.json 拿新卡片
  - banner 隱藏 / dismiss 時清掉 `_eaActiveMode`
  - 補：banner 從 server status 回填 `_eaActiveMode = s.name`（page refresh 中途 resume 也能正確 render button）

### Why
B 方案（手動 click 看報告 vs 自動開新 tab）：尊重 user 是否想立刻看，避免分心。amber 色與既有 morph button 一致辨識「前瞻 = 黃色」。

---

## [2.15.2] — 2026-05-06
### Fixed — `--pre-earnings` 對 negative-EPS ticker (CRWV / RIVN / SOFI) 不再 abort

**動機**：user 跑 CRWV 財報前瞻 → forecaster 因 TTM EPS = -2.49 直接 return `unsupported` rc=1 → server SCRIPT_PROTOCOLS 標 error。但 pre-earnings cheat sheet（consensus / seasonality / watch list）**根本不需要 positive EPS**——只有 12M target price section 才要 PE math。

### Changed
- `skills/earnings-valuation-forecaster/scripts/forecast.py`:
  - Negative TTM EPS + `--pre-earnings` flag → 改回傳 `status: "ok_partial"` 含 `pre_earnings` block + `scenarios: null` + `negative_eps: true`，而非整個 abort
  - `to_markdown_pre_earnings()` 偵測 `negative_eps` → header 加 ⚠ 警告 + skip Forward EPS line + 12M section 替換為 explanation 註解（指向 P/S / EV/Sales 替代）
  - `main()` 接受 `ok_partial` 為 success rc=0（僅 pre-earnings mode；plain mode 仍嚴格 require positive EPS）

### Why
unprofitable growth tech（CRWV / RIVN / SOFI / RDDT）仍有 quarterly earnings reports，pre-earnings cheat sheet 對這類名單照樣有用：consensus EPS（即使 -$0.89）+ revenue trajectory + GM% trend + 待觀察 metric 都是有用 input。**前瞻 ≠ 估值**，沒理由因 negative EPS 全 reject。

### Verified
- CRWV `--pre-earnings` → rc=0，產出完整 cheat sheet（next earnings 1d / consensus / 4Q seasonality + revenue 0.98→1.57B 成長軌跡 / 12M section graceful skip）
- NVDA `--pre-earnings` → rc=0，仍正常產出 12M scenarios（regression OK）

---

## [2.15.1] — 2026-05-06
### Changed — Earnings command bar 即時 morph + 模式 hint

**動機**：V2.15.0 morph 邏輯只在卡片上生效；user 從 input bar 手動輸入 ticker 也應該即時 reflect 模式（前瞻 vs 分析上季），不要等按下執行才知道跑哪一個。

### Added
- `Dashboard/page-earnings.js`:
  - 新 `upcomingEarningsMap` (ticker → `{date, days_until}`) — 從 data.json `upcoming_events`（已是 FMP confirmed）抽 future earnings，nearest-date wins
  - `rebuildUpcomingEarningsMap()` 在 `loadAndRender()` + DataStore subscribe 都呼叫
  - `wireCommandBar()` 新 `syncMode()` — input listener 每次 keystroke 比對 map：
    - `0 ≤ days ≤ 7` → button 變 amber「📋 財報前瞻」+ hint「⚡ 下次財報 X（Yd）→ 跑前瞻 cheat sheet」
    - `8 ≤ days ≤ 30` → button 維持 default「執行」+ hint「📅 下次財報 X（Yd）→ 跑分析上季（前瞻在 7d 內才開放）」
    - 其他 → button「執行」+ hint「📊 無近期確認財報日 → 跑分析上季」
  - `trigger()` 改依 `btn.dataset.mode` 分派 `runEarningsPreview` vs `runEarnings`
- `Dashboard/earnings.html` + 內嵌 CSS：
  - cmdbar 下方加 `#ea-cmd-hint` span
  - `.ea-cmdbar-btn-preview` amber 變體
  - `.ea-cmd-hint[data-mode="preview"]` amber / `soon` slate / `post` zinc 三色

### Why
User 觀察：「假如我輸入的是七天內的 ticker, 應該要註明是財報前瞻」。直接 reuse `data.json.upcoming_events`（calendar cache 同源），無需新 endpoint，0 額外 FMP 呼叫。Map 在 page load 一次建好，每次 keystroke 是 in-memory lookup（O(1)），延遲 0ms。

---

## [2.15.0] — 2026-05-06
### Added — Pre-earnings 前瞻 mode + Dashboard 7-day morph button (Phase B-1)

**動機**：reference/financial-services equity-research vertical 有 `earnings-preview` skill；本專案決定以**擴充既有 forecaster** 達成（避免新 skill 維護成本）+ Dashboard UI 在財報 ≤ 7 天時自動 morph 出「📋 前瞻」button，跑 forecaster --pre-earnings cheat sheet。**option Z 邏輯**：≤7d 用 forecaster（最準）、>7d 維持 earnings-analyst（看上季品質），兩 skill 互補不重疊。詳見 `~/.claude/plans/refernce-finanical-services-mcp-server-snazzy-canyon.md`。

### Added
- `skills/earnings-valuation-forecaster/scripts/forecast.py` — `--pre-earnings` flag (~150 行)：
  - 新 FMP method `earnings_upcoming()` → `/earnings?symbol=` future-dated row 抓 `epsEstimated` / `revenueEstimated`
  - `_seasonality_4q()` — last 4Q revenue / EPS dil. / GM% chronological 表
  - `_watch_metrics_from_cache()` + `_watch_metrics_default()` — 從 earnings-analyst cache 抽 segment names + quality_flags 強化 watch list；無 cache fallback 5 條 generic
  - 新 MD layout `to_markdown_pre_earnings()` — cheat sheet at top, seasonality middle, 12M scenarios demoted to bottom supplementary
  - 輸出 `reports/<DATE>_<TICKER>_pre_earnings.md`（與 plain `_valuation.md` 區分；cache key 也分離）
- `dashboard_server.py` — `SCRIPT_PROTOCOLS` 新基礎設施（~120 行）：
  - 新 dict 註冊純 subprocess 協議（不走 Claude turn，省 ~$0.02/click + ~30s）
  - `_run_script_protocol()` 鏡像 `run_protocol` 的 state machine（status / log / cancel / banner 全相容）
  - `enqueue_protocol` + `_label_for` + `run_protocol` 都加 SCRIPT_PROTOCOLS 分支
  - 註冊 `earnings_preview` 路由 forecast.py --pre-earnings，timeout 180s

### Changed
- `Dashboard/page-earnings.js` — 卡片 render 計算 `daysTo(next_earnings_est)`，`fmp_confirmed` 且 `0 ≤ days ≤ 7` → swap 重跑 button 為「📋 財報前瞻」（amber 色）。新 `runEarningsPreview()` handler、click 分派 action='preview'、poller 接受 `name='earnings_preview'`
- `Dashboard/page-calendar.js` — Option Z 4-quadrant 邏輯：
  - ≤7d + nocache → 「📋 前瞻」單 button（forecaster 最準時機，post-earnings 跑會吃舊 cache）
  - ≤7d + cached → 看報告 + 📋 前瞻 + 🔄（上季 / 下季 / 重跑上季 三事權各對應一鈕）
  - \>7d + nocache → 📊 跑財報分析（維持，user 可主動分析上季）
  - \>7d + cached → 看報告 + 🔄（維持）
  - 新 `window.runEarningsPreview()` global handler
- `Dashboard/earnings.html` + `Dashboard/style.css` — `ea-act-btn-preview` + `cal-earnings-btn-preview` amber 色 (`#fbbf24`) variant
- `skills/earnings-valuation-forecaster/SKILL.md` — 「Pre-Earnings Mode (V2.15.0+)」section：output schema / 適用條件 / UI 觸發規則 / 不適用場景
- `CLAUDE.md` — trigger 表加「財報前瞻」+ Ops Shortcuts 加 `--pre-earnings` CLI

### Why
forecaster 距離 earnings 越近越準（fresh consensus + whisper 出爐 + management commentary cues）；earnings-analyst cache key = `last_earnings_date` 不會因下次財報未發布而更新，跑了浪費資源。Option Z 把兩 skill 在時間軸上互補：7 天內 forecaster 主導，7 天外 earnings-analyst 主導。Dashboard morph 讓 user 不用記 trigger，UI 自動出最適 button。

### Architecture note
`SCRIPT_PROTOCOLS` 是新類別的 protocol —— 不走 Claude conversation。長期可把其他純腳本工作（e.g. `daily_update.sh` step、`build_event_index.py`）也搬進來，省 LLM cost。目前先收 earnings_preview 一個。

---

## [2.14.0] — 2026-05-06
### Added — reference/financial-services Phase A 移植（IC-memo + thesis registry + skills linter + hyperlink discipline）

**動機**：對照 Anthropic 官方 `reference/financial-services/` 找出 4 個高 ROI 低成本的強化點：機構級 IC-memo 結構、thesis 生命週期串接、skills cross-ref linter、earnings 報告強制 EDGAR/IR clickable hyperlinks。詳細決策見 `~/.claude/plans/refernce-finanical-services-mcp-server-snazzy-canyon.md`。

### Added
- `investment/scripts/register_thesis.py` (104L) — Phase 5.5 wire-up，把 history.json 最後一筆 register 進 trader-memory-core，回填 `thesis_id` + `thesis_registered_at`。Idempotent + non-fatal（trader-memory-core 不在 / dep 缺失時 graceful skip）。State 寫到 `investment/invest_logs/theses/`。
- `scripts/check_skills.py` (160L) — skills/*/SKILL.md frontmatter + cross-ref linter。Lenient mode 預設（rc=0 always），`--strict` 旗標 CI 用。檢查 frontmatter name/description、referenced script files exist、cross-skill references 有效、cache/ dir 一致性。22 skills 全 pass 0 warnings。

### Changed
- `skills/earnings-analyst/SKILL.md` — 新增「Citations & Hyperlinks ⭐⭐⭐ MANDATORY」section（仿 reference equity-research/earnings-analysis）。MD 報告所有財務數字必須掛 markdown clickable link 指向 SEC EDGAR / IR / FMP source page。提供 7 類內容對應 URL 模板。
- `investment/investment_protocol_v5_0.md`：
  - Phase 5 Step 4 OUTPUT 結構強化 §7-§8（V2.14.0 IC-memo pattern）：
    - §7 Red Team 拆 Consensus View / Differentiated View / Counter Thesis / Numbered Kill Conditions（強制 numbered list，禁 free-form）
    - §8 進場計畫拆 Base / Bull / Bear case 三檔
  - 新增 Phase 5 Step 6 = Phase 5.5 thesis registry wire-up（呼叫 `register_thesis.py`，non-fatal）
- `investment/phase5_export_schema.md` — `trades_this_session[]` 加 optional `thesis_id` + `thesis_registered_at` 欄位 + FULL EXAMPLE 範例值
- `investment/scripts/validate_session_export.py` — 接受 V2.14.0 optional thesis 欄位（type-check string-or-null，不強制存在）
- `CLAUDE.md` — 更新 trigger 表（Phase 5.5 + hyperlink 強制）+ Ops Shortcuts 加兩條（register_thesis.py + check_skills.py）

### Why
Reference repo 的 IC-memo / hyperlink discipline / lifecycle tracker 是機構研究室標配；本專案投資 protocol 已成熟但缺這幾片。Phase A 全 doc-level + 一個小 script，無破壞性改動：所有改動 backward-compatible（V5.0 entries 仍 valid，optional 欄位缺失不擋 validator）。

---

## [2.13.13] — 2026-05-06
### Fixed — daily_update.sh Step 6 進度可見化

**動機**：`daily_update.sh` 跑到 `[ 6/6 ] Thematic Screener` 完全靜默 3-8 分鐘，使用者誤以為當機。Root cause：`screen.py --json-only > /dev/null 2>&1` 把 stderr 進度（每 10 tickers 一行 `[HH:MM:SS] ... i/N (elapsed Ns)`）也吞了。

### Changed
- `daily_update.sh` Step 6:
  - 跑前先讀 theme-detector cache 算 unique ticker 數，印 `▶ predicting ~N unique tickers（4h cache 命中數秒；冷跑 3-8 分鐘）` 預期 hint
  - stderr 改用 process substitution stream：`2> >(sed 's/^/         │ /' >&2)`，預測進度即時縮排輸出
  - 完成 / 失敗訊息附 wall-clock elapsed 秒數
  - stdout 仍 `> /dev/null`（不汙染 terminal — 大量 JSON 已寫到 `data/recommendations/`）

### Why
無 progress feedback 的長時操作 = bad UX。screen.py 早已 flush stderr `_log()`，只是被 shell redirect 吃掉。修 shell 層即可，不動 screen.py。

---

## [2.13.12] — 2026-05-05
### Added — Forward P/E + EV/EBITDA TTM（補 PE TTM 不足）

**動機**：HPE PE TTM = -253 因 Q2 2025 一次性 -$1.05B 拖累，但公司實際 ongoing 賺錢。User 詢問「PE / P/B 哪個更有參考價值」— 結論 Forward P/E + EV/EBITDA 比 TTM PE 與 P/B 都更實用。

**Server (dashboard_server.py)**
- `_fetch_pe_ttm` 改回 valuation bundle，每 ticker 3 次 FMP 呼叫：
  - `/stable/ratios-ttm` → `priceToEarningsRatioTTM`
  - `/stable/key-metrics-ttm` → `evToEBITDATTM`
  - `/stable/analyst-estimates?period=annual` → 最近未來年度 `epsAvg`（forward EPS）
- `_heatmap_pe_cache` 改存 dict `{pe_ttm, ev_ebitda, fwd_eps}`
- `_heatmap_refresh_quotes` + `_heatmap_refresh_pe_universe` + `_fetch_theme_extra_quotes` 都attach `pe`、`ev_ebitda`、`forward_pe`（forward_pe 即時用 row.price / fwd_eps 算，價格漂移仍即時）
- Theme heatmap payload 多帶兩欄

**Bridge (bridge.py)**
- `extract_earnings_analyses` + `ingest_momentum_screen` 從 `Dashboard/heatmap.json` 讀 forward_pe + ev_ebitda lookup
- earnings row 新增 `forward_pe` + `ev_ebitda`（earnings cache 已有 ev_ebitda from key-metrics-ttm；forward_pe 借 heatmap）
- momentum row 新增 `forward_pe` + `ev_ebitda`（資料齊但目前 UI 不顯示，留 future 用）

**Frontend**
- `page-sector.js` heatmap tooltip：新增 Fwd P/E + EV/EBITDA 兩 row（同 4 段染色 + tooltip 解釋）。增量 update path 同步加欄
- `page-radar.js` tooltip 同樣新增兩 row
- `page-earnings.js` card meta-pills：PE pill 之後加 Fwd Pill + EV/EBITDA pill，皆染色 + hover 解釋

**色階**
- P/E（TTM 與 Forward 同）：< 0 紅 / < 15 綠 / 15-30 白 / > 30 黃
- EV/EBITDA：< 0 紅 / < 10 綠 / 10-20 白 / > 20 黃

### Why
P/E TTM 易被一次性項目扭曲，P/B 對輕資產（科技、軟體、品牌）幾乎無參考價值。Forward P/E 排除一次性 hit、看分析師共識，與 EV/EBITDA（跨資本結構可比）為實務最常用兩個補充指標。HPE 案例驗證：TTM PE = -253，但 Forward PE 預期應在 17-20 範圍。

FMP `/stable/key-metrics-ttm.evToEBITDATTM` 與 `/stable/analyst-estimates.epsAvg` 都按 ticker 單獨呼叫，所以 PE daemon 從原本 600 calls/24h 變成 1800 calls/24h；ThreadPool(10) 估 ~3 min 完成，仍可接受。

### How to apply
- Restart `dashboard_server.py`，等 stderr `[heatmap-pe] done: N/N`（~3min）
- 重跑 `bridge.py` 讓 earnings / momentum 拿到新欄位
- Hard refresh sector / radar / earnings 各 page

---

## [2.13.11] — 2026-05-05
### Changed — 盤前檢查 chain 從前端搬到 server-side orchestrator（修「sector 從未啟動」race）

**Server (dashboard_server.py)**
- 新 `_premarket_chain_state` + `_premarket_chain_lock`，shape：`{status, started_at, ended_at, phase, elapsed_sec, items: {daily/news/sector: {status, elapsed_sec, reason, error}}, error}`
- 新 `run_premarket_chain()` daemon thread sequencer：
  - Phase 1a daily：`preflight_check` 全 free FRESH → skip；否則 `run_daily_update()` + 輪詢 `_daily_update_state.status` 至 done/error
  - Phase 1b news：`news` key FRESH → skip；否則 `enqueue_protocol("news")` + `_wait_protocol_completion()` 透過 **`_protocol_history`** 偵測完成（durable record，不會錯過瞬間 transition）
  - Phase 2 sector：`sector` key FRESH → skip；否則 enqueue + wait
- 新 `_wait_protocol_completion(name, history_baseline, timeout, on_progress)` helper
- 新 endpoints：
  - `POST /api/run-premarket-chain` → 啟動（409 duplicate_active 含當前 phase）
  - `GET /api/run-premarket-chain/status` → 完整 state

**Frontend (Dashboard/script.js)**
- `runPremarketChain` 簡化為 thin POST + 起 2s poll loop
- 新 `_pollPremarketChain` — 單一 endpoint 取 server aggregated state、render 三 row（daily / news / sector）+ verdict
- 移除 `_pollDailyUpdate` / `_pollProtoForChain` / `_maybeStartPhase2` / `_finalizeChain` / `_chainState`（現由 server 持有 canonical state）
- 新 page-load resume IIFE：若 server 端 chain `running` 或 5min 內 `done/error`，自動 attach poll，user 重整不丟進度

### Why
原 chain 邏輯純前端 polling `/api/run-protocol/status` 2.5s 一次。發現的問題：
1. **Race**：news done 後 server 端 `_protocol_state` 立即被 sector 覆蓋（worker 切下個 job），如果 frontend 沒在那瞬間 catch 到 `name=news status=done` 就永遠不會設 `newsDone=true`、Phase 2 永遠不 fire（今天觀察到「2 次 chain 都失敗，sector 從未啟動」即此症狀）。
2. **Tab close kill**：browser 關 tab → chain 整個失效。Server 端有 daily 跑完、news 跑完，但 sector 永遠 enqueue 不到。

Server-side daemon thread 用 `_protocol_history`（持久 完成記錄）偵測 transition，不依賴瞬時狀態；user 關 tab 也能繼續完成。Frontend 只負責 render，重整即 resume。

### How to apply
- Restart `dashboard_server.py`
- Hard refresh dashboard
- 試：點「開始盤前檢查」→ 應依序看到 daily（skip 或 running→done）→ news（skip 或 running→done）→ sector（skip 或 running→done）→ verdict ✅。中途關 tab 重開應自動恢復進度。

---

## [2.13.10] — 2026-05-05
### Added — 個股 PE TTM 全 Dashboard 顯示（heatmap tooltip / radar / earnings card / momentum row）

**新基建（dashboard_server.py）**
- `_heatmap_pe_cache: {sym: (ts, pe)}` + `_heatmap_pe_lock` + `HEATMAP_PE_TTL_SEC=86400`（24h）
- `_fetch_pe_ttm(ticker, api_key)`：FMP `/stable/ratios-ttm` 單支抓 `priceToEarningsRatioTTM`
- `_heatmap_refresh_pe_universe(max_workers=10)`：ThreadPool 10 平行刷整個 universe，啟動時跑一次 daemon thread
- `_heatmap_refresh_quotes` 每次 batch-quote 後從 PE cache 補 `row["pe"]`
- `_fetch_theme_extra_quotes` 對 radar small/mid cap 也帶 `pe`，缺 PE 的 ticker 在背景 thread pool lazy fetch

**Bridge.py**
- `extract_earnings_analyses` 加 `pe_ttm`（從 earnings cache `ttm_metrics.from_ratios_ttm.priceToEarningsRatioTTM`）
- `ingest_momentum_screen` 載入 `Dashboard/heatmap.json` 建 `pe_lookup` → 每 row 加 `pe`

**Frontend**
- `page-sector.js` heatmap tooltip：加「P/E (TTM)」row（color 分級：<0 紅、<15 綠、>30 黃、其他白）。ticker 增量 update 也帶 pe
- `page-radar.js` `_radarShowTooltip` 同樣加 PE row
- `page-earnings.js` card meta-pills 加 `P/E xx.x` 染色 pill
- `page-momentum.js` table 加 P/E 欄（價格右側）+ sort 支援；header 翻譯 `col_pe` zh「本益比」/ en「P/E」；emptyRow colspan 12 → 13
- `momentum.html` 加 `<th id="th-pe" data-sort="pe">P/E</th>`

### Why
個股 PE 之前完全沒在 Dashboard 任何 list / hover 出現，只在 invest deep-dive 報告 markdown 內。User 平時看 heatmap / earnings / momentum 都看不到 valuation 資訊。

FMP `/stable/batch-quote` 與 `/stable/quote` 已 drop `pe` 欄位（測試確認），改走 `/stable/ratios-ttm`（每 ticker 單獨 fetch、24h TTL cache）。Universe ~600 ticker × 24h refresh × ThreadPool(10) ≈ 60s，FMP usage 可承受。

色階沿用財務分析常識：< 15 便宜 / 15-30 fair / > 30 高估 / < 0 虧損。User 一眼看 hover / card / row 就能判斷估值區間。

### How to apply
- Restart `dashboard_server.py`（PE daemon 啟動 + 補欄 quote refresh）
- 等 1-2 分鐘 PE universe fetch 完（看 stderr `[heatmap-pe] done: N/N`）
- Hard refresh 各 page

---

## [2.13.9] — 2026-05-05
### Added — 盤前檢查 chain 加 freshness skip（外部跑過 daily_update.sh 不重跑）

- `dashboard_server.py::POST /api/run-daily-update`：先跑 `preflight_check()`，若所有 `free=true` 項目皆 `FRESH` → 200 `{skipped: true, reason: "all_free_caches_fresh", items, ages}`。否則維持 202 啟 daily_update.sh。Defensive：preflight_check 自身錯時 fall-through 到實跑（不誤跳）。
- `Dashboard/script.js::runPremarketChain`：
  - 開跑前一次 `/api/preflight` 撈 freshness，記錄 `newsFresh` / `sectorFresh`。
  - Phase 1 daily 收 `{skipped: true}` → row 顯「已新鮮 · 跳過」綠勾，不啟 poll。
  - Phase 1 news：`newsFresh === true` → 不打 `/api/protocol-queue`，row 直接綠勾。
  - Phase 1 兩個都 skip → 立即進 Phase 2，不啟 daily/proto poll loop。
  - Phase 2 sector：`sectorFresh === true` → 不打 protocol-queue，row 直接綠勾、`_finalizeChain()`。
  - 啟動的 timer 只針對 actually-launched job（之前無條件啟兩個 timer）。

### Why
User 已在 shell 跑過 `./daily_update.sh`，回 dashboard 點「開始盤前檢查」應 detect cache 全 fresh 直接跳過。原本無條件 fire daily_update.sh + news Claude + sector Claude，浪費 ~5min + tokens。同邏輯延伸至 news / sector Claude protocol — 今日 digest / sector_intel 若 < 3h 視為 fresh，使用者一個 session 內按多次也只跑第一次。

也順便處理「我沒按開始盤前檢查就自己開始跑了」的副作用：即使誤觸按鈕，全 fresh → chain 秒結束、不消耗資源。

### How to apply
- Restart `dashboard_server.py` + hard refresh index 頁。
- 跑前可先 `./daily_update.sh` 在 shell，回 UI 按「開始盤前檢查」應全部顯「跳過」3 秒內完成。

---

## [2.13.8] — 2026-05-05
### Fixed — thematic-screener 加 socket timeout + 進度 log（修 65min hang）

- `skills/thematic-screener/scripts/screen.py`：
  - `socket.setdefaulttimeout(15)` 模組頂層 — 任何 yfinance / FMP socket op 15s 沒回就 raise，避免 SYN_SENT 無限 hang。
  - 新 `_log(msg)` helper（HH:MM:SS prefix + `flush=True`）讓 daily_update.sh 的 stderr tail 即時看到進度。
  - Predict loop 加每 10 ticker batch 進度 + 個別 > 5s 的單筆 log + TIMEOUT 標籤。
  - Predict + Enrich 階段印總 elapsed。

### Why
今日 daily_update.sh PID 31623（screen.py）卡 65 分鐘。診斷：`lsof` 看到 1 個 socket 在 `SYN_SENT` 對 ec2 host（FMP / yfinance proxy 之一），對方無回應 → Python socket 預設無 timeout → 阻塞 IO 等到 OS 自己 RST。Predict loop 順序跑 249 tickers，1 個 ticker hang 整個 pipeline 死。

加 `socket.setdefaulttimeout(15)` 強制每個 op 上限；progress log 讓 user 下次能立即定位是哪個 ticker / 階段慢。

### How to apply
- 立刻生效（Python module-level 改）。下次 `./daily_update.sh` Step 6 stderr 會出時間戳記日誌。

---

## [2.13.7] — 2026-05-05
### Added — earnings page 專屬 run banner（分離自 news scan-card）

- `Dashboard/earnings.html`：在 hero strip 與 command bar 之間插入 `#ea-run-banner`（紫色 accent，`scan-card-frame` reuse）。含 expand / cancel / dismiss / reload 按鈕 + 即時日誌 pre。
- `Dashboard/style.css`：`scan-card-frame` + `scan-card-log` styles 從 news.html inline 搬到全域，所有 page 共用。
- `Dashboard/page-earnings.js`：
  - `runEarnings` 排隊成功後記 `_eaActiveJobId` + `_eaActiveTicker`、起 2s poll。
  - `pollEarningsRunStatus`：fetch `/api/run-protocol/status`，gate by `name === 'earnings'` AND (`queue_id === _eaActiveJobId` OR `analyze_ticker === _eaActiveTicker`)；只有自家 job 才 render banner。
  - `done` 翻 emerald + 自動 `loadAndRender()` 補資料；`error` 翻 red 顯示錯誤訊息。
  - `resumeEarningsRunBanner`：page load 時若 server 端正跑 earnings 直接接續顯示 banner（重整不會丟進度）。

### Why
User 點「財報分析」時觀察到右下角 protocol pill 顯 `news · 📰 DIGEST`，因為當時 server 端真的在跑 news（earnings 排在 queue 後面）。News page 有 scan-card 顯活 log → 看起來像 news 取代了 earnings。問題不是 pill 標錯，而是 **earnings page 沒有自己的 banner**，user 不知道自己的 job 排在哪、哪時候會跑。新增 earnings-scoped banner 解決：
1. queue 排隊期間 toast 提示位置；
2. 輪到自己跑 → banner 顯示 ticker / elapsed / 即時 log；
3. 完成自動 reload 資料 + 顯示綠色完成框；error 紅色 + 錯誤訊息。

### How to apply
- Hard refresh earnings 頁。
- 排一個 earnings job 觀察 banner 從 hidden → 紫色 running → 綠色 done。

---

## [2.13.6] — 2026-05-04
### Fixed — radar K 線 tail label 格式 + header 文字重複

- `Dashboard/page-radar.js`：tail label / header `updated` 改 `toLocaleTimeString('en-GB', { hour12: false })` → 24h `HH:MM:SS`，避免 zh-TW 加「下午/上午」與 bar label 的 `HH:MM` 風格混搭。
- Header `updated` field 在 tick 模式下從 `tick HH:MM:SS` 改成純 `HH:MM:SS`，避免和 status `15s tick` 的 `tick` 字重複。

### Why
盤中截圖顯示 bar label `10:45` 與 tail label `下午10:58:37` 風格不一致 + status 區出現 `15s tick · tick 下午10:58:52` 重複字。和 5-min bar 沒到 10:50/10:55 無關（那是 FMP 個別 bar commit 慢於 wall-clock，下次 base poll 就會補上）。

---

## [2.13.5] — 2026-05-04
### Added — radar K 線 live tail（FMP `/quote` 每 15s tick 疊在 5-min bars 後）

- `dashboard_server.py`：新 `/api/heatmap/quote/<TICKER>` endpoint + `_fetch_heatmap_quote()`（FMP `/stable/quote`，5s TTL `_heatmap_quote_cache`）。回 `{symbol, price, change_pct, volume, as_of, market_open}`。
- `Dashboard/page-radar.js`：
  - 拆兩個 polling：base bars 60s（`/api/heatmap/intraday/`，原本 15s）+ live tick 15s（新 `/api/heatmap/quote/`）。
  - `_radarTickTail` 維護 ≤25 個 tick（25 × 15s = 6.25min 上限），每 tick `{t: HH:MM:SS, price}`。新 5-min bar 出現（base re-fetch 偵測 `lastBarTime` 變化）→ 清空 tail。
  - `renderRadarKline` 加第二個 dataset：dashed amber line + 1.8px points，從最後一根 bar close 接續延伸。Volume chart 不疊 tail（quote 不帶該 bar 累計 volume）。
  - Header price + change_pct 改用 quote tick 即時更新（比 5-min bar close 即時）。
  - `visibilitychange` 切回 tab 同時觸發 base + tick 各一次。

### Why
v2.13.4 拿掉 visibility gate 但 chart 視覺仍每 5min 才動 — 因 FMP 5-min bars 在 boundary 之間沒新資料。User 質疑「15s API 沒意義」。改用雙 endpoint：粗 bars 走 `/historical-chart/5min`、細 ticks 走 `/quote`，base 不漂移、tail 即時延長，5-min boundary 自動 reset。20 ticks/min × 1 ticker FMP 用量輕。

### How to apply
- Restart `dashboard_server.py`（新 endpoint）+ hard refresh radar 頁。
- 盤中點 ticker tile，5-min bar 後應每 15s 看到黃色虛線往右延一段。每 5min 黃線歸零、新 indigo bar 出現。

---

## [2.13.4] — 2026-05-04
### Fixed — radar K 線 polling 拿掉 visibility gate（不切 tab 也會自更新）

- `Dashboard/page-radar.js:1322`：移除 `setInterval` 內 `document.visibilityState === 'visible'` 條件，只保留 `_radarKlineTicker` 存在性檢查。

### Why
原 gate 是省 FMP/server 用量設計，但 1 ticker × 15s 對 server 無負擔（且 server 端 `HEATMAP_INTRADAY_TTL_SEC_OPEN=15` 已 TTL coalesce）。Browser visibility 在 macOS Stage Manager / 其他 app 全屏覆蓋 / Chrome Memory Saver 下會誤判 `hidden`，user 看著頁面但 polling 卻被 skip → 體感「切 tab 才更新」。

注意：chart bars 是 FMP 5-min OHLCV，視覺形狀仍每 5 分鐘才換新；header `updated HH:MM:SS` 每 15s 跳秒可確認 polling 在跑。

### How to apply
- Hard refresh radar 頁（cache busting 已由 mtime 注入處理）。

---

## [2.13.3] — 2026-05-04
### Fixed — radar 熱力圖補抓非 S&P 500 ticker（修「主題股數 5 卻只看到 1 檔」）

- `dashboard_server.py::_build_theme_heatmap_payload`：第一輪掃 TD theme `representative_stocks` 收集所有不在 `_heatmap_state["tickers"]` 的 ticker，呼叫新 helper `_fetch_theme_extra_quotes(symbols)` 用 FMP `batch-quote` 一次撈齊（單 request、TTL 180s in-process cache）。第二輪 join lookup 用 `_resolve(sym)` 包含 heatmap state + extra fetch 結果。FMP miss / 無 API key → 該 ticker skip（舊行為）。
- 新增 `_theme_extra_quote_cache` + `THEME_EXTRA_QUOTE_TTL_SEC=180`。

### Why
TD theme universe 涵蓋 small/mid cap，heatmap state universe 只 S&P 500（517 tickers）。例：Gold & Precious Metals 5 檔 representative_stocks（NEM/CDE/AU/GFI/HL）只有 NEM 在 S&P 500 → 4 檔被 skip → tile 只剩 NEM 一個。Card body top movers 不受影響因 thematic-screener 用 FMP 直接抓自己的 prediction。

擴 universe 太重；最少改動方案：render 時補抓缺的 ticker quote、cache 3min。實測 17 themes 平均缺 ~25 ticker，1 個 batch-quote call 即解決，不影響整體 latency。

### How to apply
- Restart `dashboard_server.py`。
- Smoke test：`/api/theme-heatmap` 回傳 Gold theme `tickers` length 應 = 5。

---

## [2.13.2] — 2026-05-04
### Fixed — radar 熱力圖 pin 到 recommendations.json 同源 TD cache（修「無覆蓋資料」假空白）

- `dashboard_server.py::_build_theme_heatmap_payload`：先讀 `skills/thematic-screener/data/recommendations/<latest>.json` 的 `theme_detector_meta.file`，找到對應 TD cache 才 join `_heatmap_state`。recommendations 缺檔或 meta 缺欄位 → fallback 最新 TD cache（舊行為）。
- 回傳 payload 增加 `theme_detector_file` + `pin_source`（debug 用，前端不需動）。

### Why
今日 radar 觀察到 17 個 theme 卡片中 4 個顯「無覆蓋資料」，但點開卡片底部 top movers 有資料。根因：thematic-screener 21:06 跑時讀 TD-03 cache 寫 recommendations.json，22:00 跑 `產業掃描` 時 sector Phase 2 又重寫一份 TD-04（`--skip-if-fresh 10800` 觸發），thematic-screener 沒跟著重跑。`/api/theme-heatmap` 一直 glob 抓最新 TD（TD-04）；前端 card body 的 theme.name 來自 recommendations.json（指 TD-03）。兩份 TD 的 sector concentration 系列 theme 名字不同（TD-03 `Financial Sector Concentration` ↔ TD-04 `Financial Services & Banks`），strict name match 失敗 → 4 個 theme heatmap slot 顯空白。

Pin 到同源 TD 後 card body 與熱力圖看的 theme 結構一致；tile 顏色（漲跌幅）仍取自 live `_heatmap_state`，不受影響。

### How to apply
- Restart `dashboard_server.py`。
- 之後若想長期解 TD/screener cache 不同步，要在 sector protocol Phase 2 重寫 TD 後接 thematic-screener re-run（單獨另案）。

---

## [2.13.1] — 2026-05-04
### Fixed — protocol 完成判定加 validator gate（修「綠燈 + 空 dashboard」假成功）

- `dashboard_server.py`：新增 `PROTOCOL_VALIDATORS` map（`sector` → `validate_sector_intel.py`、`news` → `validate_digest_output.py`）。`run_protocol` 跑完且 subprocess `rc=0` 時，再跑對應 validator；validator rc≠0 → 狀態翻 `error` + error 訊息塞前 5 行（含完整輸出 append 到 scan log）。

### Why
今天跑 `產業掃描` 觀察到 banner 顯示綠燈 DONE，但 Dashboard index 市場機制 / 熱門產業 top3 / sector hot/warm/cold / 政治訊號 / 背離觀察全空白。實際 `2026-05-04_sector_intel.json` 缺 top-level `market_regime` / `summary` / `actionable_themes` / `_phase3.political_overlay` / `_phase3.top_catalysts` — Phase 5 emit + validator gate 從未執行。

根因：`_run` 只看 Claude subprocess 的 `rc`，turn 正常結束就標 done，**完全沒驗證產出物**。Schema 規定 Phase 5 末尾 mandatory `validate_sector_intel.py rc=0`，但 server 沒接這條繩。新 gate 直接補上，未來這類 stop-mid-protocol 會以 error 紅色 banner 呈現 + bridge.py 不會被誤觸發。

### How to apply
- Python 3 syntax-only 改動，restart `dashboard_server.py` 即生效。
- 若要新增其他 protocol 的 gate（invest 用 `validate_session_export.py` 等），加進 `PROTOCOL_VALIDATORS` 即可。

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

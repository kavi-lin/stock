# INTEL COMMAND — Session Notes & System State

> **Last Updated**: 2026-08-02 (v4.86.0)
> **Role**: This file serves as the "Short-term Memory" and "Handoff Cache" for AI Agents. It contains market regime states, token optimization logs, and data integrity notes. **Task backlog has been moved to TODO.md; full version history to CHANGELOG.md.**

## 🟢 Session Note (v4.86.0) — 4.82–4.85 review 修正（1 P1 + 7 P2）
- **八條先逐一複跑重現才動手**，沒有照單全收。結果全部屬實，但有一條的嚴重度我下修了：reviewer 說 §14 有「三條路徑全炸」，實測第三條（probe capped）的失敗是 fixture 產物（那條鏈是照 BUY 算的），probe 分支本身是對的。P1 是**兩條** Phase 4.6 路徑。**判準：確認 bug 為真之後，仍要確認它的邊界在哪。**
- **七個 P2 裡有五個是我自己在 4.82–4.85 引入的**，其中兩個是同一種病：**修了 A 卻打開 B**。`_fetch_pe_ttm` 的失敗語意一改，radar 懶抓那條路就從「每天 3 個 call」變成「每小時 60 個、無限期」，因為它的重試原本就是靠「失敗會被快取」這個副作用擋住的。**教訓：改共用函式的失敗語意時，先列出所有呼叫端，逐一問「這條路的重試由誰負責」**——radar 的答案是「沒有人」，而我在程式註解裡寫的是「warm-up 的 sweep 會管」，事實上那個 sweep 只掃 universe。**註解寫了一個我沒驗證的機制，這比程式錯更危險，因為下一個人會信它。**
- **cooldown 跨日被清除是最刺的一條**：我當時就在重寫那個 rollover 分支、還特地寫了「時間戳不能歸零」的長註解，卻只搬了 `call_timestamps`，沒問「同一個 blank 重建還丟掉了什麼別的、也不屬於 UTC 日的東西」。**判準：把某欄位從「隨日重置」救出來時，要掃過同一個 reset 裡的每一欄，逐欄問它到底屬不屬於那個週期。**
- **P1 選擇補欄而不是放寬檢查**：Phase 4.6 改寫決策後，`final_decision` 不再能解釋 sizing 鏈（折半該不該套）。可以把檢查放寬成「兩種都接受」，但那會讓真正該折半卻沒折半的鏈也過關。改成讓 engine 記下 `sized_for_decision`（它自己的輸入），檢查照舊嚴格。**歧義的正解是消除歧義，不是接受兩種答案。**
- **有一條刻意不修**：window 管不到 protocol subprocess 路徑（`note_run` 一次 agentic run 只記 1 筆，實際幾十到幾百 turn）。把那條路納管會讓使用者主動點的操作被背景配額擋掉——那是行為變更，該由使用者定奪。我只把 docstring 改成事實（「governed calls，不是 API turns」）並明講依此 cap 對應 provider turn budget 保護不了那條路。**說謊的 docstring 要修；要不要改行為是另一個決定。**
- **併發鎖補在對的層**：`llm_usage.json` 的單次寫入本來就 atomic，壞的是 read-modify-write。flock 加在**獨立的 `.lock` 檔**上，因為 `os.replace` 會把 usage 檔的 inode 換掉，鎖在它自己身上沒有意義。
- **驗收**：8 支測試 + 3 個 validator/replay 全 rc=0；`test_session_export_schema.py` 50 案（新增 §14 × Phase 4.6 五案）；router 新增 cooldown 跨日 / 過期不復活 / >48h window / 時鐘故障 / roundtrip / 24 執行緒併發；heatmap 新增 mid-batch 429 partial / 非重入 / lazy retry floor。commit 排除 `data.json` / `llm_usage.json` 兩個 runtime artifact（上一版夾帶進去被 review 點名）。SYNC OK 4.86.0。

## 🟢 Session Note (v4.85.0) — heatmap PE warm-up 重試（V325.X-PE-WARMUP-RETRY）
- **TODO 描述的症狀對，病因更嚴重**：記的是「cache 空到下次重啟」。實際讀 code 發現 `_fetch_pe_ttm` 在 429 熔斷期回傳**全 None 的 dict** —— 跟「這支股票本來就沒 P/E」完全同形。而 `val_snapshot` 的過濾條件是 `isinstance(v[1], dict)`，全 None dict **通過了**。所以失敗值不只被快取 24 小時，還會被當成事實**蓋掉既有的好值**。**教訓：修 bug 前先讀清楚失敗值長什麼樣，不要照 TODO 的描述直接動手。**
- **根因是型別分不出兩件事**：「抓到了但沒有資料」vs「根本沒去抓 / 抓失敗」在原本的回傳型別上是同一個東西。加 retry 之前要先讓函式**有能力表達失敗**（改回 `None`），否則重試邏輯只是在重試一個它以為成功的東西。
- **失敗不進快取，比「快取失敗但標記」更簡單也更安全**：舊值留著就是最好的降級（stale 好過空白），而失敗的 ticker 自動落回 `todo`（因為 `not isinstance(cached[1], dict)`），不需要第二份失敗清單。
- **429 熔斷不該計 backoff**：熔斷期根本沒發請求，記一次失敗是懲罰錯對象；改成把下次嘗試時間對齊熔斷解除時間。
- **兩個 caller 都要修**：radar 的 lazy fetch `_bg()` 也在快取 None，會佔住 24h TTL 並讓 warm-up 的重試掃描看不到那支 ticker。
- **驗收**：`tests/test_heatmap_pe_retry.py` rc=0（部分失敗 / backoff 抑制 / 補抓不重抓已成功者 / 失敗不洗掉好值 / escalate 且有上限 / 429 不計失敗 / 全暖零 HTTP）；`dashboard_server.py` 語法 OK；SYNC OK 4.85.0。

## 🟢 Session Note (v4.84.0) — model router rolling window（V321.X-ROUTER）
- **本版最重要的一行是「不要歸零」**：`_load_usage()` 原本在 UTC 換日時整份重建。日計數該歸零，但 `call_timestamps` **不能** —— session window 不理會午夜，跟著清空等於在 00:00 UTC 憑空發還一整個 window 的額度，正好是這個計數器要防的事故。這是整個功能唯一真正微妙的地方，測試特地寫了一條跨午夜案例。
- **測試通過但功能沒生效，抓到的是最典型的一種假綠燈**：`--status` 顯示 `window_max_calls: null`，查下去發現 `load_llm_config()` 是**逐鍵白名單**不是 merge，只複製 `daily_max_calls`，我新加的兩個 key 被靜默丟掉。單元測試全過是因為它們餵手搭的 cfg dict，繞過了 loader。**教訓：新增 config key 一定要有一條走真 loader + 真 config 檔的 end-to-end 斷言**，否則測的是自己餵進去的東西。已加，並寫進 OPS §7。
- **降級方向再次一致**：時鐘偏移到未來的時間戳「照算」（丟掉會少算 window）、naive timestamp 當 UTC 讀（丟掉同樣少算）、解析失敗的才忽略。原則是**寧可少給額度也不要多給**。
- **兩道閘獨立而不是取代**：daily budget 與 window 各自能單獨擋下一個 model，`model_headroom()` 回較緊者 —— 呼叫端打算連發 N 次時，不能被日額度騙過去。
- **只有 session-window 制的 CLI 設 window**（claude / codex）；gemini / grok 是 per-minute rate limit，硬套 5hr window 是張冠李戴，留空 = 不設閘（與 `daily_max_calls` 缺/0 同慣例）。
- **驗收**：`test_model_router_window.py` rc=0（含跨午夜、舊 shape、corrupt 檔、loader end-to-end）；`--status` 四個 model 的 window 欄位皆正確（claude 0/120、codex 0/80、gemini/grok null）；`/api/llm-config` POST 的 merge 不會洗掉新 key；SYNC OK 4.84.0。

## 🟢 Session Note (v4.83.0) — decision badge 改吃決策時真值（V20-A5）
- **TODO 過期了，動工前先查證**：V20-A1 / A2 寫著「已存 data.json，UI 沒秀」，實際上 badge 與 `SIGNAL_TIPS` 兩邊都在，更早的版本就做掉了（`ALIGNED` / `unclassified` 兩個良性值刻意不發 badge，與 `macro_alignment` 只標 CONTRARIAN 同一慣例——那是設計不是遺漏）。**教訓：UI 類 TODO 動工前先跑一次 grep 確認現況，backlog 會比 code 舊。**
- **但 A5 不是「只省一層 `.det_shadow`」**：renderer 原本**只**讀 `det_shadow`，那是 `apply_det_shadow.py` 事後補寫的 shadow；V5.1+ entry 的 `calculation_steps` 才是決策當下真的動了分數的值（confidence 乘數 / position cap / buy_threshold / cascade 罰則）。兩者理應相同但來源不同，badge 顯示錯的那個不會有人發現。改成 **決策時優先、shadow fallback**，並把 `*_source` 一起送出去。
- **有了兩個來源就該驗它們一致**：加 `*_disagrees` + 兩個 SPLIT badge（與既有 `RT DISAGREE` / `VAL DISAGREE` 同一套視覺語言）。不一致代表後處理跑的時候看到的 lane scores / counter_thesis 文字跟決策當下不同 —— 通常是 entry 被事後編輯。現行 172 筆 0 不一致（健康），但這是往後才會用到的哨兵。
- **fallback 留著是為了不綁 bridge 重跑**：renderer 讀不到攤平欄位就退回 `det_shadow`，還沒重生成的 `data.json` 照樣渲染。
- **驗收**：`bridge.extract_audit_history()` 實跑 192 筆，2 筆 source=calculation_steps（V5.1 那兩筆）、67/170 筆 source=det_shadow、0 筆 disagree；`node --check` 兩檔語法 OK；SYNC OK 4.83.0。

## 🟢 Session Note (v4.82.0) — Phase 4 script 化（TODO L2）
- **起因**：Phase 3 已在 4.80.0 script 化，Phase 4 是最後一塊仍靠 LLM 手算的決策數學（九段乘法鏈 + 兩張查表 + 一個條件 reject + 兩個獨立導出的停損價要調和）。
- **先跑 feasibility 再定分母，這次證明是對的**：動工前掃 172 筆 history —— `vol_adjusted_limit_pct` 持久化 **0 筆**、`tail_risk_score` 1 筆。sizing 鏈根本無法前向 replay，硬做出來的「100% parity」會是假的。改用 **inverse solve**（把已知乘數除回去、檢查隱含 base 是否落在 (0, 20%] 可行區間），47/172 全過。**教訓：replay harness 的第一步是量分母，不是寫比對邏輯。**
- **`min()` 不可逆這件事值得記**：macro cap 是 `min(tail_adj, 0.03)` 不是乘法，鏈上只留數字就無法從尾部反推它有沒有觸發。這批 trade 直接整批排除（`macro_cap_min_not_invertible`）而不是硬解一個假因子。存 `sizing_chain.steps[]` 就是為了讓未來的 entry 不必再走這條退路。
- **replay 抓到 engine 的真 bug**（不是它本來要找的東西）：`band_capped` 是 `[max(band_lower, support), band_point, min(band_upper, resistance)]`，support 高過 band_point 時兩軌會產出 `[高, 低]` —— 歷史上 AAPL/PLTR/TSM 三筆命中。**教訓：replay 跑歷史資料時，異常的「replay 值」和異常的「stored 值」一樣值得看。**我第一眼只在讀 stored 那欄。
- **rule-era 一開始標錯，rc=1 是假的**：R/R cohort 我先寫死 `era="current"`，40 筆全變 NEEDS_TRIAGE。但 V4.82.0 之前根本沒有任何 script 強制 entry = band 或 R/R = 區間隱含值 —— 那 40 筆量的是本版要消除的漂移，不是 engine 缺陷。三個 cohort 統一綁 `CURRENT_RULES_SINCE`。**判準：問「這條規則當時存在嗎」，不是「這個欄位當時存在嗎」。**
- **protocol 有三處原文沒定義，script 化才浮出來**：① `base_stop_pct` 從未被獨立定義（採「結構停損價相對 entry reference 的百分比」，唯一能讓 Step 1 與 Step 4 談論同一個部位的讀法）；② binary `× 0.5-0.7` 是區間，一律取保守端 0.5 才可重現；③「R/R 不足 → 收緊 entry 或降級 HOLD」沒說收到哪，定為 aggressive 中點 → conservative 中點 → conservative 下界。**三處都寫回 protocol，不是只寫進 code。**
- **降級一律往保守側，且要說出口**：tail_risk 拿不到時取 `MODERATE ×0.75` 不取 ROBUST（把最大乘數給最不了解的情況）；表外 sector 取 cyclical；day-21 reject 的 RS/distance 兩個輸入都缺時「不 reject 但維持 ×0.50」並註記「無法判定」——**缺料 ≠ 通過**。同理 F1 registry 不可得時標 `registry_unavailable` 而不是回報 0 個部位。
- **順手補一個洞**：`fragility_label` 值域從來沒驗過（§6 只驗非 null），歷史上有 6 筆用了表外標籤（`RESILIENT` / `MEDIUM`），Step 3 乘數無從對應。是 replay 的 sizing cohort 排除表跳出來的。
- **驗收**：`test_trade_plan_builder.py` 17 組 rc=0；`test_session_export_schema.py` 45 條（含 18 條新 §14 tamper）rc=0；`replay_trade_plan.py` 三 cohort `current_rule_mismatched=0` rc=0；`replay_decision_engine.py` / `test_decision_engine.py` / live validator 全 rc=0；SYNC OK 4.82.0。

## 🟢 Session Note (v4.81.0) — export schema 升 V5.1（TODO L1b）
- **起因**：4.80.1 把 §13 硬閘綁在 `export_date ≥ 2026-08-03`，當時就記著「日期切不如版本切」。這一版把門檻改綁 `session_export_version = V5.1`。
- **掃描比 TODO 寫的多兩個點**：① TODO 只列了 validator + schema doc + protocol，漏掉 `validate_markdown_export.py` 這個隱藏消費端（`!= "V5.0"` 直接 return，新版 entry 會整段跳過「合理股價」檢查）；② `Dashboard/page-decisions.js` 的 `detectProtocolVersion()` 已經把 `'V5.1'` 這個 token 用在別的概念上（有 `forward_expectations.trajectory` 就回 V5.1，且優先級最高）——直接拿 V5.1 當 schema 版號會撞名。**教訓：升版號前先 grep 這個 token 有沒有被別人當成別的意思用**，不只 grep 欄位名。
- **單值比較是這次的主題**：`ver == "V5.0"` / `ver != "V5.0"` 這種寫法在升版當下不會報錯，只會靜默改變行為——replay 會把新 entry 全判成 `pre_v5_four_lane_schema`（覆蓋數歸零但 rc 仍 0），markdown validator 會整段跳過。全部改成版本集合，且下游兩支改 **import** validator 的集合而不是各自硬寫。
- **順手抓到兩個真的洞**（都不在 TODO 上，都是實測出來的）：① `hot_zone_eval` 的 warning 條件 `ver != "V5.0"` **寫反了**——只對不可能有該欄的舊 entry 發警告，對必須有該欄的現行 export 恆不發（REVIEW_2026-07-31 記的「75 筆全 None 卻沒人吭聲」就是這個）；② §13 Tier B 的 cascade 檢查只在 `rule_*` 名稱上比對 `penalty_value`，把已套 0.95 懲罰的鏈條改標 `no_penalty` 就能過閘——是寫 tamper battery 時第 11 條意外 rc=0 才發現的。**tamper 測試要包含「標籤說謊」而不只是「數字說謊」**。
- **修一個錯的預期而不是錯的程式**：tamper「banded BUY 卻標 HOLD」我原本預期 rc=1，實際 rc=0 —— 查表確認 `BUY → HOLD` 是 Auto REJECT / decision cap 的合法路徑，是我的斷言錯。改成反向（低於門檻卻標 BUY）才是真的越界。
- **schema doc 的 FULL EXAMPLE 本身是壞的**：header 寫 V5.0、JSON 戳 `V4.8`、內容卻有 `valuation_lane`——照抄會直接撞 §2b mis-stamp guard。改成實跑 engine 產出的完整 V5.1 範例，並讓驗收 fixture **直接從 doc 解析**，以後 doc 壞掉測試就會紅。
- **review 抓到一個對稱性遺漏**：cascade 標籤檢查我只鎖了 penalty 側，bonus 側同款謊言（×1.15 鏈條改標 `no_penalty`，`bonus_applied` 與數字都不動）仍 errors=0。已補兩側各雙向，並用 `run_phase3()` **現跑**一條 consensus_bonus 鏈當 fixture（不寫死，規則移動時不會過期）。**教訓：補一條 invariant 時先問「這條規則有幾個對稱面」**——penalty/bonus 是同一個 cascade 欄位的兩側，我只想到觸發我的那一側。
- **驗收**：23 條 battery 全過（舊 V5.0 rc=0、V5.1 缺 `calculation_steps`/`decision_engine_version` 各 rc=1、日期後衛 rc=1、V4.8/V5.0 兩個 mis-stamp guard rc=1、11 條 §13 tamper 全 rc=1、bonus 側 3 條含 engine 實跑鏈 rc=0）；live history rc=0；`test_decision_engine.py` rc=0；markdown validator rc=0 且 V5.1 仍強制「合理股價」section；replay 覆蓋不變（1+2+169=172）；SYNC OK 4.81.0。

## 🟢 Session Note (v4.80.1) — 4.80.0 review 的兩個 P1
- **起因**：外部 review 對 v4.80.0 做端到端實測，抓到 2 個 P1、2 個 P2。兩個 P1 我都先自己複跑重現才動手（不照單全收），確認屬實。
- **P1-1 是本次最有價值的一條**：Auto REJECT 的 `rr < 2.0` 與 `FULL_FALLBACK` 兩條我寫成「只在決策是 BUY-side 時才評」——單看是對的（HOLD 的 rr 本來就是 null）。但熱區 probe 是在硬閘之後才把 HOLD 升成 STAGED_ENTRY，升完不回檢，於是 probe 可以帶著 R/R 1.5 開倉。**教訓：閘的評估對象若是「決策」，那任何會改寫決策的步驟之後都必須重評**；我把 probe 排在硬閘之後是對的（spec 要求硬閘優先），錯在沒意識到那兩條閘的輸入被自己改掉了。修法是 fire 前用假設決策 `STAGED_ENTRY` 重跑一次硬閘。
- **P1-2 是自己挖的坑**：同一版 protocol 才定案「cap + override → STAGED_ENTRY」，validator §13 的 band 可達集卻沒跟著加，第一筆真走 override 的 BUY 會卡死在收尾（而 PM 依規禁止手改）。**教訓：新增一條決策路徑時，要同時問「哪個 validator 會看到這條路徑」**。
- **測試盲點**：`reject.rr_irrelevant_for_hold` 與 `reject.full_fallback_hold_ok` 兩條單元斷言各自都對，漏的是「HOLD × probe」的組合。已補 4 條 e2e fixture，含「R/R 2.5 仍應 fire」的反向斷言防止修過頭變成 blanket veto。
- **順手**：§13 原本能靠「省略 `calculation_steps`」整段繞過（protocol 寫的「validator 會擋」實際不成立）→ 改為 2026-08-03 起缺此欄 rc=1；engine 缺 lane 由 warn 改 raise（原本會產出 `MISSING` 字串讓 validator 報「unparseable」，訊息誤導 triage）。
- **量測紀律**：驗收時我自己的 shell 迴圈把三筆 rc 讀成 2（實際 0），改成無 pipe、無迴圈展開的逐條直跑才對得上——與 reviewer 稍早的 pipe-吃-rc 是同一類錯。**rc 驗收一律逐條直跑**。
- **驗收**：`test_decision_engine.py` rc=0；validator 4 個正常 fixture rc=0（含 live history 與 pre-4.70 entry）、7 種竄改/違規全部 rc=1；replay rc=0 且覆蓋數不變（1+2+169=172）；SYNC OK 4.80.1。

## 🟢 Session Note (v4.80.0) — Phase 3 決策數學 script 化（TODO L1）
- **起因**：TODO「Protocol Lean 化」的 L1。共識是「先 script 化決策數學，再談條件式跳過 LLM」，所以這一版只搬公式、不動 score 的生產方式。
- **做掉**：`decision_engine.py`（Step 1 三檔 C_eff → 1.5 structural → 1.7 polarization → 2 五級 cascade → 3 macro → 4 dynamic threshold + band → Rec 11 判定樹 → Auto REJECT；`--phase 4.6` 獨立套 decision cap）+ `test_decision_engine.py`（spec parity 契約）+ `replay_decision_engine.py`；protocol Phase 3/4.6 改 script call；validator §13 硬閘。polarization / red_team_basis 直接 import `apply_det_shadow.py`，沒有第二份實作。
- **原假設被實測推翻**：TODO 寫「111 筆 replay 逐筆 triage」，實際能做 parity 的只有 **1 筆**。原因不是 harness 弱，是**史料本身沒有 per-lane confidence**——`history.json` 只存 `avg_confidence`，per-lane 值只能從 `calculation_steps`（全語料 2 筆）、event_index `agent_breakdown`（有 5 lane 的 33 筆全在 V4.70.0 之前）或 MD 報告表頭（格式十幾種）回收。V4.70.0（2026-07-16）之後累積的 deep-dive 只有 4 筆，那 4 筆全部逐點相符（1 筆嚴格 parity + 3 筆在 spec 預設假設下 |Δ| ≤ 0.0003）。
- **不猜的做法**：未持久化的離散輸入（structural_shift tier / counter_evidence_strength / rule-2 transition / binary event 48h）不套預設值，而是**列舉全組合跑 sweep**——結果不變才算 eligible，會變就列 `decision_sensitive_unknown` 並附「spec 預設值」advisory（明確標示是假設）。38 筆落這一類，其中 `structural_shift.tier` 38 次全中，等於量化證明「這個欄位該被持久化」。
- **順手抓到兩個 spec 矛盾**（已寫進 protocol，非默默處理）：① Phase 4.6 rule 6 的「熱區例外」在 decision_cap 路徑上恆不成立——validator §11 禁止 probe 與 cap 併存，且 Phase 3 判定樹會先出 `suppressed_by_cap`；② cap 對 `BUY` 的落點原文沒寫死，依 override 條款與歷史 23 筆 entry 定案為「無 override → HOLD、有 override → STAGED_ENTRY」。
- **驗收**：`test_decision_engine.py` rc=0（A–M fixture + MU 2026-08-02 golden replay，5 條 Step 1 字串逐字相符）；validator 對現行 history rc=0（向後相容），6 種竄改（分數、乘積、band 不可達、polarization 說謊、threshold 矩陣、legacy C_eff）全部 rc=1；replay rc=0；SYNC OK 4.80.0。

## 🟢 Session Note (v4.79.1) — signed bias 改吃去重集合
- **起因**：4.79.0 實作 P2-3 時順手發現 `_signed_bias` 繞過 dedup，記進 TODO；使用者指示接著做。
- **做掉**：`_bias_rows` 改優先讀 `forecast_points`（v4 新暴露），criterion 加 `bias_basis` 記錄實際來源。對照數字：一個樂觀預測重跑 20 次 + 一個準確預測，未去重 bias `1.905` vs 去重 `1.0`——差距純由重跑次數造成。這是 shadow→live gate 的四個誤差判準之一，等於讓「跑幾次」影響升格判斷。
- **中途攔下自己的第二個坑**：原本 legacy fallback 無條件套 `_dedupe_forecast_rows`。但 dedup key 是預測身分，pre-v3 與手工 rows 沒有 `ticker`，全部 hash 到同一 key——實測 16 筆塌縮成 **1 筆**，還標成 `deduped_legacy_evaluations`（標籤是錯的，那是塌縮不是去重）。改成：無 identity 就不去重、原樣計分並標 `raw_evaluations_not_deduped`。**教訓同上一版**：既有測試 fixture 的 row 沒有 identity 欄位，塌縮後測試照樣全綠，是手動印出 `n` 才看到。
- **驗收**：20 支 fe regression rc=0（success_criteria 27 asserts，新增 9 條）；真實語料 `bias_basis: deduped_forecast_points`、verdict 維持 `insufficient_evidence`；SYNC OK 4.79.1。Shadow-only。

## 🟢 Session Note (v4.79.0) — 4.78.0 review 的三項 P2 收尾
- **起因**：使用者要求 review Codex 對 forward-expectations 的修正。review 結論是方向正確、宣稱幾乎全部重現（20 支測試 rc=0、MU 數字逐項對上），但找到 1 個 P1（archive 最新 MU snapshot 生成於兩個 commit 之間，仍帶被晉升的 -9% cohort median）與 3 個 P2。P1 已於 `ce59d45` 重跑蓋掉，本次做 3 個 P2。
- **做掉**：① promoted cohort 的 note 改由 `rationale.criteria` 動態產生——原本寫死演算法描述，curated cohort 一旦取得 `growth_base_rate` 核准就會被誤標成演算法選取；② window-CAGR 路徑補上與 level 路徑對等的 point-in-time gate（`generated_at ≥ window_to` 拒收，`≥ window_from` 標 caveat 但仍計分）；③ CLI 改印 `summary` + `forecast_points`，`evaluations` 需 `--full-evaluations`。
- **自己踩到的坑**：原本只加一個 `point_in_time_caveat_count` 且只數 comparable rows——真實語料跑出來顯示 0，但實際有 19 筆帶 caveat 在等成熟，讀起來像「沒有 caveat」。拆成 `scored_` / `pending_` 兩個欄位才誠實。**教訓**：計數欄位若有前置篩選條件，要問「這個 0 是真的沒有，還是被篩掉了」。
- **實測**：685 snapshots，CAGR gate 新增拒收 **0 筆**（符合 review 預估的「現存 0 筆」，無回歸）；19 筆 legacy row 帶 caveat；CLI 輸出 1.82 MB → 54 KB（3.0%）。`success_criteria` verdict 維持 `insufficient_evidence`。
- **驗收**：20 支 fe regression rc=0（calibration 65 asserts、核心 68 asserts）；SYNC OK 4.79.0。Shadow-only。
- **新發現（未修，已記 TODO）**：`forward_expectations_success_criteria.py:38` 的 `_signed_bias` 直接走 `evaluations` 全量 rows，**繞過 dedup**——summary 用 99 筆去重後的 row，signed bias 卻會用 2696 筆含重跑重複的 row。今天 comparable=0 所以無影響，樣本成熟後會是實質偏誤。
- **並行風險**：本次全程有另一個 session 同時在改 `forward_expectations_calibration.py` / 其測試檔（移除 `_latest_snapshot_per_ticker` 死碼 + 新增 Fixture I guard），兩次 Edit 都收到「file modified on disk」。本次 commit 因此含該 session 的清理，非全部為本 session 產出。

## 🟢 Session Note (v4.78.1) — Calibration index（先量測再選方案）
- **起因**：committing 全部未提交改動後盤點體積，forward_expectations ledger 磁碟 80MB / 684 檔、約 31 檔/日成長。使用者問壓縮歸檔對效能的衝擊。
- **量測翻轉了結論**：tar.gz 壓縮 9.6x 但**只省空間不省時間**（讀取反而慢 7%，且 git 本來就 zlib 壓過，加 96MB artifacts 只讓 `.git` 從 83M 長到 92M）。真正的問題是全語料掃描隨檔數線性成長：684 檔 0.36–0.64 s → 1 年 3.2 s → 5 年 13.5 s。
- **關鍵發現**：calibration 只評 2 條 lane、只讀 6 個欄位，這 6 欄在整個語料只有 1.81MB（**比 79MB 小 44 倍**）；97% 解析成本花在它從不讀的 evidence/provenance 與尚未評分的 lane 上。且它是**唯一**掃整個 ledger 的消費者——其餘 fe_gap / fe_price_range / success_criteria 等都是 `--snapshot-file` 單檔入口。
- **做掉**：derived index（放 ledger 目錄**旁**，放裡面會被 `*.json` glob 當快照）；條目綁 size+mtime，不符即回讀原始檔；`--no-index` 可全量核對。685 快照 362 ms → 29 ms（12.5x），輸出與全量掃描逐字相同。
- **紀律**：索引是快取、ledger 才是紀錄——快照不可重新產生（vintage 依賴當日分析師估計），任何情況不得為索引刪原始檔。之後要評 `base_rate_lane` 等目前未計分的 lane，須擴 `INDEX_FIELDS` 並 bump `INDEX_SCHEMA`（舊索引自動重建）。
- **驗收**：calibration 42 asserts（新增 Fixture H）、20 支 fe regression rc=0、success_criteria 正常委派；SYNC OK 4.78.1。
- **未動**：`_latest_snapshot_per_ticker` 是 v2 遺留死碼（只剩自己的測試在呼叫），本次不清理。

## 🟢 Session Note (v4.78.0) — Forward Expectations 前瞻預測修正
- **範圍**：正式 `forward_expectations` shadow engine；未混入舊 12m EPS×P/E forecaster，也未改 live DCF/FV/decision。
- **修正**：三個 annual-estimate 消費者統一 future-only cutoff；終端區間加 horizon/年化/coverage 降級；calibration 能在完整 FY 實績後核對 level 並保留最早 vintage；base-rate 需 metric-specific scope，MU 的 P/E `range_only` cohort 不自動擴成 growth anchor。
- **MU 影響**：排除 1 筆 elapsed FY 後，consensus revenue/EPS CAGR `66.72%/100.90%` → `41.34%/40.40%`；2030 終端 coverage 8，明確 thin。SNDK/WDC/STX 多年 revenue CAGR 中位 `-9%` 因 cohort 僅核准 P/E range，保留揭露但不進 numeric gap。
- **驗收**：23 支 Forward Expectations regression scripts rc=0；核心 55/33/41/61/16 asserts；682 snapshots → 99 dedup forecast points，0 comparable（尚未真正成熟，誠實維持 insufficient sample）；SYNC OK 4.78.0。

## 🟢 Session Note (v4.77.0) — 估值引擎 review 修正（degraded path 治理）
- **起因**：4.76.0 的外部 Claude review 因 CLI 未登入中斷，改由本 session 直接完成 review（範圍 A = commit `4e54e79`；B = 未提交的 DCF-primary + range-only peer fallback），共 12 項發現；使用者指示「你來負責修正」。
- **關鍵判斷**：12 項全部落在 degraded / fallback 分支，happy path（MU）完全正確。所以修法統一為「缺資料 → 保守且出聲」，而不是原本的「缺資料 → 套最寬鬆的合法上界」。
- **做掉(firm)**：① start EBIT margin 期間對齊（3 季 roll-forward vs 已公布季度兩種基礎，provenance 可分辨）；② `_render_degraded_md` 讓無 FV 的 run 產出 `DEGRADED` 報告而非 TypeError；③ 缺年度估計時成長種子改用 base growth 假設（原本直接套 45% cap）；④ `projection_degrade_reason` 5 種 reason 進 payload + warnings，禁止靜默退回 legacy；⑤ mode 讀不到的 override 列入 warnings；⑥ earnings cache 改 parse 檔名日期（mtime 會被 git checkout 重置）；⑦ `_eps_growth` 只取最近兩個未來 FY、超 clamp 回 None（原本會拿歷史成長或改抓更後面高成長年度）；⑧ cohort schema 驗證 + `pe_min/max` 離散度；⑨ canonical peer set 健康時不渲染第二張 peer 表；⑩ 新增 `--projection-mode auto|legacy`、`--xlsx` graceful skip、報告「本次採用」欄與 sensitivity 下限註記。
- **MU 迴歸**：FV `$762.13`、WACC `12.49%`、sensitivity `$693.74–853.60` 與 4.76.0 逐項一致（MU 走 3 季 roll-forward，不受修正影響）。快取宇宙 25 檔中 PEG 僅 CSCO 變動（`11.95%` → `10.15%`，修正值）。
- **驗收**：`test_dcf` 104 / `test_comps` 52 / `test_export_xlsx` 13 asserts 全 rc=0（新增 27 條對應 regression）；`test_compute_price_framework.py` + `test_valuation_pack_consistency.py` + `check_skills.py` + `validate_session_export.py` rc=0；SYNC OK 4.77.0。
- **下一步**：範圍 B 的 6 個檔案（SKILL.md / config / comps.py / peer_cohorts.py / export_xlsx.py / 2 支測試）仍是 untracked——review 發現 #9 指出 commit `4e54e79` 的 `--xlsx` 會 import 到不存在的 `export_xlsx`，已加 graceful skip 擋住 crash，但根本解是把 B 一起 commit。等使用者決定。

## 🟢 Session Note (v4.76.0) — DCF-primary + audited peer range
- **使用者定案**：DCF commit 結果作主 FV；LLM 找到的同產業候選若 provider peer endpoint 漏掉，可進 skill，但數字與 eligibility 必須由 Python；其他 anchors 只解釋區間。
- **做掉**：DCF commit `4e54e79`；audited `peer_cohorts.json` 只存候選/限制，P/E 由 shared adapter 重抓且 ≥3；`range_only` 永不補 live peer anchor。Structural DCF 改 primary FV，新增 explained range 與 report injection。
- **MU**：primary `$762.13`；sensitivity `$693.74–853.60`；without peer `$797.32`；SNDK/WDC/STX P/E anchor `$1,785.39`、with-peer `$1,291.36`；含 PT 的完整帶 `$693.74–1,468.26`。
- **驗收**：comps/framework/inject regression、pack consistency、invest validator、skill validator、Claude same-session review（結果見本 session 後續）與 version sync。

## 🟢 Session Note (v4.75.1) — MU through-cycle DCF 重建
- **起因**：MU 舊 vendor DCF `$384–446` 與多個估值落差過大；使用者要求聚焦重建 DCF。
- **做掉**：confirmed shift 改以 FY26 quarterly roll-forward 作 t0、FY27 起折現；分析師營收套 45/30/20/12/8% caps；EBIT/D&A/capex fade 到 normalized state；terminal capex 含成長再投資；最新 net cash/shares；異常 EBITDA/FCF sign fail-visible；beta 用 Blume mean reversion，override 保留原意。
- **MU 結果**：DCF `$762.13`，WACC `12.49%`，terminal g `2.5%`；cached `$823.03` 下 upside `-7.4%`，使用者報價 `$812` 下約 `-6.1%`；sensitivity `$693.74–853.60`。舊 vendor DCF 保留 audit、退出 live vote。
- **驗收**：DCF / canonical framework regression、py_compile、invest validator、version sync rc=0；報告 `reports/20260802_MU_dcf_model.md`。

<!-- 批次輪替制：主檔超過 20 個 Session Note 時跑 `python3 scripts/rotate_session_notes.py`，最舊 10 個自動切成 archive/session_notes_v<A>_to_v<B>.md。查舊版本：Grep 版號於 archive/session_notes_v*.md（規則：docs/agent-ops/MAINTENANCE.md §3） -->

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
| `investment_v5_0` | `invest_logs/history.json` | `final_decision`, `score`, `macro_alignment`, `key_risks` | decisions 頁全部 |
| `sector_v1.3` | `sector_logs/*_intel.json` | `market_regime`, `_phase0` (breadth/FTD/MT), `today_verdict` | index + sector |
| `news_v2.1` | `news_logs/*_digest.json` | `verdicts[]`, `trump_signals`, `catalysts` | news 頁 + sidebar |
| `breadth_analyzer`| `breadth_cache/*.json` | 6 組件 breadth + trend | index 廣度 gauge |
| `positions.json`  | — | lots → avg_cost / live_position | decisions 持倉 |

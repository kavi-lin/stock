# INTEL COMMAND — Backlog & Tasks

> **Last Updated**: 2026-08-10 (v4.127.1)

---

## ✅ Done (v4.123.0) — Phase 2 fan-in 紀律（§17）+ fan-out 契約與語法分離

> 承接 `docs/plan_invest_stale_stages.md` T2 / T3。

- [x] **validator §17**：`degraded_analysts` 裡每個 lane 的 `C_eff` 不得 > 0.60。繞過「per-lane confidence 沒進 export」的方法是用 `c_eff()` 的三檔量化（`<0.45→0.35`/`<0.675→0.60`/`else 0.72`），所以「confidence ≤ 0.6」等價於「不得為 0.72」，零偽陽；C_eff 取自 `calculation_steps`，受 §13 + §5l 保護。
- [x] `FULL_FALLBACK` ⟹ 5 degraded + `STRONG_COUNTER`；≥2 degraded ⟹ 非 `PARALLEL_SUBAGENT`；mode 值域強制。**恰好 1 個 degraded 只 warning**（protocol 未定義單一失敗的 mode）。
- [x] **`degraded_analysts` 改為可機器讀**：過去 10 種寫法指涉 5 個 lane（cap 接不上去的真正原因），現要求以 canonical lane 名開頭；附註照留。名稱與 mode 值域對 `export_date >= 2026-08-10` 為 error。
- [x] Fan-Out 段與 GLOBAL RULES #3 改成**先講行為契約再講 Claude 語法**，並指向 `_adapt_protocol_prompt()`（非 claude provider 的詞彙對照，已有 per-provider 測試）。
- [x] 殘留掃描更正 `investment/README.md` 兩處**四 lane 時代**的數字（「4 全失敗 → FULL_FALLBACK」「2-3 失敗 → PARTIAL」），否則文件與 §17 直接打架。
- [x] 6 個種回 bug 全紅；§17 對 188 筆歷史掃描 0 error / 12 warning。

## ✅ Done (v4.127.0–.1) — Phase 5 組裝 script 化，並由首次真跑驗收

- [x] `build_session_export.py`：吃各 phase artifact + 單一質性檔 → 吐 export entry **與** `phase_inputs` bundle（後者過去無人產生，是 renderer 硬性前置）。封閉 schema 擋「質性檔長回手寫 literal」。
- [x] protocol §PHASE 5 Step 1 改寫：🚫 不得自寫組裝腳本。schema doc 補「Phase 5 質性檔」節。
- [x] **2026-08-10 12:03 META 真跑驗收（codex，9m40s，6.47M in，rc=0）**：零自組腳本、**質性檔一次寫對**（原本預期會來回幾輪，沒發生）、validate rc=0、render 333 行報告。
- [x] **fix 3 生產驗證**：`comps.py` 同一個 META 資料缺口回 **rc=0** + `comps_implied_value: null`，模型繼續走完 —— 09:03 那輪就是這裡硬停的。
- [x] **v4.127.1 補兩個組裝器漏欄**：`burry_score`（改讀 p3 輸入）、`multi_horizon_price_framework`（改讀 p4 輸入）。重建 entry 與 live 決策數字逐欄相同，validator 由 2 warning 轉全綠。
- [ ] **live 的 META entry 仍是 v4.127.0 版**（缺那兩欄，validator 只出 warning 不擋）。要補的話跑 `build_session_export.py … | append_session_export.py --replace-last` 再重跑 Step 1.5 + renderer。**決策數字不會變**（已驗證逐欄相同），純粹是紀錄完整度。**等使用者決定要不要動 live 決策帳本。**
- [ ] **`thesis_registry` 這次回 `registry_unavailable`**（log: `⚠ concentration 輸入不可得 — F1 未評估，不當作 0 部位`）。行為正確（不把不可得當成 0），但 V20-F1 的 sector concentration 檢查等於這次沒生效。要查 registry 為什麼不可得。

## ✅ Done (v4.126.0) — META 兩次失敗的兩個根因（都在 repo，不在 codex）

- [x] **`_persist_artifact` 寫完整 phase-3 輸出**（6 → 24 欄）。被丟掉的 18 欄裡有 META run 要讀的 5 欄，
  於是 `KeyError: 'avg_confidence'` → 空輸入 → 沒 history 沒報告。§5l 只讀 `calculation_steps` 不受影響。
  種回 6 個斷言驗過會紅。
- [x] **`comps.py` 同業不足改回 rc=0**（見上方拆解）。種回 1 個斷言驗過會紅。
- [x] **artifact gate 訊息不再誣賴模型**：原文對「依紀律中止」的 run 是錯的，改為並列兩種可能 + 附 log 路徑。
- [x] **證明不是 codex 硬傷**：當天五次 run 全是 codex、成功兩次；成功的 NVDA 08:43 與失敗的 META 09:14
  同樣 ~7.3M context、同樣寫拋棄式組裝腳本，**唯一差別是後者去讀了 artifact**。
- [x] ~~**Phase 5 組裝仍是模型每跑一次現寫一支拋棄式腳本**~~ → **v4.127.0 完成**：
  `build_session_export.py` 同時吐 export entry 與 `phase_inputs` bundle（後者過去沒有任何
  script 產生，是 renderer 的硬性前置）。封閉 schema 擋掉「質性檔長回手寫 literal」。
  實測用那次失敗的 META artifact 重跑：validate rc=0 + render rc=0（276 行報告）。
- [ ] **仍不是全自動，且這是設計上的**：質性檔裡 5 個 lane 的 `key_factors`/`risk_flags`、
  Red Team 論述、`watch_conditions` 是質性內容，script 能組裝不能發明。要再往前推得讓 lane
  交出結構化輸出（C2 factpack per-lane views 方向）。**下一次真跑 invest 才會知道模型能不能
  一次把質性檔寫對**——目前只驗過我手工填的版本。

## ✅ Done (v4.124.0) — web-search 額度 shadow ledger（T2 第三項，走第三條路）

- [x] `investment/scripts/websearch_shadow.py`：從 **run log**（非 PM 自陳）讀每個 lane 的實際 web call 數 → `invest_logs/websearch_shadow.jsonl`。Claude 的 `parent_tool_use_id` 讓歸屬精確到 lane；codex 的 JSONL 沒有 web 工具事件型別，一律 `observable: false` 而非 `web_calls: 0`。探索層，validator 不讀、不進決策。
- [x] 測試 4 個種回 bug 全紅；最重要的案例走**真實 log**（2026-04-18 MSFT）而非合成 fixture。
- [x] **回填 203 支歷史 log，不必等 20 場就有答案**：超額率 2026-04 **66%**（55/83）→ 05 月起 **0%**，連續 100 場、三個多月合規，而這條規則從來沒有任何機制在執行。lane 分布：Sentiment 52 / News 35 / Fundamentals 6 / Technical 與 Valuation 幾乎零。

## ⏸ 待拍板 (v4.124.0) — web-search 額度規則的處置

- [ ] **建議從「刪宣稱」改為「三者皆不做」**：(a) 補產生器＝為一個近 100 場沒發生過的情況建跨 session 計數器；(b) 刪宣稱有風險，因為不知道現在的合規靠什麼維持，prompt 那段文字是候選之一。**保留文字、讓 shadow ledger 繼續看**，違規率回升就會被看到。**不宣稱因果**：v4_8 與 v5.0 都有「≤ 1 次」額度（不是拿新規則量舊行為），但 V5.0 上線同日改了很多東西，ledger 說不出是哪一項。

## 🔍 新發現 (v4.124.0，尚未動工) — `phase2_fanout_mode` 是 100% 自陳，run log 是沒人讀的證據源

- [ ] 掃 203 支 log 時的順帶觀察：**codex 的 run 全部 `threads=1`、`receiver_thread_ids` 恆空、collab 工具只有 `wait`**；同一份 protocol 下 Claude 的 log 清楚顯示 `Agent × 6`（5 lane + Red Team）。兩者 export 都宣稱 `PARALLEL_SUBAGENT`。**這同時相容於「codex 沒開子代理」與「codex 開了但 CLI 不上報」，log 分辨不出來**，所以沒有寫成任何斷言。
- 但可以確定的是：**fan-out mode 與 isolation contract 目前沒有任何證據支撐**，而 `websearch_shadow.py` 已證明 run log 讀得出 `Agent` spawn 數。下一步的低成本作法是把 spawn 數也記進同一份 shadow ledger（同樣不扣分），先看資料再談要不要驗。
- 若要分辨 codex 那個歧義，唯一方法是實跑一次並直接觀察（或查 codex CLI 的 JSON 輸出是否上報 sub-thread），不能靠既有 log 推。

## ✅ Done (v4.125.0) — 共通 subagent 模板對 C1 契約核一次（T2 收尾，零行為變更）

- [x] `signal` 補記為 §16 的輸入（PM 必須填進 `conflict_bias.lane_signals`）；模板過去只把它當敘述欄。
- [x] `score` −5..+5 註明只適用四個 LLM lane；valuation verbatim 抄 `valuation_pack.score`。歷史唯一超界的 −4.0（2026-06-14 RGTI）查明是 pack 成為必填前的自由填寫，現已不可能重現。
- [x] Fan-In 表的 `subagent_execution_failed`（零產生器、零消費端、189 筆 export 零出現）改指向真實被驗的 `degraded_analysts`。`skill_execution_failed` 是真欄位，不合併。
- [x] 新增負向規範：subagent 不得產 lane_contract 的四個 post-processor 欄位。

## ✅ Done (v4.122.0) — Phase 2.5 `conflict_bias` 進 export + validator §16 重算

> 全貌與其餘 6 項待辦（含未動工的 T2–T5）見 `docs/plan_invest_stale_stages.md`。

- [x] `conflict_bias` export block（schema doc 新章節 + protocol §PHASE 2.5 輸出規格）；日期閘 `export_date >= 2026-08-10`，舊 entry 不回填。
- [x] validator **§16**：依 export 自己的欄位重算 T1–T5 應觸發集合，與 `triggers_fired` 比對，少報／多報 rc=1；缺輸入回 `None`（不猜 False）並留 warning。
- [x] 新自陳欄位補錨：signal 不得與同 lane score 反向、`lane_signals.valuation` == `valuation_lane.signal`；`OVERRIDE_BURRY` ⟺ `burry_override_active` **雙向鎖**（那個布林餵 ×0.5，鏈尾受 §14 重算）；`proceed_to_phase3=false` ⟹ `final_action=CANCEL`。
- [x] 測試兩層（字面輸入重算契約 + 真 validator subprocess 接線），**8 個種回 bug 全紅**；cutoff 寫死不讀被測常數。
- [x] 修 schema doc FULL EXAMPLE：五 lane 全正卻 `devils_advocate_filed: false`。
- [ ] **待累積 ≥20 場**再做 Phase 2.5 版的 V4.70 audit（各 trigger fire 率、T4 裁決熵、T5 與 30d outcome 相關性），報表按 provider 分欄。

## ⏸ 待拍板 (v4.122.0 挖出) — 兩條「有文件、無產生器」的 Phase 2.5 規則

- [ ] **T7a — T5 的「valuation −3 → 自動 downgrade」**：`decision_engine.py` 全檔沒有 T5 邏輯，§13 band 可達集合也沒有 T5 路徑。實據 2026-08-09 NOW（−3、STAGED_ENTRY、無 BIPOLAR/cap/probe、rc=0）；歷史 −3 收在 BUY 側 4 筆。**與 V4.112 B2 的 ×0.7/×1.15 同形狀**。選項：(a) 照 B2 先例刪降階宣稱、降為 reasoning-only（**傾向**：valuation 已以 0.15 權重壓過分數，再硬降是同訊號扣兩次）；(b) 補產生器並在 §13 開路徑（還要決定與 Rec 11 熱區鬆綁衝突時誰優先）。**前置：等 T1 的 ≥20 場樣本**。
- [ ] **T7b — Anti-Bias 的「5 lane 同向」沒有定義**（score 正負 vs signal 全等）。§16 本版採 score 正負一致且**只出 warning**——把沒定義過的話變成 rc=1 是單方面收緊。選項：(a) score 同號升 error、(b) signal 全等升 error、(c) 維持 warning。前置同上。

## ✅ Done (v4.122.1) — LLM 額度卡 live dot

- [x] provider row 拿掉 route 候選 chip（完整清單留在 hover card），同位置改放 protocol run 的脈動綠點 + hover `invest · META · 5m 22s`。
- [x] 掛在 proto pill 既有 5 秒輪詢上（`UI._llmActiveRun` / `_paintLlmActive()`），不新增輪詢；quota render 後補畫避免燈熄一拍。
- [x] node + vm 跑真實 `_initLlmPanel()` + `pollProtoPill()` 驗三態（codex run / 無 run / model=null 不猜）；殘留掃描確認無 tag class 與 `tagsFor` 殘留。
- [ ] **燈的涵蓋範圍只到 protocol run**：Break News daemon、Nexus gap-fill、intraday narration 不經 `/api/protocol-queue`，燈不會亮。要涵蓋得先有 in-flight registry（broker 只報 quota 不報 lease）。目前語意已在 tooltip/註解/CHANGELOG 三處寫明，不是靜默漏報。

## ✅ Done (v4.121.4) — visible invest→invest cooldown

- [x] worker 改 peek + deadline 重評，等待期間項目留在佇列；`get_queue_state()` 匯出 `cooldown`；pill 顯示 `⏸ 冷卻中 · m:ss`。
- [x] 去重漏洞一併關上：cooldown 中的項目仍在 queue → 重排同一 ticker 被 `duplicate_pending` 擋。
- [x] `tests/test_protocol_cooldown.py` 走真實 worker loop，mutation 驗過會紅（gap 2.0s / 倒數未發布 / 去重未擋）。
- [x] ~~`/api/run-protocol/status` 回傳非法 JSON~~ —— **誤報，已撤銷**。是診斷用的 `curl -m 3` 在高負載下截斷 24 KB 回應，不是 server。`_json()` 的序列化與 Content-Length 都正確，前端無 timeout 不受影響。
- [x] ~~**「comps rc=1」該硬停還是降級**~~ → **V4.126.0 定案**：改成**不是 rc=1**。同業不足是完整且正確的答案（`comps_implied_value: null` + `fewer_than_3_business_similar_peers`），不是執行失敗，script 改回 rc=0；V4.116.1 閘門紀律不放寬（rc≠0 仍只代表工具失敗）。protocol 估值錨表補明文。四個同日樣本：NVDA 08:36 停 / 08:43 續 / META 09:03 停 / 09:14 續。
- [ ] **peer cohort 篩選是不是把超大型股的同業全排除了**（上一條拆出來的另一半，仍未查）：NVDA 回 0 peers、META 只回 GOOGL 1 家。rc 的歧義已解，但「為什麼只剩 1 家」還沒查。可能是對的（真的沒有可比公司），也可能是 `select_valuation_peers` 的 exact-industry 篩選對 mega-cap 過嚴。
- [ ] **`dcf.py:918` 有同型的 exit code 缺陷**（V4.126.0 §2b 殘留掃描抓到，本輪**刻意未動**）：同樣是 `sys.exit(0 if not payload["degraded"] else 1)`，同樣是 protocol 必跑的估值錨 script。**沒有跟著 comps 一起改的理由**：dcf 的 `degraded` 是 `fv is None`（`dcf.py:858`），語意比 comps 的「明確的 eligibility reason」模糊得多——`fv is None` 可能是「算不出來」也可能是「輸入缺失」，兩者該不該停不一樣。目前沒有證據它正在觸發（2026-08-10 META 的 dcf 成功回 $317.38）。要處理得先分類 `fv is None` 的成因。

## ✅ Done (v4.121.3) — proto pill engine attribution

- [x] 跨頁浮動 pill 收合行顯示 broker 選派的 provider、展開行顯示 `engine · provider (tier)`；`model` 未回來時顯示「選派中 / assigning」。
- [x] provider 字形／名稱集中到 `UI.MODEL_META` + `modelMeta/modelBadge/modelText`；`analyze-queue.js` 的重複表刪除改呼叫共用 helper（舊快取 JS 用 optional call 退化成不顯示）。
- [x] node + vm 載入真實 `utils.js` 跑 `pollProtoPill()`，對 live 8080 payload 與三組邊界輸入驗四種輸出皆不同；殘留掃描確認 repo 已無第二份 provider 表。
- [x] pill 視覺驗證：使用者實機截圖 `invest · META · running · 5m 22s · 🟢 Codex` 單行不換行，寬度 OK。
- [ ] 仍未目視：detail 面板展開後（多了 engine 列）與盤前 chain pill 的 `bottom: 92px` 疊放——要等兩者同時出現才驗得到。

## ✅ Done (v4.121.2) — Break News materiality gate + quiet-pool fallback

- [x] 一般 RSS gate 改用 materiality、effective credibility、genre 與精確 binary event。
- [x] fresh-first；空輪有 hourly slot 時從六小時池補最高品質一則，禁止 stale burst。
- [x] `run_once()` 入口測試鎖 materiality、listicle、pool quality/rank、fresh precedence 與 hourly cap；mutation test 證明拆掉補位接線會紅，真 RSS dry-run 通過且 0 LLM。
- [x] Dashboard server 已重啟；首輪 live poll 建立一則 `pool_materiality` pending item，後續由既有 10 分鐘 debate loop 處理。

## ✅ Done (v4.121.1) — Claude text-only timeout hardening

- [x] `nexus_gap_fill` 固定 Sonnet、單 turn、no tools、strict MCP，仍走 broker。
- [x] hard deadline 360s、JSON output budget ≤1,500 tokens、單 provider 不 fallback。
- [x] role profile kwargs + governed chain 接線測試；本版不花模型額度。
- [ ] 若要 live smoke test，選 `data_center_infrastructure`；這會消耗該 topic 唯一 inference turn，需使用者另行執行。

## ✅ Done (v4.121.0) — Source-ID evidence packet

- [x] canonical source ID、excerpt ID/hash、claim extract 與 fetched page provenance 分流。
- [x] 關係級 evidence tier；source cap 後重算；validator 鎖 source/excerpt ownership 與 aggregate quality counts。
- [x] gap-fill closed packet：禁止新增 URL，每項需 fetched-page excerpt，draft + packet 雙 digest。
- [x] `data_center_infrastructure` 真實抓頁：7/16 fetched、19 excerpts；Radar 顯示品質數據。
- [ ] 下一次模型試跑前先確認目標 packet 有至少 2 個可用 fetched domains；仍不得重跑 NAND。
- [ ] Valid proposal 出現後才設計 human-review → curated YAML promotion；目前 proposal 數為 0。

## ✅ Done (v4.120.0) — Bounded gap-fill runner

- [x] 單 topic / 單 inference / 無 fallback；base digest、原子 ledger、一次性 spend gate。
- [x] Proposal caps、逐項 URL、跨 domain、不可覆寫 base、不可進 decision validators。
- [x] Radar 顯示 proposed / failed / blocked 與 turn/provider 稽核資訊。
- [x] `topic:nand` 真實一 turn 試跑：Claude 240s timeout，正確記 failed 並停止，未重試。
- [x] 下一步已於 v4.121.0 改為 closed source packet；NAND 維持不得重跑。
- [x] promotion 前置移至 v4.121.0 backlog；目前 proposal 數仍為 0。

## ✅ Done (v4.119.0) — 高分候選 evidence-only 草稿

- [x] 最高分 12 個 uncovered topics 自動轉為 upstream / intermediate / downstream / unresolved 草稿，零 LLM。
- [x] claim artifact intersection、evidence-level、known gaps、decision isolation 與 validator。
- [x] Tier 1 自動重建；Radar draft-ready 排序、metric、badge 與 detail layer view。
- [x] **下一步**：bounded gap-fill runner 與一次性 ledger 已於 v4.120.0 完成；首輪 timeout 透明保留，不重試。
- [ ] topic alias / merge / split 與 syndicated-source family 偵測，避免相近名稱重複占 queue。

## ✅ Done (v4.118.1) — Nexus 淺色主題

- [x] 圖譜畫布、控制面板、Radar 卡片與 metrics 跟隨全站 light/dark theme。
- [x] Canvas 節點、連線、標籤及 tooltip 使用各自的淺色／深色 palette，theme 切換即時重繪。
- [ ] **待 user 實看**：淺色模式的卡片密度與 ego graph 對比；目前 browser runtime 無可用 instance。

## ✅ Done (v4.118.0) — Nexus 證據型供應鏈雷達第一輪

- [x] Claim ledger：URL/domain 去重、canonical triple、promotion gate、direction-conflict audit、quality JSON、validator。
- [x] 正式 direct relations 接回每日 Tier 1；移除 regex ticker 共現→`PEER_OF` 污染。
- [x] 零 LLM topic discovery：state/score/why-now、chain candidate、existing-chain coverage gap。
- [x] Knowledge Graph 預設 Radar + topic ego focus + relation evidence link；供應鏈 quick-pick 接 proactive queue。
- [x] 44 tests、JS syntax、真 build、兩支 validator、三個真 server endpoint 全綠。
- [ ] **待 user 實看**：`/graph.html` Radar 卡片密度、topic 點入後 ego graph 可讀性、右側 evidence link。
- [x] **下一波第一步**：validated candidate 自動生成 evidence-only layered draft（v4.119.0）。後續 bounded gap-fill 與 alias/syndication 見上方新區塊。

## ✅ Done (v4.117.0) — 三道閘：export 從「模型打字出來的」變成「工具產出的」

- [x] **`export_provenance`**：`append_session_export.py` 蓋涵蓋決策內容的 sha256；`export_date >= 2026-08-09` 缺 stamp 或 digest 不符 → rc=1。digest 排除 `det_shadow` / `lane_contract` / `thesis_id` / `thesis_registered_at` / `_` 開頭鍵，核可鏈用**真的 `apply_det_shadow.py`** 跑 round-trip 鎖住。
- [x] **`news_lane.pt_revision_momentum` 必填**（同日期閘）。`UNKNOWN` 要帶 `unavailable_reason`；`UP`/`DOWN` 要帶數值 `delta_1m`；把 `news_lane` 設 null 也繞不過（lane 有評分就代表跑過）。
- [x] **`calculation_steps` 對 engine artifact**：`decision_engine.py --phase 3` 落地到 `invest_logs/decision_engine/<T>_decision_engine.json`，validator §5l 逐欄遞迴比對（浮點容差 1e-6），artifact 缺席/過期/ticker 不符則靜默。
- [x] `test_validate_session_export_gates.py` 擴充：含**接線斷言**（把 check 從 `main()` 拆掉要會紅）。十個種回的 bug 全部驗過會紅。
- [x] 殘留掃描抓到 artifact 路徑重複定義 → 改成從 `decision_engine` import（原本改一邊會讓閘永久靜音而非報錯）。

- [x] **agy 的 invest 紀律軸結案（2026-08-09 閘後同日 BAC 三跑實測）**：agy 手寫 history.json 從 7+6 次 → **0**，`--replace-last` 用了 2 次，`pt_revision_momentum` 填真數字 `-2.94` 沒走 `UNKNOWN`；codex 一次過 0 輪 drift。兩家 Gate 1/2/3 全過。
- [x] **Technical rubric 閘證明有決策價值**：agy 閘後與 codex 在同一 hint 下都給 1.5，證明閘前那個 2.5 是異常值；實跑 decision_engine 確認單那 1.0 分把 STAGED_ENTRY 翻成 BUY（1.2822 vs 門檻 1.2）。
- [ ] **agy／codex 的穩定度軸未結案 —— 這是升正式候選唯一還缺的**。現況：agy 在 BAC 兩次 News 差 1.3、NOW 兩次差 1.5；agy vs codex 在 BAC 決策直接分歧（進場 4.25% vs HOLD 0%）。但 codex n=1，跨引擎分歧不等於某一家不穩。
  **測試設計**：挑 **2 支 final_score 遠離 0.8/1.2 門檻**的股票（BAC 的 0.78–1.11 正好壓在邊界上，會放大雜訊），每家每支連跑 3 次 = 12 runs。同日跑可讓 phase0/technical 快取複用，輸入才真的固定。判準：decision 是否 3/3 一致 + lane score 全距。
  **成本**：agy ~4-5 min／run、codex ~12 min／run → 純執行約 1.7 小時。
- [ ] **News lane 是唯一「script 算得出計分成分、卻沒有任何東西接住」的 lane —— 這是 News 全距最寬的結構性原因**（2026-08-09 BAC 三跑診斷）。
  **證據（不是輸入變了）**：三次引用同一組事實（USAA 和解、近新高、PT −2.94%），agy 兩次 reasoning 幾乎逐字相同（"despite modest analyst PT trim" / "despite minor 1M PT trims"）卻差 1.3 分。實跑 `fetch.py BAC`：`analyst_consensus.consensus = "Buy"` → protocol §News 表給 **+1**；`pt_revision_momentum = DOWN −2.94%` → **沒破 −3% 門檻 → 0**。所以 rubric 導得出的基準是 **+1**，三次分別是 +0.2 / **+1.5** / +0.5 的自由心證加權。**同一則 USAA 和解，一次值 0.2 分、一次值 1.5 分。**
  **錨盤點**：Valuation 有硬閘（lane 必須等於 pack）、Technical 有 `rubric_hint` 硬閘（V4.116.3）、Sentiment 有 `sentiment_det` shadow + 明訂翻預設判準、**News 的兩個計分成分只活在 stdout，`fetch.py` 連 `rubric_hint` 欄位都沒有**。這正是 Technical 在 V4.116.3 之前的狀態。
  **三跑全距**：fundamentals 0.50 / sentiment 0.67 / technical 1.00（那個 2.5 已被閘攔）/ **news 1.30**。⚠️ 但**不能推出「有錨就窄」**——Fundamentals 沒有 `rubric_hint` 卻最窄，因為它的輸入本來就是硬數字。準確的說法是：**News 天生詮釋空間最大，而它偏偏是唯一連可導出的那部分都沒被接住的**。n=3，是觀察不是證明。
  **修法（V4.116.3 的翻版）**：`fetch.py` 落地 payload → 從 `analyst_consensus` + `pt_revision_momentum` 導出 `rubric_hint` → validator 對帶外未宣告的紅。
  **未決：帶寬**。Technical 的帶由 stage 結構決定、很緊；News 的自由心證**是合理的**（USAA 和解確實該加分），帶要寬到容納真新聞、窄到擋住「同一則新聞這次 1.5 下次 0.2」。初步建議 `base ±1`（BAC 例：base +1 → 帶 [0,2]，agy 1.2 與 codex 1.5 在帶內、2.5 要寫理由），但**這是會影響決策的參數，不應由 agent 自定**。
  **相依**：先跑 MU/AAOI 那 12 次拿到各 lane 的 σ，**帶寬用量出來的數字定，不要用挑的**。
  另：同一個 lane 的 `decision_point_days` 三跑是 21 / **66** / 21，同樣的鬆散，同一道閘可以一起處理。

- [ ] **`valuation_reviewer_gate` 的 `triggers_fired` 沒對照 `triggers` 表**：agy 15:03 那筆寫 `triggers_fired: []` 但 `triggers.no_peer_cohort: true`，且缺 `shadow_only`（validator 只 warning）。同一次 run 的 11:48 版本反而是對的。跑了 script 但抄錯 —— 若 `valuation_reviewer_gate.py` 有落地輸出，可用同 Gate 3 的 artifact 比對法補第四道閘。
- [ ] **`audit_gate_compliance.py` 的 log 形狀支援**：目前認得 gemini（`step_update.tool_info.parameters.CommandLine`）與 codex（`item.command`）兩種；claude 的 log 形狀未驗，會落到「掃全文 + 印警告」的退路。
- [ ] **`replay_decision_engine.py` 對 NOW EXPERIMENT 報 mismatch**：stored 1.0855 vs replay 0.977，stored final_score 用它自己的輸入重算不出來。該筆已隔離、不進決策日曆，待 triage。
- [ ] **`decision_point_days` 無閘**：同檔同日 agy 兩次給 21 / 80。它決定 watch_conditions 的 review trigger，但沒有可比對的 script 產出物，補閘需要先有 deterministic 來源。

## ✅ Done (v4.116.1) — 閘硬化 + 前導閘門紀律 + runner 硬化，兩個引擎實測驗證

- [x] script 閘從「檔案存在」升級成「內容可信」（`echo '{}'` 可繞過，七種形狀逐一驗證）+ 新增 `anchor_dropped_script_value`。
- [x] `_adapt_protocol_prompt` 第五句閘門紀律：rc≠0 停下回報，禁止改輸入迎合檢查。
- [x] `investment/scripts/run_protocol_manual.py`：provider+protocol+ticker 參數化、原子鎖、每次獨立 log/backup/job_id、失敗隔離報告。取代 gitignored 的一次性腳本。
- [x] `reports/20260809_NOW.md` → `_EXPERIMENT.md`（第一次那份），退出決策日曆。
- [x] **實測**：codex/PLTR rc=0 11m 全綠；agy/NOW rc=0 4m，四道閘全部生效（script 有跑、權重不再坍縮、phase0 真重跑、shell 汙染 0、position_size 3.53%）。

- [x] **`PROTOCOL_VALIDATORS` 補上 `invest`**（v4.116.2）+ `PROTOCOL_REQUIRED_ARTIFACTS` 補 invest 報告（validator 讀最後一筆，run 沒寫入會驗到上一個 session）。測試對照 CLAUDE.md 記載的三道 gate 逐一斷言已註冊。
- [x] ~~**`valuation_reviewer_gate.py` 無閘可管**~~ → v4.116.3 解決：改驗 export 欄位（`export_date >= 2026-08-09` 缺 block → rc=1）。閘後 agy/BAC 確實跑了。
- [x] **稽核推算 $121.85 已被推翻**（結論，非待辦）：第二次兩支 script 都跑了，`extreme_overvalued` 沒變且更空（$64.37 / −48.45%）。NOW 的估值判定不是「跳過 script 造成的假象」。

## ✅ Done (v4.116.0) — 三道「說綠但沒驗到」的閘（稽核 agy 首次 invest 挖出，非引擎特有）

- [x] `validate_phase0.py` 新鮮度閘：`scan_date` 過舊/未來 → rc=1；**內容與較舊快照除 `scan_date` 外相同 → rc=1**。週末邊界刻意處理（雙胞胎須比窗口更舊才算證據）。新增 `test_validate_phase0.py`。
- [x] `script_not_run` 判別（`mark_unrun_anchor_scripts`）+ `validate_session_export.py` rc=1 閘。只在 anchor 無值時觸發、artifact 新鮮則維持原 reason、上游 reason 不覆蓋、`forecaster_blend` 不納入。
- [x] 報告揭露 `outlier_diagnostics`（含有效權重），advisory 不改數字。
- [x] `position_size` 單位修正：`fmt_position_size()`，`0.035325%` → `3.53%`。兩支 renderer 共用。
- [x] 更正稽核誤判：`suppression_proposals` 不渲染**不是 bug**（protocol `:568` advisory/audit-only，V4.88.0 刻意設計）。
- [x] 全部新斷言種回 bug 驗過會紅；13 支測試 rc=0。

- [ ] **既有已發布報告未回填 `position_size`**（使用者決定保留）。`inject_report_facts.py` 本來就有重刷用途，要批次修正隨時可以。
- [x] ~~**Technical lane 的 `rubric_hint` 沒有被帶進 `phase_inputs`**~~ → v4.116.3 解決，但**走的是另一條路**：不動 lane 資料契約，改讓 `analyze.py` 把 payload 落地到 `skills/technical-analyst/cache/<T>_technical_payload.json`，validator 直接讀 script 自己的輸出。**「讓 producer 留下物證」比「擴充 lane 契約」便宜得多**，v4.117.0 的 `calculation_steps` parity 沿用同一招。
- [ ] **shell quoting 汙染無閘可擋**：雙引號 `python3 -c "…"` 讓 zsh 吃掉 `$652M`，產出的是語法合法的 JSON、內容才錯。已在 agy 檢討文件列為紀律項；要自動偵測只能靠啟發式（`(M in`、` .45B` 簽名），會有偽陽性。

## ✅ Done (v4.115.0) — LLM 額度面板改版 + agy 5 分鐘天花板

- [x] bar 語意全面翻成「已用」（側邊欄常駐列 + hover card），hard reserve 在消費軸換算成 80%，齒輪說明文字同步改。
- [x] hover card：標題列 `名稱 · 方案chip · 新鮮度` 一行（砍掉 `observed` 那行），每個窗口各一條 bar。
- [x] 重置時間粗略單一單位（`4d` / `19h`），claude 的絕對字串 `Aug13at12pm(Asia/Taipei)` 解析成相對天數，失敗退回原字串。
- [x] `broker_gate` bucket 補帶 `used_percent` + `label`；**null 維持 null**，UI 對推算值標虛線底線。
- [x] claude 方案名改讀 `~/.claude.json`（`MAX 5×`），取代原訂的 12.5 秒 `lqb probe` + 背景執行緒方案。
- [x] `tests/test_broker_gate.py` 新增 window 欄位契約，種回 bug 驗過會紅。
- [x] **v4.114.1**：`_protocol_command` 補 `--print-timeout`，解掉 agy 所有長 protocol 被 5 分鐘靜默腰斬的問題。

- [ ] **gemini 的方案名仍是空的**：broker 對 agy 的 `snapshot.plan` 時有時無（CLI `lqb status` 拿得到 `Google AI Pro`、`/v1/providers` 端是 null），`~/.gemini/` 底下也沒有。目前沒有 chip。要補的話得先搞清楚 broker 為什麼兩條路徑不一致。
- [ ] **面板尚未在真實瀏覽器看過**：dashboard_server 需重啟才會載到新的 Python（靜態檔是每次請求重讀，JS/CSS 不用重啟）。helper 已用真實 payload 在 node 上跑過、輸出與設計稿一致，但版面密度（四家並排、每家 2-4 條 bar）只有實際開起來才知道。

## ✅ Done (v4.114.0) — 各家 CLI 只讀自己的 context 檔 + protocol provider 白名單 + 執行引擎署名

- [x] 診斷 `invest_20260809_000447` rc=1（208K token 零產出）：broker 首次把 invest 派給 gemini × 裸觸發詞 prompt × `agy --print` 不載入任何專案 context 檔，三層疊加。
- [x] **A**：`_adapt_protocol_prompt` 從 codex 專用擴成全部非 claude provider，前導帶自己的 context 檔（`PROVIDER_CONTEXT_FILE`）+ 本次 protocol 規範路徑（`PROTOCOL_DOC`，11 支全覆蓋）+ 工具詞彙對照 + cwd 邊界。
- [x] **各家 .md 自足**：`scripts/sync_agent_context.py` 從 CLAUDE.md 生成 `GEMINI.md` / `AGENTS.md` 的 generated 區塊（`--check` 進收尾 checklist）；CLAUDE.md 的「只引用不複製」改為「唯一手寫來源 + 生成」。
- [x] **B**：`config/llm_config.json` 的 `protocol_providers`（invest/sector 限 claude+codex）；白名單落到 `forbidden_providers`（只放 preferred 不生效）+ 選型前也套一次（蓋 broker-off 與 grok 兩條 early-return）+ 空/壞掉 fail closed。
- [x] **執行引擎署名**：env `AIC_PROTOCOL_MODEL/_TIER/_NAME/_JOB_ID` → 報告 H1 下一行 + `/api/analyze-queue` 的 `model`/`model_tier` → Dashboard 分析中與最近各一顆 provider badge。
- [x] 驗收：codex/grok 探針從 `UNKNOWN` → 正確答出 `investment/investment_protocol_v5_0.md`；四支回歸測試 + `sync_agent_context --check` 全 rc=0；新斷言均種回 bug 驗過會紅。

- [x] **gemini 端路由驗證**（2026-08-09 使用者手動執行，agy headless 需 `--dangerously-skip-permissions`）：前導 → Read `GEMINI.md` → 正確答出 `investment/investment_protocol_v5_0.md`。**四家 provider 的路由現在全部從自己那一個 context 檔就能完成。**

- [ ] **gemini 跑 invest 的執行能力（仍未驗，這是加白名單的唯一剩餘條件）**：路由通了不等於跑得動。invest 要 5 lane 平行 subagent + Red Team，agy 的 `define_subagent` / `invoke_subagent` 撐不撐得住完全沒測過。驗法只有真跑一次（30-45 分鐘、量級 200K+ token），而且要挑一檔不重要的標的、跑完比對 `investment/scripts/validate_session_export.py` rc=0 + 報告六個決策區塊齊全。**沒過就別加進 `protocol_providers.invest`** —— 現況（claude+codex）是安全的預設，不動也不會壞。
- [ ] **codex CLI 每次啟動噴 `failed to install system skills: Permission denied (os error 13)`**（2026-08-09 探針時發現，與本次故障無關）：`codex_skills_extension` 想刪既有 system skills 目錄但沒權限。目前不影響 protocol 執行，但它是個持續的壞狀態。

## ✅ Done (v4.111.6) — 上游對齊批:v3 legacy 清理 + 兩個偵測器 FMP 路徑修復

- [x] 比對 fork 源頭 tradermonty/claude-trading-skills(現 71 skills,MIT)4 月後 delta;評估:5 個值得引入,其餘重複或超綱。
- [x] ftd/market-top `fmp_client.py`:historical 遷 `stable/historical-price-eod/full` + flat-list normalizer + timeseries 截斷 + `from` 縮 payload(上游 c54959e/20a9a1);死的 v3 鏈與 `BASE_URL` 移除(原鏈 stable 404 → v3 403 兩條全死)。實測 ^GSPC 80 bars + quote。
- [x] theme-detector:`representative_stock_selector` 移除死 FMP etf-holder 層(v3 403;stable 替代 402 不在訂閱);`etf_scanner` 移除 v3 quote fallback。
- [x] `intraday.py` 移除死 v3 fallback(實測 stable 90 bars);econ-calendar SKILL.md v3 URL → stable。
- [x] 10 個 SKILL.md 回填 upstream alignment blockquote;MARKET_INDEX 維護規則加上游對齊條目。

- [ ] **theme-detector 上游方法論回灌**(設計題,獨立 session):Heat v2 stock-leadership evidence(5D+20% / EP9M / range expansion / 新高 / high-RS)+ `--history-file` heat 歷史與加速度(1D/5D delta、20D z-score、What Changed Today)。上游 92baba0 / ad75b2c。
- [ ] **fmp_pool endpoint circuit breaker**(可選):連續失敗端點自動停打,防「壞兩個月沒人發現」再犯(上游 561df13 概念,加在 fmp_pool 一處)。
- [x] **stale test 修復批**(v4.113.2 完成):theme-detector 460 / ftd 65 / market-top 210 全綠(原 29+11+12=52 紅)。三種不同根因——(a) mock 打在 fmp_pool 重構後已無人使用的 `session.get`,每個測試靜默打真網路(12-13 秒 → 0.10 秒);(b) 斷言 V4.111.6 已刪除的 v3 fallback;(c) V2.19.2 換掉全部四個 heat 公式而測試沒跟上。**順帶挖出共用 `rsi_14` 的真 bug**(無損失回 NaN 而非 100 → 最極端超買變成 `zone=unknown`),已修並補 14 個測試。
- [x] **風控三支改版 Batch A**(v4.111.7 完成):burry 價格失敗誤觸 T4_VETO、rm sector 分母膨脹兩個真 bug + top-level try/except + 死參數清理 + 三份文件詐欺/漂移修正 + 106 個測試(零網路,兩個 bug 皆種回確認紅)。基線 diff 僅刻意移除的 `portfolio_size_usd` 一處差異;replay 三 cohort current-rule mismatched 皆 0。
- [x] **風控三支改版 Batch B 第一波**(v4.112.0,使用者逐項拍板後執行):B2 刪 ×0.7/×1.15 文件宣稱、B3 sector enum 收斂為 3 值 + 刪 `EXTREMELY_FRAGILE` 死規則 + 移除 `fragility_downgrade`、B7 兩個 off-band 門檻對齊 60(`<40`→`<60`、`>70`→`≥60`)+ `downside_deviation` NaN 修復、B1 天花板參數化 `--max-cap`(預設不變)。另修 `investment/README.md` 相關性表(review 新發現,原盤點漏掉,含不存在的 ×1.1)。決策備忘 `docs/plan_risk_trio_B.md`。
- [x] **B4 — 風控三支遷 technical_core**(v4.113.3 完成):零翻轉閘門過真實 code path(16 檔 0 翻轉,|Δscore| 最大 0.400)。**⚠ 餘裕不大**:最接近帶邊的樣本距 0.60 分,落在帶邊 0.4 分內的標的會翻。
- [x] **引入 dual-axis-skill-reviewer**(v4.113.4):上游 `b814274` vendored 進 `skills/`,報告落 `reports/skill_reviews/`。三支風控 final 75 / 73 / 71。**讀 breakdown 不要只看總分**——auto 軸的三個子項量的是上游 SKILL.md 章節模板符合度,與本 repo 風格不同故三支同扣。
- [ ] **dual-axis LLM 軸點出、尚未處理的項目**(v4.113.4 評估產出,詳見 `reports/skill_reviews/llm_review_*.json`):
  - rm:vol-scaling 失能未解(參數化 ≠ 修好);sector 檢查任一失敗即全盤停用過於粗糙(應只在未定價權重會改變判定時才停用);`load_positions` 對畸形 entry 靜默補 0 不進 warnings
  - burry:insider string-sniffing 可能**誤判**而非只是失敗(含 'Sale' 字樣的無關欄位會投 SELL);`burry_voice`/`veto_flag` 分工只有散文約束,validator 未驗;FCF 的 OpCF×0.85 代打未標記來源
  - tail-risk:normalizer 2026-04 校準無漂移偵測;無 `band_margin` 欄位讓消費者分辨「穩的 MODERATE」與「離 FRAGILE 0.2 分的 MODERATE」;無 cache

- [ ] **`auto_adjust` 慣例盤點(標註,非統一)**(v4.113.1 立項,排在 B4 之後):repo 內至少三套並存——`auto_adjust=True`(technical_core / tail_risk / burry / risk_manager / sector `*_yfinance` / journal / sentiment / mood / fred-macro / weekly-tech-playbook)、`auto_adjust=False`(short-term-target `predict.py` + `weekly_review.py` / thematic-screener / build_event_index / backtest_postmortem)。**問題從來不是慣例不同,是慣例隱形。** 產出物:每個取價位點一列(位置 / 慣例 / deliberate 或 accidental / 一行理由)。已知先例直接填:`predict.py` = deliberate(`weights.yaml` 在該基準校準)、`build_event_index` 很可能 deliberate(事件價應對得上當日報價)。**標不出理由的就是下一個候選修正。** 順帶立規範:新取價 code 必須明示 adjust 慣例。**不預設任何統一動作**——盤點完每個 accidental 個案逐項拍板。

- [ ] **風控三支 Batch B 餘三項——備忘結論為「維持現狀」,重啟需先解決前置條件**(證據見 `docs/plan_risk_trio_B.md`):
  - **B4 遷 technical_core**:~~前置為除息調整~~ **前置已解除(2026-08-08 下午)**。`/stable/historical-price-eod/dividend-adjusted` 在現行方案可用且回 `adjClose`;用它重跑同批 16 檔 shadow **翻轉 1 → 0**、bar 數 250/254 → 250/250,配息股 dd 漂移 +1.14 → -0.000、TLT 7.74→10.72 變 7.74→7.74。**閘門通過。** 共用模組已於 v4.113.0 修好,**下一步:B4 三支遷 `fetch_history` 並過真實 code path 重跑零翻轉 shadow**(先前的 v2 是直打端點,不算數)。
- [x] **`technical_core` 主源與 fallback 的調整慣例不一致**(v4.113.0 完成):`_fetch_fmp_ohlc` 改打 `historical-price-eod/dividend-adjusted`,端點提為 module 常數 `_FMP_OHLC_ENDPOINT`(不用環境變數);兩路徑同慣例的契約寫進 docstring 並由 16 個新測試斷言(含 fallback 的 `auto_adjust=True`)。Shadow 59 檔:無配息組 7/7 逐位元一致、ma_200 51/51 全部下修、真分類翻轉全部可歸因(消失的 4 筆 cross 皆為「一兩天內來回穿越」的除息假訊號)。影響面 5 個消費者(非先前誤報的 9 個)。範圍表與完整 shadow 見 `docs/plan_technical_core_adjclose.md`。**已知系統性影響:配息股技術面讀數會系統性偏多一點(修正而非 bug,但方向一致)。**
  - **B5 insider 換 fmp_supplementary**:一致率 67%,但 FMP 對 12 檔判 10 檔 `distributing`(8 檔 ratio=0.000),直接映射會讓該元件變常數偏移。**重啟前置**:改用相對基準映射(自身前 4 季中位數或同業中位數)並先出門檻校準 shadow。
  - **B6 drawdown-circuit-breaker**:資料源存在(`positions.json` 有 `realized_pl`/`exit_price`/`exit_date`)。**重啟前置**:帳本目前僅 7 筆、全獲利、全在 2026-04 同一週,連敗與週月虧損門檻無從校準——需先累積含虧損的關倉樣本。上游機制參考 `tradermonty/claude-trading-skills` 的 `drawdown-circuit-breaker`。

## ✅ Done (v4.111.3) — decisions 倒數環的永久重繪迴圈

- [x] `decisions.html:35` transition 拿掉 `stroke-dashoffset`(每 1.0s 續一個 0.9s 的不可合成 transition,頁面永遠不 idle)。Paint 110.3→3.1/s、Commit 55.1→1.1/s、RecalcStyle 2789→53(/50s)。
- [x] `page-decisions.js:2490` 1s 倒數加 `document.hidden` 跳過 + `visibilitychange` 立即補跑(已實測:強制設 STALE 後 dispatch 事件 600ms 內復原)。
- [x] 排除法有量測背書:timer(JS 僅 0.4%–2.8% 一顆核)、記憶體洩漏(3 分鐘元素數固定 13,921)、`dashboard_server.py`(累計 1:10 CPU)、backdrop-filter(全關反而更慢)皆非元凶。

- [ ] **Safari 端未複驗**:全部量測來自 headless Chrome(該頁修前 8.1% / 修後 6.7% 一顆核),使用者回報的是 Safari 燒掉一整顆核。**無法證明這一行 100% 解釋 Safari 那顆核**——請開 decisions 頁觀察是否仍卡;若仍卡需用 Safari Web Inspector Timeline 再查一輪。
- [ ] **`intraday-eval.html` 同類問題未修**:閒置 241 Paint/s(比修前的 decisions 還高),來自 3 張可見的 `.ie-scard.repeat-strong` 在動 `box-shadow`(`style.css:4874-4875`),`box-shadow` 同樣不可合成。改法是換成 `opacity` 動偽元素光環,但**會動到外觀**,需使用者決定。
- [ ] `docs/agent-ops/LESSONS.md` **2026-08-10 實測 221 行**(門檻 150,原記載的 160 已過期),下個 dev session 收尾時精簡。

## ✅ Done (v4.111.2) — sidebar 控制項收進 header 齒輪

- [x] 主題 / 風險容忍 / 語言 / 系統日誌 + 額度說明全部收進 header 齒輪的 popup;footer 只留額度面板與版號。
- [x] 風險容忍由整條寬按鈕縮成 popup 一行 + 小 chip;語言與主題列改顯示當前值而非切換目標。
- [x] popup outside-click / Escape 只綁一次;切主題語言後自動重開(renderSidebar 會銷毀它)。

- [ ] **popup 未做視覺驗證**:結構用 DOM stub 驗過(齒輪在 header、四列齊全、footer 已清空),但實際位置(`right:14px` / `width:214px` 在 256px sidebar 內)與深淺色對比需開頁確認。

## ✅ Done (v4.111.1) — 卡片級距表補齊 + 面板細節改 hover

- [x] `UI.SIGNAL_TIERS`(breadth / market_top / macro)+ `signalTier/signalColor/signalStages`;三張卡改讀它,`colorByScore` 只剩 FTD fallback。
- [x] 頂部風控 31.6 由綠改 🟡 早期警告(與 tooltip、與 `mt.zone` 一致)。
- [x] Macro 卡補上真正的 popup(舊的 `data-tip-key: macro_briefing_tip` 沒有對應 PILL_TIPS 項,靜默無效);顏色改由體制名稱決定。
- [x] LLM 面板常駐區只留長條;窗口明細/新鮮度/逐 provider 花費改 hover card;移除 `辯手：全部 N 家候選` 與 `虛線 = 硬保留` 兩行。

- [ ] **Macro 分級的部位含意文案未經實戰檢驗**:順風/過渡/緊縮/壓力四級的 action 與 detail 是本輪新寫的,分級經使用者核准但文字未逐句校過。實際遇到 Stagflation / Recession Risk 時回頭看措辭是否可操作。
- [ ] **`fg` / `vix` / `cycle` / `regime` 四個 tip 仍各自持有級距表**,目前沒有卡片用通用 helper 幫它們上色(所以沒有牴觸),但同樣的 drift 風險還在。要收就一起收進 `SIGNAL_TIERS`。

## ✅ Done (v4.111.0) — LLM 額度常駐視覺化 + 曝險門檻收斂

- [x] LLM 額度面板移出齒輪常駐在 sidebar footer;齒輪改放說明。每家一條 quota bar + 20% 硬保留線 + per-bucket 明細(5h / 週 / 本節與重置時間)+ 路由 badge。
- [x] `broker_gate.quota_snapshot()` — providers 與 `hard_reserve_percent` 一次取回(原本會打兩次 `/v1/status`);`provider_quota()` 保留為薄封裝。
- [x] 本地用量拆開:呼叫次數上限只在 broker 關閉/連不上時顯示(那時才是真閘門),花費(token / `$`)常駐一行(broker 不報金額,本地帳本是唯一來源)。
- [x] `UI.EXPOSURE_TIERS` 成為曝險門檻唯一來源(75/50/25),五個 consumer 全部改讀;`STAGE_DOTS` 的 `ex_*` 由 tier 表生成。
- [x] 修掉曝險卡吃 `sty.fg`(裁決 stance)著色的 bug,以及圓環「填充用中位數、印上界」的分岔。
- [x] 曝險卡在 xl 斷點放大 `col-span-2` + 72px 圓環 + tier tag,與其他撈數據卡區隔。

- [ ] **面板未做瀏覽器視覺驗證**:本輪 Chrome 擴充未連線,改用 DOM stub 對實際 broker payload 驗證四種狀態與中英雙語。實際版面(sidebar 寬 256px、三家 provider 的高度)需下次開頁時目視確認,特別是 provider 家數增加時 footer 會不會擠壓 nav。
- [ ] **`window_minutes` 只有 codex 有**:bucket 標籤對 `primary` 靠它判斷是週池還日池,其他 provider 全走名稱推斷。若日後有 provider 只給 `primary` 又不給 window,會顯示成「主池」而看不出窗長。

## ✅ Done (v4.109.0) — LLM Quota Broker 接管額度

- [x] `broker_client.py`(vendored)+ `broker_gate.py`(本 repo 的邊界)+ `model_router` 全面改走預約→執行→結算。
- [x] 本地 daily / rolling-window 預算降為降級路徑專用;仍逐筆記錄。
- [x] agentic protocol run 納管(V4.86.0 明確保留給使用者決定的那一項,2026-08-08 已決定)。
- [x] Office `_call_claude_text` 與 link digest 翻譯補上閘門(原本只有事後回報)。
- [x] `tests/test_broker_gate.py` 鎖住失效政策。
- [x] 側邊欄五個 LLM 下拉移除,改唯讀讀出(每 30s;V4.111.0 起改為常駐 + 分頁在背景時暫停輪詢)。

- [x] 辯手 A/B 改由 broker 指派(目前能服務的前兩名);設定檔那對降為 fallback,並依 `AGENTS.md` 改回 claude+gemini。

- [ ] **protocol 的合格名單只有 claude + gemini**。chain 是 primary=claude / secondary=gemini / **tertiary=claude**,去重後 codex 根本沒進名單——即使它有額度也不會被派到 protocol run。要讓 codex 有資格就把 tertiary 改成 codex。(辯論那條沒有這個問題:它問的是全部三家。)
- [ ] **快照過期會讓 broker 拒絕全部派工**。2026-08-08 實測:快照 1.5 小時舊 → 三家全部 `stale_snapshot` → `no_capacity`。這是 freshness 閘門的正確行為,但**操作上看起來像「額度用完」**。~~目前只能手動 `lqb refresh`。broker 的 LaunchAgent 沒有排程刷新~~ → broker 已於 2026-08-08 加入 daemon 內建的 300 秒排程刷新;同日又修好一次「排程有跑但 launchd 的 PATH 找不到 agy、且 claude 解析到四個月前的舊安裝」,見 broker `docs/TODO.md` 缺陷 7。仍保留這條是因為**操作上的誤讀還在**:過期造成的拒絕看起來仍像額度用完(broker 端已改為逐 provider 說明真正原因)。

- [ ] **live smoke test 三條線**:Dashboard protocol、Break News、Office。要真燒額度,須人在場;先用 `lqb status` 確認三家都不在 reserve-only。
- [ ] **重的 protocol 還沒有任何量測值**。V4.110.0 把 `broker.protocol_tokens` 改成逐 protocol,但只有 `triage` 填了實測數字(233,139 in / 28,702 out / 143s,2026-08-08 agy)。`invest`／`sector`／`playbook`／`llm_review` 仍走 `default` 200k/40k——**而那個 default 連 triage 都不夠**,這幾個又是 opus 檔的 30–45 分鐘多路辯論。各跑一次後用 `lqb history --stats --task-type agentic_protocol-invest` 逐一填回（V4.111.4 起分隔符是 `-` 不是 `:`）。改大改小都要有數字支撐。
- [ ] **`grok` 仍在 chain 內但無人治理**:broker 端休眠(Phase 3 延後——weekly 池只能靠登入後網頁 DOM 取得)。要嘛從 `llm_config.json` 的 chain 拿掉,要嘛接受它是唯一不受 20% 硬性保留約束的出口。目前是後者,且只寫在 `broker_gate.PROVIDER_FOR_MODEL` 的註解裡。
- [ ] **daemon 沒起來時只有 stderr 一行**:若實際使用常忘記起 daemon,考慮讓 Break News 狀態面板顯示 `broker.reachable=false` 橫幅(`model_status()` 已經帶這個欄位)。

## ✅ Done (v4.108.0) — 第 9 根 anchor（虧損題材股）+ speculative governor

- [x] `fwd_earnings_discounted`（條件錨，peer-free）：覆蓋 ≥3 家的最遠獲利年度 EPS × justified PE ÷ CAPM 折現；live 資格僅在四根 cashflow_intrinsic 皆非 live 且 TTM EPS 非正時開。AAOI 0 根 → 2 根、conf medium。
- [x] `valuation_pack.evidence_independence.sell_side_only`：標記「兩個 family 其實同一批賣方餵養」，不假裝獨立。
- [x] `implied_expectations.market_implied_revenue`：FCF ≤ 0 時改問「營收要長多快才撐得住今天的 EV/S」。
- [x] Phase 4.6 speculative governor（size ≤ 1% / conf ≤ 0.70，verdict 不動）+ validator §10b + §14 合法出路。
- [x] **`FWD_PE_CLAMP` 校準工具**：反解市場隱含 PE（`price × (1+r)^h ÷ target_eps`）進 `shadow_report.py`；`pe_clamp_binding` / `justified_pe_raw` 進 pack 的 `calibration`。實測 11 檔：全母體中位數 36.7、上限綁到 8/11。
- [ ] **累積 live cohort ≥5 檔後回頭看判準**：目前 live 只有 AAOI 一檔（隱含 PE 31.6），`shadow_report.py` 的判準會回 `accumulating`——那是「還不知道」，不是「沒問題」。跑法與紀律見 `OPS_COMMANDS.md` §7 對應列；**改值一律 user 核准，不可自動跟隨中位數**。
- [x] **`TERMINAL_EV_SALES` 已量測並拆成兩情境**：4.0（保守／規範性）+ 8.0（科技中樞）。實測成熟獲利公司 median EV/S 半導體 13.9 / 通訊設備 8.3 / 軟體 8.0 / 工業 2.8——原文件把 4.0 誤稱為「成熟中樞」，已更正為壓力測試假設。
- [x] **無效 beta 不再落到折現率下限**：`beta ≤ 0`／缺值 → `FWD_BETA_FALLBACK = 2.73`（母體中位數，n=14 實測）。SPCX（beta=0，IPO 2026-06-12）由最寬鬆的一檔改為 r=16.9%。
- [ ] **`FWD_BETA_FALLBACK` / `TERMINAL_EV_SALES_SECTOR_TYPICAL` 都是 2026-08-07 的單次量測**，各 n=14 / n=20。`shadow_report.py` 的 `beta_fallback_rate` 偏高時就該重量前者。
- [ ] **`FWD_DISCOUNT_CLAMP` 上限 0.30 仍未回答**：實測 CRWV beta 7.41、APLD 5.68 綁到上限（11 檔中 2 檔）。要問的不是「0.30 對不對」，而是「beta 7 的 CAPM 還有沒有意義」——若無，這個 archetype 的折現率可能該換一套非 CAPM 的推法（例如按 stage 分級的要求報酬率）。現況已可觀測：`discount_clamp_binding` 進了 calibration，校準區段會報綁定次數。
- [ ] **`market_implied_pe` 不是無假設的市場觀測**（已寫進 docstring）：它是「在我們假設的折現率下」市場付的倍數，折現率一改它就跟著動（SPCX 38.8→45.3）。所以倍數校準與折現率校準不能同時做——先釘住折現率，再看 PE 分布。
- [ ] **目標年度選擇的敏感度**：AAOI FY27 覆蓋 3 家 → $153，掉到 2 家則退回 FY26 → $33。已由四道限制約束且寫進 schema，但若實務上出現覆蓋數在門檻附近跳動的標的，考慮加「跨年度加權」而非單點取值。
- [ ] `valuation_reviewer_gate` 的 `transition_case_active` 仍不區分 false 與 unknown（v4.107.0 留下的洞，本輪未動）。

## ✅ Done (v4.105.1) — Break News stale backlog 死鎖修復

- [x] `_pending_backlog_count()` 改用 `PENDING_MAX_AGE_HOURS` 判準,只數 debater 實際會處理的新鮮 backlog,解除即時辯論 2+ 天靜默停擺。
- [ ] (低優先)43 筆歷史 stale backlog(2026-05-27 ~ 2026-07-13)未清,可透過 `/break-news.html` 既有的 stale-pending 手動 triage UI 清理,或討論是否要加自動過期機制。

## ✅ Done (v4.105.0) — 盤中頁單頁化

- [x] strategy/mood 兩 tab 合併單頁(決策→環境→個股→策略→板塊),警報橫幅永遠可見;重複顯示歸一;族群密集卡。驗收 8/8 PASS、搬丟=0。
- [ ] (低優先)族群卡「連 N 天」欄:需 history.py 存族群層快照才做得出來,要做時連後端一起評估。

## ✅ Done (v4.104.0–.1) — 個股反轉降噪(偵測層)+ 推播擴充

- [x] 雙確認(KDJ∧MACD 同向)+ σ 位移門檻(1.5σ/退 0.3%)+ 翻面冷卻(10 分/2.5σ)+ 開盤 09:30–09:45 加嚴;同批 bars 誤報 9/14 → 0,fresh-context 驗收 8/8 PASS。
- [x] (.1) 推播擴充三事件源:合格反轉★/急拉擊殺/高強度 spike;移除前端區間二次過濾(偵測層已把關)。

## 🔵 Backlog — 盤中分析檢討待辦(2026-08-07 定案,優先序由上而下)

- [ ] 先行小改:`narrate.py` 的 input 加入 `intraday_spikes` 個股訊號 + `kill_triggers`(目前是 hub 死輸入),讓盤中導讀能點名個股與擊殺條件距離。
- [ ] 維運:`intraday_spikes.json` 補收盤快照;`daily_health.py` 補監控 spikes / intraday_eval 新鮮度。
- [ ] 故事層 A:跨資產 watch ring——USO/TLT/UUP/GLD/IBIT/SMH/XLE/XLK 走同一條 Alpaca 1 分線 free lane(盤中層目前零跨資產:無油價/利率/美元/金)。
- [ ] 故事層 B:session 級事件日誌 `intraday_events.jsonl`——各 detector + break news 事件帶時間戳入流(現在訊號流 stateless、只回溯 30 bars)。
- [ ] 故事層 C:deterministic 鏈接器——手寫 linkage map(油↑→risk-off、利率↑→成長↓、QQQ↓→高β半導體放大),時間窗內找方向一致的 macro→index→sector→stock 鏈,措辭用「時序共振」非因果。
- [ ] 故事層 D:`narrate.py` 改餵事件鏈,產出「10:02 油急拉 → 10:15 QQQ 失守 VWAP → 10:21 SNDK KDJ 死叉」式導讀(change-gate 照舊)。

## 🔵 In Progress (v4.100.0) — X KOL 市場氣氛試點

- [x] 骨架:預算閘 / client / collector / dry-run 可跑。
- [x] 分析水位(`pending.py`):只有新貼文會進 LLM;at-least-once,崩潰重送不漏送。20 支測試。
- [x] 限速查證:`/2/users/:id/tweets` 10,000/15min per app、900 per user。**頻率不是瓶頸**,20 帳號每 5 分鐘只用 60 req/15min。
- [x] 「0 則回傳 = $0」**已實測成立**(帳本沒動、限速有走)。
- [ ] 仍要拿 `--status` 花費對一次 X billing dashboard —— 帳本記的是我方收到筆數,X 的 24h 去重會讓我方高估。
- [x] `X_BEARER_TOKEN` 已放 `premarket_cron.env`,`--status` 確認讀到(116 chars)。
- [x] 首次 live sweep 完成:分頁 bug 已修,log 5 筆 0 重複,花費 $0.0650/$10。
- [ ] **等使用者**:KOL 名單(`config/x_kol.json` 的 roster,目前只有 Serenity)。選人準則見 config 內註解 —— 要挑真的打 `$TICKER` 的帳號。
- [ ] 第一次 live sweep 後檢查:`--status` 的花費是否合乎預期(冷啟每帳號上限 5 則)。
- [x] 族群熱度 + 人工晉升閘(`heat.py`)完成,含代號身分驗證。
- [x] UI 完成:`/x-kol.html`,含送分析/剔除按鈕。
- [ ] **未驗**:頁面渲染沒親眼確認(瀏覽器擴充未連線)。使用者開一次確認版面。
- [ ] 排程決定:掃描節奏(盤中 15-30 分一輪)與掛在哪(cron / dashboard poll loop)。**使用者說暫時不用排程,維持手動。**
- [x] `$SIVE` 已查證:`SIVEF` 不存在;`SIVE.ST` 只有 profile 無價格(EOD 0 筆);裸代號是無關的 OTC 仙股。**結論:不可分析**,已標記,僅計入族群熱度。
- [ ] 若之後真要追 Sivers,需要 FMP 以外的歐股價格源 —— 這是資料源決策,不是這條 pipeline 的事。
- [ ] 主體/道具目前是位置啟發式(第一個 cashtag)。要更準就換 LLM 分類,接口已預留。
- [ ] 累積 ≥2 週資料後做領先性評估;**過不了就砍掉,不要接進 mood 面板**。判準未定,要在看資料前先寫死。
- [ ] (可選)`yan-labs/serenity-aleabitoreddit` 的 6,232 則歷史存檔可做零成本回溯驗證,補足付費試點的樣本不足。該 repo 無 LICENSE,僅自用。

## ✅ Done (v4.99.3) — 盤前 chain 解除 news→sector 連坐

- [x] `_PREMARKET_NONBLOCKING = {"news"}`：news 失敗記 warning 但 phase 2 照跑；daily 因真資料相依維持 fail-fast。
- [x] UI `done` 帶 warnings 出黃色降級 toast，不再用成功 toast 蓋掉失敗。
- [x] 3 支回歸鎖住連坐解除、daily 仍阻斷、非阻斷名單只含 news。
- [x] 8 份超篩歷史 digest 日檔已刪（backup + JSONL 皆可還原）。

## ✅ Done (v4.99.2) — Projection shallow top-10 cap

- [x] `build_projection()` 補 `_cap_shallow()`：同日多次 run 的 union 重切回 top-10（deep 不設限），修好盤前 chain 卡在 phase 1、sector 從不 enqueue。
- [x] 兩支回歸鎖住「多 run union 重切」與「全同分 tie 穩定不重排」；2026-08-06 re-project 後 validator rc=0。
- [x] 8 天超篩的歷史 digest 已於 v4.99.3 刪除（使用者裁示）。

## ✅ Done (v4.99.1) — Mixed DIGEST/FLASH validation

- [x] Validator 改按 record-level event mode/fanout 檢查 mixed projection，不再把 pending INLINE FLASH 當成 DIGEST deep failure。
- [x] 真實 WDC FLASH event、projection 與 Dashboard bridge 資料確認存在；新增同日 DIGEST + FLASH 回歸測試。

## ✅ Done (v4.99.0) — News append-only event store

- [x] DIGEST／FLASH／REVIEW judgment 改為 JSONL append-only event；daily digest deterministic projection 保持 UI contract。
- [x] REVIEW 以 stable event_id supersede pending FLASH，cache patch 下沉 deterministic projector。
- [x] 86 份 legacy digest migration、一次性 backup、rollback/re-project 與 idempotent replay。
- [x] 自動記錄每場 DIGEST telemetry；目前 1/10，滿 10 場前 materiality threshold 保持 4.5。

## ✅ Done (v4.98.0) — News deterministic finalizer

- [x] compact debate input 契約；LLM 不再手算 score/verdict 或重寫 digest/MD/cache。
- [x] 共用 Arbiter 公式、validator 重算、stable event ID 與 phase0 idempotency ledger。
- [x] digest assembly、cache patch、Markdown render 收斂為單一 finalizer call。
- [x] 第三階段：append-only event store，解開 DIGEST/FLASH/REVIEW 共用 daily digest 單檔覆寫競態；migration、rollback 與 Dashboard projection 已於 v4.99.0 完成。

## ✅ Done (v4.97.2) — Heatmap 401 熱斷

- [x] FMP 401 由逐 ticker error 改為 process-wide 6h breaker，單批只印一行可行動訊息。
- [x] Auth-failed 零成功 batch 保留舊 heatmap snapshot/timestamp，新增回歸測試。

## ✅ Done (v4.97.1) — 盤前鏈 degraded 契約

- [x] `daily_update.sh rc=2` 顯示為黃色降級完成，不再錯誤中止 Sector protocol 與 Dashboard 刷新。
- [x] modal、全站 status pill 與 server exit-code mapping 統一，新增契約回歸測試。

## ✅ Done (v4.97.0) — News V2.3 訊號與首批 token 優化

- [x] Stage 1 materiality 與 direction 分離，加入 genre/event/source diversity；安靜日不強迫 top-5。
- [x] BINARY 改為 explicit pending event；非 binary verdict 由 deterministic ±0.75 gate 驗證。
- [x] compact digest packet、原始 URL 保存、Stage 2 bundle cap 3,000 chars。
- [ ] 累積 10 次 V2.3 DIGEST 後統計 Stage 2 平均則數、genre/source 分布、BINARY rate 與 CLI token/cost；資料不足前不再調 materiality 4.5 門檻。
- [x] 第二階段 token 優化：digest assemble/render/cache patch 下沉 deterministic runner（append-only event store 拆至 v4.98.0 後續項）。

## ✅ Done (v4.96.0) — Daily update 可靠性與 thematic 加速

- [x] daily_update single-run lock、degraded rc=2、current-day/parse/partial health gate。
- [x] 日常 Nexus 降為 deterministic Tier 1+2；Tier 3 LLM full rebuild 保留 on-demand。
- [x] thematic enrichment 接中央 FMP pool、12-worker bounded concurrency、atomic output。
- [ ] 下一次 cron 真實執行後，比對 enrichment 基線 518 秒與總輪 682 秒，確認 pool 等待／429 telemetry；若仍 >240 秒，再做 endpoint batch/cache hit 分析。

## ✅ Done (v4.95.7) — Earnings calendar 去瓶頸與完整性

- [x] Upcoming calendar 以 cached company screener 取代 2,837 支逐檔 profile fan-out；cold cache 2 calls、warm cache 0 calls。
- [x] 30 日 earnings calendar 遇 4,000-row cap 自動切段／去重，單日仍飽和 fail closed。
- [x] 完整 sector prefetch 由 360 秒 timeout 改為 266.5 秒、九項全 rc=0。

## ✅ Done (v4.95.6) — RSS 一手來源與來源排序

- [x] 移除凍結的 MarketWatch MarketPulse，加入 SEC／FTC／Census／EIA 四個官方 RSS。
- [x] Digest + Break News 共用 `source_kind` 去重優先序，unified raw 保留逐-feed health metadata。
- [ ] **BLS/SEC enforcement adapter**：BLS Employment/CPI/PPI/JOLTS 與 SEC Litigation/Trading Suspensions 是官方 RSS，但目前執行環境回 403；要用專用 header/rate policy 並在部署環境 live 通過後才接入。
- [ ] **EDGAR watchlist 化**：全市場 8-K 最近三日 192 筆、0 筆晉級 Stage 2；改為持倉／watchlist CIK + 8-K/10-Q/10-K/6-K 優先，避免高權威低語意 feed 淹沒 triage。

---

## ✅ Done (v4.95.5) — FMP calendar 中央限流

- [x] economic/earnings calendar 與 per-symbol profile fan-out 全數接入 cross-process `fmp_pool`；prefetch/fallback 不再引用 `~/.claude` 旁路腳本。
- [x] 429 response body／`Retry-After` 安全落盤，錯誤輸出與 artifact 不保存 API key。

---

## ✅ Done (v4.95.4) — Dashboard protocol 主要 LLM 路由

- [x] 盤前檢查的 news/sector 與所有 Dashboard agentic protocols 改由 primary → secondary → tertiary 啟動時選擇，移除 Claude hardcode。
- [x] Codex 寫入、tool/subagent 語意、JSONL 進度/錯誤/token usage 相容層與回歸測試。

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

## 📋 Backlog — S路線：產業掃描 Lean 化 + 資料補強（2026-08-03 兩輪審視定案）

> 來源：2026-08-03 對 sector protocol V1.4 的兩輪審視。編號：**SE** = 第一輪（執行效率 Efficiency）、**SD** = 第二輪（資料補強 Data）。紀律對齊 invest 端 L 路線：**score 生產方式改變必 shadow-first**；權重/門檻/翻預設**使用者拍板**；探索層（break news / nexus / 回測）產出**永不進 score/verdict**。每項獨立 bump 一版。
> 依賴：SE2 依賴 SE1 達標；SE6 動工前先立 lane contract（C1 教訓）；SD1 是一切權重再校準的前提。**不動的**：News lane / DA / `upcoming_events` / `today_verdict` 留 LLM——那是真判斷。

### SE — 執行效率（第一輪：元件×stage 盤點）

- [x] **五 agent review 彙整的殘餘 P2/P3** — **4.95.3 完成**。L5 NaN 大洞（`sentiment_score._num` 沒 isfinite → NaN 變 +3.0 假極端看多；`_direction(nan)` 假 NEUTRAL；yfinance 源頭）、`_slim_fred` 第二層型別崩潰、flip 判準拆 band_mismatch、validator `shadow_only` 只認 JSON true、SE1/SE3/SE5 全部可修 P3。刻意不修：hard-require 出貨紀錄、SE3b（規格決策）、L5 契約側（全過）。詳見 CHANGELOG 4.95.3。
- [ ] **SE1b — `build_phase0()` 加 cache-dir 注入點，讓 build 層接線可 hermetic 測**：backfill 判定與 shadow 落盤的接線目前沒有測試釘住（刪掉 `backfill=backfill` 照樣全綠），因為 `build_phase0()` 經 subprocess 跑 `phase0_read_caches.py` 讀 live repo cache，測試無法給它假資料。先給 reader/builder 開 `--cache-root` 之類的注入點，再補「backfill 場次 `sample_valid=false`」與「score_components 壞形狀 die」的 e2e 案例。
- [x] **4.95.1 的第二輪 review 修正** — **4.95.2 完成**。修 bug class 的那輪自己漏掃同構位置：SE3 覆蓋守衛在值層復發（`{"Utilities": null}` 仍讀成「查過了」）、SE5 rc 契約沒守到歷史 intel + `_slim_fred` 源頭沒消毒、SE4 抓到 FTD `exposure_range` 讀錯 dict（live intel 恆 null，文件是對的）、SE1 讀出端三個分母灌水口（`.prev` 備份、truthiness、非字串版號炸 `--status`）。`CALCULATOR_VERSION` 刻意不 bump（未動計分語意）。L5 review findings 另輪。詳見 CHANGELOG 4.95.2。
- [x] **SE1/SE3/SE4/SE5 的 code review 修正** — **4.95.1 完成**。四支 script 共用同一個盲點：**韌性只做到檔案層，沒做到欄位／元素層**（`_num(...) or 0`、`cache.get(s) or {}`、`_canon_list` 不守元素型別）。三處都已在整檔層級寫了正確守衛，只是規則沒往下延伸一層，而測試因現有資料乾淨而全綠。另修：回填舊日期會從後門寫進 live 割接分母、half-up 只換了最外層（中間 2dp 仍是銀行家捨入 + 缺 eps）、SE4 把 `exposure_ceiling` 錯分類成 script 自動填而連帶刪掉它的映射 rubric。詳見 CHANGELOG 4.95.1。
- [x] **SE1 — Shadow score 報告落盤** — **4.92.0 完成**。`shadow_score_<DATE>.json`（含 `coverage` 與 `sample_valid`）+ `--status` 割接進度 + `--audit-decisions` 歷史重放 + `test_sector_score_calculator.py`。
  - **原假設被實測推翻**：條目寫的「補模 Step 5 消假 hard diff」是錯的方向。33 筆帶 binary risk 的歷史樣本中 31 筆證明 LLM 把 ×0.70 **烙進 score_components 後**才寫下，補模 = 雙重計分（實跑當場產生 diff=20 的假 hard diff）。改為「偵測不重算 + 標 `unverified_steps`」，SE2 割接後才會變成可驗證。
  - **順手修掉 `round()` 的銀行家捨入**：473 筆實測 half-up 92.2% vs banker's 91.5%，差的 3 筆全是 `.5` 邊界。用錯只會產生整批 ±1 的系統性 soft diff——剛好落在 soft 門檻內，看起來像 LLM 心算飄而不是捨入錯。
  - **SE2 的證據一次到位，不必等 5 場**：audit 43 場、38 場全乾淨；問題幾乎全在 5 月早期，7 月以後 9 場裡 8 場乾淨，唯一 hard diff 是 2026-07-20 Communication（calc 56 vs LLM 39，套不套 ×0.70 都對不上，真實漂移）。**歷史 audit 刻意不計入 `--status` 分母**（那些場次 `_phase0` 不可考，混進去＝C1 說的假證據）。
- [ ] **SE2 — Phase 4c 決策樹 script 化割接**（invest L1/4.80.0 的移植）：STEP A–G.5（乘數/降級/verdict/stance）全是 threshold 邏輯。割接後 PS 只出 4 component 分數 + 質化欄位，script 算 verdict；LLM 只寫 STEP H `today_verdict`。消心算漂移 + 砍 4c（PS 最長 inline 推理段）。零星手算清理（`synthesized_exposure` 三訊號合成、`uptrend_ratio_overall` 平均）割接時順手併入，不獨立開項。
  - **SE1 已把證據備齊，不必再等 5 場 live**（照 invest L1 用 replay 取代累積的前例）：`--audit-decisions` 43 場、38 場全乾淨，7 月以後 9 場裡 8 場乾淨。動工前重跑一次確認基線沒退。
  - **但 `sector_score_calculator.py` 只寫完三步**（base / valuation_penalty / step6），**Step 5 特殊乘數與 STEP A–G.5 整棵樹都還沒有**。SE1 的教訓在此變成 SE2 的規格：LLM 現在把 Step 5 烙進 `score_components`，割接後 engine 必須改吃**未經乘數的原始分項**，否則等於把同一個乘數套兩次。這是 decision JSON 的 schema 變更（`score_components` 語意改變），要一併定版。
  - 已知的兩筆真實漂移可當 fixture：2026-07-20 Communication（calc 56 vs LLM 39）、2026-05-19 Technology（calc 49 vs LLM 35）。
- [x] **SE3 — R4–R7 DA pre-trigger script 化** — **4.93.0 完成**。`da_pretrigger.py`（零新計算）+ `--prompt-only` 直接產 `<TRIGGERED_DIVERGENCE_RULES>` 內容 + `test_da_pretrigger.py`；`phase_4-5.md` 改「MUST 用 script」（同 step6_overlay 紀律）。
  - **設計重點是「資料缺席 ≠ 沒觸發」**：FRED 缺席 → R4 標 `available=false` 且 prompt 明寫「未能判定」；HARD cache 缺席 → rc=1 不得回「沒觸發」。把未知講成安全會讓 DA 少發該發的 challenge 且全鏈路無人察覺。
  - 驗證：7/31 cache 實跑，輸出與當日 intel 的 `sector_divergence_watch` **逐字吻合**（R7 Technology 三窗口數值、R4 Financials real_rate 門檻）。
- [x] **SE4 — Protocol 文件瘦身** — **4.95.0 完成**。`protocol_appendix_fallback.md`（173 行，條件式載入）；常駐 context **−157 行**（phase_0 164→106、phase_1-2-3 342→243）。
  - **切分準則是「先查誰在用」**：`cycle_phase` 推斷規則留主檔（仍是 LLM authored，`require(decision, ...)`）、`warning_flags` 表可以走（已 script 化）。七類 live rubric（beat_rate ±5、R5/R6/R7 提示、WebSearch 禁令、FTD 反幻覺、FRED slim 11 欄、cycle_phase、情緒映射）全部留下。
  - **舊「欄位映射表」標記為非現行 spec 而非原樣搬走**：實查與實作有三處不一致（`breadth_components` 1 欄 vs 4 欄、`regime_confidence` 硬編 0.9、`warning_flags` 4 種 vs 6 種）。把過期的表當參考資料搬走＝讓它繼續誤導。
- [x] **SE5 — FRED lane 條件式 gate**（shadow-only）— **4.94.0 完成**。`fred_lane_gate.py` 4 條 trigger（`adjustments_active` 為 **mandatory**）+ `--write` / `--status` + `test_fred_lane_gate.py`。
  - **trigger 設計依據是實查而非直覺**：lane 的增量只剩 `adjustments` 層（GUIDE RULE 1/2），因為 `favor[]` 已由 `step6_overlay.py` deterministic 套進分數，而 `adjustments` **沒有任何腳本消費**（step6_overlay.py:81-82 只讀 favor/avoid）。adjustments 為空（RULE 4）→ lane 只會覆述 step6 算過的東西。
  - **`regime_confidence < 0.40` 刻意不設為 trigger**：低信心時 step6 的 confidence gating 已把乘數壓回 1.0 附近、lane 也必須自標 LOW-CONFIDENCE，增量更低——當觸發條件方向是反的。
  - **與 L4b 不同：跳過不改決策數字**（STEP G.5 / Step 6 / consensus_warning 都不經此 lane）。翻預設時唯一要小心的是 **skip 不得寫進 `degraded_agents`**（會誤觸發 PARTIAL_FALLBACK 的 cap）。
- [ ] **SE3b — `da_pretrigger` 的 FRED 時序交叉檢查（4.95.1 只做了記錄）**：`fred_latest.json` 沒有日期版本，4.95.1 已把 `fred_generated_at` 寫進輸出讓稽核可重現，但**還沒有比對**：(a) snapshot 比 `--date` 舊多久算 stale、(b) daemon 停擺時 Phase 0 已宣告 `fred_available=false`，而 da_pretrigger 讀到殘留的舊檔仍會回 R4 `available=true` —— 兩者對同一場次給出矛盾的可用性。修法要先決定 stale 門檻由誰定（跟 `phase_0.md` 的 fresh_window 3600s 對齊還是另立），屬規格決策不是純 bug。
- [ ] **SE5b — FRED lane 收不到 `adjustments`（SE5 發現的既有缺口，行為變更故未同版動）**：protocol 要求 lane「`adjustments[]` overrides favor（不可只重複 favor）」，但 lane 的資料切片 `_phase0.fred_snapshot` 是 slim 11 欄、**不含 adjustments** —— lane 被要求套用一份它從未收到的資料，只能覆述 favor（正是 RULE 1 禁止的）。修法：把 `adjustments` 併進 lane 切片（連帶決定要不要進 slim shape / schema）。**會改變 lane 產出 → 需 shadow 或至少一場人工對照**；`fred_lane_gate.py` 的 `notes` 每場都會標出這件事。
- [ ] **SE6 — Rotation lane det-shadow + sector 版 lane contract**（C1/4.90.0 教訓：**割接第一個 lane 前先立契約**）：先在 sector_intel 加 per-lane `{provenance, llm_invoked, producer_version, shadow_score}`（現只有 session 級 `phase4_fanout_mode`/`degraded_agents`），再做 Rotation lane（最機械：uptrend_ratio + rotation_signal 排序）det producer shadow。否則 `backtest_step6_overlay.py` 這類回測會混 LLM 分與 script 分。

### SD — 資料補強（第二輪：缺口 / 用滿 / 跨頁供給）

- [ ] **SD1 — Verdict 成績單（feedback loop）**：sector verdict 從未回測命中率，25/25/25/25 base 權重是手拍的。照 `momentum-journal` 模式寫 `sector/scripts/verdict_journal.py`：scan 時 snapshot（date × sector × verdict × score × components），事後回填 proxy ETF 5/20/60d forward return → `sector_verdict_index.json`（比照 invest `event_index`），供 Dashboard decisions 頁。**沒有 ledger，任何 rubric 調整都是猜**；權重調整另開項目且使用者拍板。
- [ ] **SD2 — 盤前數據**（協定名為 Pre-Market 卻零盤前數字）：`phase_prefetch.py` 加 premarket task（SOFT fail）：ES/NQ 期貨 + 11 支 proxy ETF 盤前漲跌/gap（FMP `/stable/` premarket 或 yfinance）→ `_phase0.premarket` 新 block，`today_verdict` 可引用；亦供 break-news / mood 頁。
- [ ] **SD3 — 跨板塊共同因子風險**（新時代盲點：HOT 集合全押同一 AI 敘事 = 表面分散實際單注）：script 算 11 proxy ETF 90d 報酬相關矩陣 + theme-detector `affected_sectors` 重疊計數；HOT 集合 avg pairwise corr > 門檻 → `risk_flags += "correlated_bets"` + stance cap。**先 shadow 兩週再定門檻**；矩陣輸出供 sector.html 證據熱力區。
- [ ] **SD4 — 小額訊號補強**（三個皆 shadow-first、SOFT fail）：(a) VIX 期限結構 ^VIX/^VIX3M 進 `sentiment.py`（backwardation flag）；(b) earnings revisions breadth：`fetch_earnings_pulse.py` 擴 FMP analyst-estimates 上修/下修比（前瞻，補 `beat_rate_30d` 的回望性）；(c) equal vs cap weight RS：RSP* vs XL* 配對偵測 mega-cap masking → Phase 4b divergence 提示（R8 候選，不改 score）。
- [ ] **SD5 — 既有數據用滿 + 跨頁供給**：(a) V2.9.0 多週期 RS（已算、只當 DA 提示）→ deterministic momentum-exhaustion overlay 候選（照 valuation_penalty 模式，shadow 看分佈再定）；(b) PT/grades ~111 calls 產出只有 R6 一條提示 → 配 SD4(b) 重估 ROI，不值就 `--skip-analyst` 常態化；(c) Break News divergence notes → 只餵 `watch_next`/narrative + provenance 標記（**探索層紀律：不進 score/verdict**）；(d) 跨頁：stance/synthesized_exposure 歷史 → mood.html regime 時間軸；sector PE z-score cache → valuation-modeler comps 的 sector baseline（純資料供給）。
- [ ] **SD6 — Watchlist（不動工，等資料源）**：CFTC COT 持倉（週頻可行但排後）；真 ETF flow / 板塊選擇權 GEX、IV skew（免費源不穩，不為它加爬蟲維護債）。

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
- [x] **L4 — Valuation quant 提前 Phase 1.5**（4.88.0）：`--stage quant` / `--stage mhp --from-quant`；單發模式 = 兩段的組合，等價是結構保證。protocol 新增 §PHASE 1.5、Phase 2.4 縮成 MHP-only、修 Valuation lane 數字來源時序矛盾。live NVDA 兩段 vs 單發 bitwise identical。
- [x] **L4b — Valuation Specialist 改條件式 reviewer**（4.89.0，shadow-only）：5 條 trigger，其中 `transition_case_active` 為 **mandatory**——實測發現跳過 lane 會讓 `valuation_confirmed_transition=False`、Phase 3 cascade rule #2 的 ×0.95 落回 ×0.85，「跳過不改決策數字」前提不成立。peer discovery cache TTL 30d，只餵 gate 不餵 build_pe_cohort，且不覆寫人工核准的 config。
- [ ] **L4b-2 — 翻預設（skip 生效）**（依賴 L4b shadow 樣本，**使用者拍板**）：gate 接進 `shadow_report.py` 讀出端；停止規則用「discovery 覆蓋率穩定後再數 N」而非固定 session 數（暖機期命中率不反映穩態）——但**「穩定」必須落成具名可操作常數**（例：連續 K 個 session 的 `no_peer_cohort` 命中率不再下降），理由同 `ARCHETYPE_CHECKPOINT_N` 寫成常數；否則只是把人工判斷點從「跑滿沒」換成「穩定沒」；validator 目前擋 `shadow_only=false`，翻預設時要一併鬆綁。
- [x] **L5 — Sentiment lane deterministic 化**（shadow-first）— **4.91.0 完成（shadow-only）**。`sentiment_score.py` det producer + `test_sentiment_score.py` + `sentiment_det` block + validator §5j + `apply_det_shadow` 映進 C1 契約 + `shadow_report.py` L5 哨兵。
  - **動工盤點推翻「公式已寫死」**：只有市場層是完整規格（PLTR 那筆 `+0.92` 可重現）。`stock_specific` 的**聚合方式與 clamp 全庫無定義** —— 本版定死為「加總 + clamp [-3,+3]」，寫成具名常數 + 測試釘住；insider 取 `quarters[0]` 是沿用 schema 既有 `det_inputs.insider_ratio_q`，非新發明。**這兩個定案是填規格空白，不是搬既有規則**，使用者要改是常數層 5 行。
  - **兩條規則現行資料源做不出來**：`institutional.accumulation_signal`（bundle 該 block 實測常為空）、`SBC > 15% revenue`（bundle 無 SBC/revenue）。一律進 `missing_inputs[]`，不猜值、不假裝有跑。
  - **契約側只映 `score`**：`producer_version` 那格記的是 lane 的產出者，shadow 期是 LLM；填 det 版號等於向 Phase 6 宣稱這筆已是 script 產的。
- [ ] **L5b — 翻預設（det 取代 LLM lane）**（依賴 L5 shadow 樣本，**使用者拍板**）：條件 = 累積 ≥ `SENTIMENT_CHECKPOINT_N`(20) session **且**方向翻轉率 < `SENTIMENT_DIRECTION_FLIP_MAX`(20%)。翻預設時要一併：validator §5j 鬆綁 `shadow_only=false`、producer 改寫 `provenance: "deterministic"` + `producer_version`、weight 凍結窗（照 V3.45.4 News 前例）。
  - 哨兵看**方向翻轉**而非分數差：det 移除了 LLM 的規則表外因子（歷史報告可見 APP 那筆把「retail/momo 資金 5 日 +19%」算進去），連續值落差是預期的。
  - 翻預設前值得先回答：`missing_inputs` 是否集中在同幾檔（若是，補資料源比翻預設優先）。
- [ ] **L6 — Technical deterministic-first**（shadow-first）：det score producer（technical_core 為基）；LLM reviewer 觸發規則化（指標矛盾 / gap / parabolic / det score 落 threshold ±band）；qualitative 欄位（pattern_taxonomy / smart_money / key_levels → MHP 依賴）需 det 版或觸發 LLM 時才產。shadow + weight 凍結窗。
- [ ] **L7 — Red Team evidence ledger**：Python 壓 ledger（consensus_thesis / claims / negative_evidence / valuation_assumptions / implied_expectations / dq_flags / unresolved_conflicts）；RT prompt 改吃 ledger（先縮 prompt，不跳過）；classifier haystack 欄位保留。
- [ ] **L8 — RT decision-invariant skip**（依賴 L1）：bounded simulation 窮舉 verdict × strength × basis × shift-tier，final action / cap / size tier / risk flags 全不變才 skip；skip = 跳過推理**不跳過產出物**——kill_conditions ← det kill triggers 生成、counter_thesis 模板化；decision_lock / Dashboard kill_triggers 相容。
  - **原本規劃的 `red_team_provenance: deterministic_skip` 欄位不要開**：C1（4.90.0）已把 red_team 納為第六個 lane，skip 只要寫 `lane_contract.lanes.red_team = {provenance: "deterministic", llm_invoked: false, producer_version: ...}`。另立平行欄位正是 C1 要消滅的東西。
- [ ] **L9 — Refresh / content-hash mode**：factpack 加 `content_hash` + `material_change_since_last`；`analysis_mode: LEAN|FULL_IC|REFRESH` + LEAN→FULL_IC 升級規則 deterministic 寫進 protocol 正文（首次覆蓋 / structural shift / 高信心可行動決策必升）；refresh entry 的 history/Phase 6 語意定義。
  - **契約側的兩個欄位 C1 已開好**：`lane_contract.analysis_mode`（值域已釘 `FULL_IC|LEAN|REFRESH`，validator 驗）與 per-lane `input_hash`（目前恆 null，等 factpack content_hash）。L9 只需要改「什麼時候寫哪個值」，不必再動契約形狀。
- [x] **C1（橫切）— 統一 lane 資料契約** — **4.90.0 完成**（schema `V5.3`）。`lane_contract`：六個 lane（五個分析 lane + **red_team**）的 `{provenance, llm_invoked, producer_version, input_hash, shadow_score}` + session 層 `{analysis_mode, llm_invoked_lanes[], llm_skipped_lanes[]}`；producer 併進 `apply_det_shadow.py`（Step 1.5 同一步，不另開 script）；validator §15 + §2e 反向 guard；`test_lane_contract.py`（producer 半 + 18 例 tamper battery）。
  - **持久化缺口的裁決**：只有**契約欄位**進 history。質性大塊（五個 lane 的 `key_factors` / `risk_flags`、sentiment 質性欄、`macro_context` 全文）留在 `phase_inputs/` artifact —— history.json 是決策帳本，不是報告的第二份原稿；L3 已讓 artifact 落地存檔且有重疊欄位硬閘。缺口 1-4 因此**不進 history**，狀態不變。
  - **缺口 5（形狀不一）已修**：`moat_assessment` / `smart_money_analysis` 一律 dict、`immediate_catalyst_5d` dict 或 null、smart money 正文欄位統一 `narrative`。**只對 V5.3+ 生效**。
  - **原計畫「renderer 三處相容碼在 C1 落地後刪」沒做，是刻意的**：形狀鎖對舊 entry 豁免（181 筆全在 V5.0 以下），renderer 讀得到它們，刪相容碼＝舊 entry 渲染時靜默掉字。刪除條件應是「舊 entry 淡出 render 路徑」，不是「C1 落地」。
  - **`producer_version` 對 LLM lane 填 `protocol:<repo VERSION>`**（不是 null）：LLM lane 沒有 producer script 版號，但評分行為由 rubric 決定、rubric 改動一律 bump repo 版號 —— 這回答的正是 Phase 6 要問的「這筆在哪一版 rubric 下打的分」。
  - **`input_hash` 目前恆 null**：factpack `content_hash` 是 L9 的產出物。欄位先開，L5 的 det producer 才有位置寫，不必再改一次契約形狀。
  - **舊 entry 不回填**（版本閘綁 `V5.3`，同 §13/§14 紀律）：V4.6 的四 lane fanout 與六 lane 契約不是同一回事，補一份「看起來很完整」的 provenance 等於在稽核軌跡放假證據，而 Phase 6 分層會直接吃到。
  - **`lane_scores` 升為 validator 硬性要求**（V5.3+）：契約用它推導 `provenance: absent`；protocol 從 V2.10.0 寫必填但 validator 從未擋，於是「整塊省略」＝ 把四個跑過的 lane 標成沒產出。FULL EXAMPLE 也補齊了這個一直缺席的欄位。
  - **順手補的下游洞**：Dashboard `VERSION_COLOR` / tooltip 缺 `V5.2`（L2 就漏了）與 `V5.3` → 新 entry 會被標成灰色 `ARCHIVE` badge，最新的變最舊的。
  - **4.90.1 收掉 review 的 P2**（保留規則套到 `lanes.valuation.shadow_score` → 吸收閘永久 rc=1 且重跑修不好）+ 1 個 P3（缺版號的 payload 仍寫契約）。明細見 CHANGELOG。
  - **4.90.2 自審收掉 §15 兩條實錘繞道**：null lane block 跳過全部欄位檢查；有分數的 lane 手改 `absent` 全綠。修法 = provenance 雙向錨在 lane_scores（§13 保護）與 RT 旗標（schema 必填）上。
  - **4.90.3 複審 4.90.2**：抽出 `authoritative_valuation_score()`（4.90.2 在 validator 重寫了一份取值順序 = 自己引入的漂移面）+ 擋 `lane_scores` **部分**省略（整塊省略的零售版，producer 與 validator 會一致同意那個偽造）。
  - **4.90.4 第四輪 review**：保留規則界線改為逐欄位定域（`EXTERNAL_PROVENANCE` 常數）——P2 同型死結在 `provenance` 的 llm/absent 與 `llm_invoked` 復發，真實序列（漏填 lane score → 補上 → 重跑）就會鎖死。**L5/L6/L8 加契約欄位時照兩域表歸類**（schema doc `lane_contract` 節），不再逐次憑直覺。
  - **[P3, 已知未修]** 形狀鎖的「正文欄位改名」檢查只認得 `note` 這一個錯名（`text` / `comment` 之類漏網）。要收緊就是把條件改成「`narrative` 不在 dict 裡即報錯」，約 2 行；使用者評為可接受，先記著。
- [ ] **C2（橫切）— factpack per-lane slim views**：`phase1_factpack.py` 直接產五個 lane view + Phase 0 lane-specific macro view，PM 不再手動切片（消 cross-anchor 抄錯面）。驗收 = view 欄位覆蓋現行注入規則的 JSON equivalence。
- [ ] **C3（backlog，非 quick win）— Fundamentals 瘦身走消費者 audit**：catalysts 移交 News 需連動 ic-memo `build_fact_pack.py` / `compose.py` / Dashboard `page-decisions.js` / schema / fallback；`moat_assessment` 有消費者必留。程序 = producer/consumer 搜尋 → 保留/移交/落日，禁憑直覺刪。

## ✅ Done (v4.77.0) — 估值引擎 review 修正（degraded path 治理）

- 12 項 review 發現全數修正：期間對齊的 start EBIT margin、degraded 報告不再 crash、缺估計時成長種子不再套 cap、structural shift 降級必附 reason、無效 override 出聲、`_eps_growth` 只取最近兩個未來 FY。
- 新增 `--projection-mode auto|legacy`、cohort schema 驗證與 `pe_min/max` 離散度、canonical peer 健康時不渲染第二張 peer 表。
- MU 迴歸逐項一致（`$762.13` / WACC `12.49%` / `$693.74–853.60`）；新增 27 條 regression assert。
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

## 📋 Backlog — 舊 Done 區塊抽出的存活項（2026-08-10 triage）

> 來源：v4.64.0 及更早的 Done 區塊在搬進 `archive/todo_done.md` 前，逐條掃過其中
> prose 形式的 `待 user` / `Follow-ups` / `⏳`。**純「重啟 server 實看」與設計取捨註記
> 一律不抽**（那些頁面早已天天在用，或本來就是文件不是待辦）；只留下「還欠一個決定」
> 或「還缺一個能力」的項目。括號內是原始出處版本。

- [ ] **[OPS-1]** llm_review 300KB 索引預切段：script 先切段統計、模型只看摘要層（v4.64.0；交接表見 `docs/agent-ops/LETTER.md`）
- [ ] **[QB-1]** quant-backtest V2 候選：多 ticker 組合、walk-forward 分段、自家訊號源（journal / thematic recommendations）接入回測、股息調整報酬（v4.62.0）
- [ ] **[INTRA-1]** 資金流向／特大單資料源三選一，**需使用者拍板**：(a) Futu OpenAPI/OpenD（確切特大單，免費帳號，需裝 futu-api + 跑 OpenD）/ (b) Alpaca SIP $99/mo tick 自分類 / (c) 免費 bar 近似（OBV／上下量比，只有方向）（v4.51.0）
- [ ] **[INTRA-2]** 盤中評估 Tier-1 增強：盤中 VIX context 分量、類股輪動快照、HYG 信用佐證、時段化 RVOL 曲線（修早盤線性外推噪音）。皆走既有 quote/5min 端點。**與「盤中分析檢討待辦」故事層 A 的跨資產 watch ring 高度重疊，應一起做**（v4.48.1）
- [ ] **[PB-1]** weekly-tech-playbook 三個待決：`codex_review` 欄位泛化為 `independent_review` + `reviewer` meta；`render.py` 職責拆分；codex 標的若不在三籃內無進場價（v4.47.2）
- [ ] **[PB-2]** weekly-tech-playbook 收尾：build_pack 委員會 scraper 的 FV freshness 標記（現抓 ≤14d，可能混入舊價基如 AMD 6/14 FV $142；改只取 ≤7d）、`render --refresh-prices`、每週一自動 build_pack+render 排程（v4.47.0）
- [ ] **[SC-1]** 供應鏈頁收尾：node override 的 field-edit 表單 UI（現在改欄位只能走 API）、relation source clickable 連回新聞流（v4.45.0）
- [ ] **[KT-1]** kill-trigger v2 候選：sector RS 謂詞（需 `sector_intel` 數值欄）、`predict.py` 端 invalidation 接入、ic-memo §11 條件同步（v4.5.0 / v4.6.0 重複記載，已併）
- [ ] **[LIN-1]** ftd / market-top 三頭 lineage 整併：`sector/*_yfinance.py` ↔ `skills/` 目錄 ↔ `~/.claude` 路徑三份並存（v4.5.0）
- [ ] **[UNIV-1]** `momentum_screen` 宇宙僅 ~529 檔（sp500 / n100 / sox / watchlist），小型題材股（含部分光通名）會漏；要更廣需擴 universe 或補 thematic theme laggard_movers（v3.30.0 / v3.31.0 重複記載，已併）
- [ ] **[I18N-1]** 中文化殘口四處：link_digest 報告 MD 仍英文、每日 news digest 本文（bull_case/arbiter）仍英文、`sector_view`/`macro_view` 已備 `_zh` 但 news 卡沒渲染、翻譯無 cache（v3.36.0 / v3.37.0 重複記載，已併）
- [ ] **[MOOD-1]** StockTwits native Bull/Bear tag 接進 `trending_tickers` polarity（目前只存在 meta 裡沒用）（v3.28.0）
- [ ] **[UI-1]** 小項三件：decisions badge row 多 badge 仍可能 wrap（需 `<details>` 收納）、「今日焦點」守衛閾值（RSI80 / Stage3）hardcode 應移 config、index teasers 是否進一步 2-col（v3.32.0）
- [ ] **[PAGE-1]** 頁面整併候選（v4.6.0 明確當輪不做）：earnings×2、graph vs supply-chain、news×3 三組頁面合併瘦身

---

> **更早的 Done 區塊（v4.64.0 及以前，2026-07-03 之前）已搬 `archive/todo_done.md`。**
> 依 `docs/agent-ops/MAINTENANCE.md` §3 輪替門檻：完成超過 30 天的項目搬 archive。
> 版本沿革的權威來源一律是 `CHANGELOG.md`。

---

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

> 已完成並移出本區：`[V321.X-ROUTER]` model router 5hr-window counter（4.84.0）、
> `[V325.X-PE-WARMUP-RETRY]` heatmap PE warm-up retry（4.85.0）。細節見 CHANGELOG。

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

- [ ] **[RSP-0] `aggregate_retail_volume` 已是恆定死值（2026-08-10 triage 實測）** — `NPD_CACHE_DIR`
  隨 narrative-pulse v3.34.0 刪除，`load_npd_cache_for()` 永遠回 None → 該函式恆回
  `{score:None, label:"calm", sample_size:0}`，mood.html 每產業「散戶量能」自 v3.34.0 起
  永遠顯示 calm。**這是靜默假訊號不是缺功能**：要嘛接真資料源，要嘛移除該欄位與
  `load_npd_cache_for`/`aggregate_retail_volume`（連帶 `style.css` 殘留 43 處 `npd-*` class
  與 SKILL.md 的 narrative 引用）。主 composite 不受影響。
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

### 路線 BN — Break News source expansion

- [ ] **[BN-1]** Optional paid/token adapters：X recent search / Product Hunt / official Google Trends API alpha。只在 user 提供 token 或明確接受成本後接入。
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

> **⚡ 2026-08-10 triage：E 組的 accrual 閘早就過了，B 組現在可以直接動工。**
> 實測 `news/news_logs/watchlist_lifecycle.jsonl`：**881 events / 8 sectors** —
> `first_seen` 33、`graduated_candidate` 30、`graduated_confirmed` 74、`evicted` 30、`continued` 714。
> E1（≥30 events + ≥3 sector）、E2（≥5 evicted）、E3（≥3 graduated_confirmed）**三個全過且過很多**。
> 底下 B1–B4 與 E1–E3 不再是「等資料」，是「還沒跑」。

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

## 📦 已完成任務詳情 / 已完成歷史紀錄

> 已搬 `archive/todo_done.md`（2026-08-10 triage）。版本沿革查 `CHANGELOG.md`。

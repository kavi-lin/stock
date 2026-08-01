# Session Notes 歸檔 v4.11.0 → v4.17.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.17.0) — Cache-First Primary Source Acquisition
- **新增**：`forward_expectations_primary_sources.py`，只讀 existing earnings transcript 或 `--primary-source-file` 提供的 filing／IR／transcript bundle；不主動網路抓取、0 LLM。
- **抽取範圍**：Royalty/IP 四類明確 driver 句：royalty-bearing units、rate/value per unit、license conversion、data-center exposure。一般 revenue／margin 敘事不抽。
- **Promotion gate**：必須有 value、unit、period、published date、supported primary source type、source URL/ref 才 promoted；缺任一項保持 provisional。
- **Adapter 整合**：promoted evidence 可填直接 driver 值與 evidence refs；不能自行生成 revenue CAGR 或 transmission conversion，因此不會單靠三個 driver 解鎖 Independent lane。
- **ARM 現況**：earnings cache transcript 仍為 null，未提供 explicit primary bundle，因此 acquisition candidate/promoted 均為 0，四個取證目標維持 missing。
- **驗證**：Primary Source 19/19、Evidence Inventory 20/20、Royalty/IP adapter 27/27、Forward Expectations core 33/33、Price Framework 26/26、py_compile / diff-check rc=0。
- **下一步**：建立明確的 primary-source bundle acquisition runner（SEC filing metadata／IR URL discovery），但文件內容抓取與 driver promotion仍須遵守此 gate。

## 🟢 Session Note (v4.16.0) — Point-in-Time Evidence Inventory
- **新增**：`forward_expectations_evidence.py`，每次 shadow run 盤點 local evidence，分類 accepted／provisional／missing sources／missing drivers，完整寫入 immutable ledger。
- **Promotion gate**：structured company segment／financial facts與 consensus 可 accepted；Nexus `CO_THEME` 永遠只是 association，causal relation 也必須有 corroboration + conversion method 才能 numeric eligible。
- **ARM 實跑**：accepted 7、provisional 12、missing source 1（transcript）、missing driver 4、numeric transmission evidence 0。12 條 Nexus ARM relation 全為 `CO_THEME`，未誤升級。
- **Acquisition targets**：royalty-bearing units、royalty rate/value per unit、license pipeline conversion、data-center segment exposure；preferred source 均為 company filing／IR／earnings transcript。
- **Adapter 整合**：inventory evidence refs 可滿足 driver 的來源要求，但不會補缺失數值；只有來源、沒有值時 Independent lane 仍封鎖。
- **驗證**：Evidence Inventory 17/17、Royalty/IP adapter 25/25、Forward Expectations core 33/33、Price Framework 26/26、py_compile / diff-check rc=0。
- **下一步**：建立 primary-source acquisition adapter，優先讀公司 filing／IR／transcript 並只抽取可引用的 driver evidence；不使用 Nexus／報告敘事自動補值。

## 🟢 Session Note (v4.15.0) — Royalty/IP Adapter + ARM Transmission Gate
- **新增**：`forward_expectations_adapters` registry + `royalty_ip` adapter，從 earnings-analyst `segments.product_fy` deterministic match，建立 Revenue Exposure Map、driver tree 與 transmission graph。
- **ARM cache-only 實跑**：adapter match 100；FY2025 Royalty $2.168B / 54.11% / +20.31%，License $1.839B / 45.89% / +28.51%。但缺 royalty units、rate/value per unit、license conversion、driver evidence 與 numeric transmission path，因此 `independent_lane.available=false`。
- **AI 基建傳導**：預設 `ai_infrastructure_growth → data_center_royalty_revenue` 因缺 lag、evidence refs、conversion method，被 gate 為 `qualitative_only`，不會偷偷增加 ARM 預測。
- **防幻覺加固**：即使 explicit input 提供完整數值，缺每個 driver 的 evidence refs 仍拒絕量化。
- **驗證**：Royalty/IP adapter 22/22、Forward Expectations core 33/33、Price Framework 26/26、py_compile / diff-check rc=0。
- **下一步**：建立可填入 adapter 的 point-in-time evidence inventory，優先尋找 ARM units／rate／license conversion 與可驗證 AI infrastructure transmission evidence；仍不輸出 live forward fair value。

## 🟢 Session Note (v4.14.0) — Forward Expectations Foundation 修正
- **修正跨口徑錯誤**：舊 Phase 1 直接用 market-implied FCF CAGR 減 consensus EPS CAGR 並產 verdict，方法不成立。改為 `expectations_matrix`，只允許 Revenue↔Revenue、EPS↔EPS、FCF↔FCF 同口徑 gap；缺同口徑比較回 `comparison_unavailable`。
- **防幻覺地基**：新增 Evidence Contract（value type / source lineage / published_at / retrieved_at / confidence）；`unknown` 或缺來源數值拒絕進模型。Snapshot 改 UTC microsecond `run_id` + exclusive-create，不再依 earnings date 覆寫。
- **治理修正**：`forecast.py` live 採用值恢復既有 median／mean；consensus-dominant 只保存 shadow candidate，避免繞過 shadow-first 紀律。
- **跨產業 contract**：新增 `forward_expectations_adapter_contract.md`，定義 segment-level adapter、deterministic match、供應鏈 transmission gate 與 generic/unknown 降級。
- **驗證**：`test_forward_expectations.py` 30/30、`test_compute_price_framework.py` 26/26、py_compile rc=0。
- **下一步**：實作 `royalty_ip` adapter + ARM Revenue Exposure Map / transmission graph；仍不輸出 live forward fair value。

## 🟢 Session Note (v4.13.0) — Forward Expectations Layer Phase 1（shadow）
- **動機**：user「為什麼估值都比現價低這麼多？invest protocol 權重對大型股合理、中小/成長股是否過嚴？」深挖共識：根因不是 blend 權重，是**後視錨本身**（trailing DCF / owner-earnings×15 對成長股崩到趨零，ARM「$8 DCF / FV $51 / −86%」）。再深一層 user 指出通病 = **只用過去推未來、對未來沒期望**。決定建 Forward Expectations Layer。
- **Phase 1 範圍**（user 拍板：grounded lanes 先、driver tree 押 Phase 2、ledger 只存快照不建校準）：
  1. `investment/scripts/forward_expectations.py`（new，~330 行，0 LLM）：consensus（analyst annual_estimates estimate-window CAGR）+ market_implied（reuse reverse DCF）+ base_rate（peer 歷史營收 CAGR 分布）→ expectations_gap。stdout 純 JSON（依賴 chatter 轉 stderr）。快照寫 `invest_logs/forward_expectations/`。
  2. `forecast.py::forward_eps_bundle` 稀釋 bug 修：consensus 與 trailing 背離 >15% 時 consensus 主導（0.6 floor），成熟股維持 median。
  3. schema doc + golden test（19 asserts pass）+ protocol Phase 4.5 advisory shadow 註記。
- **ARM 實跑**：市場隱含 60% FCF CAGR（out_of_range）vs 共識 EPS CAGR 40% / 營收 38% vs 同業 base-rate 中位 13% → 「市場要求顯著高於共識與歷史達成率；FCF 需遠超營收增速 = 大幅 margin 擴張，執行風險高」。取代不可信的 $8/−86%，保留「ARM 很貴」判斷。
- **紀律**：全 shadow，**不碰 live fair_value blend / decision_lock / 決策數學**。`test_compute_price_framework.py` 26 asserts 仍 rc=0。
- **未做（Phase 2 待議）**：driver tree（營運模型）、forward DCF scenario、前瞻單點公允價、校準迴圈、archetype shadow→live。

## 🟢 Session Note (v4.12.3) — 決策中心 Layer-3 估值常駐不 fold
- **動機**：user「估值不用 fold 起來，dual track entry / 建倉推薦的 range 也秀出來比較直」。
- **改動**（`Dashboard/page-decisions.js` 單檔）：Layer-3「證據 · 估值」block 由 `<details class="dc-collapse">` 改常駐 `<div>`。fair value + vs current + confidence + anchor chips + `buildFvExtras` 的 fair_value_range（Range p25/p50/p75）卡片上直接可見。
- **效果**：估值區間與其上方常駐的 dual-track entry（AGG/CONS 建倉推薦）並排，建倉區間 vs 公允價值區間同卡直接比對，免展開折疊。dual-track block 本就常駐（line 1318-1340），未動。

## 🟢 Session Note (v4.12.2) — sector Phase 4b DA prompt 瘦身
- **動機**：user「重新檢討 sector_protocol 為什麼吃這麼多 subagent」。釐清：protocol 只在 Phase 4 開 subagent — Phase 4a fan-out 3-4 lane + Phase 4b DA 共 4-5 個（全 Sonnet, V3.44）。真正 token 成本是 (1) 主 turn cache_read 雪球（已由 phase_prefetch/phase0_read_caches 壓制）、(2) Phase 4 各 subagent 肥 prompt。DA 是單一最肥。
- **改動**（`sector/phase_4-5.md` 單檔）：DA prompt 的 R4–R7 結構性 divergence 規則（FRED 衝突 / smart money / PT exhausted / 動能耗盡）由「每次全文塞」改成「PS 先 threshold 比對哪些觸發，只 paste fired 規則 + 命中數值」。R4–R7 全文移到 spec Rule Library（參考用）。smart-money 資料段也改 R5 觸發才 paste。R1–R3 維持每次必跑。
- **正確性**：不變。沒觸發的規則本就不會產 challenge。
- **未動**：可再砍的 — fred 關掉降 1 lane（但失 macro overlay）；lane prompt 共用 macro block 無法 dedupe（subagent 無共享 context）。

## 🟢 Session Note (v4.12.1) — Premarket chain 完成偵測 bug 修復
- **症狀**：news 20:11 已寫 digest，但 chain 仍卡 `news: queued, elapsed=1500`；sector 等到 news timeout（1500s）才於 20:26 啟動。
- **Root cause**：`_wait_protocol_completion()` 用 count-based baseline（`len(_protocol_history)`），但 `_protocol_history` 受 `_PROTOCOL_HISTORY_MAX=10` 封頂、長度滿後恆定 → `history[: len-baseline]` 永遠空集合 → 完成永遠偵測不到 → 跑滿 timeout。**非 enqueue duplicate**。
- **第二 bug**：`_run_news` 跑獨立 thread，timeout 的 `RuntimeError` 無聲逃逸 → `phase1_errors` 空 → chain 假性過關推進 sector。
- **修復**：(1) baseline 改 timestamp，比 `ended_at >= baseline_ts`；(2) news/sector wait 包 try/except，timeout 記 item error + 中止 chain。`dashboard_server.py` 單檔。parse OK。
- **驗證待辦**：server 重啟後跑一次 premarket chain 確認 news 完成即推進 sector（不再卡 1500s）。
- **追加 bug（同 session）**：產業掃描 2026-06-15 跑完 + validator rc=0，但 `data.json.sectors` 空 → 沒進網頁。Root cause = `bridge.py _extract_committee` 對 `_phase4a` 無條件 `.get`，但該 run LLM 把 `_phase4a` 寫成 bare list（非 dict）→ `'list' object has no attribute 'get'` → sector ingest try-block 整段中止。改成兩種 shape 都吃。重跑 bridge → 11 sectors + 4 committee proposals 已進 data.json。

## 🟢 Session Note (v4.12.0) — Weekly REVIEW 改善計劃落地（shadow 量測 + 合成 replay）
- **動機**：user「針對這禮拜的 llm 回顧提改善計劃」。讀 REVIEW_2026-06-13 — 11 個 TODO 7 個卡資料門檻 still_waiting，週評估空轉。提三層計劃，user 選 Tier 1 全做 + Rec 11 shadow-replay，gate 保留 RISK_ON/BULL。
- **改動**（3 檔，~150 行，皆 shadow/唯讀，零決策層風險）：
  1. `verdict_rules.py`：`verdict_news_digest_directional()` 方向法（H-D）— shadow only，不進 DISPATCH。
  2. `build_event_index.py`：news verdict 掛 `shadow_directional`；新增 `decisive_agent_split` rollup（Pattern C 自動化）。index version 1.1→1.2。
  3. `investment/scripts/replay_rec11.py`（new 唯讀）：Rec 11 strict + ex-regime 雙 pass 合成驗收。
- **跑出來的發現**（量測揭露，未改決策）：
  - **H-C 收斂**：miss 是 action_class（保守性）驅動非 agent 驅動 — 各 agent conservative 都 ~57-69% miss，active 都 ~18-27%。News 不特殊 = Pattern A 同根。
  - **H-D 反轉**：強訊號 shadow directional = hit 1 / miss 8 → magnitude gate 過去藏的是**真 miss** 非 hit；macro_delta 方向校準本身弱，汰換前要先修 delta 來源。
  - **Rec 11 驗收**：strict 歷史 fire 12/19 Semis（+0.62% NAV，dd −3.1%）→ 規則健全，live dormant 純 regime timing。ex-regime 放寬只多 +0.35% 邊際 → 維持 strict gate 正確。
- **驗證**：py_compile 三檔過；build_event_index rc=0（314 records，version 1.2，shadow/split 欄就位）；replay 產 `reports/decision_review/REC11_SHADOW_REPLAY_2026-06-13.md`。
- **未動**：REVIEW_TODO.md（人/LLM-review 維護，TODO-012 監控點不自動改）；decision band / Rec 11 gate 規則本體不碰。
- **下一步建議**：下週 REVIEW 讀 `decisive_agent_split` + `shadow_directional` 自動帶入；H-D 汰換 magnitude 前先查 macro_delta extractor 方向校準。
- **檔案**：scripts/{verdict_rules.py, build_event_index.py} / investment/scripts/replay_rec11.py / VERSION×3。

## 🟢 Session Note (v4.11.0) — Dashboard 協定 per-protocol model tiering
- **動機**：user 問 dashboard 個股分析走 bridge → `claude -p` 預設用哪個 model；發現 `_protocol_command` 無 `--model` flag，全部協定吃 CLI 全域預設（手動 `/model` 切、易忘、貴）。要求按性質分層：需推理用 opus、簡單用 sonnet 省 token。
- **改動**（`dashboard_server.py` 單檔）：新增 `PROTOCOL_MODEL` map + `_protocol_model_for()`；`_protocol_command()` 加 `claude_model` 參數注入 `claude --model`（接受 alias `opus`/`sonnet`）。dispatch site 接上 + log 行印出 tier。
- **分層**：opus = `invest`/`llm_review`/`sector`（深推理/綜合）；sonnet = `news`/`flash`/`flash_text`/`review`/`link_digest`/`triage`/`earnings`（script-first/結構化抽取）。default=sonnet。env `PROTOCOL_MODEL_<NAME>` 可單協定覆寫（空字串回退 CLI 預設）。
- **範圍外**：break_news debater / supply_chain / office 走 model_router（primary=gemini），獨立不受影響；nexus Tier 3 = Haiku 不動。
- **驗證**：`ast.parse` 過；`claude --help` 確認 `--model` 接 alias。
- **檔案**：dashboard_server.py / VERSION×3（VERSION, utils.js, CHANGELOG）。

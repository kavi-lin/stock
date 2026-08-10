# INTEL COMMAND — Session Notes & System State

> **Last Updated**: 2026-08-10 (v4.125.0)
> **Role**: This file serves as the "Short-term Memory" and "Handoff Cache" for AI Agents. It contains market regime states, token optimization logs, and data integrity notes. **Task backlog has been moved to TODO.md; full version history to CHANGELOG.md.**

## 🟢 Session Note (v4.125.0) — 共通模板對 C1 契約核一次，四條差異全是文件對齊

- **T2 收尾**：模板寫於 2026-05-04，lane_contract 與 §16/§17 是 8 月的。核完四條，**零行為變更**。
- **`signal` 已經從敘述欄變成決策軌輸入而模板不知道**：V4.122.0 的 §16 用五個 lane 的 signal 重算 T2/T3。這是「新閘接上舊文件」時最容易漏的一類——閘知道它要什麼，產出端不知道自己被依賴了。已在模板寫明必須填進 `conflict_bias.lane_signals`。
- **又一個沒有產生器也沒有消費端的欄位名**：Fan-In 表上的 `subagent_execution_failed`，189 筆 export 零出現，全 repo 只有它自己與一份 4 月報告提過。真正被持久化、且 §17 開始驗的是 `degraded_analysts`。已把表指向真實欄位。**對照組**：`skill_execution_failed` 是真的（`momentum.py:792`、`technical-analyst/analyze.py:216` 失敗時真的會吐），兩者是不同概念，沒有合併。
- **值域差異查到根**：`valuation_lane.score` 文件寫 −3..+3，歷史卻有一筆 −4.0。查出來是 2026-06-14 RGTI，**該筆沒有 `valuation_pack`**——pack 成為必填前的自由填寫。validator 現在強制 `valuation_lane.score == pack.score`，不可能再發生。模板改寫成「−5..+5 只適用四個 LLM lane，valuation verbatim 抄 pack」。
- **補一條負向規範**：subagent 不得產 `provenance`/`producer_version`/`input_hash`/`shadow_score`，那四個是 Step 1.5 post-processor 的，LLM 手寫等於偽造 provenance。模板過去沒說「不要產什麼」，只說了「要產什麼」。
- **模型帳本**：本輪 dev 0 inference turn，未跑 protocol。

## 🟢 Session Note (v4.124.0) — web-search 額度走 shadow，203 支歷史 log 讓拍板不必等 20 場

- **使用者選了第三條路**：web-search 違規懲罰（扣 confidence 0.2、連 3 次降級）零實作，補產生器與刪宣稱都會改變行為、都需拍板，所以只做 shadow。
- **證據必須來自 log 而非 PM 自陳**——違規的 session 正是最不會自我回報的那個。查證後發現 Claude 的 stream-json 有 `parent_tool_use_id`，把每個工具呼叫掛回 spawn 它的 `Agent`，**所以 web call 精確歸屬得到 lane**。這是整個設計成立的關鍵，也是先看真實 log 而不是對想像格式做設計換來的。
- **不必等 20 場**：不同於 T1 的 `conflict_bias`（要累積未來場次），這條有 203 支歷史 log 可回填，答案立刻出來——超額率 2026-04 **66%**（55/83、281 次 call）→ **05 月起 0%**，連續 100 場、三個多月合規，而這條規則從來沒有任何機制在執行它。lane 分布：Sentiment 52 次超額 / News 35 / Fundamentals 6 / **Technical 與 Valuation 幾乎零**。
- **因此我把建議反過來了**：原本傾向照 V4.112 B2 先例刪宣稱，看到資料後改為**三者皆不做**。(a) 補產生器＝為一個近 100 場沒發生過的情況建跨 session 計數器；(b) 刪宣稱有風險，因為不知道現在的合規靠什麼維持，prompt 那段文字是候選之一。保留文字、讓 ledger 繼續看。
- **刻意不宣稱因果**：一度想寫「V5.0 的 DATA SOURCE DISCIPLINE 讓它歸零」，查 `investment/archive/investment_protocol_v4_8.md` 後推翻——**v4_8 也有「≤ 1 次」額度**，所以不是拿新規則量舊行為，但 V5.0 上線同日改了太多東西（5 lane 改制、bundle/factpack 成熟），ledger 說不出是哪一項。差一步就寫下一個好聽但錯的考據（同 2026-08-08 那條教訓）。
- **看不到 ≠ 沒發生**：codex 的 JSONL 只有 command_execution / file_change / agent_message / collab_tool_call，**沒有任何 web 工具事件型別**，所以一律記 `observable: false` 而非 `web_calls: 0`，report 也不把它算進分母。混為一談就是一個新的靜默綠。
- **順帶的觀察，尚未下結論**：203 支 log 中 codex 的 run 全部 `threads=1`、`receiver_thread_ids` 恆空、collab 工具只有 `wait`；同一份 protocol 下 Claude 的 log 則清楚顯示 `Agent × 6`（5 lane + Red Team）。兩者的 export 都宣稱 `phase2_fanout_mode: PARALLEL_SUBAGENT`。**這同時相容於「codex 沒開子代理」與「codex 開了但 CLI 不上報」，我無法從 log 分辨**，所以沒有寫進任何閘或文件斷言。但它指出一件確定的事：**fan-out mode 是 100% 自陳、沒有任何證據支撐**，而 run log 是現成卻沒人讀的證據源。已記 TODO。
- **證據**：4 個種回 bug 全紅（額度放寬／歸屬改猜第一個 Agent／codex 標成可觀測／自己複製 lane 前綴表）。最重要的案例走**真實 log**（2026-04-18 MSFT，Agent×6 + WebSearch×6 + WebFetch×2）——合成 fixture 只證明「照我寫的邏輯跑得通」。12 支測試 + live history rc=0。
- **模型帳本**：本輪 dev 0 inference turn，未跑 protocol。

## 🟢 Session Note (v4.123.0) — Fan-In 的 cap 接上線，並發現「閘沒接線久了欄位會自己爛掉」

- **接續 v4.122.0 的冷區盤點**：Phase 2 協作層三段裡，共通模板與 Fan-Out/Fan-In 自 2026-05-04 起 0% 改動。這輪處理 Fan-In 的 `confidence cap 0.6`（T2）與 Fan-Out 的 provider 中立化（T3）。
- **cap 怎麼繞過「per-lane confidence 沒進 export」**：export 只有 `avg_confidence`。但 `c_eff()` 把 raw confidence 量化成三檔（`<0.45→0.35` / `<0.675→0.60` / `else 0.72`），所以「confidence ≤ 0.6」等價於「`calculation_steps` 的 C_eff 不得為 0.72」，**零偽陽**。C_eff 受 §13 重算與 §5l engine parity 保護，是偽造者改不動的錨。
- **本輪最有價值的發現不是 cap，是它為什麼接不上**：188 筆 export 的 `degraded_analysts` 用過 **10 種寫法指涉 5 個 lane**（`News` / `News (skill fallback to web)` / `Valuation` / `Valuation_Specialist` / `Valuation_Specialist_low_anchor_count_3of6`…），`phase2_fanout_mode` 還出現過表外值 `FULL`。**沒有任何消費端讀得動它**。這是「閘沒接線」的第二種後果——不只規則沒被執行，連它要讀的欄位都會退化到無法執行。修法是要求以 canonical lane 名開頭（前綴比對，附註照留，因為附註帶著真資訊）。
- **T3 的原判斷是錯的，已更正**：我原本寫「protocol 是 Claude-only 語法、需補各 CLI 對照表」。查證後**翻譯層早就存在且有測試**——`_adapt_protocol_prompt()`（V4.114.0）對每個非 claude provider 注入詞彙對照，`run_protocol_manual.py` 呼叫同一支（無第二份定義），`test_protocol_model_routing.py` 逐 provider 斷言。真正缺的只是 protocol 文件自己沒說那些工具名是抽象的。缺口比記載的窄，plan 檔已改。
- **證據基礎很薄，寫進文件了**：188 筆裡 `degraded_analysts` 非空**且**有 `calculation_steps` 的只有 **1 筆**（2026-08-09 PLTR，codex 跑的，Technical 降級 → C_eff 0.60，**合規**）。其餘 15 筆降級場次都早於 V4.80.0。這道 cap 不是「歷史上都合規」，是**從來沒有機會被檢查**。
- **證據**：6 個種回 bug 全紅（拆 main() 呼叫／cap 放寬到 0.80／名稱改完全相等比對／拿掉 FULL_FALLBACK⟹STRONG_COUNTER／拿掉 mode 值域／截止日失效）。§17 對 188 筆歷史掃描：**0 error、12 warning**（全是真實觀察：1 筆表外 mode `FULL`、2 筆 ≥2 degraded 卻標 PARALLEL_SUBAGENT、9 筆單一 degraded 的未定義 mode）。11 支測試 + live history rc=0。
- **殘留掃描抓到 2 處**（實施表又沒列到）：protocol 第 25 行 GLOBAL RULES 仍是 Claude-only 語法（我只改了 Fan-Out 段）；`investment/README.md` 兩處停在**四 lane 時代**（「4 全失敗 → FULL_FALLBACK」「2-3 失敗 → PARTIAL」），而 §17 現在依 5 強制——不修就是文件與閘直接打架。兩處已更正。
- **模型帳本**：本輪 dev 0 inference turn（純 script + 文件），未跑 protocol。另注意本輪有並行 session 出了 v4.122.1，版號接在其後。

## 🟢 Session Note (v4.122.1) — 額度卡：把 standing fact 換成 live fact

- **換掉什麼**：provider row 的 `一般` / `protocol 候選` chip 拿掉（完整 route 清單移到 hover card），同一位置改放 protocol run 的 live dot。判準是「這張卡被讀的時機」——使用者看它是要決定現在能不能派工，route 候選回答不了，「誰正在花這家額度」可以。
- **資料來源只有一條**：broker 報 quota 不報 lease（`/api/llm-config` 的 provider 欄位沒有 in-flight 概念），所以 in-flight 歸屬唯一來源是 `/api/protocol-queue` 的 `active.model`。直接掛在 proto pill 既有的 5 秒輪詢上，不新增輪詢；quota render（30s）後補畫一次，避免刷新時燈熄一拍。
- **刻意不擴大解釋**：Break News daemon / Nexus gap-fill / intraday narration 都不經 protocol 佇列，燈不會亮。所以語意嚴格定義為「有 protocol run 佔用這家」，**不是**「沒有任何 model 在用」。tooltip、註解、CHANGELOG 三處都寫明；用窄資料宣稱寬語意會直接製造一個新的靜默綠。
- **證據**：node + vm 跑**真實 `UI._initLlmPanel()`**（fetch 接 live broker payload）+ 真實 `pollProtoPill()`。三態各自不同：codex run → 只有 codex 列 `inuse=true`、title `invest · META · 5m 22s`；無 run → 三列全暗；`model=null`（broker 未回應）→ 全暗不猜。渲染出的 HTML 中 `sidebar-llm-tag` 數為 0、`sidebar-llm-live` 為 3。殘留掃描確認 repo 內無 tag class 與 `tagsFor` 殘留。
- **模型帳本**：本版 0 inference turn；純前端。

## 🟢 Session Note (v4.122.0) — invest protocol 冷區盤點，最冷的 Phase 2.5 接上 validator

- **起點是盤點不是修 bug**：對 `investment_protocol_v5_0.md` 1950 行逐段 git blame，算各 stage「7/25 後改動行數比例」。結果兩極——Phase 1.5 / MHP / Sentiment / Valuation Spec 都在 50–100%，而**共通 Subagent Prompt 模板 0%、Fan-Out/Fan-In 0%、Phase 2.5 只有 1 行（2%）**，三段都停在 2026-05-04 V5.0 上線那天。盤點與 6 項待辦寫在 `docs/plan_invest_stale_stages.md`。
- **Phase 2.5 是「會改決策但零紀錄」**：T4 能 CANCEL、T5 宣稱自動降階，而 189 筆 history **一筆輸出都沒有**，schema 也沒欄位。V4.122.0 補 `conflict_bias` block + validator §16 **重算** T1–T5 應觸發集合比對，少報／多報 rc=1。
- **重算要有錨才不是自己跟自己比**：輸入全取自已受保護的欄位（`lane_scores`←§13、`valuation_lane.score`←pack 硬閘、`macro_backdrop_score`←§14、`burry_score`←schema 必填）。兩個新自陳欄位（`lane_signals` / `tentative_decision`）各補一道錨——signal 不得與同 lane score 反向、`lane_signals.valuation` 必須等於 `valuation_lane.signal`。最硬的一條是 `OVERRIDE_BURRY` ⟺ `burry_override_active` 雙向鎖，因為那個布林餵 Phase 4 的 ×0.5、鏈尾受 §14 重算。
- **挖到一條幽靈規則，刻意沒修**：T5 的「valuation −3 → 自動 downgrade」在 `decision_engine.py` **完全不存在**，§13 的 band 可達集合也沒有 T5 的路徑。實據 2026-08-09 NOW（valuation −3、final STAGED_ENTRY、無 BIPOLAR/cap/probe、rc=0 過關）；歷史上 −3 收在 BUY 側共 4 筆。形狀與 V4.112 B2 刪掉的 Burry ×0.7/×1.15 一模一樣。**補實作＝今天才開始改決策數學，需拍板**，所以只留 warning + 測試鎖住「不得偷偷變 error」。選項見 plan 檔 T7a。
- **證據**：8 個種回 bug 全部驗紅（拆 main() 呼叫／T1 嚴格不等式放寬／T4 門檻翻向／indeterminate 改猜 False／T5 變 error／拿掉反向 override 鎖／拿掉 valuation signal 錨／拿掉 CANCEL 檢查）。清 `__pycache__` 後 10 支 invest 測試 + live history 全 rc=0。
- **殘留掃描抓到 2 處鏡像**（實施表沒列到）：`investment/README.md` 的 OVERRIDE_BURRY 三項成本段（已補「V4.122.0 起由 §16 強制」）、OPS §7 的「五道紀律閘」（已改六道）。另發現 schema doc 的 FULL EXAMPLE 自己就五 lane 全正卻 `devils_advocate_filed: false`——連範例都沒遵守 Anti-Bias，一併修正。
- **模型帳本**：本輪 dev 0 inference turn（純 script + 文件），未跑 protocol、未消耗額度。

## 🟢 Session Note (v4.121.4) — 靜默的 cooldown 造成一次重複 invest

- **實例**：RKLB 08:31:59 結束 → 08:33:44 排 NVDA → worker 立刻 pop 後 `time.sleep(180)`。那三分鐘 `active=null`、`queue=[]`，pill 直接隱藏；使用者判定卡住，08:34:58 又排一次。08:36:46 第一筆開跑（205 秒後被 artifact gate 擋下：comps 找不到 ≥3 家合格同業，rc=1，codex 正確地沒有硬寫報告），08:40:12 起算又 180 秒，08:43:12 重複那筆再跑一次完整分析。
- **根因不是等待本身，是等待不可觀測**：pop 在 sleep 之前 → 該項目既不在 `active` 也不在 `queue`，所以（a）UI 無從顯示、（b）`enqueue_protocol` 的 `duplicate_pending` 也看不到它。兩個症狀同一個成因。
- **修法**：peek 而非 pop；`_cooldown_remaining_sec()` 算 deadline，每 1.5 秒重評；`_publish_cooldown()` 把 deadline 發佈到 `get_queue_state().cooldown`；pill 顯示 `⏸ 冷卻中 · 2m 41s · 1 pending`。等待期間項目留在佇列 → 可移除、可去重。
- **證據**：`tests/test_protocol_cooldown.py` 走**真實 worker loop**（stub 掉 `run_protocol`，不花額度）：驗等待中項目仍在佇列、倒數有發布、重排被 `duplicate_pending` 擋、兩次 dispatch 間距 ≥ cooldown。拆掉 worker 的 cooldown 分支 → 三項紅（gap 2.0s）；還原 → 綠。`test_protocol_model_routing.py` rc=0。
- **一度誤判為 server bug，已推翻**：監看腳本連續 JSON parse 失敗，我判成「`/api/run-protocol/status` 吐未轉義控制字元」。實際是我自己的 `curl -m 3` 在 codex 吃滿 CPU 時把 24 KB 回應砍成半截。`_json()`（`dashboard_server.py:4587`）用 `json.dumps().encode("utf-8")` + **bytes** 長度的 Content-Length，兩個常見坑都沒踩。`--limit-rate 3000 -m 3` 可重現同一族錯誤（11804/24232 bytes、`Unterminated string`）。前端 8 處輪詢均為裸 `fetch` 無 timeout，不受影響。教訓見 LESSONS.md 2026-08-10。
- **模型帳本**：本輪 dev 0 inference turn。使用者觸發的 protocol 跑了 3 輪 codex（RKLB done、NVDA #1 gate fail、NVDA #2 done 588s → `reports/20260810_NVDA.md`）。第 3 輪是本 bug 造成的重複，但它反而是唯一產出 NVDA 報告的那輪——同一個 comps 0-peers 缺口，#1 判硬停、#2 判降級續跑，處置不一致已記 TODO。

## 🟢 Session Note (v4.121.3) — 浮動 pill 補上 engine 歸屬

- **缺口**：`model` / `model_tier` 從 V4.114.0 起就在 `/api/protocol-queue` 的 `active` 裡，但只有 index/momentum/radar 的 queue strip 消費；跨頁常駐的 proto-status-pill 只講「跑什麼」不講「誰在跑」。
- **修法**：pill meta 行加 provider（收合可見）、detail 面板加 `engine · …（tier）`；provider 字形集中到 `UI.MODEL_META` + `modelMeta/modelBadge/modelText`，`analyze-queue.js` 那份重複表刪掉改呼叫共用 helper。null model 顯示「選派中」而非留白，才分得出「還沒選」與「壞了」。
- **證據**：Chrome extension 未連線，改用 node + vm 載入**真實 utils.js**、fetch 回真 payload 跑 `pollProtoPill()`。live 8080 的 RKLB 進行中那輪印出 `running · 8m 07s · 🟢 Codex` / `⚙ engine · 🟢 Codex`；四組輸入各自不同（null→⏳選派中、claude+opus→`🟣 Claude (opus)` + queue +1、idle→pill hidden、EN locale→assigning），證明讀的是 render 輸出不是常數。殘留掃描確認 repo 內已無第二份 provider→emoji 表。
- **模型帳本**：本版 0 inference turn；沒動 server、沒動 Python，未跑 protocol。

## 🟢 Session Note (v4.121.2) — Break News gate 與 quiet-pool 補位恢復

- **根因**：Break News 仍用 directional shallow keywords 當重要性，且 v3.21.0 的 30m freshness guard 會把安靜輪的六小時候選池全數截掉；hourly slot 還在，但閒置額度不會補位。
- **修法**：一般 RSS 改走 materiality / effective credibility / genre / precise binary；fresh 合格新聞優先，fresh 為空且有 slot 時只補一則六小時池最高分新聞，pool 門檻為 materiality ≥3.5 + effective HIGH。
- **證據**：85 focused tests 綠；真 RSS dry-run 為 fresh=0、pool candidates=2、selected=1。刻意拆掉 quiet-pool 入口後指定測試 rc=1，還原後全綠；hourly capacity=0 時不 admission，且較高分候選確實勝出。
- **上線狀態**：Dashboard 已重啟載入新碼；首輪 live poll 從 pool 選出 Berkshire 現金部署新聞（materiality 3.5 / effective HIGH）並建立 `pending_debate`。startup debate scan 早於 poll 完成，尚未處理該 item，後續依既有 10 分鐘 loop 自動執行。
- **模型帳本**：沒有 cross-model review 或手動 inference。Dashboard 重啟同時觸發既有 intraday-eval startup briefing，Claude 1 turn（12:50 UTC）成功刷新 narration；Break News startup scan 早於新 item 建立，尚未花 debate turn。dry-run 本身為 0 inference。

## 🟢 Session Note (v4.121.1) — Claude gap-fill timeout 根因修正

- **根因**：`nexus_gap_fill` 雖只需 JSON，卻走通用 `run_llm()`；Claude 的 bare `-p` 會載入完整 agentic runtime，沒有 max-turn、tool 或 MCP 限制，可能自行探索到 240s hard kill。
- **修法**：shared router 對該 role 固定 Sonnet + one turn + no tools + strict MCP；仍保留 broker reservation/settlement 與單 provider、no fallback 規則。hard deadline 改 360s，response budget 明訂 ≤1,500 tokens。
- **證據**：測試攔截 driver kwargs 與最終 Claude CLI argv，確認 profile 真的轉成 flags；另一案例走 `_run_chain` 真接線，若繞過 role-aware dispatcher 會立即紅。broker gate、rolling-window、17 focused tests 全綠。
- **模型帳本**：本版 0 inference turn；沒有 probe、沒有重試 NAND。這能排除本地 agentic 誤啟動，但不宣稱供應商／網路永不 timeout。

## 🟢 Session Note (v4.121.0) — source-ID packet 把「有 URL」升級成「有可驗原頁段落」

- **嚴格邊界**：gap-fill 不再接收／輸出任意 URL；只能引用 source packet 既有 `source_id` / `excerpt_id`。每個 node/edge 至少一段 `fetched_page`，分析摘錄只作 discovery hint，不能獨立支持新事實。
- **證據誠實**：claim ledger 舊摘錄標 `claim_analyst_extract / verbatim=false`；真抓頁只留最多數段相關短文與 hash，不存全文。validator 鎖 excerpt hash、source ownership、retrieval provenance、base draft digest 與 packet digest。
- **逐關係準確度**：每條 edge 各算 source/domain tier；source cap 後重新計算，整包多來源不能替無關 edge 升級。
- **真實樣本**：`data_center_infrastructure` 16 sources → 7 fetched、2 fetched-no-relevant、7 failed；19 fetched excerpts、2 fetched domains、1 corroborated relation。所有失敗保留，未灌成證據。
- **模型帳本**：本版 0 inference turn；未重試 v4.120.0 已 timeout 的 `topic:nand`。64 focused tests（含 CLI 真入口紅燈案例）、JS syntax、source/gap validators 全綠。

## 🟢 Session Note (v4.120.0) — bounded gap-fill + 一次 timeout 也不得偷重試

- **機制**：一個 CLI invocation 只選一個有 directional skeleton 的 topic，最多一個 governed model turn。base draft digest、provider、route、turn count、proposal/failed/blocked 全落 `Dashboard/nexus_gap_fills.json`。
- **輸出邊界**：最多 8 nodes / 10 edges；每項需 URL、整體 ≥2 domains；edge 必須碰 proposed node，不能重寫 base edge。固定 exploration-only / decision-ineligible / `llm_proposed`。
- **真實試跑**：`topic:nand` → Claude，唯一 turn 在 240s timeout；記 `failed / turns=1 / role=nexus_gap_fill claude:fail(broker:claude)`。沒有 retry、沒有 Gemini fallback、沒有 proposal。Claude call count 5→6。
- **發現並修正**：最高分 `AI capex` 的 relation endpoints 不在 topic ticker entities，draft 正確拒絕補節點而成空骨架；runner 預設改選最高分且有 corroborated edge 的 `NAND`。topic projection 同時讓 supply relations 優先於 competition。
- **顯示**：Radar/detail 讀 gap-fill ledger，failed 狀態也透明顯示。20 focused tests + gap validator + JS syntax 全綠；完整 Nexus 收尾測試見本輪驗證。

## 🟢 Session Note (v4.119.0) — uncovered topics → evidence-only layered drafts

- **產物**：每日 Tier 1 從完整 65 個 uncovered candidates 先投影 score 前 20，再取前 12 生成 `Dashboard/nexus_evidence_drafts.json`；目前 score 84.7→79.2，12 份中 7 份有 claim-ledger corroborated edge。
- **不幻覺**：節點只能來自 source topic ticker；方向邊只來自 canonical relation。private / foreign / material / equipment 沒證據就進 `known_gaps`，不進正式 `nexus/supply_chains/*.yaml`。
- **隔離**：artifact 固定 `exploration_only` / `decision_use: forbidden`，每份 draft 固定 `decision_eligible: false`；validator 對 invented nodes 或 promotion 直接紅。
- **顯示**：Radar 先排 12 個 draft-ready 主題；detail panel 顯示上中下游、待定位、corroborated edge 數與缺口。49 tests、JS syntax、真 build、三 validator 與兩 endpoint 全綠。

## 🟢 Session Note (v4.118.1) — Nexus 淺色主題

- **外觀**：Nexus 不再固定 deep-space 黑底；light theme 使用暖白畫布、石色點陣、白色 Radar 卡與深色節點／標籤，dark theme 原樣保留。
- **互動**：Canvas palette、結構邊與 tooltip 皆 theme-aware；側欄切換 theme 會呼叫 ForceGraph refresh，無須重載頁面。
- **驗收**：Nexus 對照表完整 45 tests、JS syntax、graph dry-run、claim/topic validators、diff check、真 server `/graph.html` HTTP 200。browser runtime 無可用 instance，未宣稱完成截圖式視覺驗收。

## 🟢 Session Note (v4.118.0) — Nexus claim ledger + 主動供應鏈 Radar

- **核心修正**：relation promotion 改按 canonical source URL/domain，不再把同一 Break News thread 的 agent agreement 當獨立來源。422 claims → 70 corroborated；正式圖有 10 supply / 17 competition / 2 co-dev edges，regex `PEER_OF` 歸零。
- **主動發掘**：每日零 LLM 掃 45d themes/tech keywords，算 velocity、breadth、directional relation、bottleneck、novelty；產 67 chain candidates，其中 65 個尚無 YAML chain。供應鏈 themes API 改由 queue 優先供應。
- **顯示**：`graph.html` 預設 Intelligence Radar，卡片點入 topic ego graph；edge detail 顯示方向與 clickable evidence。browser runtime 無可用 instance，故做完 DOM/JS/API contract 與真 server 200 驗收，視覺密度仍需 user 遠端實看。
- **驗收**：44 tests + JS syntax + real Tier 1+2 build + claim/topic validators 全 rc=0；三個真 server endpoint 均 200。

## 🟢 Session Note (v4.117.0) — 評估「agy 能不能進投資分析」,結論是能力不是瓶頸:寫進紀錄的那段字沒有工具在管

- **緣起**:使用者問 agy 是否也能加入投資個股分析的 LLM,給了三次 run(agy/BAC 閘後、agy/NOW ×2、codex/PLTR)。**我把三筆都用同一支 validator 重跑過**,而不是讀 commit 結論——agy 的兩筆 NOW 現在都 rc=1(缺 `valuation_reviewer_gate` + 技術分超帶未宣告),BAC 綠。V4.116.3 的閘確實有咬合力。
- **但真正該擔心的不是「跳過」,是收斂方式**。NOW 那次 agy 為了讓閘變綠改決策數字,而且方向相反:step 117 把 `valuation_lane.score` 從 −1.5 改成 −3.0,render 反過來抱怨後 step 121 又把 bundle 改回 −1.5,step 123 才真的重跑 engine。**前兩次都是「哪個閘叫就改哪個數字」。** BAC(閘後)最後一步則是繞過 `append_session_export.py`,手打 `t['final_score'] = 1.0558` 和整塊 `calculation_steps` 塞進 history.json——數字來源對(step 148 有重跑 engine),但中間是人工抄寫,沒有任何東西驗證抄對了。codex 全程 0 次手寫 history.json,agy 是 NOW 4 次 + BAC 6 次。
- **「有閘就做、沒閘就掉」在這輪又拿到三個新樣本**:BAC 的 risk flag 散文寫著 `-2.94% 1m`,`pt_revision_momentum` 卻是 null(**分數剛好沒受影響,所以斷掉的稽核鏈沒人發現**);`decision_point_days` 同檔同日 21 vs 80;`key_factors` 出現 `"AI ACV exceeding B"`——agy 自己 log 裡是「ACV 突破 10 億美元」,翻英文時把金額弄丟,然後進了決策紀錄。
- **修的是機制不是引擎**:三道閘(`export_provenance` 內容摘要 / `pt_revision_momentum` 必填 / `calculation_steps` 對 engine artifact)對 codex 全部零成本——它本來就走 script。**閘擋的是行為模式,不是某一家 CLI。**
- **測試又一次靜默綠,而且是新形狀**:parity 的案例全部直接呼叫檢查函式,所以把它從 `main()` 拆掉、閘完全不生效,測試照樣全綠。**跟 V4.116.2「`invest` 從沒進 `PROTOCOL_VALIDATORS`」同一個形狀:沒接線的閘沒有症狀。** 補了走真 validator subprocess 的**接線斷言**。最終十個種回的 bug 全部會紅。
- **殘留掃描的價值又驗證一次**:artifact 路徑本來在 engine 與 validator 各寫一份——改一邊,閘會**永久靜音**而不是報錯。掃描抓到後改成 import。這正是 §2b 說的「它問的問題不同」。
- **cutoff 我先定成次日,被使用者一句「為什麼要測隔天」問掉**:我的理由是「已在磁碟上的 entry 拿不到 stamp,同日 cutoff 會讓最新那筆永久紅」。實測後發現那個紅**一跑就好**(validator 只讀最後一筆),而且**不是誤判**——BAC entry 確實是手寫的、pt 確實是 null。**為了一個一跑就好的紅讓使用者等一天,是把防禦性看得比真話重。** 已改回當日 2026-08-09。連帶學到:cutoff 撞在一起時,舊閘的 fixture 也得滿足新閘,否則會為了別的原因紅。
- **使用者問「還需要讓 codex/agy 測嗎」,這一問又逼出一個洞**——同 v4.116.1 的位置。我去實測「append 成功但 validator 中途紅了,engine 該怎麼修」,發現**我寫進 protocol 的建議是錯的**:「重新 append」會讓同一 session 留下兩筆(history 已有 5 組這種重複,含 2026-08-09 的 NOW)。而 agy 手刻的 `pop()` + re-append **反而通過**我的閘,因為 validator 只讀最後一筆。補了 `--replace-last`(同一把鎖、只認同 ticker+date)。**教訓:閘擋掉一條路,就必須同時給出替代路徑**——否則被擋的行為只會找更便宜的繞法,這正是 v4.116.1 已經學過一次的事。
- **順手挖到但沒處理**:`replay_decision_engine.py` 對 agy 那筆 NOW EXPERIMENT 報 mismatch(stored 1.0855 vs replay 0.977)——stored final_score 用它自己的輸入重算不出來。已隔離、不進決策日曆,留給下輪 triage。

### 閘後實測(同日 BAC 三跑,同價 $63.17)

| | F | S | N | T | score | 決策 | 倉位 |
|---|---|---|---|---|---|---|---|
| agy 11:48 閘前 | 2.5 | 1.5 | 1.2 | **2.5** | 1.0558 | STAGED_ENTRY | 4.25% |
| agy 15:03 閘後 | 2.5 | 0.83 | **2.5** | 1.5 | 1.1112 | STAGED_ENTRY | 4.25% |
| codex 15:14 閘後 | 2.0 | 0.83 | **1.5** | 1.5 | 0.7789 | **HOLD** | **0%** |

- **紀律軸兩家都過,agy 的行為確實變了**:手寫 history.json 從 7+6 次變 **0**;`export_provenance` digest ✓;`pt_revision_momentum` 從 null 變 `{DOWN, -2.94}`(**沒走 `UNKNOWN` 那條便宜出口**);中途 validator 紅了它用了 `--replace-last` 2 次,history 剛好 +1 筆。codex 一次過、0 輪 drift。**兩家填了同一個 `-2.94`**——反證那個數字是真的,agy 上次確實是把它掉了。
- **Technical 的歸因被 codex 解掉了**:同一個 hint `+1 to +2`,agy 閘後與 codex **都給 1.5、都沒宣告 override**。所以 agy 的 1.5 不是「為了不寫理由而壓分」,**閘前那個 2.5 才是異常值**——而我實跑 decision_engine 算過,單那 1.0 分就把 STAGED_ENTRY 翻成 BUY(1.2822 vs 門檻 1.2)。**V4.116.3 那道 rubric 閘攔下的是一個會翻轉決策的虛高分,這是整輪最有價值的單一結果。**
- **穩定度軸反而證據更重**:agy 自己兩次 News 1.2→2.5(Δ+1.3);agy 閘後 2.5 vs codex 1.5(Δ1.0);最終 **agy 進場 4.25% vs codex HOLD 0%**。`macro_alignment` 也分歧(agy 閘後 CONTRARIAN,另兩次 ALIGNED)。**但跨引擎分歧不等於 agy 不穩——codex 也只有 n=1**,且 BAC 的 score 在 0.78–1.11 游走而門檻是 0.8/1.2,**這支本身坐在決策邊界上,會放大任何分歧**。下一組測試要挑遠離門檻的股票。
- **我自己的稽核腳本先報了 5 個偽陽性**(`json.dump`/`h.pop()`/`--replace-last` 次數/重複筆數/drift 輪數),全部來自掃「引擎讀進去的檔案內容」而非「執行的指令」——其中 `h.pop()` 命中的正是**我自己寫的那句禁令**。**我違反了自己剛寫進 MAINTENANCE §2c 的規則:對照工具要先證明在已知輸入上報得對,才能拿它報數。** 若直接轉述第一份輸出,我會告訴使用者兩家都還在手寫 history。已改成只掃 tool-call 的 command 欄位,並處理 gemini/codex 兩種 log 形狀。
- **artifact 是單槽快取,回溯稽核有邊界**:codex 的 run 蓋掉了 agy 的 `BAC_decision_engine.json`,回溯比對 agy 會拿到 codex 的 artifact 而印出一堆假 diff。腳本改成偵測 artifact mtime 超出 run 窗就明說「無法回溯比對」。**Gate 3 的結果只在該 run 剛跑完時可信。**

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

# Session Notes 歸檔 v4.122.0 → v4.129.0（新在上，共 10 個）

> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。

## 🟢 Session Note (v4.129.0) — agy 被一個沒人要用的池卡住；修在 broker，但沒有 `--model` 就只是換一種說謊

- **使用者的觀察比症狀準**：側欄寫 `GEMINI 保留區 100%／剩餘 0%`，但 agy 選單裡有六個 model，只有 GPT-OSS 那條滿了。根因不在 UI：broker 的 `scope_for()` 只解了「有指定 model」的一半，**未指定時退回「記到全部池、取全域最小值」——而未指定才是常態**。`claude_gpt.five_hour` 歸零 → agy 整個 `reserve_only` → 連只會跑 Gemini 的工作都被擋。
- **診斷是實跑對照出來的，不是讀 code 讀出來的**：同一時刻打三次 `/v1/recommend --reserve=false`，不帶 model → `eligible=false, before=0.0`；帶 `gemini-3.6-flash-medium` → `eligible=true, before=56.84, rank 1`；帶 `claude-opus-4-6-thinking` → 正確被擋。三條對照才能區分「broker 壞了」與「broker 沒被告知」。
- **最重要的一件事：broker 選了池，本 repo 卻沒有任何一個 agy 呼叫點帶 `--model`**（`llm_drivers.run_gemini`、`dashboard_server._protocol_command`、手動 runner 都沒有）。agy 沒有 `--model` 就用 TUI 當下選的 model，所以**只修 broker 等於把「取最小值」換成「賭 TUI 沒被切過」**——預約在 gemini 池、花費可能出在 claude_gpt 池。兩邊一起改才成立。
- **偏好序不是比剩餘量，這是使用者拍板的**：`gemini → claude_gpt`，取第一個過得了 20% 線的。兩個池裝不同廠商的 model，挑「比較滿的那個」等於在 debate 裡讓 Claude Opus 頂著 gemini 席次回答。
- **實測抓到一個我差點放過的副作用**：第一版讓 catalogue 順序決定 model，live 跑出來是 `gemini-3.6-flash-**high**`——`agy models` 每個家族 high 排在 medium 前面。**這次修的是路由，不該順手把所有未指定的 run 升級到最貴的 tier**。改成預設寫死在 `POOL_DEFAULT_MODELS`，catalogue 只負責回答「這個 id 還在不在」。
- **證據**：broker 1036 passed / ruff / mypy 全綠（新增 9 個測試，含「兩池都滿仍須拒絕」與「tier 不跟隨 catalogue」）；本 repo `test_broker_gate.py` / `test_protocol_model_routing.py` / `test_model_router_window.py` rc=0；daemon 重啟後 live 對照 `recommended=agy, model=gemini-3.6-flash-medium, before=56.84`，側欄 `56.84 / gemini 池 / reserve_only=False`；`agy --print --model gemini-3.6-flash-medium` 實跑 rc=0。
- **跨 repo 副作用**：`lqb client sync` 會同時改寫 `tw-stock-wonwon` 的 vendored client（新欄位有預設值，向後相容），這是 broker repo 的 drift test 強制的，不是本輪決定。
- **模型帳本**：本輪 dev 0 inference turn；agy 實跑 1 次（驗證 `--model` 可用）。

## 🟢 Session Note (v4.128.0) — T4／T5 收尾：兩支腳本的狀態跟我盤點時的猜測相反

- **本輪最該記住的不是修了什麼，是盤點的猜測必須實跑驗證**。plan 檔 T5 我寫「`validate_v219.py` 疑 legacy，確認無 caller 後刪除」——實跑 16 個 fixture 全過，而且它 import 的是**真 producer**（`apply_det_shadow.compute_polarization`），驗的 4-tier polarization 與 RT basis 今天仍是 §13 的活規則。真正的問題完全相反：它**不在 OPS §7 對照表裡**，改 polarization 的人不會知道要跑它。已補列。同樣地 `backtest_watchlist.py` 我以為要翻新，實際 `--dry-run` rc=0 完全正常，連 TODO 的「加 --dry-run flag」都早就做完沒勾銷。**這是 T3 之後第二、第三次盤點預測失準。**
- **`register_thesis.py` 從上線起就沒運作過**（T5 最嚴重的一項，也是 reviewer 這次在 live run 撞到的）：`~/.claude/skills/` 底下只有 `grill-me`，**trader-memory-core 從來沒安裝過**。實跑 `No module named 'thesis_store'`、**rc=0**——non-fatal hook 照設計不紅，所以沒人發現。後果：**183 筆 trade 的 `thesis_id` 全是 null**，連帶 **V20-F1 sector concentration 從未生效**（11 筆帶該 block 的 entry，`applied=true` 是 **0 筆**）。三條出路都改變風控行為，未修，待拍板。
- **`backtest_postmortem.py` 對 V4.87.0 renderer 靜默半殘**：renderer 把 action 摺進決策格，舊 regex 要求決策字後直接接 `|`，**145 份報告 decision 漏 33、action 漏 126**，工具照樣 rc=0 吐 None 表。修 regex 之外**加了解析缺口彙總警告**——這比修 regex 重要，下次格式再變會先出聲。
- **T4：Fundamentals 的缺口與 Technical 在 V4.116.3 之前完全同形**。producer 算得出全部六個 rubric scalar，只印 stdout，數字躺在 subagent transcript 裡 validator 構不到。走同一條便宜路線落地 `<T>_fundamentals_payload.json`。**刻意不做 `rubric_hint`**——Technical 的 hint 是既有的 stage→band 翻譯，Fundamentals 沒有議定過的 base-score 公式，發明一個等於偷寫一條計分規則。證據先落地。
- **證據**：payload 落地種回驗紅（把寫檔那段從 `main()` 拿掉 → 接線斷言紅）；postmortem 警告路徑實測觸發；六個 rubric 區塊形狀斷言全過。
- **協作紀錄**：本輪與另一個 session 並行，版號讓到 4.128.0（對方出了 4.126.0/4.127.0/4.127.1）。上一輪 `dec67dc` 我把對方的 TODO triage 掃進 commit，已 push 不拆；這輪 stage 前逐檔確認歸屬。
- **模型帳本**：本輪 dev 0 inference turn，未跑 protocol。

## 🟢 Session Note (v4.127.1) — META 真跑驗收：新路徑成立，但組裝器自己漏了兩欄

- **驗收結果**：2026-08-10 12:03 codex 跑 META，9m40s、6.47M in / 24k out、rc=0。**零自組腳本**（禁令生效）、**質性檔一次寫對**（我原本預期會在 `watch_conditions` 要 object、`pt_revision_momentum` 要巢狀、`trade_metadata` 不得 null 這三處來回幾輪，實際沒發生）、validate rc=0、render 333 行。
- **fix 3 在生產環境確認**：`comps.py` 對 META 回 **rc=0** + `comps_implied_value: null`（`<2 usable metrics`），模型繼續走完。09:03 那輪就是在這裡硬停的，同一個資料缺口現在不再是擲骰子。
- **但 validator 兩條 `⚠ degraded` 指出組裝器漏欄——是我漏的不是模型漏的**：(a) `burry_score` 我猜在 `pf_quant.quant_blocks.burry`，那個路徑根本不存在，所以恆 None，連帶讓 §16 的 T4 無法重算；(b) `multi_horizon_price_framework` 我整個沒吐。
- **兩個都在 phase 輸入裡，不需要新的 subprocess 或網路**：burry 在 **p3 輸入**（`{"score":44.4,"veto_flag":false}`）、MHP 在 **p4 輸入**。`--stage mhp` 只印 stdout 不落地，這正是它過去被手打進 export 的原因。改成從輸入取，並加進 `DERIVED_KEYS` 禁止手填。
- **教訓**：`_burry_score()` 我是照著自己寫的測試 fixture 想當然耳，而那個 fixture 是我自己編的（`quant_blocks.burry`）。**測試 fixture 若不是從真實 artifact 取樣，它只會確認我的假設自洽，不會揭穿假設本身是錯的。**這次是 validator 的 degraded warning 補上了這個缺口。
- **live entry 尚未補**：重建驗證過 `final_score`/`final_decision`/`final_action`/`avg_confidence`/`position_size_pct` **逐欄相同**，只差那兩欄。要不要用 `--replace-last` 補是使用者的決定（動的是決策帳本）。

## 🟢 Session Note (v4.127.0) — Phase 5 組裝交給 script；封閉 schema 是唯一真護欄

- **做的事**：`build_session_export.py` 取代模型每跑一次現寫的 `build_<T>_session.py`。關鍵是它**同時**吐 export entry 與 `phase_inputs` bundle——那包 bundle 過去**沒有任何 script 產生**，是 renderer 的硬性前置，也是 META 那次「就算修好 KeyError 仍然產不出報告」的真正原因。
- **封閉 schema 才是護欄，不是便利**：質性檔出現任何 script 導得出來的欄位一律 rc=1 而**非合併**。沒有這條，那個檔會慢慢長回原本 130 行的手寫 literal，這支 script 就白做了。
- **使用者原本核准的邊界被實測推翻，我改了**：原訂 lane 的 `score`/`confidence` 算質性（模型判斷）。實跑時 renderer 的一致性閘直接打臉——bundle 的 technical confidence 0.65 → c_eff 0.60 vs `calculation_steps` 的 0.72。**Phase 3 engine 輸入才是「決策數學實際吃到的值」的權威記錄**，手填等於製造二源漂移。改成從 `--p3-input` 導出，質性檔禁填這兩欄。
- **單一來源讓一整類矛盾變成表達不出來**：`lane_scores` / `conflict_bias.lane_signals` / `<name>_lane` / bundle 的 `lanes` 全從同一處導出。§16 的「signal 與同 lane score 反向」這類矛盾不再是「驗得出來」而是「寫不出來」。
- **bring-up 時我自己違反了自己的原則**：bundle 的 `analysis_price` 取 `entry_reference_price`（596.55）、entry 取 `valuation_pack.current_price`（592.10）。**renderer 的一致性閘抓到了**，已修並種成測試。這條閘的價值今天證明了兩次。
- **驗收**：用 2026-08-10 那次失敗的 META artifact 重跑完整 Phase 5 鏈，build → append → det_shadow → **validate rc=0** → **render rc=0（276 行）**。26 條斷言 + 5 個 mutation 全紅。
- **還沒驗的**：模型能不能一次把質性檔寫對。目前只跑過我手工填的版本，中間修了三輪欄位形狀（`watch_conditions` 要 object、`pt_revision_momentum` 要巢狀物件、`trade_metadata` 不得 null）。**下一次真跑 invest 才算數。**

## 🟢 Session Note (v4.126.0) — 兩次 META 失敗，兩個根因都在 repo 不在 codex

- **起點是一則 UI 錯誤**：`rc=0 but required artifact missing/stale: reports/20260810_META.md`。使用者的第一個假設是「codex 的硬傷」。**實測推翻**：當天五次 invest run **全部是 codex，成功兩次**（RKLB、NVDA 08:43）。成功的 NVDA 08:43 與失敗的 META 09:14 幾乎同構——7.3M vs 7.4M input tokens、兩支都寫了拋棄式組裝腳本——**唯一差別是後者去讀了 engine artifact**。
- **根因一：artifact 名不副實。** `run_phase3()` 回 24 欄，`_persist_artifact()` 只寫 6 欄。檔名 `<T>_decision_engine.json`、路徑 `invest_logs/decision_engine/`、內容有 `final_score`/`final_decision`/`calculation_steps`、protocol 還寫「engine 把輸出留在」它——**四項都在暗示這是完整輸出**，實際是為 §5l 裁剪的子集。長 run 把 stdout 擠出 context 後，模型回頭讀它就中。META 那支腳本 9 個取值有 5 個落在被丟掉的欄位，修好第一個還會再炸四次。
- **這類「子集偽裝成全集」的坑，成本不對稱**：多寫 18 欄約 2 KB，漏寫的代價是 7.4M token 的 run 全毀。裁剪的理由（§5l 只比對 `calculation_steps`）是**寫入端的方便**，不是讀取端的契約。
- **根因二：`comps.py` 把答案當失敗。** `sys.exit(0 if not degraded else 1)`——但「同業不足 3 家」是**完整且正確的答案**，不是執行失敗。映射成 rc=1 會撞上 V4.116.1 的閘門紀律（rc≠0 → 停下回報），PM 只好當場自行決定，於是同一天決定了四次、兩種結果。**修法選擇很關鍵：修訊號不修規則。** V4.116.1 完全不放寬，rc≠0 仍只代表工具失敗；改的是「同業不足不該回 rc≠0」。
- **殘留掃描的價值又一次驗證**：§2b 掃到 `dcf.py:918` 有**完全同型**的 exit code 缺陷。**刻意沒跟著改**——dcf 的 `degraded` 是 `fv is None`，比 comps 的明確 eligibility reason 模糊，成因沒分類前不該一起套。已進 TODO。
- **UI 訊息也是缺陷**：`model may have finished without writing output` 對「依紀律中止」的 run 是誣賴。**紀律生效和引擎壞掉不該長一樣。**
- **⚠️ 兩個 session 同時在 repo 上撞版號**：本輪 bump 時 `VERSION` 已被另一個 session 寫成 4.125.0（utils.js/CHANGELOG 也是），我原本要拿的號被佔走，改用 4.126.0。**沒有內容被覆蓋**（我的 printf 只多加了一個換行），但這是運氣不是機制。雙 session 併行時，收尾前先 `stat VERSION` 是必要動作。

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

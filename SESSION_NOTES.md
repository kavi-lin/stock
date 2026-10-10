# INTEL COMMAND — Session Notes & System State

> **Last Updated**: 2026-10-10 (v4.141.1)
> **Role**: This file serves as the "Short-term Memory" and "Handoff Cache" for AI Agents. It contains market regime states, token optimization logs, and data integrity notes. **Task backlog has been moved to TODO.md; full version history to CHANGELOG.md.**

## 🟢 Session Note (v4.141.1) — Codex 配額重置倒數

- Broker 與 `/api/llm-config` 已傳送 Codex `resets_at`，浮動卡片 `resetHint()` 只讀相對秒數／文字標籤才是倒數空白原因。
- 浮動卡片優先支援秒／毫秒／ISO 絕對時間，保留 Claude/Agy 備援；實際週窗口 `1791960087` 對應台北 2026-10-14 14:41:27，重現由空白恢復 `4d`。
- 12 個 Node 倒數案例、移除修正必失敗的正控制、`node --check Dashboard/utils.js` 與 `python3 tests/test_broker_gate.py` 通過；後者需允許本機臨時 HTTP 埠。
- 使用者要求將累積工作分類提交並 push；依資料來源、新聞、投資、signals、財報、broker、研究、quota、文件與產出拆分。新增 ignore 排除本機 tmp／日誌／原始研究快取，保留正式分析快照與報告。
- 預推驗證：959 項 Python、20 項 Node 通過，另 9 支契約腳本通過。兩項既有失敗單獨重跑仍失敗：`test_research_boundary.py::test_http_research_route_and_stale_observation` 缺研究面板頁面接線；`test_run_investment.py::test_lane_fmp_helpers_share_cache_limiter_and_classified_status` 的 sector PE fixture 缺 `sector` 欄位，被新版過濾規則排除。追蹤於 TODO，分類整理未修改功能。

## 🟢 Session Note (v4.141.0) — 正式常駐研究與 25k 預估

- 使用者核准正式模式與25,000／呼叫；四類research送件22k input＋3k output、Luna/max。Broker仍按真實用量結算，未改Broker校準、額度或冷卻。
- `scripts/research/service.py` 隨Dashboard啟動，共用跨程序鎖；獨立service狀態與research-production ID，保留trial／四份報告。滾動24h≤30組／60calls、1h≤5組，重啟不重置，包含先前試驗live calls。
- Broker未啟動模型前的cooldown可等狀態解除＋無預約預檢通過再續跑；實際推論quota/auth/未知用量要人工處理。ACK補送不再錯誤解除推論停止；有效部分結果可續發布，已審閱中斷失敗不重跑。
- 61 Python＋3 Node通過；最後恢复修正18專項通過。36k正控制會被真實acquire測試攔下；governance/window/broker/protocol routing通過。Dashboard閒置後已重啟，新服務PID3837、mode=production、25k；Broker標記cooldown至2026-10-11T16:39:13Z（台北10/12 00:39），因此持續取材、暫停模型推論。
- 啟用證據：`reports/research_production_20261005.json`；工作副本備份 `tmp/research-production-before-20261005/`。版本4.141.0。未改正式投資決策、未額外發模型驗證呼叫。

## 🟢 Session Note (v4.140.0) — 事件研究／Broker 六小時實驗完成

- 使用者授權 AIC 與 sibling llm-quota-broker 完整實作；新研究卡供個股／財報／動能／Nexus，原始證據＋反證保留，無持倉／watchlist 依賴。既有投資決策／圖譜晉升閘保留。
- 四種研究角色走 ensemble registry，gpt-6-luna/max；Broker TaskContext、schema v8 冪等 complete／late usage／history 過濾與平均數落地。canonical vendored client 未因本任務改動。
- 初測24 calls／487172已知tokens，平均20298.83；11完整A/B、首例僅analysis＋結算復原、1錯引文失敗如實保留。首例v7帳本complete500，備份+migrate v8後精確補送；後續結果先持久保存再結算。正式六小時台北10/5 02:07:31–08:07:31，08:07:42自動結束，worker已退出，狀態complete_with_gaps。
- 正式28 calls／15 attempts（13完整A/B）、19卡；26筆已知532900 tokens，平均20496.15／call，2筆native schema／quota失敗未知。含初測52 calls與52 Broker execution逐欄位一致，另1筆未執行expired reservation；滾動一小時峰值5辯論。07:24:41 quota後不重試，來源觀察持續，沒有截止後呼叫。初期453秒心跳間隔保留；Futu／社群逾時隔離、ticker提示與識別分開、低增量篩選、逐階段deadline、busy恢復與已完成結果優先發布均已修。
- Broker1237 tests/ruff/mypy；AIC245 News/research/signal、91 Break News/Nexus/launcher，最後修正後38研究測試及2 Node面板契約通過。四lane收尾HTTP200；無視覺驗收。32輪取材、19卡中18張實際只引feed；真實filing/calendar/followup零樣本。完整結論 `reports/research_observation_research-20261005_conclusion.md`，同名前綴MD/JSON/audit含逐筆證據；既有DIGEST缺席／3筆Nexus digest stale未降閘。

## 🟢 Session Note (v4.139.4) — Skills 接線與保留／整併評估

- 使用者 OK 後修復稽核 F01–F06：安全交付 launchd 環境、評等 endpoint／欄位與方向、事件／快照區分、sector PE 日期、repo breadth 路徑、Finnhub singular split。重啟腳本只停止 LISTEN PID，盤中 partial 顯示錯誤。
- 111 pytest + 8 subtests、四支直接腳本、MU cache／infographic 雙閘通過；新增測試修正前會紅。既有 stale-gate 三個舊斷言已改成來源 fetched_at 規則，未降級 production gate。
- Live FMP 評等／共識／事件有效；AAPL 365 天升6降4、Technology PE48.8。服務閒置預檢後正式 8080 重啟，五項 data credential 的存在性驗證通過；詳細 final health 見 `reports/SKILLS_ENDPOINT_FIX_2026-10-04.json`。
- 26 skills 評估寫入 `skills/MARKET_INDEX.md`：dual-axis／weekly playbook 降選配，calendar／retail 優先整併，其餘22保留；前瞻仍為價格框架依賴。未刪 skill、未改探索層邊界／權重，沒有主動呼叫額外模型。
- 原稽核 `reports/SKILLS_ENDPOINT_AUDIT_2026-10-04.json` 保留為修正前證據；本輪前副本位於 `tmp/skills-endpoint-fix-20261004/before/`。FMP／Finnhub 權限與 CNN／CBOE 缺資料仍列限制。

## 🟢 Session Note (v4.139.3) — MU 收尾 validator argv 修復

- 根因：V4.138 新增 earnings 第二支 validator 後，host 仍把 registry 全部腳本塞進單一 argv，變成 `python validate.py validate_infographic.py MU --require-history`。MU log `earnings_20261004_102135_e381` 分析 rc=0、host gate rc=2；不是使用者操作或模型未產出。
- Server 與 manual runner 共用逐支驗證入口，保留 ticker／日期替換、60 秒限制、第一錯誤即停止及產物 freshness gate。Routing 增加實際 subprocess 的 success／各閘失敗／單腳本參數案例；合併 argv mutation 會紅，恢復全綠，scheduler／broker contracts 通過。
- MU 兩閘與原場次 freshness 重驗 rc=0；等待中的 DDOG 完成後確認同一 host 錯誤，現有報告兩閘重驗 rc=0。原失敗 log 保留，未重跑或新增 LLM 推論。
- DDOG 結束後確認 protocol queue／Break News in-flight 為空且只有 caffeinate 子程序，正式 8080 已安全重啟載入 v4.139.3；MU／DDOG API 都回傳最新季度、摘要可用且無 warnings。原失敗 log 保留。本輪前副本：`tmp/earnings-validator-before-20261004/`。

## 🟢 Session Note (v4.139.2) — 比較 UX 對齊本季

- 使用者接受獨立 tab，要求 UX 接近本季財報；比较 renderer 直接沿用 `ed-section`／`ed-section-head`／`ed-chart-card`／`ed-detail-collapse`，數字字型、主題狀態色、欄寬與間距同步。
- 重複大標題移除；季度、日期、前次入口收進財務表格卡片。手機橫滑固定指標欄，原文證據改為和完整報告一致的展開列。
- 16 Node tests、五種真實 API／頁面 DOM 案例通過；隔離移除原文轉義 mutation 被攔下。Chrome 桌機／400px 手機目視確認，含原文展開及橫滑至年比欄。
- 僅比較 JS／CSS 與例行版本紀錄更新，本季內容及預設分頁保留。工作副本備份 `tmp/earnings-ux-before-20261004/`；未重啟 server、未呼叫其他模型。

## 🟢 Session Note (v4.139.1) — 本季優先與跨季比較分頁

- 使用者偏好：點入財報首先看本季，跨季比較另放 tab。`earnings-tabs.js` 管理本季／比較兩面板，預設不記憶舊 tab；明確 `tab=compare` 可分享與保留歷季選擇，支援上一頁與鍵盤。
- 比較頁改為緊湊五指標表格、預期驗收主欄與下季追蹤側欄；小螢幕堆疊、表格局部橫捲。主列表按鈕恢復「查看財報」，季度圖表僅在可见面板繪製與 resize。
- 16 項 Node 測試、五種正式 API／完整頁面 DOM 案例通過；預設比較的隔離 mutation 會紅，正式程式重跑全綠。Chrome 桌機與 400px 手機版已目視驗收，補完上一輪無法取圖的項目。
- 僅前端及版本紀錄更新，正式 8080 靜態資源已載入；無需重啟 server。`tmp/earnings-tabs-before-20261004/` 保存本輪前狀態，無額外 LLM 呼叫。

## 🟢 Session Note (v4.139.0) — 財報比較 UI 與季度導覽

- 專用 `earnings-comparison.js/css` 已接入財報詳情，列表主鈕改為「財報比較」。前置五指標季比／年比、原文預期與實際值／五態結果、財務警訊差異、下季基準；季度選單、中英文、明暗及窄版樣式。
- 唯讀 `scripts/earnings_detail.py` + 原 API 加 period/revision：最新主資料不因缺 infographic 而回退舊季；歷史優先完成快照，前次連結可固定當時 revision。沒有改評分或回寫舊 cache。
- Python 173 passed + 24 subtests、Node 11 tests、routing 通過；54 ticker／72 季度讀取通過，選錯最舊季度的隔離 mutation 能被攔下。正式 API + 完整頁面 JS 的 DOM 驗收通過 MSFT／PLTR／NKE／ARM／MSFT 舊季度，含語言切換、證據展開、完整報告和主題樣式狀態；實機視窗控制不可用（cgWindowNotFound／browser provider unavailable），桌機／手機截圖待使用者恢復視窗連線。
- 正式 localhost:8080 已重啟載入 UI API 與 v4.138.0 completed gates；MSFT 待補證據／PLTR 全年未到期／NKE 首次分析／ARM 最新季缺摘要均以正式 API 驗證。重啟前無 protocol job／子程序；用 tmp 隔離腳本僅停止監聽 PID，保留 FTNN 連線端。
- `tmp/earnings-ui-before-20261004/` 保存本輪前工作狀態；未動無關髒檔，未主動呼叫額外 LLM。

## 🟢 Session Note (v4.138.0) — 財報跨季比較與預期驗收

- 第一階段完成：`earnings_history.py` 以財季對齊比較，結構化預期五態驗收、待到期延續、觀察清單回訪；raw event 需同季營收匹配，不能用 earnings 第一筆。財報／投資計分公式未改。
- `analyze` 提供前次預期給既有 narrate；新 infographic 需 `history_schema_version=earnings-history/1`、expectations、observed_metrics。`render` 先驗兩層输入，再寫 MD／不可覆寫快照及報告封存；`--preview` 可唯讀重播舊摘要。
- 37 新測試；相關套件 163 passed + 8 subtests，forecaster 13 tests、prewarm／routing 通過，CLI gate 隔離 mutation 會紅。完整 EA suite 3 個 stale-gate 舊斷言失敗已用動工前 analyze working copy 重現；沒有改回既有來源時間政策。
- 預覽：`reports/2026-10-04_{MSFT,PLTR,NKE}_earnings_comparison_preview.md`。舊摘要缺數值契約／原始來源時明示不可驗證；PLTR 全年指引待到期，NKE 無前次分析仍可季比。
- Dashboard 新完成 validator 登記已寫入程式，常駐 server 下次正常重啟載入；此輪未重啟服務或呼叫模型。第二階段專用 UI／完整舊資料補建尚未實作。

## 🟢 Session Note (v4.137.4) — News 選稿與低影響判準

- 原 10/3 run 的 Theme cache rc=0，真正失敗為 finalizer 多數低影響 guard。原始 raw/triage/debate 已保留於 `news/news_logs/audits/2026-10-03_news_repair/`。
- 例行監管與背景報導辨識修復；完整四 lane 低影響允許降級，缺漏／無效數值／binary guard 仍驗證。原輸入唯讀重播得 2 deep + 3 demoted；同一 351 則重新分類得 4 個候選（就業、紅海、柴油出口、LNG）。
- 驗證：News 129 passed；routing、scheduler、broker contract 通過，5 支 Dashboard JS syntax 通過；記憶體 mutation 確認省略-the 回歸確實能抓到 bug。
- Luna 共 2 次協調推論：首次 effort=default 被 host 拒絕，第二次明確 medium 完成 4 lane，345 則取材／3 個候選。主代理補 3 個缺漏翻譯，lane hash 不變；finalizer／validator rc=0，2 deep + 10 shallow、2 個 cache updates。394 個受監測 Python 檔未被實跑改動。比較報告 `reports/2026-10-04_news_selection_comparison.md`：原五則為 3 低增量、2 有影響；另補理財教學辨識。

- Dashboard/data.json 已由 bridge 更新為 10/4、12 則；背景 Break News 仍有活動中的 CLI，因此長駐 server 的根因訊息 helper 尚待下次正常重啟載入。既有 10/3 失敗歷史未改寫。

## 🟢 Session Note (v4.137.3) — Theme Detector 403 修復與可靠性

- finvizfinance 預設 UA 的 13 空白觸發驗證頁；正規化後取得 144 產業。抓取端驗欄位／finite momentum／重複列，錯誤分類保留 HTTP／DNS／timeout 原因。
- Theme Detector 與 News packet 共用 `scripts/_shared/theme_cache.py` 排除 sidecar／壞檔；freshness 遵守 output-dir，主 JSON 原子發布。Scanner 分批保留成果、逾時停止後续請求、隔離執行緒的統計 context。
- 驗證：491 passed；UA 修正移除的記憶體 mutation 2 failed，恢復入口 2 passed。完整實跑 rc=0，213.8s、144 產業／18 主題；`theme_detector_2026-10-03_215131.json` 與 MD 已產出。行情受既有 120 秒預算限制，保留 52/219 檔（RSI 50/219），metadata／data-quality 明示不足；尚未重跑 DIGEST 辯論。

## 🟢 Session Note (v4.137.2) — Broker 用量證據

- 已接通常規 router、Dashboard protocol、manual protocol、Wind 推論的 usage_details；只傳 metadata。Claude 包含 modelUsage 全模型，Wind 的多次推論分開記帳。
- 離線檢查：router rolling-window、broker gate、Wind 19 cases、governance audit 24 tasks／3 providers 通過；fixture 經真實結算入口的 payload 經 broker schema 驗證。
- 正式啟用與覆蓋率詳 `../llm-quota-broker/reports/project-accounting-2026-10-02/`；既有常駐 process 須安全重載才會 import 新入口。未啟用每日 learner。

## 🟢 Session Note (v4.137.1) — 修正 V5.5 卡片誤標 ARCHIVE

- HPE 場次與 Dashboard/data.json 均正確標為 V5.5；page-decisions.js 的 VERSION_COLOR／tooltip 表只到 V5.4，未知版本落入 LEGACY。補 V5.5 與通用版本標籤 fallback，保留真正 ARCHIVE 行為。
- 驗證：JS syntax、真實 HPE 投影的修正前／後標籤對照、新版本／legacy／無效標籤檢查、三處版號同步與 live server JS 逐位元一致均通過；無可用瀏覽器，未做 GUI 目視驗收。
- 使用者另行指定的 HPE 重跑已完成：`HPE_20261001T223002_25eeeee46b`，Luna/max、2040 秒、JSON／MD／provenance 通過，380 個受監測 Python 檔未變。正式三股成功 1／3，成功試行 1／5；細節見工程驗收報告，前次失敗證據保留。

## 🟢 Session Note (v4.137.0) — 個股 V5.5 工程更新與試行

- 使用者授權五批工程並要求完成後用 gpt-6-luna／max 試跑 HPE、NVDA、BE。入口 `run_protocol_manual.py codex invest <T> --yes --v55 --codex-model gpt-6-luna --effort max`；broker／registry 不變。
- 正式評分與部位公式未改。新控制器及操作契約在 `investment/run_workflow_v55.md`；固定來源快照、獨立 prompt、有限派工、即時 schema、quota/auth 停機、原子提交、V5.5 evidence gate。
- 檢討改讀已提交且 provenance 正確的 JSON；歷史分類保留，探索層熱度只進評估 sidecar；synthetic RT 與不完整窗口不進正式校準。
- 驗收報告：`reports/decision_review/investment_v55_acceptance.md`；新測試 48 passed。Luna/max 三股均已試跑，0／3 完整驗收成功；NVDA／BE 修正後保存輸入重播 JSON／MD 皆過，HPE 五線過但模型修改已封存 RT prompt 被 hash 閘攔下。控制器已在封存前補齊 Phase 0／FRED；停止額外模型重跑，保留全部失敗證據。
- 歷史重播 201 筆數字與修改前一致，11 筆歷史 mismatch 為既存。News parenthetical parser 的 extractor 測試為既存失敗，未混入本次修正。最終 cap／部位、finalize 失敗遙測與策略最終決策重播已補接。
- 試行前 5 場／觀測前 20 場仍需實際累積；情緒切換、RT 懲罰／權重／門檻只出提案，不能自動啟用。

## 🟢 Session Note (v4.136.1) — Dashboard 關閉即停止自動辯論

- 根因：`open_dashboard.sh` 把 `caffeinate` wrapper 當 server PID；關閉 wrapper 不會連帶結束 Python server。辯論 CLI 又以獨立 process group 啟動，因此 server 殘留時會繼續吃 quota。
- 現在啟動器直接追蹤 Python PID；SIGTERM／SIGHUP／Ctrl+C 會設定 shutdown event、終止已啟動的 CLI process group、禁止新 CLI 啟動，並在掃描佇列項目間停止。shutdown 期間也不會再產生 market brief。
- 回歸測試不呼叫任何模型：直接啟動無害的 sleep 子程序驗證清理，再確認 stop event 不會讓掃描進入下一個新聞項目。

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

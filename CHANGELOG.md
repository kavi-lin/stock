# Changelog

Older entries: [before v4.135](archive/changelog_pre_v4.135.md).

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + [SemVer](https://semver.org).
Single source of truth for version history. Current version authority is `VERSION` file + `Dashboard/utils.js`.

> **Purpose**: Let future Claude sessions (and humans) understand the evolution
> of the system — what changed, where to look, why. Entries link back to git
> commits where applicable; for un-committed work, dates reflect local VERSION
> bump time.

## [4.141.1] — 2026-10-10 — Codex 配額浮動卡片重置倒數

### Fixed
- `Dashboard/utils.js` 浮動卡片優先讀取 `resets_at`（秒、毫秒或 ISO 日期），保留 Claude/Agy 的相對秒數與文字標籤備援。

### Why
- Broker 與委員會 API 已完整傳送 Codex 重置時間，但浮動卡片漏讀絕對時間欄位，造成週／5h 倒數空白。

## [4.141.0] — 2026-10-05 — 正式常駐研究與 25k 呼叫預估

### Changed
- 四類 research 任務改為 22,000 input＋3,000 output；固定 gpt-6-luna/max，Broker 結算仍用實際原生用量。
- Dashboard 啟動常駐研究服務，共用跨程序鎖；獨立 service 狀態保留六小時 trial 紀錄。所有真實 research 呼叫共用滾動 24h 30 辯論／60 呼叫與 1h 5 辯論上限，重啟與更換 run ID 不重置。
- Broker cooldown 拒絕期間仍取材，解除且無預約預檢通過才恢復；實際推論 quota/auth/未知用量保留人工處理停止。修復「失敗結算補送成功」錯誤解除推論停止的路徑。
- 面板顯示正式服務、25k 預估、滾動用量、冷卻與暫停原因；安全關機在 A/B 之間停下，可恢復已對帳的部分結果。

### Validation
- 研究／啟停／launcher 61 項 Python 測試與 3 項 Node 面板契約；36k 錯誤預估正控制被真實 acquire 測試攔截。Broker／protocol routing、治理與 window 測試通過。
- 正式啟用證據與當下 Broker 限制見 `reports/research_production_20261005.json`。

## [4.140.0] — 2026-10-05 — 事件研究卡與 Broker 實驗治理

### Added
- 新事件研究層：新聞／公告／排程發布／追蹤四種觸發，原文引證、逐主張審查、版本與爭議保留；個股、財報、動能、Nexus 共用探索卡。
- Broker 四種研究分類、experiment/phase/event/revision/stage/effort metadata；每次呼叫原子保存結算、冪等補送及逐欄位 token 對帳。
- Luna/max 初步 12 組／24 呼叫上限；正式六小時 30 辯論／60 呼叫、每小時 5 辯論；持久化起訖、heartbeat、中斷與完整報告。

### Changed
- 共用 RSS 增加 BLS／BEA／NVIDIA IR；來源健康、條件式 HTTP 與退避；FMP/Finnhub/SEC 隔離抓取輸出避免失敗時讀舊快取；SEC 有界分頁／CIK 對應。
- Signal Queue 修訂鍵納入內容；Codex 明確傳 native model/effort，逾時盡量排空 stdout 保留 usage。正式投資決策與 Nexus 晉升閘未變更。
- Live 故障修復：Futu／社群來源隔離並設逾時；RSS 304 保留 validator；空 ticker 的 native schema 相容；無用量程序失敗停止新增呼叫；每個 A/B 階段檢查截止時間。每週前瞻與沒有可辨識財務影響途徑的事件不直接辯論。
- 公司名解析涵蓋摘要；研究卡區分來源摘要／原始網頁並顯示發布時間；報告分開 execution 與未執行預約，附研究卡清單並攔截重複 execution。
- Broker 忙碌改為確認空閒後續跑同一事件；保留已完成階段，quota／auth 不自動重試。供應商 ticker 提示分開記錄，無法單獨讓無財務關聯事件通過研究門檻。

### Validation
- Broker 1,237 測試、ruff/mypy；AIC 245 News/research/signal 與 91 Break News/Nexus/launcher 測試；治理、直接 CLI contract 與 JS 語法通過（測試集合不可重複加總）。
- 六頁研究面板另有 2 項 Node 行為契約；移除文字轉義的正控制會失敗，原始程式回到全綠。
- 六小時實測完成：正式28 calls／15 attempts／13完整A/B／19卡，26筆已知平均20496.15 tokens、2筆未知；含初測52筆Broker對帳一致。busy恢復兩次；quota後停止、截止後零呼叫；狀態complete_with_gaps。完整結論與audit見 `reports/research_observation_research-20261005_conclusion.md`。

### Why
- 把辯論產出拆成可驗證與追蹤的研究資訊，保留不確定性；支出與結果可由 Broker 逐筆監管。

## [4.139.4] — 2026-10-04 — Skills endpoint 接線修復與生命週期盤點

### Fixed
- Dashboard launchd 透過私有 Unix socket 接收呼叫端環境；不把憑證放入 argv 或暫存檔，缺 FMP 時於停止舊服務前中止。重啟只選 LISTEN PID，log 留在專案；盤中 partial 資料回報錯誤。
- 財報改用 `ratings-historical`／`grades-consensus`，對齊 `overallScore` 高分較佳及 `publishedDate`；News／thematic 的評等事件改用 `grades`，月度推薦快照仍用 `grades-historical`。
- 個股 sector PE 補 NY 日期與有限交易日回溯；Finnhub 拆股改為 `stock/split`（本帳戶仍無權限）；breadth preflight／sector fallback 統一 repo 路徑。

### Changed
- `skills/MARKET_INDEX.md` 完成 26 skills 消費關係與生命週期評估：22 保留、2 整併候選、2 選配；未移除 skill 或改決策權重。供應商 402／403／418 另列為尚存限制。
- 既有 stale-gate 測試對齊 source_records 政策：缺失／過期來源不可因 cache mtime 更新而通過；未放寬 production gate。

### Validation
- 111 pytest cases + 8 subtests 通過；bundle merge、routing、intraday、drift 腳本及 MU 現有報告雙驗證器 rc=0。
- 新 endpoint contract 修正前 9 failed／1 passed，修正後 10 passed；真 subprocess 測試 launchd 空環境、私有 socket 傳送、缺 key 與 timeout 清理。
- 實際 FMP 取得評等歷史／共識／事件日期；AAPL 365 天 6 次升評、4 次降評，Technology PE 48.8。正式服務與最終驗收見 `reports/SKILLS_ENDPOINT_FIX_2026-10-04.json`。

### Why
- HTTP 200 不保證事件 schema 正確，shell 有 API key 也不代表 launchd 常駐服務有；需驗證實際 consumer payload 與 runtime 環境。

## [4.139.3] — 2026-10-04 — 修復財報多驗證器收尾誤判

### Fixed
- `dashboard_server.py` 原先把 validator registry 的多個腳本展開為同一條 Python argv，第二支腳本被誤認為 ticker，MU／DDOG 因多餘參數而被標為失敗。
- 新共用 `_run_protocol_validators` 逐支執行、各自帶入 ticker／completed-history 參數，第一個非零結果即中止；手動 runner 亦使用相同入口及投資場次參數。

### Validation
- Routing contract 增加真實 subprocess 測試：雙閘成功、第二閘失敗、第一閘失敗且不得被後續成功掩蓋；驗證 News 無參數與 Invest 日期／ticker 替換。
- 合併 argv 的記憶體 mutation 確實失敗，正式入口恢復全綠；scheduler、broker contracts 與 Python／Dashboard JS syntax 通過。
- MU 現有報告通過雙驗證器及原場次產物 freshness gate；DDOG 現有報告亦通過雙驗證器，無需重跑模型。
- DDOG 完成後閒置重啟正式 Dashboard，live V4.139.3／兩股最新財報 API 確認正常，原失敗 log 保留。

### Why
- 分別執行 validator 的測試無法發現主程式把兩支腳本串成一條指令；需要測試實際 subprocess 派送入口。

## [4.139.2] — 2026-10-04 — 比較 UX 對齊本季財報

### Changed
- 比較頁沿用本季財報的 `ed-section-head`、`ed-chart-card`、`ed-detail-collapse`；標題置於卡片外，數字使用 JetBrains Mono，狀態顏色共用主題 token，雙欄與間距一致。
- 季度選擇、比較範圍、日期與上次財報入口集中在財務表格上方；移除重複大標題。原文與觀察變化沿用完整報告的展開操作。
- 手機表格橫滑固定指標欄並提示操作，季度控制與內容依序堆疊。

### Validation
- 16 項前端測試、五種正式 API／完整頁面 DOM 案例通過；新 disclosure 移除原文轉義的隔離 mutation 確實失敗，正式程式重跑全綠。
- Chrome 桌機及 400px 手機版目視驗收，原文展開與橫滑至去年同期／年增減時固定指標欄正常。

### Why
- 使用者接受分頁安排，要求比較頁 UX 盡量對齊本季財報，減少兩頁閱讀與操作落差。

## [4.139.1] — 2026-10-04 — 本季財報優先與獨立比較分頁

### Changed
- 財報詳情預設「本季財報」，呈現本季數字、圖表、摘要與完整報告；「跨季比較」改為獨立分頁，列表主入口為「查看財報」。只有明確 `tab=compare` 連結才直接開比較。
- 比較頁收斂為五指標財務表、上次預期驗收與下季追蹤；移除重複大卡片與頁內導覽，保留原文證據、季度選擇與歷史版本連結。
- 分頁支援鍵盤及瀏覽器上一頁，歷季選擇保留比較分頁；圖表在本季面板顯示時才繪製，切回時重新適配尺寸。

### Validation
- Node 16 tests 通過；隔離 mutation 將預設改為比較時確實失敗，正式程式重跑全綠。五種真實 API／完整頁面 DOM 案例通過。
- Chrome 實機檢查桌機與 400px 手機版：預設本季內容、比較表格與核對區、分頁切換正常；修正側欄背景受全域 aside 樣式覆蓋。補完 v4.139.0 的視覺驗收。

### Why
- 使用者要求點進去先讀這一季財報，跨季比較另放分頁，並簡化比較畫面的資訊密度。

## [4.139.0] — 2026-10-04 — 財報比較 Dashboard

### Added
- 財報詳情前置三區：本季季比／年比與五指標、上次預期逐項驗收、下季觀察基準；有季度選單、歷季數字展開、原文依據、警訊變化及中英文／明暗／窄版樣式。
- 財報列表主入口改為「財報比較」。唯讀 API 即時計算舊資料，支援 period 與 revision；完成分析優先使用封存快照，原紀錄連結固定到當時版本。

### Fixed
- 最新季沒有摘要時仍展示當季數字與完成狀態，不再退回較舊 infographic。會計期末與財報公布日分開，市場預期只用配對成功的事件。
- 達標、超標、未達標、尚未到期、待補證據分色及文字標記；缺資料不列入達標評分。首次分析仍有歷季財務比較，利潤率以百分點呈現。
- 詳細報告只綁一次展開事件；隱藏載入狀態不再被 flex 樣式覆蓋。

### Validation
- Python 173 passed + 24 subtests、前端 11 tests、protocol routing 通過；54 個 ticker／72 個歷史季度唯讀檢查通過。隔離 mutation 證明選錯最舊季度會被測試攔下，還原後通過。
- 真實頁面 JS + 正式 API 的 DOM 接線檢查通過五種案例（MSFT／PLTR／NKE／ARM／MSFT 舊季度），包含語言、展開狀態、報告讀取與明暗色樣式。
- 瀏覽器實機驗收受工具限制：Safari／Chrome 回報 cgWindowNotFound，iab／chrome browser provider 不可用；尚未取得桌面／手機實際截圖。使用者可從 earnings.html 的「財報比較」檢視。

### Why
- 讓上次預期與這次結果在財報畫面直接相鄰可讀，並能回查當時紀錄。

## [4.138.0] — 2026-10-04 — 財報跨季比較與預期驗收（第一階段）

### Added
- 財報 Markdown 前置「本季變化／上次預期驗收／下次追蹤」；對齐相鄰財季與去年同期，回訪前次觀察基準，保留季距與原始來源。
- 結構化公司指引／市場共識／分析預期；依目標期間、會計／幣別／匯率／業務口徑判定超標、達標、未達標、待到期、無法驗證，pending 目標延續。
- 成功 render 後保存 hash 歷史快照與 Markdown 封存，同季修訂追加、相同輸入冪等；舊文字僅作歷史補建，preview 不改快取與歷史。
- 正式財報完成檢查登記兩個 validator，要求最新主快取、敘事、報告與歷史快照一致；財報評分／投資決策公式維持原規則。

### Fixed
- 依同季營收匹配已完成 earnings 事件，排除未來第一筆；會計期末與公布日分欄。保留三表幣別與 filing 連結，避免跨口徑驗收。
- 舊 accruals_warning 定義改版不誤報解除；季度稀釋 EPS 為零仍保留，年度 EPS 不由四季 EPS 相加。

### Validation
- 新增 37 項離線測試；財報／schema／Signal Queue 合計 163 passed + 8 subtests，forecaster 13 tests、Phase 1 prewarm 與 protocol routing 通過。
- MSFT／PLTR／NKE 比較預覽已產出；72 份現有快取的 analyze 輸出與動工前逐項一致。移除 CLI 比較 gate 的隔離 mutation 觸發預期失敗。完整財報 suite 中 stale-gate 舊測試的 3 項失敗，已用動工前 working copy 重現，保留既有來源時鐘修改。

## [4.137.4] — 2026-10-04 — News 選稿、低影響降級與失敗根因

### Fixed
- Stage 1 例行核准公告容許省略 the，辨識徵詢延期／重開、人物背景與理財教學報導；行政公告不再標成貨幣政策。
- Finalizer 先驗完整四 lane 與 Arbiter，再將非 binary 且四 lane 均低影響的項目降為摘要；保留實際分析與來源、不 patch cache。多數低影響不再等同缺漏辯論，Sector/Macro 實質影響與 binary 事件保留 deep。
- Dashboard 在 validator 失敗時從 Codex completed command 取出未恢復的必跑腳本錯誤，成功重試會清除舊錯誤，缺產物訊息保留為 fallback。

### Why
- 10/3 原 5 則有 3 則選稿誤判，四 lane 已完成却被整批拒絕；UI 又只呈現「今日無 digest」。修正來源分類與完整性判準，原始 lane 分數不改。

## [4.137.3] — 2026-10-03 — Theme Detector 資料取得與快取可靠性

### Fixed
- FINVIZ group client 正規化套件預設 User-Agent 的 13 個連續空白，恢復產業／板塊資料抓取；缺欄、重複列與無效動能輸入明確失敗。
- Theme Detector 與 News packet 共用主報告選擇，排除 narrative sidecar／損壞快取，freshness 遵守指定輸出目錄；JSON 原子發布。
- 代表股掃描分批保留成果；逾時取消尚未啟動的請求，保留已取得行情與完整批次，隔離 stock／ETF 統計。
- 報告新增實際 stock／RSI 覆蓋率與逾時旗標；HTTP 403、timeout、DNS 錯誤直接回報來源，移除已失效的 FMP v3 fallback 說明。

### Why
- FINVIZ 驗證頁造成 DIGEST 缺產物；原快取及逾時流程還會把「附屬檔新鮮」或「219 個空結果」當成有效資料。

## [4.137.2] — 2026-10-03 — Broker 用量證據接線

### Changed
- 一般 router 結算傳入原始 CLI stdout 在本機解析；Dashboard／手動協定傳入 log_path 逐行解析，僅回報 allowlist 用量 metadata。
- Wind 每次推論獨立保留模型與 token 明細，以 attempt 區隔後結算；Claude 多模型摘要不重複計費，缺漏來源明示 partial／missing。
- vendored client 同步 broker capability negotiation、nullable 用量證據與模型補正。

### Why
- 更新 client 本身不會自動讓業務入口送明細；逐日學習必須先接通所有結算路徑。

## [4.137.1] — 2026-10-01 — Dashboard 正確顯示 V5.5 場次

### Fixed
- 決策卡片補上 V5.5 標籤與中英文說明；V5.4 不再標為最新。
- 尚無配色的有效版本保留原版本號，不再回退為 ARCHIVE；真正 legacy 紀錄維持原標籤。

### Why
- HPE export 與 Dashboard 投影均為 V5.5，前端配色表漏列新版卻誤標為歸檔。

## [4.137.0] — 2026-09-30 — 個股分析凍結快照、續跑與可追溯檢討

### Added
- `run_investment.py` 與 `run_data.py`：指定 Phase 0、來源時間 TTL、不可變快照、五份獨立 prompt、最多三線派工、即時驗收、一次重試、配額停機、依賴與 hash 續跑、同場 idempotent 提交。
- V5.5 `run_context`、程式產生的情緒 shadow／det_inputs、lane 模型／版本／hash、統一價格與供應商差異、階段遙測、synthetic Red Team 執行品質。
- `committed_investment.py` 與 `run_observability.py`：JSON 權威索引、穩定 ID／歧義表、歷史分類凍結、評估 sidecar、完整窗口／有限價格篩選、股票群組 bootstrap、只提案不啟用的策略重播。

### Changed
- 財報 7 天／市場資料 24 小時／報價 5 分鐘分層快取；舊快取缺可靠來源時間即刷新。分析重算不延長期限；FMP 接入共用限流與呼叫觀測。
- Dashboard 與手動入口共用股票鎖；V5.5 路徑先以 `--v55` 試行。模型能力沿用 registry/certification；manual 支援明確 model／effort。
- Phase 0 FRED 欄位改用 deterministic assembler，保留來源時鐘；V5.5 schema 組裝允許一次有來源證據的修正，正式 gate 不變。
- prepare 自動收集原始 scripts 與執行收據；Forecaster PE 歷史不足等選用缺漏不阻斷全場，也不回填舊快取。Burry 原始 burry_score 統一映射 score／既有 veto 規則，V5.5 gate 強制比對。
- 試跑修正：assembler 接回既有 Phase 4.6 cap／speculative governor，從 risk_audit 讀取部位並重算驗證；RT prompt 封存前加入 Phase 0／FRED。最終閘門失敗與未提交 prompt 竄改納入遙測；策略候選比較最終決策／部位，RT 增加按股票群組的交易條件觸及率。
- export、renderer、history 保留舊版相容。修正既有 valuation-pack 測試 fixture 未經 forward-validation composition 的缺欄位。

### Validation
- 新流程 48 項離線測試，含盈利／虧損／同業不足的完整 prepare→commit、1/2/3 名額、來源竄改與驗證接線突變；Phase 4.6 高信心 cap 與部位非 null 經完整提交入口驗證。
- Luna/max 三股試跑完整驗收 0／3；NVDA／BE 修正後保存輸入的 JSON／MD 重播通過，HPE 的 prompt hash 閘成功阻止提交。原失敗證據保留，未切預設或啟用策略。
- 既有 quant／決策／部位／export／renderer／broker 閘門通過。201 筆決策重播與修改前數字完全一致；既有 11 筆歷史 mismatch 未改寫，部位 current-rule mismatch=0。
- `scripts/extractors/tests` 有既存 News parenthetical parser 失敗，非本次個股變更；相關 macro-regime 測試通過。

### Why
- 分離來源時間與分析時間，讓每場決策可重現、可續跑且可稽核；策略閾值與權重維持現況。

## [4.136.1] — 2026-09-22 — 關閉 Dashboard 時停止自動辯論與模型子程序

### Fixed
- `open_dashboard.sh` 現在直接管理 Python server PID；關閉時送 SIGTERM 並等待 server 清理，不再只結束 `caffeinate` wrapper。
- Dashboard 收到 SIGTERM／SIGHUP／Ctrl+C 時設定 shutdown event、終止所有辯論 CLI process group，並拒絕關閉後的新模型呼叫。
- 自動辯論掃描可在佇列項目之間停止；關閉流程不再接著觸發 market brief。

### Added
- `tests/test_break_news_shutdown.py`：驗證活動子程序會被收掉、shutdown 後拒絕新程序，以及掃描不會繼續辯論下一項。

### Why
- 啟動器原本記錄的是 `caffeinate` PID，結束它不會結束 Python server；server 與獨立 process group 的 CLI 子程序便可能在 dashboard 關閉後繼續耗用 quota。

## [4.136.0] — 2026-09-17 — 盤前 brief 事件日曆：ET 時區、標題截斷、跨來源重複、dict 外洩

### Fixed
- **`bridge.py` 時區**：FMP stable `economic-calendar` 的 `date` 欄是 **UTC**，舊碼直接接 `" ET"` 當標籤，讓每一筆早盤數據在 brief 上晚 4 小時（`12:30 ET` 實為 08:30 ET）。新增 `_utc_hhmm_to_et()`（zoneinfo，DST-aware）真轉換。`_from_sector_protocol_new` 的裸 `HH:MM`（LLM 轉手的同一批 FMP 時戳，比對 8 個已知發布時間全部吻合 UTC）一併轉換，原值留 `source_payload.raw_time_utc`。
- **`bridge.py` 標題截斷**：`title[:36]` 把 `Jobless Claims 4-Week Average (Sep/12)` 切成 `…(Sep/1`，截斷的日期標籤讀起來像另一份數據。改 `_truncate_title()` 在詞界斷，上限 48，`_clean_event_text` 共用。
- **`bridge.py` 跨來源重複**：同一份數據從 fmp-econ（英文 / `econ` / 有時間與 prev-est）和 sector-protocol（LLM 中文 / `macro`）各進一次，Pass 1 看不出是同一件事（category 不同，且 `_slugify` 會把中文整段丟掉）。新增 `_CANONICAL_RELEASES` 關鍵字表 + Pass 1b（單一 series 合併，保留資料較完整者）與 Pass 1c（複合標題如「8 月新屋開工與建照」在其涵蓋的每個 series 都已有更完整記錄時才吸收）。9/17 當日 9 筆 → 8 筆。
- **`bridge.py` `_slugify` 丟棄 CJK**：`8 月新屋開工與建照` → `'8'`、`FOMC 會議紀要` → `'fomc'`，同日兩個無關中文事件可能撞 key 被靜默併掉。改為保留 CJK；並在切長度之後再 `strip('-')`，讓同一標題不因上游截斷位置不同而產生不同 key。
- **`bridge.py` archive 蓋掉修正**：`_merge_two` 只在 impact 較高時換主記錄，同 impact 時舊 archive 版本原樣留下 —— 上述時區／標題修正對已入庫事件一律無效。新增 `pin_primary=True`（fresh 為主、impact 仍取高者）＋ `_repair_archived_times()` 一次性遷移（以 `source_payload.raw_utc` 缺席辨識舊資料，轉換後蓋章，冪等）。本次修掉 146 筆。
- **`bridge.py` earnings universe**：`_load_calendar_universe` 同時收 `BRK-B` 與 `BRK.B` 兩種拼法，避免 FMP 端點拼法不一致時漏掉真名單。
- **`scripts/premarket/morning_brief.py` §10 吐 dict**：`r.get('title', r)` —— `binary_risks` 的鍵是 `event` 不是 `title`，fallback 直接把整個 dict 的 repr 印進報告。改讀 `event`，缺鍵改推 `_warnings`。
- **`scripts/premarket/morning_brief.py` §10 重複**：`binary_risks` 與 `upcoming_events` 各列一次同一催化劑（FDX 出現兩次）。改用 (date, ticker) 交叉抑制；ticker 抽不出來的一律保留，不會被無 ticker 的事件誤殺。
- **`scripts/premarket/morning_brief.py` §5 Time 全空**：FDX 的 `AMC` 埋在 `source_payload.raw_event.time`，舊碼只看一層。改 `_earnings_time()` 逐層找。
- **`scripts/premarket/morning_brief.py` 表頭誠實化**：09:30 ET 之後重跑仍寫「pre-open snapshot」。改為依實際生成時間切換文案並標 ⚠️。
- **Universe 名單過期**（screener 每日 4 errors 的來源）：`nasdaq100.txt` 移除 ANSS（已併入 Synopsys）、WBA（已下市私有化）；`sp500.txt` + 兩份 `*_sectors.json` 的 `BRK.B`/`BF.B` 改為 Yahoo 拼法 `BRK-B`/`BF-B`（yfinance 對點號拼法回 0 rows，實測確認）；`themes.yaml` 移除 ABMD（2022 併入 J&J）。

### Added
- `tests/test_event_calendar_hygiene.py` — 40 個回歸測試，逐項釘住上述行為（含 DST 邊界、複合標題不可被單一 series 吸收、archive 遷移冪等、無 ticker 風險不被誤殺）。

### Why
- 2026-09-17 盤前 brief 同時出現原始 dict、同一份房市數據列三次、以及全表晚 4 小時的時間戳。時區那條是唯一會讓人真的看錯發布時間的；其餘是可信度問題。morning_brief 當時回報「0 warnings」——渲染層的 fallback 命中不進 warning 通道，屬 MAINTENANCE §2c「靜默綠」同一類。

## [4.135.11] — 2026-09-17 — open_dashboard.sh 收舊 server 要等 port 真的釋放

### Fixed
- `open_dashboard.sh`：舊版 `kill -9` 完立刻 bind，但 kill 是非同步的 —— process 還沒收屍前 socket 不釋放，新 server 撞 `[Errno 48] Address already in use`。改成 `stop_port()` TERM → KILL 逐級升，每級輪詢 `lsof` 直到 port 空出來（各 5s），5s 內都收不掉就 abort 並印出佔用者 PID。
- 啟動後改用 health poll（`curl` 最多 10s）確認真的 listening；沒起來就 `exit 1`，不再往下開瀏覽器／風向派工器／印出「Dashboard running (PID …)」—— 舊版 server 已經 traceback 死掉了那行還是照印，看起來像有開。

### Why
- 2026-09-17 實際撞到：traceback 後 script 照常印「Dashboard running」＋「Wind dispatcher already running」，使用者無法從輸出判斷 dashboard 到底活著沒有。這是 MAINTENANCE §2c「靜默綠」的同一類問題 —— 失敗被下游輸出蓋掉。

## [4.135.10] — 2026-09-03 — Phase 0 重建加鎖，防止並發 ticker 各自重跑 L3

### Added
- `investment/scripts/phase0_lock.py`：mkdir-based 鎖，`acquire` / `wait` / `release` 三個子指令，
  token-based ownership（每次呼叫都是獨立的一次性 process，沒有可靠的長壽 PID 可比對，因此棄用
  PID liveness 判斷改用 20 分鐘 time-based staleness 自動回收 abandoned lock）。

### Changed
- `investment_protocol_v5_0.md` Phase 0 L3 段落：重建前先 `acquire` 鎖；拿不到鎖就 `wait`（預設
  逾時 900s），逾時停下回報而非搶鎖硬重建；等到鎖釋放後重新檢查 canonical `phase0.json` 是否已
  變新鮮，新鮮就直接沿用、不重複重建。

### Why
- 2026-09-02 22:01 GOOG(claude) 與 JPM(codex) 兩個 ticker 分析相差 8 秒派工，各自判定 canonical
  Phase 0 快照 stale 後各跑了一次完整 4-skill L3 重建（`sector/breadth_cache/` 等在 90 分鐘內被
  重建了 3 波），對外部 API 重複付了成本、也拖慢了兩邊。

## [4.135.9] — 2026-09-03 — 修正 FINVIZ 一週產業報酬放大 100 倍

### Added
- `news/fetch_news_rss.py` 新增 FinancialJuice 公開 RSS，來源分類為 publisher、可信度 Medium。

### Fixed
- `finviz_performance_client.py` 將所有帶 `%` 的字串按字面百分比轉成 decimal；FINVIZ 的
  `0.54%` 不再被後續換算放大成 `54%`，也不會被 hard cap 偽裝成 `30%`。
- 新增小於 1% 的正負回歸案例；舊邏輯種回時測試確實失敗，還原後 theme-detector
  全套 462 項通過。重建快取與 Dashboard 投影後，產業榜已無錯誤 `±30.0%`。

### Why
- `finvizfinance` 將 Perf Week 保留為百分比字串，其他績效欄位則轉為 decimal float；舊解析器
  以數值是否大於 1 猜測單位，讓所有絕對值小於 1% 的週報酬被放大 100 倍並污染排名。

## [4.135.8] — 2026-08-27 — 產業成分股清單改按市值降冪排

### Changed
- `Dashboard/page-radar.js`：`showIndustryStocks()` 的 finviz 完整清單改依市值降冪排序
  （原本沿用 finviz 回傳的字母序）。新增 `_mktCapNum()` 把 "12.13B" / "197.6M" 這類
  字串換算成數字；無市值（"" 或 "-"）記 -1 沉底。

### Why
- 43 檔的 Health Information Services 清單以字母排，VEEV（$46.55B）夾在中段，
  要一個個掃才看得出誰是龍頭；按市值排一眼就分得出大中小型。

## [4.135.7] — 2026-08-27 — 快照過期不再被說成「額度用完」

### Fixed
- `scripts/_shared/model_router.py` 的 `_blocked_reason()` 依 broker 回傳的 code 分流：
  `stale_snapshot`（讀數過期，額度本身沒事）與 `not_authenticated`（CLI 登出）各有自己的
  說法，只有真正的容量不足才提 hard reserve。
- `dashboard_server.py` 的 `_requeue_protocol_entry()` 為 `stale_snapshot` 開獨立
  `waiting_reason`，重試間隔 15 秒（broker 收到這種拒絕會自己重新偵測），不再併入
  30 秒的 `quota_wait`。
- `Dashboard/utils.js` 佇列列新增 `stale_snapshot` 文案「額度讀數過期，broker 重新偵測中」。

### Why
- 2026-08-27 盤前檢查的 News Digest 卡在「等待額度釋放，自動重試 #8」二十五分鐘，
  當時 CODEX 83%、GEMINI 96.8%、CLAUDE 100% 都是滿的。真正的原因是筆電進
  Maintenance Sleep，broker 的排程刷新追不上 900 秒的新鮮度門檻，三家全被判
  `stale_snapshot`；而本 repo 把所有 refused 都顯示成「額度用完」，把人送去查一個
  完全正常的額度。broker 端的修法（睡醒即刷新、拒絕時就地重新偵測）在
  `llm-quota-broker`。

## [4.135.6] — 2026-08-26 — 讀不到 broker 額度不再顯示成「broker 無 provider」

### Fixed
- `scripts/_shared/broker_gate.py` 的 `quota_snapshot()` 自己吞掉 `BrokerError` 後回空
  `providers`，`model_router.broker_status()` 外層那道 `except BrokerError` 因此永遠不會
  觸發，逾時的輪詢被當成「成功讀到、但一家 provider 都沒有」。現在回傳多帶一個 `error`
  欄位，成功讀取為 `None`。
- `broker_status()` 只在真的讀到答案時才宣告 `authority`；讀失敗改回
  `handshake_status="broker_error"` 並帶原因。
- `Dashboard/utils.js` 為 `broker_error` 增加獨立提示「讀不到 broker 額度」+ 一鍵重啟；
  「broker 無 provider」現在只在真的零家時出現。

### Changed
- broker client 預設 `timeout_sec` 10 → 20 秒。

### Why
- 2026-08-26 側欄顯示「broker 無 provider」，同時 `lqb status` 三家都健康
  （agy 71% / claude 43% / codex 98%）。`/v1/status` 在尖峰量到 12.5 秒、超過 10 秒的
  client timeout，三層各自「合理」地把「沒讀到」變成「沒有」。broker 端的延遲已在
  llm-quota-broker 修掉；這邊修的是誤報——同樣的誤報以後只會顯示成讀取失敗。

## [4.135.5] — 2026-08-22 — 額度主卡直接顯示 broker 限制窗口

### Changed
- `Dashboard/utils.js` 的三家 provider 主條改畫 broker 實際派選使用的最緊 bucket，並在百分比前明示 `週` 或 `5h`。
- Agy/Gemini 先限定在 broker 當前 routable pool 內找限制窗口；provider 排序與 tooltip `▸` 也改用同一 bucket。

### Why
- 舊主卡固定偏好 5h，卻同時顯示 weekly reset；Claude `5h 2%` 會遮住實際限制派選的 `週 27%`。全部強制改畫 weekly 也會在 Gemini 被 5h 卡住時誤導，因此改為顯示每家當下真正的限制窗口。

## [4.135.4] — 2026-08-22 — 即時辯論不再把 broker busy 當成模型失敗

### Fixed
- Break News 跨新聞執行固定序列化；即使舊 CLI 傳入 `--workers 2`，也不會讓兩筆新聞同時搶同一組互斥 provider slots。
- 任一辯論 turn 遇 broker blocked 時回到 `pending_debate` 等下輪重試，不再永久關成 `partial_closed` / `failed`；scan state 另計 `deferred_in_scan`。
- comment 與 item 保存 bounded `error`、`route_note`、`deferred_reason`，後續可直接看到 `provider_busy` / broker unavailable 原因。
- restart script 為 launchd 明示 Node／Agy／Codex 所需 PATH；避免互動 shell 正常、daemon 卻回 Codex rc=127／Agy rc=-2。
- 無活動超過 thread timeout + 120 秒的 `debating` orphan 自動回 pending；不碰既有 partial/failed 歷史。
- `debate_item` daemon boundary 捕捉 roster／broker malformed response 等未預期例外，寫入原因並還原 pending，不留下空的 `debating`。
- 新增 opener／responder blocked、跨 item 不重疊、exception safety 與 orphan recovery 回歸；47 項 Break News tests、broker gate、全量 artifact validator 通過。

### Why
- v4.132.0 已把單場辯論改為循序對話，卻保留兩個跨新聞 workers；兩者會同時向 broker 索取同一 provider，失敗方在 0 ms 收到 `rc=-9`，但 debater 誤判成模型實際執行失敗。2026-08-21 因此只有 10/59 筆完整結案。
- Dashboard 改由 launchd 常駐後未攜帶互動 PATH，重啟才暴露 CLI wrapper/runtime 無法解析；部署驗證因此納入固定 PATH 與 binary lookup。

## [4.135.3] — 2026-08-21 — 盤前工作與全域任務 queue 整合

### Changed
- 移除跨頁的橘色 `chain-status-pill` 及整組專用 CSS，不再與紫色 global protocol queue 同時顯示同一個 News/Sector 工作。
- global queue 依 entry 既有的 `source="premarket_chain"` 加上 workflow provenance：顯示 `盤前檢查 · News Digest` 或 `盤前檢查 · Sector Scan`，收合標題、slot tooltip、active detail 與 pending row 使用同一标籤。
- `daily_update` 仍只在盤前 modal 的 phase progress 顯示；它不是 broker-governed LLM task，不進 protocol queue、不佔三個 provider slots。

### Why
- 橘色卡與紫色 queue 原本從兩個 endpoint 重複繪製 News/Sector 狀態，還會互相重疊；任務來源已在 queue payload 裡，直接顯示 provenance 比維護第二個狀態面更清楚。

## [4.135.2] — 2026-08-21 — 併行狀態面板不再重複燈號或隱藏工作

### Fixed
- quota panel 以 broker 每 provider 單一互斥 execution slot 為準：`/api/protocol-queue` 已證明是本專案的 run 時，同 provider 不再因 broker v0.3 的 flat reservation 缺 `project` 而又亮外部藍燈。
- 浮動 protocol pill 的收合標題從只取 `active[0]` 改為彙總全部 active runs；同 protocol 顯示如 `invest ×3 · MU / SNDK / NVDA`。
- 等待區每筆加入 `×`，以 queue entry ID 呼叫專用 `DELETE /api/protocol-queue/<id>`，只移除指定 pending job。

### Why
- 並行 scheduler 已能佔滿三個 provider slot，但額度燈號、收合標題與 pending controls 仍沿用單工作時期的假設，使同一組真實狀態在不同位置顯示成互相矛盾的資訊。

## [4.135.1] — 2026-08-21 — LLM 燈號區分本專案與外部程式

### Fixed
- broker active reservation 映射保留 `project` 並由後端產生 `is_local_project`；只有 AI 投資委員會可亮綠燈，其他程式亮藍燈。
- 同一 provider 同時有本專案與外部使用時同時顯示綠／藍兩燈；缺少 project attribution 的 broker row 保守視為外部。

### Why
- broker 是跨專案共用權威；全域 reservation 不能全部用綠燈偽裝成 AI 投資委員會正在執行。

## [4.135.0] — 2026-08-21 — 全專案 LLM 統一由 quota broker 分配

### Added
- 新增 24 個 LLM task 的 registry、capability certification ledger、靜態 governance audit 與分類文件；未註冊或未認證的 inference fail closed。
- Nexus Tier 3 改用共用 router，Claude／Agy／Codex 各一個隔離 schema canary 均通過，未寫正式 graph/cache。

### Changed
- 一般 LLM 任務改由 broker 從已認證 provider 集合實際選擇；ensemble／認證才允許 broker-pinned provider，任何失敗都不再跨模型重播。
- 移除 Tier 3 Anthropic SDK、weekly cron Claude CLI、manual runner 無 lease、driver probe、Office／brief／翻譯固定模型等旁路；Grok 停用。
- protocol 在 broker busy／無額度／瞬斷時留在 queue 自動重試；daemon/cron defer；額度面板綠燈改讀全專案 active broker reservations。
- Dashboard restart 改由 launchd submit 持有 process，避免啟動 shell 結束後 server 一併退出。

### Why
- 同一模型被重複選派、選派中的 ticker 消失與非 broker 呼叫，根因都是多個分配權威並存；現在只有 broker 能授權 LLM process。

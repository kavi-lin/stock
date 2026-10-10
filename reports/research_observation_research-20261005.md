# 事件研究觀察報告：research-20261005

狀態：六小時結束；complete_with_gaps。
已觀察 6.00 小時；起點 2026-10-04T18:07:31.109927+00:00；終點 2026-10-05T00:07:31.109927+00:00。

初步案例 news-supported 限制：analysis transcript was not persisted; no B turn for this case。
## 功能與驗證

新聞、原始公告、排程發布與研究追蹤共用事件及主張資料。個股、財報、動能與 Nexus 顯示研究卡；正式投資決策與圖譜晉升門檻保留。

確定性驗證：{"passed": true, "checked_at": "2026-10-04T21:08:06.632073+00:00", "checks": [{"name": "research source/runtime/router/HTTP regressions including timeout/empty tickers/deadline", "passed": 38}, {"name": "News + research + signal queue", "passed": 245}, {"name": "Break News + Nexus + dashboard launcher", "passed": 91}, {"name": "llm-quota-broker full suite", "passed": 1237}, {"name": "broker ruff/mypy + AIC governance + direct broker/routing scripts + JS syntax", "status": "passed"}, {"name": "research panel browser entry contracts", "passed": 2, "positive_control": "escaping bypass fails; original restored passes"}], "artifact_notes": ["Existing daily digest absent for 2026-10-05; no DIGEST protocol requested or fabricated.", "Existing Nexus source packet checks have 3 stale base_draft_digest values; graph promotion remains gated."]}

## Token 與 Broker 對帳

| 階段 | 呼叫 | 辯論嘗試 | 失敗呼叫 | 平均 token／呼叫 | P50 | P95 | 未知樣本 |
|---|---:|---:|---:|---:|---:|---:|---:|
| preflight | 24 | 13 | 1 | 20,298.8 | 20,111.0 | 21,364.0 | 0 |
| live | 28 | 15 | 2 | 20,496.2 | 20,397.0 | 21,298.0 | 2 |
Broker 對帳：一致；本地 52 筆呼叫，Broker 52 筆 execution，另有 1 筆尚無 execution 的預約紀錄。
Live 平均 token／辯論：40,992.3；每張有效卡：未知。

| Live 用量欄位 | 合計 | 平均／呼叫 | 缺失筆數 |
|---|---:|---:|---:|
| input_tokens | 513,058.0 | 19,733.0 | 2 |
| output_tokens | 19,842.0 | 763.2 | 2 |
| cache_read_tokens | 0.0 | 0.0 | 2 |
| reasoning_tokens | 13,071.0 | 502.7 | 2 |
| total_tokens | 未知 | 未知 | 28 |
| comparable_tokens | 532,900.0 | 20,496.2 | 2 |

## 來源與研究結果

主張狀態：{"insufficient": 5, "supported": 14}。
主張種類：{"question": 7, "fact": 11, "inference": 1}；13 個事件產出卡片，17 張卡僅有 feed 摘錄。
可供個股頁篩選的 ticker：AKZOY, BNO, FLXS, LEVI, PEP, PTC。
觸發分布（呼叫數）：{"news": 28}。

| 來源 | 狀態 | 取得 | 6 小時內 | HTTP |
|---|---|---:|---:|---|
| Yahoo Finance | not_modified | 0 | 0 | 304 |
| MarketWatch | ok | 10 | 4 | 200 |
| CNBC Top | ok | 30 | 4 | 200 |
| CNBC Markets | ok | 30 | 0 | 200 |
| CNBC Economy | ok | 30 | 0 | 200 |
| Seeking Alpha | not_modified | 0 | 0 | 304 |
| Investing.com | ok | 10 | 10 | 200 |
| FinancialJuice | ok | 100 | 9 | 200 |
| PR Newswire | ok | 20 | 0 | 200 |
| Fed Press | not_modified | 0 | 0 | 304 |
| SEC Press | not_modified | 0 | 0 | 304 |
| FTC Competition | ok | 30 | 0 | 200 |
| Census Indicators | not_modified | 0 | 0 | 304 |
| EIA Press | not_modified | 0 | 0 | 304 |
| BLS CPI | backoff | 0 | 0 | 403 |
| BLS Employment | backoff | 0 | 0 | 403 |
| BEA Releases | not_modified | 0 | 0 | 304 |
| NVIDIA IR | ok | 20 | 0 | 200 |
| Nasdaq Markets | ok | 15 | 15 | 200 |
| Benzinga | not_modified | 0 | 0 | 304 |
| FMP | ok | 27 | 27 | — |
| Finnhub | ok | 1 | 1 | — |
| SEC EDGAR | ok | 0 | 0 | — |
| Social | degraded | 18 | 0 | — |
| Futu Push | ok | 0 | 0 | — |

## 結論與限制

已完成觀察，需先處理對帳或中斷問題。
實際啟動 15／30 次辯論嘗試，其中 13 次完成 A/B；使用 28／60 次呼叫。上限不是必須填滿的樣本量。
四種觸發的辯論嘗試：{"news": 15, "filing": 0, "calendar": 0, "followup": 0}；零樣本類別僅有初步案例／確定性測試覆蓋，不能宣稱已驗證真實事件表現。
- A/B 皆為 gpt-6-luna max；不是跨模型獨立驗證。
- 平均值包含失敗呼叫；缺失 token 不補零，分母僅含已測得樣本。
- Codex cache input／reasoning 為子集合，不重複加總。
- 有效卡指通過格式及原文引用閘、未撤回的卡，仍包含爭議及證據不足；不等於已證實。
- 低事件量不補造事件；六小時結果不能代表長期投資績效。

詳細逐筆用量、缺失欄位與對帳錯誤見同名 JSON。

## 執行可靠性與來源觀察

觀察窗內完成 32 次取材。心跳超過 180 秒的區間 1 段，共 453.4 秒；這是保守的中斷指標，不直接等同漏掉新聞數。
Broker provider_busy 等候後恢復 2 次；只在 Broker 回報空閒後重新申請，不以模型呼叫探測狀態。
逐頁接線驗證：{"invest": {"http": 200, "cards": 4}, "earnings": {"http": 200, "cards": 4}, "momentum": {"http": 200, "cards": 4}, "nexus": {"http": 200, "cards": 4}, "LEVI": {"http": 200, "cards": 1, "top3": true}, "BNO": {"http": 200, "cards": 2, "top3": true}, "at": "2026-10-04T20:21:12.855013+00:00", "visual": "Unavailable: no controllable browser window; HTTP and JS syntax verified", "PTC": {"http": 200, "cards": 1, "top3": true, "exploratory": true}, "AKZOY": {"http": 200, "cards": 1, "top3": true, "exploratory": true}, "FLXS": {"http": 200, "cards": 2, "top3": true, "exploratory": true}, "served_provenance_labels": true}。

| 來源 | Poll 次數 | 狀態分布 | 最長毫秒 |
|---|---:|---|---:|
| Yahoo Finance | 32 | {"not_modified": 32} | 681 |
| MarketWatch | 32 | {"ok": 32} | 905 |
| CNBC Top | 32 | {"ok": 32} | 903 |
| CNBC Markets | 32 | {"ok": 32} | 908 |
| CNBC Economy | 32 | {"ok": 32} | 656 |
| Seeking Alpha | 32 | {"not_modified": 25, "ok": 7} | 6591 |
| Investing.com | 32 | {"ok": 31, "not_modified": 1} | 371 |
| FinancialJuice | 32 | {"ok": 32} | 937 |
| PR Newswire | 32 | {"ok": 32} | 402 |
| Fed Press | 32 | {"not_modified": 29, "error": 1, "backoff": 1, "ok": 1} | 639 |
| SEC Press | 32 | {"not_modified": 31, "ok": 1} | 278 |
| FTC Competition | 32 | {"ok": 32} | 1189 |
| Census Indicators | 32 | {"not_modified": 32} | 3043 |
| EIA Press | 32 | {"not_modified": 31, "ok": 1} | 10642 |
| BLS CPI | 32 | {"error": 4, "backoff": 28} | 299 |
| BLS Employment | 32 | {"error": 4, "backoff": 28} | 289 |
| BEA Releases | 32 | {"not_modified": 32} | 1197 |
| NVIDIA IR | 32 | {"ok": 32} | 1928 |
| Nasdaq Markets | 32 | {"ok": 32} | 3472 |
| Benzinga | 32 | {"not_modified": 29, "ok": 3} | 3305 |
| FMP | 32 | {"ok": 32} | 4221 |
| Finnhub | 32 | {"ok": 32} | 2077 |
| SEC EDGAR | 32 | {"ok": 32} | 984 |
| Social | 32 | {"degraded": 31, "error": 1} | 90020 |
| Futu Push | 32 | {"error": 30, "ok": 2} | 15036 |

執行事件：2026-10-04T18:15:25.764214+00:00；Futu local directory scan blocked in opendir under launchd；修正：optional discovery adapters isolated in bounded subprocesses; primary poll survives timeout。

執行事件：2026-10-04T18:20:35.033924+00:00；native invalid_json_schema for empty ticker set; first failed live call usage unavailable；修正：removed unsupported zero-length array constraint; deterministic symbol subset gate retained; process errors now stop intake calls; unknown usage remains unknown。

執行事件：2026-10-04T18:24:38.643272+00:00；first five live attempts included low-increment weekly preview and generic political news；修正：preview awaits actual release; events require a public ticker, primary official source, or explicit economic transmission channel; historical outputs retained。

執行事件：2026-10-04T19:24:24.006751+00:00；company name present only in summary was not mapped to ticker in earlier sample；修正：company-name resolution now scans title and summary; earlier model outputs retained as observed。

執行事件：2026-10-04T19:27:54.958116+00:00；Micron alias missed; first-person stock-picking headline consumed a research slot；修正：reuse existing Nexus ticker aliases; explicit buy/sell opinion headlines require new primary evidence。

執行事件：2026-10-04T19:28:34.574827+00:00；launcher environment handoff timed out during idle reload; old worker and failed job confirmed absent；修正：one fresh launch after confirmed teardown; no model call was active。

執行事件：2026-10-04T21:08:06.629410+00:00；shared Codex provider_busy paused research; FMP associated an unrelated city hearing with CHCO；修正：wait for a read-only broker free-slot observation before resuming; provider ticker hints alone no longer admit an event; preserve inference caps and auth/quota stops。

執行事件：2026-10-04T21:16:43.764437+00:00；New high-priority event could hide an acknowledged result awaiting publication at the call limit.；修正：Prioritize pending events with an existing debate_id. Regression reproduced before fix and 38 research tests passed after fix. Idle worker reload; no extra inference.。

執行事件：2026-10-04T23:25:28.166359+00:00；Live call rd_915215910b42427da46e24b839f906eb_a exited with quota error and no native token usage.；修正：Broker acknowledged unknown usage; new inference remains paused, no retry. Read-only source observation continues through original six-hour deadline.。

## 研究卡樣本

資料庫保留本輪所有版本；目前 19 張未被新版本取代。以下最多五例，完整卡片摘要及來源 URL 見 JSON。

1. **FLXS｜fact／supported**（包含原始網頁片段）
   MarketBeat報導稱，FLXS在投資人會議說明爭取市占、擴大利潤率及創造現金的策略；高管並稱家具業近期仍具挑戰。摘錄未提供量化指引或策略成效。
   審查：摘錄支持 FLXS 在投資人會議說明爭取市占、利潤率擴張及現金創造策略，也支持高管稱家具業近期仍具挑戰；摘錄未提供量化指引或策略成效。
   反證：完整會議資料或公司後續披露若顯示摘錄對策略或近期產業狀況的描述不準確，則此報導摘要不成立。；追蹤：觀察公司後續會議資料或申報文件是否披露策略目標、量化指引及家具市場狀況。

2. **總體／未對應 ticker｜inference／supported**（只有來源摘要）
   若民主黨在11月期中選舉後取得參議院控制權，川普的潛在最高法院提名可能受阻；目前選舉結果及提名進展都尚未確定。
   審查：證據稱民主黨可能在11月期中選舉後取得參議院控制權，並危及川普潛在的最高法院提名；用條件式表述保留了選舉結果與提名進展的不確定性。
   反證：期中選舉後參議院未由民主黨控制，或相關提名仍順利推進。；追蹤：公布期中選舉後的參議院控制權，並觀察是否出現退休空缺及後續提名進展。

3. **總體／未對應 ticker｜question／insufficient**（只有來源摘要）
   目前摘錄未說明沙烏地阿美的產出、設施運作或出口是否中斷，也未提供獨立確認；實際供應影響仍待查證。
   審查：提供的摘錄未交代沙烏地阿美設施運作、產出或出口是否受影響，也沒有獨立確認；因此實際供應影響無法由此判定。
   反證：後續可靠報導確認設施運作與出口均未受影響，或確認已有供應中斷。；追蹤：觀察後續可靠報導是否確認設施損害、運作狀況或產出與出口中斷。

4. **總體／未對應 ticker｜fact／supported**（只有來源摘要）
   路透摘錄稱，胡塞武裝攻擊沙烏地阿美設施後，布蘭特原油期貨升至每桶 103.06 美元；這是來源報導的市場變動，摘錄本身不能確認攻擊造成上漲。
   審查：摘錄明確報導布蘭特原油期貨升至每桶 103.06 美元；摘錄不足以證明攻擊造成這項漲勢。
   反證：路透後續更正報價，或指出布蘭特期貨並未升至該價位。；追蹤：觀察路透是否更正這則報導或其所述期貨價格。


## 本輪判斷

用量治理仍有缺口：應先補齊上列未知或未對帳紀錄，不能用目前平均數當完整成本。
本輪產出 19 張未撤回研究卡；支援項與爭議／不足項應分別閱讀，A/B 一致不代表多個獨立來源。
新機制可提供原文、主張、反證與追蹤條件給各分頁；本輪結果只驗證研究資料流及成本，不能推論交易績效。
下一輪優先處理反覆失敗來源、只有摘要的高影響事件，以及本輪沒有真實樣本的觸發類型。

## 舊機制比較

歷史樣本 182 次辯論、451 次呼叫，平均 2.48 次呼叫／辯論；新機制每次完整辯論為兩次。
歷史 token 可量測 15 筆、缺失 436 筆，不能據此宣稱精確節省比例；事件與模型組合亦不同。

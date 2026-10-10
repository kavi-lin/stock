# 個股分析 V5.5 工程驗收

版本 4.137.0；工程五批已實作，2026-10-01 23:02 完成使用者指定的 HPE 重跑後，三股實際試跑完整驗收成功數為 **1／3**，成功試行累積 **1／5**。正式權重、門檻、情緒 LLM 評分、Red Team 懲罰維持現況。V5.5 仍由 `--v55` 選用，尚未切成預設。

## 五批交付

| 批次 | 已實作行為 | 主要檔案 |
|---|---|---|
| 1 資料 | 財報／市場／報價分層快取、真實來源時鐘、季度失效、不可變快照、固定價格、共用 FMP 限流 | run_data.py、collect_run_inputs.py、skills/_shared/investment_data.py |
| 2 執行 | 五份 prompt 先凍結、1–3 名額隔離派工、即時驗收、一次重試、配額停機、hash／版本續跑、原子提交 | run_investment.py、run_protocol_manual.py |
| 3 對照 | V5.5 run_context、程式 sentiment_det／det_inputs、lane 來源、FMP／時間／token 遙測 | run_exports.py、build_session_export.py |
| 4 檢討 | 已提交 JSON 優先、穩定 ID／歧義、歷史分類凍結、評估 sidecar、完整有限窗口 | committed_investment.py、build_event_index.py |
| 5 校準 | synthetic 排除、按股票群組 bootstrap、RT 分組報酬／回撤／交易條件觸及率、論點事件證據獨立、套完 cap 的策略候選重播 | run_observability.py |

## 指定模型試跑

模型為 `gpt-6-luna`，effort=`max`，沿用既有 broker／registry。首輪 HPE／NVDA／BE 模型階段分別耗時 1972／2045／2043 秒（約 33／34／34 分鐘），完整驗收成功數為 0／3；三次執行期間皆確認 380 個受監測 Python 檔案未變。每次呼叫與失敗保留於 [機器可讀驗收紀錄](investment_v55_engineering_acceptance.json)。以下保留首輪結果。

| 股票 | 正式入口試跑 | 修正後保存輸入重播 |
|---|---|---|
| HPE | 五線驗收完成；模型修改已封存 RT prompt，被 hash 閘攔下；尚未呼叫 RT／計算決策 | 控制器已補齊封存前 Phase 0／FRED；隔離與竄改測試通過，未重跑模型 |
| NVDA | 五線、RT、定倉完成；最終 Phase 4.6 閘拒絕提交 | JSON／MD rc=0；HOLD，score 0.7151，confidence 0.65，position 0 |
| BE | 五線、RT、定倉完成；technical 舊字串形狀造成 renderer 失敗 | JSON／MD rc=0；HOLD，score 0.2824，position 0 |

[NVDA 工程重播報告](trial_replays/NVDA_cap_replay.md) · [BE 工程重播報告](trial_replays/BE_fixed_replay.md)。重播沒有呼叫模型，也沒有改寫或提交原場次。

早先 NVDA `NVDA_20261001T003605_0eab632f7a` 雖已提交，事後查到 Burry 原始 `burry_score` 未映射 `score`。原 history 保留；新增 evidence gate 與索引已排除該筆，不能計入成功試行。修正映射後，該筆決策重播數字不變。

### HPE 指定重跑：已完成

使用者另行要求「重跑 HPE」後，場次 `HPE_20261001T223002_25eeeee46b` 於 2026-10-01 23:02（台北）完成正式提交。主流程耗時 2040 秒（34 分鐘）；啟動前等待 Dashboard 佇列 213 秒，broker 等待 2.857 秒。五條分析線與 Red Team 均使用 `gpt-6-luna / max`，第一次驗收即通過，執行品質 complete。

JSON 與 Markdown validator 均 rc=0；快照／prompt／產物 hash、export provenance 通過，history 中此 run_id 恰好一筆且與 session.json 相同。380 個受監測 Python 檔案未變，未改寫前次失敗場次。結果為 STAGED_ENTRY，score 0.9422，計算部位 3.5375%，凍結價格 $62.99；Red Team 為 STRONG_COUNTER，非 synthetic。此為分析提案，沒有送出券商交易。

[HPE 不可變場次報告](../../investment/invest_logs/runs/HPE_20261001T223002_25eeeee46b/report.md)。Host receipt 回報 input 11,846,021、cached input 11,467,776、output 76,508 tokens；子 agent 是否包含於 host receipt 依供應商口徑，lane 未提供的 token 仍為 unknown，不重複加總。

## 驗證與限制

1. 新流程 48 項離線測試通過，含完整 prepare→commit、盈利／虧損／同業不足、名額 1／2／3、來源／hash 注入、驗證斷線突變、重複提交、JSON 權威、完整窗口與 synthetic 排除。
2. 真實 NVDA 揭露 Phase 4.6 漏接與部位欄位取錯；現已自動呼叫既有 cap／speculative governor，保留原 Phase 3 證據，並逐欄重算驗證。原 .694 信心按既有規則封頂 .65，沒有改策略參數。
3. 既有 quant、decision、position、assembler、renderer、export、broker、earnings 與 forecaster 對應測試通過。201 筆歷史重播與基線數字一致；既存 11 筆歷史 decision mismatch 未改寫。
4. News parenthetical parser 有既存單項回歸失敗，位置為 `scripts/extractors/tests/test_extractors_review_fixes.py::test_news_digest_parenthetical_backcompat`；不屬本次個股修改。
5. 5 場成功試行與 20 場觀測仍待日常累積；目前資料不能證明節省多少時間或成本。供應商未提供的 lane token 保留 unknown；host receipt 不與 lane receipt 相加。

HPE 成功重跑前建立的索引保留 566 筆紀錄，其中 206 筆來自已提交 JSON，205 筆具完整有限價格窗口；RT 校準有效 156 筆，另 49 筆執行品質不完整、1 筆窗口或來源未合格。新 HPE 的事後窗口尚未完成，沒有加入這批校準。每個指標另列獨立股票數、集中度與區間，不能把 156 筆視為 156 個完全獨立樣本。

[流程健康與策略候選](investment_process_health.json) 保留有效樣本數、集中度、信賴區間及排除原因；所有策略候選都需要另外核准。

Git 修改基線與既有未提交工作保留於 `tmp/investment-v55-baseline/`；未建立 commit，未批次改寫歷史決策。操作入口見 `investment/run_workflow_v55.md`。

原先「離線測試通過即可順利跑完整場」的假設已被首輪試跑否證。首輪後曾暫停模型重跑；本次只依使用者新指示完成 HPE，沒有另啟動 NVDA／BE。後續成功樣本由日常分析累積。前次缺陷與 HPE 的 prompt 修改均留下原證據，離線重播不計為正式成功。

維護收尾：版號三處同步為 4.137.0，agent context 同步通過；CHANGELOG 超過輪替門檻，v4.135 以前的 12,579 行已逐字保留至 `archive/changelog_pre_v4.135.md`，搬移前副本另存於驗收基線目錄。

# V5.5 場次執行路徑（試行）

正式評分、權重、Red Team 懲罰、買進門檻與部位公式均沿用現行 protocol。
此文件只取代資料搬運、派工排程與提交步驟。`AIC_INVEST_RUNNER=v55` 啟用試行；
未啟用時走相容入口。回退不會關閉來源時間與快取期限防線。

## 1. 準備與凍結

依 `investment_protocol_v5_0.md` 完成 Phase 0/1。新產生的 Phase 0 必須保存
真正取得資料時的 `fetched_at`（UTC ISO timestamp）；不得替舊快照補現在時間。
舊檔只有 `scan_date` 或 mtime 時重新執行 Phase 0。有效期限 3 小時，既有
`validate_phase0.py --path` 仍必過。

Phase 0 草稿內的 `fred_snapshot` 使用本次 FRED fetch 原始輸出，然後執行
`python3 investment/scripts/assemble_phase0.py --input <DRAFT> --out <NEW_CANONICAL_PATH>`。
組裝器共用 cache reader 的 FRED 欄位映射、保留原始來源時間，並執行 validator；
拒絕覆寫既有檔案。schema／參數組裝錯誤可依同一真實來源修正一次，再走同一驗證；
不得修改來源值、時間、hash 或程式碼來通過閘門。第二次失敗保存進度並停止。

直接執行 prepare，由控制器收集 deterministic skill script、DCF/comps、forecaster
與 factpack；原始輸出和執行收據保存於場次的 `raw/`。PM 不需逐支執行或搬運 JSON。
Forecaster 的 PE 歷史不足、DCF/comps 缺資料等選用來源錯誤，保存 null 與原因，
沿用既有信心與 decision cap；這類缺漏不屬於必須停止整場的 validator 失敗。
保留 Finnhub scoring 與 FMP audit 分工；報價、有效 Phase 0 與最新財報期間確認仍為必要閘門。

```bash
python3 investment/scripts/run_investment.py prepare --ticker <T> --phase0 <EXACT_PHASE0_PATH>
```

保存回傳的 `run_id` 與 `directory`，後面所有輸入、輸出都放在該目錄。prepare 會確認
最新財報期間、抓 5 分鐘內報價、凍結 quant 原料／原始來源／五條 lane 輸入，產出
`quant.json`，並在任何 lane 回傳前寫好全部五份 `prompts/<lane>.json`。
禁止用最新快取替代快照。財報 7 天、市場估值資料 24 小時、forecaster 4 小時；
新財報使相關快取失效。選用資料更新失敗保留缺漏；報價／Phase 0 不可用直接停止。

已有可靠原始資料時仍可明確傳入 `--factpack`／`--lane-data`；缺來源時間須重新抓取。
`--package` 僅供離線 fixture，產生的場次禁止提交正式 history。

## 2. 隔離派工與立即驗收

能力與可用模型以現行 registry/certification 和宿主工具為準。使用者指定模型／effort
時保留指定值；不要把文件中的 Claude 語法或舊白名單當成現行模型限制。
同時執行數 = min(3, 環境可用名額)，未知為 1。分批本身不算失敗。

```bash
python3 investment/scripts/run_investment.py claim <RUN_ID> --slots <1_TO_3> --model <ACTUAL_MODEL> --effort <ACTUAL_EFFORT>
```

只派工回傳的 claimed lanes；每條使用獨立 context，逐字讀自己的凍結 prompt。
不得注入其他 lane 結果、PM 結論或歷史 bias。量化估值直接讀 `quant.json`。
每條完成立即寫 JSON 並驗收，再取得下一批：

```bash
python3 investment/scripts/run_investment.py accept <RUN_ID> --stage <LANE> --result <RESULT.json>
python3 investment/scripts/run_investment.py status <RUN_ID>
```

供應商有 token receipt 時用 `--usage` 傳入 `{input,output,cached}`；缺欄位保留 null。
schema 錯誤自動進 retry，最多一次；一般執行錯誤用 `fail --reason execution`。
兩次失敗後 `claim --fallback --stage <LANE>`，沿用既有 inline 降級規則，收件用
`accept --degraded`，confidence ≤0.6。Red Team 始終使用隔離 subagent；其執行失敗
沿用原有禁止新增部位規則，不能 inline 補一份正常裁決。
配額／登入錯誤用 `fail --reason quota|authentication`，保存進度並停止模型呼叫。
不得重複用 prompt 查進度。

五線完成後，控制器才建立 `prompts/red_team.json`，包含凍結的 Phase 0／FRED。
不得直接修改 `prompts/` 檔案；背景若缺失應停下回報，不能自行補寫已封存 prompt。
將 protocol 要求的 Burry／
conflict-bias 存為 `{burry: {...}, conflict_bias: {...}}`，使用
`claim <RUN_ID> --stage red_team --context <CONTEXT.json> --model <ACTUAL_MODEL> --effort <ACTUAL_EFFORT>`
凍結 context；後續 p3／export 必須相符。RT 正常回傳必含 ticker、verdict、
counter_thesis、kill_conditions、counter_evidence_strength、thesis_break_probability、subagent_isolated=true。

## 3. 決策、風控與提交

PM 繼續負責 Burry、Phase 2.5、risk 的質性輸入。p3 的 lane 數字／RT 必須原樣來自
已驗收結果；macro 與 forward_validation 必須來自快照與 quant。

```bash
python3 investment/scripts/run_investment.py compute <RUN_ID> --p3-input <RUN_DIR>/p3_draft.json
python3 investment/scripts/compute_price_framework.py --stage mhp --from-quant <RUN_DIR>/quant.json --from-file <RUN_DIR>/mhp_qualitative.json
python3 investment/scripts/run_investment.py compute <RUN_ID> --p3-input <RUN_DIR>/p3_draft.json --p4-input <RUN_DIR>/p4_draft.json --mhp-input <RUN_DIR>/mhp_qualitative.json
python3 investment/scripts/run_investment.py finalize <RUN_ID> --qualitative <RUN_DIR>/qualitative_draft.json
```

p3 `decision_cap` 的 anchors_available／fair_value_confidence 必須逐字取自 quant 的 fair_value_summary。
p4 `analysis_price` 必須等於快照價格，MHP 必須等於以凍結 quant 計算的程式產物。finalize 共用既有 assembler、export validator、
renderer、Markdown validator 與 history 原子鎖；任一閘不過就不提交。
assembler 在 Phase 4 定倉後自動呼叫既有 Phase 4.6 cap／speculative governor，
從 risk_audit 讀取實際部位；原 Phase 3 產物不改寫。export 的 `phase4_6` 保留完整
調整 trace，V5.5 validator 以場次引擎產物重算比對，PM 不得手動搬運或覆寫。
`session.json` 為 V5.5，run_context、lane provenance、sentiment_det、det_inputs 由
程式填入；模型不得手填。完整報告保留在場次 `report.md`，並發布既有 reports 路徑。
同 run_id／相同內容重做不會多一筆 history；內容不同直接拒絕。

## 4. 續跑、觀測與回退

`resume <RUN_ID>` 檢查版本、快照、prompt、完成產物與依賴 hash，並再次確認最新財報
期間。僅重用已驗證結果；running 工作先確認原宿主是否還活著，不得直接重發。
快照超過 3 小時或新財報已到時建立新 run；原場次保留。
配額／登入恢復後，才可用 `resume <RUN_ID> --recovered "具體狀態改變證據"` 解除停機。

```bash
python3 investment/scripts/run_observability.py
```

報表在 `reports/decision_review/investment_process_health.json`。前 5 場為試行、前
20 場觀測；尚未達標不自動切換預設。RT 校準排除 synthetic、incomplete、未完成
窗口與非有限價格；論點成立需事件證據。情緒方向翻轉率 <20% 且有效樣本 ≥20 只
產生提案，仍需使用者核准。沒有實際模型／完整窗口樣本時如實回報零樣本。

# 事件研究與辯論

此層發現值得研究的問題，供其他分頁閱讀與追蹤。正式 investment 決策、position sizing、Nexus 獨立來源晉升門檻不讀入此層結論。

```text
Before
RSS / Futu / social -> 新聞門檻 -> A / B / 回應 / 仲裁 (2–4 calls)
                                      |
                              一個 bullish/bearish verdict
                                      |
                           Signal Queue -> 分頁候選

After
RSS + FMP + Finnhub + SEC + IR + macro
                 |  來源健康 / 原始 URL / 轉載脈絡 / 發布時間
                 v
       事件 + 證據版本 <---- calendar due / followup due
                 |          (只要求新證據，不直接叫模型)
           重大且新增的證據
                 v
        Broker reserve/start -> Luna/max A -> Luna/max B
                 |                   |             |
                 |          原文驗證 / 主張逐項審查
                 |                   v
                 +------ durable result + settlement outbox
                                     |
                         Broker ACK + token reconciliation
                                     v
                   主張卡 / 爭議 / 反證 / 追蹤條件
                                     |
              個股  財報  動能  事件研究  Nexus provisional
```

`scripts/research/store.py` 持有 SQLite WAL 的 event/revision/card/observation；資料落於 `news/research_cache/`。新內容產生 revision，單純重新抓取或轉載不重新辯論。`intake.py` 共用既有 provider adapters，來源失敗不讀舊輸出；RSS 支援條件式 HTTP、錯誤與退避。發現股票由 maintained public index universe、公司名、來源 ticker tags 解析，無持倉或 watchlist 依賴。

`engine.py` 每次 A/B 最多兩個模型呼叫；固定最多五項主張。`fact`、`inference`、`question` 分開，逐項狀態為 supported/contested/insufficient/retracted。引用必須能在 evidence packet 找到逐字原文。原始網頁片段與 feed 摘錄分別標示；分析者意見不充當來源引證。過期排程、同一份證據的追蹤到期都不直接消耗 token。

GET `/api/research?lane=invest&ticker=NVDA` 回傳上次分析後最多三項變化；lane 也可為 earnings/momentum/nexus/all。POST `/api/research/observe` 接收 lane/ticker/revision；POST `/api/research/track` 接收 claim_id/revision，版本過期拒絕。GET `/api/research/nexus` 僅提供 provisional candidates，不能直接晉升節點。頁面不再嵌入獨立研究面板：`scripts/signal_queue.py` 只把 `supported`／`contested` 的 fact／inference 主張併入 **invest lane** 的 Signal Queue（個股決策頁候選列）。同代碼已有辯論候選就合併加分（不改方向，方向相反標 `research_disagrees`）；只有研究的代碼自成候選，方向不明為 `neutral`（待判讀）。`question`、`insufficient`、`retracted` 不上列。按「加入深度分析」才送進 invest protocol；研究主張本身仍不進入投資決策。

Broker task types 為 `research-initial-analysis`、`research-initial-challenge`、`research-recheck-analysis`、`research-recheck-challenge`，category 為 ensemble。每筆提供 experiment、phase、event、revision、debate、trigger、stage、reasoning effort；native model 與回覆實際回報的 model 分開。正式圖譜與投資資料不寫入 Broker，只有允許的呼叫 metadata、usage 與結果狀態。

實驗順序：確定性測試 → 12 組 Luna/max 初步測試（≤24 呼叫）→ 起算六小時 → 每小時≤5辯論、合計≤30辯論／60呼叫 → 停止新呼叫、補送結算、報告。初步第一筆曾遭 v7 帳本拒絕結算；v8 migration 後原樣補送成功。該筆回覆只留格式驗證結果，原文未保存；首例明列 analysis＋結算復原覆蓋，未計成完整雙聲辯論。後續已先持久保存回覆再結算。

可讀取狀態：`python3 -m scripts.research.experiment status research-20261005`。`report` 子命令可產生中途報告，但只有超過六小時且 runner 收尾後才會標記 final。報告留在 `reports/research_observation_<id>.md`／JSON；input/output/cache/reasoning 分欄，Codex 可比用量為 input+output。缺失值保留未知，不補零。所有失敗呼叫仍列入成本與樣本分母說明。

來源目錄依據：[BLS RSS](https://www.bls.gov/feed/)、[BEA developer feeds](https://www.bea.gov/resources/for-developers)、[NVIDIA IR RSS](https://investor.nvidia.com/investor-resources/rss/default.aspx)、[SEC developer resources](https://www.sec.gov/about/developer-resources)。可用性另以實際抓取狀態為準；2026-10-05 首次驗證 BLS 403，BEA/NVIDIA 200。

Live 期間的修正保留於 experiment.operational_incidents：Futu／社群來源在獨立程序內分別限15／90秒，避免本機權限掃描拖住主取材；RSS 304 保留 ETag。空 ticker 不使用 native service 拒絕的 maxItems=0，改由實際輸出子集合驗證維持不得新增 ticker 的閘。沒有 token 的失敗仍記未知並停止新呼叫，人工檢查原因及修正後才恢復；不以 API 拒絕推定零消耗。

低增量每週前瞻只留 discovery，等待實際發布；其他事件需有公開 ticker、官方原始來源或明確經濟影響途徑。初輪已發出的低增量卡保留在報告，避免用清除失敗樣本美化結果。每個 A/B 階段都檢查六小時截止，截止前已在執行的呼叫可完成結算，截止後不開新推論。

公司別名沿用既有 Nexus alias map，掃描標題與摘要；`identified_tickers` 與 `provider_tickers` 分開。供應商可能誤標（實測紐約市 AI 聽證新聞被標成 CHCO），單獨的 provider hint 不能通過研究門檻，packet 亦標示其未驗證性。Broker `provider_busy` 只查唯讀狀態，等 Codex slot 空閒後重申請同一事件，已 ACK 的 A 階段沿用；quota／auth 等錯誤不走這條自動恢復路徑。

恢復中的既有辯論優先於新事件，避免額度用盡後，新高優先新聞擋住已完成且已對帳的卡片發布；回歸測試同時放入兩類事件，確認不需要新增模型呼叫即可完成發布。

2026-10-05 六小時觀察已結束，worker 已退出；既有卡仍可查閱，新付費觀察窗沒有自動開啟。正式28呼叫、13完整A/B、19卡；含初測52筆Broker逐欄位一致，2筆用量未知。完整判斷、來源限制與測試證據見 [六小時結論](../reports/research_observation_research-20261005_conclusion.md)。

## 取材改由 Break News 辯論升級（`intake: break_news`）

研究層不再自己抓新聞。Break News 是第一層：每則過閘新聞由 broker 依即時額度排出三家，前兩家辯論、第三家只在僵持時裁決（`scripts/break_news/debater.py` 的 `_roster`）。研究是第二層，只深挖辯論結果顯示值得查的項目。`scripts/research/handoff.py` 每次 service poll 掃描 6 小時內收斂的辯論，用程式算升級分數，不呼叫模型：

| 條件 | 分數 |
|---|---|
| 辯論未收斂（`arbitrated`／`unresolved_*`） | 3 |
| 二元事件（`binary_flag`） | 3 |
| ≥3 個來源報導（`echo_count`） | 2 |
| 高優先（`is_high_priority_item`） | 1 |
| 多空結論且信心 ≥0.75 | 1 |
| B 方明確提出爭點 | 1 |

前提是至少一檔 universe ticker；達 `handoff_min_score`（預設 3）才升級。門檻以 2026-10-01～04 的辯論校準：忙碌日約 30–36 則、清淡日 5–10 則，對照研究上限每天 30 組。單有爭點不夠，因為 60–80% 的辯論 B 方都會反駁至少一點。升級後仍要通過研究自己的 6 小時時效與 `research_gate`（觀點專欄、預告文、無財務管道的新聞會被擋），最後由既有的滾動額度決定實際跑幾組。分數高的先跑。

轉載合併成同一事件時，`break_news_ids` 記錄所有來源辯論，升級分數取最高的那次。`/api/break-news/item/<id>` 附上 `research`（升級紀錄、事件狀態、研究卡），辯論室右側面板顯示在合議摘要下方；研究卡不再出現在辯論室頂端。`intake: self` 可切回原本的獨立多來源取材。`break_news` 模式下 `engine.pending` 只接受有 `escalation` 的事件。舊取材留下的 pending 事件不會再開新研究，6 小時後自然過期；已預約（有 `debate_id`）的照常補完結算。

## 正式常駐模式（v4.141.0，使用者另行授權）

`config/research.json` 的 `service_enabled` 啟用後，Dashboard 啟動 `scripts.research.service` 背景工作；與獨立 CLI、六小時實驗共用跨程序鎖，同時只能有一個取材／推論 owner。服务狀態使用 SQLite `service`，不覆寫 `experiment` 或已完成報告；Broker context 使用 `experiment_id=research-production`、`phase=live`。Dashboard 主機關閉時服務跟著停止，下次啟動恢復已持久保存的狀態，不因重啟解除 quota/auth 停止。

四類 research task 的預估為 **22,000 input＋3,000 output＝25,000 token／呼叫**；完整 A/B 預估50,000。這是保留緩衝的送件估計，不是改寫實測平均或實際結算。gpt-6-luna/max 固定不變。Broker 仍以額度、預約、歷史校準及安全係數作最終審核，effort metadata 不代表已獨立完成按 effort 的成本校準。

預設每滾動24小時最多30組／60呼叫、每滾動1小時最多5組。計數包含先前試驗中的真實呼叫，排除合成 preflight；失敗及未知用量照樣計入。設定可收緊但不超過上述上限。限額只是上限，不為填滿額度發起辯論；局部結果優先恢復，原 call ID 不重複推論。

Broker 忙碌或尚未執行模型前的 cooldown 拒絕，會查狀態、確認容量後續跑；不使用 LLM 探測狀態。cooldown 解除還需 `reserve=false` 預檢通過。真正已啟動的模型若 quota/auth/未知用量失敗，停止新推論，補送結算不能清除停止原因。來源取材仍繼續。API `/api/research` 增加 `service`，面板顯示正式狀態、heartbeat、預估、滾動用量及阻擋原因。

操作：`python3 -m scripts.research.service status` 查看狀態；`stop` 請求停止，新階段不再啟動。人工確認外部問題解決後，可使用 `resume --reason "已核實的恢復原因"`；命令必先確認結算 ACK 與 Broker 預檢通過，不補零或重跑失敗呼叫。若 worker 已停止，恢復後再正常重啟 Dashboard（或執行 `python3 -m scripts.research.service run`）。既有 user session 環境由 Dashboard launcher 記憶體交付，不新增憑證檔。

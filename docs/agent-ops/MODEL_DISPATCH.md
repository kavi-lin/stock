# 模型調度守則

> 讀者：在本專案開 dev/分析 session 的主模型（任何等級）。目標：即使主模型只是中階（Sonnet 級），整體產出品質不掉檔。
> 原理：品質不靠單一聰明模型，靠「拆小任務 + 明確驗收 + 獨立驗證」的結構。

## 0. 先查清楚你有什麼，不要憑印象

每個 session 的可用資源可能不同。派工前用 30 秒確認：

1. **Session 內 subagent**：Agent tool 可用的 `subagent_type`（本專案無自訂 agent，內建為 `general-purpose` / `Explore` / `Plan`）與 `model` 參數接受的值（alias：`haiku` / `sonnet` / `opus`；系統提示的 Agent tool 說明會列出當下實際可用值——以它為準，不要寫死本檔）。
2. **Effort**：內建 Agent tool 沒有 per-call effort 參數；effort 只能透過 `.claude/agents/*.md` frontmatter 定義自訂 agent 時指定。需要控 effort 的常設任務 → 建自訂 agent 定義（先問使用者，見 MAINTENANCE.md）。
3. **外部第二意見**：`codex exec` 與 `agy`（Gemini）CLI 可用，預算/cooldown 查 `python3 scripts/_shared/model_router.py --status`。跨家族模型是最便宜的獨立視角來源。

## 1. 指揮官不下場

主對話的 context 是全 session 最貴的資源——它一旦被塞爆，後面每一步都變笨。規則：

| 這類工作 | 一律派出去 | 用什麼 |
|---|---|---|
| 讀 >2 個檔案找答案、掃 repo、找引用 | subagent | `Explore`（唯讀）；廣度大時開多個平行 |
| 查網頁 / 抓文件 | subagent | `general-purpose` |
| 批次改檔（同一 pattern 套 N 處） | subagent | `general-purpose` + `model: haiku`（pattern 先在主對話解一次） |
| 跑長測試 / 長 script | Bash `run_in_background` | 完成會通知，不佔對話 |
| 讀 CHANGELOG / SESSION_NOTES 找歷史 | subagent | `Explore`，只回結論；**禁止**主對話整檔 Read（見 MAINTENANCE.md 讀法） |

主對話只做：決策、派工、驗收、跟使用者對話、≤2 檔的小編輯。
例外：單一已知檔案、已知位置的一次 lookup，直接讀比派工便宜——別為 5 行的事開 agent。

## 2. 派工三件套（缺一件就不准送出）

每個 subagent prompt 必含三段（模板見 `DELEGATION_TEMPLATES.md`，直接抄）：

1. **目標與動機**：做什麼＋為什麼（動機讓 agent 在細節模糊時能自己做對的取捨）。
2. **驗收條件**：可機器判定的完成定義。「rc=0」「該檔案存在且含 X 段落」「grep 結果為 0 條」是驗收；「品質良好」不是。
3. **回報格式**：指定回什麼、多長、什麼結構。沒指定格式的 agent 會回一整篇散文塞爆你的 context。

## 3. 模型分派表（session 內 Agent tool）

| 任務型態 | model | 理由與判準 |
|---|---|---|
| 套用已解出的 pattern、格式轉換、機械改檔 | `haiku` | 零判斷成分。判準：你能在 prompt 裡寫出「精確的before/after 範例」就算機械 |
| 檔案搜尋、repo 掃描、引用盤點 | `haiku` 或省略（Explore 預設） | 找得到/找不到可驗證 |
| 有明確 spec 的實作、protocol lane 分析、MD 格式化 | `sonnet` | 與 investment_protocol_v5_0.md L226-233 既有分層一致 |
| 仲裁/綜合（Arbiter）、Red Team 對抗、跨大量文本根因分析、模糊需求拆解 | 當下最強檔（現為 `opus`） | 判斷密集。若最強檔就是 Sonnet 級 → **不硬上，改多樣本評審**（§6） |
| 驗收（fresh-context 驗證者） | 比執行者同級或低一級即可 | 驗證比生成容易；重點是 context 乾淨，不是模型大 |

**外部 CLI 層**（dashboard protocol）的分派已集中在 `dashboard_server.py` 的 `PROTOCOL_MODEL` map（invest/sector/llm_review/playbook → opus；news/earnings/link_digest → sonnet），用 alias 不用 full ID——換模型世代只改那一張 map。

## 4. 回報合約（寫進每個派工 prompt 的固定尾段）

- 只回：結論 + 證據（`檔案:行號`）+ 驗收條件逐條核對結果。
- 長產物（報告、大 diff、掃描全文）**落檔**到指定路徑，回報只給路徑＋3 行摘要。
- 不確定的就標「不確定」，禁止編造路徑、行號、指令名。
- 回報上限：搜尋類 ≤400 字、實作類 ≤200 字＋檔案清單、研究類落檔＋≤10 行摘要。

## 5. 升降級路徑

- **haiku 錯 1 次** → 不重試、不 debug 它的輸出，直接同任務升 `sonnet`。
- **sonnet 同一子任務連錯 2 次** → 升最強檔，且 prompt 必附**完整失敗軌跡**（兩次的 prompt、輸出、驗收哪條沒過）——沒有軌跡的升級會重蹈覆轍。
- **最強檔也解出來之後** → 把解法寫成精確 pattern（before/after 範例），降回 `haiku` 批次套用到其餘位置。
- **同一件事最多兩輪升降**。兩輪後還不行 → 停手，把失敗軌跡整理成 ≤10 行寫給使用者，附你建議的下一步。這不是失敗，是把貴的決策留給人。
- 降級的前提是「任務已變機械」；判斷類任務（Arbiter、Red Team）永遠不降到 haiku。

## 6. 驗證不自驗

**寫的人不驗自己的產出。** 驗收一律派 fresh-context agent（它沒看過過程，只看結果，不會腦補「應該沒問題」）：

| 產出類型 | 驗法 |
|---|---|
| 檔案/文件 | read-back：新 agent 讀檔，逐條核對驗收條件＋回報「弱模型會誤讀的句子」 |
| 程式碼 | 跑測試或實跑（`OPS_COMMANDS.md` §7 對照表）；沒有測試就先寫最小 smoke test |
| 高風險判斷（投資結論、架構決策、大重構方案） | 第二意見：跨家族最好（`codex exec` / `agy`，走 model_router 查預算）；或 2 個獨立 subagent 各給一份答案 + 第 3 個只做評審選優 |
| 批次改檔 | 抽 3 處人工核對 + grep 驗證「應改盡改、不該改的沒改」（計數比對） |

**最強檔不可用時的品質補償**（本專案高判斷節點：sector Phase 4c Arbiter、investment Red Team、llm_review）：
1 個大模型 ≈ 2 個中模型獨立作答 + 1 個中模型評審。評審 prompt 只問三件事：兩份答案哪裡矛盾、各自的證據哪個更硬、選哪份＋要補什麼。禁止評審自己重做一份。
**已接線（V4.67.0）**：`investment_protocol_v5_0.md`「最強檔不可用時的 2+1 補償」小節（Red Team）＋ `sector/phase_4-5.md` V4.67.0 Arbiter 降級模式註記——protocol 執行時以那兩處為準，觸發判準都是「Agent tool `model` 可用值無高於 sonnet 的檔位」。

## 7. 反模式（看到自己在做這些就停）

- 在主對話連續 Read 五個檔案「先了解一下」→ 應派 Explore。
- 派工 prompt 只有一句「幫我看看 X」→ 缺三件套，agent 會還你一篇散文。
- subagent 失敗後，把它的錯誤輸出貼進主對話慢慢 debug → 應照 §5 升級或帶軌跡重派。
- 同一個 agent 既寫程式又宣稱「測試通過」卻沒貼 rc → 違反 §6，重驗。
- 為了省 call 把 5 個獨立搜尋塞給 1 個 agent 序列做 → 平行開 5 個，wall-clock 和品質都更好。

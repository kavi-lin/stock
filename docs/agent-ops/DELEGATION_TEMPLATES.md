# 派工 Prompt 模板

> 用法：複製對應模板 → 填 `【】` 空格 → 作為 Agent tool 的 prompt 送出。
> 每份模板已內建三件套（目標動機／驗收條件／回報格式）與回報合約。`model` 建議值見 MODEL_DISPATCH.md §3。
> 通用鐵則：專案根目錄一律寫絕對路徑 `/Users/kavi/Developer/Claude/Projects/ai-investment-committee`，subagent 沒有你的對話記憶。

---

## T1 搜尋／盤點（subagent_type: Explore；model: 預設即可）

```
專案根目錄：/Users/kavi/Developer/Claude/Projects/ai-investment-committee

【目標】找出【要找什麼，例：所有引用 investment_protocol_v4_8 的活文件】。
【動機】【為什麼找，例：舊檔已歸檔，殘留引用會讓弱模型讀錯真相來源】。

範圍：【目錄/檔案類型，例：*.md *.py，排除 reports/ logs/ cache/ CHANGELOG SESSION_NOTES】
搜索廣度：【medium / very thorough】

【驗收條件】
- 每條發現附 檔案路徑:行號 + 該行內容
- 明確說「共 N 條」；0 條也要明說「確認為 0」
- 對每條標注：活文件（會被讀來執行）還是歷史紀錄（不用改）

【回報格式】條列，每條一行，≤400 字。不要貼大段原文，不要給修改建議（只盤點）。
```

## T2 實作（subagent_type: general-purpose；model: sonnet；機械套用降 haiku）

```
專案根目錄：/Users/kavi/Developer/Claude/Projects/ai-investment-committee

【目標】【改什麼，例：在 poller.py 的 stage1_triage 加一個 source_weight 參數】。
【動機】【為什麼，含取捨方向，例：社群源噪音高，要能單獨調降；寧可保守不動現有 feed 權重】。

先讀：【必讀檔案清單，含行號範圍，例：scripts/break_news/poller.py:80-150、config 範例】
遵循：與周圍程式碼同風格；不新增依賴；不動【明確列出禁區，例：weights.yaml、history.json】。

【驗收條件】（全部要有實際輸出佐證，不接受「應該會過」）
- 【測試命令，查 docs/agent-ops/OPS_COMMANDS.md §7】rc=0，貼出末 5 行輸出
- 【行為驗證，例：跑 poller.py --once，新參數生效的證據】
- 沒動到的測試沒變紅

【回報格式】≤200 字：改了哪些檔（路徑:行號區間）+ 每條驗收的證據。diff 不用貼，我會自己看。
若兩次嘗試後驗收仍不過：停手，回報兩次的失敗軌跡（做了什麼、錯在哪條驗收、報錯原文），不要硬繞。
```

## T3 重構／批次改檔（subagent_type: general-purpose；model: haiku——前提：pattern 已解出）

```
專案根目錄：/Users/kavi/Developer/Claude/Projects/ai-investment-committee

【目標】把以下 pattern 套用到指定的 N 個位置。這是機械任務，不要自由發揮、不要「順手改進」其他地方。

Pattern（精確 before/after）：
BEFORE:【原文範例】
AFTER: 【改後範例】

位置清單（共【N】處）：
【檔案:行號 一行一個——由派工者先用 T1 盤點出來，不要讓本 agent 自己找】

【驗收條件】
- 改動處數 = 【N】（用 grep 新 pattern 計數證明）
- grep 舊 pattern 結果 = 0 條（貼命令與輸出）
- 位置清單以外的檔案 0 改動

【回報格式】三行：改了 N 處｜grep 舊 pattern = 0 的輸出｜有無異常（某處長得跟 pattern 不符 → 跳過並列出，不要硬改）。
```

## T4 研究（subagent_type: general-purpose；model: sonnet；結論影響重大決策時升級或加第二意見）

```
專案根目錄：/Users/kavi/Developer/Claude/Projects/ai-investment-committee

【研究問題】【一句話，例：FMP legacy econ-calendar 403 之後，免費替代資料源有哪些、遷移成本多大】。
【動機／決策脈絡】研究結果將用來決定【什麼決策】，所以請側重【判斷維度，例：免費額度、欄位覆蓋、維護風險】。

方法要求：
- 【來源要求，例：WebSearch ≥3 個獨立來源；或：讀 skills/economic-calendar-fetcher 現有實作先確認欄位需求】
- 每個關鍵事實標來源（URL 或 檔案:行號）；查不到的標「未查到」，禁止推測補全
- 相互矛盾的來源要並列，不要自行擇一隱藏另一個

【驗收條件】
- 結論可直接回答研究問題（不是資料堆砌）
- 每個候選方案有【比較維度】的具體值或「未知」
- 有明確建議 + 一句話理由 + 最大風險

【回報格式】全文落檔到【docs/ 或 scratch/ 路徑】，對話只回 ≤10 行：建議、關鍵理由、最大不確定性、檔案路徑。
```

## T5 審查／驗收（subagent_type: general-purpose；fresh context 是重點，model 同級或低一級即可）

```
專案根目錄：/Users/kavi/Developer/Claude/Projects/ai-investment-committee

你是驗收者，沒有參與產出過程——這是刻意的，請只根據檔案現況判斷，不要腦補作者意圖。

【驗收對象】【檔案路徑清單 / diff 範圍】
【它宣稱做到的事】【逐條列出原始驗收條件】

逐條檢查：
1. 每條驗收條件：PASS / FAIL + 證據（檔案:行號、rc 輸出、grep 計數）
2. 【對文件】標出「較弱模型會誤讀」的句子：模糊指代、沒有判準的形容詞、互相矛盾的規則、指向不存在路徑的引用
3. 【對程式碼】實跑【測試命令】，貼 rc 與末 5 行
4. 找「宣稱做了但檔案裡沒有」的項目——這是驗收的頭號目標

【回報格式】
- 第一行：VERDICT: PASS / FAIL(N 條不過)
- 之後每條一行：條目｜PASS/FAIL｜證據
- 最後：弱模型誤讀風險清單（0 條也要明說）
禁止：自己動手修（只報告）；用「大致沒問題」帶過任何一條。
```

---

## 高風險判斷加開：2+1 評審制（配 MODEL_DISPATCH.md §6）

1. 同一題開 2 個獨立 subagent（prompt 相同，禁止互相看見；平行送出）。
2. 第 3 個 agent 只做評審，prompt 固定三問：兩份答案哪裡矛盾？各自證據哪個更硬？選哪份、需補什麼？
3. 評審禁止自己重做一份答案。
4. 更高獨立性：其中一份改用外部 CLI（`codex exec` / `agy`），先查 `model_router.py --status` 預算。

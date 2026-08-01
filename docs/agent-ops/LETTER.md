# 給未來 session 的信（2026-07-03）

寫這封信的 session 做了 `docs/agent-ops/` 全套治理文件與 CLAUDE.md 瘦身（背景見 `DIAGNOSIS.md`）。以下是使用者沒問、但我認為對這個環境最重要的三件事，以及這套制度會怎麼壞掉。

## 三件沒被問到但最重要的事

### 1. 這個系統最脆的不是模型智力，是資料源的靜默劣化

`economic-calendar-fetcher` 的 FMP legacy endpoint 已經 403，sector Phase 3 因此 **silent SOFT fail**——分析照跑、報告照出，只是少了一塊沒人喊。弱模型比強模型更不會「覺得怪」。模型可以降級，但**資料斷供必須大聲**。✅ **已於 v4.65.0 落地**：`scripts/daily_health.py`（17 個資料源的 artifact 新鮮度檢查，auto/manual 分級），`daily_update.sh` 收尾自動印表。之後新增資料源時記得補它的 SOURCES 清單；economic-calendar 修好後健檢會自動轉綠。

### 2. 剩餘的強模型依賴有便宜的工程解，優先做掉

DIAGNOSIS §三已定位三處：(a) ✅ 決策數字 LLM 手抄→已於 v4.66.0 改 script 注入（`inject_report_facts.py` + protocol Step 4.5；定位修正見 DIAGNOSIS §三.1）；(b) llm_review 一次吞 300KB 索引→先 script 切段統計再給模型摘要層；(c) Arbiter/Red Team→已有 2+1 評審制規則（MODEL_DISPATCH §6），但 protocol 檔案本文還沒接線，需要把「最強檔不可用時走 2+1」寫進 `sector/phase_4-5.md` 與 `investment_protocol_v5_0.md` 的模型分層段。做完 (b)(c)，這個 repo 對「只有 Sonnet」的世界基本免疫。

### 3. 跨家族 CLI 是被低估的品質資產

`codex exec` 和 `agy` 不只是 Break News 的辯手——它們是**免費的獨立第二意見**，且 model_router 已有預算治理。同家族模型（Claude 驗 Claude）有相關性偏誤：會犯同樣的錯、被同樣的表述說服。高風險判斷（投資 verdict、大重構方案）的驗收，一票給跨家族比兩票給同家族更值錢。用法已寫在 DELEGATION_TEMPLATES 尾段。注意 gemini 側 `llm_drivers.py:34` 硬編碼了 `gemini-2.5-flash-lite`，模型世代更迭時這行要跟著檢查。

## 這套制度最可能的退化方式（按可能性排序）與預防

1. **CLAUDE.md 長回去**。每加一個功能順手塞一行版號敘述，兩個月後又是 178 行 changelog。預防：MAINTENANCE §1 已列為「永遠不准」；§5 體檢有 120 行紅線——體檢時第一個查這個。
2. **驗證變成儀式**。agent 說「測試通過」沒貼 rc、驗收者變橡皮圖章（全 PASS 零發現）。預防：JUDGMENT §2 規定「沒有輸出=沒完成」；T5 模板的頭號目標是找「宣稱做了但不存在」的項目——**連續三次驗收全 PASS 零發現，就該懷疑驗收本身**，換一個更兇的驗收 prompt。
3. **模板被跳過**。「這個很簡單就不用三件套了」→ 散文派工回歸 → 主對話再度塞爆。預防：三件套最短可以只有五行，成本藉口不成立；發現自己在寫散文派工，回去抄 T1-T5。
4. **LESSONS.md 變垃圾場**。只寫不整併，150 行門檻形同虛設。預防：MAINTENANCE §4 的「已回寫規則？」欄位是關鍵——教訓的終點是規則檔，不是 LESSONS 本身。
5. **雙入口再脫鉤**。AGENTS.md（Codex）或父層 CLAUDE.md 又被人手動加規則。預防：兩檔開頭都已寫明「單一真相在專案 CLAUDE.md」；體檢時 diff 一下。

## 交接：本 session 留下的未完成項

| 項 | 說明 | 建議 |
|---|---|---|
| `CLAUDE拷貝.md` 刪除 | 冗餘舊副本，備份已在 `docs/agent-ops/backups/` | 問使用者一句即可刪 |
| ~~巨檔歸檔~~ | ✅ 已完成（2026-07-03）：SESSION_NOTES 保留最近 10 個區塊，其餘 236 個在 `archive/session_notes_archive.md`；CHANGELOG 未達門檻暫不動 | 之後照 MAINTENANCE §3 每次收尾搬第 11 個 |
| ~~§11 script 注入~~ | ✅ 已完成（v4.66.0），且定位修正：真正的手抄風險在 Phase 5 Step 4 Formatter（非 ic-memo §11）。`inject_report_facts.py` + protocol Step 4.5，6 個決策關鍵區塊佔位符注入，33-assert golden fixture | 下次跑 `分析 [TICKER]` 時實戰驗證一輪 |
| ~~daily health 摘要~~ | ✅ 已完成（v4.65.0）：`scripts/daily_health.py`（17 源 artifact 新鮮度，auto/manual 分級），daily_update.sh 收尾自動印表 | 之後新增資料源時記得補 SOURCES 清單 |
| ~~2+1 評審制接線進 protocol 本文~~ | ✅ 已完成（v4.67.0，經使用者提案核可）：Red Team（investment）+ Arbiter（sector）降級補償入 protocol 本文，觸發判準=「Agent tool model 清單無高於 sonnet 檔位」，schema 零改動 | **首次在降級世界跑 protocol 時**，人工盯 referee 輸出是否守三問制（矛盾/證據/選優）而非自己重寫——這是無法預先測試的部分 |

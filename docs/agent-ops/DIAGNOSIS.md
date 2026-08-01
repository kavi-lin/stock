# Harness 診斷報告（2026-07-03）

> 本檔是 `docs/agent-ops/` 全套治理文件的依據。掃描範圍：兩份 CLAUDE.md、根目錄與 docs/ 全部 .md、24 個 skills、三大 protocol、dashboard_server.py 模型調度、model_router。
> 讀者：未來的 Claude session（任何等級模型）與維護者本人。

---

## 一、最漏 token 前三名

### 1. 每個 session 固定載入「兩份」CLAUDE.md，其中一份還是過期的（~35KB/session）

**證據**：
- 父層 `/Users/kavi/Documents/CLAUDE.md`（14KB，141 行）在目錄鏈上，任何在 `Documents/` 底下開的 session 都會自動載入。
- 專案 `CLAUDE.md`（21KB，178 行）在專案內開 session 時也載入 → 兩份幾乎相同的內容重複載入。
- 父層版本停在 V4.13 時代，缺 `回測`、quant-backtest 等新條目 → 不只浪費，還會給模型**互相矛盾的舊指令**。
- `CLAUDE拷貝.md`（根目錄，6/12 快照）是第三份冗餘副本，diff 父層僅 2 行。

**修法**（本次已執行）：
- 父層 CLAUDE.md 改成 ≤10 行的純指標檔，只指向專案 CLAUDE.md。
- 專案 CLAUDE.md 重寫為 ≤100 行精簡路由（見下一條）。
- `CLAUDE拷貝.md` 建議刪除（本次不代刪，備份已在 `docs/agent-ops/backups/`）。

### 2. CLAUDE.md 的 Ops Shortcuts 區塊：68 行指令清單，其中 ~30 行是 golden-fixture 測試指令

**證據**：`docs/agent-ops/backups/CLAUDE.md.bak-20260703:87-156`（重寫前的原檔）。`test_forward_expectations_*.py` 一族就佔 20+ 行，每個 session 載入，但只有「改了對應 engine 之後」才需要。protocol trigger 表每格還內嵌 V 版號歷史敘述（V2.14.0、V3.25.0…），對執行毫無作用——CLAUDE.md 被當成 changelog 用了。

**修法**（本次已執行）：
- 完整指令清單抽到 `docs/agent-ops/OPS_COMMANDS.md`，CLAUDE.md 只留 daily/weekly 兩條常用 + 一行指標。
- trigger 表刪掉所有版號敘述，只留「指令 → 讀哪個檔 → 一句話紀律」。
- 版本演進史本來就在 CHANGELOG.md，不重複。

### 3. Append-only 巨檔被收尾規則指定「每次 session 必讀寫」

**證據**：
- `CHANGELOG.md` 9463 行 / 689KB；`SESSION_NOTES.md` 4754 行 / 420KB（~245 個 session 區塊）；`TODO.md` 779 行。
- 舊 Workflow Rule 說「格式參考既有 v1.42.x 條目」→ 弱模型會為了找格式範例整檔讀入（一次 10 萬+ token）。
- SESSION_NOTES 的「update Last Session Note」若不帶 offset/limit 直接 Read，同樣整檔進 context。

**修法**（規則已寫入 `MAINTENANCE.md` §3，讀法/limit/輪替門檻**以該檔為準**，此處不重複數字）：
- 三檔都是最新內容在上：一律帶 limit 讀頭部，禁止整檔 Read。
- CHANGELOG 條目格式模板直接內嵌在 MAINTENANCE.md §2，不再叫模型去舊檔找範例。
- 超過輪替門檻時把舊區塊搬 `archive/`。

---

## 二、最容易失焦前三名

### 1. 路由層與歷史層混在一起

CLAUDE.md 的 trigger 表每格塞滿版本演進註記，弱模型分不清哪句是「現在要遵守的指令」哪句是「歷史敘述」。**修法**：CLAUDE.md 只放「做什麼→讀哪檔」，任何帶 V 版號的句子一律不准進 CLAUDE.md（規則寫入 MAINTENANCE.md §可自行修改的邊界）。

### 2. 舊版 protocol 與索引 drift 並存，模型會讀錯真相來源

**證據**：
- `investment/investment_protocol_v4_8.md`（1278 行）與 `v5_0.md`（1524 行）並存。弱模型用 glob 搜 "investment_protocol" 會抓到兩份，讀錯一份就是整場分析走舊規則。
- `skills/MARKET_INDEX.md` 自稱 23 skills，磁碟上有 24 個——`quant-backtest` 沒入索引（違反它自己寫的維護規則）。

**修法**：v4_8 移入 `investment/archive/`（本次已執行）；MARKET_INDEX 補 quant-backtest（本次已執行）；MAINTENANCE.md 規定「新增 skill 的 DoD 包含更新索引」。

### 3. Protocol Triggers 表三處維護

同一張表存在於 `CLAUDE.md`、`AGENTS.md`（Codex 用）、`CLAUDE拷貝.md`。改一處漏兩處。**修法**：CLAUDE.md 是唯一 source of truth；AGENTS.md 只留「表在 CLAUDE.md，以它為準」＋Codex 特有差異；拷貝檔建議刪除。

---

## 三、最容易出錯前三名（換弱模型後風險放大）

### 1. 決策數字靠 LLM 手抄進報告，validator 只驗格式不驗值

**證據（V4.66.0 覆查後修正定位）**：真正的暴露點是 Phase 5 Step 4 的 Sonnet MD Formatter——要把幾十個數字、kill conditions「直接照搬」、watch_conditions dict 全列手抄進主報告，而 Step 5 的 `validate_markdown_export.py` 只驗分數刻度格式（/3.0、/100），**值抄錯照樣過關**。（原診斷指的 ic-memo §11 其實已由 `compose.py` deterministic 渲染＋SHA256 gate 保護，風險本來就低。）

**修法（✅ V4.66.0 已實作）**：`investment/scripts/inject_report_facts.py` — Formatter 對 6 個決策關鍵區塊只寫 `<!--INJECT:*-->` 佔位符，Step 4.5 由 script 從 history.json verbatim 注入（idempotent、N/A-safe）；golden-fixture `test_inject_report_facts.py` 33 asserts。LLM 永遠不碰需要 byte-level 保真的內容——**verbatim 複製就是一種算術**。

### 2. 版本 bump 三處同步靠模型記憶

**證據**：`VERSION` + `Dashboard/utils.js` + `CHANGELOG.md` 三處手動同步，「任一 desync 都不算完成」。弱模型最常漏 utils.js。**修法**：MAINTENANCE.md 提供一條驗證命令（grep 三處比對），收尾 checklist 規定「跑過這條命令且輸出一致才算完成」。判準從「記得改三處」變成「命令輸出三個相同版號」。

### 3. 高判斷力節點（Arbiter / Red Team / llm_review）沒有降級後的品質護欄

**證據**：
- `sector/phase_4-5.md:30` — lane 降 Sonnet 但 Phase 4c Arbiter 保留 Opus；`dashboard_server.py:147-158` — invest/llm_review/sector/playbook 走 opus。這個分層是對的，但**如果未來 opus 檔位由更弱的模型頂上**，Arbiter 綜合、Red Team 對抗推理、300KB 索引根因分析這三類任務沒有任何補償機制。
- 各 protocol 內建 validator 只驗 schema（結構），不驗判斷品質。

**修法**（已寫入 `MODEL_DISPATCH.md` §升降級 與 `JUDGMENT.md`）：
- 判斷類任務的補償不是「換更大模型」而是「多樣本＋評審」：Arbiter 決策改跑 2 個獨立 subagent 各出一份裁決 → 第 3 個 fresh-context agent 只做「選優＋指出分歧」。成本 3 個 call，換回穩定性。
- Red Team 給 kill-condition 檢核清單（見 JUDGMENT.md §品質底線），把自由發揮壓成半結構化任務。
- llm_review 的 300KB 索引先用 script 切段/統計預處理，再給模型看摘要層。

---

## 四、既有優點（不要在優化時破壞）

1. **算術全面 script 化**：`compute_price_framework.py`、`forward_expectations*.py`、triage 打分等全是 0-LLM。多處明令「禁止手算」。這是弱模型友善的最大既有資產。
2. **模型引用全走 alias**：專案程式碼幾乎沒有硬編碼 full model ID（唯一例外 `llm_drivers.py:34` 的 gemini-2.5-flash-lite）。換模型世代只需改 `PROTOCOL_MODEL` map 和 protocol 內的 alias。
3. **Skills 已模型無關**：24 個 SKILL.md 零「需要高階模型」假設，market-top-detector 等反而刻意支援 Codex/cron 降級路徑。
4. **探索層/決策層隔離紀律**（Break News、Nexus、戰術層、回測不入 investment_protocol 決策）——這是防止弱模型污染決策的結構性護欄，必須保留。
5. **Validator gates rc=0 制度**：schema 驗證已是 fresh-context、deterministic。

## 五、修復狀態總表

| # | 問題 | 狀態 |
|---|---|---|
| 1 | 父層 CLAUDE.md 過期雙載 | ✅ 本次改為指標檔 |
| 2 | 專案 CLAUDE.md 膨脹 | ✅ 本次重寫（備份在 backups/） |
| 3 | Ops Shortcuts 抽離 | ✅ → `OPS_COMMANDS.md` |
| 4 | v4_8 舊 protocol 並存 | ✅ 本次移入 `investment/archive/` |
| 5 | MARKET_INDEX 缺 quant-backtest | ✅ 本次補上 |
| 6 | CLAUDE拷貝.md 冗餘 | ⚠️ 建議刪除，留給使用者決定 |
| 7 | 巨檔輪替 | ✅ SESSION_NOTES 已輪替（保留最近 10 個區塊，236 個搬 `archive/session_notes_archive.md`）；CHANGELOG 未達門檻暫不動 |
| 8 | 決策數字 LLM 手抄 → script 注入 | ✅ V4.66.0：`inject_report_facts.py` + protocol Step 4.5 |
| 9 | Arbiter/RedTeam 降級護欄 | ✅ 規則寫入 MODEL_DISPATCH.md + JUDGMENT.md |
| 10 | 版本 bump 驗證命令 | ✅ 寫入 MAINTENANCE.md |

# 踩坑教訓（格式見 MAINTENANCE.md §4；>150 行時精簡）

## 2026-08-02 ｜修引擎不重跑 snapshot，archive 最新一筆仍是壞資料
- 情境：review v4.78.0 forward-expectations 修正（5274299 cutoff + 77642f4 scope gate）
- 坑：`MU_20260801T230255Z.json` 生成於兩個 commit 之間（07:02，scope fix 07:04 才進），base_rate_lane 帶著被自動晉升的 -9% cohort median 與錯誤 note，成為 archive 最新 MU snapshot——任何讀 latest snapshot 的報表都會拿到 fix 前的數值。程式碼與測試全對，壞的是資料層
- 修法：引擎行為修正的收尾 checklist 加一步：受影響 ticker 重跑一次 snapshot（ledger 不可變，用新檔蓋 latest 而非刪舊檔）；review 引擎變更時，除了 diff 與測試，一定抽 archive 最新 snapshot 核對關鍵欄位是否已是 post-fix 行為
- 已回寫規則？：否（先記 LESSONS；若再犯考慮寫進 MAINTENANCE §2 收尾 checklist）

## 2026-08-02 ｜估值引擎驗收只驗 happy path，等於沒驗
- 情境：4.76.0 交付 MU structural-shift DCF + range-only peer fallback，驗收是「MU 跑出 $762.13、測試 rc=0、validator rc=0」，看起來很完整
- 坑：後續 review 找到 12 項問題，**全部**在 degraded / fallback 分支，happy path 一項都沒錯——因為 MU 剛好是「3 季已公布 + 有 next-quarter estimate + estimates 有 ebitAvg」的最順情境。實際踩到的：2 季 ticker 會拿已公布季度獲利除全年營收估計（`dcf.py` start EBIT margin）；缺年度估計時整條成長路徑直接套成長上限表 45/30/20/12/8（把「證據上界」當「預設值」）；confirmed shift 建不起來時靜默退回 legacy 而 legacy 對該股會算出負 terminal FCFF；資料缺失的 ticker 在非 `--json-only` 模式直接 TypeError 而不是 degraded
- 修法：引擎類交付的 DoD 加一條——**每個 early-return / fallback / except 分支都要有一條 regression test**，且測試 fixture 不能只有一個「資料齊全」版本。寫 fallback 時問一句「這個預設值是保守還是最寬鬆？」缺資料一律往保守 + 出聲（寫 reason 進 payload + warnings），不准往上界靠
- 已回寫規則？：是（`skills/valuation-modeler/SKILL.md` 新增「缺資料時的紀律（degraded path）」段；本條記通則，其他引擎同樣適用）

## 2026-07-03 ｜開處方前先確認「這件事實際是誰在做」
- 情境：實作「§11 verbatim 改 script 注入」backlog
- 坑：診斷時把 verbatim 風險定位在 ic-memo §11，動工前覆查才發現 ic-memo 的 §11 早就是 `compose.py` deterministic 渲染；真正由 LLM 手抄數字的是 protocol Step 4 的 Sonnet MD Formatter，且其 validator 只驗刻度格式不驗值
- 修法：任何「叫 X 改為 script 做」的處方，動工第一步先讀原始碼確認 X 目前的執行者到底是 LLM 還是 script（grep 該欄位在 protocol/scripts 兩邊的出現點），再定改動對象
- 已回寫規則？：是（DIAGNOSIS §三.1 已改為正確定位；本條記過程）

## 2026-07-03 ｜兩層 CLAUDE.md 會同時載入且會脫鉤
- 情境：治理文件總體檢
- 坑：父層 `/Users/kavi/Documents/CLAUDE.md` 是舊拷貝，與專案版一起被載入，內容停在 V4.13 → 每 session 浪費 ~14KB 且指令互相矛盾
- 修法：父層永遠只放指標；規則只寫專案 CLAUDE.md 一處
- 已回寫規則？：是（父層已改指標檔；MAINTENANCE.md §1「永遠不准」）

## 2026-07-03 ｜檔名帶版號的 protocol 換版時要清引用
- 情境：v4_8 歸檔
- 坑：16 個活文件（skills SKILL.md/README、sector/news README、docs/plan_short.md、兩個 .py docstring）仍指向 investment_protocol_v4_8，弱模型會照舊檔名去找；且第一輪 grep 漏了 plan_short.md 的 2 條（自以為「歷史文件」而排除，但它被 CLAUDE.md 指名為活文件）——排除清單要保守
- 修法：protocol 換版的 DoD 含 `grep -rn "舊檔名" --include="*.md" --include="*.py"` 清零（排除 archive/CHANGELOG/SESSION_NOTES/reports）
- 已回寫規則？：部分（本條即記錄；未來換 v5_1 時照此 grep）

## 2026-07-21 ｜治理檔裡的絕對路徑會悄悄漂移（Documents vs Developer）且不會報錯
- 情境：專案全面更名搬遷（`AI投資委員會` → `ai-investment-committee`，含實體資料夾）
- 坑：`docs/agent-ops/MAINTENANCE.md`、`DELEGATION_TEMPLATES.md`、`scripts/run_weekly_review.sh`、`config/office_claude/.claude.json` 等多處硬編路徑寫的是 `/Users/kavi/Documents/Claude/Projects/AI投資委員會`，但實際專案早就在 `/Users/kavi/Developer/Claude/Projects/...`——兩者長期並存、沒有任何 script 會因此報錯（cd 失敗只在真的執行到那條指令時才會發現），純文件型路徑（範本、註解）尤其容易漂移沒人發現
- 修法：全面更名這類 session 動工前，除了 grep 專案名稱字串，另外 grep 完整絕對路徑（含所有已知歷史路徑變體，不只目前 cwd 這個）——本次順手修正 Documents 變體；`config/office_claude/**`、`cache/projects.json` 是巢狀 Claude 執行狀態（office 模擬功能用）指向另一條路徑，判斷為 out-of-scope 不動，已告知使用者
- 已回寫規則？：否（本條屬一次性事件記錄；MAINTENANCE.md §1 的「路徑不存在可自行修正」規則已足夠涵蓋，不需新增規則）

## 2026-07-17 ｜治理檔改前備份是動手前一步，不是事後補
- 情境：新增 grok CLI 進 LLM 治理鏈（`config/llm_config.json` 屬 §1 使用者手動校準區）
- 坑：使用者已 OK 改動摘要表後直接下手 Edit `config/llm_config.json`，改完才想到 §1「永遠不准做」的無備份改治理檔規則，靠 `git show HEAD:` 補回原始內容才補上備份——若該檔當時不是 clean（已有未 commit 的異動），git show HEAD 補的會是錯的版本
- 修法：治理檔（`config/llm_config.json`、`weights.yaml`、`positions.json`…）的 Edit 前，先跑 `cp X docs/agent-ops/backups/X.bak-YYYYMMDD`，跟「先問使用者」同一步驟做，不要等改完
- 已回寫規則？：否（規則本身在 MAINTENANCE.md §1 已存在且夠清楚，這條純記過程疏漏）

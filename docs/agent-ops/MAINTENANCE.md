# 維護協議 — 如何安全地更新治理檔案與巨檔

> 讀者：未來任何等級的 session 模型。原則：規則改壞的代價由之後每個 session 承擔，所以「改治理檔」比「改程式」更需要保守。

## 1. 權限分級

### 可以自行改（不用問使用者）
- `docs/agent-ops/LESSONS.md` 追加教訓（照 §4 格式）
- `OPS_COMMANDS.md`：新增/修正指令條目（前提：指令實跑過一次）
- `skills/MARKET_INDEX.md`：新 skill 上線同步補列（這是義務不是選項）
- `SESSION_NOTES.md` / `TODO.md` / `CHANGELOG.md`：照 §3 讀寫規則的例行更新
- 修正治理檔中**確認錯誤的事實**（路徑不存在、指令名打錯）——修正前先驗證（ls / 實跑），並在 LESSONS.md 記一筆

### 動之前必須先問使用者
- `CLAUDE.md`（兩層任一）的任何規則增刪——路由條目跟著新功能加是例外，但規則段（Workflow Rules、全域紀律）必問
- `MODEL_DISPATCH.md` / `JUDGMENT.md` / `DELEGATION_TEMPLATES.md` / 本檔的**規則本身**（新增反模式例子可自行加；規則文字裡的純事實性錯誤——錯路徑、錯指令名——走上面「可自行改」的例外，驗證後修）
- 刪除任何使用者建立的檔案；移動 protocol 檔案
- `weights.yaml`、`config/llm_config.json`、`positions.json`、mega-cap 名單（使用者手動校準區）
- 新增 `.claude/agents/*.md` 自訂 agent 定義

### 永遠不准做
- 把版號歷史敘述寫回 CLAUDE.md（歷史只進 CHANGELOG）
- 在多處複製同一張表（trigger 表只在 CLAUDE.md；指令清單只在 OPS_COMMANDS.md）
- 無備份改治理檔（改前 `cp X docs/agent-ops/backups/X.bak-YYYYMMDD`）

## 2. 版本 bump（dev session 收尾）

三處一起改：`VERSION`（純數字）→ `Dashboard/utils.js` 的 `const VERSION = 'Vx.y.z'`（約第 11 行）→ `CHANGELOG.md` 新條目。大改 bump minor、小改 bump patch。

**改完必跑驗證（輸出含 SYNC OK 才算完成）**：
```bash
cd "/Users/kavi/Developer/Claude/Projects/ai-investment-committee" && v=$(cat VERSION) && \
grep -q "'V$v'" Dashboard/utils.js && grep -q "^## \[$v\]" CHANGELOG.md && \
echo "SYNC OK: $v" || echo "DESYNC — 三處版本不一致，回去補"
```

**CHANGELOG 條目模板**（直接抄，不要去舊條目找格式；插入位置見 §3）：
```markdown
## [x.y.z] — YYYY-MM-DD — 一句話標題

### Added / Changed / Fixed（三選用到的）
- 條列具體變更（動了哪些檔、行為差異）

### Why
- 一兩句動機
```

## 2b. 收尾殘留掃描（必做，與版本 bump 同批）

**對本輪改動的關鍵字串／數值／規則名做一次全 repo grep，不得只走實施表清單。**

```bash
# 例：本輪刪了一個 enum 值、改了一個門檻、修了一張乘數表
grep -rn "EXTREMELY_FRAGILE\|×1\.1\|tail_risk < 40" --include=*.md --include=*.py . | grep -v archive
```

理由：實施表是「盤點的人 → 列表的人 → 執行的人」，而這三個角色通常是同一個 session，
**三道關卡實際上只有一道**。殘留掃描有效正是因為它問的問題不同——不是「我要改哪些檔」
而是「這個字串還在不在」，它不經過那份清單。V4.111.7／V4.112.0 兩輪各靠它抓到實施表
遺漏的 5 處行號與 4 處規則鏡像。

命中後照 `investment/README.md` 的處理慣例：**現行規則改掉，版本沿革／歷史報告保留原文
加註**，不要竄改歷史。

## 3. 巨檔讀寫規則（防整檔 Read 塞爆 context）

三個檔都是**最新內容在上**（header 之後）。**一律禁止無 limit 的整檔 Read。**

| 檔 | 讀法 | 寫法 |
|---|---|---|
| `CHANGELOG.md`（>9000 行） | `Read(limit=40)` 看最近 2-3 條即可 | 新條目插在 header 與「目前最新條目」之間：Edit 以現任最新的 `## [x.y.z]` 標題行為錨點，在其前插入 |
| `SESSION_NOTES.md`（常態 ~100-200 行） | `Read(limit=60)` 看 header + 最近 2 個 Session Note；查舊版本 → Grep 版號於 `archive/session_notes_v*.md`（批次檔以版號範圍命名） | 新 `## 🟢 Session Note (vx.y.z) — 標題` 區塊插在現任最新區塊之前；同時更新 header 的 `Last Updated`；尾部兩個常駐狀態區塊（Momentum Context、Bridge 資料流對照）不是 Session Note，永遠留在原檔 |
| `TODO.md`（~780 行） | `Read(limit=60)` + 需要找特定項時用 Grep | 勾銷用 Edit 精準替換該行；新項加在對應版本區塊 |

**輪替門檻**（超過就在收尾時順手做）：
- `SESSION_NOTES.md`：**批次制（2026-07-03 使用者定案 v2）** — 收尾新增 note 後跑 `python3 scripts/rotate_session_notes.py`：主檔 ≤20 個 no-op；>20 個自動把最舊 10 個切成 `archive/session_notes_v<最舊>_to_v<最新>.md`（批內新在上）。**不要手動搬**，一律走 script
- `CHANGELOG.md` > 12000 行 → 兩個 minor 版本以前的條目搬 `archive/changelog_pre_vX.md`，header 加指標
- `TODO.md`：已完成超過 30 天的項目搬 `archive/todo_done.md`

## 4. 教訓寫回 — `docs/agent-ops/LESSONS.md`

每次踩坑（規則誤讀、路徑失效、派工失敗模式、驗收漏洞）在 session 收尾寫一條。格式固定：

```markdown
## YYYY-MM-DD ｜一句話教訓標題
- 情境：當時在做什麼
- 坑：具體錯在哪（附 檔案:行號 或指令）
- 修法：下次怎麼做對（可執行的動作，不是「要小心」）
- 已回寫規則？：是（改了哪檔哪節）/ 否（為什麼）
```

**精簡門檻**：LESSONS.md > 150 行時，把重複主題合併、把已回寫進正式規則的條目刪掉（規則檔才是長期記憶，LESSONS 是中繼站）。合併動作可自行做，刪除前確認「已回寫」欄為是。

## 5. 治理檔自身的體檢（每 ~10 個 dev session 或發現異味時）

跑一個 fresh-context agent 用 `DELEGATION_TEMPLATES.md` T5 審查 `docs/agent-ops/` 全部檔案 + CLAUDE.md，重點三問：
1. 有沒有規則互相打架？
2. 引用的路徑/指令還存在嗎（`scripts/check_skills.py` 順便跑）？
3. CLAUDE.md 是否又長回去了（>120 行就該抽東西出來）？

---
name: weekly-tech-playbook
description: 每週產出三個各 $100k 的科技投資籃子與獨立 Codex Review，保留原文並提供風險附註、100% 替代配置、執行紀律及來源，輸出 Dashboard/playbook.json 與日期化科技 playbook 報告，並於下週比較原籃與 Codex 配置績效。使用於「投資方案」、「週選方案」、「科技選股」、「Codex review」、「投資方案檢討」或「方案檢討」。
---

# weekly-tech-playbook — 三籃子 $100k 科技投資方案

## 目的

把「從本週系統分析（指標線 + 新聞辯論 + 委員會 verdict）擬下週投資方案」固化成可重跑流程。
每次產出 **三個獨立籃子，每個假設投入 $100k**：

| 籃子 | 定位 | 配重 |
|---|---|---|
| 🛡️ 保險 (conservative) | megacap 質地 + 現金流 + 控估值,可較滿配 | 核心 $15k×3 / 標準 $10k×4 / 輕倉 $5k×3 |
| 🔥 激進 (aggressive) | 最夯題材高 beta 衝刺,分批/等回檔/嚴設停損 | 同上 |
| ⚖️ 混合 (hybrid) | 65% 保險 sleeve + 35% 激進 sleeve | 依 sleeve 加總 = $100k |

每次同時產出一段 **Codex Review**：原三籃全文不可被覆寫；review 必須逐點引用原報告、提出獨立附註，並給出含現金且合計 100% 的替代配置。

**紀律**：本 skill 為**前瞻探索層**，**不**進入 investment_protocol 決策。委員會單股 verdict 仍以各自 `reports/<DATE>_<TICKER>.md` 為準；Codex Review 不得只因委員會 verdict 接受或排除標的。

## 流程（每週重跑）

### Step 1 — 組資料包（0 LLM）
```bash
python3 skills/weekly-tech-playbook/scripts/build_pack.py            # 即時抓 yfinance 報價
python3 skills/weekly-tech-playbook/scripts/build_pack.py --no-fetch # 跳過報價（離線/快測）
```
輸出兩份資料：

- `data/blind_pack_<DATE>.json`：regime、熱題、候選宇宙行情與動能，**不含**委員會 verdict。
- `data/pack_<DATE>.json`：另含近 14 天委員會 verdict，供 blind pass 完成後 reconciliation。

### Step 2 — LLM 選股（Claude turn）
Claude 讀 pack，依「最夯題材 + 委員會 verdict + 估值/動能紀律」選 **每籃 10 檔**，寫
`skills/weekly-tech-playbook/data/selections_<DATE>.json`（schema 見下）。
- 保險籃偏 megacap 質地與相對估值；近月回檔的優質股視為再進場價值。
- 激進籃押熱題，但近月已大漲 / 委員會標 `extreme_overvalued` / `decision_cap` 者降級為輕倉並標「等回檔」。
- 混合籃 = 保險 sleeve（$65k）+ 激進 sleeve（$35k），每檔標 `sleeve`。

### Step 2.5 — Codex Review（建議；對生成為**可選**）

獨立第二意見。**`render.py` 不強制要求** `codex_review`——缺它仍正常生成三籃（rc=0），weekly 生成器可獨立重跑；但**強烈建議**每週附上以制衡單一視角。若提供，`render.py` 會驗證其結構（缺漏才報 fatal）。
使用不可倒序的兩階段流程，將結果寫入同一份 selections 的 `codex_review`：

**A. Committee-blind pass**

1. 只讀 `blind_pack_<DATE>.json`、原始財報／公司 IR、監管機關與官方統計；不得先讀 `pack_<DATE>.json`、selections 或個股委員會報告。
2. 寫 `data/codex_blind_<DATE>.json`，至少保存候選排序、排除理由、初步配置、查證來源與時間。
3. 初步配置完成後才進入 B；不得回頭覆寫 blind artifact。

**B. Reconciliation**

1. 再讀完整 pack、原三籃與委員會 verdict，逐項說明一致與分歧。
2. 設 `review_mode = committee_blind_then_reconcile`、`committee_dependency` 與 `dependency_note`，並引用 `blind_artifact`。

共同要求：保留原始籃子；至少比較總曝險、集中度／相關性、高動能追價、爭議標的與風控；對時效性事實使用第一方來源；替代配置含現金且合計 100%；明定分批與風險上限。被委員會否決的股票可重新納入，但必須引用 blind pass 的獨立論證。

### Step 3 — 配重 + 渲染 + 驗證（0 LLM）
```bash
python3 skills/weekly-tech-playbook/scripts/render.py --selections skills/weekly-tech-playbook/data/selections_<DATE>.json
python3 skills/weekly-tech-playbook/scripts/render.py --selections skills/weekly-tech-playbook/data/selections_<DATE>.json --validate-only
```
算每檔股數（`round(weight_usd/price)`）+ 實際成本，驗證每籃加總 = $100k，輸出
`Dashboard/playbook.json`（餵 Dashboard）+ `reports/<DATE>_TECH_PLAYBOOK.md`（人讀 + 檢討 scaffold）。
renderer 同時驗證 Codex Review 必填欄位、至少 3 組原文／附註，以及替代配置合計 100%。
**rc**：0 pass / 1 fatal（籃 ≠ $100k、缺價、0 檔、Codex Review 缺漏或配重錯誤）/ 2 degraded-usable（rounding drift > 2%、缺委員會資料或 review 來源不足）。

### Step 4 — Dashboard 呈現
`/playbook.html`（sidebar「投資方案」）讀 `playbook.json`，先以雙欄顯示「原報告 / Codex Review 附註」，再顯示 Codex 替代配置、執行紀律與來源；原三籃仍可切換。靜態檔由 dashboard_server 自動服務，無需改 server。

### Step 5 — 下週檢討機制（觸發詞「投資方案檢討」）

兩段式：先跑 `review.py` 算硬數據（0 LLM），再由 Claude turn 讀數據填質性判讀。

```bash
# 1) deterministic 計算：抓 review 日收盤,算每檔報酬 / 每籃 vs SPY / 命中率 / kill 觸發
python3 skills/weekly-tech-playbook/scripts/review.py --playbook skills/weekly-tech-playbook/data/playbook_<ENTRY_DATE>.json --asof <REVIEW_DATE>
#   亦可用 --date <ENTRY_DATE> 自動解析 snapshot；--asof 預設今天
```
- 進場錨點 = `render.py` 當週寫的 dated snapshot `data/playbook_<ENTRY_DATE>.json`（immutable，故 `Dashboard/playbook.json` 被下週覆寫後仍可回放）。
- kill 觸發 = 從 kill 文字（「跌破 $195」等）擷取門檻價,現價跌破則標 `🔴`。
- 同時計算 Codex 替代配置；現金／短債 sleeve 報酬設為 0%，股票使用原報告 price 作進場錨點。
- 輸出 `reports/<REVIEW_DATE>_TECH_PLAYBOOK_REVIEW.md`（含原三籃、Codex 替代配置與空白「🧠 LLM 檢討」段）+ `Dashboard/playbook_review.json`（`/playbook.html` 頂部「上週方案檢討」橫幅,只在 entry≠review 日顯示）。

```
2) LLM 檢討（Claude turn）：讀上面 MD 的硬數據,填「🧠 LLM 檢討」段 —
   原三籃與 Codex 替代配置哪個贏+為什麼 / 觸發 kill 的標的認賠或續抱 / 最大貢獻+拖累 /
   催化兌現檢查（Core PCE 等）/ 下週調整建議。可據此改下週 selections。
```
**紀律**：檢討為前瞻探索層,**不**回寫 investment_protocol；調整僅作用於下週 selections。`review.py` 永不改 config、永不自動覆寫選股（比照 short-term `weekly_review.py`）。

## selections JSON schema

```jsonc
{
  "as_of": "YYYY-MM-DD",
  "week_label": "...",
  "capital_per_basket": 100000,
  "tier_weights": { "core": 15000, "standard": 10000, "light": 5000 },
  "discipline_note": "...",
  "macro": { "regime": "...", "exposure_ceiling": "...", "breadth": "...",
             "market_top": "...", "sentiment": "...", "real_rate_10y": "...",
             "key_events": ["..."], "playbook_logic": "..." },
  "codex_review": {
    "label": "Codex Review",
    "reviewed_on": "YYYY-MM-DD",
    "review_mode": "committee_blind_then_reconcile",
    "committee_dependency": "low|medium|high",
    "dependency_note": "哪些結論獨立、哪些承接委員會資料",
    "blind_artifact": "data/codex_blind_<DATE>.json",
    "verdict": "...",
    "comparison_notes": [
      { "title": "總曝險", "original": "原報告內容", "note": "Codex 獨立附註" }
    ],
    "recommended_allocation": [
      { "ticker": "現金／短債", "weight_pct": 25, "role": "事件風險" },
      { "ticker": "NVDA", "weight_pct": 10, "role": "AI 核心" }
    ],
    "execution": ["..."],
    "sources": [ { "label": "官方來源", "url": "https://..." } ]
  },
  "baskets": {
    "conservative": { "label_zh": "保險", "label_en": "Conservative", "thesis": "...",
      "picks": [ { "ticker": "NVDA", "tier": "core|standard|light", "weight_usd": 15000,
                   "theme": "...", "price": 0.0, "mom_5d": 0.0, "mom_1mo": 0.0,
                   "committee": "...", "reason": "...", "data": "...", "kill": "...",
                   "sleeve": "保險|激進" /* hybrid only */ } ] },
    "aggressive": { ... }, "hybrid": { ... }
  }
}
```
**不變量**：每籃 `sum(weight_usd) == capital_per_basket`；每籃 10 檔；每檔需 `price`；`codex_review` 必填；`sum(recommended_allocation.weight_pct) == 100`；review 只能附註，不能修改 `baskets`。沒有 blind artifact 的舊 review 必須標為 committee-informed，不得宣稱獨立。

## 檔案

| 路徑 | 角色 |
|---|---|
| `scripts/build_pack.py` | Step 1 資料層（0 LLM）→ `data/pack_<DATE>.json` |
| `scripts/render.py` | Step 3 配重+渲染+驗證（0 LLM）→ `Dashboard/playbook.json` + `data/playbook_<DATE>.json`（immutable snapshot）+ `reports/<DATE>_TECH_PLAYBOOK.md` |
| `scripts/review.py` | Step 5 檢討計算（0 LLM）→ `reports/<REVIEW_DATE>_TECH_PLAYBOOK_REVIEW.md` + `Dashboard/playbook_review.json` |
| `data/selections_<DATE>.json` | Step 2 LLM 選股輸出（人/LLM 編輯） |
| `Dashboard/playbook.html` + `Dashboard/page-playbook.js` | Step 4 呈現 |

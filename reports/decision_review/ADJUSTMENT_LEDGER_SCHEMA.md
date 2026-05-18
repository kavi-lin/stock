# Adjustment Ledger Schema

> 給 LLM weekly REVIEW pass + 人類維護者讀。Ledger 每筆 entry 用 markdown level-2 heading
> `## Rec <N> — <title>`，body 是 bullet list（`- **field**: value`）。
> Hot-path：`scripts/build_event_index.py:_load_adjustment_ledger` 會 parse 出 active entries
> 注入 `event_index.adjustment_ledger_active`。Schema 變更要同步該 parser。

## 必填欄位

| field | type | example | 用途 |
|---|---|---|---|
| `applied_date` | YYYY-MM-DD | `2026-05-09` | 評估窗起點；REVIEW 找出 `applied_date <= 評估週` 的 entries |
| `applied_version` | semver | `2.17.16` | 對應 git commit / VERSION 檔當時值 |
| `rec_source` | string | `REVIEW_2026-05-09 Rec 7` | 反向追蹤到原始 LLM review |
| `hypothesis` | 一句話 | `deep-dive repeat-miss 集中在熱門 sub-industry...` | 證偽用 |
| `target_metric` | bullet list | `tuning_hooks.sub_industry_heat 非 null 比例 ≥ 80%` | LLM 用此指標下「moved / no_move / regressed」judgement |
| `files_changed` | path list | `scripts/_sector_heat.py` (NEW) | 出問題時 rollback path |
| `rollback_plan` | 一句話 | `git revert` 或具體步驟 | 緊急回退 |
| `status` | enum | `active` / `rolled-back` / `superseded` / `paused` | active 才會被 build_event_index 抓出 |
| `evaluation_history` | bullet list of weekly results | `2026-05-16: target metric 達 85%, hypothesis 證實` | 累積證據 |

## 狀態語義

- `active` — 目前生效中，每週 REVIEW 會評估
- `paused` — 暫停評估（資料不足 / blocker），但檔還在
- `rolled-back` — 已 revert，留 entry 作為「曾試過不 work」證據
- `superseded` — 被後續 Rec 取代（新 entry 用 `rec_source` 指回此 Rec id）

## REVIEW 評估流程（每週）

1. LLM REVIEW 開頭讀 `event_index_<DATE>.json:adjustment_ledger_active`
2. 對每筆 active entry：
   - 拉出 `target_metric` 的當前數值（從 `industry_rollup` / `decisions` / 外部）
   - 跟前次 `evaluation_history` 比，下 `improved / no_change / regressed` 判斷
   - 寫進 REVIEW 報告新增的「## Adjustment Evaluation」段
3. 人類 review 後手動 append 一筆 `evaluation_history` 到 `ADJUSTMENT_LEDGER.md`

## 反例（不要這樣寫）

- ❌ `target_metric: 系統表現變好` — 沒有量化指標
- ❌ `hypothesis: 改了應該會好` — 沒有可證偽的假設
- ❌ `applied_date: 上週四` — 用相對日期；總是寫絕對 YYYY-MM-DD

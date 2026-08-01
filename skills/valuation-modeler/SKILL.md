---
name: valuation-modeler
description: Build driver-based DCF valuation models and multi-metric comparable company (comps) tables for US stocks, with WACC/terminal-growth sensitivity grids and optional Excel workbook export. All numbers are script-computed (zero LLM hand-math). Feeds the investment protocol's dcf_self_built and comps_implied fair-value anchors (V4.69.0+). Use when user asks for 估值模型, DCF 模型, 同業比較, comps analysis, comparable company analysis, WACC sensitivity, or wants an auditable valuation model with adjustable assumptions for a specific ticker.
---

# Valuation Modeler

## Purpose

Ported from the gap analysis vs Anthropic's official "Claude for Financial
Services" skill suite (2026-07): the project consumed FMP's pre-computed DCF
numbers but could not build an **auditable, assumption-adjustable DCF model**,
and had only a single-metric peer anchor (`peer_pe_implied`) instead of a full
multi-metric comps table. This skill fills both gaps **as deterministic Python
engines** — the official skills are LLM prompt packs whose hand-math violates
this project's 數字全走 script 紀律.

**Two engines, one deliverable set**:
- `dcf.py` — driver-based 5-year FCFF DCF: normal case uses FMP historicals +
  analyst estimates; confirmed structural shifts use a current-FY quarterly
  roll-forward plus bounded through-cycle revenue/margin/reinvestment paths
  (each field carries provenance:
  `analyst` / `derived` / `override` / `default`), CAPM WACC (beta from FMP
  profile, risk-free from fred-macro cache DGS10, ERP 4.5% default), Gordon
  terminal value, 5×5 sensitivity grid (WACC ±1.0% × terminal growth ±0.5%).
- `comps.py` — comps table over shared exact-industry + business-model peer selector: P/E, EV/EBITDA,
  EV/Sales, PEG with peer Q1/median/Q3 (IQR-winsorized), implied per-share
  value per metric (EV math identical to `compute_price_framework.py`).
- `peer_cohorts.py` — range-only fallback when the provider peer list is sparse or
  broad. LLM/manual research may propose tickers in `config/peer_cohorts.json`,
  but Python fetches every multiple, requires ≥3 positive observations, and
  never promotes the cohort into the primary FV.

**Protocol integration (decision path — user-approved V4.69.0)**:
- `dcf.py <T> --json-only` → `.fair_value_per_share` = **`dcf_self_built`** anchor
- `comps.py <T> --json-only` → `.comps_implied_value` = **`comps_implied`** anchor
- comps anchor = median of EV/EBITDA + EV/Sales + PEG implied values only;
  **P/E deliberately excluded** — the protocol's existing `peer_pe_implied`
  anchor already covers it (anti double-count)
- Either model failing/ineligible → payload retains `model_eligibility.reason` and
  canonical valuation pack excludes it from live aggregation (no silent null / no hard dependency).
- Non-positive terminal FCFF is `model_ineligible`, not a zero/low DCF valuation.
- An eligible structural-shift DCF becomes `primary_fv`. Other methods remain
  visible as scenario points; an adjacent curated peer cohort may extend the
  explained range but receives zero primary-FV weight.

## Usage

```bash
export FMP_API_KEY=your_key_here

# DCF — report + JSON
python3 skills/valuation-modeler/scripts/dcf.py NVDA
python3 skills/valuation-modeler/scripts/dcf.py NVDA --json-only          # anchor mode
python3 skills/valuation-modeler/scripts/dcf.py MSFT --set wacc=0.09 --set terminal_growth=0.03
python3 skills/valuation-modeler/scripts/dcf.py AAPL --overrides my_assumptions.json --xlsx

# Comps — report + JSON
python3 skills/valuation-modeler/scripts/comps.py NVDA
python3 skills/valuation-modeler/scripts/comps.py NVDA --json-only --xlsx
```

Flags: `--json-only`（stdout JSON，不寫報告）、`--overrides F.json` / `--set k=v`
（僅 dcf；可覆寫鍵見 `dcf.OVERRIDABLE`）、`--projection-mode auto|legacy`（僅 dcf；
`legacy` 強制 constant-ratio，用於與 structural 模式對照）、`--xlsx`（另出 Excel
workbook）、`--output-dir`（預設 `reports/`）、`--no-cache`。

Exit codes: `0` 成功；`1` fair value 無法計算（degraded）或 override 鍵錯誤。
Degraded 時仍會產出報告，但檔頭標 `DEGRADED` + reason，不得當 anchor 用。

## Method

### DCF assumptions（自動推導 + 可覆寫）

| 假設 | 推導 | Clamp |
|---|---|---|
| revenue growth y1-2 | analyst revenue estimates；缺 → 歷史 CAGR × 0.7 阻尼（同 forecaster Step 1 係數） | analyst [-20%, +60%]；derived [-10%, +40%] |
| revenue growth y3-5 | 由 y2 線性 fade 至 terminal growth | — |
| ebitda_margin / da_pct / capex_pct | 3 年歷史均值（cashflow 行以會計年度 join income revenue） | — |
| nwc_pct | 3 年 ΔNWC/Δrevenue 均值（FMP 符號慣例：負 changeInWorkingCapital = 現金流出） | [0, 30%] |
| tax_rate | 3 年有效稅率 | [10%, 35%] |
| WACC | CAPM + 市值權重稅後債務成本 | [6%, 15%]；wacc − g ≥ 2%（違反時降 g 並記 warning） |
| terminal_growth | 預設 2.5% | — |

Confirmed structural-shift mode replaces the constant-ratio rows above with:

- current FY base = reported quarters + next-quarter estimate; forecast Year 1
  starts in the following fiscal year（避免把 current FY 重複折現）
- annual analyst revenue is evidence, not a command: growth caps decline
  45% → 30% → 20% → 12% → 8%
- EBIT, D&A and capex fade from latest operating state to analyst-normalized
  margins; terminal capex = D&A + `g / sales_to_capital`
- inconsistent provider EBITDA/FCF signs are ignored with explicit warnings;
  latest quarterly net cash and shares replace stale annual balance inputs
- WACC retains observed beta for audit but uses Blume mean reversion
  `2/3 × observed + 1/3 × 1.0`; an explicit `--set beta=` override is untouched

**缺資料時的紀律（degraded path，違反就是 bug）**：

- start EBIT margin 的分子分母必須同期：3 季 + 次季估計走 roll-forward
  （`quarterly_rollforward`）；其餘情況只用已公布季度
  （`reported_quarters_only`），不得拿已公布季度獲利除全年營收估計
- 成長上限表是「證據的上界」不是預設值：缺年度營收估計時改用 base growth
  假設（analyst / derived），再受 cap 約束，絕不直接套 45%
- confirmed shift 但無法建模時，`projection_degrade_reason` 必須寫入 payload
  並在 run warnings 出現——靜默退回 legacy 是被禁止的
- 當前 mode 讀不到的 override（如 structural 下的 `ebitda_margin`）會列入
  warnings，不會靜默忽略

### Comps anchor 規則

- peer universe：`company_context.get_peers`（24h cache）；剔除市值 < 本體/20 的 peer
- 每指標需 ≥3 個 peer 有值；先 IQR winsorize 再取 quartiles
- PEG 用 forward EPS 成長：只取**最近兩個未來會計年度**（過去年度一律排除，
  避免歷史成長冒充 forward），成長超出 clamp [2%, 60%] 回 `None`，
  **不得**改抓更後面成長更高的年度配對
- anchor 需 ≥2 個可用指標，否則 null
- provider exact-industry/business-model peers不足時，讀取 audited curated
  cohort；候選 provenance 與 limitations 必須存在，P/E 數字仍由
  `company_context.get_ratios_ttm` 取得，≥3 正值才輸出 `peer_pe_range_scenario`；
  config `schema` 版本不符時回報 `unsupported_cohort_schema`（非「查無 cohort」）
- cohort 樣本太小無法 winsorize，因此同時輸出 `pe_min`/`pe_max` 與
  `value_low`/`value_high`，讓單一週期高點倍數對中位數的影響可見
- `peer_pe_range_scenario.scope = range_only`：不得填入 `comps_implied` 或
  `peer_pe_implied` live anchor；只用於 `valuation_explained_range`。canonical
  peer set eligible 時報告**不渲染**第二張 peer 表（payload 仍保留供審計）

### DCF-primary explained range

- `primary_fv`：eligible `structural_shift_through_cycle` DCF
- `primary_sensitivity`：DCF 5×5 grid 的 min/max
- `scenario_without_peer`：fundamental family representative
- `scenario_with_peer`：without-peer scenario 與 range-only peer P/E scenario
  的兩個獨立 family 等權點
- `range_low/high`：上述點的 envelope；上緣不是新的單點 fair value

## Outputs

- `reports/YYYYMMDD_<T>_dcf_model.md` — 假設表（含 provenance）+ FCFF 投影 + sensitivity
- `reports/YYYYMMDD_<T>_comps.md` — peer multiples 表 + implied values + anchor
- `reports/YYYYMMDD_<T>_valuation_model.xlsx` —（`--xlsx`）Cover / Assumptions /
  DCF Model / Sensitivity（紅綠 vs 現價）/ Comps 五個 sheet；openpyxl 缺席時
  graceful skip（stderr 警告，rc 不變）
- Cache: `cache/<T>_<endpoint>.json` TTL 24h（走 `scripts/_shared/fmp_pool` 統一限流）

## Tests

```bash
python3 skills/valuation-modeler/tests/test_dcf.py          # 104 asserts, golden fixture
python3 skills/valuation-modeler/tests/test_comps.py        # 52 asserts
python3 skills/valuation-modeler/tests/test_export_xlsx.py  # 13 asserts (skips w/o openpyxl)
```

全部零網路（fixture 直測純函數）。golden 值 $248.41 為人工驗算 baseline。

## Boundaries

- **是**：可審計估值模型（假設可調、每個數字可追溯）、protocol 的 2 個新 anchor 來源
- **不是**：不重跑 protocol、不寫 history.json、不做 buy/sell verdict —
  anchor 之外的用途皆為分析參考
- 與 `earnings-valuation-forecaster` 互補不重疊：forecaster 是 12 個月
  scenario 目標價（earnings × multiple）；本 skill 是內在價值（FCFF DCF）+
  相對估值（comps）

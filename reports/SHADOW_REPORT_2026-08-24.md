# Shadow Report — 2026-08-24

> 唯讀讀出端。history entries scanned: 209。

## #2 Anchor Dispersion（backfill — 立即可用）

- 樣本 n=96，CV min/P33/median/P66/max = 0.0209 / 0.4072 / 0.4678 / 0.5638 / 1.3419
- 現行門檻 high<0.15 / low>0.35（拍腦袋初值）
- **建議門檻（33/66 pct）**: high<0.4072 / low>0.5638
- 建議門檻 = 歷史 CV 33/66 percentile（三等分 high/medium/low）。#2 cap 接線前由 user 核可。

## #6 Owner-Earnings 倍數 shadow

- 累積 30/20 session；翻轉 14 筆（rate=0.4667）；decision: **keep_static_pending_backtest**
- checkpoint: ≥20 session 且翻轉率 <15% → 切換提案

## #3 Valuation Archetype shadow

- 累積 62/20 session；翻轉率 0.4194；archetype 分布 {'hypergrowth': 33, 'balanced': 22, 'cyclical': 3, 'financial': 4}
- checkpoint: ≥20 session → 翻轉率報告 → user 拍 → #3b 切 live（含 cap/T5 接線）

## #4 News PT 去重監測

- post-切換 8 session（凍結窗剩 2）
- baseline mean 1.71 → post mean 1.125（shift -0.585）
- 分布 baseline {'-1': 1, '0': 2, '1': 6, '2': 18, '3': 4} → post {'-1': 1, '0': 1, '1': 3, '2': 2, '3': 1}
- leakage: 0/59（rate=0.0）
- 預期 post mean 較 baseline 下移（PT +1 源移除）；下移 ≈ 證實 PT 曾在計分。凍結窗滿後恢復 News weight 調整。

## L5 Sentiment deterministic shadow

- 累積 6/20 筆樣本；方向翻轉 0 筆（rate=0.0，門檻 <20%）；decision: **accumulating**
- |det − LLM| 平均 0.002／最大 0.005
- checkpoint: ≥20 筆 shadow 樣本（1 筆 = 一支個股的一次分析，非 session 數）且方向翻轉率（POS↔NEG 對翻）<20% → 翻預設提案（**需使用者拍板**）。翻後照 V3.45.4 News 前例上 weight 凍結窗。det 拿掉了 LLM 的規則表外因子，分數差異是預期的；band_mismatch（NEUTRAL↔方向性）另列——它量的是帶寬不是方向，集中出現時該檢討 SENTIMENT_NEUTRAL_BAND 而不是擋翻預設。另看 missing_inputs 是否集中在同幾檔。

| 日期 | ticker | LLM | det | Δ | 方向 | missing |
|---|---|---|---|---|---|---|
| 2026-08-07 | NET | 0.97 | 0.965 | -0.005 | POS→POS | 2 |
| 2026-08-07 | AAOI | -0.55 | -0.545 | +0.005 | NEG→NEG | 2 |
| 2026-08-09 | PLTR | 0.33 | 0.33 | +0.0 | NEUTRAL→NEUTRAL | 2 |
| 2026-08-09 | BAC | 0.83 | 0.83 | +0.0 | POS→POS | 2 |
| 2026-08-10 | RKLB | 0.08 | 0.08 | +0.0 | NEUTRAL→NEUTRAL | 2 |
| 2026-08-10 | NVDA | 0.58 | 0.58 | +0.0 | POS→POS | 2 |

## FWD_PE_CLAMP 校準（V4.108.0 — 反解市場隱含 PE，立即可用）

- 來源 `*_pf_quant.json`（同標的取最新一次）；全母體 n=17，其中 anchor live **n=3**
- **live cohort**（判準來源）隱含 PE min/P33/median/P66/max = 29.3 / 31.0 / 31.8 / 101.6 / 241.3
- 全母體（背景脈絡，混 archetype，**不是**校準目標）= 8.0 / 25.6 / 29.3 / 35.2 / 241.3；帶內 8/17，高於上限 6，低於下限 3
- 現行 clamp [15.0, 35.0]；上限實際綁到 6/17（rate=0.3529）
- 折現率：beta fallback 0/17（rate=0.0，資料品質訊號——偏高就該重量 `FWD_BETA_FALLBACK`）；折現率 clamp 綁到 4/17
- **判準**: accumulating（live cohort 3/5）
- 上限校準判準 = **live cohort** 的市場隱含 PE P33–P66 是否包住現行上限（包住 = 對中位數標的不帶方向）。全母體那組只是背景脈絡，混了 archetype，不可當校準目標。**不可自動跟隨中位數**：泡沫期中位數上移、上限跟著上移，錨就永遠不會說貴——與 agreement_grade 同紀律，改值一律 user 核准。

| ticker | 狀態 | 目標年 | 市場隱含 PE | 我們給的 PE | 未夾前 | clamp | anchor | 價 |
|---|---|---|---:|---:|---:|---|---:|---:|
| AAOI | eligible | 2027-12 | 29.3 | 35.0 | 454.9 | upper | 153.35 | 128.2505 |
| BAC | ineligible | 2028-12 | 13.5 | 15.0 | 11.87 | lower | 70.02 | 63.17 |
| BE | ineligible | 2029-12 | 36.8 | 35.0 | 41.8 | upper | 195.25 | 205.35 |
| COIN | ineligible | 2029-12 | 43.1 | 35.0 | 50.25 | upper | 140.08 | 172.35 |
| ECHO | eligible | 2028-12 | 31.8 | 31.49 | 31.49 | — | 84.52 | 85.4396 |
| GEV | ineligible | 2029-12 | 28.3 | 34.87 | 34.87 | — | 1190.57 | 966.01 |
| GOOGL | ineligible | 2029-12 | 23.6 | 15.0 | 14.59 | lower | 219.46 | 344.9229 |
| META | ineligible | 2029-12 | 16.4 | 27.03 | 27.03 | — | 977.93 | 592.1 |
| MRVL | ineligible | 2030-01 | 32.0 | 30.01 | 30.01 | — | 222.68 | 237.695 |
| MU | ineligible | 2029-08 | 8.0 | 15.0 | 9.98 | lower | 1838.16 | 974.33 |
| NOW | ineligible | 2029-12 | 24.3 | 16.55 | 16.55 | — | 85.01 | 124.88 |
| NVDA | ineligible | 2030-01 | 28.2 | 15.0 | -19.9 | lower | 115.45 | 216.85 |
| PLTR | ineligible | 2029-12 | 38.5 | 35.0 | 94.95 | upper | 161.73 | 177.845 |
| RKLB | eligible | 2029-12 | 241.3 | 35.0 | 84.24 | upper | 12.01 | 82.83 |
| SNDK | ineligible | 2029-07 | 12.2 | 15.0 | 3.46 | lower | 1961.13 | 1600.62 |
| TER | ineligible | 2028-12 | 37.1 | 31.48 | 31.48 | — | 366.3 | 432.185 |
| TSLA | ineligible | 2029-12 | 78.0 | 35.0 | 108.44 | upper | 151.16 | 336.87 |

## Lane Model 分層哨兵（V4.0.0 — Sent/News/Tech → Sonnet 監測）

- 近 10 session（baseline n=97）lane mean drift：
  - fundamentals: baseline 1.41 → recent 2.77（drift 1.36）
  - sentiment: baseline 0.36 → recent 0.17（drift -0.19）
  - news: baseline 1.76 → recent 2.4（drift 0.64）
  - technical: baseline 0.66 → recent 0.53（drift -0.13）
- 近 10 val DISAGREE: 0；polarization 異常: 6
- 哨兵規則：降級 lane 的 |drift| 明顯 > 其他 lane、或 DISAGREE/BIPOLAR 率較歷史升 → 該 lane 改回 inherit（V4.0.0 Phase 2 model 分層表）

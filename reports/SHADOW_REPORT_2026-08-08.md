# Shadow Report — 2026-08-08

> 唯讀讀出端。history entries scanned: 183。

## #2 Anchor Dispersion（backfill — 立即可用）

- 樣本 n=71，CV min/P33/median/P66/max = 0.033 / 0.3807 / 0.4559 / 0.5406 / 1.3224
- 現行門檻 high<0.15 / low>0.35（拍腦袋初值）
- **建議門檻（33/66 pct）**: high<0.3807 / low>0.5406
- 建議門檻 = 歷史 CV 33/66 percentile（三等分 high/medium/low）。#2 cap 接線前由 user 核可。

## #6 Owner-Earnings 倍數 shadow

- 累積 15/20 session；翻轉 5 筆（rate=0.3333）；decision: **accumulating**
- checkpoint: ≥20 session 且翻轉率 <15% → 切換提案

## #3 Valuation Archetype shadow

- 累積 36/20 session；翻轉率 0.3056；archetype 分布 {'hypergrowth': 17, 'balanced': 16, 'cyclical': 3}
- checkpoint: ≥20 session → 翻轉率報告 → user 拍 → #3b 切 live（含 cap/T5 接線）

## #4 News PT 去重監測

- post-切換 7 session（凍結窗剩 3）
- baseline mean 1.71 → post mean 1.0（shift -0.71）
- 分布 baseline {'-1': 1, '0': 2, '1': 6, '2': 18, '3': 4} → post {'-1': 1, '0': 1, '1': 3, '2': 1, '3': 1}
- leakage: 0/33（rate=0.0）
- 預期 post mean 較 baseline 下移（PT +1 源移除）；下移 ≈ 證實 PT 曾在計分。凍結窗滿後恢復 News weight 調整。

## L5 Sentiment deterministic shadow

- 累積 2/20 筆樣本；方向翻轉 0 筆（rate=0.0，門檻 <20%）；decision: **accumulating**
- |det − LLM| 平均 0.005／最大 0.005
- checkpoint: ≥20 筆 shadow 樣本（1 筆 = 一支個股的一次分析，非 session 數）且方向翻轉率（POS↔NEG 對翻）<20% → 翻預設提案（**需使用者拍板**）。翻後照 V3.45.4 News 前例上 weight 凍結窗。det 拿掉了 LLM 的規則表外因子，分數差異是預期的；band_mismatch（NEUTRAL↔方向性）另列——它量的是帶寬不是方向，集中出現時該檢討 SENTIMENT_NEUTRAL_BAND 而不是擋翻預設。另看 missing_inputs 是否集中在同幾檔。

| 日期 | ticker | LLM | det | Δ | 方向 | missing |
|---|---|---|---|---|---|---|
| 2026-08-07 | NET | 0.97 | 0.965 | -0.005 | POS→POS | 2 |
| 2026-08-07 | AAOI | -0.55 | -0.545 | +0.005 | NEG→NEG | 2 |

## FWD_PE_CLAMP 校準（V4.108.0 — 反解市場隱含 PE，立即可用）

- 來源 `*_pf_quant.json`（同標的取最新一次）；全母體 n=0，其中 anchor live **n=0**
- **live cohort**（判準來源）隱含 PE min/P33/median/P66/max = None / None / None / None / None
- 全母體（背景脈絡，混 archetype，**不是**校準目標）= None / None / None / None / None；帶內 0/0，高於上限 0，低於下限 0
- 現行 clamp [15.0, 35.0]；上限實際綁到 0/0（rate=None）
- 折現率：beta fallback 0/0（rate=None，資料品質訊號——偏高就該重量 `FWD_BETA_FALLBACK`）；折現率 clamp 綁到 0/0
- **判準**: accumulating（live cohort 0/5）
- 上限校準判準 = **live cohort** 的市場隱含 PE P33–P66 是否包住現行上限（包住 = 對中位數標的不帶方向）。全母體那組只是背景脈絡，混了 archetype，不可當校準目標。**不可自動跟隨中位數**：泡沫期中位數上移、上限跟著上移，錨就永遠不會說貴——與 agreement_grade 同紀律，改值一律 user 核准。

## Lane Model 分層哨兵（V4.0.0 — Sent/News/Tech → Sonnet 監測）

- 近 10 session（baseline n=71）lane mean drift：
  - fundamentals: baseline 1.25 → recent 1.75（drift 0.5）
  - sentiment: baseline 0.32 → recent 0.1（drift -0.22）
  - news: baseline 1.68 → recent 1.47（drift -0.21）
  - technical: baseline 0.63 → recent -1.3（drift -1.93）
- 近 10 val DISAGREE: 4；polarization 異常: 9
- 哨兵規則：降級 lane 的 |drift| 明顯 > 其他 lane、或 DISAGREE/BIPOLAR 率較歷史升 → 該 lane 改回 inherit（V4.0.0 Phase 2 model 分層表）

# Shadow Report — 2026-06-15

> 唯讀讀出端。history entries scanned: 156。

## #2 Anchor Dispersion（backfill — 立即可用）

- 樣本 n=48，CV min/P33/median/P66/max = 0.0394 / 0.4222 / 0.472 / 0.5334 / 1.2726
- 現行門檻 high<0.15 / low>0.35（拍腦袋初值）
- **建議門檻（33/66 pct）**: high<0.4222 / low>0.5334
- 建議門檻 = 歷史 CV 33/66 percentile（三等分 high/medium/low）。#2 cap 接線前由 user 核可。

## #6 Owner-Earnings 倍數 shadow

- 累積 4/20 session；翻轉 0 筆（rate=0.0）；decision: **accumulating**
- checkpoint: ≥20 session 且翻轉率 <15% → 切換提案

## #3 Valuation Archetype shadow

- 累積 11/20 session；翻轉率 0.0909；archetype 分布 {'hypergrowth': 4, 'balanced': 5, 'cyclical': 2}
- checkpoint: ≥20 session → 翻轉率報告 → user 拍 → #3b 切 live（含 cap/T5 接線）

## #4 News PT 去重監測

- post-切換 3 session（凍結窗剩 7）
- baseline mean 1.71 → post mean 2.0（shift 0.29）
- 分布 baseline {'-1': 1, '0': 2, '1': 6, '2': 18, '3': 4} → post {'1': 1, '2': 1, '3': 1}
- leakage: 0/11（rate=0.0）
- 預期 post mean 較 baseline 下移（PT +1 源移除）；下移 ≈ 證實 PT 曾在計分。凍結窗滿後恢復 News weight 調整。

## Lane Model 分層哨兵（V4.0.0 — Sent/News/Tech → Sonnet 監測）

- 近 10 session（baseline n=44）lane mean drift：
  - fundamentals: baseline 1.11 → recent 0.7（drift -0.41）
  - sentiment: baseline 0.58 → recent 0.25（drift -0.33）
  - news: baseline 1.74 → recent 1.98（drift 0.24）
  - technical: baseline 1.17 → recent 0.0（drift -1.17）
- 近 10 val DISAGREE: 9；polarization 異常: 8
- 哨兵規則：降級 lane 的 |drift| 明顯 > 其他 lane、或 DISAGREE/BIPOLAR 率較歷史升 → 該 lane 改回 inherit（V4.0.0 Phase 2 model 分層表）

# Investment Protocol V5.0 — Design Notes (human-only, NOT loaded at runtime)

> 這裡放 `investment_protocol_v5_0.md` 抽出的**設計理由 / 痛點 / 動機**。
> 純給人讀，protocol 執行時**不需要**載入(省每-turn context)。
> 所有對應的**操作規則**仍留在主 protocol 的 Phase 3 step 定義裡 — 這裡只解釋「為什麼」。

---

## V2.18.0 — Structural Shift Modulation 設計理由

**痛點**：MU/QCOM 案例顯示 Valuation Lane（被過時 analyst PT 拖累）+ Red Team（用歷史週期 mean-reversion 攻擊）+ Macro（sector_avoid 一視同仁壓 multiplier）三個 backward-looking 模型同時壓制 forward signal，導致超級週期股票被迫 `DEFENSIVE HOLD`，錯失主升段。

**機制**：earnings-analyst (`compute_structural_shift`) 偵測 EPS QoQ ≥30% + GM 歷史 +2σ + revenue 加速三個 signal，≥2 過 → CANDIDATE，連 2 季 → CONFIRMED。Phase 3 讀此 tier 對症給予豁免。

**安全閥**：
- CANDIDATE 只放寬不解除，position cap 50% — 避免單季 noise 導致 bubble-top BUY
- CONFIRMED 才完全解除估值錨點，但仍要求 Red Team 必須以 forward mechanism breakage 攻擊（不接受純歷史均值論證）
- Tier 不影響 Step 1 raw_total — 個別 lane 仍然獨立評分；modulation 只動 Step 2/3 的 backward-looking 折扣

**對稱性原則**：missing top 是 bounded loss（少賺）；buying top 是 unbounded loss（套牢）。Tier 階梯 + position cap 把後者風險壓住。

---

## V2.19.0 — Lane Polarization + Red Team Anti-Spoofing 設計理由

**痛點 1 — Lane 各自為政**：5 lane 獨立評分後 PM 加權平均，但加權平均把「集體看多」(ALIGNED +2) 和「兩極衝突」(+3 +3 -3 -3 +1) 都壓平成中性數字，喪失「lane 衝突 = 系統不確定性」的訊號。Phase 3 沒做 divergence detection。

**痛點 2 — Red Team 偷渡 mean-reversion**：V2.18 在 PM 端 post-filter，但 Red Team prompt 仍用標準歷史攻擊；LLM 常塞 1 個 forward 關鍵字（"客戶庫存"）但本質是 mean-reversion 論證（"歷史均值"），表面 mixed 實則污染。

**機制 1 — Polarization 4-tier**：reuse 既存 `apply_det_shadow.compute_polarization`，加 OUTLIER 級避免 4-vs-1 outlier 誤判 BIPOLAR。Phase 3 Step 1.7 對應 confidence multiplier 0.5/0.85/0.75/1.0。

**機制 2 — Red Team basis classifier**：deterministic keyword scan（mr_keywords + fw_keywords）→ 4 級 basis（pure_forward / pure_mean_reversion / contaminated / unclassified）。CONFIRMED 狀態下 contaminated 跟 pure_mean_reversion 同等對待 → STRONG_COUNTER 自動降 MODERATE。

**Anti-Adversarial 鐵律**：
1. **mr 一票否決**：mr keyword 出現即觸發 dampening，無論搭配多少 fw keyword
2. **OUTLIER 不誤殺**：4-vs-1 不是真衝突，confidence × 0.85（不像 BIPOLAR 砍倉位）
3. **雙層防偽**：prompt 限制 + post-filter classifier，不單靠 LLM 自律

---

## V2.14.0 — IC-memo 結構強化動機

對齊機構級投資決策備忘錄 (PE 業界標準 ic-memo skill pattern) — 強迫呈現「consensus vs differentiated view」避免 echo chamber，Kill Conditions numbered 加強執行紀律，Returns Profile 三檔給未來 thesis review 一致對照基準。所有欄位來源**仍是** Phase 2-4 已產出 JSON，formatter 不重新評分。

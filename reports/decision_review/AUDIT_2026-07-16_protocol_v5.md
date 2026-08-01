# 審計報告：分析 [TICKER] 協議（investment_protocol_v5_0）全面檢討

- **日期**：2026-07-16
- **範圍**：`分析 [TICKER]` 協議全部 phases / lanes / 周邊 skills
- **方法**：協議文件逐行審查 + 過往輸出全量統計 + 兩個新增統計檢驗
- **數據樣本**：`history.json` 177 sessions / 168 trades（2026-04-07 → 2026-07-08）、76 個 phase0 檔、164 份 ticker 報告、316 個 short-term-target cache、`event_index_latest.json` 406 筆決策（deep-dive 163 筆，其中 30 天窗口完成且可 join history 者 134 筆）
- **重現**：統計檢驗腳本 `reports/decision_review/audit_stats_2026-07-16.py`（read-only，不改任何引擎）

---

## 執行摘要

1. **保守偏誤是最大實際虧損來源**：59.9% 決策 CANCEL；覆盤證實 conservative miss 46.3% vs active 22.2%，錯過的是 +28% runup 而非避開 −5% drawdown（F1）。
2. **Red Team 統計上無效**：80.4% 裁決是 STRONG_COUNTER，且本次新檢驗證實其與 30 天後果**零相關**——被強烈反對的標的平均反而漲更多（F2 + 檢驗 A）。
3. **估值 anchor 無品質 gate**：11.6 倍離散的 anchors 照樣加權，引擎算好的 dispersion/agreement_grade 純展示不接線（F3）。
4. **LLM confidence 在核心區間無鑑別度**：0.6 與 0.7 bucket 方向命中率完全相同（67%），只有極端低值有訊號（F4 + 檢驗 B）。
5. **9 類 LLM 產出無下游消費者**，純燒 token（F5）。
6. 另有文件↔實作斷鏈（F6）、Phase 6 自我強化回路（F7）。

---

## 新增統計檢驗（2026-07-16）

### 檢驗 A：Red Team verdict × 30 天實際結果 —— 結論：無預測力

樣本：134 筆（30 天窗口完成、event index join history 成功）。
rt 分佈：STRONG_COUNTER 105 / None 21 / MODERATE_COUNTER 8。

| 分組 | n | 30d 平均報酬 | 中位數 | 顯著性 |
|---|---|---|---|---|
| STRONG_COUNTER | 105 | **+12.52%** | +4.75% | — |
| MODERATE/other | 8 | +8.64% | +5.08% | diff +3.88pp, p=0.689 |
| （無 red team） | 21 | +14.39% | +7.83% | — |

- **方向反了**：若紅隊有訊號，STRONG_COUNTER 標的應表現更差；實際反而更好（不顯著，即零資訊）。
- Drawdown 亦無差異：STRONG −7.36% vs other −6.39%（p=0.766）。
- 紅隊反對但仍執行的 45 筆：平均 **+15.29%**——紅隊反對完全沒有攔到壞 trade。
- 紅隊反對且 CANCEL 的 60 筆：**57% 之後照漲**（平均 +10.44%）——紅隊「成功阻止」的名單一半以上是錯殺。

**財務解讀**：一個 80% 時間輸出同一裁決、且裁決與結果零相關的委員，其意見不是風控是噪音。現制對 STRONG_COUNTER 施加 ×0.85 懲罰，等於對「平均 30 天會漲 12.5% 的標的」系統性砍分——這直接加重 F1 的保守偏誤。注意樣本期為多頭段（見侷限），但即使在多頭段，一個有效的反方訊號至少應在 drawdown 維度顯示分辨力，實際沒有。

### 檢驗 B：LLM confidence 校準 —— 結論：核心區間無鑑別度

方向命中定義：sign(final_score) 與 sign(30d return) 一致（|ret|≥1%、|score|≥0.05，n=125）。

| avg_confidence bucket | 方向命中率 |
|---|---|
| 0.3 | 1/4 = 25% |
| 0.5 | 10/19 = 53% |
| 0.6 | 31/46 = **67%** |
| 0.7 | 36/54 = **67%** |
| 0.8 | 2/2 = 100% |

- Spearman ρ(conf, 方向命中) = **+0.168**（permutation p=0.061，邊緣）；改用覆盤 hit/miss 標籤則 ρ=+0.056 ≈ 0。
- 全部訊號來自尾端（0.3 bucket 的 25%）；**佔 80% 樣本的 0.6–0.7 帶內完全無鑑別度**（67% vs 67%）。
- 對照：avg_confidence 全樣本 mean 0.597 / stdev 0.117——LLM 幾乎永遠回報 0.5–0.7。

**財務解讀**：confidence 作為 `raw_total = Σ(W×S×C)` 的連續乘項，實際效果 ≈ 全體乘常數 0.6，卻讓每個 lane 多一個 LLM 自由發揮的數字。有效資訊只有「極端低 conf = 危險旗標」一個 bit。附帶發現：final_score 本身 ρ(score, 30d ret)=+0.186，弱但方向正確——分數有一點訊號，confidence 沒有增量。

### 侷限（誠實聲明）

- 樣本期 2026-04 → 07 為多頭段（全樣本 30d 平均報酬 +12.5%），保守偏誤的機會成本在空頭段會縮小；但檢驗 A 的「drawdown 無分辨力」與檢驗 B 的「校準平坦」不依賴多頭假設。
- 30 天窗口偏短，對 long horizon 論點（如 DCF anchor）不構成完整檢驗。
- MODERATE/None 組僅 29 筆，檢定力有限——但這本身就是問題：對照組小到無法檢定，正是因為裁決分佈退化到單一值。

---

## 發現明細

### F1. 保守偏誤【高】
- CANCEL 106/177（59.9%）、EXECUTE 41、STAGED 29、HOLD 1。
- 覆盤已證實（`REVIEW_2026-06-28.md:85-97`）：conservative miss 46.3% vs active 22.2%；半導體內 conservative miss 66.7% vs active 12.0%（同產業同期差 55pp）；miss 的平均 runup +27.97% vs drawdown 僅 −4.91% → 「平順錯過上漲」，非避險。
- 根因（覆盤 H1 確認）：正分模糊區 `[0, staged_threshold)` default HOLD；結構性放大器：懲罰乘數疊乘——structural shift ×0.925 × polarization conf×0.75 × red team ×0.85 × macro ×0.9…每層單獨合理，疊起來系統性向下壓分（`investment_protocol_v5_0.md:781-910`）。
- 檢驗 A 補刀：×0.85 紅隊懲罰無資訊基礎，卻是疊乘鏈的固定一環（80% 案例觸發）。

### F2. Red Team 是昂貴的儀式【高】
- STRONG_COUNTER 135/168（80.4%）——裁決熵趨近零；consensus_bonus 僅 1/168 觸發（×1.15 名存實亡）；`red_team_execution_failed` 0/168。
- kill_conditions 449/475（94.5%）為 `IF … WITHIN … 天 THEN …` 固定句式填空，且不進任何決策數學（`v5_0.md:1045`）。
- 機制上是 soft multiplier 而非 gate：STRONG_COUNTER → ×0.85（可被 cascade 軟化至 ×0.925/×0.95），從不強制 HOLD（`v5_0.md:850-901`）。
- 檢驗 A 證實裁決與結果零相關。**現制的紅隊 = 一行 `×0.85` 常數 + 一段模板文字，成本卻是一個不可降級的 subagent**（`v5_0.md:238-254`）。

### F3. 估值 anchor 無品質 gate【高，幻覺主戰場】
- NVDA 2026-07-08（`reports/20260708_NVDA.md:112-155`）：anchors $31.80（owner_earnings×15）～ $369.30（peer_pe），**11.6 倍離散**，仍標「錨一致度 medium / confidence high / extreme_undervalued」。owner_earnings×15 對高成長 archetype 根本不適用，仍以 0.05 權重進 weighted_fair_value $269.24。
- TXN 2026-06-22：Valuation 合理價 $91.56 vs 現價 $322（−71.6%），靠 mandatory_risk_flag 硬保險才未觸發熱區 probe（`REVIEW_2026-06-28.md:45`）。
- 引擎其實已算出 `anchor_dispersion_cv` / `agreement_grade` / P25-P75，但 agreement_grade 等「純展示，不接 Phase 4.6 cap，接線留 P2」（`protocol_appendix_price_framework.md:129,151-153`）——防線做好了沒插電。
- 報告中出現無來源精確數字：PEG 0.59、隱含 5Y FCF CAGR 50.3%（全文無計算輸入引用）。

### F4. confidence 與 macro multiplier 是偽變數【中】
- confidence：見檢驗 B。
- `phase3_macro_multiplier`：0.9 出現 70/76（92%），其餘 0.75×4 / 1.0×2；`macro_multiplier_rationale` 文字模板化重複（同開頭 40 字樣板 ×6、×7 組）。整條 Phase 0 LLM baseline → 乘數管線的資訊量 ≈ 一個常數（FRED cap 的 deterministic 部分才有變異）。
- `decision_confidence_pct`：n=63, mean 49.8 / stdev 12.2 ≈ 擲硬幣宣言。

### F5. LLM 白產清單（產出無下游消費者）【中，token 浪費】
| # | 項目 | 狀態 | 出處 |
|---|---|---|---|
| 1 | `systemic_backdrop` | 永遠 null 的 v0.1_stub | `v5_0.md:116-130`；實例 `2026-06-25_phase0_nvda.json:74-79` |
| 2 | `valuation_archetype_shadow` | shadow-only，≥20 session 才議切換 | `protocol_appendix_price_framework.md:163-197` |
| 3 | `fair_value_range` 的 agreement_grade/P25-P75/range_verdict | 純展示 | 同上 :129,151-153 |
| 4 | `owner_earnings_multiple_shadow` | 僅 shadow-log | 同上 :139-143 |
| 5 | Forward Expectations block（V4.26.0） | 最大孤兒 block，只渲染 MD | `v5_0.md:1214-1247` |
| 6 | `implied_expectations` | 唯一消費者 = Red Team「可選」kill seed | `v5_0.md:712,716` |
| 7 | `institutional_lens`/`scenario_odds`/`action_label` | 只進 MD；validator 連 odds 加總=100 都不驗 | `v5_0.md:1048-1067` |
| 8 | moat/TAM/bull-bear thesis/cross_asset/medium_term_shift 敘事 | 全標「不影響 score」 | `v5_0.md:321-435` |
| 9 | `news_pt_leakage`、`transition_data_stale_or_inconsistent` | 統計/警示用 | schema:324-326 |

- 另：short-term-target **5d horizon 84%（265/315）insufficient_data**；全 cache 67% 預測 \|幅度\|<1%、22% conf<0.2——大量「預測不動」的無效輸出。
- hot_zone_probe 上線 21 天 extractor 取得 0/160（TODO-015 儀器盲飛）。

### F6. 文件↔實作斷鏈【中，可靠性】
1. `large_cap_parabolic`：Technical lane 規則引用此 flag（`v5_0.md:444`），但該 lane MANDATORY 的 technical-analyst 不產它——只有 `momentum-monitor/scripts/momentum.py:673` 產，協議未把 momentum.py 列為該 lane MUST run。
2. forecaster `SKILL.md` 宣稱「not auto-wired」，但 `compute_price_framework.py:830-836` 實際讀其 cache 當 anchor（weight 0.05）——兩處聲明矛盾。
3. validator 只驗 schema：不驗 final_score 界限（放過 VRT `final_score=6.72` + `lane_scores=None` + HOLD/CANCEL 自相矛盾的紀錄）、不驗權重加總=1、不驗 scenario_odds 加總。
4. ftd-detector / market-top-detector skill 目錄 FMP 版閒置，Phase 0 實跑 `sector/` 複製改寫版（已列 backlog）。
5. news-digest `HIT_THRESHOLD_PCT=2.0` 誤套 SPY 致結構性 0% hit（TODO-011，已知）。

### F7. Phase 6 自我強化回路【中】
LLM 每 session 自調 lane 權重 ±0.05（`v5_0.md:1490-1511`），但 60% 決策 CANCEL 無結果回饋、無 out-of-sample 檢驗——模型用自己的判斷強化自己的判斷。檢驗 B 顯示其輸入（confidence）本身未校準。

---

## 優化路線圖

> **實施狀態（2026-07-16 同日）**：P0 四項已於 V4.70.0 落地（詳見 CHANGELOG）——P0-1 改為 Rec 11 probe 分數分層（15/30bps）、P0-2 懲罰依 strength 分級 + 新校準欄位、P0-3 引擎 anchor 修剪、P0-4 confidence 三檔量化。P1/P2 待核准。

### P0 — 決策品質（直接影響損益）
| # | 項目 | 對症 | 依據 |
|---|---|---|---|
| P0-1 | 模糊區 `[0, staged_threshold)` 改小額 probe（≤0.15% NAV）取代 default HOLD | F1 | 覆盤 Pattern A + H1 已確認 |
| P0-2 | Red Team 改制：verdict enum → 「可證偽測試 + 機率估計」；懲罰乘數改依 counter_evidence_strength 分級；或直接移除 ×0.85 改為 kill_conditions 進 watch 自動化 | F2 | 檢驗 A：零相關 |
| P0-3 | Anchor 品質 gate 接線：dispersion > 閾值 → trimmed anchors + confidence 強制降級 + Phase 4.6 cap（引擎已算好，只差接線） | F3 | NVDA/TXN 實例 |
| P0-4 | confidence 從連續乘項改 3 檔 rule-based（low<0.45 → 降級旗標；其餘視為常數） | F4 | 檢驗 B：0.6/0.7 無差異 |

### P1 — 砍白產（省 token、降幻覺面）
- P1-5 落日條款：shadow 欄位 ≥20 sessions 未接線即刪或接線（F5 表 #1/2/4/5）。
- P1-6 敘事欄位（moat/TAM/cross_asset/medium_term_shift/institutional_lens）移到 `--memo` 時才產。
- P1-7 short-term-target 5d horizon 廢棄或修數據源。
- P1-8 macro multiplier：LLM baseline → FRED 規則表直接映射（92% 是常數）。

### P2 — 一致性修補
- P2-9 修 `large_cap_parabolic` 斷鏈（momentum.py 入 Technical lane MUST run，或改引用 technical-analyst 的 `parabolic_risk`）。
- P2-10 forecaster SKILL.md 聲明同步。
- P2-11 validator 補強：final_score 界限、權重加總=1、scenario_odds 加總=100。
- P2-12 ftd/market-top 複製版與 skill 版整併（backlog 已列）。

### 每項的驗證方式
- P0-1/2：仿 `investment/scripts/replay_rec11.py` 模式寫 what-if replay，對 history.json 全樣本比較新舊規則 conservative miss rate。
- P0-3/4：以本報告腳本延伸，回測 dispersion→估值誤差、3 檔 conf→命中 的分辨力。
- P2-11：`validate_session_export.py` 加測試 case，rc 檢查。
- 協議文件改動後跑 `OPS_COMMANDS.md` §7 對應測試 rc=0。

---

*本報告為探索層分析產物，依全域紀律不自動進入任何決策參數；所有改制需使用者逐項核准後實施。*

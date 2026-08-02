# Decision Engine Replay — 2026-08-02

> Engine: `investment/scripts/decision_engine.py` · harness: `investment/scripts/replay_decision_engine.py` · score tolerance ±0.005
> Current-rule cutoff: decisions on/after **2026-07-16** (V4.70.0) run the math this engine implements; earlier entries are rule-drift measurement only.

## 1. Coverage（eligible + excluded = total，無隱藏截斷）

| 分類 | 筆數 |
|---|---|
| history trades 總數 | 172 |
| replayed（current rules） | 1 |
| replayed（pre-V4.70.0 rules，drift 量測） | 2 |
| excluded | 169 |
| **合計** | **172** |

## 2. Parity verdict（current rules）

- match: **1/1**
- mismatch: **0** → 需逐筆 triage

| date | ticker | lane source | stored score | replay score | Δ | stored decision | replay decision | verdict |
|---|---|---|---|---|---|---|---|---|
| 2026-08-02 | MU | `calculation_steps` | -0.2963 | -0.2963 | +0.0000 | HOLD | HOLD | ✓ match |

**當期規則但因未記錄輸入而排除的筆數（advisory 對照，非 parity 證據）**

這 3 筆決策日 ≥ 2026-07-16、lane 輸入齊全，只因 `structural_shift.tier` 等欄位未持久化、且 sweep 顯示會改變結果而排除。取 spec 預設值重算的結果列於下——一致代表 engine 與當時 PM 手算同號，但因假設成立與否無法證實，不計入 §2 的 parity 分母。

| date | ticker | lane source | stored → advisory score | Δ | decision | 一致 |
|---|---|---|---|---|---|---|
| 2026-07-31 | MU | `report:20260731_MU.md` | +0.7823 → +0.7823 | +0.0000 | HOLD → HOLD | ✓ |
| 2026-08-02 | MSFT | `report:20260802_MSFT.md` | +0.7290 → +0.7292 | +0.0002 | HOLD → HOLD | ✓ |
| 2026-08-02 | PLTR | `report:20260802_PLTR.md` | -0.2610 → -0.2613 | -0.0003 | HOLD → HOLD | ✓ |

## 3. Rule-version drift（pre-V4.70.0 cohort — 不計入 parity）

- 同號: 0/2；差異: 2
- 全部自動歸類 `rule_version_drift`：這些 entry 當時走連續 confidence 乘項與未分級的 cascade 懲罰，用今天的規則重算本來就會不同。差異幅度即 V4.70.0 的實際衝擊。

- |Δfinal_score| 中位數 0.0126、最大 0.0126；decision 改變 0 筆

| date | ticker | stored → replay score | Δ | stored → replay decision |
|---|---|---|---|---|
| 2026-05-07 | ALAB | -0.3825 → -0.3900 | -0.0075 | HOLD → HOLD |
| 2026-06-13 | MU | +0.6396 → +0.6270 | -0.0126 | HOLD → HOLD |

## 4. Exclusions（逐筆列出，無 silent cap）

### `pre_v5_four_lane_schema` — 94 筆

> session_export_version='V4.6' predates the 5-lane weighting (replayable: V5.0, V5.1, V5.2)

- **V4.6**（21 筆）：2026-04-15/AMD, 2026-04-15/APLD, 2026-04-15/APP, 2026-04-15/AVGO, 2026-04-15/CRWV, 2026-04-15/GOOGL, 2026-04-15/IONQ, 2026-04-15/LITE, 2026-04-15/META, 2026-04-15/MU, 2026-04-15/NBIS, 2026-04-15/NVDA, 2026-04-15/ORCL, 2026-04-15/PLTR, 2026-04-15/RGTI, 2026-04-15/SMR, 2026-04-15/TSLA, 2026-04-15/TSM, 2026-04-15/VST, 2026-04-16/AMD, 2026-04-17/BAC
- **V4.8**（73 筆）：2026-04-18/AMD, 2026-04-18/AVGO, 2026-04-18/INTC, 2026-04-18/MSFT, 2026-04-18/MU, 2026-04-18/TSLA, 2026-04-19/CFG, 2026-04-19/CHRW, 2026-04-19/EME, 2026-04-19/HPE, 2026-04-19/IR, 2026-04-21/AAPL, 2026-04-21/ALAB, 2026-04-21/AMZN, 2026-04-21/APLD, 2026-04-21/GOOGL, 2026-04-21/MRVL, 2026-04-21/MU, 2026-04-21/NTRS, 2026-04-21/NVTS, 2026-04-21/ORCL, 2026-04-21/STT, 2026-04-21/TEL, 2026-04-22/ALAB, 2026-04-22/GEV, 2026-04-22/HPE, 2026-04-22/MRVL, 2026-04-22/MSFT, 2026-04-22/NTRS, 2026-04-22/NVDA, 2026-04-23/POET, 2026-04-23/TSM, 2026-04-23/VRT, 2026-04-24/FCX, 2026-04-24/MRVL, 2026-04-24/MU, 2026-04-24/NEE, 2026-04-24/ON, 2026-04-25/SNA, 2026-04-26/AIZ, 2026-04-26/AVGO, 2026-04-26/CSCO, 2026-04-26/CSX, 2026-04-26/DLR, 2026-04-26/GSAT, 2026-04-26/NVDA, 2026-04-26/QCOM, 2026-04-26/TSM, 2026-04-26/VRT, 2026-04-27/AAOI, 2026-04-27/ALAB, 2026-04-27/ARM, 2026-04-27/CRM, 2026-04-27/FTV, 2026-04-27/GLW, 2026-04-27/LITE, 2026-04-27/MU, 2026-04-27/NOW, 2026-04-27/NVDA, 2026-04-27/PKG, 2026-04-27/SLB, 2026-04-27/TSM, 2026-04-28/BE, 2026-04-28/HUBB, 2026-04-29/NVDA, 2026-04-29/TSM, 2026-05-01/AAPL, 2026-05-01/GOOG, 2026-05-01/LLY, 2026-05-01/MRVL, 2026-05-01/MU, 2026-05-02/TEAM, 2026-05-02/VRT

### `decision_sensitive_unknown` — 38 筆

> 未持久化的 Phase 3 輸入在這些 entry 上**真的會改變結果**，故不列入 parity。下表另附「spec 預設值」replay 作為 advisory（明確標示為假設，不是 parity 證據）。

| 被掃描的未知欄位 | 出現於幾筆 |
|---|---|
| `structural_shift.tier` | 38 |
| `gates.binary_event_within_48h` | 8 |
| `red_team.counter_evidence_strength` | 5 |
| `transition.rule2_eligible` | 3 |

- advisory（全部未知取 spec 預設：tier=NONE / strength=4 / rule2=off / binary_event=off）與存檔一致：**3/38**

| date | ticker | stored → advisory score | Δ | stored → advisory decision | 一致 |
|---|---|---|---|---|---|
| 2026-05-02 | EME | +0.6620 → +0.7704 | +0.1084 | HOLD → HOLD | ✗ |
| 2026-05-02 | GOOGL | +0.9546 → +1.0089 | +0.0543 | STAGED_ENTRY → STAGED_ENTRY | ✗ |
| 2026-05-02 | NVDA | +1.3050 → +1.4250 | +0.1200 | BUY → BUY | ✗ |
| 2026-05-02 | TEAM | +0.9030 → +1.0363 | +0.1333 | STAGED_ENTRY → STAGED_ENTRY | ✗ |
| 2026-05-02 | VRT | +0.6250 → +0.6053 | -0.0197 | HOLD → HOLD | ✗ |
| 2026-05-03 | LLY | +1.1000 → +1.1132 | +0.0132 | STAGED_ENTRY → STAGED_ENTRY | ✗ |
| 2026-05-03 | QCOM | +0.7225 → +0.8436 | +0.1211 | HOLD → STAGED_ENTRY | ✗ |
| 2026-05-03 | TSM | +1.4150 → +0.8680 | -0.5470 | BUY → STAGED_ENTRY | ✗ |
| 2026-05-05 | TSM | +1.4930 → +1.5390 | +0.0460 | BUY → BUY | ✗ |
| 2026-05-07 | AMD | +0.4620 → +0.5220 | +0.0600 | HOLD → STAGED_ENTRY | ✗ |
| 2026-05-07 | CRWV | +0.0455 → +0.0564 | +0.0109 | HOLD → HOLD | ✗ |
| 2026-05-08 | CRWV | -0.2750 → -0.3135 | -0.0385 | HOLD → HOLD | ✗ |
| 2026-05-08 | MU | +0.6920 → +0.7218 | +0.0298 | HOLD → STAGED_ENTRY | ✗ |
| 2026-05-08 | NEE | +0.1340 → +0.1539 | +0.0199 | HOLD → STAGED_ENTRY | ✗ |
| 2026-05-10 | HPE | +0.5860 → +0.6612 | +0.0752 | HOLD → HOLD | ✗ |
| 2026-05-10 | MU | +1.1940 → +1.1156 | -0.0784 | HOLD → STAGED_ENTRY | ✗ |
| 2026-05-10 | TSM | +1.4050 → +1.2349 | -0.1701 | BUY → BUY | ✗ |
| 2026-05-11 | NVDA | +1.8450 → +1.7955 | -0.0495 | BUY → BUY | ✗ |
| 2026-05-16 | MU | +0.6920 → +0.6494 | -0.0426 | HOLD → STAGED_ENTRY | ✗ |
| 2026-05-20 | GOOGL | +0.8060 → +0.7079 | -0.0981 | HOLD → STAGED_ENTRY | ✗ |
| 2026-05-20 | MRVL | +0.3600 → +0.3847 | +0.0247 | HOLD → STAGED_ENTRY | ✗ |
| 2026-05-20 | MU | +0.9940 → +0.9416 | -0.0524 | STAGED_ENTRY → STAGED_ENTRY | ✗ |
| 2026-05-20 | TSM | +1.4080 → +1.4763 | +0.0683 | BUY → HOLD | ✗ |
| 2026-05-23 | NOK | +0.3250 → +0.3232 | -0.0018 | HOLD → STAGED_ENTRY | ✗ |
| 2026-05-26 | CRWD | +0.1770 → +0.2167 | +0.0397 | HOLD → HOLD | ✗ |
| 2026-05-29 | MU | +0.9210 → +0.7942 | -0.1268 | HOLD → STAGED_ENTRY | ✗ |
| 2026-05-31 | TSM | +1.5637 → +1.4116 | -0.1521 | HOLD → BUY | ✗ |
| 2026-06-14 | AAPL | -0.6350 → -0.7002 | -0.0652 | HOLD → HOLD | ✗ |
| 2026-06-14 | RGTI | -0.3245 → -0.4050 | -0.0805 | HOLD → HOLD | ✗ |
| 2026-06-21 | NBIS | -0.0090 → -0.0513 | -0.0423 | HOLD → HOLD | ✗ |
| 2026-06-22 | AAPL | -0.1510 → -0.1710 | -0.0200 | HOLD → HOLD | ✗ |
| 2026-06-22 | NOK | -0.5890 → -0.6120 | -0.0230 | HOLD → HOLD | ✗ |
| 2026-06-27 | PLTR | -0.5700 → -0.7310 | -0.1610 | HOLD → HOLD | ✗ |
| 2026-07-08 | MU | +0.3810 → +0.4284 | +0.0474 | HOLD → HOLD | ✗ |
| 2026-07-08 | PLTR | +0.0120 → +0.0231 | +0.0111 | HOLD → HOLD | ✗ |
| 2026-07-31 | MU | +0.7823 → +0.7823 | +0.0000 | HOLD → HOLD | ✓ |
| 2026-08-02 | MSFT | +0.7290 → +0.7292 | +0.0002 | HOLD → HOLD | ✓ |
| 2026-08-02 | PLTR | -0.2610 → -0.2613 | -0.0003 | HOLD → HOLD | ✓ |

### `lane_inputs_unavailable` — 37 筆

> no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report)

| date | ticker | version | detail |
|---|---|---|---|
| 2026-05-03 | CRWV | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-05-03 | CRWV | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-05-03 | MSFT | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-05-07 | ORCL | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-05-07 | TSM | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-05-18 | MU | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-05-20 | D | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-05-29 | MRVL | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-05-30 | PANW | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-05-31 | MSFT | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-03 | PLTR | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-08 | MRVL | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-13 | GOOGL | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-13 | NOK | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-13 | SPCX | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-14 | ALAB | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-14 | AMD | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-14 | MRVL | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-14 | PLTR | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-14 | TSM | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-15 | ARM | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-15 | ORCL | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-18 | TSM | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-21 | MU | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-21 | NVDA | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-21 | PLTR | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-22 | CCJ | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-22 | CEG | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-22 | CRDO | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-22 | IONQ | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-22 | MRVL | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-22 | TXN | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-24 | JBL | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-24 | SNDK | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-24 | SPCX | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-06-27 | MSFT | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |
| 2026-07-08 | NVDA | V5.0 | no source carries all 5 lane scores + confidences (calculation_steps / event_index / MD report) |

## 5. Declared assumptions（會影響判讀，明寫不藏）

1. `proceed_to_phase3=true` — 由「session 走到 Phase 3 並產出決策」反推，非猜測。
2. `mandatory_risk_flags` — **V5.2 (V4.82.0) 起持久化**，該版之後的 entry 讀真值，不再是假設。此前的 entry 沒有這個欄位，replay 只能餵 `[]`；`[]` 等於斷言「沒有任何 flag 觸發」，而那正是無法保證的事。因此舊 entry 若 replay 給 BUY-side 而存檔是 HOLD，`unrecorded_gate_input` 仍是合法 triage 結論；新 entry 不再適用此免責。
3. `industry_top_30pct` 取自 event_index `sub_industry_heat`，那是**產生索引當下**的熱度、非決策當下；只影響 Rec 11 hot-zone 判定。
4. `calculation_steps` 來源的 lane confidence 由 C_eff 反推代表值（0.35→0.40 / 0.60→0.55 / 0.72→0.75）——decision 數學只吃 C_eff，故無損；但 `avg_confidence` 不在本 harness 的比對範圍內。
5. Phase 4.6 decision cap：entry 有存 `decision_cap_active` 時直接沿用該結果，否則由 `fair_value_summary` 的 anchors/confidence 與 `degraded_analysts` 重推。
6. `lane_source=calculation_steps` 的筆數獨立性較弱——輸入取自同一 entry 的 Step 1 字串、輸出比對 `final_score`/`final_decision` 兩個獨立欄位，能抓「鏈中段算錯」但抓不到「輸入本身抄錯」。`event_index` / `report` 來源沒有這個限制。


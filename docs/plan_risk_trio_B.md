# 風控三支 Batch B — 決策備忘（七項，逐項待拍板）

> 產生：2026-08-08（repo V4.111.7，Batch A 已 commit `01d422e`）。
> 承接 `docs/plan_risk_trio.md` §4。**每一項都會改變 position sizing 或 protocol 行為，未經使用者
> 逐項拍板不得動手。** 本檔只出選項與證據，不含任何已實施的變更。
> 所有 shadow 數字為 2026-08-08 實跑；重跑腳本留在 session scratchpad，必要時可重建。

## 摘要（先看這張表再讀內文）

| # | 題目 | 建議 | 一句話理由 |
|---|---|---|---|
| B2 | ×0.7 / ×1.15 有文件無實作 | **刪文件** | 自 V4.7 寫下起（~4 個月、174 筆）沒有一筆倉位依它調整過，補實作等於今天才開始改變倉位，而它從沒被驗證過 |
| B4 | 三支遷 technical_core | **不遷（維持 yfinance）** | 閘門是零翻轉，實測 16 檔翻 1 檔；FMP 不做除息調整，而尾部風險算的正是報酬分布 |
| B3 | sector 5 值 enum 死規則 | **sector 文件收斂為 3 值** | script 的三值是 protocol 唯一在用的字彙，sector 那套五值從來沒有產生器 |
| B1 | vol-scaling 失能 | **ceiling 參數化 + 預設不變** | 先讓它可被觀測，再談要不要改；現在改等於在沒有基線的情況下動全部倉位 |
| B7 | normalizer 再校準 + sector off-band 門檻 | **只修門檻對齊，不動 normalizer** | 實測分布 6/8/2 仍健康，normalizer 沒壞；壞的是 sector 那兩個 off-band 數字 |
| B5 | insider 換 fmp_supplementary | **不換（或換但要改映射）** | FMP 對 12 檔判 10 檔 distributing，直接映射會讓這個元件變成常數而非訊號 |
| B6 | drawdown-circuit-breaker | **設計可寫，但先不接線** | 資料源存在（開工表說沒有是錯的），但帳本只有 7 筆、全是獲利、全在 4 月 |

---

## B2 — `WARNING ×0.7` / `VALUE_BONUS ×1.15`：有文件無實作

### 現況（已實證）

`investment_protocol_v5_0.md:711` 與 `:713` 的表明寫：

| Verdict | Score | Phase 4 影響 |
|---|---|---|
| `WARNING` | 20-35 | Phase 4 final × 0.7 |
| `VALUE_BONUS` | ≥ 60 | Phase 4 final × 1.15 |

`skills/short-contrarian-analyst/SKILL.md:48-49` 重複同一宣稱。

**而 sizing chain 裡沒有這一段。** `trade_plan_builder.py` 九段 chain 只有
`burry_override_adj`（`:622-624`，OVERRIDE_BURRY 的 ×0.5），`grep -rn "VALUE_BONUS\|WARNING"
investment/scripts/*.py` 在決策路徑上零命中（唯二命中在 `backtest_postmortem.py:58-59`，
是解析報告文字的 regex，不參與計算）。§14 validator 也沒有對應的驗算段。

**結論：目前 `WARNING` 與 `VALUE_BONUS` 對倉位零影響。** 唯一真的會動倉位的是
OVERRIDE_BURRY 的 ×0.5。

### 選項

**(i) 實作**——在 chain 插入 `burry_verdict_adj` 段。

- Blast radius（段序被 §14 逐段鎖定，以下**全部**要同批改，否則 validator rc≠0）：
  1. `investment/scripts/trade_plan_builder.py` — chain 函式 `:584-660` 加段 + `:594-595` 段序 docstring + `:653` 輸出鍵
  2. `investment/scripts/validate_session_export.py` — `:489-492` 的 `_chain_step` 串接加一段 + `:83` TRADE_REQUIRED 鍵
  3. `investment/phase5_export_schema.md` — FULL EXAMPLE 的 chain 區塊
  4. `investment/scripts/test_trade_plan_builder.py` — A–Q 全部 spec-parity fixture 的期望值
  5. `investment/scripts/test_session_export_schema.py` — fixture
  6. `investment/scripts/replay_trade_plan.py` — 反解要把新乘數除出去，否則 `sizing` cohort 全掛
  7. `investment/investment_protocol_v5_0.md` — 表 + chain 規格段
  8. `skills/short-contrarian-analyst/SKILL.md`
  9. history.json 既有 174 筆的 replay 基線要重新解釋（現行 `current-rule mismatched = 0` 會變動）
- 額外風險：×1.15 是**唯一會放大倉位的乘數**，其餘全是縮減。它與 Consensus Bonus ×1.15
  （`investment/README.md:207`）可能疊乘，複合後 1.32×——需要先決定是否互斥。

**(ii) 刪文件**——protocol `:711`/`:713` 與 SKILL.md `:48-49` 改為「不影響倉位，僅
narrative」。

- Blast radius：2 檔 4 行。零程式碼變更，零 replay 影響。

**(iii) 不做**——保留現狀。

- Blast radius：0。代價是文件繼續教錯，下一個讀 protocol 的 agent（人或模型）會以為
  倉位已經被乘過。

### Shadow 證據

不適用（此項是「文件與現實是否一致」，不是數值選擇）。可量化的只有一點：`grep` 顯示
`burry_override_adj` 出現在 6 個非 archive 檔案，實作方向要同步的就是這一組加 replay。

### 建議

**(ii) 刪文件。** 理由：這兩個乘數從 V4.7 寫下起就沒有實作，期間累積 174 筆歷史交易，
沒有一筆的倉位反映過它——補實作不是「修好一個 bug」，而是**今天開始改變倉位規則**，
而這個規則從未被任何回測或 replay 驗證過。要引入應該當作新提案走 B1 那種 shadow 流程，
不該以「文件早就寫了」當正當性。

---

## B4 — 三支遷 `skills/_shared/technical_core.py`

### 現況

三支直打 `yf.Ticker(...).history(auto_adjust=True)`，繞過 canonical 價格源
`technical_core.fetch_history()`（FMP `/stable/historical-price-eod/full` 主源，
yfinance fallback）與 `fmp_pool` 的共享限流。專案慣例是走 technical_core。

**但 `technical_core.py:86-90` 自己留了一段註解**：FMP 的 close 是 split-adjusted
**但非 dividend-adjusted**，yfinance `auto_adjust=True` 是 dividend-adjusted；該註解
明確把適用範圍限定在「RSI/MA/MACD 型態辨識」，並說差異「不影響技術訊號」。

**tail-risk 不是型態辨識，是報酬分布統計。** 未做除息調整的序列在每個除息日會出現一個
**假的負報酬**——配息股一年四次、債券 ETF 每月一次，直接污染 max drawdown、下行標準差、
負偏態與峰度，而這四者佔 tail_risk 權重的 65%（vol 35% + dd 30%）。

### 選項

**(i) 不遷**——維持 yfinance。Blast radius：0。代價：三支繼續繞過共享限流（實務上每次
protocol run 各呼叫 1-2 次，非熱點）。

**(ii) 遷移 + 接受漂移**——直接換源。Blast radius：三支 script + 分級帶邊的歷史不可比 +
replay cohort 需重新基線。

**(iii) 遷移但要求 dividend-adjusted 源**——先確認 FMP 是否提供調整後序列（本輪未驗），
或在 technical_core 加除息還原。Blast radius：technical_core（**共用模組，會影響
technical-analyst 等既有 consumer**）+ 三支 + 全部下游重驗。

**(iv) 只遷 portfolio-risk-manager**——它只用 close 算 vol 與相關性，除息造成的假跌對
**相關性**影響小、對 vol 影響小於對 drawdown 的影響。tail-risk 與 burry 不遷。

### Shadow 證據（2026-08-08 實跑，16 ticker，兩源平行算 tail_risk 全部指標）

```
grp   tkr    bars y/f   vol y→f       dd y→f         skew y→f      score y→f    label
div   KO     250/254    18.62→18.67   7.87→8.5       0.69→0.66     19.6→20.0    ROBUST
div   JNJ    250/254    18.3→18.25    10.96→10.96    0.14→0.14     20.8→20.8    ROBUST
div   PG     250/254    19.73→19.5    15.52→16.15    0.12→0.11     24.0→24.3    ROBUST
div   XOM    250/254    25.09→24.91   20.11→20.65   -0.31→-0.33    32.8→33.1    MODERATE
div   T      250/254    25.0→24.92    28.89→30.86    0.03→0.05     37.1→38.2    MODERATE
div   VZ     250/254    24.96→25.11   17.05→18.28    1.52→1.46     38.2→39.1    MODERATE
div   MO     250/254    25.04→25.28   16.4→19.15    -1.1→-1.09     38.1→40.0    MODERATE
div   PFE    250/254    23.28→24.32   15.72→17.09    0.65→0.64     29.1→30.6    ROBUST ⚠FLIP→MODERATE
nodiv NVDA   250/254    36.67→36.41   20.21→20.22    0.06→0.05     40.0→39.9    MODERATE
nodiv TSLA   250/254    46.41→46.24   39.1→39.1     -0.33→-0.35    60.9→60.8    FRAGILE
nodiv AMZN   250/254    34.45→34.41   21.74→21.74    1.57→1.54     46.0→45.8    MODERATE
nodiv GOOGL  250/254    32.58→32.41   21.05→21.09    0.82→0.81     38.1→38.0    MODERATE
nodiv COIN   250/254    67.95→67.77   63.57→63.57    0.52→0.51     81.1→81.1    FRAGILE
etf   SPY    250/254    12.89→12.84   8.88→9.13     -0.21→-0.22    17.0→17.2    ROBUST
etf   XLK    250/254    25.99→25.82   15.92→16.16   -0.17→-0.18    30.6→30.7    MODERATE
etf   TLT    250/254    9.27→9.46     7.74→10.72    -0.05→-0.07    12.1→14.2    ROBUST
```

**label 翻轉 1/16** — PFE `ROBUST → MODERATE`（score 29.1 → 30.6，跨過 30 帶邊）。
**開工表訂的閘門是「0 翻轉才可視為 A 級安全遷移」→ FAIL。**

漂移方向與預測完全一致，且**只出現在有配息的標的**：

| 群組 | max drawdown 平均差 | 最大差 |
|---|---|---|
| 配息股 (8) | **+1.140** | +2.750 (MO) |
| ETF (3) | **+1.157** | **+2.980 (TLT)** |
| 無配息 (5) | **+0.010** | +0.040 |

TLT 最刺眼：drawdown `7.74 → 10.72`（相對放大 38%），因為它每月配息。無配息股的
drawdown 差幾乎是 0，證明漂移來源就是除息而非隨機噪音。

第二個獨立漂移源：**bar 數 250 vs 254**——同樣傳 `period="1y"`，兩源回不同長度。

### 建議

**(i) 不遷。** 理由：閘門明訂零翻轉，實測翻了；而且漂移不是噪音，是一個
**有方向、可解釋、對配息標的系統性偏高**的偏誤——它會讓所有配息股與債券 ETF 看起來比
實際更脆弱，正好是防禦性配置最常出現的那一類標的。若之後仍要遷，走選項 (iii) 先解決
除息調整，且必須連 `technical-analyst` 等既有 consumer 一起重驗。

---

## B3 — sector 端 `EXTREMELY_FRAGILE` 死規則

### 現況

`sector/phase_4-5.md:310-316` STEP D：

```
IF fragility_label = EXTREMELY_FRAGILE:  → DOWNGRADE: HOT → WARM
ELIF (fragility_label = FRAGILE AND extreme_sentiment_triggered): → DOWNGRADE
```

`sector/schema.md:289` 與 `:487` 的 enum 是
`ANTIFRAGILE | RESILIENT | FRAGILE | EXTREMELY FRAGILE`（`:487` 另有 `N/A`）。

**而 `tail_risk.py` 只輸出 `ROBUST | MODERATE | FRAGILE`。** 落差不只是「5 值 vs 3 值」，
是**兩套完全不同的字彙**——sector 的 `ANTIFRAGILE`/`RESILIENT` 在 script 裡不存在，
script 的 `ROBUST`/`MODERATE` 在 sector schema 裡也不存在。唯一交集是 `FRAGILE`。

後果：STEP D 第一條分支**永不觸發**；第二條（FRAGILE + extreme sentiment）是唯一活的。

附帶兩處拼寫不一致：STEP D 寫 `EXTREMELY_FRAGILE`（底線），schema 寫
`EXTREMELY FRAGILE`（空格）。

歷史殘留可證：`replay_trade_plan.py` 的 sizing cohort 排除了
`unusable_fragility_label:RESILIENT` 4 筆、`MEDIUM` 2 筆——這些就是舊字彙寫進 history 的產物。

### 選項

**(i) sector 文件收斂為 3 值**——schema enum 改
`ROBUST | MODERATE | FRAGILE | N/A`，STEP D 第一條改以 `FRAGILE` 觸發（或刪除第一條，
保留 FRAGILE + extreme sentiment 的複合條件）。

- Blast radius：`sector/schema.md`（2 行）、`sector/phase_4-5.md`（STEP D 段）、
  `sector/phase_1-2-3.md:207` 的 `tail_risk < 40`（見 B7）。
  `sector/scripts/validate_sector_intel.py` **完全不驗這些欄位**（已確認），所以無 validator 變更。
- 副作用：降級規則會變得**更容易觸發**（FRAGILE 比 EXTREMELY_FRAGILE 寬），HOT→WARM
  的降級數會上升。需決定是否同時收緊複合條件。

**(ii) script 加 sector 模式輸出 5 級**——`tail_risk.py --sector-mode` 額外輸出五值標籤。

- Blast radius：`tail_risk.py` + SKILL.md + 五值到三值的映射表要新訂（等於新增一組
  未經校準的門檻）+ §14b enum gate 要確認不會被 sector 產物污染。
- 風險：投資端與產業端從此有兩套字彙，是現在這個 bug 的成因本身。

**(iii) 不做**——STEP D 第一條繼續是死碼。Blast radius：0。

### Shadow 證據

開工表要求「對 top-3 HOT proxy ETF 實跑，看五級制下是否真的會出現 EXTREMELY_FRAGILE」。
本輪實跑的 ETF（SPY 17.0 / XLK 30.6 / TLT 12.1）全部落在 ROBUST-MODERATE，
16 檔全樣本中只有 TSLA 60.9 與 COIN 81.1 進 FRAGILE。**產業 proxy ETF 因為天然分散，
分數結構性偏低**——即使真的做出五級制，最高那級對 proxy ETF 幾乎不可能觸發。這反過來
支持選項 (i)：五值制對 sector 的實際用途是空的。

### 建議

**(i) sector 文件收斂為 3 值**，且 STEP D 第一條直接刪除（不是改成 FRAGILE 觸發），
保留第二條複合條件。理由：script 的三值是 protocol 唯一在用的字彙；把 EXTREMELY_FRAGILE
改成 FRAGILE 單獨觸發會**放寬**降級門檻，那是語意變更而非修 bug，不該混在對齊裡做。

---

## B1 — vol-scaling 失能（20% ceiling 恆綁）

### 現況

`risk_manager.py:106-107`：

```python
raw_cap = (vol_budget / daily_vol * 100) if daily_vol > 0 else 0.0
raw_cap = float(min(raw_cap, 20.0))   # hard cap 20% regardless
```

預設 `vol_budget = 0.6`（%/日）。解 `0.6 / daily_vol × 100 ≥ 20` 得 **daily_vol ≤ 3.0%**
（≈48% 年化）就頂到 20。這涵蓋幾乎所有正常股票——NVDA 年化 38.6% 仍然輸出 20.0。

實務後果：Step 2 的 `final_position_cap_pct = raw_cap × corr_mult (× 0.5)`，raw_cap 恆為
20 時，**唯一活的差異化只剩相關性乘數**（四檔）與 sector cap（二值），共 8 種可能值。

### Shadow 證據（history.json 反解，n=47）

用 `replay_trade_plan.replay_sizing()` 對 174 筆歷史交易反解 implied Step 2 base
（47 筆可解，其餘因零倉位／binary 事件／舊字彙標籤被排除）：

- min / median / max = **0.0040 / 0.1144 / 0.1957**
- 若 raw_cap 恆為 20（天花板綁定），base 只能落在
  `20 × {1.0, .85, .70, .55} × {1, 0.5} / 100` 這 **8 個格點**：
  `0.055 0.07 0.085 0.10 0.11 0.14 0.17 0.20`

**格點命中率對容差高度敏感，必須連容差一起讀：**

| 容差 | 命中 | 說明 |
|---|---|---|
| ±0.0005 | **13/47 = 28%** | 真正「精確落點」 |
| ±0.001 | 14/47 = 30% | |
| ±0.005 | 33/47 = 70% | 但 8 個 bin × 0.01 寬 = 0.08，**覆蓋了觀測區間 [0.004, 0.196] 的 42%**——這個數字是支持性的，不是決定性的 |

**決定性的證據是精確簇，不是總命中率**：3 位小數下 `0.140` 出現 **8 次**（= 20 × 0.70，
相關性 0.6-0.8 帶），`0.100` 2 次、`0.070` 2 次亦在格點上。同一個值重複 8 次不可能來自
連續的 vol 計算——只能來自一個被天花板釘死的常數乘上離散的相關性檔位。

**分布頂端反而顯示 vol 曾經邊際參與過**：

| implied base | 筆數 | 隱含 raw_cap | 隱含 daily_vol |
|---|---|---|---|
| 0.1955–0.1957 | 4（AIZ、TSM ×3） | 19.55–19.57 | 3.065–3.070% |
| 0.1778 | 2（TSM） | 17.78 | 3.375% |
| 0.1680 | 2（GOOGL、NTRS） | 16.80 | 3.571% |

這些值一致地**低於**格點 0.20，且只能用 `corr_mult = 1.00` 配 `raw_cap < 20` 解釋
（除以 0.85 會得到 > 0.20，不可能）。對應的 daily_vol 全部落在 **3.07%–3.57%** 這條
窄帶上——正是 `0.6 / daily_vol × 100 = 20` 的斷點（daily_vol = 3.0%）**剛過去**的那一側。
（`0.1680` 距格點 0.17 只有 0.002，也可能是反解捨入漂移，歸屬不確定。）

### 修正後的結論

不能說「vol 從未參與過任何一筆」。準確的說法是：

> **最多約 6–8 筆（涉及 3–4 個 ticker）在天花板邊緣有過邊際參與，cap 偏離 20 不超過
> 3.2 個百分點；其餘全部頂死在 20，倉位差異化完全來自相關性乘數與 sector cap。**

P1 的實質仍然成立——vol-scaling 的作用域被壓縮到 daily_vol 3.0%–3.6% 這條窄縫裡，
而縫外（絕大多數正常股票）它完全不作用。這反而**更支持**建議 (iii)：問題不是
「vol 完全沒接上」，是「它只在一條看不見的窄縫裡作用」，那更需要先讓它可觀測。

（其餘 off-lattice 筆數推測來自 PM 判斷覆寫或反解時未能整除的其他段，本輪未逐筆歸因。）

### 選項

**(i) 降 vol-budget 讓 cap 有分布**——例如 0.6 → 0.25（daily_vol ≤ 1.25% 才頂到 20）。

- Blast radius：`risk_manager.py` 預設值一行 + SKILL.md。但**倉位會全面縮小**：
  NVDA daily_vol 2.43% → cap 從 20 降到 10.3，腰斬。
- 需要對 47 筆 cohort 重算並逐筆解釋倉位變化，才知道是否可接受。

**(ii) 改用上游 position-sizer 的 ATR / stop-distance sizing**
（`tradermonty/claude-trading-skills` 的 `skills/position-sizer/scripts/position_sizer.py`，
fixed-fractional / ATR-based / Kelly 三法 + `apply_constraints` + 整股 floor）。

- Blast radius：最大。等於換掉 Step 2 的演算法，Step 2 輸出 shape 要重訂，
  `trade_plan_builder.compute_step2` 與 §14 反解全部要動，history 全部不可比。

**(iii) ceiling 參數化交使用者**——`--max-cap` 參數，預設仍 20.0。

- Blast radius：`risk_manager.py` 加參數 + SKILL.md。**預設不變 → 零行為變更、零 replay 影響。**
- 效果：讓「20% 是不是對的」變成可以被實驗的問題，而不是寫死的常數。

**(iv) 不做**——Blast radius：0。代價：Step 2 名為 vol-adjusted、實為 correlation-adjusted。

### 建議

**(iii) ceiling 參數化 + 預設不變**，並在 SKILL.md 記錄上面那張格點表與窄縫現象。
理由：現在就改數值等於在**沒有基線**的情況下動全部倉位——上面的 shadow 證明的是
「vol 的作用域被壓縮到 daily_vol 3.0%–3.6% 這條窄縫」，**沒有**證明「把縫開大之後會更好」。
先讓 ceiling 可觀測、可實驗（同一批 47 筆可以在不同 ceiling 下重解，直接看倉位分布怎麼變），
等有對照再談改預設。選項 (ii) 是真正的答案但屬於重寫 Step 2，應獨立立案。

---

## B7 — normalizer 再校準 + sector off-band 門檻對齊

### 現況

`tail_risk.py:65-69` 的 normalizer 標註「Calibrated 2026-04 against
SPY/TLT/NVDA/TSLA/COIN/RIVN/BTC-USD」，至今四個月未動。

另外 sector 端有兩個**不在 30/60 分級帶上**的門檻：
- `sector/phase_1-2-3.md:207`：`IF (COLD AND uptrend_ratio > 0.5 AND tail_risk < 40)`
- `sector/phase_4-5.md:268`：`tail_risk_score > 70 OR excess_kurtosis > 5 → fat_tail_warning`

`< 40` 落在 MODERATE 帶中間、`> 70` 落在 FRAGILE 帶中間，兩者都無法用分級語言解釋。

### Shadow 證據（2026-08-08，16 ticker 現行 normalizer 的實際分布）

| 帶 | n | 標的 |
|---|---|---|
| ROBUST (<30) | 6 | TLT 12.1、SPY 17.0、KO 19.6、JNJ 20.8、PG 24.0、PFE 29.1 |
| MODERATE (30-60) | 8 | XLK 30.6、XOM 32.8、T 37.1、MO 38.1、GOOGL 38.1、VZ 38.2、NVDA 40.0、AMZN 46.0 |
| FRAGILE (≥60) | 2 | TSLA 60.9、COIN 81.1 |

**分布是健康的**：三帶都有樣本、沒有堆在單一帶、排序符合直覺（債券 ETF 最低、
迷因/加密相關最高、大型科技居中）。**沒有證據顯示 2026-04 校準已經失效。**

值得注意的邊界案例：TSLA 60.9 只比 FRAGILE 門檻高 0.9，NVDA 40.0 在 MODERATE 正中。

對照 sector 的 off-band 門檻：`< 40` 會把上表 6 個 ROBUST 全收、外加 XLK/XOM/T/MO/GOOGL/VZ
六個 MODERATE，共 12/16 —— 它其實是一條「非極端即可」的寬門檻，語意上接近
「ROBUST 或 MODERATE 前段」。`> 70` 則只有 COIN 一檔命中。

### 選項

**(i) 只修 sector off-band 門檻對齊，不動 normalizer**——`< 40` → `≤ MODERATE`（即 `< 60`）
或明寫 `< 30`（ROBUST）依語意決定；`> 70` → `FRAGILE`（`≥ 60`）。

- Blast radius：`sector/phase_1-2-3.md` 1 行 + `sector/phase_4-5.md` 1 行。零程式碼。
- 需要使用者決定語意：`< 40` 原意是「不夠脆弱到需要排除」還是「相當穩健」？

**(ii) 重新校準 normalizer**——調整 `:65-69` 的五個係數。

- Blast radius：`tail_risk.py` + 全部歷史 label 不可比 + replay 基線 + SKILL.md 的
  normalizer 表 + 下游三處鏡像表（若同時動門檻）。
- 前提：需要先有「現行校準哪裡不對」的證據，本輪沒有找到。

**(iii) 不做**——Blast radius：0。

### 建議

**(i) 只修門檻對齊，不動 normalizer。** 理由：normalizer 的問題是被假設的，實測分布
6/8/2 反證了它；而 off-band 門檻是**確定的**不一致——同一個分數在 investment 端叫
MODERATE、在 sector 端卻用一條看不出出處的 40 來判。先修確定的，別動沒壞的。

順帶：`downside_deviation` 在視窗內只有一天負報酬時 `neg.std()` 回 NaN，`json.dumps`
會輸出非嚴格 JSON 的 `NaN` 字面值（V4.111.7 review 發現，既有問題）。目前無 consumer
讀這欄故無實害；本項若動手，順手改 `len(neg) < 2 → 0.0`。

---

## B5 — insider 換 `skills/_shared/fmp_supplementary.py`

### 現況

`burry_score.py:54-73` 的 `get_insider_net()` 把 yfinance 的 `insider_transactions`
DataFrame 每列攤平成字串，用 `"buy"/"purchase"` 與 `"sale"/"sell"` 做子字串比對數次數，
`buys > sells×1.5 → BUY`、`sells > buys×1.5 → SELL`、否則 `NEUTRAL`，例外 → `UNKNOWN`
（renorm 掉）。極脆弱但 fail-safe。

`fmp_supplementary._fetch_insider_summary()` 走 `/stable/insider-trading/statistics`，
回季度 `acquiredDisposedRatio`，並以 `≥1.0 → accumulating / <0.5 → distributing /
其餘 neutral` 定 `latest_trend`。有 24h cache。

### Shadow 證據（2026-08-08，12 ticker 兩法對照）

| tkr | yfinance sniff | FMP stats | trend | A/D ratio | 一致 |
|---|---|---|---|---|---|
| KO | SELL | NEUTRAL | neutral | 0.533 | ✗ |
| JNJ | SELL | SELL | distributing | 0.375 | ✓ |
| PG | NEUTRAL | SELL | distributing | 0.000 | ✗ |
| XOM | SELL | SELL | distributing | 0.000 | ✓ |
| NVDA | NEUTRAL | SELL | distributing | 0.000 | ✗ |
| TSLA | SELL | SELL | distributing | 0.200 | ✓ |
| AMZN | SELL | SELL | distributing | 0.000 | ✓ |
| GOOGL | SELL | SELL | distributing | 0.000 | ✓ |
| COIN | SELL | SELL | distributing | 0.000 | ✓ |
| PFE | NEUTRAL | SELL | distributing | 0.000 | ✗ |
| MSFT | SELL | SELL | distributing | 0.000 | ✓ |
| AAPL | SELL | SELL | distributing | 0.175 | ✓ |

**一致率 8/12 = 67%**；yfinance 側 0/12 回 UNKNOWN（本輪抓取都成功）。

**比一致率更重要的發現：FMP 對 12 檔判了 10 檔 `distributing`**，其中 8 檔
`acquired_disposed_ratio = 0.000`。這不是資料錯誤，是結構性事實——大型股內部人賣出多半是
RSU 既得的機械性行為，買進才是裁量性的。直接把 `distributing → SELL(20分)` 映射，
會讓 insider 元件對幾乎每一檔大型股都輸出 20：**它會從一個有噪音的訊號變成一個沒有訊號
的常數偏移**（權重 10%，等於把所有大型股的 Burry Score 壓低約 2-3 分）。

現行 yfinance 法雖然粗糙，至少產生了 SELL/NEUTRAL 的分化（8 SELL / 4 NEUTRAL）。

### 選項

**(i) 不換**——Blast radius：0。代價：繼續依賴 string-sniffing，yfinance 一改欄位就
全部退化成 UNKNOWN（但 fail-safe，會 renorm 掉）。

**(ii) 換，且沿用現行映射**——Blast radius：`burry_score.py` + SKILL.md + frontmatter
資料源（會重新變成真的有 FMP）+ 三支測試。**不建議**，理由見上。

**(iii) 換，但改映射為相對基準**——例如與該股自身前 4 季 ratio 的中位數比較，或與同業
中位數比較，讓「比平常更賣」才算 SELL。Blast radius：同 (ii) 再加一組新門檻需要校準。

### 建議

**(i) 不換**，或若要換則走 **(iii)** 並先出一份門檻校準 shadow。理由：換資料源的目的
是提高訊號品質，而實測顯示直接換會**降低**——把一個 10% 權重的元件變成常數，等於
悄悄把 Burry Score 的有效權重從五元件降到四元件，還多付了一次 FMP 呼叫。

---

## B6 — drawdown-circuit-breaker（帳戶層）

### 現況

概念來自上游 `skills/drawdown-circuit-breaker/scripts/check_circuit_breaker.py`：
`TRADING_ALLOWED / COOLDOWN / HALTED` 三態，依日／週／月虧損門檻（帳戶 %）與連敗次數
決定「今天可否開新倉」。本 repo 無對應機制。

**開工表原文說「需先解決 realized P&L 資料源（positions.json 只有現況）」——這句是錯的。**
實查 `positions.json` 的欄位含 `realized_pl` / `exit_price` / `exit_date` /
`closed_shares` / `status`，資料源存在。

**但帳本本身撐不起這個機制**：

| 事實 | 值 |
|---|---|
| 部位總數 | 8（closed 7 / open 1） |
| 有 `realized_pl` 的 | 7 |
| 其中虧損筆數 | **0**（+111.4 / +1324 / +351 / +750 / +735 / +782.5 / +243.5） |
| 出場日期範圍 | 全部在 2026-04-17 ~ 2026-04-24 |

七筆全是獲利、全部集中在四個月前的同一週。**連敗冷卻與週／月虧損門檻在這份帳本上
永遠不會觸發，也無從校準**——沒有任何一個門檻值能用歷史資料證明合理。

### 選項

**(i) 寫設計文檔，不接線**——定義三態、門檻參數、資料契約、接入點（Phase 4 之前的
gate），但不實作。Blast radius：新增 1 份 docs。

**(ii) 實作 + 用保守預設接線**——Blast radius：新 skill + protocol 新增一個前置 gate +
Phase 4 流程變更 + validator。且門檻是憑空訂的。

**(iii) 不做**——Blast radius：0。

### 建議

**(i) 寫設計文檔，不接線。** 理由：機制本身合理，缺的是校準資料——七筆全贏的帳本連
「一次正常回檔長什麼樣」都沒有。先把設計與資料契約定下來（尤其是**要求 positions.json
的關倉紀錄持續累積**），等帳本有足夠樣本再談接線。現在接等於用猜出來的門檻去否決真實交易。

---

## 附錄 — 本輪 shadow 腳本

兩支一次性對照腳本留在 session scratchpad（非 repo 產物）：
- `b4_shadow.py` — 兩源平行算 tail_risk 全指標，計 label 翻轉與分群漂移
- `b5_shadow.py` — yfinance sniff vs FMP insider statistics 一致率

B1 的格點反解直接呼叫 `replay_trade_plan.replay_sizing()`，無獨立腳本。
若要重跑，三者都只依賴 repo 內既有模組，無額外相依。

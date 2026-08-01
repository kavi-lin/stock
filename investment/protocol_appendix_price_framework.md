# Price Framework Spec Appendix（V4.0.0 自 protocol 外移）

> **角色**：本檔是 Phase 2.4 `compute_price_framework.py` engine 內含邏輯的 **spec 文件（audit 用）**。
> **實作以 engine script + `test_compute_price_framework.py` golden fixtures 為準** — 本檔與 engine
> 不一致時以 engine 為準並回修本檔。PM 執行 `分析` **不需要讀本檔**（protocol Phase 4.5 摘要已足）。
> 外移動機：V3.45.x–3.46.x 累積 366 行演算法 spec，PM 每跑一次全讀 = 純 token 浪費。

## PHASE 4.5 — MULTI-HORIZON PRICE FRAMEWORK (V5.1 — 升級自 V5.0 fair_value_summary)

**V3.45.3 起：全部數字由 Phase 2.4 `compute_price_framework.py` 算出，本 Phase 只封裝呈現。**
**禁止 LLM 手算/重算任何 framework 數字** — V3.45.x 累積的數學（weighted percentile、CV、reverse DCF
迭代解）超出 LLM inline 可靠範圍，engine script 是唯一計算來源。PM verbatim 抄寫 engine 輸出。
以下演算法區塊為 **spec 文件**（記載 engine 內含邏輯供 audit），實作以 script 為準。

> **V5.1 升級**：原單一 `fair_value_summary`（長期 6-anchor）擴展成三時間框架。
> 每層用該時間尺度合適的方法：5 天用波動率機率帶，60 天用動能+重定價，長期用估值錨點。
> **契約相容**：`fair_value_summary` 保留為 `valuation_pack` projection（仍受 decision_lock + validator 保護）；
> engine 只 build 一次，validator 強制 projection 數值相等。三框架另存於 sibling block `multi_horizon_price_framework`，
> 長期層**直接引用** `fair_value_summary.weighted_fair_value`，不複製不重算。

### 4.5.0 — Long-Term Layer：canonical `valuation_pack`

### 算法

```python
anchors = deterministic_sources_with_provenance
eligible = apply_model_predicates_and_freshness(anchors)

# 同 correlation group 先 median，一 group 一票；再得到 family representative。
# correlation group 由固定 anchor-type mapping + assumption/input lineage 產生，LLM 不可指定。
families = {
  "fundamental": ["cashflow_intrinsic", "earnings_projection"],
  "relative": ["peer_relative"],
  "external_expectations": ["external_pt"],
}
family_weights = {"fundamental": 0.55, "relative": 0.25, "external_expectations": 0.20}
weighted_fair_value = aggregate_eligible_family_representatives(eligible, family_weights)
# 三 family 齊全才用 fixed weights；只剩 1/2 family 時改為 equal family votes，
# 不把缺失 family 的權重指定轉移給某個 survivor，並壓低 confidence。
if eligible_dcf_self_built.projection_mode == "structural_shift_through_cycle":
    family_blended_fair_value = weighted_fair_value       # audit/scenario only
    weighted_fair_value = eligible_dcf_self_built.value   # primary FV
    aggregation_mode = "dcf_primary_anchor_range"
vs_current_pct = (weighted_fair_value - current_price) / current_price * 100

# Verdict band
if vs_current_pct >= 30:   verdict_band = "extreme_undervalued"
elif vs_current_pct >= 10: verdict_band = "undervalued"
elif vs_current_pct >= -10: verdict_band = "fairly_valued"
elif vs_current_pct >= -30: verdict_band = "overvalued"
else:                       verdict_band = "extreme_overvalued"

# Confidence by independent family coverage；不是 anchor count。
if len(families_present) == 3: confidence = "high"
elif len(families_present) == 2: confidence = "medium"
else: confidence = "low"

# 少於 2 個獨立 family，或同方向 family vote 少於 2，禁止 |score| >= 2。
```

Eligibility 先於聚合：LOW forecaster、transition 無安全模型、<3 business-similar peers、
負 terminal FCFF、缺 provenance/as_of、PT 超過 180 天，或 PT 早於 confirmed structural-shift evidence date，
一律保留 value/reason 供 shadow audit，但不得進 live FV。Reverse DCF 是 market-implied diagnostic，永不投票。
`--self-assemble` 的八個 live anchor 由 engine 擁有；input file 同名 value/meta 會被清除並列入
`blocked_anchor_overrides[]`，不能以 LLM 或手工 metadata 偽裝成 deterministic source。
當 eligible `dcf_self_built` 使用 `structural_shift_through_cycle` 模式時，來源不透明且與其同屬
cash-flow intrinsic 的 vendor `dcf_unlevered` / `dcf_levered` 保留 value/lineage 但標記
`superseded_by_auditable_through_cycle_dcf`，不得重複投票。若自建模型失敗或仍是 legacy mode，
vendor DCF 不會因此被壓掉。

`peer_cohorts.json` 只保存經人工核准的候選 ticker/角色/限制，不保存倍數。候選可由 LLM
協助 discovery，但 `peer_cohorts.py` 必須重新由 deterministic ratio adapter 取數、取得 ≥3 個
正 P/E 才輸出 `scope=range_only` scenario。此 scenario 不得填入 live `peer_pe_implied` 或
`comps_implied`；只進 `valuation_explained_range`。該 block 以 DCF 為 primary，另列 DCF
sensitivity、without-peer、with-peer 與其他 eligible anchor，並記錄 range_low/high 的實際 driver。

### 輸出

```json
{
  "phase": "4.5",
  "agent": "Portfolio_Manager",
  "fair_value_summary": {
    "anchors": {
      "dcf_unlevered":        "float|null",
      "dcf_levered":          "float|null",
      "analyst_pt_consensus": "float|null",
      "peer_pe_implied":      "float|null",
      "owner_earnings_mult":  "float|null",
      "forecaster_blend":     "float|null"
    },
    "weights_used": {"dcf_unlevered": 0.18, ...},  // pack projection
    "weighted_fair_value":  "float",
    "current_price":        "float",
    "vs_current_pct":       "float",
    "verdict_band":         "extreme_undervalued | undervalued | fairly_valued | overvalued | extreme_overvalued",
    "confidence":           "high | medium | low（按獨立 family coverage + dispersion cap）",
    "anchors_available":    "int 0-8",
    "families_present":     ["fundamental", "relative"],
    "excluded_anchors":     {"forecaster_blend": "low_forecast_confidence"},
    "valuation_pack_schema": "valuation_pack.v1",
    "methodology_note":     "string"
  }
}
```

### 與 Valuation lane 的關係
- `valuation_pack` 給唯一 FV / score / confidence。
- Valuation Specialist 只 reviewer/explainer；lane 數值欄只能 verbatim projection。
- `fair_value_summary`、MHP long-term、T5、det-shadow 全部只讀同一 pack，禁止重算。

### 4.5.0b — Anchor Distribution：`fair_value_range`（V3.45.1 NEW，advisory sibling）

**動機**：加權平均把 anchor **分歧銷毀**了 — DCF $155 / PT $325 平均成 $215，沒有任何模型相信這數字。分歧本身是最重要的資訊。改輸出 anchor 分布**區間**，下游 conservative entry 貼 P25 而非貼平均。

> **契約鐵律**：`fair_value_summary`（含 `weighted_fair_value` / `verdict_band` / `confidence`）**整塊 byte-for-byte 不動** — 受 11-field decision_lock + validator + apply_det_shadow `val_det` 鎖死。本層全部欄位**另存 sibling block `fair_value_range`**，**不**進 decision_lock。`weighted_fair_value` 仍是決策數字唯一來源；`fair_value_range` 純 advisory 呈現。

```python
anchors_list = [v for v in available.values()]            # 既有 available（缺 anchor 已濾）
weights_list = [weights_norm[k] for k in available]
n = len(anchors_list)

# 退化行為（review point 4）
if n >= 4:
    range_method = "weighted_percentile"
    p25 = weighted_percentile(anchors_list, weights_list, 0.25)
    p50 = weighted_percentile(anchors_list, weights_list, 0.50)
    p75 = weighted_percentile(anchors_list, weights_list, 0.75)
elif n >= 2:
    range_method = "minmax_fallback"                      # n=2,3 → percentile 無統計意義
    p25, p50, p75 = min(anchors_list), median(anchors_list), max(anchors_list)
else:
    range_method = None                                   # n<2 → 整組 null
    p25 = p50 = p75 = None

min_anchor, max_anchor = (min(anchors_list), max(anchors_list)) if n else (None, None)

# 位置判定（獨立欄位 range_verdict，不碰 fair_value_summary.verdict_band）
if p25 is None:                          range_verdict = None
elif current_price > max_anchor:         range_verdict = "extreme_overvalued"   # 連最樂觀的錨都說貴
elif current_price < min_anchor:         range_verdict = "extreme_undervalued"
elif current_price > p75:                range_verdict = "overvalued_zone"
elif current_price < p25:                range_verdict = "undervalued_zone"
else:                                    range_verdict = "fair_zone"

# 分歧度（review point 3 — 純展示，3.45.1 不接 Phase 4.6 cap；接線留 P2）
if n >= 2:
    wmean = weighted_mean(anchors_list, weights_list)
    wstd  = weighted_std(anchors_list, weights_list)
    anchor_dispersion_cv = wstd / wmean if wmean else None
    # V4.72.1 — 門檻改歷史 33/66 percentile（0.375/0.52，user 核准）；原 0.15/0.35 初值
    # 把 28/30 session 判 low，標籤無鑑別度
    agreement_grade = ("high" if anchor_dispersion_cv < 0.375    # cv 小 = 錨一致 = 高同意度
                       else "medium" if anchor_dispersion_cv < 0.52 else "low")
else:
    anchor_dispersion_cv, agreement_grade = None, None

# Owner-earnings 倍數 shadow（review point 2 — option a；live anchor 仍用 static ×15 不變）
oe = anchors.get("owner_earnings_mult")                   # 既有 anchor 值（static ×15 算出）
required_yield = phase0.fred.treasury_10y_real + 0.04     # FRED real 10Y + ERP 0.04
oe_mult_rate_linked = clamp(1.0 / required_yield, 10, 22) if required_yield else None
# 僅 shadow-log，不回寫 anchors / weighted_fair_value
```

> **B3 常數註記（V3.45.3）**：本處 earnings-yield premium 用 **real 10Y + 0.04**（owner earnings 隨通膨成長，
> 以實質利率為基底、premium 不含通膨補償成分）；reverse DCF 的 WACC 用 **nominal 10Y + ERP 0.045**
> （折現名目 FCF）。兩組常數**用途不同非筆誤**，集中定義在 `compute_price_framework.py` 頂部
> （`ERP_EARNINGS_YIELD` / `ERP_WACC`），改值只改 script 一處。

> **agreement_grade 門檻已校準（V4.72.1，user 核准 2026-07-16）**：0.15/0.35 初值 → **0.375/0.52**
> （SHADOW_REPORT_2026-07-16 n=67 的 33/66 percentile；歷史分級從 28/30 low → 4 high / 6 medium / 20 low）。
> ⚠ **再校準檢查點**：此校準基於修剪前 anchors；P0-3 trim（V4.70.0）上線後 cv 分佈左移
> （NVDA 例 0.341→0.188），累積 ≥20 筆修剪後 session 由 `shadow_report.py` 重出分佈再議門檻。
> （歷史紀錄：V3.46.1 backfill 37 筆 median=0.46、建議 0.367/0.484，與本次 67 筆結果一致。）
>
> **#6 shadow 退出條件（寫死，避免永久欠債）**：累積 **≥ 20 session** 後，比對「若 live anchor 改用 `oe_mult_rate_linked` 會翻轉 `verdict_band` 的比率」。**翻轉率 < 15% → 出切換提案**（rate-linked 影響小、安全可切）；**≥ 15% → 維持 static 並標記需 backtest 驗證方向性**（影響大、不可盲切）。
>
> **報告讀出端（V3.46.1）**：`python3 investment/scripts/shadow_report.py` — 唯讀，一次算齊
> #2 dispersion backfill / #6 oe 翻轉率 / #3 archetype 翻轉率 / #4 news 分布偏移 + checkpoint 進度，
> 輸出 `reports/SHADOW_REPORT_<date>.md`。所有 shadow 的「≥N session 報告」都由它產。

輸出 sibling block `fair_value_range`（見 schema）。

> **V4.70.0 (P0-3) — outlier 修剪已接線（原「winsorize / outlier 降權留 P2」項）**：
> `trim_anchor_outliers()` 在 `fair_value_summary` / `fair_value_range` 計算**之前**執行——
> n≥4 時錨值落在錨中位數 ×1/3..×3 之外 → 剔除不進加權（剩 <2 錨則放棄修剪）。
> 修剪相對「錨共識」而非現價：全體錨一致偏低（真高估）時中位數同步下移，不誤剪。
> 依據 AUDIT_2026-07-16 F3：NVDA owner_earnings×15 = $31.80（vs 錨中位 $258）以 0.05
> 權重把 fair value 從 $296 拉到 $272 仍標 high confidence。修剪紀錄進
> `fair_value_summary.anchors_trimmed`（raw 值保留於 anchors 欄）。
> dispersion→confidence cap（V4.46.0）與 confidence→Phase 4.6 cap 既有鏈不變——
> 修剪後 cv 仍 ≥0.60 者照樣壓 low → 觸發 decision cap，即 dispersion gate 已閉環。
> `agreement_grade` 本身仍為展示欄（門檻校準議題不變，見上）。

### 4.5.0c — Valuation Archetype Shadow（V3.46.0 NEW，shadow-only）

**動機**：固定 anchor 權重對所有公司一視同仁 — DCF 兩條合計 0.45 對 FCF 負的高成長股是雜訊；
peer_pe 在 EPS ≤ 0 時失效（權重變相塞給 PT）；金融股缺 P/B 維度。原 6-anchor 池對未獲利成長股
與金融股的估值**半殘**。

**紀律**：**live `fair_value_summary` 權重 / anchor 池 / verdict 完全不動**。Engine（Phase 2.4）另輸出
`valuation_archetype_shadow`：deterministic archetype 分類 + 9-anchor 池（6 既有 + 3 新）archetype
權重 shadow blend + `flip_vs_live`。**退出條件**：≥ 20 session 後出翻轉率報告 → user 拍 → #3b 切 live
（cap / T5 接線同步做）。與 #6 oe shadow 同模式。

**Archetype 分類（deterministic，按序首中；門檻為初值，#3b 前校準）**：

| 序 | Archetype | 判定（全部 Phase 1 bundle 既有欄位） |
|---|---|---|
| 1 | `financial` | `snapshot.sector ∈ {Financial Services, Financials}` |
| 2 | `hypergrowth` | `revenue_yoy > 25%` OR `epsTTM ≤ 0` |
| 3 | `cyclical` | sector ∈ {Technology, Energy, Materials, Industrials} AND 8Q 淨利率 σ > 5pp |
| 4 | `mature_cashflow` | `fcf_margin > 8%` AND `revenue_yoy < 15%` |
| 5 | `balanced` | fallback — 權重 = live + 新 anchor 0（shadow==live 自驗） |

**3 新 anchor（engine 算，精確 EV 數學）**：

| Anchor | 算式 | 資料源 |
|---|---|---|
| `peer_ev_ebitda_implied` | `(peer_median × (EV/self_mult) − netDebt) / shares` | PEER_BUNDLE `peer_ev_ebitda_median`（V3.46.0 新欄）+ `self_ratios_ttm` + earnings bundle `enterprise_value` |
| `peer_ev_sales_implied` | 同上以 EV/Sales | 同上 |
| `pb_roe_justified` | `(ROE−g)/(r−g) × BVPS`，`r = 10Y + beta×0.045`、`g=0.025`、justified P/B clamp [0.2,15] | `self_ratios_ttm` + beta + FRED |

**Archetype 權重表**：見 `compute_price_framework.py` `ARCHETYPE_WEIGHTS`（單一事實來源；
hypergrowth 主錨 EV/Sales 0.30 + DCF 壓 0.15 總和；cyclical 壓 peer_pe 0.10（TTM EPS 順週期陷阱）
拉 EV/EBITDA 0.25；financial 主錨 pb_roe 0.35 + DCF/EV 歸零）。

**範疇外（deferred）**：forward EPS 替換 peer_pe TTM、cyclical normalized-earnings anchor、cap/T5 接線（#3b）。

---

### 4.5.1 — Short-Term Layer：5-Day Volatility Band（波動率錨定機率帶）

5 天後股價是個**機率分布**不是一個點。給 80% 信賴帶（含漂移平移）+ key_levels 反射判定。

**輸入**（全部 deterministic，缺料 → confidence 降級不擋）：
```python
# 從 technical_lane.volatility（V5.1 新增；deterministic FMP technicalIndicators read）
sigma_daily = tech.volatility.hist_vol_20d_daily      # 20D 日報酬標準差（小數，e.g. 0.028）
atr_14      = tech.volatility.atr_14                   # 缺 sigma_daily 時反推：sigma_daily ≈ atr_14 / current_price
current_price = ticker_data_bundle["scoring"]["price"]
Z = 1.28                                               # 80% 雙尾（單尾 10/90）
sqrt5 = 5 ** 0.5
```

**Drift（方向偏移，σ 單位）** — 純查表，吃 `pattern_taxonomy` + `smart_money_analysis.label`：
```python
DRIFT_BY_PATTERN = {
  "uptrend_breakout":        +0.30,
  "uptrend_continuation":    +0.20,
  "pullback_in_uptrend":     +0.10,
  "oversold_bounce_attempt": +0.10,
  "consolidation":            0.00,
  "false_breakout":          -0.20,
  "topping_pattern":         -0.30,
  "downtrend":               -0.50,
}
SMART_MONEY_NUDGE = {"accumulating": +0.10, "distributing": -0.10, "mixed": 0.0, "neutral": 0.0}

drift_sigma = DRIFT_BY_PATTERN.get(pattern, 0.0) + SMART_MONEY_NUDGE.get(sm_label, 0.0)
drift_sigma = max(-0.60, min(0.50, drift_sigma))      # clamp
```

**機率帶**（中心隨 drift 平移，帶寬 = ±1.28σ_5d）：
```python
center_ret = drift_sigma * sigma_daily * sqrt5
half_width = Z * sigma_daily * sqrt5

band_lower = current_price * (1 + center_ret - half_width)
band_point = current_price * (1 + center_ret)          # 點估計（drift 平移後）
band_upper = current_price * (1 + center_ret + half_width)
confidence = "high" if sigma_daily else "low"          # 缺 vol 數據 → low
```

**Catalyst override**（5 天內有 binary 事件 → 帶放大 + 信心降一級 + drift 收斂向 0）：
```python
cat = news_lane.immediate_catalyst_5d                   # None 或 {event,date,direction_lean,expected_move_pct}
if cat and cat.get("expected_move_pct"):
    em = cat["expected_move_pct"] / 100.0
    half_width += em                                    # 財報跳空風險疊加
    if cat["direction_lean"] == "NEUTRAL":              # 方向不可預測 → 不押 drift
        center_ret = 0.0
        band_point = current_price
    confidence = "low"                                  # binary 不可預測方向 → 強制降級
    band_lower = current_price * (1 + center_ret - half_width)
    band_upper = current_price * (1 + center_ret + half_width)
```

**Key-level 反射判定**（support/resistance 是真實反射邊界，比純統計帶可信）：
```python
kl = tech.key_levels                                    # {support, resistance, pivot}
# 帶上界穿越 resistance → 標記「上界受 $resistance 壓制」
# 帶下界穿越 support    → 標記「下界受 $support 撐住」
band_lower_capped = max(band_lower, kl["support"])    if kl.get("support")    else band_lower
band_upper_capped = min(band_upper, kl["resistance"]) if kl.get("resistance") else band_upper
key_level_note = "..."                                  # 哪一邊被反射、原始帶 vs capped 帶
```

輸出 `[band_lower, band_point, band_upper]`（含 capped 版）+ confidence + `catalyst_widened` flag + key_level_note。

---

### 4.5.2 — Mid-Term Layer：60-Day Target（動能 + 重定價加權）

```python
# 三個中期錨，加權（缺項重分配）
DECAY_FACTOR = 0.50                                      # 動能半衰；20D 動能延續到 60D 的折減
PULL_FACTOR  = 1.00                                      # 賣方 12m PT 拉力係數

momentum_20d_pct = tech.volatility.momentum_20d_pct     # 20D 報酬 %（V5.1 新增）
analyst_pt       = fair_value_summary.anchors["analyst_pt_consensus"]   # 已有錨，零額外 call
forecaster_blend = fair_value_summary.anchors["forecaster_blend"]       # 已有錨

momentum_target  = current_price * (1 + (momentum_20d_pct/100) * DECAY_FACTOR)
pt_60d           = current_price + (analyst_pt - current_price) * (60/365) * PULL_FACTOR  if analyst_pt else None
# V3.48.0 #8a：forecaster 是長期錨，直接當 60d 成分 = horizon mismatch → 折算 60/250 交易日
earnings_revision = current_price + (forecaster_blend - current_price) * (60/250)  if forecaster_blend else None

# 加權（預設 0.40 / 0.35 / 0.25；缺項把 weight 重分配給其餘）
W = {"momentum": 0.40, "pt_60d": 0.35, "earnings_revision": 0.25}
parts = {"momentum": momentum_target, "pt_60d": pt_60d, "earnings_revision": earnings_revision}
avail = {k: v for k, v in parts.items() if v is not None and v > 0}
wsum  = sum(W[k] for k in avail)
mid_target = sum((W[k]/wsum) * avail[k] for k in avail) if avail else None

# Key-level reality check（不改數字，只加註成立條件）
# mid_target > resistance → "需突破 $resistance 才成立"
# mid_target < support    → "需跌破 $support 才成立"
mid_reality_note = "..."
```

---

### 4.5.3 — Convergence：三框相對位置 → 交易語意

三框架的**相對位置**自動產生 `mhp_signal`（deterministic 規則，按序判定，取第一個命中）：

```python
LT = fair_value_summary["weighted_fair_value"]          # 長期層（引用，不重算）

if band_lower_capped > LT:
    mhp_signal = "wait_for_pullback"        # 短期超漲、長期偏貴 → 等回檔（Technical×Valuation 衝突量化）
elif band_point < LT and mid_target and mid_target > current_price and current_price < LT * 0.9:
    # V3.45.1 fix: 舊條件 current < band_lower_capped 是 dead code（band_lower 必 < current，
    # half_width 1.28σ > drift clamp 0.6σ；capped=max(band_lower,support) 要 > current 需 support>current 反常）。
    # 改為「現價顯著低於長期FV(<0.9×) + 中期動能向上(mid>current) + 短期點估計仍低於FV」→ 三框一致看多
    mhp_signal = "high_conviction_long_zone"
elif mid_target and mid_target > current_price > LT:
    mhp_signal = "momentum_not_value"       # 動能在、估值貴 → 動能交易非價值持有（對應 hot_zone_probe）
else:
    mhp_signal = "neutral_aligned"

# V3.45.3 degraded guard：fair_value_summary.confidence == "low"（如僅 1 anchor）時
# signal 照算但 signal_note 必附「長期FV 信心 low，訊號僅供參考」— 防弱數據強訊號誤導
```

### 與下游 Phase 的接線（補 TP/SL 來源缺口）

| 下游 | 取值來源 |
|---|---|
| Phase 3 T5 仲裁 | `mhp_signal == "wait_for_pullback"` → reasoning 追加估值警告（**不改決策數學**）；`momentum_not_value` → 對齊既有 `hot_zone_probe` 語意 |
| Phase 4 `trade_plan.entry_*` | short_term band `[band_lower_capped, band_point]`（aggressive 近 point，conservative 近 lower/support）|
| Phase 4 `trade_plan.take_profit` | mid_term `mid_target`（若 > resistance 則 cap 在 resistance 並註記）|
| Phase 4 `trade_plan.stop_loss` | `min(band_lower_capped, key_levels.support)` − buffer；與 `final_stop_loss_pct` 取較保守者 |

> **重點紀律**：MHP 為**呈現 + 接線層**。`mhp_signal` 餵 reasoning 與 trade_plan 取值，**不**改 lane score、不改 final_decision 數學、**不**進 11-field decision_lock（derived/advisory）。長期層數字一律以 `fair_value_summary` 為準。

### 4.5.4 — 輸出 `multi_horizon_price_framework`

```json
{
  "phase": "4.5",
  "agent": "Portfolio_Manager",
  "multi_horizon_price_framework": {
    "short_term_5d": {
      "band":               ["float band_lower", "float band_point", "float band_upper"],
      "band_capped":        ["float lower_capped", "float band_point", "float upper_capped"],
      "drift_sigma":        "float — clamp [-0.6, +0.5]",
      "sigma_daily":        "float|null",
      "atr_14":             "float|null",
      "confidence":         "high | medium | low",
      "catalyst_widened":   "bool",
      "key_level_note":     "string — 哪邊被 support/resistance 反射"
    },
    "mid_term_60d": {
      "momentum_target":    "float|null",
      "pt_60d":             "float|null",
      "earnings_revision":  "float|null",
      "weights_used":       "object — 重分配後（sum=1.0）",
      "mid_target":         "float|null",
      "reality_check_note": "string — vs key_levels 成立條件"
    },
    "long_term_ref": {
      "weighted_fair_value": "float — 引用自 fair_value_summary，不重算",
      "verdict_band":        "string — 引用自 fair_value_summary",
      "confidence":          "string — 引用自 fair_value_summary"
    },
    "convergence": {
      "mhp_signal":   "wait_for_pullback | high_conviction_long_zone | momentum_not_value | neutral_aligned",
      "signal_note":  "string — 1 句解釋三框相對位置"
    }
  }
}
```

> 缺料降級：`sigma_daily` 缺 → short_term confidence=low（仍輸出 atr 反推帶）；`mid_target` 全錨缺 → null（不擋）；長期層引用既有 `fair_value_summary`，永遠可得。Validator 對 MHP block 缺失/不全只印 **warning（非 fatal，rc 維持 0）**，向後相容 V5.0 舊 entry。


---

## Forward Expectations（shadow，advisory — V4.71.0 起移出 分析 flow，on-demand 工具）

> 本節自 `investment_protocol_v5_0.md` Phase 4.5 移入（V4.71.0 P1-5 落日條款：協議本文
> 每次 run 載入，此段為版本演進紀錄，無 runtime 必要）。指令與紀律速記留在協議本文。

成長股的 `fair_value_summary` 後視錨（trailing DCF / owner-earnings）會把公允價壓到不可信
（ARM「$8 DCF / FV $51 / −86%」）。手動跑
`python3 investment/scripts/forward_expectations.py --ticker <T> --self-assemble`
產出前瞻 lane（consensus 分析師估計 / market_implied reverse DCF / base_rate 同業歷史成長 /
adapter-gated Independent）+ expectations matrix + expectations gap + forward financial bridge。
可用 `python3 investment/scripts/forward_expectations_report.py --snapshot-file <snapshot.json>`
將 snapshot render 成 MD §6 advisory 區塊。**只有同口徑指標可計算 gap 與 verdict**；
FCF / EPS / 營收 CAGR 可並列描述，但禁止互減或產生跨口徑判定。
**shadow-only — 不進 decision_lock、不改 `fair_value_summary` 或任何決策數學**；schema 見
`investment/forward_expectations_schema.md`。跨產業 Independent lane 須遵守
`investment/forward_expectations_adapter_contract.md`。

版本演進（原協議本文段落 verbatim 保存）：
- V4.15.0 起 `royalty_ip` adapter 可由 product segment deterministic match 並輸出 Revenue Exposure Map / driver tree / transmission graph；缺 units、rate、conversion 或 evidence 時必須維持 `independent_lane.available=false`，外部趨勢只能標為 `qualitative_only`。
- V4.16.0 起每次 run 另保存 point-in-time `evidence_inventory`：structured company facts 可 accepted；Nexus `CO_THEME`／無 corroboration 或無 conversion method 的關係只能 provisional；缺來源與 adapter 必要 driver 必須明列 acquisition target。
- V4.17.0 primary-source acquisition 僅讀既有 transcript 或 `--primary-source-file` 明確提供的 filing／IR／transcript bundle；缺 URL、日期、期間、單位或 supported source type 的候選不得 promoted。
- V4.18.0 起 source discovery 對所有 ticker 共用：只依實際 filing metadata 分類 10-K／20-F／40-F／10-Q／6-K 等來源，不按 ticker、國家、產業或 adapter 猜測；URL 與 metadata 永遠 provisional，不得 numeric eligible。
- V4.19.0 起可選 `--acquire-documents`，僅下載 discovery manifest 內 allowlisted SEC filing 文件並正規化成 text bundle；公司 IR root、SEC submissions manifest 與任意網站不抓。下載全文本身仍不是證據，必須再通過 primary-source promotion gate。
- V4.20.0 起 management guidance extraction 可從 primary-source document 抽 revenue／EPS／margin／FCF／capex 明確 guidance；range 必須保持 range，midpoint 只當 derived helper，不得直接改 fair value。
- V4.21.0 起 estimate revision snapshot 保存 annual revenue／EPS consensus curve、dispersion、analyst count 與 rating momentum；單一 cache 無歷史 estimate 版本時必須標示 delta unavailable，不得假造上修/下修。
- V4.22.0 起 calibration scaffold 可唯讀對照 forecast snapshot 與後續 earnings actual；樣本不足固定 `insufficient_sample`，不得調權重或決策規則。
- V4.23.0 起 forward financial bridge 將 annual estimates + 歷史 margin／FCF conversion／share count 映射成簡化 P&L/FCF；缺核心輸入必須降級。
- V4.24.0 起 expectations gap 只做同口徑 gap，bridge wide-gap / negative FCF 只作財務敘事風險。
- V4.25.0 起 report renderer 只產生 shadow MD section，不進 validator 必填欄位。
- V4.26.0 起 scenario policy 先判定 allowed modes；缺 driver evidence / conversion method 時只能 qualitative-only 或 range/overlay-only，禁止固定 EPS/P-E 百分比加減、LLM invented TAM 或跨口徑 gap 當 driver。輸出 ≠ 前瞻單點公允價。

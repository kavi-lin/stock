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
> **契約相容**：`fair_value_summary` key/shape **完全不變**（仍是長期層、仍受 decision_lock + validator 保護；
> engine 的 blend 演算法與 V5.0 byte-identical）；三框架另存於新 sibling block `multi_horizon_price_framework`，
> 長期層**直接引用** `fair_value_summary.weighted_fair_value`，不複製不重算。

### 4.5.0 — Long-Term Layer：`fair_value_summary`（既有 6-anchor，原封不動）

### 算法

```python
# 從 Valuation Specialist (Phase 2) 拿 valuation_anchors
anchors = phase2.valuation_specialist.valuation_anchors
weights_default = {
  "dcf_unlevered":      0.30,
  "dcf_levered":        0.15,
  "analyst_pt_consensus": 0.20,
  "peer_pe_implied":    0.20,
  "owner_earnings_mult": 0.10,
  "forecaster_blend":   0.05,
}

# 缺 anchor → weight 重分配
available = {k: v for k, v in anchors.items() if v is not None and v > 0}
total_w = sum(weights_default[k] for k in available)
weights_norm = {k: weights_default[k] / total_w for k in available}

weighted_fair_value = sum(weights_norm[k] * available[k] for k in available)
current_price = ticker_data_bundle["scoring"]["price"]
vs_current_pct = (weighted_fair_value - current_price) / current_price * 100

# Verdict band
if vs_current_pct >= 30:   verdict_band = "extreme_undervalued"
elif vs_current_pct >= 10: verdict_band = "undervalued"
elif vs_current_pct >= -10: verdict_band = "fairly_valued"
elif vs_current_pct >= -30: verdict_band = "overvalued"
else:                       verdict_band = "extreme_overvalued"

# Confidence by anchor count
if len(available) >= 5:    confidence = "high"
elif len(available) >= 3:  confidence = "medium"
else:                       confidence = "low"
```

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
    "weights_used": {"dcf_unlevered": 0.32, "dcf_levered": 0.16, ...},  // 重分配後
    "weighted_fair_value":  "float",
    "current_price":        "float",
    "vs_current_pct":       "float",
    "verdict_band":         "extreme_undervalued | undervalued | fairly_valued | overvalued | extreme_overvalued",
    "confidence":           "high | medium | low",
    "anchors_available":    "int 0-6",
    "methodology_note":     "string — e.g. '5/6 anchors used; owner_earnings_mult unavailable, weight redistributed'"
  }
}
```

### 與 Valuation lane 的關係
- Valuation Specialist (Phase 2) 給 lane score（-5 ~ +5）參與加權
- `fair_value_summary` (Phase 4.5) 給 deterministic 數字呈現給 user（"合理股價 $215，現價 $285，溢價 32.5%"）
- 兩者都用同一組 anchor，但 Specialist 是 LLM 詮釋（含 narrative），Phase 4.5 是純算數

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
    agreement_grade = ("high" if anchor_dispersion_cv < 0.15      # cv 小 = 錨一致 = 高同意度
                       else "medium" if anchor_dispersion_cv < 0.35 else "low")
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

> **agreement_grade / dispersion_cv 門檻（0.15 / 0.35）目前為初值** — 待 P2 接 Phase 4.6 cap 時用實際歷史分布校準。
> **V3.46.1 backfill 發現**：歷史 37 筆 CV 分布 median=0.46、P33=0.367 — 初值 0.15/0.35 會把幾乎全部
> session 判 low；校準建議門檻（33/66 pct）= **0.367 / 0.484**，#2 cap 接線前由 user 核可後改 engine 常數。
>
> **#6 shadow 退出條件（寫死，避免永久欠債）**：累積 **≥ 20 session** 後，比對「若 live anchor 改用 `oe_mult_rate_linked` 會翻轉 `verdict_band` 的比率」。**翻轉率 < 15% → 出切換提案**（rate-linked 影響小、安全可切）；**≥ 15% → 維持 static 並標記需 backtest 驗證方向性**（影響大、不可盲切）。
>
> **報告讀出端（V3.46.1）**：`python3 investment/scripts/shadow_report.py` — 唯讀，一次算齊
> #2 dispersion backfill / #6 oe 翻轉率 / #3 archetype 翻轉率 / #4 news 分布偏移 + checkpoint 進度，
> 輸出 `reports/SHADOW_REPORT_<date>.md`。所有 shadow 的「≥N session 報告」都由它產。

輸出 sibling block `fair_value_range`（見 schema）。**winsorize / outlier 降權留 P2**（percentile 取區間天然抗 outlier，P1 不需要）。

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


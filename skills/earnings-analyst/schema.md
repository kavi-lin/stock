# earnings-analyst — JSON Schema (V1.0)

> Cache file: `skills/earnings-analyst/cache/<TICKER>_<LAST_EARNINGS_DATE>.json`
> Markdown report: `reports/<RUN_DATE>_<TICKER>_earnings.md`

## Top-level

```json
{
  "ticker":              "string",
  "as_of_date":          "YYYY-MM-DD — when fetch ran",
  "last_earnings_date":  "YYYY-MM-DD — most recent quarter date (cache key)",
  "next_earnings_est":   "YYYY-MM-DD — derived = last_earnings_date + ~90d",
  "schema_version":      "V1.0",
  "data_source":         "FMP HTTP REST",

  "snapshot":            { ... },
  "quarterly_pnl":       [ {q1}, {q2}, ... ],     // 8 quarters, newest-first
  "balance_sheet":       [ {q1}, {q2}, ... ],     // 8 quarters
  "cash_flow":           [ {q1}, {q2}, ... ],     // 8 quarters
  "ttm_metrics":         { ... },                  // key-metrics-ttm + ratios-ttm union
  "annual_growth":       [ {y1}, {y2}, ... ],     // 5 years financial-growth
  "enterprise_value":    { ... },
  "valuation":           { ... },                  // DCF + analyst PT + ratings
  "analyst_grades":      [ {monthly_snapshot}, ... ],

  "derived":             { ... },                  // analyze.py output (margins / quality / growth / score)
  "quality_flags":       [ "string", ... ],
  "composite_score":     "int 0-100",
  "verdict":             "STRONG | SOLID | MIXED | WEAK | DETERIORATING",
  "score_components":    {
    "quality":    "0-30",
    "growth":     "0-30",
    "valuation":  "0-25",
    "analyst":    "0-15"
  }
}
```

## snapshot

```json
{
  "companyName":  "string",
  "sector":       "string",
  "industry":     "string",
  "price":        "float",
  "marketCap":    "int",
  "ipoDate":      "YYYY-MM-DD",
  "ceo":          "string",
  "fullTimeEmployees": "int | null"
}
```

## quarterly_pnl[i] (subset of FMP income-statement)

```json
{
  "date": "YYYY-MM-DD", "fiscalYear": "string", "period": "Q1|Q2|Q3|Q4",
  "revenue": "int", "grossProfit": "int", "operatingIncome": "int",
  "netIncome": "int", "eps": "float", "epsDiluted": "float",
  "researchAndDevelopmentExpenses": "int",
  "sellingGeneralAndAdministrativeExpenses": "int",
  "ebitda": "int", "ebit": "int"
}
```

## balance_sheet[i] (subset)

```json
{
  "date": "YYYY-MM-DD", "period": "Q1-Q4",
  "totalAssets": "int", "totalLiabilities": "int", "totalEquity": "int",
  "totalCurrentAssets": "int", "totalCurrentLiabilities": "int",
  "cashAndCashEquivalents": "int", "shortTermInvestments": "int",
  "totalDebt": "int", "longTermDebt": "int", "shortTermDebt": "int",
  "netReceivables": "int", "inventory": "int",
  "retainedEarnings": "int"
}
```

## cash_flow[i] (subset)

```json
{
  "date": "YYYY-MM-DD", "period": "Q1-Q4",
  "operatingCashFlow": "int", "freeCashFlow": "int",
  "capitalExpenditure": "int",
  "stockBasedCompensation": "int",
  "commonStockRepurchased": "int",
  "commonDividendsPaid": "int",
  "netIncome": "int"
}
```

## ttm_metrics

```json
{
  "from_key_metrics_ttm": {
    "marketCap": "int",
    "freeCashFlowYieldTTM": "float",
    "evToEBITDATTM": "float",
    "currentRatioTTM": "float",
    "netDebtToEBITDATTM": "float",
    "incomeQualityTTM": "float",
    "capexToOperatingCashFlowTTM": "float",
    "daysOfSalesOutstandingTTM": "float"
  },
  "from_ratios_ttm": {
    "grossProfitMarginTTM":   "float",
    "operatingProfitMarginTTM":"float",
    "netProfitMarginTTM":     "float",
    "ebitMarginTTM":          "float",
    "priceToEarningsRatioTTM":"float",
    "priceToBookRatioTTM":    "float",
    "debtToEquityRatioTTM":   "float",
    "interestCoverageRatioTTM":"float"
  }
}
```

## valuation

```json
{
  "dcf_intrinsic":          "float — FMP /discounted-cash-flow (FCFF, unlevered)",
  "dcf_levered_intrinsic":  "float — FMP /levered-discounted-cash-flow (FCFE); null if not available",
  "dcf_vs_price_pct":       "float — (intrinsic - price) / price",
  "price_target_consensus": "float",
  "price_target_high":      "float",
  "price_target_low":       "float",
  "price_target_median":    "float",
  "pt_upside_pct":          "float — (consensus - price) / price",
  "pt_dispersion_pct":      "float — (pt_high - pt_low) / pt_consensus × 100; >40% = high analyst disagreement",
  "pt_news": [
    {
      "date":            "YYYY-MM-DD",
      "analystCompany":  "string — e.g. Goldman Sachs",
      "priceTarget":     "float — new price target",
      "adjPriceTarget":  "float — split-adjusted",
      "publishedDate":   "string"
    }
  ],
  "ratings_snapshot": {
    "overallScore":              "int 1-5",
    "rating":                    "string",
    "discountedCashFlowScore":   "int 1-5",
    "priceToEarningsScore":      "int 1-5",
    "priceToBookScore":          "int 1-5",
    "debtToEquityScore":         "int 1-5",
    "returnOnEquityScore":       "int 1-5",
    "returnOnAssetsScore":       "int 1-5"
  },
  "forward_eps_estimate":   "float | null — derived via earnings-valuation-forecaster (3-method avg);null if insufficient history"
}
```

## analyst (V1.74 新增 — 分析師動態深度層)

```json
{
  "rating_history": [
    { "date": "YYYY-MM-DD", "rating": "string — e.g. A+", "ratingScore": "int 1-5" }
  ],
  "rating_trend": "improving | stable | declining | insufficient_data — 3M composite trend",
  "grades_summary": {
    "strongBuy": "int", "buy": "int", "hold": "int", "sell": "int", "strongSell": "int",
    "strong_buy_pct": "float — strongBuy / total × 100",
    "total_analysts": "int"
  },
  "grades_news": [
    {
      "date":           "YYYY-MM-DD",
      "gradingCompany": "string — institution name",
      "previousGrade":  "string — e.g. Neutral",
      "newGrade":       "string — e.g. Buy",
      "action":         "string — upgrade | downgrade | init | reit"
    }
  ]
}
```

**Protocol 引用規則（Phase 2 News lane）：**
- `grades_news` 近 10 天升評數 > 降評數 → Bull +1 signal
- `pt_news` 近 8 筆平均 PT 調整方向 → 輔助 Bull/Bear 論點
- `pt_dispersion_pct` > 40% → 注記「分析師分歧高，目標價參考度下降」
- `rating_trend == improving` → +0.5 analyst confidence bonus（替換舊「升評 +0.5」邏輯）
- `dcf_levered_intrinsic` vs `dcf_intrinsic` 差距 > 20% → Burry lane 資本結構警告

## derived (analyze.py output)

```json
{
  "margins_8q": [ {"date":"...","gross":0.45,"operating":0.32,"net":0.28}, ... ],
  "yoy_growth": {
    "revenue_yoy":        "float — latest Q vs same Q a year ago",
    "earnings_yoy":       "float",
    "operating_yoy":      "float",
    "revenue_qoq":        "float — latest Q vs prior Q",
    "growth_acceleration":"accelerating | steady | decelerating"
  },
  "balance_health": {
    "working_capital":     "int — totalCurrentAssets - totalCurrentLiabilities",
    "current_ratio":       "float",
    "debt_to_equity":      "float",
    "net_cash":            "int — cash+ST inv - totalDebt"
  },
  "cash_flow_quality": {
    "fcf_margin":          "float — freeCashFlow / revenue (latest Q)",
    "cash_conversion":     "float — operatingCashFlow / netIncome (TTM sum)",
    "capex_intensity":     "float — capex / revenue"
  }
}
```

## quality_flags(deterministic — `analyze.py` 內運算)

| Flag | 觸發條件 |
|---|---|
| `accruals_warning` | TTM \|NI − OpCF\| / \|NI\| > 0.30 |
| `capex_outpaces_ocf` | latest Q OpCF / abs(capex) < 1.0 |
| `gross_margin_compression` | 最新 4 季 gross margin 連續下滑 |
| `dso_slowdown` | 最新 4 季 DSO(receivables/revenue×91) 連續上升 |
| `negative_fcf` | latest Q FCF < 0 |
| `debt_buildup` | totalDebt 環比增 > 15% 連 2 季 |

無 flag → 空 list `[]`(品質乾淨)。

## verdict 對應

| composite_score | verdict |
|---|---|
| 80–100 | STRONG |
| 65–79  | SOLID |
| 50–64  | MIXED |
| 35–49  | WEAK |
| 0–34   | DETERIORATING |

---

# Cache 檔 V1.73 新增欄位（infographic data layer）

`fetch.py` 在原 V1.0 cache 的 `<TICKER>_<DATE>.json` 內**追加**這幾個 key（既有 schema 不破壞）：

| Key | 來源 | 說明 |
|---|---|---|
| `earnings_surprises` | `/stable/earnings` | `[{date, epsActual, epsEstimated, revenueActual, revenueEstimated, lastUpdated}]`，最近 8 筆 |
| `segments.product_fy` | `/stable/revenue-product-segmentation` | `[{date, fiscal_year, period, products: {name: amount_usd}}]`，**僅 FY 年度**（季度需付費） |
| `segments.geographic_fy` | `/stable/revenue-geographic-segmentation` | `[{date, fiscal_year, period, regions: {name: amount_usd}}]`，僅 FY 年度 |
| `dividends_history` | `/stable/dividends` | `[{date, dividend, frequency, declarationDate, ...}]`，最近 8 筆 |
| `transcript` | `/stable/earning-call-transcript` (4-tier resolver) | `{year, quarter, date, content, source_q_offset}` 或 `null`。`source_q_offset=0` 表 Tier 1 命中；>0 表回退過 N 季 |

**Edge cases**：
- AMD 無股息（latest entry 1995 special）→ `dividends_history` 只 1 筆 → 渲染端應 detect `dividend < 2010-01` 視為 not paying
- MSFT geographic 只 US/Non-US（FY 端點限制）→ 渲染端 detect `len(regions) ≤ 2` 退化 2-card 配置
- 任何 endpoint 回 None → 沿用既有 graceful pattern（log stderr，cache 寫 null/[]）

---

# Infographic Cache `<TICKER>_<DATE>.infographic.json` (V1.0)

由 LLM narrate phase 在 `fetch + analyze + validate` 後產生（Claude Code in-conversation 讀 cache JSON + transcript.content，Write 寫此檔）。`schema_kind` 必須等於 `"infographic"`，與 V1.0 資料層 cache 區別。

### 必填頂層 keys

| Key | 型別 | 說明 |
|---|---|---|
| `ticker` | string | 大寫，與 cache 一致 |
| `as_of_date` | string | 與 cache 一致 (`YYYY-MM-DD`) |
| `last_earnings_date` | string | 與 cache 一致 |
| `fiscal_label` | string | 顯示用，例 `"FY26 Q2"` |
| `schema_version` | string | `"V1.0"` |
| `schema_kind` | string | **必須** `"infographic"` |
| `transcript_used` | bool | 是否抽到 transcript content |
| `transcript_source` | object \| null | `{year, quarter, offset}` |
| `headline_oneliner` | string | 整體一句話摘要 |
| `surprise` | object | revenue/EPS actual vs estimated |
| `segments_q` | object | 產品分部 |
| `geographic_q` | object | 地理分部 |
| `capital_returns` | object | 回購 + 股息 + 現金 |
| `key_highlights` | array(≥3) | icon + title + body |
| `summary` | array(≥2) | tldr 條列 |

### 條件必填

- `ceo_quote` (object): 當 `transcript_used==true` 時必填，否則可省略

### 結構範例 (AAPL FY26 Q2)

```json
{
  "ticker": "AAPL",
  "as_of_date": "2026-05-01",
  "last_earnings_date": "2026-04-30",
  "fiscal_label": "FY26 Q2",
  "schema_version": "V1.0",
  "schema_kind": "infographic",
  "transcript_used": true,
  "transcript_source": {"year": 2026, "quarter": 2, "offset": 0},
  "headline_oneliner": "iPhone 強勁 + 服務新高,股東回饋加碼 $100B",

  "surprise": {
    "revenue_actual":       111180000000,
    "revenue_estimated":    109460000000,
    "revenue_beat":         true,
    "revenue_surprise_pct": 0.0157,
    "eps_actual":           2.02,
    "eps_estimated":        1.92,
    "eps_beat":             true,
    "eps_surprise_pct":     0.0521,
    "yoy_revenue_growth":   0.05,
    "yoy_eps_growth":       0.13
  },
  "segments_q": {
    "is_fy_fallback": false,
    "kind": "product",
    "items": [
      {"name": "iPhone",        "amount_usd": 56990000000, "yoy_pct": 0.02,
       "icon": "smartphone",    "highlight": true},
      {"name": "Services",      "amount_usd": 30980000000, "yoy_pct": 0.12,
       "icon": "cloud",         "highlight": true},
      {"name": "Mac",           "amount_usd":  8400000000, "yoy_pct": 0.07,
       "icon": "monitor"},
      {"name": "Wearables",     "amount_usd":  7900000000, "yoy_pct": -0.02,
       "icon": "watch"},
      {"name": "iPad",          "amount_usd":  6910000000, "yoy_pct": 0.05,
       "icon": "tablet"},
      {"name": "Greater China", "amount_usd": 20500000000, "yoy_pct": 0.06,
       "icon": "globe",         "highlight": true}
    ]
  },
  "geographic_q": {
    "is_fy_fallback": true,
    "items": [
      {"region": "Americas",      "amount_usd": ..., "yoy_pct": ...}
    ]
  },
  "capital_returns": {
    "buyback_authorization_usd": 100000000000,
    "buyback_qtr_executed_usd":   11000000000,
    "dividend_qtr_paid_usd":       3800000000,
    "dividend_per_share_new":            0.27,
    "dividend_per_share_prev":           0.26,
    "dividend_hike_pct":             0.04,
    "total_returned_qtr_usd":      15000000000,
    "cash_and_marketable_usd":    147000000000,
    "announcements": [
      "Board authorized additional $100B buyback",
      "Quarterly dividend raised 4% to $0.27/share"
    ]
  },
  "ceo_quote": {
    "speaker": "Tim Cook",
    "title":   "CEO",
    "quote":   "...",
    "context": "On iPhone supply constraints"
  },
  "key_highlights": [
    {"icon": "trending-up", "title": "Services 創新高",
     "body": "Services 季營收 $30.9B,YoY +12%."}
  ],
  "summary": [
    "本季 revenue + EPS 雙 beat,服務 + iPhone 雙引擎",
    "$100B 新 buyback + 4% 加股息,資本回報訊號強"
  ],
  "dividends": {
    "frequency": "Quarterly",
    "latest_dps": 0.27,
    "previous_dps": 0.26,
    "consecutive_increases_yrs": 13,
    "is_paying": true
  }
}
```

### Fallback 行為

- `transcript_used=false`：`ceo_quote` 省；`segments_q.is_fy_fallback=true` 取 `cache.segments.product_fy[0]`；`capital_returns.announcements=[]`；`key_highlights` 由 yoy+flags 合成
- AMD 無股息：`dividends.is_paying=false`，`capital_returns.dividend_*` 全 0/null

### Quarterly segment 處理規則

LLM narrate phase 應**優先**從 transcript content 抽 CFO 報的季度 segment 數字（infographic 上的數字本來就是這樣來的），抽不到才退化用 FY 年度 + `is_fy_fallback=true`。

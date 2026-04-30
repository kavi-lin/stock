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
  "dcf_intrinsic":          "float — FMP discounted-cash-flow result",
  "dcf_vs_price_pct":       "float — (intrinsic - price) / price",
  "price_target_consensus": "float",
  "price_target_high":      "float",
  "price_target_low":       "float",
  "price_target_median":    "float",
  "pt_upside_pct":          "float — (consensus - price) / price",
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

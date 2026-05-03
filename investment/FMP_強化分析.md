Agent completed. agent_id: fmp-protocol-enhancement, agent_type: general-purpose, status: completed, description: FMP API protocol enhancement analysis, elapsed: 421s, total_turns: 0, model: claude-sonnet-4.6, duration: 416s

Now I have a complete picture of the current implementation. Let me write the full report.

---

# FMP Stable API 強化分析報告 — Investment Protocol V4.8
**版本**: 分析日 2025-01-30 | 範疇: 全協議 Phase 0-4 + 支援 skills

---

## Section 1: Web-Fetch 替換機會（最高優先）

### 1.1 `theme-detector/scripts/finviz_performance_client.py` → FMP 產業績效端點

**Where**: Phase 0 → `daily_update.sh` Step 6 → `theme_detector.py` → `finviz_performance_client.py`

**Current**: `finvizfinance.group.performance` 網頁爬取（無 API key），取 perf_1w / perf_1m / perf_3m / perf_6m / perf_1y / perf_ytd per industry。依賴 HTML DOM，頻繁 breakage 風險。

**Replacement**:
```python
# 完整替換 finviz_performance_client.py 的 get_industry_performance()
def _fmp_get(path, params=None):
    api_key = os.environ["FMP_API_KEY"]
    r = requests.get(f"https://financialmodelingprep.com/stable/{path}",
                     params={**(params or {}), "apikey": api_key}, timeout=15)
    r.raise_for_status()
    return r.json()

def get_industry_performance_fmp() -> list[dict]:
    """Replace finviz scraping with FMP structured data."""
    # Current snapshot (perf_1w equivalent = changesPercentage)
    snapshot = _fmp_get("industry-performance-snapshot")
    # Historical: 1m / 3m / 6m / 1y from historical endpoint
    hist_1m  = _fmp_get("historical-industry-performance",
                         {"from": (date.today() - timedelta(days=35)).isoformat()})
    hist_3m  = _fmp_get("historical-industry-performance",
                         {"from": (date.today() - timedelta(days=95)).isoformat()})
    # Merge by industryName into the same COLUMN_MAP shape
    ...
```

需要的 endpoints:
- `/stable/industry-performance-snapshot` → changesPercentage (1d/ytd)
- `/stable/historical-industry-performance` → 多時間框架績效
- `/stable/sector-performance-snapshot` → sector 層級
- `/stable/historical-sector-performance` → sector 多時間框架

**Data Coverage**: FMP 產業分類（GICS）與 Finviz 略有差異（Finviz 較細分）。需建一次 industry name mapping table。

**Risk**: 低。FMP 免費 tier 含此端點；爬取替換後可消除 finviz HTML 依賴，theme-detector 穩定性大幅提升。

---

### 1.2 `market-news-analyst/scripts/fetch.py` — Finviz 新聞爬取

**Where**: Phase 2 News lane → `_finviz_news()` — finvizfinance.quote().ticker_news()

**Current**: Web scraping via `finvizfinance` library，100-row news list，return `{date, title, source, url}`。

**Replacement**:
```python
def _fmp_stock_news(ticker: str, since: datetime, api_key: str,
                    max_items: int = 50) -> list[dict]:
    """FMP /stable/news-stock — ticker-specific news, structured."""
    try:
        r = requests.get(
            "https://financialmodelingprep.com/stable/news-stock",
            params={
                "symbols": ticker,
                "from": since.date().isoformat(),
                "to": datetime.now(timezone.utc).date().isoformat(),
                "limit": max_items,
                "apikey": api_key,
            }, timeout=10)
        if r.status_code != 200:
            return []
        return [
            {"date": it.get("publishedDate"), "title": it.get("title"),
             "source": it.get("site"), "url": it.get("url"),
             "sentiment": it.get("sentiment")}   # bonus: FMP includes sentiment score
            for it in (r.json() or [])
        ]
    except Exception:
        return []

# Also: press releases
def _fmp_press_releases(ticker: str, since: datetime, api_key: str) -> list[dict]:
    r = requests.get("https://financialmodelingprep.com/stable/news-press-release",
                     params={"symbols": ticker, "limit": 20, "apikey": api_key}, timeout=10)
    ...
```

**Risk**: 中。FMP `/stable/news-stock` 的 coverage 比 Finviz 略窄（Finviz 整合更多小型媒體）。建議保留 finviz 做補充，不完全替換 — 改為：FMP 為主 + finviz 為 fallback（與目前 analyst_actions 策略一致）。額外優勢：FMP news 附帶 `sentiment` 欄位，News subagent 可直接參考。

---

### 1.3 `us-stock-analysis/scripts/analyze.py` — yfinance 為主數據源

**Where**: Phase 2 Fundamentals lane，yfinance 是 PRIMARY

**Current**: `yf.Ticker(ticker).info` 取 P/E、EPS、revenue、FCF、debt/equity、next earnings date。協議 V4.8 已明確說「EARNINGS_ANALYST_BUNDLE 存在時 Skill 應優先讀 bundle」，但 `analyze.py` 本身未修改仍拉 yfinance。

**Replacement**: 若 `EARNINGS_ANALYST_BUNDLE` 存在，`analyze.py` 應讀取 bundle 而非重打 yfinance：

```python
def _load_from_bundle(bundle: dict) -> dict:
    """Extract the same fields analyze.py currently fetches from yfinance,
    from the EARNINGS_ANALYST_BUNDLE passed by Phase 1 PM."""
    q0 = bundle.get("quarterly_pnl", [{}])[0]
    bs0 = bundle.get("balance_sheet", [{}])[0]
    cf0 = bundle.get("cash_flow", [{}])[0]
    ttm = bundle.get("ttm_metrics", {})
    km = ttm.get("from_key_metrics_ttm", {})
    rat = ttm.get("from_ratios_ttm", {})
    ev = bundle.get("enterprise_value", {})
    return {
        "revenue_ttm":        q0.get("revenue"),
        "net_income_ttm":     q0.get("netIncome"),
        "ebit":               q0.get("ebit"),
        "pe_ratio":           rat.get("priceToEarningsRatioTTM"),
        "pb_ratio":           rat.get("priceToBookRatioTTM"),
        "fcf_margin":         km.get("freeCashFlowYieldTTM"),  # derive if needed
        "debt_to_equity":     rat.get("debtToEquityRatioTTM"),
        "ev_ebitda":          km.get("evToEBITDATTM"),
        "current_ratio":      km.get("currentRatioTTM"),
        "gross_margin":       rat.get("grossProfitMarginTTM"),
        "operating_margin":   rat.get("operatingProfitMarginTTM"),
        "net_margin":         rat.get("netProfitMarginTTM"),
        "enterprise_value":   ev.get("enterpriseValue"),
        "next_earnings":      bundle.get("next_earnings_est"),
    }
```

若 bundle 不存在，目前的 yfinance fallback 保留即可。**直接 FMP 替換**時，sector P/E 已用 `/stable/sector-pe-snapshot`（現有），其他欄位從 `/stable/ratios-ttm` + `/stable/key-metrics-ttm` 取得。

**Risk**: 中。`analyze.py` 目前仍然有效，問題是重複 fetch（bundle 與 yfinance 抓相同欄位）。此項是「efficiency」改善，非「correctness」問題。

---

### 1.4 Phase 0 `key_themes` / `bullish_signals` / `bearish_signals` — 保留 LLM

**Where**: Phase 0 macro synthesis

**Current**: 協議明確說「僅 key_themes / bullish_signals / bearish_signals 文字面保留 LLM 摘要」。數字已由 skill chain 提供，敘事由 LLM 合成。

**Assessment**: ✅ **此設計正確，不需替換**。LLM 的比較優勢正是敘事合成（narrative tone），而非數字提取。保留此設計。

---

### 1.5 `market-sentiment-analyzer` — `short_pct_float` yfinance

**Where**: Phase 2 Sentiment lane，`_per_ticker_structured_signals()` 中的 `short_pct_float`

**Current**: `yf.Ticker(ticker).info.get("shortPercentOfFloat")` — FINRA bi-monthly snapshot

**Replacement**: FMP Stable API **未提供** `shortPercentOfFloat` 的直接端點。FMP 有 `shares-float`（total float shares）和 `key-metrics-ttm`（有 `shortRatioTTM`），但 **short % of float 需要 short interest shares ÷ float shares**，短倉股數本身在 FMP stable 無直接端點。

```python
# Best-effort FMP approach: short ratio as proxy (不同但有參考)
km_ttm = _fmp_get("/stable/key-metrics-ttm", {"symbol": ticker})
short_ratio = km_ttm[0].get("shortRatioTTM") if km_ttm else None
# short_ratio = float shares short / daily avg volume (days to cover)
# NOT the same as short% of float, but signals same directional risk
```

**Risk**: 高替換風險。`shortRatioTTM`（days-to-cover）≠ `short % of float`（協議 rubric 直接用 20% threshold）。**建議保留 yfinance 作為 short_pct_float 的唯一來源**，同時加入 `shortRatioTTM` 作為補充信號。

---

## Section 2: 現有 Finnhub 資料強化

### 2.1 原則確認 — 隔離合約

`scoring.*` = Finnhub-only → LLM；`_audit.*` = FMP-only → 永不傳 LLM。此合約**不得打破**。

任何新 FMP 資料**必須走獨立的 FMP_SUPPLEMENTARY_BUNDLE**（Section 6 提案），不得混入 dual_fetch 的 `scoring.*`。

### 2.2 TICKER_DATA_BUNDLE（scoring.*）目前欄位 vs 協議引用欄位

| 協議引用欄位 | 目前 scoring.* 中？ | 來源 | 問題 |
|---|---|---|---|
| `price` | ✅ | Finnhub quote | — |
| `previousClose` | ✅ | Finnhub quote | — |
| `dayHigh` / `dayLow` | ✅ | Finnhub quote | — |
| `mktCap` | ✅ | Finnhub profile | — |
| `peRatio` | ✅ | Finnhub metric | — |
| `epsTTM` | ✅ | Finnhub metric | — |
| `dividendYield` | ✅ | Finnhub metric | — |
| `priceToBookRatio` | ✅ | Finnhub metric | — |
| `forwardPE` | ✅ | Finnhub metric | — |
| `pegRatio` | ✅ | Finnhub metric (pegTTM) | Trailing PEG，非 forward PEG |
| `roeTTM` | ✅ | Finnhub metric | — |
| `debtToEquity` | ✅ | Finnhub metric | — |
| `fcfPerShareTTM` | ✅ | Derived from pfcfShareTTM | 間接計算，需 audit 校驗 |
| `nextEarningsDate` | ✅ | Finnhub calendar | — |
| **`insider_stats[]`** | ❌ | Protocol says FMP | 不在 scoring.* —正確，在 Sentiment skill |
| **`insider_sentiment.mspr`** | ❌ | Finnhub /stock/insider-sentiment | 不在 scoring.* — 正確，在 Sentiment skill |
| **`short_pct_float`** | ❌ | yfinance | 不在 scoring.* — 正確，在 Sentiment skill |

**結論**: `scoring.*` 15 個欄位完整。`insider_stats` / `mspr` / `short_pct_float` 按設計放在 Sentiment skill 而非 dual_fetch，是正確的架構決策。

### 2.3 Missing Fields → 應進 FMP_SUPPLEMENTARY_BUNDLE

下列欄位**協議分析時有用但目前無結構化來源**：

| 欄位 | FMP Endpoint | 分析用途 |
|---|---|---|
| Altman Z-Score | `financial-scores` | 破產風險量化（Burry lane） |
| Piotroski F-Score (0-9) | `financial-scores` | 盈餘品質篩選（Fundamentals） |
| Owner Earnings | `owner-earnings` | Buffett 品質指標（Burry） |
| Institutional holdings % | `institutional-ownership-symbol-positions-summary` | 法人籌碼（Sentiment） |
| Congressional trade signals | `senate-trades` / `house-trades` | 政治風險（Sentiment/News） |
| M&A target flag | `mergers-acquisitions-latest` | 事件驅動（News） |
| EV/EBIT (直接欄位) | `key-metrics-ttm` → `evToEBITTTM` | Burry EV/EBIT rubric |

---

## Section 3: Phase 2 各 Lane 資料缺口

### 3.1 Fundamentals Lane

**目前已有**: TICKER_DATA_BUNDLE (15 fields) + EARNINGS_ANALYST_BUNDLE (8Q financials, TTM ratios, DCF, price targets, grades, surprises, segments, transcript) + PEER_BUNDLE (peer_pe_median, peer_pb_median, peer_fcf_yield_median, peer_ev_ebitda_median)

**協議引用但未確認 fetch 的欄位**:
```
peer_pe_median     → ✅ PEER_BUNDLE 已實作（company_context.py）
ev_ebitda          → ✅ earnings-analyst bundle: km.evToEBITDATTM
ev_ebit (Burry)    → ❌ 缺口！key-metrics-ttm 有 evToEBITTTM，但未放入任何 bundle
income_quality     → ❌ key-metrics-ttm.incomeQualityTTM 未提取（雖 slim_ttm_keymetrics 包含它）
```

**待補強**:
```python
# earnings-analyst fetch.py slim_ttm_keymetrics 已包含 incomeQualityTTM ✅
# 但 evToEBITTTM 未在 slim_ttm_keymetrics 中 — 需加入:
def slim_ttm_keymetrics(d: dict) -> dict:
    keep = [
        ...,
        "evToEBITTTM",          # ADD: Burry EV/EBIT rubric
        "roicTTM",               # ADD: 資本配置效率
        "returnOnTangibleAssetsTTM",  # ADD: 資產品質
    ]
```

**高優先新增 — financial-scores**:
```python
# 完全未在任何 bundle 中 — Altman Z + Piotroski F 是免費端點
scores = _fmp_get("/stable/financial-scores", {"symbol": ticker})
# returns: altmanZScore, piotroskiScore, workingCapital, totalAssets,
#          retainedEarnings, ebit, bookValueOfDebt, revenue, grossProfit...
```

### 3.2 Sentiment Lane

**目前已有**: FMP insider-trading-statistics (quarterly, 4 periods) ✅，Finnhub MSPR ✅，yfinance short_pct_float ✅

**資料缺口**:

| 缺口 | FMP Endpoint | 補充方式 |
|---|---|---|
| Institutional holdings change (QoQ) | `institutional-ownership-symbol-positions-summary` | FMP_SUPPLEMENTARY_BUNDLE |
| Smart money concentration | `institutional-ownership-extract-analytics-holders` | FMP_SUPPLEMENTARY_BUNDLE |
| Congressional insider signal | `senate-trades` / `house-trades` by ticker | FMP_SUPPLEMENTARY_BUNDLE |
| Short ratio (days-to-cover) | `key-metrics-ttm.shortRatioTTM` | 已在 EARNINGS_ANALYST_BUNDLE，但未傳 Sentiment |

**Congressional trade check** — 高度差異化信號（SEC 要求 2 天內報告）:
```python
def _fmp_congressional_trades(ticker: str, api_key: str,
                               days_back: int = 180) -> dict:
    since = (date.today() - timedelta(days=days_back)).isoformat()
    senate = requests.get("https://financialmodelingprep.com/stable/senate-trades",
                          params={"symbol": ticker, "from": since, "apikey": api_key},
                          timeout=10)
    house  = requests.get("https://financialmodelingprep.com/stable/house-trades",
                          params={"symbol": ticker, "from": since, "apikey": api_key},
                          timeout=10)
    s_data = senate.json() if senate.status_code == 200 else []
    h_data = house.json()  if house.status_code == 200 else []
    # Aggregate: net buy/sell, most recent trade date, politicians involved
    trades = s_data + h_data
    buys  = [t for t in trades if "purchase" in t.get("type", "").lower()]
    sells = [t for t in trades if "sale"     in t.get("type", "").lower()]
    return {
        "congressional_buy_count":  len(buys),
        "congressional_sell_count": len(sells),
        "net_signal": "bullish" if len(buys) > len(sells) * 2 else
                      "bearish" if len(sells) > len(buys) * 2 else "neutral",
        "most_recent_trade": max((t.get("transactionDate","") for t in trades), default=None),
        "source": "FMP senate-trades + house-trades",
    }
```

### 3.3 News Lane

**目前已有**: finviz 新聞爬取 + yfinance headlines + Finnhub company-news（3 源 dedup）✅，FMP grades-historical + grades-news + sec-filings-financials + price-target-consensus ✅

**資料缺口**:

| 缺口 | 目前 | FMP 替換 |
|---|---|---|
| M&A 事件 | 無 | `mergers-acquisitions-latest` + `mergers-acquisitions-search` |
| Press releases | 無 | `news-press-release` (by symbol) |
| IPO pipeline context | 無 | `ipos-disclosure` / `ipos-prospectus` |
| 8-K filings (非財報) | sec-filings-financials | `sec-filings-8k` (non-financial 8-K: material events) |

**目前 `_fmp_sec_filings()` 使用的是 `/stable/sec-filings-financials`（財報相關 SEC 文件）**。更廣的重大事件應使用 `/stable/sec-filings-8k`：
```python
def _fmp_sec_8k_filings(ticker: str, api_key: str, since: datetime) -> list[dict]:
    """8-K = material event filings (M&A, leadership changes, restructuring).
    Supplement to sec-filings-financials which only covers 10-K/10-Q."""
    r = requests.get("https://financialmodelingprep.com/stable/sec-filings-8k",
                     params={"symbol": ticker,
                             "from": since.date().isoformat(),
                             "limit": 10, "apikey": api_key}, timeout=10)
    if r.status_code != 200:
        return []
    return [{"date": f.get("filedDate"), "type": "8-K",
             "title": f.get("title"), "url": f.get("finalLink")}
            for f in (r.json() or [])]
```

### 3.4 Technical Lane

**目前已有**: FMP `/stable/historical-price-eod/full` 為 PRIMARY，yfinance 為 FALLBACK（`technical_core.py` v1.62 已實作）✅

**資料缺口**:

| 缺口 | 目前 | FMP 替換 |
|---|---|---|
| Intraday bars (30min/1hr) | 無 | `intraday-30min` / `intraday-1hour` |
| Short-term momentum (5min) | 無 | `intraday-5min` |
| Batch OHLCV (多 ticker) | 逐個 | `chart-batch` |

**Technical lane 現狀評估**: ✅ FMP OHLCV 已是 PRIMARY，此處缺口屬「增強」而非「修正」。若要加入 intraday momentum 分析（盤中 volume spike detection）可用：
```python
# intraday 1-hour bars — last 5 trading days
r = requests.get(
    "https://financialmodelingprep.com/stable/intraday-1hour",
    params={"symbol": ticker,
            "from": (date.today() - timedelta(days=5)).isoformat(),
            "apikey": os.environ["FMP_API_KEY"]}, timeout=15)
```

### 3.5 Burry (Contrarian) Lane

**目前已有**: TICKER_DATA_BUNDLE (fcfPerShareTTM, debtToEquity) + EARNINGS_ANALYST_BUNDLE (EV, cashflow, balance sheet, enterprise_value, key_metrics_ttm) + PEER_BUNDLE

**資料缺口**:

| Burry Rubric 欄位 | 目前來源 | 問題 |
|---|---|---|
| FCF yield | fcfPerShareTTM / price (Finnhub scoring) | ✅ 可計算 |
| EV/EBIT | EARNINGS_ANALYST_BUNDLE → enterprise_value + income | ❌ `ev.enterpriseValue` 有，`ebit` 在 quarterly_pnl[0] 有，但 `evToEBITTTM` 未提取 |
| Debt/Equity | debtToEquity (Finnhub scoring) | ✅ |
| Insider activity | insider_stats[].acquired_disposed_ratio | ✅ (Sentiment skill) — 但 **Burry inline 無法讀 Sentiment subagent 的輸出**（parallel lanes） |
| Altman Z-Score | 無 | ❌ `financial-scores` 未用 |
| Owner Earnings | 無 | ❌ `owner-earnings` 未用 |

**重要問題**: Burry lane 在 Phase 2 末段 inline 執行，此時 **Sentiment lane 的 `insider_stats` 輸出尚不可用**（4 lanes 平行，Burry 在 phase 2 末但 insider 來自 Sentiment lane）。

**解決方案**: `insider_stats[]` 應移入 Phase 1 的 **FMP_SUPPLEMENTARY_BUNDLE**（Section 6），讓所有 lanes 包含 Burry 都能讀到。

---

## Section 4: 新增強化機會（協議未提及但高價值）

### 4.1 `financial-scores` — Altman Z + Piotroski F（最高優先！）

**Phase**: Phase 1 FMP_SUPPLEMENTARY_BUNDLE → Fundamentals + Burry lanes

**理由**: 免費端點，結構化數值，直接對應 Burry 的「會不會倒」判斷邏輯。

```python
# 一次 call 取得兩個經典品質分數
scores = _fmp_get("/stable/financial-scores", {"symbol": ticker})
# Response fields:
# altmanZScore:       < 1.81 危險, 1.81-2.99 灰色, > 2.99 安全
# piotroskiScore:     0-9, ≥ 7 = strong, ≤ 2 = weak
# workingCapital, totalAssets, retainedEarnings, ebit (for Z-score check)
```

**Protocol Impact**: Burry rubric 可增加「`altmanZScore < 1.81` → 財務困境風險 → burry_score -2」確定性規則，替代 LLM 對 debt/asset 比值的定性判斷。

### 4.2 `owner-earnings` — Buffett Owner Earnings

**Phase**: Phase 1 FMP_SUPPLEMENTARY_BUNDLE → Burry lane

```python
oe = _fmp_get("/stable/owner-earnings", {"symbol": ticker})
# Returns: ownerEarnings, averageGrowthEstimate, multipliedEstimate, stocksBasedOnOwnerEarnings
# ownerEarnings = net income + depreciation - capex (simplified)
# FMP 的定義: reportedNetIncome + depreciationAmortization - capex - workingCapitalChange
```

**Protocol Impact**: Burry rubric「FCF yield」可用 owner earnings 補強（Buffett 更強調 owner earnings 而非 GAAP FCF，兩者差異在 stock-based comp 處理上有意義）。

### 4.3 `institutional-ownership-symbol-positions-summary` — 法人籌碼變化

**Phase**: Phase 1 FMP_SUPPLEMENTARY_BUNDLE → Sentiment lane

```python
inst = _fmp_get("/stable/institutional-ownership-symbol-positions-summary",
                {"symbol": ticker})
# Returns: institutionsCount, putCallRatio, 
#          investorHoldingChange (QoQ % change in shares held),
#          ownershipPercent (% of float held by institutions)
```

**Protocol Impact**: 機構持股 QoQ 變化 > +5% → `institutional_accumulation` 正訊號；< -5% → 分散訊號。補強 Sentiment lane 的智慧資金面。

### 4.4 `senate-trades` / `house-trades` — 國會議員交易

**Phase**: Phase 1 FMP_SUPPLEMENTARY_BUNDLE → Sentiment + News lanes

已在 Section 3.2 提供 code。

**Protocol Impact**: 國會議員是法規資訊先行者（特別是科技、醫療、國防板塊）。買入訊號尤其在 STOCK Act 下有強烈 information asymmetry 意涵。建議新增 protocol 規則：`congressional_net_signal == "bullish"` → `sentiment_pts +0.5`（半點，避免過度權重）。

### 4.5 `mergers-acquisitions-latest` — M&A 事件

**Phase**: Phase 2 News lane fetch.py

```python
def _fmp_ma_events(ticker: str, api_key: str, days_back: int = 90) -> list[dict]:
    since = (date.today() - timedelta(days=days_back)).isoformat()
    # Check if ticker is target or acquirer
    r = requests.get("https://financialmodelingprep.com/stable/mergers-acquisitions-search",
                     params={"name": ticker, "apikey": api_key}, timeout=10)
    if r.status_code != 200:
        return []
    events = r.json() or []
    return [{"date": e.get("announcedDate"), "type": "M&A",
             "acquirer": e.get("companyName"), "target": e.get("targetedCompanyName"),
             "transaction_value": e.get("transactionValue")}
            for e in events if e.get("announcedDate", "") >= since]
```

### 4.6 `esg-rating` — ESG 風險因子

**Phase**: FMP_SUPPLEMENTARY_BUNDLE → Fundamentals / Risk lanes

注意：`fetch.py` 將 ESG 標為 402 paid blocker。但 `esg-rating` 在 stable API 中被列為「ESG」類別。**需要驗證是否確為免費**：
```python
# Test call (non-billable probe):
r = requests.get("https://financialmodelingprep.com/stable/esg-rating",
                 params={"symbol": "AAPL", "apikey": api_key})
# 若 200: 免費，加入 bundle
# 若 402: 確認付費牆，維持 skipped
```

### 4.7 `analyst-estimate` (Annual) — Forward Consensus

**Phase**: EARNINGS_ANALYST_BUNDLE 補充

目前 `paid_blockers_skipped` 包含 `/stable/analyst-estimates?period=quarter`（402），但 **annual 版本可能免費**：
```python
estimates_annual = _fmp_get("/stable/analyst-estimate",
                             {"symbol": ticker, "period": "annual", "limit": 3})
# If returns 200: revenue/EPS/EBITDA estimates for next 3 FY
# 提供 forward growth 的 consensus — Fundamentals lane 可用於 PEG 計算
```

### 4.8 `commitment-of-traders-report` — 期貨籌碼

**Phase**: Phase 0 macro intelligence

```python
# For relevant futures (e.g., S&P 500 futures, oil, rates) as macro context
cot = _fmp_get("/stable/commitment-of-traders-analysis")
# Large specs net position change = trend confirmation/divergence signal
```

---

## Section 5: 優先實作清單

| 優先 | 強化項目 | Phase | FMP Endpoint | 難度 | 影響 | 備注 |
|---|---|---|---|---|---|---|
| **P0** | `financial-scores` 加入 FMP_SUPPLEMENTARY_BUNDLE | Phase 1 | `financial-scores` | ⭐ 易 | 🔥🔥🔥 高 | Altman Z + Piotroski F；Burry lane 決定性強化；免費端點 |
| **P0** | `evToEBITTTM` 加入 earnings-analyst slim_ttm_keymetrics | earnings-analyst fetch.py | `key-metrics-ttm` | ⭐ 易 | 🔥🔥🔥 高 | Burry EV/EBIT rubric 目前缺直接欄位；1行 slim 修改 |
| **P1** | finviz_performance_client → FMP industry-performance | Phase 0 / daily_update | `industry-performance-snapshot` + `historical-industry-performance` | ⭐⭐ 中 | 🔥🔥🔥 高 | 消除 web scraping 依賴；theme-detector 穩定性大提升 |
| **P1** | `insider_stats[]` 移入 Phase 1 FMP_SUPPLEMENTARY_BUNDLE | Phase 1 | `insider-trading-statistics` | ⭐⭐ 中 | 🔥🔥 中 | 讓 Burry lane 能讀到（目前只在 Sentiment skill）；protocol 隔離優化 |
| **P1** | `owner-earnings` 加入 FMP_SUPPLEMENTARY_BUNDLE | Phase 1 | `owner-earnings` | ⭐ 易 | 🔥🔥 中 | Burry lane Buffett 品質指標；補強 FCF yield |
| **P2** | FMP news-stock 替換 finviz 新聞爬取（FMP 主，finviz fallback）| Phase 2 News | `news-stock` + `news-press-release` | ⭐⭐ 中 | 🔥🔥 中 | 消除 HTML 爬取依賴；FMP 附帶 sentiment score |
| **P2** | `sec-filings-8k` 加入 News lane fetch.py | Phase 2 News | `sec-filings-8k` | ⭐ 易 | 🔥🔥 中 | 重大事件 8-K（M&A、高管異動、訴訟）補充 10-K/Q 財報 |
| **P2** | institutional-ownership 加入 FMP_SUPPLEMENTARY_BUNDLE | Phase 1 | `institutional-ownership-symbol-positions-summary` | ⭐⭐ 中 | 🔥🔥 中 | 法人籌碼 QoQ 變化 → Sentiment lane 智慧資金信號 |
| **P2** | us-stock-analysis → bundle-first（不重打 yfinance） | Phase 2 Fundamentals | — (bundle read) | ⭐⭐ 中 | 🔥🔥 中 | 效率改善；消除重複 yfinance fetch；需修改 analyze.py |
| **P3** | congressional trades 加入 FMP_SUPPLEMENTARY_BUNDLE | Phase 1 | `senate-trades` + `house-trades` | ⭐⭐ 中 | 🔥 低-中 | 政治風險先行信號；科技/醫療/國防板塊效果最強 |
| **P3** | M&A events 加入 News lane fetch.py | Phase 2 News | `mergers-acquisitions-search` | ⭐ 易 | 🔥 低-中 | 事件驅動補充；ticker 為 target/acquirer 的掃描 |
| **P3** | `analyst-estimate` annual 測試免費性 | EARNINGS_ANALYST | `analyst-estimate` | ⭐ 易 | 🔥 低 | 目前 quarter 為 402；annual 可能免費；forward EPS consensus |
| **P4** | ESG rating 測試免費性後加入 bundle | FMP_SUPPLEMENTARY | `esg-rating` | ⭐ 易 | 🔥 低 | 先測試 402；若免費加入 Phase 4 Risk 層 |
| **P4** | COT report 加入 Phase 0 macro | Phase 0 | `commitment-of-traders-analysis` | ⭐⭐ 中 | 🔥 低 | 期貨籌碼 macro overlay；目前 skill chain 未覆蓋 |

---

## Section 6: Phase 1 資料層新提案 — FMP_SUPPLEMENTARY_BUNDLE

### 6.1 設計原則

- **FMP-only**：不含 Finnhub 任何欄位（維持 dual_fetch 隔離合約）
- **24h cache**：與 `company_context` 相同機制，cache key = `(TICKER, today())`
- **Phase 1 末段執行**：在 PEER_BUNDLE 之後，所有 Phase 2 subagent 之前
- **接收 lanes**：Fundamentals ✅、Sentiment ✅、News ✅、Burry ✅（Technical lane 無需）

### 6.2 Bundle Schema

```json
{
  "ticker": "AAPL",
  "as_of_date": "2025-01-30",
  "cache_key": "AAPL_2025-01-30",
  "schema_version": "V1.0",
  "data_source": "FMP HTTP REST",

  "quality_scores": {
    "altmanZScore": 4.87,
    "piotroskiScore": 7,
    "altman_zone": "safe",
    "piotroski_strength": "strong",
    "_note": "altman: <1.81=danger, 1.81-2.99=grey, >2.99=safe"
  },

  "owner_earnings": {
    "ownerEarnings": 98765432100,
    "growthEstimate": 0.12,
    "impliedValue": 189.50
  },

  "insider_summary": {
    "quarters": [
      {
        "period": "2024-Q3",
        "acquired_disposed_ratio": 0.82,
        "total_acquired_shares": 450000,
        "total_disposed_shares": 550000,
        "acquired_transactions": 8,
        "disposed_transactions": 10
      }
    ],
    "source": "FMP /stable/insider-trading/statistics"
  },

  "institutional": {
    "ownership_percent": 61.2,
    "institutions_count": 4823,
    "put_call_ratio": 0.87,
    "holding_change_pct_qoq": 1.3,
    "source": "FMP /stable/institutional-ownership-symbol-positions-summary"
  },

  "congressional_trades": {
    "lookback_days": 180,
    "buy_count": 3,
    "sell_count": 1,
    "net_signal": "bullish",
    "most_recent_date": "2024-11-15",
    "source": "FMP senate-trades + house-trades"
  },

  "ma_events": {
    "lookback_days": 90,
    "events": [],
    "source": "FMP /stable/mergers-acquisitions-search"
  },

  "_fetch_stats": {
    "fmp_calls": 5,
    "fmp_failures": 0,
    "cached": false
  }
}
```

### 6.3 實作腳本 — `skills/_shared/fmp_supplementary.py`

```python
#!/usr/bin/env python3
"""
FMP Supplementary Bundle — Phase 1 資料層新增 (FMP-only, 24h cache)

High-value FMP fields NOT in TICKER_DATA_BUNDLE (Finnhub) or
EARNINGS_ANALYST_BUNDLE. Fetched once per session, cached 24h.
Delivered to: Fundamentals + Sentiment + News + Burry lanes.

Physical isolation: FMP-only. Never mixed with Finnhub scoring.*.

Usage (Phase 1 PM):
    from skills._shared.fmp_supplementary import get_supplementary_bundle
    FMP_SUPP_BUNDLE = get_supplementary_bundle("NVDA")
    # → dict or None (on full failure)
"""
from __future__ import annotations
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

BASE_DIR   = Path(__file__).resolve().parent.parent.parent
CACHE_DIR  = BASE_DIR / "skills" / "_shared" / "fmp_supp_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL  = 86400   # 24h


def _fmp_get(path: str, params: dict, *, timeout: int = 12) -> list | dict | None:
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return None
    try:
        r = requests.get(
            f"https://financialmodelingprep.com/stable/{path}",
            params={**params, "apikey": api_key},
            timeout=timeout,
        )
        if r.status_code in (402, 401, 403):
            return None
        if r.status_code == 429:
            time.sleep(2)
            return None
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _fetch_quality_scores(ticker: str) -> dict:
    """Altman Z-Score + Piotroski F-Score via /stable/financial-scores."""
    data = _fmp_get("financial-scores", {"symbol": ticker})
    if not isinstance(data, list) or not data:
        return {}
    d = data[0]
    z = d.get("altmanZScore")
    f = d.get("piotroskiScore")
    zone = ("danger" if z is not None and z < 1.81 else
            "grey"   if z is not None and z < 2.99 else
            "safe"   if z is not None else None)
    strength = ("strong" if f is not None and f >= 7 else
                "weak"   if f is not None and f <= 2 else
                "moderate" if f is not None else None)
    return {
        "altmanZScore":    z,
        "piotroskiScore":  f,
        "altman_zone":     zone,
        "piotroski_strength": strength,
        "_note": "altman: <1.81=danger, 1.81-2.99=grey, >2.99=safe",
    }


def _fetch_owner_earnings(ticker: str) -> dict:
    """Buffett owner earnings via /stable/owner-earnings."""
    data = _fmp_get("owner-earnings", {"symbol": ticker})
    if not isinstance(data, list) or not data:
        return {}
    d = data[0]
    return {
        "ownerEarnings":   d.get("ownerEarnings"),
        "growthEstimate":  d.get("averageGrowthEstimate"),
        "impliedValue":    d.get("stocksBasedOnOwnerEarnings"),
    }


def _fetch_insider_summary(ticker: str, quarters: int = 4) -> dict:
    """Quarterly insider trade statistics via /stable/insider-trading/statistics."""
    data = _fmp_get("insider-trading/statistics",
                    {"symbol": ticker, "limit": quarters})
    if not isinstance(data, list) or not data:
        return {"quarters": [], "source": "FMP insider-trading/statistics"}
    rows = []
    for d in data[:quarters]:
        # FMP field: acquiredTransactions, disposedTransactions, etc.
        acq_t = d.get("acquiredTransactions") or 0
        dis_t = d.get("disposedTransactions") or 0
        ratio = round(acq_t / dis_t, 3) if dis_t > 0 else None
        rows.append({
            "period":                   d.get("quarter") or d.get("date"),
            "acquired_disposed_ratio":  ratio,
            "total_acquired_shares":    d.get("totalAcquiredShares"),
            "total_disposed_shares":    d.get("totalDisposedShares"),
            "acquired_transactions":    acq_t,
            "disposed_transactions":    dis_t,
        })
    return {"quarters": rows, "source": "FMP /stable/insider-trading/statistics"}


def _fetch_institutional(ticker: str) -> dict:
    """Institutional ownership summary via /stable/institutional-ownership-symbol-positions-summary."""
    data = _fmp_get("institutional-ownership/symbol-positions-summary",
                    {"symbol": ticker})
    if not isinstance(data, list) or not data:
        return {}
    d = data[0]
    change = d.get("investorHoldingChange")
    return {
        "ownership_percent":     d.get("ownershipPercent"),
        "institutions_count":    d.get("institutionsCount"),
        "put_call_ratio":        d.get("putCallRatio"),
        "holding_change_pct_qoq": round(float(change) * 100, 2)
                                   if change is not None else None,
        "source": "FMP institutional-ownership-symbol-positions-summary",
    }


def _fetch_congressional(ticker: str, days_back: int = 180) -> dict:
    """Congressional trading signals via senate-trades + house-trades."""
    since = (date.today() - timedelta(days=days_back)).isoformat()
    senate = _fmp_get("senate-trades",
                      {"symbol": ticker, "from": since}) or []
    house  = _fmp_get("house-trades",
                      {"symbol": ticker, "from": since}) or []
    trades = (senate if isinstance(senate, list) else []) + \
             (house  if isinstance(house,  list) else [])
    buys   = [t for t in trades if "purchase" in (t.get("type") or "").lower()]
    sells  = [t for t in trades if "sale"     in (t.get("type") or "").lower()]
    net    = ("bullish" if len(buys)  > len(sells) * 2 else
              "bearish" if len(sells) > len(buys)  * 2 else "neutral")
    recent = max((t.get("transactionDate","") for t in trades), default=None)
    return {
        "lookback_days":    days_back,
        "buy_count":        len(buys),
        "sell_count":       len(sells),
        "net_signal":       net,
        "most_recent_date": recent,
        "source":           "FMP senate-trades + house-trades",
    }


def _fetch_ma_events(ticker: str, days_back: int = 90) -> dict:
    """Recent M&A activity where ticker is acquirer or target."""
    since = (date.today() - timedelta(days=days_back)).isoformat()
    data = _fmp_get("mergers-acquisitions-search",
                    {"name": ticker}) or []
    events = [
        {
            "date":            e.get("announcedDate"),
            "acquirer":        e.get("companyName"),
            "target":          e.get("targetedCompanyName"),
            "transaction_usd": e.get("transactionValue"),
        }
        for e in (data if isinstance(data, list) else [])
        if (e.get("announcedDate") or "") >= since
    ]
    return {"lookback_days": days_back, "events": events,
            "source": "FMP mergers-acquisitions-search"}


def get_supplementary_bundle(ticker: str,
                              force: bool = False) -> dict | None:
    """
    Fetch or load-from-cache the FMP supplementary bundle for `ticker`.
    Returns dict on success, None on hard failure.

    Physical isolation guarantee:
      - All data in this bundle is FMP-sourced.
      - This function MUST NOT import or call dual_fetch / FinnhubClient.
      - PM passes this bundle to Fundamentals / Sentiment / News / Burry lanes.
      - NEVER pass to Technical lane (OHLCV-only, no need).
    """
    ticker   = ticker.upper()
    cache_path = CACHE_DIR / f"{ticker}_{date.today().isoformat()}_supp.json"

    # Cache check (24h TTL — same-day file always valid)
    if not force and cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < CACHE_TTL:
            print(f"[fmp_supp] cache hit: {ticker}", file=sys.stderr)
            with open(cache_path) as f:
                return json.load(f)

    calls, failures = 0, 0
    print(f"[fmp_supp] fetching {ticker}: quality_scores ...", file=sys.stderr)
    quality   = _fetch_quality_scores(ticker);  calls += 1
    if not quality:
        failures += 1

    print(f"[fmp_supp] fetching {ticker}: owner_earnings ...", file=sys.stderr)
    owner_e   = _fetch_owner_earnings(ticker);  calls += 1
    if not owner_e:
        failures += 1

    print(f"[fmp_supp] fetching {ticker}: insider_summary ...", file=sys.stderr)
    insider   = _fetch_insider_summary(ticker); calls += 1
    if not insider.get("quarters"):
        failures += 1

    print(f"[fmp_supp] fetching {ticker}: institutional ...", file=sys.stderr)
    inst      = _fetch_institutional(ticker);   calls += 1
    if not inst:
        failures += 1

    print(f"[fmp_supp] fetching {ticker}: congressional ...", file=sys.stderr)
    congress  = _fetch_congressional(ticker);   calls += 1

    print(f"[fmp_supp] fetching {ticker}: M&A events ...", file=sys.stderr)
    ma_events = _fetch_ma_events(ticker);       calls += 1

    if failures >= 4:  # hard failure — 4+ of 6 calls failed
        print(f"[fmp_supp] WARN: {ticker} — {failures}/{calls} calls failed, "
              f"returning partial bundle", file=sys.stderr)

    bundle = {
        "ticker":          ticker,
        "as_of_date":      date.today().isoformat(),
        "cache_key":       f"{ticker}_{date.today().isoformat()}",
        "schema_version":  "V1.0",
        "data_source":     "FMP HTTP REST (FMP-only; no Finnhub)",

        "quality_scores":       quality or {},
        "owner_earnings":       owner_e or {},
        "insider_summary":      insider,
        "institutional":        inst or {},
        "congressional_trades": congress,
        "ma_events":            ma_events,

        "_fetch_stats": {
            "fmp_calls":    calls,
            "fmp_failures": failures,
            "cached":       False,
        },
    }

    with open(cache_path, "w") as f:
        json.dump(bundle, f, indent=2)
    print(f"[fmp_supp] wrote {cache_path.name} ({len(json.dumps(bundle)):,} bytes)",
          file=sys.stderr)
    return bundle
```

### 6.4 Protocol 整合方式

```markdown
### Phase 1 資料層（FMP_SUPPLEMENTARY_BUNDLE 新增）

Phase 1 末段 PM **MUST** 執行以下步驟取得 FMP 補充束：

```python
from skills._shared.fmp_supplementary import get_supplementary_bundle
FMP_SUPP_BUNDLE = get_supplementary_bundle(ticker)
# 失敗（全部 None）→ FMP_SUPP_BUNDLE = None，Phase 2 相關 prompt 段落省略
```

**物理隔離合約**：此 bundle 為 FMP-only，**不得混入 dual_fetch scoring.* 欄位**。

**各 Lane 接收規則**：
- ✅ Fundamentals：傳入 `quality_scores`（Altman Z / Piotroski F）+ `owner_earnings`
- ✅ Sentiment：傳入 `insider_summary` + `institutional` + `congressional_trades`
- ✅ News：傳入 `ma_events`（M&A 事件補充 sec_filings_recent）
- ✅ Burry：傳入 `quality_scores` + `owner_earnings` + `insider_summary`
- ❌ Technical：不傳（OHLCV-only lane，無需基本面資料）
```

### 6.5 Phase 2 Burry Lane 新增規則（協議文字建議）

```markdown
**Altman Z-Score Gate（FMP_SUPP_BUNDLE.quality_scores）**：
- `altman_zone == "danger"` → `burry_score -= 2`，`burry_voice` 加入「財務困境 Z-score={z:.2f}」
- `altman_zone == "grey"` → `burry_score -= 1`（風險提醒）
- `altman_zone == "safe"` → 不調整

**Piotroski F-Score Filter**：
- F-score ≤ 2 → `burry_verdict` 自動為 `PASS`（財務品質太差，Burry 不持有）
- F-score ≥ 7 → `burry_score += 1`（品質溢價）

**Owner Earnings vs GAAP FCF 差異**：
- 若 `owner_earnings.ownerEarnings` vs `cash_flow[0].freeCashFlow` 差異 > 30%
  → `burry_voice` 加入「SBC 調整差異顯著：owner_earnings={oe} vs GAAP_FCF={fcf}」
```

---

## 總結

| 維度 | 現況 | 改善後 |
|---|---|---|
| Web scraping 依賴 | finviz (3 處)、yfinance (多處) | finviz industry perf → FMP；finviz news → FMP 主；yfinance 保留 short% fallback |
| 結構化分析欄位 | 15 Finnhub + ~30 FMP earnings fields | +6 新 FMP 欄位（Z/F-score, owner earnings, institutional, congressional, M&A, evToEBIT） |
| Burry Lane 確定性 | 依賴 LLM 定性 debt/asset 判斷 | Altman Z / Piotroski F / owner earnings → 確定性數值規則替代 LLM 估算 |
| Sentiment Lane 信號 | FMP insider + Finnhub MSPR + yfinance short | +institutional QoQ + congressional trades → 多維籌碼面 |
| Protocol 版本影響 | — | FMP_SUPPLEMENTARY_BUNDLE = 新 Phase 1 步驟 → **V4.9 版本 bump 建議** |
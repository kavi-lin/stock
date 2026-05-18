# FMP MCP Tools 中文參考

> **來源**：透過 Claude Code MCP 連線取得（`mcp list` ✓ Connected）
> **連線 URL**：`https://financialmodelingprep.com/mcp?apikey=$FMP_API_KEY`
> **生成日期**：2026-05-03
> **總計**：27 個 tool / ~230 個 endpoint

---

## 使用方式

LLM 對話中直接呼叫 `mcp__fmp__<tool>` 並指定 `endpoint` 參數：

```
mcp__fmp__quote(endpoint="quote", symbol="AAPL")
mcp__fmp__statements(endpoint="income-statement", symbol="AAPL", period="annual", limit=8)
mcp__fmp__news(endpoint="general-news", limit=20)
```

> ⚠️ Python 腳本**不能**直接呼叫 MCP；要從腳本拿同樣資料請走 HTTP REST（見 `FMP_API_中文參考.md`）。
> ⚠️ 每個 endpoint 都吃既有 FMP API quota（不需另外計費）。
> ⚠️ Free tier 部分 endpoint 會回 402（需付費）— 標記在「付費」欄；未標即 free 可用。

---

## 工具分類目錄（27 tools）

| # | Tool | Endpoint 數 | 主要用途 |
|---|---|---|---|
| 1 | [`quote`](#1-quote--即時報價) | 16 | 即時 / 盤後 / 全市場批次報價 |
| 2 | [`search`](#2-search--搜尋與篩選) | 7 | 代號/名稱/CIK/ISIN 查找 + 多維 stock screener |
| 3 | [`company`](#3-company--公司基本資料) | 17 | profile / executives / market cap / M&A / peers |
| 4 | [`directory`](#4-directory--清單與目錄) | 11 | 全市場 ETFs / actively trading / 國家/交易所/行業清單 |
| 5 | [`statements`](#5-statements--財務報表) | 27 | 三表（IS/BS/CF）+ TTM + growth + key metrics + ratios + DCF prep |
| 6 | [`analyst`](#6-analyst--分析師) | 8 | grades / ratings snapshot / price target / EPS estimates |
| 7 | [`news`](#7-news--新聞) | 10 | 一般新聞 / 個股 / 加密 / 外匯 / 新聞稿 / FMP 文章 |
| 8 | [`chart`](#8-chart--k-線圖表) | 10 | EOD（4 種調整方式）+ intraday（1m / 5m / 15m / 30m / 1h / 4h） |
| 9 | [`calendar`](#9-calendar--行事曆) | 9 | 財報 / 配息 / IPO / 拆股 |
| 10 | [`economics`](#10-economics--總體經濟) | 4 | economic calendar / GDP/CPI 等 indicator / treasury rates / 風險溢酬 |
| 11 | [`technicalIndicators`](#11-technicalindicators--技術指標) | 9 | SMA/EMA/DEMA/TEMA/WMA/RSI/ADX/Williams%R/StdDev |
| 12 | [`earningsTranscript`](#12-earningstranscript--財報電話會議) | 4 | 全文 transcript + 可用清單 |
| 13 | [`insiderTrades`](#13-insidertrades--內部人交易) | 6 | Form 4 + 統計 + acquisition ownership |
| 14 | [`senate`](#14-senate--國會交易) | 6 | Senate / House STOCK Act 揭露 |
| 15 | [`form13F`](#15-form13f--13f-機構持倉) | 8 | 13F filings extract + 機構績效 + 行業分布 |
| 16 | [`secFilings`](#16-secfilings--sec-文件) | 12 | 8-K / 10-K / 任意 form type + SIC 行業分類 |
| 17 | [`discountedCashFlow`](#17-discountedcashflow--dcf-估值) | 4 | 標準/槓桿 DCF + 自訂參數版 |
| 18 | [`etfAndMutualFunds`](#18-etfandmutualfunds--etf-與共同基金) | 9 | holdings / 行業 / 國家 / 資產配置 |
| 19 | [`indexes`](#19-indexes--股市指數) | 15 | S&P 500 / Nasdaq / Dow + EOD + intraday |
| 20 | [`marketPerformance`](#20-marketperformance--市場表現) | 11 | gainers/losers/most active + 行業/產業 PE 與 performance |
| 21 | [`marketHours`](#21-markethours--交易時段) | 3 | exchange hours + 假期 |
| 22 | [`crypto`](#22-crypto--加密貨幣) | 9 | crypto quote + EOD + intraday |
| 23 | [`forex`](#23-forex--外匯) | 9 | currency pair + EOD + intraday |
| 24 | [`commodity`](#24-commodity--商品) | 9 | commodity quote + EOD + intraday |
| 25 | [`ESG`](#25-esg--esg-評級) | 3 | ESG ratings + benchmark |
| 26 | [`commitmentOfTraders`](#26-commitmentoftraders--cot-持倉報告) | 3 | CFTC COT report |
| 27 | [`Fundraisers`](#27-fundraisers--群眾募資與股權融資) | 6 | crowdfunding + equity offering（小型公司 SEC filings） |

---

## 1. `quote` — 即時報價

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `quote` | symbol | 個股完整即時報價（價格、成交量、52w high/low、market cap、PE、EPS） |
| `quote-short` | symbol | 簡版報價（price / change / volume） |
| `quote-change` | symbol | 多週期漲跌幅（1D/5D/1M/3M/6M/YTD/1Y/3Y/5Y/10Y） |
| `batch-quote` | symbols[] | 批次完整報價（多 ticker 一次拉） |
| `batch-quote-short` | symbols[] | 批次簡版報價 |
| `aftermarket-quote` | symbol | 盤後報價 |
| `aftermarket-trade` | symbol | 盤後成交明細 |
| `batch-aftermarket-quote` | symbols[] | 批次盤後報價 |
| `batch-aftermarket-trade` | symbols[] | 批次盤後成交 |
| `full-exchange-quotes` | exchange | 整個交易所所有股票即時報價（如 NASDAQ / NYSE） |
| `full-etf-quotes` | — | 全市場所有 ETF 即時報價 |
| `full-mutualfund-quotes` | — | 全市場所有共同基金即時報價 |
| `full-index-quotes` | — | 全部指數即時報價（含全球） |
| `full-commodities-quotes` | — | 全部商品即時報價 |
| `full-cryptocurrency-quotes` | — | 全部加密貨幣即時報價 |
| `full-forex-quotes` | — | 全部外匯對即時報價 |

---

## 2. `search` — 搜尋與篩選

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `search-symbol` | query | 模糊搜尋 ticker（部分代號比對） |
| `search-name` | query | 公司名稱搜尋（中英皆可） |
| `search-CIK` | cik | 用 SEC CIK 編號反查公司 |
| `search-ISIN` | isin | 用 ISIN 國際證券編碼反查 |
| `search-cusip` | cusip | 用 CUSIP（北美證券編碼）反查 |
| `search-exchange-variants` | symbol | 同一公司在各交易所的不同代號（ADR/雙重上市） |
| `search-company-screener` | （多重 filter）| **Stock Screener** — marketCap / price / beta / dividend / volume / sector / industry / country / isEtf / isFund 多維篩選 |

---

## 3. `company` — 公司基本資料

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `profile-symbol` | symbol | 公司全資料（行業、員工數、CEO、市值、IPO 日、總部、官網、描述） |
| `profile-cik` | cik | 同上但用 CIK 查 |
| `market-cap` | symbol | 當前 market cap |
| `historical-market-cap` | symbol | 歷史 market cap 序列 |
| `batch-market-cap` | symbols[] | 批次拉多家市值 |
| `shares-float` | symbol | 流通股數 + 流動性指標 |
| `all-shares-float` | — | 全市場流通股數清單 |
| `company-executives` | symbol | 高管名單（職位、年薪、股權） |
| `executive-compensation` | symbol | 高管薪酬細項（base / bonus / stock awards / 總額） |
| `executive-compensation-benchmark` | year | 高管薪酬同業比較基準 |
| `employee-count` | symbol | 當前員工數 |
| `historical-employee-count` | symbol | 歷年員工數變化（年度） |
| `peers` | symbol | 同業競爭對手清單（FMP 自動分群） |
| `company-notes` | symbol | 公司債券發行紀錄（notes/bonds） |
| `latest-mergers-acquisitions` | — | 最新 M&A 公告 |
| `search-mergers-acquisitions` | name | M&A 名稱搜尋 |
| `delisted-companies` | — | 下市公司清單 |

---

## 4. `directory` — 清單與目錄

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `company-symbols-list` | — | 全市場 company ticker 清單 |
| `financial-symbols-list` | — | 有財報資料的 ticker 清單 |
| `ETFs-list` | — | 全部 ETF 清單 |
| `actively-trading-list` | — | 目前活躍交易的 ticker（過濾下市/暫停交易） |
| `cik-list` | — | 全部 CIK 清單 |
| `earnings-transcript-list` | — | 有財報電話會議紀錄的 ticker 清單 |
| `symbol-changes-list` | — | ticker 改名/合併紀錄 |
| `available-countries` | — | FMP 涵蓋的國家清單 |
| `available-exchanges` | — | 涵蓋的交易所清單 |
| `available-industries` | — | GICS 行業清單 |
| `available-sectors` | — | 11 大 GICS 部門清單 |

---

## 5. `statements` — 財務報表

> 大多 endpoint 接受 `period: annual | quarter` + `limit`（季數/年數）。

### 三大表（標準版）

| Endpoint | 說明 |
|---|---|
| `income-statement` | 損益表（Revenue → Net Income） |
| `balance-sheet-statement` | 資產負債表 |
| `cashflow-statement` | 現金流量表 |
| `latest-financial-statements` | 最新一期所有公司財報 |

### TTM（過去 12 個月滾動）

| Endpoint | 說明 |
|---|---|
| `income-statements-ttm` | TTM 損益表 |
| `balance-sheet-statements-ttm` | TTM 資產負債表 |
| `cashflow-statements-ttm` | TTM 現金流量表 |

### Growth（YoY 成長率）

| Endpoint | 說明 |
|---|---|
| `income-statement-growth` | 損益表各項 YoY 成長率 |
| `balance-sheet-statement-growth` | 資產負債表 YoY |
| `cashflow-statement-growth` | 現金流 YoY |
| `financial-statement-growth` | 三表合一成長率總表 |

### As-Reported（原始 SEC 申報版本）

| Endpoint | 說明 |
|---|---|
| `as-reported-income-statements` | 原始損益表（未經 FMP 標準化） |
| `as-reported-balance-statements` | 原始 BS |
| `as-reported-cashflow-statements` | 原始 CF |
| `as-reported-financial-statements` | 三表合一（原始） |

### 估值與比率

| Endpoint | 說明 |
|---|---|
| `key-metrics` | 關鍵指標（每股、ROE、ROIC、EBITDA、free cash flow yield 等 60+ 欄位） |
| `key-metrics-ttm` | TTM 版 |
| `metrics-ratios` | 財務比率（流動比、速動比、debt-to-equity、毛利率、ROA 等） |
| `metrics-ratios-ttm` | TTM 比率 |
| `financial-scores` | FMP 自家 financial health score（Altman Z / Piotroski F 等） |
| `enterprise-values` | 企業價值（EV）+ EV/EBITDA / EV/Sales |
| `owner-earnings` | Buffett 式 owner earnings（CFO − maintenance capex） |

### 營收細分

| Endpoint | 說明 |
|---|---|
| `revenue-geographic-segments` | 地理別營收（依國家/地區） |
| `revenue-product-segmentation` | 產品線營收細分 |

### 10-K 全文

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `financial-reports-dates` | symbol | 可用 10-K 申報日期清單 |
| `financial-reports-form-10-k-json` | symbol, year, period | 10-K 全文 JSON 結構化版本 |
| `financial-reports-form-10-k-xlsx` | symbol, year, period | 10-K 全文 Excel 下載 |

---

## 6. `analyst` — 分析師

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `ratings-snapshot` | symbol | 當前綜合評等快照（買進/持有/賣出 比例 + 綜合評分 0-5） |
| `historical-ratings` | symbol | 歷史評等時序 |
| `grades` | symbol | 個別機構評等紀錄（Goldman / JPM 等各家） |
| `historical-grades` | symbol | 歷史評等調整全紀錄（升/降評日期） |
| `grades-summary` | symbol | 評等摘要（強買/買/持有/賣/強賣 數量） |
| `price-target-summary` | symbol | 目標價摘要（high/low/mean/median） |
| `price-target-consensus` | symbol | 目標價共識（加權平均） |
| `financial-estimates` | symbol, period | EPS / 營收 估計值（含 forward 數季） |

---

## 7. `news` — 新聞

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `general-news` | （from/to/limit） | 一般市場新聞（不綁特定 ticker — 適合做 narrative 補位） |
| `stock-news` | （from/to/limit） | 全市場個股新聞（最新優先） |
| `search-stock-news` | symbols[] | 指定 ticker 個股新聞（時間區間） |
| `press-releases` | （from/to/limit）| 全市場新聞稿 |
| `search-press-releases` | symbols[] | 指定 ticker 新聞稿 |
| `crypto-news` | — | 加密貨幣新聞 |
| `search-crypto-news` | symbols[] | 指定 crypto symbol 新聞 |
| `forex-news` | — | 外匯新聞 |
| `search-forex-news` | symbols[] | 指定 forex pair 新聞 |
| `fmp-articles` | — | FMP 自家分析文章 |

---

## 8. `chart` — K 線圖表

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `historical-price-eod-light` | symbol | EOD 輕量版（date / price / volume，最常用） |
| `historical-price-eod-full` | symbol | EOD 完整版（含 open/high/low/close/adjClose/change） |
| `historical-price-eod-dividend-adjusted` | symbol | 配息調整後價格（total return 序列） |
| `historical-price-eod-non-split-adjusted` | symbol | 未經拆股調整的原始價（少用，研究 split 情境用） |
| `intraday-1-min` | symbol | 1 分 K 線（含 from/to） |
| `intraday-5-min` | symbol | 5 分 K |
| `intraday-15-min` | symbol | 15 分 K |
| `intraday-30-min` | symbol | 30 分 K |
| `intraday-1-hour` | symbol | 1 小時 K |
| `intraday-4-hour` | symbol | 4 小時 K |

---

## 9. `calendar` — 行事曆

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `earnings-calendar` | （from/to）| 全市場財報日曆（含 EPS estimate / 盤前盤後） |
| `earnings-company` | symbol | 個股歷年財報紀錄 |
| `dividends-calendar` | （from/to）| 配息日曆（除息日 / 配息日 / 金額） |
| `dividends-company` | symbol | 個股配息歷史 |
| `ipos-calendar` | （from/to）| IPO 日曆 |
| `ipos-disclosure` | — | IPO 揭露文件清單 |
| `ipos-prospectus` | — | IPO 招股書清單 |
| `splits-calendar` | （from/to）| 拆股日曆 |
| `splits-company` | symbol | 個股拆股歷史 |

---

## 10. `economics` — 總體經濟

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `economics-calendar` | （from/to）| 經濟事件日曆（FOMC / CPI / NFP / GDP / PMI / unemployment 等） |
| `economics-indicators` | name | 個別指標時序（如 `name=GDP` / `CPI` / `unemploymentRate`） |
| `treasury-rates` | （from/to）| 美國公債殖利率曲線（1M / 3M / 6M / 1Y / 2Y / 5Y / 10Y / 20Y / 30Y） |
| `market-risk-premium` | country | 市場風險溢酬（DCF cost of equity 用） |

---

## 11. `technicalIndicators` — 技術指標

> 共用參數：`symbol` + `periodLength`（如 14 / 20 / 50） + `timeframe`（1min / 5min / 15min / 30min / 1hour / 4hour / daily）

| Endpoint | 說明 |
|---|---|
| `simple-moving-average` | SMA 簡單移動平均 |
| `exponential-moving-average` | EMA 指數移動平均 |
| `weighted-moving-average` | WMA 加權移動平均 |
| `double-exponential-moving-average` | DEMA |
| `triple-exponential-moving-average` | TEMA |
| `relative-strength-index` | RSI 相對強弱指標（超買 70 / 超賣 30） |
| `average-directional-index` | ADX 趨勢強度 |
| `williams` | Williams %R |
| `standard-deviation` | 標準差（波動率測量） |

---

## 12. `earningsTranscript` — 財報電話會議

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `search-transcripts` | symbol, year, quarter | 取出該季財報電話會議全文逐字稿 |
| `transcripts-dates-by-symbol` | symbol | 個股可用 transcript 季度清單 |
| `latest-transcripts` | — | 最新財報會議全市場 |
| `available-transcript-symbols` | — | 有 transcript 的 ticker 清單 |

---

## 13. `insiderTrades` — 內部人交易

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `latest-insider-trade` | — | 最新 Form 4 申報（全市場） |
| `search-insider-trades` | （symbol/cik/transactionType filter）| 自訂條件搜尋 |
| `search-reporting-name` | name | 用內部人姓名查交易（如 "Elon Musk"） |
| `insider-trade-statistics` | symbol | 個股內部人交易統計（買賣比、季度趨勢） |
| `acquisition-ownership` | symbol | 持股 5% 以上的大股東變化（13D/13G） |
| `all-transaction-types` | — | 所有交易類型代碼參考表 |

---

## 14. `senate` — 國會交易（STOCK Act）

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `senate-latest` | — | 最新參議員財務揭露（Periodic Transaction Report） |
| `senate-trading` | symbol | 該股票被哪些參議員交易過 |
| `senate-trading-by-name` | name | 用參議員姓名查（如 `name="Pelosi"` 是 House，這裡是 Senate） |
| `house-latest` | — | 最新眾議員財務揭露 |
| `house-trading` | symbol | 該股票被哪些眾議員交易過 |
| `house-trading-by-name` | name | 用眾議員姓名查 |

---

## 15. `form13F` — 13F 機構持倉

> ⚠️ 部分 endpoint 在 free tier 可能 402（如 `industry-summary`）— 看現場回應為準。

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `latest-filings` | — | 最新 13F 申報清單 |
| `form-13f-filings-dates` | cik | 該機構（依 CIK）的歷史 13F 申報日期 |
| `filings-extract` | cik, year, quarter | 該機構該季完整持倉明細 |
| `filings-extract-with-analytics-by-holder` | symbol, year, quarter | 個股被哪些 13F holder 持有（含 analytics） |
| `positions-summary` | symbol, year, quarter | 個股機構持股摘要（持倉、變化） |
| `holder-performance-summary` | cik | 該機構歷史績效摘要 |
| `holders-industry-breakdown` | cik, year, quarter | 該機構持倉的行業分布 |
| `industry-summary` | year, quarter | 整個行業的 13F 持倉摘要（**可能付費**） |

---

## 16. `secFilings` — SEC 文件

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `8k-latest` | — | 最新 8-K（重大事件） |
| `financials-latest` | — | 最新財務 SEC filings |
| `search-by-symbol` | symbol | 個股全部 SEC filings |
| `search-by-cik` | cik | 用 CIK 查 |
| `search-by-form-type` | formType | 依表單類型篩選（10-K / 10-Q / S-1 / DEF 14A 等） |
| `search-by-name` | company | 用公司名稱搜尋 |
| `company-search-by-symbol` | symbol | 公司 SEC profile |
| `company-search-by-cik` | cik | 同上但用 CIK |
| `sec-company-full-profile` | symbol | 公司完整 SEC 資料（CIK / SIC / 註冊地） |
| `industry-classification-list` | — | SIC 行業分類清單 |
| `industry-classification-search` | （sicCode / industryTitle）| SIC 代碼/名稱搜尋 |
| `all-industry-classification` | — | 全部 industry classification |

---

## 17. `discountedCashFlow` — DCF 估值

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `dcf-advanced` | symbol | 標準 DCF 估值（FMP 預設假設） |
| `dcf-levered` | symbol | 槓桿 DCF（含負債） |
| `custom-dcf-advanced` | symbol + 多個 % 假設 | 自訂成長率 / WACC / tax rate / capex% / D&A% 等 |
| `custom-dcf-levered` | symbol + 多個 % 假設 | 自訂版槓桿 DCF |

> 自訂 DCF 可調參數：`revenueGrowthPct` / `ebitdaPct` / `ebitPct` / `taxRate` / `longTermGrowthRate` / `costOfDebt` / `costOfEquity` / `marketRiskPremium` / `beta` / `riskFreeRate` / `capitalExpenditurePct` / `depreciationAndAmortizationPct` / `operatingCashFlowPct` / `sellingGeneralAndAdministrativeExpensesPct` / `cashAndShortTermInvestmentsPct` / `receivablesPct` / `inventoriesPct` / `payablePct`

---

## 18. `etfAndMutualFunds` — ETF 與共同基金

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `holdings` | symbol | ETF/基金成分股與權重 |
| `sector-weighting` | symbol | 11 大 GICS 部門配置權重 |
| `country-weighting` | symbol | 國家別配置權重 |
| `etf-asset-exposure` | symbol | 資產類別配置（股/債/現金/其他 %） |
| `information` | symbol | 基金 factsheet（費率 / AUM / 追蹤指數） |
| `latest-disclosures` | symbol | 最新揭露文件 |
| `disclosures-dates` | symbol | 可用揭露日期清單 |
| `disclosures-name-search` | name | 用基金名稱搜尋揭露 |
| `mutual-fund-disclosures` | symbol, year, quarter | 共同基金特定季度持倉 |

---

## 19. `indexes` — 股市指數

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `indexes-list` | — | 所有可用指數清單 |
| `index-quote` | symbol | 指數即時報價 |
| `index-quote-short` | symbol | 簡版指數報價 |
| `all-index-quotes` | — | 全部指數一次拉 |
| `sp-500` | — | S&P 500 當前成分股 |
| `historical-sp-500` | — | S&P 500 歷史成分股變動 |
| `nasdaq` | — | Nasdaq 100 當前成分股 |
| `historical-nasdaq` | — | Nasdaq 100 歷史成分股 |
| `dow-jones` | — | Dow Jones 30 當前成分股 |
| `historical-dow-jones` | — | Dow Jones 30 歷史成分股 |
| `index-historical-price-eod-light` | symbol | 指數 EOD 輕量版 |
| `index-historical-price-eod-full` | symbol | 指數 EOD 完整版 |
| `index-intraday-1-min` | symbol | 指數 1m K |
| `index-intraday-5-min` | symbol | 指數 5m K |
| `index-intraday-1-hour` | symbol | 指數 1h K |

---

## 20. `marketPerformance` — 市場表現

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `biggest-gainers` | — | 當日漲幅最大 |
| `biggest-losers` | — | 當日跌幅最大 |
| `most-active` | — | 當日成交量最大 |
| `sector-performance-snapshot` | date | 11 大部門當日漲跌幅快照 |
| `historical-sector-performance` | sector | 個別部門歷史報酬時序 |
| `industry-performance-snapshot` | date | 行業層級漲跌快照 |
| `historical-industry-performance` | industry | 個別行業歷史報酬 |
| `sector-PE-snapshot` | date | 11 大部門當前 P/E |
| `historical-sector-pe` | sector | 個別部門歷史 P/E（**現用：sector_valuation**） |
| `industry-PE-snapshot` | date | 行業層級 P/E |
| `historical-industry-pe` | industry | 個別行業歷史 P/E |

---

## 21. `marketHours` — 交易時段

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `exchange-market-hours` | exchange | 個別交易所交易時段 + 當前 status（開市/休市） |
| `all-exchange-market-hours` | — | 全球交易所一次拉 |
| `holidays-by-exchange` | exchange | 交易所假期清單 |

---

## 22. `crypto` — 加密貨幣

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `cryptocurrency-list` | — | 全部 crypto symbol 清單 |
| `cryptocurrency-quote` | symbol | 完整即時報價 |
| `cryptocurrency-quote-short` | symbol | 簡版報價 |
| `all-cryptocurrency-quotes` | — | 批次全部 crypto |
| `cryptocurrency-historical-price-eod-light` | symbol | EOD 輕量 |
| `cryptocurrency-historical-price-eod-full` | symbol | EOD 完整 |
| `cryptocurrency-intraday-1-min` | symbol | 1m K |
| `cryptocurrency-intraday-5-min` | symbol | 5m K |
| `cryptocurrency-intraday-1-hour` | symbol | 1h K |

---

## 23. `forex` — 外匯

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `forex-list` | — | 全部外匯對清單 |
| `forex-quote` | symbol | 即時報價（如 `EURUSD`） |
| `forex-quote-short` | symbol | 簡版 |
| `all-forex-quotes` | — | 全部外匯一次拉 |
| `forex-historical-price-eod-light` | symbol | EOD 輕量 |
| `forex-historical-price-eod-full` | symbol | EOD 完整 |
| `forex-intraday-1-min` | symbol | 1m |
| `forex-intraday-5-min` | symbol | 5m |
| `forex-intraday-1-hour` | symbol | 1h |

---

## 24. `commodity` — 商品

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `commodities-list` | — | 商品清單（金/銀/原油/天然氣/小麥/玉米...） |
| `commodities-quote` | symbol | 即時報價 |
| `commodities-quote-short` | symbol | 簡版 |
| `all-commodities-quotes` | — | 全部商品一次拉 |
| `commodities-historical-price-eod-light` | symbol | EOD 輕量 |
| `commodities-historical-price-eod-full` | symbol | EOD 完整 |
| `commodities-intraday-1-min` | symbol | 1m |
| `commodities-intraday-5-min` | symbol | 5m |
| `commodities-intraday-1-hour` | symbol | 1h |

---

## 25. `ESG` — ESG 評級

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `esg-ratings` | symbol | 公司 ESG 三軸評分（Environmental / Social / Governance） |
| `esg-search` | symbol | ESG 投資搜尋（含同業比較） |
| `esg-benchmark` | year | 全市場 ESG 基準（依年度） |

---

## 26. `commitmentOfTraders` — COT 持倉報告

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `COT-report` | （symbol/from/to）| CFTC COT 報告（commercial / non-commercial / retail 各群體淨多空） |
| `COT-report-analysis` | （symbol/from/to）| COT sentiment 分析（極端定位偵測） |
| `COT-report-list` | — | 可用 COT symbol 清單（期貨商品/外匯/指數） |

---

## 27. `Fundraisers` — 群眾募資與股權融資

| Endpoint | 必要參數 | 說明 |
|---|---|---|
| `latest-crowdfunding` | — | 最新 Reg CF 群眾募資申報（Form C） |
| `crowdfunding-search` | name | 群眾募資公司名稱搜尋 |
| `crowdfunding-by-cik` | cik | 用 CIK 查特定群眾募資公司 |
| `latest-equity-offering` | — | 最新私募股權發行（Reg D / Form D） |
| `equity-offering-search` | name | 私募名稱搜尋 |
| `equity-offering-by-cik` | cik | 用 CIK 查私募 |

---

## 與專案現有腳本的對照

當前專案的 sector / earnings 腳本走 HTTP REST（因為 Python 腳本不能呼叫 MCP），endpoint path 與這份 MCP tool 對照：

| 用途 | HTTP path（腳本用） | MCP 等效 |
|---|---|---|
| 部門 P/E 快照 | `/stable/sector-pe-snapshot` | `mcp__fmp__marketPerformance(endpoint="sector-PE-snapshot")` |
| 部門 P/E 歷史 | `/stable/historical-sector-pe` | `mcp__fmp__marketPerformance(endpoint="historical-sector-pe")` |
| EOD 價格 | `/stable/historical-price-eod/light` | `mcp__fmp__chart(endpoint="historical-price-eod-light")` |
| 個股新聞 | `/stable/news/stock` | `mcp__fmp__news(endpoint="search-stock-news")` |
| 一般新聞 | `/stable/news/general-latest` | `mcp__fmp__news(endpoint="general-news")` |
| 財報日曆 | `/stable/earnings-calendar` | `mcp__fmp__calendar(endpoint="earnings-calendar")` |
| 內部人統計 | `/stable/insider-trading/statistics` | `mcp__fmp__insiderTrades(endpoint="insider-trade-statistics")` |
| Senate 最新 | `/stable/senate-latest` | `mcp__fmp__senate(endpoint="senate-latest")` |
| 分析師評等共識 | `/stable/grades-consensus` | `mcp__fmp__analyst(endpoint="grades-summary")` 或 `ratings-snapshot` |

> 寫腳本時繼續走 HTTP；LLM 在對話中查資料優先走 MCP（省 token、不必貼 API doc 教學）。

---

## 更新方式

未來 MCP server 端 endpoint 有增減時，重跑 `claude mcp list`、用 `ToolSearch` 載入 `mcp__fmp__*` schema 即可重生此檔。

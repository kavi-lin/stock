# AI Investment Committee — 個股資料撈取功能總表

> **目的**：盤點目前透過 FMP / Finnhub / yfinance / Alpaca 等 API，撈取「個股層級」（單一 ticker，含 SP500/NASDAQ 成分股）資料的所有功能，說明各自的資料來源、抓取內容與下游用途。
>
> **範圍**：僅涵蓋個股/單一 ticker 層級的資料撈取。市場整體或指數層資料（FRED 總經、market breadth、FTD/market-top 指數 OHLCV）不在此列，見文末「排除項目」。
>
> **產出方式**：3 個並行 Explore agent 分別掃描 `skills/`、`investment+sector+news`、`scripts+Dashboard+config`，再手動確認補齊 Alpaca 用法後彙整而成。

---

## 資料來源總覽

| 來源 | 角色 | 免費額度 |
|---|---|---|
| **FMP** | 主力來源：財報三表、估值比率、分析師評等、內部人/機構/國會交易、ESG、公司 profile/peers | 250 call/min（`scripts/_shared/fmp_pool.py` 集中限流） |
| **Finnhub** | 即時報價 + K線 + metric，做為 `finnhub-client` dual-fetch 的 canonical scoring 主來源（FMP 平行抓來 audit，不進 LLM） | 60 call/min |
| **yfinance** | 免費 OHLCV/技術面/波動度，供不需要精確度的模組（momentum、technical、tail-risk）使用 | 無金鑰限制 |
| **Alpaca** | 唯一使用場景：`skills/market-sentiment-analyzer/scripts/intraday_spikes.py` 抓 1 分鐘線做「個股急拉/急殺監控」——因為 FMP 的 1-min REST 是付費牆（402），改用 Alpaca 免費 IEX feed | 需 `ALPACA_API_KEY`/`SECRET_KEY`，無則優雅降級 |
| **FINVIZ** | 產業/個股層 rating 與新聞（theme-detector、market-news-analyst） | Elite 選用 |

---

## A. 共用基礎設施層（所有其他功能的地基）

| 功能 | 檔案 | 抓取內容 | 用途 |
|---|---|---|---|
| **company_context** | `skills/_shared/company_context.py` | FMP `/profile`、`/stock-peers`、`/ratios-ttm`+`/key-metrics-ttm`、`/historical-market-capitalization`、`/historical-employee-count`、`/income-statement`(8Q) | 全站個股 metadata 單一來源，供 earnings-analyst、momentum-monitor、us-stock-analysis、sector 腳本、forward_expectations 共用（24h／7d cache） |
| **fmp_supplementary** | `skills/_shared/fmp_supplementary.py` | Altman Z / Piotroski F-Score、Buffett owner earnings、內部人交易統計、13F 機構持股、國會議員交易、M&A 事件、ESG、高管薪酬 | 餵 investment_protocol 的 Fundamentals / Burry veto / Sentiment lane（24h cache） |
| **finnhub-client / dual_fetch** | `skills/finnhub-client/scripts/{finnhub_client,dual_fetch}.py` | `/quote`、`/stock/candle`、`/stock/profile2`、`/stock/metric` 等 17 個端點 | 產出 15 個「canonical scoring 標量」給 Phase 2 五個 lane 共用，物理隔離 FMP audit 資料不讓 LLM 看到 |
| **fmp_pool** | `scripts/_shared/fmp_pool.py` | 無資料本身，純限流層 | 跨程序 250/min 額度控管 + 429 自動退避重試 |

---

## B. 個股深度分析（`分析 [TICKER]` / `財報 [TICKER]` 人工觸發）

| 功能 | 檔案 | 抓取內容 | 用途 |
|---|---|---|---|
| **Phase 1 Factpack** | `investment/scripts/phase1_factpack.py` | 彙整上述 TICKER_DATA_BUNDLE + PEER_BUNDLE + FMP_SUPP_BUNDLE + EARNINGS_ANALYST_BUNDLE | 一次性組裝 Phase 1，避免 13-16 次分散呼叫 |
| **Price Framework Engine** | `investment/scripts/compute_price_framework.py` | FMP `/historical-price-eod/light`（OHLCV）算 ATR14、20D 歷史波動率、20D 動能 | 餵 fair_value 6-anchor blend、fair_value_range、MHP 三時間框架、reverse DCF（0 LLM 算術） |
| **Forward Expectations** | `investment/scripts/forward_expectations*.py` | FMP `/sec-filings-financials`、SEC EDGAR 文件、`/historical-price-eod` | Shadow 引擎：management guidance、analyst revisions、base-rate cohort、bear/base/bull 價格區間 |
| **earnings-analyst** | `skills/earnings-analyst/scripts/fetch.py` | 三表 8Q、TTM ratios/key-metrics、DCF、price-target consensus、ratings snapshot/history/news、earnings surprises、segment 分拆（產品/地區）、dividends、splits、transcript | 財報綜合報告 + 0-100 composite 分數；90 天 cache（key: ticker+last_earnings_date） |
| **earnings-valuation-forecaster** | `skills/earnings-valuation-forecaster/scripts/forecast.py` | 8Q/5Y EPS、analyst 5Y consensus、20Y P/E 分布、當前報價 | 12 個月目標價情境（bull/base/bear）+ 財報前 cheat sheet（`--pre-earnings`，4h cache） |
| **ic-memo-writer** | `skills/ic-memo-writer/scripts/{build_fact_pack,compose}.py` | 純讀取上述既有 cache（不重新 fetch） | 組裝 12 章節 IC Memo（0 LLM，decision_lock SHA256 保護結論） |
| **us-stock-analysis** | `skills/us-stock-analysis/scripts/analyze.py` | yfinance OHLCV + company_context profile/peers/quarterly income | Investment protocol Fundamentals lane 的 `--json-only` 輸出 |
| **technical-analyst** | `skills/technical-analyst/scripts/analyze.py` | yfinance OHLCV + FMP `/technical-indicators`（選用） | Technical lane：均線結構、RSI/MACD、支撐壓力 |
| **short-contrarian-analyst (Burry Score)** | `skills/short-contrarian-analyst/scripts/burry_score.py` | fmp_supplementary（FCF yield、EV/EBIT）+ yfinance（52週高低、內部人動向） | T4 估值否決 agent：分數 <20 強制 HOLD，≥60 給估值加成 |
| **register_thesis / backtest_postmortem** | `investment/scripts/{register_thesis,backtest_postmortem}.py` | 讀 history.json + earnings cache；yfinance 回測實際股價 | 論點生命週期登記、決策回測，非即時抓取 |

---

## C. 短期戰術雷達（每日自動，`daily_update.sh` 驅動）

| 功能 | 檔案 | 抓取內容 | 用途 |
|---|---|---|---|
| **momentum-monitor** | `skills/momentum-monitor/scripts/{momentum,screen,prefetch_fundamentals}.py` | yfinance 60d OHLCV+short interest + company_context 季度營收/毛利 | 對 SP500+NASDAQ100+SOX ~500 檔算動能分數、Weinstein 階段、EPS 加速濾網 |
| **short-term-target** | `skills/short-term-target/scripts/predict.py` | yfinance + finnhub-client cache + sector_intel 熱度 | 單股 1d/5d/15d 方向預測（±5%/±15%/±30%） |
| **thematic-screener** | `skills/thematic-screener/scripts/screen.py` | 呼叫 short-term-target subprocess 對主題代表股 | 每日 Top5 主題 × Top4 個股（`daily_update.sh` Step 6） |
| **theme-detector** | `skills/theme-detector/scripts/theme_detector.py` | FINVIZ 產業層 + yfinance 驗證趨勢（非嚴格個股，但決定主題代表股名單） | 14+ 跨產業主題偵測，餵 thematic-screener |
| **retail-sector-pulse** | `skills/retail-sector-pulse/scripts/{trending_tickers,aggregate}.py` | 社群來源（Reddit/HN/Google Trends）+ short-term-target 預測 | Dashboard 雷達頁 11-產業卡片（純探索層） |

---

## D. 風險與部位管理

| 功能 | 檔案 | 抓取內容 | 用途 |
|---|---|---|---|
| **tail-risk-analyzer** | `skills/tail-risk-analyzer/scripts/tail_risk.py` | yfinance 1-3y 日報酬 | 峰度/偏度/VaR95/最大回撤 → FRAGILE/MODERATE/ROBUST 分級 |
| **portfolio-risk-manager** | `skills/portfolio-risk-manager/scripts/risk_manager.py` | yfinance 波動度 + 既有持股相關性 | Phase 4 部位上限（波動度縮放 + 相關性懲罰 + 產業集中度檢查） |
| **kill_trigger_monitor** | `scripts/kill_trigger_monitor.py` | 逐個現有持倉報價 | 每日 Step 9.9 監控停損/停利觸發 |

---

## E. Dashboard 即時報價與監控（`dashboard_server.py` 背景執行緒）

| 功能 | 抓取內容 | 用途 |
|---|---|---|
| **Heatmap 報價刷新** | FMP `/quote`，20 workers 並發，10 分鐘 TTL | 前端熱力圖即時色塊 |
| **PE/估值快取刷新** | FMP `/ratios-ttm`+`/key-metrics-ttm`+`/analyst-estimates`，24h TTL | 熱力圖估值徽章 |
| **1 分鐘 K 線** | FMP `/historical-chart/1min`，開盤 60s／收盤 300s TTL | 個股下鑽 K 線圖 |
| **主題補充報價** | FMP `/batch-quote`，3 分鐘 TTL | 補足非 SP500 成分股（主題代表股）的報價 |
| **急拉/急殺監控** | **Alpaca** `/v2/stocks/bars`（1-min，IEX feed） | `intraday_spikes.py`：FMP 1-min 是付費牆，改用 Alpaca 免費源做監控名單急拉急殺偵測 |

對外 API：`/api/heatmap/data`、`/api/theme-heatmap`、`/api/graph/centrality/<TICKER>`、`/api/intraday-spikes/watchlist`。

---

## F. 知識圖譜 / 供應鏈 / 新聞的個股關聯

| 功能 | 檔案 | 抓取內容 | 用途 |
|---|---|---|---|
| **Nexus 供應鏈驗證** | `scripts/nexus/supply_chain.py` | FMP `/profile`（batch 50 檔）驗證 ticker/exchange/sector | 確保知識圖譜節點與 FMP universe 一致 |
| **市場新聞個股層** | `skills/market-news-analyst/scripts/fetch.py` | finvizfinance `ticker_news()`+`ticker_outer_ratings()`、yfinance `.news`、FMP `/sec-filings`(8-K) | News lane：分析師動向、SEC 8-K 事件 |
| **新聞協議 Stage1** | `news/fetch_all_news.py`（4 fetchers 之一） | FMP `/news-stock-latest` | 個股新聞納入新聞辯論流程 |
| **產業掃描個股層** | `sector/scripts/fetch_{sector_valuation,earnings_pulse,smart_money,sector_news}.py` | 對 SECTOR_TOP_5/UNIVERSE 逐檔抓 PE Z-score、財報驚喜、內部人/國會/13F、個股新聞 | 產業協議 Phase 1-4 的產業內個股訊號 |

---

## 排除項目（市場/指數層，非個股）

`market-breadth-analyzer`（TraderMonty CSV）、`FTD/market-top-detector`（指數 ^GSPC/^IXIC OHLCV）、`fred-macro`（FRED 總經指標）、`market-sentiment-analyzer` 的 `mood.py`/`intraday.py`（VIX/SPY/QQQ/IWM 聚合）—— 這些抓的是市場整體或指數層資料，不算「個股」功能，故未列入上表。

---

## 架構重點

1. 所有個股 metadata 都收斂到 `company_context.py` 單一來源，避免各技能各自重複打 FMP。
2. Finnhub 走 dual-fetch 架構——canonical scoring 用 Finnhub，FMP 平行抓來只做 audit、物理隔離不讓 LLM 看到，防止分數被污染。
3. Alpaca 目前**唯一**用途是繞開 FMP 1-min 付費牆做急拉急殺監控，不是主力資料源。
4. Cache 分層很清楚：即時報價 10min、估值比率 24h、季度財報 7d、財報分析包 90d——都是為了在 250/min FMP 額度下盡量不重複抓。

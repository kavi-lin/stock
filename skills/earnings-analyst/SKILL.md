# earnings-analyst — 個股財報深度分析

> **Trigger**: `財報 [TICKER]`
> **Version**: V1.0
> **Data Source**: FMP HTTP REST(`$FMP_API_KEY`)

## 目的

針對單一個股產出**深度財報分析報告**(逐季趨勢、品質指標、估值、分析師共識),涵蓋 sector V1.4 與 `分析 [TICKER]` 既有 protocol **沒有**的「財報層級」深潛內容。

## 與既有 skill 的差異

| Skill | 重點 | 觸發 |
|---|---|---|
| `us-stock-analysis` | 估值/技術/情緒 snapshot(yfinance + FMP partial) | Phase 2 fundamentals lane |
| `earnings-valuation-forecaster` | 12M 目標價 3×3 敏感度 | ad-hoc / earnings 前 14 天 |
| **`earnings-analyst`(本)** | **8 季三表結構化趨勢 + 品質 flag + 0-100 composite score** | `財報 [TICKER]` |

## 執行流程 (V1.73 — 6 步驟,含 LLM narrate phase)

```bash
# Step 1 — Fetch:呼叫 17 個 FMP endpoint(含 5 個 V1.73 infographic 層),寫 cache
python3 skills/earnings-analyst/scripts/fetch.py NVDA

# Step 2 — Analyze:derive 邊際/成長/品質 + composite scoring(in-place 寫回 cache)
python3 skills/earnings-analyst/scripts/analyze.py NVDA

# Step 3 — Validate cache schema(rc=0 才能進 narrate phase)
python3 skills/earnings-analyst/scripts/validate.py NVDA
```

### Step 4 — Narrate (LLM in-conversation phase, NEW)

**由 Claude Code 在 conversation 內執行,不寫 python orchestrator**(50K 字 transcript 抽取)。

Claude 用 Read 工具讀取:
1. `skills/earnings-analyst/cache/<TICKER>_<DATE>.json` 全文
2. 內含 `transcript.content` 字串(~50K 字),為 CFO 季度電話會議逐字稿

接著用 Write 工具寫出 `skills/earnings-analyst/cache/<TICKER>_<DATE>.infographic.json`,schema 見 `schema.md` 的「Infographic Cache (V1.0)」section。

**必抽欄位**(transcript 有時):
- `headline_oneliner` — 整體一句話摘要
- `surprise.*` — 直接複製 `cache.earnings_context.surprise`（Python 已挑選同財季、已有實際值的事件並計算；禁止取第一筆）。缺資料時 actual/estimated/beat/surprise_pct 可為 null。
- `segments_q.items[]` — **從 transcript CFO 段落抽季度數字**(infographic 上的 569.9/309.8 億等),抽不到才退化用 `cache.segments.product_fy[0]` + `is_fy_fallback=true`
- `geographic_q.items[]` — 同上邏輯
- `capital_returns.{buyback_authorization_usd, dividend_per_share_*, dividend_hike_pct, announcements[]}` — 從 transcript 抓 "authorized $X buyback"、"raising our dividend by Y% to $Z" 等句子
- `ceo_quote.{speaker, title, quote, context}` — 挑 1-2 句最能表達本季 narrative 的 CEO 引述
- `key_highlights[]`(≥3) — icon + title + body,涵蓋成長/產品/區域/資本/風險 等面向
- `summary[]`(≥2) — tldr 條列

**跨季追蹤必填（earnings-history/1）**：
- `history_schema_version: "earnings-history/1"`、`expectations: []`、`observed_metrics: []`，詳 `schema.md`「跨季追蹤契約」。
- 先讀 `cache.comparison.expectation_audit[].expectation` 的前次說法；只補有來源、相同期間與口徑的實際值到 `observed_metrics`。程式已有營收、GAAP 稀釋 EPS、毛利率、營益率、FCF，無須重抄。
- `expectations` 記本次提出、指向未來期間的公司指引／市場共識／分析預期；數值需原文門檻與來源。沒有可靠指引留 `[]`；模糊觀察用 `qualitative`，不得自行補達標門檻。
- 每項保存 source_ref（公開可點網址，禁止 API key）、source_quote、published_at、target_period、幣別、會計／匯率／業務口徑。來源是舊季 transcript 或 FY fallback 時，不得當本季季度證據。
- 舊文字只標「歷史摘要補建」，不計預測命中。下次觀察清單由 Python 產生；預期判定、差額、百分比全部由 Python 計算。只使用既有 narrate turn，不新增模型呼叫。

**transcript=null 時**(fallback):
- `transcript_used=false`,省略 `ceo_quote`
- `segments_q.is_fy_fallback=true`,用 FY 年度
- `capital_returns.announcements=[]`,只填 `cash_flow[0]` 上有的執行金額
- `key_highlights` 從 `quarterly_pnl yoy + quality_flags` 合成

```bash
# Step 5 — Render:驗證兩層輸入，產出跨季比較／預期驗收／下次追蹤並保存不可覆寫歷史
python3 skills/earnings-analyst/scripts/render.py NVDA

# Step 6 — Validate infographic schema(rc=0 才算完成)
python3 skills/earnings-analyst/scripts/validate_infographic.py NVDA --require-history
```

### 一次跑完(`財報 [TICKER]` trigger)

```bash
T=NVDA && \
  python3 skills/earnings-analyst/scripts/fetch.py "$T" && \
  python3 skills/earnings-analyst/scripts/analyze.py "$T" && \
  python3 skills/earnings-analyst/scripts/validate.py "$T" && \
  echo "→ Step 4: Claude reads cache+transcript, writes infographic.json" && \
  python3 skills/earnings-analyst/scripts/render.py "$T" && \
  python3 skills/earnings-analyst/scripts/validate_infographic.py "$T" --require-history
```

## Cache 設計

- **Key**: `(TICKER, fiscal_period_end)`；相容舊欄位 `last_earnings_date`，它是會計期末而非公布日。
- **檔名**: `cache/<TICKER>_<YYYY-MM-DD>.json`；公布日另存 `earnings_context.earnings_release_date`，僅在已完成事件可與本季營收對應時填入，無法對應留 null。
- **來源時鐘**：財務 7 天、market 24 小時、quote 5 分鐘；每次確認最新季度，`--force` 強制刷新來源。快取刷新不改寫歷史紀錄。
- **歷史**：成功 render 才保存 `cache/history/<TICKER>/<期末>/<hash>.json`，以及 `reports/earnings_history/<TICKER>/<期末>/<hash>.md`。同內容重跑冪等，修訂追加版本；historical lookup 不受最新頁面的 90 天限制。
- **預覽**：`render.py <TICKER> --preview --out reports/<DATE>_<TICKER>_earnings_comparison_preview.md` 可用舊摘要檢查新報告；不回寫快取、不補造事前預測、不保存已完成歷史。正式六步驟禁止用 preview 取代 render。

## FMP Endpoints 用量

實際呼叫數由來源快取是否到期決定；下表為核心 endpoint，完整取材亦包含 infographic 所需 endpoint。

| Endpoint | 用途 |
|---|---|
| `/profile` | sector / industry / marketCap / price / CEO |
| `/income-statement?period=quarter&limit=8` | 8 季 P&L |
| `/balance-sheet-statement?period=quarter&limit=8` | 8 季 BS |
| `/cash-flow-statement?period=quarter&limit=8` | 8 季 CF |
| `/key-metrics-ttm` | ROE/ROIC/FCF yield/Income Quality TTM |
| `/ratios-ttm` | margins/D-E/PE/PB/Current Ratio TTM |
| `/financial-growth?period=annual&limit=5` | 5y CAGR |
| `/enterprise-values?period=quarter&limit=1` | EV |
| `/discounted-cash-flow` | DCF intrinsic |
| `/price-target-consensus` | 分析師目標價區間 |
| `/ratings-snapshot` | FMP 1-5 composite + 子分項 |
| `/grades-historical?limit=6` | 6 個月 buy/hold/sell 變動 |

**Paid blocker(graceful skip)**:
- `/key-metrics?period=quarter`(逐季 metric 細項)→ TTM + 自算替代
- `/analyst-estimates?period=quarter`(forward EPS)→ `earnings-valuation-forecaster` 自算 3-method 替代
- `earningsTranscript` → 略過 transcript sentiment
- `ESG` → 略過 ESG section

## 報告 10 個區塊

1. **Snapshot** — companyName / sector / price / market cap / CEO / employees
2. **Quarterly P&L Trend** — 8Q revenue / GP / OpInc / NI / EPS + GM/OM/NM
3. **Balance Sheet Health** — working capital / current ratio / D/E / net cash
4. **Cash Flow Quality** — OpCF / FCF / FCF margin / cash conversion / capex intensity
5. **Profitability & Efficiency** — 8Q margin trend table + TTM ratios + capital efficiency
6. **Growth Trajectory** — YoY/QoQ acceleration label + 5y annual growth + per-share CAGR
7. **Valuation** — PE/PB/EV-EBITDA TTM + DCF intrinsic vs price + FMP 1-5 ratings
8. **Analyst Consensus** — PT consensus/median/high/low + 6-month grades trend
9. **Quality Flags(deterministic)** — accruals / capex outpaces / margin compression / DSO slowdown / negative FCF / debt buildup(無 flag → ✅ clean)
10. **Bottom Line** — composite 0-100 + verdict(STRONG/SOLID/MIXED/WEAK/DETERIORATING)

## Composite Scoring(0-100)

| 元件 | 滿分 | 邏輯 |
|---|---|---|
| Quality | 30 | 25 base − 4×flag count + bonus(income quality > 1.1 / cash conv > 1.1) |
| Growth | 30 | 10 base + revenue YoY tier + acceleration ± + 5y CAGR tier |
| Valuation | 25 | 10 base + DCF upside tier + FCF yield tier + ratings overall ± |
| Analyst | 15 | 5 base + PT upside tier + grades buy% tier |

**Verdict 對照**: 80+ STRONG / 65+ SOLID / 50+ MIXED / 35+ WEAK / <35 DETERIORATING

## Structural Shift Detection (V2.18.0)

`analyze.py` 額外輸出 `structural_shift` 區塊（不影響 composite_score，獨立 signal）：

| Signal | 條件 |
|---|---|
| `eps_qoq_jump` | EPS QoQ ≥ 30% |
| `gm_breakout` | gross margin ≥ 歷史 8Q [1:9] mean + 2σ |
| `rev_accel` | revenue YoY ≥ 25% AND 比上一季 YoY 高 ≥ 5pp |

**Tier**：
- `NONE` — 0 ~ 1 signal
- `CANDIDATE` — 最新 Q ≥ 2 signal
- `CONFIRMED` — 最新 Q AND 上一 Q 都 CANDIDATE（兩季連續結構性跳躍）
- `INSUFFICIENT_DATA` — 不足 5 季

**下游消費**：投資 protocol Phase 3 Step 1.5 (V2.18.0 modulation) 讀此 tier，CANDIDATE 放寬估值錨點 + position cap 50%；CONFIRMED 解除 sector_avoid + Red Team mean-reversion attack blocked。MU/QCOM 超級週期錯失案例的 systemic fix。

詳見 `schema.md` 與 `investment/investment_protocol_v5_0.md` Phase 3 Step 1.5。

## Institutional Format Standards (V2.17.0)

仿 reference equity-research/earnings-analysis SKILL.md 的 JPMorgan / Goldman 格式。MD report 規範如下：

| 維度 | 規範 | Why |
|---|---|---|
| **長度** | 8-12 頁（A4 single-column） | 機構分析師 1-2 day turnaround 就要產出，不是長篇 initiation |
| **字數** | 3,000-5,000 字（純內容，不含表格 / 圖 caption）| 太短 = 沒洞察；太長 = client 不讀 |
| **Summary tables** | 1-3 張（**不**完整三表）| 焦點是「本季 vs guide / consensus 變動」，不是教學財報 |
| **Charts** | 8-12 張（infographic + sparkline 混合）| segment / margin / capex / FCF trend / 估值帶狀圖 |
| **Turnaround** | earnings 後 24-48h 內產出 | 後續價格反應已 priced in，越晚越無 alpha |
| **Audience 假設** | reader 已熟悉公司基本面 | 不重述產品線 / 創辦人故事 |
| **焦點** | **NEW info only** — beat/miss、guidance 變動、segment mix shift、management commentary 新訊號 | 區別於 initiating-coverage（30-50 頁完整覆蓋） |

### 不做的

- 不做 P&L / BS / CF 完整重列（投資人查 10-Q）
- 不做歷史 5y 公司故事 review（initiating-coverage 才做）
- 不做 sector overview / TAM 估算（sector_protocol + investment_protocol fundamentals lane 各司其職）

### Format checklist（render.py 應自動檢查）

- [ ] 報告字數在 3,000-5,000 之間（軟警告，超出印 WARN）
- [ ] 至少 1 張 summary table，最多 3 張
- [ ] 「What's NEW」block 在報告前 1/3（不藏在最後）
- [ ] 每張表 + 每個關鍵數字都有 Citations & Hyperlinks（見下節）
- [ ] Composite score + verdict 在第一頁（讀者一眼掃完）

---

## Citations & Hyperlinks ⭐⭐⭐ MANDATORY (V2.14.0)

**規則**：MD report 內**所有財務數字、表格 footer、引述、guidance 變動**都必須掛 markdown clickable hyperlink，**不能**只寫 `Source: 10-Q` 純文字。讀者點得到才算 source。

### 必填 link 對照表

| 內容 | 必掛 link 指向 | URL 模板 |
|---|---|---|
| 季度三表數字（P&L / BS / CF）| SEC EDGAR 10-Q filing | `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-Q` |
| 年度數字（5y CAGR）| SEC EDGAR 10-K | `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K` |
| Earnings release 數字 / guidance | 公司 IR 頁面 press release | `https://investor.{company}.com/news/...`（從 transcript / FMP profile 抓） |
| Transcript CEO/CFO 引述 | FMP earningsTranscript endpoint 或 IR webcast 連結 | `https://discountingcashflows.com/company/{TICKER}/transcripts/` 或公司 IR webcast |
| Analyst PT consensus | FMP `/price-target-consensus` 來源頁 | `https://financialmodelingprep.com/financial-statements/{TICKER}` |
| FMP ratings 評級 | FMP `/ratings-snapshot` ticker 頁 | `https://site.financialmodelingprep.com/financial-summary/{TICKER}` |
| DCF intrinsic | FMP `/discounted-cash-flow` ticker 頁 | `https://site.financialmodelingprep.com/discounted-cash-flow/{TICKER}` |

### 範例

**❌ 錯**：
```
Source: Q3 2024 10-Q filed November 8, 2024; Company earnings release
```

**✅ 對**：
```
Source: [Q3 2024 10-Q](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=NVDA&type=10-Q) filed Nov 8, 2024;
        [earnings release](https://investor.nvidia.com/news/2024-q3-earnings)
```

### 強制範圍

- §1 Snapshot：CEO 名 → IR team page
- §2-§4 三表 8Q：每張表 footer 加 EDGAR 10-Q link（最近一季用 latest filing；其餘可省）
- §7 Valuation：DCF intrinsic / PE TTM / PB → FMP 對應頁 link
- §8 Analyst Consensus：consensus PT → FMP price-target-consensus link
- §10 Bottom Line composite：每個子分數來源 metric 都要可追溯（footnote 帶 link）

### 不強制範圍

- §6 Growth Trajectory 5y CAGR 純算術，不用 link
- §9 Quality Flags 是 deterministic 算出，標 `(deterministic, see analyze.py)` 即可

### 違規處理

`render.py` 產出時應自動填 link（template 預設帶 markdown link 結構）。若 LLM narrate phase（Step 4）寫 infographic.json 時忘掉 hyperlink，render 階段 fallback 到「無 link 純文字」是允許的（degrade gracefully），但 final report 一行 `WARN: missing source links — see Citations section in SKILL.md` 必須出現。

---

## 已知限制

- mega-cap universe 不限定 — 任何有 FMP 三表的 ticker 都可跑
- forward EPS 自算需要再呼叫 `earnings-valuation-forecaster`(此 skill 沒整合,使用者需自己接)
- transcript / ESG / per-Q metric 細項是 paid plan only
- DSO 計算用簡化(receivables/revenue × 91d),非 365d 全年口徑

## 不影響範圍

- **不改 `分析 [TICKER]` Phase 2 流程** — 此 skill 是獨立深度層,不自動掛上 daily protocol(避免 token 浪費)
- **Cache 與其他 skill 隔離** — 此 skill 不直接寫 `data.json`；Dashboard 財報入口使用相同完成檢查，專用比較畫面留待第二階段。

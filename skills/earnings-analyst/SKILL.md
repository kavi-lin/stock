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
| `earnings-trade-analyzer` | post-earnings gap/趨勢 5 因子評分 | earnings 後 |
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
- `surprise.*` — 從 `cache.earnings_surprises[0]` 計算 beat/miss + surprise_pct
- `segments_q.items[]` — **從 transcript CFO 段落抽季度數字**(infographic 上的 569.9/309.8 億等),抽不到才退化用 `cache.segments.product_fy[0]` + `is_fy_fallback=true`
- `geographic_q.items[]` — 同上邏輯
- `capital_returns.{buyback_authorization_usd, dividend_per_share_*, dividend_hike_pct, announcements[]}` — 從 transcript 抓 "authorized $X buyback"、"raising our dividend by Y% to $Z" 等句子
- `ceo_quote.{speaker, title, quote, context}` — 挑 1-2 句最能表達本季 narrative 的 CEO 引述
- `key_highlights[]`(≥3) — icon + title + body,涵蓋成長/產品/區域/資本/風險 等面向
- `summary[]`(≥2) — tldr 條列

**transcript=null 時**(fallback):
- `transcript_used=false`,省略 `ceo_quote`
- `segments_q.is_fy_fallback=true`,用 FY 年度
- `capital_returns.announcements=[]`,只填 `cash_flow[0]` 上有的執行金額
- `key_highlights` 從 `quarterly_pnl yoy + quality_flags` 合成

```bash
# Step 5 — Render:既有 markdown 報告(細節 reference,不變)
python3 skills/earnings-analyst/scripts/render.py NVDA

# Step 6 — Validate infographic schema(rc=0 才算完成)
python3 skills/earnings-analyst/scripts/validate_infographic.py NVDA
```

### 一次跑完(`財報 [TICKER]` trigger)

```bash
T=NVDA && \
  python3 skills/earnings-analyst/scripts/fetch.py "$T" && \
  python3 skills/earnings-analyst/scripts/analyze.py "$T" && \
  python3 skills/earnings-analyst/scripts/validate.py "$T" && \
  echo "→ Step 4: Claude reads cache+transcript, writes infographic.json" && \
  python3 skills/earnings-analyst/scripts/render.py "$T" && \
  python3 skills/earnings-analyst/scripts/validate_infographic.py "$T"
```

## Cache 設計

- **Key**: `(TICKER, last_earnings_date)`
- **檔名**: `skills/earnings-analyst/cache/<TICKER>_<YYYY-MM-DD>.json`(YYYY-MM-DD = 最新季財報日)
- **TTL 上限**: 90 天(超過硬失效,即使 last_earnings_date 未變)
- **Invalidation step**: fetch.py 先用最便宜呼叫 (`/income-statement?limit=1`) 拿最新季 date;若 cache 已有同 date 檔且 < 90d → skip 11 個 endpoint
- **`--force`**: 繞過 cache 強制重 fetch

## FMP Endpoints 用量

12 calls/run(完整 fetch),free plan 250/day。Cache hit 只用 1 call。

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

## 已知限制

- mega-cap universe 不限定 — 任何有 FMP 三表的 ticker 都可跑
- forward EPS 自算需要再呼叫 `earnings-valuation-forecaster`(此 skill 沒整合,使用者需自己接)
- transcript / ESG / per-Q metric 細項是 paid plan only
- DSO 計算用簡化(receivables/revenue × 91d),非 365d 全年口徑

## 不影響範圍

- **不改 `分析 [TICKER]` Phase 2 流程** — 此 skill 是獨立深度層,不自動掛上 daily protocol(避免 token 浪費)
- **Cache 與其他 skill 隔離** — 不寫 `data.json`、不影響 Dashboard

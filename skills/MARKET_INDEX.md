# Skills Market Index

> Source of truth for `market` / `scope` classification of every skill used by
> AI 投資委員會 protocols. Generated from SKILL.md frontmatter.

`market` values:
- **us-equity** — hard-coded to US data sources (FMP, FINRA, GICS, TraderMonty CSV, etc.); not reusable for other markets without rewrite
- **market-agnostic** — pure technical / math logic; reusable for any equity market if you supply the universe / data feed
- **global-macro** — macro events / news with global reach (Fed + ECB + BOJ etc.)

`scope` values: `single-ticker` / `universe-scan` / `sector-level` / `market-level` / `portfolio-level` / `event-scan` / `news-scan` / `theme-scan`

---

## 🇺🇸 US-Equity (11 skills — hard-coded to US market)

| Skill | Scope | Data sources | Used by |
|---|---|---|---|
| `us-stock-analysis` | single-ticker | yfinance, FMP | investment (phase-level) |
| `short-contrarian-analyst` | single-ticker | FMP, yfinance | investment Phase 2（第 5 agent, Burry） |
| `earnings-valuation-forecaster` | single-ticker | FMP (/stable) | 獨立使用（未整合至 protocol）— 12M 目標價 scenario + 敏感度 grid |
| `earnings-analyst` | single-ticker | FMP HTTP REST | `財報 [TICKER]` trigger — 8Q 三表深度 + 品質 flag + 0-100 composite + Markdown report |
| `supply-chain-event-analyst` | single-ticker/chain | WebSearch, FMP | 產業鏈上下游、供應鏈依賴度與歷史事件分析 |
| `sector-analyst` | sector-level | finvizfinance, yfinance | sector protocol core |
| `market-breadth-analyzer` | market-level | TraderMonty CSV | sector Phase 0 層 A |
| `market-sentiment-analyzer` | market-level | yfinance (VIX/SPY), CNN F&G | investment Phase 2 fallback, sector Phase 3 |
| `market-news-analyst` | news-scan | WebSearch/WebFetch | news protocol |
| `theme-detector` | theme-scan | finviz-performance, yfinance ETFs | sector Phase 4a |
| `ftd-detector` | market-level | yfinance | sector Phase 0 層 C（via script）|
| `market-top-detector` | market-level | yfinance | sector Phase 0 層 D（via script）|

## 🌐 Market-Agnostic (4 skills — reusable across markets)

| Skill | Scope | Data sources | Used by |
|---|---|---|---|
| `momentum-monitor` | universe-scan | yfinance | 動能選股 Dashboard 頁（pluggable universe file）|
| `technical-analyst` | single-ticker | chart image / yfinance | investment Phase 2 Technical |
| `tail-risk-analyzer` | single-ticker | yfinance | investment Phase 4 Step 3、sector Phase 4b |
| `portfolio-risk-manager` | portfolio-level | positions.json, yfinance | investment Phase 4 Step 2 |

> **Future reuse note**：這 4 個 skill 的邏輯**不綁特定市場**。若日後要做台股 / 加密 / ETF 專屬協定，只需替換 universe / data feed，核心分析程式碼可原樣使用。

## 🌍 Global-Macro (1 skill)

| Skill | Scope | Data sources | Used by |
|---|---|---|---|
| `economic-calendar-fetcher` | event-scan | FMP API | sector Phase 0, investment 事件檢查 |

> FMP 事件列表以美股為主但涵蓋 ECB/BOJ/英央等全球央行。歸入 `global-macro` 而非 `us-equity`，因核心用途與美股無綁定。

---

## 市場劃分的使用方式

當未來要新增第二個市場（例：台股）時：

1. **`market-agnostic` 類**：檢視即可直接套用，頂多換 universe 檔
2. **`us-equity` 類**：每個都要寫一個 `tw-equity` 對應版本（資料源、GICS → GICS-TW、FINRA → 台證所等）
3. **`global-macro` 類**：看需求，可能共用一個，或切分 `us-macro` / `tw-macro`

Protocol 檔案內用 `[framework]` / `[domain:us-equity]` HTML 註解標註哪些段落通用、哪些綁美股 — 切新市場時直接依註解替換對應段落。

---

## 維護規則

- SKILL.md frontmatter 是**唯一真相**；此文件若過時 `grep -l "market:" skills/*/SKILL.md` 重新生成
- 每加新 skill 必須同步更新此索引
- 改動分類（例如原本 `us-equity` 被抽象成 `market-agnostic`）時，必須同步檢查 CLAUDE.md「美股專區」章節

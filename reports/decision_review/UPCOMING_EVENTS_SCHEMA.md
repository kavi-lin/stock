# Upcoming Events — Unified Schema

> **目的**：把所有未來事件來源（sector-protocol binary risks、Finnhub/FMP 財報行事曆、經濟數據、Fed 行事曆、user manual）統一成一個 schema，給 `Dashboard/calendar.html` 的「即將發生」與其他下游使用。
>
> 取代 `data.json.binary_risks`（subset of this），news.html 的二元風險 sidebar 移除。

## 檔案位置

- **Output（每次 bridge.py 跑完寫入）**：`Dashboard/data.json` → `upcoming_events[]` 欄位
- **Server route**：透過 `dashboard_server.py /` (Dashboard/ 已 served)
- **Schema 參照**：本檔（手動更新）

## 一筆 UpcomingEvent

```jsonc
{
  "id":          "fmp-earnings_AAPL_2026-04-30",   // 必填. unique. 格式: <source>_<ticker_or_slug>_<date>
  "date":        "2026-04-30",                     // 必填. ISO YYYY-MM-DD
  "time":        "AMC",                            // 選填. "BMO" | "AMC" | "HH:MM ET" | "ALL" | null

  "category":    "earnings",                       // 必填. 列舉:
                                                   //   earnings | macro | econ | binary
                                                   //   geopolitical | system | watchlist
  "title":       "AAPL Q2 FY26",                   // 必填. 顯示用標題
  "description": "EPS est. $1.62 / Revenue $94B",  // 選填. 詳述

  "tickers":     ["AAPL"],                         // 選填. 個股事件; 空 array = 市場/經濟事件
  "sectors":     ["Technology"],                   // 選填. 影響的 GICS 產業 (cross-link sector page)

  "impact":      "high",                           // 必填. "high" | "med" | "low"
  "is_binary":   false,                            // 必填. true = 觸發 calendar 紅框警示樣式
  "within_48h":  false,                            // 派生. days_until <= 2

  "source":      "finnhub-earnings",               // 必填. 列舉見下表
  "source_payload": {                              // 選填. source-specific 完整欄位
    "epsEstimate": 1.62,
    "revenueEstimate": 94000000000,
    "hour": "amc",
    "quarter": 2,
    "year": 2026
  },

  "links": {                                       // 選填
    "report_path":  "reports/20260411_AAPL.md",
    "external_url": null
  }
}
```

## category 列舉

| category | 觸發 source | 視覺 (calendar) |
|---|---|---|
| `earnings` | finnhub-earnings / fmp-earnings | 💼 icon, ticker chip |
| `macro` | fed-calendar / sector-protocol (Fed 相關) | 🏛️ icon |
| `econ` | fmp-econ / 自製 | 📊 icon |
| `binary` | sector-protocol `_phase3.upcoming_binary_risks` | ⚠️ icon, **紅框** |
| `geopolitical` | sector-protocol / news-digest | ⚠️ icon |
| `system` | thematic-screener self-schedule | 📅 icon |
| `watchlist` | manual / momentum-monitor flagged | 🎯 icon |

## source 列舉

| source | 說明 | binary 判定 |
|---|---|---|
| `sector-protocol` | sector_intel.json `_phase3.upcoming_binary_risks` | 一律 `is_binary=true` |
| `finnhub-earnings` | Finnhub `/calendar/earnings` | mega-cap 或 impact=high → true |
| `fmp-earnings` | FMP `/earning_calendar` | 同上 |
| `fmp-econ` | FMP `/economic_calendar` | importance=3 → true |
| `fed-calendar` | 手寫 YAML (FOMC + Powell speeches) | 一律 `is_binary=true` |
| `manual` | user 自加 | user 指定 |
| `thematic-screener` | radar 自排程 | 一律 false |

## Dedupe Key

```python
def event_key(e):
    if e['tickers']:
        # 個股: 同 ticker × 同 category × 同日 → 同事件
        return (e['date'], e['tickers'][0], e['category'])
    else:
        # 市場/經濟: 同 category 同日仍可能有多筆 (e.g., 4/29 FOMC + DOJ)
        # 用 title-slug 區分
        slug = re.sub(r'[^a-z0-9]+', '-', e['title'].lower())[:30]
        return (e['date'], None, e['category'], slug)
```

**Cross-category 合併規則**（同 ticker × 同日 不同 category）：
- 同一 AAPL 4/30 既是 sector-protocol `binary` 又是 finnhub `earnings`
  - 取 `impact` 最高的當主筆
  - `is_binary = OR` (任一 source true 就 true)
  - `source_payload` merge（key 衝突時以主筆為準）
  - `tickers` / `sectors` union

## Pipeline

```
sector-protocol  Finnhub  FMP  Fed YAML  user-manual
       │           │       │      │           │
       └───────────┴───────┴──────┴───────────┘
                          │
                          ▼
            bridge.py:aggregate_upcoming_events()
                          │
            ┌─────────────┼──────────────┐
            ▼             ▼              ▼
       1. 各 source     2. 套 schema   3. dedupe + sort
          原始讀取         轉換             by date asc
                          │
                          ▼
            data.json.upcoming_events[]
                          │
                          ▼
            page-calendar.js fetch (via /data.json)
```

## 改動清單（Stage 1，目前要做的）

- [ ] `bridge.py`：新增 `aggregate_upcoming_events()`（接 sector-protocol 一個來源即可）
- [ ] `bridge.py`：data.json 加 `upcoming_events[]` 欄位
- [ ] `Dashboard/page-calendar.js`：移除 mock；改 fetch `data.json` 讀 `upcoming_events`
- [ ] `Dashboard/news.html` + `page-news.js`：移除 binary risks sidebar
- [ ] `data.json.binary_risks` 暫時保留以免破壞其他依賴

## 後續（Stage 2/3）

- Stage 2：wire Finnhub/FMP earnings calendar
- Stage 3：wire FMP econ calendar + 手寫 `config/fed_calendar.yaml`

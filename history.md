# AI 投資委員會 — Project History

---

## System Changelog — 系統版本紀錄

### 2026-04-11 — 資料夾架構重整 & Protocol 升級

**目錄結構重整**
- 建立 `reports/` 作為所有最終 MD/HTML 報告的統一存放位置
- 建立 `reports/optimized/` 存放優化版報告
- 建立 `skills/theme-detector/cache/` 存放 theme-detector JSON 中繼 cache
- 各模組的 `_logs/` 目錄改為純 JSON cache 用途
- 清理根目錄散落檔案，統一命名規則為**日期開頭（YYYYMMDD_*）**

**搬移紀錄**

| 原位置 | 新位置 |
|--------|--------|
| `investment/invest_logs/YYYYMMDD_*.md` | `reports/` |
| `investment/invest_logs/*_optimized.*` | `reports/optimized/` |
| `20260408_MSFT_optimized.html`（根目錄）| `reports/optimized/` |
| `MU_Comprehensive_Report.html`（根目錄）| `reports/20260407_MU.html` |
| `RKLB_Comprehensive_Report.html`（根目錄）| `reports/20260407_RKLB.html` |
| `NEE_vs_VRT_比較報告_2026-04-09.md`（根目錄）| `reports/20260409_NEE_vs_VRT比較報告.md` |
| `sector_logs/`（根目錄重複）| 合併至 `sector/sector_logs/` |
| `session_export_AMD_20260409.json`（根目錄）| `investment/invest_logs/` |
| `reports/theme_detector_*.json` | `skills/theme-detector/cache/` |

**Protocol 更新**
- `investment_protocol_v4_3` → `investment_protocol_v4_4`
  - MD 報告輸出路徑改為 `../reports/YYYYMMDD_TICKER.md`
  - GLOBAL RULES 新增 Theme Cache 規則（Rule 3）
- `sector_protocol_v1`
  - Phase 2 新增 Theme-Detector Cache Check
  - Phase 5 新增 MD 報告輸出步驟 → `../reports/YYYY-MM-DD_sector_report.md`
  - 本地檔案結構說明更新
- `news_protocol_v1`
  - GLOBAL RULES 新增 Theme Cache 規則（Rule 2）
  - Phase 4 新增 MD 報告輸出步驟 → `../reports/YYYYMMDD_news_*.md`
  - 本地檔案結構說明更新
- `CLAUDE.md` 新增，統一記錄路徑規則與觸發方式

**Theme-Detector Cache 邏輯（三個 protocol 共用）**
```
執行前先查: skills/theme-detector/cache/theme_detector_YYYY-MM-DD_*.json
命中 → 載入，theme_source: THEME_CACHE，跳過 skill 執行
未命中 → 執行 skill → JSON 存 cache/，MD 移 reports/ 並改名為 YYYYMMDD_theme_detector_*.md
```

---

### 2026-04-11 — Theme Detection & Bilingual Report

**執行紀錄**
- 執行 `theme-detector` skill（FINVIZ Elite 模式，耗時 318 秒）
- 掃描 144 個產業，偵測 10 個主題（8 LEAD · 2 LAG）
- WebSearch 敘事確認 Top 5 主題

**主要發現**
| 主題 | Heat | 階段 | Confidence |
|------|------|------|------------|
| Basic Materials | 64.0 | Trending | High |
| Infrastructure & Construction | 59.8 | Trending | High |
| Oil & Gas | 58.7 | Accelerating | Medium ⚠️ |
| Clean Energy & EV | 58.5 | Accelerating | Low |
| Defense & Aerospace | 54.3 | Accelerating | High |
| AI & Semiconductors | 30.0 | **Exhausting** | High |

- 輸出：`reports/20260411_theme_report.md`（雙語報告）
- Cache：`skills/theme-detector/cache/theme_detector_2026-04-11_094958.json`

---

## Git Commit History — 提交紀錄

### `98cce74` — 2026-04-09 — Initial commit
`AI投資委員會 multi-protocol investment system`

初始建立三套 protocol：
- `investment_protocol_v4_3`：8-Agent 個股分析，Phase 0–6
- `sector_protocol_v1`：盤前產業情報，多空辯論機制
- `news_protocol_v1`：即時新聞分析，FLASH / DIGEST 雙模式
- Three-layer Phase 0 cache：sector_intel → phase0 → web search
- Skills 整合：`us-stock-analysis`、`market-news-analyst`、`technical-analyst`

### `e13cb1e` — 2026-04-09 — add msft 0408 report
MSFT 0408 分析報告加入版本控制（`investment/invest_logs/20260408_MSFT_optimized.html`）

### `acbdac2` — 2026-04-07 — Create MU_Comprehensive_Report.html
MU（Micron Technology）綜合分析報告

### `8eb594e` — 2026-04-07 — Create RKLB_Comprehensive_Report.html
RKLB（Rocket Lab）綜合分析報告

---

## Analysis Session Log — 個股分析紀錄

| 日期 | Ticker | Action | Score | Confidence | 備註 |
|------|--------|--------|-------|------------|------|
| 2026-04-07 | TSLA | ❌ CANCEL | -2.10 | 0.74 | 關稅衝擊期，EPS -47%，P/E 356x，Q1交車量不及預期 |
| 2026-04-07 | VST | ✅ EXECUTE | +1.80 | 0.68 | 電力/數據中心需求牛市，從高點 -32% 提供進場機會 |
| 2026-04-08 | MSFT | ✅ EXECUTE | +0.26 | 0.71 | 雲端 SaaS 防禦屬性，Azure +40%；技術面雙均線空頭為風險，分批建倉 |
| 2026-04-08 | NBIS | ❌ CANCEL | +1.83 | 0.76 | AI 基礎設施高成長，但現價略高於理想區 $108–115，等回調 |
| 2026-04-08 | MU | ✅ EXECUTE | +2.50 | 0.71 | 美伊停火解除尾部風險，RISK_ON；進場區 $375–390，TP $452，SL $350，R/R 2.19x |
| 2026-04-09 | AMD | — | — | — | Session export 存檔，未完整記錄 |
| 2026-04-10 | CRWV | ❌ CANCEL | +0.48 | 0.56 | HOLD；槓桿結構極端（D/E 8.94x），建議財報後（May 20）或回落 $75–85 再進場 |

---

## 目前檔案結構

```
AI投資委員會/
├── CLAUDE.md                          ← 系統說明與路徑規則
├── history.md                         ← 本檔案
├── README.md
├── investment/
│   ├── investment_protocol_v4_4.md    ← 現行 protocol
│   ├── investment_protocol_v4_3.md    ← 舊版備存
│   └── invest_logs/                   ← JSON cache only
│       ├── YYYY-MM-DD_phase0.json
│       ├── history.json
│       └── session_export_*.json
├── sector/
│   ├── sector_protocol_v1.md
│   └── sector_logs/                   ← JSON cache only
│       └── YYYY-MM-DD_sector_intel.json
├── news/
│   ├── news_protocol_v1.md
│   └── news_logs/                     ← JSON cache only
│       └── YYYY-MM-DD_digest.json
├── skills/
│   └── theme-detector/
│       └── cache/                     ← theme-detector JSON cache
│           └── theme_detector_YYYY-MM-DD_*.json
└── reports/                           ← 所有最終報告
    ├── YYYYMMDD_TICKER.md             ← 個股分析
    ├── YYYY-MM-DD_sector_report.md    ← 產業掃描
    ├── YYYY-MM-DD_news_digest.md      ← 新聞 DIGEST
    ├── YYYYMMDD_theme_detector_*.md   ← 主題偵測
    └── optimized/                     ← 優化版報告
        └── YYYYMMDD_*_optimized.*
```

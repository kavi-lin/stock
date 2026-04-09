# AI 投資委員會 — 總覽

這是一套給 Claude 使用的多 Agent 投資分析系統，包含兩個獨立 protocol：

---

## 專案結構

```
AI投資委員會/
├── README.md                        ← 本文件
├── investment/
│   ├── README.md                    ← 個股分析說明
│   ├── investment_protocol_v4_3.md  ← 個股分析 instruction
│   └── invest_logs/
│       ├── history.json             ← 所有 session exports
│       ├── YYYY-MM-DD_phase0.json   ← 當日 macro cache
│       └── YYYY-MM-DD_TICKER.md     ← 個股 session logs
├── sector/
│   ├── README.md                    ← 產業分析說明
│   ├── sector_protocol_v1.md        ← 盤前產業分析 instruction
│   └── sector_logs/
│       ├── YYYY-MM-DD_sector_intel.json  ← 當日產業 cache
│       └── sector_history.json           ← 歷史產業 verdict
└── news/
    ├── README.md                    ← 新聞分析說明
    ├── news_protocol_v1.md          ← 即時新聞分析 instruction
    └── news_logs/
        ├── YYYY-MM-DD_digest.json   ← 當日累積新聞分析
        └── YYYY-MM-DD_HH-MM_flash.json  ← 單則即時快閃
```

---

## 三個 Protocol 的關係

```
盤前（每日一次）
sector_protocol ──→ sector_intel.json
                              │
                              ▼
隨時觸發                      │ cache shared
news_protocol ────→ patch ───┤
                              │ patch
                              ▼
個股分析（每支股票）    phase0.json
investment_protocol ←────────┘
（Phase 0 三層 cache：sector_intel → phase0 → web search）
```

**news_protocol 的作用：**
不需要重跑 sector_protocol，直接 patch cache，下次 investment_protocol 執行時自動 pick up 最新新聞影響。

---

## 各 Protocol 快速說明

| Protocol | 用途 | 觸發時機 | Session Config |
|---|---|---|---|
| `sector_protocol_v1.md` | 產業熱度、輪動、主題偵測 | 每日盤前一次 | `RISK_TOLERANCE`, `FOCUS_DATE` |
| `news_protocol_v1.md` | 即時新聞分析、cache 更新 | 隨時（重大消息時） | `MODE: FLASH\|DIGEST` |
| `investment_protocol_v4_3.md` | 個股完整分析、進出場決策 | 每次分析個股 | `RISK_TOLERANCE` |

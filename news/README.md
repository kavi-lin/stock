# News Protocol — 即時新聞分析說明

即時新聞截取與影響分析 instruction，可隨時觸發，完成後自動更新其他 protocol 的 cache。

---

## 快速開始

```
NEWS TRIGGER
──────────────────────────────────────────
MODE : FLASH | DIGEST
──────────────────────────────────────────
```

然後直接在對話中說：
- 「幫我分析這則新聞：[標題/連結]」→ FLASH mode
- 「更新新聞 cache」→ DIGEST mode（掃描近 48h）

---

## 兩種模式

| 模式 | 觸發方式 | 耗時 | 適用情境 |
|---|---|---|---|
| **FLASH** | 貼入特定新聞 | 快（< 5 min） | 看到重大消息時立即分析 |
| **DIGEST** | 主動掃描 | 較長 | 盤前/盤中全面更新 |

---

## 執行流程

```
Phase 1          →  Phase 2               →  Phase 3          →  Phase 4
新聞收集              Bull vs Bear 辯論         Arbiter 仲裁         Cache Patch
FLASH: 用戶提供        雙方獨立解讀              採納/拒絕論點         更新 3 個 cache 檔案
DIGEST: web search    禁止互相妥協              輸出 net_impact_score
```

---

## 辯論規則

每則新聞**強制**同時產出 Bull 和 Bear 兩個解讀：

| Bull Analyst | Bear Analyst |
|---|---|
| 為何這是利多 | 為何這是利空 |
| 受益產業 | 受損產業 |
| 關鍵假設（何時成立） | 關鍵假設（何時成立） |

**Arbiter 仲裁邏輯**：
- `|bull - bear| < 1` → verdict = `BINARY`（市場解讀分歧，不可單邊下注）
- `source_credibility = LOW` → confidence 上限 0.5
- `binary_risk + within_48h` → 相關產業強制降一個 verdict 等級

---

## Cache 更新機制

分析完成後，News Arbiter 自動 patch：

| 檔案 | 更新內容 |
|---|---|
| `../sector/sector_logs/YYYY-MM-DD_sector_intel.json` | 在 `top_catalysts` 最前插入新事件 |
| `../investment/invest_logs/YYYY-MM-DD_phase0.json` | 更新 `binary_risks`、重算 `macro_backdrop_score` |
| `./news_logs/YYYY-MM-DD_digest.json` | 累積當日所有新聞分析 |

> 其他 protocol 下次執行時，讀取 cache 即自動取得最新新聞影響。  
> **不需要重新跑整個 sector_protocol 或 investment_protocol。**

---

## Impact Card 輸出樣式

```
╔══════════════════════════════════════════════════════════╗
║  NEWS FLASH  │  2026-04-09 14:32  │  MODE: FLASH        ║
╠══════════════════════════════════════════════════════════╣
║  [BULLISH +3.2]  川普暫停對科技股加徵關稅 90 天             ║
╠══════════════════════════════════════════════════════════╣
║  BULL ✅  科技供應鏈壓力驟降，AI 採購週期重啟               ║
║  BEAR ❌  90 天後不確定性仍在，資本支出可能推遲              ║
║  ARBITER → BULLISH，採納 BULL 主論點                      ║
╠══════════════════════════════════════════════════════════╣
║  受益 ↑  Technology (+strong)  Industrials (+moderate)  ║
║  受損 ↓  None                                            ║
║  Binary Risk: No                                         ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated: sector_intel.json ✅  phase0.json ✅     ║
╚══════════════════════════════════════════════════════════╝
```

---

## 本地檔案

```
news/
├── README.md                         ← 本文件
├── news_protocol_v1.md               ← Claude instruction
└── news_logs/
    ├── YYYY-MM-DD_digest.json        ← 當日累積新聞分析
    └── YYYY-MM-DD_HH-MM_flash.json   ← 單則即時快閃（選擇性）
```

---

## 與其他 Protocol 的關係

```
news_protocol（任意時間觸發）
    ↓ patch
sector_intel.json  ←  sector_protocol 讀取
phase0.json        ←  investment_protocol 讀取（層 2 cache）

不需要重新跑 sector_protocol 或 investment_protocol，
下次分析自動 pick up 更新後的 cache。
```

---

## 觸發情境速查

| 情境 | 說明 | MODE |
|---|---|---|
| 看到重大新聞 | 直接貼標題給 Claude | FLASH |
| 開盤前更新氣氛 | 「更新新聞 cache」 | DIGEST |
| 個股分析前確認新聞 | 「掃描 NVDA 最新新聞」 | FLASH |
| 盤中走勢異常 | 「掃描近 2 小時重大事件」 | DIGEST |
| 關稅/政策突發 | 貼原文或連結 | FLASH |

---

## 版本紀錄

### V1.0（當前）
- FLASH / DIGEST 雙模式
- Bull vs Bear 強制辯論框架
- Arbiter 仲裁 + net_impact_score（-5 to +5）
- 自動 patch 三個 cache 檔案（sector_intel / phase0 / digest）
- Impact Card Markdown 輸出

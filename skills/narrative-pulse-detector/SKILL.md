---
name: narrative-pulse-detector
description: 熱潮股 / 話題股短期上漲潛力探測器 — 把單股放進 narrative trade 五階段框架 (蘊釀 → 啟動 → 加速 → 狂熱 → 分配),量化 R/R 期望值,給出「是否還有短期上漲空間」判斷。針對 user 在新聞 / 社群 / 圖卡看到的剛起來話題股,不取代 investment_protocol 中長期決策。
version: V1.0
data_sources:
  - FMP /stable/historical-price-eod/full (via momentum-monitor/technical_core.fetch_history)
  - FMP /stable/quote (via market-top-detector/fmp_client.FMPClient)
  - Finnhub /stock/upgrade-downgrade (via finnhub-client.upgrade_downgrade)
  - Reddit RSS + Hacker News Algolia (via scripts/break_news/social_sources)
  - news/news_logs/<DATE>_raw.json (mention 次數彙總)
  - FRED ^VIX + breadth_csv_client (macro context)
---

# narrative-pulse-detector — 熱潮股短期上漲潛力探測器

> **Trigger**: `脈動 [TICKER]` / `narrative [TICKER]` / `話題股 [TICKER]`
> **Version**: V1.0 (2026-05-23)
> **Tier**: 探索層 (NOT investment_protocol Arbiter,跟 Nexus / Break News 同層)

## 目的

User 在新聞、財經圖卡、Reddit / Stocktwits 看到一個剛起來的話題股,想快速判斷:

> 「現在進場還有沒有短期上漲空間?還是已經在 climactic 後段、追高 R/R 是負的?」

這 skill 把單股放進 **narrative trade 五階段** 框架,輸出量化階段判斷 + 4 scenario R/R 表 + 建議倉位動作。

## 與既有 skill 的差異

| Skill | 重點 | Scope | 觸發 |
|---|---|---|---|
| `momentum-monitor` | tape flow (RSI / SMA / vol / short interest 4-component composite) | 通用動能評分 | `動能 [TICKER]` |
| `short-term-target` | 1d / 5d / 15d 預測 ± ATR 區間 | tactical 短線預測 | `predict.py <T>` |
| `thematic-screener` | top themes × top movers 主題層 | 主題輪動 | daily_update Step 6 |
| **`narrative-pulse-detector`(本)** | **單股 narrative lifecycle 階段 (Stage 1-5) + R/R 量化** | **熱潮股短期上漲潛力** | `脈動 [TICKER]` |

**本 skill 補上述 3 個工具沒追的維度**:
- 連續 RSI 超買日數
- 價 / SMA200 拉伸倍數
- Gap-up (5%+) 4 週內密集度
- Per-stock distribution day (O'Neil 高量黑 K)
- Sell-side PT raise 30/60d 速度
- Retail ($TICKER cashtag) 提及量
- 媒體 mention 次數 + source diversity
- Narrative stage 1-5 分類 + 4 scenario R/R

## 執行流程

```bash
# 單股 ad-hoc
python3 skills/narrative-pulse-detector/scripts/pulse.py NOK
# → 寫 skills/narrative-pulse-detector/cache/NOK_<DATE>.json
# → stderr 印 stage / confidence / E[R] one-liner

# 批次 (daily_update.sh Step 9)
python3 skills/narrative-pulse-detector/scripts/batch_scan.py \
    --source thematic_screener \
    --top-n 30 \
    --output Dashboard/narrative_pulse.json

# Render markdown summary (optional)
python3 skills/narrative-pulse-detector/scripts/render.py NOK
# → reports/<DATE>_NOK_pulse.md
```

## Narrative Trade 五階段

| Stage | 中文 | 判定條件 (簡述,完整在 `config/stage_weights.yaml`) | 建議動作 |
|---|---|---|---|
| 1 | 蘊釀 | 突破 SMA200 < 30d + 媒體無聲 + 0 sell-side raise / 60d | **早期建倉窗口** |
| 2 | 啟動 | volume 1.5-3x baseline + RSI 從 <50 → 60+ + 1-2 sell-side action | **積極布局** |
| 3 | 加速 | volume 3-5x + RSI ≥ 65 + 3-5 PT raise / 30d + media 進場 | **持有 / 跟進** |
| 4 | 狂熱 | RSI ≥ 70 連續 ≥ 10d + 價/SMA200 ≥ 1.8x + gap-up 4 週 ≥ 3 個 + retail FOMO | **減倉 / 不新進** |
| 5 | 分配 | Stage 4 訊號 + distribution day ≥ 4 / 25d | **出場 / 做空候選** |

## 輸出 schema

詳見 `schema.md`。核心欄位:

```json
{
  "ticker": "NOK",
  "stage": 4,
  "stage_label_zh": "狂熱後段",
  "stage_confidence": 0.82,
  "scenarios": [
    {"label": "末段衝高", "prob": 0.35, "target_pct": 13.0},
    {"label": "橫盤消化", "prob": 0.25, "target_pct": -10.0},
    {"label": "回測 SMA50", "prob": 0.25, "target_pct": -30.0},
    {"label": "回測 SMA200", "prob": 0.15, "target_pct": -53.0}
  ],
  "expected_return_pct": -13.4,
  "next_warning_condition": "distribution day count ≥ 4 / 25d",
  "recommended_action": "no_new_entry",
  "components": {
    "rsi_overbought_days": 17,
    "price_to_sma200_ratio": 2.14,
    "gap_up_density_4w": 6,
    "distribution_days_25d": 2,
    "pt_raise_30d": 7,
    "retail_mention_24h": 142,
    "media_mention_30d": 38,
    "media_source_diversity": 12
  }
}
```

## 重點紀律

- **探索層**: 跟 Nexus / Break News 同等級,**不**進入 `investment_protocol_v5_0.md` 的 Arbiter 決策樹
- **不**自動調倉位,只給 `recommended_action` 字串
- Stage 閾值在 `config/stage_weights.yaml`,user 可手動微調 (參考 `feedback_exploration_phase.md` — 探索期工具設計原則)
- Daily batch 跑 thematic-screener top movers + structural_watchlist (~30 ticker),user ad-hoc 可查 universe 外的 ticker

## Cross-ref

- `skills/momentum-monitor/SKILL.md` — tape flow 動能榜
- `skills/short-term-target/SKILL.md` — 1d/5d/15d tactical 預測
- `skills/thematic-screener/SKILL.md` — 主題層 movers
- `skills/market-top-detector/SKILL.md` — 大盤層 distribution day (本 skill fork 改 per-stock)
- `reports/2026-05-23_NOK_image_review.md` §10-11 — 本 skill 的設計案例 (NOK 5/22 Stage 4 後段驗證)

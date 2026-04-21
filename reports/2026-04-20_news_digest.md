# 新聞分析 DIGEST — 2026-04-20

> **Mode**: DIGEST | **Fan-out**: PER_AGENT_BATCH (Bull/Bear/Sector/Macro × 4 subagent isolated) | **Stage 1**: 25 triaged → **Stage 2**: 5 deep
> **Session Macro Delta**: **-0.4**（伊朗 binary 主導，被 REE 結構性利多與 AI demand 驗證部分抵銷）
> **Validator**: ✓ V2.1 schema compliant
> **Cache patches**: `sector/sector_logs/2026-04-19_sector_intel.json` ✅ | `investment/invest_logs/2026-04-19_phase0.json` ✅（macro_backdrop_score -0.5 → -0.7）

---

## 1. Triage Summary

| # | News ID | Score | Headline | Type | Verdict |
|---|---|---|---|---|---|
| ✅ DEEP | n057 | -2.0 | US-Iran ceasefire toward brink (USS Spruance seized Iranian ship Touska) | geopolitical | **BINARY** |
| ✅ DEEP | n032 | +1.3 | Eli Lilly to acquire Kelonia $7B (in-vivo CAR-T) | corporate | **BULLISH** |
| ✅ DEEP | n058 | +2.2 | USA Rare Earth $2.8B acquires Brazil Serra Verde | sector_news | **BULLISH** |
| ✅ DEEP | n042 | -0.2 | One company (NVDA) = half of S&P 500 EPS revisions since Iran war | sentiment | **NEUTRAL** ⚠ |
| ✅ DEEP | n065 | +0.5 | AI startup Cursor $2B raise at $50B valuation | sentiment | **NEUTRAL** ↗ |
| ❌ SKIP | n030 | +2.8 | Susquehanna: data center demand drives semis upside | sector_news | — |
| ❌ SKIP | n050 | -2.6 | Investors misreading Iran war news, markets whipsaw | sentiment | — |
| ❌ SKIP | n047 | -2.4 | Kevin Warsh would be the first 'tech bro' Fed chair | monetary_policy | — |
| ❌ SKIP | n044 | +2.4 | Psychedelic stocks +40% on Trump executive order | sector_news | — |
| ❌ SKIP | n066 | -2.3 | Wall Street's brutal message to oil stocks after Iran's move | sector_news | — |
| ❌ SKIP | n024 | +2.2 | Marvell pops on Google AI ASIC talks (worrying for AVGO) | corporate | — |
| ❌ SKIP | n067 | +2.1 | Software 'dogs' join market rally | sector_news | — |
| ❌ SKIP | n063 | +2.0 | Mitsubishi Heavy first-ever warship export (to Australia) | sector_news | — |
| ❌ SKIP | n048 | -1.9 | Hidden options mechanics no longer helping stocks | sentiment | — |
| ❌ SKIP | n061 | +1.7 | UniCredit pursues Commerzbank takeover | corporate | — |
| ❌ SKIP | (43 more) | <±1.7 | small-cap earnings, lifestyle, retirement Q&A | various | — |

---

## 2. Deep Analysis — Impact Cards

### 🚨 [BINARY -2.0] n057 — US-Iran Ceasefire Toward Brink (within 48h)

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-04-20 23:10  │  MODE: DIGEST         ║
╠══════════════════════════════════════════════════════════╣
║  [BINARY -2.0]  US-Iran ceasefire 4/22 expiry / Hormuz   ║
║  type: geopolitical  │  weights: Macro 40%, Bear 30%     ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ XLE / ITA / 油輪 / 防務 結構性受惠            ║
║  BEAR    ❌ Stagflation wedge + SPY Greed 擁擠去槓桿     ║
║  SECTOR  ⚖ XLE strong↑, ITA mod↑, JETS↓ IYT↓ XLY↓       ║
║  MACRO   ❌ Brent +5.6-7% to $95-97; Fed cut path 延後   ║
║  ARBITER → BINARY (spread 8 + within_48h)               ║
╠══════════════════════════════════════════════════════════╣
║  受益產業 ↑  Energy_XLE (strong), Defense_ITA (mod)     ║
║  受損產業 ↓  Airlines, Transports, Discretionary, SPY   ║
║  Binary Risk  YES — 2026-04-22 ceasefire expiry         ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel.json ✅  phase0.json ✅    ║
╚══════════════════════════════════════════════════════════╝
```

**ARBITER 加權**：Bull +3 (×0.15) + Bear -5 (×0.30) + Sector +3 (×0.15) + Macro -3.5 (×0.40) = **-2.0**
**Bull-Bear spread = 8** ≥ 4 → 觸發 BINARY 規則
**Binary 48h** → 所有相關產業降一個 verdict 等級

**核心事實**：
- USS Spruance 攔截伊朗船隻 Touska；Iran 取消伊斯蘭堡代表團；停火 2026-04-22 到期
- Brent +5.6-7% to $95.50-96.88（自 3/10 以來新高）；WTI +6% to $89
- 週日 Hormuz 零油輪通過（佔全球 1/5 原油）

**操作建議**：
- LONG `XLE` / `ITA` / `XOM` / `MPC` / `RTX` / `LMT` / `FRO` (tanker rate spike)
- SHORT or trim `JETS` / `AAL` / `DAL` / `IYT` / `FDX` / `XLY`
- 對沖：QQQ put spread / VIX call（macro risk-off 觸發 VaR 去槓桿）
- 歷史類比 1990 Iraq-Kuwait：Brent $17→$36 兩個月，Fed 暫停降息 4 個月，S&P -15%

---

### 🟢 [BULLISH +1.3] n032 — Eli Lilly $7B Acquires Kelonia (In-Vivo CAR-T)

```
╔══════════════════════════════════════════════════════════╗
║  [BULLISH +1.3]  Lilly/Kelonia $7B in-vivo CAR-T deal   ║
║  type: corporate  │  weights: Sector 40%                ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ +4 GLP-1 後第二曲線 + biotech M&A premium    ║
║  BEAR    ⚠ -2 FDA viral vector 監管疑慮 + 現金流壓力    ║
║  SECTOR  ✅ +2 In-vivo 平台 = XBI / 基因療法估值錨       ║
║  MACRO   ➖ +0.3 對 Fed 路徑無傳導                       ║
║  ARBITER → BULLISH，採 Sector 主論點                     ║
╠══════════════════════════════════════════════════════════╣
║  受益產業 ↑  Biotech XBI, Gene Editing (CRSP/BEAM/NTLA) ║
║              Large Pharma XLV (M&A appetite)            ║
║  Cache Updated:  sector_intel.json ✅                    ║
╚══════════════════════════════════════════════════════════╝
```

**核心事實**：$3.25B 上前現金 + 最高 $3.75B 里程碑 = $7B 總額；KLN-1010 = 首款 lentiviral in-vivo CAR-T（Phase 1 多發性骨髓瘤，2025 ASH plenary）；H2 2026 close。

**最大分歧**：Bull-Bear spread = 6（接近 BINARY 線但 Bear conf 0.55 為執行風險，未觸發）
**操作建議**：LONG `CRSP` / `BEAM` / `NTLA` / `VERV` / `CRL`；中性 `LLY`（已 mega-cap）

---

### 🟢 [BULLISH +2.2] n058 — USA Rare Earth $2.8B Acquires Serra Verde

```
╔══════════════════════════════════════════════════════════╗
║  [BULLISH +2.2]  USAR/Serra Verde $2.8B 稀土去風險       ║
║  type: sector_news  │  weights: Sector 50%              ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ +5 唯一非亞洲全 4 磁性 REE + SPV 包銷        ║
║  BEAR    ⚠ -2 巴西 ESG / 中國傾銷 / 股本稀釋             ║
║  SECTOR  ✅ +3 USAR/MP/REMX 結構性 re-rating              ║
║  MACRO   ➖ +0.5 邊際支持中長期供應鏈韌性                 ║
║  ARBITER → BULLISH，採 Sector 主論點                     ║
╠══════════════════════════════════════════════════════════╣
║  受益產業 ↑  Materials/Critical Minerals (USAR/MP)      ║
║              Defense (LMT/RTX), EV OEMs (TSLA/F/GM)     ║
║  Cache Updated:  sector_intel.json ✅                    ║
╚══════════════════════════════════════════════════════════╝
```

**核心事實**：$300M cash + $126.9M USAR 股票首期；Pela Ema 礦區 = 全球唯一非亞洲、可規模化生產 4 種磁性 REE（Nd/Pr/Dy/Tb）+ Y；15 年美政府 SPV 包銷 100% 磁性 REE；2027 底 $550-650M EBITDA；2030 合併 $1.8B EBITDA + 80% 現金轉換。Q3 2026 close。

**最大分歧**：2027 EBITDA 達標機率 — Bull 視 SPV 包銷為近確定，Bear 強調 ramp 執行 + 中國傾銷反制
**操作建議**：LONG `USAR` / `MP` / `REMX` / `PICK`；間接受惠 `LMT` / `RTX` / `TSLA` / `F` / `GM`

---

### ⚠ [NEUTRAL -0.2] n042 — NVDA = 50% of S&P 500 EPS Revisions (Concentration Risk)

```
╔══════════════════════════════════════════════════════════╗
║  [NEUTRAL -0.2 cautionary]  Single-stock = ½ S&P revisn ║
║  type: sentiment  │  weights: Bull 30 / Bear 30         ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ +4 NVDA 盈餘動能真實，正確的少數股票繼續贏   ║
║  BEAR    ❌ -3 末期窄幅，2000Q1 + 2021 末類比             ║
║  SECTOR  ⚖ -1 Mag7↑ vs RSP/IWM↓ (breadth divergence)    ║
║  MACRO   ❌ -1.5 Fed reaction function 綁定 NVDA 5/29   ║
║  ARBITER → NEUTRAL with cautionary tone                  ║
╠══════════════════════════════════════════════════════════╣
║  受益 / 受損  Mega-cap Tech ↑ vs Equal-Weight ↓          ║
║              SPY = binary (NVDA earnings event-driven)  ║
║  Cache Updated:  phase0 mandatory_risk_flag 重申 ✅      ║
╚══════════════════════════════════════════════════════════╝
```

**ARBITER 加權**：Bull +4 (×0.30) + Bear -3 (×0.30) + Sector -1 (×0.15) + Macro -1.5 (×0.25) = **-0.225**
**核心事實**：NVDA 一家貢獻 ~50% S&P 500 EPS 上修；NVDA ~8% 指數權重；Mag7 +22.8% YoY EPS Q1 vs 其他 493 +10.1%；Top 20 = 50% 指數
**與 Phase 0 mandatory_risk_flag「Narrow_rally_late_cycle」完全吻合**
**操作建議**：減碼 mega-cap concentration，加碼 RSP / equal-weight 對沖；NVDA 5/29 財報前控制 SPY beta

---

### 🟡 [NEUTRAL +0.5] n065 — Cursor $50B Valuation, $2B Raise

```
╔══════════════════════════════════════════════════════════╗
║  [NEUTRAL +0.5 bullish-lean]  Cursor $50B (從 $29.3B)   ║
║  type: sentiment  │  weights: Bull 30 / Bear 30         ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ +3 AI 應用層 monetization 第一波驗證         ║
║  BEAR    ⚠ -2 Vendor financing + AI bubble froth         ║
║  SECTOR  ✅ +3 NVDA/AVGO/MU pull-through 加速            ║
║  MACRO   ⚠ -1 Fed 鷹派可能引用為 FCI 過鬆證據            ║
║  ARBITER → NEUTRAL，AI infra bullish / late-stage VC↓   ║
╠══════════════════════════════════════════════════════════╣
║  受益產業 ↑  AI Infra (NVDA/AVGO/MU), SaaS (IGV)        ║
║              Data Center Power (VST/CEG)                ║
║  Cache Updated:  sector_intel.json ✅                    ║
╚══════════════════════════════════════════════════════════╝
```

**核心事實**：Cursor 6 個月估值 $29.3B → $50B+（+70%）；ARR $2B (Feb) → 預期 $6B (year-end 2026, 3x in 10 months)；NVIDIA 戰略入股 + Thrive/A16z lead + Battery 新加入。
**操作建議**：infra side（NVDA/AVGO/VST/CEG）持有，application side（ARKK/late-stage AI SPAC）警惕 mark-down 風險

---

## 3. Shallow Digest（top 10 — Stage 1 未晉級項目）

### [+2.8] n030  Data center demand drives upside for range of semis ahead of earnings: Susquehanna
- **Bull**: 資料中心 capex 補增帶動 SOXX 全鏈條 EPS 上修
- **Bear**: Sell-side preview 已是市場 consensus，beat 門檻提高
- **Sector**: Semis bullish moderate，下游 utilities 同步受惠
- **Macro**: AI capex 持續性對 GDP 成長提供結構性支撐
- Source: Seeking Alpha MEDIUM │ type: sector_news

---

### [-2.6] n050  Investors are misreading news about the Iran war, analysts say as markets whipsaw
- **Bull**: 誤讀利空 = 提供低點吸籌窗口（解放日類比）
- **Bear**: 頻繁逆轉反映 narrative 真空，volatility regime 已轉
- **Sector**: 對 SPY/QQQ broad 中性，VIX 持續溢價
- **Macro**: geopolitical premium 重新嵌入風險溢酬模型
- Source: CNBC HIGH │ type: sentiment

---

### [-2.4] n047  Kevin Warsh would be the first tech bro Fed chair. How Silicon Valley shaped him
- **Bull**: 親 AI tech 主席 = 對風險資產偏鴿、容忍 valuation
- **Bear**: 矽谷意識形態進入央行 = 政策獨立性疑慮
- **Sector**: Tech bullish；Bank bearish（YC 形狀疑慮）
- **Macro**: Fed 路徑潛在系統性偏鴿，long-end yield 風險升
- Source: CNBC HIGH │ type: monetary_policy

---

### [+2.4] n044  Psychedelic stocks jump as high as 40% after Trump supports using drugs like LSD for mental health
- **Bull**: FDA fast-track 路徑開啟，COMP/CMPS/MNMD 估值重估
- **Bear**: 政策方向易反覆，Phase 3 數據缺口仍大
- **Sector**: 迷幻藥小型生技 bullish strong（短期動能）
- **Macro**: 對 Fed/macro 無傳導，純題材交易
- Source: MarketWatch HIGH │ type: sector_news

---

### [-2.3] n066  Wall Street just sent oil stocks a brutal message after Iran's move
- **Bull**: 油股 oversold + crude 上行 = mean-reversion setup
- **Bear**: XLE 不跟 crude = 市場 price-in demand destruction
- **Sector**: XLE binary，需配合 4/22 停火窗口判斷
- **Macro**: demand destruction narrative 對 growth 偏空
- Source: Yahoo Finance HIGH │ type: sector_news

---

### [+2.2] n024  Marvell Stock Pops Amid AI Chip Talks With Google. Why It's Worrying for Broadcom.
- **Bull**: MRVL 取得 GOOG TPU 訂單 = 客製 ASIC 雙供應商建立
- **Bear**: AVGO 既有 share 受威脅，TAM 切割壓力
- **Sector**: MRVL bullish strong；AVGO bearish moderate
- **Macro**: 對 macro 無顯著傳導
- Source: Yahoo Finance HIGH │ type: corporate

---

### [+2.1] n067  Software stock dogs have joined market rally
- **Bull**: MSFT 跌 20% 後反彈，IGV 補漲行情啟動
- **Bear**: rally 末期狗股輪動 = 動能耗盡訊號
- **Sector**: Software IGV bullish moderate（短期動能）
- **Macro**: 對 macro 無顯著傳導
- Source: CNBC HIGH │ type: sector_news

---

### [+2.0] n063  Japan's Mitsubishi Heavy Industries first-ever warship export deal
- **Bull**: 日本國防出口解禁 = 全球軍工 backlog 重建敘事
- **Bear**: 美系國防股佔比下降，採購預算分散
- **Sector**: Defense_ITA bullish moderate（國際標案放大）
- **Macro**: 對 Fed/macro 無傳導
- Source: CNBC HIGH │ type: sector_news

---

### [-1.9] n048  Why the hidden mechanics behind the market's record run may no longer be helping stocks
- **Bull**: 若 vol 收斂，dealer gamma 重新支撐
- **Bear**: Options gamma 反向 = volatility regime shift
- **Sector**: 對 SPY/QQQ broad 偏空（vol 結構轉變）
- **Macro**: 市場結構脆弱性提升，VaR 下行風險加大
- Source: MarketWatch HIGH │ type: sentiment

---

### [+1.7] n061  UniCredit boss plots Commerzbank shake-up
- **Bull**: 歐銀整併潮利多 cross-border 估值重估
- **Bear**: 德國政治阻力與工會反對是長期障礙
- **Sector**: 歐洲 Banks bullish weak（敘事支撐）
- **Macro**: 對美股 macro 影響有限
- Source: CNBC HIGH │ type: corporate

---

## 4. Session Summary

**整體 macro_backdrop_score 變動**：-0.5 → **-0.7**（session_macro_delta -0.4 × 50% 半衰權重）

**最高優先級訊號**：
1. 🚨 **n057** 4/22 停火到期 within_48h → 既有 binary_risk 重新確認 high_risk
2. ⚠ **n042** NVDA 集中度警鐘 → mandatory_risk_flag「Narrow_rally_late_cycle」二度確認
3. 🟢 **n058** 稀土供應鏈結構性利多 → top_catalysts rank 2

**Cache patches**：
- `sector/sector_logs/2026-04-19_sector_intel.json` → `top_catalysts` 前 5 名替換為今日新聞
- `investment/invest_logs/2026-04-19_phase0.json` → `macro_backdrop_score` -0.5 → -0.7；`news_patch_count` 5 → 10；`binary_risks[0]` Hormuz 條目 `updated_at` 重整

**Pending Dashboard 操作建議**：
- 開盤前重新跑 `python3 bridge.py` 將最新 cache 整合到 Dashboard
- 重點觀察：4/22 停火窗口、NVDA 5/29 財報、TSLA/GOOGL 4/22 財報、FOMC 4/29

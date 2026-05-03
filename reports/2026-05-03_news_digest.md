# News Digest — 2026-05-03

> **Mode**: DIGEST | **Stage 1 Triage**: 159 raw → top 5 deep + 10 shallow JSON / 20 shallow MD
> **Fanout Mode**: PER_AGENT_BATCH (4 subagent isolated) | **Schema**: V2.1
> **Session Macro Delta**: -0.9 | **macro_backdrop**: -0.72 → -0.99
> **Sources**: RSS (45) + Finnhub (6) + FMP (113) + SEC EDGAR (0) → dedupe 159

---

## ⚠️ Active Binary Risks (within 48h)

| # | Event | Expires | Category |
|---|---|---|---|
| 1 | OPEC+ +188k bpd nominal but Hormuz physically blocks delivery; Brent $126; UAE exit from cartel | 2026-05-05 | geopolitical |
| 2 | Trump signals possible restart of US strikes on Iran | 2026-05-05 | geopolitical |
| 3 | Fed independence at risk — Trump legal challenges, Powell forced to stay as governor | 2026-06-01 | monetary_policy |

---

## 📊 Triage Summary (Stage 1)

```
╔══════════════════════════════════════════════════════════════════════════╗
║  NEWS TRIAGE  │  2026-05-03 20:55  │  159 raw → 5 deep + top-20 shallow ║
╠══════════════════════════════════════════════════════════════════════════╣
║  ✅ DEEP   n0091  [-2.4]  Powell stays / Trump Fed challenge   monetary ║
║  ✅ DEEP   n0095  [BIN]   OPEC+ 3rd hike since Hormuz closure  geopol   ║
║  ✅ DEEP   n0107  [+2.3]  Alphabet $190B AI capex / 3 semis    corporate║
║  ✅ DEEP   n0157  [-2.8]  US-Iran war hits credit/mortgage     macro    ║
║  ✅ DEEP   n0083  [-0.8]  SMH +141% 1Y, valuation alarm        sentiment║
║  ────────────────────────────────────────────────────────────────────── ║
║  ⚠ SHAL    n0126  [-3.0 BIN] Trump may restart Iran strikes   geopol    ║
║  ✅ SHAL   n0048  [+3.0]  US crude exports record 5.2M bpd     sector   ║
║  ⚠ SHAL    n0031  [-2.8]  Iran disrupts electronics supply    sector   ║
║  ✅ SHAL   n0034  [+2.5]  Nebius AI breakout, Meta/NVDA deals  corp     ║
║  ✅ SHAL   n0050  [+2.5]  Sanmina AI EMS undervalued           corp     ║
║  ✅ SHAL   n0148  [+2.5]  S&P/Nasdaq record rally, +10.4% Apr  sentiment║
║  ✅ SHAL   n0086  [+2.5]  Seagate strong fiscal Q3, AI HDD     earnings ║
║  ⚠ SHAL    n0019  [-2.5]  Fed unchanged 3.5-3.75%, Warsh chr  monetary ║
║  ⚠ SHAL    n0152  [-2.5]  Diesel prices skyrocket, SMB squeeze macro    ║
║  ⚠ SHAL    n0003  [-2.5]  Detroit autos $5B commodity spike   sector   ║
║  ⚠ SHAL    n0092  [-2.5]  Roblox slashed guidance             corp     ║
║  ❌ SKIP   n0079  [-2.0]  NVDA $110 crash call (single expert) sentiment║
║  ⚠ SKIP    n0142  [-2.0]  MarketWatch: higher inflation       macro    ║
║  ✅ SKIP   n0104  [+2.0]  Goldman: AI software selloff overdone sector  ║
║  ✅ SKIP   n0033  [+2.0]  Constellium Q1 strong, raised guide  earnings ║
║  ✅ SKIP   n0040  [+2.0]  Celestica AI infra, AMD partner      earnings ║
║  ⚠ SKIP    n0145  [-1.8]  Private credit hiding losses (MW)   sentiment║
║  ✅ SKIP   n0125  [+1.8]  EM stocks powering past Iran war     macro    ║
║  ✅ SKIP   n0005  [+1.8]  Israel approves F-35/F-15 from LMT/BA defense ║
║  ✅ SKIP   n0035  [+1.5]  CEO warns on critical minerals         sector ║
║  ... (139 more skipped — class-action notices, retiree finance,         ║
║       crypto promo, foreign-language PR, daily mortgage rate spam)      ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 🎯 Deep Analysis (Stage 2)

### 1. [BEARISH -2.4] n0091 — Powell stays on Fed board / Trump legal challenges threaten Fed independence

```
╔══════════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-05-03 05:00 UTC  │  type: monetary_policy║
╠══════════════════════════════════════════════════════════════╣
║  weights: Bull 15 / Bear 15 / Sector 20 / Macro 50            ║
║  scores:  Bull +3 / Bear -4 / Sector -1 / Macro -4            ║
║  arbiter:  -2.35 → BEARISH (Macro lane dominant)              ║
║  binary_risk: true (SCOTUS timing unknown, not within 48h)    ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ BULL    Powell as governor 制度錨; Warsh 鴿派 + 制度錨 = 6月再降 25bp   ║
║  ❌ BEAR    Fed credibility 折價推升 10Y term premium +30-50bp; TLT -4~-7% ║
║  ➖ SECTOR  XLF mixed; KRE 雙重打擊（duration + CRE）；GLD/IBIT 受惠      ║
║  ❌ MACRO   1951 Treasury-Fed Accord 以來最嚴重央行政治化壓力測試         ║
║             1972 Burns/1978 Miller historical analogue                  ║
║             Fed path: remove 50bp of 2026 cuts; 10Y +30-50bp             ║
║  ARBITER → BEARISH, 採 Macro 主論點 (50% weight)                         ║
╠══════════════════════════════════════════════════════════════╣
║  受惠 ↑  Gold (GLD/GDX), BTC (IBIT)                          ║
║  受損 ↓  Financials, Regional Banks (KRE), Utilities, TLT     ║
║  Tickers: XLF KRE KBE GLD GDX IBIT TLT XLU                    ║
╠══════════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel ✅  phase0 ✅                  ║
╚══════════════════════════════════════════════════════════════╝
```

**Debate Note**: Macro/Bear（Fed independence 折價 → long-end 失控）vs Bull（Warsh 鴿派 + Powell 制度錨 = 6 月再降息 pricing）最大分歧：term premium 走向。Warsh 鴿派 vs hawkish overcompensate 路徑分岔點。

---

### 2. [BINARY -2.3] n0095 — OPEC+ third oil hike since Hormuz closure (largely on paper)

```
╔══════════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-05-03 03:58 UTC  │  type: geopolitical  ║
╠══════════════════════════════════════════════════════════════╣
║  weights: Bull 15 / Bear 30 / Sector 15 / Macro 40            ║
║  scores:  Bull +4 / Bear -5 / Sector +4 / Macro -5            ║
║  arbiter:  -2.30 → BINARY (max-min spread = 9, true binary)   ║
║  binary_risk: true (within_48h=true; Iran retaliation window) ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ BULL    US 頁岩 XOM/CVX/EOG/PXD FCF 12-18%; 油服 SLB/HAL; LNG          ║
║  ❌ BEAR    +188k bpd 'on paper' 揭露供給崩壞; 航空+消費+工業 demand 毀滅 ║
║  ✅ SECTOR  XLE/XOP strong; Tankers FRO/STNG VLCC TCE 破 2008 高點         ║
║  ❌ MACRO   1979 stagflation 困境; Fed 若 Brent 破 $150 須升息 25-50bp     ║
║  ARBITER → BINARY, Sector 看 US 能源 alpha vs Macro/Bear 看 SPY 廣義 demand 殺戮 ║
╠══════════════════════════════════════════════════════════════╣
║  受惠 ↑  Energy (XLE/XOP), Oil Services (OIH), Tankers       ║
║  受損 ↓  Cons Discretionary (XLY), Airlines (JETS), Industrials║
║  Tickers: XLE XOP OIH BNO USO FANG PXD EOG SLB FRO STNG EURN  ║
║           JETS XLY DAL AAL                                     ║
╠══════════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel ✅  phase0 ✅                  ║
╚══════════════════════════════════════════════════════════════╝
```

**Debate Note**: Sector（US 能源 + tankers FCF 爆表 bullish strong）vs Bear/Macro（demand destruction + 1979 stagflation 重演）最大分歧：能源族群 alpha vs 廣義 SPY beta 哪個贏。Bull 看 'sweet spot $110-130' vs Bear 看 '一旦破 $150 立刻 stagflation'。

---

### 3. [BULLISH +2.3] n0107 — Alphabet $190B AI capex / 3 semi winners

```
╔══════════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-05-03 02:02 UTC  │  type: corporate     ║
╠══════════════════════════════════════════════════════════════╣
║  weights: Bull 25 / Bear 25 / Sector 40 / Macro 10            ║
║  scores:  Bull +5 / Bear -3 / Sector +4 / Macro +2            ║
║  arbiter:  +2.30 → BULLISH (Sector lane dominant)             ║
║  binary_risk: false                                           ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ BULL    AVGO ASIC contract 2031, AI rev $15B→$100B; TSM 90% adv AI    ║
║              NVDA 86% DC share + Blackwell/Rubin 路線圖延伸 2027           ║
║  ❌ BEAR    GOOGL incremental ROIC 崩壞 (capex 2.5x vs revenue +10%)      ║
║              ASIC/inhouse silicon 蠶食 NVDA; SMH P/E 142x cycle 頂        ║
║  ✅ SECTOR  Hyperscaler combined ~$700B 創高; AVGO 是最高信號 idiosyncratic║
║  ➕ MACRO   1965-69 guns-and-butter 重演; GDP 直接貢獻 1.2-1.5pp           ║
║  ARBITER → BULLISH, 採 Sector 主論點 (40% weight)                         ║
╠══════════════════════════════════════════════════════════════╣
║  受惠 ↑  Semis (SMH/SOXX), Semi Equip, HBM Memory, DC Power   ║
║  受損 ↓  None (relative; Bear 警示保留至 Q3 hyperscaler guidance)║
║  Tickers: SMH SOXX AVGO TSM NVDA GOOGL ASML AMAT ANET CRDO    ║
║           ALAB VST CEG MU LRCX                                 ║
╠══════════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel ✅  phase0 ✅                  ║
╚══════════════════════════════════════════════════════════════╝
```

**Debate Note**: Bull/Sector（hyperscaler $700B 三條訂單線兌現）vs Bear（GOOGL incremental ROIC 崩壞 + ASIC/inhouse silicon 蠶食 NVDA）最大分歧：capex 是 secular（Bull）還是 cyclical 頂部（Bear）。Q3 earnings 為 trigger window。

---

### 4. [BEARISH -2.8] n0157 — US-Iran war hits credit scores & mortgage applications

```
╔══════════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-05-02 13:17 UTC  │  type: macro_data    ║
╠══════════════════════════════════════════════════════════════╣
║  weights: Bull 15 / Bear 15 / Sector 20 / Macro 50            ║
║  scores:  Bull +3 / Bear -4 / Sector -3 / Macro -4            ║
║  arbiter:  -2.75 → BEARISH (Macro+Sector aligned)             ║
║  binary_risk: false                                           ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ BULL    JPM/BAC/WFC 大者愈大; BX/KKR private credit IRR 15-20%        ║
║  ❌ BEAR    KRE NIM -20-30bp; sub-700 FICO 違約 4.2%→6%; XHB EPS -15%      ║
║  ❌ SECTOR  KRE/XHB/COF/AFRM/ALLY 三條 sector kill list                    ║
║  ❌ MACRO   1979-82 Volcker stagflation 困境; GDP 衰退機率 25%→55%        ║
║  ARBITER → BEARISH, 採 Macro+Sector 主論點 (50% + 20% weight)              ║
╠══════════════════════════════════════════════════════════════╣
║  受惠 ↑  Money Center Banks (JPM/BAC), Utilities (defensive)  ║
║  受損 ↓  Regional Banks, Homebuilders, Cons Finance, BNPL     ║
║  Tickers: KRE KBE XHB ITB XLY XRT COF DFS AFRM ALLY DHI LEN   ║
║           PHM JPM BAC WFC BX KKR MCO SPGI                      ║
╠══════════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel ✅  phase0 ✅                  ║
╚══════════════════════════════════════════════════════════════╝
```

**Debate Note**: Bull（信用緊縮 = 大者愈大、JPM/BX 受惠）vs Bear/Macro（典型 stagflation credit cycle turn → 衰退機率 55%）最大分歧：是個股 dispersion event 還是 systemic recession。

---

### 5. [NEUTRAL -0.8] n0083 — SMH +141% 1Y, recent 42% rally signals dangerous valuations

```
╔══════════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-05-03 06:15 UTC  │  type: sentiment     ║
╠══════════════════════════════════════════════════════════════╣
║  weights: Bull 30 / Bear 30 / Sector 15 / Macro 25            ║
║  scores:  Bull +4 / Bear -4 / Sector -2 / Macro -2            ║
║  arbiter:  -0.80 → NEUTRAL (Bull/Bear 對撞 + Sector/Macro mild bear) ║
║  binary_risk: false                                           ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ BULL    PEG ~1.1 + EPS 30-50% 成長撐住 P/E 28-30x; AVGO/TSM/Memory laggard║
║  ❌ BEAR    +141% 1Y = 2000/1989/2021 melt-up 末期; insider selling 18:1   ║
║  ➖ SECTOR  reduce SMH ETF beta 50%; 集中個股 AVGO/TSM; SOXS/VIX hedge     ║
║  ➖ MACRO   1999 Q4 SOX 路徑類似但 monetization 真實，下行 -30~-40% not -85%║
║  ARBITER → NEUTRAL, 配置層面降 ETF beta 但保留 AVGO/TSM 個股 alpha         ║
╠══════════════════════════════════════════════════════════════╣
║  受惠 ↑  Defensive (XLP/XLU), VIX hedges                      ║
║  受損 ↓  SMH/SOXX (overheated)                                ║
║  Tickers: SMH SOXX SOXS NVDA AVGO TSM INTC QCOM MRVL AMAT     ║
║           LRCX KLAC MU XLP XLU VIX                             ║
╠══════════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel ✅  phase0 ✅                  ║
╚══════════════════════════════════════════════════════════════╝
```

**Debate Note**: Bull（PEG ~1.1 + EPS 30-50% 成長撐住 P/E 28-30x）vs Bear（RSI 月線 >85 + insider selling 18:1 + 散戶 capitulation buying $9.2B）最大分歧：fundamentals vs technicals 哪個先觸發 reprice。

---

## 📰 Shallow Digest (Top 20)

### [-3.0 BIN] n0126  Trump says US could restart strikes on Iran
- **Bull**: 防衛股 LMT/RTX/NOC/GD 受惠
- **Bear**: Brent 突破 $150，SPY -3% gap
- **Sector**: Defense+strong, Energy+strong, SPY-
- **Macro**: Fed hold, DXY safe-haven bid +1.5%
- Source: Reuters HIGH │ type: geopolitical │ binary_risk within_48h
---

### [+3.0] n0048  US crude oil exports surge to record (5.2M bpd) during Iran war
- **Bull**: US E&P FCF 爆表 EOG/PXD/FANG/XOM
- **Bear**: 高油價最終由需求毀滅
- **Sector**: Energy+strong, Tankers+strong
- **Macro**: USD oil-export 順差擴大
- Source: CNBC HIGH │ type: sector_news
---

### [-2.8] n0031  Tech prices could rise as Iran conflict disrupts electronics supply chain
- **Bull**: 供應鏈 reshore 受惠 INTC/GFS
- **Bear**: AAPL/Dell GM 壓縮
- **Sector**: Hardware-, Reshoring+
- **Macro**: Goods CPI MoM +0.3%
- Source: Fox Business HIGH │ type: sector_news
---

### [+2.5] n0034  Nebius near breaking out, AI bears silenced (Meta/NVDA deals)
- **Bull**: $643M Eigen AI 收購打開 open-source AI 領導地位
- **Bear**: AI infra 第二供應商替代風險
- **Sector**: AI infra+, NeoCloud peers+
- **Macro**: AI capex spillover 持續
- Source: Seeking Alpha HIGH │ type: corporate
---

### [+2.5] n0050  Sanmina — AI Supercycle's Most Undervalued Manufacturer
- **Bull**: ZT Systems 資料中心訂單超預期
- **Bear**: EMS 微利率 < 5%，需訂單持續
- **Sector**: AI-EMS+strong (CLS/SANM/FN)
- **Macro**: AI capex spillover at margins
- Source: MarketBeat HIGH │ type: corporate
---

### [+2.5] n0148  S&P 500 / Nasdaq kept record rallies; April +10.4%
- **Bull**: 漲勢由 corporate earnings 驅動
- **Bear**: 極端集中 Mag 7 + 戰時警示
- **Sector**: Mega-cap+ vs broad mixed
- **Macro**: RoR 持續但 RoR/Risk 比惡化
- Source: CNBC HIGH │ type: sentiment
---

### [+2.5] n0086  Seagate stock skyrocketed — fiscal Q3 strong, AI HDD demand
- **Bull**: AI cold-storage HDD 需求驅動
- **Bear**: Memory cycle 已 priced in
- **Sector**: Storage+strong, Memory+
- **Macro**: AI capex spillover
- Source: Motley Fool HIGH │ type: earnings
---

### [-2.5] n0019  Will Powell have influence when Warsh assumes Fed Chairman role?
- **Bull**: Warsh 鴿派傾向支撐降息預期
- **Bear**: FOMC 公開分裂訊號矛盾
- **Sector**: Rate-sensitive 短多長空
- **Macro**: QE 結束 + flexible policy 不透明
- Source: Seeking Alpha HIGH │ type: monetary_policy
---

### [-2.5] n0152  CHOKEPOINT — diesel prices skyrocket, squeeze SMBs
- **Bull**: 煉油 VLO/MPC crack spread 擴大
- **Bear**: 卡車/物流 Russell 2000 EBITDA 壓縮
- **Sector**: Refiners+, Trucking-
- **Macro**: Goods inflation MoM +0.4-0.6%
- Source: Fox Business HIGH │ type: macro_data
---

### [-2.5] n0003  Detroit automakers warn commodity spike could add $5B in costs
- **Bull**: 傳遞至消費者 ARPU 提升
- **Bear**: GM/F/STLA EPS -10~-15%
- **Sector**: Autos-strong, Mining+
- **Macro**: PPI durable goods +0.3%
- Source: Seeking Alpha MED │ type: sector_news
---

### [-2.5] n0092  Roblox shares tumble after company slashed guidance
- **Bull**: 年齡驗證合規領先同業
- **Bear**: 用戶成長放緩，FY26 收入下修
- **Sector**: Gaming-, Metaverse-
- **Macro**: 消費降級延伸至數位娛樂
- Source: Motley Fool HIGH │ type: corporate
---

### [-2.0] n0079  Trading expert sets date Nvidia stock will crash to $110
- **Bull**: 估值仍由 EPS 50% 成長撐住
- **Bear**: 散戶 capitulation buy + 技術 RSI 過熱
- **Sector**: SMH 短線消化, 個股 dispersion
- **Macro**: 對 Fed 路徑無直接影響
- Source: Finbold HIGH │ type: sentiment │ ⚠ single-analyst opinion
---

### [-2.0] n0142  MarketWatch: higher inflation is on the way; Fed needs to communicate
- **Bull**: TIPS/實質資產配置受惠
- **Bear**: Fed easing bias 被迫暫停
- **Sector**: Energy+, Long-duration tech-
- **Macro**: Re-acceleration risk; 1979 警示
- Source: MarketWatch HIGH │ type: macro_data
---

### [+2.0] n0104  Goldman: AI software sell-off was overdone; growth names to buy
- **Bull**: 軟體 P/S compression 已過度
- **Bear**: Anthropic Mythos 衝擊 SaaS moat
- **Sector**: SaaS dispersion, 大者愈大
- **Macro**: Tech earnings beat 維持 Risk-on
- Source: Motley Fool HIGH │ type: sector_news
---

### [+2.0] n0033  Constellium SE — conviction boost, strong Q1 FY2026 earnings
- **Bull**: Pass-through pricing power 維持，FY26 guide $920M EBITDA
- **Bear**: 包裝市場已成熟
- **Sector**: Aluminium+, Packaging+
- **Macro**: 工業金屬 demand 韌性
- Source: Seeking Alpha HIGH │ type: earnings
---

### [+2.0] n0040  Celestica — AI Infrastructure Dominance Meets Supply Chain Realities
- **Bull**: AMD partnership + hyperscaler capex 紀錄
- **Bear**: 元件短缺 revenue push-out 風險
- **Sector**: AI EMS+, Network+
- **Macro**: AI capex spillover 持續
- Source: Seeking Alpha HIGH │ type: earnings
---

### [-1.8] n0145  Private credit isn't safer than banks — better at hiding losses
- **Bull**: 透明度低 = 高 IRR 機會
- **Bear**: BX/KKR/APO mark-to-myth 風險
- **Sector**: Private Credit Funds-
- **Macro**: 與 n0157 信貸週期共振
- Source: MarketWatch HIGH │ type: sentiment
---

### [+1.8] n0125  Emerging-Market Stocks Are Powering Past the War (WSJ)
- **Bull**: AI + 油價推升南韓/巴西
- **Bear**: USD safe-haven 拉升將反向
- **Sector**: EM Equity+ (EWZ/EWY)
- **Macro**: AI/oil 雙引擎延續
- Source: WSJ HIGH │ type: sentiment
---

### [+1.8] n0005  Israel approves plan to buy F-35 and F-15IA from Lockheed/Boeing
- **Bull**: LMT/BA 海外訂單能見度延伸 2030
- **Bear**: BA 737 MAX 仍需消化品質
- **Sector**: Defense+strong (ITA/LMT/BA/NOC)
- **Macro**: 中東軍備循環延長
- Source: Investing.com MED │ type: geopolitical
---

### [+1.5] n0035  CEO sounds alarm on foreign reliance on critical minerals (antimony)
- **Bull**: 國防原物料 reshore — USAS/MP 受惠
- **Bear**: 開採許可週期長
- **Sector**: Critical Minerals+ (MP/USAS/UEC)
- **Macro**: 戰略物資供應鏈安全主題
- Source: Fox Business HIGH │ type: sector_news
---

## 🔧 Phase 4 Cache Patches

| File | Action |
|---|---|
| `sector/sector_logs/2026-05-03_sector_intel.json` | 4 catalysts prepended (n0091/n0095/n0107/n0157) |
| `sector/sector_logs/phase0.json` | macro_backdrop -0.72 → -0.99 (clamped); 4 binary_risks (1 expired pruned, 3 added) |
| `news/news_logs/2026-05-03_digest.json` | 5 deep + 10 shallow verdicts; validator rc=0 ✅ |

---

## 🎯 Top-Level Takeaways

1. **Macro_backdrop hits floor (-0.99)** — 三大 BEARISH 疊加（Fed 獨立性 + 信貸緊縮 + Iran war 第三輪 OPEC 紙上增產）。
2. **Single offset BULLISH**: Alphabet $190B AI capex 為 hyperscaler $700B 訂單能見度確認；AVGO/TSM/NVDA 為核心受惠者，但與 n0083 SMH 過熱警報形成 tension（個股 alpha vs ETF beta）。
3. **Active 48h binary risks**: Trump may restart Iran strikes（expires 2026-05-05）+ OPEC+ 紙上增產（expires 2026-05-05）→ 所有相關產業降一個 verdict 等級。
4. **Stagflation 雛形**: macro_backdrop -0.99 + Brent $126 + Fed credibility 折價 + lender tightening = 1979-82 Volcker 困境路徑風險升高。
5. **Sector rotation 建議**：Energy/Tankers OW；Money Center Banks/Defense/Gold OW；Regional Banks/Homebuilders/Cons Finance UW；Semis 個股 selective（AVGO/TSM）+ ETF beta 降配。

# News Digest — 2026-04-26 (DIGEST Mode)

> Protocol: News V2.1 · Fan-out: PER_AGENT_BATCH · Stage 1: 40 → Stage 2 deep: 5 · session_macro_delta: **-0.3**

## Phase 0 Macro 快照

- **Regime**: RISK_ON · Mid-cycle · Exposure 60-75%
- **Breadth** 43.3 (Neutral) | **FTD** CONFIRMED (Q100) | **Market Top** 29.2 (Early_Warning)
- **FRED**: Overheating (conf 0.71), composite 62; yield curve +0.53 not inverted; HY/NFCI accelerating warnings
- **Sector favor**: Energy / Materials / Financials | **Avoid**: Tech / Real Estate / Discretionary
- **Near-term binary**: FOMC 4/28-4/29, Warsh Senate vote 4/29, AMZN earnings 4/30, META/GOOGL 4/29

---

## Triage Summary (40 items → 5 deep)

```
╔══════════════════════════════════════════════════════════════════════╗
║  NEWS TRIAGE  │  2026-04-26 12:30  │  40 則 → 5 則晉級              ║
╠══════════════════════════════════════════════════════════════════════╣
║  ✅ DEEP   n011  [-3.5]  Trump cancels Iran negotiations  geopolitical
║  ✅ DEEP   n004  [+3.2]  US shale refuses to boost oil    sector_news 
║  ✅ DEEP   n034  [-3.2]  AI talent war hits SaaS          sector_news 
║  ✅ DEEP   n010  [+3.0]  Memory stocks buy call (HBM)     sector_news 
║  ✅ DEEP   n021  [+3.0]  AI gold mines: Defense/Health    sector_news 
║  ──────────────────────────────────────────────────────────────────── 
║  ❌ SHALLOW (top 10 by |score|):                                     
║       n014 [-2.8] private credit fad peaked              sentiment   
║       n002 [-2.5] WHCD shooter / Trump safe              geopolitical
║       n016 [+2.5] Bonds lag stocks 2026 (contrarian)     sentiment   
║       n017 [-2.5] Apple new CEO AI gap concern           corporate   
║       n038 [+2.5] BWET tanker ETF +600% YTD              sector_news 
║       n040 [+2.0] US +$26B unrealized on Intel trade     corporate   
║       n032 [+2.0] Goldman: 100 IPOs $160B in 2026        sector_news 
║       n020 [+2.0] LMT CEO Mid East 2-word message        sector_news 
║       n012 [+1.5] Key M&A: HLX/TSLA/QXO/USAR             corporate   
║       n022 [+1.5] BRK entry point post-underperformance  corporate   
║  ❌ SKIP (≤ |1.5|): n001/n003/n005-n008/n013/n015/n018-n019/n023-n031/n033/n035-n037/n039 (24 則)
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Deep Analysis — Impact Cards

### [BINARY -1.1] n011 · Trump cancels Witkoff/Kushner Pakistan trip; Iran refuses negotiations

```
╔══════════════════════════════════════════════════════════════╗
║  type: geopolitical  │  weights: B15 / Br30 / S15 / M40      ║
║  source: CNBC Top (HIGH)                                     ║
╠══════════════════════════════════════════════════════════════╣
║  BULL    +4.0  Energy/Defense/Shipping benefit from extended ║
║                stalemate; Hormuz cost-push extends           ║
║  BEAR    -4.0  Risk-off unwind trigger + FOMC binary col-    ║
║                lision; Brent $120-140 tail; VIX 35+ tail     ║
║  SECTOR  +2.8  Energy E&P + Tankers (BWET +600%) winners;    ║
║                Industrials/Materials/Staples cost-pressed    ║
║  MACRO   -2.2  Hormuz extension lifts CPI; Fed dilemma;      ║
║                1990 Iraq-Kuwait analogue; DXY/Gold bid       ║
╠══════════════════════════════════════════════════════════════╣
║  ARBITER → BINARY (binary_risk + within_48h, |spread|=8)     ║
║  受益 ↑  Energy strong / Defense strong / Shipping strong    ║
║  受損 ↓  Industrials_Transport / Materials / Staples         ║
║  Tickers  XOM CVX EOG FANG SLB OXY LMT RTX FRO STNG          ║
║          DAL UAL DOW LYB (avoid)                             ║
║  Cache: sector_intel ✅  phase0 ✅                            ║
╚══════════════════════════════════════════════════════════════╝
```

**Debate Note**: Bull/Bear 8-pt spread；最大分歧『市場是否已將地緣風險充分定價』—Bull yes, Bear no。

---

### [BULLISH +1.3] n004 · U.S. shale industry reluctant to boost production

```
╔══════════════════════════════════════════════════════════════╗
║  type: sector_news  │  weights: B20 / Br20 / S50 / M10       ║
║  source: Seeking Alpha (MEDIUM, conf cap 0.7)                ║
╠══════════════════════════════════════════════════════════════╣
║  BULL    +4.0  Shale 2.0 capital discipline = OPEC+ pricing  ║
║                power; FCF yield 8-12%; multi-quarter alpha   ║
║  BEAR    -3.0  Tier-1 inventory exhaustion + demand destr.   ║
║                ahead (Brent>$100 持 6m → ISM <48)            ║
║  SECTOR  +2.5  E&P + Midstream pure winners; Refiners/Chems/ ║
║                Airlines cost-squeezed                        ║
║  MACRO   -1.5  Sticky $80+ floor → CPI 黏 → Fed cut window   ║
║                收斂；2005-2007 OPEC discipline analogue      ║
╠══════════════════════════════════════════════════════════════╣
║  ARBITER → BULLISH on Energy (Sector 50% 主導)               ║
║  受益 ↑  Energy strong / Midstream moderate                  ║
║  受損 ↓  Refiners / Materials_Chems / Airlines (moderate)    ║
║  Tickers  FANG PXD EOG CTRA OVV EPD ET KMI XOM CVX           ║
║          VLO MPC DOW LYB DAL UAL (avoid)                     ║
║  Cache: sector_intel ✅  phase0 ✅                            ║
╚══════════════════════════════════════════════════════════════╝
```

**Debate Note**: Sector(+2.5) vs Macro(-1.5) 4-pt spread；分歧『高油價持續時間』—Sector 看 multi-quarter 窗口、Macro 看 6m 後 demand destruction。

---

### [BEARISH -1.0] n034 · AI talent war hits enterprise software (OpenAI poaching)

```
╔══════════════════════════════════════════════════════════════╗
║  type: sector_news  │  weights: B20 / Br20 / S50 / M10       ║
║  source: CNBC Top (HIGH)                                     ║
╠══════════════════════════════════════════════════════════════╣
║  BULL    +3.0  K-shape: Hyperscalers/AI infra winners        ║
║                (NVDA/MSFT/AVGO/MU); legacy SaaS contrarian   ║
║  BEAR    -4.0  Multiple compression CRM/ADBE/NOW/ORCL 6-10x  ║
║                → 4-6x P/S；NRR 110→100 risk                  ║
║  SECTOR  -1.8  Application_SaaS strong bearish; Hyperscalers ║
║                / Semis_AI_Infra moderate bullish (K shape)   ║
║  MACRO   +0.6  Capex rotation neutral-positive (建設/電力/   ║
║                晶片乘數高); 1999-2000 dot-com analogue       ║
╠══════════════════════════════════════════════════════════════╣
║  ARBITER → BEARISH on legacy SaaS (Sector + Bear consensus)  ║
║  受益 ↑  Hyperscalers / Semi_AI_Infra (moderate)             ║
║  受損 ↓  Application_Software strong / IT_Services moderate  ║
║  Tickers  CRM ADBE NOW ORCL WDAY TEAM (avoid)               ║
║          MSFT GOOGL NVDA AVGO MU (long alt)                  ║
║  Cache: sector_intel ✅  phase0 ✅                            ║
╚══════════════════════════════════════════════════════════════╝
```

**Debate Note**: Sector(-1.8) vs Bull(+3.0) 4.8-pt spread；K 型分化—『SaaS 與 AI infra 在 Tech 板塊內部的權衡』。Q1 earnings season ADBE/NOW/CRM 為驗證點。

---

### [BULLISH +1.3] n010 · Buy these memory stocks (HBM/DDR5 mix shift)

```
╔══════════════════════════════════════════════════════════════╗
║  type: sector_news  │  weights: B20 / Br20 / S50 / M10       ║
║  source: Investing.com (MEDIUM, conf cap 0.7)                ║
╠══════════════════════════════════════════════════════════════╣
║  BULL    +4.0  HBM3E/4 sold out; DRAM 三寡頭定價權 2017 以來 ║
║                最強; AI server BOM 10%→40%; MU fwd PE 10x     ║
║  BEAR    -3.0  Sell-side 群體 bullish = cycle top 訊號;      ║
║                2H26-2027 供給 wall; DeepSeek/Huawei 擠壓中國 ║
║  SECTOR  +2.2  Memory strong / AI Accelerators moderate /    ║
║                Semi Equipment + OSAT moderate                ║
║  MACRO   +0.4  AI capex 確認 expansion; rate-insensitive;    ║
║                2017-2018 super-cycle analogue                ║
╠══════════════════════════════════════════════════════════════╣
║  ARBITER → BULLISH on Memory rotation (3 of 4 lanes positive)║
║  受益 ↑  Memory strong / Semi Equipment / OSAT / Accel.      ║
║  受損 ↓  PC_OEM weak (BOM cost up)                           ║
║  Tickers  MU WDC STX AMAT LRCX NVDA AVGO ASML AMKR           ║
║  Cache: sector_intel ✅  phase0 ✅                            ║
╚══════════════════════════════════════════════════════════════╝
```

**Debate Note**: Bull/Bear 7-pt spread 反映『時間框架』分歧；Bull 看 6-12m HBM tightness、Bear 看 2027 供給 wall。Hyperscaler 4/29-30 capex guide 為 trigger。

---

### [BULLISH +1.6] n021 · ChatGPT is so 2025 — AI gold mines = Defense / Healthcare / Agentics

```
╔══════════════════════════════════════════════════════════════╗
║  type: sector_news  │  weights: B20 / Br20 / S50 / M10       ║
║  source: MarketWatch (HIGH)                                  ║
╠══════════════════════════════════════════════════════════════╣
║  BULL    +4.0  Defense AI (PLTR/ANDR/LMT) + Healthcare AI    ║
║                (RXRX/SDGR) + Agentics (NOW/MSFT) 三軸 alpha  ║
║  BEAR    -2.0  媒體式包裝 = sector top 訊號; PLTR PE 200x;   ║
║                AMZN/META/GOOGL 4/29-30 capex 為 trigger      ║
║  SECTOR  +2.3  Defense_Tech strong / Enterprise_Agentics     ║
║                strong / Healthcare_AI moderate / Primes mod. ║
║  MACRO   +0.8  Fiscal-defense GDP 支撐; R-star 上修;         ║
║                1980s Reagan defense + Volcker analogue       ║
╠══════════════════════════════════════════════════════════════╣
║  ARBITER → BULLISH (3 of 4 lanes positive, Sector 主導)      ║
║  受益 ↑  Defense_Tech / Enterprise_Agentics strong           ║
║         Healthcare_AI / Defense_Primes moderate              ║
║  受損 ↓  Consumer_SaaS (與 n034 相互佐證)                    ║
║  Tickers  PLTR LMT RTX NOC GD MSFT NOW NVDA AVGO RXRX SDGR   ║
║  Cache: sector_intel ✅  phase0 ✅                            ║
╚══════════════════════════════════════════════════════════════╝
```

**Debate Note**: Bull(+4) vs Bear(-2) 6-pt spread；Sector + Macro 同向背書 Bull。Industrials 已 Top-1 INFLOW (0.439) 驗證 rotation。

---

## Shallow Digest (Top 20 — MD only, JSON cache 限 top 10)

### [-2.8] n014  Private credit fad peaked — 牙醫接到 cold call 即週期信號
- **Bull**: 私募信貸警報是 contrarian 訊號—主流媒體警示時頂部尚遠
- **Bear**: 私募信貸 $2T 規模 + retail 募資泛濫 = 2008 CDO 級信用事件前兆
- **Sector**: BDC (ARCC, MAIN)、Apollo/KKR/BX/OWL 估值風險上行；中型銀行受惠存款回流
- **Macro**: HY spread 已 accelerating warning + NFCI 收緊；Fed 對 NBFI 監管壓力升溫
- Source: MarketWatch HIGH │ type: sentiment
---

### [-2.5] n002  WHCD 槍擊事件—一名警官中彈、川普安全
- **Bull**: Trump 安全結局 + 安全機制即時反應降低長期政治尾風險
- **Bear**: 週日開盤 risk-off 跳空、VIX 短期 +2-3 點、SPX 期貨 -0.5~1%
- **Sector**: Defense (LMT/RTX) 邊際小幅；保險與安防 (ALLE) 短期關注
- **Macro**: 短期 risk-off bid for Treasury / Gold；DXY safe-haven 微升；事件單日影響
- Source: CNBC Top HIGH │ type: geopolitical
---

### [+2.5] n016  債券基金資金流入創新高—2026 餘下時間 contrarian 看好股優於債
- **Bull**: 極度 bond inflow = 後續 risk-on rotation 驅動股票延長 leg up
- **Bear**: 債券 inflow 反映末期防禦心態，反向訊號可能在 cycle 變盤前失效
- **Sector**: Beneficiaries: Cyclicals (Industrials/Materials)、Small Caps (IWM)；REITs/Utilities 邊際弱化
- **Macro**: 與 FRED Overheating regime 一致—10Y 上行壓力延續，bear steepener 確認
- Source: MarketWatch HIGH │ type: sentiment
---

### [-2.5] n017  Apple Tim Cook 卸任，John Ternus 接班—AI 落差為核心 CEO 任務
- **Bull**: 新 CEO 帶來 product cycle 重啟與 AI 收購整合機會 (PERPLEX, Anthropic 合作?)
- **Bear**: $4T market cap + AI 落後 + 中國需求疲軟 = multiple compression 起點
- **Sector**: Tech-Mega-Cap K 型分化加深；Suppliers (TSM, AVGO) 短期影響有限
- **Macro**: 對 Fed/yield 無直接影響；DXY 中性；對 AAPL ADR 散戶情緒短期負面
- Source: MarketWatch HIGH │ type: corporate
---

### [+2.5] n038  BWET 油輪 ETF YTD +600%—Hormuz 干擾結構性受惠勝過原油本身
- **Bull**: Tankers (FRO/STNG/EURN) ton-mile demand 結構性增長至 2H26 持續
- **Bear**: +600% YTD parabolic move 已 priced in，任何 ceasefire = -30~50% reversal
- **Sector**: Marine Shipping Tankers strong bullish；下游煉廠/航空成本上行
- **Macro**: 確認 Hormuz cost-push 結構性事件；推升全球海運保險 + 通膨持久性
- Source: CNBC Top HIGH │ type: sector_news
---

### [+2.0] n040  美國政府持有 Intel 股權未實現獲利 $26B—foundry 復興確認
- **Bull**: Government backing + INTC +24% 1987 以來最佳單日 = sentiment 與 multiple 雙修復
- **Bear**: 政府獲利兌現壓力 + foundry 競爭力仍未證實 = pump-and-dump 結構
- **Sector**: Semi 內部 K 型再平衡—lagger catch-up 確認 (INTC/MU/AMAT)
- **Macro**: 工業政策成功例證—延續 reshoring 主題對 GDP/就業正面
- Source: Investing.com MEDIUM │ type: corporate
---

### [+2.0] n032  Goldman 預估 2026 全年 100 件 IPO 共 $160B—資本市場活躍度高峰
- **Bull**: IPO pipeline 顯示風險偏好強、私募 backlog 釋放、Investment Banks (GS/MS/JPM) FY26 EPS 上修
- **Bear**: IPO 高峰歷史上接近市場頂部 (1999, 2021)；供給壓力對既有 mega-cap 構成輪動分流
- **Sector**: Investment Banks (GS, MS, JPM) 受惠；alt assets (KKR, BX) 受惠 exit pipeline
- **Macro**: 與 FRED Overheating + risk-on regime 一致；fiscal/financial conditions 寬鬆持續
- Source: Investing.com MEDIUM │ type: sector_news
---

### [+2.0] n020  Lockheed Martin CEO 對中東兩字訊息—訂單能見度延長
- **Bull**: Defense backlog 拉長 + Iran war 訂單 visibility 至 2027；LMT 估值 reset 起點
- **Bear**: 敘事 priced in；單一 CEO 喊話不改 single-digit revenue grower 本質
- **Sector**: Defense Primes (LMT, RTX, NOC, GD) bullish moderate；ETF: ITA
- **Macro**: 確認 fiscal defense buildup；對 yield/USD 邊際支撐
- Source: Yahoo Finance HIGH │ type: sector_news
---

### [+1.5] n012  本週關鍵 M&A: Helix Energy / Tesla / QXO / USA Rare Earth
- **Bull**: M&A activity broad-based 驗證 risk-on；Rare Earth 稀土題材延續
- **Bear**: M&A spike 接近 cycle 頂；多筆案件分散小型，broad market alpha 有限
- **Sector**: Energy_Services (HLX)、EV/Auto (TSLA)、Rare Earth (USAR, MP) 個股驅動
- **Macro**: 對 macro 中性—M&A 活躍是 risk-on regime 的副產品
- Source: Seeking Alpha MEDIUM │ type: corporate
---

### [+1.5] n022  Barron's: BRK 落後 SPX 後為良好進場點
- **Bull**: BRK $345B 現金 buffer + Buffett succession overhang 已部分消化；defensive value rotation 候選
- **Bear**: BRK underperformance 反映 mega-cap 集中度問題未解；轉折需 catalyst
- **Sector**: Insurance (BRK, TRV, CB)、Diversified Holdings 邊際支持
- **Macro**: 對 macro 無直接影響；體現 active manager 在 mag-7 集中市場尋找 alpha
- Source: Seeking Alpha MEDIUM │ type: corporate
---

### [+1.5] n035  Berkshire 吸引投資人關注（CNBC 補充報導）
- **Bull**: BRK 折扣 + 巨額現金 = 防禦 + 機會主義雙重 setup
- **Bear**: 落後 SPX 反映 portfolio 過度防禦；Mag-7 強勢延續會持續壓 BRK
- **Sector**: Insurance/Diversified；BRK.B 為核心
- **Macro**: 與 risk-on regime 不衝突，但反映散戶 rotation 思考
- Source: CNBC Top HIGH │ type: corporate
---

### [+1.5] n028  Goldman: 此股市可能優於美股指數 (Japan/Europe?)
- **Bull**: 海外股市 catch-up trade — JPX/STOXX 估值折扣 + JPY/EUR 弱勢支撐
- **Bear**: 美股 leadership 未變，海外輪動歷史上短期 alpha 但結構性缺乏
- **Sector**: International ETFs (EWJ, VGK)、跨國 cyclical (CAT, DE) 邊際支持
- **Macro**: USD 結構性偏強壓制海外 returns；分散持有可降組合 beta
- Source: Investing.com MEDIUM │ type: sector_news
---

### [+1.0] n025  Market chaos 給 active manager 擊敗 index fund 機會
- **Bull**: Volatility regime = stock-pickers 重生；Index fund FOMO 結束
- **Bear**: 90% active manager 仍跑輸—『chaos = alpha』敘事不可靠
- **Sector**: Asset managers 邊際；ARK 系列、boutique funds 流入
- **Macro**: 反映 dispersion 上升、波動率重啟，與 NFCI 收緊一致
- Source: MarketWatch HIGH │ type: sentiment
---

### [+1.0] n006  3 forces drove historic week for S&P 500
- **Bull**: Iran war + earnings + hardware/software 分裂—市場仍向上消化壓力
- **Bear**: 'Historic but volatile' = 動能脆弱；任何 shock 即觸發 unwind
- **Sector**: Hardware (Semis) > Software (legacy SaaS) 確認 K 型
- **Macro**: 與 FTD CONFIRMED + Market Top Early Warning 並存矛盾
- Source: CNBC Top HIGH │ type: sentiment
---

### [-1.0] n039  Supreme Court deportation case—Trump 主張司法無權干預
- **Bull**: 政治制度仍允許司法獨立爭議—制度韌性顯現
- **Bear**: 行政/司法權力衝突升溫，制度不確定性對長期 USD 與股市風險溢價推升
- **Sector**: 對個股影響有限；Defense / Border Security 邊際
- **Macro**: 制度風險長期累積，當前不影響 fed path
- Source: Investing.com MEDIUM │ type: geopolitical
---

### [+0.5] n037  CNBC: Tesla + xAI Grok 在車內整合測試
- **Bull**: TSLA + xAI synergy 驗證 Musk 生態系延伸；FSD adoption 加速
- **Bear**: AI chatbot 在駕駛環境的安全性風險未驗證；regulatory headline 風險
- **Sector**: TSLA / xAI / NVIDIA (compute) 邊際；Auto OEM 競爭壓力
- **Macro**: 對 macro 無直接影響
- Source: CNBC Top HIGH │ type: corporate
---

### [+0.5] n036  Generation X 驅動美容銷售
- **Bull**: ELF, ULTA, EL 受惠 Gen X 高 disposable income; 防禦性消費
- **Bear**: 美容業 saturation; PMI 數據如轉弱即首當其衝
- **Sector**: Beauty/Personal Care (ELF, ULTA, EL, COTY)
- **Macro**: 確認 K 型消費—年長/高所得仍消費，年輕/低所得收斂
- Source: CNBC Top HIGH │ type: sector_news
---

### [+0.5] n031  $300 bags / $150 earrings 中價位成 Gen Z 地位象徵
- **Bull**: Mid-tier brands (COACH/TPR, Levi's, Lululemon) 受惠 trade-up
- **Bear**: Trade-down from luxury 對 LVMH/PPRUY/RL 為長期負面
- **Sector**: Discretionary mid-tier (TPR, RL, LULU); Luxury (LVMUY) 邊際弱
- **Macro**: 確認 consumer K 分化但整體消費仍 resilient
- Source: CNBC Top HIGH │ type: sector_news
---

### [+0.3] n005  品牌與零售商：行銷景觀現況
- **Bull**: 廣告支出回升，META/GOOGL/AMZN ad rev 邊際支持
- **Bear**: 廣告預算對 macro 高度敏感，ISM 走弱即首當其衝
- **Sector**: Digital ads (META, GOOGL); Retail (AMZN, WMT)
- **Macro**: 中性，與 META/GOOGL 4/29 earnings 為驗證點
- Source: Investing.com MEDIUM │ type: sector_news
---

### [-0.5] n029  Right to repair populist wave 對 OEM 不利
- **Bull**: Right-to-repair 法案推動回收/維修產業 (IFIX, RPR)
- **Bear**: AAPL, DE, TSLA 等 OEM aftermarket revenue 受擠壓
- **Sector**: Auto OEM、農機 (DE)、Tech hardware (AAPL) 受影響
- **Macro**: 反映 affordability 政治壓力，與 election cycle 同步
- Source: CNBC Top HIGH │ type: sector_news
---

## 委員會結論 (Arbiter Synthesis)

**Net session bias**: 略偏 risk-off (-0.3)，主因 n011 BINARY geopolitical 與 n034 BEARISH SaaS。

**Sector rotation 強化方向**:
- ↑↑↑ **Energy / Energy_E&P / Midstream / Tankers** — n004 + n011 + n038 三重共振
- ↑↑ **Defense_Primes / Defense_Tech** — n011 + n020 + n021 三重共振
- ↑↑ **Semi_Memory / Semi_Equipment / AI Accelerators** — n010 + n040 雙確認
- ↑ **Investment_Banks / Insurance** — n032 + n022 + n016 (cyclical rotation)
- ↓↓ **Application_Software (CRM/ADBE/NOW/ORCL/WDAY)** — n034 結構性 bearish
- ↓ **Airlines / Discretionary / Materials_Chems** — n004 + n011 cost-push 受害
- ↓ **Asset_Managers / BDCs** — n014 私募信貸頂部訊號
- ↓ **AAPL** — n017 CEO transition + AI gap

**本週 binary watch (within 48h)**:
1. **FOMC 4/28-4/29** 利率決議 (從 sector_intel cache 延續)
2. **Warsh Senate 投票 4/29** (Kalshi 86% 確認機率)
3. **AMZN earnings 4/30**, **META/GOOGL earnings 4/29** — 將決定 n010/n021/n034 K 型分化的真實深度
4. **Iran/Hormuz 升級風險** (n011) — 與 FOMC 同週疊加為 macro tail

**Cache update**: `sector_intel.json` top_catalysts prepend 5 則; `phase0` macro_backdrop_score -0.3 → -0.6; binary_risks +1。

---

> Generated: 2026-04-26 12:30 · Validator: ✅ V2.1 schema compliant (10 shallow + 5 deep) · Subagent isolation: PER_AGENT_BATCH (4/4 isolated)

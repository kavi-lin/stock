# News Digest — 2026-05-27

**Mode**: DIGEST | **Generated**: 2026-05-27 20:55 | **fanout_mode**: PER_AGENT_BATCH
**Raw**: 358 items (4 sources: RSS + Finnhub + FMP + EDGAR) | **Stage 1**: 25 triaged | **Stage 2**: 5 deep | **session_macro_delta**: −0.22

---

## 1. Triage Summary

```
╔══════════════════════════════════════════════════════════════════════════╗
║  NEWS TRIAGE  │  2026-05-27 20:55  │  358 raw → 25 shallow → 5 deep       ║
╠══════════════════════════════════════════════════════════════════════════╣
║  ✅ DEEP   n0316  [-3.8 BINARY]  策略師警告：能源風險定價過低，迫近通膨衝擊  ║
║  ✅ DEEP   n0105  [-3.2]         Dimon 警告市場「過度狂熱」，加入 Burry      ║
║  ✅ DEEP   n0257  [+3.5]         S&P/Nasdaq 創高，Micron 入 $1T 俱樂部      ║
║  ✅ DEEP   n0007  [+2.8 BINARY]  US 油跌破 $89，Hormuz 1mo 重啟報告         ║
║  ✅ DEEP   n0091  [-3.0]         房貸再融資需求 -18%，利率觸 8 月新高       ║
║  ──────────────────────────────────────────────────────────────────────  ║
║  ❌ SKIP   n0315  [-3.5 BINARY]  Piper：Hormuz 封閉數月，油價創新高 (n0007) ║
║  ❌ SKIP   n0242  [-3.0]         大盤警訊：IPO、margin debt、yield (n0105)  ║
║  ❌ SKIP   n0122  [+3.0]         Nvidia $150B、台廠晶片股飆漲 (n0257)        ║
║  ❌ SKIP   n0073  [-2.8]         Zscaler 盤前 -24%，指引保守                 ║
║  ❌ SKIP   n0078  [-2.5 BINARY]  南韓：伊朗飛彈攻擊 Hormuz 船隻 (n0007)     ║
║  ❌ SKIP   n0220  [-2.5]         ECB VP 警告修正風險升高 (n0105)            ║
║  ❌ SKIP   n0121  [+2.5]         SK Hynix 入 $1T，AI underhyped (n0257)     ║
║  ❌ SKIP   n0085  [+2.5]         Dycom 業績飆，data center 併購驅動         ║
║  ❌ SKIP   n0228  [-2.0]         WSJ：高殖利率可對沖 AI 泡沫                 ║
║  ❌ SKIP   n0343  [-2.0]         金價下跌：戰爭通膨推升升息押注             ║
║  ❌ SKIP   n0123  [+2.0]         殖利率下行：伊朗和平樂觀                   ║
║  ❌ SKIP   n0103  [-2.0]         99% CEO 計劃 AI 裁員                       ║
║  ❌ SKIP   n0204  [+2.0 BINARY]  脆弱停火，股漲油落 (n0007)                 ║
║  ❌ SKIP   n0094  [+1.5]         SpaceX-Tesla 合併傳聞 + IPO                ║
║  ❌ SKIP   n0252  [+1.0]         Trump 任命 Bondi 入白宮 AI 委員會           ║
║  ❌ SKIP   n0310  [+1.5]         Apple 創高，下月 WWDC 大考                  ║
║  ❌ SKIP   n0064  [+1.5]         Goldman 脫離 Apple Card 進買進區            ║
║  ❌ SKIP   n0323  [-1.5]         油價對 DuPont 影響重大，財報關注           ║
║  ❌ SKIP   n0115  [-1.5]         英國能源帳單 +13% on 伊朗戰爭              ║
║  ❌ SKIP   n0126  [-1.5]         伊朗戰爭分化全球市場贏家輸家               ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 2. Deep Analysis

### Impact Card — n0316 [BEARISH −1.1] BINARY tail
```
╔══════════════════════════════════════════════════════════╗
║  DEEP  │  2026-05-27 20:55  │  type=macro_data           ║
╠══════════════════════════════════════════════════════════╣
║  Markets are mispricing energy risk, strategist warns    ║
║  of looming inflation shock                              ║
║  weights: Bull 15 / Bear 15 / Sector 20 / Macro 50      ║
║  scores : Bull +3 / Bear -4 / Sector +1.5 / Macro -2.5  ║
║  source : CNBC International (HIGH)                      ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ⚠ Warning = contrarian indicator；XLE/XOP 兩面贏 ║
║  BEAR    ❌ $20-30/bbl 直灌 CPI，逼 Fed hold/hike (Yardeni)║
║  SECTOR  ⚖ Energy +strong vs Disc/Tech/Trans -moderate   ║
║  MACRO   ❌ 1973-74 Yom Kippur cost-push 類比，2s10s steep ║
║  ARBITER → BEARISH −1.1，採 Macro 主論點                  ║
╠══════════════════════════════════════════════════════════╣
║  受益 ↑  Energy strong  │  Cons Staples weak             ║
║  受害 ↓  Cons Disc / Tech / Industrials moderate         ║
║  Binary Risk  ✅ within 48h (Hormuz expires 2026-07-04)  ║
╠══════════════════════════════════════════════════════════╣
║  tickers : XLE XOM CVX COP XOP OXY SLB XLY XLK XLP DAL  ║
║            UAL DD DOW                                     ║
║  Cache Updated: phase0.json ✅                            ║
╚══════════════════════════════════════════════════════════╝
```
**Arbiter reasoning**: news_type=macro_data 權重 Macro 50% 主導；Hormuz 尾部 + Yardeni 7 月升息 + CPI 3.8% 確認三軸交叉。Sector 採部分（Energy 強多 vs 多數類股弱空淨值小），Bull contrarian 視為再評條件而非否定。
**Debate note**: Bull +3 vs Bear −4 spread=7。關鍵分歧：4-6 週通膨衝擊是否實現決定路徑。

---

### Impact Card — n0105 [NEUTRAL −0.9]
```
╔══════════════════════════════════════════════════════════╗
║  DEEP  │  2026-05-27 20:55  │  type=sentiment            ║
╠══════════════════════════════════════════════════════════╣
║  Jamie Dimon warns markets have 'too much exuberance,'   ║
║  joining forecasters like Michael Burry                  ║
║  weights: Bull 30 / Bear 30 / Sector 15 / Macro 25      ║
║  scores : Bull +2 / Bear -3 / Sector -1.0 / Macro -1.8  ║
║  source : Yahoo Finance (HIGH)                           ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ 2021 Dimon「颶風」後 S&P +6mo；wall of worry  ║
║  BEAR    ❌ Dimon+Burry 收斂 + record margin debt 反身性  ║
║  SECTOR  ⚖ Defensives 弱+ vs Growth 弱-                  ║
║  MACRO   ⚠ 1999-2000 / 2007 頂部結構 6-9mo 領先窗口      ║
║  ARBITER → NEUTRAL −0.9，等待 fund-flow 證實             ║
╠══════════════════════════════════════════════════════════╣
║  受益 ↑  Cons Staples / Utilities / Healthcare weak     ║
║  受害 ↓  Financials / Tech / Cons Disc weak              ║
║  Binary Risk  ❌                                          ║
╠══════════════════════════════════════════════════════════╣
║  tickers : JPM XLF XLK XLY XLP XLU XLV SPY QQQ VIX      ║
║  Cache Updated: phase0.json ✅                            ║
╚══════════════════════════════════════════════════════════╝
```
**Arbiter reasoning**: Bull contrarian 案在 sentiment 類別有 0.30 權重，1990s Dimon 先例存在；Bear 案需 fund-flow 證實才升級為 signal。判 NEUTRAL 因：(1) 無新增 binary 事件 (2) sentiment 警告領先指標通常 6-9 月，timing 模糊 (3) 配合 n0257 BULLISH 同週反向證據。
**Debate note**: Bull +2 vs Bear −3 spread=5。決定取決於 fund-flow 是否在 30 天內反轉。

---

### Impact Card — n0257 [BULLISH +2.35]
```
╔══════════════════════════════════════════════════════════╗
║  DEEP  │  2026-05-27 20:55  │  type=sector_news          ║
╠══════════════════════════════════════════════════════════╣
║  S&P 500, Nasdaq hit record closing highs on AI          ║
║  optimism, Micron joins $1 trillion club                 ║
║  weights: Bull 20 / Bear 20 / Sector 50 / Macro 10      ║
║  scores : Bull +5 / Bear -4 / Sector +4.0 / Macro +1.5  ║
║  source : Reuters (HIGH)                                 ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ HBM3e 結構需求驗證 + NVDA $150B capex 執行   ║
║  BEAR    ❌ Late-cycle 頂部 + 集中度極端 + 估值無緩衝    ║
║  SECTOR  ✅ Semi memory + foundry + equipment strong+    ║
║  MACRO   ⚖ Wealth effect 短期，AI capex 黏服務 PCE       ║
║  ARBITER → BULLISH +2.35，採 Sector 50% 壓倒性           ║
╠══════════════════════════════════════════════════════════╣
║  受益 ↑  Semi strong / Semi Equipment strong / Comm svc weak  ║
║  受害 ↓  None (Bear 警告作 mean-reversion 觸發)           ║
║  Binary Risk  ❌                                          ║
╠══════════════════════════════════════════════════════════╣
║  tickers : NVDA MU AVGO TSM ASML ARM SMH SOXX AMAT LRCX KLAC ║
║  Cache Updated: phase0.json ✅                            ║
╚══════════════════════════════════════════════════════════╝
```
**Arbiter reasoning**: news_type=sector_news Sector 權重 50% 壓倒性；HBM3e 緊俏 → CoWoS → TSM/ASML supply chain 廣化驗證。Bull 完全接受結構性需求論述；Macro wealth effect 真實但短期；Bear 警告作 4-8 週 mean-reversion 再評觸發（CPI / 指引 / 地緣）。
**Debate note**: Bull +5 vs Bear −4 spread=9。Sector 50% 權重碾壓 spread divergence。

---

### Impact Card — n0007 [BINARY −1.2]
```
╔══════════════════════════════════════════════════════════╗
║  DEEP  │  2026-05-27 20:55  │  type=geopolitical         ║
╠══════════════════════════════════════════════════════════╣
║  U.S. oil falls below $89 on report Iran agreement       ║
║  would restore Hormuz traffic in one month               ║
║  weights: Bull 15 / Bear 30 / Sector 15 / Macro 40      ║
║  scores : Bull +4 / Bear -4 / Sector -1.5 / Macro -1.0  ║
║  source : CNBC (HIGH)                                    ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ 1mo 重啟移除最大 binary 尾部 → risk-on 廣化  ║
║  BEAR    ❌ Korea 飛彈攻擊 + Piper 封閉數月 + Reuters「shaky」║
║  SECTOR  ⚖ Energy strong- vs Airlines/Chem moderate+    ║
║  MACRO   ⚠ 雙向尾部：重啟 → 10y -15bp / 確認封閉 → +25bp ║
║  ARBITER → BINARY −1.2，spread=8 + 真實 binary 事件      ║
╠══════════════════════════════════════════════════════════╣
║  受益/受害 ↕  Energy binary | Airlines/Disc/Chem binary  ║
║                Defense binary                             ║
║  Binary Risk  ✅ within 48h (Hormuz expires 2026-07-04)  ║
╠══════════════════════════════════════════════════════════╣
║  tickers : XLE XOM CVX COP XOP OXY DAL UAL AAL LUV DD   ║
║            DOW LYB LMT RTX NOC                            ║
║  Cache Updated: phase0.json ✅                            ║
╚══════════════════════════════════════════════════════════╝
```
**Arbiter reasoning**: news_type=geopolitical Bear 30% + Macro 40% = 70% 權重；Korea 飛彈攻擊新證據強烈反證 1mo 重啟敘事，spread=8 + 真實 binary 事件強制 verdict=BINARY。降一等級（Bull-leaning → BINARY）。歷史類比：1990 Iraq-Kuwait V-recovery、1973 Yom Kippur cost-push 多年。
**Debate note**: Bull +4 vs Bear −4 spread=8。30 日內驗證視窗。

---

### Impact Card — n0091 [BEARISH −1.3]
```
╔══════════════════════════════════════════════════════════╗
║  DEEP  │  2026-05-27 20:55  │  type=macro_data           ║
╠══════════════════════════════════════════════════════════╣
║  Mortgage refinance demand drops 18% as rates hit        ║
║  highest level since August                              ║
║  weights: Bull 15 / Bear 15 / Sector 20 / Macro 50      ║
║  scores : Bull +2 / Bear -3 / Sector -2.0 / Macro -1.5  ║
║  source : CNBC Top (HIGH)                                ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ⚠ Fed pivot trigger 線索；Long-duration tech 受惠 ║
║  BEAR    ❌ Wealth-effect 拖累 + 房屋週轉凍結 + 慢燃 demand  ║
║  SECTOR  ❌ Homebuilders/REIT/Mortgage Origin 中空        ║
║  MACRO   ❌ 停滯通膨 tell：rate-sensitive 先斷裂於 svc CPI║
║  ARBITER → BEARISH −1.3，採 Macro 50% 主論點             ║
╠══════════════════════════════════════════════════════════╣
║  受害 ↓  Cons Disc (homebuilders) / Real Estate /        ║
║          Financials (originators) / Materials moderate   ║
║  Binary Risk  ❌                                          ║
╠══════════════════════════════════════════════════════════╣
║  tickers : KBH LEN DHI NVR PHM ITB XHB NLY AGNC RKT     ║
║            UWMC HD LOW SHW MAS                            ║
║  Cache Updated: phase0.json ✅                            ║
╚══════════════════════════════════════════════════════════╝
```
**Arbiter reasoning**: Macro 50% 主導 — 確認停滯通膨 tell；2022 H2 / 2006-07 類比警示傳導 12-18mo 入廣信用。Bull pivot 案需 PCE / 失業 cluster 才生效；當前單一訊號不足。Sector 接受全面（房屋鏈廣泛受害）。
**Debate note**: Bull +2 vs Bear −3 spread=5。決定取決於 Q3 失業 / PCE cluster。

---

## 3. Shallow Digest (top 20)

### [-3.5] n0315 — Piper Sandler says Strait of Hormuz to remain closed for months and oil to hit new highs
- **Bull**: Energy strong+；defense bid 持續
- **Bear**: 油 $115+ 灌 CPI，consumer 重壓
- **Sector**: Energy strong+，Airlines/Disc strong-
- **Macro**: 停滯通膨鎖定，升息尾部 40%+
- Source: CNBC Top HIGH │ type: geopolitical │ binary

---

### [-3.0] n0242 — Big Stock Market Warning Signs: Red Hot IPOs, Record Margin Debt, Lowest Ever S&P 500 Yield, Meme ETFs
- **Bull**: late-cycle 警訊但仍有 6-9 月窗口
- **Bear**: 1999/2007 頂部結構鏡像
- **Sector**: Semis / Mega-cap Growth 最脆弱
- **Macro**: Margin debt 系統性風險、VIX 上行
- Source: Seeking Alpha HIGH │ type: sentiment

---

### [+3.0] n0122 — Taiwan chip stocks climb after Nvidia announces $150 billion spending plans
- **Bull**: TSM / ASE / 後段封裝 multi-year 訂單能見度
- **Bear**: 估值已 priced in，Trump-Xi 尾部
- **Sector**: Semi Foundry + Equipment strong+
- **Macro**: AI capex 支撐 risk-on
- Source: CNBC HIGH │ type: sector_news

---

### [-2.8] n0073 — Zscaler stock plunges 24% premarket on cautious guidance
- **Bull**: 個股事件，零售逢低承接
- **Bear**: Cybersecurity SaaS 需求疑慮蔓延 CRWD / PANW
- **Sector**: Cybersecurity SaaS 廣泛弱-
- **Macro**: 企業 IT 支出降溫早期訊號
- Source: Yahoo Finance HIGH │ type: earnings

---

### [-2.5] n0078 — Iranian missile likely involved in attack on ship in Strait of Hormuz, South Korea says
- **Bull**: 孤立事件，停火框架可維持
- **Bear**: 停火違反信號，Hormuz 重啟敘事破裂
- **Sector**: Energy strong+，Airlines 弱-
- **Macro**: Iran tail 重啟，油 $20+ spike 可能
- Source: Reuters HIGH │ type: geopolitical │ binary

---

### [-2.5] n0220 — Market correction risk looks elevated as stocks hit record highs, top Europe central banker warns
- **Bull**: 央行口頭警告通常無效
- **Bear**: ECB + Dimon + Burry 三方收斂
- **Sector**: Defensives 弱+，Growth 弱-
- **Macro**: 金融穩定關注 ≠ Fed path delta
- Source: CNBC HIGH │ type: sentiment

---

### [+2.5] n0121 — A rival joins Micron in the $1 trillion club as one bank argues AI is actually underhyped
- **Bull**: HBM 雙寡頭 memory upcycle 結構性
- **Bear**: $1T 集中度升高，回調幅度放大
- **Sector**: Memory + HBM strong+
- **Macro**: AI capex 支撐 risk-on
- Source: MarketWatch HIGH │ type: sector_news

---

### [+2.5] n0085 — Dycom Soars As Earnings, Revenue Growth Accelerate Amid Data Center Acquisitions
- **Bull**: Data center 鏟子股驗證
- **Bear**: 個股事件，估值偏高
- **Sector**: Comms Infrastructure 強+
- **Macro**: AI capex 第二導數確認
- Source: Yahoo Finance HIGH │ type: earnings

---

### [-2.0] n0228 — Afraid of an AI Bubble? Soaring Bond Yields Can Protect You
- **Bull**: AI 泡沫敘事 + 對沖工具
- **Bear**: mainstream 也在準備風險
- **Sector**: Bond proxies (Utilities / REITs) 受益
- **Macro**: 10y 5%+ 結構性平衡點
- Source: WSJ HIGH │ type: sentiment

---

### [-2.0] n0343 — Gold falls as war-driven inflation fears fuel rate-hike bets
- **Bull**: 短期回檔但中期戰爭尾部仍支撐
- **Bear**: 升息押注升溫，real yield 重壓 gold
- **Sector**: Gold miners 弱-
- **Macro**: DXY + real yield 升、Fed 鷹派定價
- Source: Reuters HIGH │ type: macro_data

---

### [+2.0] n0123 — Treasury yields fall as investors remain optimistic on Iran peace deal prospects despite U.S. strike
- **Bull**: 重啟敘事支撐 risk-on，duration rally
- **Bear**: 南韓飛彈報告反證未消化
- **Sector**: Tech / Long-duration 受益
- **Macro**: 10y 從 5% 退潮，Fed 鴿派回桌
- Source: CNBC HIGH │ type: macro_data

---

### [-2.0] n0103 — 99% of CEOs are planning AI layoffs in the next 2 years
- **Bull**: 成本下降利好企業利潤率
- **Bear**: 結構性失業 + 消費萎縮中長期風險
- **Sector**: Enterprise Software / AI infra +
- **Macro**: 勞動市場拐點訊號
- Source: Yahoo Finance HIGH │ type: sentiment

---

### [+2.0] n0204 — Shares advance, oil prices ease as investors weigh shaky US-Iran truce
- **Bull**: 重啟敘事支撐風險偏好
- **Bear**: 「shaky」框架 = 反轉風險高
- **Sector**: Risk-on 廣化
- **Macro**: 雙向波動，10y 雙向尾部
- Source: Reuters HIGH │ type: geopolitical │ binary

---

### [+1.5] n0094 — SpaceX-Tesla merger chatter reignites as Musk pushes rocket company toward Nasdaq
- **Bull**: Tesla 多元化敘事注入
- **Bear**: stretched 估值 + 控股結構問題
- **Sector**: EV / Aerospace 弱+
- **Macro**: 風險偏好升溫但個股事件
- Source: CNBC Top HIGH │ type: corporate

---

### [+1.5] n0310 — Apple's surge to record highs faces a major test next month
- **Bull**: WWDC AI 敘事可延長 melt-up
- **Bear**: 預期高，miss 風險顯著
- **Sector**: Mega-cap Tech 弱+
- **Macro**: 個股事件，無 Fed delta
- Source: CNBC Top HIGH │ type: corporate

---

### [+1.5] n0064 — Goldman Sachs Moves Away From Apple Card And Into Buy Range
- **Bull**: GS 戰略聚焦，估值修復
- **Bear**: Apple Card 業務剝離損失
- **Sector**: Financials 弱+
- **Macro**: 個股事件
- Source: Yahoo Finance HIGH │ type: corporate

---

### [-1.5] n0323 — Why oil prices matter so much to DuPont, and the big earnings report to watch tonight
- **Bull**: DD feedstock 紓解可期
- **Bear**: 原料成本壓力持續
- **Sector**: Chemicals 弱-
- **Macro**: 個股財報事件
- Source: CNBC HIGH │ type: earnings

---

### [-1.5] n0115 — Energy bills in Britain to jump 13% on impact of Iran war
- **Bull**: UK utilities pricing power
- **Bear**: 歐洲消費萎縮，全球需求第二階
- **Sector**: Utilities (UK) +，Disc -
- **Macro**: 歐洲通膨黏性升高
- Source: Reuters HIGH │ type: macro_data

---

### [-1.5] n0126 — Iran war splits global markets into clear winners and losers
- **Bull**: Energy / Defense / Cyber 結構受益
- **Bear**: Disc / Transport / EM 結構受害
- **Sector**: 分化清晰
- **Macro**: 停滯通膨 regime 跡證
- Source: Reuters HIGH │ type: geopolitical

---

### [+1.0] n0252 — Trump appoints former Attorney General Bondi to White House AI panel
- **Bull**: AI 政策定型，輕度 BAT supportive
- **Bear**: 監管色彩可能升溫
- **Sector**: Big Tech AI 中性
- **Macro**: 政策訊號弱
- Source: Reuters HIGH │ type: corporate

---

## 4. Session Outcome

| 項目 | 值 |
|---|---|
| session_macro_delta | **−0.22** |
| phase0 macro_backdrop_score | −4.31 → **−4.53** |
| binary_risks 新增 | 2 筆 (n0316 energy shock + n0007 Hormuz binary) |
| Active binary expires | 2026-07-04 (Iran/Hormuz window) |
| news_patch_count | 85 → **90** |

**Top thread**: Hormuz binary 雙向尾部佔據 stage 1 + 2 半壁江山（n0007 / n0315 / n0078 / n0316 / n0204 / n0115 / n0126），Korea 飛彈打擊報告 (n0078) 使尾部偏向「封閉」。
**反向 thread**: AI bull (n0257 / n0122 / n0121 / n0085) 廣化驗證 — Micron / Hynix 同週入 $1T 俱樂部 + NVDA $150B Taiwan capex + Dycom data-center 第二導數。
**頂部訊號收斂**: Dimon + Burry (n0105) + ECB VP (n0220) + Seeking Alpha 警訊 (n0242)，但 fund-flow 尚未確認；NEUTRAL 等待 30 日驗證。
**停滯通膨 tell**: 房貸 -18% (n0091) + 黃金升息押注 (n0343) + 10y 測 5.0% 痛閾值 — rate-sensitive 部門先斷裂於服務 CPI 降溫。

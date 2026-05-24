# NEWS DIGEST — 2026-05-23

> **Mode**: DIGEST | **Generated**: 2026-05-23 09:30 | **Schema**: V2.1
> **Stage 1**: 336 raw (RSS + Finnhub + FMP + EDGAR) → 52 shallow verdicts → **5 deep**
> **Fanout**: PER_AGENT_BATCH (4 subagent isolated) | **Session macro delta**: -0.55

---

## ⚠️ TODAY'S DOMINANT NARRATIVE

**Fed regime change + stagflation rails**: Warsh sworn in as Fed Chair (5/22, succeeding Powell). Same day, Waller (formerly dovish) publicly drops cut signal + opens hike door. Markets pricing >50% Dec hike. Consumer sentiment hits **fresh record low** as Iran war drives gasoline to 4-yr high, Memorial Day inventory drawdown setting up 4-6 week fuel-price spike. **Macro_backdrop_score: -3.96 → -4.51 (Phase 0 patched)**.

**Net session delta**: -0.55 (clear hawkish/risk-off tilt)
**Deep verdicts**: 3 BEARISH, 1 BINARY, 1 BULLISH

---

## 1. TRIAGE SUMMARY

```
╔════════════════════════════════════════════════════════════════════════════╗
║  NEWS TRIAGE  │  2026-05-23 09:30  │  52 scored → 5 advanced               ║
╠════════════════════════════════════════════════════════════════════════════╣
║  ✅ DEEP   n0258  [+2.0]  Warsh chairman of Fed         monetary_policy    ║
║  ✅ DEEP   n0326  [-4.0]  Waller no longer signal cuts  monetary_policy    ║
║  ✅ DEEP   n0331  [+4.0]  Consumer sentiment record low macro_data         ║
║  ✅ DEEP   n0272  [+4.0/BINARY] Iran war + gas 4-yr high geopolitical      ║
║  ✅ DEEP   n0092  [+1.5]  Micron US memory chip AI surge corporate         ║
║  ──────────────────────────────────────────────────────────────────────  ║
║  ❌ SKIP   n0043  [-4.5]  BrasilAgro crop risk          earnings           ║
║  ❌ SKIP   n0064  [+4.0]  Weekly Wrap NVDA/War/FOMC     sector_news        ║
║  ❌ SKIP   n0316  [+4.0]  Tech Parabolic Rally Test SPX macro_data         ║
║  ❌ SKIP   n0015  [+3.0]  BOE 8% Yield + AI Growth      earnings           ║
║  ❌ SKIP   n0118  [+2.0]  Esther George hike possibility monetary_policy   ║
║  ... (42 more skipped)                                                     ║
╚════════════════════════════════════════════════════════════════════════════╝
```

**Manual override note**: Auto-triage top 5 were single-name earnings (n0043 BrasilAgro / n0015 BOE / etc) which lack market-wide impact. PM manually elevated **Warsh sworn-in (n0258)** + **Consumer sentiment (n0331)** + **Iran war/gas (n0272)** + **Micron AI expansion (n0092)** as the actual macro/sector-moving stories of the day. Auto's #4 (Waller n0326) retained.

---

## 2. DEEP ANALYSIS (5 verdicts × 4-view debate)

### Verdict #1 — n0258 Warsh sworn in as Fed Chair

```
╔══════════════════════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-05-22 17:00 UTC  │  MODE: DIGEST                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║  [BEARISH -2.3]  Kevin Warsh is officially the chairman of the Fed       ║
║  type: monetary_policy  │  weights: Macro 50% / Sector 20% / B+Br 30%    ║
╠══════════════════════════════════════════════════════════════════════════╣
║  BULL    ➕ leadership uncertainty 收斂 + 鷹派 credibility 壓低 term premium ║
║  BEAR    ❌ 鷹派立威風險 → multiple compression + AI 集中度脆弱           ║
║  SECTOR  ❌ Real Estate/Utilities 重估;Financials/Energy 受惠           ║
║          tickers: XLF, XLRE, XLU, XLE, KRE, O, VICI, HD, NVDA, MSFT      ║
║  MACRO   ❌ terminal rate +25-50bp repricing,bear flattening → steepening ║
║  ARBITER → BEARISH, 採 Macro 主論點 (Macro 50% 主權重)                    ║
╠══════════════════════════════════════════════════════════════════════════╣
║  受惠 ↑  Financials, Energy                                              ║
║  受損 ↓  Real Estate, Utilities, Technology                              ║
║  Binary Risk  No                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Cache:  sector_intel pending  │  phase0 ✅ macro -3.96→-4.51            ║
╚══════════════════════════════════════════════════════════════════════════╝
```

- **Source**: [Yahoo Finance — Kevin Warsh is officially the chairman of the Federal Reserve](https://www.youtube.com/watch?v=75E2D4-Tkck) | HIGH | 2026-05-22T17:00 UTC
- **Debate note**: Bull(leadership uncertainty 收斂 + credibility 壓低 term premium) vs Bear/Macro(鷹派立威 + 估值多壓縮);Warsh 首次 FOMC 或國會證詞是否會比 Powell 更鷹

---

### Verdict #2 — n0326 Waller: Fed Should No Longer Signal Cuts

```
╔══════════════════════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-05-22 10:39 UTC  │  MODE: DIGEST                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║  [BEARISH -3.0]  Fed's Waller: Inflation Risks Mean Fed Should No Longer ║
║  type: monetary_policy  │  weights: Macro 50%                            ║
╠══════════════════════════════════════════════════════════════════════════╣
║  BULL    ➕ 明確 pause guidance 終結 rate-path 不確定性 → vol 下行         ║
║  BEAR    ❌ Fed 鴿派最後堡壘陷落 + AI 集中度 SPY 與 rate path disconnect  ║
║  SECTOR  ❌ Bonds proxy 殺;Banks/Insurance 強;Energy 受惠 reflation     ║
║          tickers: XLF, JPM, BAC, WFC, BRK.B, TLT, XLU, XLRE, XLE, IWM    ║
║  MACRO   ❌ 升息尾部 15%→30-40%;2y +15-20bp 測 5.0%;bear steepening      ║
║  ARBITER → BEARISH, Macro 50% + 三方一致 HIGH 信心下行                   ║
╠══════════════════════════════════════════════════════════════════════════╣
║  受惠 ↑  Financials (Banks), Energy                                      ║
║  受損 ↓  Real Estate, Utilities, Small Caps, Technology                  ║
║  Binary Risk  No                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Cache:  sector_intel pending  │  phase0 ✅                              ║
╚══════════════════════════════════════════════════════════════════════════╝
```

- **Source**: [WSJ — Fed's Waller: Inflation Risks Mean Fed Should No Longer Signal Cuts](https://www.wsj.com/economy/central-banking/feds-waller-inflation-risks-mean-fed-should-no-longer-signal-cuts-73c965c1) | HIGH | 2026-05-22T10:39 UTC
- **Debate note**: 6 月 CPI 若 sticky 是否觸發 dot plot 上修 + multiple compression。Waller (前鴿派) 與 Warsh (新主席) 同日鷹派表態 — coordination signal 強烈

---

### Verdict #3 — n0331 Consumer sentiment hits fresh record low

```
╔══════════════════════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-05-22 10:11 UTC  │  MODE: DIGEST                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║  [BEARISH -2.3]  Consumer sentiment hits fresh record low (Iran war)     ║
║  type: macro_data  │  weights: Macro 50%                                 ║
╠══════════════════════════════════════════════════════════════════════════╣
║  BULL    ➕ contrarian buy signal:8 次歷史低點後 12M S&P +24.6%          ║
║  BEAR    ❌ SPY 新高 vs sentiment 新低 divergence → 向下收斂風險          ║
║  SECTOR  ❌ XLY 全線 (TGT/M/F/GM/CCL) + Credit Card (V/MA/AXP) 承壓     ║
║          tickers: XLY, TGT, CMG, F, GM, CCL, DG, V, MA, AXP, WMT, COST   ║
║  MACRO   ❌ Stagflation 風險具體化;Fed 兩難 → 鷹派優先保 credibility     ║
║  ARBITER → BEARISH, Sector + Macro 一致下行,Bull contrarian 需 Iran 降溫前提 ║
╠══════════════════════════════════════════════════════════════════════════╣
║  受惠 ↑  Healthcare (defensive)                                          ║
║  受損 ↓  Consumer Discretionary, Financials, Industrials                 ║
║  Binary Risk  No                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Cache:  sector_intel pending  │  phase0 ✅                              ║
╚══════════════════════════════════════════════════════════════════════════╝
```

- **Source**: [CNBC — Consumer sentiment hits fresh record low in May](https://www.cnbc.com/2026/05/22/consumer-sentiment-hits-fresh-record-low-in-may-as-iran-war-fuels-inflation-worries.html) | HIGH | 2026-05-22T10:11 UTC
- **Debate note**: Bull(歷史 contrarian pattern,12M +24.6%) vs Bear(divergence 向下收斂 + 低端消費信用卡 delinquency 14yr high):Iran 緊張是否 6-7 月降溫帶動 sentiment 反彈

---

### Verdict #4 — n0272 Iran war + US gas 4-yr high (BINARY / Hormuz tail)

```
╔══════════════════════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-05-22 15:26 UTC  │  MODE: DIGEST                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║  [BINARY -1.6]  Iran war drives U.S. gas prices to 4-yr high             ║
║  type: geopolitical  │  weights: Macro 40% / Bear 30% / Bull+Sec 30%     ║
║  ⚠️  within_48h = TRUE (Hormuz outcome 二元結局)                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  BULL    ✅ Energy textbook setup:WTI $95-100,XOM/CVX FCF yield 15%     ║
║  BEAR    ❌ supply shock CPI +50-100bp → Fed 鷹派被迫回應 → 殺估值        ║
║  SECTOR  ✅ Energy/Defense 強;Airlines/Transportation/Chemicals 殺      ║
║          tickers: XLE, XOM, CVX, COP, VLO, MPC, FANG, SLB, LMT, RTX,     ║
║                    DAL, UAL, LUV, UPS, FDX, DOW, JETS                    ║
║  MACRO   ❌ break-even +30-50bp,10y 測 5.0-5.25%,brent $130 tail risk   ║
║  ARBITER → BINARY (二軸辯證對立 + Hormuz 二元 outcome + within_48h flag) ║
╠══════════════════════════════════════════════════════════════════════════╣
║  受惠 ↑  Energy (XLE), Defense                                           ║
║  受損 ↓  Airlines (JETS), Transportation (IYT), Materials/Chemicals      ║
║  Binary Risk  YES (Hormuz: 完全封閉 vs 局部干擾 → brent $130+ vs $90)    ║
║  Event Date  2026-05-25 watch                                             ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Cache:  sector_intel pending  │  phase0 ✅ (binary_risk appended)       ║
╚══════════════════════════════════════════════════════════════════════════╝
```

- **Source**: [CNBC Top — Iran war leaves U.S. gas prices at highest levels in nearly four years](https://www.cnbc.com/2026/05/22/gas-price-iran-war-strait-hormuz-memorial-day.html) | HIGH | 2026-05-22T15:26 UTC
- **Debate note**: Bull/Sector(Energy/Defense catalyst,$95-100 油價 + crack spread 擴張) vs Bear/Macro(stagflation 鏈條 + Fed 鷹派被迫回應):Hormuz 是否完全封閉決定 brent 是否 $130+

---

### Verdict #5 — n0092 Micron expands US memory chip production

```
╔══════════════════════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-05-22 22:30 UTC  │  MODE: DIGEST                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║  [BULLISH +2.2]  Micron expands US memory chip production amid AI surge  ║
║  type: corporate  │  weights: Sector 40% / Bull 25% / Bear 25% / Mac 10% ║
╠══════════════════════════════════════════════════════════════════════════╣
║  BULL    ✅ HBM3e 供需缺口 >30%,24+ 個月 visibility,MU fwd P/E 10-12x   ║
║  BEAR    ➖ 大 capex + 升息環境融資成本,2027 折舊壓力,ASP 修正 40%+ 風險 ║
║  SECTOR  ✅ Semis/Semicap 強 + AI infra 二階 + Data Center Power 受惠     ║
║          tickers: MU, SOXX, SMH, AMAT, LRCX, KLAC, ASML, NVDA, AVGO,     ║
║                    AMD, MSFT, META, GOOGL, EQIX, VST, CEG                ║
║  MACRO   ➕ second-order news,marginal USD positive,CHIPS Act narrative  ║
║  ARBITER → BULLISH, Sector + Bull 高信心一致 (HIGH),Bear 時間框架較遠   ║
╠══════════════════════════════════════════════════════════════════════════╣
║  受惠 ↑  Semiconductors, Semicap Equipment, Data Center REITs, Utilities ║
║  受損 ↓  China Memory (CXMT/YMTC) — onshoring 排擠                       ║
║  Binary Risk  No                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Cache:  sector_intel pending  │  phase0 ✅                              ║
╚══════════════════════════════════════════════════════════════════════════╝
```

- **Source**: [Fox Business — Micron expands US memory chip production amid AI demand surge](https://www.youtube.com/watch?v=BerUK-oJ4Fk) | HIGH | 2026-05-22T22:30 UTC
- **Debate note**: Bull/Sector(HBM 結構性需求缺口 + CHIPS Act 補貼 + AI 24+M visibility) vs Bear(記憶體週期擴產風險 + ASP 修正 40%+):Hyperscaler AI ROI 檢討是否在 2026H2 觸發 capex 鬆動

---

## 3. SHALLOW DIGEST (Top 20 — 一行式快照)

### [+4.0] n0064  This Week's Market Wrap: Nvidia, War Headlines, And FOMC Minutes
- **Bull**: NVDA 業績爆發確認 AI 週期
- **Bear**: 戰爭頭條牽動油價 殺估值風險升
- **Sector**: Energy + Defense + AI infra 同步輪動
- **Macro**: FOMC 紀要轉鷹強化 Fed path
- Source: Seeking Alpha HIGH │ type: monetary_policy
---

### [+4.0] n0316  Economic Data & Tech's Parabolic Rally Test SPX Record Run
- **Bull**: SPX 最長連勝週期 since 2023
- **Bear**: 軟數據 (消費信心) 開始 test rally
- **Sector**: 防禦股相對強勢
- **Macro**: 經濟數據雙面 + Fed path 不對稱
- Source: Schwab Network HIGH │ type: macro_data
---

### [-4.5] n0043  BrasilAgro Faces A Risk Storm But Crop Prices Are Not Reacting
- **Bull**: 估值已 bottom-cycle,週期反彈 optionality
- **Bear**: 3Q26 EBITDA 大幅下滑,作物價格 + input cost 雙殺
- **Sector**: 農業 commodities 個股風險
- **Macro**: EM 農業出口疲軟
- Source: Seeking Alpha HIGH │ type: earnings
---

### [+3.0] n0015  BOE: Collect An 8% Yield While Participating In AI Growth
- **Bull**: 8.3% 月分紅 + AI 上行 exposure
- **Bear**: closed-end fund discount + leverage tail
- **Sector**: 結構性收益型 vehicle
- **Macro**: 高利率環境支撐 income yield
- Source: Seeking Alpha HIGH │ type: earnings
---

### [-3.0] n0117  Spike in global bond yields a warning sign of market fragility despite strong earnings cycle: Citi
- **Bull**: 強勁財報週期支撐 EPS
- **Bear**: 10y 殖利率測 5% 估值脆弱
- **Sector**: 高 duration 板塊承壓
- **Macro**: Term premium 擴張 risk-off
- Source: CNBC International TV HIGH │ type: sentiment
---

### [+3.0] n0284  Dow Jones: Apple Hits $4.5T as AI Rally Sends US 30 to Record
- **Bull**: AI Rally 擴散到 Dow 大型股
- **Bear**: 集中度升 RSP-SPY gap 脆弱
- **Sector**: Mega-cap Tech 領漲 + 廣度差
- **Macro**: 風險偏好升但 yield 警示
- Source: FXEmpire HIGH │ type: sentiment
---

### [+3.0] n0032  Ukraine Drone Strike Sets Russia's Novorossiysk Oil Terminal Ablaze
- **Bull**: Brent supply premium 擴大利好 Energy
- **Bear**: 供應鏈中斷加劇 stagflation 鏈
- **Sector**: Energy + Defense 雙線受惠
- **Macro**: 通膨預期 unanchoring 風險
- Source: Benzinga HIGH │ type: geopolitical
---

### [-3.0] n0313  The new-Fed-chair 'curse' and $100-plus oil are already testing Kevin Warsh
- **Bull**: 鷹派 credibility 壓低 term premium
- **Bear**: 新主席要立威 multiple compression
- **Sector**: 利率敏感板塊承壓
- **Macro**: stagflation 風險顯著上升
- Source: Market Watch HIGH │ type: monetary_policy
---

### [-3.0] n0118  Former Kansas City Fed President Esther George: A rate hike is 'very much a possibility'
- **Bull**: 前 FOMC 言論影響有限
- **Bear**: 鷹派合唱加深 dot plot 上修壓力
- **Sector**: Banks 受惠 NIM 但 IWM 承壓
- **Macro**: 升息尾部風險再強化
- Source: CNBC International TV HIGH │ type: monetary_policy
---

### [-3.0] n0304  Traders Bet Warsh's Fed Will Hike Rates by December
- **Bull**: Hike 預期已 price 不再 surprise
- **Bear**: 12 月升息成 base case 多空轉折
- **Sector**: Bonds proxy 跌、Energy/Banks 升
- **Macro**: Fed funds path 重大 repricing
- Source: Bloomberg Markets and Finance HIGH │ type: monetary_policy
---

### [+3.0] n0062  Energy Transfer's Valuation Can't Be Justified In Light Of Its Surging NGL Exposure
- **Bull**: NGL exposure 上升 → 美墨灣出口槓桿
- **Bear**: MLP 估值已偏貴
- **Sector**: Midstream / Pipeline 個股
- **Macro**: 油 / 天然氣 export 結構性受惠
- Source: Seeking Alpha HIGH │ type: earnings
---

### [+3.0] n0078  Tutor Perini: Strong Backlog With Larger Higher-Margin Contracts
- **Bull**: backlog 強 + margin mix 改善 → upgrade
- **Bear**: 大型工程 execution risk + working capital 沉重
- **Sector**: Industrials / E&C 個股強訊號
- **Macro**: 基建支出韌性
- Source: Seeking Alpha HIGH │ type: earnings
---

### [+3.0] n0075  Upgrading eGain As Market Ignores Compelling Growth Catalysts
- **Bull**: 被忽視 small-cap SaaS,catalysts 接近
- **Bear**: 小型股升息環境融資困難
- **Sector**: Software/CCaaS 細分
- **Macro**: 小型股 IWM 整體承壓
- Source: Seeking Alpha HIGH │ type: earnings
---

### [-3.0] n0081  SES AI Corporation Securities Fraud Class Action Result of Weak Revenue Guidance
- **Bull**: 法律事件已 known,price-in
- **Bear**: 集體訴訟 + 弱 guidance + EV battery 賽道 stress
- **Sector**: EV/Battery 個股 idiosyncratic
- **Macro**: EV 需求疲軟連動
- Source: GuruFocus HIGH │ type: earnings
---

### [+3.0] n0238  Review & Preview: On the Bright Side
- **Bull**: 樂觀情緒 + IPO 解凍延續
- **Bear**: 樂觀偏誤 sentiment-高 vs hard data 落差
- **Sector**: Capital Markets / IPO
- **Macro**: risk-on 持續但有警訊
- Source: Barrons HIGH │ type: earnings
---

### [+2.0] n0286  Good News Is Good News. The Market Has Passed the Earnings Test.
- **Bull**: 財報季 EPS 上修 → 大盤 valid
- **Bear**: 已 price in 高 EPS 預期
- **Sector**: 全市場 EPS 革命確認
- **Macro**: earnings cycle 仍向上
- Source: Barrons HIGH │ type: sector_news
---

### [-2.0] n0044  Google Appeals Landmark Monopoly Ruling That Targets Apple Default Deals
- **Bull**: 上訴拖延執行 短期不影響營收
- **Bear**: 若敗訴 Apple 搜尋分潤被切
- **Sector**: Mega-cap Tech 監管尾部風險
- **Macro**: 反壟斷壓力不變 long-term de-rating
- Source: Benzinga HIGH │ type: corporate
---

### [+2.0] n0048  Semis Won The First AI Trade. Software May Win The Next One
- **Bull**: AI ROI 從 hardware 進入 software 階段
- **Bear**: software 估值仍偏高 + AI revenue 不明確
- **Sector**: Software vs Semis rotation 提示
- **Macro**: AI 主題 narrative 演化
- Source: Seeking Alpha HIGH │ type: sector_news
---

### [+2.0] n0288  USTR Greer sees no immediate chip tariffs but says protection important for sector
- **Bull**: 短期關稅疑慮解除 利好 SOXX
- **Bear**: 中長期保護主義基調未變
- **Sector**: Semi onshoring 政策確認
- **Macro**: tech goods 通膨壓力短期紓緩
- Source: Reuters HIGH │ type: sector_news
---

### [+2.0] n0178  Qualcomm's stock pop shows investors are 'waking up' to boom in AI devices
- **Bull**: QCOM 上漲反映 AI device cycle 確認
- **Bear**: 估值 + Apple modem migration 風險
- **Sector**: 邊緣 AI / Smartphone Semi
- **Macro**: AI 主題擴散
- Source: CNBC Top HIGH │ type: sentiment
---

## 4. KEY ACTIONABLE READS

| Theme | Direction | Tickers |
|---|---|---|
| **Energy supply tightness** | ↑↑ | XLE, XOM, CVX, COP, VLO, MPC, FANG, EOG, SLB, ET, EPD |
| **Defense / Iran tail** | ↑ | LMT, RTX, NOC, GD |
| **Banks (NIM expansion)** | ↑ | XLF, JPM, BAC, WFC |
| **AI memory / semicap onshoring** | ↑ | MU, SOXX, SMH, AMAT, LRCX, KLAC, ASML |
| **Data center power** | ↑ | VST, CEG, NRG, EQIX, DLR |
| **Bond proxies (殺估值)** | ↓↓ | TLT, XLU, XLRE, O, VICI |
| **Consumer discretionary (sentiment 殺)** | ↓ | XLY, XRT, TGT, M, F, GM, CCL |
| **Airlines / Transports (jet fuel 殺)** | ↓ | DAL, UAL, AAL, LUV, JETS, IYT |
| **Small caps (融資成本 + leverage)** | ↓ | IWM |
| **Mega-cap AI (multiple compression)** | ↓ (短期) | NVDA, MSFT, GOOGL, AAPL — but earnings 仍韌 |

---

## 5. BINARY RISKS (Phase 0 patched)

1. **Hormuz closure (n0272)** — within_48h flag. Brent $130+ tail vs $90 base. Watch 5/25.
2. **Iran ceasefire knife-edge (前置)** — 7/4 expires, oil-shock breakpoint.
3. **July rate-HIKE tail** — Yardeni + Goolsbee on inflation. Dec hike now base case post-Warsh + Waller.

---

## 6. CACHE STATUS

| Cache | Status | Note |
|---|---|---|
| `news_logs/2026-05-23_digest.json` | ✅ Written (validator pass) | 5 deep + 10 shallow |
| `news_logs/2026-05-23_triage.json` | ✅ 52 shallow, 5 stage2_items (manual override) | |
| `sector/sector_logs/phase0.json` | ✅ macro_backdrop -3.96 → -4.51 | binary_risk n0272 appended |
| `sector/sector_logs/2026-05-23_sector_intel.json` | ⏳ Pending (sector protocol not run today) | top_catalysts prepend deferred |

---

> **Discipline reminder**: 此 digest 為 short-term 新聞訊號,**不直接驅動** investment protocol 決策。Investment / Sector protocol 各有獨立 cache 與 weighting,本檔只 patch `phase0.json` 提供 macro backdrop reference。

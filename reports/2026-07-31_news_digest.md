# 新聞分析 DIGEST — 2026-07-31 22:15

## 1. Triage Summary

Stage 1 deterministic triage（`news/scripts/stage1_triage.py`）：427 則合併原始新聞（RSS 118 + Finnhub 30 + FMP 200 + EDGAR 100 - dedupe 1）→ scored 426，blocked 0，dedup 1 → **5 則晉級 Stage 2**。

```
✅ DEEP     n0249  [+5.0] Microsoft: I'm More Bullish Than Ever                        earnings
✅ DEEP     n0314  [+4.0] Life Time Holdings: Excellent Performance, But Lock In Gains sentiment
✅ DEEP     n0415  [-4.0] U.S. economy slowed to 1.5% growth rate in Q2; June core inf macro_data
✅ DEEP     n0026  [+3.0] Amazon surges 14%, Apple falls 9% as investors pick post-ear earnings
✅ DEEP     n0176  [-3.0] Coinbase Q2 earnings fall short of estimates as crypto marke earnings
❌ SKIP     n0202  [+3.0] Dow climbs 200 points at open as Amazon joins Microsoft in r earnings
❌ SKIP     n0215  [-3.0] Novo Nordisk Says Anti-Inflammatory Drug Trial Fails to Cut  sentiment
❌ SKIP     n0232  [+3.0] FormFactor Q2 Review: If You Haven't Sold On The Way Down, D earnings
❌ SKIP     n0258  [+3.0] WHD Q2 Earnings Beat Estimates on Pressure Control, Spoolabl earnings
❌ SKIP     n0268  [+3.0] Dolby's Q3 Earnings Beat Estimates on Lower Operating Expens earnings
❌ SKIP     n0269  [+3.0] Monolithic Power Beats Q2 Earnings Estimates on Enterprise D earnings
❌ SKIP     n0282  [+3.0] 5 Things to Know Before the Stock Market Opens on Friday     earnings
❌ SKIP     n0284  [+3.0] The Hidden Debt Is Getting Worrisome                         earnings
❌ SKIP     n0317  [-3.0] Puma posts Q2 sales slightly ahead of expectations           earnings
❌ SKIP     n0351  [+3.0] Korean Stock Surge Leads Asian Rally on Renewed AI Enthusias sentiment
```

`stage1_count` = 50（triage.json `shallow_verdicts` 長度）｜`stage2_count` = 5｜`fanout_mode` = PER_AGENT_BATCH（4 subagent 全成功，`degraded_agents=[]`）

---

## 2. Deep Analysis（Stage 2, 5 則）

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-07-31 22:15  │  MODE: DIGEST          ║
╠══════════════════════════════════════════════════════════╣
║  [BINARY +2.4]  微軟：我從未如此看多 (n0249)               ║
║  type: earnings  │  weights: Sector 40%                  ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ Azure guidance上修45%、backlog+84%至$678B      ║
║  BEAR    ❌ backlog為未兌現訂單，需鉅額capex才能轉換        ║
║  SECTOR  ✅ 雲端/半導體/資料中心電力 strong                ║
║           tickers: MSFT, NVDA, AMD, VRT, ETN, DLR, EQIX   ║
║  MACRO   ➖ 對Fed路徑中性偏微幅正向                        ║
║  ARBITER → Bull/Bear差7(≥4)裁BINARY，採Sector主論點        ║
╠══════════════════════════════════════════════════════════╣
║  受益產業 ↑ Cloud/半導體/資料中心   受損產業 ↓ None        ║
║  Binary Risk  No                                          ║
╚══════════════════════════════════════════════════════════╝
```
**Debate note**：Bull看多84% backlog增長與Azure guidance上修為AI貨幣化實證；Bear質疑backlog僅為未兌現訂單，需鉅額資本支出才能兌現，且Vertiv暴跌顯示供應鏈執行風險。

```
╔══════════════════════════════════════════════════════════╗
║  [BINARY -0.4]  Life Time Holdings：表現優異，但該獲利了結 (n0314) ║
║  type: sentiment │ weights: Bull/Bear 30%, Macro 25%      ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ 今年+60%、同店銷售+8.6%、資產輕量化擴張         ║
║  BEAR    ❌ 標題本身即「鎖利」訊號，評價已超前基本面        ║
║  SECTOR  ➖ 健身休閒中性偏弱，無明顯供應鏈外溢              ║
║           tickers: LTH, PLNT, XPOF                        ║
║  MACRO   ➖ 個股情緒文章，對總經無實質傳導                  ║
║  ARBITER → Bull/Bear差5(≥4)裁BINARY，基本面優異vs評價過熱  ║
╚══════════════════════════════════════════════════════════╝
```

```
╔══════════════════════════════════════════════════════════╗
║  [BINARY -1.9]  美國Q2 GDP放緩至1.5%；核心通膨3.3% (n0415) ║
║  type: macro_data │ weights: Macro 50%                    ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ 疲弱源自政府支出/存貨而非需求崩潰，通膨符合預期 ║
║  BEAR    ❌ 連兩季放緩+通膨頑固+殖利率19年高，類滯脹        ║
║  SECTOR  ❌ 利率敏感股(REITs/Utilities)承壓，銀行略受益     ║
║           tickers: XLU, XLRE, XLF, TLT                    ║
║  MACRO   ❌ 殖利率同日走高與鴿派解讀矛盾，財政供給/期限溢酬主導 ║
║  ARBITER → Bull/Bear差5(≥4)裁BINARY，呼應既有鷹派/高殖利率敘事 ║
╚══════════════════════════════════════════════════════════╝
```

```
╔══════════════════════════════════════════════════════════╗
║  [BINARY +1.1]  亞馬遜財報後+14%，蘋果重挫9% (n0026)        ║
║  type: earnings │ weights: Sector 40%                     ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ AMZN資本支出上修至$220B，AWS 18季最快成長       ║
║  BEAR    ❌ AAPL財報優於預期仍因guidance疲弱重挫9%，市場零容忍 ║
║  SECTOR  ✅ AI基礎設施供應鏈受惠 vs 消費硬體OEM承壓          ║
║           tickers: AMZN, AAPL, NVDA, AMD, MU, TSM, AVGO, VRT, DLR ║
║  MACRO   ➖ 資本支出挹注GDP投資項目，邊際偏鷹派              ║
║  ARBITER → Bull/Bear差7(≥4)裁BINARY，雲端贏家vs硬體輸家對立 ║
╚══════════════════════════════════════════════════════════╝
```

```
╔══════════════════════════════════════════════════════════╗
║  [BINARY -1.6]  Coinbase Q2獲利不如預期 (n0176)             ║
║  type: earnings │ weights: Sector 40%                     ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ 88%營收已來自現貨手續費以外，市占連3季創高      ║
║  BEAR    ❌ EPS虧損達預期逾3倍，加密貨幣疲軟拖累營收         ║
║  SECTOR  ❌ 加密交易所承壓，惟USDC穩定幣基礎設施受惠         ║
║           tickers: COIN, CRCL, MARA, RIOT, HOOD            ║
║  MACRO   ➖ 個股財報事件，對總經無直接傳導                   ║
║  ARBITER → Bull/Bear差7(≥4)裁BINARY，多元化進展vs財報大幅落差 ║
╚══════════════════════════════════════════════════════════╝
```

Cache Updated：`sector/sector_logs/phase0.json` ✅（top_catalysts prepend ×5、news_patch_count 168→173、macro_backdrop_score -4.85→-4.95）

---

## 3. Shallow Digest（Top 10, 依 |shallow_score| 排序）

### [+3.0] n0202  Dow climbs 200 points at open as Amazon joins Microsoft in reviving AI optimism
- **Bull**: 現金流改善空間 ｜ **Bear**: 成長放緩風險
- **Sector**: 行業內相對強弱 ｜ **Macro**: 成本控制關鍵
- Source: Invezz HIGH │ type: earnings

### [-3.0] n0215  Novo Nordisk Says Anti-Inflammatory Drug Trial Fails to Cut Cardiovascular Risk in High Risk Patients
- **Bull**: 市場情緒轉好 ｜ **Bear**: 情緒反轉風險
- **Sector**: 板塊追漲機會 ｜ **Macro**: 風險偏好提升
- Source: Benzinga HIGH │ type: sentiment

### [+3.0] n0232  FormFactor Q2 Review: If You Haven't Sold On The Way Down, Don't Sell On The Way Up
- **Bull**: 現金流改善空間 ｜ **Bear**: 成長放緩風險
- **Sector**: 行業內相對強弱 ｜ **Macro**: 成本控制關鍵
- Source: Seeking Alpha HIGH │ type: earnings

### [+3.0] n0258  WHD Q2 Earnings Beat Estimates on Pressure Control, Spoolable Growth
- **Bull**: 收益超預期提振前景 ｜ **Bear**: 高基期+競爭加劇
- **Sector**: 受惠產業擴張 ｜ **Macro**: 利率敏感性降低
- Source: Zacks Investment Research HIGH │ type: earnings

### [+3.0] n0268  Dolby's Q3 Earnings Beat Estimates on Lower Operating Expenses
- **Bull**: 收益超預期提振前景 ｜ **Bear**: 高基期+競爭加劇
- **Sector**: 受惠產業擴張 ｜ **Macro**: 利率敏感性降低
- Source: Zacks Investment Research HIGH │ type: earnings

### [+3.0] n0269  Monolithic Power Beats Q2 Earnings Estimates on Enterprise Data Growth
- **Bull**: 收益超預期提振前景 ｜ **Bear**: 高基期+競爭加劇
- **Sector**: 受惠產業擴張 ｜ **Macro**: 利率敏感性降低
- Source: Zacks Investment Research HIGH │ type: earnings

### [+3.0] n0282  5 Things to Know Before the Stock Market Opens on Friday
- **Bull**: 現金流改善空間 ｜ **Bear**: 成長放緩風險
- **Sector**: 行業內相對強弱 ｜ **Macro**: 成本控制關鍵
- Source: Investopedia HIGH │ type: earnings

### [+3.0] n0284  The Hidden Debt Is Getting Worrisome
- **Bull**: 現金流改善空間 ｜ **Bear**: 成長放緩風險
- **Sector**: 行業內相對強弱 ｜ **Macro**: 成本控制關鍵
- Source: Seeking Alpha HIGH │ type: earnings

### [-3.0] n0317  Puma posts Q2 sales slightly ahead of expectations
- **Bull**: 現金流改善空間 ｜ **Bear**: 成長放緩風險
- **Sector**: 行業內相對強弱 ｜ **Macro**: 成本控制關鍵
- Source: Reuters HIGH │ type: earnings

### [+3.0] n0351  Korean Stock Surge Leads Asian Rally on Renewed AI Enthusiasm
- **Bull**: 市場情緒轉好 ｜ **Bear**: 情緒反轉風險
- **Sector**: 板塊追漲機會 ｜ **Macro**: 風險偏好提升
- Source: WSJ HIGH │ type: sentiment

---

`session_macro_delta` = **-0.1**（今日5則深度分析淨衝擊，主要由n0415 GDP/通膨數據拖累）

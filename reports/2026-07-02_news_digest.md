# 新聞分析 DIGEST — 2026-07-02

> Mode: DIGEST │ Stage1 scored=391 │ blocked=13 (law_firm_solicitation) │ dedup=4 │ 晉級 Stage2=5
> Fanout: PER_AGENT_BATCH（4 lane 全成功，無降級）│ session_macro_delta: **-0.1**

---

## 1. Triage Summary（Stage 1 script 篩選表，top 25 of 50）

| Tag | news_id | Score | Headline | Type |
|---|---|---|---|---|
| ✅ DEEP | n0300 | +4.5 | Unusual Machines: Riding The Pentagon's Multi-Billion Dollar Drone Push | corporate |
| ✅ DEEP | n0372 | -4.5 | O-I Glass: Upside Is Questionable Now (Downgrade) | earnings |
| ✅ DEEP | n0169 | +4.0 | June Jobs Report: Winning Streak Stalls As Employers Add Less Than Expected | macro_data |
| ✅ DEEP | n0146 | +3.0 | Can Orion Convert $200M of New Awards Into Stronger 2026 Results? | corporate |
| ✅ DEEP | n0152 | +3.0 | Top-Performing ETF Areas of 1H 2026 | earnings |
| ❌ SKIP | n0186 | +3.0 | Tesla posts stronger-than-expected Q2 deliveries as Europe sales improve | earnings |
| ❌ SKIP | n0197 | +3.0 | As U.S. Stock Markets Continue Rallying... ELEKTROS Strengthens Its Vision | sentiment |
| ❌ SKIP | n0210 | +3.0 | Bloom Energy's Long-Term Rally Is Just Getting Started | earnings |
| ❌ SKIP | n0219 | -3.0 | RBLX INVESTOR NOTICE: Roblox Corporation Investors with Substantial Losses | earnings |
| ❌ SKIP | n0220 | -3.0 | HUBG INVESTOR ALERT: Hub Group, Inc. Investors with Substantial Losses | sentiment |
| ❌ SKIP | n0227 | -3.0 | CVLT INVESTOR NOTICE: Commvault Systems, Inc. Investors with Substantial Losses | earnings |
| ❌ SKIP | n0259 | +3.0 | Bandwidth Is Building A Stronger AI Growth Story | earnings |
| ❌ SKIP | n0269 | +3.0 | Natural Resource Partners: Nearing Debt-Free Status Despite Soda Ash Headwinds | earnings |
| ❌ SKIP | n0389 | +3.0 | Cramer shares next steps for a software stock after a rare bullish analyst call | earnings |
| ❌ SKIP | n0059 | +2.0 | Bitcoin and ethereum prices today, Thursday, July 2 | macro_data |
| ❌ SKIP | n0123 | +2.0 | Best Gold Stocks Right Now | sector_news |
| ❌ SKIP | n0132 | +2.0 | Technical Assessment: Bullish in the Intermediate-Term | sentiment |
| ❌ SKIP | n0161 | +2.0 | Tesla crushes delivery estimates, giving its stock a boost | sentiment |
| ❌ SKIP | n0168 | +2.0 | Aura Minerals' Shares Rise 20% YTD | sentiment |
| ❌ SKIP | n0229 | -2.0 | VERI INVESTOR NOTICE: Veritone, Inc. Investors with Substantial Losses | sentiment |
| ❌ SKIP | n0249 | -2.0 | Hiring slowed in June, unemployment rate ticked down | macro_data |
| ❌ SKIP | n0255 | +2.0 | Sky-high funding rates spell danger | sentiment |
| ❌ SKIP | n0271 | +2.0 | 'Buy Now, While Supplies Last' Doesn't Apply to Stocks | macro_data |
| ❌ SKIP | n0301 | -2.0 | Chinese and US risks mean EU chip sector faces a 'bleak future' | geopolitical |
| ❌ SKIP | n0324 | +2.0 | Yen Consolidates Ahead of U.S. Nonfarm Payrolls Report | macro_data |

---

## 2. Deep Analysis（Stage 2 晉級 5 則 — Bull/Bear/Sector/Macro 四視角 + Arbiter 裁決）

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-07-02 21:44  │  MODE: DIGEST          ║
╠══════════════════════════════════════════════════════════╣
║  [BINARY +1.8]  Unusual Machines：搭上五角大廈千億美元無人機採購浪潮 ║
║  type: corporate  │  weights: Sector 40% / Bull Bear 25% / Macro 10%
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ Pentagon戰略資本辦公室潛在注資 + Q1營收年增296%      ║
║  BEAR    ❌ 政府融資未定案，同步啟動多線資本支出燒錢             ║
║  SECTOR  ✅ 國防/無人機在地供應鏈正面，binary_risk（融資未定）  ║
║           tickers: UMAC                                     ║
║  MACRO   ➖ 個股層級事件，總經傳導極有限                        ║
║  ARBITER → BINARY，四方分歧達6分（Bull+4 vs Bear-2）觸發BINARY規則║
╠══════════════════════════════════════════════════════════╣
║  受益產業 ↑  國防/無人機製造 (bullish)  美國工業在地化供應鏈 (bullish) ║
║  受損產業 ↓  None            Binary Risk  Yes（Pentagon融資決議未定）║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel.json N/A（檔案不存在，跳過）phase0.json ✅ ║
╚══════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-07-02 21:44  │  MODE: DIGEST          ║
╠══════════════════════════════════════════════════════════╣
║  [BINARY -1.4]  O-I Glass 遭降評：上行空間存疑              ║
║  type: earnings  │  weights: Sector 40% / Bull Bear 25% / Macro 10%
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ 估值相對同業便宜，2029年EBITDA目標保留             ║
║  BEAR    ❌ Q1營收衰退+虧損擴大+財測下修+高槓桿放大下檔風險     ║
║  SECTOR  ❌ 公司特定執行/成本問題，未見產業性需求衝擊           ║
║           tickers: OI                                       ║
║  MACRO   ➖ 個股信用/槓桿故事，緊縮週期典型案例                 ║
║  ARBITER → BINARY，四方分歧達4分（Bull+1 vs Bear-3）觸發BINARY規則║
╠══════════════════════════════════════════════════════════╣
║  受益產業 ↑  None             受損產業 ↓  玻璃/剛性包裝 (bearish)║
║  Binary Risk  No                                             ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel.json N/A（檔案不存在，跳過）phase0.json ✅ ║
╚══════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-07-02 21:44  │  MODE: DIGEST          ║
╠══════════════════════════════════════════════════════════╣
║  [BINARY -1.2]  6月非農報告：連續增長熄火，新增就業不如預期      ║
║  type: macro_data  │  weights: Macro 50% / Sector 20% / Bull Bear 15%
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ 降溫勞動市場有助Fed轉鴿，重啟降息預期辯論           ║
║  BEAR    ❌ 57K遠低於100K+預期，循環性雇用動能停滯疑慮          ║
║  SECTOR  ➖ 純總經事件，服務業/醫療保健相對抗跌                 ║
║           tickers: (無 — 純總經數據事件)                      ║
║  MACRO   ❌ 鴿派重定價 vs 失業率回落矛盾訊號，信心度受限         ║
║  ARBITER → BINARY，四方分歧達5分（Bull+2 vs Bear-3）觸發BINARY規則║
╠══════════════════════════════════════════════════════════╣
║  受益 ↑ 利率敏感類股(金融/REITs)   受損 ↓ 廣義市場/小型股(Russell 2000)║
║  Binary Risk  No（屬定期排程數據，非binary event）             ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel.json N/A（檔案不存在，跳過）phase0.json ✅ ║
╚══════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-07-02 21:44  │  MODE: DIGEST          ║
╠══════════════════════════════════════════════════════════╣
║  [BINARY +1.1]  Orion 能否將 2 億美元新訂單轉化為更強勁的 2026 年業績？ ║
║  type: corporate  │  weights: Sector 40% / Bull Bear 25% / Macro 10%
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ Q1新訂單2.19億美元+待完成訂單6.68億美元+230億管線   ║
║  BEAR    ❌ 訂單轉化執行風險 + McAmis併購新增4700萬美元槓桿      ║
║  SECTOR  ✅ 海事/重型土木建築供應鏈正面，小型股併購驅動成長      ║
║           tickers: ORN                                       ║
║  MACRO   ➖ 純個股層級事件，總經傳導極有限                       ║
║  ARBITER → BINARY，四方分歧達5分（Bull+3 vs Bear-2）觸發BINARY規則║
╠══════════════════════════════════════════════════════════╣
║  受益產業 ↑  海事/重型土木建築 (bullish)  受損產業 ↓  None       ║
║  Binary Risk  No                                              ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel.json N/A（檔案不存在，跳過）phase0.json ✅ ║
╚══════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-07-02 21:44  │  MODE: DIGEST          ║
╠══════════════════════════════════════════════════════════╣
║  [BINARY +1.8]  2026 上半年表現最佳的 ETF 板塊                ║
║  type: earnings  │  weights: Sector 40% / Bull Bear 25% / Macro 10%
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ SOXX+113%/PSI+138%/AIS+124%/EWY+106%全面領漲       ║
║  BEAR    ❌ 槓桿型2倍單一個股ETF主導榜首，晚期投機擁擠訊號       ║
║  SECTOR  ✅ AI資本支出/記憶體超級週期實證確認，惟為回顧性數據     ║
║           tickers: SOXX, PSI, AIS, EWY, BWET                 ║
║  MACRO   ❌ BWET航運+684%暗示運價通膨，與鷹派立場相互強化        ║
║  ARBITER → BINARY，四方分歧達7分；Sector vs Macro差5分採Sector主論點║
╠══════════════════════════════════════════════════════════╣
║  受益產業 ↑  半導體/AI硬體  記憶體/南韓科技  油輪航運（皆bullish）║
║  受損產業 ↓  None            Binary Risk  No                  ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel.json N/A（檔案不存在，跳過）phase0.json ✅ ║
╚══════════════════════════════════════════════════════════╝
```

**觀察**：本輪 5 則晉級新聞的四方 impact_score 分歧幅度全數 ≥4，依 Arbiter 仲裁規則全數裁定為 `BINARY`（非單純方向性 BULLISH/BEARISH）。這反映 Bull/Bear 兩方確實依規則進行了真實對立辯論（並未因「與共識一致」而收斂分數），而非系統性偏誤——`net_impact_score` 的加權方向仍可作為淨傾向參考（UMAC/ORN/ETF板塊 偏多；O-I Glass/非農 偏空）。

---

## 3. Shallow Digest（Top 10 by \|shallow_score\|，snaps 照抄 triage.json）

### [+3.0] n0186 特斯拉 Q2 交車優於預期，歐洲銷售回溫抵銷北美疲軟
- **Bull**: 現金流改善空間 ｜ **Bear**: 成長放緩風險
- **Sector**: 行業內相對強弱 ｜ **Macro**: 成本控制關鍵
- Source: Reuters HIGH │ type: earnings

### [+3.0] n0197 美股持續創新高之際，ELEKTROS 強化高速充電站布局願景
- **Bull**: 市場情緒轉好 ｜ **Bear**: 情緒反轉風險
- **Sector**: 板塊追漲機會 ｜ **Macro**: 風險偏好提升
- Source: Accesswire HIGH │ type: sentiment

### [+3.0] n0210 Bloom Energy 長期漲勢才剛起步
- **Bull**: 現金流改善空間 ｜ **Bear**: 成長放緩風險
- **Sector**: 行業內相對強弱 ｜ **Macro**: 成本控制關鍵
- Source: Seeking Alpha HIGH │ type: earnings

### [-3.0] n0219 Roblox（RBLX）投資人集體訴訟通知：股價重挫求償機會
- **Bull**: 現金流改善空間 ｜ **Bear**: 成長放緩風險
- **Sector**: 行業內相對強弱 ｜ **Macro**: 成本控制關鍵
- Source: PRNewsWire HIGH │ type: earnings

### [-3.0] n0220 Hub Group（HUBG）投資人集體訴訟警示
- **Bull**: 市場情緒轉好 ｜ **Bear**: 情緒反轉風險
- **Sector**: 板塊追漲機會 ｜ **Macro**: 風險偏好提升
- Source: PRNewsWire HIGH │ type: sentiment

### [-3.0] n0227 Commvault（CVLT）投資人集體訴訟通知：股價曾單日重挫 31%
- **Bull**: 現金流改善空間 ｜ **Bear**: 成長放緩風險
- **Sector**: 行業內相對強弱 ｜ **Macro**: 成本控制關鍵
- Source: PRNewsWire HIGH │ type: earnings

### [+3.0] n0259 Bandwidth 正打造更強勁的 AI 成長故事
- **Bull**: 現金流改善空間 ｜ **Bear**: 成長放緩風險
- **Sector**: 行業內相對強弱 ｜ **Macro**: 成本控制關鍵
- Source: Seeking Alpha HIGH │ type: earnings

### [+3.0] n0269 Natural Resource Partners：儘管純鹼逆風仍近乎無債
- **Bull**: 現金流改善空間 ｜ **Bear**: 成長放緩風險
- **Sector**: 行業內相對強弱 ｜ **Macro**: 成本控制關鍵
- Source: Seeking Alpha HIGH │ type: earnings

### [+3.0] n0389 Cramer：軟體股獲罕見分析師看多評級後的操作建議
- **Bull**: 現金流改善空間 ｜ **Bear**: 成長放緩風險
- **Sector**: 行業內相對強弱 ｜ **Macro**: 成本控制關鍵
- Source: CNBC HIGH │ type: earnings

### [+2.0] n0059 比特幣與以太幣今日行情：受 6 月就業報告激勵走高
- **Bull**: 經濟動能疲軟 ｜ **Bear**: 衰退擔憂加重
- **Sector**: 防守股相對強勢 ｜ **Macro**: 降息預期升溫
- Source: Yahoo Finance HIGH │ type: macro_data

---

## Cache Patch 紀錄

- `news/news_logs/2026-07-02_digest.json` ✅ Written（validator rc=0）
- `sector/sector_logs/phase0.json` ✅ Patched — `news_patch_count` 122→127、`macro_backdrop_score` -5.2→-5.3、`binary_risks` 新增 n0300（UMAC Pentagon融資，event_date 未定）、`top_catalysts` prepend 5 則
- `sector/sector_logs/sector_intel.json` ⚠️ 檔案不存在（尚未經由 `產業掃描` 建立），本次跳過該項 patch，非 fatal

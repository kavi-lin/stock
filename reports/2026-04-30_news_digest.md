# News Digest — 2026-04-30 12:30 (DIGEST)

> **Pipeline**：raw 4 sources (RSS+Finnhub+FMP+SEC EDGAR, 403 dedupe) → Stage 1 triage 25 → Stage 2 deep 5（PER_AGENT_BATCH，無 degradation）→ Arbiter → cache patch ✅ → MD
> **Session macro_delta**：**-0.35**（油 / 日圓雙重 binary 主導，AI capex 利多部分抵消）

---

## 1. TRIAGE SUMMARY

```
╔══════════════════════════════════════════════════════════════════════════╗
║  NEWS TRIAGE  │  2026-04-30 12:30  │  25 則 → 5 則晉級                  ║
╠══════════════════════════════════════════════════════════════════════════╣
║  ✅ DEEP   n0020  [+4.0]  Alphabet capex $190B 2026                earnings        ║
║  ✅ DEEP   n0049  [+4.0]  Eli Lilly mega beat + GLP-1 $12.9B/Q     earnings        ║
║  ✅ DEEP   n0042  [-3.5]  Yen +3% biggest rally since 2022         monetary_policy ║
║  ✅ DEEP   n0088  [-2.5]  Brent $126 + Trump Iran blockade [BIN]   geopolitical    ║
║  ✅ DEEP   n0009  [+1.0]  MSFT slips despite Azure beat            earnings        ║
║  ──────────────────────────────────────────────────────────────────────  ║
║  ❌ SKIP   n0193  [-3.0]  GE HealthCare crash 13% on guidance cut   earnings       ║
║  ❌ SKIP   n0079  [+3.0]  Google pops on Full Stack AI              earnings       ║
║  ❌ SKIP   n0085  [-2.5]  Stellantis -10% post Q1                   earnings       ║
║  ❌ SKIP   n0016  [+2.5]  Caterpillar AI buildout drives outlook    earnings       ║
║  ❌ SKIP   n0076  [+2.5]  Entegris tops on AI demand                earnings       ║
║  ❌ SKIP   n0056  [+2.5]  UBS Q1 +80% beat                          earnings       ║
║  ❌ SKIP   n0017  [+2.0]  LLY lifts annual forecasts (oral pill)    earnings       ║
║  ❌ SKIP   n0111  [+2.0]  Lilly $12.9B GLP-1 quarterly run-rate     earnings       ║
║  ❌ SKIP   n0164  [+2.0]  META lowest multiple in Mag-7             earnings       ║
║  ❌ SKIP   n0188  [+2.0]  META business AI 10M conv/wk              corporate      ║
║  ❌ SKIP   n0001  [-1.5]  Trump Iran blockade rhetoric              geopolitical   ║
║  ❌ SKIP   n0029  [+1.5]  US railroads $85B merger (UNP/NSC)        corporate      ║
║  ❌ SKIP   n0073  [+1.5]  RCL bookings recovering as Iran fear ease sentiment      ║
║  ❌ SKIP   n0185  [+1.5]  60/40 portfolio crushing it               sentiment      ║
║  ❌ SKIP   n0192  [+1.5]  Cardinal Health raises FY guidance        earnings       ║
║  ❌ SKIP   n0154  [-1.0]  US weighs troop reduction in Germany      geopolitical   ║
║  ❌ SKIP   n0158  [+1.0]  NVDA invests in Legora AI legal           corporate      ║
║  ❌ SKIP   n0030  [-0.5]  BoE holds 3.75% as Iran war shakes        monetary_policy║
║  ❌ SKIP   n0011  [-0.5]  MA Q1 beats but April cross-border slows  earnings       ║
║  ❌ SKIP   n0003  [+0.5]  ECB holds rates steady                    monetary_policy║
║  ❌ SKIP   n0162  [ 0.0]  Disney wait-and-see ahead of earnings     sentiment      ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 2. DEEP ANALYSIS — 5 ITEMS

### Impact Card #1 — n0020 [BULLISH +2.6]

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-04-30 12:12  │  MODE: DIGEST          ║
╠══════════════════════════════════════════════════════════╣
║  [BULLISH +2.6]  Alphabet capex 上修至 $190B（2026），    ║
║                  2027 將『顯著加碼』                       ║
║  type: earnings   │  weights: B25 / Br25 / S40 / M10      ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ +5  Cloud booming + Full Stack AI 變現確認，    ║
║                  AI infra 全鏈條 demand pull-through         ║
║  BEAR    ❌ -2  margin/FCF 擠壓，2027 derating trap 風險   ║
║  SECTOR  ✅ +4  Semis / Power / HVAC / Networking 強利多    ║
║                  NVDA AVGO TSM ASML VRT GEV CEG VST CARR    ║
║  MACRO   ➕ +2  productivity 敘事支撐 Fed 鴿派傾向          ║
║  ARBITER → BULLISH，採 Sector 主論點                        ║
╠══════════════════════════════════════════════════════════╣
║  受益：Semi ↑strong  Tech ↑mod  Util ↑mod  Indu ↑mod      ║
║  受損：(none — 但 hyperscaler 自身軟體 margin 受壓)        ║
║  Binary：No                                                ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel ✅  phase0 ✅                ║
╚══════════════════════════════════════════════════════════╝
```

**Bull**：Alphabet capex 自原本市場共識的 $160-170B 拉到 $190B，且 2027 還要『顯著增加』，是 AI infra 結構性需求最有力的背書。Cloud 營收 booming 證明企業 AI 變現是真的；TPU+Gemini+GCP+Vertex 的『Full Stack』敘事讓 GOOG 在自家堆疊抓 margin、不只是把 capex 漏給 NVDA。對市場而言，這是對 AI 供應鏈的需求 pull-through：semis、networking、power/cooling、data-center REITs，每 $1 hyperscaler capex 通常 spawn 2-3x 下游營收。

**Bear**：$190B capex + 2027 顯著加碼是 margin 與 FCF 擠壓被包成 AI 利多。折舊壓力會在 2027-28 全面顯現，AI workload 的 unit economics 仍未證明。Search 仍是金牛養月球計畫，任何被 Perplexity/ChatGPT 蠶食的查詢量都會放大失衡。市場已開始擔心 Mag-7 capex digestion（同日 MSFT 即跌就是訊號），設置了典型『先花、ROIC 後到』的 derating trap。

**Sector**：受惠 NVDA GPU、AVGO ASIC（TPU 合作）、TSM 先進製程、ASML EUV；power/cooling 端 VRT/ETN/EMR/GEV/CEG/VST 量價齊揚；HVAC 的 CARR/JCI、銅纜的 PWR/MTZ、變電站旁工業 REIT、以及 24/7 GPU cluster 所需的 nat-gas/uranium baseload。確認 Industrials 熱度並重新背書 Semis_AI 主軸；唯一逆風是 hyperscaler 自身軟體 margin 被 capex 強度壓縮（與 n0009 互相印證）。

**Macro**：Fed path 中性偏小幅鴿；持續 AI capex 支撐 productivity 敘事，符合 Powell『supply-side soft landing』框架。Curve bear-steepener，2y 不動、10y +2-4bp、30y +3-5bp。DXY 微撐、銅/銀因 data-center 電氣化買盤強。歷史類比 1996-99 telecom/fiber 超級資本周期 + 2024 Q1 META/GOOGL guide-up（10y 兩週內 +15bp、USD +1%）。

**Arbiter**：Bull-Bear spread = 7 但屬正常 capex 利多/利空辯論而非離散事件，故不升級為 BINARY。採 Sector 主論點。Bear 的『2027 derating trap』記入再評條件。

---

### Impact Card #2 — n0049 [BULLISH +2.0]

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-04-30 12:01  │  MODE: DIGEST          ║
╠══════════════════════════════════════════════════════════╣
║  [BULLISH +2.0]  Eli Lilly 大幅超預期，GLP-1 季銷售          ║
║                  $12.9B，全年指引上修 $2B                   ║
║  type: earnings   │  weights: B25 / Br25 / S40 / M10      ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ +4  GLP-1 franchise 持續複利，orforglipron 開新  ║
║                  TAM；防禦性成長皇冠                         ║
║  BEAR    ❌ -1  集中度極端、IRA 2027-28 + Phase 3 風險       ║
║  SECTOR  ✅ +3  LLY/CDMO 強，NVO 競爭壓力升；Staples 弱       ║
║                  CTLT TMO DHR WST BDX；KHC GIS MDLZ          ║
║  MACRO   ➕ +1  PCE 健康貢獻溫和，Fed 中性                   ║
║  ARBITER → BULLISH，採 Sector + Bull                        ║
╠══════════════════════════════════════════════════════════╣
║  受益：Healthcare ↑strong  Industrials ↑weak               ║
║  受損：Consumer_Staples ↓weak (snack/QSR pressure)         ║
║  Binary：No                                                ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel ✅  phase0 ✅                ║
╚══════════════════════════════════════════════════════════╝
```

**Bull**：Lilly 在關稅 / 油價 / capex 焦慮的盤面下提供防禦性成長皇冠：tirzepatide 單季 $12.9B 年化超 $50B，等於把 top-10 pharma 規模塞進一個產品家族還在複利。全年 sales outlook 上修 $2B + adjusted profit 同步加碼，意味產能瓶頸鬆動且需求對宏觀無感。口服 GLP-1 (orforglipron) 開啟下一段曲線：TAM 擴展到怕針族與冷鏈薄弱的新興市場。Healthcare 在 sector ranking 屬 Cold，正是 best-in-class 名字突破而族群 lag 的反向設置。

**Bear**：$12.9B/Q 單一產品線創造極端集中：safety signal、PBM formulary、IRA 2027-28（LLY 已被點名）、compounding 復活，任何一項都會崩 multiple。口服 GLP-1 假設 Phase 3 完美 + pricing power 成立，兩者都脆弱。LLY 50x+ forward 估值意味 2026 H2 任何小 miss 都不被原諒。蔓延風險：若 LLY GLP-1 TAM 假設下修，NVO 與整個肥胖相關生態系（醫材 bariatric、食品/飲料 staples）一起重新定價。

**Sector**：tirzepatide $12.9B/Q + orforglipron pipeline 鞏固 GLP-1 龍頭，NVO 競爭護城河受壓（NVO ADR 預估 -3 ~ -5%）。受惠：生物 CDMO（CTLT — LLY 合作、TMO/DHR fill-finish）、自動注射器（WST/BDX）、特殊藥品冷鏈物流。負面 read：減重/零食壓力打到 packaged-food（KHC/GIS/MDLZ）與 QSR 客流，呼應 Consumer_Staples 的 Avoid 標籤。Healthcare 整體 Cold，所以這是 LLY/NVO 個股故事而非全 sector lift。

**Macro**：Fed path 中性，GLP-1 屬微觀；Curve 可忽略；歷史類比 2023 Q3 LLY/NVO blowout 造成 XLP 1 日 -2% 輪動但 zero rates impact。

**Arbiter**：Sector 主論點被採納；Bear 的『集中度 + IRA + Phase 3 風險』屬 mid-term 觀察點，不影響短期 verdict。Bull-Bear spread = 5 但屬正常的 EPS-beat 高估值股辯論，未升級 BINARY。

---

### Impact Card #3 — n0042 [BINARY -2.1] ⚠️ within 48h

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-04-30 12:03  │  MODE: DIGEST          ║
╠══════════════════════════════════════════════════════════╣
║  [BINARY -2.1]  日圓單日急升 3% — 2024-08 carry unwind     ║
║                  重演風險 / BoJ 口頭干預                     ║
║  type: monetary_policy │ weights: B15 / Br15 / S20 / M50  ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ +3  強日圓 = 反通膨 + Fed put 強化；BoE/ECB hold ║
║                  顯央行不恐慌；US JPY-revenue 翻譯利多       ║
║  BEAR    ❌ -4  carry-unwind 重演 → vol-target/risk-parity   ║
║                  機械去槓桿；Mag-7 + Financials 蔓延         ║
║  SECTOR  ❌ -2  Tech / Semis / Financials / Cons.Disc 承壓   ║
║                  TM SONY MUFG NVDA MSFT META FXY            ║
║  MACRO   ❌ -3  全球流動性收緊；2024-08 / 1998-LTCM 類比      ║
║  ARBITER → BINARY，spread=7 + within_48h                   ║
╠══════════════════════════════════════════════════════════╣
║  受益：(none confirmed)                                     ║
║  受損：Tech / Semis / Financials / Cons.Disc 全部 binary     ║
║  Binary：YES — 24-72h 觀察 USDJPY 是否破 145                 ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel ✅  phase0 binary ✅          ║
╚══════════════════════════════════════════════════════════╝
```

**Bull**：USDJPY -3% 對 select cohort 反而利多。強日圓緩解日本進口能源成本，部分對沖 Brent 全球 pass-through，邊際反通膨，紓解 Fed 緊縮尾風險。日本出口商遭健康 reset（已是擁擠空頭），美國 JPY 收入的多國公司（AAPL/MCD/KO/BA）獲翻譯順風。BoE 同日在 Iran 衝擊下仍按兵不動 3.75%，央行沒在恐慌升息 — 風險資產獲穩定利率背景。Carry-unwind 尾風險仍在但 BoJ 已建立『口頭底』，最大空氣口袋過去。

**Bear**：3% 單日日圓漲幅是自 2024 年 8 月以來最大聲的 carry-trade unwind 警報。USDJPY 急殺迫使 JPY-funded 槓桿多頭（Nasdaq mega-cap、EM、commodities、gold）同步去槓桿。再疊加 BoE 在 Iran 戰爭升溫下 hold，這是穿著 FX 噪音外衣的全球流動性收縮訊號。歷史先例：2024-08 yen 急升觸發 Nikkei -12% drawdown 與 S&P 72 小時內 -7% intraday flush。Risk-parity 與 vol-target 基金將機械性 degross。Financials 透過 JPY funding 帳戶承受全球敞口；跨資產蔓延是 base case。

**Sector**：3% USDJPY rally 押韻 2024-08 carry-unwind 那次重擊 Mag-7 momentum 與小型股 5 個 session。JPY-funded 槓桿多頭被迫降槓桿，high-beta semis 與 momentum tech 最暴露。日本出口商 ADR（TM/SONY/HMC/MUFG）面臨翻譯與競爭力 drag。BINARY 警告：這是口頭干預非實際升息，若無 follow-through 24-48h 內可能完全反轉。

**Macro**：Fed path 曖昧偏鴿；JPY 升 = 全球金融條件收緊 = 市場替 Fed 做事。Curve bull-flattener 若 unwind 升級。USDJPY -3% 已印；DXY -0.6 ~ -0.8；Cross-yen 對（AUDJPY/MXNJPY）-4 ~ -6% 是 carry canary。歷史類比：2024-08-05（USDJPY -3.5% / S&P -6% / VIX 65）、1998-10 LTCM/yen squeeze（USDJPY -15% / Fed 緊急降息）、2022-09 純口頭干預版本 2 週內反轉。

**Arbiter**：Bull-Bear-Macro spread = 7 ≥ 4 + 屬離散 carry-unwind 觸發事件 + within_48h，依規則升級為 BINARY 而非 BEARISH。Macro 50% 權重主導：若 unwind 升級，Mag-7 + financials -3 ~ -5%；若僅口頭止住，48-72h 內可能反轉。所有相關產業 verdict 等級已各降一級。

---

### Impact Card #4 — n0088 [BINARY -1.0] ⚠️ within 48h, expires 2026-05-02

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-04-30 11:37  │  MODE: DIGEST          ║
╠══════════════════════════════════════════════════════════╣
║  [BINARY -1.0]  Brent 摸 $126 後回吐，Trump 對 Iran『封鎖』  ║
║                  言論 / Hormuz 動能視窗本週                 ║
║  type: geopolitical │ weights: B15 / Br30 / S15 / M40     ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ +4  恐慌溢價衰減；Energy/Defense 結構受惠        ║
║                  XOM CVX SLB HAL LMT RTX                    ║
║  BEAR    ❌ -4  $10/桶 Brent → CPI +25bp + GDP -0.2%；      ║
║                  stagflation shock 未被 price in            ║
║  SECTOR  ✅ +3  Energy ↑strong / Defense ↑mod；Airlines 弱   ║
║                  CCL/RCL/DAL/UAL/AAL；DOW/LYB feedstock     ║
║  MACRO   ❌ -2  Brent >$100 → CPI 30-50bp；Fed 6-7 月降息    ║
║                  機率降；breakevens +5-10bp                 ║
║  ARBITER → BINARY，spread=8 + Hormuz binary 48h             ║
╠══════════════════════════════════════════════════════════╣
║  受益：Energy ↑strong  Industrials ↑mod  Materials ↑weak   ║
║  受損：Cons.Disc ↓mod (airlines/cruise/auto)                ║
║  Binary：YES — 觀察 2026-05-02 前 Trump 行動是否實現         ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel ✅  phase0 binary ✅          ║
╚══════════════════════════════════════════════════════════╝
```

**Bull**：Brent 從 $126 回吐是 bull tell — 市場把 Trump 封鎖言論當虛張，CNBC 引述分析師認為 Hormuz 短期不會封鎖。連消費端都正面：Royal Caribbean 明確說 bookings RECOVERING。$110-115 區間的高但穩 Brent 是 Energy 族群盈餘甜蜜點，不破壞消費需求。Defense/oil-services 獲持續順風；煉油受惠 crack spread。『恐慌溢價衰減』本身是可交易 bull thesis。

**Bear**：Brent 摸 $126 不是結束，是開胃菜。Trump『explode this week』言論預先擺好動能事件視窗；任何 Hormuz 事件立刻把 Brent 推到 $140-150（20% 海運原油過此）。即使無升級，risk premium 本身就是 stagflationary shock：每 $10 持續高 Brent = 美國 headline CPI +25bp、全球 GDP -0.2%。扼殺 Fed 反通膨敘事，壓 Consumer Disc，擠壓 transports/chemicals/staples margin。CNBC『不會發生』正是被打臉的 consensus。

**Sector**：上游 E&P（XOM/CVX/COP/OXY/EOG）與油服（SLB/HAL/BKR）強買；LNG/midstream（LNG/ET/KMI）若 Hormuz 阻斷則 reroute 受惠（~20% 全球油 + 25% LNG 過此）。國防主承包商（LMT/RTX/NOC/GD/HII）獲衝突溢價買盤。負面 read：航空 jet-fuel hedges 到期撞 spike；郵輪、卡車、化工原料壓力。煉油混合：crack spread 受惠但需求毀滅風險。

**Macro**：Fed path 鷹派偏向（terminal +2-4bp）；Brent 持續 >$100 歷史 2-3 個月 headline CPI +30-50bp。Curve bear-flattener。歷史類比：2019-09-14 Abqaiq（Brent +14% intraday，週內 +5%、CPI 影響有限）；1990 Iraq-Kuwait（Brent doubled，12 個月內衰退）；2022 Q1 俄烏（Brent $130、CPI 9.1% peak、Fed 75bp）。當前接近 2019 甚於 2022 — 若封鎖未實現。

**Arbiter**：Bull-Bear spread = 8 + 屬真正離散事件（Hormuz 封鎖 within 48h）→ BINARY。Sector vs Macro 差 5 必須說明：Sector 看 Energy/Defense 結構性受惠（+3），Macro 看 stagflation 全市場壓力（-2）— Macro 40% 主導但 Sector 子集受惠是真實 long opportunity，故報告兩面並存。

---

### Impact Card #5 — n0009 [NEUTRAL +0.4]

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP  │  2026-04-30 12:15  │  MODE: DIGEST          ║
╠══════════════════════════════════════════════════════════╣
║  [NEUTRAL +0.4]  MSFT 在 Azure beat + 上修指引下卻下跌        ║
║                  ── Mag-7 capex anxiety canary              ║
║  type: earnings (MEDIUM cred) │ weights: 25/25/40/10        ║
╠══════════════════════════════════════════════════════════╣
║  BULL    ✅ +3  buy-the-dip 教科書，AI workload 變現加速     ║
║  BEAR    ❌ -3  Mag-7 估值 regime 改變，capex/ROIC 重審        ║
║  SECTOR  ➕ +1  Semis 鎬鏟受惠（NVDA/AVGO/AMD/ANET/VRT）；   ║
║                 軟體 margin 承壓（CRM/NOW/ORCL）             ║
║  MACRO   ➖  0  個股事件，無 macro 蔓延                      ║
║  ARBITER → NEUTRAL，採 Sector intra-rotation 解讀            ║
╠══════════════════════════════════════════════════════════╣
║  受益：Semiconductors_AI ↑mod  Utilities ↑weak              ║
║  受損：Technology ↓weak（軟體 margin compression）           ║
║  Binary：No                                                ║
╠══════════════════════════════════════════════════════════╣
║  Cache Updated:  sector_intel ✅  phase0 ✅                 ║
║  ⚠️ MEDIUM credibility — confidence ≤ 0.7                   ║
╚══════════════════════════════════════════════════════════╝
```

**Bull**：MSFT 因 capex 焦慮下跌是教科書級的 buy-the-dip，不是 thesis 破裂。Azure beat + 上修指引才是真正重要的數字。Capex『concern』是每個週期重複的 bear narrative（cf. AMZN AWS 2014-2016、GOOG 2017）。GOOG/AMZN 漲、MSFT/META 跌的事實告訴你市場在分化、不是對 AI capitulation。Mag-7 dispersion 是『健康』的，殺『all-or-nothing』尾風險。

**Bear**：MSFT 在 beat-and-raise 後下跌是 canary。市場終於誠實 price 此 trade-off：Azure 成長需要愈大 GPU 與 datacenter 開支，下一個 $50B 的 marginal ROIC 可疑低於資金成本。Mag-7 反應分化本身就 bearish — 投資人不再給予『AI exposure』通用 multiple。META Reality Labs 先例顯示 capex 超出耐心會發生什麼。再疊加 yen unwind 與 oil shock，Mag-7 capex 幻滅是今天 bear stool 的第三條腿。

**Sector**：Mag-7 split 為純粹 intra-Tech rotation。鎬鏟鏈（NVDA/AVGO/AMD GPU、ARM/MRVL/ALAB networking、ANET/CSCO/CIEN switches、VRT/ETN power、GEV/CEG 發電）受惠；mega-cap 軟體折舊壓力上升（CRM/NOW/ORCL margin watch）。確認 hyperscaler capex 主軸（已被 GOOG n0020 驗證）；增量資訊在於 Tech 內部 margin-pressure rotation 訊號。

**Macro**：Fed path 中性；單一個股 capex 焦慮不改 Fed reaction function。曲線：單獨可忽略；若延伸成 Mag-7 broader sell-off（>5%）才出現 -2 ~ -3bp 2y 反應。歷史類比：2022-04 META capex-anxiety drop 個股 -25%、Fed 無反應、利率 noise level；2024 Q3 同模式。

**Arbiter**：Bull-Bear spread = 6 但屬正常的 capex/AI 估值辯論，非離散事件，未升級 BINARY。MEDIUM credibility 已將四方 confidence 上限至 0.7。Sector +1 反映 intra-Tech rotation：semis 受惠、軟體承壓相互抵消。Sector vs Macro 差 1 無分歧。

---

## 3. SHALLOW DIGEST — Top 20

### [+3.0] n0079  Google Stock Pops On Q1 Earnings As Analysts Trumpet 'Full Stack' AI Platform
- **Bull**: TPU+Gemini+GCP 整合敘事獲市場確認，AI 變現可見度提升
- **Bear**: 估值已先反映，後續看 capex/FCF 是否壓 multiple
- **Sector**: Communication+Tech+Semis 全面受惠（與 n0020 互相印證）
- **Macro**: productivity 敘事支撐，Fed 路徑中性偏鴿
- Source: Yahoo Finance HIGH │ type: earnings
---
### [-3.0] n0193  GE HealthCare Just Crashed 13% on a Guidance Cut. Here's the Case for Buying the Dip
- **Bull**: $59 vs PT $89，極度低估打開 mid-term 價值入場
- **Bear**: guidance cut 顯示醫療設備需求疲軟，恐二度下修
- **Sector**: Healthcare equip 拖累，PHG/SYK/MDT 連帶承壓
- **Macro**: 對 Fed 無感，但確認非 GLP-1 醫療 capex 走弱
- Source: 24/7 Wall Street HIGH │ type: earnings
---
### [-2.5] n0085  Shares of Jeep maker Stellantis fall as much as 10% after first-quarter results
- **Bull**: 已 beat 共識的 €960M operating income 提供下檔支撐
- **Bear**: 需求疲軟+關稅疑慮+ guidance 不明，賣壓恐延燒至 F/GM
- **Sector**: Auto OEM 全線承壓，Auto Parts (APTV/MGA) 連帶
- **Macro**: Consumer Discretionary cyclical 需求邊際走弱
- Source: CNBC HIGH │ type: earnings
---
### [+2.5] n0016  Caterpillar forecasts higher annual revenue as power equipment benefits from AI buildout
- **Bull**: 與 Alphabet capex 敘事直接接軌，CAT 電力產品線水位確認
- **Bear**: Heavy machinery 仍受美中關稅與 mining capex 不確定影響
- **Sector**: Industrials (CAT/ETN/EMR/HUBB)、Power (GEV) 受惠
- **Macro**: non-residential 投資加速，支撐 GDP capex 子項
- Source: Investing.com MEDIUM │ type: earnings
---
### [+2.5] n0076  Chip Gear Firm Entegris Tops Targets On AI-Fueled Demand
- **Bull**: AI 製程化學品/濾材剛性需求，與 ASML/AMAT 同步利多
- **Bear**: 晶圓設備傳統 cyclical，KLAC/AMAT guidance 仍待驗證
- **Sector**: Semi-equip 全線（ENTG/AMAT/LRCX/KLAC/ASML）受惠
- **Macro**: AI infra capex 周期確認，無明顯 Fed 路徑變化
- Source: Yahoo Finance HIGH │ type: earnings
---
### [+2.5] n0056  UBS Q1 2026 profit soars 80% on broad-based growth
- **Bull**: Wealth+IB 全面 beat，股價 +5%，歐銀板塊風向偏多
- **Bear**: Credit Suisse 整合紅利可能 1-2 季內 fading
- **Sector**: Financials (UBS/CS/DBK/MS/GS) 受惠
- **Macro**: 全球資產規模成長，Fed 路徑無直接影響
- Source: Yahoo Finance HIGH │ type: earnings
---
### [+2.0] n0188  Meta says its business AI now facilitates 10 million conversations a week
- **Bull**: AI 商業變現 4 個月 10x，廣告 CTR 與單價齊升
- **Bear**: META 同時被 capex 焦慮拖累，Reality Labs 燒錢未停
- **Sector**: Communication / Tech 雙利多，但 Mag-7 內部分化
- **Macro**: AI productivity 敘事補強，無直接 Fed 衝擊
- Source: TechCrunch HIGH │ type: corporate
---
### [+2.0] n0164  Meta Platforms Trades At The Lowest Multiple Among Mag 7 Stocks
- **Bull**: 33% YoY 營收 + EPS beat，FCF 仍強，逢低相對 Mag-7 機會
- **Bear**: capex 上修引發 sell-off，市場對 memory/infra 投入仍懷疑
- **Sector**: Communication 估值修正，鏡映 GOOGL/MSFT 內部分化
- **Macro**: 個股 valuation 故事，無 Fed 牽動
- Source: Seeking Alpha HIGH │ type: earnings
---
### [+2.0] n0017  Eli Lilly lifts annual forecasts, spotlight on new oral obesity pill
- **Bull**: 與 n0049 相印，pipeline+執行力雙背書
- **Bear**: 已大漲後追價風險升，IRA/Medicare 仍是中期變數
- **Sector**: Healthcare 個股強，板塊整體仍 cold
- **Macro**: 對 Fed 中性
- Source: Investing.com MEDIUM │ type: earnings
---
### [+2.0] n0111  Lilly is now selling $12.9 billion of GLP-1 drugs every three months and expects to sell even more
- **Bull**: tirzepatide 量價齊揚，GLP-1 TAM 持續上修
- **Bear**: 高基期效應 2H 將檢驗，PBM 議價壓力升
- **Sector**: GLP-1 供應鏈（CTLT/TMO/DHR/WST/BDX）受惠
- **Macro**: PCE 健康支出貢獻，但對 Fed 過細
- Source: MarketWatch HIGH │ type: earnings
---
### [+1.5] n0029  US railroads seek approval for $85 billion merger
- **Bull**: UNP/NSC 合併創北美第一鐵路，營運綜效 +30%
- **Bear**: STB 反壟斷審批漫長，貨運客戶反對聲浪
- **Sector**: Transports (UNP/NSC/CSX) 重新定價
- **Macro**: 對 Fed 中性，但長期 supply-chain 效率提升
- Source: Investing.com MEDIUM │ type: corporate
---
### [+1.5] n0073  Royal Caribbean says people booking cruises aren't so worried about Iran anymore
- **Bull**: 消費韌性訊號，cruise demand 回到 YoY 之上
- **Bear**: 若 Iran 再升級 30 天內可能再翻轉
- **Sector**: Cruise (RCL/CCL/NCLH)、Travel (BKNG/EXPE) 受惠
- **Macro**: 對 Fed 中性，但 leisure 需求 resilient 確認
- Source: MarketWatch HIGH │ type: sentiment
---
### [+1.5] n0185  Why the 60/40 portfolio is crushing it — despite market chaos and inflation fears
- **Bull**: 風險平衡組合再被驗證，long-duration 配置觀念回歸
- **Bear**: 若油 + 利率同時上行則 60/40 失效
- **Sector**: 對個股無直接，整體 Treasuries duration 偏多
- **Macro**: 通膨預期錨定 → Fed 緩和路徑可信
- Source: MarketWatch HIGH │ type: sentiment
---
### [+1.5] n0192  Cardinal Health Rises. A Guidance Hike Powers the Stock Past These Weak Points.
- **Bull**: FY 指引第二度上修，特殊藥品需求穩定
- **Bear**: 已包含 GLP-1 配送紅利，後續成長率將正常化
- **Sector**: Healthcare distribution (CAH/MCK/COR) 受惠
- **Macro**: 對 Fed 中性
- Source: Barrons HIGH │ type: earnings
---
### [-1.5] n0001  Trump said his blockade would cause Iran's oil industry to 'explode' this week. Why that won't happen
- **Bull**: 文章本身偏分析者認為短期不會發生 → bear trap
- **Bear**: Trump 言論預先設下動能視窗，binary 升級風險
- **Sector**: Energy 仍受惠 risk premium，Defense 上行
- **Macro**: Fed 路徑面臨 stagflation 壓力（與 n0088 同源）
- Source: CNBC HIGH │ type: geopolitical
---
### [-1.0] n0154  U.S. weighs 'reduction' of troops in Germany as Trump's feud with Berlin deepens
- **Bull**: 撤軍可釋放預算回國防 R&D
- **Bear**: NATO 信任受損，歐洲國防自主提速 → US prime 訂單可能下降
- **Sector**: Defense (LMT/RTX/NOC) 中性偏負；歐洲 (BAE/Rheinmetall) 利多
- **Macro**: 對 Fed 無直接，但歐美關係再 stress
- Source: CNBC HIGH │ type: geopolitical
---
### [+1.0] n0158  Nvidia just invested in the AI legal startup that's splashing Jude Law ads everywhere
- **Bull**: NVDA 持續擴張生態系投資，戰略意涵超過財務
- **Bear**: $5.6B 估值偏高，AI legal 商業模式仍未驗證
- **Sector**: Tech 生態系 / SaaS 邊際正面
- **Macro**: 微觀，無 macro 衝擊
- Source: CNBC HIGH │ type: corporate
---
### [-0.5] n0030  Bank of England keeps rates on hold at 3.75% as Iran war shakes outlook
- **Bull**: 央行不恐慌升息 = 風險資產利多
- **Bear**: Iran war 帶來經濟前景大不確定性，BoE 後續可能 dovish
- **Sector**: UK Financials (LYG/BARC/HSBC) 中性
- **Macro**: G7 央行 hold 共識成形，Fed 路徑被動 dovish
- Source: CNBC HIGH │ type: monetary_policy
---
### [-0.5] n0011  Mastercard Q1 earnings top consensus, but April trend shows slowdown in cross-border activity
- **Bull**: Q1 beat 主數仍強健
- **Bear**: 4 月 cross-border 放緩 = travel/discretionary 邊際走弱
- **Sector**: Payments (MA/V/AXP) 邊際逆風；Travel 連帶
- **Macro**: 消費邊際走弱，Fed 鴿派證據加一
- Source: Seeking Alpha MEDIUM │ type: earnings
---
### [+0.5] n0003  ECB holds interest rates steady
- **Bull**: 政策可預測，EUR 穩定，歐銀利多
- **Bear**: 內生通膨升溫風險未解除
- **Sector**: 歐洲 Financials 中性
- **Macro**: G7 央行同步 hold，Fed 路徑 dovish
- Source: Seeking Alpha MEDIUM │ type: monetary_policy
---

---

## 4. CACHE PATCH SUMMARY

| 檔案 | 動作 | 細節 |
|---|---|---|
| `sector/sector_logs/2026-04-30_sector_intel.json` | **prepend top_catalysts × 5** | 加入 5 則今日 deep verdicts，舊 catalysts 保留 |
| `sector/sector_logs/phase0.json` | **macro_backdrop_score += -0.35** | 並 append 2 筆 binary_risks（Yen carry / Hormuz） |

---

## 5. KEY TAKEAWAYS

1. **AI infra capex super-cycle 仍 intact**：GOOGL $190B、CAT 電力線、ENTG AI 化學品、META biz-AI 變現 — Bull rotation 集中在 Semis_AI / Power / Industrials / Networking。
2. **Mag-7 反應分化是 healthy 但 capex anxiety 是 canary**：MSFT/META 跌 vs GOOG/AMZN 漲；下次 NVDA earnings (FY27 guide) 將是 capex/ROIC 終極檢驗。
3. **兩個 binary 並存 within 48h**：Yen carry-unwind（市場壓力）與 Hormuz/Iran（油供給）— session_macro_delta 落 -0.35 主要來自此。動態：若任一升級則建議部位降至 sector_intel ceiling 60-70%；若兩者均 fade 則 risk-on 重啟。
4. **Healthcare 仍 cold 但 LLY/CDMO 個股 alpha**：LLY GLP-1 dominance 擴大但全 sector 無 lift；對 Consumer_Staples（snacks/QSR）長期負面。
5. **下一個觀察點**：明日（5/1）Apple/Amazon 財報 + 日股 / USDJPY 開盤反應 + Trump 是否在週末前對 Iran 採取行動。

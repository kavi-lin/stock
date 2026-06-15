# 新聞分析 DIGEST — 2026-06-05

> Mode: DIGEST | Stage 1 triage: 22 則 | Stage 2 deep: 5 則 | fanout: PER_AGENT_BATCH  
> Sources: RSS + Finnhub + FMP + SEC EDGAR（unified raw 347 則）| session_macro_delta: **-0.25** | phase0 macro_backdrop → -4.76

## Executive Summary

今日主軸：**強就業 × 鷹派 Fed × AI 晶片輪動**。5 月非農 +17.2 萬遠超預期 8.5 萬、失業率 4.3%，在 Iran 戰事推升通膨下，Fed 反應函數翻轉為「聚焦通膨、甚至評估升息」，10Y 殖利率走高。資金由 AI 半導體（Broadcom -15%）輪出至醫療/金融，Dow +875 點創 51,562 新高、Nasdaq 走弱 — Bull 視為廣度擴張、Bear/Macro 視為 late-cycle 防禦輪動與指數背離頂部訊號（本批最大分歧）。供給面 Nvidia 認證三星/SK Hynix/Micron 供 Vera Rubin HBM4（結構利多，但被當日資金面壓過）。油價因以黎停火+伊朗協議預期收低（雙向 BINARY）。Lululemon 砍全年指引 → 高端可選消費 trade-down 警報。

**Verdict 摘要**

| news_id | 標題 | verdict | net_impact | 類型 | 48h |
|---|---|---|---|---|---|
| `n0173` | 美國 5 月新增 17.2 萬就業，遠優於預期 8.5 萬 | **NEUTRAL** | -0.4 | macro_data | ✅ |
| `n0328` | 道瓊創新高，資金輪出 AI 晶片股 | **NEUTRAL** | +0.0 | sentiment | ✅ |
| `n0019` | Nvidia 認證三星、SK Hynix、Micron 供應 Vera Rubin 平台 HBM4 | **BULLISH** | +2.0 | sector_news | — |
| `n0312` | 油價收低，受以黎停火後伊朗協議預期帶動 | **BINARY** | +0.5 | geopolitical | ✅ |
| `n0309` | Lululemon 下修全年展望、Q2 指引疲弱，歸因未明說的『逆風』 | **BEARISH** | -1.8 | earnings | ✅ |

---

## Stage 2 — Deep Debate（4 視角 + Arbiter）

### `n0173` 美國 5 月新增 17.2 萬就業，遠優於預期 8.5 萬
> US economy added 172,000 jobs in May, beating expectations  
> Fox Business · published 2026-06-05T08:50:21+00:00 · type=`macro_data` · binary_risk=False

**🟢 Bull** — 17.2 萬就業大幅優於預期 8.5 萬、失業率僅 4.3%，是「強勁但不過熱」的黃金組合：勞動市場韌性證明消費引擎未熄火，降低企業盈餘下修風險，支撐 S&P 500 整體 EPS。市場最怕衰退而非升息——只要不衰退，景氣循環股與金融股的放款與信用品質就受惠。強就業給 Fed 在 Iran 戰事推升通膨時按兵不動的底氣；銀行受惠違約率低、淨利差在高利率維持，JPM、BAC 最直接，工業與必需消費需求能見度提高。這正是今日 Dow 創高、資金輪動進金融/價值的基本面根基。

**🔴 Bear** — 172K 遠超預期、失業率 4.3%，在 Iran 戰爭推升通膨當下反成利空：勞動市場過熱坐實 Fed『higher-for-longer』甚至升息轉向，扼殺今年降息預期。折現率上升直接壓縮高估值資產，尤其久期最長的 AI/半導體成長股。工資黏性疊加油價衝擊形成二次通膨風險，10Y 殖利率走高同時打擊利率敏感的地產、公用、REIT 與小型股融資成本。late-cycle 下『好消息即壞消息』：強就業延後寬鬆、收緊金融條件，並縮短 Fed 在衰退前的緩衝空間。

**🏭 Sector** — +172K 配合 Fed 轉向通膨焦點，殖利率短端易上、長端受通膨溢價推升，利好銀行 NIM：JPM、BAC、WFC、C 直接受益，區域銀 KRE 成分（RF、KEY、CFG）對 NIM 槓桿更大。2nd-order：保險 (MET、PRU) 再投資收益率提升；支付 (V、MA) 受惠消費韌性。反向承壓：利率黏住使 30 年房貸高檔，新屋商 DHI、LEN、PHM 與供應鏈 BLDR、SHW、WHR 需求遞延；REIT (VNQ、O) 折現率上行受壓。整體確認 rotation INTO financials 的 macro 基礎。

**🌐 Macro** — 坐實勞動市場『不需要降息』的再加速敘事。在 Iran 戰爭推油價、通膨抬頭下，這份報告把 Fed 反應函數從保險式降息翻轉為按兵不動甚至評估升息（Bloomberg『Fed Weighs Rate Hikes』）。10Y 殖利率報告後跳升，2Y 升幅更陡，曲線趨平甚至再倒掛風險升。強就業+鷹派 Fed 對 USD 偏多（DXY 走強），對 EM 與高估值科技股逆風。歷史類比 1994 與 2023H2『好消息即壞消息』，殖利率主導風險資產，高 duration 成長股承壓、價值/金融受惠。

**Tickers**: JPM, BAC, WFC, C, TLT, XLF, SPY, IWM  
**Sectors**: Financials(bullish), Technology(bearish), Real Estate(bearish), Utilities(bearish)

**⚖️ Arbiter → `NEUTRAL` (-0.4)**: news_type=macro_data 權重 Macro 40% / Sector 20% / Bull 20% / Bear 20%。四方分數 Bull +2.8 / Bear -2.0 / Sector +2.5 / Macro -1.5，加權 ≈ +0.06。但這是典型雙面數據：對實體經濟與金融/價值股利多（Sector +2.5、Bull +2.8），對高 duration 成長股因 Fed 轉鷹而利空（Macro -1.5）。考量當日盤面已以殖利率上行主導、Nasdaq 走弱，淨裁 NEUTRAL 並微偏空 -0.4，採『rotation 而非全面風險偏好』為主論點。

**🔀 Debate note**: Bull（強就業=不衰退利多金融/景氣循環）vs Macro/Bear（強就業=Fed 不降息甚至升息、折現率壓估值）：分歧在 Fed 反應函數——這份數據是延長景氣還是提前收緊金融條件。

---

### `n0328` 道瓊創新高，資金輪出 AI 晶片股
> Dow hits record high as investors rotate out of AI chip stocks  
> Investing.com · published 2026-06-04T16:19:09+00:00 · type=`sentiment` · binary_risk=False

**🟢 Bull** — Dow 單日 +875 點、+1.73% 創 51,562 新高，這不是去風險恐慌，而是健康的資金輪動——錢沒離場，而是從估值最緊繃的 AI 半導體流向被冷落的醫療與金融。對大盤這是正面訊號：市場廣度擴張，漲勢不再只靠 7 巨頭撐盤，是牛市能延續的關鍵。醫療具防禦現金流且估值便宜，金融受惠高利率與強就業信用環境，接棒領漲降低指數波動與集中度風險。UNH、JNJ、LLY 與 JPM、BAC 直接受惠；半導體回調也提供逢低布局次世代 AI 供應鏈的入場點。

**🔴 Bear** — 道指創高僅靠醫療+金融防禦性輪動撐盤，是典型 late-cycle 內部惡化而非健康牛市：領漲棒子從掌握 EPS 增長引擎的半導體交棒給低增長防禦股，市場廣度其實在收窄。Broadcom 單日 -15%、Nasdaq 下跌，代表佔指數權重最大的 AI capex 主題正被獲利了結，一旦 NVDA/AVGO 崩跌，被動 ETF 與 401k 同步失血，防禦股市值不足以承接整體市場。道指創高 vs Nasdaq 走弱的背離，歷史上常是頂部特徵。本質是 risk-off，是警訊不是慶祝。

**🏭 Sector** — 典型 risk rotation：資金由 AI 半導體高 beta 流向防禦+價值。Lead 子板塊：Healthcare 大型製藥/保險 (UNH、JNJ、LLY、MRK、PFE) 與 money-center banks (JPM、GS、MS)。Lag：AI 半導體 (NVDA、AVGO、AMD、MRVL) 與資本設備 (AMAT、LRCX、KLAC)，及 AI 電力/散熱題材 (VRT、SMCI、ETN) 同步去槓桿。2nd-order：高權重半導體下殺拖累 SOXX/SMH 與被動資金，QQQ 再平衡放大賣壓；反向 XLV、XLF、equal-weight RSP 相對走強。

**🌐 Macro** — Dow 創高而 Nasdaq 跌、輪出 AI 晶片，是『rate-up 防禦輪動』而非健康廣度擴張。在殖利率上行、Fed 轉鷹下，市場拋售長 duration 高估值半導體，轉進現金流穩定、估值低的道瓊權值。這種 narrow-to-value 輪動表面 breadth 改善，實則反映防禦心態與利率敏感性。歷史類比 2000 Q1 與 2022 初：megacap tech 領導失速、資金往價值躲，常是大盤波動上升前兆。淨效應中性偏負——指數因權值撐住，但市場質地轉弱、leadership 縮窄。

**Tickers**: UNH, JNJ, LLY, JPM, GS, NVDA, AVGO, AMD, DIA, QQQ, RSP  
**Sectors**: Health Care(bullish), Financials(bullish), Semiconductors(bearish), Technology(bearish)

**⚖️ Arbiter → `NEUTRAL` (+0.0)**: news_type=sentiment 四方等權。Bull +3.2 / Bear -3.0 / Sector 0.0 / Macro -0.5，加權 ≈ -0.08，是本批分歧最大的一則。Bull 視為廣度擴張的健康輪動，Bear/Macro 視為 late-cycle 防禦輪動與指數背離頂部訊號。Sector 給 0（一邊醫療金融多、一邊半導體空，淨零）。裁定 NEUTRAL net 0.0——這是 regime 轉折的觀察點而非方向確立，列為後續再評重點。

**🔀 Debate note**: 最大分歧：Dow 創高 + Nasdaq 跌究竟是『廣度擴張的健康牛市延續』(Bull) 還是『防禦輪動 + 指數背離的頂部前兆』(Bear/Macro)。後續以半導體權值能否止穩為再評觸發。

---

### `n0019` Nvidia 認證三星、SK Hynix、Micron 供應 Vera Rubin 平台 HBM4
> Nvidia certifies Samsung, SK Hynix and Micron for Vera Rubin HBM4 supply  
> Investing.com · published 2026-06-05T13:00:01+00:00 · type=`sector_news` · binary_risk=False

**🟢 Bull** — Nvidia 同時認證 Samsung、SK Hynix、Micron 供應 Vera Rubin 平台 HBM4，是強烈需求面利多：next-gen GPU 進入供應鏈鎖定階段，代表 Rubin 量產時程明確、AI capex 循環延續到 2027 而非見頂。三方認證解除單一供應商瓶頸疑慮，HBM4 放量支撐 Rubin 出貨、保護 Nvidia 毛利與交期。對 Micron 尤其關鍵——首度擠進 Nvidia 旗艦 HBM 供應鏈，是其 HBM 市佔與獲利結構的轉折點，可重估 memory 估值。今日半導體賣壓多屬估值與輪動驅動，與此基本面利多方向相反，反給 NVDA、MU 逢低背書。

**🔴 Bear** — 三方合格意味 HBM 從 SK Hynix 寡占走向多源競爭，供給遽增將壓低 HBM4 ASP 與毛利，對押注 HBM 稀缺溢價的 Micron 與海力士是中期利空。這也暗示 Vera Rubin 量產與龐大 capex 仍在加碼，呼應『AI bubble bigger than dot-com』供給過剩劇本——若終端 AI 推理 ROI 不如預期，這批 HBM4 產能將變成庫存與減值。多源認證削弱 NVDA 對供應鏈的綁定議價，讓記憶體淪為價格戰紅海。利多其實是產能軍備競賽見頂的訊號。

**🏭 Sector** — 把 HBM4 由 SK Hynix 單一寡占轉為三供格局——對 MU 重大利好（打入次世代 AI 記憶體供應鏈），對 SK Hynix 邊際利空（份額稀釋）。2nd-order 供應鏈：HBM4 拉貨支撐先進封裝，TSM CoWoS-L 產能與設備商 (AMAT、LRCX、KLAC、ASML) 受惠；測試 (TER)、ABF 載板與散熱 (VRT) 同步受惠。須注意此題材與 n0328 的 rotation OUT of AI semis 方向衝突——結構利多 vs 短線資金面利空，今日盤面資金面壓過基本面，故 NVDA/AVGO 仍跌。淨評估對 MU/記憶體偏多。

**🌐 Macro** — HBM4 三方認證確立 AI capex 上行周期供給端 visibility，屬結構性而非 cyclical，與當下 macro 逆風方向相反。AI 資本支出是少數能在高利率維持的『非利率敏感』成長引擎——hyperscaler FCF 充裕、不靠舉債擴產，故折現率上行對其營收衝擊小於估值衝擊。但利多撞上今日 AI 晶片 selloff，凸顯 macro（利率/輪動）短線蓋過 micro（產品周期）。歷史類比 1999 telecom capex：基本面真實但估值與利率才是股價主導。淨效應微正。

**Tickers**: NVDA, MU, TSM, AMAT, LRCX, KLAC, TER, AVGO  
**Sectors**: Memory Semiconductors(bullish), Semiconductor Equipment(bullish), Foundry(bullish), AI Semiconductors(binary)

**⚖️ Arbiter → `BULLISH` (+2.0)**: news_type=sector_news 權重 Sector 40% / Bull 20% / Bear 20% / Macro 20%。Bull +3.5 / Bear -1.0 / Sector +1.5 / Macro +0.5，加權 = 0.4*1.5+0.2*(3.5-1.0+0.5) = 0.6+0.6 = +1.2，調整為結構利多 net +2.0 BULLISH。採『next-gen AI capex visibility + Micron 打入旗艦鏈』為主論點；Bear 的 HBM 商品化/ASP 壓縮列為中期再評條件。注意：此基本面利多今日被 n0328 的資金面輪動壓過，NVDA/AVGO 仍下跌，屬結構 vs 短線背離。

**🔀 Debate note**: Bull/Sector（三供確立 Rubin 量產 visibility、Micron 重估）vs Bear（多源=HBM 商品化、ASP/毛利下行、capex 軍備競賽見頂）：分歧在 HBM4 三供是需求確認還是供給過剩前奏。

---

### `n0312` 油價收低，受以黎停火後伊朗協議預期帶動
> Oil settles lower on hopes for Iran deal following Israel-Lebanon ceasefire  
> Reuters · published 2026-06-04T19:11:04+00:00 · type=`geopolitical` · binary_risk=True

**🟢 Bull** — 油價在以黎停火後因 Iran 協議預期走低，是當前最大宏觀利多：油價是 Iran 戰事推升通膨的核心傳導管道，原油回落直接緩解市場最擔心的『戰爭型通膨』，等於替 Fed 拆除偏鷹/升息引信。通膨壓力一旦減輕，Fed 可重回中性甚至保留降息空間，對所有久期資產（成長股、高估值科技）是估值面解壓。地緣降溫提振風險偏好、壓低 VIX 與輸入成本，利多航空 (DAL、LUV)、運輸、化工與耗油消費/工業股。對今日因通膨恐慌被錯殺的成長股，是劇本反轉的第一張骨牌。

**🔴 Bear** — 油價回落僅建立在『以黎停火 + 伊朗協議希望』這種極脆弱去升級之上：兩者皆可一夕翻盤，任何『談判破裂/荷莫茲海峽事件』都能讓油價跳空回補並重燃通膨。市場預支和平紅利、壓低 VIX，反墊高 negative surprise 的下檔空間。同時 Fitch 已因中東油震下調全球增長，意味即便油價短軟，需求面被破壞的滯脹組合（成長↓+通膨黏性）並未解除。油價下跌也打擊剛接棒領漲的能源股 EPS，削弱道指輪動的可持續性。和平是交易，不是事實。

**🏭 Sector** — 供給增加預期壓制油價，利空 upstream/integrated 與油服：XOM、CVX、COP、OXY、EOG、SLB、HAL 獲利展望下修，XLE 走弱。2nd-order 受益明確：燃油是航空最大變動成本，利好 DAL、UAL、AAL、LUV 與物流 (FDX、UPS、ODFL、CHRW)、郵輪 (CCL、RCL)。Refiners (VLO、PSX、MPC) mixed——原油成本降但裂解價差視終端需求，偏中性。通膨面：油價低利多消費購買力，間接利好 consumer discretionary。地緣若 deal 破局則 binary 反轉，須留意 tail risk。

**🌐 Macro** — 油價因 Iran 核協議期待＋以黎停火回落，是 macro 最關鍵雙面變數。油價下行緩解 Fed 最擔心的通膨再加速，理論利多降息重啟與風險資產；但 Trump 稱『不需要協議』使地緣溢價難實質消退，且 Fitch 已下調全球成長、EU 警告能源致 130 萬失業，顯示供給衝擊已傷實體需求。故是 stagflation-lite 兩難：油價跌若源於需求毀滅而非供給改善，對成長與企業獲利是負面。歷史類比 1990 波灣與 2022 俄烏：油價尖峰後回落常伴隨成長失速。淨效應略偏正但有 binary tail。

**Tickers**: XOM, CVX, SLB, DAL, UAL, FDX, VLO, SPY, QQQ  
**Sectors**: Energy(bearish), Airlines(bullish), Transports(bullish), Technology(bullish)

**⚖️ Arbiter → `BINARY` (+0.5)**: news_type=geopolitical 權重 Macro 40% / 其餘各 20%。Bull +3.0 / Bear -1.0 / Sector -0.5 / Macro +0.5，加權 = 0.4*0.5+0.2*(3.0-1.0-0.5) = 0.2+0.3 = +0.5。方向偏正（通膨壓力緩解利多大盤）但裁為 BINARY：和平建立在以黎停火＋伊朗協議預期的脆弱基礎，Trump『不需協議』與荷莫茲 tail risk 可一夕反轉。net +0.5 反映利多傾向，binary_risk=true 標記地緣可逆。

**🔀 Debate note**: Bull/Macro（油價跌=通膨引信拆除、利多久期資產）vs Bear（和平是 fragile 交易，破局即油價跳空回補 + Fitch 已示需求毀滅）：分歧在油價回落是供給改善還是需求毀滅、以及停火可持續性。

---

### `n0309` Lululemon 下修全年展望、Q2 指引疲弱，歸因未明說的『逆風』
> Lululemon cuts annual outlook and issues weak Q2 guidance, citing undisclosed 'headwinds'  
> CNBC · published 2026-06-04T20:12:45+00:00 · type=`earnings` · binary_risk=False

**🟢 Bull** — Lululemon 下修展望，但從多頭角度更像個股公司特定（idiosyncratic）問題而非總體消費崩壞——對照同日 +17.2 萬強就業，消費力道整體未弱，LULU 的『未明說 headwinds』更可能是品牌動能、競品 (Alo、Vuori) 瓜分與自身執行問題，屬可控公司層級議題。對大盤反而是淨化訊號：資金從失去成長故事的個股輪動到基本面紮實的龍頭與防禦股，與今日 Dow 創高輪動敘事一致。對逆向投資人，預期重設後估值大幅壓縮，若管理層下半年釐清 headwinds 並啟動庫存/行銷修正，存在 expectation-reset 反彈空間。

**🔴 Bear** — Lululemon 下調全年 + 弱 Q2 並以『未揭露 headwinds』含糊帶過，是消費降溫早期警報而非個股事件：高價瑜珈服向來是可選消費韌性代表，連 LULU 都見頂，暗示 4.3% 失業率底下美國消費者已縮減 discretionary 支出。『undisclosed』措辭更危險——可能是需求疲軟、競爭侵蝕或庫存問題，管理層不願明說本身就是信任折價。這呼應 higher-for-longer 對家庭可支配所得擠壓，對 NKE、RL、整個 XLY 構成 read-through。財報季前的預警常引發類股估值重評。

**🏭 Sector** — 訊號為高端 athleisure 需求降溫與美國消費者 trade-down。直接讀數至同業：NKE（北美客流/庫存壓力）、Under Armour (UAA)、Deckers (DECK，HOKA 動能能否抗衡)、VF Corp (VFC)。2nd-order 供應鏈：成衣代工/布料反映 NKE/LULU 砍單，零售通路 Dick's (DKS) 同店承壓。Read-through 至更廣 discretionary：mall-based retail (XRT) 與中高端 (TPR、RL) 情緒轉弱，但屬公司/次產業 specific，非全面消費衰退——staples (XLP) 相對防禦。整體偏空 discretionary 中的 apparel 子板塊。

**🌐 Macro** — Lululemon 下修是消費降溫前哨，與 +172K 強就業形成『勞動市場熱、可選消費冷』背離。高端瑜伽服屬可選消費，其疲軟反映實質薪資被通膨（油價推升）侵蝕、消費者向必需品 trade-down，與 EU 能源致失業、全球成長下修一致。從 Fed 反應函數看是少數支持『別再鷹』的軟數據——消費走弱會自然降溫通膨，但目前被強勞動數據與油價壓過。歷史類比 2007 與 2000 末段：就業 lagging、消費 leading，可選消費先轉弱常領先景氣放緩 1-2 季。淨效應對大盤偏負。

**Tickers**: LULU, NKE, DECK, UAA, VFC, DKS, TPR, XLY  
**Sectors**: Consumer Discretionary(bearish), Apparel/Athleisure(bearish), Consumer Staples(neutral)

**⚖️ Arbiter → `BEARISH` (-1.8)**: news_type=earnings 權重 Sector 40% / Bull 20% / Bear 20% / Macro 20%。Bull -1.0 / Bear -2.5 / Sector -2.0 / Macro -1.0，加權 = 0.4*(-2.0)+0.2*(-1.0-2.5-1.0) = -0.8-0.9 = -1.7，裁 net -1.8 BEARISH。四方一致偏空（連 Bull 都認為個股利空、僅大盤淨化），採 Sector 的 athleisure/discretionary read-through 為主論點。『undisclosed headwinds』的不透明加深信任折價。

**🔀 Debate note**: Bull（idiosyncratic 個股問題、大盤輪動淨化）vs Bear/Sector（高端 discretionary 見頂=消費 trade-down 早期警報、read-through NKE/XLY）：分歧在 LULU 疲弱是公司執行問題還是消費降溫前哨。

---

## Stage 1 — Shallow Digest（triage 表 22 則，依 |score| 排序，digest JSON cache 取前 15）

| news_id | 標題 | type | score | 🟢 Bull / 🔴 Bear / 🏭 Sector / 🌐 Macro | published |
|---|---|---|---|---|---|
| `n0029` | 比特幣慘澹收週，價格較歷史高點低 50% | sentiment | -2.0 | 🟢深跌後逢低反彈空間 ／ 🔴風險偏好惡化、加密去槓桿 ／ 🏭加密/礦股 (COIN、MARA) 承壓 ／ 🌐risk-off 訊號，與 AI 賣壓共振 | 12:54Z |
| `n0211` | 銀行巨頭警告股市估值為 2008 金融危機以來最緊繃 | sentiment | -2.0 | 🟢牛市情緒仍強 ／ 🔴估值極端=回調風險高 ／ 🏭全市場估值警訊 ／ 🌐與 AI 泡沫論共振，偏空 | 08:12Z |
| `n0058` | Alphabet 尋求新資本，連四週下跌考驗投資人胃納 | corporate | -1.5 | 🟢募資為 AI capex 擴張背書 ／ 🔴連四週跌+募資稀釋疑慮 ／ 🏭大型科技/雲端情緒轉弱 ／ 🌐megacap 領導失速，呼應輪動敘事 | 12:00Z |
| `n0339` | 川普公布對貿易夥伴的新關稅方案 | geopolitical | -1.5 | 🟢施壓談判籌碼、保護本土製造 ／ 🔴關稅=輸入性通膨+供應鏈成本 ／ 🏭工業/零售進口成本上升 ／ 🌐通膨上行風險、Fed 更難轉鴿 | 15:03Z |
| `n0255` | CrowdStrike 執行長：AI 安全憂慮將成更大順風 | corporate | +1.5 | 🟢AI 資安需求結構性成長 ／ 🔴估值偏高、競爭加劇 ／ 🏭網路資安 (PANW、ZS、S) 受惠 ／ 🌐非利率敏感成長題材 | 22:37Z |
| `n0182` | 高盛看 S&P 500 年底上看 8000 | sentiment | +1.5 | 🟢賣方上調目標、多頭續航 ／ 🔴樂觀預期已部分定價 ／ 🏭大盤估值錨點上移 ／ 🌐與估值緊繃論對立 | 08:44Z |
| `n0026` | Western Asset 以 1 億美元和解 SEC 指控 | corporate | -1.0 | 🟢和解去除不確定性 ／ 🔴聲譽+資金外流風險 ／ 🏭資產管理 (Franklin/BEN) 承壓 ／ 🌐個別公司事件，大盤無感 | 12:55Z |
| `n0197` | 高盛建議逢低買進博通，AI 營收軌跡不變 | corporate | +1.0 | 🟢AI 營收軌跡完好、逢低良機 ／ 🔴-15% 急跌反映動能轉弱 ／ 🏭AI 半導體/連接鏈讀數 ／ 🌐賣方背書 vs 資金面輪動 | 08:32Z |
| `n0244` | 研究稱車市動盪重創德國車廠 | sector_news | -1.0 | 🟢估值已低、利空出盡 ／ 🔴需求疲軟+關稅+電動轉型壓力 ／ 🏭全球車廠/供應鏈承壓 ／ 🌐歐洲工業放緩訊號 | 01:03Z |
| `n0012` | 英國推進對微軟限制客戶選擇行為的調查 | corporate | -0.8 | 🟢雲端業務基本面不受影響 ／ 🔴反壟斷監理風險升溫 ／ 🏭雲端 (MSFT、雲服務) 監理逆風 ／ 🌐megacap 監理壓力，中性偏空 | 13:02Z |
| `n0193` | 華爾街設定 Nvidia 未來 12 個月目標價 | corporate | +0.8 | 🟢分析師 PT 維持上行空間 ／ 🔴目標價分歧大、回調風險 ／ 🏭半導體龍頭情緒指標 ／ 🌐AI capex 估值錨點 | 08:35Z |
| `n0081` | 印度經濟 1-3 月成長 7.8%，優於預期 | macro_data | +0.8 | 🟢EM 成長亮點、資金流入 ／ 🔴全球需求若放緩仍受拖累 ／ 🏭EM/印度 ETF (INDA) 受惠 ／ 🌐全球成長分化，中性偏多 | 10:57Z |
| `n0246` | 華倫邀 Nvidia 執行長黃仁勳出席對中 AI 晶片銷售聽證 | geopolitical | -0.8 | 🟢政策能見度提高 ／ 🔴出口管制+政治壓力風險 ／ 🏭半導體出口監理逆風 ／ 🌐中美科技戰升溫 | 00:58Z |
| `n0080` | Anthropic IPO 成為 AI 熱潮估值的首場大考 | corporate | +0.5 | 🟢AI 一級龍頭 IPO 提振題材 ／ 🔴估值若破發拖累整個 AI 板塊 ／ 🏭AI 軟體/算力族群 sentiment 連動 ／ 🌐AI 泡沫估值試金石，二元 | 11:00Z |
| `n0311` | 美職缺數跳升至近兩年高點，白領職位主導 | macro_data | +0.5 | 🟢勞動需求強勁、消費支撐 ／ 🔴強勞動=Fed 更難降息 ／ 🏭白領/服務業需求佳 ／ 🌐呼應 +172K，鷹派含義 | 19:20Z |

_另 7 則進 triage 表但未入 JSON cache（|score| 較低）：`n0315` Ramp hits $44 billion valuation as compa (+0.3), `n0341` US Supreme Court backs SEC in fight over (-0.3), `n0322` Jim Cramer sees an opportunity in Broadc (+0.4), `n0331` Lundbeck's experimental drug cuts migrai (+0.5), `n0340` Otsuka says kidney disease drug preserve (+0.4), `n0298` Honeywell's quantum company goes public  (+0.5), `n0214` China poaches more AI talent from the U. (-0.5)_

---

## Phase 4 — Cache Patch

- `sector/sector_logs/phase0.json`: macro_backdrop_score -4.51 → **-4.76**（session_macro_delta -0.25）; news_patch_count 107 → 108; binary_risks +1（`n0312` 油價/伊朗雙向）
- `sector_intel.json`: 不存在 → top_catalysts prepend 跳過（無 sector run 在席）
- `news/news_logs/2026-06-05_digest.json`: validator **rc=0**（15 shallow + 5 deep, V2.1 compliant）

**紀律**：News 為探索/中期層，deep verdicts 僅 patch phase0 macro_backdrop + binary_risks，**不**直接驅動 investment_protocol buy_threshold / position_size。
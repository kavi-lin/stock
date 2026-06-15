# News Digest — 2026-06-10

> Mode: DIGEST │ Stage 1: 402 raw → 25 triaged │ Stage 2: 5 deep (PER_AGENT_BATCH, 4 isolated subagents) │ session_macro_delta: -0.7
> Validator: ✓ V2.1 rc=0 │ Cache patched: sector_intel.json ✅ phase0.json ✅ (macro_backdrop -4.76 → -4.90)

---

## 1. Triage Summary

```
╔════════════════════════════════════════════════════════════════════════╗
║  NEWS TRIAGE  │  2026-06-10 22:40  │  402 則 → 25 評分 → 5 晉級          ║
╠════════════════════════════════════════════════════════════════════════╣
║  ✅ DEEP   n0271  [-4.5]  US May CPI 4.2% 三年新高連三升      macro_data ║
║  ✅ DEEP   n0064  [-4.2]  [BINARY] 美伊停火破裂再空襲       geopolitical ║
║  ✅ DEEP   n0129  [-3.8]  金銀比特幣齊跌 升息押注上調    monetary_policy ║
║  ✅ DEEP   n0047  [-3.4]  SMCI $7B 融資暴跌13%                corporate ║
║  ✅ DEEP   n0106  [-3.3]  油價跳漲 EIA庫存警告             geopolitical ║
║  ────────────────────────────────────────────────────────────────────  ║
║  ❌ SKIP   n0402  [-2.9]  AI 股恢復拋售                       sentiment ║
║  ❌ SKIP   n0219  [-2.8]  Warsh 遭熱通膨+強就業夾擊     monetary_policy ║
║  ❌ SKIP   n0211  [+2.5]  Meta 印度 AI 資料中心               corporate ║
║  ❌ SKIP   n0031  [-2.4]  亞馬遜卡車擴張 貨運股殺           sector_news ║
║  ❌ SKIP   n0300  [-2.2]  中國 PPI 四年高點                  macro_data ║
║  ❌ SKIP   n0272  [-2.2]  德國衰退警告 (DIW)                 macro_data ║
║  ❌ SKIP   n0399  [-2.0]  BTC 財庫蒸發 $62B                   sentiment ║
║  ❌ SKIP   n0041  [-1.8]  巴菲特指標 screaming sell           sentiment ║
║  ❌ SKIP   n0003  [+1.8]  [BINARY] ORCL 今晚財報               earnings ║
║  ❌ SKIP   n0044  [-1.7]  Barclays 槓桿 ETF 警告              sentiment ║
║  ❌ SKIP   n0366  [+1.6]  SpaceX IPO 定價出爐                 corporate ║
║  ❌ SKIP   n0245  [+1.5]  MU AI 記憶體 +232% YTD              corporate ║
║  ❌ SKIP   n0396  [-1.3]  AAPL Siri AI 賣事實                 corporate ║
║  ❌ SKIP   n0014  [+1.2]  BWA 獲 UBS 升評 DC 電力             corporate ║
║  ❌ SKIP   n0127  [+1.2]  房貸需求單週 +11%                  macro_data ║
║  ❌ SKIP   n0288  [-1.2]  北京 AI 間諜升級 (CRWD)          geopolitical ║
║  ❌ SKIP   n0038  [+1.0]  CBRL 軋空 +30%                       earnings ║
║  ❌ SKIP   n0039  [-0.8]  DJT 取消 Truth Social 分拆          corporate ║
║  ❌ SKIP   n0212  [+0.3]  BoC 按兵不動 2.25%            monetary_policy ║
║  ❌ SKIP   n0368  [+0.2]  Fed 壓力測試 6/24             monetary_policy ║
╚════════════════════════════════════════════════════════════════════════╝
```

**今日敘事主軸**：CPI 4.2%（能源驅動、連三月加速）× 美伊停火破裂 × 升息定價 — 三者形成自我強化迴圈。AI capex 融資疲勞（SMCI）為獨立第二主軸。全日 25 則中 17 則偏空，session_macro_delta -0.7。

---

## 2. Deep Analysis（Stage 2 Impact Cards）

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP │ 2026-06-10 │ MODE: DIGEST │ 1/5             ║
╠══════════════════════════════════════════════════════════╣
║  [BEARISH -2.9]  美國5月 CPI 4.2% 三年新高，連三月加速      ║
║  type: macro_data │ weights: Macro 50%                   ║
╠══════════════════════════════════════════════════════════╣
║  BULL  (+2.0) core 放緩=外生能源衝擊，地緣降溫可逆          ║
║  BEAR  (-4.0) Warsh 降息交易瓦解，2022 式股債同跌風險       ║
║  SECTOR(-3.0) REITs/非必需消費 -strong；Energy +moderate   ║
║  MACRO (-4.0) 7月升息 odds → ~50-55%；1973 Burns 類比      ║
║  ARBITER → BEARISH，採 Macro 主論點                        ║
╠══════════════════════════════════════════════════════════╣
║  受益 ↑ Energy │ 受損 ↓ Real Estate, Cons-Disc, Tech       ║
║  Binary Risk: No │ tickers: XOM HD DHI AMT JPM WMT        ║
╚══════════════════════════════════════════════════════════╝
```

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP │ 2026-06-10 │ MODE: DIGEST │ 2/5             ║
╠══════════════════════════════════════════════════════════╣
║  [BINARY -3.4]  美伊停火破裂：Apache 被擊落後美軍再空襲     ║
║  type: geopolitical │ weights: Bear 30% Macro 40%        ║
╠══════════════════════════════════════════════════════════╣
║  BULL  (+3.5) 國防補貨週期+油運費率跳升；極限施壓促談       ║
║  BEAR  (-4.5) Hormuz 封鎖尾部→油價三位數→衰退式緊縮        ║
║  SECTOR(-4.0) Defense/E&P/油運 +strong；Airlines -strong   ║
║  MACRO (-5.0) 1990 Kuwait 類比：油+170%、SPX -18%          ║
║  ARBITER → BINARY（四方分歧 8.0，48h 升級/降溫二元路徑）    ║
╠══════════════════════════════════════════════════════════╣
║  受益 ↑ Defense, Energy, Tankers │ 受損 ↓ Airlines, ConsD  ║
║  Binary Risk: YES (event ~6/12, within 48h)               ║
║  tickers: LMT RTX NOC FRO STNG XOM OXY DAL UAL            ║
╚══════════════════════════════════════════════════════════╝
```

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP │ 2026-06-10 │ MODE: DIGEST │ 3/5             ║
╠══════════════════════════════════════════════════════════╣
║  [BEARISH -2.1]  金銀比特幣齊跌，市場上調 Fed 升息押注      ║
║  type: monetary_policy │ weights: Macro 50%              ║
╠══════════════════════════════════════════════════════════╣
║  BULL  (+2.0) 升息 pricing 過頭，FOMC 後鴿派重定價空間     ║
║  BEAR  (-3.5) 全資產去槓桿前兆，MSTR 反身性死亡螺旋風險     ║
║  SECTOR(-2.0) 礦商/crypto 股 -strong；Banks +weak          ║
║  MACRO (-3.0) 戰火中黃金照跌=實質利率主導（2022Q1 類比）    ║
║  ARBITER → BEARISH，與 n0271 同源但獨立計分（定價 vs 數據）║
╠══════════════════════════════════════════════════════════╣
║  受益 ↑ Banks │ 受損 ↓ PM Miners, Crypto Equities          ║
║  Binary Risk: No │ tickers: NEM GOLD MSTR COIN MARA RIOT  ║
╚══════════════════════════════════════════════════════════╝
```

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP │ 2026-06-10 │ MODE: DIGEST │ 4/5             ║
╠══════════════════════════════════════════════════════════╣
║  [BEARISH -2.0]  SMCI $7B 融資暴跌13%，AI 融資疲勞擴散      ║
║  type: corporate │ weights: Sector 40%                   ║
╠══════════════════════════════════════════════════════════╣
║  BULL  (+3.0) 訂單超產能的 demand-driven 融資，需求未弱    ║
║  BEAR  (-3.5) AI 信用週期轉折；circular financing 疑慮     ║
║  SECTOR(-4.0) ODM→HBM→CoWoS→電力散熱逐層估值傳染           ║
║  MACRO (-3.0) 1999-2000 電信 vendor-financing 類比         ║
║  ARBITER → BEARISH，採 Sector；Bull vs Sector 分歧 7 分    ║
║            為本日辯論最激烈一則                            ║
╠══════════════════════════════════════════════════════════╣
║  受損 ↓ AI Hardware, Semis, HBM, DC Power/Cooling          ║
║  Binary Risk: No                                          ║
║  tickers: SMCI NVDA AMD MU DELL VRT META GOOGL TSM        ║
╚══════════════════════════════════════════════════════════╝
```

```
╔══════════════════════════════════════════════════════════╗
║  NEWS DEEP │ 2026-06-10 │ MODE: DIGEST │ 5/5             ║
╠══════════════════════════════════════════════════════════╣
║  [BEARISH -2.5]  油價跳漲，EIA 警告庫存奔向數十年低點       ║
║  type: geopolitical │ weights: Bear 30% Macro 40%        ║
╠══════════════════════════════════════════════════════════╣
║  BULL  (+4.0) 庫存結構性支撐油價；能源股 underweight 回補  ║
║  BEAR  (-4.0) 油價每+10% → CPI +0.3-0.4pp，升息迴圈強化   ║
║  SECTOR(-2.0) E&P/油服/油運 +strong；Airlines/化工 -       ║
║  MACRO (-4.0) 1979 第二次石油危機類比；SPR 緩衝已耗盡      ║
║  ARBITER → BEARISH（板塊 alpha vs 系統性 beta 之辯，採     ║
║            Macro 滯脹論為市場 verdict，能源雙向標記）      ║
╠══════════════════════════════════════════════════════════╣
║  受益 ↑ Energy, OilSvc, Tankers │ 受損 ↓ Airlines, Chems   ║
║  Binary Risk: YES (Hormuz 斷點 ~2026-07-04, not 48h)      ║
║  tickers: XOM CVX COP SLB HAL LNG FRO INSW DAL LYB        ║
╚══════════════════════════════════════════════════════════╝
```

### Arbiter 計算明細

| ID | type | weights (B/B/S/M) | scores | net | verdict |
|---|---|---|---|---|---|
| n0271 | macro_data | 15/15/20/50 | +2 / -4 / -3 / -4 | **-2.9** | BEARISH |
| n0064 | geopolitical | 15/30/15/40 | +3.5 / -4.5 / -4 / -5 | **-3.4** | **BINARY** |
| n0129 | monetary_policy | 15/15/20/50 | +2 / -3.5 / -2 / -3 | **-2.1** | BEARISH |
| n0047 | corporate | 25/25/40/10 | +3 / -3.5 / -4 / -3 | **-2.0** | BEARISH |
| n0106 | geopolitical | 15/30/15/40 | +4 / -4 / -2 / -4 | **-2.5** | BEARISH |

---

## 3. Shallow Digest（Stage 1 未晉級 Top 20）

### [-2.9] n0402  AI stocks resume sell-off and drag Wall Street lower from record highs
- **Bull**: 獲利了結非基本面惡化，訂單面未轉弱
- **Bear**: 高位擁擠交易解構，回調未到位
- **Sector**: AI 硬體/半導體領跌，rotation 至防禦
- **Macro**: 風險偏好收縮疊加升息定價
- Source: Fast Company HIGH │ type: sentiment
---
### [-2.8] n0219  A Hot Inflation Report and a Strong Jobs Report Just Trapped Trump's New Fed Chair
- **Bull**: Warsh 降息使命未變，數據壓力或為短期
- **Bear**: 降息預期全面瓦解，信譽風險溢價上升
- **Sector**: 利率敏感板塊（REITs/小型股）承壓
- **Macro**: 首次 FOMC 政策不確定性極高
- Source: 24/7 Wall Street HIGH │ type: monetary_policy
---
### [+2.5] n0211  Meta agrees to Indian AI data center deal (Reliance)
- **Bull**: AI 基建需求外溢至新興市場，租賃減輕 capex
- **Bear**: 資本強度持續攀升，回報週期拉長
- **Sector**: 資料中心/印度基建受益，RIL 連動
- **Macro**: 對 Fed 路徑中性
- Source: CNBC HIGH │ type: corporate
---
### [-2.4] n0031  Amazon trucking expansion sparks freight stock selloff
- **Bull**: AMZN 物流變現新收入來源
- **Bear**: 貨運業者結構性份額流失（ODFL -6%）
- **Sector**: LTL/卡車運輸承壓，AMZN 受益
- **Macro**: 通縮性競爭，對 CPI 邊際利好
- Source: CNBC HIGH │ type: sector_news
---
### [-2.2] n0300  China's factory-gate inflation at nearly 4-year high in May
- **Bull**: 中國走出通縮，需求面修復訊號
- **Bear**: 全球輸入性通膨第二引擎點火
- **Sector**: 進口中國中間財的製造業成本上升
- **Macro**: 全球通膨傳導已啟動，Fed 更難轉鴿
- Source: Reuters HIGH │ type: macro_data
---
### [-2.2] n0272  Germany risks recession as Iran energy shock hits growth (DIW)
- **Bull**: 歐央行被迫寬鬆，歐股估值支撐
- **Bear**: 歐洲工業衰退外溢美國出口需求
- **Sector**: 歐洲化工/汽車承壓，美國在地產能受益
- **Macro**: ECB 進退兩難：輸入通膨 vs 衰退
- Source: Reuters HIGH │ type: macro_data
---
### [-2.0] n0399  Bitcoin Treasuries Shed $62B in Deepening Crypto Rout
- **Bull**: 槓桿出清後籌碼結構改善
- **Bear**: 反身性去槓桿，margin call 外溢股市
- **Sector**: MSTR/COIN/礦企承壓
- **Macro**: 流動性收縮的領先指標
- Source: Bloomberg HIGH │ type: sentiment
---
### [-1.8] n0041  Warren Buffett's favorite stock market indicator is screaming sell
- **Bull**: 估值指標長期失準，非擇時工具
- **Bear**: 市值/GDP 極端值疊加升息環境
- **Sector**: 高估值成長股最受衝擊
- **Macro**: 估值壓縮與升息定價共振
- Source: Yahoo Finance HIGH │ type: sentiment
---
### [+1.8] n0003  Oracle has to deliver the earnings to match AI hype（今晚財報，BINARY）
- **Bull**: RPO/資料中心建設進度若超預期可重燃 AI 多頭
- **Bear**: AI 融資疲勞下，guidance miss 殺傷力放大
- **Sector**: 雲端/AI 基建鏈連動（NVDA 訂單 read-through）
- **Macro**: 對 Fed 中性，但牽動科技風險偏好
- Source: MarketWatch HIGH │ type: earnings │ ⚠️ binary within 48h
---
### [-1.7] n0044  Exploding investor euphoria and leveraged ETFs turned one bull cautious
- **Bull**: 策略師謹慎本身是反向指標
- **Bear**: 槓桿 ETF 持倉極端，去槓桿放大下跌
- **Sector**: 高 beta/題材股最脆弱
- **Macro**: 散戶槓桿是流動性收縮的放大器
- Source: MarketWatch HIGH │ type: sentiment
---
### [+1.6] n0366  SpaceX IPO: price set, retail allocation up in the air
- **Bull**: 史詩級 IPO 點燃散戶參與度
- **Bear**: 巨額凍資抽走市場流動性
- **Sector**: 太空/衛星題材股連動
- **Macro**: IPO 視窗 = 後期週期訊號
- Source: CNBC HIGH │ type: corporate
---
### [+1.5] n0245  NVIDIA gets the headlines, but Micron could offer more upside
- **Bull**: HBM 供不應求，guidance 上修
- **Bear**: +232% YTD 最擁擠持倉
- **Sector**: 記憶體/HBM 鏈強勢
- **Macro**: 對 Fed 中性
- Source: Zacks HIGH │ type: corporate
---
### [-1.3] n0396  Apple shares slide after big Siri AI reveal
- **Bull**: Siri 更新落地，生態變現起點
- **Bear**: AI 敘事不及預期，賣事實
- **Sector**: AAPL 供應鏈中性偏空
- **Macro**: 對 Fed 中性
- Source: CNBC HIGH │ type: corporate
---
### [+1.2] n0014  BorgWarner upgraded to buy at UBS on data-center power
- **Bull**: 汽車零件商轉型 DC 電力第二曲線
- **Bear**: 題材外溢估值，本業仍疲
- **Sector**: DC 電力鏈（VRT/ETN）正向 read-through
- **Macro**: 對 Fed 中性
- Source: Investing.com MEDIUM │ type: corporate
---
### [+1.2] n0127  Weekly mortgage demand surges nearly 11%
- **Bull**: 房市需求韌性，買家搶在升息前
- **Bear**: 搶跑式需求不可持續
- **Sector**: Homebuilders/房貸鏈短多
- **Macro**: 需求韌性反強化升息理由
- Source: CNBC HIGH │ type: macro_data
---
### [-1.2] n0288  Beijing escalating AI espionage (CrowdStrike)
- **Bull**: 資安支出強制性上升（CRWD/PANW）
- **Bear**: 美中科技戰升級，管制風險
- **Sector**: Cybersecurity 結構性受益
- **Macro**: 科技冷戰深化
- Source: CNBC HIGH │ type: geopolitical
---
### [+1.0] n0038  Cracker Barrel +30% on earnings short squeeze
- **Bull**: 財報 beat + 高空單比率軋空
- **Bear**: 單日軋空非趨勢反轉
- **Sector**: 餐飲板塊個別事件
- **Macro**: 對 Fed 中性
- Source: Investing.com MEDIUM │ type: earnings
---
### [-0.8] n0039  Trump Media scraps Truth Social spinoff
- **Bull**: 保留資產整體性
- **Bear**: 釋放價值路徑消失
- **Sector**: 個別事件，無板塊外溢
- **Macro**: 對 Fed 中性
- Source: Investing.com MEDIUM │ type: corporate
---
### [+0.3] n0212  Bank of Canada holds at 2.25%
- **Bull**: G7 央行未集體轉鷹
- **Bear**: 能源通膨 vs 弱經濟兩難全球化
- **Sector**: 加股/CAD 中性
- **Macro**: 央行兩難為全球縮影
- Source: WSJ HIGH │ type: monetary_policy
---
### [+0.2] n0368  Fed bank stress test results June 24
- **Bull**: 通過後開啟回購/股息上調窗口
- **Bear**: 高利率情境下資本要求趨嚴
- **Sector**: 大型銀行事件日曆
- **Macro**: 6/24 financial-conditions 檢查點
- Source: Fed Press HIGH │ type: monetary_policy
---

## Cache Patch Summary

| Target | Action |
|---|---|
| `news/news_logs/2026-06-10_digest.json` | 5 deep + 10 shallow，validator rc=0 ✅ |
| `news/news_logs/2026-06-10_triage.json` | 25 shallow_verdicts + stage2_items ✅ |
| `sector/sector_logs/2026-06-09_sector_intel.json` | top_catalysts prepend ×4（CPI / 美伊 / 油價 / SMCI）✅ |
| `sector/sector_logs/phase0.json` | macro_backdrop -4.76 → **-4.90**；news_patch_count 113；binary_risks +1（n0064 美伊 48h，expires 7/4）✅ |

*Fanout: PER_AGENT_BATCH（Bull / Bear / Sector / Macro 4 個獨立 subagent，全部 subagent_isolated=true，0 degraded）*

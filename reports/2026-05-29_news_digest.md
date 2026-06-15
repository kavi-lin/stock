# 📰 News Digest — 2026-05-29

> Mode: **DIGEST** │ fanout: `PER_AGENT_BATCH` │ 212 raw → 20 triaged → **5 deep** │ session_macro_delta **+0.3**
> Sources: RSS (79) + Finnhub (36) + SEC EDGAR (100) + FMP (0) → dedupe 212
> Stage 2: 4 isolated subagents (Bull / Bear / Sector / Macro), all `subagent_isolated: true`

今日主軸：**美伊 60 天停火 MOU 待 Trump 批准 → 油價自高點 −20%** 的去通膨 risk-on 主旋律，疊加 **AI 資本支出超級循環從硬體（Dell +39%）擴散到軟體（Snowflake +36%）與私募融資（Anthropic 逼近 $1T）**。宏觀面核心 PCE 3.3% 符合預期 + Bowman 鴿派發言，移除近月升息尾端。

---

## 1. Triage Summary

```
╔══════════════════════════════════════════════════════════════════════╗
║  NEWS TRIAGE  │  2026-05-29 14:00  │  212 raw → 20 triaged → 5 DEEP    ║
╠══════════════════════════════════════════════════════════════════════╣
║  ✅ DEEP   n0185  [+4.2]  Snowflake +36% AI 軟體狂熱        corporate   ║
║  ✅ DEEP   n0086  [BINARY] 油 −20% 美伊停火 MOU 待批      geopolitical  ║
║  ✅ DEEP   n0116  [+4.0]  Dell +39% AI 伺服器最快增速       corporate   ║
║  ✅ DEEP   n0154  [+3.5]  Anthropic 逼近 $1T 超越 OpenAI    sentiment   ║
║  ✅ DEEP   n0206  [+3.0]  核心 PCE 3.3% 符合預期       monetary_policy  ║
║  ──────────────────────────────────────────────────────────────────  ║
║  ❌ SKIP   n0103  [+3.5]  三星 HBM4E 樣品出貨 +6%        sector_news    ║
║  ❌ SKIP   n0130  [-3.2]  Gap 砍指引 −14%                  corporate    ║
║  ❌ SKIP   n0129  [+2.8]  Okta +8% agentic AI             corporate    ║
║  ❌ SKIP   n0192  [+2.8]  Kohl's +20% 銷售改善             corporate    ║
║  ❌ SKIP   n0196  [+2.8]  Arm 再創新高                     corporate    ║
║  ❌ SKIP   n0096  [-2.8]  Blue Origin 火箭爆炸             corporate    ║
║  ❌ SKIP   n0101  [+2.6]  信達 × 輝瑞 $10.5B               corporate    ║
║  ❌ SKIP   n0193  [+2.6]  Best Buy +15% 財報超預期         corporate    ║
║  ❌ SKIP   n0099  [+2.5]  輝達押注矽光子                   corporate    ║
║  ❌ SKIP   n0019  [-2.5]  太空股齊跌                      sector_news   ║
║  ❌ SKIP   n0045  [+2.4]  SoFi +13% 穩定幣                 corporate    ║
║  ❌ SKIP   n0023  [+2.2]  Bowman 反對升息            monetary_policy    ║
║  ❌ SKIP   n0123  [+2.0]  Exxon 警告油庫存偏低           sector_news    ║
║  ❌ SKIP   n0115  [-1.8]  Tesla Robotaxi 落後 Waymo        corporate    ║
║  ❌ SKIP   n0208  [+1.5]  星巴克下午客流回升               corporate    ║
╠══════════════════════════════════════════════════════════════════════╣
║  n0023/n0123 併入 deep（n0206 / n0086 cluster）                        ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## 2. Deep Analysis (Stage 2 Impact Cards)

### ╔ [BULLISH +2.1] n0116 — Dell shares jump 39% (AI 伺服器最快增速)
- **type**: corporate │ weights: Sector 40% / Bull 25% / Bear 25% / Macro 10%
- **BULL** ✅ +88% 營收 YoY 是 AI 資本支出超級循環轉化為真實出貨營收的硬證，驗證整條 GPU/HBM/網通/電力散熱價值鏈，去風險化需求面。
- **BEAR** ❌ 低毛利 ODM、客戶集中於少數超大規模業者、單日 39% 噴出 = 循環後段融漲頂訊號；GPU 轉嫁稀釋毛利讓 beat 品質偏低。
- **SECTOR** ✅ Technology +strong；直接驗證 NVDA / AMD / AVGO 與 HBM4E、伺服器 ODM 吞吐。
- **MACRO** ➖ 對 Fed 路徑可忽略；邊際支持「不著陸/名目 GDP 火熱」。
- **ARBITER** → BULLISH，採 Sector 主論點。三方同向偏多、僅 Bear −2，不升 BINARY。
- tickers: DELL, NVDA, AVGO, AMD │ 受益 ↑ Technology, Semiconductors

### ╔ [BULLISH +1.45] n0185 — Snowflake +36% best day ever (軟體全面回升)
- **type**: corporate │ weights: Sector 40% / Bull 25% / Bear 25% / Macro 10%
- **BULL** ✅ AI 變現從基礎設施擴散到軟體/應用層（更高毛利、更高本益比）；帶動 ServiceNow/Oracle/Palantir + Okta +8%，提供延長行情所需的領導廣度。
- **BEAR** ❌ 教科書級狂熱 + 相關性=1 擁擠；Salesforce 逆勢暗示領導收窄；估值標到狂熱而非現金流，單一族群失誤即連鎖。
- **SECTOR** ✅ Software/Technology +strong（ORCL/NOW/CRM/ADBE 曝險），漲勢部分為本益比擴張。
- **MACRO** ➖ 金融情勢寬鬆症狀而非 Fed 行動成因；邊際降低降息急迫性。
- **ARBITER** → BULLISH，採 Sector 主論點。Bear 擁擠論具份量未翻轉淨值，保留再評。
- tickers: SNOW, ORCL, NOW, CRM, PLTR │ 受益 ↑ Software, Technology

### ╔ [BINARY +0.45] n0086 — Oil drops 20% on US-Iran ceasefire（待 Trump 批准，48h 內）
- **type**: geopolitical │ weights: Macro 40% / Bear 30% / Bull 15% / Sector 15%
- **BULL** ✅ 油 −20% 朝 $60 + 霍爾木茲重啟 = 橫跨運輸/航空/化工/消費的成本下降順風 + risk-on 觸發，壓低通膨能源分項。
- **BEAR** ❌ 停火僅脆弱 60 天 MOU 待批；Exxon 警告庫存危險偏低，破局則 Brent 飆 $150-160 暴力衝擊；廉價油壓縮能源獲利/資本支出/高收益信用。
- **SECTOR** ⚠️ Energy −strong（XOM/CVX/COP/SLB/OXY）vs Industrials/Consumer_Disc +moderate；兩面性極強。
- **MACRO** ✅ 本批最具 Fed 相關性：去通膨強化不升息/年內降息偏向；Exxon 尾端是讓 Fed 不敢預先承諾降息的非對稱風險。產油 FX 弱、進口國 FX 強、美元偏軟。
- **ARBITER** → BINARY，採 Macro 主論點（去通膨外溢 > 單一能源獲利壓縮），保留 Energy −strong 警示。
- **Binary Risk**: ✅ event_date 2026-05-31，within_48h │ tickers: XOM, CVX, COP, SLB

### ╔ [NEUTRAL +0.7] n0206 — Core PCE 3.3% April, as expected
- **type**: monetary_policy │ weights: Macro 50% / Sector 20% / Bull 15% / Bear 15%
- **BULL** ✅ 精準符合預期移除上行驚奇；Bowman 主張對供給面通膨升息「已被證明無效」→ Fed 反應函數偏耐心，實質利率路徑封頂利長存續期成長股。
- **BEAR** ❌ 三年最大年增、結構性黏著遠高於 2%；Fed 容忍 3%+ 核心埋政策失誤尾端（日後鷹派轉向或實質利率侵蝕本益比）。
- **SECTOR** ➖ 純折現率輸入，無個股通道；REITs/公用事業/信用型 Financials 溫和緩解。
- **MACRO** ✅ 偏鴿邊際——移除升息尾端，首次降息往後推。歷史類比 2023「完美去通膨」高原期。
- **ARBITER** → NEUTRAL，Bull/Bear 量級相抵，Macro（重權重）+1 鴿派看穿主導淨值小正。屬數據型多空對立非事件二元，不升 BINARY。
- tickers: [] (純宏觀) │ 受益 ↑ Financials, Real_Estate

### ╔ [NEUTRAL +0.05] n0154 — Anthropic nears $1T, tops OpenAI
- **type**: sentiment │ weights: Bull 30% / Bear 30% / Macro 25% / Sector 15%
- **BULL** ✅ $65B 一輪超越 OpenAI 確認私募 AI 募資循環加速；資金流入運算（NVDA/雲端資本支出），驗證 n0116/n0185 需求管線；Ives「2027 Nasdaq 30k」強化長多敘事。
- **BEAR** ❌ 尚未達營收規模的私募實驗室標到近兆 + 永多目標價 = 峰值狂歡質性訊號；抬高 AI 複合體隱含估值地板、集中系統風險。
- **SECTOR** ➕ Technology +moderate；承銷運算資本支出需求（NVDA/AVGO/ORCL），但離公開現金流隔一步。
- **MACRO** ➖ 風險偏好量尺；狂熱鬆動金融情勢、邊際讓 Fed 對降息謹慎 + 升泡沫尾端。
- **ARBITER** → NEUTRAL，Bull/Bear 對稱相抵 + Sector 小正被 Macro 小負抵消，淨值近零。情緒型對立非事件二元。
- tickers: NVDA, GOOGL, META │ 受益 ↑ Technology, Communication

---

## 3. Shallow Digest (Stage 1 未晉級，top 15)

### [+3.5] n0103  Samsung 出貨次世代 AI 記憶體樣品，股價漲 6%
- **Bull**: HBM4E 樣品出貨追上 AI 記憶體供應鏈
- **Bear**: 僅樣品階段，量產/認證仍待客戶驗證
- **Sector**: Memory/Semi +strong，HBM 供需續緊
- **Macro**: 個體供給事件，宏觀中性
- Source: CNBC HIGH │ type: sector_news
---
### [-3.2] n0130  Gap 砍銷售指引、Old Navy 不如預期，重挫 14%
- **Bull**: 其他品牌穩健，估值已反映悲觀
- **Bear**: 主力 Old Navy 走弱 + 砍指引，消費降溫
- **Sector**: 服飾零售 −moderate
- **Macro**: 低端消費走弱、溫和去通膨側證
- Source: CNBC HIGH │ type: corporate
---
### [+2.8] n0129  Okta 因 agentic AI 需求季績超預期，漲 8%
- **Bull**: agentic AI 帶動身分驗證需求，Q1 超預期
- **Bear**: 「長線布局」暗示近期投入壓縮利潤率
- **Sector**: Software/資安 +moderate，呼應軟體回升
- **Macro**: 個體軟體事件，宏觀中性
- Source: CNBC HIGH │ type: corporate
---
### [+2.8] n0192  Kohl's 稱銷售趨勢改善，股價飆 20%
- **Bull**: 四年來最佳同店成長，轉機題材發酵
- **Bear**: 營收仍下滑，僅趨勢改善非絕對成長
- **Sector**: 零售 +moderate（轉機）
- **Macro**: 低端零售回穩，消費韌性側證
- Source: CNBC HIGH │ type: corporate
---
### [+2.8] n0196  Arm Holdings 再創歷史新高
- **Bull**: AI 授權題材續燒，動能強勁創新高
- **Bear**: 估值偏高，追高風險升溫
- **Sector**: Semiconductors/IP +moderate
- **Macro**: 個體動能事件，宏觀中性
- Source: CNBC HIGH │ type: corporate
---
### [-2.8] n0096  Blue Origin 火箭地面測試時於發射台爆炸
- **Bull**: 私有公司，對上市太空股直接衝擊有限
- **Bear**: New Glenn 重大挫敗，拖累太空族群情緒
- **Sector**: Aerospace/太空 −moderate
- **Macro**: 個體事件，宏觀無影響
- Source: CNBC HIGH │ type: corporate
---
### [+2.6] n0101  信達生物與輝瑞達成最高 $10.5B 合作，漲 10%
- **Bull**: 與輝瑞達成最高 $10.5B 腫瘤藥全球授權
- **Bear**: 里程碑金分階段，近期入帳有限
- **Sector**: Biotech/Pharma +moderate
- **Macro**: 個體交易事件，宏觀中性
- Source: CNBC HIGH │ type: corporate
---
### [+2.6] n0193  Best Buy 財報超預期、力拚銷售回升，漲 15%
- **Bull**: 獲利優於預期，轉機執行見效
- **Bear**: 銷售仍處低迷期，回升仍待驗證
- **Sector**: 3C 零售 +moderate
- **Macro**: 消費韌性側證，宏觀中性
- Source: CNBC HIGH │ type: corporate
---
### [+2.5] n0099  輝達投入數十億押注矽光子，可能改變 AI 產業
- **Bull**: 矽光子提升資料傳輸效率，深化 AI 護城河
- **Bear**: 商業化時程長，近期財務影響有限
- **Sector**: Semiconductors/光通訊 +moderate
- **Macro**: 結構性技術投資，宏觀中性
- Source: CNBC HIGH │ type: corporate
---
### [-2.5] n0019  Blue Origin 爆炸 + SpaceX 估值降溫，太空股齊跌
- **Bull**: 回調自 5 月急漲高點，長線題材未變
- **Bear**: 雙重利空打擊紅火太空族群情緒
- **Sector**: Aerospace/太空 −moderate
- **Macro**: 個體/族群情緒事件，宏觀中性
- Source: MarketWatch HIGH │ type: sector_news
---
### [+2.4] n0045  SoFi 因穩定幣題材漲 13%
- **Bull**: 穩定幣 + 散戶回流
- **Bear**: 軋空驅動非基本面
- **Sector**: Fintech +moderate
- **Macro**: 風險偏好回升
- Source: Investing.com MEDIUM │ type: corporate
---
### [+2.2] n0023  Fed 理事 Bowman 反對因通膨升息
- **Bull**: 鴿派、不升息訊號
- **Bear**: 容忍通膨恐讓預期脫錨
- **Sector**: 利率敏感類股偏多
- **Macro**: Fed 反應函數偏鴿（併入 n0206 deep）
- Source: CNBC HIGH │ type: monetary_policy
---
### [+2.0] n0123  Exxon 警告油庫存數週內危險偏低，價格將飆升
- **Bull**: 供給緊俏支撐能源股
- **Bear**: Brent $150-160 暴衝 = 通膨/需求衝擊
- **Sector**: Energy 雙向波動
- **Macro**: 停火破局尾端風險（併入 n0086 deep）
- Source: CNBC HIGH │ type: sector_news
---
### [-1.8] n0115  Tesla Robotaxi 車隊規模不到 Waymo 十分之一
- **Bull**: 早期階段，擴張空間大
- **Bear**: Robotaxi 規模遠落後對手
- **Sector**: Auto/Autonomous −weak
- **Macro**: 宏觀中性
- Source: CNBC HIGH │ type: corporate
---
### [+1.5] n0208  星巴克稱下午客流回升，轉機初見成效
- **Bull**: 轉機計畫初見成效
- **Bear**: 單點客流不代表整體獲利
- **Sector**: Consumer/餐飲 +weak
- **Macro**: 消費韌性側證
- Source: CNBC HIGH │ type: corporate
---

> Cache patched: `phase0.json` ✅ (news_patch_count 96, macro_backdrop −4.16, binary_risks +1 美伊停火) │ `sector_intel.json` ✅ (top_catalysts ×5 prepended)
> Validator: `validate_digest_output.py` → **rc=0** (V2.1 schema compliant, 10 shallow + 5 deep, PER_AGENT_BATCH)

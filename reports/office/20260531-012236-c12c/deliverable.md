# AI Server 記憶體需求成長性 2027–2030 — 需求面分析與受益股

> 範圍：只看**需求拉力 (demand pull)**。不評估估值、進場時機、供給競爭優劣。所有 TAM 數字為 sell-side / market-research forecast，離散度大 → 標來源日期 + 信賴等級，看**趨勢**而非單點。

---

## 1. 核心結論

記憶體是 AI server 2027–2030 成長最確定的需求向量，其中 **HBM 斜率最陡、信賴最高**。需求由四條軌道驅動，受益股依「營收對記憶體 bit 需求的純度」分六層。最乾淨的美股需求純標的：**MU（記憶體 beta）· RMBS（HBM4 IP）· TSM（base-die + CoWoS）· AMAT/LRCX/KLA（產能）**。

---

## 2. 需求 TAM — 標日期 + 信賴帶

| 指標 | 數字 | 來源 / 日期 | 信賴 |
|---|---|---|---|
| HBM bit demand 2024→2028（compute ASIC） | **35×** | Counterpoint | 高 — 方向最確定 |
| HBM 市場 CAGR to 2030 | **~30%/yr** | SK Hynix 管理層 / Reuters | 高 |
| HBM TAM | **$100B**（2028 新 deck / 2030 舊 deck） | Micron IR | 中 — 帶非點 |
| 全球記憶體市場 2026 / 2027 | **$889B / >$1.28T（+44%）** | TrendForce 2026-05-29 | 低 — 最激進，需交叉驗證 |
| DRAM 產值 2026 / 2027 | **$618.7B / $903.3B（+46%）** | 同上（單位 = USD 已驗） | 低 — 同 caveat |
| NAND 產值 2026 / 2027 | **$270.6B / $379.4B（+40%）** | 同上 | 低 — 同 caveat |
| 半導體總業 Q1-2026 | **$298.5B（季）**，2026 上看 >$1T | SIA / WSTS | 高 — sanity-check 上界 |

**TrendForce 數字裁決**：原文單位確認為**美元**（中文「億」= 100M、「兆」= trillion，換算無誤）。但該數高到逼近整體半導體 forecast → 標為 **TrendForce 激進預測，非 consensus**。不可換台幣，使用時須對 WSTS / Gartner / IDC / Omdia 交叉或明標 caveat。

**淨判斷**：point estimate 分歧是 timing / aggressiveness 差異，**方向所有 primary 源一致** — HBM 是斜率最陡、最確定的需求向量。

---

## 3. 四條需求軌道

| 軌道 | 驅動 | 2027–30 斜率 | 主受惠 |
|---|---|---|---|
| **HBM** | accelerator 出貨 × stack 數 × stack 容量，三項複利；GPU + 自研 ASIC 雙引擎 | 最陡 | DRAM 三雄 + 封裝 / 測試 / IP |
| **Server DDR5 / MRDIMM** | AI server content 高於一般 server；供給緊到 2028–29（Micron Idaho、SK Hynix Yongin fab 2027 才上線） | 高 | DRAM 三雄 + 模組接口 |
| **LPDDR5X / 6** | **雲端** Grace / GB200 用大容量 LPDDR（GH200 480GB、GB200 NVL72 17TB/rack）；成本敏感推論的高 CP 值方案 | 中-高 | Micron, Samsung — 框為 HBM **互補 / 分層 + 部分推論替代**，非 HBM killer |
| **Enterprise NAND / QLC eSSD** | 多模態 + RAG + KV-cache offload + AI 資料湖 HDD→QLC；Micron 245TB 6600 ION 已出貨 | 高 | Micron / Samsung / SK Hynix-Solidigm / Kioxia-SanDisk + 主控廠 |

---

## 4. 需求彈性排序

「每單位 HBM-bit 成長誰營收最敏感」。此為**需求純度排序，與投資吸引力分開**（需求驗證不等於股價必漲 — 估值、margin、份額、capex 循環另論）。

| Tier | Ticker | 對記憶體需求營收純度 | 邏輯 |
|---|---|---|---|
| **1 純記憶體 beta** | SK Hynix, **MU**, Samsung | 極高 | 營收 = 記憶體價 × bit；HBM mix 同時拉 ASP + margin |
| **2 高增量小基數** | **RMBS** | 絕對小、**% 敏感極高** | HBM4 / HBM4e controller IP，~90%+ 增量 margin，per-device royalty |
| **3 產能 / 測試 / 檢測槓桿** | **Hanmi (042700.KS)**, ASMPT, Advantest, Camtek, Onto | 中-高 | TCB 鍵合 + 測試 + 檢測隨 stack 高度（12→16-Hi）**超線性**；檢測（warpage / micro-crack）非線性 |
| **3.5 自研 ASIC / HBM4 整合** | **AVGO, MRVL** | 中 | hyperscaler 自研晶片（TPU/Maia/Trainium）整合 HBM4 堆疊高度依賴其設計服務；強 AI-ASIC play，**非純 memory bit beta** |
| **4 NAND 控制 / eSSD** | WDC-SanDisk, Phison, SIMO | 中（qualified） | QLC 企業級主控有產品線，但**頂級超高容量 hyperscale eSSD 多由原廠自研**（Solidigm / Samsung）→ 列 qualified beneficiary，純度低於 NAND 原廠 |
| **5 鄰接 / 部分替代** | ALAB, Montage 688008 | 低 | CXL retimer / MRCD — 受惠記憶體擴張但稀釋 HBM intensity |

**HBM4 Base-die value-leakage**：HBM4 base-die 移先進邏輯製程（TSMC）屬實 → 價值鏈向 foundry / IP / ASIC 擴。但「DRAM 廠利潤池被稀釋到要把 MU/Hynix 踢出 Tier 1」**未量化證實**（記憶體廠仍可能掌握 bundle 售價）→ 框為 **margin-mix / 價值分配風險，不改 Tier-1 需求 beta 排序**。

---

## 5. 受益股全圖 + 美股可交易性

**US-listed 純 / 近純**：MU · TSM(ADR) · RMBS · SNPS · CDNS · AVGO · MRVL · ALAB · AMAT · LRCX · KLA · ENTG · ONTO · CAMT · TER · AMKR · SNDX · ASX(ADR) · WDC · SIMO(ADR) · PHISON(OTC)

**外國（需國際 / OTC）**：SK Hynix · Samsung（韓）· **Hanmi**（韓）· Advantest · Disco · Kioxia（日）· ASMPT · Montage（港 / A 股）· BESI（荷）

| Bucket | 標的 | 需求推力 |
|---|---|---|
| **A — HBM 廠（最高最確定）** | SK Hynix (000660.KS), **MU**（美股最純）, Samsung (005930.KS) | HBM bit 35× + ~30% CAGR |
| **A+ — HBM4 IP / ASIC** | **RMBS**（HBM4 + HBM4e controller IP）, SNPS / CDNS（PHY / IP）, **AVGO / MRVL**（hyperscaler 自研 ASIC HBM4 整合） | base-die 邏輯化 → 設計服務增量 |
| **B — 鍵合 + 測試 + 檢測** | **Hanmi (042700.KS)**（SK Hynix dual TC bonder 核心供應、HBM 純度高）, ASMPT (0522.HK), Advantest (6857.T), **Camtek / Onto**（檢測非線性） | HBM4 延後 hybrid bonding、改良型 TCB 成剛需；stack 變高變薄 → 檢測超額需求 |
| **C — Foundry / 封裝** | **TSM**（HBM4 base-die + CoWoS）, ASE (ASX) / Amkor (AMKR) | CoWoS 是 HBM 落地硬上限 |
| **D — 製程設備 / 材料** | AMAT / LRCX / KLA（DRAM + TSV）, ENTG（耗材隨 wafer） | 產能擴張 |
| **E — NAND / eSSD** | **Micron, Samsung, SK Hynix-Solidigm, Kioxia / SanDisk**（純度最高）；Phison / SIMO（qualified 主控） | AI 存儲 + RAG 爆發 |
| **F — CXL / 池化** | **ALAB**（retimer）, Montage 688008 | 記憶體池化 — 雙面（擴張受惠 / 稀釋 HBM） |

> 注：BESI 因 HBM4 hybrid bonding 延後至 2028–29，從近期 base case 降為 optionality，移出 Bucket B 主名單。

---

## 6. 需求面假設 + 下行情境

demand-only 前提。以下皆為**風險，非已證實對沖**；HBM 需求成長**方向**扛得住全部五項，它們威脅的是**斜率 / 幅度**。

1. **CoWoS / 先進封裝產能 = HBM 需求落地硬上限**。HBM 出貨受封裝 / 基板 / TCB / 測試 / 檢測產能限制。需求再高、封裝不擴 → 無法轉營收。**反向使封裝 + 檢測（Hanmi / ASMPT / CAMT / ONTO）求 > 供確定性 ≥ 記憶體廠本身**。
2. **CXL 3.0 / 4.0 池化**。2028+ 可能封頂推論 HBM intensity。證據 = 論文 / 廠商 demo，**非廣泛 hyperscaler 部署** → HBM-bit 斜率下行風險、server-DDR5 / retimer 上行。
3. **量化 FP4 / INT4 + MoE + 推測解碼**。降 memory/token。方向真實、**未量化** → 當衰減因子，非 base-case kill。
4. **Edge / on-device AI**。推論移出雲 → LPDDR6 / LPCAMM2 上、雲端 TAM 趨緩。
5. **AI capex 放緩 / 供給超建 → 跌價**。記憶體經典循環。

---

## 7. 一句話投資映射（需求驅動價值）

- 需求最確定 + 最高斜率 = **HBM** → 美股最純 **MU**
- 增量 margin + IP 槓桿 = **RMBS**
- 賣鏟人（封裝是硬上限）= **TSM + Hanmi + ASMPT + CAMT / ONTO**
- 容量擴張 = **AMAT / LRCX / KLA**
- 存儲爆發 = **Micron + Samsung + SK Hynix-Solidigm**（純度）；Phison / SIMO（qualified）

---

## 8. 已驗證事實 + 殘留限制（誠實揭露）

**已驗證**：
- Counterpoint HBM bit 35× / SK Hynix ~30% CAGR / Micron $100B TAM — 多源支持。
- Samsung 2026 年 2 月宣布 HBM4 量產 + 商業出貨（Samsung Global Newsroom primary）。
- HBM4 base-die 移 foundry 邏輯製程（Samsung 4nm、SK Hynix TSMC 12nm）— TrendForce + Samsung 證實。
- HBM4 初期 sticks with microbumps、hybrid bonding 延後（SemiEng / JEDEC）。
- Rambus HBM4 + HBM4e controller IP；NVIDIA Grace LPDDR5X 雲端用量；Micron 245TB QLC eSSD — 皆 primary / IR。
- Hanmi 供 SK Hynix TC bonder（ChosunBiz / News1，含 2026 訂單）。

**殘留限制**：
- HBM 份額（Hynix ~57% / Samsung 22% / MU 21%）僅 secondary（Bloomberg / Counterpoint via 媒體）→ 用「龍頭、第三方估 >50%」措辭，避免硬報精確 %。
- §4 營收敏感度為 ordinal 方向序，非 segment filing 量化。
- CXL / edge / quant 影響未量化 → 呈情境帶，非 base-case 對沖。
- TrendForce 2026-05 TAM 屬激進預測 → 須對 WSTS / Gartner / IDC / Omdia 交叉或明標 caveat。

---

*此為研究分析，非投資建議。需求驗證 ≠ 股價必漲 — 估值、margin、份額、供給循環須另行評估。*
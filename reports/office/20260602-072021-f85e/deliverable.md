# Vera Rubin 平台 — 元件 × 股票供應商 × 世代增減 × 比例推算

> **關於名稱**：你寫的「vera robin」判定為 NVIDIA **Vera Rubin**（Vera CPU + Rubin GPU）平台，下一代 AI 機櫃系統。若你指的是別的標的，請告知，整份重做。

> **信心分層（全程強制標示，不混為事實）**
> - ✅ **官方/可核實規格**（NVIDIA IR、官方技術部落格、TrendForce/Digitimes/Tom's/DCD 第三方）
> - 🟡 **市場估值**（供應商份額、ASP、dollar content uplift —— 產業共識估值，非官方）
> - 🔴 **推測假說**（無可引用來源，僅列觀察/風險註記）

> **基準對照**
> - 標準本代 = **Vera Rubin NVL72**（72 Rubin GPU + 36 Vera CPU + NVLink6 + ConnectX-9 + BlueField-4）—— NVIDIA 官方主線，用此對照上代。
> - 上代 = **GB200 NVL72**（Blackwell）。
> - **NVL144 CPX**（加掛 Rubin CPX die，百萬-token 長文本推理）與 **Rubin Ultra NVL576（Kyber 機櫃，2027）** 為獨立配置，分開列，不混進標準 BoM。

---

## A. 運算矽（GPU / CPU / CPX die）

| 元件 | 供應商 (ticker) | 世代變化 | 比例推算 |
|---|---|---|---|
| Rubin GPU die | **TSMC (TSM)** 代工 N3；Ultra→N2 | Blackwell N4P → Rubin N3 | 🟡 die 矽面積 +30~40%；wafer 營收/櫃 +40~60% |
| Vera CPU die | TSMC；88 Olympus core | Grace 72→88 core **+22.2%** ✅；72→176 thread（SMT）**+144%** ✅ | ✅ 配比 1 Vera : 2 Rubin |
| Rubin CPX die | TSMC | 全新品類（Blackwell 無對應），用 GDDR7 非 HBM | 🟡 僅 NVL144 CPX 配置新增 |

---

## B. 記憶體（增量最大的單一類別 —— 多回合重大修正）

| 元件 | 供應商 | 世代變化 | 比例推算 |
|---|---|---|---|
| **HBM4** | **SK Hynix (000660.KS)**、**Samsung**、**Micron (MU)** 三家全進 ✅（Micron 官方證實 36GB 12H 已 2026 Q1 量產，designed for Vera Rubin） | HBM3e→HBM4；192→**288GB/GPU +50%** ✅；NVL72 總量 13.824→**20.736TB +50%** ✅ | 🟡 份額（Hynix 60~70% / Samsung 25~30% / Micron 5~10%）= **市場估值**；HBM4 ASP +30~60%、美元 content/櫃 ~+2x 皆 🟡 |
| **HBM4 base die 製程**（產能風險列） | **SK Hynix → 外包 TSMC N3** ✅；**Micron → 自製（DRAM 製程）** ✅；Samsung 自家 foundry turnkey | base die 首採先進 logic node | 🔴 **TSMC 產能排擠僅壓 SK Hynix**（搶 TSMC 額度）；**Micron 自製、Samsung turnkey 此維度相對占優**。⚠️ **時序註記**：Micron 自製優勢**僅限 HBM4 世代**；HBM4E（2027 / Rubin Ultra 期）Micron 亦轉 TSMC N3P，屆時排擠風險回歸三家 |
| **LPDDR5X / SOCAMM2**（Vera CPU 標配，漏項補正） | **SK Hynix、Samsung、Micron 三家全量產** ✅（SK Hynix 192GB SOCAMM2 2026-04 首發量產，optimized for Vera Rubin） | Vera 標配 **1.5TB**（Grace 480GB → **+212.5%** ✅）；頻寬 512GB/s→1.2TB/s **+134%** ✅ | 🟡 三家競爭，Micron 非獨家、非真空優勢，面臨南韓雙雄份額與價格競爭 |
| GDDR7（CPX 用） | Micron / Samsung / Hynix | NVL144 CPX 新增 | 🟡 對沖 Micron HBM 份額 |
| SSD（KV cache, PCIe Gen6） | Samsung、Hynix、**Micron**、Kioxia | BlueField-4 內建 SSD = 新增 content | 🟡 NAND content/櫃 新增量 |

**Micron 結論（✅ 從早期版本撤回）**：「可能出局/相對輸家」**錯** → 修正為 **多元受益者**：HBM4 已量產 + LPDDR5X SOCAMM2 + PCIe Gen6 SSD 三線，且 HBM4 期 base die 自製不受 TSMC 排擠。

---

## C. 先進封裝 / 基板（ABF 重大修正）

| 元件 | 供應商 | 世代變化 | 比例推算 |
|---|---|---|---|
| CoWoS-L | **TSMC (TSM)** | interposer 面積↑（更多 HBM stack + 更大 die） | 🟡 面積/櫃 +30~50%；🔴 大面積 interposer 初期良率 = 產能釋放瓶頸風險 |
| ABF 載板 | Ibiden (4062.T)、Shinko（Resonac 3402.T）、AT&S (ATS.VI)、Unimicron 欣興 (3037.TW) | 層數/面積↑ | 🟡 +20~40%；✅ **近端供不應求**（缺口 2H26 ~10% / 2027 ~21% / 2028 ~42%；AI 加速器 ABF 用量為 PC 的 15-18x）→ Ibiden/欣興/Unimicron 為**緊缺受益** |
| **玻璃基板**（技術路徑風險） | TSMC CoPoS、Samsung、Rapidus | 傳統 ABF 翹曲/訊損逼近物理極限 | 🔴 **量產 2028-29、NVIDIA 導入目標 2028（Feynman 期）**；**駁回「2026 底 ABF 結構性下修」說** —— 不在 Rubin 期增量內，僅屬 2028+ 長線估值風險 |
| 測試 | Advantest (6857.T)、Teradyne (TER) | HBM4 / 大 die 測試時間↑ | 🟡 +15~30% |

---

## D. 機櫃級互連（銅 vs 光 —— CPO 時點已鎖定）

| 元件 | 供應商 | 世代變化 | 比例推算 |
|---|---|---|---|
| NVLink switch ASIC | TSMC 代工（NVIDIA 設計） | NVLink5 → **NVLink6**；NVL72 scale-up **全銅** | ASIC 數同階，頻寬翻倍 |
| 銅纜 / connector | **Amphenol (APH)**、TE Connectivity (TEL) | NVLink6 速率升級 | 🟡 content/櫃 +20~35%，APH 最大受益 |
| **CPO**（Spectrum-X / Quantum-X Ethernet Photonics） | **Coherent (COHR)**、**Lumentum (LITE)**、**Fabrinet (FN)** | Blackwell pluggable → Rubin **CPO，200Gb/s SerDes，官方「now in production」** ✅（2026-05-31 NVIDIA IR）；5x power eff / 5x uptime ✅ | ✅ **時點已修正**：CPO 在 Rubin（NVL72）世代已量產，**非只等 Rubin Ultra**；NVIDIA 對 LITE + COHR **$4B（各 $2B）戰略投資** ✅（Reuters/Tom's）鎖產能。🟡 但 Rubin 營收 dollar content 比例不可直接推算。🔴 ELS 外部雷射「2-3 年消耗品 / razor-blade TAM 乘數 / FN 賠償壓毛利」= 假說無來源，僅列 COHR/LITE 潛在售後 upside 觀察 |
| Broadcom 釐清 | — | BCM CPO（Tomahawk）與 NVIDIA Spectrum-X 屬**直接競爭，非供應** | 移出 Rubin 供應鏈 |

---

## E. 網路 NIC / DPU

| 元件 | 供應商 | 世代變化 | 比例推算 |
|---|---|---|---|
| ConnectX-9 / BlueField-4 | NVIDIA（TSMC 代工） | CX8→CX9 1.6Tb/s；BF4 內建 SSD 存 KV cache | 每節點頻寬翻倍 |

---

## F. 電源（800VDC 為世代分水嶺）

| 元件 | 供應商 | 世代變化 | 比例推算 |
|---|---|---|---|
| VRM / PMIC / 功率半導體 | **Monolithic Power (MPWR)**、Infineon (IFX.DE)、Vicor (VICR)、Navitas (NVTS) | 轉 **800VDC**、液冷 busbar、20x 儲能 ✅（DCD） | 🟡 content/櫃 +50~100% |
| PSU / 電容蓄能架 / CDU | **Delta 台達電 (2308.TW)**（800VDC + Power Capacitance Shelf 主導 + 3MW 液冷 CDU）、Vertiv (VRT)、Lite-On | 高壓直流 + 大儲能 | 🟡 Delta content +80~120%。🔴 **隱形上游**：高暫態電容由 Nippon Chemi-Con (6997.T) / Rubycon 主導為產業常識，但「NCC 確供 Rubin 蓄能架 / Delta 純低毛利組裝」無來源，列假說，不據此自我推翻 Delta 系統整合地位 |

**功耗校正**：標準 NVL72/NVL144 約 **350~400kW**（🔴 估值，缺可引用來源），為 GB200（~120kW）的 ~3x。**~1MW 屬 Rubin Ultra / Kyber / 576 級配置，非 NVL72**；兩者非互相推翻，是不同配置層。

---

## G. 散熱（全液冷，content 大增 —— UQD 補上市標的）

| 元件 | 供應商 | 世代變化 | 比例推算 |
|---|---|---|---|
| 冷板 / CDU / manifold | **Vertiv (VRT)**、**Delta (2308.TW)**、AVC 奇鋐 (3017.TW)、Auras 雙鴻 (3324.TW)、**Jentech 健策 (3653.TW)**、Cooler Master、Boyd | Rubin **45°C 全液冷標配** ✅（DCD）、液冷 busbar | 🟡 content/櫃 +40~70%；🔴 台廠合格鏈未逐一核實 |
| **UQD 快接頭** | **Stäubli**（已入 NVIDIA RVL，MQD 依 VR200/Rubin 規格共同開發 ✅）、**Parker Hannifin (PH)**、CPC；**+ ZJK Industrial (NASDAQ: ZJK)** 已為 NVIDIA UQD 連接器供應商 ✅；Amphenol (APH, UQD/MQD) | UQD 標準 2020 由三家工作組制定 | ✅ 寡佔屬實，但**有上市替代 ZJK**，非純歐美鎖死；🔴「集體漏液訴訟滅頂」= 推測無來源，僅列風險註記 |

---

## H. 系統組裝 / ODM

| 供應商 | 世代變化 | 比例推算 |
|---|---|---|
| Foxconn 鴻海 (2317.TW)、Quanta 廣達 (2382.TW)、Wiwynn 緯穎 (6669.TW)、Dell (DELL)、Supermicro (SMCI) | 液冷 + 800VDC + CPO 複雜度↑ | 🟡 ASP/櫃大增（全推估，見下） |

---

## 世代「變多 / 變少」摘要

### ✅ 已核實增量（官方規格可算）
- HBM 容量 **+50%**（192 → 288GB/GPU）
- NVL72 HBM 總量 **+50%**（13.824 → 20.736TB）
- Vera CPU LPDDR5X 容量 **+212.5%**（Grace 480GB → 1.5TB）
- Vera CPU memory 頻寬 **+134%**（512GB/s → 1.2TB/s）
- Vera CPU core **+22.2%**（72 → 88）、thread **+144%**（72 → 176）
- 光通訊：pluggable → **CPO 已量產**
- 電源/散熱架構：800VDC + 45°C 全液冷 + 20x 儲能
- ABF 載板：近端供不應求（緊缺受益）

### 🟡 估值增量（dollar content，需來源佐證）
HBM 美元 content/櫃 ~**+2x** > 電源半導體 **+50~100%** > Delta 電源 **+80~120%** > 液冷 **+40~70%** > CoWoS **+30~50%** > connector **+20~35%** ≈ substrate **+20~40%**

### 變少 / 風險方
1. 純 pluggable 光收發模組中長期被 CPO 部分替代（無矽光/CPO 佈局者不利）
2. 風冷相關零組件占比下降
3. **SK Hynix** 新增 base die 依賴 TSMC 邏輯產能之排擠風險（HBM4 期 Micron 自製 / Samsung turnkey 相對占優；HBM4E 2027 後回歸三家）
4. 玻璃基板為 ABF **2028+ 長線**估值風險（非 Rubin 期）
5. ~~Micron HBM 出局~~ —— **已撤回**（三家全進 + 多線受益）

---

## ASP（全 🔴 推估，非事實）

上代 GB200 NVL72 ~US$3M → Rubin NVL72 估 **US$4~5M**、NVL144 估 **US$6~8M+**。**無可引用來源，僅 BoM 膨脹推算。**

---

## 投資含義（committee 視角，非交易指令）

- **最高槓桿純度（含已核實規格支撐）**
  - **TSM** —— 矽 + CoWoS 雙吃，且 HBM4 base die 外包再吃 SK Hynix 額度（三重）
  - **APH** —— connector + 液冷 + UQD 多線
  - **VRT、MPWR**
  - **Delta (2308.TW)** —— 電源 + 蓄能架 + CDU 三線

- **HBM 三家分歧**
  - SK Hynix：份額龍頭 🟡，但新增 TSMC 產能排擠風險
  - Micron：由「輸家」→ 多元受益 ✅（HBM4 自製 + LPDDR5X + SSD）
  - Samsung：foundry turnkey 彈性最大

- **CPO 時點已提前** ✅
  - COHR / LITE / FN —— 已量產 + $4B 鎖產能，**非純 2027 故事**；惟 Rubin 營收占比 🟡、ELS 售後乘數 🔴 假說

- **新增可投資標的**
  - **ZJK (NASDAQ)** —— UQD 連接器
  - **Nippon Chemi-Con (6997.T)** —— 蓄能架上游隱形贏家（🔴 待證）

---

## 仍為「永遠估值」或「探索層」之未鎖定項
1. HBM4 三家精確份額 —— 無官方/一致第三方數據，只能標範圍 + 市場共識
2. NVL72 功耗 350~400kW、ASP US$4~8M —— 缺可引用來源，維持 🔴 推測
3. ELS 消耗品壽命 / TAM 乘數、Fabrinet 賠償、NCC 收割、Delta 毛利稀釋 —— 全為無來源假說，僅列 upside/risk 註記
4. 台廠 ABF / 冷板 / ODM / connector 是否已逐一進入 Rubin 合格鏈 —— 探索層，不阻塞結論

---

*三回合辯證收斂：框架 → 兩輪技術/供應鏈盲點挑戰 → 兩輪 grounding（官方 IR + TrendForce/Digitimes/Tom's/DCD）。官方規格已附來源類型；所有份額/ASP/功耗/dollar content 維持估值或推測標示，未當事實呈現。*
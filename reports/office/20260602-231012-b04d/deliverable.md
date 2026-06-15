# CPO（Co-Packaged Optics）趨勢研究報告
**完成日期：2026-06-02**

---

## 摘要（一句話定錨）

CPO 是 800G → 1.6T（2026 商用元年）開啟、3.2T（2028–2030）才真正放量的**結構性轉折**。最確定的成長在**被 NVIDIA $4B 綁定的雷射份額/ASP 與 SiPho 先進封裝**，而非「雷射 TAM 必然量增」；可插拔模組層（中系）短期續旺、長期承壓但**非末日**；純 CPO 市場絕對值各家口徑分歧過大，應用「AI optics 總盤 × CPO 滲透率」框架判讀，不可看單一數字。

---

## 0. 背景：為何 CPO 現在成焦點

Switch ASIC 頻寬每代翻倍（51.2T → 102.4T → 未來 204.8T），但可插拔光模組（OSFP/QSFP-DD）走 ASIC↔模組的長電氣 trace，SerDes 重驅 + retimer DSP 功耗撞上「copper wall」。CPO 把光引擎（silicon photonics, SiPho）直接 co-package 在 ASIC 旁，砍掉長 trace 與 DSP，NVIDIA 官方數據省電約 3.5x、resiliency 約 10x。這是 AI scale-out 網路的結構性轉折，不是單點產品。

---

## 1. Speed 世代 × 平台 × CPO 滲透（總覽）

| 世代 | 每 lane | 當下主力形態 | CPO 滲透 | 代表平台 / 時點 |
|---|---|---|---|---|
| **400G** | 100G×4 | 可插拔 OSFP/QSFP-DD（成熟） | ~0 | 上一代 AI cluster，已被 800G 取代 |
| **800G** | 100G×8 / 200G×4 | 可插拔絕對主力；LPO 小量 | <5%，僅 demo | GB200/GB300 NVL72；Broadcom Bailly 51.2T 為首代 CPO 示範 |
| **1.6T** | 200G×8 | **可插拔（OSFP1600）>90% 主導** | pilot / 高 radix switch 點狀導入 | NVIDIA Quantum-X（2026H1, 115T）、Spectrum-X Photonics（2026H2, SN6800 達 409.6T）、Broadcom Davisson 102.4T（2026 出貨）。**LPO/LRO 為此世代主要競爭路線** |
| **3.2T+** | 400G×8（448G PAM4 SerDes，2027 樣品 / 2028 量產） | CPO 趨於必要，但 LRO 分流 | **真正 S-curve 放量窗口** | Broadcom 第 4 代 CPO（400G/ch）、Coherent OFC 2026 已 demo 6.4T(32×200G) **socketed** CPO + 400G lane modulator |

**時程定錨**：2026 = CPO switch **商用/首出貨元年**；**大規模部署落在 2028–2030**（Yole / LightCounting 一致）。1.6T 世代仍是可插拔天下（Cignal AI 預估 >5M 顆 2026、Nomura 20M 顆 2026 底，均指可插拔放量，非 CPO）。

---

## 2. 每平台精確 BOM 用量（本報告最關鍵交付 — 含證據分級）

> ⚠️ **計量單位的根本轉變**：轉 CPO 後，光「模組」消失，改成「光引擎 die + 外置雷射模組 + SiPho 封裝」。這是供應鏈價值重分配的核心。以下表格嚴格區分**官方口徑**與**業界拆解/推算**。

| 平台 | 總頻寬 | 光引擎 (OE) | 外置雷射模組 (ELS) | 證據層級 |
|---|---|---|---|---|
| **Broadcom Bailly** | 51.2T | **8 × 6.4T**（Broadcom 官方） | **16 顆**（每 6.4T 引擎配 2 顆） | OE = 官方；ELS = APNIC 拆解口徑，非 Broadcom 官方 BOM |
| **Broadcom Davisson** | 102.4T | **16 × 6.4T**（Broadcom 官方） | **~32 顆（推算，未證實）** | OE = 官方；ELS 顆數 **Broadcom 未公開**。32 為沿 Bailly 比例外推，但 100G→200G/lane 後通道數減半、單通道功率/RIN 要求升高，split ratio 可能改變 → **僅列情境推算，不作定論** |
| **NVIDIA Quantum-X Photonics** | 115.2T（144×800G） | **72 顆 1.6T 引擎**（4 packages × 18 engines；72×1.6T=115.2T 自洽） | **18 顆前面板雷射模組** | 18 ELS + 72 OE = APNIC 拆解，數學自洽可引用。⚠️「每 ELS 餵 8 顆引擎」**作廢**（18×8=144 引擎→230.4T，與 115.2T 矛盾）；APNIC 原文如此寫但內部不一致，可能涉備援 / laser-input / engine 定義差異 |

→ NVIDIA「**4x fewer lasers**」官方說法成立：18 顆 ELS 模組撐 144×800G，同頻寬可插拔約需 144 顆內建雷射模組。

**SiPho 封裝歸屬**：Quantum-X 用 **TSMC COUPE**（官方）。**Davisson 採 COUPE 的說法已撤回** — Broadcom 多處強調自家 CPO/SiPho/CMOS 製造，無 COUPE 口徑。

---

## 3. scale-up vs scale-out（用量框架的關鍵分野）

很多人誤以為 GB200 NVL72 機櫃內部塞滿光模組，**錯**：

- **scale-up（NVLink，機櫃內）**：GB200 NVL72 = **全銅**（官方 copper cartridge / passive backplane，>5,000 條；坊間「精確 5,184」為第三方數，不列官方口徑）。**CPO/光用量 = 0**。
- **scale-out（Spine/Leaf 交換器）= CPO 主戰場**；用量由資料中心拓撲決定，並非機櫃固定 BOM。
- **最大上行變數**：Rubin 世代 NVLink domain 擴大、800G+ 銅互連撞牆 → **scale-up 2027+ 起轉光**，LightCounting 列為下一個放量引擎、2028 高量。Rubin 規格未定，目前僅能定性，但這是整體 TAM 上修的最大潛在變數。

---

## 4. 雷射 / ELS TAM — P×Q 模型（撤回「TAM 必擴」結論）

雷射層常被吹捧為「CPO 必需、最乾淨多頭」。本報告**修正此過度樂觀論述**，改用嚴謹的量價拆解：

**必須區分「模組級」與「晶粒級」兩層 Q：**

| 層級 | 可插拔架構 | CPO 架構 | 衝擊 |
|---|---|---|---|
| **ELS 模組級** | ~144 顆內建雷射模組 | 18 顆外置 ELS 模組 | 模組數 ↓ 約 8x；NVIDIA 取保守口徑稱 4x |
| **雷射晶粒級 (Laser Die / CW source)** | 144 模組 × ~4 die ≈ **576 顆** | 18 模組 × ~8 die ≈ **144 顆** | die 物理出貨量 **↓ 4x** ← 這才是 NVIDIA「4x fewer lasers」的物理數學基礎 |

**P×Q 推導：**
- **Q（量）**：CPO 架構下每單位頻寬的雷射 **die 物理數量縮減約 4x**。
- **P（價）**：CW 高功率雷射（ELSFP，25dBm 級、單顆餵多引擎、高功率/良率要求）ASP 遠高於可插拔內建 DFB；但**絕對報價無公開數據**，無法量化收斂。
- **三情境**：
  - **悲觀**：P 漲幅 < 4x → CPO 滲透段雷射營收**淨縮**。
  - **中性**：P↑ ≈ 4x → 持平，靠滲透率增長拉動。
  - **樂觀**：P↑ > 4x **且** scale-up 轉光放大總基數 → 淨擴張。

**結論校正**：雷射多頭論點**不靠「數量」，靠「價值集中 + 總光連結基數擴張（含 scale-up）」**。對 Lumentum / Coherent 的投資彈性，還取決於其參與深度是 **bare die、laser subassembly，還是完整 ELS module** — die 級 Q 下降、module 級 ASP/封裝價值上升，淨效應因參與層級而異。NVIDIA 2026/03 投資 **$4B（Lumentum $2B + Coherent $2B，含 multibillion 採購承諾與產能優先權）**，證明的是 **ASP / 份額話語權與供應安全，不等於量增**。最確定者 = 被綁定的份額，而非 TAM 必然擴張。

---

## 5. 競爭技術路線：LPO / LRO（壓扁 CPO S-curve 的關鍵變數）

CPO 不是可插拔的唯一終點。**LPO**（拿掉 DSP/CDR，保留可插拔）與 **LRO**（只去接收端 retiming）是 CPO 在 200G/lane 世代的主要**分流/延後**力量：

- 2026 已有多家 1.6T 產品/驗證工具：Source Photonics 1.6T LPO、Sivers/Jabil 1.6T LRO、Keysight 1.6T 驗證、Juniper LRO 文件。Ethernet Alliance 2025 roadmap 已把 LPO/LRO 與 1.6T/3.2T 並列。
- **保守表述**：LPO/LRO 降低 retimed 可插拔功耗、保留熱插拔維護性 → **可能延後 CPO S-curve**。但「與 CPO 相當省電」**無足夠數據支持**；link budget、互通性、均衡負擔、實際省電幅度仍待客戶部署驗證。
- **若 LRO 在 1.6T/3.2T 成功，CPO S-curve 將被壓扁並後推至 2030 年之後。**

**但 400G/lane 是 CPO 的底層剛需邏輯**：當單通道電氣訊號達 400G/lane（PAM4 約 212.5 GBaud、Nyquist 約 106 GHz），PCB 趨膚效應與介電損耗呈指數飆升，ASIC↔模組電氣 trace 距離被壓到極短。CPO/NPO 把電氣路徑縮到毫米/微米級，在此世代**優勢變得關鍵**。惟須注意：IEEE 802.3 材料同時列 NPO/CPO，市場仍有 400G/lane DSP、LRO、NPO 等路線 —— CPO 是**強勢候選而非唯一解方**，能否完全取代可插拔仍取決於各路線的功耗、成本與可維修性。

---

## 6. 供應鏈分層（誰賺什麼）

**(A) 平台定義者**
- **Broadcom**：自有 SiPho/CMOS，垂直整合最深（Bailly → Davisson → 第 4 代 400G/ch）。
- **NVIDIA**：Quantum-X / Spectrum-X Photonics，靠 **TSMC COUPE** + micro-ring modulator (MRM)。
- **Marvell**：custom CPO（Teralynx-based、液冷）+ 3D SiPho engine，走 ELS 架構。

**(B) SiPho / 光引擎**
- TSMC COUPE（NVIDIA 御用，護城河高）、Broadcom 自有、Marvell（併 Inphi）、Ayar Labs（TeraPHY，Computex 2026 × Wiwynn）、Coherent（6.4T socketed CPO）。

**(C) 外置雷射 ELS（最被綁定的多頭標的）**
- **Lumentum、Coherent**（NVIDIA $4B 鎖定，已證雙方官方稿）。
- 論點細緻化見 §4：被綁定的是**份額/ASP/供應安全**，量增需 scale-up 轉光佐證。

**(D) 封裝 / 組裝 / 連接器 / FAU（被低估的剛需環節）**
- Fabrinet、ASE（封裝測試）；Corning / Senko（光連接）；AuthenX（Computex 2026 demo detachable FAU + 12 吋 CMOS meta-lens，解對位 yield）；Wiwynn（rack-level 整合）。
- **關鍵洞見**：CPO 最難、良率最低的步驟是 **FAU（光纖陣列）自動化精密耦合對位** 與 ELSFP 製造/光學測試。晶圓代工廠（TSMC）與封測廠（ASE）不擅長處理光纖材料與精密光路校準 —— 這正是傳統光模組龍頭累積數十年的核心競爭力。

**(E) 現行可插拔贏家（轉型風險方，中系）**
- Innolight(中际旭创) / Eoptolink(新易盛) 合計約 **60% 800G 市佔**（ip-fiber 口徑）；800G SiPho 滲透已近 50% 且續升。
- 可證事實：Eoptolink 泰國廠（規避出口管制）2025 末起支援 1.6T 量產。
- **定性修正：CPO 是「洗牌」而非「中系末日」**。憑藉 FAU 精密對位與測試能力，中系龍頭有機會從「光模組品牌商」轉型為 **CPO 時代的光學 OSAT（Photonics OSAT）代工候選**。但「Innolight 建全球首條 CPO 量產線 / 矽光佔比 >50% / 3.2T 送測 NVIDIA」等具體說法**無 primary 來源 → 屬券商/市場傳聞，不入結論主幹**。其 CPO 設計案卡位程度，目前無公開硬數據可確認，列為**待證假設**。

---

## 7. 供應鏈風險（依嚴重度排序）

1. **TSMC COUPE 產能 / 良率**：COUPE = SoIC-X 堆疊（官方 2024 Symposium），需 TSV / micro-bump / FAU 對位；AI GPU（Blackwell/Rubin）強烈爭奪 CoWoS / SoIC 產能下，CPO 封裝順位可能被排擠。**但「排擠到無法 2026H1 出貨」無公開量化證據** → 列為「初期量產爬坡風險」，不寫成已發生的瓶頸。
2. **運維抗拒（MTTR）**：CPO 故障需更換整台 switch → **socketed（插槽式）CPO**（Coherent OFC 2026 已 demo 6.4T）是化解關鍵。**但須注意 socket 在 200G/400G/lane 超高頻下會引入寄生電容/電感與阻抗不匹配（return loss），可能反而被迫補償功耗甚至重引 retimer/DSP，與 CPO 省電初衷衝突**（Broadcom 因此堅持焊接式）。Socketed CPO 屬「可維修性 vs 物理性能的技術妥協點」，商用成敗未定。
3. **LRO / LPO 分流**（見 §5）→ 壓扁 S-curve、後推時程。
4. **時程屢延**：熱 / yield / FAU 對位歷史性延遲。

---

## 8. 成長潛力（統一框架，棄絕對值）

採「AI optics 總盤 × CPO 滲透率」框架（最可靠）：

- **LightCounting**：AI Ethernet optics + CPO 合計 **$16.5B(2025) → $26B(2026)**，YoY 約 60%。
- **Yole**：photonics packaging 至 2031 規模三倍化，其中 **CPO packaging demand 約 $5B**，大規模部署落在 2028–2030。
- **純 CPO 窄口徑**（Mordor $165M / R&M $603M for 2026）**口徑分歧過大 → 僅列附註，不入主幹**。單看純 CPO 絕對值極易誤判。

---

## 9. 結論（投資視角，依確定性排序）

1. **最確定**：NVIDIA 綁定的**雷射 ASP / 份額**（Lumentum、Coherent，$4B 已證）+ **SiPho 先進封裝**（TSMC COUPE，護城河高）。注意確定的是「份額/價值集中」，**非雷射 TAM 必然量增**（P×Q 未收斂，die 級 Q 反而 ↓4x）。
2. **結構轉折確立但放量在後**：CPO 2026 為商用元年，**2028–2030 才進入 S-curve**；3.2T（400G/lane）+ scale-up 轉光是主放量引擎，底層由 400G/lane 電氣物理壁壘驅動。
3. **最大上行變數**：scale-up 於 2027+ 轉光（Rubin 規格未定，僅能定性）。
4. **最大下行 / 延後變數**：LRO/LPO 分流、TSMC COUPE 良率/產能、socketed CPO 運維成熟度。
5. **中系可插拔（Innolight/Eoptolink）**：短期（近 3 年）續旺，長期承壓；具 SiPho + 先進封裝能力者有機會轉為 Photonics OSAT，但 CPO 卡位屬**待證**，不宜入結論主幹。

---

## 附錄：證據層級總則

> 官方（Broadcom / NVIDIA / TSMC / Lumentum / Coherent IR）> 業界拆解（APNIC / Internet Watch，僅在數學自洽時引用）> 市場機構（LightCounting / Yole）> 券商傳聞（中系 CPO 數字，僅附註）。
>
> **兩處殘留不確定已明確標註、不作定論**：(1) Davisson ELS 顆數（Broadcom 未公開，32 僅推算）；(2) Quantum-X 每 ELS 對應引擎數（APNIC 內部數學矛盾）。此為公開資料天花板。
>
> **雷射 ASP 絕對報價無公開數據** → P×Q 三情境無法量化收斂為單一投資結論；若需下單決策，須以券商 BOM 成本拆解補強（超出公開研究範圍）。

---

*主要來源*：Broadcom IR（Bailly 51.2T / Davisson Tomahawk 6 102.4T）、NVIDIA Investor Release + Technical Blog（Quantum-X / Spectrum-X Photonics 規格、4x fewer lasers）、NVIDIA × Lumentum / Coherent $2B+$2B 官方稿、TSMC 2024 Tech Symposium（COUPE / SoIC-X）、Coherent OFC 2026（6.4T socketed CPO）、APNIC CPO deep dive + Internet Watch（BOM 拆解）、IEEE 802.3 400G/lane、Ethernet Alliance 2025 Roadmap、LightCounting / Yole（市場規模）、Cignal AI / Nomura（1.6T 出貨量）。
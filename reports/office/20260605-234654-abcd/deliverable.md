# 800V HVDC 架構 vs GB300（54V）供應鏈逐元件對照與關鍵獲利利器分析

> 本報告比較 NVIDIA 自 Kyber/Rubin 世代（2027 量產，單櫃 600kW–1MW）導入的 **800V HVDC** 架構，與既有 GB200/GB300（54V/48V 機內配電）的供應鏈元件用量增減，並指出每個關鍵節點的「獲利利器」公司。所有定量數字標明來源層級；NVIDIA/ODM 尚未公開逐櫃 BOM，第三方 ASP 估算（如 SemiAnalysis）一律標註為產業研究預估。

---

## 一、為何要從 54V 改成 800V HVDC

GB200/GB300 NVL72 單櫃約 **120kW**；當功率突破 **200kW** 後，54V 架構在電流與銅排損耗上撞到物理極限（NVIDIA 官方說法）。Kyber 世代單櫃上看 **600kW–1MW**，NVIDIA 改走 800V HVDC：資料中心端把中壓 AC 轉成 800V DC，用兩條導體送進機櫃，櫃內 DC-DC 再降到低壓給 GPU。

**官方量化效益（NVIDIA 架構級估算，非逐廠等比例受惠）**
- 端到端效率 **+5%**
- 每 MW 銅需求 **−45%**、維護成本 **−70%**、TCO 最高 **−30%**
- 800V Bus 整流／前段 DC-DC 導入 **1200V SiC MOSFET**，轉換損耗較矽元件低 **25–40%**

### 關鍵架構分歧：SST vs. AFE（決定誰受惠）

| 路徑 | 內容 | 2027 落地判斷 |
|---|---|---|
| **固態變壓器 SST** | 13.8kV AC 直接轉 800V DC，省去多級轉換 | CAPEX 較傳統變壓器高 3–5×、高壓隔離與故障率使 Hyperscaler 規避。NVIDIA 官方文僅列為「研究中候選路徑」，**非 Kyber 初期確定配置** |
| **AFE 整流器（折衷主流）** | MV-LV 傳統變壓器 + 排級/機櫃級 800VDC 高效率整流器（Active Front End） | **2027 初期預期主流**。一步到位全 SST 機率低 |

> **AFE 部署位置再分兩種，受惠者完全不同**：
> - **機櫃級/Sidecar AFE**（如台達電 180kW）：進櫃的是三相 AC，櫃內才轉 800VDC → **不需**大功率 800VDC Busway，利好機櫃電源廠（Delta、LiteOn）。
> - **排級/集中式 AFE**：排頭櫃或電力房就轉好，800VDC 兩條導體進櫃 → 計算櫃僅需 DC-DC 降壓架，催生 **800VDC Busway**（Legrand Starline、Eaton、Schneider）需求，但壓低機櫃級 AFE 用量。
>
> 此分歧在 Kyber 最終出貨規格定案前未定，是全篇最大的結構性變數。

---

## 二、逐元件用量增減對照（GB300 54V → 800V HVDC）

| 元件類別 | GB300（54V） | 800V HVDC | 變動與技術壁壘 | 主要受惠公司 / 風險提示 |
|---|---|---|---|---|
| **1200V SiC MOSFET**（整流/前段 AFE/SST） | 極少（多用低壓 Si） | **大增（核心新增）** | ▲▲▲ 高壓高效率剛需 | **Infineon（龍頭確定性最高）**、**onsemi（一站式整合）**。⚠️ Wolfspeed 2025/9 已脫離 Chapter 11 重整，但流動性與 8 吋良率仍存疑、份額流失中，不可與前兩者同列「確定性」 |
| **GaN 功率半導體**（板級高頻降壓） | 少量/局部 | **大增（核心新增）** | ▲▲▲ 800V→12V/6V 高比率降壓的材料升級主線；空間受限必用高頻 GaN HEMT 縮小磁性元件 | **Navitas**、**EPC**、**Innoscience**、**Infineon**、**Power Integrations**、**TI**。⚠️ Navitas 等為技術展示/架構支援，量產採購承諾待觀察 |
| **板級/托盤級 DC-DC 模組**（800V→12V/6V/54V） | 無（原 54V→12V） | **全新增量（核心樞紐）** | ★全新爆發。NVIDIA 採 **64:1 LLC 高比率轉換器**，面積較傳統多級少 26% | **Delta（台達電）**、**MPS**、**Renesas**。⚠️ Vicor 技術強但**未列**官方 800V 夥伴名單，有被取代風險 |
| **高壓直流防護元件**（斷路器/熔斷器/接觸器/絕緣監測） | 傳統 AC/低壓保護 | **高壓 DC 新規格** | ★全新爆發。DC 無過零點，斷弧難度極高、認證週期長、壁壘極高 | **系統級官方候選**：ABB、Eaton。**元件級候選（需 design-in 佐證）**：Eaton Bussmann、Littelfuse、Mersen。⚠️ 用語應為 solid-state breaker / DC fuse / contactor，非低壓 PCB eFuse |
| **高壓大電流連接器/線纜** | 54V 連接器 | **800V 高壓規格** | ▲▲ 爬電距離/電氣間隙/高壓互鎖 HVIL 要求高，ASP 與毛利顯著升 | **Bizlink 貿聯（已列官方名單）**。⚠️ TE Connectivity、Amphenol 為強勢候選，但**未從官方 800V 名單確認 design-in** |
| **高密度 Power Shelf**（AC-DC 及降壓機架） | 機架級 PSU | **集中化、單位 kW ASP 暴增** | ▲▲ 單櫃 Sidecar 價值量量級躍升 | **Delta**、**LiteOn 光寶**、**Megmeet 麥格米特**。📊 第三方（SemiAnalysis）估單櫃 Sidecar ASP 約 **$400k–$500k**，較舊架構約 10×（產業研究預估，非官方數字） |
| **電源櫃散熱系統** | 一般風冷 | **發熱密度大幅上升** | ▲▲ 1MW@98% 效率 → 損耗發熱 ~20kW（600kW ~12kW，算術成立） | **Delta**、**Vertiv**。⚠️ 液冷「必然性」未獲一手證實；**高壓櫃禁用一般水冷板**（滲漏→介電擊穿/拉弧），須走介電液浸沒/兩相或排級風水熱交（RDHx）。台廠散熱（雙鴻/奇鋐）design-in 待查 |
| **高壓銅匯流排 Busbar** | ~200kg/MW | **單櫃絕對用量大增** | ▲▲ 量價齊揚 | **Methode**、**Rogers**（疊層 Busbar）。糾正：每 MW 銅 −45%，但單櫃功率 ×5 → 單櫃絕對銅量約 **+2.75×**；高壓絕緣（Epoxy/Polyimide）+ 精密公差使 ASP/毛利雙升。⚠️ 健和興目前僅供 BBU 連接器/高壓端子，**非機櫃級 Busbar 供應商**，剔除為主要受惠者 |
| **高壓 BBU 備援** | 48/54V BBU | **800V 高壓 BBU 或低壓側 BBU** | ▲ 但路線未定 | onsemi、Renesas；電芯 LG/Samsung。⚠️ 機櫃級 800V BBU 串聯數/熱失控/BMS 難度幾何上升；產業更傾向**集中式 BESS** 或降壓後低壓側備援 → 機櫃 BBU 恐被 Eaton/Schneider/Vertiv 集中式儲能邊緣化 |
| **板級 VRM/多相控制器**（12V/6V→0.8V） | 需求高 | **仍高，密度/相數提升** | ▲ | MPS、Infineon、TI、Renesas |
| **超級電容/能源緩衝架** | 板級去耦電容 | **系統級防護（吸收 LLM 負載尖峰）** | ▲ 路線競爭 | 系統整合：Delta、Eaton、Vertiv；電芯：Maxwell、Skeleton。⚠️ 超電能量密度低，與 **LIC（鋰離子電容）/高倍率 LFP** 競爭未定。板級 MLCC 廠（Murata/TDK/Yageo）只受惠**板級去耦**，非系統級緩衝櫃 |
| **傳統集中式鉛酸 UPS** | 大量 | **部分被 AFE+高壓 BBU/電容架取代** | ▼ 相對逆風 | 傳統 UPS/鉛酸廠 |

---

## 三、NVIDIA 800V HVDC 官方生態三層名單（可驗證）

- **半導體層**：AOS、ADI、EPC、Infineon、Innoscience、MPS、Navitas、onsemi、Power Integrations、Renesas、Richtek、ROHM、STMicro、TI
- **電源系統元件層**：Bizlink、Delta、Flex、Lead Wealth、LITEON、Megmeet
- **資料中心電力系統層**：ABB、Eaton、GE Vernova、Heron Power、Hitachi Energy、Mitsubishi Electric、Schneider、Siemens、Vertiv

> Vicor、TE、Amphenol、Methode、Littelfuse、Mersen 等**未**出現在官方名單，列為候選需各自 design-in 佐證。

---

## 四、關鍵元件 → 哪家公司的「獲利利器」

**最高新增價值節點：把 Si 換成 1200V SiC / GaN 的功率半導體 + 800V→低壓高比率 DC-DC 模組 + 系統級高密度電源櫃。** 這是 800V 相對 54V 的純增量、單櫃 ASP 最高環節。

### 1. Delta 台達電 — 系統整合 + 散熱最大台廠受惠
**獲利利器：高密度 800V Power Shelf（180kW AC-DC）+ 800V→50V/12V DC-DC 托盤模組（90kW）+ 電源櫃散熱。**
非規格微調，是單櫃 ASP 數量級躍升；20kW 電源損耗熱再給散熱第二重紅利。確定性最高的系統級台廠。

### 2. Infineon 英飛凌 — SiC/GaN/功率半導體龍頭
**獲利利器：1200V CoolSiC MOSFET + GaN 功率晶片 + 高頻驅動晶片。**
Grid-to-Core 全材覆蓋、產能與財務最穩。Wolfspeed 重整期間最穩定吃下 AFE 整流 SiC 份額，同時卡位板級 GaN。確定性最高的半導體贏家。

### 3. MPS（Monolithic Power）— 板級高比率降壓 + 多相 VRM
**獲利利器：高壓板級 DC-DC 控制器 + 低壓多相 VRM。**
800V 直送計算板使降壓難度大增，MPS 以高密度電源管理工藝卡位增量半導體市場。

### 4. ABB 與 Eaton — 系統級安全與高壓防護
**獲利利器：中高壓 DC 斷路器、固態斷路器、特種高壓 DC 熔斷器。**
DC 無過零點滅弧難、認證久、壁壘高、毛利高的利基。兩者皆官方資料中心電力層夥伴，領先卡位。

### 5. Methode / Rogers — 銅匯流排高壓化升級
**獲利利器：高壓絕緣（Epoxy/Polyimide）精密疊層 Busbar。**
單櫃功率 ×5 帶來絕對銅量 +2.75×，加防電弧/絕緣/精密公差，從低毛利金屬加工升級為高毛利特殊工藝，量價齊揚。

### 6. Navitas（NVTS）— 高 beta 純題材彈性
**獲利利器：GaNFast + GeneSiC（10kW 800V→50V @98.5%、800V→6V 單級 PDB）。** NVIDIA 親自 design-in，但**年營收基數極小、2027 才放量、量產採購未定**，屬高 beta 投機性題材，非當期受惠，須明確警示。

---

## 五、一句話結論

800V HVDC 最大贏家是 **「把矽換成 1200V SiC/GaN」的功率半導體**（**Infineon** 確定性、**Navitas** 高彈性高風險）＋ **「系統整合的高密度電源櫃、高比率 DC-DC 與散熱」**（**Delta** 最確定台廠、Vertiv、Eaton）＋ **「高壓 DC 防護與高壓化 Busbar/連接器」**（ABB、Eaton、Methode、Bizlink）。逆風方：傳統 54V 機架 PSU、集中式鉛酸 UPS、低壓矽元件、低毛利純銅排加工。時程上 **2027 量產**，現在是 design-win 卡位、**非當期營收**。

---

## 六、投資風險與不確定性警示（Warning Checklist）

1. **逐櫃 BOM 未公開**：NVIDIA/ODM 未公布官方 800V 拆解 BOM；$400k–$500k Sidecar ASP 等為第三方產業研究預估，量產版可能因大量採購而偏差。
2. **AFE 部署位置未定**：機櫃級（利 Delta/LiteOn）vs. 排級集中式（利 Legrand/Eaton/Schneider Busway）走向不同，將大幅改變受惠分配。
3. **SST 商業化時程**：2027 初期大機率僅限特定 Hyperscale 測試，大宗仍走 AFE。
4. **能源緩衝路線分歧**：超級電容 vs. LIC vs. 高倍率 LFP vs. 集中式 BESS 未定；機櫃級 800V BBU 有被集中化邊緣化風險。
5. **散熱方案未定**：20kW 發熱算術成立，但液冷「必然性」未證實；水冷板因介電擊穿風險已被排除，須介電液/RDHx，台廠 design-in 待查。
6. **候選≠已入鏈**：Vicor、TE、Amphenol、Littelfuse、Mersen 未列官方名單，列受惠者需各自 design-in 一手佐證；健和興僅 BBU 連接器/端子，非機櫃 Busbar 供應商。
7. **Wolfspeed 財務風險**：雖脫離 Chapter 11，流動性與 8 吋良率仍存疑，不可與 Infineon/onsemi 同列確定性受益。

---

**主要來源**：NVIDIA 800 VDC Architecture 官方頁與 Tech Blog（含 ecosystem partner list、64:1 LLC、−45% 銅/+5% 效率）、NVIDIA DGX GB200 User Guide（rack ~120kW）、Delta 官方新聞稿（180kW/90kW power shelf 規格）、Navitas 10kW 與 800V→6V PDB 新聞稿、Wolfspeed 重整完成公告與 SEC filing、ABB/Eaton 800VDC 白皮書與新聞稿、SemiAnalysis《Inside the 800VDC Revolution》（付費研究，ASP 估算層級）。
# Cross-Sector Theme Definitions

This reference defines market themes by their constituent FINVIZ industries, sectors, proxy ETFs, and representative stocks. The theme_classifier.py script reads these definitions to map industry-level data into theme-level aggregations.

**Usage Notes:**
- Industry names must exactly match FINVIZ industry names (see `finviz_industry_codes.md`)
- `min_matching_industries`: Design-intent minimum for each theme. In practice, theme detection uses the global `cross_sector_min_matches` setting (default: 2, configurable in themes.yaml) as the threshold. Per-theme values below are informational and not individually enforced in code
- `static_stocks`: Fallback representative stocks used when industry-level data is insufficient
- `proxy_etfs`: Used for quick volume/momentum checks and as user-facing exposure recommendations

---

## AI & Semiconductors

- **Direction bias**: Bullish (typically)
- **Industries**: Semiconductors, Software - Application, Software - Infrastructure, Information Technology Services, Electronic Components, Computer Hardware, Scientific & Technical Instruments
- **Sectors**: Technology (primary), Communication Services, Industrials
- **Proxy ETFs**: SMH, SOXX, AIQ, BOTZ, CHAT
- **Static stocks**: NVDA, AVGO, AMD, INTC, QCOM, MRVL, AMAT, LRCX, KLAC, TSM, MU, ARM, SNPS, CDNS, MCHP
- **Min matching industries**: 2

---

## Clean Energy & EV

- **Direction bias**: Bullish (typically)
- **Industries**: Solar, Utilities - Renewable, Auto Manufacturers, Auto Parts, Electrical Equipment & Parts, Specialty Chemicals
- **Sectors**: Utilities, Consumer Cyclical, Industrials, Basic Materials
- **Proxy ETFs**: ICLN, QCLN, TAN, DRIV, LIT
- **Static stocks**: ENPH, SEDG, FSLR, RUN, TSLA, RIVN, LCID, NIO, PLUG, BE, CHPT, ALB, SQM, LAC, LTHM
- **Min matching industries**: 2

---

## Cybersecurity

- **Direction bias**: Bullish (typically)
- **Industries**: Software - Infrastructure, Information Technology Services, Software - Application, Communication Equipment
- **Sectors**: Technology (primary)
- **Proxy ETFs**: CIBR, HACK, BUG
- **Static stocks**: CRWD, PANW, FTNT, ZS, NET, S, OKTA, CYBR, QLYS, RPD, TENB, VRNS, SAIL, MNDT, DDOG
- **Min matching industries**: 2

**Note:** Cybersecurity overlaps with broader software industries. Theme classification uses proxy ETF volume and static stock performance to differentiate from general software themes.

---

## Cloud Computing & SaaS

- **Direction bias**: Bullish (typically)
- **Industries**: Software - Application, Software - Infrastructure, Information Technology Services
- **Sectors**: Technology (primary), Communication Services
- **Proxy ETFs**: SKYY, WCLD, CLOU
- **Static stocks**: CRM, NOW, SNOW, DDOG, TEAM, MDB, ESTC, NET, ZS, HUBS, BILL, TTD, PLTR, DOCN, DT
- **Min matching industries**: 2

**Note:** Cloud/SaaS overlaps significantly with Cybersecurity and AI themes. When multiple themes share the same industries, proxy ETF performance differentiates them.

---

## Biotech & Genomics

- **Direction bias**: Bullish (typically, but highly volatile)
- **Industries**: Biotechnology, Drug Manufacturers - Specialty & Generic, Medical Devices, Diagnostics & Research, Drug Manufacturers - General
- **Sectors**: Healthcare (primary)
- **Proxy ETFs**: XBI, IBB, ARKG, GNOM
- **Static stocks**: AMGN, GILD, VRTX, REGN, MRNA, BIIB, ILMN, CRSP, NTLA, BEAM, EDIT, EXAS, TWST, SGEN, BMRN
- **Min matching industries**: 2

---

## Infrastructure & Construction

- **Direction bias**: Bullish (typically, policy-driven)
- **Industries**: Engineering & Construction, Building Materials, Industrial Distribution, Farm & Heavy Construction Machinery, Steel, Specialty Industrial Machinery, Railroads, Waste Management
- **Sectors**: Industrials (primary), Basic Materials
- **Proxy ETFs**: PAVE, IFRA, SIMS
- **Static stocks**: CAT, DE, VMC, MLM, URI, PWR, EME, MTZ, GVA, AECOM, STRL, GBX, NUE, CLF, RS
- **Min matching industries**: 3

---

## Gold & Precious Metals

- **Direction bias**: Bullish (typically in risk-off or inflation)
- **Industries**: Gold, Silver, Other Precious Metals & Mining
- **Sectors**: Basic Materials (primary)
- **Proxy ETFs**: GDX, GDXJ, RING, SIL
- **Static stocks**: NEM, GOLD, AEM, FNV, WPM, RGLD, KGC, AGI, AU, HMY, PAAS, CDE, HL, MAG, EQX
- **Min matching industries**: 2

---

## Oil & Gas (Energy Sector)

- **Direction bias**: Varies (cyclical)
- **Industries**: Oil & Gas E&P, Oil & Gas Equipment & Services, Oil & Gas Midstream, Oil & Gas Refining & Marketing, Oil & Gas Integrated, Oil & Gas Drilling
- **Sectors**: Energy (primary)
- **Proxy ETFs**: XLE, XOP, OIH
- **Static stocks**: XOM, CVX, COP, EOG, SLB, HAL, PXD, DVN, MPC, VLO, PSX, OXY, FANG, HES, WMB
- **Min matching industries**: 2

---

## Financial Services & Banks

- **Direction bias**: Varies (rate-sensitive)
- **Industries**: Banks - Diversified, Banks - Regional, Capital Markets, Insurance - Diversified, Insurance - Property & Casualty, Financial Data & Stock Exchanges, Credit Services, Asset Management, Insurance Brokers, Mortgage Finance
- **Sectors**: Financial Services (primary)
- **Proxy ETFs**: XLF, KBE, KRE, IAI
- **Static stocks**: JPM, BAC, WFC, GS, MS, C, SCHW, BLK, AXP, ICE, CME, MCO, SPGI, BX, KKR
- **Min matching industries**: 3

---

## Healthcare & Pharma

- **Direction bias**: Varies (defensive in downturns)
- **Industries**: Drug Manufacturers - General, Health Care Plans, Medical Care Facilities, Health Information Services, Medical Distribution, Medical Instruments & Supplies, Pharmaceutical Retailers
- **Sectors**: Healthcare (primary)
- **Proxy ETFs**: XLV, IHE, IHI
- **Static stocks**: UNH, JNJ, LLY, PFE, ABT, TMO, DHR, MDT, ISRG, SYK, BSX, EW, HCA, CVS, CI
- **Min matching industries**: 3

**Note:** Healthcare & Pharma is distinct from Biotech & Genomics. Healthcare focuses on established pharma, insurance, and medical devices; Biotech focuses on emerging drug development and genomics.

---

## Defense & Aerospace

- **Direction bias**: Bullish (typically in geopolitical tension)
- **Industries**: Aerospace & Defense, Airlines, Security & Protection Services
- **Sectors**: Industrials (primary)
- **Proxy ETFs**: ITA, PPA
- **Static stocks**: LMT, RTX, NOC, BA, GD, LHX, HII, TDG, HWM, AXON, LDOS, BWXT, KTOS, SPR, TXT
- **Min matching industries**: 2

**Note (v0.2 split)**: Pure-play space economy names (RKLB, ASTS, LUNR) moved to dedicated **Space Economy** theme below — different driver dynamics (commercial satellite/launch economy vs. military procurement cycles). BWXT remains in both because of its dual military-naval and commercial-nuclear exposure.

---

## Space Economy

- **Direction bias**: Bullish (commercial space race, satellite constellation buildout)
- **Industries**: Aerospace & Defense, Communication Equipment, Scientific & Technical Instruments
- **Sectors**: Industrials, Communication Services, Technology
- **Proxy ETFs**: ROKT, ARKX, UFO
- **Static stocks**: RKLB, ASTS, LUNR, MAXR, GSAT, IRDM, PL, BWXT, RDW, KTOS, JOBY, RDW, ACHR, BKSY, MNTS
- **Min matching industries**: 1

**Note**: Narrow universe + small-cap dominated → high beta + low liquidity. Many constituents have <$5B market cap. Driver = launch cadence, satellite contracts, defense space spending — distinct from broader Defense & Aerospace. Min industries=1 because pure-play universe is small.

---

## Real Estate & REITs

- **Direction bias**: Varies (rate-sensitive)
- **Industries**: REIT - Residential, REIT - Industrial, REIT - Retail, REIT - Office, REIT - Healthcare Facilities, REIT - Diversified, REIT - Hotel & Motel, REIT - Specialty, Real Estate Services, Real Estate - Diversified, Real Estate - Development
- **Sectors**: Real Estate (primary)
- **Proxy ETFs**: VNQ, XLRE, IYR
- **Static stocks**: PLD, AMT, CCI, EQIX, SPG, O, WELL, DLR, PSA, VICI, EXR, AVB, ARE, MAA, IRM
- **Min matching industries**: 3

---

## Retail & Consumer

- **Direction bias**: Varies (consumer sentiment driven)
- **Industries**: Internet Retail, Specialty Retail, Apparel Retail, Home Improvement Retail, Department Stores, Discount Stores, Luxury Goods, Restaurants, Leisure, Resorts & Casinos, Gambling, Apparel Manufacturing, Footwear & Accessories
- **Sectors**: Consumer Cyclical (primary), Consumer Defensive
- **Proxy ETFs**: XLY, XRT, XLP, IBUY
- **Static stocks**: AMZN, HD, LOW, TJX, COST, WMT, TGT, NKE, SBUX, MCD, DPZ, LULU, ROST, BURL, DECK
- **Min matching industries**: 3

---

## Crypto & Blockchain

- **Direction bias**: Bullish (typically in risk-on)
- **Industries**: Capital Markets, Software - Application, Financial Data & Stock Exchanges, Information Technology Services
- **Sectors**: Financial Services, Technology
- **Proxy ETFs**: BITO, BLOK, BITQ, IBIT, DAPP
- **Static stocks**: COIN, MSTR, MARA, RIOT, CLSK, HUT, BITF, SQ, PYPL, HOOD, CIFR, IREN, HIVE, CORZ, BTBT
- **Min matching industries**: 2

**Note:** Crypto theme uses proxy ETFs and static stocks as primary signals rather than industry classification, since blockchain companies span multiple traditional industries.

---

## Nuclear Energy

- **Direction bias**: Bullish (policy-driven, AI data center demand)
- **Industries**: Uranium, Utilities - Independent Power Producers, Specialty Industrial Machinery, Electrical Equipment & Parts
- **Sectors**: Energy, Utilities, Industrials
- **Proxy ETFs**: URA, URNM, NLR, NUKZ
- **Static stocks**: CCJ, UEC, NXE, DNN, UUUU, LEU, SMR, OKLO, BWX, GEV, CEG, VST, TLN, NRG, BWXT
- **Min matching industries**: 2

---

## Uranium

- **Direction bias**: Bullish (supply deficit narrative)
- **Industries**: Uranium, Other Industrial Metals & Mining
- **Sectors**: Energy (primary), Basic Materials
- **Proxy ETFs**: URA, URNM, URNJ
- **Static stocks**: CCJ, UEC, NXE, DNN, UUUU, LEU, URG, GLATF, EU, PALAF, SRUUF, LTBR, FCUUF, AEC, WSTRF
- **Min matching industries**: 1

**Note:** Uranium is a sub-theme of Nuclear Energy but tracked separately due to its distinct commodity-driven dynamics. Requires only 1 matching industry due to narrow sector focus.

---

## Quantum Computing

- **Direction bias**: Bullish (early-stage, high volatility — pure plays often >5% daily ATR)
- **Industries**: Computer Hardware, Software - Infrastructure, Information Technology Services, Semiconductors
- **Sectors**: Technology
- **Proxy ETFs**: QTUM, ARKQ
- **Static stocks**: IONQ, RGTI, QBTS, QUBT, ARQQ, IBM, GOOGL, MSFT, HON, INTC, NVDA
- **Min matching industries**: 1

**Note:** Pure-plays (IONQ / RGTI / QBTS / QUBT / ARQQ) are extremely volatile (~8% daily ATR not unusual). Mega-cap exposure (IBM, GOOGL, MSFT, NVDA, INTC) dilutes signal — they have quantum divisions but it's <5% of revenue. Theme score should weight pure-plays heavier. Min industries=1 because pure-play universe < 10 names.

---

## Robotics & Automation

- **Direction bias**: Bullish (industrial automation + AI-physical-world integration)
- **Industries**: Specialty Industrial Machinery, Medical Devices, Semiconductor Equipment & Materials, Computer Hardware, Industrial Distribution, Auto Parts
- **Sectors**: Industrials, Healthcare, Technology
- **Proxy ETFs**: BOTZ, ROBO, IRBO, ARKQ
- **Static stocks**: ISRG, TER, ONTO, NVDA, ABBN, FANUY, ROK, EMR, KION, HEINY, MIDD, AME, COHR, IPGP, SYK
- **Min matching industries**: 2

**Note:** Robotics theme overlaps with AI & Semiconductors via NVDA / ONTO / TER. Differentiation: Robotics emphasizes physical-world execution (industrial machines, surgical robots, factory automation) while AI & Semiconductors emphasizes inference compute. Co-recommendations across these two themes are EXPECTED, not duplication.

---

## Utilities Defensive

- **Direction bias**: Defensive (counter-cyclical, low beta — outperforms in risk-off / recession)
- **Industries**: Utilities - Regulated Electric, Utilities - Diversified, Utilities - Regulated Gas, Utilities - Regulated Water
- **Sectors**: Utilities (primary)
- **Proxy ETFs**: XLU, IDU, VPU, FUTY
- **Static stocks**: NEE, DUK, SO, AEP, XEL, ED, PEG, EXC, AEE, ETR, ES, EIX, SRE, AWK, AWR
- **Min matching industries**: 2

**Note:** Distinct from **Nuclear Energy** (which is offense — AI data center power demand thesis). Utilities Defensive is the canonical risk-off play: regulated returns, dividend-heavy, low beta (~0.4). Includes neither IPP names (CEG/VST — those are in Nuclear) nor renewable pure-plays (those are in Clean Energy & EV). Sample-bias counterweight: most other v0.2 themes (AI / Quantum / Space / Robotics) are high-beta growth — Utilities provides risk-on/risk-off coverage diversity.

---

## Obesity & GLP-1

- **Direction bias**: Bullish (medical innovation)
- **Industries**: Drug Manufacturers - General, Drug Manufacturers - Specialty & Generic, Medical Devices, Biotechnology
- **Sectors**: Healthcare (primary)
- **Proxy ETFs**: SLIM, HRTS
- **Static stocks**: LLY, NVO, AMGN, VKTX, ALT, GPCR, SMLR, RVMD, PTGX, IVA
- **Min matching industries**: 2

**Note:** Obesity/GLP-1 is a narrow theme that overlaps with Healthcare & Pharma. It is differentiated primarily through proxy ETF volume and static stock performance rather than industry classification.

---

## Summary Table

| Theme | Industries | Sectors | Proxy ETFs | Static Stocks | Min Industries |
|-------|-----------|---------|-----------|--------------|----------------|
| AI & Semiconductors | 7 | 3 | 5 | 15 | 2 |
| Clean Energy & EV | 6 | 4 | 5 | 15 | 2 |
| Cybersecurity | 4 | 1 | 3 | 15 | 2 |
| Cloud Computing & SaaS | 3 | 2 | 3 | 15 | 2 |
| Biotech & Genomics | 5 | 1 | 4 | 15 | 2 |
| Infrastructure & Construction | 8 | 2 | 3 | 15 | 3 |
| Gold & Precious Metals | 3 | 1 | 4 | 15 | 2 |
| Oil & Gas (Energy) | 6 | 1 | 3 | 15 | 2 |
| Financial Services & Banks | 10 | 1 | 4 | 15 | 3 |
| Healthcare & Pharma | 7 | 1 | 3 | 15 | 3 |
| Defense & Aerospace | 3 | 1 | 2 | 15 | 2 |
| Space Economy | 3 | 3 | 3 | 14 | 1 |
| Real Estate & REITs | 11 | 1 | 3 | 15 | 3 |
| Retail & Consumer | 13 | 2 | 4 | 15 | 3 |
| Crypto & Blockchain | 4 | 2 | 5 | 15 | 2 |
| Nuclear Energy | 4 | 3 | 4 | 15 | 2 |
| Uranium | 2 | 2 | 3 | 15 | 1 |
| Quantum Computing | 4 | 1 | 2 | 11 | 1 |
| Robotics & Automation | 6 | 3 | 4 | 15 | 2 |
| Utilities Defensive | 4 | 1 | 4 | 15 | 2 |
| Obesity & GLP-1 | 4 | 1 | 2 | 10 | 2 |

**Total: 21 themes** covering major market narratives + v0.2 expansion (Space, Quantum, Robotics, Utilities Defensive).

---

## Theme Overlap Matrix

Some industries contribute to multiple themes. When scoring, each industry's data is used in all applicable themes:

| Industry | Themes |
|----------|--------|
| Software - Application | AI, Cybersecurity, Cloud, Crypto |
| Software - Infrastructure | AI, Cybersecurity, Cloud, Quantum |
| Drug Manufacturers - General | Healthcare, Biotech, Obesity |
| Biotechnology | Biotech, Obesity |
| Capital Markets | Financial Services, Crypto |
| Electrical Equipment & Parts | Clean Energy, Nuclear |
| Uranium | Nuclear, Uranium |
| Aerospace & Defense | Defense, Space |
| Computer Hardware | AI, Quantum, Robotics |
| Semiconductors | AI, Quantum, Robotics |
| Specialty Industrial Machinery | Infrastructure, Nuclear, Robotics |
| Medical Devices | Biotech, Healthcare, Obesity, Robotics |
| Utilities - Regulated Electric | Utilities Defensive |

This overlap is intentional - a strong software industry may boost multiple themes simultaneously, reflecting the interconnected nature of market narratives.

**v0.2 cross-theme dynamics**:
- BWXT appears in both Defense & Aerospace AND Nuclear Energy AND Space Economy (military naval reactors + commercial nuclear + space launch reactors). Triple-membership is correct, not error.
- NVDA appears in AI & Semiconductors + Quantum Computing + Robotics & Automation. Reflects NVIDIA's positioning as compute backbone for all three.
- ISRG appears only in Robotics & Automation (surgical robots). Despite Healthcare sector, it is NOT in Healthcare & Pharma to avoid sub-theme confusion.

#!/usr/bin/env python3
"""Phase 3-4 assembler for 2026-05-07 DIGEST.

- Reads triage.json + 4 inline subagent verdicts
- Computes Arbiter weighted scores per news_type
- Writes news_logs/2026-05-07_digest.json (5 deep + 10 shallow, schema V2.1)
- Patches sector_intel.json top_catalysts (prepend)
- Patches phase0.json (last_news_update, news_patch_count, macro_backdrop_score, binary_risks)
"""
import json
from pathlib import Path
from datetime import datetime, date

ROOT = Path(__file__).resolve().parent.parent.parent
TRIAGE = ROOT / "news/news_logs/2026-05-07_triage.json"
DIGEST_OUT = ROOT / "news/news_logs/2026-05-07_digest.json"
SECTOR_INTEL = ROOT / "sector/sector_logs/2026-05-07_sector_intel.json"
PHASE0 = ROOT / "sector/sector_logs/phase0.json"
TODAY = "2026-05-07"
NOW_TS = datetime.now().strftime("%Y-%m-%d %H:%M")

# ── Subagent outputs (collected from 4 parallel Stage 2 calls) ──
BULL = {
  "agent": "Bull_Analyst",
  "subagent_isolated": True,
  "per_item": {
    "n001": {"interpretation": "US-Iran 短期停火框架若 48h 內落地，將直接拆除壓在風險資產上的最大地緣定價尾巴。Brent 已先行跌破 $100 反映 peace premium 解除，但股市的 risk-on rotation 才剛啟動：航空 / 消費 / 工業 / EM equities 將迎來 multiple re-rating，VIX 壓縮可釋放 systematic 槓桿回補。Hormuz 通行恢復亦解鎖亞洲 refining margin 與全球 supply chain 正常化，對 cyclicals 是 demand pull-forward 而非僅 cost relief。", "primary_beneficiary_sectors": ["Airlines & Travel", "Consumer Discretionary", "Industrials", "EM Equities", "Transports & Shipping"], "catalyst_type": "sentiment_boost", "impact_score": 4, "time_horizon": "immediate", "confidence": 0.7, "key_assumption": "48h 內具體停火文件或元首級表態，且 Brent 不出現 reversal"},
    "n002": {"interpretation": "AMD Q1 beat + Lisa Su 罕見大幅上修 guidance 直指 hyperscaler bookings 真實落地，這不是估值故事而是 order-book 故事。+16-19% 單日漲幅將觸發 momentum / CTA 加碼與 SOX 二次 breakout，NVDA / AVGO / TSM / ARM 等 AI 供應鏈被同步 re-rate。Lisa Su 解釋 'massive forecast change' 意味 MI300/MI325 已從 sample 進入 production ramp，AI capex cycle 進入第二段擴張，Cloud capex guide-up 將連動跟進。S&P + Nasdaq ATH 證明 breadth 正在補強而非 narrow leadership。", "primary_beneficiary_sectors": ["AI & Semiconductors", "Cloud Infra", "DC REITs", "Power & Utilities (AI)", "Equipment (ASML, AMAT, LRCX)"], "catalyst_type": "demand_increase", "impact_score": 5, "time_horizon": "short_term", "confidence": 0.85, "key_assumption": "AMD guide 上修反映 hyperscaler 真實簽約量；NVDA 5/28 不打臉"},
    "n003": {"interpretation": "Whirlpool 用 'recession-level' 字眼且股價 -20%，從 contrarian 角度是典型 capitulation prints — 公司把所有壞消息一次倒出，常標記近期需求 trough。若 n001 US-Iran 停火 48h 內落地，consumer confidence 重建路徑直接打開，appliance / housing-related demand 將出現 sharp mean reversion。-20% 後 short interest 抬升 + valuation 跌至歷史低位，create 了 short squeeze + value rotation 雙引擎。XHB / ITB / 大型 retailer 反而是 contrarian buy。Whirlpool 的悲觀是 backward-looking 的 Feb-Mar 數據。", "primary_beneficiary_sectors": ["Homebuilders", "Consumer Discretionary deep-value", "Retail (TGT/LOW)", "Building Products"], "catalyst_type": "short_squeeze", "impact_score": 3, "time_horizon": "short_term", "confidence": 0.55, "key_assumption": "Iran 停火確實落地推升 confidence；commentary 是 lagging Feb 數據"},
    "n004": {"interpretation": "EU 仍在 weighs 階段且未進入 final rule-making，最壞情境最快 12-18 個月才落地，眼前對 MSFT / AMZN / GOOG cloud revenue 衝擊近零。反而 sovereign cloud carve-out 將 catalyse 美國 hyperscaler 加速與 SAP / OVH / T-Systems / Deutsche Telekom 合資建構 EU sovereign zones，這是 capex 而非 revenue loss。長期看美國 cybersecurity / hybrid-cloud / data-sovereignty 軟體 (HashiCorp / MongoDB / Snowflake federated) 受惠 — 規範越嚴，分區架構越複雜，越需要美系工具層。對 Oracle Cloud + IBM 也是搶份額契機。", "primary_beneficiary_sectors": ["US Hyperscalers (sovereign capex)", "EU Cloud (OVH, T-Systems)", "Cybersecurity & Data Governance", "Hybrid-Cloud Software"], "catalyst_type": "policy_tailwind", "impact_score": 2, "time_horizon": "mid_term", "confidence": 0.6, "key_assumption": "EU 採 carve-out / partnership 而非 ban；12-18 個月 timeline 給予 hyperscaler 建構 sovereign zone"},
    "n005": {"interpretation": "Chip frenzy goes global 證明 AMD beat 不是孤立事件而是全球 AI capex cycle 同步 inflect — SoftBank +18% (ARM 持股 + AI 投資組合)、Nikkei 63K ATH、Samsung / SK Hynix HBM 新高，這是 HBM3e / HBM4 supply tightness 的全球定價。日本 / 韓國 chip names 補漲意味 US-only 集中度風險被稀釋，breadth 改善才是 sustainable rally 訊號。MarketWatch dot-com 警告反而是反向 indicator — 真正 top 不會有人在敲警鐘。SOX / SOXX / SMH ETF 將吸引被動資金 rotation。", "primary_beneficiary_sectors": ["AI & Semis (Global)", "Memory (Samsung, SK Hynix, MU)", "Equipment (ASML, AMAT, TEL)", "Japanese Tech (SoftBank, Advantest, TEL)"], "catalyst_type": "demand_increase", "impact_score": 4, "time_horizon": "short_term", "confidence": 0.78, "key_assumption": "全球 chip rally 由 HBM/AI 真實 demand 驅動而非 momentum-only"},
  }
}

BEAR = {
  "agent": "Bear_Analyst",
  "subagent_isolated": True,
  "per_item": {
    "n001": {"interpretation": "短期停火協議 24h binary，市場已 price-in oil <$100 與風險溢價收斂。Deal 失敗情境：Hormuz 48h live-fire 同步惡化 → Brent reversal +$10-15 (15-18%)，能源/航空/消費反向 shock；即使 deal 成功也只是 short-term ceasefire，根本性對抗未解 → 任何二度升溫將觸發更劇烈 unwind（市場已無 buffer）。Whirlpool n003 已驗證消費端被 Iran 衝擊，deal 失敗 = 衰退式破壞延伸。CTA/系統性 fund 對能源 long unwind 已過度，反向 squeeze 風險高。", "primary_at_risk_sectors": ["airlines","consumer_discretionary","transportation","industrials","semis_via_risk_off"], "risk_type": "cost_increase", "impact_score": -3, "time_horizon": "immediate", "confidence": 0.7, "key_assumption": "24h binary 失敗機率 ≥30%；Brent +$10-15 在 1-3 日內，risk-off spillover -2~-3.5%", "binary_risk": True},
    "n002": {"interpretation": "AMD +16-19% 單日 + SOX 推升大盤至 ATH 是典型 blow-off top 訊號。Hyperscaler-tied guidance 反映 capex 集中度極高 (MSFT/META/GOOGL/AMZN) → 任一 hyperscaler capex guide-down (下次財報季) 將同步引爆。AMD 估值已 price-in 完美執行，beat 後 +19% 意味 sentiment 已透支未來 2-3 季 surprise。MW 'dot-com warning' 與此同步出現非偶然 — 2000 年 3 月 Nasdaq ATH 後 18 個月 -78%。Concentration risk: top 10 stocks 佔 S&P >35%，AI 主題 unwind 將拖累指數遠超個股。", "primary_at_risk_sectors": ["semiconductors","ai_hyperscalers","tech_megacap","sox"], "risk_type": "sentiment_crash", "impact_score": -3, "time_horizon": "mid_term", "confidence": 0.6, "key_assumption": "Hyperscaler capex 在 2026 H2 出現 guide-down 機率 ≥35%"},
    "n003": {"interpretation": "Whirlpool -20% + 'recession-level industry decline' 直接 quote 是極重要 leading indicator。家電是消費耐久財最 cyclical 的指標，此處崩跌等同 2008 早期警訊。Quote 明示 consumer confidence 'collapsed in late February and March' — 已是過去式，意味 Q1 GDP 數據將顯著低於預期。傳染路徑：(1) 同類 HD/LOW/WHR/MAS 同步壓力；(2) 信用卡/auto loan delinquency 上行；(3) 銀行 (regional) loan loss provision 提高；(4) 整體 consumer discretionary -8 至 -12% over 2-4 weeks。市場仍在 ATH 表示未 price-in 此 signal — gap 將靠股市下修補回。", "primary_at_risk_sectors": ["consumer_discretionary","home_builders","appliances","regional_banks","retail"], "risk_type": "demand_destruction", "impact_score": -4, "time_horizon": "short_term", "confidence": 0.8, "key_assumption": "Whirlpool 訊號代表整體耐久財 demand collapse；2-4 週內 peer downgrade wave 機率 ≥65%"},
    "n004": {"interpretation": "EU 雖在 weighs 階段，但方向已確立 — 政策 headwind 一旦啟動極少回頭。MSFT Azure / GOOGL GCP / AMZN AWS 在歐洲 sovereign workload 收入估 8-15% global cloud rev，此塊 carve-out 將被 OVH/Deutsche Telekom/Atos 取代。更關鍵的是示範效應：英國/加拿大/澳洲/日本可能跟進，digital sovereignty 已成全球趨勢。長期 TAM 壓縮 + margin 下行（sovereign cloud 須在地化部署成本高）。當下市場給予 hyperscaler 25-30x forward EBITDA，任何 TAM 受損將觸發 multiple compression。配合 n002 AMD blow-off，雙重壓力。", "primary_at_risk_sectors": ["us_hyperscalers","cloud_software","cybersecurity","tech_megacap"], "risk_type": "policy_headwind", "impact_score": -2, "time_horizon": "mid_term", "confidence": 0.55, "key_assumption": "EU 草案 6-9 個月內成形機率 ≥50%；其他西方國家跟進機率 ≥40%"},
    "n005": {"interpretation": "MarketWatch 公開使用 'dot-com' 比喻 + Nikkei 63K ATH + SoftBank +18% + Samsung/SK Hynix new highs = 教科書級 global FOMO blow-off。歷史對照：2000/3 Nasdaq peak 前 3 個月日經同步飆升、半導體 ROE 與 capex 同步走高 — 之後 SOX -85%。下行 path 量化：(1) 短期 1-3 週：任何負面催化 → SOX -8 至 -12%；(2) 中期 3-6 月：若 AI ROI 質疑浮現 (GS、MS 報告 hint)，SOX -20 至 -30%；(3) 極端：dot-com 2.0 → 18 個月 -50%+。當前 chip frenzy 廣度過寬 = 賣方耗盡，無新 marginal buyer。", "primary_at_risk_sectors": ["semiconductors","sox","nikkei_tech","softbank","ai_capex_chain"], "risk_type": "sentiment_crash", "impact_score": -4, "time_horizon": "short_term", "confidence": 0.65, "key_assumption": "Global chip frenzy breadth 觸頂；3-8 週內 -10% 以上回檔機率 ≥55%"},
  }
}

SECTOR = {
  "agent": "Sector_Analyst",
  "subagent_isolated": True,
  "per_item": {
    "n001": {"primary_sectors": [{"sector": "Energy (Oil & Gas)", "direction": "bearish", "magnitude": "moderate"}, {"sector": "Airlines / Transports", "direction": "bullish", "magnitude": "moderate"}, {"sector": "Defense", "direction": "bearish", "magnitude": "weak"}, {"sector": "Consumer Discretionary (Travel)", "direction": "bullish", "magnitude": "moderate"}], "supply_chain_impact": "Brent <$100 prices in deal success; if deal holds → jet fuel cracks compress (DAL/UAL/AAL margin relief, jet fuel +56% YoY headwind reverses) → airline capacity restoration → aerospace aftermarket (RTX/HON) demand. Upstream: shale E&P (XOM/CVX/COP/EOG) capex peaks, OFS (SLB/HAL) backlog softens. 2nd-order: lower energy CPI → discretionary tailwind (CCL/RCL, MAR/HLT). Cancel: defense (LMT/NOC/RTX) backlog bookings slow if Hormuz de-escalates. Asymmetric 24h binary — failure flips signs with +$10-15 oil shock.", "tickers_mentioned": ["XOM","CVX","COP","EOG","SLB","HAL","DAL","UAL","AAL","LMT","RTX","NOC","CCL","RCL"], "impact_score": -2, "confidence": 0.55},
    "n002": {"primary_sectors": [{"sector": "Semiconductors (AI Compute)", "direction": "bullish", "magnitude": "strong"}, {"sector": "Semicap Equipment", "direction": "bullish", "magnitude": "strong"}, {"sector": "DC Infra (Power/Cooling/Optics)", "direction": "bullish", "magnitude": "strong"}, {"sector": "Hyperscaler Cloud", "direction": "bullish", "magnitude": "moderate"}], "supply_chain_impact": "AMD MI-series beat re-rates entire AI accelerator TAM (no longer NVDA monopoly story) → 1st: AMD/NVDA/AVGO custom-silicon orderbook expands. 2nd: CoWoS / advanced packaging at TSM tight (sold-out 2027) → ASML EUV / High-NA push-out demand, KLAC/AMAT/LRCX WFE upcycle extends. 3rd: HBM tightness → MU/Samsung/SK Hynix HBM3E pricing power (corroborated by n005). 4th: DC power densification → VRT (liquid cooling), ETN/PWR (grid), COHR (1.6T optical), CIEN/AVGO (DCI). Hyperscaler MSFT/META/GOOGL/AMZN capex revisions higher.", "tickers_mentioned": ["AMD","NVDA","AVGO","ARM","TSM","ASML","MU","COHR","VRT","KLAC","AMAT","LRCX","CIEN","ETN","PWR","MSFT","META","GOOGL","AMZN"], "impact_score": 4, "confidence": 0.85},
    "n003": {"primary_sectors": [{"sector": "Consumer Discretionary (Durables)", "direction": "bearish", "magnitude": "strong"}, {"sector": "Home Improvement Retail", "direction": "bearish", "magnitude": "moderate"}, {"sector": "Homebuilders", "direction": "bearish", "magnitude": "moderate"}, {"sector": "Building Products / HVAC", "direction": "bearish", "magnitude": "moderate"}], "supply_chain_impact": "WHR -20% recession-language is a leading-indicator data point for big-ticket durable demand collapse triggered by Iran-war Feb-Mar consumer-confidence shock. 1st: peer appliance OEMs (Electrolux, LG) and HVAC (LII/AOS/WSO) face same demand destruction. 2nd: HD/LOW big-ticket SSS deteriorates → housing-related discretionary (HD/LOW/FND/WSM/RH) earnings risk. 3rd: homebuilders (DHI/LEN/PHM/TOL) buyer-traffic compresses → cyclical materials (cement, lumber WY). 4th: bank consumer-credit (SYF/COF) appliance financing volume drops, credit losses tick up. Cancel: macro n001 deal could partially reverse confidence shock but durable-goods cycle damage sticky 2-3 quarters.", "tickers_mentioned": ["WHR","LII","AOS","WSO","HD","LOW","FND","WSM","RH","DHI","LEN","PHM","TOL","WY","SYF","COF"], "impact_score": -3, "confidence": 0.7},
    "n004": {"primary_sectors": [{"sector": "US Hyperscaler Cloud", "direction": "bearish", "magnitude": "moderate"}, {"sector": "EU Sovereign Cloud", "direction": "bullish", "magnitude": "moderate"}, {"sector": "Cybersecurity (data-residency)", "direction": "bullish", "magnitude": "weak"}, {"sector": "EU Telecom / Datacenter", "direction": "bullish", "magnitude": "weak"}], "supply_chain_impact": "EU restricting Azure/AWS/GCP for sensitive govt → 1st: MSFT/AMZN/GOOGL EMEA government segment revenue (low-single-digit % of cloud rev, high-margin) at risk. 2nd: EU sovereign players benefit — OVH (OVHcloud), Deutsche Telekom T-Systems, Atos, Capgemini, SAP (Sovereign Cloud JV with MS). 3rd: data-residency cybersec → Thales, local SIEM/SASE; partial bleed to ZS/CRWD. 4th: EU datacenter colo (EQIX EMEA, DLR) ambiguous. Cancel: AI compute (n002) keeps US hyperscaler capex robust globally — regional revenue mix shift, not absolute hyperscaler bear thesis.", "tickers_mentioned": ["MSFT","AMZN","GOOGL","SAP","OVH.PA","ATO.PA","CAP.PA","HO.PA","EQIX","DLR","ZS","CRWD"], "impact_score": -2, "confidence": 0.55},
    "n005": {"primary_sectors": [{"sector": "Asian Semis", "direction": "bullish", "magnitude": "strong"}, {"sector": "Memory (HBM/DRAM/NAND)", "direction": "bullish", "magnitude": "strong"}, {"sector": "Japanese Tech / Semicap", "direction": "bullish", "magnitude": "strong"}, {"sector": "Chip Equipment (Asia)", "direction": "bullish", "magnitude": "moderate"}], "supply_chain_impact": "Asia chip rally is direct piggyback on n002 AMD beat — confirms global re-rating not US-only. 1st: SoftBank +18% (ARM stake mark-to-market + Stargate optionality), Samsung/SK Hynix new highs validate HBM tightness. 2nd: Japanese semicap (Tokyo Electron, Advantest, Disco, Lasertec) — Advantest is HBM tester monopoly, direct AMD/NVDA volume beneficiary. 3rd: Taiwan substrate / ABF / OSAT (Unimicron, ASE/AMKR) downstream packaging tightens. 4th: Korean equipment (Hanmi Semi TC-Bonder for HBM stacking) inflects. Currency: yen weakness amplifies Japanese semicap export earnings.", "tickers_mentioned": ["9984.T","005930.KS","000660.KS","8035.T","6857.T","6146.T","6920.T","ARM","TSM","AMKR","ASX"], "impact_score": 3, "confidence": 0.8},
  }
}

MACRO = {
  "agent": "Macro_Analyst",
  "subagent_isolated": True,
  "per_item": {
    "n001": {"fed_path_delta": "Hawkish-leaning if deal holds — removes oil supply-shock tail, allows Fed to lean into productivity-disinflation narrative; pushes first cut risk later (Sep→Dec). Deal failure flips Fed to defensive hold (stagflation handcuff).", "yield_curve_impact": "Deal success: 2s anchored, 10s +5-10bp, mild bear-steepener. Deal failure: 2s -15bp on growth scare, 10s flat-down on flight-to-quality, bull-steepening.", "fx_commodity_impact": "Deal: USD weaker (-0.5% DXY), Brent -$8 to mid-$80s, gold -$40, EUR/JPY firmer. Failure: Brent +$10-15 to $105+, gold +$60, DXY +1%, JPY outperforms.", "historical_analogue": "2003 Q1 Iraq invasion ceasefire-rumor cycles — every 'deal close' headline saw oil -5% / equities +2% then reversal on collapse; final resolution required ground facts not framework language.", "impact_score": 3, "confidence": 0.55, "binary_risk": True},
    "n002": {"fed_path_delta": "Marginally hawkish — equity ATH + AI capex acceleration tightens financial conditions in reverse (wealth effect), reduces Fed cut urgency; reinforces Goolsbee productivity-front-running warning.", "yield_curve_impact": "Bear-steepener bias: 2s sticky, 10s +5-8bp on growth/term-premium re-rating. Real yields drift higher.", "fx_commodity_impact": "USD firm on growth differential, JPY weak (BoJ patience), copper/silver bid on AI infra, Brent neutral, gold capped.", "historical_analogue": "1999 Q3-Q4 dot-com final melt-up — Nasdaq +30% in 4 months on productivity-miracle narrative while Fed (Greenspan) hiked into it; rally extended 6+ months past first bubble warning before March 2000 peak.", "impact_score": 3, "confidence": 0.7},
    "n003": {"fed_path_delta": "Dovish pull — durable goods recession-level print is exactly the K-shaped weakness that gives doves (Goolsbee/Daly) cover to argue cut sooner. Pulls first cut risk earlier (Sep back on table) if confirmed by housing/auto data.", "yield_curve_impact": "Bull-steepener: 2s -8 to -12bp on cut repricing, 10s flat-down on growth concern. Curve dis-inverts further.", "fx_commodity_impact": "USD softer on growth scare (-0.4% DXY), Brent neutral, gold +1%, copper weak, JPY/CHF bid.", "historical_analogue": "2007 Q3-Q4 Whirlpool/housing-adjacent durable warnings — early canary for consumer recession; market initially dismissed as idiosyncratic, validated 6 months later.", "impact_score": -3, "confidence": 0.6},
    "n004": {"fed_path_delta": "No direct Fed impact short-term; medium-term marginally hawkish via deglobalization premium (capex duplication, sticky services inflation in tech).", "yield_curve_impact": "Negligible near-term. Medium-term: term-premium support on fragmentation/duplicated capex thesis; 10s +2-4bp drift over months.", "fx_commodity_impact": "EUR neutral-to-firm on sovereignty premium, USD slightly soft on reserve-currency erosion narrative (slow burn), no commodity impact.", "historical_analogue": "2018-2019 Huawei/5G fragmentation precedent — initial market reaction muted, compounded over 24 months into capex duplication and structural margin headwind.", "impact_score": -1, "confidence": 0.55},
    "n005": {"fed_path_delta": "Hawkish-leaning globally — BoJ gets cover to normalize on Nikkei strength; Fed marginally hawkish on AI capex sustaining nominal GDP. Reinforces productivity-overshoot Goolsbee warning.", "yield_curve_impact": "Global bear-steepener: JGB 10s pressured higher (BoJ exit risk), Bund/UST 10s drag higher in sympathy +3-6bp; 2s anchored.", "fx_commodity_impact": "JPY weak despite Nikkei rally (carry trade extension), KRW/TWD firm, copper/silver bid, Brent neutral, gold capped.", "historical_analogue": "1999-2000 Y2K + telecom/semi global capex synchronization — SOX +180% in 12 months pre-peak, Nikkei mini-bubble, parabola can run 3-6 more months before breaking.", "impact_score": 3, "confidence": 0.65},
  }
}

# ── News-type weights (Bull, Bear, Sector, Macro) ──
WEIGHTS = {
    "monetary_policy": (0.15, 0.15, 0.20, 0.50),
    "macro_data":      (0.15, 0.15, 0.20, 0.50),
    "geopolitical":    (0.15, 0.30, 0.15, 0.40),
    "earnings":        (0.25, 0.25, 0.40, 0.10),
    "corporate":       (0.25, 0.25, 0.40, 0.10),
    "sector_news":     (0.20, 0.20, 0.50, 0.10),
    "sentiment":       (0.30, 0.30, 0.15, 0.25),
    "default":         (0.25, 0.25, 0.25, 0.25),
}

# ── Per-deep-item Arbiter logic ──
DEEP_META = {
    "n001": {"binary_risk": True, "binary_event_date": "2026-05-08", "within_48h": True,
             "verdict": "BINARY",
             "reasoning_extra": "Geopolitical 權重 Bull15/Bear30/Sector15/Macro40。四方分數 Bull +4 / Bear -3 / Sector -2 / Macro +3，加權 +0.6。Bull/Macro 看 deal 成功路徑 (sentiment_boost、historical 2003 Q1)；Bear/Sector 強調失敗反向情境 (Brent +$10-15、jet fuel +56%、DAL/UAL margin)。|max-min|=7 ≥4 + within_48h binary → 強制 verdict=BINARY，淨分值僅供參考。Macro 主導採納（40%）：Fed 路徑由 deal 結果決定 (success → hawkish, failure → stagflation handcuff)。",
             "debate_note": "Bull immediate sentiment_boost vs Bear cost_increase reversal — 24h binary 的 deal 失敗機率仍 ≥30%；資產 already priced in success",
             "primary_tickers": ["DAL","UAL","AAL","XOM","CVX","CCL","LMT","RTX"],
             "affected_sectors_final": [
                 {"sector": "Energy", "direction": "binary"},
                 {"sector": "Airlines", "direction": "binary"},
                 {"sector": "Defense", "direction": "binary"},
                 {"sector": "Consumer Discretionary", "direction": "binary"},
             ]},
    "n002": {"binary_risk": False, "binary_event_date": None, "within_48h": False,
             "verdict": "BULLISH",
             "reasoning_extra": "Earnings 權重 Bull25/Bear25/Sector40/Macro10。四方 Bull +5 / Bear -3 / Sector +4 / Macro +3，加權 +2.4。|max-min|=8 但分歧為時間軸（Bull/Sector 看 short_term capex inflection；Bear 看 mid_term blow-off）非 binary 事件，故維持 BULLISH。Sector 主導（40%）— 4 階供應鏈受惠覆蓋全面 (TSM CoWoS → ASML EUV → MU HBM → VRT/ETN power)，連動 n005 全球 chip frenzy 形成自我強化。Bear 1999 dot-com 類比保留作中期 re-evaluate condition。",
             "debate_note": "短期 capex demand_increase vs 中期 sentiment_crash blow-off top — top 10 stocks 佔 S&P >35%、AI 主題 unwind 將拖累指數",
             "primary_tickers": ["AMD","NVDA","AVGO","TSM","ASML","MU","VRT","COHR"],
             "affected_sectors_final": [
                 {"sector": "Semi", "direction": "bullish"},
                 {"sector": "Semi-equip", "direction": "bullish"},
                 {"sector": "DC Infra", "direction": "bullish"},
                 {"sector": "Cloud", "direction": "bullish"},
             ]},
    "n003": {"binary_risk": False, "binary_event_date": None, "within_48h": False,
             "verdict": "BEARISH",
             "reasoning_extra": "Corporate 權重 Bull25/Bear25/Sector40/Macro10。四方 Bull +3 / Bear -4 / Sector -3 / Macro -3，加權 -1.75。|max-min|=7 但分歧為觀點（Bull 看 capitulation 反轉，Bear/Sector/Macro 三方看 leading indicator）。三家收斂 BEARISH 採納；Sector 主導（40%）— 4 階傳染 (WHR → HD/LOW SSS → DHI/LEN buyer traffic → 區域銀行信貸質量)。Macro 2007 Q3 housing 早期警訊類比強化 leading-indicator 解讀。",
             "debate_note": "Bull short_squeeze 反轉 vs Bear/Sector/Macro 三方 leading indicator — 'recession-level' 直接 quote 是極罕見措辭",
             "primary_tickers": ["WHR","HD","LOW","DHI","LEN","SYF","COF","RH"],
             "affected_sectors_final": [
                 {"sector": "Consumer Discretionary", "direction": "bearish"},
                 {"sector": "Homebuilders", "direction": "bearish"},
                 {"sector": "Building Products", "direction": "bearish"},
                 {"sector": "Regional Banks", "direction": "bearish"},
             ]},
    "n004": {"binary_risk": False, "binary_event_date": None, "within_48h": False,
             "verdict": "BEARISH",
             "reasoning_extra": "Geopolitical 權重 Bull15/Bear30/Sector15/Macro40。四方 Bull +2 / Bear -2 / Sector -2 / Macro -1，加權 -1.0。|max-min|=4 邊界，方向收斂 BEARISH light。Macro 主導（40%）— 2018-2019 Huawei/5G 類比，slow-bleed 結構性 margin headwind。Sector 受影響但 Bull policy_tailwind 部分對沖（sovereign zone capex 反帶動 hyperscaler）。中期 mid_term，估值 25-30x EBITDA 任何 TAM 受損將 trigger compression。",
             "debate_note": "短期僅 weighs 階段（Bull）vs 政策方向已確立 + 全球示範效應（Bear/Macro）",
             "primary_tickers": ["MSFT","AMZN","GOOGL","SAP","ORCL","IBM","ZS","CRWD"],
             "affected_sectors_final": [
                 {"sector": "US Hyperscaler", "direction": "bearish"},
                 {"sector": "EU Sovereign Cloud", "direction": "bullish"},
                 {"sector": "Cybersecurity", "direction": "bullish"},
             ]},
    "n005": {"binary_risk": False, "binary_event_date": None, "within_48h": False,
             "verdict": "BULLISH",
             "reasoning_extra": "Sector_news 權重 Bull20/Bear20/Sector50/Macro10。四方 Bull +4 / Bear -4 / Sector +3 / Macro +3，加權 +1.8。|max-min|=8 但分歧時間軸不同（Bull/Sector 看當下 breadth 改善 + HBM 真實 demand；Bear 看 dot-com 類比 18 個月路徑）。Sector 主導（50%）— Japanese semicap (Advantest HBM monopoly) + Korean memory + Taiwan OSAT 多階受惠，與 n002 形成共振，支持 BULLISH。Macro 1999-2000 類比認同 parabola 仍可運行 3-6 個月。Bear sentiment_crash 條件式（任一 hyperscaler capex 雜訊）保留作 watch trigger。",
             "debate_note": "全球 capex breadth 改善 (Bull/Sector) vs 教科書 blow-off + 廣度過寬 = 賣方耗盡 (Bear) — top vs middle of 1999 是關鍵 frame",
             "primary_tickers": ["AMD","NVDA","TSM","ASML","9984.T","005930.KS","000660.KS","8035.T","6857.T"],
             "affected_sectors_final": [
                 {"sector": "Semi (Global)", "direction": "bullish"},
                 {"sector": "Memory", "direction": "bullish"},
                 {"sector": "Japanese Tech", "direction": "bullish"},
                 {"sector": "Chip Equipment", "direction": "bullish"},
             ]},
}


def calc_net(b, br, s, m, news_type):
    w = WEIGHTS.get(news_type, WEIGHTS["default"])
    val = b * w[0] + br * w[1] + s * w[2] + m * w[3]
    return round(val, 1)


# ── Build digest verdicts ──
triage = json.load(open(TRIAGE))
shallow_in = triage["shallow_verdicts"]
deep_ids = set(triage["advanced_ids"])

deep_verdicts = []
shallow_verdicts = []
session_macro_delta = 0.0

for sv in shallow_in:
    nid = sv["news_id"]
    if nid in deep_ids:
        meta = DEEP_META[nid]
        bull_per = BULL["per_item"][nid]
        bear_per = BEAR["per_item"][nid]
        sec_per  = SECTOR["per_item"][nid]
        mac_per  = MACRO["per_item"][nid]

        net = calc_net(bull_per["impact_score"], bear_per["impact_score"],
                       sec_per["impact_score"], mac_per["impact_score"],
                       sv["news_type"])
        session_macro_delta += net * 0.1  # crude delta accumulation

        # Build full deep view fields
        bull_text = bull_per["interpretation"] + " (catalyst=" + bull_per["catalyst_type"] + f", impact +{bull_per['impact_score']}, conf={bull_per['confidence']:.2f})"
        bear_text = bear_per["interpretation"] + " (risk=" + bear_per["risk_type"] + f", impact {bear_per['impact_score']}, conf={bear_per['confidence']:.2f})"
        sector_text = "Primary: " + ", ".join(f"{p['sector']} {p['direction']}/{p['magnitude']}" for p in sec_per["primary_sectors"]) + ". Supply chain: " + sec_per["supply_chain_impact"]
        macro_text = (
            f"Fed: {mac_per['fed_path_delta']} | Curve: {mac_per['yield_curve_impact']} | "
            f"FX/Cmdty: {mac_per['fx_commodity_impact']} | Analogue: {mac_per['historical_analogue']}"
        )

        # Merge tickers
        all_tickers = set(sec_per["tickers_mentioned"]) | set(meta["primary_tickers"])
        all_tickers = sorted(all_tickers)

        arbiter_reasoning = (
            f"news_type={sv['news_type']} 權重套用 → "
            f"Bull {bull_per['impact_score']:+d} × {WEIGHTS[sv['news_type']][0]:.2f} + "
            f"Bear {bear_per['impact_score']:+d} × {WEIGHTS[sv['news_type']][1]:.2f} + "
            f"Sector {sec_per['impact_score']:+d} × {WEIGHTS[sv['news_type']][2]:.2f} + "
            f"Macro {mac_per['impact_score']:+d} × {WEIGHTS[sv['news_type']][3]:.2f} = {net:+.1f}. "
            + meta["reasoning_extra"]
        )

        deep_verdicts.append({
            "news_id": nid,
            "depth": "deep",
            "review_status": "reviewed",
            "headline": sv["headline"],
            "headline_zh": sv["headline"],  # placeholder; not separately translated
            "url": sv["url"],
            "published": sv["published"],
            "source_label": sv["source"],
            "source_credibility": sv["source_credibility"],
            "news_type": sv["news_type"],
            "bull_case": bull_text,
            "bear_case": bear_text,
            "sector_view": sector_text,
            "macro_view": macro_text,
            "verdict": meta["verdict"],
            "net_impact_score": net,
            "arbiter_reasoning": arbiter_reasoning,
            "debate_note": meta["debate_note"],
            "binary_risk": meta["binary_risk"],
            "binary_event_date": meta["binary_event_date"],
            "within_48h": meta["within_48h"],
            "cache_updated": True,
            "affected_sectors": meta["affected_sectors_final"],
            "tickers_mentioned": all_tickers,
            "subagent_isolated": True,
            "weights_used": dict(zip(["bull","bear","sector","macro"], WEIGHTS[sv["news_type"]])),
        })
    else:
        shallow_verdicts.append({
            "news_id": nid,
            "depth": "shallow",
            "review_status": "reviewed",
            "headline": sv["headline"],
            "headline_zh": sv["headline"],
            "url": sv["url"],
            "published": sv["published"],
            "source_label": sv["source"],
            "source_credibility": sv["source_credibility"],
            "news_type": sv["news_type"],
            "bull_case": sv["bull_case"],
            "bear_case": sv["bear_case"],
            "sector_view": sv["sector_view"],
            "macro_view": sv["macro_view"],
            "verdict": None,
            "net_impact_score": sv["shallow_score"],
            "arbiter_reasoning": "",
            "debate_note": None,
            "binary_risk": sv["binary_flag"],
            "binary_event_date": None,
            "within_48h": False,
            "cache_updated": False,
            "affected_sectors": [],
            "tickers_mentioned": [],
            "subagent_isolated": None,
        })

# Cap shallow at top 10 for digest.json
shallow_top10 = sorted(shallow_verdicts, key=lambda v: abs(v["net_impact_score"]), reverse=True)[:10]

digest = {
    "timestamp": NOW_TS,
    "mode": "DIGEST",
    "stage1_count": len(shallow_in),
    "stage2_count": len(deep_verdicts),
    "fanout_mode": "PER_AGENT_BATCH",
    "degraded_agents": [],
    "verdicts": deep_verdicts + shallow_top10,
    "session_macro_delta": round(session_macro_delta, 2),
}

DIGEST_OUT.write_text(json.dumps(digest, ensure_ascii=False, indent=2))
print(f"WROTE {DIGEST_OUT}  size={DIGEST_OUT.stat().st_size}B  deep={len(deep_verdicts)} shallow={len(shallow_top10)}")
print(f"  session_macro_delta = {digest['session_macro_delta']}")

# ── Phase 4 — patch sector_intel.json ──
si = json.load(open(SECTOR_INTEL))
top_cats = si.get("top_catalysts", []) or []
new_cats = []
for d in deep_verdicts:
    direction = "bullish" if d["verdict"] == "BULLISH" else ("bearish" if d["verdict"] == "BEARISH" else ("binary" if d["verdict"] == "BINARY" else "neutral"))
    timing = "within_48h" if d["within_48h"] else ("this_week" if abs(d["net_impact_score"]) >= 1.5 else "beyond")
    impact_mapped = max(1, min(5, round(abs(d["net_impact_score"]))))
    new_cats.append({
        "rank": len(new_cats) + 1,  # will recalc after merge
        "event": d["headline"],
        "type": d["news_type"],
        "impact_score": impact_mapped,
        "affected_sectors": [s["sector"] for s in d["affected_sectors"]],
        "direction": direction,
        "timing": timing,
        "source": "news_protocol_v2",
        "updated_at": NOW_TS,
        "news_id": d["news_id"],
    })
si["top_catalysts"] = new_cats + top_cats
# recalc ranks
for i, c in enumerate(si["top_catalysts"], start=1):
    c["rank"] = i
SECTOR_INTEL.write_text(json.dumps(si, ensure_ascii=False, indent=2))
print(f"PATCHED {SECTOR_INTEL}  top_catalysts={len(si['top_catalysts'])} (prepended {len(new_cats)})")

# ── Phase 4 — patch phase0.json ──
p0 = json.load(open(PHASE0))
p0["last_news_update"] = NOW_TS
p0["news_patch_count"] = int(p0.get("news_patch_count", 0)) + 1
prev = float(p0.get("macro_backdrop_score", 0.0))
new_score = round(prev + digest["session_macro_delta"], 2)
new_score = max(-1.0, min(1.0, new_score))
p0["macro_backdrop_score"] = new_score

# binary_risks: drop expired (today > expires) + add Iran deal binary if not present
today = date.fromisoformat(TODAY)
br = []
for r in p0.get("binary_risks", []):
    exp = r.get("expires")
    if exp:
        try:
            if date.fromisoformat(exp) >= today:
                br.append(r)
            else:
                pass  # expired
        except ValueError:
            br.append(r)
    else:
        br.append(r)

# Add new from this run's deep verdicts that are within_48h binary
for d in deep_verdicts:
    if d["binary_risk"] and d["within_48h"]:
        if not any("Iran" in r.get("event", "") and "deal" in r.get("event", "").lower() for r in br):
            br.append({
                "event": d["headline"],
                "category": d["news_type"],
                "within_48h": True,
                "expires": d["binary_event_date"] or "2026-05-08",
                "added": NOW_TS,
            })
p0["binary_risks"] = br
PHASE0.write_text(json.dumps(p0, ensure_ascii=False, indent=2))
print(f"PATCHED {PHASE0}  macro_backdrop_score: {prev:+.2f} → {new_score:+.2f} (Δ={digest['session_macro_delta']:+.2f}); binary_risks={len(br)}")

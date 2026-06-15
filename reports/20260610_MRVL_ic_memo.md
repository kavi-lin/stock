# MRVL (Marvell Technology, Inc.) — IC Memo

- **Date**: 2026-06-10
- **Live Spot**: $266.88 | 52w: $61.44 – $324.2
- **Analysis Price**: $289.77 (protocol session 2026-06-08)
- **Market Cap**: $233.47B
- **Sector / Industry**: Technology / Semiconductors
- **Final Action**: **CANCEL** | Verdict: extreme_overvalued | FV $37.89 (-86.92% vs analysis; -85.80% vs live)
- **Source**: investment_protocol V5.0 session 2026-06-08 | Memo composer V1.0.0

<!-- src: profile.live + protocol.history.phase5 -->

---

## §1 一頁摘要

| Field | Value |
|---|---|
| Final Action | **CANCEL** |
| Confidence | 29% |
| Position Size | 0.00% |
| Entry (aggr / cons) | — / $169.00 - $214.00 |
| Stop Loss | — |
| Take Profit | — |
| Risk/Reward | — |
| Time Horizon | mid |
| Fragility | FRAGILE |

<!-- src: protocol.history.phase5 -->

---

## §2 公司與商業模式

Marvell Technology, Inc., together with its affiliated companies, specializes in the development, engineering, and commercialization of a broad range of integrated circuits. These offerings encompass analog, mixed-signal, digital signal processing, embedded, and standalone chip solutions. The company's product portfolio includes a variety of Ethernet solutions, such as controllers, network adapters, physical layer transceivers, and switches. They also provide single and multi-core processors, application-specific integrated circuits (ASICs), and System-on-a-Chip products for printers, along with application processors. Furthermore, Marvell delivers extensive storage solutions. These consist of controllers for both hard disk drives (HDDs) and solid-state drives (SSDs), designed to support diverse host system interfaces including serial attached SCSI (SAS), serial advanced technology attachment (SATA), peripheral component interconnect express (PCIe), non-volatile memory express (NVMe), and NVMe over fabrics. Their fiber channel product line features host bus adapters and controllers essential for server and storage system connectivity. Marvell maintains operations across numerous international locations, including the United States, China, Malaysia, the Philippines, Thailand, Singapore, India, Israel, Japan, South Korea, Taiwan, and Vietnam. The company was founded in 1995 and is headquartered in Wilmington, Delaware.

- **CEO**: Matthew J. Murphy
- **Employees**: 7,042
- **IPO**: 2000-06-30
- **HQ**: Wilmington, DE, US
- **Website**: https://www.marvell.com

<!-- src: profile.live -->

---

## §3 收入結構與成長驅動

_(資料待補：跑 `財報 <TICKER>` 補 earnings-analyst cache)_

<!-- src: earnings_analyst.cache (MISSING) -->

---

## §4 客戶 / 供應商 / 競爭格局

### Moat

- **Level**: —
- **Type**: —
- **Evidence**: NARROW — custom-silicon/ASIC IP + hyperscaler design-win switching cost（type: IP/switching）

### Peers Comparison

| Ticker | Focus Area | Market Share Note |
|---|---|---|
| FTNT | — | — |
| GLW | — | — |
| INFY | — | — |
| MPWR | — | — |
| MSTR | — | — |
| NET | — | — |
| NXPI | — | — |
| RBLX | — | — |
| SNPS | — | — |
| TEL | — | — |

> _Focus Area / Market Share descriptor 為 V1.0 stub。Phase A.5 將以 Haiku 4.5 batch call 補。_

<!-- src: peers.live_fmp + llm_synth.peer_descriptor (stub) -->

---

## §5 最新財務與申報重點

_(資料待補：跑 `財報 <TICKER>`)_

<!-- src: earnings_analyst.cache (MISSING) -->

---

## §6 資產負債表與現金流品質

_(資料待補：跑 `財報 <TICKER>`)_

<!-- src: earnings_analyst.cache (MISSING) -->

---

## §7 盈利能力與 2-3 年模型

_(資料待補：跑 `財報 <TICKER>`)_

<!-- src: earnings_analyst.cache (MISSING) -->

---

## §8 估值：DCF + Multiples + Analyst PT

### Fair Value 6-Anchor Blend

| Anchor | Value | Weight |
|---|---|---|
| dcf_unlevered | — | — |
| dcf_levered | — | — |
| analyst_pt_consensus | — | — |
| peer_pe_implied | — | — |
| owner_earnings_mult | $37.89 | 100.0% |
| forecaster_blend | — | — |

- **Weighted FV**: $37.89
- **Analysis Price**: $289.77
- **vs Analysis Price**: -86.92% (extreme_overvalued)
- **Live Spot**: $266.88
- **vs Live Spot**: -85.80%
- **Confidence**: low (1/6 anchors)
- **Methodology**: 1/6 anchors usable: owner_earnings_mult only (annualized OE/sh 2.526 × 15 Buffett multiple = $37.89). dcf_unlevered/dcf_levered/analyst_pt_consensus null (no earnings-analyst cache), peer_pe_implied null (peer_pe_median unavailable), forecaster_blend null (forecast.py failed — insufficient PE history). Single static-multiple anchor is structurally unreliable for a high-growth semi; this is NOT a confident fair value, hence confidence=low → triggers decision_cap insufficient_anchors. Do not read $37.89 as a literal price target.

<!-- src: protocol.history.phase4_5 + earnings_analyst.cache.valuation -->

---

## §9 催化劑與風險

### Catalysts

| Date | Type | Impact | Description |
|---|---|---|---|
| 2026-06-10 | macro | negative | May CPI；再加速壓制高倍數半導體 |
| 2026-06-16 | macro | negative | FOMC 點陣圖；限制性 real-rate de-rate 風險 |
| 2026-08-26 | earnings | high | Q2 FY27 財報；AI custom-silicon + datacenter 營收軌跡 |
| 2026-06-26 | macro_event | medium | S&P500 納入正式生效，被動買盤 |

### Cross-Asset Spillover

| Asset | Direction | Mechanism |
|---|---|---|
| sector_SOX_SMH | BULLISH | custom AI-ASIC peer 群（AVGO）連動；半導體板塊反彈同步抬升 |
| AVGO | BULLISH | 同為 custom AI-ASIC，design-win 敘事外溢 |

### Key Risks

- 極端估值：PE 91x / fwdPE 44x / EV/EBIT 85.5，FCF yield 僅 0.98%，RISK_OFF + real_rate 2.1 下 de-rate 風險高。
- 拋物線拉伸：現價高出 MA200 174%、+371% off 52w 低點、+9% 大漲僅 0.32× 量能，MA50 回測潛在 ~-41%。
- 內部人連 3 季淨拋售（acq/disp 0.50）+ 現價高出分析師 PT 共識約 25%，缺有機承接。
- 估值錨點不足：6 取 1（僅 owner-earnings），DCF/PT/peer 皆缺、forecaster 失敗，無法產出可信合理價（decision_cap insufficient_anchors）。
- 6/10 May CPI + 6/16-17 FOMC binary 事件落在 48h 內，波動放大。

**Days to next binary**: 18d

<!-- src: protocol.history.phase2 -->

---

## §10 Bull / Bear / Base case

### Scenario Odds

| Scenario | Odds |
|---|---|
| Bull | 25% |
| Base | 38% |
| Bear | 37% |

### Red Team Counter Thesis

News BUY (+2) 幾乎全押在 S&P500 納入的「強制買盤」一次性機械事件上，但該事件已公告（6 月底生效）、已被市場提前定價，且現價已高出分析師 PT 共識 25%；一旦 index rebalance 買盤消化完畢，需求海綿即抽離，留下 EV/EBIT 85.5、FCF yield 0.98%、fwdPE 44x、174% above MA200、+371% off lows 的極端估值與內部人淨拋售（disposal 0.50），而 +9% 大漲僅 0.32x 量能更證明無有機買盤承接。

### Kill Conditions

- IF MRVL 在 S&P500 正式納入生效後（6 月底）5 個交易日內回吐 ≥10% 且日均量無法維持 >1.0x 均量 WITHIN 10 days THEN 強制買盤=可持續需求 的 News BUY 論點破裂，事件純屬已定價的一次性脈衝。
- IF 6/16-17 FOMC dot plot 在 real_rate_preferred 2.1（>2.0 restrictive）+ CPIAUCSL accelerating 背景下維持或上修限制性路徑、未釋放降息訊號 WITHIN 10 days THEN RISK_OFF（conf 0.9）下高久期成長股折現率假設破裂，fwdPE 44x 無法靠寬鬆續命。
- IF Valuation 補齊 DCF/PT/peer anchor 後 fair_value blend 落在現價下方 >15% WITHIN 21 days THEN 估值僅因 forecaster failed 而暫缺、實際合理 的隱含假設破裂，SELL -3 dissent 獲證實。

<!-- src: protocol.history.red_team -->

---

## §11 委員會結論

> _此章節 verbatim 來自 protocol.history.phase5，受 decision_lock hash 保護。_

### 當下動作

**CANCEL** — HOLD

### 進場計畫

- Entry (aggressive): —
- Entry (conservative): $169.00 - $214.00
- Stop Loss: —
- Take Profit: —
- Position Size: 0.00% (VOL_ADJUSTED)
- Staged Split: —

### Watch / Re-eval 條件

| Trigger | Metric |
|---|---|
| index_inclusion_digest | S&P500 6 月底正式納入生效後 10 日內回吐 ≥10% 且日均量 <1.0×20 日均量 → 一次性指數買盤消化完畢、無有機承接，轉防禦。 |
| macro_rate_watch | 6/16-17 FOMC 點陣圖維持/上修限制性路徑（FRED real_rate 2.1 >2.0 + CPI 加速）→ fwdPE 44x 折現率壓力加劇；10Y 實質利率升破 2.30% 估值進一步承壓。 |
| valuation_reentry | 回測 MA50 ~$169–MA20 $214（-26% 至 -41%）且 DCF/PT/peer valuation anchor 補齊後合理價落於現價下方 <15% → 風險報酬改善才評估試水倉。 |
| volume_confirmation | 突破 $292 阻力需 >1.5×20 日均量確認；無量突破視為 false_breakout。 |
| earnings_watch | 2026-08-26 Q2 FY27 財報：datacenter/custom-ASIC 營收成長 < +25% YoY 或 guidance 下修 → AI re-rate 敘事受損。 |

<!-- src: protocol.history.phase5 (decision-locked) -->

---

## §12 附錄

### Lane Scores

| Lane | Score |
|---|---|
| fundamentals | -1 |
| sentiment | -1.5 |
| news | 2 |
| technical | 1 |
- Decision confidence: 29%

### Provenance Roster

| Source | Type | Path | Meta |
|---|---|---|---|
| profile | profile.live | live:fmp/profile/MRVL | — |
| protocol_history | protocol.history | investment/invest_logs/history.json#entry[142] | session 2026-06-08 |
| earnings_cache | earnings_analyst.cache | — | — |
| peers | peers.shared | _shared/cache/peers/MRVL.json (24h) | n=10 |
| peer_descriptor | llm_synth.peer_descriptor | skills/ic-memo-writer/cache/peer_descriptor/MRVL.json | stub_no_llm |

### Degraded Sections

- sec_3
- sec_5
- sec_6
- sec_7
- sec_4_peer_descriptor_stub
- sec_8_low_confidence

### Validator

- rc: _(not yet run; see compose --validate or run validate_ic_memo.py)_
- decision_lock_hash: `3db5b0229f7aab5f1e1abb08...`
- fact_pack_hash: `67469c0253eb44b871ef5346...`

<!-- src: meta.composed -->

---

*Composed by ic-memo-writer V1.0.0 (deterministic, 0 LLM call) — fact_pack hash 67469c0253eb44b8...*

#!/usr/bin/env python3
"""One-shot Stage 1 triage builder for 2026-05-07 DIGEST.

Reads raw.json, joins manually pre-curated shallow verdicts (by headline keyword)
with raw published/url, emits triage.json with shallow_verdicts sorted by |score|.
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "news_logs" / "2026-05-07_raw.json"
OUT = ROOT / "news_logs" / "2026-05-07_triage.json"

raw = json.load(open(RAW))
items = raw["items"]


def find_kw(keywords):
    """First raw item whose headline contains all keywords (case-insensitive)."""
    kws = [k.lower() for k in keywords]
    for it in items:
        h = it["headline"].lower()
        if all(k in h for k in kws):
            return it
    raise SystemExit(f"NOT FOUND: {keywords}")


CURATED = [
    # ── DEEP-1: US-Iran short-term deal ──
    {"kw": ["us and iran", "short-term deal"], "news_type": "geopolitical",
     "bull": "Brent <$100 priced in、risk-on 廣度延續、週期股加碼", "bear": "已 priced in，deal 失敗 24h binary 反向 oil +$10-15",
     "sector": "Energy 短壓、Airlines/Cruises/Discretionary 受惠、Defense 回吐", "macro": "USD 走弱、長端殖利率回落、Fed 路徑略偏鴿",
     "score": 3.6, "binary": True, "advance": True,
     "reason": "BINARY 48h + HIGH credibility + 主導 macro_backdrop"},

    # ── DEEP-2: AMD-led AI rally / record highs ──
    {"kw": ["amd results spark"], "news_type": "earnings",
     "bull": "AI capex 週期續航明確、DC 訂單確定性、hyperscaler 加碼", "bear": "AMD-only beat、INTC 落後、集中度風險增加",
     "sector": "Semi +strong、Semi-equip +moderate、HBM/Cooling 連動", "macro": "強化美股 outperform，FX 中性",
     "score": 4.0, "binary": False, "advance": True,
     "reason": "earnings 權重 Sector 40% + 史記新高觸發 + |score|≥3"},

    # ── DEEP-3: Whirlpool -20% / 'recession-level' ──
    {"kw": ["whirlpool", "recession-level"], "news_type": "corporate",
     "bull": "個股 idiosyncratic、通膨 cooling 後可能反轉", "bear": "'recession-level' 罕見措辭、Iran 戰爭造成耐久財需求毀壞",
     "sector": "Consumer Cyclical 重災 (Housing/Appliance/Auto)、Industrial 連動下修", "macro": "拉低 Q2 GDP 預估、Goolsbee 警告 productivity 過熱被對沖",
     "score": -3.4, "binary": False, "advance": True,
     "reason": "罕見 'recession-level' 措辭 + 大盤分歧訊號 + |score|≥3"},

    # ── DEEP-4: EU vs US Cloud ──
    {"kw": ["eu weighs", "u.s. cloud"], "news_type": "geopolitical",
     "bull": "目前僅 weighs 階段、落地時程不確定、估值衝擊有限", "bear": "Hyperscaler EMEA 政府部門 revenue 風險、Sovereign Cloud 替代加速",
     "sector": "US Cloud (MSFT/AMZN/GOOGL) 微逆風；EU local cloud (DTE/ATOS) 受惠", "macro": "Tech/SVC 出口逆風但 USD 影響有限",
     "score": -2.6, "binary": False, "advance": True,
     "reason": "HIGH credibility + 大型科技股 sector 衝擊 + 即時性"},

    # ── DEEP-5: Chip frenzy global / Asia tech AI ──
    {"kw": ["morning bid", "chip frenzy"], "news_type": "sector_news",
     "bull": "亞洲晶片 capex 與訂單動能跨區域傳導、硬體鏈 EPS 上修", "bear": "估值極致 (MW 'partying like dot-com')、集中度警訊",
     "sector": "Semi 全面 +strong、Semi-equip +moderate、Cloud +moderate", "macro": "Risk-on 全球同步、JPY 走弱壓力升高",
     "score": 3.2, "binary": False, "advance": True,
     "reason": "跨市場 chip 訊號 + Nikkei 63K 史高 + 與 dot-com 對比警訊"},

    # ── SHALLOW (not advancing) ──
    {"kw": ["maersk", "iran war"], "news_type": "sector_news",
     "bull": "海運運價短壓力可能催動補貨", "bear": "Maersk CEO 預警 Iran 影響更深、shipping 轉向繞行",
     "sector": "Shipping/Logistics 偏空、Aerospace 受 jet-fuel +56% 拖累", "macro": "貿易效率下降、補通膨壓力",
     "score": -2.4, "binary": False, "advance": False},

    {"kw": ["shell tops profit"], "news_type": "corporate",
     "bull": "Energy 高油價推升 Shell EPS、現金流", "bear": "Buyback 砍量 = 對中期油價並不樂觀",
     "sector": "Integrated Oil +moderate (SHEL/XOM/CVX)", "macro": "Brent 結構性轉強的通膨尾巴",
     "score": 1.6, "binary": False, "advance": False},

    {"kw": ["record oil exports"], "news_type": "sector_news",
     "bull": "煉廠 / E&P EPS 受惠 crack spread", "bear": "美國夏季油價零售壓力推升通膨",
     "sector": "Refiners (VLO/MPC/PSX) +strong、Energy E&P 中性", "macro": "Headline CPI 補通膨",
     "score": 1.4, "binary": False, "advance": False},

    {"kw": ["gold and silver", "fog of war"], "news_type": "sector_news",
     "bull": "黃金白銀延續多頭、礦業股利潤擴張", "bear": "若 Iran 和平確認、避險需求快速回吐",
     "sector": "Precious Metals (NEM/GOLD/PAAS) +strong", "macro": "USD 走弱與實質殖利率配合",
     "score": 1.8, "binary": False, "advance": False},

    {"kw": ["nasdaq stocks", "dot-com"], "news_type": "sentiment",
     "bull": "極致動能持續、流入未斷", "bear": "MW 直接點名 dot-com 類比、回檔風險上升",
     "sector": "Mega-cap Tech 動能 stretched", "macro": "Sentiment 過熱訊號",
     "score": -2.0, "binary": False, "advance": False},

    {"kw": ["paul tudor jones", "ai bull"], "news_type": "sentiment",
     "bull": "PTJ 看多 AI 多頭 1-2 年延續、配置仍偏進攻", "bear": "頂部前最後階段警訊",
     "sector": "Tech/AI", "macro": "風險偏好仍 risk-on",
     "score": 2.4, "binary": False, "advance": False},

    {"kw": ["applovin", "ai platform"], "news_type": "corporate",
     "bull": "AI 報表觸發短線洗盤、長線題材未變", "bear": "AppLovin AI Platform earnings 雜訊大、估值反映過頭",
     "sector": "AdTech (APP/TTD/ROKU)", "macro": "AI 純度敘事鬆動",
     "score": -1.4, "binary": False, "advance": False},

    {"kw": ["why arm holdings"], "news_type": "corporate",
     "bull": "ARM IP 授權成長率仍正", "bear": "EPS 不及高預期、NPU 競爭加劇",
     "sector": "Semi (ARM/QCOM/AVGO 連動)", "macro": "AI 邊緣端動能訊號 mixed",
     "score": -1.6, "binary": False, "advance": False},

    {"kw": ["albemarle", "blowout"], "news_type": "earnings",
     "bull": "Albemarle 鋰價見底訊號、業績優於預期", "bear": "鋰庫存仍高、需求復甦尚待 EV 訂單確認",
     "sector": "Lithium / EV materials (ALB/SQM/LIT)", "macro": "風險偏好支持週期回補",
     "score": 2.0, "binary": False, "advance": False},

    {"kw": ["tesla china", "spike 36"], "news_type": "corporate",
     "bull": "Tesla 中國 +36%、高動能延續", "bear": "全球銷量仍未轉正、EU 管制是隱憂",
     "sector": "EV (TSLA/BYD)", "macro": "中美需求差異化",
     "score": 2.2, "binary": False, "advance": False},

    {"kw": ["wegovy pill"], "news_type": "corporate",
     "bull": "Wegovy 口服劑大幅 beat、NVO 重啟動能", "bear": "Lilly 競爭仍強、Wegovy pill 利潤率不確定",
     "sector": "Obesity/GLP-1 (NVO/LLY)", "macro": "Healthcare innovation 多頭",
     "score": 2.6, "binary": False, "advance": False},

    {"kw": ["doordash pops"], "news_type": "earnings",
     "bull": "DoorDash 訂單成長指引上修、平台網路效應穩固", "bear": "高估值仍敏感於 macro",
     "sector": "Internet / Last-Mile (DASH/UBER)", "macro": "消費韌性訊號",
     "score": 2.4, "binary": False, "advance": False},

    {"kw": ["uber pops"], "news_type": "earnings",
     "bull": "Uber bookings 指引高於預期、廣告與 freight 雙引擎", "bear": "燃油價格上行為下季成本壓力",
     "sector": "Mobility / Internet (UBER)", "macro": "服務通膨支撐",
     "score": 2.2, "binary": False, "advance": False},

    {"kw": ["disney pops"], "news_type": "earnings",
     "bull": "Disney streaming + Parks 雙超預期、新 CEO 蜜月期", "bear": "Linear TV 承壓、廣告週期未確認",
     "sector": "Media / Theme Parks (DIS)", "macro": "消費升級支撐",
     "score": 2.6, "binary": False, "advance": False},

    {"kw": ["cvs blows past"], "news_type": "earnings",
     "bull": "CVS 保險與藥房雙領先、指引上修", "bear": "Healthcare cost trend 仍待觀察",
     "sector": "Managed Care / Pharmacy (CVS/UNH)", "macro": "Defensive 韌性",
     "score": 2.4, "binary": False, "advance": False},

    {"kw": ["peloton surges"], "news_type": "corporate",
     "bull": "Peloton subscription 提價成功、Spotify 合作擴大粘性", "bear": "硬體需求疲軟仍是主軸",
     "sector": "Consumer Discretionary (PTON)", "macro": "中性",
     "score": 2.0, "binary": False, "advance": False},

    {"kw": ["mcdonald's earnings", "challenging"], "news_type": "earnings",
     "bull": "MCD 在 challenging environment 下 still beat、價值定位優勢", "bear": "Same-store sales 增速放緩、低收入族群壓力",
     "sector": "Restaurants (MCD/QSR/SBUX)", "macro": "消費分層加劇",
     "score": 1.8, "binary": False, "advance": False},

    {"kw": ["terafab"], "news_type": "corporate",
     "bull": "Terafab $119B chip factory = 美國 onshoring 大箭頭", "bear": "Capex 承諾規模史上少見、執行風險高",
     "sector": "Semi-equip / Power 受惠 (LRCX/AMAT/VRT)", "macro": "Industrial policy 加碼",
     "score": 2.8, "binary": False, "advance": False},

    {"kw": ["snap issues cautious"], "news_type": "corporate",
     "bull": "Snap 廣告營收基本盤穩、預期低反而易超預期", "bear": "Perplexity 合作終止 + Middle East 不確定性",
     "sector": "AdTech (SNAP/META)", "macro": "中性偏空",
     "score": -1.8, "binary": False, "advance": False},

    {"kw": ["warner bros", "2.9 billion"], "news_type": "corporate",
     "bull": "WBD 收益面臨 Paramount 整合的長線綜效", "bear": "$2.9B 重組 charge、現金流短期惡化",
     "sector": "Media (WBD/PARA/DIS)", "macro": "中性",
     "score": -1.6, "binary": False, "advance": False},

    {"kw": ["fed's goolsbee"], "news_type": "monetary_policy",
     "bull": "Goolsbee 偏鴿延續、AI 帶動的生產力改善正面", "bear": "警告 AI 過熱風險、不應 front-run",
     "sector": "Tech/Mega-cap", "macro": "Fed 路徑短期維持耐心",
     "score": 0.8, "binary": False, "advance": False},

    {"kw": ["jobless claims"], "news_type": "macro_data",
     "bull": "Jobless claims 仍低、勞動市場韌性續存", "bear": "資料只是 marginal beat、Fed 短期不急降息",
     "sector": "Cyclical 普遍受惠", "macro": "Risk-on 風偏延續",
     "score": 1.4, "binary": False, "advance": False},

    {"kw": ["private payrolls", "april"], "news_type": "macro_data",
     "bull": "ADP +109k 高於預期、企業仍在補人", "bear": "資料波動大、與 NFP 易出現 divergence",
     "sector": "Consumer / Cyclical 中性偏多", "macro": "Risk-on 訊號之一",
     "score": 1.2, "binary": False, "advance": False},

    {"kw": ["eurozone retail sales"], "news_type": "macro_data",
     "bull": "歐洲零售下滑屬 Iran 短期衝擊、後續可逆", "bear": "Eurozone 增長延伸下行、ECB 壓力增大",
     "sector": "EU Consumer/Banks 偏空", "macro": "EUR 下行風險",
     "score": -1.6, "binary": False, "advance": False},

    {"kw": ["surging gas prices"], "news_type": "macro_data",
     "bull": "高油價拉低低收入家戶支出 = Defensive 韌性", "bear": "通膨/支出受擠壓 → 衰退風險上升",
     "sector": "Consumer Defensive +moderate, Discretionary -moderate", "macro": "K-shaped 復甦警訊",
     "score": -1.2, "binary": False, "advance": False},

    {"kw": ["morgan stanley", "growth forecast"], "news_type": "macro_data",
     "bull": "MS 預估下修是技術性、非結構性", "bear": "Gas prices 抵消 tax refund、Q2 GDP 偏低",
     "sector": "Discretionary/Travel 偏空", "macro": "Stagflation 尾風險升高",
     "score": -2.0, "binary": False, "advance": False},

    {"kw": ["pendulum", "extreme fear to greed"], "news_type": "sentiment",
     "bull": "Cycle 末段 fear→greed pendulum 對 risk asset 仍正", "bear": "Sentiment 過熱倒置 contrarian 訊號",
     "sector": "整體股市 stretched", "macro": "Sentiment 警訊",
     "score": -1.4, "binary": False, "advance": False},

    {"kw": ["what's at stake", "trump-xi"], "news_type": "geopolitical",
     "bull": "Trump-Xi 期待破冰、KWEB/FXI 已 priced in tariff truce", "bear": "失敗則 Asia 出口股 -8~12%",
     "sector": "China ADR / Semi 高 beta", "macro": "BINARY 高 stakes",
     "score": -2.0, "binary": True, "advance": False,
     "reason": "BINARY 但 expires 2026-06-15、超出 48h 窗口"},

    {"kw": ["china's shift to electric trucks"], "news_type": "geopolitical",
     "bull": "Iran 影響 EV truck 加速電化轉型 (TSLA/BYD)", "bear": "全球供應鏈再洗牌、補通膨壓力",
     "sector": "EV trucks +moderate, Diesel -moderate", "macro": "結構轉型加速",
     "score": 1.4, "binary": False, "advance": False},

    {"kw": ["wall street banks", "capital rules"], "news_type": "sector_news",
     "bull": "Wall St banks 推動最終資本規則、IB 業績受惠", "bear": "Capital rules 再放鬆對長線金融穩定的隱憂",
     "sector": "Financial (JPM/GS/MS) +moderate", "macro": "Pro-cyclical",
     "score": 1.6, "binary": False, "advance": False},

    {"kw": ["trump says", "very good talks"], "news_type": "geopolitical",
     "bull": "Trump 表態正向強化 24h binary 上行", "bear": "外交 noise 易反覆",
     "sector": "Risk-on 普遍受惠", "macro": "USD 偏弱",
     "score": 2.0, "binary": True, "advance": False,
     "reason": "已被 DEEP-1 涵蓋"},

    {"kw": ["jet-fuel prices are spiking"], "news_type": "corporate",
     "bull": "高燃料價格短期可能因 Iran 解和回落", "bear": "Airlines 燃料 +56% 對 Q2 EPS 重壓",
     "sector": "Airlines (DAL/UAL/AAL) 偏空", "macro": "通膨尾風險",
     "score": -1.8, "binary": False, "advance": False},
]

# Build verdicts
verdicts = []
for i, c in enumerate(CURATED, start=1):
    raw_item = find_kw(c["kw"])
    verdicts.append({
        "news_id": f"n{i:03d}",
        "raw_news_id": raw_item["news_id"],
        "headline": raw_item["headline"],
        "headline_zh": "",
        "url": raw_item.get("url", ""),
        "published": raw_item.get("published", ""),
        "source": raw_item.get("source", ""),
        "source_credibility": raw_item.get("source_credibility", "MEDIUM"),
        "raw_summary": (raw_item.get("raw_summary") or "")[:400],
        "news_type": c["news_type"],
        "bull_case": c["bull"],
        "bear_case": c["bear"],
        "sector_view": c["sector"],
        "macro_view": c["macro"],
        "shallow_score": c["score"],
        "binary_flag": c["binary"],
        "advance_to_stage2": c["advance"],
        "advance_reason": c.get("reason"),
    })

# Sort by |score| desc
verdicts_sorted = sorted(verdicts, key=lambda v: abs(v["shallow_score"]), reverse=True)
advanced_ids = [v["news_id"] for v in verdicts_sorted if v["advance_to_stage2"]]
assert len(advanced_ids) <= 5, f"Too many advanced: {len(advanced_ids)}"

triage = {
    "phase": "stage1_triage",
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "raw_count": raw["raw_count"],
    "after_dedupe": raw["after_dedupe"],
    "shallow_verdicts": verdicts_sorted,
    "advanced_count": len(advanced_ids),
    "advanced_ids": advanced_ids,
}

OUT.write_text(json.dumps(triage, ensure_ascii=False, indent=2))
print(f"WROTE {OUT}")
print(f"  shallow={len(verdicts_sorted)}  advanced={len(advanced_ids)}")
print()
print("┌──────────────────────────────────────────────────────────────────────────────────────┐")
print(f"│  NEWS TRIAGE  │  {triage['timestamp']}  │  {raw['raw_count']} 則 → {len(verdicts_sorted)} shallow → {len(advanced_ids)} 晉級")
print("├──────────────────────────────────────────────────────────────────────────────────────┤")
for v in verdicts_sorted:
    flag = "✅ DEEP" if v["advance_to_stage2"] else "❌ SKIP"
    score_s = f"{v['shallow_score']:+4.1f}"
    extra = "[BINARY] " if v["binary_flag"] else ""
    print(f"│  {flag}  {v['news_id']}  [{score_s}]  {extra}{v['headline'][:62]:62s}  {v['news_type'][:14]:14s}")
print("└──────────────────────────────────────────────────────────────────────────────────────┘")

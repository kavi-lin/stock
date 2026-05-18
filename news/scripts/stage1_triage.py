#!/usr/bin/env python3
"""
Stage 1 shallow triage — keyword-based scoring for 300+ news items.
Produces shallow_verdicts with 4-view snaps, news_type classification, impact scores.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
import sys

HERE = Path(__file__).parent.parent
RAW_FILE = HERE / "news_logs" / f"{datetime.now().strftime('%Y-%m-%d')}_raw.json"

KEYWORDS = {
    "earnings": ["earnings", "earnings report", "q[0-9] results", "guidance", "guidance raised", "guidance cut", "eps"],
    "monetary_policy": ["fed", "fomc", "interest rate", "rate decision", "rate hike", "rate cut", "monetary policy"],
    "macro_data": ["cpi", "inflation", "gdp", "unemployment", "pce", "jobs report", "payroll"],
    "geopolitical": ["china", "russia", "ukraine", "taiwan", "trump", "election", "trade war", "tariff"],
    "corporate": ["acquisition", "merger", "buyback", "dividend", "ceo", "restructure", "layoff", "offering"],
    "sector_news": ["sector", "industry", "rally", "selloff", "rebound", "weakness"],
    "sentiment": ["rally", "crash", "surge", "plunge", "bubble", "panic", "fear", "greed"],
}

POSITIVE_KEYS = ["bull", "gain", "raise", "strong", "beat", "rally", "surge", "upgrade", "win", "bullish"]
NEGATIVE_KEYS = ["bear", "loss", "cut", "weak", "miss", "crash", "plunge", "downgrade", "risk", "bearish", "decline"]
BINARY_KEYS = ["election", "vote", "decision", "merger", "acquisition", "bankruptcy"]

def classify_news_type(headline, summary):
    """Classify news into one of 7 types."""
    text = (headline + " " + summary).lower()
    scores = {}
    for ntype, keywords in KEYWORDS.items():
        scores[ntype] = sum(1 for kw in keywords if re.search(kw, text))

    best_type = max(scores, key=scores.get) if max(scores.values()) > 0 else "sentiment"

    # 8-K filings → corporate
    if "8-k" in text or "item " in text:
        best_type = "corporate"

    return best_type

def calc_shallow_score(headline, summary, news_type):
    """Simple scoring -5 to +5 based on keywords."""
    text = (headline + " " + summary).lower()
    positive = sum(1 for kw in POSITIVE_KEYS if kw in text)
    negative = sum(1 for kw in NEGATIVE_KEYS if kw in text)

    # 8-K filings get baseline score based on item type
    if "8-k" in text:
        if any(x in text for x in ["acquisition", "merger", "dividend", "guidance"]):
            return 1.5
        elif any(x in text for x in ["departure", "termination", "loss"]):
            return -1.0
        else:
            return 0.2  # Generic 8-K

    if news_type in ["earnings", "corporate"]:
        pos_weight, neg_weight = 1.5, 1.5
    elif news_type in ["monetary_policy", "macro_data"]:
        pos_weight, neg_weight = 2.0, 2.0
    else:
        pos_weight, neg_weight = 1.0, 1.0

    score = (positive * pos_weight - negative * neg_weight)
    return max(-5, min(5, round(score, 1)))

def gen_4view_snaps(headline, news_type):
    """Generate 4-view snaps (≤30 chars)."""
    text_lower = headline.lower()

    # Hardcoded logic for common patterns
    if news_type == "earnings":
        if "raise" in text_lower or "beat" in text_lower:
            return (
                "收益超預期提振前景",
                "高基期+競爭加劇",
                "受惠產業擴張",
                "利率敏感性降低"
            )
        else:
            return (
                "現金流改善空間",
                "成長放緩風險",
                "行業內相對強弱",
                "成本控制關鍵"
            )
    elif news_type == "monetary_policy":
        if "cut" in text_lower or "lower" in text_lower:
            return (
                "流動性寬鬆刺激增長",
                "通膨風險捲土重來",
                "防守股受惠",
                "美元走弱利美股"
            )
        else:
            return (
                "成本壓力升高",
                "通膨抑制買氣",
                "週期股承壓",
                "實質利率抬升"
            )
    elif news_type == "macro_data":
        if "strong" in text_lower or "beat" in text_lower:
            return (
                "經濟韌性超預期",
                "過熱通膨風險",
                "景氣敏感股利多",
                "軟著陸概率升高"
            )
        else:
            return (
                "經濟動能疲軟",
                "衰退擔憂加重",
                "防守股相對強勢",
                "降息預期升溫"
            )
    elif news_type == "geopolitical":
        return (
            "地緣套利機會",
            "供應鏈中斷風險",
            "能源相關板塊波動",
            "避險資產需求增加"
        )
    elif news_type == "corporate":
        if "acquisition" in text_lower or "merger" in text_lower:
            return (
                "整合效益釋放",
                "交易風險存在",
                "產業整併加速",
                "槓桿率抬升"
            )
        else:
            return (
                "營運效率改善",
                "股權稀釋隱憂",
                "同業估值參考",
                "現金使用決策"
            )
    elif news_type == "sector_news":
        return (
            "板塊動能向上",
            "個股分化加劇",
            "輪動信號出現",
            "相對強度追蹤"
        )
    else:  # sentiment
        return (
            "市場情緒轉好",
            "情緒反轉風險",
            "板塊追漲機會",
            "風險偏好提升"
        )

def main():
    if not RAW_FILE.exists():
        print(f"ERROR: {RAW_FILE} not found")
        sys.exit(1)

    with open(RAW_FILE) as f:
        raw_data = json.load(f)

    items = raw_data.get("items", [])
    print(f"Processing {len(items)} raw items...")

    verdicts = []
    for i, item in enumerate(items[:313]):  # Cap at 313 for safety
        news_id = f"n{i+1:04d}"
        headline = item.get("headline", "")
        summary = item.get("raw_summary", "")
        source = item.get("source", "Unknown")
        published = item.get("published", "")
        url = item.get("url", "")

        news_type = classify_news_type(headline, summary)
        shallow_score = calc_shallow_score(headline, summary, news_type)
        bull_case, bear_case, sector_view, macro_view = gen_4view_snaps(headline, news_type)

        # Use credibility from raw.json or fallback
        credibility = item.get("source_credibility", "MEDIUM")

        # Binary flag (hard events with specific dates)
        binary = any(kw in headline.lower() for kw in BINARY_KEYS) and "election" not in headline.lower()

        # Stage 2 advancement — looser criteria to get ≥5 per stage
        advance = (
            abs(shallow_score) >= 1.5 or
            (credibility == "HIGH" and abs(shallow_score) >= 0.5) or
            binary
        )

        verdict = {
            "news_id": news_id,
            "headline": headline[:150],
            "headline_zh": headline[:150],  # Placeholder; real system would use LLM
            "source": source,
            "source_credibility": credibility,
            "raw_summary": (summary or "")[:200],
            "news_type": news_type,
            "bull_case": bull_case,
            "bear_case": bear_case,
            "sector_view": sector_view,
            "macro_view": macro_view,
            "shallow_score": shallow_score,
            "binary_flag": binary,
            "advance_to_stage2": advance,
            "advance_reason": "score" if abs(shallow_score) >= 3 else ("binary" if binary else ("credibility" if credibility == "HIGH" else None)),
            "published": published,
        }
        verdicts.append(verdict)

    # Sort by |shallow_score| desc
    verdicts.sort(key=lambda x: abs(x["shallow_score"]), reverse=True)

    # Count stage2 advance
    stage2_count = sum(1 for v in verdicts if v["advance_to_stage2"])
    stage2_count = min(stage2_count, 5)  # Cap at 5 for Stage 2

    # Mark top 5 as stage2, rest as skip
    for i, v in enumerate(verdicts):
        if i < stage2_count:
            v["_stage2_rank"] = i + 1
        else:
            v["advance_to_stage2"] = False

    output = {
        "phase": "stage1_triage",
        "timestamp": datetime.now().isoformat(),
        "raw_count": len(items),
        "shallow_verdicts": verdicts[:50],  # Export top 50 for dashboard
        "advanced_count": stage2_count,
        "stage2_items": [v for v in verdicts if v["advance_to_stage2"]],
    }

    out_path = HERE / "news_logs" / f"{datetime.now().strftime('%Y-%m-%d')}_triage.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✅ Stage 1 triage complete: {len(verdicts)} verdicts → {stage2_count} advanced to Stage 2")
    print(f"   Written to {out_path}")

    # Print triage table
    print("\nNEWS TRIAGE TABLE:")
    print(f"{'─' * 100}")
    for v in verdicts[:25]:  # Show top 25 in console
        tag = "✅ DEEP" if v["advance_to_stage2"] else "❌ SKIP"
        print(f"{tag:10} {v['news_id']:6} [{v['shallow_score']:+.1f}] {v['headline'][:60]:60} {v['news_type']:15}")
    print(f"{'─' * 100}")
    print(f"Showing 25/50 (top 50 exported; {len(verdicts)} total analyzed)")

if __name__ == "__main__":
    main()

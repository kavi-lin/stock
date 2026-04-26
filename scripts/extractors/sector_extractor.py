"""Extract sector-scan markdown reports.

Looks for the FINAL VERDICT TABLE (產業 / 評級 / 分數 / ETF) and macro fields.
"""
from __future__ import annotations
import re
from pathlib import Path

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_sector_report\.md$")
RATING_NORMALIZE = {"HOT": "HOT", "WARM": "WARM", "COLD": "COLD"}


def _parse_filename(path: Path) -> str | None:
    m = DATE_RE.search(path.name)
    return m.group(1) if m else None


def _find_table_rows(text: str) -> list[dict]:
    """Find rows in FINAL VERDICT TABLE: 產業 | 評級 | 分數 | 理由 | 尾部風險 | ETF | 風險旗標."""
    rows = []
    after_header = False
    for line in text.splitlines():
        if "FINAL VERDICT" in line:
            after_header = True
            continue
        if not after_header:
            continue
        if line.startswith("##") and "FINAL VERDICT" not in line:
            break  # next section
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 5:
            continue
        # 找評級欄位
        rating_match = re.search(r"\b(HOT|WARM|COLD)\b", line)
        score_match = re.search(r"\|\s*(\d+\*?)\s*\|", line)
        etf_match = re.search(r"\b(XL[BFKVUYREICP]|XLRE|XLU|XBI|XHB)\b", line)
        if rating_match:
            rows.append({
                "sector": cells[0],
                "rating": rating_match.group(1),
                "score": int(score_match.group(1).rstrip("*")) if score_match else None,
                "etf": etf_match.group(1) if etf_match else None,
            })
    return rows


def _find_market_regime(text: str) -> dict:
    regime = None
    for p in (r"Market Regime\s*[:\s]+\s*([A-Z_]+)",
              r"市場制度\**[^A-Z]*([A-Z_]+)",
              r"\*\*市場制度\*\*[^A-Z]*🔴?\s*([A-Z_]+)"):
        m = re.search(p, text)
        if m:
            regime = m.group(1)
            break
    breadth = None
    m = re.search(r"廣度分數\**[^|]+?(\d+\.?\d*)\s*/\s*100", text)
    if m:
        breadth = float(m.group(1))
    exposure = None
    m = re.search(r"曝險上限\**[^|]+?\**\s*(\d+[–\-]?\d*%)", text)
    if m:
        exposure = m.group(1)
    return {"market_regime": regime, "breadth_score": breadth, "exposure_ceiling": exposure}


def extract(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    decision_date = _parse_filename(path)
    ratings = _find_table_rows(text)
    macro = _find_market_regime(text)

    hot_count  = sum(1 for r in ratings if r["rating"] == "HOT")
    warm_count = sum(1 for r in ratings if r["rating"] == "WARM")
    cold_count = sum(1 for r in ratings if r["rating"] == "COLD")

    record = {
        "source": "sector-scan",
        "decision_date": decision_date,
        "scope": "market",
        "tickers": [r["etf"] for r in ratings if r["etf"]],
        "raw_path": str(path.relative_to(path.parents[1])) if len(path.parents) > 1 else str(path),
        "summary": f"sector scan: {hot_count}H/{warm_count}W/{cold_count}C, regime={macro['market_regime']}",
        "decision_content": {
            "sector_ratings": ratings,
            "market_regime": macro["market_regime"],
            "breadth_score": macro["breadth_score"],
            "exposure_ceiling": macro["exposure_ceiling"],
        },
        "agent_breakdown": [],
        "tuning_hooks": {
            "regime": macro["market_regime"],
            "breadth_score": macro["breadth_score"],
            "n_hot": hot_count,
            "n_warm": warm_count,
            "n_cold": cold_count,
            "rating_skew": "defensive" if (hot_count + warm_count) < cold_count else "offensive",
        },
    }
    record["decision_id"] = f"sector-scan_{decision_date}"
    return record

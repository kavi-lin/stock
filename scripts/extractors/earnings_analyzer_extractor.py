"""Extract earnings_trade_analyzer JSON output."""
from __future__ import annotations
import json
from pathlib import Path
import re


def _parse_filename(path: Path) -> str | None:
    m = re.search(r"earnings_trade_analyzer_(\d{4}-\d{2}-\d{2})", path.stem)
    return m.group(1) if m else None


def extract(path: Path) -> dict:
    with path.open() as f:
        data = json.load(f)

    decision_date = _parse_filename(path)
    meta = data.get("metadata") or {}
    summary = data.get("summary") or {}
    results = data.get("results") or []

    # 簡化每筆 result, 保留 verdict 用得到的欄位
    slim = []
    for r in results:
        slim.append({
            "symbol": r.get("symbol"),
            "company_name": r.get("company_name"),
            "earnings_date": r.get("earnings_date"),
            "earnings_timing": r.get("earnings_timing"),
            "gap_pct": r.get("gap_pct"),
            "composite_score": r.get("composite_score"),
            "grade": r.get("grade"),
            "current_price": r.get("current_price"),
            "sector": r.get("sector"),
        })

    record = {
        "source": "earnings-analyzer",
        "decision_date": decision_date,
        "scope": "market",
        "tickers": [r["symbol"] for r in slim if r.get("symbol")],
        "raw_path": str(path).split("AI投資委員會/")[-1],
        "summary": (
            f"earnings analyzer: {summary.get('total','?')} stocks, "
            f"A:{summary.get('grade_a',0)} B:{summary.get('grade_b',0)} "
            f"C:{summary.get('grade_c',0)} D:{summary.get('grade_d',0)}"),
        "decision_content": {
            "metadata": {k: meta.get(k) for k in ("lookback_days", "total_screened", "min_gap")},
            "summary": summary,
            "results": slim,
            "sector_distribution": data.get("sector_distribution"),
        },
        "agent_breakdown": [],
        "tuning_hooks": {
            "grade_a_count": summary.get("grade_a", 0),
            "grade_b_count": summary.get("grade_b", 0),
            "grade_c_count": summary.get("grade_c", 0),
            "grade_d_count": summary.get("grade_d", 0),
            "total": summary.get("total", 0),
            "lookback_days": meta.get("lookback_days"),
            "top_sector": max(
                (data.get("sector_distribution") or {}).items(),
                key=lambda x: x[1], default=(None, 0))[0],
        },
    }
    record["decision_id"] = f"earnings-analyzer_{decision_date}"
    return record

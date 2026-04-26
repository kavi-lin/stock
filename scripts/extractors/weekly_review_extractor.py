"""Extract SHORT_TERM_WEEKLY_*.md.

Looks for hit_rate / alpha tables. When window has not elapsed, output is
"No outcomes available" — extractor records this as eval_pending.
"""
from __future__ import annotations
import re
from pathlib import Path

DATE_RE = re.compile(r"SHORT_TERM_WEEKLY_(\d{4}-\d{2}-\d{2})")


def _parse_filename(path: Path) -> str | None:
    m = DATE_RE.search(path.stem)
    return m.group(1) if m else None


def _find_summary_metrics(text: str) -> dict:
    """Try multiple patterns; weekly review format may evolve."""
    out = {"hit_rate": None, "avg_alpha_pct": None, "n_evaluated": None}
    for p in (r"Overall hit rate[:\s]+([\d.]+)\s*%",
              r"hit_rate[:\s]+([\d.]+)\s*%?",
              r"\*\*Hit rate\*\*[:\s]+([\d.]+)\s*%"):
        m = re.search(p, text, re.IGNORECASE)
        if m:
            v = float(m.group(1))
            out["hit_rate"] = v / 100.0 if v > 1 else v
            break
    for p in (r"avg alpha[:\s]+([+\-]?[\d.]+)\s*%",
              r"avg_alpha_pct[:\s]+([+\-]?[\d.]+)",
              r"Average alpha[:\s]+([+\-]?[\d.]+)\s*%"):
        m = re.search(p, text, re.IGNORECASE)
        if m:
            out["avg_alpha_pct"] = float(m.group(1))
            break
    m = re.search(r"(\d+)\s+(?:predictions|recommendations)\s+evaluated", text, re.IGNORECASE)
    if m:
        out["n_evaluated"] = int(m.group(1))
    return out


def extract(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    decision_date = _parse_filename(path)
    metrics = _find_summary_metrics(text)
    pending = "No outcomes available" in text

    record = {
        "source": "short-term-weekly",
        "decision_date": decision_date,
        "scope": "market",
        "tickers": [],
        "raw_path": str(path.relative_to(path.parents[1])) if len(path.parents) > 1 else str(path),
        "summary": (
            "weekly review: window 未到 (pending)" if pending else
            f"weekly: hit_rate={metrics['hit_rate']} alpha={metrics['avg_alpha_pct']}"),
        "decision_content": {
            "hit_rate": metrics["hit_rate"],
            "avg_alpha_pct": metrics["avg_alpha_pct"],
            "n_evaluated": metrics["n_evaluated"],
            "pending": pending,
        },
        "agent_breakdown": [],
        "tuning_hooks": {
            "pending": pending,
            "n_evaluated": metrics["n_evaluated"],
            "hit_rate_band": (
                "high" if (metrics["hit_rate"] or 0) >= 0.6 else
                "med"  if (metrics["hit_rate"] or 0) >= 0.4 else
                "low"  if metrics["hit_rate"] is not None else None),
        },
    }
    record["decision_id"] = f"short-term-weekly_{decision_date}"
    return record

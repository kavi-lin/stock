"""Extract POSTMORTEM_*.md (already retrospective; no eval needed)."""
from __future__ import annotations
import re
from pathlib import Path

DATE_RE = re.compile(r"POSTMORTEM_(\d{4}-\d{2}-\d{2})")


def _parse_filename(path: Path) -> str | None:
    m = DATE_RE.search(path.stem)
    return m.group(1) if m else None


def _find_top_metrics(text: str) -> dict:
    out: dict = {"reports_parsed": None, "with_outcome": None}
    m = re.search(r"\*\*Reports parsed\*\*[:\s]+(\d+)", text)
    if m:
        out["reports_parsed"] = int(m.group(1))
    m = re.search(r"\*\*With price outcome\*\*[:\s]+(\d+)", text)
    if m:
        out["with_outcome"] = int(m.group(1))
    return out


def _find_decision_buckets(text: str) -> list[dict]:
    """Section '1. Overall scoring vs realized outcomes' table rows."""
    rows = []
    in_section = False
    for line in text.splitlines():
        if "1. Overall scoring" in line:
            in_section = True
            continue
        if not in_section:
            continue
        if line.startswith("##"):
            break
        m = re.match(r"\|\s*`?([A-Z_]+)`?\s*\|\s*(\d+)\s*\|\s*([+\-—\d.%]+)\s*\|", line)
        if m:
            rows.append({
                "bucket": m.group(1),
                "n": int(m.group(2)),
                "ret_so_far": m.group(3).strip(),
            })
    return rows


def extract(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    decision_date = _parse_filename(path)
    metrics = _find_top_metrics(text)
    buckets = _find_decision_buckets(text)

    record = {
        "source": "postmortem",
        "decision_date": decision_date,
        "scope": "market",
        "tickers": [],
        "raw_path": str(path.relative_to(path.parents[1])) if len(path.parents) > 1 else str(path),
        "summary": (
            f"postmortem: parsed {metrics['reports_parsed']} reports, "
            f"{metrics['with_outcome']} with outcomes"),
        "decision_content": {
            "reports_parsed": metrics["reports_parsed"],
            "with_outcome":   metrics["with_outcome"],
            "decision_buckets": buckets,
        },
        "agent_breakdown": [],
        "tuning_hooks": {
            "reports_parsed": metrics["reports_parsed"],
            "decision_bucket_count": len(buckets),
        },
    }
    record["decision_id"] = f"postmortem_{decision_date}"
    return record

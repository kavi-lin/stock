"""Extract news digest markdown.

Pulls macro_delta + impact card titles + any tickers/sectors flagged.
News digests are market-wide (no single ticker). Verdict uses SPY as proxy.
"""
from __future__ import annotations
import re
from pathlib import Path

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_news_digest\.md$")


def _parse_filename(path: Path) -> str | None:
    m = DATE_RE.search(path.name)
    return m.group(1) if m else None


def _find_macro_delta(text: str) -> float | None:
    # 多版本 digest header. V2026-05+ digests embed delta inside the
    # macro_backdrop_score line: "(session_macro_delta +0.20)" — older
    # patterns required signed prefix on the bolded label which misses.
    for p in (
            # New format — delta inside parenthetical, optional sign
            r"session_macro_delta\s*\(?([+\-−]?\d+\.?\d*)",
            # New format — colon / equals form (JSON-ish)
            r"session_macro_delta[\s:=]+([+\-−]?\d+\.?\d*)",
            # Greek-Δ headers (May 2026+ inline form, e.g. "**Macro Backdrop Δ**: -0.10")
            r"\*\*Macro Backdrop\s*Δ\*\*[:\s]+([+\-−]?[\d.]+)",
            r"\*\*Session macro\s*Δ\*\*[:\s]+([+\-−]?[\d.]+)",
            r"Macro Backdrop\s*Δ\**[:\s]+([+\-−]?[\d.]+)",
            r"Session macro\s*Δ\**[:\s]+([+\-−]?[\d.]+)",
            # Older bolded-header forms with the word "Delta" (kept for back-compat)
            r"Macro Backdrop Delta\**[:\s]+([+\-−][\d.]+)",
            r"Session Macro Delta\**[:\s]+([+\-−][\d.]+)",
            r"\*\*Macro Backdrop Delta\*\*[:\s]+([+\-−][\d.]+)"):
        m = re.search(p, text)
        if m:
            v = m.group(1).replace("−", "-")
            try:
                return float(v)
            except ValueError:
                continue
    return None


def _find_macro_delta_from_triage(text: str) -> float | None:
    """v2 digest: derive delta from Triage Summary table scores (sum / N)."""
    rows = re.findall(r"\|\s*(?:✅\s*)?DEEP\s*\|[^|]+\|\s*(?:BINARY\s*)?([+\-−][\d.]+)\s*\|",
                      text)
    if not rows:
        return None
    vals = []
    for v in rows:
        try:
            vals.append(float(v.replace("−", "-")))
        except ValueError:
            continue
    if not vals:
        return None
    return round(sum(vals) / len(vals), 2)


def _find_impact_cards(text: str) -> list[dict]:
    """Match '## Impact Card #N — {title}' + the bracketed [{TYPE} {score}] header."""
    cards = []
    card_re = re.compile(
        r"##\s+Impact Card\s*#\d+\s*[—\-]\s*([^\n]+?)\n.*?"
        r"\[([A-Z_]+)\s+([+\-−]?[\d.]+)\]",
        re.DOTALL)
    for m in card_re.finditer(text):
        score = m.group(3).replace("−", "-")
        try:
            score_f = float(score)
        except ValueError:
            score_f = None
        cards.append({
            "title": m.group(1).strip(),
            "type": m.group(2),
            "score": score_f,
        })
    return cards


def _find_items_count(text: str) -> int | None:
    m = re.search(r"\*\*Items Analyzed\*\*[:\s]+(\d+)", text)
    return int(m.group(1)) if m else None


def extract(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    decision_date = _parse_filename(path)

    macro_delta = _find_macro_delta(text)
    if macro_delta is None:
        macro_delta = _find_macro_delta_from_triage(text)
    cards = _find_impact_cards(text)
    items = _find_items_count(text)

    binary_count = sum(1 for c in cards if c["type"].upper() == "BINARY")
    bull_score = sum(c["score"] for c in cards if c["score"] is not None and c["score"] > 0)
    bear_score = sum(c["score"] for c in cards if c["score"] is not None and c["score"] < 0)

    record = {
        "source": "news-digest",
        "decision_date": decision_date,
        "scope": "market",
        "tickers": ["SPY"],
        "raw_path": str(path.relative_to(path.parents[1])) if len(path.parents) > 1 else str(path),
        "summary": f"news digest: Δ={macro_delta}, {len(cards)} cards ({binary_count} binary)",
        "decision_content": {
            "macro_delta": macro_delta,
            "items_analyzed": items,
            "impact_cards": cards,
        },
        "agent_breakdown": [],
        "tuning_hooks": {
            "macro_delta_sign": (
                "negative" if (macro_delta or 0) < -0.3 else
                "positive" if (macro_delta or 0) > 0.3 else "neutral"),
            "binary_count": binary_count,
            "bull_score_total": bull_score,
            "bear_score_total": bear_score,
            "card_count": len(cards),
        },
    }
    record["decision_id"] = f"news-digest_{decision_date}"
    return record

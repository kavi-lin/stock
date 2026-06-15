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


# TODO-008 (REVIEW_2026-05-31 Rec 4 regression — null 回升 35%). One tolerant
# matcher replaces the 10-pattern ladder that kept missing new digest dialects.
# Handles every observed form (Apr–May 2026):
#   session_macro_delta **+0.3**        (label + bold, no separator)
#   **session_macro_delta**: −0.22      (bolded label + colon)
#   **Session macro delta**: -0.55      (space words + bold + colon, mixed case)
#   session_macro_delta: **-0.3**       (colon + bolded number)
#   `session_macro_delta` = **-0.5**    (backtick + equals + bold)
#   **Macro Δ**: -0.4 / **Macro Backdrop Δ**: -0.10   (Greek-Δ short & long)
#   (session_macro_delta +0.20)         (parenthetical)
# Label variants + optional backtick/bold wrappers + optional :/= + IGNORECASE.
_MACRO_DELTA_LABEL = (
    r"(?:session[ _]macro[ _]delta"
    r"|net[ _]session[ _]delta"
    r"|macro[ _]backdrop[ _](?:delta|Δ)"
    r"|session[ _]macro[ _]Δ"
    r"|macro[ _]Δ)")
_MACRO_DELTA_RE = re.compile(
    _MACRO_DELTA_LABEL + r"[`*]*\s*[:=]?\s*[`*]*([+\-−]?\d+\.?\d*)",
    re.IGNORECASE)


def _find_macro_delta(text: str) -> float | None:
    m = _MACRO_DELTA_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(1).replace("−", "-"))
    except ValueError:
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

"""Extract decision snapshot from V4.x deep-dive markdown reports.

V4 reports vary slightly across versions (V4.4, V4.6, V4.8). Extractor uses
lenient regex over section headers; missing fields default to None.
"""
from __future__ import annotations
import re
from pathlib import Path

FILENAME_RE = re.compile(r"(\d{8})_([A-Z][A-Z0-9]+)")


def _parse_filename(path: Path) -> tuple[str | None, str | None]:
    m = FILENAME_RE.match(path.stem)
    if not m:
        return None, None
    yyyymmdd, ticker = m.group(1), m.group(2)
    decision_date = f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"
    return decision_date, ticker


def _find_final_score(text: str) -> float | None:
    # 嘗試多種 pattern: V4.8 用 "Final Score" / V4.x 用 final_score JSON / decision table
    patterns = [
        r"\"final_score\"\s*:\s*([+-]?\d+\.?\d*)",
        r"Final Score[*:\s|]*\**\s*([+-]?\d+\.?\d*)",
        r"\*\*Final\*\*[^|]*\|[^|]*\|\s*\*\*([+-]?\d+\.?\d*)\*\*",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def _find_decision(text: str) -> str | None:
    patterns = [
        r"\"decision\"\s*:\s*\"([A-Z_]+)\"",
        r"\"final_action\"\s*:\s*\"([A-Z_]+)\"",
        r"\*\*Action\*\*[:\s]*([A-Z_/() ]+?)[\n\|]",
        r"\| \*\*(BUY|HOLD|SELL|CANCEL|EXECUTE)\*\* \|",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return None


def _find_position_size(text: str) -> float | None:
    m = re.search(r"\"position_size\"\s*:\s*([0-9.]+)", text)
    if m:
        return float(m.group(1))
    m = re.search(r"Position Size[\s|]+\**([0-9.]+)%?", text)
    if m:
        try:
            return float(m.group(1)) / 100.0
        except ValueError:
            pass
    return None


def _find_trader_proposal(text: str) -> dict | None:
    """Phase 4 trader 提案 entry/TP/SL — JSON 格式優先, 表格次之."""
    # JSON
    m = re.search(
        r'"entry_price"\s*:\s*([\d.]+)[^}]*?"take_profit"\s*:\s*([\d.]+)[^}]*?"stop_loss"\s*:\s*([\d.]+)',
        text, re.DOTALL)
    if m:
        return {"entry": float(m.group(1)), "tp": float(m.group(2)), "sl": float(m.group(3))}

    # Markdown table forms vary; try entry/SL/TP keywords
    entry = re.search(r"entry[:\s]*\$?([\d.]+)", text, re.IGNORECASE)
    tp = re.search(r"(?:take[_ ]?profit|TP)[:\s]*\$?([\d.]+)", text, re.IGNORECASE)
    sl = re.search(r"(?:stop[_ ]?loss|SL)[:\s]*\$?([\d.]+)", text, re.IGNORECASE)
    if entry or tp or sl:
        return {
            "entry": float(entry.group(1)) if entry else None,
            "tp":    float(tp.group(1))    if tp    else None,
            "sl":    float(sl.group(1))    if sl    else None,
        }
    return None


# Match agent sections like "### Fundamentals · BUY +4.0 (0.82)" or
# "### Fundamentals Analyst — Signal: BUY | Score: +3 | Confidence: 0.75"
AGENT_RE_V46 = re.compile(
    r"###\s+(Fundamentals|Sentiment|News|Technical|Contrarian|Burry)\s*"
    r"(?:Analyst)?\s*[·•—\-]\s*"
    r"([A-Z_]+)\s*([+\-]?[\d.]+)\s*\(([\d.]+)\)",
    re.IGNORECASE)

AGENT_RE_V44 = re.compile(
    r"###\s+(Fundamentals|Sentiment|News|Technical|Contrarian|Burry)\s*"
    r"(?:Analyst)?[\s—\-]+"
    r"Signal[:\s]+([A-Z_]+)\s*\|\s*Score[:\s]+([+\-]?\d+)\s*\|\s*Confidence[:\s]+([\d.]+)",
    re.IGNORECASE)


AGENT_NAMES = ("Fundamentals", "Sentiment", "News", "Technical", "Contrarian", "Burry")
# Allow optional emoji / decoration prefix between ### and the agent name
AGENT_BLOCK_RE = re.compile(
    r"###\s+[^\n]*?(" + "|".join(AGENT_NAMES) + r")\s*(?:Analyst)?\s*\n+```json\s*\n(.*?)\n```",
    re.DOTALL | re.IGNORECASE)


def _find_agent_breakdown(text: str) -> list[dict]:
    agents: list[dict] = []
    seen = set()
    # V4.6+ inline format
    for regex in (AGENT_RE_V46, AGENT_RE_V44):
        for m in regex.finditer(text):
            name = m.group(1).title()
            if name in seen:
                continue
            seen.add(name)
            try:
                agents.append({
                    "agent": name,
                    "signal": m.group(2).upper(),
                    "score": float(m.group(3)),
                    "confidence": float(m.group(4)),
                })
            except ValueError:
                continue
    # V4.4 JSON-block format
    import json as _json
    for m in AGENT_BLOCK_RE.finditer(text):
        name = m.group(1).title()
        if name in seen:
            continue
        try:
            obj = _json.loads(m.group(2))
            agents.append({
                "agent": name,
                "signal": str(obj.get("signal", "")).upper(),
                "score": float(obj.get("score", 0)),
                "confidence": float(obj.get("confidence", 0)),
            })
            seen.add(name)
        except (ValueError, _json.JSONDecodeError):
            continue
    return agents


def _find_macro_regime(text: str) -> dict:
    regime = None
    for p in (r"\"market_regime\"\s*:\s*\"([A-Z_]+)\"",
              r"\*\*market_regime\*\*[^A-Z]+([A-Z_]+)",
              r"PHASE 0[^\n]*([A-Z_]+ regime)"):
        m = re.search(p, text)
        if m:
            regime = m.group(1).split()[0]
            break

    mult = None
    m = re.search(r"macro_multiplier[\"\s|:×]+([\d.]+)", text)
    if m:
        try:
            mult = float(m.group(1))
        except ValueError:
            pass

    return {"market_regime": regime, "macro_multiplier": mult}


def extract(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    decision_date, ticker = _parse_filename(path)

    agents = _find_agent_breakdown(text)
    decisive_agent = None
    if agents:
        decisive_agent = max(agents, key=lambda a: abs(a["score"] * a["confidence"]))["agent"]

    final_score = _find_final_score(text)
    decision = _find_decision(text)
    position = _find_position_size(text)
    trader = _find_trader_proposal(text)
    macro = _find_macro_regime(text)

    record = {
        "source": "deep-dive",
        "decision_date": decision_date,
        "scope": "ticker",
        "tickers": [ticker] if ticker else [],
        "raw_path": str(path.relative_to(path.parents[1])) if len(path.parents) > 1 else str(path),
        "summary": f"{ticker} deep-dive: {decision or 'unknown'} (score {final_score})",
        "decision_content": {
            "final_score": final_score,
            "final_action": decision,
            "position_size": position,
            "trader_proposal": trader,
            "macro_regime": macro["market_regime"],
            "macro_multiplier": macro["macro_multiplier"],
        },
        "agent_breakdown": agents,
        "tuning_hooks": {
            "decisive_agent": decisive_agent,
            "macro_regime": macro["market_regime"],
            "macro_multiplier": macro["macro_multiplier"],
            "agent_count": len(agents),
            "min_agent_confidence": min((a["confidence"] for a in agents), default=None),
            "max_agent_confidence": max((a["confidence"] for a in agents), default=None),
        },
    }
    record["decision_id"] = f"deep-dive_{ticker}_{decision_date}"
    return record

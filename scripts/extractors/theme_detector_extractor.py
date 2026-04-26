"""Extract theme-detector markdown report.

Theme dashboard table format:
| # | Theme | Dir | Heat | Stage | Confidence |
"""
from __future__ import annotations
import re
from pathlib import Path

DATE_RE = re.compile(r"(\d{8})_theme")
DATE_RE_ALT = re.compile(r"theme_detector_(\d{4}-\d{2}-\d{2})")


def _parse_filename(path: Path) -> str | None:
    m = DATE_RE.match(path.stem)
    if m:
        d = m.group(1)
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    m = DATE_RE_ALT.search(path.stem)
    if m:
        return m.group(1)
    return None


# theme name → typical sector ETF (best-effort mapping)
THEME_ETF_MAP = {
    "basic materials": "XLB",
    "infrastructure":  "XLI",
    "oil & gas":       "XLE",
    "clean energy":    "ICLN",
    "ev":              "ICLN",
    "defense":         "ITA",
    "aerospace":       "ITA",
    "cybersecurity":   "HACK",
    "cloud":           "WCLD",
    "saas":            "WCLD",
    "ai":              "SOXX",
    "semiconductors":  "SOXX",
    "industrials":     "XLI",
    "consumer defensive": "XLP",
    "consumer staples":   "XLP",
    "healthcare":      "XLV",
    "utilities":       "XLU",
    "financials":      "XLF",
    "real estate":     "XLRE",
    "communication":   "XLC",
    "technology":      "XLK",
    "energy":          "XLE",
    "consumer discretionary": "XLY",
}


def _proxy_etf(theme_name: str) -> list[str]:
    name = theme_name.lower()
    etfs = []
    for k, v in THEME_ETF_MAP.items():
        if k in name:
            etfs.append(v)
    # de-dup, preserve order
    return list(dict.fromkeys(etfs))


def _find_themes(text: str) -> list[dict]:
    themes = []
    in_dashboard = False
    for line in text.splitlines():
        if "Theme Dashboard" in line:
            in_dashboard = True
            continue
        if not in_dashboard:
            continue
        if line.startswith("##") and "Dashboard" not in line:
            break
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 6:
            continue
        # 第一格通常是 #（數字）, 第二格主題名
        if not cells[0].isdigit():
            continue
        name = re.sub(r"[^一-鿿A-Za-z& /]+", "", cells[1]).strip()
        # direction: LEAD ↑ / LAG ↓
        dir_raw = cells[2].upper()
        direction = "LEAD" if "LEAD" in dir_raw else ("LAG" if "LAG" in dir_raw else None)
        # heat
        heat_match = re.search(r"([\d.]+)", cells[3])
        heat = float(heat_match.group(1)) if heat_match else None
        # stage
        stage = re.sub(r"[^A-Za-z一-鿿 ]", "", cells[4]).strip()
        # confidence
        conf = re.sub(r"[*⚠️]", "", cells[5]).strip()

        themes.append({
            "name": name,
            "direction": direction,
            "heat": heat,
            "stage": stage,
            "confidence": conf,
            "proxy_etfs": _proxy_etf(name),
        })
    return themes


def extract(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    decision_date = _parse_filename(path)
    themes = _find_themes(text)

    lead_count = sum(1 for t in themes if t["direction"] == "LEAD")
    lag_count  = sum(1 for t in themes if t["direction"] == "LAG")
    high_conf  = sum(1 for t in themes if t["confidence"].lower().startswith("high"))

    all_etfs = sorted({e for t in themes for e in (t["proxy_etfs"] or [])})

    record = {
        "source": "theme-detector",
        "decision_date": decision_date,
        "scope": "market",
        "tickers": all_etfs,
        "raw_path": str(path.relative_to(path.parents[1])) if len(path.parents) > 1 else str(path),
        "summary": f"theme detector: {lead_count} LEAD / {lag_count} LAG, {high_conf} high-conf",
        "decision_content": {
            "themes": themes,
        },
        "agent_breakdown": [],
        "tuning_hooks": {
            "lead_count": lead_count,
            "lag_count": lag_count,
            "high_confidence_count": high_conf,
            "exhausting_count": sum(1 for t in themes if "exhaust" in (t["stage"] or "").lower()),
            "emerging_count":   sum(1 for t in themes if "emerg" in (t["stage"] or "").lower()),
        },
    }
    record["decision_id"] = f"theme-detector_{decision_date}"
    return record

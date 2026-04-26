"""Extract thematic-screener daily recommendation JSON.

The full file is ~700KB. We extract:
- regime snapshot
- top N themes (by mid_heat) with their top movers + 5d projection
- global warnings
"""
from __future__ import annotations
import json
from pathlib import Path

DEFAULT_TOP_THEMES = 5
DEFAULT_TOP_MOVERS_PER_THEME = 4


def _pick_target_pct(short_term: dict, horizon: str = "5d") -> float | None:
    h = (short_term or {}).get("horizons", {}).get(horizon, {})
    return h.get("target_central_pct")


def _pick_target_confidence(short_term: dict, horizon: str = "5d") -> float | None:
    h = (short_term or {}).get("horizons", {}).get(horizon, {})
    return h.get("confidence")


def extract(path: Path,
            top_themes: int = DEFAULT_TOP_THEMES,
            top_movers: int = DEFAULT_TOP_MOVERS_PER_THEME) -> dict:
    with path.open() as f:
        data = json.load(f)

    decision_date = (data.get("as_of") or "")[:10]
    themes = data.get("themes") or []
    # 排序: bullish + 高 mid_heat 先
    themes_sorted = sorted(
        themes,
        key=lambda t: (
            -(1 if (t.get("direction") or "").lower() == "bullish" else 0),
            -(t.get("mid_heat") or 0),
        ),
    )[:top_themes]

    extracted_themes: list[dict] = []
    all_movers: list[dict] = []
    for t in themes_sorted:
        movers_in = t.get("top_movers") or []
        movers_out = []
        for m in movers_in[:top_movers]:
            ticker = m.get("ticker")
            st = m.get("short_term") or {}
            row = {
                "ticker": ticker,
                "current_price": st.get("current_price"),
                "target_5d_pct": _pick_target_pct(st, "5d"),
                "target_5d_conf": _pick_target_confidence(st, "5d"),
                "target_1d_pct": _pick_target_pct(st, "1d"),
            }
            movers_out.append(row)
            all_movers.append(row)
        extracted_themes.append({
            "name": t.get("name"),
            "direction": t.get("direction"),
            "mid_heat": t.get("mid_heat"),
            "lifecycle_stage": t.get("lifecycle_stage"),
            "confidence": t.get("confidence"),
            "proxy_etfs": t.get("proxy_etfs") or [],
            "top_movers": movers_out,
        })

    regime = data.get("regime_snapshot") or {}
    warnings = data.get("global_warnings") or []

    bullish_themes = sum(1 for t in extracted_themes if (t["direction"] or "").lower() == "bullish")
    mature_count   = sum(1 for t in extracted_themes if (t["lifecycle_stage"] or "").lower() == "mature")
    low_conf_count = sum(1 for t in extracted_themes if (t["confidence"] or "").lower() == "low")

    record = {
        "source": "thematic-screener",
        "decision_date": decision_date,
        "scope": "market",
        "tickers": [m["ticker"] for m in all_movers if m.get("ticker")],
        "raw_path": str(path).split("AI投資委員會/")[-1],
        "summary": f"radar: {len(extracted_themes)} themes × {len(all_movers)} movers",
        "decision_content": {
            "framework": data.get("framework"),
            "regime_snapshot": {k: regime.get(k) for k in
                                ("regime_label", "exposure_ceiling", "breadth_score",
                                 "cycle_phase", "fear_greed") if k in regime},
            "themes": extracted_themes,
            "top_movers": all_movers,
            "global_warnings": warnings,
        },
        "agent_breakdown": [],
        "tuning_hooks": {
            "n_themes": len(extracted_themes),
            "bullish_themes": bullish_themes,
            "mature_lifecycle_count": mature_count,
            "low_confidence_count": low_conf_count,
            "warning_count": len(warnings),
            "regime_label": regime.get("regime_label"),
        },
    }
    record["decision_id"] = f"thematic-screener_{decision_date}"
    return record

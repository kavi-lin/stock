"""Sector / sub-industry heat join helper.

Pulls latest snapshots from:
  - sector/sector_logs/<DATE>_sector_intel.json    (sector composite_score)
  - skills/theme-detector/cache/theme_detector_<DATE>_*.json
        (industry_rankings + theme representative_stocks)
  - skills/theme-detector/cache/fmp_industry/snapshot_<DATE>.json
        (industry averageChange)

Joins per-ticker context via `skills/_shared/company_context.get_profile`
to resolve sector + industry.

Output schema (flat, JSON-serialisable) under tuning_hooks.sub_industry_heat:
  {
    "data_date":              "2026-05-09",        # latest snapshot date
    "ticker_sector":          "Technology",
    "ticker_industry":        "Semiconductors",
    "sector_composite_score": 61.13,               # 0-100, sector_intel
    "sector_rank":            1,                    # 1-based, by composite_score
    "sector_top_3":           true,
    "industry_avg_change_1d": 1.23,                 # %; from fmp_industry snap
    "industry_avg_rank":      4,                    # rank among 128 industries
    "industry_top_30pct":     true,
    "theme_heat_max":         0.85,                 # max theme score where ticker is rep stock
    "theme_directions":       ["bullish"],          # uniq directions of those themes
    "missing":                ["theme_detector"],   # which join sources failed
  }

Designed read-only and idempotent. Safe to call from extractors during
event_index build; failures degrade to {"missing": [...]} rather than raise.
"""
from __future__ import annotations
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "_shared"))

try:
    import company_context  # type: ignore
except Exception:                                                          # pragma: no cover
    company_context = None


_CACHE: dict[str, dict] = {}


def _latest_json(pattern: str) -> tuple[str, dict | list] | None:
    paths = sorted(glob.glob(pattern))
    if not paths:
        return None
    p = paths[-1]
    try:
        with open(p, "r", encoding="utf-8") as f:
            return p, json.load(f)
    except (OSError, ValueError):
        return None


def _load_snapshots() -> dict:
    """Read + memoise the three source snapshots once per process."""
    if "_loaded" in _CACHE:
        return _CACHE
    out: dict = {"missing": []}

    si = _latest_json(str(ROOT / "sector/sector_logs/*_sector_intel.json"))
    if si:
        out["sector_intel_path"] = si[0]
        out["sector_intel"] = si[1]
    else:
        out["missing"].append("sector_intel")

    td = _latest_json(str(ROOT / "skills/theme-detector/cache/theme_detector_*.json"))
    if td:
        out["theme_path"] = td[0]
        out["theme"] = td[1]
    else:
        out["missing"].append("theme_detector")

    fi = _latest_json(str(ROOT / "skills/theme-detector/cache/fmp_industry/snapshot_*.json"))
    if fi:
        out["industry_path"] = fi[0]
        out["industry"] = fi[1]
    else:
        out["missing"].append("fmp_industry")

    _CACHE.update(out)
    _CACHE["_loaded"] = True
    return _CACHE


def _ticker_sector_industry(ticker: str) -> tuple[str | None, str | None]:
    """Resolve (sector, industry) via company_context.get_profile.
    Returns (None, None) if profile fetch fails. Cached locally."""
    if not ticker:
        return None, None
    key = f"prof:{ticker}"
    if key in _CACHE:
        return _CACHE[key]
    if company_context is None:
        result = (None, None)
    else:
        try:
            prof = company_context.get_profile(ticker)
            result = ((prof or {}).get("sector"), (prof or {}).get("industry"))
        except Exception:
            result = (None, None)
    _CACHE[key] = result
    return result


def enrich_ticker_heat(ticker: str) -> dict:
    """Build sub_industry_heat block for one ticker. Always returns a dict;
    failed joins are listed under "missing"."""
    snap = _load_snapshots()
    sector_name, industry_name = _ticker_sector_industry(ticker)
    out: dict = {
        "ticker_sector":   sector_name,
        "ticker_industry": industry_name,
        "missing":         list(snap.get("missing", [])),
    }
    out["data_date"] = None

    si = snap.get("sector_intel")
    if isinstance(si, dict):
        out["data_date"] = si.get("verdict_date") or out["data_date"]
        sectors = si.get("sectors") or []
        if isinstance(sectors, list):
            ranked = sorted(
                (s for s in sectors if isinstance(s, dict) and s.get("composite_score") is not None),
                key=lambda s: s["composite_score"],
                reverse=True,
            )
            for idx, s in enumerate(ranked, 1):
                if (s.get("name") or "").lower() == (sector_name or "").lower():
                    out["sector_composite_score"] = s.get("composite_score")
                    out["sector_rank"] = idx
                    out["sector_top_3"] = idx <= 3
                    break

    ind = snap.get("industry")
    if isinstance(ind, list) and industry_name:
        ranked_ind = sorted(
            (r for r in ind if isinstance(r, dict) and r.get("averageChange") is not None),
            key=lambda r: r["averageChange"],
            reverse=True,
        )
        n = len(ranked_ind)
        for idx, row in enumerate(ranked_ind, 1):
            if (row.get("industry") or "").lower() == industry_name.lower():
                out["industry_avg_change_1d"] = round(float(row.get("averageChange") or 0.0), 4)
                out["industry_avg_rank"] = idx
                out["industry_top_30pct"] = (idx / n) <= 0.30 if n else False
                if not out.get("data_date"):
                    out["data_date"] = row.get("date")
                break

    td = snap.get("theme")
    if isinstance(td, dict):
        themes = td.get("themes") or []
        heat_scores: list[float] = []
        directions: set[str] = set()
        for t in themes:
            if not isinstance(t, dict):
                continue
            reps = t.get("representative_stocks") or []
            rep_syms = {(r.get("ticker") or r.get("symbol") or "").upper() for r in reps if isinstance(r, dict)}
            if ticker.upper() in rep_syms:
                score = t.get("score") or t.get("composite_score") or t.get("strength")
                try:
                    if score is not None:
                        heat_scores.append(float(score))
                except (TypeError, ValueError):
                    pass
                d = (t.get("direction") or "").lower()
                if d:
                    directions.add(d)
        if heat_scores:
            out["theme_heat_max"] = max(heat_scores)
        if directions:
            out["theme_directions"] = sorted(directions)

    return out


if __name__ == "__main__":                                                  # pragma: no cover
    for sym in sys.argv[1:] or ["AMD", "MU", "INTC", "NVDA", "CRWD"]:
        print(sym, json.dumps(enrich_ticker_heat(sym), ensure_ascii=False, indent=2))

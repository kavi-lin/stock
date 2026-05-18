#!/usr/bin/env python3
"""Compact one-table sector digest for the 產業掃描 protocol LLM.

Why: during a sector scan the LLM otherwise fires many ad-hoc `python3 -c
"import json; ..."` peeks at the phase caches — each costs a turn. This script
prints ONE compact human-readable table so the LLM reads every decision-relevant
number in a single read.

Read-only. No API/network calls. No writes. Degrades gracefully: any missing
cache value prints "n/a" instead of failing.

Usage:
    python3 sector/scripts/sector_digest.py
    python3 sector/scripts/sector_digest.py --date 2026-05-18

Sources (all on-disk caches):
    sector/cache/sector_valuation_<DATE>.json       PE TTM, pe_zscore_1y, rs_vs_spy_3m
    sector/cache/sector_smart_money_<DATE>.json     insider ratio, senate net buy
    sector/cache/sector_earnings_pulse_<DATE>.json  beat_rate_30d
    sector/cache/sector_news_<DATE>.json            news-catalyst count per sector
    skills/theme-detector/cache/theme_detector_*    theme heat, sector uptrend_ratio
    phase0_read_caches.py stdout                    breadth / FTD / market-top / FRED macro header
"""
from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "sector" / "cache"
THEME_CACHE_DIR = ROOT / "skills" / "theme-detector" / "cache"
PHASE0_SCRIPT = ROOT / "sector" / "scripts" / "phase0_read_caches.py"

# Canonical 11 sector names (cache key order)
SECTORS = [
    "Technology", "Healthcare", "Energy", "Financials", "Industrials",
    "Materials", "Communication", "Consumer_Discretionary",
    "Consumer_Staples", "Utilities", "Real_Estate",
]

# theme-detector sector_uptrend uses GICS-ish display names
UPTREND_NAME_MAP = {
    "Technology": "Technology",
    "Healthcare": "Healthcare",
    "Energy": "Energy",
    "Financials": "Financial Services",
    "Industrials": "Industrials",
    "Materials": "Basic Materials",
    "Communication": "Communication Services",
    "Consumer_Discretionary": "Consumer Cyclical",
    "Consumer_Staples": "Consumer Defensive",
    "Utilities": "Utilities",
    "Real_Estate": "Real Estate",
}


def load_json(path: Path):
    """Return parsed JSON or None (never raises)."""
    try:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except (OSError, json.JSONDecodeError):
        return None


def latest_theme_cache():
    files = sorted(glob.glob(str(THEME_CACHE_DIR / "theme_detector_*.json")))
    return Path(files[-1]) if files else None


def fmt(v, nd=2, pct=False):
    if v is None:
        return "n/a"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if pct:
        return f"{f * 100:+.1f}%"
    return f"{f:.{nd}f}"


def run_phase0():
    """Return phase0_read_caches.py layers dict, or {} on any failure."""
    if not PHASE0_SCRIPT.exists():
        return {}
    try:
        proc = subprocess.run(
            [sys.executable, str(PHASE0_SCRIPT)],
            capture_output=True, text=True, timeout=120,
        )
        return (json.loads(proc.stdout) or {}).get("layers", {})
    except (subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return {}


def theme_heat_by_sector(theme_data):
    """Map canonical sector -> max bullish theme heat touching it.

    Uses each theme's sector_weights / cross_sector_reach to attribute heat.
    """
    out = {s: None for s in SECTORS}
    if not theme_data:
        return out
    themes = (theme_data.get("themes") or {}).get("all") or []
    # display-name -> canonical
    disp_to_canon = {v: k for k, v in UPTREND_NAME_MAP.items()}
    for t in themes:
        heat = t.get("heat")
        if heat is None:
            continue
        touched = set()
        for sw in (t.get("sector_weights") or {}):
            touched.add(disp_to_canon.get(sw, sw))
        for cs in (t.get("cross_sector_reach") or []):
            touched.add(disp_to_canon.get(cs, cs))
        for s in touched:
            if s in out and (out[s] is None or heat > out[s]):
                out[s] = heat
    return out


def uptrend_by_sector(theme_data):
    out = {s: None for s in SECTORS}
    if not theme_data:
        return out
    su = theme_data.get("sector_uptrend") or {}
    for canon, disp in UPTREND_NAME_MAP.items():
        blk = su.get(disp) or su.get(canon)
        if isinstance(blk, dict):
            out[canon] = blk.get("ratio")
    return out


def print_macro_header(layers):
    breadth = (layers.get("breadth") or {}).get("data") or {}
    ftd = (layers.get("ftd") or {}).get("data") or {}
    mtop = (layers.get("market_top") or {}).get("data") or {}
    fred = (layers.get("fred") or {}).get("data") or {}

    bcomp = breadth.get("composite") or {}
    mt_comp = mtop.get("composite") or {}
    ftd_state = (ftd.get("market_state") or {})

    print("─" * 78)
    print("MACRO HEADER")
    print("─" * 78)
    print(f"  Breadth     : score {fmt(bcomp.get('composite_score'))}  "
          f"zone {bcomp.get('zone') or 'n/a'}  "
          f"guidance {bcomp.get('exposure_guidance') or 'n/a'}")
    ftd_qual = (ftd.get("quality_score") or {})
    print(f"  FTD         : state "
          f"{ftd_state.get('combined_state') or ftd_state.get('state') or 'n/a'}  "
          f"quality {fmt(ftd_qual.get('total_score'), 0)}  "
          f"dual-confirm {ftd_state.get('dual_confirmation') if ftd_state else 'n/a'}")
    print(f"  Market-Top  : score {fmt(mt_comp.get('composite_score'))}  "
          f"zone {mt_comp.get('zone') or 'n/a'}  "
          f"risk-budget {mt_comp.get('risk_budget') or 'n/a'}")
    if fred:
        print(f"  FRED regime : {fred.get('regime_label') or 'n/a'}  "
              f"conf {fmt(fred.get('regime_confidence'))}  "
              f"macro {fmt(fred.get('macro_scores_composite'), 0)}")
        favor = ", ".join(fred.get("sector_rotation_favor") or []) or "n/a"
        avoid = ", ".join(fred.get("sector_rotation_avoid") or []) or "n/a"
        print(f"               favor: {favor}")
        print(f"               avoid: {avoid}")
    else:
        print("  FRED regime : n/a")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description="Compact sector digest table for 產業掃描")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                    help="Cache date YYYY-MM-DD (default: today)")
    args = ap.parse_args()
    date = args.date

    valuation = load_json(CACHE_DIR / f"sector_valuation_{date}.json") or {}
    smartmoney = load_json(CACHE_DIR / f"sector_smart_money_{date}.json") or {}
    earnings = load_json(CACHE_DIR / f"sector_earnings_pulse_{date}.json") or {}
    news = load_json(CACHE_DIR / f"sector_news_{date}.json") or {}
    theme_path = latest_theme_cache()
    theme_data = load_json(theme_path) if theme_path else None

    val_s = valuation.get("sectors") or {}
    sm_s = smartmoney.get("sectors") or {}
    ep_s = earnings.get("sectors") or {}
    news_s = news.get("sectors") or {}

    heat = theme_heat_by_sector(theme_data)
    uptrend = uptrend_by_sector(theme_data)

    layers = run_phase0()

    print()
    print(f"SECTOR DIGEST — {date}")
    missing = []
    if not val_s:   missing.append("valuation")
    if not sm_s:    missing.append("smart_money")
    if not ep_s:    missing.append("earnings_pulse")
    if not news_s:  missing.append("sector_news")
    if theme_data is None: missing.append("theme_detector")
    if missing:
        print(f"  (missing caches: {', '.join(missing)} — those columns show n/a)")
    print()

    print_macro_header(layers)

    print("─" * 78)
    hdr = (f"{'Sector':<22} {'Uptr':>6} {'PE_TTM':>8} {'z1y':>7} "
           f"{'RS3m':>8} {'Heat':>6} {'News':>5} {'InsR':>6} {'SenN':>5} {'Beat':>6}")
    print(hdr)
    print("─" * 78)

    for s in SECTORS:
        v = val_s.get(s) or {}
        sm = sm_s.get(s) or {}
        ep = ep_s.get(s) or {}
        nlist = news_s.get(s)
        news_ct = len(nlist) if isinstance(nlist, list) else None

        row = (
            f"{s:<22} "
            f"{fmt(uptrend.get(s), 3):>6} "
            f"{fmt(v.get('pe_ttm')):>8} "
            f"{fmt(v.get('pe_zscore_1y')):>7} "
            f"{fmt(v.get('rs_vs_spy_3m'), pct=True):>8} "
            f"{fmt(heat.get(s), 1):>6} "
            f"{(str(news_ct) if news_ct is not None else 'n/a'):>5} "
            f"{fmt(sm.get('insider_acquired_disposed_ratio_q'), 2):>6} "
            f"{(str(sm['senate_net_buy_30d']) if sm.get('senate_net_buy_30d') is not None else 'n/a'):>5} "
            f"{fmt(ep.get('beat_rate_30d'), 2):>6}"
        )
        print(row)

    print("─" * 78)
    print("Uptr=uptrend_ratio  z1y=pe_zscore_1y  RS3m=rs_vs_spy_3m  Heat=max bullish")
    print("theme heat  News=catalyst article count  InsR=insider acq/disp ratio")
    print("SenN=senate net buy 30d  Beat=earnings beat_rate_30d")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

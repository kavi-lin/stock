#!/usr/bin/env python3
"""
Pre-Market Morning Brief — deterministic one-page open-prep digest.

Aggregates the warm daily_update.sh caches (regime / breadth / FTD / market-top,
thematic radar, momentum screen, structural watchlist, upcoming events) plus a
handful of fresh FMP calls (index quotes, biggest movers, sector performance,
watchlist overnight gaps) into reports/PREMARKET_<DATE>.md.

Design:
  * NO LLM by default — every section is a deterministic render of existing data
    so it's fast and reproducible for a one-shot pre-open run.
  * Reuses caches wherever possible; fresh FMP is limited to movers/quotes and is
    routed through scripts/_shared/fmp_pool (shared 250/min budget).
  * Graceful degradation: with FMP_API_KEY unset the cache-only sections still
    render and the fresh sections print a warning instead of failing.
  * Staleness guard: any source cache older than STALE_HOURS is flagged in the
    footer rather than silently used.

Usage:
  python3 scripts/premarket/morning_brief.py --date 2026-05-29 \
      --output reports/PREMARKET_2026-05-29.md
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
import time
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from scripts._shared import fmp_pool
except Exception:  # pragma: no cover - pool should always import
    fmp_pool = None

STALE_HOURS = 36.0
INDICES = [("^GSPC", "S&P 500"), ("^IXIC", "Nasdaq Comp"), ("^DJI", "Dow Jones"), ("^VIX", "VIX")]

_warnings: list[str] = []
_sources: list[str] = []
_fresh_calls = 0


# ── cache helpers ──────────────────────────────────────────────────────────
def _latest(pattern: str) -> str | None:
    fs = glob.glob(os.path.join(_ROOT, pattern))
    return max(fs, key=os.path.getmtime) if fs else None


def _load_json(path: str | None):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        _warnings.append(f"failed to read {os.path.relpath(path, _ROOT)}: {e}")
        return None


def _note_source(path: str | None, label: str) -> None:
    if not path or not os.path.exists(path):
        _warnings.append(f"{label}: source missing")
        return
    age_h = (time.time() - os.path.getmtime(path)) / 3600.0
    rel = os.path.relpath(path, _ROOT)
    _sources.append(rel)
    if age_h > STALE_HOURS:
        _warnings.append(f"{label} cache is {age_h:.0f}h old (> {STALE_HOURS:.0f}h) → possibly stale")


def _fmt_pct(v, digits=2) -> str:
    try:
        return f"{float(v):+.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_num(v, digits=2) -> str:
    try:
        return f"{float(v):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def _have_key() -> bool:
    if not os.environ.get("FMP_API_KEY"):
        return False
    if fmp_pool is None:
        return False
    return True


def _fmp_get(path, params, stable=True):
    global _fresh_calls
    if not _have_key():
        return None
    _fresh_calls += 1
    return fmp_pool.get(path, params, stable=stable, timeout=15)


# ── section renderers ──────────────────────────────────────────────────────
def section_regime(data) -> list[str]:
    out = ["## 1. Regime Snapshot", ""]
    if not data:
        out.append("_data.json unavailable — regime snapshot skipped._")
        out.append("")
        return out
    b = data.get("breadth") or {}
    ftd = data.get("ftd") or {}
    mt = data.get("market_top") or {}
    mk = data.get("market") or {}
    out.append(f"- **Breadth**: {_fmt_num(b.get('score'), 1)}/100 — {b.get('zone', '?')} "
               f"(exposure {b.get('exposure_ceiling', '?')})")
    out.append(f"- **FTD**: {ftd.get('state', '?')} — {ftd.get('signal', '')} "
               f"(exposure {ftd.get('exposure_range', '?')}, day {ftd.get('days_since_ftd', '?')})")
    out.append(f"- **Market-Top**: {_fmt_num(mt.get('composite_score'), 1)}/100 — {mt.get('zone', '?')} "
               f"(risk budget {mt.get('risk_budget', '?')})")
    out.append(f"- **Regime**: {mk.get('regime', '?')} · cycle {mk.get('cycle_phase', '?')} · "
               f"Fear/Greed {_fmt_num(mk.get('fear_greed'), 0)} ({mk.get('fear_greed_label', '?')}) · "
               f"macro {mk.get('macro_multiplier', '?')}")
    if mk.get("hot_sectors"):
        out.append(f"- **Hot**: {', '.join(mk['hot_sectors'])}  |  **Cold**: "
                   f"{', '.join((mk.get('cold_sectors') or [])[:4])}")
    out.append("")
    return out


def section_indices() -> list[str]:
    out = ["## 2. Overnight / Pre-Market Index Moves", ""]
    if not _have_key():
        out.append("_FMP_API_KEY unset — index moves skipped._")
        out.append("")
        return out
    reqs = [{"path": "quote", "params": {"symbol": sym}, "stable": True} for sym, _ in INDICES]
    global _fresh_calls
    _fresh_calls += len(reqs)
    results = fmp_pool.fetch_many(reqs, max_workers=4)
    out.append("| Index | Last | Chg% |")
    out.append("|---|--:|--:|")
    any_row = False
    for (sym, name), res in zip(INDICES, results):
        row = res[0] if isinstance(res, list) and res else (res if isinstance(res, dict) else None)
        if not row:
            out.append(f"| {name} ({sym}) | — | — |")
            continue
        any_row = True
        out.append(f"| {name} ({sym}) | {_fmt_num(row.get('price'))} | "
                   f"{_fmt_pct(row.get('changePercentage', row.get('changesPercentage')))} |")
    if not any_row:
        _warnings.append("index quotes returned no data")
    out.append("")
    return out


def _chg_pct(r):
    try:
        return float(r.get("changePercentage", r.get("changesPercentage")))
    except (TypeError, ValueError):
        return None


def _movers_table(rows, n=10) -> list[str]:
    out = ["| Ticker | Chg% | Price | Name |", "|---|--:|--:|---|"]
    for r in (rows or [])[:n]:
        out.append(f"| {r.get('symbol', '?')} | "
                   f"{_fmt_pct(_chg_pct(r))} | "
                   f"{_fmt_num(r.get('price'))} | {str(r.get('name', ''))[:28]} |")
    if len(out) == 2:
        out.append("| — | | | |")
    return out


def section_movers() -> list[str]:
    # 權值股 movers only: quote the curated mega-cap universe (SECTOR_UNIVERSE,
    # ~131 large caps) and rank by overnight move — deliberately NOT the FMP
    # market-wide biggest-gainers/losers feed, which is dominated by sub-$5 penny
    # stocks and leveraged ETNs. price>=$5 is a belt-and-suspenders guard.
    out = ["## 3. Biggest Movers — Large Caps (overnight)", ""]
    if not _have_key():
        out.append("_FMP_API_KEY unset — movers skipped._")
        out.append("")
        return out
    try:
        from skills._shared.company_context import SECTOR_UNIVERSE
        universe = sorted({t for v in SECTOR_UNIVERSE.values() for t in v})
    except Exception as e:
        _warnings.append(f"mega-cap universe load failed: {e}")
        universe = []
    if not universe:
        out.append("_mega-cap universe unavailable._")
        out.append("")
        return out

    global _fresh_calls
    reqs = [{"path": "quote", "params": {"symbol": t}, "stable": True} for t in universe]
    _fresh_calls += len(reqs)
    rows = []
    for res in fmp_pool.fetch_many(reqs, max_workers=16):
        row = res[0] if isinstance(res, list) and res else (res if isinstance(res, dict) else None)
        if not row:
            continue
        price = row.get("price")
        pct = _chg_pct(row)
        try:
            if price is None or float(price) < 5 or pct is None:
                continue
        except (TypeError, ValueError):
            continue
        rows.append(row)

    if not rows:
        out.append("_no large-cap quotes returned._")
        out.append("")
        return out
    rows.sort(key=lambda r: _chg_pct(r) or 0.0, reverse=True)
    out.append(f"_(ranked across {len(rows)} mega-cap names)_")
    out.append("")
    out.append("### Gainers")
    out += _movers_table(rows[:10])
    out.append("")
    out.append("### Losers")
    out += _movers_table(list(reversed(rows[-10:])))
    out.append("")
    return out


def section_sector_perf(date_str) -> list[str]:
    out = ["## 4. Sector Performance (prev session)", ""]
    if not _have_key():
        out.append("_FMP_API_KEY unset — sector performance skipped._")
        out.append("")
        return out
    rows = _fmp_get("sector-performance-snapshot", {"date": date_str})
    if not isinstance(rows, list) or not rows:
        out.append("_sector performance unavailable._")
        out.append("")
        return out

    def _pct(r):
        try:
            return float(r.get("changesPercentage", r.get("averageChange", 0)))
        except (TypeError, ValueError):
            return 0.0

    rows = sorted(rows, key=_pct, reverse=True)
    out.append("| Sector | Chg% |")
    out.append("|---|--:|")
    for r in rows:
        out.append(f"| {r.get('sector', '?')} | {_fmt_pct(_pct(r))} |")
    out.append("")
    return out


def section_earnings(data, date_str) -> list[str]:
    out = ["## 5. Today's Earnings", ""]
    events = (data or {}).get("upcoming_events") or []
    today = [e for e in events if e.get("category") == "earnings" and e.get("date") == date_str]
    if not today:
        out.append("_No tracked earnings (>$2B universe) scheduled for today._")
        out.append("")
        return out
    out.append("| Time | Ticker | Estimate |")
    out.append("|---|---|---|")
    for e in today:
        p = e.get("source_payload") or {}
        t = p.get("time") or e.get("time") or "—"
        out.append(f"| {t or '—'} | {', '.join(e.get('tickers') or []) or '?'} | "
                   f"{e.get('description', '')} |")
    out.append("")
    return out


def section_economic(data, date_str) -> list[str]:
    out = ["## 6. Today's Economic Events", ""]
    events = (data or {}).get("upcoming_events") or []
    econ_cats = {"econ", "economic", "macro", "fed", "fomc", "data"}
    today = [e for e in events
             if e.get("date") == date_str and (e.get("category") in econ_cats)]
    if not today:
        out.append("_No tracked economic events scheduled for today._")
        out.append("")
        return out
    out.append("| Time | Event | Impact |")
    out.append("|---|---|---|")
    for e in today:
        out.append(f"| {e.get('time') or '—'} | {e.get('title', '?')} | {e.get('impact', '')} |")
    out.append("")
    return out


def section_watchlist(date_str) -> list[str]:
    out = ["## 7. Watchlist Overnight Gaps (structural)", ""]
    wl_path = os.path.join(_ROOT, "news", "news_logs", "structural_watchlist.json")
    _note_source(wl_path, "structural_watchlist")
    wl = _load_json(wl_path)
    cands = (wl or {}).get("candidates") or []
    if not cands:
        out.append("_structural watchlist empty._")
        out.append("")
        return out
    tickers = [c.get("ticker") for c in cands if c.get("ticker")][:25]
    quotes = {}
    if _have_key() and tickers:
        global _fresh_calls
        reqs = [{"path": "quote", "params": {"symbol": t}, "stable": True} for t in tickers]
        _fresh_calls += len(reqs)
        for t, res in zip(tickers, fmp_pool.fetch_many(reqs, max_workers=12)):
            row = res[0] if isinstance(res, list) and res else (res if isinstance(res, dict) else None)
            if row:
                quotes[t] = row
    else:
        out.append("_(FMP_API_KEY unset — showing watchlist without live gaps)_")
    out.append("| Ticker | Sector | Chg% | Hits(14d) | Days since hit |")
    out.append("|---|---|--:|--:|--:|")
    # Sort by absolute overnight move when we have quotes, else by hit recency.
    def _chg(c):
        q = quotes.get(c.get("ticker"))
        try:
            return abs(float(q.get("changePercentage", q.get("changesPercentage", 0)))) if q else -1
        except (TypeError, ValueError):
            return -1
    for c in sorted(cands, key=_chg, reverse=True)[:15]:
        t = c.get("ticker")
        q = quotes.get(t)
        chg = _fmt_pct(q.get("changePercentage", q.get("changesPercentage"))) if q else "—"
        cell = f"**{chg}**" if (q and abs(float(q.get("changePercentage", q.get("changesPercentage", 0)) or 0)) > 3) else chg
        out.append(f"| {t} | {c.get('sector', '?')} | {cell} | "
                   f"{c.get('hit_count_14d', '?')} | {c.get('days_since_last_hit', '?')} |")
    out.append("")
    return out


def section_thematic() -> list[str]:
    out = ["## 8. Thematic Radar (top themes)", ""]
    path = _latest("skills/thematic-screener/data/recommendations/*.json")
    _note_source(path, "thematic_recommendations")
    recs = _load_json(path)
    themes = (recs or {}).get("themes") or []
    if not themes:
        out.append("_no thematic recommendations available._")
        out.append("")
        return out
    for t in themes[:5]:
        movers = t.get("top_movers") or []
        names = []
        for m in movers[:4]:
            tk = m.get("ticker")
            st = (m.get("short_term") or {}).get("horizons", {}).get("5d", {})
            pct = st.get("target_central_pct")
            names.append(f"{tk} ({_fmt_pct(pct, 1)})" if pct is not None else str(tk))
        out.append(f"- **{t.get('name', '?')}** [{t.get('direction', '?')} · "
                   f"{t.get('heat_label', '?')} · {t.get('lifecycle_stage', '?')}]: "
                   f"{', '.join(names) if names else '—'}")
    out.append("")
    return out


def section_momentum() -> list[str]:
    out = ["## 9. Momentum Leaders (latest screen)", ""]
    path = _latest("skills/momentum-monitor/cache/screen_*.csv")
    _note_source(path, "momentum_screen")
    if not path:
        out.append("_no momentum screen csv available._")
        out.append("")
        return out
    try:
        with open(path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        _warnings.append(f"momentum csv read failed: {e}")
        rows = []
    if not rows:
        out.append("_momentum screen empty._")
        out.append("")
        return out
    out.append("| Rank | Ticker | Score | 1d% | Stage | Signals |")
    out.append("|--:|---|--:|--:|---|---|")
    for r in rows[:10]:
        sig = (r.get("signals") or "").replace("|", ", ")[:46]
        out.append(f"| {r.get('rank', '?')} | {r.get('ticker', '?')} | {r.get('score', '?')} | "
                   f"{_fmt_pct(r.get('return_1d_pct'), 2)} | {r.get('stage', '?')} | {sig} |")
    out.append("")
    return out


def section_binary(data, date_str) -> list[str]:
    out = ["## 10. Watch Items / Binary Risks (≤48h)", ""]
    events = (data or {}).get("upcoming_events") or []

    # Recompute the 48h window from the report date rather than trusting the
    # stored within_48h flag (which is only fresh as of the last bridge run).
    try:
        ref = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        ref = datetime.now().date()

    def _within(e, days=2):
        d = e.get("date")
        if not d:
            return False
        try:
            ed = datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            return False
        return 0 <= (ed - ref).days <= days

    flagged = [e for e in events if _within(e) and (e.get("is_binary") or e.get("impact") == "high")]
    risks = (data or {}).get("binary_risks") or []
    if not flagged and not risks:
        out.append("_No binary catalysts in the next 48h._")
        out.append("")
        return out
    for r in risks[:8]:
        out.append(f"- ⚠️ {r.get('title', r) if isinstance(r, dict) else r}")
    for e in sorted(flagged, key=lambda e: e.get("date", ""))[:12]:
        tag = "🔴 binary" if e.get("is_binary") else "🟡 high-impact"
        out.append(f"- {tag} · {e.get('date', '?')} · {e.get('title', '?')} "
                   f"({e.get('category', '')}, impact {e.get('impact', '?')})")
    out.append("")
    return out


def section_footer() -> list[str]:
    out = ["---", ""]
    out.append(f"_Sources: {len(set(_sources))} cache files + {_fresh_calls} fresh FMP calls._")
    if _warnings:
        out.append("")
        out.append("**⚠️ Data warnings:**")
        for w in _warnings:
            out.append(f"- {w}")
    return out


def build_report(date_str: str) -> str:
    data_path = os.path.join(_ROOT, "Dashboard", "data.json")
    _note_source(data_path, "data.json")
    data = _load_json(data_path)

    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Pre-Market Morning Brief — {date_str}",
        f"_Generated {gen} · pre-open snapshot (EOD + overnight, no live intraday)_",
        "",
    ]
    lines += section_regime(data)
    lines += section_indices()
    lines += section_movers()
    lines += section_sector_perf(date_str)
    lines += section_earnings(data, date_str)
    lines += section_economic(data, date_str)
    lines += section_watchlist(date_str)
    lines += section_thematic()
    lines += section_momentum()
    lines += section_binary(data, date_str)
    lines += section_footer()
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Pre-market morning brief renderer")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                    help="Report date YYYY-MM-DD (default: today local)")
    ap.add_argument("--output", default=None, help="Output MD path (default: reports/PREMARKET_<DATE>.md)")
    args = ap.parse_args()

    out_path = args.output or os.path.join(_ROOT, "reports", f"PREMARKET_{args.date}.md")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    report = build_report(args.date)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[morning_brief] wrote {os.path.relpath(out_path, _ROOT)} "
          f"({_fresh_calls} fresh FMP calls, {len(_warnings)} warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

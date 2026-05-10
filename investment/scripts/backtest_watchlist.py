#!/usr/bin/env python3
"""V2.19.1 — backtest structural_watchlist signal quality.

Goal: validate that watchlist `first_seen` events lead to:
  (A) earnings-analyst structural_shift tier graduation (CANDIDATE/CONFIRMED), OR
  (B) price outperformance vs SPY/sector ETF benchmark.

Inputs:
  - news/news_logs/watchlist_lifecycle.jsonl   (V2.19.1 append-only event log)
  - news/news_logs/watchlist_history/*.json    (V2.19.1 daily snapshots)
  - skills/earnings-analyst/cache/*.json       (tier ground truth)
  - FMP /historical-price-eod                  (price returns)

Outputs:
  - reports/WATCHLIST_BACKTEST_<DATE>.md       (markdown report)
  - reports/watchlist_backtest_<DATE>.json     (raw per-ticker stats)

Sample size warning: <50 events in first 2-4 weeks of operation = directional
sanity check only. Statistical confidence requires 6+ months (n>100 events).

Usage:
    python3 investment/scripts/backtest_watchlist.py
        rc=0 → report written
        rc=1 → no events found (waiting for accrual)
        rc=2 → critical error (price fetch / IO)

V2.19.1: SKELETON — implements (A) earnings tier check end-to-end;
(B) price returns require FMP price helper which is not yet wired here.
TODO V2.20: implement price returns + sector ETF benchmark + alpha distribution.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT             = Path(__file__).resolve().parents[2]
LIFECYCLE_LOG    = ROOT / "news" / "news_logs" / "watchlist_lifecycle.jsonl"
HISTORY_DIR      = ROOT / "news" / "news_logs" / "watchlist_history"
EARNINGS_CACHE   = ROOT / "skills" / "earnings-analyst" / "cache"
REPORTS_DIR      = ROOT / "reports"

# Time windows for forward-return evaluation
RETURN_HORIZONS_DAYS = (5, 15, 45, 90)

# Sector → ETF ticker for sector-relative alpha. Aligned with sector names emitted
# by news_protocol_v2 / theme-detector. Unknown sector → SPY only.
SECTOR_ETF_MAP = {
    "Memory Semiconductors":      "SOXX",
    "Semiconductors":             "SOXX",
    "Semis":                      "SOXX",
    "Technology":                 "XLK",
    "Tech":                       "XLK",
    "Energy":                     "XLE",
    "Energy_Services_LNG":        "XLE",
    "Financials":                 "XLF",
    "Healthcare":                 "XLV",
    "Pharma":                     "XLV",
    "Biotech":                    "XBI",
    "Consumer Discretionary":     "XLY",
    "Consumer Staples":           "XLP",
    "Industrials":                "XLI",
    "Utilities":                  "XLU",
    "Real Estate":                "XLRE",
    "Materials":                  "XLB",
    "Communication Services":     "XLC",
    "Defense":                    "ITA",
    "Aerospace":                  "ITA",
    "Data_Center_Power":          "XLU",  # closest proxy
}

# Module-level price cache: avoid re-fetching SPY / sector ETF for every ticker
_PRICE_CACHE: dict[str, list[dict]] = {}

# V2.20.0 — random sector baseline universe
# 5 representative tickers per sector ETF for "did watchlist beat random sector
# member?" sanity check. Light coverage; enough for directional baseline.
RANDOM_SECTOR_TICKERS = {
    "SOXX":  ["AVGO", "AMAT", "LRCX", "KLAC", "QCOM"],
    "XLK":   ["MSFT", "AAPL", "ADBE", "CRM", "ORCL"],
    "XLE":   ["XOM", "CVX", "COP", "EOG", "SLB"],
    "XLF":   ["JPM", "BAC", "WFC", "GS", "MS"],
    "XLV":   ["UNH", "JNJ", "PFE", "ABBV", "TMO"],
    "XBI":   ["VRTX", "REGN", "GILD", "BIIB", "MRNA"],
    "XLY":   ["AMZN", "TSLA", "HD", "MCD", "NKE"],
    "XLP":   ["PG", "KO", "PEP", "WMT", "COST"],
    "XLI":   ["CAT", "GE", "BA", "UNP", "HON"],
    "XLU":   ["NEE", "DUK", "SO", "AEP", "D"],
    "XLRE":  ["AMT", "PLD", "CCI", "EQIX", "PSA"],
    "XLB":   ["LIN", "APD", "SHW", "FCX", "NEM"],
    "XLC":   ["GOOGL", "META", "DIS", "NFLX", "CMCSA"],
    "ITA":   ["LMT", "RTX", "NOC", "GD", "BA"],
}


def _fetch_price_series(ticker: str) -> list[dict]:
    """Fetch FMP /stable/historical-price-eod/light?symbol=<T>; return
    [{date, close}, ...] sorted desc (newest first per FMP).

    Uses light endpoint: flat array of {symbol, date, price, volume}.
    Mapped to {date, close} for internal consistency.

    Cached in process. FMP_API_KEY required; missing key → empty list.
    Failure modes (network / 4xx / 5xx) → empty list, never raise.
    """
    if ticker in _PRICE_CACHE:
        return _PRICE_CACHE[ticker]

    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        _PRICE_CACHE[ticker] = []
        return []

    url = (
        "https://financialmodelingprep.com/stable/historical-price-eod/light"
        f"?symbol={urllib.parse.quote(ticker)}"
        f"&apikey={urllib.parse.quote(api_key)}"
    )
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            if r.status != 200:
                _PRICE_CACHE[ticker] = []
                return []
            payload = json.loads(r.read().decode("utf-8"))
        series = payload if isinstance(payload, list) else (payload.get("historical") or [])
        # Defensive: map price → close
        cleaned = [{"date": p.get("date"), "close": p.get("price") or p.get("close")}
                   for p in series if p.get("date") and (p.get("price") or p.get("close")) is not None]
        _PRICE_CACHE[ticker] = cleaned
        time.sleep(0.3)  # be polite to FMP
        return cleaned
    except Exception as e:
        print(f"[backtest_watchlist] FMP fetch {ticker} failed: {e}", file=sys.stderr)
        _PRICE_CACHE[ticker] = []
        return []


def _close_at_or_after(by_date: dict[str, float], target_iso: str) -> tuple[str | None, float | None]:
    """Find first available trading-day close at or after target date.
    Walks forward up to 7 calendar days (handles weekends + holidays)."""
    try:
        target = datetime.strptime(target_iso, "%Y-%m-%d").date()
    except ValueError:
        return None, None
    for offset in range(8):
        check = (target + timedelta(days=offset)).isoformat()
        if check in by_date:
            return check, by_date[check]
    return None, None


def load_lifecycle_events() -> list[dict]:
    if not LIFECYCLE_LOG.exists():
        return []
    events: list[dict] = []
    with LIFECYCLE_LOG.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def collapse_by_ticker(events: list[dict]) -> dict[str, dict]:
    """Per-ticker timeline: first_seen_date, evicted_date, graduations[], continued_count."""
    tk: dict[str, dict] = defaultdict(lambda: {
        "first_seen": None, "evicted": None, "continued": 0,
        "graduated_candidate_first": None, "graduated_confirmed_first": None,
        "events": [],
    })
    for ev in events:
        t = ev.get("ticker")
        if not t:
            continue
        slot = tk[t]
        slot["events"].append(ev)
        e = ev.get("event")
        d = ev.get("date")
        if e == "first_seen" and not slot["first_seen"]:
            # V2.19.2 — use first_observed (news date) for backtest anchor, not
            # event date (watchlist algo first-detection date). Difference
            # matters for bootstrap runs when 30d lookback finds existing hits.
            slot["first_seen"] = ev.get("first_observed") or d
            slot["sector"] = ev.get("sector")
            slot["credibility"] = ev.get("credibility")
        elif e == "continued":
            slot["continued"] += 1
        elif e == "evicted" and not slot["evicted"]:
            slot["evicted"] = d
        elif e == "graduated_candidate" and not slot["graduated_candidate_first"]:
            slot["graduated_candidate_first"] = d
        elif e == "graduated_confirmed" and not slot["graduated_confirmed_first"]:
            slot["graduated_confirmed_first"] = d
    return dict(tk)


def days_between(d1: str, d2: str) -> int | None:
    try:
        a = datetime.strptime(d1, "%Y-%m-%d").date()
        b = datetime.strptime(d2, "%Y-%m-%d").date()
        return (b - a).days
    except (ValueError, TypeError):
        return None


def compute_tier_lead_time(timeline: dict[str, dict]) -> dict:
    """For each ticker that graduated, compute days from first_seen → graduation.

    Returns:
        {
          "candidate": [(ticker, lead_days, sector), ...],
          "confirmed": [(ticker, lead_days, sector), ...],
          "still_active": [...],
          "evicted_no_graduation": [...],
        }
    """
    out = {"candidate": [], "confirmed": [], "still_active": [], "evicted_no_graduation": []}
    for t, slot in timeline.items():
        first = slot.get("first_seen")
        if not first:
            continue
        if slot.get("graduated_confirmed_first"):
            ld = days_between(first, slot["graduated_confirmed_first"])
            out["confirmed"].append((t, ld, slot.get("sector")))
        elif slot.get("graduated_candidate_first"):
            ld = days_between(first, slot["graduated_candidate_first"])
            out["candidate"].append((t, ld, slot.get("sector")))
        elif slot.get("evicted"):
            out["evicted_no_graduation"].append((t, days_between(first, slot["evicted"]), slot.get("sector")))
        else:
            out["still_active"].append((t, slot.get("continued", 0), slot.get("sector")))
    return out


def fetch_forward_returns(ticker: str, base_date: str, sector: str | None) -> dict:
    """V2.19.2 — fetch ticker + SPY (+ sector ETF if mapped) prices, compute
    forward returns at horizons {5d, 15d, 45d, 90d} and alpha vs benchmarks.

    Returns:
        {
          "r_5d":            float | None,    # raw ticker return %
          "r_15d":           ...,
          "r_45d":           ...,
          "r_90d":           ...,
          "alpha_spy_5d":    float | None,    # ticker − SPY %
          "alpha_spy_15d":   ...,
          ...
          "alpha_sector_5d": float | None,    # ticker − sector ETF %
          ...
          "sector_etf":      str | None,
          "base_close":      float | None,
          "_status":         "ok | partial | no_data | api_unavailable"
        }
    """
    out: dict = {f"r_{h}d": None for h in RETURN_HORIZONS_DAYS}
    out.update({f"alpha_spy_{h}d": None for h in RETURN_HORIZONS_DAYS})
    out.update({f"alpha_sector_{h}d": None for h in RETURN_HORIZONS_DAYS})
    out["sector_etf"] = SECTOR_ETF_MAP.get(sector or "")

    if not os.getenv("FMP_API_KEY"):
        out["_status"] = "api_unavailable"
        return out

    series = _fetch_price_series(ticker)
    if not series:
        out["_status"] = "no_data"
        return out

    by_date = {p["date"]: p["close"] for p in series}
    _, base_close = _close_at_or_after(by_date, base_date)
    if base_close is None:
        out["_status"] = "no_data"
        return out
    out["base_close"] = round(base_close, 2)

    spy_series = _fetch_price_series("SPY")
    spy_by_date = {p["date"]: p["close"] for p in spy_series}
    _, spy_base = _close_at_or_after(spy_by_date, base_date)

    sector_etf = out["sector_etf"]
    sec_series = _fetch_price_series(sector_etf) if sector_etf else []
    sec_by_date = {p["date"]: p["close"] for p in sec_series}
    _, sec_base = _close_at_or_after(sec_by_date, base_date) if sec_series else (None, None)

    today_iso = date.today().isoformat()
    horizon_hits = 0
    for h in RETURN_HORIZONS_DAYS:
        target = (datetime.strptime(base_date, "%Y-%m-%d").date()
                  + timedelta(days=h)).isoformat()
        # Skip horizons that haven't elapsed yet
        if target > today_iso:
            continue

        _, t_close = _close_at_or_after(by_date, target)
        if t_close is None or base_close is None:
            continue
        r = (t_close / base_close - 1) * 100
        out[f"r_{h}d"] = round(r, 2)
        horizon_hits += 1

        if spy_base:
            _, s_close = _close_at_or_after(spy_by_date, target)
            if s_close is not None:
                spy_r = (s_close / spy_base - 1) * 100
                out[f"alpha_spy_{h}d"] = round(r - spy_r, 2)

        if sec_base:
            _, sec_close_t = _close_at_or_after(sec_by_date, target)
            if sec_close_t is not None:
                sec_r = (sec_close_t / sec_base - 1) * 100
                out[f"alpha_sector_{h}d"] = round(r - sec_r, 2)

    out["_status"] = "ok" if horizon_hits == len(RETURN_HORIZONS_DAYS) else \
                     ("partial" if horizon_hits > 0 else "no_data")
    return out


def compute_random_baseline(timeline: dict) -> dict:
    """V2.20.0 (B1) — for each sector represented in watchlist, sample
    RANDOM_SECTOR_TICKERS forward returns over the same window, compute
    sector-level alpha mean / hit-rate as null-hypothesis baseline.

    Returns:
        {sector_etf: {n_tickers, mean_r_15d, hit_rate_15d, sample_tickers}}

    "Watchlist mean alpha vs SPY" looks great in absolute terms, but if random
    same-sector tickers also outperform SPY by similar margin, then watchlist
    has no edge — only sector momentum.
    """
    # Map: sector_etf → list of (sample_ticker, base_date)
    by_etf: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for tkr, slot in timeline.items():
        first = slot.get("first_seen")
        sector = slot.get("sector")
        etf = SECTOR_ETF_MAP.get(sector or "")
        if not first or not etf:
            continue
        for sample in RANDOM_SECTOR_TICKERS.get(etf, []):
            if sample == tkr:  # don't compare ticker to itself
                continue
            by_etf[etf].append((sample, first))

    out: dict[str, dict] = {}
    for etf, pairs in by_etf.items():
        if not pairs:
            continue
        r_15d_list: list[float] = []
        for sample, base_date in pairs:
            ret = fetch_forward_returns(sample, base_date, None)
            if ret.get("r_15d") is not None:
                # Subtract SPY 15d return for alpha
                a = ret.get("alpha_spy_15d")
                if a is not None:
                    r_15d_list.append(a)
        if not r_15d_list:
            continue
        out[etf] = {
            "n_samples":      len(r_15d_list),
            "mean_alpha_15d": round(sum(r_15d_list) / len(r_15d_list), 2),
            "hit_rate_15d":   round(sum(1 for a in r_15d_list if a > 0) / len(r_15d_list) * 100, 0),
            "sample_tickers": sorted(set(p[0] for p in pairs))[:5],
        }
    return out


def compute_per_keyword(timeline: dict, fwd_returns: dict) -> dict:
    """V2.20.0 (B2) — for each keyword in keyword_hits, aggregate alpha across
    tickers that hit that keyword. Identifies high-signal vs noisy keywords.

    Returns:
        {keyword: {n, mean_alpha_spy_15d, mean_alpha_sector_15d, hit_rate}}
    """
    # Reverse map: keyword → list of (ticker, fwd_data)
    kw_to_tickers: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for tkr, slot in timeline.items():
        # The keyword_hits live in the lifecycle event payload; derive from latest
        # first_seen event via slot.events list
        for ev in slot.get("events", []):
            if ev.get("event") == "first_seen":
                # No keyword_hits in lifecycle event itself — read from the
                # current watchlist.json candidates (best-effort).
                pass
        fwd = fwd_returns.get(tkr) or {}
        # Read keywords directly from current watchlist (single snapshot)
        # Fall back: skip if no fwd data
        if fwd.get("alpha_spy_15d") is None:
            continue

    # Read keywords from latest watchlist.json (authoritative, has keyword_hits)
    wl_path = ROOT / "news" / "news_logs" / "structural_watchlist.json"
    try:
        with wl_path.open("r", encoding="utf-8") as fp:
            wl = json.load(fp)
    except Exception:
        return {}

    out: dict[str, dict] = defaultdict(lambda: {"alphas_spy": [], "alphas_sec": [], "tickers": []})
    for c in (wl.get("candidates") or []):
        tkr = c.get("ticker")
        fwd = fwd_returns.get(tkr) or {}
        a_spy = fwd.get("alpha_spy_15d")
        a_sec = fwd.get("alpha_sector_15d")
        if a_spy is None and a_sec is None:
            continue
        for kw in (c.get("keyword_hits") or []):
            if a_spy is not None:
                out[kw]["alphas_spy"].append(a_spy)
            if a_sec is not None:
                out[kw]["alphas_sec"].append(a_sec)
            out[kw]["tickers"].append(tkr)

    # Aggregate
    final: dict[str, dict] = {}
    for kw, agg in out.items():
        spy = agg["alphas_spy"]
        sec = agg["alphas_sec"]
        if not spy and not sec:
            continue
        final[kw] = {
            "n":              len(agg["tickers"]),
            "tickers":        sorted(set(agg["tickers"])),
            "mean_alpha_spy": round(sum(spy) / len(spy), 2) if spy else None,
            "hit_rate_spy":   round(sum(1 for a in spy if a > 0) / len(spy) * 100, 0) if spy else None,
            "mean_alpha_sec": round(sum(sec) / len(sec), 2) if sec else None,
            "hit_rate_sec":   round(sum(1 for a in sec if a > 0) / len(sec) * 100, 0) if sec else None,
        }
    return dict(sorted(final.items(),
                       key=lambda kv: -(kv[1].get("mean_alpha_spy") or 0)))


def compute_per_credibility(fwd_returns: dict) -> dict:
    """V2.20.0 (B3) — split candidates by source_credibility_max (HIGH vs MEDIUM),
    aggregate alpha. If HIGH ≈ MEDIUM, credibility is false signal."""
    wl_path = ROOT / "news" / "news_logs" / "structural_watchlist.json"
    try:
        with wl_path.open("r", encoding="utf-8") as fp:
            wl = json.load(fp)
    except Exception:
        return {}

    buckets: dict[str, list[float]] = defaultdict(list)
    for c in (wl.get("candidates") or []):
        cred = c.get("source_credibility_max") or "UNKNOWN"
        tkr = c.get("ticker")
        fwd = fwd_returns.get(tkr) or {}
        a_spy = fwd.get("alpha_spy_15d")
        if a_spy is not None:
            buckets[cred].append(a_spy)

    out: dict[str, dict] = {}
    for cred, alphas in buckets.items():
        if not alphas:
            continue
        out[cred] = {
            "n":               len(alphas),
            "mean_alpha_spy":  round(sum(alphas) / len(alphas), 2),
            "hit_rate":        round(sum(1 for a in alphas if a > 0) / len(alphas) * 100, 0),
        }
    return out


def compute_horizon_sweep(fwd_returns: dict) -> dict:
    """V2.20.0 (B4) — aggregate alpha across all 4 horizons.

    Returns: {h: {n, mean_alpha_spy, hit_rate_spy, mean_alpha_sec, hit_rate_sec}}
    Helps decide optimal hold horizon for any future systematic strategy.
    """
    out: dict = {}
    for h in RETURN_HORIZONS_DAYS:
        spy_alphas = [f.get(f"alpha_spy_{h}d") for f in fwd_returns.values()
                      if f.get(f"alpha_spy_{h}d") is not None]
        sec_alphas = [f.get(f"alpha_sector_{h}d") for f in fwd_returns.values()
                      if f.get(f"alpha_sector_{h}d") is not None]
        if not spy_alphas and not sec_alphas:
            continue
        out[f"{h}d"] = {
            "n_spy":          len(spy_alphas),
            "mean_alpha_spy": round(sum(spy_alphas) / len(spy_alphas), 2) if spy_alphas else None,
            "hit_rate_spy":   round(sum(1 for a in spy_alphas if a > 0) / len(spy_alphas) * 100, 0) if spy_alphas else None,
            "n_sec":          len(sec_alphas),
            "mean_alpha_sec": round(sum(sec_alphas) / len(sec_alphas), 2) if sec_alphas else None,
            "hit_rate_sec":   round(sum(1 for a in sec_alphas if a > 0) / len(sec_alphas) * 100, 0) if sec_alphas else None,
        }
    return out


def render_markdown(stats: dict, timeline: dict, today_iso: str) -> str:
    n_total = len(timeline)
    n_grad_conf = len(stats["confirmed"])
    n_grad_cand = len(stats["candidate"])
    n_active = len(stats["still_active"])
    n_evict = len(stats["evicted_no_graduation"])

    def _fmt_lead(rows):
        if not rows:
            return "_(無)_"
        rows_sorted = sorted(rows, key=lambda r: (r[1] is None, r[1] or 0))
        lines = []
        for t, ld, sec in rows_sorted:
            ld_s = f"{ld}d" if ld is not None else "?"
            lines.append(f"- **{t}** (`{sec or '–'}`) — lead time {ld_s}")
        return "\n".join(lines)

    md = f"""# Structural Watchlist Backtest — {today_iso}

> V2.19.1 directional sanity check.
> Sample = {n_total} unique tickers from `watchlist_lifecycle.jsonl`.
> **n < 50 = directional only — do NOT use as production decision rule.**

## Tier graduation (Ground Truth A)

`first_seen` (watchlist enter) → `graduated_candidate / graduated_confirmed`
(earnings-analyst structural_shift tier upgrade).

| Outcome | Count | % |
|---|---|---|
| Graduated CONFIRMED | {n_grad_conf} | {(n_grad_conf / n_total * 100) if n_total else 0:.1f}% |
| Graduated CANDIDATE | {n_grad_cand} | {(n_grad_cand / n_total * 100) if n_total else 0:.1f}% |
| Still active (no graduation yet) | {n_active} | {(n_active / n_total * 100) if n_total else 0:.1f}% |
| Evicted without graduation | {n_evict} | {(n_evict / n_total * 100) if n_total else 0:.1f}% |
| **Total tickers** | **{n_total}** | 100% |

### Graduated → CONFIRMED
{_fmt_lead(stats["confirmed"])}

### Graduated → CANDIDATE
{_fmt_lead(stats["candidate"])}

### Still active
{_fmt_lead(stats["still_active"])}

### Evicted without graduation (false positive candidates)
{_fmt_lead(stats["evicted_no_graduation"])}

## Lead time stats (CONFIRMED only)
"""
    leads = [r[1] for r in stats["confirmed"] if r[1] is not None]
    if leads:
        leads_sorted = sorted(leads)
        median = leads_sorted[len(leads_sorted) // 2]
        avg = sum(leads) / len(leads)
        md += f"""
- Sample n = {len(leads)}
- Mean lead = {avg:.1f}d
- Median lead = {median}d
- Min / Max = {min(leads)}d / {max(leads)}d
"""
    else:
        md += "\n_(no CONFIRMED graduation events yet — accrual pending)_\n"

    md += "\n## Forward returns (Ground Truth B)\n"

    fwd = stats.get("forward_returns") or {}
    if fwd:
        md += "\n| Ticker | Sector ETF | Base | r_5d | r_15d | r_45d | r_90d | α_SPY_15d | α_sector_15d | Status |\n"
        md += "|---|---|---|---|---|---|---|---|---|---|\n"
        for tkr in sorted(fwd.keys()):
            f = fwd[tkr]
            def _f(k): return f"{f.get(k):+.1f}%" if f.get(k) is not None else "—"
            md += (f"| **{tkr}** | {f.get('sector_etf') or '—'} | "
                   f"{('$' + str(f.get('base_close'))) if f.get('base_close') else '—'} | "
                   f"{_f('r_5d')} | {_f('r_15d')} | {_f('r_45d')} | {_f('r_90d')} | "
                   f"{_f('alpha_spy_15d')} | {_f('alpha_sector_15d')} | "
                   f"`{f.get('_status', '?')}` |\n")

        # Aggregate alpha histogram (15d window — most common partial-data horizon)
        alphas_spy_15d = [f.get("alpha_spy_15d") for f in fwd.values()
                          if f.get("alpha_spy_15d") is not None]
        alphas_sec_15d = [f.get("alpha_sector_15d") for f in fwd.values()
                          if f.get("alpha_sector_15d") is not None]
        md += "\n### 15d alpha aggregates\n"
        if alphas_spy_15d:
            avg_spy = sum(alphas_spy_15d) / len(alphas_spy_15d)
            pos_spy = sum(1 for a in alphas_spy_15d if a > 0)
            md += (f"- SPY-relative: n={len(alphas_spy_15d)} | mean={avg_spy:+.1f}% | "
                   f"hit_rate (α>0)={pos_spy}/{len(alphas_spy_15d)} = "
                   f"{(pos_spy/len(alphas_spy_15d)*100):.0f}%\n")
        else:
            md += "- SPY-relative: _(no 15d data yet)_\n"
        if alphas_sec_15d:
            avg_sec = sum(alphas_sec_15d) / len(alphas_sec_15d)
            pos_sec = sum(1 for a in alphas_sec_15d if a > 0)
            md += (f"- Sector-relative: n={len(alphas_sec_15d)} | mean={avg_sec:+.1f}% | "
                   f"hit_rate (α>0)={pos_sec}/{len(alphas_sec_15d)} = "
                   f"{(pos_sec/len(alphas_sec_15d)*100):.0f}%\n")
        else:
            md += "- Sector-relative: _(no 15d data yet)_\n"
    else:
        md += "\n_(forward returns require `FMP_API_KEY` env var — set it and re-run)_\n"

    # V2.20.0 — B1/B2/B3/B4 deeper analysis sections
    rb = stats.get("random_baseline") or {}
    if rb:
        md += "\n## Random sector baseline (B1) — null hypothesis test\n\n"
        md += "If watchlist mean alpha ≈ random sector baseline → **no edge, only sector momentum**.\n\n"
        md += "| Sector ETF | Watchlist mean α (15d) | Random baseline mean α (15d) | n_random | Hit rate Δ |\n"
        md += "|---|---|---|---|---|\n"
        # Compute watchlist per-sector mean for direct comparison
        wl_by_etf: dict[str, list[float]] = defaultdict(list)
        for tkr, f in (stats.get("forward_returns") or {}).items():
            etf = f.get("sector_etf")
            a = f.get("alpha_spy_15d")
            if etf and a is not None:
                wl_by_etf[etf].append(a)
        for etf, base in rb.items():
            wl_alphas = wl_by_etf.get(etf, [])
            wl_mean = (sum(wl_alphas) / len(wl_alphas)) if wl_alphas else None
            wl_hit = (sum(1 for a in wl_alphas if a > 0) / len(wl_alphas) * 100) if wl_alphas else None
            edge = (wl_mean - base.get("mean_alpha_15d")) if wl_mean is not None else None
            edge_str = f"{edge:+.1f}pp" if edge is not None else "—"
            md += (f"| {etf} | {f'{wl_mean:+.1f}%' if wl_mean is not None else '—'} | "
                   f"{base.get('mean_alpha_15d'):+.1f}% | {base.get('n_samples')} | {edge_str} |\n")

    def _pct(v, fmt="+.1f"):
        if v is None:
            return "—"
        return f"{v:{fmt}}%"

    pk = stats.get("per_keyword") or {}
    if pk:
        md += "\n## Per-keyword breakdown (B2) — which keywords carry signal\n\n"
        md += "| Keyword | n | Tickers | Mean α (SPY 15d) | Hit rate | Mean α (sector 15d) |\n"
        md += "|---|---|---|---|---|---|\n"
        for kw, agg in pk.items():
            tickers_str = ", ".join(agg.get("tickers") or [])[:50]
            md += (f"| `{kw}` | {agg.get('n')} | {tickers_str} | "
                   f"{_pct(agg.get('mean_alpha_spy'))} | "
                   f"{_pct(agg.get('hit_rate_spy'), '.0f')} | "
                   f"{_pct(agg.get('mean_alpha_sec'))} |\n")

    pc = stats.get("per_credibility") or {}
    if pc:
        md += "\n## Per-credibility (B3) — HIGH vs MEDIUM source\n\n"
        md += "If HIGH ≈ MEDIUM, credibility is false signal.\n\n"
        md += "| Credibility | n | Mean α SPY 15d | Hit rate |\n"
        md += "|---|---|---|---|\n"
        for cred, agg in pc.items():
            md += (f"| {cred} | {agg.get('n')} | "
                   f"{_pct(agg.get('mean_alpha_spy'))} | "
                   f"{_pct(agg.get('hit_rate'), '.0f')} |\n")

    hs = stats.get("horizon_sweep") or {}
    if hs:
        md += "\n## Horizon sweep (B4) — optimal hold window\n\n"
        md += "| Horizon | n | Mean α SPY | Hit rate SPY | Mean α sector | Hit rate sec |\n"
        md += "|---|---|---|---|---|---|\n"
        for h_label, agg in hs.items():
            md += (f"| {h_label} | {agg.get('n_spy')} | "
                   f"{_pct(agg.get('mean_alpha_spy'))} | "
                   f"{_pct(agg.get('hit_rate_spy'), '.0f')} | "
                   f"{_pct(agg.get('mean_alpha_sec'))} | "
                   f"{_pct(agg.get('hit_rate_sec'), '.0f')} |\n")

    md += """
## Caveats

- Lifecycle log only began 2026-05-10 (V2.19.1 deploy date)
- Earnings tier graduation requires next earnings cycle (~30-90d) — small n until Q2/Q3 reports
- Watchlist eviction at 21d may flag false positives that would have graduated later
- IR boilerplate ("supply tight" / "demand strong") inflates baseline noise floor
"""
    return md


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Print summary to stdout; do NOT write reports/ files")
    args = ap.parse_args()

    events = load_lifecycle_events()
    if not events:
        print("[backtest_watchlist] no lifecycle events yet — accrual pending", file=sys.stderr)
        return 1

    timeline = collapse_by_ticker(events)
    stats = compute_tier_lead_time(timeline)

    # V2.19.2 — fetch forward returns for every ticker that has a first_seen date
    fwd_returns: dict[str, dict] = {}
    for tkr, slot in timeline.items():
        first = slot.get("first_seen")
        if not first:
            continue
        sector = slot.get("sector")
        try:
            fwd_returns[tkr] = fetch_forward_returns(tkr, first, sector)
        except Exception as e:
            print(f"[backtest_watchlist] WARN: forward returns {tkr} failed ({e})", file=sys.stderr)
    stats["forward_returns"] = fwd_returns

    # V2.20.0 — B1/B2/B3/B4 deeper analysis layers
    try:
        stats["random_baseline"]  = compute_random_baseline(timeline)
    except Exception as e:
        print(f"[backtest_watchlist] WARN: random baseline failed ({e})", file=sys.stderr)
        stats["random_baseline"] = {}
    try:
        stats["per_keyword"]      = compute_per_keyword(timeline, fwd_returns)
    except Exception as e:
        print(f"[backtest_watchlist] WARN: per-keyword failed ({e})", file=sys.stderr)
        stats["per_keyword"] = {}
    try:
        stats["per_credibility"]  = compute_per_credibility(fwd_returns)
    except Exception as e:
        print(f"[backtest_watchlist] WARN: per-credibility failed ({e})", file=sys.stderr)
        stats["per_credibility"] = {}
    try:
        stats["horizon_sweep"]    = compute_horizon_sweep(fwd_returns)
    except Exception as e:
        print(f"[backtest_watchlist] WARN: horizon sweep failed ({e})", file=sys.stderr)
        stats["horizon_sweep"] = {}

    today_iso = date.today().isoformat()
    md = render_markdown(stats, timeline, today_iso)

    if args.dry_run:
        # V2.20.0 — print summary only, skip file writes
        print(md)
        print(f"\n[backtest_watchlist] dry-run: {len(timeline)} tickers / "
              f"{len(stats['confirmed'])} CONFIRMED / {len(stats['candidate'])} CANDIDATE — no files written",
              file=sys.stderr)
        return 0

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = REPORTS_DIR / f"WATCHLIST_BACKTEST_{today_iso}.md"
    json_path = REPORTS_DIR / f"watchlist_backtest_{today_iso}.json"

    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps({
        "as_of": today_iso,
        "n_tickers": len(timeline),
        "stats": {
            "confirmed": [{"ticker": t, "lead_days": ld, "sector": s} for t, ld, s in stats["confirmed"]],
            "candidate": [{"ticker": t, "lead_days": ld, "sector": s} for t, ld, s in stats["candidate"]],
            "still_active": [{"ticker": t, "continued_count": ld, "sector": s} for t, ld, s in stats["still_active"]],
            "evicted": [{"ticker": t, "days_active": ld, "sector": s} for t, ld, s in stats["evicted_no_graduation"]],
        },
        "forward_returns": fwd_returns,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[backtest_watchlist] ✓ {len(timeline)} tickers / "
          f"{len(stats['confirmed'])} CONFIRMED / {len(stats['candidate'])} CANDIDATE → {md_path.name}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

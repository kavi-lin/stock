#!/usr/bin/env python3
"""
fred-macro — fetch structured macro snapshot from FRED (Federal Reserve Economic Data).

Outputs JSON consumed by investment_protocol Phase 0, macro-regime-detector,
and news-protocol macro context layer.

13 default series covering rates, inflation, employment, credit, stress, commodities.
Per-series derived stats: latest value, YoY / MoM change, 1y percentile rank, 30d trend.
  - RATE_SERIES: change expressed in bps (delta_bps_1m/3m/1y), with value_smooth_3d
    (3-day avg to reduce boundary noise in scoring)
Aggregate `regime_signals` synthesises the key macro state booleans.
  - real_rate_dfii10: TIPS-implied real rate (market-derived, no CPI lag)
  - real_rate_10y_estimate: legacy DGS10 - CPI YoY (backward compatible)
  - real_rate_preferred: dfii10 if available, else estimate

FRED is free (120 req/min, no daily limit) — unlike FMP there's no quota pressure.

Usage:
    python3 fetch.py                             # all defaults, 15-min cache
    python3 fetch.py --json-only
    python3 fetch.py --no-cache
    python3 fetch.py --series DGS10,T10Y2Y       # custom subset
    python3 fetch.py --asof 2024-07-01           # backtest mode
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests


FRED_BASE = "https://api.stlouisfed.org/fred"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "cache"))
CACHE_FILE = os.path.join(CACHE_DIR, "fred_latest.json")
PREV_FILE  = os.path.join(CACHE_DIR, "fred_prev.json")   # previous daily snapshot for delta reporting
DEFAULT_TTL_SEC = 3600  # 1 hour — FRED daily series update at most once/day; 15 min was wasteful
PREV_MIN_AGE_SEC = 3600 # only rotate prev → new once per hour (avoids prev = latest on rapid re-runs)


# ── Default series ──────────────────────────────────────────────────────
DEFAULT_SERIES = [
    # Rates
    "DGS10",        # 10Y Treasury yield
    "DGS2",         # 2Y Treasury yield
    "T10Y2Y",       # 10Y-2Y spread (market forward guidance / policy pivot signal)
    "T10Y3M",       # 10Y-3M spread (Fed research preferred; 3M tracks policy rate directly)
    "DFF",          # Fed Funds effective rate
    "DFII10",       # 10Y real interest rate (TIPS-implied, market-derived — no CPI lag)
    # Inflation
    "CPIAUCSL",     # CPI (headline, monthly)
    "CPILFESL",     # Core CPI
    "PCEPILFE",     # Core PCE (Fed's preferred gauge)
    # Employment
    "UNRATE",       # Unemployment rate
    "PAYEMS",       # Nonfarm payrolls
    "ICSA",         # Initial jobless claims (weekly — leading)
    # Recession indicator
    "SAHMREALTIME", # Sahm Rule real-time recession indicator (≥0.5 = triggered)
    # Consumer demand
    "RSXFS",        # Retail Sales Excl. Food Services (monthly; MoM direction used, not level)
    # Credit / stress
    "BAMLH0A0HYM2", # High-yield corp bond spread
    "NFCI",         # Chicago Fed Financial Conditions Index
    # Commodity
    "DCOILWTICO",   # WTI crude oil spot
]

# Series reported in % (interest rates, spreads) — market convention quotes
# change in basis points (bps), not percentage change.
# 1 bp = 0.01 percentage point.
# Also get value_smooth_3d (3-day avg) to reduce boundary noise in scoring.
RATE_SERIES = {"DGS10", "DGS2", "T10Y2Y", "T10Y3M", "DFF", "BAMLH0A0HYM2", "DFII10"}


# -- Fetch helpers
def _fetch_series(series_id, api_key, days=400, observation_end=None,
                  retries=3, backoff=2.0):
    """Return list of {date, value} observations (newest first, last `days` bars).
    observation_end: YYYY-MM-DD string — used by --asof backtest mode to cap data at a historical date.
    retries: number of attempts before giving up (default 3).
    backoff: initial wait seconds between retries, doubles each attempt (2s → 4s → 8s).
    """
    import time
    url = f"{FRED_BASE}/series/observations"
    params = {
        "series_id":       series_id,
        "api_key":         api_key,
        "file_type":       "json",
        "sort_order":      "desc",
        "limit":           days,
    }
    if observation_end:
        params["observation_end"] = observation_end

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 429:
                # Rate-limited — back off longer
                wait = backoff * (2 ** attempt)
                print(f"[fred-macro] {series_id} rate-limited, waiting {wait}s…", file=sys.stderr)
                time.sleep(wait)
                continue
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            obs = (r.json() or {}).get("observations") or []
            # FRED uses '.' for missing; drop them
            clean = []
            for o in obs:
                v = o.get("value")
                if v in (None, ".", ""):
                    continue
                try:
                    clean.append({"date": o.get("date"), "value": float(v)})
                except (TypeError, ValueError):
                    continue
            return clean
        except requests.exceptions.RequestException as e:
            last_err = e
            if attempt < retries:
                wait = backoff * (2 ** (attempt - 1))
                print(f"[fred-macro] {series_id} attempt {attempt}/{retries} failed ({e}), retry in {wait}s…",
                      file=sys.stderr)
                time.sleep(wait)
        except Exception as e:
            # Non-network errors (bad JSON, etc.) — no retry benefit
            raise

    raise RuntimeError(f"All {retries} attempts failed for {series_id}: {last_err}")


def _derive_stats(obs, series_id=None):
    """Compute latest / YoY / MoM / percentile_1y / trend_30d / trend_90d from obs list (newest first).

    All windows are calendar-day based, NOT observation-count based.
    This matters greatly for monthly series (UNRATE, PAYEMS, CPI):
      obs[:30] would span 2.5 years; calendar-day filter gives the correct 30-day window.

    For RATE_SERIES (interest rates / spreads): change is expressed in basis points (bps)
    instead of percentage change — delta_bps_1m / delta_bps_3m / delta_bps_1y.
    For all other series: yoy_change_pct / mom_change_pct as before.
    """
    if not obs:
        return None
    latest = obs[0]
    latest_val  = latest["value"]
    latest_date = latest["date"]

    try:
        latest_ord = datetime.fromisoformat(latest_date).date().toordinal()
    except Exception:
        latest_ord = None

    # Helper: find observation closest to N calendar days back
    def _find_ago(target_days):
        if latest_ord is None:
            return None
        target = latest_ord - target_days
        best, best_diff = None, 9999
        for o in obs:
            try:
                d = datetime.fromisoformat(o["date"]).date().toordinal()
            except Exception:
                continue
            diff = abs(d - target)
            if diff < best_diff:
                best_diff = diff
                best = o
        return best

    # Helper: observations within the last N calendar days (inclusive of today)
    def _window(days):
        if latest_ord is None:
            return []
        cutoff = latest_ord - days
        result = []
        for o in obs:
            try:
                d = datetime.fromisoformat(o["date"]).date().toordinal()
            except Exception:
                continue
            if d >= cutoff:
                result.append(o)
        return result

    yr_ago = _find_ago(365)
    mo_ago = _find_ago(30)

    def _pct_change(new, old):
        if old is None or old == 0:
            return None
        return round((new - old) / abs(old) * 100, 2)

    yoy = _pct_change(latest_val, yr_ago["value"]) if yr_ago else None
    mom = _pct_change(latest_val, mo_ago["value"]) if mo_ago else None

    # 1y percentile: where does latest sit within the past 12 calendar months?
    year_window = _window(365)
    if len(year_window) >= 2:
        year_vals = [o["value"] for o in year_window]
        below  = sum(1 for v in year_vals if v < latest_val)
        pctile = round(below / len(year_vals) * 100)
    else:
        pctile = None

    def _trend_label(window, is_rate=False):
        """Rising / falling / stable based on endpoint-to-endpoint change.
        Rate series: threshold ±10 bps (absolute).
        Other series: threshold ±2% (relative).
        """
        if len(window) < 2:
            return "stable"
        first = window[-1]["value"]   # oldest in window
        last  = window[0]["value"]    # newest (= latest)
        if is_rate:
            delta_bps = (last - first) * 100   # pct → bps
            if delta_bps > 10:    return "rising"
            if delta_bps < -10:   return "falling"
            return "stable"
        else:
            if first == 0:
                return "stable"
            pct = (last - first) / abs(first) * 100
            if pct > 2:    return "rising"
            if pct < -2:   return "falling"
            return "stable"

    is_rate = series_id in RATE_SERIES

    # trend_30d  — last 30 calendar days (short-term direction)
    # trend_90d  — last 90 calendar days (medium-term momentum, more stable for monthly series)
    trend_30d = _trend_label(_window(30), is_rate=is_rate)
    trend_90d = _trend_label(_window(90), is_rate=is_rate)

    # Data freshness: days since the most recent observation
    try:
        from datetime import date as _date
        freshness_days = (_date.today().toordinal() - latest_ord) if latest_ord else None
    except Exception:
        freshness_days = None

    if is_rate:
        # Basis-point deltas: (new - old) × 100.  e.g. 4.3% → 4.0% = -30 bps
        def _bps(ago_entry):
            if ago_entry is None:
                return None
            return round((latest_val - ago_entry["value"]) * 100, 1)

        q3_ago  = _find_ago(90)

        # 3-day smoothed value — avoids score cliff-effects when daily series
        # crosses a hard threshold by ±1 bp (e.g. T10Y2Y flipping 0.01 → -0.01)
        recent_3 = [o["value"] for o in obs[:3]]
        smooth_3d = round(sum(recent_3) / len(recent_3), 4) if recent_3 else round(latest_val, 4)

        return {
            "value":              round(latest_val, 4),
            "value_smooth_3d":    smooth_3d,
            "date":               latest_date,
            "data_freshness_days": freshness_days,
            "delta_bps_1m":       _bps(mo_ago),
            "delta_bps_3m":       _bps(q3_ago),
            "delta_bps_1y":       _bps(yr_ago),
            "percentile_1y":      pctile,
            "trend_30d":          trend_30d,
            "trend_90d":          trend_90d,
        }

    # Week-over-week change for non-rate series (most useful for weekly series like NFCI/ICSA)
    wk_ago = _find_ago(7)
    wow = round(latest_val - wk_ago["value"], 4) if wk_ago else None

    return {
        "value":               round(latest_val, 4),
        "date":                latest_date,
        "data_freshness_days": freshness_days,
        "yoy_change_pct":      yoy,
        "mom_change_pct":      mom,
        "wow_change":          wow,
        "percentile_1y":       pctile,
        "trend_30d":           trend_30d,
        "trend_90d":           trend_90d,
    }


def _regime_signals(series):
    """Synthesise key macro state booleans from raw series.

    Uses value_smooth_3d (3-day avg) for daily rate series to avoid score
    cliff-effects when a value crosses a threshold by a single basis point.
    Falls back to value if smooth field is absent (e.g. custom series subset).
    """
    def _val(sid):
        s = series.get(sid)
        return s.get("value") if s else None

    def _smooth(sid):
        """Use 3d-smoothed value for daily rate series; fallback to raw value."""
        s = series.get(sid)
        if s is None:
            return None
        return s.get("value_smooth_3d") if s.get("value_smooth_3d") is not None else s.get("value")

    t10y2y = _smooth("T10Y2Y")
    t10y3m = _smooth("T10Y3M")   # Fed research preferred curve (3M tracks policy rate)
    dff    = _smooth("DFF")
    hy     = series.get("BAMLH0A0HYM2") or {}
    nfci   = _val("NFCI")
    dgs10  = _smooth("DGS10")
    dfii10 = _smooth("DFII10")   # TIPS-implied real rate
    cpi    = series.get("CPIAUCSL") or {}

    # Fed direction: delta_bps_3m on DFF (>+25 bps = one hike, <-25 bps = one cut)
    dff_entry = series.get("DFF") or {}
    dff_bps3m = dff_entry.get("delta_bps_3m")
    if dff_bps3m is None:
        fed_dir = "unknown"
    elif dff_bps3m > 25:    fed_dir = "rising"
    elif dff_bps3m < -25:   fed_dir = "falling"
    else:                   fed_dir = "flat"

    # Real rate — two variants:
    #   dfii10 (preferred): TIPS-implied, market-priced daily, no CPI publication lag
    #   estimate (legacy):  DGS10 - CPI YoY, lags by ~4-6 weeks at turning points
    cpi_yoy = cpi.get("yoy_change_pct")
    real_rate_estimate = round(dgs10 - cpi_yoy, 2) if (dgs10 is not None and cpi_yoy is not None) else None
    real_rate_dfii10   = round(dfii10, 2)           if dfii10 is not None else None
    real_rate_preferred = real_rate_dfii10 if real_rate_dfii10 is not None else real_rate_estimate

    # NFCI WoW: absolute change in financial conditions index week-over-week.
    # NFCI is weekly — WoW is the natural velocity unit.
    # Deteriorating fast = WoW > +0.15 (conditions tightening rapidly).
    # Historical signal: before 2007/2020 crises, NFCI moved +0.2–0.5 WoW
    # while still negative (absolute level looked OK, velocity was the tell).
    nfci_entry   = series.get("NFCI") or {}
    nfci_wow     = nfci_entry.get("wow_change")
    nfci_det_fast = nfci_wow is not None and nfci_wow > 0.15

    # Sahm Rule: SAHMREALTIME ≥ 0.5 = recession triggered (historically perfect record).
    # Not a hard override — applied as -20 penalty to employment_score to preserve
    # multi-signal correction space (avoids false-positive lockout like Aug 2024).
    sahm_entry   = series.get("SAHMREALTIME") or {}
    sahm_val     = sahm_entry.get("value")
    sahm_triggered = sahm_val is not None and sahm_val >= 0.5

    # Retail Sales (RSXFS): use MoM direction only — absolute level is nominal (inflation-polluted).
    # Contracting = MoM negative AND 30d trend falling (two-condition to avoid single-month noise).
    rsxfs        = series.get("RSXFS") or {}
    rsxfs_mom    = rsxfs.get("mom_change_pct")
    rsxfs_trend  = rsxfs.get("trend_30d")
    retail_contracting = (rsxfs_mom is not None and rsxfs_mom < 0 and rsxfs_trend == "falling")

    # Yield curve: OR logic — either T10Y3M or T10Y2Y inverted triggers the signal.
    # T10Y3M: Fed research preferred (Estrella & Mishkin 1998); 3M tracks policy rate directly.
    # T10Y2Y: market convention; captures forward guidance / expected policy pivot timing.
    # Both retained: they measure different dimensions of curve shape.
    t10y3m_inverted = t10y3m is not None and t10y3m < 0
    t10y2y_inverted = t10y2y is not None and t10y2y < 0
    curve_inverted  = t10y3m_inverted or t10y2y_inverted
    curve_steep     = (t10y3m is not None and t10y3m > 1.0) or (t10y2y is not None and t10y2y > 1.0)

    return {
        "yield_curve_inverted":       curve_inverted,
        "yield_curve_steep":          curve_steep,
        "yield_curve_value":          round(t10y3m, 2) if t10y3m is not None else None,  # T10Y3M as primary
        "yield_curve_10y2y":          round(t10y2y, 2) if t10y2y is not None else None,
        "yield_curve_10y3m":          round(t10y3m, 2) if t10y3m is not None else None,
        "yield_curve_10y3m_inverted": t10y3m_inverted,
        "yield_curve_10y2y_inverted": t10y2y_inverted,
        "credit_stress_elevated":     (hy.get("percentile_1y") or 0) > 75,
        "credit_spread_pctile_1y":    hy.get("percentile_1y"),
        "financial_stress_above_avg": nfci is not None and nfci > 0,
        "nfci_wow_change":            round(nfci_wow, 3) if nfci_wow is not None else None,
        "nfci_deteriorating_fast":    nfci_det_fast,
        "sahm_value":                 round(sahm_val, 2) if sahm_val is not None else None,
        "sahm_triggered":             sahm_triggered,
        "retail_contracting":         retail_contracting,
        "retail_sales_mom_pct":       round(rsxfs_mom, 2) if rsxfs_mom is not None else None,
        "fed_rate_direction":         fed_dir,
        "fed_funds_current":          round(dff, 2) if dff is not None else None,
        "real_rate_10y_estimate":     real_rate_estimate,   # legacy (DGS10 - CPI YoY)
        "real_rate_dfii10":           real_rate_dfii10,     # TIPS-implied (preferred)
        "real_rate_preferred":        real_rate_preferred,  # use this downstream
    }


def _macro_scores(series, rs):
    """
    Per-category equity-friendliness score (0-100, higher = more bullish for stocks).
    Scores are opinionated but deterministic — no LLM needed.
    """
    def _v(sid):
        s = series.get(sid)
        return s.get("value") if s else None
    def _yoy(sid):
        s = series.get(sid)
        return s.get("yoy_change_pct") if s else None
    def _pct(sid):
        s = series.get(sid)
        return s.get("percentile_1y") if s else None

    # ── Rates (yield curve + real rate) ──────────────────────────────────
    t10y2y  = rs.get("yield_curve_value")
    # Prefer TIPS-implied real rate (no CPI lag); fallback to DGS10-CPI estimate
    real_r  = rs.get("real_rate_preferred") or rs.get("real_rate_10y_estimate")
    if t10y2y is None:
        rates_score = 50
    elif t10y2y < 0:        rates_score = 20   # inverted = recession risk
    elif t10y2y < 0.3:      rates_score = 45   # flat / barely positive
    elif t10y2y < 1.0:      rates_score = 65   # normal positive slope
    else:                   rates_score = 75   # steep = early recovery signal
    if real_r is not None:
        if real_r > 2.5:    rates_score = max(rates_score - 20, 10)  # restrictive
        elif real_r > 1.5:  rates_score = max(rates_score - 10, 20)
        elif real_r < 0:    rates_score = min(rates_score + 10, 90)  # neg real = accommodative

    # ── Inflation ─────────────────────────────────────────────────────────
    cpi_yoy  = _yoy("CPIAUCSL")
    core_cpi = _yoy("CPILFESL")
    core_pce = _yoy("PCEPILFE")
    # Use is-not-None check — avoids falsy bug when value is exactly 0.0
    inf_ref  = core_pce if core_pce is not None else (core_cpi if core_cpi is not None else cpi_yoy)
    if inf_ref is None:
        inflation_score = 50
    elif inf_ref <= 2.0:    inflation_score = 80   # at / below target
    elif inf_ref <= 2.5:    inflation_score = 68
    elif inf_ref <= 3.5:    inflation_score = 50
    elif inf_ref <= 5.0:    inflation_score = 30
    else:                   inflation_score = 15   # runaway inflation
    # Trend penalty: if CPI still rising MoM, dock points
    cpi_mom = (series.get("CPIAUCSL") or {}).get("mom_change_pct")
    if cpi_mom is not None and cpi_mom > 0.4:
        inflation_score = max(inflation_score - 10, 10)

    # ── Employment ────────────────────────────────────────────────────────
    # UNRATE: level series, meaningful as absolute value
    # PAYEMS: level series — percentile_1y always ~100 (long-term uptrend).
    #         Use YoY growth rate instead as the signal.
    unrate      = _v("UNRATE")
    icsa_trend  = (series.get("ICSA") or {}).get("trend_30d")
    payems_yoy  = _yoy("PAYEMS")   # % YoY job growth; >1% healthy, <0% contraction

    if unrate is None:
        employment_score = 50
    elif unrate < 4.0:      employment_score = 80
    elif unrate < 5.0:      employment_score = 65
    elif unrate < 6.5:      employment_score = 45
    else:                   employment_score = 25
    # PAYEMS YoY growth adjustment (±10)
    if payems_yoy is not None:
        if payems_yoy < 0:      employment_score = max(employment_score - 10, 10)
        elif payems_yoy > 1.5:  employment_score = min(employment_score + 5,  90)
    # Initial claims trend (leading signal, higher weight ±15)
    if icsa_trend == "rising":    employment_score = max(employment_score - 15, 10)
    elif icsa_trend == "falling": employment_score = min(employment_score + 10, 90)
    # Sahm Rule penalty: triggered = recession already underway; -20 regardless of UNRATE level.
    # Not a hard cap — preserves room for multi-signal correction (e.g. Aug 2024 false alarm).
    if rs.get("sahm_triggered"):
        employment_score = max(employment_score - 20, 10)
    # Retail contraction: consumer demand weakening corroborates employment stress; -10 penalty.
    # Two-condition gate (MoM < 0 AND trend falling) prevents single-month noise from triggering.
    if rs.get("retail_contracting"):
        employment_score = max(employment_score - 10, 10)

    # ── Credit ────────────────────────────────────────────────────────────
    hy_pct = _pct("BAMLH0A0HYM2")
    if hy_pct is None:
        credit_score = 50
    elif hy_pct < 25:       credit_score = 85   # spreads tight = risk-on
    elif hy_pct < 50:       credit_score = 70
    elif hy_pct < 75:       credit_score = 45
    else:                   credit_score = 20   # stress zone

    # ── Financial conditions ──────────────────────────────────────────────
    nfci = _v("NFCI")
    if nfci is None:
        fin_cond_score = 50
    elif nfci < -0.5:       fin_cond_score = 85  # very easy
    elif nfci < 0:          fin_cond_score = 70
    elif nfci < 0.5:        fin_cond_score = 45
    else:                   fin_cond_score = 25  # tight conditions
    # WoW velocity penalty: NFCI rising fast = conditions tightening rapidly.
    # Absolute level may still look OK (negative) but acceleration is the early signal.
    if rs.get("nfci_deteriorating_fast"):
        fin_cond_score = max(fin_cond_score - 15, 10)

    # ── Composite (latency-weighted) ──────────────────────────────────────
    # FRED series have very different freshness:
    #   real-time (1-7d): T10Y2Y / NFCI / HY spread / DGS10 / DFF → 1.0
    #   weekly-leading:   ICSA → folded into employment
    #   monthly lagging (~30-60d): CPI / UNRATE / PAYEMS → discount
    # Equal-weighting all 5 categories lets 2-month-stale CPI drive today's
    # regime overlay → "Lag Trap". Discount lagging tier instead.
    WEIGHTS = {
        "rates":                1.0,   # all daily series
        "credit":               1.0,   # HY spread daily
        "financial_conditions": 1.0,   # NFCI weekly
        "employment":           0.7,   # ICSA fresh, UNRATE/PAYEMS lag → blended
        "inflation":            0.5,   # CPI/PCE always 30-60d lag
    }
    weighted_sum = (
        rates_score      * WEIGHTS["rates"] +
        credit_score     * WEIGHTS["credit"] +
        fin_cond_score   * WEIGHTS["financial_conditions"] +
        employment_score * WEIGHTS["employment"] +
        inflation_score  * WEIGHTS["inflation"]
    )
    composite = round(weighted_sum / sum(WEIGHTS.values()))

    return {
        "rates":                rates_score,
        "inflation":            inflation_score,
        "employment":           employment_score,
        "credit":               credit_score,
        "financial_conditions": fin_cond_score,
        "composite":            composite,
        "_weights":             WEIGHTS,
    }


def _regime_label(series, rs, scores):
    """
    Classify current macro environment into a named regime.
    Priority: worst-case signals first (recession > stagflation > tightening > ...).
    """
    inverted      = rs.get("yield_curve_inverted", False)
    credit_stress = rs.get("credit_stress_elevated", False)
    fin_stress    = rs.get("financial_stress_above_avg", False)
    fed_dir       = rs.get("fed_rate_direction", "unknown")
    real_r        = rs.get("real_rate_preferred") or rs.get("real_rate_10y_estimate")
    t10y2y        = rs.get("yield_curve_value")
    inf_score     = scores["inflation"]
    emp_score     = scores["employment"]
    composite     = scores["composite"]

    # Recession risk: inverted + credit stress
    if inverted and credit_stress:
        return "Recession Risk"
    # Stagflation: bad inflation + deteriorating employment
    if inf_score < 35 and emp_score < 50:
        return "Stagflation"
    # Late cycle tightening: inverted or very high real rate
    if inverted or (real_r is not None and real_r > 2.5):
        return "Late Cycle Tightening"
    # Easing cycle: Fed actively cutting + curve positive slope
    # Split: Recession Easing (distress-driven) vs Benign Easing (insurance cut)
    if fed_dir == "falling" and (t10y2y is not None and t10y2y > 0.3):
        # Primary: employment already deteriorating → rescue cut
        if emp_score < 45:
            return "Recession Easing"
        # Early-warning: credit stress is leading indicator of coming job losses
        if credit_stress and emp_score < 60:
            return "Recession Easing"
        return "Benign Easing"
    # Goldilocks: inflation AT/BELOW target + strong employment + easy credit
    # Check before Soft Landing — it's the more specific (better) case
    if inf_score >= 68 and emp_score >= 65 and scores["credit"] >= 65:
        return "Goldilocks"
    # Soft landing: inflation cooling toward target, employment still solid
    if 45 <= inf_score <= 75 and emp_score >= 60:
        return "Soft Landing"
    # Overheating: inflation running hot but employment still good
    if inf_score < 45 and emp_score >= 65:
        return "Overheating"
    # Reflation: Fed not hiking + low composite (recovering from downturn).
    # Requires inflation still sub-target (not overheating) + cycle improving.
    if fed_dir in ("falling", "flat") and inf_score >= 45 and composite < 55:
        return "Reflation"
    return "Transitional"


def _market_implications(rs, scores, regime_label):
    """
    Derive 3-5 actionable market implications from macro state.
    Returns list of strings ordered by conviction.
    """
    lines = []
    real_r     = rs.get("real_rate_preferred") or rs.get("real_rate_10y_estimate")
    inv        = rs.get("yield_curve_inverted", False)
    steep      = rs.get("yield_curve_steep", False)
    hy_pct     = rs.get("credit_spread_pctile_1y")
    fed_dir    = rs.get("fed_rate_direction", "unknown")
    fin_stress = rs.get("financial_stress_above_avg", False)

    # Regime-level headline
    regime_tips = {
        "Goldilocks":            "✅ Goldilocks — 股票最佳環境：低通膨 + 就業強 + 信用寬鬆",
        "Soft Landing":          "🟢 Soft Landing — 通膨降溫中，股票偏多但需選股",
        "Reflation":             "🟡 Reflation — 週期初段，週期股 / 能源 / 原物料受惠",
        "Benign Easing":         "🟢 Benign Easing — 保險性降息，就業穩健；成長股 / 長存續期資產受惠",
        "Recession Easing":      "🔴 Recession Easing — 救火式降息，就業 / 信用已惡化；防禦為主，不宜追漲",
        "Overheating":           "🟠 Overheating — Fed 可能再升息，科技 / 成長股承壓",
        "Late Cycle Tightening": "🔴 Late Cycle — 實質利率偏高，防禦股 / 現金為王",
        "Stagflation":           "🔴 Stagflation — 股票 / 債券雙重壓力，大宗商品 / TIPS 避險",
        "Recession Risk":        "⛔ Recession Risk — 風險資產大幅減碼，信用 / 利率利差擴大",
        "Transitional":          "⚪ Transitional — 訊號混雜，維持中性，等待方向確認",
    }
    lines.append(regime_tips.get(regime_label, f"Regime: {regime_label}"))

    # Real rate impact on growth/value rotation
    if real_r is not None:
        if real_r > 2.0:
            lines.append(f"📉 實質利率 {real_r:.1f}% 偏高 → 成長股估值壓力，價值股 / 金融股相對佔優")
        elif real_r < 0:
            lines.append(f"📈 實質利率 {real_r:.1f}% 為負 → 成長股 / 黃金受惠，現金持有成本高")
        else:
            lines.append(f"➡️ 實質利率 {real_r:.1f}% 正常範圍，股票 / 債券均衡配置")

    # Yield curve shape
    if inv:
        lines.append("⚠️ 殖利率曲線倒掛 → 12-18 個月衰退前兆，縮短持倉久期")
    elif steep:
        lines.append("📈 殖利率曲線陡峭 → 早期復甦訊號，銀行 / 週期股受惠")

    # Credit conditions
    if hy_pct is not None:
        if hy_pct > 75:
            lines.append(f"🔴 高收益債利差壓力 (1y pctile {hy_pct}) → 信用市場緊張，避開高槓桿公司")
        elif hy_pct < 25:
            lines.append(f"✅ 信用市場寬鬆 (1y pctile {hy_pct}) → risk-on，高收益 / 新興市場債可參與")

    # Fed direction
    if fed_dir == "falling":
        lines.append("🟢 Fed 降息週期 → 債券多頭，成長股 / REIT 受惠")
    elif fed_dir == "rising":
        lines.append("🔴 Fed 升息週期 → 債券空頭，浮動利率貸款 / 短存續期資產佔優")

    # Financial conditions
    if fin_stress:
        lines.append("⚠️ 金融條件緊縮（NFCI > 0）→ 信貸收緊，小型股 / 高負債企業承壓")

    return lines[:5]  # cap at 5 to keep output clean


def _change_velocity(series):
    """
    Per-series velocity: is the recent pace of change faster or slower than the
    trailing annual baseline?  Compares MoM rate vs YoY/12 (monthly equivalent).
      accelerating  — recent month moving faster than annual average rate
      decelerating  — recent month moving slower / reversing
      stable        — within ±20% of annual monthly pace, or insufficient data
    """
    KEY_SERIES = ["T10Y2Y", "DGS10", "DFF", "CPIAUCSL", "CPILFESL",
                  "UNRATE", "ICSA", "BAMLH0A0HYM2", "NFCI"]
    result = {}
    for sid in KEY_SERIES:
        s = series.get(sid)
        if not s:
            continue
        trend = s.get("trend_30d", "stable")

        if sid in RATE_SERIES:
            # Rate series: use bps deltas
            bps_1m = s.get("delta_bps_1m")
            bps_1y = s.get("delta_bps_1y")
            velocity = "stable"
            if bps_1m is not None and bps_1y is not None:
                monthly_baseline_bps = bps_1y / 12.0
                if abs(monthly_baseline_bps) < 2:          # near-flat baseline
                    velocity = "accelerating" if abs(bps_1m) > 10 else "stable"
                else:
                    ratio = bps_1m / monthly_baseline_bps
                    if ratio > 1.2:    velocity = "accelerating"
                    elif ratio < 0.8:  velocity = "decelerating"
            result[sid] = {
                "trend_30d":              trend,
                "delta_bps_1m":           bps_1m,
                "monthly_baseline_bps":   round(bps_1y / 12.0, 1) if bps_1y is not None else None,
                "velocity":               velocity,
                "data_freshness_days":    s.get("data_freshness_days"),
            }
        else:
            mom = s.get("mom_change_pct")
            yoy = s.get("yoy_change_pct")
            freshness = s.get("data_freshness_days")
            velocity = "stable"
            if mom is not None and yoy is not None:
                monthly_baseline = yoy / 12.0
                if abs(monthly_baseline) < 0.05:
                    velocity = "accelerating" if abs(mom) > 0.5 else "stable"
                else:
                    ratio = mom / monthly_baseline
                    if ratio > 1.2:    velocity = "accelerating"
                    elif ratio < 0.8:  velocity = "decelerating"
            # Stale flag: monthly series not yet updated (>35 days since last obs).
            # velocity is computed from the previous release — meaningful to flag.
            stale = freshness is not None and freshness > 35
            result[sid] = {
                "trend_30d":           trend,
                "mom_change_pct":      mom,
                "monthly_baseline":    round(yoy / 12.0, 4) if yoy is not None else None,
                "velocity":            velocity,
                "data_freshness_days": freshness,
                "stale":               stale,
            }
    return result


def _regime_confidence(rs, scores, regime_label, series=None):
    """
    Confidence score (0.0–1.0) in the regime_label based on:
      1. Signal agreement  — how many independent signals align with the labelled regime
      2. Data freshness    — penalty only for series that are *overdue* vs their expected
                             update cadence (e.g. CPI monthly OK, but >45d = stale)
    """
    bullish_regimes  = {"Goldilocks", "Soft Landing", "Reflation", "Benign Easing"}
    bearish_regimes  = {"Late Cycle Tightening", "Stagflation", "Recession Risk", "Recession Easing"}
    is_bullish = regime_label in bullish_regimes
    is_bearish = regime_label in bearish_regimes

    agree, disagree, total = 0, 0, 0

    def _signal(condition_agrees, clear=True):
        nonlocal agree, disagree, total
        weight = 1.0 if clear else 0.5
        total += weight
        if condition_agrees: agree   += weight
        else:                disagree += weight

    t10y2y    = rs.get("yield_curve_value")
    real_r    = rs.get("real_rate_preferred") or rs.get("real_rate_10y_estimate")
    hy_pct    = rs.get("credit_spread_pctile_1y")
    inverted  = rs.get("yield_curve_inverted", False)
    fed_dir   = rs.get("fed_rate_direction", "unknown")
    fin_stress = rs.get("financial_stress_above_avg", False)

    # Yield curve: inverted = bearish signal
    if t10y2y is not None:
        clear = abs(t10y2y) > 0.3
        _signal(inverted == is_bearish, clear)

    # Real rate: high real rate = bearish for equities
    if real_r is not None:
        high_real = real_r > 2.0
        clear = abs(real_r) > 1.0
        _signal(high_real == is_bearish, clear)

    # Credit: stress = bearish
    if hy_pct is not None:
        stressed = hy_pct > 60
        clear = hy_pct < 30 or hy_pct > 70
        _signal(stressed == is_bearish, clear)

    # Inflation score extremes = clearer signal
    inf = scores.get("inflation", 50)
    if inf != 50:
        low_inf = inf >= 65
        clear = inf < 35 or inf > 70
        _signal(low_inf == is_bullish, clear)

    # Employment score
    emp = scores.get("employment", 50)
    if emp != 50:
        strong_emp = emp >= 60
        clear = emp < 40 or emp > 70
        _signal(strong_emp == is_bullish, clear)

    # Fed direction: falling = bullish, rising = bearish
    if fed_dir in ("rising", "falling"):
        _signal((fed_dir == "falling") == is_bullish, clear=True)
    elif fed_dir == "flat":
        _signal(is_bullish, clear=False)    # flat is slightly bullish but low conviction

    # Financial stress
    if fin_stress is not None:
        _signal(fin_stress == is_bearish, clear=True)

    if total == 0:
        return 0.50

    raw = agree / total
    # Penalty when regime is "Transitional" — inherently uncertain
    if regime_label == "Transitional":
        raw = min(raw, 0.55)

    # ── Data freshness penalty ─────────────────────────────────────────────
    # Only penalise series that are OVERDUE vs their normal cadence.
    # "Monthly" CPI at 30d age = fine.  Same CPI at 50d = stale → penalise.
    # Each overdue series applies a small multiplicative haircut (5% / 30d overdue),
    # capped so a single stale series can't crash confidence below 0.85×raw.
    if series:
        # expected_max_lag: normal max age in days before data is considered stale
        EXPECTED_LAG = {
            "DFF":          2,    # daily
            "T10Y2Y":       2,
            "DGS10":        2,
            "DGS2":         2,
            "BAMLH0A0HYM2": 2,
            "ICSA":         9,    # weekly (Friday release + weekend)
            "NFCI":         9,
            "UNRATE":       40,   # monthly (released ~4 weeks after month-end)
            "CPIAUCSL":     45,
            "CPILFESL":     45,
            "PCEPILFE":     50,   # PCE released ~5-6 weeks after month-end
            "PAYEMS":       40,
            "DCOILWTICO":   2,
        }
        today = datetime.now().date().toordinal()
        freshness_factor = 1.0
        for sid, max_lag in EXPECTED_LAG.items():
            s = series.get(sid)
            if not s or not s.get("date"):
                continue
            try:
                data_ord = datetime.fromisoformat(s["date"]).date().toordinal()
            except Exception:
                continue
            actual_lag = today - data_ord
            overdue    = max(0, actual_lag - max_lag)      # days past expected cadence
            if overdue > 0:
                # 5% penalty per 30 overdue days, floored at 0.85 per series
                haircut = min(0.15, overdue / 30 * 0.05)
                freshness_factor *= (1.0 - haircut)

        raw *= max(0.70, freshness_factor)   # global floor: freshness can't cut >30%

    return round(max(0.20, min(0.95, raw)), 2)


# Sector rotation map: which sectors benefit / suffer under each macro regime.
_SECTOR_ROTATION_MAP = {
    "Goldilocks": {
        "favor": ["Technology", "Consumer Discretionary", "Industrials", "Financials"],
        "avoid": ["Utilities", "Consumer Staples"],
        "rationale": "低通膨 + 就業強 + 信用寬鬆 → risk-on 最佳環境，成長 / 週期全面受惠",
    },
    "Soft Landing": {
        "favor": ["Technology", "Industrials", "Consumer Discretionary"],
        "avoid": ["Consumer Staples", "Utilities"],
        "rationale": "通膨降溫 + 就業穩固 → 偏多但需選股，品質成長 > 投機成長",
    },
    "Reflation": {
        "favor": ["Energy", "Materials", "Industrials", "Financials"],
        "avoid": ["Technology", "Utilities", "Real Estate"],
        "rationale": "週期初段復甦 → 實物資產 / 週期股 / 銀行受惠，高估值成長承壓",
    },
    "Benign Easing": {
        "favor": ["Technology", "Real Estate", "Consumer Discretionary", "Utilities"],
        "avoid": ["Financials"],
        "rationale": "保險性降息（就業穩）→ 長存續期資產 / REIT / 成長股反彈，銀行利差收窄",
    },
    "Recession Easing": {
        "favor": ["Consumer Staples", "Health Care", "Utilities"],
        "avoid": ["Financials", "Consumer Discretionary", "Industrials", "Technology"],
        "rationale": "救火式降息（就業 / 信用惡化）→ 降息利多被衰退利空抵消；防禦三角優先，等待就業落底再加碼成長",
    },
    "Overheating": {
        "favor": ["Energy", "Materials", "Financials"],
        "avoid": ["Technology", "Real Estate", "Consumer Discretionary"],
        "rationale": "通膨升溫 → 實物資產 / 銀行（利差擴）> 高估值成長股",
    },
    "Late Cycle Tightening": {
        "favor": ["Energy", "Consumer Staples", "Health Care", "Utilities"],
        "avoid": ["Technology", "Consumer Discretionary", "Real Estate"],
        "rationale": "實質利率高 / 曲線倒掛 → 防禦股 + 現金，避開高負債 / 高估值",
    },
    "Stagflation": {
        "favor": ["Energy", "Materials", "Consumer Staples"],
        "avoid": ["Technology", "Consumer Discretionary", "Real Estate", "Financials"],
        "rationale": "物價漲 + 成長弱 → 硬資產 / 必需消費保護購買力，成長 / 金融雙殺",
    },
    "Recession Risk": {
        "favor": ["Consumer Staples", "Health Care", "Utilities"],
        "avoid": ["Technology", "Consumer Discretionary", "Industrials", "Financials"],
        "rationale": "Risk-off → 防禦三角（必需消費 / 醫療 / 公用）+ 現金，避開週期 / 信用敏感",
    },
    "Transitional": {
        "favor": ["Consumer Staples", "Health Care"],
        "avoid": [],
        "rationale": "訊號混雜 → 輕倉防禦，等待 Regime 確認再加碼",
    },
}


def _sector_rotation(regime_label, rs=None):
    """Return sector rotation guidance for the current regime.

    Output has two layers (see skills/fred-macro/SECTOR_ROTATION_GUIDE.md):
      base   — static map derived purely from regime_label
      adjustments — dynamic overlays triggered by continuous macro variables
                    (real_rate, credit_stress, yield curve shape)
    """
    entry = _SECTOR_ROTATION_MAP.get(regime_label, _SECTOR_ROTATION_MAP["Transitional"])
    result = {
        "_guide":      "⚠️ 使用前必讀 skills/fred-macro/SECTOR_ROTATION_GUIDE.md — 說明 favor（base）vs adjustments（overlay）差異、衝突處理規則與使用時機",
        "regime":      regime_label,
        "favor":       list(entry["favor"]),
        "avoid":       list(entry["avoid"]),
        "rationale":   entry["rationale"],
        "adjustments": [],
    }

    if not rs:
        return result

    real_r    = rs.get("real_rate_preferred") or rs.get("real_rate_10y_estimate")
    inverted  = rs.get("yield_curve_inverted", False)
    steep     = rs.get("yield_curve_steep", False)
    credit_st = rs.get("credit_stress_elevated", False)

    # ── Real rate overlays ────────────────────────────────────────────────
    if real_r is not None and real_r > 2.0:
        adj = {
            "factor": "real_rate_high",
            "value":  real_r,
            "lower":  ["Technology", "Real Estate"],
            "raise":  ["Financials", "Energy"],
            "note":   (
                f"實質利率 {real_r:.1f}% > 2% — "
                "科技 / REIT 長存續期 DCF 折現率壓升；銀行 NIM 擴大、能源現金流不受影響"
            ),
        }
        if real_r > 3.0:
            adj["lower"].append("Consumer Discretionary")
            adj["note"] += "；>3% 消費信用成本同步上升，壓制選擇性消費"
        result["adjustments"].append(adj)

    # ── Credit stress overlay ─────────────────────────────────────────────
    if credit_st:
        result["adjustments"].append({
            "factor": "credit_stress_elevated",
            "value":  rs.get("credit_spread_pctile_1y"),
            "lower":  ["Financials", "Consumer Discretionary", "Industrials"],
            "raise":  ["Consumer Staples", "Health Care", "Utilities"],
            "note":   (
                "HY 利差 >75th pctile — 信用市場壓力傳導至高槓桿行業；"
                "防禦三角（必需消費 / 醫療 / 公用）抗跌"
            ),
        })

    # ── Yield curve shape overlay ─────────────────────────────────────────
    if inverted:
        result["adjustments"].append({
            "factor": "yield_curve_inverted",
            "value":  rs.get("yield_curve_value"),
            "lower":  ["Industrials", "Materials"],
            "raise":  ["Utilities", "Consumer Staples"],
            "note":   (
                "曲線倒掛 — 歷史領先衰退 6-18 個月；"
                "週期 / 工業提前減倉，公用 / 必需消費防禦"
            ),
        })
    elif steep:
        result["adjustments"].append({
            "factor": "yield_curve_steep",
            "value":  rs.get("yield_curve_value"),
            "lower":  ["Utilities"],
            "raise":  ["Financials", "Industrials"],
            "note":   (
                "曲線陡峭（>1.0%）— 銀行借短貸長利差最大化；"
                "景氣擴張預期升溫有利工業，長債利率上升壓制公用"
            ),
        })

    return result


# ── Portfolio posture + risk ───────────────────────────────────────────
# Base equity/duration/cash by regime
_POSTURE_MAP = {
    "Goldilocks":            {"equity": 0.85, "bond_dur": "medium", "cash": 0.05},
    "Soft Landing":          {"equity": 0.75, "bond_dur": "medium", "cash": 0.10},
    "Benign Easing":         {"equity": 0.80, "bond_dur": "long",   "cash": 0.05},
    "Reflation":             {"equity": 0.70, "bond_dur": "short",  "cash": 0.10},
    "Overheating":           {"equity": 0.60, "bond_dur": "short",  "cash": 0.15},
    "Late Cycle Tightening": {"equity": 0.45, "bond_dur": "short",  "cash": 0.25},
    "Stagflation":           {"equity": 0.35, "bond_dur": "short",  "cash": 0.30},
    "Recession Risk":        {"equity": 0.25, "bond_dur": "long",   "cash": 0.40},
    "Recession Easing":      {"equity": 0.35, "bond_dur": "long",   "cash": 0.30},
    "Transitional":          {"equity": 0.55, "bond_dur": "medium", "cash": 0.20},
}


def _macro_posture_guidance(regime_label, rs):
    """
    Directional posture derived purely from macro regime + real rate + credit stress.
    NOT a portfolio mandate — must be calibrated with valuation and momentum signals.
    """
    base    = _POSTURE_MAP.get(regime_label, _POSTURE_MAP["Transitional"])
    equity  = base["equity"]
    dur     = base["bond_dur"]
    cash    = base["cash"]

    real_r    = rs.get("real_rate_preferred") or rs.get("real_rate_10y_estimate")
    credit_st = rs.get("credit_stress_elevated", False)

    # High real rate: compress long-duration assets
    if real_r is not None and real_r > 2.0:
        equity = max(equity - 0.10, 0.20)
        if dur == "long":  dur = "medium"
    if real_r is not None and real_r > 3.0:
        equity = max(equity - 0.05, 0.20)
        dur = "short"

    # Credit stress: defensive shift
    if credit_st:
        equity = max(equity - 0.10, 0.20)
        cash   = min(cash   + 0.10, 0.50)

    equity = round(equity, 2)
    cash   = round(min(cash, 1.0 - equity), 2)

    return {
        "equity_exposure": equity,
        "bond_duration":   dur,
        "cash_level":      cash,
        "note": "macro-only — calibrate with valuation (Shiller PE) and momentum before execution",
    }


def _top_risks(regime_label, rs, scores, series):
    """Up to 5 most salient forward risks given current macro state."""
    risks = []
    real_r    = rs.get("real_rate_preferred") or rs.get("real_rate_10y_estimate")
    credit_st = rs.get("credit_stress_elevated", False)
    inverted  = rs.get("yield_curve_inverted", False)
    fed_dir   = rs.get("fed_rate_direction", "unknown")
    hy_pct    = rs.get("credit_spread_pctile_1y", 50)

    inf_score = scores.get("inflation", 50)
    emp_score = scores.get("employment", 50)

    cpi_trend  = (series.get("CPIAUCSL")     or {}).get("trend_30d")
    hy_trend   = (series.get("BAMLH0A0HYM2") or {}).get("trend_30d")
    icsa_trend = (series.get("ICSA")         or {}).get("trend_30d")
    ur_trend   = (series.get("UNRATE")       or {}).get("trend_30d")

    # Sahm Rule — highest priority if triggered (historically recession already underway)
    if rs.get("sahm_triggered"):
        sahm_v = rs.get("sahm_value", 0)
        risks.append(
            f"⚠️ Sahm Rule triggered ({sahm_v:.2f} ≥ 0.5) — historically signals active recession; "
            f"employment_score penalised -20"
        )

    # Inflation reacceleration
    if inf_score < 55 and cpi_trend == "rising":
        risks.append("Inflation reacceleration — CPI 30d trend rising, limits further easing room")

    # Fed policy error (easing into sticky inflation)
    if fed_dir == "falling" and inf_score < 50:
        risks.append("Fed policy error risk — easing while inflation above target may reignite price pressure")

    # Credit stress or spread widening
    if credit_st:
        risks.append(f"Credit stress elevated — HY spread at {hy_pct}th pctile; systemic contagion risk rising")
    elif hy_pct > 45 and hy_trend == "rising":
        risks.append("Credit spread reversal — HY spreads trending wider, watch for 75th pctile breach")

    # Labor weakening
    if icsa_trend == "rising" or ur_trend == "rising":
        risks.append("Labor market weakening — initial claims / unemployment trending up (leading recession signal)")

    # Retail contraction (consumer demand)
    if rs.get("retail_contracting"):
        mom = rs.get("retail_sales_mom_pct", 0)
        risks.append(f"Consumer demand contracting — retail sales MoM {mom:+.1f}% with falling trend; spending cycle turning")

    # Recession from yield curve
    if inverted:
        risks.append("Recession onset risk — yield curve inverted; historical lead time 6-18 months")

    # Growth derating from high real rates
    if real_r is not None and real_r > 2.5:
        risks.append(f"Growth derating — real rate {real_r:.1f}% compresses long-duration equity valuations")

    # Stagflation trap
    if inf_score < 45 and emp_score < 55:
        risks.append("Stagflation trap — inflation sticky while growth softens, limits policy response")

    # Regime structural risk (always fires for high-risk regimes as baseline)
    REGIME_STRUCTURAL = {
        "Overheating":           "Fed re-tightening risk — inflation above target constrains rate cuts, policy pivot delayed",
        "Late Cycle Tightening": "Recession onset risk — tightening cycle historically ends in slowdown within 12-18 months",
        "Stagflation":           "Policy trap — no good options: tightening deepens recession, easing fuels more inflation",
        "Recession Easing":      "Credit contagion risk — rescue cuts may not prevent demand destruction if job losses accelerate",
        "Transitional":          "Regime uncertainty — conflicting signals raise risk of sharp re-pricing if clarity emerges",
    }
    if regime_label in REGIME_STRUCTURAL and len(risks) < 5:
        risks.append(REGIME_STRUCTURAL[regime_label])

    return risks[:5]


# ── Backtest validation ────────────────────────────────────────────────
_SECTOR_ETFS = {
    "Technology":             "XLK",
    "Financials":             "XLF",
    "Utilities":              "XLU",
    "Energy":                 "XLE",
    "Health Care":            "XLV",
    "Industrials":            "XLI",
    "Consumer Discretionary": "XLY",
    "Consumer Staples":       "XLP",
    "Real Estate":            "XLRE",
    "Materials":              "XLB",
}


def _backtest_validate(payload, asof_date):
    """
    Fetch 3-month forward returns for SPY + sector ETFs via yfinance.
    Compares regime direction and sector map predictions vs actual outcomes.
    ⚠️ n=1 — single point has no statistical significance. Use for sanity-check only.
    """
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance not installed — pip install yfinance"}

    from datetime import date as _date, timedelta

    try:
        asof  = _date.fromisoformat(asof_date)
    except ValueError:
        return {"error": f"Invalid --asof date: {asof_date}. Use YYYY-MM-DD."}

    end_3m = asof + timedelta(days=91)
    today  = _date.today()

    if end_3m > today:
        return {
            "status": "insufficient_history",
            "note":   f"3-month window ends {end_3m} — still in the future, cannot validate yet",
        }

    def _fwd_return(ticker):
        """Closest trading day open price at asof, close price at asof+91d."""
        try:
            hist = yf.Ticker(ticker).history(
                start=asof.isoformat(),
                end=(end_3m + timedelta(days=7)).isoformat(),
                auto_adjust=True,
            )
            if hist.empty or len(hist) < 5:
                return None
            p0 = hist.iloc[0]["Close"]
            # find row closest to end_3m
            end_ord = end_3m.toordinal()
            closest = min(hist.index, key=lambda x: abs(x.date().toordinal() - end_ord))
            p1 = hist.loc[closest]["Close"]
            return round((p1 - p0) / p0 * 100, 2)
        except Exception:
            return None

    # SPY benchmark
    spy_ret = _fwd_return("SPY")

    sr       = payload.get("sector_rotation", {})
    favor    = sr.get("favor", [])
    avoid    = sr.get("avoid", [])

    # Net favor after overlay adjustments
    adj_lower, adj_raise = set(), set()
    for a in sr.get("adjustments", []):
        adj_lower.update(a.get("lower", []))
        adj_raise.update(a.get("raise",  []))
    net_favor = [s for s in favor if s not in adj_lower] + \
                [s for s in adj_raise if s not in favor]

    # Fetch all sector ETF returns
    etf_rets = {}
    for sector, etf in _SECTOR_ETFS.items():
        r = _fwd_return(etf)
        if r is not None:
            etf_rets[sector] = {"etf": etf, "return_3m_pct": r}

    def _avg(sectors):
        vals = [etf_rets[s]["return_3m_pct"] for s in sectors if s in etf_rets]
        return round(sum(vals) / len(vals), 2) if vals else None

    bullish_regimes = {"Goldilocks", "Soft Landing", "Reflation", "Benign Easing"}
    regime_label    = payload.get("regime_label", "")
    is_bullish      = regime_label in bullish_regimes

    favor_avg    = _avg(favor)
    avoid_avg    = _avg(avoid)
    net_favor_avg = _avg(net_favor)

    spread = round(favor_avg - avoid_avg, 2) \
             if favor_avg is not None and avoid_avg is not None else None

    return {
        "asof":            asof_date,
        "forward_period":  f"{asof_date} → {end_3m.isoformat()}",
        "spy_3m_pct":      spy_ret,
        "regime_direction_correct": (
            (spy_ret > 0) == is_bullish if spy_ret is not None else None
        ),
        "base_map": {
            "favor_avg_pct":  favor_avg,
            "avoid_avg_pct":  avoid_avg,
            "spread_pp":      spread,
            "map_correct":    (spread > 0) if spread is not None else None,
        },
        "net_map_after_overlay": {
            "sectors":  net_favor,
            "avg_pct":  net_favor_avg,
            "vs_base_favor": round(net_favor_avg - favor_avg, 2)
                             if net_favor_avg is not None and favor_avg is not None else None,
        },
        "etf_returns": etf_rets,
        "warning": "⚠️ n=1 single backtest point — no statistical significance. Sanity-check only.",
    }


# ── Cache ──────────────────────────────────────────────────────────────
def _load_cache(max_age_sec):
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        age = int(datetime.now().timestamp() - os.path.getmtime(CACHE_FILE))
        if age >= max_age_sec:
            return None
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)
        payload["cache_hit"] = True
        payload["cache_age_sec"] = age
        return payload
    except Exception:
        return None


def _load_prev():
    """Load previous snapshot (fred_prev.json) for delta reporting.
    Returns None if not found or unreadable.
    """
    if not os.path.exists(PREV_FILE):
        return None
    try:
        with open(PREV_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_cache(payload):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        # Rotate: if fred_latest.json is older than PREV_MIN_AGE_SEC, save it as prev
        # before overwriting. This gives a stable "previous snapshot" for delta reporting.
        if os.path.exists(CACHE_FILE):
            age = int(datetime.now().timestamp() - os.path.getmtime(CACHE_FILE))
            if age >= PREV_MIN_AGE_SEC:
                try:
                    import shutil
                    shutil.copy2(CACHE_FILE, PREV_FILE)
                except Exception:
                    pass
        tmp = CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp, CACHE_FILE)
    except Exception as e:
        print(f"[fred-macro] cache write failed: {e}", file=sys.stderr)


def _compute_delta(current, prev):
    """Compare current payload vs previous snapshot.
    Returns dict with changed fields + arrow notation strings.
    """
    if prev is None:
        return None

    delta = {}
    prev_ts  = prev.get("generated_at", "unknown")
    curr_rs  = current.get("regime_signals", {})
    prev_rs  = prev.get("regime_signals", {})

    # Regime label change
    curr_lbl = current.get("regime_label")
    prev_lbl = prev.get("regime_label")
    if curr_lbl != prev_lbl:
        delta["regime_label"] = f"{prev_lbl} → {curr_lbl} ⚠️"

    # Confidence change (>5pp = notable)
    curr_conf = current.get("regime_confidence", 0)
    prev_conf = prev.get("regime_confidence", 0)
    diff_conf = round((curr_conf - prev_conf) * 100, 1)
    if abs(diff_conf) >= 3:
        arrow = "↑" if diff_conf > 0 else "↓"
        delta["regime_confidence"] = f"{curr_conf:.0%} ({arrow}{abs(diff_conf):.1f}pp)"

    # Real rate preferred
    for field, label in [
        ("real_rate_preferred", "real_rate"),
        ("yield_curve_value",   "curve"),
        ("fed_funds_current",   "fed_funds"),
    ]:
        curr_v = curr_rs.get(field)
        prev_v = prev_rs.get(field)
        if curr_v is not None and prev_v is not None:
            d = round(curr_v - prev_v, 2)
            if abs(d) >= 0.01:
                arrow = "↑" if d > 0 else "↓"
                delta[label] = f"{curr_v} ({arrow}{abs(d)})"

    # NFCI WoW flag (new deterioration)
    curr_det = curr_rs.get("nfci_deteriorating_fast", False)
    prev_det = prev_rs.get("nfci_deteriorating_fast", False)
    if curr_det and not prev_det:
        delta["nfci_alert"] = f"⚠️ NFCI WoW {curr_rs.get('nfci_wow_change')} — NEW fast tightening"

    # Composite score
    curr_sc = (current.get("macro_scores") or {}).get("composite")
    prev_sc = (prev.get("macro_scores") or {}).get("composite")
    if curr_sc is not None and prev_sc is not None and abs(curr_sc - prev_sc) >= 3:
        arrow = "↑" if curr_sc > prev_sc else "↓"
        delta["composite_score"] = f"{curr_sc} ({arrow}{abs(curr_sc - prev_sc)})"

    delta["_prev_generated_at"] = prev_ts
    return delta if len(delta) > 1 else None  # >1 because _prev_generated_at always present


# ── Main ───────────────────────────────────────────────────────────────
def fetch(series_ids, api_key, asof_date=None):
    """Fetch + derive stats for each series. Parallel fetch (14 serial would be
    ~14s, parallel is 1-2s).
    asof_date: YYYY-MM-DD — if set, caps FRED data at that date (backtest mode).

    Retry: each series retries up to 3x with exponential backoff (2s→4s→8s).
    Fallback: if ALL series fail (network down), returns stale cache with
    `degraded_mode: true` rather than crashing downstream protocols.
    """
    result = {}
    failed = []

    def _one(sid):
        try:
            obs = _fetch_series(sid, api_key, observation_end=asof_date)
            stats = _derive_stats(obs, series_id=sid)
            return sid, stats, None
        except Exception as e:
            return sid, None, str(e)

    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_one, sid): sid for sid in series_ids}
        for fut in as_completed(futures):
            sid, stats, err = fut.result()
            if err:
                failed.append({"series": sid, "error": err})
            elif stats is not None:
                result[sid] = stats
            else:
                failed.append({"series": sid, "error": "no data returned"})

    # Stale-cache fallback: if nothing fetched successfully, degrade gracefully
    if not result and os.path.exists(CACHE_FILE):
        print("[fred-macro] ⚠️ All series failed — falling back to stale cache", file=sys.stderr)
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                stale = json.load(f)
            stale["degraded_mode"]  = True
            stale["degraded_reason"] = f"All {len(failed)} series failed; using stale cache"
            stale["cache_hit"]      = True
            stale["cache_age_sec"]  = int(datetime.now().timestamp() - os.path.getmtime(CACHE_FILE))
            return stale
        except Exception as fe:
            print(f"[fred-macro] stale cache fallback also failed: {fe}", file=sys.stderr)

    rs     = _regime_signals(result)
    scores = _macro_scores(result, rs)
    label  = _regime_label(result, rs, scores)

    payload = {
        "generated_at":   datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "asof":           asof_date,   # None = live mode
        "cache_hit":      False,
        "cache_age_sec":  0,
        "series":         result,
        "regime_signals": rs,
        "macro_scores":   scores,
        "regime_label":   label,
        "regime_confidence": _regime_confidence(rs, scores, label, series=result),
        "market_implications": _market_implications(rs, scores, label),
        "macro_posture_guidance": _macro_posture_guidance(label, rs),
        "top_risks":      _top_risks(label, rs, scores, result),
        "change_velocity": _change_velocity(result),
        "sector_rotation": _sector_rotation(label, rs=rs),
        "data_quality": {
            "series_fetched": len(result),
            "series_failed":  len(failed),
            "missing":        [f["series"] for f in failed],
            "errors":         failed if failed else [],
        },
    }
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-only", action="store_true")
    ap.add_argument("--no-cache",  action="store_true")
    ap.add_argument("--max-age",   type=int, default=DEFAULT_TTL_SEC,
                    help=f"cache TTL in seconds (default {DEFAULT_TTL_SEC})")
    ap.add_argument("--series",    default=None,
                    help="Comma-separated series IDs (default: 12 standard series)")
    ap.add_argument("--asof",      default=None, metavar="YYYY-MM-DD",
                    help="Backtest mode: fetch FRED data as-of this date, then validate vs 3m forward ETF returns")
    args = ap.parse_args()

    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        print(json.dumps({"error": "FRED_API_KEY env var not set"}), indent=2)
        sys.exit(1)

    series_ids = args.series.split(",") if args.series else DEFAULT_SERIES
    series_ids = [s.strip().upper() for s in series_ids if s.strip()]

    # ── Backtest mode ──────────────────────────────────────────────────
    if args.asof:
        print(f"[fred-macro] backtest mode: asof={args.asof}", file=sys.stderr)
        payload = fetch(series_ids, api_key, asof_date=args.asof)
        payload["backtest"] = _backtest_validate(payload, args.asof)
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        if not args.json_only:
            bt   = payload["backtest"]
            lbl  = payload.get("regime_label", "—")
            conf = payload.get("regime_confidence", 0)
            pos  = payload.get("macro_posture_guidance", {})
            risks = payload.get("top_risks", [])
            print(f"\n=== BACKTEST {args.asof} ===", file=sys.stderr)
            print(f"  Regime:  {lbl}  ({conf:.0%})", file=sys.stderr)
            print(f"  Posture: equity={pos.get('equity_exposure')}  "
                  f"dur={pos.get('bond_duration')}  cash={pos.get('cash_level')}", file=sys.stderr)
            if risks:
                print(f"  Risks:   {' | '.join(r.split(' — ')[0] for r in risks)}", file=sys.stderr)
            spy = bt.get("spy_3m_pct")
            ok  = bt.get("regime_direction_correct")
            print(f"  SPY 3m:  {spy}%  {'✅' if ok else '❌' if ok is False else '—'}",
                  file=sys.stderr)
            bm = bt.get("base_map", {})
            print(f"  Sector:  favor avg={bm.get('favor_avg_pct')}%  "
                  f"avoid avg={bm.get('avoid_avg_pct')}%  "
                  f"spread={bm.get('spread_pp')}pp  "
                  f"{'✅' if bm.get('map_correct') else '❌' if bm.get('map_correct') is False else '—'}",
                  file=sys.stderr)
            nm = bt.get("net_map_after_overlay", {})
            if nm.get("avg_pct") is not None:
                delta = nm.get("vs_base_favor")
                print(f"  Overlay: {nm['sectors']} → {nm['avg_pct']}%"
                      + (f"  (vs base {delta:+.2f}pp)" if delta is not None else ""),
                      file=sys.stderr)
            print(f"  {bt.get('warning', '')}", file=sys.stderr)
        return

    # ── Live mode ──────────────────────────────────────────────────────
    if not args.no_cache:
        cached = _load_cache(args.max_age)
        if cached is not None:
            print(json.dumps(cached, ensure_ascii=False, indent=2, default=str))
            if not args.json_only:
                rs   = cached.get("regime_signals", {})
                lbl  = cached.get("regime_label", "—")
                conf = cached.get("regime_confidence", 0)
                print(f"\n→ cache hit ({cached['cache_age_sec']}s) │ "
                      f"regime={lbl} ({conf:.0%}) │ "
                      f"curve={rs.get('yield_curve_value')} "
                      f"fed={rs.get('fed_funds_current')} ({rs.get('fed_rate_direction')}) │ "
                      f"real rate={rs.get('real_rate_preferred') or rs.get('real_rate_10y_estimate')}%", file=sys.stderr)
            return

    payload = fetch(series_ids, api_key)
    prev    = _load_prev()
    _write_cache(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

    if args.json_only:
        return

    # Summary
    rs    = payload["regime_signals"]
    dq    = payload["data_quality"]
    s     = payload["series"]
    sc    = payload.get("macro_scores", {})
    lbl   = payload.get("regime_label", "—")
    conf  = payload.get("regime_confidence", 0)
    rot   = payload.get("sector_rotation", {})
    pos   = payload.get("macro_posture_guidance", {})
    risks = payload.get("top_risks", [])
    print(f"\n=== FRED macro snapshot ===", file=sys.stderr)
    print(f"  Regime:  {lbl}  (confidence {conf:.0%})", file=sys.stderr)
    print(f"  Scores:  inflation={sc.get('inflation')}  employment={sc.get('employment')}  "
          f"credit={sc.get('credit')}  composite={sc.get('composite')}", file=sys.stderr)
    print(f"  Posture: equity={pos.get('equity_exposure')}  "
          f"duration={pos.get('bond_duration')}  cash={pos.get('cash_level')}", file=sys.stderr)
    if risks:
        print(f"  Risks:   {' | '.join(r.split(' — ')[0] for r in risks)}", file=sys.stderr)
    if rot:
        print(f"  Favor:   {', '.join(rot.get('favor', []))}", file=sys.stderr)
        if rot.get("adjustments"):
            print(f"  Overlay: {len(rot['adjustments'])} adjustment(s) active", file=sys.stderr)
    print(f"  Fetched: {dq['series_fetched']}/{dq['series_fetched']+dq['series_failed']} series" +
          (f"  (failed: {dq['missing']})" if dq['missing'] else ""), file=sys.stderr)
    print(f"  Curve:   10y3m={rs.get('yield_curve_10y3m')}  10y2y={rs.get('yield_curve_10y2y')}  " +
          ("⚠ INVERTED" if rs.get('yield_curve_inverted') else
           "⚠ STEEP"    if rs.get('yield_curve_steep') else "normal"), file=sys.stderr)
    print(f"  Fed:     {rs.get('fed_funds_current')}%  ({rs.get('fed_rate_direction')})"
          f"  real(TIPS)={rs.get('real_rate_dfii10')}%  real(est)={rs.get('real_rate_10y_estimate')}%", file=sys.stderr)
    nfci_wow = rs.get("nfci_wow_change")
    nfci_det = rs.get("nfci_deteriorating_fast", False)
    nfci_val = (s.get("NFCI") or {}).get("value")
    if nfci_val is not None:
        nfci_tag = "  ⚠ FAST TIGHTENING" if nfci_det else ""
        print(f"  NFCI:    {nfci_val}  (WoW {nfci_wow:+.3f}){nfci_tag}" if nfci_wow is not None
              else f"  NFCI:    {nfci_val}", file=sys.stderr)
    if s.get("UNRATE"):
        print(f"  UNRATE:  {s['UNRATE']['value']}%  "
              f"(YoY {s['UNRATE'].get('yoy_change_pct',0):+.2f}%)", file=sys.stderr)
    if s.get("CPIAUCSL"):
        print(f"  CPI:     {s['CPIAUCSL'].get('yoy_change_pct',0):+.2f}% YoY  "
              f"Core={s.get('CPILFESL',{}).get('yoy_change_pct')}%", file=sys.stderr)
    # Stale velocity warnings
    stale_sids = [sid for sid, v in (payload.get("change_velocity") or {}).items()
                  if v.get("stale")]
    if stale_sids:
        print(f"  Stale:   {', '.join(stale_sids)} velocity may reflect prior release", file=sys.stderr)
    # Delta report vs previous snapshot
    delta = _compute_delta(payload, prev)
    if delta:
        prev_ts = delta.pop("_prev_generated_at", "?")
        print(f"\n  ── Δ vs prev snapshot ({prev_ts[:16]}) ──", file=sys.stderr)
        for k, v in delta.items():
            print(f"    {k}: {v}", file=sys.stderr)


if __name__ == "__main__":
    main()

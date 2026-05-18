#!/usr/bin/env python3
"""
earnings-valuation-forecaster · Scenario-based 12-month target price.

Combines three forward-EPS estimates (trailing CAGR, analyst consensus, trend
regression) with the ticker's own 5-year PE percentile range (p25/p50/p75) to
produce a 3x3 sensitivity grid. Bull/base/bear scenarios are corner picks
with falsifiable trigger conditions.

Usage:
    export FMP_API_KEY=...
    python3 forecast.py MSFT
    python3 forecast.py NVDA --json-only
    python3 forecast.py AAPL --output-dir reports/ --no-cache

See ../SKILL.md for full method and output schema.

NOTE: FMP basic tier caps limit=5 and requires /stable/ endpoints with
symbol=X query param (v3 legacy endpoints return "Legacy Endpoint" errors).
EPS field is 'epsDiluted' (camelCase) in /stable/.
"""
import argparse
import datetime as dt
import json
import os
import statistics as stats
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. pip install requests", file=sys.stderr)
    sys.exit(2)

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_DIR  = SCRIPT_DIR.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
DEFAULT_TTL_SEC = 4 * 3600  # 4h

FMP_BASE = "https://financialmodelingprep.com/stable"
RATE_LIMIT = 0.25

# Static peer fallback (used when FMP /stock-peers returns nothing)
PEER_MAP = {
    "MSFT": ["AAPL", "GOOGL", "AMZN", "META"],
    "NVDA": ["AMD", "AVGO", "TSM", "MU"],
    "AAPL": ["MSFT", "GOOGL", "SONY", "DELL"],
    "GOOGL": ["META", "MSFT", "AMZN"],
    "AMZN": ["WMT", "COST", "MSFT", "GOOGL"],
    "TSLA": ["GM", "F", "RIVN", "NIO"],
    "META": ["GOOGL", "SNAP", "PINS", "TTD"],
    "JPM":  ["BAC", "GS", "MS", "WFC"],
    "XOM":  ["CVX", "COP", "SLB", "OXY"],
    "AMD":  ["NVDA", "INTC", "AVGO", "QCOM"],
}


# ── FMP client (stable endpoints) ─────────────────────────────────────────
class FMP:
    def __init__(self, api_key):
        self.api_key = api_key
        self.sess = requests.Session()
        self.last = 0.0
        self.exhausted = False   # set when 429 confirms daily quota is hit

    def get(self, path, params=None):
        # Short-circuit once quota is exhausted — daily quota doesn't reset in
        # 60s. Previous code slept + recursed on 429, which guaranteed an
        # infinite retry loop when the quota was actually hit.
        if self.exhausted:
            return None
        elapsed = time.time() - self.last
        if elapsed < RATE_LIMIT:
            time.sleep(RATE_LIMIT - elapsed)
        params = dict(params or {})
        params["apikey"] = self.api_key
        try:
            r = self.sess.get(f"{FMP_BASE}{path}", params=params, timeout=30)
            self.last = time.time()
            if r.status_code == 429:
                if not self.exhausted:
                    print(
                        "WARN: FMP returned 429 (daily quota reached); skipping all further FMP calls this run",
                        file=sys.stderr,
                    )
                self.exhausted = True
                return None
            if r.status_code != 200:
                return None
            data = r.json()
            # Some error responses come back 200 with an error-shaped dict
            if isinstance(data, dict) and ("Error Message" in data or "Premium" in str(data)[:200]):
                print(f"WARN: FMP {path} returned error: {str(data)[:150]}", file=sys.stderr)
                return None
            return data
        except (requests.RequestException, ValueError) as e:
            print(f"WARN: FMP request failed {path}: {e}", file=sys.stderr)
            return None

    def quote(self, ticker):
        data = self.get("/quote", {"symbol": ticker})
        return data[0] if isinstance(data, list) and data else None

    def income_quarter(self, ticker):
        # limit=8 so pre-earnings watch_metrics can compute YoY (Q-1 vs Q-5).
        return self.get("/income-statement", {"symbol": ticker, "period": "quarter", "limit": 8})

    def income_annual(self, ticker):
        return self.get("/income-statement", {"symbol": ticker, "period": "annual", "limit": 5})

    def ratios_annual(self, ticker):
        return self.get("/ratios", {"symbol": ticker, "limit": 5})

    def analyst_estimates(self, ticker):
        return self.get("/analyst-estimates", {"symbol": ticker, "period": "annual", "limit": 5})

    def stock_peers(self, ticker):
        return self.get("/stock-peers", {"symbol": ticker})

    def earnings_upcoming(self, ticker):
        """Fetch /stable/earnings — returns past + scheduled rows. We pick future-dated."""
        return self.get("/earnings", {"symbol": ticker, "limit": 8})


# ── Cache ─────────────────────────────────────────────────────────────────
def cache_path(ticker):
    return CACHE_DIR / f"{ticker.upper()}.json"


def load_cache(ticker, max_age):
    p = cache_path(ticker)
    if not p.exists():
        return None
    age = time.time() - p.stat().st_mtime
    if age > max_age:
        return None
    try:
        payload = json.loads(p.read_text())
        payload["cache_hit"] = True
        payload["cache_age_sec"] = int(age)
        return payload
    except Exception:
        return None


def write_cache(ticker, payload):
    try:
        cache_path(ticker).write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"WARN: cache write failed: {e}", file=sys.stderr)


# ── Forward EPS estimators ───────────────────────────────────────────────
def _ttm_eps(income_q):
    """Sum last 4 quarters of diluted EPS."""
    eps_vals = [q.get("epsDiluted") for q in (income_q or [])[:4] if q.get("epsDiluted") is not None]
    if len(eps_vals) < 4:
        return None
    return round(sum(eps_vals), 4)


def _cagr_method(income_annual):
    """Annual EPS CAGR dampened ×0.7 to avoid runaway extrapolation."""
    if not income_annual or len(income_annual) < 2:
        return None
    # income_annual is most-recent-first; each has epsDiluted for that fiscal year
    eps_series = [y.get("epsDiluted") for y in income_annual if y.get("epsDiluted") is not None]
    if len(eps_series) < 2:
        return None
    recent = eps_series[0]
    oldest = eps_series[-1]
    years = len(eps_series) - 1
    if oldest <= 0 or recent <= 0:
        return None
    cagr = (recent / oldest) ** (1 / years) - 1
    cagr_adj = max(-0.30, min(0.50, cagr * 0.7))  # dampen + cap
    return round(recent * (1 + cagr_adj), 4)


def _consensus_method(estimates):
    """FMP analyst-estimates: pick next-fiscal-year estimated EPS."""
    if not estimates:
        return None
    today = dt.date.today()
    candidates = []
    for e in estimates:
        date_str = e.get("date", "")
        try:
            d = dt.date.fromisoformat(date_str[:10])
        except Exception:
            continue
        if d < today or (d - today).days > 1100:
            continue
        # Stable endpoint may return epsAvg or estimatedEpsAvg
        eps = e.get("epsAvg") or e.get("estimatedEpsAvg")
        if eps is not None:
            candidates.append((d, eps))
    if not candidates:
        return None
    candidates.sort()
    # Prefer the closest fiscal year at least 6 months out
    forward = [e for d, e in candidates if (d - today).days >= 180]
    pick = forward[0] if forward else candidates[0][1]
    return round(pick, 4)


def _trend_method(income_annual):
    """Linear regression on annual EPS series → project one year forward."""
    if not income_annual or len(income_annual) < 3:
        return None
    # Oldest → newest
    series = [y.get("epsDiluted") for y in reversed(income_annual) if y.get("epsDiluted") is not None]
    if len(series) < 3:
        return None
    n = len(series)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(series) / n
    num = sum((xs[i] - mean_x) * (series[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if den == 0:
        return None
    slope = num / den
    intercept = mean_y - slope * mean_x
    forward = intercept + slope * n
    if forward <= 0:
        return None
    return round(forward, 4)


def forward_eps_bundle(income_annual, estimates):
    m1 = _cagr_method(income_annual)
    m2 = _consensus_method(estimates)
    m3 = _trend_method(income_annual)
    methods = {"cagr": m1, "consensus": m2, "trend": m3}
    vals = [v for v in methods.values() if v is not None and v > 0]
    if not vals:
        return None, methods, None, None
    adopted = stats.median(vals) if len(vals) >= 3 else sum(vals) / len(vals)
    spread = (max(vals) - min(vals)) / adopted if adopted > 0 else 0
    if len(vals) >= 3 and spread <= 0.10:
        confidence = "HIGH"
    elif spread <= 0.25:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    return round(adopted, 2), methods, confidence, round(spread * 100, 1)


# ── Multiple range ────────────────────────────────────────────────────────
def pe_percentiles(ratios_annual):
    """Extract PE (priceToEarningsRatio) from annual ratios; compute p25/p50/p75."""
    if not ratios_annual:
        return None
    pes = [r.get("priceToEarningsRatio") for r in ratios_annual if r.get("priceToEarningsRatio") is not None]
    pes = [p for p in pes if 0 < p < 500]
    if len(pes) < 3:
        return None
    pes_sorted = sorted(pes)
    n = len(pes_sorted)

    def pct(p):
        k = (n - 1) * p
        f = int(k)
        c = min(f + 1, n - 1)
        return pes_sorted[f] + (pes_sorted[c] - pes_sorted[f]) * (k - f)

    return {
        "pe_p25": round(pct(0.25), 2),
        "pe_p50": round(pct(0.50), 2),
        "pe_p75": round(pct(0.75), 2),
        "window_years": n,
        "source": "annual_ratios",
    }


# ── Peer PE blending (v1.1) ──────────────────────────────────────────────
def _fetch_peer_pe(client, ticker):
    """
    Fetch median PE of peer group.
    Tries FMP /stock-peers first; falls back to static PEER_MAP.
    Returns (median_pe_or_None, peers_used_list, source_str).
    """
    peer_tickers = None
    source = "none"

    data = client.stock_peers(ticker)
    if data and isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict) and "peersList" in first:
            peer_tickers = first["peersList"][:5]
            source = "fmp_stock_peers"
        elif isinstance(first, str):
            peer_tickers = data[:5]
            source = "fmp_stock_peers"

    if not peer_tickers:
        peer_tickers = PEER_MAP.get(ticker)
        if peer_tickers:
            source = "peer_map_static"

    if not peer_tickers:
        return None, [], "none"

    pes, peers_used = [], []
    for p in peer_tickers:
        q = client.quote(p)
        if q and q.get("pe"):
            pe = q["pe"]
            if 0 < pe < 200:
                pes.append(pe)
                peers_used.append(p)

    if not pes:
        return None, [], source

    return round(stats.median(pes), 2), peers_used, source


def blend_pe(own_pe, peer_median):
    """Blend own-history PE range 70% + peer median 30%. Returns new dict."""
    if peer_median is None:
        return own_pe
    result = dict(own_pe)
    result["pe_p25"] = round(own_pe["pe_p25"] * 0.7 + peer_median * 0.3, 2)
    result["pe_p50"] = round(own_pe["pe_p50"] * 0.7 + peer_median * 0.3, 2)
    result["pe_p75"] = round(own_pe["pe_p75"] * 0.7 + peer_median * 0.3, 2)
    return result


# ── Rate adjustment (v1.1) ────────────────────────────────────────────────
# Path: project_root/skills/fred-macro/cache/fred_latest.json
_FRED_MACRO_CACHE = (
    Path(__file__).resolve().parent.parent.parent / "fred-macro" / "cache" / "fred_latest.json"
)


def _load_real_rate():
    """
    Read real_rate_preferred (DFII10) from fred-macro cache.
    Returns (rate_float, source_str). Fallback: 4.5%.
    """
    try:
        if _FRED_MACRO_CACHE.exists():
            data = json.loads(_FRED_MACRO_CACHE.read_text())
            rs = data.get("regime_signals", {})
            rate = rs.get("real_rate_preferred") or rs.get("real_rate_dfii10")
            if rate is not None:
                return float(rate), "fred_macro_cache"
    except Exception:
        pass
    return 4.5, "fallback"


def rate_adjust_pe(pe_range, real_rate):
    """
    Scale PE multiples by real interest rate regime (DFII10-based).
      < 1.0%: accommodative → ×1.08
      1–2%:   neutral       → ×1.00
      2–3%:   elevated      → ×0.90
      > 3%:   restrictive   → ×0.82
    Returns (adjusted_pe_dict, multiplier, regime_label).
    """
    if real_rate < 1.0:
        mul, regime = 1.08, "accommodative"
    elif real_rate < 2.0:
        mul, regime = 1.00, "neutral"
    elif real_rate < 3.0:
        mul, regime = 0.90, "elevated"
    else:
        mul, regime = 0.82, "restrictive"

    result = dict(pe_range)
    result["pe_p25"] = round(pe_range["pe_p25"] * mul, 2)
    result["pe_p50"] = round(pe_range["pe_p50"] * mul, 2)
    result["pe_p75"] = round(pe_range["pe_p75"] * mul, 2)
    return result, mul, regime


# ── Expected value + signal (v1.1) ───────────────────────────────────────
def calc_expected_value(scenarios, confidence):
    """
    Probability-weighted target price. Probabilities reflect EPS forecast confidence:
      HIGH:   bear=0.20 / base=0.60 / bull=0.20
      MEDIUM: bear=0.25 / base=0.50 / bull=0.25
      LOW:    bear=0.30 / base=0.40 / bull=0.30
    Returns (expected_value, probability_dict).
    """
    probs_map = {
        "HIGH":   {"bear": 0.20, "base": 0.60, "bull": 0.20},
        "MEDIUM": {"bear": 0.25, "base": 0.50, "bull": 0.25},
        "LOW":    {"bear": 0.30, "base": 0.40, "bull": 0.30},
    }
    probs = probs_map.get(confidence or "MEDIUM")
    ev = (
        scenarios["bear"]["target"] * probs["bear"]
        + scenarios["base"]["target"] * probs["base"]
        + scenarios["bull"]["target"] * probs["bull"]
    )
    return round(ev, 2), probs


def valuation_signal(price, expected_value, base_target):
    """
    Advisory signal (not a trading instruction).
      STRONG BUY : price < EV × 0.90   (> 10% margin of safety vs EV)
      BUY        : price < EV
      HOLD       : price within base ± 10%
      TRIM       : price > base × 1.10 but ≤ base × 1.25
      SELL       : price > base × 1.25
    """
    if price < expected_value * 0.90:
        return "STRONG BUY"
    elif price < expected_value:
        return "BUY"
    elif price <= base_target * 1.10:
        return "HOLD"
    elif price <= base_target * 1.25:
        return "TRIM"
    return "SELL"


# ── Scenario builder ─────────────────────────────────────────────────────
def build_scenarios(forward_eps, pe_range, current_price):
    p25, p50, p75 = pe_range["pe_p25"], pe_range["pe_p50"], pe_range["pe_p75"]
    eps_bear = round(forward_eps * 0.85, 2)
    eps_base = forward_eps
    eps_bull = round(forward_eps * 1.15, 2)

    grid = [
        [round(eps_bear * p25, 2), round(eps_base * p25, 2), round(eps_bull * p25, 2)],
        [round(eps_bear * p50, 2), round(eps_base * p50, 2), round(eps_bull * p50, 2)],
        [round(eps_bear * p75, 2), round(eps_base * p75, 2), round(eps_bull * p75, 2)],
    ]

    def up(t):
        return round((t / current_price - 1) * 100, 1) if current_price > 0 else None

    bear_t, base_t, bull_t = grid[0][0], grid[1][1], grid[2][2]

    scenarios = {
        "bear": {
            "target": bear_t, "upside_pct": up(bear_t),
            "eps": eps_bear, "eps_delta_pct": -15, "pe": p25,
            "achieves_if":    "forward EPS misses by > 10% OR gross margin compression OR sector multiple de-rating",
            "invalidated_if": "company beats guidance 2 quarters in a row WITH multiple holding > p50",
        },
        "base": {
            "target": base_t, "upside_pct": up(base_t),
            "eps": eps_base, "eps_delta_pct": 0, "pe": p50,
            "achieves_if":    "earnings trajectory in-line with trend AND multiple stays in p25-p75 range",
            "invalidated_if": "material earnings surprise (> 10% either side) OR multiple breaks range",
        },
        "bull": {
            "target": bull_t, "upside_pct": up(bull_t),
            "eps": eps_bull, "eps_delta_pct": +15, "pe": p75,
            "achieves_if":    "forward EPS beats consensus by > 10% AND multiple re-rates to p75 (requires narrative catalyst)",
            "invalidated_if": "any guidance cut OR macro multiple compression (rates up / recession)",
        },
    }
    return scenarios, grid


def build_ps_scenarios(income_q, current_price, market_cap):
    """V2.16 — fallback 12M target for negative-EPS growth names. Uses P/S anchored
    on TTM revenue + recent YoY growth rate. Returns scenarios dict in same shape
    as PE scenarios (without `pe`/`eps` keys), or None when data insufficient."""
    if not income_q or len(income_q) < 4 or not current_price or not market_cap:
        return None
    ttm_rev = sum((q.get("revenue") or 0) for q in income_q[:4])
    if ttm_rev <= 0:
        return None
    shares = market_cap / current_price
    if shares <= 0:
        return None
    cur_ps = market_cap / ttm_rev

    yoy = None
    if len(income_q) >= 5 and (income_q[4].get("revenue") or 0) > 0:
        yoy = income_q[0]["revenue"] / income_q[4]["revenue"] - 1
    if yoy is None and len(income_q) >= 2 and (income_q[1].get("revenue") or 0) > 0:
        qoq = income_q[0]["revenue"] / income_q[1]["revenue"] - 1
        yoy = (1 + qoq) ** 4 - 1
    if yoy is None:
        return None
    yoy = max(min(yoy, 2.0), -0.5)

    growth = {"bull": yoy, "base": yoy * 0.7, "bear": yoy * 0.4}
    fwd_rev = {k: ttm_rev * (1 + g) for k, g in growth.items()}
    ps_mult = {"bull": cur_ps, "base": cur_ps * 0.85, "bear": cur_ps * 0.6}

    def _price(rev, p):
        return round(p * rev / shares, 2)

    out = {}
    for k in ("bull", "base", "bear"):
        t = _price(fwd_rev[k], ps_mult[k])
        out[k] = {
            "target":     t,
            "upside_pct": round((t / current_price - 1) * 100, 1),
            "ps":         round(ps_mult[k], 2),
            "fwd_rev":    round(fwd_rev[k] / 1e9, 2),
            "achieves_if": (
                f"YoY 維持 {growth[k]*100:+.0f}% 帶 fwd rev ${fwd_rev[k]/1e9:.1f}B；P/S 站 {ps_mult[k]:.1f}x"
            ),
        }
    out["method"]      = "ps"
    out["ttm_revenue_b"] = round(ttm_rev / 1e9, 2)
    out["current_ps"]    = round(cur_ps, 2)
    out["recent_yoy_pct"] = round(yoy * 100, 1)
    return out


# ── Output ───────────────────────────────────────────────────────────────
def to_json(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ── Pre-earnings extension (V2.15.0) ─────────────────────────────────────
def _next_earnings_info(client, ticker):
    """Return {date, days_until, eps_est, rev_est, source} or None.
    `source`: 'fmp_confirmed' if FMP returned a future-dated row, else None.
    """
    rows = client.earnings_upcoming(ticker) or []
    today_iso = dt.date.today().isoformat()
    # Include today: ticker reporting today still wants the consensus shown.
    # FMP marks today's row with epsActual=null until release, so it's the right pick.
    future = sorted(
        [r for r in rows if r.get("date") and r["date"] >= today_iso and r.get("epsActual") is None],
        key=lambda r: r["date"],
    )
    if not future:
        return None
    nxt = future[0]
    try:
        d = dt.date.fromisoformat(nxt["date"][:10])
        days_until = (d - dt.date.today()).days
    except Exception:
        days_until = None
    return {
        "date":          nxt.get("date"),
        "days_until":    days_until,
        "eps_estimated": nxt.get("epsEstimated"),
        "rev_estimated": nxt.get("revenueEstimated"),
        "source":        "fmp_confirmed",
    }


def _seasonality_4q(income_q):
    """Last 4 quarters: revenue / EPS diluted / GM%. Most-recent first → reverse for chronological."""
    out = []
    for q in (income_q or [])[:4]:
        rev = q.get("revenue")
        gp  = q.get("grossProfit")
        gm  = round((gp / rev) * 100, 1) if (rev and gp is not None and rev > 0) else None
        out.append({
            "period":      f"{q.get('period') or ''} {q.get('fiscalYear') or ''}".strip(),
            "date":        q.get("date"),
            "revenue":     rev,
            "eps_diluted": q.get("epsDiluted"),
            "gross_margin_pct": gm,
        })
    return list(reversed(out))  # chronological for reading L→R


def _watch_metrics_default(ticker, income_q):
    """Generic watch list — fallback when no earnings-analyst cache available.
    Returns list of (label_zh, label_en, hint) tuples for MD render."""
    items = [
        ("營收 YoY",       "Revenue YoY",       "vs 同期上年；< 0 = decel"),
        ("毛利率 (GM%)",   "Gross margin %",    "QoQ ±100bps 看 mix / pricing"),
        ("營業利益率",     "Operating margin",  "QoQ ±50bps 看 opex 紀律"),
        ("Forward guide",  "Next-Q FY guide",   "公司給的下季 / 全年 EPS / Rev range"),
        ("Segment mix",    "Segment mix",       "主力業務佔比變動 — 切換點 = 估值 re-rate"),
    ]
    return items


def _watch_metrics_computed(income_q):
    """Compute watch metrics with REAL VALUES from income_q (most-recent first, up to 8Q).
    Returns list of (label_zh, label_en, value_str). Falls back to {} when data missing."""
    items = []
    if not income_q:
        return items

    def _pct(a, b):
        if a is None or not b:
            return None
        try:
            return round((a / b - 1) * 100, 1)
        except Exception:
            return None

    def _gm(q):
        rev, gp = q.get("revenue"), q.get("grossProfit")
        return (gp / rev * 100) if (rev and gp is not None and rev > 0) else None

    def _opm(q):
        rev, oi = q.get("revenue"), q.get("operatingIncome")
        return (oi / rev * 100) if (rev and oi is not None and rev > 0) else None

    q0 = income_q[0]
    q1 = income_q[1] if len(income_q) >= 2 else None
    q4 = income_q[4] if len(income_q) >= 5 else None
    q5 = income_q[5] if len(income_q) >= 6 else None

    # Revenue YoY (preferred) or QoQ fallback
    if q4:
        yoy = _pct(q0.get("revenue"), q4.get("revenue"))
        prev_yoy = _pct(q1.get("revenue"), q5.get("revenue")) if (q1 and q5) else None
        if yoy is not None:
            tail = ""
            if prev_yoy is not None:
                d = yoy - prev_yoy
                tag = "accel" if d > 0.5 else "decel" if d < -0.5 else "flat"
                tail = f" · {tag} (prev {prev_yoy:+.1f}%)"
            items.append(("營收 YoY", "Revenue YoY", f"{yoy:+.1f}% YoY{tail}"))
    elif q1:
        qoq = _pct(q0.get("revenue"), q1.get("revenue"))
        if qoq is not None:
            items.append(("營收 QoQ", "Revenue QoQ", f"{qoq:+.1f}% QoQ (YoY 需 ≥5Q)"))

    # GM% trend (last 4Q chronological + QoQ delta in bps)
    gms = [_gm(q) for q in income_q[:4]]
    if gms[0] is not None and gms[1] is not None:
        d_bps = round((gms[0] - gms[1]) * 100)
        trend = " → ".join(f"{g:.0f}" for g in reversed([g for g in gms if g is not None]))
        items.append(("毛利率 GM%", "Gross margin %", f"{trend}% · QoQ {d_bps:+d}bps"))

    # Operating margin trend
    opms = [_opm(q) for q in income_q[:4]]
    if opms[0] is not None and opms[1] is not None:
        d_bps = round((opms[0] - opms[1]) * 100)
        trend = " → ".join(f"{o:.1f}" for o in reversed([o for o in opms if o is not None]))
        items.append(("營業利益率", "Operating margin", f"{trend}% · QoQ {d_bps:+d}bps"))

    # EPS Diluted trend (4Q)
    eps_list = [q.get("epsDiluted") for q in income_q[:4]]
    if eps_list[0] is not None and eps_list[1] is not None:
        trend = " → ".join(f"${e:.2f}" for e in reversed([e for e in eps_list if e is not None]))
        items.append(("EPS Diluted", "EPS Diluted", trend))

    items.append(("Forward guide", "Forward guide", "盤後 IR press release / call 開頭"))
    return items


def _merged_watch_metrics(ticker, income_q):
    """Compose final watch list: cache-derived (segments / quality flags) prepended,
    computed real values from income_q in middle, generic fallback only if all empty.
    Cap at 6 chips so card stays compact."""
    cached = _watch_metrics_from_cache(ticker) or []
    computed = _watch_metrics_computed(income_q) or []
    # Dedupe by zh-label; cache wins, computed fills, default fills only if both empty.
    seen, merged = set(), []
    for it in cached + computed:
        if it[0] in seen:
            continue
        seen.add(it[0])
        merged.append(it)
    if not merged:
        merged = _watch_metrics_default(ticker, income_q)
    return merged[:6]


def _watch_metrics_from_cache(ticker):
    """Try to enrich watch list from earnings-analyst cache (segments / quality flags).
    Returns enriched list or None if no cache available."""
    cache_dir = SCRIPT_DIR.parent.parent / "earnings-analyst" / "cache"
    if not cache_dir.exists():
        return None
    # Find most recent cache file matching ticker (excludes infographic.json)
    candidates = sorted(
        [p for p in cache_dir.glob(f"{ticker.upper()}_*.json")
         if not p.name.endswith(".infographic.json")],
        reverse=True,
    )
    if not candidates:
        return None
    try:
        data = json.loads(candidates[0].read_text())
    except Exception:
        return None

    items = []
    # Pull segment names if available (most-recent fiscal year). FMP wraps each
    # row as {date, fiscal_year, period, products: {Name: revenue, ...}} — drill
    # into .products before reading keys (top-level keys are just metadata).
    segs = (data.get("segments") or {}).get("product_fy") or []
    if segs and isinstance(segs[0], dict):
        seg_dict = segs[0].get("products") or {}
        seg_names = list(seg_dict.keys())[:4]
        if seg_names:
            items.append(("Segment 變動", "Segment mix", f"主力 segments: {', '.join(seg_names)}"))

    # Quality flags signal what to watch
    flags = data.get("quality_flags") or []
    if flags:
        items.append(("Quality flags",
                      "Quality flags",
                      f"上季有 {len(flags)} 個品質警訊：{'/'.join(flags[:3])} — 看本季是否惡化"))

    # Always-include generic
    items.append(("營收 YoY",      "Revenue YoY",      "consensus vs 公司 guide"))
    items.append(("毛利率 (GM%)",  "Gross margin %",   "QoQ ±100bps 看 pricing / mix"))
    items.append(("Forward guide", "Next-Q FY guide",  "下季 / 全年 EPS / Rev range（Street 對 guide reaction）"))
    return items[:6]


def _format_seasonality_table(rows):
    md = ["| Period | Date | Revenue ($B) | EPS dil. | GM% |",
          "|---|---|---|---|---|"]
    for r in rows:
        rev_b = f"{r['revenue']/1e9:.2f}" if r.get("revenue") else "—"
        eps   = f"${r['eps_diluted']:.2f}" if r.get("eps_diluted") is not None else "—"
        gm    = f"{r['gross_margin_pct']:.1f}%" if r.get("gross_margin_pct") is not None else "—"
        md.append(f"| {r.get('period') or '—'} | {r.get('date') or '—'} | {rev_b} | {eps} | {gm} |")
    return "\n".join(md)


def to_markdown_pre_earnings(p):
    """Pre-earnings cheat sheet MD layout — focuses on what to watch THIS earnings.
    The standard 12M scenarios become a supplementary section below.

    V2.15.2: handle negative-EPS partial payload (status='ok_partial') — skip
    forward EPS reconciliation + 12M scenarios, still render cheat sheet.
    """
    pe   = p.get("pre_earnings") or {}
    nxt  = pe.get("next_earnings") or {}
    seas = pe.get("seasonality_4q") or []
    watch = pe.get("watch_metrics") or []
    fe   = p.get("forward_eps") or {}
    is_negative_eps = bool(p.get("negative_eps"))

    md = []
    md.append(f"# {p['ticker']} · Pre-Earnings Cheat Sheet")
    md.append("")
    if nxt.get("date"):
        days_str = f"in {nxt['days_until']}d" if nxt.get("days_until") is not None else "?"
        md.append(f"**Next earnings**: 📅 **{nxt['date']}** ({days_str})  ·  source: {nxt.get('source','—')}")
    else:
        md.append("**Next earnings**: ❓ no FMP-confirmed date in next 90 days")
    md.append(f"**Current price**: ${p['current_price']}  ·  **TTM EPS**: ${p['ttm_eps']}"
              + ("  ·  ⚠ **Negative TTM EPS** — 12M target price section skipped" if is_negative_eps else ""))
    md.append("")

    # Consensus block
    md.append("## Street Consensus (本季)")
    md.append("")
    eps_e = nxt.get("eps_estimated")
    rev_e = nxt.get("rev_estimated")
    md.append(f"- **EPS estimate**: ${eps_e if eps_e is not None else 'n/a'}")
    if rev_e is not None:
        md.append(f"- **Revenue estimate**: ${rev_e/1e9:.2f}B")
    else:
        md.append("- **Revenue estimate**: n/a")
    if not is_negative_eps and fe.get("value") is not None:
        md.append(f"- **Forward (next-FY) EPS adopted**: ${fe['value']} ({fe.get('confidence','?')} conf)")
    md.append("")

    # Seasonality
    md.append("## 過去 4Q Seasonality（chronological）")
    md.append("")
    md.append(_format_seasonality_table(seas))
    md.append("")
    md.append("_看本季 vs 同期 1Y 前同 quarter 的趨勢；revenue YoY 加速 / 衰退 + GM% 拉伸 / 壓縮是估值 re-rate driver。_")
    md.append("")

    # Watch metrics
    md.append("## 本季 Watch List")
    md.append("")
    if watch:
        for item in watch:
            label_zh, label_en, hint = item if len(item) == 3 else (item[0], item[0], item[-1])
            md.append(f"- **{label_zh}** / _{label_en}_ — {hint}")
    else:
        md.append("- (no specific watch list — fallback to generic revenue / margin / guide)")
    md.append("")

    # Supplementary 12M scenarios — only when scenarios present (positive EPS path)
    s = p.get("scenarios")
    if s:
        md.append("## 12M Target Price (supplementary — 不直接跟本季 earnings 綁)")
        md.append("")
        md.append("| Scenario | 12M Target | Upside | Trigger |")
        md.append("|---|---|---|---|")
        for name, icon in [("bull", "🐂"), ("base", "📊"), ("bear", "🐻")]:
            sc = s[name]
            md.append(f"| {icon} {name.capitalize()} | ${sc['target']} | {sc['upside_pct']:+.1f}% | _{sc['achieves_if']}_ |")
        md.append("")
    else:
        md.append("## 12M Target Price")
        md.append("")
        md.append(f"⚠ **Skipped** — TTM EPS = {p.get('ttm_eps')} (≤ 0). PE-multiple math invalid for unprofitable names.")
        md.append("Use P/S, EV/Sales, or growth-adjusted metrics for valuation context (not in this skill's scope).")
        md.append("")

    md.append("## Caveats")
    md.append("- Consensus EPS / Rev = FMP `/earnings` 的 `epsEstimated` / `revenueEstimated`；whisper number 不在 free plan 範圍")
    md.append("- Watch list 來源：earnings-analyst cache（若存在）+ generic fallback；非 ticker-customized 深度研究")
    if s:
        md.append("- 12M target 為**長期**估值 reference，不直接預測本季 beat/miss 反應")
    else:
        md.append("- 12M target 因 negative EPS 跳過 — 本 skill 對 unprofitable 名單僅提供 cheat sheet 部分")
    md.append(f"- Forecast pulled at {p['generated_at']}")
    md.append("")
    return "\n".join(md)


def to_markdown(p):
    s = p["scenarios"]
    grid = p["sensitivity_grid"]
    axes = p["sensitivity_axes"]
    fe = p["forward_eps"]
    pm_raw = p["multiple_range"]
    pm_eff = p.get("multiple_range_effective", pm_raw)
    ev = p.get("expected_value")
    ev_up = p.get("expected_value_upside_pct")
    sig = p.get("signal", "—")
    rc = p.get("rate_context", {})
    pi = p.get("peer_pe_info", {})

    _SIGNAL_BADGE = {"STRONG BUY": "🟢", "BUY": "🟩", "HOLD": "🟡", "TRIM": "🟠", "SELL": "🔴"}
    badge = _SIGNAL_BADGE.get(sig, "⬜")

    ev_str = f"  ·  **EV**: ${ev} ({ev_up:+.1f}%)" if ev is not None and ev_up is not None else ""

    md = []
    md.append(f"# {p['ticker']} · 12-Month Valuation Scenarios")
    md.append("")
    md.append(
        f"**Current**: ${p['current_price']}"
        f"  ·  **Signal**: {badge} {sig}"
        f"  ·  **TTM EPS**: ${p['ttm_eps']}"
        f"  ·  **Forward EPS**: ${fe['value']} ({fe['confidence']} conf)"
        f"{ev_str}"
    )
    md.append("")
    md.append(f"_Generated {p['generated_at']}_")
    md.append("")
    md.append("## Scenarios")
    md.append("")
    md.append("| Scenario | Target | Upside | PE  | EPS Δ | Forward EPS |")
    md.append("|---|---|---|---|---|---|")
    md.append(f"| 🐂 Bull | ${s['bull']['target']} | {s['bull']['upside_pct']:+.1f}% | {s['bull']['pe']}× | +15% | ${s['bull']['eps']} |")
    md.append(f"| 📊 Base | ${s['base']['target']} | {s['base']['upside_pct']:+.1f}% | {s['base']['pe']}× |   0% | ${s['base']['eps']} |")
    md.append(f"| 🐻 Bear | ${s['bear']['target']} | {s['bear']['upside_pct']:+.1f}% | {s['bear']['pe']}× | −15% | ${s['bear']['eps']} |")
    if ev is not None:
        md.append(f"| ⚖️ EV   | ${ev} | {ev_up:+.1f}% | — | — | — |")
    md.append("")
    md.append("### Trigger Conditions")
    for name, icon in [("bull", "🐂"), ("base", "📊"), ("bear", "🐻")]:
        sc = s[name]
        md.append(f"- {icon} **{name.capitalize()}** — achieves if: _{sc['achieves_if']}_")
        md.append(f"  - invalidated if: _{sc['invalidated_if']}_")
    md.append("")
    md.append("## Sensitivity Matrix (target price)")
    md.append("")
    md.append(f"| | {axes['cols'][0]} | {axes['cols'][1]} | {axes['cols'][2]} |")
    md.append("|---|---|---|---|")
    for i, row in enumerate(grid):
        md.append(f"| **{axes['rows'][i]}** | ${row[0]} | ${row[1]} | ${row[2]} |")
    md.append("")
    md.append("## Forward EPS Reconciliation")
    md.append("")
    for k, v in fe["methods"].items():
        md.append(f"- **{k}**: {'$' + str(v) if v is not None else 'n/a'}")
    md.append(f"- **Adopted**: ${fe['value']} ({fe['confidence']} conf, ±{fe['spread_pct']}% spread)")
    md.append("")
    md.append(f"## PE Multiple")
    md.append("")
    md.append(f"_Raw (own 5Y history):_ p25={pm_raw['pe_p25']}× · p50={pm_raw['pe_p50']}× · p75={pm_raw['pe_p75']}×")
    if pi.get("median_pe") is not None:
        peers_str = ", ".join(pi.get("peers_used", [])) or "—"
        md.append(f"_Peer median PE_: {pi['median_pe']}× (from {peers_str}, source: {pi.get('source','—')})")
    rate_note = ""
    if rc:
        rate_note = f"Real rate: {rc.get('real_rate','?')}% ({rc.get('rate_regime','?')}) → ×{rc.get('rate_multiplier','?')}"
        md.append(f"_Rate adjustment_: {rate_note}")
    md.append(f"_Effective (used for scenarios):_ p25={pm_eff['pe_p25']}× · p50={pm_eff['pe_p50']}× · p75={pm_eff['pe_p75']}×")
    md.append("")
    md.append("## Caveats")
    for c in p.get("caveats", []):
        md.append(f"- {c}")
    md.append("")
    return "\n".join(md)


# ── Main ─────────────────────────────────────────────────────────────────
def run(ticker, no_cache=False, max_age=DEFAULT_TTL_SEC, pre_earnings=False):
    ticker = ticker.upper().strip()
    # Cache distinguishes pre_earnings extension via separate cache key suffix
    # (mixing them would cause the plain-mode cache to be picked up by --pre-earnings
    # and skip the new fields). Only check cache when pre_earnings flag matches.
    if not no_cache:
        cached = load_cache(ticker, max_age)
        if cached:
            cache_has_pre = bool(cached.get("pre_earnings"))
            if pre_earnings == cache_has_pre:
                return cached

    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return {"status": "error", "reason": "FMP_API_KEY env var not set"}

    client = FMP(api_key)
    quote = client.quote(ticker)
    if not quote:
        return {"status": "error", "reason": f"no quote for {ticker}"}
    current_price = quote.get("price") or 0
    if current_price <= 0:
        return {"status": "error", "reason": f"invalid price for {ticker}"}

    income_q = client.income_quarter(ticker) or []
    if len(income_q) < 4:
        return {"status": "error", "reason": f"insufficient quarterly income ({len(income_q)} quarters)"}

    ttm = _ttm_eps(income_q)
    if ttm is None or ttm <= 0:
        # V2.15.2 — pre-earnings cheat sheet does NOT need positive EPS.
        # Consensus + seasonality + watch list still produce useful output for
        # unprofitable growth names (CRWV / RIVN / SOFI / RDDT). Only the 12M
        # target price section requires PE math; skip it gracefully.
        if pre_earnings:
            seas = _seasonality_4q(income_q)
            next_info = _next_earnings_info(client, ticker)
            watch = _merged_watch_metrics(ticker, income_q)
            ps_scen = build_ps_scenarios(income_q, current_price, quote.get("marketCap"))
            partial = {
                "status":        "ok_partial",
                "ticker":        ticker,
                "generated_at":  dt.datetime.now().isoformat(timespec="seconds"),
                "current_price": round(current_price, 2),
                "ttm_eps":       ttm,
                "negative_eps":  True,
                "pre_earnings": {
                    "next_earnings":  next_info,
                    "seasonality_4q": seas,
                    "watch_metrics":  watch,
                    "mode_version":   "V2.16",
                },
                "scenarios":          ps_scen,  # P/S-based fallback when EPS ≤ 0
                "cache_hit":          False,
                "cache_age_sec":      0,
            }
            write_cache(ticker, partial)
            return partial
        return {"status":  "unsupported",
                "reason":  "negative_or_missing_ttm_eps",
                "ticker":  ticker,
                "ttm_eps": ttm,
                "note":    "Skill supports positive-EPS companies only. For unprofitable names use P/S or EV/EBITDA."}

    income_a = client.income_annual(ticker) or []
    estimates = client.analyst_estimates(ticker) or []
    ratios_a  = client.ratios_annual(ticker) or []

    pe_range = pe_percentiles(ratios_a)
    if pe_range is None:
        return {"status": "error", "reason": "insufficient PE history from ratios endpoint"}

    fwd_eps, methods, confidence, spread = forward_eps_bundle(income_a, estimates)
    if fwd_eps is None:
        return {"status": "error", "reason": "could not compute forward EPS from any method"}

    # v1.1: peer blending + rate adjustment on PE range
    peer_median, peers_used, peer_source = _fetch_peer_pe(client, ticker)
    blended = blend_pe(pe_range, peer_median)
    real_rate, rate_source = _load_real_rate()
    effective_pe, rate_mul, rate_regime = rate_adjust_pe(blended, real_rate)

    scenarios, grid = build_scenarios(fwd_eps, effective_pe, current_price)

    # v1.1: expected value + advisory signal
    ev, ev_probs = calc_expected_value(scenarios, confidence)
    sig = valuation_signal(current_price, ev, scenarios["base"]["target"])
    ev_upside = round((ev / current_price - 1) * 100, 1) if current_price > 0 else None

    payload = {
        "status":        "ok",
        "ticker":        ticker,
        "generated_at":  dt.datetime.now().isoformat(timespec="seconds"),
        "current_price": round(current_price, 2),
        "ttm_eps":       ttm,
        "forward_eps": {
            "value":       fwd_eps,
            "methods":     methods,
            "confidence":  confidence,
            "spread_pct":  spread,
        },
        "multiple_range":           pe_range,      # raw own-history (reference)
        "multiple_range_effective": effective_pe,  # after peer blend + rate adjust (used for scenarios)
        "peer_pe_info": {
            "median_pe":  peer_median,
            "peers_used": peers_used,
            "source":     peer_source,
        },
        "rate_context": {
            "real_rate":       real_rate,
            "rate_multiplier": rate_mul,
            "rate_regime":     rate_regime,
            "source":          rate_source,
        },
        "scenarios":          scenarios,
        "sensitivity_grid":   grid,
        "sensitivity_axes": {
            "rows": [f"PE p25 ({effective_pe['pe_p25']})",
                     f"PE p50 ({effective_pe['pe_p50']})",
                     f"PE p75 ({effective_pe['pe_p75']})"],
            "cols": ["EPS −15%", "EPS base", "EPS +15%"],
        },
        "expected_value":               ev,
        "expected_value_upside_pct":    ev_upside,
        "expected_value_probabilities": ev_probs,
        "signal":                       sig,
        "caveats": [
            "Multiple range uses company's own 5-year annual history — blind to sector regime shifts",
            "Forward EPS assumes business model continuity (secular disruption breaks all 3 methods)",
            "Earnings quality not adjusted (SBC, one-offs, GAAP vs non-GAAP ignored)",
            "Peer PE blend uses median of up to 5 peers — thin or mismatched peer groups reduce accuracy",
            "Rate adjustment uses DFII10 real rate from fred-macro cache (stale if cache not refreshed)",
            "Signal is advisory only — not a trading instruction",
            f"Multiple window: {pe_range['window_years']} years of annual PE history",
        ],
        "cache_hit":     False,
        "cache_age_sec": 0,
    }

    # V2.15.0 — pre-earnings extension: appended only when --pre-earnings mode requested
    if pre_earnings:
        seas = _seasonality_4q(income_q)
        next_info = _next_earnings_info(client, ticker)
        watch = _watch_metrics_from_cache(ticker) or _watch_metrics_default(ticker, income_q)
        payload["pre_earnings"] = {
            "next_earnings":  next_info,
            "seasonality_4q": seas,
            "watch_metrics":  watch,
            "mode_version":   "V2.15.0",
        }

    write_cache(ticker, payload)
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--json-only", action="store_true")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--max-age", type=int, default=DEFAULT_TTL_SEC)
    ap.add_argument("--output-dir", type=str, default=None)
    ap.add_argument("--pre-earnings", action="store_true",
                    help="V2.15.0 pre-earnings cheat sheet mode: next earnings date "
                         "+ consensus EPS/Rev + 4Q seasonality + watch list. Output "
                         "filename suffix changes to _pre_earnings.md.")
    args = ap.parse_args()

    out = run(args.ticker, no_cache=args.no_cache, max_age=args.max_age,
              pre_earnings=args.pre_earnings)
    # V2.15.2 — accept "ok_partial" (negative-EPS pre-earnings) as success.
    # Plain mode still requires "ok" (12M scenarios are mandatory there).
    ok_statuses = ("ok",) if not args.pre_earnings else ("ok", "ok_partial")
    if args.json_only or out.get("status") not in ok_statuses:
        print(to_json(out))
        sys.exit(0 if out.get("status") in ok_statuses else 1)

    md = to_markdown_pre_earnings(out) if args.pre_earnings else to_markdown(out)
    print(md)
    if args.output_dir:
        d = Path(args.output_dir)
        d.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d")
        suffix = "pre_earnings" if args.pre_earnings else "valuation"
        outpath = d / f"{stamp}_{out['ticker']}_{suffix}.md"
        outpath.write_text(md)
        print(f"\n[wrote] {outpath}", file=sys.stderr)


if __name__ == "__main__":
    main()

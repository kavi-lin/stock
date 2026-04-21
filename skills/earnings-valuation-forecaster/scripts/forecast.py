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


# ── FMP client (stable endpoints) ─────────────────────────────────────────
class FMP:
    def __init__(self, api_key):
        self.api_key = api_key
        self.sess = requests.Session()
        self.last = 0.0

    def get(self, path, params=None):
        elapsed = time.time() - self.last
        if elapsed < RATE_LIMIT:
            time.sleep(RATE_LIMIT - elapsed)
        params = dict(params or {})
        params["apikey"] = self.api_key
        try:
            r = self.sess.get(f"{FMP_BASE}{path}", params=params, timeout=30)
            self.last = time.time()
            if r.status_code == 429:
                print("WARN: FMP rate-limited, sleeping 60s", file=sys.stderr)
                time.sleep(60)
                return self.get(path, params)
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
        return self.get("/income-statement", {"symbol": ticker, "period": "quarter", "limit": 5})

    def income_annual(self, ticker):
        return self.get("/income-statement", {"symbol": ticker, "period": "annual", "limit": 5})

    def ratios_annual(self, ticker):
        return self.get("/ratios", {"symbol": ticker, "limit": 5})

    def analyst_estimates(self, ticker):
        return self.get("/analyst-estimates", {"symbol": ticker, "period": "annual", "limit": 5})


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


# ── Output ───────────────────────────────────────────────────────────────
def to_json(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2)


def to_markdown(p):
    s = p["scenarios"]
    grid = p["sensitivity_grid"]
    axes = p["sensitivity_axes"]
    fe = p["forward_eps"]
    pm = p["multiple_range"]
    md = []
    md.append(f"# {p['ticker']} · 12-Month Valuation Scenarios")
    md.append("")
    md.append(f"**Current**: ${p['current_price']}  ·  **TTM EPS**: ${p['ttm_eps']}  ·  **Forward EPS**: ${fe['value']} ({fe['confidence']} conf)")
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
    md.append(f"## Multiple Range ({pm['window_years']}-year annual window, {pm['source']})")
    md.append("")
    md.append(f"- PE p25 (bear multiple): **{pm['pe_p25']}×**")
    md.append(f"- PE p50 (base multiple): **{pm['pe_p50']}×**")
    md.append(f"- PE p75 (bull multiple): **{pm['pe_p75']}×**")
    md.append("")
    md.append("## Caveats")
    for c in p.get("caveats", []):
        md.append(f"- {c}")
    md.append("")
    return "\n".join(md)


# ── Main ─────────────────────────────────────────────────────────────────
def run(ticker, no_cache=False, max_age=DEFAULT_TTL_SEC):
    ticker = ticker.upper().strip()
    if not no_cache:
        cached = load_cache(ticker, max_age)
        if cached:
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

    scenarios, grid = build_scenarios(fwd_eps, pe_range, current_price)

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
        "multiple_range":     pe_range,
        "scenarios":          scenarios,
        "sensitivity_grid":   grid,
        "sensitivity_axes": {
            "rows": [f"PE p25 ({pe_range['pe_p25']})",
                     f"PE p50 ({pe_range['pe_p50']})",
                     f"PE p75 ({pe_range['pe_p75']})"],
            "cols": ["EPS −15%", "EPS base", "EPS +15%"],
        },
        "caveats": [
            "Multiple range uses company's own 5-year annual history — blind to sector regime shifts",
            "Forward EPS assumes business model continuity (secular disruption breaks all 3 methods)",
            "Earnings quality not adjusted (SBC, one-offs, GAAP vs non-GAAP ignored)",
            "Not a replacement for DCF / intrinsic value analysis",
            f"Multiple window: {pe_range['window_years']} years of annual PE history",
        ],
        "cache_hit":     False,
        "cache_age_sec": 0,
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
    args = ap.parse_args()

    out = run(args.ticker, no_cache=args.no_cache, max_age=args.max_age)
    if args.json_only or out.get("status") != "ok":
        print(to_json(out))
        sys.exit(0 if out.get("status") == "ok" else 1)

    md = to_markdown(out)
    print(md)
    if args.output_dir:
        d = Path(args.output_dir)
        d.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d")
        outpath = d / f"{stamp}_{out['ticker']}_valuation.md"
        outpath.write_text(md)
        print(f"\n[wrote] {outpath}", file=sys.stderr)


if __name__ == "__main__":
    main()

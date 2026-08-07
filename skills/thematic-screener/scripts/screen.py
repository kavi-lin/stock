#!/usr/bin/env python3
"""
thematic-screener v0.2 — All themes × per-theme short-term breadth + conviction.

Per plan_short.md design discussion (2026-04-25):
- Show ALL detected themes (not Top N)
- Per-theme metrics:
    - mid_heat (from theme-detector)
    - short_term.bullish_breadth_pct = % of movers with positive 5d target
    - short_term.avg_conviction = mean of 5d confidence
    - short_term.components (reserved for v0.2 multi-factor synthesis)
- Top-5 movers per theme (ranked by 5d target_pct × confidence)
- Regime layer: 2 independent badges (RSI + VIX) + factor for # adjustment
  (per §extreme thresholds 85/25 for RSI; 25/35/40 for VIX)
- Concentration WARNING (theme membership proxy, per §11.B)
- Per-ticker predict cache (4h TTL) → screener wall time stays manageable

Output: data/recommendations/<DATE>.json (consumed by Dashboard radar.html)
"""
import os
import sys
import json
import glob
import socket
import time
import argparse
import datetime
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# v0.3.1 — global socket timeout. Without this yfinance / FMP requests can
# hang indefinitely when a route black-holes the SYN (observed: 65min stuck
# in SYN_SENT state). 15s per network op is plenty for this script's needs.
socket.setdefaulttimeout(15)

ROOT = Path(__file__).resolve().parent.parent.parent.parent
SKILL_DIR = Path(__file__).resolve().parent.parent
RECS_DIR = SKILL_DIR / "data" / "recommendations"
THEME_CACHE = ROOT / "skills" / "theme-detector" / "cache"
FRED_CACHE = ROOT / "skills" / "fred-macro" / "cache"
PREDICT_SCRIPT = ROOT / "skills" / "short-term-target" / "scripts" / "predict.py"

def _log(msg):
    """Stderr line-buffered log so the daily_update.sh tail sees progress live."""
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}",
          file=sys.stderr, flush=True)

# v0.3 — per-mover enrichment (market_cap_tier + earnings/quality/smart-money/analyst)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from enrich import enrich_movers
    HAS_ENRICH = True
except ImportError:
    HAS_ENRICH = False

# v0.4 — in-process predict (saves ~1-2s interpreter+import per ticker vs subprocess).
# Falls back to subprocess if the module can't be imported.
sys.path.insert(0, str(PREDICT_SCRIPT.parent))
try:
    from predict import predict_ticker as _predict_inproc
except Exception:
    _predict_inproc = None

sys.path.insert(0, str(ROOT))
from skills._shared.technical_core import rsi_14 as _shared_rsi_14  # noqa: E402


# ---------- data loaders (unchanged from v0.1) ----------

def load_latest_themes():
    if not THEME_CACHE.exists():
        return None, {"error": "theme_detector cache directory missing"}
    files = sorted(glob.glob(str(THEME_CACHE / "theme_detector_*.json")), reverse=True)
    if not files:
        return None, {"error": "no theme_detector cache files"}
    p = files[0]
    age_hr = (datetime.datetime.now().timestamp() - os.path.getmtime(p)) / 3600
    try:
        return json.load(open(p)), {"age_hr": round(age_hr, 1), "file": Path(p).name}
    except Exception as e:
        return None, {"error": f"parse failed: {e}"}


def load_fred_snapshot():
    if not FRED_CACHE.exists():
        return None
    files = sorted(glob.glob(str(FRED_CACHE / "*.json")), reverse=True)
    if not files:
        return None
    try:
        d = json.load(open(files[0]))
        sig = d.get("regime_signals", {})
        snap = {
            "yield_curve_t10y2y": sig.get("yield_curve_value"),
            "yield_curve_inverted": sig.get("yield_curve_inverted"),
            "fed_funds_current": sig.get("fed_funds_current"),
            "fed_rate_direction": sig.get("fed_rate_direction"),
            "credit_spread_pctile_1y": sig.get("credit_spread_pctile_1y"),
            "credit_stress_elevated": sig.get("credit_stress_elevated"),
            "financial_stress_above_avg": sig.get("financial_stress_above_avg"),
            "real_rate_10y_estimate": sig.get("real_rate_10y_estimate"),
        }
        caution = sig.get("yield_curve_inverted") or sig.get("credit_stress_elevated") \
                  or sig.get("financial_stress_above_avg")
        snap["fred_regime_label"] = "caution" if caution else "expansion"
        return snap
    except Exception as e:
        print(f"WARN: fred load failed: {e}", file=sys.stderr)
        return None


def get_market_snapshot():
    try:
        import yfinance as yf
        import numpy as np
    except ImportError:
        return {}
    out = {}
    try:
        spy = yf.Ticker("SPY").history(period="60d", auto_adjust=False)
        # yfinance occasionally returns a trailing NaN Close row (observed 2026-06-10)
        spy_close_series = spy["Close"].dropna() if not spy.empty else None
        if spy_close_series is not None and not spy_close_series.empty:
            closes = spy_close_series.values
            out["spy_close"] = round(float(closes[-1]), 2)
            if len(closes) >= 50:
                ma50 = float(np.mean(closes[-50:]))
                out["spy_ma50"] = round(ma50, 2)
                out["spy_ma50_status"] = "above" if closes[-1] > ma50 else "below"
            if len(closes) >= 15:
                # shared Wilder RSI (skills/_shared/technical_core) — same numbers as momentum/sector pages
                rsi = _shared_rsi_14(spy_close_series).iloc[-1]
                if rsi == rsi:  # not NaN
                    out["spy_rsi_14"] = round(float(rsi), 1)
            if len(closes) >= 6:
                out["spy_5d_pct"] = round((float(closes[-1]) / float(closes[-6]) - 1) * 100, 2)
        vix = yf.Ticker("^VIX").history(period="5d", auto_adjust=False)
        if not vix.empty:
            out["vix"] = round(float(vix["Close"].iloc[-1]), 2)
    except Exception as e:
        print(f"WARN: market snapshot failed: {e}", file=sys.stderr)
    return out


# ---------- per-ticker prediction (in-process; uses predict.py 4h cache) ----------

def run_short_term_target(ticker, timeout=60):
    if _predict_inproc is not None:
        # In-process: no per-ticker hard timeout, but the global
        # socket.setdefaulttimeout(15) bounds every network op inside predict.
        try:
            return _predict_inproc(ticker)
        except Exception as e:
            return {"ticker": ticker, "error": str(e)[:200]}
    try:
        r = subprocess.run(
            ["python3", str(PREDICT_SCRIPT), ticker, "--json-only"],
            capture_output=True, text=True, timeout=timeout
        )
        if r.returncode != 0:
            return {"ticker": ticker, "error": (r.stderr or "").strip()[:200]}
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError as e:
            return {"ticker": ticker, "error": f"json parse: {e}"}
    except subprocess.TimeoutExpired:
        return {"ticker": ticker, "error": "predict_timeout"}
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def _timed_short_term_target(ticker, timeout=60):
    t0 = time.time()
    pred = run_short_term_target(ticker, timeout=timeout)
    return ticker, pred, time.time() - t0


def run_short_term_targets(tickers, workers=1, timeout=60):
    """Run short-term predictions with bounded subprocess fanout."""
    total = len(tickers)
    pred_start = time.time()
    slow_tickers = []
    all_predictions = {}
    workers = max(1, int(workers or 1))

    if workers == 1:
        for i, t in enumerate(tickers, 1):
            t0 = time.time()
            all_predictions[t] = run_short_term_target(t, timeout=timeout)
            dt = time.time() - t0
            if dt > 5:
                slow_tickers.append((t, dt))
                _log(f"  [{i}/{total}] {t} took {dt:.1f}s "
                     f"{'(TIMEOUT)' if all_predictions[t].get('error') == 'predict_timeout' else ''}")
            if i % 10 == 0:
                _log(f"  ... {i}/{total} (elapsed {time.time() - pred_start:.0f}s)")
        return all_predictions, slow_tickers, time.time() - pred_start

    _log(f"Prediction fanout: {workers} workers")
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_timed_short_term_target, t, timeout): t for t in tickers}
        for fut in as_completed(futs):
            t = futs[fut]
            try:
                _, pred, dt = fut.result()
            except Exception as e:
                pred = {"ticker": t, "error": str(e)}
                dt = 0
            all_predictions[t] = pred
            done += 1
            if dt > 5:
                slow_tickers.append((t, dt))
                _log(f"  [{done}/{total}] {t} took {dt:.1f}s "
                     f"{'(TIMEOUT)' if pred.get('error') == 'predict_timeout' else ''}")
            if done % 10 == 0 or done == total:
                _log(f"  ... {done}/{total} (elapsed {time.time() - pred_start:.0f}s)")
    return all_predictions, slow_tickers, time.time() - pred_start


# ---------- regime: 2-badge + 1-factor ----------

def compute_regime_badges(regime):
    """Per design discussion: 2 independent badges (RSI + VIX), 4-quadrant aware."""
    rsi = regime.get("spy_rsi_14")
    vix = regime.get("vix")
    badges = {"rsi": None, "vix": None}

    if rsi is not None:
        if rsi >= 85:
            badges["rsi"] = {
                "level": "extreme_overbought", "value": rsi,
                "msg": f"SPY RSI {rsi:.1f} 極端超買 — mean reversion 風險",
                "msg_en": f"SPY RSI {rsi:.1f} extreme overbought — mean reversion risk",
            }
        elif rsi <= 25:
            badges["rsi"] = {
                "level": "extreme_oversold", "value": rsi,
                "msg": f"SPY RSI {rsi:.1f} 極端超賣 — 反彈燃料",
                "msg_en": f"SPY RSI {rsi:.1f} extreme oversold — contrarian fuel",
            }

    if vix is not None:
        if vix >= 40:
            badges["vix"] = {
                "level": "capitulation", "value": vix,
                "msg": f"VIX {vix:.1f} 投降底 — 中期 contrarian buy",
                "msg_en": f"VIX {vix:.1f} capitulation — mid-term contrarian buy",
            }
        elif vix >= 35:
            badges["vix"] = {
                "level": "panic", "value": vix,
                "msg": f"VIX {vix:.1f} 恐慌 — 防禦",
                "msg_en": f"VIX {vix:.1f} panic — defensive posture",
            }
        elif vix >= 25:
            badges["vix"] = {
                "level": "elevated_fear", "value": vix,
                "msg": f"VIX {vix:.1f} 緊張 — caution",
                "msg_en": f"VIX {vix:.1f} elevated fear — caution",
            }
        elif vix <= 13:
            badges["vix"] = {
                "level": "complacency", "value": vix,
                "msg": f"VIX {vix:.1f} 低度恐慌 — 複雜頂可能性",
                "msg_en": f"VIX {vix:.1f} complacency — possible top-distribution",
            }

    return badges


def compute_regime_factor(regime):
    """Pick max(RSI偏離, VIX偏離) per spec table; 1.0 when normal."""
    rsi = regime.get("spy_rsi_14")
    vix = regime.get("vix")
    triggers = []
    if rsi is not None:
        if rsi > 85: triggers.append((0.90, f"rsi_{rsi:.0f}_overbought"))
        if rsi < 25: triggers.append((1.10, f"rsi_{rsi:.0f}_oversold"))
    if vix is not None:
        if vix > 40: triggers.append((1.15, f"vix_{vix:.0f}_capitulation"))
        elif vix > 35: triggers.append((0.85, f"vix_{vix:.0f}_panic"))
        elif vix > 25: triggers.append((0.92, f"vix_{vix:.0f}_elevated"))
    if not triggers:
        return {"factor": 1.0, "reason": "normal_regime", "triggers": []}
    triggers.sort(key=lambda x: abs(x[0] - 1.0), reverse=True)
    chosen = triggers[0]
    return {"factor": chosen[0], "reason": chosen[1], "triggers": triggers}


# ---------- per-theme short-term metrics ----------

def select_top_movers_ranked(theme, all_predictions, top_n, enrichments=None):
    """Rank theme's mover predictions by (5d target_pct × confidence × enrichment_multiplier).

    v0.3.1 — direction-aware ranking. Bullish themes pick top-N MOST positive
    (long candidates). Bearish themes pick top-N MOST negative (short candidates
    or "stocks most likely to drop further"). Previous behavior always picked
    most-positive regardless of theme direction → bearish themes showed all-bullish
    movers, contradicting the theme call.

    enrichments: dict {ticker: enrichment_dict} from enrich_movers(); if None,
    multiplier defaults to 1.0 and behavior matches v0.2.
    """
    direction = (theme.get("direction") or "bullish").lower()
    candidates = []
    for ticker in (theme.get("representative_stocks") or []):
        pred = all_predictions.get(ticker)
        if not pred or pred.get("error"):
            continue
        h5 = pred.get("horizons", {}).get("5d", {})
        if h5.get("status") != "ok":
            continue
        raw_score = (h5.get("target_central_pct") or 0) * (h5.get("confidence") or 0)
        enrich = (enrichments or {}).get(ticker) or {}
        mult = enrich.get("enrichment_multiplier", 1.0) if isinstance(enrich, dict) else 1.0
        final_score = raw_score * mult
        candidates.append((final_score, raw_score, ticker, pred))
    # bullish → DESC (top positive); bearish → ASC (top negative); other (neutral / unknown) → DESC
    candidates.sort(key=lambda x: x[0], reverse=(direction != "bearish"))
    return candidates[:top_n]


def compute_theme_short_term(theme, all_predictions, regime_factor):
    """Compute bullish_breadth + conviction per horizon, OVER ALL THEME CONSTITUENTS.

    Critical fix (v0.2.1, per user feedback): breadth was previously computed on
    the top-5 movers (already pre-selected by score×conv → biased to 100%
    bullish). Now uses ALL representative_stocks of the theme so breadth
    actually reflects "how many of this theme's stocks are predicted up".

    Returns:
      {
        "n_total_constituents": int,
        "primary_horizon": "5d",
        "by_horizon": {"1d": {bullish_breadth_pct, avg_conviction, n_valid, ...}, ...},
        "components": {...}  # 5d-based driver averages, full constituent set
      }
    """
    constituents = theme.get("representative_stocks") or []
    n_total = len(constituents)

    if n_total == 0:
        return {
            "n_total_constituents": 0,
            "primary_horizon": "5d",
            "by_horizon": {h: {"bullish_breadth_pct": None,
                               "bullish_breadth_pct_adjusted": None,
                               "avg_conviction": None,
                               "mean_target_pct": None,
                               "n_valid_predictions": 0,
                               "n_bullish": 0}
                           for h in ("1d", "5d", "15d")},
            "trailing": {"trailing_breadth_5d_pct": None, "median_trailing_5d_pct": None,
                         "median_trailing_20d_pct": None, "median_momentum_score": None,
                         "n_valid_trailing": 0, "n_up_5d": 0},
            "components": {},
        }

    by_horizon = {}
    for h in ("1d", "5d", "15d"):
        target_pcts, confs = [], []
        for ticker in constituents:
            pred = all_predictions.get(ticker)
            if not pred or pred.get("error"):
                continue
            hh = pred.get("horizons", {}).get(h, {})
            if hh.get("status") != "ok":
                continue
            target_pcts.append(hh.get("target_central_pct", 0))
            confs.append(hh.get("confidence", 0))
        n_valid = len(target_pcts)
        if n_valid == 0:
            by_horizon[h] = {
                "bullish_breadth_pct": None,
                "bullish_breadth_pct_adjusted": None,
                "avg_conviction": None,
                "mean_target_pct": None,
                "n_valid_predictions": 0,
                "n_bullish": 0,
            }
            continue
        bullish = sum(1 for p in target_pcts if p > 0)
        bp = bullish / n_valid * 100
        by_horizon[h] = {
            "bullish_breadth_pct": round(bp, 1),
            "bullish_breadth_pct_adjusted": round(bp * regime_factor, 1),
            "avg_conviction": round(sum(confs) / n_valid, 3),
            "mean_target_pct": round(sum(target_pcts) / n_valid, 2),
            "n_valid_predictions": n_valid,
            "n_bullish": bullish,
        }

    # ── Trailing (REAL price) breadth — direction-honest, can read bearish ──
    # Distinct from bullish_breadth_pct (forward target>0, structurally >50).
    # trailing_breadth = % of constituents whose price ACTUALLY rose over 5d.
    def _median(vals):
        s = sorted(vals)
        n = len(s)
        if n == 0:
            return None
        m = n // 2
        return s[m] if n % 2 else round((s[m - 1] + s[m]) / 2, 2)

    tr5, tr20, mom_all = [], [], []
    for ticker in constituents:
        pred = all_predictions.get(ticker)
        if not pred or pred.get("error"):
            continue
        r5 = pred.get("trailing_return_5d_pct")
        r20 = pred.get("trailing_return_20d_pct")
        if r5 is not None:
            tr5.append(r5)
        if r20 is not None:
            tr20.append(r20)
        d = pred.get("horizons", {}).get("5d", {}).get("drivers", {})
        if d and d.get("momentum_score") is not None:
            mom_all.append(d.get("momentum_score"))
    n_tr5 = len(tr5)
    if n_tr5:
        up5 = sum(1 for r in tr5 if r > 0)
        trailing_breadth = round(up5 / n_tr5 * 100, 1)
    else:
        up5 = 0
        trailing_breadth = None
    trailing = {
        "trailing_breadth_5d_pct": trailing_breadth,   # % constituents with REAL 5d gain
        "median_trailing_5d_pct": _median(tr5),
        "median_trailing_20d_pct": _median(tr20),
        "median_momentum_score": _median(mom_all),     # -1..1 RSI/MA structural lean
        "n_valid_trailing": n_tr5,
        "n_up_5d": up5,
    }

    # Shared components context — uses 5d drivers across ALL constituents
    momentums, sectors, atrs = [], [], []
    for ticker in constituents:
        pred = all_predictions.get(ticker)
        if not pred or pred.get("error"):
            continue
        d = pred.get("horizons", {}).get("5d", {}).get("drivers", {})
        if d:
            momentums.append(d.get("momentum_score", 0))
            sectors.append(d.get("sector_heat", 0))
            atrs.append(d.get("atr_pct", 0))
    n_d = len(momentums)
    components = {"regime_factor_applied": regime_factor}
    if n_d:
        components.update({
            "mean_momentum": round(sum(momentums) / n_d, 3),
            "mean_sector_heat": round(sum(sectors) / n_d, 3),
            "mean_atr_pct": round(sum(atrs) / n_d, 3),
        })

    return {
        "n_total_constituents": n_total,
        "primary_horizon": "5d",
        "by_horizon": by_horizon,
        "trailing": trailing,
        "components": components,
    }


def tag_concentration(themes_block):
    """§11.B: same theme ≥ 2 ok-predictions → flag (proxy for sub-industry)."""
    for theme in themes_block:
        ok_tickers = [m["ticker"] for m in theme.get("top_movers", []) if not m["short_term"].get("error")]
        if len(ok_tickers) >= 2:
            for m in theme["top_movers"]:
                if m["short_term"].get("error"):
                    m["concentration_flag"] = None
                    continue
                co = [t for t in ok_tickers if t != m["ticker"]]
                m["concentration_flag"] = {
                    "theme": theme["name"],
                    "co_recommendations": co,
                    "warning": (
                        f"Theme '{theme['name']}' has {len(ok_tickers)} co-recs; "
                        f"correlated drawdown risk in same-theme exposure"
                    ),
                }
        else:
            for m in theme.get("top_movers", []):
                m["concentration_flag"] = None
    return themes_block


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Thematic Screener v0.2 — Tactical Opportunity Radar")
    ap.add_argument("--top-movers", type=int, default=5,
                    help="Top N movers per theme (default 5)")
    ap.add_argument("--no-write", action="store_true",
                    help="Skip writing to data/recommendations/")
    ap.add_argument("--json-only", action="store_true",
                    help="Compact JSON output")
    ap.add_argument("--predict-workers", type=int, default=1,
                    help="Bounded parallelism for per-ticker predict.py subprocesses")
    ap.add_argument("--enrich-workers", type=int, default=12,
                    help="Bounded FMP-pool-governed enrichment concurrency")
    args = ap.parse_args()

    themes_data, theme_meta = load_latest_themes()
    if not themes_data:
        print(json.dumps({"error": "no_theme_detector_cache", "detail": theme_meta}))
        sys.exit(1)
    all_themes = (themes_data.get("themes") or {}).get("all", [])
    if not all_themes:
        print(json.dumps({"error": "themes.all empty in cache"}))
        sys.exit(1)

    fred = load_fred_snapshot()
    market = get_market_snapshot()
    regime_snapshot = {**market}
    if fred:
        regime_snapshot.update(fred)
    badges = compute_regime_badges(regime_snapshot)
    factor_info = compute_regime_factor(regime_snapshot)

    # Collect all unique tickers across ALL themes — dedup so cache hits maximally
    all_tickers = sorted({
        ticker
        for theme in all_themes
        for ticker in (theme.get("representative_stocks") or [])
    })
    _log(f"Predicting {len(all_tickers)} unique tickers across {len(all_themes)} themes (cache 4h)...")

    all_predictions, slow_tickers, pred_elapsed = run_short_term_targets(
        all_tickers,
        workers=args.predict_workers,
    )
    _log(f"Predict phase done: {len(all_tickers)} tickers in {pred_elapsed:.0f}s "
         f"({len(slow_tickers)} slow >5s)")

    # v0.3 — enrich every ticker (cap tier + earnings landmines + quality + smart-money + analyst)
    enrichments = {}
    if HAS_ENRICH:
        # Restrict to tickers that have a usable prediction (skip noise)
        ok_tickers = [t for t in all_tickers
                      if all_predictions.get(t) and not all_predictions[t].get("error")]
        _log(f"Enriching {len(ok_tickers)} tickers (caches first, light FMP fetches as needed)...")
        enrich_start = time.time()
        try:
            enrichments = enrich_movers(ok_tickers, workers=args.enrich_workers)
            _log(f"Enrich phase done in {time.time() - enrich_start:.0f}s "
                 f"({len(enrichments)} enriched)")
        except Exception as e:
            print(f"WARN: enrich failed (continuing without): {e}", file=sys.stderr)

    # Build per-theme blocks
    themes_block = []
    for theme in all_themes:
        ranked = select_top_movers_ranked(theme, all_predictions, args.top_movers, enrichments)
        # Breadth/conviction over ALL constituents (per user feedback v0.2.1)
        st = compute_theme_short_term(theme, all_predictions, factor_info["factor"])
        themes_block.append({
            "name": theme["name"],
            "direction": theme.get("direction"),
            "mid_heat": round(theme.get("heat", 0), 1),
            "heat_label": theme.get("heat_label"),
            "lifecycle_stage": theme.get("stage"),
            "confidence": theme.get("confidence"),
            "proxy_etfs": theme.get("proxy_etfs", []),
            "short_term": st,
            "top_movers": [
                {
                    "ticker": tk,
                    "short_term": pred,
                    "concentration_flag": None,
                    # v0.3 — enrichment fields (always present, may be {} if unavailable)
                    "enrichment": enrichments.get(tk) or {},
                    "raw_score": round(raw_score, 4),
                    "final_score": round(final_score, 4),
                }
                for final_score, raw_score, tk, pred in ranked
            ],
        })
    themes_block = tag_concentration(themes_block)

    # Sort themes by REAL trailing 5d breadth descending (default sort).
    # v0.4: switched off forward bullish_breadth_pct (structurally >50, direction-blind)
    # → trailing_breadth_5d_pct so leaders surface and genuinely-weak themes sink (still visible).
    themes_block.sort(
        key=lambda t: (t["short_term"].get("trailing", {}).get("trailing_breadth_5d_pct") or -1),
        reverse=True,
    )

    out = {
        "as_of": datetime.datetime.utcnow().isoformat() + "Z",
        "experimental": True,
        "framework": "Tactical Opportunity Radar v0.3 (thematic-screener)",
        "regime_snapshot": regime_snapshot,
        "regime_badges": badges,
        "regime_factor": factor_info,
        "theme_detector_meta": theme_meta,
        "screener_params": {
            "top_movers": args.top_movers,
            "n_themes_total": len(all_themes),
            "n_unique_tickers_predicted": len(all_tickers),
            "predict_workers": args.predict_workers,
            "enrich_workers": args.enrich_workers,
            "show_all_themes": True,
        },
        "themes": themes_block,
        "global_warnings": [],
    }
    if isinstance(theme_meta, dict) and theme_meta.get("age_hr", 0) > 24:
        out["global_warnings"].append(
            f"theme-detector cache is {theme_meta['age_hr']}h old; recommend refresh"
        )
    if not fred:
        out["global_warnings"].append("FRED snapshot unavailable; regime context partial")
    if not market:
        out["global_warnings"].append("market snapshot fetch failed; regime context partial")

    print(json.dumps(out, indent=None if args.json_only else 2, default=str))

    if not args.no_write:
        RECS_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.date.today().isoformat()
        path = RECS_DIR / f"{date_str}.json"
        tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
        try:
            tmp.write_text(json.dumps(out, indent=2, default=str))
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
        print(f"\nWrote {path}", file=sys.stderr)


if __name__ == "__main__":
    main()

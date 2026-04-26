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
import argparse
import datetime
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
SKILL_DIR = Path(__file__).resolve().parent.parent
RECS_DIR = SKILL_DIR / "data" / "recommendations"
THEME_CACHE = ROOT / "skills" / "theme-detector" / "cache"
FRED_CACHE = ROOT / "skills" / "fred-macro" / "cache"
PREDICT_SCRIPT = ROOT / "skills" / "short-term-target" / "scripts" / "predict.py"


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
        if not spy.empty:
            closes = spy["Close"].values
            out["spy_close"] = round(float(closes[-1]), 2)
            if len(closes) >= 50:
                ma50 = float(np.mean(closes[-50:]))
                out["spy_ma50"] = round(ma50, 2)
                out["spy_ma50_status"] = "above" if closes[-1] > ma50 else "below"
            if len(closes) >= 15:
                deltas = np.diff(closes[-15:])
                gains = np.where(deltas > 0, deltas, 0).mean()
                losses = np.where(deltas < 0, -deltas, 0).mean()
                rsi = 100 - (100 / (1 + gains / losses)) if losses > 0 else 100
                out["spy_rsi_14"] = round(float(rsi), 1)
            if len(closes) >= 6:
                out["spy_5d_pct"] = round((float(closes[-1]) / float(closes[-6]) - 1) * 100, 2)
        vix = yf.Ticker("^VIX").history(period="5d", auto_adjust=False)
        if not vix.empty:
            out["vix"] = round(float(vix["Close"].iloc[-1]), 2)
    except Exception as e:
        print(f"WARN: market snapshot failed: {e}", file=sys.stderr)
    return out


# ---------- per-ticker prediction (subprocess; uses predict.py 4h cache) ----------

def run_short_term_target(ticker, timeout=60):
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

def select_top_movers_ranked(theme, all_predictions, top_n):
    """Rank theme's mover predictions by (5d target_pct × confidence) desc, take top N."""
    candidates = []
    for ticker in (theme.get("representative_stocks") or []):
        pred = all_predictions.get(ticker)
        if not pred or pred.get("error"):
            continue
        h5 = pred.get("horizons", {}).get("5d", {})
        if h5.get("status") != "ok":
            continue
        score = (h5.get("target_central_pct") or 0) * (h5.get("confidence") or 0)
        candidates.append((score, ticker, pred))
    candidates.sort(key=lambda x: x[0], reverse=True)
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
    print(f"Predicting {len(all_tickers)} unique tickers across {len(all_themes)} themes "
          f"(cache 4h)...", file=sys.stderr)

    all_predictions = {}
    for i, t in enumerate(all_tickers, 1):
        if i % 10 == 0:
            print(f"  ... {i}/{len(all_tickers)}", file=sys.stderr)
        all_predictions[t] = run_short_term_target(t)

    # Build per-theme blocks
    themes_block = []
    for theme in all_themes:
        ranked = select_top_movers_ranked(theme, all_predictions, args.top_movers)
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
                {"ticker": tk, "short_term": pred, "concentration_flag": None}
                for _, tk, pred in ranked
            ],
        })
    themes_block = tag_concentration(themes_block)

    # Sort themes by 5d bullish_breadth_pct descending (default sort)
    themes_block.sort(
        key=lambda t: (t["short_term"].get("by_horizon", {}).get("5d", {}).get("bullish_breadth_pct") or -1),
        reverse=True,
    )

    out = {
        "as_of": datetime.datetime.utcnow().isoformat() + "Z",
        "experimental": True,
        "framework": "Tactical Opportunity Radar v0.2 (thematic-screener)",
        "regime_snapshot": regime_snapshot,
        "regime_badges": badges,
        "regime_factor": factor_info,
        "theme_detector_meta": theme_meta,
        "screener_params": {
            "top_movers": args.top_movers,
            "n_themes_total": len(all_themes),
            "n_unique_tickers_predicted": len(all_tickers),
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
        path.write_text(json.dumps(out, indent=2, default=str))
        print(f"\nWrote {path}", file=sys.stderr)


if __name__ == "__main__":
    main()

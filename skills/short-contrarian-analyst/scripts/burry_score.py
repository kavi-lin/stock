#!/usr/bin/env python3
"""
short-contrarian-analyst — Burry Score (0-100) + T4 veto check.

Usage:
    python3 burry_score.py NVDA
    python3 burry_score.py KO --json-only
"""
import argparse
import json
import sys
from datetime import datetime, timezone

import yfinance as yf


def score_fcf_yield(fcf_yield_pct):
    if fcf_yield_pct is None: return None
    if fcf_yield_pct < 2:   return 10.0 + max(0, fcf_yield_pct) * 5
    if fcf_yield_pct < 5:   return 20 + (fcf_yield_pct - 2) * 10    # → 50
    if fcf_yield_pct < 10:  return 50 + (fcf_yield_pct - 5) * 8     # → 90
    return 90.0


def score_ev_ebit(ev_ebit):
    if ev_ebit is None or ev_ebit <= 0: return None
    if ev_ebit > 30: return 10.0
    if ev_ebit > 15: return 50 - (ev_ebit - 15) * (40 / 15)         # 50→10
    if ev_ebit > 8:  return 90 - (ev_ebit - 8) * (40 / 7)           # 90→50
    return 90.0


def score_de(de):
    if de is None: return None
    if de > 2:   return 10.0
    if de > 1:   return 50 - (de - 1) * 40                          # 50→10
    if de > 0.3: return 90 - (de - 0.3) * (40 / 0.7)                # 90→50
    return 90.0


def score_52w(pct_below):
    # pct_below = positive number = % below 52w high
    if pct_below < 5:   return 20.0
    if pct_below < 20:  return 20 + (pct_below - 5) * (40 / 15)     # → 60
    if pct_below < 40:  return 60 + (pct_below - 20) * (30 / 20)    # → 90
    return 90.0


def score_insider(net):
    return {"BUY": 80, "NEUTRAL": 50, "SELL": 20, "UNKNOWN": None}[net]


def get_insider_net(tk):
    try:
        trans = tk.insider_transactions
        if trans is None or trans.empty:
            return "UNKNOWN"
        # Columns vary; look for any Value/Shares with Transaction type
        recent = trans.head(10)
        buys = 0
        sells = 0
        for _, row in recent.iterrows():
            text = " ".join(str(v) for v in row.values).lower()
            if "buy" in text or "purchase" in text:
                buys += 1
            elif "sale" in text or "sell" in text:
                sells += 1
        if buys > sells * 1.5: return "BUY"
        if sells > buys * 1.5: return "SELL"
        return "NEUTRAL"
    except Exception:
        return "UNKNOWN"


def compute(ticker: str):
    tk = yf.Ticker(ticker)
    info = tk.info or {}

    # FCF yield = FCF / EV
    # yfinance's freeCashflow field is sometimes wrong (e.g. KO reports -1.46B
    # despite OpCF +7.4B). Fallback: if FCF <= 0 but OpCF > 0, estimate FCF ≈ OpCF × 0.85
    fcf = info.get("freeCashflow")
    op_cf = info.get("operatingCashflow")
    ev = info.get("enterpriseValue")
    if (fcf is None or fcf <= 0) and op_cf and op_cf > 0:
        fcf = op_cf * 0.85  # assume 15% capex/OpCF ratio (mature-company typical)
    fcf_yield_pct = None
    if fcf and ev and ev > 0:
        fcf_yield_pct = (fcf / ev) * 100

    # EV/EBIT — use EBITDA as proxy if EBIT not available
    ebit = info.get("ebitda")  # yfinance doesn't expose EBIT directly
    ev_ebit = None
    if ebit and ev and ebit > 0:
        ev_ebit = ev / ebit  # technically EV/EBITDA; close enough for screening

    # yfinance returns debtToEquity as percentage (NVDA=7.26, KO=139.79, PG=68.72).
    # Always divide by 100 to get the ratio.
    de = info.get("debtToEquity")
    if de is not None:
        de = de / 100

    # 52-week high
    try:
        hist = tk.history(period="1y", auto_adjust=True)["Close"].dropna()
        high_52 = float(hist.max())
        current = float(hist.iloc[-1])
        pct_below_high = (1 - current / high_52) * 100
    except Exception:
        pct_below_high = 0.0
        current = None

    insider_net = get_insider_net(tk)

    comp_scores = {
        "fcf_yield": score_fcf_yield(fcf_yield_pct),
        "ev_ebit": score_ev_ebit(ev_ebit),
        "debt_to_equity": score_de(de),
        "pct_below_52w_high": score_52w(pct_below_high),
        "insider": score_insider(insider_net),
    }
    weights = {"fcf_yield": 0.35, "ev_ebit": 0.25, "debt_to_equity": 0.15,
               "pct_below_52w_high": 0.15, "insider": 0.10}

    # Renormalize weights over available components
    active = {k: w for k, w in weights.items() if comp_scores[k] is not None}
    total_w = sum(active.values())
    burry = round(sum(comp_scores[k] * w for k, w in active.items()) / total_w, 1) if total_w else None

    if burry is None:
        verdict = "UNKNOWN"
    elif burry < 20:
        verdict = "T4_VETO"
    elif burry < 35:
        verdict = "WARNING"
    elif burry >= 60:
        verdict = "VALUE_BONUS"
    else:
        verdict = "NEUTRAL"

    reasoning_bits = []
    if fcf_yield_pct is not None: reasoning_bits.append(f"FCF yield {fcf_yield_pct:.1f}%")
    if ev_ebit is not None: reasoning_bits.append(f"EV/EBITDA {ev_ebit:.1f}")
    if de is not None: reasoning_bits.append(f"D/E {de:.2f}")
    reasoning_bits.append(f"{pct_below_high:.0f}% below 52wH")
    reasoning_bits.append(f"insider={insider_net}")

    return {
        "ticker": ticker.upper(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "burry_score": burry,
        "verdict": verdict,
        "components": {
            "fcf_yield_pct": round(fcf_yield_pct, 2) if fcf_yield_pct is not None else None,
            "ev_ebit": round(ev_ebit, 2) if ev_ebit is not None else None,
            "debt_to_equity": round(de, 2) if de is not None else None,
            "pct_below_52w_high": round(pct_below_high, 2),
            "insider_net": insider_net,
        },
        "component_scores": {k: (round(v, 1) if v is not None else None) for k, v in comp_scores.items()},
        "weights_active": list(active.keys()),
        "reasoning": " │ ".join(reasoning_bits),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()

    try:
        out = compute(args.ticker)
    except Exception as e:
        print(json.dumps({"error": str(e), "ticker": args.ticker}))
        sys.exit(1)

    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not args.json_only:
        print(f"\n→ {out['ticker']} Burry={out['burry_score']} {out['verdict']}", file=sys.stderr)


if __name__ == "__main__":
    main()

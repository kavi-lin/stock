#!/usr/bin/env python3
"""
portfolio-risk-manager — vol-adjusted position cap + correlation multiplier.

Usage:
    python3 risk_manager.py NVDA
    python3 risk_manager.py NVDA --positions positions.json --vol-budget 0.8
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf


def load_positions(path: Path):
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    # positions.json may be list or {positions:[...]}
    if isinstance(raw, dict):
        raw = raw.get("positions", raw.get("holdings", []))
    out = []
    for p in raw:
        if not isinstance(p, dict):
            continue
        tkr = p.get("ticker") or p.get("symbol")
        if not tkr:
            continue
        status = (p.get("status") or "open").lower()
        if status in ("closed", "exited"):
            continue
        out.append({
            "ticker": tkr.upper(),
            "shares": float(p.get("shares", 0) or 0),
            "entry_price": float(p.get("entry_price", 0) or 0),
        })
    return out


def fetch_history(tickers, period="6mo"):
    if not tickers:
        return pd.DataFrame()
    data = yf.download(list(tickers), period=period, interval="1d",
                       auto_adjust=True, progress=False, group_by="column")
    if len(tickers) == 1:
        return pd.DataFrame({tickers[0]: data["Close"].squeeze()}).dropna()
    closes = data["Close"] if "Close" in data.columns.get_level_values(0) else data
    return closes.dropna(how="all")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--positions", default="positions.json")
    ap.add_argument("--vol-budget", type=float, default=0.6, help="daily portfolio vol budget pct")
    ap.add_argument("--portfolio-size", type=float, default=100000)
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()

    candidate = args.ticker.upper()
    positions = load_positions(Path(args.positions))
    holdings_tickers = [p["ticker"] for p in positions if p["ticker"] != candidate]

    # Candidate stats
    tk = yf.Ticker(candidate)
    hist = tk.history(period="6mo", auto_adjust=True)["Close"].dropna()
    if len(hist) < 30:
        print(json.dumps({"error": f"insufficient data for {candidate}"}))
        sys.exit(1)
    rets = hist.pct_change().dropna()
    daily_vol = float(rets.std() * 100)
    ann_vol = float(rets.std() * np.sqrt(252) * 100)

    # Correlation with existing portfolio
    avg_corr = 0.0
    if holdings_tickers:
        all_hist = fetch_history([candidate] + holdings_tickers, "6mo")
        if not all_hist.empty and candidate in all_hist.columns:
            all_rets = all_hist.pct_change().dropna()
            corrs = []
            for h in holdings_tickers:
                if h in all_rets.columns:
                    c = all_rets[candidate].corr(all_rets[h])
                    if not np.isnan(c):
                        corrs.append(float(c))
            avg_corr = float(np.mean(corrs)) if corrs else 0.0

    # Sector info
    try:
        info = tk.info or {}
        candidate_sector = info.get("sector", "Unknown")
    except Exception:
        candidate_sector = "Unknown"

    # Raw vol-adjusted cap: vol_budget / daily_vol * 100 (= position % of portfolio)
    raw_cap = (args.vol_budget / daily_vol * 100) if daily_vol > 0 else 0.0
    raw_cap = float(min(raw_cap, 20.0))  # hard cap 20% regardless

    # Correlation multiplier
    a = abs(avg_corr)
    if a < 0.3:   corr_mult = 1.00
    elif a < 0.6: corr_mult = 0.85
    elif a < 0.8: corr_mult = 0.70
    else:         corr_mult = 0.55

    # Sector concentration check (best-effort, requires sector per holding)
    sector_cap_triggered = False
    if positions and candidate_sector != "Unknown":
        sector_exposure = 0.0
        portfolio_value = 0.0
        for p in positions:
            try:
                h_info = yf.Ticker(p["ticker"]).info or {}
                h_price = yf.Ticker(p["ticker"]).history(period="5d")["Close"].iloc[-1]
                val = p["shares"] * float(h_price)
                portfolio_value += val
                if h_info.get("sector") == candidate_sector:
                    sector_exposure += val
            except Exception:
                continue
        if portfolio_value > 0 and (sector_exposure / portfolio_value) > 0.30:
            sector_cap_triggered = True

    final_cap = raw_cap * corr_mult
    if sector_cap_triggered:
        final_cap *= 0.5

    reasoning_bits = [
        f"daily_vol={daily_vol:.2f}% → raw_cap={raw_cap:.2f}%",
        f"avg_corr={avg_corr:+.2f} → mult={corr_mult}",
    ]
    if sector_cap_triggered:
        reasoning_bits.append(f"sector {candidate_sector} >30% exposure → ×0.5")

    out = {
        "ticker": candidate,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "vol_budget_pct": args.vol_budget,
            "positions_loaded": len(positions),
            "candidate_sector": candidate_sector,
            "portfolio_size_usd": args.portfolio_size,
        },
        "ticker_stats": {
            "daily_vol_pct": round(daily_vol, 3),
            "ann_vol_pct": round(ann_vol, 2),
            "avg_correlation_with_portfolio": round(avg_corr, 3),
        },
        "raw_vol_adjusted_cap_pct": round(raw_cap, 2),
        "correlation_multiplier": corr_mult,
        "sector_cap_triggered": sector_cap_triggered,
        "final_position_cap_pct": round(final_cap, 2),
        "reasoning": " │ ".join(reasoning_bits),
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not args.json_only:
        print(f"\n→ {candidate} final_cap={out['final_position_cap_pct']}%", file=sys.stderr)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
build_pack.py — Weekly Tech Playbook · data assembly layer (0 LLM)

Assembles a decision pack the LLM reads before selecting the 3 baskets:
  - regime snapshot      (market_mood.json + thematic regime_snapshot)
  - hot themes ranked    (latest thematic-screener recommendations)
  - committee verdicts   (recent reports/<DATE>_<TICKER>.md — Final Score / fair value / band / decision cap)
  - candidate universe   (live price + 5d/1mo momentum via yfinance)

Writes the full pack plus a committee-blind pack used by Codex Review before
the committee output is revealed.
This is the deterministic input to the LLM selection step (see SKILL.md). It does NOT pick stocks.

Usage:
  python3 build_pack.py [--date YYYY-MM-DD] [--no-fetch] [--universe T1,T2,...]
"""
import argparse
import datetime as _dt
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
REPORTS = os.path.join(ROOT, "reports")
THEMATIC = os.path.join(ROOT, "skills", "thematic-screener", "data", "recommendations")
MOOD = os.path.join(ROOT, "Dashboard", "market_mood.json")

# Tech-centric candidate universe spanning the hottest themes. Edit freely — the
# LLM selection step picks 10 per basket out of whatever lands in the pack.
DEFAULT_UNIVERSE = [
    # AI semis / megacap quality
    "NVDA", "TSM", "AVGO", "MSFT", "GOOGL", "AAPL", "META", "ORCL", "ANET", "TXN",
    "AMAT", "ASML",
    # high-beta theme riders
    "AMD", "MU", "MRVL", "CRDO", "ALAB", "SMCI", "VRT", "PLTR", "NBIS",
    # AI power / nuclear / uranium
    "CEG", "VST", "CCJ", "UEC",
    # quantum
    "IONQ", "RGTI",
]


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def latest_thematic():
    files = sorted(glob.glob(os.path.join(THEMATIC, "*.json")), reverse=True)
    if not files:
        return None, None
    d = _load_json(files[0])
    return d, os.path.basename(files[0])


def themes_ranked(thematic):
    out = []
    if not thematic:
        return out
    for t in thematic.get("themes", []):
        st5 = (t.get("short_term", {}).get("by_horizon", {}) or {}).get("5d", {})
        out.append({
            "name": t.get("name"),
            "mid_heat": t.get("mid_heat"),
            "heat_label": t.get("heat_label"),
            "lifecycle": t.get("lifecycle_stage"),
            "direction": t.get("direction"),
            "confidence": t.get("confidence"),
            "breadth_5d_pct": st5.get("bullish_breadth_pct"),
            "target_5d_pct": st5.get("mean_target_pct"),
            "movers": [m.get("ticker") for m in t.get("top_movers", [])][:5],
        })
    out.sort(key=lambda x: (x.get("mid_heat") or 0), reverse=True)
    return out


def regime_snapshot(thematic):
    mood = _load_json(MOOD) or {}
    snap = (thematic or {}).get("regime_snapshot", {}) if thematic else {}
    m = mood.get("mood", {})
    vix = mood.get("vix", {})
    fg = mood.get("fear_greed", {})
    return {
        "mood_score": m.get("score"),
        "mood_label": m.get("label"),
        "vix": vix.get("current"),
        "vix_regime": vix.get("regime"),
        "fear_greed": fg.get("index") if isinstance(fg, dict) else fg,
        "skew": (mood.get("skew") or {}).get("current"),
        "spy_close": snap.get("spy_close"),
        "spy_ma50_status": snap.get("spy_ma50_status"),
        "spy_rsi_14": snap.get("spy_rsi_14"),
        "real_rate_10y_estimate": snap.get("real_rate_10y_estimate"),
        "fred_regime_label": snap.get("fred_regime_label"),
        "yield_curve_inverted": snap.get("yield_curve_inverted"),
    }


# ── Committee verdict scraping from recent reports/<DATE>_<TICKER>.md ──
_RE_TICKER_FILE = re.compile(r"(\d{8})_([A-Z]{1,6})\.md$")
_PAT = {
    "final_score": re.compile(r"Final Score[^\d\-]*([\-\d.]+)\s*/\s*3"),
    "fair_value": re.compile(r"(?:Weighted Fair Value|加權合理價|合理股價)[^\d$]*\$?([\d,]+\.?\d*)"),
    "band": re.compile(r"Verdict Band[^a-zA-Z]*([a-z_]+)"),
    "decision_cap": re.compile(r"decision_cap_active\s*=\s*true|Decision Cap[^\n]*啟動"),
}


def committee_verdicts(universe, lookback_days=14, today=None):
    today = today or _dt.date.today()
    out = {}
    for path in glob.glob(os.path.join(REPORTS, "*.md")):
        m = _RE_TICKER_FILE.search(os.path.basename(path))
        if not m:
            continue
        d8, tk = m.group(1), m.group(2)
        if tk not in universe:
            continue
        try:
            fdate = _dt.datetime.strptime(d8, "%Y%m%d").date()
        except ValueError:
            continue
        if (today - fdate).days > lookback_days or fdate > today:
            continue
        try:
            txt = open(path, "r", encoding="utf-8").read()
        except Exception:
            continue
        rec = {"date": fdate.isoformat(), "report": os.path.basename(path)}
        fs = _PAT["final_score"].search(txt)
        if fs:
            rec["final_score"] = float(fs.group(1))
        fv = _PAT["fair_value"].search(txt)
        if fv:
            rec["fair_value"] = float(fv.group(1).replace(",", ""))
        bd = _PAT["band"].search(txt)
        if bd:
            rec["verdict_band"] = bd.group(1)
        rec["decision_cap"] = bool(_PAT["decision_cap"].search(txt))
        # keep the most recent report per ticker
        if tk not in out or rec["date"] >= out[tk]["date"]:
            out[tk] = rec
    return out


def fetch_prices(universe):
    try:
        import yfinance as yf
    except Exception as e:
        sys.stderr.write(f"[build_pack] yfinance unavailable: {e}\n")
        return {}
    out = {}
    try:
        data = yf.download(list(universe), period="1mo", interval="1d",
                           progress=False, auto_adjust=True)
        close = data["Close"]
        for t in universe:
            try:
                s = close[t].dropna()
                if len(s) < 2:
                    continue
                last = float(s.iloc[-1])
                p5 = float(s.iloc[-6]) if len(s) > 6 else float(s.iloc[0])
                p20 = float(s.iloc[0])
                out[t] = {
                    "price": round(last, 2),
                    "mom_5d": round((last / p5 - 1) * 100, 1),
                    "mom_1mo": round((last / p20 - 1) * 100, 1),
                }
            except Exception:
                continue
    except Exception as e:
        sys.stderr.write(f"[build_pack] price fetch failed: {e}\n")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=_dt.date.today().isoformat())
    ap.add_argument("--no-fetch", action="store_true", help="skip yfinance price fetch")
    ap.add_argument("--universe", default="", help="comma-separated override")
    args = ap.parse_args()

    universe = ([u.strip().upper() for u in args.universe.split(",") if u.strip()]
                or DEFAULT_UNIVERSE)
    today = _dt.datetime.strptime(args.date, "%Y-%m-%d").date()

    thematic, thematic_file = latest_thematic()
    pack = {
        "as_of": args.date,
        "generated_by": "weekly-tech-playbook/build_pack.py",
        "universe": universe,
        "regime": regime_snapshot(thematic),
        "themes": themes_ranked(thematic),
        "thematic_source": thematic_file,
        "committee_verdicts": committee_verdicts(universe, today=today),
        "prices": {} if args.no_fetch else fetch_prices(universe),
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, f"pack_{args.date}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)
    blind_pack = {k: v for k, v in pack.items() if k != "committee_verdicts"}
    blind_pack["generated_by"] = "weekly-tech-playbook/build_pack.py (committee-blind)"
    blind_pack["review_constraint"] = "Do not read pack_<DATE>.json, selections, or committee reports before completing the blind pass."
    blind_path = os.path.join(DATA_DIR, f"blind_pack_{args.date}.json")
    with open(blind_path, "w", encoding="utf-8") as f:
        json.dump(blind_pack, f, ensure_ascii=False, indent=2)

    # human summary
    r = pack["regime"]
    print(f"\n=== Weekly Tech Playbook · data pack {args.date} ===")
    print(f"Regime: mood={r.get('mood_label')} ({r.get('mood_score')})  "
          f"VIX={r.get('vix')} {r.get('vix_regime')}  F&G={r.get('fear_greed')}  "
          f"real_rate={r.get('real_rate_10y_estimate')}  FRED={r.get('fred_regime_label')}")
    print(f"\nHot themes (top 8, from {thematic_file}):")
    for t in pack["themes"][:8]:
        print(f"  {str(t['mid_heat']):>5} {t['heat_label'] or '':5} {t['lifecycle'] or '':11} "
              f"{t['direction'] or '':8} | {t['name'][:34]:34} | {t['movers']}")
    print(f"\nCommittee verdicts (last 14d, {len(pack['committee_verdicts'])} tickers):")
    for tk, v in sorted(pack["committee_verdicts"].items()):
        print(f"  {tk:6} score={v.get('final_score')}  FV={v.get('fair_value')}  "
              f"band={v.get('verdict_band')}  cap={v.get('decision_cap')}  ({v['date']})")
    print(f"\nPrices: {len(pack['prices'])}/{len(universe)} fetched")
    print(f"\nWrote {out_path}")
    print(f"Wrote {blind_path}")
    print("Next: Codex completes blind review from blind_pack first; only then read full pack/selections and reconcile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

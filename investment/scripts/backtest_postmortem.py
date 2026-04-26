#!/usr/bin/env python3
"""
Backtest postmortem — scan investment protocol reports vs actual price action.

Goal: empirically test whether 4 proposed calibration changes are warranted by
historical data, or are n=1 extrapolations from the NTRS case.

Inputs:
  - reports/YYYYMMDD_TICKER.md (NEW format only — contains "## 決議摘要")
Outputs:
  - reports/POSTMORTEM_<run_date>.md

Usage:
  python3 investment/scripts/backtest_postmortem.py
  python3 investment/scripts/backtest_postmortem.py --reports-dir /tmp/reports
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("ERROR: pip install yfinance pandas", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_REPORTS = ROOT / "reports"

# ----------------- regex parsers -----------------

DEC_RE = re.compile(r"\|\s*\*?\*?Final Decision\*?\*?\s*\|\s*\*?\*?(BUY|HOLD|SELL|STAGED_ENTRY)\*?\*?\s*\|", re.I)
# Fallback: extract decision from RESULT row when summary table missing/non-standard
RESULT_DEC_RE = re.compile(
    r"\|\s*[A-Z]*\s*\|\s*\*?\*?(BUY|HOLD|SELL|STAGED_ENTRY)\*?\*?\s*\|\s*[+-]?\d+\.?\d*\s*\|",
    re.I
)
SCORE_RE = re.compile(r"\|\s*\*?\*?Final Score\*?\*?\s*\|\s*([+-]?\d+\.?\d*)\s*\|", re.I)
POS_RE = re.compile(r"\|\s*\*?\*?Position Size\*?\*?\s*\|\s*([\d.]+)%", re.I)
RR_RE = re.compile(r"\|\s*\*?\*?Risk/Reward\*?\*?\s*\|\s*([\d.]+)", re.I)
ACTION_RE = re.compile(r"\|\s*\*?\*?Action\*?\*?\s*\|\s*\*?\*?(EXECUTE|CANCEL|SKIP|STAGED|WAIT|MONITOR)\*?\*?", re.I)

# per-lane in Visualization Table — "| Fundamentals | BUY | 2.5 | 0.78 | ..."
LANE_RE = re.compile(
    r"\|\s*(Fundamentals|Sentiment|News|Technical)\s*\|\s*(BUY|HOLD|SELL|STAGED_ENTRY)\s*\|\s*([+-]?\d+\.?\d*)\s*\|\s*([\d.]+)\s*\|",
    re.I
)
# Red Team — "| Red Team (V4.8) | STRONG_COUNTER | 4/5 | ..." or "| Red Team | ... | strength 4 | ..."
RT_RE = re.compile(
    r"\|\s*Red Team[^|]*\|\s*([A-Z_]+)\s*\|\s*(?:strength\s*)?(\d)(?:/5)?\s*\|",
    re.I
)
# Burry — "| Contrarian (Burry) | — | 60.8/100 VALUE_BONUS | ..."
BURRY_RE = re.compile(
    r"\|\s*(?:Contrarian\s*\()?Burry\)?\s*\|\s*[—\-]?\s*\|\s*([\d.]+)\s*/?\s*100",
    re.I
)
# RESULT row — "| | BUY | 1.721 | ×0.85 | ×0.9 | 1.463 | ..."
RESULT_RE = re.compile(
    r"\|\s*(?:RESULT)?\s*\|\s*(BUY|HOLD|SELL|STAGED_ENTRY)\s*\|\s*([+-]?\d+\.?\d*)\s*\|\s*[×x]([\d.]+)\s*\|\s*[×x]([\d.]+)\s*\|\s*([+-]?\d+\.?\d*)\s*\|",
    re.I
)

# Stop loss / take profit — variations
SL_RE = re.compile(r"Stop Loss\s*\|\s*\$?([\d.]+)", re.I)
TP_RE = re.compile(r"Take Profit\s*\|\s*\$?([\d.]+)", re.I)
# Entry ranges — "**進場區間**：$160 – $165" or "進場區間: $160 - $165"
ENTRY_RANGE_RE = re.compile(r"進場區間\**\s*[:：]\s*\$?([\d.]+)\s*[–\-—~]\s*\$?([\d.]+)")

# Technical RSI — REQUIRES separator (|/:/：) to avoid grabbing "RSI 14" as the value.
# Matches: "RSI 14 | 98.08", "RSI(14): 98.08", "RSI | 39.5"
RSI_RE = re.compile(r"RSI\s*(?:14|\(14\))?\s*[|:：]\s*([\d.]+)", re.I)

# Phase 0 regime / warning text search
EARLY_WARN_RE = re.compile(r"Early[_\s]Warning", re.I)
CONFIRMED_TOP_RE = re.compile(r"Confirmed[_\s]Top", re.I)


def parse_report(path):
    """Parse a single NEW-format report. Return dict of extracted fields."""
    txt = path.read_text(errors="ignore")
    if "## 決議摘要" not in txt:
        return None
    m = re.match(r"(\d{8})_([A-Z]+)\.md", path.name)
    if not m:
        return None
    date_str, ticker = m.group(1), m.group(2)
    decision_date = dt.datetime.strptime(date_str, "%Y%m%d").date()

    out = {"ticker": ticker, "date": decision_date, "report_path": str(path)}

    def find1(rx, default=None, group=1):
        m = rx.search(txt)
        return m.group(group) if m else default

    out["decision"] = find1(DEC_RE) or find1(RESULT_DEC_RE)
    out["final_score"] = float(find1(SCORE_RE)) if find1(SCORE_RE) else None
    out["pos_pct"] = float(find1(POS_RE)) if find1(POS_RE) else None
    out["rr"] = float(find1(RR_RE)) if find1(RR_RE) else None
    out["action"] = find1(ACTION_RE)

    # Lanes
    lanes = {}
    for m in LANE_RE.finditer(txt):
        lanes[m.group(1).capitalize()] = {
            "signal": m.group(2).upper(),
            "score": float(m.group(3)),
            "confidence": float(m.group(4)),
        }
    out["lanes"] = lanes

    # Red Team
    rt_m = RT_RE.search(txt)
    if rt_m:
        out["rt_label"] = rt_m.group(1).upper()
        out["rt_strength"] = int(rt_m.group(2))
    else:
        out["rt_label"] = None
        out["rt_strength"] = None

    # Burry
    burry_m = BURRY_RE.search(txt)
    out["burry_score"] = float(burry_m.group(1)) if burry_m else None

    # RESULT row (gives RT gate × macro × → final)
    result_m = RESULT_RE.search(txt)
    if result_m:
        out["raw_score"] = float(result_m.group(2))
        out["rt_gate"] = float(result_m.group(3))
        out["macro_mult"] = float(result_m.group(4))
        # 5th group is final, redundant with SCORE_RE
    else:
        out["raw_score"] = None
        out["rt_gate"] = None
        out["macro_mult"] = None

    # SL / TP
    sl_m = SL_RE.search(txt)
    tp_m = TP_RE.search(txt)
    out["sl"] = float(sl_m.group(1)) if sl_m else None
    out["tp"] = float(tp_m.group(1)) if tp_m else None

    # Entry ranges (first two occurrences = aggressive, conservative)
    ranges = ENTRY_RANGE_RE.findall(txt)
    if len(ranges) >= 1:
        out["aggr_low"], out["aggr_high"] = sorted([float(ranges[0][0]), float(ranges[0][1])])
    else:
        out["aggr_low"] = out["aggr_high"] = None
    if len(ranges) >= 2:
        out["cons_low"], out["cons_high"] = sorted([float(ranges[1][0]), float(ranges[1][1])])
    else:
        out["cons_low"] = out["cons_high"] = None

    # Technical RSI
    rsi_m = RSI_RE.search(txt)
    out["tech_rsi"] = float(rsi_m.group(1)) if rsi_m else None

    # Phase 0 warnings
    out["early_warning"] = bool(EARLY_WARN_RE.search(txt))
    out["confirmed_top"] = bool(CONFIRMED_TOP_RE.search(txt))

    return out


# ----------------- price fetching -----------------

def fetch_prices(ticker, start_date, n_days=30):
    """Fetch trading days from start_date through today (max n_days)."""
    end = min(dt.date.today() + dt.timedelta(days=1),
              start_date + dt.timedelta(days=n_days * 2))  # buffer for weekends
    try:
        h = yf.Ticker(ticker).history(start=start_date.isoformat(),
                                      end=end.isoformat(), auto_adjust=False)
        if h.empty:
            return None
        h.index = h.index.tz_localize(None) if h.index.tz else h.index
        return h
    except Exception as e:
        print(f"WARN: yfinance {ticker} failed: {e}", file=sys.stderr)
        return None


def compute_outcome(parsed, prices, window_days=20):
    """Compute realized outcomes for a parsed report using actual price action."""
    out = {}
    if prices is None or prices.empty:
        return {"outcome_available": False}

    # Find decision-day row (first trading day >= decision_date)
    dd = pd.Timestamp(parsed["date"])
    forward = prices[prices.index >= dd]
    if forward.empty:
        return {"outcome_available": False}
    decision_close = float(forward["Close"].iloc[0])
    out["decision_close"] = decision_close

    # Look at next N trading days (excluding decision day itself)
    after = forward.iloc[1:window_days + 1]
    if after.empty:
        return {"outcome_available": False, "decision_close": decision_close}
    out["outcome_available"] = True
    out["days_observed"] = len(after)

    # Aggressive fill check
    aggr_filled, aggr_fill_price = False, None
    if parsed["aggr_low"] is not None:
        in_range = after[(after["Low"] <= parsed["aggr_high"]) & (after["High"] >= parsed["aggr_low"])]
        if not in_range.empty:
            aggr_filled = True
            # Approximate fill: midpoint or aggr_high (LIMIT BUY at upper edge)
            first_touch = in_range.iloc[0]
            aggr_fill_price = min(parsed["aggr_high"], float(first_touch["High"]))
    out["aggr_filled"] = aggr_filled
    out["aggr_fill_price"] = aggr_fill_price

    # Conservative fill check
    cons_filled, cons_fill_price = False, None
    if parsed["cons_low"] is not None:
        in_range = after[(after["Low"] <= parsed["cons_high"]) & (after["High"] >= parsed["cons_low"])]
        if not in_range.empty:
            cons_filled = True
            first_touch = in_range.iloc[0]
            cons_fill_price = min(parsed["cons_high"], float(first_touch["High"]))
    out["cons_filled"] = cons_filled
    out["cons_fill_price"] = cons_fill_price

    # SL / TP touches
    out["sl_hit"] = bool(parsed["sl"] and (after["Low"] <= parsed["sl"]).any())
    out["tp_hit"] = bool(parsed["tp"] and (after["High"] >= parsed["tp"]).any())

    # Latest observed return (always available)
    out["ret_so_far"] = (float(after["Close"].iloc[-1]) / decision_close - 1) * 100
    # Strict 5/10/20 day returns — None if window not yet elapsed
    for k, n in [("ret_5d", 5), ("ret_10d", 10), ("ret_20d", 20)]:
        out[k] = (float(after["Close"].iloc[n - 1]) / decision_close - 1) * 100 if len(after) >= n else None
    out["max_close_pct"] = (float(after["Close"].max()) / decision_close - 1) * 100
    out["min_close_pct"] = (float(after["Close"].min()) / decision_close - 1) * 100

    # P/L if aggressive filled (using min of close window vs fill)
    if aggr_filled and aggr_fill_price:
        out["aggr_pnl_close_now"] = (float(after["Close"].iloc[-1]) / aggr_fill_price - 1) * 100
        out["aggr_pnl_max_dd"] = (float(after["Low"].min()) / aggr_fill_price - 1) * 100
        out["aggr_pnl_max_up"] = (float(after["High"].max()) / aggr_fill_price - 1) * 100

    return out


# ----------------- aggregation / cross-tabs -----------------

def make_xtab(rows, group_fn, group_label, metric_keys):
    """Generic cross-tab: bucket rows by group_fn, average metric_keys per bucket."""
    buckets = {}
    for r in rows:
        if not r.get("outcome_available"):
            continue
        g = group_fn(r)
        if g is None:
            continue
        buckets.setdefault(g, []).append(r)
    lines = [f"### Cross-tab by {group_label}", "",
             "| Bucket | N | " + " | ".join(metric_keys) + " |",
             "|---|---:|" + "|".join([":---:"] * len(metric_keys)) + "|"]
    for g in sorted(buckets.keys(), key=lambda x: (str(type(x)), x)):
        rs = buckets[g]
        cells = [f"`{g}`", str(len(rs))]
        for k in metric_keys:
            vals = [r[k] for r in rs if r.get(k) is not None]
            if vals:
                cells.append(f"{sum(vals)/len(vals):+.2f}%")
            else:
                cells.append("—")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def render_report(parsed_rows, run_date):
    """Build the postmortem markdown report."""
    rows = parsed_rows
    n_total = len(rows)
    n_outcome = sum(1 for r in rows if r.get("outcome_available"))

    n_have_5d = sum(1 for r in rows if r.get("ret_5d") is not None)
    n_have_10d = sum(1 for r in rows if r.get("ret_10d") is not None)
    n_have_20d = sum(1 for r in rows if r.get("ret_20d") is not None)
    out = [f"# Postmortem Backtest — {run_date}", "",
           f"**Reports parsed**: {n_total} (NEW format only)",
           f"**With price outcome**: {n_outcome}",
           f"**Window coverage**: {n_have_5d}/{n_outcome} have ≥5d, {n_have_10d}/{n_outcome} have ≥10d, {n_have_20d}/{n_outcome} have ≥20d",
           "",
           "> ⚠️ **Most reports have <5 trading days elapsed.** Treat `ret_so_far` (current return) as the primary metric. `ret_5d`/`ret_10d`/`ret_20d` cells show '—' when window not yet elapsed.",
           "",
           "**Method**: For each report, fetch yfinance prices from decision_date forward up to 20 trading days. "
           "Compute aggressive/conservative fill, SL/TP touches, 5/10/20-day close returns from decision-day close.",
           "",
           "**Limits**: Reports newer than ~20 trading days have partial windows. "
           "Outcomes use unadjusted close prices; intraday slippage and transaction costs not modeled.",
           "",
           "---",
           "",
           "## 1. Overall scoring vs realized outcomes",
           ""]

    # Decision vs ret_10d
    out.append(make_xtab(rows, lambda r: r["decision"], "Final Decision",
                         ["ret_so_far", "ret_5d", "ret_10d", "min_close_pct", "max_close_pct"]))

    out.append("---\n\n## 2. Red Team strength validation\n")
    out.append("**Question**: Does Red Team strength 4-5 actually predict bad outcomes?\n")
    out.append(make_xtab(rows, lambda r: r["rt_strength"], "Red Team strength (0-5)",
                         ["ret_so_far", "ret_5d", "ret_10d", "min_close_pct"]))

    out.append("---\n\n## 3. Technical RSI extreme validation\n")
    out.append("**Question**: Does RSI > 90/95 + breakout actually predict mean reversion?\n")
    def rsi_bucket(r):
        v = r.get("tech_rsi")
        if v is None: return None
        if v >= 95: return ">=95_extreme"
        if v >= 90: return "90-95_overbought"
        if v >= 70: return "70-90_strong"
        if v >= 50: return "50-70_neutral_up"
        if v >= 30: return "30-50_neutral_dn"
        return "<30_oversold"
    out.append(make_xtab(rows, rsi_bucket, "Technical RSI bucket",
                         ["ret_so_far", "ret_5d", "ret_10d", "min_close_pct"]))

    out.append("---\n\n## 4. Phase 0 Early_Warning validation\n")
    out.append("**Question**: Does Early_Warning regime actually need a stronger macro multiplier cap?\n")
    out.append(make_xtab(rows, lambda r: "Early_Warning" if r["early_warning"] else "Other",
                         "Phase 0 warning flag", ["ret_5d", "ret_10d", "ret_20d", "min_close_pct"]))

    out.append("---\n\n## 5. News BUY +4 + RSI > 90 co-occurrence\n")
    out.append("**Question**: Does the 'sell-the-news' pattern empirically show up?\n")
    def co_pattern(r):
        n = r["lanes"].get("News")
        rsi = r.get("tech_rsi")
        if not n or rsi is None: return None
        if n["score"] >= 3 and rsi >= 90: return "News>=3 AND RSI>=90"
        if n["score"] >= 3: return "News>=3 only"
        if rsi >= 90: return "RSI>=90 only"
        return "neither"
    out.append(make_xtab(rows, co_pattern, "News+RSI pattern",
                         ["ret_so_far", "ret_5d", "ret_10d", "min_close_pct"]))

    out.append("---\n\n## 6. Aggressive entry fill statistics\n")
    out.append("**Question**: Did aggressive LIMIT entries actually fill, and how did they perform?\n")
    aggr_rows = [r for r in rows if r.get("outcome_available") and r.get("aggr_filled")]
    out.append(f"\n**Filled aggressive entries**: {len(aggr_rows)} / {n_outcome}\n")
    out.append(make_xtab(aggr_rows, lambda r: r["decision"], "Final Decision (aggr-filled only)",
                         ["aggr_pnl_close_now", "aggr_pnl_max_dd", "aggr_pnl_max_up"]))

    out.append("---\n\n## 7. SL / TP hit rates\n")
    sl_hits = sum(1 for r in rows if r.get("sl_hit"))
    tp_hits = sum(1 for r in rows if r.get("tp_hit"))
    out.append(f"\n| Metric | Count | % of with-outcome |\n|---|---:|---:|\n"
               f"| SL hit | {sl_hits} | {sl_hits/n_outcome*100:.1f}% |\n"
               f"| TP hit | {tp_hits} | {tp_hits/n_outcome*100:.1f}% |\n")

    out.append("---\n\n## 8. Score-to-outcome correlation (additive analysis)\n")
    out.append("**Question**: Do model scores actually predict ret_so_far? Pearson r close to 0 = noise.\n")

    def pearson(xs, ys):
        if len(xs) < 3:
            return None, len(xs)
        mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
        num = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
        dx = sum((x-mx)**2 for x in xs) ** 0.5
        dy = sum((y-my)**2 for y in ys) ** 0.5
        if dx == 0 or dy == 0:
            return None, len(xs)
        return num / (dx * dy), len(xs)

    def lane_score(r, lane):
        d = r["lanes"].get(lane)
        return d["score"] if d else None

    sources = [
        ("final_score", lambda r: r.get("final_score")),
        ("raw_score", lambda r: r.get("raw_score")),
        ("Fundamentals", lambda r: lane_score(r, "Fundamentals")),
        ("Sentiment", lambda r: lane_score(r, "Sentiment")),
        ("News", lambda r: lane_score(r, "News")),
        ("Technical", lambda r: lane_score(r, "Technical")),
        ("Burry score", lambda r: r.get("burry_score")),
        ("RT strength (inverted: -x)", lambda r: -r.get("rt_strength") if r.get("rt_strength") is not None else None),
    ]
    out.append("| Source | Pearson r vs ret_so_far | N |")
    out.append("|---|---:|---:|")
    rows_with_ret = [r for r in rows if r.get("ret_so_far") is not None]
    for name, fn in sources:
        pairs = [(fn(r), r["ret_so_far"]) for r in rows_with_ret if fn(r) is not None]
        if not pairs:
            out.append(f"| {name} | — | 0 |")
            continue
        xs, ys = zip(*pairs)
        r_val, n = pearson(list(xs), list(ys))
        rstr = f"{r_val:+.3f}" if r_val is not None else "—"
        out.append(f"| {name} | {rstr} | {n} |")
    out.append("")
    out.append("> Interpret: |r| > 0.3 = some signal; |r| < 0.15 = noise. Negative = predictor inversely correlated.\n")

    # Outlier-stripped means
    out.append("\n### Outlier-robust BUY vs HOLD comparison\n")
    by_dec = {}
    for r in rows_with_ret:
        d = r.get("decision")
        if d:
            by_dec.setdefault(d, []).append(r["ret_so_far"])
    out.append("| Decision | N | Mean | Mean (drop top1+bot1) | Median |")
    out.append("|---|---:|---:|---:|---:|")
    for d, vs in sorted(by_dec.items()):
        srt = sorted(vs)
        mean = sum(vs) / len(vs)
        if len(vs) >= 4:
            trimmed = srt[1:-1]
            t_mean = sum(trimmed) / len(trimmed)
            t_str = f"{t_mean:+.2f}%"
        else:
            t_str = "—"
        med = srt[len(srt)//2] if len(srt) % 2 else (srt[len(srt)//2 - 1] + srt[len(srt)//2]) / 2
        out.append(f"| {d} | {len(vs)} | {mean:+.2f}% | {t_str} | {med:+.2f}% |")
    out.append("")

    out.append("---\n\n## 9. Per-report detail\n")
    out.append("\n| Date | Ticker | Decision | Score | RT | Tech RSI | EarlyWarn | 10d Ret | Aggr filled | Aggr P/L now |\n"
               "|---|---|---|---:|---:|---:|:---:|---:|:---:|---:|")
    for r in sorted(rows, key=lambda x: (x["date"], x["ticker"])):
        if not r.get("outcome_available"):
            continue
        rt = f"{r['rt_strength']}/5" if r.get("rt_strength") is not None else "—"
        rsi = f"{r['tech_rsi']:.0f}" if r.get("tech_rsi") else "—"
        ew = "Y" if r["early_warning"] else "n"
        ret10 = f"{r['ret_10d']:+.1f}%" if r.get("ret_10d") is not None else "—"
        af = "Y" if r.get("aggr_filled") else "n"
        ap = f"{r['aggr_pnl_close_now']:+.1f}%" if r.get("aggr_pnl_close_now") is not None else "—"
        dec = r['decision'] or "—"
        fs = f"{r['final_score']:+.2f}" if r.get('final_score') is not None else "—"
        out.append(f"| {r['date']} | {r['ticker']} | {dec} | "
                   f"{fs} | {rt} | {rsi} | {ew} | {ret10} | {af} | {ap} |")
    out.append("")

    return "\n".join(out)


# ----------------- main -----------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--reports-dir", default=str(DEFAULT_REPORTS))
    ap.add_argument("--output", default=None,
                    help="Override default reports/POSTMORTEM_<date>.md")
    ap.add_argument("--window", type=int, default=20,
                    help="Trading-day window for outcome computation (default 20)")
    args = ap.parse_args()

    rdir = Path(args.reports_dir)
    paths = sorted(rdir.glob("2026[01]*_*.md"))
    paths = [p for p in paths if re.match(r"\d{8}_[A-Z]+\.md", p.name)]
    print(f"Scanning {len(paths)} ticker-report files...", file=sys.stderr)

    rows = []
    for p in paths:
        parsed = parse_report(p)
        if not parsed:
            continue
        prices = fetch_prices(parsed["ticker"], parsed["date"], n_days=args.window + 14)
        outcome = compute_outcome(parsed, prices, window_days=args.window)
        parsed.update(outcome)
        rows.append(parsed)
        print(f"  {parsed['date']} {parsed['ticker']}: "
              f"{parsed.get('decision', '?')} score={parsed.get('final_score')} "
              f"ret10d={parsed.get('ret_10d')}", file=sys.stderr)

    run_date = dt.date.today().isoformat()
    report_md = render_report(rows, run_date)
    out_path = Path(args.output) if args.output else rdir / f"POSTMORTEM_{run_date}.md"
    out_path.write_text(report_md)
    print(f"\nWrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

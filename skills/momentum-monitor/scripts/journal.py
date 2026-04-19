#!/usr/bin/env python3
"""
momentum-monitor — forward-return journal.

Records every momentum-screen hit with entry price, then fills in 5/20/60 day
forward returns + MAE/MFE over time. After a few weeks you have real
signal-quality data (win rate by signal, return distribution by score bin).

Subcommands
-----------
  snapshot  <csv_path>   Append each row of a screen CSV to journal.jsonl
  update                 Fetch delayed forward returns for pending entries
  stats                  Aggregate → stats.json (by_signal / by_score_bin / by_stage)

Examples
--------
  python3 journal.py snapshot ../cache/screen_20260418_1430.csv
  python3 journal.py update
  python3 journal.py stats
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

import pandas as pd
import yfinance as yf

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
JOURNAL_DIR  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "journal"))
JOURNAL_FILE = os.path.join(JOURNAL_DIR, "journal.jsonl")
STATS_FILE   = os.path.join(JOURNAL_DIR, "stats.json")

HORIZONS = [5, 20, 60]  # trading days
MAE_MFE_HORIZON = 20    # compute max adverse/favorable excursion over 20d


# ── IO helpers ───────────────────────────────────────────────────────────
def _ensure_dir():
    os.makedirs(JOURNAL_DIR, exist_ok=True)


def _load_journal():
    _ensure_dir()
    if not os.path.exists(JOURNAL_FILE):
        return []
    entries = []
    with open(JOURNAL_FILE, "r", encoding="utf-8") as fp:
        for ln in fp:
            ln = ln.strip()
            if not ln:
                continue
            try:
                entries.append(json.loads(ln))
            except json.JSONDecodeError as e:
                print(f"[journal] skipping malformed line: {e}", file=sys.stderr)
    return entries


def _write_journal(entries):
    _ensure_dir()
    tmp = JOURNAL_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fp:
        for e in entries:
            fp.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(tmp, JOURNAL_FILE)


def _entry_key(e):
    return (e["snap_id"], e["ticker"])


# ── snapshot ─────────────────────────────────────────────────────────────
def _snap_id_from_path(csv_path):
    base = os.path.basename(csv_path)
    name, _ = os.path.splitext(base)
    return name  # e.g. screen_20260418_1430


def _snap_date_from_id(snap_id):
    # snap_id form: screen_YYYYMMDD_HHMM
    parts = snap_id.split("_")
    if len(parts) >= 2 and len(parts[1]) == 8:
        return f"{parts[1][:4]}-{parts[1][4:6]}-{parts[1][6:8]}"
    return str(date.today())


def _parse_signals(csv_cell):
    if not csv_cell:
        return []
    return [s for s in csv_cell.split("|") if s]


def _float_or_none(x):
    if x == "" or x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def cmd_snapshot(csv_path):
    if not os.path.exists(csv_path):
        raise SystemExit(f"CSV not found: {csv_path}")

    snap_id = _snap_id_from_path(csv_path)
    snap_date = _snap_date_from_id(snap_id)
    snap_ts = datetime.now().isoformat(timespec="seconds")

    existing = _load_journal()
    existing_keys = {_entry_key(e) for e in existing}

    added = 0
    skipped = 0
    with open(csv_path, "r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            ticker = (row.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            key = (snap_id, ticker)
            if key in existing_keys:
                skipped += 1
                continue
            entry = {
                "snap_id": snap_id,
                "snap_date": snap_date,
                "snap_timestamp": snap_ts,
                "ticker": ticker,
                "entry_price": _float_or_none(row.get("price")),
                "score": _float_or_none(row.get("score")),
                "label": row.get("label"),
                "stage": row.get("stage"),
                "ratio_20d": _float_or_none(row.get("ratio_20d")),
                "above_ma200_pct": _float_or_none(row.get("above_ma200_pct")),
                "rsi_14":   _float_or_none(row.get("rsi_14")),
                "rsi_zone": row.get("rsi_zone") or None,
                "signals": _parse_signals(row.get("signals", "")),
                "warnings": _parse_signals(row.get("warnings", "")),
                "returns": {f"{h}d": {"value": None, "filled_date": None} for h in HORIZONS},
                "mae_20d": None,
                "mfe_20d": None,
                "updated_at": snap_ts,
            }
            existing.append(entry)
            existing_keys.add(key)
            added += 1

    _write_journal(existing)
    print(f"[journal] snapshot: +{added} added, {skipped} duplicate "
          f"({snap_id}, total={len(existing)})")


# ── update (fill forward returns) ────────────────────────────────────────
def _business_days_ahead(start_date, n):
    """Return the calendar date n US business days after start_date."""
    return (pd.Timestamp(start_date) + pd.tseries.offsets.BDay(n)).date()


def _entries_needing_update(entries, today):
    """Group pending returns by ticker, return dict {ticker: [(entry, horizon), ...]}."""
    todo = defaultdict(list)
    for e in entries:
        snap_d = date.fromisoformat(e["snap_date"])
        for h in HORIZONS:
            if e["returns"][f"{h}d"]["value"] is not None:
                continue
            target = _business_days_ahead(snap_d, h)
            if target <= today:
                todo[e["ticker"]].append((e, h))
        # MAE/MFE: fill once at 20d horizon
        if e["mae_20d"] is None:
            target = _business_days_ahead(snap_d, MAE_MFE_HORIZON)
            if target <= today:
                todo[e["ticker"]].append((e, "mae_mfe"))
    return todo


def _fetch_hist_for_ticker(ticker, start_date, end_date):
    """Fetch daily OHLC for ticker in [start_date, end_date] inclusive. Returns DF or None."""
    try:
        hist = yf.Ticker(ticker).history(
            start=start_date.isoformat(),
            end=(end_date + timedelta(days=3)).isoformat(),  # buffer
            auto_adjust=True,
        )
        if hist is None or hist.empty:
            return None
        return hist
    except Exception as e:
        print(f"[journal] fetch failed {ticker}: {e}", file=sys.stderr)
        return None


def _price_at_or_before(hist, target_date):
    """Return (close, index_date) on target_date or latest available trading day before it."""
    if hist is None or hist.empty:
        return None, None
    # Convert index to naive dates for comparison
    idx_dates = [d.date() for d in hist.index]
    closes = hist["Close"].tolist()
    match = None
    for dt, c in zip(idx_dates, closes):
        if dt <= target_date:
            match = (c, dt)
    return match if match else (None, None)


def cmd_update():
    entries = _load_journal()
    if not entries:
        print("[journal] empty journal — nothing to update")
        return

    today = date.today()
    todo = _entries_needing_update(entries, today)
    if not todo:
        print("[journal] all entries up to date")
        _update_snapshot_counts(entries)
        _write_journal(entries)
        return

    total_pending = sum(len(v) for v in todo.values())
    print(f"[journal] updating {total_pending} pending fills across {len(todo)} tickers…",
          file=sys.stderr)

    now_ts = datetime.now().isoformat(timespec="seconds")
    filled_count = 0
    failed_tickers = []

    for ticker, items in todo.items():
        # Widest range needed for this ticker
        min_snap = min(date.fromisoformat(it[0]["snap_date"]) for it in items)
        max_target = today + timedelta(days=1)
        hist = _fetch_hist_for_ticker(ticker, min_snap - timedelta(days=3), max_target)
        if hist is None:
            failed_tickers.append(ticker)
            continue

        for entry, kind in items:
            snap_d = date.fromisoformat(entry["snap_date"])
            entry_price = entry.get("entry_price")
            if not entry_price:
                continue
            if kind == "mae_mfe":
                target = _business_days_ahead(snap_d, MAE_MFE_HORIZON)
                window = hist[(hist.index.date > snap_d) & (hist.index.date <= target)]
                if window.empty:
                    continue
                low = float(window["Low"].min())
                high = float(window["High"].max())
                entry["mae_20d"] = round((low / entry_price - 1) * 100, 2)
                entry["mfe_20d"] = round((high / entry_price - 1) * 100, 2)
                entry["updated_at"] = now_ts
                filled_count += 1
            else:
                horizon = kind
                target = _business_days_ahead(snap_d, horizon)
                close, actual_date = _price_at_or_before(hist, target)
                if close is None:
                    continue
                ret_pct = round((close / entry_price - 1) * 100, 2)
                entry["returns"][f"{horizon}d"]["value"] = ret_pct
                entry["returns"][f"{horizon}d"]["filled_date"] = actual_date.isoformat()
                entry["updated_at"] = now_ts
                filled_count += 1

    _update_snapshot_counts(entries)
    _write_journal(entries)
    print(f"[journal] updated {filled_count} fills "
          f"({len(failed_tickers)} tickers failed: {failed_tickers[:5]}{'…' if len(failed_tickers) > 5 else ''})")


def _update_snapshot_counts(entries):
    # no-op placeholder for future hook; kept to centralize write-time housekeeping
    pass


# ── stats ────────────────────────────────────────────────────────────────
def _percentile(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = k - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _agg_group(values):
    """Aggregate a list of return % values to summary stats."""
    vals = [v for v in values if v is not None]
    if not vals:
        return {"n": 0}
    n = len(vals)
    wins = sum(1 for v in vals if v > 0)
    s = sorted(vals)
    return {
        "n": n,
        "win_rate": round(wins / n, 3),
        "mean":     round(sum(vals) / n, 2),
        "median":   round(_percentile(s, 0.5), 2),
        "p25":      round(_percentile(s, 0.25), 2),
        "p75":      round(_percentile(s, 0.75), 2),
        "min":      round(min(vals), 2),
        "max":      round(max(vals), 2),
    }


def _score_bin(score):
    if score is None:
        return "unknown"
    if score >= 90: return "90-100"
    if score >= 80: return "80-90"
    if score >= 70: return "70-80"
    if score >= 60: return "60-70"
    if score >= 50: return "50-60"
    return "<50"


def cmd_stats():
    entries = _load_journal()
    if not entries:
        print("[journal] empty journal — nothing to aggregate")
        return

    now_ts = datetime.now().isoformat(timespec="seconds")

    # Buckets keyed by group → {horizon → [returns]}
    by_signal = defaultdict(lambda: defaultdict(list))
    by_score_bin = defaultdict(lambda: defaultdict(list))
    by_stage = defaultdict(lambda: defaultdict(list))
    mae_by_signal = defaultdict(list)
    mfe_by_signal = defaultdict(list)

    for e in entries:
        bin_key = _score_bin(e.get("score"))
        stage = e.get("stage") or "unknown"
        for h in HORIZONS:
            v = e["returns"].get(f"{h}d", {}).get("value")
            if v is None:
                continue
            by_score_bin[bin_key][f"{h}d"].append(v)
            by_stage[stage][f"{h}d"].append(v)
            for sig in e.get("signals", []):
                by_signal[sig][f"{h}d"].append(v)
        if e.get("mae_20d") is not None:
            for sig in e.get("signals", []):
                mae_by_signal[sig].append(e["mae_20d"])
                mfe_by_signal[sig].append(e["mfe_20d"])

    def _summarize(bucket):
        out = {}
        for grp, by_h in bucket.items():
            out[grp] = {h: _agg_group(vals) for h, vals in by_h.items()}
        return out

    stats = {
        "generated_at": now_ts,
        "total_entries": len(entries),
        "date_range": {
            "earliest": min((e["snap_date"] for e in entries), default=None),
            "latest":   max((e["snap_date"] for e in entries), default=None),
        },
        "fill_counts": {
            f"{h}d": sum(1 for e in entries if e["returns"].get(f"{h}d", {}).get("value") is not None)
            for h in HORIZONS
        },
        "by_signal":    _summarize(by_signal),
        "by_score_bin": _summarize(by_score_bin),
        "by_stage":     _summarize(by_stage),
        "mae_mfe_by_signal": {
            sig: {
                "n": len(mae_by_signal[sig]),
                "mae_20d_mean":   round(sum(mae_by_signal[sig]) / len(mae_by_signal[sig]), 2),
                "mfe_20d_mean":   round(sum(mfe_by_signal[sig]) / len(mfe_by_signal[sig]), 2),
                "mae_20d_median": round(sorted(mae_by_signal[sig])[len(mae_by_signal[sig]) // 2], 2),
                "mfe_20d_median": round(sorted(mfe_by_signal[sig])[len(mfe_by_signal[sig]) // 2], 2),
            }
            for sig in mae_by_signal
        },
    }

    _ensure_dir()
    with open(STATS_FILE, "w", encoding="utf-8") as fp:
        json.dump(stats, fp, ensure_ascii=False, indent=2)

    # Print a compact MD summary for terminal
    print(f"## Journal Stats — {now_ts}")
    print(f"- Entries: **{stats['total_entries']}** "
          f"({stats['date_range']['earliest']} → {stats['date_range']['latest']})")
    print(f"- Filled: 5d={stats['fill_counts']['5d']}  "
          f"20d={stats['fill_counts']['20d']}  "
          f"60d={stats['fill_counts']['60d']}")
    print()
    if stats["by_signal"]:
        print("### Top signals by 20d win rate (n≥5)")
        rows = []
        for sig, by_h in stats["by_signal"].items():
            d20 = by_h.get("20d", {})
            if d20.get("n", 0) >= 5:
                rows.append((sig, d20))
        rows.sort(key=lambda r: -r[1]["win_rate"])
        print("| Signal | n | Win% | Mean | Median | P25 | P75 |")
        print("|---|---|---|---|---|---|---|")
        for sig, d in rows[:15]:
            print(f"| {sig} | {d['n']} | {d['win_rate']*100:.1f}% | "
                  f"{d['mean']:+.2f} | {d['median']:+.2f} | "
                  f"{d['p25']:+.2f} | {d['p75']:+.2f} |")
    print(f"\n→ written {STATS_FILE}")


def cmd_clear(yes=False):
    """Delete journal.jsonl + stats.json. Used after schema changes or fresh start."""
    paths = [JOURNAL_FILE, STATS_FILE]
    existing = [p for p in paths if os.path.exists(p)]
    if not existing:
        print("[journal] nothing to clear")
        return
    sizes = {p: os.path.getsize(p) for p in existing}
    entries = 0
    if JOURNAL_FILE in existing:
        entries = sum(1 for _ in open(JOURNAL_FILE, "r", encoding="utf-8"))
    print(f"[journal] about to delete:")
    for p in existing:
        print(f"  - {p} ({sizes[p]} bytes)")
    if entries:
        print(f"[journal] {entries} journal entries will be lost")
    if not yes:
        resp = input("Type YES to confirm: ")
        if resp.strip() != "YES":
            print("[journal] aborted")
            return
    for p in existing:
        os.remove(p)
    print(f"[journal] removed {len(existing)} file(s)")


# ── main ─────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Forward-return journal for momentum screens")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("snapshot", help="Append a screen CSV to journal")
    s1.add_argument("csv_path")

    sub.add_parser("update", help="Fetch delayed forward returns")
    sub.add_parser("stats",  help="Aggregate → stats.json")
    sc = sub.add_parser("clear", help="Delete journal.jsonl + stats.json (confirm required)")
    sc.add_argument("--yes", action="store_true", help="Skip interactive confirmation")

    args = ap.parse_args()
    if args.cmd == "snapshot":
        cmd_snapshot(args.csv_path)
    elif args.cmd == "update":
        cmd_update()
    elif args.cmd == "stats":
        cmd_stats()
    elif args.cmd == "clear":
        cmd_clear(args.yes)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
kill_trigger_monitor — daily deterministic check of Red Team kill / overturn conditions.

Closes the committee loop: protocol writes `IF ... WITHIN ... THEN ...` conditions
(investment red_team_kill_conditions + sector _phase4b risk_scenario) but nothing
re-checked them after decision day. This script re-checks every active condition
daily, 0 LLM:

  - Parseable predicates (price/MA/volume/VIX/SPY-RSI/breadth) are evaluated
    against live data → status `triggered` / `armed`.
  - Unparseable conditions (earnings guides, geopolitics, insider flow …) are
    surfaced as `manual` with a window countdown so a human eyeballs them.
  - Window elapsed without trigger → `expired` (thesis survives that challenge).

Sources:
  - investment/invest_logs/history.json  → trades_this_session[].red_team_kill_conditions
  - sector/sector_logs/<latest>_sector_intel.json → _phase4b.challenge_targets[].risk_scenario

Output: Dashboard/kill_triggers.json (static-served; index.html renders red banner
when any `triggered`). Exploration/monitor layer — does NOT modify history.json,
sector_intel, or any protocol decision artifact.

CLI:
  python3 scripts/kill_trigger_monitor.py             # write Dashboard/kill_triggers.json
  python3 scripts/kill_trigger_monitor.py --dry-run   # print, no write
"""
import argparse
import glob
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from skills._shared.technical_core import fetch_history, rsi_14  # noqa: E402

HISTORY_PATH = ROOT / "investment" / "invest_logs" / "history.json"
SECTOR_LOGS = ROOT / "sector" / "sector_logs"
BREADTH_DIR = ROOT / "sector" / "breadth_cache"
FRED_CACHE = ROOT / "skills" / "fred-macro" / "cache" / "fred_latest.json"
OUT_PATH = ROOT / "Dashboard" / "kill_triggers.json"

STANDING_DAYS = 90       # conditions with no parseable window stay active this long
LOOKBACK_DAYS = 90       # ignore decisions older than this
TRADING_TO_CALENDAR = 1.45


# ── condition window parsing ────────────────────────────────────────────

def parse_window(text, origin):
    """Return (expires: date|None, window_label: str|None)."""
    m = re.search(r"WITHIN\s+(\d{4}-\d{2}-\d{2})", text)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date(), m.group(1)
        except ValueError:
            pass
    m = re.search(r"WITHIN\s+(\d+)\s*(?:個)?\s*(trading\s*days?|交易日)", text, re.I)
    if m:
        n = int(m.group(1))
        return origin + timedelta(days=round(n * TRADING_TO_CALENDAR)), f"{n} trading days"
    m = re.search(r"WITHIN\s+(\d+)\s*(?:d\b|days?|天|日)", text, re.I)
    if m:
        n = int(m.group(1))
        return origin + timedelta(days=n), f"{n} days"
    m = re.search(r"(\d+)\s*(?:個)?交易日內", text)
    if m:
        n = int(m.group(1))
        return origin + timedelta(days=round(n * TRADING_TO_CALENDAR)), f"{n} trading days"
    m = re.search(r"(\d+)\s*天內", text)
    if m:
        n = int(m.group(1))
        return origin + timedelta(days=n), f"{n} days"
    return None, None


# ── market data (lazy, memoized per run) ────────────────────────────────

class MarketData:
    def __init__(self):
        self._hist = {}

    def hist(self, ticker):
        if ticker not in self._hist:
            try:
                h, _ = fetch_history(ticker, period="1y")
                self._hist[ticker] = h
            except Exception as e:
                print(f"[kill-trigger] WARN: history {ticker}: {e}", file=sys.stderr)
                self._hist[ticker] = None
        return self._hist[ticker]

    def close(self, ticker):
        h = self.hist(ticker)
        return float(h["Close"].iloc[-1]) if h is not None and len(h) else None

    def ma(self, ticker, n):
        h = self.hist(ticker)
        if h is None or len(h) < n:
            return None
        return float(h["Close"].rolling(n).mean().iloc[-1])

    def vol_ratio_20d(self, ticker):
        h = self.hist(ticker)
        if h is None or len(h) < 21:
            return None
        avg20 = float(h["Volume"].iloc[-21:-1].mean())
        return float(h["Volume"].iloc[-1]) / avg20 if avg20 > 0 else None

    def vix(self):
        return self.close("^VIX")

    def spy_rsi(self):
        h = self.hist("SPY")
        if h is None or len(h) < 15:
            return None
        v = rsi_14(h["Close"]).iloc[-1]
        return float(v) if v == v else None

    def breadth(self):
        files = sorted(glob.glob(str(BREADTH_DIR / "market_breadth_*.json")), key=os.path.getmtime)
        if not files:
            return None, None
        try:
            d = json.load(open(files[-1]))
            return float(d.get("composite_score")), d.get("data_date")
        except Exception:
            return None, None

    def real_rate(self):
        """FRED DFII10 (10Y real rate) from fred-macro cache. Returns (value, date)."""
        try:
            d = json.load(open(FRED_CACHE))
            s = (d.get("series") or {}).get("DFII10") or {}
            return (float(s["value"]), s.get("date")) if s.get("value") is not None else (None, None)
        except Exception:
            return None, None


def _cmp(op, lhs, rhs):
    return {"<": lhs < rhs, "<=": lhs <= rhs, ">": lhs > rhs, ">=": lhs >= rhs}[op]


# ── predicate extraction ────────────────────────────────────────────────
# Returns list of check dicts for one clause, or [] when nothing recognized.

def extract_checks(clause, ticker, md):
    # normalize unicode operators so one regex family covers ≥/≤/×
    clause = clause.replace("≥", ">=").replace("≤", "<=").replace("×", "x")
    checks = []

    def add(name, value, met):
        checks.append({"predicate": name, "value": value, "met": bool(met)})

    # 10Y real rate: "real_rate_dfii10 維持 >=2.08" / "DFII10 突破 2.20"
    for m in re.finditer(r"(?:real[_ ]?rate\w*|DFII10)\s*(?:10Y real rate)?[^<>≥≤\d]{0,8}([<>]=?|突破|跌破)\s*(\d+\.?\d*)", clause, re.I):
        rr, rr_date = md.real_rate()
        if rr is not None:
            op = {"突破": ">", "跌破": "<"}.get(m.group(1), m.group(1))
            add(f"DFII10 {op} {m.group(2)} (data {rr_date})", rr, _cmp(op, rr, float(m.group(2))))

    # VIX <15 / VIX > 25 (單日 qualifier treated as current-level check)
    for m in re.finditer(r"VIX\s*(?:單日)?\s*([<>]=?)\s*(\d+\.?\d*)", clause):
        v = md.vix()
        if v is not None:
            add(f"VIX {m.group(1)} {m.group(2)}", round(v, 1), _cmp(m.group(1), v, float(m.group(2))))

    # breadth >50 (market breadth composite 0-100)
    for m in re.finditer(r"breadth\s*([<>]=?)\s*(\d+\.?\d*)", clause, re.I):
        b, b_date = md.breadth()
        if b is not None:
            add(f"breadth {m.group(1)} {m.group(2)} (data {b_date})", b, _cmp(m.group(1), b, float(m.group(2))))

    # SPY RSI_14 < 70
    for m in re.finditer(r"(?:SPY\s+)?RSI[_ ]?14\s*([<>]=?)\s*(\d+\.?\d*)", clause):
        r = md.spy_rsi()
        if r is not None:
            add(f"SPY RSI_14 {m.group(1)} {m.group(2)}", round(r, 1), _cmp(m.group(1), r, float(m.group(2))))

    # close/收盤 vs dollar level: "close >$452.43" / "收盤 < $226.72"
    if ticker:
        for m in re.finditer(r"(?:close|收盤)\s*([<>]=?)\s*\$?\s*(\d+\.?\d*)", clause, re.I):
            c = md.close(ticker)
            if c is not None:
                add(f"{ticker} close {m.group(1)} {m.group(2)}", round(c, 2), _cmp(m.group(1), c, float(m.group(2))))

        # 跌破 MA20/$X  (close below level or MA)
        for m in re.finditer(r"跌破\s*MA\s*(\d+)", clause):
            c, mav = md.close(ticker), md.ma(ticker, int(m.group(1)))
            if c is not None and mav is not None:
                add(f"{ticker} close < MA{m.group(1)} ({round(mav, 2)})", round(c, 2), c < mav)
        for m in re.finditer(r"跌破\s*\$?\s*(\d+\.?\d*)", clause):
            if "MA" in m.group(0):
                continue
            c = md.close(ticker)
            if c is not None:
                add(f"{ticker} close < {m.group(1)}", round(c, 2), c < float(m.group(1)))

        # 收盤 < MA50 / close < MA200  (also "200MA" digit-first form)
        for m in re.finditer(r"(?:close|收盤)\s*([<>]=?)\s*(?:MA\s*(\d+)|(\d+)\s*MA)", clause, re.I):
            n = int(m.group(2) or m.group(3))
            c, mav = md.close(ticker), md.ma(ticker, n)
            if c is not None and mav is not None:
                add(f"{ticker} close {m.group(1)} MA{n} ({round(mav, 2)})", round(c, 2),
                    _cmp(m.group(1), c, mav))
        # holds MA200 / 收復 / 站上 / 站回(並守住) 200MA
        for m in re.finditer(r"(?:holds|收復|站上|站回(?:並守住)?|守住)\s*(?:MA\s*(\d+)|(\d+)\s*MA)", clause, re.I):
            n = int(m.group(1) or m.group(2))
            c, mav = md.close(ticker), md.ma(ticker, n)
            if c is not None and mav is not None:
                add(f"{ticker} close > MA{n} ({round(mav, 2)})", round(c, 2), c > mav)

        # volume ratio: ">1.3x vol" / "量 >= 1.3x 20D avg" / "1.5× 20D avg"
        for m in re.finditer(r"([<>]=?)?\s*(\d+\.?\d*)\s*[x×]\s*(?:vol\b|20D avg|20日)", clause, re.I):
            vr = md.vol_ratio_20d(ticker)
            if vr is not None:
                op = m.group(1) or ">="
                add(f"{ticker} vol {op} {m.group(2)}x 20D avg", round(vr, 2), _cmp(op, vr, float(m.group(2))))

    return checks


def evaluate_condition(text, ticker, md):
    """Split on AND/且 (OR/或 → manual if mixed). Returns (status_hint, checks, met, deadline).
    status_hint: 'evaluable' only when EVERY clause produced >=1 check.
    deadline=True for negated wait-out conditions ("未能站回 X WITHIN N THEN fail") —
    those can only be confirmed at window expiry, never mid-window."""
    body = text
    m = re.search(r"\bIF\b(.*?)\bTHEN\b", text, re.S)
    if m:
        body = m.group(1)

    has_or = bool(re.search(r"\bOR\b|或", body))
    deadline = bool(re.search(r"未能|無法|fails?\s+to", body))
    clauses = re.split(r"\bAND\b|且", body)
    all_checks, clause_met, evaluable = [], [], True
    for cl in clauses:
        checks = extract_checks(cl, ticker, md)
        all_checks.extend(checks)
        if not checks:
            evaluable = False
        else:
            clause_met.append(all(c["met"] for c in checks))

    if has_or:
        # mixed OR semantics — only auto-evaluate the trivial all-parseable single-clause case
        evaluable = False

    met = evaluable and bool(clause_met) and all(clause_met)
    if deadline:
        met = not met  # condition fires when the positive predicate was NOT achieved
    return ("evaluable" if evaluable else "partial" if all_checks else "manual"), all_checks, met, deadline


# ── collectors ──────────────────────────────────────────────────────────

def collect_thesis_conditions(today):
    items = []
    try:
        hist = json.load(open(HISTORY_PATH))
    except Exception as e:
        print(f"[kill-trigger] WARN: history.json: {e}", file=sys.stderr)
        return items
    cutoff = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    latest_by_ticker = {}
    for e in hist:
        d = e.get("date") or ""
        if d < cutoff:
            continue
        for tr in e.get("trades_this_session") or []:
            t = (tr.get("ticker") or e.get("ticker") or "").upper()
            if t:
                latest_by_ticker[t] = (d, tr)
    for t, (d, tr) in sorted(latest_by_ticker.items()):
        for i, cond in enumerate(tr.get("red_team_kill_conditions") or []):
            items.append({
                "id": f"thesis_{t}_{d}_{i}",
                "source": "thesis",
                "ticker": t,
                "sector": None,
                "origin_date": d,
                "decision": tr.get("final_decision"),
                "condition": cond,
            })
    return items


def collect_sector_conditions():
    files = sorted(glob.glob(str(SECTOR_LOGS / "*_sector_intel.json")))
    if not files:
        return []
    path = files[-1]
    origin = os.path.basename(path)[:10]
    try:
        d = json.load(open(path))
    except Exception as e:
        print(f"[kill-trigger] WARN: sector_intel: {e}", file=sys.stderr)
        return []
    items = []
    p4b = d.get("_phase4b") or {}
    for i, c in enumerate(p4b.get("challenge_targets") or []):
        rs = c.get("risk_scenario") or ""
        if not rs:
            continue
        items.append({
            "id": f"sector_{c.get('challenged_sector', '?')}_{origin}_{i}",
            "source": "sector_da",
            "ticker": None,
            "sector": c.get("challenged_sector"),
            "origin_date": origin,
            "decision": c.get("challenged_call"),
            "condition": rs,
            "confidence": c.get("confidence_level"),
            "accepted": bool(c.get("accepted")),
        })
    return items


# ── main ────────────────────────────────────────────────────────────────

def run(dry_run=False):
    today = date.today()
    md = MarketData()
    raw = collect_thesis_conditions(today) + collect_sector_conditions()

    items = []
    for it in raw:
        origin = datetime.strptime(it["origin_date"], "%Y-%m-%d").date()
        expires, window_label = parse_window(it["condition"], origin)
        if expires is None:
            expires = origin + timedelta(days=STANDING_DAYS)
            window_label = f"standing ({STANDING_DAYS}d cap)"
        days_left = (expires - today).days

        if days_left < -7:
            # long past window — skip market fetches, archive only
            status, checks = "expired", []
        else:
            hint, checks, met, deadline = evaluate_condition(it["condition"], it.get("ticker"), md)
            if days_left < 0:
                # just past expiry (≤7d grace): deadline-style conditions confirm NOW
                status = "triggered" if (deadline and hint == "evaluable" and met) else "expired"
            elif hint == "evaluable":
                # deadline conditions can't fire mid-window — they wait out the clock
                status = "armed" if deadline else ("triggered" if met else "armed")
            else:
                status = "manual"
        items.append({**it, "window": window_label, "expires": expires.isoformat(),
                      "days_left": days_left, "status": status, "checks": checks})

    active = [i for i in items if i["status"] != "expired"]
    summary = {s: sum(1 for i in items if i["status"] == s)
               for s in ("triggered", "armed", "manual", "expired")}
    payload = {
        "as_of": datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        # active first (triggered → soonest expiry), expired tail kept for audit
        "items": sorted(active, key=lambda i: (i["status"] != "triggered", i["days_left"]))
                 + [i for i in items if i["status"] == "expired"],
    }

    print(f"[kill-trigger] {len(items)} conditions | triggered={summary['triggered']} "
          f"armed={summary['armed']} manual={summary['manual']} expired={summary['expired']}",
          file=sys.stderr)
    for i in payload["items"]:
        if i["status"] == "triggered":
            print(f"  🔴 TRIGGERED [{i.get('ticker') or i.get('sector')}] {i['condition'][:110]}", file=sys.stderr)

    if dry_run:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"[kill-trigger] wrote {OUT_PATH.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print JSON, don't write")
    args = ap.parse_args()
    sys.exit(run(dry_run=args.dry_run))

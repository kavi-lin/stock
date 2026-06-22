#!/usr/bin/env python3
"""
review.py — Weekly Tech Playbook · 檢討機制 (deterministic compute, 0 LLM)

Scores a PAST week's playbook against actual prices at a review date, so the
next-week LLM review has hard numbers to reason over (it does NOT pick or re-score):

  per-pick     : entry → now return %, kill-trigger fired?
  per-basket   : weighted return % (by weight_usd/100k), $ value now, hit rate, vs SPY alpha
  cross-basket : 保險 vs 激進 vs 混合 ranking

Output:
  reports/<ASOF>_TECH_PLAYBOOK_REVIEW.md   — numbers + an empty "LLM 檢討" section to fill
  Dashboard/playbook_review.json           — surfaced on /playbook.html

The LLM review step (Step 5 of SKILL.md) reads the MD, fills the qualitative verdict
(which basket won + why, what to adjust), and may revise next week's selections.

Usage:
  python3 review.py --playbook data/playbook_2026-06-22.json            # review vs today
  python3 review.py --playbook data/playbook_2026-06-22.json --asof 2026-06-27
  python3 review.py --date 2026-06-22 --asof 2026-06-27                 # resolve snapshot by date
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
REVIEW_JSON = os.path.join(ROOT, "Dashboard", "playbook_review.json")
BENCH = "SPY"
CASH_LABELS = {"現金", "現金／短債", "現金/短債", "cash", "cash/t-bills"}

# kill triggers are free text like "跌破 $195" / "跌破 $475 (-12%)" / "站不回 $238".
# Best-effort: extract the first dollar threshold and flag if now-price breaches it.
_KILL_PRICE = re.compile(r"\$?\s*([0-9][0-9,]*\.?[0-9]*)")
_KILL_BELOW = ("跌破", "站不回", "below", "<")


def _fmt_pct(x):
    return f"{'+' if x >= 0 else ''}{x:.1f}%"


def load_playbook(args):
    if args.playbook:
        path = args.playbook
    else:
        if not args.date:
            sys.exit("need --playbook or --date")
        path = os.path.join(DATA_DIR, f"playbook_{args.date}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), path


def all_tickers(pb):
    s = set()
    for b in pb.get("baskets", {}).values():
        for p in b.get("picks", []):
            s.add(p["ticker"])
    for p in (pb.get("codex_review") or {}).get("recommended_allocation", []):
        if p.get("ticker", "").lower() not in {x.lower() for x in CASH_LABELS}:
            s.add(p["ticker"])
    s.add(BENCH)
    return sorted(s)


def fetch_asof_prices(tickers, asof):
    """Return {ticker: close at/just-before asof}. yfinance daily."""
    try:
        import yfinance as yf
    except Exception as e:
        sys.stderr.write(f"[review] yfinance unavailable: {e}\n")
        return {}
    end = _dt.datetime.strptime(asof, "%Y-%m-%d").date() + _dt.timedelta(days=1)
    start = _dt.datetime.strptime(asof, "%Y-%m-%d").date() - _dt.timedelta(days=10)
    out = {}
    try:
        data = yf.download(tickers, start=start.isoformat(), end=end.isoformat(),
                           interval="1d", progress=False, auto_adjust=True)
        close = data["Close"]
        for t in tickers:
            try:
                s = close[t].dropna()
                if len(s):
                    out[t] = round(float(s.iloc[-1]), 2)
            except Exception:
                continue
    except Exception as e:
        sys.stderr.write(f"[review] price fetch failed: {e}\n")
    return out


def kill_fired(kill_text, entry, now):
    if not kill_text or now is None:
        return False
    m = _KILL_PRICE.search(kill_text)
    if not m:
        return False
    try:
        thr = float(m.group(1).replace(",", ""))
    except ValueError:
        return False
    # only treat as a downside breach trigger
    if any(k in kill_text for k in _KILL_BELOW):
        return now < thr
    return False


def review_basket(b, prices):
    capital = 0
    val_now = 0.0
    rows = []
    up = 0
    for p in b.get("picks", []):
        entry = p.get("price")
        now = prices.get(p["ticker"])
        w = p.get("weight_usd", 0)
        capital += w
        ret = None
        if entry and now:
            ret = (now / entry - 1) * 100
            val_now += w * (now / entry)
            if ret >= 0:
                up += 1
        else:
            val_now += w  # missing price → hold flat, no credit/penalty
        rows.append({
            "ticker": p["ticker"], "tier": p.get("tier"), "theme": p.get("theme"),
            "weight_usd": w, "entry": entry, "now": now,
            "return_pct": round(ret, 1) if ret is not None else None,
            "weight_pct": p.get("weight_pct"),
            "kill": p.get("kill"),
            "kill_fired": kill_fired(p.get("kill"), entry, now),
        })
    n = len(rows)
    basket_ret = (val_now / capital - 1) * 100 if capital else 0.0
    return {
        "label_zh": b.get("label_zh"), "label_en": b.get("label_en"),
        "capital": capital, "value_now": round(val_now, 2),
        "return_pct": round(basket_ret, 2),
        "hit_rate": round(up / n * 100, 1) if n else 0.0,
        "n": n, "kills_fired": [r["ticker"] for r in rows if r["kill_fired"]],
        "rows": rows,
    }


def review_codex_allocation(pb, prices):
    """Score the Codex alternative allocation, treating cash as a 0% return sleeve."""
    review = pb.get("codex_review") or {}
    allocation = review.get("recommended_allocation", [])
    if not allocation:
        return None

    pick_by_ticker = {}
    for basket in pb.get("baskets", {}).values():
        for pick in basket.get("picks", []):
            pick_by_ticker.setdefault(pick["ticker"], pick)

    capital = pb.get("capital_per_basket", 100000)
    value_now = 0.0
    rows = []
    up = 0
    investable = 0
    for item in allocation:
        ticker = item.get("ticker", "")
        weight_pct = item.get("weight_pct", 0)
        weight_usd = capital * weight_pct / 100
        is_cash = ticker.lower() in {x.lower() for x in CASH_LABELS}
        source_pick = pick_by_ticker.get(ticker, {})
        entry = None if is_cash else source_pick.get("price")
        now = None if is_cash else prices.get(ticker)
        ret = 0.0 if is_cash else None
        if entry and now:
            ret = (now / entry - 1) * 100
            value_now += weight_usd * (now / entry)
            investable += 1
            if ret >= 0:
                up += 1
        else:
            value_now += weight_usd
            if not is_cash:
                investable += 1
        rows.append({
            "ticker": ticker, "tier": "codex", "theme": item.get("role"),
            "weight_usd": round(weight_usd, 2), "weight_pct": weight_pct,
            "entry": entry, "now": now, "return_pct": round(ret, 1) if ret is not None else None,
            "kill": source_pick.get("kill"),
            "kill_fired": kill_fired(source_pick.get("kill"), entry, now),
            "is_cash": is_cash,
        })

    portfolio_ret = (value_now / capital - 1) * 100 if capital else 0.0
    cash_pct = round(sum(r["weight_pct"] for r in rows if r["is_cash"]), 1)
    return {
        "label_zh": "Codex替代", "label_en": "Codex Review",
        "capital": capital, "value_now": round(value_now, 2),
        "return_pct": round(portfolio_ret, 2),
        "hit_rate": round(up / investable * 100, 1) if investable else 0.0,
        "n": investable, "kills_fired": [r["ticker"] for r in rows if r["kill_fired"]],
        # this sleeve holds cash, so its alpha vs SPY is NOT a same-beta comparison.
        "deployed_pct": round(100 - cash_pct, 1), "cash_pct": cash_pct,
        "rows": rows, "is_codex_review": True,
    }


def render_md(rv):
    L = []
    L.append(f"# 投資方案檢討 — {rv['entry_date']} 方案 @ {rv['asof']} 收盤\n")
    L.append(f"> **進場日**: {rv['entry_date']}  |  **檢討日**: {rv['asof']}  |  "
             f"**基準**: {BENCH} {_fmt_pct(rv['bench_return_pct'])}  |  "
             f"**產出**: weekly-tech-playbook · review.py (0 LLM 計算)\n")

    L.append("## 籃子排名（依超額報酬 alpha）\n")
    L.append("| 名次 | 籃子 | 報酬 | vs SPY (alpha) | 命中率 | 觸發 Kill |")
    L.append("|---|---|---|---|---|---|")
    for i, b in enumerate(rv["ranking"], 1):
        kills = ", ".join(b["kills_fired"]) or "—"
        L.append(f"| {i} | {b['label_zh']} | {_fmt_pct(b['return_pct'])} "
                 f"| {_fmt_pct(b['return_pct'] - rv['bench_return_pct'])} "
                 f"| {b['hit_rate']:.0f}% ({sum(1 for r in b['rows'] if (r['return_pct'] or 0) >= 0)}/{b['n']}) | {kills} |")

    for b in rv["baskets"].values():
        L.append(f"\n---\n\n## {b['label_zh']}籃子 — {_fmt_pct(b['return_pct'])} "
                 f"(${b['value_now']:,.0f} / ${b['capital']:,.0f})\n")
        L.append("| 檔 | 配重 | 進場 | 現價 | 報酬 | Kill 觸發 |")
        L.append("|---|---|---|---|---|---|")
        for r in sorted(b["rows"], key=lambda x: (x["return_pct"] is None, -(x["return_pct"] or 0))):
            ret = _fmt_pct(r["return_pct"]) if r["return_pct"] is not None else "n/a"
            fired = "🔴 是" if r["kill_fired"] else "—"
            L.append(f"| {r['ticker']} | ${r['weight_usd']:,} | {r['entry']} | {r['now'] or 'n/a'} "
                     f"| {ret} | {fired} |")

    if rv.get("codex_result"):
        b = rv["codex_result"]
        L.append(f"\n---\n\n## Codex Review 替代配置 — {_fmt_pct(b['return_pct'])} "
                 f"(${b['value_now']:,.0f} / ${b['capital']:,.0f})\n")
        L.append(f"> 部署 {b.get('deployed_pct', 100):.0f}% / 現金 {b.get('cash_pct', 0):.0f}% "
                 f"— 含現金 sleeve,與滿倉三籃的 alpha **非同 beta 比較**。\n")
        L.append("| 標的 | 配重 | 進場 | 現價 | 報酬 | Kill 觸發 |")
        L.append("|---|---|---|---|---|---|")
        for r in sorted(b["rows"], key=lambda x: (x["is_cash"], x["return_pct"] is None, -(x["return_pct"] or 0))):
            ret = _fmt_pct(r["return_pct"]) if r["return_pct"] is not None else "n/a"
            fired = "🔴 是" if r["kill_fired"] else "—"
            L.append(f"| {r['ticker']} | {r['weight_pct']}% | {r['entry'] or '—'} | {r['now'] or '—'} | {ret} | {fired} |")

    L.append("\n---\n\n## 🧠 LLM 檢討（待填）\n")
    L.append("> 下週 LLM 讀上方硬數據後填寫。建議涵蓋：\n")
    L.append("1. **哪個籃子贏 + 為什麼**（題材對了還是配重對了？保險的抗跌 vs 激進的爆發力誰兌現）")
    L.append("2. **觸發 Kill 的標的**該認賠還是論點仍成立")
    L.append("3. **最大貢獻 / 最大拖累**個股，及當初理由是否被市場驗證")
    L.append("4. **催化兌現檢查**（Core PCE / Fed 壓力測試等事件實際走向 vs 預期）")
    L.append("5. **下週調整建議**（題材輪動？配重級距？要不要把過熱輕倉名單換掉）\n")
    L.append("_本檔為前瞻探索層檢討，不回寫 investment_protocol。調整僅作用於下週 selections。_\n")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--playbook", help="path to a dated playbook snapshot (data/playbook_<DATE>.json)")
    ap.add_argument("--date", help="entry date — resolve snapshot data/playbook_<DATE>.json")
    ap.add_argument("--asof", default=_dt.date.today().isoformat(), help="review date (default today)")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    pb, path = load_playbook(args)
    entry_date = pb.get("as_of")
    tickers = all_tickers(pb)
    prices = fetch_asof_prices(tickers, args.asof)
    if not prices:
        print("FATAL: no prices fetched (need yfinance + network). rc=1")
        return 1

    # benchmark return needs SPY entry price at entry_date — fetch it
    spy_entry = fetch_asof_prices([BENCH], entry_date).get(BENCH)
    spy_now = prices.get(BENCH)
    bench_ret = ((spy_now / spy_entry) - 1) * 100 if (spy_entry and spy_now) else 0.0

    baskets = {k: review_basket(b, prices) for k, b in pb.get("baskets", {}).items()}
    codex_result = review_codex_allocation(pb, prices)
    ranked = list(baskets.values()) + ([codex_result] if codex_result else [])
    ranking = sorted(ranked, key=lambda b: b["return_pct"] - bench_ret, reverse=True)

    rv = {
        "entry_date": entry_date, "asof": args.asof,
        "bench": BENCH, "bench_return_pct": round(bench_ret, 2),
        "bench_entry": spy_entry, "bench_now": spy_now,
        "baskets": baskets, "codex_result": codex_result, "ranking": ranking,
        "source_snapshot": os.path.basename(path),
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
    }

    print(f"=== Playbook review {entry_date} @ {args.asof} ===")
    print(f"  {BENCH} {_fmt_pct(bench_ret)}")
    for b in rv["ranking"]:
        depl = f"  部署 {b['deployed_pct']:.0f}%" if b.get("deployed_pct") is not None else ""
        print(f"  {b['label_zh']:8} {_fmt_pct(b['return_pct']):>7}  "
              f"alpha {_fmt_pct(b['return_pct'] - bench_ret):>7}  "
              f"hit {b['hit_rate']:.0f}%{depl}  kills={b['kills_fired'] or '—'}")

    if args.no_write:
        print("\n--no-write: skipped outputs")
        return 0

    with open(REVIEW_JSON, "w", encoding="utf-8") as f:
        json.dump(rv, f, ensure_ascii=False, indent=2)
    md_path = os.path.join(REPORTS, f"{args.asof}_TECH_PLAYBOOK_REVIEW.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_md(rv))
    print(f"\nWrote {REVIEW_JSON}")
    print(f"Wrote {md_path}")
    print("Next: LLM reads the MD → fills 「🧠 LLM 檢討」 section → revises next-week selections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

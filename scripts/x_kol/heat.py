#!/usr/bin/env python3
"""Theme heat + a human-gated promotion queue, over the X KOL shadow log.

    python3 scripts/x_kol/heat.py                    # heat table + pending queue
    python3 scripts/x_kol/heat.py --with-prices      # same, enriched from FMP
    python3 scripts/x_kol/heat.py --promote AAOI     # mark "I want 分析 AAOI"
    python3 scripts/x_kol/heat.py --reject TSM       # never ask me about this again
    python3 scripts/x_kol/heat.py --queue            # what I approved, not yet run

WHAT THIS IS. A thermometer for "which cluster has crowd attention right now",
not a stock picker. Grounded on 2026-08-06 data: every name Serenity discussed
outran the market hard over 5 days (AEVA +65.3%, AAOI +45.8%, RKLB +21.1%,
VIAV +16.4%, JBL +12.7% vs SPY +3.7%), and they all sit in one chain (CPO /
optical). Counting cashtags alone recovers that cluster — no LLM needed.

WHAT IT IS NOT. An entry signal. The posts are concurrent-to-lagging on the
individual name: AAOI had already run +22.73% on 08-03 before the 08-06 post, and
the AEVA post opens by *reporting* a +18.26% after-hours move. Theme persistence
is the usable part; the single-name move is usually gone.

PRIMARY vs SECONDARY. The first cashtag in a post is treated as what the post is
about; later ones are supporting mentions at a reduced weight. Validated on the
pronunciation joke — subject $AAOI +45.8% over 5d while the props $TSM/$AMD did
+4.8%/+1.4%. Secondary is weighted down, never dropped: $SIVE only ever appeared
as a secondary and is the actual supply-chain link in that cluster. This is a
deterministic heuristic standing in for a classifier; an LLM pass would do it
better and belongs exactly here (see `classify_hook` in the docstring below).

THEMES are co-mention clusters (connected components over "appeared in the same
post"), not a hardcoded sector map — the whole point is to discover the grouping
the crowd is actually trading, not the one GICS thinks exists.

DISCIPLINE. Exploration layer. Nothing here feeds investment_protocol. Promotion
to `分析 [TICKER]` is a **manual** decision recorded by `--promote`; this script
never launches an analysis and never writes to Dashboard/*.json.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.x_kol import budget as budget_mod  # noqa: E402

DECISIONS = ("pending", "promoted", "rejected", "analyzed")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def load_records(log_path: Path) -> list[dict]:
    out = []
    try:
        with open(log_path, encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return []
    return out


def score_tickers(records: list[dict], heat_cfg: dict, *, now: datetime | None = None) -> dict:
    """Recency-decayed attention score per ticker.

    Weight per mention = position_weight * 0.5 ** (age_days / half_life). A post
    from a week ago should not read as current heat, but it should not vanish
    either — a theme that keeps getting re-mentioned is exactly the durable case.
    """
    now = now or datetime.now(timezone.utc)
    half_life = float(heat_cfg.get("half_life_days", 3.0)) or 3.0
    w_primary = float(heat_cfg.get("primary_weight", 1.0))
    w_secondary = float(heat_cfg.get("secondary_weight", 0.4))

    stats: dict[str, dict] = {}
    for rec in records:
        tags = rec.get("cashtags") or []
        if not tags:
            continue
        created = _parse_ts(rec.get("created_at")) or now
        age_days = max(0.0, (now - created).total_seconds() / 86400.0)
        decay = 0.5 ** (age_days / half_life)
        for idx, sym in enumerate(tags):
            weight = (w_primary if idx == 0 else w_secondary) * decay
            slot = stats.setdefault(sym, {
                "ticker": sym, "score": 0.0, "mentions": 0, "primary_mentions": 0,
                "first_seen": None, "last_seen": None, "handles": set(), "posts": [],
            })
            slot["score"] += weight
            slot["mentions"] += 1
            if idx == 0:
                slot["primary_mentions"] += 1
            iso = rec.get("created_at") or ""
            if not slot["first_seen"] or iso < slot["first_seen"]:
                slot["first_seen"] = iso
            if not slot["last_seen"] or iso > slot["last_seen"]:
                slot["last_seen"] = iso
            slot["handles"].add(rec.get("handle") or "?")
            slot["posts"].append({"post_id": rec.get("post_id"), "url": rec.get("url"),
                                  "created_at": iso, "primary": idx == 0})
    for slot in stats.values():
        slot["score"] = round(slot["score"], 4)
        slot["handles"] = sorted(slot["handles"])
    return stats


def cluster_themes(records: list[dict], stats: dict) -> list[dict]:
    """Connected components over co-mention. Tickers that keep showing up in the
    same posts are, empirically, the cluster the crowd is trading together."""
    parent: dict[str, str] = {t: t for t in stats}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for rec in records:
        tags = [t for t in (rec.get("cashtags") or []) if t in parent]
        for other in tags[1:]:
            union(tags[0], other)

    groups: dict[str, list[str]] = {}
    for ticker in stats:
        groups.setdefault(find(ticker), []).append(ticker)

    themes = []
    for members in groups.values():
        members = sorted(members, key=lambda t: -stats[t]["score"])
        themes.append({
            "members": members,
            "score": round(sum(stats[t]["score"] for t in members), 4),
            "lead": members[0],
            "size": len(members),
        })
    return sorted(themes, key=lambda t: -t["score"])


# ── candidate queue (durable human decisions) ────────────────────────────
def load_candidates(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as fp:
            return json.load(fp)
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "tickers": {}}


def save_candidates(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2, sort_keys=True)
        fp.write("\n")
    os.replace(tmp, path)


def refresh_candidates(stats: dict, path: Path, *, surface_min: float) -> dict:
    """Add newly-surfaced tickers as `pending`. NEVER overwrites a decision that
    was already made — the point of the queue is that you are asked once."""
    data = load_candidates(path)
    tickers = data.setdefault("tickers", {})
    for sym, slot in stats.items():
        if slot["score"] < surface_min and sym not in tickers:
            continue
        entry = tickers.get(sym)
        if entry is None:
            tickers[sym] = {
                "decision": "pending",
                "first_seen": slot["first_seen"],
                "surfaced_at": _now_iso(),
                "decided_at": None,
                "note": None,
            }
        else:
            entry.setdefault("decision", "pending")
            entry["first_seen"] = entry.get("first_seen") or slot["first_seen"]
    data["updated_at"] = _now_iso()
    save_candidates(path, data)
    return data


def decide(path: Path, ticker: str, decision: str, *, note: str | None = None) -> dict:
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    ticker = ticker.upper().lstrip("$")
    data = load_candidates(path)
    entry = data.setdefault("tickers", {}).setdefault(
        ticker, {"decision": "pending", "first_seen": None, "surfaced_at": _now_iso()})
    entry["decision"] = decision
    entry["decided_at"] = _now_iso()
    if note:
        entry["note"] = note
    data["updated_at"] = _now_iso()
    save_candidates(path, data)
    return entry


# ── optional price context ───────────────────────────────────────────────
IDENTITY_CACHE_PATH = ROOT / "config/x_kol_symbol_identity.json"


def load_identity_cache(path: Path | None = None) -> dict:
    """Symbol identity is static — a listing's exchange and company do not change
    between page loads. Caching it permanently matters here because fmp_pool is a
    shared 220-calls/min window: the heatmap's 517-ticker fan-out routinely pins it
    at the cap (observed 2026-08-07), and identity was 2 of every 3 calls this
    module made. Cached symbols cost nothing and leave the window for prices."""
    try:
        with open(path or IDENTITY_CACHE_PATH, encoding="utf-8") as fp:
            return json.load(fp)
    except (OSError, json.JSONDecodeError):
        return {}


def save_identity_cache(cache: dict, path: Path | None = None) -> None:
    path = path or IDENTITY_CACHE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fp:
        json.dump(cache, fp, ensure_ascii=False, indent=2, sort_keys=True)
        fp.write("\n")
    os.replace(tmp, path)


def resolve_identity(tickers: list[str]) -> dict:
    """Flag cashtags whose bare symbol does not mean what the post meant.

    A cashtag is a string, not an identifier. Real case from 2026-08-06: Serenity
    discussed `$SIVE` as the CW DFB laser supplier in the CPO chain — that is
    Sivers Semiconductors AB, listed in Stockholm as SIVE.ST. The bare symbol
    `SIVE` resolves to Silver Verde May Mining, a $0.07 OTC shell with a $1.5M
    market cap. Promoting that to 分析 would have produced a confident report on
    entirely the wrong company.

    So: anything OTC/pink-sheet, sub-$50M, or with same-symbol listings on other
    exchanges gets flagged for a human look instead of being silently accepted.
    """
    cache = load_identity_cache()
    unknown = [s for s in tickers if s not in cache]
    if not unknown:
        return {s: cache[s] for s in tickers if cache.get(s)}

    try:
        from scripts._shared import fmp_pool
    except Exception:
        return {s: cache[s] for s in tickers if cache.get(s)}
    flags = {}
    for sym in unknown:
        note = None
        try:
            quote = fmp_pool.get("quote", {"symbol": sym})
        except Exception:
            continue
        row = quote[0] if isinstance(quote, list) and quote else None
        if not row:
            flags[sym] = {"flag": "unresolved", "note": "no quote for the bare symbol"}
            continue
        exchange = str(row.get("exchange") or "")
        cap = row.get("marketCap") or 0
        if exchange.upper() in ("OTC", "PNK", "OTCBB"):
            note = f"{exchange} listing, cap ${cap:,.0f}"
        elif cap and cap < 50_000_000:
            note = f"micro cap ${cap:,.0f}"
        try:
            matches = fmp_pool.get("search-symbol", {"query": sym, "limit": 5}) or []
        except Exception:
            matches = []
        # Only a genuine collision counts: the SAME base symbol carrying an
        # exchange suffix (SIVE vs SIVE.ST). Prefix matching flags JBLU for JBL
        # and AMDS for AMD, which is noise — and a warning that cries wolf is a
        # warning nobody reads on the day it matters.
        others = [m for m in matches if isinstance(m, dict)
                  and str(m.get("symbol", "")).upper() != sym.upper()
                  and str(m.get("symbol", "")).upper().split(".")[0] == sym.upper()]
        if others:
            alt = ", ".join(f"{m.get('symbol')} ({m.get('exchange')})" for m in others[:3])
            note = (note + "; " if note else "") + f"same-symbol elsewhere: {alt}"
        if note:
            flags[sym] = {"flag": "ambiguous", "note": note,
                          "resolves_to": row.get("name") or "?"}
            cache[sym] = flags[sym]
        else:
            cache[sym] = {}          # resolved clean — remember, never re-query
    save_identity_cache(cache)
    for sym in tickers:
        if cache.get(sym):
            flags[sym] = cache[sym]
    return flags


def price_backend_status() -> str | None:
    """Why the price backend is unusable right now, or None when it is fine.

    Split out so `mark_unanalyzable` can tell two opposite things apart. Both
    arrive as "this symbol is missing from `prices`":

      * FMP was asked and has no series for it   → a fact about the TICKER
      * FMP was never asked                      → a fact about this MACHINE

    Real case, 2026-08-16: Homebrew upgraded the default `python3` to 3.14 with
    an empty site-packages, so `import requests` (via fmp_pool) raised, this
    function's caller returned `{}`, and the page reported "no price series in
    FMP" for every symbol including NVDA and AMZN. FMP was fine; nothing had
    called it. An error message that names the wrong subsystem sends you to
    debug the wrong thing.
    """
    try:
        from scripts._shared import fmp_pool  # noqa: F401
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    return None


def fetch_price_context(tickers: list[str]) -> dict:
    """5d / 1m / YTD move per ticker, so a promote/reject call is informed rather
    than a guess. Degrades to {} — heat must still print if FMP is unavailable."""
    try:
        from scripts._shared import fmp_pool
    except Exception:
        return {}
    out = {}
    year_start = f"{datetime.now(timezone.utc).year - 1}-12-31"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for sym in tickers:
        try:
            rows = fmp_pool.get("historical-price-eod/full",
                                {"symbol": sym, "from": year_start, "to": today})
        except Exception:
            continue
        if not isinstance(rows, list) or len(rows) < 6:
            continue
        rows = sorted(rows, key=lambda x: x.get("date") or "")
        closes = [r["close"] for r in rows if r.get("close")]
        if len(closes) < 6:
            continue

        def pct(n):
            return round((closes[-1] / closes[-1 - n] - 1) * 100, 1) if len(closes) > n else None

        out[sym] = {"last": closes[-1], "d5": pct(5), "d21": pct(21),
                    "ytd": round((closes[-1] / closes[0] - 1) * 100, 1)}
    return out


def mark_unanalyzable(stats: dict, prices: dict, identity: dict) -> dict:
    """Tickers the analysis stack physically cannot process.

    `分析 [TICKER]` takes every number from FMP scripts by protocol — no hand
    calculation — so a symbol with no price series cannot be analysed at all,
    however interesting the post was. Real case: $SIVE is Sivers Semiconductors
    AB; FMP carries its profile under SIVE.ST (STO, SEK, ~10.8B SEK cap) but
    serves no EOD or quote for it, and there is no US F-share (SIVEF does not
    exist). The bare `SIVE` that DOES price is an unrelated $0.07 OTC shell.

    Such a ticker still counts toward theme heat — it is evidence about the
    cluster — it just can never be promoted to a position-level analysis. Those
    are different jobs, which is exactly why they are separate stages here.
    """
    backend_error = price_backend_status()
    out = {}
    for sym in stats:
        if sym in prices:
            continue
        if backend_error:
            # Say what actually happened. Claiming FMP has no series for NVDA
            # is a false statement about the ticker, and it points whoever
            # reads it at the data vendor instead of at this machine.
            out[sym] = f"price backend unavailable on this host ({backend_error})"
            continue
        reason = "no price series in FMP"
        info = identity.get(sym) or {}
        if info.get("note"):
            reason += f" ({info['note']})"
        out[sym] = reason
    return out


def build(config: dict, *, log_path: Path | None = None, now: datetime | None = None,
          with_prices: bool = False) -> dict:
    heat_cfg = config.get("heat") or {}
    log_path = log_path or (ROOT / config["collect"]["shadow_log"])
    records = load_records(log_path)
    stats = score_tickers(records, heat_cfg, now=now)
    themes = cluster_themes(records, stats)
    prices = fetch_price_context(list(stats)) if with_prices else {}
    identity = resolve_identity(list(stats)) if with_prices else {}
    return {
        "generated_at": _now_iso(),
        "posts_scanned": len(records),
        "tickers": sorted(stats.values(), key=lambda s: -s["score"]),
        "themes": themes,
        "prices": prices,
        "identity_flags": identity,
        "unanalyzable": mark_unanalyzable(stats, prices, identity) if with_prices else {},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="X KOL theme heat + promotion queue")
    ap.add_argument("--with-prices", action="store_true", help="enrich from FMP")
    ap.add_argument("--promote", metavar="TICKER", help="approve for 分析 [TICKER]")
    ap.add_argument("--reject", metavar="TICKER", help="never surface again")
    ap.add_argument("--mark-analyzed", metavar="TICKER", help="分析 已跑完")
    ap.add_argument("--note", help="free-text reason, stored with the decision")
    ap.add_argument("--queue", action="store_true", help="show approved-not-yet-run only")
    ap.add_argument("--json", action="store_true", help="machine-readable heat dump")
    ap.add_argument("--config", default=str(budget_mod.CONFIG_PATH))
    args = ap.parse_args(argv)

    config = budget_mod.load_config(Path(args.config))
    heat_cfg = config.get("heat") or {}
    cand_path = ROOT / heat_cfg.get("candidates_path", "news/x_kol_logs/x_kol_candidates.json")

    for flag, decision in (("promote", "promoted"), ("reject", "rejected"),
                           ("mark_analyzed", "analyzed")):
        value = getattr(args, flag)
        if value:
            sym = value.upper().lstrip("$")
            if decision == "promoted":
                blocked = (load_candidates(cand_path).get("tickers", {})
                           .get(sym, {}).get("unanalyzable"))
                if blocked:
                    print(f"[x_kol.heat] ⚠ ${sym} cannot be analysed: {blocked}")
                    print("    Recorded anyway as a watch item — but 分析 will have "
                          "no numbers to work from.")
            entry = decide(cand_path, value, decision, note=args.note)
            print(f"[x_kol.heat] {sym} → {entry['decision']}")
            return 0

    data = build(config, with_prices=args.with_prices)
    cands = refresh_candidates(
        {s["ticker"]: s for s in data["tickers"]}, cand_path,
        surface_min=float(heat_cfg.get("surface_min_score", 0.3)))
    if data.get("unanalyzable"):
        for sym, reason in data["unanalyzable"].items():
            if sym in cands.get("tickers", {}):
                cands["tickers"][sym]["unanalyzable"] = reason
        for sym in list(cands.get("tickers", {})):
            if sym not in data["unanalyzable"] and sym in data.get("prices", {}):
                cands["tickers"][sym].pop("unanalyzable", None)
        save_candidates(cand_path, cands)
    decisions = {k: v.get("decision") for k, v in cands.get("tickers", {}).items()}

    heat_path = ROOT / heat_cfg.get("heat_path", "news/x_kol_logs/x_kol_heat.json")
    heat_path.parent.mkdir(parents=True, exist_ok=True)
    heat_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps({**data, "decisions": decisions}, ensure_ascii=False, indent=2))
        return 0

    if args.queue:
        queued = [t for t, d in sorted(decisions.items()) if d == "promoted"]
        print(f"[x_kol.queue] approved for 分析, not yet run: {len(queued)}")
        for t in queued:
            print(f"  分析 {t}")
        return 0

    if not data["posts_scanned"]:
        print("[x_kol.heat] shadow log is empty — run collect.py first")
        return 0

    print(f"[x_kol.heat] {data['posts_scanned']} posts · "
          f"{len(data['tickers'])} tickers · {len(data['themes'])} clusters")
    for i, theme in enumerate(data["themes"], 1):
        print(f"\n  cluster {i}  score={theme['score']:.2f}  lead=${theme['lead']}  "
              f"({', '.join('$' + m for m in theme['members'])})")
        hdr = f"    {'ticker':<8}{'score':>7}{'ment':>6}{'prim':>6}  {'first seen':<12}{'state':<10}"
        if data["prices"]:
            hdr += f"{'5d%':>8}{'1m%':>8}{'YTD%':>9}"
        print(hdr)
        for sym in theme["members"]:
            slot = next(s for s in data["tickers"] if s["ticker"] == sym)
            row = (f"    ${sym:<7}{slot['score']:7.2f}{slot['mentions']:6}"
                   f"{slot['primary_mentions']:6}  {(slot['first_seen'] or '')[:10]:<12}"
                   f"{decisions.get(sym, 'pending'):<10}")
            p = data["prices"].get(sym)
            if data["prices"]:
                row += (f"{p['d5']:>8}{p['d21']:>8}{p['ytd']:>9}" if p
                        else f"{'-':>8}{'-':>8}{'-':>9}")
            if sym in data.get("identity_flags", {}):
                row += "  ⚠"
            print(row)

    flags = data.get("identity_flags") or {}
    if flags:
        print("\n[x_kol.identity] ⚠ the bare symbol may not be the company discussed:")
        for sym, info in sorted(flags.items()):
            print(f"    ${sym:<7} → {info.get('resolves_to', '?')}")
            print(f"    {'':<8}  {info.get('note', '')}")
        print("    Confirm identity BEFORE --promote; 分析 on a wrong symbol looks "
              "just as confident as a right one.")

    blocked = data.get("unanalyzable") or {}
    if blocked:
        print("\n[x_kol.analyzable] ✗ cannot reach 分析 — no numbers for the protocol:")
        for sym, reason in sorted(blocked.items()):
            print(f"    ${sym:<7} {reason}")
        print("    These still count toward theme heat; they just cannot be a position.")

    pending = [t for t, d in sorted(decisions.items()) if d == "pending"]
    if pending:
        print(f"\n[x_kol.queue] {len(pending)} pending your call: "
              f"{', '.join('$' + t for t in pending)}")
        print("  approve → heat.py --promote TICKER    drop → heat.py --reject TICKER")
    return 0


if __name__ == "__main__":
    sys.exit(main())

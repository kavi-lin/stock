#!/usr/bin/env python3
"""Keyword-heat container over Break News entities + X KOL cashtags.

    python3 scripts/wind/terms.py                 # rebuild + print the heat table
    python3 scripts/wind/terms.py --dry-run       # compute and print, write nothing
    python3 scripts/wind/terms.py --top 40        # longer table
    python3 scripts/wind/terms.py --json          # machine-readable

WHAT THIS IS. A decayed attention counter over terms the pipeline has ALREADY
extracted, plus the queue state that stops the dispatcher rescanning the same
term forever. It does no NLP: `bn_*.json` already carries
`summary.merged_entities.{tickers,sectors,themes,tech_keywords}`, curated by the
Break News debate, and `x_kol_events.jsonl` already carries X's structured
cashtags. This module only accumulates and decays them.

WHY A DICT IS ENOUGH. Selection is one `max()` over a few hundred keys once an
hour — a heap buys nothing. What a plain counter WOULD get wrong is three
things, so all three are here:
  * decay      — without it a term that trended last week outranks today's news
                 forever (0.5 ** (age_days / half_life), same as x_kol/heat.py)
  * cooldown   — "delete after scanning" is wrong: a genuinely hot term
                 re-accumulates within the hour and bills again. `scan_state`
                 plus `cooldown_until` is the fix; a term leaves the queue
                 without leaving the table.
  * durability — the process is not resident; the dict has to survive on disk.

TWO INDEPENDENT STATE AXES. `scan_state` is machine-owned and automatic (the
hourly social scan). `decision` is human-owned and is the SAME gate x_kol uses
for `分析 [TICKER]` — the investment protocol is never auto-launched from here.
Confusing the two is the one change that would break the exploration-layer
discipline this module operates under.

DISCIPLINE. Exploration layer. Nothing here feeds investment_protocol, writes
Nexus, or touches Dashboard/market_mood.json atmosphere indicators. Lead-lag
criteria are pre-registered in docs/wind_evaluation_criteria.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.wind import budget as budget_mod  # noqa: E402

BN_DIR = ROOT / "news/break_news_logs"
KOL_EVENTS = ROOT / "news/x_kol_logs/x_kol_events.jsonl"
X_KOL_CONFIG = ROOT / "config/x_kol.json"

SCAN_STATES = ("pending", "scanning", "scanned", "skipped")
KINDS = ("ticker", "theme", "tech_keyword")

# Break News only contributes entities once its debate has actually closed.
USABLE_BN_STATES = ("closed", "partial_closed")

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,14}$")
_WS_RE = re.compile(r"\s+")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


def _parse_ts(value) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


# ── normalization ────────────────────────────────────────────────────────
def normalize(term: str, kind: str) -> str | None:
    """Collapse the spelling variants the upstream extractor emits.

    Real collisions in the 2026-08-15 sample: `"IP Monetization"` and
    `"IP monetization"` in the same artifact, `"Digital Gaming"` / `"digital
    gaming"`, `"foundry expansion"` / `"Semiconductor Foundry"`. Casefolding
    catches the first two. The third is a genuine synonym pair and is left
    alone — merging on meaning needs a classifier, and guessing would silently
    fuse unrelated terms.
    """
    if not isinstance(term, str):
        return None
    text = _WS_RE.sub(" ", term).strip()
    if not text:
        return None
    if kind == "ticker":
        text = text.upper().lstrip("$")
        return text if _TICKER_RE.match(text) else None
    return text.casefold()


def _display(kind: str, spellings: dict[str, int]) -> str:
    """Most frequent original spelling wins; ties break alphabetically so the
    table does not reshuffle between runs on equal counts."""
    if not spellings:
        return ""
    return sorted(spellings.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


# ── producers ────────────────────────────────────────────────────────────
def _iter_break_news(lookback_days: int):
    """Yield (kind, raw_term, weight_ctx, ts, source) from closed Break News."""
    cutoff = _now() - timedelta(days=lookback_days)
    if not BN_DIR.is_dir():
        return
    for path in sorted(BN_DIR.glob("bn_*.json")):
        try:
            with open(path, encoding="utf-8") as fp:
                doc = json.load(fp)
        except (OSError, json.JSONDecodeError):
            continue
        if doc.get("state") not in USABLE_BN_STATES:
            continue
        source = doc.get("source") or {}
        ts = _parse_ts(source.get("published")) or _parse_ts(doc.get("fetched_at"))
        if ts is None or ts < cutoff:
            continue
        entities = (doc.get("summary") or {}).get("merged_entities") or {}
        triage = doc.get("triage") or {}
        ctx = {
            "credibility": source.get("credibility") or triage.get("effective_credibility") or "MEDIUM",
            "materiality": triage.get("materiality_score"),
            # url_hash is the dedupe key: the same wire story reaches us through
            # several feeds and would otherwise ballot-stuff its own keywords.
            "fingerprint": source.get("url_hash") or source.get("url") or doc.get("news_id"),
            # The tickers this article filed alongside the term. A theme is not
            # tradeable by itself — "Claude" is a real market story only because
            # its articles are about AMZN/GOOGL/MSFT/NVDA. Carrying the co-mention
            # forward is what lets the scan ask a question with an answer.
            "co_tickers": [t for t in (entities.get("tickers") or []) if isinstance(t, str)],
        }
        origin = {
            "kind": "break_news",
            "id": doc.get("news_id"),
            "url": source.get("url"),
            "headline": doc.get("headline"),
        }
        for field, kind in (("tickers", "ticker"), ("themes", "theme"),
                            ("tech_keywords", "tech_keyword")):
            for raw in entities.get(field) or []:
                yield kind, raw, ctx, ts, origin


def _iter_kol(lookback_days: int, primary_w: float, secondary_w: float):
    """Yield cashtags from the X KOL shadow log, primary-vs-secondary weighted."""
    cutoff = _now() - timedelta(days=lookback_days)
    if not KOL_EVENTS.is_file():
        return
    with open(KOL_EVENTS, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = _parse_ts(rec.get("created_at"))
            if ts is None or ts < cutoff:
                continue
            tags = rec.get("cashtags") or []
            for idx, raw in enumerate(tags):
                ctx = {
                    "credibility": "MEDIUM",
                    "materiality": None,
                    "fingerprint": rec.get("post_id"),
                    "position_weight": primary_w if idx == 0 else secondary_w,
                }
                origin = {
                    "kind": "x_kol",
                    "id": rec.get("post_id"),
                    "url": rec.get("url"),
                    "headline": (rec.get("text") or "")[:160],
                }
                yield "ticker", raw, ctx, ts, origin


# ── scoring ──────────────────────────────────────────────────────────────
def score_terms(config: dict, *, now: datetime | None = None) -> dict:
    """Recency-decayed attention score per term, plus its acceleration.

    weight = kind × credibility × materiality × position × 0.5 ** (age/half_life)

    Every factor is a hand-calibrated constant in config/wind.json (or, for the
    KOL primary/secondary split, config/x_kol.json — that pair was validated on
    real 2026-08-06 data and there is no reason to re-derive it here).

    Two decays are accumulated over the same mentions, not one:

      score     fast half-life  → proportional to the CURRENT mention rate
      baseline  slow half-life  → proportional to the LONGER-RUN mention rate
      surprise  = rate(score) / rate(baseline)

    Ranking on `score` alone is wrong and was measured to be wrong: on 14 days
    of real Break News it returns NVDA / AI capex / SPY / AMZN / MSFT / QQQ,
    because a name that appears in every macro article every day accumulates
    the most weight forever. That is coverage volume, not wind direction. Under
    a constant mention rate r, an exponentially decayed sum converges to
    r·h/ln2 — so dividing each decayed sum by its own half-life recovers the
    rate, and their ratio is "how much hotter than usual is this, right now".
    A permanently-covered name lands near 1.0; a term that just accelerated
    lands well above it; a brand-new term lands at h_slow/h_fast.
    """
    now = now or _now()
    heat = config["heat"]
    half_life = float(heat.get("half_life_days", 2.0)) or 2.0
    base_half_life = float(heat.get("baseline_half_life_days", 10.0)) or 10.0
    epsilon = float(heat.get("surprise_epsilon", 0.05))
    kind_w = heat.get("kind_weight", {})
    cred_w = heat.get("credibility_weight", {})
    mat_scale = float(heat.get("materiality_scale", 0.0))
    min_chars = int(heat.get("min_term_chars", 3))
    lookback = int(heat.get("lookback_days", 14))

    primary_w, secondary_w = 1.0, 0.4
    try:
        with open(X_KOL_CONFIG, encoding="utf-8") as fp:
            kol_heat = json.load(fp).get("heat", {})
        primary_w = float(kol_heat.get("primary_weight", 1.0))
        secondary_w = float(kol_heat.get("secondary_weight", 0.4))
    except (OSError, json.JSONDecodeError, ValueError):
        pass

    stats: dict[str, dict] = {}
    producers = (
        _iter_break_news(lookback),
        _iter_kol(lookback, primary_w, secondary_w),
    )
    for producer in producers:
        for kind, raw, ctx, ts, origin in producer:
            norm = normalize(raw, kind)
            if not norm or len(norm) < min_chars:
                continue
            key = f"{kind}:{norm}"
            slot = stats.setdefault(key, {
                "key": key, "term": norm, "kind": kind, "score": 0.0,
                "baseline": 0.0, "mentions": 0, "first_seen": None,
                "last_seen": None, "spellings": {}, "sources": [],
                "_fingerprints": set(), "_co": {},
            })

            fingerprint = ctx.get("fingerprint")
            # One article contributes a given term once, no matter how many
            # feeds carried it or how many times the extractor repeated it.
            if fingerprint and fingerprint in slot["_fingerprints"]:
                continue
            if fingerprint:
                slot["_fingerprints"].add(fingerprint)

            age_days = max(0.0, (now - ts).total_seconds() / 86400.0)
            materiality = ctx.get("materiality")
            mat_mult = 1.0
            if isinstance(materiality, (int, float)):
                mat_mult = 1.0 + mat_scale * max(0.0, float(materiality) - 2.0)
            base_weight = (
                float(kind_w.get(kind, 1.0))
                * float(cred_w.get(str(ctx.get("credibility")).upper(), 0.7))
                * mat_mult
                * float(ctx.get("position_weight", 1.0))
            )
            weight = base_weight * (0.5 ** (age_days / half_life))

            slot["score"] += weight
            slot["baseline"] += base_weight * (0.5 ** (age_days / base_half_life))
            # Weight co-mentions by the same decay, so a theme's ticker anchors
            # track what it is about NOW rather than what it once was about.
            if kind != "ticker":
                for sym in ctx.get("co_tickers") or []:
                    sym = normalize(sym, "ticker")
                    if sym:
                        slot["_co"][sym] = slot["_co"].get(sym, 0.0) + weight
            slot["mentions"] += 1
            slot["spellings"][str(raw).strip()] = slot["spellings"].get(str(raw).strip(), 0) + 1
            iso = ts.isoformat(timespec="seconds")
            if not slot["first_seen"] or iso < slot["first_seen"]:
                slot["first_seen"] = iso
            if not slot["last_seen"] or iso > slot["last_seen"]:
                slot["last_seen"] = iso
            if len(slot["sources"]) < 12:
                slot["sources"].append(origin)

    for slot in stats.values():
        # Divide each decayed sum by its own half-life to recover a per-day
        # rate, then take the ratio. Without this normalization the slow decay
        # always dominates and every term looks equally "cold".
        rate_fast = slot["score"] / half_life
        rate_slow = slot["baseline"] / base_half_life
        slot["surprise"] = round(rate_fast / (rate_slow + epsilon), 4)
        slot["score"] = round(slot["score"], 4)
        slot["baseline"] = round(slot["baseline"], 4)
        slot["display"] = _display(slot["kind"], slot["spellings"])
        slot["related_tickers"] = [
            sym for sym, _ in sorted(slot["_co"].items(), key=lambda kv: (-kv[1], kv[0]))
        ][:5]
        slot.pop("_fingerprints", None)
        slot.pop("spellings", None)
        slot.pop("_co", None)
    return stats


# ── container persistence ────────────────────────────────────────────────
def load_terms(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as fp:
            return json.load(fp)
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "terms": {}}


def save_terms(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2, sort_keys=True)
            fp.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def merge(stats: dict, path: Path, *, surface_min: float, now: datetime | None = None) -> dict:
    """Fold freshly computed scores into the durable container.

    Scores are recomputed from scratch every tick (they decay, so they are a
    function of the source logs and the clock, never of the stored value).
    What IS durable and must never be clobbered: scan_state, cooldown_until,
    score_at_scan, and first_surfaced_at.

    `first_surfaced_at` is the event timestamp the lead-lag evaluation keys on
    (docs/wind_evaluation_criteria.md §2). It is stamped ONCE, the first time a
    term's score crosses the surface threshold, and never rewritten — including
    when the term cools off and crosses again later.
    """
    now = now or _now()
    data = load_terms(path)
    terms = data.setdefault("terms", {})

    for key, slot in stats.items():
        entry = terms.get(key)
        if entry is None:
            entry = {
                "scan_state": "pending",
                "scanned_at": None,
                "cooldown_until": None,
                "last_scan_path": None,
                "score_at_scan": None,
                "first_surfaced_at": None,
            }
            terms[key] = entry
        entry.update({
            "term": slot["term"],
            "display": slot["display"],
            "kind": slot["kind"],
            "score": slot["score"],
            "baseline": slot["baseline"],
            "surprise": slot["surprise"],
            "mentions": slot["mentions"],
            "first_seen": slot["first_seen"],
            "last_seen": slot["last_seen"],
            # Provenance is only carried for terms that can actually reach the
            # queue. Keeping 12 sourced headlines for all ~4,700 tracked terms
            # made this file 4.4 MB, 55% of it evidence for terms that will
            # never be picked — and it is rewritten every tick.
            "sources": slot["sources"][:4] if slot["score"] >= surface_min else [],
            "related_tickers": slot.get("related_tickers") or [],
        })
        entry.setdefault("scan_state", "pending")
        if entry.get("first_surfaced_at") is None and slot["score"] >= surface_min:
            entry["first_surfaced_at"] = now.isoformat(timespec="seconds")

    # Terms absent from this rebuild have decayed out of the lookback window.
    live = set(stats)
    for key in list(terms):
        if key in live:
            continue
        entry = terms[key]
        # A term that decayed away without ever surfacing is not evidence of
        # anything — drop it. One that DID surface is kept forever at score 0:
        # its first_surfaced_at is the event timestamp the lead-lag evaluation
        # keys on (docs/wind_evaluation_criteria.md §2).
        if entry.get("first_surfaced_at") is None and entry.get("scan_state") == "pending":
            del terms[key]
            continue
        entry["score"] = 0.0
        entry["surprise"] = 0.0
        entry["sources"] = []

    data["version"] = 1
    data["updated_at"] = now.isoformat(timespec="seconds")
    data["surface_min_score"] = surface_min
    save_terms(path, data)
    return data


def set_scan_state(path: Path, key: str, state: str, *, scan_path: str | None = None,
                   cooldown_hours: float | None = None, score_at_scan: float | None = None) -> dict:
    if state not in SCAN_STATES:
        raise ValueError(f"scan_state must be one of {SCAN_STATES}")
    data = load_terms(path)
    entry = data.setdefault("terms", {}).setdefault(key, {"scan_state": "pending"})
    entry["scan_state"] = state
    if state == "scanned":
        now = _now()
        entry["scanned_at"] = now.isoformat(timespec="seconds")
        if cooldown_hours:
            entry["cooldown_until"] = (
                now + timedelta(hours=float(cooldown_hours))
            ).isoformat(timespec="seconds")
        if scan_path:
            entry["last_scan_path"] = scan_path
        if score_at_scan is not None:
            entry["score_at_scan"] = round(float(score_at_scan), 4)
    data["updated_at"] = _now_iso()
    save_terms(path, data)
    return entry


def in_cooldown(entry: dict, *, rescan_jump: float, now: datetime | None = None) -> bool:
    """True while a scanned term is still resting.

    Cooldown breaks early only if attention genuinely re-accelerated: the score
    must exceed its value at scan time by `rescan_jump`. Re-crossing the plain
    surface threshold is not enough — that is the state the term was already in
    when we paid for the last scan.
    """
    until = _parse_ts(entry.get("cooldown_until"))
    if until is None:
        return False
    if (now or _now()) >= until:
        return False
    baseline = entry.get("score_at_scan")
    if isinstance(baseline, (int, float)) and baseline > 0:
        if float(entry.get("score", 0.0)) >= float(baseline) * (1.0 + float(rescan_jump)):
            return False
    return True


def eligible(data: dict, config: dict, *, now: datetime | None = None,
             ignore_cooldown: bool = False) -> list[tuple[str, dict]]:
    """Terms that clear every queue gate, most-accelerated first.

    Three gates, each answering a different question:
      score    ≥ surface_min_score  — is this covered enough to be worth money?
      mentions ≥ min_mentions       — do independent carriers corroborate it?
      term     ∉ stop_terms         — is it a subject, or just the backdrop?

    Then rank by `surprise`, not by score. Both halves matter: gating on score
    alone and ranking on score picks the same mega-caps every hour; ranking on
    surprise without the mentions gate lets one listicle set the agenda.

    pick_next() and the CLI table share this function so the queue you see is
    the queue the dispatcher acts on.
    """
    heat = config["heat"]
    dispatch = config["dispatch"]
    surface_min = float(heat.get("surface_min_score", 1.0))
    min_mentions = int(heat.get("min_mentions", 1))
    rescan_jump = float(dispatch.get("rescan_score_jump", 0.5))
    stop = {str(t).casefold() for t in heat.get("stop_terms", [])}

    out: list[tuple[str, dict]] = []
    for key, entry in (data.get("terms") or {}).items():
        if entry.get("scan_state") in ("scanning", "skipped"):
            continue
        if str(entry.get("term", "")).casefold() in stop:
            continue
        if float(entry.get("score") or 0.0) < surface_min:
            continue
        if int(entry.get("mentions") or 0) < min_mentions:
            continue
        if not ignore_cooldown and in_cooldown(entry, rescan_jump=rescan_jump, now=now):
            continue
        out.append((key, entry))
    out.sort(key=lambda kv: -float(kv[1].get("surprise") or 0.0))
    return out


def pick_next(data: dict, config: dict, *, now: datetime | None = None) -> tuple[str, dict] | None:
    """Most-accelerated eligible term, or None on a quiet tick."""
    ranked = eligible(data, config, now=now)
    return ranked[0] if ranked else None


def rebuild(config: dict, *, path: Path | None = None, now: datetime | None = None) -> dict:
    heat = config["heat"]
    path = path or (ROOT / heat["terms_path"])
    stats = score_terms(config, now=now)
    return merge(stats, path, surface_min=float(heat.get("surface_min_score", 1.0)), now=now)


# ── CLI ──────────────────────────────────────────────────────────────────
def _table(data: dict, config: dict, top: int) -> str:
    """Queue order: gated on raw score, sorted by surprise — the same order
    pick_next() uses, so the table shows what the dispatcher would actually do."""
    rows = [entry for _, entry in eligible(data, config, ignore_cooldown=True)][:top]
    if not rows:
        return "(nothing at/above surface_min_score — check news/break_news_logs/ for closed bn_*.json)"
    width = max((len(str(r.get("display") or r.get("term", ""))) for r in rows), default=12)
    width = min(max(width, 12), 44)
    out = [f"{'TERM'.ljust(width)}  {'KIND':<12} {'SURPRISE':>8} {'SCORE':>7} {'MEN':>4}  STATE"]
    for r in rows:
        label = str(r.get("display") or r.get("term", ""))[:width]
        state = r.get("scan_state", "pending")
        cd = r.get("cooldown_until")
        if state == "scanned" and cd:
            state = f"scanned→{cd[5:16]}"
        out.append(
            f"{label.ljust(width)}  {r.get('kind',''):<12} "
            f"{float(r.get('surprise') or 0.0):>8.2f} "
            f"{float(r.get('score') or 0.0):>7.3f} {int(r.get('mentions') or 0):>4}  {state}"
        )
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Wind keyword-heat container")
    ap.add_argument("--dry-run", action="store_true", help="compute and print, write nothing")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--json", action="store_true", help="emit the container as JSON")
    args = ap.parse_args(argv)

    config = budget_mod.load_config()
    path = ROOT / config["heat"]["terms_path"]

    if args.dry_run:
        stats = score_terms(config)
        data = {"terms": stats, "updated_at": _now_iso()}
    else:
        data = rebuild(config, path=path)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print(_table(data, config, args.top))
    total = len(data.get("terms") or {})
    surface = float(config["heat"].get("surface_min_score", 1.0))
    above = sum(1 for e in (data.get("terms") or {}).values()
                if float(e.get("score") or 0.0) >= surface)
    nxt = pick_next(data, config)
    print(f"\n{total} terms tracked · {above} at/above surface_min_score {surface}"
          + ("  [dry-run, nothing written]" if args.dry_run else f"  → {path.relative_to(ROOT)}"))
    print(f"next to scan: {nxt[0] if nxt else '(none — quiet tick, $0)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

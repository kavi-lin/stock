#!/usr/bin/env python3
"""V2.19.0 — build news/news_logs/structural_watchlist.json from digest cache.

Scans past 30 days of `news_logs/*_digest.json` for tickers with structural
keyword hits (sold out / capacity constrained / supercycle / 供不應求 ...),
applies decay rules:
  - 14-day rolling hit window
  - 21-day eviction after last_observed_date
  - First-hit gate (≥ 2 independent sources / 14d to enter)
  - Source dedup (url stem OR headline 8-gram match → 1 hit)

Output: `news/news_logs/structural_watchlist.json` (atomic temp + rename).

Failure non-fatal: missing inputs → write empty `candidates: []`, rc=0.
Daily cron: invoked from `daily_update.sh` Step 7.

Usage:
    python3 news/scripts/build_structural_watchlist.py
        rc=0 → success (incl. empty candidates)
        rc=1 → unrecoverable error (e.g. cannot write output dir)
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT       = Path(__file__).resolve().parents[2]
LOGS_DIR   = ROOT / "news" / "news_logs"
OUTPUT     = LOGS_DIR / "structural_watchlist.json"

HIT_WINDOW_DAYS    = 14
EVICTION_DAYS      = 21
FIRST_HIT_GATE_MIN = 2   # ≥ 2 independent sources / 14d window
LOOKBACK_DAYS      = 30  # how far back to load digest files

# Narrow whitelist — broader sentiment keywords excluded by design
STRUCTURAL_KEYWORDS = (
    "sold out", "capacity constrained", "structural deficit", "supercycle",
    "super-cycle", "supply tight", "shortage", "all-time high demand",
    "booked through", "fully allocated", "production at capacity",
    "capacity expansion", "供不應求", "結構性短缺",
)


def _load_recent_digests() -> list[tuple[date, dict]]:
    """Return [(file_date, payload), ...] for last LOOKBACK_DAYS days."""
    out: list[tuple[date, dict]] = []
    if not LOGS_DIR.exists():
        return out
    today = date.today()
    cutoff = today - timedelta(days=LOOKBACK_DAYS)
    for path in sorted(glob.glob(str(LOGS_DIR / "*_digest.json"))):
        m = re.search(r"(\d{4}-\d{2}-\d{2})_digest\.json$", path)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if d < cutoff:
            continue
        try:
            with open(path, "r", encoding="utf-8") as fp:
                out.append((d, json.load(fp)))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def _headline_8gram(headline: str) -> str:
    """Build a stable 8-gram fingerprint from first 8 ASCII-word tokens.
    Used for dedup when same news is re-posted by multiple wires."""
    if not isinstance(headline, str):
        return ""
    tokens = re.findall(r"\w+", headline.lower())[:8]
    return " ".join(tokens)


def _verdict_keyword_hits(v: dict) -> list[str]:
    """Return list of structural keywords found in this verdict's narrative."""
    haystack_parts: list[str] = []
    for k in ("headline", "headline_zh", "bull_case", "bear_case",
              "arbiter_reasoning", "thesis"):
        s = v.get(k)
        if isinstance(s, str):
            haystack_parts.append(s)
    haystack = "\n".join(haystack_parts).lower()
    return [kw for kw in STRUCTURAL_KEYWORDS if kw.lower() in haystack]


def _sector_str(affected_sectors) -> str:
    """Pick the first sector from affected_sectors[] entries (dict or string)."""
    if not isinstance(affected_sectors, list) or not affected_sectors:
        return ""
    first = affected_sectors[0]
    if isinstance(first, dict):
        return first.get("sector") or ""
    if isinstance(first, str):
        return first
    return ""


def build_watchlist() -> dict:
    """Aggregate ticker-level hits across digests; apply decay rules."""
    digests = _load_recent_digests()

    # ticker -> {"hits": [(date, source_label, fingerprint, keyword)], "sector": str}
    ticker_state: dict[str, dict] = {}

    for file_date, payload in digests:
        for v in (payload.get("verdicts") or []):
            kws = _verdict_keyword_hits(v)
            if not kws:
                continue
            sector = _sector_str(v.get("affected_sectors"))
            source = v.get("source_label") or v.get("source") or ""
            fingerprint = _headline_8gram(v.get("headline") or "")
            for tkr in (v.get("tickers_mentioned") or []):
                if not isinstance(tkr, str) or not tkr.strip():
                    continue
                tkr_u = tkr.upper().strip()
                state = ticker_state.setdefault(tkr_u, {"hits": [], "sector": sector})
                if not state.get("sector") and sector:
                    state["sector"] = sector
                # Append; dedup applied later
                for kw in kws:
                    state["hits"].append({
                        "date": file_date.isoformat(),
                        "source": source,
                        "fingerprint": fingerprint,
                        "keyword": kw,
                    })

    today = date.today()
    candidates: list[dict] = []
    stats = {"raw_tickers": len(ticker_state), "evicted": 0, "first_hit_filtered": 0}

    for tkr, state in ticker_state.items():
        hits = state.get("hits") or []
        if not hits:
            continue

        # Sort hits by date asc
        hits.sort(key=lambda h: h["date"])
        last_hit_date = datetime.strptime(hits[-1]["date"], "%Y-%m-%d").date()
        first_hit_date = datetime.strptime(hits[0]["date"], "%Y-%m-%d").date()
        days_since_last = (today - last_hit_date).days

        # Eviction: stale tickers dropped
        if days_since_last > EVICTION_DAYS:
            stats["evicted"] += 1
            continue

        # 14d window: keep hits within last_hit - 14d to last_hit
        window_start = last_hit_date - timedelta(days=HIT_WINDOW_DAYS)
        windowed = [h for h in hits if datetime.strptime(h["date"], "%Y-%m-%d").date() >= window_start]

        # Dedup within window: same fingerprint OR same source on same date = 1 hit
        seen: set[tuple[str, str, str]] = set()
        deduped: list[dict] = []
        for h in windowed:
            key = (h["date"], h["source"], h["fingerprint"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(h)

        # First-hit gate: need ≥ 2 independent sources to enter
        unique_sources = {h["source"] for h in deduped if h["source"]}
        if len(deduped) < FIRST_HIT_GATE_MIN or len(unique_sources) < FIRST_HIT_GATE_MIN:
            stats["first_hit_filtered"] += 1
            continue

        keywords_seen = sorted({h["keyword"] for h in deduped})
        candidates.append({
            "ticker": tkr,
            "sector": state.get("sector") or "",
            "keyword_hits": keywords_seen,
            "hit_count_14d": len(deduped),
            "source_credibility_max": "HIGH" if len(unique_sources) >= 3 else "MEDIUM",
            "first_observed": first_hit_date.isoformat(),
            "last_observed": last_hit_date.isoformat(),
            "days_since_last_hit": days_since_last,
            "note": "watchlist only; not a Phase 3 modulation trigger in V2.19",
        })

    # Sort candidates by hit_count desc, then days_since_last asc
    candidates.sort(key=lambda c: (-c["hit_count_14d"], c["days_since_last_hit"]))

    # Sector aggregation
    sector_counts: dict[str, int] = {}
    for c in candidates:
        s = c.get("sector") or ""
        if s:
            sector_counts[s] = sector_counts.get(s, 0) + 1
    sectors = [
        {"sector": s, "hot": cnt >= 2, "ticker_count": cnt}
        for s, cnt in sorted(sector_counts.items(), key=lambda kv: -kv[1])
    ]

    return {
        "as_of": today.isoformat(),
        "decay_rules": {
            "hit_window_days": HIT_WINDOW_DAYS,
            "eviction_after_days": EVICTION_DAYS,
            "eviction_basis": "last_observed_date",
            "first_hit_gate_min_sources": FIRST_HIT_GATE_MIN,
        },
        "candidates": candidates,
        "sectors": sectors,
        "stats": {
            "candidates_in": len(candidates),
            "candidates_evicted": stats["evicted"],
            "first_hit_filtered": stats["first_hit_filtered"],
            "digests_scanned": len([d for d, _ in _load_recent_digests()]),
        },
    }


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".structural_watchlist_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, indent=2, ensure_ascii=False)
            fp.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def main() -> int:
    try:
        watchlist = build_watchlist()
    except Exception as e:
        # Failure non-fatal: write empty payload + log to stderr, rc=0
        print(f"[build_structural_watchlist] WARN: build failed ({e}); writing empty",
              file=sys.stderr)
        watchlist = {
            "as_of": date.today().isoformat(),
            "decay_rules": {
                "hit_window_days": HIT_WINDOW_DAYS,
                "eviction_after_days": EVICTION_DAYS,
                "eviction_basis": "last_observed_date",
                "first_hit_gate_min_sources": FIRST_HIT_GATE_MIN,
            },
            "candidates": [],
            "sectors": [],
            "stats": {"candidates_in": 0, "build_error": str(e)[:200]},
        }

    try:
        _atomic_write(OUTPUT, watchlist)
    except OSError as e:
        print(f"[build_structural_watchlist] FATAL: cannot write {OUTPUT}: {e}",
              file=sys.stderr)
        return 1

    n_cand = len(watchlist.get("candidates") or [])
    n_sect = sum(1 for s in (watchlist.get("sectors") or []) if s.get("hot"))
    print(f"[build_structural_watchlist] ✓ {n_cand} candidates, {n_sect} hot sectors → {OUTPUT.name}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

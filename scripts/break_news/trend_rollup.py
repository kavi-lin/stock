"""3-day sentiment-trend rollup over break-news debate logs.

Builds a running *sentiment index* per market / sector / theme. Each closed
debate log is one signed event at its `fetched_at` timestamp:

    sign     = +1 BULLISH / -1 BEARISH / 0 NEUTRAL|SPLIT
    weight   = impact(shallow_score) x source-credibility
    contrib  = sign * weight

Events are bucketed into hourly slots across a rolling 72h window, then run
through a time-decay EMA:

    S[h] = S[h-1] * decay + contrib_in_bucket[h]

`decay` comes from a half-life (default 12h) so stale optimism fades — with no
fresh news the index drifts back toward 0. The plotted value is `tanh(S/scale)`
so it stays in [-1, +1] and a flat run regresses to 0.

Why US-Eastern is irrelevant here: the index is a continuous hourly series, so
bucketing is done directly in UTC (no "trading day" notion needed).

Read-only. No file writes. The dashboard server calls `compute_trends()`
on-demand behind a short TTL cache.

Standalone debug: `python3 scripts/break_news/trend_rollup.py`
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Bootstrap the repo root onto sys.path so `scripts.break_news.store` resolves
# whether this file is imported by dashboard_server or run directly.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.break_news import store  # noqa: E402
from news.fetch_news_rss import headline_fingerprint  # noqa: E402

_USABLE_STATES = {"closed", "partial_closed"}
# News-digest dirs + depth weighting — committee (4-agent) verdicts feed the
# trend index too, weighted higher than the 2-model break-news debate.
_NEWS_LOGS_DIR = _ROOT / "news" / "news_logs"
_DIGEST_DEPTH_MULT = {"deep": 1.8, "shallow": 1.0}
_WS_RE = re.compile(r"\s+")

_WINDOW_HOURS = 72          # rolling window = 3 days, hourly buckets
_HALF_LIFE_H = 12.0         # an event keeps 50% weight after this many hours
_DECAY = 0.5 ** (1.0 / _HALF_LIFE_H)
_ATANH_TARGET = math.atanh(0.9)   # an entity's peak maps to ~0.9 on the chart
_MIN_SCALE = 4.0            # floor so a near-flat entity isn't amplified to noise
_MIN_EVENTS = 3             # sector/theme needs this many events to be plotted
_TOP_ENTITIES = 12          # cap selectable sectors / themes (by activity)

_ALL_KEY = "__ALL__"
_VERDICT_SIGN = {"BULLISH": 1.0, "BEARISH": -1.0}  # others -> 0
_CRED_MULT = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}

# Hand-curated theme aliases — fold obvious free-text duplicates onto a
# canonical key. Keys + values are pre-normalized (lowercase, single-spaced).
# Intentionally small: extend as fragmentation actually shows up.
ALIAS_MAP = {
    "ai data center power infrastructure": "ai capex",
    "ai data center buildout": "ai capex",
    "ai infrastructure spending": "ai capex",
    "ai hardware manufacturing": "ai capex",
    "data center capex": "ai capex",
    "semiconductor export controls": "ai chip export controls",
    "chip export controls": "ai chip export controls",
    "semis export controls": "ai chip export controls",
    "china reopening": "china reopening trade",
}


def _norm_theme(raw: str) -> str:
    """Lowercase, collapse whitespace, fold known aliases."""
    s = _WS_RE.sub(" ", (raw or "").strip().lower())
    return ALIAS_MAP.get(s, s)


def _norm_sector(raw: str) -> str:
    """Sectors are clean GICS strings — only trim/collapse whitespace."""
    return _WS_RE.sub(" ", (raw or "").strip())


def _utc_dt(iso: str):
    """ISO8601 string -> tz-aware UTC datetime, or None on parse failure."""
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _event_weight(shallow_score, credibility) -> float:
    """Impact weight for one news event: bigger triage score + more credible
    source -> stronger nudge on the sentiment index."""
    try:
        s = float(shallow_score)
    except (TypeError, ValueError):
        s = 2.0
    impact = min(2.0, max(0.25, s / 4.0))
    return impact * _CRED_MULT.get(str(credibility or "").upper(), 0.7)


def _ema_series(buckets):
    """Hourly contribution buckets -> tanh-squashed EMA series in [-1, 1].

    The squash scale is adaptive per entity: an entity's own peak maps to ~0.9
    (floored by _MIN_SCALE) so each line uses the chart's full range — the
    market is far more active than any one sector, and the selector shows one
    line at a time, so a shared scale would flatten the quieter entities.
    """
    raw = []
    s = 0.0
    for c in buckets:
        s = s * _DECAY + c
        raw.append(s)
    peak = max((abs(x) for x in raw), default=0.0)
    scale = max(_MIN_SCALE, peak / _ATANH_TARGET) if peak > 0 else _MIN_SCALE
    return [round(math.tanh(x / scale), 4) for x in raw]


def compute_trends(now_utc: datetime | None = None,
                   window_hours: int = _WINDOW_HOURS) -> dict:
    """Aggregate break-news logs into hourly sentiment-index series.

    Returns one series for the whole market plus one per active sector/theme,
    sharing a single `series_labels` time axis.
    """
    now = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    end = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    start = end - timedelta(hours=window_hours)
    n = window_hours

    contrib: dict = {}   # key -> [n] hourly contribution sums
    meta: dict = {}      # key -> {key,label,kind,events}

    def _slot(key, label, kind):
        if key not in contrib:
            contrib[key] = [0.0] * n
            meta[key] = {"key": key, "label": label, "kind": kind, "events": 0}

    def _idx_for(dt):
        """Hourly bucket index for a UTC datetime, or None if outside window."""
        if dt is None or dt < start or dt >= end:
            return None
        i = int((dt - start).total_seconds() // 3600)
        return i if 0 <= i < n else None

    log_count = 0

    def _add_event(idx, contrib_val, sectors, themes):
        """Accumulate one signed event into the market line + its sector/theme
        lines. `contrib_val` already carries sign × weight."""
        nonlocal log_count
        log_count += 1
        _slot(_ALL_KEY, "Market", "all")
        contrib[_ALL_KEY][idx] += contrib_val
        meta[_ALL_KEY]["events"] += 1
        seen = set()
        for raw in sectors or []:
            name = _norm_sector(str(raw))
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            key = "sector:" + name
            _slot(key, name, "sector")
            contrib[key][idx] += contrib_val
            meta[key]["events"] += 1
        seen = set()
        for raw in themes or []:
            norm = _norm_theme(str(raw))
            if not norm or norm in seen:
                continue
            seen.add(norm)
            key = "theme:" + norm
            _slot(key, str(raw).strip(), "theme")  # first-seen casing wins
            contrib[key][idx] += contrib_val
            meta[key]["events"] += 1

    # ── Pass 1: committee news digests ───────────────────────────────
    # Deep (4-agent) verdicts weigh 1.8×; their headlines also win the dedup
    # race against any break-news log covering the same story.
    digest_fps: set = set()
    for path in sorted(_NEWS_LOGS_DIR.glob("*_digest.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            continue
        for v in data.get("verdicts") or []:
            headline = str(v.get("headline") or "")
            if headline:
                fp = headline_fingerprint(headline)
                if fp:
                    digest_fps.add(fp)
            idx = _idx_for(_utc_dt(v.get("published")))
            if idx is None:
                continue
            sign = _VERDICT_SIGN.get(str(v.get("verdict") or "").upper(), 0.0)
            depth_mult = _DIGEST_DEPTH_MULT.get(str(v.get("depth") or "").lower(), 1.0)
            # net_impact_score passed as-is (may be negative) — matches how the
            # break-news pass feeds raw shallow_score into _event_weight.
            weight = _event_weight(v.get("net_impact_score"), "HIGH") * depth_mult
            sectors = [s.get("sector") if isinstance(s, dict) else s
                       for s in (v.get("affected_sectors") or [])]
            _add_event(idx, sign * weight, sectors, [])

    # ── Pass 2: break-news debate logs ───────────────────────────────
    for path in sorted(store.STORE_DIR.glob("bn_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            continue
        if data.get("state") not in _USABLE_STATES:
            continue
        idx = _idx_for(_utc_dt(data.get("fetched_at")))
        if idx is None:
            continue
        headline = str(data.get("headline") or "")
        if headline and headline_fingerprint(headline) in digest_fps:
            continue  # already counted via the higher-quality digest verdict

        summary = data.get("summary") or {}
        sign = _VERDICT_SIGN.get(
            str(summary.get("consensus_verdict") or "").upper(), 0.0)
        triage = data.get("triage") or {}
        src = data.get("source") or {}
        weight = _event_weight(triage.get("shallow_score"), src.get("credibility"))
        ent = summary.get("merged_entities") or {}
        _add_event(idx, sign * weight, ent.get("sectors"), ent.get("themes"))

    # Keep the market line always; sector/theme lines need enough events so
    # the curve isn't a 2-point zigzag.
    rows = [m for m in meta.values()
            if m["kind"] == "all" or m["events"] >= _MIN_EVENTS]
    kind_rank = {"all": 0, "sector": 1, "theme": 2}
    rows.sort(key=lambda m: (kind_rank[m["kind"]], -m["events"], m["label"].lower()))

    entities, kept_keys, per_kind = [], [], {"sector": 0, "theme": 0}
    for m in rows:
        if m["kind"] in per_kind:
            if per_kind[m["kind"]] >= _TOP_ENTITIES:
                continue
            per_kind[m["kind"]] += 1
        entities.append(m)
        kept_keys.append(m["key"])

    series = {k: _ema_series(contrib[k]) for k in kept_keys}
    labels = [(start + timedelta(hours=i + 1))
              .isoformat(timespec="seconds").replace("+00:00", "Z")
              for i in range(n)]

    return {
        "generated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "window_hours": window_hours,
        "half_life_hours": _HALF_LIFE_H,
        "log_count": log_count,
        "series_labels": labels,
        "series": series,
        "entities": entities,
    }


if __name__ == "__main__":
    out = compute_trends()
    print(json.dumps({
        **{k: v for k, v in out.items() if k != "series"},
        "series_sample": {
            k: out["series"][k][-8:] for k in list(out["series"])[:4]
        },
    }, indent=2, ensure_ascii=False))

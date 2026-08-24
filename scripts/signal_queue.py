"""Cross-page signal queue — turns one page's conclusions into another's candidates.

A debate that closes BULLISH on FN is, today, invisible to the earnings page.
This module is the bus that fixes that: it reads a producer's output, aggregates
it per (lane, ticker), and hands consumer pages a ranked candidate list they can
act on — click back to the originating debate, or push the ticker into the
existing protocol queue.

V1 has exactly one collector (break-news debates), but the **output contract is
source-neutral** because sector / momentum / radar are meant to become producers
too. Hence `source_refs[{source, artifact_id, event_id}]` rather than a bare
`news_ids` list: the Break News id shape is an implementation detail of one
collector and must not leak into the public API.

Discipline (CLAUDE.md 全域紀律): this is an *exploration / delivery* layer. It
only ever triggers an independent analysis. It never writes buy_threshold,
position_size or verdict, and no consumer may treat a candidate as a decision.

Read-mostly. The only file it writes is the central delivery ledger
(`signals/queue_state.json`); the dashboard server calls `compute_signal_queue()`
on demand behind a short TTL cache.

Standalone debug: `python3 scripts/signal_queue.py [--days 3] [--lane earnings]`
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Bootstrap the repo root so `scripts.break_news.store` resolves whether this is
# imported by dashboard_server or run directly. Same trick as trend_rollup.py.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.break_news import store  # noqa: E402

# ── Contract constants ───────────────────────────────────────────────
SCHEMA_VERSION = 1
SOURCE_BREAK_NEWS = "break_news"
KNOWN_SOURCES = {SOURCE_BREAK_NEWS}

# Radar is deliberately absent in V1: it is sector-shaped rather than
# ticker-shaped, and shipping it half-formed would put an unactionable lane in
# front of the user. Add it when the sector-level card design exists.
LANES = ("earnings", "invest", "momentum")

STATE_PATH = _ROOT / "signals" / "queue_state.json"

# Delivery lifecycle. `failed` is a distinct terminal state on purpose — a run
# that errored or was cancelled re-opens immediately, while `consumed` only
# applies to the exact evidence revision that produced the completed analysis.
STATUS_PENDING = "pending"
STATUS_QUEUED = "queued"
STATUS_CONSUMED = "consumed"
STATUS_FAILED = "failed"
STATUS_DISMISSED = "dismissed"

# ── Scan / scoring tunables ──────────────────────────────────────────
_USABLE_STATES = {"closed", "partial_closed"}   # same set as trend_rollup
DEFAULT_WINDOW_DAYS = 3
MAX_WINDOW_DAYS = 7
MIN_MATERIALITY = 2.0        # below this the debate is not worth a page slot
MIN_SCORE = 12.0
SINGLE_HIT_MIN_MATERIALITY = 3.0   # one MEDIUM 2.5 item is noise, not a signal
MAX_TICKERS_PER_EVENT = 8    # more than this is a theme, not a ticker signal
_HALF_LIFE_H = 12.0          # matches trend_rollup._HALF_LIFE_H
_SCORE_SCALE = 1.5
_CONFLICT_MIN_HITS = 3
_CONFLICT_AGREEMENT = 0.5

_CRED_MULT = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.4}

# Direction predicates. CATALYST_FOR / MENTIONED_IN / COMPETES_WITH are
# deliberately excluded: they say a ticker is *involved*, not which way.
_BULL_PREDICATES = {"BENEFITS_FROM"}
_BEAR_PREDICATES = {"HEADWIND_FROM"}

_VERDICT_DIRECTION = {"BULLISH": "bullish", "BEARISH": "bearish"}

# Mirrors dashboard_server._TICKER_RE. `merged_entities.tickers` is raw model
# output, so it carries "N/A", lowercase words and "ticker:NVDA" prefixes.
_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,5}$")
_ARTIFACT_RE = {SOURCE_BREAK_NEWS: re.compile(r"^bn_\d{8}_[0-9a-f]{8}$")}
_CANDIDATE_ID_RE = re.compile(r"^(%s):([A-Z][A-Z0-9.\-]{0,5})$" % "|".join(LANES))

_EARNINGS_HEADLINE_RE = re.compile(
    r"\b(Q[1-4]|results|earnings|guidance|beats?|misses?|EPS|revenue)\b", re.I)

# Re-arm thresholds — a dismissal is bound to what was known at the time.
_REARM_SCORE_DELTA = 15.0
_REARM_MATERIALITY = 3.0

# Ledger hygiene.
_STATE_MAX_AGE_DAYS = 30
_STATE_MAX_ENTRIES = 500
_MAX_REFS = 100
_MAX_CONSUMED_BY = 10

_state_lock = threading.Lock()


# ── Small helpers ────────────────────────────────────────────────────
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso(dt: datetime | None = None) -> str:
    return (dt or _utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dt(value: Any) -> datetime | None:
    """Parse the several timestamp shapes the logs carry, always to aware UTC."""
    if not value or not isinstance(value, str):
        return None
    txt = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(txt)
    except ValueError:
        return None
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(f) or math.isinf(f) else f


def normalize_ticker(value: Any) -> str | None:
    """Strip the `ticker:` node prefix the graph relations use, then validate."""
    if not isinstance(value, str):
        return None
    txt = value.strip().upper()
    if txt.startswith("TICKER:"):
        txt = txt[7:]
    return txt if _TICKER_RE.match(txt) else None


def valid_artifact_id(source: str, artifact_id: Any) -> bool:
    """Gate every id that will be used to build a filesystem path."""
    pattern = _ARTIFACT_RE.get(source)
    return bool(pattern and isinstance(artifact_id, str) and pattern.match(artifact_id))


def parse_candidate_id(candidate_id: Any) -> tuple[str, str] | None:
    if not isinstance(candidate_id, str):
        return None
    m = _CANDIDATE_ID_RE.match(candidate_id.strip())
    return (m.group(1), m.group(2)) if m else None


def _revision(event_ids: list[str]) -> str:
    """Stable digest of the contributing event set.

    Bound to accept / dismiss / consumed so a genuinely new catalyst (a changed
    event set) is not silenced by a dismissal aimed at the previous one.
    """
    joined = ",".join(sorted(event_ids))
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:12]


# ── Producer: break-news collector ───────────────────────────────────
def _window_paths(window_days: int, now: datetime) -> list[Path]:
    """Glob per calendar day rather than `bn_*.json`.

    The archive is 5000+ files and grows ~100/day, so a full glob is O(all
    history) for a 3-day question. One extra trailing day is included because
    `news_id` carries the *fetch* date: a debate that closes after UTC midnight
    still lives under the previous day's filename.
    """
    paths: list[Path] = []
    for back in range(window_days + 1):
        stamp = (now - timedelta(days=back)).strftime("%Y%m%d")
        paths.extend(store.STORE_DIR.glob(f"bn_{stamp}_*.json"))
    return paths


def scan_signature(window_days: int = DEFAULT_WINDOW_DAYS,
                   now: datetime | None = None) -> tuple:
    """Cheap `stat()`-only fingerprint of the inputs, for cache invalidation.

    Lets the server recompute the instant a debate closes or the user dismisses
    something, instead of serving a stale queue for the rest of the TTL.
    """
    now = now or _utc_now()
    count = 0
    newest = 0.0
    for path in _window_paths(_clamp_days(window_days), now):
        try:
            newest = max(newest, path.stat().st_mtime)
            count += 1
        except OSError:
            continue
    try:
        state_mtime = STATE_PATH.stat().st_mtime
    except OSError:
        state_mtime = 0.0
    return (count, round(newest, 3), round(state_mtime, 3))


def _clamp_days(window_days: Any) -> int:
    try:
        days = int(window_days)
    except (TypeError, ValueError):
        return DEFAULT_WINDOW_DAYS
    return max(1, min(MAX_WINDOW_DAYS, days))


def _ticker_directions(summary: dict) -> dict[str, str]:
    """Per-ticker direction from the merged relations.

    This is the difference between a useful queue and a misleading one. A
    "Hormuz shipping disruption" debate closes BULLISH and names XOM, CVX, DAL
    and UAL; sticking the event verdict on all four marks the airlines as buys
    when the same debate says they take the headwind. Measured on real logs:
    24% of multi-ticker mentions carry a direction opposite to the event verdict.
    """
    out: dict[str, str] = {}
    for rel in summary.get("merged_relations") or []:
        if not isinstance(rel, dict):
            continue
        ticker = normalize_ticker(rel.get("subject"))
        if not ticker:
            continue
        predicate = str(rel.get("predicate") or "").upper()
        if predicate in _BULL_PREDICATES:
            out.setdefault(ticker, "bullish")
        elif predicate in _BEAR_PREDICATES:
            out.setdefault(ticker, "bearish")
    return out


def _collect_break_news(window_days: int, now: datetime,
                        dropped: dict[str, int]) -> list[dict]:
    """Return one normalized event per cluster, newest representative wins."""
    by_event: dict[str, dict] = {}
    scanned = 0

    for path in _window_paths(window_days, now):
        scanned += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            dropped["unreadable"] = dropped.get("unreadable", 0) + 1
            continue
        if not isinstance(data, dict):
            continue
        if data.get("state") not in _USABLE_STATES:
            continue

        summary = data.get("summary") or {}
        if not summary:
            continue
        verdict = str(summary.get("consensus_verdict") or "").upper()
        event_direction = _VERDICT_DIRECTION.get(verdict)
        if event_direction is None:
            dropped["neutral_split"] = dropped.get("neutral_split", 0) + 1
            continue

        triage = data.get("triage") or {}
        materiality = _as_float(triage.get("materiality_score"))
        if materiality < MIN_MATERIALITY:
            dropped["low_materiality"] = dropped.get("low_materiality", 0) + 1
            continue

        news_id = str(data.get("news_id") or path.stem)
        if not valid_artifact_id(SOURCE_BREAK_NEWS, news_id):
            dropped["bad_artifact"] = dropped.get("bad_artifact", 0) + 1
            continue

        entities = summary.get("merged_entities") or {}
        tickers: list[str] = []
        for raw in entities.get("tickers") or []:
            ticker = normalize_ticker(raw)
            if ticker is None:
                dropped["bad_ticker"] = dropped.get("bad_ticker", 0) + 1
            elif ticker not in tickers:
                tickers.append(ticker)
        if not tickers:
            continue
        if len(tickers) > MAX_TICKERS_PER_EVENT:
            dropped["too_many_tickers"] = dropped.get("too_many_tickers", 0) + 1
            # Source order is not relevance order. Keeping the first eight turns
            # a broad market recap into an arbitrary ticker signal, which is the
            # exact failure the cap exists to prevent.
            continue

        src = data.get("source") or {}
        cluster = data.get("cluster") or {}
        # `published` is the market-relevant clock; `closed_at` is when the
        # committee actually reached the verdict; `fetched_at` is the floor.
        when = (_parse_dt(src.get("published"))
                or _parse_dt(summary.get("closed_at"))
                or _parse_dt(data.get("fetched_at"))
                or now)

        cluster_id = str(cluster.get("cluster_id") or "") or None
        event_key = cluster_id or news_id
        event = {
            "source": SOURCE_BREAK_NEWS,
            "event_key": event_key,
            "artifact_id": news_id,
            "cluster_id": cluster_id,
            "direction": event_direction,
            "verdict": verdict,
            "materiality": materiality,
            "credibility": str(src.get("credibility") or "MEDIUM").upper(),
            "echo": max(1, int(_as_float(cluster.get("echo_count"), 1.0)) or 1),
            "members": 1,
            "when": when,
            "tickers": tickers,
            "directions": _ticker_directions(summary),
            "news_type": str(triage.get("news_type") or ""),
            "content_genre": str(triage.get("content_genre") or ""),
            "sectors": [str(s) for s in (entities.get("sectors") or []) if s],
            "themes": [str(t) for t in (entities.get("themes") or []) if t],
            "headline": str(data.get("headline") or ""),
            "headline_zh": data.get("headline_zh"),
            "source_name": str(src.get("name") or ""),
            "url": str(src.get("url") or ""),
            "published": src.get("published") or data.get("fetched_at"),
            "final_take": str(summary.get("final_take") or "")[:400],
            "consumed_by": data.get("consumed_by") or [],
        }

        prior = by_event.get(event_key)
        if prior is None:
            by_event[event_key] = event
        else:
            # Same story from several outlets: one event, and the highest-
            # materiality member speaks for it. Echo counts the syndication.
            prior["members"] += 1
            prior["echo"] = max(prior["echo"], event["echo"], prior["members"])
            if materiality > prior["materiality"]:
                event["members"] = prior["members"]
                event["echo"] = prior["echo"]
                by_event[event_key] = event

    dropped["_scanned_files"] = scanned
    return list(by_event.values())


# ── Lane routing ─────────────────────────────────────────────────────
def _lanes_for(event: dict) -> set[str]:
    """Which consumer pages care about this event.

    Routing is per event; an event may legitimately feed more than one lane, and
    each lane aggregates independently (the candidate key carries the lane).
    """
    lanes: set[str] = set()
    news_type = event["news_type"]
    genre = event["content_genre"]

    is_earnings = (
        news_type == "earnings"
        or genre in ("earnings_preview", "research_commentary")
        # triage mislabels some "Baidu Q2 results preview" items as `corporate`;
        # the headline is the backstop. `content_genre` is 22% null in real
        # logs, so it can only ever supplement, never gate.
        #
        # The ticker cap is what keeps the regex honest: a market recap
        # ("Stock Market Today: ... as investors await earnings") names a dozen
        # symbols and matched on a word that was about none of them. A genuine
        # earnings story is about one or two companies.
        or (len(event["tickers"]) <= 2
            and bool(_EARNINGS_HEADLINE_RE.search(event["headline"])))
    )
    if is_earnings:
        lanes.add("earnings")

    # Not `elif`: an earnings item stays out of the invest lane on purpose. The
    # invest protocol is a 60-minute LLM run; spending it on something the $0
    # earnings skill already covers is the expensive kind of duplicate.
    if not is_earnings and (
        news_type in ("corporate", "sector_news")
        or (len(event["tickers"]) == 1 and event["materiality"] >= 3.0)
    ):
        lanes.add("invest")

    # Momentum is display-only in V1 (see the module docstring on discipline):
    # the lane surfaces "we should be watching this", and the card deep-links
    # into the screener rather than running anything.
    if news_type == "sentiment" or event["echo"] >= 3 or event["materiality"] >= 3.5:
        lanes.add("momentum")

    return lanes


# ── Aggregation ──────────────────────────────────────────────────────
def _event_weight(event: dict, n_tickers: int, now: datetime) -> float:
    age_h = max(0.0, (now - event["when"]).total_seconds() / 3600.0)
    recency = 0.5 ** (age_h / _HALF_LIFE_H)
    cred = _CRED_MULT.get(event["credibility"], 0.7)
    echo_mult = 1.0 + 0.25 * min(event["echo"] - 1, 4)
    spread = 1.0 / math.sqrt(max(1, n_tickers))
    return (event["materiality"] / 5.0) * cred * echo_mult * recency * spread


def _mention_direction(event: dict, ticker: str) -> str | None:
    """Single-ticker events inherit the verdict; multi-ticker ones must be told.

    A multi-ticker mention with no explicit relation is genuinely unknown, and
    guessing it is what produces the "airline marked bullish on an oil spike"
    failure. Dropping only the *mention* (not the whole event) keeps the 71% of
    mentions that do carry a direction — gating per event would discard 68%.
    """
    if len(event["tickers"]) == 1:
        return event["direction"]
    return event["directions"].get(ticker)


def _build_candidate(lane: str, ticker: str, mentions: list[tuple[dict, float, str]],
                     ) -> dict:
    raw = sum(weight if direction == "bullish" else -weight
              for _, weight, direction in mentions)
    mass = sum(weight for _, weight, _ in mentions)
    agreement = abs(raw) / mass if mass > 0 else 0.0
    hits = len(mentions)
    score = round(100.0 * math.tanh(abs(raw) / _SCORE_SCALE)
                  * (0.5 + 0.5 * agreement), 1)

    events = [event for event, _, _ in mentions]
    bullish_hits = sum(1 for _, _, d in mentions if d == "bullish")
    ordered = sorted(mentions, key=lambda m: m[1], reverse=True)
    times = [event["when"] for event in events]

    sectors: list[str] = []
    themes: list[str] = []
    news_types: dict[str, int] = {}
    consumed_by: list[dict] = []
    for event in events:
        for s in event["sectors"]:
            if s not in sectors:
                sectors.append(s)
        for t in event["themes"]:
            if t not in themes:
                themes.append(t)
        if event["news_type"]:
            news_types[event["news_type"]] = news_types.get(event["news_type"], 0) + 1
        for record in event["consumed_by"]:
            if isinstance(record, dict) and record.get("ticker") == ticker:
                consumed_by.append(record)

    return {
        "candidate_id": f"{lane}:{ticker}",
        "revision": _revision([event["event_key"] for event in events]),
        "lane": lane,
        "ticker": ticker,
        "direction": "bullish" if raw > 0 else "bearish",
        "score": score,
        "hits": hits,
        "raw_mentions": sum(event["members"] for event in events),
        "agreement": round(agreement, 3),
        "conflict": agreement < _CONFLICT_AGREEMENT and hits >= _CONFLICT_MIN_HITS,
        "bullish_hits": bullish_hits,
        "bearish_hits": hits - bullish_hits,
        "max_materiality": round(max(event["materiality"] for event in events), 2),
        "top_credibility": max((event["credibility"] for event in events),
                               key=lambda c: _CRED_MULT.get(c, 0.0)),
        "first_seen": _utc_iso(min(times)),
        "last_seen": _utc_iso(max(times)),
        "sectors": sectors[:6],
        "themes": themes[:8],
        "news_types": news_types,
        "source_refs": [{"source": event["source"],
                         "artifact_id": event["artifact_id"],
                         "event_id": event["event_key"]}
                        for event in events][:_MAX_REFS],
        "evidence": [{
            "artifact_id": event["artifact_id"],
            "headline": event["headline"],
            "headline_zh": event["headline_zh"],
            "source_name": event["source_name"],
            "credibility": event["credibility"],
            "url": event["url"],
            "published": event["published"],
            "verdict": event["verdict"],
            "materiality": event["materiality"],
            "direction": direction,
            "final_take": event["final_take"],
        } for event, _, direction in ordered[:3]],
        "consumed_by": consumed_by[:_MAX_CONSUMED_BY],
    }


def _suppress(candidate: dict, min_score: float) -> bool:
    if candidate["score"] < min_score:
        return True
    # A lone MEDIUM-credibility 2.5-materiality item is one outlet having an
    # opinion, not a signal worth a slot on someone's page.
    return candidate["hits"] == 1 and candidate["max_materiality"] < SINGLE_HIT_MIN_MATERIALITY


def compute_signal_queue(window_days: int = DEFAULT_WINDOW_DAYS,
                         now: datetime | None = None,
                         min_score: float = MIN_SCORE,
                         include_dismissed: bool = False,
                         limit: int = 20,
                         lanes: tuple[str, ...] = LANES) -> dict:
    """Aggregate producer output into per-lane candidate lists."""
    now = now or _utc_now()
    window_days = _clamp_days(window_days)
    dropped: dict[str, int] = {}

    events = _collect_break_news(window_days, now, dropped)
    scanned_files = dropped.pop("_scanned_files", 0)

    # (lane, ticker) -> [(event, weight, direction)]
    buckets: dict[tuple[str, str], list[tuple[dict, float, str]]] = {}
    for event in events:
        event_lanes = _lanes_for(event) & set(lanes)
        if not event_lanes:
            continue
        weight = _event_weight(event, len(event["tickers"]), now)
        for ticker in event["tickers"]:
            direction = _mention_direction(event, ticker)
            if direction is None:
                dropped["ambiguous_ticker_direction"] = (
                    dropped.get("ambiguous_ticker_direction", 0) + 1)
                continue
            for lane in event_lanes:
                buckets.setdefault((lane, ticker), []).append((event, weight, direction))

    state = load_state()
    out: dict[str, list[dict]] = {lane: [] for lane in lanes}
    for (lane, ticker), mentions in buckets.items():
        candidate = _build_candidate(lane, ticker, mentions)
        if _suppress(candidate, min_score):
            dropped["low_score"] = dropped.get("low_score", 0) + 1
            continue
        delivery = _delivery_for(candidate, state.get("entries", {}))
        if delivery["status"] == STATUS_DISMISSED and not include_dismissed:
            dropped["dismissed"] = dropped.get("dismissed", 0) + 1
            continue
        candidate["delivery"] = delivery
        out[lane].append(candidate)

    for lane in out:
        out[lane].sort(key=lambda c: c["score"], reverse=True)
        del out[lane][max(1, min(50, int(limit))):]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_iso(now),
        "window_days": window_days,
        "scanned_files": scanned_files,
        "usable_events": len(events),
        "lanes": out,
        "counts": {lane: len(items) for lane, items in out.items()},
        "dropped": dropped,
    }


def find_candidate(candidate_id: str, window_days: int = DEFAULT_WINDOW_DAYS,
                   now: datetime | None = None) -> dict | None:
    """Re-derive one candidate server-side.

    Every action re-computes rather than trusting what the client echoes back.
    The evidence list decides which artifacts get written to, so accepting the
    client's copy would let a caller name any file it liked.
    """
    parsed = parse_candidate_id(candidate_id)
    if parsed is None:
        return None
    lane, _ = parsed
    queue = compute_signal_queue(window_days, now=now, min_score=0.0,
                                 include_dismissed=True, limit=50, lanes=(lane,))
    for candidate in queue["lanes"].get(lane, []):
        if candidate["candidate_id"] == candidate_id:
            return candidate
    return None


# Which protocols a lane is allowed to launch. A lane that is display-only has
# no entry, so an accept on it cannot start a run no matter what is posted.
LANE_PROTOCOLS = {
    "earnings": {"earnings", "earnings_preview"},
    "invest": {"invest"},
}


# ── Delivery ledger ──────────────────────────────────────────────────
def _empty_state() -> dict:
    return {"schema_version": SCHEMA_VERSION, "updated_at": _utc_iso(), "entries": {}}


def load_state() -> dict:
    """Read the ledger, treating a corrupt file as empty.

    Losing dismiss history is a nuisance; refusing to serve the queue because a
    bookkeeping file got truncated would be a self-inflicted outage.
    """
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return _empty_state()
    if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
        return _empty_state()
    return data


def _prune(entries: dict, now: datetime) -> dict:
    cutoff = now - timedelta(days=_STATE_MAX_AGE_DAYS)
    kept = {}
    for key, entry in entries.items():
        if not isinstance(entry, dict) or parse_candidate_id(key) is None:
            continue
        at = _parse_dt(entry.get("at"))
        if at is not None and at < cutoff:
            continue
        kept[key] = entry
    if len(kept) > _STATE_MAX_ENTRIES:
        ordered = sorted(kept.items(),
                         key=lambda kv: str(kv[1].get("at") or ""), reverse=True)
        kept = dict(ordered[:_STATE_MAX_ENTRIES])
    return kept


def _save_state(state: dict, now: datetime) -> None:
    state["schema_version"] = SCHEMA_VERSION
    state["updated_at"] = _utc_iso(now)
    state["entries"] = _prune(state.get("entries") or {}, now)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)


def _rearm(candidate: dict, entry: dict) -> bool:
    """Should a dismissal stop applying?

    A dismissal answers "not interesting given what I just saw". Letting it
    silence the ticker forever means the next genuine catalyst never surfaces,
    so it expires when the picture materially changes.
    """
    if candidate["revision"] != entry.get("revision"):
        if candidate["max_materiality"] >= _REARM_MATERIALITY:
            return True
        if candidate["direction"] != entry.get("direction"):
            return True
    return candidate["score"] - _as_float(entry.get("score_at")) >= _REARM_SCORE_DELTA


def _delivery_for(candidate: dict, entries: dict) -> dict:
    base = {"status": STATUS_PENDING, "revision": candidate["revision"],
            "job_id": None, "at": None, "report_path": None}
    entry = entries.get(candidate["candidate_id"])
    if not isinstance(entry, dict):
        return base

    status = str(entry.get("status") or STATUS_PENDING)
    if status == STATUS_DISMISSED and _rearm(candidate, entry):
        return base
    # Failure/cancellation is retryable against the SAME evidence. Keep the
    # previous error as context, but expose `pending` so the action button comes
    # back immediately instead of waiting for a new catalyst.
    if status == STATUS_FAILED:
        return {
            **base,
            "previous_status": STATUS_FAILED,
            "previous_revision": entry.get("revision"),
            "at": entry.get("at"),
            "error": entry.get("error"),
        }
    # A completed analysis consumes one evidence revision, not the ticker for
    # life. A new event set must surface as a new candidate.
    if status == STATUS_CONSUMED and candidate["revision"] != entry.get("revision"):
        return {
            **base,
            "previous_status": STATUS_CONSUMED,
            "previous_revision": entry.get("revision"),
            "at": entry.get("at"),
        }

    return {
        "status": status,
        "revision": entry.get("revision") or candidate["revision"],
        "job_id": entry.get("job_id"),
        "at": entry.get("at"),
        "report_path": entry.get("report_path"),
        "error": entry.get("error"),
    }


def record_action(candidate_id: str, revision: str, action: str,
                  *, candidate: dict | None = None, job_id: str | None = None,
                  now: datetime | None = None) -> dict:
    """Persist an accept / dismiss. Raises ValueError on invalid input."""
    parsed = parse_candidate_id(candidate_id)
    if parsed is None:
        raise ValueError("invalid candidate_id")
    if action not in ("accept", "dismiss"):
        raise ValueError("invalid action")
    if not isinstance(revision, str) or not revision:
        raise ValueError("invalid revision")

    now = now or _utc_now()
    status = STATUS_QUEUED if action == "accept" else STATUS_DISMISSED
    entry = {
        "status": status,
        "revision": revision,
        "job_id": job_id,
        "at": _utc_iso(now),
        "report_path": None,
        "lane": parsed[0],
        "ticker": parsed[1],
        # Captured so the re-arm rule has a baseline to compare against.
        "score_at": (candidate or {}).get("score"),
        "direction": (candidate or {}).get("direction"),
        "last_seen_at": (candidate or {}).get("last_seen"),
        "source_refs": (candidate or {}).get("source_refs") or [],
    }
    with _state_lock:
        state = load_state()
        state.setdefault("entries", {})[candidate_id] = entry
        _save_state(state, now)
    return entry


def clear_action(candidate_id: str, revision: str | None = None,
                 now: datetime | None = None) -> bool:
    """Undo a dismissal — only for the revision it was made against."""
    if parse_candidate_id(candidate_id) is None:
        raise ValueError("invalid candidate_id")
    now = now or _utc_now()
    with _state_lock:
        state = load_state()
        entries = state.setdefault("entries", {})
        entry = entries.get(candidate_id)
        if not isinstance(entry, dict):
            return False
        if revision and entry.get("revision") != revision:
            return False
        del entries[candidate_id]
        _save_state(state, now)
    return True


def record_delivery(candidate_id: str, revision: str | None, *, status: str,
                    refs: Any = None, protocol: str | None = None,
                    ticker: str | None = None, report_path: str | None = None,
                    error: str | None = None, now: datetime | None = None) -> bool:
    """Close the loop after a protocol run: ledger first, then source backlink.

    Called from the protocol worker. The ledger is the authority on delivery;
    the per-artifact `consumed_by` is a backlink so the originating page can show
    what its debate produced.
    """
    parsed = parse_candidate_id(candidate_id)
    if parsed is None:
        raise ValueError("invalid candidate_id")
    if status not in (STATUS_CONSUMED, STATUS_FAILED):
        raise ValueError("invalid status")
    lane, lane_ticker = parsed
    ticker = normalize_ticker(ticker) or lane_ticker
    now = now or _utc_now()

    with _state_lock:
        state = load_state()
        entries = state.setdefault("entries", {})
        entry = entries.get(candidate_id)
        entry = dict(entry) if isinstance(entry, dict) else {}
        entry.update({
            "status": status,
            "revision": revision or entry.get("revision"),
            "at": _utc_iso(now),
            "report_path": report_path,
            "error": error,
            "lane": lane,
            "ticker": ticker,
        })
        entries[candidate_id] = entry
        _save_state(state, now)

    if status == STATUS_CONSUMED:
        _write_backlinks(refs, protocol=protocol, lane=lane, ticker=ticker,
                         report_path=report_path, now=now)
    return True


def _write_backlinks(refs: Any, *, protocol: str | None, lane: str, ticker: str,
                     report_path: str | None, now: datetime) -> None:
    """Stamp `consumed_by` onto the originating artifacts.

    Every id is re-validated here even though it came back through our own
    params: it makes a round trip through an HTTP body, and it is about to be
    turned into a filesystem path.
    """
    if not isinstance(refs, list):
        return
    record = {
        "protocol": str(protocol or "")[:40],
        "ticker": ticker,
        "lane": lane if lane in LANES else "",
        "at": _utc_iso(now),
        "report_path": str(report_path)[:300] if report_path else None,
    }
    for ref in refs[:_MAX_REFS]:
        if not isinstance(ref, dict):
            continue
        source = str(ref.get("source") or "")
        artifact_id = ref.get("artifact_id")
        if source not in KNOWN_SOURCES or not valid_artifact_id(source, artifact_id):
            continue
        if source == SOURCE_BREAK_NEWS:
            try:
                store.add_consumed_by(artifact_id, record)
            except Exception as exc:  # a backlink is cosmetic; never fatal
                sys.stderr.write(f"[signal_queue] backlink {artifact_id}: {exc}\n")


# ── Earnings eligibility ─────────────────────────────────────────────
EARNINGS_CACHE_DIR = _ROOT / "skills" / "earnings-analyst" / "cache"
_DATA_JSON = _ROOT / "Dashboard" / "data.json"
_PRE_EARNINGS_WINDOW_DAYS = 7
_EARNINGS_CACHE_TTL_DAYS = 90

ELIGIBILITY_PRE_EARNINGS = "pre_earnings_window"
ELIGIBILITY_STALE = "cache_stale"
ELIGIBILITY_CURRENT = "cache_current"
ELIGIBILITY_NONE = "no_cache"
ELIGIBILITY_UNKNOWN = "unknown"


def latest_earnings_cache(ticker: str) -> dict | None:
    """Newest `<TICKER>_<YYYY-MM-DD>.json`, excluding the infographic sibling.

    Shared with the `/api/earnings-cache/<T>` handler so the path convention
    lives in exactly one place.
    """
    ticker = normalize_ticker(ticker) or ""
    if not ticker:
        return None
    candidates = [p for p in EARNINGS_CACHE_DIR.glob(f"{ticker}_*.json")
                  if not p.name.endswith(".infographic.json")]
    if not candidates:
        return None
    newest = max(candidates, key=lambda p: p.name)
    try:
        data = json.loads(newest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    # Best-effort: a path that will not relativise (a relocated cache dir, a
    # symlink out of the tree) is a cosmetic loss. Letting it raise would take
    # the whole eligibility answer down to `unknown` and disable every button.
    try:
        data["_path"] = str(newest.relative_to(_ROOT))
    except ValueError:
        data["_path"] = str(newest)
    data.setdefault("as_of_date", newest.stem.split("_", 1)[-1])
    return data


def _fmp_earnings_dates() -> dict[str, list[str]]:
    """ticker -> confirmed earnings dates, from the calendar the pages already use.

    Deliberately reads `data.json` rather than calling FMP: this feature must not
    add a network dependency to a page render, and the daily pipeline already
    keeps this fresh. If it is missing, eligibility degrades to cache-only.
    """
    try:
        data = json.loads(_DATA_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    out: dict[str, list[str]] = {}
    for event in (data.get("upcoming_events") or []):
        if not isinstance(event, dict) or event.get("category") != "earnings":
            continue
        merged = ((event.get("source_payload") or {}).get("_merged_from_sources")
                  if isinstance(event.get("source_payload"), dict) else None)
        confirmed = (event.get("source") == "fmp-earnings"
                     or (isinstance(merged, list) and "fmp-earnings" in merged))
        date = event.get("date")
        if not confirmed or not date:
            continue
        for raw in (event.get("tickers") or []):
            ticker = normalize_ticker(raw)
            if ticker:
                out.setdefault(ticker, []).append(str(date))
    return out


def _days_between(target: str, today: str) -> int | None:
    try:
        a = datetime.strptime(target, "%Y-%m-%d").date()
        b = datetime.strptime(today, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
    return (a - b).days


def earnings_eligibility(ticker: str, *, calendar: dict | None = None,
                         now: datetime | None = None) -> dict:
    """Should the earnings button run, preview, or stand down?

    The user-facing rule is "if it is the same quarter we already analysed, do
    not fetch again". Precedence is pre_earnings > stale > current > none: a
    report due to be superseded within a week is worse than no report.
    """
    now = now or _utc_now()
    today = now.strftime("%Y-%m-%d")
    normalized = normalize_ticker(ticker)
    if not normalized:
        return {"state": ELIGIBILITY_UNKNOWN, "ticker": ticker}

    calendar = _fmp_earnings_dates() if calendar is None else calendar
    dates = sorted(calendar.get(normalized) or [])
    future = [(d, _days_between(d, today)) for d in dates]
    future = [(d, n) for d, n in future if n is not None and n >= 0]
    past = [d for d in dates
            if (_days_between(d, today) or 0) < 0]

    try:
        cache = latest_earnings_cache(normalized)
    except Exception:
        return {"state": ELIGIBILITY_UNKNOWN, "ticker": normalized}

    out: dict[str, Any] = {
        "ticker": normalized,
        "days_until": future[0][1] if future else None,
        "next_earnings_date": future[0][0] if future else None,
        "as_of_date": (cache or {}).get("as_of_date"),
        "last_earnings_date": (cache or {}).get("last_earnings_date"),
        "report_path": (cache or {}).get("report_path"),
        "cache_age_days": None,
    }

    if future and future[0][1] <= _PRE_EARNINGS_WINDOW_DAYS:
        out["state"] = ELIGIBILITY_PRE_EARNINGS
        return out

    if cache is None:
        out["state"] = ELIGIBILITY_NONE
        return out

    as_of = str(cache.get("as_of_date") or "")
    age = _days_between(today, as_of)
    out["cache_age_days"] = age if age is not None and age >= 0 else None

    # Compare against `as_of` (when we ran the analysis), NOT against
    # `last_earnings_date`. Those two dates measure different things: the cache
    # field is the fiscal period END from the income statement (AMZN: 2026-06-30)
    # while the calendar carries the ANNOUNCEMENT date (2026-07-31). Comparing
    # them marks a perfectly current report stale roughly every quarter, because
    # the announcement always postdates the period it reports on. "Did a company
    # report after we last looked?" is the question, and `as_of` answers it.
    superseded = bool(as_of) and any(d > as_of for d in past)
    expired = (out["cache_age_days"] is not None
               and out["cache_age_days"] > _EARNINGS_CACHE_TTL_DAYS)
    if superseded or expired or not as_of:
        out["state"] = ELIGIBILITY_STALE
        return out

    out["state"] = ELIGIBILITY_CURRENT
    return out


def attach_eligibility(queue: dict, now: datetime | None = None) -> dict:
    """Embed eligibility into earnings-lane candidates — one request, not N."""
    candidates = (queue.get("lanes") or {}).get("earnings") or []
    if not candidates:
        return queue
    calendar = _fmp_earnings_dates()
    for candidate in candidates:
        candidate["eligibility"] = earnings_eligibility(
            candidate["ticker"], calendar=calendar, now=now)
    return queue


# ── Debug entrypoint ─────────────────────────────────────────────────
def _main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Debug dump of the cross-page signal queue")
    ap.add_argument("--days", type=int, default=DEFAULT_WINDOW_DAYS,
                    help=f"Lookback window in days (1-{MAX_WINDOW_DAYS})")
    ap.add_argument("--lane", choices=LANES, help="Restrict output to one lane")
    ap.add_argument("--json", action="store_true", help="Dump the raw payload")
    args = ap.parse_args(argv)

    lanes = (args.lane,) if args.lane else LANES
    queue = attach_eligibility(compute_signal_queue(args.days, lanes=lanes))
    if args.json:
        print(json.dumps(queue, ensure_ascii=False, indent=2))
        return 0

    print(f"scanned={queue['scanned_files']} events={queue['usable_events']} "
          f"window={queue['window_days']}d")
    print(f"dropped={queue['dropped']}")
    for lane, items in queue["lanes"].items():
        print(f"\n── {lane} ({len(items)}) ──")
        for c in items:
            flag = " ⚠conflict" if c["conflict"] else ""
            elig = f"  [{c.get('eligibility', {}).get('state', '-')}]" if lane == "earnings" else ""
            print(f"  {c['score']:5.1f}  {c['ticker']:<6} {c['direction']:<8} "
                  f"hits={c['hits']}/{c['raw_mentions']} agree={c['agreement']}{flag}{elig}")
            print(f"         {c['evidence'][0]['headline'][:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))

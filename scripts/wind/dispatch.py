#!/usr/bin/env python3
"""Hourly dispatcher: pick the most-accelerated term, scan it, cool it down.

    python3 scripts/wind/dispatch.py --once --dry-run   # what would run, and what it costs
    python3 scripts/wind/dispatch.py --once             # one real scan
    python3 scripts/wind/dispatch.py --term ticker:RCAT # force one term (dashboard button)
    python3 scripts/wind/dispatch.py --interval 3600    # resident loop
    python3 scripts/wind/dispatch.py --status           # budget + queue head

WHAT ONE TICK DOES. Rebuild the heat container → take the single most
accelerated eligible term → pre-authorize one scan against both ceilings → run
the last30days engine headless → drop off-topic items the engine has no filter
for → write the scan artifact → mark the term scanned and start its cooldown.

A tick with nothing eligible costs $0 and writes nothing but the container.
That is the same "no work, no spend" property the X KOL collector already
proved in production; it is what makes an hourly cadence affordable.

WHY WE POST-FILTER. The engine has no general topic allowlist — verified
2026-08-16 by reading it: the only keyword gates are --polymarket-keywords and
--amazon-query, both single-source. X gets a real judge (lib/x_judge.py) but it
is skipped on --quick, and TikTok/Instagram get none at all (lib/tiktok.py:430
and lib/instagram.py:478 append a creator's whole timeline). We exclude those
two lanes outright and still filter what comes back, because a resolved handle
drags its author's unrelated posts along on every platform.

DISCIPLINE. Exploration layer. Writes only news/wind_logs/. Never launches
`分析 [TICKER]` — that gate stays human, in scripts/x_kol/heat.py. Never
touches Dashboard/market_mood.json atmosphere indicators or Nexus. Lead-lag
criteria are pre-registered in docs/wind_evaluation_criteria.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.wind import budget as budget_mod  # noqa: E402
from scripts.wind import terms as terms_mod  # noqa: E402

_TOKEN_RE = re.compile(r"[A-Za-z0-9$#]+")
REASONING_ADAPTER = ROOT / "scripts" / "wind" / "reasoning_adapter.py"
_REASONING_API_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_GENAI_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
)
_STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "から", "stock", "stocks",
    "market", "markets", "news", "investor", "discussion", "about",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


def _stamp() -> str:
    return _now().strftime("%Y%m%dT%H%M%SZ")


# ── daemon heartbeat ─────────────────────────────────────────────────────
# Only the resident loop writes this. `--once`, `--term` and the dashboard's
# scan button are one-shot ticks with no next round, and stamping a
# `next_tick_at` from them would put a countdown on the page for a daemon that
# does not exist — a clock that keeps ticking after the thing it measures is
# gone is worse than no clock.
HEARTBEAT_NAME = "wind_daemon.json"


def heartbeat_path(config: dict) -> Path:
    return ROOT / config["heat"]["scans_dir"] / HEARTBEAT_NAME


def write_heartbeat(config: dict, **fields) -> dict:
    """Merge `fields` into the heartbeat and write it atomically.

    Merging rather than overwriting keeps `started_at` / `tick_count` alive
    across the two writes each round makes (one entering the tick, one entering
    the sleep) without the caller having to carry them.
    """
    path = heartbeat_path(config)
    try:
        with open(path, encoding="utf-8") as fp:
            state = json.load(fp)
    except (OSError, json.JSONDecodeError):
        state = {}
    state.update(fields)
    state["written_at"] = _now_iso()
    terms_mod.save_terms(path, state)   # generic atomic JSON write
    return state


def read_heartbeat(config: dict) -> dict | None:
    try:
        with open(heartbeat_path(config), encoding="utf-8") as fp:
            return json.load(fp)
    except (OSError, json.JSONDecodeError):
        return None


# ── crowding heuristics ──────────────────────────────────────────────────
def _script_of(text: str) -> str:
    """Coarse writing-system bucket for one string.

    Multi-language spread is the crowding tell that mattered in the AAOI
    sample: Korean, Chinese, Thai, German and English explainers on the same
    ticker inside ten days is retail saturation, not research. Bucketing by
    Unicode block is enough to count that and costs nothing; real language ID
    would be more precise and is not worth a dependency here.
    """
    counts: dict[str, int] = {}
    for ch in text:
        if not ch.isalpha():
            continue
        try:
            name = unicodedata.name(ch)
        except ValueError:
            continue
        for prefix, bucket in (
            ("CJK", "cjk"), ("HIRAGANA", "japanese"), ("KATAKANA", "japanese"),
            ("HANGUL", "korean"), ("THAI", "thai"), ("CYRILLIC", "cyrillic"),
            ("ARABIC", "arabic"), ("DEVANAGARI", "devanagari"), ("HEBREW", "hebrew"),
            ("GREEK", "greek"),
        ):
            if name.startswith(prefix):
                counts[bucket] = counts.get(bucket, 0) + 1
                break
        else:
            counts["latin"] = counts.get("latin", 0) + 1
    if not counts:
        return "unknown"
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _tokens(text: str) -> set[str]:
    return {t.casefold().lstrip("$#") for t in _TOKEN_RE.findall(text or "")} - _STOPWORDS


def _relevance(text: str, term: str, kind: str) -> float:
    """Fraction of the term's tokens present in the item text.

    A ticker is all-or-nothing: either the symbol is in there or the item is
    about something else. A multi-word theme is scored by overlap so that
    "counter-UAS procurement" still matches "counter-UAS".
    """
    have = _tokens(text)
    want = _tokens(term)
    if not want:
        return 0.0
    if kind == "ticker":
        return 1.0 if want <= have else 0.0
    return len(want & have) / len(want)


# ── engine invocation ────────────────────────────────────────────────────
def _query_for(entry: dict) -> str:
    """Build the engine topic for one term.

    A ticker is self-anchoring. A theme is not, and appending "stocks" to it
    produces a question with no answer: `Claude stocks investor discussion`
    searches for a stock that does not exist (Anthropic is private) and returns
    AI-developer chatter — the exact failure that put a 550k-view TikTok about
    prompting technique into an AAOI report.

    So a non-ticker term is anchored by the tickers its own source articles
    filed it alongside. `Claude` becomes `Claude $AMZN $GOOGL $MSFT`, which is
    what those three Anthropic-revenue stories were actually about. With no
    co-mention to anchor on, ask about the theme itself rather than invent a
    security for it.
    """
    label = str(entry.get("display") or entry.get("term") or "").strip()
    if entry.get("kind") == "ticker":
        return f"${label} stock news and investor discussion"
    anchors = [f"${t}" for t in (entry.get("related_tickers") or [])[:3]]
    if anchors:
        return f"{label} {' '.join(anchors)} investor discussion"
    return f"{label} stock market impact"


def _engine_path(config: dict) -> Path:
    return Path(os.path.expanduser(config["dispatch"]["engine_path"])).resolve()


def _reasoning_child_env() -> dict[str, str]:
    """Force the adapter path and keep direct reasoning credentials out."""
    child_env = dict(os.environ)
    for name in _REASONING_API_ENV_VARS:
        child_env.pop(name, None)
    # Process env wins over last30days' global .env. If adapter injection ever
    # stops matching an upgraded skill, its native resolver rejects "broker"
    # instead of silently spending a key from that file.
    child_env["LAST30DAYS_REASONING_PROVIDER"] = "broker"
    return child_env


def _read_reasoning_meta(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as fp:
            payload = json.load(fp)
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def run_engine(config: dict, entry: dict, *, scratch: Path) -> tuple[dict | None, dict]:
    """Run one headless scan. Returns (agent-profile payload or None, meta)."""
    dispatch = config["dispatch"]
    engine = _engine_path(config)
    scratch.mkdir(parents=True, exist_ok=True)
    if not engine.is_file():
        return None, {
            "argv": [], "engine": str(engine), "exit_code": None,
            "error": f"engine not found at {engine}",
        }
    if not REASONING_ADAPTER.is_file():
        return None, {
            "argv": [], "engine": str(engine), "exit_code": None,
            "error": f"reasoning adapter not found at {REASONING_ADAPTER}",
        }

    fd, reasoning_meta_name = tempfile.mkstemp(
        prefix="wind_broker_", suffix=".json", dir=str(scratch),
    )
    os.close(fd)
    reasoning_meta_path = Path(reasoning_meta_name)
    argv = [
        sys.executable, str(REASONING_ADAPTER),
        "--engine", str(engine),
        "--meta-out", str(reasoning_meta_path),
        "--",
        _query_for(entry),
        "--emit=json", "--json-profile=agent",
        "--days", str(int(dispatch.get("lookback_days", 14))),
        "--search", str(dispatch.get("sources", "x,reddit,grounding,youtube,github")),
        "--save-dir", str(scratch),
    ]
    plan = dispatch.get("plan_path")
    if plan:
        argv += ["--plan", str(ROOT / plan)]

    meta = {"argv": argv[1:], "engine": str(engine)}

    started = time.time()
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True,
            timeout=float(dispatch.get("scan_timeout_sec", 600)), check=False,
            env=_reasoning_child_env(),
        )
    except subprocess.TimeoutExpired:
        meta.update({"exit_code": None, "error": "timeout",
                     "elapsed_sec": round(time.time() - started, 1)})
        return None, meta
    finally:
        reasoning = _read_reasoning_meta(reasoning_meta_path)
        if reasoning is not None:
            meta["reasoning"] = reasoning
        try:
            reasoning_meta_path.unlink()
        except OSError:
            pass

    meta["exit_code"] = proc.returncode
    meta["elapsed_sec"] = round(time.time() - started, 1)
    # exit 3 is LAST30DAYS_STRICT_EXIT signalling a degraded source, not a
    # failure — the payload is still on stdout and still worth keeping.
    if proc.returncode not in (0, 3):
        meta["error"] = (proc.stderr or "")[-800:]
        return None, meta
    try:
        return json.loads(proc.stdout), meta
    except json.JSONDecodeError:
        meta["error"] = "stdout was not JSON; " + (proc.stderr or "")[-400:]
        return None, meta


# ── artifact assembly ────────────────────────────────────────────────────
def build_artifact(config: dict, key: str, entry: dict, payload: dict, meta: dict) -> dict:
    """Filter the engine payload down to on-topic items and summarize."""
    floor = float(config["dispatch"].get("relevance_floor", 0.15))
    term = str(entry.get("display") or entry.get("term") or "")
    kind = str(entry.get("kind") or "")

    kept, dropped = [], []
    for item in payload.get("results") or []:
        text = " ".join(str(item.get(f) or "") for f in ("title", "summary", "url"))
        score = _relevance(text, term, kind)
        row = {
            "title": item.get("title"),
            "source": item.get("source"),
            "url": item.get("url"),
            "published_at": item.get("published_at"),
            "summary": item.get("summary"),
            "engagement": item.get("engagement"),
            "relevance_score": item.get("relevance_score"),
            "wind_relevance": round(score, 3),
            "language": _script_of(text),
        }
        (kept if score >= floor else dropped).append(row)

    platforms: dict[str, int] = {}
    languages: dict[str, int] = {}
    engagement: dict[str, int] = {}
    for row in kept:
        platforms[str(row.get("source"))] = platforms.get(str(row.get("source")), 0) + 1
        languages[row["language"]] = languages.get(row["language"], 0) + 1
        # The engine reports engagement per platform-native metric
        # ({likes, replies, reposts} on X, {views, likes, comments} on video
        # platforms), so keep the breakdown rather than flattening incompatible
        # units into one number — 1 view and 1 like are not the same thing.
        value = row.get("engagement")
        if isinstance(value, dict):
            for metric, count in value.items():
                if isinstance(count, (int, float)):
                    engagement[metric] = engagement.get(metric, 0) + int(count)
        elif isinstance(value, (int, float)):
            engagement["total"] = engagement.get("total", 0) + int(value)

    return {
        "version": 1,
        "key": key,
        "term": entry.get("term"),
        "display": entry.get("display"),
        "kind": kind,
        "scanned_at": _now_iso(),
        "window_days": payload.get("window_days"),
        "query": payload.get("query"),
        "score_at_scan": entry.get("score"),
        "surprise_at_scan": entry.get("surprise"),
        "mentions_at_scan": entry.get("mentions"),
        "engine": {
            "schema_version": payload.get("schema_version"),
            "exit_code": meta.get("exit_code"),
            "elapsed_sec": meta.get("elapsed_sec"),
            "degraded": meta.get("exit_code") == 3,
            "reasoning": meta.get("reasoning"),
        },
        "source_status": payload.get("source_status"),
        "freshness_verdicts": payload.get("freshness_verdicts"),
        "clusters": payload.get("clusters"),
        "filter": {
            "relevance_floor": floor,
            "kept": len(kept),
            "dropped": len(dropped),
            "dropped_titles": [d.get("title") for d in dropped[:20]],
        },
        # Raw counts only. Turning these into a crowding SCORE is exactly the
        # step docs/wind_evaluation_criteria.md forbids until the lead-lag
        # evaluation passes.
        "crowding": {
            "platform_counts": platforms,
            "language_counts": languages,
            "distinct_languages": len(languages),
            "engagement": engagement,
        },
        "results": kept,
    }


# ── one tick ─────────────────────────────────────────────────────────────
def tick(config: dict, *, dry_run: bool = False, force_key: str | None = None) -> dict:
    heat = config["heat"]
    dispatch = config["dispatch"]
    terms_path = ROOT / heat["terms_path"]
    scans_dir = ROOT / heat["scans_dir"]

    data = terms_mod.rebuild(config, path=terms_path)

    if force_key:
        entry = (data.get("terms") or {}).get(force_key)
        if entry is None:
            return {"status": "unknown_term", "key": force_key}
        picked = (force_key, entry)
    else:
        picked = terms_mod.pick_next(data, config)

    if picked is None:
        return {"status": "quiet", "checked_at": _now_iso(), "cost_usd": 0.0}

    key, entry = picked
    try:
        projected = budget_mod.check(config, scans=1)
    except budget_mod.BudgetExceeded as exc:
        return {"status": "refused", "key": key, "reason": str(exc)}

    if dry_run:
        return {
            "status": "dry_run", "key": key,
            "display": entry.get("display"), "kind": entry.get("kind"),
            "score": entry.get("score"), "surprise": entry.get("surprise"),
            "mentions": entry.get("mentions"),
            "query": _query_for(entry), "projected_cost_usd": projected,
        }

    terms_mod.set_scan_state(terms_path, key, "scanning")
    payload, meta = run_engine(config, entry, scratch=scans_dir / "raw")

    if payload is None:
        # Nothing was delivered, so nothing is booked. Return the term to the
        # queue rather than burning its cooldown on a failed call.
        terms_mod.set_scan_state(terms_path, key, "pending")
        return {"status": "engine_failed", "key": key, "meta": meta}

    artifact = build_artifact(config, key, entry, payload, meta)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(entry.get("term") or "term")).strip("-")[:40]
    out_path = scans_dir / f"wind_scan_{slug}_{_stamp()}.json"
    terms_mod.save_terms(out_path, artifact)

    budget_mod.record(config, scans=1)
    terms_mod.set_scan_state(
        terms_path, key, "scanned",
        scan_path=str(out_path.relative_to(ROOT)),
        cooldown_hours=float(dispatch.get("cooldown_hours", 24)),
        score_at_scan=entry.get("score"),
    )
    return {
        "status": "scanned", "key": key, "display": entry.get("display"),
        "kept": artifact["filter"]["kept"], "dropped": artifact["filter"]["dropped"],
        "degraded": artifact["engine"]["degraded"],
        "path": str(out_path.relative_to(ROOT)), "cost_usd": projected,
    }


def _detail_of(result: dict) -> str | None:
    """One-line human summary of a tick, for the heartbeat / dashboard.

    Deliberately not a re-derivation of `_print`: that one writes several lines
    to a log a human is tailing, this one has to fit on a status row.
    """
    status = result.get("status")
    if status == "scanned":
        detail = f"留 {result.get('kept')} 丟 {result.get('dropped')}"
        return detail + "（來源降級）" if result.get("degraded") else detail
    if status == "dry_run":
        return None
    if status == "quiet":
        return "無符合門檻的關鍵字 — $0"
    if status == "refused":
        return result.get("reason")
    if status == "engine_failed":
        return f"引擎失敗：{(result.get('meta') or {}).get('error', '未知')}"
    if status == "unknown_term":
        return f"找不到 {result.get('key')}"
    return None


def _print(result: dict, config: dict) -> None:
    status = result.get("status")
    if status == "quiet":
        print("[wind] quiet tick — nothing eligible, $0")
    elif status == "dry_run":
        print(f"[wind] would scan {result['key']} "
              f"(surprise {result.get('surprise')}, score {result.get('score')}, "
              f"{result.get('mentions')} mentions)")
        print(f"       query: {result['query']}")
        print(f"       projected cost: ${result['projected_cost_usd']:.4f}")
    elif status == "scanned":
        flag = " [degraded sources]" if result.get("degraded") else ""
        print(f"[wind] scanned {result['key']} → kept {result['kept']}, "
              f"dropped {result['dropped']}{flag}")
        print(f"       {result['path']}")
    elif status == "refused":
        print(f"[wind] {result['reason']}")
    elif status == "engine_failed":
        print(f"[wind] engine failed for {result['key']}: "
              f"{result['meta'].get('error', 'unknown')}")
    elif status == "unknown_term":
        print(f"[wind] no such term: {result['key']}")
    print(budget_mod.status_line(config))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Wind social-scan dispatcher")
    ap.add_argument("--once", action="store_true", help="run a single tick and exit")
    ap.add_argument("--interval", type=int, default=None,
                    help="resident loop, seconds between ticks (default from config)")
    ap.add_argument("--dry-run", action="store_true", help="pick and price, do not scan")
    ap.add_argument("--term", help="force a specific container key, e.g. ticker:RCAT")
    ap.add_argument("--status", action="store_true", help="budget + queue head, no work")
    args = ap.parse_args(argv)

    config = budget_mod.load_config()

    if args.status:
        data = terms_mod.load_terms(ROOT / config["heat"]["terms_path"])
        head = terms_mod.eligible(data, config)[:5]
        print(budget_mod.status_line(config))
        if not head:
            print("[wind] queue empty")
        for key, entry in head:
            print(f"  {key:<40} surprise {float(entry.get('surprise') or 0):>6.2f}"
                  f"  score {float(entry.get('score') or 0):>7.3f}")
        return 0

    if args.once or args.term or args.dry_run:
        _print(tick(config, dry_run=args.dry_run, force_key=args.term), config)
        return 0

    interval = args.interval or int(config["dispatch"].get("interval_sec", 3600))
    print(f"[wind] resident loop, every {interval}s — Ctrl-C to stop")
    write_heartbeat(config, pid=os.getpid(), started_at=_now_iso(),
                    interval_sec=interval, tick_count=0, state="ticking",
                    tick_started_at=_now_iso(), last_tick_at=None,
                    next_tick_at=None, last_status="starting",
                    last_key=None, last_display=None, last_detail=None)
    ticks = 0
    # The sleep must be inside the try too: the loop spends ~3599 of every 3600
    # seconds in it, so that is where Ctrl-C actually lands. With the sleep
    # outside, "stopped" was unreachable in practice and the daemon died on a
    # KeyboardInterrupt traceback instead.
    try:
        while True:
            result = None
            try:
                result = tick(config)
                _print(result, config)
            except Exception as exc:  # a bad tick must not kill the loop
                print(f"[wind] tick failed: {type(exc).__name__}: {exc}", file=sys.stderr)
                result = {"status": f"error:{type(exc).__name__}"}

            ticks += 1
            now = _now()
            write_heartbeat(
                config, state="sleeping", tick_count=ticks,
                last_tick_at=now.isoformat(timespec="seconds"),
                next_tick_at=(now + timedelta(seconds=interval)).isoformat(timespec="seconds"),
                last_status=result.get("status"), last_key=result.get("key"),
                last_display=result.get("display"), last_detail=_detail_of(result),
                scans_left_today=budget_mod.scans_left_today(config))
            time.sleep(interval)
            write_heartbeat(config, state="ticking", tick_started_at=_now_iso())
    except KeyboardInterrupt:
        print("\n[wind] stopped")
        write_heartbeat(config, state="stopped", stopped_at=_now_iso(),
                        next_tick_at=None)
        return 0


if __name__ == "__main__":
    sys.exit(main())

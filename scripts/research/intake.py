"""Shared news intake with per-source health, lineage and deterministic promotion."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from news.fetch_news_rss import FEEDS, fetch_feed, headline_fingerprint
from news.source_policy import infer_source_kind, source_priority
from scripts.break_news.cluster import extract_tickers
from scripts.break_news.poller import (_score_materiality, calc_shallow_score, classify_news_type,
                                      detect_binary_event, gate)
from scripts.research.store import CACHE, ROOT, Repository, digest, now_iso, parse_time, profile


def canonical_url(value):
    try:
        parts = urlsplit(value)
        if parts.scheme not in {"https", "http"} or not parts.hostname:
            return ""
        query = [(k, v) for k, v in parse_qsl(parts.query)
                 if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
        return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"),
                           urlencode(sorted(query)), ""))
    except (TypeError, ValueError):
        return ""


@lru_cache(maxsize=1)
def company_universe():
    """Maintained public index universe; no holdings/watchlist dependency."""
    from scripts.nexus.build_graph import load_config

    data = json.loads((ROOT / "Dashboard/heatmap_universe.json").read_text())
    rows = [r for r in data.get("tickers", []) if isinstance(r, dict)]
    names = {}
    for row in rows:
        name = re.sub(r"\s+(Corporation|Corp\.?|Inc\.?|Ltd\.?|plc)$", "", row.get("name", ""), flags=re.I)
        if len(name) >= 4:
            names[name.lower()] = row["ticker"]
    symbols = {r['ticker'] for r in rows}
    # Reuse the project's curated entity names (e.g. Micron / Google), without
    # changing Nexus promotion, holdings, or any user-maintained universe.
    for name, canonical in load_config().get('alias_map', {}).items():
        if canonical.startswith('ticker:') and canonical.split(':',1)[1] in symbols:
            names[name.lower()] = canonical.split(':',1)[1]
    return symbols, names


def research_gate(headline, summary, tickers, source_kind):
    """Require a public-company link or explicit economic transmission channel."""
    if re.search(r"\b(?:what to watch|to watch (?:this|next) week|week ahead|weekly preview|earnings preview)\b",
                 headline, re.I):
        return False, "preview_awaits_new_release"
    if source_kind not in {'company_filing','company_ir','official_macro'} and re.search(
            r"\b(?:I(?:'|’)m|I am)\s+(?:buying|selling|bullish|bearish)\b|"
            r"\bstocks?\s+to\s+(?:buy|sell)\b|\bshould you buy\b", headline, re.I):
        return False, 'opinion_requires_new_primary_evidence'
    if tickers or source_kind in {"company_filing", "company_ir", "official_macro"}:
        return True, None
    if re.search(r'\b(?:sell|sells|buy|buys|acquire|acquires)\b.{0,60}\b(?:unit|company|business|stake)\b',
                 headline, re.I):
        return True, None
    economic = (r"\b(?:inflation|payrolls?|unemployment|GDP|CPI|PCE|FOMC|Federal Reserve|"
                r"interest rates?|rate cuts?|rate hikes?|Treasur(?:y|ies)|bond yields?|"
                r"earnings|profits?|revenue|margins?|capex|capital spending|"
                r"tariffs?|exports?|imports?|sanctions?|antitrust|supply chains?|"
                r"acquisitions?|mergers?|takeovers?|buyouts?|"
                r"oil|crude|natural gas|LNG|shipping|semiconductors?|chipmakers?|"
                r"bankruptc(?:y|ies)|credit|default|liquidity|currency|currencies)\b")
    if re.search(economic, headline + " " + summary, re.I):
        return True, None
    return False, "no_identified_financial_channel"


def normalize(raw, now=None):
    now = now or datetime.now(timezone.utc)
    title = str(raw.get("headline") or "").strip()
    url = canonical_url(raw.get("url") or "")
    if not title or not url:
        return None
    summary = str(raw.get("raw_summary") or "").strip()
    published = parse_time(raw.get("published"))
    kind = "social" if raw.get("_social_source") else raw.get("source_kind") or infer_source_kind(raw.get("source", ""))
    news_type = classify_news_type(title, summary)
    shallow = calc_shallow_score(title, summary, news_type)
    materiality, credibility, genre = _score_materiality(raw, title, summary, news_type, shallow)
    eligible, reason = gate(materiality, detect_binary_event(title, summary))
    timely = published is not None and timedelta(minutes=-5) <= now - published <= timedelta(hours=6)
    if kind == "social":
        eligible, reason = False, "social_discovery_requires_primary_evidence"
    if not timely:
        eligible, reason = False, "missing_or_stale_publication_time"
    evidence_text = (title + "\n" + summary)[:6000]
    # Timestamp and retrieval provider are metadata, never excerpt content.
    evidence = {"id": "ev_" + digest(url), "url": url, "text": evidence_text,
                "source": raw.get("source", ""), "source_kind": kind,
                "content_type": "feed_excerpt", "published_at": published.isoformat() if published else None,
                "retrieved_at": now.isoformat()}
    tagged = re.split(r"[,;\s]+", str(raw.get("symbol") or raw.get("related") or ""))
    universe, company_names = company_universe()
    identified = extract_tickers(title) & universe
    provider_tickers = {t.upper() for t in tagged
                        if re.fullmatch(r"[A-Za-z][A-Za-z0-9.-]{0,9}", t)}
    for name, ticker in company_names.items():
        if re.search(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])", title + "\n" + summary, flags=re.I):
            identified.add(ticker)
    tickers = identified | provider_tickers
    # Provider associations are discovery hints, not proof of an issuer link.
    # A bad CHCO tag on a New York City AI hearing must not pass this gate.
    relevant, relevance_reason = research_gate(title, summary, identified, kind)
    if eligible and not relevant:
        eligible, reason = False, relevance_reason
    return {"id": "re_" + digest(url), "headline": title, "url": url,
            "source": raw.get("source", ""), "source_kind": kind,
            "source_priority": source_priority({**raw, "source_kind": kind})[0],
            "lineage": [raw.get("provider") or raw.get("source") or "unknown"],
            "published_at": evidence["published_at"], "received_at": now.isoformat(),
            "evidence": [evidence], "tickers": sorted(tickers)[:8],
            "identified_tickers": sorted(identified), "provider_tickers": sorted(provider_tickers),
            "trigger": "filing" if kind in {"company_filing", "company_ir"} else "news",
            "materiality": materiality, "credibility": credibility, "content_genre": genre,
            "eligible": bool(eligible), "gate_reason": reason or (
                "material_new_evidence" if eligible else "below_materiality_threshold")}


def ingest_items(repo, items, now=None):
    counts = {"received": len(items), "new_revisions": 0, "duplicates": 0, "eligible": 0,
              "invalid": 0}
    for raw in items:
        event = normalize(raw, now)
        if event is None:
            counts["invalid"] += 1
            continue
        day = (event["published_at"] or event["received_at"])[:10]
        aliases = ["url:" + event["url"], "headline:" + day + ":" + headline_fingerprint(event["headline"])]
        saved, changed = repo.ingest(event, aliases)
        counts["new_revisions" if changed else "duplicates"] += 1
        counts["eligible"] += int(changed and saved["eligible"])
    return counts


def _provider(name, script):
    """Existing provider adapters, isolated output paths: failures cannot reuse old files."""
    CACHE.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix=f"intake-{name}-", dir=CACHE) as output:
            proc = subprocess.run([sys.executable, str(ROOT / "news" / script),
                                   "--hours", "6", "--output", output],
                                  capture_output=True, timeout=90)
            if proc.returncode:
                return [], {"feed": name, "status": "error", "exit_code": proc.returncode}
            paths = list(Path(output).glob("*_raw.json"))
            if len(paths) != 1:
                return [], {"feed": name, "status": "error", "error": "missing_output"}
            data = json.loads(paths[0].read_text())
            items = [{**item, "provider": name} for item in data.get("items", [])]
            # Older adapters swallow individual endpoint failures. stderr is
            # inspected only for status and is never copied (may contain URLs).
            degraded = b"[WARN]" in proc.stderr or b"ERROR" in proc.stderr
            return items, {"feed": name, "status": "degraded" if degraded else "ok",
                           "fetched": len(items), "latency_ms": int((time.monotonic()-started)*1000)}
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return [], {"feed": name, "status": "error", "error": type(exc).__name__}


def _discovery(name):
    """Keep optional social/local adapters outside the worker's failure domain.

    macOS can block a background process inside opendir for a protected local
    source indefinitely; requests' network timeouts cannot bound that wait.
    """
    label = "Futu Push" if name == "futu" else "Social"
    started = time.monotonic()
    try:
        proc = subprocess.run([sys.executable, "-m", "scripts.research.discovery", name],
                              cwd=ROOT, capture_output=True, timeout=15 if name == "futu" else 90)
        if proc.returncode:
            return [], {"feed": label, "status": "error", "exit_code": proc.returncode}
        payload = json.loads(proc.stdout)
        return payload["items"], {"feed": label, "status": payload["status"],
                                  "fetched": len(payload["items"]),
                                  "adapters": payload["adapters"],
                                  "latency_ms": int((time.monotonic()-started)*1000)}
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        return [], {"feed": label, "status": "error", "error": type(exc).__name__,
                    "latency_ms": int((time.monotonic()-started)*1000)}


def poll(repo=None):
    repo = repo or Repository()
    settings = profile()
    previous = repo.get("source_health", {})
    now = datetime.now(timezone.utc)
    feeds = list(FEEDS) + settings.get("extra_feeds", []) + settings.get("company_feeds", [])

    def rss(feed):
        name, url, credibility = feed
        last = previous.get(name, {})
        retry = parse_time(last.get("retry_at"))
        if retry and retry > now:
            return [], {**last, "status": "backoff"}
        health = {"feed": name, "checked_at": now.isoformat()}
        started = time.monotonic()
        items = fetch_feed(name, url, credibility, health=health, conditional=last, summary_limit=4000)
        failures = int(last.get("failures", 0)) + 1 if health["status"] == "error" else 0
        health.update(failures=failures, latency_ms=int((time.monotonic()-started)*1000))
        if failures:
            health["retry_at"] = (now + timedelta(seconds=min(21600, 600*2**min(failures,5)))).isoformat()
        return items, health

    jobs = [(rss, feed) for feed in feeds]
    jobs += [(lambda pair: _provider(*pair), pair) for pair in (
        ("FMP", "fetch_fmp_news.py"), ("Finnhub", "fetch_finnhub_news.py"),
        ("SEC EDGAR", "fetch_sec_edgar.py"))]
    from scripts.break_news import poller as legacy
    if legacy.SOCIAL_ENABLED and legacy.SOCIAL_AVAILABLE:
        jobs.append((_discovery, "social"))
    if legacy.FUTU_ENABLED and legacy.FUTU_AVAILABLE:
        jobs.append((_discovery, "futu"))
    items, health = [], {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(function, arg) for function, arg in jobs]
        for future in futures:
            batch, status = future.result()
            items.extend(batch)
            health[status["feed"]] = status
    result = ingest_items(repo, items, now)
    for name, status in health.items():
        status["checked_at"] = now.isoformat()
        status["fresh"] = sum(1 for raw in items if (raw.get("provider") or raw.get("source")) == name
                              and parse_time(raw.get("published")) is not None
                              and timedelta(minutes=-5) <= now - parse_time(raw["published"]) <= timedelta(hours=6))
    repo.set("source_health", health)
    repo.set("last_poll", {"at": now_iso(), **result})
    history = repo.get("source_history", [])
    history.append({"at": now.isoformat(), "counts": result, "sources": health})
    repo.set("source_history", history[-300:])
    return result

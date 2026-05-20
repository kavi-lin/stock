"""Free social/trend source adapters for Break News.

Each adapter returns the same normalized item shape as news.fetch_news_rss:
headline, url, raw_summary, source, source_credibility, published, _fp, _dt.
These sources are noisy by design, so poller.py gates them more conservatively.
"""
from __future__ import annotations

import html
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote, urlencode

import requests
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from news.fetch_news_rss import clean_text, headline_fingerprint, parse_date  # noqa: E402

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
)
TIMEOUT = int(os.environ.get("BREAK_NEWS_SOCIAL_TIMEOUT_SEC", "12"))
MAX_TOTAL = int(os.environ.get("BREAK_NEWS_SOCIAL_MAX_TOTAL", "80"))
MAX_PER_SOURCE = int(os.environ.get("BREAK_NEWS_SOCIAL_MAX_PER_SOURCE", "20"))
MAX_PER_QUERY = int(os.environ.get("BREAK_NEWS_SOCIAL_MAX_PER_QUERY", "5"))
TRUTH_SOCIAL_ENABLED = os.environ.get("BREAK_NEWS_TRUTH_SOCIAL_ENABLED", "1").lower() not in ("0", "false", "no")
TRUTH_SOCIAL_MAX_PER_CYCLE = int(os.environ.get("BREAK_NEWS_TRUTH_SOCIAL_MAX_PER_CYCLE", "10"))

DEFAULT_REDDIT_SUBS = [
    "stocks", "investing", "wallstreetbets", "options",
    "SecurityAnalysis", "technology", "artificial", "LocalLLaMA",
]
DEFAULT_BLUESKY_QUERIES = [
    "$NVDA OR Nvidia",
    "$AMD OR semiconductors",
    "$TSM OR TSMC",
    "\"AI capex\" OR \"data center\"",
    "\"rate cuts\" OR inflation",
    "\"uranium\" OR \"nuclear power\"",
]
DEFAULT_HN_QUERIES = [
    "nvidia", "semiconductor", "\"data center\"", "openai",
    "\"AI agent\"", "robotics", "cloud gpu", "nuclear power",
]
DEFAULT_TRUTH_SOCIAL_HANDLES = ["realDonaldTrump"]
MARKET_TERMS = [
    "stock", "stocks", "market", "markets", "nasdaq", "s&p", "sp500",
    "dow", "rates", "fed", "inflation", "earnings", "guidance", "ipo",
    "ai", "semiconductor", "chip", "gpu", "data center", "nuclear",
    "uranium", "robotics", "cloud", "bitcoin", "crypto",
]


def _split_env(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        return default
    vals = [x.strip() for x in raw.split(",") if x.strip()]
    return vals or default


def _http_get(url: str, **params):
    if params:
        url = url + ("&" if "?" in url else "?") + urlencode(params)
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    return r


def _parse_rfc3339_or_rfc822(s: str):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    dt = parse_date(s)
    if dt is not None:
        return dt
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _iso(dt) -> str | None:
    return dt.astimezone(timezone.utc).isoformat() if dt else None


def _social_item(source: str, headline: str, url: str, summary: str,
                 published_dt, credibility: str = "LOW", meta: dict | None = None) -> dict | None:
    headline = clean_text(html.unescape(headline or ""))
    summary = clean_text(html.unescape(summary or ""))
    if not headline:
        return None
    return {
        "headline": headline[:240],
        "url": url or "",
        "raw_summary": summary[:500],
        "source": source,
        "source_credibility": credibility,
        "published": _iso(published_dt),
        "_fp": headline_fingerprint(headline),
        "_dt": published_dt,
        "_social_source": True,
        "_source_meta": meta or {},
    }


def _within(dt, cutoff) -> bool:
    return dt is None or dt >= cutoff


def fetch_reddit(window_hours: int) -> tuple[list[dict], dict]:
    """Fetch recent subreddit RSS entries. Anonymous Reddit RSS can be flaky;
    failures are reported in stats and do not fail the whole poll."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    subs = _split_env("BREAK_NEWS_REDDIT_SUBS", DEFAULT_REDDIT_SUBS)
    out: list[dict] = []
    errors: list[str] = []
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    def first(el, *paths):
        for path in paths:
            hit = el.find(path, ns)
            if hit is not None:
                return hit
        return None

    for sub in subs:
        if len(out) >= MAX_PER_SOURCE:
            break
        url = f"https://www.reddit.com/r/{quote(sub)}/new/.rss"
        try:
            root = etree.fromstring(
                _http_get(url).content,
                parser=etree.XMLParser(recover=True),
            )
        except Exception as e:
            errors.append(f"{sub}:{str(e)[:80]}")
            continue
        entries = root.findall(".//atom:entry", ns) or root.findall(".//entry")
        kept = 0
        for e in entries:
            if kept >= MAX_PER_QUERY or len(out) >= MAX_PER_SOURCE:
                break
            title_el = first(e, "atom:title", "title")
            sum_el = first(e, "atom:summary", "summary")
            upd_el = first(e, "atom:updated", "updated")
            link_el = first(e, "atom:link", "link")
            title = title_el.text if title_el is not None and title_el.text else ""
            summary = sum_el.text if sum_el is not None and sum_el.text else ""
            dt = _parse_rfc3339_or_rfc822(upd_el.text if upd_el is not None else "")
            if not _within(dt, cutoff):
                continue
            link = link_el.get("href") if link_el is not None else ""
            item = _social_item(
                f"Reddit:r/{sub}", title, link, summary, dt, "LOW",
                {"platform": "reddit", "subreddit": sub},
            )
            if item:
                out.append(item)
                kept += 1
    return out, {"feed": "Reddit", "fetched": len(out), "errors": errors[:5]}


def fetch_bluesky(window_hours: int) -> tuple[list[dict], dict]:
    if os.environ.get("BREAK_NEWS_BLUESKY_ENABLED", "0").lower() in ("0", "false", "no"):
        return [], {"feed": "Bluesky Search", "fetched": 0, "disabled": True}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    queries = _split_env("BREAK_NEWS_BLUESKY_QUERIES", DEFAULT_BLUESKY_QUERIES)
    out: list[dict] = []
    errors: list[str] = []
    endpoint = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
    since = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    for q in queries:
        if len(out) >= MAX_PER_SOURCE:
            break
        try:
            data = _http_get(endpoint, q=q, sort="latest", limit=MAX_PER_QUERY, since=since).json()
        except Exception as e:
            errors.append(f"{q}:{str(e)[:80]}")
            continue
        for p in data.get("posts") or []:
            if len(out) >= MAX_PER_SOURCE:
                break
            rec = p.get("record") or {}
            text = rec.get("text") or ""
            dt = _parse_rfc3339_or_rfc822(rec.get("createdAt") or p.get("indexedAt") or "")
            if not _within(dt, cutoff):
                continue
            author = p.get("author") or {}
            handle = author.get("handle") or ""
            uri = p.get("uri") or ""
            rkey = uri.rsplit("/", 1)[-1] if "/" in uri else ""
            url = f"https://bsky.app/profile/{handle}/post/{rkey}" if handle and rkey else ""
            display = author.get("displayName") or handle
            headline = f"{display}: {text}" if display else text
            item = _social_item(
                "Bluesky Search", headline, url, text, dt, "LOW",
                {"platform": "bluesky", "query": q, "handle": handle},
            )
            if item:
                out.append(item)
    return out, {"feed": "Bluesky Search", "fetched": len(out), "errors": errors[:5]}


def fetch_hacker_news(window_hours: int) -> tuple[list[dict], dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    queries = _split_env("BREAK_NEWS_HN_QUERIES", DEFAULT_HN_QUERIES)
    out: list[dict] = []
    errors: list[str] = []
    min_created = int(cutoff.timestamp())
    endpoint = "https://hn.algolia.com/api/v1/search_by_date"
    for q in queries:
        if len(out) >= MAX_PER_SOURCE:
            break
        try:
            data = _http_get(
                endpoint,
                query=q,
                tags="story",
                hitsPerPage=MAX_PER_QUERY,
                numericFilters=f"created_at_i>{min_created}",
            ).json()
        except Exception as e:
            errors.append(f"{q}:{str(e)[:80]}")
            continue
        for h in data.get("hits") or []:
            if len(out) >= MAX_PER_SOURCE:
                break
            title = h.get("title") or h.get("story_title") or ""
            created_i = h.get("created_at_i")
            dt = datetime.fromtimestamp(created_i, tz=timezone.utc) if created_i else _parse_rfc3339_or_rfc822(h.get("created_at") or "")
            if not _within(dt, cutoff):
                continue
            object_id = h.get("objectID") or ""
            url = h.get("url") or (f"https://news.ycombinator.com/item?id={object_id}" if object_id else "")
            points = h.get("points")
            comments = h.get("num_comments")
            summary = f"HN story; points={points}, comments={comments}, query={q}"
            item = _social_item(
                "Hacker News", title, url, summary, dt, "MEDIUM",
                {"platform": "hacker_news", "query": q, "points": points, "comments": comments},
            )
            if item:
                out.append(item)
    return out, {"feed": "Hacker News", "fetched": len(out), "errors": errors[:5]}


def fetch_google_trends(window_hours: int) -> tuple[list[dict], dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    geo = os.environ.get("BREAK_NEWS_GOOGLE_TRENDS_GEO", "US")
    url = f"https://trends.google.com/trending/rss?geo={quote(geo)}"
    out: list[dict] = []
    errors: list[str] = []
    try:
        root = etree.fromstring(
            _http_get(url).content,
            parser=etree.XMLParser(recover=True),
        )
    except Exception as e:
        return [], {"feed": "Google Trends", "fetched": 0, "errors": [str(e)[:120]]}
    for it in root.findall(".//item"):
        if len(out) >= MAX_PER_SOURCE:
            break

        def g(tag):
            el = it.find(tag)
            return clean_text(el.text) if el is not None and el.text else ""

        title = g("title")
        desc = g("description")
        joined = f"{title} {desc}".lower()
        if not any(term in joined for term in MARKET_TERMS):
            continue
        dt = _parse_rfc3339_or_rfc822(g("pubDate"))
        if not _within(dt, cutoff):
            continue
        item = _social_item(
            "Google Trends", f"Google trend: {title}", g("link"), desc, dt, "LOW",
            {"platform": "google_trends", "geo": geo},
        )
        if item:
            out.append(item)
    return out, {"feed": "Google Trends", "fetched": len(out), "errors": errors}


def _strip_tags(text: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", text or "", flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return clean_text(html.unescape(text))


def fetch_truth_social(window_hours: int) -> tuple[list[dict], dict]:
    """Fetch recent public posts from Truth Social handles.

    Truth Social does not advertise a stable public API, but its web app has
    retained Mastodon-like account lookup/statuses endpoints. Treat failures as
    soft source errors so the rest of Break News keeps running.
    """
    if not TRUTH_SOCIAL_ENABLED:
        return [], {"feed": "Truth Social", "fetched": 0, "disabled": True}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    handles = _split_env("BREAK_NEWS_TRUTH_SOCIAL_HANDLES", DEFAULT_TRUTH_SOCIAL_HANDLES)
    base = os.environ.get("BREAK_NEWS_TRUTH_SOCIAL_BASE", "https://truthsocial.com").rstrip("/")
    out: list[dict] = []
    errors: list[str] = []
    for handle in handles:
        if len(out) >= TRUTH_SOCIAL_MAX_PER_CYCLE:
            break
        acct = handle.lstrip("@").strip()
        if not acct:
            continue
        try:
            account = _http_get(f"{base}/api/v1/accounts/lookup", acct=acct).json()
            account_id = account.get("id")
            if not account_id:
                raise RuntimeError("account id not found")
            statuses = _http_get(
                f"{base}/api/v1/accounts/{account_id}/statuses",
                limit=min(TRUTH_SOCIAL_MAX_PER_CYCLE, MAX_PER_SOURCE),
                exclude_replies="true",
            ).json()
        except Exception as e:
            errors.append(f"{acct}:{str(e)[:100]}")
            continue
        for s in statuses or []:
            if len(out) >= TRUTH_SOCIAL_MAX_PER_CYCLE:
                break
            dt = _parse_rfc3339_or_rfc822(s.get("created_at") or "")
            if not _within(dt, cutoff):
                continue
            text = _strip_tags(s.get("content") or "")
            reblog = s.get("reblog") or {}
            if not text and reblog:
                text = "RT: " + _strip_tags(reblog.get("content") or "")
            if not text:
                continue
            status_id = s.get("id") or ""
            url = s.get("url") or f"{base}/@{acct}/{status_id}"
            item = _social_item(
                f"Truth Social:@{acct}",
                text[:180],
                url,
                text,
                dt,
                "MEDIUM",
                {
                    "platform": "truth_social",
                    "handle": acct,
                    "status_id": status_id,
                    "replies": s.get("replies_count"),
                    "reblogs": s.get("reblogs_count"),
                    "favourites": s.get("favourites_count"),
                },
            )
            if item:
                out.append(item)
    return out, {"feed": "Truth Social", "fetched": len(out), "handles": handles, "errors": errors[:5]}


def fetch_social_items(window_hours: int) -> tuple[list[dict], list[dict]]:
    items: list[dict] = []
    stats: list[dict] = []
    adapters = [
        fetch_truth_social,
        fetch_reddit,
        fetch_bluesky,
        fetch_hacker_news,
        fetch_google_trends,
    ]
    for fn in adapters:
        if len(items) >= MAX_TOTAL:
            break
        try:
            got, stat = fn(window_hours)
        except Exception as e:
            got, stat = [], {"feed": fn.__name__, "fetched": 0, "errors": [str(e)[:120]]}
        room = max(MAX_TOTAL - len(items), 0)
        items.extend(got[:room])
        stats.append(stat)
    return items, stats


if __name__ == "__main__":
    import json
    data, feed_stats = fetch_social_items(int(os.environ.get("BREAK_NEWS_WINDOW_HOURS", "6")))
    print(json.dumps({"count": len(data), "stats": feed_stats, "items": data[:10]}, ensure_ascii=False, indent=2, default=str))

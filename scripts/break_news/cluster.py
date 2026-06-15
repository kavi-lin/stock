"""Event clustering for break news — pure Python, 0 LLM.

Groups near-duplicate headlines (same story, different feeds / re-pushes) into
rolling event clusters so one event is debated once, not once per source.
Subsequent matches are recorded as *echoes*: they bump `echo_count`, extend the
source list, and feed the cluster's importance signal — but spend no LLM call.

Matching: zh-aware token Jaccard / containment over headline tokens, scoped to
the same `news_type` (a sentiment headline never merges into an earnings one).
Cluster store: `news/break_news_logs/_clusters.json`, rolling CLUSTER_TTL_H.

Escalation: a cluster that keeps accumulating echoes is by definition a story
the market keeps talking about. At echo milestones (4, 8, 16 …) and ≥
ESCALATE_MIN_GAP_H since the last debate, `assign_item` flags one follow-up
debate; the poller admits it with `advance_reason=cluster_escalation` and the
debater feeds the prior conclusion into the prompt so the round argues only the
increment.
"""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STORE_DIR = ROOT / "news" / "break_news_logs"
CLUSTERS_FILE = STORE_DIR / "_clusters.json"

CLUSTER_TTL_H = float(os.environ.get("BREAK_NEWS_CLUSTER_TTL_H", "48"))
SIM_THRESHOLD = float(os.environ.get("BREAK_NEWS_CLUSTER_SIM", "0.55"))
ESCALATE_MILESTONES = (4, 8, 16, 32)
ESCALATE_MIN_GAP_H = float(os.environ.get("BREAK_NEWS_ESCALATE_GAP_H", "3"))
MAX_CLUSTERS = int(os.environ.get("BREAK_NEWS_MAX_CLUSTERS", "600"))

_lock = threading.Lock()

_STOPWORDS = {
    "a", "an", "the", "to", "of", "in", "on", "for", "and", "or", "as", "at",
    "by", "with", "is", "are", "be", "was", "were", "after", "amid", "over",
    "from", "into", "its", "his", "her", "their", "this", "that", "it", "but",
    "will", "would", "could", "should", "has", "have", "had", "new", "says",
    "say", "said", "report", "reports", "update", "live", "breaking", "news",
}
_PUNCT_RE = re.compile(r"[，。、；：！？「」『』（）()【】\[\]—…'\"’‘“”:;,.!?%$#@*&/\\|<>~`+=\-]+")
_WS_RE = re.compile(r"\s+")
_TICKER_RE = re.compile(r"\b[A-Z]{2,5}\b")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _stem(w: str) -> str:
    """Ultra-light suffix stem so 'cuts/cutting', 'cools/cooling' merge.
    Order matters: 'ing'/'ed' before plain 's'."""
    for suf in ("ing", "ed", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def tokenize(text: str) -> set[str]:
    """zh-aware token set: en words lowercased + light-stemmed (stopwords
    dropped), zh chars as bigrams (single chars too noisy, bigrams capture
    詞 boundaries well enough for headline-grain matching)."""
    if not text:
        return set()
    cleaned = _WS_RE.sub(" ", _PUNCT_RE.sub(" ", text)).strip()
    toks: set[str] = set()
    for word in cleaned.split():
        zh_chars = re.findall(r"[一-鿿]", word)
        if zh_chars:
            for i in range(len(zh_chars) - 1):
                toks.add(zh_chars[i] + zh_chars[i + 1])
            if len(zh_chars) == 1:
                toks.add(zh_chars[0])
            latin = re.sub(r"[一-鿿]+", " ", word)
            for w in latin.split():
                lw = w.lower()
                if len(lw) >= 2 and lw not in _STOPWORDS:
                    toks.add(_stem(lw))
        else:
            lw = word.lower()
            if len(lw) >= 2 and lw not in _STOPWORDS:
                toks.add(_stem(lw))
    return toks


def extract_tickers(text: str) -> set[str]:
    return set(_TICKER_RE.findall(text or "")) - {"CEO", "CFO", "CTO", "IPO",
                                                  "GDP", "CPI", "PCE", "FED",
                                                  "ETF", "SEC", "FDA", "USA",
                                                  "WSJ", "PMI", "EPS"}


def similarity(a: set[str], b: set[str]) -> float:
    """max(Jaccard, containment) — containment catches a short re-push of a
    long original ("Fed cuts rates" vs "Fed cuts rates by 25bp as inflation…")."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    jac = inter / len(a | b)
    cont = inter / min(len(a), len(b))
    return max(jac, cont)


# ── store ──────────────────────────────────────────────────────────────────


def _atomic_write(payload: dict) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CLUSTERS_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CLUSTERS_FILE)


def load_clusters() -> dict:
    if not CLUSTERS_FILE.exists():
        return {"clusters": []}
    try:
        with open(CLUSTERS_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("clusters"), list):
            return d
    except (OSError, json.JSONDecodeError):
        pass
    return {"clusters": []}


def _prune(clusters: list[dict], now: datetime) -> list[dict]:
    kept = []
    for c in clusters:
        last = _parse_iso(c.get("last_seen")) or _parse_iso(c.get("created_at"))
        if last is None:
            continue
        if (now - last).total_seconds() / 3600.0 <= CLUSTER_TTL_H:
            kept.append(c)
    kept.sort(key=lambda c: c.get("last_seen") or "", reverse=True)
    return kept[:MAX_CLUSTERS]


def assign_item(headline: str, summary: str, news_type: str,
                shallow_score: float, source_name: str | None,
                key: str | None = None) -> dict:
    """Match item against live clusters; create one when nothing matches.

    Returns {cluster_id, is_echo, echo_count, should_escalate, sim,
             prior_news_ids, rep_headline}.
    `should_escalate=True` at most once per milestone (flag persists on the
    cluster so concurrent polls can't double-fire).
    """
    toks = tokenize(headline)
    tickers = extract_tickers(f"{headline} {summary or ''}")
    now = _utc_now()
    with _lock:
        store = load_clusters()
        clusters = _prune(store.get("clusters") or [], now)

        best, best_sim = None, 0.0
        for c in clusters:
            if c.get("news_type") != news_type:
                continue
            sim = similarity(toks, set(c.get("tokens") or []))
            # ticker overlap is a strong tiebreaker for company stories
            c_tickers = set(c.get("tickers") or [])
            if tickers and c_tickers and (tickers & c_tickers):
                sim += 0.10
            if sim > best_sim:
                best, best_sim = c, sim

        if best is not None and best_sim >= SIM_THRESHOLD:
            best["echo_count"] = int(best.get("echo_count") or 1) + 1
            best["last_seen"] = _utc_iso()
            srcs = best.setdefault("sources", [])
            if source_name and source_name not in srcs:
                srcs.append(source_name)
            best["tickers"] = sorted(set(best.get("tickers") or []) | tickers)
            # union-cap tokens so the cluster signature follows the story
            merged = set(best.get("tokens") or []) | toks
            best["tokens"] = sorted(merged)[:80]
            try:
                if abs(float(shallow_score)) > abs(float(best.get("best_score") or 0.0)):
                    best["best_score"] = float(shallow_score)
            except (TypeError, ValueError):
                pass
            if key:
                best.setdefault("member_keys", []).append(key)
                best["member_keys"] = best["member_keys"][-50:]

            should_escalate = False
            ec = best["echo_count"]
            fired = set(best.get("escalations_fired") or [])
            if best.get("debated_news_ids"):
                last_dbt = _parse_iso(best.get("last_debate_at"))
                gap_ok = (last_dbt is None or
                          (now - last_dbt).total_seconds() / 3600.0 >= ESCALATE_MIN_GAP_H)
                milestone = next((m for m in ESCALATE_MILESTONES
                                  if ec >= m and m not in fired), None)
                if milestone is not None and gap_ok:
                    should_escalate = True
                    fired.add(milestone)
                    best["escalations_fired"] = sorted(fired)

            store["clusters"] = clusters
            _atomic_write(store)
            return {
                "cluster_id": best["cluster_id"],
                "is_echo": True,
                "echo_count": best["echo_count"],
                "should_escalate": should_escalate,
                "sim": round(best_sim, 3),
                "prior_news_ids": list(best.get("debated_news_ids") or []),
                "rep_headline": best.get("rep_headline"),
            }

        cid = "cl_" + now.strftime("%Y%m%d") + "_" + uuid.uuid4().hex[:8]
        clusters.append({
            "cluster_id": cid,
            "created_at": _utc_iso(),
            "last_seen": _utc_iso(),
            "news_type": news_type,
            "rep_headline": (headline or "")[:200],
            "tokens": sorted(toks)[:80],
            "tickers": sorted(tickers),
            "echo_count": 1,
            "sources": [source_name] if source_name else [],
            "member_keys": [key] if key else [],
            "debated_news_ids": [],
            "last_debate_at": None,
            "best_score": float(shallow_score or 0.0),
            "escalations_fired": [],
        })
        store["clusters"] = clusters
        _atomic_write(store)
        return {
            "cluster_id": cid,
            "is_echo": False,
            "echo_count": 1,
            "should_escalate": False,
            "sim": 0.0,
            "prior_news_ids": [],
            "rep_headline": (headline or "")[:200],
        }


def mark_debated(cluster_id: str, news_id: str) -> None:
    """Record that a debate item was opened for this cluster."""
    with _lock:
        store = load_clusters()
        for c in store.get("clusters") or []:
            if c.get("cluster_id") == cluster_id:
                ids = c.setdefault("debated_news_ids", [])
                if news_id not in ids:
                    ids.append(news_id)
                c["last_debate_at"] = _utc_iso()
                _atomic_write(store)
                return


def cluster_feed(hours: float = 24.0, min_echo: int = 1) -> list[dict]:
    """Read-only cluster list for the API / market brief, hottest first.
    Heat = echo_count × max(1, |best_score|)."""
    cutoff = _utc_now()
    out = []
    for c in load_clusters().get("clusters") or []:
        last = _parse_iso(c.get("last_seen"))
        if last is None or (cutoff - last).total_seconds() / 3600.0 > hours:
            continue
        ec = int(c.get("echo_count") or 1)
        if ec < min_echo:
            continue
        try:
            score = abs(float(c.get("best_score") or 0.0))
        except (TypeError, ValueError):
            score = 0.0
        out.append({
            "cluster_id": c.get("cluster_id"),
            "rep_headline": c.get("rep_headline"),
            "news_type": c.get("news_type"),
            "echo_count": ec,
            "sources": c.get("sources") or [],
            "tickers": c.get("tickers") or [],
            "best_score": c.get("best_score"),
            "heat": round(ec * max(1.0, score), 2),
            "debated_news_ids": c.get("debated_news_ids") or [],
            "last_seen": c.get("last_seen"),
        })
    out.sort(key=lambda x: x["heat"], reverse=True)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Break-news cluster store inspector")
    ap.add_argument("--feed", action="store_true", help="print 24h cluster feed")
    ap.add_argument("--hours", type=float, default=24.0)
    args = ap.parse_args()
    if args.feed:
        print(json.dumps(cluster_feed(args.hours), ensure_ascii=False, indent=2))
    else:
        d = load_clusters()
        print(f"{len(d.get('clusters') or [])} clusters in store")

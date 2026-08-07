#!/usr/bin/env python3
"""X API v2 client for the KOL collector — paced, budget-gated, single-threaded.

Endpoints used (both billable, see scripts/x_kol/budget.py):
  GET /2/users/by/username/{handle}   $0.010 per user returned  — resolved ONCE
                                       per handle then cached forever; handles
                                       change far less often than $0.01 matters.
  GET /2/users/{id}/tweets            $0.005 per post returned

Cost discipline lives in three places and all three are load-bearing:
  1. `since_id` — the API bills per resource RETURNED, so an incremental sweep
     that finds nothing new returns 0 posts and costs $0. This is what makes
     polling affordable at all; without it a 5-minute sweep re-reads the same
     posts all day. X does document a 24h UTC dedup window, but its own docs call
     it a "soft guarantee" that can lapse during outages — so cost correctness
     must not depend on it.
  2. `max_results` — the API floor is 5. Whatever we ask for is the worst case the
     budget guard pre-authorizes.
  3. Pacing — one request at a time with a fixed floor between calls, and a
     doubling backoff on 429. Never concurrent: a burst is exactly how the free
     syndication endpoint was made to return 429 for ~3 minutes during the
     2026-08-06 feasibility test.

Auth: bearer token from $X_BEARER_TOKEN. Absent → `dry_run` is the only usable mode.

This module returns raw parsed posts; it does no scoring and writes no dashboard
artifact. Exploration layer only.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.x_kol import budget as budget_mod  # noqa: E402

API_BASE = "https://api.x.com/2"
HANDLE_CACHE_PATH = ROOT / "config/x_kol_handles.json"
TWEET_FIELDS = "created_at,entities,public_metrics,lang"

# Secrets file. Same one premarket_cron.sh sources, for the same reason: launchd
# and cron start with no login shell, so anything exported from ~/.zshrc is
# invisible to a scheduled run. The token must NEVER go in config/x_kol.json —
# that file is tracked in git.
ENV_FILE_DEFAULT = ROOT / "scripts/premarket/premarket_cron.env"
TOKEN_VAR = "X_BEARER_TOKEN"


def load_env_file(path: Path | None = None) -> dict:
    """Parse KEY=VALUE lines from the secrets file. Returns names→values but
    never logs them. A real environment variable always wins over the file."""
    path = Path(path or os.environ.get("X_KOL_ENV_FILE") or ENV_FILE_DEFAULT)
    out: dict[str, str] = {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            out[key] = value
    return out


def env_file_is_private(path: Path | None = None) -> bool | None:
    """True if the secrets file is owner-only (0600-ish). None if absent.
    A world-readable secrets file is readable by every process running as you."""
    path = Path(path or os.environ.get("X_KOL_ENV_FILE") or ENV_FILE_DEFAULT)
    try:
        mode = path.stat().st_mode
    except OSError:
        return None
    return not (mode & 0o077)


def resolve_token(*, env_file: Path | None = None) -> tuple[str, str]:
    """Return (token, source). Source is 'env' | 'env_file' | '' — never the value."""
    token = os.environ.get(TOKEN_VAR, "").strip()
    if token:
        return token, "env"
    token = (load_env_file(env_file).get(TOKEN_VAR) or "").strip()
    if token:
        return token, "env_file"
    return "", ""


class XClientError(RuntimeError):
    pass


class XAuthMissing(XClientError):
    pass


def _load_handle_cache(path: Path | None = None) -> dict:
    try:
        with open(path or HANDLE_CACHE_PATH, encoding="utf-8") as fp:
            return json.load(fp)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_handle_cache(cache: dict, path: Path | None = None) -> None:
    path = path or HANDLE_CACHE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(cache, fp, ensure_ascii=False, indent=2, sort_keys=True)
        fp.write("\n")


class XClient:
    """One instance per sweep. Not thread-safe by design — see module docstring."""

    def __init__(self, config: dict, *, token: str | None = None, dry_run: bool = False,
                 usage_path: Path | None = None, handle_cache_path: Path | None = None,
                 session=None, sleep=time.sleep):
        self.config = config
        self.pacing = config["pacing"]
        self.dry_run = dry_run
        self.usage_path = usage_path
        self.handle_cache_path = handle_cache_path
        if token is not None:
            self.token, self.token_source = token, "explicit"
        else:
            self.token, self.token_source = resolve_token()
        self.session = session or requests.Session()
        self._sleep = sleep
        self._last_call_at = 0.0
        self.calls = 0
        # Last seen x-rate-limit-* headers. X returns these on every response at
        # no extra cost, so they are the honest way to measure real frequency
        # headroom instead of guessing from published numbers.
        self.rate_limit: dict = {}
        if not self.token and not dry_run:
            raise XAuthMissing(
                f"{TOKEN_VAR} not found. Add a line to {ENV_FILE_DEFAULT} "
                f"(chmod 600, already gitignored), or export it, "
                f"or run with --dry-run (no HTTP, no spend)."
            )

    # ── pacing ───────────────────────────────────────────────────────────
    def _pace(self) -> None:
        floor = float(self.pacing.get("min_interval_sec", 2.0))
        delta = time.monotonic() - self._last_call_at
        if self._last_call_at and delta < floor:
            self._sleep(floor - delta)
        self._last_call_at = time.monotonic()

    def _note_rate_limit(self, path: str, resp) -> None:
        """Record x-rate-limit-* from a response. Free — the headers ride along on
        a call we already paid for, so this measures real headroom rather than
        trusting published per-endpoint numbers."""
        headers = getattr(resp, "headers", None) or {}
        limit = headers.get("x-rate-limit-limit")
        remaining = headers.get("x-rate-limit-remaining")
        reset = headers.get("x-rate-limit-reset")
        if limit is None and remaining is None:
            return

        def _int(v):
            try:
                return int(v)
            except (TypeError, ValueError):
                return None

        self.rate_limit[path.split("/")[-1] or path] = {
            "endpoint": path,
            "limit": _int(limit),
            "remaining": _int(remaining),
            "reset_epoch": _int(reset),
            "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    def _get(self, path: str, params: dict) -> dict:
        """Single paced GET with 429 backoff. Budget is checked by the caller,
        which is the only place that knows the worst-case resource count."""
        backoff = float(self.pacing.get("backoff_sec", 60))
        backoff_max = float(self.pacing.get("backoff_max_sec", 900))
        url = f"{API_BASE}{path}"
        headers = {"Authorization": f"Bearer {self.token}"}
        while True:
            self._pace()
            self.calls += 1
            resp = self.session.get(
                url, params=params, headers=headers,
                timeout=float(self.pacing.get("timeout_sec", 20)),
            )
            self._note_rate_limit(path, resp)
            if resp.status_code == 429:
                if backoff > backoff_max:
                    raise XClientError(f"429 on {path} and backoff exhausted (>{backoff_max}s)")
                self._sleep(backoff)
                backoff *= 2
                continue
            if resp.status_code == 401:
                raise XAuthMissing(f"401 unauthorized on {path} — check X_BEARER_TOKEN")
            if resp.status_code >= 400:
                raise XClientError(f"{resp.status_code} on {path}: {resp.text[:200]}")
            return resp.json()

    # ── endpoints ────────────────────────────────────────────────────────
    def resolve_user_id(self, handle: str) -> str | None:
        """Handle → numeric id, cached permanently. Returns None in dry-run when
        the handle has never been resolved (nothing to look up offline)."""
        handle = handle.lstrip("@")
        cache = _load_handle_cache(self.handle_cache_path)
        if handle in cache:
            return cache[handle]["id"]
        if self.dry_run:
            return None
        budget_mod.check(self.config, users=1, usage_path=self.usage_path)
        payload = self._get(f"/users/by/username/{handle}", {})
        data = payload.get("data") or {}
        if not data.get("id"):
            budget_mod.record(self.config, users=0, usage_path=self.usage_path)
            return None
        budget_mod.record(self.config, users=1, usage_path=self.usage_path)
        cache[handle] = {
            "id": str(data["id"]),
            "name": data.get("name") or "",
            "resolved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        _save_handle_cache(cache, self.handle_cache_path)
        return cache[handle]["id"]

    def fetch_timeline(self, user_id: str, *, since_id: str | None = None,
                       max_results: int | None = None,
                       paginate: bool = True,
                       stop_after: int | None = None) -> tuple[list[dict], dict]:
        """Return (posts, meta) newest-first, for posts newer than since_id.

        Costs nothing when there is nothing new: the API returns an empty data
        array and we book 0 reads (verified live 2026-08-06 — an idle sweep moved
        the rate-limit counter but not the ledger).

        Pagination is not optional for correctness. `max_results` is a ceiling and
        pages come back UNDER-filled (asked 10, got 5 — observed 2026-08-06), and
        results are newest-first. So if an account posts more than one page's worth
        between sweeps, a single fetch returns only the newest slice; advancing the
        watermark to `newest_id` would then skip everything below it, permanently
        and silently. Following `next_token` walks the same since_id query back to
        the watermark and closes that gap.

        `stop_after` bounds the walk by RECORD count rather than page count, which
        is what a cold start wants: pages arrive under-filled, so "give me the 5
        most recent" cannot be expressed as a single request (asking 5 returned 1
        live on 2026-08-06, losing that day's other four posts). Paginate until
        `stop_after` records are in hand, then stop.

        `meta["truncated"]` is set when the page cap stopped us before the timeline
        was exhausted — a real gap, surfaced rather than swallowed.
        """
        want = int(max_results or self.config["collect"]["max_results"])
        want = max(5, min(100, want))  # API floor is 5, ceiling 100
        if self.dry_run:
            return [], {"result_count": 0, "dry_run": True}

        max_pages = int(self.config["collect"].get("max_pages_per_sweep", 5))
        collected: list[dict] = []
        newest_id = None
        token = None
        pages = 0
        truncated = False

        while True:
            budget_mod.check(self.config, posts=want, usage_path=self.usage_path)
            params = {"max_results": want, "tweet.fields": TWEET_FIELDS}
            if since_id:
                params["since_id"] = str(since_id)
            if token:
                params["pagination_token"] = token
            payload = self._get(f"/users/{user_id}/tweets", params)
            posts = payload.get("data") or []
            meta = payload.get("meta") or {}
            budget_mod.record(self.config, posts=len(posts), usage_path=self.usage_path)

            collected.extend(posts)
            newest_id = newest_id or meta.get("newest_id")
            pages += 1
            if stop_after is not None and len(collected) >= stop_after:
                collected = collected[:stop_after]
                break
            token = meta.get("next_token") if paginate else None
            if not token:
                break
            if pages >= max_pages:
                truncated = True
                break

        return collected, {
            "result_count": len(collected),
            "newest_id": newest_id,
            "pages": pages,
            "truncated": truncated,
        }


def cashtags(post: dict) -> list[str]:
    """Tickers X already parsed for us. Verified 2026-08-06: X returns structured
    cashtag entities, so no NLP and no 'Apple the fruit' false positives."""
    tags = ((post.get("entities") or {}).get("cashtags")) or []
    out = []
    for t in tags:
        sym = str(t.get("tag") or "").upper().strip()
        if sym and sym not in out:
            out.append(sym)
    return out


def normalize(post: dict, *, handle: str, label: str) -> dict:
    """Flatten one API post into the shadow-log record shape."""
    metrics = post.get("public_metrics") or {}
    return {
        "post_id": str(post.get("id") or ""),
        "handle": handle,
        "label": label,
        "created_at": post.get("created_at") or "",
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "text": post.get("text") or "",
        "lang": post.get("lang") or "",
        "cashtags": cashtags(post),
        "url": f"https://x.com/{handle}/status/{post.get('id')}" if post.get("id") else "",
        "metrics": {
            "like": metrics.get("like_count"),
            "reply": metrics.get("reply_count"),
            "repost": metrics.get("retweet_count"),
            "impression": metrics.get("impression_count"),
        },
    }

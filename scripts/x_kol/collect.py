#!/usr/bin/env python3
"""One collection sweep over the X KOL roster → append-only shadow log.

    python3 scripts/x_kol/collect.py --dry-run     # no HTTP, no spend — start here
    python3 scripts/x_kol/collect.py               # one real sweep
    python3 scripts/x_kol/collect.py --status      # ledger + per-handle watermarks

**Exploration layer.** This writes ONE artifact — the shadow JSONL — and nothing
else. It does not touch Dashboard/*.json, does not patch any cache, and its output
never enters investment_protocol decisions (buy_threshold / position_size /
verdict), per the global discipline in CLAUDE.md. Wiring it into the intraday mood
panel is a separate, later decision that should be made from measured data, not
from the fact that a collector exists.

Watermarks (`since_id` per handle) live in `config/x_kol_state.json`. They are what
keep a sweep cheap: only posts newer than the last one seen are billed. A handle
seen for the first time is capped at `collect.first_run_max` so a cold start on a
prolific account cannot drain a pilot budget in one call.

Exit codes: 0 ok · 1 hard failure · 2 partial (some handles failed, log still written).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.x_kol import budget as budget_mod  # noqa: E402
from scripts.x_kol import pending  # noqa: E402
from scripts.x_kol.client import (  # noqa: E402
    ENV_FILE_DEFAULT,
    TOKEN_VAR,
    XAuthMissing,
    XClient,
    XClientError,
    env_file_is_private,
    normalize,
    resolve_token,
)

STATE_PATH = ROOT / "config/x_kol_state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_state(path: Path | None = None) -> dict:
    try:
        with open(path or STATE_PATH, encoding="utf-8") as fp:
            return json.load(fp)
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "handles": {}}


def save_state(state: dict, path: Path | None = None) -> None:
    path = path or STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fp:
        json.dump(state, fp, ensure_ascii=False, indent=2, sort_keys=True)
        fp.write("\n")
    os.replace(tmp, path)


def append_shadow(records: list[dict], log_path: Path) -> int:
    """Append-only. The log is the raw observation record; anything derived from
    it is rebuildable, so this file is never rewritten in place."""
    if not records:
        return 0
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fp:
        for rec in records:
            fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(records)


def active_roster(config: dict) -> list[dict]:
    out = []
    for entry in config.get("roster") or []:
        handle = str(entry.get("handle") or "").lstrip("@").strip()
        if not entry.get("enabled") or not handle or handle == "REPLACE_ME":
            continue
        out.append({"handle": handle, "label": entry.get("label") or handle})
    return out


def sweep(config: dict, *, dry_run: bool = False, client=None,
          state_path: Path | None = None, usage_path: Path | None = None,
          log_path: Path | None = None) -> dict:
    """Run one pass over the roster. Never raises for a single bad handle — one
    dead account must not cost the sweep every other account's data."""
    roster = active_roster(config)
    state = load_state(state_path)
    handles_state = state.setdefault("handles", {})
    log_path = log_path or (ROOT / config["collect"]["shadow_log"])
    first_run_max = int(config["collect"].get("first_run_max", 5))

    client = client or XClient(config, dry_run=dry_run, usage_path=usage_path)
    result = {
        "started_at": _now_iso(),
        "dry_run": bool(dry_run),
        "roster_size": len(roster),
        "per_handle": [],
        "new_posts": 0,
        # The records this sweep newly appended. An in-process consumer can take
        # these directly; a separate process uses scripts/x_kol/pending.py, which
        # gives the same only-new guarantee via a cursor over the log.
        "records": [],
        "errors": [],
        "budget_stopped": False,
        "rate_limit": {},
    }

    for member in roster:
        handle, label = member["handle"], member["label"]
        hstate = handles_state.setdefault(handle, {})
        since_id = hstate.get("since_id")
        try:
            user_id = hstate.get("user_id") or client.resolve_user_id(handle)
            if not user_id:
                result["per_handle"].append({"handle": handle, "new": 0, "note": "unresolved"})
                continue
            hstate["user_id"] = user_id
            posts, meta = client.fetch_timeline(
                user_id,
                since_id=since_id,
                # Cold start: bound by RECORD count, not page count. Pages come
                # back under-filled, so asking for first_run_max in one request
                # yields fewer (asked 5, got 1 live on 2026-08-06). Paginating to
                # a record cap gives a predictable "N most recent" without walking
                # into years of history — none of which is a live signal anyway.
                max_results=None if since_id else first_run_max,
                stop_after=None if since_id else first_run_max,
            )
        except budget_mod.BudgetExceeded as e:
            # Deliberate stop, not a failure: the ceiling did its job. Everything
            # collected before this point is already durable in the log.
            result["budget_stopped"] = True
            result["errors"].append(f"{handle}: {e}")
            break
        except (XClientError, XAuthMissing) as e:
            result["errors"].append(f"{handle}: {str(e)[:160]}")
            result["per_handle"].append({"handle": handle, "new": 0, "note": "error"})
            continue

        records = [normalize(p, handle=handle, label=label) for p in posts]
        written = append_shadow(records, log_path)
        result["new_posts"] += written
        result["records"].extend(records)
        row = {"handle": handle, "new": written}
        if meta.get("truncated"):
            # The page cap stopped us before reaching the watermark, so posts
            # between here and the previous sweep are missing. Say so — a silent
            # gap would quietly corrupt the lead/lag measurement this pilot is for.
            row["note"] = f"TRUNCATED after {meta.get('pages')} pages — gap below oldest fetched"
            result["errors"].append(
                f"{handle}: timeline truncated at page cap; raise collect.max_pages_per_sweep")
        result["per_handle"].append(row)

        newest = meta.get("newest_id") or (records[0]["post_id"] if records else None)
        if newest:
            hstate["since_id"] = str(newest)
        hstate["last_swept_at"] = _now_iso()

    save_state(state, state_path)
    result["rate_limit"] = dict(getattr(client, "rate_limit", {}) or {})
    result["ended_at"] = _now_iso()
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="X KOL collector — one sweep")
    ap.add_argument("--dry-run", action="store_true",
                    help="no HTTP, no spend; verifies roster/state/log plumbing")
    ap.add_argument("--status", action="store_true", help="print ledger + watermarks and exit")
    ap.add_argument("--config", default=str(budget_mod.CONFIG_PATH))
    args = ap.parse_args(argv)

    config = budget_mod.load_config(Path(args.config))

    if args.status:
        print(budget_mod.status_line(config))
        state = load_state()
        roster = active_roster(config)
        if not roster:
            print("[x_kol] roster is empty — enable accounts in config/x_kol.json")
        for member in roster:
            h = member["handle"]
            hs = state.get("handles", {}).get(h, {})
            print(f"  @{h:<20} since_id={hs.get('since_id') or '-':<22} "
                  f"last_swept={hs.get('last_swept_at') or '-'}")
        token, source = resolve_token()
        if token:
            private = env_file_is_private()
            warn = ""
            if source == "env_file" and private is False:
                warn = "  ⚠️ secrets file is not owner-only — chmod 600 it"
            elif source == "env":
                warn = "  (from environment; a scheduled run has no login shell — "
                warn += "put it in the secrets file too)"
            print(f"[x_kol.auth] token found via {source}, {len(token)} chars{warn}")
        else:
            print(f"[x_kol.auth] NO TOKEN — add {TOKEN_VAR}=... to {ENV_FILE_DEFAULT}")
        st = pending.status(ROOT / config["collect"]["shadow_log"])
        print(f"[x_kol.llm] pending for analysis: {st['pending_records']} "
              f"(analyzed so far {st['analyzed_total']}, cursor @{st['cursor_offset']}B "
              f"of {st['log_bytes']}B)")
        return 0

    roster = active_roster(config)
    if not roster:
        print("[x_kol] roster is empty — enable accounts in config/x_kol.json", file=sys.stderr)
        return 1

    try:
        result = sweep(config, dry_run=args.dry_run)
    except XAuthMissing as e:
        print(f"[x_kol] {e}", file=sys.stderr)
        return 1

    mode = "DRY-RUN" if result["dry_run"] else "live"
    print(f"[x_kol] {mode} sweep: {result['new_posts']} new posts "
          f"across {result['roster_size']} handles")
    for row in result["per_handle"]:
        note = f" ({row['note']})" if row.get("note") else ""
        print(f"  @{row['handle']:<20} +{row['new']}{note}")
    print(budget_mod.status_line(config))
    for info in result.get("rate_limit", {}).values():
        used = (info["limit"] - info["remaining"]) if (
            info.get("limit") is not None and info.get("remaining") is not None) else "?"
        print(f"[x_kol.rate] {info['endpoint']}: {info.get('remaining')}/{info.get('limit')} "
              f"left this window (used {used})")
    if result["budget_stopped"]:
        print("[x_kol] STOPPED on budget ceiling — raise budget.total_usd to continue",
              file=sys.stderr)
    for err in result["errors"]:
        print(f"[x_kol] {err}", file=sys.stderr)
    return 2 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())

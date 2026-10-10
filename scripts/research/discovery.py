"""Bounded child-process entry point for optional research discovery sources."""
from __future__ import annotations

import contextlib
import json
import sys


def collect(name):
    from scripts.break_news import poller as legacy

    if name == "futu":
        items, _ = legacy._futu.load_for_break_news(
            window_hours=6, max_items=legacy.FUTU_MAX_PER_CYCLE)
        statuses = [{"feed": "Futu Push", "fetched": len(items)}]
    elif name == "social":
        items, statuses = legacy._social_sources.fetch_social_items(6)
    else:
        raise ValueError("unknown discovery adapter")
    # Raw exception strings may contain local paths or authenticated URLs.
    adapters = [{"feed": row.get("feed") or "unknown",
                 "fetched": row.get("fetched", 0),
                 "errors": len(row.get("errors") or []) + int(bool(row.get("error")))}
                for row in statuses]
    return {"items": items, "adapters": adapters,
            "status": "degraded" if any(row["errors"] for row in adapters) else "ok"}


if __name__ == "__main__":
    with contextlib.redirect_stdout(sys.stderr):
        result = collect(sys.argv[1])
    print(json.dumps(result, default=str))

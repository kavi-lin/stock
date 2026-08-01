"""
Intraday Evaluation hub — the single consolidation layer over every intraday
artifact in docs/STOCK_DATA_FETCH_INVENTORY.md.

Downstream consumers read through THIS package (not each fetching on their own):
    from scripts.intraday_eval import build, get_snapshot, load_history
"""
from .engine import build, evaluate, load_sources, _write_atomic, DASHBOARD_DIR
from .history import load_history

import os as _os
import json as _json

OUTPUT_PATH = _os.path.join(DASHBOARD_DIR, "intraday_eval.json")


def get_snapshot():
    """Read the last-written intraday_eval.json (the shared snapshot). Returns
    None if not built yet. This is the single accessor for the page/API."""
    try:
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return None


__all__ = ["build", "evaluate", "load_sources", "get_snapshot", "load_history",
           "_write_atomic", "OUTPUT_PATH", "DASHBOARD_DIR"]

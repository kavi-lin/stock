#!/usr/bin/env python3
"""
Intraday Evaluation — optional LLM narration (繁中導讀).

Best-effort, CHANGE-GATED: the worker runs every 10 min (~39x/session), so we
only spend an LLM call when the strategy picture actually changes. If the
signature (regime label + top strategy ids) is unchanged and the cached
narration is still fresh, we reuse it for free.

Goes through scripts/_shared/model_router.py (multi-model governance / budgets /
cooldown). Returns a deterministic fallback string if the LLM is unavailable.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

from . import engine as _eng

_CACHE = os.path.join(_eng.DASHBOARD_DIR, "intraday_eval_narration.json")
_TTL_SEC = int(os.getenv("INTRADAY_EVAL_NARRATE_TTL_SEC", "1800"))  # 30 min

_SYSTEM = (
    "你是盤中策略導讀員。根據提供的結構化盤中評估數據，用繁體中文寫一段 150-220 字的"
    "導讀：先講 regime 與曝險紀律，再點出 1-2 個最重要的策略主旋律與對應板塊/個股，"
    "最後給一句風險提醒。務實、不喊單、不加碼形容詞。"
    '只回傳一個 ```json``` 區塊：{"briefing_zh": "..."}。'
)


def _signature(payload):
    r = payload.get("regime", {})
    ids = tuple(c["id"] for c in payload.get("strategies", [])[:4])
    return f"{r.get('label')}|{'/'.join(ids)}"


def _load_cache():
    return _eng._read_json(_CACHE) or {}


def _fresh(cache, sig):
    if cache.get("signature") != sig:
        return False
    ts = cache.get("ts")
    if not ts:
        return False
    try:
        age = (datetime.now(timezone.utc) -
               datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds()
    except Exception:
        return False
    return age < _TTL_SEC


def _user_prompt(payload):
    r = payload.get("regime", {})
    g = payload.get("groups", {})
    slim = {
        "regime": {"label": r.get("label"), "posture": r.get("posture"),
                   "exposure_ceiling": r.get("exposure_ceiling"),
                   "drivers": r.get("drivers"), "cautions": r.get("cautions")},
        "mood": payload.get("mood"),
        "breadth": payload.get("breadth"),
        "groups": {k: {"avg": v.get("avg"), "up": v.get("up"), "down": v.get("down")}
                   for k, v in g.items()},
        "top_sectors": payload.get("sectors", [])[:5],
        "strategies": [{"title": c["title"], "stance": c["stance"],
                        "streak": c.get("streak"), "day_count": c.get("day_count"),
                        "tickers": c.get("tickers")}
                       for c in payload.get("strategies", [])[:5]],
        "themes": payload.get("themes", [])[:4],
    }
    return "盤中評估數據：\n" + json.dumps(slim, ensure_ascii=False)


def narrate(payload):
    """Return a zh-TW briefing string. Reuse cache when unchanged; else 1 LLM call."""
    sig = _signature(payload)
    cache = _load_cache()
    if _fresh(cache, sig) and cache.get("briefing_zh"):
        payload.setdefault("_narration_meta", {})["cached"] = True
        return cache["briefing_zh"]

    if _eng.ROOT not in sys.path:
        sys.path.insert(0, _eng.ROOT)
    try:
        from scripts._shared.model_router import run_role
    except Exception:
        return _eng._fallback_narrative(payload)

    res = run_role("intraday_eval", _SYSTEM, _user_prompt(payload))
    text = None
    if res is not None and getattr(res, "exit_code", 1) == 0 and getattr(res, "parsed", None):
        text = (res.parsed or {}).get("briefing_zh")
    if not text:
        return _eng._fallback_narrative(payload)

    try:
        _eng._write_atomic(_CACHE, {
            "signature": sig, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "briefing_zh": text, "model_used": getattr(res, "model_used", None),
        })
    except Exception:
        pass
    payload.setdefault("_narration_meta", {})["cached"] = False
    payload["_narration_meta"]["model_used"] = getattr(res, "model_used", None)
    return text

"""Deterministic schemas for Break News agent payloads.

Prompt instructions are not a gate.  This module is the runtime authority for
the two payload shapes accepted by the debate orchestrator and the log
validator.  It deliberately uses only the standard library so the daemon does
not gain another runtime dependency.
"""
from __future__ import annotations

import math
import re
from typing import Any

from scripts.break_news.prompts import PREDICATES

# V4.132.0 bumped this to 2 for the sequential (一問一答) debate: side B at round
# 0 now answers A's opener with the `response` payload instead of a second blind
# `opening`, and a third model may close the thread with an `arbiter` payload.
# The bump is what grandfathers every pre-existing log — `validate.py` only
# applies this module to threads stamped with the current version.
AGENT_PAYLOAD_SCHEMA_VERSION = 2

OPENING_KEYS = frozenset({
    "commentary",
    "bull_points",
    "bear_points",
    "final_take",
    "entities",
    "relations",
    "done",
    "confidence",
    "rationale_short",
})
#: Side B's round-0 answer. It adjudicates A's points one by one rather than
#: producing a second balanced survey — that duplication is what made both
#: voices say the same thing. No `bull_points`/`bear_points`: B is not required
#: to be balanced, only to be specific about where it disagrees.
RESPONSE_KEYS = frozenset({
    "commentary",
    "assessments",
    "added_bull",
    "added_bear",
    "final_take",
    "entities",
    "relations",
    "done",
    "confidence",
    "rationale_short",
})
REBUTTAL_KEYS = frozenset({
    "commentary",
    "stance",
    "relations",
    "done",
    "confidence",
    "rationale_short",
})
#: The tie-breaker's payload. Only reached when B disputed a point and A refused
#: to concede it, so `ruling` is the whole reason this call happened.
ARBITER_KEYS = frozenset({
    "commentary",
    "ruling",
    "final_take",
    "relations",
    "done",
    "confidence",
    "rationale_short",
})
ASSESSMENT_KEYS = frozenset({"point", "verdict", "reason"})
ENTITY_KEYS = frozenset({"tickers", "sectors", "themes", "tech_keywords"})
RELATION_KEYS = frozenset({"subject", "predicate", "object"})
ALLOWED_PREDICATES = frozenset(p.strip() for p in PREDICATES.split(","))

ASSESSMENT_VERDICTS = frozenset({"agree", "dispute"})
ARBITER_RULINGS = frozenset({"side_a", "side_b", "split"})

# V4.132.0 — these caps catch a RUNAWAY (an essay, or the news body echoed back);
# length as style is the prompt's job, and the prompt still asks for the tight
# numbers. Sized from the logged corpus rather than from the prompt text, because
# the two disagree by a factor of three:
#   commentary   round 0  p50=139  p90=216  p99=467  max=973  (n=10377)
#   commentary   round 1+ p50=192  p90=347  p99=792  max=931  (n=5689)
#   bullets               p50=17   p90=29   p99=37   max=66   (n=76238)
#   final_take            p50=22   p90=29   p99=37   max=59   (n=15482)
#   rationale_short       p50=23   p90=35   p99=68   max=194  (n=16484)
# The old caps (150 / 30 / 30 / 40) sat at or below the p50 of what the models
# actually write, so they rejected ordinary output: 31% of one day's debates lost
# a voice to `length 157 outside 80..150` and `length 32 exceeds 30`. The first
# arbiter call ever made died the same way at 243 characters.
COMMENTARY_MAX = 400
REBUTTAL_COMMENTARY_MAX = 400
BULLET_MAX = 60
TAKE_MAX = 60
RATIONALE_MAX = 80

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
_NODE_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*:[^\s:]+$")
#: `bull:0` / `bear:2` — which of A's opening bullets an assessment answers.
_POINT_REF_RE = re.compile(r"^(bull|bear):[0-2]$")


def payload_kind(round_idx: int, side: str | None = None) -> str:
    """Return the schema name for a zero-based debate round and side.

    Round 0 is no longer symmetric: A opens, B answers that opener. `side` is
    optional so the pre-V4.132.0 two-argument-free callers (and any log without
    a side recorded) still resolve to the round-only mapping they expect.
    """
    if side == "C":
        return "arbiter"
    if round_idx == 0:
        return "response" if side == "B" else "opening"
    return "rebuttal"


def _keys(errors: list[str], value: dict, required: frozenset[str], path: str) -> None:
    missing = sorted(required - set(value))
    extra = sorted(set(value) - required)
    if missing:
        errors.append(f"{path}: missing keys {missing}")
    if extra:
        errors.append(f"{path}: unexpected keys {extra}")


def _string(errors: list[str], value: Any, path: str, *, min_len: int = 1,
            max_len: int) -> None:
    if not isinstance(value, str):
        errors.append(f"{path}: expected string")
        return
    length = len(value.strip())
    if not min_len <= length <= max_len:
        errors.append(f"{path}: length {length} outside {min_len}..{max_len}")


def _string_list(errors: list[str], value: Any, path: str, *, min_items: int = 0,
                 max_items: int | None = None, max_len: int | None = None) -> None:
    if not isinstance(value, list):
        errors.append(f"{path}: expected array")
        return
    if len(value) < min_items or (max_items is not None and len(value) > max_items):
        upper = "unbounded" if max_items is None else str(max_items)
        errors.append(f"{path}: item count {len(value)} outside {min_items}..{upper}")
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{path}[{idx}]: expected non-empty string")
        elif max_len is not None and len(item.strip()) > max_len:
            errors.append(f"{path}[{idx}]: length {len(item.strip())} exceeds {max_len}")


def _confidence(errors: list[str], value: Any, path: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{path}: expected number")
        return
    if not math.isfinite(float(value)) or not 0 <= float(value) <= 1:
        errors.append(f"{path}: expected finite value in 0..1")


def _relations(errors: list[str], value: Any, path: str = "relations") -> None:
    if not isinstance(value, list):
        errors.append(f"{path}: expected array")
        return
    for idx, relation in enumerate(value):
        rel_path = f"{path}[{idx}]"
        if not isinstance(relation, dict):
            errors.append(f"{rel_path}: expected object")
            continue
        _keys(errors, relation, RELATION_KEYS, rel_path)
        for field in ("subject", "object"):
            node_id = relation.get(field)
            if not isinstance(node_id, str) or not _NODE_ID_RE.fullmatch(node_id):
                errors.append(f"{rel_path}.{field}: expected canonical namespace:id")
        predicate = relation.get("predicate")
        if predicate not in ALLOWED_PREDICATES:
            errors.append(f"{rel_path}.predicate: unsupported {predicate!r}")


def _entities(errors: list[str], value: Any) -> None:
    if not isinstance(value, dict):
        errors.append("entities: expected object")
        return
    _keys(errors, value, ENTITY_KEYS, "entities")
    for field in ENTITY_KEYS:
        _string_list(errors, value.get(field), f"entities.{field}")
    tickers = value.get("tickers")
    if isinstance(tickers, list):
        for idx, ticker in enumerate(tickers):
            if isinstance(ticker, str) and ticker.strip() and not _TICKER_RE.fullmatch(ticker):
                errors.append(f"entities.tickers[{idx}]: expected uppercase root ticker")


def _assessments(errors: list[str], value: Any) -> None:
    """Side B's per-point adjudication of A's opener.

    `reason` is required on every entry, including `agree`: an agreement with no
    stated reason is indistinguishable from a model skimming the list, and the
    dispute counter downstream is only as trustworthy as the weakest entry.
    """
    if not isinstance(value, list):
        errors.append("assessments: expected array")
        return
    if not 1 <= len(value) <= 6:
        errors.append(f"assessments: item count {len(value)} outside 1..6")
    seen: set[str] = set()
    for idx, entry in enumerate(value):
        path = f"assessments[{idx}]"
        if not isinstance(entry, dict):
            errors.append(f"{path}: expected object")
            continue
        _keys(errors, entry, ASSESSMENT_KEYS, path)
        point = entry.get("point")
        if not isinstance(point, str) or not _POINT_REF_RE.fullmatch(point):
            errors.append(f"{path}.point: expected bull:N or bear:N with N in 0..2")
        elif point in seen:
            errors.append(f"{path}.point: duplicate {point}")
        else:
            seen.add(point)
        if entry.get("verdict") not in ASSESSMENT_VERDICTS:
            errors.append(f"{path}.verdict: expected agree or dispute")
        _string(errors, entry.get("reason"), f"{path}.reason", max_len=RATIONALE_MAX)


def validate_payload(payload: Any, round_idx: int,
                     side: str | None = None, kind: str | None = None) -> list[str]:
    """Return every schema violation for one debate payload.

    `kind` overrides the (round, side) mapping. The orchestrator needs that for
    one case: when A's opener fails, B falls back to a blind `opening` even
    though it is sitting on side B.
    """
    kind = kind or payload_kind(round_idx, side)
    if not isinstance(payload, dict):
        return [f"{kind}: expected object"]

    errors: list[str] = []
    if kind == "opening":
        _keys(errors, payload, OPENING_KEYS, kind)
        _string(errors, payload.get("commentary"), "commentary", min_len=80, max_len=COMMENTARY_MAX)
        _string_list(errors, payload.get("bull_points"), "bull_points",
                     min_items=1, max_items=3, max_len=BULLET_MAX)
        _string_list(errors, payload.get("bear_points"), "bear_points",
                     min_items=1, max_items=3, max_len=BULLET_MAX)
        _string(errors, payload.get("final_take"), "final_take", max_len=TAKE_MAX)
        _entities(errors, payload.get("entities"))
        if payload.get("done") is not False:
            errors.append("done: opening round must be false")
        _string(errors, payload.get("rationale_short"), "rationale_short", max_len=RATIONALE_MAX)
    elif kind == "response":
        _keys(errors, payload, RESPONSE_KEYS, kind)
        _string(errors, payload.get("commentary"), "commentary", min_len=40, max_len=COMMENTARY_MAX)
        _assessments(errors, payload.get("assessments"))
        _string_list(errors, payload.get("added_bull"), "added_bull",
                     max_items=3, max_len=BULLET_MAX)
        _string_list(errors, payload.get("added_bear"), "added_bear",
                     max_items=3, max_len=BULLET_MAX)
        _string(errors, payload.get("final_take"), "final_take", max_len=TAKE_MAX)
        _entities(errors, payload.get("entities"))
        if not isinstance(payload.get("done"), bool):
            errors.append("done: expected boolean")
        _string(errors, payload.get("rationale_short"), "rationale_short", max_len=RATIONALE_MAX)
    elif kind == "arbiter":
        _keys(errors, payload, ARBITER_KEYS, kind)
        _string(errors, payload.get("commentary"), "commentary", min_len=40, max_len=COMMENTARY_MAX)
        if payload.get("ruling") not in ARBITER_RULINGS:
            errors.append("ruling: expected side_a, side_b or split")
        _string(errors, payload.get("final_take"), "final_take", max_len=TAKE_MAX)
        # The arbiter is the last voice by construction — nothing follows it.
        if payload.get("done") is not True:
            errors.append("done: arbiter must be true")
        _string(errors, payload.get("rationale_short"), "rationale_short", max_len=RATIONALE_MAX)
    else:
        _keys(errors, payload, REBUTTAL_KEYS, kind)
        _string(errors, payload.get("commentary"), "commentary", max_len=REBUTTAL_COMMENTARY_MAX)
        if payload.get("stance") not in {"challenge", "concede"}:
            errors.append("stance: expected challenge or concede")
        if not isinstance(payload.get("done"), bool):
            errors.append("done: expected boolean")
        _string(errors, payload.get("rationale_short"), "rationale_short", max_len=RATIONALE_MAX)

    _relations(errors, payload.get("relations"))
    _confidence(errors, payload.get("confidence"), "confidence")
    return errors

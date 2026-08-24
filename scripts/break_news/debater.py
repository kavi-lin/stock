"""Break-news debate orchestrator (V4.132.0 sequential + third-model tie-break).

State machine per item:
    pending_debate ─► debating ─► closed / partial_closed / failed

The exchange is a turn-taking one, not two parallel monologues:

    round 0  A opens (`opening`)
    round 0  B answers A point by point (`response`: agree/dispute + reason)
    round 1  A replies to what B disputed (`rebuttal`: challenge/concede)
    ─────── only if A refuses to concede ───────
             C rules on the contested point (`arbiter`)

2 calls when B agrees, 3 when A settles it, 4 when it goes to the arbiter.

Until V4.132.0 round 0 was two BLIND parallel openers, on the theory that
independence made divergence a genuine signal. Measured on 2026-08-17 it made
duplication instead: both sides are required to produce a balanced bull/bear
pack, so each take was individually four-square and the pair said the same
thing twice — 56 of 58 debates closed in round 1 without a single exchange. The
gate could not see the disagreement either: it needed both sides to spell the
same node identically, and over 260 logged debates 26% shared a subject|object
pair while only 14% were detectable (`theme:x` vs `narrative:x` was enough to
miss). B now states its disagreement outright, which is what `stated_disputes`
reads. Items flagged `cluster.escalated` get the prior cluster conclusion in
the opener prompt and argue only the increment.

Run modes:
  --news-id <id>     Debate a single item (testing)
  --scan             Loop: find pending_debate items, debate them
  --workers N        Compatibility flag; broker-governed debates stay serial
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.break_news import schema as agent_schema  # noqa: E402
from scripts.break_news import store, prompts  # noqa: E402
from scripts.break_news.llm_drivers import (  # noqa: E402, F401
    load_llm_config, LLMResult)
from scripts._shared import broker_gate  # noqa: E402
from scripts._shared.model_router import run_with_fallback  # noqa: E402

MAX_ROUNDS = int(os.environ.get("BREAK_NEWS_MAX_ROUNDS", "2"))
MAX_ROUNDS_FUTU = int(os.environ.get("BREAK_NEWS_MAX_ROUNDS_FUTU", "2"))
THREAD_TIMEOUT_SEC = int(os.environ.get("BREAK_NEWS_THREAD_TIMEOUT_SEC", "480"))
# Every debate uses the broker's same top-two provider slots. Running two news
# items concurrently makes them race for those exclusive slots and turns the
# loser into a zero-latency provider_busy result. Cross-item execution must
# therefore remain serial.
PARALLEL = 1
# Auto-debate stale-pending guard: items older than this stay in pending_debate
# state but are skipped by scan_and_debate. Surfaced via list_stale_pending()
# so the UI can offer per-item manual triggers. Prevents queue-flood after a
# long idle period (e.g. user opens dashboard 10hr later → no auto burst).
PENDING_MAX_AGE_HOURS = float(os.environ.get("BREAK_NEWS_PENDING_MAX_AGE_HOURS", "2"))
ORPHAN_STALE_SEC = THREAD_TIMEOUT_SEC + 120

_MODEL_NAMES = {"claude": "Claude", "gemini": "Gemini", "codex": "Codex"}


def _roster() -> tuple[list[str], str | None]:
    """The two debaters plus the tie-breaker, from the broker's live ranking.

    Top two debate; the third is held back and only called when they deadlock
    (see `_deadlock`). `None` when the broker names fewer than three — a missing
    arbiter closes the thread as unresolved rather than inventing a third voice
    the quota system did not offer.
    """
    ranked = broker_gate.ranked_models("debate", count=3, cfg=load_llm_config())
    if ranked is None:
        raise RuntimeError("quota broker unavailable; debate deferred")
    if len(ranked) < 2:
        raise RuntimeError("fewer than two broker providers available; debate deferred")
    return ranked[:2], (ranked[2] if len(ranked) > 2 else None)


def _turn_order() -> list[str]:
    """The two debaters — the quota broker's current top two, best first.

    V4.109.0: this used to be a fixed pair in `config/llm_config.json`, chosen
    once and then wrong every time a provider ran out. The broker ranks what can
    actually serve *right now*, across both projects that share these
    subscriptions, so it assigns A and B.

    Returns an empty list when the broker cannot supply two voices. Callers
    defer the daemon cycle; no configured/local pair may start unleased.

    Since V4.132.0 the order is NOT cosmetic: A opens and B answers A point by
    point, so the broker's first choice speaks first.
    """
    # `cfg` is passed explicitly: without it `broker_gate` falls back to its own
    # defaults and silently ignores the `broker` block in llm_config.json —
    # including a base_url or an `enabled: false` the operator set there.
    ranked = broker_gate.ranked_models("debate", count=2, cfg=load_llm_config())
    return ranked if ranked is not None and len(ranked) >= 2 else []


_SIDES = ("A", "B", "C")


def _role_for(idx: int, model: str) -> dict:
    """Role label for the debater at a turn position. Side is positional
    (A opens, B answers, C arbitrates); the model name is appended so the
    transcript shows who spoke."""
    side = _SIDES[idx] if 0 <= idx < len(_SIDES) else "B"
    name = _MODEL_NAMES.get(model, model.title())
    zh = "裁決者 C" if side == "C" else f"分析師 {side}"
    en = "Arbiter-C" if side == "C" else f"Analyst-{side}"
    return {"en": f"{en} ({name})", "zh": f"{zh} ({name})"}


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_done(parsed: dict | None, raw_text: str) -> bool:
    if parsed and parsed.get("done") is True:
        return True
    if raw_text and "<DONE>" in raw_text:
        return True
    return False


def _comment_from_result(res: LLMResult, role: str, side: str, round_idx: int,
                         news_id: str, comment_id_hint: str,
                         kind: str | None = None) -> dict:
    parsed = res.parsed
    parse_status = res.parse_status
    schema_errors: list[str] = []

    # A provider envelope can itself be valid JSON.  A non-zero provider exit
    # must therefore win over parse_status, or quota/auth errors get mistaken
    # for an analyst payload and leak into the summary.
    if res.exit_code != 0:
        schema_errors.append(f"provider exit_code={res.exit_code}")
        parse_status = "failed"
        parsed = None
    elif parse_status != "ok":
        schema_errors.append(f"response parse_status={parse_status}")
        parse_status = "schema_failed" if parsed is not None else "failed"
        parsed = None
    else:
        schema_errors = agent_schema.validate_payload(parsed, round_idx, side, kind)
        if schema_errors:
            parse_status = "schema_failed"
            parsed = None

    raw_path = ""
    if parse_status != "ok":
        raw_path = store.write_raw_stdout(
            news_id, comment_id_hint, res.raw_stdout or res.raw_text or "")
    comment = {
        "agent": res.agent,
        "agent_role_label": role,
        "side": side,
        "round": round_idx,
        "ts": _utc_iso(),
        "latency_ms": res.latency_ms,
        "raw_stdout_path": raw_path,
        "parsed": parsed,
        "parse_status": parse_status,
        "exit_code": res.exit_code,
    }
    if schema_errors:
        comment["schema_errors"] = schema_errors
    error = str(res.error or "").strip()
    route_note = str(getattr(res, "route_note", "") or "").strip()
    if error:
        comment["error"] = error[:500]
    if route_note:
        comment["route_note"] = route_note[:500]
    return comment


def _comment_failed(comment: dict) -> bool:
    """A voice only counts when both its process and round schema pass."""
    return comment.get("exit_code") != 0 or comment.get("parse_status") != "ok"


def _broker_deferred(res: LLMResult) -> bool:
    """True when no provider process ran and a later cycle should retry."""
    if res.exit_code != -9:
        return False
    if res.parse_status == "blocked":
        return True
    route_note = str(getattr(res, "route_note", "") or "")
    error = str(res.error or "")
    return "blocked(" in route_note or "LLM call blocked" in error


def _load_universe_tickers() -> set[str]:
    path = ROOT / "Dashboard" / "heatmap_universe.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data["tickers"] if isinstance(data, dict) and "tickers" in data else data
        if isinstance(raw, list):
            out = set()
            for item in raw:
                if isinstance(item, str):
                    out.add(item.upper())
                elif isinstance(item, dict):
                    sym = item.get("ticker") or item.get("symbol")
                    if sym:
                        out.add(str(sym).upper())
            return out
        if isinstance(raw, dict):
            return {str(k).upper() for k in raw}
    except Exception:
        pass
    return set()


def is_high_priority_item(item: dict) -> bool:
    src = item.get("source") or {}
    src_name = src.get("name") or ""
    src_cred = src.get("credibility") or ""
    
    # 1. 來源高可信度（如 Futu Push / Bloomberg）或 credibility == "HIGH"
    if src_name in ("Bloomberg", "Futu Push") or src_cred == "HIGH":
        return True

    triage = item.get("triage") or {}
    # 2. binary_flag == True
    if triage.get("binary_flag") is True:
        return True

    # 3. abs(shallow_score) >= 3.0  (stage1_triage scale: |s|>=1.5 important,
    #    |s|>=3 strong; the V4 plan's "高 abs(shallow_score)" maps to the strong gate.)
    try:
        score = abs(float(triage.get("shallow_score") or 0.0))
        if score >= 3.0:
            return True
    except (ValueError, TypeError):
        pass

    # 4. Ticker belongs to SECTOR_TOP_5
    from skills._shared.company_context import SECTOR_TOP_5
    all_top_5_tickers = {t.upper() for list_t in SECTOR_TOP_5.values() for t in list_t}
    headline = item.get("headline") or ""
    summary = item.get("raw_summary") or ""
    text_to_check = f"{headline} {summary}"

    if all_top_5_tickers:
        # Case-insensitive: feeds occasionally render tickers as "Nvda" / "nvda".
        ticker_pattern = re.compile(
            r"\b(" + "|".join(sorted(all_top_5_tickers, key=len, reverse=True)) + r")\b",
            re.IGNORECASE,
        )
        if ticker_pattern.search(text_to_check):
            return True

    # 5. Tech Node hits >= 2 (ALL_DOMAIN_PATTERNS)
    try:
        from scripts.nexus.tier2_regex import ALL_DOMAIN_PATTERNS
        hits = 0
        for key, pattern in ALL_DOMAIN_PATTERNS.items():
            if pattern.search(text_to_check):
                hits += 1
                if hits >= 2:
                    return True
    except Exception:
        pass

    return False


# Confidence gap (A vs B) that counts as divergence — high-priority items only
# (V6: a gap alone on a routine item is not worth a rebuttal round).
DIVERGENCE_CONF_GAP = float(os.environ.get("BREAK_NEWS_DIVERGENCE_CONF_GAP", "0.65"))

_POS_PREDS = {"BENEFITS_FROM", "CATALYST_FOR"}
_NEG_PREDS = {"HEADWIND_FROM"}


def _side_verdict(parsed: dict) -> str:
    pos = neg = 0
    for r in (parsed.get("relations") or []):
        if not isinstance(r, dict):
            continue
        pred = r.get("predicate")
        if pred in _POS_PREDS:
            pos += 1
        elif pred in _NEG_PREDS:
            neg += 1
    if pos > neg:
        return "BULLISH"
    if neg > pos:
        return "BEARISH"
    return "NEUTRAL"


def stated_disputes(thread: list[dict]) -> tuple[list[dict], str]:
    """The disagreements side B actually declared, and a note naming them.

    This replaces predicate-set inference as the primary gate. The old gate
    could only see a conflict when both sides happened to spell the same node
    the same way — measured over 260 logged debates, 26% discussed the same
    subject|object pair but only 14% were detectable, so nearly half of the
    candidate conflicts were lost to `theme:` vs `narrative:` alone.
    """
    latest_b: dict = {}
    for c in thread:
        if c.get("side") == "B" and (c.get("parsed") or {}):
            latest_b = c["parsed"]
    disputes = [a for a in (latest_b.get("assessments") or [])
                if isinstance(a, dict) and a.get("verdict") == "dispute"]
    if not disputes:
        return [], ""
    note = "; ".join(
        f"B disputes {d.get('point')}: {(d.get('reason') or '').strip()}"
        for d in disputes)
    return disputes, note


def _deadlock(thread: list[dict]) -> tuple[bool, str]:
    """True when B disputed a point and A's rebuttal did not concede it.

    A missing or unparsed rebuttal is NOT a deadlock: nobody argued the point,
    so there is nothing for a third model to rule on — that closes as
    unresolved instead of spending an arbiter call on a gap in the transcript.
    """
    disputes, note = stated_disputes(thread)
    if not disputes:
        return False, ""
    rebuttal = None
    for c in thread:
        if c.get("side") == "A" and (c.get("round") or 0) >= 1 and (c.get("parsed") or {}):
            rebuttal = c["parsed"]
    if rebuttal is None:
        return False, note
    if rebuttal.get("stance") == "concede":
        return False, note
    return True, note


def _strip_ns(node_id) -> str:
    """`theme:climate_change` and `narrative:climate-change` → `climate_change`.

    Namespace choice is a labelling accident, not a claim about the world, so it
    must not decide whether two sides are talking about the same thing.
    """
    tail = str(node_id or "").split(":", 1)[-1]
    return tail.strip().lower().replace("-", "_")


def divergence_gate(thread: list[dict], is_high: bool = False) -> tuple[bool, str]:
    """Deterministic (0 LLM) check: is a rebuttal round worth the tokens?

    Secondary since V4.132.0: `stated_disputes` is the primary signal now, and
    this remains for the relabel pass and for threads whose side B produced no
    assessments. Node IDs are compared with the namespace stripped, so
    `theme:x` and `narrative:x` no longer read as two different subjects.

    V6 strict mode: divergent ONLY on a true conflict — opposite verdicts, or
    conflicting relation polarity on the same subject|object pair. A
    confidence gap ≥ DIVERGENCE_CONF_GAP counts only for high-priority items.
    A `stance: concede` from either side ends the debate regardless. The note
    is fed verbatim into the rebuttal prompt so the next round argues the
    exact conflict instead of re-surveying the news.
    """
    latest: dict[str, dict] = {}
    for c in thread:
        side = c.get("side")
        parsed = c.get("parsed") or {}
        if side and parsed:
            latest[side] = parsed
    if len(latest) < 2:
        return False, "single_side_only"
    a, b = latest.get("A") or {}, latest.get("B") or {}

    if a.get("stance") == "concede" or b.get("stance") == "concede":
        return False, "concession"

    notes: list[str] = []
    va, vb = _side_verdict(a), _side_verdict(b)
    if {va, vb} == {"BULLISH", "BEARISH"}:
        notes.append(f"verdict conflict: A={va} vs B={vb}")

    def _polarity(parsed: dict) -> dict[str, set[str]]:
        m: dict[str, set[str]] = {}
        for r in (parsed.get("relations") or []):
            if not isinstance(r, dict):
                continue
            pred = r.get("predicate")
            sign = "+" if pred in _POS_PREDS else "-" if pred in _NEG_PREDS else None
            if sign:
                key = f"{_strip_ns(r.get('subject'))}|{_strip_ns(r.get('object'))}"
                m.setdefault(key, set()).add(sign)
        return m

    pa, pb = _polarity(a), _polarity(b)
    for k in sorted(set(pa) & set(pb)):
        if pa[k] != pb[k]:
            notes.append(f"relation polarity conflict on {k.replace('|', ' → ')}")
            break

    if is_high:
        try:
            ca = float(a.get("confidence") or 0.0)
            cb = float(b.get("confidence") or 0.0)
            if abs(ca - cb) >= DIVERGENCE_CONF_GAP:
                notes.append(f"confidence gap: A={ca:.2f} vs B={cb:.2f}")
        except (ValueError, TypeError):
            pass

    if notes:
        return True, "; ".join(notes)
    return False, "converged"


def _low_relation_density(thread: list[dict], item: dict) -> bool:
    """Old round-1 early-stop conditions: no ticker→ticker relation, or
    NEUTRAL consensus with no universe ticker anywhere in sight."""
    for c in thread:
        for rel in ((c.get("parsed") or {}).get("relations") or []):
            if isinstance(rel, dict) and (rel.get("subject") or "").startswith("ticker:") \
                    and (rel.get("object") or "").startswith("ticker:"):
                break
        else:
            continue
        break
    else:
        return True  # no ticker-to-ticker relation at all

    if prompts.build_summary_block(thread).get("consensus_verdict") == "NEUTRAL":
        universe_tickers = _load_universe_tickers()
        text = f"{item.get('headline') or ''} {item.get('raw_summary') or ''}"
        words = set(re.findall(r"\b[A-Z]{2,5}\b", text))
        for c in thread:
            for t in ((c.get("parsed") or {}).get("entities") or {}).get("tickers") or []:
                if isinstance(t, str):
                    words.add(t.upper())
        if not any(w in universe_tickers for w in words):
            return True
    return False


def debate_item(news_id: str, max_rounds: int = MAX_ROUNDS,
                wall_timeout: int = THREAD_TIMEOUT_SEC,
                verbose: bool = False) -> dict:
    """Run one debate and fail back to the queue on an unexpected exception."""
    try:
        return _debate_item(news_id, max_rounds, wall_timeout, verbose)
    except Exception as exc:  # noqa: BLE001 - daemon boundary must restore state
        reason = f"debate worker exception: {type(exc).__name__}: {exc}"
        try:
            store.set_state(
                news_id,
                "pending_debate",
                summary=None,
                deferred_reason=reason[:500],
                last_deferred_at=_utc_iso(),
            )
            store.push_error(news_id, "debate_item", reason)
        except Exception:
            pass
        return {
            "ok": False,
            "deferred": True,
            "news_id": news_id,
            "error": reason,
        }


def _debate_item(news_id: str, max_rounds: int,
                 wall_timeout: int, verbose: bool) -> dict:
    item = store.load_item(news_id)
    if item is None:
        return {"ok": False, "error": f"unknown news_id={news_id}"}
    if item.get("state") not in ("pending_debate", "partial_closed", "failed"):
        return {"ok": False, "error": f"state={item.get('state')}, refusing"}

    # Dynamic depth policy — V6: 2 rounds max for everyone. is_high now only
    # widens the divergence gate (confidence-gap trigger), not the depth.
    is_high = is_high_priority_item(item)
    max_rounds = min(max_rounds, 2)

    if (item.get("source") or {}).get("name") == "Futu Push" and max_rounds == MAX_ROUNDS:
        max_rounds = min(max_rounds, MAX_ROUNDS_FUTU)

    # A re-debate starts clean: the abandoned run's turns are kept as evidence
    # under `retired_threads`, but they must not reach this run's summary.
    retired = store.retire_thread(news_id)
    if retired:
        if verbose:
            print(f"[{news_id}] retired {retired} turn(s) from the previous attempt")
        # `item` was read before the retirement, so its thread is now stale —
        # and it is the fallback every `store.load_item(...) or item` falls back to.
        item = store.load_item(news_id) or item

    store.set_state(news_id, "debating")

    try:
        turn_order, arbiter_model = _roster()
    except RuntimeError as exc:
        reason = str(exc)
        store.set_state(
            news_id,
            "pending_debate",
            summary=None,
            deferred_reason=reason[:500],
            last_deferred_at=_utc_iso(),
        )
        return {"ok": False, "deferred": True, "error": reason}
    t0 = time.time()
    close_reason = "max_rounds"
    state_final = "closed"
    div_note = ""
    a_agent, b_agent = turn_order[0], turn_order[1]

    def _record(res: LLMResult, idx: int, side: str, round_idx: int, where: str,
                kind: str | None = None) -> dict:
        """Append one turn to the thread and report whether it counted."""
        actual = getattr(res, "model_used", res.agent) or turn_order[min(idx, 1)]
        thread_len = len((store.load_item(news_id) or {}).get("thread") or [])
        comment = _comment_from_result(res, _role_for(idx, actual), side, round_idx,
                                       news_id, f"c{thread_len}", kind)
        store.append_comment(news_id, comment)
        if _comment_failed(comment):
            detail = str(getattr(res, "route_note", "") or res.error or "").strip()
            detail_suffix = f" detail={detail[:300]}" if detail else ""
            store.push_error(news_id, where,
                             f"rc={res.exit_code} parse={comment['parse_status']} "
                             f"schema={'; '.join(comment.get('schema_errors') or [])}"
                             f"{detail_suffix}")
        if verbose:
            print(f"  {where} parse_status={comment['parse_status']} rc={res.exit_code}")
        return comment

    def _defer_if_blocked(res: LLMResult, where: str) -> dict | None:
        if not _broker_deferred(res):
            return None
        reason = str(getattr(res, "route_note", "") or res.error or "broker blocked")
        store.set_state(
            news_id,
            "pending_debate",
            summary=None,
            deferred_reason=reason[:500],
            last_deferred_at=_utc_iso(),
        )
        return {
            "ok": False,
            "deferred": True,
            "news_id": news_id,
            "where": where,
            "error": reason,
        }

    # ── Round 0, turn 1: A opens ────────────────────────────────────────
    usr_p = prompts.opener_user_prompt(item, _role_for(0, a_agent))
    if verbose:
        print(f"[{news_id}] round=0 A={a_agent} opener prompt_len={len(usr_p)}")
    res_a = run_with_fallback(a_agent, "debate", prompts.SYSTEM_PROMPT, usr_p)
    comment_a = _record(res_a, 0, "A", 0, f"round0.{a_agent}")
    if deferred := _defer_if_blocked(res_a, f"round0.{a_agent}"):
        return deferred
    a_ok = not _comment_failed(comment_a)

    # ── Round 0, turn 2: B answers A point by point ─────────────────────
    # With A down there is nothing to answer, so B falls back to a blind opener:
    # a salvaged single take still carries entities for the graph, where a
    # `response` payload with no opener to reference would be meaningless.
    if a_ok:
        usr_p = prompts.responder_user_prompt(item, comment_a["parsed"],
                                              _role_for(1, b_agent))
        sys_p, kind_b = prompts.RESPONDER_SYSTEM_PROMPT, "response"
    else:
        usr_p = prompts.opener_user_prompt(item, _role_for(1, b_agent))
        sys_p, kind_b = prompts.SYSTEM_PROMPT, "opening"
    if verbose:
        print(f"[{news_id}] round=0 B={b_agent} {kind_b} prompt_len={len(usr_p)}")
    res_b = run_with_fallback(b_agent, "debate", sys_p, usr_p)
    comment_b = _record(res_b, 1, "B", 0, f"round0.{b_agent}", kind_b)
    if deferred := _defer_if_blocked(res_b, f"round0.{b_agent}"):
        return deferred
    b_ok = not _comment_failed(comment_b)
    rounds_completed = 1

    if not a_ok and not b_ok:
        close_reason = "cli_failures"
        state_final = "failed"
    elif not (a_ok and b_ok):
        # One voice down → no exchange happened. Close on the healthy turn
        # instead of burning a rebuttal call against a salvage record.
        close_reason = "single_voice"
        state_final = "partial_closed"

    # ── Round 1: A answers only what B actually disputed ────────────────
    if state_final == "closed":
        thread = (store.load_item(news_id) or item).get("thread") or []
        disputes, div_note = stated_disputes(thread)
        if _is_done(comment_b.get("parsed"), res_b.raw_text) and not disputes:
            close_reason = "both_done"
        elif not disputes:
            # B agreed with every point and added nothing to argue about. Fall
            # back to the relation-polarity gate: B may still have contradicted
            # A in the graph without flagging it as a dispute.
            divergent, div_note = divergence_gate(thread, is_high)
            if not divergent:
                close_reason = "converged_round1"
        if close_reason == "max_rounds" and max_rounds > 1:
            if not is_high and _low_relation_density(thread, item):
                # Noise with no tradeable node — the dispute may be real but
                # there is nothing to trade on either side of it.
                close_reason = "early_stop_low_relation_density"
            elif time.time() - t0 > wall_timeout:
                close_reason = "timeout"
                state_final = "partial_closed"
            else:
                role = _role_for(0, a_agent)
                usr_p = prompts.rebuttal_user_prompt(item, thread, role, "A", div_note)
                if verbose:
                    print(f"[{news_id}] round=1 A={a_agent} rebuttal "
                          f"prompt_len={len(usr_p)}")
                res = run_with_fallback(a_agent, "debate",
                                        prompts.REBUTTAL_SYSTEM_PROMPT, usr_p)
                comment_r = _record(res, 0, "A", 1, f"round1.{a_agent}")
                if deferred := _defer_if_blocked(res, f"round1.{a_agent}"):
                    return deferred
                if _comment_failed(comment_r):
                    close_reason = "invalid_rebuttal"
                    state_final = "partial_closed"
                else:
                    rounds_completed = 2
                    if (comment_r.get("parsed") or {}).get("stance") == "concede":
                        close_reason = "divergence_resolved"

    # ── Tie-break: a third model rules on what A would not concede ──────
    if state_final == "closed" and close_reason in ("max_rounds", "invalid_rebuttal"):
        thread = (store.load_item(news_id) or item).get("thread") or []
        deadlocked, contested = _deadlock(thread)
        if not deadlocked:
            close_reason = "divergence_resolved"
        elif arbiter_model is None:
            close_reason = "unresolved_no_arbiter"
        elif time.time() - t0 > wall_timeout:
            close_reason = "unresolved_timeout"
            state_final = "partial_closed"
        else:
            usr_p = prompts.arbiter_user_prompt(item, thread, contested)
            if verbose:
                print(f"[{news_id}] arbiter={arbiter_model} prompt_len={len(usr_p)}")
            res = run_with_fallback(arbiter_model, "debate",
                                    prompts.ARBITER_SYSTEM_PROMPT, usr_p)
            comment_c = _record(res, 2, "C", rounds_completed,
                                f"arbiter.{arbiter_model}", "arbiter")
            if deferred := _defer_if_blocked(res, f"arbiter.{arbiter_model}"):
                return deferred
            if _comment_failed(comment_c):
                close_reason = "arbiter_failed"
                state_final = "partial_closed"
            else:
                close_reason = "arbitrated"
            div_note = contested

    final_thread = (store.load_item(news_id) or {}).get("thread") or []

    summary = prompts.build_summary_block(final_thread)
    summary["blind_openers"] = False
    summary["arbiter_model"] = arbiter_model
    summary["stated_dispute_count"] = len(stated_disputes(final_thread)[0])
    summary["rounds_completed"] = rounds_completed
    summary["closed_at"] = _utc_iso()
    summary["agent_payload_schema_version"] = agent_schema.AGENT_PAYLOAD_SCHEMA_VERSION
    summary["close_reason"] = close_reason
    summary["divergence_note"] = _divergence_note(final_thread)
    summary["divergence_gate_note"] = div_note
    store.set_summary(news_id, summary)
    store.set_state(news_id, state_final, graph_status="provisional")
    return {"ok": True, "news_id": news_id, "state": state_final,
            "rounds": rounds_completed, "close_reason": close_reason}


def _divergence_note(thread: list[dict]) -> str:
    """Crude divergence detector based on relation-predicate disagreement."""
    by_agent: dict[str, set[str]] = {}
    for c in thread:
        agent = c.get("agent")
        if not agent:
            continue
        preds = {r.get("predicate") for r in ((c.get("parsed") or {}).get("relations") or [])
                 if isinstance(r, dict)}
        by_agent.setdefault(agent, set()).update(preds)
    if len(by_agent) < 2:
        return ""
    agents = list(by_agent.keys())
    a, b = by_agent[agents[0]], by_agent[agents[1]]
    only_a = a - b
    only_b = b - a
    if not only_a and not only_b:
        return ""
    parts = []
    if only_a:
        parts.append(f"{agents[0]}-only: {', '.join(sorted(only_a))}")
    if only_b:
        parts.append(f"{agents[1]}-only: {', '.join(sorted(only_b))}")
    return "; ".join(parts)


def _parse_iso_utc(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _pending_age_hours(d: dict, now_utc: datetime) -> float | None:
    fetched = _parse_iso_utc(d.get("fetched_at"))
    if fetched is None:
        return None
    return (now_utc - fetched).total_seconds() / 3600.0


def scan_pending(max_items: int = 100, include_stale: bool = False) -> list[str]:
    """List pending_debate news_ids eligible for auto-debate.

    Skips items older than PENDING_MAX_AGE_HOURS unless include_stale=True.
    Stale items remain pending_debate and surface via list_stale_pending()
    so the user can manually choose which to debate.
    """
    out = []
    now_utc = datetime.now(timezone.utc)
    for p in sorted(store.STORE_DIR.glob("bn_*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = __import__("json").load(f)
        except Exception:
            continue
        if d.get("state") != "pending_debate":
            continue
        if not include_stale:
            age = _pending_age_hours(d, now_utc)
            if age is not None and age > PENDING_MAX_AGE_HOURS:
                continue
        out.append(d.get("news_id"))
        if len(out) >= max_items:
            break
    return out


def recover_orphaned_debates(now_utc: datetime | None = None) -> list[str]:
    """Return abandoned `debating` items to the retry queue.

    The server serializes every debate entry point with one dispatch lock, so a
    debating item older than the per-thread wall timeout plus a two-minute
    grace period cannot belong to the scan that is about to start. This catches
    server restarts and unexpected worker exits without touching terminal
    partial/failed history.
    """
    now_utc = now_utc or datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(seconds=ORPHAN_STALE_SEC)
    recovered: list[str] = []
    for path in sorted(store.STORE_DIR.glob("bn_*.json")):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                item = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if item.get("state") != "debating":
            continue
        activity = _parse_iso_utc(item.get("last_activity_ts") or item.get("fetched_at"))
        if activity is not None and activity > cutoff:
            continue
        news_id = str(item.get("news_id") or "")
        if not news_id:
            continue
        reason = f"orphaned debating state recovered after {ORPHAN_STALE_SEC}s"
        store.set_state(
            news_id,
            "pending_debate",
            summary=None,
            deferred_reason=reason,
            last_deferred_at=_utc_iso(),
        )
        recovered.append(news_id)
    return recovered


def list_stale_pending() -> list[dict]:
    """Summaries of pending_debate items past PENDING_MAX_AGE_HOURS.

    UI calls /api/break-news/stale-pending → renders a manual-trigger list so
    the user opts in to spending LLM budget on backlog.
    """
    out: list[dict] = []
    now_utc = datetime.now(timezone.utc)
    for p in sorted(store.STORE_DIR.glob("bn_*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = __import__("json").load(f)
        except Exception:
            continue
        if d.get("state") != "pending_debate":
            continue
        age = _pending_age_hours(d, now_utc)
        if age is None or age <= PENDING_MAX_AGE_HOURS:
            continue
        src = d.get("source") or {}
        triage = d.get("triage") or {}
        out.append({
            "news_id": d.get("news_id"),
            "headline": d.get("headline"),
            "headline_zh": d.get("headline_zh"),
            "source": src.get("name"),
            "credibility": src.get("credibility"),
            "url": src.get("url"),
            "published": src.get("published"),
            "fetched_at": d.get("fetched_at"),
            "age_hours": round(age, 2),
            "shallow_score": triage.get("shallow_score"),
            "news_type": triage.get("news_type"),
            "binary_flag": triage.get("binary_flag"),
        })
    out.sort(key=lambda x: x.get("fetched_at") or "", reverse=True)
    return out


def scan_and_debate(workers: int = PARALLEL, verbose: bool = False) -> dict:
    recover_orphaned_debates()
    ids = scan_pending()
    if not ids:
        return {"ok": True, "items_processed": 0, "ids": []}
    completed = 0
    failed = 0
    deferred = 0
    started = _utc_iso()
    store.update_state("debater", {
        "scan_started_at": started, "queue_depth": len(ids), "in_flight": [],
    })

    in_flight: set[str] = set()

    def _worker(nid: str) -> dict:
        in_flight.add(nid)
        store.update_state("debater", {"in_flight": sorted(in_flight)})
        try:
            return debate_item(nid, verbose=verbose)
        finally:
            in_flight.discard(nid)
            store.update_state("debater", {"in_flight": sorted(in_flight)})

    # `workers` remains in the public CLI/API for compatibility, but exclusive
    # provider slots make values above one unsafe for a fixed two-model roster.
    for nid in ids:
        res = _worker(nid)
        if res.get("deferred"):
            deferred += 1
        elif res.get("ok") and res.get("state") in ("closed", "partial_closed"):
            completed += 1
        else:
            failed += 1

    store.update_state("debater", {
        "scan_ended_at": _utc_iso(),
        "completed_in_scan": completed,
        "failed_in_scan": failed,
        "deferred_in_scan": deferred,
        "queue_depth": 0,
    })
    return {"ok": True, "items_processed": len(ids),
            "completed": completed, "failed": failed, "deferred": deferred,
            "ids": ids}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--news-id", help="Debate a single item")
    ap.add_argument("--scan", action="store_true", help="Find all pending and debate")
    ap.add_argument("--workers", type=int, default=PARALLEL)
    ap.add_argument("--max-rounds", type=int, default=MAX_ROUNDS)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.news_id:
        res = debate_item(args.news_id, max_rounds=args.max_rounds, verbose=args.verbose)
        print(res)
        return 0 if res.get("ok") else 1
    if args.scan:
        res = scan_and_debate(workers=args.workers, verbose=args.verbose)
        print(res)
        return 0
    print("nothing to do (use --news-id or --scan)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

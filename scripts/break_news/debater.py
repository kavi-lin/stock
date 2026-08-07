"""Break-news debate orchestrator (V6 blind-open + strict divergence gate).

State machine per item:
    pending_debate ─► debating ─► closed / partial_closed / failed

Round 1: both debaters (Claude=Analyst-A, Gemini=Analyst-B) evaluate the item
BLIND in parallel — neither sees the other, so divergence is a genuine signal.
A deterministic gate (0 LLM) then decides whether ONE rebuttal round is worth
the tokens. V6 tightening (V5 hit max_rounds on 69% of items): the gate
re-opens only on a TRUE conflict — opposite verdicts or opposite relation
polarity on the same pair. A confidence gap alone counts only for
high-priority items and only when ≥ DIVERGENCE_CONF_GAP (default 0.65).
Max 2 rounds for everyone (4 calls worst case, 2 typical). Items flagged
`cluster.escalated` get the prior cluster conclusion in the opener prompt and
argue only the increment.

Run modes:
  --news-id <id>     Debate a single item (testing)
  --scan             Loop: find pending_debate items, debate them
  --workers N        Parallel debates (default 1; bounded by BREAK_NEWS_PARALLEL)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.break_news import store, prompts  # noqa: E402
from scripts.break_news.llm_drivers import (  # noqa: E402, F401
    run_llm, load_llm_config, break_news_pair, LLMResult)
from scripts._shared import broker_gate  # noqa: E402
from scripts._shared.model_router import run_with_fallback  # noqa: E402

MAX_ROUNDS = int(os.environ.get("BREAK_NEWS_MAX_ROUNDS", "2"))
MAX_ROUNDS_FUTU = int(os.environ.get("BREAK_NEWS_MAX_ROUNDS_FUTU", "2"))
THREAD_TIMEOUT_SEC = int(os.environ.get("BREAK_NEWS_THREAD_TIMEOUT_SEC", "480"))
PARALLEL = int(os.environ.get("BREAK_NEWS_PARALLEL", "2"))
# Auto-debate stale-pending guard: items older than this stay in pending_debate
# state but are skipped by scan_and_debate. Surfaced via list_stale_pending()
# so the UI can offer per-item manual triggers. Prevents queue-flood after a
# long idle period (e.g. user opens dashboard 10hr later → no auto burst).
PENDING_MAX_AGE_HOURS = float(os.environ.get("BREAK_NEWS_PENDING_MAX_AGE_HOURS", "2"))

_MODEL_NAMES = {"claude": "Claude", "gemini": "Gemini", "codex": "Codex"}


def _turn_order() -> list[str]:
    """The two debaters — the quota broker's current top two, best first.

    V4.109.0: this used to be a fixed pair in `config/llm_config.json`, chosen
    once and then wrong every time a provider ran out. The broker ranks what can
    actually serve *right now*, across both projects that share these
    subscriptions, so it assigns A and B.

    Falls back to the configured pair when the broker cannot answer, or when it
    names fewer than two: a debate needs two voices to be a debate, and handing
    back a one-element list here would quietly turn every debate into a
    monologue. The per-call gate then refuses whichever voice it must, which
    lands in the existing `single_voice` / `cli_failures` paths rather than in a
    new one.

    A and B are symmetric — round 1 is two blind parallel openers — so the order
    only decides which model is labelled A in the transcript.
    """
    # `cfg` is passed explicitly: without it `broker_gate` falls back to its own
    # defaults and silently ignores the `broker` block in llm_config.json —
    # including a base_url or an `enabled: false` the operator set there.
    ranked = broker_gate.ranked_models("debate", count=2, cfg=load_llm_config())
    if ranked is not None and len(ranked) >= 2:
        return ranked
    return break_news_pair()


def _role_for(idx: int, model: str) -> dict:
    """Role label for the debater at a turn position. Side (A/B) is positional;
    the model name is appended so the transcript shows who spoke."""
    side = "A" if idx == 0 else "B"
    name = _MODEL_NAMES.get(model, model.title())
    return {"en": f"Analyst-{side} ({name})", "zh": f"分析師 {side} ({name})"}


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_done(parsed: dict | None, raw_text: str) -> bool:
    if parsed and parsed.get("done") is True:
        return True
    if raw_text and "<DONE>" in raw_text:
        return True
    return False


def _comment_from_result(res: LLMResult, role: str, side: str, round_idx: int,
                         news_id: str, comment_id_hint: str) -> dict:
    parsed = res.parsed
    if not parsed:
        # Build a salvage record so downstream merge still has something to chew.
        snippet = (res.raw_text or res.raw_stdout or "")[:200]
        parsed = {
            "commentary": snippet,
            "entities": {"tickers": [], "sectors": [], "themes": [], "tech_keywords": []},
            "relations": [],
            "done": False,
            "confidence": 0.0,
            "rationale_short": "parse_failed",
        }
    raw_path = ""
    if res.parse_status != "ok":
        raw_path = store.write_raw_stdout(news_id, comment_id_hint, res.raw_stdout)
    return {
        "agent": res.agent,
        "agent_role_label": role,
        "side": side,
        "round": round_idx,
        "ts": _utc_iso(),
        "latency_ms": res.latency_ms,
        "raw_stdout_path": raw_path,
        "parsed": parsed,
        "parse_status": res.parse_status,
        "exit_code": res.exit_code,
    }


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


def divergence_gate(thread: list[dict], is_high: bool = False) -> tuple[bool, str]:
    """Deterministic (0 LLM) check: is a rebuttal round worth the tokens?

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
                m.setdefault(f"{r.get('subject')}|{r.get('object')}", set()).add(sign)
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

    store.set_state(news_id, "debating")

    turn_order = _turn_order()
    t0 = time.time()
    consecutive_failures = {m: 0 for m in turn_order}
    last_done = {m: False for m in turn_order}
    close_reason = "max_rounds"
    state_final = "closed"
    div_note = ""

    # ── Round 1: blind parallel openers ─────────────────────────────────
    def _opener_call(idx_agent: tuple[int, str]):
        idx, agent = idx_agent
        usr_p = prompts.opener_user_prompt(item, _role_for(idx, agent))
        if verbose:
            print(f"[{news_id}] round=0 agent={agent} (blind) prompt_len={len(usr_p)}")
        return idx, agent, run_with_fallback(agent, "debate", prompts.SYSTEM_PROMPT, usr_p)

    with ThreadPoolExecutor(max_workers=len(turn_order)) as ex:
        opener_results = sorted(ex.map(_opener_call, enumerate(turn_order)))

    opener_failures = 0
    for idx, agent, res in opener_results:
        actual = getattr(res, "model_used", res.agent) or agent
        side = "A" if idx == 0 else "B"
        comment = _comment_from_result(res, _role_for(idx, actual), side, 0,
                                       news_id, f"c{idx}")
        store.append_comment(news_id, comment)
        if res.exit_code != 0:
            opener_failures += 1
            consecutive_failures[agent] += 1
            store.push_error(news_id, f"round0.{agent}",
                             f"rc={res.exit_code} err={res.error}")
        last_done[agent] = _is_done(res.parsed, res.raw_text)
        if verbose:
            print(f"  agent={agent} done={last_done[agent]} "
                  f"parse_status={res.parse_status} rc={res.exit_code}")
    rounds_completed = 1

    if opener_failures == len(turn_order):
        close_reason = "cli_failures"
        state_final = "failed"
    elif opener_failures > 0:
        # One voice down → no real debate possible. Close on the healthy
        # opener instead of burning rebuttal calls against a salvage record.
        close_reason = "single_voice"
        state_final = "partial_closed"

    # ── Rounds 2+: divergence-gated slim rebuttals ──────────────────────
    for r in range(1, max_rounds):
        if state_final != "closed":
            break
        if all(last_done[m] for m in turn_order):
            close_reason = "both_done"
            break

        thread = (store.load_item(news_id) or item).get("thread") or []
        if not is_high and _low_relation_density(thread, item):
            close_reason = "early_stop_low_relation_density"
            break

        divergent, div_note = divergence_gate(thread, is_high)
        if not divergent:
            close_reason = "converged_round1" if r == 1 else "divergence_resolved"
            break

        for idx, agent in enumerate(turn_order):
            if time.time() - t0 > wall_timeout:
                close_reason = "timeout"
                state_final = "partial_closed"
                break
            role = _role_for(idx, agent)
            side = "A" if idx == 0 else "B"
            thread = (store.load_item(news_id) or item).get("thread") or []
            usr_p = prompts.rebuttal_user_prompt(item, thread, role, side, div_note)
            if verbose:
                print(f"[{news_id}] round={r} agent={agent} rebuttal "
                      f"prompt_len={len(usr_p)}")
            res = run_with_fallback(agent, "debate",
                                    prompts.REBUTTAL_SYSTEM_PROMPT, usr_p)
            actual = getattr(res, "model_used", res.agent) or agent
            if actual != agent:
                role = _role_for(idx, actual)
            comment = _comment_from_result(res, role, side, r, news_id,
                                           f"c{len(thread)}")
            store.append_comment(news_id, comment)

            if res.exit_code != 0:
                consecutive_failures[agent] += 1
                store.push_error(news_id, f"round{r}.{agent}",
                                 f"rc={res.exit_code} err={res.error}")
                if consecutive_failures[agent] >= 2:
                    close_reason = "cli_failures"
                    state_final = "failed"
                    break
            else:
                consecutive_failures[agent] = 0

            last_done[agent] = _is_done(res.parsed, res.raw_text)
            if verbose:
                print(f"  done={last_done[agent]} parse_status={res.parse_status} "
                      f"rc={res.exit_code}")

        rounds_completed = r + 1

    final_thread = (store.load_item(news_id) or {}).get("thread") or []

    # Relabel when the loop exhausted max_rounds but the last rebuttal round
    # actually resolved the conflict (concession / convergence).
    if state_final == "closed" and close_reason == "max_rounds":
        still_divergent, note = divergence_gate(final_thread, is_high)
        if not still_divergent:
            close_reason = "divergence_resolved"
        div_note = note if still_divergent else div_note
    summary = prompts.build_summary_block(final_thread)
    summary["rounds_completed"] = rounds_completed
    summary["closed_at"] = _utc_iso()
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
    ids = scan_pending()
    if not ids:
        return {"ok": True, "items_processed": 0, "ids": []}
    completed = 0
    failed = 0
    started = _utc_iso()
    store.update_state("debater", {
        "scan_started_at": started, "queue_depth": len(ids), "in_flight": [],
    })

    lock = threading.Lock()
    in_flight: set[str] = set()

    def _worker(nid: str) -> dict:
        with lock:
            in_flight.add(nid)
            store.update_state("debater", {"in_flight": sorted(in_flight)})
        try:
            return debate_item(nid, verbose=verbose)
        finally:
            with lock:
                in_flight.discard(nid)
                store.update_state("debater", {"in_flight": sorted(in_flight)})

    workers = max(1, min(workers, PARALLEL))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(_worker, ids):
            if res.get("ok") and res.get("state") in ("closed", "partial_closed"):
                completed += 1
            else:
                failed += 1

    store.update_state("debater", {
        "scan_ended_at": _utc_iso(),
        "completed_in_scan": completed,
        "failed_in_scan": failed,
        "queue_depth": 0,
    })
    return {"ok": True, "items_processed": len(ids),
            "completed": completed, "failed": failed, "ids": ids}


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

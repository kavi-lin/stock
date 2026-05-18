"""Break-news debate orchestrator.

State machine per item:
    pending_debate ─► debating ─► closed / partial_closed / failed

Alternates Claude (Analyst-A) and Gemini (Analyst-B). Each round, the
responding agent sees the full prior thread and must either add a new point
or signal `<DONE>` / `done:true`. Thread closes when both DONE signals are
emitted consecutively, OR max rounds hit, OR total wall-clock budget exceeded.

Run modes:
  --news-id <id>     Debate a single item (testing)
  --scan             Loop: find pending_debate items, debate them
  --workers N        Parallel debates (default 1; bounded by BREAK_NEWS_PARALLEL)
"""
from __future__ import annotations

import argparse
import os
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
from scripts._shared.model_router import run_with_fallback  # noqa: E402

MAX_ROUNDS = int(os.environ.get("BREAK_NEWS_MAX_ROUNDS", "3"))
MAX_ROUNDS_FUTU = int(os.environ.get("BREAK_NEWS_MAX_ROUNDS_FUTU", "2"))
THREAD_TIMEOUT_SEC = int(os.environ.get("BREAK_NEWS_THREAD_TIMEOUT_SEC", "480"))
PARALLEL = int(os.environ.get("BREAK_NEWS_PARALLEL", "2"))

_MODEL_NAMES = {"claude": "Claude", "gemini": "Gemini", "codex": "Codex"}


def _turn_order() -> list[str]:
    """The two debaters — read from the dedicated `break_news` config section
    (independent of the general primary/secondary chain). Falls back to
    claude↔gemini if that section is missing/invalid."""
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


def debate_item(news_id: str, max_rounds: int = MAX_ROUNDS,
                wall_timeout: int = THREAD_TIMEOUT_SEC,
                verbose: bool = False) -> dict:
    item = store.load_item(news_id)
    if item is None:
        return {"ok": False, "error": f"unknown news_id={news_id}"}
    if item.get("state") not in ("pending_debate", "partial_closed", "failed"):
        return {"ok": False, "error": f"state={item.get('state')}, refusing"}

    if item.get("source") == "Futu Push" and max_rounds == MAX_ROUNDS:
        max_rounds = MAX_ROUNDS_FUTU

    store.set_state(news_id, "debating")

    turn_order = _turn_order()
    t0 = time.time()
    rounds_completed = 0
    consecutive_failures = {m: 0 for m in turn_order}
    last_done = {m: False for m in turn_order}
    close_reason = "max_rounds"
    state_final = "closed"

    for r in range(max_rounds):
        for idx, agent in enumerate(turn_order):
            if time.time() - t0 > wall_timeout:
                close_reason = "timeout"
                state_final = "partial_closed"
                break
            role = _role_for(idx, agent)
            thread = (store.load_item(news_id) or item).get("thread") or []
            sys_p = prompts.SYSTEM_PROMPT
            usr_p = (prompts.opener_user_prompt(item, role) if not thread
                     else prompts.followup_user_prompt(item, thread, role))
            comment_id_hint = f"c{len(thread)}"
            if verbose:
                print(f"[{news_id}] round={r} agent={agent} prompt_len={len(usr_p)}")
            # Governed call: prefer this turn's intended model, but fall back
            # down the chain (quota / failure) instead of aborting the debate.
            res = run_with_fallback(agent, "debate", sys_p, usr_p)
            # If fallback swapped the model, relabel the role so the stored
            # role name matches res.agent (side A/B stays positional).
            actual = getattr(res, "model_used", res.agent) or agent
            if actual != agent:
                role = _role_for(idx, actual)
            side = "A" if idx == 0 else "B"
            comment = _comment_from_result(res, role, side, r, news_id, comment_id_hint)
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
        if state_final in ("failed", "partial_closed"):
            break
        # Stop when both debaters signalled DONE in this round.
        if all(last_done[m] for m in turn_order):
            close_reason = "both_done"
            break

    summary = prompts.build_summary_block((store.load_item(news_id) or {}).get("thread") or [])
    summary["rounds_completed"] = rounds_completed
    summary["closed_at"] = _utc_iso()
    summary["close_reason"] = close_reason
    summary["divergence_note"] = _divergence_note(
        (store.load_item(news_id) or {}).get("thread") or []
    )
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


def scan_pending(max_items: int = 100) -> list[str]:
    out = []
    for p in sorted(store.STORE_DIR.glob("bn_*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = __import__("json").load(f)
        except Exception:
            continue
        if d.get("state") == "pending_debate":
            out.append(d.get("news_id"))
            if len(out) >= max_items:
                break
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

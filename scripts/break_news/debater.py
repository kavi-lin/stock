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


def debate_item(news_id: str, max_rounds: int = MAX_ROUNDS,
                wall_timeout: int = THREAD_TIMEOUT_SEC,
                verbose: bool = False) -> dict:
    item = store.load_item(news_id)
    if item is None:
        return {"ok": False, "error": f"unknown news_id={news_id}"}
    if item.get("state") not in ("pending_debate", "partial_closed", "failed"):
        return {"ok": False, "error": f"state={item.get('state')}, refusing"}

    # Dynamic depth policy
    is_high = is_high_priority_item(item)
    rounds_limit = 3 if is_high else 2
    max_rounds = min(max_rounds, rounds_limit)

    if (item.get("source") or {}).get("name") == "Futu Push" and max_rounds == MAX_ROUNDS:
        max_rounds = min(max_rounds, MAX_ROUNDS_FUTU)

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
            res = run_with_fallback(agent, "debate", sys_p, usr_p)
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

        # At the end of Round 1 (r == 0), check for early stop on low relation density / neutrality
        if r == 0 and not is_high:
            # 1. Both debaters set done: true
            cond_done = all(last_done[m] for m in turn_order)
            
            # 2. No ticker-to-ticker relation generated (both subject and object start with "ticker:")
            thread = (store.load_item(news_id) or item).get("thread") or []
            has_ticker_relation = False
            for c in thread:
                relations = (c.get("parsed") or {}).get("relations") or []
                for rel in relations:
                    if isinstance(rel, dict):
                        subj = rel.get("subject") or ""
                        obj = rel.get("object") or ""
                        if subj.startswith("ticker:") and obj.startswith("ticker:"):
                            has_ticker_relation = True
                            break
                if has_ticker_relation:
                    break
            cond_no_ticker_rel = not has_ticker_relation
            
            # 3. Consensus verdict is "NEUTRAL" AND no ticker in thread/text is in universe_tickers
            temp_summary = prompts.build_summary_block(thread)
            verdict = temp_summary.get("consensus_verdict", "NEUTRAL")
            cond_neutral_no_universe = False
            if verdict == "NEUTRAL":
                universe_tickers = _load_universe_tickers()
                headline = item.get("headline") or ""
                summary = item.get("raw_summary") or ""
                text_to_check = f"{headline} {summary}"
                words = set(re.findall(r"\b[A-Z]{2,5}\b", text_to_check))
                for c in thread:
                    parsed = c.get("parsed") or {}
                    ent = parsed.get("entities") or {}
                    for t in ent.get("tickers") or []:
                        if isinstance(t, str):
                            words.add(t.upper())
                has_universe_ticker = any(w in universe_tickers for w in words)
                cond_neutral_no_universe = not has_universe_ticker

            if cond_done or cond_no_ticker_rel or cond_neutral_no_universe:
                close_reason = "early_stop_low_relation_density"
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

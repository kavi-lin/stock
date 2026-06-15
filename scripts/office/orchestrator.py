"""AI Office — autonomous multi-agent collaboration loop.

Drives a task to completion by running a small team of role-pinned CLI agents
(roles.py) round-robin via the project's existing model_router driver — which
gives per-model daily budgets, quota cooldown, and fallback for free. Reuses the
same `claude -p` / `agy --print` / `codex exec` engines Break News already runs,
so it adds **no new billing surface** beyond the project's existing usage.

Each turn is a structured JSON envelope (roles.ENVELOPE_SPEC) appended to the
run's event log; the loop ends when every role reports done, or a round / wall /
budget cap is hit. A final Lead pass composes the deliverable markdown.

Stop is cooperative: the server sets a flag; the loop checks it between turns.
"""

import argparse
import json
import os
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.office import roles as roles_mod  # noqa: E402
from scripts.office import store  # noqa: E402
from scripts._shared import model_router  # noqa: E402
from scripts.break_news import llm_drivers  # noqa: E402

MAX_ROUNDS = int(os.getenv("OFFICE_MAX_ROUNDS", "3"))
WALL_TIMEOUT_SEC = int(os.getenv("OFFICE_WALL_TIMEOUT_SEC", "1800"))
PER_CALL_TIMEOUT = int(os.getenv("OFFICE_CALL_TIMEOUT_SEC",
                                 str(getattr(llm_drivers, "LLM_TIMEOUT_SEC", 180))))

# run_id -> threading.Event (set => cooperative stop requested)
_stop_flags = {}
_reg_lock = threading.Lock()


class _Stopped(Exception):
    pass


def request_stop(run_id):
    with _reg_lock:
        ev = _stop_flags.get(run_id)
    if ev:
        ev.set()
        return True
    return False


def is_running(run_id):
    with _reg_lock:
        return run_id in _stop_flags


# ── prompt building ──────────────────────────────────────────────────────
def _render_transcript(transcript):
    if not transcript:
        return "(empty — you are first)"
    lines = []
    for t in transcript:
        concerns = t.get("concerns") or []
        lines.append(
            f"[Round {t['round'] + 1}] {t['name']} ({t.get('engine_used') or t['engine']}) "
            f"— done={t.get('done')}\n"
            f"  summary: {t.get('summary', '')}\n"
            f"  detail: {t.get('detail', '')}\n"
            + (f"  concerns: {'; '.join(map(str, concerns))}\n" if concerns else "")
        )
    return "\n".join(lines)


def _user_prompt(task, transcript, role, round_idx):
    return (
        f"TASK:\n{task}\n\n"
        f"TRANSCRIPT SO FAR:\n{_render_transcript(transcript)}\n\n"
        f"You are {role.name} ({role.key}). This is round {round_idx + 1}. "
        f"Give your next contribution from your role, as the JSON envelope."
    )


def _parse_envelope(res, role):
    """Coerce an LLMResult into the turn envelope, tolerating non-JSON replies."""
    p = res.parsed if isinstance(res.parsed, dict) else None
    if p:
        concerns = p.get("concerns")
        if isinstance(concerns, str):
            concerns = [concerns]
        elif not isinstance(concerns, list):
            concerns = []
        return {
            "summary": str(p.get("summary") or "")[:400],
            "detail": str(p.get("detail") or res.raw_text or ""),
            "concerns": [str(c) for c in concerns][:20],
            "done": bool(p.get("done")),
        }
    # Fallback: model didn't emit clean JSON — keep the raw text, treat as not-done.
    raw = (res.raw_text or res.raw_stdout or "").strip()
    first = raw.splitlines()[0] if raw else "(no output)"
    return {"summary": first[:400], "detail": raw, "concerns": [], "done": False}


# ── core loop ────────────────────────────────────────────────────────────
def orchestrate(run_id, task, team=None, max_rounds=MAX_ROUNDS):
    team = team or roles_mod.DEFAULT_TEAM
    stop = threading.Event()
    with _reg_lock:
        _stop_flags[run_id] = stop

    t0 = time.time()
    transcript = []
    rounds_completed = 0
    close_reason = "max_rounds"
    status = "done"
    err = None
    try:
        for r in range(max_rounds):
            last_done = {}
            for role in team:
                if stop.is_set():
                    close_reason, status = "stopped", "stopped"
                    raise _Stopped()
                if time.time() - t0 > WALL_TIMEOUT_SEC:
                    close_reason = "wall_timeout"
                    raise _Stopped()

                store.append_event(run_id, {
                    "type": "turn_started", "role": role.key,
                    "name": role.name, "engine": role.engine, "round": r,
                })
                res = model_router.run_with_fallback(
                    role.engine, "office", role.system_prompt,
                    _user_prompt(task, transcript, role, r),
                    timeout=PER_CALL_TIMEOUT,
                )
                engine_used = getattr(res, "model_used", None) or role.engine
                store.bump_spend(run_id, engine_used)

                if res.exit_code == -9:  # every model unavailable (budget/cooldown)
                    store.append_event(run_id, {
                        "type": "error", "role": role.key,
                        "message": "all models unavailable (budget / cooldown)",
                        "route_note": getattr(res, "route_note", ""),
                    })
                    close_reason, status = "no_models", "failed"
                    err = "all models unavailable"
                    raise _Stopped()

                env = _parse_envelope(res, role)
                turn = {
                    "type": "turn", "role": role.key, "name": role.name,
                    "engine": role.engine, "engine_used": engine_used,
                    "fell_back": bool(getattr(res, "fell_back", False)),
                    "round": r, "rc": res.exit_code,
                    "parse_status": res.parse_status,
                    "latency_ms": res.latency_ms, **env,
                }
                transcript.append(turn)
                store.append_event(run_id, turn)
                last_done[role.key] = env["done"] and res.exit_code == 0

            rounds_completed = r + 1
            store.update_meta(run_id, rounds_completed=rounds_completed)
            store.append_event(run_id, {"type": "round_complete", "round": r,
                                        "all_done": all(last_done.values())})
            if all(last_done.get(role.key) for role in team):
                close_reason = "all_done"
                break

        # ── compose final deliverable (Lead engine, direct driver) ─────────
        if status == "done":
            store.append_event(run_id, {"type": "composing"})
            compose_usr = (
                f"TASK:\n{task}\n\nFULL TEAM TRANSCRIPT:\n"
                f"{_render_transcript(transcript)}\n\n"
                "Write the final deliverable markdown for the user now."
            )
            cres = llm_drivers.run_claude(roles_mod.COMPOSE_SYSTEM, compose_usr,
                                          timeout=PER_CALL_TIMEOUT)
            store.bump_spend(run_id, "claude")
            model_router.note_run("claude", cres.exit_code == 0,
                                  cres.error or "")
            deliverable = (cres.raw_text or cres.raw_stdout or "").strip() \
                or "_(compose step produced no output)_"
            store.write_deliverable(run_id, deliverable)
            store.append_event(run_id, {"type": "deliverable",
                                        "markdown": deliverable})

    except _Stopped:
        pass
    except Exception as e:  # noqa: BLE001
        status, close_reason, err = "failed", "exception", str(e)[:500]
        store.append_event(run_id, {"type": "error", "message": err})
    finally:
        with _reg_lock:
            _stop_flags.pop(run_id, None)
        store.set_terminal(run_id, status, close_reason=close_reason, error=err)
        store.append_event(run_id, {"type": "run_finished", "status": status,
                                    "close_reason": close_reason,
                                    "rounds_completed": rounds_completed})
    return {"run_id": run_id, "status": status, "close_reason": close_reason,
            "rounds_completed": rounds_completed}


def start_run(task, team=None, max_rounds=MAX_ROUNDS):
    """Create a run + launch the loop in a background thread. Returns meta."""
    team = team or roles_mod.DEFAULT_TEAM
    run_id, meta = store.create_run(task, team)
    threading.Thread(
        target=orchestrate, args=(run_id, task, team, max_rounds),
        daemon=True, name=f"office_run_{run_id}",
    ).start()
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--max-rounds", type=int, default=MAX_ROUNDS)
    args = ap.parse_args()
    run_id, _ = store.create_run(args.task, roles_mod.DEFAULT_TEAM)
    print(f"run_id={run_id}")
    result = orchestrate(run_id, args.task, max_rounds=args.max_rounds)
    print(json.dumps(result, ensure_ascii=False))
    print("deliverable:\n" + (store.load_deliverable(run_id) or "(none)"))
    return 0 if result["status"] == "done" else 1


if __name__ == "__main__":
    sys.exit(main())

"""AI Office — parallel-debate pipeline (v2).

Replaces the round-robin transcript loop: every turn used to re-read the full
transcript (O(rounds²) tokens) and roles spent turns reacting to each other in
sequence. v2 runs four phases (roles.py has the prompt contracts):

  1. drafts      — the four role-pinned engines (claude/gemini/codex/grok)
                   answer the task in parallel, blind to each other.
                   Cross-read tokens: zero.
  2. adjudicate  — one structured pass diffs the drafts into consensus vs. a
                   numbered disagreement list (max OFFICE_MAX_DISAGREEMENTS).
  3. rebuttals   — each disagreement goes only to the roles holding a stance,
                   with only that disagreement as context.
  4. verdict     — a strong model (OFFICE_STRONG_MODEL, default opus) rules on
                   each disagreement and writes the final deliverable.

The claude legs run text-only (`--max-turns 1 --strict-mcp-config` + pinned
model): a bare `claude -p` in this repo goes agentic on analysis prompts and
times out, which is why Lead used to show "(no output)".

Events append to the run's JSONL (store.py) for the SSE UI. Stop is
cooperative: checked between calls; in-flight CLI calls finish first.
"""

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.office import roles as roles_mod  # noqa: E402
from scripts.office import store  # noqa: E402
from scripts._shared import model_router  # noqa: E402
from scripts.break_news import llm_drivers  # noqa: E402

MAX_ROUNDS = int(os.getenv("OFFICE_MAX_ROUNDS", "3"))  # legacy API compat only
WALL_TIMEOUT_SEC = int(os.getenv("OFFICE_WALL_TIMEOUT_SEC", "1800"))
PER_CALL_TIMEOUT = int(os.getenv("OFFICE_CALL_TIMEOUT_SEC",
                                 str(getattr(llm_drivers, "LLM_TIMEOUT_SEC", 180))))
VERDICT_TIMEOUT = int(os.getenv("OFFICE_VERDICT_TIMEOUT_SEC", "300"))
# grok CLI regularly needs 90-150s even on small prompts (no web search, long
# reasoning) — the shared 180s cap made the Trader leg a coin flip.
GROK_TIMEOUT = int(os.getenv("OFFICE_GROK_TIMEOUT_SEC", "300"))
# Research pass reads the repo's data caches agentically — allow extra time.
RESEARCH_TIMEOUT = int(os.getenv("OFFICE_RESEARCH_TIMEOUT_SEC", "240"))
# claude legs: debate turns are text-only reasoning — pin a fast model for
# drafts/rebuttals and a strong one for the final verdict.
CLAUDE_DRAFT_MODEL = os.getenv("OFFICE_CLAUDE_MODEL", "sonnet")
STRONG_MODEL = os.getenv("OFFICE_STRONG_MODEL", "opus")
MAX_DISAGREEMENTS = int(os.getenv("OFFICE_MAX_DISAGREEMENTS", "5"))

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


# ── engine calls ─────────────────────────────────────────────────────────
def _call_claude_text(system_prompt, user_prompt, model, timeout):
    """Text-only claude turn: pinned model, no agentic loop, no MCP startup,
    no built-in tools. One retry — headless `claude -p` occasionally fails
    transiently even on prompts that normally succeed in under a minute.

    V4.106.0: each attempt takes a quota reservation first. This path calls the
    driver directly rather than through `run_with_fallback`, so before the broker
    it was reported to the budget afterwards but gated by nothing — and a retry
    doubled the spend. The Office is a decision-bearing flow, so a broker that
    cannot answer stops it (fail-closed) rather than falling back to the local
    counters; the caller already handles a failed `LLMResult`.
    """
    res = None
    for _attempt in range(2):
        try:
            with model_router.governed_call("office", "claude",
                                            system_prompt, user_prompt) as hold:
                res = llm_drivers.run_claude(system_prompt, user_prompt, timeout=timeout,
                                             model=model, max_turns=1, strict_mcp=True,
                                             no_tools=True)
                hold.settle(res)
        except model_router.RunBlocked as blocked:
            res = llm_drivers.LLMResult(
                agent="claude", parsed=None, raw_text="", raw_stdout="",
                exit_code=-9, latency_ms=0, parse_status="failed", error=str(blocked))
            model_router.note_run("claude", False, str(blocked))
            break
        model_router.note_run("claude", res.exit_code == 0, res.error or "")
        if res.exit_code == 0:
            break
    res.model_used = f"claude:{model}"
    res.fell_back = False
    return res


def _call_role(role, system_prompt, user_prompt, timeout=PER_CALL_TIMEOUT):
    """One structured call on the role's pinned engine, with one retry when the
    reply has no extractable JSON (grok especially is flaky about envelope
    discipline; a second attempt usually lands)."""
    if role.engine == "grok":
        timeout = max(timeout, GROK_TIMEOUT)
    res = None
    for _attempt in range(2):
        if role.engine == "claude":
            res = _call_claude_text(system_prompt, user_prompt,
                                    CLAUDE_DRAFT_MODEL, timeout)
        else:
            res = model_router.run_with_fallback(role.engine, "office",
                                                 system_prompt, user_prompt,
                                                 timeout=timeout)
        if res.exit_code == 0 and isinstance(res.parsed, dict):
            break
    return res


# ── phase 0: research (gemini reads the repo's fresh caches; facts only) ──
def _research(run_id, task):
    """Returns a rendered fact pack ('' when research fails — drafts proceed
    without it rather than blocking the debate)."""
    role = roles_mod.RESEARCHER
    store.append_event(run_id, {"type": "research_started", "role": role.key,
                                "name": role.name, "engine": role.engine})
    res = _call_role(role, role.system_prompt, f"TASK:\n{task}",
                     timeout=RESEARCH_TIMEOUT)
    store.bump_spend(run_id, role.engine)
    p = res.parsed if isinstance(res.parsed, dict) else {}
    facts = [f for f in (p.get("facts") or []) if isinstance(f, dict)
             and str(f.get("fact") or "").strip()][:12]
    gaps = [str(g) for g in (p.get("gaps") or [])][:8]
    store.append_event(run_id, {
        "type": "research", "role": role.key, "name": role.name,
        "engine_used": getattr(res, "model_used", None) or role.engine,
        "rc": res.exit_code, "parse_status": res.parse_status,
        "latency_ms": res.latency_ms,
        "summary": str(p.get("summary") or "")[:400],
        "facts": [{"fact": str(f.get("fact")), "source": str(f.get("source") or "?")}
                  for f in facts],
        "gaps": gaps,
        "ok": res.exit_code == 0 and bool(facts),
    })
    if not facts:
        return ""
    lines = ["REFERENCE DATA（資料官已蒐集的事實，作為共同依據；可指出其不足）:"]
    lines += [f"- {f['fact']}（來源: {f.get('source', '?')}）" for f in facts]
    if gaps:
        lines.append("已知資料缺口: " + "；".join(gaps))
    return "\n".join(lines)


# ── phase 1: parallel drafts ─────────────────────────────────────────────
def _draft_one(run_id, task, role, fact_pack=""):
    store.append_event(run_id, {"type": "draft_started", "role": role.key,
                                "name": role.name, "engine": role.engine})
    usr = f"TASK:\n{task}" + (f"\n\n{fact_pack}" if fact_pack else "")
    res = _call_role(role, role.system_prompt, usr)
    engine_used = getattr(res, "model_used", None) or role.engine
    store.bump_spend(run_id, role.engine)
    p = res.parsed if isinstance(res.parsed, dict) else {}
    raw = (res.raw_text or res.raw_stdout or "").strip()
    claims = p.get("claims")
    if not isinstance(claims, list):
        claims = []
    draft = {
        "type": "draft", "role": role.key, "name": role.name,
        "engine": role.engine, "engine_used": engine_used,
        "rc": res.exit_code, "parse_status": res.parse_status,
        "latency_ms": res.latency_ms,
        "summary": str(p.get("summary") or (raw.splitlines()[0] if raw else "(no output)"))[:400],
        "detail": str(p.get("detail") or raw),
        "claims": [str(c) for c in claims][:8],
        "ok": res.exit_code == 0 and bool(p or raw),
    }
    store.append_event(run_id, draft)
    return draft


# ── phase 2: adjudication ────────────────────────────────────────────────
def _render_drafts(drafts):
    parts = []
    for d in drafts:
        claims = "\n".join(f"  - {c}" for c in d["claims"]) or "  (no claims list)"
        parts.append(f"[{d['role']}] summary: {d['summary']}\n"
                     f"claims:\n{claims}\ndetail:\n{d['detail']}\n")
    return "\n---\n".join(parts)


def _adjudicate(run_id, task, drafts):
    usr = (f"TASK:\n{task}\n\nTHREE INDEPENDENT DRAFTS:\n"
           f"{_render_drafts(drafts)}")
    res = _call_claude_text(roles_mod.ADJUDICATE_SYSTEM, usr,
                            CLAUDE_DRAFT_MODEL, PER_CALL_TIMEOUT)
    store.bump_spend(run_id, "claude")
    if not (res.exit_code == 0 and isinstance(res.parsed, dict)):
        # one retry on a different engine before giving up on structure
        res = model_router.run_with_fallback(
            "gemini", "office", roles_mod.ADJUDICATE_SYSTEM, usr,
            timeout=PER_CALL_TIMEOUT)
        store.bump_spend(run_id, "gemini")
    p = res.parsed if isinstance(res.parsed, dict) else {}
    consensus = [str(c) for c in p.get("consensus") or [] if str(c).strip()]
    dis = []
    for i, d in enumerate(p.get("disagreements") or []):
        if not isinstance(d, dict):
            continue
        positions = d.get("positions") if isinstance(d.get("positions"), dict) else {}
        positions = {k: str(v) for k, v in positions.items()
                     if k in ("lead", "critic", "verifier", "trader")
                     and str(v).strip()}
        if len(positions) < 1:
            continue
        dis.append({"id": str(d.get("id") or f"D{i + 1}"),
                    "topic": str(d.get("topic") or "")[:120],
                    "positions": positions,
                    "crux": str(d.get("crux") or "")})
    dis = dis[:MAX_DISAGREEMENTS]
    store.append_event(run_id, {"type": "adjudication", "rc": res.exit_code,
                                "parse_status": res.parse_status,
                                "latency_ms": res.latency_ms,
                                "consensus": consensus, "disagreements": dis})
    return consensus, dis


# ── phase 3: targeted rebuttals ──────────────────────────────────────────
def _rebut_one(run_id, task, dis, role):
    store.append_event(run_id, {"type": "rebuttal_started", "role": role.key,
                                "name": role.name, "dis_id": dis["id"]})
    others = "\n".join(f"- {k}: {v}" for k, v in dis["positions"].items()
                       if k != role.key)
    usr = (f"TASK (context only): {task}\n\n"
           f"DISAGREEMENT {dis['id']} — {dis['topic']}\n"
           f"你先前的立場: {dis['positions'].get(role.key, '(未表態)')}\n"
           f"其他人的立場:\n{others or '- (無)'}\n"
           f"CRUX: {dis['crux']}")
    res = _call_role(role, roles_mod.REBUTTAL_SYSTEM, usr)
    store.bump_spend(run_id, role.engine)
    p = res.parsed if isinstance(res.parsed, dict) else {}
    reb = {
        "type": "rebuttal", "role": role.key, "name": role.name,
        "engine_used": getattr(res, "model_used", None) or role.engine,
        "dis_id": dis["id"], "topic": dis["topic"],
        "rc": res.exit_code, "latency_ms": res.latency_ms,
        "stance": str(p.get("stance") or ("maintain" if res.exit_code == 0 else "no_reply")),
        "position": str(p.get("position") or dis["positions"].get(role.key, "")),
        "argument": str(p.get("argument") or "")[:400],
        "evidence": str(p.get("evidence") or ""),
    }
    store.append_event(run_id, reb)
    return reb


# ── phase 4: verdict + deliverable ───────────────────────────────────────
def _render_verdict_input(task, consensus, disagreements, rebuttals):
    lines = [f"TASK:\n{task}", "\nCONSENSUS:"]
    lines += [f"- {c}" for c in consensus] or ["- (無)"]
    for d in disagreements:
        lines.append(f"\nDISAGREEMENT {d['id']} — {d['topic']}\n"
                     f"crux: {d['crux']}")
        for r in rebuttals:
            if r["dis_id"] != d["id"]:
                continue
            lines.append(f"- {r['role']} [{r['stance']}] {r['position']}"
                         f" ｜理由: {r['argument']} ｜證據: {r['evidence']}")
    return "\n".join(lines)


def _fallback_deliverable(consensus, disagreements, rebuttals):
    """Deterministic assembly when the verdict model is unavailable."""
    out = ["## 團隊共識"] + [f"- {c}" for c in (consensus or ["(無)"])]
    if disagreements:
        out.append("\n## 未裁決分歧（裁決模型無回應）")
        for d in disagreements:
            out.append(f"### {d['id']} — {d['topic']}")
            for r in rebuttals:
                if r["dis_id"] == d["id"]:
                    out.append(f"- **{r['role']}** [{r['stance']}] {r['position']}")
    return "\n".join(out)


# ── core pipeline ────────────────────────────────────────────────────────
def orchestrate(run_id, task, team=None, max_rounds=MAX_ROUNDS):  # noqa: ARG001
    team = team or roles_mod.random_team()
    stop = threading.Event()
    with _reg_lock:
        _stop_flags[run_id] = stop

    t0 = time.time()

    def _checkpoint():
        if stop.is_set():
            raise _Stopped("stopped")
        if time.time() - t0 > WALL_TIMEOUT_SEC:
            raise _Stopped("wall_timeout")

    def _phase(idx, key, title):
        _checkpoint()
        store.append_event(run_id, {"type": "phase", "phase": key, "title": title})
        store.update_meta(run_id, phase=key, rounds_completed=idx)

    status, close_reason, err = "done", "all_done", None
    try:
        # 0 — research: gemini gathers a shared fact pack (facts, not opinions)
        _phase(1, "research", "資料蒐集（Researcher）")
        fact_pack = _research(run_id, task)

        # 1 — parallel independent drafts (all seats see the same fact pack)
        _phase(2, "draft", "獨立觀點（平行）")
        with ThreadPoolExecutor(max_workers=len(team)) as pool:
            drafts = list(pool.map(
                lambda r: _draft_one(run_id, task, r, fact_pack), team))
        ok_drafts = [d for d in drafts if d["ok"]]
        if len(ok_drafts) < 2:
            raise RuntimeError(
                f"only {len(ok_drafts)}/{len(team)} drafts succeeded — "
                "not enough to debate")

        # 2 — structured diff: consensus vs disagreements
        _phase(3, "adjudicate", "分歧萃取")
        consensus, disagreements = _adjudicate(run_id, task, ok_drafts)

        # 3 — targeted rebuttals, only where roles actually disagree
        rebuttals = []
        if disagreements:
            _phase(4, "rebuttal", "定點交鋒")
            # Resolve roles from THIS run's team — engines are shuffled per run,
            # so the registry's pinned defaults would misroute the rebuttals.
            team_by_key = {r.key: r for r in team}
            jobs = [(d, team_by_key[k])
                    for d in disagreements for k in d["positions"]
                    if k in team_by_key]
            with ThreadPoolExecutor(max_workers=4) as pool:
                futs = [pool.submit(_rebut_one, run_id, task, d, r)
                        for d, r in jobs]
                for f in futs:
                    rebuttals.append(f.result())
            _checkpoint()

        # 4 — strong-model verdict + deliverable (fact pack included so the
        # ruling can be grounded in the same data the seats debated from)
        _phase(5, "verdict", f"終局裁決（{STRONG_MODEL}）")
        vin = _render_verdict_input(task, consensus, disagreements, rebuttals)
        if fact_pack:
            vin = f"{fact_pack}\n\n{vin}"
        vres = _call_claude_text(roles_mod.VERDICT_SYSTEM, vin,
                                 STRONG_MODEL, VERDICT_TIMEOUT)
        store.bump_spend(run_id, "claude")
        deliverable = (vres.raw_text or vres.raw_stdout or "").strip()
        if vres.exit_code != 0 or not deliverable:
            store.append_event(run_id, {
                "type": "error",
                "message": f"verdict model failed (rc={vres.exit_code}) — "
                           "emitting deterministic assembly instead"})
            deliverable = _fallback_deliverable(consensus, disagreements, rebuttals)
        store.write_deliverable(run_id, deliverable)
        store.append_event(run_id, {"type": "deliverable", "markdown": deliverable})

    except _Stopped as s:
        status = "stopped" if str(s) == "stopped" else "done"
        close_reason = str(s)
        if close_reason == "wall_timeout":
            status = "failed"
    except Exception as e:  # noqa: BLE001
        status, close_reason, err = "failed", "exception", str(e)[:500]
        store.append_event(run_id, {"type": "error", "message": err})
    finally:
        with _reg_lock:
            _stop_flags.pop(run_id, None)
        store.set_terminal(run_id, status, close_reason=close_reason, error=err)
        store.append_event(run_id, {"type": "run_finished", "status": status,
                                    "close_reason": close_reason})
    return {"run_id": run_id, "status": status, "close_reason": close_reason}


def start_run(task, team=None, max_rounds=MAX_ROUNDS):
    """Create a run + launch the pipeline in a background thread. Returns meta.
    `max_rounds` is accepted for API compatibility; the v2 pipeline has fixed
    phases and caps debate width via OFFICE_MAX_DISAGREEMENTS instead."""
    team = team or roles_mod.random_team()
    run_id, meta = store.create_run(task, team)
    threading.Thread(
        target=orchestrate, args=(run_id, task, team, max_rounds),
        daemon=True, name=f"office_run_{run_id}",
    ).start()
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    args = ap.parse_args()
    team = roles_mod.random_team()
    run_id, _ = store.create_run(args.task, team)
    print(f"run_id={run_id} team=" + ",".join(f"{r.key}:{r.engine}" for r in team))
    result = orchestrate(run_id, args.task, team)
    print(json.dumps(result, ensure_ascii=False))
    print("deliverable:\n" + (store.load_deliverable(run_id) or "(none)"))
    return 0 if result["status"] == "done" else 1


if __name__ == "__main__":
    sys.exit(main())

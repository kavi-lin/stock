#!/usr/bin/env python3
"""Contract for the quota-broker gate in `scripts/_shared/model_router.py` (V4.106.0).

What this locks down is the failure policy, because that is where an integration
like this goes wrong quietly:

  * fail-closed by default — a decision-bearing role does not run when the broker
    cannot answer;
  * the news line may degrade to the local budget — but only when the broker
    could not answer;
  * **nothing** degrades when the broker answered "no capacity". That answer is
    about the 20% hard reserve, and falling back from it would spend exactly the
    quota the broker had just refused. It is the single most important assertion
    in this file.

Runs against a stub broker over real HTTP — the client is stdlib urllib, so the
transport is worth exercising — and never invokes a vendor CLI: `run_llm` is
replaced by a recorder.

Usage: python3 tests/test_broker_gate.py   (rc=0 = pass)
"""
from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Pin a token so the client never reaches for the developer's Keychain.
os.environ["LQB_API_TOKEN"] = "test-token-do-not-reuse"

from scripts._shared import broker_gate  # noqa: E402
from scripts._shared import model_router as mr  # noqa: E402
from scripts.break_news import debater  # noqa: E402
from scripts.break_news.llm_drivers import _DEFAULT_CONFIG, LLMResult, break_news_pair  # noqa: E402

#: The last-resort debate pair, read straight from the module default so this
#: file cannot pass against a config file that happens to disagree with it.
_LLM_DRIVERS_DEFAULT = [_DEFAULT_CONFIG["break_news"]["primary"],
                        _DEFAULT_CONFIG["break_news"]["secondary"]]

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        failures.append(f"{name}: {detail}")


# ───────────────────────────── stub broker ──────────────────────────────────
class StubBroker(BaseHTTPRequestHandler):
    """Answers the three calls the gate makes. Behaviour set on the server."""

    def log_message(self, *_args):     # silence
        return

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):                  # noqa: N802 - stdlib naming
        self._send(200, {"status": "healthy"})

    def do_POST(self):                 # noqa: N802 - stdlib naming
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        mode = self.server.mode

        if self.path == "/v1/recommend":
            self.server.requests.append(body)
            task_type = str((body.get("task") or {}).get("task_type") or "")
            if not broker_gate.TASK_TYPE_PATTERN.match(task_type):
                # The daemon's own field pattern, enforced here because V4.110.0
                # shipped `agentic_protocol:<name>` and this file passed. A stub
                # that accepts more than the real broker does cannot see a
                # fail-closed regression: every protocol run 400'd in production
                # while every assertion here stayed green.
                self._send(400, {"error": {
                    "code": "invalid_request",
                    "message": f"task_type {task_type!r} does not match "
                               r"'^[a-z0-9][a-z0-9_-]*$'",
                    "retryable": False,
                    "occurred_at": "2026-08-08T00:00:00+00:00", "context": {},
                }})
                return
            if mode == "rank":
                # A full evaluation: two eligible and ranked, one excluded.
                self._send(200, {
                    "decision_id": "d-1", "task_id": body["task"]["task_id"],
                    "generated_at": "2026-08-08T00:00:00+00:00",
                    "recommended": "agy", "fallback_used": False, "override_used": False,
                    "candidates": [
                        {"provider": "claude", "eligible": True, "rank": 2, "score": 0.6,
                         "exclusion_reasons": []},
                        {"provider": "codex", "eligible": False, "rank": None,
                         "exclusion_reasons": ["reserve_only"]},
                        {"provider": "agy", "eligible": True, "rank": 1, "score": 0.9,
                         "exclusion_reasons": []},
                    ],
                })
                return
            if mode == "refuse":
                self._send(200, {
                    "decision_id": "d-1", "task_id": body["task"]["task_id"],
                    "generated_at": "2026-08-08T00:00:00+00:00",
                    "recommended": None, "candidates": [],
                    "fallback_used": False, "override_used": False,
                    "error": {"code": "no_capacity", "message": "every provider is reserve-only",
                              "retryable": False, "occurred_at": "2026-08-08T00:00:00+00:00",
                              "context": {}},
                })
                return
            self._send(200, {
                "decision_id": "d-1", "task_id": body["task"]["task_id"],
                "generated_at": "2026-08-08T00:00:00+00:00",
                "recommended": self.server.grant_provider,
                "candidates": [], "fallback_used": False, "override_used": False,
                "reservation": {
                    "reservation_id": "r-1", "task_id": body["task"]["task_id"],
                    "provider": self.server.grant_provider, "state": "pending",
                    "created_at": "2026-08-08T00:00:00+00:00",
                    "expires_at": "2026-08-08T06:00:00+00:00",
                },
            })
            return

        self.server.settlements.append((self.path, body))
        self._send(200, {"reservation": {
            "reservation_id": "r-1", "task_id": "t", "provider": self.server.grant_provider,
            "state": "completed", "created_at": "2026-08-08T00:00:00+00:00",
            "expires_at": "2026-08-08T06:00:00+00:00",
        }})


def start_stub(mode: str = "grant", grant_provider: str = "agy"):
    server = HTTPServer(("127.0.0.1", 0), StubBroker)
    server.mode = mode
    server.grant_provider = grant_provider
    server.requests = []
    server.settlements = []
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
    thread.daemon = True
    thread.start()
    return server, thread


def config_for(server, **overrides) -> dict:
    """A full llm_config with the broker pointed at `server` (or nowhere)."""
    broker = {
        "enabled": True,
        "base_url": f"http://127.0.0.1:{server.server_address[1]}" if server else
                    "http://127.0.0.1:1",
        "timeout_sec": 5,
        "degradable_roles": ["debate", "brief", "link_digest"],
    }
    broker.update(overrides)
    return {
        "primary": "gemini", "secondary": "codex", "tertiary": "claude",
        "enabled": {"claude": True, "gemini": True, "codex": True, "grok": True},
        "budgets": {m: {"daily_max_calls": 500} for m in
                    ("claude", "gemini", "codex", "grok")},
        "cooldown_hours": 4,
        "break_news": {"primary": "claude", "secondary": "gemini"},
        "broker": broker,
    }


class Recorder:
    """Stands in for `run_llm`, so no vendor CLI is ever spawned."""

    def __init__(self, exit_code: int = 0, parsed=None) -> None:
        self.calls: list[tuple] = []
        self.exit_code = exit_code
        self.parsed = parsed if parsed is not None else {"ok": True}

    def __call__(self, model, system_prompt, user_prompt, timeout=0):
        self.calls.append((model, system_prompt, user_prompt))
        return LLMResult(
            agent=model, parsed=(self.parsed if self.exit_code == 0 else None),
            raw_text="", raw_stdout="", exit_code=self.exit_code, latency_ms=1,
            parse_status="ok" if self.exit_code == 0 else "failed",
            error=None if self.exit_code == 0 else "boom",
            input_tokens=1_200, output_tokens=340,
        )


class _Patched:
    """Swap module globals for one scenario and put them back afterwards."""

    def __init__(self, cfg: dict, recorder: Recorder) -> None:
        self.cfg = cfg
        self.recorder = recorder

    def __enter__(self):
        self._config = mr.load_llm_config
        self._run = mr.run_llm
        self._record = mr._record
        self._debater_config = debater.load_llm_config
        mr.load_llm_config = lambda: self.cfg
        mr.run_llm = self.recorder
        mr._record = lambda *a, **k: None    # never touch the real llm_usage.json
        # `debater` imported the loader by value, so patching `mr`'s is not
        # enough — and without this the ranking call would reach the developer's
        # live daemon instead of the stub.
        debater.load_llm_config = lambda: self.cfg
        return self

    def __exit__(self, *_exc):
        mr.load_llm_config = self._config
        mr.run_llm = self._run
        mr._record = self._record
        debater.load_llm_config = self._debater_config
        return False


# ─────────────────────────── pure helpers ───────────────────────────────────
check("map.gemini_is_agy", broker_gate.provider_for("gemini") == "agy",
      "the `gemini` runner has invoked the agy binary since llm_drivers was written")
check("map.claude", broker_gate.provider_for("claude") == "claude")
check("map.grok_ungoverned", broker_gate.provider_for("grok") is None,
      "grok is dormant in the broker; pretending otherwise would route into a void")

check("task_type.sanitised", mr._task_type("Report Polish!") == "report-polish-",
      mr._task_type("Report Polish!"))
check("task_type.empty", mr._task_type("") == "call")

# V4.111.4 — every task type this repo can build must satisfy the broker's own
# field pattern. It is checked here on the names rather than only through the
# stub because the cost of failing it is not a bad history row: `_acquire` reads
# a 400 as this repo's bug and fails closed, so one invalid character stops every
# protocol run while `lqb status` reports a healthy daemon.
check("task_type.protocol_is_schema_valid",
      broker_gate.TASK_TYPE_PATTERN.match(broker_gate.protocol_task_type("invest")) is not None,
      broker_gate.protocol_task_type("invest"))
check("task_type.protocol_no_colon",
      broker_gate.protocol_task_type("invest") == "agentic_protocol-invest",
      "V4.110.0 used a colon, which the broker's pattern rejects")
check("task_type.protocol_unnamed", broker_gate.protocol_task_type() == "agentic_protocol")
check("task_type.protocol_keeps_underscores",
      broker_gate.protocol_task_type("llm_review") == "agentic_protocol-llm_review",
      "underscores are legal; the separator is a hyphen so the boundary stays readable")
for _hostile in ("invest:v2", "產業掃描", "Sector Scan", "!!!"):
    _built = broker_gate.protocol_task_type(_hostile)
    check(f"task_type.hostile[{_hostile}]",
          broker_gate.TASK_TYPE_PATTERN.match(_built) is not None, _built)
check("task_type.role_is_schema_valid",
      all(broker_gate.TASK_TYPE_PATTERN.match(mr._task_type(r)) is not None
          for r in ("debate", "brief", "link_digest", "report_polish", "Report Polish!", "")),
      "the single-call path must satisfy the same pattern")

est_in, est_out = broker_gate.estimate_tokens("debate", "x" * 300, "y" * 300)
check("estimate.input_measured", est_in == 200, str(est_in))
check("estimate.output_prior", est_out == 3_000, str(est_out))

usage = broker_gate.usage_for_broker(
    {"input": 10, "output": 5, "cache_read": 2, "cost_usd": 0.5})
check("usage.mapped", usage["input_tokens"] == 10 and usage["cache_read_tokens"] == 2, str(usage))
check("usage.no_cost", "cost_usd" not in usage,
      "TokenUsage forbids extras; a stray key turns settlement into a 4xx")
check("usage.counts_a_call", usage.get("model_calls") == 1, str(usage))
check("usage.empty_stays_empty", broker_gate.usage_for_broker(None) == {})

# ───────────────────────── granted: reserve → run → settle ──────────────────
server, _thread = start_stub("grant", "agy")
try:
    recorder = Recorder()
    with _Patched(config_for(server), recorder):
        result = mr.run_role("intraday_eval", "SYS", "USR")

    check("grant.ran", len(recorder.calls) == 1, str(recorder.calls))
    check("grant.model", recorder.calls and recorder.calls[0][0] == "gemini",
          "agy is this repo's `gemini`")
    check("grant.ok", result.exit_code == 0)
    check("grant.note", "broker:agy" in (result.route_note or ""), result.route_note)

    reserved = server.requests[0]["task"]
    check("grant.project", reserved["project"] == "ai-investment-committee", str(reserved))
    check("grant.ttl", reserved["reservation_ttl_seconds"] == 1_800, str(reserved))
    check("grant.pinned", reserved["forbidden_providers"] == ["claude", "codex"],
          "a single-shot call is pinned to its role's model; the broker may not substitute")

    paths = [path for path, _body in server.settlements]
    check("grant.started", any(p.endswith("/start") for p in paths), str(paths))
    settled = [body for path, body in server.settlements if path.endswith("/complete")]
    check("grant.settled", len(settled) == 1, str(server.settlements))
    check("grant.real_tokens",
          settled and settled[0]["usage"]["input_tokens"] == 1_200, str(settled))
    check("grant.no_error_class", settled and "error_class" not in settled[0], str(settled))
finally:
    server.shutdown()

# ───────────────────────── refused: nobody may proceed ──────────────────────
server, _thread = start_stub("refuse")
try:
    for role in ("office", "debate"):          # decision-bearing AND news-line
        recorder = Recorder()
        with _Patched(config_for(server), recorder):
            result = mr.run_role(role, "SYS", "USR")
        check(f"refuse.{role}.did_not_run", recorder.calls == [],
              "the broker refused; running anyway spends the hard reserve it protected")
        check(f"refuse.{role}.failed", result.exit_code != 0)
        check(f"refuse.{role}.explains", "refused" in (result.route_note or ""),
              result.route_note)
finally:
    server.shutdown()

# ─────────────────── unreachable: fail-closed, except the news line ─────────
recorder = Recorder()
with _Patched(config_for(None), recorder):     # port 1 — nothing listening
    result = mr.run_role("office", "SYS", "USR")
check("down.office.did_not_run", recorder.calls == [],
      "a decision-bearing role must not run when the quota authority is unreachable")
check("down.office.explains", "unavailable" in (result.route_note or ""), result.route_note)

recorder = Recorder()
with _Patched(config_for(None), recorder):
    result = mr.run_with_fallback("gemini", "debate", "SYS", "USR")
check("down.debate.ran", len(recorder.calls) == 1,
      "the news line may fall back to the local budget when the broker is DOWN")
check("down.debate.ok", result.exit_code == 0)
check("down.debate.explains", "degraded" in (result.route_note or ""), result.route_note)

# The local budget is the only gate on the degraded path, so it must still bite.
recorder = Recorder()
exhausted = config_for(None)
exhausted["budgets"]["gemini"] = {"daily_max_calls": 1}
_real_load_usage = mr._load_usage
try:
    mr._load_usage = lambda cfg=None: {
        "date": "2026-08-08",
        "models": {m: {"calls": 99, "cooldown_until": None, "last_error": None,
                       "tokens": {}, "call_timestamps": []}
                   for m in ("claude", "gemini", "codex", "grok")},
    }
    with _Patched(exhausted, recorder):
        result = mr.run_with_fallback("gemini", "debate", "SYS", "USR")
finally:
    mr._load_usage = _real_load_usage
check("down.debate.local_budget_bites", recorder.calls == [],
      "degrading to the local budget must mean the local budget is enforced")
check("down.debate.local_budget_explains", "budget" in (result.route_note or ""),
      result.route_note)

# ─────────────────────────── protocol path ──────────────────────────────────
server, _thread = start_stub("refuse")
try:
    with _Patched(config_for(server), Recorder()):
        try:
            mr.acquire_protocol_lease()
            check("protocol.fail_closed", False, "a refused protocol run was authorised")
        except mr.ProtocolBlocked as blocked:
            check("protocol.fail_closed", True)
            check("protocol.explains", "hard reserve" in str(blocked), str(blocked))
finally:
    server.shutdown()

server, _thread = start_stub("grant", "codex")
try:
    with _Patched(config_for(server), Recorder()):
        model, lease, note = mr.acquire_protocol_lease()
    check("protocol.model", model == "codex", model)
    check("protocol.lease", lease is not None)
    reserved = server.requests[0]["task"]
    check("protocol.type", reserved["task_type"] == "agentic_protocol", str(reserved))
    check("protocol.ttl", reserved["reservation_ttl_seconds"] == 21_600,
          "a protocol run outliving its TTL cannot be settled at all")
    check("protocol.whole_chain_offered", reserved["preferred_providers"] == ["agy", "codex", "claude"],
          "any chain member is acceptable for a protocol run; the broker picks on quota")
    check("protocol.estimate_is_not_zero",
          reserved["estimated_input_tokens"] >= 100_000, str(reserved))
finally:
    server.shutdown()

# V4.110.0 — a named protocol reserves against its own measured prior and files
# its tokens under its own task type. One shared `agentic_protocol` row averaged
# a 143-second triage pass together with a forty-minute five-lane debate, so no
# protocol could calibrate from it and the prior stayed a guess for all of them.
per_protocol = {"protocol_tokens": {
    "default": {"input": 200_000, "output": 40_000},
    "triage": {"input": 240_000, "output": 32_000},
}}
server, _thread = start_stub("grant", "codex")
try:
    with _Patched(config_for(server, **per_protocol), Recorder()):
        mr.acquire_protocol_lease("agentic_protocol", "triage")
    reserved = server.requests[0]["task"]
    check("protocol.named_type", reserved["task_type"] == "agentic_protocol-triage", str(reserved))
    check("protocol.named_estimate", reserved["estimated_input_tokens"] == 240_000, str(reserved))
    check("protocol.named_output", reserved["estimated_output_tokens"] == 32_000, str(reserved))
finally:
    server.shutdown()

# An unmeasured protocol falls back to `default`, never to zero — the one we have
# no numbers for is the one most likely to surprise us.
server, _thread = start_stub("grant", "codex")
try:
    with _Patched(config_for(server, **per_protocol), Recorder()):
        mr.acquire_protocol_lease("agentic_protocol", "invest")
    reserved = server.requests[0]["task"]
    check("protocol.unmeasured_type", reserved["task_type"] == "agentic_protocol-invest", str(reserved))
    check("protocol.unmeasured_estimate",
          reserved["estimated_input_tokens"] == 200_000, str(reserved))
finally:
    server.shutdown()

# The pre-V4.110.0 flat shape keeps its old meaning rather than being dropped in
# favour of the constants — a config file is not upgraded when the code is.
flat = broker_gate.broker_config({"broker": {"protocol_tokens": {"input": 111, "output": 22}}})
check("protocol.flat_shape_still_read", flat["protocol_tokens"] == {"default": (111, 22)},
      str(flat["protocol_tokens"]))

# ─────────────────── governed_call, for callers that run their own CLI ──────
server, _thread = start_stub("grant", "claude")
try:
    with _Patched(config_for(server), Recorder()):
        with mr.governed_call("office", "claude", "SYS", "USR") as hold:
            hold.settle(LLMResult(agent="claude", parsed={"ok": 1}, raw_text="",
                                  raw_stdout="", exit_code=0, latency_ms=1,
                                  parse_status="ok", error=None,
                                  input_tokens=7, output_tokens=3))
    settled = [b for p, b in server.settlements if p.endswith("/complete")]
    check("governed.settled", len(settled) == 1, str(server.settlements))
    check("governed.tokens", settled and settled[0]["usage"]["output_tokens"] == 3, str(settled))
finally:
    server.shutdown()

server, _thread = start_stub("grant", "claude")
try:
    with _Patched(config_for(server), Recorder()):
        try:
            with mr.governed_call("office", "claude", "SYS", "USR"):
                raise RuntimeError("the CLI blew up")
        except RuntimeError:
            pass
    cancelled = [p for p, _b in server.settlements if p.endswith("/cancel")]
    check("governed.hold_released", len(cancelled) == 1,
          "an unsettled hold makes every other project see less headroom than exists")
finally:
    server.shutdown()

# ───────── the broker assigns the debate pair (V4.109.0) ────────────────────
server, _thread = start_stub("rank")
try:
    with _Patched(config_for(server), Recorder()):
        stub_cfg = config_for(server)
        ranked = broker_gate.ranked_models("debate", cfg=stub_cfg)
        top_two = broker_gate.ranked_models("debate", count=2, cfg=stub_cfg)
        order = debater._turn_order()

    check("rank.order", ranked == ["gemini", "claude"],
          f"{ranked} — rank 1 first, and agy is this repo's `gemini`")
    check("rank.excluded_dropped", "codex" not in ranked,
          "a provider the broker excluded must not be handed a debate turn")
    check("rank.count", top_two == ["gemini", "claude"], str(top_two))
    check("debate.pair_from_broker", order == ["gemini", "claude"], str(order))

    preview = server.requests[0]["task"]
    check("rank.is_preview", server.requests and "reservation" not in preview,
          "the ranking must hold no quota — it is asked before the work exists")
    check("rank.estimate_is_realistic", preview["estimated_input_tokens"] >= 10_000,
          "asking with ~0 tokens would make a provider that cannot cover a turn look eligible")
finally:
    server.shutdown()

# Fewer than two able to serve → keep the configured pair rather than silently
# turning every debate into a monologue.
# `break_news_pair()` reads the real config file (it calls llm_drivers' own
# loader, not the patched one), so assert against it rather than a literal —
# otherwise this passes or fails on what happens to be in config/ today.
configured_pair = break_news_pair()

server, _thread = start_stub("refuse")
try:
    with _Patched(config_for(server), Recorder()):
        check("debate.refused_falls_back_to_pair",
              debater._turn_order() == configured_pair,
              "a debate needs two voices; the per-call gate refuses what it must")
finally:
    server.shutdown()

with _Patched(config_for(None), Recorder()):    # broker unreachable
    check("debate.unreachable_falls_back_to_pair",
          debater._turn_order() == configured_pair, "config pair is the fallback")

check("debate.fallback_pair_matches_agents_md",
      set(broker_gate.MODEL_FOR_PROVIDER.values()) >= {"claude", "gemini"}
      and _LLM_DRIVERS_DEFAULT == ["claude", "gemini"],
      f"{_LLM_DRIVERS_DEFAULT} — AGENTS.md calls Claude×Gemini divergence an intended signal")

if failures:
    print("✗ broker gate contract violated:")
    for failure in failures:
        print(f"  - {failure}")
    sys.exit(1)
print("✓ broker gate contract holds")

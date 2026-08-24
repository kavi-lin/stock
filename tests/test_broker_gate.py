#!/usr/bin/env python3
"""Contract for the quota-broker gate in `scripts/_shared/model_router.py` (V4.106.0).

What this locks down is the failure policy, because that is where an integration
like this goes wrong quietly:

  * every role is fail-closed when the broker cannot answer;
  * normal calls offer the complete certified set and let the broker choose;
  * pinned ensemble/certification calls still require a broker lease.

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
        self._send(200, {
            "status": "healthy",
            "broker_version": getattr(self.server, "broker_version", "0.3.0"),
        })

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
                # V4.129.0 — the winning candidate carries the model the broker
                # chose. Only agy ever gets one (two quota pools, and the model
                # is what decides which is spent), so the stub mirrors that.
                "candidates": [{
                    "provider": self.server.grant_provider, "eligible": True, "rank": 1,
                    "exclusion_reasons": [],
                    "model": getattr(self.server, "grant_model", None),
                }],
                "fallback_used": False, "override_used": False,
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


def start_stub(mode: str = "grant", grant_provider: str = "agy",
               grant_model: str | None = None, broker_version: str = "0.3.0"):
    server = HTTPServer(("127.0.0.1", 0), StubBroker)
    server.mode = mode
    server.grant_provider = grant_provider
    server.grant_model = grant_model
    server.broker_version = broker_version
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
        #: `provider_model` per call — the vendor-native model the broker
        #: assigned. Recorded separately from `calls` so the existing
        #: assertions on that tuple keep their shape.
        self.provider_models: list[str] = []
        self.exit_code = exit_code
        self.parsed = parsed if parsed is not None else {"ok": True}

    def __call__(self, model, system_prompt, user_prompt, timeout=0, provider_model="",
                 process_callback=None):
        self.calls.append((model, system_prompt, user_prompt))
        self.provider_models.append(provider_model)
        if process_callback is not None:
            process_callback(os.getpid(), os.getpgid(0))
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
check(
    "usage.preserves_explicit_model_calls",
    broker_gate.usage_for_broker({"input_tokens": 10, "model_calls": 3}).get("model_calls") == 3,
)
check("usage.empty_stays_empty", broker_gate.usage_for_broker(None) == {})

# ───────────────────────── granted: reserve → run → settle ──────────────────
server, _thread = start_stub("grant", "agy", grant_model="gemini-3.6-flash-medium")
try:
    recorder = Recorder()
    with _Patched(config_for(server), recorder):
        result = mr.run_role("intraday_eval", "SYS", "USR")

    check("grant.ran", len(recorder.calls) == 1, str(recorder.calls))
    check("grant.model", recorder.calls and recorder.calls[0][0] == "gemini",
          "agy is this repo's `gemini`")
    check("grant.ok", result.exit_code == 0)
    check("grant.note", "broker:agy" in (result.route_note or ""), result.route_note)
    # V4.129.0 — the whole point of the assignment is that it reaches the CLI.
    # agy's two pools refill independently and the hold is against ONE of them,
    # so a run that ignores this spends a pool nothing is holding. This walks
    # the real path: stub response → `Lease.model` → `_run_model_for_role`.
    check("grant.assigned_model_reaches_the_driver",
          recorder.provider_models == ["gemini-3.6-flash-medium"],
          str(recorder.provider_models))
    started = [body for path, body in server.settlements if path.endswith("/start")]
    check("grant.start_records_the_real_model",
          started and started[0].get("model") == "gemini-3.6-flash-medium",
          f"{started} — the ledger calibrates each pool from what it records; "
          "the `gemini` alias is not a pool")
    heartbeats = [body for path, body in server.settlements if path.endswith("/heartbeat")]
    check("grant.heartbeat_records_process_identity",
          heartbeats and heartbeats[0].get("process_pid") == os.getpid()
          and heartbeats[0].get("process_pgid") == os.getpgid(0),
          repr(heartbeats))

    reserved = server.requests[0]["task"]
    check("grant.project", reserved["project"] == "ai-investment-committee", str(reserved))
    check("grant.ttl", reserved["reservation_ttl_seconds"] == 1_800, str(reserved))
    check("grant.broker_selects",
          set(reserved.get("preferred_providers") or []) == {"claude", "agy", "codex"}
          and not (reserved.get("forbidden_providers") or []),
          "normal calls offer every certified provider to the broker")

    paths = [path for path, _body in server.settlements]
    check("grant.started", any(p.endswith("/start") for p in paths), str(paths))
    settled = [body for path, body in server.settlements if path.endswith("/complete")]
    check("grant.settled", len(settled) == 1, str(server.settlements))
    check("grant.real_tokens",
          settled and settled[0]["usage"]["input_tokens"] == 1_200, str(settled))
    check("grant.no_error_class", settled and "error_class" not in settled[0], str(settled))
finally:
    server.shutdown()

# Text-output tasks settle successfully without pretending Markdown is JSON.
class RawRecorder(Recorder):
    def __call__(self, model, system_prompt, user_prompt, timeout=0, provider_model="",
                 process_callback=None):
        self.calls.append((model, system_prompt, user_prompt))
        return LLMResult(
            agent=model, parsed=None, raw_text="## Verdict\nApproved", raw_stdout="",
            exit_code=0, latency_ms=1, parse_status="raw", error=None,
            input_tokens=100, output_tokens=20,
        )


server, _thread = start_stub("grant", "codex")
try:
    recorder = RawRecorder()
    with _Patched(config_for(server), recorder):
        result = mr.run_role("office_verdict", "SYS", "USR")
    check("text_task.route_ok", ":ok(" in (result.route_note or ""), result.route_note)
    settled = [body for path, body in server.settlements if path.endswith("/complete")]
    check("text_task.no_invalid_output",
          settled and "error_class" not in settled[-1], repr(settled))
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

# ───────────────────── unreachable: every role is fail-closed ───────────────
recorder = Recorder()
with _Patched(config_for(None), recorder):     # port 1 — nothing listening
    result = mr.run_role("office", "SYS", "USR")
check("down.office.did_not_run", recorder.calls == [],
      "a decision-bearing role must not run when the quota authority is unreachable")
check("down.office.explains", "unavailable" in (result.route_note or ""), result.route_note)

recorder = Recorder()
with _Patched(config_for(None), recorder):
    result = mr.run_with_fallback("gemini", "debate", "SYS", "USR")
check("down.debate.did_not_run", recorder.calls == [],
      "daemon/news work must defer rather than spend from a local fallback")
check("down.debate.failed", result.exit_code != 0)
check("down.debate.explains", "unavailable" in (result.route_note or ""), result.route_note)

# Local counters are telemetry and can never authorise inference.
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
check("down.debate.local_budget_cannot_authorise", recorder.calls == [],
      "an available local budget must not bypass an unavailable broker")
check("down.debate.local_budget_explains", "unavailable" in (result.route_note or ""),
      result.route_note)

# A reachable but stale daemon is not an outage. Even the news line must stop:
# degrading here would let an old routing policy keep spending after deployment.
server, _thread = start_stub("grant", broker_version="0.1.0")
try:
    status = mr.broker_status(config_for(server))
    check("version_mismatch.status.reachable", status.get("reachable") is True, repr(status))
    check("version_mismatch.status.not_authority", status.get("authority") is False, repr(status))
    check("version_mismatch.status.restart", status.get("restart_required") is True, repr(status))
    check("version_mismatch.status.versions",
          status.get("broker_version") == "0.1.0" and status.get("client_version") == "0.3.0",
          repr(status))
    recorder = Recorder()
    with _Patched(config_for(server), recorder):
        result = mr.run_with_fallback("gemini", "debate", "SYS", "USR")
    check("version_mismatch.debate.did_not_run", recorder.calls == [],
          "version mismatch must never take the outage fallback")
    check("version_mismatch.debate.explains", "version" in (result.route_note or ""),
          result.route_note)
    check("version_mismatch.no_reservation", server.requests == [],
          "handshake must block before POST /v1/recommend")
finally:
    server.shutdown()

# ─────────────────────────── protocol path ──────────────────────────────────
server, _thread = start_stub("refuse")
try:
    with _Patched(config_for(server), Recorder()):
        try:
            mr.acquire_protocol_lease("agentic_protocol", "invest")
            check("protocol.fail_closed", False, "a refused protocol run was authorised")
        except mr.ProtocolBlocked as blocked:
            check("protocol.fail_closed", True)
            check("protocol.explains", "hard reserve" in str(blocked), str(blocked))
finally:
    server.shutdown()

server, _thread = start_stub("grant", "codex")
try:
    with _Patched(config_for(server), Recorder()):
        model, lease, note = mr.acquire_protocol_lease("agentic_protocol", "invest")
    check("protocol.model", model == "codex", model)
    check("protocol.lease", lease is not None)
    reserved = server.requests[0]["task"]
    check("protocol.type", reserved["task_type"] == "agentic_protocol-invest", str(reserved))
    check("protocol.ttl", reserved["reservation_ttl_seconds"] == 21_600,
          "a protocol run outliving its TTL cannot be settled at all")
    check("protocol.certified_set_offered",
          set(reserved["preferred_providers"]) == {"agy", "codex", "claude"},
          "every certified provider is acceptable; the broker picks on quota")
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

# Fewer than two able to serve → defer the daemon cycle. A configured pair may
# describe the intended voices but cannot authorise an inference.

server, _thread = start_stub("refuse")
try:
    with _Patched(config_for(server), Recorder()):
        check("debate.refused_defers", debater._turn_order() == [],
              "hard-reserve refusal must not fall back to a configured pair")
finally:
    server.shutdown()

with _Patched(config_for(None), Recorder()):    # broker unreachable
    check("debate.unreachable_defers", debater._turn_order() == [],
          "broker outage must defer rather than use a local pair")

check("debate.fallback_pair_matches_agents_md",
      set(broker_gate.MODEL_FOR_PROVIDER.values()) >= {"claude", "gemini"}
      and _LLM_DRIVERS_DEFAULT == ["claude", "gemini"],
      f"{_LLM_DRIVERS_DEFAULT} — AGENTS.md calls Claude×Gemini divergence an intended signal")


# ─────────────────── V4.115.0 — window fields reach the UI ───────────────────
# The bucket mapping is a hand-written whitelist, so a field it was not taught
# about is dropped in silence and the panel just renders something slightly
# wrong. `used_percent` is the case that matters: the quota bars draw
# consumption, and without it every provider falls back to 100 − remaining.
# That inference is right for claude and WRONG for agy, which reports remaining
# with `used_percent: null` — the broker does not claim to know what was spent
# there, and inverting the one figure it gives invents a reading.
_BUCKET_FIELDS = {"name", "remaining_percent", "used_percent", "label",
                  "resets_at", "reset_label", "refresh_in_seconds",
                  "window_minutes", "reserve_only"}

_STATUS_FIXTURE = {
    "hard_reserve_percent": 20.0,
    "active_reservations": [{
        "task": {"project": "ai-investment-committee",
                 "task_id": "brief-live", "task_type": "brief"},
        "reservation": {"reservation_id": "live-1", "provider": "agy",
                        "state": "active", "created_at": "2026-08-21T08:00:00Z"},
    }, {
        "project": "tw-stock-wonwon", "task_id": "screen-live",
        "task_type": "screen", "reservation_id": "live-2",
        "provider": "codex", "state": "active",
        "created_at": "2026-08-21T08:01:00Z",
    }, {
        # Missing ownership must never be guessed local/green.
        "task_id": "unknown-live", "task_type": "unknown",
        "reservation_id": "live-3", "provider": "claude", "state": "active",
        "created_at": "2026-08-21T08:02:00Z",
    }],
    "providers": [
        {"info": {"id": "claude"}, "authenticated": True,
         "snapshot": {"plan": None, "buckets": {
             "weekly.all_models": {"remaining_percent": 36.0, "used_percent": 64.0,
                                   "label": "allmodels",
                                   "reset_label": "Aug13at12pm(Asia/Taipei)"},
             "session": {"remaining_percent": 94.0, "used_percent": 6.0,
                         "label": "session", "reset_label": "9:40am(Asia/Taipei)"},
         }}},
        # agy's shape: what is left is known, what was spent is not. Two pools
        # that refill independently, so the broker sends the headline it will
        # actually route on plus the pool it came from — here the exhausted
        # claude_gpt windows must NOT set the number.
        {"info": {"id": "agy"}, "authenticated": True,
         "remaining_percent": 73.4, "routable_pool": "gemini",
         "snapshot": {"plan": "Google AI Pro", "buckets": {
             "gemini.weekly": {"remaining_percent": 73.4, "used_percent": None,
                               "refresh_in_seconds": 301680},
             "claude_gpt.five_hour": {"remaining_percent": 0.0, "used_percent": None,
                                      "reserve_only": True},
         }}},
        {"info": {"id": "codex"}, "authenticated": True,
         "plan_label": "ChatGPT Pro 5x", "current_model": "gpt-5.6-sol",
         "snapshot": {"plan": "prolite", "buckets": {
             "primary": {"remaining_percent": 97.0, "used_percent": 3.0,
                         "window_minutes": 10080, "label": "Weekly limit"},
         }}},
    ],
}


class _StatusOnlyClient:
    """Enough client to drive `quota_snapshot`, which only calls `status()`."""

    def __init__(self, payload):
        self._payload = payload

    def status(self):
        return self._payload


_old_broker_client = broker_gate.broker_client
try:
    broker_gate.broker_client = lambda cfg=None: _StatusOnlyClient(_STATUS_FIXTURE)
    _snap = broker_gate.quota_snapshot({})
finally:
    broker_gate.broker_client = _old_broker_client

_provs = _snap.get("providers") or {}
check("buckets.provider_ids_mapped", set(_provs) == {"claude", "gemini", "codex"},
      f"{sorted(_provs)} — agy must surface under this repo's name")
check("active_reservations.provider_mapped",
      (_snap.get("active_reservations") or [{}])[0].get("model") == "gemini",
      repr(_snap.get("active_reservations")))
_active_by_id = {row.get("reservation_id"): row
                 for row in (_snap.get("active_reservations") or [])}
check("active_reservations.local_project_green",
      _active_by_id.get("live-1", {}).get("is_local_project") is True,
      repr(_active_by_id))
check("active_reservations.external_project_blue",
      _active_by_id.get("live-2", {}).get("project") == "tw-stock-wonwon"
      and _active_by_id.get("live-2", {}).get("is_local_project") is False,
      repr(_active_by_id))
check("active_reservations.unknown_project_blue",
      _active_by_id.get("live-3", {}).get("project") is None
      and _active_by_id.get("live-3", {}).get("is_local_project") is False,
      repr(_active_by_id))

_claude = {b["name"]: b for b in (_provs.get("claude") or {}).get("buckets", [])}
_gem = {b["name"]: b for b in (_provs.get("gemini") or {}).get("buckets", [])}

for _name, _b in {**_claude, **_gem}.items():
    _missing = _BUCKET_FIELDS - set(_b)
    check(f"buckets.fields.{_name}", not _missing, f"dropped: {sorted(_missing)}")

check("buckets.used_percent_verbatim",
      _claude.get("weekly.all_models", {}).get("used_percent") == 64.0,
      "the provider's own reading must survive the mapping")
check("buckets.used_percent_null_preserved",
      "used_percent" in _gem.get("gemini.weekly", {})
      and _gem["gemini.weekly"]["used_percent"] is None,
      "null must stay null — the UI marks a derived figure and cannot if this is filled in here")
check("buckets.label_carried",
      _claude.get("weekly.all_models", {}).get("label") == "allmodels",
      "the provider's own window name beats the namespaced key the UI reverse-engineers")
check("buckets.plan_carried",
      (_provs.get("gemini") or {}).get("plan") == "Google AI Pro",
      "raw plan must survive for diagnostics")
check("provider.plan_label_carried",
      (_provs.get("codex") or {}).get("plan_label") == "ChatGPT Pro 5x",
      "the panel must not expose the provider's internal prolite slug")
check("provider.current_model_carried",
      (_provs.get("codex") or {}).get("current_model") == "gpt-5.6-sol",
      "the active model is part of the provider identity shown in the panel")
# V4.130.0 — was `== 36.0`, the tightest window. The panel now reads the
# five-hour one, which claude calls `session`; the weekly pools stay in the
# hover card. The number a run is dispatched on is still the broker's minimum —
# that is `reserve_only` / `cooldown_until`, both passed through untouched.
check("buckets.remaining_is_five_hour_window",
      (_provs.get("claude") or {}).get("remaining_percent") == 94.0
      and (_provs.get("claude") or {}).get("headline_bucket") == "session",
      f"got {(_provs.get('claude') or {}).get('remaining_percent')} from "
      f"{(_provs.get('claude') or {}).get('headline_bucket')} — expected the session window")
# The codex entry carries no `remaining_percent` and no five-hour window, so it
# pins the fallback chain end to end: a broker too old to send the field still
# gets the local minimum rather than a blank panel.
check("buckets.legacy_broker_falls_back_to_local_min",
      (_provs.get("codex") or {}).get("remaining_percent") == 97.0
      and (_provs.get("codex") or {}).get("headline_bucket") is None,
      "no headline field and no five-hour window → local minimum, and say it is not five-hour")
check("buckets.headline_from_broker",
      (_provs.get("gemini") or {}).get("remaining_percent") == 73.4,
      "the broker's own headline wins — 0% from a pool it will not route to is "
      "not this provider's number")
check("buckets.routable_pool_carried",
      (_provs.get("gemini") or {}).get("routable_pool") == "gemini",
      "the panel has to be able to say which pool the figure came from")
check("buckets.routable_pool_none_for_single_pool",
      (_provs.get("claude") or {}).get("routable_pool") is None,
      "one pool means the figure is the provider as a whole")

# V4.130.0 — the panel reads the FIVE-HOUR window for every provider. The
# broker's headline is the tightest window it can see, so the bars used to change
# meaning between providers and between days: on 2026-08-14 claude drew 45% from
# `weekly.fable` — one model's weekly pool — while the five-hour window it was
# actually spending sat at 8%. The two assertions above are the untouched half:
# that fixture has no five-hour window, so the broker's figure stands.
def _snapshot_with(payload, model="claude"):
    saved = broker_gate.broker_client
    try:
        broker_gate.broker_client = lambda cfg=None: _StatusOnlyClient(payload)
        return (broker_gate.quota_snapshot({}).get("providers") or {}).get(model) or {}
    finally:
        broker_gate.broker_client = saved


def _claude_fixture(session_remaining: float) -> dict:
    """claude's real shape: two weekly pools, and a five-hour one called
    `session` — the name is the only thing marking it as the short window."""
    return {"hard_reserve_percent": 20.0, "providers": [
        {"info": {"id": "claude"}, "authenticated": True, "remaining_percent": 55.0,
         "snapshot": {"plan": None, "buckets": {
             "weekly.fable": {"remaining_percent": 55.0, "used_percent": 45.0,
                              "label": "Fable"},
             "weekly.all_models": {"remaining_percent": 73.0, "used_percent": 27.0,
                                   "label": "allmodels"},
             "session": {"remaining_percent": session_remaining,
                         "used_percent": 100 - session_remaining, "label": "session"},
         }}},
    ]}


_five_hour = _snapshot_with(_claude_fixture(92.0))
check("buckets.headline_is_five_hour_window",
      _five_hour.get("remaining_percent") == 92.0,
      f"got {_five_hour.get('remaining_percent')} — the bar reads the five-hour "
      "window, not whichever pool happens to be tightest")
check("buckets.headline_bucket_named",
      _five_hour.get("headline_bucket") == "session",
      "the panel has to be able to say which window the number came from")
check("buckets.routable_pool_untouched_by_headline",
      _five_hour.get("headline_bucket") is not None
      and _five_hour.get("routable_pool") is None,
      "routable_pool stays the broker's routing fact — the window the panel reads "
      "is a separate question and has its own field")
check("buckets.other_windows_still_listed",
      {"weekly.fable", "weekly.all_models"} <= {b["name"] for b in _five_hour.get("buckets", [])},
      "the weekly windows belong in the hover card — passed over for the headline, not dropped")

# The five-hour window wins even when a weekly pool is far tighter: this is a
# fixed window, not a minimum. Without this the rule degenerates back to "worst".
_tight_weekly = _snapshot_with(_claude_fixture(96.0))
check("buckets.five_hour_wins_over_tighter_weekly",
      _tight_weekly.get("remaining_percent") == 96.0,
      f"got {_tight_weekly.get('remaining_percent')} — weekly.fable at 55 must not "
      "take the headline back")

# agy meters two independent pools, each with its own five-hour window. The one
# the broker will not route to must not set the number.
_agy = _snapshot_with({"hard_reserve_percent": 20.0, "providers": [
    {"info": {"id": "agy"}, "authenticated": True,
     "remaining_percent": 12.0, "routable_pool": "gemini",
     "snapshot": {"plan": None, "buckets": {
         "gemini.five_hour": {"remaining_percent": 88.0, "used_percent": None},
         "gemini.weekly": {"remaining_percent": 70.0, "used_percent": None},
         "claude_gpt.five_hour": {"remaining_percent": 12.0, "used_percent": None},
     }}},
]}, model="gemini")
check("buckets.five_hour_respects_routable_pool",
      _agy.get("remaining_percent") == 88.0 and _agy.get("headline_bucket") == "gemini.five_hour",
      f"got {_agy.get('remaining_percent')} from {_agy.get('headline_bucket')} — the "
      "five-hour window of a pool the broker will not route to is not this provider's number")

# codex reports one weekly bucket and no five-hour window. Inventing one is the
# failure mode this guards: the panel must keep the broker's figure and say so.
_codex = _snapshot_with({"hard_reserve_percent": 20.0, "providers": [
    {"info": {"id": "codex"}, "authenticated": True, "remaining_percent": 81.0,
     "snapshot": {"plan": None, "buckets": {
         "primary": {"remaining_percent": 81.0, "used_percent": 19.0,
                     "window_minutes": 10080, "label": "Weekly limit"},
     }}},
]}, model="codex")
check("buckets.no_five_hour_keeps_broker_headline",
      _codex.get("remaining_percent") == 81.0 and _codex.get("headline_bucket") is None,
      f"got {_codex.get('remaining_percent')} / {_codex.get('headline_bucket')} — a weekly "
      "window must not be relabelled as five-hour; null headline_bucket is how the UI says so")

# --- the panel's reading of what the gate passes through ---------------------
#
# `cooldown_until` is transported verbatim on purpose (see above), so whether an
# expired deadline benches a provider is decided in the JS. It is asserted here
# because this is the file that documents the pass-through, and the two halves
# only make sense together.
#
# V4.130.2: the broker's `providers` row keeps the last deadline after it lapses.
# `if (info.cooldown_until)` therefore drew claude as 冷卻中 for six hours past
# its own reset, through four runs the router had already dispatched to it.
_utils_source = (ROOT / "Dashboard" / "utils.js").read_text(encoding="utf-8")
check("ui.cooldown_checked_against_now",
      "Date.parse(info.cooldown_until" in _utils_source
      and "Date.now()" in _utils_source,
      "an expired cooldown must not flag a provider as cooling — compare the "
      "deadline with now, never test the string for truthiness")
check("ui.cooldown_not_bare_truthy",
      "if (info.cooldown_until)" not in _utils_source,
      "a bare truthiness test on the ISO string is the V4.130.2 regression")

if failures:
    print("✗ broker gate contract violated:")
    for failure in failures:
        print(f"  - {failure}")
    sys.exit(1)
print("✓ broker gate contract holds")

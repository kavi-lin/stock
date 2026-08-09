#!/usr/bin/env python3
"""Regression contract for Dashboard agentic protocol model routing."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.argv = ["dashboard_server.py"]

import dashboard_server as ds  # noqa: E402
from scripts.break_news.llm_drivers import parse_stream_log_usage  # noqa: E402


failures = []


def check(name, condition, detail=""):
    if not condition:
        failures.append(f"{name}: {detail}")


# Primary selection delegates to the shared governor instead of pinning Claude,
# and (V4.106.0) comes back with the broker reservation that covers the run.
old_acquire = ds._mrouter.acquire_protocol_lease
sentinel_lease = object()
seen = {}
try:
    def _fake(role="", protocol=None):
        seen["role"], seen["protocol"] = role, protocol
        return "codex", sentinel_lease, "broker:codex"

    ds._mrouter.acquire_protocol_lease = _fake
    selected, lease = ds._select_protocol_model("triage")
    check("selection.primary", selected == "codex")
    check("selection.lease", lease is sentinel_lease,
          "the reservation must reach the caller, or note_run cannot settle it")
    # V4.110.0 — the protocol's own name sizes the reservation and keys the
    # ledger. Dropping it here is silent: the run still starts, but against the
    # `default` prior, and its tokens land in a pooled row that no protocol can
    # calibrate from.
    check("selection.protocol_name", seen.get("protocol") == "triage", repr(seen))
finally:
    ds._mrouter.acquire_protocol_lease = old_acquire

# A run the broker declines must NOT fall through to a default provider: that is
# how the largest consumer in this repo used to escape governance entirely.
def _blocked(role="", protocol=None):
    raise ds._mrouter.ProtocolBlocked("no capacity")


try:
    ds._mrouter.acquire_protocol_lease = _blocked
    try:
        ds._select_protocol_model()
        check("selection.fail_closed", False, "a blocked run was allowed to start")
    except ds._mrouter.ProtocolBlocked:
        check("selection.fail_closed", True)
finally:
    ds._mrouter.acquire_protocol_lease = old_acquire

# Codex gets a writable agentic command rooted at this repo, with options before
# the prompt so prompts beginning with '-' cannot be parsed as CLI flags.
cmd = ds._protocol_command("codex", "RUN PROTOCOL")
check("codex.binary", cmd[:2] == [ds.CODEX_BIN, "exec"], repr(cmd))
check("codex.json", "--json" in cmd, repr(cmd))
check("codex.cwd", cmd[cmd.index("-C") + 1] == ds.ROOT, repr(cmd))
check("codex.permissions", "--dangerously-bypass-approvals-and-sandbox" in cmd, repr(cmd))
check("codex.prompt_last", cmd[-1] == "RUN PROTOCOL", repr(cmd))

# V4.114.1 — `agy --print-timeout` defaults to 5m, so a protocol budget larger
# than that was fiction: PROTOCOL_TIMEOUT_OVERRIDES only bounded the parent's
# proc.wait() while agy quit on its own at 5m00s. That is what ended
# invest_20260809_000447 at 308s wall. The child deadline must be passed and
# must sit UNDER the parent's, so the child times out first and still emits a
# final result event instead of being hard-killed mid-stream.
gcmd = ds._protocol_command("gemini", "RUN", timeout_sec=3600)
check("gemini.print_timeout_present", "--print-timeout" in gcmd, repr(gcmd))
_gt = gcmd[gcmd.index("--print-timeout") + 1]
check("gemini.print_timeout_unit", _gt.endswith("s"), _gt)
check("gemini.print_timeout_under_parent", int(_gt[:-1]) < 3600, _gt)
check("gemini.print_timeout_beats_default", int(_gt[:-1]) > 300,
      f"{_gt} — a value at or under agy's own 5m default changes nothing")
# A short protocol must not end up with a nonsensical or negative deadline.
_short = ds._protocol_command("gemini", "RUN", timeout_sec=10)
check("gemini.print_timeout_floor",
      int(_short[_short.index("--print-timeout") + 1][:-1]) >= 60, repr(_short))
# Every protocol's configured budget must actually reach the child.
for _p in ds.PROTOCOL_PROMPTS:
    _budget = ds.PROTOCOL_TIMEOUT_OVERRIDES.get(_p, ds.PROTOCOL_TIMEOUT_SEC)
    _c = ds._protocol_command("gemini", "RUN", timeout_sec=_budget)
    _v = int(_c[_c.index("--print-timeout") + 1][:-1])
    check(f"gemini.budget_reaches_child.{_p}", _v >= min(_budget, 60) - 30,
          f"budget={_budget} child={_v}")

# V4.114.0 — per-protocol provider allowlist. The broker treats providers as
# interchangeable for protocol runs (that is its documented job), and on
# 2026-08-09 it sent `分析 NOW` to agy — the first non-Claude invest run ever,
# which produced nothing. `preferred_providers` alone cannot express this: it
# only scores. The allowlist has to reach `forbidden_providers` or it does not
# bind at all, so that is what these cases pin.
_mr = ds._mrouter
_captured = {}


class _FakeLease:
    provider = "claude"

    def start(self, **_kw):
        pass

    def cancel(self, *_a, **_kw):
        pass


class _FakeClient:
    def acquire(self, **kw):
        _captured.clear()
        _captured.update(kw)
        return _FakeLease()


_old_client = _mr.broker_gate.broker_client
try:
    _mr.broker_gate.broker_client = lambda cfg: _FakeClient()
    _cfg = dict(_mr.load_llm_config())
    _cfg["protocol_providers"] = {"invest": ["claude", "codex"], "_default": None}

    _mr._acquire("agentic_protocol", "claude", _cfg, protocol=True, protocol_name="invest")
    check("allowlist.preferred", set(_captured.get("preferred_providers") or []) == {"claude", "codex"},
          repr(_captured.get("preferred_providers")))
    check("allowlist.forbidden_binds", "agy" in (_captured.get("forbidden_providers") or []),
          "agy must be forbidden, not merely un-preferred — preference alone does not bind")

    # An unrestricted protocol keeps the pre-V4.114.0 behaviour exactly: the
    # whole chain offered, nothing forbidden.
    _mr._acquire("agentic_protocol", "claude", _cfg, protocol=True, protocol_name="news")
    check("allowlist.unrestricted_untouched", not (_captured.get("forbidden_providers") or []),
          repr(_captured.get("forbidden_providers")))

    # Allowlist naming only providers that are switched off must block, not fall
    # through to whatever the chain happens to offer.
    _cfg_off = dict(_cfg)
    _cfg_off["protocol_providers"] = {"invest": ["codex"]}
    _cfg_off["enabled"] = {**_cfg["enabled"], "codex": False}
    _lease, _note, _allowed = _mr._acquire("agentic_protocol", "claude", _cfg_off,
                                           protocol=True, protocol_name="invest")
    check("allowlist.fail_closed", _allowed is False, f"note={_note}")
    check("allowlist.reason_explains", "protocol_providers" in _mr._blocked_reason(_note), _note)
finally:
    _mr.broker_gate.broker_client = _old_client

# A present-but-unusable allowlist is a typo, not permission to use anything.
check("allowlist.malformed_blocks",
      _mr.protocol_provider_allowlist({"protocol_providers": {"invest": "claude"}}, "invest") == [])
check("allowlist.empty_blocks",
      _mr.protocol_provider_allowlist({"protocol_providers": {"invest": []}}, "invest") == [])
check("allowlist.explicit_null_unrestricted",
      _mr.protocol_provider_allowlist({"protocol_providers": {"invest": None}}, "invest") is None)
# The loader is a whitelist, not a merge — a key it was not taught about is
# dropped silently and the allowlist never takes effect. Same trap the rolling
# window budget hit in V4.84.0, so it is pinned end-to-end against the real file.
check("allowlist.survives_loader",
      _mr.protocol_provider_allowlist(_mr.load_llm_config(), "invest") == ["claude", "codex"],
      repr(_mr.protocol_provider_allowlist(_mr.load_llm_config(), "invest")))

# V4.114.0 — the preamble is no longer codex-only, and it now carries the two
# things the 2026-08-09 invest failure proved were load-bearing: the provider's
# OWN context file (agy loads none of its own accord) and this protocol's spec
# path (a bare `分析 NOW` routes to nothing without a trigger table). Claude is
# still returned untouched — it auto-loads CLAUDE.md, which is the assumption
# every PROTOCOL_PROMPTS entry was written against.
check("prompt.claude_unchanged", ds._adapt_protocol_prompt("claude", "BASE", "invest") == "BASE")

for _model, _ctx in (("codex", "AGENTS.md"), ("grok", "AGENTS.md"), ("gemini", "GEMINI.md")):
    adapted = ds._adapt_protocol_prompt(_model, "BASE", "invest")
    check(f"prompt.{_model}.own_context", f"`{_ctx}`" in adapted, adapted)
    # Naming another provider's file would send the agent to rules that are not
    # its own — the thing the per-provider context split exists to prevent.
    _others = {"CLAUDE.md", "AGENTS.md", "GEMINI.md"} - {_ctx}
    check(f"prompt.{_model}.no_foreign_context",
          not any(o in adapted for o in _others), adapted)
    check(f"prompt.{_model}.protocol_doc",
          "investment/investment_protocol_v5_0.md" in adapted, adapted)
    check(f"prompt.{_model}.tool_mapping", "Read/Write/Edit" in adapted, adapted)
    check(f"prompt.{_model}.subagents", "subagent" in adapted, adapted)
    check(f"prompt.{_model}.cwd_scope", "cwd" in adapted, adapted)
    check(f"prompt.{_model}.original", adapted.endswith("BASE"), adapted)

# An unknown protocol still gets the context + vocabulary preamble; only the
# spec-path line drops out. Silently returning the bare prompt here would
# reintroduce the failure for any protocol missing from PROTOCOL_DOC.
_unknown = ds._adapt_protocol_prompt("gemini", "BASE", "not_a_protocol")
check("prompt.unknown_protocol.context", "`GEMINI.md`" in _unknown, _unknown)
check("prompt.unknown_protocol.original", _unknown.endswith("BASE"), _unknown)

# Provider identity has two layers: the raw entitlement slug remains available
# for diagnostics, while the UI gets a public plan label. Claude's optional
# local annotation follows the same contract instead of overwriting `plan`.
_old_plan_reader = ds._claude_plan_label
try:
    ds._claude_plan_label = lambda: "MAX 5×"
    _plans = ds._annotate_plans({"broker": {"providers": {
        "claude": {"plan": None, "plan_label": None},
        "codex": {"plan": "prolite", "plan_label": "ChatGPT Pro 5x",
                  "current_model": "gpt-5.6-sol"},
    }}})["broker"]["providers"]
finally:
    ds._claude_plan_label = _old_plan_reader

check("plans.claude_public_label", _plans["claude"].get("plan_label") == "MAX 5×",
      repr(_plans["claude"]))
check("plans.claude_raw_untouched", _plans["claude"].get("plan") is None,
      repr(_plans["claude"]))
check("plans.codex_public_label",
      _plans["codex"].get("plan_label") == "ChatGPT Pro 5x", repr(_plans["codex"]))
check("plans.codex_model", _plans["codex"].get("current_model") == "gpt-5.6-sol",
      repr(_plans["codex"]))

_utils_source = (ROOT / "Dashboard" / "utils.js").read_text(encoding="utf-8")
check("plans.ui_uses_public_label", "info.plan_label" in _utils_source)
check("plans.ui_shows_current_model", "info.current_model" in _utils_source)
check("plans.ui_hides_raw_code", "String(info.plan)" not in _utils_source,
      "provider-native plan codes must remain diagnostic-only")

# Every protocol that runs through PROTOCOL_PROMPTS must name a spec document,
# and that document must exist. A typo'd path reads as a working preamble.
for _name in ds.PROTOCOL_PROMPTS:
    _doc = ds.PROTOCOL_DOC.get(_name)
    check(f"protocol_doc.present.{_name}", bool(_doc), f"{_name} has no PROTOCOL_DOC entry")
    if _doc:
        check(f"protocol_doc.exists.{_name}",
              os.path.exists(os.path.join(ds.ROOT, _doc)), _doc)

# UI progress, error extraction, and usage accounting understand Codex JSONL.
events = [
    {"type": "thread.started", "thread_id": "abc123456789xyz"},
    {"type": "turn.started"},
    {"type": "item.started", "item": {"type": "command_execution", "command": "python validator.py"}},
    {"type": "item.completed", "item": {"type": "command_execution", "command": "python validator.py", "exit_code": 0}},
    {"type": "item.completed", "item": {"type": "agent_message", "text": "artifact written"}},
    {"type": "turn.completed", "usage": {"input_tokens": 120, "cached_input_tokens": 80, "output_tokens": 30}},
]
fd, log_path = tempfile.mkstemp(prefix="protocol_codex_", suffix=".jsonl")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")
    parsed = ds._parse_events(log_path)
    text = " ".join(e["text"] for e in parsed)
    check("events.session", "Codex session started" in text, text)
    check("events.command", "python validator.py" in text, text)
    check("events.message", "artifact written" in text, text)
    usage = parse_stream_log_usage(log_path)
    check("usage.input", usage.get("input_tokens") == 120, repr(usage))
    check("usage.cached", usage.get("cache_read_tokens") == 80, repr(usage))
    check("usage.output", usage.get("output_tokens") == 30, repr(usage))
finally:
    os.unlink(log_path)

fd, error_path = tempfile.mkstemp(prefix="protocol_codex_error_", suffix=".jsonl")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "turn.failed", "error": {"message": "quota exhausted"}}) + "\n")
    check("error.codex", ds._extract_error_from_log(error_path, 1) == "quota exhausted")
finally:
    os.unlink(error_path)

if failures:
    print("FAIL")
    for failure in failures:
        print(" -", failure)
    raise SystemExit(1)
print("✓ protocol model routing contract holds")

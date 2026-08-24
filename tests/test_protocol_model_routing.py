#!/usr/bin/env python3
"""Regression contract for Dashboard agentic protocol model routing."""
from __future__ import annotations

import fnmatch
import inspect
import json
import os
import sys
import tempfile
from datetime import datetime
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

# ── V4.129.0: agy's assigned model has to reach the CLI ─────────────────────
# agy meters its Gemini models and its Claude/GPT models in two pools that
# refill independently. The broker reserves against ONE of them and hands back
# the model that lands there; without `--model` the CLI runs whatever is
# selected in its own TUI, so the hold and the spend can be in different pools.
# Before V4.129.0 nothing here passed a model at all, which is also why one
# exhausted pool used to take the whole provider out of routing.
_amcmd = ds._protocol_command("gemini", "RUN", agy_model="gemini-3.6-flash-medium",
                              timeout_sec=3600)
check("gemini.model_flag_present", "--model" in _amcmd, repr(_amcmd))
check("gemini.model_flag_value",
      _amcmd[_amcmd.index("--model") + 1] == "gemini-3.6-flash-medium", repr(_amcmd))
check("gemini.model_absent_when_unassigned", "--model" not in ds._protocol_command(
    "gemini", "RUN", timeout_sec=3600),
      "no assignment must leave the CLI's own selection alone")
# The flag is agy's; the other providers must not grow one by accident.
check("codex.no_agy_model",
      "--model" not in ds._protocol_command("codex", "RUN", agy_model="gemini-3.6-flash-medium"),
      "agy_model is agy's; it must not leak into another CLI's argv")

# Wiring, not just behaviour (MAINTENANCE 2c member #7): the assertions above
# call `_protocol_command` directly, so deleting `agy_model=` from the launcher
# would leave every one of them green while no run ever pinned a model again.
# `run_protocol` spawns a thread and a subprocess, so its source is what can be
# checked here — a static read, but it is anchored on the real call site.
_launcher_src = inspect.getsource(ds.run_protocol)
check("gemini.model_wired_into_launcher", "agy_model=agy_model" in _launcher_src,
      "run_protocol must pass the assigned model to _protocol_command")
check("gemini.model_read_from_lease_in_launcher",
      "assigned_model(proto_lease)" in _launcher_src,
      "the model has to come off the lease that reserved the pool, not from config")

# The value itself comes off the lease, and `assigned_model` is the only reader.
# An empty lease (broker off, or a single-pool provider) must produce no flag
# rather than an empty one, which agy would reject.
check("gemini.assigned_model_empty_is_none",
      ds._mrouter.broker_gate.assigned_model(None) == "",
      "no lease means no assignment")
check("gemini.assigned_model_reads_lease",
      ds._mrouter.broker_gate.assigned_model(
          type("L", (), {"model": "gemini-3.6-flash-medium"})()) == "gemini-3.6-flash-medium")
check("gemini.assigned_model_tolerates_old_client",
      ds._mrouter.broker_gate.assigned_model(type("L", (), {})()) == "",
      "a vendored client predating the field is a stale sync, not a crash")

# ── V4.116.2: every protocol with a documented gate must be registered ───────
# `invest` was missing from PROTOCOL_VALIDATORS for its whole life while
# CLAUDE.md § Validator Gates listed it, so the heaviest protocol was the one
# whose validator ran only when the model chose to run it. A missing dict key
# has no symptom — nothing errors, the run just completes ungated — which is
# why it needs an assertion rather than a reading.
_GATE_DOCUMENTED = {          # CLAUDE.md § Validator Gates
    "news":   "news/scripts/validate_digest_output.py",
    "sector": "sector/scripts/validate_sector_intel.py",
    "invest": "investment/scripts/validate_session_export.py",
}
for _proto, _script in _GATE_DOCUMENTED.items():
    _registered = ds.PROTOCOL_VALIDATORS.get(_proto) or []
    check(f"validator_registered.{_proto}", _script in _registered,
          f"CLAUDE.md documents {_script} for `{_proto}` but PROTOCOL_VALIDATORS has "
          f"{_registered or 'nothing'} — the gate exists and never runs")

_invest_validator_args = ds.PROTOCOL_VALIDATOR_ARGS.get("invest") or []
check("validator_args.invest_isolated_session",
      _invest_validator_args == [
          "--history", "investment/invest_logs/session_exports/{today}_{ticker}.json",
          "--require-committed-to", "investment/invest_logs/history.json"],
      repr(_invest_validator_args))
_invest_protocol_text = Path(ds.PROTOCOL_DOC["invest"]).read_text(encoding="utf-8")
check("validator_args.invest_producer_path_wired",
      "investment/invest_logs/session_exports/<DATE>_<T>.json" in _invest_protocol_text,
      "invest protocol does not produce the isolated path family validated by the server")

for _proto, _paths in ds.PROTOCOL_VALIDATORS.items():
    for _p in _paths:
        check(f"validator_exists.{_proto}", os.path.exists(os.path.join(ds.ROOT, _p)), _p)

# The validator reads the last history entry, which a run that died before
# writing did not produce — so `invest` also needs an artifact that cannot be
# inherited from the previous session.
_inv_artifacts = ds.PROTOCOL_REQUIRED_ARTIFACTS.get("invest") or []
check("required_artifact.invest_present", bool(_inv_artifacts),
      "a run that writes nothing would validate the PREVIOUS session's entry and pass")
for _a in _inv_artifacts:
    check("required_artifact.invest_templated",
          "{ticker}" in _a and "{today_compact}" in _a,
          f"{_a} — a deep-dive report path needs both the ticker and the compact date")

# V4.131.14 — the same inheritance problem applies to every gated protocol, not
# just invest: sector/news validators read whichever cache is newest, so a run
# that halted at a HARD gate validates the PREVIOUS day's file and passes. On
# 2026-08-16 four sector runs died at the Phase 1 valuation gate and every one
# rendered as a completed scan, because `sector` was never listed in
# PROTOCOL_REQUIRED_ARTIFACTS — the comment there named the sector/news families
# from the start, which is exactly why nobody noticed the keys were absent.
for _proto in _GATE_DOCUMENTED:
    check(f"required_artifact.{_proto}_present",
          bool(ds.PROTOCOL_REQUIRED_ARTIFACTS.get(_proto)),
          f"`{_proto}` has a documented validator gate but no required artifact — "
          f"a run that halts early exits rc=0 and looks identical to a finished one")

# Producer/consumer agreement (§2c #8): the gate's path and the preflight panel's
# glob must resolve to the same file. They live ~1300 lines apart in one module
# and are written by hand twice; when they drift, the gate silently checks a path
# nothing ever writes and passes forever.
_PREFLIGHT_PATTERN = {i["key"]: i.get("pattern") for i in ds.PREFLIGHT_ITEMS}
for _proto in ("sector", "news"):
    _pat = _PREFLIGHT_PATTERN.get(_proto)
    for _a in ds.PROTOCOL_REQUIRED_ARTIFACTS.get(_proto) or []:
        _resolved = _a.replace("{today}", "2026-08-14")
        check(f"required_artifact.{_proto}_matches_preflight",
              bool(_pat) and fnmatch.fnmatch(_resolved, _pat),
              f"gate wants {_resolved!r} but the freshness panel globs {_pat!r}")

# Signal Queue dispatches these two protocols and only marks them consumed when
# the server reports `done`. Both execution families must therefore prove a
# fresh report exists; trusting rc=0 recreates the stale-success bug at the card.
_EARNINGS_ARTIFACTS = {
    "earnings": "reports/{today}_{ticker}_earnings.md",
    "earnings_preview": "reports/{today_compact}_{ticker}_pre_earnings.md",
}
for _proto, _wanted in _EARNINGS_ARTIFACTS.items():
    check(f"required_artifact.{_proto}_exact",
          _wanted in (ds.PROTOCOL_REQUIRED_ARTIFACTS.get(_proto) or []),
          repr(ds.PROTOCOL_REQUIRED_ARTIFACTS.get(_proto)))
check("required_artifact.agentic_wired",
      "_required_artifact_error(" in inspect.getsource(ds.run_protocol),
      "agentic earnings must run the shared freshness gate")
check("required_artifact.script_wired",
      "_required_artifact_error(" in inspect.getsource(ds._run_script_protocol),
      "earnings_preview bypasses run_protocol, so its script runner needs the gate too")

_old_root = ds.ROOT
try:
    with tempfile.TemporaryDirectory(prefix="signal_artifact_gate_") as _tmp:
        ds.ROOT = _tmp
        _reports = Path(_tmp) / "reports"
        _reports.mkdir()
        _start = datetime(2026, 8, 18, 12, 0, 0)
        _report = _reports / "2026-08-18_FN_earnings.md"
        _report.write_text("old", encoding="utf-8")
        os.utime(_report, (_start.timestamp() - 60, _start.timestamp() - 60))
        check("required_artifact.stale_rejected",
              ds._required_artifact_error("earnings", {"ticker": "FN"}, _start) is not None)
        os.utime(_report, (_start.timestamp() + 1, _start.timestamp() + 1))
        check("required_artifact.fresh_accepted",
              ds._required_artifact_error("earnings", {"ticker": "FN"}, _start) is None)
        check("signal_report.fresh_only",
              ds._signal_report_path("earnings", "FN", since=_start.isoformat())
              == "reports/2026-08-18_FN_earnings.md")
finally:
    ds.ROOT = _old_root

# Every exit after a Signal Queue accept must hit the same terminal writeback:
# explicit pending removal, rejection before dispatch, and normal completion.
_removed_src = inspect.getsource(ds.remove_from_queue)
_worker_src = inspect.getsource(ds._analyze_worker) + inspect.getsource(ds._finalize_inflight_runs)
check("signal_delivery.remove_wired", "_record_signal_delivery(" in _removed_src)
check("signal_delivery.worker_paths_wired", _worker_src.count("_record_signal_delivery(") >= 2,
      "worker needs both pre-dispatch rejection and normal completion writebacks")
_old_available = ds.SIGNAL_QUEUE_AVAILABLE
_old_signal_queue = ds._signal_queue
_delivery_calls = []


class _FakeSignalQueue:
    @staticmethod
    def record_delivery(*args, **kwargs):
        _delivery_calls.append((args, kwargs))


try:
    ds.SIGNAL_QUEUE_AVAILABLE = True
    ds._signal_queue = _FakeSignalQueue()
    _signal_entry = {
        "name": "earnings",
        "params": {"signal_id": "earnings:FN", "signal_revision": "rev1",
                   "signal_refs": [], "ticker": "FN"},
    }
    check("signal_delivery.helper_success",
          ds._record_signal_delivery(_signal_entry, status="failed", error="cancelled"))
    check("signal_delivery.helper_payload",
          bool(_delivery_calls)
          and _delivery_calls[0][0][:2] == ("earnings:FN", "rev1")
          and _delivery_calls[0][1].get("status") == "failed",
          repr(_delivery_calls))
    _queued_entry = {**_signal_entry, "id": "signal_contract_cancel"}
    # Hold the protocol lock so the daemon worker cannot race this direct queue
    # cancellation check after we append the fixture.
    with ds._protocol_lock:
        with ds._protocol_queue_lock:
            ds._protocol_queue.append(_queued_entry)
        _removed = ds.remove_from_queue("signal_contract_cancel")
    check("signal_delivery.pending_remove_returns_true", _removed)
    check("signal_delivery.pending_remove_writes_failed",
          len(_delivery_calls) == 2
          and _delivery_calls[1][1].get("status") == "failed"
          and "removed" in (_delivery_calls[1][1].get("error") or ""),
          repr(_delivery_calls))
finally:
    ds.SIGNAL_QUEUE_AVAILABLE = _old_available
    ds._signal_queue = _old_signal_queue

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
    check("allowlist.reason_explains", "certified" in _mr._blocked_reason(_note), _note)
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
# Compared against the file itself, not a literal copy of today's roster: which
# CLIs may run invest is a policy decision that legitimately changes (V4.131.12
# added gemini after the SNDK trial), and a second hardcoded copy here would only
# prove the two literals were typed alike. Reading the raw JSON still catches the
# trap this guards — a dropped key makes the loader return None (unrestricted)
# while the file says a list, and that mismatch fails.
with open(ROOT / "config/llm_config.json", encoding="utf-8") as _f:
    _raw_invest = json.load(_f)["protocol_providers"]["invest"]
check("allowlist.survives_loader",
      _mr.protocol_provider_allowlist(_mr.load_llm_config(), "invest") == _raw_invest,
      repr(_mr.protocol_provider_allowlist(_mr.load_llm_config(), "invest")))

# V4.114.0 — the preamble is no longer codex-only, and it now carries the two
# things the 2026-08-09 invest failure proved were load-bearing: the provider's
# OWN context file (agy loads none of its own accord) and this protocol's spec
# path (a bare `分析 NOW` routes to nothing without a trigger table). Claude is
# still returned untouched — it auto-loads CLAUDE.md, which is the assumption
# every PROTOCOL_PROMPTS entry was written against.
check("prompt.claude_unchanged", ds._adapt_protocol_prompt("claude", "BASE", "invest") == "BASE")

for _model, _ctx in (("codex", "AGENTS.md"), ("gemini", "GEMINI.md")):
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
    # V4.116.1 — the preamble has to say what to do when a gate fails, not only
    # that gates matter. The 2026-08-09 run met a validator rc=1 by editing the
    # input until it passed; every protocol doc forbade accepting rc≠0 and none
    # named the alternative, which left "make the check pass" as the cheapest
    # available reading.
    check(f"prompt.{_model}.gate_discipline", "validator" in adapted and "非 0" in adapted,
          adapted)
    check(f"prompt.{_model}.no_input_fitting", "禁止為了讓檢查通過而修改輸入" in adapted,
          adapted)
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
_style_source = (ROOT / "Dashboard" / "style.css").read_text(encoding="utf-8")
check("plans.ui_uses_public_label", "info.plan_label" in _utils_source)
check("plans.ui_shows_current_model", "info.current_model" in _utils_source)
check("plans.ui_hides_raw_code", "String(info.plan)" not in _utils_source,
      "provider-native plan codes must remain diagnostic-only")
check("broker_handshake.ui_restart_button", "data-broker-restart" in _utils_source)
check("broker_handshake.ui_calls_owner", "/api/broker/restart" in _utils_source)
check("broker_active.ui_reads_reservations", "broker.active_reservations" in _utils_source)
check("broker_active.ui_merges_protocol_and_broker", "UI._llmBrokerRuns" in _utils_source)
check("broker_active.ui_local_green_external_blue",
      "run.is_local_project === true ? 'local' : 'external'" in _utils_source
      and "sidebar-llm-live-local" in _utils_source
      and "sidebar-llm-live-external" in _utils_source
      and ".sidebar-llm-live-local { --llm-live-color: #10b981; }" in _style_source
      and ".sidebar-llm-live-external { --llm-live-color: #3b82f6; }" in _style_source,
      "the quota panel must not paint shared-broker activity green by default")
check("broker_active.ui_exclusive_slot_local_wins",
      "const externalRun = localRun ? null : externalRuns.find(" in _utils_source,
      "one broker-exclusive provider slot must not render the same local lease green and blue")
check("protocol_pill.ui_aggregates_active_heading",
      "activeNames.length === 1" in _utils_source
      and "activeLabels.join(' / ')" in _utils_source
      and "AI research'} ×${active.length}" in _utils_source,
      "the collapsed heading must represent every active run, not only active[0]")
check("protocol_pill.ui_pending_remove_by_id",
      'data-proto-queue-remove="${queueId}"' in _utils_source
      and '/api/protocol-queue/${encodeURIComponent(queueId)}' in _utils_source
      and "method: 'DELETE'" in _utils_source,
      "pending removal must use the queue entry id and the dedicated DELETE endpoint")
check("protocol_pill.ui_pending_remove_styled",
      ".proto-pill-queue-remove" in _style_source,
      "the pending remove control must remain visible and clickable")
check("protocol_pill.ui_premarket_source_label",
      "run?.source !== 'premarket_chain'" in _utils_source
      and "news: 'News Digest'" in _utils_source
      and "sector: 'Sector Scan'" in _utils_source
      and "protoSourceLabel(q, isZh)" in _utils_source,
      "pre-market news/sector jobs must carry workflow provenance in the global queue")
check("protocol_pill.ui_daily_not_a_provider_slot",
      "daily: '" not in _utils_source
      and "daily_update remains visible in the pre-market modal" in _utils_source,
      "daily_update is not broker-governed and must not consume a provider slot")

# The caller-side endpoint owns the restart. Exercise the helper without
# touching launchd: a successful command must still wait for a matching health
# handshake before it tells the button to unlock.
_old_which = ds.shutil.which
_old_run = ds.subprocess.run
_old_status = ds._mrouter.model_status
try:
    ds.shutil.which = lambda _name: "/usr/local/bin/lqb"
    ds.subprocess.run = lambda *a, **k: type("Done", (), {"returncode": 0})()
    ds._mrouter.model_status = lambda: {
        "broker": {"handshake_status": "compatible", "authority": True}
    }
    _restart_code, _restart_payload = ds._restart_broker()
finally:
    ds.shutil.which = _old_which
    ds.subprocess.run = _old_run
    ds._mrouter.model_status = _old_status
check("broker_handshake.restart_endpoint_ok", _restart_code == 200, repr(_restart_payload))
check("broker_handshake.restart_rehandshakes", _restart_payload.get("ok") is True,
      repr(_restart_payload))

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

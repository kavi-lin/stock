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


# Primary selection delegates to the shared governor instead of pinning Claude.
old_pick = ds._mrouter.pick_model
try:
    ds._mrouter.pick_model = lambda role="": "codex"
    check("selection.primary", ds._select_protocol_model() == "codex")
finally:
    ds._mrouter.pick_model = old_pick

# Codex gets a writable agentic command rooted at this repo, with options before
# the prompt so prompts beginning with '-' cannot be parsed as CLI flags.
cmd = ds._protocol_command("codex", "RUN PROTOCOL")
check("codex.binary", cmd[:2] == [ds.CODEX_BIN, "exec"], repr(cmd))
check("codex.json", "--json" in cmd, repr(cmd))
check("codex.cwd", cmd[cmd.index("-C") + 1] == ds.ROOT, repr(cmd))
check("codex.permissions", "--dangerously-bypass-approvals-and-sandbox" in cmd, repr(cmd))
check("codex.prompt_last", cmd[-1] == "RUN PROTOCOL", repr(cmd))

adapted = ds._adapt_protocol_prompt("codex", "BASE")
check("prompt.tool_mapping", "Map Read/Write/Edit" in adapted, adapted)
check("prompt.subagents", "collaboration subagent" in adapted, adapted)
check("prompt.original", adapted.endswith("BASE"), adapted)
check("prompt.claude_unchanged", ds._adapt_protocol_prompt("claude", "BASE") == "BASE")

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

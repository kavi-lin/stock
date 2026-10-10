"""Single-shot drivers must report what a run cost, for every provider.

This is the gap that made the quota broker's calibration wrong rather than
merely coarse. `run_claude` had always parsed its envelope's `usage`, so the
ledger looked healthy; `run_gemini` never asked for structured output at all and
`run_codex` asked for it and then read only the answer out of it. Both settled
every run with zero tokens — which, in a ledger, is indistinguishable from a run
that was free. Measured on the live database: 96% of Agy runs and 97% of Codex
runs. The broker's percent-per-1k-token rate was therefore set by the surviving
few percent, and read an order of magnitude cheap.

The assertions here are about the two things that must both hold: the CLI is
asked for the structured stream, and the numbers in it reach `LLMResult`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._shared import broker_gate  # noqa: E402
from scripts.break_news import llm_drivers  # noqa: E402

AGY_STREAM = json.dumps({
    "event": "result",
    "result": {
        "response": '{"ok": true}',
        "usage": {"input_tokens": 310, "output_tokens": 27, "cache_read_tokens": 120},
    },
})

#: Two event shapes on purpose: the driver reads the answer out of
#: `item.completed`, while the usage totals arrive nested under `msg`. Reading
#: only the first is exactly how this stream was being consumed — the numbers
#: were in the stdout the driver already had, one event further down.
CODEX_STREAM = "\n".join([
    json.dumps({"type": "item.completed",
                "item": {"type": "agent_message", "text": '{"ok": true}'}}),
    json.dumps({"msg": {"total_token_usage": {
        "input_tokens": 900, "output_tokens": 42, "cached_input_tokens": 800}}}),
])


def _record(monkeypatch, stdout: str) -> list:
    calls: list = []

    def fake_run_cli(cmd, timeout, process_callback=None):
        calls.append(cmd)
        return 0, stdout, "", 1, None

    monkeypatch.setattr(llm_drivers, "_run_cli", fake_run_cli)
    return calls


def test_agy_is_asked_for_the_stream_that_carries_its_usage(monkeypatch) -> None:
    calls = _record(monkeypatch, AGY_STREAM)

    result = llm_drivers.run_gemini("SYS", "USR")

    argv = calls[0]
    assert argv[argv.index("--output-format") + 1] == "stream-json", (
        "without the flag the CLI prints prose and no usage is emitted anywhere")
    assert result.parsed == {"ok": True}, "the answer now arrives as a `result` event"
    assert (result.input_tokens, result.output_tokens) == (310, 27)
    assert result.cache_read_tokens == 120


def test_codex_usage_events_are_no_longer_read_past(monkeypatch) -> None:
    _record(monkeypatch, CODEX_STREAM)

    result = llm_drivers.run_codex("SYS", "USR")

    assert result.parsed == {"ok": True}
    assert (result.input_tokens, result.output_tokens) == (900, 42)
    assert result.cache_read_tokens == 800, "`cached_input_tokens`, under `msg`"


def test_what_the_driver_reports_is_what_the_broker_is_told(monkeypatch) -> None:
    """The settlement path drops zeros, so zeros here mean a run recorded free."""
    _record(monkeypatch, AGY_STREAM)

    result = llm_drivers.run_gemini("SYS", "USR")
    usage = broker_gate.usage_for_broker({
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cache_read_tokens": result.cache_read_tokens,
        "cache_write_tokens": result.cache_write_tokens,
    })

    assert usage["input_tokens"] == 310
    assert usage["output_tokens"] == 27
    assert usage["cache_read_tokens"] == 120


def test_a_run_with_no_usage_in_it_reports_zero_rather_than_guessing(monkeypatch) -> None:
    """A stream that said nothing about tokens stays at zero.

    Zero is what the broker reads as "the vendor did not report this field": its
    calibration discards zero-token intervals rather than treating them as
    evidence that a run was free. Inventing a plausible number here would be the
    one failure it could not detect.
    """
    _record(monkeypatch, "")

    result = llm_drivers.run_gemini("SYS", "USR")

    assert (result.input_tokens, result.output_tokens) == (0, 0)
    assert result.cache_read_tokens == 0

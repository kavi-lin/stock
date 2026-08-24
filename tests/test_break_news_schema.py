import copy
import json
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.break_news import debater
from scripts.break_news import prompts
from scripts.break_news import schema as agent_schema
from scripts.break_news import validate as log_validator
from scripts.break_news.llm_drivers import LLMResult


def valid_opening() -> dict:
    return {
        "commentary": "市" * 80,
        "bull_points": ["需求成長支撐營收"],
        "bear_points": ["估值偏高限制漲幅"],
        "final_take": "偏多但需等待訂單確認",
        "entities": {
            "tickers": ["NVDA"],
            "sectors": ["Information Technology"],
            "themes": ["AI capex"],
            "tech_keywords": ["Blackwell"],
        },
        "relations": [{
            "subject": "ticker:NVDA",
            "predicate": "BENEFITS_FROM",
            "object": "narrative:ai_capex",
        }],
        "done": False,
        "confidence": 0.8,
        "rationale_short": "需求與估值風險並存",
    }


def valid_response(*, dispute: bool = True) -> dict:
    """Side B's round-0 answer to A's opener (V4.132.0 sequential debate)."""
    return {
        "commentary": "市" * 80,
        "assessments": [
            {"point": "bull:0",
             "verdict": "dispute" if dispute else "agree",
             "reason": "訂單能見度僅一季，不足以支撐營收推估"},
            {"point": "bear:0", "verdict": "agree", "reason": "估值確實已反映樂觀情境"},
        ],
        "added_bull": [],
        "added_bear": ["匯率逆風壓縮毛利"],
        "final_take": "偏空，等訂單能見度轉佳",
        "entities": {
            "tickers": ["NVDA"],
            "sectors": ["Information Technology"],
            "themes": ["AI capex"],
            "tech_keywords": ["Blackwell"],
        },
        "relations": [{
            "subject": "ticker:NVDA",
            "predicate": "HEADWIND_FROM" if dispute else "BENEFITS_FROM",
            "object": "narrative:ai_capex",
        }],
        "done": False,
        "confidence": 0.6,
        "rationale_short": "能見度不足",
    }


def valid_arbiter() -> dict:
    return {
        "commentary": "市" * 80,
        "ruling": "side_b",
        "final_take": "採信 B：訂單能見度不足",
        "relations": [],
        "done": True,
        "confidence": 0.72,
        "rationale_short": "能見度是關鍵爭點",
    }


def valid_rebuttal() -> dict:
    return {
        "commentary": "供應瓶頸可能使訂單延後認列",
        "stance": "challenge",
        "relations": [{
            "subject": "ticker:NVDA",
            "predicate": "HEADWIND_FROM",
            "object": "narrative:supply_constraint",
        }],
        "done": False,
        "confidence": 0.7,
        "rationale_short": "供應限制兌現速度",
    }


def llm_result(agent: str, payload: dict | None, *, exit_code: int = 0,
               parse_status: str = "ok") -> LLMResult:
    raw = json.dumps(payload or {}, ensure_ascii=False)
    return LLMResult(
        agent=agent,
        parsed=payload,
        raw_text=raw,
        raw_stdout=raw,
        exit_code=exit_code,
        latency_ms=1,
        parse_status=parse_status,
        error=None,
    )


def test_round_specific_schemas_accept_valid_payloads():
    assert agent_schema.validate_payload(valid_opening(), 0) == []
    assert agent_schema.validate_payload(valid_rebuttal(), 1) == []


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda p: p.pop("final_take"), "missing keys"),
        (lambda p: p.update(commentary="太短"), "outside 80..400"),
        (lambda p: p.update(done=True), "must be false"),
        (lambda p: p["entities"].update(tickers=["nvda"]), "uppercase root ticker"),
        (
            lambda p: p["relations"][0].update(predicate="MOVES_WITH"),
            "unsupported",
        ),
        (lambda p: p.update(extra_field=True), "unexpected keys"),
    ],
)
def test_opening_schema_rejects_contract_drift(mutate, expected):
    payload = valid_opening()
    mutate(payload)

    assert any(expected in issue for issue in agent_schema.validate_payload(payload, 0))


def test_side_decides_the_round0_schema():
    # Same round, different sides — B answers, so B's payload is not an opening.
    assert agent_schema.validate_payload(valid_response(), 0, "B") == []
    assert agent_schema.validate_payload(valid_arbiter(), 2, "C") == []
    assert any("unexpected keys" in issue
               for issue in agent_schema.validate_payload(valid_response(), 0, "A"))
    # A's opener failing puts a blind opening on side B — `kind` overrides side.
    assert agent_schema.validate_payload(valid_opening(), 0, "B", "opening") == []


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda p: p.update(assessments=[]), "item count 0 outside 1..6"),
        (lambda p: p["assessments"][0].update(point="bull:9"), "expected bull:N or bear:N"),
        (lambda p: p["assessments"][0].update(point="bear:0"), "duplicate bear:0"),
        (lambda p: p["assessments"][0].update(verdict="maybe"), "expected agree or dispute"),
        (lambda p: p["assessments"][0].pop("reason"), "missing keys"),
        (lambda p: p.update(bull_points=["屬於開場輪"]), "unexpected keys"),
    ],
)
def test_response_schema_rejects_contract_drift(mutate, expected):
    payload = valid_response()
    mutate(payload)

    assert any(expected in issue
               for issue in agent_schema.validate_payload(payload, 0, "B"))


def test_arbiter_must_rule_and_must_be_final():
    payload = valid_arbiter()
    payload["ruling"] = "both_ok"
    payload["done"] = False

    issues = agent_schema.validate_payload(payload, 2, "C")

    assert any("expected side_a, side_b or split" in issue for issue in issues)
    assert any("arbiter must be true" in issue for issue in issues)


def test_relaxed_lengths_accept_what_the_old_caps_killed():
    """The observed failure mode: real content rejected for a few characters.

    Logged examples — `commentary: length 157 outside 80..150` and
    `bull_points[0]: length 32 exceeds 30` — cost 31% of one day's debates a
    second voice.
    """
    payload = valid_opening()
    payload["commentary"] = "市" * 157
    payload["bull_points"] = ["需" * 32]

    assert agent_schema.validate_payload(payload, 0) == []

    # The first arbiter call ever made died at 243 characters; the cap now sits
    # above the corpus p90, and only a runaway is still rejected.
    payload["commentary"] = "市" * 243
    assert agent_schema.validate_payload(payload, 0) == []

    payload["commentary"] = "市" * 401
    assert any("outside 80..400" in issue
               for issue in agent_schema.validate_payload(payload, 0))


def test_redebate_does_not_summarize_the_abandoned_run(monkeypatch):
    """A re-debate of a partial_closed item must start from an empty thread.

    Observed live: three attempts on one item left all three openers in `thread`,
    so the summary merged three bull/bear lists and `point_assessments` held
    adjudications of an opener that was no longer visible.
    """
    item, prompts_seen = stub_debate(monkeypatch)
    item["state"] = "partial_closed"
    item["thread"] = [{"comment_id": "c0", "agent": "gemini", "side": "A", "round": 0,
                       "parse_status": "ok", "exit_code": 0, "parsed": valid_opening()}]
    wire_runner(monkeypatch, prompts_seen, lambda agent, _n: llm_result(
        agent, valid_opening() if agent == "claude" else valid_response(dispute=False)))

    debater.debate_item("bn_test")

    assert len(item["thread"]) == 2
    assert len(item["retired_threads"]) == 1
    assert len(item["summary"]["final_takes_by_round"]) == 2


def test_polarity_conflict_survives_a_namespace_mismatch():
    """`theme:` vs `narrative:` is a spelling accident, not a difference of view.

    Measured over 260 logged debates: 26% shared a subject|object pair, only
    14% were detectable before the namespace was stripped.
    """
    a = dict(valid_opening())
    a["relations"] = [{"subject": "ticker:LVMUY", "predicate": "BENEFITS_FROM",
                       "object": "theme:climate_change"}]
    b = dict(valid_opening())
    b["relations"] = [{"subject": "ticker:LVMUY", "predicate": "HEADWIND_FROM",
                       "object": "narrative:climate-change"}]
    thread = [{"side": "A", "parsed": a}, {"side": "B", "parsed": b}]

    divergent, note = debater.divergence_gate(thread)

    assert divergent
    assert "relation polarity conflict" in note


def test_rebuttal_schema_rejects_opening_shape_and_bad_stance():
    payload = valid_rebuttal()
    payload["stance"] = "agree"
    payload["bull_points"] = ["不應出現在反駁輪"]

    issues = agent_schema.validate_payload(payload, 1)

    assert any("unexpected keys" in issue for issue in issues)
    assert any("expected challenge or concede" in issue for issue in issues)


def test_provider_error_envelope_never_becomes_analysis(monkeypatch):
    monkeypatch.setattr(debater.store, "write_raw_stdout", lambda *_args: "raw.txt")
    envelope = {"type": "result", "is_error": True, "api_error_status": 429}

    comment = debater._comment_from_result(
        llm_result("claude", envelope, exit_code=1),
        "Analyst-A (Claude)", "A", 0, "bn_test", "c0",
    )

    assert comment["parse_status"] == "failed"
    assert comment["parsed"] is None
    assert comment["schema_errors"] == ["provider exit_code=1"]


def test_broker_blocked_opener_returns_to_pending_with_reason(monkeypatch):
    item, prompts_seen = stub_debate(monkeypatch)
    blocked = llm_result("claude", None, exit_code=-9, parse_status="blocked")
    blocked.error = "LLM call blocked (broker:refused(provider_busy))"
    blocked.route_note = "role=debate blocked(broker:refused(provider_busy))"
    calls = wire_runner(monkeypatch, prompts_seen, lambda _agent, _n: blocked)

    result = debater.debate_item("bn_test")

    assert result["ok"] is False
    assert result["deferred"] is True
    assert item["state"] == "pending_debate"
    assert item["summary"] is None
    assert calls == {"claude": 1}
    assert item["thread"][0]["error"] == blocked.error
    assert item["thread"][0]["route_note"] == blocked.route_note


def test_broker_blocked_responder_does_not_terminalize_a_healthy_opener(monkeypatch):
    item, prompts_seen = stub_debate(monkeypatch)
    blocked = llm_result("gemini", None, exit_code=-9, parse_status="blocked")
    blocked.error = "LLM call blocked (broker:refused(provider_busy))"
    blocked.route_note = "role=debate blocked(broker:refused(provider_busy))"

    def script(agent, _n):
        return llm_result(agent, valid_opening()) if agent == "claude" else blocked

    calls = wire_runner(monkeypatch, prompts_seen, script)

    result = debater.debate_item("bn_test")

    assert result["deferred"] is True
    assert item["state"] == "pending_debate"
    assert item["summary"] is None
    assert calls == {"claude": 1, "gemini": 1}
    assert [comment["exit_code"] for comment in item["thread"]] == [0, -9]


def test_unexpected_roster_exception_restores_pending_state(monkeypatch):
    item, _prompts_seen = stub_debate(monkeypatch)
    monkeypatch.setattr(
        debater,
        "_roster",
        lambda: (_ for _ in ()).throw(ValueError("malformed broker response")),
    )

    result = debater.debate_item("bn_test")

    assert result["deferred"] is True
    assert item["state"] == "pending_debate"
    assert "ValueError: malformed broker response" in item["deferred_reason"]
    assert item["errors"][-1]["where"] == "debate_item"


def test_scan_never_overlaps_items_even_when_two_workers_are_requested(monkeypatch):
    first_active = threading.Event()
    release_first = threading.Event()
    overlap_seen = threading.Event()

    monkeypatch.setattr(debater, "scan_pending", lambda: ["bn_one", "bn_two"])
    monkeypatch.setattr(debater.store, "update_state", lambda *_args, **_kwargs: None)

    def fake_debate(news_id, **_kwargs):
        if news_id == "bn_one":
            first_active.set()
            release_first.wait(timeout=0.05)
            first_active.clear()
        elif first_active.is_set():
            overlap_seen.set()
            release_first.set()
        return {"ok": True, "state": "closed"}

    monkeypatch.setattr(debater, "debate_item", fake_debate)

    result = debater.scan_and_debate(workers=2)

    assert overlap_seen.is_set() is False
    assert result["completed"] == 2


def test_orphaned_debating_item_returns_to_pending_without_touching_recent_one(
        tmp_path, monkeypatch):
    now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    old = now - timedelta(seconds=debater.ORPHAN_STALE_SEC + 1)
    recent = now - timedelta(seconds=debater.ORPHAN_STALE_SEC - 1)
    monkeypatch.setattr(debater.store, "STORE_DIR", tmp_path)

    for news_id, activity in (("bn_old", old), ("bn_recent", recent)):
        (tmp_path / f"{news_id}.json").write_text(json.dumps({
            "news_id": news_id,
            "state": "debating",
            "last_activity_ts": activity.isoformat().replace("+00:00", "Z"),
            "thread": [],
            "summary": None,
        }), encoding="utf-8")

    recovered = debater.recover_orphaned_debates(now)

    old_item = json.loads((tmp_path / "bn_old.json").read_text(encoding="utf-8"))
    recent_item = json.loads((tmp_path / "bn_recent.json").read_text(encoding="utf-8"))
    assert recovered == ["bn_old"]
    assert old_item["state"] == "pending_debate"
    assert "orphaned debating state" in old_item["deferred_reason"]
    assert recent_item["state"] == "debating"


def stub_debate(monkeypatch, *, is_high: bool = False,
                arbiter: str | None = "codex") -> tuple[dict, list]:
    """In-memory store + roster for `debate_item`. Returns (item, prompt_log).

    `prompt_log` records (system_prompt, user_prompt) per call, which is how the
    sequential-turn tests check that B was actually shown A's opener.
    """
    item = {
        "news_id": "bn_test",
        "state": "pending_debate",
        "headline": "Test headline",
        "raw_summary": "Test summary",
        "source": {"name": "Test", "credibility": "HIGH", "url": "https://example.test"},
        "triage": {},
        "thread": [],
        "summary": None,
        "errors": [],
    }
    monkeypatch.setattr(debater, "_roster", lambda: (["claude", "gemini"], arbiter))
    monkeypatch.setattr(debater, "is_high_priority_item", lambda _item: is_high)
    monkeypatch.setattr(debater.store, "load_item", lambda _news_id: item)
    monkeypatch.setattr(
        debater.store, "set_state",
        lambda _news_id, state, **extra: item.update(state=state, **extra),
    )

    def append_comment(_news_id, comment):
        item["thread"].append({"comment_id": f"c{len(item['thread'])}", **comment})

    monkeypatch.setattr(debater.store, "append_comment", append_comment)
    monkeypatch.setattr(debater.store, "set_summary",
                        lambda _news_id, value: item.update(summary=value))
    monkeypatch.setattr(
        debater.store, "push_error",
        lambda _news_id, where, msg: item["errors"].append({"where": where, "msg": msg}),
    )
    monkeypatch.setattr(debater.store, "write_raw_stdout", lambda *_args: "raw.txt")

    def retire_thread(_news_id):
        retired = len(item["thread"])
        item.setdefault("retired_threads", []).append({"thread": item["thread"]})
        item["thread"] = []
        return retired

    monkeypatch.setattr(debater.store, "retire_thread", retire_thread)
    return item, []


def wire_runner(monkeypatch, prompt_log: list, script):
    """Route `run_with_fallback` through `script(agent, call_index)`."""
    calls: dict[str, int] = {}

    def run(agent, _role, system_prompt, user_prompt, *_args, **_kwargs):
        calls[agent] = calls.get(agent, 0) + 1
        prompt_log.append((agent, system_prompt, user_prompt))
        return script(agent, calls[agent])

    monkeypatch.setattr(debater, "run_with_fallback", run)
    return calls


def test_debate_entry_marks_schema_invalid_opener_partial_closed(monkeypatch):
    item, prompts_seen = stub_debate(monkeypatch)
    invalid = valid_opening()
    invalid.pop("final_take")

    # A's opener is rejected, so B has nothing to answer and falls back to a
    # blind opener — the salvage path, which must still yield entities.
    wire_runner(monkeypatch, prompts_seen, lambda agent, _n: llm_result(
        agent, invalid if agent == "claude" else valid_opening()))

    result = debater.debate_item("bn_test")

    assert result["state"] == "partial_closed"
    assert result["close_reason"] == "single_voice"
    assert item["thread"][0]["parse_status"] == "schema_failed"
    assert item["thread"][0]["parsed"] is None
    assert item["thread"][1]["parse_status"] == "ok"
    assert item["summary"]["agent_payload_schema_version"] == \
        agent_schema.AGENT_PAYLOAD_SCHEMA_VERSION
    assert item["summary"]["merged_entities"]["tickers"] == ["NVDA"]


def test_round0_is_sequential_and_b_answers_the_opener(monkeypatch):
    item, prompts_seen = stub_debate(monkeypatch)
    wire_runner(monkeypatch, prompts_seen, lambda agent, _n: llm_result(
        agent, valid_opening() if agent == "claude" else valid_response(dispute=False)))

    debater.debate_item("bn_test")

    assert [c["agent"] for c in item["thread"][:2]] == ["claude", "gemini"]
    assert [c["side"] for c in item["thread"][:2]] == ["A", "B"]
    # B was handed A's actual words, not a blind copy of the news item.
    b_agent, b_system, b_user = prompts_seen[1]
    assert b_agent == "gemini"
    assert b_system == prompts.RESPONDER_SYSTEM_PROMPT
    assert valid_opening()["final_take"] in b_user
    assert "bull:0" in b_user
    # A spoke before B: A's prompt cannot contain B's answer.
    assert valid_response()["final_take"] not in prompts_seen[0][2]


def test_agreement_closes_at_round1_without_extra_calls(monkeypatch):
    item, prompts_seen = stub_debate(monkeypatch)
    calls = wire_runner(monkeypatch, prompts_seen, lambda agent, _n: llm_result(
        agent, valid_opening() if agent == "claude" else valid_response(dispute=False)))

    result = debater.debate_item("bn_test")

    assert result["close_reason"] == "converged_round1"
    assert calls == {"claude": 1, "gemini": 1}
    assert item["summary"]["stated_dispute_count"] == 0
    assert item["summary"]["arbiter_ruling"] is None
    # B contributes only what A missed — no second balanced pair.
    assert "匯率逆風壓縮毛利" in item["summary"]["bear_summary"]


def test_dispute_then_refusal_calls_the_third_model(monkeypatch):
    item, prompts_seen = stub_debate(monkeypatch, is_high=True)

    def script(agent, n):
        if agent == "claude":
            return llm_result(agent, valid_opening() if n == 1 else valid_rebuttal())
        if agent == "gemini":
            return llm_result(agent, valid_response())
        return llm_result(agent, valid_arbiter())

    calls = wire_runner(monkeypatch, prompts_seen, script)

    result = debater.debate_item("bn_test")

    assert result["close_reason"] == "arbitrated"
    assert result["state"] == "closed"
    assert calls == {"claude": 2, "gemini": 1, "codex": 1}
    arbiter_comment = item["thread"][-1]
    assert arbiter_comment["side"] == "C"
    assert arbiter_comment["agent"] == "codex"
    assert "裁決者 C" in arbiter_comment["agent_role_label"]["zh"]
    # The ruling supersedes the losing side's self-assessed confidence.
    assert item["summary"]["final_take"] == valid_arbiter()["final_take"]
    assert item["summary"]["arbiter_ruling"]["ruling"] == "side_b"
    assert item["summary"]["stated_dispute_count"] == 1
    # The arbiter was told what it is ruling on.
    assert "bull:0" in prompts_seen[-1][2]


def test_concession_settles_it_without_the_third_model(monkeypatch):
    item, prompts_seen = stub_debate(monkeypatch, is_high=True)
    conceded = valid_rebuttal()
    conceded["stance"] = "concede"

    def script(agent, n):
        if agent == "claude":
            return llm_result(agent, valid_opening() if n == 1 else conceded)
        return llm_result(agent, valid_response())

    calls = wire_runner(monkeypatch, prompts_seen, script)

    result = debater.debate_item("bn_test")

    assert result["close_reason"] == "divergence_resolved"
    assert "codex" not in calls
    assert item["summary"]["arbiter_ruling"] is None


def test_deadlock_without_an_arbiter_closes_unresolved(monkeypatch):
    item, prompts_seen = stub_debate(monkeypatch, is_high=True, arbiter=None)

    def script(agent, n):
        if agent == "claude":
            return llm_result(agent, valid_opening() if n == 1 else valid_rebuttal())
        return llm_result(agent, valid_response())

    wire_runner(monkeypatch, prompts_seen, script)

    result = debater.debate_item("bn_test")

    assert result["close_reason"] == "unresolved_no_arbiter"
    assert result["state"] == "closed"
    assert item["summary"]["arbiter_model"] is None


def test_debate_entry_marks_schema_invalid_rebuttal_partial_closed(monkeypatch):
    item, prompts_seen = stub_debate(monkeypatch, is_high=True, arbiter=None)
    invalid_rebuttal = valid_rebuttal()
    invalid_rebuttal["stance"] = "agree"

    def script(agent, n):
        if agent == "claude":
            return llm_result(agent, valid_opening() if n == 1 else invalid_rebuttal)
        return llm_result(agent, valid_response())

    wire_runner(monkeypatch, prompts_seen, script)

    result = debater.debate_item("bn_test")

    assert result["state"] == "partial_closed"
    assert result["close_reason"] == "invalid_rebuttal"
    assert item["thread"][-1]["round"] == 1
    assert item["thread"][-1]["parse_status"] == "schema_failed"
    assert item["thread"][-1]["parsed"] is None


def log_payload(comment: dict, *,
                schema_version: int | None = agent_schema.AGENT_PAYLOAD_SCHEMA_VERSION) -> dict:
    summary = {
        "final_takes_by_round": [],
        "merged_relations": [],
    }
    if schema_version is not None:
        summary["agent_payload_schema_version"] = schema_version
    return {
        "news_id": "bn_20260816_test",
        "schema_version": 1,
        "state": "partial_closed",
        "fetched_at": "2026-08-16T00:00:00Z",
        "source": {"name": "Test", "credibility": "HIGH", "url": "https://example.test"},
        "headline": "Test",
        "raw_summary": "Test",
        "triage": {
            "news_type": "company",
            "shallow_score": 3,
            "binary_flag": False,
            "advance_reason": "test",
            "bull_case": "test",
            "bear_case": "test",
            "sector_view": "test",
            "macro_view": "test",
        },
        "thread": [{"comment_id": "c0", "agent": "codex", "round": 0,
                    "ts": "2026-08-16T00:00:01Z", "exit_code": 0, **comment}],
        "summary": summary,
        "errors": [],
        "graph_status": "provisional",
    }


def test_log_validator_enforces_payload_schema_for_new_logs(tmp_path):
    payload = valid_opening()
    payload["confidence"] = 2
    path = tmp_path / "bn_20260816_test.json"
    path.write_text(
        json.dumps(log_payload({"parsed": payload, "parse_status": "ok"})),
        encoding="utf-8",
    )

    issues = log_validator.validate_file(path)

    assert any("expected finite value in 0..1" in issue for issue in issues)


def test_log_validator_accepts_explicitly_rejected_voice(tmp_path):
    path = tmp_path / "bn_20260816_test.json"
    comment = {
        "parsed": None,
        "parse_status": "schema_failed",
        "schema_errors": ["opening: missing keys ['final_take']"],
    }
    path.write_text(json.dumps(log_payload(comment)), encoding="utf-8")

    assert log_validator.validate_file(path) == []


def test_log_validator_rejects_inconsistent_status_and_schema_version(tmp_path):
    path = tmp_path / "bn_20260816_test.json"
    document = log_payload({
        "parsed": valid_opening(),
        "parse_status": "ok",
        "schema_errors": ["stale"],
    })
    document["thread"][0]["exit_code"] = 1
    document["summary"]["agent_payload_schema_version"] = "1"
    path.write_text(json.dumps(document), encoding="utf-8")

    issues = log_validator.validate_file(path)

    assert any("must be integer" in issue for issue in issues)
    assert any("exit_code!=0" in issue for issue in issues)
    assert any("cannot have schema_errors" in issue for issue in issues)


def test_historical_log_without_payload_schema_version_is_not_reinterpreted(tmp_path):
    payload = copy.deepcopy(valid_opening())
    payload.pop("final_take")
    path = tmp_path / "bn_20260816_test.json"
    path.write_text(
        json.dumps(log_payload(
            {"parsed": payload, "parse_status": "ok"}, schema_version=None)),
        encoding="utf-8",
    )

    assert log_validator.validate_file(path) == []


def test_validator_cli_gate_rejects_then_accepts_payload(tmp_path):
    path = tmp_path / "bn_20260816_test.json"
    invalid = valid_opening()
    invalid.pop("final_take")
    path.write_text(
        json.dumps(log_payload({"parsed": invalid, "parse_status": "ok"})),
        encoding="utf-8",
    )
    command = [
        sys.executable,
        str(Path(log_validator.__file__)),
        "--dir",
        str(tmp_path),
    ]

    rejected = subprocess.run(command, capture_output=True, text=True, check=False)

    assert rejected.returncode == 1
    assert "missing keys ['final_take']" in rejected.stdout

    path.write_text(
        json.dumps(log_payload({"parsed": valid_opening(), "parse_status": "ok"})),
        encoding="utf-8",
    )
    accepted = subprocess.run(command, capture_output=True, text=True, check=False)

    assert accepted.returncode == 0
    assert "OK: 1 file(s) validated" in accepted.stdout


def test_link_digest_projection_uses_its_own_schema(tmp_path):
    path = tmp_path / "bn_20260816_link.json"
    document = {
        "news_id": "bn_20260816_link",
        "schema_version": 1,
        "state": "closed",
        "fetched_at": "2026-08-16T00:00:00Z",
        "source": {"name": "Test", "credibility": "MEDIUM", "url": "https://example.test"},
        "headline": "Test",
        "origin": "link_digest",
        "summary": {
            "consensus_verdict": "BULLISH",
            "merged_entities": {"tickers": [], "sectors": [], "themes": [], "tech_keywords": []},
            "merged_relations": [],
            "bull_summary": "bull",
            "bear_summary": "bear",
            "final_take": "take",
            "final_take_by": "link_digest",
            "rounds_completed": 1,
            "closed_at": "2026-08-16T00:00:01Z",
            "close_reason": "link_digest",
            "divergence_note": "note",
        },
    }
    path.write_text(json.dumps(document), encoding="utf-8")

    assert log_validator.validate_file(path) == []

    del document["summary"]["final_take"]
    path.write_text(json.dumps(document), encoding="utf-8")

    assert any("summary missing keys" in issue for issue in log_validator.validate_file(path))

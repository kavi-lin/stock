import copy
import json
from types import SimpleNamespace

import pytest

from scripts.nexus import gap_fill
from scripts._shared import model_router
from scripts.break_news.llm_drivers import LLMResult


def _draft():
    return {
        "draft_id": "draft:hbm",
        "status": "evidence_only",
        "decision_eligible": False,
        "source_topic": {"topic_id": "topic:hbm", "label": "HBM", "score": 90},
        "nodes": [
            {"id": "MU", "ticker": "MU", "layer": "upstream"},
            {"id": "NVDA", "ticker": "NVDA", "layer": "downstream"},
        ],
        "edges": [{"from": "MU", "to": "NVDA", "rel": "SUPPLIES_TO", "evidence_level": "corroborated"}],
        "context_edges": [],
        "known_gaps": ["private_and_foreign_company_coverage_not_available_in_ticker_only_evidence"],
        "evidence": [{"headline": "HBM demand", "domain": "one.example", "url": "https://one.example/hbm"}],
    }


def _source_packet(draft=None):
    draft = draft or _draft()
    return {
        "packet_id": "packet:hbm",
        "topic_id": "topic:hbm",
        "base_draft_digest": gap_fill._digest(draft),
        "immutable_nodes": [
            {"id": "MU", "ticker": "MU", "layer": "upstream"},
            {"id": "NVDA", "ticker": "NVDA", "layer": "downstream"},
        ],
        "immutable_edges": draft["edges"],
        "sources": [
            {
                "source_id": "src:skh",
                "domain": "news.skhynix.com",
                "headline": "HBM supply",
                "excerpts": [{
                    "excerpt_id": "excerpt:skh",
                    "text": "SK hynix supplies HBM products for accelerated computing platforms.",
                    "provenance": "fetched_page",
                    "verbatim_page_text": True,
                }],
            },
            {
                "source_id": "src:wire",
                "domain": "reuters.com",
                "headline": "HBM reporting",
                "excerpts": [{
                    "excerpt_id": "excerpt:wire",
                    "text": "Industry reporting identifies SK hynix as a major HBM supplier.",
                    "provenance": "fetched_page",
                    "verbatim_page_text": True,
                }],
            },
        ],
        "relation_evidence": [],
    }


def _valid_response():
    return {
        "topic_id": "topic:hbm",
        "proposed_nodes": [{
            "id": "sk_hynix",
            "label": "SK hynix",
            "entity_type": "foreign_company",
            "layer": "upstream",
            "role": "HBM memory supplier",
            "ticker": None,
            "listing": "foreign_listed",
            "market": "KR",
            "citations": [
                {"source_id": "src:skh", "excerpt_ids": ["excerpt:skh"]},
                {"source_id": "src:wire", "excerpt_ids": ["excerpt:wire"]},
            ],
            "reason": "fills the named foreign-company gap",
        }],
        "proposed_edges": [{
            "from": "sk_hynix",
            "to": "NVDA",
            "rel": "SUPPLIES_TO",
            "citations": [{"source_id": "src:wire", "excerpt_ids": ["excerpt:wire"]}],
            "rationale": "reported HBM supply relationship",
        }],
        "unresolved_gaps": ["equipment vendors still unresolved"],
        "notes": [],
    }


def test_one_call_produces_isolated_proposal_without_mutating_base():
    draft = _draft()
    before = copy.deepcopy(draft)
    calls = []

    def fake_call(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(
            exit_code=0, parsed=_valid_response(), model_used="claude",
            agent="claude", route_note="role=nexus_gap_fill claude:ok", error=None,
        )

    packet = _source_packet(draft)
    entry = gap_fill.execute_once(draft, packet, "system", call_fn=fake_call)
    ledger = gap_fill.empty_ledger()
    ledger["entries"].append(entry)

    assert len(calls) == 1
    assert calls[0][0][0] == "nexus_gap_fill"
    assert entry["status"] == "proposed"
    assert entry["inference_turns"] == 1
    assert entry["decision_eligible"] is False
    assert entry["proposal"]["proposed_edges"][0]["evidence_level"] == "llm_proposed"
    assert draft == before
    assert not gap_fill.validate_ledger(
        ledger, {"topic:hbm": draft}, {"topic:hbm": packet},
    )
    sent_packet = calls[0][0][2]
    assert "https://" not in sent_packet
    assert "excerpt:skh" in sent_packet


def test_spent_topic_cannot_run_a_second_turn():
    draft = _draft()
    ledger = gap_fill.empty_ledger()
    ledger["entries"] = [{"topic_id": "topic:hbm", "inference_turns": 1}]

    with pytest.raises(ValueError, match="already consumed"):
        gap_fill.select_draft({"drafts": [draft]}, ledger, "topic:hbm")


def test_pre_call_quota_block_does_not_consume_topic():
    draft = _draft()

    def blocked(*args, **kwargs):
        return SimpleNamespace(
            exit_code=-9, parsed=None, model_used="claude", agent="claude",
            route_note="claude:skip(quota)", error="no model could run",
        )

    entry = gap_fill.execute_once(draft, _source_packet(draft), "system", call_fn=blocked)
    ledger = gap_fill.empty_ledger()
    ledger["entries"] = [entry]

    assert entry["status"] == "blocked"
    assert entry["inference_turns"] == 0
    assert gap_fill.select_draft({"drafts": [draft]}, ledger, "topic:hbm") == draft


def test_validator_rejects_base_drift_and_duplicate_spend():
    draft = _draft()

    def fake_call(*args, **kwargs):
        return SimpleNamespace(
            exit_code=0, parsed=_valid_response(), model_used="claude",
            agent="claude", route_note="ok", error=None,
        )

    packet = _source_packet(draft)
    entry = gap_fill.execute_once(draft, packet, "system", call_fn=fake_call)
    entry["base_draft_digest"] = "sha256:wrong"
    ledger = gap_fill.empty_ledger()
    ledger["entries"] = [entry, copy.deepcopy(entry)]

    errors = gap_fill.validate_ledger(
        ledger, {"topic:hbm": draft}, {"topic:hbm": packet},
    )

    assert any("base_draft_digest mismatch" in error for error in errors)
    assert any("more than one inference turn" in error for error in errors)


def test_proposal_caps_and_source_diversity_are_enforced():
    draft = _draft()
    raw = _valid_response()
    raw["proposed_nodes"] = raw["proposed_nodes"] * 9
    proposal = gap_fill._normalize_response(raw, draft)

    errors = gap_fill._proposal_errors(proposal, draft, _source_packet(draft))

    assert any("exceeds node/edge cap" in error for error in errors)
    assert any("duplicate proposed node id" in error for error in errors)


def test_validator_rejects_unknown_ids_external_urls_and_analyst_only_evidence():
    draft = _draft()
    packet = _source_packet(draft)
    packet["sources"][0]["excerpts"][0]["provenance"] = "claim_analyst_extract"
    packet["sources"][0]["excerpts"][0]["verbatim_page_text"] = False
    raw = _valid_response()
    raw["proposed_nodes"][0]["source_urls"] = ["https://invented.example/source"]
    raw["proposed_edges"][0]["citations"][0]["excerpt_ids"] = ["excerpt:unknown"]
    proposal = gap_fill._normalize_response(raw, draft)

    errors = gap_fill._proposal_errors(proposal, draft, packet)

    assert any("external URLs are forbidden" in error for error in errors)
    assert any("unknown or mismatched excerpt_id" in error for error in errors)


def test_default_selection_skips_higher_score_empty_skeleton():
    empty = _draft()
    empty["source_topic"] = {"topic_id": "topic:empty", "label": "Empty", "score": 99}
    empty["edges"] = []
    empty["evidence_summary"] = {"corroborated_edge_count": 0}
    grounded = _draft()
    grounded["evidence_summary"] = {"corroborated_edge_count": 1}

    selected = gap_fill.select_draft({"drafts": [empty, grounded]}, gap_fill.empty_ledger())

    assert selected["source_topic"]["topic_id"] == "topic:hbm"


def test_check_cli_rejects_proposed_entry_with_bad_citation(tmp_path):
    draft = _draft()
    packet = _source_packet(draft)

    def fake_call(*args, **kwargs):
        return SimpleNamespace(
            exit_code=0, parsed=_valid_response(), model_used="claude",
            agent="claude", route_note="ok", error=None,
        )

    entry = gap_fill.execute_once(draft, packet, "system", call_fn=fake_call)
    entry["proposal"]["proposed_nodes"][0]["citations"][0]["excerpt_ids"] = ["excerpt:bad"]
    drafts_path = tmp_path / "drafts.json"
    packets_path = tmp_path / "packets.json"
    ledger_path = tmp_path / "gap_fills.json"
    drafts_path.write_text(json.dumps({"drafts": [draft]}), encoding="utf-8")
    packets_path.write_text(json.dumps({"packets": [packet]}), encoding="utf-8")
    ledger_path.write_text(json.dumps({
        "schema_version": 1,
        "artifact_class": "exploration_only",
        "decision_use": "forbidden",
        "entries": [entry],
    }), encoding="utf-8")

    rc = gap_fill.main([
        "--drafts", str(drafts_path), "--source-packets", str(packets_path),
        "--output", str(ledger_path), "--check",
    ])

    assert rc == 1


def _llm_result(agent="claude"):
    return LLMResult(
        agent=agent, parsed={"ok": True}, raw_text='{"ok":true}',
        raw_stdout='{"ok":true}', exit_code=0, latency_ms=1,
        parse_status="ok", error=None,
    )


def test_nexus_claude_role_uses_single_turn_text_only_profile(monkeypatch):
    calls = []

    def fake_claude(system_prompt, user_prompt, **kwargs):
        calls.append((system_prompt, user_prompt, kwargs))
        return _llm_result()

    monkeypatch.setattr(model_router.llm_drivers, "run_claude", fake_claude)

    result = model_router._run_model_for_role(
        "claude", "nexus_gap_fill", "SYS", "USR", 360,
    )

    assert result.exit_code == 0
    assert calls == [("SYS", "USR", {
        "timeout": 360,
        "process_callback": None,
        "model": "sonnet",
        "max_turns": 1,
        "strict_mcp": True,
        "no_tools": True,
    })]


def test_broker_lease_reaches_text_only_dispatch_without_fallback(monkeypatch):
    calls = []
    cfg = {
        "primary": "claude",
        "secondary": "gemini",
        "tertiary": "codex",
        "enabled": {"claude": True, "gemini": True, "codex": True, "grok": True},
        "budgets": {},
        "broker": {"enabled": True},
    }

    monkeypatch.setattr(model_router, "load_llm_config", lambda: cfg)
    lease = SimpleNamespace(provider="claude", model="")
    monkeypatch.setattr(
        model_router, "_acquire",
        lambda *args, **kwargs: (lease, "broker:claude", True),
    )
    monkeypatch.setattr(model_router, "_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(model_router, "_settle", lambda *args, **kwargs: None)

    # **kwargs so the fake keeps matching the real dispatcher's signature. The
    # caller gained `provider_model=` in V4.132.0 and this stub did not, which
    # turned a passing test into a TypeError inside the chain.
    def fake_dispatch(model, role, system, user, timeout, **kwargs):
        calls.append((model, role, timeout))
        return _llm_result(model)

    monkeypatch.setattr(model_router, "_run_model_for_role", fake_dispatch)
    monkeypatch.setattr(
        model_router, "run_llm",
        lambda *args, **kwargs: pytest.fail("_run_chain bypassed role-aware dispatcher"),
    )

    result = model_router.run_with_fallback(
        "claude", "nexus_gap_fill", "SYS", "USR", timeout=360,
    )

    assert result.exit_code == 0
    assert calls == [("claude", "nexus_gap_fill", 360)]
    assert result.model_used == "claude"
    assert result.fell_back is False


def test_text_only_profile_reaches_final_claude_cli_argv(monkeypatch):
    calls = []

    def fake_run_cli(cmd, timeout, process_callback=None):
        calls.append((cmd, timeout, process_callback))
        envelope = json.dumps({"result": '{"ok": true}', "usage": {}})
        return 0, envelope, "", 1, None

    monkeypatch.setattr(model_router.llm_drivers, "_run_cli", fake_run_cli)

    result = model_router._run_model_for_role(
        "claude", "nexus_gap_fill", "SYS", "USR", 360,
    )

    assert result.parsed == {"ok": True}
    assert len(calls) == 1
    cmd, timeout, process_callback = calls[0]
    assert timeout == 360
    assert process_callback is None
    assert cmd[cmd.index("--model") + 1] == "sonnet"
    assert cmd[cmd.index("--max-turns") + 1] == "1"
    assert "--strict-mcp-config" in cmd
    assert cmd[cmd.index("--tools") + 1] == ""
    assert "--system-prompt" in cmd
    assert "--append-system-prompt" not in cmd

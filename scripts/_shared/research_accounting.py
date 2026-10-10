"""Durable, metadata-only accounting for research calls through model_router."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from scripts._shared.broker_client import BrokerError, parse_run_stream

ROOT = Path(__file__).resolve().parents[2]
CALLS = ROOT / "news" / "research_cache" / "calls"


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".research-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def records(directory=CALLS):
    return [json.loads(path.read_text()) for path in sorted(directory.glob("*.json"))]


def reconcile(record, response):
    """A positive ACK must name the same execution and match every sent count."""
    execution = response.get("execution") or {}
    reservation = response.get("reservation") or {}
    if reservation.get("reservation_id") != record["reservation_id"]:
        raise BrokerError("settlement reservation mismatch")
    if not execution.get("execution_id"):
        raise BrokerError("settlement execution missing")
    payload = record["settlement"]
    for field, value in payload["usage"].items():
        if (execution.get("usage") or {}).get(field) != value:
            raise BrokerError(f"settlement token mismatch: {field}")
    if execution.get("usage_details") != payload["usage_details"]:
        # Broker supplies schema defaults; compare field values in the facts,
        # keeping omitted token fields distinct from actual zeros.
        actual = execution.get("usage_details") or {}
        expected = payload["usage_details"]
        if actual.get("status") != expected.get("status"):
            raise BrokerError("settlement usage status mismatch")
        facts = {f["key"]: f for f in actual.get("facts", [])}
        if len(facts) != len(expected.get("facts", [])):
            raise BrokerError("settlement usage fact count mismatch")
        for fact in expected.get("facts", []):
            stored = facts.get(fact["key"], {})
            if stored.get("model_source") != fact.get("model_source"):
                raise BrokerError("settlement model provenance mismatch")
            for name, value in fact["tokens"].items():
                if stored.get("tokens", {}).get(name) != value:
                    raise BrokerError(f"settlement usage evidence mismatch: {name}")
    return execution["execution_id"]


def deliver(client, record, directory=CALLS):
    response = client.request("POST", f'/v1/reservations/{record["reservation_id"]}/complete',
                              body=record["settlement"])
    record["execution_id"] = reconcile(record, response)
    record["status"] = "acknowledged"
    record["acknowledged_at"] = utcnow()
    atomic_json(directory / f'{record["call_id"]}.json', record)
    return record


def flush(client, directory=CALLS):
    """Retry delivery only. An interrupted invocation must never be re-run."""
    for record in records(directory):
        if record["status"] == "pending":
            deliver(client, record, directory)
        elif record["status"] == "running":
            pid = record.get("process_pid")
            if pid:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    pid = None
                except PermissionError:
                    pass
            if pid:
                raise BrokerError(f'research process still alive: {record["call_id"]}')
            record.update(status="pending", schema_valid=False, validation_error="owner_interrupted",
                          observed_model=None, latency_ms=None,
                          settlement={"settlement_id": record["call_id"], "usage": {},
                                      "usage_details": {"schema_version": 1, "status": "missing", "facts": []},
                                      "model": record["requested_model"], "exit_code": -1,
                                      "finished_at": utcnow(), "error_class": "cancelled",
                                      "error_detail": "owner interrupted; actual usage unavailable"})
            atomic_json(directory / f'{record["call_id"]}.json', record)
            deliver(client, record, directory)
            raise BrokerError("interrupted research call settled with unknown usage; review required")


def settlement(result, native_model, validation_error=None):
    stream = parse_run_stream("codex", result.raw_stdout or "")
    details = stream.usage_details or {"schema_version": 1, "status": "missing", "facts": []}
    for fact in details["facts"]:
        if fact.get("model"):
            fact["model_source"] = "response"
        if not fact.get("model"):
            fact["model"] = native_model
            fact["model_source"] = "cli_selected"
    message = (result.error or "").lower()
    error_class = None
    if result.exit_code or validation_error:
        if any(x in message for x in ("quota", "usage limit", "rate limit")):
            error_class = "quota"
        elif any(x in message for x in ("unauthorized", "authentication", "login", "401")):
            error_class = "auth"
        elif "timeout" in message:
            error_class = "timeout"
        else:
            error_class = "invalid_output" if validation_error and result.exit_code == 0 else "transient"
    # Do not ship CLI stderr, prompts or transcripts to the broker.
    return {
        "usage": dict(stream.usage or {}), "usage_details": details,
        "model": stream.model or native_model, "exit_code": result.exit_code,
        "finished_at": utcnow(), "error_class": error_class,
        "error_detail": "research schema validation failed" if validation_error and result.exit_code == 0 else error_class,
    }, stream.model

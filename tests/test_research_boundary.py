"""Real router and HTTP entry points with deterministic vendor/broker doubles."""
import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from scripts._shared import broker_gate, model_router, research_accounting as accounting
from scripts.break_news.llm_drivers import LLMResult
from scripts.research import api
from scripts.research.store import Repository


def test_router_reserves_native_model_validates_then_settles(tmp_path, monkeypatch):
    events = []
    def request(method, path, body=None):
        if path.endswith("ready"):
            return {"status":"ok"}
        if path.endswith("health"):
            return {"details": {"usage_details":"1", "task_context":"1", "idempotent_settlement":"1"}}
        events.append(("settle", body))
        return {"reservation":{"reservation_id":"res"},"execution":{
            "execution_id":"exec", "usage":body["usage"],"usage_details":body["usage_details"]}}
    client = SimpleNamespace(request=request)
    lease = SimpleNamespace(provider="codex", reservation_id="res", _stop_heartbeat=lambda:None,
                            attach_process=lambda *args:None)
    def acquire(role, model, cfg, **kwargs):
        assert model == "codex" and kwargs["native_model"] == "gpt-6-luna"
        events.append(("reserve", kwargs))
        return lease, "ok", True
    def run(*args, **kwargs):
        assert kwargs["model"] == "gpt-6-luna" and kwargs["reasoning_effort"] == "max"
        events.append(("invoke", None))
        return LLMResult("codex", {"claims":[]}, "", json.dumps({"type":"turn.completed", "usage":{
            "input_tokens":40,"output_tokens":12,"cached_input_tokens":20}}), 0, 1, "ok", None)
    def validate(payload):
        events.append(("validate", None))
        raise ValueError("bad schema")
    monkeypatch.setattr(accounting, "CALLS", tmp_path)
    # Default arguments intentionally hold their paths; stub only the initial
    # flush because this test owns no previous outbox records.
    monkeypatch.setattr(accounting, "flush", lambda client:None)
    original_deliver = accounting.deliver
    monkeypatch.setattr(accounting, "deliver", lambda client, record:original_deliver(client, record, tmp_path))
    monkeypatch.setattr(broker_gate, "broker_client", lambda cfg=None:client)
    monkeypatch.setattr(model_router, "_acquire", acquire)
    monkeypatch.setattr(model_router, "_record", lambda *args:None)
    monkeypatch.setattr(model_router.llm_drivers, "run_codex", run)
    with pytest.raises(model_router.RunBlocked, match="invalid_output"):
        model_router.run_research_call("research-initial-analysis", "system", "prompt",
                                      context={"phase":"preflight"}, call_id="test-call", validate=validate)
    assert [e[0] for e in events] == ["reserve","invoke","validate","settle"]
    body = events[-1][1]
    assert body["usage"]["input_tokens"] == 40 and body["error_class"] == "invalid_output"
    assert accounting.records(tmp_path)[0]["status"] == "acknowledged"


def test_broker_capability_failure_never_invokes_vendor(monkeypatch):
    client = SimpleNamespace(request=lambda *args:{"details":{}})
    monkeypatch.setattr(broker_gate, "broker_client", lambda cfg=None:client)
    monkeypatch.setattr(model_router.llm_drivers, "run_codex", lambda *a,**kw:pytest.fail("unleased inference"))
    with pytest.raises(model_router.RunBlocked, match="capabilities"):
        model_router.run_research_call("research-initial-analysis", "", "", context={}, call_id="test", validate=lambda p:None)


def test_native_driver_passes_constrained_schema_and_max(tmp_path, monkeypatch):
    from scripts.break_news import llm_drivers
    captured=[]
    def fake(cmd, timeout, callback):
        captured.extend(cmd)
        return 0, json.dumps({"type":"item.completed", "item":{"type":"agent_message","text":"{}"}}), "", 1, None
    monkeypatch.setattr(llm_drivers,"ROOT",tmp_path)
    monkeypatch.setattr(llm_drivers,"_run_cli",fake)
    schema={"type":"object","properties":{},"additionalProperties":False,"required":[]}
    result=llm_drivers.run_codex("system","user",model="gpt-6-luna",reasoning_effort="max",output_schema=schema)
    assert result.exit_code==0
    assert captured[captured.index('--model')+1]=='gpt-6-luna'
    assert 'model_reasoning_effort="max"' in captured
    assert json.loads(__import__('pathlib').Path(captured[captured.index('--output-schema')+1]).read_text())==schema


def test_http_research_route_and_stale_observation(tmp_path, monkeypatch):
    import dashboard_server
    repo = Repository(tmp_path / "research.sqlite3")
    monkeypatch.setattr(api, "Repository", lambda:repo)
    server = ThreadingHTTPServer(("127.0.0.1", 0), dashboard_server.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_address[1]}'
    try:
        with urlopen(url + "/api/research?lane=invest&ticker=NVDA") as response:
            data = json.load(response)
        assert data["ticker"] == "NVDA" and data["cards"] == []
        with pytest.raises(HTTPError) as error:
            urlopen(Request(url + "/api/research/observe", data=json.dumps({
                "lane":"invest","ticker":"NVDA","revision":"stale"}).encode(),
                headers={"Content-Type":"application/json"}))
        assert error.value.code == 409
        with urlopen(url + "/decisions.html") as response:
            assert b'research-panel.js' in response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

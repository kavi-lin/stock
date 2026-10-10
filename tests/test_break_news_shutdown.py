import sys
import threading
import time

from scripts.break_news import debater
from scripts.break_news import llm_drivers
from scripts.break_news.llm_drivers import _CliProcessRegistry


def test_shutdown_hook_stops_active_cli_and_rejects_new_runs(monkeypatch):
    registry = _CliProcessRegistry()
    monkeypatch.setattr(llm_drivers, "_ACTIVE_CLI_RUNS", registry)
    result = {}
    worker = threading.Thread(
        target=lambda: result.setdefault(
            "run", llm_drivers._run_cli(
                [sys.executable, "-c", "import time; time.sleep(60)"],
                timeout=60)),
        daemon=True,
    )
    worker.start()

    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        with registry._lock:
            active = bool(registry._processes)
        if active:
            break
        time.sleep(0.01)
    if not active:
        llm_drivers.shutdown_active_cli_runs()
        worker.join(timeout=3)
        raise AssertionError("_run_cli did not register its child process")

    llm_drivers.shutdown_active_cli_runs()
    worker.join(timeout=3)

    assert not worker.is_alive()
    assert result["run"][0] != 0
    rc, _, _, _, error = llm_drivers._run_cli(
        [sys.executable, "-c", "pass"], timeout=1)
    assert rc == -4
    assert error == "service shutting down"


def test_scan_stops_before_debating_next_item(monkeypatch):
    stop_event = threading.Event()
    debated = []
    monkeypatch.setattr(debater, "recover_orphaned_debates", lambda: None)
    monkeypatch.setattr(debater, "scan_pending", lambda: ["first", "second"])
    monkeypatch.setattr(debater.store, "update_state", lambda *args, **kwargs: None)

    def debate_one(news_id, verbose=False):
        debated.append(news_id)
        stop_event.set()
        return {"ok": True, "state": "closed"}

    monkeypatch.setattr(debater, "debate_item", debate_one)
    result = debater.scan_and_debate(stop_event=stop_event)

    assert debated == ["first"]
    assert result["items_processed"] == 1
    assert result["stopped"] is True

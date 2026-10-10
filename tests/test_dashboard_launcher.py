"""Exercise the real socket receiver/exec under a launchd-like empty env."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import dashboard_launcher as launcher


def test_launchd_receives_environment_without_argv_or_secret_file(monkeypatch, tmp_path):
    children, calls, handoffs = [], [], []
    secret = "test-only-socket-value"
    env = {"FMP_API_KEY": secret, "FINNHUB_API_KEY": "test-finnhub",
           "FRED_API_KEY": "test-fred", "ALPACA_API_KEY": "test-alpaca",
           "ALPACA_SECRET_KEY": "test-alpaca-secret", "DASHBOARD_PORT": "8099"}
    # This is a synthetic secret, never the operator's actual environment.
    command = [sys.executable, "-c", "import os,json; print(json.dumps(dict(os.environ)))"]

    def launchctl(argv, **kw):
        calls.append(argv)
        assert secret not in " ".join(argv)
        assert argv[:2] == ["launchctl", "submit"]
        child_argv = argv[argv.index("--") + 1:]
        socket_path = Path(child_argv[child_argv.index("--receive-env") + 1])
        handoffs.append(socket_path)
        assert socket_path.parent.stat().st_mode & 0o777 == 0o700
        assert socket_path.stat().st_mode & 0o777 == 0o600
        assert list(socket_path.parent.iterdir()) == [socket_path]
        children.append(subprocess.Popen(child_argv, env={"PATH": os.defpath},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(launcher.subprocess, "run", launchctl)
    launcher.submit("test.job", tmp_path / "server.log", env, command)
    stdout, stderr = children[0].communicate(timeout=5)
    assert children[0].returncode == 0, stderr
    received = json.loads(stdout)
    for key, value in env.items():
        assert received[key] == value
    assert len(calls) == 1
    assert all(not p.parent.exists() for p in handoffs)


def test_missing_main_feed_is_rejected_before_submit(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(launcher.subprocess, "run", lambda *a, **k: calls.append(a))
    with pytest.raises(RuntimeError, match="FMP_API_KEY missing"):
        launcher.submit("test.job", tmp_path / "server.log", {}, [sys.executable])
    assert calls == []
    script = (ROOT / "scripts/restart_dashboard.sh").read_text()
    assert script.index("dashboard_launcher.py --check-env") < script.index('launchctl remove "$LABEL"')
    assert "dashboard_launcher.py --label" in script
    pid_queries = [line for line in script.splitlines() if "$(lsof " in line]
    assert len(pid_queries) == 3
    assert all('-iTCP:"$PORT" -sTCP:LISTEN' in line for line in pid_queries)


def test_handoff_timeout_removes_job_and_socket(monkeypatch, tmp_path):
    calls, socket_paths = [], []
    def launchctl(argv, **kw):
        calls.append(argv)
        if "--receive-env" in argv:
            socket_paths.append(Path(argv[argv.index("--receive-env") + 1]))
        return subprocess.CompletedProcess(argv, 0)
    monkeypatch.setattr(launcher, "TIMEOUT", 0.05)
    monkeypatch.setattr(launcher.subprocess, "run", launchctl)
    with pytest.raises(RuntimeError, match="handoff failed"):
        launcher.submit("test.job", tmp_path / "server.log", {"FMP_API_KEY": "test-only"}, [sys.executable])
    assert calls[-1] == ["launchctl", "remove", "test.job"]
    assert all(not p.parent.exists() for p in socket_paths)

import json
from pathlib import Path

from scripts._shared import fmp_pool


class FakeResponse:
    status_code = 429
    text = ""

    def __init__(self, body, retry_after="7"):
        self._body = body
        self.headers = {"Retry-After": retry_after}

    def json(self):
        return self._body


def test_429_artifact_is_safe_and_retry_after_is_honored(monkeypatch, tmp_path):
    artifact = tmp_path / "last_429.json"
    sleeps = []
    monkeypatch.setattr(fmp_pool, "_LAST_429_PATH", artifact)
    monkeypatch.setattr(fmp_pool, "acquire_slot", lambda block=True: True)
    monkeypatch.setattr(fmp_pool.requests, "get", lambda *a, **k: FakeResponse({
        "Error Message": "Limit Reach",
        "apikey": "secret-test-key",
    }))
    monkeypatch.setattr(fmp_pool.time, "sleep", sleeps.append)
    monkeypatch.setenv("FMP_API_KEY", "secret-test-key")

    data, status = fmp_pool._request(
        "https://financialmodelingprep.com/stable/profile?apikey=secret-test-key",
        {},
        retries=0,
        timeout=1,
    )

    assert data is None
    assert status == 429
    assert sleeps == [7.0]
    saved = json.loads(artifact.read_text())
    assert saved["retry_after"] == "7"
    assert saved["endpoint"] == "https://financialmodelingprep.com/stable/profile"
    assert "secret-test-key" not in artifact.read_text()
    assert "[REDACTED]" in saved["response_body"]

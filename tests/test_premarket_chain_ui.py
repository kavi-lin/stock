"""Static contract for the compact pre-market three-phase stepper."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "Dashboard/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "Dashboard/style.css").read_text(encoding="utf-8")
JS = (ROOT / "Dashboard/script.js").read_text(encoding="utf-8")
UTILS = (ROOT / "Dashboard/utils.js").read_text(encoding="utf-8")


def test_chain_is_one_connected_three_phase_stepper():
    assert 'id="preflight-chain"' in HTML
    assert [HTML.index(f'id="preflight-phase-{n}"') for n in (1, 2, 3)] == sorted(
        HTML.index(f'id="preflight-phase-{n}"') for n in (1, 2, 3)
    )
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in CSS
    assert ".preflight-phase:not(:last-child)::after" in CSS


def test_dialog_is_viewport_bounded_and_mobile_safe():
    assert "max-height: calc(100dvh - 24px)" in CSS
    assert "max-height: calc(100dvh - 132px)" in CSS
    assert "@media (max-width: 640px)" in CSS
    assert 'class="preflight-dialog ' in HTML


def test_runtime_drives_phase_and_row_states():
    for state in ("active", "complete", "error", "waiting"):
        assert f"is-{state}" in JS
    assert JS.count("_setPhaseState(") >= 9
    assert "_setPhaseState(3, 'complete')" in JS
    assert "preflight-run-free')?.classList.add('hidden')" in JS
    assert "preflight-run-all')?.classList.add('hidden')" in JS


def test_protocol_pill_keeps_retry_and_terminal_failure_visible():
    assert "broker 暫時無回應，自動重試" in UTILS
    assert "recentFailures.length === 0" in UTILS
    assert ".proto-pill-failure-row" in CSS


def test_cross_page_premarket_status_is_integrated_into_protocol_queue():
    assert "chain-status-pill" not in UTILS
    assert ".chain-status-pill" not in CSS
    assert "run?.source !== 'premarket_chain'" in UTILS
    assert "news: 'News Digest'" in UTILS
    assert "sector: 'Sector Scan'" in UTILS
    assert "daily: '" not in UTILS
    assert "daily_update remains visible in the pre-market modal" in UTILS

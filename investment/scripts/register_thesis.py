#!/usr/bin/env python3
"""
Phase 5.5 — register one investment_protocol session into trader-memory-core,
then back-fill `thesis_id` + `thesis_registered_at` into that same JSON object.

Wires investment_protocol V5 output into the cross-session thesis lifecycle
(IDEA → ENTRY_READY → ACTIVE → CLOSED). Read-only on theses state if final_decision
is HOLD/CANCEL (we still register so the analysis is recoverable for postmortem).

Invocation (from protocol Phase 5.5):
    python3 investment/scripts/register_thesis.py --session <SESSION.json>
        rc=0  → registered (or gracefully skipped — see stdout)
        rc=1  → trader-memory-core unavailable / state corrupt

Idempotent: if the selected entry already has non-null thesis_id, exits 0 without re-register.
"""
import json
import os
import sys
import argparse
import fcntl
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT         = Path(__file__).resolve().parents[2]
STATE_DIR    = ROOT / "investment" / "invest_logs" / "theses"
EARNINGS_CACHE_DIR = ROOT / "skills" / "earnings-analyst" / "cache"

TMC_SCRIPTS = Path.home() / ".claude" / "skills" / "trader-memory-core" / "scripts"
sys.path.insert(0, str(TMC_SCRIPTS))


def _read_structural_shift(ticker: str) -> dict | None:
    """Pick the freshest earnings-analyst cache for ticker and return its
    structural_shift block (V2.18.0). Returns None if cache missing/malformed."""
    if not EARNINGS_CACHE_DIR.exists():
        return None
    files = sorted(
        p for p in EARNINGS_CACHE_DIR.glob(f"{ticker}_*.json")
        if ".infographic." not in p.name
    )
    if not files:
        return None
    try:
        with files[-1].open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        return data.get("structural_shift")
    except Exception:
        return None


def _load_payload(path: Path):
    if not path.exists():
        print(f"[register_thesis] session not found: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _entry_from_payload(payload):
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list) and payload:
        return payload[-1]
    print("[register_thesis] session must be an object or non-empty history array",
          file=sys.stderr)
    sys.exit(1)


def _atomic_write(path: Path, payload) -> None:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False,
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp",
    )
    try:
        json.dump(payload, tmp, indent=2, ensure_ascii=False)
        tmp.write("\n")
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, path)
    except Exception:
        try:
            tmp.close()
        except Exception:
            pass
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


def _build_thesis_data(entry):
    """Convert the selected session entry → thesis_data for register()."""
    trade = (entry.get("trades_this_session") or [{}])[0]
    ticker = trade.get("ticker") or entry.get("ticker") or "UNKNOWN"
    fvs = trade.get("fair_value_summary") or {}
    return {
        "ticker": ticker,
        "source": "investment_protocol_v5",
        "_register_reason": f"Phase 5 export — {trade.get('final_decision','?')} ({trade.get('final_score','?')})",
        "thesis_oneliner": (trade.get("macro_context") or "")[:200] or f"{ticker} V5 protocol output",
        "fair_value": fvs.get("weighted_fair_value"),
        "current_price": fvs.get("current_price") or trade.get("analysis_price"),
        "confidence": fvs.get("confidence"),
        "verdict_band": fvs.get("verdict_band"),
        "final_decision": trade.get("final_decision"),
        "final_score": trade.get("final_score"),
        "position_size_pct": trade.get("position_size_pct"),
        "kill_conditions": trade.get("red_team_kill_conditions") or [],
        "key_risks": trade.get("key_risks") or [],
        "watch_conditions": trade.get("watch_conditions") or {},
        "export_date": entry.get("export_date"),
        "structural_shift": _read_structural_shift(ticker),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Register one investment session thesis")
    ap.add_argument("--session", required=True,
                    help="isolated session object (legacy history arrays are read-compatible)")
    args = ap.parse_args(argv)
    session_path = Path(args.session)
    payload = _load_payload(session_path)
    entry = _entry_from_payload(payload)
    trade = (entry.get("trades_this_session") or [{}])[0]

    # Idempotent guard
    if trade.get("thesis_id"):
        print(f"[register_thesis] already registered: thesis_id={trade['thesis_id']}")
        sys.exit(0)

    try:
        import thesis_store  # noqa: E402
    except Exception as e:
        print(f"[register_thesis] trader-memory-core unavailable ({e}). Skipping register, "
              "thesis_id stays null. Phase 5.5 is non-fatal.", file=sys.stderr)
        sys.exit(0)

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    thesis_data = _build_thesis_data(entry)
    lock_fp = (STATE_DIR / ".register.lock").open("a+", encoding="utf-8")
    try:
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX)
        thesis_id = thesis_store.register(str(STATE_DIR), thesis_data)
    except Exception as e:
        print(f"[register_thesis] thesis_store.register failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            fcntl.flock(lock_fp.fileno(), fcntl.LOCK_UN)
        finally:
            lock_fp.close()

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    trade["thesis_id"] = thesis_id
    trade["thesis_registered_at"] = now_iso

    try:
        _atomic_write(session_path, payload)
    except OSError as e:
        print(f"[register_thesis] session write failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[register_thesis] ✓ registered {thesis_data['ticker']} → thesis_id={thesis_id} "
          f"(state: {STATE_DIR.relative_to(ROOT)})")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Append a Phase 5 session export entry to `investment/invest_logs/history.json`.

Replaces the legacy pattern of having the PM hand-write the full JSON block
inside the protocol prompt — which was high-output-token, error-prone (malformed
JSON forces a Sonnet retry), and tangled append + validate into one prompt step.

Now Phase 5 Step 1 calls this script with the entry JSON, and the script:
  1. Reads stdin / --from-file / --from-arg
  2. Validates basic top-level shape (full schema check is `validate_session_export.py`)
  3. Acquires an exclusive flock on history.json
  4. Atomic write: tmp file + rename
  5. Mirrors top-level `ticker` / `final_action` / `export_date` to entry root if missing

Invocation:
    cat new_entry.json | python3 investment/scripts/append_session_export.py
    python3 investment/scripts/append_session_export.py --from-file path/to/entry.json
    python3 investment/scripts/append_session_export.py --from-arg '<json>'

Return codes:
    0 — appended successfully
    1 — schema error (malformed JSON, missing required top-level keys)
    2 — IO error (history.json unreadable / unwritable / lock failure)

Idempotency: this script does NOT dedupe — protocol must call it exactly once
per session. `register_thesis.py` runs AFTER this and back-fills `thesis_id` on
the same (last) entry.

Fixing a session you already appended: `--replace-last`. It exists because the
alternative is what actually happened on 2026-08-09 — a run whose validator went
red popped the entry off with an ad-hoc `json.dump` over the whole file, and
another edited fields in place. Re-appending instead would leave two entries for
one session (history already carries five such pairs). `--replace-last` is the
same operation under the same lock, refusing to touch an entry that is not the
same (ticker, export_date).

Race safety: `fcntl.flock(LOCK_EX)` held for the full read-modify-write window;
parallel callers serialize. Atomic rename ensures readers never see a half-write.

V4.117.0 — this script also stamps `export_provenance`, which is what makes it
the *only* sanctioned writer rather than merely the recommended one. See
`entry_digest()` for why the stamp is a content digest and not just a marker.
"""
import argparse
import fcntl
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT         = Path(__file__).resolve().parents[2]
HISTORY_JSON = ROOT / "investment" / "invest_logs" / "history.json"

PROVENANCE_SCHEMA = "export_provenance.v1"

#: Keys the sanctioned post-append tools own. The digest must ignore them, or
#: the approved chain would invalidate its own stamp one step after writing it:
#:   append_session_export.py → apply_det_shadow.py --inplace → register_thesis.py
#: Anything NOT listed here is decision content and freezes at append time.
DIGEST_SKIP_ENTRY_KEYS = frozenset({"export_provenance"})
DIGEST_SKIP_TRADE_KEYS = frozenset({
    "det_shadow",            # apply_det_shadow.py
    "lane_contract",         # apply_det_shadow.py (V5.3+)
    "thesis_id",             # register_thesis.py
    "thesis_registered_at",  # register_thesis.py
})


def _strip_for_digest(entry: dict) -> dict:
    """Entry reduced to the fields whose value is a decision, not a derivation.

    Underscore-prefixed trade keys are dropped wholesale: `_as_of_date_inherited`
    is written by `apply_det_shadow.apply_to_session_export` on every `--inplace`
    pass, and the leading underscore is this repo's existing marker for
    post-processor scratch. Naming them one by one would make the digest brittle
    against the next such field.
    """
    out = {k: v for k, v in entry.items() if k not in DIGEST_SKIP_ENTRY_KEYS}
    trades = out.get("trades_this_session")
    if isinstance(trades, list):
        out["trades_this_session"] = [
            {k: v for k, v in t.items()
             if k not in DIGEST_SKIP_TRADE_KEYS and not k.startswith("_")}
            if isinstance(t, dict) else t
            for t in trades
        ]
    return out


def entry_digest(entry: dict) -> str:
    """sha256 over the entry's decision content, canonically serialised.

    A bare "written by me" marker would be satisfied by anyone who types the
    marker, and the failure this closes is not someone forging a stamp — it is
    2026-08-09, where a run hand-edited `final_score` and the whole
    `calculation_steps` block into history.json *after* a clean append, and
    another popped entries off the list with an ad-hoc `json.dump`. A digest
    catches both: the first because the content moved away from what was
    stamped, the second because a hand-written entry carries no stamp at all.

    Canonical form is `sort_keys` + tight separators, so re-serialisation by
    `apply_det_shadow` / `register_thesis` (different indent, same data) does not
    move the hash.
    """
    canonical = json.dumps(_strip_for_digest(entry), sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _repo_version() -> str:
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip() or "unknown"
    except OSError:
        return "unknown"


def _stamp_provenance(entry: dict) -> None:
    entry["export_provenance"] = {
        "schema": PROVENANCE_SCHEMA,
        "writer": f"append_session_export.py (V{_repo_version()})",
        "appended_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entry_digest": entry_digest(entry),
    }

# Minimal top-level shape gate — full schema enforcement is delegated to
# `validate_session_export.py`, which the protocol runs in Phase 5 Step 2.
TOP_REQUIRED_MIN = (
    "session_export_version", "export_date", "ticker", "final_action",
    "trades_this_session",
)


def _err(msg: str, rc: int = 1) -> None:
    print(f"[append_session_export] ✗ {msg}", file=sys.stderr)
    sys.exit(rc)


def _read_input(args) -> str:
    if args.from_file:
        try:
            return Path(args.from_file).read_text(encoding="utf-8")
        except OSError as e:
            _err(f"--from-file unreadable: {e}", rc=2)
    if args.from_arg:
        return args.from_arg
    if sys.stdin.isatty():
        _err("no input — pipe JSON via stdin, --from-file PATH, or --from-arg '<json>'")
    return sys.stdin.read()


def _parse_entry(raw: str) -> dict:
    raw = raw.strip()
    if not raw:
        _err("empty input")
    try:
        entry = json.loads(raw)
    except json.JSONDecodeError as e:
        _err(f"malformed JSON: {e}")
    if not isinstance(entry, dict):
        _err(f"top-level must be object, got {type(entry).__name__}")
    return entry


def _check_min_shape(entry: dict) -> None:
    missing = [k for k in TOP_REQUIRED_MIN if k not in entry]
    if missing:
        _err(f"missing required top-level keys: {missing}")
    trades = entry.get("trades_this_session")
    if not isinstance(trades, list) or not trades:
        _err("trades_this_session must be a non-empty array")
    if not isinstance(trades[0], dict):
        _err("trades_this_session[0] must be an object")


def _mirror_top_level(entry: dict) -> None:
    """Phase 5 schema requires top-level ticker / final_action / export_date to
    mirror trades_this_session[0]. Fill if missing; cross-check if present."""
    trade0 = entry["trades_this_session"][0]
    for k in ("ticker", "final_action"):
        if k not in entry and k in trade0:
            entry[k] = trade0[k]
    # `date` is a legacy alias for export_date — keep both filled
    if "date" not in entry and "export_date" in entry:
        entry["date"] = entry["export_date"]


def _same_session(a: dict, b: dict) -> bool:
    """Two entries describe the same session: same ticker, same export date."""
    def key(e):
        t = (e.get("trades_this_session") or [{}])[0]
        return (str(t.get("ticker") or e.get("ticker") or "").upper(),
                str(e.get("export_date") or e.get("date") or ""))
    ka, kb = key(a), key(b)
    return all(ka) and ka == kb


def _atomic_append(entry: dict, history_path: Path | None = None,
                   replace_last: bool = False) -> int:
    target = history_path or HISTORY_JSON
    if not target.exists():
        _err(f"history.json not found at {target}", rc=2)

    # Open for read+write, hold exclusive lock for the whole RMW window so
    # concurrent appends serialize and register_thesis.py never reads a
    # half-written file.
    try:
        fp = target.open("r+", encoding="utf-8")
    except OSError as e:
        _err(f"history.json unreadable: {e}", rc=2)
    try:
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
        try:
            existing = json.load(fp)
        except json.JSONDecodeError as e:
            _err(f"history.json is malformed JSON: {e}", rc=2)
        if not isinstance(existing, list):
            _err("history.json must be a JSON array", rc=2)
        if replace_last:
            # Guarded so a --replace-last on the wrong turn cannot eat a
            # different session's record: the entry being dropped has to be the
            # same (ticker, export_date) as the one coming in.
            if not existing:
                _err("--replace-last on an empty history.json — nothing to replace")
            if not _same_session(existing[-1], entry):
                last = existing[-1]
                _err(
                    f"--replace-last refused: last entry is "
                    f"{last.get('ticker')} / {last.get('export_date')} but the "
                    f"incoming entry is {entry.get('ticker')} / "
                    f"{entry.get('export_date')}. 只能取代同一 session 自己寫的那筆")
            existing[-1] = entry
        else:
            existing.append(entry)

        # Atomic write via tempfile in the same directory + rename.
        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False,
            dir=str(target.parent), prefix=".history.", suffix=".tmp",
        )
        try:
            json.dump(existing, tmp, indent=2, ensure_ascii=False)
            tmp.write("\n")
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, target)
        except OSError as e:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            _err(f"atomic write failed: {e}", rc=2)
        return len(existing)
    finally:
        try:
            fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
        finally:
            fp.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Append Phase 5 session export entry")
    ap.add_argument("--from-file", type=str, help="Read entry JSON from this file")
    ap.add_argument("--from-arg",  type=str, help="Read entry JSON from this argument")
    # Exists so the gate contract can drive this script rather than restate what
    # it does; it changes the destination, never whether the stamp is applied.
    ap.add_argument("--history", type=str, default=None,
                    help="history JSON path (default: investment/invest_logs/history.json)")
    ap.add_argument("--replace-last", action="store_true",
                    help="replace the last entry instead of appending — for fixing "
                         "a session you already appended (same ticker + export_date only)")
    args = ap.parse_args()

    entry = _parse_entry(_read_input(args))
    _check_min_shape(entry)
    _mirror_top_level(entry)
    # After the mirror, so the stamped digest covers the entry as it lands on
    # disk rather than as it arrived.
    _stamp_provenance(entry)

    new_len = _atomic_append(entry, Path(args.history) if args.history else None,
                             replace_last=args.replace_last)
    trade0 = entry["trades_this_session"][0]
    verb = "replaced last" if args.replace_last else "appended"
    print(
        f"[append_session_export] ✓ {verb} — "
        f"{trade0.get('ticker','?')} / {trade0.get('final_decision','?')} / "
        f"{entry.get('final_action','?')} (history len={new_len})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

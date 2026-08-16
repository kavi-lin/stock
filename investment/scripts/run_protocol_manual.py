#!/usr/bin/env python3
"""Run one agentic protocol on a chosen provider, outside the allowlist.

    python3 investment/scripts/run_protocol_manual.py gemini invest NOW
    python3 investment/scripts/run_protocol_manual.py codex  invest PLTR

This exists to answer one question that nothing else can: **can provider X
actually execute protocol Y?** `config/llm_config.json` forbids gemini for
`invest` precisely because that is unproven, so the only way to gather the
evidence is a deliberate run outside the gate.

Everything about the launch is taken from `dashboard_server` rather than
restated — the prompt through `_adapt_protocol_prompt`, the argv through
`_protocol_command`, the deadline through `PROTOCOL_TIMEOUT_OVERRIDES`. A copy
would drift, and then the experiment would be measuring the copy.

What it deliberately does NOT reproduce
---------------------------------------
The quota-broker reservation. This run is ungoverned and its tokens settle
against nothing. Acceptable for a one-off probe, stated here so it is not
discovered later from a budget that does not add up.

Safety
------
* an atomic lock, so two manual runs cannot interleave on `history.json`;
* per-run log / backup / job id, because the previous version of this tool used
  fixed names — a second run overwrote the clean backup with the already-
  contaminated file, i.e. the safety net destroyed itself on its second use;
* a post-run gate: if the validator fails, the report is **quarantined** by
  rename so it cannot enter the decision calendar (`build_event_index` matches
  `^\\d{8}_[A-Z][A-Z0-9]+\\.md$`).

Quarantine rather than rollback is deliberate. A validator can fail for reasons
unrelated to the run's quality, and restoring `history.json` automatically would
destroy a legitimate session irreversibly. Renaming a file is reversible; the
restore command is printed for the operator to run if they want it.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
# `dashboard_server` parses sys.argv at import. Stash ours first, hand it a bare
# argv, and restore — otherwise this tool's own arguments reach the server's
# parser and its own parser sees none.
_ARGV = sys.argv[1:]
sys.argv = ["dashboard_server.py"]
import dashboard_server as ds               # noqa: E402
sys.argv = ["run_protocol_manual.py", *_ARGV]

HISTORY = os.path.join(ROOT, "investment/invest_logs/history.json")
LOCK_DIR = os.path.join(ROOT, "investment/invest_logs/.manual_protocol.lock")
RUN_DIR = os.path.join(ROOT, "investment/scan_logs")
#: Same pattern `scripts/build_event_index.py` uses to pick up deep-dive reports.
DEEP_DIVE_RE = re.compile(r"^\d{8}_[A-Z][A-Z0-9]+\.md$")
#: Trees whose .py files a protocol run must never write to. Not a security
#: boundary — it is the control that makes a passing validator mean something.
WATCH = ("investment/scripts", "skills", "scripts")


def _py_snapshot() -> dict[str, str]:
    """sha256 of every .py under WATCH, so a run can be asked what it edited.

    This is the check the 2026-08-16 agy trials turned on. The first run passed
    `validate_session_export.py` cleanly — but only after the agent had edited
    `build_session_export.py` to accept its own malformed p3 shape, which makes
    that green worth nothing. Content hashes rather than mtimes: an edit that is
    written back byte-identical is not an edit, and a `touch` is not either.
    """
    snap = {}
    for tree in WATCH:
        for dirpath, _, filenames in os.walk(os.path.join(ROOT, tree)):
            if "__pycache__" in dirpath:
                continue
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "rb") as fp:
                        snap[os.path.relpath(path, ROOT)] = hashlib.sha256(fp.read()).hexdigest()
                except OSError:
                    continue
    return snap


def _context_ids(log_path: str) -> set[str]:
    """Distinct conversation ids in the log = how many contexts really ran.

    Count these, NOT `invoke_subagent` calls: agy batch-dispatches, so one call
    can carry five subagents. Counting calls on 2026-08-16 gave 2 and the wrong
    conclusion that the 5-lane fan-out had collapsed; the log held 7 ids.
    """
    ids, pat = set(), re.compile(r'"conversation_id"\s*:\s*"([0-9a-f-]{36})"')
    try:
        with open(log_path, encoding="utf-8", errors="replace") as fp:
            for line in fp:
                ids.update(pat.findall(line))
    except OSError:
        pass
    return ids


def acquire_lock():
    """`mkdir` is atomic on POSIX; `open(O_CREAT|O_EXCL)` would do as well.

    Only protects manual run vs manual run. `dashboard_server` holds an
    in-process lock and does not take this one, so the queue check below stays
    as the best available signal about the server — a check, not a lock, and
    labelled as such rather than implied to be more.
    """
    try:
        os.mkdir(LOCK_DIR)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
        held = "unknown"
        try:
            with open(os.path.join(LOCK_DIR, "owner")) as fp:
                held = fp.read().strip()
        except OSError:
            pass
        sys.exit(f"✗ another manual run holds the lock ({held}).\n"
                 f"  If you are certain none is running: rm -rf {LOCK_DIR}")
    with open(os.path.join(LOCK_DIR, "owner"), "w") as fp:
        fp.write(f"pid={os.getpid()} started={datetime.now().isoformat(timespec='seconds')}\n")


def release_lock():
    shutil.rmtree(LOCK_DIR, ignore_errors=True)


def server_busy():
    """True when the dashboard is mid-protocol. Best effort; see `acquire_lock`."""
    try:
        import urllib.request
        with urllib.request.urlopen(
                "http://127.0.0.1:8080/api/analyze-queue", timeout=3) as resp:
            state = json.load(resp)
        return bool(state.get("active")) or bool(state.get("queue"))
    except Exception:
        return False                        # not reachable → no contention


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("provider", choices=sorted(ds.PROVIDER_CONTEXT_FILE))
    ap.add_argument("protocol", choices=sorted(ds.PROTOCOL_PROMPTS))
    ap.add_argument("ticker", nargs="?", help="required by ticker-scoped protocols")
    ap.add_argument("--risk-tolerance", default="MEDIUM",
                    choices=("LOW", "MEDIUM", "HIGH"))
    ap.add_argument("--yes", action="store_true",
                    help="skip the confirmation prompt")
    args = ap.parse_args(argv)

    template = ds.PROTOCOL_PROMPTS[args.protocol]
    if "{ticker}" in template and not args.ticker:
        ap.error(f"protocol '{args.protocol}' needs a ticker")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = f"{args.protocol}_manual_{args.provider}" + (
        f"_{args.ticker.upper()}" if args.ticker else "")
    job_id = f"{tag}_{stamp}"
    log_path = os.path.join(RUN_DIR, f"{job_id}.log")
    backup = os.path.join(RUN_DIR, f"history.{job_id}.bak.json")
    os.makedirs(RUN_DIR, exist_ok=True)

    prompt = template
    for key, value in (("ticker", (args.ticker or "").upper()),
                       ("risk_tolerance", args.risk_tolerance)):
        prompt = prompt.replace("{" + key + "}", value)
    prompt = ds._adapt_protocol_prompt(args.provider, prompt, args.protocol)

    timeout = ds.PROTOCOL_TIMEOUT_OVERRIDES.get(args.protocol, ds.PROTOCOL_TIMEOUT_SEC)
    claude_model = (ds._protocol_model_for(args.protocol)
                    if args.provider == "claude" else None)
    cmd = ds._protocol_command(args.provider, prompt,
                               claude_model=claude_model, timeout_sec=timeout)

    print(f"▶ {job_id}")
    print(f"  provider={args.provider}  protocol={args.protocol}"
          f"  ticker={args.ticker or '—'}  timeout={timeout}s")
    print(f"  log    : {os.path.relpath(log_path, ROOT)}")
    print(f"  ⚠ writes to the REAL history.json; this run is NOT quota-governed")
    if server_busy():
        sys.exit("✗ the dashboard is running a protocol — wait for it to finish")
    if not args.yes:
        try:
            if input("  continue? [y/N] ").strip().lower() not in ("y", "yes"):
                sys.exit("aborted")
        except EOFError:
            sys.exit("aborted (no tty; pass --yes)")

    acquire_lock()
    rc = -1
    before = _py_snapshot()
    print(f"  baseline: {len(before)} .py hashed under {', '.join(WATCH)}")
    started = datetime.now()
    try:
        if os.path.exists(HISTORY):
            shutil.copy2(HISTORY, backup)
            print(f"  backup : {os.path.relpath(backup, ROOT)}")
        env = {
            **os.environ,
            "PATH": os.environ.get("PATH", "") + ":/Users/kavi/.local/bin",
            "NEWS_RUN_START_MS": str(int(started.timestamp() * 1000)),
            "AIC_PROTOCOL_MODEL": args.provider,
            "AIC_PROTOCOL_MODEL_TIER": claude_model or "cli-default",
            "AIC_PROTOCOL_NAME": args.protocol,
            "AIC_PROTOCOL_JOB_ID": job_id,
        }
        with open(log_path, "w", buffering=1, encoding="utf-8") as log:
            log.write(f"=== protocol={args.protocol} "
                      f"model={args.provider}:{claude_model or 'cli-default'} "
                      f"prompt={prompt!r} started={started.isoformat(timespec='seconds')} "
                      f"manual=1 ===\n")
            proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True,
                                    bufsize=1, env=env)
            beat = time.time()
            try:
                for line in iter(proc.stdout.readline, ""):
                    if not line:
                        break
                    log.write(line)
                    if time.time() - beat > 60:
                        mins = int((datetime.now() - started).total_seconds() // 60)
                        print(f"  … {mins}m, log {os.path.getsize(log_path) // 1024}KB")
                        beat = time.time()
                rc = proc.wait(timeout=60)
            except KeyboardInterrupt:
                proc.kill()
                log.write("\n[interrupted by operator]\n")
                rc = -2
            log.write(f"\n=== ended={datetime.now().isoformat(timespec='seconds')} "
                      f"rc={rc} ===\n")
    finally:
        release_lock()

    elapsed = int((datetime.now() - started).total_seconds())
    print(f"\n■ rc={rc}  elapsed={elapsed}s ({elapsed // 60}m)")

    # ── evidence the validator cannot give you ───────────────────────────────
    # Both of these outrank rc and the validator when judging "can provider X
    # drive protocol Y". A run that edited the machinery to get green proves
    # nothing, and a run that collapsed the fan-out is not the protocol.
    after = _py_snapshot()
    touched = sorted(set(before) ^ set(after)) + sorted(
        p for p in before.keys() & after.keys() if before[p] != after[p])
    if touched:
        print(f"  ✗ protocol code touched: {len(touched)} file(s) — this run proves nothing")
        for p in touched:
            print(f"      {p}")
    else:
        print(f"  ✓ protocol code untouched ({len(before)} .py byte-identical)")
    ids = _context_ids(log_path)
    if ids:
        print(f"  contexts: {len(ids)} (1 coordinator + subagents; count ids, not invoke calls)")

    # ── post-run gate ────────────────────────────────────────────────────────
    validator = ds.PROTOCOL_VALIDATORS.get(args.protocol)
    v_rc = None
    if validator:
        result = subprocess.run(
            [sys.executable, *[os.path.join(ROOT, p) for p in validator]],
            cwd=ROOT, capture_output=True, text=True)
        v_rc = result.returncode
        print(f"\nvalidator rc={v_rc}")
        for line in (result.stdout or result.stderr).strip().splitlines()[:10]:
            print(f"  | {line}")

    report = None
    if args.ticker:
        candidate = os.path.join(
            ROOT, "reports", f"{started.strftime('%Y%m%d')}_{args.ticker.upper()}.md")
        if os.path.exists(candidate) and os.path.getmtime(candidate) >= started.timestamp():
            report = candidate

    if (rc != 0 or (v_rc not in (None, 0))) and report:
        # Quarantine, not rollback. The rename takes the report out of
        # `build_event_index`'s pattern so a failed run cannot become a sample in
        # the decision calendar, while leaving every byte on disk for diagnosis.
        quarantined = report.replace(".md", "_EXPERIMENT.md")
        os.rename(report, quarantined)
        print(f"\n⚠ 隔離：{os.path.relpath(report, ROOT)} → "
              f"{os.path.basename(quarantined)}")
        print("  （檔名不再符合 deep-dive pattern，不會進決策日曆；內容原封不動）")
    elif report:
        print(f"\n報告：{os.path.relpath(report, ROOT)}"
              + ("" if DEEP_DIVE_RE.match(os.path.basename(report))
                 else "  (不符 deep-dive pattern，不會進決策日曆)"))
    elif args.ticker:
        print("\n⚠ 沒有產出本次的報告檔")

    if os.path.exists(backup):
        print(f"\n要回退決策日曆：cp '{os.path.relpath(backup, ROOT)}' "
              f"'{os.path.relpath(HISTORY, ROOT)}'")
    print(f"log：{os.path.relpath(log_path, ROOT)}")
    return 0 if (rc == 0 and v_rc in (None, 0)) else 1


if __name__ == "__main__":
    raise SystemExit(main())

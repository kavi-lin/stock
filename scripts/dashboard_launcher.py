#!/usr/bin/env python3
"""Transfer the caller's environment to a launchd job without storing secrets.

launchctl submit inherits launchd's environment, not the invoking shell's.
A private, one-shot Unix socket carries the environment in memory. The job's
argv contains only the socket path and program paths, never credential values.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 20
MAX_ENV_BYTES = 1024 * 1024
DATA_KEYS = ("FMP_API_KEY", "FINNHUB_API_KEY", "FRED_API_KEY",
             "ALPACA_API_KEY", "ALPACA_SECRET_KEY")


def check_environment(env):
    """Fail before stopping a working server when its main feed would be lost."""
    if not env.get("FMP_API_KEY"):
        raise RuntimeError("FMP_API_KEY missing in calling environment; existing server left running")
    missing = [key for key in DATA_KEYS if not env.get(key)]
    if missing:
        print("Optional data credentials missing: " + ", ".join(missing), file=sys.stderr)


def receive_exact(conn, size):
    chunks = bytearray()
    while len(chunks) < size:
        part = conn.recv(size - len(chunks))
        if not part:
            raise RuntimeError("environment handoff closed early")
        chunks.extend(part)
    return bytes(chunks)


def receive_and_exec(path, command):
    if not command:
        raise RuntimeError("missing Dashboard command")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(TIMEOUT)
        conn.connect(path)
        size = struct.unpack("!I", receive_exact(conn, 4))[0]
        if not 0 < size <= MAX_ENV_BYTES:
            raise RuntimeError("invalid environment handoff size")
        env = json.loads(receive_exact(conn, size))
        if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                               for k, v in env.items()):
            raise RuntimeError("invalid environment handoff shape")
        conn.sendall(b"OK")
    os.chdir(ROOT)
    os.execvpe(command[0], command, env)


def submit(label, log, env, command):
    check_environment(env)
    payload = json.dumps(dict(env)).encode()
    if len(payload) > MAX_ENV_BYTES:
        raise RuntimeError("calling environment too large")
    (ROOT / "tmp").mkdir(exist_ok=True)
    Path(log).parent.mkdir(parents=True, exist_ok=True)
    # mkdtemp uses 0700. The only filesystem object inside it is a socket,
    # removed on success/failure; no environment JSON file is ever created.
    with tempfile.TemporaryDirectory(prefix=".dash-env-", dir=ROOT / "tmp") as directory:
        path = str(Path(directory) / "s")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(path)
            os.chmod(path, 0o600)
            listener.listen(1)
            listener.settimeout(TIMEOUT)
            argv = ["launchctl", "submit", "-l", label, "-o", str(log), "-e", str(log),
                    "--", sys.executable, str(Path(__file__).resolve()),
                    "--receive-env", path, "--", *command]
            try:
                subprocess.run(argv, check=True, capture_output=True, timeout=TIMEOUT)
                conn, _ = listener.accept()
                with conn:
                    conn.settimeout(TIMEOUT)
                    conn.sendall(struct.pack("!I", len(payload)) + payload)
                    if receive_exact(conn, 2) != b"OK":
                        raise RuntimeError("environment handoff not acknowledged")
            except Exception:
                subprocess.run(["launchctl", "remove", label], capture_output=True, timeout=TIMEOUT)
                raise RuntimeError("Dashboard environment handoff failed; submitted job removed") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-env", action="store_true")
    parser.add_argument("--receive-env")
    parser.add_argument("--label")
    parser.add_argument("--log")
    parser.add_argument("--port", default="8080")
    parser.add_argument("--path", default=os.environ.get("PATH", ""))
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.receive_env:
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            receive_and_exec(args.receive_env, command)
        elif args.check_env:
            check_environment(os.environ)
        else:
            if not args.label or not args.log:
                parser.error("--label and --log required")
            env = {**os.environ, "DASHBOARD_PORT": args.port, "PATH": args.path}
            submit(args.label, args.log, env,
                   ["/usr/bin/caffeinate", "-i", sys.executable, str(ROOT / "dashboard_server.py")])
    except Exception as exc:
        # Exception text from decoding/subprocesses could contain input data.
        print("Dashboard startup failed: " + (str(exc) if isinstance(exc, RuntimeError)
                                              else type(exc).__name__), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

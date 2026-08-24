#!/bin/bash
# Restart the Dashboard server in the background, then prove it picked up the
# current `scripts/_shared/broker_gate.py`.
#
# Why this exists separately from `open_dashboard.sh`: that script opens a
# browser and then blocks on `wait`, so it owns the terminal. This one detaches
# and returns, which is what you want when the page is already open and only the
# server is stale.
#
# The verification at the end is the point. `dashboard_server.py` imports
# broker_gate once at startup, so a long-lived process keeps serving whatever
# that file said on the day it launched. On 2026-08-15 the server had been up
# since 08-12 and was still emitting `headline_bucket: null` for every provider,
# which the current Dashboard/utils.js renders as "該家未回報 5h 窗口" — a claim
# about the provider that was really a fact about the process.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${DASHBOARD_PORT:-8080}"
LOG="${DASHBOARD_LOG:-/tmp/dashboard_server.log}"
LABEL="${DASHBOARD_LAUNCH_LABEL:-com.kavi.aicommittee.dashboard}"
# `launchctl submit` does not inherit the interactive shell's PATH. Codex is a
# `/usr/bin/env node` wrapper and Agy lives in ~/.local/bin, so omitting these
# directories makes every daemon inference fail before a provider process can
# start (Codex rc=127, Agy rc=-2).
LAUNCH_PATH="/Users/kavi/.local/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# A launchd-submitted process survives the terminal/session that ran this
# script. Remove the previous submitted job first; killing only its child PID
# leaves the label occupied and the next `launchctl submit` cannot replace it.
if command -v launchctl >/dev/null 2>&1 && launchctl list "$LABEL" >/dev/null 2>&1; then
    launchctl remove "$LABEL" || true
    sleep 0.5
fi

pids=$(lsof -ti:"$PORT" 2>/dev/null || true)
if [ -n "$pids" ]; then
    echo "Stopping server on port $PORT (PID $(echo "$pids" | tr '\n' ' '))"
    # TERM first so the handler can close the listening socket; KILL only for
    # what is still there after the grace period. `open_dashboard.sh` goes
    # straight to -9, which can leave the port in TIME_WAIT and make the
    # restart below fail for a reason that has nothing to do with the code.
    echo "$pids" | xargs kill 2>/dev/null || true
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        sleep 0.3
        [ -z "$(lsof -ti:"$PORT" 2>/dev/null || true)" ] && break
    done
    remaining=$(lsof -ti:"$PORT" 2>/dev/null || true)
    if [ -n "$remaining" ]; then
        echo "Still listening after TERM; sending KILL"
        echo "$remaining" | xargs kill -9 2>/dev/null || true
        sleep 0.5
    fi
fi

# `caffeinate -i` keeps macOS awake while the server runs: a locked screen
# suspends long analysis runs mid-stream (see open_dashboard.sh).
echo "Starting dashboard_server.py on port $PORT (log: $LOG)"
if command -v launchctl >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
    launchctl submit -l "$LABEL" -o "$LOG" -e "$LOG" -- \
        /usr/bin/env "DASHBOARD_PORT=$PORT" "PATH=$LAUNCH_PATH" \
        /usr/bin/caffeinate -i \
        "$PYTHON_BIN" "$PWD/dashboard_server.py"
else
    PATH="$LAUNCH_PATH" DASHBOARD_PORT="$PORT" \
        nohup caffeinate -i python3 dashboard_server.py >"$LOG" 2>&1 &
    disown || true
fi

for _ in $(seq 1 40); do
    sleep 0.25
    if curl -sf -o /dev/null "http://127.0.0.1:$PORT/"; then break; fi
done
if ! curl -sf -o /dev/null "http://127.0.0.1:$PORT/"; then
    echo "FAILED: server did not answer on port $PORT. Last log lines:" >&2
    tail -20 "$LOG" >&2 || true
    exit 1
fi
echo "Dashboard running → http://localhost:$PORT/"

# --- did it actually pick up the current broker_gate? ----------------------
echo
echo "LLM quota panel — which window each bar is reading:"
curl -s --max-time 10 "http://127.0.0.1:$PORT/api/llm-config" | python3 -c '
import json, sys

providers = ((json.load(sys.stdin).get("status") or {}).get("broker") or {}).get("providers") or {}
if not providers:
    print("  (broker unreachable or disabled — nothing to check)")
    raise SystemExit(0)

# codex genuinely reports no five-hour window, so null is correct there and only
# there. Anywhere else it means the running process predates `_headline_bucket`.
EXPECT_NONE = {"codex"}
stale = []
for name, info in sorted(providers.items()):
    bucket = info.get("headline_bucket")
    cooldown = info.get("cooldown_until")
    note = "" if bucket or name in EXPECT_NONE else "  <-- expected a 5h window"
    if not bucket and name not in EXPECT_NONE:
        stale.append(name)
    print(f"  {name:<8} headline_bucket={str(bucket):<20} cooldown_until={cooldown}{note}")

if stale:
    print()
    print("WARNING: " + ", ".join(stale) + " reported no five-hour window.")
    print("The panel will say 該家未回報 5h 窗口 for them. If broker_gate.py has")
    print("_headline_bucket, the server is still running old code — check the log.")
    raise SystemExit(1)
print()
print("OK: every provider that has a five-hour window is reporting one.")
'

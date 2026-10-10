#!/bin/bash
# Start Dashboard server (positions API + mtime cache-busting) and open browser.
set -e
cd "$(dirname "$0")"
PORT=8080

# 先收掉舊 server。kill 是非同步的：process 還沒收屍前 socket 不會釋放，
# 舊版直接 kill -9 完就 bind，撞上 [Errno 48] Address already in use ——
# 而且失敗的是 python，script 照樣往下印「Dashboard running」，看起來像有開。
# 所以這裡 TERM → KILL 逐級升，每級都等到 port 真的空出來為止。
stop_port() {
    local pids sig i
    for sig in TERM KILL; do
        pids=$(lsof -ti:$PORT 2>/dev/null || true)
        [ -z "$pids" ] && return 0
        echo "Stopping existing listener on :$PORT (PID $(echo $pids | tr '\n' ' ')) with SIG$sig"
        kill -"$sig" $pids 2>/dev/null || true
        for i in $(seq 1 25); do
            [ -z "$(lsof -ti:$PORT 2>/dev/null || true)" ] && return 0
            sleep 0.2
        done
    done
    return 1
}
if ! stop_port; then
    echo "Port $PORT still held by PID $(lsof -ti:$PORT 2>/dev/null | tr '\n' ' ') — aborting instead of starting a server that cannot bind" >&2
    exit 1
fi

echo "Starting Dashboard server at http://localhost:$PORT"
# caffeinate -i prevents macOS from sleeping while server is running
# (avoids Claude API stream timeouts when screen is locked during long analysis)
python3 -u dashboard_server.py &
SERVER_PID=$!
caffeinate -i -w "$SERVER_PID" &
CAFFEINATE_PID=$!

WIND_PID=""
cleanup() {
    trap - EXIT INT TERM HUP
    kill -TERM "$SERVER_PID" 2>/dev/null || true
    if [ -n "$WIND_PID" ]; then
        kill -TERM "$WIND_PID" 2>/dev/null || true
    fi
    wait "$SERVER_PID" 2>/dev/null || true
    wait "$CAFFEINATE_PID" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 0' INT TERM HUP

# Wait for server to start listening. 沒起來就不要往下走 —— 後面的 open /
# 風向派工器 / 「Dashboard running」都建立在「真的有 server」這個前提上。
ready=0
for i in $(seq 1 50); do
    if curl -sf -o /dev/null "http://localhost:$PORT/"; then ready=1; break; fi
    sleep 0.2
done
if [ "$ready" != "1" ]; then
    echo "Dashboard server failed to come up on :$PORT — see the traceback above" >&2
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

open "http://localhost:$PORT/index.html"

# --- 風向派工器（探索層，會花錢）-------------------------------------------
# 生命週期綁在這個 script 上：Ctrl+C 兩個一起收。派工器啟動後**立刻**跑第一輪，
# 之後每 interval 一次 —— 所以「開 dashboard」= 「開始掃描」，這是刻意的取捨。
# 花費上限不靠這裡把關，靠 scripts/wind/budget.py 的雙上限（$10 累計 + 每日 8 次），
# 額度用完派工器自己會拒絕並記一筆 refusal。
# 不想跑就 WIND_DISPATCH=0 ./open_dashboard.sh，不必改檔。
WIND_LOG="${WIND_LOG:-/tmp/wind_dispatch.log}"
if [ "${WIND_DISPATCH:-1}" = "1" ]; then
    # 上一輪的 daemon 可能沒被 trap 收到（關終端機、kill -9），它不歸我們管但也
    # 不能再疊一隻上去 —— 兩隻同時跑會各自吃每日次數。
    existing=$(pgrep -f "scripts/wind/dispatch.py" 2>/dev/null || true)
    if [ -n "$existing" ]; then
        echo "Wind dispatcher already running (PID $(echo "$existing" | tr '\n' ' ')) — not starting another"
    else
        # `-u` 不可省：stdout 導到檔案時 Python 是 block buffering（4-8KB 才落盤），
        # 一輪只印三四行，log 會空好幾個小時 —— 一個要等到自己沒用時才有內容的 log。
        python3 -u scripts/wind/dispatch.py --interval 3600 >>"$WIND_LOG" 2>&1 &
        WIND_PID=$!
        echo "Wind dispatcher running (PID $WIND_PID, log: $WIND_LOG)"
    fi
fi

echo "Dashboard running (PID $SERVER_PID). Press Ctrl+C to stop."
wait $SERVER_PID

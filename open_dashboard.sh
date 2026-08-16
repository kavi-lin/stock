#!/bin/bash
# Start Dashboard server (positions API + mtime cache-busting) and open browser.
set -e
cd "$(dirname "$0")"
PORT=8080

# Kill any existing server on that port
lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true

echo "Starting Dashboard server at http://localhost:$PORT"
# caffeinate -i prevents macOS from sleeping while server is running
# (avoids Claude API stream timeouts when screen is locked during long analysis)
caffeinate -i python3 dashboard_server.py &
SERVER_PID=$!

# Wait for server to start listening
for i in 1 2 3 4 5; do
    if curl -sf -o /dev/null "http://localhost:$PORT/"; then break; fi
    sleep 0.2
done

open "http://localhost:$PORT/index.html"

# --- 風向派工器（探索層，會花錢）-------------------------------------------
# 生命週期綁在這個 script 上：Ctrl+C 兩個一起收。派工器啟動後**立刻**跑第一輪，
# 之後每 interval 一次 —— 所以「開 dashboard」= 「開始掃描」，這是刻意的取捨。
# 花費上限不靠這裡把關，靠 scripts/wind/budget.py 的雙上限（$10 累計 + 每日 8 次），
# 額度用完派工器自己會拒絕並記一筆 refusal。
# 不想跑就 WIND_DISPATCH=0 ./open_dashboard.sh，不必改檔。
WIND_LOG="${WIND_LOG:-/tmp/wind_dispatch.log}"
WIND_PID=""
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
trap 'kill $SERVER_PID $WIND_PID 2>/dev/null; exit 0' INT TERM
wait $SERVER_PID

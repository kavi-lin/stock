#!/bin/bash
# Start Dashboard server (positions API + mtime cache-busting) and open browser.
set -e
cd "$(dirname "$0")"
PORT=8080

# Kill any existing server on that port
lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true

echo "Starting Dashboard server at http://localhost:$PORT"
python3 dashboard_server.py &
SERVER_PID=$!

# Wait for server to start listening
for i in 1 2 3 4 5; do
    if curl -sf -o /dev/null "http://localhost:$PORT/"; then break; fi
    sleep 0.2
done

open "http://localhost:$PORT/index.html"

echo "Dashboard running (PID $SERVER_PID). Press Ctrl+C to stop."
trap "kill $SERVER_PID 2>/dev/null; exit 0" INT TERM
wait $SERVER_PID

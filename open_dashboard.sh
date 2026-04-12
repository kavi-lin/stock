#!/bin/bash
# Start local HTTP server and open Dashboard in browser
cd "$(dirname "$0")/Dashboard"
PORT=8080

# Kill any existing server on that port
lsof -ti:$PORT | xargs kill -9 2>/dev/null

echo "Starting Dashboard server at http://localhost:$PORT"
python3 -m http.server $PORT &
SERVER_PID=$!

sleep 0.5
open "http://localhost:$PORT/index.html"

echo "Dashboard running (PID $SERVER_PID). Press Ctrl+C to stop."
wait $SERVER_PID

#!/bin/bash
# Weekly decision REVIEW scheduler. It only enqueues the broker-governed
# dashboard protocol; the cron process never starts an LLM directly.

set -uo pipefail

ROOT="/Users/kavi/Developer/Claude/Projects/ai-investment-committee"
LOG_DIR="$ROOT/reports/decision_review"
LOG="$LOG_DIR/cron_review_$(date +%Y%m%d_%H%M%S).log"
SERVER_URL="${AIC_DASHBOARD_URL:-http://127.0.0.1:8080}"

mkdir -p "$LOG_DIR"
exec >>"$LOG" 2>&1
echo "weekly REVIEW enqueue $(date -u +%Y-%m-%dT%H:%M:%SZ)"

response="$(curl --fail --silent --show-error --max-time 10 \
  -H 'Content-Type: application/json' \
  --data '{"name":"llm_review"}' \
  "$SERVER_URL/api/protocol-queue" 2>&1)"
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "deferred: dashboard queue unavailable (curl rc=$rc); retry next schedule"
  echo "$response"
  exit 75
fi

echo "queued: $response"
exit 0

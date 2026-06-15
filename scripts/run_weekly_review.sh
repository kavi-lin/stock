#!/bin/bash
# Weekly decision REVIEW runner (local cron).
# Rebuilds event_index, gates on rc=0, then spawns a single `claude` turn that
# executes the llm_review protocol per REVIEW_PROMPT.md and writes
# reports/decision_review/REVIEW_<TODAY>.md + updates REVIEW_TODO.md carry-over.
#
# Crontab (Sunday 08:00 Asia/Taipei — local machine time):
#   0 8 * * 0 /Users/kavi/Documents/Claude/Projects/AI投資委員會/scripts/run_weekly_review.sh
#
# Caveats:
#   - Mac must be AWAKE at run time (cron does not fire while asleep). Consider
#     `caffeinate` or pmset, or just run manually if you missed the slot.
#   - This bypasses dashboard_server's _protocol_lock. A lockfile guard below
#     prevents two REVIEW runs overlapping, but won't see a dashboard-launched
#     protocol. Sunday morning is low-traffic, so risk is minimal.

set -uo pipefail

ROOT="/Users/kavi/Documents/Claude/Projects/AI投資委員會"
PYTHON="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
CLAUDE="/Users/kavi/.local/bin/claude"
export PATH="/Users/kavi/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

cd "$ROOT" || { echo "cannot cd $ROOT"; exit 1; }

TODAY="$(date +%Y-%m-%d)"
LOG_DIR="$ROOT/reports/decision_review"
LOG="$LOG_DIR/cron_review_$(date +%Y%m%d_%H%M%S).log"
LOCK="/tmp/ai_weekly_review.lock"

exec >>"$LOG" 2>&1
echo "=== weekly REVIEW cron start $(date -u +%Y-%m-%dT%H:%M:%SZ) (today=$TODAY) ==="

# Single-run guard.
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "another REVIEW run holds $LOCK — abort"; exit 1
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

# Step 0 — rebuild event_index, hard rc gate.
echo "--- rebuild event_index ---"
"$PYTHON" scripts/build_event_index.py
rc=$?
if [ $rc -ne 0 ]; then
  echo "build_event_index FAILED rc=$rc — abort REVIEW (do not run on stale index)"; exit $rc
fi

PROMPT='非互動 weekly decision REVIEW。一個 turn 跑完，不要中途停下問問題、不要輸出意見徵詢。
0. event_index 已由 wrapper rebuild 完成 (rc=0)。先確認 reports/decision_review/event_index_latest.json 的 generated_at 是今天日期，否則 abort。
1. Read reports/decision_review/REVIEW_PROMPT.md 拿完整規範。
2. Read reports/decision_review/event_index_latest.json (可能 300KB+)。
3. 完全依 REVIEW_PROMPT.md 執行：Step -1 Carry-over (讀並更新 reports/decision_review/REVIEW_TODO.md Active Items 的 review_count +1 / last_check=今天 / 對每項下 ready|still_waiting|stale 判斷) + Step 0 Adjustment Evaluation (對照 reports/decision_review/ADJUSTMENT_LEDGER.md 每筆 active Rec 拉本週 target_metric 值，下 improved|no_change|regressed) + Pattern Detection (N>=5 robust) + Root Cause Hypotheses + Adjustment Recommendations。
4. Write 結果到 reports/decision_review/REVIEW_'"$TODAY"'.md。
5. 依 REVIEW_PROMPT postamble 把本週新識別的 carry-over 候選 append 到 REVIEW_TODO.md (ID 連號)。
禁止：跳過 Adjustment Evaluation、跑到一半停下問問題、未產出 REVIEW_'"$TODAY"'.md 就結束。'

echo "--- spawn claude REVIEW turn ---"
"$CLAUDE" -p "$PROMPT" \
  --output-format stream-json --verbose \
  --permission-mode bypassPermissions
rc=$?
echo "--- claude rc=$rc ---"

if [ -f "$LOG_DIR/REVIEW_$TODAY.md" ]; then
  echo "OK — REVIEW_$TODAY.md written"
else
  echo "WARN — REVIEW_$TODAY.md NOT found (claude rc=$rc); check log"
fi
echo "=== weekly REVIEW cron end $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
exit $rc

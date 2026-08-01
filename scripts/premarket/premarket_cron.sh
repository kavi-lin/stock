#!/bin/bash
# ============================================================
# Pre-market data refresh — launchd entrypoint (headless).
#
# Runs daily_update.sh, which fetches raw data (breadth / FTD /
# market-top / FRED / thematic / momentum / nexus / mood / intraday /
# retail / morning brief / kill-triggers) and rebuilds
# Dashboard/data.json via bridge.py.
#
# Fully independent of dashboard_server.py and of any Claude turn — so
# it runs even when the dashboard server is off. When you later open the
# dashboard and press 盤前檢查, the "daily" leg is already fresh and is
# skipped; only the LLM legs (news digest / sector) run.
#
# Scheduled by ~/Library/LaunchAgents/com.kavi.aicommittee.premarket.plist
# ============================================================
set -u

PROJECT_DIR="/Users/kavi/Developer/Claude/Projects/ai-investment-committee"
cd "$PROJECT_DIR" || { echo "cannot cd $PROJECT_DIR"; exit 1; }

# launchd runs with a minimal environment: no login shell, no ~/.zshrc,
# no API keys, and a bare PATH. Load both explicitly.
ENV_FILE="$PROJECT_DIR/scripts/premarket/premarket_cron.env"
[ -f "$ENV_FILE" ] && source "$ENV_FILE"
export PATH="/Library/Frameworks/Python.framework/Versions/3.11/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

DATE=$(date '+%Y-%m-%d')
LOG_DIR="$PROJECT_DIR/logs/premarket_cron"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/premarket_${DATE}.log"

# Catch-up guard. The plist fires at several morning slots (04:30 / 05:00 /
# 06:00 / 07:00 / 08:00) because the 04:27 pmset wake is skipped when the Mac
# sleeps on battery with the lid closed — the first slot after the Mac is
# actually awake does the work, and every later slot is a no-op.
if [ -f "$LOG" ] && grep -q "daily_update.sh rc=0" "$LOG"; then
  echo "[premarket_cron] $(date '+%H:%M:%S') already succeeded today — skip" >> "$LOG"
  exit 0
fi

# Log retention: keep the 10 most recent per-day logs (one per trading day =
# ~2 weeks of weekdays), prune older. Count-based, not calendar-based, so
# weekends/holidays with no run don't shrink the retained history.
ls -1t "$LOG_DIR"/premarket_*.log 2>/dev/null | tail -n +11 | while IFS= read -r _old; do
  rm -f "$_old"
done

{
  echo "==================================================================="
  echo "[premarket_cron] START $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "  python3 = $(command -v python3)  ($(python3 --version 2>&1))"
  echo "  FMP_API_KEY set = $([ -n "${FMP_API_KEY:-}" ] && echo yes || echo NO)"
  echo "  FRED_API_KEY set = $([ -n "${FRED_API_KEY:-}" ] && echo yes || echo NO)"
  echo "-------------------------------------------------------------------"

  # Keep the Mac awake for the whole run. A scheduled pmset wake is often a
  # short "dark wake" that returns to sleep on idle and would suspend/kill the
  # multi-minute daily_update. caffeinate -i asserts against idle sleep (works
  # on battery too) and exits when daily_update.sh exits.
  caffeinate -i bash "$PROJECT_DIR/daily_update.sh"
  RC=$?

  echo "-------------------------------------------------------------------"
  echo "[premarket_cron] daily_update.sh rc=$RC"
  echo "[premarket_cron] END   $(date '+%Y-%m-%d %H:%M:%S %Z')"
} >> "$LOG" 2>&1

exit "${RC:-0}"

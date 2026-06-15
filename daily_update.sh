#!/bin/bash
# ============================================================
# AI 投資委員會 — 每日標準更新流程
# 執行方式：bash daily_update.sh
# ============================================================

set -e  # 任一步驟失敗即停止

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DATE=$(date '+%Y-%m-%d')
# Worker counts raised for the FMP paid plan (250/min). Aggregate RPM is now
# capped centrally by scripts/_shared/fmp_pool, so worker count only governs
# local concurrency/latency, not quota safety.
MOMENTUM_SCREEN_WORKERS="${MOMENTUM_SCREEN_WORKERS:-20}"
THEMATIC_PREDICT_WORKERS="${THEMATIC_PREDICT_WORKERS:-16}"
DAILY_RUN_THEMATIC="${DAILY_RUN_THEMATIC:-1}"
DAILY_RUN_MOMENTUM_SCREEN="${DAILY_RUN_MOMENTUM_SCREEN:-1}"
DAILY_FORCE_THEMATIC="${DAILY_FORCE_THEMATIC:-0}"
FRED_STATUS="skipped"

RUN_BG_PIDS=()
RUN_BG_NAMES=()
RUN_BG_LOGS=()

_daily_log_path() {
  local name="$1"
  echo "${TMPDIR:-/tmp}/daily_update_${DATE}_$$_${name}.log"
}

run_bg() {
  local name="$1"
  shift
  local log
  log="$(_daily_log_path "$name")"
  echo "         ▶ ${name} started → ${log}"
  (
    _job_start=$(date +%s)
    set +e
    "$@"
    _job_rc=$?
    set -e
    echo "__JOB_ELAPSED_SEC__:$(( $(date +%s) - _job_start ))"
    exit "$_job_rc"
  ) > "$log" 2>&1 &
  RUN_BG_PIDS+=("$!")
  RUN_BG_NAMES+=("$name")
  RUN_BG_LOGS+=("$log")
}

dump_job_log() {
  local log="$1"
  if [ -s "$log" ]; then
    sed '/^__JOB_ELAPSED_SEC__:/d; s/^/         │ /' "$log"
  fi
}

wait_bg_jobs() {
  local fatal="$1"
  local failed=0
  local i pid name log rc

  for i in "${!RUN_BG_PIDS[@]}"; do
    pid="${RUN_BG_PIDS[$i]}"
    name="${RUN_BG_NAMES[$i]}"
    log="${RUN_BG_LOGS[$i]}"

    if wait "$pid"; then
      rc=0
    else
      rc=$?
    fi

    echo ""
    echo "──── ${name} log (rc=${rc}) ────"
    dump_job_log "$log"
    if grep -q "__JOB_ELAPSED_SEC__:" "$log" 2>/dev/null; then
      echo "         ⏱ ${name} elapsed $(grep "__JOB_ELAPSED_SEC__:" "$log" | tail -1 | cut -d: -f2)s"
    fi

    if [ "$rc" -ne 0 ]; then
      failed="$rc"
      if [ "$fatal" = "fatal" ]; then
        echo "         ❌ ${name} 失敗，中止。"
      else
        echo "         ⚠️  ${name} 失敗（非致命，rc=${rc}），繼續..."
      fi
    fi
  done

  RUN_BG_PIDS=()
  RUN_BG_NAMES=()
  RUN_BG_LOGS=()

  if [ "$fatal" = "fatal" ] && [ "$failed" -ne 0 ]; then
    return "$failed"
  fi
  return 0
}

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  AI 投資委員會 — 每日更新  │  $TIMESTAMP  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1-4｜Phase 1 parallel, bridge prerequisites ─────────
step1_breadth() {
  # Use the repo-local skill (was ~/.claude/skills/, which let different
  # machines/agents run different versions). plan_support_codex.md cleanup item.
  # Non-fatal (V4.4.0): bridge.py falls back to the newest stale breadth cache,
  # so a TraderMonty GitHub Pages outage must not abort the whole daily run.
  echo "[ 1/10 ] 市場廣度分析（TraderMonty CSV）..."
  set +e
  python3 skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py \
    --output-dir sector/breadth_cache/
  local rc=$?
  set -e
  if [ "$rc" -eq 0 ]; then
    echo "         ✅ 廣度數據完成 → sector/breadth_cache/"
  else
    echo "         ⚠️  Step 1 失敗（非致命，rc=${rc}）— bridge 將用最近一份 stale breadth cache 繼續..."
  fi
  return 0
}

step2_ftd() {
  echo "[ 2/10 ] FTD 偵測（yfinance）..."
  set +e
  python3 sector/ftd_yfinance.py --output-dir sector/ftd_cache/
  local rc=$?
  set -e
  if [ "$rc" -eq 0 ]; then
    echo "         ✅ FTD 偵測完成 → sector/ftd_cache/"
  else
    echo "         ❌ Step 2 失敗。"
  fi
  return "$rc"
}

step3_market_top() {
  echo "[ 3/10 ] 市場頂部偵測（yfinance）..."
  set +e
  python3 sector/market_top_yfinance.py --output-dir sector/market_top_cache/
  local rc=$?
  set -e
  if [ "$rc" -eq 0 ]; then
    echo "         ✅ 頂部偵測完成 → sector/market_top_cache/"
  else
    echo "         ❌ Step 3 失敗。"
  fi
  return "$rc"
}

step4_fred() {
  # Non-fatal: keep bridge usable when FRED has a network/API blip.
  echo "[ 4/10 ] FRED 宏觀數據更新（利率 / 通膨 / 就業 / 信用）..."
  if [ -z "$FRED_API_KEY" ]; then
    echo "         ⚠️  FRED_API_KEY 未設定，跳過（不影響後續步驟）"
    echo "__FRED_STATUS__:skipped"
    return 0
  fi

  set +e
  python3 skills/fred-macro/scripts/fetch.py --no-cache --json-only > /dev/null
  local rc=$?
  set -e
  if [ "$rc" -eq 0 ]; then
    echo "         ✅ FRED cache 更新完成 → skills/fred-macro/cache/fred_latest.json"
    echo "__FRED_STATUS__:ok"
  else
    echo "         ⚠️  FRED 更新失敗（非致命，rc=${rc}），繼續執行..."
    echo "__FRED_STATUS__:failed"
  fi
  return 0
}

echo "[ Phase 1 ]  並行更新 breadth / FTD / market-top / FRED..."
run_bg "1_breadth" step1_breadth
run_bg "2_ftd" step2_ftd
run_bg "3_market_top" step3_market_top
run_bg "4_fred" step4_fred
wait_bg_jobs fatal

FRED_LOG="$(_daily_log_path "4_fred")"
if grep -q "__FRED_STATUS__:ok" "$FRED_LOG" 2>/dev/null; then
  FRED_STATUS="ok"
elif grep -q "__FRED_STATUS__:failed" "$FRED_LOG" 2>/dev/null; then
  FRED_STATUS="failed"
else
  FRED_STATUS="skipped"
fi

echo ""

# ── Step 5｜整合 → Dashboard/data.json ───────────────────────
echo "[ 5/10 ] 整合所有 cache → Dashboard/data.json..."
python3 bridge.py

if [ $? -eq 0 ]; then
  echo "         ✅ Dashboard 更新完成 → Dashboard/data.json"
else
  echo "         ❌ Step 5 失敗，中止。" && exit 1
fi

echo ""

# ── Step 5.5-9.7｜Phase 2 hybrid lanes ───────────────────────
step55_etf_holdings() {
  local ETF_META LAST_REFRESH DAYS_OLD REFRESH_RC
  ETF_META="skills/thematic-screener/etf_meta.yaml"
  if [ -f "$ETF_META" ]; then
    LAST_REFRESH=$(grep "etf_holdings_last_refreshed" "$ETF_META" | sed -E "s/.*: '?([0-9-]+)'?.*/\1/")
    if [ -n "$LAST_REFRESH" ]; then
      DAYS_OLD=$(( ($(date +%s) - $(date -j -f "%Y-%m-%d" "$LAST_REFRESH" "+%s" 2>/dev/null || date -d "$LAST_REFRESH" "+%s")) / 86400 ))
      if [ "$DAYS_OLD" -ge 90 ]; then
        echo "[ 5.5 ] ETF holdings ${DAYS_OLD}d 舊 → 自動 refresh（每季一次）..."
        set +e
        set -o pipefail
        python3 skills/thematic-screener/scripts/refresh_etf_holdings.py --top-n 25 2>&1 | tail -3
        REFRESH_RC=$?
        set +o pipefail
        set -e
        if [ "$REFRESH_RC" -eq 0 ]; then
          echo "         ✅ ETF holdings refreshed → themes.yaml + etf_meta.yaml"
          echo "         ⚠️  將同步重跑 theme-detector 以套用新 universe（下游 screen.py 用得到）"
          set +e
          python3 skills/theme-detector/scripts/theme_detector.py --max-themes 25 --max-stocks-per-theme 25 > /dev/null 2>&1
          local TD_RC=$?
          set -e
          if [ "$TD_RC" -ne 0 ]; then
            echo "         ⚠️  theme-detector 重跑失敗（rc=${TD_RC}）— 舊 universe 將沿用到下次手動重跑，請檢查！"
          fi
        else
          echo "         ⚠️  ETF refresh 失敗（非致命），用舊 holdings 繼續..."
        fi
      elif [ "$DAYS_OLD" -ge 60 ]; then
        echo "[ 5.5 ] ⚠ ETF holdings ${DAYS_OLD}d 舊（≥ 60d），90d 將自動 refresh"
      else
        echo "[ 5.5 ] ✅ ETF holdings ${DAYS_OLD}d 舊（fresh）"
      fi
    fi
  fi
  return 0
}

step6_thematic() {
  local LATEST_RECS LATEST_THEME THEME_AGE_HR TICKER_COUNT STEP6_START SCREEN_RC STEP6_ELAPSED RECS_FILE RECS_SIZE
  echo "[ 6/10 ] Thematic Screener — Tactical Opportunity Radar..."
  RECS_FILE="skills/thematic-screener/data/recommendations/${DATE}.json"
  LATEST_RECS=$(ls -t skills/thematic-screener/data/recommendations/*.json 2>/dev/null | head -1 || true)

  if [ "$DAILY_RUN_THEMATIC" != "1" ] && [ "$DAILY_FORCE_THEMATIC" != "1" ]; then
    if [ -n "$LATEST_RECS" ]; then
      RECS_SIZE=$(ls -lh "$LATEST_RECS" 2>/dev/null | awk '{print $5}')
      echo "         ✅ 使用最新 thematic recommendations，跳過重跑 → $LATEST_RECS ($RECS_SIZE)"
      echo "           （daily 預設會刷新；設 DAILY_RUN_THEMATIC=0 才會走這個快取模式）"
    else
      echo "         ⚠️  recommendations 不存在，跳過（daily 預設會生成；目前 DAILY_RUN_THEMATIC=0）"
    fi
    return 0
  fi

  if [ "$DAILY_FORCE_THEMATIC" != "1" ] && [ -s "$RECS_FILE" ]; then
    RECS_SIZE=$(ls -lh "$RECS_FILE" 2>/dev/null | awk '{print $5}')
    echo "         ✅ 今日推薦已存在，跳過重跑 → $RECS_FILE ($RECS_SIZE)"
    echo "           （需要強制重跑可設 DAILY_FORCE_THEMATIC=1）"
    return 0
  fi

  LATEST_THEME=$(ls -t skills/theme-detector/cache/theme_detector_*.json 2>/dev/null | head -1)
  if [ -z "$LATEST_THEME" ]; then
    echo "         ⚠️  theme-detector cache 不存在，跳過（請先跑「產業掃描」生成 cache）"
    return 0
  fi

  THEME_AGE_HR=$(( ($(date +%s) - $(stat -f %m "$LATEST_THEME" 2>/dev/null || stat -c %Y "$LATEST_THEME")) / 3600 ))
  if [ "$THEME_AGE_HR" -gt 168 ]; then
    echo "         ⚠️  theme-detector cache 已 ${THEME_AGE_HR}h 舊（> 7 天），跳過。請先跑「產業掃描」"
    return 0
  fi

  TICKER_COUNT=$(python3 -c "
import json,sys
d=json.load(open('$LATEST_THEME'))
themes = (d.get('themes') or {}).get('all') or d.get('themes') or []
ts=set()
for t in themes:
    for s in (t.get('representative_stocks') or []):
        ts.add(s)
print(len(ts))
" 2>/dev/null)
  [ -z "$TICKER_COUNT" ] && TICKER_COUNT="?"
  echo "         ▶ predicting ~${TICKER_COUNT} unique tickers（4h cache 命中數秒；冷跑 3-8 分鐘）"
  STEP6_START=$(date +%s)
  set +e
  python3 skills/thematic-screener/scripts/screen.py --json-only \
    --predict-workers "$THEMATIC_PREDICT_WORKERS" \
    > /dev/null 2> >(sed 's/^/         │ /' >&2)
  SCREEN_RC=$?
  set -e
  STEP6_ELAPSED=$(( $(date +%s) - STEP6_START ))
  if [ "$SCREEN_RC" -eq 0 ]; then
    RECS_SIZE=$(ls -lh "$RECS_FILE" 2>/dev/null | awk '{print $5}')
    echo "         ✅ 推薦輸出完成 (${STEP6_ELAPSED}s) → $RECS_FILE ($RECS_SIZE)"
  else
    echo "         ⚠️  thematic-screener 執行失敗（非致命，${STEP6_ELAPSED}s 後 rc=${SCREEN_RC}），繼續..."
  fi
  return 0
}

step7_structural() {
  local WATCHLIST_RC
  echo "[ 7/10 ] Structural Watchlist — V2.19 結構性轉變候選..."
  set +e
  python3 news/scripts/build_structural_watchlist.py 2> >(sed 's/^/         │ /' >&2)
  WATCHLIST_RC=$?
  set -e
  if [ "$WATCHLIST_RC" -eq 0 ]; then
    echo "         ✅ watchlist 更新 → news/news_logs/structural_watchlist.json"
  else
    echo "         ⚠️  watchlist build 失敗 (rc=${WATCHLIST_RC})，非致命，繼續..."
  fi
  return 0
}

step8_nexus() {
  local NEXUS_RC NEXUS_SIZE
  echo "[ 8/10 ] Nexus 知識圖譜（Tier 1+2+3）..."
  set +e
  python3 scripts/nexus/build_graph.py --tier 1,2,3 --full 2> >(sed 's/^/         │ /' >&2)
  NEXUS_RC=$?
  set -e
  if [ "$NEXUS_RC" -eq 0 ]; then
    NEXUS_SIZE=$(ls -lh Dashboard/nexus_graph.json 2>/dev/null | awk '{print $5}')
    echo "         ✅ Nexus graph 更新完成 → Dashboard/nexus_graph.json (${NEXUS_SIZE})"
  else
    echo "         ⚠️  Nexus build 失敗 (rc=${NEXUS_RC})，非致命，繼續..."
  fi
  return 0
}

step93_market_mood() {
  local MOOD_RC
  echo "[ 9.3 ] Market Mood（VIX/SKEW/期權 put-call/Fear&Greed 合成）..."
  set +e
  python3 skills/market-sentiment-analyzer/scripts/mood.py \
    --output Dashboard/market_mood.json --json-only \
    > /dev/null 2> >(sed 's/^/         │ /' >&2)
  MOOD_RC=$?
  set -e
  if [ "$MOOD_RC" -eq 0 ]; then
    echo "         ✅ Market Mood → Dashboard/market_mood.json"
  else
    echo "         ⚠️  Market Mood 失敗 (rc=${MOOD_RC})，非致命,繼續..."
  fi
  return 0
}

step94_trending() {
  local TTK_RC TTK_COUNT
  echo "[ 9.4 ] Trending Ticker Discovery (社群極性)..."
  set +e
  python3 skills/retail-sector-pulse/scripts/trending_tickers.py \
    --window-hours 24 \
    --output Dashboard/trending_tickers.json \
    2> >(sed 's/^/         │ /' >&2)
  TTK_RC=$?
  set -e
  if [ "$TTK_RC" -eq 0 ]; then
    TTK_COUNT=$(python3 -c "import json; d=json.load(open('Dashboard/trending_tickers.json')); print(f\"{len(d.get('tickers',[]))} tickers, {len(d.get('market_wide_buzz',[]))} topics\")" 2>/dev/null || echo "?")
    echo "         ✅ Trending discovery 完成 → Dashboard/trending_tickers.json (${TTK_COUNT})"
  else
    echo "         ⚠️  Trending discovery 失敗 (rc=${TTK_RC})，非致命,繼續..."
  fi
  return 0
}

step95_retail_sector() {
  local RSP_RC RSP_COUNT
  echo "[ 9.5 ] Retail Sector Pulse 聚合..."
  set +e
  python3 skills/retail-sector-pulse/scripts/aggregate.py \
    --output Dashboard/retail_sector_pulse.json \
    2> >(sed 's/^/         │ /' >&2)
  RSP_RC=$?
  set -e
  if [ "$RSP_RC" -eq 0 ]; then
    RSP_COUNT=$(python3 -c "import json; d=json.load(open('Dashboard/retail_sector_pulse.json')); print(len(d.get('sectors',[])))" 2>/dev/null || echo "?")
    echo "         ✅ Retail Sector Pulse 完成 → Dashboard/retail_sector_pulse.json (${RSP_COUNT} sectors)"
  else
    echo "         ⚠️  Retail Sector Pulse 失敗 (rc=${RSP_RC})，非致命,繼續..."
  fi
  return 0
}

step96_fundamentals_prefetch() {
  local FND_RC
  echo "[ 9.6 ] Momentum Fundamentals Prefetch (P/S / GM% / Rev YoY TTM)..."
  set +e
  python3 skills/momentum-monitor/scripts/prefetch_fundamentals.py \
    2> >(sed 's/^/         │ /' >&2) \
     > >(sed 's/^/         │ /')
  FND_RC=$?
  set -e
  if [ "$FND_RC" -eq 0 ]; then
    echo "         ✅ Fundamentals cache 預熱完成"
  else
    echo "         ⚠️  Fundamentals prefetch rc=${FND_RC}（非致命，screen.py lazy refetch 即可）"
  fi
  return 0
}

step97_momentum_screen() {
  local MOM_RC MOM_CSV
  if [ "$DAILY_RUN_MOMENTUM_SCREEN" != "1" ]; then
    echo "[ 9.7 ] Momentum Screen skipped（daily 預設開啟；目前 DAILY_RUN_MOMENTUM_SCREEN=0）"
    return 0
  fi

  echo "[ 9.7 ] Momentum Screen（all universe, workers=${MOMENTUM_SCREEN_WORKERS}）..."
  set +e
  python3 skills/momentum-monitor/scripts/screen.py \
    --universe all \
    --workers "$MOMENTUM_SCREEN_WORKERS" \
    --top 30 \
    2> >(sed 's/^/         │ /' >&2)
  MOM_RC=$?
  set -e
  if [ "$MOM_RC" -eq 0 ]; then
    MOM_CSV=$(ls -t skills/momentum-monitor/cache/screen_*.csv 2>/dev/null | head -1 || true)
    echo "         ✅ Momentum screen 完成 → ${MOM_CSV:-skills/momentum-monitor/cache/screen_*.csv}"
  else
    echo "         ⚠️  Momentum screen rc=${MOM_RC}（非致命，繼續...）"
  fi
  return 0
}

# Two independent FMP sub-chains. Ordering WITHIN each chain is required
# (5.5→6: screen.py consumes the theme cache refreshed by ETF step; 9.6→9.7:
# fundamentals prefetch warms the cache momentum screen reads). The two chains
# have no cross-dependency, so they run in parallel — the central fmp_pool keeps
# their combined call rate under 250/min, which the old serialized lane had to
# enforce by hand.
fmp_chain_thematic() {
  step55_etf_holdings
  step6_thematic
}
fmp_chain_momentum() {
  step96_fundamentals_prefetch
  step97_momentum_screen
}

fmp_lane() {
  echo "[ Phase 2A ] FMP lane (pool-governed, parallel chains: thematic ∥ momentum)..."
  RUN_BG_PIDS=()
  RUN_BG_NAMES=()
  RUN_BG_LOGS=()
  run_bg "2a_thematic" fmp_chain_thematic
  run_bg "2a_momentum" fmp_chain_momentum
  wait_bg_jobs nonfatal
}

non_fmp_lane() {
  echo "[ Phase 2B ] Non-FMP lane: structural / Nexus / trending..."
  RUN_BG_PIDS=()
  RUN_BG_NAMES=()
  RUN_BG_LOGS=()
  run_bg "7_structural" step7_structural
  run_bg "8_nexus" step8_nexus
  run_bg "93_market_mood" step93_market_mood
  run_bg "94_trending" step94_trending
  wait_bg_jobs nonfatal
  step95_retail_sector
}

echo "[ Phase 2 ]  Hybrid parallel: FMP-heavy work serialized, light lanes parallel..."
run_bg "phase2a_fmp_lane" fmp_lane
run_bg "phase2b_non_fmp_lane" non_fmp_lane
wait_bg_jobs nonfatal

step98_morning_brief() {
  local MB_RC
  echo "[ 9.8 ] Pre-Market Morning Brief..."
  set +e
  python3 scripts/premarket/morning_brief.py --date "$DATE" \
    --output "reports/PREMARKET_${DATE}.md" \
    2> >(sed 's/^/         │ /' >&2)
  MB_RC=$?
  set -e
  if [ "$MB_RC" -eq 0 ]; then
    echo "         ✅ Morning brief → reports/PREMARKET_${DATE}.md"
  else
    echo "         ⚠️  Morning brief rc=${MB_RC}（非致命，繼續...）"
  fi
  return 0
}
step98_morning_brief

step99_kill_triggers() {
  local KT_RC
  echo "[ 9.9 ] Kill-Trigger Monitor（Red Team 推翻條件每日檢查）..."
  set +e
  python3 scripts/kill_trigger_monitor.py 2> >(sed 's/^/         │ /' >&2)
  KT_RC=$?
  set -e
  if [ "$KT_RC" -eq 0 ]; then
    echo "         ✅ Kill triggers → Dashboard/kill_triggers.json"
  else
    echo "         ⚠️  Kill-trigger monitor rc=${KT_RC}（非致命，繼續...）"
  fi
  return 0
}
step99_kill_triggers

echo ""
echo "[ 10/10 ] Final bridge refresh → Dashboard/data.json..."
set +e
python3 bridge.py
FINAL_BRIDGE_RC=$?
set -e
if [ "$FINAL_BRIDGE_RC" -eq 0 ]; then
  echo "         ✅ Dashboard final refresh 完成（含 retail / momentum screen）"
else
  echo "         ⚠️  Final bridge refresh 失敗 (rc=${FINAL_BRIDGE_RC})，保留前段 data.json"
fi

echo ""
case "$FRED_STATUS" in
  ok)      FRED_LINE="║  提醒：FRED 宏觀數據已更新（個股分析將使用此 cache） ║" ;;
  failed)  FRED_LINE="║  提醒：⚠️  FRED 本次更新失敗，個股分析將沿用舊 cache ║" ;;
  *)       FRED_LINE="║  提醒：⚠️  FRED 未跑（FRED_API_KEY 未設定）          ║" ;;
esac

echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ 全部完成  │  $DATE                    ║"
echo "║  提醒：產業上升趨勢比例需另執行「產業掃描」才更新    ║"
echo "$FRED_LINE"
echo "║  提醒：每週末跑 weekly_review.py 評估推薦準確度      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

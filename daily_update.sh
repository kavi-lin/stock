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

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  AI 投資委員會 — 每日更新  │  $TIMESTAMP  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1｜廣度數據 ─────────────────────────────────────────
echo "[ 1/5 ]  市場廣度分析（TraderMonty CSV）..."
python3 ~/.claude/skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py \
  --output-dir sector/breadth_cache/

if [ $? -eq 0 ]; then
  echo "         ✅ 廣度數據完成 → sector/breadth_cache/"
else
  echo "         ❌ Step 1 失敗，中止。" && exit 1
fi

echo ""

# ── Step 2｜FTD 偵測 ─────────────────────────────────────────
echo "[ 2/5 ]  FTD 偵測（yfinance）..."
python3 sector/ftd_yfinance.py --output-dir sector/ftd_cache/

if [ $? -eq 0 ]; then
  echo "         ✅ FTD 偵測完成 → sector/ftd_cache/"
else
  echo "         ❌ Step 2 失敗，中止。" && exit 1
fi

echo ""

# ── Step 3｜市場頂部偵測 ──────────────────────────────────────
echo "[ 3/5 ]  市場頂部偵測（yfinance）..."
python3 sector/market_top_yfinance.py --output-dir sector/market_top_cache/

if [ $? -eq 0 ]; then
  echo "         ✅ 頂部偵測完成 → sector/market_top_cache/"
else
  echo "         ❌ Step 3 失敗，中止。" && exit 1
fi

echo ""

# ── Step 4｜FRED Macro Cache ──────────────────────────────────
echo "[ 4/5 ]  FRED 宏觀數據更新（利率 / 通膨 / 就業 / 信用）..."
if [ -z "$FRED_API_KEY" ]; then
  echo "         ⚠️  FRED_API_KEY 未設定，跳過（不影響後續步驟）"
else
  python3 skills/fred-macro/scripts/fetch.py --no-cache --json-only > /dev/null
  if [ $? -eq 0 ]; then
    echo "         ✅ FRED cache 更新完成 → skills/fred-macro/cache/fred_latest.json"
  else
    echo "         ⚠️  FRED 更新失敗（非致命），繼續執行..."
  fi
fi

echo ""

# ── Step 5｜整合 → Dashboard/data.json ───────────────────────
echo "[ 5/6 ]  整合所有 cache → Dashboard/data.json..."
python3 bridge.py

if [ $? -eq 0 ]; then
  echo "         ✅ Dashboard 更新完成 → Dashboard/data.json"
else
  echo "         ❌ Step 5 失敗，中止。" && exit 1
fi

echo ""

# ── Step 5.5｜ETF Holdings Refresh Check (auto every 90 days) ───
ETF_META="skills/thematic-screener/etf_meta.yaml"
if [ -f "$ETF_META" ]; then
  LAST_REFRESH=$(grep "etf_holdings_last_refreshed" "$ETF_META" | sed -E "s/.*: '?([0-9-]+)'?.*/\1/")
  if [ -n "$LAST_REFRESH" ]; then
    DAYS_OLD=$(( ($(date +%s) - $(date -j -f "%Y-%m-%d" "$LAST_REFRESH" "+%s" 2>/dev/null || date -d "$LAST_REFRESH" "+%s")) / 86400 ))
    if [ $DAYS_OLD -ge 90 ]; then
      echo "[ 5.5 ]  ETF holdings ${DAYS_OLD}d 舊 → 自動 refresh（每季一次）..."
      set +e
      python3 skills/thematic-screener/scripts/refresh_etf_holdings.py --top-n 25 2>&1 | tail -3
      REFRESH_RC=$?
      set -e
      if [ $REFRESH_RC -eq 0 ]; then
        echo "         ✅ ETF holdings refreshed → themes.yaml + etf_meta.yaml"
        echo "         ⚠️  將同步重跑 theme-detector 以套用新 universe（下游 screen.py 用得到）"
        python3 skills/theme-detector/scripts/theme_detector.py --max-themes 25 --max-stocks-per-theme 25 > /dev/null 2>&1
      else
        echo "         ⚠️  ETF refresh 失敗（非致命），用舊 holdings 繼續..."
      fi
    elif [ $DAYS_OLD -ge 60 ]; then
      echo "[ 5.5 ]  ⚠ ETF holdings ${DAYS_OLD}d 舊（≥ 60d），90d 將自動 refresh"
    else
      echo "[ 5.5 ]  ✅ ETF holdings ${DAYS_OLD}d 舊（fresh）"
    fi
  fi
fi

echo ""

# ── Step 6｜Thematic Screener (Tactical Opportunity Radar) ────
echo "[ 6/6 ]  Thematic Screener — Tactical Opportunity Radar..."
LATEST_THEME=$(ls -t skills/theme-detector/cache/theme_detector_*.json 2>/dev/null | head -1)
if [ -z "$LATEST_THEME" ]; then
  echo "         ⚠️  theme-detector cache 不存在，跳過（請先跑「產業掃描」生成 cache）"
else
  THEME_AGE_HR=$(( ($(date +%s) - $(stat -f %m "$LATEST_THEME" 2>/dev/null || stat -c %Y "$LATEST_THEME")) / 3600 ))
  if [ $THEME_AGE_HR -gt 168 ]; then
    echo "         ⚠️  theme-detector cache 已 ${THEME_AGE_HR}h 舊（> 7 天），跳過。請先跑「產業掃描」"
  else
    # 非致命：thematic-screener 失敗不中止整體流程
    set +e
    python3 skills/thematic-screener/scripts/screen.py --json-only > /dev/null 2>&1
    SCREEN_RC=$?
    set -e
    if [ $SCREEN_RC -eq 0 ]; then
      RECS_FILE="skills/thematic-screener/data/recommendations/${DATE}.json"
      RECS_SIZE=$(ls -lh "$RECS_FILE" 2>/dev/null | awk '{print $5}')
      echo "         ✅ 推薦輸出完成 → $RECS_FILE ($RECS_SIZE)"
    else
      echo "         ⚠️  thematic-screener 執行失敗（非致命），繼續..."
    fi
  fi
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ 全部完成  │  $DATE                    ║"
echo "║  提醒：產業上升趨勢比例需另執行「產業掃描」才更新    ║"
echo "║  提醒：FRED 宏觀數據已更新（個股分析將使用此 cache） ║"
echo "║  提醒：每週末跑 weekly_review.py 評估推薦準確度      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

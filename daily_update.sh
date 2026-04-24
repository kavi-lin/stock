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
echo "[ 5/5 ]  整合所有 cache → Dashboard/data.json..."
python3 bridge.py

if [ $? -eq 0 ]; then
  echo "         ✅ Dashboard 更新完成 → Dashboard/data.json"
else
  echo "         ❌ Step 5 失敗，中止。" && exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ 全部完成  │  $DATE                    ║"
echo "║  提醒：產業上升趨勢比例需另執行「產業掃描」才更新    ║"
echo "║  提醒：FRED 宏觀數據已更新（個股分析將使用此 cache） ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

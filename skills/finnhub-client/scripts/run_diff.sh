#!/usr/bin/env bash
# Run the Finnhub vs FMP diff tool with default ticker basket.
# Outputs Markdown report to skills/finnhub-client/diff_reports/YYYYMMDD.md
#
# Required env: FINNHUB_API_KEY, FMP_API_KEY
# Optional flag: --no-cache (force live Finnhub calls)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -z "${FINNHUB_API_KEY:-}" ]]; then
    echo "ERROR: FINNHUB_API_KEY not set" >&2
    exit 2
fi
if [[ -z "${FMP_API_KEY:-}" ]]; then
    echo "ERROR: FMP_API_KEY not set" >&2
    exit 2
fi

# Default basket: 8 mega-caps across sectors + 2 broad ETFs
TICKERS="${TICKERS:-AAPL,MSFT,NVDA,TSLA,AMD,META,JPM,XOM,SPY,QQQ}"

python3 diff_tool.py --tickers "$TICKERS" "$@"

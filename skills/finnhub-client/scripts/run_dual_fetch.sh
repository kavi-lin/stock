#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -z "${FINNHUB_API_KEY:-}" ]; then
    echo "ERROR: FINNHUB_API_KEY not set" >&2
    exit 1
fi
if [ -z "${FMP_API_KEY:-}" ]; then
    echo "ERROR: FMP_API_KEY not set (audit side disabled)" >&2
    exit 1
fi

python3 dual_fetch.py "$@"

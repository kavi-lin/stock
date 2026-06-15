#!/usr/bin/env python3
"""fetch_peer_descriptor.py — Peer descriptor cache (V1.0 STUB).

V1.0: writes empty descriptor (no LLM call, no network). Interface preserved
for Phase A.5 swap to Haiku 4.5 one-shot batch call.

Schema written:
{
    "ticker": "PL",
    "peers": {},            # to be filled with {peer: {focus_area, market_share_note}}
    "status": "stub_no_llm",
    "llm_model": null,
    "generated_at": "...",
    "ttl_days": 14
}

When future LLM version is implemented:
  - Read peers from _shared.company_context.get_peers(ticker)
  - Build single batch prompt for all peers (~5-10) into one Haiku 4.5 call
  - Parse JSON response into peers dict
  - Write same schema with status=ok, llm_model=claude-haiku-4-5, generated_at=now

Usage:
  python3 fetch_peer_descriptor.py PL                 # writes stub
  python3 fetch_peer_descriptor.py PL --force         # overwrite existing
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache" / "peer_descriptor"


def write_stub(ticker: str, *, force: bool = False) -> Path:
    ticker = ticker.upper()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = CACHE_DIR / f"{ticker}.json"
    if p.exists() and not force:
        existing = json.loads(p.read_text())
        if existing.get("status") and existing.get("status") != "stub_no_llm":
            print(f"[peer-desc] existing non-stub descriptor at {p}; pass --force to overwrite")
            return p
    stub = {
        "ticker": ticker,
        "peers": {},
        "status": "stub_no_llm",
        "llm_model": None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ttl_days": 14,
        "note": (
            "First-version stub. Phase A.5 will swap to Haiku 4.5 one-shot batch call. "
            "Until then, IC Memo §4 Peers table renders Focus Area / Market Share Note as '—'."
        ),
    }
    p.write_text(json.dumps(stub, indent=2, ensure_ascii=False))
    return p


def main():
    ap = argparse.ArgumentParser(description="Peer descriptor stub writer (V1.0 — no LLM).")
    ap.add_argument("ticker", help="Stock ticker")
    ap.add_argument("--force", action="store_true", help="Overwrite existing file")
    args = ap.parse_args()
    p = write_stub(args.ticker, force=args.force)
    print(f"[peer-desc] stub written: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

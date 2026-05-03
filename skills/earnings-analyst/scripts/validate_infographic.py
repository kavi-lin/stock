"""
earnings-analyst — Infographic JSON schema validator (V1.0)

Verifies that <TICKER>_<DATE>.infographic.json (produced by the LLM narrate
phase) has all required fields per schema.md "Infographic Cache" section.

Usage:
    python3 skills/earnings-analyst/scripts/validate_infographic.py NVDA
        rc=0  → pass
        rc=1  → schema drift / missing fields — see stderr
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CACHE_DIR = os.path.join(BASE_DIR, "skills", "earnings-analyst", "cache")
EXPECTED_VERSION = "V1.0"
EXPECTED_KIND = "infographic"

TOP_REQUIRED = [
    "ticker", "as_of_date", "last_earnings_date",
    "fiscal_label", "schema_version", "schema_kind",
    "transcript_used", "headline_oneliner",
    "surprise", "segments_q", "capital_returns",
    "key_highlights", "summary",
]

SURPRISE_REQUIRED = [
    "revenue_actual", "revenue_estimated", "revenue_beat",
    "eps_actual", "eps_estimated", "eps_beat",
]

SEGMENT_REQUIRED = ["is_fy_fallback", "items"]
ITEM_REQUIRED = ["name", "amount_usd"]

CAPITAL_REQUIRED = [
    "buyback_authorization_usd", "buyback_qtr_executed_usd",
    "dividend_qtr_paid_usd", "total_returned_qtr_usd",
    "announcements",
]

CEO_QUOTE_REQUIRED = ["speaker", "quote"]

SUMMARY_MIN = 2
HIGHLIGHT_MIN = 3


def find_infographic(ticker: str) -> str | None:
    files = sorted(glob.glob(os.path.join(CACHE_DIR, f"{ticker}_*.infographic.json")))
    return files[-1] if files else None


def fail(errors: list):
    print(f"[validate-infographic] ✗ schema drift (expected {EXPECTED_VERSION}/{EXPECTED_KIND}):",
          file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker", nargs="?")
    ap.add_argument("--json", help="explicit infographic JSON path")
    args = ap.parse_args()

    if args.json:
        path = args.json
    else:
        if not args.ticker:
            sys.exit("Usage: validate_infographic.py <TICKER>  (or --json <path>)")
        path = find_infographic(args.ticker.upper())
        if not path:
            fail([f"no infographic.json for {args.ticker} under {CACHE_DIR}"])

    with open(path) as f:
        d = json.load(f)

    errors = []

    # 1. Top-level keys
    for k in TOP_REQUIRED:
        if k not in d:
            errors.append(f"missing top-level key: {k}")

    # 2. Schema version + kind
    if d.get("schema_version") != EXPECTED_VERSION:
        errors.append(f"schema_version = {d.get('schema_version')!r}, expected {EXPECTED_VERSION!r}")
    if d.get("schema_kind") != EXPECTED_KIND:
        errors.append(f"schema_kind = {d.get('schema_kind')!r}, expected {EXPECTED_KIND!r}")

    # 3. headline_oneliner is non-empty string
    hl = d.get("headline_oneliner")
    if not isinstance(hl, str) or not hl.strip():
        errors.append("headline_oneliner must be non-empty string")

    # 4. surprise block
    sp = d.get("surprise") or {}
    for k in SURPRISE_REQUIRED:
        if k not in sp:
            errors.append(f"surprise missing {k}")
    if isinstance(sp.get("revenue_beat"), bool) is False:
        errors.append(f"surprise.revenue_beat must be bool (got {type(sp.get('revenue_beat')).__name__})")
    if isinstance(sp.get("eps_beat"), bool) is False:
        errors.append(f"surprise.eps_beat must be bool (got {type(sp.get('eps_beat')).__name__})")

    # 5. segments_q (always required) + geographic_q (optional)
    seg = d.get("segments_q") or {}
    for k in SEGMENT_REQUIRED:
        if k not in seg:
            errors.append(f"segments_q missing {k}")
    items = seg.get("items") or []
    if not isinstance(items, list) or not items:
        errors.append(f"segments_q.items must be non-empty list (got {len(items) if isinstance(items, list) else 0})")
    else:
        for i, it in enumerate(items):
            for k in ITEM_REQUIRED:
                if k not in it:
                    errors.append(f"segments_q.items[{i}] missing {k}")

    geo = d.get("geographic_q")
    if geo is not None:
        if "items" not in geo:
            errors.append("geographic_q present but missing 'items'")

    # 6. capital_returns block
    cap = d.get("capital_returns") or {}
    for k in CAPITAL_REQUIRED:
        if k not in cap:
            errors.append(f"capital_returns missing {k}")
    if not isinstance(cap.get("announcements"), list):
        errors.append(f"capital_returns.announcements must be list")

    # 7. ceo_quote — required only when transcript_used
    if d.get("transcript_used") is True:
        cq = d.get("ceo_quote") or {}
        for k in CEO_QUOTE_REQUIRED:
            if k not in cq:
                errors.append(f"ceo_quote missing {k} (transcript_used=true)")

    # 8. key_highlights ≥ 3, summary ≥ 2
    kh = d.get("key_highlights") or []
    if not isinstance(kh, list) or len(kh) < HIGHLIGHT_MIN:
        errors.append(f"key_highlights must have ≥ {HIGHLIGHT_MIN} items (got {len(kh) if isinstance(kh, list) else 0})")
    else:
        for i, h in enumerate(kh):
            if not (isinstance(h, dict) and h.get("title") and h.get("body")):
                errors.append(f"key_highlights[{i}] missing title/body")

    sm = d.get("summary") or []
    if not isinstance(sm, list) or len(sm) < SUMMARY_MIN:
        errors.append(f"summary must have ≥ {SUMMARY_MIN} items (got {len(sm) if isinstance(sm, list) else 0})")

    # 9. ticker / dates non-empty
    for k in ("ticker", "as_of_date", "last_earnings_date", "fiscal_label"):
        v = d.get(k)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"{k} must be non-empty string")

    if errors:
        fail(errors)

    transcript_marker = "✓ transcript" if d.get("transcript_used") else "○ no-transcript"
    fy_marker = " (FY fallback)" if seg.get("is_fy_fallback") else ""
    print(f"[validate-infographic] ✓ {EXPECTED_VERSION} compliant — {d['ticker']} "
          f"{d.get('fiscal_label','')} {transcript_marker} "
          f"segs={len(items)}{fy_marker} highlights={len(kh)} summary={len(sm)}")
    return 0


if __name__ == "__main__":
    main()

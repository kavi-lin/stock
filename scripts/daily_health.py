#!/usr/bin/env python3
"""Daily data-source health check (V4.65.0, 0 LLM).

Checks artifact freshness (existence + mtime age) for every data source the
daily pipeline and protocols depend on. Catches silent SOFT fails: a step that
"succeeds" while downstream keeps reading a stale cache still shows up here,
because the artifact stops getting newer.

Usage:
    python3 scripts/daily_health.py            # table, always rc=0 (informational)
    python3 scripts/daily_health.py --strict   # rc=1 if any FAIL
    python3 scripts/daily_health.py --json     # machine-readable output

Called at the end of daily_update.sh. Thresholds are per-source below —
`max_age_hours` is "expected refresh cadence + slack"; age beyond 3x that
(or a missing artifact) is FAIL.
"""
import argparse
import glob
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# kind: "auto" = daily_update.sh should refresh it every run (stale ⇒ pipeline
# problem). "manual" = refreshed by a user-triggered protocol; never FAIL,
# only informational age (INFO/WARN) so a forgotten weekly run is visible.
SOURCES = [
    # Phase 1
    {"name": "breadth (TraderMonty)", "glob": "sector/breadth_cache/market_breadth_*.json", "max_age_hours": 30, "kind": "auto"},
    {"name": "FTD detector",          "glob": "sector/ftd_cache/ftd_detector_*.json",       "max_age_hours": 30, "kind": "auto"},
    {"name": "market-top detector",   "glob": "sector/market_top_cache/market_top_*.json",  "max_age_hours": 30, "kind": "auto"},
    {"name": "FRED macro",            "glob": "skills/fred-macro/cache/fred_latest.json",   "max_age_hours": 30, "kind": "auto"},
    # Bridge
    {"name": "Dashboard data.json",   "glob": "Dashboard/data.json",                        "max_age_hours": 30, "kind": "auto"},
    # Phase 2A
    {"name": "thematic recommendations", "glob": "skills/thematic-screener/data/recommendations/*.json", "max_age_hours": 30, "kind": "auto"},
    {"name": "momentum screen CSV",   "glob": "skills/momentum-monitor/cache/screen_*.csv", "max_age_hours": 30, "kind": "auto"},
    # Phase 2B
    {"name": "structural watchlist",  "glob": "news/news_logs/structural_watchlist.json",   "max_age_hours": 30, "kind": "auto"},
    {"name": "Nexus graph",           "glob": "Dashboard/nexus_graph.json",                 "max_age_hours": 30, "kind": "auto"},
    {"name": "market mood",           "glob": "Dashboard/market_mood.json",                 "max_age_hours": 30, "kind": "auto"},
    {"name": "intraday mood",         "glob": "Dashboard/intraday_mood.json",               "max_age_hours": 30, "kind": "auto"},
    {"name": "trending tickers",      "glob": "Dashboard/trending_tickers.json",            "max_age_hours": 30, "kind": "auto"},
    {"name": "retail sector pulse",   "glob": "Dashboard/retail_sector_pulse.json",         "max_age_hours": 30, "kind": "auto"},
    {"name": "kill triggers",         "glob": "Dashboard/kill_triggers.json",               "max_age_hours": 30, "kind": "auto"},
    # Manual / protocol-cadence sources (informational only)
    {"name": "theme-detector cache（產業掃描）", "glob": "skills/theme-detector/cache/theme_detector_*.json", "max_age_hours": 168, "kind": "manual"},
    {"name": "news digest（新聞分析）",          "glob": "news/news_logs/*_digest.json",                      "max_age_hours": 72,  "kind": "manual"},
    {"name": "economic calendar（已知上游 403）", "glob": "skills/economic-calendar-fetcher/cache/*.json",     "max_age_hours": 168, "kind": "manual"},
]


def check(src):
    paths = glob.glob(os.path.join(ROOT, src["glob"]))
    if not paths:
        return {"name": src["name"], "kind": src["kind"], "status": "FAIL" if src["kind"] == "auto" else "MISS",
                "age_hours": None, "artifact": None}
    newest = max(paths, key=os.path.getmtime)
    age_h = (time.time() - os.path.getmtime(newest)) / 3600.0
    if age_h <= src["max_age_hours"]:
        status = "OK"
    elif age_h <= 3 * src["max_age_hours"]:
        status = "WARN"
    else:
        status = "FAIL" if src["kind"] == "auto" else "WARN"
    return {"name": src["name"], "kind": src["kind"], "status": status,
            "age_hours": round(age_h, 1), "artifact": os.path.relpath(newest, ROOT)}


def fmt_age(h):
    if h is None:
        return "—"
    return f"{h:.0f}h" if h < 48 else f"{h / 24:.1f}d"


ICON = {"OK": "✅", "WARN": "⚠️ ", "FAIL": "❌", "MISS": "∅ "}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="rc=1 if any auto source FAILs")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    results = [check(s) for s in SOURCES]
    counts = {k: sum(1 for r in results if r["status"] == k) for k in ("OK", "WARN", "FAIL", "MISS")}

    if args.json:
        print(json.dumps({"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                          "summary": counts, "sources": results}, ensure_ascii=False, indent=2))
    else:
        print("── 資料源健康檢查 ──────────────────────────────────────")
        for r in results:
            tag = "" if r["kind"] == "auto" else "（手動節奏）"
            print(f" {ICON[r['status']]} {r['status']:<4} {fmt_age(r['age_hours']):>6}  {r['name']}{tag}"
                  + (f"  → {r['artifact']}" if r["status"] != "OK" and r["artifact"] else "")
                  + ("  → artifact 不存在" if r["artifact"] is None else ""))
        print(f"── HEALTH: {counts['OK']} OK / {counts['WARN']} WARN / {counts['FAIL']} FAIL / {counts['MISS']} 從未產出 ──")
        if counts["FAIL"] or counts["WARN"]:
            print("   ⚠️  WARN/FAIL = 該源的最新 artifact 已超齡：對應 step 可能連續失敗中，")
            print("      下游正在沿用舊 cache（silent SOFT fail）。回看上方對應 step log。")

    if args.strict and counts["FAIL"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

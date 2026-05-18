#!/usr/bin/env python3
"""Render reports/2026-05-07_news_digest.md from digest.json + triage.json.

3 sections per protocol:
  1. Triage Summary (one-line per item, all 37 with DEEP/SKIP)
  2. Deep Analysis (5 deep Impact Cards)
  3. Shallow Digest (top-20 shallow snaps)
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent.parent
DIGEST = ROOT / "news/news_logs/2026-05-07_digest.json"
TRIAGE = ROOT / "news/news_logs/2026-05-07_triage.json"
PHASE0 = ROOT / "sector/sector_logs/phase0.json"
OUT = ROOT / "reports/2026-05-07_news_digest.md"

d = json.load(open(DIGEST))
t = json.load(open(TRIAGE))
p0 = json.load(open(PHASE0))

deep = [v for v in d["verdicts"] if v["depth"] == "deep"]
deep_by_id = {v["news_id"]: v for v in deep}
all_shallow = t["shallow_verdicts"]  # 37 sorted by |score| desc

lines = []
lines.append(f"# News Digest — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
lines.append("")
lines.append(f"**Mode**: DIGEST | **Stage 1**: {d['stage1_count']} shallow → **Stage 2**: {d['stage2_count']} deep | **fanout_mode**: {d['fanout_mode']}")
lines.append(f"**Session macro Δ**: {d['session_macro_delta']:+.2f} | **Updated phase0 macro_backdrop_score**: {p0['macro_backdrop_score']:+.2f}")
lines.append(f"**Sources**: 4 (RSS · Finnhub · FMP · SEC EDGAR) | **Raw items**: {t['raw_count']} → after dedupe {t['after_dedupe']}")
lines.append("")
lines.append("---")
lines.append("")

# ── 1. Triage Summary ──
lines.append("## 1. Triage Summary")
lines.append("")
lines.append("| status | id | score | type | source | published | headline |")
lines.append("|---|---|---|---|---|---|---|")
for v in all_shallow:
    flag = "✅ DEEP" if v["advance_to_stage2"] else "❌ SKIP"
    extra = " (BINARY)" if v["binary_flag"] else ""
    pub = (v["published"] or "")[:16].replace("T", " ")
    headline = v["headline"].replace("|", "│")[:90]
    lines.append(f"| {flag}{extra} | `{v['news_id']}` | {v['shallow_score']:+.1f} | {v['news_type']} | {v['source']} ({v['source_credibility']}) | {pub} | [{headline}]({v['url']}) |")
lines.append("")
lines.append("---")
lines.append("")

# ── 2. Deep Analysis Impact Cards ──
lines.append("## 2. Deep Analysis (Stage 2)")
lines.append("")
for dv in deep:
    pub = (dv["published"] or "")[:16].replace("T", " ")
    verdict_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "BINARY": "⚠️", "NEUTRAL": "⚪"}.get(dv["verdict"], "")
    lines.append(f"### {verdict_emoji} `{dv['news_id']}` [{dv['verdict']} {dv['net_impact_score']:+.1f}] — {dv['headline']}")
    lines.append("")
    lines.append(f"- **Source**: [{dv['source_label']}]({dv['url']}) ({dv['source_credibility']}) | **Published**: {pub} | **type**: {dv['news_type']}")
    w = dv["weights_used"]
    lines.append(f"- **Weights**: Bull {int(w['bull']*100)}% / Bear {int(w['bear']*100)}% / Sector {int(w['sector']*100)}% / Macro {int(w['macro']*100)}%")
    if dv["binary_risk"]:
        lines.append(f"- **⚠️ Binary risk**: event_date={dv['binary_event_date']}, within_48h={dv['within_48h']}")
    lines.append("")
    lines.append(f"**🟢 BULL** — {dv['bull_case']}")
    lines.append("")
    lines.append(f"**🔴 BEAR** — {dv['bear_case']}")
    lines.append("")
    lines.append(f"**🏭 SECTOR** — {dv['sector_view']}")
    lines.append("")
    lines.append(f"**🌐 MACRO** — {dv['macro_view']}")
    lines.append("")
    lines.append(f"**🧭 ARBITER** — {dv['arbiter_reasoning']}")
    lines.append("")
    lines.append(f"**🔍 Debate** — {dv['debate_note']}")
    lines.append("")
    sectors_str = ", ".join(f"{s['sector']} ({s['direction']})" for s in dv["affected_sectors"])
    lines.append(f"**Affected sectors**: {sectors_str}")
    lines.append(f"**Tickers**: {', '.join(dv['tickers_mentioned'])}")
    lines.append("")
    lines.append("---")
    lines.append("")

# ── 3. Shallow Digest top 20 ──
lines.append("## 3. Shallow Digest (Top 20 not advancing)")
lines.append("")
shallow_only = [v for v in all_shallow if not v["advance_to_stage2"]][:20]
for v in shallow_only:
    pub = (v["published"] or "")[:16].replace("T", " ")
    extra = " ⚠️ BINARY" if v["binary_flag"] else ""
    lines.append(f"### [{v['shallow_score']:+.1f}]{extra} `{v['news_id']}` — {v['headline']}")
    lines.append(f"- **🟢 Bull**: {v['bull_case']}")
    lines.append(f"- **🔴 Bear**: {v['bear_case']}")
    lines.append(f"- **🏭 Sector**: {v['sector_view']}")
    lines.append(f"- **🌐 Macro**: {v['macro_view']}")
    lines.append(f"- Source: [{v['source']}]({v['url']}) ({v['source_credibility']}) │ type: {v['news_type']} │ {pub}")
    lines.append("")
    lines.append("---")
    lines.append("")

# ── Footer: Cache patch summary ──
lines.append("## 4. Cache Patches Applied")
lines.append("")
lines.append(f"- ✅ `news_logs/2026-05-07_digest.json` (V2.1 schema, validator rc=0)")
lines.append(f"- ✅ `sector/sector_logs/2026-05-07_sector_intel.json` (top_catalysts prepended {len(deep)} 則)")
lines.append(f"- ✅ `sector/sector_logs/phase0.json` (macro_backdrop_score → {p0['macro_backdrop_score']:+.2f}; binary_risks={len(p0['binary_risks'])})")
lines.append("")
lines.append("**Phase 0 binary_risks active:**")
for r in p0["binary_risks"]:
    badge = " (within_48h)" if r.get("within_48h") else ""
    lines.append(f"- {r['category']}{badge}: {r['event']} (expires {r.get('expires','?')})")

OUT.write_text("\n".join(lines))
print(f"WROTE {OUT}  size={OUT.stat().st_size}B  ({len(lines)} lines)")

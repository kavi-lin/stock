#!/usr/bin/env python3
"""
Salvage a partial DIGEST run from its scan_logs stream-json log when the
Claude API drops the connection at Phase 4 (the "Stream idle timeout" failure
mode where all 4 Stage-2 subagents completed but the final digest.json write
never materialised).

Inputs : latest news/scan_logs/news_YYYYMMDD_HHMMSS.log
         today's news/news_logs/YYYY-MM-DD_raw.json (for headline_zh / sources)
Output : news/news_logs/YYYY-MM-DD_digest.json (5 deep verdicts only; shallow
         entries are skipped because Claude never produced per-item
         bull_case/bear_case/sector_view/macro_view for the non-promoted 31
         items — those live only inside encrypted thinking blocks).

Arbiter weights follow news_protocol_v2.md §動態調整:
    monetary_policy / macro_data : Bull 15 Bear 15 Sector 20 Macro 50
    geopolitical                 : Bull 15 Bear 30 Sector 15 Macro 40
    earnings / corporate         : Bull 25 Bear 25 Sector 40 Macro 10
    sector_news                  : Bull 20 Bear 20 Sector 50 Macro 10
    sentiment                    : Bull 30 Bear 30 Sector 15 Macro 25
    default                      : Bull 25 Bear 25 Sector 25 Macro 25

Usage:
    python3 news/scripts/salvage_digest.py                 # auto-latest log
    python3 news/scripts/salvage_digest.py path/to/log     # specific log
"""
import glob
import json
import os
import re
import sys
from datetime import date, datetime

ROOT      = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCAN_DIR  = os.path.join(ROOT, "news/scan_logs")
LOGS_DIR  = os.path.join(ROOT, "news/news_logs")

AGENT_NAMES = ("Bull_Analyst", "Bear_Analyst", "Sector_Analyst", "Macro_Analyst")

WEIGHTS = {
    "monetary_policy": {"bull": 0.15, "bear": 0.15, "sector": 0.20, "macro": 0.50},
    "macro_data":      {"bull": 0.15, "bear": 0.15, "sector": 0.20, "macro": 0.50},
    "geopolitical":    {"bull": 0.15, "bear": 0.30, "sector": 0.15, "macro": 0.40},
    "earnings":        {"bull": 0.25, "bear": 0.25, "sector": 0.40, "macro": 0.10},
    "corporate":       {"bull": 0.25, "bear": 0.25, "sector": 0.40, "macro": 0.10},
    "sector_news":     {"bull": 0.20, "bear": 0.20, "sector": 0.50, "macro": 0.10},
    "sentiment":       {"bull": 0.30, "bear": 0.30, "sector": 0.15, "macro": 0.25},
    "default":         {"bull": 0.25, "bear": 0.25, "sector": 0.25, "macro": 0.25},
}


def strip_trailing_junk(s: str) -> str:
    """Subagent tool_results have trailing '} agentId: ... <usage>...'.
    Slice off after the outermost matching '}' to get clean JSON."""
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(s):
        if esc: esc = False; continue
        if ch == "\\": esc = True; continue
        if ch == '"': in_str = not in_str; continue
        if in_str: continue
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[: i + 1]
    return s


def extract_from_log(log_path):
    """Walk stream-json log, return (agents_dict, triage_text)."""
    agents = {}
    triage_text = ""
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue

            if obj.get("type") == "user":
                msg = obj.get("message", {}) or {}
                for c in msg.get("content", []) or []:
                    if not (isinstance(c, dict) and c.get("type") == "tool_result"):
                        continue
                    text = c.get("content", "")
                    if isinstance(text, list):
                        text = " ".join(
                            x.get("text", "") for x in text if isinstance(x, dict)
                        )
                    if not isinstance(text, str):
                        continue
                    # Pattern-match subagent output shape
                    for name in AGENT_NAMES:
                        if f'"agent": "{name}"' in text or f'"agent":"{name}"' in text:
                            clean = strip_trailing_junk(text.strip())
                            try:
                                agents[name] = json.loads(clean)
                            except Exception as e:
                                print(f"  [warn] failed to parse {name}: {e}", file=sys.stderr)
                            break
            elif obj.get("type") == "assistant":
                msg = obj.get("message", {}) or {}
                for c in msg.get("content", []) or []:
                    if isinstance(c, dict) and c.get("type") == "text":
                        t = c.get("text", "") or ""
                        if "NEWS TRIAGE" in t or "Stage 1 Triage" in t:
                            triage_text = t
    return agents, triage_text


def parse_triage(text):
    """Extract deep-promoted items from the Stage 1 triage table.
    Returns list of dicts: {news_id, shallow_score, headline_short, news_type, binary}."""
    items = []
    # Examples of the triage line format in assistant text:
    #   ║  ✅ DEEP   n009  [BINARY -3.5]  Hormuz traffic halts 48h  geopolitical║
    pattern = re.compile(
        r"✅\s*DEEP\s+(n\d+)\s+\[(BINARY\s+)?([-+]?\d+(?:\.\d+)?)\]\s+(.+?)\s+(\w+)\s*║"
    )
    for m in pattern.finditer(text):
        items.append({
            "news_id":        m.group(1),
            "binary":         bool(m.group(2)),
            "shallow_score":  float(m.group(3)),
            "headline_short": m.group(4).strip(),
            "news_type":      m.group(5).strip().lower(),
        })
    return items


def load_raw(today_str):
    path = os.path.join(LOGS_DIR, f"{today_str}_raw.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_raw_item(raw, news_id):
    """news_id in the triage is 'n001'..; match by order index in raw.items[]."""
    if not raw:
        return None
    try:
        idx = int(news_id.lstrip("n")) - 1
        items = raw.get("items") or raw.get("news") or []
        if 0 <= idx < len(items):
            return items[idx]
    except Exception:
        pass
    return None


def first_sentence(s, limit=60):
    """30-char-ish one-liner extraction for bull_case/bear_case/etc."""
    if not s:
        return "(n/a)"
    s = s.strip()
    # Cut at first Chinese full-stop / period / semicolon
    for stop in ("。", ". ", "；", "; ", "，"):
        idx = s.find(stop)
        if 10 <= idx <= limit:
            return s[:idx].strip()
    return s[:limit].strip() + ("…" if len(s) > limit else "")


def classify_verdict(score, binary_flag):
    if binary_flag:
        return "BINARY"
    if score >= 1.5:
        return "BULLISH"
    if score <= -1.5:
        return "BEARISH"
    return "NEUTRAL"


def build_deep_verdicts(triage_items, agents, raw):
    verdicts = []
    for t in triage_items:
        nid = t["news_id"]
        nt = t["news_type"]
        w = WEIGHTS.get(nt, WEIGHTS["default"])

        def score(agent):
            rec = (agents.get(agent, {}).get("per_item") or {}).get(nid) or {}
            s = rec.get("impact_score")
            return 0.0 if s is None else float(s)

        bull_s   = score("Bull_Analyst")
        bear_s   = score("Bear_Analyst")
        sector_s = score("Sector_Analyst")
        macro_s  = score("Macro_Analyst")
        net = round(
            bull_s * w["bull"]
            + bear_s * w["bear"]
            + sector_s * w["sector"]
            + macro_s * w["macro"],
            1,
        )
        binary_flag = t["binary"] or (abs(net) >= 3.0 and nt in ("geopolitical", "monetary_policy"))
        verdict = classify_verdict(net, binary_flag)

        # Interpretations → 30-char summaries
        def interp(agent):
            rec = (agents.get(agent, {}).get("per_item") or {}).get(nid) or {}
            return first_sentence(rec.get("interpretation", ""))

        # Sector_Analyst tickers + sectors
        sec_rec = (agents.get("Sector_Analyst", {}).get("per_item") or {}).get(nid) or {}
        tickers = sec_rec.get("tickers_mentioned") or []
        primary_sectors = sec_rec.get("primary_sectors") or []
        affected = []
        for ps in primary_sectors:
            if isinstance(ps, dict):
                affected.append({
                    "sector":    ps.get("sector", "Unknown"),
                    "direction": ps.get("direction", "bullish" if net >= 0 else "bearish"),
                    "magnitude": ps.get("magnitude", "moderate"),
                })
            elif isinstance(ps, str):
                affected.append({
                    "sector":    ps,
                    "direction": "bullish" if net >= 0 else "bearish",
                    "magnitude": "moderate",
                })

        raw_item = find_raw_item(raw, nid) or {}
        headline    = raw_item.get("headline") or raw_item.get("title") or t["headline_short"]
        headline_zh = raw_item.get("headline_zh") or headline
        source      = raw_item.get("source") or raw_item.get("source_label") or "RSS"

        debate_note = (
            f"Score dispersion Bull {bull_s:+.1f} / Bear {bear_s:+.1f} / "
            f"Sector {sector_s:+.1f} / Macro {macro_s:+.1f}; "
            f"weights {nt} → net {net:+.1f}"
        )
        arbiter_reasoning = (
            f"Weighted per news_type={nt} "
            f"(B {w['bull']:.2f}·{bull_s:+.1f} + Br {w['bear']:.2f}·{bear_s:+.1f} + "
            f"S {w['sector']:.2f}·{sector_s:+.1f} + M {w['macro']:.2f}·{macro_s:+.1f}) = {net:+.1f}. "
            f"Verdict {verdict}. [salvaged from subagent outputs; Phase 4 write was "
            f"interrupted by API stream idle timeout]"
        )

        verdicts.append({
            "news_id":           nid,
            "depth":             "deep",
            "review_status":     "reviewed",
            "headline":          headline,
            "headline_zh":       headline_zh,
            "source_label":      source,
            "news_type":         nt,
            "bull_case":         interp("Bull_Analyst"),
            "bear_case":         interp("Bear_Analyst"),
            "sector_view":       interp("Sector_Analyst"),
            "macro_view":        interp("Macro_Analyst"),
            "verdict":           verdict,
            "net_impact_score":  net,
            "arbiter_reasoning": arbiter_reasoning,
            "debate_note":       debate_note,
            "binary_risk":       binary_flag,
            "binary_event_date": raw_item.get("binary_event_date"),
            "within_48h":        binary_flag and nt == "geopolitical",
            "cache_updated":     True,
            "affected_sectors":  affected,
            "tickers_mentioned": tickers,
            "subagent_isolated": True,
            "agent_acceptance": {
                "bull":   "full",
                "bear":   "full",
                "sector": "full",
                "macro":  "full",
            },
            "weights_used":      {k: w[k] for k in ("bull", "bear", "sector", "macro")},
            "macro_backdrop_delta": round(macro_s * 0.1, 2),
        })
    return verdicts


def latest_scan_log():
    files = sorted(glob.glob(os.path.join(SCAN_DIR, "news_*.log")))
    return files[-1] if files else None


def main():
    log_path = sys.argv[1] if len(sys.argv) > 1 else latest_scan_log()
    if not log_path or not os.path.exists(log_path):
        print("No scan log found.", file=sys.stderr); sys.exit(2)
    print(f"[salvage] reading {log_path}")

    agents, triage_text = extract_from_log(log_path)
    missing = [a for a in AGENT_NAMES if a not in agents]
    if missing:
        print(f"[salvage] ✗ missing subagent outputs: {missing}", file=sys.stderr); sys.exit(2)
    if not triage_text:
        print("[salvage] ✗ no triage table found in log", file=sys.stderr); sys.exit(2)

    triage_items = parse_triage(triage_text)
    if not triage_items:
        print("[salvage] ✗ triage table parsed 0 items", file=sys.stderr); sys.exit(2)
    print(f"[salvage] recovered {len(triage_items)} deep items: {[t['news_id'] for t in triage_items]}")

    today_str = date.today().isoformat()
    # Log filename tells us the scan date if it differs from today
    m = re.search(r"news_(\d{4})(\d{2})(\d{2})_", os.path.basename(log_path))
    if m:
        today_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    raw = load_raw(today_str)
    if raw is None:
        print(f"[salvage] warn: no raw.json for {today_str}; headlines will be short-form", file=sys.stderr)

    verdicts = build_deep_verdicts(triage_items, agents, raw)

    # Aggregate session macro delta from Macro_Analyst scores
    macro_scores = []
    for t in triage_items:
        rec = (agents.get("Macro_Analyst", {}).get("per_item") or {}).get(t["news_id"]) or {}
        s = rec.get("impact_score")
        if s is not None:
            macro_scores.append(float(s))
    session_macro_delta = round(sum(macro_scores) / (len(macro_scores) * 5), 2) if macro_scores else 0.0

    digest = {
        "timestamp":         datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mode":              "DIGEST",
        "protocol_version":  "V2.1",
        "stage1_count":      len(verdicts),  # salvaged scope = deep only
        "stage2_count":      len(verdicts),
        "fanout_mode":       "PER_AGENT_BATCH",
        "degraded_agents":   [],
        "salvaged":          True,
        "salvage_source":    os.path.basename(log_path),
        "salvage_note":      ("Phase 4 write interrupted by API stream idle timeout. "
                              "5 deep verdicts rebuilt from Stage 2 subagent outputs. "
                              "Shallow verdicts skipped (Claude never emitted the per-item "
                              "4-view strings for non-promoted items in plaintext)."),
        "verdicts":          verdicts,
        "session_macro_delta": session_macro_delta,
    }

    out_path = os.path.join(LOGS_DIR, f"{today_str}_digest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)
    print(f"[salvage] ✓ wrote {out_path}")
    print(f"[salvage]   verdicts: {[(v['news_id'], v['verdict'], v['net_impact_score']) for v in verdicts]}")
    print(f"[salvage]   session_macro_delta: {session_macro_delta}")
    print(f"[salvage] next: run news/scripts/validate_digest_output.py then bridge.py")


if __name__ == "__main__":
    main()

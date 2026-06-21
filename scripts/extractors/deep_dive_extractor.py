"""Extract decision snapshot from V4.x deep-dive markdown reports.

V4 reports vary slightly across versions (V4.4, V4.6, V4.8). Extractor uses
lenient regex over section headers; missing fields default to None.
"""
from __future__ import annotations
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from _sector_heat import enrich_ticker_heat                              # type: ignore
except Exception:                                                            # pragma: no cover
    enrich_ticker_heat = None                                                # type: ignore

FILENAME_RE = re.compile(r"(\d{8})_([A-Z][A-Z0-9]+)")

# Repo root for cross-file Phase 0 cache lookup (Codex review #4).
# Does NOT depend on cwd — pytest monkeypatch.chdir 不會干擾 build_event_index 行為。
ROOT = Path(__file__).resolve().parents[2]


def _parse_filename(path: Path) -> tuple[str | None, str | None]:
    m = FILENAME_RE.match(path.stem)
    if not m:
        return None, None
    yyyymmdd, ticker = m.group(1), m.group(2)
    decision_date = f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"
    return decision_date, ticker


def _find_final_score(text: str) -> float | None:
    # V5.0 / V4.8 / V4.x 多版本：JSON / "Final Score" 表頭 / 表格範本
    patterns = [
        r"\"final_score\"\s*:\s*([+-]?\d+\.?\d*)",
        # V5.0 explicit table row: | **Final Score** | 0.462 / 3.0 |
        r"\|\s*\*\*Final Score\*\*\s*\|\s*([+\-]?\d+\.?\d*)",
        r"Final Score[*:\s|]*\**\s*([+-]?\d+\.?\d*)",
        r"\*\*Final\*\*[^|]*\|[^|]*\|\s*\*\*([+-]?\d+\.?\d*)\*\*",
        # V4.x body forms: "final_score 0.558", "Phase 3 final score**：1.175"
        # — case-insensitive, accepts both ASCII and full-width colon.
        r"(?i)final[_ ]score\**[\s:：|]+\**\s*([+\-]?\d+\.?\d*)",
        # V4.x table cell: | final score | 2.055 |
        r"(?i)\|\s*final score\s*\|\s*([+\-]?\d+\.?\d*)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


_DECISION_ROW_FINAL = re.compile(
    # Row label may or may not be bold-wrapped (NVDA report omits **).
    # Group 1 = verb. Group 2 = paren modifier (optional).
    r"\|\s*(?:\*\*)?(?:Final Decision|最終決議)(?:\*\*)?\s*\|\s*\**\s*"
    r"([A-Z_]+)(?:\s*\(([^)]+?)\))?",
)
_DECISION_ROW_ACTION = re.compile(
    r"\|\s*(?:\*\*)?Final Action(?:\*\*)?\s*\|\s*\**\s*([A-Z_]+)",
)
_DECISION_ROW_ACTION_LABEL = re.compile(
    r"\|\s*(?:\*\*)?Action Label(?:\*\*)?\s*\|\s*\**\s*([A-Z_]+)",
)


def _find_decision(text: str) -> tuple[str | None, str | None]:
    """V4.x + V5.0 decision extractor — returns (verb, modifier).

    V5.0 reports can have up to **three** related rows in the summary table
    (observed in reports/20260510_MU.md):
        | Final Decision | HOLD |
        | Final Action   | CANCEL |
        | Action Label   | DEFENSIVE |
    Earlier reports collapse all of this into one row:
        | **Final Decision** | **HOLD (DEFENSIVE)** |
    Codex round-2 review caught the multi-row case — the old single-regex
    early-return missed Final Action / Action Label entirely, defeating the
    HOLD-vs-HOLD+CANCEL distinction.

    Modifier priority (most specific verb override wins):
        1. paren content in Final Decision row  → "HOLD (DEFENSIVE)" → DEFENSIVE
        2. Final Action row (secondary verb)    → CANCEL / EXECUTE / WAIT
        3. Action Label row (flavor tag)        → DEFENSIVE / OFFENSIVE / NEUTRAL
    """
    verb = None
    paren_modifier = None
    final_action = None
    action_label = None

    # 1) V5.0 primary "Final Decision" row (+ paren modifier if present)
    m = _DECISION_ROW_FINAL.search(text)
    if m:
        verb = m.group(1).strip().split("(")[0].strip() or None
        if m.group(2):
            paren_modifier = _normalize_modifier(m.group(2))

    # 2) V5.0 secondary "Final Action" row (CANCEL / EXECUTE / WAIT / etc)
    m = _DECISION_ROW_ACTION.search(text)
    if m:
        final_action = m.group(1).strip() or None

    # 3) V5.0 tertiary "Action Label" row (flavor tag)
    m = _DECISION_ROW_ACTION_LABEL.search(text)
    if m:
        action_label = m.group(1).strip() or None

    if verb:
        # Prefer most specific modifier (paren > Final Action > Action Label)
        modifier = paren_modifier or final_action or action_label
        return (verb, modifier)

    # Legacy fallback chain — JSON forms / older V4 bolded row / inline verb
    for p in (
        r"\"decision\"\s*:\s*\"([A-Z_]+)\"",
        r"\"final_action\"\s*:\s*\"([A-Z_]+)\"",
        r"\*\*Action\*\*[:\s]*([A-Z_/() ]+?)[\n\|]",
        r"\| \*\*(BUY|HOLD|SELL|CANCEL|EXECUTE|STAGED_ENTRY|STAGED_EXIT)\*\* \|",
        r"\b(EXECUTE|STAGED_ENTRY|STAGED_EXIT)\b",
    ):
        m = re.search(p, text)
        if m:
            return (m.group(1).strip().split("(")[0].strip() or None, None)
    return (None, None)


_MODIFIER_TOKEN_RE = re.compile(r"[A-Z][A-Z_]{1,}")


def _normalize_modifier(raw: str) -> str | None:
    """Extract action_label token from paren modifier text.

    Format variants observed in V5.0 reports:
        "DEFENSIVE"                                                       → DEFENSIVE
        "CANCEL — 不建倉"                                                   → CANCEL
        "action_label: **WAIT** — Burry WARNING + binary earnings 9d …"  → WAIT
        "Auto REJECT"                                                     → REJECT  (GLW; Codex round-2)
        "flag: NEUTRAL"                                                   → NEUTRAL

    Strategy: drop key prefix on `:`, strip bold/whitespace, then return the
    FIRST ALL-CAPS token (≥2 chars). Skips title-case noise like "Auto" so
    downstream buckets stay clean (Codex round-2 review #3).
    """
    s = raw.strip()
    if ":" in s:
        s = s.split(":", 1)[1].strip()
    s = s.replace("*", "")
    # First ALL-CAPS token (filters title-case prefixes like "Auto", "Forward")
    m = _MODIFIER_TOKEN_RE.search(s)
    return m.group(0) if m else None


def _find_position_size(text: str) -> float | None:
    m = re.search(r"\"position_size\"\s*:\s*([0-9.]+)", text)
    if m:
        return float(m.group(1))
    m = re.search(r"Position Size[\s|]+\**([0-9.]+)%?", text)
    if m:
        try:
            return float(m.group(1)) / 100.0
        except ValueError:
            pass
    return None


def _find_trader_proposal(text: str) -> dict | None:
    """Phase 4 trader 提案 entry/TP/SL — JSON 格式優先, 表格次之."""
    # JSON
    m = re.search(
        r'"entry_price"\s*:\s*([\d.]+)[^}]*?"take_profit"\s*:\s*([\d.]+)[^}]*?"stop_loss"\s*:\s*([\d.]+)',
        text, re.DOTALL)
    if m:
        return {"entry": float(m.group(1)), "tp": float(m.group(2)), "sl": float(m.group(3))}

    # Markdown table forms vary; try entry/SL/TP keywords
    entry = re.search(r"entry[:\s]*\$?([\d.]+)", text, re.IGNORECASE)
    tp = re.search(r"(?:take[_ ]?profit|TP)[:\s]*\$?([\d.]+)", text, re.IGNORECASE)
    sl = re.search(r"(?:stop[_ ]?loss|SL)[:\s]*\$?([\d.]+)", text, re.IGNORECASE)
    if entry or tp or sl:
        return {
            "entry": float(entry.group(1)) if entry else None,
            "tp":    float(tp.group(1))    if tp    else None,
            "sl":    float(sl.group(1))    if sl    else None,
        }
    return None


# V5.0 Final Visualization Table — table row 是 confidence 的權威來源。
# 樣本 (across verified V5 reports — NOK / GOOGL / MU / NVDA / MU-20260510):
#   "| Fundamentals | HOLD | -1.5 | 0.70 | MISALIGNED |"          (NOK)
#   "| Fundamentals | BUY | 3.0 | 0.78 | 25% |"                    (GOOGL — Conf col, Weight col)
#   "| Valuation Specialist | SELL | -3 | 0.55 | NEUTRAL |"        (MU — "Specialist" 後綴)
#   "| L5 Valuation Specialist | BUY | +1 | 0.70 | NEUTRAL |"      (NVDA — L\d+ prefix)
#   "| Fundamentals | BUY | 4 (capped +3) | 0.82 | …"              (MU 20260510 — trailing paren)
# 容忍: L\d+ prefix / Specialist 後綴 / score ±decimal / "(capped +3)" 等 trailing
# 註記 / Conf 或 Confidence column。
# Score cell uses `[^|]*?` after the number to absorb annotation like "(capped +3)"
# without breaking the column boundary (Codex round-2 review #2).
AGENT_TABLE_V50_RE = re.compile(
    r"\|\s*(?:L\d+\s+)?"
    r"(Fundamentals|Sentiment|News|Technical|Valuation)"
    r"(?:\s+Specialist)?\s*\|\s*"
    r"([A-Z_]+)\s*\|\s*"
    r"([+\-]?\d+(?:\.\d+)?)[^|]*?\|\s*"
    r"([\d.]+)\s*\|",
    re.IGNORECASE,
)

# V5.0 alternate table — Score|Signal column order (TSM 20260510 form):
# "| Fundamentals | 3 | BUY | 0.88 | Rev +35% / … |"
# Order detection by column header is too brittle — separate regex per layout is
# simpler and the priority chain dedupes via the seen-set.
AGENT_TABLE_V50_INV_RE = re.compile(
    r"\|\s*(?:L\d+\s+)?"
    r"(Fundamentals|Sentiment|News|Technical|Valuation)"
    r"(?:\s+Specialist)?\s*\|\s*"
    r"([+\-]?\d+(?:\.\d+)?)[^|]*?\|\s*"
    r"([A-Z_]+)\s*\|\s*"
    r"([\d.]+)\s*\|",
    re.IGNORECASE,
)

# V5.0 heading fallback — table 缺欄或解析失敗時仍能拿 signal/score.
# 樣本: "### Fundamentals — HOLD / -1.5"
# 此 form 無 confidence 欄 — agent dict 不填 confidence 欄(Codex review #2)。
AGENT_HEADING_V50_RE = re.compile(
    r"###\s+(Fundamentals|Sentiment|News|Technical|Valuation)\s*"
    r"[—\-]\s*([A-Z_]+)\s*/\s*([+\-]?\d+(?:\.\d+)?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# V5.0 alternate heading — Score-first inline form (TSM 20260510):
# "### Fundamentals — Score 3 | BUY | conf 0.88"
AGENT_HEADING_V50_SCORE_FIRST_RE = re.compile(
    r"###\s+(Fundamentals|Sentiment|News|Technical|Valuation)\s*"
    r"[—\-]\s*Score\s+([+\-]?\d+(?:\.\d+)?)\s*\|\s*"
    r"([A-Z_]+)\s*\|\s*conf\s+([\d.]+)",
    re.IGNORECASE,
)

# Match agent sections like "### Fundamentals · BUY +4.0 (0.82)" or
# "### Fundamentals Analyst — Signal: BUY | Score: +3 | Confidence: 0.75"
AGENT_RE_V46 = re.compile(
    r"###\s+(Fundamentals|Sentiment|News|Technical|Contrarian|Burry)\s*"
    r"(?:Analyst)?\s*[·•—\-]\s*"
    r"([A-Z_]+)\s*([+\-]?[\d.]+)\s*\(([\d.]+)\)",
    re.IGNORECASE)

AGENT_RE_V44 = re.compile(
    r"###\s+(Fundamentals|Sentiment|News|Technical|Contrarian|Burry)\s*"
    r"(?:Analyst)?[\s—\-]+"
    r"Signal[:\s]+([A-Z_]+)\s*\|\s*Score[:\s]+([+\-]?\d+)\s*\|\s*Confidence[:\s]+([\d.]+)",
    re.IGNORECASE)


AGENT_NAMES = ("Fundamentals", "Sentiment", "News", "Technical",
               "Valuation", "Contrarian", "Burry")
# Allow optional emoji / decoration prefix between ### and the agent name
AGENT_BLOCK_RE = re.compile(
    r"###\s+[^\n]*?(" + "|".join(AGENT_NAMES) + r")\s*(?:Analyst)?\s*\n+```json\s*\n(.*?)\n```",
    re.DOTALL | re.IGNORECASE)


def _find_agent_breakdown(text: str) -> list[dict]:
    """Priority chain (first hit per lane name wins):
        1. V5.0 Final Visualization Table (has real confidence)
        2. V5.0 heading fallback (signal/score only — no confidence injected)
        3. V4.6 inline format (legacy, has confidence)
        4. V4.4 inline pipe format (legacy, has confidence)
        5. V4.4 JSON-block format (legacy, has confidence)
    """
    agents: list[dict] = []
    seen: set[str] = set()

    # 1) V5.0 Final Visualization Table (Signal-Score order) — primary
    for m in AGENT_TABLE_V50_RE.finditer(text):
        name = m.group(1).title()
        if name in seen:
            continue
        seen.add(name)
        try:
            agents.append({
                "agent": name,
                "signal": m.group(2).upper(),
                "score": float(m.group(3)),
                "confidence": float(m.group(4)),
            })
        except ValueError:
            continue

    # 1b) V5.0 alternate table — Score-Signal column order (TSM form)
    for m in AGENT_TABLE_V50_INV_RE.finditer(text):
        name = m.group(1).title()
        if name in seen:
            continue
        seen.add(name)
        try:
            agents.append({
                "agent": name,
                "score": float(m.group(2)),
                "signal": m.group(3).upper(),
                "confidence": float(m.group(4)),
            })
        except ValueError:
            continue

    # 1c) V5.0 alternate heading — "### Lane — Score N | SIGNAL | conf X" (TSM form)
    for m in AGENT_HEADING_V50_SCORE_FIRST_RE.finditer(text):
        name = m.group(1).title()
        if name in seen:
            continue
        seen.add(name)
        try:
            agents.append({
                "agent": name,
                "score": float(m.group(2)),
                "signal": m.group(3).upper(),
                "confidence": float(m.group(4)),
            })
        except ValueError:
            continue

    # 2) V5.0 heading fallback (only fills lanes table missed; no confidence faked)
    for m in AGENT_HEADING_V50_RE.finditer(text):
        name = m.group(1).title()
        if name in seen:
            continue
        seen.add(name)
        try:
            agents.append({
                "agent": name,
                "signal": m.group(2).upper(),
                "score": float(m.group(3)),
                # confidence intentionally absent — heading has no source.
            })
        except ValueError:
            continue

    # 3) V4.6 inline format
    for m in AGENT_RE_V46.finditer(text):
        name = m.group(1).title()
        if name in seen:
            continue
        seen.add(name)
        try:
            agents.append({
                "agent": name,
                "signal": m.group(2).upper(),
                "score": float(m.group(3)),
                "confidence": float(m.group(4)),
            })
        except ValueError:
            continue

    # 4) V4.4 inline pipe format
    for m in AGENT_RE_V44.finditer(text):
        name = m.group(1).title()
        if name in seen:
            continue
        seen.add(name)
        try:
            agents.append({
                "agent": name,
                "signal": m.group(2).upper(),
                "score": float(m.group(3)),
                "confidence": float(m.group(4)),
            })
        except ValueError:
            continue

    # 5) V4.4 JSON-block format (legacy)
    import json as _json
    for m in AGENT_BLOCK_RE.finditer(text):
        name = m.group(1).title()
        if name in seen:
            continue
        try:
            obj = _json.loads(m.group(2))
            agents.append({
                "agent": name,
                "signal": str(obj.get("signal", "")).upper(),
                "score": float(obj.get("score", 0)),
                "confidence": float(obj.get("confidence", 0)),
            })
            seen.add(name)
        except (ValueError, _json.JSONDecodeError):
            continue
    return agents


def _find_macro_regime(text: str, decision_date: str | None = None,
                       ticker: str | None = None) -> dict:
    """Resolve macro_regime + macro_multiplier with priority:
        1. Phase 0 cache JSON (V5.0 真實來源 — MD report does not embed regime)
        2. MD regex fallback (V4.x reports + bridge cases)

    Returns dict with keys: market_regime, macro_multiplier, source.
    source ∈ {"phase0_cache", "md_regex", None}
    """
    regime = None
    mult = None
    source = None

    # 1) Phase 0 cache lookup (Codex review #4 + #5 — repo-root path + wide fallback)
    if decision_date:
        candidates = []
        if ticker:
            candidates.append(
                ROOT / "investment/invest_logs"
                     / f"{decision_date}_phase0_{ticker.lower()}.json"
            )
        candidates.append(
            ROOT / "investment/invest_logs"
                 / f"{decision_date}_phase0.json"
        )
        for p in candidates:
            if not p.exists():
                continue
            try:
                import json as _json
                with open(p, encoding="utf-8") as f:
                    data = _json.load(f)
                # Multi-key fallback — Phase 0 schema drifts across V5.0 minor versions.
                # Actual observed path (2026-05-23_phase0_nok.json): macro_summary.market_regime
                ph0 = data.get("phase0") or {}
                ph1 = data.get("phase1") or {}
                msum = data.get("macro_summary") or {}
                for cand in (msum.get("market_regime"),
                             ph1.get("market_regime"),
                             ph0.get("market_regime"),
                             data.get("market_regime"),
                             data.get("macro_regime"),
                             data.get("regime")):
                    if cand:
                        regime = cand
                        break
                for cand in (data.get("phase3_macro_multiplier"),
                             ph1.get("macro_multiplier"),
                             data.get("macro_multiplier"),
                             data.get("multiplier")):
                    if cand is not None:
                        try:
                            mult = float(cand)
                            break
                        except (TypeError, ValueError):
                            continue
                if regime:
                    source = "phase0_cache"
                    break
            except (OSError, _json.JSONDecodeError):
                continue

    # 2) MD regex fallback (legacy V4.x reports still inline regime)
    if regime is None:
        for p in (r"\"market_regime\"\s*:\s*\"([A-Z_]+)\"",
                  r"\*\*market_regime\*\*[^A-Z]+([A-Z_]+)",
                  r"PHASE 0[^\n]*([A-Z_]+ regime)"):
            m = re.search(p, text)
            if m:
                regime = m.group(1).split()[0]
                source = "md_regex"
                break

    if mult is None:
        m = re.search(r"macro_multiplier[\"\s|:×]+([\d.]+)", text)
        if m:
            try:
                mult = float(m.group(1))
            except ValueError:
                pass

    return {"market_regime": regime, "macro_multiplier": mult, "source": source}


def extract(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    decision_date, ticker = _parse_filename(path)

    agents = _find_agent_breakdown(text)

    # decisive_agent computation — score×confidence when all lanes have it,
    # else fall back to |score| only. Method tag (Codex review #3) lets the
    # next REVIEW round distinguish real-confidence-driven picks from fallbacks.
    decisive_agent = None
    decisive_agent_method = None
    if agents:
        has_conf = all("confidence" in a for a in agents)
        if has_conf:
            decisive_agent = max(
                agents, key=lambda a: abs(a["score"] * a["confidence"])
            )["agent"]
            decisive_agent_method = "score_x_confidence"
        else:
            decisive_agent = max(agents, key=lambda a: abs(a["score"]))["agent"]
            decisive_agent_method = "max_abs_score"

    final_score = _find_final_score(text)
    decision, decision_modifier = _find_decision(text)
    position = _find_position_size(text)
    trader = _find_trader_proposal(text)
    macro = _find_macro_regime(text, decision_date=decision_date, ticker=ticker)

    confs = [a["confidence"] for a in agents if "confidence" in a]
    # TODO-013 (REVIEW 2026-06-20) — lane score dispersion. Lets next REVIEW
    # split the 0–1 score band into weak-signal (low stdev) vs agent-high-
    # dispersion (high stdev). Shadow field only; population stdev so a single
    # 2-lane report still yields a value. None when <2 lanes parsed.
    lane_scores = [a["score"] for a in agents if "score" in a]
    agent_score_stdev = (
        round(statistics.pstdev(lane_scores), 4) if len(lane_scores) >= 2 else None
    )

    record = {
        "source": "deep-dive",
        "decision_date": decision_date,
        "scope": "ticker",
        "tickers": [ticker] if ticker else [],
        "raw_path": str(path.relative_to(path.parents[1])) if len(path.parents) > 1 else str(path),
        "summary": f"{ticker} deep-dive: {decision or 'unknown'} (score {final_score})",
        "decision_content": {
            "final_score": final_score,
            "final_action": decision,                         # verb only (back-compat)
            "final_action_modifier": decision_modifier,       # paren modifier — DEFENSIVE/OFFENSIVE/etc
            "position_size": position,
            "trader_proposal": trader,
            "macro_regime": macro["market_regime"],
            "macro_multiplier": macro["macro_multiplier"],
        },
        "agent_breakdown": agents,
        "tuning_hooks": {
            "decisive_agent": decisive_agent,
            "decisive_agent_method": decisive_agent_method,   # Codex review #3
            "macro_regime": macro["market_regime"],
            "macro_multiplier": macro["macro_multiplier"],
            "macro_regime_source": macro["source"],           # phase0_cache / md_regex / None
            "agent_count": len(agents),
            "agent_confidence_count": len(confs),             # 有真 confidence 的 lane 數
            "agent_score_stdev": agent_score_stdev,           # TODO-013 — 0–1 band dispersion split
            "agent_score_count": len(lane_scores),
            "min_agent_confidence": min(confs, default=None),
            "max_agent_confidence": max(confs, default=None),
        },
    }
    # Rec 7 (V2.17.16) — sub-industry heat overlay so weekly review can group
    # repeat-misses by sector/industry instead of only by ticker. Fail-soft.
    if enrich_ticker_heat is not None and ticker:
        try:
            record["tuning_hooks"]["sub_industry_heat"] = enrich_ticker_heat(ticker)
        except Exception as e:                                              # pragma: no cover
            record["tuning_hooks"]["sub_industry_heat"] = {"error": str(e)[:120]}
    record["decision_id"] = f"deep-dive_{ticker}_{decision_date}"
    return record

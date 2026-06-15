#!/usr/bin/env python3
"""validate_ic_memo.py — IC Memo + fact_pack integrity validator.

Checks (rc table):
  rc=0  pass
  rc=1  fatal (CI-blocking):
        - decision_lock 11-field hash mismatch (recomputed from history.json)
        - fact_pack hash mismatch (composed from fact_pack contents)
        - §11 verbatim fields do NOT match _protocol_decision_lock.payload
        - §8 weighted_fair_value mismatch vs fair_value_summary
        - §11 missing entirely from MD
        - forbidden re-scoring phrases match
  rc=2  degraded-usable:
        - earnings cache missing (sec_3/5/6/7 stub)
        - peer_descriptor is stub
        - anchors_available < 3
        - any provenance-tag line missing on a section header
        - Provenance Roster table missing
        - section 1..12 not all present in MD

Usage:
  python3 validate_ic_memo.py reports/<DATE>_<TICKER>_ic_memo.md
  python3 validate_ic_memo.py reports/<DATE>_<TICKER>_ic_memo.md --fact-pack skills/.../fact_pack.json
  python3 validate_ic_memo.py --fact-pack-only skills/.../fact_pack.json   # skip MD check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HISTORY_PATH = ROOT / "investment" / "invest_logs" / "history.json"
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

LOCK_FIELDS = [
    "final_decision", "final_action", "position_size_pct", "analysis_price",
    "fair_value_summary", "scenario_odds", "watch_conditions", "key_risks",
    "red_team_counter_thesis", "red_team_kill_conditions", "lane_scores",
]

FORBIDDEN_PHRASES = [
    r"重新評估.*score",
    r"adjusted score",
    r"新版 lane",
    r"override.*final_action",
    r"composer 重算.*FV",
]

SECTION_HEADERS = [f"§{i}" for i in range(1, 13)]


def _round_floats(obj):
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, dict):
        return {k: _round_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(x) for x in obj]
    return obj


def compute_decision_lock_hash(trade: dict) -> str:
    payload = {k: _round_floats(trade.get(k)) for k in LOCK_FIELDS if k in trade}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_fact_pack_hash(fact_pack: dict) -> str:
    stable_copy = {k: v for k, v in fact_pack.items() if k not in ("composed_at", "fact_pack_hash")}
    canonical = json.dumps(stable_copy, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def find_trade_in_history(ticker: str, session_idx_hint: int | None = None) -> dict | None:
    if not HISTORY_PATH.exists():
        return None
    h = json.loads(HISTORY_PATH.read_text())
    if not isinstance(h, list):
        return None
    if session_idx_hint is not None and 0 <= session_idx_hint < len(h):
        e = h[session_idx_hint]
        if e.get("ticker") == ticker:
            for t in e.get("trades_this_session") or []:
                if t.get("ticker") == ticker:
                    return t
    for e in reversed(h):
        if e.get("ticker") == ticker:
            for t in e.get("trades_this_session") or []:
                if t.get("ticker") == ticker:
                    return t
    return None


class Finding:
    def __init__(self, severity: str, code: str, msg: str):
        self.severity = severity  # "fatal" or "degraded"
        self.code = code
        self.msg = msg

    def __repr__(self):
        return f"[{self.severity.upper()}/{self.code}] {self.msg}"


def _section_block(md_text: str, section_no: int) -> str:
    start = md_text.find(f"## §{section_no}")
    if start < 0:
        return ""
    next_match = re.search(r"\n## §\d+", md_text[start + 1:])
    if not next_match:
        return md_text[start:]
    return md_text[start:start + 1 + next_match.start()]


def validate_fact_pack(fact_pack: dict, *, check_history: bool = True) -> list[Finding]:
    findings: list[Finding] = []

    # F-1: decision_lock hash must match recomputed history
    lock = fact_pack.get("_protocol_decision_lock") or {}
    stored_hash = lock.get("hash") or ""
    payload = lock.get("payload") or {}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    recomputed_from_payload = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if recomputed_from_payload != stored_hash:
        findings.append(Finding("fatal", "F-1.1", "decision_lock.hash does not match SHA256 of its own payload"))

    # F-2: recompute lock from history.json — should equal stored hash
    if check_history:
        ticker = fact_pack.get("ticker")
        # Try to extract session index hint from sources.protocol_history.path "...#entry[N]"
        sess_idx = None
        try:
            path = ((fact_pack.get("sources") or {}).get("protocol_history") or {}).get("path") or ""
            m = re.search(r"entry\[(\d+)\]", path)
            if m:
                sess_idx = int(m.group(1))
        except Exception:
            pass
        trade = find_trade_in_history(ticker, sess_idx)
        if trade is not None:
            recomputed_from_history = compute_decision_lock_hash(trade)
            if recomputed_from_history != stored_hash:
                findings.append(Finding(
                    "fatal", "F-1.2",
                    f"decision_lock hash mismatch vs history.json: "
                    f"history={recomputed_from_history[:12]}... vs fact_pack={stored_hash[:12]}..."
                ))

    # F-3: fact_pack_hash self-consistency
    stored_fp_hash = fact_pack.get("fact_pack_hash")
    recomputed_fp_hash = compute_fact_pack_hash(fact_pack)
    if stored_fp_hash and stored_fp_hash != recomputed_fp_hash:
        findings.append(Finding(
            "fatal", "F-1.3",
            f"fact_pack_hash self-inconsistent: stored={stored_fp_hash[:12]}... vs recomputed={recomputed_fp_hash[:12]}..."
        ))

    # D-1: degraded_sections flagged
    deg = fact_pack.get("degraded_sections") or []
    if deg:
        findings.append(Finding("degraded", "D-1", f"degraded_sections: {deg}"))

    # D-2: anchors_available < 3
    fv = ((fact_pack.get("facts") or {}).get("sec_8") or {}).get("fair_value_summary") or {}
    if (fv.get("anchors_available") or 0) < 3:
        findings.append(Finding(
            "degraded", "D-2",
            f"sec_8 anchors_available={fv.get('anchors_available')} (<3) — FV confidence low",
        ))

    # F-4: sec_11 verbatim — must match _protocol_decision_lock.payload subset
    sec_11 = ((fact_pack.get("facts") or {}).get("sec_11")) or {}
    payload_11_relevant = {
        "final_action": payload.get("final_action"),
        "final_decision": payload.get("final_decision"),
        "position_size_pct": payload.get("position_size_pct"),
        "watch_conditions": payload.get("watch_conditions"),
    }
    sec_11_relevant = {
        "final_action": sec_11.get("final_action"),
        "final_decision": sec_11.get("final_decision"),
        "position_size_pct": _round_floats(sec_11.get("position_size_pct")),
        "watch_conditions": sec_11.get("watch_conditions"),
    }
    if payload_11_relevant != sec_11_relevant:
        findings.append(Finding(
            "fatal", "F-2",
            f"sec_11 verbatim fields differ from _protocol_decision_lock.payload: "
            f"payload={payload_11_relevant} vs sec_11={sec_11_relevant}"
        ))

    return findings


def validate_markdown(md_text: str, fact_pack: dict | None) -> list[Finding]:
    findings: list[Finding] = []

    # D-3: all 12 section headers present
    missing_sections = [s for s in SECTION_HEADERS if s not in md_text]
    if missing_sections:
        sev = "fatal" if "§11" in missing_sections else "degraded"
        findings.append(Finding(sev, "F-3" if sev == "fatal" else "D-3",
                                 f"missing section markers: {missing_sections}"))

    # D-4: each section should have a provenance <!-- src: --> comment after it
    # heuristic: count src comments; expect >= 8 (header + ~10 sections)
    src_count = len(re.findall(r"<!--\s*src:\s*[^>]+-->", md_text))
    if src_count < 8:
        findings.append(Finding("degraded", "D-4",
                                 f"only {src_count} provenance <!-- src: --> comments found (expected >=8)"))

    # D-5: Provenance Roster table present (look for "Provenance Roster" heading)
    if "Provenance Roster" not in md_text:
        findings.append(Finding("degraded", "D-5", "Provenance Roster section/table missing"))

    # F-5: forbidden re-scoring phrases
    for phrase in FORBIDDEN_PHRASES:
        if re.search(phrase, md_text, re.IGNORECASE):
            findings.append(Finding("fatal", "F-4", f"forbidden re-scoring phrase matched: /{phrase}/"))

    # F-6: weighted_fair_value in MD §8 must match fact_pack
    if fact_pack:
        fv = ((fact_pack.get("facts") or {}).get("sec_8") or {}).get("fair_value_summary") or {}
        wfv = fv.get("weighted_fair_value")
        if wfv is not None:
            # Locate "Weighted FV" line; extract $ value
            m = re.search(r"Weighted FV.*?\$?([\d,\.]+)([BM]?)", md_text)
            if m:
                raw = m.group(1).replace(",", "")
                try:
                    parsed = float(raw)
                except ValueError:
                    parsed = None
                if parsed is not None and abs(parsed - float(wfv)) > 0.01:
                    findings.append(Finding(
                        "fatal", "F-5",
                        f"§8 Weighted FV in MD ({parsed}) != fact_pack ({wfv})"
                    ))

    # F-7: §11 final_action keyword present in MD body
    if fact_pack:
        fa = ((fact_pack.get("facts") or {}).get("sec_11") or {}).get("final_action")
        if fa and "## §11" in md_text:
            sec_11_idx = md_text.find("## §11")
            sec_12_idx = md_text.find("## §12", sec_11_idx)
            block = md_text[sec_11_idx:sec_12_idx if sec_12_idx > 0 else len(md_text)]
            if fa not in block:
                findings.append(Finding(
                    "fatal", "F-6",
                    f"§11 body does not contain final_action='{fa}' verbatim"
                ))

    if fact_pack:
        facts = fact_pack.get("facts") or {}
        sec_1 = facts.get("sec_1") or {}
        has_analysis = sec_1.get("analysis_price") is not None
        has_live = (sec_1.get("live_spot") is not None) or (sec_1.get("current_price") is not None)
        if has_analysis and has_live:
            head_end = md_text.find("## §1")
            header = md_text[:head_end if head_end > 0 else min(len(md_text), 1200)]
            if "Analysis Price" not in header or "Live Spot" not in header:
                findings.append(Finding(
                    "fatal", "F-7",
                    "header must render both Analysis Price and Live Spot when fact_pack has both"
                ))

        sec_11 = facts.get("sec_11") or {}
        sec_11_idx = md_text.find("## §11")
        sec_12_idx = md_text.find("## §12", sec_11_idx)
        sec_11_block = md_text[sec_11_idx:sec_12_idx if sec_12_idx > 0 else len(md_text)] if sec_11_idx >= 0 else ""
        sec_1_idx = md_text.find("## §1")
        sec_2_idx = md_text.find("## §2", sec_1_idx)
        sec_1_block = md_text[sec_1_idx:sec_2_idx if sec_2_idx > 0 else len(md_text)] if sec_1_idx >= 0 else ""
        for key, label in (("entry_aggressive", "aggressive"), ("entry_conservative", "conservative")):
            if sec_11.get(key) is None and sec_1.get(key) is None:
                continue
            if re.search(rf"Entry \({label}\):\s*—", sec_11_block):
                findings.append(Finding("fatal", "F-8", f"§11 renders {key} as — despite fact_pack value"))

        # §1 entry range check fires once across both keys (not per-key)
        any_entry_set = any(
            sec_11.get(k) is not None or sec_1.get(k) is not None
            for k in ("entry_aggressive", "entry_conservative")
        )
        if (
            any_entry_set
            and "Entry (aggr / cons)" in sec_1_block
            and re.search(r"Entry \(aggr / cons\).*\|\s*—\s*/\s*—", sec_1_block)
        ):
            findings.append(Finding("fatal", "F-8", "§1 renders entry ranges as — despite fact_pack values"))

    sec_7_block = _section_block(md_text, 7)
    if re.search(r"\{\s*['\"]tier['\"]\s*:", sec_7_block):
        findings.append(Finding("degraded", "D-6", "raw structural_shift JSON fragment found in memo"))
    sec_10_block = _section_block(md_text, 10)
    if re.search(r"^#{2,4}\s+(Consensus View|Differentiated View)\b", sec_10_block, re.MULTILINE):
        findings.append(Finding("degraded", "D-7", "dead §10 consensus/differentiated headers found"))

    return findings


def determine_rc(findings: list[Finding]) -> int:
    if any(f.severity == "fatal" for f in findings):
        return 1
    if any(f.severity == "degraded" for f in findings):
        return 2
    return 0


def main():
    ap = argparse.ArgumentParser(description="Validate IC Memo + fact_pack integrity.")
    ap.add_argument("memo_md", nargs="?", help="Path to memo MD")
    ap.add_argument("--fact-pack", type=Path, help="Path to fact_pack JSON (auto-located if omitted)")
    ap.add_argument("--fact-pack-only", type=Path, help="Validate only fact_pack (no MD)")
    ap.add_argument("--no-history-check", action="store_true",
                    help="Skip history.json re-validation (used by tests with synthetic data)")
    ap.add_argument("--json", action="store_true", help="Output findings as JSON")
    args = ap.parse_args()

    fact_pack = None
    md_text = None

    if args.fact_pack_only:
        fact_pack = json.loads(Path(args.fact_pack_only).read_text())
    else:
        if not args.memo_md:
            ap.error("Provide memo_md path or use --fact-pack-only")
        md_path = Path(args.memo_md)
        if not md_path.exists():
            print(f"[ic-memo-validator] memo not found: {md_path}", file=sys.stderr)
            sys.exit(1)
        md_text = md_path.read_text()
        # Locate fact_pack
        fp_path = args.fact_pack
        if fp_path is None:
            # Extract ticker from filename: <DATE>_<TICKER>_ic_memo.md
            m = re.match(r"(\d{8})_([A-Z]+)_ic_memo\.md$", md_path.name)
            if m:
                ticker = m.group(2)
                candidates = sorted(CACHE_DIR.glob(f"{ticker}_*_fact_pack.json"))
                if candidates:
                    fp_path = candidates[-1]
        if fp_path and Path(fp_path).exists():
            fact_pack = json.loads(Path(fp_path).read_text())

    findings: list[Finding] = []
    if fact_pack:
        findings.extend(validate_fact_pack(fact_pack, check_history=not args.no_history_check))
    if md_text is not None:
        findings.extend(validate_markdown(md_text, fact_pack))

    rc = determine_rc(findings)

    if args.json:
        print(json.dumps({
            "rc": rc,
            "findings": [{"severity": f.severity, "code": f.code, "msg": f.msg} for f in findings],
        }, indent=2, ensure_ascii=False))
    else:
        rc_label = {0: "PASS", 1: "FATAL", 2: "DEGRADED"}[rc]
        print(f"[ic-memo-validator] rc={rc} ({rc_label}) — {len(findings)} finding(s)")
        for f in findings:
            print(f"  {f}")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())

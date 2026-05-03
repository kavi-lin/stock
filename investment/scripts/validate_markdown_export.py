#!/usr/bin/env python3
"""
Validate the Phase 5 markdown report at `reports/<YYYYMMDD>_<TICKER>.md`
for V4.8 score-scale consistency.

Scope (per user requirement: "所有報告都是一樣的 scale")：
  - Final Score scale 若有標註 → 必須 `/ 3.0`，禁 `/5.0` 或 `/10`
  - Burry score 必須 `/ 100`，禁 `/12`（舊 bug）/ `/10`
  - 全文不得在 score 上下文出現 `/5.0` 或 `/10` 字樣

Out of scope（歷史 V4.6/V4.7 報告變體很多，避免大量誤判）：
  - 標題格式（早期報告不一致）
  - section header（早期 schema 不同）
  - lane score 上限（protocol 允許 ±5 強訊號 +3/+4）

Invocation (from protocol Phase 5 Step 5):
    python3 investment/scripts/validate_markdown_export.py
        rc=0  → pass
        rc=1  → scale drift detected — see stderr

    python3 investment/scripts/validate_markdown_export.py --report <path>
        validate a specific file (audit / debug)

Catches the historical drift modes:
  - `/5.0` scale (e.g. legacy 20260421_MRVL.md, 4-lane × 1.25 = 5)
  - `/10` scale (e.g. freestyle 2026-05-02_VRT.md, manually written when
    Sonnet formatter failed and PM fallback didn't enforce schema)
  - `/12` Burry scale (legacy bug in V4.6 reports)
"""
import argparse
import json
import os
import re
import sys

ROOT         = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HISTORY_JSON = os.path.join(ROOT, "investment/invest_logs/history.json")
REPORTS_DIR  = os.path.join(ROOT, "reports")


def fail(errors):
    print("[validate_markdown_export] ✗ score scale drift:", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    print(
        "\nFix: rewrite the MD report so Final Score uses `/ 3.0` scale "
        "(or bare 0-3 number) and Burry score uses `/ 100`. "
        "See reports/20260502_TEAM.md for canonical V4.8 template.",
        file=sys.stderr,
    )
    sys.exit(1)


def _resolve_latest_report():
    """Read history.json last entry → derive expected MD path. Returns (path, entry)."""
    if not os.path.exists(HISTORY_JSON):
        fail([f"history.json not found at {HISTORY_JSON}"])
    with open(HISTORY_JSON, "r", encoding="utf-8") as fp:
        hist = json.load(fp)
    if not isinstance(hist, list) or not hist:
        fail(["history.json is empty"])
    last = hist[-1]
    ticker = last.get("ticker") or (last.get("trades_this_session") or [{}])[0].get("ticker")
    export_date = last.get("export_date")
    if not ticker or not export_date:
        fail(["history.json last entry missing ticker / export_date"])
    yyyymmdd = export_date.replace("-", "")
    candidate = os.path.join(REPORTS_DIR, f"{yyyymmdd}_{ticker}.md")
    if not os.path.exists(candidate):
        fail([f"expected MD not found: {candidate}"])
    return candidate, last


def _check_final_score(text, errors):
    """Final Score 若有 scale 標註 → 必須 /3.0；裸數字接受任何值。"""
    m = re.search(
        r"Final\s*Score[^\d\n]{0,40}?([\d\.]+)\s*(?:/\s*([\d\.]+))?",
        text, re.IGNORECASE,
    )
    if not m:
        # Final Score 行可能不存在於某些舊報告 — 不強擋
        return
    score, scale = m.groups()
    if scale is None:
        return  # 裸數字模式（standard V4.8 多份報告如此）
    s = scale.strip()
    if s not in ("3.0", "3"):
        errors.append(f"Final Score scale 必須 /3.0，實際 /{s}")


def _check_forbidden_score_scales(text, errors):
    """禁用 scale 偵測。只擋三種明確 drift pattern，避免誤抓計算式 (X/10−5)。"""
    forbidden = [
        # 1. Final Score 後 scale 標註 / 5.0 或 / 10
        (r"Final\s*Score[^\n]*?\s/\s*5\.0\b", "Final Score /5.0"),
        (r"Final\s*Score[^\n]*?\s/\s*10\b(?!\s*[Bb])", "Final Score /10"),
        # 2. Lane name : X / 10 或 / 5.0（VRT freestyle pattern）
        (r"(?:Fundamentals|Sentiment|News|Technical)\s*[:：][^\n]*?\d\s*/\s*10\b", "Lane /10"),
        (r"(?:Fundamentals|Sentiment|News|Technical)\s*[:：][^\n]*?\d\s*/\s*5\.0\b", "Lane /5.0"),
        # 3. Status / 摘要行 X / 10（VRT 開頭 "HOLD (6.72/10 risk-adjusted)"）
        (r"(?:Status|Final\s*Decision|HOLD|BUY|SELL|STAGED)[^\n]*?\(\s*\d+\.?\d*\s*/\s*10\b", "Final score /10"),
    ]
    for pat, label in forbidden:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            ctx = m.group(0)[:80].replace("\n", " ")
            errors.append(f"報告含禁用 scale `{label}`（V4.8 統一 /3.0）；命中: `{ctx}...`")


def _check_burry_scale(text, errors):
    """Burry score 必須 /100。擋早期 V4.6 的 /12 bug 跟 /10 freestyle。"""
    # 抓 "Burry score X / Y" 或 "Burry X / Y" 同行內
    m = re.search(r"Burry[^\n]*?\b(\d+\.?\d*)\s*/\s*(\d+\.?\d*)\b", text, re.IGNORECASE)
    if not m:
        return
    scale = m.group(2).strip()
    if scale not in ("100", "100.0"):
        errors.append(f"Burry score scale 必須 /100，實際 /{scale}")


def _check_fair_value_section(text, errors, history_entry):
    """V5.0+ MD reports must contain '合理股價' section if entry is V5.0."""
    if not history_entry:
        return  # standalone --report mode without history context, skip
    if history_entry.get("session_export_version") != "V5.0":
        return  # V4.8 entries don't need fair value section
    if not re.search(r"合理股價", text):
        errors.append("V5.0 報告缺「合理股價」section（fair_value_summary 必須在 MD 呈現）")
    # Check anchor table mentions weighted fair value
    if not re.search(r"(weighted_fair_value|加權合理價|Weighted\s*Fair\s*Value)", text, re.IGNORECASE):
        errors.append("V5.0 報告「合理股價」section 缺 weighted_fair_value 標示")


def validate(report_path, history_entry=None):
    if not os.path.exists(report_path):
        fail([f"report not found: {report_path}"])
    with open(report_path, "r", encoding="utf-8") as fp:
        text = fp.read()

    errors = []
    _check_final_score(text, errors)
    _check_forbidden_score_scales(text, errors)
    _check_burry_scale(text, errors)
    _check_fair_value_section(text, errors, history_entry)

    if errors:
        fail(errors)

    print(f"[validate_markdown_export] ✓ {os.path.relpath(report_path, ROOT)} passes V4.8/V5.0 schema check")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", help="absolute or repo-relative path; default = derive from history.json last entry")
    args = ap.parse_args()

    if args.report:
        path = args.report
        if not os.path.isabs(path):
            path = os.path.join(ROOT, path)
        history_entry = None  # standalone audit, no history context
    else:
        path, history_entry = _resolve_latest_report()

    return validate(path, history_entry)


if __name__ == "__main__":
    sys.exit(main())

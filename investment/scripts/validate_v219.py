#!/usr/bin/env python3
"""V2.19 — fixture test for compute_polarization (4-tier) + classify_red_team_basis.

Asserts:
  - Polarization correctly distinguishes BIPOLAR / OUTLIER / MIXED / ALIGNED
    on synthetic lane_score arrays (incl. Gemini's [+4,+3,+3,+2,-2] outlier case)
  - Red Team basis classifier blocks LLM mr-spoofing via "contaminated" tier
  - V2.18 NONE-tier behaviour unaffected (regression baseline)

Usage:
    python3 investment/scripts/validate_v219.py
        rc=0 → all fixtures pass
        rc=1 → assertion failure (prints first failing fixture)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "investment" / "scripts"))

from apply_det_shadow import compute_polarization, classify_red_team_basis  # noqa: E402


def _polar_label(scores: list[float]) -> str:
    """Helper: feed a 5-tuple into compute_polarization signature.

    lane_scores dict expects fundamentals/sentiment/news/technical;
    val_score passed separately.
    """
    fund, sent, news, tech, val = scores
    lane_scores = {
        "fundamentals": fund, "sentiment": sent,
        "news": news, "technical": tech,
    }
    return compute_polarization(lane_scores, val).get("label")


POLARIZATION_FIXTURES = [
    # (name, scores [F,S,N,T,V], expected_label)
    ("Gemini outlier 4-vs-1 high",   [+4, +3, +3, +2, -2], "OUTLIER"),
    ("Gemini outlier 4-vs-1 mod",    [+2, +2, +2, +2, -2], "OUTLIER"),
    ("True bipolar balanced",        [+3, +2, -3, -2, +1], "BIPOLAR"),
    ("True bipolar 2-vs-3",          [+4, +3, -1, -3, -4], "BIPOLAR"),
    ("Mixed mild",                   [+2, +1, -1, -1, 0],  "MIXED"),
    ("Aligned bull",                 [+2, +1, +2, +1, +1], "ALIGNED"),
    ("Aligned bear",                 [-2, -1, -2, -1, -1], "ALIGNED"),
    ("Aligned weak",                 [+1, 0, 0, -1, -1],   "ALIGNED"),
    ("OUTLIER bear-side",            [-4, -3, -3, -2, +2], "OUTLIER"),
    ("Bipolar tight extremes",       [+2, +2, -2, -2, 0],  "BIPOLAR"),
]


RT_BASIS_FIXTURES = [
    # (name, counter_thesis, kill_conditions, expected_basis)
    ("Pure mean-reversion",
     "估值雖然合理，但 forward P/E 6.4x 是週期峰值特徵，歷史均值 12x，回歸後股價腰斬",
     [],
     "pure_mean_reversion"),
    ("Gemini contamination spoof",
     "客戶 NVDA 庫存日數從 30 天降至 18 天，HBM 訂單能見度高，"
     "但這正是週期見頂的訊號 — 歷史上每次 inventory 谷底都對應毛利率均值回歸",
     [],
     "contaminated"),
    ("Pure forward attack",
     "三星 HBM4 預計 2026 Q3 量產，capacity addition 將壓縮 MU 的議價力。"
     "客戶庫存若回升至 45 天以上，毛利率 80% 不可持續。",
     [{"if": "三星 HBM4 capacity addition >50% TAM", "then": "MU GM compress 20pp"}],
     "pure_forward"),
    ("Unclassified neutral",
     "目前估值合理，沒有明顯催化劑風險。",
     [],
     "unclassified"),
    ("Kill conditions carry mr",
     "公司基本面強勁。",
     [{"if": "P/E 重回歷史均值", "then": "股價腰斬"}],
     "pure_mean_reversion"),
    ("Mixed string both keywords",
     "新進入者 (next-gen technology) 加速，但歷史上每次 capacity addition 都觸發 mean reversion",
     [],
     "contaminated"),
]


def main() -> int:
    failures = []

    print("=== compute_polarization fixtures ===")
    for name, scores, expected in POLARIZATION_FIXTURES:
        actual = _polar_label(scores)
        ok = actual == expected
        marker = "✓" if ok else "✗"
        print(f"  {marker} {name:35s} scores={scores} expected={expected} actual={actual}")
        if not ok:
            failures.append((name, expected, actual))

    print()
    print("=== classify_red_team_basis fixtures ===")
    for name, ct, kc, expected in RT_BASIS_FIXTURES:
        actual = classify_red_team_basis(ct, kc)
        ok = actual == expected
        marker = "✓" if ok else "✗"
        ct_short = (ct[:50] + "...") if len(ct) > 50 else ct
        print(f"  {marker} {name:35s} expected={expected:25s} actual={actual}")
        if not ok:
            print(f"      counter_thesis: {ct_short}")
            failures.append((name, expected, actual))

    print()
    if failures:
        print(f"FAILED: {len(failures)} fixture(s)")
        for name, exp, act in failures:
            print(f"  - {name}: expected={exp} actual={act}")
        return 1
    print(f"PASSED: {len(POLARIZATION_FIXTURES)} polarization + {len(RT_BASIS_FIXTURES)} basis fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())

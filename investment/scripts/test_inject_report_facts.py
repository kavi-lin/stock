#!/usr/bin/env python3
"""Golden-fixture tests for inject_report_facts.py (V4.66.0). rc=0 = all pass."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "inject_report_facts.py")

FIXTURE_TRADE = {
    "ticker": "TEST",
    "final_decision": "HOLD", "final_action": "CANCEL",
    "final_score": -0.57, "decision_confidence_pct": 62,
    "position_size_pct": 0.0, "analysis_price": 113.21,
    "burry_score": 36.2, "red_team_verdict": "STRONG_COUNTER",
    "scenario_odds": {"bull": 18, "base": 37, "bear": 45},
    "entry_conservative": None, "entry_aggressive": None,
    "take_profit": None, "stop_loss": None,
    "risk_reward_ratio": None, "staged_split": None,
    "lane_scores": {"fundamentals": 1, "sentiment": -1, "news": -2, "technical": -3},
    "fair_value_summary": {
        "anchors": {"dcf_unlevered": 10.7976, "analyst_pt_consensus": 193.36},
        "weights_used": {"dcf_unlevered": 0.3, "analyst_pt_consensus": 0.7},
        "weighted_fair_value": 66.27, "vs_current_pct": -41.46,
        "verdict_band": "extreme_overvalued", "confidence": "low",
        "current_price": 113.21,
        "primary_method": "dcf_self_built",
    },
    "fair_value_range": {"p25": 10.8, "p50": 21.19, "p75": 116.64,
                         "min_anchor": 5.65, "max_anchor": 262.09,
                         "range_verdict": "fair_zone", "agreement_grade": "low"},
    "implied_expectations": {"implied_5y_fcf_cagr": 0.6, "implied_out_of_range": True,
                             "wacc_used": 0.09},
    "valuation_explained_range": {
        "available": True, "primary_fv": 66.27,
        "primary_sensitivity": {"low": 55.0, "high": 75.0},
        "scenario_without_peer": 70.0, "scenario_with_peer": 110.0,
        "peer_pe_range_anchor": 150.0, "range_low": 55.0, "range_high": 110.0,
        "peer_symbols": ["P1", "P2", "P3"], "peer_count": 3,
    },
    "red_team_kill_conditions": ["IF 條件甲 THEN 論點失效", "IF 條件乙 THEN 反轉"],
    "key_risks": ["風險一：估值極端", "風險二：Stage 4 下降趨勢"],
    "watch_conditions": {"earnings_2026_08_03": "Q2 財報 operating margin ≥44%",
                         "reclaim_ma20": "站回 MA20 且量能配合"},
}
FIXTURE_ENTRY = {"ticker": "TEST", "export_date": "2026-07-03",
                 "trades_this_session": [FIXTURE_TRADE]}

PLACEHOLDER_MD = """# 2026-07-03 TEST — 投資委員會分析

## 決議摘要
本委員會維持觀望。
<!--INJECT:decision_summary-->

## Final Visualization Table
<!--INJECT:lane_scores-->

## 合理股價
<!--INJECT:fair_value_anchors-->

## Kill Conditions
<!--INJECT:kill_conditions-->

## 關鍵風險
<!--INJECT:key_risks-->

## Watch
<!--INJECT:watch_conditions-->
"""

n_pass = 0


def check(cond, msg):
    global n_pass
    if cond:
        n_pass += 1
    else:
        print(f"✗ FAIL: {msg}", file=sys.stderr)
        sys.exit(1)


def run(report, history):
    return subprocess.run([sys.executable, SCRIPT, "--report", report, "--history", history],
                          capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as td:
        hist = os.path.join(td, "history.json")
        json.dump([FIXTURE_ENTRY], open(hist, "w"))
        report = os.path.join(td, "report.md")
        open(report, "w").write(PLACEHOLDER_MD)

        # 1) 基本注入
        r = run(report, hist)
        check(r.returncode == 0, f"注入 rc 應 0，得 {r.returncode}: {r.stderr}")
        text = open(report).read()
        check("<!--INJECT:" not in text, "不應殘留 INJECT token")
        for name in ("decision_summary", "lane_scores", "fair_value_anchors",
                     "kill_conditions", "key_risks", "watch_conditions"):
            check(f"<!--FACTS:{name}:start-->" in text, f"缺 {name} start marker")
            check(f"<!--FACTS:{name}:end-->" in text, f"缺 {name} end marker")
        # 2) 數值 verbatim
        check("-0.57 / 3.0" in text, "final_score /3.0 應 verbatim")
        check("36.2 / 100" in text, "burry /100 應 verbatim")
        check("$66.27" in text, "weighted_fair_value 應 verbatim")
        check("$113.21" in text, "analysis_price 應 verbatim")
        check("bull 18 / base 37 / bear 45" in text, "scenario_odds 應 verbatim")
        check("| Technical | -3 |" in text, "lane score 應 verbatim")
        check("1. IF 條件甲 THEN 論點失效" in text, "kill condition 應編號照搬")
        check("- 風險一：估值極端" in text, "key_risks 應條列")
        check("**earnings_2026_08_03**" in text, "watch_conditions key 應保留")
        check("加權合理價 (weighted_fair_value)" in text, "需含 validator 要求的標示字串")
        check("DCF 主FV／加權合理價 (weighted_fair_value)" in text, "structural DCF 應標成主 FV")
        check("完整解釋帶 $55.00–$110.00" in text, "應呈現 DCF-primary explained range")
        check("P1, P2, P3；n=3" in text, "應揭露 range-only peer 組成")
        check("合理股價" in text, "需含「合理股價」字樣（validator gate）")
        # 3) N/A-safe（HOLD/CANCEL 的 None entry/TP/SL）
        check("N/A / N/A" in text, "None entry 應渲染 N/A")
        # 4) idempotent re-run：改 history 數值 → refreshed
        FIXTURE_TRADE["final_score"] = 1.23
        json.dump([FIXTURE_ENTRY], open(hist, "w"))
        r2 = run(report, hist)
        check(r2.returncode == 0, f"re-run rc 應 0: {r2.stderr}")
        text2 = open(report).read()
        check("1.23 / 3.0" in text2, "re-run 應刷新 FACTS 區塊")
        check("-0.57 / 3.0" not in text2, "舊值應被替換")
        check(text2.count("<!--FACTS:decision_summary:start-->") == 1, "marker 不應重複")
        # 5) 未知 placeholder → rc=1
        bad = os.path.join(td, "bad.md")
        open(bad, "w").write("x\n<!--INJECT:not_a_block-->\n")
        r3 = run(bad, hist)
        check(r3.returncode == 1, "未知 placeholder 應 rc=1")
        # 6) 無 placeholder 舊報告 → rc=0 不改動
        plain = os.path.join(td, "plain.md")
        open(plain, "w").write("# 舊報告\n無佔位符\n")
        before = open(plain).read()
        r4 = run(plain, hist)
        check(r4.returncode == 0 and open(plain).read() == before, "無 placeholder 應 rc=0 且不改檔")
        # 7) validator 相容：注入後跑 validate_markdown_export --report
        val = os.path.join(HERE, "validate_markdown_export.py")
        r5 = subprocess.run([sys.executable, val, "--report", report],
                            capture_output=True, text=True)
        check(r5.returncode == 0, f"注入後 validate_markdown_export 應 rc=0: {r5.stdout} {r5.stderr}")

    print(f"✓ test_inject_report_facts: {n_pass}/{n_pass} asserts PASS")


if __name__ == "__main__":
    main()

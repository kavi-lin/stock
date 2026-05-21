# AI 投資委員會 — 產業掃描分數心算計算器 (Score Calculator)
import sys

def compute_deterministic_valuation_penalty(pe_zscore_1y: float | None, uptrend_ratio: float | None) -> int:
    """計算 V1.4 確定的估值懲罰 (Valuation Penalty Overlay):
    - pe_zscore_1y > 2.0 且 uptrend_ratio > 0.7: -10 (過熱派發風險)
    - pe_zscore_1y < -1.0 且 uptrend_ratio < 0.3: +5 (超賣價值機會)
    - 其他: 0
    """
    if pe_zscore_1y is None or uptrend_ratio is None:
        return 0
    if pe_zscore_1y > 2.0 and uptrend_ratio > 0.7:
        return -10
    if pe_zscore_1y < -1.0 and uptrend_ratio < 0.3:
        return 5
    return 0

def run_shadow_score_check(sector_data: dict, valuation_cache: dict | None) -> dict:
    """執行單個板塊的分數雙軌驗證 (Shadow Run)，回傳比對報告。
    
    階段合約定義:
    1. base_score: breadth_momentum + theme_heat + news_catalyst + rotation_signal (範圍 [0, 100])
    2. pre_step6_score: base_score + valuation_penalty, 限制在 [0, 100] (Step 1-5 調整後分數)
    3. post_step6_score: pre_step6_score * step6_fred_multiplier, 限制在 [0, 100]
    """
    name = sector_data.get("name", "Unknown")
    sc = sector_data.get("score_components", {})
    
    # ── 1. 計算 Base Score & Pre-Step 6 Score ──
    bm = sc.get("breadth_momentum", 0)
    th = sc.get("theme_heat", 0)
    nc = sc.get("news_catalyst", 0)
    rs = sc.get("rotation_signal", 0)
    llm_penalty = sc.get("valuation_penalty", 0)
    
    base_score = bm + th + nc + rs
    # 限制 base_score 範圍為 [0, 100]
    base_score = max(0, min(100, base_score))
    
    # 計算期望的 Valuation Penalty
    expected_penalty = 0
    if valuation_cache:
        sv = valuation_cache.get(name, {})
        pe_z = sv.get("pe_zscore_1y")
        ur = sector_data.get("uptrend_ratio")
        expected_penalty = compute_deterministic_valuation_penalty(pe_z, ur)
        
    pre_step6_score = base_score + llm_penalty
    pre_step6_score = max(0, min(100, pre_step6_score))
    
    # ── 2. 套用 Step 6 FRED Multiplier ──
    mult = sector_data.get("step6_fred_multiplier")
    if mult is not None:
        post_step6_score = round(pre_step6_score * mult, 2)
        post_step6_score_capped = round(max(0.0, min(100.0, post_step6_score)))
    else:
        post_step6_score_capped = round(pre_step6_score)
        
    # ── 3. 比對 LLM composite_score ──
    llm_composite = sector_data.get("composite_score", 0)
    diff = abs(llm_composite - post_step6_score_capped)
    
    return {
        "name": name,
        "base_score": base_score,
        "expected_valuation_penalty": expected_penalty,
        "llm_valuation_penalty": llm_penalty,
        "pre_step6_score": pre_step6_score,
        "calculated_post_score": post_step6_score_capped,
        "llm_composite_score": llm_composite,
        "diff": diff,
        "penalty_drift": expected_penalty != llm_penalty
    }

def verify_session_dual_run(sectors_report: list[dict]) -> tuple[bool, str]:
    """驗證整場 Session 的雙軌運行結果是否符合割接成功指標:
    - N=5 dual-run sessions
    - 0 個 hard diff > 1.0 (重大偏差)
    - <= 2 個 soft diff (0.5 - 1.0) (浮點四捨五入累積誤差)
    - 估值懲罰 penalty_drift 必須為 0 (強制估值 penalty 算術正確)
    """
    hard_errors = 0
    soft_errors = 0
    penalty_drifts = 0
    
    details = []
    for r in sectors_report:
        diff = r["diff"]
        name = r["name"]
        
        # 統計估值懲罰漂移
        if r["penalty_drift"]:
            penalty_drifts += 1
            details.append(f"  - {name}: Valuation Penalty drifted! Expected {r['expected_valuation_penalty']}, got {r['llm_valuation_penalty']}")
            
        # 統計分數漂移
        if diff > 1.0:
            hard_errors += 1
            details.append(f"  - {name}: Hard diff! Calculated {r['calculated_post_score']}, LLM got {r['llm_composite_score']} (diff={diff:.2f})")
        elif 0.5 < diff <= 1.0:
            soft_errors += 1
            details.append(f"  - {name}: Soft diff. Calculated {r['calculated_post_score']}, LLM got {r['llm_composite_score']} (diff={diff:.2f})")
            
    is_ok = (hard_errors == 0) and (soft_errors <= 2) and (penalty_drifts == 0)
    
    summary_msg = (
        f"[Calculator Dual-Run Check] Hard diffs: {hard_errors}, Soft diffs: {soft_errors}, Penalty drifts: {penalty_drifts}. "
        f"Status: {'✅ PASS' if is_ok else '❌ FAIL'}"
    )
    
    if details:
        summary_msg += "\n" + "\n".join(details)
        
    return is_ok, summary_msg

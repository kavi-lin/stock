#!/usr/bin/env python3
"""test_shadow_report.py — V4.108.0 FWD_PE_CLAMP 校準讀出端的契約測試。

鎖三件事：
  1. **反解算式本身**（implied_pe = price × (1+r)^h ÷ target_eps）——這是整個校準的
     量尺，算錯的話後面所有判準都是錯的，而且錯得很安靜。
  2. **判準只看 live cohort**。全母體混 archetype（MSFT 23x 與 NET 183x 同池），
     拿它出判準等於用錯的母體校準因果參數。
  3. **對舊 artifact 前向相容**：V4.108.0 之前的 `*_pf_quant.json` 沒有 calibration
     欄位，必須靜默略過而不是 crash——invest_logs 裡本來就存著這種檔。

Run: python3 investment/scripts/test_shadow_report.py   # rc=0 全過 / rc=1 fail
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from compute_price_framework import FWD_PE_CLAMP  # noqa: E402
from shadow_report import (  # noqa: E402
    FWD_PE_CALIB_MIN_N,
    section_fwd_pe_calibration,
)

FAILS = []


def eq(label, got, want, tol=0.01):
    ok = (got == want) if not isinstance(want, float) else (
        got is not None and abs(got - want) <= tol)
    if not ok:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


def artifact(ticker, *, price, eps, r, hz, status="eligible", pe=35.0,
             clamp="upper", date="2026-08-07", calibration=True,
             beta_source="profile", r_clamp=None):
    """最小可用的 pf_quant artifact——只放 section 真正會讀的欄位。"""
    entry = {"value": round(eps * pe / (1 + r) ** hz, 2), "status": status}
    if calibration:
        entry["calibration"] = {
            "target_fiscal_year": "2027-12-31", "target_eps": eps,
            "discount_rate": r, "horizon_years": hz,
            "justified_pe": pe, "justified_pe_raw": 999.0, "pe_clamp_binding": clamp,
            "growth_source": "eps_cagr", "beta_used": 2.73,
            "beta_source": beta_source, "discount_clamp_binding": r_clamp,
        }
    return date, ticker, {
        "ticker": ticker,
        "quant_blocks": {"valuation_pack": {
            "current_price": price,
            "anchors": {"fwd_earnings_discounted": entry},
        }},
    }


def write_dir(specs, tmp):
    for date, ticker, payload in specs:
        with open(os.path.join(tmp, f"{date}_{ticker}_pf_quant.json"), "w",
                  encoding="utf-8") as f:
            json.dump(payload, f)
    return tmp


# ── 1. 反解算式：手算基準 ────────────────────────────────────────────────────
# price 100 × (1.20)^2 ÷ eps 5.0 = 144 / 5 = 28.8
with tempfile.TemporaryDirectory() as tmp:
    write_dir([artifact("AAA", price=100.0, eps=5.0, r=0.20, hz=2.0)], tmp)
    out = section_fwd_pe_calibration(tmp)
    eq("math.implied_pe", out["rows"][0]["market_implied_pe"], 28.8)
    eq("math.n", out["n"], 1)
    eq("math.n_live", out["n_live"], 1)
    eq("math.no_verdict_below_min_n", out["verdict"], None)

# ── 2. 判準只看 live cohort ─────────────────────────────────────────────────
# live 五檔全部隱含 PE ≈ 28.8（低於上限 35）→ 上限對這個母體偏多。
# 另外塞兩檔 shadow 的極端值（NET 形狀，隱含 PE 上百），判準不得被它們拉動。
LOW = [artifact(f"L{i}", price=100.0, eps=5.0, r=0.20, hz=2.0) for i in range(5)]
SHADOW_EXTREME = [
    artifact("NETLIKE", price=300.0, eps=2.2, r=0.12, hz=2.4, status="ineligible"),
    artifact("MSFTLIKE", price=500.0, eps=18.0, r=0.10, hz=2.9, status="ineligible"),
]
with tempfile.TemporaryDirectory() as tmp:
    write_dir(LOW + SHADOW_EXTREME, tmp)
    out = section_fwd_pe_calibration(tmp)
    eq("cohort.n_all", out["n"], 7)
    eq("cohort.n_live", out["n_live"], 5)
    eq("cohort.live_median", out["live_cohort"]["implied_pe_median"], 28.8)
    eq("cohort.verdict_from_live", out["verdict"], "upper_clamp_structurally_bullish")
    eq("cohort.suggested_from_live", out["suggested_upper"], 28.8)
    # 極端 shadow 值只進全母體、不進 live——兩組的 max 相差一個量級才證明真的分開算
    eq("cohort.all_n", out["all_cohort"]["n"], 7)
    eq("cohort.live_max_excludes_shadow", out["live_cohort"]["implied_pe_max"], 28.8)
    eq("cohort.all_max_includes_shadow", out["all_cohort"]["implied_pe_max"] > 150, True)

# live 全部落在 clamp 帶正中（35 附近）→ centered
CENTERED = [artifact(f"C{i}", price=100.0, eps=5.0, r=0.20, hz=2.0)
            for i in range(2)] + [
    artifact(f"C{i}", price=150.0, eps=5.0, r=0.20, hz=2.0) for i in range(2, 5)]
with tempfile.TemporaryDirectory() as tmp:
    write_dir(CENTERED, tmp)
    out = section_fwd_pe_calibration(tmp)
    # 兩檔 28.8 + 三檔 43.2 → P33=28.8… P66=43.2，35 夾在中間
    eq("cohort.centered", out["verdict"], "upper_clamp_centered")

# live 全部遠高於上限 → 上限對這個母體偏空（EV/S 分位錨的失敗模式，必須抓得到）
HIGH = [artifact(f"H{i}", price=400.0, eps=5.0, r=0.20, hz=2.0) for i in range(5)]
with tempfile.TemporaryDirectory() as tmp:
    write_dir(HIGH, tmp)
    out = section_fwd_pe_calibration(tmp)
    eq("cohort.bearish", out["verdict"], "upper_clamp_structurally_bearish")
    eq("cohort.bearish_above_upper", out["live_cohort"]["above_upper"], 5)

# ── 3. 同標的多天 → 取最新一筆（常分析的標的不得主導母體）───────────────────
with tempfile.TemporaryDirectory() as tmp:
    write_dir([artifact("DUP", price=100.0, eps=5.0, r=0.20, hz=2.0, date="2026-08-01"),
               artifact("DUP", price=400.0, eps=5.0, r=0.20, hz=2.0, date="2026-08-07")], tmp)
    out = section_fwd_pe_calibration(tmp)
    eq("dedup.n", out["n"], 1)
    eq("dedup.keeps_latest", out["rows"][0]["market_implied_pe"], 115.2)
    eq("dedup.keeps_latest_date", out["rows"][0]["date"], "2026-08-07")

# ── 4. 前向相容 / fail-soft ─────────────────────────────────────────────────
with tempfile.TemporaryDirectory() as tmp:
    # 舊 artifact（無 calibration）+ 壞檔 + 無關檔案：全部靜默略過，不影響合法樣本
    write_dir([artifact("OLD", price=100.0, eps=5.0, r=0.20, hz=2.0, calibration=False),
               artifact("GOOD", price=100.0, eps=5.0, r=0.20, hz=2.0)], tmp)
    with open(os.path.join(tmp, "2026-08-07_BROKEN_pf_quant.json"), "w") as f:
        f.write("{not json")
    with open(os.path.join(tmp, "history.json"), "w") as f:
        f.write("[]")
    out = section_fwd_pe_calibration(tmp)
    eq("compat.skips_legacy_and_broken", out["n"], 1)
    eq("compat.keeps_good", out["rows"][0]["ticker"], "GOOD")

eq("missing_dir_no_crash", section_fwd_pe_calibration("/nonexistent/path/xyz")["n"], 0)

# ── 5. clamp 綁定統計 ───────────────────────────────────────────────────────
with tempfile.TemporaryDirectory() as tmp:
    write_dir([artifact("U1", price=100.0, eps=5.0, r=0.20, hz=2.0, clamp="upper"),
               artifact("U2", price=100.0, eps=5.0, r=0.20, hz=2.0, clamp="upper"),
               artifact("N1", price=100.0, eps=5.0, r=0.20, hz=2.0, clamp=None)], tmp)
    out = section_fwd_pe_calibration(tmp)
    eq("clamp.binding_n", out["upper_clamp_binding_n"], 2)
    eq("clamp.binding_rate", out["upper_clamp_binding_rate"], 0.6667, tol=0.001)
    eq("clamp.reports_current", out["current_clamp"],
       {"lower": FWD_PE_CLAMP[0], "upper": FWD_PE_CLAMP[1]})
    eq("clamp.min_n_exposed", out["min_n_for_verdict"], FWD_PE_CALIB_MIN_N)

# ── 6. beta fallback 率（資料品質訊號，不是校準參數）─────────────────────────
with tempfile.TemporaryDirectory() as tmp:
    write_dir([artifact("NEWLY_LISTED", price=100.0, eps=5.0, r=0.17, hz=2.0,
                        beta_source="population_median_fallback"),
               artifact("HIBETA", price=100.0, eps=5.0, r=0.30, hz=2.0, r_clamp="upper"),
               artifact("NORMAL", price=100.0, eps=5.0, r=0.20, hz=2.0)], tmp)
    out = section_fwd_pe_calibration(tmp)
    eq("beta.fallback_n", out["beta_fallback_n"], 1)
    eq("beta.fallback_rate", out["beta_fallback_rate"], 0.3333, tol=0.001)
    eq("beta.discount_clamp_n", out["discount_clamp_binding_n"], 1)

# ──────────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} regression(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ fwd PE calibration readout contract holds")

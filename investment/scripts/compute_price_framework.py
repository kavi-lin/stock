#!/usr/bin/env python3
"""compute_price_framework.py — V3.45.3 deterministic price framework engine.

Computes the ENTIRE Phase 4.5 price stack in one call (0 LLM arithmetic):
  1. fair_value_summary        — 8-anchor weighted blend (V4.69.0: +dcf_self_built
                                 +comps_implied，來源 skills/valuation-modeler)
  2. fair_value_range          — anchor distribution P25/P50/P75 + range_verdict +
                                 dispersion CV + owner-earnings multiple shadow (V3.45.1)
  3. multi_horizon_price_framework — 5d volatility band / 60d target / long-term ref /
                                 convergence mhp_signal (V5.1)
  4. implied_expectations      — reverse DCF implied 5Y FCF CAGR (V3.45.1)

Why a script: the V3.45.x spec accumulated math an LLM cannot reliably do inline
(weighted percentiles, CV, iterative reverse-DCF solve). Protocol discipline says
"禁止 LLM 重新評估數字" — this engine enforces it. PM calls this at Phase 3 Step 0
(all inputs are ready at end of Phase 2) and copies the output verbatim.

Volatility inputs (sigma_daily / atr_14 / momentum_20d_pct) are computed HERE from
FMP OHLCV when --ticker is given (eliminates LLM transcription risk); explicit
values in the input file override the fetch.

Usage:
  python3 investment/scripts/compute_price_framework.py --from-file /tmp/nvda_pf.json
  cat inputs.json | python3 investment/scripts/compute_price_framework.py
  python3 investment/scripts/compute_price_framework.py --from-file f.json --no-fetch

Staged mode (V4.88.0 — quant 提前 Phase 1.5)：六個 quant block 完全不吃 qualitative
lane 輸入（anchors / FRED / OHLCV 全由 engine 自組），所以可以在 Phase 2 lane fan-out
之前就算完；Phase 2.4 只剩 MHP 需要 technical/news lane 的 key_levels 與 catalyst。
  # Phase 1.5 — 產 quant artifact（預設寫 invest_logs/<DATE>_<TICKER>_pf_quant.json）
  python3 investment/scripts/compute_price_framework.py --from-file /tmp/nvda_pf.json \
      --self-assemble --stage quant
  # Phase 2.4 — 只算 MHP，quant block 從 artifact verbatim 併回（現價/sigma 不會重抓而漂移）
  python3 investment/scripts/compute_price_framework.py --from-file /tmp/nvda_qual.json \
      --stage mhp --from-quant investment/invest_logs/2026-08-02_NVDA_pf_quant.json
兩段合併輸出與單發模式逐位元一致（唯一例外：`valuation_pack.built_at` 是 quant 段的
時戳）——因為單發模式本身就是 build_quant_stage() → build_full_output() 的組合，
等價是結構保證而非事後比對。不給 --stage 即單發模式，行為與 V4.87.0 相同。

Input JSON shape (all price-level fields in the SAME per-share unit):
{
  "ticker": "NVDA",
  "current_price": 455.07,                  # required
  "anchors": {                              # deterministic source values (prefer --self-assemble)
    "dcf_unlevered": 495.8, "dcf_levered": null, "analyst_pt_consensus": 525.0,
    "peer_pe_implied": 480.0, "owner_earnings_mult": 410.0, "forecaster_blend": null
  },
  "anchor_meta": {                          # live eligibility requires provenance + as_of
    "dcf_unlevered": {"provenance": "earnings_analyst_bundle", "as_of": "2026-07-01"}
  },
  "structural_shift": {                     # optional typed gate; incomplete = advisory only
    "status": "CONFIRMED", "evidence_date": "2026-07-15", "provenance": "filing"
  },
  "volatility": {                           # optional — overrides FMP fetch
    "sigma_daily": 0.028, "atr_14": 12.5, "momentum_20d_pct": 8.2
  },
  "key_levels": {"support": 415.0, "resistance": 500.0, "pivot": 460.0},
  "pattern_taxonomy": "pullback_in_uptrend",
  "smart_money_label": "accumulating",
  "immediate_catalyst_5d": {"event": "Q2 earnings", "date": "2026-08-13",
                            "direction_lean": "BULLISH", "expected_move_pct": 5.5},
  "fred": {"treasury_10y": 0.041, "treasury_10y_real": 0.018},   # decimals
  "reverse_dcf": {                          # optional block
    "fcf_base_per_share": 14.2,             # owner earnings per share (Burry rule 3)
    "actual_3y_fcf_cagr": 0.14, "lane_fcf_estimate": 0.18
  }
}

Output: single JSON object on stdout with canonical valuation_pack + projections/advisory blocks. rc=0 even
when sub-blocks degrade to null (degradation is data, not failure); rc=1 only on
unusable input (missing current_price / unparseable JSON).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

ENGINE_VERSION = "compute_price_framework.py v2.4 (V4.131.13)"

# Staged mode (V4.88.0). QUANT_BLOCK_KEYS = 完全由 engine-owned 決定論輸入算出的
# block；MHP_QUALITATIVE_KEYS = 唯一需要等 Phase 2 lane 的欄位。
QUANT_STAGE_SCHEMA = "price_framework_quant.v1"
QUANT_BLOCK_KEYS = (
    "valuation_pack", "fair_value_summary", "fair_value_range",
    "implied_expectations", "valuation_archetype_shadow", "forward_validation",
    "valuation_explained_range",
)
MHP_QUALITATIVE_KEYS = (
    "pattern_taxonomy", "smart_money_label", "key_levels", "immediate_catalyst_5d",
)

# ── Constants (B3 — 兩組常數用途不同，集中定義並註明) ─────────────────────────
# WACC for reverse DCF: nominal 10Y + full equity risk premium (discounting nominal FCF).
ERP_WACC = 0.045
WACC_FALLBACK_RF = 0.045        # FRED unavailable → long-run nominal 10Y proxy
# Required earnings yield for owner-earnings multiple shadow: REAL 10Y + a lower
# premium (owner earnings already grow with inflation, so the real rate is the
# correct base and the premium excludes the inflation-compensation component).
ERP_EARNINGS_YIELD = 0.04

TERMINAL_GROWTH = 0.025
IMPLIED_CAGR_CLAMP = (-0.20, 0.60)
OE_MULT_CLAMP = (10.0, 22.0)

# V4.108.0 — reverse DCF 對 FCF ≤ 0 的公司無定義（AAOI 實測直接棄權），但「市場在
# 定價什麼」對這種標的恰恰是最該問的問題。改問營收：在 EV 不變的前提下，營收要成長
# 幾倍、年化幾 % 才能把今天的 EV/S 消化到目標倍數。這是 diagnostic 不是 anchor
# ——不進權重、不進 verdict，只餵 Red Team 與 speculative governor。
#
# 兩個 terminal 是刻意的，因為這個假設的槓桿極大（AAOI：4x → 需 32% CAGR；8x → 15%），
# 藏在單一常數裡等於把結論藏起來：
#   CONSERVATIVE 4.0  = **規範性**假設：「倍數正常化到無題材光環的硬體業」。它不是實測
#                       中樞——2026-08-07 量測成熟獲利公司 median EV/S：半導體 13.9、
#                       通訊設備 8.3、軟體 8.0、工業/包裝 2.8。4.0 大約在工業水準，
#                       對科技股刻意保守，當壓力測試用。
#   SECTOR_TYPICAL 8.0 = 同次量測的科技中樞（通訊設備 8.26 / 軟體 7.99）。標為「情境」
#                       而非基準是因為它有循環性：拿今天正在 re-rating 的可比公司當
#                       「成熟終值」（LITE 28.1x、PE 143）會讓門檻自動變低。
TERMINAL_EV_SALES = 4.0
TERMINAL_EV_SALES_SECTOR_TYPICAL = 8.0
IMPLIED_REVENUE_HORIZON_Y = 5.0

# V4.72.1 (user 核准 2026-07-16) — agreement_grade 門檻改歷史 33/66 percentile。
# 原初值 0.15/0.35 把 28/30 session 判 low（歷史 cv 中位數 0.45，8 個異方法錨對
# 科技股天生散）——93% 時間亮的警示燈無資訊量。SHADOW_REPORT_2026-07-16 校準：
# n=67，P33=0.3751 / P66=0.5207。⚠ 此校準基於「修剪前」anchors；P0-3 trim 上線後
# cv 分佈會左移（NVDA 例 0.341→0.188），累積 ≥20 筆修剪後 session 需重新校準（TODO）。
AGREEMENT_GRADE_HIGH_CV = 0.375   # cv < this → high
AGREEMENT_GRADE_LOW_CV = 0.52     # cv >= this → low；中間 → medium

# V4.69.0 — 8 anchors。家族層權重不變（DCF 族 0.45 / 倍數族 0.30 / 市場預期 0.25），
# 只動族內拆分：新增 dcf_self_built（valuation-modeler 自建 driver-based DCF）與
# comps_implied（EV/EBITDA + EV/Sales + PEG implied 中位數；P/E 排除防與
# peer_pe_implied 重複計權）。兩個新 anchor 缺值時照舊重分配。
LEGACY_ANCHOR_WEIGHTS = {
    "dcf_unlevered": 0.20,
    "dcf_levered": 0.10,
    "dcf_self_built": 0.15,
    "analyst_pt_consensus": 0.20,
    "peer_pe_implied": 0.15,
    "comps_implied": 0.10,
    "owner_earnings_mult": 0.05,
    "forecaster_blend": 0.05,
}

# ── V4.108.0 — anchor 9: fwd_earnings_discounted（虧損中的題材成長股）─────────
# 為什麼要第 9 根：八根 live anchor 全部要求「現在」就有正的現金流／盈餘（DCF 族、
# owner earnings）或 ≥3 家同業（倍數族）。還在虧損、又沒有可比同業的題材股兩者都拿
# 不到——AAOI 2026-08-07 實測八根全 null → anchors_available=0 → insufficient_anchors
# 把決策直接封死。這根把「市場在追的那個未來」本身變成可證偽的數字：取分析師覆蓋
# 足夠的最遠獲利年度 EPS，乘一個受限的 justified P/E，用 CAPM 門檻利率折回今天。
#
# 它的 raw weight 刻意留在 LEGACY_ANCHOR_WEIGHTS 的 1.0 預算之外：live 資格只在
# cashflow_intrinsic 整組（raw 權重合計 0.50）結構性缺席時才開（見
# evaluate_fwd_anchor_scope），所以它永遠不會擠掉任何一根既有 anchor 的權重。
FWD_EARNINGS_RAW_WEIGHT = 0.15
ANCHOR_WEIGHTS = {**LEGACY_ANCHOR_WEIGHTS,
                  "fwd_earnings_discounted": FWD_EARNINGS_RAW_WEIGHT}

FWD_MIN_ANALYSTS = 3               # 目標年度 EPS 覆蓋數；strict 模式缺 → fail closed
FWD_MAX_HORIZON_YEARS = 3.5        # 更遠的預估不可用（覆蓋薄且沒人能預測那麼遠）
FWD_PE_CLAMP = (15.0, 35.0)        # justified P/E 上下限（成長率再高也不給第 36 倍）
FWD_PEG_FACTOR = 1.0               # justified P/E = 成長率(%) × factor
FWD_DISCOUNT_CLAMP = (0.10, 0.30)  # CAPM 門檻利率；低 beta 的題材股也不得低於 10%
# 無效 beta（≤0 或缺）**不得**解讀成「市場級風險」而落到折現率下限——這根錨服務的母體
# 定義上就比市場危險，那等於把資料缺陷換成最寬鬆的折現。實例：SPCX beta=0（IPO
# 2026-06-12，歷史不足兩個月）原本吃到 10% 下限，是整組樣本裡最寬鬆的一檔。
# 2.73 = 題材股母體 valid beta 中位數（n=14，2026-08-07 量測；重新量測見 TODO）。
FWD_BETA_FALLBACK = 2.73
CASHFLOW_INTRINSIC_ANCHORS = ("dcf_unlevered", "dcf_levered", "dcf_self_built",
                              "owner_earnings_mult")
# 同一批賣方分析師餵養的錨。兩根同時 eligible 時 family topology 會給它們各一票，
# 但那不是兩份獨立證據——build_valuation_pack 因此另外標記 sell_side_only，由
# decision_engine 的 speculative governor 限制倉位（不是拒絕決策）。
# forecaster_blend 不列入：它的 cagr / trend 兩法用歷史實績，不是純 consensus。
SELL_SIDE_ANCHORS = ("analyst_pt_consensus", "fwd_earnings_discounted")

# Canonical valuation topology.  Anchor-level weights above remain as legacy
# audit metadata; live aggregation happens group -> family -> portfolio so
# correlated methods do not receive independent votes.
ANCHOR_TOPOLOGY = {
    "dcf_unlevered": ("fundamental", "cashflow_intrinsic"),
    "dcf_levered": ("fundamental", "cashflow_intrinsic"),
    "dcf_self_built": ("fundamental", "cashflow_intrinsic"),
    "owner_earnings_mult": ("fundamental", "cashflow_intrinsic"),
    "forecaster_blend": ("fundamental", "earnings_projection"),
    "fwd_earnings_discounted": ("fundamental", "earnings_projection"),
    "peer_pe_implied": ("relative", "peer_relative"),
    "comps_implied": ("relative", "peer_relative"),
    "analyst_pt_consensus": ("external_expectations", "external_pt"),
}
FAMILY_WEIGHTS = {
    "fundamental": 0.55,
    "relative": 0.25,
    "external_expectations": 0.20,
}
VALUATION_PACK_SCHEMA = "valuation_pack.v1"
PT_MAX_AGE_DAYS = 180

DRIFT_BY_PATTERN = {
    "uptrend_breakout": 0.30,
    "uptrend_continuation": 0.20,
    "pullback_in_uptrend": 0.10,
    "oversold_bounce_attempt": 0.10,
    "consolidation": 0.00,
    "false_breakout": -0.20,
    "topping_pattern": -0.30,
    "downtrend": -0.50,
}
SMART_MONEY_NUDGE = {"accumulating": 0.10, "distributing": -0.10, "mixed": 0.0, "neutral": 0.0}
DRIFT_CLAMP = (-0.60, 0.50)
Z80 = 1.28
SQRT5 = math.sqrt(5)

MID_WEIGHTS = {"momentum": 0.40, "pt_60d": 0.35, "earnings_revision": 0.25}
MOMENTUM_DECAY = 0.50
PT_PULL_FACTOR = 1.00

# ── V3.46.0 — Valuation archetype (shadow-only; live weights untouched) ──────
# 判定門檻（初值，#3b 切換前用累積數據校準）
HYPERGROWTH_REV_YOY = 0.25       # rev YoY > 25%
MATURE_FCF_MARGIN = 0.08         # FCF margin > 8%
MATURE_REV_YOY = 0.15            # rev YoY < 15%
CYCLICAL_MARGIN_SIGMA_PP = 5.0   # 8Q 淨利率 σ > 5pp
CYCLICAL_SECTORS = ("Technology", "Energy", "Basic Materials", "Materials", "Industrials")
FINANCIAL_SECTORS = ("Financial Services", "Financials")

# 11-anchor 池 archetype 權重表（shadow blend 用；V4.69.0 起含 dcf_self_built /
# comps_implied 兩個 live 新 anchor）。balanced = live 權重 + shadow-only anchor 0。
# financial 的兩個新 anchor 刻意 0：FCFF DCF 對金融股無意義、comps 的 EV 指標同理。
ARCHETYPE_WEIGHTS = {
    "mature_cashflow": {
        "dcf_unlevered": 0.20, "dcf_levered": 0.10, "dcf_self_built": 0.10,
        "analyst_pt_consensus": 0.15, "peer_pe_implied": 0.10, "comps_implied": 0.05,
        "owner_earnings_mult": 0.15, "forecaster_blend": 0.05,
        "fwd_earnings_discounted": 0.0,
        "peer_ev_ebitda_implied": 0.10, "peer_ev_sales_implied": 0.0, "pb_roe_justified": 0.0,
    },
    # V4.108.0：fwd_earnings_discounted 是 hypergrowth shadow 池唯一的新成員，權重與
    # live 表同樣掛在 1.0 預算之外——既有 11 根的相對權重一位元都不動，#3b 翻轉率報告
    # 才能把差異單一歸因到「多了這根」，而不是混進一次重分配。
    "hypergrowth": {
        "dcf_unlevered": 0.10, "dcf_levered": 0.05, "dcf_self_built": 0.10,
        "analyst_pt_consensus": 0.20, "peer_pe_implied": 0.0, "comps_implied": 0.10,
        "owner_earnings_mult": 0.0, "forecaster_blend": 0.10,
        "fwd_earnings_discounted": FWD_EARNINGS_RAW_WEIGHT,
        "peer_ev_ebitda_implied": 0.15, "peer_ev_sales_implied": 0.20, "pb_roe_justified": 0.0,
    },
    "cyclical": {
        "dcf_unlevered": 0.15, "dcf_levered": 0.10, "dcf_self_built": 0.10,
        "analyst_pt_consensus": 0.15, "peer_pe_implied": 0.10, "comps_implied": 0.05,
        "owner_earnings_mult": 0.10, "forecaster_blend": 0.05,
        "fwd_earnings_discounted": 0.0,
        "peer_ev_ebitda_implied": 0.20, "peer_ev_sales_implied": 0.0, "pb_roe_justified": 0.0,
    },
    "financial": {
        "dcf_unlevered": 0.05, "dcf_levered": 0.05, "dcf_self_built": 0.0,
        "analyst_pt_consensus": 0.30, "peer_pe_implied": 0.20, "comps_implied": 0.0,
        "owner_earnings_mult": 0.0, "forecaster_blend": 0.05,
        "fwd_earnings_discounted": 0.0,
        "peer_ev_ebitda_implied": 0.0, "peer_ev_sales_implied": 0.0, "pb_roe_justified": 0.35,
    },
    "balanced": {**LEGACY_ANCHOR_WEIGHTS, "fwd_earnings_discounted": 0.0,
                 "peer_ev_ebitda_implied": 0.0,
                 "peer_ev_sales_implied": 0.0, "pb_roe_justified": 0.0},
}


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def _pos(x):
    v = _num(x)
    return v if v is not None and v > 0 else None


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ── Weighted statistics ───────────────────────────────────────────────────────
def weighted_mean(vals, wts):
    s = sum(wts)
    return sum(v * w for v, w in zip(vals, wts)) / s if s else None


def weighted_std(vals, wts):
    m = weighted_mean(vals, wts)
    if m is None:
        return None
    s = sum(wts)
    var = sum(w * (v - m) ** 2 for v, w in zip(vals, wts)) / s
    return math.sqrt(var)


def weighted_percentile(vals, wts, q):
    """Weighted percentile via cumulative-weight interpolation on sorted values."""
    pairs = sorted(zip(vals, wts))
    total = sum(w for _, w in pairs)
    if total <= 0:
        return None
    cum, points = 0.0, []
    for v, w in pairs:
        points.append((cum + w / 2, v))   # midpoint convention
        cum += w
    target = q * total
    if target <= points[0][0]:
        return points[0][1]
    if target >= points[-1][0]:
        return points[-1][1]
    for (c0, v0), (c1, v1) in zip(points, points[1:]):
        if c0 <= target <= c1:
            t = (target - c0) / (c1 - c0) if c1 > c0 else 0.0
            return v0 + t * (v1 - v0)
    return points[-1][1]


def median(vals):
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _verdict_band(vs_pct: float) -> str:
    if vs_pct >= 30:
        return "extreme_undervalued"
    if vs_pct >= 10:
        return "undervalued"
    if vs_pct >= -10:
        return "fairly_valued"
    if vs_pct >= -30:
        return "overvalued"
    return "extreme_overvalued"


def _valuation_score(vs_pct: float | None, family_values: dict) -> float | None:
    """Deterministic -3..+3 score with independent-family guard."""
    if vs_pct is None:
        return None
    if vs_pct >= 30:
        score = 3.0
    elif vs_pct >= 20:
        score = 2.0
    elif vs_pct >= 10:
        score = 1.0
    elif vs_pct <= -30:
        score = -3.0
    elif vs_pct <= -20:
        score = -2.0
    elif vs_pct <= -10:
        score = -1.0
    else:
        score = 0.0
    votes = [1 if v >= 1.10 else -1 if v <= 0.90 else 0
             for v in family_values.values()]
    same_direction = votes.count(1) if score > 0 else votes.count(-1)
    if abs(score) >= 2 and same_direction < 2:
        score = 1.0 if score > 0 else -1.0
    return score


def _stable_hash(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def _iso_date(value) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


# ── V4.108.0 — anchor 9 computation ──────────────────────────────────────────
def compute_fwd_earnings_anchor(estimates, *, today: dt.date | None = None,
                                beta=None, treasury_10y=None) -> dict:
    """Price the first credibly-covered profitable year back to today.

    Deliberately peer-free: 題材股最常見的失敗模式就是「沒有可比同業」（AAOI 的
    exact-industry peer set = 0），任何吃 peer median 的方法在這個 archetype 上會
    重複踩同一個坑。這裡只用分析師 EPS 預估 + CAPM 折現率。

    目標年度取 horizon 內**最遠**一個覆蓋足夠的獲利年度（取最近的那個會把公司價值
    低估成「僅僅一年的盈餘」——第一個轉盈年之後的所有年份都還在）。覆蓋數與 horizon
    上限就是防止這個選擇滑進沒人真的在預測的遠方。

    Returns a detail dict；任何一道 gate 沒過 → value=None + reason（不是例外）。
    """
    today = today or dt.date.today()
    detail = {
        "value": None, "reason": None, "target_fiscal_year": None, "target_eps": None,
        "analyst_count": None, "justified_pe": None, "justified_pe_raw": None,
        "pe_clamp_binding": None, "growth_used": None,
        "growth_source": None, "discount_rate": None, "discount_clamp_binding": None,
        "horizon_years": None, "beta_used": None, "beta_source": None,
        "beta": _num(beta), "risk_free": _num(treasury_10y),
    }
    # 過去年度**保留**在序列裡：目標年只從未來年度挑，但成長率的分母要用它前一個
    # 年度——目標年正好是第一個未來年度時，那個分母就是最近的已實現年度。
    rows = sorted(
        ((d, row) for row, d in ((r, _iso_date((r or {}).get("date")))
                                 for r in (estimates or []) if isinstance(r, dict))
         if d is not None),
        key=lambda pair: pair[0],
    )
    if not any(d > today for d, _ in rows):
        detail["reason"] = "no_future_analyst_estimates"
        return detail

    def _analysts(row):
        return _num(row.get("numAnalystsEps")) or _num(row.get("numAnalystEstimatedEps"))

    eligible_idx = [
        i for i, (d, row) in enumerate(rows)
        if d > today
        and _pos(row.get("epsAvg")) is not None
        and (_analysts(row) or 0) >= FWD_MIN_ANALYSTS
        and (d - today).days / 365.25 <= FWD_MAX_HORIZON_YEARS
    ]
    if not eligible_idx:
        detail["reason"] = (
            f"no_estimate_year_with_positive_eps_and_{FWD_MIN_ANALYSTS}_analysts"
            f"_within_{FWD_MAX_HORIZON_YEARS:g}y")
        return detail

    idx = eligible_idx[-1]
    target_date, target = rows[idx]
    target_eps = _pos(target.get("epsAvg"))
    horizon = max((target_date - today).days / 365.25, 0.25)

    # justified P/E ← PEG。EPS CAGR 優先；轉盈年之前 EPS ≤ 0 使 CAGR 無定義時退回
    # 營收 CAGR（近似，已標在 growth_source）。兩者皆不可得 → 放棄，不猜。
    growth, growth_source = None, None
    if idx > 0:
        prior_date, prior = rows[idx - 1]
        span = max((target_date - prior_date).days / 365.25, 0.25)
        prior_eps = _pos(prior.get("epsAvg"))
        if prior_eps:
            growth, growth_source = (target_eps / prior_eps) ** (1 / span) - 1, "eps_cagr"
        else:
            prior_rev, target_rev = _pos(prior.get("revenueAvg")), _pos(target.get("revenueAvg"))
            if prior_rev and target_rev:
                growth, growth_source = (target_rev / prior_rev) ** (1 / span) - 1, "revenue_cagr"
    if growth is None:
        detail["reason"] = "no_usable_growth_rate_for_justified_pe"
        return detail

    # 校準原料：pre-profit 標的的成長率幾乎必然爆表，PE 因此恆取上限——上限是不是
    # 對的，就成了這根錨最關鍵的一個假設。把「原始值」與「綁到哪一端」一起留下來，
    # shadow_report 的校準區塊才能用 grep 回答「上限綁到的頻率」而不必重算。
    justified_pe_raw = growth * 100 * FWD_PEG_FACTOR
    justified_pe = clamp(justified_pe_raw, *FWD_PE_CLAMP)
    pe_clamp_binding = ("upper" if justified_pe_raw > FWD_PE_CLAMP[1]
                        else "lower" if justified_pe_raw < FWD_PE_CLAMP[0] else None)
    rf = _num(treasury_10y)
    rf = WACC_FALLBACK_RF if rf is None else rf
    b_raw = _num(beta)
    if b_raw is None or b_raw <= 0:
        b_used, beta_source = FWD_BETA_FALLBACK, "population_median_fallback"
    else:
        b_used, beta_source = b_raw, "profile"
    r_raw = rf + b_used * ERP_WACC
    r = clamp(r_raw, *FWD_DISCOUNT_CLAMP)
    discount_clamp_binding = ("upper" if r_raw > FWD_DISCOUNT_CLAMP[1]
                              else "lower" if r_raw < FWD_DISCOUNT_CLAMP[0] else None)

    detail.update({
        "value": round(target_eps * justified_pe / (1 + r) ** horizon, 2),
        "target_fiscal_year": target_date.isoformat(),
        "target_eps": round(target_eps, 4),
        "analyst_count": int(_analysts(target) or 0),
        "justified_pe": round(justified_pe, 2),
        "justified_pe_raw": round(justified_pe_raw, 2),
        "pe_clamp_binding": pe_clamp_binding,
        "growth_used": round(growth, 4),
        "growth_source": growth_source,
        "discount_rate": round(r, 4),
        "discount_clamp_binding": discount_clamp_binding,
        "beta_used": round(b_used, 4),
        "beta_source": beta_source,
        "horizon_years": round(horizon, 3),
    })
    return detail


def evaluate_fwd_anchor_scope(inp: dict) -> tuple[bool, str | None]:
    """Live 資格：只在所有內在價值法結構性無定義時才開。

    這道閘是「只填真空、不排擠」的執行點——任何一根 cashflow_intrinsic 錨還活著，
    或公司本來就有正的 TTM EPS，這根就退回 shadow（值照樣算、照樣進 archetype
    shadow 池，只是不進 live blend）。
    """
    anchors = inp.get("anchors") or {}
    meta = inp.get("anchor_meta") or {}
    live = []
    for name in CASHFLOW_INTRINSIC_ANCHORS:
        if _pos(anchors.get(name)) is None:
            continue
        m = meta.get(name) or {}
        if m.get("eligible") is False:
            continue
        if (m.get("model_eligibility") or {}).get("eligible") is False:
            continue
        live.append(name)
    if live:
        return False, f"cashflow_intrinsic_anchors_live:{','.join(live)}"
    eps_ttm = _num((inp.get("archetype_inputs") or {}).get("eps_ttm"))
    if eps_ttm is not None and eps_ttm > 0:
        return False, "profitable_issuer_shadow_only"
    return True, None


# pack entry 的 calibration 欄位鍵；reverse-implied PE 的重算只需要前四個
# （implied_pe = price × (1+discount_rate)^horizon_years ÷ target_eps）。
CALIBRATION_KEYS = ("target_fiscal_year", "target_eps", "analyst_count", "discount_rate", "horizon_years",
                    "justified_pe", "justified_pe_raw", "pe_clamp_binding", "growth_source",
                    "beta_used", "beta_source", "discount_clamp_binding")


def _calibration_block(meta: dict) -> dict | None:
    block = {k: meta.get(k) for k in CALIBRATION_KEYS}
    return block if any(v is not None for v in block.values()) else None


#: Anchors whose value can only come from running a script, mapped to the
#: artifact that script writes and the command that writes it.
#:
#: `forecaster_blend` is deliberately NOT here. Its cache
#: (`skills/earnings-valuation-forecaster/cache/<T>.json`) is also written by the
#: earnings-preview flow, so its presence would not prove *this* session ran the
#: forecaster — the discriminator would be unsound. It also already reports a
#: distinct reason when it does run and declines (`low_forecast_confidence`).
#: `required_keys` is what makes this a content check rather than a presence
#: check. V4.116.0 shipped presence only, and `echo '{}' > <T>_dcf_payload.json`
#: walked straight through it — which matters because the behaviour this gate
#: exists to catch is an agent that responded to a blocked gate by making the
#: input fit (the 2026-08-09 Phase 0 copy). A gate that can be satisfied by
#: `touch` just moves such an agent to a cheaper bypass.
SCRIPT_SOURCED_ANCHORS = {
    "dcf_self_built": {
        "artifact": "skills/valuation-modeler/cache/{t}_dcf_payload.json",
        "command": "python3 skills/valuation-modeler/scripts/dcf.py {t} --json-only",
        "value_key": "fair_value_per_share",
        "required_keys": ("ticker", "asof", "fair_value_per_share",
                          "degraded", "assumptions"),
    },
    "comps_implied": {
        "artifact": "skills/valuation-modeler/cache/{t}_comps_payload.json",
        "command": "python3 skills/valuation-modeler/scripts/comps.py {t} --json-only",
        "value_key": "comps_implied_value",
        "required_keys": ("ticker", "asof", "comps_implied_value",
                          "degraded", "table"),
    },
}

#: The script ran and its artifact carries a usable number, but the anchor came
#: through empty — the value was computed and then lost between the script and
#: the pack. Distinct from `script_not_run` because the fix is different: this
#: one is a wiring bug, not a skipped step.
ANCHOR_DROPPED_VALUE = "anchor_dropped_script_value"

#: How recent a script artifact must be to count as "this session's". Matches the
#: Phase 0 gate's default for the same reason: a run that starts before midnight
#: and finishes after it is legitimate, and one day is the coarsest unit that
#: still excludes a stale payload.
SCRIPT_ARTIFACT_MAX_AGE_DAYS = 1

SCRIPT_NOT_RUN = "script_not_run"


def mark_unrun_anchor_scripts(ticker, anchors: dict | None, anchor_meta: dict,
                              *, now: float | None = None,
                              max_age_days: int = SCRIPT_ARTIFACT_MAX_AGE_DAYS,
                              base_dir: str | None = None) -> dict:
    """Separate "the script produced nothing usable" from "it was never run".

    Both used to arrive as `missing_or_nonpositive_value`, and that conflation is
    what let the 2026-08-09 NOW session skip Phase 1.5's two mandatory valuation
    scripts without anything noticing. The engine then did exactly the right
    thing for an ineligible anchor — redistribute its weight — and
    `owner_earnings_mult` went from a raw 0.05 to an effective 0.275, producing
    the `extreme_overvalued` verdict on its own. Nothing downstream could tell,
    because nothing downstream knew the difference between the two cases.

    This only fires when the anchor has NO value: a value present means the
    script ran, whatever the artifact looks like. The artifact must also be
    recent — a month-old payload says nothing about this session.

    Returns a NEW metadata dict; the caller's is not mutated.
    """
    out = {k: dict(v) if isinstance(v, dict) else v for k, v in (anchor_meta or {}).items()}
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return out                      # pure-function callers pass no ticker
    root = base_dir or BASE_DIR
    now = now if now is not None else dt.datetime.now().timestamp()
    cutoff = max_age_days * 86400

    for name, spec in SCRIPT_SOURCED_ANCHORS.items():
        if _pos((anchors or {}).get(name)) is not None:
            continue                    # it produced a value; it ran
        meta = out.setdefault(name, {})
        if not isinstance(meta, dict):
            continue
        if meta.get("reason"):
            continue                    # an upstream reason is more specific

        artifact = os.path.join(root, spec["artifact"].format(t=ticker))
        payload = None
        try:
            if (now - os.path.getmtime(artifact)) <= cutoff:
                with open(artifact, "r", encoding="utf-8") as fp:
                    payload = json.load(fp)
        except (OSError, json.JSONDecodeError):
            payload = None

        # Credible = this script's own output, for this ticker, with the shape it
        # actually emits. Anything less is treated as not-run, because a file
        # that merely exists proves nothing about whether the script ran.
        credible = (
            isinstance(payload, dict)
            and str(payload.get("ticker") or "").strip().upper() == ticker
            and all(k in payload for k in spec["required_keys"])
        )
        if not credible:
            meta["reason"] = SCRIPT_NOT_RUN
            continue

        # Ran, and produced a number the anchor should have carried. Something
        # between the script and the pack dropped it.
        if _pos(payload.get(spec["value_key"])) is not None:
            meta["reason"] = ANCHOR_DROPPED_VALUE
        # else: ran and had nothing usable to say — a legitimate ineligibility,
        # left to the existing `missing_or_nonpositive_value`.
    return out


def _anchor_eligibility(name: str, value, meta: dict, structural_shift: dict,
                        strict_metadata: bool) -> tuple[bool, str | None]:
    if _pos(value) is None:
        return False, meta.get("reason") or "missing_or_nonpositive_value"
    provenance, as_of = meta.get("provenance"), meta.get("as_of")
    if strict_metadata and not provenance:
        return False, "missing_provenance"
    if strict_metadata and not as_of:
        return False, "missing_as_of"
    if meta.get("eligible") is False:
        return False, meta.get("reason") or "source_marked_ineligible"
    model = meta.get("model_eligibility") or {}
    if model.get("eligible") is False:
        return False, model.get("reason") or "model_ineligible"
    if name == "forecaster_blend":
        if str(meta.get("confidence") or "").upper() == "LOW":
            return False, "low_forecast_confidence"
        if _num(meta.get("usable_methods")) is not None and meta["usable_methods"] < 2:
            return False, "fewer_than_2_usable_methods"
        if meta.get("transition_case") is True:
            return False, "transition_without_safe_model"
    if name == "fwd_earnings_discounted":
        n_analysts = _num(meta.get("analyst_count"))
        if strict_metadata and n_analysts is None:
            return False, "missing_analyst_count"
        if n_analysts is not None and n_analysts < FWD_MIN_ANALYSTS:
            return False, f"fewer_than_{FWD_MIN_ANALYSTS}_analysts_on_target_year"
        horizon = _num(meta.get("horizon_years"))
        if strict_metadata and horizon is None:
            return False, "missing_forecast_horizon"
        if horizon is not None and horizon > FWD_MAX_HORIZON_YEARS:
            return False, "forecast_horizon_beyond_limit"
    if name in ("peer_pe_implied", "comps_implied"):
        pc = _num(meta.get("peer_count"))
        if strict_metadata and pc is None:
            return False, "missing_peer_count"
        if pc is not None and pc < 3:
            return False, "fewer_than_3_exact_industry_peers"
    if name == "analyst_pt_consensus" and strict_metadata:
        try:
            pt_date = dt.date.fromisoformat(str(as_of)[:10])
        except (TypeError, ValueError):
            return False, "invalid_pt_as_of"
        if (dt.date.today() - pt_date).days > PT_MAX_AGE_DAYS:
            return False, "stale_analyst_pt"
    if name == "analyst_pt_consensus" and isinstance(structural_shift, dict):
        confirmed = (structural_shift.get("confirmed") is True or
                     str(structural_shift.get("status") or "").upper() == "CONFIRMED")
        evidence_date = str(structural_shift.get("evidence_date") or "")[:10]
        shift_prov = structural_shift.get("provenance")
        # Incomplete shift evidence is advisory and cannot suppress a live PT.
        if confirmed and evidence_date and shift_prov and as_of:
            if str(as_of)[:10] <= evidence_date:
                return False, "predates_structural_shift"
    return True, None


def build_valuation_pack(anchors: dict, current_price: float, *,
                         anchor_meta: dict | None = None,
                         structural_shift: dict | None = None,
                         strict_metadata: bool = True) -> dict:
    """Build the single authoritative valuation result for a session."""
    anchor_meta = anchor_meta or {}
    structural_shift = structural_shift or {}
    entries = {}
    grouped: dict[str, dict[str, list[float]]] = {}
    group_members: dict[str, list[str]] = {}
    for name in ANCHOR_WEIGHTS:
        value = _pos((anchors or {}).get(name))
        meta = dict(anchor_meta.get(name) or {})
        family, base_group = ANCHOR_TOPOLOGY[name]
        assumption_inputs = meta.get("assumption_inputs")
        assumption_hash_inputs = {
            "as_of": meta.get("as_of"),
            "provenance": meta.get("provenance"),
            "inputs": assumption_inputs,
        }
        # Legacy pure-function callers have no metadata. Preserve their former
        # per-anchor behavior without weakening live strict-mode correlation.
        if not strict_metadata:
            assumption_hash_inputs["legacy_anchor"] = name
        assumption_set_id = meta.get("assumption_set_id") or _stable_hash(assumption_hash_inputs)
        # Explicit lineage lets sibling anchors share a group; otherwise the
        # fixed mapping supplies the conservative correlation bucket.
        lineage_group = meta.get("correlation_key")
        correlation_group = f"{base_group}:{lineage_group or assumption_set_id}"
        eligible, reason = _anchor_eligibility(
            name, value, meta, structural_shift, strict_metadata,
        )
        status = "eligible" if eligible else "ineligible"
        entries[name] = {
            "value": value,
            "family": family,
            "correlation_group": correlation_group,
            "assumption_set_id": assumption_set_id,
            "provenance": meta.get("provenance"),
            "as_of": meta.get("as_of"),
            "input_lineage_ids": meta.get("input_lineage_ids") or [],
            "status": status,
            "reason": reason,
            "weight_raw": ANCHOR_WEIGHTS[name],
            "weight_effective": 0.0,
            "projection_mode": meta.get("projection_mode"),
            "sensitivity_low": _pos(meta.get("sensitivity_low")),
            "sensitivity_high": _pos(meta.get("sensitivity_high")),
            # anchor 自帶的校準原料（目前只有 fwd_earnings_discounted 有；其餘為 None）。
            # 放進 pack 而不是只留在 anchor_meta，是因為 export 只帶 pack——沒有這一格，
            # 未來要從 history.json 做結果回測時就得回頭重算輸入。
            "calibration": _calibration_block(meta),
        }
        if eligible:
            grouped.setdefault(family, {}).setdefault(correlation_group, []).append(value)
            group_members.setdefault(correlation_group, []).append(name)

    families = {}
    for family, groups in grouped.items():
        reps = {group: median(values) for group, values in groups.items()}
        families[family] = {
            "groups": {g: {"value": round(v, 2), "members": group_members[g]}
                       for g, v in reps.items()},
            "representative": median(list(reps.values())),
            "weight_raw": FAMILY_WEIGHTS[family],
            "weight_effective": 0.0,
        }

    covered_weight = sum(FAMILY_WEIGHTS[f] for f in families)
    if families:
        # Complete coverage uses configured weights.  In a degraded 1/2-family
        # case, missing-family weight is not transferred to a particular
        # survivor; each independent family gets one equal vote instead.
        complete = len(families) == len(FAMILY_WEIGHTS)
        for family, detail in families.items():
            detail["weight_effective"] = (
                FAMILY_WEIGHTS[family] if complete else 1.0 / len(families)
            )
        family_fair_value = sum(d["representative"] * d["weight_effective"]
                                for d in families.values())
    else:
        family_fair_value = None
    for family, detail in families.items():
        family_share = detail["weight_effective"]
        groups_n = max(len(detail["groups"]), 1)
        for group, gd in detail["groups"].items():
            member_share = family_share / groups_n / max(len(gd["members"]), 1)
            for name in gd["members"]:
                entries[name]["weight_effective"] = round(member_share, 6)

    # A validated structural-shift DCF is the primary intrinsic-value answer.
    # Other independent methods explain the range; they do not average the
    # through-cycle model away into a synthetic price no method actually owns.
    dcf_entry = entries.get("dcf_self_built") or {}
    dcf_primary = (dcf_entry.get("status") == "eligible" and
                   dcf_entry.get("projection_mode") == "structural_shift_through_cycle")
    if dcf_primary:
        fair_value = dcf_entry["value"]
        for entry in entries.values():
            entry["weight_effective"] = 0.0
        dcf_entry["weight_effective"] = 1.0
    else:
        fair_value = family_fair_value

    fv = round(fair_value, 2) if fair_value is not None else None
    vs_pct = ((fair_value - current_price) / current_price * 100
              if fair_value is not None else None)
    family_ratios = {f: d["representative"] / current_price for f, d in families.items()}
    score = _valuation_score(vs_pct, family_ratios)
    family_count = len(families)
    confidence = "high" if family_count == 3 else "medium" if family_count == 2 else "low"
    # Family topology gives independent families independent votes; it cannot see
    # that two *different* families may be fed by the same sell-side analysts.
    # Flagging it is the honest answer — the number stands, the size does not.
    eligible_names = sorted(n for n, e in entries.items() if e["status"] == "eligible")
    sell_side_only = bool(eligible_names) and all(n in SELL_SIDE_ANCHORS
                                                  for n in eligible_names)
    return {
        "schema": VALUATION_PACK_SCHEMA,
        "engine": ENGINE_VERSION,
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "current_price": current_price,
        "anchors": entries,
        "families": families,
        "families_present": sorted(families),
        "family_coverage_weight": round(covered_weight, 4),
        "aggregation_mode": ("dcf_primary_anchor_range" if dcf_primary
                             else "complete_fixed_family_weights" if len(families) == 3
                             else "degraded_equal_family_votes" if families else "unavailable"),
        "primary_method": "dcf_self_built" if dcf_primary else "family_aggregation",
        "family_blended_fair_value": (round(family_fair_value, 2)
                                      if family_fair_value is not None else None),
        "weighted_fair_value": fv,
        "vs_current_pct": round(vs_pct, 2) if vs_pct is not None else None,
        "verdict_band": _verdict_band(vs_pct) if vs_pct is not None else None,
        "score": score,
        "confidence": confidence,
        "evidence_independence": {
            "eligible_anchors": eligible_names,
            "sell_side_anchors": [n for n in eligible_names if n in SELL_SIDE_ANCHORS],
            "sell_side_only": sell_side_only,
            "note": ("每一根合格錨都源自賣方分析師預估——兩個 family 的票不是兩份獨立"
                     "證據；估值可用但屬 speculative grade" if sell_side_only else
                     "至少一根合格錨獨立於賣方預估"),
        },
        "structural_shift": structural_shift,
    }


# ── Block 1: fair_value_summary — projection of canonical valuation_pack ────
def fair_value_summary_from_pack(pack: dict) -> dict:
    eligible = {k: v for k, v in pack["anchors"].items() if v["status"] == "eligible"}
    excluded = {k: v["reason"] for k, v in pack["anchors"].items()
                if v["status"] != "eligible"}
    return {
        "anchors": {k: v["value"] for k, v in pack["anchors"].items()},
        "anchors_effective": {
            k: v["value"] if v["status"] == "eligible" else None
            for k, v in pack["anchors"].items()
        },
        "weights_used": {k: v["weight_effective"] for k, v in eligible.items()},
        "weighted_fair_value": pack["weighted_fair_value"],
        "current_price": pack["current_price"],
        "vs_current_pct": pack["vs_current_pct"],
        "verdict_band": pack["verdict_band"],
        "score": pack["score"],
        "confidence": pack["confidence"],
        "anchors_available": len(eligible),
        "families_present": pack["families_present"],
        "family_coverage_weight": pack["family_coverage_weight"],
        "excluded_anchors": excluded,
        "valuation_pack_schema": pack["schema"],
        "primary_method": pack.get("primary_method"),
        "family_blended_fair_value": pack.get("family_blended_fair_value"),
        # Phase 4.6 speculative governor 直接讀這兩欄（不必自己重解 valuation_pack）
        "sell_side_only": (pack.get("evidence_independence") or {}).get("sell_side_only"),
        "pre_profit_anchor_live": (
            (pack["anchors"].get("fwd_earnings_discounted") or {}).get("status") == "eligible"),
        "methodology_note": (
            f"{'DCF primary with anchor range' if pack.get('primary_method') == 'dcf_self_built' else 'canonical family aggregation'}; "
            f"mode={pack.get('aggregation_mode')}; {len(eligible)}/{len(ANCHOR_WEIGHTS)} anchors; "
            f"families={','.join(pack['families_present']) or 'none'}"
        ),
    }


def build_explained_valuation_range(pack: dict, scenarios: dict | None = None) -> dict:
    """DCF-primary interval with explicit no-peer / with-peer scenario points."""
    scenarios = scenarios or {}
    dcf = (pack.get("anchors") or {}).get("dcf_self_built") or {}
    if pack.get("primary_method") != "dcf_self_built" or dcf.get("status") != "eligible":
        return {"available": False, "reason": "no_eligible_structural_dcf_primary"}

    primary = dcf.get("value")
    fundamental = ((pack.get("families") or {}).get("fundamental") or {}).get("representative")
    without_peer = round(fundamental, 2) if _pos(fundamental) else primary
    peer = scenarios.get("peer_pe_range") or {}
    peer_value = _pos(peer.get("value")) if peer.get("eligible") else None
    with_peer = round((without_peer + peer_value) / 2, 2) if peer_value else None
    other_eligible = {
        name: entry.get("value")
        for name, entry in (pack.get("anchors") or {}).items()
        if name != "dcf_self_built" and entry.get("status") == "eligible"
        and _pos(entry.get("value"))
    }
    sensitivity_low = dcf.get("sensitivity_low") or primary
    sensitivity_high = dcf.get("sensitivity_high") or primary
    named_points = {
        "dcf_sensitivity_low": sensitivity_low,
        "dcf_primary": primary,
        "fundamental_without_peer": without_peer,
        "dcf_sensitivity_high": sensitivity_high,
    }
    if with_peer:
        named_points["two_family_with_peer"] = with_peer
    named_points.update({f"anchor:{name}": value for name, value in other_eligible.items()})
    named_points = {name: value for name, value in named_points.items() if _pos(value)}
    range_low_driver = min(named_points, key=named_points.get)
    range_high_driver = max(named_points, key=named_points.get)
    return {
        "available": True,
        "primary_fv": primary,
        "primary_method": "structural_shift_through_cycle_dcf",
        "primary_sensitivity": {
            "low": round(sensitivity_low, 2), "high": round(sensitivity_high, 2),
        },
        "scenario_without_peer": without_peer,
        "scenario_with_peer": with_peer,
        "peer_pe_range_anchor": peer_value,
        "range_low": round(named_points[range_low_driver], 2),
        "range_high": round(named_points[range_high_driver], 2),
        "range_low_driver": range_low_driver,
        "range_high_driver": range_high_driver,
        "peer_scope": peer.get("scope"),
        "peer_count": peer.get("peer_count", 0),
        "peer_symbols": sorted((peer.get("peers") or {}).keys()),
        "other_eligible_anchors": other_eligible,
        "interpretation": (
            f"DCF is the primary FV; low={range_low_driver}; high={range_high_driver}. "
            "Range-only peers explain a scenario and never replace the primary."
        ),
        "limitations": peer.get("limitations") or [],
    }


def compute_fair_value_summary(anchors: dict, current_price: float) -> dict:
    """Backward-compatible pure-function entry; uses the canonical builder."""
    pack = build_valuation_pack(anchors, current_price, strict_metadata=False)
    return fair_value_summary_from_pack(pack)


# ── Block 2: fair_value_range (V3.45.1) ──────────────────────────────────────
def compute_fair_value_range(anchors: dict, current_price: float, fred: dict) -> dict:
    available = {k: _pos(anchors.get(k)) for k in ANCHOR_WEIGHTS}
    available = {k: v for k, v in available.items() if v is not None}
    vals = list(available.values())
    total_w = sum(ANCHOR_WEIGHTS[k] for k in available) or 1.0
    wts = [ANCHOR_WEIGHTS[k] / total_w for k in available]
    n = len(vals)

    if n >= 4:
        range_method = "weighted_percentile"
        p25 = weighted_percentile(vals, wts, 0.25)
        p50 = weighted_percentile(vals, wts, 0.50)
        p75 = weighted_percentile(vals, wts, 0.75)
    elif n >= 2:
        range_method = "minmax_fallback"
        p25, p50, p75 = min(vals), median(vals), max(vals)
    else:
        range_method = None
        p25 = p50 = p75 = None

    min_a, max_a = (min(vals), max(vals)) if n else (None, None)

    if p25 is None:
        range_verdict = None
    elif current_price > max_a:
        range_verdict = "extreme_overvalued"
    elif current_price < min_a:
        range_verdict = "extreme_undervalued"
    elif current_price > p75:
        range_verdict = "overvalued_zone"
    elif current_price < p25:
        range_verdict = "undervalued_zone"
    else:
        range_verdict = "fair_zone"

    if n >= 2:
        wmean = weighted_mean(vals, wts)
        wstd = weighted_std(vals, wts)
        cv = (wstd / wmean) if wmean else None
        grade = None if cv is None else (
            "high" if cv < AGREEMENT_GRADE_HIGH_CV
            else "medium" if cv < AGREEMENT_GRADE_LOW_CV else "low")
    else:
        cv, grade = None, None

    real10 = _num((fred or {}).get("treasury_10y_real"))
    if real10 is not None:
        req_yield = real10 + ERP_EARNINGS_YIELD
        oe_linked = clamp(1.0 / req_yield, *OE_MULT_CLAMP) if req_yield > 0 else None
    else:
        req_yield, oe_linked = None, None

    # max/min spread — plain-language dispersion signal for the UI ("anchors span N×")
    disp_ratio = round(max_a / min_a, 2) if (min_a and min_a > 0 and max_a is not None) else None

    return {
        "range_method": range_method,
        "p25": round(p25, 2) if p25 is not None else None,
        "p50": round(p50, 2) if p50 is not None else None,
        "p75": round(p75, 2) if p75 is not None else None,
        "min_anchor": round(min_a, 2) if min_a is not None else None,
        "max_anchor": round(max_a, 2) if max_a is not None else None,
        "dispersion_ratio": disp_ratio,
        "range_verdict": range_verdict,
        "anchor_dispersion_cv": round(cv, 4) if cv is not None else None,
        "agreement_grade": grade,
        "anchors_used_n": n,
        "owner_earnings_multiple_shadow": {
            "oe_mult_static": 15.0,
            "oe_mult_rate_linked": round(oe_linked, 2) if oe_linked is not None else None,
            "required_yield": round(req_yield, 4) if req_yield is not None else None,
        },
    }


# ── V4.70.0 — anchor outlier trim (P0-3 audit fix) ───────────────────────────
# 審計實證（AUDIT_2026-07-16）：owner_earnings×15 對高成長 archetype 產出如 NVDA
# $31.80（vs 錨中位數 $258）仍以 0.05 權重進 weighted_fair_value，anchors 離散 11.6x
# 照樣加權。修剪規則刻意相對「錨共識」而非相對現價：全體 anchors 一致偏低（真高估）
# 時中位數同步下移，不會誤剪。
TRIM_MIN_ANCHORS = 4          # n<4 不修剪（樣本太少，中位數不穩）
TRIM_FACTOR = 3.0             # 錨值落在 [median/3, median×3] 之外 → 剔除
TRIM_KEEP_FLOOR = 2           # 修剪後剩餘 <2 錨 → 放棄修剪（避免自砍到無法估值）


def trim_anchor_outliers(anchors: dict) -> tuple:
    """Drop anchors wildly inconsistent with the anchor-consensus median.

    Returns (anchors_effective, trimmed_log). anchors_effective 與輸入同 shape，
    被剔除的 anchor 置 None（下游 weight 重分配照舊機制走）。不修改輸入 dict。
    """
    avail = {k: _pos(anchors.get(k)) for k in ANCHOR_WEIGHTS}
    avail = {k: v for k, v in avail.items() if v is not None}
    if len(avail) < TRIM_MIN_ANCHORS:
        return dict(anchors), []
    med = median(list(avail.values()))
    lo, hi = med / TRIM_FACTOR, med * TRIM_FACTOR
    out_keys = [k for k, v in avail.items() if not (lo <= v <= hi)]
    if not out_keys or len(avail) - len(out_keys) < TRIM_KEEP_FLOOR:
        return dict(anchors), []
    eff = dict(anchors)
    trimmed = []
    for k in out_keys:
        trimmed.append({
            "anchor": k, "value": avail[k],
            "reason": f"outside [{lo:.2f}, {hi:.2f}] (median {med:.2f} × 1/{TRIM_FACTOR:g}..{TRIM_FACTOR:g})",
        })
        eff[k] = None
    return eff, trimmed


# ── V4.46.0 — confidence ← anchor dispersion (general, all tickers) ──────────
_CONF_ORDER = {"low": 0, "medium": 1, "high": 2}
# Two-tier cv cap (decoupled from agreement_grade, which is a blunt 0.35 cliff:
# owner_earnings_mult is a structural low outlier across the tech universe, so
# grade=low fires almost everywhere). These give confidence some discrimination:
# extreme dispersion -> low, moderate -> medium, tight -> untouched.
CONF_CAP_CV_LOW = 0.60       # cv >= this -> cap confidence at "low"
CONF_CAP_CV_MEDIUM = 0.35    # cv >= this (and < LOW) -> cap at "medium"


def reconcile_confidence(fvs: dict, frange: dict) -> None:
    """Cap fair_value_summary.confidence by anchor dispersion (cv), in place.

    Pre-V4.46.0 `confidence` was set purely from how many anchors *returned a
    number* (n>=5 -> high), ignoring whether they *agreed*. A blend of anchors
    spanning 50x (e.g. ARM: $3.17-$163.75, cv=1.20) was still labelled "high".
    The dispersion cv already lives in fair_value_range; here we feed it back so
    the point estimate can't claim more confidence than the anchors support.
    Tight anchors (cv < 0.35) are untouched.
    """
    cv = frange.get("anchor_dispersion_cv")
    cur = fvs.get("confidence")
    if cv is None or cur not in _CONF_ORDER:
        return
    if cv >= CONF_CAP_CV_LOW:
        cap, thr = "low", CONF_CAP_CV_LOW
    elif cv >= CONF_CAP_CV_MEDIUM:
        cap, thr = "medium", CONF_CAP_CV_MEDIUM
    else:
        return
    if _CONF_ORDER[cap] < _CONF_ORDER[cur]:
        fvs["confidence_count_based"] = cur
        fvs["confidence"] = cap
        fvs["confidence_capped_by"] = (
            f"anchor_dispersion cv={cv} (>= {thr}) -> {cap}; "
            f"span={frange.get('dispersion_ratio')}x"
        )


# ── Block 3: multi_horizon_price_framework (V5.1) ────────────────────────────
def compute_mhp(inp: dict, fvs: dict) -> dict:
    cp = inp["current_price"]
    vol = inp.get("volatility") or {}
    sigma = _pos(vol.get("sigma_daily"))
    atr = _pos(vol.get("atr_14"))
    confidence = "high"
    if sigma is None and atr is not None:
        sigma = atr / cp          # ATR 反推
        confidence = "medium"
    if sigma is None:
        sigma, confidence = 0.0, "low"

    pattern = inp.get("pattern_taxonomy")
    sm = inp.get("smart_money_label")
    drift = DRIFT_BY_PATTERN.get(pattern, 0.0) + SMART_MONEY_NUDGE.get(sm, 0.0)
    drift = clamp(drift, *DRIFT_CLAMP)

    center_ret = drift * sigma * SQRT5
    half_width = Z80 * sigma * SQRT5
    catalyst_widened = False

    cat = inp.get("immediate_catalyst_5d")
    if isinstance(cat, dict) and _pos(cat.get("expected_move_pct")):
        half_width += cat["expected_move_pct"] / 100.0
        if cat.get("direction_lean") == "NEUTRAL":
            center_ret = 0.0
        confidence = "low"
        catalyst_widened = True

    band_lower = cp * (1 + center_ret - half_width)
    band_point = cp * (1 + center_ret)
    band_upper = cp * (1 + center_ret + half_width)

    kl = inp.get("key_levels") or {}
    support, resistance = _pos(kl.get("support")), _pos(kl.get("resistance"))
    lower_capped = max(band_lower, support) if support is not None else band_lower
    upper_capped = min(band_upper, resistance) if resistance is not None else band_upper
    notes = []
    if support is not None and band_lower < support:
        notes.append(f"下界受 support ${support:g} 撐住（原始 ${band_lower:.2f}）")
    if resistance is not None and band_upper > resistance:
        notes.append(f"上界受 resistance ${resistance:g} 壓制（原始 ${band_upper:.2f}）")
    key_level_note = "；".join(notes) or "帶未觸及 key levels"

    short_term = {
        "band": [round(band_lower, 2), round(band_point, 2), round(band_upper, 2)],
        "band_capped": [round(lower_capped, 2), round(band_point, 2), round(upper_capped, 2)],
        "drift_sigma": round(drift, 2),
        "sigma_daily": round(sigma, 5) if sigma else None,
        "atr_14": atr,
        "confidence": confidence,
        "catalyst_widened": catalyst_widened,
        "key_level_note": key_level_note,
    }

    # mid-term 60d
    mom_pct = _num(vol.get("momentum_20d_pct"))
    anchors = fvs.get("anchors_effective") or fvs["anchors"]
    analyst_pt = _pos(anchors.get("analyst_pt_consensus"))
    forecaster = _pos(anchors.get("forecaster_blend"))
    momentum_target = cp * (1 + (mom_pct / 100) * MOMENTUM_DECAY) if mom_pct is not None else None
    pt_60d = cp + (analyst_pt - cp) * (60 / 365) * PT_PULL_FACTOR if analyst_pt else None
    # V3.48.0 #8a: forecaster_blend 是長期錨，原直接當 60d 成分 = horizon mismatch
    # （等於假設 60 天走完通往長期合理價全程）→ 折算 60/250 交易日
    earnings_revision = cp + (forecaster - cp) * (60 / 250) if forecaster else None
    parts = {"momentum": momentum_target, "pt_60d": pt_60d, "earnings_revision": earnings_revision}
    avail = {k: v for k, v in parts.items() if _pos(v)}
    if avail:
        wsum = sum(MID_WEIGHTS[k] for k in avail)
        mid_target = sum((MID_WEIGHTS[k] / wsum) * avail[k] for k in avail)
        weights_used = {k: round(MID_WEIGHTS[k] / wsum, 4) for k in avail}
    else:
        mid_target, weights_used = None, {}
    reality = []
    if mid_target is not None and resistance is not None and mid_target > resistance:
        reality.append(f"需突破 ${resistance:g} 才成立")
    if mid_target is not None and support is not None and mid_target < support:
        reality.append(f"需跌破 ${support:g} 才成立")
    mid_term = {
        "momentum_target": round(momentum_target, 2) if momentum_target is not None else None,
        "pt_60d": round(pt_60d, 2) if pt_60d is not None else None,
        "earnings_revision": round(earnings_revision, 2) if earnings_revision is not None else None,
        "weights_used": weights_used,
        "mid_target": round(mid_target, 2) if mid_target is not None else None,
        "reality_check_note": "；".join(reality) or "mid_target 在 key levels 區間內",
    }

    # convergence (V3.45.1 #7 fix logic)
    LT = fvs.get("weighted_fair_value")
    mt = mid_term["mid_target"]
    if LT is None:
        signal, note = None, "長期 FV 不可得，convergence 跳過"
    elif lower_capped > LT:
        signal = "wait_for_pullback"
        note = f"5d 帶下界 ${lower_capped:.2f} > 長期FV ${LT:.2f} → 短期超漲、長期偏貴，等回檔"
    elif band_point < LT and mt is not None and mt > cp and cp < LT * 0.9:
        signal = "high_conviction_long_zone"
        note = f"現價 ${cp:.2f} < 0.9×FV ${LT:.2f}、mid ${mt:.2f} 向上、短期點估仍低於FV → 三框一致看多"
    elif mt is not None and mt > cp > LT:
        signal = "momentum_not_value"
        note = f"mid ${mt:.2f} > 現價 ${cp:.2f} > FV ${LT:.2f} → 動能交易非價值持有"
    else:
        signal = "neutral_aligned"
        note = "三框無顯著背離"

    if signal and fvs.get("confidence") == "low":
        note += "（長期FV 信心 low，訊號僅供參考）"

    return {
        "short_term_5d": short_term,
        "mid_term_60d": mid_term,
        "long_term_ref": {
            "weighted_fair_value": fvs.get("weighted_fair_value"),
            "verdict_band": fvs.get("verdict_band"),
            "confidence": fvs.get("confidence"),
        },
        "convergence": {"mhp_signal": signal, "signal_note": note},
        "engine": ENGINE_VERSION,
    }


# ── Block 4: implied_expectations (reverse DCF, V3.45.1) ─────────────────────
def _dcf_pv(fcf0: float, g: float, wacc: float, gt: float) -> float:
    pv = sum(fcf0 * (1 + g) ** t / (1 + wacc) ** t for t in range(1, 6))
    tv = fcf0 * (1 + g) ** 5 * (1 + gt) / (wacc - gt)
    return pv + tv / (1 + wacc) ** 5


def compute_market_implied_revenue(inp: dict) -> dict:
    """EV 不變下，把今天的 EV/S 消化到成熟中樞所需的營收 CAGR。

    這條式子刻意假設「EV 原地不動」——所以答案的意思是「光是要撐住今天的價格，
    營收就得長這麼快」，而不是任何形式的目標價。
    """
    ev_sales = _pos((inp.get("self_ratios") or {}).get("ev_to_sales_ttm"))
    out = {
        "applicable": False, "reason": None,
        "ev_to_sales_ttm": ev_sales, "terminal_ev_to_sales": TERMINAL_EV_SALES,
        "terminal_ev_to_sales_sector_typical": TERMINAL_EV_SALES_SECTOR_TYPICAL,
        "horizon_years": IMPLIED_REVENUE_HORIZON_Y,
        "required_revenue_multiple": None, "implied_revenue_cagr": None,
        "required_revenue_multiple_sector": None, "implied_revenue_cagr_sector": None,
        "analyst_revenue_cagr": _num((inp.get("revenue_path") or {}).get("analyst_revenue_cagr")),
        "analyst_horizon_years": _num((inp.get("revenue_path") or {}).get("horizon_years")),
        "verdict": None, "note": "", "red_team_kill_seed": "",
    }
    if ev_sales is None:
        out["reason"] = "ev_to_sales_ttm_unavailable"
        return out
    if ev_sales <= TERMINAL_EV_SALES:
        out["applicable"] = True
        out["required_revenue_multiple"] = 1.0
        out["implied_revenue_cagr"] = 0.0
        out["note"] = (f"EV/S {ev_sales:.2f}x 已在成熟中樞 {TERMINAL_EV_SALES:g}x 之下"
                       "——現價未內含營收擴張要求")
        return out

    mult = ev_sales / TERMINAL_EV_SALES
    cagr = mult ** (1 / IMPLIED_REVENUE_HORIZON_Y) - 1
    sector_mult = max(ev_sales / TERMINAL_EV_SALES_SECTOR_TYPICAL, 1.0)
    sector_cagr = sector_mult ** (1 / IMPLIED_REVENUE_HORIZON_Y) - 1
    out.update({
        "applicable": True,
        "required_revenue_multiple": round(mult, 2),
        "implied_revenue_cagr": round(cagr, 4),
        "required_revenue_multiple_sector": round(sector_mult, 2),
        "implied_revenue_cagr_sector": round(sector_cagr, 4),
    })
    parts = [f"EV/S {ev_sales:.2f}x → 收斂到 {TERMINAL_EV_SALES:g}x 需營收 ×{mult:.2f}"
             f"（{IMPLIED_REVENUE_HORIZON_Y:g}Y CAGR {cagr * 100:.0f}%，且 EV 原地不動）；"
             f"若倍數只收斂到科技中樞 {TERMINAL_EV_SALES_SECTOR_TYPICAL:g}x 則需 "
             f"{sector_cagr * 100:.0f}%"]
    analyst = out["analyst_revenue_cagr"]
    if analyst is not None:
        parts.append(f"分析師路徑 {analyst * 100:.0f}%")
        ratio = (cagr / analyst) if analyst else None
        if ratio is not None and ratio > 1.2:
            out["verdict"] = "market_above_sell_side"
            parts.append("→ 市場要求的成長高於賣方預估，定價已跑在共識前面")
        elif ratio is not None and ratio < 0.8:
            out["verdict"] = "market_below_sell_side"
            parts.append("→ 市場要求的成長低於賣方預估：若共識成真，現價偏保守")
        else:
            out["verdict"] = "aligned_with_sell_side"
            parts.append("→ 與賣方預估大致一致")
    out["note"] = "；".join(parts)
    out["red_team_kill_seed"] = (
        f"IF 未來 2 季營收年化增速 < {cagr * 100:.0f}% THEN 現價內含的營收路徑破裂")
    return out


def compute_implied_expectations(inp: dict) -> dict:
    cp = inp["current_price"]
    rdcf = inp.get("reverse_dcf") or {}
    fcf_ps = _num(rdcf.get("fcf_base_per_share"))
    fred = inp.get("fred") or {}
    t10 = _num(fred.get("treasury_10y"))
    if t10 is not None:
        wacc, wacc_source = t10 + ERP_WACC, "fred_10y"
    else:
        wacc, wacc_source = WACC_FALLBACK_RF + ERP_WACC, "fallback_fixed"

    out = {
        "implied_5y_fcf_cagr": None,
        "implied_out_of_range": False,
        "wacc_used": round(wacc, 4),
        "wacc_source": wacc_source,
        "fcf_base": fcf_ps,
        "fcf_base_source": "owner_earnings",
        "terminal_growth": TERMINAL_GROWTH,
        "actual_3y_fcf_cagr": _num(rdcf.get("actual_3y_fcf_cagr")),
        "lane_fcf_estimate": _num(rdcf.get("lane_fcf_estimate")),
        "sanity_note": "",
        "red_team_kill_seed": "",
        "market_implied_revenue": compute_market_implied_revenue(inp),
    }
    if fcf_ps is None or fcf_ps <= 0:
        rev = out["market_implied_revenue"]
        out["sanity_note"] = "FCF base ≤ 0 或缺，reverse DCF 不適用" + (
            f"；改用營收路徑：{rev['note']}" if rev.get("applicable") else "")
        out["red_team_kill_seed"] = rev.get("red_team_kill_seed") or ""
        return out
    if wacc <= TERMINAL_GROWTH:
        out["sanity_note"] = f"WACC {wacc:.3f} ≤ terminal growth，模型退化，跳過"
        return out

    # bisection: PV(g) 對 g 單調遞增，解 PV = current_price
    lo, hi = -0.90, 3.00
    if _dcf_pv(fcf_ps, hi, wacc, TERMINAL_GROWTH) < cp:
        raw = hi
    elif _dcf_pv(fcf_ps, lo, wacc, TERMINAL_GROWTH) > cp:
        raw = lo
    else:
        for _ in range(80):
            mid = (lo + hi) / 2
            if _dcf_pv(fcf_ps, mid, wacc, TERMINAL_GROWTH) < cp:
                lo = mid
            else:
                hi = mid
        raw = (lo + hi) / 2

    clamped = clamp(raw, *IMPLIED_CAGR_CLAMP)
    out["implied_5y_fcf_cagr"] = round(clamped, 4)
    out["implied_out_of_range"] = bool(raw < IMPLIED_CAGR_CLAMP[0] or raw > IMPLIED_CAGR_CLAMP[1])

    act, est = out["actual_3y_fcf_cagr"], out["lane_fcf_estimate"]
    cmp_parts = [f"現價 ${cp:g} 隱含 5Y FCF CAGR {clamped * 100:.0f}%"]
    if act is not None:
        cmp_parts.append(f"過去 3 年實際 {act * 100:.0f}%")
    if est is not None:
        cmp_parts.append(f"lane 估 {est * 100:.0f}%")
    verdict = ""
    ref = est if est is not None else act
    if ref is not None:
        ratio = (clamped / ref) if ref else None
        if ratio is not None and ratio > 1.5:
            verdict = " → 隱含預期顯著高於現實，過度樂觀"
        elif ratio is not None and ratio < 0.7:
            verdict = " → 隱含預期低於現實，市場悲觀定價"
    out["sanity_note"] = "；".join(cmp_parts) + verdict
    out["red_team_kill_seed"] = (
        f"IF 未來 2 季 FCF 年化增速 < {clamped * 100 / 2:.0f}%（隱含值一半）THEN 現價估值論點破滅"
    )
    return out


# ── V3.46.0: Valuation archetype shadow（live fair_value_summary 不動）────────
def classify_archetype(ai: dict | None) -> dict:
    """Deterministic archetype classification — 按序首中。缺判定輸入 → 該規則跳過。"""
    if not isinstance(ai, dict):
        return {"archetype": "balanced", "rule_hit": "no_inputs", "missing_inputs": ["archetype_inputs"]}
    sector = ai.get("sector")
    rev_yoy = _num(ai.get("revenue_yoy"))           # decimal, e.g. 0.32
    fcf_margin = _num(ai.get("fcf_margin"))         # decimal
    eps_ttm = _num(ai.get("eps_ttm"))
    sigma_pp = _num(ai.get("margin_sigma_pp"))      # 8Q 淨利率 σ（pp）；可直接給
    m8 = ai.get("margins_8q_net")                   # 或給 8Q 淨利率 list（decimal）
    if sigma_pp is None and isinstance(m8, list):
        vals = [v for v in m8 if isinstance(v, (int, float))]
        if len(vals) >= 4:
            mu = sum(vals) / len(vals)
            sigma_pp = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5 * 100

    missing = [k for k, v in (("sector", sector), ("revenue_yoy", rev_yoy),
                              ("fcf_margin", fcf_margin), ("eps_ttm", eps_ttm),
                              ("margin_sigma_pp", sigma_pp)) if v is None]
    if sector in FINANCIAL_SECTORS:
        hit = ("financial", f"sector={sector}")
    elif (rev_yoy is not None and rev_yoy > HYPERGROWTH_REV_YOY) or \
         (eps_ttm is not None and eps_ttm <= 0):
        hit = ("hypergrowth", f"rev_yoy={rev_yoy} / eps_ttm={eps_ttm}")
    elif sector in CYCLICAL_SECTORS and sigma_pp is not None and sigma_pp > CYCLICAL_MARGIN_SIGMA_PP:
        hit = ("cyclical", f"sector={sector} + margin_sigma={sigma_pp:.1f}pp")
    elif fcf_margin is not None and fcf_margin > MATURE_FCF_MARGIN and \
         rev_yoy is not None and rev_yoy < MATURE_REV_YOY:
        hit = ("mature_cashflow", f"fcf_margin={fcf_margin} + rev_yoy={rev_yoy}")
    else:
        hit = ("balanced", "fallback")
    return {"archetype": hit[0], "rule_hit": hit[1], "missing_inputs": missing}


def compute_new_anchors(inp: dict) -> dict:
    """3 新 anchor（per-share fair price）。資料不足 → null（重分配照舊）。

    EV implied 用精確數學：implied_EV = peer_median × self_metric_absolute，
    self_metric 由 self multiple 反推（EBITDA = EV / ev_ebitda；Sales = EV / ev_sales），
    equity = implied_EV − net_debt，price = equity / shares。
    """
    pr = inp.get("peer_ratios") or {}
    sr = inp.get("self_ratios") or {}
    evb = inp.get("ev_block") or {}
    ev, nd, sh = _pos(evb.get("enterprise_value")), _num(evb.get("net_debt")), _pos(evb.get("shares"))

    def _ev_implied(peer_med, self_mult):
        if not all(isinstance(x, (int, float)) for x in (peer_med or 0, self_mult or 0)):
            return None
        if not (peer_med and self_mult and self_mult > 0 and ev and sh):
            return None
        metric = ev / self_mult                       # EBITDA or Sales (absolute)
        equity = peer_med * metric - (nd or 0.0)
        return round(equity / sh, 2) if equity > 0 else None

    ev_ebitda = _ev_implied(_pos(pr.get("peer_ev_ebitda_median")), _pos(sr.get("ev_to_ebitda_ttm")))
    ev_sales = _ev_implied(_pos(pr.get("peer_ev_sales_median")), _pos(sr.get("ev_to_sales_ttm")))

    # pb_roe_justified: justified P/B = (ROE − g)/(r − g)，r = 10Y + beta×ERP
    roe, bvps = _num(sr.get("roe_ttm")), _pos(sr.get("book_value_per_share_ttm"))
    beta = _num(inp.get("beta"))
    t10 = _num((inp.get("fred") or {}).get("treasury_10y"))
    pb_roe = None
    if roe and bvps and roe > TERMINAL_GROWTH:
        r = (t10 if t10 is not None else WACC_FALLBACK_RF) + (beta if beta is not None else 1.0) * ERP_WACC
        if r > TERMINAL_GROWTH:
            jpb = clamp((roe - TERMINAL_GROWTH) / (r - TERMINAL_GROWTH), 0.2, 15.0)
            pb_roe = round(jpb * bvps, 2)

    return {"peer_ev_ebitda_implied": ev_ebitda,
            "peer_ev_sales_implied": ev_sales,
            "pb_roe_justified": pb_roe}


def compute_archetype_shadow(inp: dict, fvs: dict) -> dict:
    """Shadow blend：9-anchor 池 × archetype 權重。live fair_value_summary 不動。"""
    cp = inp["current_price"]
    cls = classify_archetype(inp.get("archetype_inputs"))
    new_anchors = compute_new_anchors(inp)
    anchors_full = {**(fvs.get("anchors") or {}), **new_anchors}
    weights = ARCHETYPE_WEIGHTS[cls["archetype"]]
    available = {k: _pos(anchors_full.get(k)) for k, w in weights.items() if w > 0}
    available = {k: v for k, v in available.items() if v is not None}
    if available:
        tw = sum(weights[k] for k in available)
        wn = {k: weights[k] / tw for k in available}
        wfv_s = sum(wn[k] * available[k] for k in available)
        vs_s = (wfv_s - cp) / cp * 100
        verdict_s = _verdict_band(vs_s)
        flip = verdict_s != fvs.get("verdict_band")
        weights_used = {k: round(v, 4) for k, v in wn.items()}
    else:
        wfv_s = vs_s = verdict_s = None
        flip, weights_used = None, {}
    return {
        "archetype": cls["archetype"],
        "rule_hit": cls["rule_hit"],
        "missing_inputs": cls["missing_inputs"],
        "new_anchors": new_anchors,
        "anchors_used_n": len(available),
        "weights_used": weights_used,
        "weighted_fair_value_shadow": round(wfv_s, 2) if wfv_s is not None else None,
        "vs_current_pct_shadow": round(vs_s, 2) if vs_s is not None else None,
        "verdict_band_shadow": verdict_s,
        "flip_vs_live": flip,
        "note": "shadow-only — live fair_value_summary 權重/verdict 不受影響（#3b 切換待 ≥20 session 翻轉率報告）",
    }


# ── V4.131.13: extreme-DCF forward validation ───────────────────────────────
FORWARD_VALIDATION_SCHEMA = "forward_validation.v1"
EXTREME_DCF_GAP_PCT = -30.0
FORWARD_PRICE_SUPPORT_PCT = -10.0
REVENUE_CAGR_TOLERANCE = 0.05
FORWARD_MIN_EVALUATED_CHECKS = 2


def compute_forward_validation(pack: dict, implied: dict, shadow: dict) -> dict:
    """Test whether an extreme DCF gap survives independent forward evidence.

    The DCF value and verdict remain untouched.  This block only adjusts the
    valuation *score*: at least one credible forward support softens an extreme
    negative score to -1; a hard T5 downgrade is reserved for a fully evaluated
    FAIL.  Sparse evidence returns NO_DATA and never manufactures a hard veto.
    """
    cp = _pos(pack.get("current_price"))
    raw_score = _num(pack.get("score"))
    dcf = (pack.get("anchors") or {}).get("dcf_self_built") or {}
    dcf_value = _pos(dcf.get("value"))
    dcf_gap = ((dcf_value - cp) / cp * 100
               if cp is not None and dcf_value is not None else None)
    applies = bool(dcf.get("status") == "eligible" and dcf_gap is not None
                   and dcf_gap <= EXTREME_DCF_GAP_PCT)

    checks = []

    def add_check(name, available, supports, actual, threshold, detail=None):
        checks.append({
            "name": name,
            "available": bool(available),
            "supports_current_price": bool(supports) if available else None,
            "actual": actual,
            "threshold": threshold,
            "detail": detail,
        })

    if applies:
        shadow_gap = _num(shadow.get("vs_current_pct_shadow"))
        shadow_n = _num(shadow.get("anchors_used_n"))
        shadow_available = shadow_gap is not None and shadow_n is not None and shadow_n >= 2
        add_check(
            "archetype_shadow",
            shadow_available,
            shadow_available and shadow_gap >= FORWARD_PRICE_SUPPORT_PCT,
            shadow_gap,
            f">={FORWARD_PRICE_SUPPORT_PCT:.0f}% vs current",
            {"anchors_used_n": int(shadow_n) if shadow_n is not None else None},
        )

        fwd = (pack.get("anchors") or {}).get("fwd_earnings_discounted") or {}
        fwd_value = _pos(fwd.get("value"))
        fwd_cal = fwd.get("calibration") or {}
        fwd_horizon = _num(fwd_cal.get("horizon_years"))
        analyst_count = _num(fwd_cal.get("analyst_count"))
        fwd_reason = str(fwd.get("reason") or "")
        scope_only = (fwd.get("status") == "eligible"
                      or fwd_reason.startswith("cashflow_intrinsic_anchors_live:")
                      or fwd_reason == "profitable_issuer_shadow_only")
        fwd_available = bool(
            fwd_value is not None and cp is not None and scope_only
            and analyst_count is not None and analyst_count >= FWD_MIN_ANALYSTS
            and fwd_horizon is not None and fwd_horizon <= FWD_MAX_HORIZON_YEARS
        )
        fwd_gap = ((fwd_value - cp) / cp * 100
                   if fwd_value is not None and cp is not None else None)
        add_check(
            "forward_earnings",
            fwd_available,
            fwd_available and fwd_gap >= FORWARD_PRICE_SUPPORT_PCT,
            round(fwd_gap, 2) if fwd_gap is not None else None,
            f">={FORWARD_PRICE_SUPPORT_PCT:.0f}% vs current",
            {"analyst_count": int(analyst_count) if analyst_count is not None else None,
             "horizon_years": fwd_horizon},
        )

        rev = (implied.get("market_implied_revenue") or {})
        implied_cagr = _num(rev.get("implied_revenue_cagr"))
        analyst_cagr = _num(rev.get("analyst_revenue_cagr"))
        analyst_horizon = _num(rev.get("analyst_horizon_years"))
        revenue_available = bool(
            rev.get("applicable") is True and implied_cagr is not None
            and analyst_cagr is not None and analyst_horizon is not None
            and analyst_horizon > 0
        )
        add_check(
            "revenue_path",
            revenue_available,
            revenue_available and implied_cagr <= analyst_cagr + REVENUE_CAGR_TOLERANCE,
            implied_cagr,
            f"<= analyst CAGR + {REVENUE_CAGR_TOLERANCE:.2f}",
            {"analyst_revenue_cagr": analyst_cagr,
             "analyst_horizon_years": analyst_horizon},
        )

    evaluated = [c for c in checks if c["available"]]
    supported = [c for c in evaluated if c["supports_current_price"]]
    failed = [c for c in evaluated if not c["supports_current_price"]]
    quality_flags = []
    rev_check = next((c for c in evaluated if c["name"] == "revenue_path"), None)
    if rev_check and _num((rev_check.get("detail") or {}).get("analyst_horizon_years")) < 2:
        quality_flags.append("analyst_revenue_horizon_under_2y")
    if applies and implied.get("implied_out_of_range") is True:
        quality_flags.append("reverse_dcf_growth_out_of_range")

    if not applies:
        status, reason = "NOT_APPLICABLE", "eligible DCF gap is not extreme"
    elif len(evaluated) < FORWARD_MIN_EVALUATED_CHECKS:
        status, reason = "NO_DATA", "fewer than two forward checks are evaluable"
    elif not supported:
        status, reason = "FAIL", "all evaluable forward checks reject current price"
    elif not failed and not quality_flags:
        status, reason = "PASS", "all evaluable forward checks support current price"
    else:
        status, reason = "STRETCHED", "at least one credible forward check supports current price"

    effective_score = raw_score
    if status in ("PASS", "STRETCHED") and raw_score is not None and raw_score <= -2:
        effective_score = -1.0
    return {
        "schema": FORWARD_VALIDATION_SCHEMA,
        "status": status,
        "applies": applies,
        "reason": reason,
        "dcf_value": dcf_value,
        "dcf_gap_pct": round(dcf_gap, 2) if dcf_gap is not None else None,
        "extreme_dcf_threshold_pct": EXTREME_DCF_GAP_PCT,
        "checks": checks,
        "evaluated_count": len(evaluated),
        "support_count": len(supported),
        "supported_checks": [c["name"] for c in supported],
        "failed_checks": [c["name"] for c in failed],
        "quality_flags": quality_flags,
        "valuation_score_before": raw_score,
        "valuation_score_effective": effective_score,
        "score_adjustment": ("soften_to_-1" if effective_score != raw_score else "none"),
        "t5_hard_downgrade_eligible": bool(status == "FAIL" and raw_score is not None
                                            and raw_score <= -3),
    }


# ── Volatility fetch (FMP OHLCV → sigma/atr/momentum；LLM 抄寫風險消除) ───────
def fetch_volatility(ticker: str) -> dict:
    from scripts._shared import fmp_pool
    rows = fmp_pool.get(
        "historical-price-eod/full",
        {"symbol": ticker},
        stable=True, retries=2, timeout=20, hard_fail=False,
    )
    if not isinstance(rows, list) or len(rows) < 25:
        return {}
    rows = sorted(rows, key=lambda r: r.get("date", ""))[-60:]
    closes = [_num(r.get("close")) for r in rows]
    highs = [_num(r.get("high")) for r in rows]
    lows = [_num(r.get("low")) for r in rows]
    if any(c is None for c in closes[-21:]):
        return {}
    rets = [closes[i] / closes[i - 1] - 1 for i in range(len(closes) - 20, len(closes))
            if closes[i - 1]]
    m = sum(rets) / len(rets)
    sigma = math.sqrt(sum((r - m) ** 2 for r in rets) / len(rets))
    trs = []
    for i in range(len(rows) - 14, len(rows)):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        if None in (h, l, pc):
            continue
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = sum(trs) / len(trs) if trs else None
    mom = (closes[-1] / closes[-21] - 1) * 100 if closes[-21] else None
    return {
        "sigma_daily": round(sigma, 5),
        "atr_14": round(atr, 4) if atr is not None else None,
        "momentum_20d_pct": round(mom, 2) if mom is not None else None,
        "source": "fmp_historical_price_eod",
    }


# ── V3.48.0: self-assemble — quant inputs 由 engine 直接讀 cache/bundle，0 LLM 抄寫 ──
def _latest_earnings_cache(ticker: str) -> dict | None:
    import glob as _glob
    files = sorted(_glob.glob(os.path.join(
        BASE_DIR, "skills", "earnings-analyst", "cache", f"{ticker.upper()}_*.json")))
    if not files:
        return None
    try:
        with open(files[-1], encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            payload["_cache_path"] = files[-1]
        return payload
    except Exception:
        return None


def _block_manual_anchor_overrides(inp: dict) -> list[str]:
    """Remove input-file values/meta for engine-owned live anchors.

    Qualitative lane inputs may still come from an LLM, but live valuation anchors
    are authoritative only when reassembled from deterministic cache/API sources.
    """
    anchors = inp.setdefault("anchors", {})
    anchor_meta = inp.setdefault("anchor_meta", {})
    blocked = []
    for name in ANCHOR_WEIGHTS:
        supplied = anchors.get(name) is not None or bool(anchor_meta.get(name))
        if supplied:
            blocked.append(name)
        anchors[name] = None
        anchor_meta[name] = {}
    inp["blocked_anchor_overrides"] = blocked
    return blocked


def _supersede_vendor_dcf(anchor_meta: dict, dcf_payload: dict) -> list[str]:
    """Demote opaque vendor DCFs when the auditable shift model is live.

    Values and lineage remain in the pack for audit.  They simply stop casting
    duplicate cash-flow votes after a structurally normalized self-built DCF
    passes its own eligibility gate.
    """
    model = dcf_payload.get("model_eligibility") or {}
    mode = ((dcf_payload.get("dcf") or {}).get("projection_mode") or
            dcf_payload.get("projection_mode"))
    if model.get("eligible") is not True or mode != "structural_shift_through_cycle":
        return []
    superseded = []
    for name in ("dcf_unlevered", "dcf_levered"):
        meta = anchor_meta.setdefault(name, {})
        meta["eligible"] = False
        meta["reason"] = "superseded_by_auditable_through_cycle_dcf"
        meta["superseded_by"] = "dcf_self_built"
        superseded.append(name)
    return superseded


def assemble_inputs(ticker: str, inp: dict, *, authoritative_anchors: bool = False) -> list:
    """Fill missing fields from deterministic sources.

    With ``authoritative_anchors=True`` (the CLI ``--self-assemble`` path), all
    engine-owned anchor values and metadata from the input file are discarded
    before assembly so an LLM cannot inject a live valuation number.
    Returns list of assembled field paths（audit 用）。

    來源：earnings-analyst cache（DCF/PT/EV/archetype 原料）、FMP quote（price/epsTTM）、
    phase1_factpack peer bundle（peer medians + self ratios + beta）、fmp_supplementary
    （owner earnings per share）、valuation-modeler payloads、forecaster cache，並為每個
    anchor 寫入 provenance/as_of/eligibility。nominal 10Y 直接重用 valuation-modeler
    的 FRED cache adapter。
    """
    import glob as _glob
    filled = []

    if authoritative_anchors:
        blocked = _block_manual_anchor_overrides(inp)
        filled.extend(f"blocked_anchor_override.{name}" for name in blocked)

    def _fill(path: str, value):
        if value is None:
            return
        parts = path.split(".")
        d = inp
        for p in parts[:-1]:
            d = d.setdefault(p, {})
        if d.get(parts[-1]) is None:
            d[parts[-1]] = value
            filled.append(path)

    def _meta(anchor: str, **values):
        block = inp.setdefault("anchor_meta", {}).setdefault(anchor, {})
        for key, value in values.items():
            if value is not None and block.get(key) is None:
                block[key] = value

    today = dt.date.today().isoformat()

    ec = _latest_earnings_cache(ticker) or {}
    val = ec.get("valuation") or {}
    _fill("anchors.dcf_unlevered", _pos(val.get("dcf_intrinsic")))
    _fill("anchors.dcf_levered", _pos(val.get("dcf_levered_intrinsic")))
    _fill("anchors.analyst_pt_consensus", _pos(val.get("price_target_consensus")))
    earnings_asof = ec.get("last_earnings_date") or ec.get("as_of_date")
    earnings_lineage = f"earnings_analyst:{ticker.upper()}:{earnings_asof or 'unknown'}"
    for name in ("dcf_unlevered", "dcf_levered"):
        _meta(name, provenance="earnings_analyst_bundle", as_of=earnings_asof,
              correlation_key=earnings_lineage, input_lineage_ids=[earnings_lineage])
    pt_dates = [str(row.get("publishedDate"))[:10] for row in (val.get("pt_news") or [])
                if isinstance(row, dict) and row.get("publishedDate")]
    pt_asof = max(pt_dates) if pt_dates else None
    _meta("analyst_pt_consensus", provenance="earnings_analyst_bundle.pt_news",
          as_of=pt_asof, correlation_key=f"analyst_pt:{ticker.upper()}:{pt_asof or 'unknown'}",
          input_lineage_ids=[f"analyst_pt:{ticker.upper()}:{pt_asof or 'unknown'}"])
    ev = ec.get("enterprise_value") or {}
    _fill("ev_block.enterprise_value", _pos(ev.get("enterpriseValue")))
    _fill("ev_block.shares", _pos(ev.get("numberOfShares")))
    if _num(ev.get("addTotalDebt")) is not None and _num(ev.get("minusCashAndCashEquivalents")) is not None:
        _fill("ev_block.net_debt", ev["addTotalDebt"] - ev["minusCashAndCashEquivalents"])
    der = ec.get("derived") or {}
    _fill("archetype_inputs.sector", (ec.get("snapshot") or {}).get("sector"))
    _fill("archetype_inputs.revenue_yoy", _num((der.get("yoy_growth") or {}).get("revenue_yoy")))
    _fill("archetype_inputs.fcf_margin", _num((der.get("cash_flow_quality") or {}).get("fcf_margin")))
    m8 = der.get("margins_8q")
    if isinstance(m8, list):
        nets = [r.get("net") for r in m8 if isinstance(r, dict) and isinstance(r.get("net"), (int, float))]
        if len(nets) >= 4:
            _fill("archetype_inputs.margins_8q_net", nets)

    # quote: current_price（stable quote 無 eps 欄 — eps 由 ratios-ttm P/E 反推，見下）
    try:
        from scripts._shared import fmp_pool
        q = fmp_pool.get("quote", {"symbol": ticker}, stable=True, retries=1, timeout=15, hard_fail=False)
        row = q[0] if isinstance(q, list) and q else (q if isinstance(q, dict) else {})
        _fill("current_price", _pos(row.get("price")))
    except Exception:
        pass
    eps_ttm = None

    # peer bundle: peer_pe_median × epsTTM、peer ratio medians、self ratios、beta
    try:
        sys.path.insert(0, os.path.join(BASE_DIR, "investment", "scripts"))
        from phase1_factpack import load_peer_bundle
        pb = load_peer_bundle(ticker) or {}
        if pb.get("status") == "ok":
            sr = pb.get("self_ratios_ttm") or {}
            # eps_ttm = price / pe_ttm 反推（stable quote 無 eps）。pe ≤ 0 / null（虧損股）→
            # eps_ttm 保持 None：hypergrowth 規則退化為只看 rev_yoy（限制，文件已註）
            pe_self = _num(sr.get("pe_ttm"))
            cp_now = _pos(inp.get("current_price"))
            if pe_self and pe_self > 0 and cp_now:
                eps_ttm = round(cp_now / pe_self, 4)
                _fill("archetype_inputs.eps_ttm", eps_ttm)
            pe_med = _pos(pb.get("peer_pe_median"))
            if pe_med and eps_ttm and eps_ttm > 0:
                _fill("anchors.peer_pe_implied", round(pe_med * eps_ttm, 2))
                peer_ids = sorted(pb.get("peers") or [])
                peer_key = f"peers:{_stable_hash(peer_ids)}:{today}"
                _meta("peer_pe_implied", provenance=pb.get("peer_selector") or "peer_bundle",
                      as_of=today, peer_count=len(peer_ids), correlation_key=peer_key,
                      input_lineage_ids=peer_ids)
            _fill("peer_ratios.peer_ev_ebitda_median", _pos(pb.get("peer_ev_ebitda_median")))
            _fill("peer_ratios.peer_ev_sales_median", _pos(pb.get("peer_ev_sales_median")))
            _fill("peer_ratios.peer_pb_median", _pos(pb.get("peer_pb_median")))
            for k in ("ev_to_ebitda_ttm", "ev_to_sales_ttm", "roe_ttm", "book_value_per_share_ttm"):
                _fill(f"self_ratios.{k}", _num(sr.get(k)))
        pb_range = pb.get("range_peer_scenario") or {}
        if pb_range.get("eligible") and _pos(pb_range.get("value")):
            inp.setdefault("valuation_scenarios", {})["peer_pe_range"] = pb_range
            filled.append("valuation_scenarios.peer_pe_range")
        from skills._shared.company_context import get_profile
        prof = get_profile(ticker) or {}
        _fill("beta", _num(prof.get("beta")))
    except Exception:
        pass

    # valuation-modeler payloads are first-class deterministic anchor inputs.
    vm_cache = os.path.join(BASE_DIR, "skills", "valuation-modeler", "cache")
    dcf_path = os.path.join(vm_cache, f"{ticker.upper()}_dcf_payload.json")
    if os.path.exists(dcf_path):
        try:
            with open(dcf_path, encoding="utf-8") as f:
                dcf_payload = json.load(f)
            _fill("anchors.dcf_self_built", _pos(dcf_payload.get("fair_value_per_share")))
            model = dcf_payload.get("model_eligibility") or {}
            _meta("dcf_self_built", provenance="valuation_modeler.dcf",
                  as_of=dcf_payload.get("asof"), model_eligibility=model,
                  eligible=model.get("eligible"), reason=model.get("reason"),
                  projection_mode=(dcf_payload.get("dcf") or {}).get("projection_mode"),
                  sensitivity_low=min(
                      (v for row in (dcf_payload.get("sensitivity") or {}).get("grid", [])
                       for v in row if _pos(v)), default=None),
                  sensitivity_high=max(
                      (v for row in (dcf_payload.get("sensitivity") or {}).get("grid", [])
                       for v in row if _pos(v)), default=None),
                  correlation_key=f"dcf_self:{ticker.upper()}:{dcf_payload.get('asof')}",
                  input_lineage_ids=[os.path.relpath(dcf_path, BASE_DIR)])
            superseded = _supersede_vendor_dcf(inp.setdefault("anchor_meta", {}), dcf_payload)
            filled.extend(f"superseded_anchor.{name}" for name in superseded)
        except Exception:
            pass
    comps_path = os.path.join(vm_cache, f"{ticker.upper()}_comps_payload.json")
    if os.path.exists(comps_path):
        try:
            with open(comps_path, encoding="utf-8") as f:
                comps_payload = json.load(f)
            universe = comps_payload.get("universe") or {}
            model = comps_payload.get("model_eligibility") or {}
            _fill("anchors.comps_implied", _pos(comps_payload.get("comps_implied_value")))
            peer_ids = sorted((universe.get("peers") or {}).keys())
            _meta("comps_implied", provenance="valuation_modeler.comps",
                  as_of=comps_payload.get("asof"), model_eligibility=model,
                  eligible=model.get("eligible"), reason=model.get("reason"),
                  peer_count=universe.get("peer_count_used"),
                  correlation_key=f"peers:{_stable_hash(peer_ids)}:{comps_payload.get('asof')}",
                  input_lineage_ids=[os.path.relpath(comps_path, BASE_DIR), *peer_ids])
            range_scenario = comps_payload.get("peer_pe_range_scenario") or {}
            if range_scenario.get("eligible") and _pos(range_scenario.get("value")):
                inp.setdefault("valuation_scenarios", {})["peer_pe_range"] = range_scenario
                filled.append("valuation_scenarios.peer_pe_range")
            # Subject-side ratios survive a failed peer search (they need no peers).
            # phase1_factpack only emits them when the peer bundle is "ok", which is
            # exactly the case that fails for 沒有可比同業的題材股 — so backfill here.
            comps_self = universe.get("self") or {}
            _fill("self_ratios.ev_to_sales_ttm", _pos(comps_self.get("ev_sales")))
            _fill("self_ratios.ev_to_ebitda_ttm", _pos(comps_self.get("ev_ebitda")))
            _fill("ev_block.enterprise_value", _pos(comps_self.get("enterprise_value")))
            _fill("ev_block.net_debt", _num(comps_self.get("net_debt")))
            _fill("ev_block.shares", _pos(comps_self.get("shares")))
        except Exception:
            pass

    # owner earnings per share → ×15 anchor + reverse DCF fcf base
    try:
        from skills._shared.fmp_supplementary import get_supplementary_bundle
        supp = get_supplementary_bundle(ticker) or {}
        oeps = _num((supp.get("owner_earnings") or {}).get("ownersEarningsPerShare"))
        if oeps and oeps > 0:
            _fill("anchors.owner_earnings_mult", round(oeps * 15, 2))
            _fill("reverse_dcf.fcf_base_per_share", oeps)
            owner_asof = supp.get("as_of") or supp.get("generated_at") or today
            _meta("owner_earnings_mult", provenance="fmp_supplementary.owner_earnings",
                  as_of=str(owner_asof)[:10],
                  correlation_key=f"owner_earnings:{ticker.upper()}:{str(owner_asof)[:10]}",
                  input_lineage_ids=[f"owner_earnings:{ticker.upper()}:{str(owner_asof)[:10]}"])
    except Exception:
        pass

    # forecaster cache（不 subprocess 跑 — 只讀 cache；缺/stale → null）
    fc_path = os.path.join(BASE_DIR, "skills", "earnings-valuation-forecaster", "cache",
                           f"{ticker.upper()}.json")
    if os.path.exists(fc_path):
        try:
            with open(fc_path, encoding="utf-8") as f:
                fc = json.load(f)
            _fill("anchors.forecaster_blend", _pos(fc.get("expected_value")))
            live = fc.get("live_eligibility") or {}
            methods = (fc.get("forward_eps") or {}).get("methods") or {}
            usable_methods = sum(
                1 for key in ("cagr", "consensus", "trend")
                if _pos(methods.get(key)) is not None
            )
            transition = (fc.get("transition_case") or {}).get("transition_case") is True
            _meta("forecaster_blend", provenance="earnings_valuation_forecaster",
                  as_of=str(fc.get("generated_at") or "")[:10] or None,
                  confidence=(fc.get("forward_eps") or {}).get("confidence"),
                  usable_methods=live.get("usable_methods") if live else usable_methods,
                  transition_case=transition,
                  eligible=live.get("eligible") if live else None,
                  reason=",".join(live.get("reasons") or []) or None,
                  correlation_key=f"forecaster:{ticker.upper()}:{str(fc.get('generated_at') or '')[:10]}",
                  input_lineage_ids=[os.path.relpath(fc_path, BASE_DIR)])
        except Exception:
            pass

    # phase0 snapshot: real rate
    p0 = sorted(_glob.glob(os.path.join(BASE_DIR, "investment", "invest_logs", "*phase0*.json")))
    if p0:
        try:
            with open(p0[-1], encoding="utf-8") as f:
                rr = _num((json.load(f).get("fred_snapshot") or {}).get("real_rate_preferred"))
            if rr is not None:
                _fill("fred.treasury_10y_real", rr / 100.0)
        except Exception:
            pass

    # Nominal 10Y for reverse DCF: same FRED cache adapter used by dcf.py.
    try:
        vm_scripts = os.path.join(BASE_DIR, "skills", "valuation-modeler", "scripts")
        if vm_scripts not in sys.path:
            sys.path.insert(0, vm_scripts)
        import fmp_client as vm_fmp_client
        rf, rf_source = vm_fmp_client.risk_free_rate()
        if rf_source and str(rf_source).startswith("fred"):
            _fill("fred.treasury_10y", _num(rf))
            _fill("fred.treasury_10y_source", rf_source)
    except Exception:
        pass

    # ── anchor 9 + 營收反解（都吃同一份 analyst estimates cache）────────────────
    # 必須排在最後：折現率要 beta（peer bundle 段填）與 10Y（上一段填），scope gate
    # 要看其餘 anchor 的最終值與 eligibility。
    estimates = []
    try:
        vm_scripts = os.path.join(BASE_DIR, "skills", "valuation-modeler", "scripts")
        if vm_scripts not in sys.path:
            sys.path.insert(0, vm_scripts)
        import fmp_client as vm_fmp_client  # noqa: F811 — 同一模組，上段已載入
        estimates = vm_fmp_client.analyst_estimates(ticker) or []
    except Exception:
        estimates = []
    if estimates:
        fwd = compute_fwd_earnings_anchor(
            estimates, beta=_num(inp.get("beta")),
            treasury_10y=_num((inp.get("fred") or {}).get("treasury_10y")))
        scope_ok, scope_reason = evaluate_fwd_anchor_scope(inp)
        # 值一律填（shadow 池要用），live 資格由 meta.eligible 決定。
        _fill("anchors.fwd_earnings_discounted", fwd["value"])
        lineage = f"analyst_estimates:{ticker.upper()}:{fwd.get('target_fiscal_year') or 'none'}"
        _meta("fwd_earnings_discounted",
              provenance="fmp_analyst_estimates.annual", as_of=today,
              analyst_count=fwd.get("analyst_count"),
              horizon_years=fwd.get("horizon_years"),
              target_fiscal_year=fwd.get("target_fiscal_year"),
              target_eps=fwd.get("target_eps"),
              justified_pe=fwd.get("justified_pe"),
              justified_pe_raw=fwd.get("justified_pe_raw"),
              pe_clamp_binding=fwd.get("pe_clamp_binding"),
              growth_used=fwd.get("growth_used"),
              growth_source=fwd.get("growth_source"),
              discount_rate=fwd.get("discount_rate"),
              discount_clamp_binding=fwd.get("discount_clamp_binding"),
              beta_used=fwd.get("beta_used"),
              beta_source=fwd.get("beta_source"),
              correlation_key=lineage, input_lineage_ids=[lineage])
        if not scope_ok:
            _meta("fwd_earnings_discounted", eligible=False, reason=scope_reason)
        elif fwd.get("reason"):
            _meta("fwd_earnings_discounted", eligible=False, reason=fwd["reason"])
        filled.append("anchors.fwd_earnings_discounted.scope="
                      + ("live" if scope_ok else scope_reason or "shadow"))

        # 營收路徑：拿覆蓋 ≥3 家的最遠年度營收預估對照市場隱含值
        rev_rows = sorted(
            ((d, r) for r, d in ((row, _iso_date((row or {}).get("date")))
                                 for row in estimates if isinstance(row, dict))
             if d is not None and _pos(r.get("revenueAvg"))),
            key=lambda pair: pair[0])
        covered = [(d, r) for d, r in rev_rows
                   if (_num(r.get("numAnalystsRevenue")) or 0) >= FWD_MIN_ANALYSTS]
        if len(covered) >= 2:
            (d0, r0), (d1, r1) = covered[0], covered[-1]
            span = (d1 - d0).days / 365.25
            if span >= 0.5:
                cagr = (r1["revenueAvg"] / r0["revenueAvg"]) ** (1 / span) - 1
                _fill("revenue_path.analyst_revenue_cagr", round(cagr, 4))
                _fill("revenue_path.horizon_years", round(span, 2))
                _fill("revenue_path.source",
                      f"analyst_estimates {d0.isoformat()}→{d1.isoformat()}")

    return filled


# ── V4.88.0: staged execution (Phase 1.5 quant / Phase 2.4 MHP) ──────────────
class EngineInputError(Exception):
    """Unusable input — main() renders it as {"error": ...} with rc=1."""


def read_input(path: str | None, *, allow_empty: bool = False) -> dict:
    """Load the input JSON object. ``allow_empty`` maps blank/absent input to {}."""
    if path:
        try:
            with open(path, encoding="utf-8") as f:
                raw = f.read()
        except OSError as e:
            raise EngineInputError(f"unparseable input: {e}")
    elif allow_empty and sys.stdin.isatty():
        raw = ""
    else:
        raw = sys.stdin.read()
    if allow_empty and not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except Exception as e:
        raise EngineInputError(f"unparseable input: {e}")
    if not isinstance(payload, dict):
        raise EngineInputError("input must be a JSON object")
    return payload


def resolve_effective_input(inp: dict, *, self_assemble: bool = False,
                            no_fetch: bool = False) -> list:
    """Normalize price + volatility (+ optional self-assembly) in place.

    Everything resolved here is engine-owned quant state. Freezing it once is
    what lets the quant stage run at Phase 1.5 and the MHP stage reuse it
    unchanged — a second live fetch at Phase 2.4 would silently move the price
    and sigma out from under an already-published valuation_pack.
    Returns the self-assembled field list（audit 用）。
    """
    assembled = []
    if self_assemble:
        ticker = inp.get("ticker")
        if not ticker:
            raise EngineInputError("--self-assemble requires ticker in input")
        assembled = assemble_inputs(ticker, inp, authoritative_anchors=True)

    cp = _pos(inp.get("current_price"))
    if cp is None:
        raise EngineInputError("current_price required and must be > 0")
    inp["current_price"] = cp

    vol = inp.get("volatility") or {}
    if _pos(vol.get("sigma_daily")) is None and not no_fetch and inp.get("ticker"):
        fetched = fetch_volatility(inp["ticker"])
        merged = dict(fetched)
        merged.update({k: v for k, v in vol.items() if v is not None})
        inp["volatility"] = merged
    return assembled


def build_quant_stage(inp: dict, *, assembled: list | None = None) -> dict:
    """Phase 1.5 half — every block that needs no Phase 2 qualitative input."""
    cp = inp["current_price"]
    anchors_raw = inp.get("anchors") or {}
    fred = inp.get("fred") or {}
    # Median outlier detection remains diagnostic only.  A correlated majority
    # must not be allowed to erase a legitimate dissenting valuation method.
    _, outlier_diagnostics = trim_anchor_outliers(anchors_raw)
    # Stamped here rather than inside `build_valuation_pack`, which has no
    # ticker and therefore cannot look for the artifacts. `_anchor_eligibility`
    # already prefers `meta["reason"]`, so the marking flows through untouched.
    pack = build_valuation_pack(
        anchors_raw, cp,
        anchor_meta=mark_unrun_anchor_scripts(
            inp.get("ticker"), anchors_raw, inp.get("anchor_meta") or {}),
        structural_shift=inp.get("structural_shift") or {},
        strict_metadata=True,
    )
    effective_anchors = {
        name: detail["value"] if detail["status"] == "eligible" else None
        for name, detail in pack["anchors"].items()
    }
    fvs = fair_value_summary_from_pack(pack)
    frange = compute_fair_value_range(effective_anchors, cp, fred)
    reconcile_confidence(fvs, frange)
    pack["confidence"] = fvs["confidence"]
    if outlier_diagnostics:
        pack["outlier_diagnostics"] = outlier_diagnostics
        fvs["outlier_diagnostics"] = outlier_diagnostics
    implied = compute_implied_expectations(inp)
    shadow = compute_archetype_shadow(inp, fvs)
    forward = compute_forward_validation(pack, implied, shadow)
    pack["score_before_forward_validation"] = forward["valuation_score_before"]
    pack["score"] = forward["valuation_score_effective"]
    pack["forward_validation_status"] = forward["status"]
    fvs["score_before_forward_validation"] = forward["valuation_score_before"]
    fvs["score"] = forward["valuation_score_effective"]
    fvs["forward_validation_status"] = forward["status"]
    return {
        "schema": QUANT_STAGE_SCHEMA,
        "stage": "quant",
        "engine": ENGINE_VERSION,
        "ticker": inp.get("ticker"),
        "quant_blocks": {
            "valuation_pack": pack,
            "fair_value_summary": fvs,
            "fair_value_range": frange,
            "implied_expectations": implied,
            "valuation_archetype_shadow": shadow,
            "forward_validation": forward,
            "valuation_explained_range": build_explained_valuation_range(
                pack, inp.get("valuation_scenarios") or {}),
        },
        "effective_input": inp,
        "self_assembled_fields": list(assembled or []),
        "blocked_anchor_overrides": list(inp.get("blocked_anchor_overrides") or []),
    }


def build_full_output(quant: dict, qualitative: dict | None = None) -> dict:
    """Phase 2.4 half — add MHP, carry every quant block through verbatim.

    Single-shot mode is this same composition with ``qualitative is inp``, so
    "staged == single-shot" holds by construction rather than by comparison.
    """
    qual = qualitative or {}
    eff = quant.get("effective_input") or {}
    blocks = quant["quant_blocks"]
    fvs = blocks["fair_value_summary"]
    # compute_mhp only ever reads these six fields; anchors reach it via fvs.
    mhp_input = {"current_price": eff["current_price"], "volatility": eff.get("volatility")}
    for key in MHP_QUALITATIVE_KEYS:
        value = qual.get(key)
        mhp_input[key] = eff.get(key) if value is None else value

    out = {
        "engine": ENGINE_VERSION,
        "ticker": quant.get("ticker"),
        "valuation_pack": blocks["valuation_pack"],
        "fair_value_summary": fvs,
        "fair_value_range": blocks["fair_value_range"],
        "multi_horizon_price_framework": compute_mhp(mhp_input, fvs),
        "implied_expectations": blocks["implied_expectations"],
        "valuation_archetype_shadow": blocks["valuation_archetype_shadow"],
        "forward_validation": blocks["forward_validation"],
        "valuation_explained_range": blocks["valuation_explained_range"],
    }
    if quant.get("self_assembled_fields"):
        # audit：哪些欄位由 engine 自組（非 LLM 提供）
        out["self_assembled_fields"] = quant["self_assembled_fields"]
    if quant.get("blocked_anchor_overrides"):
        out["blocked_anchor_overrides"] = quant["blocked_anchor_overrides"]
    return out


def load_quant_stage(path: str) -> dict:
    """Read + validate a Phase 1.5 artifact. A broken file must fail loudly:
    silently degrading here would recompute quant blocks at Phase 2.4 prices."""
    try:
        with open(path, encoding="utf-8") as f:
            quant = json.load(f)
    except Exception as e:
        raise EngineInputError(f"unreadable --from-quant artifact: {e}")
    if not isinstance(quant, dict) or quant.get("schema") != QUANT_STAGE_SCHEMA:
        raise EngineInputError(f"--from-quant artifact is not {QUANT_STAGE_SCHEMA}")
    blocks = quant.get("quant_blocks")
    missing = ([k for k in QUANT_BLOCK_KEYS if k not in blocks]
               if isinstance(blocks, dict) else list(QUANT_BLOCK_KEYS))
    if missing:
        raise EngineInputError(f"--from-quant artifact missing quant_blocks: {','.join(missing)}")
    eff = quant.get("effective_input")
    if not isinstance(eff, dict) or _pos(eff.get("current_price")) is None:
        raise EngineInputError("--from-quant artifact missing effective_input.current_price")
    return quant


def default_quant_artifact_path(ticker: str | None) -> str | None:
    if not ticker:
        return None
    return os.path.join(BASE_DIR, "investment", "invest_logs",
                        f"{dt.date.today().isoformat()}_{str(ticker).upper()}_pf_quant.json")


def write_quant_artifact(quant: dict, path: str) -> str:
    """Persist the artifact and stamp where it went (file == stdout payload)."""
    # 前綴比對會被同名兄弟目錄騙到（…/ai-investment-committee-old）→ 補 sep 界定
    inside = os.path.abspath(path).startswith(os.path.join(BASE_DIR, ""))
    quant["persisted_to"] = os.path.relpath(path, BASE_DIR) if inside else path
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(quant, f, ensure_ascii=False, indent=2)
    except OSError as e:
        raise EngineInputError(f"cannot persist quant artifact to {path}: {e}")
    return path


def main():
    ap = argparse.ArgumentParser(description="Deterministic price framework engine (V4.88.0)")
    ap.add_argument("--from-file", help="input JSON path (default: stdin)")
    ap.add_argument("--no-fetch", action="store_true",
                    help="skip FMP volatility fetch even if volatility absent")
    ap.add_argument("--self-assemble", action="store_true",
                    help="V3.48.0: quant inputs 自組（earnings cache / peer bundle / supp / "
                         "forecaster cache / phase0）。input file 給的欄位永遠優先；"
                         "qualitative 欄（pattern/key_levels/catalyst）仍須 LLM lane 提供")
    ap.add_argument("--stage", choices=("quant", "mhp"),
                    help="V4.88.0 staged mode：quant = Phase 1.5 六個 quant block（另持久化）；"
                         "mhp = Phase 2.4 只算 MHP，quant block 從 --from-quant verbatim 併回。"
                         "不給 = 單發模式（向後相容）")
    ap.add_argument("--from-quant", help="--stage mhp 用的 Phase 1.5 quant artifact 路徑")
    ap.add_argument("--out", help="--stage quant 的持久化路徑"
                                  "（預設 investment/invest_logs/<DATE>_<TICKER>_pf_quant.json）")
    args = ap.parse_args()

    try:
        if args.from_quant and args.stage != "mhp":
            raise EngineInputError("--from-quant only applies to --stage mhp")
        if args.stage == "mhp":
            if not args.from_quant:
                raise EngineInputError("--stage mhp requires --from-quant")
            # qualitative 缺料不擋：compute_mhp 自己降級（drift=0 / 無 key level cap）
            out = build_full_output(load_quant_stage(args.from_quant),
                                    read_input(args.from_file, allow_empty=True))
        else:
            inp = read_input(args.from_file)
            assembled = resolve_effective_input(
                inp, self_assemble=args.self_assemble, no_fetch=args.no_fetch)
            quant = build_quant_stage(inp, assembled=assembled)
            if args.stage == "quant":
                path = args.out or default_quant_artifact_path(inp.get("ticker"))
                if path:
                    write_quant_artifact(quant, path)
                else:
                    quant["persisted_to"] = None
                out = quant
            else:
                out = build_full_output(quant, inp)
    except EngineInputError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()

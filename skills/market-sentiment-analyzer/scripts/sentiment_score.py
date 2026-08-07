#!/usr/bin/env python3
"""sentiment_score.py — Sentiment lane 的 deterministic score producer（L5，shadow-first）。

protocol §PHASE 2 Sentiment Subagent 的 rubric 搬成 script：

    Sentiment Score = 0.5 × stock_specific + 0.5 × (market_composite/10 − 5)

**市場層是完整規格，個股層不是。** 動工時逐條驗過：
  - 市場層 `(composite/10 − 5)` 在 protocol 與歷史報告裡完全一致（PLTR 2026-08-02 那筆
    報告寫 `0.5 × (-1.5) + 0.5 × (+0.92) = -0.29`，history 存的正是 -0.29，`+0.92`
    回推 composite = 59.2，與 `sentiment.py` 實跑一致）。零爭議。
  - 個股層只有一張「哪個訊號給幾分」的規則表，**從未定義如何聚合、也沒定義 clamp**。
    全庫 grep `stock_specific` 只命中 protocol 那一行公式與報告裡的敘述值。

所以本檔在兩個地方**填規格空白**，兩者都寫成具名常數，改動成本是改一行：
  1. `stock_specific` = 規則表命中項**加總**後 clamp 到 STOCK_CLAMP
  2. 最終分數 clamp 到 SCORE_CLAMP（歷史 69 筆 lane score 全落在 [-3, +3]，
     所以 clamp 確實存在，只是從未寫下來）

**這是 shadow-only producer**：輸出**不進**任何決策數字，只落進 C1 契約的
`lane_contract.lanes.sentiment.shadow_score`（provenance 仍是 `llm`）。翻預設要先累積
N 個 session 過 `shadow_report.py` 的哨兵、再由使用者拍板 —— 同 L4b gate 的紀律。

**已知做不出來的兩條規則**（不憑空補資料源，一律進 `missing_inputs[]`）：
  - `institutional.accumulation_signal` —— FMP_SUPP_BUNDLE 的 `institutional` block
    實測常為空 dict（NVDA 2026-08-03 即是）
  - `SBC > 15% revenue` —— bundle 只有 CEO comp，沒有 SBC 與 revenue

Usage:
  python3 skills/market-sentiment-analyzer/scripts/sentiment_score.py --ticker NVDA
  python3 ... --ticker NVDA --from-sentiment <sentiment.py 輸出.json>   # 不重抓
  python3 ... --ticker NVDA --market-composite 59.2                     # 只給市場層數字
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys

PRODUCER_VERSION = "sentiment_score.py v1.1 (L5 / V4.95.3)"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── 規格空白 #1：規則表如何聚合成 stock_specific ────────────────────────────
# protocol 只給「哪個訊號幾分」，沒說怎麼合。定為加總後 clamp。
# 加總是各規則寫成有號分數時的自然讀法；clamp 讓個股層與市場層值域可比
# （市場層 composite∈[0,100] → (c/10−5)∈[-5,+5]，實務上極少觸底/頂）。
STOCK_CLAMP = (-3.0, 3.0)

# ── 規格空白 #2：最終 clamp ─────────────────────────────────────────────────
# 未寫在 protocol，但 69 筆歷史 lane score 全部落在 [-3, +3] —— LLM 一直在做這件事。
SCORE_CLAMP = (-3.0, 3.0)

# ── 規則表（protocol §PHASE 2 Sentiment Subagent 逐條搬）────────────────────
# insider_stats[].acquired_disposed_ratio：用 quarters[0]（最近一季）。
# protocol 寫「4 季」但沒說取哪季；schema 既有的 `det_inputs.insider_ratio_q`
# 已定義為 `quarters[0]`，沿用同一定義而不是另立一個。
INSIDER_RATIO_LOW, INSIDER_RATIO_HIGH = 0.3, 1.0
MSPR_POS, MSPR_NEG = 30.0, -30.0
SHORT_CROWDED, SHORT_ELEVATED, SHORT_LOW = 20.0, 10.0, 5.0


def _clamp(x: float, lo_hi: tuple) -> float:
    return max(lo_hi[0], min(lo_hi[1], x))


def _num(x):
    """只認真正的**有限**數字（與 `sector_score_calculator._num` 同款守則）。

    NaN/inf 必須擋在唯一入口：NaN 的所有比較都回 False，market_composite 是 NaN
    時不走降級分支，`_clamp` 會因 `min(hi, nan)` 回 hi 而輸出**上界 +3.0 的假極端
    看多**且 `degraded_reason=None`；規則層輸入是 NaN 時既不進 `missing_inputs`
    也不觸發規則，被讀成「查過了、中性」。NaN 來源是真實的（yfinance
    `shortPercentOfFloat` 偶發）。
    """
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return float(x) if math.isfinite(x) else None


def _obj(x) -> dict:
    """非 dict 一律當空 —— bundle 的欄位偶有 null／字串，`.get` 直接炸掉不值得。"""
    return x if isinstance(x, dict) else {}


def _insider_q0(ticker_signals) -> dict:
    """`insider_stats` 的最近一季（quarters[0]）。

    形狀防禦集中在這一處：評分與 `input_hash` 必須看同一格資料，各寫一份 `[0]`
    存取的下場是同一筆畸形輸入在一邊安全略過、另一邊 KeyError（4.95.1 review 抓到）。
    """
    q = _obj(ticker_signals).get("insider_stats")
    return _obj(q[0]) if isinstance(q, list) and q else {}


def stock_specific_score(ticker_signals: dict, supp: dict | None) -> dict:
    """個股層：規則表逐條命中 → 加總 → clamp。

    回傳 `{score, rules_fired[], missing_inputs[]}`。每條命中都留可追溯字串 ——
    shadow 期要靠它回答「det 與 LLM 差在哪一條」，只給總分無法診斷。
    """
    ts = _obj(ticker_signals)
    sp = _obj(supp)
    fired: list[dict] = []
    missing: list[str] = []

    # 1) insider acquired/disposed ratio（最近一季）
    ratio = _num(_insider_q0(ts).get("acquired_disposed_ratio"))
    if ratio is None:
        missing.append("insider_stats[0].acquired_disposed_ratio")
    elif ratio < INSIDER_RATIO_LOW:
        fired.append({"rule": "insider_ratio_low", "points": -1.0,
                      "detail": f"acquired_disposed_ratio {ratio} < {INSIDER_RATIO_LOW}"})
    elif ratio > INSIDER_RATIO_HIGH:
        fired.append({"rule": "insider_ratio_high", "points": 1.0,
                      "detail": f"acquired_disposed_ratio {ratio} > {INSIDER_RATIO_HIGH}"})

    # 2) Finnhub MSPR
    mspr = _num(_obj(ts.get("insider_sentiment")).get("latest_mspr"))
    if mspr is None:
        missing.append("insider_sentiment.latest_mspr")
    elif mspr > MSPR_POS:
        fired.append({"rule": "mspr_positive", "points": 1.0,
                      "detail": f"latest_mspr {mspr} > {MSPR_POS}"})
    elif mspr < MSPR_NEG:
        fired.append({"rule": "mspr_negative", "points": -1.0,
                      "detail": f"latest_mspr {mspr} < {MSPR_NEG}"})

    # 3) short % float —— 唯一一條 ±2 的規則
    short = _num(ts.get("short_pct_float"))
    if short is None:
        missing.append("short_pct_float")
    elif short > SHORT_CROWDED:
        fired.append({"rule": "short_crowded", "points": -2.0,
                      "detail": f"short_pct_float {short}% > {SHORT_CROWDED}%"})
    elif short >= SHORT_ELEVATED:
        fired.append({"rule": "short_elevated", "points": -1.0,
                      "detail": f"short_pct_float {short}% in [{SHORT_ELEVATED}, {SHORT_CROWDED}]%"})
    elif short < SHORT_LOW:
        fired.append({"rule": "short_low", "points": 1.0,
                      "detail": f"short_pct_float {short}% < {SHORT_LOW}%"})

    # 4) 法人 QoQ accumulation —— block 實測常為空；缺就記缺，不猜。
    #    但 `"neutral"` 是 fmp_supplementary 算出來的**已知中性**（同檔 congress 的
    #    三值設計），與「拿不到」語意相反。4.95.1 修：原本 else 一律記 missing，
    #    把已知中性灌進 missing_inputs —— 而翻預設前要問的正是「missing 是否集中在
    #    同幾檔」，這筆會讓該診斷失真。未知字串仍記 missing（不知道就是不知道）。
    acc = _obj(sp.get("institutional")).get("accumulation_signal")
    if acc == "accumulating":
        fired.append({"rule": "institutional_accumulating", "points": 1.0,
                      "detail": "institutional.accumulation_signal=accumulating"})
    elif acc == "distributing":
        fired.append({"rule": "institutional_distributing", "points": -1.0,
                      "detail": "institutional.accumulation_signal=distributing"})
    elif acc != "neutral":
        missing.append("institutional.accumulation_signal")

    # 5) 議員交易淨訊號（同上三值：bullish / bearish / neutral）
    net = _obj(sp.get("congressional_trades")).get("net_signal")
    if net == "bullish":
        fired.append({"rule": "congress_bullish", "points": 0.5,
                      "detail": "congressional_trades.net_signal=bullish"})
    elif net == "bearish":
        fired.append({"rule": "congress_bearish", "points": -0.5,
                      "detail": "congressional_trades.net_signal=bearish"})
    elif net != "neutral":
        missing.append("congressional_trades.net_signal")

    # 6) SBC > 15% revenue —— 資料源不存在（bundle 只有 CEO comp）。
    #    protocol 另一半「CEO comp YoY > 30% → reasoning 註記」本來就不調分，不列。
    missing.append("stock_based_compensation_pct_revenue")

    raw = sum(f["points"] for f in fired)
    return {
        "score":          _clamp(raw, STOCK_CLAMP),
        "raw_sum":        round(raw, 4),
        "clamped":        raw != _clamp(raw, STOCK_CLAMP),
        "rules_fired":    fired,
        "missing_inputs": missing,
    }


def market_layer_score(composite: float | None) -> float | None:
    """市場層：`composite/10 − 5`。完整規格，無爭議。"""
    c = _num(composite)
    return None if c is None else round(c / 10.0 - 5.0, 4)


def _input_hash(payload: dict) -> str:
    """契約 `input_hash` 用 —— 同輸入必得同分數，這個 hash 讓它可稽核。"""
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def build_sentiment_det(ticker: str, sentiment_payload: dict,
                        supp: dict | None = None) -> dict:
    """組 `sentiment_det` block（寫進 trade，由 apply_det_shadow 映進 C1 契約）。"""
    ts = _obj(_obj(sentiment_payload).get("ticker_signals"))
    composite = _obj(sentiment_payload).get("composite_score")
    market = market_layer_score(composite)
    stock = stock_specific_score(ts, supp)

    if market is None:
        score = None
        degraded = "market_composite_unavailable"
    else:
        score = round(_clamp(0.5 * stock["score"] + 0.5 * market, SCORE_CLAMP), 4)
        degraded = None

    return {
        "producer_version": PRODUCER_VERSION,
        "shadow_only":      True,
        "ticker":           ticker.upper(),
        "score":            score,
        "market_layer":     market,
        "market_composite": composite,
        "stock_specific":   stock["score"],
        "stock_detail":     {k: stock[k] for k in ("raw_sum", "clamped", "rules_fired")},
        "missing_inputs":   stock["missing_inputs"],
        "degraded_reason":  degraded,
        # 每一格都走與評分同一套存取（`_insider_q0` / `_obj`）—— 兩邊各寫一份存取
        # 邏輯，畸形輸入就會出現「分數算得出來、hash 炸掉」的不對稱。
        "input_hash":       _input_hash({
            "composite":    composite,
            "insider_q0":   _insider_q0(ts).get("acquired_disposed_ratio"),
            "mspr":         _obj(ts.get("insider_sentiment")).get("latest_mspr"),
            "short":        ts.get("short_pct_float"),
            "institutional": _obj(_obj(supp).get("institutional")).get("accumulation_signal"),
            "congress":     _obj(_obj(supp).get("congressional_trades")).get("net_signal"),
        }),
        "note": ("shadow-only — LLM 照跑 Sentiment lane，本紀錄不改任何決策數字。"
                 "翻預設需使用者拍板（見 protocol §PHASE 2 Sentiment Subagent）"),
    }


def _load_sentiment(ticker: str, from_file: str | None,
                    market_composite: float | None) -> dict:
    if from_file:
        with open(from_file, encoding="utf-8") as f:
            return json.load(f)
    if market_composite is not None:
        # 只給市場層數字時仍要抓個股訊號，否則 stock_specific 全 missing。
        from sentiment import _fetch_ticker_signals  # noqa: E402 — same dir
        return {"composite_score": market_composite,
                "ticker_signals": _fetch_ticker_signals(ticker)}
    out = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "sentiment.py"),
         "--ticker", ticker, "--json-only"],
        capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"[sentiment_score] sentiment.py failed rc={out.returncode}:\n{out.stderr[:400]}")
    return json.loads(out.stdout)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Sentiment lane deterministic score producer (L5, shadow-only)")
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--from-sentiment", help="sentiment.py --json-only 的輸出檔（避免重抓）")
    ap.add_argument("--market-composite", type=float,
                    help="直接給市場層 composite（Phase 0 _market_signals 已有時用）")
    args = ap.parse_args()

    sys.path.insert(0, SCRIPT_DIR)
    payload = _load_sentiment(args.ticker, args.from_sentiment, args.market_composite)

    supp = None
    try:
        from skills._shared.fmp_supplementary import get_supplementary_bundle
        supp = get_supplementary_bundle(args.ticker)
    except Exception as e:
        print(f"[sentiment_score] FMP_SUPP_BUNDLE unavailable: {e}", file=sys.stderr)

    print(json.dumps(build_sentiment_det(args.ticker, payload, supp),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

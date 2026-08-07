#!/usr/bin/env python3
"""test_sentiment_score.py — L5 Sentiment det producer 契約（V4.91.0）。

這支測試守的東西與一般 scoring 測試不同。det producer 的 score 本身**不進決策**
（shadow-only），所以「算錯一分」的即時代價是零；真正的代價在 shadow 期結束後——
翻預設時整條 lane 換成這份公式。所以測試要鎖的是**規格層**：

1. **兩個「填空白」的常數必須可驗證**（`STOCK_CLAMP` / `SCORE_CLAMP`）。protocol 沒寫
   聚合方式與 clamp，是本檔定的；定的東西要有測試釘住，否則下次有人「順手」改成
   平均或加權，shadow 累積的樣本就與翻預設時跑的公式不是同一個。
2. **市場層必須逐位元對得上歷史**。它是唯一有實測錨點的一半：PLTR 2026-08-02 的報告
   寫 `0.5 × (-1.5) + 0.5 × (+0.92) = -0.29`，history 存 -0.29。這條 golden 讓
   「我搬對了公式」不是宣稱而是可重現的事實。
3. **缺輸入不得偽裝成 0 分**。`missing_inputs[]` 與「規則命中但給 0 分」在總分上都是 0，
   但語意相反——一個是不知道，一個是知道且中性。shadow 期靠這個區分診斷分歧來源。

Usage:  python3 skills/market-sentiment-analyzer/scripts/test_sentiment_score.py
        rc=0 → contract holds;  rc=1 → see the failure list
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sentiment_score import (  # noqa: E402
    SCORE_CLAMP,
    STOCK_CLAMP,
    build_sentiment_det,
    market_layer_score,
    stock_specific_score,
)

FAILS: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    if cond:
        print(f"  ok  {label}")
    else:
        FAILS.append(f"{label}{': ' + detail if detail else ''}")


def sig(**kw) -> dict:
    """ticker_signals fixture —— 只給要測的那條，其餘留 None 走 missing。"""
    out = {"insider_stats": None, "insider_sentiment": None, "short_pct_float": None}
    if "ratio" in kw:
        out["insider_stats"] = [{"acquired_disposed_ratio": kw["ratio"]}]
    if "mspr" in kw:
        out["insider_sentiment"] = {"latest_mspr": kw["mspr"]}
    if "short" in kw:
        out["short_pct_float"] = kw["short"]
    return out


def supp(**kw) -> dict:
    out = {}
    if "acc" in kw:
        out["institutional"] = {"accumulation_signal": kw["acc"]}
    if "congress" in kw:
        out["congressional_trades"] = {"net_signal": kw["congress"]}
    return out


def fired_names(res: dict) -> set:
    return {f["rule"] for f in res["rules_fired"]}


# ═══════════════════════════════════════════════════════════════════════════
# 1. 市場層 —— 唯一有歷史錨點的一半
# ═══════════════════════════════════════════════════════════════════════════

def test_market_layer() -> None:
    print("[市場層 — protocol 公式 + 歷史 golden]")
    check(market_layer_score(59.2) == 0.92,
          "PLTR 2026-08-02 golden：composite 59.2 → +0.92（報告與 history 皆為此值）",
          str(market_layer_score(59.2)))
    check(market_layer_score(50) == 0.0, "composite 50 → 0（中性）")
    check(market_layer_score(0) == -5.0 and market_layer_score(100) == 5.0,
          "值域兩端 → [-5, +5]")
    check(market_layer_score(None) is None, "composite 缺 → None（不當成 0）")
    check(market_layer_score("59.2") is None, "字串型 composite → None（不隱式轉型）")


# ═══════════════════════════════════════════════════════════════════════════
# 2. 規則表逐條
# ═══════════════════════════════════════════════════════════════════════════

def test_rules() -> None:
    print("[個股層 — 規則表逐條命中]")
    cases = [
        (sig(ratio=0.2),  {}, "insider_ratio_low",  -1.0, "insider ratio < 0.3"),
        (sig(ratio=1.5),  {}, "insider_ratio_high",  1.0, "insider ratio > 1.0"),
        (sig(mspr=45),    {}, "mspr_positive",       1.0, "MSPR > +30"),
        (sig(mspr=-45),   {}, "mspr_negative",      -1.0, "MSPR < -30"),
        (sig(short=25),   {}, "short_crowded",      -2.0, "short > 20%（唯一 ±2 規則）"),
        (sig(short=15),   {}, "short_elevated",     -1.0, "short 10-20%"),
        (sig(short=2),    {}, "short_low",           1.0, "short < 5%"),
        ({}, supp(acc="accumulating"),  "institutional_accumulating",  1.0, "法人吸籌"),
        ({}, supp(acc="distributing"),  "institutional_distributing", -1.0, "法人出貨"),
        ({}, supp(congress="bullish"),  "congress_bullish",   0.5, "議員淨買"),
        ({}, supp(congress="bearish"),  "congress_bearish",  -0.5, "議員淨賣"),
    ]
    for ts, sp, rule, pts, label in cases:
        r = stock_specific_score(ts, sp)
        hit = [f for f in r["rules_fired"] if f["rule"] == rule]
        check(len(hit) == 1 and hit[0]["points"] == pts,
              f"{label} → {rule} {pts:+}", str(r["rules_fired"]))

    print("[個股層 — 邊界與中性]")
    check(fired_names(stock_specific_score(sig(ratio=0.3), {})) == set(),
          "insider ratio 恰 0.3 不命中（規則是嚴格 <）")
    check(fired_names(stock_specific_score(sig(ratio=1.0), {})) == set(),
          "insider ratio 恰 1.0 不命中（規則是嚴格 >）")
    check("short_elevated" in fired_names(stock_specific_score(sig(short=10.0), {})),
          "short 恰 10% 落在 elevated（區間下界含）")
    check("short_crowded" in fired_names(stock_specific_score(sig(short=20.1), {})),
          "short 20.1% 落在 crowded")
    check(fired_names(stock_specific_score(sig(short=7), {})) == set(),
          "short 5-10% 是規則表的空檔 → 不命中、不給分")
    r = stock_specific_score({}, supp(congress="neutral"))
    check("congressional_trades.net_signal" not in r["missing_inputs"]
          and not [f for f in r["rules_fired"] if f["rule"].startswith("congress")],
          "議員 neutral = 已知且中性（既不命中也不算缺輸入）")

    # 4.95.1 —— 法人 neutral 與議員 neutral 是同一種東西（fmp_supplementary 的三值設計）。
    # 原本法人走 else 一律記 missing，把「算出來是中性」灌進了 missing_inputs；而翻預設
    # 前要問的正是「missing 是否集中在同幾檔」，被灌水就診斷不出來。
    r = stock_specific_score({}, supp(acc="neutral"))
    check("institutional.accumulation_signal" not in r["missing_inputs"]
          and not [f for f in r["rules_fired"] if f["rule"].startswith("institutional")],
          "法人 neutral = 已知且中性（不得記成 missing）", str(r["missing_inputs"]))

    # 未知字串仍是「不知道」—— 兩條規則都要一致：只有列舉內的中性值才算已知
    for sp_kw, key in ((dict(acc="???"), "institutional.accumulation_signal"),
                       (dict(congress="???"), "congressional_trades.net_signal")):
        r = stock_specific_score({}, supp(**sp_kw))
        check(key in r["missing_inputs"], f"未知值 → 仍記 missing：{key}", str(r["missing_inputs"]))


# ═══════════════════════════════════════════════════════════════════════════
# 3. 兩個「填規格空白」的常數
# ═══════════════════════════════════════════════════════════════════════════

def test_clamps() -> None:
    print("[規格空白 — 聚合與 clamp（本檔定的，必須可驗證）]")
    # 全負：-1(insider) -1(mspr) -2(short) -1(法人) -0.5(議員) = -5.5 → clamp -3
    ts = sig(ratio=0.1, mspr=-50, short=30)
    sp = supp(acc="distributing", congress="bearish")
    r = stock_specific_score(ts, sp)
    check(r["raw_sum"] == -5.5, "規則以加總聚合（-5.5 = 五條全負）", str(r["raw_sum"]))
    check(r["score"] == STOCK_CLAMP[0] and r["clamped"] is True,
          f"raw -5.5 → clamp 到 {STOCK_CLAMP[0]}，且 clamped 旗標為真")

    # 全正：+1 +1 +1 +1 +0.5 = +4.5 → clamp +3
    r = stock_specific_score(sig(ratio=2.0, mspr=50, short=1),
                             supp(acc="accumulating", congress="bullish"))
    check(r["raw_sum"] == 4.5 and r["score"] == STOCK_CLAMP[1],
          f"raw +4.5 → clamp 到 {STOCK_CLAMP[1]}")

    # 最終 clamp：stock +3、market +5 → 0.5×3 + 0.5×5 = +4 → clamp +3
    det = build_sentiment_det("T", {"composite_score": 100,
                                    "ticker_signals": sig(ratio=2.0, mspr=50, short=1)},
                              supp(acc="accumulating", congress="bullish"))
    check(det["score"] == SCORE_CLAMP[1],
          f"stock+3 × market+5 → 最終 clamp 到 {SCORE_CLAMP[1]}", str(det["score"]))
    det = build_sentiment_det("T", {"composite_score": 0,
                                    "ticker_signals": sig(ratio=0.1, mspr=-50, short=30)},
                              supp(acc="distributing", congress="bearish"))
    check(det["score"] == SCORE_CLAMP[0], f"反向 → {SCORE_CLAMP[0]}")

    # 融合公式本身
    det = build_sentiment_det("T", {"composite_score": 59.2,
                                    "ticker_signals": sig(ratio=0.1, mspr=-50, short=15)},
                              supp(congress="bearish"))
    # stock = -1 -1 -1 -0.5 = -3.5 → clamp -3；0.5×-3 + 0.5×0.92 = -1.04
    check(det["stock_specific"] == -3.0 and det["score"] == -1.04,
          "融合 = 0.5×stock + 0.5×market（clamp 後才融合）",
          f"{det['stock_specific']} / {det['score']}")


# ═══════════════════════════════════════════════════════════════════════════
# 4. 降級 —— 缺輸入不得偽裝成 0 分
# ═══════════════════════════════════════════════════════════════════════════

def test_degrade() -> None:
    print("[降級 — 不知道 ≠ 知道且中性]")
    r = stock_specific_score({}, {})
    check(r["score"] == 0.0 and r["rules_fired"] == [],
          "全缺 → stock 0 分但零命中")
    for f in ("insider_stats[0].acquired_disposed_ratio", "insider_sentiment.latest_mspr",
              "short_pct_float", "institutional.accumulation_signal",
              "stock_based_compensation_pct_revenue"):
        check(f in r["missing_inputs"], f"缺輸入登記：{f}")

    det = build_sentiment_det("T", {"composite_score": None, "ticker_signals": sig()}, {})
    check(det["score"] is None and det["degraded_reason"] == "market_composite_unavailable",
          "市場層缺 → score=None（不用 0 頂替，0 是有意義的中性值）",
          str(det["score"]))

    # 資料源不存在的兩條規則永遠在 missing 裡，不會靜默消失
    det = build_sentiment_det("T", {"composite_score": 50,
                                    "ticker_signals": sig(ratio=0.5, mspr=0, short=7)}, {})
    check("stock_based_compensation_pct_revenue" in det["missing_inputs"],
          "SBC 規則資料源不存在 → 恆列 missing（不假裝有跑）")

    # 4.95.1 —— 畸形形狀在評分與 input_hash 兩條路徑上必須同樣安全。兩邊各寫一份
    # `[0]` 存取時，同一筆輸入會「分數算得出來、hash 炸掉」，而 hash 是稽核用的。
    for bad in ({"insider_stats": {"acquired_disposed_ratio": 0.2}},   # dict 不是 list
                {"insider_stats": ["oops"]},                            # list of str
                {"insider_stats": []},
                {"insider_stats": "oops"},
                {"insider_sentiment": "oops"}):
        try:
            d = build_sentiment_det("T", {"composite_score": 50, "ticker_signals": bad}, {})
            ok = d["score"] is not None and isinstance(d["input_hash"], str)
        except Exception as e:                                          # noqa: BLE001
            ok = False
            d = {"err": f"{type(e).__name__}: {e}"}
        check(ok, f"畸形 ticker_signals 不炸且 hash 仍產出：{list(bad)[0]}={bad[list(bad)[0]]!r}",
              str(d)[:120])
    # 畸形 supp 同理（bundle 欄位偶爾是 null/字串）
    d = build_sentiment_det("T", {"composite_score": 50, "ticker_signals": sig()},
                            {"institutional": "oops", "congressional_trades": None})
    check(isinstance(d["input_hash"], str) and "institutional.accumulation_signal" in d["missing_inputs"],
          "畸形 supp → 當缺輸入處理，不炸")

    # 4.95.3 —— NaN 不是數字（NaN 的所有比較都回 False）。真實來源：yfinance
    # shortPercentOfFloat 偶發 NaN，float() 原樣放行。
    nan = float("nan")
    # (a) market_composite=NaN：舊版不走降級分支，_clamp 因 min(hi, nan)=hi 回傳
    #     **上界 +3.0 的假極端看多**且 degraded_reason=None —— 最危險的一條
    det = build_sentiment_det("T", {"composite_score": nan, "ticker_signals": sig()}, {})
    check(det["score"] is None and det["degraded_reason"] == "market_composite_unavailable",
          "market_composite=NaN → 降級（不是 +3.0 假極端看多）",
          f"score={det['score']} degraded={det['degraded_reason']}")
    # (b) 規則層輸入 NaN：既不觸發規則也不得靜默 —— 要進 missing_inputs
    r = stock_specific_score(sig(ratio=nan, mspr=nan, short=nan), {})
    check(r["rules_fired"] == [], "規則層 NaN → 零命中（不是誤觸發）")
    for f in ("insider_stats[0].acquired_disposed_ratio",
              "insider_sentiment.latest_mspr", "short_pct_float"):
        check(f in r["missing_inputs"], f"規則層 NaN 登記 missing：{f}")
    # (c) inf 同樣擋（short_pct_float=inf 會命中 short_crowded 假訊號）
    r = stock_specific_score(sig(short=float("inf")), {})
    check(all(x["rule"] != "short_crowded" for x in r["rules_fired"])
          and "short_pct_float" in r["missing_inputs"],
          "inf → 不觸發 short_crowded、進 missing")


# ═══════════════════════════════════════════════════════════════════════════
# 5. shadow 紀律 + input_hash
# ═══════════════════════════════════════════════════════════════════════════

def test_shadow_contract() -> None:
    print("[shadow 紀律 + input_hash]")
    payload = {"composite_score": 59.2, "ticker_signals": sig(ratio=0.5, mspr=10, short=7)}
    a = build_sentiment_det("NVDA", payload, supp(congress="neutral"))
    b = build_sentiment_det("NVDA", payload, supp(congress="neutral"))
    check(a["shadow_only"] is True, "shadow_only 恆為 True（翻預設要改 producer，不是改 entry）")
    check(a["input_hash"] == b["input_hash"], "同輸入 → 同 input_hash")
    c = build_sentiment_det("NVDA", {**payload, "composite_score": 60.0},
                            supp(congress="neutral"))
    check(a["input_hash"] != c["input_hash"], "輸入變 → hash 變")
    check(a["producer_version"].startswith("sentiment_score.py"),
          "producer_version 具名（C1 契約要求 det lane 可歸屬到公式版本）")
    check(a["score"] == round(0.5 * a["stock_specific"] + 0.5 * a["market_layer"], 4),
          "score 可由 stock/market 兩欄重算（稽核用）")


def main() -> int:
    test_market_layer()
    test_rules()
    test_clamps()
    test_degrade()
    test_shadow_contract()

    if FAILS:
        print(f"\n✗ {len(FAILS)} failure(s):")
        for f in FAILS:
            print("  - " + f)
        return 1
    print("\n✓ sentiment det producer contract holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Golden-fixture regression test for intraday.py (the intraday-weakness engine).

Network-free: feeds synthetic 5-min + daily bars straight into the pure
assess()/aggregate() cores. Run after touching intraday.py — must stay rc=0.

    python3 skills/market-sentiment-analyzer/scripts/test_intraday.py
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intraday  # noqa: E402

_FAILS = []


def check(cond, msg):
    if cond:
        print(f"  ✓ {msg}")
    else:
        print(f"  ✗ {msg}")
        _FAILS.append(msg)


def daily_series(specs):
    """specs: list of (low, close, vol). Dates auto-incremented oldest-first."""
    base = date(2026, 1, 1)
    out = []
    for i, (low, close, vol) in enumerate(specs):
        out.append({"date": (base + timedelta(days=i)).isoformat(),
                    "o": close, "h": close + 1, "l": low, "c": close, "v": vol})
    return out


def intraday_series(open_px, path, per_vol=30_000):
    """path: list of close prices (5-min steps). Each bar h/l bracket the close."""
    bars = []
    prev = open_px
    for i, c in enumerate(path):
        hi = max(prev, c) + 0.05
        lo = min(prev, c) - 0.05
        o = open_px if i == 0 else prev
        bars.append({"time": f"2026-06-25 {9 + i // 12:02d}:{(30 + 5 * i) % 60:02d}:00",
                     "o": o, "h": hi, "l": lo, "c": c, "v": per_vol})
        prev = c
    return bars


def test_break_20d_distribution():
    print("\n[A] 破底 20 日 + 量增價跌（偏空）")
    # 40 old sessions low=90 (50d-low anchor), 20 recent low=101 (20d-low anchor)
    specs = [(90, 110, 1_000_000)] * 40 + [(101, 105, 1_200_000)] * 20
    daily = daily_series(specs)
    # Intraday: open 104, slide to 99, pierce 20d-low (100) but stay above 50d-low (90)
    path = [103.5, 102.5, 101.5, 100.5, 99.5, 98.5, 99.0]  # day_low ~98.45
    bars = intraday_series(104.0, path, per_vol=300_000)    # cum≈2.1M vs avg20 1.2M → RVOL>1
    r = intraday.assess("SPY", bars, daily, label="大盤")

    check(r["break_low_level"] == "20d", f"break_low_level == 20d (got {r['break_low_level']})")
    check(r["score"] is not None and r["score"] < -20, f"score < -20 (got {r['score']})")
    check(r["risk_label"] in ("破底警戒", "偏弱"), f"risk_label 偏空 (got {r['risk_label']})")
    types = {f["type"] for f in r["flags"]}
    check("break_low" in types, "has break_low flag")
    check("distribution" in types, f"has distribution flag (types={types})")
    check(r["rvol"] is not None and r["rvol"] > 1.0, f"rvol > 1 (got {r['rvol']})")
    check(r["range_position"] < 0.4, f"range_position near low (got {r['range_position']})")
    return r


def test_stabilizing_reclaim():
    print("\n[B] 破底後止跌收復（假跌破）")
    specs = [(95, 100, 1_000_000)] * 40 + [
        (99, 103, 1_000_000), (98, 102, 1_000_000), (97, 101, 1_000_000),
        (96, 100, 1_000_000), (95, 99, 1_000_000)]  # declining → cdd, 5d-low ~95
    daily = daily_series(specs)
    # Open 98, dip to 94 (pierce 5d-low 95), reclaim and close strong near high at 99
    path = [97, 95.5, 94.0, 96.0, 98.0, 99.0]
    bars = intraday_series(98.0, path, per_vol=200_000)
    r = intraday.assess("QQQ", bars, daily, label="科技")

    check(r["stabilizing"] is True, "stabilizing True")
    check(r["range_position"] > 0.6, f"price reclaimed to upper range (got {r['range_position']})")
    joined = " ".join(f["text_zh"] for f in r["flags"])
    check(("止跌" in joined) or ("收復" in joined), f"flag mentions 止跌/收復 ({joined!r})")
    return r


def test_gap_up_fade():
    print("\n[C] 高開低走")
    specs = [(98, 100, 1_000_000)] * 25
    daily = daily_series(specs)
    # prev_close 100, gap up open 102, fade to 100.3 near the low
    path = [101.8, 101.4, 100.9, 100.5, 100.3]
    bars = intraday_series(102.0, path, per_vol=150_000)
    r = intraday.assess("SPY", bars, daily, label="大盤")

    check(r["open_pattern"] == "gap_up_fade", f"open_pattern gap_up_fade (got {r['open_pattern']})")
    check(any(f["type"] == "gap_up_fade" for f in r["flags"]), "has gap_up_fade flag")
    return r


def test_strong_healthy():
    print("\n[D] 量價齊揚 強勢（偏多）")
    specs = [(95, 96 + i * 0.1, 1_000_000) for i in range(55)]  # steady uptrend
    daily = daily_series(specs)
    last = specs[-1][1]
    # open at last close, rally all day, close near high on volume
    path = [last + 0.3, last + 0.7, last + 1.1, last + 1.6, last + 2.0]
    bars = intraday_series(last, path, per_vol=300_000)
    r = intraday.assess("SPY", bars, daily, label="大盤")

    check(r["score"] is not None and r["score"] > 20, f"score > 20 (got {r['score']})")
    check(r["risk_label"] in ("偏強", "強勢"), f"risk_label 偏多 (got {r['risk_label']})")
    check(r["break_low_level"] is None, "no 破底")
    check(not any(f["type"] == "break_low" for f in r["flags"]), "no break_low flag")
    return r


def test_empty_intraday():
    print("\n[E] 盤中資料缺")
    r = intraday.assess("IWM", [], daily_series([(95, 100, 1_000_000)] * 10), label="小型股")
    check(r["score"] is None, "score None when intraday empty")
    check(r["_health"] == "missing", "_health missing")


def test_aggregate(a_row, d_row):
    print("\n[F] aggregate 跨標的合併")
    a_row = dict(a_row, weight=0.5)
    d_row = dict(d_row, weight=0.3)
    agg = intraday.aggregate([a_row, d_row])
    check(agg["score"] is not None, "aggregate score present")
    check(isinstance(agg["flags"], list) and agg["flags"], "aggregate has merged flags")
    check(all("tickers" in f and f["tickers"] for f in agg["flags"]), "each merged flag lists tickers")
    check(isinstance(agg["headline_zh"], str) and agg["headline_zh"], "headline string non-empty")
    # weighted score must sit between the two inputs
    lo, hi = sorted([a_row["score"], d_row["score"]])
    check(lo <= agg["score"] <= hi, f"weighted score within [{lo},{hi}] (got {agg['score']})")


def test_live_quote_override():
    print("\n[H] 即時 quote 覆蓋（破底偵測秒級化）")
    # 20d-low = 99 (recent), 50d-low = 90 (old)
    specs = [(90, 110, 1_000_000)] * 50 + [(99, 105, 1_000_000)] * 20
    daily = daily_series(specs)
    # 5-min bars stay benign — bar-derived day_low ~100.7, NO break of 20d-low 99
    path = [101.5, 101.2, 101.0, 100.8, 101.0]
    bars = intraday_series(101.6, path, per_vol=200_000)

    r_nolive = intraday.assess("SPY", bars, daily, label="大盤")
    check(r_nolive["break_low_level"] is None, f"無 live 時不破底 (got {r_nolive['break_low_level']})")
    check(r_nolive["data_source"] == "5min", "data_source == 5min when no live")

    # Live quote: real-time session low 98 pierces the 20d-low 99 (bars hadn't caught it)
    live = {"price": 100.8, "day_open": 101.5, "day_high": 101.6, "day_low": 98.0,
            "prev_close": 102.0, "volume": 5_000_000, "timestamp": 1782405001}
    r_live = intraday.assess("SPY", bars, daily, label="大盤", live=live)
    check(r_live["break_low_level"] == "20d", f"live day_low 觸發破底20日 (got {r_live['break_low_level']})")
    check(r_live["data_source"] == "live_quote+5min", "data_source flags live")
    check(r_live["price"] == 100.8, f"price 用 live spot (got {r_live['price']})")
    check(r_live["day_low"] == 98.0, f"day_low 用 live (got {r_live['day_low']})")
    check(r_live["cum_volume"] == 5_000_000, f"cum_volume 用 live 官方量 (got {r_live['cum_volume']})")
    check(r_live["quote_timestamp"] == 1782405001, "quote_timestamp 透出")
    check(any(f["type"] == "break_low" for f in r_live["flags"]), "live 破底旗標生成")


def test_oscillator_helpers():
    print("\n[I] MACD/KDJ helpers + 資料量守門")
    check(intraday.compute_macd([100 + i for i in range(10)]) is None, "MACD None when <35 bars (早盤守門)")
    check(intraday.compute_kdj([1] * 8, [1] * 8, [1] * 8) is None, "KDJ None when <12 bars")
    # KDJ death cross @ overbought
    up = [100 + i * 1.2 for i in range(18)]
    death = up + [up[-1] + 0.5, up[-1] - 6.0]
    kd = intraday.compute_kdj([x + 0.3 for x in death], [x - 0.3 for x in death], death)
    check(kd and kd["cross"] == "death", f"KDJ death cross (got {kd and kd['cross']})")
    check(kd and kd["k_prev"] >= intraday.KDJ_OB, f"death k_prev 超買 (got {kd and kd['k_prev']})")
    # KDJ golden cross @ oversold
    dn = [120 - i * 1.2 for i in range(18)]
    gold = dn + [dn[-1] - 0.5, dn[-1] + 6.0]
    kg = intraday.compute_kdj([x + 0.3 for x in gold], [x - 0.3 for x in gold], gold)
    check(kg and kg["cross"] == "golden", f"KDJ golden cross (got {kg and kg['cross']})")
    check(kg and kg["k_prev"] <= intraday.KDJ_OS, f"golden k_prev 超賣 (got {kg and kg['k_prev']})")
    # MACD full dict on sufficient data
    m = intraday.compute_macd([100 + i * 0.5 for i in range(50)])
    check(m is not None and {"dif", "dea", "hist", "cross"} <= set(m), "MACD 完整 dict on 50 bars")
    return death, gold


def test_momentum_flags(death, gold):
    print("\n[J] 下殺 / 反轉 旗標整合")
    daily = daily_series([(95, 100, 1_000_000)] * 60)
    r_d = intraday.assess("SPY", intraday_series(death[0], death, per_vol=200_000), daily, label="大盤")
    check(any(f["type"] == "momentum_breakdown" for f in r_d["flags"]), "下殺 momentum_breakdown 旗標")
    check(r_d["momentum"]["kdj_5m"] is not None, "kdj_5m 有算")
    check(r_d["momentum"]["macd_1d"] is not None, "macd_1d 有算（日線）")
    r_g = intraday.assess("QQQ", intraday_series(gold[0], gold, per_vol=200_000), daily, label="科技")
    check(any(f["type"] == "momentum_reversal" for f in r_g["flags"]), "反轉 momentum_reversal 旗標")


def test_risk_label_boundaries():
    print("\n[G] risk_label 邊界")
    check(intraday.risk_label(-60)[1] == "破底警戒", "-60 → 破底警戒")
    check(intraday.risk_label(-30)[1] == "偏弱", "-30 → 偏弱")
    check(intraday.risk_label(0)[1] == "中性", "0 → 中性")
    check(intraday.risk_label(40)[1] == "偏強", "40 → 偏強")
    check(intraday.risk_label(70)[1] == "強勢", "70 → 強勢")
    check(intraday.risk_label(None)[1] == "資料缺", "None → 資料缺")


def main():
    a = test_break_20d_distribution()
    test_stabilizing_reclaim()
    test_gap_up_fade()
    d = test_strong_healthy()
    test_empty_intraday()
    test_aggregate(a, d)
    test_live_quote_override()
    death, gold = test_oscillator_helpers()
    test_momentum_flags(death, gold)
    test_risk_label_boundaries()

    print("\n" + "=" * 56)
    if _FAILS:
        print(f"FAILED — {len(_FAILS)} assertion(s):")
        for m in _FAILS:
            print(f"  - {m}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

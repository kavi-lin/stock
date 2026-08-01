#!/usr/bin/env python3
"""
Golden-fixture test for intraday_spikes.py (Alpaca 1-min 急拉/急殺 detector).
Network-free — feeds synthetic 1-min bars into the pure detect_spikes() core.

    python3 skills/market-sentiment-analyzer/scripts/test_intraday_spikes.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intraday_spikes as sp  # noqa: E402

_FAILS = []


def check(cond, msg):
    print(f"  {'✓' if cond else '✗'} {msg}")
    if not cond:
        _FAILS.append(msg)


def bars(closes, vols=None):
    vols = vols or [1000] * len(closes)
    return [{"t": f"2026-06-25T12:{30 + i:02d}:00Z", "o": c, "h": c, "l": c, "c": c, "v": v}
            for i, (c, v) in enumerate(zip(closes, vols))]


def hl_bars(rows):
    """rows = list of (c, h, l) → bars with explicit high/low (for 持續性/突破 tests)."""
    return [{"t": f"2026-06-25T12:{30 + i:02d}:00Z", "o": c, "h": h, "l": l, "c": c, "v": 1000}
            for i, (c, h, l) in enumerate(rows)]


def test_no_spike():
    print("\n[A] 平盤無急拉/急殺")
    check(sp.detect_spikes("AAPL", bars([100] * 8)) is None, "flat → None")


def test_insufficient():
    print("\n[B] 資料不足")
    check(sp.detect_spikes("AAPL", bars([100, 100, 100, 100])) is None, "<5 bars → None")


def test_spike_up():
    print("\n[C] 急拉（1分 +2.5% → high）")
    r = sp.detect_spikes("NVDA", bars([100] * 7 + [102.5]))
    check(r is not None, "detected")
    check(r and r["direction"] == "spike_up", f"direction spike_up (got {r and r['direction']})")
    check(r and r["dir_zh"] == "急拉", "dir_zh 急拉")
    check(r and r["severity"] == "high", f"severity high (got {r and r['severity']})")
    check(r and r["m1"] >= 2.4, f"m1 ~+2.5 (got {r and r['m1']})")


def test_spike_down():
    print("\n[D] 急殺（1分 -1.6% → med）")
    r = sp.detect_spikes("TSLA", bars([100] * 7 + [98.4]))
    check(r and r["direction"] == "spike_down", f"direction spike_down (got {r and r['direction']})")
    check(r and r["dir_zh"] == "急殺", "dir_zh 急殺")
    check(r and r["severity"] == "med", f"severity med (got {r and r['severity']})")


def test_m3_only():
    print("\n[E] 3 分鐘累積觸發（每分 <1%，3 分 >2%）")
    r = sp.detect_spikes("AMD", bars([100, 100, 100, 100.7, 101.4, 102.1]))
    check(r is not None, "detected via m3")
    check(r and r["direction"] == "spike_up", "direction spike_up")
    check(r and abs(r["m3"]) >= 2.0, f"|m3| ≥ 2 (got {r and r['m3']})")
    check(r and abs(r["m1"]) < 1.0, f"|m1| < 1 (qualified by m3, got {r and r['m1']})")


def test_vol_confirm():
    print("\n[F] 量增確認")
    vols = [1000] * 7 + [5000]
    r = sp.detect_spikes("AAPL", bars([100] * 7 + [101.5], vols))
    check(r and r["vol_confirmed"] is True, f"vol_confirmed True (got {r and r.get('vol_confirmed')})")
    check(r and r["vol_mult"] is not None and r["vol_mult"] >= sp.VOL_MULT, f"vol_mult ≥ {sp.VOL_MULT} (got {r and r['vol_mult']})")
    check("✓量" in (r["text_zh"] if r else ""), "text 含量確認 ✓量")


def test_confirmation():
    print("\n[H] MACD/KDJ 確認（長上升序列 + 末根急拉 → confirmed）")
    base = [round(100 + i * 0.3 + ((-1) ** i) * 0.5, 4) for i in range(40)]  # rising zigzag
    tail = [round(base[-1] + 0.6, 4), round(base[-1] + 1.1, 4), round(base[-1] + 1.5, 4)]
    closes = base + tail
    closes.append(round(closes[-1] * 1.012, 4))   # +1.2% spike on the last bar
    r = sp.detect_spikes("NVDA", bars(closes))
    check(r is not None and r["direction"] == "spike_up", "spike_up detected")
    check(r and r["macd"] is not None, "macd computed (≥35 bars)")
    check(r and r["kdj"] is not None, "kdj computed")
    check(r and "MACD" in r["confirmations"], f"MACD confirms uptrend (confs={r and r['confirmations']})")
    check(r and r["confirmed"] is True, f"confirmed ≥2 (got {r and r['confirmed']})")
    check(r and r["severity"] == "high", "confirmed → severity high")


def test_watchlist_loader():
    print("\n[G] watchlist 解析")
    wl = sp._load_watchlist()
    check(isinstance(wl, list) and len(wl) > 0, f"loaded {len(wl)} tickers")
    check("AAPL" in wl, "AAPL in list")
    check(all(not t.startswith("#") and t == t.upper() for t in wl), "no comments / upper-cased")


def _v_shape_bars():
    """Long decline then sharp recovery → KDJ golden + MACD bullish turn (SNDK case)."""
    closes = [100 - 0.1 * i for i in range(40)] + [96.0, 96.4, 96.9, 97.5]
    return [{"t": f"2026-06-25T17:{m:02d}:00Z", "o": 100, "h": c + 0.2,
             "l": c - 0.2, "c": c, "v": 1000} for m, c in enumerate(closes)]


def test_reversal_alert():
    print("\n[H] 反轉偵測 — KDJ+MACD 同向 = alert（SNDK 範例）")
    r = sp.detect_reversal("SNDK", _v_shape_bars())
    check(r is not None, "V-shape → reversal detected")
    check(r and r["direction"] == "up", f"direction up (got {r and r['direction']})")
    check(r and r["alert"] is True, "KDJ+MACD 同向 → alert=True")
    check(r and r["strength"] == "strong", "alert → strength strong")
    check(r and any("KDJ" in b for b in r["basis"]) and any("MACD" in b for b in r["basis"]),
          f"basis 含 KDJ+MACD (got {r and r['basis']})")


def test_reversal_none_on_flat():
    print("\n[I] 反轉偵測 — 平盤無交叉 → None")
    flat = [{"t": f"2026-06-25T17:{m:02d}:00Z", "o": 100, "h": 100, "l": 100,
             "c": 100, "v": 1000} for m in range(44)]
    check(sp.detect_reversal("FLAT", flat) is None, "flat → None (不列)")


def test_signal_flow():
    print("\n[J] 訊號流重建 — 事件帶時間、新到舊")
    flow = sp.build_signal_flow("SNDK", _v_shape_bars())
    check(len(flow) > 0, f"flow 有事件 (got {len(flow)})")
    check(all("at" in e and "icon" in e and "label" in e for e in flow), "每事件含 at/icon/label")
    ats = [e["at"] for e in flow]
    check(ats == sorted(ats, reverse=True), "newest-first 排序")


def _ramp(start, step, n):
    return [round(start + step * i, 4) for i in range(n)]


def test_trend_bull():
    print("\n[K] 順勢續攻 — 嚴格多頭排列(ma5>ma10>ma20)+KDJ K>D+創高")
    tr = sp.detect_trend("BULL", bars(_ramp(100.0, 0.25, 30)))
    check(tr is not None, "穩定上升序列 → 偵測到 trend")
    check(tr and tr["direction"] == "up", f"direction up (got {tr and tr['direction']})")
    check(tr and tr["dir_zh"] == "順勢續攻", "dir_zh 順勢續攻")
    check(tr and tr["ma"]["5"] > tr["ma"]["10"] > tr["ma"]["20"], "ma5>ma10>ma20 嚴格疊排")
    check(tr and tr["k"] > tr["d"] and tr["k"] >= sp.TREND_K_MIN, f"K>D 且 K≥{sp.TREND_K_MIN}")
    check(tr and "均線多頭排列" in tr["basis"], f"basis 含均線多頭排列 (got {tr and tr['basis']})")


def test_trend_bear():
    print("\n[L] 順勢續跌 — 嚴格空頭排列(ma5<ma10<ma20)+KDJ K<D+破低")
    tr = sp.detect_trend("BEAR", bars(_ramp(120.0, -0.25, 30)))
    check(tr is not None, "穩定下降序列 → 偵測到 trend")
    check(tr and tr["direction"] == "down", f"direction down (got {tr and tr['direction']})")
    check(tr and tr["dir_zh"] == "順勢續跌", "dir_zh 順勢續跌")
    check(tr and tr["ma"]["5"] < tr["ma"]["10"] < tr["ma"]["20"], "ma5<ma10<ma20 嚴格疊排")
    check(tr and tr["k"] < tr["d"], "K<D")


def test_trend_chop_none():
    print("\n[M] 盤整震盪不成排列 → 無 trend")
    chop = [100.0 + (0.5 if i % 2 else 0.0) for i in range(30)]
    check(sp.detect_trend("CHOP", bars(chop)) is None, "上下震盪 → None")


def test_trend_insufficient():
    print("\n[N] bar 數不足(<ma20+1) → None")
    check(sp.detect_trend("SHORT", bars(_ramp(100.0, 0.25, 10))) is None, "<21 bars → None")


def test_trend_strict_stack():
    print("\n[O] 嚴格門檻 — 漲後回落破排列 → 不報多頭續攻")
    closes = _ramp(100.0, 0.4, 18) + _ramp(107.0, -0.5, 12)
    tr = sp.detect_trend("PULLBACK", bars(closes))
    check(tr is None or tr["direction"] != "up", "回落破排列 → 不報順勢續攻")


def test_counter_trend_demote():
    print("\n[P] 逆勢反轉降級 — 多頭金叉撞空頭排列 → 不當反轉(MU 急跌案)")
    rv = {"direction": "up", "dir_zh": "反轉向上", "alert": True, "basis": ["KDJ金叉"]}
    out = sp.apply_trend_context(rv, {"direction": "down"})
    check(out["counter_trend"] is True, "標記 counter_trend")
    check(out["alert"] is False, "alert 降為 False")
    check(out["dir_zh"] == "逆勢反彈", f"dir_zh → 逆勢反彈 (got {out['dir_zh']})")


def test_aligned_reversal_kept():
    print("\n[Q] 同向反轉保留 — 多頭金叉 + 多頭趨勢 → alert 不動")
    rv = {"direction": "up", "dir_zh": "反轉向上", "alert": True}
    out = sp.apply_trend_context(rv, {"direction": "up"})
    check(not out.get("counter_trend"), "未標 counter_trend")
    check(out["alert"] is True, "alert 維持 True")


def test_reversal_no_trend_kept():
    print("\n[R] 無趨勢時反轉保留 — tr=None → 原樣")
    rv = {"direction": "up", "dir_zh": "反轉向上", "alert": True}
    out = sp.apply_trend_context(rv, None)
    check(not out.get("counter_trend"), "未標 counter_trend")
    check(out["alert"] is True, "alert 維持 True")


def test_flow_collapse():
    print("\n[S] 訊號流收合 — 連續同向只留一筆(不再連三次)")
    evs = [
        {"at": "2026-06-25T14:00:00Z", "icon": "⤴", "kind": "kdj", "dir": "up", "label": "KDJ金叉"},
        {"at": "2026-06-25T14:01:00Z", "icon": "⤴", "kind": "macd", "dir": "up", "label": "MACD金叉"},
        {"at": "2026-06-25T14:02:00Z", "icon": "⤴", "kind": "kdj", "dir": "up", "label": "KDJ金叉"},
        {"at": "2026-06-25T14:05:00Z", "icon": "⤵", "kind": "kdj", "dir": "down", "label": "KDJ死叉"},
    ]
    out = sp._collapse_flow([dict(e) for e in evs], 3)
    check(len(out) == 2, f"三筆連續 up 收成 1 + 1 down = 2 (got {len(out)})")
    check(out[0]["dir"] == "down" and out[0]["at"].endswith("14:05:00Z"), "newest-first：down@14:05")
    up_run = out[1]
    check(up_run["dir"] == "up" and up_run["at"].endswith("14:02:00Z"), "up run 推進到最新 14:02")
    check(up_run["count"] == 3, f"up run count==3 (got {up_run['count']})")
    dirs = [e["dir"] for e in out]
    check(all(dirs[i] != dirs[i + 1] for i in range(len(dirs) - 1)), "輸出無相鄰同向")


def test_ctx_breakout():
    print("\n[T] 區間突破急拉 — 10 分鐘橫盤後衝破區間上緣 → breakout, 不抑制, 高分")
    rows = [(100 + 0.05 * ((-1) ** i), 100.1, 99.9) for i in range(14)]
    rows.append((102.0, 102.0, 100.0))                 # +2% breakout bar
    r = sp.detect_spikes("QUIET", hl_bars(rows))
    check(r is not None and r["direction"] == "spike_up", "spike_up detected")
    check(r and r["context_label"] == "突破急拉", f"context 突破急拉 (got {r and r.get('context_label')})")
    check(r and r["breakout"] is True, "breakout True")
    check(r and r["suppressed"] is False, "突破不抑制")
    check(r and r["sigma_mult"] is not None and r["sigma_mult"] >= 3, f"σ-mult 大 (got {r and r.get('sigma_mult')})")
    check(r and r["score"] >= 60, f"score ≥ 60 (got {r and r.get('score')})")


def test_ctx_counter_trend():
    print("\n[U] 逆勢急拉 — 穩定下降趨勢中突然急拉 → counter（軋空/反轉嫌疑）")
    closes = [round(100 - 0.4 * i, 4) for i in range(14)]
    closes.append(round(closes[-1] * 1.02, 4))         # +2% against the downtrend
    r = sp.detect_spikes("DROP", bars(closes))
    check(r is not None and r["direction"] == "spike_up", "spike_up detected")
    check(r and r["regime"] == "down", f"regime down (got {r and r.get('regime')})")
    check(r and r["context_label"] == "逆勢急拉", f"context 逆勢急拉 (got {r and r.get('context_label')})")
    check(r and r["suppressed"] is False, "逆勢不抑制")


def test_ctx_suppress_noise():
    print("\n[V] σ 自適應抑制 — 高波動來回甩，1.5% 動能 < 2σ + 無確認 + 區間 → 抑制/low")
    closes = [100.0, 101.5] * 10                        # ±1.5% chop, 20 bars
    r = sp.detect_spikes("CHOPPY", bars(closes))
    check(r is not None, "仍偵測到（過絕對門檻）")
    check(r and r["sigma_mult"] is not None and r["sigma_mult"] < sp.NOISE_SIGMA_K,
          f"σ-mult < {sp.NOISE_SIGMA_K} (got {r and r.get('sigma_mult')})")
    check(r and r["suppressed"] is True, f"suppressed True (got {r and r.get('suppressed')})")
    check(r and r["severity"] == "low", f"severity low (got {r and r.get('severity')})")


def test_legacy_short_unchanged():
    print("\n[W] 短序列走 legacy 路徑 — 無 baseline 欄位，行為不變")
    r = sp.detect_spikes("NVDA", bars([100] * 7 + [102.5]))   # 8 bars (<BASELINE_MIN)
    check(r and r["severity"] == "high", "rmax≥2 → high（同舊行為）")
    check(r and r["sigma_mult"] is None, "無 baseline → sigma_mult None")
    check(r and r["suppressed"] is False, "legacy 不抑制")
    check(r and r["context_label"] is None, "legacy 無 context_label")


def test_pump_fade():
    print("\n[X] 急拉擊殺 — 急拉 +3% 後被急殺回吐過半 → pump_fade")
    closes = [100, 100, 100, 100.5, 101.5, 103.0, 102.0, 101.4]
    pf = sp.detect_pump_fade("PUMP", bars(closes))
    check(pf is not None, "偵測到 pump_fade")
    check(pf and pf["dir_zh"] == "急拉擊殺", f"dir_zh 急拉擊殺 (got {pf and pf.get('dir_zh')})")
    check(pf and pf["pump_pct"] >= 2.5, f"pump_pct ~+3 (got {pf and pf.get('pump_pct')})")
    check(pf and pf["retrace"] >= 0.5, f"retrace ≥ 0.5 (got {pf and pf.get('retrace')})")
    check(pf and "急拉擊殺" in pf["text_zh"], "text 含 急拉擊殺")


def test_pump_fade_mirror():
    print("\n[Y] 急殺反軋 — 急殺 -3% 後快速收回過半 → mirror pump_fade")
    closes = [100, 100, 100, 99.5, 98.5, 97.0, 98.0, 98.6]
    pf = sp.detect_pump_fade("FLUSH", bars(closes))
    check(pf is not None, "偵測到 mirror pump_fade")
    check(pf and pf["dir_zh"] == "急殺反軋", f"dir_zh 急殺反軋 (got {pf and pf.get('dir_zh')})")
    check(pf and pf["direction"] == "down_then_up", "direction down_then_up")


def test_pump_fade_none():
    print("\n[Z] 平順趨勢無回吐 → pump_fade None")
    check(sp.detect_pump_fade("RAMP", bars(_ramp(100.0, 0.3, 12))) is None, "穩升無 fade → None")


def test_regime_context():
    print("\n[AA] 10 分鐘脈絡 — 上升序列 → regime up + spark + 距高 + σ 上限")
    cx = sp.regime_context(bars(_ramp(100.0, 0.2, 20)))
    check(cx is not None, "≥BASELINE_MIN bars → 有脈絡")
    check(cx and cx["regime"] == "up" and cx["regime_zh"] == "多頭", f"regime up/多頭 (got {cx and cx.get('regime')})")
    check(cx and len(cx["spark"]) == sp.REGIME_WINDOW, f"spark = {sp.REGIME_WINDOW} 點 (got {cx and len(cx.get('spark', []))})")
    check(cx and cx["dist_high"] <= 0, f"距高 ≤ 0 (got {cx and cx.get('dist_high')})")
    check(cx and (cx["sigma_mult"] is None or cx["sigma_mult"] <= 50.0), "σ-mult 有上限 50")


def test_regime_context_insufficient():
    print("\n[AB] 10 分鐘脈絡 — bar 數不足 → None")
    check(sp.regime_context(bars([100] * 10)) is None, "<BASELINE_MIN → None")


def main():
    test_no_spike()
    test_insufficient()
    test_spike_up()
    test_spike_down()
    test_m3_only()
    test_vol_confirm()
    test_confirmation()
    test_watchlist_loader()
    test_reversal_alert()
    test_reversal_none_on_flat()
    test_signal_flow()
    test_trend_bull()
    test_trend_bear()
    test_trend_chop_none()
    test_trend_insufficient()
    test_trend_strict_stack()
    test_counter_trend_demote()
    test_aligned_reversal_kept()
    test_reversal_no_trend_kept()
    test_flow_collapse()
    test_ctx_breakout()
    test_ctx_counter_trend()
    test_ctx_suppress_noise()
    test_legacy_short_unchanged()
    test_pump_fade()
    test_pump_fade_mirror()
    test_pump_fade_none()
    test_regime_context()
    test_regime_context_insufficient()
    print("\n" + "=" * 50)
    if _FAILS:
        print(f"FAILED — {len(_FAILS)} assertion(s):")
        for m in _FAILS:
            print(f"  - {m}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

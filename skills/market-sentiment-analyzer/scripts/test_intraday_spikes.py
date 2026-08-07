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


def ts_bars(closes, end_min, hl=0.0):
    """Bars whose LAST bar sits at `end_min` minutes-past-UTC-midnight (2026-06-25).
    開盤窗測試專用：09:30 ET = 13:30 UTC（EDT）。hl = 高低點對 close 的展幅。"""
    n = len(closes)
    out = []
    for i, c in enumerate(closes):
        m = end_min - (n - 1) + i
        out.append({"t": f"2026-06-25T{m // 60:02d}:{m % 60:02d}:00Z",
                    "o": c, "h": c + hl, "l": c - hl, "c": c, "v": 1000})
    return out


ET_0935 = 13 * 60 + 35      # 開盤窗內（09:35 ET）
ET_1300 = 17 * 60           # 開盤窗外（13:00 ET）


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
    print("\n[H] 反轉偵測 — KDJ+MACD 雙確認 + 大位移 = alert（SNDK 範例）")
    r = sp.detect_reversal("SNDK", _v_shape_bars())
    check(r is not None, "V-shape → reversal detected")
    check(r and r["direction"] == "up", f"direction up (got {r and r['direction']})")
    check(r and r["zone"] == "超賣翻揚", f"zone 超賣翻揚 (got {r and r.get('zone')})")
    check(r and r["alert"] is True, "雙確認 + zone → alert=True")
    check(r and r["strength"] == "strong", "alert → strength strong")
    check(r and r["both"] is True, "both=True（雙確認已是前提）")
    check(r and any("KDJ" in b for b in r["basis"]) and any("MACD" in b for b in r["basis"]),
          f"basis 含 KDJ+MACD (got {r and r['basis']})")
    check(r and r.get("disp_pct") is not None and r["disp_pct"] > 0,
          f"disp_pct 為正位移 (got {r and r.get('disp_pct')})")
    check(r and r.get("disp_sigma_mult") is not None
          and r["disp_sigma_mult"] >= sp.REV_SIGMA_K,
          f"disp_sigma_mult ≥ {sp.REV_SIGMA_K} (got {r and r.get('disp_sigma_mult')})")


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


# ── 反轉降噪四件套（雙確認 / σ 位移 / 翻面冷卻 / 開盤加嚴窗）─────────────────
def _single_source_bars():
    """穩定上升 42 根後小回檔兩根 → 只有 KDJ 死叉、MACD 沒翻 = 單一來源。
    舊版會報「反轉向下」（多頭排列中的雜訊），新版必須 None。"""
    return bars([round(100 + 0.2 * i, 4) for i in range(42)] + [108.2, 108.1])


def _chop_bars():
    """±0.5% 來回甩 44 根：KDJ 金叉 + MACD 金叉都在，但位移 0.5% ≈ 自身 σ 0.53%
    → 位移／σ ≈ 0.95 < REV_SIGMA_K。這就是「小小波動就報反轉」的原型。"""
    return bars([100.0 + (0.5 if i % 2 else 0.0) for i in range(44)])


def _flat_then_jump(pct):
    """完全平盤 40 根（σ = 0，算不出倍數）後跳一根 → 走 REV_MIN_DISP_PCT 固定門檻。"""
    return bars([100.0] * 40 + [round(100 * (1 + pct / 100), 4)])


def test_reversal_needs_both():
    print("\n[AC] 雙確認 — 只有 KDJ 交叉、MACD 沒翻 → 不算反轉")
    b = _single_source_bars()
    closes = [x["c"] for x in b]
    kc, ka, _ = sp._kdj_cross_recent([x["h"] for x in b], [x["l"] for x in b], closes)
    md, _, _ = sp._macd_turn_recent(closes)
    check(kc == "death", f"fixture 確實有 KDJ 死叉 (got {kc})")
    check(md is None, f"fixture 確實沒有 MACD 翻轉 (got {md})")
    check(sp.detect_reversal("SOLO", b) is None, "單一來源 → None（舊版會誤報反轉向下）")


def test_reversal_disp_gate_fail():
    print("\n[AD] σ 位移門檻 — 雙確認但位移 < 1.5σ → 降級不報")
    b = _chop_bars()
    closes = [x["c"] for x in b]
    kc, _, _ = sp._kdj_cross_recent([x["h"] for x in b], [x["l"] for x in b], closes)
    md, _, _ = sp._macd_turn_recent(closes)
    check(kc == "golden" and md == "up", f"fixture 雙確認齊備 (kdj={kc} macd={md})")
    sigma = sp._ret_sigma(closes[len(closes) - 1 - sp.REGIME_WINDOW:len(closes) - 1])
    disp = abs((closes[-1] / closes[-2] - 1) * 100)
    check(sigma and disp / sigma < sp.REV_SIGMA_K,
          f"位移/σ = {disp / sigma:.2f} < {sp.REV_SIGMA_K}")
    check(sp.detect_reversal("CHOPPY", b) is None, "整盤雜訊 → None（不再轟炸）")


def test_reversal_sigma_fallback():
    print("\n[AE] σ 算不出 → 退固定門檻 REV_MIN_DISP_PCT")
    ok = sp.detect_reversal("FLATJ", _flat_then_jump(0.4))
    check(ok is not None, f"平盤後 +0.4% ≥ {sp.REV_MIN_DISP_PCT}% → 放行")
    check(ok and ok["disp_sigma_mult"] is None, f"σ=0 → disp_sigma_mult None (got {ok and ok['disp_sigma_mult']})")
    check(ok and abs(ok["disp_pct"] - 0.4) < 0.01, f"disp_pct ≈ 0.4 (got {ok and ok['disp_pct']})")
    check(ok and ok["alert"] is False and ok["strength"] == "med",
          f"無 zone 又無 σ 倍數 → 不升 alert (got alert={ok and ok['alert']})")
    check(sp.detect_reversal("FLATJ", _flat_then_jump(0.2)) is None,
          f"平盤後 +0.2% < {sp.REV_MIN_DISP_PCT}% → None")


def test_flip_cooldown_suppress():
    print("\n[AF] 翻面冷卻 — 10 分鐘內反向翻面且無 zone/高 σ → 壓掉")
    prev = {"symbol": "X", "direction": "down", "at": "2026-06-25T17:35:00Z"}
    rv = {"symbol": "X", "direction": "up", "at": "2026-06-25T17:40:00Z",
          "zone": None, "disp_sigma_mult": 1.8}
    check(sp.flip_cooldown_ok(rv, prev) is False, "5 分鐘前反向 + 弱訊號 → 不放行")


def test_flip_cooldown_release():
    print("\n[AG] 翻面冷卻放行 — zone 註記 / 高 σ / 逾時 / 同向")
    prev = {"symbol": "X", "direction": "down", "at": "2026-06-25T17:35:00Z"}
    base = {"symbol": "X", "direction": "up", "at": "2026-06-25T17:40:00Z",
            "zone": None, "disp_sigma_mult": 1.8}
    check(sp.flip_cooldown_ok({**base, "zone": "超賣翻揚"}, prev) is True, "有 zone → 放行")
    check(sp.flip_cooldown_ok({**base, "disp_sigma_mult": sp.REV_FLIP_SIGMA}, prev) is True,
          f"σ ≥ {sp.REV_FLIP_SIGMA} → 放行")
    check(sp.flip_cooldown_ok({**base, "at": "2026-06-25T17:50:00Z"}, prev) is True,
          f"距前次 ≥ {sp.REV_FLIP_COOLDOWN_MIN} 分 → 放行")
    check(sp.flip_cooldown_ok({**base, "direction": "down"}, prev) is True, "同向 → 不套冷卻")
    check(sp.flip_cooldown_ok(base, None) is True, "無前一輪 → 放行")
    check(sp.flip_cooldown_ok(None, prev) is True, "本輪無反轉 → True（無事可壓）")


def test_prev_reversal_map():
    print("\n[AH] 前檔解析 — 同日才套冷卻；缺檔/壞格式/跨日 → {}")
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).isoformat()
    good = {"generated_at": today, "reversals": [{"symbol": "AAPL", "direction": "up",
                                                  "at": "2026-06-25T17:40:00Z"}]}
    m = sp.prev_reversal_map(good)
    check(m.get("AAPL", {}).get("direction") == "up", f"同日 → 取得 AAPL (got {m})")
    check(sp.prev_reversal_map({"generated_at": "2020-01-01T00:00:00Z",
                                "reversals": [{"symbol": "AAPL"}]}) == {}, "跨日 → {}")
    check(sp.prev_reversal_map(None) == {}, "None → {}")
    check(sp.prev_reversal_map({"generated_at": "not-a-time"}) == {}, "壞時間 → {}")
    check(sp.prev_reversal_map({"generated_at": today}) == {}, "無 reversals → {}")


def test_prev_payload_graceful():
    print("\n[AI] 前檔缺失 graceful — 不存在/壞 JSON → None，build() 簽名相容")
    import inspect
    check(sp._read_prev_payload("/nonexistent/does/not/exist.json") is None, "檔不存在 → None（不 raise）")
    bad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bad_prev.tmp.json")
    try:
        with open(bad, "w", encoding="utf-8") as f:
            f.write("{not json")
        check(sp._read_prev_payload(bad) is None, "壞 JSON → None（不 raise）")
    finally:
        if os.path.exists(bad):
            os.remove(bad)
    params = inspect.signature(sp.build).parameters
    check(list(params) == ["prev_payload"] and params["prev_payload"].default is None,
          f"build(prev_payload=None) 簽名（dashboard_server 呼叫 build() 相容）(got {list(params)})")


def _no_key_env(fn):
    """暫時清掉 Alpaca 金鑰，確保 build() 走 skeleton 路徑、測試絕不連網。"""
    saved = {k: os.environ.pop(k, None) for k in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY")}
    try:
        return fn()
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def test_build_version():
    print("\n[AJ] build() — version 1.6 + 無金鑰時 skeleton")
    p = _no_key_env(lambda: sp.build())
    check(p.get("version") == "1.6", f"version 1.6 (got {p.get('version')})")
    check(p.get("_health") == "no_alpaca_key", f"無金鑰 → skeleton (got {p.get('_health')})")
    p2 = _no_key_env(lambda: sp.build(prev_payload={"generated_at": "x", "reversals": []}))
    check(p2.get("version") == "1.6", "傳入 prev_payload 亦可（不 raise）")


def test_open_grace_helper():
    print("\n[AK] 開盤窗判定 — 吃 bar 時間戳（09:30 含 ~ 09:45 不含），非 wall clock")
    check(sp.in_open_grace("2026-06-25T13:30:00Z") is True, "09:30 ET → True（含）")
    check(sp.in_open_grace("2026-06-25T13:44:00Z") is True, "09:44 ET → True")
    check(sp.in_open_grace("2026-06-25T13:29:00Z") is False, "09:29 ET → False")
    check(sp.in_open_grace("2026-06-25T13:45:00Z") is False, "09:45 ET → False（不含）")
    check(sp.in_open_grace("2026-06-25T17:00:00Z") is False, "13:00 ET → False")
    check(sp.in_open_grace("2026-06-25T13:35:00.123456789Z") is True, "奈秒小數可解析")
    check(sp.in_open_grace("bogus") is False and sp.in_open_grace(None) is False,
          "壞字串/None → False（不 raise）")


def test_open_grace_spike_gate():
    print("\n[AL] 開盤窗 — spike 門檻 ×1.5 且未確認者 severity 封頂 med")
    weak = [100] * 7 + [101.2]                      # +1.2%：平時過門檻，窗內不過(需 ≥1.5%)
    check(sp.detect_spikes("OPEN", ts_bars(weak, ET_0935)) is None, "窗內 +1.2% → 不報")
    out = sp.detect_spikes("OPEN", ts_bars(weak, ET_1300))
    check(out is not None and out["severity"] == "med", f"窗外 +1.2% → 照舊 med (got {out and out['severity']})")
    check(out and out["open_grace"] is False, "窗外 open_grace False")
    big_in = sp.detect_spikes("OPEN", ts_bars([100] * 7 + [103.0], ET_0935))
    check(big_in is not None and big_in["open_grace"] is True, "窗內 +3% → 仍偵測到")
    check(big_in and big_in["severity"] == "med", f"窗內未確認 → severity 封頂 med (got {big_in and big_in['severity']})")
    big_out = sp.detect_spikes("OPEN", ts_bars([100] * 7 + [103.0], ET_1300))
    check(big_out and big_out["severity"] == "high", f"窗外 +3% → high 不受影響 (got {big_out and big_out['severity']})")


def test_open_grace_reversal_gate():
    print("\n[AM] 開盤窗 — 反轉額外要求 zone 註記")
    flat = [100.0] * 40 + [100.4]
    check(sp.detect_reversal("OPEN", ts_bars(flat, ET_0935)) is None, "窗內無 zone → 不報")
    check(sp.detect_reversal("OPEN", ts_bars(flat, ET_1300)) is not None, "窗外同一組 bars → 照報")
    vs = [100 - 0.1 * i for i in range(40)] + [96.0, 96.4, 96.9, 97.5]
    rv = sp.detect_reversal("OPEN", ts_bars(vs, ET_0935, hl=0.2))
    check(rv is not None and rv["zone"] == "超賣翻揚", f"窗內有 zone → 放行 (got {rv and rv.get('zone')})")


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
    test_reversal_needs_both()
    test_reversal_disp_gate_fail()
    test_reversal_sigma_fallback()
    test_flip_cooldown_suppress()
    test_flip_cooldown_release()
    test_prev_reversal_map()
    test_prev_payload_graceful()
    test_build_version()
    test_open_grace_helper()
    test_open_grace_spike_gate()
    test_open_grace_reversal_gate()
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

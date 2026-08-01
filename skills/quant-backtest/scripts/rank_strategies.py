#!/usr/bin/env python3
"""rank_strategies — 策略模板基準排名 runner (V4.63.0)。

以 STRATEGIES registry 預設參數,對 12 檔代表性標的 (指數 ETF + 跨產業
mega-cap) 跑 5 年窗、單邊 10 bps 回測,以跨標的「中位數 Sharpe」排名
(比平均值抗單一標的離群),寫入 data/strategy_rank.json 供
Dashboard/backtest.html 策略卡片 badge 使用。

選型脈絡:V4.63.0 曾對 20 個候選模板跑同一基準,取前 10 名 + 自家
momentum 引擎入 registry;落選 9 個 (chandelier / rsi2 / stoch / zscore /
boll_breakout / adx_trend / macd_cross / dip_buy / breakout_vol,
中位 Sharpe 0.42→0.09) 不入 UI。

Discipline: 探索層。0 LLM。排名僅供卡片參考,不進 investment_protocol。

Usage:
    python3 skills/quant-backtest/scripts/rank_strategies.py
    python3 skills/quant-backtest/scripts/rank_strategies.py --period 5y --cost-bps 10

Exit codes: 0 ok / 1 fatal (全數 fetch 失敗) / 2 degraded (部分 ticker 失敗)。
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from backtest import (  # noqa: E402
    DATA_DIR, PERIOD_BARS, PERIOD_FETCH, STRATEGIES,
    build_signals, replay_momentum_scores, run_strategy,
)

REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "_shared"))
from technical_core import fetch_history  # noqa: E402

# 指數 2 + 跨產業 mega-cap 10 (科技/電商/金融/能源/醫療)
UNIVERSE = ["SPY", "QQQ", "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META",
            "TSLA", "JPM", "XOM", "UNH"]


def main():
    ap = argparse.ArgumentParser(description="strategy template benchmark ranking")
    ap.add_argument("--period", default="5y", choices=list(PERIOD_BARS))
    ap.add_argument("--cost-bps", type=float, default=10)
    ap.add_argument("--output-dir", default=DATA_DIR)
    args = ap.parse_args()

    bars = PERIOD_BARS[args.period]
    fulls, failed = {}, []
    for tk in UNIVERSE:
        t0 = time.time()
        try:
            hist, _ = fetch_history(tk, period=PERIOD_FETCH[args.period])
            fulls[tk] = replay_momentum_scores(hist)
            print(f"[fetch] {tk} {len(hist)} bars in {time.time() - t0:.1f}s")
        except Exception as e:
            failed.append(tk)
            print(f"[warn] {tk} fetch failed: {e}")
    if not fulls:
        print("[fatal] no ticker fetched")
        sys.exit(1)

    rows = {}
    for key, spec in STRATEGIES.items():
        params = dict(spec["params"])
        stats = []
        for tk, full in fulls.items():
            w = min(bars, len(full))
            entry, exit_ = build_signals(key, full, params)
            r = run_strategy(full.iloc[-w:], entry.iloc[-w:], exit_.iloc[-w:],
                             args.cost_bps)
            stats.append(r["metrics"])
        rows[key] = {
            "label": spec["label"],
            "default_params": params,
            "median_sharpe": round(float(np.median([m["sharpe"] for m in stats])), 2),
            "median_cagr_pct": round(float(np.median([m["cagr_pct"] for m in stats])), 1),
            "median_max_dd_pct": round(float(np.median([m["max_dd_pct"] for m in stats])), 1),
            "median_n_trades": int(np.median([m["n_trades"] for m in stats])),
            "beat_bh_pct": round(100 * sum(
                m["total_return_pct"] > m["bh_total_return_pct"] for m in stats)
                / len(stats)),
        }
        print(f"[done] {key:15s} medSharpe={rows[key]['median_sharpe']} "
              f"medCAGR={rows[key]['median_cagr_pct']}%")

    ranked = sorted(rows.items(), key=lambda kv: kv[1]["median_sharpe"], reverse=True)
    out = {
        "schema_version": "v1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "methodology": f"{len(fulls)} 檔 ({', '.join(fulls)}) × {args.period} 窗 × "
                       f"單邊 {args.cost_bps:g} bps,registry 預設參數,"
                       "以跨標的中位數 Sharpe 排名",
        "universe": list(fulls),
        "failed_tickers": failed,
        "period": args.period,
        "cost_bps_per_side": args.cost_bps,
        "ranking": [{"rank": i + 1, "template": k, **v}
                    for i, (k, v) in enumerate(ranked)],
    }
    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, "strategy_rank.json")
    tmp = f"{out_path}.tmp{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    os.replace(tmp, out_path)
    print(f"[write] {out_path}")
    sys.exit(2 if failed else 0)


if __name__ == "__main__":
    main()

# short-term-target — Usage Guide

Companion to `SKILL.md` (spec) and `CHANGELOG.md` (versions). This file is the **how-to** for daily / batch use.

---

## Quick start

```bash
# Single ticker, pretty JSON
python3 skills/short-term-target/scripts/predict.py NVDA

# Pipe-friendly compact JSON
python3 skills/short-term-target/scripts/predict.py AMD --json-only | jq '.horizons.5d'

# Batch (shell loop)
for t in NVDA AMD CEG IONQ; do
  python3 skills/short-term-target/scripts/predict.py $t --json-only > out_$t.json
done
```

---

## How to read the output (interpretation guide)

### 1. **Always check `confidence` and `confidence_breakdown` BEFORE the target**

A target of "$210" with confidence 0.15 is almost noise. A target of "$210" with confidence 0.65 means several drivers aligned.

The breakdown tells you WHY:
```
"confidence_breakdown": {
  "base": 0.50,                   # always 0.50 starting point
  "news_freshness": +0.12,        # high if news driver was strong + fresh
  "sector_heat_persistence": +0.10,  # high if sector is HOT
  "atr_penalty": -0.04,           # negative if stock is volatile
  "horizon_penalty": -0.05,       # 5d -0.05, 15d -0.15 (longer = less certain)
  "data_completeness_bonus": +0.02,
  "model_clamped_penalty": 0.0    # -0.15 if prediction was clamped
}
```

Sum equals final confidence (within rounding). Audit-able.

### 2. **`drivers` shows the input scores; `driver_labels` shows the human reading**

```
"drivers": {
  "news_score": 0.4,        # -1 to +1
  "sector_heat": 0.64,      # 0 to 1
  "momentum_score": 0.6,    # -1 to +1
  "atr_pct": 3.95           # daily ATR as % of price
}
"driver_labels": {
  "momentum": "RSI=97, current>MA20>MA50",
  "news": "vol 2.2× avg, gap +13.9%",
  "sector_status": "ok_proxy_median"
}
```

If `news_score` and `momentum_score` are both 0, the prediction is essentially "follow sector heat" — much weaker basis than catalyst-driven moves.

### 3. **`model_clamped: true` is a red flag**

It means the raw model wanted to predict outside [-cap, +cap] and was forced to the boundary. Confidence is auto-penalized -0.15.

If you see `model_clamped: true` with confidence still > 0.4, the underlying drivers were extreme — either real signal or driver mis-calibration.

### 4. **`benchmark_etf` + `implied_alpha_pct`**

Tells you: "is the stock predicted to beat its sector ETF?"

```
"benchmark_etf": "SOXX",
"benchmark_realized_pct": 1.2,    # SOXX last N days
"implied_alpha_pct": 3.0          # prediction - benchmark realized
```

⚠️ **Caveat**: Compares forward prediction to backward realized. If SPY just had a huge week, alpha will look small/negative. Use as **directional context**, not as a definitive alpha statement.

### 5. **`status: insufficient_data` is a feature, not a bug**

When sources are too stale, the script REFUSES to predict:
```
"5d": {
  "status": "insufficient_data",
  "missing": ["sector>72h_old", "news>24h_old"],
  "would_need": "Refresh stale sources OR wait..."
}
```

**Do not extrapolate from `1d` to fill in `5d` when 5d is insufficient**. The whole point is to be honest.

### 6. **`global_warnings` matter**

```
"global_warnings": [
  "v0.1 uses volume/gap proxy for news driver; real Finnhub /company-news integration deferred to v0.2",
  "dual_fetch unavailable (no_ticker_file); using yfinance only"
]
```

These are persistent caveats about the run. The first warning is **always present in v0.1** because the news driver is a proxy.

---

## Trading meta — for actual trades

```json
"trading_meta": {
  "stop_suggestion": 188.0,            // 1.5×ATR below current
  "stop_distance_pct": 5.93,
  "position_size_hint_pct": 5.0,       // 0.33/ATR%, capped 0.5-5%
  "tx_cost_estimate_pct": 0.05,        // flat estimate for liquid US
  "min_holding_days": 1,
  "exit_trigger": "Close < 188.0 OR 5d target X reached OR confidence drops < 0.4"
}
```

Use cases:
- **Entry**: pull `target_low` (entry zone bottom) + `target_high` (entry zone top) from your chosen horizon
- **Stop**: `stop_suggestion` is mechanical 1.5×ATR; consider tighter for low-conviction trades
- **Position sizing**: `position_size_hint_pct` assumes 0.5% portfolio risk per trade. If you want different risk, scale linearly
- **Exit**: re-run script daily; if confidence drops < 0.4 OR new prediction direction reversed → consider exit

---

## Recalibration — the weekend workflow

Every Saturday/Sunday:

1. **Run weekly review** (Step 7, separate tool — to be built)
   ```bash
   python3 skills/short-term-target/scripts/weekly_review.py
   ```
   Reads `data/recommendations/<dates>.json`, compares to actual price action, suggests weight adjustments.

2. **Read the report**: `reports/SHORT_TERM_WEEKLY_<DATE>.md`
   - Per-horizon hit rate (1d / 5d / 15d separately)
   - Per-theme alpha
   - Failed-case analysis ("why did NTRS prediction miss?")
   - Suggested config diffs

3. **Decide**: do you accept the suggestions?
   - Edit `skills/short-term-target/config/weights.yaml`
   - **Bump `weights_version`** (e.g., `v0.1.0` → `v0.1.1`)
   - All future predictions tagged with new version

4. **Don't auto-apply**: tool gives suggestions; you have final say. This prevents over-fitting.

---

## Common interpretation mistakes

| Mistake | Reality |
|---|---|
| Using `target_central` as a price target with stop at `target_low` | They're not entry/SL pairs. Range is volatility envelope; stop is in `trading_meta.stop_suggestion` |
| Reading `1d target +4%` as "buy now expect +4% tomorrow" | Confidence matters. 0.6 confidence on +4% means "directionally likely up but range is wide" |
| Treating `implied_alpha_pct` as guaranteed alpha | It's forward prediction vs backward benchmark; rough proxy only |
| Ignoring `model_clamped: true` | This is the main "the model wanted to be more extreme" signal |
| Treating `confidence > 0.7` as high | v0.1 caps at 0.95 and 15d caps near 0.6. > 0.7 is "very high" in this scale |

---

## Comparison with sister skills

| Skill | Time horizon | Method | Output |
|---|---|---|---|
| `short-term-target` (this) | 1d / 5d / 15d | News + sector + momentum + ATR fusion | Target range + confidence |
| `momentum-monitor` | tape (intraday-ish) | RSI + MA + volume composite | 0-100 score + signals |
| `earnings-valuation-forecaster` | 12 months | Forward EPS × multiple | Bull/Base/Bear scenarios |
| `investment_protocol_v4_8.md` | 3-6 months | Multi-lane subagent debate | BUY/HOLD/SELL + position size |

These are **complementary, not redundant**. You can use multiple together; just don't average their outputs.

---

## When NOT to use this skill

| Situation | Use instead |
|---|---|
| You want long-term valuation | `earnings-valuation-forecaster` |
| You want a full investment decision (not just price view) | `分析 [TICKER]` (investment_protocol) |
| You want pure technical scan across many stocks | `momentum-monitor` (batch mode) |
| You want sector / theme heat | `theme-detector` |
| You want fundamental quality check | `kanchi-dividend-sop` / `vcp-screener` etc |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| All horizons `insufficient_data` | sector_intel cache stale (>7d) | Run `產業掃描` to refresh |
| Confidence very low for all horizons | Stock has high ATR (typical >6%) | Expected — high vol = low confidence |
| `dual_fetch unavailable` warning | dual_fetch not run for ticker today | Run `bash skills/finnhub-client/scripts/run_dual_fetch.sh --tickers TICKER` first |
| Benchmark always SPY | sub_industry GICS lookup deferred to v0.2 | Acceptable for v0.1; predictions still work |
| Prediction looks reversed (negative when news bullish) | Drivers conflict (e.g., RSI 95 → momentum_score 0.3 dampened) | Read `driver_labels` to understand |

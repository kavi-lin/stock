---
name: short-contrarian-analyst
description: Burry-style valuation anchor and contrarian veto check for a single ticker. Computes Burry Score (0-100) from FCF yield, EV/EBIT, debt/equity, and price vs 52-week high. Use in investment protocol Phase 2 as the 5th agent — triggers T4 veto when Burry Score < 20 (extremely overvalued) on an otherwise bullish thesis.
market: us-equity
scope: single-ticker
data_sources: [yfinance]
---

# Short Contrarian Analyst (Burry)

## Purpose
Independent valuation anchor for investment protocol Phase 2. Unlike Bull/Bear/Sentiment/
Technical agents (which are weighted), this agent has **veto power** on T4 (overvaluation
veto) when Burry Score < 20 — forces the protocol into HOLD regardless of other bullish signals.

## Usage
```bash
python3 skills/short-contrarian-analyst/scripts/burry_score.py NVDA
python3 skills/short-contrarian-analyst/scripts/burry_score.py KO --json-only
```

## Burry Score components (0-100, higher = cheaper / safer)

| Metric | Weight | Scoring |
|---|---|---|
| FCF yield (FCF / EV) | 35% | < 2% → 10, 5% → 50, 10% → 90 |
| EV / EBIT * | 25% | > 30 → 10, 15 → 50, < 8 → 90 |
| Debt / Equity | 15% | > 2 → 10, 1 → 50, < 0.3 → 90 |
| Price vs 52w high | 15% | at high → 20, -20% → 60, -40% → 90 |
| Insider activity | 10% | net buy → 80, neutral → 50, net sell → 20 |

\* **The `ev_ebit` key is really EV/EBITDA.** yfinance exposes no EBIT, so `burry_score.py:93`
substitutes `ebitda`. The key name is frozen for `history.json` / renderer compatibility —
do not rename it. The `reasoning` string reports it honestly as `EV/EBITDA`.

Components missing → dropped from the weighted average, and the surviving weights
renormalize to sum 1 (`:131-133`). `weights_active` lists which ones counted.

**A missing component must never be scored as a bad one.** Both the insider read and the
52-week-high read return `None` on failure so they renormalize out. Until V4.111.7 a failed
price fetch instead set `pct_below_high = 0.0`, which lands on the harshest band (20) and
entered the average as if it were real data — a transient network blip could manufacture a
`WARNING`, or a `T4_VETO`, out of nothing. This agent holds veto power; that path is now
`None` and the `reasoning` string says the component was dropped.

## Veto rules
- Burry Score `< 20` → **T4 veto active** → HOLD regardless of other agents
- Burry Score `< 35` → **warning flag** → Phase 4 position multiplier × 0.7
- Burry Score `>= 60` → deep value bonus → Phase 4 multiplier × 1.15

## Output schema
```json
{
  "ticker": "NVDA",
  "generated_at": "ISO8601",
  "burry_score": "float 0-100, or null if every component is missing",
  "verdict": "T4_VETO | WARNING | NEUTRAL | VALUE_BONUS | UNKNOWN",
  "components": {
    "fcf_yield_pct": "float or null",
    "ev_ebit": "float or null — see the EV/EBITDA note above",
    "debt_to_equity": "float or null",
    "pct_below_52w_high": "float or null (null = price fetch failed)",
    "insider_net": "BUY | SELL | NEUTRAL | UNKNOWN"
  },
  "component_scores": {"fcf_yield": 50, "ev_ebit": 30, ...},
  "weights_active": ["fcf_yield", "ev_ebit", ...],
  "reasoning": "string"
}
```

Failure → `{"error", "ticker"}` on stdout + exit 1.

## Division of labour with the PM (Phase 2)

The script is invoked inline by the PM at the end of Phase 2 (protocol `:701`); there is no
programmatic caller. The Phase 2 JSON contract (protocol `:728-739`) has two fields this
script does **not** emit — the PM synthesizes them from the script output plus the
PEER_BUNDLE / FMP_SUPP_BUNDLE / EARNINGS_ANALYST_BUNDLE adjustment rules (protocol `:715-725`):

| Field | Source |
|---|---|
| `burry_voice` | LLM — narrative carrying every rule adjustment, traceable |
| `veto_flag` | LLM — `true` when `burry_score < 20`, i.e. `verdict == "T4_VETO"` |

Burry is not one of the six scored lanes (`apply_det_shadow.py:368` `LANE_NAMES` excludes it);
its fields land flat on `trades_this_session[0]` as `burry_score` / `burry_override_active` /
`burry_override_recheck_date`.

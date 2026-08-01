# MU DCF Rebuild Audit — 2026-08-02

## Result

- Rebuilt fair value: **$762.13/share**
- Cached close: **$823.03** → upside **-7.4%**
- User-reported price: **$812** → upside approximately **-6.1%**
- WACC: **12.49%**; terminal growth: **2.5%**
- 5×5 WACC/g sensitivity: **$693.74–$853.60**

This is a DCF output, not the final canonical multi-method fair value.

## What was rebuilt

| Driver | Rebuilt treatment |
|---|---|
| Timing | FY2026 roll-forward is t0; discounted forecast starts FY2027 |
| Revenue | FY2026 base $126.52B; FY2027–31 growth capped at 45% / 30% / 20% / 12% / 8% |
| Revenue path | $183.45B / $238.48B / $286.18B / $320.52B / $346.16B |
| EBIT margin | Fades from current 74.14% state to 33.0% normalized terminal margin |
| Capex/revenue | Fades from 23.09% to 20.17%; terminal capex includes growth reinvestment |
| Balance/share | Latest quarterly net cash $20.23B; 1.126B shares |
| Beta/WACC | Observed beta 2.142 retained; Blume-adjusted beta 1.7613 used for through-cycle WACC |

## Why the old outputs were lower

The old self DCF mixed three-year trough ratios with the new earnings regime and produced
non-positive terminal FCFF. The interim rebuilt value of $662.30 fixed operating drivers but
still applied the dislocation-period beta 2.142 directly, producing a 14.17% WACC. Matching the
cost of capital to the through-cycle operating model lowers WACC to 12.49% and moves fair value
to $762.13 without calibrating to the market price.

Provider cash-flow sign inconsistencies and a quarterly EBITDA value below operating income are
ignored and surfaced as warnings. The opaque vendor DCF values remain visible for audit but no
longer receive a live vote when this rebuilt structural model is eligible.

# MU · Driver-based DCF Model — 2026-08-02

> fair value **$762.13** vs current $823.03 → **-7.4%** · WACC 12.49% · terminal g 2.50%
> projection mode `structural_shift_through_cycle`

## Assumptions（value / provenance）

| 假設 | 值 | 來源 |
|---|---|---|
| revenue_growth_y1 | 0.6000 | analyst |
| revenue_growth_y2 | 0.1145 | analyst |
| terminal_growth | 0.0250 | default |
| ebitda_margin | 0.3311 | derived |
| da_pct | 0.3441 | derived |
| capex_pct | 0.4174 | derived |
| nwc_pct | 0.0746 | derived |
| tax_rate | 0.1507 | derived |
| beta | 2.1420 | derived |
| risk_free | 0.0468 | derived |
| erp | 0.0450 | default |
| cost_of_debt | 0.0618 | default |
| wacc | None | derived |
| projection_mode | structural_shift_through_cycle | derived |
| projection_as_of | 2026-06-25 | skills/earnings-analyst/cache/MU_2026-05-28.json |
| projection_base_revenue | 126516290000 | quarterly_actuals_plus_next_quarter_estimate |
| revenue_path | [183448620500, 238483206650, 286179847980, 320521429738, 346163144117] | quarterly_actuals_plus_next_quarter_estimate |
| ebit_margin_start | 0.7414 | quarterly_rollforward |
| ebit_margin_terminal | 0.3300 | analyst_normalized |
| da_pct_start | 0.2234 | latest_fiscal_year |
| da_pct_terminal | 0.1700 | analyst_normalized |
| capex_pct_start | 0.2309 | quarterly_ttm_abs_capex |
| capex_pct_terminal | 0.2017 | normalized_reinvestment |
| sales_to_capital | 0.7898 | latest_fiscal_year |
| projection_notes | ['FY2027 analyst growth 76.2% capped to 45.0%', 'FY2028 analyst growth 32.3% capped to 30.0%', 'FY2029 analyst growth 69.8% capped to 20.0%', 'FY2030 analyst growth 67.4% capped to 12.0%', 'FY2031 revenue estimate missing; bounded fade used', 'cashflow sign inconsistency: abs(capex) used, reported FCF ignored', 'quarterly EBITDA below operating income: EBITDA field ignored'] | quality_gate |

## FCFF Projection

| Yr | g | Revenue | EBIT % | EBITDA | NOPAT | Capex % | Capex | ΔNWC | FCFF | PV |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 45.0% | 183,448,620,500 | 65.9% | 159,937,845,297 | 102,692,816,274 | 22.5% | 41,286,946,530 | 4,247,151,855 | 96,181,908,442 | 85,502,629,960 |
| 2 | 30.0% | 238,483,206,650 | 57.7% | 185,749,799,996 | 116,835,358,328 | 21.9% | 52,280,288,562 | 4,105,580,127 | 108,632,636,711 | 85,848,455,708 |
| 3 | 20.0% | 286,179,847,980 | 49.5% | 196,296,481,326 | 120,204,066,601 | 21.3% | 61,065,055,962 | 3,558,169,443 | 110,344,216,905 | 77,518,940,189 |
| 4 | 12.0% | 320,521,429,738 | 41.2% | 190,056,386,977 | 112,230,387,592 | 20.8% | 66,521,017,528 | 2,561,881,999 | 101,059,299,990 | 63,113,260,744 |
| 5 | 8.0% | 346,163,144,117 | 33.0% | 173,081,572,059 | 97,018,798,239 | 20.2% | 69,821,106,168 | 1,912,871,893 | 84,132,554,677 | 46,708,346,418 |

- PV explicit $358,691,633,019 + PV terminal $479,239,790,568 = EV $837,931,423,587
- − net debt $-20,228,000,000 = equity $858,159,423,587 ÷ 1,126,000,000 shares

## Sensitivity（WACC × terminal growth，fair value $）

| WACC \ g | 2.00% | 2.25% | 2.50% | 2.75% | 3.00% |
|---|---|---|---|---|---|
| 11.49% | 826.27 | 832.4 | 838.92 | 846.15 | 853.6 |
| 11.99% | 788.24 | 793.23 | 798.54 | 804.44 | 810.47 |
| 12.49% | 753.79 | 757.83 | 762.13 | 766.94 | 771.82 |
| 12.99% | 722.42 | 725.68 | 729.14 | 733.04 | 736.97 |
| 13.49% | 693.74 | 696.34 | 699.1 | 702.25 | 705.39 |

## Warnings

- FY2027 analyst growth 76.2% capped to 45.0%
- FY2028 analyst growth 32.3% capped to 30.0%
- FY2029 analyst growth 69.8% capped to 20.0%
- FY2030 analyst growth 67.4% capped to 12.0%
- FY2031 revenue estimate missing; bounded fade used
- cashflow sign inconsistency: abs(capex) used, reported FCF ignored
- quarterly EBITDA below operating income: EBITDA field ignored
- net debt sourced from latest quarterly earnings context

---
*valuation-modeler · deterministic engine · 數字全由 script 計算*

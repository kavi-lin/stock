# MU DCF-primary Valuation Range — 2026-08-02

## Primary fair value

- MU price used: **$812.00**
- Primary FV: **$762.13** (`structural_shift_through_cycle_dcf`)
- Upside/downside: **-6.14%**
- DCF sensitivity: **$693.74–$853.60**

The primary FV remains the rebuilt DCF. No peer, analyst, or owner-earnings
multiple is averaged into this number.

## Explained range

| Point | Value | Role |
|---|---:|---|
| DCF sensitivity low | $693.74 | Lower intrinsic case |
| DCF primary | $762.13 | Decision FV |
| Fundamental without peer | $797.32 | DCF + owner-earnings scenario |
| DCF sensitivity high | $853.60 | Upper intrinsic case |
| With range-only peer family | $1,291.36 | Cyclical relative scenario |
| Analyst PT consensus | $1,468.26 | Highest eligible external anchor |

Full explained envelope: **$693.74–$1,468.26**. The low driver is DCF
sensitivity; the high driver is analyst PT, not the DCF or peer calculation.

## Audited range-only peers

| Peer | P/E TTM | Why included |
|---|---:|---|
| SNDK | 39.8436× | NAND flash and storage |
| WDC | 29.1514× | NAND and storage |
| STX | 58.8810× | Storage-cycle demand read-through |

- Median peer P/E: **39.8436×**
- MU TTM EPS: **$44.81**
- Peer P/E implied value: **$1,785.39**
- Two-family with-peer scenario: **$1,291.36**

This cohort is adjacent rather than exact: there is no listed US pure-play
DRAM/HBM peer, and storage mix/capital intensity differ. Candidate discovery
was LLM-assisted and user-approved; all P/E observations were fetched again by
Python. The result is `range_only` and cannot replace the DCF primary FV.

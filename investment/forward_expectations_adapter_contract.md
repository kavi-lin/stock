# Forward Expectations Adapter Contract

> Status: Phase 1 contract only. No adapter may change live valuation or decisions.

Implemented adapter: `investment/scripts/forward_expectations_adapters/royalty_ip.py`.

## Purpose

The Forward Expectations core is industry-neutral. An adapter supplies the economic
model for a business model or segment. A company may compose multiple adapters; it
must not be forced into one company-wide technology-style growth model.

```text
Evidence -> Adapter match -> External transmission -> Operating drivers
         -> Financial bridge -> Same-metric expectations matrix -> Shadow output
```

## Required Adapter Shape

```yaml
adapter_id: royalty_ip
version: 1
supported_business_models: [royalty_ip]
required_evidence: []
revenue_drivers: []
cost_drivers: []
external_drivers: []
transmission_rules: []
leading_indicators: []
financial_bridge: []
supported_valuation_methods: []
unsupported_valuation_methods: []
base_rate_cohort_rules: []
degradation_rules: []
```

Every driver and transmission rule must reference evidence records conforming to
`investment/forward_expectations_schema.md`. Unknown values remain `unknown`; an
adapter cannot manufacture a default value merely to complete a model.

## Adapter Matching

LLM output may propose adapter candidates, but it cannot approve them. Matching must
be accepted by deterministic evidence:

- segment revenue and company business description;
- disclosed operating KPIs;
- balance-sheet and cash-flow structure;
- revenue recognition and cost structure;
- source lineage and freshness.

Match results:

| Result | Meaning | Allowed output |
|---|---|---|
| `matched` | Required evidence passes | Independent lane and scenarios |
| `partial` | Some required evidence missing | Range or qualitative catalyst only |
| `generic` | No specialized adapter exists | Consensus/base-rate matrix only |
| `unknown` | Business model cannot be verified | No Independent forecast |

Only `matched` may become the selected adapter or create adapter-specific acquisition
targets. `partial` remains visible as a candidate for research but cannot specialize
the company's Evidence Inventory.

## Segment Composition

Multi-business companies use segment-level adapters:

```text
Company forecast = sum(segment adapter forecasts) - corporate costs
```

Examples:

- Amazon: cloud/platform + retail + advertising.
- A diversified bank: lending + markets + wealth management.
- An integrated energy company: upstream + refining + chemicals.

No external theme may be applied to total company revenue when evidence only supports
one segment.

## External Transmission Gate

An industry, macro, or supply-chain trend can influence an Independent forecast only
when every required field is present:

```yaml
external_driver:
transmission_target:
direction:
lag_range_quarters:
evidence_refs:
conversion_method:
confidence:
```

Rules:

1. A trend without a verified company or segment exposure is qualitative only.
2. A relationship without a conversion method cannot change revenue numerically.
3. Lag ranges must be retained; license, production, and revenue recognition are not
   assumed to occur in the same quarter.
4. The same demand signal cannot be counted through multiple supply-chain paths.
5. Conflicting sources are surfaced, not silently resolved.

Example:

```text
Hyperscaler AI CapEx growth
-> ARM-based custom silicon project evidence
-> license/product launch
-> production volume
-> royalty-bearing units
-> ARM data-center royalty revenue
```

Missing any conversion step means the signal remains a catalyst, not a revenue input.

## Numeric Independent Lane Gate

An adapter may emit a numeric Independent forecast only when all conditions pass:

- required operating drivers are numeric;
- every operating driver has one or more evidence references;
- at least one external transmission path is `numeric_eligible`;
- the final forecast metric has a deterministic derivation evidence reference;
- the forecast metric can be compared on the same basis in the expectations matrix.

Supplying numbers without evidence references remains `insufficient_evidence`.

## Point-in-Time Evidence Inventory

The core engine builds an inventory with `forward_expectations_evidence.py` before the
selected adapter's final evaluation. Adapters may use accepted inventory evidence
references, but the inventory does not manufacture missing values.

`forward_expectations_primary_sources.py` may promote explicit primary-source driver
statements into the inventory. A promoted record can populate its directly observed
driver value and evidence reference. It cannot populate a derived forecast metric or
invent a transmission conversion.

`forward_expectations_source_discovery.py` is deliberately adapter-neutral. It finds
company website roots, SEC submission manifests, filing metadata, and transcripts for
any ticker, then leaves them provisional. Adapters define which metrics are useful
only after document content passes the primary-source promotion gate.

Nexus rules:

- `CO_THEME` is association only and always provisional.
- A causal relation must be an approved supply-chain type and independently
  corroborated.
- Even a corroborated causal relation remains non-numeric without a conversion method.
- Reports and narrative artifacts guide acquisition work; they do not auto-promote.

## Initial Adapter Pilots

| Adapter | Pilot | Core drivers | Unsupported default |
|---|---|---|---|
| `royalty_ip` | ARM | license conversion, royalty-bearing units, mix/rate | trailing FCF as sole value base |
| `bank` | JPM | loans, NIM, deposit cost, credit loss, fees, CET1 | corporate FCF reverse DCF |
| `retail_membership` | COST | stores, traffic, ticket, membership, margin | technology revenue CAGR model |

The architecture is considered cross-industry only after all three pilots can use the
same core evidence, ledger, matrix, and validation contracts.

## Valuation Mapping

Adapters declare supported and unsupported valuation methods. The core engine does
not select one universal method.

- `royalty_ip`: forward earnings/revenue and scenario range after drivers exist.
- `bank`: forward P/B, ROE, dividends, and excess capital.
- `retail_membership`: forward earnings and EV/EBITDA.

Full free-assumption forward DCF remains deferred until the Independent lane is
calibrated. Missing evidence must produce `insufficient_evidence`, not precise value.

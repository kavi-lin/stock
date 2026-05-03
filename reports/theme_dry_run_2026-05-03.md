# theme-detector dry-run: Finviz vs FMP (rolling 5d)

**Date**: 2026-05-03

## Coverage

- Finviz industries: **144**
- FMP industries:    **128**
- Matched (name normalized): **73**
- Only in Finviz: **71**
- Only in FMP:    **55**

## Drift summary (Finviz perf_1w − FMP rolling 5d, both %)

- Sample size: **73**
- Mean delta: **-4.096%**
- Std dev:    **37.425%**
- Industries with |drift| > 2%: **52** / 73

## Top 20 by absolute drift

| Industry | Finviz 1w % | FMP roll-5d % | Δ % |
|---|---:|---:|---:|
| Insurance - Life | +98.00 | -0.28 | +98.28 |
| Railroads | -99.00 | -1.35 | -97.65 |
| Software - Infrastructure | -95.00 | +2.61 | -97.61 |
| REIT - Specialty | +90.00 | +1.09 | +88.91 |
| Insurance - Diversified | +84.00 | -0.90 | +84.90 |
| Food Distribution | -77.00 | +6.70 | -83.70 |
| Conglomerates | -81.00 | +0.16 | -81.16 |
| Consulting Services | +80.00 | +0.69 | +79.31 |
| Electronic Gaming & Multimedia | -70.00 | +3.31 | -73.31 |
| Semiconductors | -67.00 | +2.05 | -69.05 |
| REIT - Industrial | -62.00 | +6.75 | -68.75 |
| Packaging & Containers | -67.00 | -0.49 | -66.51 |
| Discount Stores | +60.00 | -0.24 | +60.24 |
| Insurance - Property & Casualty | -57.00 | -0.24 | -56.76 |
| Rental & Leasing Services | -58.00 | -2.85 | -55.15 |
| Packaged Foods | -34.00 | +1.96 | -35.96 |
| Insurance - Reinsurance | -37.00 | -1.22 | -35.77 |
| Household & Personal Products | +33.00 | -1.24 | +34.24 |
| Leisure | -36.00 | -2.47 | -33.53 |
| Specialty Business Services | -30.00 | +1.38 | -31.38 |

## Bottom 10 (smallest drift = best agreement)

| Industry | Finviz 1w % | FMP roll-5d % | Δ % |
|---|---:|---:|---:|
| Shell Companies | +2.10 | +1.32 | +0.78 |
| Education & Training Services | +1.89 | +2.66 | -0.77 |
| Communication Equipment | +4.50 | +5.04 | -0.55 |
| Internet Content & Information | +5.44 | +4.91 | +0.53 |
| Steel | +2.46 | +2.98 | -0.52 |
| Insurance - Specialty | -3.57 | -3.15 | -0.42 |
| Biotechnology | -2.18 | -1.83 | -0.35 |
| REIT - Healthcare Facilities | +3.37 | +3.22 | +0.15 |
| Software - Application | +2.32 | +2.19 | +0.13 |
| Drug Manufacturers - Specialty & Generic | +1.73 | +1.86 | -0.13 |

## Industries only in Finviz (71)

- Airlines
- Airports & Air Services
- Aluminum
- Apparel Manufacturing
- Apparel Retail
- Asset Management
- Auto & Truck Dealerships
- Auto Manufacturers
- Auto Parts
- Banks - Diversified
- Beverages - Brewers
- Building Materials
- Building Products & Equipment
- Capital Markets
- Coking Coal
- Confectioners
- Copper
- Credit Services
- Department Stores
- Diagnostics & Research
- Electronic Components
- Electronics & Computer Distribution
- Farm & Heavy Construction Machinery
- Farm Products
- Financial Conglomerates
- Financial Data & Stock Exchanges
- Footwear & Accessories
- Gambling
- Health Information Services
- Healthcare Plans
- *(+41 more)*

## Industries only in FMP (55)

- Agricultural - Machinery
- Agricultural Farm Products
- Airlines, Airports & Air Services
- Apparel - Footwear & Accessories
- Apparel - Manufacturers
- Apparel - Retail
- Auto - Dealerships
- Auto - Manufacturers
- Auto - Parts
- Auto - Recreational Vehicles
- Banks
- Chemicals - Specialty
- Coal
- Construction
- Construction Materials
- Diversified Utilities
- Financial - Capital Markets
- Financial - Conglomerates
- Financial - Credit Services
- Financial - Data & Stock Exchanges
- Financial - Mortgages
- Gambling, Resorts & Casinos
- Hardware, Equipment & Parts
- Home Improvement
- Industrial - Distribution
- Industrial - Machinery
- Industrial - Pollution & Treatment Controls
- Industrial Materials
- Insurance - Brokers
- Investment - Banking & Investment Services
- *(+25 more)*

## Verdict

🔴 **RED** — < 70% coverage. Industries differ substantially. Migration not recommended without rework.

> ⚠️ NOTE: FMP rolling sum ≠ Finviz point-to-point pct. Some drift is methodological, not data-quality.
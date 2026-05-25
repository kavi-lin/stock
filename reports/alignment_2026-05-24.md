# Data Alignment Audit — 2026-05-24

> Threshold: 1.0% relative diff (price / PE / market_cap)
> Paths: A=`skills/market-top-detector/scripts/fmp_client.FMPClient.quote` · B=`requests.get /stable/quote`

## Summary

| Ticker | Status | Alerted Fields | Notes |
|---|---|---|---|
| NVDA | ✅ OK | — | both paths agree within 1.0% |
| AAPL | ✅ OK | — | both paths agree within 1.0% |
| MSFT | ✅ OK | — | both paths agree within 1.0% |

## Per-Ticker Detail

### NVDA — `OK`
| Field | A (FMPClient) | B (REST) | Diff |
|---|---|---|---|
| price | 215.33 | 215.33 | 0.00% |
| pe | None | None | n/a |
| market_cap | 5215507930000 | 5215507930000 | 0.00% |

### AAPL — `OK`
| Field | A (FMPClient) | B (REST) | Diff |
|---|---|---|---|
| price | 308.82 | 308.82 | 0.00% |
| pe | None | None | n/a |
| market_cap | 4535749279920 | 4535749279920 | 0.00% |

### MSFT — `OK`
| Field | A (FMPClient) | B (REST) | Diff |
|---|---|---|---|
| price | 418.57 | 418.57 | 0.00% |
| pe | None | None | n/a |
| market_cap | 3109317945100 | 3109317945100 | 0.00% |

---

**Soft-fail policy**: rc=0 always. Acceptance is reported, not enforced. Treat ALERTs as investigation triggers, not blockers.
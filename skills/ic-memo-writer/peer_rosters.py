"""Local peer rosters for ic-memo-writer.

These overrides are intentionally skill-local. Shared FMP peers remain the
fallback for tickers without a curated roster.
"""

from __future__ import annotations

PEER_ROSTERS = {
    "MU": [
        {"ticker": "WDC", "name": "Western Digital", "role": "NAND / storage competitor"},
        {"ticker": "STX", "name": "Seagate", "role": "storage demand read-through"},
        {"ticker": None, "name": "Samsung Electronics", "role": "DRAM / NAND / HBM competitor (KRX 005930)"},
        {"ticker": None, "name": "SK Hynix", "role": "DRAM / HBM competitor (KRX 000660)"},
    ],
    "NVDA": [
        {"ticker": "AMD", "name": "AMD", "role": "GPU / accelerator competitor"},
        {"ticker": "AVGO", "name": "Broadcom", "role": "AI custom silicon / networking"},
        {"ticker": "INTC", "name": "Intel", "role": "CPU + Gaudi accelerator"},
    ],
    "AMD": [
        {"ticker": "NVDA", "name": "Nvidia", "role": "GPU / AI accelerator leader"},
        {"ticker": "INTC", "name": "Intel", "role": "x86 CPU competitor"},
        {"ticker": "AVGO", "name": "Broadcom", "role": "AI custom silicon"},
    ],
    "INTC": [
        {"ticker": "AMD", "name": "AMD", "role": "x86 CPU competitor"},
        {"ticker": "NVDA", "name": "Nvidia", "role": "GPU / DC AI leader"},
        {"ticker": "TSM", "name": "TSMC", "role": "foundry rival"},
    ],
    "TSM": [
        {"ticker": "INTC", "name": "Intel Foundry", "role": "foundry competitor (IFS)"},
        {"ticker": "UMC", "name": "UMC", "role": "mature-node foundry"},
        {"ticker": None, "name": "Samsung Foundry", "role": "leading-edge foundry (KRX 005930)"},
    ],
}


def get_peer_roster(ticker: str) -> list[dict] | None:
    return PEER_ROSTERS.get(ticker.upper())

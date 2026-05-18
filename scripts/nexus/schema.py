"""Node / edge dataclasses + enums for Project Nexus knowledge graph."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    TICKER = "ticker"
    THEME = "theme"
    CATALYST = "catalyst"
    SECTOR = "sector"
    NARRATIVE = "narrative"
    THESIS = "thesis"
    STRUCTURAL_SHIFT = "structural_shift"


class EdgeType(str, Enum):
    MENTIONED_IN = "MENTIONED_IN"
    BELONGS_TO_THEME = "BELONGS_TO_THEME"
    BELONGS_TO_SECTOR = "BELONGS_TO_SECTOR"
    BELONGS_TO_NARRATIVE = "BELONGS_TO_NARRATIVE"   # Tier 2 default
    CATALYST_FOR = "CATALYST_FOR"
    PEER_OF = "PEER_OF"
    BULL_CASE_FOR = "BULL_CASE_FOR"
    BEAR_CASE_FOR = "BEAR_CASE_FOR"
    OUTCOME_FOR = "OUTCOME_FOR"
    SUPPLY_CHAIN_HOP = "SUPPLY_CHAIN_HOP"
    # ─── Tier 3 LLM-only directional supply-chain edges ────────────────
    SUPPLIES_TO       = "SUPPLIES_TO"           # A's product is input to B
    CUSTOMER_OF       = "CUSTOMER_OF"           # A buys from B
    CONTRACT_MFG_FOR  = "CONTRACT_MFG_FOR"      # A manufactures for B (pharma CDMOs)
    COMPETES_WITH     = "COMPETES_WITH"         # peer in same vertical
    CO_DEVELOPS_WITH  = "CO_DEVELOPS_WITH"      # joint program / partnership
    BENEFITS_FROM     = "BENEFITS_FROM"         # narrative tailwind
    HEADWIND_FROM     = "HEADWIND_FROM"         # narrative pressure


EDGE_TO_DECAY_KEY = {
    EdgeType.MENTIONED_IN: "mentioned_in",
    EdgeType.BELONGS_TO_THEME: "belongs_to_theme",
    EdgeType.BELONGS_TO_SECTOR: "belongs_to_sector",
    EdgeType.BELONGS_TO_NARRATIVE: "narrative",
    EdgeType.CATALYST_FOR: "catalyst",
    EdgeType.PEER_OF: "peer_of",
    EdgeType.BULL_CASE_FOR: "bull_case_for",
    EdgeType.BEAR_CASE_FOR: "bear_case_for",
    EdgeType.OUTCOME_FOR: "outcome_for",
    EdgeType.SUPPLY_CHAIN_HOP: "supply_chain_hop",
    # Tier 3 directional edges — supply chain longer half-life (industrial)
    EdgeType.SUPPLIES_TO:      "supply_chain_hop",
    EdgeType.CUSTOMER_OF:      "supply_chain_hop",
    EdgeType.CONTRACT_MFG_FOR: "supply_chain_hop",
    EdgeType.COMPETES_WITH:    "peer_of",
    EdgeType.CO_DEVELOPS_WITH: "peer_of",
    EdgeType.BENEFITS_FROM:    "narrative",
    EdgeType.HEADWIND_FROM:    "narrative",
}


@dataclass
class Node:
    id: str
    type: str
    label: str
    weight: float = 0.0
    pagerank: float = 0.0
    mentions: int = 0
    last_seen: str | None = None
    status: str = "promoted"
    sources: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["sources"] = sorted(self.sources)
        return d


@dataclass
class Edge:
    source: str
    target: str
    type: str
    weight: float = 0.0
    raw_frequency: float = 0.0
    tier: str = "tier1"
    confidence: float = 1.0
    last_seen: str | None = None
    sources: set[str] = field(default_factory=set)

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.source, self.target, self.type)

    def to_json(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "weight": round(self.weight, 6),
            "raw_frequency": round(self.raw_frequency, 4),
            "tier": self.tier,
            "confidence": self.confidence,
            "last_seen": self.last_seen,
            "sources": sorted(self.sources),
        }


def make_ticker_id(symbol: str) -> str:
    return f"ticker:{symbol.upper()}"


def make_theme_id(name: str) -> str:
    slug = "_".join(name.lower().split())
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    return f"theme:{slug}"


def make_sector_id(name: str) -> str:
    slug = "_".join(name.lower().split())
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    return f"sector:{slug}"


def make_narrative_id(label: str) -> str:
    slug = label.lower().strip()
    slug = "_".join(slug.split())
    slug = "".join(c for c in slug if c.isalnum() or c == "_" or c == "-")
    return f"narrative:{slug}"


def make_catalyst_id(label: str, date: str | None = None) -> str:
    slug = label.lower().strip()
    slug = "_".join(slug.split())
    slug = "".join(c for c in slug if c.isalnum() or c == "_" or c == "-")
    suffix = f"_{date}" if date else ""
    return f"catalyst:{slug}{suffix}"


def make_thesis_id(thesis_id: str) -> str:
    return f"thesis:{thesis_id}"

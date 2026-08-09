import json
from html.parser import HTMLParser
from pathlib import Path

from scripts.nexus import claim_ledger, topic_discovery


ROOT = Path(__file__).resolve().parents[1]


class _Ids(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "id" and value:
                self.ids.add(value)


def test_graph_radar_dom_and_script_contract():
    html = (ROOT / "Dashboard/graph.html").read_text(encoding="utf-8")
    script = (ROOT / "Dashboard/page-graph.js").read_text(encoding="utf-8")
    parser = _Ids()
    parser.feed(html)

    assert {"ng-radar", "ng-open-radar", "ng-detail", "ng-breadcrumb", "graph-host"} <= parser.ids
    assert "nexus_topics.json" in script
    assert "nexus_evidence_drafts.json" in script
    assert "nexus_gap_fills.json" in script
    assert "nexus_source_packets.json" in script
    assert "function renderRadar()" in script
    assert "function enterTopicFocus(topic)" in script
    assert "evidence_urls" in script
    assert "ng-source-link" in script
    assert "DRAFT_INDEX" in script
    assert "evidence drafts ready" in script
    assert "gap proposals ready" in script
    assert "GAP_INDEX" in script
    assert "SOURCE_PACKET_INDEX" in script
    assert "fetched excerpts ready" in script


def test_graph_visuals_follow_dashboard_theme():
    html = (ROOT / "Dashboard/graph.html").read_text(encoding="utf-8")
    script = (ROOT / "Dashboard/page-graph.js").read_text(encoding="utf-8")

    assert "[data-theme='light'] .ng-canvas" in html
    assert "[data-theme='light'] .ng-radar-shell" in html
    assert "[data-theme='light'] .ng-radar-card" in html
    assert "const LIGHT_EDGE_COLOR" in script
    assert "const isLight" in script
    assert "UI._onThemeChange" in script
    assert "GraphInst.refresh" in script


def test_generated_nexus_artifacts_clear_their_validators():
    claims = claim_ledger.read_jsonl(ROOT / "nexus/claim_ledger.jsonl")
    topics = json.loads((ROOT / "Dashboard/nexus_topics.json").read_text(encoding="utf-8"))
    graph = json.loads((ROOT / "Dashboard/nexus_graph.json").read_text(encoding="utf-8"))

    assert not claim_ledger.validate_records(claims)
    assert not topic_discovery.validate_payload(topics)
    assert graph["meta"]["claim_ledger"]["claims_corroborated"] > 0
    assert graph["meta"]["topic_discovery"]["chain_candidates"] > 0

    supply_edges = [edge for edge in graph["edges"] if edge["type"] == "SUPPLIES_TO"]
    assert supply_edges, "source-deduplicated supply edges must reach the graph projection"
    assert all(edge["metadata"].get("claim_id") for edge in supply_edges)
    assert all(edge["metadata"].get("evidence_urls") for edge in supply_edges)


def test_ticker_comention_noise_is_not_rendered_as_peer_of():
    graph = json.loads((ROOT / "Dashboard/nexus_graph.json").read_text(encoding="utf-8"))

    assert not [edge for edge in graph["edges"] if edge["type"] == "PEER_OF"]

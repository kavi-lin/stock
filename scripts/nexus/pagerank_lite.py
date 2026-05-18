"""Power Iteration PageRank — networkx-free fallback for Nexus graph."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable


def pagerank_lite(
    edges: Iterable[tuple[str, str, float]],
    alpha: float = 0.85,
    iters: int = 50,
    tol: float = 1e-4,
) -> dict[str, float]:
    """Edges: iterable of (src, dst, weight). Treats graph as undirected.

    Returns dict mapping node id -> pagerank score.
    """
    out_weight: dict[str, float] = defaultdict(float)
    adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
    nodes: set[str] = set()

    for src, dst, w in edges:
        if w <= 0:
            continue
        nodes.add(src)
        nodes.add(dst)
        adj[src].append((dst, w))
        adj[dst].append((src, w))
        out_weight[src] += w
        out_weight[dst] += w

    n = len(nodes)
    if n == 0:
        return {}

    base = (1.0 - alpha) / n
    rank = {node: 1.0 / n for node in nodes}

    for _ in range(iters):
        new = {node: base for node in nodes}
        for node in nodes:
            if out_weight[node] <= 0:
                share = rank[node] / n
                for other in nodes:
                    new[other] += alpha * share
                continue
            for neighbor, w in adj[node]:
                new[neighbor] += alpha * rank[node] * (w / out_weight[node])
        delta = sum(abs(new[node] - rank[node]) for node in nodes)
        rank = new
        if delta < tol:
            break

    total = sum(rank.values()) or 1.0
    return {node: r / total for node, r in rank.items()}


def degree_centrality(edges: Iterable[tuple[str, str, float]]) -> dict[str, float]:
    deg: dict[str, float] = defaultdict(float)
    nodes: set[str] = set()
    for src, dst, w in edges:
        if w <= 0:
            continue
        deg[src] += 1
        deg[dst] += 1
        nodes.add(src)
        nodes.add(dst)
    n = len(nodes)
    denom = max(n - 1, 1)
    return {node: deg[node] / denom for node in nodes}

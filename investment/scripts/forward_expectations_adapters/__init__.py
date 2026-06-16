"""Deterministic business-model adapter registry for Forward Expectations."""
from __future__ import annotations

from . import royalty_ip


ADAPTERS = (royalty_ip,)


def evaluate_adapters(ticker: str, earnings_cache: dict, explicit_input: dict | None = None) -> dict:
    """Select the highest-confidence deterministic adapter match."""
    candidates = [
        adapter.evaluate(ticker, earnings_cache, explicit_input or {})
        for adapter in ADAPTERS
    ]
    ranked = sorted(
        candidates,
        key=lambda item: (
            {"matched": 3, "partial": 2, "generic": 1, "unknown": 0}.get(item["match"]["status"], 0),
            item["match"].get("score", 0),
        ),
        reverse=True,
    )
    best = ranked[0] if ranked else None
    selected = best if best and best["match"]["status"] == "matched" else {
        "adapter_id": None,
        "adapter_version": None,
        "match": {"status": "unknown", "score": 0, "reasons": ["no_fully_matched_adapter"]},
        "independent_lane": {
            "available": False,
            "revenue_cagr": None,
            "reason": "no_matched_adapter",
        },
    }
    return {
        "selected_adapter": selected,
        "candidates": [
            {
                "adapter_id": item["adapter_id"],
                "match": item["match"],
            }
            for item in ranked
        ],
    }

"""Deterministic cache projection for reviewed News events."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def patch_news_caches(data: dict, root: Path) -> dict:
    deep = [
        v for v in (data.get("verdicts") or [])
        if v.get("depth") == "deep" and v.get("review_status") == "reviewed"
    ]
    phase0_path = root / "sector/sector_logs/phase0.json"
    phase0 = _load(phase0_path)
    ledger = phase0.get("applied_news_event_ids") or []
    if not isinstance(ledger, list):
        ledger = []
    seen = {str(x) for x in ledger}
    newly_applied = [v for v in deep if str(v.get("event_id") or "") not in seen]

    intel_files = sorted((root / "sector/sector_logs").glob("*_sector_intel.json"))
    if not intel_files:
        raise ValueError("no sector_intel.json available for cache projection")
    intel_path = intel_files[-1]
    if newly_applied:
        applied_ids = {v["event_id"] for v in newly_applied}
        intel = _load(intel_path)
        old = [x for x in (intel.get("top_catalysts") or []) if isinstance(x, dict)]
        old = [x for x in old if x.get("event_id") not in applied_ids]
        new = []
        for verdict in newly_applied:
            sectors = verdict.get("affected_sectors") or []
            sector_names = [
                str(x.get("sector")) if isinstance(x, dict) else str(x)
                for x in sectors if x
            ]
            score = float(verdict.get("net_impact_score", 0) or 0)
            new.append({
                "rank": 0,
                "event_id": verdict["event_id"],
                "event": verdict.get("headline") or "",
                "type": verdict.get("news_type") or "sentiment",
                "impact_score": max(1, min(5, round(abs(score)))),
                "affected_sectors": sector_names,
                "direction": str(verdict.get("verdict") or "neutral").lower(),
                "timing": "within_48h" if verdict.get("within_48h") else "this_week",
                "source": "news_protocol_v2",
                "updated_at": data.get("timestamp"),
            })
        intel["top_catalysts"] = new + old
        for rank, row in enumerate(intel["top_catalysts"], 1):
            row["rank"] = rank
        _atomic(intel_path, intel)

        delta = sum(float(v.get("macro_backdrop_delta", 0) or 0) for v in newly_applied)
        phase0["macro_backdrop_score"] = round(float(phase0.get("macro_backdrop_score", 0) or 0) + delta, 2)
        phase0["news_patch_count"] = int(phase0.get("news_patch_count", 0) or 0) + len(newly_applied)
        phase0["last_news_update"] = data.get("timestamp")
        projection_date = data.get("projection_date") or str(data.get("timestamp"))[:10]
        phase0["last_news_digest"] = f"news/news_logs/{projection_date}_digest.json"
        risks = phase0.get("binary_risks") or []
        if not isinstance(risks, list):
            risks = []
        risk_ids = {x.get("event_id") for x in risks if isinstance(x, dict)}
        for verdict in newly_applied:
            if verdict.get("binary_risk") and verdict["event_id"] not in risk_ids:
                risks.append({
                    "event_id": verdict["event_id"],
                    "event": verdict.get("headline") or "",
                    "event_date": verdict.get("binary_event_date"),
                    "within_48h": bool(verdict.get("within_48h")),
                    "directional_bias": verdict.get("directional_bias"),
                    "source": "news_protocol_v2",
                })
        phase0["binary_risks"] = risks
        phase0["applied_news_event_ids"] = (ledger + [v["event_id"] for v in newly_applied])[-500:]
        _atomic(phase0_path, phase0)
    return {"sector_intel": str(intel_path), "phase0": str(phase0_path), "new_events": len(newly_applied)}

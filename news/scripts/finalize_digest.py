#!/usr/bin/env python3
"""Deterministically finalize a News V2.3 DIGEST from compact debate JSON.

The LLM produces only four lane payloads, translations, and small Arbiter
metadata. This script owns arithmetic, verdict semantics, digest assembly,
Markdown rendering, validator sequencing, and idempotent cache patching.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from news.arbiter_rules import (
    ARBITER_RULE_VERSION,
    LANES,
    classify_verdict,
    compute_net_impact,
    directional_bias,
)
from news.scripts.build_digest_packet import build_packet
from news.scripts.news_event_store import (
    ingest_digest,
    load_events,
    migrate_digest,
    stable_event_id,
)
from news.scripts.news_cache_projection import patch_news_caches

VALID_FANOUT = {"PER_AGENT_BATCH", "PARTIAL_FALLBACK", "FULL_FALLBACK"}
VALID_DIRECTIONS = {"bullish", "bearish", "binary", "neutral"}


class DebateInputError(ValueError):
    pass


def _load_object(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DebateInputError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DebateInputError(f"expected JSON object in {path}")
    return data


def _atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _finite_score(value, lane: str, news_id: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DebateInputError(f"{news_id} {lane}.impact_score must be numeric")
    score = float(value)
    bounds = {"bull": (1, 5), "bear": (-5, -1), "sector": (-5, 5), "macro": (-5, 5)}
    lo, hi = bounds[lane]
    if not math.isfinite(score) or not lo <= score <= hi:
        raise DebateInputError(f"{news_id} {lane}.impact_score must be within {lo}..{hi}")
    return score


def _confidence(value, lane: str, news_id: str, low_credibility: bool) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DebateInputError(f"{news_id} {lane}.confidence must be numeric")
    confidence = float(value)
    if not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise DebateInputError(f"{news_id} {lane}.confidence must be within 0..1")
    if low_credibility and confidence > 0.5:
        raise DebateInputError(f"{news_id} {lane}.confidence exceeds LOW-source cap 0.5")
    return confidence


def _lane_item(debate: dict, lane: str, news_id: str) -> dict:
    lane_data = (debate.get("lanes") or {}).get(lane)
    if not isinstance(lane_data, dict):
        raise DebateInputError(f"missing lanes.{lane}")
    per_item = lane_data.get("per_item")
    item = per_item.get(news_id) if isinstance(per_item, dict) else None
    if not isinstance(item, dict):
        raise DebateInputError(f"missing lanes.{lane}.per_item.{news_id}")
    return item


def _translation(debate: dict, item: dict) -> str:
    news_id = item.get("news_id")
    translated = (debate.get("translations") or {}).get(news_id)
    translated = translated or item.get("headline_zh")
    if not isinstance(translated, str) or not translated.strip():
        raise DebateInputError(f"missing translations.{news_id}")
    return translated.strip()


def _sector_payload(item: dict) -> tuple[str, list[dict], list[str]]:
    primary = item.get("primary_sectors") or []
    affected = []
    labels = []
    for row in primary:
        if not isinstance(row, dict) or not str(row.get("sector") or "").strip():
            continue
        direction = str(row.get("direction") or "neutral").lower()
        if direction not in VALID_DIRECTIONS:
            direction = "neutral"
        sector = str(row["sector"]).strip()
        magnitude = str(row.get("magnitude") or "moderate")
        affected.append({"sector": sector, "direction": direction})
        labels.append(f"{sector} {direction}/{magnitude}")
    if not affected:
        affected = [{"sector": "Broad Market", "direction": "neutral"}]
        labels = ["Broad Market neutral"]
    supply = str(item.get("supply_chain_impact") or "No material second-order impact identified.").strip()
    text = "; ".join(labels) + f"；供應鏈：{supply}"
    tickers = item.get("tickers_mentioned")
    if not isinstance(tickers, list):
        raise DebateInputError("sector.tickers_mentioned must be an array")
    return text, affected, [str(x).upper() for x in tickers if str(x).strip()]


def _macro_text(item: dict) -> str:
    parts = []
    for key, label in (
        ("fed_path_delta", "Fed"), ("yield_curve_impact", "Yield curve"),
        ("fx_commodity_impact", "FX/commodity"), ("historical_analogue", "Analogue"),
    ):
        value = item.get(key)
        if value not in (None, ""):
            parts.append(f"{label}: {value}")
    return "；".join(parts) or "No material macro-path change identified."


def _event_id(item: dict) -> str:
    """Stable across reruns, triage rank changes, and repeated-day ingestion."""
    return stable_event_id(item)


def assemble_digest(date: str, debate: dict, root: Path = ROOT, now: str | None = None) -> dict:
    packet = build_packet(date, root)
    stage2 = packet["stage2_items"]
    if not stage2:
        raise DebateInputError("packet has no stage2_items; DIGEST should stop without LLM debate")

    fanout = debate.get("fanout_mode")
    if fanout not in VALID_FANOUT:
        raise DebateInputError(f"fanout_mode must be one of {sorted(VALID_FANOUT)}")
    degraded = debate.get("degraded_agents") or []
    if not isinstance(degraded, list):
        raise DebateInputError("degraded_agents must be an array")
    degraded_lanes = {
        str(name).lower().replace("_analyst", "").replace(" analyst", "").strip()
        for name in degraded
    }
    if not degraded_lanes <= set(LANES):
        raise DebateInputError(f"degraded_agents contains unknown lanes: {sorted(degraded_lanes - set(LANES))}")
    if fanout == "PER_AGENT_BATCH" and degraded_lanes:
        raise DebateInputError("PER_AGENT_BATCH requires degraded_agents=[]")
    if fanout == "PARTIAL_FALLBACK" and not 1 <= len(degraded_lanes) <= 2:
        raise DebateInputError("PARTIAL_FALLBACK requires 1-2 degraded_agents")
    if fanout == "FULL_FALLBACK" and len(degraded_lanes) < 3:
        raise DebateInputError("FULL_FALLBACK requires 3-4 degraded_agents")
    lane_flags = {
        lane: (
            isinstance((debate.get("lanes") or {}).get(lane), dict)
            and debate["lanes"][lane].get("subagent_isolated") is True
        )
        for lane in LANES
    }
    isolated = all(lane_flags.values())
    if fanout == "PER_AGENT_BATCH" and not isolated:
        raise DebateInputError("PER_AGENT_BATCH requires all four subagent_isolated=true")
    if fanout == "PARTIAL_FALLBACK" and any(
        lane_flags[lane] == (lane in degraded_lanes) for lane in LANES
    ):
        raise DebateInputError("PARTIAL_FALLBACK isolation flags must match degraded_agents")
    if fanout == "FULL_FALLBACK" and any(lane_flags.values()):
        raise DebateInputError("FULL_FALLBACK requires all four subagent_isolated=false")

    arbiter_items = ((debate.get("arbiter") or {}).get("per_item") or {})
    if not isinstance(arbiter_items, dict):
        raise DebateInputError("arbiter.per_item must be an object")
    deep = []
    demoted = []
    macro_deltas = []
    expected_ids = {item.get("news_id") for item in stage2}
    for item in stage2:
        news_id = item["news_id"]
        lane_items = {lane: _lane_item(debate, lane, news_id) for lane in LANES}
        scores = {lane: _finite_score(lane_items[lane].get("impact_score"), lane, news_id) for lane in LANES}
        low_credibility = item.get("effective_credibility") == "LOW"
        confidences = {
            lane: _confidence(lane_items[lane].get("confidence"), lane, news_id, low_credibility)
            for lane in LANES
        }
        too_confident = [lane for lane in degraded_lanes if confidences[lane] > 0.5]
        if too_confident:
            raise DebateInputError(
                f"{news_id} degraded lane confidence exceeds 0.5: {sorted(too_confident)}"
            )
        for lane in ("bull", "bear"):
            if not str(lane_items[lane].get("interpretation") or "").strip():
                raise DebateInputError(f"{news_id} {lane}.interpretation must be non-empty")
        # Non-substantive debate → demote this one item to shallow rather than
        # kill the run. news_protocol_v2.md states the rule per item ("退回該
        # 則"); the fatal version meant a single immaterial headline that Stage 1
        # advanced discarded a finished four-lane debate (2026-08-14 n0376, a Fed
        # notice about one former bank employee). Laziness is still caught: both
        # interpretations are required above, and a debate where most items come
        # back flat fails at the majority guard after this loop.
        if abs(scores["bull"]) <= 1 and abs(scores["bear"]) <= 1:
            demoted.append(item)
            print(
                f"WARN: {news_id} demoted to shallow — Bull/Bear both have "
                "|impact|<=1; debate is not substantive",
                file=sys.stderr,
            )
            continue
        net, weights = compute_net_impact(
            scores,
            item.get("news_type"),
            item.get("effective_credibility") or item.get("source_credibility") or "MEDIUM",
            fanout,
        )

        meta = arbiter_items.get(news_id)
        if not isinstance(meta, dict):
            raise DebateInputError(f"missing arbiter.per_item.{news_id}")
        binary = bool(item.get("binary_flag")) or meta.get("binary_risk") is True
        event_date = meta.get("binary_event_date")
        if binary and not event_date:
            raise DebateInputError(f"{news_id} binary event requires binary_event_date")
        if binary and not (
            lane_items["bear"].get("binary_risk") is True
            and lane_items["macro"].get("binary_risk") is True
        ):
            raise DebateInputError(f"{news_id} binary event requires Bear and Macro binary_risk=true")
        verdict = classify_verdict(net, binary)
        sector_text, affected, tickers = _sector_payload(lane_items["sector"])
        macro_delta = meta.get("macro_backdrop_delta", 0.0)
        if isinstance(macro_delta, bool) or not isinstance(macro_delta, (int, float)) or not math.isfinite(float(macro_delta)):
            raise DebateInputError(f"{news_id} macro_backdrop_delta must be finite numeric")
        macro_delta = max(-1.0, min(1.0, float(macro_delta)))
        macro_deltas.append(macro_delta)
        spread = max(scores.values()) - min(scores.values())
        reasoning_note = str(meta.get("reasoning_note") or "").strip()
        calc = " + ".join(f"{scores[k]:g}×{weights[k]:.2f}" for k in LANES)
        reasoning = f"{calc} = {net:+.1f}；依 {ARBITER_RULE_VERSION} 裁定 {verdict}。"
        if reasoning_note:
            reasoning += reasoning_note
        debate_note = str(meta.get("debate_note") or f"lane score spread={spread:g}").strip()
        evidence = meta.get("evidence_urls") or []
        if not isinstance(evidence, list):
            raise DebateInputError(f"{news_id} evidence_urls must be an array")

        deep.append({
            "news_id": news_id,
            "event_id": _event_id(item),
            "depth": "deep", "review_status": "reviewed",
            "headline": item.get("headline") or "", "headline_zh": _translation(debate, item),
            "source_label": item.get("source") or "Unknown", "source_url": item.get("url") or "",
            "published": item.get("published") or "", "news_type": item.get("news_type") or "sentiment",
            "content_genre": item.get("content_genre") or "unknown",
            "source_credibility": item.get("effective_credibility") or item.get("source_credibility") or "MEDIUM",
            "bull_case": str(lane_items["bull"].get("interpretation") or "").strip(),
            "bear_case": str(lane_items["bear"].get("interpretation") or "").strip(),
            "sector_view": sector_text, "macro_view": _macro_text(lane_items["macro"]),
            "verdict": verdict, "directional_bias": directional_bias(net),
            "net_impact_score": net, "weights_used": weights, "lane_scores": scores,
            "lane_confidences": confidences,
            "arbiter_reasoning": reasoning, "debate_note": debate_note,
            "binary_risk": binary, "binary_event_date": event_date if binary else None,
            "within_48h": bool(meta.get("within_48h")), "cache_updated": True,
            "affected_sectors": affected, "tickers_mentioned": tickers,
            "subagent_isolated": isolated, "macro_backdrop_delta": macro_delta,
            "evidence_urls": [str(x) for x in evidence if str(x).strip()],
        })

    extra_ids = set(arbiter_items) - expected_ids
    if extra_ids:
        raise DebateInputError(f"arbiter contains unknown news_ids: {sorted(extra_ids)}")

    # One flat item is an immaterial news story; most of them flat is a debate
    # that never happened. The second case must not be able to buy a passing
    # digest by demoting its way to an empty deep section.
    if demoted and len(demoted) * 2 > len(stage2):
        raise DebateInputError(
            f"{len(demoted)}/{len(stage2)} stage2 items have Bull/Bear both |impact|<=1: "
            f"{[x['news_id'] for x in demoted]} — that is an absent debate, not an "
            "immaterial news day"
        )

    demoted_ids = {item["news_id"] for item in demoted}
    # Demoted items take slots from the shallow tail instead of being appended.
    # The projection caps shallow at 10 by materiality (news_event_store.
    # _cap_shallow), so appending an 11th row would silently drop whichever row
    # ranks last — and a demoted item cleared the Stage 2 materiality gate, so
    # it outranks the tail it would be cut against.
    shallow_pool = packet["shallow_items"]
    if demoted:
        shallow_pool = shallow_pool[: max(0, len(shallow_pool) - len(demoted))]
    shallow = []
    for item in shallow_pool + demoted:
        shallow.append({
            "news_id": item["news_id"], "event_id": _event_id(item),
            "depth": "shallow", "review_status": "reviewed",
            "headline": item.get("headline") or "", "headline_zh": _translation(debate, item),
            "source_label": item.get("source") or "Unknown", "source_url": item.get("url") or "",
            "published": item.get("published") or "", "news_type": item.get("news_type") or "sentiment",
            "content_genre": item.get("content_genre") or "unknown",
            "bull_case": item.get("bull_case") or "", "bear_case": item.get("bear_case") or "",
            "sector_view": item.get("sector_view") or "", "macro_view": item.get("macro_view") or "",
            "verdict": None, "directional_bias": None,
            "net_impact_score": item.get("shallow_score", 0.0),
            "materiality_score": item.get("materiality_score"),
            "arbiter_reasoning": None, "debate_note": None,
            "binary_risk": bool(item.get("binary_flag")), "binary_event_date": None,
            "within_48h": False, "cache_updated": False,
            "affected_sectors": [], "tickers_mentioned": [], "subagent_isolated": None,
            "demoted_from": ("stage2_non_substantive" if item["news_id"] in demoted_ids else None),
        })

    session_delta = max(-1.0, min(1.0, round(sum(macro_deltas), 2)))
    return {
        "timestamp": now or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "arbiter_rule_version": ARBITER_RULE_VERSION,
        "mode": "DIGEST", "stage1_count": packet["triage_stats"]["exported_shallow_count"],
        "stage2_count": len(deep), "fanout_mode": fanout,
        "degraded_agents": [str(x) for x in degraded],
        # Recorded, not just logged: a reader comparing stage2_items to the deep
        # section has to be able to see why an item is missing from it.
        "demoted_stage2": [item["news_id"] for item in demoted],
        "verdicts": deep + shallow, "session_macro_delta": session_delta,
    }


def render_markdown(data: dict) -> str:
    deep = [v for v in data["verdicts"] if v["depth"] == "deep"]
    shallow = [v for v in data["verdicts"] if v["depth"] == "shallow"]
    lines = [
        f"# News Digest — {data['timestamp'][:10]}", "",
        f"**Mode**: DIGEST ｜ **Generated**: {data['timestamp']} Asia/Taipei ｜ "
        f"**Stage 1**: {data['stage1_count']} ｜ **Stage 2**: {data['stage2_count']} ｜ "
        f"**Fan-out**: {data['fanout_mode']}", "",
    ]
    if data.get("demoted_stage2"):
        lines += [
            "> 降級為 shallow（Bull/Bear 皆 |impact| ≤ 1，無實質辯論）："
            + "、".join(data["demoted_stage2"]),
            "",
        ]
    lines += ["## Deep Analysis", ""]
    for v in deep:
        lines += [
            f"### [{v['verdict']} {v['net_impact_score']:+.1f}] {v['news_id']} — {v['headline_zh']}",
            f"- **Published**: {v['published']} ｜ **Type**: {v['news_type']}",
            f"- **Bull {v['lane_scores']['bull']:+g}**: {v['bull_case']}",
            f"- **Bear {v['lane_scores']['bear']:+g}**: {v['bear_case']}",
            f"- **Sector {v['lane_scores']['sector']:+g}**: {v['sector_view']}",
            f"- **Macro {v['lane_scores']['macro']:+g}**: {v['macro_view']}",
            f"- **Arbiter**: {v['arbiter_reasoning']}",
            f"- **Debate**: {v['debate_note']}",
        ]
        if v["evidence_urls"]:
            lines.append("- **Evidence**: " + ", ".join(v["evidence_urls"]))
        lines.append("")
    lines += ["## Shallow Digest", ""]
    for v in shallow:
        lines += [
            f"### [{v['net_impact_score']:+.1f} / M={v.get('materiality_score')}] {v['news_id']} — {v['headline_zh']}",
            f"- **Bull**: {v['bull_case']} ｜ **Bear**: {v['bear_case']}",
            f"- **Sector**: {v['sector_view']} ｜ **Macro**: {v['macro_view']}",
            f"- Source: {v['source_label']} │ type: {v['news_type']} │ published: {v['published']}", "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def finalize(
    date: str,
    debate_path: Path,
    root: Path = ROOT,
    now: str | None = None,
    validate: bool = True,
    patch_caches: bool = True,
) -> dict:
    debate = _load_object(debate_path)
    data = assemble_digest(date, debate, root=root, now=now)
    digest_path = root / f"news/news_logs/{date}_digest.json"
    report_path = root / f"reports/{date}_news_digest.md"
    store_path = root / "news/news_logs/news_events.jsonl"
    if digest_path.exists() and not any(
        event.get("effective_date") == date for event in load_events(store_path)
    ):
        migrate_digest(digest_path, root=root, store_path=store_path, backup=True)
    event_result = ingest_digest(data, date=date, root=root, store_path=store_path)
    data = event_result["projection"]

    if validate:
        result = subprocess.run(
            [sys.executable, str(ROOT / "news/scripts/validate_digest_output.py"), "--path", str(digest_path)],
            cwd=root, capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            raise DebateInputError((result.stderr or result.stdout or "validator failed").strip())
    cache_result = patch_news_caches(data, root) if patch_caches else {"new_events": 0}
    _atomic_text(report_path, render_markdown(data))
    return {
        "digest": str(digest_path), "report": str(report_path),
        "events": {"store": event_result["store"], "appended": event_result["appended"]},
        "cache": cache_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--debate", help="compact debate JSON; defaults to <DATE>_debate.json")
    parser.add_argument("--no-cache-patch", action="store_true", help="test/debug only")
    args = parser.parse_args()
    debate_path = Path(args.debate) if args.debate else ROOT / f"news/news_logs/{args.date}_debate.json"
    if not debate_path.is_absolute():
        debate_path = ROOT / debate_path
    try:
        result = finalize(
            args.date, debate_path, patch_caches=not args.no_cache_patch,
        )
    except (DebateInputError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

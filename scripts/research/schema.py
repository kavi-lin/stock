"""Bounded claims with verified source excerpts, not model confidence votes."""
from __future__ import annotations

import re

from scripts.research.store import parse_time

KINDS = {"fact", "inference", "question"}
DIRECTIONS = {"bullish", "bearish", "mixed", "neutral"}
STATUSES = {"supported", "contested", "insufficient", "retracted"}


def output_schema(evidence, analysis=None, tickers=()):
    """Constrain citations at generation time to exact source spans."""
    def obj(properties):
        return {"type": "object", "properties": properties,
                "required": list(properties), "additionalProperties": False}
    string = {"type": "string"}
    citations = []
    for item in evidence:
        spans = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", item["text"]) if s.strip()]
        spans = list(dict.fromkeys(s[:480] for s in spans))[:10]
        citations.append(obj({"evidence_id": {"type":"string", "enum":[item["id"]]},
                              "quote": {"type":"string", "enum":spans}}))
    refs = {"type":"array", "items":{"anyOf":citations}, "maxItems":4}
    if analysis is not None:
        return obj({"assessments":{"type":"array", "items":obj({
            "claim_id":{"type":"string", "enum":[c["id"] for c in analysis["claims"]]},
            "status":{"type":"string", "enum":sorted(STATUSES)},
            "reason":string, "evidence_refs":refs}), "minItems":len(analysis["claims"]),
            "maxItems":len(analysis["claims"])}})
    return obj({"claims":{"type":"array", "minItems":1,"maxItems":5,"items":obj({
        "id":string,"text":string,"kind":{"type":"string","enum":sorted(KINDS)},
        "direction":{"type":"string","enum":sorted(DIRECTIONS)},
        # The native structured-output service rejects maxItems=0. An empty
        # universe is enforced by validate_analysis's subset gate instead.
        "tickers":{"type":"array","items":{"type":"string", **({"enum":list(tickers)} if tickers else {})},"maxItems":8},
        "horizon":string,"evidence_refs":refs,"falsifier":string,
        "followup":obj({"due_at":{"type":["string","null"]},"condition":string})})}})


def text(value, field, limit=1200):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"invalid {field}")


def references(refs, evidence, required=False):
    if not isinstance(refs, list) or len(refs) > 4 or (required and not refs):
        raise ValueError("invalid evidence references")
    by_id = {e["id"]: e for e in evidence}
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {"evidence_id", "quote"}:
            raise ValueError("invalid citation structure")
        item = by_id.get(ref["evidence_id"])
        quote = ref["quote"]
        text(quote, "quote", 500)
        if not item or " ".join(quote.split()) not in " ".join(item["text"].split()):
            raise ValueError("citation is not present in the supplied source")


def validate_analysis(payload, evidence, allowed_tickers=None):
    if not isinstance(payload, dict) or set(payload) != {"claims"}:
        raise ValueError("analysis must contain claims only")
    claims = payload["claims"]
    if not isinstance(claims, list) or not 1 <= len(claims) <= 5:
        raise ValueError("one to five claims required")
    ids = set()
    for claim in claims:
        required = {"id", "text", "kind", "direction", "tickers", "horizon",
                    "evidence_refs", "falsifier", "followup"}
        if not isinstance(claim, dict) or set(claim) != required:
            raise ValueError("claim fields do not match schema")
        text(claim["id"], "id", 40)
        if claim["id"] in ids:
            raise ValueError("duplicate claim id")
        ids.add(claim["id"])
        text(claim["text"], "claim")
        if claim["kind"] not in KINDS or claim["direction"] not in DIRECTIONS:
            raise ValueError("invalid kind/direction")
        if not isinstance(claim["tickers"], list) or len(claim["tickers"]) > 8:
            raise ValueError("invalid tickers")
        if any(not isinstance(t, str) or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", t)
               for t in claim["tickers"]):
            raise ValueError("invalid ticker")
        if allowed_tickers is not None and set(claim["tickers"]) - set(allowed_tickers):
            raise ValueError("ticker was not identified in the source packet")
        text(claim["horizon"], "horizon", 160)
        text(claim["falsifier"], "falsifier", 500)
        references(claim["evidence_refs"], evidence, required=claim["kind"] == "fact")
        followup = claim["followup"]
        if not isinstance(followup, dict) or set(followup) != {"due_at", "condition"}:
            raise ValueError("invalid followup")
        if followup["due_at"] is not None and parse_time(followup["due_at"]) is None:
            raise ValueError("invalid followup timestamp")
        text(followup["condition"], "followup condition", 500)


def validate_challenge(payload, analysis, evidence):
    if not isinstance(payload, dict) or set(payload) != {"assessments"}:
        raise ValueError("challenge must contain assessments only")
    rows = payload["assessments"]
    if not isinstance(rows, list) or len(rows) != len(analysis["claims"]):
        raise ValueError("challenge must assess every claim exactly once")
    expected = {c["id"] for c in analysis["claims"]}
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"claim_id", "status", "reason", "evidence_refs"}:
            raise ValueError("invalid assessment fields")
        if row["claim_id"] not in expected or row["claim_id"] in seen or row["status"] not in STATUSES:
            raise ValueError("invalid assessment identity/status")
        seen.add(row["claim_id"])
        text(row["reason"], "challenge reason")
        references(row["evidence_refs"], evidence, required=row["status"] == "supported")

"""Prompt templates for the Claude / Gemini break-news debate."""
from __future__ import annotations

import json
from typing import Iterable

PREDICATES = ("BENEFITS_FROM, HEADWIND_FROM, COMPETES_WITH, SUPPLIES_TO, "
              "CUSTOMER_OF, CO_DEVELOPS_WITH, MENTIONED_IN, CATALYST_FOR")

SYSTEM_PROMPT = f"""You are an equity analyst opening the discussion on one
breaking news item. You speak FIRST: a second analyst (a different model) will
read your take and answer it point by point, so state each point in a form that
can be agreed with or disputed — specific, attributable, no hedging both ways
inside one bullet.

Reply with a SINGLE fenced ```json``` block, no prose outside. Schema:
{{
  "commentary": str,       // 繁體中文(台灣) 80-150 字，市場/產業/個股影響。專有名詞 (NVDA, HBM3e) 保留英文
  "bull_points": [str],    // 利多論點 1-3 條，每條 ≤30 字繁中，獨立可讀（不可寫「見 commentary」）
  "bear_points": [str],    // 利空/風險 1-3 條，同格式。整體偏空仍要給 ≥1 條 bull_points，反之亦然
  "final_take": str,       // 一句話結論，繁中 ≤30 字，例「看多但需觀察Q2訂單兌現」
  "entities": {{
    "tickers": [str],      // US-listed root tickers, UPPERCASE English
    "sectors": [str],      // GICS-style sector names, English
    "themes": [str],       // English keys: "AI capex", "GLP-1", "HBM3e"
    "tech_keywords": [str] // English tech-nodes: HBM3e, N3P, CoWoS-L, Blackwell
  }},
  "relations": [{{"subject": "ticker:NVDA", "predicate": "BENEFITS_FROM", "object": "narrative:hbm3e"}}],
  "done": false,
  "confidence": float 0-1,
  "rationale_short": str   // 繁中 ≤40 字
}}
Rules: 中文欄位必須繁體中文(台灣)；`entities` 與 `relations` 內容維持英文 —
它們是 knowledge graph canonical ID，混入中文會破壞 dedup。
Do not add fields outside the schema. Relation subject/object IDs must use a
whitespace-free canonical `namespace:id` form.
Predicates must be one of: {PREDICATES}.
"""

RESPONDER_SYSTEM_PROMPT = f"""You are the SECOND analyst in an equity-news
debate. The first analyst's opening take is given to you in full. Your job is
NOT to write a second survey of the same news — it is to adjudicate theirs.

For EVERY bullet they raised, say whether you agree or dispute it, and why. A
dispute must carry a specific reason (second-order effect, a named supply-chain
node, contra-evidence, a wrong magnitude) — "too optimistic" is not a reason.
You are NOT required to be balanced: if their bull case is simply right, agree
with all of it. Add a point only when they MISSED something material.

Reply with a SINGLE fenced ```json``` block, no prose outside. Schema:
{{
  "commentary": str,       // 繁體中文(台灣) 80-150 字，你的整體判讀。專有名詞 (NVDA, HBM3e) 保留英文
  "assessments": [         // 對方每一條 bull/bear 都要有一則，1-6 則
    {{"point": "bull:0",   // 對方的第幾條，格式 bull:N / bear:N（N 從 0 起）
      "verdict": "agree" | "dispute",
      "reason": str}}      // 繁中 ≤40 字，具體理由；agree 也要寫為什麼站得住
  ],
  "added_bull": [str],     // 對方漏掉的利多 0-3 條，每條 ≤30 字繁中（沒有就給 []）
  "added_bear": [str],     // 對方漏掉的利空 0-3 條，同格式
  "final_take": str,       // 你的一句話結論，繁中 ≤30 字
  "entities": {{
    "tickers": [str],      // US-listed root tickers, UPPERCASE English
    "sectors": [str],      // GICS-style sector names, English
    "themes": [str],       // English keys: "AI capex", "GLP-1", "HBM3e"
    "tech_keywords": [str] // English tech-nodes: HBM3e, N3P, CoWoS-L, Blackwell
  }},
  "relations": [{{"subject": "ticker:NVDA", "predicate": "BENEFITS_FROM", "object": "narrative:hbm3e"}}],
  "done": bool,            // true = 你全部 agree、也無新論點
  "confidence": float 0-1,
  "rationale_short": str   // 繁中 ≤40 字
}}
Rules: 中文欄位必須繁體中文(台灣)；`entities` 與 `relations` 內容維持英文 —
它們是 knowledge graph canonical ID，混入中文會破壞 dedup。
Do not add fields outside the schema. Relation subject/object IDs must use a
whitespace-free canonical `namespace:id` form — `narrative:uranium_supply_deficit`,
NOT `narrative:uranium supply deficit`.
Reuse the first analyst's `namespace:id` spelling for anything they already
named — inventing `theme:x` for their `narrative:x` hides a real disagreement.
Predicates must be one of: {PREDICATES}.
"""

ARBITER_SYSTEM_PROMPT = f"""You are the THIRD analyst, brought in only because
the first two could not settle it: the second analyst disputed a point and the
first refused to concede. You see the whole exchange.

Rule on the CONTESTED point specifically — do not re-survey the news, and do not
split the difference to be diplomatic. `ruling` must name whose reading of the
contested point holds: `side_a`, `side_b`, or `split` (only when both are right
about different horizons or different entities — say which in the commentary).

Reply with a SINGLE fenced ```json``` block, no prose outside. Schema:
{{
  "commentary": str,       // 繁體中文(台灣) 80-150 字：爭點是什麼、你採信哪一方、依據
  "ruling": "side_a" | "side_b" | "split",
  "final_take": str,       // 裁決後的一句話結論，繁中 ≤30 字
  "relations": [],         // ONLY relations neither side stated; same format
  "done": true,
  "confidence": float 0-1, // 對這個裁決的信心
  "rationale_short": str   // 繁中 ≤40 字
}}
Do not add fields outside the schema. Relation subject/object IDs must use a
whitespace-free canonical `namespace:id` form.
Predicates must be one of: {PREDICATES}.
"""

REBUTTAL_SYSTEM_PROMPT = f"""You are in a focused rebuttal round of an equity-news
debate. You will see the exact divergence point and the opponent's stance. Either
CHALLENGE it with ONE new specific point (second-order effect, named supply-chain
node, contra-evidence) or CONCEDE if the opponent's view is stronger. Do NOT
restate prior points; do NOT re-extract entities (round 1 already did).

Reply with a SINGLE fenced ```json``` block, no prose outside. Schema:
{{
  "commentary": str,       // 繁體中文 ≤60 字，只寫新論點或讓步理由
  "stance": "challenge" | "concede",
  "relations": [],         // ONLY relations NOT already in the known list; same format
                           // {{"subject":"ticker:X","predicate":"...","object":"narrative:y"}}
  "done": bool,            // true = 無新實質論點，可收斂
  "confidence": float 0-1, // 對自己整體立場的信心
  "rationale_short": str   // 繁中 ≤20 字
}}
Do not add fields outside the schema. Relation subject/object IDs must use a
whitespace-free canonical `namespace:id` form.
Predicates must be one of: {PREDICATES}.
"""

BRIEF_SYSTEM_PROMPT = """You are a market strategist writing a short situational
brief (市場現況導讀) for a human investor, from aggregated break-news debate
output. You see verdict tallies, hot event clusters (echo_count = how many
independent pushes reported the same story), and top closed-debate conclusions.
Weigh clusters by echo_count x |score|; multi-source stories matter more than
single-push noise. Do NOT invent events not present in the input.

Reply with a SINGLE fenced ```json``` block, no prose outside. Schema:
{
  "regime": str,              // ≤12 字繁中標籤，例「風險偏好回升」「避險主導」
  "regime_confidence": float, // 0-1
  "brief_text": str,          // 繁體中文(台灣) 200-300 字導讀：當前市場敘事、主導力量、轉折觀察。專有名詞 (NVDA, FOMC) 保留英文
  "drivers": [str],           // 主導事件 2-5 條，每條 ≤30 字繁中
  "bull_pressure": [str],     // 多方力量 1-4 條，≤25 字
  "bear_pressure": [str],     // 空方力量 1-4 條，≤25 字
  "watch": [str]              // 後續觀察點 2-5 條，≤30 字
}
中文欄位必須繁體中文(台灣)。
"""


def brief_user_prompt(ctx: dict) -> str:
    """Compact context block for the market brief — pre-aggregated, the LLM
    only synthesizes prose. Keep it lean: top clusters + top debates only."""
    lines = [f"WINDOW: last {ctx.get('window_hours')}h",
             f"VERDICT TALLY: {json.dumps(ctx.get('verdict_tally') or {}, ensure_ascii=False)}",
             f"NEWS TYPE MIX: {json.dumps(ctx.get('news_type_mix') or {}, ensure_ascii=False)}",
             "", "HOT EVENT CLUSTERS (multi-source stories, by heat):"]
    for c in ctx.get("hot_clusters") or []:
        lines.append(
            f"- [{c.get('news_type')}] x{c.get('echo_count')} srcs={len(c.get('sources') or [])} "
            f"score={c.get('best_score')} tickers={','.join((c.get('tickers') or [])[:5]) or '-'} :: "
            f"{c.get('rep_headline')}")
    lines.append("")
    lines.append("TOP CLOSED DEBATES (by impact):")
    for d in ctx.get("top_debates") or []:
        take = (d.get("final_take") or "").strip()
        lines.append(
            f"- [{d.get('verdict')}] {d.get('headline')}"
            + (f" → {take}" if take else ""))
    lines.append("")
    lines.append("Write the situational brief JSON as specified in your system prompt.")
    return "\n".join(lines)


def _comment_label(c: dict, default: str = "?") -> str:
    """Return a string label for a thread comment. `agent_role_label` may be a
    `{en,zh}` dict (debater._role_for); fall back to `agent` (model name) when
    the label is missing or not a string."""
    label = c.get("agent_role_label")
    if isinstance(label, dict):
        label = label.get("en") or label.get("zh")
    if not isinstance(label, str) or not label:
        label = c.get("agent") or default
    return str(label)


def _latest_by_side(thread: list[dict]) -> dict[str, dict]:
    """Latest comment per side ('A' / 'B')."""
    out: dict[str, dict] = {}
    for c in thread:
        s = c.get("side")
        if s:
            out[s] = c
    return out


def _known_state_lines(thread: list[dict]) -> str:
    """One-line compact known entities + relations — dedup hint for rebuttal,
    so agents never re-list what round 1 already extracted."""
    tickers: set[str] = set()
    themes: set[str] = set()
    rel_keys: list[str] = []
    seen = set()
    for c in thread:
        parsed = c.get("parsed") or {}
        ent = parsed.get("entities") or {}
        tickers.update((t or "").upper() for t in (ent.get("tickers") or []) if t)
        themes.update(t for t in (ent.get("themes") or []) if t)
        for r in (parsed.get("relations") or []):
            if isinstance(r, dict) and r.get("subject") and r.get("predicate") and r.get("object"):
                k = f"{r['subject']} {r['predicate']} {r['object']}"
                if k not in seen:
                    seen.add(k)
                    rel_keys.append(k)
    return (f"KNOWN entities (do NOT re-extract): tickers={sorted(tickers)}; "
            f"themes={sorted(themes)}\n"
            f"KNOWN relations (do NOT repeat): {'; '.join(rel_keys) or '(none)'}")


def _role_text(role) -> str:
    """Accept either string or {'zh','en'} dict — render single line for prompt."""
    if isinstance(role, dict):
        return f"{role.get('en','')} / {role.get('zh','')}"
    return str(role)


def _escalation_block(item: dict) -> str:
    """Cluster-escalation context: prior conclusion of the same event cluster,
    so the follow-up debate argues only the increment (more sources / new
    details), not the whole story again."""
    cl = item.get("cluster") or {}
    prior = cl.get("prior_summary") or {}
    if not cl.get("escalated") or not prior:
        return ""
    return f"""
PRIOR DEBATE — SAME EVENT CLUSTER (echo x{cl.get('echo_count')}, {len(cl.get('sources') or [])} sources)
  prior_verdict    = {prior.get('consensus_verdict')}
  prior_final_take = {prior.get('final_take')}
This story keeps accumulating coverage. Do NOT re-litigate the prior round.
Focus ONLY on what is NEW or CHANGED: fresh details in this headline, the
significance of the growing coverage itself, second-order effects not yet
covered. If nothing material is new, say so and keep confidence near prior.
"""


def opener_user_prompt(item: dict, role) -> str:
    triage = item.get("triage") or {}
    src = item.get("source") or {}
    role = _role_text(role)
    return f"""You are {role}.
{_escalation_block(item)}

NEWS ITEM
---------
Headline : {item.get('headline')}
Source   : {src.get('name')} ({src.get('credibility')})
URL      : {src.get('url')}
Published: {src.get('published') or '(unknown)'}
Summary  : {item.get('raw_summary')}

Pre-triage signal (keyword classifier, not authoritative):
  news_type      = {triage.get('news_type')}
  shallow_score  = {triage.get('shallow_score')}
  binary_flag    = {triage.get('binary_flag')}
  bull_case_snap = {triage.get('bull_case')}
  bear_case_snap = {triage.get('bear_case')}

Give your take on market / sector / individual-stock implications. Identify the
tickers, sectors, themes, and specific tech-keywords (e.g. HBM3e, N3P, CoWoS-L,
GLP-1, Blackwell) that this news touches. Set `done: false` (this is the opening
round; the second analyst will answer each of your bullets in turn).

Respond with the single JSON block as specified in your system prompt.
"""


def _numbered_points(parsed: dict) -> str:
    """A's bullets as the exact `bull:N` / `bear:N` refs B must answer."""
    lines = []
    for kind in ("bull", "bear"):
        for idx, point in enumerate((parsed.get(f"{kind}_points") or [])[:3]):
            lines.append(f"  {kind}:{idx}  {str(point).strip()}")
    return "\n".join(lines) or "  (none)"


def responder_user_prompt(item: dict, opener: dict, role) -> str:
    """Side B's round-0 prompt — the whole opener, with every bullet addressable.

    Deliberately carries the news item too: B has to be able to check A's claims
    against the source, not only against A's framing of it.
    """
    triage = item.get("triage") or {}
    src = item.get("source") or {}
    role = _role_text(role)
    ent = opener.get("entities") or {}
    return f"""You are {role}.

NEWS ITEM
---------
Headline : {item.get('headline')}
Source   : {src.get('name')} ({src.get('credibility')})
URL      : {src.get('url')}
Published: {src.get('published') or '(unknown)'}
Summary  : {item.get('raw_summary')}

Pre-triage signal (keyword classifier, not authoritative):
  news_type      = {triage.get('news_type')}
  shallow_score  = {triage.get('shallow_score')}
  binary_flag    = {triage.get('binary_flag')}

FIRST ANALYST'S OPENING TAKE
----------------------------
commentary  : {(opener.get('commentary') or '').strip()}
final_take  : {opener.get('final_take')}
confidence  : {opener.get('confidence')}
their points (answer EVERY line by its ref):
{_numbered_points(opener)}
they named  : tickers={sorted((ent.get('tickers') or []))}; \
themes={sorted((ent.get('themes') or []))}

Adjudicate each of their points, add anything material they missed, and give
your own final_take. Respond with the single JSON block as specified in your
system prompt.
"""


def arbiter_user_prompt(item: dict, thread: list[dict], contested: str) -> str:
    """Tie-breaker prompt — the contested point plus both sides' own words."""
    latest = _latest_by_side(thread)
    opener = (latest.get("A") or {}).get("parsed") or {}
    response = (latest.get("B") or {}).get("parsed") or {}
    rebuttals = [c for c in thread if c.get("side") == "A" and (c.get("round") or 0) >= 1
                 and (c.get("parsed") or {})]
    reb = (rebuttals[-1].get("parsed") if rebuttals else {}) or {}
    return f"""You are the arbiter (Analyst-C).

NEWS: {item.get('headline')}
Summary: {item.get('raw_summary')}

{_known_state_lines(thread)}

CONTESTED POINT(S)
------------------
{contested or '(unspecified)'}

ANALYST-A opened with:
  points:
{_numbered_points(opener)}
  final_take = {opener.get('final_take')} (confidence {opener.get('confidence')})

ANALYST-B answered:
  {json.dumps(response.get('assessments') or [], ensure_ascii=False)}
  added_bull = {json.dumps(response.get('added_bull') or [], ensure_ascii=False)}
  added_bear = {json.dumps(response.get('added_bear') or [], ensure_ascii=False)}
  final_take = {response.get('final_take')} (confidence {response.get('confidence')})

ANALYST-A refused to concede:
  stance     = {reb.get('stance')}
  argument   = {(reb.get('commentary') or '').strip() or '(none recorded)'}

Rule on the contested point. Respond with the single JSON block as specified in
your system prompt.
"""


def _stance_block(parsed: dict, full: bool = False) -> str:
    """Compact one-line JSON of a side's stance. `full` adds bull/bear +
    commentary head (used for the opponent; own side only needs the take)."""
    out = {
        "final_take": parsed.get("final_take"),
        "confidence": parsed.get("confidence"),
        "stance": parsed.get("stance"),
    }
    if full:
        out["bull_points"] = parsed.get("bull_points")
        out["bear_points"] = parsed.get("bear_points")
        commentary = (parsed.get("commentary") or "").strip()
        if commentary:
            out["commentary"] = commentary[:120]
    out = {k: v for k, v in out.items() if v not in (None, [], "")}
    return json.dumps(out, ensure_ascii=False)


def rebuttal_user_prompt(item: dict, thread: list[dict], role, side: str,
                         divergence_note: str) -> str:
    """Slim round-2+ prompt: headline + known state + exact divergence point +
    both stances. No news body re-paste, no triage block, no full transcript."""
    role = _role_text(role)
    latest = _latest_by_side(thread)
    own = (latest.get(side) or {}).get("parsed") or {}
    opp_side = "B" if side == "A" else "A"
    opp = (latest.get(opp_side) or {}).get("parsed") or {}
    return f"""You are {role}.

NEWS: {item.get('headline')}

{_known_state_lines(thread)}

DIVERGENCE POINT: {divergence_note}

YOUR prior stance: {_stance_block(own)}
OPPONENT (Analyst-{opp_side}) stance: {_stance_block(opp, full=True)}

Challenge the opponent on the divergence point with ONE new specific argument,
or concede. If nothing substantive remains, set `done: true`.

Respond with the single JSON block as specified in your system prompt.
"""


import re as _re


def _tokenize_zh(s: str) -> set[str]:
    """Word-grain tokens for Jaccard dedup of bullet points.
    Splits on whitespace + punctuation; keeps zh chars as single-char tokens
    (繁中 short bullets benefit from char-level overlap)."""
    if not s:
        return set()
    cleaned = _re.sub(r"[，。、；：！？「」『』（）()【】\[\]—…\s]+", " ", s)
    toks = set()
    for word in cleaned.split():
        if _re.search(r"[一-鿿]", word):
            toks.update(word)  # char-level for zh
        else:
            toks.add(word.lower())
    return toks


def _rough_dedup(points: Iterable[str], threshold: float = 0.6) -> list[str]:
    """Merge near-duplicate bullets using Jaccard similarity over zh-aware tokens."""
    out: list[str] = []
    seen_keys: list[set[str]] = []
    for p in points:
        p = (p or "").strip()
        if not p:
            continue
        toks = _tokenize_zh(p)
        if not toks:
            continue
        dup = False
        for s in seen_keys:
            union = toks | s
            if not union:
                continue
            if len(toks & s) / len(union) >= threshold:
                dup = True
                break
        if dup:
            continue
        seen_keys.append(toks)
        out.append(p)
    return out


def build_summary_block(thread: list[dict]) -> dict:
    """Merge entities + relations + bull/bear bullets across the thread.
    Derives a consensus verdict and implements V4 summary aggregation."""
    tickers: set[str] = set()
    sectors: set[str] = set()
    themes: set[str] = set()
    techs: set[str] = set()

    # 關係聚合專用結構
    # key -> {subject, predicate, object, confidences: [], source_agents: set, source_rounds: set, evidence_candidates: []}
    rel_agg: dict[str, dict] = {}

    verdict_votes: dict[str, int] = {}
    bull_buf: list[str] = []
    bear_buf: list[str] = []
    final_takes_by_round = []
    point_assessments: list[dict] = []
    arbiter_ruling: dict | None = None

    for c in thread:
        rnd = c.get("round", 0)
        agent = _comment_label(c, default="Unknown")
        p = c.get("parsed") or {}

        # 收集 entities
        ent = p.get("entities") or {}
        tickers.update((t or "").upper() for t in (ent.get("tickers") or []) if t)
        sectors.update(s for s in (ent.get("sectors") or []) if s)
        themes.update(t for t in (ent.get("themes") or []) if t)
        techs.update(k for k in (ent.get("tech_keywords") or []) if k)

        # 收集 final_takes_by_round
        ft = p.get("final_take")
        if isinstance(ft, str) and ft.strip():
            final_takes_by_round.append({
                "round": rnd,
                "agent": agent,
                "final_take": ft.strip(),
                "confidence": p.get("confidence")
            })

        # 收集與聚合 relations
        conf = p.get("confidence")
        commentary = p.get("commentary") or p.get("rationale_short") or ""
        snippet = commentary.strip()[:200]

        for r in (p.get("relations") or []):
            if isinstance(r, dict) and r.get("subject") and r.get("predicate") and r.get("object"):
                k = f"{r.get('subject')}|{r.get('predicate')}|{r.get('object')}"
                if k not in rel_agg:
                    rel_agg[k] = {
                        "subject": r.get("subject"),
                        "predicate": r.get("predicate"),
                        "object": r.get("object"),
                        "confidences": [],
                        "source_agents": set(),
                        "source_rounds": set(),
                        "evidence_candidates": []  # list of (conf_val, round_idx, snippet_text)
                    }

                slot = rel_agg[k]
                slot["source_agents"].add(agent)
                slot["source_rounds"].add(rnd)

                conf_val = None
                if conf is not None:
                    try:
                        conf_val = float(conf)
                        slot["confidences"].append(conf_val)
                    except (ValueError, TypeError):
                        pass

                if snippet:
                    slot["evidence_candidates"].append((
                        conf_val if conf_val is not None else -1.0,  # 無 conf 時排最後
                        rnd,
                        snippet
                    ))

        # 共識投票
        for pred in (r.get("predicate") for r in (p.get("relations") or []) if isinstance(r, dict)):
            if pred == "BENEFITS_FROM":
                verdict_votes["BULLISH"] = verdict_votes.get("BULLISH", 0) + 1
            elif pred == "HEADWIND_FROM":
                verdict_votes["BEARISH"] = verdict_votes.get("BEARISH", 0) + 1

        bull_buf.extend(bp for bp in (p.get("bull_points") or []) if isinstance(bp, str))
        bear_buf.extend(bp for bp in (p.get("bear_points") or []) if isinstance(bp, str))
        # V4.132.0 — side B no longer restates a balanced pair; it contributes
        # only what A missed. Folded into the same buffers so the dedup and the
        # 6-item cap stay the single place those lists are shaped.
        bull_buf.extend(bp for bp in (p.get("added_bull") or []) if isinstance(bp, str))
        bear_buf.extend(bp for bp in (p.get("added_bear") or []) if isinstance(bp, str))

        for a in (p.get("assessments") or []):
            if isinstance(a, dict) and a.get("point"):
                point_assessments.append({
                    "point": a.get("point"),
                    "verdict": a.get("verdict"),
                    "reason": a.get("reason"),
                    "by": agent,
                })
        if p.get("ruling") in ("side_a", "side_b", "split"):
            arbiter_ruling = {"ruling": p.get("ruling"), "by": agent,
                              "confidence": p.get("confidence"),
                              "commentary": (p.get("commentary") or "").strip(),
                              "final_take": (ft.strip() if isinstance(ft, str) else None)}

    # 計算 consensus
    consensus = "NEUTRAL"
    if verdict_votes:
        consensus = max(verdict_votes, key=verdict_votes.get)
        if len(set(verdict_votes.values())) == 1 and len(verdict_votes) > 1:
            consensus = "SPLIT"

    # 挑選最高置信度的 final_take (tie-break 取較早 round)
    final_take = None
    final_take_by = None
    if final_takes_by_round:
        def get_ft_sort_key(x):
            c_val = x.get("confidence")
            try:
                c_val = float(c_val) if c_val is not None else 0.0
            except (ValueError, TypeError):
                c_val = 0.0
            r_val = int(x.get("round", 0))
            return (-c_val, r_val)
        best_ft = sorted(final_takes_by_round, key=get_ft_sort_key)[0]
        final_take = best_ft["final_take"]
        final_take_by = best_ft["agent"]

    # The arbiter only ever speaks on a point the first two could not settle, so
    # its take supersedes the confidence ranking — otherwise the losing side's
    # self-assessed confidence can outrank the ruling that was called to settle it.
    if arbiter_ruling and arbiter_ruling.get("final_take"):
        final_take = arbiter_ruling["final_take"]
        final_take_by = arbiter_ruling["by"]

    # 建立最終 merged_relations 物件陣列
    merged_relations = []
    for k, slot in rel_agg.items():
        # 計算置信度平均 (排除 confidence=null)
        confs = slot["confidences"]
        conf_avg = sum(confs) / len(confs) if confs else None

        # 擷取 evidence_snippets (最多 3 條，每條 ≤200 字，按置信度排序；無置信度時按最早 round 排序)
        def get_snippet_sort_key(x):
            return (-x[0], x[1])

        sorted_candidates = sorted(slot["evidence_candidates"], key=get_snippet_sort_key)
        seen_snippets = set()
        snippets = []
        for _, _, text in sorted_candidates:
            if text not in seen_snippets:
                seen_snippets.add(text)
                snippets.append(text)
                if len(snippets) >= 3:
                    break

        merged_relations.append({
            "subject": slot["subject"],
            "predicate": slot["predicate"],
            "object": slot["object"],
            "support_count": len(slot["source_agents"]),
            "confidence_avg": conf_avg,
            "source_agents": sorted(list(slot["source_agents"])),
            "source_rounds": sorted(list(slot["source_rounds"])),
            "evidence_snippets": snippets,
            "provisional": True
        })

    return {
        "consensus_verdict": consensus,
        "merged_entities": {
            "tickers": sorted(tickers),
            "sectors": sorted(sectors),
            "themes": sorted(themes),
            "tech_keywords": sorted(techs),
        },
        "merged_relations": merged_relations,
        "bull_summary": _rough_dedup(bull_buf)[:6],
        "bear_summary": _rough_dedup(bear_buf)[:6],
        "final_take":    final_take,
        "final_take_by": final_take_by,
        "final_takes_by_round": final_takes_by_round,
        "point_assessments": point_assessments,
        "arbiter_ruling": arbiter_ruling,
    }

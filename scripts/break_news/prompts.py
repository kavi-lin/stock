"""Prompt templates for the Claude / Gemini break-news debate."""
from __future__ import annotations

import json
from typing import Iterable

SYSTEM_PROMPT = """You are an equity-market analyst commenting on a single
breaking news item alongside another analyst (different model). Your job is
to keep the discussion sharp and additive — do NOT restate points the other
analyst already made.

Output rules — STRICT:
1. Reply with a SINGLE fenced ```json``` block. No prose outside the block.
2. The block MUST match this schema:
   {
     "commentary": str — Traditional Chinese (繁體中文), 80-200 字, 可含 markdown 粗體。
                         **必須**用繁體中文書寫，不可用簡體中文或英文段落。
                         可在句中保留專有名詞 (NVDA, HBM3e, Blackwell, N3P, GLP-1) 不翻譯。
     "bull_points": [str, ...]   # 你方看法中的**正方論點**(看多 / 利多), 1-3 條,
                                 # 每條 ≤30 字繁體中文, 條列短句, 不要重複 commentary 原文。
     "bear_points": [str, ...]   # **反方論點**(看空 / 風險 / 利空), 1-3 條, 同上格式。
     "final_take":  str           # 你個人的最終一句話結論 (繁體中文, ≤30字),
                                 # 例如「看多但需觀察Q2訂單兌現」。
     "entities": {
       "tickers":      [str, ...],   # US-listed root tickers, UPPERCASE English
       "sectors":      [str, ...],   # GICS-style sector names in English
       "themes":       [str, ...],   # English keys: "AI capex", "GLP-1", "HBM3e"
       "tech_keywords":[str, ...]    # English tech-nodes: HBM3e, N3P, CoWoS-L, Blackwell
     },
     "relations": [
       {"subject": "ticker:NVDA", "predicate": "BENEFITS_FROM", "object": "narrative:hbm3e"}
     ],
     "done": bool,             # true ONLY if no new substantive point to add
     "confidence": float (0-1),
     "rationale_short": str — Traditional Chinese (繁體中文), <= 40 字
   }
3. CRITICAL: `commentary` / `bull_points` / `bear_points` / `final_take` /
   `rationale_short` 必須是**繁體中文 (台灣)**。
   `entities` 的內容 (ticker / sector / theme / tech_keyword) 維持英文 — 它們是
   knowledge graph 的 canonical ID，混入中文會破壞 dedup。`relations` 的
   `subject` / `predicate` / `object` 也維持英文。
4. `bull_points` / `bear_points` 是給下游 UI 摘要展示用的**短條列**, 必須
   獨立可讀 — 不可以是「同上」/「見 commentary」這種引用。即使你整體偏空
   也要至少給出 1 條 bull_points (代表方論點), 反之亦然 — 平衡兩面觀點。
5. In Round 2 and Round 3, prioritize adding second-order effects, customer-supplier/competitor/co-development relations, or checking contradictions. Set `done: true` ONLY if the other analyst has covered all relevant angles AND you have no fresh angle to add. Otherwise add a NEW point not already raised in the prior thread.
6. Predicates must be one of: BENEFITS_FROM, HEADWIND_FROM, COMPETES_WITH,
   SUPPLIES_TO, CUSTOMER_OF, CO_DEVELOPS_WITH, MENTIONED_IN, CATALYST_FOR.
"""


def compact_thread_formatter(thread: list[dict]) -> str:
    """V4 Slide-Window Thread Compression.
    Returns a string containing the current kg_state and the raw last comment from each agent."""
    if not thread:
        return "(no prior comments)"

    # 1. 提取每個 Agent 最後一條 comment 原文 (確保 A/B stance 都在 context)
    latest_comments: dict[str, dict] = {}
    for c in thread:
        agent = c.get("agent_role_label", c.get("agent", "?")).upper()
        latest_comments[agent] = c

    # 2. 建立 kg_state
    tickers: set[str] = set()
    themes: set[str] = set()
    relations: list[dict] = []

    for c in thread:
        parsed = c.get("parsed") or {}
        ent = parsed.get("entities") or {}
        tickers.update((t or "").upper() for t in (ent.get("tickers") or []) if t)
        themes.update(t for t in (ent.get("themes") or []) if t)
        for r in (parsed.get("relations") or []):
            if isinstance(r, dict) and r.get("subject") and r.get("predicate") and r.get("object"):
                relations.append(r)

    deduped_rels = []
    seen_rels = set()
    for r in relations:
        k = f"{r.get('subject')}|{r.get('predicate')}|{r.get('object')}"
        if k not in seen_rels:
            seen_rels.add(k)
            deduped_rels.append({
                "subject": r.get("subject"),
                "predicate": r.get("predicate"),
                "object": r.get("object")
            })

    recent_claims = []
    for agent, c in sorted(latest_comments.items()):
        parsed = c.get("parsed") or {}
        recent_claims.append(
            f"{agent} (Round {c.get('round')}) take: {parsed.get('final_take') or ''} "
            f"[confidence: {parsed.get('confidence', 'N/A')}]"
        )

    kg_state = {
        "known_tickers": sorted(tickers),
        "known_themes": sorted(themes),
        "discovered_relations": deduped_rels,
        "recent_claims": recent_claims,
        "unresolved_gaps_hint": "Please identify any contradiction between A and B, or missing second-order / supply-chain links."
    }

    # 3. 組合 slide-window stance text
    parts = []
    parts.append("CURRENT KNOWLEDGE GRAPH STATE (kg_state):")
    parts.append(json.dumps(kg_state, ensure_ascii=False, indent=2))
    parts.append("\nLAST COMMENT RAW TEXT FROM EACH ANALYST (SLIDING WINDOW):")

    for agent, c in sorted(latest_comments.items()):
        parsed = c.get("parsed") or {}
        raw_text = parsed.get("commentary") or ""
        rnd = c.get("round")
        parts.append(f"--- [{agent} · Round {rnd}] ---\n{raw_text}")

    return "\n\n".join(parts)


def _role_text(role) -> str:
    """Accept either string or {'zh','en'} dict — render single line for prompt."""
    if isinstance(role, dict):
        return f"{role.get('en','')} / {role.get('zh','')}"
    return str(role)


def opener_user_prompt(item: dict, role) -> str:
    triage = item.get("triage") or {}
    src = item.get("source") or {}
    role = _role_text(role)
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
  bull_case_snap = {triage.get('bull_case')}
  bear_case_snap = {triage.get('bear_case')}

You are commenting FIRST. Give your independent take on market / sector /
individual-stock implications. Identify the tickers, sectors, themes, and
specific tech-keywords (e.g. HBM3e, N3P, CoWoS-L, GLP-1, Blackwell) that
this news touches. Set `done: false` (you opened the thread).

Respond with the single JSON block as specified in your system prompt.
"""


def followup_user_prompt(item: dict, thread: list[dict], role) -> str:
    src = item.get("source") or {}
    role = _role_text(role)
    return f"""You are {role}.

NEWS ITEM
---------
Headline : {item.get('headline')}
Source   : {src.get('name')} ({src.get('credibility')})
URL      : {src.get('url')}
Summary  : {item.get('raw_summary')}

PRIOR DISCUSSION (COMPRESSED SLIDING WINDOW)
--------------------------------------------
{compact_thread_formatter(thread)}

Add ONE genuinely new angle the prior thread missed (different ticker, a
2nd-order effect, a contra-argument, a specific named supply-chain node).
If you cannot find a new substantive point, set `done: true` and explain why
in `rationale_short`. Do NOT restate prior points.

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

    for c in thread:
        rnd = c.get("round", 0)
        agent = c.get("agent_role_label", c.get("agent", "Unknown"))
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
        "final_takes_by_round": final_takes_by_round
    }


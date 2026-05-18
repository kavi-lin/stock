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
5. Set `done: true` ONLY if the other analyst has covered all relevant angles
   AND you have no fresh angle to add. Otherwise add a NEW point not already
   raised in the prior thread.
6. Predicates must be one of: BENEFITS_FROM, HEADWIND_FROM, COMPETES_WITH,
   SUPPLIES_TO, CUSTOMER_OF, CO_DEVELOPS_WITH, MENTIONED_IN, CATALYST_FOR.
"""


def _format_thread(thread: list[dict]) -> str:
    if not thread:
        return "(no prior comments)"
    parts = []
    for c in thread:
        agent = c.get("agent", "?").upper()
        rnd = c.get("round", "?")
        text = (((c.get("parsed") or {}).get("commentary")) or
                (c.get("parsed") or {}).get("rationale_short") or "")
        parts.append(f"[Round {rnd} · {agent}] {text}")
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

PRIOR DISCUSSION
----------------
{_format_thread(thread)}

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
    Derives a consensus verdict and surfaces the LATEST agent's final_take."""
    tickers: set[str] = set()
    sectors: set[str] = set()
    themes: set[str] = set()
    techs: set[str] = set()
    relations: list[dict] = []
    verdict_votes: dict[str, int] = {}
    # Order matters: keep Claude's points first, then Gemini's. Iterate the
    # thread, accumulating per side in arrival order; dedup at the end.
    bull_buf: list[str] = []
    bear_buf: list[str] = []
    final_take: str | None = None
    final_take_by: str | None = None

    for c in thread:
        p = c.get("parsed") or {}
        ent = p.get("entities") or {}
        tickers.update((t or "").upper() for t in (ent.get("tickers") or []) if t)
        sectors.update(s for s in (ent.get("sectors") or []) if s)
        themes.update(t for t in (ent.get("themes") or []) if t)
        techs.update(k for k in (ent.get("tech_keywords") or []) if k)
        for r in (p.get("relations") or []):
            if isinstance(r, dict) and r.get("subject") and r.get("predicate") and r.get("object"):
                relations.append(r)
        for pred in (r.get("predicate") for r in (p.get("relations") or []) if isinstance(r, dict)):
            if pred == "BENEFITS_FROM":
                verdict_votes["BULLISH"] = verdict_votes.get("BULLISH", 0) + 1
            elif pred == "HEADWIND_FROM":
                verdict_votes["BEARISH"] = verdict_votes.get("BEARISH", 0) + 1
        bull_buf.extend(bp for bp in (p.get("bull_points") or []) if isinstance(bp, str))
        bear_buf.extend(bp for bp in (p.get("bear_points") or []) if isinstance(bp, str))
        ft = p.get("final_take")
        if isinstance(ft, str) and ft.strip():
            final_take = ft.strip()
            final_take_by = c.get("agent")

    consensus = "NEUTRAL"
    if verdict_votes:
        consensus = max(verdict_votes, key=verdict_votes.get)
        if len(set(verdict_votes.values())) == 1 and len(verdict_votes) > 1:
            consensus = "SPLIT"

    return {
        "consensus_verdict": consensus,
        "merged_entities": {
            "tickers": sorted(tickers),
            "sectors": sorted(sectors),
            "themes": sorted(themes),
            "tech_keywords": sorted(techs),
        },
        "merged_relations": _dedup_relations(relations),
        "bull_summary": _rough_dedup(bull_buf)[:6],
        "bear_summary": _rough_dedup(bear_buf)[:6],
        "final_take":    final_take,
        "final_take_by": final_take_by,
    }


def _dedup_relations(relations: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for r in relations:
        k = f"{r.get('subject')}|{r.get('predicate')}|{r.get('object')}"
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out

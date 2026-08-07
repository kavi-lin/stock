# Link Digest Protocol (V1.0)

> **Trigger**: Dashboard News page → URL input box → `link_digest` protocol
> (`dashboard_server.py` PROTOCOL_PROMPTS). Runs as a single non-interactive
> `claude -p … --permission-mode bypassPermissions` turn, so **WebFetch + WebSearch
> tools are available**.
>
> **What it is**: user supplies ONE article URL. You read the full article, search
> the web for related news/context, run a 4-view debate + Arbiter, and emit a
> judgment digest. The output lands as (a) a raw `.md` in the reports center,
> (b) a card in the news feed, and (c) entities + supply-chain relations that the
> Knowledge Graph (Project Nexus) and supply-chain page ingest.
>
> **Relationship to FLASH**: this is `flash_text` (see `news/news_protocol_v2.md`)
> with a URL input, real WebSearch (3-5 related sources), and an extra KG payload.
> Reuse the same 4-view debate rubric and net_impact scoring.

---

## Flow (one turn, do not stop to ask)

### Step 1 — Read the source article
- `WebFetch(url)` → full article body. Extract: headline, publisher (`source_label`),
  publish timestamp (`published`, ISO 8601), primary entities.
- If WebFetch fails or returns a paywall stub, still proceed using whatever text is
  available + the URL slug; note the degradation in `arbiter_reasoning`.

### Step 2 — Search the web for related news/context
- `WebSearch` for the central event/entities (e.g. company + catalyst). Pick the
  **3-5 most relevant, most recent** results.
- `WebFetch` the top 3-5 of those to read their actual content (not just snippets).
- The goal: corroborate or challenge the source article, surface second-order
  effects (suppliers / customers / competitors / sector / macro), and gather the
  URLs that back each relation you assert in Step 4.

### Step 3 — 4-view debate + Arbiter
- Run **inline** Bull / Bear / Sector / Macro views over (source article + the
  related sources). Same rubric as `news_protocol_v2.md` Stage 2 deep debate.
  - `bull_case` / `bear_case`: 150-250 words each.
  - `sector_view`: include the 2-stage supply-chain read (who benefits / who is hurt
    upstream↔downstream).
  - `macro_view`: Fed / yield / FX / historical-analogue read.
- **Arbiter**: weighted `net_impact_score` (float, -5..+5), a `verdict`
  (BULLISH / BEARISH / BINARY / NEUTRAL), `arbiter_reasoning` (≥150 words), and a
  one-line `debate_note` (the key disagreement).

### Step 4 — Extract entities + supply-chain relations (the KG payload)
- `entities`: all real `tickers` (uppercase), `sectors` (GICS names), `themes`
  (free-text narratives), `tech_keywords`.
- `relations`: directed edges. **Only assert a relation you can back with ≥1
  source URL.** Tag each with `corroborating_sources` (the URLs — source article +
  any related source that affirms it). This list directly powers the graph: a
  ticker↔ticker relation affirmed by **≥2 sources** becomes a real provisional
  supply-chain edge (Nexus Phase-2 threshold `support_count>=2`).
  - **ticker↔ticker predicates** (supply-chain): `SUPPLIES_TO`, `CUSTOMER_OF`,
    `CONTRACT_MFG_FOR`, `CO_DEVELOPS_WITH`, `COMPETES_WITH`.
    Format `subject:"ticker:NVDA"`, `object:"ticker:TSM"`. Direction matters:
    `SUPPLIES_TO` = subject supplies object. (Both tickers should be real, listed
    US tickers — the graph drops edges where either ticker is outside its universe.)
  - **ticker→theme predicates**: `BENEFITS_FROM`, `HEADWIND_FROM`.
    Format `object:"theme:hbm"` (lowercase slug).
  - Each relation: `{subject, predicate, object, confidence (0-1), evidence (short
    quote/paraphrase), corroborating_sources:[url, …]}`.

### Step 5 — Write artifacts, then run the deterministic writer
1. **Write the report MD** (your prose — this is your strength):
   `reports/YYYY-MM-DD_HHMM_link_digest.md` — sections: source summary + link,
   related-news synthesis (with cited links), 4-view debate, Arbiter verdict, and a
   "KG payload" appendix listing the entities + relations you extracted.
2. **Write the judgment JSON** (machine record — strict schema below):
   `news/news_logs/link_digest/<id>.judgment.json` where `<id>` =
   `ld_YYYYMMDD_<8hexhash-of-url>`.
3. **Run the deterministic writer** (fans the judgment into the two files the KG +
   news feed consume, with guaranteed schema):
   ```bash
   python3 scripts/link_digest/build_artifacts.py news/news_logs/link_digest/<id>.judgment.json
   ```
   - rc=0 → done. rc=2 → degraded but usable (e.g. digest validator count nudge);
     still acceptable. rc=1 → fatal, fix the judgment.json and re-run.
   - Do **not** hand-write `news_events.jsonl`, the digest projection, or `bn_*.json`
     yourself — the writer owns those schemas. Your job is the MD + judgment.json.

End condition: the MD + judgment.json are written and `build_artifacts.py` exited
0 or 2. Do not stop mid-flow to ask the user anything.

---

## judgment.json schema (V1.0)

```jsonc
{
  "id": "ld_20260530_1a2b3c4d",       // ld_YYYYMMDD_<8hex of url>
  "url": "https://…",                  // the source URL (required)
  "headline": "…",                     // English (or original) headline
  "headline_zh": "…",                  // zh-TW headline
  "source_label": "Reuters",           // publisher
  "published": "2026-05-30T11:00:00Z", // ISO 8601 publish time of the SOURCE article
  "news_type": "corporate",            // earnings|corporate|monetary_policy|macro_data|geopolitical|sector_news|sentiment
  "verdict": "BULLISH",                // BULLISH|BEARISH|BINARY|NEUTRAL
  "net_impact_score": 2.4,             // float, -5..+5
  "bull_case": "… 150-250 words …",
  "bear_case": "… 150-250 words …",
  "sector_view": "… incl. 2-stage supply chain …",
  "macro_view": "… Fed/yield/FX/analogue …",
  "arbiter_reasoning": "… ≥150 words …",
  "debate_note": "… key disagreement, one line …",
  "binary_risk": false,
  "binary_event_date": null,           // ISO date or null
  "within_48h": false,
  "affected_sectors": [
    {"sector": "Information Technology", "direction": "bullish"}
  ],
  "entities": {
    "tickers": ["NVDA", "TSM"],
    "sectors": ["Information Technology"],
    "themes": ["hbm", "ai accelerators"],
    "tech_keywords": ["HBM3e", "CoWoS"]
  },
  "relations": [
    {
      "subject": "ticker:NVDA",
      "predicate": "CUSTOMER_OF",
      "object": "ticker:TSM",
      "confidence": 0.86,
      "evidence": "NVDA relies on TSMC CoWoS capacity for Blackwell.",
      "corroborating_sources": ["https://…", "https://…"]   // ≥2 ⇒ real graph edge
    },
    {
      "subject": "ticker:NVDA",
      "predicate": "BENEFITS_FROM",
      "object": "theme:hbm",
      "confidence": 0.8,
      "evidence": "…",
      "corroborating_sources": ["https://…"]
    }
  ],
  "related_sources": [
    {"url": "https://…", "title": "…", "published": "2026-05-29T…Z"}
  ]
}
```

### Localisation (zh-TW)
- Write the analytical prose (`bull_case` / `bear_case` / `sector_view` / `macro_view` /
  `arbiter_reasoning` / `debate_note`) in **English** — keep it analytical and faithful
  to the source. `build_artifacts.py` runs a **gemini (agy) translation pass** that adds
  zh-TW variants (`bull_case_zh`, …, `arbiter_reasoning_zh`, `headline_zh`) to the digest
  verdict + `bn_*.json`; the News page renders the `_zh` variant when the UI is in
  Chinese, falling back to the English base otherwise.
- You **may** supply `headline_zh` in the judgment — it takes precedence over the gemini
  translation. The report MD prose language is your choice (English is fine; the card
  surface is what gets localised).
- Translation is best-effort (env `LINK_DIGEST_TRANSLATE`, default on). If agy is
  unavailable the writer degrades to rc=2 and cards show the English base — not fatal.

### Notes
- `arbiter_reasoning` must be ≥30 chars (validator hard floor; aim ≥150 words).
- `tickers_mentioned` in the digest verdict is derived from `entities.tickers` by the
  writer — you do not set it.
- Relations whose `subject`/`object` are not both real listed tickers (for the
  supply-chain predicates) will surface as entity nodes but not as a directed edge —
  that's expected; assert them anyway when the article supports them.
- A single article usually yields `support_count = len(corroborating_sources)`. To
  get a **directed supply-chain edge** in the graph, make sure a genuine ticker↔ticker
  relation is affirmed by ≥2 of the sources you fetched.

# LLM Task Catalog

Runtime authority: `config/llm_task_registry.json` + `config/llm_certifications.json`.
Every inference requires a live `llm-quota-broker` lease. Claude, Agy/Gemini,
and Codex are the only formal providers; Grok is disabled until the broker can
measure and reserve its quota.

| Category | Task IDs | Runtime behavior |
|---|---|---|
| Agentic protocols | `agentic_protocol-{invest,sector,news,earnings,flash,flash_text,review,triage,link_digest,llm_review,playbook}` | Interactive queue waits and retries before launch; a started protocol is never replayed on another provider |
| Ensembles | `debate`, `office`, `office_verdict` | Broker assigns voices; each inference has its own lease; no provider fallback after a failed turn |
| Structured research | `generate`, `nexus_gap_fill`, `nexus_tier3_ner`, `narrative_confirm`, `link_digest`, `capability_probe` | Daemon jobs defer on broker failure; explicit `--agent` is a broker-pinned certification route |
| Narrative synthesis | `brief`, `intraday_eval`, `report_polish` | Broker chooses one provider; deterministic output may remain when narration/polish is unavailable |
| External tool reasoning | `wind_reasoning` | One broker-selected provider is held for the complete external research run |

Deterministic scripts such as earnings preview, quant backtest, shadow report,
and ordinary weekly review rendering are outside this catalog only when they do
not launch an LLM. If a deterministic task later adds inference, its task ID,
certification, broker route, and audit coverage are required in the same change.

Run the gate:

```bash
python3 scripts/audit_llm_governance.py
```

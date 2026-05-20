# news/scripts/archive

Deprecated scripts that conflict with `news/news_protocol_v2.md` Phase 4 rules.
Kept here so git blame / archaeology still works, but **do NOT call from new code**.

| Script | Why archived |
|---|---|
| `assemble_digest.py` | Pre-v3.14.x workflow assembled chunked subagent outputs into a final digest. Protocol v2 Phase 4 (see `news/news_protocol_v2.md` "DO NOT" block) forbids chunked assembly: each run writes `news_logs/YYYY-MM-DD_digest.json` in one shot. Leaving the script in `news/scripts/` was a documentation hazard — agents seeing it would assume the chunked path was current. Moved here in v3.14.3. |

If you need to revive any of these, copy the file out, integrate the new
behaviour into `stage1_triage.py` + Phase 4 single-write, and update the
protocol — do **not** restore the legacy chunked flow.

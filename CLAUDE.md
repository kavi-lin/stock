# AI Investment Committee（AI 投資委員會） — Agent Execution Context

> 版本同步：`VERSION` + `Dashboard/utils.js` + `CHANGELOG.md` 三處一起（驗證命令見 `docs/agent-ops/MAINTENANCE.md`）。專案背景見 `README.md`。
> 本檔只做路由：指令 → 讀哪個檔。歷史沿革一律查 `CHANGELOG.md`，不寫在這裡。
> 本檔的 Protocol Triggers 表是唯一 source of truth；`AGENTS.md`（Codex）只引用不複製。

## Protocol Triggers（中期 / 委員會層）

| 指令 | 先讀這個檔 | 一句話紀律 |
|---|---|---|
| `產業掃描` | `sector/sector_protocol_main.md` | 主檔載入 phase_0 / phase_1-2-3 / phase_4-5 子檔 |
| `分析 [TICKER]` | `investment/investment_protocol_v5_0.md` | 5 lane subagent + Red Team；數字全走 script 禁手算；FMP bundle 規範見 `investment/protocol_appendix_fmp_bundles.md` |
| `財報 [TICKER]` | `skills/earnings-analyst/SKILL.md` | Cache key = (TICKER, last_earnings_date)；MD 報告必附 EDGAR/IR/FMP clickable link（規則在 SKILL.md Citations） |
| `新聞分析 DIGEST` | `news/news_protocol_v2.md` | RSS → deterministic triage → debate |
| `新聞分析 FLASH [text]` | `news/news_protocol_v2.md` | Deep Debate only |
| `動能 [TICKER]` / `動能選股` / `更新 journal` | `skills/momentum-monitor/scripts/` 的 momentum.py / screen.py / journal.py | 直接跑 script |
| `ic-memo [TICKER]`（或 `分析 --memo`） | `skills/ic-memo-writer/SKILL.md` | Deterministic renderer（0 LLM）；不重評分、不改 history.json |
| `首次覆蓋 [TICKER]`（或 `分析 --initiation`） | `skills/ic-memo-writer/SKILL.md`（`template_initiation.md`） | Deterministic renderer；前置 = history entry + valuation-modeler cache；validator `--initiation` rc=0/2 |
| `估值模型 [TICKER]` / `同業比較 [TICKER]` | `skills/valuation-modeler/SKILL.md` | 直接跑 dcf.py / comps.py；數字全 script；餵 protocol 的 dcf_self_built / comps_implied anchor |
| `財報前瞻 [TICKER]` | （UI 自動觸發，server subprocess，不走 Claude turn） | 手動版指令見 `docs/agent-ops/OPS_COMMANDS.md` §2 |
| `回測 [TICKER]` | （UI 自動觸發，server subprocess，不走 Claude turn） | 探索層；手動版見 `docs/agent-ops/OPS_COMMANDS.md` §2；細節 `skills/quant-backtest/SKILL.md` |

## 自動層（無需觸發，直接讀輸出檔）

| 層 | 輸出在哪 | 細節文件 |
|---|---|---|
| 戰術雷達（1-15 天） | `skills/thematic-screener/data/recommendations/<DATE>.json` | `skills/MARKET_INDEX.md`、`docs/plan_short.md` |
| Break News（daemon） | `news/break_news_logs/bn_*.json`、`/break-news.html` | 手動指令 `docs/agent-ops/OPS_COMMANDS.md` §6 |
| Nexus 知識圖譜 | `Dashboard/nexus_graph.json`、`/graph.html` | `docs/agent-ops/OPS_COMMANDS.md` §5 |
| Link Digest（News 頁貼 URL） | `reports/*_link_digest.md` + judgment.json | `news/link_digest_protocol.md` |

**全域紀律（不可違反）**：以上自動層 + 回測全部是**探索層**——產出**永不**進入 investment_protocol 的決策（buy_threshold / position_size / verdict）。Break News 的 Claude × Gemini 分歧是刻意設計，divergence_note 是訊號不是 bug。Nexus Tier 3 LLM 找到的新實體先標 `provisional`，需 ≥3 份獨立報告才晉升一級節點。`skills/short-term-target/config/weights.yaml` 只由使用者手動校準，任何 agent 不得自動覆寫。

## Validator Gates（protocol 收尾必 rc=0）

| Mode | Script | Schema |
|---|---|---|
| News | `news/scripts/validate_digest_output.py` | `news/digest_output_schema.md` |
| Sector | `sector/scripts/validate_sector_intel.py` | `sector/schema.md` |
| Invest | `investment/scripts/validate_session_export.py` | `investment/phase5_export_schema.md` |

## Output Paths

- Reports → `reports/`（`YYYYMMDD_TICKER.md`、`YYYY-MM-DD_sector_report.md`…）
- Caches → `sector/logs/`、`investment/invest_logs/`、`news/news_logs/`、`skills/*/cache/`

## Ops

```bash
./daily_update.sh                                              # 每日例行（3-5 min）
python3 skills/short-term-target/scripts/weekly_review.py      # 週末覆盤
```

其餘全部指令（單股查詢、引擎測試對照表、validator、break news 手動）→ **`docs/agent-ops/OPS_COMMANDS.md`**。

## Shared Modules（改名單/資料源只改這裡）

- `skills/_shared/company_context.py` — FMP company metadata 唯一來源（SECTOR_UNIVERSE / peers / 24h cache）
- `skills/_shared/technical_core.py` — 技術指標唯一來源（fetch_history / rsi_14 / MA）
- `scripts/_shared/model_router.py` — 外部 CLI（claude/gemini/codex）預算與 fallback 治理；config 在 `config/llm_config.json`

## Agent 治理文件（dev session 與派工必讀）

| 檔 | 何時讀 |
|---|---|
| `docs/agent-ops/MODEL_DISPATCH.md` | 要 spawn subagent / 選 model 之前 |
| `docs/agent-ops/DELEGATION_TEMPLATES.md` | 寫派工 prompt 時直接套模板 |
| `docs/agent-ops/JUDGMENT.md` | 拿不準「該升級／算完成／該問人／方向錯了」時 |
| `docs/agent-ops/MAINTENANCE.md` | 要改 CLAUDE.md、SESSION_NOTES、CHANGELOG、skills 索引之前 |
| `docs/agent-ops/DIAGNOSIS.md` | 想知道這套規則為什麼存在 |

## Workflow Rules（dev/refactor/fix session）

1. **動工前確認**：改動 ≥2 檔或單檔 ≥50 行 → 先輸出摘要表（File / Action / Est. Lines / Description），等使用者「OK」。使用者已在本輪明確授權自主作業時免確認。
2. **收尾 checklist**：(a) 三處版本同步並跑 MAINTENANCE.md 的驗證命令；(b) 按 MAINTENANCE.md 的讀寫規則更新 `SESSION_NOTES.md` / `TODO.md`（禁止整檔 Read）；(c) 改了引擎 → 跑 `OPS_COMMANDS.md` §7 對應測試 rc=0；(d) 收尾殘留掃描 —— `MAINTENANCE.md` §2b，用字串問不用清單問。
3. **🚫 排除**：protocol 執行（`產業掃描`、`分析` 等）不是 dev session——不 bump 版本、不動 todolist。

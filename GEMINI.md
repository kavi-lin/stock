# AI Investment Committee（AI 投資委員會） — Antigravity (agy) CLI Execution Context

**本檔自足。** 下方 generated 區塊帶著觸發表、探索層邊界、validator gates 與
workflow rules（自 `CLAUDE.md` 逐字同步），你**不需要**去讀 `CLAUDE.md` 或
`AGENTS.md` —— 從觸發詞直接跳到它指名的 protocol 檔。

⚠️ 實測 2026-08-09：`agy --print` **不會**自動載入本檔（兩次探針分別回 `NONE`
與 `UNKNOWN`）。因此 dashboard_server 派工時會在 prompt 開頭明確要求你先
Read 本檔。若你是被那樣叫起來的，先讀完本檔再動作。

## 專案核心定位 (Core Identity)
- **Role**: Senior Software Engineer / Quantitative Research Engineer.
- **Context**: 協助開發與維護 AI 驅動的投資決策系統，包含數據抓取、量化分析、LLM 投資協議 (Protocols) 與視覺化儀表板。
- **深入資料**（需要時才讀）:
    - 系統架構: `docs/ARCHITECTURE_DIAGRAM.md`, `README.md`.
    - 開發狀態: `SESSION_NOTES.md`, `TODO.md`.
    - 全部指令總表: `docs/agent-ops/OPS_COMMANDS.md`.

## 作業範圍 (Scope)
一律在目前工作目錄（cwd）這個 repo 內作業。cwd 以外的路徑（家目錄、
`~/Documents`、`~/Stock`、其他 CLI 的 state 目錄）都**不是**本專案，禁止去那裡
搜尋專案檔案。

## 收尾補充 (Session Close)
版本三處同步後必跑 `docs/agent-ops/MAINTENANCE.md` §2 的驗證命令，輸出
`SYNC OK` 才算完成；SESSION_NOTES / CHANGELOG 的讀寫規則（禁整檔 Read、插入
錨點）見 MAINTENANCE §3。

## Antigravity 專屬規範 (Antigravity Specific Guidelines)

### 1. Topic Model 使用規範
- **啟動任務**: 在第一回合呼叫 `update_topic` 描述任務目標與預計步驟。
- **重大轉折**: 當遇到預期外的錯誤（如測試失敗、架構衝突）需要調整策略時，必須呼叫 `update_topic` 紀錄策略變更。
- **任務總結**: 在任務結束後的最後一回合呼叫 `update_topic` 摘要已完成的工作。
- **避免濫用**: 簡單的檔案讀取、搜尋或詢問不需要呼叫 `update_topic`。

### 2. 程式風格與標準 (Coding Standards)
- **Python**: 遵循 PEP 8，優先使用專案現有的 `skills/_shared/` 模組進行數據存取。
- **Frontend**: 遵循 `Dashboard/style.css` 的設計風格。修改儀表板時需確保 `i18n.js` 的多語言支援正確。
- **Testing**: 修改核心邏輯後，必須執行相關的 Validator Gates (例如 `news/scripts/validate_digest_output.py`) 確保 Schema 符合規範。

### 3. 安全性與環境變數 (Security)
- 嚴格禁止將 `ANTHROPIC_API_KEY`, `FMP_API_KEY` 等敏感資訊寫入程式碼或日誌。
- 修改 `.env` 檔案時需極度謹慎。

## 常用操作捷徑 (Ops Shortcuts)

完整指令總表（按情境分組，含「改了哪個引擎跑哪組測試」對照）：`docs/agent-ops/OPS_COMMANDS.md`。
```bash
./daily_update.sh   # 每日例行
```

<!-- BEGIN generated from CLAUDE.md — do not edit by hand -->

> **本區塊由 `scripts/sync_agent_context.py` 從 `CLAUDE.md` 生成，不要手改。**
> 本檔是 Antigravity (`agy`) 的 context 檔。實測 2026-08-09：`agy --print` **不會**自動載入本檔，所以 protocol prompt 會明確要求你先 Read 它。
> 你只需要這一個 context 檔 —— 不必去讀 `CLAUDE.md` 或 `AGENTS.md`。

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
| Nexus 知識圖譜／主動供應鏈 Radar | `Dashboard/nexus_graph.json`、`nexus_topics.json`、`nexus_quality.json`、`nexus/claim_ledger.jsonl`、`/graph.html` | `docs/agent-ops/OPS_COMMANDS.md` §5 |
| Link Digest（News 頁貼 URL） | `reports/*_link_digest.md` + judgment.json | `news/link_digest_protocol.md` |

**全域紀律（不可違反）**：以上自動層 + 回測全部是**探索層**——產出**永不**進入 investment_protocol 的決策（buy_threshold / position_size / verdict）。Break News 的 Claude × Gemini 分歧是刻意設計，divergence_note 是訊號不是 bug。Nexus Tier 3 LLM 找到的新實體先標 `provisional`，需 ≥3 份獨立報告才晉升一級節點。`skills/short-term-target/config/weights.yaml` 只由使用者手動校準，任何 agent 不得自動覆寫。

## Validator Gates（protocol 收尾必 rc=0）

| Mode | Script | Schema |
|---|---|---|
| News | `news/scripts/validate_digest_output.py` | `news/digest_output_schema.md` |
| Sector | `sector/scripts/validate_sector_intel.py` | `sector/schema.md` |
| Invest | `investment/scripts/validate_session_export.py` | `investment/phase5_export_schema.md` |

## Workflow Rules（dev/refactor/fix session）

1. **動工前確認**：改動 ≥2 檔或單檔 ≥50 行 → 先輸出摘要表（File / Action / Est. Lines / Description），等使用者「OK」。使用者已在本輪明確授權自主作業時免確認。
2. **收尾 checklist**：(a) 三處版本同步並跑 MAINTENANCE.md 的驗證命令；(b) 按 MAINTENANCE.md 的讀寫規則更新 `SESSION_NOTES.md` / `TODO.md`（禁止整檔 Read）；(c) 改了引擎 → 跑 `OPS_COMMANDS.md` §7 對應測試 rc=0；(d) 收尾殘留掃描 + 靜默綠防線 —— `MAINTENANCE.md` §2b / §2c。
3. **🚫 排除**：protocol 執行（`產業掃描`、`分析` 等）不是 dev session——不 bump 版本、不動 todolist。

<!-- END generated from CLAUDE.md -->

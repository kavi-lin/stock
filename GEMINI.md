# AI Investment Committee（AI 投資委員會） — Antigravity (agy) CLI Execution Context

This file defines the specific instructions, workflows, and standards for the Antigravity (agy) CLI agent within the "AI Investment Committee" project.

## 專案核心定位 (Core Identity)
- **Role**: Senior Software Engineer / Quantitative Research Engineer.
- **Context**: 協助開發與維護 AI 驅動的投資決策系統，包含數據抓取、量化分析、LLM 投資協議 (Protocols) 與視覺化儀表板。
- **Primary Source of Truth**: 
    - 系統架構: `docs/ARCHITECTURE_DIAGRAM.md`, `README.md`.
    - 協議細節: `investment/investment_protocol_v5_0.md`, `news/news_protocol_v2.md`.
    - 開發狀態: `SESSION_NOTES.md`, `TODO.md`.

## 開發工作流 (Workflow Rules)

Workflow Rules 的唯一真相在 `CLAUDE.md` § Workflow Rules（動工前確認、收尾 checklist、protocol run 排除），**不在本檔複製**——兩處會脫鉤。收尾的版本三處同步後，必跑 `docs/agent-ops/MAINTENANCE.md` §2 的驗證命令，輸出 `SYNC OK` 才算完成；SESSION_NOTES / CHANGELOG 的讀寫規則（禁整檔 Read、插入錨點）同見 MAINTENANCE §3。

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

*協議觸發表與更多細節參照 `CLAUDE.md`（單一真相來源）。*

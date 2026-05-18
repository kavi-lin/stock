# AI 投資委員會 — Gemini CLI Execution Context

This file defines the specific instructions, workflows, and standards for the Gemini CLI agent within the "AI Investment Committee" project.

## 專案核心定位 (Core Identity)
- **Role**: Senior Software Engineer / Quantitative Research Engineer.
- **Context**: 協助開發與維護 AI 驅動的投資決策系統，包含數據抓取、量化分析、LLM 投資協議 (Protocols) 與視覺化儀表板。
- **Primary Source of Truth**: 
    - 系統架構: `docs/ARCHITECTURE_DIAGRAM.md`, `README.md`.
    - 協議細節: `investment/investment_protocol_v5_0.md`, `news/news_protocol_v2.md`.
    - 開發狀態: `SESSION_NOTES.md`, `TODO.md`.

## 開發工作流 (Workflow Rules)

### 1. 實作前確認 (Pre-implementation Confirmation)
**觸發條件 (Trigger)**: 修改涉及 **≥ 2 個檔案** 或 單一檔案修改 **≥ 50 行**。
**執行動作 (Action)**: 
1. 進入 `Plan Mode` 進行設計。
2. 輸出一份摘要表格 (File, Action, Est. Lines, Description) 與預估影響範圍。
3. 等待使用者回覆 "OK" 後再開始執行。

### 2. 任務完成檢查表 (Session Completion Checklist)
**定義 (Definition)**: 使用者要求的開發、重構或修復任務已完成。
1. **同步版本號 (Bump VERSION)**: 同時更新以下 **三個** 位置：
    - `VERSION` 檔案 (例如: `1.5.0`)
    - `Dashboard/utils.js` (例如: `'V1.5.0'`)
    - `CHANGELOG.md` (新增 `## [x.y.z] — YYYY-MM-DD` 區塊，含 `### Changed/Added/Fixed` 條列與 `### Why` 動機)。
    *Note: 大改動跳 minor (x.Y.z)，小修復跳 patch (x.y.Z)。*
2. **更新進度紀錄 (Update SESSION_NOTES.md / TODO.md)**: 勾選已完成項目，更新狀態，並撰寫 `Last Session Note`。

**🚫 例外規定 (EXCLUSION)**: 執行投資協議 (`分析`, `產業掃描` 等) **不屬於** Session。執行完協議後 **不可** 更新版本號或修改 TODO list。

## Gemini 專屬規範 (Gemini Specific Guidelines)

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

```bash
# 每日自動更新 (含數據抓取與圖譜建立)
./daily_update.sh

# 數據校對與分析
python3 skills/finnhub-client/scripts/audit_drift_check.py            # Finnhub vs FMP 漂移檢查
python3 investment/scripts/backtest_postmortem.py                     # 協議決策回測

# Break News 偵錯
python3 scripts/break_news/poller.py --once             # 單次抓取
python3 scripts/break_news/debater.py --news-id <id>    # 單條 Debate
```

*參照 `CLAUDE.md` 獲取更多協議細節與進階命令。*

# Office Claude Member — Route A (Persistent PTY Terminal) 定稿

> **Status**: Design RFC, pre-implementation. 地基（billing smoke test）未過不准進 v1。
> **Scope**: 僅 AI 辦公室 Dashboard 頁的 **Claude member**。Codex / Gemini member 各自實測，差異見文末。
> **Last reviewed**: 2026-05-30 — Claude × Codex × Gemini(agy) 三方 review 後整合。

---

## 0. 一句話

v1 = **persistent PTY terminal member**：drawer 內是前端 **xterm.js terminal viewport**，後端純 **PTY raw byte relay**。**不**承諾整理過的 chat transcript。乾淨 transcript parser 延到 phase 2。

定位刻意從原 proposal 的「chat transcript scraper」改成「terminal viewport」——因為 `claude` 沒有 inline mode，永遠 alt-screen TUI，只有真 terminal emulator 能正確 render。Scraper 路是死路。

---

## 1. Billing premise（待驗證 — 不是已證實事實）

> ⚠️ **待官方第一方來源確認 + 上線前實測。**

- 多個第三方來源（Zed / VentureBeat / Apiyi 等）報導 **2026-06-15** 起 Anthropic 訂閱拆兩池：第一方互動式終端 CLI 留訂閱；`claude -p` / Agent SDK / ACP / 第三方 programmatic 移入計量 **Agent SDK Credit pool**（Pro $20 / Max5x $100 / Max20x $200/mo，非滾存，按 API rate）。
- **未找到 Anthropic 第一方精確公告。** 因此「no `-p` 才留訂閱」當**設計方向**，不當已證實依據。
- agy 宣稱「跑在 `pty.openpty()` 上且無 `-p` → `isatty()` 判定 → 100% 走 flat-rate 訂閱」——**駁回此確定性**。計費路徑可能看 auth token 類型 / request flag / OAuth vs API / session metadata，不一定只看 `isatty()`。無來源不接受「100%」。

**地基 gate**：上線前用真帳號跑一輪互動 PTY claude，驗訂閱 usage 有扣、Agent SDK credit 沒動。**這關不過，整個 Route A 不准進 v1。**

來源（皆第三方，待第一方覆核）：
- https://zed.dev/blog/anthropic-subscription-changes
- https://venturebeat.com/technology/anthropic-reinstates-openclaw-and-third-party-agent-usage-on-claude-subscriptions-with-a-catch
- https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan

---

## 2. 為什麼 Claude 強制走 terminal viewport（非選配）

實測 `claude --version` = `2.1.158`：

| CLI | inline / no-alt-screen | 結論 |
|---|---|---|
| `claude` | **無** — 全螢幕 alt-screen TUI，無法關 | **強制** xterm.js full terminal |
| `codex` | 有 `--no-alt-screen` | 可走 inline，relay 較輕 |
| `agy`(Gemini) | 有 `-i/--prompt-interactive` continue session，無 no-alt flag | 比照 Claude，各自 smoke 測 |

alt-screen（游標跳位、清屏、局部重繪）只有真 terminal emulator 能正確還原。xterm.js 原生吃 alt-screen buffer → 不 scrape，純 relay bytes，claude TUI 在 drawer 內長得跟本機終端機一致。

---

## 3. v1 範圍

### 3.1 啟動
- 指令：`claude`（或 `$CLAUDE_BIN`），**no `-p` / `--print` / `--bare`**。
- 跑在 `pty.openpty()` + `subprocess.Popen()`。
- 注入 `CLAUDE_CONFIG_DIR=<office 專用精簡 config dir>`：最小 settings、**無 MCP**（避免啟動卡 MCP 互動 auth）。
- spawn 前 `env.pop` 掉 `CLAUDECODE*` / `CLAUDE_ENV` 等嵌套變數，防 dashboard_server 在 Claude Code 內啟動時的 nested 行為。
- cwd = 已信任的 project dir。
- 預設 `--permission-mode default` → 權限 y/n **由 user 在 terminal pane 內回答**。terminal viewport 讓「預設不 bypass」變可用且不卡。
- 起始固定 PTY size（e.g. 120×40），之後由 resize endpoint 同步。

> **Auth 註記**：本機 OAuth 憑證在 macOS **keychain**（`~/.claude/` 無明文 `.credentials.json`），故 fresh `CLAUDE_CONFIG_DIR` 仍讀 keychain → 不會被登出。若日後改 API-key 機器，需另處理 auth 注入。

### 3.2 IO（改自原 polling 設計）
- **WebSocket（或 SSE）raw byte relay**，取代原 proposal 的 `GET /events?since=N` text chunk——alt-screen 要逐 byte 有序串流（含 cursor escape / clear），polling 切 chunk 會錯位、xterm.js render 會壞。
- `POST /api/office/sessions/claude/message`：v1 **單行** input + `\r`（Ink editor 的 Enter；**不是** `\n`，`\n` 只插入換行）。多行先停用。
- **resize endpoint** → `TIOCSWINSZ` 同步 xterm.js 前端尺寸，否則 TUI 重繪寬度錯亂。
- scrollback raw log = best-effort，標 **experimental**。

### 3.3 Lifecycle（沿用原 proposal）
- lazy start：首次 click/send 才起該 member。
- Asia/Taipei daily session key；日界 rollover → terminate stale → 下次互動 fresh spawn。
- **clear** = terminate process + 清 in-memory transcript（真 context reset）。
- **restart** = clear + 立即 respawn。
- **stop** = terminate，留畫面到 clear / rollover。

### 3.4 Preflight smoke（實作前必跑）
1. **啟動健檢**：PTY 起 claude → 等到可輸入狀態 → 送最小 prompt → 確認**不卡** trust dialog / MCP auth / login。
2. **Billing 實測**（§1 gate）：跑一輪，驗訂閱 usage 扣、Agent SDK credit 沒動。

### 3.5 安全（red line）
- server bind `127.0.0.1`。
- office API 要 **session token / CSRF token**。
- **檢查 `Origin`**（防本機其他網頁 / 惡意頁面打 `127.0.0.1` 類 API）。
- 預設**不** `bypassPermissions`。
- 若 user 明確要免問才開 bypass，且**必須**配 dedicated minimal settings + restricted tools + restricted cwd。

> `localhost-only` 單獨**不足**。任何本機網頁都可能打 127.0.0.1；token + Origin 檢查為最低要求。

---

## 4. Phase 2（v1 四軸 relay / 送出 / 權限 / daily 全穩後才做）

- **多行 input**：bracketed paste（包 `\x1b[200~` … `\x1b[201~`，強迫 Ink 視為單次貼上）。**實測 Ink 確實吃、且其後 `\r` 仍正常提交**後才開。
- **乾淨 transcript**：
  - 優先 **client 端讀 xterm.js 的 screen buffer**——xterm.js 本身就是 grid buffer，不必後端再養一份 pyte（重工兩份 emulator）。
  - turn-end 偵測（連續靜默 + prompt box pattern）只當**輔助**，**不**當 v1 gating——長 tool run / 網路等待 / 模型停頓會誤判，pattern 還綁死 TUI 版面，claude 改版即破。
- agy 的「後端 120×40 virtual grid + 100% 過濾」原理對但放錯階段（這就是 phase-2 parser），且「100%」過度宣稱——降為 phase-2 選項，且改 client 端做。

---

## 5. Review 整合紀錄（誰提了什麼 / 怎麼處置）

| 來源 | 建議 | 處置 |
|---|---|---|
| Claude | 9 項疑慮（TUI scraping / turn-detect / 送出 / 權限 blast radius / trust / MCP / nested / 版本漂移 / billing 驗證） | 全數保留為設計約束 |
| Codex | pivot 成 persistent PTY terminal member、drawer 做 terminal pane、transcript 延後、安全 red line、preflight smoke、codex `--no-alt-screen` | **採用為主軸** |
| Claude 補 | claude 無 inline → terminal pane 對 Claude 強制；API 改 WebSocket raw relay + resize；terminal pane 讓預設不 bypass 可用 | 併入 §2 §3.2 §3.5 |
| Gemini(agy) #2 sandbox（`CLAUDE_CONFIG_DIR` + pop nested env + 無 MCP） | **採用** → §3.1（補 keychain auth 註記） |
| Gemini(agy) #3 bracketed paste 多行 | **採用但延後** → §4（實測後開） |
| Gemini(agy) #1 後端 virtual grid buffer | 原理對但 phase-2 且改 client 端 → §4 |
| Gemini(agy) #4「isatty 100% flat-rate」 | **駁回確定性** → §1 改強制實測 |

---

## 6. 版本漂移風險

整套耦合 claude `2.1.158` 的 TUI 渲染 + submit-key 行為。CLI 更新可能 silently 破壞 relay / 送出。需：CLI 版本記錄 + preflight smoke 當回歸測試（升級後重跑 §3.4）。

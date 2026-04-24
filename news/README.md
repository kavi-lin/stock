# News Protocol — 即時新聞分析模組

這是 AI 投資委員會的**新聞分析子系統**，提供三種模式分析美股相關新聞並把結論 patch 到其他 protocol 的 cache。Claude 的執行 instruction 是 `news_protocol_v2.md`；本文檔說明**為什麼**這樣設計、**團隊結構**、**檔案關係**、**歷史版本演進**。

---

## 三種模式

| 模式 | 觸發 | 耗時 | 用途 |
|---|---|---|---|
| **FLASH** | 貼新聞標題/連結 | ~3 min | 看到重大消息立即分析，`review_status: pending`，**不 patch cache** |
| **DIGEST** | 「新聞分析 DIGEST」/「更新新聞 cache」 | ~5-10 min | 盤前盤中 RSS 寬掃描→漏斗→深度辯論，全面更新 cache |
| **REVIEW** | 「新聞分析 審核 [headline]」 | ~3 min | 對 pending FLASH 重新正式委員會審核，通過才 patch cache |

---

## 團隊結構（6 人）

| Agent | 執行模式 | 職責 | 核心關注 |
|---|---|---|---|
| **News Collector** | inline | 蒐集 RSS / WebFetch 原文，確認來源可信度 | Source credibility、時效性、去重 |
| **Bull Analyst** | Stage 1 inline / **Stage 2 subagent batch** | 多頭角度解讀 | 受益族群、催化劑類型、短中期驅動 |
| **Bear Analyst** | Stage 1 inline / **Stage 2 subagent batch** | 空頭角度解讀 | 受損族群、風險傳導、尾部風險 |
| **Sector Analyst** | Stage 1 inline / **Stage 2 subagent batch** | 產業分析師視角 | 上下游傳導、供應鏈 2 階效應、受影響個股 |
| **Macro/Policy Expert** | Stage 1 inline / **Stage 2 subagent batch** | 財經/政策專家 | Fed 路徑、殖利率、匯率、地緣、歷史類比 |
| **News Arbiter** | inline | 仲裁辯論、加權評分、執行 cache patch | 綜合判斷、cache 一致性 |

### V2.1 執行模式說明

- **Stage 1**（shallow triage，30-50 則 × 4 agent snap ≤30 字）保持 inline — subagent 啟動 overhead 對 120 個短 snap 不划算
- **Stage 2**（deep debate，≤5 則 × 4 agent 完整辯論）改用 **per-agent batch subagent**：每位 agent 一個 Agent tool call，一次看全部晉級項目、輸出 N 份自己視角的分析，彼此不看對方輸出
- **目的**：消除同 model 序列產生 4 視角的 anchoring 風險，與 `investment_protocol_v4_8` Phase 2 fan-out 同邏輯
- **REVIEW** 同樣套用 subagent 模式（1 則 × 4 agent 擴展）

---

## 執行流程（DIGEST 為例）

```
Stage 1 Triage              Stage 2 Deep Debate        Phase 3 Arbiter       Phase 4 Patch
─────────────────           ─────────────────────      ──────────────        ───────────────
RSS raw.json                4 subagent parallel        加權計算              sector_intel.json
→ 30-50 則 shallow          Bull / Bear / Sector       per news_type         phase0.json
→ 4 agent snap              / Macro                    weights table         news_logs/digest.json
→ |score|≥3 / binary        ≤5 則 full text            verdict output        validator → rc=0
→ 晉級 ≤5 則                subagent_isolated=true     cache_action          → MD 報告
```

---

## 為什麼要分 Stage 1 / Stage 2？

**V1 的痛**：3 人委員會對 30 則新聞每則都深度辯論 → 單次 DIGEST 燒 ~45k tokens、10+ 分鐘。

**V2 兩階段漏斗**：
- Stage 1 用 RSS 原始摘要做便宜寬掃描（shallow score 只是 4 個 snap 的加權），快速過濾低影響雜訊
- Stage 2 只對高影響 / binary 新聞做完整 WebFetch + 四方深度辯論
- 合計 ~23k tokens（省 50%），時間也從 10+ min 降到 5-8 min

**硬上限 Stage 2 ≤ 5 則**：超過這個量深度辯論的 marginal value 大幅遞減（top 5 通常吃掉當日 80% 影響力）。

---

## 為什麼 cache patch 只在 Stage 2 / REVIEW 執行？

| 階段 | review_status | Patch cache? | 原因 |
|---|---|---|---|
| Stage 1 shallow | — | ❌ | snap 30 字沒經過完整辯論，品質不穩 |
| Stage 2 deep（DIGEST）| `reviewed` | ✅ | 4 agent 完整辯論 + Arbiter 仲裁 |
| FLASH deep | `pending` | ❌ | 使用者主動貼的單則，還沒經過正式委員會 |
| REVIEW deep | `reviewed` | ✅ | 已對 FLASH 做完整擴展辯論 + 重新裁決 |

**設計哲學**：Cache 是下游 protocol（sector / investment）的共用事實，一旦被污染就會放大錯誤決策。只允許**四方深度辯論 + Arbiter 仲裁通過**的結論進 cache。

---

## Arbiter 加權哲學

基礎權重 4 方各 25%，但不同 news_type 應該給不同 agent 更多話語權：

- **FOMC / CPI / NFP** → Macro 50%（政策/數據事件，Macro/Policy Expert 最有發言權）
- **戰爭 / 關稅 / 制裁** → Bear 30% + Macro 40%（地緣事件下行風險不對稱）
- **財報 / 併購** → Sector 40%（具體產業衝擊 > 宏觀解讀）
- **Fear & Greed / VIX spike** → Bull / Bear 各 30%（情緒事件看多空張力）

實際權重表見 `news_protocol_v2.md` §ARBITER 加權規則。

---

## 檔案結構

```
news/
├── README.md                        ← 本文件（說明、哲學、版本歷史）
├── news_protocol_v2.md              ← Claude instruction（純執行規則）
├── digest_output_schema.md          ← digest.json shape 唯一事實來源
├── fetch_news_rss.py                ← RSS 抓取腳本
├── scripts/
│   ├── validate_digest_output.py    ← schema validator（rc=0 才可進 MD 階段）
│   └── (salvage_digest.py 已移至 archive/)  ← API stream idle timeout 後的搶救工具
├── news_logs/
│   ├── YYYY-MM-DD_raw.json          ← RSS 原始資料
│   └── YYYY-MM-DD_digest.json       ← 分析結果 cache（shallow + deep）
└── scan_logs/
    └── news_YYYYMMDD_HHMMSS.log     ← protocol 執行 stream-json log

archive/old_protocols/news/
└── news_protocol_v1.md              ← V1 歸檔

reports/
├── YYYY-MM-DD_news_digest.md        ← DIGEST 最終報告
└── YYYY-MM-DD_HHMM_news_flash.md    ← FLASH 最終報告
```

---

## 與其他 Protocol 的關係

```
news_protocol_v2（任意時間觸發）
    ↓ patch（只有 Stage 2 / REVIEW 結論）
sector_intel.json  ← sector_protocol_main 讀取（top_catalysts）
phase0.json        ← investment_protocol_v4_8 讀取（macro_backdrop + binary_risks）

不需要重新跑 sector_protocol 或 investment_protocol —
下次執行時自動 pick up 更新後的 cache。
```

---

## 觸發情境速查

| 情境 | 模式 | 流程 |
|---|---|---|
| 看到重大新聞標題 | FLASH | 直接 WebFetch → Deep Debate → pending |
| 開盤前更新市場氣氛 | DIGEST | RSS → Triage → Deep Top 5 → reviewed |
| 針對個股查近期新聞 | FLASH | 「新聞分析 FLASH NVDA 近期動態」→ pending |
| Dashboard 決策卡片 📰 | FLASH | 複製 prompt → 貼回 CLI → pending |
| Dashboard 新聞頁「送審」 | REVIEW | 複製 prompt → 擴展辯論 → reviewed + cache patch |
| 盤中突發事件 | FLASH → REVIEW | 先 FLASH 快讀 → 需要時再送審正式入 cache |

---

## Token 預算

| 項目 | V1 | V2 |
|---|---|---|
| Web 請求 | ~30k（6 WebSearch） | ~8k（5 WebFetch） |
| RSS 解析 | 0 | ~3k（腳本預處理） |
| Agent 辯論 | ~15k（3 人） | ~12k（Stage 1 輕量 + Stage 2 4 人深度） |
| **DIGEST 合計** | **~45k** | **~23k** |
| **FLASH** | ~8k | ~5k |
| **REVIEW** | n/a | ~4k（只擴展 1 則）|

---

## 容錯機制

### Fan-Out 失敗（Stage 2 subagent）

| 情境 | `fanout_mode` | 處理 |
|---|---|---|
| 4 agent 全成功 | `PER_AGENT_BATCH` | 正常 |
| 1-2 agent timeout / malformed | `PARTIAL_FALLBACK` | 失敗者 inline fallback，confidence 上限 0.5，`degraded_agents[]` 列出 |
| 3-4 agent 失敗 | `FULL_FALLBACK` | 整批 inline；BULLISH verdict 強制降級（避免品質下滑仍給強 signal） |
| 1 則（FLASH） | `INLINE` | 直接 inline 四視角（subagent overhead 不划算） |

### API Stream Idle Timeout

歷史上 Phase 4 寫 digest.json 時發生過兩次：Claude 用單一超大 tool call（Bash heredoc 或 Write）噴整包 10K+ token JSON → Anthropic API 的 stream idle watchdog 觸發 → partial response 中斷、rc=1、token 全浪費。

**預防**（protocol Phase 4 強制規則）：
- ❌ 禁用 `Bash` + heredoc 一次灌入整個 JSON
- ❌ 禁用單一 `Write` 把整檔當單一字串 argument
- ✅ 必須分塊 Write（skeleton → append 5-10 筆 verdicts → 封檔）
- ✅ 推薦用 `news/scripts/digest_append_deep.py` merge script（每 tool call input_json 都很小）

**萬一撞上**：不要重跑 protocol（會再燒同樣 tokens），改跑：
```bash
python3 archive/salvage_digest.py
```
從 `scan_logs/news_*.log` 重組 digest.json（零 API 成本）。Salvage 只能救 deep verdicts — shallow 的 per-item 4 view snap 只存在加密 thinking block 裡無法還原。

### Server-Side Hard Kill

`dashboard_server.py` 對 news/flash/review 各自設 12/10/10 分鐘硬殺（其他 protocol 共用 25 分鐘預設）。news DIGEST 正常 1-2 分鐘，跑超過 10 分鐘一定是病態，直接 kill 避免燒 tokens。

---

## 版本演進

### V2.1（現行）
- **Stage 2 / REVIEW 改 per-agent batch subagent**：Bull/Bear/Sector/Macro 各自一個 Agent tool call，一次分析全部晉級項目，彼此 context 隔離 — 消除同 model 序列產生 4 視角的 anchoring
- **Phase 4 digest.json schema 抽離**至 `digest_output_schema.md`，配 `validate_digest_output.py` 驗證（rc=0 才可進 MD 階段）
- **新欄位**：`fanout_mode` / `degraded_agents` / `subagent_isolated` sentinel
- **🚨 Phase 4 寫入防護**：禁止 Bash heredoc / 禁止單一超大 Write，必須分塊；配 `archive/salvage_digest.py` 救援工具
- **server-side hard kill**：news/flash/review 獨立 timeout override

### V2.0
- 兩階段漏斗：Stage 1 RSS 便宜寬掃描 → TOP N → Stage 2 WebFetch 深度辯論
- Team 3 → 5（新增 Sector Analyst + Macro/Policy Expert）
- Triage 表給使用者（保留人類否決/加碼權）
- Cache patch 只在 Stage 2 執行

### V1.0（已歸檔 `archive/old_protocols/news/`）
- FLASH / DIGEST 雙模式
- Bull vs Bear 強制辯論（只 2 agent）
- Arbiter 仲裁 + net_impact_score
- 自動 patch sector_intel / phase0 / digest

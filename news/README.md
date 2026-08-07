# News Protocol — 即時新聞分析模組

這是 AI Investment Committee 的**新聞分析子系統**，提供三種模式分析美股相關新聞並把結論 patch 到其他 protocol 的 cache。Claude 的執行 instruction 是 `news_protocol_v2.md`；本文檔說明**為什麼**這樣設計、**團隊結構**、**檔案關係**、**歷史版本演進**。

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
| **Stage 1 Triage** | **deterministic script**（`scripts/stage1_triage.py`，0 LLM） | block / dedup / credibility / news_type / score / snap / 晉級 gate | 噪音過濾、template dedup、advancement gate |
| **News Collector** | inline | WebFetch 晉級項目原文，確認來源可信度 | Source credibility、時效性 |
| **Bull Analyst** | **Stage 2 subagent batch** | 多頭角度解讀 | 受益族群、催化劑類型、短中期驅動 |
| **Bear Analyst** | **Stage 2 subagent batch** | 空頭角度解讀 | 受損族群、風險傳導、尾部風險 |
| **Sector Analyst** | **Stage 2 subagent batch** | 產業分析師視角 | 上下游傳導、供應鏈 2 階效應、受影響個股 |
| **Macro/Policy Expert** | **Stage 2 subagent batch** | 財經/政策專家 | Fed 路徑、殖利率、匯率、地緣、歷史類比 |
| **News Arbiter** | inline | 仲裁辯論、加權評分、執行 cache patch | 綜合判斷、cache 一致性 |

### V2.3 執行模式說明

- **Stage 1**（triage）**全 deterministic**：`scripts/stage1_triage.py` 做 hard-block、headline-template dedup、credibility、news_type、方向 `shallow_score`、獨立 `materiality_score`、genre penalty、事件/來源多樣性及 4-view template snaps，寫 `YYYY-MM-DD_triage.json`。LLM **不讀 raw.json 全文**；`build_digest_packet.py` 只交付 Stage 2 + shallow top-10 + slim macro/theme，並補 top-15 `headline_zh`
- **Stage 2**（deep debate，≤5 則 × 4 agent 完整辯論）**per-agent batch subagent**：每位 agent 一個 Agent tool call，一次看全部晉級項目（每篇截 3000 chars）、輸出 N 份自己視角的分析，彼此不看對方 output
- **Phase 3–4 deterministic finalize**：LLM 只寫 compact `YYYY-MM-DD_debate.json`；`finalize_digest.py` 統一計分、裁決、組 digest、validator、idempotent cache patch 與 Markdown render
- **REVIEW** 同樣套用 subagent 模式（1 則 × 4 agent 擴展）

---

## 執行流程（DIGEST 為例）

```
Stage 1 Triage (script)     Stage 2 Deep Debate        Compact judgment      Finalizer
─────────────────────       ─────────────────────      ──────────────        ───────────────
fetch_all_news.py           4 subagent parallel        加權計算              sector_intel.json
→ stage1_triage.py          Bull / Bear / Sector       per news_type         phase0.json
  (block/dedup/score        / Macro                    lane JSON only        score + verdict
   /snap/gate, 0 LLM)       ≤5 則 × ≤3000 chars        no math/render        digest/cache/MD
→ 晉級 ≤5 則                subagent_isolated=true     one judgment Write    validator → rc=0
```

---

## 為什麼要分 Stage 1 / Stage 2？

**V1 的痛**：3 人委員會對 30 則新聞每則都深度辯論 → 單次 DIGEST 燒 ~45k tokens、10+ 分鐘。

**V2 兩階段漏斗**：Stage 1 寬掃描過濾雜訊 → Stage 2 只對高影響 / binary 新聞做完整 WebFetch + 四方深度辯論。

**V2.2 把 Stage 1 完全 script 化**：V2.0-2.1 的 Stage 1 仍由 LLM 讀整包 raw.json（~287KB ≈ 70K tokens）手寫 snaps；`stage1_triage.py` 上線後這些全 deterministic，LLM 只讀 top-25 摘要 + 補 top-15 中文標題。DIGEST 單跑 ~110K → **~35-40K tokens**。

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
├── debate_input_schema.md           ← LLM → deterministic finalizer 最小契約
├── fetch_all_news.py                ← orchestrator：4 fetcher 平行（RSS / Finnhub / FMP / SEC EDGAR）
├── fetch_news_rss.py                ← RSS 抓取腳本
├── scripts/
│   ├── stage1_triage.py             ← Stage 1 deterministic triage（block/dedup/score/snap/gate，0 LLM）
│   ├── build_digest_packet.py        ← compact Stage 2 packet（triage + slim macro/theme，0 LLM）
│   ├── finalize_digest.py           ← score/assemble/event append/validate/cache/render
│   ├── news_event_store.py          ← append-only JSONL + projection/migration/rollback
│   ├── news_cache_projection.py     ← reviewed event → sector/phase0 idempotent projection
│   ├── validate_digest_output.py    ← schema validator（rc=0 才可進 MD 階段；cross-check triage.json）
│   ├── build_structural_watchlist.py← Phase 4.5 structural watchlist（daily_update Step 7）
│   └── (salvage_digest.py 已移至 archive/)  ← API stream idle timeout 後的搶救工具
├── news_logs/
│   ├── YYYY-MM-DD_raw.json          ← 4 源合併原始資料
│   ├── YYYY-MM-DD_triage.json       ← Stage 1 script 輸出（shallow_verdicts top-50 + stage2_items）
│   ├── YYYY-MM-DD_debate.json       ← Stage 2 compact lane judgments
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
phase0.json        ← investment_protocol_v5_0 讀取（macro_backdrop + binary_risks）

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

| 項目 | V1 | V2.0-2.1（實測） | V2.3 目標 |
|---|---|---|---|
| Stage 1 triage | n/a | ~70k in（LLM 讀整包 raw.json）+ ~6k out | **~2k**（compact packet） |
| Web 請求 | ~30k（6 WebSearch） | ~8k（5 WebFetch） | **~5k**（packet URL + 每篇 3000 chars） |
| Stage 2 辯論 | ~15k（3 人） | ~32k in（4 subagent × full bundle）+ ~8k out | **~12-16k**（adaptive N + bundle cap） |
| Phase 3-4 + MD | — | ~8k（shallow 20 卡） | **~1-2k**（只產 compact judgment；其餘 0 LLM） |
| **DIGEST 合計** | **~45k** | **~110k+** | **~15-25k**（待 10 場 telemetry 驗證） |
| **FLASH** | ~8k | ~5k | ~5k |
| **REVIEW** | n/a | ~4k | ~4k |
| **TRIAGE（standalone）** | n/a | ~75k | **~5k**（script + top-15 headline_zh） |

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

歷史上 Phase 4 手寫 digest.json 曾因超大 JSON 觸發 stream idle watchdog，並重複消耗 output token。

**現行預防**：LLM 只寫 compact debate input；`finalize_digest.py` 在本機 deterministic 產生 digest 與 Markdown，不再串流大型 artifact。stable `event_id` ledger 讓同一 debate 重跑不會重複 patch macro/risk。

**萬一撞上**：不要重跑 protocol（會再燒同樣 tokens），改跑：
```bash
python3 archive/salvage_digest.py
```
從 `scan_logs/news_*.log` 重組 digest.json（零 API 成本）。Salvage 只能救 deep verdicts — shallow 的 per-item 4 view snap 只存在加密 thinking block 裡無法還原。

### Server-Side Hard Kill

`dashboard_server.py` 對 news/flash/review 各自設 12/10/10 分鐘硬殺（其他 protocol 共用 25 分鐘預設）。news DIGEST 正常 1-2 分鐘，跑超過 10 分鐘一定是病態，直接 kill 避免燒 tokens。

---

## Structural Watchlist（Phase 4.5 — daily 自動，V2.19 設計）

**目的**：把連續觀察到的 `top_catalysts[]` structural keyword 命中彙整成 watchlist，給 Dashboard「結構性轉變候選」tile + user 提早警覺。**不入 Phase 3 modulation** — 純展示用 metadata，投資 protocol 不讀此檔做決策。

**觸發**：`daily_update.sh` Step 7 自動跑 `python3 news/scripts/build_structural_watchlist.py`（deterministic，LLM 不參與；失敗 non-fatal）。

| | 路徑 |
|---|---|
| **輸入** | `news/news_logs/*_digest.json`（過去 30 天）+ `news/news_logs/sector_intel.json` |
| **輸出** | `news/news_logs/structural_watchlist.json`（atomic temp + rename） |

**STRUCTURAL_KEYWORDS（14 條 whitelist，narrow signal）**：

```
"sold out", "capacity constrained", "structural deficit", "supercycle",
"super-cycle", "supply tight", "shortage", "all-time high demand",
"booked through", "fully allocated", "production at capacity",
"capacity expansion", "供不應求", "結構性短缺"
```

廣義 sentiment keyword（"strong demand"、"growth"）刻意排除。

**Decay & Hygiene**：

| 規則 | 條件 | 行為 |
|---|---|---|
| Hit window | 只計 `last_observed - 14d` 內 keyword hits | `hit_count_14d` 不含過期 hit |
| Eviction | `(today - last_observed_date) > 21d` | candidate 自動剔除 |
| First-hit gate | 第一次出現不入 watchlist | ≥2 獨立 source 同 ticker / 14d 內才入 |
| Source dedup | 同新聞重貼（url stem 同 OR headline 8-gram 重疊） | 計 1 hit |
| Sector aggregation | 個股入榜後 sector 列 hot | sector 層級同樣 21d eviction |

**Output schema**：見 `structural_watchlist.json` 實檔（`as_of` / `decay_rules` / `candidates[]`（ticker, sector, keyword_hits, hit_count_14d, source_credibility_max, first/last_observed, days_since_last_hit）/ `sectors[]` / `stats`）。

**V2.20 規劃**：earnings-analyst structural_shift tier tie-breaker（signal 1/3 + watchlist hit → CANDIDATE 門檻降 1）；需先 backtest。

---

## 版本演進

### V2.3（現行）
- **BINARY 語意修正**：BINARY 只代表有明確結果分支與事件日期；Bull/Bear 天生異號造成的 score spread 只進 `debate_note`。非 binary verdict 由 `arbiter_rules.py` 依 net score ±0.75 deterministic 驗證。
- **Stage 1 materiality 分離**：方向分數不再兼任重要性；新增 source origin、event type、數值/實質事件、genre penalty、event clustering 與 source diversity。安靜日不強迫湊滿 5 則。
- **Validator semantic gate**：2026-08-06 起要求 `arbiter_rule_version=V2.3`，驗證 verdict/binary metadata、published ISO 與 cache flags。
- **Deterministic finalizer**：LLM output 收斂為 compact four-lane judgment；共用 Arbiter 公式、digest/MD assembly、validator 與 idempotent cache patch 全下沉 script。

### V2.2
- **Stage 1 全 deterministic**：protocol 接上 `scripts/stage1_triage.py`（v3.14.3 已具備 block / template-dedup / credibility downgrade / rule-based news_type / score / snap / gate），LLM 禁讀 raw.json 全文、禁手工 triage — DIGEST 單跑 ~110K → ~35-40K tokens
- **Stage 2 bundle cap**：每篇全文截 5000 chars（4 subagent 各收一份，重複成本 ×4）
- **MD 報告 Shallow Digest 20 → 10**，snaps 照抄 triage.json（與 digest.json 一致）
- **server `triage` protocol** 改 script-first：LLM 只補 top-15 headline_zh（舊 prompt 的 `verdicts` shape 與 validator 期望的 `shallow_verdicts` 衝突，一併修正）
- Phase 4.5 structural watchlist spec 從 protocol 移到本 README（LLM 不執行，不必佔 protocol context）

### V2.1
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

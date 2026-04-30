# Short-Term Recommendation System — 規劃

> **目標**：在 Dashboard 動能分析頁加入「短期 (1-15 天) 個股趨勢推薦」+「細粒度產業熱度推薦」，補足 investment_protocol（中期 3-6 月）的短期空白。
> **狀態**：規劃中，未開工
> **約束**：**不改 investment_protocol 任何規則**（V4.8.1 dual_fetch 之外不動）。所有新功能並行運作，不污染既有決策。
> **本文件來源**：整合 sonnet 初版規劃 + 本次對話的 backtest 發現與架構修正。

---

## 1. 解決什麼問題

| 痛點 | 來源 |
|---|---|
| 想知道「下週這檔會走到哪」 | 使用者直接需求 |
| 想看「太空 / 核能 / 量子」這種細粒度主題熱度，不要傳統 11 大類 | 使用者直接需求 |
| theme-detector 與 momentum-monitor 各自獨立，沒有串接 | 既有缺口 |
| Finnhub upgrade / insider / news 端點完全閒置 | 既有浪費 |
| Dashboard momentum 頁沒有主題層級面板，只有個股表格 | 既有缺口 |
| `分析 [TICKER]` protocol 設計給 3-6 月，沒覆蓋 1-15 天視角 | 結構性 |

---

## 2. 架構決策（已定）

### 2.1 兩個獨立 skill，不合併

| Skill | 範圍 | 時間維度 |
|---|---|---|
| `short-term-target` | 單股目標價預測 | 1d / 5d / 15d |
| `thematic-screener` | 主題層級熱度 + 主題內個股 movers | 1-3 個月（主題）+ 短期（個股） |

**為何不合併**：兩者職責不同，short-term-target 是計算題（model-based），thematic-screener 是聚合題（screener + dedup）。合併會造成 SKILL 邊界模糊。

### 2.2 Dashboard 兩個獨立分區（不合成）

```
Dashboard / Momentum 頁

[A] 「中期熱題材」分區
    顯示 Top 5 themes，附 lifecycle / heat / FRED-regime alignment
    時間視角：1-3 個月
    來源：theme-detector + thematic-screener
    
[B] 「短期 movers within hot themes」分區
    對 [A] Top 5 themes 的代表股，跑 short-term-target
    顯示 1d / 5d / 15d 預測 + insufficient_data 標記
    時間視角：1-15 天
    來源：short-term-target (per ticker)
```

**為何不合成單一分數**：使用者要做不同決策（「現在該不該買」vs「這主題是不是值得 watch」），用單一綜合分會讓推薦不可解讀。

### 2.3 重用現有基礎建設

| 元件 | 用途 |
|---|---|
| `skills/finnhub-client/dual_fetch.py` | thematic-screener 直接讀 `data/<DATE>/<TICKER>.json` 的 `scoring` 段，不另起爐灶。`_audit` 仍嚴禁進入任何輸出 |
| `skills/theme-detector/` | thematic-screener 為其下游 client |
| `skills/fred-macro/` | thematic-screener 顯示 FRED regime（不做硬編 mapping） |

### 2.4 明確不做的事

| 不做 | 原因 |
|---|---|
| 將不同時間維度（theme heat / momentum / Finnhub catalyst）合成單一分數 | 推薦不可解讀；使用者需要按時間維度做不同決策 |
| 硬編 `macro_theme_map.yaml`（FRED regime → 主題加分/扣分） | 未驗證的民俗法則；落入 n=1 過擬合陷阱（參見本次 backtest 結論） |
| 用 Finnhub upgrade / insider 直接加減分（+2/-2 機制） | 未驗證；先**只顯示**事件，不打分。等樣本累積後再評估 |
| 影響 `investment_protocol_v4_8.md` 任何決策 | V4.8 不動共識 |
| 上 dashboard 不標 EXPERIMENTAL | 推薦未驗證，需誠實標示 |

---

## 3. 新增主題（cross_sector_themes.md）

### 加入

| 主題 | 代表股 | 為何加 |
|---|---|---|
| **Space Economy**（從 Defense & Aerospace 拆出） | RKLB, ASTS, LUNR, MAXR, GSAT, BWXT | 使用者明確要；驅動因子（衛星、發射、地面站）跟 Defense 不同 |
| **Nuclear Energy** | CCJ, BWXT, CEG, VST, OKLO, SMR, LEU | 使用者明確提到；非 tech 平衡樣本 |
| **Quantum Computing** | IONQ, RGTI, QBTS, QUBT | 動能波動大，獨立追蹤有價值 |
| **Robotics & Automation** | ISRG, TER, ONTO, NVEI, PATH（ETF: BOTZ, ROBO） | 驅動因子與 AI Infra 不同（製造業、醫療機器人） |

### 不加（從 sonnet 初版砍）

| 主題 | 不加原因 |
|---|---|
| AI Infrastructure | VRT / SMCI / EQIX / DLR 已散在現有主題（Industrial AI / Tech / REIT），重複定義會稀釋 |
| Water / AgTech | 目標股票 universe 太小（< 5 主流標的），ETF 流動性弱，現階段不值得獨立 |

### v2 候選（等樣本累積再評估）

- Healthcare Innovation（基因治療 / GLP-1 衍生）
- Materials Cyclicals（銅 / 鋰 / 稀土）
- Fintech（支付 / 數位銀行）
- 平衡用：避免新主題清單**全是 tech**，加深既有 sample bias

---

## 4. 實作順序

### Step 1 — `short-term-target` skill（P1，先做）

**規格**（已在前次對話確認）：

```bash
python3 skills/short-term-target/scripts/predict.py NVDA
# 預設輸出 1d / 5d / 15d 三個 horizon
```

**輸出 JSON**（每個 horizon 獨立判定資料充足性）：
```json
{
  "ticker": "NVDA",
  "as_of": "ISO timestamp",
  "current_price": 195.32,
  "horizons": {
    "1d": {
      "status": "ok | insufficient_data",
      "target_central": ..., "target_low": ..., "target_high": ...,
      "confidence": 0.0-1.0,
      "drivers": [...],
      "data_sufficiency": {...}
    },
    "5d": {...},
    "15d": {...}
  },
  "stop_suggestion": ...,
  "invalidation": "...",
  "global_warnings": []
}
```

**資料不足規則**：

| Horizon | 必要資料 | 不足判定 |
|---|---|---|
| 1d | 即時 quote + 1d ATR + 過去 24h news | quote > 1h 舊 OR news > 8h 舊 OR ATR < 5d 樣本 → `insufficient_data` |
| 5d | 5d 動能基準 + 24-48h news + sector heat | sector_intel > 3d 舊 OR news > 24h 舊 OR 5d 量價缺 → `insufficient_data` |
| 15d | 15d realized vol + sector heat 持續性 + 多週 news | sector_intel > 7d 舊 OR 15d candle 缺 OR 3 週內 news < 5 → `insufficient_data` |

**禁止**：任何 horizon 在資料不足時偽造數值。

**model 構成（v1 簡單版）**：
```
target_central = current * (1 + α × normalized_news + β × sector_heat_factor + γ × momentum_score)
target_range = target_central ± k × ATR_n_days
confidence = f(News confidence, sector heat persistence, ATR stability)
```
α / β / γ 一開始 hardcode 經驗值。**等 backtest 累積樣本後再校準**。

**檔案結構**：
```
skills/short-term-target/
  SKILL.md
  README.md
  CHANGELOG.md
  scripts/predict.py
  cache/                # 4h TTL
```

**估時**：1.5-2 天

---

### Step 2 — 新增主題（P1，純資料工）✅ 完成 2026-04-25

**實作後校正**：原計畫 4 + §12.F 加 2 = 共 6 個。實際盤點 cross_sector_themes.md 發現：
- **Nuclear Energy 已存在**（既有 17 主題第 15 個）→ 不重複加
- **Healthcare Defensive 與既有 Healthcare & Pharma 重複**（UNH/JNJ/LLY/PFE 已涵蓋 defensive 需求）→ 不加

**實際新增 4 個主題**（17 → 21）:
- ✅ **Space Economy**（從 Defense 拆 RKLB；含 ASTS/LUNR/MAXR/GSAT 等 14 名）
- ✅ **Quantum Computing**（IONQ/RGTI/QBTS/QUBT 等 11 名，含警示「pure-plays ATR ~8%」）
- ✅ **Robotics & Automation**（ISRG/TER/ABBN/FANUY 等 15 名）
- ✅ **Utilities Defensive**（NEE/DUK/SO/AEP 等 15 名，標明與 Nuclear 區別）

**附帶調整**：
- Defense & Aerospace static_stocks 移除 RKLB（補進 TXT）
- ETFs 也同步遷移：ROKT/ARKX 從 Defense 搬到 Space
- Summary Table 更新（17 → 21）
- Overlap Matrix 加 8 行新 cross-theme 關係（含 BWXT 三重歸屬說明）

---

### Step 3 — `thematic-screener` skill（P2，簡化版）✅ 完成 2026-04-25 (v1.47.0)

**實作差異**：原計畫 sub-industry concentration 用 GICS lookup；實作改用 **theme-membership** 作為 v0.1 proxy（GICS 表延後 v0.2）。Step 5 outcome log writer **內含**於本 Step（不另外做檔案），data/recommendations/ 從 day 1 開始累積。



**規格**：

```bash
python3 skills/thematic-screener/scripts/screen.py
# 輸出 Top 5 hot themes + each theme 的 Top 3-5 個股 movers
```

**處理流程**：
```
1. theme-detector 取得 themes[].heat / lifecycle (現有)
2. FRED regime 顯示（不影響打分）
3. Top 5 themes 取 constituent tickers (從 cross_sector_themes.md static list)
4. 對每個 ticker:
   a. 嘗試從 dual_fetch data/<DATE>/<TICKER>.json 讀 scoring（無則 skip）
   b. 呼叫 short-term-target.predict()
5. sub-industry 集中度 dedup:
   - 同主題內，相同 GICS sub-industry ≥ 2 → 只保留 short-term-target 信心最高的
6. 輸出 ranked list
```

**輸出 JSON**（含 EXPERIMENTAL 標記與 outcome tracking metadata）：
```json
{
  "as_of": "ISO timestamp",
  "experimental": true,
  "fred_regime": {...},
  "themes": [
    {
      "name": "Nuclear Energy",
      "heat": 78.3,
      "lifecycle": "Mature",
      "top_movers": [
        {
          "ticker": "CEG",
          "short_term": {...short-term-target output...},
          "concentration_warning": null
        }
      ]
    }
  ]
}
```

**內含 sub-industry 集中度檢查**：source 是 NTRS+STT 同日同產業跌的 backtest case。

**估時**：1.5 天

---

### Step 4 — Dashboard 兩分區（P3）✅ 完成 2026-04-25 (v1.49.0)

**實作位置**：
- `bridge.py` — 加 `load_tactical_recommendations()` + 注入 `data.tactical`
- `Dashboard/radar.html`（新頁面 85 行，sidebar 「短期雷達」icon=radar）
- `Dashboard/page-radar.js`（260 行 render 邏輯）
- `Dashboard/utils.js` / `i18n.js` / `style.css` 增量更新

**§11.D 顯示規則全達成**：EXPERIMENTAL badge、horizon range（不只 mid）、confidence breakdown 7 項、drivers 4 sources、invalidation box、concentration warning、trading meta 完整。FRED regime banner（§11.E 軟版）+ 累積天數 + KPI hint。

**桌面 only / 預設展開第 1 個主題**（per user 決定）。



修改 `Dashboard/momentum.html` + `page-momentum.js`：

```
[現有] 個股 momentum 表格（保留不動）

[新增 A] 「中期熱題材」分區（卡片式）
  - Top 5 themes
  - 每張卡片：name / heat / lifecycle / FRED alignment / 點開展開 movers
  - 標 EXPERIMENTAL + 樣本數 + N 週運行天數

[新增 B] 「短期 movers」分區
  - 對 [A] 主題的代表股
  - 1d / 5d / 15d 預測 bar
  - insufficient_data 顯示為灰色 + 「資料不足」tooltip
  - 標 EXPERIMENTAL
```

**前端注意**：
- EXPERIMENTAL 標籤明顯（紅 / 黃色）
- 顯示「v0.1 — 推薦未經 backtest 驗證」字樣
- 顯示推薦自動更新時間

**估時**：1.5-2 天

---

### Step 5 — Outcome tracking log（P3，從 day 1 開始）

**目的**：累積真實預測 vs 實際走勢數據，2-3 個月後可獨立 backtest 整套推薦系統。

**機制**：
- 每次 thematic-screener 執行 → 寫 `data/recommendations/<YYYY-MM-DD>.json`
- 內含每個推薦：theme, ticker, current_price, predictions (1d/5d/15d), confidence, fred_regime
- 每週由排程腳本對照 yfinance 實際走勢，寫 `data/recommendations/outcomes_<YYYY-MM-DD>.json`

**評估腳本**（v1 不用建，等樣本累積後做）：
```bash
python3 investment/scripts/recommendations_postmortem.py --days 60
```
輸出：
- Hit rate (% predictions in correct direction by horizon)
- Mean alpha vs benchmark ETF (XLK / SPY by sector)
- 哪個主題的推薦最準 / 哪個應該下架

**估時**：log 部分 0.5 天；postmortem script 之後再說

---

### Step 7 — Weekend Recalibration Tool（P3，與 Step 5 並行）✅ 完成 2026-04-25 (v1.48.0)

**實作位置**：`skills/short-term-target/scripts/weekly_review.py`（330 行）

**輸出**：`reports/SHORT_TERM_WEEKLY_<DATE>.md` 含 5 段：(1) per-horizon hit rate / bias 表 (2) per-theme 5d alpha 表 (3) worst 5 cases (4) suggested adjustments — 簡單啟發式：hit rate <50% → 建議降權、bias > ±1.5% → 建議調整 alpha_news+gamma_momentum、單主題 hit rate <30% (N≥5) → 建議下架 (5) KPI gate 對照 §6+§12.H。

**Smoke test**: 跑通並正確 graceful handle 「無樣本可評估」狀態（today's logs windows 都還沒到期）。

**規格保持**：tool 只給建議**永不自動覆寫 config**。weights.yaml 完全手動。



**目的**：使用者每週末手動跑一次，看上週表現 + 拿到具體權重調整建議。**無自動覆蓋**，完全人工決定要不要套用。

```bash
python3 skills/short-term-target/scripts/weekly_review.py
# 預設掃過去 7 天 recommendations + outcomes，輸出 markdown 報告
```

**輸出 `reports/SHORT_TERM_WEEKLY_<YYYY-MM-DD>.md` 內含**：

1. **本週基本指標**
   - 推薦數 / 平均 confidence / insufficient_data 比例
   - 各 horizon hit rate (1d / 5d / 15d 各別)
   - 中位 alpha vs benchmark

2. **失敗 case 列表**（最大 negative alpha 5 個）
   - ticker / 預測 / 實際 / driver breakdown
   - 「為什麼錯」自動分析（news 過時？sector heat 高估？ATR 低估？）

3. **Per-horizon 權重調整建議**（基於系統性偏差）
   ```
   1d horizon:
     hit rate: 58% (健康)
     observation: news driver 過熱（新聞 +X 時實際反應只有 0.6X）
     suggested: HORIZON_WEIGHTS["1d"]["alpha_news"] 0.6 → 0.5
     rationale: ...
   ```

4. **配置編輯指引**
   - 直接 link 到 `skills/short-term-target/config/weights.yaml`
   - 顯示當前 vs 建議的 diff
   - 套用後自動 bump `weights_version`

**重點**：建議只是建議，使用者完全控制要不要套用。Tool 不自動覆蓋 config。

**估時**：1 天

---

### Step 6 — `daily_update.sh` 整合（P4，最後）✅ 完成 2026-04-25 (v1.48.0)

新增第 6 步驟到 `daily_update.sh`：
- 檢查 `theme-detector` cache 存在性 + 新鮮度（> 7 天 → 跳過）
- `set +e` 包覆，**失敗不中止整體 daily flow**
- 顯示輸出檔大小確認成功
- 結尾提示加「每週末跑 weekly_review.py」



執行順序：
```bash
./daily_update.sh
  → Breadth / FTD / Top / FRED cache（現有）
  → theme-detector 重跑（如 cache stale）
  → thematic-screener 重跑 → 寫 data/recommendations/
  → Dashboard cache invalidate
```

**估時**：0.5 天

---

## 5. 延後到 v2 的東西

| 延後項 | 條件 |
|---|---|
| `macro_theme_map.yaml` hardcode | 等推薦 outcome 樣本 ≥ 50 跨 regime 後評估 |
| Finnhub upgrade / insider / news event 加分機制 | 等 News lane (r=+0.373) 替代方案驗證 |
| 兩分區合成單一綜合分 | 等使用者實測雙分區後決定是否需要 |
| Water / AgTech / Healthcare / Materials / Fintech 主題 | 等樣本驗證 + 平衡 sample bias 需求出現 |
| 推薦 → 自動下單整合 | 完全不在範圍 |

---

## 6. 驗證策略

### 從 day 1 開始 log

不等系統「驗證後再做」，而是**邊做邊收集樣本**：
- Step 5 的 outcome log 從 thematic-screener 第一次跑就啟動
- 每天累積資料
- 8-12 週後自然累積 50+ 樣本

### 失敗判定

| 條件 | 反應 |
|---|---|
| 8 週後 hit rate < 50%（亂猜水平） | 砍 thematic-screener 整套 |
| 某主題 8 週推薦 < 2% alpha | 從推薦清單下架 |
| insufficient_data 比例 > 70% | 重新評估資料源 / horizon 設計 |

### 與本次對話 backtest 的延續

本次 backtest 已建立的事實：
- News lane r=+0.373（唯一強正向）
- BUY 中位 alpha +3.93% vs SPY（tech-heavy 樣本）
- Sub-industry 集中度是 portfolio-level 真實風險
- 模型在 RISK_ON 強多頭月運作；其他 regime 未驗證

新系統評估時要**特別注意**：
- 別把「強多頭月一切都對」當成 baseline
- 要等到至少經歷一次 SPY 5d window 為負的環境才能宣稱 alpha 為真

---

## 7. 與既有系統的關係

| 系統 | 關係 |
|---|---|
| `investment_protocol_v4_8.md` | **不影響**。並行運作。可在 Phase 5 報告**選擇性**引用 short-term-target 輸出當「短期參考」（v2 才考慮） |
| `dual_fetch.py` | thematic-screener 消費它的 scoring snapshot |
| `theme-detector` | thematic-screener 為其下游 client，不修改 theme-detector 本體 |
| `momentum-monitor` | 仍可獨立使用；但不再是主要推薦來源（thematic-screener 取代其在 Dashboard 的位置） |
| `fred-macro` | thematic-screener 顯示其 regime；**不做** mapping |
| `finnhub-client` (events 端點) | 暫時閒置；v2 評估後再決定是否啟用 |
| `daily_update.sh` | Step 6 整合 |
| `earnings-valuation-forecaster` | 不影響（12mo 視角，與本系統 1-15d 互補） |

---

## 8. 估算

| 項目 | 估時 | API 成本 |
|---|---|---|
| Step 1 short-term-target | 1.5-2 天 | 已在 dual_fetch budget 內 |
| Step 2 主題擴充 | 1-2 hr | 0 |
| Step 3 thematic-screener | 1.5 天 | 重用 dual_fetch + theme-detector cache |
| Step 4 Dashboard | 1.5-2 天 | 0 |
| Step 5 outcome log | 0.5 天 | 0 (yfinance free) |
| Step 6 自動化 | 0.5 天 | 0 |
| **合計** | **~7-9 工作天**（分散執行） | 無顯著增加 |

---

## 9. 開工建議順序

1. **Step 1（short-term-target）先做**：是整套系統的「短期計算核心」，沒它整個 [B] 分區跑不起來
2. **Step 2（新主題）平行做**：純資料工，可零碎時間補
3. **Step 1 完成後** → Step 3（thematic-screener 簡化版） → Step 5 (outcome log) → Step 4 (Dashboard) → Step 6 (自動化)
4. 每個 step 完成都跑 smoke test，並 bump VERSION

### v0.1 完成定義

- short-term-target 能對單股輸出 1d/5d/15d 預測或 insufficient_data
- thematic-screener 能輸出 Top 5 themes × Top 3-5 movers JSON
- Dashboard [A] [B] 兩分區可顯示，明確標 EXPERIMENTAL
- 每天自動寫 `data/recommendations/` cache
- VERSION bump → 1.46.0（Step 1 完）/ 1.47.0（Step 3 完）/ 1.48.0（Step 4 完）

---

## 10. 開工前需確認

- [ ] short-term-target horizon 確認 1d / 5d / 15d（非 1d / 5d / 21d）✅ 已決
- [ ] 不做 macro_map / Finnhub 加分 ✅ 已決
- [ ] 推薦輸出標 EXPERIMENTAL ✅ 已決
- [ ] sub-industry 集中度 dedup 內建 ✅ 已決
- [ ] 是否要先把 Step 1 規格落到 SKILL.md 草稿再開工？（next step）

---

## 🟢 [Gemini Review & Enhancements 2026-04-24]

### 核心優點 (Pros)
1. **數據充足性閘門 (Data Sufficiency Gate)**：設計了嚴格的 `insufficient_data` 判定（如新聞時效要求），有效防止模型在缺乏催化劑時進行盲目數學外推。
2. **解耦並行架構**：不改動核心 `investment_protocol`，作為增量功能運行，保證了系統整體的穩定性與容錯率。
3. **科學的閉環驗證**：從 Day 1 開始 Outcome Tracking 並設定明確的「失敗判定」標準（Hit rate < 50% 則下架），展現了工程嚴謹性。

### 潛在風險 (Risks)
1. **目標價錨定效應 (Price Target Anchoring)**：即使標註 EXPERIMENTAL，具體的 Target 數值仍可能引發使用者的心理暗示，忽略了背後的驅動邏輯。
2. **冷啟動權重偏差**：初期的 α/β/γ 係數為硬編碼，若設定不當，初期預測波動可能過大，影響系統可信度。
3. **過度過濾 (Over-filtering)**：在強勢主題（如 Nuclear）中，往往是整個 Sub-industry 同步噴發，僅保留一個最高信心標的可能會漏掉最強龍頭。

### 改進建議 (Recommended Enhancements)
1. **引入波動率校準 (Volatility-Adjusted Confidence)**：在高波動主題（如 Quantum）中，應根據 ATR 自動下調預測信心，避免在劇震中給出無意義的數值預測。
2. **強化驅動因子顯示 (Driver Visibility)**：在 Dashboard 上除了數值，應顯性化顯示「驅動來源」（如：News Sentiment vs. Sector Heat），將「計算題」轉化為「可解釋的邏輯」。
3. **顯性化失效條件 (Invalidation Logic)**：將 `predict.py` 中的 `invalidation` 條件直接呈現在 Dashboard 推薦旁（例如：Close below $X 则策略失效），協助快速止損。
4. **宏觀防禦開關**：當 FRED `regime_label` 為 `Recession Risk` 時，短期推薦應自動增加防禦性警示，不論模型得分多高。

---

## 11. 對 Gemini Review 的回應與整合

### 風險評估（全採納）

| Gemini 風險 | 採納 | 整合進哪一 Step |
|---|---|---|
| 目標價錨定效應 | ✅ | Step 4 Dashboard 強制 driver / range / invalidation 並列顯示，淡化單一目標價 |
| 冷啟動權重偏差 | ✅ | Step 1 加 **輸出 clamp 規則**（見下方 11.A） |
| 過度過濾漏掉龍頭 | ✅ | Step 3 dedup 規則修正（見下方 11.B）|

### 改進建議（3 全採納 / 1 部分採納）

| 改進 | 採納 | 整合進哪一 Step |
|---|---|---|
| 1. 波動率校準 confidence | ✅ | Step 1 model spec 明確化（11.C） |
| 2. Driver Visibility | ✅ 強採納 | Step 4 Dashboard 強制呈現（11.D） |
| 3. 顯性化 Invalidation | ✅ 強採納 | Step 4 Dashboard 強制顯示（11.D） |
| 4. 宏觀防禦開關 | ⚠️ 拆兩版，採納軟版 | 11.E |

### 11.A — Step 1 輸出 clamp（防冷啟動爆走）

`predict.py` 在輸出前必須套用：

```python
# Hard clamps to prevent cold-start absurd predictions
MAX_PCT_BY_HORIZON = {"1d": 5.0, "5d": 15.0, "15d": 30.0}

for horizon, target in predictions.items():
    cap = MAX_PCT_BY_HORIZON[horizon]
    target_central = clamp(target_central, current * (1 - cap/100), current * (1 + cap/100))
    if target was clamped:
        target.confidence *= 0.7  # 信心懲罰：被 clamp 表示模型過度外推
        target.warnings.append("model_output_clamped")
```

理由：α/β/γ 初期硬編碼可能讓某些 case（極端 News + 極端動能）產生 `target = current * 1.5` 這種數字，dashboard 顯示後完全失去可信度。Clamp 確保**最大可能錯誤**有上界。

### 11.B — Step 3 sub-industry 集中度規則修正

**原本**：同產業 ≥ 2 → 只保留信心最高那個（dedup REMOVE）

**修正**：同產業 ≥ 2 → 全部保留，但每個都加 `concentration_flag`：

```json
{
  "ticker": "CEG",
  "short_term": {...},
  "concentration_flag": {
    "sub_industry": "Independent Power Producer",
    "co_recommendations_in_same_sub": ["VST", "TLN"],
    "warning": "Same sub-industry rec ≥ 2; consider correlated drawdown risk"
  }
}
```

**Dashboard** 在卡片上顯示橘色警示圖示 + tooltip。**由使用者決定要不要分散**，不主動移除。

理由（Gemini 對的）：
- NTRS+STT 是「**同產業同跌**」的 correlated loss
- CCJ+CEG+VST 可能是「**同產業同漲**」的 sector momentum，是 feature 不是 bug
- 一刀切 dedup 會錯失龍頭群

### 11.C — Step 1 confidence 公式明確化

原本：`confidence = f(News confidence, sector heat persistence, ATR stability)` 太抽象

**明確化**：

```python
def compute_confidence(news_conf, heat_persistence, atr_pct, days_horizon):
    # base 信心
    base = 0.5
    
    # News 確定性貢獻 (-0.1 ~ +0.2)
    base += (news_conf - 0.5) * 0.4
    
    # Sector heat 持續性 (0 ~ +0.15)
    base += heat_persistence * 0.15
    
    # ATR penalty: 高波動下 confidence 下降
    # ATR > 5% (e.g. Quantum) → -0.2; ATR < 2% (e.g. utilities) → +0.1
    atr_factor = -(atr_pct - 3.0) / 10
    base += atr_factor
    
    # Horizon penalty: 越遠越不準
    base -= (days_horizon / 100)  # 1d -0.01, 5d -0.05, 15d -0.15
    
    return clamp(base, 0.0, 0.95)  # 永遠不給 1.0 信心
```

效果：
- Quantum (ATR ~8%) 1d 預測：confidence 通常 < 0.4
- Utility (ATR ~1%) 5d 預測：confidence 可達 0.7+
- 任何 15d 預測 confidence cap 約 0.6（誠實面對長期不確定性）

### 11.D — Step 4 Dashboard 強制顯示規則

每個推薦卡片**必須包含**（缺一不可）：

```
┌─────────────────────────────────────────────┐
│ CEG  Constellation Energy   [EXPERIMENTAL] │
├─────────────────────────────────────────────┤
│ 5d Target: $290 ~ $315 (mid $302)          │  ← Range 為主，mid 為輔
│ Confidence: 0.62  ATR: 3.2%                │
├─────────────────────────────────────────────┤
│ 🔥 Drivers:                                 │  ← 強制顯示 driver
│   • News: +3 (核能補貼新聞 24h 內)         │
│   • Sector: Nuclear HOT (heat 78)           │
│   • Momentum: Stage 2 breakout             │
├─────────────────────────────────────────────┤
│ ⚠ Invalidation:                            │  ← 強制顯示失效條件
│   Close < $268 OR Nuclear sector COLD      │
├─────────────────────────────────────────────┤
│ 🟠 Concentration: 2 同產業推薦 (VST, TLN)  │  ← 11.B 集中度警告
└─────────────────────────────────────────────┘
```

**禁止**：只顯示單一目標價數字而隱藏 driver / invalidation。

### 11.E — 宏觀防禦開關（軟版採納，硬版拒絕）

**軟版本（採納，整合進 Step 4）**：

Dashboard 動能頁頂部固定區塊：

```
┌─────────────────────────────────────────────────────────┐
│ FRED Macro Status: 🟢 Risk-On  /  🟡 Mixed  /  🔴 Caution│
│ Yield Curve: +0.63 | Credit Spread pctile: 29           │
│ ⚠ All short-term recs treat as DIRECTIONAL ONLY in Caution │
└─────────────────────────────────────────────────────────┘
```

當 FRED 指標惡化時，**頂部橫幅顯示警示**，但**個股 score 完全不動**。讓使用者自行判斷要不要降低短期倉位曝險。

**硬版本（拒絕）**：FRED → 個別 theme 加減分。這是 §5「延後到 v2 的東西」中明確排除的 `macro_theme_map.yaml`，理由不變：
- 是未驗證的 macro→theme 民俗規則
- 落入本次對話 backtest 結論的 n=1 過擬合陷阱
- 等推薦 outcome 樣本 ≥ 50 跨 regime 後再評估

### 11.F — 對應到 Step 進度

| Step | 修改 |
|---|---|
| Step 1 (short-term-target) | 加 11.A clamp 規則 + 11.C confidence 公式 |
| Step 3 (thematic-screener) | dedup 改成 11.B WARNING 機制 |
| Step 4 (Dashboard) | 11.D 強制顯示規則 + 11.E 軟版 macro banner |
| 其他 Step | 不變 |

估時不變（這些都是規則細化，不增加 SKILL 數量）。


review by chatgpt
總體評價：這份規劃已經很成熟，不像一般功能發想，比較像內部量化工具的產品規格書。你把時間維度拆開（短期、中期、主題熱度）這件事做得非常正確，也知道先記錄結果、累積樣本，再決定模型是否有效，這是很強的工程思維。

你做得最好的地方，是沒有把所有訊號硬湊成一個總分。很多系統喜歡做 87 分買進、42 分賣出這種表面上很漂亮但實際不可解釋的分數。你現在保留 theme heat、short-term signal、macro 狀態分開呈現，這對使用者決策價值更高。

我認為目前最大的風險，是 short-term-target 這個名字可能會誤導。你現在模型本質比較像短期方向與強弱排序系統，不是真正可以準確預測 5 天後價格到多少的目標價模型。建議名稱調整成 short-term-bias-engine、short-term-directional-engine 或 tactical-momentum-engine，會更誠實也更專業。

第二個風險是 1d / 5d / 15d 三個 horizon 不應共用同一套權重。1 天通常吃新聞與 overnight 情緒，5 天吃資金輪動與延續性，15 天則偏機構趨勢與產業主題。建議每個 horizon 使用不同權重，而不是共用 α β γ。

第三個風險是主題容易 tech bias。你新增的 Space、Quantum、Robotics、Nuclear，大多偏高 beta 成長股。市場強勢時會很亮眼，但 risk-off 時可能一起跌。建議補 defensive themes，例如 Utilities、Healthcare、Staples，或 inflation themes，例如 Energy、Gold、Commodities，讓系統在不同 regime 都有推薦能力。

我最建議你加的功能，是 benchmark-relative output。不要只說某股票預測 +4%，而要說 +4% vs SOXX +1.2%。這樣才能看出你抓到的是 alpha 還是單純跟盤一起漲。

第二個值得加的是 confidence breakdown。不要只給 confidence 0.62，而是拆成：資料新鮮度加分、主題熱度加分、高波動扣分、新聞矛盾扣分。這會讓使用者更信任系統。

第三個是 regime logging。每次推薦時，把當下市場環境一起記錄，例如 VIX、SPY 趨勢、殖利率曲線、信用利差。未來你才能知道模型是在牛市有效，還是震盪盤有效。

工程面最需要注意的是資料時間一致性。你可能 quote 是今天、news 是昨天、theme heat 是三天前、macro 是上週，最後組出一個推薦，這種訊號品質會失真。建議每次輸出都附 freshness 狀態，例如 quote 5 分鐘前、news 2 小時前、theme 1 天前、macro 3 天前。

我最想問你的三個關鍵問題：

第一，你的成功定義是什麼？Hit rate 超過 50%？超越 SPY？Sharpe 比 benchmark 高？如果沒有 KPI，系統很容易漂移。

第二，你這套是給交易決策，還是給 watchlist？如果是交易，需要停損、部位、換手成本；如果只是 watchlist，ranking 就夠。

第三，你能接受模型兩個月失效嗎？真正的 alpha 常常只在特定 regime 有效。如果不能接受，你會一直過度調參。

最後一句話：這套系統真正價值不是預測股價，而是做 Tactical Opportunity Radar。每天告訴你哪些主題升溫、哪些股票最強、哪些有新催化、哪些風險太高。這個定位比目標價預測更強，也更容易做出實際價值。

user回答

第一，你的成功定義是什麼？Hit rate 超過 50%？超越 SPY？Sharpe 比 benchmark 高？如果沒有 KPI，系統很容易漂移。
勝率超過50%, QQQ or SPy

第二，你這套是給交易決策，還是給 watchlist？如果是交易，需要停損、部位、換手成本；如果只是 watchlist，ranking 就夠。
＝＝＝>交易決策, 要給

第三，你能接受模型兩個月失效嗎？真正的 alpha 常常只在特定 regime 有效。如果不能接受，你會一直過度調參。
=>不能, 短期動能分析要準確

---

## 12. 對 ChatGPT Review 的回應與整合

### 強建議（採納，整合進對應 Step）

#### 12.A — 每 horizon 獨立權重（非共用 α/β/γ）

**ChatGPT 對的**：1d / 5d / 15d 驅動因子不同，共用權重是 v1 偷懶設計。

修改 §11.C 為**每 horizon 一套權重**：

```python
HORIZON_WEIGHTS = {
    "1d": {
        "alpha_news": 0.6,        # 1d 高度依賴新聞 + overnight gap
        "beta_sector_heat": 0.1,  # 短期內 sector 影響弱
        "gamma_momentum": 0.3,    # 短期延續性中度
        "atr_multiplier": 1.0,    # 1 個 ATR 為 range
    },
    "5d": {
        "alpha_news": 0.3,        # news 衰減
        "beta_sector_heat": 0.3,  # 5 天 sector 輪動明顯
        "gamma_momentum": 0.4,    # 主導因子
        "atr_multiplier": 1.8,
    },
    "15d": {
        "alpha_news": 0.1,        # news 邊際衰減
        "beta_sector_heat": 0.4,  # 主題持續性主導
        "gamma_momentum": 0.3,
        "atr_multiplier": 3.5,    # range 變大
        "institutional_flow": 0.2 # 15d 加入新因子
    },
}
```

整合到 Step 1 spec。

#### 12.B — Benchmark-relative output（real-time 顯示）

**ChatGPT 對的**：「+4%」單獨看沒意義，「+4% vs SOXX +1.2%」才看得出 alpha vs beta。

Step 1 `predict.py` 輸出每個 horizon 多兩個欄位：

```json
"5d": {
    "target_central_pct": +4.2,
    "benchmark_etf": "SOXX",
    "benchmark_5d_realized_pct": +1.2,    // 過去 5d SOXX 實際走勢
    "implied_alpha_pct": +3.0,            // target - benchmark realized
    ...
}
```

**ETF mapping**：依 ticker GICS sub-industry 自動選 ETF（半導體 → SOXX、軟體 → IGV、Nuclear → NLR、Defense → ITA、Utilities → XLU、廣義 → SPY）

整合到 Step 1 spec。

#### 12.C — Confidence breakdown（透明化）

**ChatGPT 對的**：單一 0.62 不可解釋，拆成貢獻來源使用者才會信任。

修改 §11.C 輸出結構：

```json
"confidence": 0.62,
"confidence_breakdown": {
    "base": 0.50,
    "news_freshness": +0.12,
    "sector_heat_persistence": +0.08,
    "atr_penalty": -0.04,
    "horizon_penalty": -0.05,
    "data_completeness_bonus": +0.01,
    "model_clamped_penalty": 0.0   // 若被 11.A clamp 才扣
}
```

確認 sum(breakdown) == final confidence（透明可審計）。

整合到 Step 1 spec。

#### 12.D — Regime logging（推薦當下記錄市場環境）

**ChatGPT 對的**：Step 5 outcome log 沒記 regime → 未來無法回答「模型在 RISK_OFF 時表現如何」。

Step 5 `recommendations/<DATE>.json` 加入頂層 regime snapshot：

```json
{
  "as_of": "2026-04-25T14:30Z",
  "regime_snapshot": {
    "spy_close": 615.3,
    "spy_rsi_14": 62,
    "spy_ma50_status": "above",
    "vix": 18.5,
    "yield_curve_t10y2y": 0.63,
    "credit_spread_pctile_1y": 29,
    "fred_regime_label": "expansion",
    "market_top_score": 32
  },
  "themes": [...]
}
```

未來 postmortem 可 cross-tab：
- VIX bucket vs hit rate
- yield_curve regime vs alpha
- 找出「模型在哪個 regime 最有效」

整合到 Step 5 spec（成本極低，加幾個欄位）。

### 中建議（採納）

#### 12.E — 資料時間一致性 (per-source freshness)

§11.C 的 `data_sufficiency` 從 binary (ok/insufficient) 改成顯示每個 source 的 age：

```json
"data_sufficiency": {
    "quote_age_min": 5,
    "news_age_hr": 2,
    "sector_intel_age_hr": 18,
    "atr_sample_days": 30,
    "overall_status": "ok"   // 加總判定
}
```

如果各 source age 差距大（quote 5min vs sector 18hr），即使 `overall_status: ok` 也要在 dashboard tooltip 提示「macro context 較舊」。

#### 12.F — 加 1-2 個 defensive themes

**ChatGPT 對的**：你新增的 4 主題（Space / Nuclear / Quantum / Robotics）3 個高 beta，risk-off 時會一起跌。

修改 §3「加入」清單，**再補 2 個 defensive**：

| 主題 | 代表股 | 為何加 |
|---|---|---|
| **Utilities Defensive** | NEE, DUK, SO, AEP, XEL（ETF: XLU, IDU） | 衰退/震盪期相對抗跌；補風險場景覆蓋 |
| **Healthcare Defensive**（區別於 v2 候選的 Healthcare Innovation） | JNJ, MRK, ABBV, LLY, UNH（ETF: XLV, IHF） | Staples-like 性質的醫療大型股；非創新題材 |

新增主題從 4 個變 6 個。

註：不加 Staples/Energy/Gold v1，避免主題清單膨脹太快。等樣本驗證後再評估。

#### 12.G — Dashboard label 改成 "Tactical Opportunity Radar"

Skill 內部名稱保留 `short-term-target`（簡潔好叫、檔案路徑穩定）。

但 **Dashboard 用戶端 label** 改成：
- 中文：「**戰術機會雷達**」(Tactical Opportunity Radar)
- 副標：「短期 (1-15d) 主題熱度 + 個股訊號 [EXPERIMENTAL]」

這個改名直接打擊 Gemini §11.D 的「錨定效應」風險 — 「雷達」比「目標價」誠實太多。

### 對應你 3 個回答的 spec 修正

#### 12.H — KPI 雙條件（hit rate AND beat benchmark）

修改 §6 失敗判定：

| 條件 | 反應 |
|---|---|
| 連續 8 週 hit rate < 50%（亂猜水平） **OR** 中位 alpha vs QQQ/SPY < 0% | 整個 thematic-screener 砍 |
| 某主題 8 週推薦中位 alpha < 0% | 從推薦清單下架該主題 |
| insufficient_data 比例 > 70% | 重新評估資料源 / horizon 設計 |

雙條件比單條件嚴苛 — 高勝率但 alpha = 0 也不算成功。

#### 12.I — Step 1 加交易決策必要欄位

你說「**交易決策，要給**」→ Step 1 `predict.py` 輸出加：

```json
"trading_meta": {
    "stop_suggestion": 188.0,        // 已有
    "position_size_hint_pct": 2.5,   // 新增：建議倉位 (vol-adjusted)
    "tx_cost_estimate_pct": 0.05,    // 新增：來回手續費 + spread 估算
    "min_holding_days": 1,           // 新增：避免被自己短訊號甩來甩去
    "exit_trigger": "Close < 188 OR target_central reached OR confidence drops < 0.4"
}
```

`position_size_hint_pct` 用 ATR-scaled：低波動股（CEG ATR 2%）建議倉位較大；高波動股（IONQ ATR 8%）建議倉位較小。

#### 12.J — 對「不能接受 2 個月失效」的折衷方案（必看）

🔴 **這條我必須老實提醒**：「短期動能準 + 永不失效」**在統計上不可能同時成立**。

**事實**：
- 2018-Q4 / 2020-Q1 / 2022-H1 都是動能策略歷史性失靈期
- Druckenmiller、AQR、Renaissance 都經歷過 1-3 個月 drawdown
- 這不是模型 bug，是動能策略本質

**如果硬要「永遠準」會掉進兩個陷阱**：
1. **過度調參**：每次失靈就改參數 → 永遠在追昨天的 regime
2. **錯過真正 alpha 期間**：失靈期把模型砍掉 → 反彈時不在線上

**使用者決定（2026-04-25）**：接受失效不要 auto-DEGRADED。改用**每週末手動 backtest + 手動調整評分機制**模式。

對應行動：
- ❌ 不做自動降級
- ✅ 新增 **Step 7: Weekend Recalibration Tool** — 每週末跑一次，產生 past-week 表現報告 + suggested 權重調整
- ✅ 將 `HORIZON_WEIGHTS` (12.A) 等所有可調參數搬到 **`skills/short-term-target/config/weights.yaml`**，方便手動編輯
- ✅ 評分機制版本控管：每次調整 → bump `weights_version` 欄位，所有歷史推薦 log 都記錄當時用的 version

### 不採納

| ChatGPT 建議 | 不採納原因 |
|---|---|
| Skill 全面改名 `short-term-target` → `tactical-momentum-engine` | 內部名稱保留簡潔好叫；Dashboard label 改 (12.G) 已解決誠實性問題 |

### 12.K — 對應到 Step 進度

| Step | 增補 |
|---|---|
| Step 1 (short-term-target) | 12.A 每 horizon 權重 + 12.B benchmark relative + 12.C confidence breakdown + 12.E freshness 細化 + 12.I trading meta |
| Step 2 (主題擴充) | 12.F 加 Utilities Defensive + Healthcare Defensive (4→6 個主題) |
| Step 4 (Dashboard) | 12.G label 改名 + 12.J DEGRADED 模式顯示 |
| Step 5 (outcome log) | 12.D regime snapshot |
| §6 失敗判定 | 12.H 雙條件 + 12.J degraded threshold |

估時調整：Step 1 增 +0.5 天（per-horizon weights + breakdown 都要更多測試）；Step 5 +0.2 天 (regime fields)；其他不變。**新總計 ~8-10 工作天**。

---

## 13. Post-Launch Iteration Log (v0.2 → v0.4)

七個 Step 完成後 (v1.49.0) 上線使用，使用者**實際操作 Dashboard 後產生 7 輪迭代**。所有變更記錄於此供未來檢視。

### 13.1 — User Feedback：「我覺得這樣不直覺」(2026-04-25)

使用者打開 v0.1 Dashboard 後反饋雙分區強迫看不直覺，要求：
- 顯示**所有主題**（而非 Top 5）
- 每主題小卡顯示中期 + 短期熱度
- 點主題卡 → 展開 Top 5 movers

→ Radar **v0.2 重設計** (v1.50.0)：移除雙分區，改 6-col grid + click expand。

### 13.2 — Theme Runtime Sync 漏修 (Step 2 incomplete)

實作後盤點發現：plan_short Step 2 我**只改了 cross_sector_themes.md（reference）但沒同步 themes.yaml（runtime）**。21 主題定義對不上 runtime 跑的 15 個。

→ 修正：
- `themes.yaml` + `default_theme_config.py` 同步加 5 新主題（Nuclear Energy / Uranium / Space / Quantum / Robotics / Utilities Defensive / Obesity & GLP-1，Nuclear & Uranium 拆 2 個）
- 重跑 theme-detector with `--max-themes 25` → 偵測到 20 主題

### 13.3 — Predict Cache Layer

screen.py 改成 21 主題 × 全 universe predict → 性能擔憂。加 `predict.py` 4-hour TTL cache：
- First call: ~5s (yfinance)
- Cached: ~0.4s
- Daily run: 第一次 ~5 min，cache 後 < 1 min

### 13.4 — Tooltip Theme 適應 (v1.50.2)

User feedback：「滑鼠不要變問號」+「顏色不符合 theme」。
- `cursor: help` → `cursor: inherit`
- Tooltip CSS 改用 `var(--bg-card)` `var(--text-main)` `var(--secondary)` `var(--primary)` → 自動 light/dark theme 切換

### 13.5 — Breadth 算法 Critical Bug 修正 (v1.51.0)

User: 「短期看多率應該算法要改成 theme 內**所有個股**有多少看多」

**之前 bug**：`bullish_breadth_pct` 基於「top 5 movers」算（已 ranked by score×conv 預先 selected）→ 必然 ≈100% bullish → metric 無意義
**修正**：對主題的**全部 representative_stocks** 算 breadth → 真實「主題內多少股看多」

例：
- Defense & Aerospace: 1d 10% (1/10) → 5d 20% (2/10) → 15d 30% (3/10)
- Cybersecurity: 66% → 77% → 88%（漸強）
- Cloud: 40% → 50% → 50%（混雜）

### 13.6 — 1d/5d/15d Horizon Switcher (v1.51.0)

User 接著問「能否切換 1d/5d/15d」。實作：
- `screen.py` 把 `compute_theme_short_term` 重寫成回傳 `by_horizon: {1d/5d/15d: {bullish_breadth, conviction, n_valid, n_bullish, mean_target_pct}}`
- `radar.html` 加 [1d] [5d] [15d] toggle
- `page-radar.js` 加 `_currentHorizon` state
- Theme card 顯示「SHORT bull [5d] 80% (8/10)」格式

**判斷標準說明**（per user 要求列出）：
- **1d**：news 0.6 + sector 0.1 + momentum 0.3，clamp ±5%，新聞主導
- **5d**：news 0.3 + sector 0.3 + momentum 0.4，clamp ±15%，動能主導（**primary horizon**）
- **15d**：news 0.1 + sector 0.4 + momentum 0.3，clamp ±30%，產業持續性主導，confidence cap 0.6

### 13.7 — 「為什麼 universe 才 10 個？」根本問題 (v1.52.0)

User 指出**結構性問題**：「'top 5' implies a universe — 你只 10 個怎麼能叫 top 5」。

**真相**：之前 themes.yaml 的 `static_stocks` 是我手選 10 個 → screen.py 只能在 10 中挑 5 → 「top 5」其實是「top 5 of my 10」。語意嚴重錯。

**修正**：用 **proxy ETF 的 top holdings** 當 universe（per user 選 Option B）：
- 新增 `skills/thematic-screener/scripts/refresh_etf_holdings.py`（150 行）
- yfinance `Ticker(etf).funds_data.top_holdings` 取每 ETF top 10 → dedup → 過濾非美股（任何含 `.` 的 ticker）→ cap 25
- 結果：21 主題從 10 個 → 4-25 個 stocks（真實 universe 大小依主題而異）
- 新增 `skills/thematic-screener/etf_meta.yaml` 紀錄 `last_refreshed` timestamp

**真實 breadth 結果**：
```
AI & Semis      N=22  95% (21/22)  真強勢
Financial       N=25  80→84→88%   漸強
Defense         N=18  33→38→44%   短空長中性
Oil & Gas       N=25  32→36→36%   失寵
Cybersecurity   N=17  52→58→64%   漸強
```

### 13.8 — ETF Holdings Auto-Refresh Mechanism

User: 「要確保這件事情會自動地每季去抓」

ETF rebalance 真實頻率：多數季度（Mar/Jun/Sep/Dec），ARK 系列例外（active management）。

**實作 (daily_update.sh Step 5.5)**：
- 讀 `etf_meta.yaml` `last_refreshed`
- < 60 days：✅ 綠燈
- 60-90 days：⚠ 黃燈提醒
- ≥ 90 days：🔄 **自動觸發** `refresh_etf_holdings.py` + 同步重跑 theme-detector

完全本地、0 LLM token 成本（yfinance 免費）。User 0 維護。

### 13.9 — UI Polish 系列 (v1.52.1 - v1.52.3)

User 連續 4 次小 feedback 改善視覺：

**v1.52.1**：
- 移除 cool 主題 opacity 0.7（user 不喜歡淡化）
- 改用**邊框顏色**表示熱度：紅邊 = mid_heat ≥60、淺藍邊 = mid_heat < 30、warm 預設灰邊
- 移除 SHORT bull row 的 sort 高亮底色（保留 ↓ arrow）

**v1.52.2**：
- Mover card 背景 `rgba(255,255,255,0.02)` → `0.045`（淡白可見）
- 加「🔍 分析」紫色按鈕到每張 mover card → click → `AnalyzeQueue.enqueue` → 投資協議 V4.8.1
- 加 `analyze-queue.js` 進 radar.html

**v1.52.3**：
- 移除「5d ★」星號（user：「不要強調 5d 如果我也不能改」）
- 移除 5d cell 的 primary 紫色背景 → 3 個 horizon cell 視覺等齊
- Drivers 區塊「(5d)」標籤拿掉
- Trading meta「5d Target」→「Target」/「目標」
- 加灰色斜體 footnote：「Drivers / Target / Stop 基於 5d 計算（primary horizon）」

### 13.10 — 19-Term Hover Tooltip System (v1.50.2)

借鏡 `momentum.html` 的 `mom-pill-tooltip` pattern，建 radar 專屬：
- `RADAR_TERMS` dict in `page-radar.js`：23 個 term（zh + en），每個含 `title / desc / hint` 三段
- CSS `#radar-term-tooltip` 用 theme variables
- `data-radar-tip="<key>"` attribute 灑在所有 term 上 (19 個位置)
- Hover handler 動態定位

涵蓋：mid_heat / short_bull / avg_conv / horizon (1d/5d/15d) / range / confidence / 4 drivers / invalidation / concentration / 4 trading meta / FRED regime / SPY RSI / VIX / yield curve / credit spread / regime factor。

### 13.11 — i18n 完整翻譯

`i18n.js` zh/en 雙語：
- 34 個 UI keys（sort_label / horizon_label / card labels / driver labels...）
- 6 個 maps：theme_names (21 主題)、lifecycle_map、heat_label_map、conf_map、fred_regime_map、ma_status_map
- mover card 內動態 zh/en 切換（concentration warning、horizon range label 等）

### 13.12 — 待決定事項（延後）

| 項 | 何時決定 |
|---|---|
| **Primary theme tagging（解 NVDA 跨主題重複）** | 等使用 1-2 週後若 visually 困擾再啟動 |
| **Mover card 跟 horizon toggle 全變** | 需擴 predict.py 對 1d/15d 也產 trading_meta + invalidation。目前只算 5d 一份。est 2h，user 確認需要才做 |
| **動態 ETF API**（不用手動 quarterly） | 手動已夠用，v0.5 才考慮 |

### 13.13 — News Driver v0.2.1（兌現 v0.2 promise）

問題：之前 SKILL.md / global_warnings 寫「v0.2 will integrate Finnhub /company-news」，但實作上 v1.46-v1.52 都還是 v0.1 volume×gap proxy。User 提醒後實作。

**Method 選擇** — 4 個方案：
1. Pure keyword counting（粗糙）
2. Keyword + magnitude + negation（finance-tuned，0 cost）
3. Finnhub `/news-sentiment` endpoint（測試 → **403 premium-only**）
4. LLM scoring（精準但 $1-2/day）

走 method 2（Finnhub 3 不能用就純 2）。

**v0.2 第一版**（粗糙）：5 ticker test 後發現 5 個 critical bug：
- NVDA 248 articles 多數無關（"Walmart's investment in Mexico" 被當 NVDA 算）
- "Is X a Buy?" 問句被當看多 +0.5
- "Lockheed Martin Shares Are Falling" 沒抓到（"falling" 不在詞庫）
- "Insiders Sold Suggesting Hesitancy" 沒抓到（"hesitancy" 不在）
- 所有 248 article 平均稀釋訊號

**v0.2.1 修正**（v1.53.0）：
- **Headline relevance filter**：用 Finnhub profile 抓 company short name (NVDA→NVIDIA, LLY→Eli Lilly, JPM→JPMorgan Chase)，新聞標題沒 ticker 也沒 short name → 過濾
- **問句 ×0.5 discount**：標題含 `?` 或開頭 `Is/Are/Why/How/Should/Will/Can` → score halved
- **Cap top 20 by recency**：避免 248 articles 噪音稀釋
- **+25 個新詞彙**：falling / hesitancy / flopped / buyback / dividend cut / sluggish / accumulation / ...
- **Source blacklist**：simplywall.st / fool.com / zacks.com 過濾掉

**5-ticker test 結果（v0.2 → v0.2.1 對比）**：

| Ticker | v0.2 raw | v0.2.1 filtered | 變化 |
|---|---|---|---|
| NVDA | 248 → +0.152 | 20 of 249 → **+0.250** | 噪音砍 92% |
| LMT | 47 → -0.011 | 20 of 92 → **-0.045** | 抓到 Q1 miss + falling |
| LLY | 36 → +0.033 | 10 of 49 → **-0.055** | **翻轉成負**（GLP-1 競爭壓力） |
| JPM | 42 → +0.031 | 1 of 52 → **-0.040** | 41 篇 commentary noise 被砍 |
| IONQ | 0 (proxy) | 0 (proxy) | 一樣（沒新聞） |

**已知殘留 bug**（小，未來修）：
- "Why X Flopped" 顯示 +0.25 但應 -0.25（summary 內某詞蓋過）
- 動詞變化漏：「slips」（有 slides 沒 slips）/「lag」（有 lagged 沒 lag）

**Fallback**：若 Finnhub 整個失敗或無相關文章 → 自動降回 v0.1 volume/gap proxy（global_warnings 標明）

整合進 screen.py 自動使用（每天 daily_update.sh 跑時生效）。

---

## 14. Final Architecture (v0.4 production state)

```
┌─────────────────────────────────────────────────────────────────┐
│ Daily auto pipeline (daily_update.sh, ~3-5 min)                 │
└─────────────────────────────────────────────────────────────────┘
  Step 1-4: Breadth / FTD / Top / FRED cache (existing)
  Step 5:   bridge.py → Dashboard/data.json
  Step 5.5: ETF holdings auto-refresh check (every 90 days)
            → refresh_etf_holdings.py (yfinance)
            → 同步重跑 theme-detector
  Step 6:   thematic-screener
            ├─ 讀 theme-detector cache（21 主題，max 25 reps each）
            ├─ 對每個 representative_stocks call short-term-target.predict() (4h cache)
            ├─ 算 by_horizon breadth/conviction (1d/5d/15d each)
            ├─ regime overlay：2 badges (RSI + VIX) + factor (max 偏離度)
            ├─ concentration WARNING (per §11.B)
            └─ 寫 data/recommendations/<DATE>.json + bridge 注入 data.tactical

┌─────────────────────────────────────────────────────────────────┐
│ Manual: weekend recalibration (every weekend, ~1-2 min)         │
└─────────────────────────────────────────────────────────────────┘
  python3 skills/short-term-target/scripts/weekly_review.py
  → reports/SHORT_TERM_WEEKLY_<DATE>.md
  → user 決定是否 edit weights.yaml + bump weights_version

┌─────────────────────────────────────────────────────────────────┐
│ Dashboard: /radar.html                                          │
└─────────────────────────────────────────────────────────────────┘
  Header: EXPERIMENTAL badge + Horizon toggle (1d/5d/15d) + Sort toggle
  Regime banner: FRED regime + SPY/RSI/VIX/YC/Credit + Factor 顯示
  Regime badges: RSI extreme / VIX extreme（4 quadrant aware）
  Theme grid: 全 20 主題卡（mid 紅/灰/藍邊框 + SHORT bull% + conv + N）
  Click theme → 展開 Top 5 movers panel
  Mover card: 1d/5d/15d horizon-bar + drivers + invalidation + concentration
              + trading meta（Stop 紅、Target 方向色）+ 5d footnote + 「分析」button
  Hover any term → tooltip (title/desc/hint)
```

---

## 15. KPI Gate (per §6 + §12.H + §13)

從 day 1 開始累積樣本到 `skills/thematic-screener/data/recommendations/<DATE>.json`。

**正式評估觸發條件**：N ≥ 30 不同 daily samples (3-4 週 daily run)
**評估指標**：
- **5d hit rate ≥ 50%** (random walk baseline)
- **5d 中位 alpha vs benchmark ≥ 0%**（不能輸 SPY/QQQ）

**失敗 → 退役**：以上兩條任一 fail 在 N≥30 → 整個 thematic-screener 系統退役。

**評估工具**：`skills/short-term-target/scripts/weekly_review.py`（Step 7 已建）。

---

整個 Tactical Opportunity Radar v0.4 完成於 2026-04-25 (v1.52.3)。從 plan_short.md 規劃到 production 共 ~3 個工作日（含 12 輪 user feedback 迭代）。Day-1 logging 已運轉，等樣本累積。

# `technical_core` 除息調整統一 — 範圍表（待拍板，尚未動工）

> 產生：2026-08-08（repo V4.112.0，commit `81a27f7` 之後）。
> 起因：探 B4 前置條件時發現 `technical_core` 主源與 fallback 的調整慣例不一致。
> **本檔是範圍表，不是實施表**——動工前需使用者核可，並照 Workflow Rule 1 另出實施表。

## 0. 修法方向（先定死，Shadow 對照組據此決定）

**目標慣例 = 全面 dividend-adjusted。**
`_fetch_fmp_ohlc` 改打 `/stable/historical-price-eod/dividend-adjusted`，
`adjOpen/adjHigh/adjLow/adjClose` 映射到現行欄名 `Open/High/Low/Close`，`volume → Volume`。

理由：與 yfinance fallback（`auto_adjust=True`）及 yfinance 生態一致，且 B4 的零翻轉
證據可直接繼承。

**Shadow 對照組因此是「現行混用」vs「全調整」，不是兩種新方案互比。**

## 1. 問題陳述（已獨立驗證）

`skills/_shared/technical_core.py` 的 `fetch_history()`：

| 路徑 | 端點 | 調整慣例 |
|---|---|---|
| 主源 `_fetch_fmp_ohlc` | `historical-price-eod/full` → `close` | split-adjusted，**未除息** |
| fallback | `yf.Ticker().history(auto_adjust=True)` | **已除息** |

**同一檔標的拿到哪一種序列，取決於當下 FMP 有沒有失敗**——而 fallback 是常態性、
靜默發生的。這比「文件教錯」更差：分析結果隨網路狀況變，連復現都不穩定。

`technical_core.py` 自陳的「配息股 MA 讀數略高、可接受」是同一個偏差的表述，且那句的
適用範圍限定在型態辨識。

## 2. 影響面（逐檔實測，**修正先前的「9 個消費者」**）

### 2a. 受影響 —— 真的呼叫 `technical_core.fetch_history()`：**5 個**

| # | 檔 | 呼叫數 | 風險等級 | 對照指標建議 |
|---|---|---|---|---|
| 1 | `skills/technical-analyst/scripts/analyze.py` | 1 | **高** | RSI14 / MA20-50-200 / MACD / stage 分類 / 型態旗標，逐 ticker diff |
| 2 | `skills/momentum-monitor/scripts/momentum.py` | 2 | **高** | composite score、volume_profile、cross 偵測、rsi_state |
| 3 | `skills/quant-backtest/scripts/backtest.py` | 1 | **中**（探索層） | 每策略 CAGR / Sharpe / maxDD / 交易次數 |
| 4 | `skills/quant-backtest/scripts/rank_strategies.py` | 1 | **中**（探索層） | 策略排名順序（名次翻轉數才是重點，不是絕對值） |
| 5 | `scripts/kill_trigger_monitor.py` | 1 | **高** | kill trigger 觸發與否的 boolean 翻轉數 |

### 2b. 不受影響 —— 只 import `rsi_14`（純函式，序列由呼叫端自備）：4 個

`short-term-target/predict.py`、`thematic-screener/screen.py`、
`market-sentiment-analyzer/sentiment.py`、`theme-detector/etf_scanner.py`。

> **`short-term-target` 不在影響面內**（推翻先前的高風險判定）。`predict.py` 的
> `fetch_history` 呼叫數 = 0，它自己走 `yf.Ticker().history(auto_adjust=False)` 取價
> ——**未調整**，是 repo 裡的第三套慣例，但它自成一格且 `weights.yaml` 就是在該基準上
> 校準的。本次變更不觸及它，**無需送使用者重新過目**。
> （附帶觀察：`auto_adjust=False` 這套慣例本身值不值得統一是另一個題目，不在本範圍。）

### 2c. 不受影響 —— 自帶同名 local function：**4 個**

`sector/ftd_yfinance.py:55`、`sector/market_top_yfinance.py:85`、
`scripts/build_event_index.py:102`、
**`skills/portfolio-risk-manager/scripts/risk_manager.py:47`**（走 `yf.download`）
各有自己的 `def fetch_history`，與 technical_core 無關。

> 最後一個是本批自己剛寫過測試的檔（`test_risk_manager.py` patch 的正是它的 local 版），
> 盤點時仍漏掉——**同名不同物是清單式盤點的典型盲區**，也是 §2b「用字串問不用清單問」
> 的又一例。

### 2d. shim 確認

`skills/momentum-monitor/scripts/technical_core.py` = 14 行純 re-export
（`from skills._shared.technical_core import *`），**非獨立實作**，不需另計。

## 3. 端點契約實測（照 V4.111.6 紀律，不假設與 `full` 同行為）

`full` 當時被抓到「忽略 `timeseries` 參數、回全史」，故逐項驗：

| 檢查項 | 結果 |
|---|---|
| 遵守 `from` / `to` | ✅ 請求 07-01..07-31 回 22 筆，範圍相符（**與 `full` 的 timeseries 行為不同，這個有守**）|
| 無 `from`/`to` | 回 1255 筆（5 年）→ 現行程式已帶 from/to，payload 不會爆 |
| 排序方向 | newest-first，**與 `full` 相同** → 現行 `.sort_index()` 不用改 |
| 欄位完整性 | `adjOpen/adjHigh/adjLow/adjClose/volume` 對 KO/TLT/NVDA 各 251 筆 **零 null** |
| 最新 bar vs `full` | KO 87.05/87.05、TLT 82.76/82.76、NVDA 223.96/223.96 **完全相同** → **`intraday_state` 對最後一根的依賴安全** |

**契約結論：drop-in 替換，只需改端點字串與欄名映射。** 無 timeseries 類陷阱。

## 4. 測試現況（第 5 條要求的答案，但答案比預期糟）

全 repo grep：**沒有任何測試碰 `technical_core` 的價格路徑**（`_fetch_fmp_ohlc`，
以及 `technical_core.fetch_history`）。

> 措辭精確度：不能說「沒有任何測試碰 `fetch_history`」——`test_risk_manager.py` 有 19 處
> patch，但打的是 `risk_manager` 自己的 local 同名函式（見 2c），與 technical_core 無關。

| 消費者 | 測試檔數 | 碰價格路徑的 |
|---|---|---|
| technical-analyst | **0** | — |
| momentum-monitor | **0** | — |
| kill_trigger_monitor | **0** | — |
| quant-backtest | 3 | **0** |
| （2b 的四個 rsi_14-only） | 3 / 15 / … | **0** |

所以**沒有 mock 遷移工作要做**——因為那條路徑上根本沒有測試。V4.111.6 教訓 (c)（改
transport 層要同步遷 patch 目標）在這裡不適用，取而代之的是更糟的狀況：

> **五個受影響消費者裡有三個零測試，且沒有任何測試覆蓋價格取得路徑。
> Shadow 對照是這次變更的唯一安全網。**

建議把「補 `_fetch_fmp_ohlc` 的契約測試」納入本批（mock `fmp_pool.get` 回固定 payload，
鎖欄名映射、排序、from/to 傳遞、fallback 觸發條件），約 60 行。

## 5. 時間序列接縫（第 3 條）

`momentum-monitor/scripts/journal.py` 記錄 5/20/60d forward return 與 MAE/MFE(20d)。
切換日之後新建的 entry 用調整後基準，切換日之前的 entry 用舊基準——**跨切換日的比較會
混入基準變化**。

處理：**不改歷史值**，在 journal 加一筆切換日註記（欄位或 README 皆可，實施表定案），
`stats` 輸出時若 cohort 跨越該日則標註。同樣適用於任何跨日比較的 momentum 統計。

## 6. 分級處置（第 2 條）

| 消費者 | 層級 | 處置 |
|---|---|---|
| quant-backtest ×2 | **探索層**（CLAUDE.md 全域紀律：產出永不進 investment_protocol 決策） | 漂移可容忍，但**要量化**：每策略績效 delta + 排名翻轉數，寫進報告 |
| technical-analyst / momentum-monitor / kill_trigger_monitor | 接決策路徑 | 逐 ticker 對照，**任何 boolean 翻轉（cross 偵測、stage 分類、kill trigger）逐筆解釋** |
| short-term-target | **不受影響**（見 2b） | 無 |

## 7. B4 後續（額外要求）

`b4_shadow_v2.py` 是**直打端點**算出零翻轉的，不是走改過的 `fetch_history`。
technical_core 改完後，B4 三支遷移要**過真實 code path 重跑一次**零翻轉 shadow，通過才算數。

## 8. 拍板結果（2026-08-08，使用者裁示）

1. **執行：准。** 問題雙方獨立驗證，方向對，影響面已精確定價。
2. **Feature flag：要，但用 module 常數，不用環境變數。** 端點字串提為
   `_FMP_OHLC_ENDPOINT` module-level 常數，shadow 腳本 patch 常數即可在同一 process
   跑兩邊。**理由：環境變數是又一個看不見的行為軸——「結果取決於執行環境的隱形狀態」
   正是本批要消滅的病，不要在治病的 commit 裡引入同款病原。** 常數是好 hygiene，
   cutover 後保留，無需清理。
3. **Docstring 契約：要寫，而且不只 docstring。** 同一個 commit **必須**改掉
   `technical_core.py:86-90` 那段舊註解——它現在寫的「FMP 未除息、配息股 MA 略高、
   可接受」在修完後就是假話，留著就是下一個 tail-risk SKILL.md。**進實施表，不靠殘留
   掃描碰運氣**（雖然 §2b 也應該會抓到——掃描字串用 `dividend-adjusted`、`not dividend`）。
4. **契約測試：納入，必做。** 零覆蓋路徑上的 60 行是本批性價比最高的投資。三點要求：
   (a) mock 打在 `fmp_pool.get`（真 transport 層，老規矩）；
   (b) 種回 bug 確認紅——例如把欄名映射改回 `close` 看它翻；
   (c) 多鎖一條：**fallback 呼叫時斷言 `auto_adjust=True` 有被傳入**——這讓第 3 項的
   「兩路徑同慣例」契約從註解變成機器可驗的斷言，兩邊都鎖死。

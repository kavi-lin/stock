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

## 5b. Shadow 通過標準（**訂錯過一次，這是修正後的版本**）

第一版實施表寫「決策層 boolean 與分類零翻轉」——**錯，而且會自我矛盾**。

B4 用零翻轉當閘門是對的，因為那是**換資料源**，翻轉 = 引入漂移。
**本批是修正基準**：配息股序列裡的假負報酬（除息日）被拿掉後，一檔剛好卡在 MA50 交叉
邊緣的 KO 或 TLT，cross 偵測或 stage 分類**應該**翻——那是修正，不是回歸。硬性零翻轉
會讓正當修正把整批卡死，或更糟，誘使執行者把「解釋得通的翻轉」硬拗成沒翻。

### 正確標準：**零「不可歸因」翻轉**

| 情況 | 判定 |
|---|---|
| 該 ticker 有配息，且翻轉方向與「假負報酬消失」的機制一致 | **記為修正，放行**（逐筆寫進報告） |
| 翻轉無法歸因到除息機制 | **擋批**，停下來問使用者 |
| **無配息標的出現任何差異** | **一律視為不可歸因** —— 它們在兩個基準下序列應該**逐位元一致** |

最後一列同時是 **shadow 自身正確性的 sanity check**：無配息組若不是逐位元一致，
先懷疑 shadow 寫錯，而不是 code 改錯。

## 5c. Shadow 樣本集（59 檔）

| 來源 | 數量 | 理由 |
|---|---|---|
| B4 shadow 原 16 檔 | 16 | 現成、分群齊（8 配息 / 5 無配息 / 3 ETF），含 TLT/KO/MO 三個最敏感的 |
| `positions.json` 全持倉 | 6 | GOOGL META MRVL MSFT NTRS VRT —— **kill_trigger_monitor 監控的是真實部位，樣本必須涵蓋它實際看的標的** |
| momentum journal 最新 snapshot（2026-06-17） | 23 | 活躍 cohort。（未結算 entry 涵蓋 529 檔＝幾乎整個 S&P，過大；最新 snapshot 才是 momentum 實際重新評分的集合） |
| 高股息壓力樣本 | 15 | PM SO D DUK ED O KMB CL PEP MRK CVX IBM MMM GIS K —— 除息機制最敏感，刻意加壓 |

聯集去重 = **59 檔**。無配息對照組（NVDA/TSLA/AMZN/GOOGL/COIN 等）必須逐位元一致。

## 6. 分級處置（第 2 條）

| 消費者 | 層級 | 處置 |
|---|---|---|
| quant-backtest ×2 | **探索層**（CLAUDE.md 全域紀律：產出永不進 investment_protocol 決策） | 漂移可容忍，但**要量化**：每策略績效 delta + 排名翻轉數，寫進報告 |
| technical-analyst / momentum-monitor / kill_trigger_monitor | 接決策路徑 | 逐 ticker 對照，**任何 boolean 翻轉（cross 偵測、stage 分類、kill trigger）逐筆歸因**——判定標準見 §5b（零「不可歸因」翻轉，不是零翻轉） |
| short-term-target | **不受影響**（見 2b） | 無 |

## 6b. Shadow 實測結果（2026-08-08，59 檔，V4.113.0）

兩邊都走**真實的 `_fetch_fmp_ohlc` code path**：舊基準靠 patch `fmp_pool.get`，讓它改打
`full` 並把 `close→adjClose` 欄名改回去，模擬 V4.113.0 之前的 payload。差異只來自上游
資料，不來自 shadow 另寫的一套邏輯。

### 閘門判定：✅ **通過（零不可歸因翻轉）**

| 檢查 | 結果 |
|---|---|
| **無配息對照組逐位元一致** | **7/7** ✅（AMZN COIN DVA GNRC MNST PANW TSLA）——同時證明 shadow 自身正確 |
| 翻轉是否全落在配息標的 | **是**，零非配息翻轉 |
| `ma_200` 位移方向 | **51/51 全部下修**（-3.978% ~ -0.028%，中位 -0.795%）——除息機制的簽名 |

### 分類翻轉分解（第一版判定過寬，此為修正後）

第一版把 `ma_structure` / `macd` 整個 dict 當分類欄位，報出 51/52「翻轉」——**錯**。
拆到子欄位後：

| 欄位 | 真翻轉數 | 說明 |
|---|---|---|
| `rsi_state.zone` | **0** | 29 筆有差異但 zone 全同，只是內嵌 rsi 值位移 |
| `ma_structure.stage` | **3** | MO / MS / PG |
| `macd.bullish_cross` | **3** | MS / TLT / WST |
| `macd.histogram_trend` | **1** | O（flat → falling） |
| `crosses`（清單） | 19 | 見下方分類 |

### 逐筆歸因

**(a) cross 清單 19 筆，四類：**

| 類型 | 數量 | 標的 | 歸因 |
|---|---|---|---|
| 同型別、日期位移 1-2 天 | 13 | DUK ED IRM KMB MCHP MMM O PFE SO T TLT VZ XLK | MA 在略微不同的日子交叉。機制直接後果 |
| **cross 消失** | 4 | HST MO MS PM | **最強證據，見下** |
| cross 出現 | 1 | PEP（`death_cross_50_200 06-29`） | ma_200 下修使 50/200 關係改變 |
| 型別替換 | 1 | PG | 同上 |

**消失的四筆全部是「一兩天內來回穿越」的假訊號：**

| 標的 | 舊基準的 cross | 調整後 |
|---|---|---|
| HST | `death 07-28` + `golden 07-31`（3 天內來回） | 空 |
| MO | `death 07-14` + `golden 07-15`（**隔天穿回**）+ `death 08-07` | 空 |
| PM | `death 07-16` + `golden 07-17`（**隔天穿回**） | 空 |
| MS | `death 08-07`（當天） | 空 |

「短期 MA 瞬間穿越又立刻穿回」正是除息假跌的指紋——一根假的大陰線把 MA20 拉下去，
隔天就回來。調整後這些假交叉全部消失。**這不是漂移，是這次變更要修的東西本身。**

**(b) `stage` 三筆，全部朝「較不看空」方向，與 `ma_200` 下修一致：**

| 標的 | 變化 | `above_ma200_pct` | `ma_200` |
|---|---|---|---|
| MO | Stage 3 top → Stage 1 basing | +4.11 → +6.60 | -2.33% |
| MS | Stage 1 basing → Stage 2 uptrend | +16.44 → +17.67 | -1.05% |
| PG | Stage 4 downtrend → Stage 1 basing | -1.47 → **-0.07** | -1.40% |

PG 尤其乾淨：`above_ma200_pct` 從 -1.47 移到 -0.07，正好卡在 0 附近的帶邊。

**(c) `macd.bullish_cross` 三筆，histogram 全在 ±0.02 的極邊界：**

| 標的 | bullish_cross | histogram |
|---|---|---|
| MS | True → False | +0.087 → +0.210 |
| TLT | False → True | **-0.006 → +0.018** |
| WST | False → True | **-0.013 → +0.005** |

TLT 與 WST 的 histogram 絕對值皆 < 0.02，是零軸上的抖動，任何微小基準位移都會翻。

### ⚠ 必須知道的系統性影響（可歸因，但方向一致）

所有翻轉都通過歸因，**但它們不是隨機的**：`ma_200` 51 筆全部下修，三筆 stage 全部朝
較看多方向。機制上這是必然的——調整後的歷史價較低，長期均線隨之下移，價格相對更高於
均線。

**結論：所有配息股的技術面讀數會系統性地偏多一點點。** 這是修正（假跌本來就在人為壓低
它們），不是 bug，但它是**方向性的、影響全部配息標的**，不是可以忽略的噪音。

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

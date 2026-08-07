# Sector Protocol — Fallback 備援與機械細節（Appendix）

> **何時讀這個檔**：兩種情況 ——
> (a) `phase0_read_caches.py` 或 `phase_prefetch.py` **實際失敗**（rc≠0）；
> (b) reader rc=0 但 `stale_layers` / `missing_layers` 非空，需要 §1 的**逐層重整指令**
> （reader 只要有一層可用就 rc=0，所以這是常見狀況，不算失敗）。
> 其餘場次全程走那兩支 reader/prefetch，本檔一行都不用讀。
>
> **為什麼分出來**（SE4）：四個 protocol 檔每場全載，其中純備援的 bash 呼叫與參數怪癖
> 佔了約 200 行 —— 它們一年用不到幾次，卻每場都吃 context。**判斷規則（rubric、紀律、
> 欄位語意）沒有搬過來，全部留在主檔**：那些是每場都在用的東西，搬走等於讓準確度換 token。

---

## §1 — Phase 0 逐層 cache 讀取（`phase0_read_caches.py` 失敗時）

> 主檔對應：`phase_0.md`。**FTD 反幻覺規則與 FRED slim 11 欄的 shape 留在主檔**，
> 因為那兩項每場都要遵守，不是備援。

### 層 A — market-breadth-analyzer（優先，量化）

取 `./breadth_cache/market_breadth_*.json` 最新檔（FRESH = mtime < 10800s）：
- FRESH → 直接讀
- STALE 或缺失 → 執行（約 5 秒）後讀新檔：
  ```bash
  python3 ~/.claude/skills/market-breadth-analyzer/scripts/market_breadth_analyzer.py \
    --output-dir ./breadth_cache/
  ```

> `uptrend_ratio_overall` 不在此處取得，由 Phase 1 完成後取各產業 `uptrend_ratio` 平均值回填。

### 層 B — Web Search（最後手段，有層 A 則跳過）

Web search: "US market breadth today"、"S&P 500 advance decline today"

### 層 C — FTD Detector cache（量化底部確認）

取 `./ftd_cache/ftd_detector_*.json` 最新檔（FRESH = mtime < 10800s）：
- STALE 或缺失 → 執行（約 10 秒）：
  ```bash
  python3 sector/ftd_yfinance.py --output-dir sector/ftd_cache/
  ```
- 讀取欄位：`market_state.combined_state`、`quality_score.total_score`、
  `quality_score.exposure_range`、`ftd_timeline.*`

> ⚠️ **FTD 文字反幻覺規則（V1.5 — BUG-006）留在 `phase_0.md` 主檔**，每場都適用。

### 層 D — Market Top Detector cache（量化頂部偵測）

取 `./market_top_cache/market_top_*.json` 最新檔（FRESH = mtime < 10800s）：
- STALE 或缺失 → 執行（約 10 秒）：
  ```bash
  python3 sector/market_top_yfinance.py --output-dir sector/market_top_cache/
  ```
- 讀取欄位：`composite.composite_score`、`composite.zone`、`composite.risk_budget`

> 層 C + 層 D 腳本完全獨立 → 並行執行。

### 層 E — FRED Macro Snapshot（MUST-run）

取 `skills/fred-macro/cache/fred_latest.json`（FRESH = mtime < 3600s；fred-macro 自帶 1 hr cache）：
- STALE 或缺失 → 執行：
  ```bash
  python3 skills/fred-macro/scripts/fetch.py --json-only
  ```
- 失敗（無 API key / 網路錯誤）→ `fred_available = false`、`fred_snapshot = null`，protocol 繼續跑不中斷

> **必讀 `SECTOR_ROTATION_GUIDE.md` 與 slim 11 欄的 shape 留在 `phase_0.md` 主檔。**

---

## §2 — Phase 0 欄位映射（歷史紀錄，**非現行 spec**）

⚠️ **舊版那張手動映射表已由 `build_sector_intel.py` 的 `build_phase0()` 取代，且實作與表
不一致。原表沒有原樣搬過來** —— 把過期的表當「參考資料」保留，等於讓它繼續誤導。本節
只留下三處**實查出來的不一致**當沿革紀錄；**判斷一律以 script 為準**，不要照舊表手填。

（原表中仍然有效的兩列已回到主檔：`exposure_ceiling ← composite.exposure_guidance` 與
`breadth_score ← composite.composite_score`，前者見 `phase_0.md` §exposure_ceiling，
後者由 `build_phase0()` 自動填。）

已知不一致（實作 = `build_sector_intel.py:154-190`）：

| 欄位 | 舊表所寫 | script 實作 |
|---|---|---|
| `breadth_components` | 四個子欄（overall / sector_participation / momentum / mean_reversion_risk） | 只寫 `overall_breadth` |
| `regime_confidence` | 由 data_quality 映射（Complete=0.9 / Partial=0.7 / Limited=0.4） | 固定 `0.9` |
| `warning_flags` | 六種旗標（含 `Early_Warning_Divergence`、`Critical_Zone`） | 四種：`Bearish_Signal_Active`（bearish_signal.score ≤ 40）、`Below_200MA`（ma_crossover.gap < 0）、`Low_Historical_Percentile`（historical_percentile.score ≤ 40）、`Weakening_Zone`（zone ∈ Weakening/Weak） |

> `cycle_phase` **不在此列** —— 它仍由 LLM 於 decision JSON authored，推斷規則留在
> `phase_0.md` 主檔。

---

## §3 — Phase 3 逐項取數（`phase_prefetch.py` 失敗時）

> 主檔對應：`phase_1-2-3.md`。**所有 rubric 用法（`news_catalyst` ±5、R5/R6/R7 提示、
> WebSearch 禁令、情緒欄位映射）留在主檔**，本節只有「怎麼跑」。

### Step 1 — Market Sentiment

```bash
python3 skills/market-sentiment-analyzer/scripts/sentiment.py --json
```
輸出 stdout JSON：`composite_score` / `label` / `vix` / `put_call_ratio` /
`spy_momentum.rsi_14` 等。失敗 = **SOFT**。

### Step 2 — Economic Calendar

```bash
python3 skills/economic-calendar-fetcher/scripts/get_economic_calendar.py \
  --from {SCAN_DATE} --to {SCAN_DATE+7d} --format json
```
argparse 介面（**不**支援 `--json` / `--days N`，會 unrecognized arguments）。失敗 = **SOFT**。

### Step 3 — Earnings Calendar

```bash
python3 sector/scripts/fetch_earnings_calendar.py {SCAN_DATE} {SCAN_DATE+7d}
```
**位置參數**（**不**支援 `--json` / `--days N` / `--from` / `--to`）。
預設讀 `$FMP_API_KEY`；calendar + per-symbol profile 全走中央 `fmp_pool`。失敗 = **SOFT**。

### Steps 3b/3c/3d/3e — 平行版（推薦，省 3-4 min）

4 個 fetch script 完全獨立（讀 FMP 不同 endpoint、寫不同 cache 檔）→ 平行安全。
串跑約 6 min wall，平行約 30s。

```bash
SCAN_DATE=$(date +%Y-%m-%d)
PIDS=()
python3 sector/scripts/fetch_earnings_pulse.py --date $SCAN_DATE > /tmp/fetch_eps.log 2>&1 &
PIDS+=($!)
python3 sector/scripts/fetch_smart_money.py    --date $SCAN_DATE > /tmp/fetch_smt.log 2>&1 &
PIDS+=($!)
python3 sector/scripts/fetch_sector_news.py    --date $SCAN_DATE --lookback-days 2 > /tmp/fetch_snews.log 2>&1 &
PIDS+=($!)
python3 sector/scripts/fetch_general_news.py   --date $SCAN_DATE > /tmp/fetch_gnews.log 2>&1 &
PIDS+=($!)
FAIL=0
for pid in "${PIDS[@]}"; do wait $pid || FAIL=$((FAIL+1)); done
echo "parallel fetches: 4 launched, $FAIL failed"
ls -la sector/cache/sector_earnings_pulse_*.json sector/cache/sector_smart_money_*.json \
       sector/cache/sector_news_*.json sector/cache/general_news_*.json | head -4
```

- `FAIL` 計數需 ≤ 1（只允許 `fetch_general_news` 這個 SOFT 項失敗）
- 任一 HARD script fail → 看 `/tmp/fetch_*.log`；通常是 FMP rate limit 或 API key
- **何時改回 sequential**：需要看單一 script 的詳細 stderr，或要加
  `--skip-analyst` / `--skip-institutional` 等 flag

### Steps 3b/3c/3d/3e — sequential 版（偵錯用）

| Step | 指令 | 輸出 | 失敗層級 |
|---|---|---|---|
| 3b | `python3 sector/scripts/fetch_earnings_pulse.py --date {SCAN_DATE}` | `sector/cache/sector_earnings_pulse_<DATE>.json` | **HARD**（earnings calendar 段；analyst 段 SOFT）|
| 3c | `python3 sector/scripts/fetch_smart_money.py --date {SCAN_DATE}` | `sector/cache/sector_smart_money_<DATE>.json` | **HARD**（insider/senate 段；institutional 段 SOFT）|
| 3d | `python3 sector/scripts/fetch_sector_news.py --date {SCAN_DATE} --lookback-days 2` | `sector/cache/sector_news_<DATE>.json`（11 sectors × top 10）| **HARD** |
| 3e | `python3 sector/scripts/fetch_general_news.py --date {SCAN_DATE}` | `sector/cache/general_news_<DATE>.json`（limit=20）| **SOFT**（寫 `{available:false, reason}`）|

省 call 的 flag（V2.9.0+）：`--skip-analyst`（3b，省 ~111 calls；舊名 `--skip-grades` 仍接受）、
`--skip-institutional`（3c，省 ~131 calls）。

⚡ **這四個 cache 都不要手抄進 JSON** —— `build_sector_intel.py` 會自己讀進
`_phase3.sector_earnings_pulse` / `_phase3.smart_money_signals` 等。確認 rc=0、cache 產生即可。

### Phase 3 耗時預算

| Step | Tool | 耗時 |
|---|---|---|
| 1 | `market-sentiment-analyzer` script | ~6s |
| 2 | `economic-calendar-fetcher` script | ~5s |
| 3 | `earnings-calendar` script | ~5s |
| 3b | `fetch_earnings_pulse.py`（含 grades-summary） | ~30s |
| 3c | `fetch_smart_money.py` | ~25s |
| 3d | `fetch_sector_news.py` | ~10s |
| 3e | `fetch_general_news.py`（soft） | ~3s |
| 4 | reuse `_phase0.fred_snapshot` | 0s |
| 5 | WebSearch ≤ 1（Case A）/ ≤ 2（Case B） | ~10–20s |

**總預算 ≤ 110s**

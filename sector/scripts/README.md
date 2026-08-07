# sector/scripts — 執行細節

fetch 腳本由 protocol Phase 1 / Phase 3 觸發（不是 daily cron）；HARD 層輸出寫到 `sector/cache/<name>_<DATE>.json`，calendar 輔助層輸出 stdout JSON。

| 腳本 | Phase | Hardness | 主 endpoint |
|---|---|---|---|
| `fetch_sector_valuation.py` | P1 | **HARD** — `sys.exit(1)` 並中止 protocol | `/stable/sector-pe-snapshot`、`/stable/historical-sector-pe`、`/stable/historical-price-eod/light`（5d/20d/3M 多週期 RS 重用同一支 chart） |
| `fetch_earnings_pulse.py` | P3 Step 3b | **HARD（核心）+ SOFT（analyst 段）** | 分段＋2h cache 的 `/stable/earnings-calendar` + 可選 `/stable/grades-consensus`（V1.71+）+ `/stable/price-target-consensus` + `/stable/batch-quote-short`（V2.9.0+） |
| `fetch_smart_money.py` | P3 Step 3c | **HARD（核心）+ SOFT（institutional 段）** | `/stable/insider-trading/statistics`、`/stable/senate-latest` + `/stable/institutional-ownership/symbol-positions-summary`（V2.9.0+） |
| `fetch_sector_news.py` | P3 Step 3d | **HARD** | `/stable/news/stock` |
| `fetch_general_news.py` | P3 Step 3e | **SOFT** — 失敗寫 `{available: false}`，protocol 續跑 | `/stable/news/general-latest` |
| `fetch_earnings_calendar.py` | P3 Step 3 | **SOFT** | `/stable/earnings-calendar` + `/stable/company-screener`；本機 join，無 per-symbol profile fan-out |

## 為什麼 P1/P3 是 HARD-FAIL

V1.4 protocol decision：`sector_valuation`、`earnings_pulse`、`smart_money`、`sector_news` 是 verdict score 的關鍵 input；缺值會導致 `valuation_penalty`、`news_catalyst`、`Phase 4b divergence` 三個位置失準，最終 verdict 不可信。所以寧可 abort 由人介入修 `$FMP_API_KEY` / FMP 服務，也不 silent fallback。

`general_news` 是 Phase 3 Step 5 narrative WebSearch 的補位 — 即使 FMP 失敗，WebSearch 可以接手，所以走 SOFT。

## Retry 策略

`scripts/_shared/fmp_pool.py`（所有上述 FMP fetch 共用）：
- cross-process rolling window 預設 220 RPM
- 429 → 遵守 `Retry-After`（若有）或 exponential backoff，最多 retries+1 次
- 最新 429 的安全化 response body / `Retry-After` 保存至 `~/.cache_bridge/fmp_last_429.json`（不含 API key）
- 其他例外 → `time.sleep(0.5)` 再 retry
- 連續失敗 → hard_fail=True 走 `sys.exit`；hard_fail=False 印錯誤到 stderr 回 `None`

## 執行範例

```bash
python3 sector/scripts/fetch_sector_valuation.py --date 2026-05-02
python3 sector/scripts/fetch_earnings_pulse.py --date 2026-05-02
python3 sector/scripts/fetch_earnings_pulse.py --date 2026-05-02 --skip-analyst   # 省 ~111 calls（grades + PT consensus）
python3 sector/scripts/fetch_smart_money.py --date 2026-05-02
python3 sector/scripts/fetch_smart_money.py --date 2026-05-02 --skip-institutional  # 省 ~131 calls
python3 sector/scripts/fetch_sector_news.py --date 2026-05-02 --lookback-days 2
python3 sector/scripts/fetch_general_news.py --date 2026-05-02
python3 sector/scripts/fetch_earnings_calendar.py 2026-05-02 2026-05-09
```

## 共用模組

`sector/lib/fmp_client.py`：`fmp_get()`、`cache_path()`、`SECTOR_UNIVERSE` / `TICKER_TO_SECTOR` / `SECTOR_TOP_5`（後三者轉 re-export 自 `skills/_shared/company_context`）。

`sector/lib/date_utils.py`：`lookback_window()`、`cutoff_date()`、`latest_complete_13f_quarter()`（13F 申報截止 45 天 lag）。

`sector/lib/earnings_calendar.py`：calendar exact-range 2h cache；回傳達 4,000 筆時自動二分日期區間並去重，單日仍飽和則 fail closed。Upcoming calendar 另以 24h cached company screener 做全市場 US $2B+ 篩選，不逐檔抓 profile。

未來工作（form13f / paid endpoints / MCP runtime）見 `sector/BACKLOG.md`。

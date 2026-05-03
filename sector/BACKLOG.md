# Sector Protocol — Deferred / Future Work

## form13f_top10_delta（fetch_smart_money.py）— V2.9.0 已取代

V2.8.x 之前此欄位永遠為 null（FMP `/stable/form-13f-summary` 在 free tier 回 402）。

V2.9.0 改用 `/stable/institutional-ownership/symbol-positions-summary?symbol=X&year=Y&quarter=Q` 對 SECTOR_UNIVERSE 全 ticker aggregate，新增 `institutional_holders_qoq_delta` / `institutional_ownership_pct_delta` 兩個欄位。13F 申報截止為季末後 45 天（helper `latest_complete_13f_quarter` 處理）。

`form13f_top10_delta` 欄位保留向後相容（永遠 null），新代碼用 `institutional_*` 系列。

## acquisition-of-beneficial-ownership — 已評估、不採用

V2.9.0 規劃時測過 `/stable/acquisition-of-beneficial-ownership?symbol=X` 想補 13D/13G 訊號，但實測 mega-cap 數據過時：

```
AAPL: total=127, last_180d=0, latest=2024-02-14
NVDA: total=47,  last_180d=0, latest=2024-07-18
TSLA: total=92,  last_180d=0, latest=2022-03-11
JPM:  total=735, last_180d=0, latest=2024-10-30
```

mega-cap 觸發 13D/13G（≥5%）門檻太高（要持有 1 兆美元 AAPL 股票才有 5%），實務上大部分公司最近一年沒有新增 filing。signal 對 sector aggregate 太稀疏，不採用。改走 institutional-ownership/symbol-positions-summary（涵蓋全部 13F holder 的 Q-on-Q 變動，不是只看 ≥5% 大股東）。

## analyst_revision_net（fetch_earnings_pulse.py）

V1.71+ 改用 `/stable/grades-consensus` 對 SECTOR_TOP_5（55 calls/round）填值；`--skip-grades`（V2.9.0+ alias 到 `--skip-analyst`）旗標可關。

- 失敗模式：任何 ticker 失敗 → 該 sector 改聚合剩下成功的；全失敗 → 該 sector null
- rubric 目前不依賴此欄位，純供 Devil's Advocate / 人工 review

## MCP vs HTTP runtime path

Python script 不能直接呼叫 MCP tools（runtime 限制）。`reference/FMP_MCP_TOOLS_中文參考_v5_03.md` 是 MCP 介面對照表，但實際 fetch 全走 HTTP REST。MCP 端點命名與 HTTP path 對應在 `sector/scripts/README.md`。

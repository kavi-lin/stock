# Initiating Coverage 首次覆蓋報告 — 格式規格（V4.69.0）

> 本檔是 `compose_initiation.py` 產出格式的規格文件（同 `template.md` 之於
> `compose.py`）。渲染完全 deterministic（0 LLM）；所有決策數字 verbatim 自
> protocol history 的 decision_lock payload，估值模型數字 verbatim 自
> valuation-modeler payload cache。

## 前置條件

1. `investment/invest_logs/history.json` 有該 ticker 的 protocol session entry
   （沒跑過 `分析 [TICKER]` 就沒有首次覆蓋的決策內容可引）
2. `skills/valuation-modeler/cache/<T>_dcf_payload.json` + `<T>_comps_payload.json`
   （由 `dcf.py <T>` / `comps.py <T>` 任一模式執行時自動持久化）
3. earnings-analyst cache（可缺 → 對應節 degraded，同 ic_memo 規則）

## 產出流程

```bash
python3 skills/valuation-modeler/scripts/dcf.py <T> --json-only     # 如 cache 缺
python3 skills/valuation-modeler/scripts/comps.py <T> --json-only   # 如 cache 缺
python3 skills/ic-memo-writer/scripts/build_fact_pack.py <T> --initiation
python3 skills/ic-memo-writer/scripts/compose_initiation.py <T>
python3 skills/ic-memo-writer/scripts/validate_ic_memo.py reports/<DATE>_<T>_initiation.md --initiation
```

輸出：`reports/YYYYMMDD_<T>_initiation.md`

## 章節結構

| 節 | 內容 | 來源 |
|---|---|---|
| Header | 「Initiating Coverage」+ 評級/合理價/verdict 一行 | sec_1 verbatim |
| §1 一頁摘要 | action/confidence/sizing/entry/stop/TP/RR | `render_sec_1`（重用） |
| §2 公司與商業模式 | profile description + meta | `render_sec_2`（重用） |
| §3 收入結構與成長驅動 | segments + growth | `render_sec_3`（重用） |
| §4 客戶/供應商/競爭格局 | peer descriptor + 競爭 | `render_sec_4`（重用） |
| §5 最新財務與申報重點 | earnings cache | `render_sec_5`（重用） |
| §6 資產負債表與現金流品質 | earnings cache | `render_sec_6`（重用） |
| §7 盈利能力與 2-3 年模型 | earnings cache | `render_sec_7`（重用） |
| §8 估值總覽 | DCF/multiples/PT/peer | `render_sec_8`（重用） |
| **§8a Fair-value anchors** | 8-anchor 表 + 權重 + verdict | `render_anchor_table`（新） |
| **§8b 自建 driver-based DCF** | 假設 provenance 表 + FCFF 投影 + 5×5 sensitivity | `render_dcf_model`（新） |
| **§8c 同業比較** | peer multiples 全表 + implied values + anchor | `render_comps_model`（新） |
| §9 催化劑與風險 | catalysts + key_risks + kill conditions | `render_sec_9`（重用） |
| §10 Bull/Base/Bear | scenario odds | `render_sec_10`（重用） |
| §11 委員會結論 | decision_lock verbatim | `render_sec_11`（重用） |
| §12 附錄 | provenance roster + degraded + hashes | `render_sec_12`（重用） |

## Validator（`--initiation` 模式新增檢查）

- **F-I1**（fatal）：initiation 專屬區塊缺失（header 標記、§8a/8b/8c、兩個
  valuation_modeler provenance 標記）
- **F-I2**（fatal）：fact_pack 缺 `valuation_model` block（不是用 `--initiation` build 的）
- **F-I3**（fatal）：DCF fair value / comps anchor 數字未 verbatim 出現在 MD
- 其餘沿用 ic_memo 檢查（decision_lock hash、§11 verbatim、禁重評分片語…）

## 紀律（與 ic-memo 相同）

- 不重評分、不改 history.json、不產生新判斷——只重排既有事實
- LLM 唯一參與點：無（V1.0 deterministic-only）
- 首次覆蓋 ≠ 重新分析：要新判斷先跑 `分析 [TICKER]`，再重 build fact pack

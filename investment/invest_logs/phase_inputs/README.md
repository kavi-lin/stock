# `phase_inputs/` — Phase 5 renderer 的第二份輸入（V4.87.0）

一次 deep dive 一個檔：`<YYYY-MM-DD>_<TICKER>.json`。

## 這是什麼

`render_investment_report.py` 吃兩份 artifact：

| 輸入 | 是什麼 | 誰產生 |
|---|---|---|
| `history.json` 末筆 | 決策記錄。所有決策關鍵數字的唯一權威 | `append_session_export.py` |
| `phase_inputs/<DATE>_<TICKER>.json` | Phase 0 / 2 證據包 | PM 在 Phase 5 Step 4a 用 Write 寫入 |

## 為什麼要落地存檔

這包**就是**以前貼進 Sonnet formatter prompt 的同一份資料。報告裡約 80 行（五個 lane 的
`key_factors` / `risk_flags` / raw signal / confidence、Burry components、Phase 0 明細）
只有這裡有來源——`history.json` 從未持久化它們。貼進 prompt 的版本渲染完就消失，報告因此
有一大段內容無從稽核、無從重現。寫成檔案之後這段來源跟決策記錄一樣長存。

## 為什麼不乾脆存進 `history.json`

「per-lane 該持久化哪些欄位」是 **C1（統一 lane 資料契約）** 要定的事。現在為了報告先開一版
schema 把這些欄位塞進去，等於在 C1 定案前預判它的設計，C1 落地時同一塊結構要再遷移一次。
所以先當獨立 artifact；C1 定案後 `--phase-inputs` 的依賴會自然縮小甚至消失。

**這批檔案同時是 C1 design 的實測樣本** —— 累積幾份之後就能回答「哪些欄位每次都在、哪些
其實沒人用」，不必憑空設計。

## Shape

完整欄位說明見 `investment/investment_protocol_v5_0.md` §PHASE 5 Step 4a，
以及 `render_investment_report.py` 的 module docstring。

```json
{
  "bundle_version": "P5-INPUTS/1.0",
  "ticker": "MU", "date": "2026-08-02",
  "phase0":  { "regime_confidence": 0.6, "market_top_zone": "Orange", "…": "…" },
  "lanes":   { "fundamentals|sentiment|news|technical|valuation": {
                 "signal": "BUY", "score": 1.5, "confidence": 0.72,
                 "phase0_alignment": "MISALIGNED",
                 "key_factors": ["…"], "risk_flags": ["…"] } },
  "burry":   { "score": 47.1, "label": "NEUTRAL", "veto_flag": false, "components": {} },
  "phase3":  { "final_score": -0.2963, "final_decision": "HOLD", "final_action": "CANCEL" },
  "phase4":  { "position_size_pct": 0.0, "analysis_price": 823.03 },
  "red_team":{ "verdict": "STRONG_COUNTER" }
}
```

`phase3` / `phase4` / `burry` / `red_team` 與 `history.json` 重複**是刻意的**：renderer 用它們
交叉驗證這包抄的是不是本次 session 的輸出。任一欄與決策記錄不符 → rc=1，不產出報告。

## 現有檔案

| 檔 | provenance | 說明 |
|---|---|---|
| `2026-08-02_MSFT.json` | **backfill** | V4.87.0 dev session 事後回填，內容逐字取自已發布的 `reports/20260802_MSFT.md` §3／§5 與 history 末筆，**不是**決策當下 PM 寫入的原件。存在的理由：L3 落地時樣本數為零，C1 的 lane 契約設計需要真實欄位形狀當輸入。已驗過重疊欄位硬閘 0 error。 |

**回填只做這一份。** MU 那筆的 lane 證據在 `test_render_investment_report.py` 裡是為了測
`calculation_steps` 硬閘現編的合成資料（`key_factors` 並非 MU 真實 Phase 2 輸出），把它寫進這裡
等於在稽核軌跡放一份假證據——正是本目錄存在要防的事。

PM 在 Phase 5 Step 4a 寫入的檔案**不得**帶 `provenance.captured = "backfill"`；往後每一份都應是
session 當下產生的原件。

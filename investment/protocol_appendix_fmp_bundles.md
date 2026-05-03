# Investment Protocol — FMP Bundles Appendix

> Detailed schemas + injection rules for the 3 data bundles loaded in Phase 1.
> Main protocol references this file via `protocol_appendix_fmp_bundles.md`.

---

## 1. EARNINGS_ANALYST_BUNDLE（optional cache read, 0 FMP call）

### Trigger
Phase 1 末段檢查 `skills/earnings-analyst/cache/<TICKER>_*.json`。**不**自動 enqueue `財報` protocol — 那是 user 主動觸發層。

### Freshness rules
- cache 必須含 `composite_score`（代表 analyze.py 已跑完）
- 距 cache 檔 mtime ≤ 90 天（對齊 earnings-analyst CACHE_TTL_DAYS）

### Bundle shape

```python
ea = json.load(open("skills/earnings-analyst/cache/<TICKER>_<DATE>.json"))
EARNINGS_ANALYST_BUNDLE = {
  "last_earnings_date":  ea["last_earnings_date"],
  "next_earnings_est":   ea.get("next_earnings_est"),
  "composite_score":     ea["composite_score"],
  "verdict":             ea["verdict"],
  "score_components":    ea["score_components"],
  "quality_flags":       ea.get("quality_flags") or [],
  "margins_8q":          (ea.get("derived") or {}).get("margins_8q"),
  "yoy_growth":          (ea.get("derived") or {}).get("yoy_growth"),
  "balance_health":      (ea.get("derived") or {}).get("balance_health"),
  "cash_flow_quality":   (ea.get("derived") or {}).get("cash_flow_quality"),
  "valuation": {
    "dcf_intrinsic":          (ea.get("valuation") or {}).get("dcf_intrinsic"),
    "dcf_levered_intrinsic":  (ea.get("valuation") or {}).get("dcf_levered_intrinsic"),
    "dcf_vs_price_pct":       (ea.get("valuation") or {}).get("dcf_vs_price_pct"),
    "price_target_consensus": (ea.get("valuation") or {}).get("price_target_consensus"),
    "pt_upside_pct":          (ea.get("valuation") or {}).get("pt_upside_pct"),
    "pt_dispersion_pct":      (ea.get("valuation") or {}).get("pt_dispersion_pct"),
    "pt_news":                (ea.get("valuation") or {}).get("pt_news") or [],
  },
  "analyst": {
    "rating_trend":   (ea.get("analyst") or {}).get("rating_trend"),
    "grades_summary": (ea.get("analyst") or {}).get("grades_summary"),
    "grades_news":    (ea.get("analyst") or {}).get("grades_news") or [],
  },
  "report_path":  "reports/<DATE>_<TICKER>_earnings.md"
}
```

### Injection rules
- ✅ Fundamentals lane + **Valuation Specialist lane**（V5.0 新增）
- ❌ Sentiment / News / Technical lane（避免 cross-lane anchoring）
- 不得修改 cache 內容；不得 mirror `composite_score / verdict` 為 lane score

### Fallback
若 cache 不存在或過期 → bundle 設 `not available`，Fundamentals 與 Valuation lane 標註，**不**中止 protocol。

---

## 2. PEER_BUNDLE（MUST fetch, 2-7 FMP call w/ 24h cache）

### Trigger
Phase 1 末段 PM **MUST** 取得同業 peer set，供 Fundamentals + Burry + Valuation lane 做 relative valuation 量化。

### Fetch
```python
import sys
sys.path.insert(0, ".")
from skills._shared.company_context import get_peers, get_profile
from statistics import median

peers_raw = get_peers(TICKER)[:5]
peer_profiles = {p: get_profile(p) for p in peers_raw}
peer_profiles = {p: prof for p, prof in peer_profiles.items() if prof}
```

### Bundle shape
```python
def _med(field):
    vals = [prof.get(field) for prof in peer_profiles.values() if prof.get(field) is not None]
    return median(vals) if vals else None

PEER_BUNDLE = {
  "peers":                  list(peer_profiles.keys()),
  "peer_pe_median":         _med("peRatio"),
  "peer_market_cap_median": _med("marketCap"),
  "peer_beta_median":       _med("beta"),
  "peer_sector":            (get_profile(TICKER) or {}).get("sector"),
}
```

### Failure modes
- `len(peer_profiles) < 3` → `PEER_BUNDLE = {"status": "insufficient_peers", "peers": [...]}`
- `get_peers()` 回 `[]` → `PEER_BUNDLE = {"status": "unavailable"}`
- Fundamentals / Burry / Valuation lane 自動 fallback 到 sector median rubric，**不**中止 protocol

### Injection rules
- ✅ Fundamentals + Burry + **Valuation Specialist** (V5.0)
- ❌ Sentiment / News / Technical
- PM 在 Phase 2.5 conflict resolution **不得**用 PEER_BUNDLE 數字作裁量（lane 內部證據）

---

## 3. FMP_SUPP_BUNDLE（MUST fetch, 2-6 FMP call w/ 24h cache）

### Trigger
Phase 1 末段取 FMP 補充束，補 dual-fetch 與 EARNINGS_ANALYST_BUNDLE 之外的高價值欄位。

### Fetch
```python
import sys
sys.path.insert(0, ".")
from skills._shared.fmp_supplementary import get_supplementary_bundle
FMP_SUPP_BUNDLE = get_supplementary_bundle(TICKER)
# 失敗 → None
```

### Bundle sections（V1.88 schema）
- `quality_scores`: Altman Z-Score, Piotroski F-Score（含 `altman_zone` ∈ {danger, grey, safe} + `piotroski_strength` ∈ {weak, moderate, strong}）
- `owner_earnings`: Buffett owner earnings (latest Q + qoq_growth)
- `insider_summary`: 季度內部人交易統計
- `institutional`: 機構持股 QoQ 變化
- `congressional_trades`: senate + house 議員交易
- `ma_events`: 近 90 日 M&A 事件
- `executive_compensation`: CEO + 前 5 高薪 comp（V5.0 新增）
- `comp_benchmark`: comp vs peer median（V5.0 新增）
- `employee_history`: 5 年雇員 CAGR（V5.0 新增）

### Injection rules
| Lane | 注入欄位 |
|---|---|
| Fundamentals | `quality_scores`, `owner_earnings`, `employee_history` |
| Sentiment | `insider_summary`, `institutional`, `congressional_trades`, `executive_compensation` |
| News | `ma_events` |
| Burry | `quality_scores`, `owner_earnings`, `insider_summary`, `comp_benchmark` |
| Valuation Specialist (V5.0) | `quality_scores`, `owner_earnings` |
| Technical | ❌ 不注入（OHLCV-only） |

### Failure
- `FMP_SUPP_BUNDLE is None` → 全部 lane 注入省略，標 `unavailable — fallback to skill-internal sources`
- 個別 section `{}` → 對應 rubric skip（lane 不得猜值）

### Physical isolation
- FMP-only。**不得**混入 dual_fetch `scoring.*` 欄位
- 24h cache @ `skills/_shared/fmp_supp_cache/<TICKER>_<DATE>_supp.json`
- 純讀，lane subagent 禁改

---

## Cross-bundle rules

1. **No cross-anchoring**：lane 不得引用其他 lane 看到的 bundle 欄位推測對方結論
2. **No PM bias injection**：bundle 數字不得進 PM 的 Phase 2.5 conflict resolution 裁量
3. **Cache discipline**：所有 bundle 走 24h cache，跨 ticker session 內重複呼叫 0 FMP call
4. **Failure isolation**：任一 bundle fail 不阻斷 protocol；對應 lane 標 fallback 但繼續執行

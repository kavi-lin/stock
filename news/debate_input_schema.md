# News Debate Input Schema (V1)

> Producer: four isolated Stage 2 lanes + PM metadata  
> Consumer: `news/scripts/finalize_digest.py`  
> Path: `news/news_logs/YYYY-MM-DD_debate.json`

此檔只保存 LLM 無法 deterministic 產生的判斷。權重、淨分、verdict、digest、Markdown 與 cache patch 全由 finalizer 產生，禁止在此重複。

## Required shape

```json
{
  "fanout_mode": "PER_AGENT_BATCH",
  "degraded_agents": [],
  "translations": {"n0001": "繁中標題"},
  "lanes": {
    "bull": {
      "subagent_isolated": true,
      "per_item": {
        "n0001": {"interpretation": "上行論點", "impact_score": 4, "confidence": 0.8}
      }
    },
    "bear": {
      "subagent_isolated": true,
      "per_item": {
        "n0001": {"interpretation": "下行論點", "impact_score": -2, "confidence": 0.7, "binary_risk": false}
      }
    },
    "sector": {
      "subagent_isolated": true,
      "per_item": {
        "n0001": {
          "impact_score": 3,
          "confidence": 0.8,
          "primary_sectors": [{"sector": "Semi", "direction": "bullish", "magnitude": "strong"}],
          "supply_chain_impact": "第二階供應鏈影響",
          "tickers_mentioned": ["NVDA"]
        }
      }
    },
    "macro": {
      "subagent_isolated": true,
      "per_item": {
        "n0001": {
          "impact_score": 0,
          "confidence": 0.7,
          "binary_risk": false,
          "fed_path_delta": "neutral",
          "yield_curve_impact": "none",
          "fx_commodity_impact": "none",
          "historical_analogue": "none"
        }
      }
    }
  },
  "arbiter": {
    "per_item": {
      "n0001": {
        "binary_risk": false,
        "binary_event_date": null,
        "within_48h": false,
        "macro_backdrop_delta": 0.2,
        "reasoning_note": "保留的定性判斷。",
        "debate_note": "最大分歧。",
        "evidence_urls": ["https://example.com/source"]
      }
    }
  }
}
```

## Constraints

- IDs 必須完整覆蓋 compact packet 的 Stage 2；`translations` 另須覆蓋 shallow top 10。
- Bull score `1..5`；Bear `-5..-1`；Sector/Macro `-5..5`；confidence `0..1`。
- LOW credibility 每 lane confidence ≤0.5；Bull/Bear 不得同時 `|score|≤1`。
- Binary 事件須有日期，且 Bear、Macro 都標 `binary_risk=true`。
- `PER_AGENT_BATCH` 時四 lane 的 `subagent_isolated` 全為 true。
- `PARTIAL_FALLBACK` 時 1–2 個 `degraded_agents` lane 必為 false 且 confidence ≤0.5；`FULL_FALLBACK` 時 3–4 個 degraded、四 lane 全為 false。
- 不輸出 `net_impact_score`、`verdict`、`weights_used`、shallow snaps 或 cache payload。

## Finalize

```bash
python3 news/scripts/finalize_digest.py \
  --date YYYY-MM-DD \
  --debate news/news_logs/YYYY-MM-DD_debate.json
```

rc=0 才算完成。finalizer 依序組裝 digest、跑 validator、idempotent patch cache、產 Markdown。

"""Reconciled token distributions and evidence-quality observation report."""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from urllib.parse import urlencode

from scripts._shared import broker_gate, research_accounting
from scripts.research.store import ROOT, now_iso, parse_time


def distribution(values, missing=0):
    values = sorted(values)
    return {"samples": len(values), "missing": missing, "sum": sum(values) if values else None,
            "mean": sum(values)/len(values) if values else None,
            "p50": values[math.ceil(len(values)*.50)-1] if values else None,
            "p95": values[math.ceil(len(values)*.95)-1] if values else None}


def tokens(record):
    facts = record.get("settlement", {}).get("usage_details", {}).get("facts", [])
    names = ("input_tokens", "output_tokens", "cache_read_tokens", "reasoning_tokens", "total_tokens")
    result = {k: sum(f["tokens"][k] for f in facts) if facts and all(
        f["tokens"].get(k) is not None for f in facts) else None for k in names}
    result["comparable_tokens"] = (result["input_tokens"] + result["output_tokens"]
                                   if result["input_tokens"] is not None and result["output_tokens"] is not None
                                   else None)
    return result


def reconcile_history(records, items):
    """The wrong-token control in tests must fail this same report boundary."""
    by_task = {i["task"]["task_id"]: i for i in items if i.get("execution")}
    counts = Counter(i['task']['task_id'] for i in items if i.get('execution'))
    errors = [{'call_id':task_id, 'error':'multiple_broker_executions', 'count':count}
              for task_id,count in counts.items() if count > 1]
    for record in records:
        item = by_task.get(record["call_id"])
        if not item:
            errors.append({"call_id": record["call_id"], "error": "broker_execution_missing"})
            continue
        try:
            research_accounting.reconcile(record, item)
            if item["task"].get("context") != record["context"]:
                raise ValueError("broker context mismatch")
        except Exception as exc:
            errors.append({"call_id": record["call_id"], "error": str(exc)[:160]})
    extras = set(by_task) - {r["call_id"] for r in records}
    errors.extend({"call_id": key, "error": "local_record_missing"} for key in extras)
    return errors


def broker_history(experiment_id):
    client = broker_gate.broker_client()
    result, cursor = [], None
    while True:
        query = {"project": broker_gate.BROKER_PROJECT, "experiment_id": experiment_id, "limit": 500}
        if cursor:
            query["cursor"] = cursor
        page = client.request("GET", "/v1/history?" + urlencode(query))
        result.extend(page["items"])
        cursor = page.get("next_cursor")
        if not cursor:
            return result


def summarize(records, cards):
    metrics = {}
    measured = [tokens(r) for r in records]
    for key in ("input_tokens", "output_tokens", "cache_read_tokens", "reasoning_tokens",
                "total_tokens", "comparable_tokens"):
        values = [row[key] for row in measured if row[key] is not None]
        metrics[key] = distribution(values, len(records)-len(values))
    debates = defaultdict(list)
    stages_by_debate = defaultdict(set)
    for record in records:
        debates[record["context"]["debate_id"]].append(tokens(record)["comparable_tokens"])
        if record.get("schema_valid") and record["status"] == "acknowledged":
            stages_by_debate[record["context"]["debate_id"]].add(record["context"]["stage"])
    totals = [sum(values) for values in debates.values() if all(v is not None for v in values)]
    accepted = [card for card in cards if card["status"] != "retracted"]
    complete = metrics["comparable_tokens"]["missing"] == 0
    return {"calls": len(records), "debates": len(debates), "valid_cards": len(accepted),
            "complete_debates": sum(stages == {"analysis", "challenge"} for stages in stages_by_debate.values()),
            "failed_calls": sum(not r.get("schema_valid") for r in records),
            "unacknowledged_calls": sum(r["status"] != "acknowledged" for r in records),
            "call_metrics": metrics, "tokens_per_debate": distribution(totals, len(debates)-len(totals)),
            "tokens_per_valid_card": metrics["comparable_tokens"]["sum"]/len(accepted)
            if accepted and complete else None,
            "statuses": dict(Counter(c["status"] for c in cards)),
            "claim_kinds": dict(Counter(c["kind"] for c in cards)),
            "current_cards": sum(not c.get('superseded') for c in cards),
            "events": len({c["event_id"] for c in cards}),
            "feed_only_cards": sum(not any(e.get("content_type") == "original_page_excerpt"
                                          for e in c.get("evidence", [])) for c in cards),
            "tickers": sorted({t for c in cards for t in c.get("tickers", [])}),
            "triggers": dict(Counter(r["context"]["trigger"] for r in records)),
            "trigger_debates": {trigger: len({r["context"]["debate_id"] for r in records
                                              if r["context"]["trigger"] == trigger})
                                for trigger in ("news", "filing", "calendar", "followup")},
            "stages": {stage: distribution([tokens(r)["comparable_tokens"] for r in records
                        if r["context"]["stage"] == stage and tokens(r)["comparable_tokens"] is not None],
                        sum(r["context"]["stage"] == stage and tokens(r)["comparable_tokens"] is None
                            for r in records))
                       for stage in ("analysis", "challenge")}}


def source_summary(history, started_at, deadline):
    """Poll observations are not unique articles; exclude development fetches."""
    start, end = parse_time(started_at), parse_time(deadline)
    samples = [row for row in history if start and parse_time(row.get("at"))
               and start <= parse_time(row["at"]) <= end]
    sources = {}
    for sample in samples:
        for name, status in sample.get("sources", {}).items():
            summary = sources.setdefault(name, {"polls": 0, "statuses": {}, "fetched_observations": 0,
                                                "fresh_observations": 0, "max_latency_ms": 0})
            summary["polls"] += 1
            key = status.get("status", "unknown")
            summary["statuses"][key] = summary["statuses"].get(key, 0) + 1
            summary["fetched_observations"] += status.get("fetched", 0)
            summary["fresh_observations"] += status.get("fresh", 0)
            summary["max_latency_ms"] = max(summary["max_latency_ms"], status.get("latency_ms", 0))
    return {"polls": len(samples), "sources": sources,
            "counting_unit": "source observations per poll; repeated articles are not unique events"}


def write_report(repo, experiment_id):
    from scripts.research.experiment import call_records
    from scripts.research.store import CACHE, Repository

    records = call_records(experiment_id)
    live_cards = [c for c in repo.all("cards") if c["experiment_id"] == experiment_id]
    preflight_path = CACHE / "preflight" / (experiment_id + ".sqlite3")
    preflight_cards = Repository(preflight_path).all("cards") if preflight_path.exists() else []
    state = repo.get("experiment", {})
    try:
        history = broker_history(experiment_id)
        reconciliation = reconcile_history(records, history)
    except Exception as exc:
        history, reconciliation = [], [{"error": "broker_history_unavailable", "type": type(exc).__name__}]
    elapsed = ((parse_time(state.get("finished_at")) or parse_time(now_iso())) - parse_time(state["started_at"])).total_seconds() if state.get("started_at") else 0
    final = elapsed >= 21600 and state.get("status") in {"complete", "complete_with_gaps"}
    phases = {phase: summarize([r for r in records if r["context"]["phase"] == phase], cards)
              for phase, cards in (("preflight", preflight_cards), ("live", live_cards))}
    executions = sum(bool(row.get('execution')) for row in history)
    report = {"schema_version": 1, "experiment_id": experiment_id, "generated_at": now_iso(),
              "final": final, "experiment": state, "elapsed_seconds": elapsed,
              "validation": repo.get("validation"), "phases": phases,
              "historical_baseline": repo.get("baseline"),
              "broker_reconciliation": {"matched": not reconciliation, "errors": reconciliation,
                                        "broker_executions": executions, "broker_history_rows": len(history),
                                        "reservations_without_execution": len(history)-executions,
                                        "local_calls": len(records)},
              "source_health": repo.get("source_health", {}), "intake": repo.get("last_poll"),
              "source_history": repo.get("source_history", []),
              "source_summary": source_summary(repo.get("source_history", []),
                                               state.get("started_at"), state.get("deadline")),
              "triggers": repo.get("trigger_health"),
              "integration_checks": repo.get("integration_checks", {}),
              "research_cards": [{k:c.get(k) for k in (
                  'id','event_id','event_revision','debate_id','tickers','headline','text','kind',
                  'status','challenge','falsifier','followup','created_at','superseded','trigger')}
                  | {'sources': [{'url':e['url'],'source':e.get('source'),
                                  'content_type':e.get('content_type')} for e in c.get('evidence',[])]}
                  for c in live_cards],
              "calls": [{k:v for k,v in r.items() if k != "result"} for r in records],
              "limitations": ["A/B 皆為 gpt-6-luna max；不是跨模型獨立驗證。",
                              "平均值包含失敗呼叫；缺失 token 不補零，分母僅含已測得樣本。",
                              "Codex cache input／reasoning 為子集合，不重複加總。",
                              "有效卡指通過格式及原文引用閘、未撤回的卡，仍包含爭議及證據不足；不等於已證實。",
                              "低事件量不補造事件；六小時結果不能代表長期投資績效。"]}
    path = ROOT / "reports" / ("research_observation_" + experiment_id)
    research_accounting.atomic_json(path.with_suffix(".json"), report)
    live = phases["live"]
    lines = [f'# 事件研究觀察報告：{experiment_id}', '',
             f'狀態：{"六小時結束" if final else "進度報告，尚未完成六小時觀察"}；{state.get("status", "未開始")}。',
             f'已觀察 {elapsed/3600:.2f} 小時；起點 {state.get("started_at", "尚未起算")}；終點 {state.get("deadline", "尚未設定")}。', '',
             '## 功能與驗證', '',
             '新聞、原始公告、排程發布與研究追蹤共用事件及主張資料。個股、財報、動能與 Nexus 顯示研究卡；正式投資決策與圖譜晉升門檻保留。', '',
             f'確定性驗證：{json.dumps(report["validation"], ensure_ascii=False)}', '',
             '## Token 與 Broker 對帳', '',
             '| 階段 | 呼叫 | 辯論嘗試 | 失敗呼叫 | 平均 token／呼叫 | P50 | P95 | 未知樣本 |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    def fmt(value):
        return '未知' if value is None else f'{value:,.1f}'
    for phase, values in phases.items():
        metric = values["call_metrics"]["comparable_tokens"]
        lines.append(f'| {phase} | {values["calls"]} | {values["debates"]} | {values["failed_calls"]} | {fmt(metric["mean"])} | {fmt(metric["p50"])} | {fmt(metric["p95"])} | {metric["missing"]} |')
    lines += [f'Broker 對帳：{"一致" if not reconciliation else "未通過"}；本地 {len(records)} 筆呼叫，Broker {executions} 筆 execution，另有 {len(history)-executions} 筆尚無 execution 的預約紀錄。',
              f'Live 平均 token／辯論：{fmt(live["tokens_per_debate"]["mean"])}；每張有效卡：{fmt(live["tokens_per_valid_card"])}。', '',
              '| Live 用量欄位 | 合計 | 平均／呼叫 | 缺失筆數 |', '|---|---:|---:|---:|']
    for key, metric in live['call_metrics'].items():
        lines.append(f'| {key} | {fmt(metric["sum"])} | {fmt(metric["mean"])} | {metric["missing"]} |')
    lines += ['',
              '## 來源與研究結果', '', f'主張狀態：{json.dumps(live["statuses"], ensure_ascii=False)}。',
              f'主張種類：{json.dumps(live["claim_kinds"], ensure_ascii=False)}；{live["events"]} 個事件產出卡片，{live["feed_only_cards"]} 張卡僅有 feed 摘錄。',
              f'可供個股頁篩選的 ticker：{", ".join(live["tickers"]) or "無"}。',
              f'觸發分布（呼叫數）：{json.dumps(live["triggers"], ensure_ascii=False)}。', '',
              '| 來源 | 狀態 | 取得 | 6 小時內 | HTTP |', '|---|---|---:|---:|---|']
    for case, result in state.get("cases", {}).items():
        if result.get("limitation"):
            lines.insert(5, f'初步案例 {case} 限制：{result["limitation"]}。')
    for name, health in report["source_health"].items():
        lines.append(f'| {name} | {health.get("status")} | {health.get("fetched", 0)} | {health.get("fresh", 0)} | {health.get("http_status", "—")} |')
    conclusion = ('已完成觀察，需先處理對帳或中斷問題。' if reconciliation or state.get("gaps") or state.get("blocker")
                  else '觀察期間對帳一致，可依有效研究卡與來源覆蓋調整下一輪取樣。') if final else '目前不能提供六小時有效性結論。'
    lines += ['', '## 結論與限制', '', conclusion,
              f'實際啟動 {live["debates"]}／30 次辯論嘗試，其中 {live["complete_debates"]} 次完成 A/B；使用 {live["calls"]}／60 次呼叫。上限不是必須填滿的樣本量。',
              f'四種觸發的辯論嘗試：{json.dumps(live["trigger_debates"], ensure_ascii=False)}；零樣本類別僅有初步案例／確定性測試覆蓋，不能宣稱已驗證真實事件表現。',
              *['- ' + item for item in report["limitations"]], '',
              '詳細逐筆用量、缺失欄位與對帳錯誤見同名 JSON。', '']
    gaps = state.get('gaps', [])
    lines += ['## 執行可靠性與來源觀察', '',
              f'觀察窗內完成 {report["source_summary"]["polls"]} 次取材。心跳超過 180 秒的區間 {len(gaps)} 段，共 {sum(g.get("seconds",0) for g in gaps):.1f} 秒；這是保守的中斷指標，不直接等同漏掉新聞數。',
              f'Broker provider_busy 等候後恢復 {len(state.get("provider_waits", []))} 次；只在 Broker 回報空閒後重新申請，不以模型呼叫探測狀態。',
              f'逐頁接線驗證：{json.dumps(report["integration_checks"], ensure_ascii=False)}。', '',
              '| 來源 | Poll 次數 | 狀態分布 | 最長毫秒 |', '|---|---:|---|---:|']
    for name, values in report['source_summary']['sources'].items():
        lines.append(f'| {name} | {values["polls"]} | {json.dumps(values["statuses"], ensure_ascii=False)} | {values["max_latency_ms"]} |')
    for incident in state.get('operational_incidents', []):
        lines += ['', f'執行事件：{incident["at"]}；{incident["cause"]}；修正：{incident["fix"]}。']
    if live_cards:
        # A bounded exhibit links the cost counters to actual reader-facing output.
        selected = []
        for predicate in (lambda c:c['kind']=='fact' and c['tickers'],
                          lambda c:c['kind']=='inference',
                          lambda c:c['status']=='insufficient',
                          lambda c:c['status'] in {'contested','retracted'},
                          lambda c:True):
            item = next((c for c in reversed(live_cards) if c not in selected and predicate(c)), None)
            if item:
                selected.append(item)
        lines += ['', '## 研究卡樣本', '',
                  f'資料庫保留本輪所有版本；目前 {live["current_cards"]} 張未被新版本取代。以下最多五例，完整卡片摘要及來源 URL 見 JSON。', '']
        for index, card in enumerate(selected, 1):
            provenance = '包含原始網頁片段' if any(e.get('content_type')=='original_page_excerpt'
                                                   for e in card.get('evidence', [])) else '只有來源摘要'
            lines += [f'{index}. **{", ".join(card["tickers"]) or "總體／未對應 ticker"}｜{card["kind"]}／{card["status"]}**（{provenance}）',
                      f'   {card["text"]}',
                      f'   審查：{card["challenge"]}',
                      f'   反證：{card["falsifier"]}；追蹤：{card["followup"]["condition"]}', '']
    if final:
        lines += ['', '## 本輪判斷', '',
                  ('用量治理驗收通過：每筆模型呼叫皆可對到 Broker，沒有以零取代未知用量。' if not reconciliation and
                   not live['unacknowledged_calls'] and not live['call_metrics']['comparable_tokens']['missing']
                   else '用量治理仍有缺口：應先補齊上列未知或未對帳紀錄，不能用目前平均數當完整成本。'),
                  f'本輪產出 {live["valid_cards"]} 張未撤回研究卡；支援項與爭議／不足項應分別閱讀，A/B 一致不代表多個獨立來源。',
                  '新機制可提供原文、主張、反證與追蹤條件給各分頁；本輪結果只驗證研究資料流及成本，不能推論交易績效。',
                  '下一輪優先處理反覆失敗來源、只有摘要的高影響事件，以及本輪沒有真實樣本的觸發類型。', '']
    baseline = report.get("historical_baseline") or {}
    if baseline:
        lines += ['## 舊機制比較', '',
                  f'歷史樣本 {baseline["events"]} 次辯論、{baseline["call_count"]} 次呼叫，平均 {baseline["calls_per_debate"]:.2f} 次呼叫／辯論；新機制每次完整辯論為兩次。',
                  f'歷史 token 可量測 {baseline["token_per_call"]["samples"]} 筆、缺失 {baseline["token_per_call"]["missing"]} 筆，不能據此宣稱精確節省比例；事件與模型組合亦不同。', '']
    path.with_suffix(".md").write_text('\n'.join(lines))
    return str(path.with_suffix(".md"))

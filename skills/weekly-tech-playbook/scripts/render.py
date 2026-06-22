#!/usr/bin/env python3
"""
render.py — Weekly Tech Playbook · sizing + render + validate (0 LLM)

Input : a selections JSON (authored by the LLM step; see SKILL.md schema).
Output: Dashboard/playbook.json  (consumed by Dashboard/page-playbook.js)
        reports/<DATE>_TECH_PLAYBOOK.md  (human-readable, review-ready)

For each basket it sizes conviction tiers into whole-share positions:
  shares = round(weight_usd / price), actual_cost = shares * price, leftover cash tracked.

Validation (rc): 0 = pass · 1 = fatal (basket != capital, missing price, <1 pick)
                 2 = degraded-usable (rounding drift > 2% of capital, missing committee data)

Usage:
  python3 render.py --selections data/selections_2026-06-22.json
  python3 render.py --selections data/selections_2026-06-22.json --validate-only
"""
import argparse
import datetime as _dt
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DASH_JSON = os.path.join(ROOT, "Dashboard", "playbook.json")
REPORTS = os.path.join(ROOT, "reports")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

TIER_LABEL = {"core": "核心", "standard": "標準", "light": "輕倉/樂透"}
TIER_ORDER = {"core": 0, "standard": 1, "light": 2}


def _fmt_usd(x):
    return f"${x:,.0f}"


def size_basket(basket, capital):
    """Return (sized_picks, summary, issues)."""
    issues = []
    picks = basket.get("picks", [])
    if not picks:
        issues.append(("fatal", "basket has 0 picks"))
        return [], {}, issues

    target_sum = sum(p.get("weight_usd", 0) for p in picks)
    if round(target_sum) != capital:
        issues.append(("fatal", f"weights sum to {target_sum:,} != capital {capital:,}"))

    sized = []
    actual_total = 0.0
    theme_alloc = {}
    for p in picks:
        price = p.get("price")
        w = p.get("weight_usd", 0)
        if not price or price <= 0:
            issues.append(("fatal", f"{p.get('ticker')} missing/invalid price"))
            shares, cost = 0, 0.0
        else:
            shares = round(w / price)
            cost = round(shares * price, 2)
        actual_total += cost
        theme_alloc[p.get("theme", "—")] = theme_alloc.get(p.get("theme", "—"), 0) + w
        if not p.get("committee"):
            issues.append(("degraded", f"{p.get('ticker')} no committee verdict"))
        sized.append({
            **p,
            "tier_label": TIER_LABEL.get(p.get("tier"), p.get("tier")),
            "shares": shares,
            "actual_cost": cost,
            "weight_pct": round(w / capital * 100, 1) if capital else 0,
        })

    sized.sort(key=lambda x: (TIER_ORDER.get(x.get("tier"), 9), -x.get("weight_usd", 0)))
    drift = abs(actual_total - capital)
    if drift > capital * 0.02:
        issues.append(("degraded", f"rounding drift {_fmt_usd(drift)} > 2% of capital"))

    summary = {
        "n_picks": len(picks),
        "target_capital": capital,
        "actual_deployed": round(actual_total, 2),
        "leftover_cash": round(capital - actual_total, 2),
        "theme_allocation": dict(sorted(theme_alloc.items(), key=lambda kv: -kv[1])),
        "tier_breakdown": {
            "core": sum(1 for p in picks if p.get("tier") == "core"),
            "standard": sum(1 for p in picks if p.get("tier") == "standard"),
            "light": sum(1 for p in picks if p.get("tier") == "light"),
        },
    }
    return sized, summary, issues


def validate_codex_review(review):
    """Validate the independent review without mutating the original baskets."""
    issues = []
    # The independent review is OPTIONAL — the playbook must render standalone so
    # the weekly generator never blocks on a second opinion being authored first.
    # When present, it is validated; when absent, generation proceeds clean.
    if not review:
        return []

    for field in ("label", "reviewed_on", "review_mode", "committee_dependency", "dependency_note", "verdict"):
        if not review.get(field):
            issues.append(("fatal", f"codex_review missing {field}"))
    # Blind-then-reconcile is the anti-anchoring gold standard; only enforce the
    # blind artifact when that mode is actually claimed — don't degrade by default
    # (that flagged every non-blind review, including ones that never claimed it).
    if review.get("review_mode") == "committee_blind_then_reconcile" and not review.get("blind_artifact"):
        issues.append(("fatal", "committee-blind codex_review missing blind_artifact"))

    notes = review.get("comparison_notes", [])
    if len(notes) < 3:
        issues.append(("fatal", "codex_review needs at least 3 comparison_notes"))
    for i, item in enumerate(notes):
        for field in ("title", "original", "note"):
            if not item.get(field):
                issues.append(("fatal", f"codex_review comparison_notes[{i}] missing {field}"))

    allocation = review.get("recommended_allocation", [])
    if not allocation:
        issues.append(("fatal", "codex_review missing recommended_allocation"))
    total_weight = sum(item.get("weight_pct", 0) for item in allocation)
    if abs(total_weight - 100) > 0.01:
        issues.append(("fatal", f"codex_review allocation sums to {total_weight}% != 100%"))
    tickers = [item.get("ticker") for item in allocation]
    if len(tickers) != len(set(tickers)):
        issues.append(("fatal", "codex_review allocation contains duplicate tickers"))
    for i, item in enumerate(allocation):
        if not item.get("ticker") or not item.get("role") or item.get("weight_pct", 0) <= 0:
            issues.append(("fatal", f"codex_review recommended_allocation[{i}] is incomplete"))

    if not review.get("execution"):
        issues.append(("fatal", "codex_review missing execution rules"))
    if len(review.get("sources", [])) < 2:
        issues.append(("degraded", "codex_review has fewer than 2 sources"))
    return issues


def build_payload(sel):
    capital = sel.get("capital_per_basket", 100000)
    out_baskets = {}
    all_issues = []
    for key, basket in sel.get("baskets", {}).items():
        sized, summary, issues = size_basket(basket, capital)
        all_issues += [(key, lvl, msg) for lvl, msg in issues]
        out_baskets[key] = {
            "label_zh": basket.get("label_zh", key),
            "label_en": basket.get("label_en", key),
            "thesis": basket.get("thesis", ""),
            "summary": summary,
            "picks": sized,
        }
    all_issues += [("codex_review", lvl, msg) for lvl, msg in validate_codex_review(sel.get("codex_review"))]
    payload = {
        "as_of": sel.get("as_of"),
        "week_label": sel.get("week_label"),
        "capital_per_basket": capital,
        "tier_weights": sel.get("tier_weights"),
        "macro": sel.get("macro", {}),
        "discipline_note": sel.get("discipline_note", ""),
        "author": sel.get("author"),
        "codex_review": sel.get("codex_review"),
        "baskets": out_baskets,
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
    }
    return payload, all_issues


def render_md(payload):
    p = payload
    L = []
    L.append(f"# 下週科技投資方案 — 三籃子 $100k Playbook ({p['as_of']})\n")
    L.append(f"> **適用週**: {p.get('week_label','')}  |  **每籃資金**: {_fmt_usd(p['capital_per_basket'])}  |  **配重**: 核心 $15k×3 / 標準 $10k×4 / 輕倉 $5k×3")
    L.append(f"> **產出**: weekly-tech-playbook skill · render.py  |  **紀律**: {p.get('discipline_note','')}\n")

    m = p.get("macro", {})
    L.append("## 市場背景\n")
    L.append(f"- **Regime**: {m.get('regime','')} · 建議{m.get('exposure_ceiling','')}")
    L.append(f"- **Breadth**: {m.get('breadth','')} · **Market Top**: {m.get('market_top','')}")
    L.append(f"- **情緒**: {m.get('sentiment','')}")
    L.append(f"- **實質利率**: {m.get('real_rate_10y','')}")
    if m.get("key_events"):
        L.append(f"- **關鍵事件**: " + " · ".join(m["key_events"]))
    if m.get("playbook_logic"):
        L.append(f"\n> {m['playbook_logic']}\n")

    review = p.get("codex_review")
    if review:
        L.append("\n---\n\n## Codex Review — 原文與建議附註\n")
        L.append(f"> **複核日期**: {review.get('reviewed_on', '')}  |  **結論**: {review.get('verdict', '')}\n")
        L.append(f"> **Review mode**: `{review.get('review_mode', '')}`  |  **委員會依賴度**: **{review.get('committee_dependency', '')}**  "
                 f"\n> {review.get('dependency_note', '')}\n")
        L.append("| 主題 | 原報告 | Codex Review 附註 |")
        L.append("|---|---|---|")
        for item in review.get("comparison_notes", []):
            L.append(f"| **{item.get('title', '')}** | {item.get('original', '')} | {item.get('note', '')} |")

        allocation = review.get("recommended_allocation", [])
        if allocation:
            L.append("\n### Codex 替代配置\n")
            L.append("| 標的 | 配重 | 定位 |")
            L.append("|---|---:|---|")
            for item in allocation:
                L.append(f"| **{item.get('ticker', '')}** | {item.get('weight_pct', 0)}% | {item.get('role', '')} |")

        if review.get("execution"):
            L.append("\n### 執行紀律\n")
            for item in review["execution"]:
                L.append(f"- {item}")

        if review.get("sources"):
            links = [f"[{item.get('label', '')}]({item.get('url', '')})" for item in review["sources"]]
            L.append("\n**Codex Review 資料來源**: " + " · ".join(links) + "\n")

    for key in ["conservative", "aggressive", "hybrid"]:
        b = p["baskets"].get(key)
        if not b:
            continue
        s = b["summary"]
        icon = {"conservative": "🛡️", "aggressive": "🔥", "hybrid": "⚖️"}.get(key, "")
        L.append(f"\n---\n\n## {icon} {b['label_zh']}籃子 — {_fmt_usd(s['target_capital'])} ({b['label_en']})\n")
        L.append(f"> {b['thesis']}\n")
        L.append(f"**部署 {_fmt_usd(s['actual_deployed'])} · 餘現金 {_fmt_usd(s['leftover_cash'])} · "
                 f"{s['n_picks']} 檔 (核心 {s['tier_breakdown']['core']}/標準 {s['tier_breakdown']['standard']}/輕 {s['tier_breakdown']['light']})**\n")
        L.append("| 檔 | 配重 | 股數 | 實際成本 | 話題 | 理由 + 數據 | Kill |")
        L.append("|---|---|---|---|---|---|---|")
        for pk in b["picks"]:
            sleeve = f" _{pk['sleeve']}_" if pk.get("sleeve") else ""
            L.append(f"| **{pk['ticker']}**{sleeve} | {_fmt_usd(pk['weight_usd'])} ({pk['weight_pct']}%) "
                     f"| {pk['shares']} | {_fmt_usd(pk['actual_cost'])} | {pk.get('theme','')} "
                     f"| {pk.get('reason','')}；{pk.get('data','')}{(' · 委員會: '+pk['committee']) if pk.get('committee') else ''} "
                     f"| {pk.get('kill','')} |")

    L.append("\n---\n\n## 📋 下週 LLM 檢討 Scaffold\n")
    L.append(f"> 進場參考價 = 各檔 price 欄（資料快照日 {p['as_of']}；實際交易前須核對最新成交價）。下週同日抓收盤,逐檔算報酬、籃子報酬 vs SPY、命中率 (上漲檔/10),對照 Kill 欄判斷論點是否被打破。\n")
    L.append("| 籃子 | 檔 | 進場參考 | 股數 | Kill 訊號 |")
    L.append("|---|---|---|---|---|")
    for key in ["conservative", "aggressive", "hybrid"]:
        b = p["baskets"].get(key)
        if not b:
            continue
        for pk in b["picks"]:
            L.append(f"| {b['label_zh']} | {pk['ticker']} | {pk['price']} | {pk['shares']} | {pk.get('kill','')} |")
    L.append("\n**檢討輸出建議**: 每籃報酬 vs SPY、命中率、被觸發 Kill 的標的、待驗證催化兌現與否、以及「保險 vs 激進 vs 混合 哪個贏 + 為什麼」一段話。\n")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selections", required=True)
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    with open(args.selections, "r", encoding="utf-8") as f:
        sel = json.load(f)

    payload, issues = build_payload(sel)

    fatal = [i for i in issues if i[1] == "fatal"]
    degraded = [i for i in issues if i[1] == "degraded"]

    print(f"=== render Weekly Tech Playbook {payload['as_of']} ===")
    for key in ["conservative", "aggressive", "hybrid"]:
        b = payload["baskets"].get(key)
        if not b:
            continue
        s = b["summary"]
        print(f"  {b['label_zh']:4} {s['n_picks']} 檔 · 部署 {_fmt_usd(s['actual_deployed'])} "
              f"· 餘 {_fmt_usd(s['leftover_cash'])}")
    if fatal:
        print("\nFATAL:")
        for k, _l, msg in fatal:
            print(f"  [{k}] {msg}")
    if degraded:
        print(f"\nDEGRADED ({len(degraded)}): " + "; ".join(f"[{k}] {msg}" for k, _l, msg in degraded[:8]))

    rc = 1 if fatal else (2 if degraded else 0)

    if args.validate_only:
        print(f"\nvalidate-only rc={rc}")
        return rc
    if fatal:
        print(f"\nrc={rc} — fatal issues, not writing outputs")
        return rc

    with open(DASH_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    # dated machine snapshot — immutable entry record so review.py can replay a
    # past week's playbook after Dashboard/playbook.json is overwritten next run.
    os.makedirs(DATA_DIR, exist_ok=True)
    snap_path = os.path.join(DATA_DIR, f"playbook_{payload['as_of']}.json")
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    md_path = os.path.join(REPORTS, f"{payload['as_of']}_TECH_PLAYBOOK.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_md(payload))

    print(f"\nWrote {DASH_JSON}")
    print(f"Wrote {snap_path}")
    print(f"Wrote {md_path}")
    print(f"rc={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

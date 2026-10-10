"""One presentation of the shared earnings comparison object (no calculations of verdicts)."""
from pathlib import Path

from earnings_history import ROOT, period_label

STATUS = {"exceeded": "超標", "met": "達標", "missed": "未達標", "pending": "待到期", "unverifiable": "無法驗證"}
REASONS = {
    "target_not_reported": "目標期間尚未完整公布",
    "legacy_no_verifiable_contract": "舊摘要補建：缺乏可驗證的原始口徑／門檻",
    "target_period_unknown": "目標期間不明",
    "qualitative_no_numeric_criterion": "定性觀察，未設定數值驗收門檻",
    "invalid_expectation_contract": "原預期欄位不完整",
    "conflicting_actuals": "同口徑實際值互相衝突",
    "basis_mismatch": "會計、幣別、匯率或業務口徑不一致",
    "actual_unavailable": "缺少同期間、同指標的實際值",
    "release_date_unavailable": "無法確認目標財報公布日",
    "not_recorded_before_release": "預期未在目標財報公布前留下可驗證紀錄",
    "same_period_same_basis": "同期間、同口徑比較",
}
ORIGINS = {"management": "公司指引", "consensus": "市場共識", "analysis": "分析預期", "legacy": "歷史摘要"}


def cell(value):
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def link(ref, label="來源"):
    if not ref:
        return "來源不足"
    if ref.startswith(("https://", "http://")):
        dest = ref
    else:
        path = Path(ref)
        if not path.is_absolute():
            path = ROOT / path
        dest = path.as_posix()
    return f"[{label}](<{dest}>)"


def value(actual):
    if not actual or actual.get("value") is None:
        return "—"
    v = actual["value"]; unit = actual.get("unit")
    if unit == "ratio":
        return f"{v * 100:.2f}%"
    suffix = actual.get("currency") or ("幣別未記錄" if unit in {"currency", "currency_per_share"} else "")
    if unit == "currency_per_share":
        return f"{v:,.2f} {suffix}"
    if unit == "currency":
        display = f"{v / 1e9:,.2f}B" if abs(v) >= 1e9 else f"{v / 1e6:,.2f}M" if abs(v) >= 1e6 else f"{v:,.0f}"
        return f"{display} {suffix}"
    return f"{v:,.0f} {suffix}".strip()


def change(row, kind):
    d = row[kind]
    if d["delta"] is None:
        return "—（缺資料／口徑不符）"
    if row["unit"] == "ratio":
        return f"{d['delta'] * 100:+.2f} 個百分點"
    if d["pct"] is not None:
        return f"{d['pct'] * 100:+.2f}%"
    return f"差額 {d['delta']:+,.4f}（前值 ≤ 0，不算成長率）"


def target(e):
    if e.get("operator") == "range":
        return value({**e, "value": e["low"]}) + "～" + value({**e, "value": e["high"]})
    if e.get("operator") in {"gte", "lte"}:
        return ("≥ " if e["operator"] == "gte" else "≤ ") + value({**e, "value": e["threshold"]})
    return "原文觀察，未設數值門檻"


def render_comparison(d):
    c = d.get("comparison")
    if not c:
        return []
    context = c["context"]; previous = c["previous_analysis"]
    lines = ["## 本季變化與前次追蹤", "",
             f"**本季：{period_label(context['fiscal_period'])}｜財報評分 {d.get('composite_score', '—')}/100 · {d.get('verdict', '—')}**",
             f"會計期末：{context['fiscal_period_end']}；財報公布日：{context['earnings_release_date'] or '無法確認'}。", "",
             "### 這季比上季如何", "",
             "| 指標 | 上一季 | 本季 | 季變化 | 年變化 |",
             "|---|---:|---:|---:|---:|"]
    for row in c["financial_changes"]:
        source = (row.get("current") or {}).get("source_ref")
        lines.append(f"| {link(source, row['label'])} | {value(row['previous_quarter'])} | {value(row['current'])} | {change(row, 'qoq')} | {change(row, 'yoy')} |")
    lines += ["", "財務比較採本次取得的歷史三表；B＝十億、M＝百萬。舊快取幣別未記錄時僅比較原始數列，不用於指引達標判定。", ""]
    if previous["status"] == "available":
        lines.append(f"前次分析：{period_label(previous['fiscal_period'])}，記錄於 {previous['recorded_at']}；{link(previous['source_ref'], '查看原紀錄')}。")
        if previous.get("quarters_apart") != 1:
            lines.append(f"前次分析與本次相隔 {previous.get('quarters_apart', '未知')} 季；上表仍比較相鄰財季。")
        flags = c["quality_flag_changes"]
        lines.append("品質警訊（與前次分析比較）：新增 " + cell(", ".join(flags["new"]) or "無") +
                     "；持續 " + cell(", ".join(flags["continuing"]) or "無") +
                     "；解除 " + cell(", ".join(flags["resolved"]) or "無") + "。")
    else:
        lines.append("沒有前次分析紀錄；財務數據仍可與快取內的上一季比較。")
    lines += ["", "### 上次說的，這次做到嗎", ""]
    if not c["expectation_audit"]:
        lines.append("沒有可核對的前次預期紀錄。這不代表全部達標。")
    else:
        lines += ["| 當時說法／來源 | 目標期間／門檻 | 本次證據 | 判定與原因 |", "|---|---|---|---|"]
        for row in c["expectation_audit"]:
            e = row["expectation"]; actual = row["actual"]
            src = link(e.get("source_ref") or e.get("original_ref"), "原紀錄")
            evidence = value(actual) + (" · " + link(actual.get("source_ref")) if actual else "")
            lines.append(f"| {cell(ORIGINS.get(e.get('origin'), e.get('origin')))}：{cell(e.get('statement'))} · {src} | {period_label(e.get('target_period'))}；{target(e)} | {evidence} | **{STATUS[row['status']]}**：{REASONS.get(row['reason'], cell(row['reason']))} |")
    if c.get("watch_audit"):
        lines += ["", "前次觀察清單回訪（只比較基準變化，不計預測命中）：", "",
                  "| 觀察項目 | 當時基準 | 目標期實際值 | 變化 |", "|---|---|---|---|"]
        directions = {"up": "增加", "down": "減少", "flat": "持平", "unavailable": "缺資料／口徑不符"}
        for row in c["watch_audit"]:
            w = row["watch"]
            lines.append(f"| {cell(w['statement'])} | {value(w['baseline'])} | {value(row['actual'])} | {directions[row['direction']]} |")
    lines += ["", "### 下次要驗證什麼", ""]
    if c["next_expectations"]:
        lines += ["| 類型／預期 | 目標期間 | 驗收門檻 | 來源 |", "|---|---|---|---|"]
        for e in c["next_expectations"]:
            lines.append(f"| {ORIGINS[e['origin']]}：{cell(e['statement'])} | {period_label(e['target_period'])} | {target(e)} | {link(e['source_ref'])} |")
    else:
        lines.append("本次沒有取得可結構化的未來指引／預期；以下保留觀察項目，不作預測命中率計算。")
    lines += ["", "| 觀察項目 | 目標期間 | 本季基準 |", "|---|---|---|"]
    for w in c["next_watchlist"]:
        lines.append(f"| {cell(w['statement'])} | {period_label(w['target_period'])} | {value(w['baseline'])} |")
    for warning in c["warnings"]:
        lines += ["", f"> 資料提醒：{cell(warning)}"]
    lines += ["", "預期驗收是獨立追蹤欄位；沿用現有財報評分與投資決策規則。", ""]
    return lines

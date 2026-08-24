#!/usr/bin/env python3
"""render_investment_report.py — Phase 5 deterministic MD renderer (V4.87.0, 0 LLM by default).

Replaces the Sonnet MD Formatter Agent call. The report is now *rendered* from two
persisted artifacts rather than *written* by a model:

    1. one session export object (or legacy `history.json` last entry) — the decision record. Every
       decision-critical number comes from here, verbatim (the six `<!--FACTS:*-->`
       blocks are the same renderers `inject_report_facts.py` already used, imported
       rather than copied so the two can never drift).

    2. `investment/invest_logs/phase_inputs/<DATE>_<TICKER>.json` — the Phase 0/2
       evidence bundle the PM assembles. This is the SAME payload that used to be
       pasted into the formatter's prompt (per-lane key_factors / risk_flags / signal /
       confidence, Burry components, Phase 0 detail). Writing it to disk instead of
       into a prompt is what makes the report reproducible: previously ~80 lines of the
       report had a source that evaporated the moment the formatter finished.

Why two inputs and not one: `history.json` does not persist per-lane key_factors /
risk_flags (only `news_lane` has them), has no `sentiment_lane` block at all, and
carries raw signal/confidence for the valuation lane only. Persisting those is the
subject of C1 (統一 lane 資料契約) — pre-empting its field design here would force a
second migration. So the bundle stays a separate artifact, and when C1 lands the
`--phase-inputs` dependency shrinks or disappears with no rework here.

**Overlap consistency gate (rc=1).** The two inputs overlap — lane scores, raw
confidence, final_score / decision / action, position size, analysis price, Burry
score. Two sources means two-source drift, so every overlapping field is cross-checked
before a single byte is rendered, INCLUDING against the `calculation_steps` step
strings, which record the exact score and quantised confidence the decision math ran
on. A mismatch aborts with rc=1 rather than producing a report whose prose contradicts
the decision record.

**`--polish` (default OFF).** Five segments are pure narrative and exist in no JSON
field: the 決議摘要 sentence, Consensus View, Differentiated View, Bull Case, Bear
Case. Without the flag they render as formulaic sentences derived from the JSON — 0
LLM, byte-stable, what CI tests. With the flag one governed LLM call rewrites those
five and only those five, subject to three guards that all fail *open* (discard the
polish, keep the deterministic text, warn on stderr — the report always ships):

    guard 1  structural: every non-narrative byte must be identical after substitution
    guard 2  numeric containment: every number in a polished segment must exist in the
             bundle / history / deterministic report — the real risk is not prose
             quality, it is a model inventing a plausible "+43%"
    guard 3  routing: the call goes through `model_router` (accounted, budgeted,
             cooldown-aware) and the footer stamps which model touched which segments

Usage:
    python3 investment/scripts/render_investment_report.py
    python3 investment/scripts/render_investment_report.py --polish
    python3 investment/scripts/render_investment_report.py --polish-model codex --polish
    python3 investment/scripts/render_investment_report.py \
        --history H.json --phase-inputs B.json --out /tmp/r.md      # tests

rc=0 rendered (polish failures degrade, they do not fail the run);
rc=1 missing input / consistency gate violation / unwritable output.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# The six decision-critical blocks keep exactly one implementation. `inject_report_facts`
# stays the owner (it still refreshes already-published reports); this module imports it.
from inject_report_facts import (  # noqa: E402
    RENDERERS as FACT_RENDERERS, fmt, fmt_position_size)
from decision_engine import c_eff  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HISTORY_JSON = os.path.join(ROOT, "investment/invest_logs/history.json")
PHASE_INPUTS_DIR = os.path.join(ROOT, "investment/invest_logs/phase_inputs")
REPORTS_DIR = os.path.join(ROOT, "reports")

RENDERER_VERSION = "1.0.0"
RENDERER_LABEL = f"render_investment_report.py v{RENDERER_VERSION} (V4.87.0)"
BUNDLE_VERSION = "P5-INPUTS/1.0"

LANE_ORDER = ("fundamentals", "sentiment", "news", "technical", "valuation")
LANE_LABEL = {"fundamentals": "Fundamentals", "sentiment": "Sentiment", "news": "News",
              "technical": "Technical", "valuation": "Valuation"}
# `calculation_steps` key per lane — the Phase 3 engine's own naming.
STEP1_KEY = {"fundamentals": "fund", "sentiment": "sent", "news": "news",
             "technical": "tech", "valuation": "val"}

NARRATIVE_KEYS = ("decision_summary_line", "consensus_view", "differentiated_view",
                  "bull_case", "bear_case")
NARRATIVE_LABEL = {
    "decision_summary_line": "決議摘要敘事句",
    "consensus_view": "Consensus View（市場共識）",
    "differentiated_view": "Differentiated View（本委員會差異化判斷）",
    "bull_case": "Bull Case",
    "bear_case": "Bear Case",
}
NARRATIVE_RE = re.compile(
    r"<!--NARRATIVE:([a-z_]+):start-->.*?<!--NARRATIVE:\1:end-->", re.DOTALL)


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _f(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return float(x)


def _v(x):
    """`fmt` treats bool as a number (bool subclasses int) and renders `True`. Every
    other flag in these reports reads as JSON — keep them lowercase."""
    if isinstance(x, bool):
        return "true" if x else "false"
    return fmt(x)


def _money(v):
    if isinstance(v, bool):
        return _v(v)
    return fmt(v, money=True)


def _pct(v):
    return fmt(v, pct=True)


def _price_range(v):
    """`["410", "427"]` → `$410.00 – $427.00`. The shared FACTS blocks print the raw
    list (byte-locked, unchanged); this is for the tables this renderer owns."""
    if isinstance(v, (list, tuple)) and len(v) == 2:
        out = []
        for x in v:
            if isinstance(x, str):
                try:
                    x = float(x.replace("$", "").replace(",", "").strip())
                except ValueError:
                    return fmt(v)
            f = _f(x)
            if f is None:
                return fmt(v)
            out.append(f"${f:,.2f}")
        return " – ".join(out)
    return _money(v)


def _bullets(items, prefix="- "):
    items = [str(i).strip() for i in (items or []) if str(i).strip()]
    return "\n".join(f"{prefix}{i}" for i in items) if items else "- N/A"


def _narrative_block(name, text):
    return (f"<!--NARRATIVE:{name}:start-->\n{text.strip()}\n"
            f"<!--NARRATIVE:{name}:end-->")


def _facts_block(name, trade):
    return (f"<!--FACTS:{name}:start-->\n{FACT_RENDERERS[name](trade)}\n"
            f"<!--FACTS:{name}:end-->")


# ---------------------------------------------------------------------------
# input loading
# ---------------------------------------------------------------------------

def load_history(path):
    with open(path, encoding="utf-8") as fp:
        hist = json.load(fp)
    if isinstance(hist, dict):
        entry = hist
    elif isinstance(hist, list) and hist:
        entry = hist[-1]
    else:
        raise SystemExit("[render] ✗ session export 必須是 object 或非空 history array")
    trades = entry.get("trades_this_session") or []
    if not trades or not isinstance(trades[0], dict):
        raise SystemExit("[render] ✗ session export 無 trades_this_session")
    return entry, trades[0]


def default_bundle_path(entry, trade):
    date = entry.get("export_date") or entry.get("date") or ""
    ticker = entry.get("ticker") or trade.get("ticker") or ""
    return os.path.join(PHASE_INPUTS_DIR, f"{date}_{ticker}.json")


def load_bundle(path):
    if not os.path.exists(path):
        raise SystemExit(
            f"[render] ✗ phase_inputs bundle 不存在: {path}\n"
            f"         Phase 5 Step 4 需 PM 先寫入這包（Phase 0 + 5 lane + Burry + Red Team）。\n"
            f"         格式見 render_investment_report.py 的 BUNDLE SHAPE 註解。")
    with open(path, encoding="utf-8") as fp:
        bundle = json.load(fp)
    if not isinstance(bundle, dict):
        raise SystemExit(f"[render] ✗ bundle 非 JSON object: {path}")
    return bundle


# ---------------------------------------------------------------------------
# overlap consistency gate
# ---------------------------------------------------------------------------

_STEP_RE = re.compile(
    r"^\s*(-?[\d.]+)\s*×\s*(-?[\d.]+)\s*×\s*(-?[\d.]+)\s*=\s*(-?[\d.]+)")


def parse_step(s):
    """`"0.25 × 1.5 × 0.60 = 0.2250"` → (weight, score, c_eff, overridden).

    `overridden` marks a step whose score deliberately differs from the score the lane
    itself reported — Step 1.5 (structural shift) rewrites the valuation lane's input
    score and records why in a trailing `// ...` note, e.g.
    `0.15 × -1.5 × 0.60 = -0.1350  // Step 1.5 CONFIRMED: … score 0.0 → -1.5`.
    Comparing the bundle's lane score against that number would flag every CONFIRMED
    entry as a mismatch, so the score check is skipped there; the c_eff check is not,
    because no adjustment touches confidence quantisation.

    Returns None when the step records a MISSING lane (no numbers to check).
    """
    if not isinstance(s, str):
        return None
    m = _STEP_RE.match(s)
    if not m:
        return None
    return (float(m.group(1)), float(m.group(2)), float(m.group(3)), "//" in s)


def _close(a, b, tol=1e-6):
    return a is not None and b is not None and abs(a - b) <= tol


def check_consistency(entry, trade, bundle):
    """Cross-check every field the two inputs both carry. Returns a list of errors;
    empty means the bundle and the decision record agree and rendering may proceed.

    Two-source drift is the inherent risk of a two-input renderer: a PM who assembles
    the bundle from a stale scratchpad produces a report whose evidence section argues
    for a different score than the decision it reports. The `calculation_steps` strings
    are the strongest available witness — they record the exact score and quantised
    confidence the Phase 3 math consumed — so they are checked whenever present.
    """
    errors = []

    bt, bd = bundle.get("ticker"), bundle.get("date")
    ht = entry.get("ticker") or trade.get("ticker")
    hd = entry.get("export_date") or entry.get("date")
    if bt and ht and bt != ht:
        errors.append(f"ticker 不符：bundle {bt!r} vs history {ht!r}")
    if bd and hd and bd != hd:
        errors.append(f"date 不符：bundle {bd!r} vs history {hd!r}")

    lanes = bundle.get("lanes") or {}
    hist_scores = trade.get("lane_scores") or {}
    steps = trade.get("calculation_steps") or {}

    for lane in LANE_ORDER:
        blk = lanes.get(lane)
        if not isinstance(blk, dict):
            continue
        b_score = _f(blk.get("score"))
        # history's own record of the same score
        if lane == "valuation":
            h_score = _f((trade.get("valuation_lane") or {}).get("score"))
        else:
            h_score = _f(hist_scores.get(lane))
        if b_score is not None and h_score is not None and not _close(b_score, h_score):
            errors.append(f"{LANE_LABEL[lane]} score 不符：bundle {b_score} vs history {h_score}")

        parsed = parse_step(steps.get(STEP1_KEY[lane])) if steps else None
        if parsed is None:
            continue
        _w, s_score, s_ce, overridden = parsed
        if b_score is not None and not overridden and not _close(b_score, s_score):
            errors.append(
                f"{LANE_LABEL[lane]} score 不符：bundle {b_score} vs calculation_steps "
                f"{s_score}（決策數學實際吃的值）")
        b_conf = _f(blk.get("confidence"))
        if b_conf is not None:
            want = c_eff(b_conf)
            if want is None or not _close(want, s_ce, 1e-9):
                errors.append(
                    f"{LANE_LABEL[lane]} confidence 帶域不符：bundle raw {b_conf} → "
                    f"c_eff {want} vs calculation_steps {s_ce}")

    # Phase 3 / 4 scalars the bundle may restate.
    p3 = bundle.get("phase3") or {}
    for key, label in (("final_score", "final_score"), ("avg_confidence", "avg_confidence")):
        bv, hv = _f(p3.get(key)), _f(trade.get(key))
        if bv is not None and hv is not None and not _close(bv, hv, 1e-4):
            errors.append(f"{label} 不符：bundle {bv} vs history {hv}")
    for key in ("final_decision", "final_action"):
        bv, hv = p3.get(key), trade.get(key)
        if bv and hv and bv != hv:
            errors.append(f"{key} 不符：bundle {bv!r} vs history {hv!r}")

    p4 = bundle.get("phase4") or {}
    for key, tol in (("position_size_pct", 1e-6), ("analysis_price", 1e-4)):
        bv, hv = _f(p4.get(key)), _f(trade.get(key))
        if bv is not None and hv is not None and not _close(bv, hv, tol):
            errors.append(f"{key} 不符：bundle {bv} vs history {hv}")

    b_burry = _f((bundle.get("burry") or {}).get("score"))
    h_burry = _f(trade.get("burry_score"))
    if b_burry is not None and h_burry is not None and not _close(b_burry, h_burry, 1e-4):
        errors.append(f"burry_score 不符：bundle {b_burry} vs history {h_burry}")

    b_rt = (bundle.get("red_team") or {}).get("verdict")
    h_rt = trade.get("red_team_verdict")
    if b_rt and h_rt and b_rt != h_rt:
        errors.append(f"red_team_verdict 不符：bundle {b_rt!r} vs history {h_rt!r}")

    return errors


# ---------------------------------------------------------------------------
# formulaic narrative (the 0-LLM default for the five polish-eligible segments)
# ---------------------------------------------------------------------------

def formulaic_narrative(entry, trade, bundle):
    ticker = entry.get("ticker") or trade.get("ticker") or "N/A"
    lanes = bundle.get("lanes") or {}
    scores = trade.get("lane_scores") or {}

    def lane_bit(lane):
        blk = lanes.get(lane) or {}
        sig = blk.get("signal")
        sc = blk.get("score")
        if sc is None:
            sc = ((trade.get("valuation_lane") or {}).get("score")
                  if lane == "valuation" else scores.get(lane))
        if sc is None:
            return None
        return f"{LANE_LABEL[lane]} {sig or '—'} ({fmt(sc)})"

    bits = [b for b in (lane_bit(l) for l in LANE_ORDER) if b]

    ranked = []
    for lane in LANE_ORDER:
        sc = ((trade.get("valuation_lane") or {}).get("score")
              if lane == "valuation" else scores.get(lane))
        if _f(sc) is not None:
            ranked.append((LANE_LABEL[lane], _f(sc)))
    ranked.sort(key=lambda kv: kv[1])

    mhp = trade.get("multi_horizon_price_framework") or {}
    st = mhp.get("short_term_5d") or {}
    mid = mhp.get("mid_term_60d") or {}
    band = st.get("band_capped") or st.get("band") or []
    kl = (trade.get("technical_lane") or {}).get("key_levels") or {}
    kills = trade.get("red_team_kill_conditions") or []

    summary = (
        f"本次委員會對 {ticker} 的判定為 {fmt(trade.get('final_decision'))}"
        f"（action: {fmt(trade.get('final_action'))}），"
        f"final_score {fmt(trade.get('final_score'))} / 3.0、"
        f"decision_confidence {_pct(trade.get('decision_confidence_pct'))}、"
        f"position_size {fmt_position_size(trade.get('position_size_pct'))}；"
        f"Red Team {fmt(trade.get('red_team_verdict'))}。")

    consensus = "Lane 訊號分佈：" + "／".join(bits) + "。" if bits else "Lane 訊號分佈：N/A。"
    news_blk = lanes.get("news") or {}
    ac = news_blk.get("analyst_consensus") or (trade.get("news_lane") or {}).get("analyst_consensus")
    if ac:
        consensus += f" analyst_consensus：{ac}。"
    if ranked:
        consensus += (f" 最高分 lane 為 {ranked[-1][0]}（{fmt(ranked[-1][1])}），"
                      f"最低分為 {ranked[0][0]}（{fmt(ranked[0][1])}）。")

    diff = fmt(trade.get("decision_margin"))
    if diff == "N/A":
        diff = (f"委員會結論 {fmt(trade.get('final_decision'))}，"
                f"final_score {fmt(trade.get('final_score'))} / 3.0。")
    # Decision-time value first, det_shadow as fallback — same precedence V20-A5 set for
    # the dashboard badge, so the report and the badge can never disagree on which
    # polarization label was in force.
    steps = trade.get("calculation_steps") or {}
    pol = (steps.get("polarization_modulation") or {}).get("label")
    pol_src = "calculation_steps"
    if not pol:
        pol = (trade.get("det_shadow") or {}).get("signal_polarization")
        pol_src = "det_shadow"
    if pol:
        diff += (f" polarization={pol}（來源 {pol_src}）；"
                 f"macro_alignment={fmt(trade.get('macro_alignment'))}；"
                 f"red_team={fmt(trade.get('red_team_verdict'))}。")

    bull = (f"上檔參考：60 日 mid_target {_money(mid.get('mid_target'))}"
            f"（成立條件：{fmt(mid.get('reality_check_note'))}）；"
            f"關鍵阻力 {_money(kl.get('resistance'))}。")
    bear_lo = band[0] if len(band) == 3 else None
    bear = (f"下檔紀律：跌破 5 日帶下界 {_money(bear_lo)} 或 support "
            f"{_money(kl.get('support'))} 即退出；stop_loss {_money(trade.get('stop_loss'))}，"
            f"另有 {len(kills)} 條 kill conditions 見上節。")

    return {"decision_summary_line": summary, "consensus_view": consensus,
            "differentiated_view": diff, "bull_case": bull, "bear_case": bear}


# ---------------------------------------------------------------------------
# deterministic sections
# ---------------------------------------------------------------------------

def sec_macro(entry, trade, bundle):
    snap = entry.get("phase0_macro_snapshot") or {}
    p0 = bundle.get("phase0") or {}
    out = ["## Phase 0 宏觀背景", ""]
    ctx = trade.get("macro_context")
    if ctx:
        out += [str(ctx).strip(), ""]
    rows = [("market_regime", snap.get("market_regime")),
            ("macro_backdrop_score", snap.get("macro_backdrop_score")),
            ("macro_multiplier", snap.get("macro_multiplier")),
            ("macro_alignment", trade.get("macro_alignment"))]
    for key in ("regime_confidence", "market_top_zone", "market_top_score", "ftd_state",
                "breadth_composite", "vix", "fear_greed", "fred_verdict", "real_rate_pct",
                "dgs10_pct"):
        if p0.get(key) is not None:
            rows.append((key, p0.get(key)))
    out += ["| 指標 | 值 |", "|---|---|"]
    out += [f"| {k} | {fmt(v)} |" for k, v in rows]
    themes = snap.get("key_themes") or p0.get("key_themes") or []
    if themes:
        out += ["", "**關鍵主題**", _bullets(themes)]
    for label, key in (("hot sectors", "hot_sectors"), ("cold sectors", "cold_sectors")):
        vals = p0.get(key)
        if vals:
            out += ["", f"**{label}**：" + "、".join(str(v) for v in vals)]
    return "\n".join(out)


def _lane_header(lane, blk, trade):
    scores = trade.get("lane_scores") or {}
    score = blk.get("score")
    if score is None:
        score = ((trade.get("valuation_lane") or {}).get("score")
                 if lane == "valuation" else scores.get(lane))
    conf = blk.get("confidence")
    if conf is None and lane == "valuation":
        conf = (trade.get("valuation_lane") or {}).get("confidence")
    sig = blk.get("signal") or ((trade.get("valuation_lane") or {}).get("signal")
                                if lane == "valuation" else None)
    parts = [f"{fmt(sig)}", f"Score {fmt(score)}", f"Conf {fmt(conf)}"]
    align = blk.get("phase0_alignment")
    tail = f"｜phase0_alignment: {align}" if align else ""
    return f"### {LANE_LABEL[lane]}（{', '.join(parts)}{tail}）"


def sec_lane_detail(trade, bundle):
    lanes = bundle.get("lanes") or {}
    out = ["## 詳細評分", ""]
    for lane in LANE_ORDER:
        blk = lanes.get(lane)
        if not isinstance(blk, dict):
            out += [f"### {LANE_LABEL[lane]}",
                    "", "_bundle 未提供本 lane 的 Phase 2 輸出（key_factors / risk_flags 無來源）_", "", "---", ""]
            continue
        out += [_lane_header(lane, blk, trade), ""]
        if blk.get("key_factors"):
            out += ["**Key Factors**", _bullets(blk["key_factors"]), ""]
        if blk.get("risk_flags"):
            out += ["**Risk Flags**", _bullets(blk["risk_flags"]), ""]
        out += _lane_extras(lane, blk, trade)
        out += ["---", ""]
    out += _sec_contrarian(trade, bundle)
    return "\n".join(out)


def _lane_extras(lane, blk, trade):
    """History-side lane blocks, rendered verbatim. These are already persisted, so they
    are decision-record content, not bundle content."""
    out = []
    if lane == "fundamentals":
        fl = trade.get("fundamentals_lane") or {}
        # Real entries carry `moat_assessment` both ways: a structured block on some
        # sessions, a single prose line on others. Rendering only the dict shape would
        # silently drop the moat call on every entry that used the string form.
        moat = fl.get("moat_assessment")
        if isinstance(moat, dict) and moat:
            out += [f"**Moat**：{fmt(moat.get('level'))} — {fmt(moat.get('type'))}"]
            if moat.get("evidence_one_line"):
                out += ["", f"> {moat['evidence_one_line']}"]
            out += [""]
        elif isinstance(moat, str) and moat.strip():
            out += [f"**Moat**：{moat.strip()}", ""]
        if fl.get("bull_thesis_one_line"):
            out += [f"**Bull Thesis**：{fl['bull_thesis_one_line']}", ""]
        if fl.get("bear_thesis_one_line"):
            out += [f"**Bear Thesis**：{fl['bear_thesis_one_line']}", ""]
        cats = fl.get("near_term_catalysts") or []
        if cats:
            out += ["**Near-term Catalysts**", "",
                    "| 日期 | 類型 | 影響 | 說明 |", "|---|---|---|---|"]
            out += [f"| {fmt(c.get('date'))} | {fmt(c.get('type'))} | {fmt(c.get('impact'))} | "
                    f"{fmt(c.get('description'))} |" for c in cats if isinstance(c, dict)]
            out += [""]
    elif lane == "news":
        nl = trade.get("news_lane") or {}
        if nl.get("reasoning_one_line"):
            out += [f"**Reasoning**：{nl['reasoning_one_line']}", ""]
        cat = nl.get("immediate_catalyst_5d")
        if isinstance(cat, dict):
            cat_s = (f"{fmt(cat.get('event'))}（{fmt(cat.get('date'))}，lean "
                     f"{fmt(cat.get('direction_lean'))}，expected_move "
                     f"{fmt(cat.get('expected_move_pct'))}）")
        else:
            cat_s = fmt(cat)
        prm = nl.get("pt_revision_momentum") or {}
        if prm or cat is not None or nl.get("decision_point_days") is not None:
            out += [f"pt_revision_momentum：{fmt(prm.get('direction'))}"
                    f"（1M {_pct(prm.get('consensus_delta_pct_1m'))}／"
                    f"3M {_pct(prm.get('consensus_delta_pct_3m'))}）；"
                    f"decision_point_days {fmt(nl.get('decision_point_days'))}；"
                    f"immediate_catalyst_5d {cat_s}", ""]
        spill = nl.get("cross_asset_spillover") or []
        if spill:
            out += ["**Cross-asset Spillover**", "", "| 資產 | 方向 | 機制 |", "|---|---|---|"]
            out += [f"| {fmt(s.get('asset'))} | {fmt(s.get('direction'))} | {fmt(s.get('mechanism'))} |"
                    for s in spill if isinstance(s, dict)]
            out += [""]
    elif lane == "technical":
        tl = trade.get("technical_lane") or {}
        pat = tl.get("pattern_taxonomy") or {}
        kl = tl.get("key_levels") or {}
        vol = tl.get("volatility") or {}
        if pat:
            out += [f"**Pattern**：{fmt(pat.get('pattern'))}；market_strength "
                    f"{fmt(tl.get('market_strength'))}", ""]
            if pat.get("confirmation_criteria"):
                out += [f"> 確認條件：{pat['confirmation_criteria']}", ""]
        if kl:
            out += [f"**Key Levels**：support {_money(kl.get('support'))}／resistance "
                    f"{_money(kl.get('resistance'))}／pivot {_money(kl.get('pivot'))}", ""]
        if vol:
            out += [f"ATR-14 {fmt(vol.get('atr_14'))}；hist_vol_20d_daily "
                    f"{fmt(vol.get('hist_vol_20d_daily'))}；momentum_20d "
                    f"{fmt(vol.get('momentum_20d_pct'))}", ""]
        sm = tl.get("smart_money_analysis")
        if isinstance(sm, dict) and sm:
            out += [f"**Smart Money**：{fmt(sm.get('label'))}", ""]
            # `narrative` on some sessions, `note` on others — take whichever exists.
            body = sm.get("narrative") or sm.get("note")
            if body:
                out += [f"> {body}", ""]
        elif isinstance(sm, str) and sm.strip():
            out += [f"**Smart Money**：{sm.strip()}", ""]
        if tl.get("high_prob_scenario"):
            out += [f"**High-prob Scenario**：{tl['high_prob_scenario']}", ""]
    elif lane == "valuation":
        vl = trade.get("valuation_lane") or {}
        out += [f"Lane 自算 weighted_fair_value {_money(vl.get('weighted_fair_value'))}"
                f"（vs 現價 {_pct(vl.get('vs_current_pct'))}）", ""]
        out += _outlier_note(trade)
    return out


def _outlier_note(trade):
    """Surface anchors the engine itself flagged as outliers.

    V4.116.0. `outlier_diagnostics` has always been in history.json and has never
    been rendered, so a fair value could be dominated by an anchor the engine had
    already marked as out of range without the report saying so anywhere.

    2026-08-09 NOW is the case that forced this: `owner_earnings_mult` at 9.45,
    flagged `outside [33.37, 300.35]`, carried an effective weight of 0.275 after
    two mandatory anchors were skipped — and produced the `extreme_overvalued`
    verdict the whole bear thesis rested on. The diagnostic was sitting in the
    decision record the entire time.

    Advisory, like the diagnostic itself: this changes no number. It exists so a
    reader can see which anchors the engine distrusts before believing the fair
    value built from them.
    """
    fvs = trade.get("fair_value_summary") or {}
    diags = fvs.get("outlier_diagnostics")
    if not isinstance(diags, list) or not diags:
        return []
    weights = fvs.get("weights_used") or {}
    rows = []
    for d in diags:
        if not isinstance(d, dict):
            continue
        anchor = d.get("anchor")
        w = weights.get(anchor)
        rows.append(
            f"- `{fmt(anchor)}` = {fmt(d.get('value'))}"
            + (f"（有效權重 {fmt(w)}）" if w is not None else "")
            + f" —— {fmt(d.get('reason'))}")
    if not rows:
        return []
    return ["**⚠ Outlier anchors（engine 自標，未從加權中剔除）**", ""] + rows + [""]


def _sec_contrarian(trade, bundle):
    b = bundle.get("burry") or {}
    out = [f"### Contrarian（Burry Score {fmt(trade.get('burry_score'))} / 100, "
           f"{fmt(b.get('label'))}, veto_flag {_v(b.get('veto_flag'))}）", ""]
    comps = b.get("components") or {}
    if comps:
        out += ["**Components**", _bullets(f"{k} {fmt(v)}" for k, v in comps.items()), ""]
    note = b.get("narrative") or trade.get("contrarian_note")
    if note:
        out += [f"**Narrative（僅註記，不調分）**：{note}", ""]
    out += ["---", ""]
    return out


def sec_mhp(trade):
    mhp = trade.get("multi_horizon_price_framework") or {}
    st = mhp.get("short_term_5d") or {}
    mid = mhp.get("mid_term_60d") or {}
    conv = mhp.get("convergence") or {}
    band = st.get("band_capped") or st.get("band") or []
    out = ["## Multi-Horizon Price Framework", "", "### 長期：合理股價", "",
           _facts_block("fair_value_anchors", trade), "", "### 5 日機率帶", ""]
    if len(band) == 3:
        out += [f"- Band（Capped）：[下界 {_money(band[0])} / 點估計 {_money(band[1])} / "
                f"上界 {_money(band[2])}]"]
    else:
        out += ["- Band（Capped）：N/A"]
    out += [f"- Drift (drift_sigma)：{fmt(st.get('drift_sigma'))}",
            f"- Sigma Daily：{fmt(st.get('sigma_daily'))}",
            f"- ATR-14：{fmt(st.get('atr_14'))}",
            f"- Confidence：{fmt(st.get('confidence'))}",
            f"- Catalyst Widened：{_v(st.get('catalyst_widened'))}"]
    if st.get("key_level_note"):
        out += [f"- 關鍵水位反射註記：{st['key_level_note']}"]
    w = mid.get("weights_used") or {}
    out += ["", "### 60 日 target", "",
            f"- Momentum Target：{_money(mid.get('momentum_target'))}",
            f"- PT 60D：{_money(mid.get('pt_60d'))}",
            f"- Earnings Revision：{_money(mid.get('earnings_revision'))}",
            f"- 權重：momentum {fmt(w.get('momentum'))} / pt_60d {fmt(w.get('pt_60d'))} / "
            f"earnings_revision {fmt(w.get('earnings_revision'))}",
            f"- Mid Target：{_money(mid.get('mid_target'))}",
            f"- Reality Check：{fmt(mid.get('reality_check_note'))}",
            "", "### 三框收斂訊號", "",
            f"mhp_signal：{fmt(conv.get('mhp_signal'))} — {fmt(conv.get('signal_note'))}"]
    shadow = trade.get("valuation_archetype_shadow") or {}
    if shadow:
        out += ["", "### Archetype Shadow（advisory，不進決策）", "",
                f"Archetype：{fmt(shadow.get('archetype'))}；weighted_fair_value_shadow "
                f"{_money(shadow.get('weighted_fair_value_shadow'))}"
                f"（vs 現價 {_pct(shadow.get('vs_current_pct_shadow'))}，verdict_band_shadow："
                f"{fmt(shadow.get('verdict_band_shadow'))}）；flip_vs_live："
                f"{_v(shadow.get('flip_vs_live'))}。"]
    return "\n".join(out)


def sec_entry_plan(trade):
    """Base Case is a table, not prose — every number in it is decision-locked."""
    rows = [
        ("Entry（積極）", _price_range(trade.get("entry_aggressive"))),
        ("Entry（保守）", _price_range(trade.get("entry_conservative"))),
        ("Take Profit", _money(trade.get("take_profit"))),
        ("Stop Loss", _money(trade.get("stop_loss"))),
        ("Risk / Reward", fmt(trade.get("risk_reward_ratio"))),
        ("Staged Split", fmt(trade.get("staged_split"))),
        ("Position Size", fmt_position_size(trade.get("position_size_pct"))),
        ("Position Size Method", fmt(trade.get("position_size_method"))),
        ("Time Horizon", fmt(trade.get("time_horizon"))),
    ]
    out = ["## 進場計畫", "", "### Base Case", "", "| 欄位 | 值 |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in rows]
    if _f(trade.get("position_size_pct")) == 0.0:
        note = "> position_size_pct = 0 —— 本次不建倉。"
        if trade.get("entry_aggressive") or trade.get("entry_conservative"):
            note += "上表 entry 區間僅為再評估參考，非進場掛單。"
        out += ["", note]
    return "\n".join(out)


def sec_footer(entry, trade, polish_stamp):
    mhp = trade.get("multi_horizon_price_framework") or {}
    return (f"*分析基準日：{fmt(entry.get('export_date') or entry.get('date'))}"
            f"｜分析價格：{_money(trade.get('analysis_price'))}"
            f"｜price engine：{fmt(mhp.get('engine'))}"
            f"｜renderer：{RENDERER_LABEL}"
            f"｜polish：{polish_stamp}*")


def engine_stamp():
    """One line naming the LLM that drove this run, for the report header.

    `dashboard_server` exports AIC_PROTOCOL_MODEL/_TIER/_JOB_ID into every
    protocol subprocess, so the report can state its own provenance instead of
    the reader having to open the scan log to find out. Which engine ran a
    report stopped being a detail on 2026-08-09, when the broker started
    assigning providers and an `invest` run silently went somewhere that could
    not execute it.

    An absent env var means the renderer was invoked by hand. That is said
    outright rather than left blank — a missing stamp would otherwise read as
    "produced by whatever ran last".
    """
    model = (os.environ.get("AIC_PROTOCOL_MODEL") or "").strip()
    if not model:
        return "_執行引擎：manual（直接跑 renderer，未經 protocol 派工）_"
    tier = (os.environ.get("AIC_PROTOCOL_MODEL_TIER") or "cli-default").strip()
    job = (os.environ.get("AIC_PROTOCOL_JOB_ID") or "").strip()
    return f"_執行引擎：**{model}** ({tier})" + (f" · job `{job}`_" if job else "_")


def render(entry, trade, bundle, narrative, polish_stamp="none"):
    ticker = entry.get("ticker") or trade.get("ticker") or "N/A"
    date = entry.get("export_date") or entry.get("date") or "N/A"
    parts = [
        f"# {date} {ticker} — 投資委員會分析",
        "",
        engine_stamp(),
        "",
        "## 決議摘要",
        "",
        _narrative_block("decision_summary_line", narrative["decision_summary_line"]),
        "",
        _facts_block("decision_summary", trade),
        "",
        "---",
        "",
        sec_macro(entry, trade, bundle),
        "",
        "---",
        "",
        "## Final Visualization Table",
        "",
        _facts_block("lane_scores", trade),
        "",
        "---",
        "",
        sec_lane_detail(trade, bundle),
        sec_mhp(trade),
        "",
        "---",
        "",
        "## Red Team Counter Thesis",
        "",
        "### Consensus View（市場共識）",
        "",
        _narrative_block("consensus_view", narrative["consensus_view"]),
        "",
        "### Differentiated View（本委員會差異化判斷）",
        "",
        _narrative_block("differentiated_view", narrative["differentiated_view"]),
        "",
        "### Counter Thesis",
        "",
        str(trade.get("red_team_counter_thesis") or "N/A").strip(),
        "",
        f"red_team_verdict {fmt(trade.get('red_team_verdict'))}"
        f"｜counter_evidence_strength {fmt(trade.get('red_team_counter_evidence_strength'))}/5"
        f"｜thesis_break_probability {fmt(trade.get('red_team_thesis_break_probability'))}",
        "",
        "### Kill Conditions",
        "",
        _facts_block("kill_conditions", trade),
        "",
        "---",
        "",
        sec_entry_plan(trade),
        "",
        "### Bull Case",
        "",
        _narrative_block("bull_case", narrative["bull_case"]),
        "",
        "### Bear Case",
        "",
        _narrative_block("bear_case", narrative["bear_case"]),
        "",
        "---",
        "",
        "## 關鍵風險",
        "",
        _facts_block("key_risks", trade),
        "",
        "---",
        "",
        "## Watch / 再評觸發條件",
        "",
        _facts_block("watch_conditions", trade),
        "",
        "---",
        "",
        sec_footer(entry, trade, polish_stamp),
    ]
    return "\n".join(parts).rstrip() + "\n"


# ---------------------------------------------------------------------------
# --polish: one governed LLM call, three fail-open guards
# ---------------------------------------------------------------------------

_NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
# Bare small integers are ordinals / counts / list sizes in Chinese prose ("1-2 句",
# "第 4 個", "5 個交易日"). Requiring those to appear in the fact set would reject
# almost every well-formed sentence, so they are exempt and the exemption is stated
# rather than silent.
#
# The exemption does NOT extend to a number carrying a unit — "上漲 9%" is a claim about
# the security, not an ordinal, and it is exactly the size of number a model invents
# without noticing. Anything immediately followed by a percent or currency mark is
# checked against the fact set however small it is.
FREE_INT_MAX = 12
_UNIT_SUFFIX = ("%", "％", "倍", "x", "X", "×")


def _norm_num(tok):
    t = tok.replace(",", "").lstrip("+-")
    if not t or t == ".":
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return f"{v:.6f}".rstrip("0").rstrip(".")


def _fact_forms(v):
    """Every rendering of one numeric fact a sentence might legitimately use: the raw
    value and its percent form (0.5874 → 58.74), each rounded 0-4 dp.

    The inverse (v / 100) is deliberately NOT generated. Prose renders a stored fraction
    as a percentage constantly; it never renders a stored percentage as a fraction. All
    that branch did was widen the accepted set — e.g. 678 → 6.78 → "7" — which is pure
    loss: every extra form is one more invented number the guard cannot see.
    """
    forms = set()
    for scaled in (v, v * 100.0):
        for dp in range(0, 5):
            try:
                r = round(scaled, dp)
            except (TypeError, ValueError, OverflowError):
                continue
            n = _norm_num(f"{r:.6f}")
            if n is not None:
                forms.add(n)
    return forms


def collect_facts(entry, trade, bundle, base_md):
    """Every number the polished prose is allowed to contain.

    Returns `(numbers, dates)`. Dates are kept whole: `2026-11-19` tokenises into
    `2026` / `-11` / `-19`, and demanding each fragment appear separately would reject
    almost every real earnings date. The date itself must appear in the source material;
    once matched it is removed before the numeric scan.
    """
    blob = (json.dumps(entry, ensure_ascii=False) + json.dumps(bundle, ensure_ascii=False)
            + base_md)
    dates = set(_DATE_RE.findall(blob))
    facts = set()
    for tok in _NUM_RE.findall(blob):
        n = _norm_num(tok)
        if n is None:
            continue
        facts.add(n)
        try:
            facts |= _fact_forms(float(n))
        except (ValueError, OverflowError):
            continue
    return facts, dates


def unbacked_numbers(text, facts, dates=frozenset()):
    """Numeric tokens in `text` with no backing fact. `facts` may be the `(numbers,
    dates)` pair `collect_facts` returns, or just the number set.

    **Known limit, stated rather than implied.** This catches numbers that are absent
    from the source material. It cannot catch a *wrong* number that happens to coincide
    with a real one, and for small magnitudes that is common: a typical entry's fact set
    covers nearly every integer from 1 to 30 (they occur as raw values, and as 0-dp
    roundings of larger facts). So "上漲 9%" passes when 9 appears anywhere in the data.
    The guard's real value is at the magnitudes models actually hallucinate — prices,
    growth rates, multiples with decimals — where the space is sparse. Do not read a
    clean polish run as proof that every number is right; read it as proof that no number
    came from nowhere.
    """
    if isinstance(facts, tuple):
        facts, dates = facts
    bad = []
    for d in _DATE_RE.findall(text):
        if d not in dates:
            bad.append(d)
    scan = _DATE_RE.sub(" ", text)
    for m in _NUM_RE.finditer(scan):
        tok = m.group(0)
        n = _norm_num(tok)
        if n is None:
            continue
        try:
            v = abs(float(n))
        except ValueError:
            continue
        # Chinese prose writes both "1.72x" and "7 倍" — allow one optional space so the
        # unit rule is not defeated by typography.
        tail = scan[m.end():m.end() + 2].lstrip()[:1]
        unit_bearing = (tail in _UNIT_SUFFIX
                        or scan[max(0, m.start() - 1):m.start()] in ("$", "＄"))
        if v <= FREE_INT_MAX and float(n).is_integer() and not unit_bearing:
            continue
        if n not in facts:
            bad.append(tok)
    return bad


def strip_narrative(md):
    """Blank out every NARRATIVE region so two renders can be compared on the bytes the
    LLM is not allowed to touch."""
    return NARRATIVE_RE.sub(lambda m: f"<!--NARRATIVE:{m.group(1)}-->", md)


POLISH_SYSTEM = (
    "你是投資委員會報告的文字編輯，不是分析師。你只改寫指定的敘事段落，"
    "不評分、不推論、不引入任何未提供的事實。"
    "所有數字必須逐字取自提供的 FACTS，禁止推算、換算、四捨五入成新數字，"
    "更禁止憑印象補一個看起來合理的數字。"
    "輸出必須是單一 JSON object，不得包含 markdown 標題、表格、程式碼區塊或 HTML 註解。"
)


def _polish_prompt(entry, trade, bundle, narrative):
    ticker = entry.get("ticker") or trade.get("ticker")
    facts = {
        "ticker": ticker,
        "date": entry.get("export_date"),
        "final_decision": trade.get("final_decision"),
        "final_action": trade.get("final_action"),
        "final_score": trade.get("final_score"),
        "decision_confidence_pct": trade.get("decision_confidence_pct"),
        "position_size_pct": trade.get("position_size_pct"),
        "analysis_price": trade.get("analysis_price"),
        "lane_scores": trade.get("lane_scores"),
        "valuation_lane": trade.get("valuation_lane"),
        "red_team_verdict": trade.get("red_team_verdict"),
        "red_team_counter_thesis": trade.get("red_team_counter_thesis"),
        "decision_margin": trade.get("decision_margin"),
        "macro_context": trade.get("macro_context"),
        "fair_value_summary": trade.get("fair_value_summary"),
        "multi_horizon_price_framework": trade.get("multi_horizon_price_framework"),
        "key_risks": trade.get("key_risks"),
        "watch_conditions": trade.get("watch_conditions"),
        "lanes": bundle.get("lanes"),
        "burry": bundle.get("burry"),
    }
    spec = "\n".join(f"  - `{k}`：{NARRATIVE_LABEL[k]}（目前制式版：{narrative[k]}）"
                     for k in NARRATIVE_KEYS)
    return (
        f"FACTS（唯一可用的事實與數字來源）:\n"
        f"```json\n{json.dumps(facts, ensure_ascii=False, indent=1)}\n```\n\n"
        f"請改寫以下 5 個敘事欄位，各 1-3 句繁體中文，讀者是投資委員會成員：\n{spec}\n\n"
        f"硬性限制：\n"
        f"  - 只輸出 JSON object，key 恰為這 5 個，value 為純文字字串。\n"
        f"  - 每個出現的數字都必須在 FACTS 裡找得到原值；沒有把握就不要寫數字。\n"
        f"  - 不得出現 markdown 標題（#）、表格（|）、HTML 註解（<!--）。\n"
        f"  - 不得改變 final_decision / final_action 的語意，也不得新增投資建議。\n")


def apply_polish(base_md, entry, trade, bundle, narrative, model=None):
    """Returns (md, stamp, warnings). Every failure path returns the untouched
    deterministic `base_md` — the report always ships."""
    warns = []
    try:
        sys.path.insert(0, ROOT)
        from scripts._shared import model_router
    except Exception as e:  # noqa: BLE001
        return base_md, "none", [f"model_router 不可用（{e}）→ 保留制式句"]

    prompt = _polish_prompt(entry, trade, bundle, narrative)
    try:
        if model:
            res = model_router.run_with_fallback(model, "report_polish", POLISH_SYSTEM, prompt)
        else:
            res = model_router.run_role("report_polish", POLISH_SYSTEM, prompt)
    except Exception as e:  # noqa: BLE001
        return base_md, "none", [f"polish 呼叫失敗（{e}）→ 保留制式句"]

    used = getattr(res, "model_used", None) or getattr(res, "agent", None) or "unknown"
    parsed = getattr(res, "parsed", None)
    if not isinstance(parsed, dict):
        return base_md, "none", [
            f"polish 未取得 JSON（model={used}, parse_status="
            f"{getattr(res, 'parse_status', '?')}, error={getattr(res, 'error', None)}）→ 保留制式句"]

    facts = collect_facts(entry, trade, bundle, base_md)
    accepted = {}
    for key in NARRATIVE_KEYS:
        val = parsed.get(key)
        if not isinstance(val, str) or not val.strip():
            warns.append(f"[{key}] 缺值或非字串 → 保留制式句")
            continue
        val = val.strip()
        # guard 1 (pre-substitution half): a segment must not carry structure.
        if re.search(r"<!--|-->|^\s*#{1,6}\s|\|", val, re.MULTILINE):
            warns.append(f"[{key}] 含結構標記（#／|／HTML 註解）→ 丟棄該段")
            continue
        # guard 2: numeric containment.
        bad = unbacked_numbers(val, facts)
        if bad:
            warns.append(f"[{key}] 出現事實集合外的數字 {bad} → 丟棄該段（防編造）")
            continue
        accepted[key] = val

    if not accepted:
        return base_md, "none", warns + [f"polish 全數未通過守衛（model={used}）→ 保留制式句"]

    merged = dict(narrative)
    merged.update(accepted)
    stamp = f"{used} @ [{', '.join(sorted(accepted))}]"
    out = render(entry, trade, bundle, merged, polish_stamp=stamp)

    # guard 1 (post-substitution half): outside the NARRATIVE regions the two renders
    # must be byte-identical. Anything else means a segment broke out of its block.
    base_skeleton = strip_narrative(base_md)
    out_skeleton = strip_narrative(out)
    if base_skeleton.replace("｜polish：none", f"｜polish：{stamp}") != out_skeleton:
        return base_md, "none", warns + [
            "polish 後非敘事區出現位元差異 → 整包丟棄，回退制式句"]
    return out, stamp, warns


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Render the Phase 5 committee MD report deterministically")
    ap.add_argument("--history", default=HISTORY_JSON)
    ap.add_argument("--phase-inputs", help="bundle 路徑（預設 invest_logs/phase_inputs/<DATE>_<TICKER>.json）")
    ap.add_argument("--out", help="輸出路徑（預設 reports/<YYYYMMDD>_<TICKER>.md）")
    ap.add_argument("--polish", action="store_true",
                    help="用一次 governed LLM call 改寫 5 個敘事段（預設關；失敗一律降級不擋）")
    ap.add_argument("--polish-model", choices=("claude", "codex", "gemini"),
                    help="認證用固定 polish model；平常由 broker 自動選擇")
    ap.add_argument("--stdout", action="store_true", help="印到 stdout 而不寫檔")
    args = ap.parse_args(argv)

    if not os.path.exists(args.history):
        print(f"[render] ✗ history 不存在: {args.history}", file=sys.stderr)
        return 1
    entry, trade = load_history(args.history)
    bundle_path = args.phase_inputs or default_bundle_path(entry, trade)
    bundle = load_bundle(bundle_path)

    if bundle.get("bundle_version") and bundle["bundle_version"] != BUNDLE_VERSION:
        print(f"[render] ! bundle_version {bundle['bundle_version']} ≠ {BUNDLE_VERSION}"
              f"（仍嘗試渲染）", file=sys.stderr)

    errors = check_consistency(entry, trade, bundle)
    if errors:
        print("[render] ✗ bundle 與 history 決策記錄不一致，拒絕渲染：", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print("\n修法：以本次 session export 為準修正 bundle（決策記錄是權威），"
              "或確認 bundle 抄的是本次 session 的 Phase 2 輸出而非上一次的暫存。",
              file=sys.stderr)
        return 1

    narrative = formulaic_narrative(entry, trade, bundle)
    md = render(entry, trade, bundle, narrative)
    stamp = "none"
    if args.polish:
        md, stamp, warns = apply_polish(md, entry, trade, bundle, narrative,
                                        model=args.polish_model)
        for w in warns:
            print(f"[render] ! polish: {w}", file=sys.stderr)

    if args.stdout:
        sys.stdout.write(md)
        return 0

    date = entry.get("export_date") or entry.get("date") or ""
    ticker = entry.get("ticker") or trade.get("ticker") or ""
    out_path = args.out or os.path.join(REPORTS_DIR, f"{date.replace('-', '')}_{ticker}.md")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write(md)
    rel = os.path.relpath(os.path.abspath(out_path), ROOT)
    print(f"[render] ✓ {rel} — {len(md.splitlines())} 行；polish: {stamp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

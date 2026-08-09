#!/usr/bin/env python3
"""test_render_investment_report.py — Phase 5 renderer contract (V4.87.0).

What must hold:

  A. Golden render — a real history entry + its phase_inputs bundle produce a byte-stable
     report. Re-rendering twice is identical (no clocks, no dict-ordering drift), and the
     six decision-critical FACTS blocks are byte-identical to what `inject_report_facts.py`
     produces, because both must keep exactly one implementation.
  B. Every decision-locked number reaches the page — the 11 decision_lock fields plus the
     Phase 4 plan numbers are asserted individually, not by eyeballing the whole file.
  C. Consistency gate — each overlapping field, drifted one at a time, must abort with
     rc=1. A gate that only catches the obvious case is worse than none, because it reads
     as coverage.
  D. Step 1.5 override is NOT a mismatch — the valuation lane's step string legitimately
     carries a rewritten score (`score 0.0 → -1.5`); flagging that would fail every
     CONFIRMED entry.
  E. `--polish` guards, all fail-OPEN — a segment that carries structure, invents a
     number, comes back malformed, or when the router is unavailable, must degrade to the
     deterministic sentence and still exit 0. The report always ships.
  F. Rendered output passes `validate_markdown_export.py` rc=0.

**Coverage boundary — read this before treating a green run as "verified on real data".**
Measured over the full 172-trade corpus at V4.87.0: renders 172/172 without raising, and
all 172 rendered outputs pass `validate_markdown_export.py`. Shape tolerance is therefore
genuinely exercised. What is NOT:

  - `calculation_steps` exists on **2 of 172** trades, and NO entry in the corpus is
    stamped V5.1. So the strongest half of the consistency gate — comparing the bundle
    against the score and quantised confidence the decision math actually consumed — has
    exactly one real specimen (MU 2026-08-02). Fixture C's step-string cases and every
    `_cs(...)` payload here are synthetic.
  - 94 of 172 trades (V4.6 / V4.8, the 4-lane era) carry no `multi_horizon_price_framework`
    and no `fair_value_summary`; those render a structurally correct but N/A-heavy §6.
    The renderer runs on new sessions, so this is not a defect — but do not backfill old
    reports with it and expect substance.

Both gaps close on their own as V5.1 deep dives accumulate. Until then, a green run means
the logic holds against the fixtures, not that production data has exercised every branch.

Run: python3 investment/scripts/test_render_investment_report.py   # rc=0 全過 / rc=1 fail
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

import render_investment_report as R  # noqa: E402
from inject_report_facts import RENDERERS as FACT_RENDERERS  # noqa: E402

HISTORY = os.path.join(ROOT, "investment/invest_logs/history.json")
FAILS: list[str] = []


def eq(label, got, want):
    if got != want:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


def ok(label, cond):
    if not cond:
        FAILS.append(f"{label}: expected True")


def contains(label, hay, needle):
    if needle not in hay:
        FAILS.append(f"{label}: report is missing {needle!r}")


def _pick(hist, ticker, date):
    for e in hist:
        if e.get("ticker") == ticker and e.get("export_date") == date:
            return copy.deepcopy(e)
    return None


with open(HISTORY, encoding="utf-8") as fp:
    HIST = json.load(fp)

MSFT = _pick(HIST, "MSFT", "2026-08-02")     # V5.0 — no calculation_steps
MU = _pick(HIST, "MU", "2026-08-02")         # V5.1 — calculation_steps + Step 1.5 override
if MSFT is None or MU is None:
    print("✗ fixture entries missing from history.json (MSFT/MU 2026-08-02)", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Fixture bundles. These reconstruct what the PM hands the renderer — the same
# per-lane evidence that used to be pasted into the Sonnet formatter's prompt.
# ---------------------------------------------------------------------------

MSFT_BUNDLE = {
    "bundle_version": R.BUNDLE_VERSION,
    "ticker": "MSFT",
    "date": "2026-08-02",
    "phase0": {
        "regime_confidence": 0.6, "market_top_zone": "Orange", "market_top_score": 46.9,
        "ftd_state": "RALLY_ATTEMPT_day2", "breadth_composite": 71, "vix": 15.99,
        "fear_greed": 42.5, "fred_verdict": "Soft Landing", "real_rate_pct": 2.41,
        "dgs10_pct": 4.68,
        "hot_sectors": ["Industrials", "Financials", "Energy", "Consumer_Discretionary"],
        "cold_sectors": ["Technology", "Real_Estate", "Utilities", "Consumer_Staples"],
    },
    "lanes": {
        "fundamentals": {
            "signal": "BUY", "score": 1.5, "confidence": 0.72,
            "phase0_alignment": "MISALIGNED",
            "key_factors": ["PE 25.8 vs peer median 35.3", "Rev +17.8% YoY, EPS +31.3%",
                            "ROE 33.2%, Altman Z 8.39 safe"],
            "risk_flags": ["Gross margin z=-2.56 compression + capex intensity 39.8%",
                           "FCF yield 1.94% below real rate 2.41%"]},
        "sentiment": {
            "signal": "HOLD", "score": 0.21, "confidence": 0.55,
            "phase0_alignment": "NEUTRAL",
            "key_factors": ["Insider MSPR -100, ratio 0 latest quarter",
                            "Short float only 1.24%"],
            "risk_flags": ["Institutional 資料為空", "Q3 insider 樣本薄：僅 1 筆賣出交易"]},
        "news": {
            "signal": "BUY", "score": 3.5, "confidence": 0.72,
            "phase0_alignment": "MISALIGNED",
            "key_factors": ["Q4 FY26 財報 Azure +43% 突破 $100B 年化 run-rate",
                            "PT 修正動能 FLAT（+0.52%），30 日零升降評"],
            "risk_flags": ["兩件證券集體訴訟律師事務所招攬"],
            "analyst_consensus": "Buy（66 buy / 16 hold / 0 sell）"},
        "technical": {
            "signal": "HOLD", "score": 1.0, "confidence": 0.55,
            "phase0_alignment": "MISALIGNED",
            "key_factors": ["Price above all MAs, testing $466 resistance",
                            "RSI 74.5 overbought; stage still Stage 1 basing"],
            "risk_flags": ["RSI 74.5 超買鄰近壓力，回檔風險"]},
        "valuation": {
            "signal": "HOLD", "score": -1.0, "confidence": 0.6,
            "phase0_alignment": "ALIGNED",
            "key_factors": ["Weighted FV $415.52 = 11.8% premium"],
            "risk_flags": ["PT dispersion 51.7% 使 consensus 錨低精度"]},
    },
    "burry": {
        "score": 36.8, "label": "NEUTRAL", "veto_flag": False,
        "components": {"fcf_yield_pct": 0.47, "ev_ebit": 18.03, "debt_to_equity": 0.29},
        "narrative": "Altman safe → 不觸發；Piotroski 6 moderate → 不調。"},
    "phase3": {"final_score": 0.729, "final_decision": "HOLD", "final_action": "CANCEL",
               "avg_confidence": 0.534},
    "phase4": {"position_size_pct": 0.0, "analysis_price": 464.72},
    "red_team": {"verdict": "STRONG_COUNTER"},
}

# MU carries `calculation_steps`, so the step-string half of the gate is live here.
# Its raw confidences all quantise to c_eff 0.60 (the 0.45–0.675 band), matching the
# stored step strings; `valuation.score` is the lane's own 0.0, while the step string
# records the Step 1.5 rewrite to -1.5 — fixture D asserts that is not a mismatch.
MU_BUNDLE = {
    "bundle_version": R.BUNDLE_VERSION,
    "ticker": "MU", "date": "2026-08-02",
    "phase0": {"market_top_zone": "Orange"},
    "lanes": {
        "fundamentals": {"signal": "BUY", "score": 1.5, "confidence": 0.6,
                         "key_factors": ["HBM 供給緊俏"], "risk_flags": ["週期性反轉風險"]},
        "sentiment": {"signal": "HOLD", "score": -0.04, "confidence": 0.5,
                      "key_factors": ["insider 中性"], "risk_flags": ["短期情緒過熱"]},
        "news": {"signal": "HOLD", "score": -0.5, "confidence": 0.55,
                 "key_factors": ["PT 修正放緩"], "risk_flags": ["競爭者擴產"]},
        "technical": {"signal": "SELL", "score": -2.5, "confidence": 0.6,
                      "key_factors": ["跌破 MA20"], "risk_flags": ["動能轉弱"]},
        "valuation": {"signal": "HOLD", "score": 0.0, "confidence": 0.65,
                      "key_factors": ["FV 接近現價"], "risk_flags": ["錨分散度高"]},
    },
    "burry": {"score": 47.1, "label": "NEUTRAL", "veto_flag": False},
    "phase3": {"final_score": -0.2963, "final_decision": "HOLD", "final_action": "CANCEL"},
    "phase4": {"position_size_pct": 0.0, "analysis_price": 823.03},
    "red_team": {"verdict": "STRONG_COUNTER"},
}


def render_str(entry, bundle):
    trade = entry["trades_this_session"][0]
    errs = R.check_consistency(entry, trade, bundle)
    if errs:
        raise AssertionError(f"unexpected gate errors: {errs}")
    narrative = R.formulaic_narrative(entry, trade, bundle)
    return R.render(entry, trade, bundle, narrative)


# ── Fixture A: golden render is byte-stable + FACTS blocks are the shared ones ──
MD = render_str(MSFT, MSFT_BUNDLE)
eq("A.deterministic_rerender", render_str(MSFT, MSFT_BUNDLE), MD)
eq("A.mu_deterministic", render_str(MU, MU_BUNDLE), render_str(MU, MU_BUNDLE))

_msft_trade = MSFT["trades_this_session"][0]
for name in FACT_RENDERERS:
    block = FACT_RENDERERS[name](_msft_trade)
    contains(f"A.facts_verbatim.{name}", MD, block)
    contains(f"A.facts_marker.{name}", MD, f"<!--FACTS:{name}:start-->")

for key in R.NARRATIVE_KEYS:
    contains(f"A.narrative_marker.{key}", MD, f"<!--NARRATIVE:{key}:start-->")

eq("A.title", MD.splitlines()[0], "# 2026-08-02 MSFT — 投資委員會分析")
contains("A.renderer_stamp", MD, R.RENDERER_LABEL)
contains("A.polish_none", MD, "｜polish：none")


# ── V4.116.0: position_size is a FRACTION wearing a `_pct` name ──────────────
# `trade_plan_builder` builds it from BASE_POSITION = 0.05 and
# vol_adjusted_limit_pct / 100.0, multiplying fractions all the way down, so
# 0.035325 is 3.53%. It used to go through the generic `pct=True` formatter,
# which appends a bare '%' — every published report understated its own position
# size by 100×. This is the kind of wrong that reads as perfectly normal, so it
# gets an explicit unit assertion rather than a format one.
from inject_report_facts import fmt_position_size as _fps  # noqa: E402

eq("A.size.fraction_to_percent", _fps(0.035325), "3.53%")
eq("A.size.five_percent",        _fps(0.05),     "5.00%")
eq("A.size.zero",                _fps(0.0),      "0.00%")
eq("A.size.none",                _fps(None),     "N/A")
# The bug's signature: a bare append would print "0.035325%".
if "0.035325%" in _fps(0.035325):
    raise AssertionError("A.size.not_raw_append: the raw fraction reached the page")
# Other pct=True fields really are percents and must NOT be scaled.
eq("A.size.confidence_untouched", R._pct(67), "67%")
eq("A.size.vs_current_untouched", R._pct(-34.5), "-34.5%")


# ── V4.116.0: anchors the engine flagged as outliers are disclosed ───────────
# `outlier_diagnostics` has always been in history.json and was never rendered,
# so a fair value could be dominated by an anchor the engine itself distrusted
# with the report saying nothing. Advisory only — it must not change a number.
_outlier_trade = {
    "fair_value_summary": {
        "weights_used": {"owner_earnings_mult": 0.275},
        "outlier_diagnostics": [
            {"anchor": "owner_earnings_mult", "value": 9.45,
             "reason": "outside [33.37, 300.35]"},
        ],
    },
}
_note = "\n".join(R._outlier_note(_outlier_trade))
contains("A.outlier.anchor",  _note, "owner_earnings_mult")
contains("A.outlier.value",   _note, "9.45")
contains("A.outlier.weight",  _note, "0.275")
contains("A.outlier.reason",  _note, "outside [33.37, 300.35]")
eq("A.outlier.absent_is_silent", R._outlier_note({"fair_value_summary": {}}), [])
eq("A.outlier.no_block_at_all", R._outlier_note({}), [])
eq("A.outlier.malformed_is_silent",
   R._outlier_note({"fair_value_summary": {"outlier_diagnostics": ["junk"]}}), [])


# ── Fixture B: decision-locked numbers actually reach the page ───────────────
for label, needle in [
    ("final_decision", "HOLD（action: CANCEL）"),
    ("final_score", "0.729 / 3.0"),
    ("confidence", "53%"),
    ("analysis_price", "$464.72"),
    ("weighted_fair_value", "$434.65"),
    ("burry", "36.8 / 100"),
    ("red_team", "STRONG_COUNTER"),
    ("scenario_odds", "bull 28 / base 47 / bear 25"),
    ("mid_target", "$494.80"),
    ("band_lower", "$427.10"),
    ("support", "$409.58"),
    ("entry_range_formatted", "$410.00 – $427.00"),
    ("kill_condition_1", "1. IF FY27 Q1 財報"),
]:
    contains(f"B.{label}", MD, needle)

# Booleans read as JSON, not as Python.
contains("B.bool_lowercase", MD, "Catalyst Widened：false")
ok("B.no_python_bool", "：True" not in MD and "：False" not in MD)
# position_size 0 gets the explicit no-entry note rather than a silently empty table.
contains("B.zero_position_note", MD, "position_size_pct = 0 —— 本次不建倉")
# The "entry 區間僅為再評估參考" half only appears when there IS an entry range: MSFT
# has one, MU has neither track, and telling the reader to consult an absent table is
# exactly the kind of stale boilerplate a renderer makes easy to ship.
_MU_MD = render_str(MU, MU_BUNDLE)
contains("B.mu_zero_position_note", _MU_MD, "position_size_pct = 0 —— 本次不建倉。")
ok("B.mu_no_phantom_entry_note", "上表 entry 區間僅為再評估參考" not in _MU_MD)
ok("B.msft_has_entry_note", "上表 entry 區間僅為再評估參考" in MD)
ok("B.no_na_percent", "N/A%" not in MD and "N/A%" not in _MU_MD)
# Every lane the bundle supplied gets its evidence rendered.
for lane in R.LANE_ORDER:
    contains(f"B.lane_section.{lane}", MD, f"### {R.LANE_LABEL[lane]}（")
contains("B.sentiment_present", MD, "Insider MSPR -100, ratio 0 latest quarter")


# ── Fixture C: consistency gate — one drifted field at a time ────────────────
def gate(mutate, entry=MSFT, bundle=MSFT_BUNDLE):
    e, b = copy.deepcopy(entry), copy.deepcopy(bundle)
    mutate(e, b)
    return R.check_consistency(e, e["trades_this_session"][0], b)


eq("C.clean_msft", R.check_consistency(MSFT, MSFT["trades_this_session"][0], MSFT_BUNDLE), [])
eq("C.clean_mu", R.check_consistency(MU, MU["trades_this_session"][0], MU_BUNDLE), [])

CASES = [
    ("lane_score", lambda e, b: b["lanes"]["news"].__setitem__("score", 2.5)),
    ("valuation_score", lambda e, b: b["lanes"]["valuation"].__setitem__("score", 1.0)),
    ("ticker", lambda e, b: b.__setitem__("ticker", "AAPL")),
    ("date", lambda e, b: b.__setitem__("date", "2026-08-01")),
    ("final_score", lambda e, b: b["phase3"].__setitem__("final_score", 1.9)),
    ("final_decision", lambda e, b: b["phase3"].__setitem__("final_decision", "BUY")),
    ("final_action", lambda e, b: b["phase3"].__setitem__("final_action", "EXECUTE")),
    ("position_size", lambda e, b: b["phase4"].__setitem__("position_size_pct", 3.0)),
    ("analysis_price", lambda e, b: b["phase4"].__setitem__("analysis_price", 400.0)),
    ("burry", lambda e, b: b["burry"].__setitem__("score", 90.0)),
    ("red_team", lambda e, b: b["red_team"].__setitem__("verdict", "NO_VIABLE_COUNTER")),
    ("avg_confidence", lambda e, b: b["phase3"].__setitem__("avg_confidence", 0.9)),
]
for name, mut in CASES:
    ok(f"C.detects.{name}", len(gate(mut)) >= 1)

# The step-string half only exists where calculation_steps does — MU.
ok("C.mu_step_score_drift",
   any("calculation_steps" in x for x in
       gate(lambda e, b: b["lanes"]["technical"].__setitem__("score", -1.0),
            entry=MU, bundle=MU_BUNDLE)))
# c_eff band: 0.30 quantises to 0.35, the stored steps say 0.60.
ok("C.mu_conf_band_drift",
   any("c_eff" in x for x in
       gate(lambda e, b: b["lanes"]["fundamentals"].__setitem__("confidence", 0.30),
            entry=MU, bundle=MU_BUNDLE)))
# ...but a different raw confidence inside the SAME band is not drift.
eq("C.mu_conf_same_band_ok",
   gate(lambda e, b: b["lanes"]["fundamentals"].__setitem__("confidence", 0.50),
        entry=MU, bundle=MU_BUNDLE), [])
# A bundle that omits a lane entirely is renderable (the section says so), not an error.
eq("C.missing_lane_not_an_error",
   gate(lambda e, b: b["lanes"].pop("sentiment"), entry=MU, bundle=MU_BUNDLE), [])


# ── Fixture D: Step 1.5 override is not a mismatch ───────────────────────────
_mu_steps = MU["trades_this_session"][0].get("calculation_steps") or {}
_val_step = _mu_steps.get("val")
ok("D.fixture_still_has_override", isinstance(_val_step, str) and "//" in _val_step)
parsed = R.parse_step(_val_step)
ok("D.parses", parsed is not None)
eq("D.override_flagged", parsed[3], True)
eq("D.step_score_is_rewritten", parsed[1], -1.5)
eq("D.lane_score_is_raw", (MU["trades_this_session"][0]["valuation_lane"] or {}).get("score"), 0.0)
eq("D.no_false_mismatch",
   [x for x in R.check_consistency(MU, MU["trades_this_session"][0], MU_BUNDLE)
    if "Valuation" in x], [])
# A step WITHOUT an override note still checks the score strictly.
eq("D.plain_step_not_overridden", R.parse_step("0.25 × 1.5 × 0.60 = 0.2250")[3], False)
eq("D.missing_lane_step_unparseable",
   R.parse_step("0.25 × MISSING = 0.0000  // lane score absent"), None)


# ── Fixture E: --polish guards, all fail-open ────────────────────────────────
_narr = R.formulaic_narrative(MSFT, _msft_trade, MSFT_BUNDLE)
BASE = R.render(MSFT, _msft_trade, MSFT_BUNDLE, _narr)


class _Res:
    def __init__(self, parsed, model_used="claude"):
        self.parsed = parsed
        self.model_used = model_used
        self.agent = model_used
        self.parse_status = "ok" if parsed else "failed"
        self.error = None


def with_router(parsed_or_exc):
    """Install a fake model_router so the guards can be exercised without an LLM."""
    import types
    mod = types.ModuleType("model_router")

    def _run(*a, **kw):
        if isinstance(parsed_or_exc, Exception):
            raise parsed_or_exc
        return _Res(parsed_or_exc)

    mod.run_role = _run
    mod.run_with_fallback = _run
    pkg = sys.modules.get("scripts._shared")
    prev = getattr(pkg, "model_router", None) if pkg else None
    sys.modules["scripts._shared.model_router"] = mod
    if pkg:
        pkg.model_router = mod
    return pkg, prev


GOOD = {
    "decision_summary_line": "委員會對 MSFT 給出 HOLD，final_score 0.729，不建立新部位。",
    "consensus_view": "News lane 明顯偏多，Valuation lane 是唯一負分。",
    "differentiated_view": "本委員會認為一次性重估不足以支撐進場。",
    "bull_case": "站穩阻力後再評估上檔。",
    "bear_case": "跌破帶下界即退出觀望。",
}

pkg, prev = with_router(GOOD)
md, stamp, warns = R.apply_polish(BASE, MSFT, _msft_trade, MSFT_BUNDLE, _narr)
ok("E.happy_replaces", GOOD["consensus_view"] in md)
ok("E.happy_stamp", stamp.startswith("claude @ ["))
contains("E.happy_footer", md, f"｜polish：{stamp}")
eq("E.happy_no_warnings", warns, [])
# Guard 1 (structural half): everything outside the NARRATIVE regions is untouched.
eq("E.skeleton_identical",
   R.strip_narrative(md).replace(f"｜polish：{stamp}", "｜polish：none"),
   R.strip_narrative(BASE))

# Guard 2 — an invented number is discarded, the rest survive, rc stays 0.
# 91.7 appears nowhere in the bundle, the entry, or the deterministic report. (Picking
# a number that *does* appear — "Azure +43%" is in the news lane's key_factors — would
# test nothing: the guard would correctly accept it.)
BAD_NUM = dict(GOOD, consensus_view="Azure 成長 +91.7%，動能強勁。")
with_router(BAD_NUM)
md2, stamp2, warns2 = R.apply_polish(BASE, MSFT, _msft_trade, MSFT_BUNDLE, _narr)
ok("E.invented_number_dropped", _narr["consensus_view"] in md2)
ok("E.invented_number_warned", any("編造" in w for w in warns2))
ok("E.invented_number_not_stamped", "consensus_view" not in stamp2)
ok("E.siblings_survive", GOOD["bull_case"] in md2)
# ...but a number that IS in the facts passes.
OK_NUM = dict(GOOD, consensus_view="News lane 3.5 為最大單一推力。")
with_router(OK_NUM)
md3, _s3, warns3 = R.apply_polish(BASE, MSFT, _msft_trade, MSFT_BUNDLE, _narr)
ok("E.backed_number_kept", OK_NUM["consensus_view"] in md3)
eq("E.backed_number_no_warn", warns3, [])

# Guard 1 — a segment carrying structure cannot break out of its block.
BAD_STRUCT = dict(GOOD, bull_case="## 我自己的新章節\n<!--FACTS:key_risks:start-->")
with_router(BAD_STRUCT)
md4, stamp4, warns4 = R.apply_polish(BASE, MSFT, _msft_trade, MSFT_BUNDLE, _narr)
ok("E.structure_dropped", "我自己的新章節" not in md4)
ok("E.structure_warned", any("結構標記" in w for w in warns4))
ok("E.structure_not_stamped", "bull_case" not in stamp4)

# Malformed / absent LLM output → whole deterministic report, exit 0.
with_router(None)
md5, stamp5, warns5 = R.apply_polish(BASE, MSFT, _msft_trade, MSFT_BUNDLE, _narr)
eq("E.no_json_falls_back", md5, BASE)
eq("E.no_json_stamp", stamp5, "none")
ok("E.no_json_warned", any("未取得 JSON" in w for w in warns5))

with_router(RuntimeError("router exploded"))
md6, stamp6, _w6 = R.apply_polish(BASE, MSFT, _msft_trade, MSFT_BUNDLE, _narr)
eq("E.router_raise_falls_back", md6, BASE)
eq("E.router_raise_stamp", stamp6, "none")

# Non-string / empty values are dropped individually.
with_router(dict(GOOD, bear_case=42, bull_case="   "))
md7, stamp7, warns7 = R.apply_polish(BASE, MSFT, _msft_trade, MSFT_BUNDLE, _narr)
ok("E.nonstring_dropped", _narr["bear_case"] in md7)
ok("E.blank_dropped", _narr["bull_case"] in md7)
ok("E.partial_stamp", "consensus_view" in stamp7 and "bear_case" not in stamp7)

sys.modules.pop("scripts._shared.model_router", None)
if pkg is not None and prev is not None:
    pkg.model_router = prev

# Numeric containment helper, directly.
_facts = R.collect_facts(MSFT, _msft_trade, MSFT_BUNDLE, BASE)
eq("E.facts_accepts_known", R.unbacked_numbers("final_score 0.729", _facts), [])
eq("E.facts_accepts_percent_form", R.unbacked_numbers("隱含 58.74%", _facts), [])
eq("E.facts_accepts_rounded", R.unbacked_numbers("隱含 58.7%", _facts), [])
eq("E.facts_rejects_invented", R.unbacked_numbers("成長 +43.7%", _facts), ["43.7"])
eq("E.facts_allows_small_ordinals", R.unbacked_numbers("1-2 句，第 5 個交易日", _facts), [])
# A real date must survive whole — tokenising it into 2026 / 10 / 27 and demanding each
# fragment be a separate fact would reject nearly every earnings-date sentence.
eq("E.facts_allows_real_date",
   R.unbacked_numbers("FY27 Q1 財報 2026-10-27 為驗證點", _facts), [])
eq("E.facts_rejects_invented_date",
   R.unbacked_numbers("財報改到 2027-03-14", _facts), ["2027-03-14"])
# The small-integer exemption is for ordinals, not for claims: a unit-bearing number is
# submitted to the fact set however small it is, rather than waved through.
_tiny = ({"55.5"}, frozenset())
eq("E.small_percent_not_exempt", R.unbacked_numbers("上漲 9%", _tiny), ["9"])
eq("E.small_multiple_not_exempt", R.unbacked_numbers("量能 7 倍", _tiny), ["7"])
eq("E.small_dollar_not_exempt", R.unbacked_numbers("目標 $8", _tiny), ["8"])
eq("E.bare_ordinal_still_exempt", R.unbacked_numbers("分 3 批、第 4 個", _tiny), [])
# ...and a unit-bearing number that IS a fact passes.
eq("E.backed_percent_ok", R.unbacked_numbers("vs 現價 -6.47%", _facts), [])

# The guard's documented limit, pinned so nobody later mistakes it for a bug or for a
# stronger guarantee than it gives: small integers are dense in a real fact set (they
# occur as raw values AND as 0-dp roundings of bigger facts), so a wrong-but-plausible
# small number is NOT catchable. What is catchable is a number from nowhere.
_small_present = sorted({int(float(x)) for x in _facts[0]
                         if float(x).is_integer() and 0 < float(x) <= 30})
ok("E.limit_small_ints_are_dense", len(_small_present) >= 20)
eq("E.limit_small_percent_passes_when_real", R.unbacked_numbers("上漲 9%", _facts), [])
# ...whereas a decimal at a hallucination-prone magnitude is caught.
eq("E.catches_invented_price", R.unbacked_numbers("目標價 $733.19", _facts), ["733.19"])
eq("E.catches_invented_growth", R.unbacked_numbers("成長 91.7%", _facts), ["91.7"])
# The v/100 form is not generated — 678 must not license "6.78".
ok("E.no_inverse_percent_form", "6.78" not in _facts[0])


# ── Fixture F: rendered output passes the markdown validator, end to end ─────
with tempfile.TemporaryDirectory() as tmp:
    hist_path = os.path.join(tmp, "history.json")
    bundle_path = os.path.join(tmp, "bundle.json")
    out_path = os.path.join(tmp, "report.md")
    with open(hist_path, "w", encoding="utf-8") as fp:
        json.dump([MSFT], fp, ensure_ascii=False)
    with open(bundle_path, "w", encoding="utf-8") as fp:
        json.dump(MSFT_BUNDLE, fp, ensure_ascii=False)

    rc = subprocess.run(
        [sys.executable, os.path.join(HERE, "render_investment_report.py"),
         "--history", hist_path, "--phase-inputs", bundle_path, "--out", out_path],
        capture_output=True, text=True)
    eq("F.cli_rc", rc.returncode, 0)
    ok("F.file_written", os.path.exists(out_path))
    with open(out_path, encoding="utf-8") as fp:
        eq("F.cli_matches_api", fp.read(), MD)

    v = subprocess.run(
        [sys.executable, os.path.join(HERE, "validate_markdown_export.py"),
         "--report", out_path], capture_output=True, text=True)
    eq("F.validator_rc", v.returncode, 0)

    # A drifted bundle must abort with rc=1 and name the field — never render.
    bad = copy.deepcopy(MSFT_BUNDLE)
    bad["phase3"]["final_score"] = 2.9
    bad_path = os.path.join(tmp, "bad.json")
    out2 = os.path.join(tmp, "never.md")
    with open(bad_path, "w", encoding="utf-8") as fp:
        json.dump(bad, fp, ensure_ascii=False)
    rc2 = subprocess.run(
        [sys.executable, os.path.join(HERE, "render_investment_report.py"),
         "--history", hist_path, "--phase-inputs", bad_path, "--out", out2],
        capture_output=True, text=True)
    eq("F.gate_rc", rc2.returncode, 1)
    ok("F.gate_names_field", "final_score" in rc2.stderr)
    eq("F.gate_writes_nothing", os.path.exists(out2), False)

    # A missing bundle is a clear instruction, not a traceback.
    rc3 = subprocess.run(
        [sys.executable, os.path.join(HERE, "render_investment_report.py"),
         "--history", hist_path, "--phase-inputs", os.path.join(tmp, "nope.json")],
        capture_output=True, text=True)
    eq("F.missing_bundle_rc", rc3.returncode, 1)
    ok("F.missing_bundle_msg", "phase_inputs bundle 不存在" in rc3.stderr)


if FAILS:
    print(f"✗ {len(FAILS)} failure(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ Phase 5 renderer contract holds (A golden / B decision-lock / C gate / "
      "D step-1.5 override / E polish fail-open / F validator)")

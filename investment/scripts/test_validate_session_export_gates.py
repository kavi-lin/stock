#!/usr/bin/env python3
"""Contract for the V4.116.3 + V4.117.0 export gates.

Both close the same shape of hole: a rule the protocol documents, that nothing
enforced, so compliance was whatever the executing model happened to choose.
2026-08-09 made the cost visible — two engines ran `invest` on the same day and
one obeyed both rules while the other obeyed neither, and both exports validated
clean.

  1. `valuation_reviewer_gate` — protocol §PHASE 2 has always said the gate's
     record goes into the session export. The validator only checked it when it
     was already there, which made it optional in practice. It is the sole
     source of the shadow samples that a future "should this gate bind?"
     decision would rest on, so skipping it loses evidence silently.

  2. Technical `rubric_hint` — `analyze.py` translates the stage structure into
     a score band. A lane returning more than the band is overriding the rubric;
     doing so is allowed, doing so silently is not. One engine returned +2.5 and
     then +2.0 against `0 to +1` on consecutive runs of the same ticker, while
     the other returned exactly +1.0 on the same hint. Either would have flipped
     the decision.

The V4.117.0 three close what the same day's logs showed the *first* two could
not reach — the export was still whatever the model typed:

  3. `export_provenance` — history.json is `append_session_export.py`'s to
     write. One run hand-edited `final_score` and a retyped `calculation_steps`
     into the decision record after a clean append; an earlier run popped
     entries off the list with an ad-hoc `json.dump` whenever a gate went red.
     Both validated green, because a hand-written entry and a script-written
     one are the same JSON.

  4. `news_lane.pt_revision_momentum` — protocol §PHASE 2 scores this field, and
     the validator only type-checked it when present, so null was free. An
     export carried `-2.94% 1m` in the lane's prose while the structured field
     stayed null.

  5. `calculation_steps` parity — §13 proves the block is self-consistent but
     cannot tell it belongs to a superseded run. One export carried steps from
     a run with valuation −1.5 while its own valuation lane said −3.0.

Usage: python3 investment/scripts/test_validate_session_export_gates.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate_session_export as V  # noqa: E402

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        failures.append(f"{name}: {detail}")


# ── 1. valuation_reviewer_gate is required from the cutoff onwards ───────────
# Driven through the REAL validator as a subprocess, on the schema doc's own
# FULL EXAMPLE. The first version of this file reimplemented the rule and read
# the same constant, so moving the cutoff moved the expectation with it and the
# seeded-bug run stayed green — the exact self-referential shape MAINTENANCE
# §2c calls out. A comparison tool that shares a source with the thing it
# compares cannot report a difference.
import copy                                                        # noqa: E402
import subprocess                                                  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_session_export_schema import extract_full_example        # noqa: E402

VALIDATOR = os.path.join(V.ROOT, "investment/scripts/validate_session_export.py")
BASE = extract_full_example()


def run_validator(entry, label, want_rc, want_substr=None):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as fp:
        json.dump([entry], fp, ensure_ascii=False)
        path = fp.name
    try:
        proc = subprocess.run([sys.executable, VALIDATOR, "--history", path],
                              capture_output=True, text=True)
        out = (proc.stdout + proc.stderr).strip()
        check(f"{label}.rc", proc.returncode == want_rc,
              f"rc={proc.returncode} want {want_rc} — {out[:240]}")
        if want_substr and proc.returncode == want_rc:
            check(f"{label}.message", want_substr in out, out[:240])
    finally:
        os.unlink(path)


APPENDER = os.path.join(V.ROOT, "investment/scripts/append_session_export.py")


def appended(entry):
    """Entry as it lands on disk, via the real appender rather than a restatement.

    Restating the stamp here would make this file agree with a broken writer —
    the §2c shape. Driving the actual script means a writer that stops stamping
    shows up as a red here.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as fp:
        json.dump([], fp)
        hist = fp.name
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as fp:
        json.dump(entry, fp, ensure_ascii=False)
        src = fp.name
    try:
        proc = subprocess.run(
            [sys.executable, APPENDER, "--from-file", src, "--history", hist],
            capture_output=True, text=True)
        if proc.returncode != 0:
            check("prov.appender_runs", False, (proc.stdout + proc.stderr)[:240])
            return entry
        with open(hist, encoding="utf-8") as fp:
            return json.load(fp)[-1]
    finally:
        for p in (hist, src):
            os.unlink(p)


def news_lane_ok():
    return {"reasoning_one_line": "fixture", "key_factors": ["fixture"],
            "pt_revision_momentum": {"direction": "FLAT"}}


def entry_dated(date_str, *, with_gate):
    e = copy.deepcopy(BASE)
    e["export_date"] = date_str
    trade = e["trades_this_session"][0]
    # The V4.117.0 cutoffs land on the same day as this gate's, so a fixture
    # aimed at `valuation_reviewer_gate` now has to satisfy the News lane rule
    # too or it fails for the wrong reason.
    trade["news_lane"] = news_lane_ok()
    if with_gate:
        trade["valuation_reviewer_gate"] = {
            "schema": "valuation_reviewer_gate.v1",
            "ticker": trade.get("ticker") or e.get("ticker"),
            "would_invoke": False, "triggers_fired": [], "shadow_only": True,
        }
    else:
        trade.pop("valuation_reviewer_gate", None)
    return e


# Literal dates, NOT `V.VALUATION_GATE_REQUIRED_FROM`. Deriving the fixture's
# date from the constant under test moves the input whenever the policy moves,
# so pushing the cutoff to 2099 kept every case green — the second time this one
# file reached for the thing it was supposed to be checking. The policy date is
# the assertion; changing it must require changing this line too.
CUTOFF = "2026-08-09"
check("vrg.cutoff_matches_policy", V.VALUATION_GATE_REQUIRED_FROM == CUTOFF,
      f"validator says {V.VALUATION_GATE_REQUIRED_FROM!r}, this contract says {CUTOFF!r} "
      f"— update both deliberately, or the cases below stop meaning anything")

# Stamped, because from this same date the provenance gate applies too — an
# unstamped fixture would red for that instead and prove nothing about vrg.
run_validator(appended(entry_dated(CUTOFF, with_gate=False)),
              "vrg.required_after_cutoff", 1, "valuation_reviewer_gate missing")
run_validator(appended(entry_dated(CUTOFF, with_gate=True)), "vrg.present_passes", 0)
# 172 historical entries predate the block; erroring on each is pure noise.
run_validator(entry_dated("2026-07-31", with_gate=False), "vrg.old_entries_silent", 0)


# ── 2. Technical lane may not out-score its own script silently ──────────────
def rubric_check(score, hint, *, override=None, ticker="ZZTEST",
                 age_days=0, write=True, payload_ticker=None):
    """Drive `_check_technical_rubric` against a synthetic artifact."""
    path = os.path.join(ROOT_CACHE, f"{ticker}_technical_payload.json")
    if write:
        with open(path, "w", encoding="utf-8") as fp:
            json.dump({"ticker": payload_ticker or ticker,
                       "signal_hints": {"rubric_hint": hint}}, fp)
        stamp = time.time() - age_days * 86400
        os.utime(path, (stamp, stamp))
    trade = {"ticker": ticker, "lane_scores": {"technical": score}}
    if override is not None:
        trade["technical_lane"] = {"rubric_override_reason": override}
    errors, warnings = [], []
    V._check_technical_rubric({"ticker": ticker}, trade, errors, warnings)
    if write and os.path.exists(path):
        os.remove(path)
    return errors, warnings


ROOT_CACHE = os.path.join(V.ROOT, "skills/technical-analyst/cache")
os.makedirs(ROOT_CACHE, exist_ok=True)

HINT = "0 to +1 (basing — wait for confirmation)"

_e, _w = rubric_check(2.0, HINT)
check("rubric.above_band_errors", _e != [], "score 2.0 against `0 to +1` must fail")
check("rubric.message_names_field",
      any("rubric_override_reason" in x for x in _e), str(_e))

_e, _w = rubric_check(1.0, HINT)
check("rubric.upper_bound_ok", _e == [], f"1.0 sits ON the band and must pass: {_e}")
_e, _w = rubric_check(0.0, HINT)
check("rubric.lower_bound_ok", _e == [], f"0.0 sits ON the band and must pass: {_e}")

_e, _w = rubric_check(-1.0, HINT)
check("rubric.below_band_errors", _e != [], "the band is two-sided, not a ceiling")

# Deviation is allowed — declared.
_e, _w = rubric_check(2.5, HINT, override="Stage read stale: gap-up on 4x volume")
check("rubric.declared_override_passes", _e == [], str(_e))
check("rubric.declared_override_warns", _w != [], "a declared override still deserves a note")
_e, _w = rubric_check(2.5, HINT, override="   ")
check("rubric.blank_override_rejected", _e != [], "whitespace is not a reason")

# Negative bands parse too.
_e, _w = rubric_check(-2.5, "-2 to -3")
check("rubric.negative_band_ok", _e == [], f"-2.5 is inside [-3, -2]: {_e}")

# Silent when there is no evidence to check against.
_e, _w = rubric_check(2.0, HINT, write=False, ticker="NOARTIFACT")
check("rubric.absent_artifact_silent", _e == [] and _w == [], str(_e + _w))
_e, _w = rubric_check(2.0, HINT, age_days=9)
check("rubric.stale_artifact_silent", _e == [], "a stale payload describes another session")
_e, _w = rubric_check(2.0, HINT, payload_ticker="SOMEONE_ELSE")
check("rubric.ticker_mismatch_silent", _e == [], "an artifact for another ticker proves nothing")
_e, _w = rubric_check(2.0, "not a band")
check("rubric.unparseable_warns", _e == [] and _w != [],
      "an unreadable hint is a warning, not a verdict")

# ── 3. history.json is append_session_export.py's to write ───────────────────
# Literal dates again, for the reason spelled out at CUTOFF above.
PROV_CUTOFF = "2026-08-09"
check("prov.cutoff_matches_policy", V.PROVENANCE_REQUIRED_FROM == PROV_CUTOFF,
      f"validator says {V.PROVENANCE_REQUIRED_FROM!r}, contract says {PROV_CUTOFF!r}")

def compliant(date_str=PROV_CUTOFF):
    """BASE dated at the new cutoff, satisfying every other gate of that era."""
    e = entry_dated(date_str, with_gate=True)
    e["trades_this_session"][0]["news_lane"] = news_lane_ok()
    return e


# A stamped, untouched entry passes; the same entry unstamped does not.
run_validator(appended(compliant()), "prov.stamped_passes", 0)
run_validator(compliant(), "prov.unstamped_after_cutoff", 1, "export_provenance missing")
# Historical entries carry no stamp and must stay silent. Dated one day before
# the cutoff, so every other gate of that era still applies.
run_validator(entry_dated("2026-08-08", with_gate=True), "prov.old_entries_silent", 0)


def tampered(mutate):
    e = appended(compliant())
    mutate(e["trades_this_session"][0], e)
    return e


def _set_score(trade, _entry):
    trade["final_score"] = 1.9999


run_validator(tampered(_set_score), "prov.post_append_edit_caught", 1,
              "entry_digest 不符")
run_validator(tampered(lambda t, e: t.get("calculation_steps", {}).update(raw_total=9.9)),
              "prov.steps_retype_caught", 1, "entry_digest 不符")
run_validator(tampered(lambda t, e: e.__setitem__("final_action", "BUY")),
              "prov.entry_level_edit_caught", 1, "entry_digest 不符")

# The sanctioned chain writes these AFTER the stamp, so the digest must be blind
# to them. Asserted on the digest directly: routing each through the validator
# would drag in §15's own opinions about what a valid det_shadow looks like, and
# fail for reasons that have nothing to do with provenance.
import append_session_export as A                                  # noqa: E402

_ref = A.entry_digest(compliant())
for _label, _mut in (
    ("det_shadow", lambda t: t.__setitem__("det_shadow", {"version": "later"})),
    ("lane_contract", lambda t: t.__setitem__("lane_contract", {"contract_version": "x"})),
    ("thesis_backfill", lambda t: t.update(thesis_id="TH-1",
                                           thesis_registered_at="2026-08-10T00:00:00Z")),
    ("transient_key", lambda t: t.__setitem__("_as_of_date_inherited", "2026-08-10")),
):
    _e2 = compliant()
    _mut(_e2["trades_this_session"][0])
    check(f"prov.{_label}_excluded", A.entry_digest(_e2) == _ref,
          f"{_label} is written by an approved tool after the stamp — including it "
          f"in the digest reds the gate on its own sanctioned path")
# …and the converse: a decision field must move the digest, or the exclusion
# list has swallowed the thing it was meant to protect.
_e2 = compliant()
_e2["trades_this_session"][0]["final_score"] = 1.9999
check("prov.decision_field_moves_digest", A.entry_digest(_e2) != _ref,
      "final_score must be inside the digest")

# A stamp with no digest is a claim, not evidence.
run_validator(tampered(lambda t, e: e["export_provenance"].pop("entry_digest", None)),
              "prov.digest_required", 1, "entry_digest missing")

# End-to-end through the real post-append tools, not a simulation of them: this
# is the case that would break if apply_det_shadow ever wrote a decision field.
_chain = appended(compliant())
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                 encoding="utf-8") as _fp:
    json.dump([_chain], _fp, ensure_ascii=False)
    _chain_path = _fp.name
subprocess.run([sys.executable,
                os.path.join(V.ROOT, "investment/scripts/apply_det_shadow.py"),
                "--inplace", _chain_path], capture_output=True, text=True)
_proc = subprocess.run([sys.executable, VALIDATOR, "--history", _chain_path],
                       capture_output=True, text=True)
check("prov.det_shadow_roundtrip", _proc.returncode == 0,
      f"rc={_proc.returncode} — apply_det_shadow must not invalidate the stamp: "
      f"{(_proc.stdout + _proc.stderr)[:240]}")
os.unlink(_chain_path)


# ── 4. News lane must resolve pt_revision_momentum ───────────────────────────
PT_CUTOFF = "2026-08-09"
check("pt.cutoff_matches_policy", V.PT_MOMENTUM_REQUIRED_FROM == PT_CUTOFF,
      f"validator says {V.PT_MOMENTUM_REQUIRED_FROM!r}, contract says {PT_CUTOFF!r}")


def pt_case(prm, label, want_rc, want_substr=None, *, date=PT_CUTOFF, drop=False):
    e = compliant(date)
    nl = e["trades_this_session"][0]["news_lane"]
    if drop:
        nl.pop("pt_revision_momentum", None)
    else:
        nl["pt_revision_momentum"] = prm
    run_validator(appended(e), label, want_rc, want_substr)


pt_case(None, "pt.missing_after_cutoff", 1, "pt_revision_momentum missing", drop=True)
pt_case(None, "pt.null_after_cutoff", 1, "pt_revision_momentum missing")
# This is the shape the 2026-08-09 export should have carried.
pt_case({"direction": "DOWN", "consensus_delta_pct_1m": -2.94},
        "pt.down_with_delta_passes", 0)
pt_case({"direction": "UP", "consensus_delta_pct_1m": 5.26,
         "consensus_delta_pct_3m": 3.84}, "pt.up_with_delta_passes", 0)
# A direction claim with no magnitude cannot be checked against the ±3% rule.
pt_case({"direction": "UP"}, "pt.direction_without_delta_rejected", 1,
        "consensus_delta_pct_1m")
pt_case({"direction": "FLAT"}, "pt.flat_needs_no_delta", 0)
# UNKNOWN is a first-class answer — with a reason.
pt_case({"direction": "UNKNOWN"}, "pt.unknown_needs_reason", 1, "unavailable_reason")
pt_case({"direction": "UNKNOWN", "unavailable_reason": "   "},
        "pt.blank_reason_rejected", 1, "unavailable_reason")
pt_case({"direction": "UNKNOWN", "unavailable_reason": "FMP grades-historical empty"},
        "pt.unknown_with_reason_passes", 0)
pt_case({"direction": "SIDEWAYS", "consensus_delta_pct_1m": 1.0},
        "pt.bogus_direction_rejected", 1, "direction=")
# Before the cutoff the field stays advisory — 187 entries predate it.
pt_case(None, "pt.old_entries_silent", 0, date="2026-08-08", drop=True)

# Nulling the parent must not switch the requirement off.
_null_parent = compliant()
_null_parent["trades_this_session"][0]["news_lane"] = None
_null_parent["trades_this_session"][0].setdefault("lane_scores", {})["news"] = 3
run_validator(appended(_null_parent), "pt.null_parent_still_caught", 1,
              "news_lane 缺漏但 lane_scores.news")
# …but a lane that genuinely did not run has nothing to declare. Asserted on the
# check directly: an entry with a null news score also needs a matching
# lane_contract, and §15's view of that is a separate argument from this one.
_e, _w = [], []
V._check_pt_revision_momentum(
    {"export_date": PT_CUTOFF},
    {"news_lane": None, "lane_scores": {"news": None}}, _e, _w)
check("pt.genuinely_absent_lane_silent", _e == [], str(_e))
_e, _w = [], []
V._check_pt_revision_momentum(
    {"export_date": PT_CUTOFF},
    {"news_lane": None, "lane_scores": {"news": 3}}, _e, _w)
check("pt.null_parent_with_score_caught", _e != [],
      "a scored lane with no block must not pass")


# ── 5. calculation_steps must equal the engine's last output ─────────────────
ENGINE_DIR = os.path.join(V.ROOT, "investment/invest_logs/decision_engine")
os.makedirs(ENGINE_DIR, exist_ok=True)

REF_STEPS = {
    "fund": "0.25 × 2.5 × 0.72 = 0.4500",
    "raw_total": 1.2348,
    "dynamic_threshold": {"buy_threshold": 1.2, "staged_threshold": 0.8},
    "macro_multiplier": 0.9,
}


def parity_check(steps, *, ticker="ZZPARITY", age_days=0, write=True,
                 artifact_ticker=None, ref=None):
    path = os.path.join(ENGINE_DIR, f"{ticker}_decision_engine.json")
    if write:
        with open(path, "w", encoding="utf-8") as fp:
            json.dump({"ticker": artifact_ticker or ticker,
                       "calculation_steps": ref if ref is not None else REF_STEPS}, fp)
        stamp = time.time() - age_days * 86400
        os.utime(path, (stamp, stamp))
    errors, warnings = [], []
    V._check_calculation_steps_parity(
        {"ticker": ticker}, {"ticker": ticker, "calculation_steps": steps},
        errors, warnings)
    if write and os.path.exists(path):
        os.remove(path)
    return errors, warnings


_e, _w = parity_check(copy.deepcopy(REF_STEPS))
check("parity.identical_passes", _e == [], str(_e))

_e, _w = parity_check({**REF_STEPS, "raw_total": 1.9999})
check("parity.scalar_drift_caught", _e != [], "a retyped raw_total must fail")
check("parity.message_shows_both", any("1.9999" in x and "1.2348" in x for x in _e), str(_e))

# The 2026-08-09 shape: steps from a superseded run with a different valuation.
_e, _w = parity_check({**REF_STEPS, "fund": "0.25 × 1.0 × 0.72 = 0.1800"})
check("parity.step_string_drift_caught", _e != [], "step strings are content too")

_e, _w = parity_check({**REF_STEPS,
                       "dynamic_threshold": {"buy_threshold": 0.5, "staged_threshold": 0.8}})
check("parity.nested_drift_caught", _e != [], "nested blocks must be walked")

_missing = copy.deepcopy(REF_STEPS)
_missing.pop("macro_multiplier")
_e, _w = parity_check(_missing)
check("parity.missing_key_caught", _e != [], "dropping an engine key is drift too")

# Extra keys belong to other schema sections, not to this comparison.
_e, _w = parity_check({**REF_STEPS, "some_other_field": 1})
check("parity.extra_key_ignored", _e == [], str(_e))

# Float re-serialisation must not read as drift.
_e, _w = parity_check({**REF_STEPS, "raw_total": 1.2348000000000001})
check("parity.float_noise_tolerated", _e == [], str(_e))

# No evidence → no verdict (same discipline as the rubric gate).
_e, _w = parity_check(copy.deepcopy(REF_STEPS), write=False, ticker="ZZNOARTIFACT")
check("parity.absent_artifact_silent", _e == [] and _w == [], str(_e + _w))
_e, _w = parity_check({**REF_STEPS, "raw_total": 1.9999}, age_days=9)
check("parity.stale_artifact_silent", _e == [], "a stale artifact describes another run")
_e, _w = parity_check({**REF_STEPS, "raw_total": 1.9999}, artifact_ticker="OTHER")
check("parity.ticker_mismatch_silent", _e == [], "another ticker's artifact proves nothing")

# The producer half: decision_engine.py must actually leave the artifact behind,
# or every case above is checking a file nobody writes.
_P3_IN = {
    "ticker": "ZZENGINE",
    "lane_scores": {"fundamentals": 1.0, "sentiment": 0.5, "news": 0.5,
                    "technical": 0.5, "valuation": 0.5},
    "lane_confidence": {k: 0.6 for k in ("fundamentals", "sentiment", "news",
                                         "technical", "valuation")},
    "structural_shift": {"tier": "NONE"},
    "red_team": {"verdict": "MODERATE_COUNTER", "basis": "unclassified"},
    "macro": {"macro_multiplier": 1.0, "macro_backdrop_score": 2.0,
              "market_regime": "RISK_ON"},
    "burry": {"score": 50.0, "veto_flag": False},
    "gates": {"proceed_to_phase3": True, "mandatory_risk_flags": [],
              "phase2_fanout_mode": "PARALLEL_SUBAGENT", "risk_reward_ratio": 3.0},
    "hot_zone": {"industry_top_30pct": True},
    "decision_cap": {"anchors_available": 5, "fair_value_confidence": "medium",
                     "lane_data_quality_low": False},
}
_art = os.path.join(ENGINE_DIR, "ZZENGINE_decision_engine.json")
if os.path.exists(_art):
    os.remove(_art)
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                 encoding="utf-8") as _fp:
    json.dump(_P3_IN, _fp)
    _p3_path = _fp.name
_proc = subprocess.run(
    [sys.executable, os.path.join(V.ROOT, "investment/scripts/decision_engine.py"),
     "--from-file", _p3_path], capture_output=True, text=True)
check("parity.engine_writes_artifact", os.path.exists(_art),
      f"decision_engine.py left no artifact (rc={_proc.returncode}) — the gate above "
      f"would then be silent on every real session")
if os.path.exists(_art):
    with open(_art, encoding="utf-8") as _fp:
        _written = json.load(_fp)
    _stdout = json.loads(_proc.stdout)
    check("parity.artifact_matches_stdout",
          _written.get("calculation_steps") == _stdout.get("calculation_steps"),
          "the persisted block must be the one the engine just printed")
    # Feeding the engine's own output back must pass — otherwise the gate reds on
    # a session that did everything right.
    _e, _w = parity_check(_stdout["calculation_steps"], ticker="ZZENGINE", write=False)
    check("parity.engine_output_self_consistent", _e == [], str(_e))
    os.remove(_art)
os.unlink(_p3_path)

# ── 6. --replace-last is the sanctioned fix path ─────────────────────────────
# Without it the documented remediation is "re-append", which leaves two entries
# for one session — history already carries five such pairs. The hand-rolled
# alternative is the `h.pop()` + `json.dump` that this whole version exists to
# stop, so the fix path has to be reachable through the script.
def replace_last_case(first, second, label, want_rc, *, want_len=None):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as fp:
        json.dump([], fp)
        hist = fp.name
    try:
        for entry, flags in ((first, []), (second, ["--replace-last"])):
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                             encoding="utf-8") as fp:
                json.dump(entry, fp, ensure_ascii=False)
                src = fp.name
            proc = subprocess.run(
                [sys.executable, APPENDER, "--from-file", src, "--history", hist,
                 *flags], capture_output=True, text=True)
            os.unlink(src)
            if flags:
                check(f"{label}.rc", proc.returncode == want_rc,
                      f"rc={proc.returncode} want {want_rc} — "
                      f"{(proc.stdout + proc.stderr)[:200]}")
        if want_len is not None:
            with open(hist, encoding="utf-8") as fp:
                got = len(json.load(fp))
            check(f"{label}.len", got == want_len, f"{got} entries, want {want_len}")
    finally:
        os.unlink(hist)


_first = compliant()
_fixed = compliant()
_fixed["trades_this_session"][0]["news_lane"]["pt_revision_momentum"] = {
    "direction": "UP", "consensus_delta_pct_1m": 4.1}
replace_last_case(_first, _fixed, "replace.same_session", 0, want_len=1)

_other = compliant()
_other["ticker"] = "ZZOTHER"
_other["trades_this_session"][0]["ticker"] = "ZZOTHER"
replace_last_case(_first, _other, "replace.refuses_other_session", 1, want_len=1)

_other_day = compliant("2026-08-11")
replace_last_case(_first, _other_day, "replace.refuses_other_date", 1, want_len=1)

# The replacement is a fresh write, so it must carry a stamp that matches ITS
# content — otherwise the fix path would hand back an entry the gate then reds.
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                 encoding="utf-8") as _fp:
    json.dump([], _fp)
    _rl_hist = _fp.name
for _entry, _flags in ((_first, []), (_fixed, ["--replace-last"])):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as _fp:
        json.dump(_entry, _fp, ensure_ascii=False)
        _src = _fp.name
    subprocess.run([sys.executable, APPENDER, "--from-file", _src,
                    "--history", _rl_hist, *_flags], capture_output=True, text=True)
    os.unlink(_src)
_proc = subprocess.run([sys.executable, VALIDATOR, "--history", _rl_hist],
                       capture_output=True, text=True)
check("replace.result_validates", _proc.returncode == 0,
      f"rc={_proc.returncode} — the sanctioned fix path must produce a passing "
      f"entry: {(_proc.stdout + _proc.stderr)[:240]}")
os.unlink(_rl_hist)


# Wiring, not just behaviour. Every case above calls the check directly, so
# unhooking it from main() left them all green — the V4.116.2 shape, where
# `invest` was absent from PROTOCOL_VALIDATORS for its whole life while the docs
# said otherwise. A gate that exists and is never called has no symptom, so the
# call site needs its own assertion.
def parity_wired(art_steps, label, want_rc, want_substr=None):
    e = compliant()
    tk = "ZZWIRED"
    e["ticker"] = tk
    trade = e["trades_this_session"][0]
    trade["ticker"] = tk
    if isinstance(trade.get("valuation_reviewer_gate"), dict):
        trade["valuation_reviewer_gate"]["ticker"] = tk
    path = os.path.join(ENGINE_DIR, f"{tk}_decision_engine.json")
    with open(path, "w", encoding="utf-8") as fp:
        json.dump({"ticker": tk, "calculation_steps": art_steps}, fp)
    try:
        run_validator(appended(e), label, want_rc, want_substr)
    finally:
        os.remove(path)


_live_total = (compliant()["trades_this_session"][0]
               .get("calculation_steps", {}).get("raw_total"))
check("parity.fixture_has_raw_total", _live_total is not None,
      "the FULL EXAMPLE stopped carrying calculation_steps.raw_total — "
      "the wiring case below needs a real field to disagree about")
parity_wired({"raw_total": 9.9999}, "parity.wired_into_main", 1,
             "decision_engine.py 最後一次的輸出不符")
parity_wired({"raw_total": _live_total}, "parity.wired_agreeing_passes", 0)

# ── 6. V4.122.0 §16 — Phase 2.5 `conflict_bias` ──────────────────────────────
# 同一個形狀的洞，這次在 Phase 2.5：protocol 要求 PM 產一塊 JSON，沒有任何欄位接住它，
# 於是 189 筆歷史 entry 一筆紀錄都沒有 —— T4 能 CANCEL、T5 宣稱降階，而「有沒有觸發」
# 事後不可考。§16 改成由 validator **重算** T1–T5 應觸發集合再與宣稱比對。
#
# 兩層測試：先用字面輸入釘住重算函式的契約，再驅動真 validator 證明它接進了主流程。
# 只有後者會被「忘了在 main() 裡呼叫」抓到，只有前者能在不牽動 §13/§14 的情況下
# 覆蓋每一條不等式（lane score / macro 都被別節重算，動它們會為了別的理由變紅）。

# 截止日寫死成字面值，不讀 V.CONFLICT_BIAS_REQUIRED_FROM —— 讀了就會跟著它一起移動，
# 種回 bug 也照樣綠（MAINTENANCE §2c，本檔開頭那條前例）。
CB_CUTOFF = "2026-08-10"
check("cb.cutoff_matches_policy", V.CONFLICT_BIAS_REQUIRED_FROM == CB_CUTOFF,
      f"validator says {V.CONFLICT_BIAS_REQUIRED_FROM!r}, contract says {CB_CUTOFF!r}")

# 重算契約：輸入全是字面值，期望也是字面值。
_S = {"fundamentals": 4.0, "sentiment": 3.0, "news": 3.0, "technical": 4.0,
      "valuation": 1.0}
_SIG = {l: "BUY" for l in V.CONFLICT_LANES}


def cb_eval(label, want, *, scores=None, signals=None, macro=-1.0, burry=37.1,
            tentative="BUY", forward=None):
    sc = dict(_S, **(scores or {}))
    sg = dict(_SIG, **(signals or {}))
    got = V.evaluate_conflict_triggers(sc, sg, macro, burry, tentative, forward)
    for trig, expect in want.items():
        check(f"cb.eval.{label}.{trig}", got[trig] is expect,
              f"{trig}={got[trig]!r} want {expect!r}")


cb_eval("baseline", {"T1": False, "T2": False, "T3": False, "T4": False,
                     "T5": False, "ANTI_BIAS": True})
# T1 — sentiment 過熱 vs fundamentals 轉負。>3 是嚴格不等式：3.0 不觸發、3.5 才觸發。
cb_eval("t1_boundary", {"T1": False}, scores={"sentiment": 3.0, "fundamentals": -1.0})
cb_eval("t1_fires", {"T1": True}, scores={"sentiment": 3.5, "fundamentals": -1.0})
cb_eval("t1_needs_negative_fund", {"T1": False},
        scores={"sentiment": 3.5, "fundamentals": 0.0})
# T2 — news 重挫但 technical 仍喊進；signal 是條件的一半，HOLD 就不觸發。
cb_eval("t2_fires", {"T2": True}, scores={"news": -4.0})
cb_eval("t2_needs_buy_signal", {"T2": False}, scores={"news": -4.0},
        signals={"technical": "HOLD"})
# T3 — macro 逆風下仍有 lane 高分喊進。
cb_eval("t3_fires", {"T3": True}, macro=-4.0)
cb_eval("t3_needs_bad_macro", {"T3": False}, macro=-3.0)
cb_eval("t3_needs_high_buy_lane", {"T3": False}, macro=-4.0,
        scores={"fundamentals": 1.0, "sentiment": 1.0, "news": 1.0,
                "technical": 1.0, "valuation": 1.0})
# T4 — burry veto 撞上 tentative BUY。
cb_eval("t4_fires", {"T4": True}, burry=15.0)
cb_eval("t4_boundary", {"T4": False}, burry=20.0)
cb_eval("t4_needs_buy_tentative", {"T4": False}, burry=15.0, tentative="HOLD")
# T5 — 負估值 + BUY 側 tentative 還不夠；forward_validation 必須明確 FAIL。
_FV_FAIL = {"status": "FAIL", "applies": True}
cb_eval("t5_fires", {"T5": True}, scores={"valuation": -2.0}, forward=_FV_FAIL)
cb_eval("t5_staged_counts", {"T5": True}, scores={"valuation": -3.0},
        tentative="STAGED_ENTRY", forward=_FV_FAIL)
cb_eval("t5_hold_does_not", {"T5": False}, scores={"valuation": -3.0},
        tentative="HOLD", forward=_FV_FAIL)
cb_eval("t5_forward_support_blocks", {"T5": False}, scores={"valuation": -3.0},
        tentative="STAGED_ENTRY", forward={"status": "STRETCHED", "applies": True})
cb_eval("t5_missing_forward_is_unknown", {"T5": None}, scores={"valuation": -3.0},
        tentative="STAGED_ENTRY")
# 缺輸入 → None（不得猜成 False）。判 False 等於替最需要證據的那一側背書。
cb_eval("indeterminate_missing_score", {"T5": None}, scores={"valuation": None})
cb_eval("indeterminate_missing_signal", {"T2": None}, scores={"news": -4.0},
        signals={"technical": None})
cb_eval("indeterminate_missing_macro", {"T3": None}, macro=None)
cb_eval("indeterminate_missing_tentative", {"T4": None, "T5": None}, burry=15.0,
        tentative=None)
# 同向：五個 lane 有一個反向就不算。
cb_eval("anti_bias_needs_all_five", {"ANTI_BIAS": False},
        scores={"valuation": -1.0})


def cb_case(label, want_rc, want_substr=None, *, date=CB_CUTOFF, mutate=None):
    """真 validator，跑在 schema 文件自己的 FULL EXAMPLE 上。"""
    e = compliant(date)
    if mutate:
        mutate(e["trades_this_session"][0], e)
    run_validator(appended(e), label, want_rc, want_substr)


# FULL EXAMPLE 帶著合法的 block，所以基準線必須綠 —— 否則以下每個紅都可能是它自己壞了。
cb_case("cb.compliant_passes", 0)
check("cb.fixture_has_block",
      isinstance(BASE["trades_this_session"][0].get("conflict_bias"), dict),
      "schema 文件的 FULL EXAMPLE 沒有 conflict_bias，以下 case 全部驗不到東西")

cb_case("cb.missing_after_cutoff", 1, "conflict_bias missing",
        mutate=lambda t, e: t.pop("conflict_bias"))
# 189 筆歷史 entry 沒有這塊，截止日之前必須完全靜默。
cb_case("cb.missing_before_cutoff_silent", 0, date="2026-08-09",
        mutate=lambda t, e: t.pop("conflict_bias"))

# 重算已接進主流程：多報一個條件不成立的 trigger。這條不動任何 lane 分數，
# 所以紅一定來自 §16 而不是 §13。
cb_case("cb.overclaim_is_red", 1, "多報了",
        mutate=lambda t, e: t["conflict_bias"].update(
            triggers_fired=["ANTI_BIAS", "T1"]))
# 少報：burry_score 不被 §13/§14 重算，是唯一能單獨翻動的 trigger 輸入。
cb_case("cb.underclaim_is_red", 1, "少了",
        mutate=lambda t, e: t.update(burry_score=15.0))
# 同一筆輸入、照實申報就過 —— 證明上一條紅的是「沒申報」而不是「burry 低」。
cb_case("cb.underclaim_declared_passes", 0,
        mutate=lambda t, e: (t.update(burry_score=15.0), t["conflict_bias"].update(
            triggers_fired=["ANTI_BIAS", "T4"],
            t4_detail={"burry_score": 15.0, "resolution": "DOWNGRADE_DECISION",
                       "override_justification": None,
                       "override_recheck_date": None})))

# 新自陳欄位的兩道錨。
cb_case("cb.signal_contradicts_score", 1, "反向",
        mutate=lambda t, e: t["conflict_bias"]["lane_signals"].update(news="SELL"))
cb_case("cb.valuation_signal_must_match_lane", 1, "valuation_lane.signal",
        mutate=lambda t, e: t["conflict_bias"]["lane_signals"].update(valuation="HOLD"))
cb_case("cb.lane_signals_must_list_all_five", 1, "missing lane(s)",
        mutate=lambda t, e: t["conflict_bias"]["lane_signals"].pop("technical"))

# 後果錨：OVERRIDE_BURRY ⟺ burry_override_active 雙向鎖。那個布林餵 ×0.5 進 §14 的
# sizing chain —— 本節唯一錨在「已經在改倉位的數字」上的檢查。
_OVERRIDE_T4 = {"burry_score": 15.0, "resolution": "OVERRIDE_BURRY",
                "override_justification": "Fundamentals lane 指 HBM 合約已鎖定四季，"
                                          "Burry 的 FCF 折價反映的是舊產品組合",
                "override_recheck_date": "2026-08-17"}
cb_case("cb.override_without_active_flag", 1, "burry_override_active",
        mutate=lambda t, e: (t.update(burry_score=15.0), t["conflict_bias"].update(
            triggers_fired=["ANTI_BIAS", "T4"], t4_detail=dict(_OVERRIDE_T4))))
cb_case("cb.active_flag_without_override_record", 1,
        "沒有記錄 T4 的 OVERRIDE_BURRY",
        mutate=lambda t, e: t.update(burry_override_active=True))
cb_case("cb.override_justification_too_short", 1, "override_justification",
        mutate=lambda t, e: (t.update(burry_score=15.0, burry_override_active=True),
                             t["conflict_bias"].update(
                                 triggers_fired=["ANTI_BIAS", "T4"],
                                 t4_detail=dict(_OVERRIDE_T4, override_justification="太短"))))
cb_case("cb.t4_detail_must_be_null_when_not_fired", 1, "must be null",
        mutate=lambda t, e: t["conflict_bias"].update(t4_detail=dict(_OVERRIDE_T4)))

cb_case("cb.no_proceed_must_be_cancel", 1, "proceed_to_phase3=false",
        mutate=lambda t, e: t["conflict_bias"].update(proceed_to_phase3=False))
cb_case("cb.schema_tag_enforced", 1, "conflict_bias.schema",
        mutate=lambda t, e: t["conflict_bias"].update(schema="conflict_bias.v2"))

# Engine 1.1.0 is the cutover: omitting the deterministic block must fail through
# the real validator entry point, not merely through a directly-called helper.
cb_case("forward.required_for_engine_1_1", 1, "forward_validation missing",
        mutate=lambda t, e: t.update(decision_engine_version="1.1.0"))

# Legacy 1.0.x 沒有 producer，仍維持歷史相容：valuation ≤−3 只留 warning。
_t5_errors, _t5_warnings = [], []
V.check_conflict_bias(
    {"export_date": CB_CUTOFF, "phase0_macro_snapshot": {"macro_backdrop_score": -1.0}},
    {"final_decision": "STAGED_ENTRY", "final_action": "STAGED", "burry_score": 37.1,
     "lane_scores": {"fundamentals": 2.5, "sentiment": 2.0, "news": 2.0,
                     "technical": 2.5, "valuation": -3.0},
     "valuation_lane": {"signal": "SELL", "score": -3.0},
     "conflict_bias": {"schema": "conflict_bias.v1", "tentative_decision": "STAGED_ENTRY",
                       "lane_signals": {"fundamentals": "BUY", "sentiment": "BUY",
                                        "news": "BUY", "technical": "BUY",
                                        "valuation": "SELL"},
                       "triggers_fired": ["T5"],
                       "t4_detail": None,
                       "t5_detail": {"valuation_score": -3.0, "downgrade_applied": False},
                       "proceed_to_phase3": True}},
    _t5_errors, _t5_warnings)
check("cb.t5_legacy_is_not_enforced", not _t5_errors,
      f"engine 1.0.x 沒有 producer，validator 不得溯及既往：{_t5_errors}")
check("cb.t5_legacy_is_recorded", any("T5" in w for w in _t5_warnings),
      f"legacy T5 至少要留下 warning：{_t5_warnings}")

# New engine: the exact same false non-downgrade is now an error when forward FAIL exists.
_new_t5 = {
    "forward_validation_status": "FAIL", "forward_validation_applies": True,
    "valuation_score": -3.0, "warning_triggered": True,
    "hard_downgrade_eligible": True, "downgrade_applied": False,
    "decision_before": "STAGED_ENTRY", "decision_after": "STAGED_ENTRY",
}
_new_t5_errors, _new_t5_warnings = [], []
V.check_conflict_bias(
    {"export_date": CB_CUTOFF, "phase0_macro_snapshot": {"macro_backdrop_score": -1.0}},
    {"decision_engine_version": "1.1.0", "final_decision": "STAGED_ENTRY",
     "final_action": "STAGED", "burry_score": 37.1,
     "forward_validation": {"status": "FAIL", "applies": True},
     "calculation_steps": {"t5_forward_validation": dict(_new_t5)},
     "lane_scores": {"fundamentals": 2.5, "sentiment": 2.0, "news": 2.0,
                     "technical": 2.5, "valuation": -3.0},
     "valuation_lane": {"signal": "SELL", "score": -3.0},
     "conflict_bias": {"schema": "conflict_bias.v1", "tentative_decision": "STAGED_ENTRY",
                       "lane_signals": {"fundamentals": "BUY", "sentiment": "BUY",
                                        "news": "BUY", "technical": "BUY",
                                        "valuation": "SELL"},
                       "triggers_fired": ["T5"], "t4_detail": None,
                       "t5_detail": dict(_new_t5), "proceed_to_phase3": True}},
    _new_t5_errors, _new_t5_warnings)
check("cb.t5_new_engine_enforces_downgrade",
      any("hard downgrade eligible" in e for e in _new_t5_errors),
      f"engine 1.1.0 的 T5 必須把未降級升為 error：{_new_t5_errors}")

# ── 7. V4.122.0 §17 — Phase 2 fan-in 紀律（inline fallback 的 confidence cap）─────
# 「subagent 失敗 → PM inline，confidence cap 0.6」從 V4.8 寫到今天，沒有一處驗算過。
# 沒接線的欄位會自己爛掉：188 筆 export 用了 10 種寫法指涉 5 個 lane，`phase2_fanout_mode`
# 還出現過表外值 `FULL` —— cap 接不上去的原因就是它的鍵讀不動。

FANIN_CUTOFF = "2026-08-10"          # 字面值，不讀被測常數（§2c）
check("fanin.cutoff_matches_policy", V.FANIN_REQUIRED_FROM == FANIN_CUTOFF,
      f"validator says {V.FANIN_REQUIRED_FROM!r}, contract says {FANIN_CUTOFF!r}")

# 名稱正規化：歷史上真的出現過的 10 種寫法必須全部解析得回 lane，否則 cap 對不上。
for _label, _want in (
    ("News", "news"),
    ("News (skill fallback to web)", "news"),
    ("Technical (skill fallback to yfinance)", "technical"),
    ("Fundamentals (skill_execution_failed: analyze.py missing)", "fundamentals"),
    ("Valuation", "valuation"),
    ("Valuation_Specialist", "valuation"),
    ("Valuation_Specialist_low_anchor_count_3of6", "valuation"),
    ("sentiment — inline", "sentiment"),
    ("Red_Team", None),              # 不是五個分析 lane 之一
    ("", None),
):
    check(f"fanin.resolve({_label[:28]!r})", V.resolve_degraded_lane(_label) == _want,
          f"got {V.resolve_degraded_lane(_label)!r} want {_want!r}")

# C_eff 取自 step 字串，且與 §13 共用同一組 `_STEP_RE` / `_STEP_LANES`。
_ceffs = V._step_ceffs(BASE["trades_this_session"][0].get("calculation_steps"))
check("fanin.ceff_parsed_from_steps", set(_ceffs) == set(V.CONFLICT_LANES),
      f"從 FULL EXAMPLE 的 calculation_steps 只解析出 {sorted(_ceffs)}")


def fanin_case(label, want_rc, want_substr=None, *, date=FANIN_CUTOFF, mutate=None):
    e = compliant(date)
    if mutate:
        mutate(e["trades_this_session"][0], e)
    run_validator(appended(e), label, want_rc, want_substr)


fanin_case("fanin.compliant_passes", 0)

# 真正的 cap：降級的 lane 帶著滿檔 C_eff=0.72 進加權。**FULL EXAMPLE 五個 lane 全是 0.72**
# （乾淨場次本來就沒有降級 lane），所以把任一個列進 degraded 都會撞 cap，不必動任何數字。
# 也因此以下每個 case 都會連帶噴 cap error —— `want_substr` 各自挑只有目標規則會產生的字串，
# 否則測的就變成「有沒有紅」而不是「哪一條紅」。
fanin_case("fanin.degraded_lane_keeps_full_confidence", 1, "confidence cap 0.6",
           mutate=lambda t, e: t.update(degraded_analysts=["Fundamentals"],
                                        phase2_fanout_mode="PARTIAL_FALLBACK"))
# 正面案例走函式層：fixture 裡沒有 C_eff ≤ 0.60 的 lane，而改 step 字串會連鎖破壞 §13 的
# 算術鏈（raw_total / final_score 全要跟著重算），紅的理由就不是本節了。接線已由上一條
# subprocess 案例證明，這裡要證的只是「門檻是 0.60，不是『出現在 degraded 裡就紅』」。
_cap_err, _cap_warn = [], []
V.check_fanin_discipline(
    {"export_date": FANIN_CUTOFF},
    {"degraded_analysts": ["Technical (skill fallback to yfinance)"],
     "phase2_fanout_mode": "PARTIAL_FALLBACK",
     "calculation_steps": {"fund": "0.25 × 4 × 0.72 = 0.7200",
                           "sent": "0.15 × 3 × 0.72 = 0.3240",
                           "news": "0.20 × 3 × 0.72 = 0.4320",
                           "tech": "0.25 × 4 × 0.60 = 0.6000",
                           "val":  "0.15 × 1 × 0.72 = 0.1080"}},
    _cap_err, _cap_warn)
check("fanin.degraded_lane_within_cap_passes", not _cap_err,
      f"C_eff 0.60 是 cap 的合法值（PLTR 2026-08-09 實際就是這樣跑的）：{_cap_err}")

fanin_case("fanin.unresolvable_label_is_red", 1, "無法解析回 lane 名",
           mutate=lambda t, e: t.update(degraded_analysts=["蘭恩壞了"],
                                        phase2_fanout_mode="PARTIAL_FALLBACK"))
fanin_case("fanin.bad_mode_enum", 1, "outside",
           mutate=lambda t, e: t.update(phase2_fanout_mode="FULL"))
fanin_case("fanin.two_degraded_needs_partial", 1, "PARTIAL_FALLBACK",
           mutate=lambda t, e: t.update(
               degraded_analysts=["Valuation_Specialist", "Sentiment"]))
fanin_case("fanin.duplicate_lane", 1, "出現多次",
           mutate=lambda t, e: t.update(
               degraded_analysts=["Valuation", "Valuation_Specialist"],
               phase2_fanout_mode="PARTIAL_FALLBACK"))
fanin_case("fanin.full_fallback_needs_five", 1, "FULL_FALLBACK 的定義",
           mutate=lambda t, e: t.update(degraded_analysts=["Valuation_Specialist"],
                                        phase2_fanout_mode="FULL_FALLBACK"))
fanin_case("fanin.full_fallback_needs_strong_counter", 1, "STRONG_COUNTER",
           mutate=lambda t, e: t.update(
               degraded_analysts=["Fundamentals", "Sentiment", "News", "Technical",
                                  "Valuation"],
               phase2_fanout_mode="FULL_FALLBACK",
               red_team_verdict="MODERATE_COUNTER"))

# 舊 entry 的 10 種寫法是既成事實：截止日之前只給 warning，不回頭紅它們。
fanin_case("fanin.old_entries_only_warn", 0, date="2026-08-09",
           mutate=lambda t, e: t.update(degraded_analysts=["蘭恩壞了"],
                                        phase2_fanout_mode="FULL"))
# 但 cap 本身是 V4.8 就有的規則，不隨截止日放行。
fanin_case("fanin.cap_applies_before_cutoff_too", 1, "confidence cap 0.6",
           date="2026-08-09",
           mutate=lambda t, e: t.update(degraded_analysts=["Fundamentals"],
                                        phase2_fanout_mode="PARTIAL_FALLBACK"))

if failures:
    print("✗ export gate contract violated:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("✓ export gate contract holds (valuation_reviewer_gate + technical rubric + "
      "export_provenance + pt_revision_momentum + calculation_steps parity + "
      "forward_validation + conflict_bias + fan-in discipline)")

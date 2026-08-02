#!/usr/bin/env python3
"""test_valuation_reviewer_gate.py — V4.89.0 gate + peer discovery cache 回歸測試。

鎖住三件事：
  1. 五條 trigger 各自獨立命中（含全靜默 → would_invoke=false）；mandatory 旗標正確
  2. peer discovery cache 的優先序與 TTL；**永不覆寫人工核准的 config**
  3. artifact 不可用一律 rc=1（gate 不得用猜的輸入產 shadow 樣本）

純 stdlib、零網路（peer/transition 全部注入，不讀真實 cache）。
Run: python3 investment/scripts/test_valuation_reviewer_gate.py   # rc=0 全過 / rc=1 fail
"""
import copy
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(BASE_DIR, "skills", "valuation-modeler", "scripts"))

from valuation_reviewer_gate import (  # noqa: E402
    CONFLICT_CV,
    GATE_SCHEMA,
    GateInputError,
    build_gate_record,
    evaluate_triggers,
    load_quant_artifact,
)
import peer_cohorts  # noqa: E402

FAILS = []


def eq(label, got, want):
    if got != want:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


TODAY = dt.date(2026, 8, 2)

# 全靜默 baseline：五條 trigger 一條都不該命中
QUIET = {
    "schema": "price_framework_quant.v1",
    "engine": "compute_price_framework.py v2.3 (V4.88.0)",
    "ticker": "ZZTEST",
    "quant_blocks": {
        "valuation_pack": {
            "structural_shift": {}, "verdict_band": "overvalued", "vs_current_pct": -14.0,
        },
        "fair_value_summary": {"confidence": "high", "anchors_available": 7},
        "fair_value_range": {"anchor_dispersion_cv": 0.20, "dispersion_ratio": 1.8,
                             "agreement_grade": "high"},
    },
}
PEERS_OK = {"available": True, "provenance": "curated", "peer_count": 3, "expires_on": None,
            "reason": None}
NO_TRANSITION = {"transition_signature": None, "forecaster_transition_case": False,
                 "earnings_cache_found": True, "forecaster_cache_found": True}


def record(quant=None, *, peers=None, transition=None):
    return build_gate_record(quant or copy.deepcopy(QUIET), ticker="ZZTEST", today=TODAY,
                             peer_availability=peers or dict(PEERS_OK),
                             transition=transition or dict(NO_TRANSITION))


def fired_of(rec):
    return sorted(rec["triggers_fired"])


# ── 1. 全靜默 ────────────────────────────────────────────────────────────────
base = record()
eq("quiet.schema", base["schema"], GATE_SCHEMA)
eq("quiet.would_invoke", base["would_invoke"], False)
eq("quiet.fired", fired_of(base), [])
eq("quiet.shadow_only", base["shadow_only"], True)
eq("quiet.mandatory", base["mandatory_fired"], False)
eq("quiet.trigger_count", len(base["triggers"]), 5)

# ── 2. transition_case_active（mandatory）──────────────────────────────────
for sig in ("paradigm_only", "mix_only", "both"):
    r = record(transition={**NO_TRANSITION, "transition_signature": sig})
    eq(f"transition.sig_{sig}", fired_of(r), ["transition_case_active"])
    eq(f"transition.mandatory_{sig}", r["mandatory_fired"], True)
r = record(transition={**NO_TRANSITION, "forecaster_transition_case": True})
eq("transition.forecaster_case", fired_of(r), ["transition_case_active"])
# 非清單內的 signature 不該命中（避免任何字串都當 transition）
r = record(transition={**NO_TRANSITION, "transition_signature": "none"})
eq("transition.unknown_sig_quiet", fired_of(r), [])

# ── 3. no_peer_cohort ───────────────────────────────────────────────────────
r = record(peers={"available": False, "provenance": None, "peer_count": 0,
                  "expires_on": None, "reason": "no_curated_peer_cohort"})
eq("peers.fired", fired_of(r), ["no_peer_cohort"])
eq("peers.not_mandatory", r["mandatory_fired"], False)
r = record(peers={"available": True, "provenance": "discovered", "peer_count": 3,
                  "expires_on": "2026-09-01", "reason": None})
eq("peers.discovered_counts", fired_of(r), [])

# ── 4. structural_shift_typed ───────────────────────────────────────────────
shift_q = copy.deepcopy(QUIET)
shift_q["quant_blocks"]["valuation_pack"]["structural_shift"] = {
    "status": "CONFIRMED", "evidence_date": "2026-07-15", "provenance": "filing"}
eq("shift.fired", fired_of(record(shift_q)), ["structural_shift_typed"])
# typed input 不齊 → 不命中（與 engine 的 advisory-only 規則一致）
partial = copy.deepcopy(QUIET)
partial["quant_blocks"]["valuation_pack"]["structural_shift"] = {"status": "CONFIRMED"}
eq("shift.incomplete_quiet", fired_of(record(partial)), [])

# ── 5. anchor_conflict_severe（三個判準各自獨立）──────────────────────────
for label, patch in (("cv", {"anchor_dispersion_cv": CONFLICT_CV}),
                     ("span", {"dispersion_ratio": 6.0}),
                     ("grade", {"agreement_grade": "low"})):
    q = copy.deepcopy(QUIET)
    q["quant_blocks"]["fair_value_range"].update(patch)
    eq(f"conflict.{label}", fired_of(record(q)), ["anchor_conflict_severe"])

# ── 6. low_quality_possible_buy（proxy 的兩側都要驗）────────────────────────
lowq = copy.deepcopy(QUIET)
lowq["quant_blocks"]["fair_value_summary"] = {"confidence": "low", "anchors_available": 2}
# 高估側 → 不命中（誤判成本對稱，不值得叫 reviewer）
eq("lowq.overvalued_quiet", fired_of(record(lowq)), [])
buyish = copy.deepcopy(lowq)
buyish["quant_blocks"]["valuation_pack"]["verdict_band"] = "undervalued"
buyish["quant_blocks"]["valuation_pack"]["vs_current_pct"] = 18.0
eq("lowq.possible_buy_fires", fired_of(record(buyish)), ["low_quality_possible_buy"])
# anchors 少但 confidence 高 → 仍算低品質（兩個條件是 OR）
few = copy.deepcopy(buyish)
few["quant_blocks"]["fair_value_summary"] = {"confidence": "high", "anchors_available": 3}
eq("lowq.few_anchors_fires", fired_of(record(few)), ["low_quality_possible_buy"])
enough = copy.deepcopy(buyish)
enough["quant_blocks"]["fair_value_summary"] = {"confidence": "high", "anchors_available": 6}
eq("lowq.enough_anchors_quiet", fired_of(record(enough)), [])
# verdict 未知 = 不在高估側（估值完全算不出來時最該叫 reviewer，不是最不該）
unknown = copy.deepcopy(QUIET)
unknown["quant_blocks"]["fair_value_summary"] = {"confidence": "low", "anchors_available": None}
unknown["quant_blocks"]["valuation_pack"].update({"verdict_band": None, "vs_current_pct": None})
eq("lowq.unknown_verdict_fires", fired_of(record(unknown)), ["low_quality_possible_buy"])

# 多條同時命中 → 全列出
multi = copy.deepcopy(buyish)
multi["quant_blocks"]["fair_value_range"]["agreement_grade"] = "low"
r = record(multi, peers={"available": False, "provenance": None, "peer_count": 0,
                         "expires_on": None, "reason": "no_curated_peer_cohort"},
           transition={**NO_TRANSITION, "transition_signature": "both"})
eq("multi.all_fired", fired_of(r),
   ["anchor_conflict_severe", "low_quality_possible_buy", "no_peer_cohort",
    "transition_case_active"])
eq("multi.mandatory", r["mandatory_fired"], True)

# trigger 名單本身是契約——漏一條 = shadow 統計少一維且不會報錯
eq("triggers.names", sorted(t["trigger"] for t in base["triggers"]),
   ["anchor_conflict_severe", "low_quality_possible_buy", "no_peer_cohort",
    "structural_shift_typed", "transition_case_active"])
eq("triggers.exactly_one_mandatory",
   [t["trigger"] for t in base["triggers"] if t["mandatory"]], ["transition_case_active"])

# ── 7. peer discovery cache：優先序 / TTL / 不覆寫人工核准 ──────────────────
with tempfile.TemporaryDirectory() as tmp:
    cfg = os.path.join(tmp, "peer_cohorts.json")
    cache = os.path.join(tmp, "peer_discovery.json")
    with open(cfg, "w", encoding="utf-8") as fh:
        json.dump({"schema": "valuation_peer_cohorts.v1", "cohorts": {
            "MU": {"name": "memory", "approved_by": "user",
                   "candidates": [{"ticker": "SNDK"}, {"ticker": "WDC"}, {"ticker": "STX"}]}}}, fh)

    def avail(ticker, today=TODAY):
        return peer_cohorts.resolve_cohort_availability(
            ticker, config_path=cfg, discovery_path=cache, today=today)

    eq("cache.cold_start", avail("NVDA")["available"], False)
    eq("cache.curated_wins_provenance", avail("MU")["provenance"], "curated")
    eq("cache.curated_peer_count", avail("MU")["peer_count"], 3)

    # 寫入 discovered → 變 available，且 config 一個位元都沒動
    cfg_before = open(cfg, encoding="utf-8").read()
    res = peer_cohorts.record_discovered_cohort(
        "NVDA", [{"ticker": "AMD", "role": "accelerator"}, {"ticker": "AVGO", "role": "custom ASIC"},
                 {"ticker": "MRVL", "role": "custom ASIC"}],
        path=cache, config_path=cfg, today=TODAY, rationale="fixture")
    eq("cache.write_ok", res["written"], True)
    eq("cache.config_untouched", open(cfg, encoding="utf-8").read(), cfg_before)
    eq("cache.now_available", avail("NVDA")["provenance"], "discovered")
    eq("cache.expires_on", avail("NVDA")["expires_on"], "2026-09-01")

    # TTL 邊界：第 30 天仍有效，第 31 天過期
    eq("cache.ttl_edge_valid", avail("NVDA", TODAY + dt.timedelta(days=30))["available"], True)
    eq("cache.ttl_expired", avail("NVDA", TODAY + dt.timedelta(days=31))["available"], False)
    eq("cache.ttl_expired_reason",
       avail("NVDA", TODAY + dt.timedelta(days=31))["discovery_reason"].startswith(
           "discovered_cohort_expired"), True)

    # 人工核准的 cohort 不得被 discovered 影子覆蓋
    blocked = peer_cohorts.record_discovered_cohort(
        "MU", [{"ticker": "FAKE"}], path=cache, config_path=cfg, today=TODAY)
    eq("cache.refuses_curated", blocked["written"], False)
    eq("cache.refuses_reason", blocked["reason"], "curated_cohort_exists")
    eq("cache.mu_still_curated", avail("MU")["provenance"], "curated")

    # 空候選不落檔；壞掉的 cache 檔不得偽裝成「還沒發現」
    eq("cache.empty_candidates", peer_cohorts.record_discovered_cohort(
        "AAPL", [], path=cache, config_path=cfg, today=TODAY)["written"], False)
    with open(cache, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    eq("cache.corrupt_reported", avail("NVDA")["discovery_reason"],
       "peer_discovery_cache_unreadable")

# ── 8. artifact 不可用 → rc=1（CLI 層）────────────────────────────────────
GATE_PATH = os.path.join(HERE, "valuation_reviewer_gate.py")


def run_cli(args):
    proc = subprocess.run([sys.executable, GATE_PATH, *args], capture_output=True, text=True)
    try:
        return proc.returncode, json.loads(proc.stdout)
    except Exception:
        return proc.returncode, {"_stdout": proc.stdout, "_stderr": proc.stderr}


with tempfile.TemporaryDirectory() as tmp:
    good = os.path.join(tmp, "good.json")
    with open(good, "w", encoding="utf-8") as fh:
        json.dump(QUIET, fh)
    rc, out = run_cli(["--from-quant", good])
    eq("cli.good_rc", rc, 0)
    eq("cli.good_schema", out.get("schema"), GATE_SCHEMA)
    eq("cli.shadow_only", out.get("shadow_only"), True)

    rc, out = run_cli(["--from-quant", os.path.join(tmp, "nope.json")])
    eq("cli.missing_rc", rc, 1)
    eq("cli.missing_error", "unreadable" in out.get("error", ""), True)

    wrong = os.path.join(tmp, "wrong.json")
    with open(wrong, "w", encoding="utf-8") as fh:
        json.dump({"schema": "other.v1"}, fh)
    rc, out = run_cli(["--from-quant", wrong])
    eq("cli.wrong_schema_rc", rc, 1)

    partial_art = os.path.join(tmp, "partial.json")
    stripped = copy.deepcopy(QUIET)
    stripped["quant_blocks"].pop("fair_value_range")
    with open(partial_art, "w", encoding="utf-8") as fh:
        json.dump(stripped, fh)
    rc, out = run_cli(["--from-quant", partial_art])
    eq("cli.missing_block_rc", rc, 1)
    eq("cli.missing_block_error", "fair_value_range" in out.get("error", ""), True)

    # artifact 無 ticker 且未給 --ticker → rc=1（不得猜）
    noticker = os.path.join(tmp, "noticker.json")
    anon = copy.deepcopy(QUIET)
    anon.pop("ticker")
    with open(noticker, "w", encoding="utf-8") as fh:
        json.dump(anon, fh)
    rc, out = run_cli(["--from-quant", noticker])
    eq("cli.no_ticker_rc", rc, 1)

    # 缺 leaf key → rc=1。只驗 block 存在會讓 `_num(...) or 0` 把缺欄讀成 0、
    # 判成低品質，shadow 統計被無聲灌水（review P3-3）。
    for block, key in (("fair_value_summary", "anchors_available"),
                       ("fair_value_summary", "confidence"),
                       ("fair_value_range", "agreement_grade"),
                       ("valuation_pack", "verdict_band")):
        path = os.path.join(tmp, f"missing_{block}_{key}.json")
        broken = copy.deepcopy(QUIET)
        broken["quant_blocks"][block].pop(key)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(broken, fh)
        rc, out = run_cli(["--from-quant", path])
        eq(f"cli.missing_leaf.{block}.{key}.rc", rc, 1)
        eq(f"cli.missing_leaf.{block}.{key}.msg", f"{block}.{key}" in out.get("error", ""), True)

    # 但 leaf 值為 null 是合法資料（無 eligible anchor 時 verdict_band 本來就 null）
    nullish = os.path.join(tmp, "nullish.json")
    nulled = copy.deepcopy(QUIET)
    nulled["quant_blocks"]["valuation_pack"]["verdict_band"] = None
    nulled["quant_blocks"]["valuation_pack"]["vs_current_pct"] = None
    nulled["quant_blocks"]["fair_value_summary"]["anchors_available"] = None
    with open(nullish, "w", encoding="utf-8") as fh:
        json.dump(nulled, fh)
    rc, out = run_cli(["--from-quant", nullish])
    eq("cli.null_leaf_ok_rc", rc, 0)
    # anchors_available=null → 算不出來 = 最低品質；verdict_band=null → 視為不在高估側。
    # （CLI 走真實 peer 解析，ZZTEST 無 cohort，所以 no_peer_cohort 也會在名單裡）
    eq("cli.null_leaf_low_quality", "low_quality_possible_buy" in out["triggers_fired"], True)

# in-process：load_quant_artifact 對非 dict payload 也要 raise
try:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        fh.write("[1,2,3]")
        listpath = fh.name
    load_quant_artifact(listpath)
    eq("load.list_payload_raises", "no_raise", "GateInputError")
except GateInputError:
    eq("load.list_payload_raises", True, True)
finally:
    os.unlink(listpath)

# evaluate_triggers 是純函式：同輸入同輸出（shadow 統計可重放）
q = copy.deepcopy(QUIET)
eq("pure.deterministic",
   evaluate_triggers(q, ticker="ZZTEST", transition=dict(NO_TRANSITION),
                     peer_availability=dict(PEERS_OK)),
   evaluate_triggers(q, ticker="ZZTEST", transition=dict(NO_TRANSITION),
                     peer_availability=dict(PEERS_OK)))

# ──────────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} regression(s):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ valuation reviewer gate + peer discovery cache fixtures pass")

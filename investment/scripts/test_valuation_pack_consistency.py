#!/usr/bin/env python3
"""Regression: canonical valuation projections must not drift across layers.

The fixture is derived from the newest real session entry because the validator
checks a full session-export shape. `investment/invest_logs/history.json` is
gitignored private trading data, so a clean checkout has nothing to derive from
and this test reports SKIP (rc=0) instead of a misleading failure — run it in a
working environment to get the real assertion.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from compute_price_framework import (  # noqa: E402
    build_valuation_pack,
    fair_value_summary_from_pack,
)
from apply_det_shadow import apply_to_trade  # noqa: E402


def run_validator(payload):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fp:
        json.dump(payload, fp)
        path = fp.name
    try:
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "validate_session_export.py"),
             "--history", path],
            capture_output=True, text=True,
        )
    finally:
        os.unlink(path)


history_path = os.path.join(ROOT, "investment", "invest_logs", "history.json")
if not os.path.exists(history_path):
    print("↷ SKIP valuation pack consistency: investment/invest_logs/history.json "
          "absent (gitignored private data) — no session entry to derive a fixture from")
    raise SystemExit(0)
history = json.load(open(history_path, encoding="utf-8"))
entry = json.loads(json.dumps(history[-1]))
trade = entry["trades_this_session"][0]
trade["analysis_price"] = 100.0
anchors = {
    "dcf_unlevered": 90.0,
    "comps_implied": 110.0,
    "analyst_pt_consensus": 105.0,
}
meta = {
    name: {"provenance": "fixture", "as_of": "2026-08-01",
           "correlation_key": name}
    for name in anchors
}
pack = build_valuation_pack(anchors, 100.0, anchor_meta=meta)
summary = fair_value_summary_from_pack(pack)
trade["valuation_pack"] = pack
trade["fair_value_summary"] = summary
trade["valuation_lane"].update({
    "weighted_fair_value": pack["weighted_fair_value"],
    "vs_current_pct": pack["vs_current_pct"],
    "score": pack["score"],
})
trade["multi_horizon_price_framework"]["long_term_ref"].update({
    "weighted_fair_value": pack["weighted_fair_value"],
    "verdict_band": pack["verdict_band"],
    "confidence": pack["confidence"],
})
# Version has to be threaded through exactly as Phase 5 Step 1.5 does it: the C1 lane
# contract is only written on V5.3+, and stamping one onto an older entry is itself a
# validator error (§2e). The fixture inherits whatever the newest real entry is stamped.
apply_to_trade(trade, entry_version=entry.get("session_export_version"))
if trade["det_shadow"]["valuation_score_det"] != pack["score"]:
    raise SystemExit("det_shadow must reuse canonical pack score")

good = run_validator([entry])
if good.returncode != 0:
    print(good.stderr)
    raise SystemExit("expected consistent pack fixture to pass")

bad_entry = json.loads(json.dumps(entry))
bad_entry["trades_this_session"][0]["fair_value_summary"]["weighted_fair_value"] += 1
bad = run_validator([bad_entry])
if bad.returncode == 0 or "projection drift" not in bad.stderr:
    print(bad.stdout, bad.stderr)
    raise SystemExit("expected projection drift fixture to fail")

print("✓ valuation pack consistency: pass fixture rc=0; drift fixture rc=1")

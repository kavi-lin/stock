#!/usr/bin/env python3
"""trade_plan_builder.py — V4.82.0 deterministic Phase 4 execution & risk engine (0 LLM arithmetic).

Computes the ENTIRE Phase 4 stack in one call, mirroring `decision_engine.py`'s role for
Phase 3:
  Step 1   — dual-track trade plan (entry / TP / SL from the Phase 2.4 MHP block)
  Step 2   — vol-adjusted position cap        (portfolio-risk-manager subprocess)
  Step 3   — tail risk fragility multiplier   (tail-risk-analyzer subprocess)
  Step 3.5 — FTD timeline gate (sector class × stage table + day-21 cyclical reject)
  Step 4   — the nine-stage sizing multiplication chain + final_stop_loss_pct
  V20-F1   — thesis-registry sector concentration: 同 sector ≥3 active CONFIRMED → ×0.5
  R/R gate — risk_reward_ratio recomputed from the built plan, must stay ≥ 2.0

Why a script: Phase 4 is an ordered multiplication chain over nine factors with two
lookup tables (FTD stage × sector class, fragility → multiplier), a conditional reject,
and a stop-loss reconciliation between two independently-derived prices. Protocol
discipline is「數字全走 script 禁手算」— this engine is the execution authority; the
protocol prose (`investment_protocol_v5_0.md` §PHASE 4) is the spec.

Single source of truth: the vol cap and the fragility label are IMPORTED from the two
skill scripts by running them — never re-implemented here. `--no-subprocess` accepts
pre-fetched blocks instead (used by the test suite and the replay harness).

Usage:
  python3 investment/scripts/trade_plan_builder.py --from-file /tmp/<T>_p4.json
  cat p4.json | python3 investment/scripts/trade_plan_builder.py
  python3 investment/scripts/trade_plan_builder.py --from-file p4.json --no-subprocess

Input JSON shape (qualitative fields — exit_conditions prose, trade_metadata — stay with
the PM and are NOT engine inputs):
{
  "ticker": "MU",
  "final_decision": "BUY",                  # from Phase 3 engine output
  "analysis_price": 455.07,
  "multi_horizon_price_framework": { ... }, # Phase 2.4 engine output, verbatim
  "technical": {"key_levels": {"support": 415.0, "resistance": 500.0},
                "rs_rating": 92, "distance_from_50ma_pct": 8.4},
  "sector": "Technology",                   # optional; resolved from ticker when absent
  "phase0": {"ftd": {"state": "FTD_CONFIRMED", "days_since_ftd": 7},
             "macro_backdrop_score": -1.0},
  "phase3": {                               # verbatim from decision_engine output
    "position_size_cap_pct": 100,           # Step 1.5 structural shift cap
    "polar_position_cap_pct": 100,          # Step 1.7 polarization cap
    "hot_zone_probe": false, "hot_zone_position_size_cap": null,
    "t4_resolution": "NONE",                # OVERRIDE_BURRY → burry ×0.5
    "binary_classification": "positive", "binary_event_within_48h": false
  },
  "mandatory_risk_flags": [],               # V4.82.0 — now persisted to the export
  "concentration": {                        # V20-F1 inputs (either form; see below)
    "active_same_sector_confirmed": 3
  },
  "risk_manager": {...}, "tail_risk": {...} # only with --no-subprocess
}

Output: single JSON object on stdout carrying `trade_plan` + `risk_audit` blocks the PM
copies verbatim into the Phase 5 export. rc=0 on success, rc=1 on unusable input.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ENGINE_VERSION = "1.0.0"
ENGINE_LABEL = f"trade_plan_builder.py v{ENGINE_VERSION} (V4.82.0)"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RISK_MANAGER = os.path.join(ROOT, "skills/portfolio-risk-manager/scripts/risk_manager.py")
TAIL_RISK = os.path.join(ROOT, "skills/tail-risk-analyzer/scripts/tail_risk.py")
THESES_DIR = os.path.join(ROOT, "investment/invest_logs/theses")

# Protocol §PHASE 4 Step 3.5 — sector classification.
CYCLICAL_SECTORS = {
    "technology", "industrials", "materials", "financials",
    "consumer_discretionary", "cons. disc.", "consumer discretionary",
    "energy", "communication", "communication services",
}
DEFENSIVE_SECTORS = {
    "utilities", "consumer_staples", "cons. staples", "consumer staples",
    "healthcare", "health care", "real_estate", "real estate",
}

# Step 3.5 stage table: days_since_ftd → (stage, cyclical_mult, defensive_mult,
# cyclical_stop_adj_pp, defensive_stop_adj_pp).
FTD_STAGES = (
    (1, 5, "prime", 1.00, 1.00, 0, 0),
    (6, 12, "standard", 0.90, 1.00, 0, 0),
    (13, 20, "late_cycle", 0.75, 0.95, -1, 0),
    (21, None, "exhausted", 0.50, 0.85, -2, 0),
)

# Step 3 fragility table: label → (score band upper bound, multiplier).
FRAGILITY_MULTIPLIER = {"ROBUST": 1.0, "MODERATE": 0.75, "FRAGILE": 0.5}

BASE_POSITION = 0.05          # Step 4 `base = vol_adjusted_limit OR 0.05`
MACRO_CAP_LIMIT = 0.03        # macro_backdrop_score < -3 → cap 3%
MACRO_CAP_TRIGGER = -3.0
STOP_LOSS_FLOOR_PCT = -10.0   # final_stop_loss_pct 上限 -10%
RR_MIN = 2.0
F1_SECTOR_THRESHOLD = 3       # 同 sector ≥3 active CONFIRMED → 第 4 個減半
F1_MULTIPLIER = 0.5


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _f(x: Any) -> float | None:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return float(x)


def _pos(x: Any) -> float | None:
    v = _f(x)
    return v if v is not None and v > 0 else None


def _i(x: Any) -> int | None:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return int(x)


def _r2(x: float | None) -> float | None:
    return None if x is None else round(x, 2)


# ---------------------------------------------------------------------------
# Step 1 — dual-track trade plan
# ---------------------------------------------------------------------------

def classify_sector(sector: str | None, ticker: str | None) -> dict:
    """cyclical / defensive per the Step 3.5 table.

    An unrecognised sector is NOT silently defaulted to defensive (the softer branch) —
    it falls back to cyclical, the conservative side, and says so in `basis`.
    """
    raw = (sector or "").strip()
    key = raw.lower().replace("-", "_")
    if key in DEFENSIVE_SECTORS:
        return {"sector": raw, "sector_class": "defensive", "basis": "protocol_table"}
    if key in CYCLICAL_SECTORS:
        return {"sector": raw, "sector_class": "cyclical", "basis": "protocol_table"}
    if not raw and ticker:
        # skills/_shared/company_context.py is the single source of truth for the
        # ticker → sector map (CLAUDE.md Shared Modules); never re-list tickers here.
        try:
            sys.path.insert(0, os.path.join(ROOT, "skills/_shared"))
            from company_context import TICKER_TO_SECTOR  # noqa: E402
        except Exception:  # noqa: BLE001
            TICKER_TO_SECTOR = {}
        resolved = TICKER_TO_SECTOR.get((ticker or "").upper())
        if resolved:
            out = classify_sector(resolved, None)
            out["basis"] = "ticker_to_sector"
            return out
    return {"sector": raw or None, "sector_class": "cyclical",
            "basis": "unknown_sector_conservative_default"}


def build_trade_plan(decision: str, mhp: dict, key_levels: dict, analysis_price: float | None,
                     pattern: str | None, time_horizon: str | None) -> dict:
    """Protocol §PHASE 4 Step 1 + the V5.1 provenance note.

    entry_aggressive   ← short_term_5d [band_point, band_upper_capped]  (突破續勢)
                         or 現價附近 when pattern == breakout
    entry_conservative ← short_term_5d [band_lower_capped, band_point]  (回檔承接)
    take_profit        ← mid_term_60d mid_target, capped at key_levels.resistance
    stop_loss          ← min(band_lower_capped, support) − buffer
    """
    notes: list[str] = []
    warnings: list[str] = []
    st = (mhp or {}).get("short_term_5d") or {}
    mid = (mhp or {}).get("mid_term_60d") or {}

    band = st.get("band_capped") or st.get("band")
    lower = point = upper = None
    if isinstance(band, (list, tuple)) and len(band) == 3:
        lower, point, upper = (_f(band[0]), _f(band[1]), _f(band[2]))
    else:
        warnings.append(
            "short_term_5d.band_capped 缺失或非三元組 — entry 區間無法由 MHP 導出；"
            "先補跑 Phase 2.4 compute_price_framework.py")

    support = _pos((key_levels or {}).get("support"))
    resistance = _pos((key_levels or {}).get("resistance"))
    cp = _pos(analysis_price)

    # ── entry tracks ─────────────────────────────────────────────────────
    entry_aggressive = entry_conservative = None
    if (pattern or "").lower() == "breakout" and cp is not None:
        # 突破型態：aggressive 貼現價（band_point 落在突破前的區間內，不追價會漏掉）
        entry_aggressive = [_r2(cp), _r2(upper if upper is not None and upper > cp else cp * 1.02)]
        notes.append("entry_aggressive 取現價附近（pattern=breakout）")
    elif point is not None and upper is not None:
        entry_aggressive = [_r2(point), _r2(upper)]
    if lower is not None and point is not None:
        entry_conservative = [_r2(lower), _r2(point)]

    # `band_capped` is [max(band_lower, support), band_point, min(band_upper, resistance)],
    # so a support above the point estimate (or a resistance below it) inverts a track.
    # Publishing [hi, lo] would read as a range nobody can fill; order it and say so.
    for name, rng in (("entry_aggressive", entry_aggressive),
                      ("entry_conservative", entry_conservative)):
        if rng and None not in rng and rng[0] > rng[1]:
            notes.append(f"{name} 由 MHP 導出時上下界顛倒（{rng[0]} > {rng[1]}）— key level "
                         "壓過 band_point，已排序；區間極窄請人工複核")
            rng.sort()

    # ── take profit ──────────────────────────────────────────────────────
    tp = _pos(mid.get("mid_target"))
    tp_capped_at_resistance = False
    if tp is not None and resistance is not None and tp > resistance:
        notes.append(f"take_profit 由 mid_target ${tp:.2f} cap 在 resistance ${resistance:.2f}"
                     f"（需突破 ${resistance:.2f} 才上看 ${tp:.2f}）")
        tp = resistance
        tp_capped_at_resistance = True
    if tp is None:
        warnings.append("mid_term_60d.mid_target 不可得 — take_profit null，R/R 無法計算")

    # ── stop loss ────────────────────────────────────────────────────────
    sl_candidates = [v for v in (lower, support) if v is not None]
    sl_base = min(sl_candidates) if sl_candidates else None
    if sl_base is None:
        warnings.append("band_lower_capped 與 key_levels.support 皆缺 — stop_loss null")
    return {
        "entry_aggressive": entry_aggressive,
        "entry_conservative": entry_conservative,
        "take_profit": _r2(tp),
        "stop_loss_pre_buffer": _r2(sl_base),
        "take_profit_capped_at_resistance": tp_capped_at_resistance,
        "time_horizon": time_horizon,
        "band_capped": [_r2(lower), _r2(point), _r2(upper)],
        "support": support,
        "resistance": resistance,
        "notes": notes,
        "warnings": warnings,
    }


def entry_candidates(plan: dict, decision: str) -> list[tuple[str, float]]:
    """Entry reference prices the R/R and the stop percentage are measured from, in the
    protocol's own remedy order.

    BUY 預設走 aggressive 軌（Step 1「兩軌二選一（預設 aggressive）」）；STAGED_ENTRY
    兩軌各半 → 取兩軌中點的加權中點。取「軌內中點」而非上緣，因為用上緣算 R/R 會系統性
    高估（entry 越高 → 分母越小）。

    Step 1 says an R/R below 2.0 is fixed by「收緊 entry 或降級 HOLD」— tightening first.
    So the fallbacks after the default are progressively lower entries; `run_phase4` walks
    this list and takes the first that clears the gate, recording which one it used.
    """
    agg, cons = plan.get("entry_aggressive"), plan.get("entry_conservative")
    mid_agg = (sum(agg) / 2) if isinstance(agg, list) and len(agg) == 2 and None not in agg else None
    mid_cons = (sum(cons) / 2) if isinstance(cons, list) and len(cons) == 2 and None not in cons else None
    low_cons = cons[0] if isinstance(cons, list) and len(cons) == 2 and cons[0] is not None else None

    ordered: list[tuple[str, float]] = []
    if decision == "STAGED_ENTRY" and mid_agg is not None and mid_cons is not None:
        ordered.append(("staged_blend", (mid_agg + mid_cons) / 2))
    elif mid_agg is not None:
        ordered.append(("aggressive_mid", mid_agg))
    if mid_cons is not None:
        ordered.append(("conservative_mid", mid_cons))
    if low_cons is not None:
        ordered.append(("conservative_low", low_cons))

    seen: set[float] = set()
    out: list[tuple[str, float]] = []
    for label, price in ordered:
        if price in seen:
            continue
        seen.add(price)
        out.append((label, price))
    return out


def reconcile_stop_loss(pre_buffer: float | None, entry_ref: float | None,
                        buffer_pct: float, final_stop_loss_pct: float | None) -> dict:
    """Step 1 SL vs Step 4 `final_stop_loss_pct` — take the more conservative (higher) price.

    Both are stops for the same position, derived independently: the Step 1 price comes
    off the technical structure, the Step 4 percentage off the FTD timeline. The protocol
    says 取較保守（較高）者, i.e. whichever exits earlier.
    """
    structural = None
    if pre_buffer is not None:
        structural = pre_buffer * (1 - buffer_pct / 100.0)
    pct_based = None
    if entry_ref is not None and final_stop_loss_pct is not None:
        pct_based = entry_ref * (1 + final_stop_loss_pct / 100.0)

    candidates = {"structural": structural, "pct_based": pct_based}
    live = {k: v for k, v in candidates.items() if v is not None}
    if not live:
        return {"stop_loss": None, "source": None, "structural": None, "pct_based": None}
    source = max(live, key=lambda k: live[k])
    return {"stop_loss": _r2(live[source]), "source": source,
            "structural": _r2(structural), "pct_based": _r2(pct_based)}


def risk_reward(entry_ref: float | None, tp: float | None, sl: float | None) -> float | None:
    if entry_ref is None or tp is None or sl is None:
        return None
    risk = entry_ref - sl
    if risk <= 0:
        return None
    return round((tp - entry_ref) / risk, 2)


# ---------------------------------------------------------------------------
# Steps 2 / 3 — external skill scripts
# ---------------------------------------------------------------------------

def _run_skill(script: str, ticker: str, timeout: int) -> dict:
    """Run a skill script and return its parsed JSON, or an `error` dict.

    Never raises: Phase 4 degrades to RULE_BASED sizing when the vol cap is unavailable,
    and to the conservative fragility branch when tail risk is. Both degradations are
    recorded in the audit rather than silently absorbed.
    """
    if not os.path.exists(script):
        return {"error": f"script not found: {script}"}
    try:
        proc = subprocess.run(
            [sys.executable, script, ticker, "--json-only"],
            capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return {"error": f"timeout after {timeout}s"}
    except Exception as e:  # noqa: BLE001 — any launch failure is a degradation, not a crash
        return {"error": f"subprocess failed: {e}"}
    out = (proc.stdout or "").strip()
    if not out:
        return {"error": f"no stdout (rc={proc.returncode}): {(proc.stderr or '')[:200]}"}
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError as e:
        return {"error": f"unparseable JSON: {e}"}
    if not isinstance(parsed, dict):
        return {"error": "skill output must be a JSON object"}
    return parsed


def compute_step2(rm: dict) -> dict:
    """`final_position_cap_pct` → `vol_adjusted_limit_pct`. Absent → RULE_BASED 5%."""
    cap_pct = _f(rm.get("final_position_cap_pct")) if isinstance(rm, dict) else None
    if cap_pct is None or rm.get("error"):
        return {
            "vol_adjusted_limit_pct": None,
            "position_size_method": "RULE_BASED",
            "base": BASE_POSITION,
            "note": f"risk_manager 不可用（{(rm or {}).get('error', 'final_position_cap_pct 缺失')}）"
                    f" → base = {BASE_POSITION} (RULE_BASED)",
        }
    return {
        "vol_adjusted_limit_pct": round(cap_pct, 2),
        "position_size_method": "VOL_ADJUSTED",
        "base": cap_pct / 100.0,
        "note": f"vol_adjusted_limit {cap_pct}% → base {cap_pct / 100.0:.4f}",
    }


def compute_step3(tr: dict) -> dict:
    """fragility_label → position_multiplier. The label is authoritative; the score is
    cross-checked against the band it claims, because the two ship from the same script
    and a disagreement means the input was hand-edited."""
    label = tr.get("fragility_label") if isinstance(tr, dict) else None
    score = _f((tr or {}).get("tail_risk_score"))
    warnings: list[str] = []
    if label not in FRAGILITY_MULTIPLIER:
        # Unavailable tail risk is NOT treated as ROBUST — that would hand the largest
        # multiplier to the case we know least about.
        return {
            "fragility_label": "MODERATE", "tail_risk_score": score,
            "fragility_multiplier": FRAGILITY_MULTIPLIER["MODERATE"],
            "degraded": True,
            "warnings": [f"tail_risk 不可用（{(tr or {}).get('error', f'fragility_label={label!r}')}）"
                         " → 保守取 MODERATE ×0.75，不得當 ROBUST"],
        }
    if score is not None:
        expected = "ROBUST" if score < 30 else ("MODERATE" if score < 60 else "FRAGILE")
        if expected != label:
            warnings.append(
                f"tail_risk_score {score} 落在 {expected} 帶但 fragility_label={label} — "
                "以 label 為準，輸入疑似手改")
    return {"fragility_label": label, "tail_risk_score": score,
            "fragility_multiplier": FRAGILITY_MULTIPLIER[label],
            "degraded": False, "warnings": warnings}


# ---------------------------------------------------------------------------
# Step 3.5 — FTD timeline gate
# ---------------------------------------------------------------------------

def compute_ftd_gate(ftd: dict, sector_class: str, technical: dict) -> dict:
    """Protocol §PHASE 4 Step 3.5.

    適用前提: state == FTD_CONFIRMED AND days_since_ftd != null. Otherwise the gate is
    inert (`applied=false`, multiplier 1.0) — recorded, never silently skipped.

    Day 21+ reject is cyclical-only: RS_rating < 90 OR distance_from_50ma > 15% → REJECT.
    """
    state = (ftd or {}).get("state") or (ftd or {}).get("ftd_status")
    days = _i((ftd or {}).get("days_since_ftd"))
    if days is None:
        days = _i((ftd or {}).get("ftd_days_since"))

    inert = {
        "applied": False, "days_since_ftd": days, "stage": "n/a",
        "sector_class": sector_class, "multiplier": 1.0,
        "stop_loss_adjustment_pp": 0, "rejection_triggered": False,
        "rejection_reason": None, "notes": [],
    }
    if state != "FTD_CONFIRMED":
        inert["notes"].append(f"ftd.state={state!r} != FTD_CONFIRMED → gate 不適用")
        return inert
    if days is None:
        inert["notes"].append("days_since_ftd 為 null → gate 不適用（protocol 適用前提）")
        return inert
    if days < 1:
        inert["notes"].append(f"days_since_ftd={days} 落在 stage 表 (1+) 之外 → gate 不適用")
        return inert

    stage = mult = stop_adj = None
    for lo, hi, name, cyc_m, def_m, cyc_s, def_s in FTD_STAGES:
        if days >= lo and (hi is None or days <= hi):
            stage = name
            mult = cyc_m if sector_class == "cyclical" else def_m
            stop_adj = cyc_s if sector_class == "cyclical" else def_s
            break

    notes = [f"day {days} → {stage} × {mult} ({sector_class})"]
    rejection = False
    reason = None
    if stage == "exhausted" and sector_class == "cyclical":
        rs = _f(technical.get("rs_rating"))
        dist = _f(technical.get("distance_from_50ma_pct"))
        triggers = []
        if rs is not None and rs < 90:
            triggers.append(f"RS_rating {rs} < 90")
        if dist is not None and dist > 15:
            triggers.append(f"distance_from_50ma {dist}% > 15%")
        if triggers:
            rejection = True
            reason = "; ".join(triggers)
            notes.append(f"day 21+ cyclical reject: {reason}")
        elif rs is None and dist is None:
            notes.append("day 21+ cyclical：RS_rating / distance_from_50ma 皆缺 — "
                         "reject 條件無法判定，維持 ×0.50 不 reject（輸入缺料，非通過）")

    return {"applied": True, "days_since_ftd": days, "stage": stage,
            "sector_class": sector_class, "multiplier": mult,
            "stop_loss_adjustment_pp": stop_adj, "rejection_triggered": rejection,
            "rejection_reason": reason, "notes": notes}


# ---------------------------------------------------------------------------
# V20-F1 — thesis registry sector concentration
# ---------------------------------------------------------------------------

def compute_concentration(conc: dict | None, sector: str | None,
                          theses_dir: str = THESES_DIR, ticker: str | None = None) -> dict:
    """同 sector ≥3 active CONFIRMED → 第 4 個 ×0.5.

    Three input forms, most explicit first:
      1. `active_same_sector_confirmed: <int>` — a count the caller already resolved
      2. `active_theses: [{ticker, sector, structural_shift_tier, status}]` — counted here
      3. absent → the registry at `theses_dir` is consulted

    The candidate's OWN open thesis is excluded from the count (V4.86.0). The rule sizes
    「第 4 個」— the 4th name in a sector — so it must count the *other* holdings. Re-running
    `分析` on something already held would otherwise count that position as one of the
    three and halve at the 3rd name. Form 1 is taken at face value: the caller resolved
    the count and owns that decision.

    When none of the three yields a number the multiplier stays 1.0 and the status says
    exactly why. An unavailable registry is never reported as "0 positions" — that would
    read as a verified all-clear.
    """
    conc = conc or {}
    sec = (conc.get("sector") or sector or "").strip().lower()
    self_ticker = (conc.get("ticker") or ticker or "").strip().upper()

    explicit = _i(conc.get("active_same_sector_confirmed"))
    if explicit is not None:
        count, source = explicit, "explicit_count"
    elif isinstance(conc.get("active_theses"), list):
        count = sum(
            1 for t in conc["active_theses"]
            if isinstance(t, dict)
            and (t.get("sector") or "").strip().lower() == sec
            and (t.get("structural_shift_tier") or t.get("tier")) == "CONFIRMED"
            and (t.get("status") or "ACTIVE").upper() in ("ACTIVE", "ENTRY_READY")
            and (not self_ticker
                 or (t.get("ticker") or "").strip().upper() != self_ticker)
        )
        source = "active_theses_input"
    else:
        count, source = _count_registry_confirmed(theses_dir, sec, self_ticker)

    if count is None:
        return {"applied": False, "multiplier": 1.0, "sector": sector,
                "active_same_sector_confirmed": None, "source": source,
                "note": f"concentration 輸入不可得（{source}）— F1 未評估，不當作 0 部位"}
    if not sec:
        return {"applied": False, "multiplier": 1.0, "sector": sector,
                "active_same_sector_confirmed": count, "source": source,
                "note": "sector 未知 — 同 sector 計數無意義，F1 略過"}
    applied = count >= F1_SECTOR_THRESHOLD
    return {
        "applied": applied,
        "multiplier": F1_MULTIPLIER if applied else 1.0,
        "sector": sector,
        "active_same_sector_confirmed": count,
        "source": source,
        "note": (f"同 sector active CONFIRMED {count} ≥ {F1_SECTOR_THRESHOLD} → ×{F1_MULTIPLIER}"
                 if applied else
                 f"同 sector active CONFIRMED {count} < {F1_SECTOR_THRESHOLD} → 不減倉"),
    }


def _count_registry_confirmed(theses_dir: str, sector_lower: str, self_ticker: str = ""):
    """Read the trader-memory-core registry index. Returns (count|None, source).

    `self_ticker` is excluded — see `compute_concentration` on why the candidate must
    not count itself toward its own concentration limit.
    """
    idx_path = os.path.join(theses_dir, "_index.json")
    if not os.path.exists(idx_path):
        return None, "registry_unavailable"
    try:
        with open(idx_path, encoding="utf-8") as fp:
            idx = json.load(fp)
    except Exception as e:  # noqa: BLE001
        return None, f"registry_unreadable: {e}"
    entries = (idx or {}).get("theses") or {}
    if not isinstance(entries, dict):
        return None, "registry_malformed"
    # The lightweight index projects neither sector nor structural_shift tier, so the
    # full record has to be opened for each active thesis. Absent yaml support the count
    # is unknown, not zero.
    try:
        import yaml  # noqa: E402
    except Exception:
        return None, "registry_needs_pyyaml"
    count = 0
    for tid, entry in entries.items():
        if (entry or {}).get("status", "").upper() not in ("ACTIVE", "ENTRY_READY"):
            continue
        if self_ticker and (entry or {}).get("ticker", "").strip().upper() == self_ticker:
            continue
        path = os.path.join(theses_dir, f"{tid}.yaml")
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as fp:
                rec = yaml.safe_load(fp) or {}
        except Exception:  # noqa: BLE001
            continue
        shift = rec.get("structural_shift") or {}
        tier = shift.get("tier") if isinstance(shift, dict) else None
        rec_sector = (rec.get("sector") or (rec.get("origin") or {}).get("sector") or "")
        if tier == "CONFIRMED" and str(rec_sector).strip().lower() == sector_lower:
            count += 1
    return count, "registry_index"


# ---------------------------------------------------------------------------
# Step 4 — the nine-stage sizing chain
# ---------------------------------------------------------------------------

def compute_sizing_chain(base: float, fragility_mult: float, macro_backdrop: float | None,
                         binary_class: str | None, binary_within_48h: bool,
                         burry_override: bool, ftd_mult: float,
                         position_size_cap_pct: float, polar_position_cap_pct: float,
                         f1_mult: float, decision: str,
                         binary_negative_mult: float = 0.5) -> dict:
    """Protocol §PHASE 4 Step 4, in order. Every stage emits its own trace line so the
    validator can re-derive the chain from the export without re-running this engine.

    Stage order (V4.82.0 inserts F1 immediately after ftd_adj — it is a sizing-side
    concentration brake of the same kind, and placing it before the two Phase 3 caps
    keeps those caps as the last word on the position, matching V2.18/V2.19 intent):
      base → tail_adj → macro_cap → binary_adj → burry_override_adj → ftd_adj
           → f1_adj → shift_adj → polar_adj → final (STAGED halving)
    """
    steps: list[str] = []

    tail_adj = base * fragility_mult
    steps.append(f"base {base:.6f} × fragility {fragility_mult} = {tail_adj:.6f}")

    mb = _f(macro_backdrop)
    if mb is not None and mb < MACRO_CAP_TRIGGER:
        macro_cap = min(tail_adj, MACRO_CAP_LIMIT)
        steps.append(f"macro_backdrop {mb} < {MACRO_CAP_TRIGGER} → "
                     f"min({tail_adj:.6f}, {MACRO_CAP_LIMIT}) = {macro_cap:.6f}")
    else:
        macro_cap = tail_adj
        steps.append(f"macro_backdrop {mb} ≥ {MACRO_CAP_TRIGGER} → macro cap 不觸發 "
                     f"= {macro_cap:.6f}")

    if binary_class in ("unknown", "negative") and binary_within_48h:
        bmult = binary_negative_mult
        binary_adj = macro_cap * bmult
        steps.append(f"binary {binary_class} + event <48h → × {bmult} = {binary_adj:.6f}")
    else:
        bmult = 1.0
        binary_adj = macro_cap
        steps.append(f"binary {binary_class} (event<48h={binary_within_48h}) → × 1.0 "
                     f"= {binary_adj:.6f}")

    bo_mult = 0.5 if burry_override else 1.0
    burry_adj = binary_adj * bo_mult
    steps.append(f"burry_override {burry_override} → × {bo_mult} = {burry_adj:.6f}")

    ftd_adj = burry_adj * ftd_mult
    steps.append(f"ftd_timeline × {ftd_mult} = {ftd_adj:.6f}")

    f1_adj = ftd_adj * f1_mult
    steps.append(f"V20-F1 sector concentration × {f1_mult} = {f1_adj:.6f}")

    shift_adj = f1_adj * (position_size_cap_pct / 100.0)
    steps.append(f"structural_shift cap {position_size_cap_pct}% → × "
                 f"{position_size_cap_pct / 100.0} = {shift_adj:.6f}")

    polar_adj = shift_adj * (polar_position_cap_pct / 100.0)
    steps.append(f"polarization cap {polar_position_cap_pct}% → × "
                 f"{polar_position_cap_pct / 100.0} = {polar_adj:.6f}")

    if decision == "STAGED_ENTRY":
        final = polar_adj * 0.5
        steps.append(f"STAGED_ENTRY → × 0.5 = {final:.6f}")
    else:
        final = polar_adj
        steps.append(f"decision {decision} → 不折半 = {final:.6f}")

    return {
        "base": round(base, 6),
        "tail_adj": round(tail_adj, 6),
        "macro_cap": round(macro_cap, 6),
        "binary_adj": round(binary_adj, 6),
        "binary_multiplier": bmult,
        "burry_override_adj": round(burry_adj, 6),
        "burry_override_multiplier": bo_mult,
        "ftd_adj": round(ftd_adj, 6),
        "f1_adj": round(f1_adj, 6),
        "f1_multiplier": f1_mult,
        "shift_adj": round(shift_adj, 6),
        "polar_adj": round(polar_adj, 6),
        "final_position_size": round(final, 6),
        "steps": steps,
    }


def compute_final_stop_pct(entry_ref: float | None, sl_pre_buffer: float | None,
                           buffer_pct: float, ftd_stop_adj_pp: int) -> dict:
    """`final_stop_loss_pct = base_stop_pct + ftd_timeline_stop_adjustment`，上限 -10%.

    `base_stop_pct` is the structural stop expressed against the entry reference — the
    protocol never defines it independently, and deriving it from the Step 1 price is the
    only reading that keeps Step 1 and Step 4 talking about the same position.
    """
    if entry_ref is None or sl_pre_buffer is None:
        return {"base_stop_pct": None, "ftd_stop_adjustment_pp": ftd_stop_adj_pp,
                "final_stop_loss_pct": None, "floored": False,
                "note": "entry_ref 或 structural stop 缺失 → final_stop_loss_pct 無法導出"}
    structural = sl_pre_buffer * (1 - buffer_pct / 100.0)
    base_stop_pct = (structural - entry_ref) / entry_ref * 100.0
    raw = base_stop_pct + ftd_stop_adj_pp
    floored = raw < STOP_LOSS_FLOOR_PCT
    final = STOP_LOSS_FLOOR_PCT if floored else raw
    return {
        "base_stop_pct": round(base_stop_pct, 2),
        "ftd_stop_adjustment_pp": ftd_stop_adj_pp,
        "final_stop_loss_pct": round(final, 2),
        "floored": floored,
        "note": (f"base {base_stop_pct:.2f}% + FTD {ftd_stop_adj_pp}pp = {raw:.2f}%"
                 + (f" → floor {STOP_LOSS_FLOOR_PCT}%" if floored else "")),
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_phase4(inp: dict, *, use_subprocess: bool = True, timeout: int = 120) -> dict:
    warnings: list[str] = []
    ticker = inp.get("ticker")
    if not ticker:
        raise ValueError("ticker is required")
    decision = inp.get("final_decision")
    if decision not in ("BUY", "STAGED_ENTRY", "HOLD", "STAGED_EXIT", "SELL"):
        raise ValueError(
            f"final_decision={decision!r} — Phase 4 只吃 Phase 3 engine 的 final_decision "
            "(BUY/STAGED_ENTRY/HOLD/STAGED_EXIT/SELL)")

    phase3 = inp.get("phase3") or {}
    technical = inp.get("technical") or {}
    key_levels = technical.get("key_levels") or {}
    mhp = inp.get("multi_horizon_price_framework") or {}
    analysis_price = _f(inp.get("analysis_price"))
    buffer_pct = _f(inp.get("stop_buffer_pct"))
    buffer_pct = 1.0 if buffer_pct is None else buffer_pct

    sector_info = classify_sector(inp.get("sector"), ticker)
    if sector_info["basis"] == "unknown_sector_conservative_default":
        warnings.append(
            f"sector={inp.get('sector')!r} 不在 protocol 分類表 → 取 cyclical（保守側）；"
            "FTD 乘數與停損調整按 cyclical 走")

    # ── Step 1 ───────────────────────────────────────────────────────────
    plan = build_trade_plan(decision, mhp, key_levels, analysis_price,
                            technical.get("pattern"), inp.get("time_horizon"))
    warnings.extend(plan.pop("warnings"))

    # ── Step 2 ───────────────────────────────────────────────────────────
    rm = inp.get("risk_manager")
    if use_subprocess and not isinstance(rm, dict):
        rm = _run_skill(RISK_MANAGER, ticker, timeout)
    s2 = compute_step2(rm or {})
    if s2["position_size_method"] == "RULE_BASED":
        warnings.append(s2["note"])

    # ── Step 3 ───────────────────────────────────────────────────────────
    tr = inp.get("tail_risk")
    if use_subprocess and not isinstance(tr, dict):
        tr = _run_skill(TAIL_RISK, ticker, timeout)
    s3 = compute_step3(tr or {})
    warnings.extend(s3["warnings"])

    # ── Step 3.5 ─────────────────────────────────────────────────────────
    ftd = (inp.get("phase0") or {}).get("ftd") or {}
    gate = compute_ftd_gate(ftd, sector_info["sector_class"], technical)

    # ── V20-F1 ───────────────────────────────────────────────────────────
    f1 = compute_concentration(inp.get("concentration"), sector_info["sector"],
                               inp.get("theses_dir") or THESES_DIR, ticker)
    if not f1["applied"] and f1["active_same_sector_confirmed"] is None:
        warnings.append(f1["note"])

    # ── Step 4 ───────────────────────────────────────────────────────────
    macro_backdrop = (inp.get("phase0") or {}).get("macro_backdrop_score")
    binary_class = phase3.get("binary_classification")
    binary_48h = phase3.get("binary_event_within_48h") is True
    # Protocol: unknown → 減倉 (0.5-0.7 band); negative (已知壞消息) → 減 50%.
    # The band's conservative end is used for both so the number is reproducible.
    burry_override = (phase3.get("t4_resolution") == "OVERRIDE_BURRY"
                      or phase3.get("burry_override_active") is True)

    chain = compute_sizing_chain(
        base=s2["base"],
        fragility_mult=s3["fragility_multiplier"],
        macro_backdrop=macro_backdrop,
        binary_class=binary_class,
        binary_within_48h=binary_48h,
        burry_override=burry_override,
        ftd_mult=gate["multiplier"],
        position_size_cap_pct=_f(phase3.get("position_size_cap_pct")) or 100.0,
        polar_position_cap_pct=_f(phase3.get("polar_position_cap_pct")) or 100.0,
        f1_mult=f1["multiplier"],
        decision=decision,
    )
    position_size = chain["final_position_size"]

    # ── entry / stop / R/R solve ─────────────────────────────────────────
    # Each candidate entry moves the percentage-based stop with it, so the stop and the
    # ratio are recomputed per candidate rather than solved once against the default.
    candidates = entry_candidates(plan, decision) or [("unavailable", None)]
    solved = []
    for label, price in candidates:
        c_stop = compute_final_stop_pct(price, plan["stop_loss_pre_buffer"], buffer_pct,
                                        gate["stop_loss_adjustment_pp"])
        c_sl = reconcile_stop_loss(plan["stop_loss_pre_buffer"], price, buffer_pct,
                                   c_stop["final_stop_loss_pct"])
        c_rr = risk_reward(price, plan["take_profit"], c_sl["stop_loss"])
        solved.append({"track": label, "entry_ref": price, "stop": c_stop, "sl": c_sl,
                       "rr": c_rr})
        if c_rr is not None and c_rr >= RR_MIN:
            break

    chosen = next((s for s in solved if s["rr"] is not None and s["rr"] >= RR_MIN), solved[0])
    entry_track, entry_ref = chosen["track"], chosen["entry_ref"]
    stop, sl, rr = chosen["stop"], chosen["sl"], chosen["rr"]
    rr_attempts = [f"{s['track']} @ "
                   f"{'n/a' if s['entry_ref'] is None else round(s['entry_ref'], 2)} → R/R {s['rr']}"
                   for s in solved]
    if entry_track != candidates[0][0]:
        warnings.append(
            f"預設 entry 軌 R/R < {RR_MIN} → 依 Step 1「收緊 entry」改用 {entry_track}"
            f"（嘗試序：{' | '.join(rr_attempts)}）")

    # ── Rec 11 probe cap — Phase 3 already sized the probe; Phase 4 must not exceed it ──
    hot_zone_cap = _f(phase3.get("hot_zone_position_size_cap"))
    hot_zone_capped = False
    if phase3.get("hot_zone_probe") is True and hot_zone_cap is not None \
            and position_size > hot_zone_cap:
        chain["steps"].append(
            f"Rec 11 probe cap: {position_size:.6f} → {hot_zone_cap} (tier 上限)")
        position_size = hot_zone_cap
        hot_zone_capped = True

    # ── approval ─────────────────────────────────────────────────────────
    approval = "APPROVED"
    rejection_reasons: list[str] = []
    if gate["rejection_triggered"]:
        rejection_reasons.append(f"FTD day-21 cyclical reject ({gate['rejection_reason']})")
    if decision in ("BUY", "STAGED_ENTRY"):
        if rr is None:
            rejection_reasons.append(
                "risk_reward_ratio 無法計算（take_profit / stop_loss / entry 任一缺失）")
        elif rr < RR_MIN:
            rejection_reasons.append(f"risk_reward_ratio {rr} < {RR_MIN}")
    if rejection_reasons:
        approval = "REJECTED"

    # A rejected plan carries no position. Emitting the computed size next to
    # approval=REJECTED invites the PM to copy the number anyway.
    downgraded_decision = decision
    if approval == "REJECTED" and decision in ("BUY", "STAGED_ENTRY"):
        downgraded_decision = "HOLD"
        position_size = 0.0

    if decision not in ("BUY", "STAGED_ENTRY"):
        # HOLD / exit decisions size nothing; the chain is still reported so the audit
        # shows what the position WOULD have been.
        position_size = 0.0

    staged_split = ({"aggressive_pct": 50.0, "conservative_pct": 50.0}
                    if downgraded_decision == "STAGED_ENTRY" else None)

    risk_level = "HIGH" if s3["fragility_label"] == "FRAGILE" else (
        "MEDIUM" if s3["fragility_label"] == "MODERATE" else "LOW")

    exit_bits = []
    if plan["take_profit_capped_at_resistance"] and plan["resistance"] is not None:
        mt = _pos((mhp.get("mid_term_60d") or {}).get("mid_target"))
        exit_bits.append(f"需突破 ${plan['resistance']:g} 才上看 ${mt:g}" if mt else
                         f"需突破 ${plan['resistance']:g}")
    if sl["stop_loss"] is not None:
        exit_bits.append(f"跌破 ${sl['stop_loss']:g}（{sl['source']} stop）觸發退場")

    trade_plan = {
        "entry_aggressive": plan["entry_aggressive"],
        "entry_conservative": plan["entry_conservative"],
        "take_profit": plan["take_profit"],
        "stop_loss": sl["stop_loss"],
        "risk_reward_ratio": rr,
        "time_horizon": inp.get("time_horizon"),
        "exit_conditions": "；".join(exit_bits) or None,
        "entry_reference_price": _r2(entry_ref),
        "entry_track_used": entry_track,
        "rr_solve_trace": rr_attempts,
        "provenance_notes": plan["notes"],
    }

    risk_audit = {
        "risk_level": risk_level,
        # The decision the sizing chain was computed against. Phase 4.6 runs AFTER this
        # and may rewrite `final_decision` (BUY → HOLD / STAGED_ENTRY under a valuation
        # cap), at which point the exported decision no longer explains the chain — in
        # particular whether the STAGED_ENTRY halving applies. Recording it here lets
        # validator §14 re-derive the chain without guessing.
        "sized_for_decision": decision,
        "vol_adjusted_limit_pct": s2["vol_adjusted_limit_pct"],
        "position_size_method": s2["position_size_method"],
        "tail_risk": {
            "fragility_label": s3["fragility_label"],
            "tail_risk_score": s3["tail_risk_score"],
            "fragility_adjustment": f"× {s3['fragility_multiplier']}",
            "degraded": s3["degraded"],
        },
        "binary_classification": binary_class,
        "binary_event_within_48h": binary_48h,
        "burry_override_active": burry_override,
        "burry_override_multiplier": chain["burry_override_multiplier"],
        "ftd_timeline_gate": {
            "applied": gate["applied"],
            "days_since_ftd": gate["days_since_ftd"],
            "stage": gate["stage"],
            "sector_class": gate["sector_class"],
            "multiplier": gate["multiplier"],
            "stop_loss_adjustment_pp": gate["stop_loss_adjustment_pp"],
            "rejection_triggered": gate["rejection_triggered"],
        },
        "sector_concentration_f1": f1,
        "sizing_chain": chain,
        "position_size_pct": round(position_size, 6),
        "final_stop_loss_pct": stop["final_stop_loss_pct"],
        "stop_loss_derivation": {
            "base_stop_pct": stop["base_stop_pct"],
            "ftd_stop_adjustment_pp": stop["ftd_stop_adjustment_pp"],
            "floored_at_limit": stop["floored"],
            "structural_stop_price": sl["structural"],
            "pct_based_stop_price": sl["pct_based"],
            "selected": sl["source"],
            "note": stop["note"],
        },
        "staged_entry_split": staged_split,
        "hot_zone_probe_capped": hot_zone_capped,
        "approval": approval,
        "rejection_reason": "; ".join(rejection_reasons) or None,
    }

    return {
        "phase": 4,
        "engine": ENGINE_LABEL,
        "trade_plan_builder_version": ENGINE_VERSION,
        "ticker": ticker,
        "final_decision_in": decision,
        "final_decision": downgraded_decision,
        "mandatory_risk_flags": list(inp.get("mandatory_risk_flags") or []),
        "trade_plan": trade_plan,
        "risk_audit": risk_audit,
        "sector_resolution": sector_info,
        "ftd_notes": gate["notes"],
        "warnings": warnings,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic Phase 4 execution & risk engine")
    ap.add_argument("--from-file", help="input JSON path (default: stdin)")
    ap.add_argument("--no-subprocess", action="store_true",
                    help="never shell out to risk_manager/tail_risk; use the blocks in the input")
    ap.add_argument("--timeout", type=int, default=120,
                    help="per-skill subprocess timeout in seconds (default 120)")
    args = ap.parse_args(argv)

    if args.from_file:
        with open(args.from_file, encoding="utf-8") as fp:
            raw = fp.read()
    else:
        raw = sys.stdin.read()
    try:
        inp = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"unparseable input: {e}"}))
        return 1
    if not isinstance(inp, dict):
        print(json.dumps({"error": "input must be a JSON object"}))
        return 1

    try:
        out = run_phase4(inp, use_subprocess=not args.no_subprocess, timeout=args.timeout)
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        return 1

    print(json.dumps(out, ensure_ascii=False, indent=2))
    for w in out.get("warnings") or []:
        print(f"[trade_plan_builder] ⚠ {w}", file=sys.stderr)
    if out["risk_audit"]["approval"] == "REJECTED":
        print(f"[trade_plan_builder] ‼ REJECTED: {out['risk_audit']['rejection_reason']}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

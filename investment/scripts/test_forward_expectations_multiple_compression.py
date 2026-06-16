#!/usr/bin/env python3
"""Golden fixtures for growth-tier multiple compression (EXP-3.4)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forward_expectations_multiple_compression as mc  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want, tol=None):
    global PASS, FAIL
    ok = (got is not None and abs(got - want) <= tol) if tol is not None else (got == want)
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print(f"  x {label}: got {got!r}, want {want!r}")


def band(p25, p50, p75):
    return {"usable": True, "p25": p25, "p50": p50, "p75": p75, "n": 6, "dispersion_ratio": round(p75 / p25, 3)}


# ── tier mapping ───────────────────────────────────────────────────────────────
check("tier hypergrowth", mc._tier(0.40)[0], "hypergrowth")
check("tier growth", mc._tier(0.18)[0], "growth")
check("tier moderate", mc._tier(0.10)[0], "moderate")
check("tier slowing", mc._tier(0.05)[0], "slowing")
check("tier mature", mc._tier(0.016)[0], "mature")
check("tier negative -> mature", mc._tier(-0.1)[0], "mature")

# ── NVDA-like: mature tier, P/E ceiling binds proportionally ───────────────────
nvda = mc.compress_band(band(42.88, 57.25, 72.24), 0.016, "pe")
check("nvda tier mature", nvda["growth_tier"], "mature")
check("nvda compressed", nvda["compressed"], True)
check("nvda pe ceiling applied", nvda["pe_ceiling_applied"], True)
check("nvda p50 capped to 22", nvda["p50"], 22.0, tol=0.01)
check("nvda dispersion preserved (p25<p50<p75)", nvda["p25"] < nvda["p50"] < nvda["p75"], True)
check("nvda historical kept", nvda["historical_band"]["p50"], 57.25, tol=0.01)

# ── ARM-like: hypergrowth factor 1.0 but absurd P/E -> ceiling 55, band scaled ──
arm = mc.compress_band(band(130, 151, 180), 0.40, "pe")
check("arm tier hypergrowth", arm["growth_tier"], "hypergrowth")
check("arm p50 capped to 55", arm["p50"], 55.0, tol=0.01)
check("arm ceiling applied", arm["pe_ceiling_applied"], True)
check("arm dispersion preserved", arm["p25"] < arm["p50"] < arm["p75"], True)
check("arm p25 scaled ~47.3", arm["p25"], 55.0 * 130 / 151, tol=0.1)

# ── moderate tier, factor only, no ceiling bind ────────────────────────────────
mod = mc.compress_band(band(20, 25, 30), 0.10, "pe")
check("mod compressed by factor 0.66", mod["p50"], 25 * 0.66, tol=0.01)
check("mod ceiling not applied (16.5<35)", mod["pe_ceiling_applied"], False)

# ── P/S metric: factor only, NO P/E ceiling ────────────────────────────────────
ps = mc.compress_band(band(6, 8, 10), 0.05, "ps")
check("ps slowing factor 0.52", ps["p50"], 8 * 0.52, tol=0.01)
check("ps no pe ceiling field active", ps.get("pe_absolute_ceiling"), None)

# ── no growth signal -> passthrough, not compressed ────────────────────────────
none_g = mc.compress_band(band(20, 25, 30), None, "pe")
check("no growth -> not compressed", none_g["compressed"], False)
check("no growth reason", none_g["compression_reason"], "no_forward_growth_signal")
check("no growth keeps band", none_g["p50"], 25)

# ── unusable band returned as-is ───────────────────────────────────────────────
un = mc.compress_band({"usable": False, "reason": "dispersion_too_high"}, 0.10, "pe")
check("unusable untouched", un.get("usable"), False)
check("unusable no compression key", "compressed" in un, False)

# ── compress_anchor end-to-end ─────────────────────────────────────────────────
anchor = {"available": True, "by_metric": {"pe": band(42.88, 57.25, 72.24), "ps": band(6, 8, 10)}}
out = mc.compress_anchor(anchor, {"eps": 0.016, "revenue": 0.05})
check("anchor compression applied flag", out["compression"]["applied"], True)
check("anchor pe compressed", out["by_metric"]["pe"]["compressed"], True)
check("anchor ps compressed", out["by_metric"]["ps"]["compressed"], True)
check("anchor echoes eps growth", out["compression"]["growth_signals"]["eps"], 0.016)
check("anchor pe routed to eps growth (mature)", out["by_metric"]["pe"]["growth_tier"], "mature")
check("anchor ps routed to revenue growth (slowing)", out["by_metric"]["ps"]["growth_tier"], "slowing")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

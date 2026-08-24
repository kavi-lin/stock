#!/usr/bin/env python3
"""
Link Digest — EN → zh-TW translator (V1.0).

Translates the English prose fields of a link-digest judgment into Traditional
Chinese through the quota broker's selected certified provider.
One batched call (JSON in → JSON out) keeps it cheap. Best-effort: on any failure
(agy missing, timeout, unparseable) returns {} and the caller proceeds untranslated
(the writer degrades to rc=2, never fatal).

Gated by env LINK_DIGEST_TRANSLATE (default "1"; set "0" to skip).
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_SYS = (
    "You are a precise financial-news translator. Translate each value from English "
    "into Traditional Chinese (zh-TW, 台灣用語). Rules: keep stock tickers, company "
    "names, numbers, %, and $ figures intact; preserve markdown emphasis (**bold**); "
    "do NOT add or drop information; keep it natural and concise. Return ONLY a single "
    "JSON object with EXACTLY the same keys as the input, values translated. No prose, "
    "no code fence."
)


def translate_to_zh(fields: dict, timeout: int = 120) -> dict:
    """fields: {key: english_text}. Returns {key: zh_text} (subset that succeeded).

    Empty/blank inputs are skipped. Returns {} on any driver failure.
    """
    if os.environ.get("LINK_DIGEST_TRANSLATE", "1") == "0":
        return {}
    payload = {k: v for k, v in (fields or {}).items() if isinstance(v, str) and v.strip()}
    if not payload:
        return {}
    user = "Translate the values of this JSON object:\n" + json.dumps(payload, ensure_ascii=False)
    from scripts._shared import model_router
    res = model_router.run_role("link_digest", _SYS, user, timeout=timeout)

    out = res.parsed if isinstance(getattr(res, "parsed", None), dict) else None
    if out is None:
        # fall back to a lenient brace-extraction on raw text
        raw = (getattr(res, "raw_text", "") or "").strip()
        a, b = raw.find("{"), raw.rfind("}")
        if a != -1 and b > a:
            try:
                out = json.loads(raw[a:b + 1])
            except json.JSONDecodeError:
                out = None
    if not isinstance(out, dict):
        sys.stderr.write(f"[link_digest.translate] broker-selected model returned no JSON "
                         f"(exit={getattr(res,'exit_code','?')}, "
                         f"err={getattr(res,'error',None)})\n")
        return {}

    # keep only requested keys with non-empty string translations
    return {k: str(out[k]).strip() for k in payload
            if isinstance(out.get(k), str) and str(out[k]).strip()}


if __name__ == "__main__":  # quick manual smoke: echoes a tiny translation
    demo = {"headline": "NVIDIA beats on data-center revenue",
            "bull_case": "Demand for Blackwell remains strong into 2026."}
    print(json.dumps(translate_to_zh(demo), ensure_ascii=False, indent=2))

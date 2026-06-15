#!/usr/bin/env python3
"""
Translate a news digest's deep verdicts into Traditional Chinese (zh-TW).

For every deep verdict, adds `*_zh` variants of the analytical prose
(bull_case / bear_case / sector_view / macro_view / arbiter_reasoning / debate_note)
using the gemini (agy) batch translator. The News page renders `_zh` when the UI is
in Chinese, falling back to the English base otherwise (so this is purely additive).

Idempotent: a verdict that already carries a non-empty `bull_case_zh` is skipped
(use --force to retranslate). Best-effort: agy unavailable / failed → leaves the
digest untouched and exits 2 (degraded), never fatal — the daily pipeline must not
break on a translation hiccup.

Usage:
    python3 news/scripts/translate_digest.py            # latest *_digest.json
    python3 news/scripts/translate_digest.py --date 2026-05-30
    python3 news/scripts/translate_digest.py <path>     # explicit file
    python3 news/scripts/translate_digest.py --force
"""
import glob
import json
import os
import re
import sys

_CJK = re.compile(r"[一-鿿]")


def _has_cjk(t) -> bool:
    return bool(isinstance(t, str) and _CJK.search(t))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS_DIR = os.path.join(ROOT, "news", "news_logs")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from scripts.link_digest.translate import translate_to_zh
except Exception as e:
    sys.stderr.write(f"[translate_digest] cannot import translator: {e}\n")
    sys.exit(2)

FIELDS = ["bull_case", "bear_case", "sector_view", "macro_view",
          "arbiter_reasoning", "debate_note"]


def _resolve_path(args) -> str | None:
    date, explicit, i = None, None, 0
    while i < len(args):
        a = args[i]
        if a == "--date" and i + 1 < len(args):
            date = args[i + 1]; i += 2; continue
        if a.startswith("--date="):
            date = a.split("=", 1)[1]; i += 1; continue
        if not a.startswith("--"):
            explicit = a
        i += 1
    if explicit:
        return explicit if os.path.isabs(explicit) else os.path.join(ROOT, explicit)
    if date:
        cand = os.path.join(LOGS_DIR, f"{date}_digest.json")
        return cand if os.path.isfile(cand) else None
    files = sorted(glob.glob(os.path.join(LOGS_DIR, "*_digest.json")))
    return files[-1] if files else None


def main() -> None:
    args = sys.argv[1:]
    force = "--force" in args
    path = _resolve_path(args)
    if not path or not os.path.isfile(path):
        sys.stderr.write("[translate_digest] no digest file found\n")
        sys.exit(2)

    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    verdicts = data.get("verdicts") or []

    # Collect work across all deep verdicts into ONE batched agy call.
    payload, keymap = {}, {}
    targets = 0
    for vi, v in enumerate(verdicts):
        if v.get("depth") != "deep":
            continue
        if not force and str(v.get("bull_case_zh") or "").strip():
            continue  # already translated
        had = False
        for f in FIELDS:
            txt = v.get(f)
            # Skip empty fields and ones already written in Chinese (the daily news
            # protocol already emits zh prose — only English stragglers need agy).
            if isinstance(txt, str) and txt.strip() and not _has_cjk(txt):
                k = f"k{len(keymap)}"
                payload[k] = txt
                keymap[k] = (vi, f)
                had = True
        if had:
            targets += 1

    if not payload:
        print(f"[translate_digest] nothing to translate in {os.path.basename(path)} "
              f"(all deep verdicts already have zh, or none present)")
        sys.exit(0)

    tr = translate_to_zh(payload)
    if not tr:
        sys.stderr.write(f"[translate_digest] gemini produced no translation for "
                         f"{os.path.basename(path)} (agy missing/failed); left as-is\n")
        sys.exit(2)

    applied = 0
    for k, zh in tr.items():
        vi, f = keymap.get(k, (None, None))
        if vi is None:
            continue
        verdicts[vi][f + "_zh"] = zh
        applied += 1

    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

    print(f"[translate_digest] {os.path.basename(path)}: {applied}/{len(payload)} fields "
          f"across {targets} deep verdict(s) → zh-TW")
    # partial success still exits 0 — the UI falls back per-field where missing
    sys.exit(0)


if __name__ == "__main__":
    main()

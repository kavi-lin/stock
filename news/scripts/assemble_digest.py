#!/usr/bin/env python3
"""
Assemble news_logs/YYYY-MM-DD_digest.json from chunk JSON files written via Write tool.
Avoids stream idle timeout from single mega Bash heredoc.

Usage:
  python3 news/scripts/assemble_digest.py <date YYYY-MM-DD>

Reads:
  news/news_logs/<date>_chunks/skeleton.json
  news/news_logs/<date>_chunks/deep.json   (array of deep verdicts)
  news/news_logs/<date>_chunks/shallow_a.json   (array of shallow verdicts)
  news/news_logs/<date>_chunks/shallow_b.json   (array of shallow verdicts)
Writes:
  news/news_logs/<date>_digest.json
"""
import json, os, sys

if len(sys.argv) < 2:
    sys.exit("usage: assemble_digest.py YYYY-MM-DD")

date = sys.argv[1]
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGS = os.path.join(ROOT, "news/news_logs")
CHUNKS = os.path.join(LOGS, f"{date}_chunks")

skel = json.load(open(os.path.join(CHUNKS, "skeleton.json"), "r", encoding="utf-8"))
deep = json.load(open(os.path.join(CHUNKS, "deep.json"), "r", encoding="utf-8"))
shal_a = json.load(open(os.path.join(CHUNKS, "shallow_a.json"), "r", encoding="utf-8"))
shal_b = json.load(open(os.path.join(CHUNKS, "shallow_b.json"), "r", encoding="utf-8"))

verdicts = []
# build verdicts in news_id order
all_v = {v["news_id"]: v for v in (deep + shal_a + shal_b)}
for i in range(1, 200):
    nid = f"n{i:03d}"
    if nid in all_v:
        verdicts.append(all_v[nid])

skel["verdicts"] = verdicts

out_path = os.path.join(LOGS, f"{date}_digest.json")
with open(out_path, "w", encoding="utf-8") as fp:
    json.dump(skel, fp, ensure_ascii=False, indent=2)

print(f"[assemble_digest] ✓ wrote {out_path} ({len(verdicts)} verdicts: "
      f"{sum(1 for v in verdicts if v['depth']=='deep')} deep, "
      f"{sum(1 for v in verdicts if v['depth']=='shallow')} shallow)")

#!/usr/bin/env python3
"""Delete local files that are safely archived on Drive. Dry-run unless --apply.

A file is deleted only if ALL hold:
  - it is listed in a prune-eligible manifest (never forward_expectations_full)
  - the bundle's tar md5 on Drive still matches archive/drive_archive/INDEX.md
  - its current sha256 equals the manifest sha256 (unchanged since archiving)
  - it is not tracked in git
"""
import gzip, hashlib, os, re, subprocess, sys

REPO = "/Users/kavi/Developer/Claude/Projects/ai-investment-committee"
apply = "--apply" in sys.argv
os.chdir(REPO)

index = open("archive/drive_archive/INDEX.md", encoding="utf-8").read()
# default: every bundle the index still marks as "尚未刪除" (RETAINED bundles never match)
PRUNE = [a for a in sys.argv[1:] if not a.startswith("--")] or re.findall(r"^\| `(\w+)` .*本機尚未刪除", index, re.M)
print("bundles:", PRUNE)
remote_cache = {}


def remote_md5(path):
    d = path.rsplit("/", 1)[0]
    if d not in remote_cache:
        remote_cache[d] = dict(l.split()[::-1] for l in subprocess.check_output(["rclone", "md5sum", d], text=True).splitlines())
    return remote_cache[d].get(path.rsplit("/", 1)[1])
tracked = set(subprocess.check_output(["git", "ls-files", "-z"], text=True).split("\0"))

freed = deleted = skipped = 0
for name in PRUNE:
    m = re.search(rf"`(gdrive:[^`]*/{name}\.tar\.gz)`（md5 `([0-9a-f]{{32}})`）", index)
    if not m or remote_md5(m.group(1)) != m.group(2):
        print(f"SKIP bundle {name}: Drive md5 does not match index"); continue
    rows = gzip.open(f"archive/drive_archive/manifests/{name}.manifest.tsv.gz", "rt", encoding="utf-8").read().splitlines()[1:]
    for row in rows:
        path, size, _, sha, _ = row.split("\t")
        if path in tracked or not os.path.isfile(path):
            skipped += 1; continue
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for c in iter(lambda: fh.read(1 << 20), b""):
                h.update(c)
        if h.hexdigest() != sha:
            skipped += 1; print(f"changed since archive, kept: {path}"); continue
        freed += int(size); deleted += 1
        if apply:
            os.remove(path)
print(f"{'DELETED' if apply else 'would delete'} {deleted} files, {freed/1048576:.1f} MB; kept {skipped}")
if not apply:
    print("re-run with --apply to delete")

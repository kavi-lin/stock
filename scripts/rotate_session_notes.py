#!/usr/bin/env python3
"""SESSION_NOTES.md 批次輪替（V4.68.0，0 LLM）。

制度（使用者 2026-07-03 定案）：
- 主檔 SESSION_NOTES.md 保留最近的 Session Note；超過 20 個時，把最舊的 10 個
  整批切成一個獨立檔 `archive/session_notes_<最舊版號>_to_<最新版號>.md`（批內新在上）。
- 也就是「每累積滿 10 個舊 note 才搬一次」，平常 session 收尾不用搬。

用法：
    python3 scripts/rotate_session_notes.py                 # 主檔輪替（不足 20 個 → no-op）
    python3 scripts/rotate_session_notes.py --split-legacy archive/session_notes_archive.md
        # 一次性：把舊式單一 rolling archive 拆成 10-note 批次檔後刪除原檔

rc=0 正常（含 no-op）；rc=1 結構異常（區塊數對不上、寫檔失敗）。
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "SESSION_NOTES.md")
ARCHIVE_DIR = os.path.join(ROOT, "archive")

KEEP = 10          # 主檔常態保留數
TRIGGER = 20       # 超過此數才切一批
BATCH = 10         # 每批數量

# 支援 "(v4.63.0)" 也支援範圍式 "(v2.10.0 → v2.11.0)"（取第一個版號）
VER_RE = re.compile(r"\(v(\d[\w.\-]*)")


def parse_blocks(lines):
    """回傳 (note_blocks, first_note_line, tail_start)。
    note_blocks = [(heading_line_idx, end_idx, version_str)]，依檔案順序（新在上）。
    tail_start = 第一個非 Session Note 內容（指標註解 / 常駐區塊）的行號。"""
    note_idx = [i for i, l in enumerate(lines)
                if l.startswith("## ") and "Session Note" in l]
    if not note_idx:
        return [], None, None
    # 尾端邊界：最後一個 note 之後，第一個 <!-- 或非 Session Note 的 ## 標題
    tail_start = len(lines)
    for i in range(note_idx[-1] + 1, len(lines)):
        l = lines[i]
        if l.startswith("<!--") or (l.startswith("## ") and "Session Note" not in l):
            tail_start = i
            break
    blocks = []
    for j, start in enumerate(note_idx):
        end = note_idx[j + 1] if j + 1 < len(note_idx) else tail_start
        m = VER_RE.search(lines[start])
        blocks.append((start, end, m.group(1) if m else f"n{j}"))
    return blocks, note_idx[0], tail_start


def write_batch(batch_lines_groups):
    """batch_lines_groups: list of (version, [lines])，依新→舊。寫成一個批次檔。"""
    newest_v = batch_lines_groups[0][0]
    oldest_v = batch_lines_groups[-1][0]
    fname = f"session_notes_v{oldest_v}_to_v{newest_v}.md"
    path = os.path.join(ARCHIVE_DIR, fname)
    if os.path.exists(path):
        print(f"[rotate_session_notes] ✗ 目標已存在，不覆蓋: {path}", file=sys.stderr)
        sys.exit(1)
    header = [f"# Session Notes 歸檔 v{oldest_v} → v{newest_v}（新在上，共 {len(batch_lines_groups)} 個）",
              "", "> 由 scripts/rotate_session_notes.py 產出。查特定版本：Grep 版號於 archive/session_notes_*.md。", ""]
    body = []
    for _, blk in batch_lines_groups:
        while blk and blk[-1] == "":
            blk = blk[:-1]
        body += blk + [""]
    with open(path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(header + body))
    return path


def rotate_main():
    lines = open(MAIN, encoding="utf-8").read().split("\n")
    blocks, first, tail = parse_blocks(lines)
    n = len(blocks)
    if n <= TRIGGER:
        print(f"[rotate_session_notes] ✓ 主檔 {n} 個 Session Note（≤{TRIGGER}），no-op")
        return
    # 切最舊的 BATCH 個（blocks 是新在上 → 最舊在尾）
    cut = blocks[-BATCH:]
    groups = [(v, lines[s:e]) for s, e, v in cut]
    path = write_batch(groups)
    keep_end = cut[0][0]  # 被切批次的第一行 = 保留區的結束
    new_lines = lines[:keep_end] + lines[tail:]
    open(MAIN, "w", encoding="utf-8").write("\n".join(new_lines))
    remain = n - BATCH
    print(f"[rotate_session_notes] ✓ 切出 {BATCH} 個 → {os.path.relpath(path, ROOT)}；主檔剩 {remain} 個")


def split_legacy(legacy_path):
    lines = open(legacy_path, encoding="utf-8").read().split("\n")
    blocks, first, tail = parse_blocks(lines)
    if not blocks:
        print("[rotate_session_notes] ✗ 舊 archive 無 Session Note", file=sys.stderr)
        sys.exit(1)
    total = len(blocks)
    # blocks 新在上；由尾端（最舊）往前，每 BATCH 一檔
    written = []
    i = total
    while i > 0:
        lo = max(0, i - BATCH)
        cut = blocks[lo:i]           # 一批（新在上）
        groups = [(v, lines[s:e]) for s, e, v in cut]
        written.append(write_batch(groups))
        i = lo
    moved = sum(1 for _ in blocks)
    os.remove(legacy_path)
    print(f"[rotate_session_notes] ✓ 舊 archive {total} 個 note 拆成 {len(written)} 個批次檔，已刪除 {os.path.basename(legacy_path)}")
    for p in written:
        print(f"   - {os.path.relpath(p, ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split-legacy", help="舊式單一 rolling archive 檔路徑（一次性拆分）")
    args = ap.parse_args()
    if args.split_legacy:
        split_legacy(os.path.join(ROOT, args.split_legacy)
                     if not os.path.isabs(args.split_legacy) else args.split_legacy)
    else:
        rotate_main()


if __name__ == "__main__":
    main()

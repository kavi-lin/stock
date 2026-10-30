# Drive 歸檔索引（ARCHIVE INDEX）

> 本檔記錄「從專案本機搬到 Google Drive」的資料，**避免備份後再也找不到**。每次新增歸檔都在最下方加一節，不要改舊節。
> 逐檔清單（path / bytes / mtime / sha256 / 是否在 git）在 `manifests/<bundle>.manifest.tsv.gz`。

- Drive 根目錄：`gdrive:ai-investment-committee-archive/`（rclone remote `gdrive`，Kavi 私人 Drive）
- 歸檔日期：2026-10-29；tar 內路徑皆為**相對專案根目錄**，在專案根解壓即回到原位
- 上傳驗證：`rclone md5sum` 與本機 tar 的 md5 逐包相符
- **機密處理**：tar 內文字檔的 `API_KEY=` / `apikey=` / `token=` / `AIza…` 值已遮成 `[REDACTED]`；manifest 的 sha256 是**原檔**的。本機原檔未改動。

## 怎麼找回資料

```bash
# 1) 找某檔在哪一包（zgrep 查 manifest）
zgrep -h 'invest_20260502' archive/drive_archive/manifests/*.manifest.tsv.gz
# 2) 只取回一個檔案
rclone cat gdrive:ai-investment-committee-archive/2026-10-29/<bundle>.tar.gz | tar -xzf - -C . '<path-from-manifest>'
# 3) 整包還原到原位（不覆蓋已存在檔，加 -k）
rclone cat gdrive:ai-investment-committee-archive/2026-10-29/<bundle>.tar.gz | tar -xzkf - -C .
```

## 本次歸檔（2026-10-29）

| bundle | 檔數 | 原始大小 | tar 大小 | 檔案日期範圍 | 本機狀態 |
|---|---:|---:|---:|---|---|
| `scan_logs_pre_20260929` | 652 | 306.7 MB | 71.6 MB | 2026-04-16 ~ 2026-09-22 | 本機已刪（2026-10-30，刪前逐檔 sha256 與 Drive md5 驗證） |
| `news_breaknews_pre_20260830` | 6972 | 138.4 MB | 24.4 MB | 2026-04-10 ~ 2026-08-30 | 本機已刪（2026-10-30，刪前逐檔 sha256 與 Drive md5 驗證） |
| `scratch_and_regenerable_caches` | 2649 | 187.2 MB | 23.0 MB | 2026-04-25 ~ 2026-10-15 | 本機已刪（2026-10-30，刪前逐檔 sha256 與 Drive md5 驗證） |
| `forward_expectations_full` | 3295 | 364.1 MB | 39.6 MB | 2026-06-15 ~ 2026-10-29 | RETAINED (backup only) |

### `scan_logs_pre_20260929`

- **內容**：protocol/scan 執行 log 與 history.*.bak.json 回滾備份（mtime>30d，untracked）
- **使用狀態**：run_protocol_manual.py 回滾只用近期 bak；dashboard 讀近期 scan_logs。>30d 的無程式依賴
- **Drive**：`gdrive:ai-investment-committee-archive/2026-10-29/scan_logs_pre_20260929.tar.gz`（md5 `0f497f0ae63d8cff7aae75ddf7f581e7`）
- **Manifest**：`archive/drive_archive/manifests/scan_logs_pre_20260929.manifest.tsv.gz`
- **遮蔽**：68 處 / 18 個檔（investment/scan_logs/invest_20260502_211808.log, investment/scan_logs/invest_20260503_003018.log, investment/scan_logs/invest_20260505_231416.log, investment/scan_logs/invest_20260508_200525.log, investment/scan_logs/invest_20260511_222531.log, investment/scan_logs/invest_20260511_224333.log, investment/scan_logs/invest_20260520_214735.log, investment/scan_logs/invest_20260526_221355.log, investment/scan_logs/invest_20260816_225301.log, investment/scan_logs/invest_20260818_011707.log, news/scan_logs/news_20260731_220233.log, sector/scan_logs/daily_update_20260622_205434.log, sector/scan_logs/daily_update_20260711_092745.log, sector/scan_logs/daily_update_20260806_010156.log, sector/scan_logs/daily_update_20260806_012330.log, sector/scan_logs/sector_20260421_071908.log, sector/scan_logs/sector_20260427_204554.log, sector/scan_logs/sector_20260917_225917_c9e9.log）
- **本機狀態**：本機已刪（2026-10-30，刪前逐檔 sha256 與 Drive md5 驗證）

### `news_breaknews_pre_20260830`

- **內容**：news_logs（>60d）+ break_news bn_*.json（>60d，untracked）
- **使用狀態**：break_news store.py 用 _seen_index.json 去重（保留在本機）；重建索引時 >60d 舊條目不再被輪詢，無影響
- **Drive**：`gdrive:ai-investment-committee-archive/2026-10-29/news_breaknews_pre_20260830.tar.gz`（md5 `598cdfefc282eb7a248c337751bf64f2`）
- **Manifest**：`archive/drive_archive/manifests/news_breaknews_pre_20260830.manifest.tsv.gz`
- **遮蔽**：0 處 / 0 個檔
- **本機狀態**：本機已刪（2026-10-30，刪前逐檔 sha256 與 Drive md5 驗證）

### `scratch_and_regenerable_caches`

- **內容**：earnings_calendar 舊快照、.cache_bridge 舊 fmp_earnings_*、tmp/ 開發暫存（不含 npm-cache）
- **使用狀態**：皆為 gitignore 的可再生 cache / 暫存；僅為保險備份
- **Drive**：`gdrive:ai-investment-committee-archive/2026-10-29/scratch_and_regenerable_caches.tar.gz`（md5 `84c4ff64e34c3c5ea52c69f22e8a70fa`）
- **Manifest**：`archive/drive_archive/manifests/scratch_and_regenerable_caches.manifest.tsv.gz`
- **遮蔽**：1 處 / 1 個檔（tmp/skills-endpoint-fix-20261004/session.patch）
- **本機狀態**：本機已刪（2026-10-30，刪前逐檔 sha256 與 Drive md5 驗證）

### `forward_expectations_full`

- **內容**：Forward Expectations 全部 snapshot（不可再生的預測原始紀錄）+ calibration index
- **使用狀態**：【使用中】forward_expectations_calibration.py glob 整個資料夾做校準 —— 本機保留，Drive 只是災難備份，勿刪本機
- **Drive**：`gdrive:ai-investment-committee-archive/2026-10-29/forward_expectations_full.tar.gz`（md5 `11f7041fa5a72aa3c11f8ac54252e510`）
- **Manifest**：`archive/drive_archive/manifests/forward_expectations_full.manifest.tsv.gz`
- **遮蔽**：0 處 / 0 個檔
- **本機狀態**：RETAINED (backup only)

## 規則

- `forward_expectations/` 是**不可再生**的預測原始紀錄，且 `forward_expectations_calibration.py` 會 glob 整個資料夾做校準 —— **本機必須保留**，Drive 那份僅為災難備份。
- 已進 git 的檔案不從本機刪除（git 即備份），因此各包只含 untracked 檔。
- 刪除任何已歸檔的本機檔之前，先確認該 bundle 在上表的 md5 已驗證。

## 追加歸檔（2026-10-30）

Drive 目錄：`gdrive:ai-investment-committee-archive/2026-10-30/`；還原方式同上（把日期目錄換成 2026-10-30）。
這三個來源原本都是 untracked／gitignore，**沒有任何其他備份**，所以 `RETAINED` 的兩包是唯一的災難備份。

| bundle | 檔數 | 原始大小 | tar 大小 | 檔案日期範圍 | 本機狀態 |
|---|---:|---:|---:|---|---|
| `momentum_screen_csv_unreferenced_pre_20260831` | 136 | 21.9 MB | 6.2 MB | 2026-04-18 ~ 2026-08-31 | 本機已刪（2026-10-30，刪前逐檔 sha256 與 Drive md5 驗證） |
| `thematic_recommendations_full` | 142 | 98.5 MB | 5.2 MB | 2026-04-25 ~ 2026-10-30 | RETAINED (backup only) |
| `momentum_journal_full` | 3 | 14.2 MB | 1.1 MB | 2026-04-18 ~ 2026-10-27 | RETAINED (backup only) |

### `momentum_screen_csv_unreferenced_pre_20260831`

- **內容**：momentum-monitor/cache 的 screen_*.csv 歷史快照（>60d 且未被 journal.jsonl 引用）
- **使用狀態**：journal.py 只會用 journal.jsonl 內 60 個 snap_id 對應的 csv（全部留在本機）；此包是未被引用的舊快照，非 point-in-time 可再生
- **Drive**：`gdrive:ai-investment-committee-archive/2026-10-30/momentum_screen_csv_unreferenced_pre_20260831.tar.gz`（md5 `0c828f120c1e6a7fb5beda5b49e48af0`）
- **Manifest**：`archive/drive_archive/manifests/momentum_screen_csv_unreferenced_pre_20260831.manifest.tsv.gz`
- **遮蔽**：0 處 / 0 個檔
- **本機狀態**：本機已刪（2026-10-30，刪前逐檔 sha256 與 Drive md5 驗證）

### `thematic_recommendations_full`

- **內容**：戰術雷達每日推薦 JSON 全部（2026-04-25 起；untracked 且原本無任何備份）
- **使用狀態**：【使用中】build_event_index.py glob 全部、weekly_review.py 讀歷史、dashboard radar 讀近期 —— 本機保留，Drive 僅為災難備份，勿刪本機
- **Drive**：`gdrive:ai-investment-committee-archive/2026-10-30/thematic_recommendations_full.tar.gz`（md5 `ebfd0a6eb3abb9cdc5b0bd4bd6699b83`）
- **Manifest**：`archive/drive_archive/manifests/thematic_recommendations_full.manifest.tsv.gz`
- **遮蔽**：0 處 / 0 個檔
- **本機狀態**：RETAINED (backup only)

### `momentum_journal_full`

- **內容**：momentum-monitor forward-return journal（journal.jsonl，5/20/60d 報酬追蹤；untracked 且原本無任何備份）
- **使用狀態**：【使用中】journal.py snapshot/update/stats 的唯一資料來源 —— 本機保留，Drive 僅為災難備份，勿刪本機
- **Drive**：`gdrive:ai-investment-committee-archive/2026-10-30/momentum_journal_full.tar.gz`（md5 `e8e9627075de475f3fda491f0e7412a0`）
- **Manifest**：`archive/drive_archive/manifests/momentum_journal_full.manifest.tsv.gz`
- **遮蔽**：0 處 / 0 個檔
- **本機狀態**：RETAINED (backup only)

### 保留規則補充

- `skills/momentum-monitor/cache/` 內被 `journal.jsonl` 引用的 60 個 `screen_*.csv` **必須留在本機**（`journal.py stats` 逐筆載入）；只有未被引用且 >60d 的才歸檔。
- `skills/thematic-screener/data/recommendations/` 與 `skills/momentum-monitor/journal/` 是唯一原始紀錄，禁止清理，只能增量備份。

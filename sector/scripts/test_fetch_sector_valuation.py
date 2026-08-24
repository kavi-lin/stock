#!/usr/bin/env python3
"""test_fetch_sector_valuation.py — PE snapshot 非交易日回退的回歸測試。

為什麼有這支：FMP `/stable/sector-pe-snapshot` **只有交易日有值**，非交易日回空
list。舊版 `fetch_pe_snapshot()` 一拿到空就 `sys.exit`，於是產業掃描**逢週末／假日
100% 必掛**（2026-07-11 六、2026-08-16 日各一次，同一錯誤）。這個 bug 活下來不是
因為難偵測，是**觸發面從沒被走到** —— 今年 sector 幾乎只在平日跑。日曆形狀的盲區
不會被任何既有測試發現，所以它需要一支自己的測試。

鎖住六件事：
  1. **非交易日回退到最近有資料的交易日**，且回報的是**實際來源日**（不是 as_of）。
     回退是**真的去抓那天的資料**，不是沿用舊 cache —— 拿舊 cache 冒充當日是這個
     修法刻意不採用的方案。
  2. **交易日不誤觸回退**：lag=0，且只探測一天（多探 = 白花 API 額度）。
  3. **半套資料不算數**：一個 exchange 有值、另一個空 → 必須繼續回退，不得用半套
     資料湊出一個看起來完整的 snapshot（靜默半真相比報錯更糟）。
  4. **回看窗口邊界**：第 5 天有資料 → 過；第 6 天才有 → rc≠0 中止。鎖住
     `PE_SNAPSHOT_MAX_LOOKBACK_DAYS` 的語義，改常數會紅。
  5. **窗口內全空仍中止**：回退不是「永遠有答案」，找不到就要中止而非回舊值。
  6. **入口接線**：走真的 `main()`，斷言 provenance 欄位有進 payload。只驗函式行為
     擋不住「欄位被人從 payload 拿掉」（MAINTENANCE §2c #7）。
  另加一條 `build_sector_intel.py` 的 passthrough 原始碼斷言（§2c #8：producer 與
  consumer 各寫一份欄位名，漂移是靜默的）。

純 stdlib、零網路、不碰真實 cache（全部走 tmpdir）。
Run: python3 sector/scripts/test_fetch_sector_valuation.py   # rc=0 全過 / rc=1 fail
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
# ROOT 要自己插，不能靠 `import fetch_sector_valuation` 的副作用（被測模組確實會
# insert 一次，但那是它的實作細節；哪天它改用相對 import，這裡的 sector.lib 匯入
# 就會在**匯入階段**炸掉，而不是給出可讀的失敗）。
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import fetch_sector_valuation as mod  # noqa: E402
from sector.lib.sector_utils import PROJECT_TO_FMP  # noqa: E402

FAILS = []


def eq(label, got, want):
    if got != want:
        FAILS.append(f"{label}: got {got!r}, want {want!r}")


# 被測模組的回退進度是印到 stderr 的正常輸出；測試會刻意跑很多次回退，全放出來
# 會把真正的失敗訊息淹掉。只在測試期間吞掉，不影響被測行為。
quiet = lambda: contextlib.redirect_stderr(io.StringIO())  # noqa: E731


# ── fake FMP ────────────────────────────────────────────────────────────────
# 只喂 fetch_sector_valuation 真正會問的四個 endpoint。snapshot 依日期／exchange
# 查表，其餘回固定形狀的合法資料（長度要夠 zscore / 3M return / 20d volume 用）。

def make_fake_fmp(snapshot_table):
    """snapshot_table: {(date, exchange): rows | []}。未列出的組合一律視為空。"""
    probed_dates = []

    def fake_fmp_get(path, params, **kw):
        if path == "/stable/sector-pe-snapshot":
            d, exch = params["date"], params["exchange"]
            probed_dates.append(d)
            return snapshot_table.get((d, exch), [])
        if path == "/stable/historical-sector-pe":
            return [{"pe": 20.0 + (i % 7)} for i in range(40)]
        if path == "/stable/historical-price-eod/light":
            return [{"date": f"2026-05-{(i % 28) + 1:02d}",
                     "price": 100.0 + i, "volume": 1_000_000 + i}
                    for i in range(70)]
        raise AssertionError(f"unexpected endpoint in test: {path}")

    return fake_fmp_get, probed_dates


def snapshot_rows(pe=30.0):
    return [{"sector": fmp_name, "pe": pe} for fmp_name in PROJECT_TO_FMP.values()]


def table_for(dates, exchanges=("NASDAQ", "NYSE"), pe=30.0):
    return {(d, e): snapshot_rows(pe) for d in dates for e in exchanges}


def install(fake):
    # §2c #1：先證明錨點存在再替換。打在不存在的名字上會安靜新增一個沒人讀的屬性。
    assert hasattr(mod, "fmp_get"), "anchor mod.fmp_get missing — 測試已與被測模組脫鉤"
    mod.fmp_get = fake


_REAL_FMP_GET = mod.fmp_get


def restore():
    mod.fmp_get = _REAL_FMP_GET


# ── 1. 週末回退：as_of 週日，只有週五有資料 ─────────────────────────────────
fake, probed = make_fake_fmp(table_for(["2026-08-14"]))
install(fake)
with quiet():
    snap, src = mod.fetch_pe_snapshot("2026-08-16")
eq("weekend.source_date", src, "2026-08-14")
eq("weekend.all_sectors_filled",
   sum(1 for v in snap.values() if v.get("NASDAQ") is not None), 11)
eq("weekend.probed_sun_sat_fri", probed[:3], ["2026-08-16", "2026-08-15", "2026-08-14"])
restore()

# ── 2. 交易日不誤觸回退，且只探一天 ─────────────────────────────────────────
fake, probed = make_fake_fmp(table_for(["2026-08-14", "2026-08-13"]))
install(fake)
with quiet():
    snap, src = mod.fetch_pe_snapshot("2026-08-14")
eq("tradingday.source_date", src, "2026-08-14")
# 兩個 exchange 各問一次同一天 = 2 次；問到第二天就是白花額度
eq("tradingday.no_extra_probes", set(probed), {"2026-08-14"})
restore()

# ── 3. 半套資料（單一 exchange 有值）必須繼續回退 ───────────────────────────
# 週日 NASDAQ 有值但 NYSE 空 —— 用半套湊出「完整」snapshot 是靜默半真相。
partial = {("2026-08-16", "NASDAQ"): snapshot_rows()}
partial.update(table_for(["2026-08-14"]))
fake, probed = make_fake_fmp(partial)
install(fake)
with quiet():
    snap, src = mod.fetch_pe_snapshot("2026-08-16")
eq("partial.rejects_half_data", src, "2026-08-14")
eq("partial.both_exchanges_present",
   all(set(v) == {"NASDAQ", "NYSE"} for v in snap.values() if v), True)
restore()

# ── 4. 回看窗口邊界：第 5 天過、第 6 天中止 ─────────────────────────────────
eq("lookback.constant_is_5", mod.PE_SNAPSHOT_MAX_LOOKBACK_DAYS, 5)

fake, _ = make_fake_fmp(table_for(["2026-08-11"]))   # as_of 08-16 往回第 5 天
install(fake)
with quiet():
    snap, src = mod.fetch_pe_snapshot("2026-08-16")
eq("lookback.day5_ok", src, "2026-08-11")
restore()

fake, _ = make_fake_fmp(table_for(["2026-08-10"]))   # 第 6 天 → 超出窗口
install(fake)
try:
    with quiet():
        mod.fetch_pe_snapshot("2026-08-16")
    FAILS.append("lookback.day6_should_exit: 沒有中止，回退窗口比宣稱的寬")
except SystemExit as e:
    eq("lookback.day6_exit_nonzero", str(e).startswith("[ERROR]"), True)
restore()

# ── 5. 窗口內全空 → 中止（回退不是「永遠有答案」）──────────────────────────
fake, _ = make_fake_fmp({})
install(fake)
try:
    with quiet():
        mod.fetch_pe_snapshot("2026-08-16")
    FAILS.append("allempty.should_exit: 全空卻沒中止")
except SystemExit as e:
    eq("allempty.message_names_date", "2026-08-16" in str(e), True)
restore()

# ── 6. 入口接線：走真的 main()，provenance 必須進 payload ───────────────────
tmp = tempfile.mkdtemp(prefix="test_sector_val_")
try:
    fake, _ = make_fake_fmp(table_for(["2026-08-14"]))
    install(fake)
    assert hasattr(mod, "cache_path"), "anchor mod.cache_path missing"
    real_cache_path = mod.cache_path
    mod.cache_path = lambda name, as_of: os.path.join(tmp, f"{name}_{as_of}.json")
    argv = sys.argv
    sys.argv = ["fetch_sector_valuation.py", "--date", "2026-08-16"]
    try:
        with quiet():
            rc = mod.main()
    finally:
        sys.argv = argv
        mod.cache_path = real_cache_path
        restore()

    eq("main.rc", rc, 0)
    with open(os.path.join(tmp, "sector_valuation_2026-08-16.json")) as fp:
        payload = json.load(fp)
    eq("main.as_of_unchanged", payload.get("as_of_date"), "2026-08-16")
    # .get() 而非 []：欄位被整個拿掉時要報「got None」這種可讀的失敗，
    # 不是 KeyError traceback —— 守衛失效的訊息本身也要看得懂。
    eq("main.provenance_date", payload.get("pe_snapshot_date"), "2026-08-14")
    eq("main.provenance_lag", payload.get("pe_snapshot_lag_days"), 2)
    eq("main.sectors_complete", len(payload["sectors"]), 11)
    eq("main.pe_landed", payload["sectors"]["Technology"]["pe_ttm"] is not None, True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ── 7. consumer 接線：build_sector_intel 必須把 provenance 帶進 _phase1 ─────
# §2c #8 —— producer 與 consumer 各寫一份欄位名，一方改動後另一方走「找不到就靜默
# 回 None」分支，rc=0 永久靜音。這裡直接斷言 consumer 的讀取來源。
with open(os.path.join(ROOT, "sector", "scripts", "build_sector_intel.py")) as fp:
    consumer_src = fp.read()
for key in ("pe_snapshot_date", "pe_snapshot_lag_days"):
    eq(f"consumer.reads_{key}", f'valuation.get("{key}")' in consumer_src, True)

# ──────────────────────────────────────────────────────────────────────────────
if FAILS:
    print(f"✗ {len(FAILS)} regression(s):")
    for f_ in FAILS:
        print("  -", f_)
    sys.exit(1)
print("✓ sector PE snapshot 非交易日回退 fixtures pass")

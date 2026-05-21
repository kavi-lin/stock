# tests/test_gics_sector_audit.py
import os
import sys
import glob
import json
import pytest

# 將專案路徑加入 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sector.lib.sector_utils import (
    canonicalize_sector_name, CANONICAL_SECTORS, UnknownSectorError,
)

# 定義快取路徑
THEME_CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills/theme-detector/cache"))
theme_caches = glob.glob(os.path.join(THEME_CACHE_DIR, "theme_detector_*.json"))

def test_canonical_alias_mappings():
    """測試別名對齊工具是否能將已知別名精確轉換為 Canonical 鍵名"""
    assert canonicalize_sector_name("Financial") == "Financials"
    assert canonicalize_sector_name("Financial Services") == "Financials"
    assert canonicalize_sector_name("Consumer Cyclical") == "Consumer_Discretionary"
    assert canonicalize_sector_name("Consumer Defensive") == "Consumer_Staples"
    assert canonicalize_sector_name("Basic Materials") == "Materials"
    assert canonicalize_sector_name("Communication Services") == "Communication"
    assert canonicalize_sector_name("Real Estate") == "Real_Estate"
    assert canonicalize_sector_name("REIT") == "Real_Estate"
    assert canonicalize_sector_name("Technology") == "Technology"


@pytest.mark.skipif(not theme_caches, reason="theme_detector cache absent in this environment")
def test_all_canonical_sectors_have_theme_keys():
    """從最新的 theme-detector 快取中讀取所有 sector_uptrend 鍵名，
    斷言利用別名工具解析後均屬於 11 大 Canonical Sector 鍵名之一，確保無隱性靜默漂移。
    """
    latest_cache_path = sorted(theme_caches)[-1]
    with open(latest_cache_path, "r", encoding="utf-8") as fp:
        cache_data = json.load(fp)

    uptrend_data = cache_data.get("sector_uptrend", {})
    assert uptrend_data, f"theme-detector cache {latest_cache_path} is empty or has no sector_uptrend"

    for raw_key in uptrend_data.keys():
        canon_key = canonicalize_sector_name(raw_key)
        assert canon_key in CANONICAL_SECTORS, (
            f"Failed to canonicalize sector key {raw_key!r} from cache. "
            f"Result {canon_key!r} is not in CANONICAL_SECTORS: {CANONICAL_SECTORS}"
        )


# ── v3.14.6 — strict mode + validator canonicalize ─────────────────────────

class TestStrictMode:
    def test_strict_known_alias_returns_canonical(self):
        assert canonicalize_sector_name("Financial Services", strict=True) == "Financials"
        assert canonicalize_sector_name("Consumer Cyclical", strict=True) == "Consumer_Discretionary"

    def test_strict_unknown_raises(self):
        with pytest.raises(UnknownSectorError):
            canonicalize_sector_name("NotARealSector", strict=True)

    def test_strict_empty_raises(self):
        with pytest.raises(UnknownSectorError):
            canonicalize_sector_name("", strict=True)
        with pytest.raises(UnknownSectorError):
            canonicalize_sector_name(None, strict=True)  # type: ignore[arg-type]

    def test_non_strict_unknown_falls_back(self, capsys):
        # non-strict default still warns + returns normalized_space
        r = canonicalize_sector_name("AnotherUnknownXYZ")
        assert r == "AnotherUnknownXYZ"
        # warning printed to stderr (dedup per process; second call silent)

    def test_silent_suppresses_warning(self, capsys):
        canonicalize_sector_name("YetAnotherUnknown42", silent=True)
        captured = capsys.readouterr()
        assert "YetAnotherUnknown42" not in captured.err


class TestValidatorCanonicalGate:
    """Validator integration — emulate the strict gate that
    validate_sector_intel.py applies to sectors[].name entries."""

    def test_canonical_form_passes(self):
        # Already canonical → should not raise
        for sector in CANONICAL_SECTORS:
            assert canonicalize_sector_name(sector, strict=True) == sector

    def test_alias_form_caught(self):
        # LLM emitting display name should fail strict gate as "non-canonical"
        name = "Financial Services"
        canon = canonicalize_sector_name(name, strict=True)
        # canonicalize succeeded but canon != original name → validator
        # would emit "name not in canonical form" error.
        assert canon == "Financials"
        assert canon != name

    def test_whitespace_padded_name_caught(self):
        name = " Technology "
        canon = canonicalize_sector_name(name, strict=True)
        assert canon == "Technology"
        assert canon != name  # validator flags difference

    def test_garbage_name_raises(self):
        # Builder / validator with strict=True must surface unknown names
        with pytest.raises(UnknownSectorError):
            canonicalize_sector_name("Healthcare_Insurance_REIT_Hybrid", strict=True)


def test_validator_module_imports_sector_utils():
    """v3.14.5 changelog claimed validator was canonicalized but no import
    was added. v3.14.6 closes the loop — make sure the import is actually
    present so this regression cannot recur silently."""
    here = os.path.dirname(__file__)
    validator_path = os.path.abspath(os.path.join(
        here, "..", "sector", "scripts", "validate_sector_intel.py",
    ))
    with open(validator_path, "r", encoding="utf-8") as f:
        src = f.read()
    assert "canonicalize_sector_name" in src, (
        "validate_sector_intel.py must import canonicalize_sector_name "
        "(v3.14.6 P2-1 closure)"
    )
    assert "strict=True" in src, (
        "validate_sector_intel.py must call canonicalize with strict=True"
    )


# ── v3.14.7 — FTD source_file path verification ──────────────────────────
# The most critical correctness fix in v3.14.6 was switching the FTD verbatim
# assert from "latest cache on disk" to "the specific cache file recorded at
# build time" (`_phase0.ftd.source_file`). These tests pin that behaviour so
# a future agent cannot silently revert to latest-cache compare.

from sector.scripts.validate_sector_intel import verify_ftd_verbatim  # noqa: E402


class TestVerifyFtdVerbatim:
    """`verify_ftd_verbatim(phase0_ftd, root)` is the testable extract of the
    validator's FTD assert. Returns list of errors (empty = pass)."""

    def _write_ftd_cache(self, ftd_dir, name, status_text):
        ftd_dir.mkdir(parents=True, exist_ok=True)
        path = ftd_dir / name
        path.write_text(json.dumps({
            "ftd_timeline": {"ftd_status_text": status_text},
        }), encoding="utf-8")
        return path

    def test_source_file_matches_returns_no_errors(self, tmp_path):
        ftd_dir = tmp_path / "sector" / "ftd_cache"
        self._write_ftd_cache(
            ftd_dir, "ftd_detector_2026-05-21_010000.json",
            "FTD CONFIRMED, day 30 post-confirmation",
        )
        phase0_ftd = {
            "source_file": "sector/ftd_cache/ftd_detector_2026-05-21_010000.json",
            "ftd_status_text": "FTD CONFIRMED, day 30 post-confirmation",
        }
        assert verify_ftd_verbatim(phase0_ftd, str(tmp_path)) == []

    def test_source_file_mismatch_returns_error(self, tmp_path):
        ftd_dir = tmp_path / "sector" / "ftd_cache"
        self._write_ftd_cache(
            ftd_dir, "ftd_detector_2026-05-21_010000.json",
            "FTD CONFIRMED, day 30 post-confirmation",
        )
        phase0_ftd = {
            "source_file": "sector/ftd_cache/ftd_detector_2026-05-21_010000.json",
            "ftd_status_text": "FTD CONFIRMED, Day 6 rally",  # hallucinated rewrite
        }
        errors = verify_ftd_verbatim(phase0_ftd, str(tmp_path))
        assert any("hallucination detected" in e for e in errors), errors

    def test_source_file_used_not_latest_cache(self, tmp_path):
        """**The critical anti-regression test**: validator must read the file
        named in `source_file`, NOT whichever cache is latest on disk. If a
        future agent reverts to `sorted(glob)[-1]`, this test catches it."""
        ftd_dir = tmp_path / "sector" / "ftd_cache"
        # OLD cache: matches what the sector intel claims it built against
        self._write_ftd_cache(
            ftd_dir, "ftd_detector_2026-05-21_010000.json",
            "FTD CONFIRMED, day 30 post-confirmation",
        )
        # NEWER cache: FTD daemon rolled a new snapshot AFTER build. Latest
        # by sort order. If validator falls back to latest it would flag the
        # legitimate report as hallucinated.
        self._write_ftd_cache(
            ftd_dir, "ftd_detector_2026-05-21_235959.json",
            "FTD CONFIRMED, day 31 post-confirmation",  # different text!
        )
        phase0_ftd = {
            # Pointing at the OLDER file — sector intel was built when it
            # was the current snapshot.
            "source_file": "sector/ftd_cache/ftd_detector_2026-05-21_010000.json",
            "ftd_status_text": "FTD CONFIRMED, day 30 post-confirmation",
        }
        # Validator must use source_file → status_text matches → pass.
        # If validator regresses to latest → comparing against day-31 cache
        # → "mismatch (hallucination)" error → test fails.
        errors = verify_ftd_verbatim(phase0_ftd, str(tmp_path))
        assert errors == [], (
            f"validator must read source_file, not latest cache. errors={errors}"
        )

    def test_missing_source_file_legacy_soft_skips(self, tmp_path, capsys):
        ftd_dir = tmp_path / "sector" / "ftd_cache"
        self._write_ftd_cache(
            ftd_dir, "ftd_detector_2026-05-21_010000.json",
            "FTD CONFIRMED, day 30 post-confirmation",
        )
        # No source_file in phase0_ftd (pre-v3.14.6 report)
        phase0_ftd = {
            "ftd_status_text": "FTD CONFIRMED, day 30 post-confirmation",
        }
        errors = verify_ftd_verbatim(phase0_ftd, str(tmp_path))
        # Soft skip — no error, just stderr warning
        assert errors == []
        captured = capsys.readouterr()
        assert "legacy report" in captured.err

    def test_source_file_points_to_missing_disk_path(self, tmp_path, capsys):
        # source_file given but file rotated off disk → soft skip, no error
        # (refuses unsafe fallback to latest)
        phase0_ftd = {
            "source_file": "sector/ftd_cache/ftd_detector_2099-01-01_000000.json",
            "ftd_status_text": "anything",
        }
        errors = verify_ftd_verbatim(phase0_ftd, str(tmp_path))
        assert errors == []
        captured = capsys.readouterr()
        assert "missing on disk" in captured.err

    def test_no_ftd_cache_at_all_errors(self, tmp_path):
        # No source_file AND no ftd_cache directory → hard error
        phase0_ftd = {"ftd_status_text": "x"}
        errors = verify_ftd_verbatim(phase0_ftd, str(tmp_path))
        assert any("No FTD cache file found" in e for e in errors), errors

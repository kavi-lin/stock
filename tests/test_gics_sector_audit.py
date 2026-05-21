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

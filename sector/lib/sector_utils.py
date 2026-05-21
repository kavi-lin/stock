# AI 投資委員會 — 產業板塊別名與 Canonical 名稱共享工具模組
import sys

# Repo 11 大 Canonical Sector 鍵名 (精確對齊 schema 與資料庫快取鍵名)
CANONICAL_SECTORS = [
    "Technology",
    "Healthcare",
    "Energy",
    "Financials",
    "Industrials",
    "Materials",
    "Communication",
    "Consumer_Discretionary",
    "Consumer_Staples",
    "Utilities",
    "Real_Estate"
]

# 統一別名對齊字典 (包含 GICS Prose Name, Display Name, FMP API 返值等)
SECTOR_ALIASES = {
    # Technology
    "Technology":             "Technology",
    "Tech":                   "Technology",
    
    # Healthcare
    "Healthcare":             "Healthcare",
    "Health Care":            "Healthcare",
    
    # Energy
    "Energy":                 "Energy",
    
    # Financials
    "Financial":              "Financials",
    "Financials":             "Financials",
    "Financial Services":     "Financials",
    
    # Industrials
    "Industrials":            "Industrials",
    "Industrial":             "Industrials",
    
    # Materials
    "Materials":              "Materials",
    "Basic Materials":        "Materials",
    "Basic_Materials":        "Materials",
    
    # Communication
    "Communication":          "Communication",
    "Communications":         "Communication",
    "Communication Services": "Communication",
    "Communication_Services": "Communication",
    
    # Consumer Discretionary
    "Consumer Cyclical":      "Consumer_Discretionary",
    "Consumer_Discretionary": "Consumer_Discretionary",
    "Consumer Discretionary": "Consumer_Discretionary",
    "ConsumerCyclical":      "Consumer_Discretionary",
    
    # Consumer Staples
    "Consumer Defensive":     "Consumer_Staples",
    "Consumer_Staples":       "Consumer_Staples",
    "Consumer Staples":       "Consumer_Staples",
    "ConsumerDefensive":     "Consumer_Staples",
    
    # Utilities
    "Utilities":              "Utilities",
    
    # Real Estate
    "Real Estate":            "Real_Estate",
    "Real_Estate":            "Real_Estate",
    "REIT":                   "Real_Estate",
}

_warned_set = set()


class UnknownSectorError(ValueError):
    """Raised by canonicalize_sector_name(..., strict=True) on unknown name.

    Builder / validator / tests opt into strict mode so an LLM-emitted bogus
    sector name fails fast at schema gate rather than silently propagating a
    `normalized_space` fallback into the cache layer where the failure mode is
    less actionable (cache miss, downstream NaN, etc.).
    """


def canonicalize_sector_name(name: str, *, silent: bool = False,
                             strict: bool = False) -> str:
    """Normalize any alias / display format into the 11-key canonical set.

    - `silent=True`  → suppress the once-per-name stderr warning on unknown.
    - `strict=True`  → raise `UnknownSectorError` on unknown (overrides
                       `silent`). Use in builder / validator / pytest callers
                       so bad names trip a schema fail rather than degrading
                       quietly. Digest / fetch keep `strict=False` because
                       upstream caches occasionally surface novel keys we
                       prefer to log + skip rather than crash on.

    Returns the canonical key, or — when `strict=False` and no alias matches —
    a defensively `normalized_space` (spaces → underscores) version of the
    input.
    """
    if not name:
        if strict:
            raise UnknownSectorError("canonicalize_sector_name received empty input")
        return ""

    cleaned = name.strip()

    # 1. 優先嘗試別名字典精確匹配
    if cleaned in SECTOR_ALIASES:
        return SECTOR_ALIASES[cleaned]

    # 2. 嘗試將空格轉為底線後的匹配
    normalized_space = cleaned.replace(" ", "_")
    if normalized_space in SECTOR_ALIASES:
        return SECTOR_ALIASES[normalized_space]

    # 3. 嘗試大小寫不敏感的匹配
    cleaned_lower = cleaned.lower()
    for alias, canon in SECTOR_ALIASES.items():
        if alias.lower() == cleaned_lower:
            return canon

    # 4. 嘗試去除底線與空格後的大小寫不敏感匹配
    cleaned_flat = cleaned_lower.replace(" ", "").replace("_", "")
    for alias, canon in SECTOR_ALIASES.items():
        alias_flat = alias.lower().replace(" ", "").replace("_", "")
        if alias_flat == cleaned_flat:
            return canon

    # 5. Unknown — strict raises, non-strict falls back with deduped warning.
    if strict:
        raise UnknownSectorError(
            f"unknown sector name {name!r}; not in SECTOR_ALIASES "
            "(strict=True). Add to alias map or fix the caller."
        )
    if cleaned not in _warned_set:
        _warned_set.add(cleaned)
        if not silent:
            print(
                f"[sector_utils] WARNING: Unknown sector name detected: "
                f"{name!r}. Fallback used.",
                file=sys.stderr,
            )
    return normalized_space



# Project Canonical Key 對應至 FMP API 查詢時所需之原始名稱
PROJECT_TO_FMP = {
    "Materials":              "Basic Materials",
    "Communication":          "Communication Services",
    "Consumer_Discretionary":  "Consumer Cyclical",
    "Consumer_Staples":        "Consumer Defensive",
    "Energy":                 "Energy",
    "Financials":              "Financial Services",
    "Healthcare":             "Healthcare",
    "Industrials":            "Industrials",
    "Real_Estate":             "Real Estate",
    "Technology":             "Technology",
    "Utilities":              "Utilities"
}


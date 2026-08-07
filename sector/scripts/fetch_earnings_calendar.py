#!/usr/bin/env python3
"""Fetch the sector protocol's US mid/large-cap earnings calendar.

One calendar request is joined locally with a cached company-screener snapshot.
This preserves whole-market coverage without the former one-profile-request per
calendar symbol fan-out (typically several thousand calls).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts._shared import fmp_pool  # noqa: E402
from sector.lib.earnings_calendar import FetchStats, fetch_calendar_range  # noqa: E402

MIN_MARKET_CAP = 2_000_000_000
US_EXCHANGES = {"NYSE", "NASDAQ", "AMEX", "NYSEArca", "BATS", "NMS", "NGM", "NCM"}
SCREENER_CACHE = ROOT / "sector" / "cache" / "company_screener_us_midcap.json"
SCREENER_TTL_SEC = 24 * 60 * 60


def _timing(value) -> str:
    normalized = str(value or "").lower()
    if normalized in {"bmo", "pre-market", "before market open"}:
        return "BMO"
    if normalized in {"amc", "after-market", "after market close"}:
        return "AMC"
    return "TAS"


def _market_cap_label(value: float) -> str:
    if value >= 1e12:
        return f"${value / 1e12:.1f}T"
    if value >= 1e9:
        return f"${value / 1e9:.1f}B"
    if value >= 1e6:
        return f"${value / 1e6:.0f}M"
    return f"${value:,.0f}"


def fetch_calendar(from_date: str, to_date: str, *, api_key: str | None = None) -> list[dict]:
    return fetch_calendar_range(from_date, to_date, api_key=api_key)


def _read_screener_cache(path: Path, ttl_sec: int) -> list[dict] | None:
    try:
        if time.time() - path.stat().st_mtime > ttl_sec:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        companies = payload.get("companies") if isinstance(payload, dict) else None
        return companies if isinstance(companies, list) else None
    except (OSError, ValueError, TypeError):
        return None


def _write_screener_cache(path: Path, companies: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "sector.company_screener.us_midcap.v1",
        "fetched_at": time.time(),
        "companies": companies,
    }
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def fetch_company_universe(
    *,
    api_key: str | None = None,
    cache_path: Path = SCREENER_CACHE,
    ttl_sec: int = SCREENER_TTL_SEC,
) -> tuple[dict[str, dict], bool]:
    """Return eligible US companies keyed by symbol and whether cache was used."""
    rows = _read_screener_cache(cache_path, ttl_sec)
    cache_hit = rows is not None
    if rows is None:
        rows = fmp_pool.get(
            "company-screener",
            {
                "marketCapMoreThan": MIN_MARKET_CAP,
                "country": "US",
                "isActivelyTrading": True,
                "isEtf": False,
                "isFund": False,
                "limit": 10_000,
            },
            stable=True,
            hard_fail=True,
            api_key=api_key,
        )
        if not isinstance(rows, list):
            raise ValueError("FMP company-screener returned a non-list response")
        _write_screener_cache(cache_path, rows)

    companies: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or "").upper()
        exchange = row.get("exchangeShortName") or row.get("exchange") or ""
        try:
            market_cap = float(row.get("marketCap") or 0)
        except (TypeError, ValueError):
            continue
        if (
            not symbol
            or market_cap < MIN_MARKET_CAP
            or row.get("country") != "US"
            or row.get("isActivelyTrading") is not True
            or row.get("isEtf") is True
            or row.get("isFund") is True
            or exchange not in US_EXCHANGES
        ):
            continue
        existing = companies.get(symbol)
        if existing is None or market_cap > float(existing.get("marketCap") or 0):
            companies[symbol] = row
    return companies, cache_hit


def build_output(earnings: list[dict], companies: dict[str, dict]) -> list[dict]:
    output = []
    for earning in earnings:
        symbol = earning.get("symbol")
        company = companies.get(symbol)
        if not symbol or not company:
            continue
        try:
            market_cap = float(company.get("marketCap") or 0)
        except (TypeError, ValueError):
            continue
        exchange = company.get("exchangeShortName") or company.get("exchange") or "N/A"
        if market_cap < MIN_MARKET_CAP or exchange not in US_EXCHANGES:
            continue
        output.append({
            "symbol": symbol,
            "companyName": company.get("companyName", symbol),
            "date": earning.get("date"),
            "timing": _timing(earning.get("time")),
            "marketCap": market_cap,
            "marketCapFormatted": _market_cap_label(market_cap),
            "sector": company.get("sector", "N/A"),
            "industry": company.get("industry", "N/A"),
            "epsEstimated": earning.get("epsEstimated"),
            "revenueEstimated": earning.get("revenueEstimated"),
            "fiscalDateEnding": earning.get("fiscalDateEnding"),
            "exchange": exchange,
        })
    timing_order = {"BMO": 1, "AMC": 2, "TAS": 3}
    return sorted(
        output,
        key=lambda row: (
            row.get("date") or "",
            timing_order.get(row.get("timing"), 3),
            -row.get("marketCap", 0),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("from_date")
    parser.add_argument("to_date")
    args = parser.parse_args()
    for value in (args.from_date, args.to_date):
        datetime.strptime(value, "%Y-%m-%d")
    if not os.environ.get("FMP_API_KEY"):
        parser.error("FMP_API_KEY is required")

    stats = FetchStats()
    earnings = fetch_calendar_range(args.from_date, args.to_date, stats=stats)
    companies, screener_cache_hit = fetch_company_universe()
    output = build_output(earnings, companies)
    print(
        f"[fetch_earnings_calendar] calendar_rows={len(earnings)} "
        f"eligible_companies={len(companies)} output_rows={len(output)} "
        f"calendar_api_calls={stats.api_calls} calendar_cache_hits={stats.cache_hits} "
        f"calendar_splits={stats.splits} screener_cache_hit={screener_cache_hit}",
        file=sys.stderr,
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Date helpers shared by sector/scripts/fetch_*.py."""
from __future__ import annotations

from datetime import date, datetime, timedelta


def lookback_window(as_of: str, days: int) -> tuple[str, str]:
    """Return (from_iso, to_iso) where from = as_of - days."""
    end = datetime.strptime(as_of, "%Y-%m-%d").date()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def cutoff_date(days_back: int) -> str:
    """Return today minus N days as ISO date (used for senate/insider windows)."""
    return (date.today() - timedelta(days=days_back)).isoformat()


_QUARTER_END_DAY = {3: 31, 6: 30, 9: 30, 12: 31}


def latest_complete_13f_quarter(as_of: str, lag_days: int = 45) -> tuple[int, int]:
    """Walk back quarter-by-quarter until (as_of - quarter_end) >= lag_days.

    13F filings are due 45 days after quarter-end; before that the data is incomplete.
    Returns (year, quarter) tuple.
    """
    d = datetime.strptime(as_of, "%Y-%m-%d").date()
    year, quarter = d.year, (d.month - 1) // 3 + 1
    while True:
        end_month = quarter * 3
        q_end = date(year, end_month, _QUARTER_END_DAY[end_month])
        if (d - q_end).days >= lag_days:
            return year, quarter
        if quarter == 1:
            year -= 1
            quarter = 4
        else:
            quarter -= 1


__all__ = ["lookback_window", "cutoff_date", "latest_complete_13f_quarter"]

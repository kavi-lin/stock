#!/usr/bin/env python3
"""
finviz_screener — shared repairs for finvizfinance screener output.

Lives in skills/_shared/ so the two independent callers of the public FINVIZ
screener stay in sync (dashboard_server `/api/industry/<name>` drill-down and
theme-detector's representative_stock_selector FINVIZ-public fallback). Both
read the `Ticker` column of `Overview().screener_view()`, so both inherit the
same upstream parsing defect.

Public API (no underscore prefix):
- normalize_screener_tickers(tickers) → list[str]
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

__all__ = ["normalize_screener_tickers"]


def normalize_screener_tickers(tickers) -> list[str]:
    """Strip the logo-fallback letter finviz prepends to every screener ticker.

    finviz renders the ticker cell as::

        <td data-boxover-ticker="NVDA">
          <a class="company-ticker"><img alt="NVDA logo"/><span>N</span></a>
          <a class="tab-link">NVDA</a>
        </td>

    That bare ``<span>`` is the placeholder shown while/if the logo image fails
    to load, and it always holds exactly the ticker's first character.
    finvizfinance 1.3.0 builds its DataFrame from ``col.text`` (screener/base.py
    ``_get_table``), which concatenates both nodes — so every ticker comes back
    with its first character duplicated: NVDA→NNVDA, AAPL→AAAPL, WOLF→WWOLF.
    Dropping one leading character is therefore exact, not approximate.

    Detection is done on the batch rather than per ticker, because in isolation
    a corrupted ``AADI`` is indistinguishable from a genuinely doubled ``AAPL``.
    An entire screener page in which *every* row starts with a doubled letter
    can only be this defect. When upstream fixes the markup (or finvizfinance
    switches to ``data-boxover-ticker``) the signature stops matching and the
    tickers pass through untouched.

    Known limit: a result set of one or two rows that happens to consist purely
    of genuinely-doubled tickers is ambiguous, and would be over-stripped if
    upstream is fixed. Correcting the currently-universal defect is worth that
    corner.

    Args:
        tickers: iterable of raw `Ticker` values from `screener_view()`.

    Returns:
        list[str]: stripped tickers when the defect signature matches, else the
        same values unchanged. Blank entries are preserved as-is.
    """
    raw = [("" if t is None else str(t).strip()) for t in tickers]
    present = [t for t in raw if t]
    if not present:
        return raw

    if not all(len(t) >= 2 and t[0] == t[1] for t in present):
        return raw

    # Loud on purpose: a silent repair hides the day upstream changes shape.
    logger.warning(
        "FINVIZ screener returned %d tickers with a duplicated leading "
        "character (logo-fallback letter); stripping it (e.g. %s → %s)",
        len(present), present[0], present[0][1:],
    )
    return [t[1:] if t else t for t in raw]

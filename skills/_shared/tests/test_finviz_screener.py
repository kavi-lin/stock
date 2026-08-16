"""finviz_screener.normalize_screener_tickers — the logo-fallback letter repair.

The bug this pins: finviz's screener ticker cell holds a bare `<span>` with the
ticker's first letter (the placeholder behind the company logo) *before* the
ticker link. finvizfinance 1.3.0 reads the cell with `col.text`, concatenating
both — so `/api/industry/Semiconductors` returned AADI for Analog Devices and
WWOLF for Wolfspeed, and theme-detector's FINVIZ-public fallback would have fed
the same corrupted symbols downstream.

The reason detection is a batch signature and not `t[0] == t[1]` per ticker:
AAPL, DDOG, LLY, FFIV and WWD are real symbols that already start doubled.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from skills._shared.finviz_screener import normalize_screener_tickers  # noqa: E402


class TestCorruptedBatch:
    def test_strips_duplicated_leading_char(self):
        raw = ["AADI", "AALAB", "WWOLF", "VVSH", "GGPRO"]
        assert normalize_screener_tickers(raw) == ["ADI", "ALAB", "WOLF", "VSH", "GPRO"]

    def test_genuinely_doubled_ticker_survives_round_trip(self):
        # Apple comes back as AAAPL under the defect; one strip restores AAPL.
        assert normalize_screener_tickers(["AAAPL", "AAXIL", "BBOXL"]) == [
            "AAPL",
            "AXIL",
            "BOXL",
        ]

    def test_warns_when_repair_fires(self, caplog):
        with caplog.at_level(logging.WARNING):
            normalize_screener_tickers(["AADI", "WWOLF"])
        assert "duplicated leading character" in caplog.text


class TestHealthyBatch:
    def test_clean_tickers_pass_through(self):
        raw = ["NVDA", "ADI", "ALAB", "AAPL"]
        assert normalize_screener_tickers(raw) == raw

    def test_single_doubled_ticker_among_clean_ones_is_not_stripped(self):
        # AAPL alongside clean neighbours must not be read as corruption.
        raw = ["AAPL", "MSFT", "DDOG"]
        assert normalize_screener_tickers(raw) == raw

    def test_no_warning_when_batch_is_clean(self, caplog):
        with caplog.at_level(logging.WARNING):
            normalize_screener_tickers(["NVDA", "AMD"])
        assert caplog.text == ""


class TestEdges:
    def test_empty_input(self):
        assert normalize_screener_tickers([]) == []

    def test_all_blank_entries_pass_through(self):
        assert normalize_screener_tickers(["", None]) == ["", ""]

    def test_blank_entries_preserved_alongside_repair(self):
        assert normalize_screener_tickers(["AADI", "", "WWOLF"]) == ["ADI", "", "WOLF"]

    def test_single_char_ticker_blocks_the_repair(self):
        # A 1-char ticker cannot carry the signature, so the batch is ambiguous
        # and must be left alone rather than silently mangled.
        assert normalize_screener_tickers(["AADI", "F"]) == ["AADI", "F"]

    def test_values_are_stripped_of_whitespace(self):
        assert normalize_screener_tickers([" AADI ", "WWOLF"]) == ["ADI", "WOLF"]

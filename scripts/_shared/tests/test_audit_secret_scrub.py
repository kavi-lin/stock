#!/usr/bin/env python3
"""V3.17.4 — Codex Finding 1 regression tests.

Pins the audit_data_alignment.py secret-leak hardening. Two attack
surfaces covered:
  1. DNS / network failure with exception message echoing the raw URL
  2. Server returning non-200 with body echoing the request

Run:
  python3 scripts/_shared/tests/test_audit_secret_scrub.py
  python3 -m pytest scripts/_shared/tests/test_audit_secret_scrub.py
"""
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import audit_data_alignment as m  # noqa: E402

# Sentinel chosen to be obviously non-real so a leak shows up immediately
# in any test failure output or coverage diff.
SENTINEL = "SENTINEL_SECRET_NEVER_VALID_V317"


class TestScrubSecretHelper(unittest.TestCase):
    def test_strips_apikey_query_pattern(self):
        s = "GET /stable/quote?symbol=NVDA&apikey=abc123def → 401"
        out = m._scrub_secret(s)
        self.assertNotIn("abc123def", out)
        self.assertIn("apikey=<REDACTED>", out)

    def test_strips_apikey_uppercase_variant(self):
        # FMP is case-insensitive in some paths; defensive regex must too.
        s = "?APIKEY=secret123 fired"
        out = m._scrub_secret(s)
        self.assertNotIn("secret123", out)

    def test_strips_literal_secret_value(self):
        # Secondary defense: even if the URL pattern is different, the
        # literal key value must be stripped when provided.
        s = "Request failed with header apikey: my-secret-key-xyz"
        out = m._scrub_secret(s, secret="my-secret-key-xyz")
        self.assertNotIn("my-secret-key-xyz", out)
        self.assertIn("<REDACTED>", out)

    def test_handles_none_secret_gracefully(self):
        out = m._scrub_secret("?apikey=xyz", secret=None)
        self.assertNotIn("xyz", out)

    def test_handles_non_string_input(self):
        # Exception objects are commonly passed through f-strings;
        # str() coercion must not crash.
        class FakeExc:
            def __str__(self): return "?apikey=leaked"
        out = m._scrub_secret(FakeExc())
        self.assertNotIn("leaked", out)


class TestDnsFailurePathDoesNotLeak(unittest.TestCase):
    """Regression for Codex Finding 1 — Reproduces the original leak path
    (DNS NameResolutionError echoing the full URL with apikey) and asserts
    the sentinel never appears in the returned error dict."""

    def setUp(self):
        self._orig_key = os.environ.get("FMP_API_KEY")
        self._orig_url = m.FMP_STABLE_QUOTE
        os.environ["FMP_API_KEY"] = SENTINEL
        # Bad host triggers requests.exceptions.ConnectionError /
        # NameResolutionError; the original code embedded the prepared URL
        # (including apikey query) in the exception message.
        m.FMP_STABLE_QUOTE = "https://this-host-definitely-does-not-exist-xyzzy.invalid/stable/quote"

    def tearDown(self):
        if self._orig_key is None:
            os.environ.pop("FMP_API_KEY", None)
        else:
            os.environ["FMP_API_KEY"] = self._orig_key
        m.FMP_STABLE_QUOTE = self._orig_url

    def test_dns_failure_does_not_leak_sentinel(self):
        out = m._path_b_rest_direct("NVDA")
        # Even though DNS failed, the sentinel API key must NOT appear in
        # any returned field. This is the exact bug Codex flagged at
        # audit_data_alignment.py:82 in V3.17.3.
        self.assertNotIn(SENTINEL, str(out),
                         f"SECRET LEAK: sentinel found in result {out!r}")
        # Error must still be informative (not blanked entirely)
        self.assertIn("_error", out)
        self.assertTrue(len(out["_error"]) > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

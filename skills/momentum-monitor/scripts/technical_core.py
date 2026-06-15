#!/usr/bin/env python3
"""Shim — canonical implementation lives in skills/_shared/technical_core.py
(moved in the V4.5 audit cleanup). Kept so existing `from technical_core
import ...` sites (momentum.py, technical-analyst/analyze.py) work unchanged.
New code should import skills._shared.technical_core directly.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from skills._shared.technical_core import *  # noqa: F401,F403,E402

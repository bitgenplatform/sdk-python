"""The request timeout: seconds in the configuration, validated once."""

from __future__ import annotations

import math

DEFAULT = 30
"""Default, in seconds"""
MAX = 2_147_483
"""Largest value, in seconds — the same bound as the other BITGEN SDKs (a 32-bit number of milliseconds)"""

_MESSAGE = f"timeout must be a number of seconds between 0 (no timeout) and {MAX}"


def resolve(seconds: object) -> float:
    """`0` = no timeout. `ValueError` when not a finite number between 0 and 2147483, `TypeError` when not a number."""
    if isinstance(seconds, bool) or not isinstance(seconds, int | float):
        raise TypeError(_MESSAGE)
    if not math.isfinite(seconds) or seconds < 0 or seconds > MAX:
        raise ValueError(_MESSAGE)
    return float(seconds)

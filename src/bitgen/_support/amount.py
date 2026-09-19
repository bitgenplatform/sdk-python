"""Amounts always reach the API as strings: a string is sent as is (trimmed), an int, a finite float or a `Decimal` ≥ 0
in its plain decimal form. Nothing is ever rounded or reformatted — send crypto amounts (up to 18 decimals) as
strings."""

from __future__ import annotations

import math
from decimal import Decimal

_MESSAGE = "amount must be a non-empty string or a finite number >= 0"


def normalize(value: object) -> str:
    """`ValueError` on an empty string, a negative or non-finite number, or a float that Python would write in exponent
    notation (`1e-08`, `1e+21`: pass it as a decimal string); `TypeError` on anything that is not a string, an int, a
    float or a `Decimal` (a bool included)."""
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed == "":
            raise ValueError(_MESSAGE)
        return trimmed
    if isinstance(value, bool) or not isinstance(value, int | float | Decimal):
        raise TypeError(_MESSAGE)
    if isinstance(value, int):
        if value < 0:
            raise ValueError(_MESSAGE)
        return str(int(value))
    if isinstance(value, Decimal):
        if not value.is_finite() or value < 0:
            raise ValueError(_MESSAGE)
        # plain notation, never `1E-8`; the sign of a negative zero is dropped
        return "0" if value == 0 else format(value, "f")
    if not math.isfinite(value) or value < 0:
        raise ValueError(_MESSAGE)
    if value == 0:
        return "0"
    # shortest round-trip representation, as `repr` writes it (exponent notation below 1e-4 and from 1e16);
    # `float(value)` so that a subclass (`numpy.float64`) does not write its own name
    text = repr(float(value))
    if "e" in text or "E" in text:
        raise ValueError(f"amount {text} would be sent in exponent notation: pass it as a decimal string")
    return text.removesuffix(".0")

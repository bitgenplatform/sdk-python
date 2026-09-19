"""The single validation of the constant lists of the SDK (`Env.VALUES`, `Locale.VALUES`…)."""

from __future__ import annotations

from collections.abc import Sequence


def ensure(value: object, values: Sequence[str], name: str) -> str:
    """Returns `value` when it is one of `values`. A value outside the list is a caller's mistake, refused before any
    request — the value itself is never echoed: `ValueError("locale must be FR or EN")`; not a string → `TypeError`."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string, one of {_join(values)}")
    if value not in values:
        raise ValueError(f"{name} must be {_join(values)}")
    return value


def _join(values: Sequence[str]) -> str:
    """`A, B or C`"""
    if len(values) <= 1:
        return "".join(values)
    return ", ".join(values[:-1]) + " or " + values[-1]


def string(value: object, name: str) -> str:
    """A required string argument"""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def optional_string(value: object, name: str) -> str | None:
    """`None` (not sent) or a string"""
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def optional_int(value: object, name: str) -> int | None:
    """`None` (not sent) or an integer — a boolean is not one"""
    if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
        raise TypeError(f"{name} must be an integer")
    return value


def optional_bool(value: object, name: str) -> bool | None:
    """`None` (not sent) or a boolean"""
    if value is not None and not isinstance(value, bool):
        raise TypeError(f"{name} must be a boolean")
    return value


def optional_choice(value: object, values: Sequence[str], name: str) -> str | None:
    """`None` (not sent) or one of `values`"""
    return None if value is None else ensure(value, values, name)

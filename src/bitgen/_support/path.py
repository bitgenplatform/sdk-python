"""Path segments (`/asset/{asset}`, `/account/{user}`…): validated and encoded before they reach a URL."""

from __future__ import annotations

from urllib.parse import quote


def segment(value: object, name: str) -> str:
    """`ValueError` on an empty value or on `.` / `..` (which the URL would normalize away), `TypeError` on a
    non-string."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if value.strip() == "":
        raise ValueError(f"{name} must be a non-empty string")
    if value in (".", ".."):
        raise ValueError(f'{name} must not be "." or ".."')
    return quote(value, safe="")

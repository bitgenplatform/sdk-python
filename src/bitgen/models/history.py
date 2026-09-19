"""A time series of the API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from bitgen.models import _cast

Point = tuple[int, float]
"""One point of a time series: `(epoch seconds, value)`"""


@dataclass(frozen=True, slots=True)
class History:
    """`d` covers the last 24 hours with one point per hour, `w` and `m` one point per day, `y` and `all` one point per
    month. Each point is `(epoch seconds, value)`, the last one is the current value."""

    d: list[Point]
    w: list[Point]
    m: list[Point]
    y: list[Point]
    all: list[Point]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> History:
        return cls(
            d=_points(data, "d"),
            w=_points(data, "w"),
            m=_points(data, "m"),
            y=_points(data, "y"),
            all=_points(data, "all"),
        )


def _points(data: Mapping[str, Any], key: str) -> list[Point]:
    """`[epoch, value]` pairs — anything else is dropped"""
    points: list[Point] = []
    for point in _cast.items(data, key):
        if isinstance(point, list) and len(point) >= 2:
            pair = {"epoch": point[0], "value": point[1]}
            points.append((_cast.integer(pair, "epoch"), _cast.number(pair, "value")))
    return points

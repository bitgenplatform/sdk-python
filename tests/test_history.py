from __future__ import annotations

from bitgen.models import History


def test_points_are_epoch_and_value_pairs() -> None:
    history = History.from_dict(
        {"d": [[1700000000, 1.5], ["1700003600", "2"], [1, 2, 3], "x", [1]], "w": "nope", "y": [[1]], "extra": []}
    )
    assert history.d == [(1700000000, 1.5), (1700003600, 2.0), (1, 2.0)]
    assert history.w == []
    assert history.m == []
    assert history.y == []
    assert history.all == []
    assert History.from_dict({}) == History([], [], [], [], [])

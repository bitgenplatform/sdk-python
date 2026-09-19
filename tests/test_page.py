from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from bitgen import Page, UnexpectedAnswerError


def uuid_of(item: Mapping[str, Any]) -> str:
    return str(item["uuid"])


def test_maps_every_item() -> None:
    page = Page.from_dict({"count": 12, "items": [{"uuid": "a"}, {"uuid": "b"}]}, uuid_of)
    assert page.count == 12
    assert page.items == ["a", "b"]
    assert page == Page(12, ["a", "b"])


def test_missing_items_and_count_default() -> None:
    page = Page.from_dict({}, dict)
    assert page.count == 0
    assert page.items == []
    assert Page.from_dict({"items": [{"a": 1}]}, dict).count == 1
    # `null` counts as missing, as in the other SDKs
    assert Page.from_dict({"count": None, "items": None}, dict) == Page(0, [])
    assert Page.from_dict({"count": None, "items": [{"a": 1}]}, dict).count == 1


@pytest.mark.parametrize(
    "data",
    [
        {"count": 1, "items": "nope"},
        {"count": 1, "items": [1]},
        {"count": "1", "items": []},
        {"count": True, "items": []},
    ],
)
def test_malformed_pages_are_refused(data: dict[str, Any]) -> None:
    with pytest.raises(UnexpectedAnswerError):
        Page.from_dict(data, dict)


def test_pages_are_frozen() -> None:
    page = Page(1, ["a"])
    with pytest.raises(AttributeError):
        page.count = 2  # type: ignore[misc]

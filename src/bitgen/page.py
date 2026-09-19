"""A paginated list of the API: `{ count, items }`."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from bitgen.errors import UnexpectedAnswerError

T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    """`count` is the total number of items of the list, `items` the items of this page."""

    count: int
    items: list[T]

    @staticmethod
    def from_dict(data: Mapping[str, Any], item: Callable[[Mapping[str, Any]], U]) -> Page[U]:
        """Builds a page from the decoded answer, mapping every item with `item`. A missing (or `null`) `items` is an
        empty page, a missing (or `null`) `count` the number of items; anything that is not a list of objects is an
        `UnexpectedAnswerError`."""
        raw_items = data.get("items")
        if raw_items is None:
            raw_items = []
        if not isinstance(raw_items, list):
            raise UnexpectedAnswerError("the API answered a page whose items are not a list")
        items: list[U] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise UnexpectedAnswerError("the API answered a page with an item that is not an object")
            items.append(item(raw))
        count = data.get("count")
        if count is None:
            count = len(items)
        if isinstance(count, bool) or not isinstance(count, int):
            raise UnexpectedAnswerError("the API answered a page whose count is not an integer")
        return Page(count, items)

"""Reads the decoded answer of the API by key, cast to the type of the contract. A missing key or a value of another
type never raises: nullable fields become `None`, the others the empty value of their type. Only the top-level shape
of an answer is checked (`answer`, `answer_list`): the API promising an object and sending something else is a
contract violation, an `UnexpectedAnswerError`."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any, TypeVar

from bitgen.errors import UnexpectedAnswerError

T = TypeVar("T")


def string(data: Mapping[str, Any], key: str) -> str:
    text = nullable_string(data, key)
    return text if text is not None else ""


def nullable_string(data: Mapping[str, Any], key: str) -> str | None:
    value = data.get(key)
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return None


def integer(data: Mapping[str, Any], key: str) -> int:
    value = nullable_int(data, key)
    return value if value is not None else 0


def nullable_int(data: Mapping[str, Any], key: str) -> int | None:
    value = data.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    # a float, or a numeric string (`"7"`, `"1.5"`): truncated, as the other SDKs do
    parsed = nullable_number({"v": value}, "v")
    return int(parsed) if parsed is not None else None


def number(data: Mapping[str, Any], key: str) -> float:
    value = nullable_number(data, key)
    return value if value is not None else 0.0


def nullable_number(data: Mapping[str, Any], key: str) -> float | None:
    value = data.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        parsed = float(value)
    elif isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
    else:
        return None
    return parsed if math.isfinite(parsed) else None


def boolean(data: Mapping[str, Any], key: str) -> bool:
    value = data.get(key)
    if isinstance(value, str):
        return value not in ("", "0", "false")
    return bool(value)


def obj(data: Mapping[str, Any], key: str) -> dict[str, Any]:
    """A nested object — `{}` when missing or not an object"""
    return as_object(data.get(key))


def nullable_obj(data: Mapping[str, Any], key: str) -> dict[str, Any] | None:
    value = data.get(key)
    return as_object(value) if isinstance(value, dict) else None


def items(data: Mapping[str, Any], key: str) -> list[Any]:
    """A nested list — `[]` when missing or not a list"""
    value = data.get(key)
    return list(value) if isinstance(value, list) else []


def strings(data: Mapping[str, Any], key: str) -> list[str]:
    """A list of strings — non-scalar items are dropped"""
    result: list[str] = []
    for item in items(data, key):
        text = nullable_string({"v": item}, "v")
        if text is not None:
            result.append(text)
    return result


def string_map(data: Mapping[str, Any], key: str) -> dict[str, str]:
    """A map of strings (`Record<string, string>`) — non-scalar values are dropped"""
    result: dict[str, str] = {}
    for name, value in obj(data, key).items():
        text = nullable_string({"v": value}, "v")
        if text is not None:
            result[name] = text
    return result


def objects(data: Mapping[str, Any], key: str, item: Callable[[Mapping[str, Any]], T]) -> list[T]:
    """A list of objects, each mapped with `item` — the items that are not objects are skipped"""
    return [item(as_object(raw)) for raw in items(data, key) if isinstance(raw, dict)]


def raw(data: Mapping[str, Any], key: str) -> Any:
    """An opaque value, kept as decoded — `None` when missing"""
    return data.get(key)


def answer(value: object) -> dict[str, Any]:
    """The decoded answer of the API, which must be a JSON object"""
    if not isinstance(value, dict):
        raise UnexpectedAnswerError(f"the API answered {_kind(value)} instead of a JSON object")
    return as_object(value)


def answer_list(value: object) -> list[dict[str, Any]]:
    """The decoded answer of the API, which must be a JSON array of objects"""
    if not isinstance(value, list):
        raise UnexpectedAnswerError(f"the API answered {_kind(value)} instead of a JSON array")
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise UnexpectedAnswerError("the API answered a list with an item that is not an object")
        result.append(as_object(item))
    return result


def as_object(value: object) -> dict[str, Any]:
    """Any decoded value as a dict with string keys — `{}` when it is not an object"""
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _kind(value: object) -> str:
    """What the API sent instead, for the message — never the value itself"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "a boolean"
    if isinstance(value, int | float):
        return "a number"
    if isinstance(value, str):
        return "a string"
    if isinstance(value, list):
        return "a JSON array"
    return "a JSON object"

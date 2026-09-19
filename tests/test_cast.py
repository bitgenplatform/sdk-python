from __future__ import annotations

from typing import Any

import pytest

from bitgen import UnexpectedAnswerError
from bitgen.models import _cast

DATA: dict[str, Any] = {
    "s": "text",
    "n": 12,
    "f": 1.5,
    "numeric": "7",
    "decimal": "1.5",
    "b": True,
    "nothing": None,
    "list": [1, 2],
    "nan": float("nan"),
}


def test_scalars_are_cast_and_missing_ones_get_the_empty_value() -> None:
    assert _cast.string(DATA, "s") == "text"
    assert _cast.string(DATA, "n") == "12"
    assert _cast.string(DATA, "b") == "true"
    assert _cast.string(DATA, "missing") == ""
    assert _cast.string(DATA, "list") == ""
    assert _cast.nullable_string(DATA, "s") == "text"
    assert _cast.nullable_string(DATA, "nothing") is None
    assert _cast.nullable_string(DATA, "missing") is None
    assert _cast.integer(DATA, "n") == 12
    assert _cast.integer(DATA, "numeric") == 7
    assert _cast.integer(DATA, "decimal") == 1
    assert _cast.integer(DATA, "f") == 1
    assert _cast.integer(DATA, "missing") == 0
    assert _cast.integer(DATA, "s") == 0
    assert _cast.integer(DATA, "b") == 0
    assert _cast.integer(DATA, "nan") == 0
    assert _cast.nullable_int(DATA, "n") == 12
    assert _cast.nullable_int(DATA, "missing") is None
    assert _cast.nullable_int(DATA, "b") is None
    assert _cast.number(DATA, "f") == 1.5
    assert _cast.number(DATA, "n") == 12.0
    assert _cast.number(DATA, "decimal") == 1.5
    assert _cast.number(DATA, "missing") == 0.0
    assert _cast.number(DATA, "nan") == 0.0
    assert _cast.nullable_number(DATA, "f") == 1.5
    assert _cast.nullable_number(DATA, "nothing") is None
    assert _cast.nullable_number(DATA, "b") is None
    assert _cast.boolean(DATA, "b") is True
    assert _cast.boolean(DATA, "missing") is False
    assert _cast.boolean({"v": "false"}, "v") is False
    assert _cast.boolean({"v": "0"}, "v") is False
    assert _cast.boolean({"v": "yes"}, "v") is True
    assert _cast.boolean({"v": 1}, "v") is True
    assert _cast.raw(DATA, "list") == [1, 2]
    assert _cast.raw(DATA, "missing") is None


def test_objects_and_lists() -> None:
    data: dict[str, Any] = {"o": {"a": 1, 0: "zero"}, "l": ["x", {"uuid": "u"}, 3], "nope": "text"}
    assert _cast.obj(data, "o") == {"a": 1, "0": "zero"}
    assert _cast.obj(data, "nope") == {}
    assert _cast.obj(data, "missing") == {}
    assert _cast.nullable_obj(data, "o") == {"a": 1, "0": "zero"}
    assert _cast.nullable_obj(data, "missing") is None
    assert _cast.items(data, "l") == ["x", {"uuid": "u"}, 3]
    assert _cast.items(data, "nope") == []
    assert _cast.items(data, "o") == []
    # objects(): only the items that are objects are mapped
    assert _cast.objects(data, "l", lambda item: str(item["uuid"])) == ["u"]
    assert _cast.as_object({"a": 1}) == {"a": 1}
    assert _cast.as_object(["a", "b"]) == {}
    assert _cast.as_object("text") == {}


def test_strings_and_string_map_keep_scalars_only() -> None:
    assert _cast.strings({"l": ["a", 1, 2.5, True, None, ["x"], {"y": 1}]}, "l") == ["a", "1", "2.5", "true"]
    assert _cast.strings({"l": "text"}, "l") == []
    assert _cast.string_map({"label": {"fr": "Taux", "en": "Rate", "n": 1, "x": ["nested"], "y": None}}, "label") == {
        "fr": "Taux",
        "en": "Rate",
        "n": "1",
    }
    assert _cast.string_map({"label": "text"}, "label") == {}


def test_answer_and_answer_list_check_the_shape_of_the_answer() -> None:
    assert _cast.answer({"uuid": "u"}) == {"uuid": "u"}
    assert _cast.answer_list([{"uuid": "u"}, {}]) == [{"uuid": "u"}, {}]
    assert _cast.answer_list([]) == []
    cases: list[tuple[object, str]] = [
        (None, "null"),
        (True, "a boolean"),
        (3, "a number"),
        ("s", "a string"),
        ([], "a JSON array"),
    ]
    for value, kind in cases:
        with pytest.raises(UnexpectedAnswerError, match=rf"^the API answered {kind} instead of a JSON object$"):
            _cast.answer(value)
    with pytest.raises(UnexpectedAnswerError, match=r"^the API answered a JSON object instead of a JSON array$"):
        _cast.answer_list({})
    with pytest.raises(UnexpectedAnswerError, match=r"^the API answered a list with an item that is not an object$"):
        _cast.answer_list([{"a": 1}, "b"])

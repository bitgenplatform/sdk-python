from __future__ import annotations

import pytest

from bitgen._support import values


def test_a_value_of_the_list_passes() -> None:
    assert values.ensure("FR", ("FR", "EN"), "locale") == "FR"
    assert values.ensure("only", ("only",), "x") == "only"


def test_a_value_outside_the_list_is_refused_without_being_echoed() -> None:
    with pytest.raises(ValueError, match=r"^locale must be FR or EN$"):
        values.ensure("SECRET", ("FR", "EN"), "locale")
    with pytest.raises(ValueError, match=r"^env must be production, sandbox, staging or localhost$"):
        values.ensure("prod", ("production", "sandbox", "staging", "localhost"), "env")
    with pytest.raises(ValueError, match=r"^x must be only$"):
        values.ensure("other", ("only",), "x")
    with pytest.raises(TypeError, match=r"^locale must be a string, one of FR or EN$"):
        values.ensure(None, ("FR", "EN"), "locale")


def test_argument_types_are_checked_at_runtime() -> None:
    # the equivalent of PHP's strict types: a wrong type is a TypeError before any request
    assert values.string("s", "email") == "s"
    assert values.optional_string(None, "fin") is None
    assert values.optional_string("FIN", "fin") == "FIN"
    assert values.optional_int(None, "offset") is None
    assert values.optional_int(0, "offset") == 0
    assert values.optional_bool(None, "notify") is None
    assert values.optional_bool(False, "notify") is False
    assert values.optional_choice(None, ("FR", "EN"), "locale") is None
    assert values.optional_choice("EN", ("FR", "EN"), "locale") == "EN"
    not_strings: list[object] = [None, 1, b"s", ["s"]]
    for wrong in not_strings:
        with pytest.raises(TypeError, match=r"^email must be a string$"):
            values.string(wrong, "email")
    for wrong in not_strings[1:]:
        with pytest.raises(TypeError, match=r"^fin must be a string$"):
            values.optional_string(wrong, "fin")
    not_ints: list[object] = ["0", 1.5, True, [1]]  # a bool is an int for Python, not for the SDK
    for wrong in not_ints:
        with pytest.raises(TypeError, match=r"^offset must be an integer$"):
            values.optional_int(wrong, "offset")
    not_bools: list[object] = ["false", 0, 1, "yes"]
    for wrong in not_bools:
        with pytest.raises(TypeError, match=r"^notify must be a boolean$"):
            values.optional_bool(wrong, "notify")
    with pytest.raises(ValueError, match=r"^locale must be FR or EN$"):
        values.optional_choice("en", ("FR", "EN"), "locale")
    with pytest.raises(TypeError, match=r"^locale must be a string, one of FR or EN$"):
        values.optional_choice(1, ("FR", "EN"), "locale")

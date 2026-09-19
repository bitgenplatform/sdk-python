"""Every constant class of the SDK (`Env`, `Asset` and the ones of `bitgen.models`), by reflection: frozen, never
instantiated, `VALUES` = every public constant in the order of its definition, without duplicate — the Python
counterpart of the PHP `EnumTest`. A class added later is checked without touching this file."""

from __future__ import annotations

import pytest

import bitgen
import bitgen.models
from bitgen._support.constants import ConstantsMeta


def constant_classes() -> list[type]:
    found: list[type] = []
    for module in (bitgen, bitgen.models):
        for name in module.__all__:
            candidate = getattr(module, name)
            if isinstance(candidate, ConstantsMeta):
                found.append(candidate)
    return found


def test_the_constant_classes_are_found() -> None:
    names = {cls.__name__ for cls in constant_classes()}
    assert {"Env", "Asset", "AssetState"} <= names


@pytest.mark.parametrize("cls", constant_classes(), ids=lambda cls: str(cls.__name__))
def test_values_list_every_constant_in_order_without_duplicate(cls: type) -> None:
    constants = [name for name in vars(cls) if name.isupper() and name != "VALUES"]
    values = [getattr(cls, name) for name in constants]
    assert constants, cls
    assert all(isinstance(value, str) and value != "" for value in values), cls
    listed = getattr(cls, "VALUES")  # noqa: B009 - the class is reflected, its attributes are not typed here
    assert isinstance(listed, tuple), cls
    assert list(listed) == values, cls
    assert len(set(values)) == len(values), cls


@pytest.mark.parametrize("cls", constant_classes(), ids=lambda cls: str(cls.__name__))
def test_frozen_and_never_instantiated(cls: type) -> None:
    with pytest.raises(AttributeError, match="cannot be changed"):
        setattr(cls, "VALUES", ())  # noqa: B010 - reflected class
    with pytest.raises(AttributeError, match="cannot be removed"):
        delattr(cls, "VALUES")
    with pytest.raises(TypeError, match="is not instantiated"):
        cls()

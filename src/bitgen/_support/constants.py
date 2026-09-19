"""The metaclass of the constant classes of the SDK (`Env`, `Asset`, `Locale`…): frozen and never instantiated."""

from __future__ import annotations

from typing import NoReturn


class ConstantsMeta(type):
    """A class of string constants: `Env.SANDBOX` is `"sandbox"`, `Env.VALUES` lists every value in the order of the
    API contract. The class is frozen (no value can be replaced or removed) and is not instantiated."""

    def __setattr__(cls, name: str, value: object) -> None:
        raise AttributeError(f"{cls.__name__} is a constant class: its values cannot be changed")

    def __delattr__(cls, name: str) -> None:
        raise AttributeError(f"{cls.__name__} is a constant class: its values cannot be removed")

    def __call__(cls, *args: object, **kwargs: object) -> NoReturn:
        raise TypeError(f"{cls.__name__} is a constant class: it is not instantiated")

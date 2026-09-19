"""`Env` and `Asset`: values, order, frozen, never instantiated."""

from __future__ import annotations

import pytest

from bitgen import Asset, Env


def test_values_in_the_order_of_the_contract() -> None:
    assert Env.VALUES == ("production", "sandbox", "staging", "localhost")
    assert (Env.PRODUCTION, Env.SANDBOX, Env.STAGING, Env.LOCALHOST) == Env.VALUES
    assert Asset.VALUES == ("btc", "eth", "usdc", "xrp", "sol")
    assert (Asset.BTC, Asset.ETH, Asset.USDC, Asset.XRP, Asset.SOL) == Asset.VALUES
    assert isinstance(Env.SANDBOX, str)
    assert isinstance(Env.VALUES, tuple)


def test_constant_classes_are_frozen_and_not_instantiated() -> None:
    for constants in (Env, Asset):
        with pytest.raises(AttributeError, match="cannot be changed"):
            constants.VALUES = ()  # type: ignore[misc]
        with pytest.raises(AttributeError, match="cannot be changed"):
            constants.NEW = "x"
        with pytest.raises(AttributeError, match="cannot be removed"):
            del constants.VALUES
        with pytest.raises(TypeError, match="is not instantiated"):
            constants()
    assert Env.VALUES == ("production", "sandbox", "staging", "localhost")

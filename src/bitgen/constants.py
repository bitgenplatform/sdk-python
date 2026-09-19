"""The constant classes of the SDK: `Env`, the environments, and `Asset`, the ISO codes of the main assets. Each value
is a plain string (`Env.SANDBOX` is `"sandbox"`); `VALUES` lists them in the order of the API contract."""

from __future__ import annotations

from typing import Final

from bitgen._support.constants import ConstantsMeta


class Env(metaclass=ConstantsMeta):
    """Target environment — `BitgenClient(env=Env.SANDBOX, …)`; the constants are the strings the API knows
    (`Env.VALUES`)."""

    PRODUCTION: Final = "production"
    SANDBOX: Final = "sandbox"
    STAGING: Final = "staging"
    LOCALHOST: Final = "localhost"

    VALUES: Final[tuple[str, ...]] = (PRODUCTION, SANDBOX, STAGING, LOCALHOST)
    """Every value, in the order of the contract"""


class Asset(metaclass=ConstantsMeta):
    """ISO codes of the main assets, as string constants (`Asset.ETH` is `"eth"`), accepted wherever an asset is
    expected (the API takes a uuid or an iso in any case). The `iso` returned by the API has its stored case (`ETH`
    today): compare it case-insensitively. Provisional list — extended once the production list is confirmed."""

    BTC: Final = "btc"
    ETH: Final = "eth"
    USDC: Final = "usdc"
    XRP: Final = "xrp"
    SOL: Final = "sol"

    VALUES: Final[tuple[str, ...]] = (BTC, ETH, USDC, XRP, SOL)
    """Every value, in the order of the contract"""

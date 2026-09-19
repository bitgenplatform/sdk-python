"""The models of the `asset` resource: the catalogue of assets, their tickers and EUR price histories."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from bitgen._support.constants import ConstantsMeta
from bitgen.models import _cast
from bitgen.models.history import History


class AssetState(metaclass=ConstantsMeta):
    """The states of an asset the contract lists — `Asset.state` is a string, compare it with `AssetState.AVAILABLE`"""

    AVAILABLE: Final = "AVAILABLE"
    UNAVAILABLE: Final = "UNAVAILABLE"
    ARCHIVED: Final = "ARCHIVED"
    HIDDEN: Final = "HIDDEN"

    VALUES: Final[tuple[str, ...]] = (AVAILABLE, UNAVAILABLE, ARCHIVED, HIDDEN)
    """Every value, in the order of the contract"""


@dataclass(frozen=True, slots=True)
class AssetRef:
    """The asset of a wallet, an order… — `{ uuid, iso, label }`. `iso` has the case the API stores: compare it
    case-insensitively."""

    uuid: str
    iso: str
    label: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AssetRef:
        return cls(uuid=_cast.string(data, "uuid"), iso=_cast.string(data, "iso"), label=_cast.string(data, "label"))


@dataclass(frozen=True, slots=True)
class AssetTicker:
    """Live market data of an asset — `price` and `marketcap` in EUR, `percentChange24h` in %"""

    price: float
    marketcap: float
    rank: int
    percentChange24h: float

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AssetTicker:
        return cls(
            price=_cast.number(data, "price"),
            marketcap=_cast.number(data, "marketcap"),
            rank=_cast.integer(data, "rank"),
            percentChange24h=_cast.number(data, "percentChange24h"),
        )


@dataclass(frozen=True, slots=True)
class AssetFeesComputed:
    """Gas cost of a transfer: `gas` in the smallest unit of the native coin, `native` in native coin units"""

    gas: str
    native: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AssetFeesComputed:
        return cls(gas=_cast.string(data, "gas"), native=_cast.string(data, "native"))


@dataclass(frozen=True, slots=True)
class AssetFees:
    """`low`, `medium`, `high`: the raw fee schedule of the gas provider, opaque"""

    low: Any
    medium: Any
    high: Any
    computed: AssetFeesComputed

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AssetFees:
        return cls(
            low=_cast.raw(data, "low"),
            medium=_cast.raw(data, "medium"),
            high=_cast.raw(data, "high"),
            computed=AssetFeesComputed.from_dict(_cast.obj(data, "computed")),
        )


@dataclass(frozen=True, slots=True)
class AssetNetworkType:
    """The family of a network (`code`: `UTXO`, `EVM`, `COMPUTE_UNIT`, `DROPS`) — `data` is an internal connector
    mapping, raw JSON"""

    uuid: str
    code: str
    label: str
    data: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AssetNetworkType:
        return cls(
            uuid=_cast.string(data, "uuid"),
            code=_cast.string(data, "code"),
            label=_cast.string(data, "label"),
            data=_cast.string(data, "data"),
        )


@dataclass(frozen=True, slots=True)
class AssetNetwork:
    """The network of an asset — `caip2` is the chain identifier (`eip155:1`), `data` an internal connector mapping,
    raw JSON"""

    uuid: str
    state: str
    caip2: str
    label: str
    gasBase: int
    data: str
    type: AssetNetworkType

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AssetNetwork:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            caip2=_cast.string(data, "caip2"),
            label=_cast.string(data, "label"),
            gasBase=_cast.integer(data, "gasBase"),
            data=_cast.string(data, "data"),
            type=AssetNetworkType.from_dict(_cast.obj(data, "type")),
        )


@dataclass(frozen=True, slots=True)
class Asset:
    """An asset of the catalogue. `iso` has the case the API stores (`ETH` today): compare it case-insensitively.
    `baseUnit` is the number of decimals an amount may carry."""

    uuid: str
    state: str
    """`AssetState` lists the known values: `AVAILABLE`, `UNAVAILABLE`, `ARCHIVED`, `HIDDEN` — a value the contract does
    not list yet is kept as is"""
    iso: str
    label: str
    contractAddress: str
    """`""` for a native asset, never `None`"""
    baseUnit: int
    gasUnit: int
    logo: str | None
    data: str
    """Internal connector mapping, raw JSON"""
    fees: AssetFees
    ticker: AssetTicker
    history: History
    """EUR price"""
    network: AssetNetwork

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Asset:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            iso=_cast.string(data, "iso"),
            label=_cast.string(data, "label"),
            contractAddress=_cast.string(data, "contractAddress"),
            baseUnit=_cast.integer(data, "baseUnit"),
            gasUnit=_cast.integer(data, "gasUnit"),
            logo=_cast.nullable_string(data, "logo"),
            data=_cast.string(data, "data"),
            fees=AssetFees.from_dict(_cast.obj(data, "fees")),
            ticker=AssetTicker.from_dict(_cast.obj(data, "ticker")),
            history=History.from_dict(_cast.obj(data, "history")),
            network=AssetNetwork.from_dict(_cast.obj(data, "network")),
        )


@dataclass(frozen=True, slots=True)
class AssetTickerItem:
    """An item of `tickers()`: the `iso` of an asset and its ticker"""

    iso: str
    ticker: AssetTicker

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AssetTickerItem:
        return cls(iso=_cast.string(data, "iso"), ticker=AssetTicker.from_dict(_cast.obj(data, "ticker")))


@dataclass(frozen=True, slots=True)
class AssetTickerDetail:
    """`ticker(iso)`: the ticker of an asset and its EUR price history"""

    iso: str
    ticker: AssetTicker
    history: History

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AssetTickerDetail:
        return cls(
            iso=_cast.string(data, "iso"),
            ticker=AssetTicker.from_dict(_cast.obj(data, "ticker")),
            history=History.from_dict(_cast.obj(data, "history")),
        )

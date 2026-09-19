"""The models of the `trading` resource: orders."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from bitgen._support.constants import ConstantsMeta
from bitgen.models import _cast
from bitgen.models.asset import AssetRef
from bitgen.models.customer import OrderUser


class OrderState(metaclass=ConstantsMeta):
    """The states of an order the contract lists — `Order.state` is a string, compare it with `OrderState.DONE`.
    A purchase goes `REGISTERED` → `EXECUTING` → `FILLED` → `DELIVERING` → `DONE`; a sale `REGISTERED` →
    `TRANSFERRING` → `DEPOSITED` → `EXECUTING` → `FILLED` → `DONE`. `PARKED`: executed but nothing was received
    (terminal); `FAILED`."""

    REGISTERED: Final = "REGISTERED"
    TRANSFERRING: Final = "TRANSFERRING"
    DEPOSITED: Final = "DEPOSITED"
    EXECUTING: Final = "EXECUTING"
    FILLED: Final = "FILLED"
    DELIVERING: Final = "DELIVERING"
    DONE: Final = "DONE"
    PARKED: Final = "PARKED"
    FAILED: Final = "FAILED"

    VALUES: Final[tuple[str, ...]] = (
        REGISTERED,
        TRANSFERRING,
        DEPOSITED,
        EXECUTING,
        FILLED,
        DELIVERING,
        DONE,
        PARKED,
        FAILED,
    )
    """Every value, in the order of the contract"""


class OrderSide(metaclass=ConstantsMeta):
    """The side of an order — `Order.side` is a string, compare it with `OrderSide.BUY`"""

    BUY: Final = "BUY"
    SELL: Final = "SELL"

    VALUES: Final[tuple[str, ...]] = (BUY, SELL)
    """Every value, in the order of the contract"""


class TradingDirection(metaclass=ConstantsMeta):
    """Filter of the orders list (`client.trading.list()`): only purchases, or only sales — lowercase, as the API
    expects it"""

    BUY: Final = "buy"
    SELL: Final = "sell"

    VALUES: Final[tuple[str, ...]] = (BUY, SELL)
    """Every value, in the order of the contract"""


@dataclass(frozen=True, slots=True)
class OrderOrganization:
    """The organization of an order — `{ uuid, name }`"""

    uuid: str
    name: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> OrderOrganization:
        return cls(uuid=_cast.string(data, "uuid"), name=_cast.string(data, "name"))


@dataclass(frozen=True, slots=True)
class OrderCreated:
    """`client.trading.buy()` / `sell()` — the uuid of the order (`tunnel`) and its initial state"""

    tunnel: str
    """The uuid of the order: read it with `client.trading.get()`"""
    state: str
    """`OrderState` lists the known values"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> OrderCreated:
        return cls(tunnel=_cast.string(data, "tunnel"), state=_cast.string(data, "state"))


@dataclass(frozen=True, slots=True)
class Order:
    """A trading order: a purchase or a sale of crypto for a customer"""

    uuid: str
    """The order — the `tunnel` returned by `buy` / `sell`"""
    state: str
    """`OrderState` lists the known values: `REGISTERED`, `TRANSFERRING`, `DEPOSITED`, `EXECUTING`, `FILLED`,
    `DELIVERING`, `DONE`, `PARKED`, `FAILED`"""
    side: str
    """`BUY` or `SELL` (`OrderSide`)"""
    amount: str
    """What was asked, as a string: EUR for a purchase (`"25.00"`), a crypto quantity for a sale"""
    reference: str | None
    """The idempotency key given, or `None`"""
    received: float | None
    """What the customer got, or `None`: the crypto quantity for a purchase, the EUR credited for a sale"""
    executedPrice: float | None
    """The EUR price of the token, or `None`"""
    fee: float | None
    """Exchange fee, in EUR, or `None`"""
    completedAt: int | None
    """Epoch seconds — `None` until the order completes"""
    createdAt: int
    """Epoch seconds"""
    user: OrderUser
    organization: OrderOrganization
    asset: AssetRef

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Order:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            side=_cast.string(data, "side"),
            amount=_cast.string(data, "amount"),
            reference=_cast.nullable_string(data, "reference"),
            received=_cast.nullable_number(data, "received"),
            executedPrice=_cast.nullable_number(data, "executedPrice"),
            fee=_cast.nullable_number(data, "fee"),
            completedAt=_cast.nullable_int(data, "completedAt"),
            createdAt=_cast.integer(data, "createdAt"),
            user=OrderUser.from_dict(_cast.obj(data, "user")),
            organization=OrderOrganization.from_dict(_cast.obj(data, "organization")),
            asset=AssetRef.from_dict(_cast.obj(data, "asset")),
        )

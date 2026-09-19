"""The models of the `bank` resource: the EUR account of a customer and its operations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from bitgen._support.constants import ConstantsMeta
from bitgen.models import _cast
from bitgen.models.history import History


class BankDirection(metaclass=ConstantsMeta):
    """Filter of the EUR operations — `ALL` (default), or one kind"""

    ALL: Final = "ALL"
    DEPOSIT: Final = "DEPOSIT"
    WITHDRAWAL: Final = "WITHDRAWAL"
    PURCHASE: Final = "PURCHASE"
    SELL: Final = "SELL"

    VALUES: Final[tuple[str, ...]] = (ALL, DEPOSIT, WITHDRAWAL, PURCHASE, SELL)
    """Every value, in the order of the contract"""


@dataclass(frozen=True, slots=True)
class BankPending:
    """EUR pending on an account: incoming not credited yet, outgoing not confirmed yet"""

    in_: float
    """`in` in the contract — `in` is a reserved word in Python"""
    out: float

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BankPending:
        return cls(in_=_cast.number(data, "in"), out=_cast.number(data, "out"))


@dataclass(frozen=True, slots=True)
class BankAccount:
    """The EUR account of a customer (`client.bank.get()`), created on first read"""

    uuid: str
    message: str
    """The wire transfer reference the customer must indicate (`BTGN` prefix)"""
    iban: str | None
    bank: str | None
    bic: str | None
    balance: float
    """EUR"""
    history: History | None
    """EUR balance curve, materialized every hour — `None` until it has run for this account"""
    pending: BankPending

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BankAccount:
        history = _cast.obj(data, "history")
        return cls(
            uuid=_cast.string(data, "uuid"),
            message=_cast.string(data, "message"),
            iban=_cast.nullable_string(data, "iban"),
            bank=_cast.nullable_string(data, "bank"),
            bic=_cast.nullable_string(data, "bic"),
            balance=_cast.number(data, "balance"),
            history=History.from_dict(history) if history else None,
            pending=BankPending.from_dict(_cast.obj(data, "pending")),
        )


@dataclass(frozen=True, slots=True)
class BankOperation:
    """One EUR operation of an account (`client.bank.operations()`)"""

    txId: str
    """Identifier of the ledger entry"""
    amount: float
    """EUR"""
    direction: str
    """`DEPOSIT`, `WITHDRAWAL`, `PURCHASE` or `SELL` (`BankDirection`)"""
    date: int
    info: str | None
    """Free label of the operation — for instance the asset bought or sold"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BankOperation:
        return cls(
            txId=_cast.string(data, "txId"),
            amount=_cast.number(data, "amount"),
            direction=_cast.string(data, "direction"),
            date=_cast.integer(data, "date"),
            info=_cast.nullable_string(data, "info"),
        )


@dataclass(frozen=True, slots=True)
class BankWithdrawal:
    """`client.bank.withdraw()` — the identifier of the transaction created for the withdrawal"""

    transaction: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BankWithdrawal:
        return cls(transaction=_cast.string(data, "transaction"))

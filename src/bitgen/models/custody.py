"""The models of the `custody` resource: wallets, the EUR value of a custody, on-chain withdrawals and their travel
rule."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from bitgen._support.constants import ConstantsMeta
from bitgen.models import _cast
from bitgen.models.asset import AssetRef
from bitgen.models.history import History


class WalletState(metaclass=ConstantsMeta):
    """The states of a wallet the contract lists — `Wallet.state` is a string, compare it with `WalletState.FROZEN`"""

    CREATED: Final = "CREATED"
    FROZEN: Final = "FROZEN"

    VALUES: Final[tuple[str, ...]] = (CREATED, FROZEN)
    """Every value, in the order of the contract"""


class WalletType(metaclass=ConstantsMeta):
    """`USER`: the wallet of a customer — `TREASURY`: a wallet of the organization itself (read-only). `Wallet.type` is
    a string."""

    USER: Final = "USER"
    TREASURY: Final = "TREASURY"

    VALUES: Final[tuple[str, ...]] = (USER, TREASURY)
    """Every value, in the order of the contract"""


@dataclass(frozen=True, slots=True)
class Wallet:
    """A custody wallet: the crypto of a customer (or of the organization) for one asset, at the custodian"""

    uuid: str
    state: str
    """`WalletState` lists the known values: `CREATED`, `FROZEN`"""
    type: str
    """`WalletType` lists the known values: `USER` (a customer), `TREASURY` (the organization, read-only)"""
    address: str | None
    """Deposit address"""
    addressLegacy: str | None
    """The same deposit address in the legacy format of the chain, when the network has two"""
    tag: str | None
    """Memo / tag of the address (XRP, XLM…)"""
    balance: str
    """Exact quantity, as a string"""
    history: History | None
    """EUR value curve — only on the unit read (`client.custody.wallet()`): `None` in the list, and until it has been
    computed for a new wallet"""
    asset: AssetRef

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Wallet:
        history = _cast.obj(data, "history")
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            type=_cast.string(data, "type"),
            address=_cast.nullable_string(data, "address"),
            addressLegacy=_cast.nullable_string(data, "addressLegacy"),
            tag=_cast.nullable_string(data, "tag"),
            balance=_cast.string(data, "balance"),
            history=History.from_dict(history) if history else None,
            asset=AssetRef.from_dict(_cast.obj(data, "asset")),
        )


@dataclass(frozen=True, slots=True)
class CustodyPortfolio:
    """The EUR value curve of the whole custody of a customer (`client.custody.portfolio()`): `{ uuid, type, history }`,
    or a flat `{ history }` at zero — `uuid` and `type` `None` — while the customer has no custody yet."""

    uuid: str | None
    """The custody account of the customer — `None` while they have no custody"""
    type: str | None
    """`WalletType` lists the known values: `USER`, `TREASURY` — `None` while the customer has no custody"""
    history: History
    """EUR value of the custody"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CustodyPortfolio:
        return cls(
            uuid=_cast.nullable_string(data, "uuid"),
            type=_cast.nullable_string(data, "type"),
            history=History.from_dict(_cast.obj(data, "history")),
        )


@dataclass(frozen=True, slots=True)
class CustodyWithdrawal:
    """`client.custody.withdraw()` — the uuid of the transaction created for the withdrawal, `None` while the analysis
    has not created it yet"""

    transaction: str | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CustodyWithdrawal:
        return cls(transaction=_cast.nullable_string(data, "transaction"))


@dataclass(frozen=True, slots=True)
class TravelRulePerson:
    """The destination of a withdrawal is a person — `{ firstname?, lastname?, address? }`, at least one of them
    (255 characters max per field, checked by the API)"""

    firstname: str | None = None
    lastname: str | None = None
    address: str | None = None

    def __post_init__(self) -> None:
        for name in ("firstname", "lastname", "address"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{name} must be a string")
        if self.firstname is None and self.lastname is None and self.address is None:
            raise ValueError("a TravelRulePerson needs at least one of firstname, lastname or address")

    def to_dict(self) -> dict[str, str]:
        """The `travelRule` object of the request body"""
        fields = {"firstname": self.firstname, "lastname": self.lastname, "address": self.address}
        return {key: value for key, value in fields.items() if value is not None}


@dataclass(frozen=True, slots=True)
class TravelRulePlatform:
    """The destination of a withdrawal is a platform (an exchange, a custodian…) — `{ platform }`"""

    platform: str

    def __post_init__(self) -> None:
        if not isinstance(self.platform, str):
            raise TypeError("platform must be a string")

    def to_dict(self) -> dict[str, str]:
        """The `travelRule` object of the request body"""
        return {"platform": self.platform}


TravelRule = TravelRulePerson | TravelRulePlatform
"""Travel rule information on the destination of an on-chain withdrawal: a person or a platform — one form or the
other"""

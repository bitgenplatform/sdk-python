"""The models of the `staking` resource: movements, positions, operations and the EUR portfolio."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from bitgen._support.constants import ConstantsMeta
from bitgen.models import _cast
from bitgen.models.asset import AssetRef
from bitgen.models.core import CoreRef
from bitgen.models.customer import UserSummary
from bitgen.models.history import History
from bitgen.models.organization import OrganizationSummary


class StakingMovementState(metaclass=ConstantsMeta):
    """The states of a staking movement the contract lists — `StakingMovement.state` is a string"""

    REQUESTED: Final = "REQUESTED"
    PENDING: Final = "PENDING"
    COMPLETED: Final = "COMPLETED"
    FAILED: Final = "FAILED"
    CANCELED: Final = "CANCELED"

    VALUES: Final[tuple[str, ...]] = (REQUESTED, PENDING, COMPLETED, FAILED, CANCELED)
    """Every value, in the order of the contract"""


class StakingMovementKind(metaclass=ConstantsMeta):
    """The kinds of staking movements — `StakingMovement.kind` is a string; also the `direction` filter of the lists"""

    STAKE: Final = "STAKE"
    UNSTAKE: Final = "UNSTAKE"
    WITHDRAW: Final = "WITHDRAW"
    REWARD: Final = "REWARD"

    VALUES: Final[tuple[str, ...]] = (STAKE, UNSTAKE, WITHDRAW, REWARD)
    """Every value, in the order of the contract"""


class StakingPositionState(metaclass=ConstantsMeta):
    """The states of a staking position the contract lists — `StakingPosition.state` is a string"""

    CREATED: Final = "CREATED"
    ENABLED: Final = "ENABLED"
    UNSTAKING: Final = "UNSTAKING"
    CLOSED: Final = "CLOSED"
    FAILED: Final = "FAILED"

    VALUES: Final[tuple[str, ...]] = (CREATED, ENABLED, UNSTAKING, CLOSED, FAILED)
    """Every value, in the order of the contract"""


@dataclass(frozen=True, slots=True)
class StakingPositionData:
    """What the provider reports on a position — `{ rewards?, lastRewardAt? }`"""

    rewards: str | None
    """Rewards accrued and available, in asset units, as a string — when available"""
    lastRewardAt: int | None
    """Epoch seconds of the last daily accrual — when available"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> StakingPositionData:
        return cls(
            rewards=_cast.nullable_string(data, "rewards"), lastRewardAt=_cast.nullable_int(data, "lastRewardAt")
        )


@dataclass(frozen=True, slots=True)
class StakingPosition:
    """The position carried by a movement: the capital placed with a provider — its `uuid` is what `rewards` /
    `unstake` take"""

    uuid: str
    state: str
    """`StakingPositionState` lists the known values: `CREATED`, `ENABLED`, `UNSTAKING`, `CLOSED`, `FAILED`"""
    amount: str
    """Net capital placed, as a string"""
    error: str | None
    """Failure reason when `FAILED`"""
    data: StakingPositionData
    createdAt: int
    updatedAt: int
    core: CoreRef
    """The provider"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> StakingPosition:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            amount=_cast.string(data, "amount"),
            error=_cast.nullable_string(data, "error"),
            data=StakingPositionData.from_dict(_cast.obj(data, "data")),
            createdAt=_cast.integer(data, "createdAt"),
            updatedAt=_cast.integer(data, "updatedAt"),
            core=CoreRef.from_dict(_cast.obj(data, "core")),
        )


@dataclass(frozen=True, slots=True)
class StakingMovement:
    """A staking request — stake, rewritten into the exit when the position is left entirely — attached to a position.
    Its `uuid` is what `stake` returns and `get` / `list` / `movements` handle."""

    uuid: str
    state: str
    """`StakingMovementState` lists the known values: `REQUESTED`, `PENDING`, `COMPLETED`, `FAILED`, `CANCELED`"""
    kind: str
    """`StakingMovementKind` lists the known values: `STAKE`, `UNSTAKE`, `WITHDRAW`, `REWARD`"""
    provider: str
    """The `name` of the staking connector (`figment_sol`)"""
    amount: str
    """The quantity of the movement, as a string"""
    createdAt: int
    updatedAt: int
    staking: StakingPosition
    """The position — `staking.uuid` is what `rewards` / `unstake` take"""
    owner: UserSummary
    """The customer"""
    asset: AssetRef
    organization: OrganizationSummary | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> StakingMovement:
        organization = _cast.nullable_obj(data, "organization")
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            kind=_cast.string(data, "kind"),
            provider=_cast.string(data, "provider"),
            amount=_cast.string(data, "amount"),
            createdAt=_cast.integer(data, "createdAt"),
            updatedAt=_cast.integer(data, "updatedAt"),
            staking=StakingPosition.from_dict(_cast.obj(data, "staking")),
            owner=UserSummary.from_dict(_cast.obj(data, "owner")),
            asset=AssetRef.from_dict(_cast.obj(data, "asset")),
            organization=OrganizationSummary.from_dict(organization) if organization is not None else None,
        )


@dataclass(frozen=True, slots=True)
class StakingOperation:
    """One staking operation of a customer (`client.staking.operations()`)"""

    txId: str
    """Identifier of the journal entry"""
    movement: str | None
    """The movement of the position — carried by every entry, `reward` and `claim` included, or `None`"""
    asset: str
    """The asset ISO code"""
    kind: str
    """`STAKE`, `UNSTAKE`, `WITHDRAW` or `REWARD` (`StakingMovementKind`)"""
    amount: str
    """Asset units, as a string"""
    price: float
    """EUR price of the asset at that time"""
    value: float
    """EUR value"""
    event: str
    """`validated`, `failed`, `canceled`, `reward`, `claim`, `closed` — other values may appear"""
    provider: str
    """The connector name"""
    date: int
    """Epoch seconds"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> StakingOperation:
        return cls(
            txId=_cast.string(data, "txId"),
            movement=_cast.nullable_string(data, "movement"),
            asset=_cast.string(data, "asset"),
            kind=_cast.string(data, "kind"),
            amount=_cast.string(data, "amount"),
            price=_cast.number(data, "price"),
            value=_cast.number(data, "value"),
            event=_cast.string(data, "event"),
            provider=_cast.string(data, "provider"),
            date=_cast.integer(data, "date"),
        )


@dataclass(frozen=True, slots=True)
class StakingBalances:
    """EUR balances of a customer's staking — `{ capital, revenues }`"""

    capital: float
    """EUR"""
    revenues: float
    """EUR"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> StakingBalances:
        return cls(capital=_cast.number(data, "capital"), revenues=_cast.number(data, "revenues"))


@dataclass(frozen=True, slots=True)
class StakingHistories:
    """EUR curves of a customer's staking — `{ capital, revenues }`, two `History`"""

    capital: History
    revenues: History

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> StakingHistories:
        return cls(
            capital=History.from_dict(_cast.obj(data, "capital")),
            revenues=History.from_dict(_cast.obj(data, "revenues")),
        )


@dataclass(frozen=True, slots=True)
class StakingPortfolio:
    """The EUR balances and curves of a customer's staking (`client.staking.portfolio()`)"""

    uuid: str
    balances: StakingBalances
    histories: StakingHistories

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> StakingPortfolio:
        return cls(
            uuid=_cast.string(data, "uuid"),
            balances=StakingBalances.from_dict(_cast.obj(data, "balances")),
            histories=StakingHistories.from_dict(_cast.obj(data, "histories")),
        )

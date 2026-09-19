"""The models of the `transaction` resource: the journal of the fiat and crypto movements of the organization."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from bitgen._support.constants import ConstantsMeta
from bitgen.models import _cast
from bitgen.models.customer import UserSummary
from bitgen.models.organization import OrganizationSummary


class TransactionState(metaclass=ConstantsMeta):
    """The states of a transaction the contract lists (`TRANSFERING` is the API's spelling) — `Transaction.state` is a
    string; also the `status` filter of the list"""

    ANALYZING: Final = "ANALYZING"
    PENDING: Final = "PENDING"
    COMPLETED: Final = "COMPLETED"
    FROZEN: Final = "FROZEN"
    FAILED: Final = "FAILED"
    TRANSFERING: Final = "TRANSFERING"
    SEIZED: Final = "SEIZED"

    VALUES: Final[tuple[str, ...]] = (ANALYZING, PENDING, COMPLETED, FROZEN, FAILED, TRANSFERING, SEIZED)
    """Every value, in the order of the contract"""


class TransactionSource(metaclass=ConstantsMeta):
    """Where a transaction comes from: the EUR account (`BANK`) or a custody wallet (`CUSTODY`) — `Transaction.source`
    is a string; also a filter of the list"""

    BANK: Final = "BANK"
    CUSTODY: Final = "CUSTODY"

    VALUES: Final[tuple[str, ...]] = (BANK, CUSTODY)
    """Every value, in the order of the contract"""


class TransactionDirection(metaclass=ConstantsMeta):
    """The direction of a transaction — `Transaction.direction` is a string; also a filter of the list"""

    IN: Final = "IN"
    OUT: Final = "OUT"

    VALUES: Final[tuple[str, ...]] = (IN, OUT)
    """Every value, in the order of the contract"""


@dataclass(frozen=True, slots=True)
class TransactionAlert:
    """The compliance alert attached to a transaction — analysis data, kept as the API gives it beyond the identified
    fields"""

    uuid: str
    state: str
    """`OPEN`, `RESOLVED`, `DISMISSED`, `DECLARATED`, `CONFIRMED`"""
    severity: str
    """`SUCCESS`, `WARNING`, `CRITICAL`"""
    type: str
    """`KYT`, `KYC_EXPIRE`, `SUSPICIOUS_ACTIVITY`, `AML`, `SANCTIONS`"""
    description: str
    confidence: float
    """Confidence of the analysis, 0 to 100"""
    recommendation: str | None
    """Suggested action"""
    factors: Any
    """The elements that weighed in the analysis"""
    sources: dict[str, Any]
    """The observations analysed"""
    history: Any
    """The state changes of the alert"""
    incidentKey: str | None
    """Groups the alerts of a same incident"""
    createdAt: int
    updatedAt: int
    user: Any
    """The customer"""
    assignee: Any
    """The compliance officer"""
    organization: Any

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TransactionAlert:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            severity=_cast.string(data, "severity"),
            type=_cast.string(data, "type"),
            description=_cast.string(data, "description"),
            confidence=_cast.number(data, "confidence"),
            recommendation=_cast.nullable_string(data, "recommendation"),
            factors=_cast.raw(data, "factors"),
            sources=_cast.obj(data, "sources"),
            history=_cast.raw(data, "history"),
            incidentKey=_cast.nullable_string(data, "incidentKey"),
            createdAt=_cast.integer(data, "createdAt"),
            updatedAt=_cast.integer(data, "updatedAt"),
            user=_cast.raw(data, "user"),
            assignee=_cast.raw(data, "assignee"),
            organization=_cast.raw(data, "organization"),
        )


@dataclass(frozen=True, slots=True)
class Transaction:
    """One entry of the transaction journal: a fiat or crypto movement of the organization, created by the platform"""

    uuid: str
    state: str
    """`TransactionState` lists the known values: `ANALYZING`, `PENDING`, `COMPLETED`, `FROZEN`, `FAILED`,
    `TRANSFERING`, `SEIZED`"""
    source: str
    """`BANK` (EUR) or `CUSTODY` (crypto) — `TransactionSource`"""
    direction: str
    """`IN` or `OUT` — `TransactionDirection`"""
    asset: str
    """The asset ISO code — `EUR` for a bank transaction"""
    amount: float
    """The amount, in that asset — a number: for crypto, the exact amount is the string held by the wallet"""
    eurValue: float | None
    """EUR value when recorded"""
    reference: str | None
    credited: bool
    """Whether the customer's balance (EUR account or wallet) has been credited"""
    silent: bool
    """An internal leg (staking, sale), not an operation of the customer"""
    data: dict[str, Any]
    """Additional context set by the platform — varies with the transaction"""
    createdAt: int
    updatedAt: int
    owner: UserSummary | None
    """The customer"""
    assignee: UserSummary | None
    """The compliance officer assigned while the transaction is on hold"""
    organization: OrganizationSummary | None
    alert: TransactionAlert | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Transaction:
        owner = _cast.nullable_obj(data, "owner")
        assignee = _cast.nullable_obj(data, "assignee")
        organization = _cast.nullable_obj(data, "organization")
        alert = _cast.nullable_obj(data, "alert")
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            source=_cast.string(data, "source"),
            direction=_cast.string(data, "direction"),
            asset=_cast.string(data, "asset"),
            amount=_cast.number(data, "amount"),
            eurValue=_cast.nullable_number(data, "eurValue"),
            reference=_cast.nullable_string(data, "reference"),
            credited=_cast.boolean(data, "credited"),
            silent=_cast.boolean(data, "silent"),
            data=_cast.obj(data, "data"),
            createdAt=_cast.integer(data, "createdAt"),
            updatedAt=_cast.integer(data, "updatedAt"),
            owner=UserSummary.from_dict(owner) if owner is not None else None,
            assignee=UserSummary.from_dict(assignee) if assignee is not None else None,
            organization=OrganizationSummary.from_dict(organization) if organization is not None else None,
            alert=TransactionAlert.from_dict(alert) if alert is not None else None,
        )

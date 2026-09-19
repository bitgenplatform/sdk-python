"""The models of the `webhooks` resource: the catalogue of events, the subscriptions of the organization, the
delivery attempts, and the envelope of a delivery verified by `client.webhooks.verify()`."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Final, Protocol

from bitgen._support.constants import ConstantsMeta
from bitgen.models import _cast


class SubscriberState(metaclass=ConstantsMeta):
    """The states of a subscription and of an event of the catalogue — `Subscriber.state` and `WebhookType.state` are
    strings"""

    ENABLED: Final = "ENABLED"
    ARCHIVED: Final = "ARCHIVED"

    VALUES: Final[tuple[str, ...]] = (ENABLED, ARCHIVED)
    """Every value, in the order of the contract"""


class WebhookEventName(metaclass=ConstantsMeta):
    """The names of the events of the catalogue the contract lists — `subscribe` takes one, `WebhookEvent.event` and
    `DeliveryLog.webhook` carry one; the catalogue may grow: `subscribe` also takes any other name"""

    USER_CREATED: Final = "user.created"
    ORGANIZATION_CREATED: Final = "organization.created"
    USER_IDENTITY_STARTED: Final = "user.identity.started"
    USER_IDENTITY_PENDING: Final = "user.identity.pending"
    USER_IDENTITY_STEP_VALIDATED: Final = "user.identity.step.validated"
    USER_IDENTITY_STEP_REJECTED: Final = "user.identity.step.rejected"
    USER_IDENTITY_STEP_REQUESTED: Final = "user.identity.step.requested"
    USER_IDENTITY_VALIDATED: Final = "user.identity.validated"
    USER_IDENTITY_RENEW: Final = "user.identity.renew"
    USER_IDENTITY_REQUEST: Final = "user.identity.request"
    ORGANIZATION_IDENTITY_STARTED: Final = "organization.identity.started"
    ORGANIZATION_IDENTITY_PENDING: Final = "organization.identity.pending"
    ORGANIZATION_IDENTITY_STEP_VALIDATED: Final = "organization.identity.step.validated"
    ORGANIZATION_IDENTITY_STEP_REJECTED: Final = "organization.identity.step.rejected"
    ORGANIZATION_IDENTITY_STEP_REQUESTED: Final = "organization.identity.step.requested"
    ORGANIZATION_IDENTITY_VALIDATED: Final = "organization.identity.validated"
    ORGANIZATION_IDENTITY_RENEW: Final = "organization.identity.renew"
    ORGANIZATION_IDENTITY_REQUEST: Final = "organization.identity.request"
    BANK_CREDITED: Final = "bank.credited"
    BANK_DEBITED: Final = "bank.debited"
    BANK_TRANSACTION: Final = "bank.transaction"
    CUSTODY_TRANSACTION: Final = "custody.transaction"
    CUSTODY_WALLET_CREATED: Final = "custody.wallet.created"
    CUSTODY_SENT: Final = "custody.sent"
    CUSTODY_RECEIVED: Final = "custody.received"
    TRADING_BUY: Final = "trading.buy"
    TRADING_SELL: Final = "trading.sell"
    STAKING_REQUESTED: Final = "staking.requested"
    STAKING_STATUS: Final = "staking.status"
    STAKING_REWARDS: Final = "staking.rewards"
    STAKING_CLAIMED: Final = "staking.claimed"
    ALERT_OPENED: Final = "alert.opened"
    ALERT_STATUS: Final = "alert.status"

    VALUES: Final[tuple[str, ...]] = (
        USER_CREATED,
        ORGANIZATION_CREATED,
        USER_IDENTITY_STARTED,
        USER_IDENTITY_PENDING,
        USER_IDENTITY_STEP_VALIDATED,
        USER_IDENTITY_STEP_REJECTED,
        USER_IDENTITY_STEP_REQUESTED,
        USER_IDENTITY_VALIDATED,
        USER_IDENTITY_RENEW,
        USER_IDENTITY_REQUEST,
        ORGANIZATION_IDENTITY_STARTED,
        ORGANIZATION_IDENTITY_PENDING,
        ORGANIZATION_IDENTITY_STEP_VALIDATED,
        ORGANIZATION_IDENTITY_STEP_REJECTED,
        ORGANIZATION_IDENTITY_STEP_REQUESTED,
        ORGANIZATION_IDENTITY_VALIDATED,
        ORGANIZATION_IDENTITY_RENEW,
        ORGANIZATION_IDENTITY_REQUEST,
        BANK_CREDITED,
        BANK_DEBITED,
        BANK_TRANSACTION,
        CUSTODY_TRANSACTION,
        CUSTODY_WALLET_CREATED,
        CUSTODY_SENT,
        CUSTODY_RECEIVED,
        TRADING_BUY,
        TRADING_SELL,
        STAKING_REQUESTED,
        STAKING_STATUS,
        STAKING_REWARDS,
        STAKING_CLAIMED,
        ALERT_OPENED,
        ALERT_STATUS,
    )
    """Every value, in the order of the contract"""


class HeaderItems(Protocol):
    """Anything with an `items()` yielding `(name, value)` pairs — a `dict`, a WSGI `environ`, the `headers` of a
    Django, Flask, Starlette or `http.server` request"""

    def items(self) -> Iterable[tuple[str, Any]]: ...


ReceivedHeaders = HeaderItems | list[tuple[str | bytes, Any]] | tuple[tuple[str | bytes, Any], ...]
"""The headers of a received delivery, as `client.webhooks.verify()` takes them: anything with an `items()` yielding
`(name, value)` pairs — a `dict`, a WSGI `environ`, the `headers` of a Django, Flask, Starlette or `http.server`
request — or a plain list of `(name, value)` pairs, names and values as `str` or `bytes` (the raw headers of an ASGI
scope)"""


@dataclass(frozen=True, slots=True)
class WebhookType:
    """An event of the catalogue — `{ uuid, state, name, label, data }`"""

    uuid: str
    state: str
    """`SubscriberState` lists the known values: `ENABLED`, `ARCHIVED`"""
    name: str
    """The event name (`custody.sent`) — `WebhookEventName` lists the known ones"""
    label: str
    """Display names by language, a raw JSON string (`{"fr": "…", "en": "…"}`)"""
    data: str
    """Internal, a raw JSON string"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WebhookType:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            name=_cast.string(data, "name"),
            label=_cast.string(data, "label"),
            data=_cast.string(data, "data"),
        )


@dataclass(frozen=True, slots=True)
class Subscriber:
    """A subscription of the organization to an event — `{ uuid, state, updatedAt, webhook }`; its `uuid` is what
    `archive`, `reactivate` and `logs` take"""

    uuid: str
    state: str
    """`SubscriberState` lists the known values: `ENABLED`, `ARCHIVED`"""
    updatedAt: int
    webhook: WebhookType
    """The event of the catalogue"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Subscriber:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            updatedAt=_cast.integer(data, "updatedAt"),
            webhook=WebhookType.from_dict(_cast.obj(data, "webhook")),
        )


@dataclass(frozen=True, slots=True)
class WebhookSubscriptions:
    """What `client.webhooks.list()` returns: the secret, the endpoint and the subscriptions of the organization"""

    secret: str
    """The secret the deliveries are signed with — for `verify`, kept server-side"""
    endpoint: str
    """The URL the events are delivered to"""
    items: list[Subscriber]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WebhookSubscriptions:
        return cls(
            secret=_cast.string(data, "secret"),
            endpoint=_cast.string(data, "endpoint"),
            items=_cast.objects(data, "items", Subscriber.from_dict),
        )


@dataclass(frozen=True, slots=True)
class DeliveryLog:
    """One delivery attempt of a subscription (`client.webhooks.logs()`) — field names as the API gives them"""

    date: int
    """Epoch seconds"""
    webhook: str
    """The event name"""
    url: str
    """The endpoint called"""
    status: str
    """`SENT` or `FAILED` for that attempt"""
    http_code: int | None
    """The status the endpoint answered"""
    duration_ms: int | None
    attempts: int
    """Attempt number"""
    payload: dict[str, Any]
    """The delivered body"""
    error: str | None
    """Failure reason, `None` on success"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DeliveryLog:
        return cls(
            date=_cast.integer(data, "date"),
            webhook=_cast.string(data, "webhook"),
            url=_cast.string(data, "url"),
            status=_cast.string(data, "status"),
            http_code=_cast.nullable_int(data, "http_code"),
            duration_ms=_cast.nullable_int(data, "duration_ms"),
            attempts=_cast.integer(data, "attempts"),
            payload=_cast.obj(data, "payload"),
            error=_cast.nullable_string(data, "error"),
        )


@dataclass(frozen=True, slots=True)
class WebhookEvent:
    """The envelope of a delivery, as `client.webhooks.verify()` returns it — field names as the API sends them"""

    delivery_id: str
    timestamp: int
    """The time of the delivery, epoch seconds"""
    event: str
    """The event name — compare it with the `WebhookEventName` constants"""
    data: Any
    """The payload of the event — its shape depends on the event"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WebhookEvent:
        return cls(
            delivery_id=_cast.string(data, "delivery_id"),
            timestamp=_cast.integer(data, "timestamp"),
            event=_cast.string(data, "event"),
            data=_cast.raw(data, "data"),
        )

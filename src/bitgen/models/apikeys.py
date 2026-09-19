"""The models of the `apikeys` resource: the keys of the organization and the journal of their calls."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from bitgen._support.constants import ConstantsMeta
from bitgen.models import _cast


class ApikeyState(metaclass=ConstantsMeta):
    """The states of a key — `Apikey.state` is a string"""

    ENABLED: Final = "ENABLED"
    REVOKED: Final = "REVOKED"

    VALUES: Final[tuple[str, ...]] = (ENABLED, REVOKED)
    """Every value, in the order of the contract"""


@dataclass(frozen=True, slots=True)
class ApikeyHub:
    """The hub the organization of a key belongs to — `{ uuid, state, name, options }`"""

    uuid: str
    state: str
    name: str
    options: dict[str, Any]
    """Internal"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ApikeyHub:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            name=_cast.string(data, "name"),
            options=_cast.obj(data, "options"),
        )


@dataclass(frozen=True, slots=True)
class ApikeyOwner:
    """The owner of the organization of a key — `{ uuid, login, firstname, lastname }`"""

    uuid: str
    login: str
    firstname: str
    lastname: str | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ApikeyOwner:
        return cls(
            uuid=_cast.string(data, "uuid"),
            login=_cast.string(data, "login"),
            firstname=_cast.string(data, "firstname"),
            lastname=_cast.nullable_string(data, "lastname"),
        )


@dataclass(frozen=True, slots=True)
class ApikeyOrganization:
    """The organization a key belongs to — `{ uuid, state, name, hub?, owner? }`"""

    uuid: str
    state: str
    name: str
    hub: ApikeyHub | None
    owner: ApikeyOwner | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ApikeyOrganization:
        hub = _cast.nullable_obj(data, "hub")
        owner = _cast.nullable_obj(data, "owner")
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            name=_cast.string(data, "name"),
            hub=ApikeyHub.from_dict(hub) if hub is not None else None,
            owner=ApikeyOwner.from_dict(owner) if owner is not None else None,
        )


@dataclass(frozen=True, slots=True)
class Apikey:
    """An API key of the organization — the raw key itself is never returned"""

    uuid: str
    state: str
    """`ApikeyState` lists the known values: `ENABLED`, `REVOKED`"""
    name: str
    """Label given at creation"""
    permissions: list[str]
    """What the key is allowed to do, as set by BITGEN"""
    expireAt: int
    createdAt: int
    organization: ApikeyOrganization

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Apikey:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            name=_cast.string(data, "name"),
            permissions=_cast.strings(data, "permissions"),
            expireAt=_cast.integer(data, "expireAt"),
            createdAt=_cast.integer(data, "createdAt"),
            organization=ApikeyOrganization.from_dict(_cast.obj(data, "organization")),
        )


@dataclass(frozen=True, slots=True)
class ApikeyLog:
    """One call made with a key (`client.apikeys.logs()`)"""

    date: int
    """Epoch seconds"""
    path: str
    """The call, as the API journals it (`GET /custody/…`)"""
    payload: str
    """The inputs of the call, a JSON string — personal data masked"""
    status: int
    """The HTTP status answered"""
    error: str | None
    """The response body of a failed call, `None` when it succeeded"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ApikeyLog:
        return cls(
            date=_cast.integer(data, "date"),
            path=_cast.string(data, "path"),
            payload=_cast.string(data, "payload"),
            status=_cast.integer(data, "status"),
            error=_cast.nullable_string(data, "error"),
        )

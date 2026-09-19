"""The organization as a transaction or a staking movement references it."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from bitgen.models import _cast


@dataclass(frozen=True, slots=True)
class OrganizationHub:
    """The hub an organization belongs to — `{ uuid, name }`"""

    uuid: str
    name: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> OrganizationHub:
        return cls(uuid=_cast.string(data, "uuid"), name=_cast.string(data, "name"))


@dataclass(frozen=True, slots=True)
class OrganizationSummary:
    """An organization as a transaction or a staking movement references it — `{ uuid, state, name, hub? }`"""

    uuid: str
    state: str
    name: str
    hub: OrganizationHub | None
    """The hub the organization belongs to — `None` when it has none, and never given on a staking movement"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> OrganizationSummary:
        hub = _cast.nullable_obj(data, "hub")
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            name=_cast.string(data, "name"),
            hub=OrganizationHub.from_dict(hub) if hub is not None else None,
        )

"""The models of the `core` resource: the connectors of the platform."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from bitgen._support.constants import ConstantsMeta
from bitgen.models import _cast
from bitgen.models.asset import AssetRef


class CoreType(metaclass=ConstantsMeta):
    """The kinds of connectors — `Core.type` is a string; also the `type` filter of the catalogue"""

    IDENTITY: Final = "IDENTITY"
    """Identity verification service"""
    AML: Final = "AML"
    """Anti-money-laundering service"""
    TRADING: Final = "TRADING"
    """Exchange"""
    CUSTODY: Final = "CUSTODY"
    """Custodian"""
    STAKING: Final = "STAKING"
    """Staking provider"""
    RAMP: Final = "RAMP"
    """Bank"""

    VALUES: Final[tuple[str, ...]] = (IDENTITY, AML, TRADING, CUSTODY, STAKING, RAMP)
    """Every value, in the order of the contract"""


class CoreState(metaclass=ConstantsMeta):
    """The states of a connector — `Core.state` is a string; also the `state` filter of the catalogue"""

    ENABLED: Final = "ENABLED"
    DISABLED: Final = "DISABLED"

    VALUES: Final[tuple[str, ...]] = (ENABLED, DISABLED)
    """Every value, in the order of the contract"""


@dataclass(frozen=True, slots=True)
class CoreRef:
    """The connector of a staking position — `{ uuid, name, label }`"""

    uuid: str
    name: str
    """The identifier of the connector (`figment_sol`)"""
    label: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CoreRef:
        return cls(uuid=_cast.string(data, "uuid"), name=_cast.string(data, "name"), label=_cast.string(data, "label"))


@dataclass(frozen=True, slots=True)
class CoreConfigData:
    """The type and value of a configuration field — `{ type, value }`"""

    type: str
    """`string`, `int`, `bool`, `password` or `webhook`"""
    value: Any
    """The value — empty for a secret"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CoreConfigData:
        return cls(type=_cast.string(data, "type"), value=_cast.raw(data, "value"))


@dataclass(frozen=True, slots=True)
class CoreConfigField:
    """One field of a connector's configuration schema — the secrets live in the organization's configuration, never
    here"""

    name: str
    """The key of the field (`min_deposit`, `apr`…)"""
    label: dict[str, str]
    """Display names by language (`fr`, `en`)"""
    data: CoreConfigData

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CoreConfigField:
        return cls(
            name=_cast.string(data, "name"),
            label=_cast.string_map(data, "label"),
            data=CoreConfigData.from_dict(_cast.obj(data, "data")),
        )


@dataclass(frozen=True, slots=True)
class Core:
    """A connector of the platform: a bank (`RAMP`), an exchange (`TRADING`), a custodian (`CUSTODY`), a staking
    provider (`STAKING`), an identity (`IDENTITY`) or anti-money-laundering (`AML`) service"""

    uuid: str
    state: str
    """`ENABLED` or `DISABLED` — `CoreState`"""
    name: str
    """The identifier of the connector — for a `STAKING` connector, `<provider>_<iso>` (`figment_sol`, `bitgen_eth`)"""
    label: str
    """Display name"""
    type: str
    """`CoreType` lists the known values: `IDENTITY`, `AML`, `TRADING`, `CUSTODY`, `STAKING`, `RAMP`"""
    asset: AssetRef | None
    """The asset of a `STAKING` connector (derived from its `name`) — `None` for the other types"""
    config: list[CoreConfigField]
    """The configuration schema of the connector"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Core:
        asset = _cast.nullable_obj(data, "asset")
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            name=_cast.string(data, "name"),
            label=_cast.string(data, "label"),
            type=_cast.string(data, "type"),
            asset=AssetRef.from_dict(asset) if asset is not None else None,
            config=_cast.objects(data, "config", CoreConfigField.from_dict),
        )

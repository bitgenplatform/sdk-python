"""The models of the `customer` resource: customers, accounts, identity files, and what a creation answers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final, TypedDict

from bitgen._support.constants import ConstantsMeta
from bitgen.models import _cast


class Locale(metaclass=ConstantsMeta):
    """Language of the BITGEN web application and of the emails — `FR` (default) or `EN`"""

    FR: Final = "FR"
    EN: Final = "EN"

    VALUES: Final[tuple[str, ...]] = (FR, EN)
    """Every value, in the order of the contract"""


class CustomerState(metaclass=ConstantsMeta):
    """The states of a customer the contract lists — `Customer.state` is a string, compare it with
    `CustomerState.ENABLED`"""

    CREATED: Final = "CREATED"
    ENABLED: Final = "ENABLED"
    CLOSED: Final = "CLOSED"
    FROZEN: Final = "FROZEN"

    VALUES: Final[tuple[str, ...]] = (CREATED, ENABLED, CLOSED, FROZEN)
    """Every value, in the order of the contract"""


class IdentityState(metaclass=ConstantsMeta):
    """The states of an identity file the contract lists — `Identity.state` is a string"""

    CREATED: Final = "CREATED"
    IN_PROGRESS: Final = "IN_PROGRESS"
    WAIT: Final = "WAIT"
    PENDING: Final = "PENDING"
    VALIDATED: Final = "VALIDATED"
    REJECTED: Final = "REJECTED"
    FROZEN: Final = "FROZEN"
    EXPIRED: Final = "EXPIRED"
    CLOSED: Final = "CLOSED"

    VALUES: Final[tuple[str, ...]] = (CREATED, IN_PROGRESS, WAIT, PENDING, VALIDATED, REJECTED, FROZEN, EXPIRED, CLOSED)
    """Every value, in the order of the contract"""


class IdentityMode(metaclass=ConstantsMeta):
    """`KYC` (a person) or `KYB` (a business) — `Identity.mode` is a string"""

    KYC: Final = "KYC"
    KYB: Final = "KYB"

    VALUES: Final[tuple[str, ...]] = (KYC, KYB)
    """Every value, in the order of the contract"""


class OrganizationCategory(metaclass=ConstantsMeta):
    """Category of a customer — the `organization` of `client.customer.create()` (`CUSTOMER` by default; `B2B` also
    opens a KYB file) and `CustomerSetup.choosenOrganization` (a string on the API's side)"""

    CUSTOMER: Final = "CUSTOMER"
    B2B: Final = "B2B"

    VALUES: Final[tuple[str, ...]] = (CUSTOMER, B2B)
    """Every value, in the order of the contract"""


class Notifications(TypedDict, total=False):
    """Email preferences of a customer, as given to `client.customer.update()`: login-related emails, BITGEN
    newsletter"""

    login: bool
    newsletter: bool


@dataclass(frozen=True, slots=True)
class Created:
    """`{ uuid }` — what a creation answers. Carries a `uuid`: it is accepted wherever a customer is expected."""

    uuid: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Created:
        return cls(uuid=_cast.string(data, "uuid"))


@dataclass(frozen=True, slots=True)
class IdentityStep:
    """One step of an identity verification (`info`, `selfie`, `identity`, `residency` — `info`, `kbis`, `status`,
    `domiciliation`, `rbe`)"""

    status: str
    submittedAt: int | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> IdentityStep:
        return cls(status=_cast.string(data, "status"), submittedAt=_cast.nullable_int(data, "submittedAt"))


@dataclass(frozen=True, slots=True)
class IdentityData:
    """Progress of an identity verification: one `IdentityStep` per step, the hosted verification URL when the provider
    hosts it"""

    steps: dict[str, IdentityStep]
    notifications: bool
    """Internal flag"""
    verificationUrl: str | None
    hosted: bool | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> IdentityData:
        hosted = data.get("hosted")
        return cls(
            steps={
                name: IdentityStep.from_dict(_cast.as_object(step))
                for name, step in _cast.obj(data, "steps").items()
                if isinstance(step, dict)
            },
            notifications=_cast.boolean(data, "notifications"),
            verificationUrl=_cast.nullable_string(data, "verificationUrl"),
            hosted=hosted if isinstance(hosted, bool) else None,
        )


@dataclass(frozen=True, slots=True)
class KycIdentityForm:
    """The answers of the KYC questionnaire (attribute names as in the contract), plus the internal `score`"""

    european_residency: Any
    ppe: Any
    """Politically exposed person"""
    ppp: Any
    """Relative of a politically exposed person"""
    source_income: str | None
    net_income: str | None
    experience: str | None
    """Crypto experience"""
    submittedAt: int | None
    score: int
    """Internal scoring"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> KycIdentityForm:
        return cls(
            european_residency=_cast.raw(data, "european_residency"),
            ppe=_cast.raw(data, "ppe"),
            ppp=_cast.raw(data, "ppp"),
            source_income=_cast.nullable_string(data, "source_income"),
            net_income=_cast.nullable_string(data, "net_income"),
            experience=_cast.nullable_string(data, "experience"),
            submittedAt=_cast.nullable_int(data, "submittedAt"),
            score=_cast.integer(data, "score"),
        )


@dataclass(frozen=True, slots=True)
class KybIdentityForm:
    """The KYB questionnaire: the business `activity`, plus the internal `score`"""

    activity: str | None
    submittedAt: int | None
    score: int
    """Internal scoring"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> KybIdentityForm:
        return cls(
            activity=_cast.nullable_string(data, "activity"),
            submittedAt=_cast.nullable_int(data, "submittedAt"),
            score=_cast.integer(data, "score"),
        )


@dataclass(frozen=True, slots=True)
class Identity:
    """The verification file of a person (`mode` `KYC` → `KycIdentity`) or of a business (`KYB` → `KybIdentity`).
    `from_dict` builds the subclass the `mode` names; a mode the contract does not list yet gives this base class, with
    the common fields only — narrow with `isinstance`."""

    uuid: str
    state: str
    """`IdentityState` lists the known values: `CREATED`, `IN_PROGRESS`, `WAIT`, `PENDING`, `VALIDATED`, `REJECTED`,
    `FROZEN`, `EXPIRED`, `CLOSED`"""
    mode: str
    """`KYC` or `KYB` (`IdentityMode`)"""
    data: IdentityData
    validatedAt: int | None
    expiresAt: int | None
    renewalNotifiedAt: int | None
    """When the renewal reminder was sent — an identity expires after 12 months (6 for a politically exposed person)"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Identity:
        mode = _cast.string(data, "mode")
        if mode == IdentityMode.KYC:
            return KycIdentity(**_common(data), form=KycIdentityForm.from_dict(_cast.obj(data, "form")))
        if mode == IdentityMode.KYB:
            return KybIdentity(**_common(data), form=KybIdentityForm.from_dict(_cast.obj(data, "form")))
        return Identity(**_common(data))


def _common(data: Mapping[str, Any]) -> dict[str, Any]:
    """The fields every identity file carries"""
    return {
        "uuid": _cast.string(data, "uuid"),
        "state": _cast.string(data, "state"),
        "mode": _cast.string(data, "mode"),
        "data": IdentityData.from_dict(_cast.obj(data, "data")),
        "validatedAt": _cast.nullable_int(data, "validatedAt"),
        "expiresAt": _cast.nullable_int(data, "expiresAt"),
        "renewalNotifiedAt": _cast.nullable_int(data, "renewalNotifiedAt"),
    }


@dataclass(frozen=True, slots=True)
class KycIdentity(Identity):
    """The KYC file of a person: the common identity fields plus the questionnaire (`form`)"""

    form: KycIdentityForm


@dataclass(frozen=True, slots=True)
class KybIdentity(Identity):
    """The KYB file of a business: the common identity fields plus the questionnaire (`form`)"""

    form: KybIdentityForm


@dataclass(frozen=True, slots=True)
class AccountAddress:
    """The postal address record of a customer — `state` is set on `Customer.account`, `None` on `Account.account`
    (reduced to `{ uuid, address }`)"""

    uuid: str
    address: str
    state: str | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AccountAddress:
        return cls(
            uuid=_cast.string(data, "uuid"),
            address=_cast.string(data, "address"),
            state=_cast.nullable_string(data, "state"),
        )


@dataclass(frozen=True, slots=True)
class CustomerAccount:
    """The details of a customer"""

    email: str
    firstname: str
    lastname: str | None
    fin: str | None
    """Tax identification number"""
    birthdate: int | None
    """Date of birth, epoch seconds"""
    phoneNumber: int | None
    """The number as an integer"""
    phoneZone: str | None
    """Dialing code, `+33` by default"""
    address: AccountAddress | None
    referralCode: str
    """The customer's own referral code, generated at creation"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CustomerAccount:
        address = _cast.nullable_obj(data, "address")
        return cls(
            email=_cast.string(data, "email"),
            firstname=_cast.string(data, "firstname"),
            lastname=_cast.nullable_string(data, "lastname"),
            fin=_cast.nullable_string(data, "fin"),
            birthdate=_cast.nullable_int(data, "birthdate"),
            phoneNumber=_cast.nullable_int(data, "phoneNumber"),
            phoneZone=_cast.nullable_string(data, "phoneZone"),
            address=AccountAddress.from_dict(address) if address is not None else None,
            referralCode=_cast.string(data, "referralCode"),
        )


@dataclass(frozen=True, slots=True)
class CustomerClient:
    """Platform-side flags of a customer's account"""

    roles: list[str]
    """Platform roles — always `ROLE_USER` for a customer"""
    hasTfa: bool
    """Two-factor authentication enabled"""
    hasPhishing: bool
    """Anti-phishing code enabled"""
    isValid: bool
    """`True` once the account has been activated"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CustomerClient:
        return cls(
            roles=_cast.strings(data, "roles"),
            hasTfa=_cast.boolean(data, "hasTfa"),
            hasPhishing=_cast.boolean(data, "hasPhishing"),
            isValid=_cast.boolean(data, "isValid"),
        )


@dataclass(frozen=True, slots=True)
class CustomerSetup:
    """The settings of a customer"""

    theme: str
    """Theme of the BITGEN web application, `light` by default"""
    currency: str
    """Display currency, `EUR`"""
    locale: str
    """Language of the web application and of the emails (`Locale`)"""
    choosenOrganization: str
    """Category chosen at signup — `OrganizationCategory` lists the known values: `CUSTOMER`, `B2B`"""
    needActivation: bool
    """Activation email pending: the customer is invisible to bank / custody / trading / staking until they activate"""
    notify: bool
    """Whether the customer accepts BITGEN emails"""
    onboarding: bool | None
    """Whether the web onboarding has been completed"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CustomerSetup:
        onboarding = data.get("onboarding")
        return cls(
            theme=_cast.string(data, "theme"),
            currency=_cast.string(data, "currency"),
            locale=_cast.string(data, "locale"),
            choosenOrganization=_cast.string(data, "choosenOrganization"),
            needActivation=_cast.boolean(data, "needActivation"),
            notify=_cast.boolean(data, "notify"),
            onboarding=onboarding if isinstance(onboarding, bool) else None,
        )


@dataclass(frozen=True, slots=True)
class CustomerAction:
    """`Customer.action` — carries the settings (`setup`)"""

    setup: CustomerSetup

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CustomerAction:
        return cls(setup=CustomerSetup.from_dict(_cast.obj(data, "setup")))


@dataclass(frozen=True, slots=True)
class CollaboratorLink:
    """The attachment of a customer to an organization"""

    uuid: str
    state: str
    """`WAIT` until activation, then `ENABLED`; `REVOKED` once removed"""
    roles: list[str]
    """`ROLE_USER` for a customer"""
    organization: str
    """Organization name"""
    organizationUuid: str
    manager: str | None
    """uuid of the collaborator in charge of the customer"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CollaboratorLink:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            roles=_cast.strings(data, "roles"),
            organization=_cast.string(data, "organization"),
            organizationUuid=_cast.string(data, "organizationUuid"),
            manager=_cast.nullable_string(data, "manager"),
        )


@dataclass(frozen=True, slots=True)
class ManagerLink:
    """An attachment where the account manages other people — always empty for a customer (CRM data)"""

    uuid: str
    state: str
    mandate: Any
    mandatedUntil: str | None
    """`d/m/Y`"""
    account: str | None
    """Email"""
    organizationUuid: str
    roles: list[str]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ManagerLink:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            mandate=_cast.raw(data, "mandate"),
            mandatedUntil=_cast.nullable_string(data, "mandatedUntil"),
            account=_cast.nullable_string(data, "account"),
            organizationUuid=_cast.string(data, "organizationUuid"),
            roles=_cast.strings(data, "roles"),
        )


@dataclass(frozen=True, slots=True)
class CustomerCollaborations:
    """`Customer.collaborations` — the customer's attachments (`collaborator`) and the attachments they manage
    (`manager`)"""

    collaborator: list[CollaboratorLink]
    manager: list[ManagerLink]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CustomerCollaborations:
        return cls(
            collaborator=_cast.objects(data, "collaborator", CollaboratorLink.from_dict),
            manager=_cast.objects(data, "manager", ManagerLink.from_dict),
        )


@dataclass(frozen=True, slots=True)
class CustomerAlert:
    """An active compliance alert on a customer"""

    uuid: str
    state: str
    """`OPEN`, `DECLARATED`, `CONFIRMED`"""
    severity: str
    """`SUCCESS`, `WARNING`, `CRITICAL`"""
    sources: dict[str, Any]
    """The observations behind the alert (analysis data)"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CustomerAlert:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            severity=_cast.string(data, "severity"),
            sources=_cast.obj(data, "sources"),
        )


@dataclass(frozen=True, slots=True)
class CustomerBusiness:
    """A business of a customer, with its KYB file"""

    identity: Identity

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CustomerBusiness:
        return cls(identity=Identity.from_dict(_cast.obj(data, "identity")))


@dataclass(frozen=True, slots=True)
class Customer:
    """An item of `client.customer.list()` — carries a `uuid`: it is accepted wherever a customer is expected"""

    uuid: str
    state: str
    """`CustomerState` lists the known values: `CREATED` (activation pending), `ENABLED`, `CLOSED`, `FROZEN`"""
    isAvailable: bool
    """`False` until the customer has activated their account, then `True`"""
    createdAt: int
    login: str
    """The email"""
    canLogin: bool
    """Whether the customer may sign in to the BITGEN web application"""
    account: CustomerAccount
    client: CustomerClient
    action: CustomerAction
    identity: Identity
    business: list[CustomerBusiness]
    """The businesses of the customer, each with its KYB file"""
    collaborations: CustomerCollaborations
    alert: list[CustomerAlert]
    """Active compliance alerts"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Customer:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            isAvailable=_cast.boolean(data, "isAvailable"),
            createdAt=_cast.integer(data, "createdAt"),
            login=_cast.string(data, "login"),
            canLogin=_cast.boolean(data, "canLogin"),
            account=CustomerAccount.from_dict(_cast.obj(data, "account")),
            client=CustomerClient.from_dict(_cast.obj(data, "client")),
            action=CustomerAction.from_dict(_cast.obj(data, "action")),
            identity=Identity.from_dict(_cast.obj(data, "identity")),
            business=_cast.objects(data, "business", CustomerBusiness.from_dict),
            collaborations=CustomerCollaborations.from_dict(_cast.obj(data, "collaborations")),
            alert=_cast.objects(data, "alert", CustomerAlert.from_dict),
        )


@dataclass(frozen=True, slots=True)
class AccountNotifications:
    """Email preferences of a customer: login-related emails, BITGEN newsletter"""

    login: bool
    newsletter: bool

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AccountNotifications:
        return cls(login=_cast.boolean(data, "login"), newsletter=_cast.boolean(data, "newsletter"))


@dataclass(frozen=True, slots=True)
class Account:
    """`client.customer.get()` — one customer's account: identity files, details, settings. Carries a `uuid`: accepted
    wherever a customer is expected."""

    uuid: str
    identity: Identity
    business: list[CustomerBusiness]
    """The businesses of the customer, each with its KYB file"""
    account: CustomerAccount
    """The same fields as `Customer.account`, with `address` reduced to `{ uuid, address }`"""
    notifications: AccountNotifications
    setup: CustomerSetup

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Account:
        return cls(
            uuid=_cast.string(data, "uuid"),
            identity=Identity.from_dict(_cast.obj(data, "identity")),
            business=_cast.objects(data, "business", CustomerBusiness.from_dict),
            account=CustomerAccount.from_dict(_cast.obj(data, "account")),
            notifications=AccountNotifications.from_dict(_cast.obj(data, "notifications")),
            setup=CustomerSetup.from_dict(_cast.obj(data, "setup")),
        )


@dataclass(frozen=True, slots=True)
class OrderUser:
    """The customer of an order — `{ uuid, login }`. Carries a `uuid`: it is accepted wherever a customer is
    expected."""

    uuid: str
    login: str
    """The email"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> OrderUser:
        return cls(uuid=_cast.string(data, "uuid"), login=_cast.string(data, "login"))


@dataclass(frozen=True, slots=True)
class UserSummaryAccount:
    """The identity of a `UserSummary` — `{ firstname, lastname, fin }`"""

    firstname: str
    lastname: str | None
    fin: str | None
    """Tax identification number"""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> UserSummaryAccount:
        return cls(
            firstname=_cast.string(data, "firstname"),
            lastname=_cast.nullable_string(data, "lastname"),
            fin=_cast.nullable_string(data, "fin"),
        )


@dataclass(frozen=True, slots=True)
class UserSummary:
    """A user as a transaction or a staking movement references them — `{ uuid, state, login, account }`: the customer
    (`owner`) or the compliance officer in charge (`assignee`). An `owner` carries the customer's `uuid`: it is accepted
    wherever a customer is expected."""

    uuid: str
    state: str
    """`CustomerState` lists the known values"""
    login: str
    """The email"""
    account: UserSummaryAccount

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> UserSummary:
        return cls(
            uuid=_cast.string(data, "uuid"),
            state=_cast.string(data, "state"),
            login=_cast.string(data, "login"),
            account=UserSummaryAccount.from_dict(_cast.obj(data, "account")),
        )


UserRef = str | Created | Customer | Account | UserSummary | OrderUser
"""A customer, as accepted by every method expecting one: their uuid (or an email, where the API resolves it), or a
model that carries a customer's uuid — the `Created` of `client.customer.create()`, a `Customer`, an `Account`, the
`user` of an `Order`, the `owner` of a `Transaction` or of a `StakingMovement`"""

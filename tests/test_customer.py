"""The `customer` resource against the fake transport: exact bodies and queries, mapping of the answers, errors,
refusals."""

from __future__ import annotations

import json
from typing import Any

import pytest

from bitgen import BitgenError
from bitgen._http.client import HttpClient
from bitgen.models import (
    Account,
    Created,
    Customer,
    CustomerState,
    Identity,
    IdentityMode,
    IdentityState,
    KybIdentity,
    KycIdentity,
    Locale,
    OrganizationCategory,
)
from bitgen.resources.customer import CustomerResource
from tests.fake_transport import FakeTransport
from tests.test_user_id import USER_MESSAGE

# A realistic KYC identity file (contract § 4)
KYC: dict[str, Any] = {
    "uuid": "id-1",
    "state": "VALIDATED",
    "mode": "KYC",
    "form": {
        "european_residency": True,
        "ppe": False,
        "ppp": False,
        "source_income": "salary",
        "net_income": "30k-50k",
        "experience": "beginner",
        "submittedAt": 1700000000,
        "score": 12,
    },
    "data": {
        "steps": {
            "info": {"status": "VALIDATED", "submittedAt": 1700000000},
            "selfie": {"status": "PENDING", "submittedAt": None},
        },
        "notifications": True,
        "verificationUrl": "https://verify.example/abc",
        "hosted": True,
    },
    "validatedAt": 1700003600,
    "expiresAt": 1731539600,
    "renewalNotifiedAt": None,
}
# A realistic KYB identity file
KYB: dict[str, Any] = {
    "uuid": "id-2",
    "state": "PENDING",
    "mode": "KYB",
    "form": {"activity": "software", "submittedAt": None, "score": 0},
    "data": {
        "steps": {"kbis": {"status": "REQUESTED", "submittedAt": None}},
        "notifications": False,
        "verificationUrl": None,
    },
    "validatedAt": None,
    "expiresAt": None,
    "renewalNotifiedAt": None,
}
# A realistic item of the customer list
CUSTOMER: dict[str, Any] = {
    "uuid": "c-1",
    "state": "ENABLED",
    "isAvailable": True,
    "createdAt": 1699000000,
    "login": "jean@valjean.fr",
    "canLogin": True,
    "account": {
        "email": "jean@valjean.fr",
        "firstname": "Jean",
        "lastname": "Valjean",
        "fin": None,
        "birthdate": 315532800,
        "phoneNumber": 612345678,
        "phoneZone": "+33",
        "address": {"uuid": "ad-1", "state": "VALIDATED", "address": "1 rue de Paris"},
        "referralCode": "JEAN42",
    },
    "client": {"roles": ["ROLE_USER"], "hasTfa": False, "hasPhishing": False, "isValid": True},
    "action": {
        "setup": {
            "theme": "light",
            "currency": "EUR",
            "locale": "FR",
            "choosenOrganization": "CUSTOMER",
            "needActivation": False,
            "notify": True,
            "onboarding": True,
        }
    },
    "identity": KYC,
    "business": [{"identity": KYB}],
    "collaborations": {
        "collaborator": [
            {
                "uuid": "col-1",
                "state": "ENABLED",
                "roles": ["ROLE_USER"],
                "organization": "ACME",
                "organizationUuid": "org-uuid",
                "manager": "man-1",
            }
        ],
        "manager": [],
    },
    "alert": [{"uuid": "al-1", "state": "OPEN", "severity": "WARNING", "sources": {"kyt": {"score": 3}}}],
    "somethingNew": "ignored",
}
ACCOUNT: dict[str, Any] = {
    "uuid": "c-1",
    "identity": KYC,
    "business": [],
    "account": {
        "email": "jean@valjean.fr",
        "firstname": "Jean",
        "lastname": None,
        "fin": None,
        "birthdate": None,
        "phoneNumber": None,
        "phoneZone": None,
        "address": {"uuid": "ad-1", "address": "1 rue de Paris"},
        "referralCode": "JEAN42",
    },
    "notifications": {"login": True, "newsletter": False},
    "setup": {
        "theme": "dark",
        "currency": "EUR",
        "locale": "EN",
        "choosenOrganization": "B2B",
        "needActivation": True,
        "notify": False,
    },
}


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def customer(transport: FakeTransport) -> CustomerResource:
    return CustomerResource(HttpClient(transport, "org-uuid", "k", "https://api.test", 1.0, "ua"))


def last_body(transport: FakeTransport) -> Any:
    body = transport.last().body
    assert body is not None
    return json.loads(body)


def test_create_sends_the_exact_body_with_the_scope_as_organization_and_no_role(
    customer: CustomerResource, transport: FakeTransport
) -> None:
    transport.will_answer(201, '{"uuid":"c-1"}')
    created = customer.create("jean@valjean.fr", "man-1", firstname="Jean", locale=Locale.FR)
    assert isinstance(created, Created)
    assert created.uuid == "c-1"
    assert (transport.last().method, transport.last().url) == ("POST", "https://api.test/customer")
    assert last_body(transport) == {
        "account": {"email": "jean@valjean.fr", "firstname": "Jean"},
        "group": {"manager": "man-1", "organization": "org-uuid"},
        "locale": "FR",
    }
    # every option, needActivation / notify travel as given (False is sent, not dropped)
    customer.create(
        "a@b.c",
        "m",
        lastname="V",
        fin="FIN",
        needActivation=False,
        notify=False,
        locale=Locale.EN,
        organization=OrganizationCategory.B2B,
    )
    assert last_body(transport) == {
        "account": {"email": "a@b.c", "lastname": "V", "fin": "FIN", "needActivation": False, "notify": False},
        "group": {"manager": "m", "organization": "org-uuid"},
        "locale": "EN",
        "organization": "B2B",
    }


def test_values_outside_the_constants_are_refused_before_any_request(
    customer: CustomerResource, transport: FakeTransport
) -> None:
    with pytest.raises(ValueError, match=r"^locale must be FR or EN$"):
        customer.create("a@b.c", "m", locale="en")
    with pytest.raises(ValueError, match=r"^locale must be FR or EN$"):
        customer.update("c-1", locale="xx")
    # BUSINESS is reserved to platform administrators: outside OrganizationCategory.VALUES, like any other string
    with pytest.raises(ValueError, match=r"^organization must be CUSTOMER or B2B$"):
        customer.create("a@b.c", "m", organization="BUSINESS")
    with pytest.raises(ValueError, match=r"^organization must be CUSTOMER or B2B$"):
        customer.create("a@b.c", "m", organization="b2b")
    with pytest.raises(TypeError, match=r"^needActivation must be a boolean$"):
        customer.create("a@b.c", "m", needActivation="false")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^email must be a string$"):
        customer.create(None, "m")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^offset must be an integer$"):
        customer.list(offset="0")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^limit must be an integer$"):
        customer.list(limit=True)  # a bool is an int for the type checker, not for the SDK
    assert transport.requests == []


def test_list_sends_the_exact_query_and_maps_customers(  # noqa: PLR0915 - one assertion per field of the contract
    customer: CustomerResource, transport: FakeTransport
) -> None:
    transport.will_answer(200, json.dumps({"count": 1, "items": [CUSTOMER]}))
    page = customer.list(offset=0, limit=50, includeClosed=True)
    assert transport.last().url == "https://api.test/customer?offset=0&limit=50&includeClosed=true"
    assert page.count == 1
    item = page.items[0]
    assert isinstance(item, Customer)
    assert item.uuid == "c-1"
    assert item.state == CustomerState.ENABLED
    assert item.isAvailable is True
    assert item.createdAt == 1699000000
    assert item.login == "jean@valjean.fr"
    assert item.canLogin is True
    assert item.account.firstname == "Jean"
    assert item.account.lastname == "Valjean"
    assert item.account.fin is None
    assert item.account.birthdate == 315532800
    assert item.account.phoneNumber == 612345678
    assert item.account.phoneZone == "+33"
    assert item.account.address is not None
    assert item.account.address.address == "1 rue de Paris"
    assert item.account.address.state == "VALIDATED"
    assert item.account.referralCode == "JEAN42"
    assert item.client.roles == ["ROLE_USER"]
    assert item.client.hasTfa is False
    assert item.client.isValid is True
    assert item.action.setup.theme == "light"
    assert item.action.setup.currency == "EUR"
    assert item.action.setup.locale == Locale.FR
    assert item.action.setup.choosenOrganization == OrganizationCategory.CUSTOMER
    assert item.action.setup.needActivation is False
    assert item.action.setup.onboarding is True
    # KYC identity, narrowed by class
    identity = item.identity
    assert isinstance(identity, KycIdentity)
    assert identity.state == IdentityState.VALIDATED
    assert identity.mode == IdentityMode.KYC
    assert identity.form.european_residency is True
    assert identity.form.source_income == "salary"
    assert identity.form.score == 12
    assert identity.data.steps["info"].status == "VALIDATED"
    assert identity.data.steps["selfie"].submittedAt is None
    assert identity.data.notifications is True
    assert identity.data.verificationUrl == "https://verify.example/abc"
    assert identity.data.hosted is True
    assert identity.validatedAt == 1700003600
    assert identity.renewalNotifiedAt is None
    # KYB identity of the business
    business = item.business[0].identity
    assert isinstance(business, KybIdentity)
    assert business.form.activity == "software"
    assert business.form.score == 0
    assert business.data.hosted is None
    assert item.collaborations.collaborator[0].state == "ENABLED"
    assert item.collaborations.collaborator[0].organization == "ACME"
    assert item.collaborations.collaborator[0].manager == "man-1"
    assert item.collaborations.manager == []
    assert item.alert[0].severity == "WARNING"
    assert item.alert[0].sources == {"kyt": {"score": 3}}

    customer.list()
    assert transport.last().url == "https://api.test/customer"
    customer.list(manager="man-1", includeClosed=False)
    assert transport.last().url == "https://api.test/customer?includeClosed=false&manager=man-1"


def test_get_by_uuid_email_or_model_maps_the_account(customer: CustomerResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps(ACCOUNT)).will_answer(200, json.dumps(ACCOUNT)).will_answer(
        200, json.dumps(ACCOUNT)
    )
    result = customer.get("c-1")
    assert transport.last().url == "https://api.test/account/c-1"
    assert isinstance(result, Account)
    assert result.uuid == "c-1"
    assert isinstance(result.identity, KycIdentity)
    assert result.business == []
    assert result.account.lastname is None
    assert result.account.address is not None
    assert result.account.address.state is None
    assert result.notifications.login is True
    assert result.notifications.newsletter is False
    assert result.setup.theme == "dark"
    assert result.setup.needActivation is True
    assert result.setup.onboarding is None

    customer.get("jean@valjean.fr")
    assert transport.last().url == "https://api.test/account/jean%40valjean.fr"
    customer.get(Created("c-1"))
    assert transport.last().url == "https://api.test/account/c-1"


def test_an_unknown_identity_mode_gives_the_base_identity(customer: CustomerResource, transport: FakeTransport) -> None:
    transport.will_answer(
        200,
        json.dumps(
            {
                "count": 1,
                "items": [
                    {"uuid": "c", "identity": {"uuid": "i", "state": "CREATED", "mode": "KYX", "form": {"x": 1}}}
                ],
            }
        ),
    )
    identity = customer.list().items[0].identity
    assert type(identity) is Identity
    assert identity.mode == "KYX"
    assert not hasattr(identity, "form")


def test_update_sends_only_the_keys_given(customer: CustomerResource, transport: FakeTransport) -> None:
    transport.will_answer(200, "[]")
    customer.update("c-1", locale=Locale.EN, notifications={"newsletter": False})
    assert (transport.last().method, transport.last().url) == ("PUT", "https://api.test/account/c-1")
    assert last_body(transport) == {"action": {"locale": "EN"}, "notifications": {"newsletter": False}}

    customer.update("c-1", theme="dark")
    assert last_body(transport) == {"action": {"theme": "dark"}}

    customer.update("c-1")
    assert transport.last().body == b"{}"
    customer.update("c-1", notifications={})  # nothing to update: nothing sent
    assert transport.last().body == b"{}"

    with pytest.raises(ValueError, match=r"^notifications only takes the keys login and newsletter$"):
        customer.update("c-1", notifications={"sms": True})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^notifications\['login'\] must be a boolean$"):
        customer.update("c-1", notifications={"login": "yes"})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^notifications must be a dict"):
        customer.update("c-1", notifications=["login"])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("status", "code", "call"),
    [
        (403, "forbidden_permission", lambda customer: customer.list()),
        (404, "unknown_user", lambda customer: customer.get("nope")),
        (422, "invalid_include_closed", lambda customer: customer.list(includeClosed=True)),
        (403, "missing_group_organization_or_manager", lambda customer: customer.create("a@b.c", "m")),
    ],
)
def test_api_errors_become_bitgen_errors(
    customer: CustomerResource, transport: FakeTransport, status: int, code: str, call: Any
) -> None:
    transport.will_answer(status, json.dumps({"error": True, "message": code, "code": status}))
    with pytest.raises(BitgenError) as caught:
        call(customer)
    assert (caught.value.status, caught.value.code) == (status, code)


@pytest.mark.parametrize("bad", ["", "..", Created("")])
def test_invalid_users_are_refused_before_any_request(
    customer: CustomerResource, transport: FakeTransport, bad: Any
) -> None:
    with pytest.raises(ValueError):
        customer.get(bad)
    assert transport.requests == []


def test_a_model_carrying_the_customer_uuid_is_accepted_and_any_other_object_is_a_type_error(
    customer: CustomerResource, transport: FakeTransport
) -> None:
    transport.will_answer(200, json.dumps({"uuid": "c-1"}))
    customer.get(Customer.from_dict(CUSTOMER))
    assert transport.last().url == "https://api.test/account/c-1"
    customer.update(Account.from_dict({"uuid": "c-1"}), theme="dark")
    assert transport.last().url == "https://api.test/account/c-1"
    sent = len(transport.requests)
    with pytest.raises(TypeError, match=USER_MESSAGE):
        customer.get(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        customer.get({"uuid": "c-1"})  # type: ignore[arg-type]
    assert len(transport.requests) == sent

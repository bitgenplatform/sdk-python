"""The `apikeys` resource against the fake transport: exact queries, mapping of the answers, errors, refusals."""

from __future__ import annotations

import json
from typing import Any

import pytest

from bitgen import BitgenError
from bitgen._http.client import HttpClient
from bitgen.models import Apikey, ApikeyState
from bitgen.resources.apikeys import ApikeysResource
from tests.fake_transport import FakeTransport

# A realistic `GET /organization/{organization}/apikeys/{apikey}` body (contract § 11)
APIKEY: dict[str, Any] = {
    "uuid": "key-1",
    "state": "ENABLED",
    "name": "backend",
    "permissions": ["customer.read", "bank.read", "custody.write"],
    "expireAt": 1735689600,
    "createdAt": 1700000000,
    "organization": {
        "uuid": "org-uuid",
        "state": "ENABLED",
        "name": "ACME",
        "hub": {"uuid": "hub-1", "state": "ENABLED", "name": "HUB", "options": {"white_label": True}},
        "owner": {"uuid": "owner-1", "login": "ceo@acme.fr", "firstname": "Anne", "lastname": None},
    },
    "somethingNew": True,
}


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def apikeys(transport: FakeTransport) -> ApikeysResource:
    return ApikeysResource(HttpClient(transport, "org-uuid", "k", "https://api.test", 1.0, "ua"))


def test_list_sends_the_exact_query_and_maps_keys(apikeys: ApikeysResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps({"count": 1, "items": [APIKEY]}))
    page = apikeys.list(includeRevoked=True, offset=0, limit=50)
    assert (transport.last().method, transport.last().url) == (
        "GET",
        "https://api.test/organization/org-uuid/apikeys?includeRevoked=true&offset=0&limit=50",
    )
    assert page.count == 1
    assert page.items[0].uuid == "key-1"
    transport.will_answer(200, json.dumps({"count": 1, "items": [APIKEY]}))
    apikeys.list()
    assert transport.last().url == "https://api.test/organization/org-uuid/apikeys"
    transport.will_answer(200, json.dumps({"count": 1, "items": [APIKEY]}))
    apikeys.list(includeRevoked=False)
    assert transport.last().url == "https://api.test/organization/org-uuid/apikeys?includeRevoked=false"


def test_get_maps_the_key(apikeys: ApikeysResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps(APIKEY))
    key = apikeys.get("key-1")
    assert transport.last().url == "https://api.test/organization/org-uuid/apikeys/key-1"
    assert isinstance(key, Apikey)
    assert (key.uuid, key.state, key.name) == ("key-1", ApikeyState.ENABLED, "backend")
    assert key.permissions == ["customer.read", "bank.read", "custody.write"]
    assert (key.expireAt, key.createdAt) == (1735689600, 1700000000)
    assert (key.organization.uuid, key.organization.state, key.organization.name) == ("org-uuid", "ENABLED", "ACME")
    assert key.organization.hub is not None
    assert (key.organization.hub.uuid, key.organization.hub.state, key.organization.hub.name) == (
        "hub-1",
        "ENABLED",
        "HUB",
    )
    assert key.organization.hub.options == {"white_label": True}
    assert key.organization.owner is not None
    assert (key.organization.owner.uuid, key.organization.owner.login) == ("owner-1", "ceo@acme.fr")
    assert key.organization.owner.firstname == "Anne"
    assert key.organization.owner.lastname is None
    # a revoked key of an organization without hub nor owner; the scope is encoded in the path
    other = ApikeysResource(HttpClient(transport, "org/1", "k", "https://api.test", 1.0, "ua"))
    revoked_body = {
        "uuid": "key-2",
        "state": "REVOKED",
        "name": "old",
        "permissions": [],
        "expireAt": 1700000000,
        "createdAt": 1690000000,
        "organization": {"uuid": "org/1", "state": "ENABLED", "name": "ACME", "hub": None, "owner": None},
    }
    transport.will_answer(200, json.dumps(revoked_body))
    revoked = other.get("key-2")
    assert transport.last().url == "https://api.test/organization/org%2F1/apikeys/key-2"
    assert revoked.state == ApikeyState.REVOKED
    assert revoked.permissions == []
    assert revoked.organization.hub is None
    assert revoked.organization.owner is None


def test_logs_map_the_calls(apikeys: ApikeysResource, transport: FakeTransport) -> None:
    items = [
        {"date": 1700000000, "path": "GET /custody/c-1", "payload": '{"user":"c-1"}', "status": 200, "error": None},
        {
            "date": 1700000060,
            "path": "PUT /bank/c-1",
            "payload": '{"amount":"50.00","iban":"****"}',
            "status": 416,
            "error": '{"error":true,"message":"requested_amount_error","code":416}',
        },
    ]
    transport.will_answer(200, json.dumps({"count": 2, "items": items}))
    page = apikeys.logs("key-1", offset=0, limit=50)
    assert transport.last().url == "https://api.test/organization/org-uuid/apikeys/key-1/logs?offset=0&limit=50"
    assert page.count == 2
    first = page.items[0]
    assert (first.date, first.path, first.payload, first.status, first.error) == (
        1700000000,
        "GET /custody/c-1",
        '{"user":"c-1"}',
        200,
        None,
    )
    assert page.items[1].status == 416
    assert page.items[1].error == '{"error":true,"message":"requested_amount_error","code":416}'
    transport.will_answer(200, json.dumps({"count": 0, "items": []}))
    apikeys.logs("key-1")
    assert transport.last().url == "https://api.test/organization/org-uuid/apikeys/key-1/logs"


@pytest.mark.parametrize(
    ("status", "code", "call"),
    [
        (404, "unknown_apikey", lambda apikeys: apikeys.get("key-x")),
        (422, "invalid_include_revoked", lambda apikeys: apikeys.list(includeRevoked=True)),
        (403, "forbidden_permission", lambda apikeys: apikeys.logs("key-1")),
    ],
)
def test_api_errors_become_bitgen_errors(
    apikeys: ApikeysResource, transport: FakeTransport, status: int, code: str, call: Any
) -> None:
    transport.will_answer(status, json.dumps({"error": True, "message": code, "code": status}))
    with pytest.raises(BitgenError) as caught:
        call(apikeys)
    assert (caught.value.status, caught.value.code) == (status, code)


def test_invalid_arguments_are_refused_before_any_request(apikeys: ApikeysResource, transport: FakeTransport) -> None:
    with pytest.raises(ValueError):
        apikeys.get("")
    with pytest.raises(ValueError):
        apikeys.logs("..")
    with pytest.raises(TypeError, match=r"^includeRevoked must be a boolean$"):
        apikeys.list(includeRevoked=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^limit must be an integer$"):
        apikeys.logs("key-1", limit=True)  # a bool is an int for the type checker, not for the SDK
    assert transport.requests == []


def test_the_key_model_is_accepted(apikeys: ApikeysResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps(APIKEY))
    key = apikeys.get("key-1")
    transport.will_answer(200, json.dumps(APIKEY))
    apikeys.get(key)
    assert transport.last().url == "https://api.test/organization/org-uuid/apikeys/key-1"
    transport.will_answer(200, json.dumps({"count": 0, "items": []}))
    apikeys.logs(key, limit=10)
    assert transport.last().url == "https://api.test/organization/org-uuid/apikeys/key-1/logs?limit=10"
    sent = len(transport.requests)
    with pytest.raises(TypeError, match=r"^apikey must be a uuid string, or a Apikey model$"):
        apikeys.get(key.organization)  # type: ignore[arg-type]
    assert len(transport.requests) == sent

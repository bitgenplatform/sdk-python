"""The `transaction` resource against the fake transport: exact queries, mapping of the answers, errors, refusals."""

from __future__ import annotations

import json
from typing import Any

import pytest

from bitgen import Asset, BitgenError
from bitgen._http.client import HttpClient
from bitgen.models import (
    AssetRef,
    Created,
    CustomerState,
    Transaction,
    TransactionDirection,
    TransactionSource,
    TransactionState,
)
from bitgen.resources.transaction import TransactionResource
from tests.fake_transport import FakeTransport

OWNER: dict[str, Any] = {
    "uuid": "c-1",
    "state": "ENABLED",
    "login": "jean@valjean.fr",
    "account": {"firstname": "Jean", "lastname": "Valjean", "fin": None},
}
# A realistic transaction (contract § 8), on hold with a compliance alert
TRANSACTION: dict[str, Any] = {
    "uuid": "tx-1",
    "state": "PENDING",
    "source": "CUSTODY",
    "direction": "OUT",
    "asset": "ETH",
    "amount": 0.5,
    "eurValue": 1015.75,
    "reference": "withdraw-42",
    "credited": False,
    "silent": False,
    "data": {"targetAddress": "0xdef", "score": 12},
    "createdAt": 1700000000,
    "updatedAt": 1700003600,
    "owner": OWNER,
    "assignee": {
        "uuid": "officer-1",
        "state": "ENABLED",
        "login": "compliance@acme.fr",
        "account": {"firstname": "Ana", "lastname": None, "fin": None},
    },
    "organization": {"uuid": "org-uuid", "state": "ENABLED", "name": "ACME", "hub": {"uuid": "hub-1", "name": "HUB"}},
    "alert": {
        "uuid": "alert-1",
        "state": "OPEN",
        "severity": "WARNING",
        "type": "KYT",
        "description": "Unusual destination",
        "confidence": 72,
        "recommendation": "review",
        "factors": ["new_address"],
        "sources": {"kyt": {"risk": "medium"}},
        "history": [{"state": "OPEN", "at": 1700000000}],
        "incidentKey": "inc-1",
        "createdAt": 1700000000,
        "updatedAt": 1700000000,
        "user": {"uuid": "c-1"},
        "assignee": None,
        "organization": {"uuid": "org-uuid"},
    },
    "somethingNew": True,
}


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def transaction(transport: FakeTransport) -> TransactionResource:
    return TransactionResource(HttpClient(transport, "org-uuid", "k", "https://api.test", 1.0, "ua"))


def test_list_sends_the_exact_query_and_maps_transactions(
    transaction: TransactionResource, transport: FakeTransport
) -> None:
    transport.will_answer(200, json.dumps({"count": 1, "items": [TRANSACTION]}))
    page = transaction.list(
        user=Created("c-1"),
        status=TransactionState.PENDING,
        source=TransactionSource.CUSTODY,
        direction=TransactionDirection.OUT,
        asset=Asset.ETH,
        offset=0,
        limit=100,
    )
    assert (transport.last().method, transport.last().url) == (
        "GET",
        "https://api.test/transaction?user=c-1&status=PENDING&source=CUSTODY&direction=OUT&asset=eth&offset=0&limit=100",
    )
    assert page.count == 1
    assert page.items[0].uuid == "tx-1"
    transaction.list()
    assert transport.last().url == "https://api.test/transaction"
    transaction.list(
        user="c-1",
        status=TransactionState.COMPLETED,
        source=TransactionSource.BANK,
        direction=TransactionDirection.IN,
        asset="EUR",
    )
    assert (
        transport.last().url
        == "https://api.test/transaction?user=c-1&status=COMPLETED&source=BANK&direction=IN&asset=EUR"
    )
    assert page.items[0].owner is not None
    transaction.list(user=page.items[0].owner)  # the owner of a transaction carries a uuid
    assert transport.last().url == "https://api.test/transaction?user=c-1"


def test_get_maps_the_transaction(transaction: TransactionResource, transport: FakeTransport) -> None:  # noqa: PLR0915 - one assertion per field
    transport.will_answer(200, json.dumps(TRANSACTION))
    tx = transaction.get("tx-1")
    assert transport.last().url == "https://api.test/transaction/tx-1"
    assert isinstance(tx, Transaction)
    assert tx.uuid == "tx-1"
    assert tx.state == TransactionState.PENDING
    assert tx.source == TransactionSource.CUSTODY
    assert tx.direction == TransactionDirection.OUT
    assert tx.asset == "ETH"
    assert tx.amount == 0.5
    assert tx.eurValue == 1015.75
    assert tx.reference == "withdraw-42"
    assert tx.credited is False
    assert tx.silent is False
    assert tx.data == {"targetAddress": "0xdef", "score": 12}
    assert tx.createdAt == 1700000000
    assert tx.updatedAt == 1700003600
    assert tx.owner is not None
    assert (tx.owner.uuid, tx.owner.state, tx.owner.login) == ("c-1", CustomerState.ENABLED, "jean@valjean.fr")
    assert (tx.owner.account.firstname, tx.owner.account.lastname, tx.owner.account.fin) == ("Jean", "Valjean", None)
    assert tx.assignee is not None
    assert tx.assignee.uuid == "officer-1"
    assert tx.assignee.account.lastname is None
    assert tx.organization is not None
    assert (tx.organization.uuid, tx.organization.state, tx.organization.name) == ("org-uuid", "ENABLED", "ACME")
    assert tx.organization.hub is not None
    assert (tx.organization.hub.uuid, tx.organization.hub.name) == ("hub-1", "HUB")
    assert tx.alert is not None
    assert tx.alert.uuid == "alert-1"
    assert tx.alert.state == "OPEN"
    assert tx.alert.severity == "WARNING"
    assert tx.alert.type == "KYT"
    assert tx.alert.description == "Unusual destination"
    assert tx.alert.confidence == 72.0
    assert tx.alert.recommendation == "review"
    assert tx.alert.factors == ["new_address"]
    assert tx.alert.sources == {"kyt": {"risk": "medium"}}
    assert tx.alert.history == [{"state": "OPEN", "at": 1700000000}]
    assert tx.alert.incidentKey == "inc-1"
    assert tx.alert.createdAt == 1700000000
    assert tx.alert.user == {"uuid": "c-1"}
    assert tx.alert.assignee is None
    assert tx.alert.organization == {"uuid": "org-uuid"}
    # a completed bank deposit: no alert, no assignee, an organization without hub; by reference
    transport.will_answer(
        200,
        json.dumps(
            {
                "uuid": "tx-2",
                "state": "COMPLETED",
                "source": "BANK",
                "direction": "IN",
                "asset": "EUR",
                "amount": 150,
                "eurValue": None,
                "reference": None,
                "credited": True,
                "silent": False,
                "data": {},
                "createdAt": 1700000000,
                "updatedAt": 1700000000,
                "owner": OWNER,
                "assignee": None,
                "organization": {"uuid": "org-uuid", "state": "ENABLED", "name": "ACME", "hub": None},
                "alert": None,
            }
        ),
    )
    deposit = transaction.get("BANK-REF-42")
    assert transport.last().url == "https://api.test/transaction/BANK-REF-42"
    assert deposit.amount == 150.0
    assert deposit.eurValue is None
    assert deposit.reference is None
    assert deposit.credited is True
    assert deposit.data == {}
    assert deposit.assignee is None
    assert deposit.organization is not None
    assert deposit.organization.hub is None
    assert deposit.alert is None
    # a Transaction model is accepted: its uuid is sent
    transport.will_answer(200, json.dumps(TRANSACTION))
    transaction.get(tx)
    assert transport.last().url == "https://api.test/transaction/tx-1"


@pytest.mark.parametrize(
    ("status", "code", "call"),
    [
        (403, "forbidden_permission", lambda transaction: transaction.list()),
        (404, "unknown_user", lambda transaction: transaction.list(user="c-x")),
        (404, "unknown_transaction", lambda transaction: transaction.get("nope")),
        (400, "invalid_transaction_state", lambda transaction: transaction.list(status=TransactionState.PENDING)),
    ],
)
def test_api_errors_become_bitgen_errors(
    transaction: TransactionResource, transport: FakeTransport, status: int, code: str, call: Any
) -> None:
    transport.will_answer(status, json.dumps({"error": True, "message": code, "code": status}))
    with pytest.raises(BitgenError) as caught:
        call(transaction)
    assert (caught.value.status, caught.value.code) == (status, code)


def test_invalid_arguments_are_refused_before_any_request(
    transaction: TransactionResource, transport: FakeTransport
) -> None:
    with pytest.raises(
        ValueError, match=r"^status must be ANALYZING, PENDING, COMPLETED, FROZEN, FAILED, TRANSFERING or SEIZED$"
    ):
        transaction.list(status="pending")
    with pytest.raises(ValueError, match=r"^source must be BANK or CUSTODY$"):
        transaction.list(source="bank")
    with pytest.raises(ValueError, match=r"^direction must be IN or OUT$"):
        transaction.list(direction="in")
    with pytest.raises(ValueError):
        transaction.get("")
    with pytest.raises(TypeError, match=r"^transaction must be a uuid string, or a Transaction model$"):
        transaction.get(Created("tx-1"))  # type: ignore[arg-type]
    assert transport.requests == []


def test_models_are_accepted_for_the_transaction_the_customer_and_the_asset(
    transaction: TransactionResource, transport: FakeTransport
) -> None:
    transport.will_answer(200, json.dumps(TRANSACTION))
    tx = transaction.get("tx-1")
    transport.will_answer(200, json.dumps(TRANSACTION))
    transaction.get(tx)
    assert transport.last().url == "https://api.test/transaction/tx-1"
    assert tx.owner is not None
    transaction.list(user=tx.owner, asset=AssetRef("asset-eth", "ETH", "Ethereum"))
    assert transport.last().url == "https://api.test/transaction?user=c-1&asset=asset-eth"
    sent = len(transport.requests)
    with pytest.raises(TypeError, match=r"^transaction must be a uuid string, or a Transaction model$"):
        transaction.get(tx.owner)  # type: ignore[arg-type]
    assert len(transport.requests) == sent

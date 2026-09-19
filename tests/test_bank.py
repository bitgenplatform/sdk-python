"""The `bank` resource against the fake transport: exact bodies and queries, mapping of the answers, errors,
refusals."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import pytest

from bitgen import BitgenError
from bitgen._http.client import HttpClient
from bitgen.models import BankAccount, BankDirection, Created
from bitgen.resources.bank import BankResource
from tests.fake_transport import FakeTransport

ACCOUNT: dict[str, Any] = {
    "uuid": "b-1",
    "message": "BTGN-4242",
    "iban": "FR7630006000011234567890189",
    "bank": "BNP",
    "bic": "BNPAFRPP",
    "balance": 150.5,
    "history": {"d": [[1700000000, 100.0], [1700003600, 150.5]], "w": [], "m": [], "y": [], "all": []},
    "pending": {"in": 20, "out": 0},
    "somethingNew": True,
}


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def bank(transport: FakeTransport) -> BankResource:
    return BankResource(HttpClient(transport, "org-uuid", "k", "https://api.test", 1.0, "ua"))


def test_get_maps_the_account(bank: BankResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps(ACCOUNT))
    account = bank.get(Created("c-1"))
    assert (transport.last().method, transport.last().url) == ("GET", "https://api.test/bank/c-1")
    assert isinstance(account, BankAccount)
    assert account.uuid == "b-1"
    assert account.message == "BTGN-4242"
    assert account.iban == "FR7630006000011234567890189"
    assert account.bank == "BNP"
    assert account.bic == "BNPAFRPP"
    assert account.balance == 150.5
    assert account.history is not None
    assert account.history.d == [(1700000000, 100.0), (1700003600, 150.5)]
    assert account.pending.in_ == 20.0
    assert account.pending.out == 0.0
    # no bank details yet, history not materialized yet ({} in the answer)
    transport.will_answer(
        200,
        json.dumps(
            {
                "uuid": "b-2",
                "message": "BTGN-1",
                "iban": None,
                "bank": None,
                "bic": None,
                "balance": 0,
                "history": {},
                "pending": {"in": 0, "out": 0},
            }
        ),
    )
    fresh = bank.get("jean@valjean.fr")
    assert transport.last().url == "https://api.test/bank/jean%40valjean.fr"
    assert fresh.iban is None
    assert fresh.history is None
    assert fresh.balance == 0.0


def test_operations_send_the_exact_query_and_map_operations(bank: BankResource, transport: FakeTransport) -> None:
    transport.will_answer(
        200,
        json.dumps(
            {
                "count": 2,
                "items": [
                    {"txId": "t-1", "amount": 150.5, "direction": "DEPOSIT", "date": 1700000000, "info": None},
                    {"txId": "t-2", "amount": 25, "direction": "PURCHASE", "date": 1700003600, "info": "ETH"},
                ],
            }
        ),
    )
    page = bank.operations("c-1", direction=BankDirection.DEPOSIT, from_=1699000000, to=1701000000, offset=0, limit=50)
    assert (
        transport.last().url
        == "https://api.test/bank/c-1/operations?direction=DEPOSIT&from=1699000000&to=1701000000&offset=0&limit=50"
    )
    assert page.count == 2
    assert page.items[0].txId == "t-1"
    assert page.items[0].amount == 150.5
    assert page.items[0].direction == BankDirection.DEPOSIT
    assert page.items[0].date == 1700000000
    assert page.items[0].info is None
    assert page.items[1].amount == 25.0
    assert page.items[1].info == "ETH"

    bank.operations("c-1")
    assert transport.last().url == "https://api.test/bank/c-1/operations"
    bank.operations("c-1", direction=BankDirection.SELL)
    assert transport.last().url == "https://api.test/bank/c-1/operations?direction=SELL"


def test_withdraw_sends_the_amount_as_a_string_and_the_bank_details_when_given(
    bank: BankResource, transport: FakeTransport
) -> None:
    transport.will_answer(200, '{"transaction":"tx-1"}')
    withdrawal = bank.withdraw("c-1", 50)
    assert withdrawal.transaction == "tx-1"
    assert (transport.last().method, transport.last().url) == ("PUT", "https://api.test/bank/c-1")
    assert transport.last().body == b'{"amount":"50"}'
    bank.withdraw("c-1", "0.000000000000000001", iban="FR76…", bic="BNPAFRPP")
    assert transport.last().body == '{"amount":"0.000000000000000001","iban":"FR76…","bic":"BNPAFRPP"}'.encode()
    bank.withdraw("c-1", 12.5, bank="BNP")
    assert transport.last().body == b'{"amount":"12.5","bank":"BNP"}'
    bank.withdraw("c-1", Decimal("19.90"))
    assert transport.last().body == b'{"amount":"19.90"}'


def test_credit_targets_a_user_or_a_wire_message(bank: BankResource, transport: FakeTransport) -> None:
    transport.will_answer(201, '{"uuid":"d-1"}')
    credit = bank.credit("100.00", user=Created("c-1"), reference="BANK-REF-42")
    assert isinstance(credit, Created)
    assert credit.uuid == "d-1"
    assert (transport.last().method, transport.last().url) == ("POST", "https://api.test/bank")
    assert transport.last().body == b'{"amount":"100.00","user":"c-1","reference":"BANK-REF-42"}'
    bank.credit(100, message="BTGN-4242", currency="EUR")
    assert transport.last().body == b'{"amount":"100","currency":"EUR","message":"BTGN-4242"}'


@pytest.mark.parametrize(
    ("status", "code", "call"),
    [
        (412, "owner_identity_not_validated", lambda bank: bank.get("c-1")),
        (412, "ramp_not_enabled", lambda bank: bank.withdraw("c-1", "10")),
        (412, "deposit_reported_by_provider", lambda bank: bank.credit("10", message="BTGN-1")),
        (416, "invalid_amount", lambda bank: bank.withdraw("c-1", "0")),
        (403, "forbidden_permission", lambda bank: bank.operations("c-1")),
    ],
)
def test_api_errors_become_bitgen_errors(
    bank: BankResource, transport: FakeTransport, status: int, code: str, call: Any
) -> None:
    transport.will_answer(status, json.dumps({"error": True, "message": code, "code": status}))
    with pytest.raises(BitgenError) as caught:
        call(bank)
    assert (caught.value.status, caught.value.code) == (status, code)


def test_invalid_amounts_users_and_directions_are_refused_before_any_request(
    bank: BankResource, transport: FakeTransport
) -> None:
    amounts: list[str | int | float] = [-1, 1e-8, "", float("inf")]
    for amount in amounts:
        with pytest.raises(ValueError):
            bank.withdraw("c-1", amount)
        with pytest.raises(ValueError):
            bank.credit(amount, user="c-1")
    with pytest.raises(TypeError):
        bank.withdraw("c-1", True)
    with pytest.raises(ValueError):
        bank.get("")
    # a typo would silently mean ALL for the API
    with pytest.raises(ValueError, match=r"^direction must be ALL, DEPOSIT, WITHDRAWAL, PURCHASE or SELL$"):
        bank.operations("c-1", direction="deposit")
    with pytest.raises(TypeError, match=r"^from_ must be an integer$"):
        bank.operations("c-1", from_="yesterday")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^iban must be a string$"):
        bank.withdraw("c-1", "10", iban=123)  # type: ignore[arg-type]
    assert transport.requests == []

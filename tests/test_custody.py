"""The `custody` resource against the fake transport: exact requests, mapping of the answers, errors, refusals."""

from __future__ import annotations

import json
from typing import Any

import pytest

from bitgen import Asset, BitgenError, UnexpectedAnswerError
from bitgen._http.client import HttpClient
from bitgen.models import AssetRef, Created, TravelRulePerson, TravelRulePlatform, Wallet, WalletState, WalletType
from bitgen.resources.custody import CustodyResource
from tests.fake_transport import FakeTransport

HISTORY: dict[str, Any] = {
    "d": [[1700000000, 900.0], [1700003600, 1015.75]],
    "w": [[1699400000, 880.0]],
    "m": [],
    "y": [],
    "all": [],
}
WALLET: dict[str, Any] = {
    "uuid": "w-1",
    "state": "CREATED",
    "type": "USER",
    "address": "0xabc",
    "addressLegacy": None,
    "tag": None,
    "balance": "0.500000000000000001",
    "history": HISTORY,
    "asset": {"uuid": "asset-eth", "iso": "ETH", "label": "Ethereum"},
    "somethingNew": True,
}


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def custody(transport: FakeTransport) -> CustodyResource:
    return CustodyResource(HttpClient(transport, "org-uuid", "k", "https://api.test", 1.0, "ua"))


def test_wallets_map_the_list_without_history(custody: CustodyResource, transport: FakeTransport) -> None:
    eth = {key: value for key, value in WALLET.items() if key != "history"}
    xrp = {
        "uuid": "w-2",
        "state": "FROZEN",
        "type": "USER",
        "address": "rXRP",
        "addressLegacy": "XLEGACY",
        "tag": "12345",
        "balance": "10",
        "asset": {"uuid": "asset-xrp", "iso": "XRP", "label": "Ripple"},
    }
    transport.will_answer(200, json.dumps([eth, xrp]))
    wallets = custody.wallets(Created("c-1"))
    assert (transport.last().method, transport.last().url, transport.last().body) == (
        "GET",
        "https://api.test/custody/c-1",
        None,
    )
    assert len(wallets) == 2
    assert isinstance(wallets[0], Wallet)
    assert wallets[0].uuid == "w-1"
    assert wallets[0].state == WalletState.CREATED
    assert wallets[0].type == WalletType.USER
    assert wallets[0].address == "0xabc"
    assert wallets[0].addressLegacy is None
    assert wallets[0].tag is None
    assert wallets[0].balance == "0.500000000000000001"
    assert wallets[0].history is None
    assert (wallets[0].asset.uuid, wallets[0].asset.iso, wallets[0].asset.label) == ("asset-eth", "ETH", "Ethereum")
    assert wallets[1].state == WalletState.FROZEN
    assert wallets[1].addressLegacy == "XLEGACY"
    assert wallets[1].tag == "12345"
    assert wallets[1].balance == "10"
    # the treasury of the organization, by its uuid (the scope) — an empty list is an empty list
    transport.will_answer(200, "[]")
    assert custody.wallets("org-uuid") == []
    assert transport.last().url == "https://api.test/custody/org-uuid"


def test_wallet_reads_one_asset_with_history(custody: CustodyResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps(WALLET))
    wallet = custody.wallet("c-1", Asset.ETH)
    assert transport.last().url == "https://api.test/custody/c-1/eth"
    assert wallet.uuid == "w-1"
    assert wallet.history is not None
    assert wallet.history.d == [(1700000000, 900.0), (1700003600, 1015.75)]
    assert wallet.history.w == [(1699400000, 880.0)]
    assert wallet.history.all == []
    # a new wallet: the API initializes `history` to `{}` until the curve has been computed
    transport.will_answer(200, json.dumps({**WALLET, "history": {}}))
    assert custody.wallet("c-1", Asset.ETH).history is None
    custody.wallet("jean@valjean.fr", "asset-eth")
    assert transport.last().url == "https://api.test/custody/jean%40valjean.fr/asset-eth"
    custody.wallet("c-1", "BTC")  # sent as is: the API normalizes the case
    assert transport.last().url == "https://api.test/custody/c-1/BTC"
    custody.wallet("c-1", AssetRef("asset-btc", "BTC", "Bitcoin"))  # a model: its uuid
    assert transport.last().url == "https://api.test/custody/c-1/asset-btc"


def test_portfolio_has_its_own_path_and_two_shapes(custody: CustodyResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps({"uuid": "custody-1", "type": "USER", "history": HISTORY}))
    portfolio = custody.portfolio("c-1")
    assert transport.last().url == "https://api.test/custody/c-1/portfolio"
    assert portfolio.uuid == "custody-1"
    assert portfolio.type == WalletType.USER
    assert portfolio.history.d == [(1700000000, 900.0), (1700003600, 1015.75)]
    # flat `{ history }` at zero while the customer has no custody
    transport.will_answer(200, json.dumps({"history": {"d": [[1700000000, 0]], "w": [], "m": [], "y": [], "all": []}}))
    empty = custody.portfolio(Created("c-2"))
    assert empty.uuid is None
    assert empty.type is None
    assert empty.history.d == [(1700000000, 0.0)]


def test_withdraw_sends_the_exact_body(custody: CustodyResource, transport: FakeTransport) -> None:
    transport.will_answer(200, '{"transaction":"tx-1"}')
    withdrawal = custody.withdraw("c-1", Asset.ETH, "0.000000000000000001", "0xdef")
    assert withdrawal.transaction == "tx-1"
    assert (transport.last().method, transport.last().url) == ("PUT", "https://api.test/custody/c-1")
    assert transport.last().body == b'{"asset":"eth","amount":"0.000000000000000001","targetAddress":"0xdef"}'
    # every option, a person
    transport.will_answer(200, '{"transaction":null}')
    pending = custody.withdraw(
        Created("c-1"),
        Asset.XRP,
        10,
        "rDEST",
        targetTag="12345",
        idempotencyKey="withdraw-42",
        travelRule=TravelRulePerson(firstname="Jean", lastname="Valjean", address="1 rue de Paris"),
    )
    assert pending.transaction is None
    travel_rule = {"firstname": "Jean", "lastname": "Valjean", "address": "1 rue de Paris"}
    expected = {
        "asset": "xrp",
        "amount": "10",
        "targetAddress": "rDEST",
        "targetTag": "12345",
        "idempotencyKey": "withdraw-42",
        "travelRule": travel_rule,
    }
    assert transport.last().body == json.dumps(expected, separators=(",", ":")).encode()
    # a platform; a person with one field only sends that field
    custody.withdraw("c-1", "asset-eth", 0.5, "0xdef", travelRule=TravelRulePlatform("Kraken"))
    assert (
        transport.last().body
        == b'{"asset":"asset-eth","amount":"0.5","targetAddress":"0xdef","travelRule":{"platform":"Kraken"}}'
    )
    custody.withdraw("c-1", Asset.ETH, "1", "0xdef", travelRule=TravelRulePerson(lastname="Valjean"))
    assert (
        transport.last().body
        == b'{"asset":"eth","amount":"1","targetAddress":"0xdef","travelRule":{"lastname":"Valjean"}}'
    )


@pytest.mark.parametrize(
    ("status", "code", "call"),
    [
        (403, "kyc_not_validated", lambda custody: custody.wallet("c-1", Asset.ETH)),
        (403, "wallet_frozen", lambda custody: custody.withdraw("c-1", Asset.ETH, "1", "0xdef")),
        (412, "custody_not_enabled", lambda custody: custody.wallet("c-1", Asset.ETH)),
        (400, "invalid_amount", lambda custody: custody.withdraw("c-1", Asset.ETH, "0", "0xdef")),
        (416, "withdraw_below_minimum", lambda custody: custody.withdraw("c-1", Asset.ETH, "0.0001", "0xdef")),
        (422, "withdraw_target_invalid", lambda custody: custody.withdraw("c-1", Asset.ETH, "1", "nope")),
        (415, "custody_portfolio_treasury_unsupported", lambda custody: custody.portfolio("org-uuid")),
        (403, "org_forbidden", lambda custody: custody.wallets("c-1")),
        (403, "forbidden_permission", lambda custody: custody.wallets("c-1")),
    ],
)
def test_api_errors_become_bitgen_errors(
    custody: CustodyResource, transport: FakeTransport, status: int, code: str, call: Any
) -> None:
    transport.will_answer(status, json.dumps({"error": True, "message": code, "code": status}))
    with pytest.raises(BitgenError) as caught:
        call(custody)
    assert (caught.value.status, caught.value.code) == (status, code)


@pytest.mark.parametrize(
    "body", ['{"uuid":"w-1"}', '["w-1"]', '"text"'], ids=["an object", "a list of strings", "a string"]
)
def test_a_list_that_is_not_a_list_of_objects_is_a_contract_violation(
    custody: CustodyResource, transport: FakeTransport, body: str
) -> None:
    transport.will_answer(200, body)
    with pytest.raises(UnexpectedAnswerError):
        custody.wallets("c-1")


def test_invalid_arguments_are_refused_before_any_request(custody: CustodyResource, transport: FakeTransport) -> None:
    with pytest.raises(ValueError):
        custody.withdraw("c-1", Asset.ETH, -1, "0xdef")
    with pytest.raises(ValueError):
        custody.withdraw("c-1", Asset.ETH, "", "0xdef")
    with pytest.raises(ValueError):
        custody.withdraw("c-1", Asset.ETH, 1e-8, "0xdef")
    with pytest.raises(ValueError):
        custody.withdraw("", Asset.ETH, "1", "0xdef")
    with pytest.raises(ValueError):
        custody.wallet("c-1", "..")
    with pytest.raises(ValueError):
        custody.wallets(Created(""))
    with pytest.raises(ValueError, match=r"^a TravelRulePerson needs at least one of firstname, lastname or address$"):
        TravelRulePerson()  # an empty person is meaningless
    with pytest.raises(TypeError, match=r"^targetAddress must be a string$"):
        custody.withdraw("c-1", Asset.ETH, "1", None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^travelRule must be a TravelRulePerson or a TravelRulePlatform$"):
        custody.withdraw("c-1", Asset.ETH, "1", "0xdef", travelRule={"platform": "Kraken"})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^platform must be a string$"):
        TravelRulePlatform(42)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^lastname must be a string$"):
        TravelRulePerson(lastname=42)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        custody.wallet("c-1", 42)  # type: ignore[arg-type]
    assert transport.requests == []


def test_travel_rules_are_frozen_and_compare_by_value() -> None:
    person = TravelRulePerson(firstname="Jean")
    assert person == TravelRulePerson(firstname="Jean")
    assert person.to_dict() == {"firstname": "Jean"}
    assert TravelRulePlatform("Kraken").to_dict() == {"platform": "Kraken"}
    with pytest.raises(AttributeError):
        person.firstname = "x"  # type: ignore[misc]

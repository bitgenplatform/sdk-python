"""The `asset` resource against the fake transport: exact requests, mapping of the answers, errors, refusals."""

from __future__ import annotations

import copy
import json
import pickle
from typing import Any

import pytest

from bitgen import Asset, BitgenError, UnexpectedAnswerError
from bitgen._http.client import HttpClient
from bitgen.models import Asset as AssetModel
from bitgen.models import AssetRef, AssetState
from bitgen.resources.asset import AssetResource
from tests.fake_transport import FakeTransport

# A realistic `GET /asset/{asset}` body (contract § 3)
ETH: dict[str, Any] = {
    "uuid": "a1",
    "state": "AVAILABLE",
    "iso": "ETH",
    "label": "Ethereum",
    "contractAddress": "",
    "baseUnit": 18,
    "gasUnit": 21000,
    "logo": None,
    "data": '{"provider":"x"}',
    "fees": {"low": {"maxFee": 1}, "medium": None, "high": "fast", "computed": {"gas": "21000", "native": "0.000021"}},
    "ticker": {"price": 2031.5, "marketcap": 244000000000, "rank": 2, "percentChange24h": -1.2},
    "history": {
        "d": [[1700000000, 2000.5], [1700003600, 2031.5]],
        "w": [],
        "m": [[1699000000, 1900]],
        "y": [],
        "all": [],
    },
    "network": {
        "uuid": "n1",
        "state": "ENABLED",
        "caip2": "eip155:1",
        "label": "Ethereum",
        "gasBase": 1,
        "data": "{}",
        "type": {"uuid": "t1", "code": "EVM", "label": "EVM", "data": "{}"},
    },
    "somethingNew": "ignored",
}
TICKER: dict[str, Any] = {"price": 61230.4, "marketcap": 1.2e12, "rank": 1, "percentChange24h": 0.3}


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def asset(transport: FakeTransport) -> AssetResource:
    return AssetResource(HttpClient(transport, "org-uuid", "k", "https://api.test", 1.0, "ua"))


def test_list_maps_every_asset_of_the_page(asset: AssetResource, transport: FakeTransport) -> None:
    transport.will_answer(
        200, json.dumps({"count": 2, "items": [ETH, {"uuid": "a2", "state": "HIDDEN", "iso": "BTC"}]})
    )
    page = asset.list()
    assert (transport.last().method, transport.last().url) == ("GET", "https://api.test/asset")
    assert page.count == 2
    assert len(page.items) == 2
    assert page.items[0].iso == "ETH"
    assert page.items[1].state == AssetState.HIDDEN
    assert page.items[1].iso == "BTC"


def test_get_maps_every_field_of_the_contract(asset: AssetResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps(ETH))
    eth = asset.get(Asset.ETH)
    assert transport.last().url == "https://api.test/asset/eth"
    assert eth.uuid == "a1"
    assert eth.state == AssetState.AVAILABLE
    assert eth.iso == "ETH"
    assert eth.label == "Ethereum"
    assert eth.contractAddress == ""
    assert eth.baseUnit == 18
    assert eth.gasUnit == 21000
    assert eth.logo is None
    assert eth.data == '{"provider":"x"}'
    assert eth.fees.low == {"maxFee": 1}
    assert eth.fees.medium is None
    assert eth.fees.high == "fast"
    assert eth.fees.computed.gas == "21000"
    assert eth.fees.computed.native == "0.000021"
    assert eth.ticker.price == 2031.5
    assert eth.ticker.marketcap == 244000000000.0
    assert eth.ticker.rank == 2
    assert eth.ticker.percentChange24h == -1.2
    assert eth.history.d == [(1700000000, 2000.5), (1700003600, 2031.5)]
    assert eth.history.w == []
    assert eth.history.m == [(1699000000, 1900.0)]
    assert eth.network.uuid == "n1"
    assert eth.network.state == "ENABLED"
    assert eth.network.caip2 == "eip155:1"
    assert eth.network.gasBase == 1
    assert eth.network.type.code == "EVM"
    assert eth.network.type.uuid == "t1"
    assert isinstance(eth, AssetModel)


def test_get_sends_the_value_as_is_encoded_and_accepts_a_uuid_or_an_iso(
    asset: AssetResource, transport: FakeTransport
) -> None:
    transport.will_answer(200, json.dumps(ETH)).will_answer(200, json.dumps(ETH))
    asset.get("a1")
    assert transport.last().url == "https://api.test/asset/a1"
    asset.get("Eth/x")
    assert transport.last().url == "https://api.test/asset/Eth%2Fx"


def test_missing_fields_never_raise_and_absent_nullables_are_none(
    asset: AssetResource, transport: FakeTransport
) -> None:
    transport.will_answer(200, json.dumps({"uuid": "a1", "state": "ARCHIVED", "iso": "btc"}))
    btc = asset.get(Asset.BTC)
    assert btc.state == AssetState.ARCHIVED
    assert btc.logo is None
    assert btc.label == ""
    assert btc.baseUnit == 0
    assert btc.fees.low is None
    assert btc.fees.computed.gas == ""
    assert btc.ticker.price == 0.0
    assert btc.history.all == []
    assert btc.network.type.code == ""


def test_tickers_and_ticker(asset: AssetResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps({"count": 1, "items": [{"iso": "BTC", "ticker": TICKER}]}))
    tickers = asset.tickers()
    assert transport.last().url == "https://api.test/ticker"
    assert tickers.count == 1
    assert tickers.items[0].iso == "BTC"
    assert tickers.items[0].ticker.price == 61230.4
    assert tickers.items[0].ticker.rank == 1

    transport.will_answer(200, json.dumps({"iso": "BTC", "ticker": TICKER, "history": {"d": [[1700000000, 61000]]}}))
    btc = asset.ticker(Asset.BTC)
    assert transport.last().url == "https://api.test/ticker/btc"
    assert btc.iso == "BTC"
    assert btc.history.d == [(1700000000, 61000.0)]
    assert btc.history.y == []


@pytest.mark.parametrize(("status", "code"), [(403, "forbidden_permission"), (404, "unknown_asset")])
def test_api_errors_become_bitgen_errors(
    asset: AssetResource, transport: FakeTransport, status: int, code: str
) -> None:
    transport.will_answer(status, json.dumps({"error": True, "message": code, "code": status}))
    with pytest.raises(BitgenError) as caught:
        asset.get("nope")
    assert (caught.value.status, caught.value.code) == (status, code)
    transport.will_answer(403, json.dumps({"error": True, "message": "forbidden_permission", "code": 403}))
    with pytest.raises(BitgenError) as caught:
        asset.list()
    assert caught.value.code == "forbidden_permission"


@pytest.mark.parametrize("bad", ["", "  ", ".", ".."])
def test_invalid_segments_are_refused_before_any_request(
    asset: AssetResource, transport: FakeTransport, bad: str
) -> None:
    with pytest.raises(ValueError, match=r"^asset must"):
        asset.get(bad)
    with pytest.raises(ValueError, match=r"^iso must"):
        asset.ticker(bad)
    assert transport.requests == []


def test_a_state_outside_the_contract_is_kept_as_is(asset: AssetResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps({"uuid": "a1", "state": "BRAND_NEW", "iso": "x"}))
    assert asset.get("x").state == "BRAND_NEW"


def test_an_answer_that_is_not_an_object_is_a_contract_violation(
    asset: AssetResource, transport: FakeTransport
) -> None:
    transport.will_answer(200, '"just a string"')
    with pytest.raises(UnexpectedAnswerError, match=r"^the API answered a string instead of a JSON object$"):
        asset.get(Asset.ETH)
    transport.will_answer(200, "[]")
    with pytest.raises(UnexpectedAnswerError, match=r"^the API answered a JSON array instead of a JSON object$"):
        asset.list()


def test_an_asset_model_is_accepted_by_get_and_its_uuid_is_sent(asset: AssetResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps(ETH))
    eth = asset.get(Asset.ETH)
    transport.will_answer(200, json.dumps(ETH))
    asset.get(eth)
    assert transport.last().url == f"https://api.test/asset/{eth.uuid}"
    transport.will_answer(200, json.dumps(ETH))
    asset.get(AssetRef("asset-eth", "ETH", "Ethereum"))
    assert transport.last().url == "https://api.test/asset/asset-eth"

    sent = len(transport.requests)
    with pytest.raises(TypeError, match=r"^iso must be a string$"):
        asset.ticker(eth)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^asset must be a uuid or an ISO code string, or an Asset / AssetRef model$"):
        asset.get(42)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=r"model with a non-empty uuid$"):
        asset.get(AssetRef("", "ETH", "Ethereum"))
    assert len(transport.requests) == sent


def test_models_are_frozen_compare_by_value_and_survive_pickling(
    asset: AssetResource, transport: FakeTransport
) -> None:
    transport.will_answer(200, json.dumps(ETH)).will_answer(200, json.dumps(ETH))
    first, second = asset.get(Asset.ETH), asset.get(Asset.ETH)
    assert first == second
    with pytest.raises(AttributeError):
        first.iso = "BTC"  # type: ignore[misc]
    assert AssetState.VALUES == ("AVAILABLE", "UNAVAILABLE", "ARCHIVED", "HIDDEN")
    # an integrator caches or ships models across processes
    assert pickle.loads(pickle.dumps(first)) == first
    assert copy.deepcopy(first) == first
    assert repr(first).startswith("Asset(uuid='a1', state='AVAILABLE', iso='ETH'")

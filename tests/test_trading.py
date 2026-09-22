"""The `trading` resource against the fake transport: exact requests, mapping of the answers, errors, refusals."""

from __future__ import annotations

import json
from typing import Any

import pytest

from bitgen import Asset, BitgenError
from bitgen._http.client import HttpClient
from bitgen.models import AssetRef, Created, Order, OrderSide, OrderState, TradingDirection
from bitgen.resources.trading import TradingResource
from tests.fake_transport import FakeTransport

ORDER: dict[str, Any] = {
    "uuid": "o-1",
    "state": "DONE",
    "side": "BUY",
    "amount": "25.00",
    "reference": "order-42",
    "received": 0.0123,
    "executedPrice": 2031.5,
    "fee": 0.25,
    "completedAt": 1700003600,
    "createdAt": 1700000000,
    "user": {"uuid": "c-1", "login": "jean@valjean.fr"},
    "organization": {"uuid": "org-uuid", "name": "ACME"},
    "asset": {"uuid": "asset-eth", "iso": "ETH", "label": "Ethereum"},
    "somethingNew": True,
}


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def trading(transport: FakeTransport) -> TradingResource:
    return TradingResource(HttpClient(transport, "org-uuid", "k", "https://api.test", 1.0, "ua"))


def test_buy_and_sell_send_the_exact_body(trading: TradingResource, transport: FakeTransport) -> None:
    transport.will_answer(201, '{"tunnel":"o-1","state":"REGISTERED"}')
    created = trading.buy(Created("c-1"), Asset.ETH, "25.00", reference="order-42")
    assert created.tunnel == "o-1"
    assert created.state == OrderState.REGISTERED
    assert (transport.last().method, transport.last().url) == ("POST", "https://api.test/trading")
    assert transport.last().body == b'{"user":"c-1","asset":"eth","amount":"25.00","mode":"BUY","reference":"order-42"}'
    # no reference: the key is absent, not null; an int amount travels as a string
    trading.buy("c-1", "asset-eth", 25)
    assert transport.last().body == b'{"user":"c-1","asset":"asset-eth","amount":"25","mode":"BUY"}'
    transport.will_answer(201, '{"tunnel":"o-2","state":"REGISTERED"}')
    sale = trading.sell("c-1", Asset.ETH, "0.01")
    assert sale.tunnel == "o-2"
    assert transport.last().body == b'{"user":"c-1","asset":"eth","amount":"0.01","mode":"SELL"}'
    trading.sell("c-1", Asset.BTC, 0.5, reference="sale-1")
    assert transport.last().body == b'{"user":"c-1","asset":"btc","amount":"0.5","mode":"SELL","reference":"sale-1"}'
    trading.buy("c-1", AssetRef("asset-eth", "ETH", "Ethereum"), "25")  # a model: its uuid
    assert transport.last().body == b'{"user":"c-1","asset":"asset-eth","amount":"25","mode":"BUY"}'


def test_get_maps_the_order(trading: TradingResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps(ORDER))
    order = trading.get("o-1")
    assert (transport.last().method, transport.last().url) == ("GET", "https://api.test/trading/o-1")
    assert isinstance(order, Order)
    assert order.uuid == "o-1"
    assert order.state == OrderState.DONE
    assert order.side == OrderSide.BUY
    assert order.amount == "25.00"
    assert order.reference == "order-42"
    assert order.received == 0.0123
    assert order.executedPrice == 2031.5
    assert order.fee == 0.25
    assert order.completedAt == 1700003600
    assert order.createdAt == 1700000000
    assert (order.user.uuid, order.user.login) == ("c-1", "jean@valjean.fr")
    assert (order.organization.uuid, order.organization.name) == ("org-uuid", "ACME")
    assert (order.asset.uuid, order.asset.iso, order.asset.label) == ("asset-eth", "ETH", "Ethereum")
    # a fresh order: nothing received yet
    transport.will_answer(
        200,
        json.dumps(
            {
                **ORDER,
                "uuid": "o-2",
                "state": "REGISTERED",
                "side": "SELL",
                "amount": "0.01",
                "reference": None,
                "received": None,
                "executedPrice": None,
                "fee": None,
                "completedAt": None,
            }
        ),
    )
    fresh = trading.get("o-2")
    assert fresh.side == OrderSide.SELL
    assert fresh.reference is None
    assert fresh.received is None
    assert fresh.executedPrice is None
    assert fresh.fee is None
    assert fresh.completedAt is None
    # an Order model is accepted: its uuid is sent
    transport.will_answer(200, json.dumps(ORDER))
    trading.get(order)
    assert transport.last().url == "https://api.test/trading/o-1"


def test_list_sends_the_exact_query_and_maps_orders(trading: TradingResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps({"count": 1, "items": [ORDER]}))
    page = trading.list(user=Created("c-1"), direction=TradingDirection.SELL, asset=Asset.ETH, offset=0, limit=50)
    assert transport.last().url == "https://api.test/trading/orders?user=c-1&direction=sell&asset=eth&offset=0&limit=50"
    assert page.count == 1
    assert page.items[0].uuid == "o-1"
    assert page.items[0].state == OrderState.DONE
    trading.list()
    assert transport.last().url == "https://api.test/trading/orders"
    trading.list(user="c-1", direction=TradingDirection.BUY, asset="ETH")  # an ISO code in upper case is sent as is
    assert transport.last().url == "https://api.test/trading/orders?user=c-1&direction=buy&asset=ETH"
    trading.list(user=page.items[0].user)  # the user of an order carries a uuid
    assert transport.last().url == "https://api.test/trading/orders?user=c-1"
    trading.list(asset=page.items[0].asset)  # the asset of an order: its uuid
    assert transport.last().url == "https://api.test/trading/orders?asset=asset-eth"


@pytest.mark.parametrize(
    ("status", "code", "call"),
    [
        (403, "kyc_not_validated", lambda trading: trading.buy("c-1", Asset.ETH, "25.00")),
        (404, "unknown_order", lambda trading: trading.get("o-x")),
        (412, "price_unavailable", lambda trading: trading.buy("c-1", Asset.ETH, "25.00")),
        (416, "requested_amount_error", lambda trading: trading.sell("c-1", Asset.ETH, "100")),
        (422, "invalid_asset", lambda trading: trading.buy("c-1", "xyz", "25.00")),
        (
            422,
            "asset_not_supported",
            lambda trading: trading.sell("c-1", "xyz", "1"),
        ),  # a custody error surfacing through a sale
        (403, "user_not_in_scope", lambda trading: trading.buy("c-1", Asset.ETH, "25.00")),
        (404, "unknown_user", lambda trading: trading.list(user="c-x")),
        (403, "forbidden_permission", lambda trading: trading.list()),
        (
            429,
            "daily_buy_limit_exceeded",
            lambda trading: trading.buy("c-1", Asset.ETH, "25.00"),
        ),  # sandbox only: daily purchase cap per customer
    ],
)
def test_api_errors_become_bitgen_errors(
    trading: TradingResource, transport: FakeTransport, status: int, code: str, call: Any
) -> None:
    transport.will_answer(status, json.dumps({"error": True, "message": code, "code": status}))
    with pytest.raises(BitgenError) as caught:
        call(trading)
    assert (caught.value.status, caught.value.code) == (status, code)


def test_invalid_arguments_are_refused_before_any_request(trading: TradingResource, transport: FakeTransport) -> None:
    with pytest.raises(ValueError, match=r"^direction must be buy or sell$"):
        trading.list(direction="BUY")  # the filter is lowercase: the API would silently ignore it
    with pytest.raises(ValueError):
        trading.buy("c-1", Asset.ETH, -1)
    with pytest.raises(ValueError):
        trading.sell("c-1", Asset.ETH, "")
    with pytest.raises(ValueError):
        trading.buy("", Asset.ETH, "25")
    with pytest.raises(ValueError):
        trading.get("")
    with pytest.raises(ValueError):
        trading.get("..")
    with pytest.raises(TypeError, match=r"^order must be a uuid string, or a Order model$"):
        trading.get(Created("o-1"))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^reference must be a string$"):
        trading.buy("c-1", Asset.ETH, "25", reference=42)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        trading.list(user={"uuid": "c-1"})  # type: ignore[arg-type]
    assert transport.requests == []

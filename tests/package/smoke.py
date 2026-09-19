"""The installed wheel against the test server: `PYTHONPATH=<repo> <blank venv>/bin/python tests/package/smoke.py`,
where only the wheel is installed — `bitgen` must come from site-packages, not from `src/`."""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable
from pathlib import Path

import bitgen
from bitgen import Asset, BitgenClient, BitgenError
from bitgen.models import (
    ApikeyState,
    AssetState,
    BankDirection,
    CoreState,
    CoreType,
    KycIdentity,
    Locale,
    OrderState,
    StakingMovementKind,
    StakingMovementState,
    StakingPositionState,
    SubscriberState,
    TradingDirection,
    TransactionSource,
    TransactionState,
    TravelRulePlatform,
    WebhookEventName,
)
from tests.server import Server
from tests.server.docs import DocsHandler
from tests.server.router import RouterHandler

KEY = "SECRET-KEY-NEVER-SHOWN"


def refused(call: Callable[[], object], status: int, code: str) -> None:
    """`call` must raise a `BitgenError` carrying exactly this status and code"""
    try:
        call()
    except BitgenError as error:
        assert (error.status, error.code) == (status, code), (error.status, error.code)
    else:
        raise AssertionError(f"expected {status} {code}, the call answered without an error")


def main() -> None:  # noqa: PLR0915 - one journey through every resource, it grows with them
    origin = Path(bitgen.__file__).resolve()
    assert "site-packages" in origin.parts, f"bitgen was imported from {origin}, not from the installed wheel"
    server = Server(RouterHandler).start()
    try:
        client = BitgenClient(
            scope="org-uuid", apiKey=KEY, host="127.0.0.1", port=server.port, isSsl=False, timeout=0.5
        )
        http = client._http  # the resources are not there yet: the HTTP layer stands for them
        echo = http.post("/ok", {"amount": "0.05"})
        assert echo["method"] == "POST" and echo["body"] == '{"amount":"0.05"}', echo
        headers = echo["headers"]
        assert headers["User-Agent"] == f"bitgen-sdk-python/{bitgen.VERSION}", headers
        assert headers["BITGEN-Scope"] == "org-uuid" and headers["Api-key"] == KEY, headers
        assert headers["Content-Length"] == str(len(echo["body"])), headers
        assert http.get("/empty") is None
        expected = {
            "/error": (412, "bank_rib_required"),
            "/hang": (0, "request_timeout"),
            "/redirect": (302, "Found"),
            "/text": (200, "plain text"),
            "/leak": (502, "Bad gateway while sending Api-key: [redacted]"),
            "/reflect": (0, "network_error"),
        }
        for path, (status, code) in expected.items():
            try:
                http.get(path)
            except BitgenError as error:
                assert (error.status, error.code) == (status, code), (path, error.status, error.code)
                chain = repr(error) + repr(error.__cause__) + repr(getattr(error.__cause__, "__cause__", None))
                assert KEY not in chain, path
            else:
                raise AssertionError(f"{path} answered without an error")
    finally:
        server.close()
    docs = Server(DocsHandler).start()
    try:
        client = BitgenClient(scope="org-uuid", apiKey=KEY, host="127.0.0.1", port=docs.port, isSsl=False, timeout=5)
        page = client.asset.list()
        assert page.count == 4 and [a.iso for a in page.items] == ["BTC", "ETH", "USDC", "SOL"], page
        eth = client.asset.get(Asset.ETH)
        assert (eth.state, eth.baseUnit, eth.ticker.price, len(eth.history.d)) == (AssetState.AVAILABLE, 18, 2031.5, 24)
        assert client.asset.get(eth).uuid == eth.uuid and client.asset.ticker(Asset.BTC).iso == "BTC"
        refused(lambda: client.asset.get(Asset.XRP), 404, "unknown_asset")  # not in the catalogue of the docs server
        created = client.customer.create("jean@valjean.fr", "MANAGER_UUID", locale=Locale.FR)
        assert created.uuid == "CUSTOMER_UUID", created
        account = client.customer.get(created)
        assert isinstance(account.identity, KycIdentity) and account.identity.form.source_income == "salary", account
        assert client.customer.list().items[0].login == "jean@valjean.fr"
        client.customer.update(created, locale=Locale.EN, notifications={"newsletter": False})
        eur = client.bank.get(account)
        assert (eur.message, eur.balance, eur.pending.in_) == ("BTGN-4242", 150.0, 0.0), eur
        assert (
            client.bank.operations(created, direction=BankDirection.DEPOSIT).items[0].direction == BankDirection.DEPOSIT
        )
        assert client.bank.withdraw(created, "50.00", iban="FR76").transaction == "transaction-1"
        assert client.bank.credit("100.00", user=created, reference="ref").uuid == "deposit-1"
        wallets = client.custody.wallets(created)
        assert [w.asset.iso for w in wallets] == ["ETH", "BTC"] and wallets[0].history is None, wallets
        wallet = client.custody.wallet(created, Asset.ETH)
        assert wallet.balance == "0.5" and wallet.history is not None and len(wallet.history.d) == 24, wallet
        assert client.custody.wallet(created, wallet.asset).uuid == wallet.uuid
        assert client.custody.portfolio(created).uuid == "custody-1"
        assert (
            client.custody.withdraw(
                created, Asset.ETH, "0.05", "0xdef", travelRule=TravelRulePlatform("Kraken")
            ).transaction
            == "transaction-2"
        )
        placed = client.trading.buy(created, Asset.ETH, "25.00", reference="order-42")
        assert (placed.tunnel, placed.state) == ("ORDER_UUID", OrderState.REGISTERED), placed
        order = client.trading.get(placed.tunnel)
        assert (order.state, order.received, client.trading.get(order).uuid) == (
            OrderState.DONE,
            0.0123,
            "ORDER_UUID",
        ), order
        assert client.trading.list(user=created, direction=TradingDirection.BUY).count == 2
        refused(lambda: client.trading.get("nope"), 404, "unknown_order")
        journal = client.transaction.list(user=created, status=TransactionState.PENDING, limit=100)
        assert journal.count == 3 and journal.items[1].source == TransactionSource.CUSTODY, journal
        transaction = client.transaction.get("BANK-TRANSFER-REF-42")  # by reference
        assert (transaction.uuid, transaction.credited, transaction.alert) == ("transaction-3", True, None), transaction
        assert transaction.owner is not None and transaction.owner.uuid == "CUSTOMER_UUID"
        assert client.transaction.get(transaction).uuid == "transaction-3"
        assert client.transaction.list(user=transaction.owner).count == 3  # the owner is a UserRef
        refused(lambda: client.transaction.get("nope"), 404, "unknown_transaction")
        providers = client.staking.providers(Asset.SOL)
        assert providers.count == 1 and providers.items[0].name == "figment_sol", providers
        assert providers.items[0].asset is not None and providers.items[0].asset.iso == "SOL"
        assert [f.name for f in providers.items[0].config][:3] == ["connector", "apr", "min_deposit"]
        assert client.staking.providers().count == 2 and client.core.list(type=CoreType.RAMP).count == 1
        assert client.core.list(state=CoreState.DISABLED).count == 0 and client.core.list().count == 5
        core = client.core.get("CORE_UUID")
        assert core.type == CoreType.STAKING and client.core.get(core).uuid == "CORE_UUID", core
        movement_created = client.staking.stake(created, Asset.SOL, "2", core.name)
        assert movement_created.uuid == "MOVEMENT_UUID", movement_created
        movement = client.staking.get(movement_created.uuid)
        assert (movement.kind, movement.state, movement.amount) == (
            StakingMovementKind.STAKE,
            StakingMovementState.COMPLETED,
            "2",
        ), movement
        position = movement.staking
        assert (position.uuid, position.state, position.data.rewards) == (
            "POSITION_UUID",
            StakingPositionState.ENABLED,
            "0.0123",
        )
        assert client.staking.get(movement).uuid == "MOVEMENT_UUID"
        client.staking.rewards(position)
        client.staking.rewards(position.uuid, "0.01")
        client.staking.unstake(position, "1")
        client.staking.unstake(position.uuid)
        assert client.staking.list(user=movement.owner, direction=StakingMovementKind.STAKE).count == 1
        assert client.staking.movements(user=created).count == 0
        operations = client.staking.operations(created, limit=50)
        assert operations.count == 2 and operations.items[1].event == "reward", operations
        assert operations.items[0].movement == "MOVEMENT_UUID" and operations.items[1].movement is None
        staking_portfolio = client.staking.portfolio(created)
        assert (staking_portfolio.balances.capital, len(staking_portfolio.histories.revenues.m)) == (256.8, 30)
        refused(lambda: client.staking.get("nope"), 404, "unknown_staking_movement")
        client.webhooks.activate("https://example.com/bitgen")
        client.webhooks.updateEndpoint("https://example.com/bitgen/v2")
        client.webhooks.regenerate()
        subscriptions = client.webhooks.list(includeArchived=True)
        assert subscriptions.secret.startswith("whsec_") and subscriptions.endpoint == "https://example.com/bitgen"
        assert [s.state for s in subscriptions.items] == [SubscriberState.ENABLED, SubscriberState.ARCHIVED]
        assert subscriptions.items[0].webhook.name == WebhookEventName.CUSTODY_SENT
        assert client.webhooks.subscribe(WebhookEventName.CUSTODY_SENT).uuid == "SUBSCRIBER_UUID"
        assert client.webhooks.subscribe(subscriptions.items[0].webhook).uuid == "SUBSCRIBER_UUID"
        client.webhooks.archive(subscriptions.items[0])
        client.webhooks.reactivate("SUBSCRIBER_UUID")
        attempts = client.webhooks.logs(subscriptions.items[0], limit=10)
        assert attempts.count == 2 and attempts.items[1].error == "connection refused", attempts
        assert attempts.items[0].payload["delivery_id"] == "delivery-1"
        catalog = client.webhooks.catalog()
        assert catalog.count == 5 and client.webhooks.catalogItem(catalog.items[0]).uuid == "WEBHOOK_UUID"
        refused(lambda: client.webhooks.catalogItem("nope"), 404, "unknown_webhook")
        secret = subscriptions.secret
        raw_body = b'{"delivery_id":"delivery-1","timestamp":1701000000,"event":"custody.sent","data":{"amount":"0.5"}}'
        timestamp = str(int(time.time()))
        digest = hmac.new(secret.encode(), timestamp.encode() + b"." + raw_body, hashlib.sha256).hexdigest()
        environ = {"HTTP_X_BITGEN_TIMESTAMP": timestamp, "HTTP_X_BITGEN_SIGNATURE": "sha256=" + digest}
        event = client.webhooks.verify(raw_body, environ, secret)
        assert (event.delivery_id, event.event, event.data) == (
            "delivery-1",
            WebhookEventName.CUSTODY_SENT,
            {"amount": "0.5"},
        )
        refused(lambda: client.webhooks.verify(raw_body, environ, "another-secret"), 0, "invalid_signature")
        refused(lambda: client.webhooks.verify(raw_body + b" ", environ, secret), 0, "invalid_signature")
        refused(lambda: client.webhooks.verify(raw_body, {}, secret), 0, "missing_signature")
        keys = client.apikeys.list(includeRevoked=True)
        assert keys.count == 1 and keys.items[0].state == ApikeyState.ENABLED, keys
        key = client.apikeys.get(keys.items[0])
        assert key.uuid == "APIKEY_UUID" and key.organization.owner is not None, key
        assert key.organization.owner.login == "ceo@acme.fr" and key.organization.hub is None
        calls = client.apikeys.logs(key, limit=50)
        assert calls.count == 2 and calls.items[1].status == 416, calls
        refused(lambda: client.apikeys.get("nope"), 404, "unknown_apikey")
    finally:
        docs.close()
    resources = "transport, asset, customer, bank, custody, trading, transaction, core, staking, webhooks, apikeys"
    print(f"wheel smoke OK ({resources}) — bitgen {bitgen.VERSION} from {origin.parent}")


if __name__ == "__main__":
    main()

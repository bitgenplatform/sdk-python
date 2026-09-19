"""What an integrator writes — checked with `mypy --strict` against the installed wheel (see the `package` job of the
CI). Every `# type: ignore[...]` is a mistake mypy must catch: `warn_unused_ignores` fails if it stops catching it."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from bitgen import VERSION, Asset, BitgenClient, BitgenError, Env, Page, UnexpectedAnswerError
from bitgen.models import (
    Account,
    Apikey,
    ApikeyLog,
    ApikeyState,
    AssetRef,
    AssetState,
    AssetTickerDetail,
    BankAccount,
    BankDirection,
    Core,
    CoreState,
    CoreType,
    Created,
    CustodyPortfolio,
    Customer,
    DeliveryLog,
    History,
    KycIdentity,
    Locale,
    Order,
    OrderCreated,
    OrderState,
    OrganizationCategory,
    StakingMovement,
    StakingMovementKind,
    StakingMovementState,
    StakingOperation,
    StakingPortfolio,
    StakingPosition,
    StakingPositionState,
    Subscriber,
    SubscriberState,
    TradingDirection,
    Transaction,
    TransactionAlert,
    TransactionDirection,
    TransactionSource,
    TransactionState,
    TravelRulePerson,
    TravelRulePlatform,
    UserSummary,
    Wallet,
    WalletType,
    WebhookEvent,
    WebhookEventName,
    WebhookSubscriptions,
    WebhookType,
)
from bitgen.models import Asset as AssetModel
from bitgen.resources import (
    ApikeysResource,
    AssetResource,
    BankResource,
    CoreResource,
    CustodyResource,
    CustomerResource,
    StakingResource,
    TradingResource,
    TransactionResource,
    WebhooksResource,
)

# --- valid usage -------------------------------------------------------------------------------------------------
client = BitgenClient(scope="YOUR_SCOPE_UUID", apiKey="YOUR_API_KEY", env=Env.SANDBOX, timeout=10)
custom = BitgenClient(scope="s", apiKey="k", host="my-hostname", port=8080, isSsl=False, timeout=0.5)
environment: str = Env.SANDBOX
assets: tuple[str, ...] = Asset.VALUES
version: str = VERSION


def uuid_of(item: Mapping[str, Any]) -> str:
    return str(item["uuid"])


page: Page[str] = Page.from_dict({"count": 1, "items": [{"uuid": "a"}]}, uuid_of)
items: list[str] = page.items
count: int = page.count

resource: AssetResource = client.asset
customers: CustomerResource = client.customer
bank: BankResource = client.bank
custody: CustodyResource = client.custody
trading: TradingResource = client.trading
transactions: TransactionResource = client.transaction
cores: CoreResource = client.core
staking: StakingResource = client.staking
webhooks: WebhooksResource = client.webhooks
apikeys: ApikeysResource = client.apikeys


def journey() -> None:
    created: Created = client.customer.create(
        "jean@valjean.fr", "MANAGER_UUID", locale=Locale.FR, organization=OrganizationCategory.B2B
    )
    listed: Page[Customer] = client.customer.list(offset=0, limit=50, includeClosed=False)
    account: Account = client.customer.get(created)
    same: Account = client.customer.get(listed.items[0])
    client.customer.update(account, locale=Locale.EN, notifications={"login": True})
    if isinstance(account.identity, KycIdentity):
        income: str | None = account.identity.form.source_income
        del income
    eur: BankAccount = client.bank.get(created)
    pending_in: float = eur.pending.in_
    curve: History | None = eur.history
    operations = client.bank.operations(created, direction=BankDirection.DEPOSIT, from_=1, to=2)
    label: str | None = operations.items[0].info
    withdrawal: str = client.bank.withdraw(created, Decimal("50.00"), iban="FR76").transaction
    deposit: Created = client.bank.credit("100.00", user=created, reference="ref")
    wallets: list[Wallet] = client.custody.wallets(created)
    wallet: Wallet = client.custody.wallet(created, Asset.ETH)
    by_model: Wallet = client.custody.wallet(created, wallet.asset)
    treasury: bool = wallet.type == WalletType.TREASURY
    portfolio: CustodyPortfolio = client.custody.portfolio(created)
    custody_uuid: str | None = portfolio.uuid
    sent: str | None = client.custody.withdraw(
        created, wallet.asset, "0.05", "0xdef", idempotencyKey="k", travelRule=TravelRulePlatform("Kraken")
    ).transaction
    person: TravelRulePerson = TravelRulePerson(lastname="Valjean")
    placed: OrderCreated = client.trading.buy(created, Asset.ETH, Decimal("25.00"), reference="order-42")
    order: Order = client.trading.get(placed.tunnel)
    again_order: Order = client.trading.get(order)
    done: bool = order.state == OrderState.DONE
    received: float | None = order.received
    orders: Page[Order] = client.trading.list(
        user=order.user, direction=TradingDirection.SELL, asset=order.asset, limit=10
    )
    sale: OrderCreated = client.trading.sell(created, order.asset, "0.01")
    del (
        same,
        pending_in,
        curve,
        label,
        withdrawal,
        deposit,
        wallets,
        by_model,
        treasury,
        custody_uuid,
        sent,
        person,
        again_order,
        done,
        received,
        orders,
        sale,
    )


def ledger(created: Created, order: Order) -> None:
    journal: Page[Transaction] = client.transaction.list(
        user=created,
        status=TransactionState.PENDING,
        source=TransactionSource.CUSTODY,
        direction=TransactionDirection.OUT,
        asset=order.asset,
        limit=100,
    )
    transaction: Transaction = client.transaction.get(journal.items[0])
    transaction = client.transaction.get(transaction.uuid)
    owner: UserSummary | None = transaction.owner
    alert: TransactionAlert | None = transaction.alert
    credited: bool = transaction.credited
    if owner is not None:
        by_owner: Page[Transaction] = client.transaction.list(user=owner)
        del by_owner
    providers: Page[Core] = client.staking.providers(Asset.SOL)
    provider: Core = providers.items[0]
    enabled: bool = provider.state == CoreState.ENABLED and provider.type == CoreType.STAKING
    minimum: Any = provider.config[0].data.value
    movement_created: Created = client.staking.stake(created, Asset.SOL, "2", provider.name)
    movement: StakingMovement = client.staking.get(movement_created.uuid)
    again_movement: StakingMovement = client.staking.get(movement)
    position: StakingPosition = movement.staking
    active: bool = position.state == StakingPositionState.ENABLED
    completed: bool = movement.state == StakingMovementState.COMPLETED
    rewards: str | None = position.data.rewards
    client.staking.rewards(position)
    client.staking.rewards(position.uuid, Decimal("0.01"))
    client.staking.unstake(position, "1")
    client.staking.unstake(position.uuid)
    movements: Page[StakingMovement] = client.staking.list(user=movement.owner, direction=StakingMovementKind.STAKE)
    in_progress: Page[StakingMovement] = client.staking.movements(user=created, offset=0, limit=10)
    staking_operations: Page[StakingOperation] = client.staking.operations(created, limit=50)
    operation_movement: str | None = staking_operations.items[0].movement
    staking_portfolio: StakingPortfolio = client.staking.portfolio(created)
    capital: float = staking_portfolio.balances.capital
    capital_curve: History = staking_portfolio.histories.capital
    connectors: Page[Core] = client.core.list(type=CoreType.RAMP, state=CoreState.ENABLED)
    by_asset: Page[Core] = client.core.list(asset=movement.asset)
    core: Core = client.core.get(position.core.uuid)
    again_core: Core = client.core.get(core)
    core_asset: AssetRef | None = core.asset
    del (
        journal,
        alert,
        credited,
        enabled,
        minimum,
        again_movement,
        active,
        completed,
        rewards,
        movements,
        in_progress,
        operation_movement,
        capital,
        capital_curve,
        connectors,
        by_asset,
        again_core,
        core_asset,
    )


def deliveries(raw_body: bytes, received: dict[str, str], environ: dict[str, Any]) -> None:
    client.webhooks.activate("https://example.com/bitgen")
    client.webhooks.updateEndpoint("https://example.com/bitgen/v2")
    client.webhooks.regenerate()
    subscriptions: WebhookSubscriptions = client.webhooks.list(includeArchived=True)
    secret: str = subscriptions.secret
    subscription: Subscriber = subscriptions.items[0]
    archived: bool = subscription.state == SubscriberState.ARCHIVED
    kind: WebhookType = subscription.webhook
    created: Created = client.webhooks.subscribe(WebhookEventName.CUSTODY_SENT)
    by_uuid: Created = client.webhooks.subscribe("WEBHOOK_UUID")
    by_model: Created = client.webhooks.subscribe(kind)
    client.webhooks.archive(created.uuid)
    client.webhooks.reactivate(subscription)
    attempts: Page[DeliveryLog] = client.webhooks.logs(subscription, offset=0, limit=10)
    http_code: int | None = attempts.items[0].http_code
    payload: dict[str, Any] = attempts.items[0].payload
    catalog: Page[WebhookType] = client.webhooks.catalog()
    item: WebhookType = client.webhooks.catalogItem(catalog.items[0])
    label: str = item.label
    event: WebhookEvent = client.webhooks.verify(raw_body, received, secret)
    same: WebhookEvent = client.webhooks.verify(raw_body.decode(), environ, secret, tolerance=60)
    strict: WebhookEvent = client.webhooks.verify(raw_body, received, secret, 0.5)
    asgi: WebhookEvent = client.webhooks.verify(raw_body, [(b"x-bitgen-signature", b"sha256=...")], secret)
    name: str = event.event
    delivered: bool = name == WebhookEventName.CUSTODY_SENT
    data: Any = event.data
    stamp: int = event.timestamp
    window: int = WebhooksResource.DEFAULT_TOLERANCE
    keys: Page[Apikey] = client.apikeys.list(includeRevoked=True, limit=50)
    key: Apikey = client.apikeys.get(keys.items[0])
    revoked: bool = key.state == ApikeyState.REVOKED
    permissions: list[str] = key.permissions
    owner_login: str | None = key.organization.owner.login if key.organization.owner else None
    calls: Page[ApikeyLog] = client.apikeys.logs(key, offset=0, limit=50)
    outcome: str | None = calls.items[0].error
    del (
        archived,
        by_uuid,
        by_model,
        http_code,
        payload,
        label,
        same,
        strict,
        asgi,
        delivered,
        data,
        stamp,
        window,
        revoked,
        permissions,
        owner_login,
        outcome,
    )


def catalogue() -> None:
    assets: Page[AssetModel] = client.asset.list()
    eth: AssetModel = client.asset.get(Asset.ETH)
    again: AssetModel = client.asset.get(eth)
    by_ref: AssetModel = client.asset.get(AssetRef("asset-eth", "ETH", "Ethereum"))
    state: str = eth.state
    available: bool = state == AssetState.AVAILABLE
    decimals: int = eth.baseUnit
    price: float = eth.ticker.price
    logo: str | None = eth.logo
    prices: History = eth.history
    epoch, value = prices.d[0]
    stamp: int = epoch
    quote: float = value
    detail: AssetTickerDetail = client.asset.ticker(Asset.BTC)
    iso: str = detail.iso
    del assets, again, by_ref, available, decimals, price, logo, stamp, quote, iso


try:
    pass
except BitgenError as error:
    status: int = error.status
    code: str = error.code
    message: str = str(error)
    cause: BaseException | None = error.__cause__
except UnexpectedAnswerError as unexpected:
    text: str = str(unexpected)

# --- mistakes mypy must catch -----------------------------------------------------------------------------------
BitgenClient(scope=1, apiKey="k")  # type: ignore[arg-type]
BitgenClient("s", "k")  # type: ignore[misc]
BitgenClient(scope="s", apiKey="k", port="80")  # type: ignore[arg-type]
BitgenClient(scope="s", apiKey="k", isSsl="no")  # type: ignore[arg-type]
BitgenClient(scope="s", apiKey="k", timeout="30")  # type: ignore[arg-type]
Env.SANDBOX = "x"  # type: ignore[misc]
wrong: Page[int] = Page.from_dict({}, uuid_of)  # type: ignore[arg-type]
number: int = BitgenError(416, "invalid_amount").code  # type: ignore[assignment]
client.asset.get(42)  # type: ignore[arg-type]
client.asset.ticker(AssetRef("u", "ETH", "Ethereum"))  # type: ignore[arg-type]
AssetState.AVAILABLE = "x"  # type: ignore[misc]
decimals_as_text: str = client.asset.get(Asset.ETH).baseUnit  # type: ignore[assignment]
client.customer.create("jean@valjean.fr")  # type: ignore[call-arg]
client.customer.create("jean@valjean.fr", "m", "Jean")  # type: ignore[misc]
client.customer.get(AssetRef("u", "ETH", "Ethereum"))  # type: ignore[arg-type]
client.customer.update("c", notifications={"sms": True})  # type: ignore[arg-type]
client.bank.withdraw("c", [50])  # type: ignore[arg-type]
client.bank.operations("c", from_="1")  # type: ignore[arg-type]
client.custody.withdraw("c", Asset.ETH, "1", "0xdef", travelRule={"platform": "Kraken"})  # type: ignore[arg-type]
client.custody.withdraw("c", Asset.ETH, "1")  # type: ignore[call-arg]
client.trading.get(OrderCreated("o", OrderState.REGISTERED))  # type: ignore[arg-type]
client.trading.list(direction=OrderState.DONE, user=Created("c"))  # a str is a str: the SDK checks the value at runtime
client.trading.buy("c", Asset.ETH, "25", "ref")  # type: ignore[misc]
client.transaction.get(Created("t"))  # type: ignore[arg-type]
client.transaction.list("c")  # type: ignore[misc]
client.transaction.list(limit="100")  # type: ignore[arg-type]
client.core.get(AssetRef("u", "ETH", "Ethereum"))  # type: ignore[arg-type]
client.core.list(CoreType.STAKING)  # type: ignore[misc]
client.staking.stake("c", Asset.SOL, "2")  # type: ignore[call-arg]
client.staking.stake("c", Asset.SOL, "2", provider=42)  # type: ignore[arg-type]
client.staking.get(StakingPosition)  # type: ignore[arg-type]
client.staking.rewards(OrderCreated("o", OrderState.REGISTERED))  # type: ignore[arg-type]
client.staking.unstake("p", [1])  # type: ignore[arg-type]
client.staking.list("c")  # type: ignore[misc]
client.staking.operations("c", 0, 10)  # type: ignore[misc]
client.staking.providers(42)  # type: ignore[arg-type]
client.webhooks.activate(endpoint=None)  # type: ignore[arg-type]
client.webhooks.list(True)  # type: ignore[misc]
client.webhooks.subscribe(Created("sub"))  # type: ignore[arg-type]
client.webhooks.archive(WebhookType("u", SubscriberState.ENABLED, WebhookEventName.CUSTODY_SENT, "{}", "{}"))  # type: ignore[arg-type]
client.webhooks.logs("sub", 0, 10)  # type: ignore[misc]
client.webhooks.catalogItem(Created("wh"))  # type: ignore[arg-type]
client.webhooks.verify(b"{}", {"X-BITGEN-Signature": "x"})  # type: ignore[call-arg]
client.webhooks.verify(b"{}", "X-BITGEN-Signature: x", "secret")  # type: ignore[arg-type]
client.webhooks.verify(b"{}", [("X-BITGEN-Signature", "x", "extra")], "secret")  # type: ignore[list-item]
client.webhooks.verify(b"{}", [b"x-bitgen-signature: x"], "secret")  # type: ignore[list-item]
client.webhooks.verify(b"{}", {}, "secret", "300")  # type: ignore[arg-type]
client.webhooks.verify({"delivery_id": "d"}, {}, "secret")  # type: ignore[arg-type]
client.apikeys.get(Created("key"))  # type: ignore[arg-type]
client.apikeys.list(True)  # type: ignore[misc]
client.apikeys.logs("key", limit="10")  # type: ignore[arg-type]

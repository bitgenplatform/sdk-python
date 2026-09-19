# Quick start

Create the client once, then run a first journey: create a customer, read their EUR account, open a wallet, buy crypto.

## 1. Create the client

```python
from bitgen import BitgenClient, Env

client = BitgenClient(
    scope="YOUR_SCOPE_UUID",  # uuid of the organization that owns the key
    apiKey="YOUR_API_KEY",
    env=Env.SANDBOX,  # Env.PRODUCTION by default
)
```

One instance per API key, reused for every call — it can be shared between threads. `scope`, `apiKey`, environments and the other options are detailed in [Configuration](configuration.md).

## 2. Create a customer

```python
from bitgen.models import Locale

customer = client.customer.create(
    "jean@valjean.fr",
    "MANAGER_UUID",  # the collaborator of your organization who follows this customer
    firstname="Jean",
    lastname="Valjean",
    locale=Locale.FR,
)
```

The customer receives an activation email: until they click it, their account stays `CREATED` and the bank, custody, trading and staking resources do not see it (unless you create them with `needActivation=False` — [Customers › create](resource/customer.md#create)). If your organization uses BITGEN's identity verification, their identity must also be validated before the next steps ([Activation and identity](concepts.md#activation-and-identity)). The `Created` object the API returned carries the customer's `uuid`: the next steps pass it as is, wherever a customer is expected ([User references](concepts.md#user-references)).

## 3. Read the EUR account

```python
account = client.bank.get(customer)

print(account.message)  # wire reference: the customer puts it on their bank transfer
print(account.balance)  # EUR balance, credited once the transfer is received
```

The EUR account is created on first read. Balance, operations and withdrawals: [Bank accounts](resource/bank.md).

## 4. Open a wallet

```python
from bitgen import Asset

wallet = client.custody.wallet(customer, Asset.ETH)

print(wallet.address)  # deposit address, created at the custodian on first read
print(wallet.balance)  # exact quantity, as a string
```

Wallets, balances and on-chain withdrawals: [Custody wallets](resource/custody.md).

## 5. Buy crypto

```python
from bitgen import Asset

created = client.trading.buy(
    customer,
    Asset.ETH,
    "25.00",  # EUR, taken from the customer's EUR account
    reference="order-42",  # optional idempotency key
)

order = client.trading.get(created.tunnel)  # `tunnel` is the order uuid; `order.state` follows its lifecycle
```

Orders, states and sales: [Trading](resource/trading.md).

## Handling errors

An error of the API raises a `BitgenError` carrying the HTTP `status` and a stable `code`:

```python
from bitgen import BitgenError

try:
    client.bank.withdraw(customer, "50.00")
except BitgenError as error:
    if error.code == "requested_amount_error":
        pass  # insufficient EUR balance
```

All the details, including the errors that happen before any request is sent: [Errors](errors.md).

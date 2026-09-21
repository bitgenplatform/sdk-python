# bitgen-sdk — v1.0.1

Official Python SDK for the BITGEN API v4 — server-side, Python 3.11+, no dependency beyond the standard library.
Install it with `pip install bitgen-sdk`.

```python
from bitgen import BitgenClient, Env

client = BitgenClient(
    scope="YOUR_SCOPE_UUID",  # uuid of the organization that owns the key
    apiKey="YOUR_API_KEY",
    env=Env.SANDBOX,  # Env.PRODUCTION by default
)
```

- [Installation](readme/installation.md) — Python 3.11+, pip, what to import
- [Quick start](readme/quick-start.md) — a customer, their EUR account, a wallet, a purchase
- [Configuration](readme/configuration.md) — credentials, environments, custom host, timeout
- [Concepts](readme/concepts.md) — user references, amounts, pagination, assets, activation, the flows of a purchase, a sale, a deposit and a withdrawal
- [Errors](readme/errors.md) — `BitgenError`, error codes, invalid arguments

Resources, in the order of an integration:

- [Customers](readme/resource/customer.md) — `client.customer`
- [Bank accounts](readme/resource/bank.md) — `client.bank`
- [Custody wallets](readme/resource/custody.md) — `client.custody`
- [Trading](readme/resource/trading.md) — `client.trading`
- [Transactions](readme/resource/transaction.md) — `client.transaction`
- [Staking](readme/resource/staking.md) — `client.staking`
- [Connectors](readme/resource/core.md) — `client.core`
- [Webhooks](readme/resource/webhooks.md) — `client.webhooks`
- [API keys](readme/resource/apikeys.md) — `client.apikeys`
- [Assets](readme/resource/asset.md) — `client.asset`

## License

Private — © BITGEN

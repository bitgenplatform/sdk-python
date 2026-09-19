# Custody wallets

A custody wallet holds the crypto of a customer for one asset, at the custodian of the platform: a deposit address the customer sends funds to, an exact balance, and on-chain withdrawals to external addresses. `client.custody` lists and reads the wallets of a customer, provisions them, reads the EUR value of their custody, and withdraws.

Examples use `client`, a configured `BitgenClient` ([Configuration](../configuration.md)), and `customer`, the `Created` returned by `client.customer.create()`. A customer is designated by a `UserRef`: their uuid, or a model carrying it ([User references](../concepts.md#user-references)). `wallets` and `wallet` also take the uuid of your organization (your `scope`) to read its treasury wallets (`type` `TREASURY`, read-only); `portfolio` and `withdraw` are for customers only. A customer who is not an activated member of your organization is refused with `403 org_forbidden` ([Activation and identity](../concepts.md#activation-and-identity)); another organization, with `403 cross_org_forbidden`.

## Methods

| Method | What it does | Returns |
|---|---|---|
| `wallets(user)` | Lists the wallets of a customer, or of your organization | `list[Wallet]` |
| `wallet(user, asset)` | Reads one wallet with its EUR value curve — provisions it on first read | `Wallet` |
| `portfolio(user)` | Reads the EUR value curve of the whole custody of a customer | `CustodyPortfolio` |
| `withdraw(user, asset, amount, targetAddress, ...)` | Sends crypto from a wallet to an external address | `CustodyWithdrawal` |

Models of this resource, under `bitgen.models`: `Wallet`, `AssetRef`, `CustodyPortfolio`, `CustodyWithdrawal`, `TravelRule` (`TravelRulePerson`, `TravelRulePlatform`) — the constant classes `WalletState`, `WalletType`, and the shared `History`.

## Wallets

```
client.custody.wallets(user: UserRef) -> list[Wallet]
```

```python
wallets = client.custody.wallets(customer)

for wallet in wallets:
    print(wallet.asset.iso, wallet.balance, wallet.address)  # ETH 0.5 0xabc…

treasury = client.custody.wallets("YOUR_SCOPE_UUID")  # the treasury wallets of your organization
```

Returns a plain list of `Wallet` (a `list[Wallet]`, not a `Page`: the API answers the whole list), without their `history`:

| Attribute | Description |
|---|---|
| `uuid` | The wallet |
| `state` | `WalletState.CREATED` or `WalletState.FROZEN` — a string |
| `type` | `WalletType.USER` for a customer, `WalletType.TREASURY` for your organization — a string |
| `address` | The deposit address (or `None`) |
| `addressLegacy` | The same deposit address in the legacy format of the chain, for networks that have two address formats; `None` otherwise |
| `tag` | The memo / tag of the address, for the assets that use one (XRP, XLM…) — or `None` |
| `balance` | The exact quantity, as a string |
| `asset` | `AssetRef`: `uuid`, `iso`, `label` ([Assets](../concepts.md#assets) — compare `iso` case-insensitively) |
| `history` | Only on `wallet`: the EUR value curve, a `History` ([Timestamps and histories](../concepts.md#timestamps-and-histories)) — `None` here, and on a new wallet until the curve has been computed |

## Wallet

```
client.custody.wallet(user: UserRef, asset: str | models.Asset | AssetRef) -> Wallet
```

| Argument | Type | Description |
|---|---|---|
| `asset` | `str \| models.Asset \| AssetRef` | The asset, by uuid or ISO code (`Asset.ETH`) or by model ([Assets](../concepts.md#assets)) — never the uuid of the wallet |

```python
from bitgen import Asset

wallet = client.custody.wallet(customer, Asset.ETH)

# Show the customer where to send their ETH
print(wallet.address)  # 0xabc…
print(wallet.tag)  # None — a memo / tag only for assets that need one
print(wallet.balance)  # 0.5
print(len(wallet.history.d) if wallet.history else 0)  # 24 — EUR value over the last 24 hours, only on this unit read
```

When the customer has no wallet for this asset yet, the API **provisions** it: a deposit address is created at the custodian. The customer must be activated, not frozen (`403 account_frozen`), with a validated identity if your organization uses BITGEN's identity verification (`403 kyc_not_validated` — [Activation and identity](../concepts.md#activation-and-identity)) and no active compliance alert (`423 blocked_by_alert`). Returns the `Wallet` with its `history`.

## Portfolio

```
client.custody.portfolio(user: UserRef) -> CustodyPortfolio
```

```python
from datetime import UTC, datetime

portfolio = client.custody.portfolio(customer)

for epoch, value in portfolio.history.m:  # EUR value of the custody, one point per day over the last month
    print(datetime.fromtimestamp(epoch, tz=UTC).date(), value)
```

Returns a `CustodyPortfolio`: `uuid`, the custody account of the customer, `type`, `WalletType.USER` (a customer) or `WalletType.TREASURY` (the organization), and `history`, the EUR value curve — `uuid` and `type` are `None`, and the curve is at zero, while the customer has no custody yet. Customers only: your organization's uuid is refused with `415 custody_portfolio_treasury_unsupported`.

## Withdraw

```
client.custody.withdraw(user: UserRef, asset: str | models.Asset | AssetRef, amount: str | int | float | Decimal, targetAddress: str, *, targetTag: str | None = None, idempotencyKey: str | None = None, travelRule: TravelRule | None = None) -> CustodyWithdrawal
```

| Argument | Type | Description |
|---|---|---|
| `asset` | `str \| models.Asset \| AssetRef` | The asset, by uuid or ISO code (`Asset.ETH`) or by model |
| `amount` | `str \| int \| float \| Decimal` | The quantity to send, as a string: more than 0, at most the decimals of the asset (`baseUnit`) — sent untouched; the EUR value of the quantity must reach a minimum — `416 withdraw_below_minimum` below it ([Amounts](../concepts.md#amounts)) |
| `targetAddress` | `str` | The destination address |
| `targetTag` | `str \| None` | The destination memo / tag, for the assets that need one |
| `idempotencyKey` | `str \| None` | Optional, 64 characters max, unique per customer: replaying the same key returns the same transaction |
| `travelRule` | `TravelRule \| None` | Optional travel rule information on the destination: a person, `TravelRulePerson(firstname=…, lastname=…, address=…)` (at least one of them), **or** a platform, `TravelRulePlatform("Kraken")` — one form or the other, 255 characters max per field |

```python
from bitgen import Asset
from bitgen.models import TravelRulePlatform

withdrawal = client.custody.withdraw(
    customer,
    Asset.ETH,
    "0.05",  # string: up to 18 decimals, sent as is — above the asset's minimum (see Errors)
    "0xdef…",
    idempotencyKey="withdraw-42",
    travelRule=TravelRulePlatform("Kraken"),  # or TravelRulePerson(firstname="Jean", lastname="Valjean", address="…")
)

if withdrawal.transaction is not None:
    transaction = client.transaction.get(withdrawal.transaction)  # follow it in the transaction journal
    print(transaction.state)  # PENDING
```

Customers only: your organization's uuid is refused with `415 custody_treasury_withdraw_unsupported`. The EUR value of the withdrawal must reach the minimum (`416 withdraw_below_minimum` — [Amounts](../concepts.md#amounts)). Returns a `CustodyWithdrawal`: `transaction`, the uuid of the `Transaction` created for the withdrawal ([Transactions](transaction.md)) — `None` while the analysis has not created it yet.

## Errors

In addition to the [common errors](../errors.md#common-errors):

| Status | `code` | Meaning |
|---|---|---|
| `400` | `invalid_amount` | The amount is not valid |
| `400` | `invalid_travel_rule` | `travelRule` mixes the two forms, or a field is too long |
| `403` | `org_forbidden` | The customer is not an activated member of your organization |
| `403` | `cross_org_forbidden` | The uuid belongs to another organization |
| `403` | `account_frozen` | The customer's account is frozen |
| `403` | `kyc_not_validated` | Your organization uses BITGEN's identity verification and the customer's identity is not validated ([Activation and identity](../concepts.md#activation-and-identity)) |
| `403` | `wallet_frozen` | The wallet is frozen |
| `403` | `user_actions_disabled` | Customer actions are disabled for your organization (`user_can_actions` flag) |
| `404` | `unknown_asset` | Unknown asset — the wallet uuid is not accepted |
| `404` | `unknown_organization` | The organization is unknown |
| `404` | `withdraw_organization_unresolved` | The organization of the withdrawal is unresolved |
| `409` | `duplicate_withdraw` | Duplicate withdrawal |
| `412` | `custody_not_enabled` | The `CUSTODY` connector of your organization is not enabled |
| `415` | `custody_portfolio_treasury_unsupported` | `portfolio` on your organization |
| `415` | `custody_treasury_withdraw_unsupported` | `withdraw` on your organization |
| `416` | `amount_precision_exceeded` | More decimals than the asset allows |
| `416` | `withdraw_below_minimum` | The EUR value of the quantity is below the minimum |
| `416` | `withdraw_price_unavailable` | No price is available to value the withdrawal |
| `416` | `requested_amount_error` | Insufficient balance |
| `416` | `custody_vault_insufficient` | The custody vault is insufficient |
| `416` | `withdraw_target_too_long` | `targetAddress` is too long |
| `422` | `withdraw_target_invalid` | `targetAddress` is not valid |
| `422` | `withdraw_target_tag_required` | The asset needs a `targetTag` |
| `422` | `withdraw_target_address_required` | `targetAddress` is missing |
| `422` | `invalid_idempotency_key` | `idempotencyKey` is not valid (64 characters max) |
| `422` | `asset_not_supported` | The custodian does not support this asset |
| `422` | `asset_address_unavailable` | No deposit address is available for this asset |
| `423` | `blocked_by_alert` | An active compliance alert blocks the customer |
| `423` | `custody_lock_unavailable` | The custody is locked by a concurrent operation |
| `503` | `custody_vault_unavailable` | The custodian's vault is unavailable |
| `503` | `custody_gas_unavailable` | Gas is unavailable at the custodian |
| `503` | `custody_address_unverifiable` | The destination address could not be verified |

## Related

- [Assets](../concepts.md#assets) — uuid or ISO code, case
- [Amounts](../concepts.md#amounts) — crypto amounts as strings, minimums
- [Assets catalogue](asset.md) — the decimals (`baseUnit`) and state of each asset
- [Trading](trading.md) — sales take crypto from custody
- [Staking](staking.md) — staking moves crypto from custody to the provider
- [Transactions](transaction.md) — the journal where deposits and withdrawals appear
- [Webhooks](webhooks.md) — `custody.wallet.created`, `custody.received`, `custody.sent`, `custody.transaction`

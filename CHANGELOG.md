## [1.0.4] - 2026-10-09

### Changed
- Documentation: the `scope` placeholder in the examples is now `YOUR_ORGANIZATION_SCOPE` (was `YOUR_SCOPE_UUID`) — the uuid of the organization that owns the key

## [1.0.3] - 2026-10-07

### Added
- `customer.create()` takes a `canLogin: bool | None` keyword argument (default `True`): `False` creates a customer who cannot sign in to the BITGEN web application — the activation then answers only their `uuid` instead of a session. For an organization that drives everything through the API with its own interface
- `bank.withdraw()` takes an `idempotencyKey: str | None` keyword argument (64 characters max, unique per customer): an identical replay reserves the amount once and returns the same `transaction`, the same key with a different amount is refused with `412 idempotency_amount_mismatch`, an invalid key with `422 invalid_idempotency_key`. A key identifies one withdrawal for good, a failed one included

### Changed
- `readme/resource/customer.md`: creating a customer from an email that already has an active, KYC-validated account no longer attaches it immediately — the person is invited and the attachment takes effect when they accept, so the customer is not usable on the financial routes until then. `409 user_already_assigned` now fires only when the person is already a **customer** of another organization
- `readme/resource/customer.md`: the `409 account_unavailable` window is **14 days**, not 15 minutes — an email belonging to an account still being created is refused for two weeks, the time the person has to answer their invitation
- `readme/resource/bank.md`: `reference` identifies one deposit and one only — same amount, idempotent; different amount, `412 reference_amount_mismatch`; over 218 characters, `416 reference_too_long`
- `readme/resource/custody.md`: new `409 withdraw_replay_mismatch` — same `idempotencyKey` replayed with a different amount or destination address. An identical replay still returns the existing movement
- `readme/resource/bank.md`: the `transaction` returned by `withdraw()` — its line in the journal is opened by the compliance analysis within a minute of the call, so reading the journal before that answers `404 unknown_transaction`. Bank details sent with a withdrawal are written to the account even when the withdrawal is then refused
- `readme/resource/staking.md`: `stake()` with a customer uuid it cannot use now answers `403 org_forbidden` instead of `404 unknown_user`

## [1.0.2] - 2026-09-23

### Changed
- Documentation only, no code change. `readme/resource/bank.md`: `credit()` on a provider that reports the deposit itself answers `201` with an empty body and no `uuid` (it answered `202` before) — `uuid` is `''`, the movement appears in `pending.in_` a second later
- `readme/resource/trading.md`: new `429 daily_buy_limit_exceeded` on `buy()` — **sandbox only**, purchases are capped per customer and per calendar day because the sandbox buys with test tokens. No such cap exists in production

## [1.0.0] - 2026-09-19

### Added
- `BitgenClient` with keyword-only arguments (`scope`, `apiKey`, `env`, `host`, `port`, `isSsl`, `timeout`); `env` is one of the `bitgen.Env` constants
- `Env` (`PRODUCTION`, `SANDBOX`) and `Asset` (`BTC`, `ETH`, `USDC`, `XRP`, `SOL` — provisional list) string constants: every enumerated value is a constant on a frozen class listing its `VALUES`
- `BitgenError` with `status` (the HTTP status) and `code` (the stable error code of the API); `str(error)` is `"<code> (HTTP <status>)"`
- `request_timeout` / `network_error` errors (`status` `0`, transport error in `__cause__`)
- `timeout` option, in seconds (default `30`, `0` disables), bounding the whole request
- Invalid arguments raise a `ValueError` (or a `TypeError` on a wrong type) before any request
- `User-Agent: bitgen-sdk-python/<version>` header on every request
- `Page[T]` for paginated lists (`count`, `items`); `UnexpectedAnswerError` for a 2xx answer that is not the shape the API promises
- `customer` resource (`create` with the `needActivation` / `notify` options, `list`, `get`, `update`) and its models — `Identity` as `KycIdentity` / `KybIdentity`; `UserRef` (`str | Created | Customer | Account | UserSummary | OrderUser`) wherever a customer is expected
- `bank` resource (`get`, `operations`, `withdraw`, `credit`) and its models — amounts as `str`, `int`, `float` or `Decimal`
- `custody` resource (`wallets`, `wallet`, `portfolio`, `withdraw` with `TravelRulePerson` / `TravelRulePlatform`) and its models
- `trading` resource (`buy`, `sell`, `get`, `list`) and its models
- `transaction` resource (`list`, `get`) and its models
- `staking` resource (`providers`, `stake`, `list`, `movements`, `get`, `rewards`, `unstake`, `operations`, `portfolio`) and its models
- `core` resource (`list`, `get`) and its models
- `webhooks` resource (`activate`, `updateEndpoint`, `regenerate`, `list`, `subscribe`, `archive`, `reactivate`, `logs`, `catalog`, `catalogItem`) and its models, with `verify()` to check a received delivery (HMAC signature, freshness, envelope) — the headers as any `dict`, WSGI `environ`, framework `headers` object or list of `(name, value)` pairs
- `apikeys` resource (`list`, `get`, `logs`) and its models
- Every method that expects the uuid of an object the SDK returns also takes the model itself (`Order`, `StakingMovement`, `StakingPosition`, `Core`, `Transaction`, `Subscriber`, `WebhookType`, `Apikey`)
- `asset` resource (`list`, `get`, `tickers`, `ticker`) and its models under `bitgen.models` (`Asset`, `AssetTicker`, `AssetFees`, `AssetNetwork`…, the `AssetState` constants, the shared `History`); every method that expects an asset also takes an `Asset` / `AssetRef` model
- No dependency beyond the standard library; Python 3.11 or later; fully typed (`py.typed`)

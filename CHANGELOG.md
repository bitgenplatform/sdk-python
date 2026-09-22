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

# API keys

An API key belongs to your organization: it is valid until it expires or is revoked, and every call made with it is journaled. `client.apikeys` reads the keys of your organization and the journal of their calls — it is read-only: a key cannot be created through the API, and the SDK does not revoke.

Examples use `client`, a configured `BitgenClient` ([Configuration](../configuration.md)). Wherever the API expects your organization, the SDK sends the `scope` of the client.

## Methods

| Method | What it does | Returns |
|---|---|---|
| `list(...)` | Lists the keys of your organization | `Page[Apikey]` |
| `get(apikey)` | Reads one key | `Apikey` |
| `logs(apikey, ...)` | Lists the calls made with a key | `Page[ApikeyLog]` |

Models of this resource, under `bitgen.models`: `Apikey`, `ApikeyOrganization`, `ApikeyHub`, `ApikeyOwner`, `ApikeyLog` — and the constant class `ApikeyState`.

## List

```
client.apikeys.list(*, includeRevoked: bool | None = None, offset: int | None = None, limit: int | None = None) -> Page[Apikey]
```

| Argument | Type | Description |
|---|---|---|
| `includeRevoked` | `bool \| None` | Also returns the `ApikeyState.REVOKED` keys — default `False` ([Query booleans](../concepts.md#query-booleans)) |
| `offset`, `limit` | `int \| None` | [Pagination](../concepts.md#pagination) |

```python
page = client.apikeys.list(includeRevoked=True)

for key in page.items:
    print(key.name, key.state, key.expireAt)  # backend ENABLED 1735689600
```

Returns a page of `Apikey` ([get](#get)).

## Get

```
client.apikeys.get(apikey: str | Apikey) -> Apikey
```

`apikey` is the uuid of the key, or an `Apikey`.

```python
from datetime import UTC, datetime

key = client.apikeys.get("APIKEY_UUID")

print(key.state, datetime.fromtimestamp(key.expireAt, UTC).date())  # ENABLED 2025-01-01
```

Returns an `Apikey`:

| Property | Description |
|---|---|
| `uuid` | The key |
| `state` | `ApikeyState.ENABLED` or `ApikeyState.REVOKED` — a string; the `ApikeyState` constants name the known values |
| `name` | Label given at creation |
| `permissions` | What the key is allowed to do, as set by BITGEN — a list of strings |
| `expireAt`, `createdAt` | Epoch seconds |
| `organization` | `ApikeyOrganization`: `uuid`, `state`, `name`, `hub`, `owner` — `hub` is an `ApikeyHub` (`uuid`, `state`, `name`, `options`: internal) or `None`, `owner` is the owner of the organization, an `ApikeyOwner` (`uuid`, `login`, `firstname`, `lastname`) or `None` |

An unknown uuid answers `404 unknown_apikey`. The raw key itself is never returned: it is shown once, when the key is created.

## Logs

```
client.apikeys.logs(apikey: str | Apikey, *, offset: int | None = None, limit: int | None = None) -> Page[ApikeyLog]
```

`apikey` is the uuid of the key, or an `Apikey`.

| Argument | Type | Description |
|---|---|---|
| `offset`, `limit` | `int \| None` | [Pagination](../concepts.md#pagination) |

```python
page = client.apikeys.logs("APIKEY_UUID", offset=0, limit=50)

for call in page.items:
    print(call.date, call.path, call.status, call.error or "ok")  # 1701000000 GET /custody/… 200 ok
```

Returns a page of `ApikeyLog`, one entry per call made with the key: `date` (epoch seconds), `path` (`"GET /custody/…"`), `payload` (the inputs of the call as a JSON string, personal data masked), `status` (the HTTP status answered), `error` (response body of the failed call, `None` when the call succeeded).

## Errors

In addition to the [common errors](../errors.md#common-errors):

| Status | `code` | Meaning |
|---|---|---|
| `404` | `unknown_apikey` | Unknown key |
| `422` | `invalid_include_revoked` | `includeRevoked` is not a boolean value |

## Related

- [Configuration](../configuration.md#credentials) — `scope` and `apiKey`
- [Errors](../errors.md#common-errors) — a missing, unknown, revoked or expired key

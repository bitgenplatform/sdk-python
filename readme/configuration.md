# Configuration

A `BitgenClient` is built once per API key and reused — it can be shared between threads: it holds the credentials, the target environment and the request timeout, and nothing else. Its arguments are keyword-only.

```python
from bitgen import BitgenClient, Env

client = BitgenClient(
    scope="YOUR_SCOPE_UUID",
    apiKey="YOUR_API_KEY",
    env=Env.PRODUCTION,  # default
    timeout=30,  # seconds, default 30
)
```

## Credentials

| Argument | Description |
|---|---|
| `scope` | uuid of the organization that owns the key. Sent as the `BITGEN-Scope` header. It is also the organization the SDK uses wherever the API expects yours. |
| `apiKey` | The raw key, shown once when it is created by an administrator of the organization, in the BITGEN interface — never through the API. Sent as the `Api-key` header. |

A missing key, an unknown, revoked or expired key, or a `scope` that is not the key's organization, is refused with a `401` ([Common errors](errors.md#common-errors)).

## Environments

| `env` | Constant | URL |
|---|---|---|
| `production` | `Env.PRODUCTION` (default) | `https://api.bitgen.com` |
| `sandbox` | `Env.SANDBOX` | `https://api.sandbox.bitgen.com` |

`Env` holds these names as constants (`Env.VALUES` lists them): pass the constant. Anything else is refused before any request ([Validation](#validation)).

## Custom host

To reach the API through another hostname — a container, a tunnel — give `host` instead of `env`:

```python
from bitgen import BitgenClient

client = BitgenClient(
    scope="YOUR_SCOPE_UUID",
    apiKey="YOUR_API_KEY",
    host="my-hostname",  # bare hostname: no scheme, port or path
    port=8080,  # default 80
    isSsl=False,  # default True (https)
)
```

`isSsl=False` sends the key unencrypted: only towards a local container or a tunnel, never across a network.

## Timeout

`timeout` is the maximum time, in seconds, the SDK waits for the API to answer — the whole request, from the connection to the last byte of the answer: `30` by default, `0` disables it; an `int` or a `float` (`0.5`). When it expires, the call raises a `BitgenError` with `status` `0` and `code` `request_timeout` ([No HTTP response](errors.md#no-http-response)).

## Requests

Every request carries the headers `BITGEN-Scope`, `Api-key`, `Content-Type: application/json`, `Accept: application/json` and `User-Agent: bitgen-sdk-python/<version>`, where `<version>` is the installed version of the SDK. TLS certificates are verified against the certificates of the system — or against those named by the `SSL_CERT_FILE` / `SSL_CERT_DIR` environment variables of OpenSSL, for a private certificate authority. Redirects are never followed. The SDK connects directly: it does not read the proxy variables of the environment.

## Validation

An invalid configuration raises a `ValueError` from the constructor — or a `TypeError` when an argument has the wrong type — before any request is sent: empty `scope` or `apiKey` (or one that is not printable ASCII), `env` that is not one of `Env.VALUES`, `host` that is not a bare hostname, `port` outside 1–65535, `timeout` that is not a number of seconds between `0` and `2147483`. The values of `scope`, `apiKey`, `env` and `host` never appear in the message. Every other invalid argument is refused the same way, by the method that receives it ([Invalid arguments](errors.md#invalid-arguments)).

## Options

| Argument | Type | Default | Description |
|---|---|---|---|
| `scope` | `str` | — | Organization uuid |
| `apiKey` | `str` | — | API key |
| `env` | `str` | `Env.PRODUCTION` | Target environment — an `Env` constant |
| `host` | `str \| None` | `None` | Custom hostname, used instead of `env` |
| `port` | `int \| None` | `80` | Port, with `host` |
| `isSsl` | `bool` | `True` | `https` or `http`, with `host` |
| `timeout` | `int \| float` | `30` | Request timeout in seconds, `0` = none |

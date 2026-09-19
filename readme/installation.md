# Installation

`bitgen-sdk` is the official Python SDK for the BITGEN API v4. It runs server-side only: the API accepts browser requests from a fixed list of origins, so the SDK is not meant to be used from a browser.

## Requirements

- Python 3.11 or later
- No other dependency: the SDK only uses what Python already provides

## Install

```bash
pip install bitgen-sdk
```

## Import

The client, its errors and the constants are imported from the `bitgen` package:

```python
from bitgen import Asset, BitgenClient, BitgenError, Env
```

The package exposes the client (`BitgenClient`), its exception (`BitgenError`), two constant classes — `Env`, the environments, and `Asset`, the ISO codes of the main assets ([Configuration](configuration.md), [Assets](concepts.md#assets)) — and `Page`, the paginated lists. Under `bitgen.models` live the models the resources return, the constant classes naming their known values ([Constants](concepts.md#constants)), and the few objects a call takes as input (`TravelRulePerson`, `TravelRulePlatform`, the `ReceivedHeaders` shape of `verify`):

```python
from bitgen.models import AssetState, History
```

## Typing

The SDK is fully typed and ships its type information (`py.typed`), so a type checker such as mypy or pyright sees every signature: paginated lists are a generic `Page[T]` (`page.count`, `page.items`), and every value the API returns is an immutable object with typed attributes.

## Next steps

- [Quick start](quick-start.md) — create the client and run a first customer journey
- [Configuration](configuration.md) — credentials, environments, custom host, timeout
- [Concepts](concepts.md) — user references, amounts, pagination, assets, activation, the flows of a purchase, a sale, a deposit and a withdrawal
- [Errors](errors.md) — what a failed call raises, and what is checked before any request

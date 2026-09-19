# Assets

The assets are the crypto currencies and tokens of the BITGEN platform, each on its network, with its decimals, its fees, a live ticker and its EUR price history. `client.asset` reads this catalogue: which assets exist and are `AVAILABLE`, how many decimals an amount may carry, and the prices.

Examples use `client`, a configured `BitgenClient` ([Configuration](../configuration.md)). An asset is designated by its uuid or its ISO code, in any case — a string, such as the `Asset` constants — or by an `Asset` / `AssetRef` model returned by the SDK ([Assets](../concepts.md#assets)).

## Methods

| Method | What it does | Returns |
|---|---|---|
| `list()` | Lists the assets of the platform | `Page[models.Asset]` |
| `get(asset)` | Reads one asset | `models.Asset` |
| `tickers()` | Reads the ticker of every asset | `Page[AssetTickerItem]` |
| `ticker(iso)` | Reads the ticker and the EUR price history of one asset | `AssetTickerDetail` |

Models of this resource, under `bitgen.models`: `Asset` (written `models.Asset` below, to tell it from the `bitgen.Asset` constants), `AssetTicker`, `AssetFees`, `AssetFeesComputed`, `AssetNetwork`, `AssetNetworkType`, `AssetTickerItem`, `AssetTickerDetail`, `AssetRef` — the constant class `AssetState`, and the shared `History`.

## List

```
client.asset.list() -> Page[models.Asset]
```

```python
from bitgen.models import AssetState

page = client.asset.list()

for asset in page.items:
    if asset.state == AssetState.AVAILABLE:
        print(asset.iso, asset.label, asset.baseUnit)  # ETH Ethereum 18
```

Returns a page of `models.Asset` ([get](#get)).

## Get

```
client.asset.get(asset: str | models.Asset | AssetRef) -> models.Asset
```

`asset` is `Asset.ETH` or a uuid, or an `Asset` / `AssetRef` model: its uuid is sent.

```python
from bitgen import Asset

eth = client.asset.get(Asset.ETH)

print(eth.state, eth.baseUnit, eth.ticker.price)  # AVAILABLE 18 2031.5
```

Returns a `models.Asset`:

| Attribute | Description |
|---|---|
| `uuid` | The asset |
| `state` | `AssetState.AVAILABLE`, `UNAVAILABLE`, `ARCHIVED` or `HIDDEN` — a string; compare it with the constants (`asset.state == AssetState.AVAILABLE`), a value added by the API later is kept as is |
| `iso` | The ISO code, with the case it is stored with (`ETH`) — compare it case-insensitively |
| `label` | Display name (`Bitcoin`) |
| `contractAddress` | The contract address of a token — `""` for a native asset, never `None` |
| `baseUnit` | The decimals of the asset (18 by default, 24 at most): the precision amounts may carry |
| `gasUnit` | Gas units consumed by a transfer of this asset on its network; with the network's `gasBase`, it sizes the network fee |
| `logo` | The logo as a data URI (SVG), or `None` |
| `data` | Internal connector mapping, raw JSON string — not needed for an integration |
| `fees` | `low`, `medium`, `high` — the raw fee schedule of the gas provider, opaque (`Any`) — and `computed` (`AssetFeesComputed`): `gas` (gas cost of a transfer, in the smallest unit of the native coin), `native` (the same, in native coin units) |
| `ticker` | `AssetTicker`: `price` and `marketcap` (in EUR), `rank` (market cap rank), `percentChange24h` (24-hour change, in %) |
| `history` | The EUR price curve, a `History` ([Timestamps and histories](../concepts.md#timestamps-and-histories)) |
| `network` | `AssetNetwork`: `uuid`, `state` (state of the network record), `caip2` (chain identifier, CAIP-2 — `eip155:1`), `label`, `gasBase`, `data`, `type` (`AssetNetworkType`: `uuid`, `code` — the network family: `UTXO`, `EVM`, `COMPUTE_UNIT` or `DROPS` —, `label`, `data`) — both `data` are internal connector mappings, raw JSON strings, not needed for an integration |

An unknown uuid or ISO code answers `404 unknown_asset`.

## Tickers

```
client.asset.tickers() -> Page[AssetTickerItem]
```

```python
page = client.asset.tickers()

for item in page.items:
    print(item.iso, item.ticker.price, item.ticker.percentChange24h)  # BTC 61230.4 -1.2
```

Returns, for every asset, an `AssetTickerItem`: its `iso` and its `ticker` (`AssetTicker`): `price` and `marketcap` (in EUR), `rank` (market cap rank), `percentChange24h` (24-hour change, in %).

## Ticker

```
client.asset.ticker(iso: str) -> AssetTickerDetail
```

`iso` is the ISO code of the asset (`Asset.BTC`).

```python
from bitgen import Asset

btc = client.asset.ticker(Asset.BTC)

print(btc.ticker.price)  # 61230.4
print(len(btc.history.d))  # 24 — the EUR price over the last 24 hours, one point per hour
```

Returns an `AssetTickerDetail`: the `iso`, the `ticker` and the EUR price `history` of the asset.

## Errors

In addition to the [common errors](../errors.md#common-errors):

| Status | `code` | Meaning |
|---|---|---|
| `404` | `unknown_asset` | Unknown uuid or ISO code |

## Related

- [Assets](../concepts.md#assets) — the `Asset` constants, uuid or ISO code, case
- [Amounts](../concepts.md#amounts) — crypto amounts as strings, up to the decimals of the asset
- [Custody wallets](custody.md) — one wallet per customer and per asset
- [Trading](trading.md) — orders take an `AVAILABLE` asset

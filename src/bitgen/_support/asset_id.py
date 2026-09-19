"""An asset, as accepted by every method expecting one: its uuid or ISO code as a string (`Asset.ETH`, `"eth"`, a uuid —
any case, the API normalizes it), or an `Asset` / `AssetRef` model — the SDK then sends its uuid."""

from __future__ import annotations

from bitgen.models.asset import Asset, AssetRef


def resolve(asset: object) -> str:
    """`ValueError` on a model without a non-empty `uuid`, `TypeError` on anything that is not a string, an `Asset` or
    an `AssetRef` — both before any request."""
    if isinstance(asset, str):
        return asset
    if not isinstance(asset, Asset | AssetRef) or not isinstance(asset.uuid, str):
        raise TypeError("asset must be a uuid or an ISO code string, or an Asset / AssetRef model")
    if asset.uuid.strip() == "":
        raise ValueError("asset must be a uuid or an ISO code, or a model with a non-empty uuid")
    return asset.uuid

"""The catalogue of assets, tickers and EUR price histories (`client.asset`)."""

from __future__ import annotations

from bitgen._http.client import HttpClient
from bitgen._support import asset_id, path
from bitgen.models import _cast
from bitgen.models.asset import Asset, AssetRef, AssetTickerDetail, AssetTickerItem
from bitgen.page import Page


class AssetResource:
    """The catalogue of assets: which assets exist and are `AVAILABLE`, how many decimals an amount may carry, and the
    prices. Every method raises a `BitgenError` when the API answers an error or no HTTP answer is received; an invalid
    argument raises a `ValueError` (or a `TypeError`) before any request."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self) -> Page[Asset]:
        """Every asset of the platform"""
        return Page.from_dict(_cast.answer(self._http.get("/asset")), Asset.from_dict)

    def get(self, asset: str | Asset | AssetRef) -> Asset:
        """One asset, by uuid or ISO code (any case, sent as is — `Asset.ETH`, `"eth"`) or by model (its uuid is
        sent)"""
        segment = path.segment(asset_id.resolve(asset), "asset")
        return Asset.from_dict(_cast.answer(self._http.get(f"/asset/{segment}")))

    def tickers(self) -> Page[AssetTickerItem]:
        """The ticker of every asset"""
        return Page.from_dict(_cast.answer(self._http.get("/ticker")), AssetTickerItem.from_dict)

    def ticker(self, iso: str) -> AssetTickerDetail:
        """The ticker and the EUR price history of one asset, by ISO code"""
        segment = path.segment(iso, "iso")
        return AssetTickerDetail.from_dict(_cast.answer(self._http.get(f"/ticker/{segment}")))

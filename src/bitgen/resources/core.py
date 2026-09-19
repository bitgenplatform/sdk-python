"""The catalogue of the connectors of the platform, read-only (`client.core`)."""

from __future__ import annotations

from bitgen._http.client import HttpClient
from bitgen._support import asset_id, path, reference, values
from bitgen.models import _cast
from bitgen.models.asset import Asset, AssetRef
from bitgen.models.core import Core, CoreState, CoreType
from bitgen.page import Page


class CoreResource:
    """Which connectors exist, their state, and — for staking providers — the asset and the offer they carry. Every
    method raises a `BitgenError` when the API answers an error or no HTTP answer is received; an invalid argument
    raises a `ValueError` (or a `TypeError`) before any request."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(
        self,
        *,
        type: str | None = None,
        asset: str | Asset | AssetRef | None = None,
        state: str | None = None,
    ) -> Page[Core]:
        """The connectors matching the filters — not paginated: `count` is everything that matches. `type` is
        `IDENTITY`, `AML`, `TRADING`, `CUSTODY`, `STAKING` or `RAMP` (a `CoreType` constant); `asset` keeps the
        connectors attached to this asset (the `STAKING` ones): uuid, ISO code or model; `state` is `ENABLED` or
        `DISABLED` (a `CoreState` constant)."""
        query = {
            "type": values.optional_choice(type, CoreType.VALUES, "type"),
            "asset": None if asset is None else asset_id.resolve(asset),
            "state": values.optional_choice(state, CoreState.VALUES, "state"),
        }
        return Page.from_dict(_cast.answer(self._http.get("/applications/core", query)), Core.from_dict)

    def get(self, core: str | Core) -> Core:
        """One connector, by uuid or by model"""
        segment = path.segment(reference.resolve(core, Core, "core"), "core")
        return Core.from_dict(_cast.answer(self._http.get(f"/applications/core/{segment}")))

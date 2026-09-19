"""Purchases and sales of crypto for a customer, through the exchange of the platform (`client.trading`)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from bitgen._http.client import HttpClient
from bitgen._support import amount as amount_
from bitgen._support import asset_id, path, reference, user_id, values
from bitgen.models import _cast
from bitgen.models.asset import Asset, AssetRef
from bitgen.models.customer import UserRef
from bitgen.models.trading import Order, OrderCreated, OrderSide, TradingDirection
from bitgen.page import Page


class TradingResource:
    """Purchases, sales, orders. Every method raises a `BitgenError` when the API answers an error or no HTTP answer is
    received; an invalid argument raises a `ValueError` (or a `TypeError`) before any request."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def buy(
        self,
        user: UserRef,
        asset: str | Asset | AssetRef,
        amount: str | int | float | Decimal,
        *,
        reference: str | None = None,
    ) -> OrderCreated:
        """Buy crypto with EUR from the customer's bank account. `asset` by uuid or ISO code (`Asset.ETH`) or by model
        — must be `AVAILABLE`; `amount` in EUR, 2 decimals max; `reference` is an idempotency key per (customer, side,
        reference): replaying it returns the existing order."""
        return self._order(user, asset, amount, OrderSide.BUY, reference)

    def sell(
        self,
        user: UserRef,
        asset: str | Asset | AssetRef,
        amount: str | int | float | Decimal,
        *,
        reference: str | None = None,
    ) -> OrderCreated:
        """Sell crypto from the customer's custody wallet. `asset` by uuid or ISO code (`Asset.ETH`) or by model —
        must be `AVAILABLE`; `amount` the crypto quantity to sell, as a string, at most `baseUnit` decimals; `reference`
        is an idempotency key per (customer, side, reference): replaying it returns the existing order."""
        return self._order(user, asset, amount, OrderSide.SELL, reference)

    def get(self, order: str | Order) -> Order:
        """One order by its uuid (the `tunnel` returned by `buy` / `sell`) or by model"""
        segment = path.segment(reference.resolve(order, Order, "order"), "order")
        return Order.from_dict(_cast.answer(self._http.get(f"/trading/{segment}")))

    def list(
        self,
        *,
        user: UserRef | None = None,
        direction: str | None = None,
        asset: str | Asset | AssetRef | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Page[Order]:
        """The orders of the organization, optionally filtered by customer (`user`, unknown → `404 unknown_user`), side
        (`direction`: `buy` or `sell` — a `TradingDirection` constant; absent, both) and asset (ISO code, uuid or
        model)"""
        query = {
            "user": None if user is None else user_id.resolve(user),
            "direction": values.optional_choice(direction, TradingDirection.VALUES, "direction"),
            "asset": None if asset is None else asset_id.resolve(asset),
            "offset": values.optional_int(offset, "offset"),
            "limit": values.optional_int(limit, "limit"),
        }
        return Page.from_dict(_cast.answer(self._http.get("/trading/orders", query)), Order.from_dict)

    def _order(
        self,
        user: UserRef,
        asset: str | Asset | AssetRef,
        amount: str | int | float | Decimal,
        mode: str,
        ref: str | None,
    ) -> OrderCreated:
        """The body of the contract, `mode` set by the caller"""
        body = _compact(
            {
                "user": user_id.resolve(user),
                "asset": asset_id.resolve(asset),
                "amount": amount_.normalize(amount),
                "mode": mode,
                "reference": values.optional_string(ref, "reference"),
            }
        )
        return OrderCreated.from_dict(_cast.answer(self._http.post("/trading", body)))


def _compact(entries: dict[str, Any]) -> dict[str, Any]:
    """The entries that were given: a `None` value is not sent"""
    return {key: value for key, value in entries.items() if value is not None}

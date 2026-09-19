"""The crypto wallets of each customer, per asset (`client.custody`)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from bitgen._http.client import HttpClient
from bitgen._support import amount as amount_
from bitgen._support import asset_id, path, user_id, values
from bitgen.models import _cast
from bitgen.models.asset import Asset, AssetRef
from bitgen.models.custody import (
    CustodyPortfolio,
    CustodyWithdrawal,
    TravelRule,
    TravelRulePerson,
    TravelRulePlatform,
    Wallet,
)
from bitgen.models.customer import UserRef


class CustodyResource:
    """Deposit addresses, balances, EUR value and on-chain withdrawals. Every method raises a `BitgenError` when the API
    answers an error or no HTTP answer is received; an invalid argument raises a `ValueError` (or a `TypeError`) before
    any request."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def wallets(self, user: UserRef) -> list[Wallet]:
        """The wallets of a customer (or of the organization), without their `history`"""
        return [Wallet.from_dict(item) for item in _cast.answer_list(self._http.get(f"/custody/{_user(user)}"))]

    def wallet(self, user: UserRef, asset: str | Asset | AssetRef) -> Wallet:
        """One wallet by asset uuid or ISO code (`Asset.ETH`) or by model, with its `history`. A missing wallet is
        provisioned on first read (deposit address created at the custodian): the key then needs `custody.write`."""
        return Wallet.from_dict(_cast.answer(self._http.get(f"/custody/{_user(user)}/{_asset(asset)}")))

    def portfolio(self, user: UserRef) -> CustodyPortfolio:
        """The EUR value curve of the whole custody of a customer (customers only)"""
        return CustodyPortfolio.from_dict(_cast.answer(self._http.get(f"/custody/{_user(user)}/portfolio")))

    def withdraw(
        self,
        user: UserRef,
        asset: str | Asset | AssetRef,
        amount: str | int | float | Decimal,
        targetAddress: str,
        *,
        targetTag: str | None = None,
        idempotencyKey: str | None = None,
        travelRule: TravelRule | None = None,
    ) -> CustodyWithdrawal:
        """On-chain withdrawal to an external address (customers only). The amount reaches the API untouched — never
        rounded or reformatted. `targetTag` is the destination memo / tag for the assets that need one,
        `idempotencyKey` (64 characters max, unique per customer) makes the call idempotent, `travelRule` a
        `TravelRulePerson` or a `TravelRulePlatform`. `transaction` is `None` while the analysis has not created the
        line yet."""
        if travelRule is not None and not isinstance(travelRule, TravelRulePerson | TravelRulePlatform):
            raise TypeError("travelRule must be a TravelRulePerson or a TravelRulePlatform")
        body = _compact(
            {
                "asset": asset_id.resolve(asset),
                "amount": amount_.normalize(amount),
                "targetAddress": values.string(targetAddress, "targetAddress"),
                "targetTag": values.optional_string(targetTag, "targetTag"),
                "idempotencyKey": values.optional_string(idempotencyKey, "idempotencyKey"),
                "travelRule": None if travelRule is None else travelRule.to_dict(),
            }
        )
        return CustodyWithdrawal.from_dict(_cast.answer(self._http.put(f"/custody/{_user(user)}", body)))


def _user(user: UserRef) -> str:
    return path.segment(user_id.resolve(user), "user")


def _asset(asset: str | Asset | AssetRef) -> str:
    return path.segment(asset_id.resolve(asset), "asset")


def _compact(entries: dict[str, Any]) -> dict[str, Any]:
    """The entries that were given: a `None` value is not sent"""
    return {key: value for key, value in entries.items() if value is not None}

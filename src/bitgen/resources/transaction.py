"""The journal of the fiat and crypto movements of the organization, read-only (`client.transaction`)."""

from __future__ import annotations

from bitgen._http.client import HttpClient
from bitgen._support import asset_id, path, reference, user_id, values
from bitgen.models import _cast
from bitgen.models.asset import Asset, AssetRef
from bitgen.models.customer import UserRef
from bitgen.models.transaction import Transaction, TransactionDirection, TransactionSource, TransactionState
from bitgen.page import Page


class TransactionResource:
    """The transactions of the organization: bank and custody deposits and withdrawals, the internal legs of sales and
    staking. Every method raises a `BitgenError` when the API answers an error or no HTTP answer is received; an
    invalid argument raises a `ValueError` (or a `TypeError`) before any request."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(
        self,
        *,
        user: UserRef | None = None,
        status: str | None = None,
        source: str | None = None,
        direction: str | None = None,
        asset: str | Asset | AssetRef | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Page[Transaction]:
        """The transactions of the organization, optionally filtered by customer (`user`, unknown → `404 unknown_user`),
        state (`status`, a `TransactionState` constant), `source` (`BANK` or `CUSTODY`), `direction` (`IN` or `OUT`)
        and asset (ISO code, uuid or model) — `limit` up to 100 on this list"""
        query = {
            "user": None if user is None else user_id.resolve(user),
            "status": values.optional_choice(status, TransactionState.VALUES, "status"),
            "source": values.optional_choice(source, TransactionSource.VALUES, "source"),
            "direction": values.optional_choice(direction, TransactionDirection.VALUES, "direction"),
            "asset": None if asset is None else asset_id.resolve(asset),
            "offset": values.optional_int(offset, "offset"),
            "limit": values.optional_int(limit, "limit"),
        }
        return Page.from_dict(_cast.answer(self._http.get("/transaction", query)), Transaction.from_dict)

    def get(self, transaction: str | Transaction) -> Transaction:
        """One transaction, by uuid, by reference, or by model"""
        segment = path.segment(reference.resolve(transaction, Transaction, "transaction"), "transaction")
        return Transaction.from_dict(_cast.answer(self._http.get(f"/transaction/{segment}")))

"""The EUR account of each customer (`client.bank`)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from bitgen._http.client import HttpClient
from bitgen._support import amount as amount_
from bitgen._support import path, user_id, values
from bitgen.models import _cast
from bitgen.models.bank import BankAccount, BankDirection, BankOperation, BankWithdrawal
from bitgen.models.customer import Created, UserRef
from bitgen.page import Page


class BankResource:
    """The EUR ledger of a customer: account, operations, withdrawals, declared deposits. Every method raises a
    `BitgenError` when the API answers an error or no HTTP answer is received; an invalid argument raises a `ValueError`
    (or a `TypeError`) before any request."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def get(self, user: UserRef) -> BankAccount:
        """The EUR account of a customer — created on first read"""
        return BankAccount.from_dict(_cast.answer(self._http.get(f"/bank/{_user(user)}")))

    def operations(
        self,
        user: UserRef,
        *,
        direction: str | None = None,
        from_: int | None = None,
        to: int | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Page[BankOperation]:
        """The EUR operations of a customer. `direction` is `ALL` (default), `DEPOSIT`, `WITHDRAWAL`, `PURCHASE` or
        `SELL` — a `BankDirection` constant; `from_` and `to` are epoch seconds, both together, otherwise ignored
        (`from_`: `from` is a reserved word in Python, the API receives `from`)."""
        query = {
            "direction": values.optional_choice(direction, BankDirection.VALUES, "direction"),
            "from": values.optional_int(from_, "from_"),
            "to": values.optional_int(to, "to"),
            "offset": values.optional_int(offset, "offset"),
            "limit": values.optional_int(limit, "limit"),
        }
        return Page.from_dict(
            _cast.answer(self._http.get(f"/bank/{_user(user)}/operations", query)), BankOperation.from_dict
        )

    def withdraw(
        self,
        user: UserRef,
        amount: str | int | float | Decimal,
        *,
        iban: str | None = None,
        bank: str | None = None,
        bic: str | None = None,
    ) -> BankWithdrawal:
        """Withdraw EUR (rounded to 2 decimals by the API) to the customer's IBAN — `iban` / `bank` / `bic` update the
        bank details first"""
        body = _compact(
            {
                "amount": amount_.normalize(amount),
                "iban": values.optional_string(iban, "iban"),
                "bank": values.optional_string(bank, "bank"),
                "bic": values.optional_string(bic, "bic"),
            }
        )
        return BankWithdrawal.from_dict(_cast.answer(self._http.put(f"/bank/{_user(user)}", body)))

    def credit(
        self,
        amount: str | int | float | Decimal,
        *,
        user: UserRef | None = None,
        message: str | None = None,
        reference: str | None = None,
        currency: str | None = None,
    ) -> Created:
        """Declare an EUR deposit (manual bank provider only) — the account is designated by `user` or by the wire
        `message`; `reference` (the bank's transfer reference) makes the call idempotent"""
        body = _compact(
            {
                "amount": amount_.normalize(amount),
                "currency": values.optional_string(currency, "currency"),
                "user": None if user is None else user_id.resolve(user),
                "message": values.optional_string(message, "message"),
                "reference": values.optional_string(reference, "reference"),
            }
        )
        return Created.from_dict(_cast.answer(self._http.post("/bank", body)))


def _user(user: UserRef) -> str:
    return path.segment(user_id.resolve(user), "user")


def _compact(entries: dict[str, Any]) -> dict[str, Any]:
    """The entries that were given: a `None` value is not sent"""
    return {key: value for key, value in entries.items() if value is not None}

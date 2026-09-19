"""The customers of the organization (`client.customer`)."""

from __future__ import annotations

from typing import Any

from bitgen._http.client import HttpClient
from bitgen._support import path, user_id, values
from bitgen.models import _cast
from bitgen.models.customer import Account, Created, Customer, Locale, Notifications, OrganizationCategory, UserRef
from bitgen.page import Page


class CustomerResource:
    """Creation, listing, and the reading or update of an account. Every method raises a `BitgenError` when the API
    answers an error or no HTTP answer is received; an invalid argument raises a `ValueError` (or a `TypeError`) before
    any request."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def create(
        self,
        email: str,
        manager: str,
        *,
        firstname: str | None = None,
        lastname: str | None = None,
        fin: str | None = None,
        needActivation: bool | None = None,
        notify: bool | None = None,
        locale: str | None = None,
        organization: str | None = None,
    ) -> Created:
        """Create a customer of the key's organization — or attach an existing, KYC-validated account to it. By default
        an activation email is sent: the customer stays `CREATED` and invisible to the financial resources (bank,
        custody, trading, staking) until they activate (`needActivation=False` skips it).

        `email` is the login of the customer, `manager` the uuid of the collaborator of the organization who follows
        them, `fin` a tax identification number (100 characters max), `locale` `FR` (default) or `EN` (a `Locale`
        constant), `organization` the category: `CUSTOMER` (default) or `B2B` (also opens a KYB file) — an
        `OrganizationCategory` constant; `BUSINESS` is reserved to platform administrators.
        """
        account = _compact(
            {
                "email": values.string(email, "email"),
                "firstname": values.optional_string(firstname, "firstname"),
                "lastname": values.optional_string(lastname, "lastname"),
                "fin": values.optional_string(fin, "fin"),
                "needActivation": values.optional_bool(needActivation, "needActivation"),
                "notify": values.optional_bool(notify, "notify"),
            }
        )
        body = _compact(
            {
                "account": account,
                # Only the manager comes from the caller: the organization is always the scope, and no role is ever
                # sent (the API takes ROLE_USER)
                "group": {"manager": values.string(manager, "manager"), "organization": self._http.scope},
                "locale": values.optional_choice(locale, Locale.VALUES, "locale"),
                # `BUSINESS` is reserved to platform administrators: refused here, like any string outside the list
                "organization": values.optional_choice(organization, OrganizationCategory.VALUES, "organization"),
            }
        )
        return Created.from_dict(_cast.answer(self._http.post("/customer", body)))

    def list(
        self,
        *,
        offset: int | None = None,
        limit: int | None = None,
        includeClosed: bool | None = None,
        manager: str | None = None,
    ) -> Page[Customer]:
        """The customers of the organization — a freshly created one appears as `CREATED`. `includeClosed` also lists
        the `CLOSED` customers; `manager` keeps only the customers directly managed by this collaborator (uuid)."""
        query = {
            "offset": values.optional_int(offset, "offset"),
            "limit": values.optional_int(limit, "limit"),
            "includeClosed": values.optional_bool(includeClosed, "includeClosed"),
            "manager": values.optional_string(manager, "manager"),
        }
        return Page.from_dict(_cast.answer(self._http.get("/customer", query)), Customer.from_dict)

    def get(self, user: UserRef) -> Account:
        """One account, by uuid (or email) or by model"""
        return Account.from_dict(_cast.answer(self._http.get(f"/account/{_user(user)}")))

    def update(
        self,
        user: UserRef,
        *,
        theme: str | None = None,
        locale: str | None = None,
        notifications: Notifications | None = None,
    ) -> None:
        """Update the settings a key may write: theme, locale (`FR` or `EN` — a `Locale` constant), notifications
        (`{"login": bool, "newsletter": bool}`) — nothing else is sent"""
        action = _compact(
            {
                "theme": values.optional_string(theme, "theme"),
                "locale": values.optional_choice(locale, Locale.VALUES, "locale"),
            }
        )
        body = _compact({"action": action, "notifications": _notifications(notifications)})
        self._http.put(f"/account/{_user(user)}", body)


def _user(user: UserRef) -> str:
    return path.segment(user_id.resolve(user), "user")


def _notifications(notifications: Notifications | None) -> dict[str, bool]:
    """The email preferences given — each one a boolean"""
    if notifications is None:
        return {}
    if not isinstance(notifications, dict):
        raise TypeError("notifications must be a dict with the keys login and newsletter")
    result: dict[str, bool] = {}
    for key in ("login", "newsletter"):
        if key in notifications:
            given = values.optional_bool(notifications[key], f"notifications[{key!r}]")
            if given is not None:
                result[key] = given
    unknown = set(notifications) - {"login", "newsletter"}
    if unknown:
        raise ValueError("notifications only takes the keys login and newsletter")
    return result


def _compact(entries: dict[str, Any]) -> dict[str, Any]:
    """The entries that were given: a `None` value — or an empty dict — is not sent"""
    return {key: value for key, value in entries.items() if value is not None and value != {}}

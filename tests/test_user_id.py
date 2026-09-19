from __future__ import annotations

from dataclasses import dataclass

import pytest

from bitgen._support import user_id
from bitgen.models import Account, AssetRef, Created, Customer, OrderUser, UserSummary

USER_MESSAGE = (
    r"^user must be a uuid or email string, or a Created / Customer / Account / UserSummary / OrderUser model$"
)
"""The `TypeError` of `user_id.resolve` — every resource taking a `UserRef` raises it"""


@dataclass(frozen=True)
class WithUuid:
    uuid: str


def test_uuid_email_and_the_models_that_carry_a_customer_uuid() -> None:
    assert user_id.resolve("ed1a19bb-1") == "ed1a19bb-1"
    assert user_id.resolve("jean@valjean.fr") == "jean@valjean.fr"
    assert user_id.resolve(Created("u")) == "u"
    assert user_id.resolve(Customer.from_dict({"uuid": "c-1"})) == "c-1"
    assert user_id.resolve(Account.from_dict({"uuid": "c-1"})) == "c-1"
    assert user_id.resolve(OrderUser("c-1", "jean@valjean.fr")) == "c-1"
    assert user_id.resolve(UserSummary.from_dict({"uuid": "c-1", "state": "ENABLED", "login": "j@v.fr"})) == "c-1"


def test_empty_values_are_refused() -> None:
    for value in ["", " ", Created(""), Created(" "), Customer.from_dict({})]:
        with pytest.raises(
            ValueError, match=r"^user must be a non-empty uuid or email, or a model with a non-empty uuid$"
        ):
            user_id.resolve(value)


def test_any_other_object_is_a_type_error() -> None:
    # a wrong model — an AssetRef, a plain object with a uuid — is a type error at the call, not an argument error
    for value in [None, 42, {"uuid": "u"}, object(), WithUuid("u"), AssetRef("u", "ETH", "Ethereum"), Created(None)]:  # type: ignore[arg-type]
        with pytest.raises(TypeError, match=USER_MESSAGE):
            user_id.resolve(value)

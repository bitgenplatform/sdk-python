"""A customer, as accepted by every method expecting one: their uuid (or an email, where the API resolves it), or one of
the models that carry a customer's uuid — the `Created` of `client.customer.create()`, a `Customer`, an `Account`, the
`user` of an `Order`, the `owner` of a `Transaction` or of a `StakingMovement`."""

from __future__ import annotations

from bitgen.models.customer import Account, Created, Customer, OrderUser, UserSummary

_MODELS = (Created, Customer, Account, UserSummary, OrderUser)


def resolve(user: object) -> str:
    """The uuid (or email) to send. A string is sent as is; a model is its `uuid`. An empty string, or a model without
    a non-empty `uuid`, is a `ValueError`; any other object — a `Wallet`, a plain object with a `uuid` — a `TypeError`:
    both before any request."""
    if isinstance(user, str):
        value = user
    elif isinstance(user, _MODELS) and isinstance(user.uuid, str):
        value = user.uuid
    else:
        raise TypeError(
            "user must be a uuid or email string, or a Created / Customer / Account / UserSummary / OrderUser model"
        )
    if value.strip() == "":
        raise ValueError("user must be a non-empty uuid or email, or a model with a non-empty uuid")
    return value

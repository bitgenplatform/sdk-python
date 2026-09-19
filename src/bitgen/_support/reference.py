"""A reference to an object the SDK returns — an order, a movement, a position, a connector… — given as its uuid or as
the model itself: the SDK then sends the model's uuid."""

from __future__ import annotations


def resolve(value: object, model: type | tuple[type, ...], name: str) -> str:
    """The uuid to send. A string is sent as is; a model of the expected class is its `uuid`. An empty string, or a
    model without a non-empty `uuid`, is a `ValueError`; any other object a `TypeError` — both before any request."""
    if isinstance(value, str):
        uuid = value
    elif isinstance(value, model) and isinstance(getattr(value, "uuid", None), str):
        uuid = getattr(value, "uuid")  # noqa: B009 - the model is checked above, its attribute is not typed here
    else:
        names = " / ".join(cls.__name__ for cls in (model if isinstance(model, tuple) else (model,)))
        raise TypeError(f"{name} must be a uuid string, or a {names} model")
    if uuid.strip() == "":
        raise ValueError(f"{name} must be a non-empty uuid, or a model with a non-empty uuid")
    return uuid

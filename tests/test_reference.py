from __future__ import annotations

import pytest

from bitgen._support import reference
from bitgen.models import AssetRef, Created, Order, OrderCreated, OrderState


def test_a_string_is_sent_as_is_and_a_model_of_the_expected_class_by_its_uuid() -> None:
    assert reference.resolve("o-1", Order, "order") == "o-1"
    assert reference.resolve(Order.from_dict({"uuid": "o-1"}), Order, "order") == "o-1"
    assert reference.resolve(Created("c"), (Created, Order), "user") == "c"


def test_empty_values_and_other_objects_are_refused() -> None:
    for empty in ["", " ", Order.from_dict({})]:
        with pytest.raises(ValueError, match=r"^order must be a non-empty uuid, or a model with a non-empty uuid$"):
            reference.resolve(empty, Order, "order")
    for wrong in [
        None,
        42,
        {"uuid": "o-1"},
        AssetRef("o-1", "ETH", "Ethereum"),
        OrderCreated("o-1", OrderState.REGISTERED),
        Order.from_dict({}).__class__,
    ]:
        with pytest.raises(TypeError, match=r"^order must be a uuid string, or a Order model$"):
            reference.resolve(wrong, Order, "order")
    with pytest.raises(TypeError, match=r"^user must be a uuid string, or a Created / Order model$"):
        reference.resolve(42, (Created, Order), "user")

"""Every model the resources return, built from the realistic fixtures of the resource tests: frozen, equal by value,
and safe to cache, ship across processes or copy (`pickle`, `copy.deepcopy`) — what an integrator does with them."""

from __future__ import annotations

import copy
import dataclasses
import pickle
from collections.abc import Callable, Mapping
from typing import Any

import pytest

from bitgen.models import (
    Account,
    Apikey,
    BankAccount,
    Core,
    Customer,
    Order,
    StakingMovement,
    Transaction,
    Wallet,
    WebhookSubscriptions,
)
from bitgen.models import Asset as AssetModel
from tests.test_apikeys import APIKEY
from tests.test_asset import ETH
from tests.test_bank import ACCOUNT as BANK_ACCOUNT
from tests.test_core import STAKING_CORE
from tests.test_custody import WALLET
from tests.test_customer import ACCOUNT, CUSTOMER
from tests.test_staking import MOVEMENT
from tests.test_trading import ORDER
from tests.test_transaction import TRANSACTION
from tests.test_webhooks import SUBSCRIPTIONS

CASES: list[tuple[Callable[[Mapping[str, Any]], object], dict[str, Any]]] = [
    (AssetModel.from_dict, ETH),
    (Customer.from_dict, CUSTOMER),
    (Account.from_dict, ACCOUNT),
    (BankAccount.from_dict, BANK_ACCOUNT),
    (Wallet.from_dict, WALLET),
    (Order.from_dict, ORDER),
    (Transaction.from_dict, TRANSACTION),
    (Core.from_dict, STAKING_CORE),
    (StakingMovement.from_dict, MOVEMENT),
    (WebhookSubscriptions.from_dict, SUBSCRIPTIONS),
    (Apikey.from_dict, APIKEY),
]


@pytest.mark.parametrize(("build", "data"), CASES, ids=[build.__qualname__.split(".")[0] for build, _ in CASES])
def test_models_are_frozen_compare_by_value_and_survive_pickle_and_deepcopy(
    build: Callable[[Mapping[str, Any]], object], data: dict[str, Any]
) -> None:
    model = build(data)
    assert dataclasses.is_dataclass(model)
    assert model == build(data)
    assert pickle.loads(pickle.dumps(model)) == model
    assert copy.deepcopy(model) == model
    first = dataclasses.fields(model)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(model, first, "x")
    # the nested models are frozen dataclasses as well: the whole tree is immutable
    for field in dataclasses.fields(model):
        nested = getattr(model, field.name)
        for item in nested if isinstance(nested, list) else [nested]:
            if dataclasses.is_dataclass(item) and not isinstance(item, type):
                with pytest.raises(dataclasses.FrozenInstanceError):
                    setattr(item, dataclasses.fields(item)[0].name, "x")

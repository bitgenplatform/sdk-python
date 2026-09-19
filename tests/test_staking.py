"""The `staking` resource against the fake transport: exact requests, mapping of the answers, errors, refusals."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from typing import Any

import pytest

from bitgen import Asset, BitgenError
from bitgen._http.client import HttpClient
from bitgen.models import Created, StakingMovementKind, StakingMovementState, StakingPositionState
from bitgen.resources.core import CoreResource
from bitgen.resources.staking import StakingResource
from tests.fake_transport import FakeTransport
from tests.test_core import STAKING_CORE
from tests.test_transaction import OWNER

# A realistic movement (contract § 9)
MOVEMENT: dict[str, Any] = {
    "uuid": "mv-1",
    "state": "COMPLETED",
    "kind": "STAKE",
    "provider": "figment_sol",
    "amount": "2",
    "createdAt": 1700000000,
    "updatedAt": 1700003600,
    "staking": {
        "uuid": "pos-1",
        "state": "ENABLED",
        "amount": "2",
        "error": None,
        "data": {"rewards": "0.0123", "lastRewardAt": 1700090000},
        "createdAt": 1700000000,
        "updatedAt": 1700090000,
        "core": {"uuid": "core-figment-sol", "name": "figment_sol", "label": "Figment SOL"},
    },
    "owner": OWNER,
    "asset": {"uuid": "asset-sol", "iso": "SOL", "label": "Solana"},
    "organization": {"uuid": "org-uuid", "state": "ENABLED", "name": "ACME"},
    "somethingNew": True,
}


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def staking(transport: FakeTransport) -> StakingResource:
    http = HttpClient(transport, "org-uuid", "k", "https://api.test", 1.0, "ua")
    return StakingResource(http, CoreResource(http))


def test_providers_delegate_to_the_core_catalogue(staking: StakingResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps({"count": 1, "items": [STAKING_CORE]}))
    providers = staking.providers(Asset.SOL)
    assert transport.last().url == "https://api.test/applications/core?type=STAKING&asset=sol"
    assert providers.count == 1
    assert providers.items[0].name == "figment_sol"
    assert providers.items[0].asset is not None
    assert providers.items[0].asset.iso == "SOL"
    staking.providers()
    assert transport.last().url == "https://api.test/applications/core?type=STAKING"
    staking.providers("asset-eth")
    assert transport.last().url == "https://api.test/applications/core?type=STAKING&asset=asset-eth"


def test_stake_sends_the_exact_body(staking: StakingResource, transport: FakeTransport) -> None:
    transport.will_answer(201, '{"uuid":"mv-1"}')
    created = staking.stake(Created("c-1"), Asset.SOL, "2", "figment_sol")
    assert created.uuid == "mv-1"
    assert (transport.last().method, transport.last().url) == ("POST", "https://api.test/staking")
    assert transport.last().body == b'{"user":"c-1","asset":"sol","amount":"2","provider":"figment_sol"}'
    staking.stake("c-1", Asset.ETH, 0.5, "core-bitgen-eth")  # the provider by uuid
    assert transport.last().body == b'{"user":"c-1","asset":"eth","amount":"0.5","provider":"core-bitgen-eth"}'


def test_list_and_movements_have_their_own_paths(staking: StakingResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps({"count": 1, "items": [MOVEMENT]}))
    page = staking.list(user=Created("c-1"), direction=StakingMovementKind.STAKE, offset=0, limit=50)
    assert transport.last().url == "https://api.test/staking?user=c-1&direction=STAKE&offset=0&limit=50"
    assert page.count == 1
    assert page.items[0].uuid == "mv-1"
    staking.list()
    assert transport.last().url == "https://api.test/staking"
    transport.will_answer(200, json.dumps({"count": 0, "items": []}))
    pending = staking.movements(user="c-1", direction=StakingMovementKind.REWARD)
    assert transport.last().url == "https://api.test/staking/movements?user=c-1&direction=REWARD"
    assert pending.count == 0
    assert pending.items == []
    staking.movements()
    assert transport.last().url == "https://api.test/staking/movements"


def test_get_maps_the_movement_and_its_position(staking: StakingResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps(MOVEMENT))
    movement = staking.get("mv-1")
    assert transport.last().url == "https://api.test/staking/mv-1"  # not /staking/movements
    assert movement.uuid == "mv-1"
    assert movement.state == StakingMovementState.COMPLETED
    assert movement.kind == StakingMovementKind.STAKE
    assert movement.provider == "figment_sol"
    assert movement.amount == "2"
    assert movement.createdAt == 1700000000
    assert movement.updatedAt == 1700003600
    assert movement.staking.uuid == "pos-1"
    assert movement.staking.state == StakingPositionState.ENABLED
    assert movement.staking.amount == "2"
    assert movement.staking.error is None
    assert movement.staking.data.rewards == "0.0123"
    assert movement.staking.data.lastRewardAt == 1700090000
    assert movement.staking.createdAt == 1700000000
    assert movement.staking.updatedAt == 1700090000
    assert (movement.staking.core.uuid, movement.staking.core.name, movement.staking.core.label) == (
        "core-figment-sol",
        "figment_sol",
        "Figment SOL",
    )
    assert movement.owner.uuid == "c-1"
    assert movement.owner.login == "jean@valjean.fr"
    assert movement.owner.account.firstname == "Jean"
    assert movement.asset.iso == "SOL"
    assert movement.organization is not None
    assert movement.organization.name == "ACME"
    assert movement.organization.hub is None
    # a failed request: position FAILED with an error, no rewards yet, no organization
    failed_body = {
        "uuid": "mv-2",
        "state": "FAILED",
        "kind": "STAKE",
        "provider": "bitgen_eth",
        "amount": "0.5",
        "createdAt": 1700000000,
        "updatedAt": 1700000000,
        "staking": {
            "uuid": "pos-2",
            "state": "FAILED",
            "amount": "0",
            "error": "custody_vault_unavailable",
            "data": {},
            "createdAt": 1700000000,
            "updatedAt": 1700000000,
            "core": {"uuid": "core-bitgen-eth", "name": "bitgen_eth", "label": "BITGEN ETH"},
        },
        "owner": OWNER,
        "asset": {"uuid": "asset-eth", "iso": "ETH", "label": "Ethereum"},
        "organization": None,
    }
    transport.will_answer(200, json.dumps(failed_body))
    failed = staking.get("mv-2")
    assert failed.staking.error == "custody_vault_unavailable"
    assert failed.staking.data.rewards is None
    assert failed.staking.data.lastRewardAt is None
    assert failed.organization is None


def test_rewards_and_unstake_send_an_amount_or_an_empty_object(
    staking: StakingResource, transport: FakeTransport
) -> None:
    transport.will_answer(200, "[]")
    staking.rewards("pos-1")
    assert (transport.last().method, transport.last().url) == ("PUT", "https://api.test/staking/pos-1/rewards")
    assert transport.last().body == b"{}"  # an object, not [] — the API reads an absent amount as "everything"
    transport.will_answer(200, "[]")
    staking.rewards("pos-1", "0.01")
    assert transport.last().body == b'{"amount":"0.01"}'
    transport.will_answer(200, "[]")
    staking.unstake("pos-1", 1)
    assert transport.last().url == "https://api.test/staking/pos-1/unstake"
    assert transport.last().body == b'{"amount":"1"}'
    transport.will_answer(200, "[]")
    staking.unstake("pos-1")
    assert transport.last().body == b"{}"
    assert len(transport.requests) == 4


def test_operations_and_portfolio_are_read_per_customer(staking: StakingResource, transport: FakeTransport) -> None:
    items = [
        {
            "txId": "op-1",
            "movement": "mv-1",
            "asset": "SOL",
            "kind": "STAKE",
            "amount": "2",
            "price": 128.4,
            "value": 256.8,
            "event": "validated",
            "provider": "figment_sol",
            "date": 1700003600,
        },
        {
            "txId": "op-2",
            "movement": None,
            "asset": "SOL",
            "kind": "REWARD",
            "amount": "0.0123",
            "price": 130,
            "value": 1.6,
            "event": "reward",
            "provider": "figment_sol",
            "date": 1700090000,
        },
    ]
    transport.will_answer(200, json.dumps({"count": 2, "items": items}))
    page = staking.operations(Created("c-1"), offset=0, limit=50)
    assert transport.last().url == "https://api.test/staking/c-1/operations?offset=0&limit=50"
    assert page.count == 2
    first = page.items[0]
    assert (first.txId, first.movement, first.asset, first.kind, first.amount) == (
        "op-1",
        "mv-1",
        "SOL",
        StakingMovementKind.STAKE,
        "2",
    )
    assert (first.price, first.value, first.event, first.provider, first.date) == (
        128.4,
        256.8,
        "validated",
        "figment_sol",
        1700003600,
    )
    assert page.items[1].movement is None  # a daily reward
    assert page.items[1].price == 130.0
    staking.operations("jean@valjean.fr")
    assert transport.last().url == "https://api.test/staking/jean%40valjean.fr/operations"
    transport.will_answer(
        200,
        json.dumps(
            {
                "uuid": "stk-1",
                "balances": {"capital": 4060.2, "revenues": 25.1},
                "histories": {
                    "capital": {
                        "d": [[1700000000, 4000.0], [1700003600, 4060.2]],
                        "w": [],
                        "m": [],
                        "y": [],
                        "all": [],
                    },
                    "revenues": {"d": [[1700003600, 25.1]], "w": [], "m": [], "y": [], "all": []},
                },
            }
        ),
    )
    portfolio = staking.portfolio("c-1")
    assert transport.last().url == "https://api.test/staking/c-1/portfolio"
    assert portfolio.uuid == "stk-1"
    assert portfolio.balances.capital == 4060.2
    assert portfolio.balances.revenues == 25.1
    assert portfolio.histories.capital.d == [(1700000000, 4000.0), (1700003600, 4060.2)]
    assert portfolio.histories.revenues.d == [(1700003600, 25.1)]
    assert portfolio.histories.revenues.all == []


@pytest.mark.parametrize(
    ("status", "code", "call"),
    [
        (412, "staking_not_enabled", lambda staking: staking.stake("c-1", Asset.SOL, "2", "figment_sol")),
        (412, "staking_connector_missing", lambda staking: staking.stake("c-1", Asset.SOL, "2", "figment_sol")),
        (422, "amount_below_minimum", lambda staking: staking.stake("c-1", Asset.SOL, "0.1", "figment_sol")),
        (416, "requested_amount_error", lambda staking: staking.stake("c-1", Asset.SOL, "100", "figment_sol")),
        (416, "insufficient_balance", lambda staking: staking.unstake("pos-1", "100")),
        (416, "insufficient_rewards", lambda staking: staking.rewards("pos-1", "100")),
        (425, "no_rewards", lambda staking: staking.rewards("pos-1")),
        (404, "unknown_staking_movement", lambda staking: staking.get("mv-x")),
        (404, "unknown_staking", lambda staking: staking.portfolio("c-x")),
        (404, "unknown_core", lambda staking: staking.stake("c-1", Asset.SOL, "2", "nope")),
        (403, "forbidden_permission", lambda staking: staking.list()),
    ],
)
def test_api_errors_become_bitgen_errors(
    staking: StakingResource, transport: FakeTransport, status: int, code: str, call: Any
) -> None:
    transport.will_answer(status, json.dumps({"error": True, "message": code, "code": status}))
    with pytest.raises(BitgenError) as caught:
        call(staking)
    assert (caught.value.status, caught.value.code) == (status, code)


def test_invalid_arguments_are_refused_before_any_request(staking: StakingResource, transport: FakeTransport) -> None:
    with pytest.raises(ValueError, match=r"^direction must be STAKE, UNSTAKE, WITHDRAW or REWARD$"):
        staking.list(direction="stake")
    with pytest.raises(ValueError, match=r"^direction must be STAKE, UNSTAKE, WITHDRAW or REWARD$"):
        staking.movements(direction="DEPOSIT")
    refused: list[Callable[[], object]] = [
        lambda: staking.stake("c-1", Asset.SOL, -1, "figment_sol"),
        lambda: staking.stake("c-1", Asset.SOL, "", "figment_sol"),
        lambda: staking.stake("", Asset.SOL, "2", "figment_sol"),
        lambda: staking.stake(Created(""), Asset.SOL, "2", "figment_sol"),
        lambda: staking.rewards("", "1"),
        lambda: staking.rewards("pos-1", 1e-8),
        lambda: staking.unstake(".."),
        lambda: staking.unstake("pos-1", math.inf),
        lambda: staking.get(""),
        lambda: staking.operations(""),
        lambda: staking.portfolio(Created(" ")),
        lambda: staking.list(user=""),
    ]
    for call in refused:
        with pytest.raises(ValueError):
            call()
    with pytest.raises(TypeError, match=r"^provider must be a string$"):
        staking.stake("c-1", Asset.SOL, "2", None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^amount must be a non-empty string or a finite number >= 0$"):
        staking.rewards("pos-1", True)  # a bool is an int for the type checker, not for the SDK
    assert transport.requests == []


def test_models_are_accepted_for_the_movement_the_position_the_customer_and_the_asset(
    staking: StakingResource, transport: FakeTransport
) -> None:
    transport.will_answer(200, json.dumps(MOVEMENT))
    movement = staking.get("mv-1")
    transport.will_answer(200, json.dumps(MOVEMENT))
    staking.get(movement)
    assert transport.last().url == "https://api.test/staking/mv-1"
    transport.will_answer(200, "[]")
    staking.rewards(movement.staking)  # the position carried by the movement
    assert transport.last().url == "https://api.test/staking/pos-1/rewards"
    transport.will_answer(200, "[]")
    staking.unstake(movement.staking, "1")
    assert transport.last().url == "https://api.test/staking/pos-1/unstake"
    transport.will_answer(201, '{"uuid":"mv-3"}')
    staking.stake(movement.owner, movement.asset, "2", movement.staking.core.name)
    assert transport.last().body == b'{"user":"c-1","asset":"asset-sol","amount":"2","provider":"figment_sol"}'
    staking.providers(movement.asset)
    assert transport.last().url == "https://api.test/applications/core?type=STAKING&asset=asset-sol"
    staking.operations(movement.owner)
    assert transport.last().url == "https://api.test/staking/c-1/operations"
    sent = len(transport.requests)
    with pytest.raises(TypeError, match=r"^movement must be a uuid string, or a StakingMovement model$"):
        staking.get(movement.staking)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^position must be a uuid string, or a StakingPosition model$"):
        staking.rewards(movement)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        staking.portfolio(object())  # type: ignore[arg-type]
    assert len(transport.requests) == sent

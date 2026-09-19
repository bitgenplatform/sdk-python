"""The `core` resource against the fake transport: exact queries, mapping of the answers, errors, refusals."""

from __future__ import annotations

import json
from typing import Any

import pytest

from bitgen import Asset, BitgenError
from bitgen._http.client import HttpClient
from bitgen.models import Core, CoreState, CoreType, Created
from bitgen.resources.core import CoreResource
from tests.fake_transport import FakeTransport

STAKING_CORE: dict[str, Any] = {
    "uuid": "core-figment-sol",
    "state": "ENABLED",
    "name": "figment_sol",
    "label": "Figment SOL",
    "type": "STAKING",
    "asset": {"uuid": "asset-sol", "iso": "SOL", "label": "Solana"},
    "config": [
        {
            "name": "connector",
            "label": {"fr": "Connecteur", "en": "Connector"},
            "data": {"type": "string", "value": "figment"},
        },
        {
            "name": "apr",
            "label": {"fr": "Taux annuel", "en": "Annual rate"},
            "data": {"type": "string", "value": "6.5"},
        },
        {
            "name": "min_deposit",
            "label": {"fr": "Dépôt minimum", "en": "Minimum deposit"},
            "data": {"type": "string", "value": "1"},
        },
        {"name": "api_key", "label": {"fr": "Clé", "en": "Key"}, "data": {"type": "password", "value": ""}},
        "not an object",
    ],
    "somethingNew": True,
}
# A bank connector: no asset
RAMP_CORE: dict[str, Any] = {
    "uuid": "core-bank",
    "state": "DISABLED",
    "name": "manual_bank",
    "label": "Manual bank",
    "type": "RAMP",
    "asset": None,
    "config": [],
}


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def core(transport: FakeTransport) -> CoreResource:
    return CoreResource(HttpClient(transport, "org-uuid", "k", "https://api.test", 1.0, "ua"))


def test_list_sends_the_exact_query_and_maps_cores(core: CoreResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps({"count": 1, "items": [STAKING_CORE]}))
    page = core.list(type=CoreType.STAKING, asset=Asset.ETH)
    assert (transport.last().method, transport.last().url) == (
        "GET",
        "https://api.test/applications/core?type=STAKING&asset=eth",
    )
    assert page.count == 1
    item = page.items[0]
    assert isinstance(item, Core)
    assert item.uuid == "core-figment-sol"
    assert item.state == CoreState.ENABLED
    assert item.name == "figment_sol"
    assert item.label == "Figment SOL"
    assert item.type == CoreType.STAKING
    assert item.asset is not None
    assert (item.asset.uuid, item.asset.iso, item.asset.label) == ("asset-sol", "SOL", "Solana")
    assert len(item.config) == 4  # the item that is not an object is skipped
    assert item.config[0].name == "connector"
    assert item.config[0].label == {"fr": "Connecteur", "en": "Connector"}
    assert item.config[0].data.type == "string"
    assert item.config[0].data.value == "figment"
    assert item.config[1].data.value == "6.5"
    assert item.config[3].data.type == "password"
    assert item.config[3].data.value == ""
    transport.will_answer(200, json.dumps({"count": 1, "items": [RAMP_CORE]}))
    banks = core.list(type=CoreType.RAMP, state=CoreState.DISABLED)
    assert transport.last().url == "https://api.test/applications/core?type=RAMP&state=DISABLED"
    assert banks.items[0].asset is None
    assert banks.items[0].config == []
    assert banks.items[0].state == CoreState.DISABLED
    core.list()
    assert transport.last().url == "https://api.test/applications/core"
    core.list(asset="asset-sol", state=CoreState.ENABLED)
    assert transport.last().url == "https://api.test/applications/core?asset=asset-sol&state=ENABLED"
    core.list(asset=item.asset)  # a model: its uuid
    assert transport.last().url == "https://api.test/applications/core?asset=asset-sol"


def test_get_maps_the_core(core: CoreResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps(STAKING_CORE))
    item = core.get("core-figment-sol")
    assert transport.last().url == "https://api.test/applications/core/core-figment-sol"
    assert item.name == "figment_sol"
    assert item.config[2].name == "min_deposit"
    assert item.config[2].data.value == "1"
    transport.will_answer(200, json.dumps(STAKING_CORE))
    core.get(item)  # a Core model: its uuid
    assert transport.last().url == "https://api.test/applications/core/core-figment-sol"


@pytest.mark.parametrize(
    ("status", "code", "call"),
    [
        (424, "unknown_core_type", lambda core: core.list(type=CoreType.RAMP)),
        (400, "invalid_core_status", lambda core: core.list(state=CoreState.ENABLED)),
        (404, "unknown_asset", lambda core: core.list(asset="xyz")),
        (404, "unknown_core", lambda core: core.get("nope")),
        (403, "forbidden_permission", lambda core: core.list()),
    ],
)
def test_api_errors_become_bitgen_errors(
    core: CoreResource, transport: FakeTransport, status: int, code: str, call: Any
) -> None:
    transport.will_answer(status, json.dumps({"error": True, "message": code, "code": status}))
    with pytest.raises(BitgenError) as caught:
        call(core)
    assert (caught.value.status, caught.value.code) == (status, code)


def test_invalid_arguments_are_refused_before_any_request(core: CoreResource, transport: FakeTransport) -> None:
    with pytest.raises(ValueError, match=r"^type must be IDENTITY, AML, TRADING, CUSTODY, STAKING or RAMP$"):
        core.list(type="staking")
    with pytest.raises(ValueError, match=r"^state must be ENABLED or DISABLED$"):
        core.list(state="enabled")
    with pytest.raises(ValueError):
        core.get("..")
    with pytest.raises(TypeError, match=r"^core must be a uuid string, or a Core model$"):
        core.get(Created("core-1"))  # type: ignore[arg-type]
    assert transport.requests == []


def test_models_are_accepted_for_the_core_and_the_asset(core: CoreResource, transport: FakeTransport) -> None:
    transport.will_answer(200, json.dumps(STAKING_CORE))
    item = core.get("core-figment-sol")
    transport.will_answer(200, json.dumps(STAKING_CORE))
    core.get(item)
    assert transport.last().url == "https://api.test/applications/core/core-figment-sol"
    assert item.asset is not None
    core.list(type=CoreType.STAKING, asset=item.asset)
    assert transport.last().url == "https://api.test/applications/core?type=STAKING&asset=asset-sol"
    sent = len(transport.requests)
    with pytest.raises(TypeError, match=r"^core must be a uuid string, or a Core model$"):
        core.get(item.asset)  # type: ignore[arg-type]
    assert len(transport.requests) == sent

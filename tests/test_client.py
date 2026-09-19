"""The entry point: configurations that build, configurations refused before any request."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

import bitgen.resources
from bitgen import BitgenClient, Env
from bitgen.resources import AssetResource, BankResource, CustomerResource

ROOT = Path(__file__).resolve().parent.parent


def test_valid_configurations_build() -> None:
    client = BitgenClient(scope="org-uuid", apiKey="k")
    assert isinstance(client, BitgenClient)
    assert isinstance(client.customer, CustomerResource)
    assert isinstance(client.bank, BankResource)
    assert isinstance(client.asset, AssetResource)
    assert isinstance(BitgenClient(scope="org-uuid", apiKey="k", env=Env.SANDBOX, timeout=0), BitgenClient)
    assert isinstance(
        BitgenClient(scope="org-uuid", apiKey="k", env=Env.LOCALHOST, port=4000, timeout=0.5), BitgenClient
    )
    assert isinstance(
        BitgenClient(scope="org-uuid", apiKey="k", host="my-hostname", port=8080, isSsl=False), BitgenClient
    )


def test_every_resource_hangs_off_the_client_in_the_order_of_the_readme() -> None:
    """Every `*Resource` the package exports is an attribute of the client, in the order README.md lists the
    resources — a resource added to the package but not to the client, or not documented, fails here"""
    client = BitgenClient(scope="org-uuid", apiKey="k")
    attributes = [name for name, value in vars(client).items() if type(value).__name__.endswith("Resource")]
    exported = {name for name in bitgen.resources.__all__ if name.endswith("Resource")}
    assert {type(getattr(client, name)).__name__ for name in attributes} == exported
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    documented = re.findall(r"^- \[[^\]]+\]\(readme/resource/[a-z]+\.md\) — `client\.([a-z]+)`$", readme, re.MULTILINE)
    assert attributes == documented, (attributes, documented)
    assert (
        BitgenClient.__annotations__
        and [name for name in BitgenClient.__annotations__ if name in attributes] == attributes
    ), "the attribute annotations of BitgenClient follow the same order"


@pytest.mark.parametrize(
    ("config", "error", "message"),
    [
        pytest.param({"scope": "", "apiKey": "k"}, ValueError, r"^scope must be a non-empty string$", id="empty scope"),
        pytest.param({"scope": "s", "apiKey": ""}, ValueError, r"^apiKey must be a non-empty string$", id="empty key"),
        pytest.param(
            {"scope": None, "apiKey": "k"}, TypeError, r"^scope must be a non-empty string$", id="scope not a string"
        ),
        pytest.param(
            {"scope": "s", "apiKey": 42}, TypeError, r"^apiKey must be a non-empty string$", id="key not a string"
        ),
        pytest.param(
            {"scope": "org\n", "apiKey": "k"}, ValueError, r"^scope contains invalid characters", id="non-ascii scope"
        ),
        pytest.param(
            {"scope": "s", "apiKey": "clé"}, ValueError, r"^apiKey contains invalid characters", id="non-ascii key"
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "env": "Sandbox"},
            ValueError,
            r"^env must be production, sandbox, staging or localhost$",
            id="unknown env",
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "host": "https://api"},
            ValueError,
            r"^host must be a bare hostname",
            id="host with scheme",
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "host": "me@attacker"},
            ValueError,
            r"^host must be a bare hostname",
            id="host with userinfo",
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "host": "api?x"},
            ValueError,
            r"^host must be a bare hostname",
            id="host with query",
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "host": "api:80"},
            ValueError,
            r"^host must be a bare hostname",
            id="host with port",
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "host": ""}, ValueError, r"^host must be a bare hostname", id="empty host"
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "port": 0},
            ValueError,
            r"^port must be an integer between 1 and 65535$",
            id="port 0",
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "host": "h", "port": 70000},
            ValueError,
            r"^port must be an integer between 1 and 65535$",
            id="port 70000",
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "port": "80"},
            TypeError,
            r"^port must be an integer between 1 and 65535$",
            id="port as a string",
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "isSsl": "no"},
            TypeError,
            r"^isSsl must be a boolean$",
            id="isSsl as a string",
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "timeout": -1},
            ValueError,
            r"^timeout must be a number of seconds between 0 \(no timeout\) and 2147483$",
            id="negative timeout",
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "timeout": float("inf")},
            ValueError,
            r"^timeout must be a number of seconds",
            id="infinite timeout",
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "timeout": float("nan")},
            ValueError,
            r"^timeout must be a number of seconds",
            id="nan timeout",
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "timeout": 2_147_484},
            ValueError,
            r"^timeout must be a number of seconds",
            id="too large timeout",
        ),
        pytest.param(
            {"scope": "s", "apiKey": "k", "timeout": "30"},
            TypeError,
            r"^timeout must be a number of seconds",
            id="timeout as a string",
        ),
    ],
)
def test_invalid_configurations_raise_before_any_request(
    config: dict[str, Any], error: type[Exception], message: str
) -> None:
    with pytest.raises(error, match=message):
        BitgenClient(**config)


def test_invalid_values_are_never_echoed() -> None:
    for config in [
        {"scope": "SECRET-SCOPE\n", "apiKey": "k"},
        {"scope": "s", "apiKey": "SECRET-KEY\n"},
        {"scope": "s", "apiKey": "k", "env": "SECRET-ENV"},
        {"scope": "s", "apiKey": "k", "host": "SECRET@HOST"},
    ]:
        with pytest.raises(ValueError) as caught:
            BitgenClient(**config)  # type: ignore[arg-type]
        assert "SECRET" not in str(caught.value)


def test_arguments_are_keyword_only() -> None:
    with pytest.raises(TypeError):
        BitgenClient("org-uuid", "k")  # type: ignore[misc]

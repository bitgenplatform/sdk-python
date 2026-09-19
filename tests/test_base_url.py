"""Hosts per environment, custom host, port and timeout validation."""

from __future__ import annotations

import math

import pytest

from bitgen import Env
from bitgen._http import base_url, timeout


def test_host_per_environment() -> None:
    assert base_url.resolve(Env.PRODUCTION, None, None, True) == "https://api.bitgen.com"
    assert base_url.resolve(Env.SANDBOX, None, None, True) == "https://api.sandbox.bitgen.com"
    assert base_url.resolve(Env.STAGING, None, None, True) == "https://api.staging.btgn.dev"
    assert base_url.resolve(Env.LOCALHOST, None, None, True) == "http://localhost:3002"
    assert base_url.resolve(Env.LOCALHOST, None, 4000, True) == "http://localhost:4000"
    with pytest.raises(ValueError, match=r"^env must be production, sandbox, staging or localhost$"):
        base_url.resolve("prod", None, None, True)
    with pytest.raises(TypeError, match=r"^env must be a string"):
        base_url.resolve(None, None, None, True)
    # port and isSsl are ignored with the hosted environments
    assert base_url.resolve(Env.SANDBOX, None, 8080, False) == "https://api.sandbox.bitgen.com"


def test_custom_host() -> None:
    assert base_url.resolve(Env.PRODUCTION, "my-hostname", None, True) == "https://my-hostname:80"
    assert base_url.resolve(Env.SANDBOX, "my-hostname", 8080, False) == "http://my-hostname:8080"
    assert base_url.resolve(Env.SANDBOX, "10.0.0.7", 3002, False) == "http://10.0.0.7:3002"
    assert base_url.resolve(Env.SANDBOX, "api_internal.corp.local", 443, True) == "https://api_internal.corp.local:443"


@pytest.mark.parametrize(
    "host", ["https://api", "api:80", "api/v4", "a b", "", "me@host", "host?x=1", "host#f", "[::1]", "api\n"]
)
def test_invalid_host(host: str) -> None:
    with pytest.raises(ValueError, match=r"^host must be a bare hostname"):
        base_url.resolve(Env.PRODUCTION, host, None, True)


@pytest.mark.parametrize("port", [0, -1, 65536])
def test_invalid_port(port: int) -> None:
    with pytest.raises(ValueError, match=r"^port must be an integer between 1 and 65535$"):
        base_url.resolve(Env.LOCALHOST, None, port, True)


def test_wrong_types() -> None:
    with pytest.raises(TypeError, match=r"^port must be an integer"):
        base_url.resolve(Env.LOCALHOST, None, "3002", True)
    with pytest.raises(TypeError, match=r"^port must be an integer"):
        base_url.resolve(Env.LOCALHOST, None, True, True)
    with pytest.raises(TypeError, match=r"^host must be a string"):
        base_url.resolve(Env.LOCALHOST, 42, None, True)
    with pytest.raises(TypeError, match=r"^isSsl must be a boolean$"):
        base_url.resolve(Env.LOCALHOST, "h", None, "yes")


def test_timeout_seconds() -> None:
    assert timeout.resolve(timeout.DEFAULT) == 30.0
    assert timeout.resolve(0) == 0.0
    assert timeout.resolve(0.0) == 0.0
    assert timeout.resolve(0.1) == 0.1
    assert timeout.resolve(timeout.MAX) == 2_147_483.0
    for bad in [-1, -0.5, math.inf, math.nan, timeout.MAX + 1]:
        with pytest.raises(
            ValueError, match=r"^timeout must be a number of seconds between 0 \(no timeout\) and 2147483$"
        ):
            timeout.resolve(bad)
    for wrong in ["30", None, True]:
        with pytest.raises(TypeError, match=r"^timeout must be a number of seconds"):
            timeout.resolve(wrong)
